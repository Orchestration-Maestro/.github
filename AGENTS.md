# AGENTS.md

This is the Orchestration-Maestro organization's `.github` repository: the
organization's settings as code, its public profile, and the files every
repository inherits.

The shared engineering rules are in
[maestro's AGENTS.md](https://github.com/Orchestration-Maestro/maestro/blob/main/AGENTS.md).
This file holds only instructions specific to the organization's settings
repository. Where the two disagree, maestro's file wins.

## `org/` is generated

GitHub is the source of truth; `org/` is its export, written by
`scripts/export-org.py`. Change a setting in this order:

1. Apply it on GitHub with `gh api`. Settings with no API go to the owner (see
   the gotchas below). Done when reading the same endpoint back returns the new
   value.
2. Run `python3 scripts/export-org.py`. Done when it exits 0 with no
   `unclassified` warning.
3. Read `git status org/` and `git diff org/`. Done when they show your change
   and nothing else. Anything else is **drift** someone made on GitHub: stop and
   report it to the owner.
4. Give the setting its reason: add or update its row in README's "What each
   decision is for" table.
5. Commit the export and the README row together.

`org/` changes only through the export; the weekly `org-drift.yml` check fails
on any file that disagrees with GitHub. One change runs these steps itself: at
each `maestro-rust-workflows` release, `quality-sync.yml`'s `repin` job
(`scripts/pin-rulesets.py`) moves the central rulesets' pins, exports, and opens
the pull request that records them, and stops on any other difference.

One file in `org/` is written by hand:

- `org/repository-rulesets/merge-queue.json`, the ruleset every repository
  carries of its own, since GitHub refuses a `merge_queue` rule in an
  organization ruleset (HTTP 422). The daily repository drift check holds
  each repository to it.

The export leaves it alone.

## GitHub API gotchas

- **Rulesets:** update from the full current state. GET the ruleset, change one
  field, and PUT `name`, `target`, `enforcement`, `conditions`, `bypass_actors`
  and `rules` together.
- **No API, owner only:** `members_can_delete_repositories` and
  `members_can_change_repo_visibility` (a PATCH returns 200 and keeps the old
  value), a repository's "Reported content" setting, the organization avatar
  and each repository's social preview.
- `members_can_create_repositories=false` also turns
  `members_can_create_public_repositories` off. That is expected.
- **Custom properties:** before deleting one, move every ruleset off it; search
  `org/rulesets/*.json` for its name.
- **Tokens:** listing organization rulesets needs Administration read *and
  write*, for an App as for a fine-grained token. The audit App, which the
  drift check reads with and the ruleset repin writes with, therefore holds an
  admin credential; its key stays in the `org-audit` environment. Locally, webhooks need the `admin:org_hook` scope; without it
  the export keeps the previous `org/webhooks.json`.
- **`unclassified` warning:** GitHub added an organization field. Classify it in
  `scripts/export-org.py`: GitHub's default in `ORG_DEFAULTS`, or `ORG_IGNORED`
  for profile, identity and counters.

## Invariants

- This repository is public: files carry no secrets, tokens, personal emails or
  billing data. The export keeps webhook URLs to scheme, host and path.
- **Workflows**, here and in `workflow-templates/`: actions come only from
  `actions/*`, `github/*`, `Orchestration-Maestro/*`,
  `googleapis/release-please-action` for releases, `codecov/codecov-action` or
  `ossf/scorecard-action`, each pinned to a full commit SHA with its version in
  a trailing comment; `permissions:` is explicit; input reaches `run:` only
  through `env:`. The organization rejects any other action or pin.
- **No required check comes from a repository's own workflow.** `rust-central`
  supplies the shared Rust workflow. `hygiene-central` is retained but disabled; the old managed-file
  sync no longer runs.
- **The central rulesets and the caller workflows follow releases.**
  `quality-sync.yml` keeps only its `repin` job (`scripts/pin-rulesets.py`). It
  finds `maestro-rust-workflows` by name, records only pin changes, opens one pull
  request per repository that calls the shared workflow (`ci/pin-maestro-rust-workflows`,
  left for a person to merge, since Maestro's caller runs only on a push to the
  default branch and no check proves the new pin first), and requires `major`
  across a major release.
- **One rule set for all repositories:** every ruleset targets `~ALL`, except
  `rust-central`, which targets `stack=rust`, `hygiene-central`, which
  targets `stack=other`, and `rust-workflows-ci-required`, which holds
  `maestro-rust-workflows`, `stack=workflows`, to its own CI. A
  repository-specific exception is its own ruleset, decided by the owner.
- **File baseline:** every repository keeps its own `README.md`, `LICENSE`,
  `AGENTS.md`, `CONTEXT.md`, `.github/CODEOWNERS`, Copilot guide, rule map,
  Scorecard and Dependabot auto-merge workflows (`OWN_FILES` in
  `scripts/repository-drift.py`). `maestro` and `maestro-rust-workflows`,
  which started with the shared CI, keep no per-repository quality files and
  land every dependency update through review: they need no Copilot guide,
  rule map or auto-merge workflow, and a rule map there is drift (`NEW`).
  Tools are pinned only in `mise.toml` and `mise.lock`, the files the shared
  CI installs from; any other pin file in `TOOL_PINS` is drift.
  Community files live here as defaults; a repository keeps its own copy only
  for a need of its own. The daily drift check opens an issue for every gap.
- **Keep this repository's Copilot guide current by hand.** The old gate's
  guide and rule-map generation and freshness checks have been removed.
- **Golden rules are mapped in every repository but the two new ones.**
  `golden-rules/` holds the rules; each older repository's `docs/standards/`
  records how it holds them.
- The repository drift check requires each repository to be named `maestro` or
  `maestro-` then lowercase kebab-case, `.github` aside, with a description and
  a topic.
- **Edit a rule in `golden-rules/`, never on the page.** The organization page's
  blocks between `<!-- generated by scripts/org-page.py: ... -->` markers are
  written from their sources: each rule's `>` summary, the principles table,
  `standards.md`, the Northstar and each repository's
  description on GitHub. A count in words must match what the page holds, and a
  new foundation or pillar needs its picture in `profile/`; `scripts/org-page.py`
  refuses otherwise. Run it explicitly when its sources change.
- Branch names follow `org/rulesets/branch-names.json`; pull request titles
  follow `org/rulesets/commits-are-conventional.json`.
- This repository's default branch takes only squash-merged pull requests.

## File placement

GitHub reads issue forms only from `.github/ISSUE_TEMPLATE/` of this repository,
and every other inherited file (`SECURITY.md`, `CONTRIBUTING.md`,
`CODE_OF_CONDUCT.md`, `SUPPORT.md`, `PULL_REQUEST_TEMPLATE.md`) from the root. A workflow
template needs a `.properties.json` with the same name. `LICENSE` covers this
repository only: GitHub never inherits a license.

## Verify before committing

The pinned tools live in `../rust-workflows/.tools/bin` in this workspace.

```bash
python3 scripts/export-org.py && git status --porcelain org/
actionlint .github/workflows/*.yml
zizmor --offline .github/workflows
gitleaks dir . --redact
typos .
python3 -m unittest discover -s scripts
```

Done when every command passes, and a second export leaves `org/` unchanged.

## Pointers

- **Brand work** (logo, banner, icons, profile copy): read `assets/README.md` first;
  it holds the palette, the logo concept and the prompts.
- **New repository in the organization:** apply README's "New repository
  checklist".
- **Drift token setup or renewal:** README's "Drift checks".

## Agent skills

### Issue tracker

Issues are GitHub issues in this repository. See `docs/agents/issue-tracker.md`
for this repository's issue operations.

### Triage labels

This repository's label mappings are in `docs/agents/triage-labels.md`.

### Domain docs

See `docs/agents/domain.md` for this repository's documentation layout.
