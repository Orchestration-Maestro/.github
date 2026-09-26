# Orchestration-Maestro organization settings

The organization's `.github` repository: its public profile, the defaults every
repository inherits, and every organization setting that differs from GitHub's
defaults, exported from the live API. A setting absent from `org/` is GitHub's
default.

This repository is **public**: the `visibility-is-frozen` ruleset allows
no other visibility. Nothing here is secret; the export leaves out the billing
email, profile fields and the member list.

## Layout

| File | What it holds |
| --- | --- |
| `org/settings.json` | Organization fields that differ from the defaults table in the script |
| `org/actions.json` | Actions policy: allowed actions, SHA pinning, and anything else non-default |
| `org/custom-properties.json` | The `stack` property the central rulesets select on |
| `org/security-configurations.json` | `maestrolabs-baseline`, enforced and the default for every new repository |
| `org/rulesets/*.json` | Organization rulesets, in the shape `PUT orgs/{org}/rulesets/{id}` accepts |
| `org/repository-rulesets/merge-queue.json` | The ruleset every repository carries of its own, in the shape `POST repos/{owner}/{repo}/rulesets` accepts; written by hand, not exported |
| `org/webhooks.json` | Organization webhooks without secrets or query strings |
| `scripts/export-org.py` | Regenerates `org/` from the live API |
| `.github/workflows/org-drift.yml` | Weekly check that GitHub still matches `org/`, and a daily one that every repository holds the standard and the file baseline |
| `.github/workflows/quality-sync.yml` | The central rulesets moved to each `rust-workflows` release as soon as it is created, then a sync pull request in every repository |
| `scripts/pin-rulesets.py`, `scripts/quality-sync.py`, `scripts/repository-drift.py`, `scripts/org_quality.py` | The ruleset repin, the sync, the per-repository drift check, and what they share |
| `scripts/test_*.py` | Their tests: `python3 -m unittest discover -s scripts` |
| `scripts/org-page.py` | Writes every generated block of the organization page from its one source, and refuses golden rules that disagree with themselves |
| `.pre-commit-config.yaml` and the other files `rust-gate sync` writes | This repository's managed files, as every repository holds them; `hygiene-central` runs its CI |
| `.github/workflows/scorecard.yml` | This repository's weekly OpenSSF Scorecard |
| `.github/dependabot.yml`, `.github/workflows/dependabot-auto-merge.yml` | Weekly action updates for this repository's workflows, patch and minor merged by the bot |
| `profile/` | The organization page on GitHub, with its banner, the Northstar panel and the pillar and foundation cards; `scripts/org-page.py` writes each block between its generated markers |
| `golden-rules/` | The golden rules every repository follows: engineering, security, the Northstar, the standards they align with and the glossary of the words every repository shares; the one source of the organization page's rules, of every rule map and of the copy `rust-gate` embeds |
| `docs/adr/` | Decisions about how the organization runs, each with the trade-off that produced it |
| `workflow-templates/scorecard.*` | The "OpenSSF Scorecard" template offered under Actions, New workflow, the same workflow for any repository |
| `assets/` | The mark, the avatar, and the palette, type and prompts behind them |
| `CONSTITUTION.md` | Spec Kit's constitution: an index of the pages that hold our identity, rules and tools, which come first |
| `AGENTS.md` | Instructions for coding agents: change order, API gotchas, invariants |
| `CONTEXT.md` | The words this repository uses: stack, standard, file baseline, default, drift |
| `.github/CODEOWNERS` | Every change here goes to the maintainer for review |
| `LICENSE` | MIT, for this repository only: GitHub never inherits a license |

### Defaults every repository inherits

GitHub shows these in any repository of the organization that has no file of
its own. A repository's own file always wins.

| File | Inherited as |
| --- | --- |
| `SECURITY.md` | Security policy, pointing reporters at private vulnerability reporting |
| `CONTRIBUTING.md` | Contribution guide, with the rules every pull request passes |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| `SUPPORT.md` | Where each kind of question goes, and what to include |
| `PULL_REQUEST_TEMPLATE.md` | Pull request description template |
| `.github/ISSUE_TEMPLATE/` | Bug and feature forms; blank issues are off |

## What each decision is for

| Setting | Why |
| --- | --- |
| `two_factor_requirement_enabled` | A member account without 2FA is a compromise of every repository |
| `members_can_create_*repositories: false` | Only owners create repositories, so each one starts under these rulesets |
| `members_can_create_teams: false` | Only owners grant access through teams |
| `members_can_delete_repositories: false` | Only owners delete or transfer a repository (web UI only) |
| `members_can_change_repo_visibility: false` | Only owners change visibility (web UI only) |
| `deploy_keys_enabled_for_repositories: false` | No repository-scoped SSH keys outside the owner's control |
| `*_enabled_for_new_repositories` | Legacy switches; `maestrolabs-baseline` supersedes them |
| Actions `allowed_actions: selected` | Only `actions/*`, `github/*` and `Orchestration-Maestro/*` run, plus `googleapis/release-please-action` for releases, `codecov/codecov-action` for coverage and `ossf/scorecard-action` for the security score |
| Actions `sha_pinning_required` | A tag can be moved to new code; a full commit SHA cannot |
| Actions `self-hosted-runners: none` | On a public repository, any pull request would run code on the runner's machine |
| Actions `fork-pr-contributor-approval` | Every external contributor's workflow run waits for an owner's approval |
| Actions `artifact-and-log-retention: 30` | Public logs and artifacts are readable by anyone signed in; keep them shorter |
| `stack` (`rust`, `other` or `workflows`, required) | Every repository says which checks guard its default branch: `rust` runs `rust-workflows`' `ci.yml` through `rust-central`, `other` its `hygiene.yml` through `hygiene-central`, and `workflows` is `rust-workflows`, held to its own CI by its own ruleset; `quality-sync.yml` syncs `rust` and `other` |
| `hygiene-central` | Every repository without Rust runs `rust-workflows`' own `hygiene.yml`, pinned to the latest release's commit, required by the ruleset itself; `quality-sync.yml` moves the pin at each release ([ADR 0001](docs/adr/0001-enforce-the-standard-centrally.md)) |
| `maestrolabs-baseline` | CodeQL, secret scanning with push protection, Dependabot, private vulnerability reporting |
| `floor-no-destruction` | No deletion or force-push of any default branch |
| `floor-release-tags` | `v*` tags cannot be deleted or moved; creation stays open for releases |
| `default-branch-discipline` | Every repository: pull request, squash only, resolved threads, signed commits, CodeQL results with no high alert |
| `rust-central` | Every Rust repository's pull request runs `rust-workflows`' own `ci.yml`, pinned to the latest release's commit, required by the ruleset itself: no repository can edit, loosen or skip the check; `quality-sync.yml` moves the pin at each release ([ADR 0001](docs/adr/0001-enforce-the-standard-centrally.md)) |
| `rust-workflows-ci-required` | `rust-workflows` merges only after its own `Required repository quality` and `Required consumer tests` |
| `commits-are-conventional` | Records the Conventional Commit title every default branch takes. GitHub enforces its metadata restriction only on the Enterprise plan, so on Team it refuses nothing; PRL-003 in the shared CI refuses a pull request whose title is not one, and a squash merge makes that title the commit's |
| `branch-names` | A branch can be created only under a Conventional Commit type, `feat/…`, `fix/…`, `docs/…` and the rest, or as a bot's: `maestro/sync`, `release-please--*`, `dependabot/…`, `gh-readonly-queue/…` (the merge queue), and GitHub's own `revert-*` (the Revert button) and `copilot/…` (the coding agent). It restricts creation outside those prefixes, since branch name patterns are Enterprise-only. Each prefix is excluded as `prefix/**/*`: a trailing `**` matches one level only, which refused the merge queue's `gh-readonly-queue/main/pr-…` and Dependabot's `dependabot/cargo/…`; PRL-004 refuses a pull request from a branch that is not lowercase kebab-case after its prefix |
| `visibility-is-frozen` | Public runners are unmetered; a private repository would start billing |
| `merge-queue` (each repository) | A pull request merges through the merge queue, squashed, one at a time: its checks run again on the default branch as it will be, so two green pull requests cannot merge into a red branch. GitHub refuses a `merge_queue` rule in an organization ruleset (HTTP 422), so each repository carries `org/repository-rulesets/merge-queue.json`, and the drift check flags one that lacks it |

### Standing decisions

- **Merge through the queue.** Every repository's default branch takes a pull
  request only from its merge queue. Queue one with `gh pr merge --auto`: it
  joins the queue once its checks pass and its threads are resolved, and
  merges once they pass again on top of the queue.
- **The same rules for every repository.** Every ruleset targets all
  repositories: none can opt out of pull requests, signed commits or the CodeQL
  gate. A repository that needs direct pushes needs its own reviewed ruleset
  exception.
- **Actions cannot approve pull requests** (`can_approve_pull_request_reviews`
  stays false). The organization's GitHub App, `orchestration-maestro-bot`,
  acts instead: release-please opens release pull requests with its token, and
  Dependabot patch and minor updates queue their merge with it. Its pull
  requests and merges trigger the checks and workflows a `GITHUB_TOKEN` one
  would not. It is installed on every repository with Contents, Issues, Pull
  requests and Workflows write; its client ID and key are the organization
  variable `RELEASE_APP_CLIENT_ID` and secret `RELEASE_APP_PRIVATE_KEY`, stored
  again as Dependabot secrets.
- **Coverage in Codecov, without a stored token.** The Codecov GitHub App is
  installed on every repository, and `rust-workflows`' `upload-coverage.yml`
  logs in through OIDC, so no Codecov token exists to leak or rotate. Codecov
  reports; the coverage floor in `rust-workflows` is what fails a run.
- **The central rulesets follow each release, before its sync pull requests.**
  `rust-workflows`' managed-files check runs from the rulesets' pin, so a sync
  pull request is green only once they run the release it brings, and a ruleset
  update does not re-run an open pull request. A repository's other pull
  requests fail that check until its sync pull request merges, minutes for a
  minor or patch release. A major release waits for a person, like its sync
  pull requests.
- **An OpenSSF Scorecard for every repository.** Each repository runs its own
  `scorecard.yml`, because the Scorecard API accepts a published result only
  from a workflow in the scored repository. It publishes the score for a README
  badge and shows the findings in code scanning.

## New repository checklist

Settings a new repository needs that no organization default covers:

1. **Name, description and topics:** the name is `maestro-` followed by
   lowercase kebab-case, the description says what it is in one line (the
   organization page shows it), and at least one topic classifies it. The
   drift check refuses a repository without them. Renaming one later breaks
   every GitHub Actions `uses:` that names it: Actions follows no redirect.
2. **Stack and managed files:** set `stack` to `rust` or `other`, then run
   `rust-gate init` at the latest `rust-workflows` release in the new
   repository and commit what it writes: the hooks and every managed file.
   `rust-central` or `hygiene-central` runs its CI from then on, and
   `quality-sync.yml` keeps the files current.

   ```bash
   gh api -X PATCH repos/Orchestration-Maestro/REPO/properties/values \
     --input - <<< '{"properties":[{"property_name":"stack","value":"rust"}]}'
   RUST_WORKFLOWS_PIN="<release commit> v<version>" rust-gate init
   ```

3. **Files of its own:** `README.md`, `LICENSE`, `AGENTS.md`, `CONTEXT.md`,
   `.github/CODEOWNERS`, the Copilot guide and the rule map, the file baseline
   GitHub never inherits. From the new repository's root, write the rule map
   with `rust-gate rules` and replace every "Not mapped yet" with what holds
   that rule here, then write the guide with `rust-gate guide`. Both keep what
   a person wrote, and the repository's commit hooks keep both current. The
   drift check opens an issue for any file that is missing.
4. **Reported content:** Settings, Moderation options, Reported content, select
   **All users**, Save. The Code of Conduct sends reports to this button; the
   default admits only prior contributors, so a newcomer could not report.
   There is no API for it.
5. **Dependabot auto-merge:** turn on auto-merge, then copy
   `rust-workflows`' `.github/workflows/dependabot-auto-merge.yml`; the bot's
   credentials are already organization-wide.

   ```bash
   gh api -X PATCH repos/Orchestration-Maestro/REPO -F allow_auto_merge=true
   ```

6. **OpenSSF Scorecard:** add the OpenSSF Scorecard workflow from this
   organization's templates (Actions, New workflow), then the badge
   `https://api.scorecard.dev/projects/github.com/Orchestration-Maestro/REPO/badge`.
7. **Social preview:** Settings, General, Social preview, upload a 1280 x 640
   crop of the banner (see `assets/README.md`). Web UI only.

## Refresh by hand

```bash
gh auth status        # needs the admin:org scope, and admin:org_hook for webhooks
python3 scripts/export-org.py
git status org/       # any change is drift between this review and GitHub
```

The script needs only Python 3 and `gh`. It warns when GitHub reports an
organization field its defaults table does not classify, so a new setting is
reviewed instead of silently dropped. Without webhook access it warns and keeps
the previous `org/webhooks.json`.

## Quality sync

`quality-sync.yml` runs as soon as `rust-workflows` creates a Release, whose
workflow sends it the event `rust-workflows-release`, and again every day and on
demand. Its first job, `repin`, runs `scripts/pin-rulesets.py` in the `org-audit`
environment: every organization ruleset that runs a workflow of
`rust-workflows`, `rust-central` and `hygiene-central`, moves to the release's
commit and tag. It then exports `org/` and, when the export differs from `org/`
by these pins alone, opens or updates the pull request from
`ci/pin-the-central-rulesets`, one commit GitHub signs, which merges itself once
green. Any other difference is drift: it publishes nothing and fails. A pin
moves only forward, and across a major release only when a person runs the
workflow with `major` after reading the release notes; that run also
re-publishes the major's sync pull requests, which then run under the release.
`python3 scripts/pin-rulesets.py --dry-run` prints every update and writes
nothing, and with `--release <tag> <commit>` shows what a release would move.

The second job builds `rust-gate` at the latest `rust-workflows` release and, in
every repository whose `stack` is `rust` or `other`, runs `rust-gate sync`,
which moves every call to `rust-workflows` to that release. It also runs on a
push to `golden-rules/`, the pictures or `scripts/org-page.py`. In this
repository it rewrites the organization page's generated blocks from their
sources, `golden-rules/`, `rust-gate gate-rules` and each public repository's
description, so a changed rule, a new gate rule or a new repository reaches the
page on its own. In `rust-workflows` it brings the golden-rules pages
`rust-gate` embeds up to these and rewrites its rule map from them, as a `fix:`
pull request that merges itself once green; a rule it adds waits, "Not mapped
yet", for a person. When a file changes, it opens or updates one pull request from
`maestro/sync`, a single commit GitHub signs. A
minor or patch release merges itself once green; a major one waits for a person.
A repository whose first sync needs a person, a manifest with lint tables of its
own for instance, is named in the run's log and failed. It runs as the
organization bot, whose token already writes contents, pull requests and
workflows in every repository.

## Drift checks

`org-drift.yml` checks the settings every Monday and on demand. It exports the
live settings and fails when they differ from `org/`. On a failure, read the diff in the run log:
if the change was intended, export and commit it here; if not, revert it on
GitHub.

It reads the organization as **Orchestration Maestro Audit**, a GitHub App that
exists only for this check and for the `repin` job of `quality-sync.yml`, the
one that writes. GitHub lets an App list organization rulesets only with
**Administration: read and write**, so its key is treated as an admin
credential: it lives only in the `org-audit`
environment, which only `main` can use, and no pull request can reach it. The
workflow mints a token that expires within the hour, so there is nothing to
renew.

| App permission (organization) | For |
| --- | --- |
| Administration: read and write | Settings, Actions policy, security configurations, rulesets; the central rulesets' pins |
| Custom properties: read | The `stack` property |
| Webhooks: read | `org/webhooks.json` |

A second job, **Every repository on the standard**, reads every repository as
the organization bot every day, on every push to `main` and on demand. A
repository drifts when it has no `stack`, when its sync pull request has waited
more than 14 days, when `rust-gate sync --check` at the latest release finds a
managed file that differs on its default branch, or when it strays from the
file baseline in `scripts/repository-drift.py`:

- its `merge-queue` ruleset is missing, not active, or has conditions or rules
  other than `org/repository-rulesets/merge-queue.json`'s; the issue gives the
  `gh api` command that restores it;
- it keeps a pull request's branch after the merge: every repository turns on
  "Automatically delete head branches" (`delete_branch_on_merge`), which GitHub
  cannot set for the whole organization;
- it misses a file every repository keeps of its own: `README.md`, `LICENSE`,
  `AGENTS.md`, `CONTEXT.md`, `.github/CODEOWNERS`, and the Scorecard and
  Dependabot auto-merge workflows;
- it pins tools of its own in `mise.toml`, `mise.lock`, `.mise.toml`,
  `.tool-versions` or `tool-updates.yml`: the pins live once, in
  `rust-workflows`, and `rust-gate setup` installs them;
- it keeps a copy identical to one of the defaults above, which a repository
  keeps only for a need of its own;
- its issue forms apply a label it lacks, which GitHub skips;
- its rule map in `docs/standards/` is stale, or still says "Not mapped yet":
  `rust-gate rules --check` compares it to the golden rules the latest release
  carries (C-001); `rust-workflows`' own `just check` holds its rule map to the
  copy it carries instead;
- its Copilot guide is stale: `rust-gate guide --check` finds a file added or
  removed since the guide was written. `rust-workflows` keeps its own guide,
  the model, under its own inventory test.

Each drifting repository has one open issue here, `Drift: <name>`, updated on
every run and closed once it is back on the standard.

The environment holds the App's client ID as the variable
`ORG_AUDIT_APP_CLIENT_ID` and a private key as the secret
`ORG_AUDIT_APP_PRIVATE_KEY`. To rotate the key, generate a new one on the App's
settings page, replace the secret, then delete the old key there.

## Not covered

- Member privileges the API reports but cannot write (repository deletion,
  visibility change) are compared like any other field; changing them needs the
  web UI.
- Repository-level settings: each repository's own `CODEOWNERS`,
  `dependabot.yml`, workflows and license. GitHub never inherits those.
