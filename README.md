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
| `org/custom-properties.json` | The `stack` property the Rust CI ruleset selects on |
| `org/security-configurations.json` | `maestrolabs-baseline`, enforced and the default for every new repository |
| `org/rulesets/*.json` | Organization rulesets, in the shape `PUT orgs/{org}/rulesets/{id}` accepts |
| `org/webhooks.json` | Organization webhooks without secrets or query strings, once a token can read them |
| `scripts/export-org.py` | Regenerates `org/` from the live API |
| `.github/workflows/org-drift.yml` | Weekly check that GitHub still matches `org/` |
| `profile/` | The organization page on GitHub, with its banner and pillar icons |
| `workflow-templates/rust-ci.*` | The "Rust CI" template offered under Actions, New workflow |
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
| Actions `allowed_actions: selected` | Only `actions/*`, `github/*` and `Orchestration-Maestro/*` run, plus `googleapis/release-please-action` for releases |
| Actions `sha_pinning_required` | A tag can be moved to new code; a full commit SHA cannot |
| Actions `self-hosted-runners: none` | On a public repository, any pull request would run code on the runner's machine |
| Actions `fork-pr-contributor-approval` | Every external contributor's workflow run waits for an owner's approval |
| Actions `artifact-and-log-retention: 30` | Public logs and artifacts are readable by anyone signed in; keep them shorter |
| `stack` (`rust`, optional) | Set it on a Rust repository whose CI calls `rust-workflows` as job `rust`, to require that CI before merge |
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

## New repository checklist

Settings a new repository needs that no organization default covers:

1. **Rust repositories** that call `rust-workflows` as job `rust`, as the Rust CI
   template does: set `stack=rust`, so `rust-ci-required` applies.
   `rust-workflows` itself has its own ruleset and no `stack`.
   ```bash
   gh api -X PATCH repos/Orchestration-Maestro/REPO/properties/values \
     --input - <<< '{"properties":[{"property_name":"stack","value":"rust"}]}'
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
4. **Social preview:** Settings, General, Social preview, upload a 1280 x 640
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

## Weekly drift check

`org-drift.yml` runs every Monday and on demand. It exports the live settings and
fails when they differ from `org/`. On a failure, read the diff in the run log:
if the change was intended, export and commit it here; if not, revert it on
GitHub.

It needs a token, and that token is powerful: GitHub lets a fine-grained token
list organization rulesets only with **Administration: read and write**, although
the script only reads. The workflow therefore takes it only from the `org-audit`
environment, which only the default branch can use, and never runs on pull
requests. One-time setup, after this repository exists on GitHub:

1. Create a fine-grained personal access token: resource owner
   Orchestration-Maestro, no repository access, organization permissions
   Administration (read and write), Custom properties (read) and Webhooks (read),
   expiring in 90 days. Approve it under Organization settings, Personal access
   tokens, if the organization asks for approval.
2. Create the environment and restrict it to `main`:
   ```bash
   gh api -X PUT repos/Orchestration-Maestro/.github/environments/org-audit \
     -F 'deployment_branch_policy[protected_branches]=false' \
     -F 'deployment_branch_policy[custom_branch_policies]=true'
   gh api -X POST repos/Orchestration-Maestro/.github/environments/org-audit/deployment-branch-policies \
     -f name=main -f type=branch
   ```
3. Store the token in it: `gh secret set ORG_SETTINGS_TOKEN --env org-audit --repo Orchestration-Maestro/.github`
4. Run it once: `gh workflow run org-drift.yml --repo Orchestration-Maestro/.github`

Renew the token before it expires; an expired token fails the check loudly.

## Not covered

- Member privileges the API reports but cannot write (repository deletion,
  visibility change) are compared like any other field; changing them needs the
  web UI.
- Repository-level settings: each repository's own `CODEOWNERS`,
  `dependabot.yml`, workflows and license. GitHub never inherits those.
