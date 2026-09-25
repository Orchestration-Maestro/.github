#!/usr/bin/env python3
"""Hold every organization repository to the standard, one issue each.

A repository drifts when it has no `stack`, when its `maestro/sync` pull
request has waited more than 14 days, when `rust-gate sync --check` at the
latest rust-workflows release finds a managed file that differs on its default
branch, or when it strays from the file baseline: a file every repository
keeps of its own is missing, a copy repeats one of this repository's
defaults, or an issue form applies a label the repository lacks. Each
drifting repository has one open issue here, "Drift: <name>", updated on
every run and closed once the repository is back on the standard. Exits 1
when any repository drifts. `--dry-run` reports and writes nothing. Needs
GH_TOKEN (the organization bot's) and cargo. Standard library only.
"""

import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from org_quality import (
    ORG,
    SYNCED,
    clone,
    gh_json,
    install_gate,
    latest_release,
    repositories,
    run,
    sync_pull_request,
    with_gate,
)

HOME = ".github"
OLDEST_DAYS = 14

# The file baseline, as rust-workflows holds it. Every repository keeps these
# files of its own: GitHub never inherits them and `rust-gate sync` does not
# write them.
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
# The Copilot guide and the rule map, the golden rules adapted to a repository:
# `rust-gate guide --check` and `rust-gate rules --check` at the latest release
# compare them. rust-workflows keeps its own guide and standards pages.
GUIDE = ".github/copilot-instructions.md"
# A file a repository needs only beside another: tools pinned by mise move
# through the weekly tool updates.
NEEDED_WITH = {".github/workflows/tool-updates.yml": "mise.toml"}
# The community files this repository gives every other one. A repository
# keeps its own copy only for a need of its own, so a copy equal to the
# default is drift.
DEFAULTS = (
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
)
FORMS = ".github/ISSUE_TEMPLATE/"


def problems_of(repo, stack, gate_bin, workspace):
    """What keeps `repo` off the standard, one sentence each."""
    problems = []
    if stack is None:
        problems.append("It has no `stack` property: set `rust`, `other` or `workflows`.")
    pending = sync_pull_request(repo)
    if pending:
        opened = datetime.fromisoformat(pending["createdAt"].replace("Z", "+00:00"))
        days = (datetime.now(timezone.utc) - opened).days
        if days > OLDEST_DAYS:
            problems.append(
                f"Its sync pull request {pending['url']} has waited {days} days; "
                f"merge it or fix what it breaks."
            )
    if stack in SYNCED:
        checkout = clone(repo, Path(workspace) / repo)
        check = subprocess.run(
            ["rust-gate", "sync", "--check"], cwd=checkout,
            env=with_gate(gate_bin), capture_output=True, text=True,
        )
        if check.returncode != 0:
            problems.append(f"Its default branch drifts: {check.stderr.strip()}")
        if (checkout / GUIDE).is_file():
            guide = subprocess.run(
                ["rust-gate", "guide", "--check"], cwd=checkout,
                env=with_gate(gate_bin), capture_output=True, text=True,
            )
            if guide.returncode != 0:
                problems.append(
                    f"Its `{GUIDE}` is stale: run `rust-gate guide` at its root and "
                    f"commit the guide."
                )
        page = subprocess.run(
            [sys.executable, str(PAGE_SCRIPT), "--check", "--root", str(checkout)],
            env=with_gate(gate_bin), capture_output=True, text=True,
        )
        if page.returncode != 0:
            problems.append(
                f"Its organization page does not say what its sources say "
                f"({page.stderr.strip()}): fix the source it names, or run "
                f"`python3 scripts/org-page.py` with the latest release's `rust-gate` "
                f"and commit the page."
            )
        if (checkout / "docs/standards").is_dir():
            rules = subprocess.run(
                ["rust-gate", "rules", "--check"], cwd=checkout,
                env=with_gate(gate_bin), capture_output=True, text=True,
            )
            if rules.returncode != 0:
                found = rules.stderr.strip().removeprefix("rules --check: ")
                problems.append(
                    f"Its rule map in `docs/standards/` is stale or incomplete "
                    f"({found.split('; run ', 1)[0]}): run `rust-gate rules` at its root, "
                    f"map every entry still \"Not mapped yet\", and commit the pages."
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
    for name, beside in NEEDED_WITH.items():
        if beside in paths and name not in paths:
            problems.append(f"It has `{beside}` but not `{name}`, which keeps it current.")
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
    tag, _ = latest_release()
    home = defaults_of()
    drifting = []
    with tempfile.TemporaryDirectory() as workspace:
        gate_bin = install_gate(tag, Path(workspace) / "gate")
        for repo, stack in repositories():
            problems = problems_of(repo, stack, gate_bin, workspace)
            problems += baseline_problems(repo, home)
            report(repo, problems, dry_run)
            state = "on the standard" if not problems else " ".join(problems)
            print(f"{repo}: {state}")
            if problems:
                drifting.append(repo)
    if drifting:
        sys.exit(f"drift in {', '.join(drifting)}; each has an issue titled Drift: <name>")


if __name__ == "__main__":
    main()
