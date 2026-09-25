# Northstar for `.github`

> Automate the guardrails to deliver faster, with higher quality, and more
> securely.

`.github` steers by the organization's
[Northstar](https://github.com/Orchestration-Maestro/.github/blob/864d85597a833864cd8506c3925830503b3c2163/golden-rules/northstar.md):
one KPI per pillar, each with its measurement. Unmeasured is written `not
measured`, never estimated; a value read by hand carries the date it was read.

## The point

Every repository in the organization holds the same standard without anyone
checking by hand: settings are code, drift surfaces within a day, and a new
repository starts from defaults instead of copies.

## KPIs

| Pillar | KPI | Current | Target | Measured by |
| --- | --- | --- | --- | --- |
| Speed | Time from a rust-workflows release to every sync pull request | not measured | set from the first baseline | The `quality-sync.yml` run after the release event |
| Quality | Repositories off the standard | 2 (read 2026-09-24) | 0 | Open `Drift:` issues from the daily drift check |
| Maintainability | Settings changed by hand, outside `org/` | 0 (read 2026-09-24) | 0 | The weekly settings drift check |
| Security | Repositories without private vulnerability reporting | 0 (read 2026-09-24) | 0 | The enforced security configuration `maestrolabs-baseline` |
