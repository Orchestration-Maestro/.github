# Orchestration-Maestro organization

The organization's settings as code, its public profile, and the files and
checks that hold every repository to one standard.

## Language

**Stack**:
The `stack` custom property: `rust`, `other` or `workflows`. Rulesets and the
sync choose what applies to a repository by it.
_Avoid_: language, type

**Standard**:
What every repository holds: a `stack`, the files `rust-gate sync` manages,
and the file baseline.
_Avoid_: template, policy

**Managed file**:
A file `rust-gate sync` writes and keeps current, such as `.editorconfig` or
the CI caller. Nobody edits one by hand.
_Avoid_: generated file, synced config

**File baseline**:
The files every repository keeps of its own because GitHub never inherits
them, listed in `scripts/repository-drift.py`.
_Avoid_: required files, checklist

**Default**:
A community file this repository gives every repository without one of its
own: `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SUPPORT.md`, the
pull request template and the issue forms. A repository keeps its own copy
only for a need of its own.
_Avoid_: inherited file, org file

**Drift**:
A difference between GitHub and `org/`, or between a repository and the
standard. The drift check reports it in an issue; a person resolves it.
_Avoid_: deviation, violation

**Sync pull request**:
The pull request from `maestro/sync` that `quality-sync.yml` opens in a
repository when `rust-workflows` releases.

**Export**:
`org/`: the organization's live settings as `scripts/export-org.py` reads
them.
_Avoid_: backup, snapshot
