#!/usr/bin/env python3
"""Hold every organization repository to the standard, one issue each.

A repository drifts when it has no `stack`, its merge queue differs from
org/repository-rulesets/, or it strays from the file baseline or metadata.
Each drifting repository has one issue here, updated on every run and closed
once it is back on the standard. Exits 1 when any repository drifts.
`--dry-run` reports and writes nothing. Needs GH_TOKEN (the organization bot's).
Standard library only.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from org_quality import (
    ORG,
    WORKFLOWS,
    clone,
    gh_json,
    repositories,
    run,
)

HOME = ".github"
# The file baseline: GitHub never inherits these repository-owned files.
OWN_FILES = (
    "README.md",
    "LICENSE",
    "AGENTS.md",
    "CONTEXT.md",
    ".github/CODEOWNERS",
    ".github/copilot-instructions.md",
    ".github/workflows/scorecard.yml",
    ".github/workflows/dependabot-auto-merge.yml",
    "docs/standards/northstar.md",
    "docs/standards/engineering.md",
    "docs/standards/security.md",
)
PAGE_SCRIPT = Path(__file__).with_name("org-page.py")
# Repository-local tool pins are outside the shared standard.
TOOL_PINS = (
    "mise.toml",
    "mise.lock",
    ".mise.toml",
    ".tool-versions",
    ".github/workflows/tool-updates.yml",
)
# The community files this repository gives every other one. A repository
# keeps its own copy only for a need of its own, so a copy equal to the
# default is drift.
DEFAULTS = (
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
)
FORMS = ".github/ISSUE_TEMPLATE/"
# The merge queue every repository's default branch goes through. GitHub refuses
# a `merge_queue` rule in an organization ruleset (HTTP 422), so each repository
# carries this ruleset of its own.
MERGE_QUEUE = Path(__file__).resolve().parent.parent / "org/repository-rulesets/merge-queue.json"


def problems_of(repo, stack, workspace):
    """What keeps `repo` off the standard, one sentence each."""
    problems = []
    if stack is None:
        problems.append("It has no `stack` property: set `rust`, `other` or `workflows`.")
    if stack in {"rust", "other"}:
        checkout = clone(repo, Path(workspace) / repo)
        page = subprocess.run(
            [sys.executable, str(PAGE_SCRIPT), "--check", "--root", str(checkout)],
            capture_output=True, text=True,
        )
        if page.returncode != 0:
            problems.append(
                f"Its organization page does not say what its sources say "
                f"({page.stderr.strip()}): fix the source it names, or run "
                f"`python3 scripts/org-page.py` and commit the page."
            )
    return problems


def files_of(repo):
    """Every file on `repo`'s default branch."""
    tree = gh_json("api", f"repos/{ORG}/{repo}/git/trees/HEAD?recursive=1")
    return {entry["path"] for entry in tree["tree"] if entry["type"] == "blob"}


def text_of(repo, path):
    """A file of `repo`'s default branch."""
    return run([
        "gh", "api", "-H", "Accept: application/vnd.github.raw",
        f"repos/{ORG}/{repo}/contents/{path}",
    ])


def own_copy(paths, default):
    """Where a repository keeps its own copy of a default, or None. GitHub reads
    issue forms only from .github/ISSUE_TEMPLATE/, other community files from
    the root, .github/ or docs/."""
    places = [default]
    if not default.startswith(FORMS):
        places += [f".github/{default}", f"docs/{default}"]
    by_lower = {path.lower(): path for path in paths}
    return next((by_lower[p.lower()] for p in places if p.lower() in by_lower), None)


def form_labels(repo, paths):
    """The labels the issue forms among `paths` apply."""
    labels = set()
    for path in sorted(paths):
        if not path.startswith(FORMS) or not path.endswith((".yml", ".yaml")):
            continue
        if path.endswith("/config.yml"):
            continue
        text = text_of(repo, path)
        for inline in re.findall(r"^labels:\s*\[(.*)\]", text, re.M):
            labels.update(name.strip(" '\"") for name in inline.split(",") if name.strip())
        for block in re.findall(r"^labels:\s*\n((?:[ \t]+-[^\n]*\n?)+)", text, re.M):
            labels.update(name.strip(" '\"") for name in re.findall(r"-\s*([^\n]+)", block))
    return labels


def defaults_of():
    """This repository's files, the text of each default and its forms' labels."""
    paths = files_of(HOME)
    texts = {}
    for default in DEFAULTS:
        copy = own_copy(paths, default)
        texts[default] = text_of(HOME, copy) if copy else None
    return {"paths": paths, "texts": texts, "labels": form_labels(HOME, paths)}


def baseline_problems(repo, home):
    """What keeps `repo` off the file baseline, one sentence each."""
    paths = home["paths"] if repo == HOME else files_of(repo)
    problems = []
    missing = [name for name in OWN_FILES if name not in paths]
    if missing:
        names = ", ".join(f"`{name}`" for name in missing)
        problems.append(f"It misses {names}, which every repository keeps of its own.")
    # A merged pull request's branch is history the squash commit already holds;
    # kept, it piles up. GitHub has no organization default, so each repository
    # is checked. Only an explicit `false` counts: a token that cannot read the
    # setting reports nothing rather than a false alarm.
    if gh_json("api", f"repos/{ORG}/{repo}").get("delete_branch_on_merge") is False:
        problems.append(
            "It keeps a pull request's branch after the merge: turn on "
            "\"Automatically delete head branches\" (`delete_branch_on_merge`)."
        )
    pins = [name for name in TOOL_PINS if name in paths]
    if pins and repo != WORKFLOWS:
        names = ", ".join(f"`{name}`" for name in pins)
        problems.append(
            f"It pins tools of its own in {names}: delete them; "
            f"the shared CI owns its toolchain."
        )
    for default in DEFAULTS:
        copy = own_copy(paths, default)
        if repo == HOME:
            if copy is None:
                problems.append(f"The default `{default}` is missing: no repository has one.")
        elif copy and text_of(repo, copy) == home["texts"][default]:
            problems.append(
                f"Its `{copy}` repeats the default: delete it, or keep it for a need "
                f"of its own."
            )
    own_forms = any(p.startswith(FORMS) and not p.endswith("/config.yml") for p in paths)
    wanted = form_labels(repo, paths) if own_forms and repo != HOME else home["labels"]
    existing = {label["name"] for label in gh_json(
        "label", "list", "-R", f"{ORG}/{repo}", "--limit", "500", "--json", "name",
    )}
    absent = sorted(wanted - existing)
    if absent:
        names = ", ".join(f"`{name}`" for name in absent)
        problems.append(f"Its issue forms apply {names}, which it lacks as labels: "
                        f"GitHub skips them.")
    return problems


def merge_queue_problems(repo, standard):
    """What keeps `repo`'s merge queue off `standard`, the ruleset in
    `org/repository-rulesets/`, one sentence at most. Its id and timestamps
    are the repository's own; its conditions and rules are compared."""
    name = standard["name"]
    source = f"org/repository-rulesets/{name}.json"
    rulesets = f"repos/{ORG}/{repo}/rulesets"
    found = [ruleset for ruleset in gh_json("api", rulesets) if ruleset["name"] == name]
    if not found:
        return [f"It has no `{name}` ruleset: create it from `{HOME}` with "
                f"`gh api -X POST {rulesets} --input {source}`."]
    live = gh_json("api", f"{rulesets}/{found[0]['id']}")
    restore = (f"restore it from `{HOME}` with "
               f"`gh api -X PUT {rulesets}/{live['id']} --input {source}`")
    if live.get("enforcement") != "active":
        return [f"Its `{name}` ruleset is {live.get('enforcement')}, not active: {restore}."]
    if any(live.get(field) != standard[field] for field in ("conditions", "rules")):
        return [f"Its `{name}` ruleset differs from the organization's: {restore}."]
    return []


def metadata_problems(repo):
    """What keeps `repo`'s name, description and topics off the organization's
    naming, one sentence each: every repository but .github is named
    `maestro-` then lowercase kebab-case, says what it is and has a topic."""
    meta = gh_json("api", f"repos/{ORG}/{repo}")
    problems = []
    if repo != ".github" and not re.fullmatch(r"maestro(-[a-z0-9]+)+", repo):
        problems.append(
            "Its name is not `maestro-` then lowercase kebab-case: rename it, and move "
            "every GitHub Actions `uses:` that names it, since Actions follows no redirect."
        )
    if not (meta.get("description") or "").strip():
        problems.append("It has no description: the organization page shows it.")
    if not meta.get("topics"):
        problems.append("It has no topic: add at least one that classifies it.")
    return problems


def report(repo, problems, dry_run):
    """Open, update or close the repository's drift issue."""
    title = f"Drift: {repo}"
    found = [
        issue for issue in gh_json(
            "issue", "list", "-R", f"{ORG}/{HOME}", "--state", "open",
            "--search", f'in:title "{title}"', "--json", "number,title",
        )
        if issue["title"] == title
    ]
    if dry_run:
        return
    if not problems:
        for issue in found:
            run(["gh", "issue", "close", str(issue["number"]), "-R", f"{ORG}/{HOME}",
                 "--comment", "Back on the standard."])
        return
    body = "\n".join(f"- {problem}" for problem in problems)
    if found:
        run(["gh", "issue", "edit", str(found[0]["number"]), "-R", f"{ORG}/{HOME}", "--body", body])
    else:
        run(["gh", "issue", "create", "-R", f"{ORG}/{HOME}", "--title", title, "--body", body])


def main():
    dry_run = "--dry-run" in sys.argv[1:]
    home = defaults_of()
    merge_queue = json.loads(MERGE_QUEUE.read_text(encoding="utf-8"))
    drifting = []
    with tempfile.TemporaryDirectory() as workspace:
        for repo, stack in repositories():
            problems = problems_of(repo, stack, workspace)
            problems += baseline_problems(repo, home)
            problems += merge_queue_problems(repo, merge_queue)
            problems += metadata_problems(repo)
            report(repo, problems, dry_run)
            state = "on the standard" if not problems else " ".join(problems)
            print(f"{repo}: {state}")
            if problems:
                drifting.append(repo)
    if drifting:
        sys.exit(f"drift in {', '.join(drifting)}; each has an issue titled Drift: <name>")


if __name__ == "__main__":
    main()
