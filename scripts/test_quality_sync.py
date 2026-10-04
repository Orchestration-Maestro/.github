"""Quality-sync exception tests; run `python3 -m unittest discover -s scripts`."""

import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import org_quality

SPEC = importlib.util.spec_from_file_location(
    "quality_sync", Path(__file__).with_name("quality-sync.py")
)
assert SPEC is not None and SPEC.loader is not None
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class SyncExceptions(unittest.TestCase):
    def load(self, entries, repos=(("lbug", "other"), ("maestro-core", "rust"))):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "exceptions.json"
            path.write_text(json.dumps(entries), encoding="utf-8")
            return sync.load_exceptions(repos, path)

    def test_only_the_named_repository_and_command_are_skipped(self):
        exceptions = sync.load_exceptions([("lbug", "other"), ("maestro-core", "rust")])
        self.assertEqual(set(exceptions), {"lbug"})
        for repo in ("lbug", "maestro-core"):
            with self.subTest(repo=repo), tempfile.TemporaryDirectory() as directory:
                checkout = Path(directory)
                with mock.patch.object(sync, "clone", return_value=checkout) as clone, \
                     mock.patch.object(sync, "run", return_value="") as run, \
                     mock.patch.object(sync, "changed_files", return_value=["guide.md"]), \
                     mock.patch.object(sync, "publish", return_value=1) as publish:
                    sync.sync_one(repo, "pin", "4.8.7", "/gate", directory, False,
                                  exceptions)
                clone.assert_called_once_with(repo, checkout / repo)
                commands = [call.args[0] for call in run.call_args_list]
                expected = [
                    ["rust-gate", "rules"],
                    [sync.sys.executable, str(sync.SCRIPTS / "org-page.py"),
                     "--root", str(checkout)],
                    ["git", "add", "--intent-to-add", "."],
                    ["rust-gate", "guide"],
                ]
                if repo == "maestro-core":
                    expected.insert(0, ["rust-gate", "sync"])
                self.assertEqual(commands, expected)
                publish.assert_called_once()
                if repo == "lbug":
                    self.assertIn("Skipped `rust-gate sync`", publish.call_args.args[5])

    def test_unknown_repository_or_part_is_refused(self):
        for repository, part in (("unknown", "rust-gate sync"), ("lbug", "rules")):
            with self.subTest(repository=repository, part=part), \
                 self.assertRaisesRegex(RuntimeError, "unknown repository or part"):
                self.load([{"repository": repository, "part": part, "reason": "upstream"}])

    def test_invalid_exceptions_stop_before_installing_or_syncing(self):
        with mock.patch.object(sync, "repositories", return_value=[("lbug", "other")]), \
             mock.patch.object(sync, "load_exceptions", side_effect=RuntimeError("invalid")), \
             mock.patch.object(sync, "install_gate") as install, \
             mock.patch.object(sync, "sync_one") as sync_one, \
             self.assertRaisesRegex(RuntimeError, "invalid"):
            sync.main()
        install.assert_not_called()
        sync_one.assert_not_called()

    def test_repository_outside_the_synced_stacks_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, "unknown repository or part"):
            self.load([{"repository": "home", "part": "rust-gate sync", "reason": "upstream"}],
                      [("home", "workflows")])

    def test_invalid_shapes_and_empty_reasons_are_refused(self):
        entry = {"repository": "lbug", "part": "rust-gate sync", "reason": "upstream"}
        for entries in ({}, [None], [dict(entry, reason=" ")],
                        [dict(entry, extra=True)], [dict(entry, repository=[])], [entry, entry]):
            with self.subTest(entries=entries), self.assertRaises(RuntimeError):
                self.load(entries)


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
