"""Tests for repository-drift.py's merge-queue check. Run from the repository's
root with `python3 -m unittest discover -s scripts`. Standard library only."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "repository_drift", Path(__file__).with_name("repository-drift.py")
)
drift = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(drift)

STANDARD = json.loads(drift.MERGE_QUEUE.read_text(encoding="utf-8"))
RULESETS = f"repos/{drift.ORG}/maestro-core/rulesets"


def live(**changes):
    """The standard ruleset as GitHub returns it, with its id and timestamps,
    and `changes` applied."""
    ruleset = copy.deepcopy(STANDARD)
    ruleset.update(id=7, source_type="Repository", created_at="2026-09-25T18:59:58Z",
                   updated_at="2026-09-25T18:59:58Z", **changes)
    return ruleset


def problems(listed, ruleset=None):
    """What merge_queue_problems says of maestro-core when GitHub lists
    `listed` and returns `ruleset` for the one it names."""
    answers = {RULESETS: listed, f"{RULESETS}/7": ruleset}
    with mock.patch.object(drift, "gh_json", side_effect=lambda _, path: answers[path]):
        return drift.merge_queue_problems("maestro-core", STANDARD)


class MergeQueueProblems(unittest.TestCase):
    def test_a_missing_ruleset_is_reported_with_the_command_that_creates_it(self):
        found = problems([{"id": 3, "name": "branch-names"}])
        self.assertEqual(found, [
            "It has no `merge-queue` ruleset: create it from `.github` with "
            f"`gh api -X POST {RULESETS} --input org/repository-rulesets/merge-queue.json`."
        ])

    def test_an_inactive_ruleset_is_reported(self):
        found = problems([{"id": 7, "name": "merge-queue"}], live(enforcement="evaluate"))
        self.assertEqual(found, [
            "Its `merge-queue` ruleset is evaluate, not active: restore it from `.github` "
            f"with `gh api -X PUT {RULESETS}/7 --input org/repository-rulesets/merge-queue.json`."
        ])

    def test_a_different_rule_is_reported(self):
        rules = copy.deepcopy(STANDARD["rules"])
        rules[0]["parameters"]["merge_method"] = "MERGE"
        found = problems([{"id": 7, "name": "merge-queue"}], live(rules=rules))
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith(
            "Its `merge-queue` ruleset differs from the organization's: restore it"))

    def test_different_conditions_are_reported(self):
        conditions = {"ref_name": {"include": ["refs/heads/main"], "exclude": []}}
        found = problems([{"id": 7, "name": "merge-queue"}], live(conditions=conditions))
        self.assertEqual(len(found), 1)

    def test_the_standard_ruleset_is_no_problem_whatever_its_id_or_key_order(self):
        reordered = json.loads(json.dumps(live(), sort_keys=True))
        self.assertEqual(problems([{"id": 7, "name": "merge-queue"}], reordered), [])

    def test_rust_workflows_is_held_to_the_queue_like_any_repository(self):
        with mock.patch.object(drift, "gh_json", return_value=[]):
            found = drift.merge_queue_problems(drift.WORKFLOWS, STANDARD)
        self.assertEqual(len(found), 1)


if __name__ == "__main__":
    unittest.main()
