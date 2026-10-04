# One shared Rust CI at Pi's level

Spec approved by the owner on 2026-10-04. Its tickets are GitHub issues in this
repository, and each one links here.

## Problem Statement

Every Rust repository in the organization runs one shared CI. It has grown far
past what the work needs:

- one workflow file of 1,626 lines with 13 jobs;
- a 26,688-line program, `rust-gate`, with 46 steps and 25,401 lines of tests;
- a settings file in every repository, `maestro-quality.toml`.

Pi, the reference for how Maestro is built, runs one workflow file of 62 lines
with 2 jobs. Our checks are slow, files drift between repositories, and each
repository carries custom settings the owner wants gone.

## Solution

One small shared CI at Pi's level, used by every Rust repository, with nothing
copied into each repository:

| Check | Command | Systems |
| --- | --- | --- |
| Format | `cargo fmt --all --check` | Linux |
| Lint: any warning fails | `cargo clippy --workspace --all-targets --locked -- -D warnings` | Linux |
| Tests | `cargo test --workspace --locked` | Linux, macOS, Windows |

It runs on every pull request and every push to `main`, and it takes no
settings.

The old CI is archived, not deleted. The old repository is renamed
`maestro-rust-workflows-v4` and archived, and a fresh `maestro-rust-workflows`
starts at version 0.1.0.

## User Stories

1. As the owner, I want every Rust repository checked the same way, so that
   nothing drifts between repositories.
2. As the owner, I want CI at Pi's level, so that checks finish fast and stay
   simple.
3. As the owner, I want no custom settings file in each repository, so that
   adopting the CI needs only standard Rust files.
4. As the owner, I want the old CI archived, not deleted, so that every past
   version stays readable.
5. As a repository maintainer, I want unformatted code to fail CI, so that
   formatting never comes up in review.
6. As a repository maintainer, I want any Clippy warning to fail CI, so that
   warnings never pile up.
7. As a repository maintainer, I want tests on Linux, macOS and Windows, so that
   code that touches files and processes works on all three.
8. As a repository maintainer, I want my repository's own rules, such as a crate
   map or banned calls, to run as normal tests or from `clippy.toml`, so that
   they need no CI setting.
9. As an agent working in a repository, I want the same three commands locally
   as in CI, so that a green local run predicts a green CI run.
10. As the owner, I want GitHub's own secret scanning and Dependabot alerts to
    cover secrets and vulnerable dependencies, so that no workflow repeats them.
11. As a maintainer of a non-Rust repository, I want the old hygiene check
    switched off, so that an archived program never blocks my pull requests.
12. As the owner, I want the organization's own automation to stop running the
    old program, so that archiving it breaks nothing.
13. As the owner, I want the organization rules to run the new CI by version
    tag, so that a CI change reaches every repository in one step.
14. As a reviewer, I want each ticket proved by its own checks, so that I can
    approve one ticket at a time.

## Implementation Decisions

- **One shared workflow file** in `maestro-rust-workflows`. It runs in every
  repository tagged `stack=rust`, through the organization rules `rust-central`
  and `rust-slices`.
- **Actions:** the organization allows GitHub's own actions, its own
  repositories and three named actions. The workflow uses `actions/checkout`
  and `actions/cache`, and installs the toolchain with `rustup`.
- **Versions:** the new repository starts at 0.1.0 and releases with
  release-please. The organization rules pin a version tag, and the repin job in
  this repository moves them on each release.
- **The new repository** runs Matt Pocock's skills setup and keeps its own
  required checks: a self-test of the shared workflow.
- **This repository:**
  - the sync that writes managed files into every repository stops;
  - the list of gate rules on the organization page goes;
  - the repin job stays and follows the new repository;
  - the organization rule `hygiene-central` is switched to disabled, not
    deleted.
- **Archive:** the old repository is renamed `maestro-rust-workflows-v4` and
  archived. GitHub doesn't redirect workflow calls to a renamed repository, and
  its redirects stop once the old name is reused. Nothing may call the old
  repository by name when it is renamed.
- **Other repositories:**
  - `maestro-model-router` drops `maestro-quality.toml`, `scorecard.yml` and
    `dependabot-auto-merge.yml`. The files stay in its history, and its own
    workflow stays.
  - `maestro-release-canary` is archived: its only job was to prove the old
    release path.
  - `maestro-core` is frozen. Its CI was disabled on 2026-10-04.

## Testing Decisions

- **One seam:** the shared workflow file, run on a repository. Nothing inside it
  is tested on its own.
- **Proof on samples:** a small sample crate passes the workflow on all three
  systems. Three broken copies each fail at the right check:
  - an unformatted copy fails the format check;
  - a copy with a Clippy warning fails the lint check;
  - a copy with a failing test fails the test check.
- **Proof on a real repository:** a pull request on `maestro-model-router`
  passes the new CI.
- **Prior art:** the old repository's "Consumer CI" job ran the shared workflow
  on fixture repositories the same way.

## Out of Scope

- The Maestro engine and its repository.
- Rewriting `maestro-model-router` on mistral.rs.
- A replacement for the hygiene check: the non-Rust repositories keep the
  organization rules and GitHub's own scanning.

## Further Notes

- **The tickets, in order:**
  1. The organization stops depending on the old program.
  2. The fresh `maestro-rust-workflows` 0.1.0 proves the new CI.
  3. The organization rules run the new CI, and the old repository is archived.
  4. `maestro-model-router` runs the new CI cleanly, and the canary is
     archived.
- **Effort:** about 6–11 hours for one lane, plus one review. This is an
  estimate, not a measurement.
