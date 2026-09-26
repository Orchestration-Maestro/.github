#!/usr/bin/env python3
"""Bring every organization repository onto the latest maestro-rust-workflows release.

For each repository whose `stack` is `rust` or `other`, clone it, run
`rust-gate sync` at the release, then `rust-gate rules` for its rule map, the
organization page's generated blocks from their sources, and `rust-gate guide`
for its Copilot guide: the same release writes them as the repository's own
commit hooks do, so the two never disagree. When a file changed, open or update the pull request from
`maestro/sync`: one commit through GitHub's createCommitOnBranch, which GitHub
signs. A minor or patch release merges itself once green; a major one waits
for a person. maestro-rust-workflows gets the golden-rules pages rust-gate embeds, and
its own rule map rewritten from them, as a `fix:` pull request that merges
itself once green. `--dry-run` reports what
would change and writes nothing. Needs GH_TOKEN (the organization bot's) and
cargo. Standard library only.
"""

import re
import sys
import tempfile
from pathlib import Path

from org_quality import (
    ORG,
    SYNC_BRANCH,
    SYNCED,
    WORKFLOWS,
    clone,
    install_gate,
    latest_release,
    open_pull_request,
    publish,
    repositories,
    run,
    with_gate,
)

# Where maestro-rust-workflows keeps the golden-rules pages rust-gate embeds.
CARRIED = "gate/golden-rules"
RULES_URL = f"https://github.com/{ORG}/.github/blob/main/golden-rules"
# The organization's own writers, beside this script.
SCRIPTS = Path(__file__).resolve().parent


def pinned_version(checkout):
    """The maestro-rust-workflows version the repository's commit hooks install, or None."""
    hooks = Path(checkout) / ".pre-commit-config.yaml"
    if not hooks.is_file():
        return None
    # Either name: maestro-rust-workflows becomes maestro-rust-workflows at a cutover.
    found = re.search(r"/(?:maestro-)?rust-workflows:v(\d+\.\d+\.\d+):rust-gate",
                      hooks.read_text())
    return found.group(1) if found else None


def changed_files(checkout):
    """Every file `rust-gate sync` wrote that differs from the default branch."""
    status = run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=checkout)
    return sorted(line[3:] for line in status.splitlines())


def sync_one(repo, pin, version, gate_bin, workspace, dry_run):
    """Sync one repository; report what changed."""
    checkout = clone(repo, Path(workspace) / repo)
    before = pinned_version(checkout)
    run(["rust-gate", "sync"], cwd=checkout, env=with_gate(gate_bin, RUST_WORKFLOWS_PIN=pin))
    # The rule map follows the golden rules this release carries.
    run(["rust-gate", "rules"], cwd=checkout, env=with_gate(gate_bin))
    # The organization page lists the gate's rules as this release holds them.
    # The organization page shows each source as it stands, the gate's rules as
    # this release lists them.
    run([sys.executable, str(SCRIPTS / "org-page.py"), "--root", str(checkout)],
        env=with_gate(gate_bin))
    # The guide lists every file, the new ones included once git knows of them.
    run(["git", "add", "--intent-to-add", "."], cwd=checkout)
    run(["rust-gate", "guide"], cwd=checkout, env=with_gate(gate_bin))
    files = changed_files(checkout)
    major = before is not None and before.split(".")[0] != version.split(".")[0]
    if not files:
        existing = open_pull_request(repo, SYNC_BRANCH)
        if existing and not dry_run:
            run(["gh", "pr", "close", str(existing["number"]), "-R", f"{ORG}/{repo}",
                 "--comment", "The default branch already holds these files."])
        print(f"{repo}: on v{version}")
        return
    if dry_run:
        print(f"{repo}: would sync {len(files)} files{' (major)' if major else ''}: {', '.join(files)}")
        return
    note = (
        "A major release: read its notes and merge by hand."
        if major
        else "A minor or patch release: this merges itself once every check passes."
    )
    text = (
        f"`rust-gate sync` at maestro-rust-workflows v{version} rewrote the files every "
        f"organization repository holds as the gate renders them.\n\n{note}\n\n"
        + "\n".join(f"- `{path}`" for path in files)
    )
    title = f"chore: sync the organization's files to maestro-rust-workflows v{version}"
    number = publish(repo, checkout, files, SYNC_BRANCH, title, text, not major)
    print(f"{repo}: pull request #{number}, {len(files)} files{' (major)' if major else ''}")


def carried(page, names):
    """A golden-rules page as maestro-rust-workflows carries it: each link to a page it
    does not carry made absolute, so its relative links all resolve."""
    return re.sub(
        r"\]\(([a-z]+\.md)(#[a-z0-9-]+)?\)",
        lambda link: link.group(0) if link.group(1) in names
        else f"]({RULES_URL}/{link.group(1)}{link.group(2) or ''})",
        page,
    )


def carry_golden_rules(workspace, dry_run):
    """Bring the golden-rules pages rust-gate embeds up to this repository's."""
    source = SCRIPTS.parent / "golden-rules"
    checkout = clone(WORKFLOWS, Path(workspace) / WORKFLOWS)
    target = checkout / CARRIED
    names = sorted(page.name for page in target.glob("*.md"))
    for name in names:
        if not (source / name).is_file():
            raise RuntimeError(f"{CARRIED}/{name} has no page in golden-rules/ to follow")
        (target / name).write_text(carried((source / name).read_text(encoding="utf-8"),
                                           names), encoding="utf-8")
    if not changed_files(checkout):
        existing = open_pull_request(WORKFLOWS, SYNC_BRANCH)
        if existing and not dry_run:
            run(["gh", "pr", "close", str(existing["number"]), "-R", f"{ORG}/{WORKFLOWS}",
                 "--comment", "The default branch already carries these golden rules."])
        print(f"{WORKFLOWS}: carries the golden rules as they stand")
        return
    commit = run(["git", "rev-parse", "HEAD"], cwd=SCRIPTS.parent).strip()
    (target / "commit.txt").write_text(f"{commit}\n", encoding="utf-8")
    # maestro-rust-workflows' own rule map follows the copy it carries, and its required
    # `just check` refuses it stale: the gate built from this very copy rewrites
    # it, so a change of wording merges itself and a new rule waits for a person.
    run(["cargo", "run", "--quiet", "--locked", "--manifest-path", "gate/Cargo.toml",
         "--", "rules"], cwd=checkout)
    files = changed_files(checkout)
    if dry_run:
        print(f"{WORKFLOWS}: would carry the golden rules of .github {commit[:7]}: "
              f"{', '.join(files)}")
        return
    text = (
        f"The golden rules changed in .github at {commit[:7]}; `rust-gate rules` "
        f"embeds them, so a repository's rule map follows them once this is "
        f"released. Each link to a page this copy does not carry points at .github. "
        f"This repository's own rule map is rewritten from the copy; a rule it adds "
        f"arrives as \"Not mapped yet\", and `just check` fails until it is mapped.\n\n"
        + "\n".join(f"- `{path}`" for path in files)
    )
    number = publish(WORKFLOWS, checkout, files, SYNC_BRANCH,
                     f"fix: carry the golden rules of .github {commit[:7]}", text, True)
    print(f"{WORKFLOWS}: pull request #{number}, the golden rules of .github {commit[:7]}")


def main():
    dry_run = "--dry-run" in sys.argv[1:]
    tag, sha = latest_release()
    version = tag.removeprefix("v")
    failed = []
    with tempfile.TemporaryDirectory() as workspace:
        gate_bin = install_gate(tag, Path(workspace) / "gate")
        for repo, stack in repositories():
            if stack not in SYNCED:
                print(f"{repo}: stack {stack}, not synced")
                continue
            try:
                sync_one(repo, f"{sha} v{version}", version, gate_bin, workspace, dry_run)
            except RuntimeError as error:
                print(f"{repo}: {error}", file=sys.stderr)
                failed.append(repo)
        try:
            carry_golden_rules(workspace, dry_run)
        except RuntimeError as error:
            print(f"{WORKFLOWS}: {error}", file=sys.stderr)
            failed.append(f"{WORKFLOWS} (golden rules)")
    if failed:
        sys.exit(f"sync failed for {', '.join(failed)}")


if __name__ == "__main__":
    main()
