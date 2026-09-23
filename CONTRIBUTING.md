# Contributing

This guide applies to every Orchestration-Maestro repository that does not ship
its own `CONTRIBUTING.md`. Where a repository has one, follow that instead.

## Before you start

- Search existing issues first. For a new idea, open an issue before a large
  pull request, so the direction is agreed before the work is done.
- Never include credentials, tokens, environment dumps or private data in an
  issue, a commit or a log. Report vulnerabilities privately, as described in
  [SECURITY.md](SECURITY.md).

## What every pull request passes

These rules are enforced by the organization for every repository; no one can
bypass them.

| Rule | What it means for you |
| --- | --- |
| Pull request required | Nothing reaches the default branch by a direct push |
| Squash merge only | One commit per pull request; its message is the pull request title |
| Conventional title | `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `build:`, `ci:`, `chore:`, `style:` or `revert:`, then a short summary |
| Signed commits | The default branch accepts only signed commits; GitHub signs the squash merge |
| Resolved conversations | Every review thread is resolved before merge |
| CodeQL | No new high or critical security alert and no CodeQL error |
| Rust CI | Rust repositories pass `rust / Required Rust CI` from [rust-workflows](https://github.com/Orchestration-Maestro/rust-workflows) |

Workflows from a first-time or external contributor wait for a maintainer's
approval before they run.

## Making the change

1. Fork the repository, or create a branch if you have write access.
2. Keep the change focused: one concern per pull request.
3. Add or update tests with any behaviour change.
4. Run the repository's own checks locally when it documents them.
5. Open the pull request with a conventional title and fill in the template.

## Conduct

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
