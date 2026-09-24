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
| `org/custom-properties.json` | The `stack` property the Rust and hygiene rulesets select on |
| `org/security-configurations.json` | `maestrolabs-baseline`, enforced and the default for every new repository |
| `org/rulesets/*.json` | Organization rulesets, in the shape `PUT orgs/{org}/rulesets/{id}` accepts |
| `org/webhooks.json` | Organization webhooks without secrets or query strings |
| `scripts/export-org.py` | Regenerates `org/` from the live API |
| `.github/workflows/org-drift.yml` | Weekly check that GitHub still matches `org/`, and that every repository holds the organization's standard |
| `.github/workflows/quality-sync.yml` | Daily sync pull request in every repository after a `rust-workflows` release |
| `scripts/quality-sync.py`, `scripts/repository-drift.py`, `scripts/org_quality.py` | The sync, the per-repository drift check, and what they share |
| `.github/workflows/ci.yml` and the other files `rust-gate sync` writes | This repository's own hygiene CI and managed files, as every repository holds them |
| `.github/workflows/scorecard.yml` | This repository's weekly OpenSSF Scorecard |
| `.github/dependabot.yml`, `.github/workflows/dependabot-auto-merge.yml` | Weekly action updates for this repository's workflows, patch and minor merged by the bot |
| `profile/` | The organization page on GitHub, with its banner and pillar icons |
| `workflow-templates/rust-ci.*` | The "Rust CI" template offered under Actions, New workflow |
| `workflow-templates/hygiene-ci.*` | The "Hygiene CI" template, for a repository without Rust |
| `workflow-templates/scorecard.*` | The "OpenSSF Scorecard" template, the same workflow for any repository |
| `assets/` | The mark, the avatar, and the palette, type and prompts behind them |
| `AGENTS.md` | Instructions for coding agents: change order, API gotchas, invariants |
| `LICENSE` | MIT, for this repository only: GitHub never inherits a license |

### Defaults every repository inherits

GitHub shows these in any repository of the organization that has no file of
its own. A repository's own file always wins.

| File | Inherited as |
| --- | --- |
| `SECURITY.md` | Security policy, pointing reporters at private vulnerability reporting |
| `CONTRIBUTING.md` | Contribution guide, with the rules every pull request passes |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| `pull_request_template.md` | Pull request description template |
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
| `stack` (`rust`, `other` or `workflows`, required) | Every repository says which checks guard its default branch: `rust` requires `rust / Required Rust CI`, `other` requires `hygiene / Required hygiene`, and `workflows` is `rust-workflows`, held to its own CI by its own ruleset; `quality-sync.yml` syncs `rust` and `other` |
| `hygiene-required` | A repository without Rust passes the organization's hygiene checks before merge, as a Rust one passes its CI |
| `maestrolabs-baseline` | CodeQL, secret scanning with push protection, Dependabot, private vulnerability reporting |
| `floor-no-destruction` | No deletion or force-push of any default branch |
| `floor-release-tags` | `v*` tags cannot be deleted or moved; creation stays open for releases |
| `default-branch-discipline` | Every repository: pull request, squash only, resolved threads, signed commits, CodeQL results with no high alert |
| `rust-ci-required` | Rust repositories merge only after `rust / Required Rust CI`, reported by GitHub Actions itself |
| `rust-workflows-ci-required` | `rust-workflows` merges only after its own `Required repository quality` and `Required consumer tests` |
| `commits-are-conventional` | Conventional commit titles on every default branch |
| `visibility-is-frozen` | Public runners are unmetered; a private repository would start billing |

### Standing decisions

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
- **An OpenSSF Scorecard for every repository.** Each repository runs its own
  `scorecard.yml`, because the Scorecard API accepts a published result only
  from a workflow in the scored repository. It publishes the score for a README
  badge and shows the findings in code scanning.

## New repository checklist

Settings a new repository needs that no organization default covers:

1. **Stack and managed files:** set `stack` to `rust` or `other`, then run
   `rust-gate init` at the latest `rust-workflows` release in the new
   repository and commit what it writes: the CI caller, the hooks and every
   managed file. From then on `quality-sync.yml` keeps them current.

   ```bash
   gh api -X PATCH repos/Orchestration-Maestro/REPO/properties/values \
     --input - <<< '{"properties":[{"property_name":"stack","value":"rust"}]}'
   RUST_WORKFLOWS_PIN="<release commit> v<version>" rust-gate init
   ```

2. **Reported content:** Settings, Moderation options, Reported content, select
   **All users**, Save. The Code of Conduct sends reports to this button; the
   default admits only prior contributors, so a newcomer could not report.
   There is no API for it.
3. **Dependabot auto-merge:** turn on auto-merge, then copy
   `rust-workflows`' `.github/workflows/dependabot-auto-merge.yml`; the bot's
   credentials are already organization-wide.

   ```bash
   gh api -X PATCH repos/Orchestration-Maestro/REPO -F allow_auto_merge=true
   ```

4. **OpenSSF Scorecard:** add the OpenSSF Scorecard workflow from this
   organization's templates (Actions, New workflow), then the badge
   `https://api.scorecard.dev/projects/github.com/Orchestration-Maestro/REPO/badge`.
5. **Social preview:** Settings, General, Social preview, upload a 1280 x 640
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

`quality-sync.yml` runs every day and on demand. It builds `rust-gate` at the
latest `rust-workflows` release and, in every repository whose `stack` is `rust`
or `other`, runs `rust-gate sync`. When a managed file changes, it opens or
updates one pull request from `maestro/sync`, a single commit GitHub signs. A
minor or patch release merges itself once green; a major one waits for a person.
A repository whose first sync needs a person, a manifest with lint tables of its
own for instance, is named in the run's log and failed. It runs as the
organization bot, whose token already writes contents, pull requests and
workflows in every repository.

## Weekly drift check

`org-drift.yml` runs every Monday and on demand. It exports the live settings and
fails when they differ from `org/`. On a failure, read the diff in the run log:
if the change was intended, export and commit it here; if not, revert it on
GitHub.

It reads the organization as **Orchestration Maestro Audit**, a GitHub App that
exists only for this check. GitHub lets an App list organization rulesets only
with **Administration: read and write**, although the script only reads, so its
key is treated as an admin credential: it lives only in the `org-audit`
environment, which only `main` can use, and no pull request can reach it. The
workflow mints a token that expires within the hour, so there is nothing to
renew.

| App permission (organization) | For |
| --- | --- |
| Administration: read and write | Settings, Actions policy, security configurations, rulesets |
| Custom properties: read | The `stack` property |
| Webhooks: read | `org/webhooks.json` |

A second job, **Every repository on the standard**, reads every repository as
the organization bot. A repository drifts when it has no `stack`, when its sync
pull request has waited more than 14 days, or when `rust-gate sync --check` at
the latest release finds a managed file that differs on its default branch. Each
drifting repository has one open issue here, `Drift: <name>`, updated on every
run and closed once it is back on the standard.

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
