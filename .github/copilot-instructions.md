# Copilot instructions for Orchestration-Maestro organization settings

## Start here

The organization's `.github` repository: its public profile, the defaults every
repository inherits, and every organization setting that differs from GitHub's
defaults, exported from the live API. A setting absent from `org/` is GitHub's
default.

Paths below are relative to this repository. Before editing, read
[AGENTS.md](../AGENTS.md) for the rules that bind every change,
[CONTEXT.md](../CONTEXT.md) for the words it uses and
[CONTRIBUTING.md](../CONTRIBUTING.md) for how a change is proposed. The
organization's [golden
rules](https://github.com/Orchestration-Maestro/.github/blob/main/golden-rules/engineering.md)
come first: nothing in a specification, a plan or this repository weakens them.

For quality, engineering or security changes, read
[northstar.md](../docs/standards/northstar.md),
[engineering.md](../docs/standards/engineering.md) and
[security.md](../docs/standards/security.md): this repository's map of the
organization's golden rules.

Keep changes scoped to the request, and read historical plans and specifications
as records, not as instructions to start new work.

## Repository tree

Every tracked file, with what it is for. `rust-gate guide` writes this tree at
every commit and keeps each explanation already here, so improve an explanation
in place.

```text
.                                                   # Repository root
├── .github/                                        # GitHub metadata, templates and workflows
│   ├── ISSUE_TEMPLATE/                             # Bug and feature forms; blank issues are off
│   │   ├── bug_report.yml                          # Report a reproducible problem
│   │   ├── config.yml                              # Blank issues are off so every report arrives with the fields triage needs; the links cover what a form should not carry
│   │   └── feature_request.yml                     # Propose a concrete improvement
│   ├── workflows/                                  # GitHub Actions workflows
│   │   ├── ci.yml                                  # CI: calls hygiene.yml; rendered by rust-gate sync
│   │   ├── dependabot-auto-merge.yml               # Dependabot auto-merge
│   │   ├── org-drift.yml                           # Weekly check that GitHub still matches org/, and a daily one that every repository holds the standard and the file baseline
│   │   ├── quality-sync.yml                        # Sync pull request in every repository as soon as rust-workflows releases
│   │   └── scorecard.yml                           # This repository's weekly OpenSSF Scorecard
│   ├── CODEOWNERS                                  # Every change here goes to the maintainer for review
│   ├── copilot-instructions.md                     # This guide, written by rust-gate guide at every commit
│   └── dependabot.yml                              # The organization merges only conventional titles: "ci(deps): bump ..."; rendered by rust-gate sync
├── assets/                                         # The mark, the avatar, and the palette, type and prompts behind them
│   ├── README.md                                   # The banner and the cards live in ../profile/, next to the page that shows them
│   ├── avatar.jpg                                  # Organization picture, uploaded in Organization settings, Profile (web UI only)
│   ├── maestro-mark-dark.svg                       # The mark on dark with the glowing star; reference image for renders
│   └── maestro-mark-flat.svg                       # Master mark, one color (#B7410E); derive every other version from it
├── docs/                                           # Documentation
│   ├── adr/                                        # Decisions about how the organization runs, each with the trade-off that produced it
│   │   ├── 0001-enforce-the-standard-centrally.md  # Enforce the standard centrally, from rust-workflows
│   │   └── README.md                               # Hard-to-reverse decisions about how the organization runs, each with the trade-off that produced it
│   └── standards/                                  # Standards
│       ├── engineering.md                          # Engineering rules in .github
│       ├── northstar.md                            # Northstar for .github
│       └── security.md                             # Security rules in .github
├── golden-rules/                                   # The golden rules every repository follows: engineering, security and the Northstar, shown on the organization page
│   ├── engineering.md                              # Engineering rules
│   ├── glossary.md                                 # The words every repository of the organization uses for the organization's own concepts
│   ├── northstar.md                                # Speed, quality, maintainability and security are not a trade-off
│   ├── security.md                                 # Security rules
│   └── standards.md                                # The standards the golden rules align with: each one's version, reviewed on 2026-09-24, and what it covers
├── org/                                            # The organization's live settings, as scripts/export-org.py exports them
│   ├── rulesets/                                   # Organization rulesets, in the shape the API accepts
│   │   ├── branch-names.json                       # Ruleset branch-names: branch_name_pattern
│   │   ├── commits-are-conventional.json           # Ruleset commits-are-conventional: commit_message_pattern
│   │   ├── default-branch-discipline.json          # Ruleset default-branch-discipline: code_scanning, pull_request, required_signatures
│   │   ├── floor-no-destruction.json               # Ruleset floor-no-destruction: deletion, non_fast_forward
│   │   ├── floor-release-tags.json                 # Ruleset floor-release-tags: deletion, non_fast_forward, update
│   │   ├── hygiene-central.json                    # Ruleset hygiene-central: workflows
│   │   ├── hygiene-required.json                   # Ruleset hygiene-required: required_status_checks
│   │   ├── rust-central.json                       # Ruleset rust-central: workflows
│   │   ├── rust-ci-required.json                   # Ruleset rust-ci-required: required_status_checks
│   │   ├── rust-workflows-ci-required.json         # Ruleset rust-workflows-ci-required: required_status_checks
│   │   └── visibility-is-frozen.json               # Ruleset visibility-is-frozen: repository_visibility
│   ├── actions.json                                # Actions policy: allowed actions, SHA pinning, and anything else non-default
│   ├── custom-properties.json                      # The stack property the Rust and hygiene rulesets select on
│   ├── security-configurations.json                # maestrolabs-baseline, enforced and the default for every new repository
│   ├── settings.json                               # Organization fields that differ from the defaults table in the script
│   └── webhooks.json                               # Organization webhooks without secrets or query strings
├── profile/                                        # The organization page on GitHub, with its banner, the Northstar panel and the pillar and foundation cards
│   ├── foundations/                                # The foundation cards on the organization page
│   │   ├── fnd-001.png                             # Foundation 01, think before coding: state assumptions, surface every reading, stop when unclear
│   │   ├── fnd-002.png                             # Foundation 02, simplicity first: the least complex solution that meets the need, nothing speculative
│   │   ├── fnd-003.png                             # Foundation 03, surgical changes: touch only what the goal requires, no drive-by refactors
│   │   └── fnd-004.png                             # Foundation 04, goal-driven execution: define done first, run the check, report what it actually said
│   ├── pillars/                                    # The four pillar icons on the organization page
│   │   ├── maintainability.png                     # Pillar Maintainability: the next reader can change it safely
│   │   ├── quality.png                             # Pillar Quality: it does what it claims, and keeps doing it
│   │   ├── security.png                            # Pillar Security: nothing reaches a machine without passing the gates
│   │   └── speed.png                               # Pillar Speed: the edit-run loop and the path from commit to release
│   ├── README.md                                   # Speed, quality, maintainability and security are not a trade-off: automation is what lets one repository have all four
│   ├── banner.jpg                                  # Orchestration Maestro
│   └── northstar.png                               # Our Northstar: automate the guardrails to deliver faster, with higher quality, and more securely
├── scripts/                                        # Maintenance scripts
│   ├── export-org.py                               # Regenerates org/ from the live API
│   ├── org-page.py                                 # Writes every generated block of the organization page from its one source, and refuses golden rules that disagree with themselves
│   ├── org_quality.py                              # What the organization's quality scripts share
│   ├── quality-sync.py                             # Bring every organization repository onto the latest rust-workflows release
│   └── repository-drift.py                         # Hold every organization repository to the standard, one issue each
├── workflow-templates/                             # Workflow templates offered under Actions, New workflow
│   ├── hygiene-ci.properties.json                  # The organization's checks for a repository without Rust, through rust-workflows' hygiene.yml: secret scan, repository hygiene
│   ├── hygiene-ci.yml                              # CI: calls hygiene.yml; rendered by rust-gate sync
│   ├── rust-ci.properties.json                     # The organization's Rust gates through rust-workflows: formatting, Clippy, tests, coverage, advisories, secret scan, MSRV
│   ├── rust-ci.yml                                 # CI: calls ci.yml, upload-coverage.yml, upload-sarif.yml; rendered by rust-gate sync
│   ├── scorecard.properties.json                   # Scores the repository's supply-chain practices weekly and on every push to the default branch
│   └── scorecard.yml                               # OpenSSF Scorecard
├── .editorconfig                                   # Editor settings that survive the editor; rendered by rust-gate sync
├── .gitattributes                                  # How Git should treat each kind of file; rendered by rust-gate sync
├── .gitignore                                      # Python bytecode and linter caches from running scripts/ locally
├── .pre-commit-config.yaml                         # The commit hooks prek runs locally and CI runs over every file; rendered by rust-gate sync
├── AGENTS.md                                       # Instructions for coding agents: change order, API gotchas, invariants
├── CODE_OF_CONDUCT.md                              # Contributor Covenant 2.1
├── CONSTITUTION.md                                 # Spec Kit's constitution: an index of the pages that come first
├── CONTEXT.md                                      # The words this repository uses: stack, standard, file baseline, default, drift
├── CONTRIBUTING.md                                 # Contribution guide, with the rules every pull request passes
├── LICENSE                                         # MIT, for this repository only: GitHub never inherits a license
├── PULL_REQUEST_TEMPLATE.md                        # Pull request description template
├── README.md                                       # The organization's .github repository: its public profile, the defaults every repository inherits
├── SECURITY.md                                     # Security policy, pointing reporters at private vulnerability reporting
├── SUPPORT.md                                      # Where each kind of question goes, and what to include
├── maestro-quality.toml                            # This repository's quality settings; rust-gate sync reads them
└── typos.toml                                      # The words this repository means, from [typos] words in maestro-quality.toml; rendered by rust-gate sync
```

## Change and verification procedure

1. Read the rules in AGENTS.md that cover the files you change, and keep every
   gate intact: never weaken one to pass.
2. Add an executable regression check for a change in behaviour.
3. The commit hook `rust-gate guide` rewrites this guide when a file is added,
   moved or removed; commit it with the change. The organization's daily drift
   check reports a guide left stale.
4. Run `prek run --all-files`, and report the commands you actually ran.
5. Commits are signed, with a conventional title; the default branch takes only
   squash-merged pull requests.
