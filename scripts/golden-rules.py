#!/usr/bin/env python3
"""Write a repository's rule map: docs/standards/{northstar,engineering,security}.md.

The organization's golden rules live in this repository's golden-rules/. Every
repository adapts them to what it is for (C-001): its engineering and security
pages say, for every rule, what holds it there or why it does not apply, and its
Northstar page states its point and one KPI per pillar. This script writes the
pages' structure from the golden rules and keeps every cell, paragraph and KPI
a repository wrote. A rule the organization holds gets its default; any other
rule arrives as "Not mapped yet".

Run it from a repository's root; in this workspace:

    python3 ../.github/scripts/golden-rules.py [--check]

`--check` writes nothing and exits 1 when a page differs from what this script
renders or still says "Not mapped yet". Standard library only.
"""

import argparse
import re
import subprocess
import sys
import textwrap
from pathlib import Path

RULES = Path(__file__).resolve().parent.parent / "golden-rules"
PAGES = Path("docs/standards")
SOURCE = "https://github.com/Orchestration-Maestro/.github/blob/main/golden-rules"
UNMAPPED = "Not mapped yet"
WIDTH = 80
PRINCIPLE = "Review: a reviewer names the principle a change breaks"

# What holds a rule in every repository, because the organization holds it.
HELD_BY_ORGANIZATION = {
    "FND-001": "Review: the pull request states its assumptions, the alternatives weighed "
               "and what stays unclear",
    "FND-002": "Review: the pull request names the requirement each change serves; nothing "
               "speculative lands",
    "FND-003": "Review: every changed line traces to the pull request's goal",
    "FND-004": "Review: the pull request's Verification section holds the check that means "
               "done, and its output",
    **{f"P-{n:03}": PRINCIPLE for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 17)},
    "ENF-003": "Review: prose and identifiers are English",
    "ENF-004": "Organization: the `commits-are-conventional` ruleset refuses any other title "
               "on the default branch",
    "ENF-006": "Organization: required checks and code scanning block every merge; a gate "
               "changes only in its own reviewed pull request",
    "ENF-007": "Organization: the `default-branch-discipline` ruleset (pull request, signed "
               "commits, code scanning) and `floor-no-destruction`, with no bypass actor",
    "ENF-010": "Organization: its settings as code in `.github/org/`, checked weekly by "
               "`org-drift.yml`",
    "ENF-011": "Organization: authority lives in rulesets, workflow `permissions:` and access "
               "control; no instruction file grants any",
    "ENF-013": "Organization: secret scanning with push protection and validity checks "
               "(`maestrolabs-baseline`); CI: gitleaks",
    "ENF-014": "Organization: two-factor authentication is required of every member and "
               "outside collaborator",
    "C-001": "These pages, kept current by `scripts/golden-rules.py`; the drift check fails "
             "on a rule not mapped yet",
    "C-004": "Organization: the daily drift check opens a `Drift:` issue for this repository",
    "C-005": "GitHub: pull requests, CI runs with their reports, and drift issues",
    "C-006": "Review: an exception is recorded in the pull request that makes it, with its "
             "scope, rationale and expiry",
    "SEC-004": "Organization: rulesets, workflow permissions and the organization bot's own "
               "App identity; automation borrows no person's credentials",
    "SEC-005": "Review: a publication, release or settings change is approved in its own "
               "pull request",
    "SEC-007": "Review: a suspected exposure stops the work and goes to SECURITY.md's private "
               "channel; a leaked secret is revoked and rotated",
    "SEC-008": "Review: results are reported as run, with what was not checked",
    "SEC-009": "Review: blocked work is reported as partial, never as done",
    "SEC-010": "Organization: private vulnerability reporting is on (`maestrolabs-baseline`), "
               "and SECURITY.md routes reports to it",
}
POINT = (f"{UNMAPPED}: whose problem this repository solves, and what changes for them "
         "when it works.")
PROTECTS = (f"{UNMAPPED}: what this repository holds or runs that an attacker would want, "
            "and where untrusted input enters it.")


def rules_of(page):
    """The rule IDs and titles of a golden-rules page, in document order."""
    text = (RULES / page).read_text(encoding="utf-8")
    found = re.findall(r"^### ([A-Z]+-\d{3}) — (.+)$|^\| (P-\d{3}) \| ([^|]+?) \|", text, re.M)
    return [(heading or row, (title or name).strip()) for heading, title, row, name in found]


def found_in(pattern, text, what, flags=re.M):
    """The first group `pattern` matches, or a stop naming what the page lacks."""
    match = re.search(pattern, text, flags)
    if match is None:
        sys.exit(f"golden-rules/northstar.md has no {what}: update scripts/golden-rules.py")
    return match.group(1)


def pillars():
    """The Northstar's pillars, from its "Four pillars" table."""
    text = (RULES / "northstar.md").read_text(encoding="utf-8")
    table = found_in(r"^## Four pillars\n(.*?)(?=^## )", text, "Four pillars table",
                     re.M | re.S)
    rows = re.findall(r"^\| ([A-Z][a-z]+) \|", table, re.M)
    return [row for row in rows if row != "Pillar"]


def motto():
    """The Northstar's opening quotation."""
    text = (RULES / "northstar.md").read_text(encoding="utf-8")
    return found_in(r"^((?:> .*\n)+)", text, "opening quotation").rstrip("\n")


def repository(root):
    """The repository's name, from its origin remote, else its directory."""
    remote = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                            capture_output=True, text=True).stdout.strip()
    name = remote.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
    return name or root.resolve().name


def section(text, title):
    """The body of a `## title` section, without its heading, or None."""
    found = re.search(rf"^## {re.escape(title)}\n\n(.*?)\n*(?=^## |\Z)", text, re.M | re.S)
    return found.group(1).strip() if found else None


def cells(text):
    """What each rule's row says, by rule ID."""
    return {rule: cell.strip() for rule, cell in
            re.findall(r"^\| ([A-Z]+-\d{3}) [^|]*\| (.+?) \|$", text, re.M)}


def kpis(text):
    """Each pillar's KPI, current value, target and measurement, by pillar."""
    return {row[0]: [cell.strip() for cell in row[1:]] for row in
            re.findall(r"^\| ([A-Z][a-z]+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", text, re.M)
            if row[0] != "Pillar"}


def prose(text):
    """A paragraph wrapped at WIDTH columns."""
    return textwrap.fill(text, WIDTH, break_on_hyphens=False, break_long_words=False)


def intro(name, page, title):
    """The paragraphs every rule map opens with."""
    return [
        prose(f"`{name}` follows the organization's [{title}]({SOURCE}/{page}). This page "
              "is its rule map (C-001): for every rule, what holds it here, or why it does "
              "not apply. A row may name a stricter local rule; none weakens one."),
        "",
        prose("The organization's `scripts/golden-rules.py` writes the rows from the golden "
              f"rules and keeps what each row says here. A rule added there arrives as "
              f"\"{UNMAPPED}\", and the drift check fails until it is mapped."),
    ]


def rule_map(page, previous):
    """The map's table: every rule of `page`, with what holds it here."""
    kept = cells(previous)
    lines = ["| Rule | Held here by |", "| --- | --- |"]
    for rule, title in rules_of(page):
        held = kept.get(rule) or HELD_BY_ORGANIZATION.get(rule) or UNMAPPED
        lines.append(f"| {rule} {title} | {held} |")
    return lines


def engineering(name, previous):
    """docs/standards/engineering.md."""
    stricter = section(previous, "Stricter here")
    return [
        f"# Engineering rules in `{name}`", "",
        *intro(name, "engineering.md", "engineering rules"), "",
        *(["## Stricter here", "", stricter, ""] if stricter else []),
        "## Rule map", "",
        *rule_map("engineering.md", previous), "",
    ]


def security(name, previous):
    """docs/standards/security.md."""
    return [
        f"# Security rules in `{name}`", "",
        *intro(name, "security.md", "security rules"), "",
        "## What this repository protects", "",
        section(previous, "What this repository protects") or prose(PROTECTS), "",
        "## Rule map", "",
        *rule_map("security.md", previous), "",
    ]


def northstar(name, previous):
    """docs/standards/northstar.md."""
    kept = kpis(previous)
    rows = ["| Pillar | KPI | Current | Target | Measured by |",
            "| --- | --- | --- | --- | --- |"]
    for pillar in pillars():
        kpi, current, target, measured = kept.get(
            pillar, [UNMAPPED, "not measured", "set from the first baseline", "none yet"])
        rows.append(f"| {pillar} | {kpi} | {current} | {target} | {measured} |")
    return [
        f"# Northstar for `{name}`", "",
        motto(), "",
        prose(f"`{name}` steers by the organization's [Northstar]({SOURCE}/northstar.md): "
              "one KPI per pillar, each with its measurement. Unmeasured is written `not "
              "measured`, never estimated; a value read by hand carries the date it was "
              "read."),
        "",
        "## The point", "",
        section(previous, "The point") or prose(POINT), "",
        "## KPIs", "",
        *rows, "",
    ]


def render(root):
    """Each page's path and the text this script writes for it."""
    name = repository(root)
    pages = {}
    for page, build in (("northstar.md", northstar), ("engineering.md", engineering),
                        ("security.md", security)):
        path = root / PAGES / page
        previous = path.read_text(encoding="utf-8") if path.is_file() else ""
        pages[path] = "\n".join(build(name, previous))
    return pages


def main():
    parser = argparse.ArgumentParser(description="Write a repository's rule map.")
    parser.add_argument("--check", action="store_true",
                        help="write nothing; exit 1 when a page is stale or not mapped yet")
    parser.add_argument("--root", default=".", help="the repository's root (default: .)")
    arguments = parser.parse_args()
    root = Path(arguments.root)
    pages = render(root)
    unmapped = sum(text.count(UNMAPPED) for text in pages.values())
    if arguments.check:
        stale = [str(path.relative_to(root)) for path, text in pages.items()
                 if not path.is_file() or path.read_text(encoding="utf-8") != text]
        if stale or unmapped:
            sys.exit(f"rule map: stale {', '.join(stale) or 'none'}; "
                     f"{unmapped} entries not mapped yet")
        print("rule map is current and complete")
        return
    for path, text in pages.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"wrote {PAGES}/: {unmapped} entries not mapped yet")


if __name__ == "__main__":
    main()
