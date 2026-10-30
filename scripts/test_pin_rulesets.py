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
             mock.patch.object(pin, "repositories", return_value=[]), \
             mock.patch.object(pin.sys, "argv", ["pin-rulesets.py", "--dry-run",
                                               "--release", "v0.1.1", "b" * 40]), \
             contextlib.redirect_stdout(output):
            pin.main()
        lookup.assert_called_once_with(
            "api", "repos/Orchestration-Maestro/maestro-rust-workflows")
        for name in ("rust-central", "rust-slices"):
            self.assertIn(f"{name}: .github/workflows/ci.yml refs/tags/v0.1.0", output.getvalue())
            self.assertIn(f"{name}: would PUT {endpoint}/", output.getvalue())


WARM_CACHE = """\
name: Warm cache
jobs:
  warm:
    uses: Orchestration-Maestro/maestro-rust-workflows/.github/workflows/ci.yml@{sha} # {tag}
    with:
      cache: true
  local:
    uses: ./.github/workflows/ci.yml
  other:
    uses: Orchestration-Maestro/maestro-rust-workflows-v4/.github/workflows/ci.yml@{sha} # {tag}
  checkout:
    steps:
      - uses: actions/checkout@{sha} # {tag}
      # uses: Orchestration-Maestro/maestro-rust-workflows/.github/workflows/ci.yml@{sha} # {tag}
"""
OLD, NEW = "a" * 40, "b" * 40


class CallerPins(unittest.TestCase):
    def test_forward_move_rewrites_only_calls_to_the_shared_workflows(self):
        text = WARM_CACHE.format(sha=OLD, tag="v0.17.0")
        moved, moves = pin.repinned_calls(text, "v0.18.0", NEW)
        self.assertEqual(moves, [(4, "refs/tags/v0.17.0", OLD)])
        expected = text.replace(
            f"workflows/ci.yml@{OLD} # v0.17.0\n    with:",
            f"workflows/ci.yml@{NEW} # v0.18.0\n    with:")
        self.assertEqual(moved, expected)

    def test_file_already_current_moves_nothing(self):
        text = WARM_CACHE.format(sha=NEW, tag="v0.18.0")
        self.assertEqual(pin.repinned_calls(text, "v0.18.0", NEW), (text, []))

    def test_call_without_a_release_comment_is_a_move_a_person_must_read(self):
        text = "    uses: Orchestration-Maestro/maestro-rust-workflows/.github/workflows/ci.yml@main\n"
        moved, moves = pin.repinned_calls(text, "v0.18.0", NEW)
        self.assertEqual(moves, [(1, "main", "main")])
        self.assertIn(f"ci.yml@{NEW} # v0.18.0", moved)
        self.assertRegex(pin.refusal(moves, "v0.18.0", (0, 18, 0), False), "not a release")

    def setup_repository(self, directory, files):
        workflows = Path(directory) / ".github/workflows"
        workflows.mkdir(parents=True)
        for name, text in files.items():
            (workflows / name).write_text(text, encoding="utf-8")
        return Path(directory)

    def pin_callers(self, files, tag, release, major, dry_run=False, existing=None):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            checkout = self.setup_repository(directory, files)
            with mock.patch.object(pin, "repositories",
                                   return_value=[("maestro", "rust"), ("maestro-docs", None)]), \
                 mock.patch.object(pin, "clone", side_effect=lambda repo, path:
                                   checkout if repo == "maestro" else self.setup_repository(
                                       Path(path), {})), \
                 mock.patch.object(pin, "open_pull_request", return_value=existing), \
                 mock.patch.object(pin, "publish", return_value="7") as publish, \
                 mock.patch.object(pin, "run") as run, \
                 contextlib.redirect_stdout(output):
                refused = pin.pin_callers(tag, NEW, release, major, dry_run)
            written = {name: (checkout / ".github/workflows" / name).read_text(encoding="utf-8")
                       for name in files}
        return refused, output.getvalue(), written, publish, run

    def test_forward_release_opens_one_pull_request_per_repository_with_callers(self):
        old = WARM_CACHE.format(sha=OLD, tag="v0.17.0")
        refused, output, written, publish, _ = self.pin_callers(
            {"warm-cache.yml": old, "notes.yml": "name: Notes\n"}, "v0.18.0", (0, 18, 0), False)
        self.assertEqual(refused, 0)
        self.assertIn(f"maestro: .github/workflows/warm-cache.yml:4 refs/tags/v0.17.0 {OLD} "
                      f"-> refs/tags/v0.18.0 {NEW}", output)
        self.assertEqual(written["warm-cache.yml"], pin.repinned_calls(old, "v0.18.0", NEW)[0])
        self.assertEqual(written["notes.yml"], "name: Notes\n")
        publish.assert_called_once()
        repo, _, files, branch, title, text, merge = publish.call_args.args
        self.assertEqual((repo, files, branch, merge),
                         ("maestro", [".github/workflows/warm-cache.yml"],
                          "ci/pin-maestro-rust-workflows", False))
        self.assertEqual(title, "ci: pin maestro-rust-workflows callers to v0.18.0")
        self.assertIn(NEW, text)
        self.assertIn(".github/workflows/warm-cache.yml", text)

    def test_dry_run_lists_each_caller_line_and_changes_nothing(self):
        old = WARM_CACHE.format(sha=OLD, tag="v0.17.0")
        refused, output, written, publish, run = self.pin_callers(
            {"warm-cache.yml": old}, "v0.18.0", (0, 18, 0), False, dry_run=True)
        self.assertEqual(refused, 0)
        self.assertIn("maestro: .github/workflows/warm-cache.yml:4 refs/tags/v0.17.0", output)
        self.assertIn("maestro: would open a pull request", output)
        self.assertEqual(written["warm-cache.yml"], old)
        publish.assert_not_called()
        run.assert_not_called()

    def test_current_file_publishes_nothing_and_closes_a_stale_pull_request(self):
        current = WARM_CACHE.format(sha=NEW, tag="v0.18.0")
        refused, output, _, publish, run = self.pin_callers(
            {"warm-cache.yml": current}, "v0.18.0", (0, 18, 0), False, existing={"number": 9})
        self.assertEqual(refused, 0)
        self.assertIn("maestro: closed pull request #9", output)
        publish.assert_not_called()
        self.assertEqual(run.call_args.args[0][:5], ["gh", "pr", "close", "9", "-R"])
        _, output, _, publish, run = self.pin_callers(
            {"warm-cache.yml": current}, "v0.18.0", (0, 18, 0), False)
        self.assertIn("maestro: on v0.18.0", output)
        publish.assert_not_called()
        run.assert_not_called()

    def test_a_major_release_waits_for_major_and_moves_with_it(self):
        old = WARM_CACHE.format(sha=OLD, tag="v0.17.0")
        files = {"warm-cache.yml": old.replace("v0.17.0", "v1.2.0")}
        refused, output, written, publish, _ = self.pin_callers(files, "v2.0.0", (2, 0, 0), False)
        self.assertEqual(refused, 1)
        self.assertIn("v2.0.0 is a major release", output)
        self.assertEqual(written, files)
        publish.assert_not_called()
        refused, _, _, publish, _ = self.pin_callers(files, "v2.0.0", (2, 0, 0), True)
        self.assertEqual(refused, 0)
        publish.assert_called_once()

    def test_a_pin_ahead_of_the_release_is_never_moved_back(self):
        files = {"warm-cache.yml": WARM_CACHE.format(sha=OLD, tag="v0.19.0")}
        refused, output, written, publish, _ = self.pin_callers(files, "v0.18.0", (0, 18, 0), False)
        self.assertEqual(refused, 1)
        self.assertIn("pinned to refs/tags/v0.19.0, ahead of v0.18.0", output)
        self.assertEqual(written, files)
        publish.assert_not_called()

    def test_main_moves_callers_after_the_rulesets_and_passes_major(self):
        order = []
        with mock.patch.object(pin, "gh_json", return_value={"id": 123}), \
             mock.patch.object(pin, "pin", side_effect=lambda *a: order.append("rulesets") or 0), \
             mock.patch.object(pin, "record", side_effect=lambda *a: order.append("record")), \
             mock.patch.object(pin, "pin_callers",
                               side_effect=lambda *a: order.append(a) or 0), \
             mock.patch.object(pin.sys, "argv", ["pin-rulesets.py", "--major"]), \
             mock.patch.object(pin, "latest_release", return_value=("v0.18.0", NEW)):
            pin.main()
        self.assertEqual(order, ["rulesets", "record", ("v0.18.0", NEW, (0, 18, 0), True, False)])


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
