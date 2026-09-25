# Constitution

Spec Kit, installed once beside the organization's checkouts, reads this page as
its constitution. It holds no rule of its own: the pages it points to do, and
they come first. When this page, a specification, a plan or a task disagrees
with them, they win and this page is the one to fix.

## What this is about

We build Maestro, an organizational agent platform that removes the plumbing
from agentic development while keeping every action governed and every answer
traceable: a catalog of agents, skills and workflows, a local runtime that runs
them under a host-owned policy broker, and a knowledge kernel that serves
source-backed evidence. [What Maestro is](https://github.com/Orchestration-Maestro/maestro-core/blob/main/docs/architecture/README.md#1-what-maestro-is) says it in
full; the [organization page](profile/README.md) lists the repositories.

## Who we are

| Page | What it sets |
| --- | --- |
| [Northstar](golden-rules/northstar.md) | The direction every repository steers by: four pillars, one KPI each |
| [Organization page](profile/README.md) | The Northstar, the golden rules and the repositories, on one page |
| [Brand](assets/README.md) | The mark, the avatar, the palette and the type |

## The rules

| Page | What it holds |
| --- | --- |
| [Engineering rules](golden-rules/engineering.md) | The foundations (FND), the named principles (P), the hard mandates (ENF) and the rules for adopting them (C); nothing overrides them |
| [Security rules](golden-rules/security.md) | The rules for people and agents alike (SEC) |
| [Standards](golden-rules/standards.md) | The standards the golden rules align with, each with its version and what it covers |
| [Gate rules](https://github.com/Orchestration-Maestro/rust-workflows/blob/main/docs/ci.md#every-rule) | Every rule the shared CI refuses, each with its ID; the organization page lists them as the latest release holds them |
| A repository's `docs/standards/` | Its rule map: what holds each rule there, or why it does not apply (C-001) |
| A repository's architecture and ADRs | What it builds and why; maestro-core's [architecture](https://github.com/Orchestration-Maestro/maestro-core/blob/main/docs/architecture/README.md) sets the product's principles |

## Our stack

What we build with. The
[technology matrix](https://github.com/Orchestration-Maestro/maestro-core/blob/main/docs/architecture/README.md#5-technology-matrix) holds every choice, its version,
the alternatives and why; this table only names them.

| Layer | What we use |
| --- | --- |
| Language | Rust, edition 2024, for everything first-party |
| Knowledge kernel | SQLite and content-addressed artifacts, the only authority; Qdrant and Neo4j as rebuildable projections |
| Models | Local llama.cpp models through [maestro-model-router](https://github.com/Orchestration-Maestro/maestro-model-router); GitHub Copilot as the explicit managed route |
| Agents and tools | GitHub Copilot's native catalog formats, MCP through rmcp, and an event-sourced workflow engine on the kernel journal |
| Guardrails | Cedar for authorization, Landlock and seccomp for the sandbox, JSON Schema for handoff contracts |

How we deliver it:

| Tool | What it does for us |
| --- | --- |
| [rust-workflows](https://github.com/Orchestration-Maestro/rust-workflows) | The shared CI every repository calls, and `rust-gate`, which holds the gate rules at commit and in CI |
| [Quality sync](README.md#quality-sync) | Every repository's managed files, rendered by `rust-gate sync` and moved to each rust-workflows release by a pull request |
| mise and prek | The pinned toolbelt `scripts/bootstrap.sh` installs, and the commit hooks, the same locally and in CI |
| [Spec Kit](https://github.com/github/spec-kit) | Specifications, plans and tasks, under each repository's `specs/NNN-*/`; installed once, never committed |
| [Organization settings](README.md#what-each-decision-is-for) | Rulesets, properties and security settings as code in `org/`, checked for drift every week |
| release-please | Versions and changelogs from conventional pull request titles (ENF-004) |

## How Spec Kit applies them

- A specification names the rules it touches by their IDs, and a plan says what
  holds each one there: a gate, a test or a review step, as the repository's
  rule map does (C-001).
- A plan and its tasks follow the foundations (FND).
- A departure from a rule is an exception as the
  [engineering rules](golden-rules/engineering.md#exceptions) set it out, never a
  local weakening (C-006).

A rule changes through a pull request to the page that holds it. This page
changes only when one of those pages moves or a new one joins.
