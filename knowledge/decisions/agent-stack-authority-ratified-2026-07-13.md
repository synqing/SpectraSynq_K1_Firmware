---
title: Agent Stack Authority Contract — Captain Ratification
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/AUTHORITY-CONTRACT.md
  - docs/agent-stack/PHASED-ROLLOUT.md
  - Captain ratification 2026-07-13 (explicit approval of agent stack rollout plan)
owner: Captain
---

# Agent Stack Authority Contract — Ratified

## Decision

Captain has **approved and ratified** the SpectraSynq agent stack rollout plan and
[`docs/agent-stack/AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md)
as the binding authority model for cross-tool agent infrastructure in this repo and
sibling SpectraSynq workspaces.

## Scope

- Governs **agent tooling and knowledge** (Herdr, Codex plugin, OpenKnowledge,
  Claude-mem coexistence, Entire pilot, Ruflo pilot, Headroom benchmark).
- Does **not** supersede [`AGENT_OS.md`](../../AGENT_OS.md) for firmware safety gates,
  build discipline, or lane verification.

## Phase 0 exit

| Criterion | Status |
|-----------|--------|
| Authority contract ratified | **PASS** — this document |
| OpenKnowledge maturity risk documented | **PASS** — [`agent-stack-openknowledge-maturity.md`](./agent-stack-openknowledge-maturity.md) |
| Promotion workflow defined | **PASS** — [`SWARM-ORCHESTRATION.md`](../../docs/agent-stack/SWARM-ORCHESTRATION.md) § Promotion |
| Phase 0 docs-only (no global tool installs) | **PASS** |

## Rollout outcome (2026-07-13)

Phases 0–6 **DONE** — standard stack v1 promoted. Canonical manifest:
[`STANDARD-STACK.md`](../../docs/agent-stack/STANDARD-STACK.md). Closure note:
[`agent-stack-rollout-complete-2026-07-13.md`](../research/agent-stack-rollout-complete-2026-07-13.md).
