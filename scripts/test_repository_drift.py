"""Tests for repository-drift.py's page, baseline, merge-queue and name checks. Run from
the repository's root with `python3 -m unittest discover -s scripts`. Standard library only."""

import copy
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from test_org_page import PAGE_SCRIPT, page_checkout

SPEC = importlib.util.spec_from_file_location(
    "repository_drift", Path(__file__).with_name("repository-drift.py")
)
assert SPEC is not None and SPEC.loader is not None
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


# What every repository keeps of its own.
BASELINE = ("README.md", "LICENSE", "AGENTS.md", "CONTEXT.md", ".github/CODEOWNERS",
            ".github/workflows/scorecard.yml")
RULE_MAPS = ("docs/standards/northstar.md", "docs/standards/engineering.md",
             "docs/standards/security.md")
# What only the repositories older than the shared CI keep as well.
OLDER = (".github/copilot-instructions.md", ".github/workflows/dependabot-auto-merge.yml",
         *RULE_MAPS)


def baseline(repo, paths):
    """What baseline_problems says of `repo` when its default branch holds
    `paths`, it deletes merged branches and its forms need no label."""
    home = {"paths": set(), "texts": dict.fromkeys(drift.DEFAULTS), "labels": set()}
    with mock.patch.object(drift, "files_of", return_value=set(paths)), \
            mock.patch.object(drift, "gh_json", side_effect=lambda kind, *_: {} if kind == "api" else []):
        return drift.baseline_problems(repo, home)


def metadata(repo):
    """What metadata_problems says of `repo` when it has a description and a topic."""
    meta = {"description": "What it is.", "topics": ["rust"]}
    with mock.patch.object(drift, "gh_json", return_value=meta):
        return drift.metadata_problems(repo)


class BaselineProblems(unittest.TestCase):
    def test_mise_pins_are_the_tool_pins(self):
        self.assertEqual(baseline("maestro-core", (*BASELINE, *OLDER, "mise.toml", "mise.lock")), [])

    def test_other_pin_files_are_drift_in_every_repository(self):
        for repo, paths in (("maestro-core", (*BASELINE, *OLDER)), (drift.WORKFLOWS, BASELINE)):
            with self.subTest(repo=repo):
                self.assertEqual(baseline(repo, (*paths, "mise.toml", ".tool-versions")), [
                    "It pins tools in `.tool-versions`: keep tool pins in `mise.toml` and "
                    "`mise.lock` only, and delete the rest."
                ])

    def test_the_new_repositories_need_no_guide_rule_map_or_auto_merge(self):
        for repo in ("maestro", drift.WORKFLOWS):
            with self.subTest(repo=repo):
                self.assertEqual(baseline(repo, BASELINE), [])

    def test_a_rule_map_in_a_new_repository_is_drift(self):
        self.assertEqual(baseline(drift.WORKFLOWS, (*BASELINE, "docs/standards/engineering.md")), [
            "It keeps the rule map `docs/standards/engineering.md`, which this repository "
            "leaves out: its rules live in its own `AGENTS.md` and the shared CI."
        ])

    def test_the_new_repositories_still_keep_the_rest_of_the_baseline(self):
        self.assertEqual(baseline("maestro", BASELINE[:4]), [
            "It misses `.github/CODEOWNERS`, `.github/workflows/scorecard.yml`, which every "
            "repository keeps of its own."
        ])

    def test_older_repositories_keep_the_whole_baseline(self):
        self.assertEqual(baseline("maestro-core", BASELINE), [
            "It misses `.github/copilot-instructions.md`, "
            "`.github/workflows/dependabot-auto-merge.yml`, `docs/standards/northstar.md`, "
            "`docs/standards/engineering.md`, `docs/standards/security.md`, which every "
            "repository keeps of its own."
        ])


class MetadataProblems(unittest.TestCase):
    def test_the_product_repository_is_named_maestro(self):
        self.assertEqual(metadata("maestro"), [])

    def test_every_other_name_starts_with_maestro_and_a_hyphen(self):
        self.assertEqual(metadata("maestro-core"), [])
        for repo in ("lbug", "maestro_core", "maestro-", "Maestro-core"):
            with self.subTest(repo=repo):
                self.assertEqual(metadata(repo), [
                    "Its name is not `maestro` or `maestro-` then lowercase kebab-case: rename "
                    "it, and move every GitHub Actions `uses:` that names it, since Actions "
                    "follows no redirect."
                ])


class PageProblems(unittest.TestCase):
    def test_a_differing_page_is_reported_without_rewriting_it(self):
        with page_checkout() as (root, env):
            rendered = subprocess.run(
                [sys.executable, str(PAGE_SCRIPT), "--root", str(root)],
                env=env, capture_output=True, text=True,
            )
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            with mock.patch.object(drift, "clone", return_value=root), \
                    mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(drift.problems_of(".github", "other", root), [])
                page = root / "profile/README.md"
                stale = page.read_text(encoding="utf-8").replace(
                    "| Example repository |", "| Stale description |",
                )
                page.write_text(stale, encoding="utf-8")
                for stack in ("other", "rust"):
                    with self.subTest(stack=stack):
                        self.assertEqual(drift.problems_of(".github", stack, root), [
                            "Its organization page does not say what its sources say "
                            "(profile/README.md: a generated block differs from its source; "
                            "run scripts/org-page.py): fix the source it names, or run "
                            "`python3 scripts/org-page.py` and commit the page."
                        ])
                self.assertEqual(page.read_text(encoding="utf-8"), stale)


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
