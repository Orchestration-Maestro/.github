# Enforce the standard centrally, from rust-workflows

Status: accepted (2026-09-25).

## Context

The standard is enforced from inside each repository today:

- Every repository carries `.github/workflows/ci.yml`, a caller of
  rust-workflows' reusable `ci.yml` (or `hygiene.yml` for `stack=other`), and
  about fifteen more files `rust-gate sync` writes: `.editorconfig`,
  `.gitattributes`, `.rumdl.toml`, `.taplo.toml`, `.yamlfmt.yml`,
  `typos.toml`, `.github/dependabot.yml`, `.pre-commit-config.yaml` and, in a
  Rust repository, `.config/nextest.toml`, `clippy.toml`,
  `rust-toolchain.toml`, `rustfmt.toml`, `deny.toml` and the lint block of
  `Cargo.toml` (`gate/src/steps/managed_files/render.rs`).
- Each rust-workflows release makes `quality-sync.yml` open one sync pull
  request per repository, and the daily drift job files a `Drift: <name>` issue
  for each repository that falls behind.
- The rulesets `rust-ci-required` and `hygiene-required` require a status check
  *named* `rust / Required Rust CI` or `hygiene / Required hygiene` from
  GitHub Actions. Any workflow of the repository that names a job that way
  satisfies them, and the repository chooses which release its caller pins.
- A gate change costs two rust-workflows pull requests, since the reusable
  workflow builds its gate through `.github/actions/gate@<sha>` and a commit
  cannot name its own hash, then one sync pull request per repository.
- The tool pins live in rust-workflows' `mise.toml` and `mise.lock`, and in the
  install rows of its CI. maestro-core and maestro-model-router carry
  hand-copied subsets; maestro-release-canary and `.github` carry none.
  rust-workflows#60 (paused) would mirror the whole toolbelt into every
  repository as more managed files.
- Every Rust repository must build and pass on Linux, macOS and Windows.

The owner's requirement: the standard is not managed in every repository,
because copies drift; it is enforced from above.

## What GitHub offers

An organization ruleset may hold a `workflows` rule, "Require workflows to pass
before merging" ([rules][rules]). It is accepted on this organization's Team
plan: a disabled probe ruleset holding it was created through the REST API and
then deleted, on 2026-09-25. What GitHub's documentation says about it:

- **Source.** The rule names a workflow file by `repository_id` and `path`,
  pinned by `ref` (branch or tag) or `sha` ([REST][rest]). The file must sit in
  the source repository's `.github/workflows`
  ([troubleshooting][troubleshoot]).
- **Visibility.** A workflow in a public repository runs in any repository of
  the organization; an internal one in internal and private repositories; a
  private one in private repositories only. Every repository here is public,
  rust-workflows included ([rules][rules]).
- **Triggers.** Only `pull_request`, `pull_request_target` and `merge_group`.
  Every filter (`branches`, `paths`, `types`) is ignored: the workflow runs, and
  always runs, on `opened`, `synchronize` and `reopened`, and on
  `checks_requested` for a merge queue ([rules][rules]).
- **Not on `GITHUB_TOKEN` events.** A pull request pushed with a workflow's
  `GITHUB_TOKEN` does not start it ([troubleshooting][troubleshoot]). The
  release and sync bots already use GitHub App tokens.
- **Pull requests only.** The rule blocks direct pushes to the branches it
  targets, so it belongs only on branches changed through pull requests; a
  ruleset created while a pull request is open does not run on it until a new
  push, update or reopen ([troubleshooting][troubleshoot]).
- **Repository creation.** A required workflow can block creating a
  repository; `do_not_enforce_on_create` ("Do not require workflows checks on
  creation") lets branches and repositories be created
  ([rules][rules], [REST][rest]).
- **Evaluate mode.** A ruleset in "Evaluate" runs the workflow without
  blocking, and a pull request that passed can merge after the switch to
  "Active" without a new run ([rules][rules]).
- **The source repository runs it too.** On `pull_request`, the file also runs
  as an ordinary workflow of rust-workflows; GitHub suggests disabling that
  workflow in the source repository ([troubleshooting][troubleshoot]).
- **Its own commit.** `job.workflow_repository` and `job.workflow_sha` name
  the repository and commit of the file that defines the running job, and
  GitHub's own example checks out that commit to reach the files beside the
  workflow ([contexts][contexts]).
- **Cost.** Standard GitHub-hosted runners are free for public repositories
  ([billing][billing]); the run bills the repository it runs in.
- **Fork pull requests.** A `pull_request` run from a fork, or from
  Dependabot, gets a read-only token and no secret ([events][events]), after
  the organization's approval of external contributors (`org/actions.json`);
  `pull_request_target` is privileged and must not check out untrusted code
  ([secure use][secure]).

The documentation leaves unclear, and a live run must settle:

1. Whether GitHub's Team-plan pages document the rule at all: it appears only
   in the Enterprise Cloud version of "Available rules for rulesets", while the
   Team plan accepts it through the API.
2. Whether `job.workflow_sha` names the rust-workflows commit the ruleset pins
   when the workflow runs as a ruleset workflow in another repository.
3. Whether `actions/checkout` with no input checks out the target repository's
   pull request, as in an ordinary run.
4. Which `permissions:` a ruleset workflow may take in the target repository:
   `security-events: write` for SARIF and `id-token: write` for Codecov.
5. Whether a ruleset workflow may call reusable workflows and run a `matrix`;
   nothing in the pages forbids either.
6. How the rule is satisfied: by the pinned file's run, which a repository
   cannot fake with a job of the same name, or by a check name. And what
   happens when a repository disables Actions: a blocked pull request or a
   skipped rule.
7. Which pin wins when a rule gives both `ref` and `sha`.

### Live test, 2026-09-25

An active ruleset targeting maestro-release-canary alone required a probe
workflow from a rust-workflows branch, pinned by `sha`, on a pull request with
no change of its own (release-canary pull request 14, closed; ruleset, branches
and probe deleted afterwards). It settled:

- The rule is enforced on the Team plan, not only accepted (1): with every other
  check green, the pull request stayed `BLOCKED` and a merge was refused while
  the probe failed; once the probe passed, the same pull request became `CLEAN`
  after nothing but a new pin and a re-run.
- `job.workflow_sha` and `github.workflow_sha` name the pinned rust-workflows
  commit, and `github.repository` names release-canary (2).
- A plain `actions/checkout` checks out release-canary's pull request: the probe
  read its `maestro-quality.toml` (3).
- A `matrix` ran `cargo test` on `ubuntu-24.04`, `macos-15` and `windows-2025`
  (5, the matrix half).

Still open: `permissions` beyond `contents: read` (4), reusable-workflow calls
(5), whether a same-named job can satisfy the rule, and Actions disabled (6),
and `ref` against `sha` (7): both named the same commit in the test.

## Decision

The standard runs from rust-workflows, required by organization rulesets; a
repository carries no CI caller and no tool pin, and keeps only the
configuration files its tools read from its root.

### CI: two entry workflows, required by `workflows` rules

- rust-workflows gains `.github/workflows/required-rust.yml` and
  `required-hygiene.yml`, triggered by `pull_request` and `merge_group`, never
  `pull_request_target`. They hold today's jobs of `ci.yml` and `hygiene.yml`,
  the Linux, macOS and Windows legs included, and take no input: the per
  repository settings (`coverage-threshold`, `mutation-test`, `platforms`...)
  come from the `[ci]` table of `maestro-quality.toml`, read from the pull
  request's base commit, so a pull request cannot loosen its own gate; the
  gate keeps refusing any value below the organization's floors.
- Two organization rulesets carry a `workflows` rule on `~DEFAULT_BRANCH` with
  `do_not_enforce_on_create`: `rust-ci` for `stack=rust` runs
  `required-rust.yml`, `hygiene-ci` for `stack=other` runs
  `required-hygiene.yml`. Each pins `sha`, the commit of the latest
  rust-workflows release, with `ref` naming its tag for the reader. The
  `floor-release-tags` ruleset already keeps every `v*` tag from moving.
- `rust-ci-required` and `hygiene-required` are deleted, with the `ci.yml`
  callers, the Rust CI templates in `workflow-templates/` and the AGENTS
  invariant "Rust CI job id is `rust`". `rust-workflows-ci-required` stays:
  rust-workflows holds itself to its own CI. The two entry workflows are
  disabled as ordinary workflows in rust-workflows.
- Moving to a release is one ruleset update, `sha` and `ref`, made from
  `quality-sync.yml` on the `rust-workflows-release` event by a token holding
  Administration: write, in a protected environment, followed by the export
  of `org/`. Majors keep waiting for a person, who applies the update.

### The gate builds from the workflow's own commit

Every job checks out `${{ job.workflow_repository }}` at
`${{ job.workflow_sha }}` and builds `gate/` from it. The `gate` action pin,
its "pin the gate that ships this release" pull request and rust-workflows#60's
release-time pin test all go. A gate change is one pull request and a
release. This holds for today's reusable `ci.yml` as well, so it ships first.

### Files that stay in repositories

Tools read these from the repository root, so they stay: `rust-toolchain.toml`,
`clippy.toml`, `rustfmt.toml`, `deny.toml`, the `Cargo.toml` lint block,
`.config/nextest.toml`, `.editorconfig`, `.gitattributes`, `typos.toml`,
`.rumdl.toml`, `.taplo.toml`, `.yamlfmt.yml`, `.pre-commit-config.yaml` and
`.github/dependabot.yml`. They keep the header
`# generated by rust-gate sync; do not edit`. The entry workflow holds them in
two ways:

1. Before any check it runs `rust-gate sync` into its checkout, so every check
   runs with the pinned release's files whatever the repository holds.
2. It fails a pull request whose diff changes one of them to anything but the
   pinned release's rendering. A repository whose files are one release behind
   still merges unrelated work; the sync pull request brings it up.

`rust-gate sync` stays, as the one writer of these files, for the bot and for a
developer. The bot's pull requests shrink to this set; a release that does not
change it opens none. The drift job keeps the file baseline, the rule map and
the Copilot guide, reports a repository still one release behind, and stops
checking CI pins.

### Tools: `rust-gate setup`

The pins live once, in rust-workflows' `mise.toml` and `mise.lock`, which the
gate embeds as it embeds the other managed sources. `rust-gate setup`, run in a
checkout, writes them to a per-user cache,
`~/.cache/maestro/tools/<version>/`, installs them there through mise with the
lock's checksums, and writes the repository's `.git/hooks` so the hooks find
those tools first. Nothing lands in the tracked tree. The entry workflow
installs through the same command, so a developer runs exactly CI's tools.
maestro-core's and maestro-model-router's copies of `mise.toml` and `mise.lock`
go, and the drift job reports a repository that pins tools of its own.

## Considered options

- **Keep callers, harden them** (rust-workflows#60: mirror the toolbelt as
  managed files, test three platforms through the caller). It adds three
  managed files to every repository, keeps a caller the repository can edit
  and a check any job can impersonate, and keeps a sync pull request per
  repository for every tool move: the drift the owner asked to end.
- **Required status checks from a GitHub App** that runs CI elsewhere and
  posts the check with its `integration_id`. A check name then cannot be
  faked, but the organization would run a service, hold its keys and rebuild
  what Actions already gives.
- **Pin the ruleset to a branch** (`ref: refs/heads/main` or a `stable` branch)
  so no update is needed per release. `main` would roll every repository onto
  unreleased gates; a moving branch is a mutable pin the organization's SHA
  pinning rule exists to avoid.
- **Tools through a global mise config.** The user's global config also serves
  every other project, and it holds one version for every repository instead of
  the one the gate's release pins.
- **Tools through a devcontainer.** It is one more file per repository, needs
  Docker, and runs Linux only, while CI tests macOS and Windows too.
- **Check the root files strictly on every pull request** (today's
  `managed-files` step). Each release would block every open pull request in
  every repository until its sync pull request merges.

## Consequences

- Nothing a repository commits turns its CI off, changes its jobs or picks its
  release; the organization moves every repository at once, with one ruleset
  update. The release rolls onto pull requests opened or updated after it.
- A repository carries no CI caller, no tool pin and no toolbelt script. It
  keeps the root configuration files, which CI overwrites before checking.
- A gate change is one pull request and a release; the second repin pull
  request is gone.
- A push to a default branch no longer runs the standard: ruleset workflows run
  on pull requests and merge queues only. The Codecov baseline and the Clippy
  SARIF of the default branch lose their push runs; CodeQL default setup is
  unaffected. The gate already measures a pull request's coverage itself.
- A pull request opened by a `GITHUB_TOKEN` can never merge; every bot of the
  organization must open its pull requests with an App token, as they do now.
- Release workflows (`release.yml`, publishing) stay in the repositories they
  release: they are the product's, not the standard's.
- Updating an organization ruleset from a workflow needs Administration: write,
  an admin credential; it lives in a protected environment only `main` of
  `.github` reaches, like the audit App's key.
- CI minutes stay free while every repository is public; a private repository
  would pay for its three platform legs.

## Migration

| Step | Where | Effort |
| --- | --- | --- |
| 1. Build the gate from `job.workflow_sha` in `ci.yml` and `hygiene.yml`; drop the `gate` action pin and its pin test | rust-workflows, one PR and a minor release | 2 h |
| 2. Add `required-rust.yml` and `required-hygiene.yml`: no inputs, `[ci]` from the base commit, `rust-gate sync` before the checks, the managed-files diff rule; disable both in rust-workflows | rust-workflows, one PR and a release | 1 day |
| 3. Live test: a `workflows` ruleset in Evaluate, then Active, targeting maestro-release-canary alone; settle the seven questions above | `.github`, `gh api` and `org/` export | 2 h |
| 4. Activate `rust-ci` and `hygiene-ci` beside the old rulesets for one release; then delete `rust-ci-required` and `hygiene-required`, drop `ci.yml` from the managed set (`sync` deletes the callers) and the CI templates; update the `stack` description, README rows and AGENTS | `.github`, rust-workflows, one sync round | 0.5 day |
| 5. Ship `rust-gate setup` with the embedded `mise.toml` and `mise.lock`; remove the consumers' toolbelt copies; drift rule "no tool pins of its own" | rust-workflows, then one PR per consumer | 1 day |
| 6. Automate the per-release ruleset update in `quality-sync.yml` behind a protected environment | `.github` | 0.5 day |

rust-workflows#60 is closed. Its commit `cd56362`, Linux, macOS and Windows
for every Rust repository, lands in step 2 as the entry workflow's fixed matrix;
`8068be6` (the toolbelt as managed files) and its release-time pin test are the
opposite of this decision and are dropped. The local drift-rule commit
`a7b3f60` in `.github` (a repository that moves its own tool pins drifts) is
not merged; step 5 replaces it with "a repository carries no tool pin".

### Where the rollout stands (2026-09-25)

The owner took the decision the same day and asked for it quickly, so steps 1,
2 and 4 were done as one release instead of the separate entry workflows above:
rust-workflows v3.0.0 runs `ci.yml` and `hygiene.yml` themselves from a ruleset
(`pull_request` and `merge_group`, settings from the base commit's
`maestro-quality.toml`), builds the gate from `job.workflow_sha` (#61, #64),
always tests macOS and Windows, refuses `license-policy: off`, and passes the
tools' settings at run time, which retires seven generated files per
repository (#63). The canary ran it end to end before any other repository.

- Active: `rust-central` (`stack=rust`, `ci.yml`) and `hygiene-central`
  (`stack=other`, `hygiene.yml`), both pinned to v3.0.0's commit.
- Kept for now: `rust-ci-required` and `hygiene-required`, and each
  repository's `ci.yml` caller, which still carries the SARIF and Codecov
  uploads the ruleset path does not make.
- Still to do: the uploads' future (a ruleset run with `security-events` and
  `id-token`, or a central job), then dropping the callers and the old
  rulesets; step 5 (`rust-gate setup`).
- Step 6 is `quality-sync.yml`'s `repin` job. It moves the rulesets before the
  sync pull requests, not after: the managed-files check runs from the
  rulesets' pin, so a sync pull request checked by the previous release fails,
  and a ruleset update does not re-run it.

### Step 4 done (2026-09-25, v4.0.0)

rust-workflows v4.0.0 uploads the SARIF and coverage from the central check
(rust-workflows#67), and its `rust-gate sync` deletes each repository's
`ci.yml` caller. `rust-central` and `hygiene-central` run v4.0.0;
`rust-ci-required` and `hygiene-required` are deleted, with the Rust and
hygiene CI templates, and the `stack` description names the central rulesets.

[rules]: https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-workflows-to-pass-before-merging
[troubleshoot]: https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/troubleshooting-rules#troubleshooting-ruleset-workflows
[rest]: https://docs.github.com/en/rest/orgs/rules
[contexts]: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#job-context
[billing]: https://docs.github.com/en/billing/concepts/product-billing/github-actions
[secure]: https://docs.github.com/en/actions/reference/security/secure-use
[events]: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflows-in-forked-repositories
