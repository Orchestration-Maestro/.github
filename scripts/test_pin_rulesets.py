"""Repin and signed-publication tests; run unittest discover from the root."""

import base64
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import org_quality

SPEC = importlib.util.spec_from_file_location(
    "pin_rulesets", Path(__file__).with_name("pin-rulesets.py")
)
pin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pin)


class Repin(unittest.TestCase):
    def test_dry_run_finds_workflows_by_name_and_central_rules_without_writing(self):
        rulesets = [
            {"id": number, "name": name, "enforcement": "active", "rules": [
                {"type": "workflows", "parameters": {"workflows": [
                    {"repository_id": 123, "path": ".github/workflows/ci.yml",
                     "ref": "refs/tags/v0.1.0", "sha": "a" * 40}
                ]}}
            ]}
            for number, name in enumerate(("rust-central", "rust-slices"), 1)
        ]
        endpoint = "orgs/Orchestration-Maestro/rulesets"
        answers = {f"{endpoint}?per_page=100": rulesets}
        answers.update({f"{endpoint}/{r['id']}": r for r in rulesets})

        def run(args, **kwargs):
            self.assertEqual(args[:2], ["gh", "api"])
            self.assertEqual(len(args), 3, "a dry run must never write")
            return json.dumps(answers[args[2]])

        output = io.StringIO()
        with mock.patch.object(pin, "gh_json", return_value={"id": 123}) as lookup, \
             mock.patch.object(pin, "run", side_effect=run), \
             mock.patch.object(pin.sys, "argv", ["pin-rulesets.py", "--dry-run",
                                               "--release", "v0.1.1", "b" * 40]), \
             contextlib.redirect_stdout(output):
            pin.main()
        lookup.assert_called_once_with(
            "api", "repos/Orchestration-Maestro/maestro-rust-workflows")
        for name in ("rust-central", "rust-slices"):
            self.assertIn(f"{name}: .github/workflows/ci.yml refs/tags/v0.1.0", output.getvalue())
            self.assertIn(f"{name}: would PUT {endpoint}/", output.getvalue())


class Publish(unittest.TestCase):
    def test_republish_moves_branch_once_without_closing_pull_request(self):
        for existing, merge in ((True, True), (True, False), (False, True)):
            with self.subTest(existing=existing, merge=merge):
                self.check_publish(existing, merge)

    def check_publish(self, existing, merge):
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            (checkout / "guide.md").write_bytes(b"new guide\n")
            reference = f"repos/{org_quality.ORG}/repo/git/refs/heads/maestro/sync"
            updates = []
            state = {"open": existing}

            def run(args, **kwargs):
                if args[:2] == ["git", "rev-parse"]:
                    return "default-head\n"
                if args[:4] == ["gh", "api", "-X", "PATCH"] and args[4] == reference:
                    sha = args[6].removeprefix("sha=")
                    updates.append(sha)
                    if sha == "default-head":
                        state["open"] = False
                    self.assertNotEqual(sha, "default-head")
                    if not existing:
                        raise RuntimeError("ref does not exist")
                if args[:3] == ["gh", "pr", "edit"]:
                    self.assertTrue(state["open"], "PR edit must target an open PR")
                if args[:3] == ["gh", "pr", "create"]:
                    state["open"] = True
                    return "https://github.com/org/repo/pull/140\n"
                if args[:3] == ["gh", "pr", "merge"]:
                    self.assertTrue(state["open"], "auto-merge must target an open PR")
                return ""

            def gh_json(*args, stdin=None):
                if args[:2] == ("api", "graphql"):
                    assert stdin is not None
                    commit = json.loads(stdin)["variables"]["input"]
                    self.assertEqual(commit["expectedHeadOid"], "default-head")
                    self.assertNotEqual(commit["branch"]["branchName"], "maestro/sync")
                    self.assertEqual(commit["message"], {"headline": "sync title"})
                    self.assertEqual(commit["fileChanges"], {
                        "additions": [{"path": "guide.md", "contents":
                                       base64.b64encode(b"new guide\n").decode()}],
                        "deletions": [{"path": "old.md"}],
                    })
                    return {"data": {"createCommitOnBranch": {"commit": {"oid": "new-commit"}}}}
                self.assertEqual(args[:2], ("pr", "list"))
                return [{"number": 140}] if state["open"] else []

            with mock.patch.object(org_quality, "run", side_effect=run) as commands, \
                 mock.patch.object(org_quality, "gh_json", side_effect=gh_json):
                number = org_quality.publish("repo", checkout, ["guide.md", "old.md"],
                                             "maestro/sync", "sync title", "sync body", merge)
            self.assertEqual(number, "140")
            self.assertEqual(updates, ["new-commit"])
            calls = [call.args[0] for call in commands.call_args_list]
            action = "edit" if existing else "create"
            pr_command = ["gh", "pr", action]
            if existing:
                pr_command.append("140")
            pr_command += ["-R", f"{org_quality.ORG}/repo"]
            if not existing:
                pr_command += ["--head", "maestro/sync"]
            pr_command += ["--title", "sync title", "--body", "sync body"]
            self.assertIn(pr_command, calls)
            self.assertEqual(sum(call[:3] == ["gh", "pr", "merge"] for call in calls),
                             int(merge))
            if not existing:
                self.assertIn(["gh", "api", "-X", "POST",
                               f"repos/{org_quality.ORG}/repo/git/refs", "-f",
                               "ref=refs/heads/maestro/sync", "-f", "sha=new-commit"], calls)
            temporary = next(call[6].removeprefix("ref=refs/heads/") for call in calls
                             if call[:4] == ["gh", "api", "-X", "POST"])
            self.assertIn(["gh", "api", "-X", "POST",
                           f"repos/{org_quality.ORG}/repo/git/refs", "-f",
                           f"ref=refs/heads/{temporary}", "-f", "sha=default-head"], calls)
            self.assertIn(["gh", "api", "-X", "PATCH", reference,
                           "-f", "sha=new-commit", "-F", "force=true"], calls)
            self.assertIn(["gh", "api", "-X", "DELETE",
                           f"repos/{org_quality.ORG}/repo/git/refs/heads/{temporary}"], calls)

    def test_failed_commit_leaves_sync_branch_untouched_and_removes_temporary_branch(self):
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(org_quality, "run", return_value="default-head") as run, \
             mock.patch.object(org_quality, "gh_json", side_effect=RuntimeError("commit failed")), \
             self.assertRaisesRegex(RuntimeError, "commit failed"):
            org_quality.publish("repo", directory, ["old.md"], "maestro/sync",
                                "sync title", "sync body", True)
        calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[1][:4], ["gh", "api", "-X", "POST"])
        temporary = calls[1][6].removeprefix("ref=refs/heads/")
        self.assertEqual(calls[2], ["gh", "api", "-X", "DELETE",
                                  f"repos/{org_quality.ORG}/repo/git/refs/heads/{temporary}"])


if __name__ == "__main__":
    unittest.main()
