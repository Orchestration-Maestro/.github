# Engineering rules in `.github`

`.github` follows the organization's [engineering
rules](https://github.com/Orchestration-Maestro/.github/blob/main/golden-rules/engineering.md).
This page is its rule map (C-001): for every rule, what holds it here, or why it
does not apply. A row may name a stricter local rule; none weakens one.

The organization's `scripts/golden-rules.py` writes the rows from the golden
rules and keeps what each row says here. A rule added there arrives as "Not
mapped yet", and the drift check fails until it is mapped.

## Rule map

| Rule | Held here by |
| --- | --- |
| FND-001 Think before coding | Review: the pull request states its assumptions, the alternatives weighed and what stays unclear |
| FND-002 Simplicity first | Review: the pull request names the requirement each change serves; nothing speculative lands |
| FND-003 Surgical changes | Review: every changed line traces to the pull request's goal |
| FND-004 Goal-driven execution | Review: the pull request's Verification section holds the check that means done, and its output |
| P-001 YAGNI | Review: a reviewer names the principle a change breaks |
| P-002 KISS | Review: a reviewer names the principle a change breaks |
| P-003 DRY | Review: a reviewer names the principle a change breaks |
| P-004 WET | Review: a reviewer names the principle a change breaks |
| P-005 Rule of three | Review: a reviewer names the principle a change breaks |
| P-006 Chesterton's fence | Review: a reviewer names the principle a change breaks |
| P-007 Boy Scout rule | Review: a reviewer names the principle a change breaks |
| P-008 Least astonishment | Review: a reviewer names the principle a change breaks |
| P-009 Single responsibility | Review: a reviewer names the principle a change breaks |
| P-010 Composition over inheritance | Review: a reviewer names the principle a change breaks |
| P-011 Fail fast | Code: every `gh` call stops the script when it fails (`org_quality.run`); `export-org.py` warns on an organization field it cannot classify |
| P-012 Make illegal states unrepresentable | Review: a reviewer names the principle a change breaks |
| P-013 Parse, don't validate | Code: API answers are parsed as JSON and classified before the export keeps them |
| P-014 Principle of least privilege | CI: each workflow declares its permissions; the audit App's admin key lives only in the `org-audit` environment; bot tokens are minted per run |
| P-015 Separation of concerns | Review: a reviewer names the principle a change breaks |
| P-016 Zero, one or many | Review: a reviewer names the principle a change breaks |
| P-017 Premature optimisation | Review: a reviewer names the principle a change breaks |
| P-018 Broken windows | Gate: the hooks and the hygiene CI refuse lint, format and link findings; a drift issue stays open until fixed |
| ENF-001 No machine-named paths | Review: scripts derive paths from their own location and temporary directories |
| ENF-002 Every claimed platform is tested | Not applicable: no platform is claimed; workflows run on `ubuntu-24.04` |
| ENF-003 English only | Review: prose and identifiers are English |
| ENF-004 Conventional commits | Organization: the `commits-are-conventional` ruleset refuses any other title on the default branch |
| ENF-005 Failing test first | Review: the scripts have no test suite yet; a change is proved by `--dry-run` and the next drift check |
| ENF-006 Never weaken a gate | Organization: required checks and code scanning block every merge; a gate changes only in its own reviewed pull request |
| ENF-007 Pull requests only | Organization: the `default-branch-discipline` ruleset (pull request, signed commits, code scanning) and `floor-no-destruction`, with no bypass actor |
| ENF-008 Tiered checks | Commit hooks (prek) on changed files; the hygiene CI runs them over every file; the drift checks run daily and weekly |
| ENF-009 Allowlists that cannot rot | Review: each inline zizmor suppression names its reason on the same line |
| ENF-010 Configuration is the authority | Organization: its settings as code in `.github/org/`, checked weekly by `org-drift.yml` |
| ENF-011 Instructions grant nothing | Organization: authority lives in rulesets, workflow `permissions:` and access control; no instruction file grants any |
| ENF-012 Pinned inputs | Gate: actions pinned by SHA; the scripts build rust-gate at a release tag with `--locked` and check jaq against its pinned SHA-256 |
| ENF-013 No secret in history | Organization: secret scanning with push protection and validity checks (`maestrolabs-baseline`); CI: gitleaks |
| ENF-014 Multi-factor authentication | Organization: two-factor authentication is required of every member and outside collaborator |
| C-001 Map every rule | These pages, kept current by `scripts/golden-rules.py`; the drift check fails on a rule not mapped yet |
| C-004 Detect drift | Organization: the daily drift check opens a `Drift:` issue for this repository |
| C-005 Keep the evidence | GitHub: pull requests, CI runs with their reports, and drift issues |
| C-006 Controlled exceptions | Review: an exception is recorded in the pull request that makes it, with its scope, rationale and expiry |
