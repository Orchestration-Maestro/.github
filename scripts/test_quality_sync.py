"""Quality-sync exception tests; run `python3 -m unittest discover -s scripts`."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


if __name__ == "__main__":
    unittest.main()
