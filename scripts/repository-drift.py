#!/usr/bin/env python3
"""Hold every organization repository to the standard, one issue each.

A repository drifts when it has no `stack`, when its `maestro/sync` pull
request has waited more than 14 days, or when `rust-gate sync --check` at the
latest rust-workflows release finds a managed file that differs on its default
branch. Each drifting repository has one open issue here, "Drift: <name>",
updated on every run and closed once the repository is back on the standard.
Exits 1 when any repository drifts. `--dry-run` reports and writes nothing.
Needs GH_TOKEN (the organization bot's) and cargo. Standard library only.
"""

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
    drifting = []
    with tempfile.TemporaryDirectory() as workspace:
        gate_bin = install_gate(tag, Path(workspace) / "gate")
        for repo, stack in repositories():
            problems = problems_of(repo, stack, gate_bin, workspace)
            report(repo, problems, dry_run)
            state = "on the standard" if not problems else " ".join(problems)
            print(f"{repo}: {state}")
            if problems:
                drifting.append(repo)
    if drifting:
        sys.exit(f"drift in {', '.join(drifting)}; each has an issue titled Drift: <name>")


if __name__ == "__main__":
    main()
