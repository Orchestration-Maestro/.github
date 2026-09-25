#!/usr/bin/env python3
"""Move the organization rulesets that run rust-workflows to its latest release.

`rust-central` and `hygiene-central` run a workflow of rust-workflows through a
`workflows` rule, pinned by `sha` to a release's commit with `ref` naming its
tag. This moves every such pin to the latest release, then exports `org/` and
opens or updates the pull request from `ci/pin-the-central-rulesets` that
records it: one commit through GitHub's createCommitOnBranch, which GitHub
signs, queued to merge itself once green. A pin moves only forward, and across
a major release only with `--major`: a person reads its notes first. The export
must differ from the reviewed `org/` by these pins alone; anything else is
drift, reported, and nothing is published. `--dry-run` prints every update and
writes nothing; with it, `--release <tag> <commit>` stands in for the latest
release. Needs GH_TOKEN (the organization bot's) and ORG_ADMIN_TOKEN (the audit
App's: only Administration write reads and writes organization rulesets);
without ORG_ADMIN_TOKEN, `gh`'s own login, which needs the admin:org scope.
Standard library only.
"""

import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

from org_quality import (
    ORG,
    WORKFLOWS,
    gh_json,
    latest_release,
    open_pull_request,
    publish,
    run,
)

HOME = ".github"
BRANCH = "ci/pin-the-central-rulesets"
ROOT = Path(__file__).resolve().parent.parent
# PUT replaces a ruleset whole: every field goes back with the one that moves.
RULESET_FIELDS = ("name", "target", "enforcement", "conditions", "bypass_actors", "rules")


def version(ref):
    """The (major, minor, patch) a `refs/tags/vX.Y.Z` names, or None."""
    found = re.fullmatch(r"refs/tags/v(\d+)\.(\d+)\.(\d+)", ref or "")
    return tuple(int(part) for part in found.groups()) if found else None


def home_workflows(ruleset, home_id):
    """Every workflow `ruleset` runs from rust-workflows."""
    for rule in ruleset.get("rules", []):
        if rule.get("type") == "workflows":
            for workflow in rule["parameters"]["workflows"]:
                if workflow.get("repository_id") == home_id:
                    yield workflow


def repinned(ruleset, home_id, tag, sha):
    """`ruleset` with every workflow it runs from rust-workflows pinned to the
    release, and each move as (path, old ref, old sha)."""
    moved = copy.deepcopy(ruleset)
    moves = []
    ref = f"refs/tags/{tag}"
    for workflow in home_workflows(moved, home_id):
        if (workflow.get("ref"), workflow.get("sha")) != (ref, sha):
            moves.append((workflow["path"], workflow.get("ref"), workflow.get("sha")))
            workflow["ref"], workflow["sha"] = ref, sha
    return moved, moves


def refusal(moves, tag, release, major):
    """Why the ruleset's pins stay where they are, or None. `release` is the
    (major, minor, patch) of `tag`."""
    for _, ref, _ in moves:
        old = version(ref)
        if old is None:
            return f"pinned to {ref}, not a release: a person moves it"
        if release < old:
            return f"pinned to {ref}, ahead of {tag}"
        if release[0] != old[0] and not major:
            return f"{tag} is a major release: a person reads its notes and runs this with --major"
    return None


def pin(admin, home_id, tag, sha, release, major, dry_run):
    """Move every ruleset's pins to the release; the number refused."""
    refused = 0
    for summary in json.loads(run(["gh", "api", f"orgs/{ORG}/rulesets?per_page=100"], env=admin)):
        ruleset = json.loads(run(["gh", "api", f"orgs/{ORG}/rulesets/{summary['id']}"], env=admin))
        moved, moves = repinned(ruleset, home_id, tag, sha)
        name = ruleset["name"]
        if not moves:
            if any(home_workflows(ruleset, home_id)):
                print(f"{name}: on {tag}")
            continue
        reason = refusal(moves, tag, release, major)
        for path, ref, old in moves:
            print(f"{name}: {path} {ref} {old} -> refs/tags/{tag} {sha}"
                  f"{' (refused)' if reason else ''}")
        if reason:
            print(f"{name}: {reason}")
            refused += 1
            continue
        if dry_run:
            print(f"{name}: would PUT orgs/{ORG}/rulesets/{ruleset['id']}")
            continue
        body = {field: moved[field] for field in RULESET_FIELDS if field in moved}
        run(["gh", "api", "-X", "PUT", f"orgs/{ORG}/rulesets/{ruleset['id']}", "--input", "-"],
            env=admin, stdin=json.dumps(body))
        print(f"{name}: moved to {tag}")
    return refused


def recorded(home_id, tag, sha):
    """The `org/` files the export changed, each checked to differ from the
    reviewed state only by its pins to the release."""
    status = run(["git", "status", "--porcelain", "--untracked-files=all", "--", "org/"], cwd=ROOT)
    files = []
    for line in status.splitlines():
        code, path = line[:2], line[3:]
        pins_only = code == " M" and re.fullmatch(r"org/rulesets/[^/]+\.json", path)
        if pins_only:
            reviewed = json.loads(run(["git", "show", f"HEAD:{path}"], cwd=ROOT))
            expected, _ = repinned(reviewed, home_id, tag, sha)
            pins_only = json.loads((ROOT / path).read_text(encoding="utf-8")) == expected
        if not pins_only:
            sys.exit(f"{path}: GitHub differs from org/ by more than the pins: drift, which "
                     f"a person resolves (README.md, Drift checks); nothing was published")
        files.append(path)
    return files


def record(admin, home_id, tag, sha):
    """Export `org/` and publish the pins it records, or close a pull request
    the default branch no longer needs."""
    run([sys.executable, str(ROOT / "scripts/export-org.py")], env=admin)
    files = recorded(home_id, tag, sha)
    if not files:
        existing = open_pull_request(HOME, BRANCH)
        if existing:
            run(["gh", "pr", "close", str(existing["number"]), "-R", f"{ORG}/{HOME}",
                 "--comment", "The default branch already records these pins."])
        print("org/: records every pin")
        return
    text = (
        f"The central rulesets now run rust-workflows {tag}, commit {sha}: this "
        f"records them in `org/`, exported from GitHub. It merges itself once every "
        f"check passes.\n\n" + "\n".join(f"- `{path}`" for path in files)
    )
    title = f"ci: pin the central rulesets to rust-workflows {tag}"
    number = publish(HOME, ROOT, files, BRANCH, title, text, True)
    print(f"org/: pull request #{number}, {len(files)} files")


def main():
    parser = argparse.ArgumentParser(description="Move the central rulesets to a release.")
    parser.add_argument("--dry-run", action="store_true", help="print every update, write nothing")
    parser.add_argument("--major", action="store_true", help="also move across a major release")
    parser.add_argument("--release", nargs=2, metavar=("TAG", "COMMIT"),
                        help="with --dry-run, the release to move to instead of the latest")
    args = parser.parse_args()
    if args.release and not args.dry_run:
        parser.error("--release only goes with --dry-run: a pin moves to a published release")
    tag, sha = args.release or latest_release()
    release = version(f"refs/tags/{tag}")
    if release is None or not re.fullmatch(r"[0-9a-f]{40}", sha):
        sys.exit(f"{tag} {sha} is not a release tag vX.Y.Z and a full commit")
    admin = dict(os.environ)
    if os.environ.get("ORG_ADMIN_TOKEN"):
        admin["GH_TOKEN"] = os.environ["ORG_ADMIN_TOKEN"]
    home_id = gh_json("api", f"repos/{ORG}/{WORKFLOWS}")["id"]
    refused = pin(admin, home_id, tag, sha, release, args.major, args.dry_run)
    if not args.dry_run:
        record(admin, home_id, tag, sha)
    if refused:
        print(f"{refused} ruleset(s) wait for a person", file=sys.stderr)


if __name__ == "__main__":
    main()
