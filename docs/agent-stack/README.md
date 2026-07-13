# Agent Stack Rollout

**Rollout:** **COMPLETE** (standard stack v1, 2026-07-13)  
**Canonical manifest:** [`STANDARD-STACK.md`](./STANDARD-STACK.md) — adopted tools, pins, forbidden paths  
**Status:** Phase 0 **ratified** (2026-07-13) · Phase 1 **DONE** · Phase 2 **DONE** (2026-07-13) · Phase 3 **DONE** (exit gate 2026-07-13) · Phase 4 **DONE** (exit gate 2026-07-13) · Phase 5 **DONE** (compression PASS; promotion DEFERRED) · Phase 6 **DONE** (standard stack v1 2026-07-13)

Cross-tool agent infrastructure for SpectraSynq: Herdr, Codex plugin, OpenKnowledge,
Claude-mem coexistence, Entire provenance, Ruflo orchestration pilot, Headroom benchmark.

## Phase status

| Phase | Status | Notes |
|-------|--------|-------|
| 0 — Authority contract | **PASS** | [`knowledge/decisions/agent-stack-authority-ratified-2026-07-13.md`](../../knowledge/decisions/agent-stack-authority-ratified-2026-07-13.md) |
| 1 — Herdr, Codex, sqlite-utils | **DONE** | Operational exit 2026-07-13; P1-08 adversarial archived; contract remediation in [`phase1-p1-08-contract-remediation.md`](../../knowledge/research/phase1-p1-08-contract-remediation.md) |
| 2 — OpenKnowledge pilot | **DONE** | Exit gate 2026-07-13 — [`phase2-openknowledge-mcp-proof.md`](../../knowledge/research/phase2-openknowledge-mcp-proof.md); Captain go [`agent-stack-openknowledge-pilot-go-2026-07-13.md`](../../knowledge/decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md) |
| 3 — Coexistence | **DONE** | Exit gate 2026-07-13 — [`agent-stack-phase3-exit-gate-2026-07-13.md`](../../knowledge/decisions/agent-stack-phase3-exit-gate-2026-07-13.md); summary [`phase3-exit-gate-summary.md`](../../knowledge/research/phase3-exit-gate-summary.md) |
| 4 — Entire + Ruflo pilots | **DONE** | Exit gate 2026-07-13 — [`agent-stack-phase4-exit-gate-2026-07-13.md`](../../knowledge/decisions/agent-stack-phase4-exit-gate-2026-07-13.md); summary [`phase4-exit-gate-summary.md`](../../knowledge/research/phase4-exit-gate-summary.md) |
| 5 — Headroom benchmark | **DONE** | Compression PASS; P5-05 no promote — [`phase5-exit-gate-summary.md`](../../knowledge/research/phase5-exit-gate-summary.md) |
| 6 — Standard stack | **DONE** | [`STANDARD-STACK.md`](./STANDARD-STACK.md) v1 — [`phase6-scorecard.md`](../../knowledge/research/phase6-scorecard.md) |

**Single ledger:** [`knowledge/current-priorities.md`](../../knowledge/current-priorities.md) mirrors this table.

## Read order

1. [`STANDARD-STACK.md`](./STANDARD-STACK.md) — **adopted tools, pins, forbidden paths** (v1)
2. [`AUTHORITY-CONTRACT.md`](./AUTHORITY-CONTRACT.md) — what owns what; forbidden paths (**ratified**)
3. [`PHASED-ROLLOUT.md`](./PHASED-ROLLOUT.md) — phases 0–6, gates, rollback, Week 1–2 order
4. [`ACTIONABLE-TASKS.md`](./ACTIONABLE-TASKS.md) — numbered backlog (P0-01 … P6-06)
5. [`SWARM-ORCHESTRATION.md`](./SWARM-ORCHESTRATION.md) — roles, Herdr/Ruflo/Codex, promotion workflow

## Knowledge pilot

Durable curated knowledge lives in [`knowledge/`](../../knowledge/) (**standard stack v1** — OpenKnowledge MCP optional; Markdown authoritative).
Routing skill: `.cursor/skills/knowledge-memory-routing/SKILL.md` (mirrored in `.claude/skills/`).
Onboarding: [`knowledge/runbooks/agent-onboarding.md`](../../knowledge/runbooks/agent-onboarding.md).

## Core rule

**Promotion, not synchronization.** Claude-mem observations promote to OpenKnowledge only
after reviewed acceptance with `status: verified` frontmatter. Never auto-dump session history into curated knowledge.

## Permanent rejections

- pxpipe (silent exact-value corruption)
- OmniRoute as primary engineering gateway (silent heterogeneous fallback)
- Codex plugin auto stop-gate (global)
- Ruflo full init (`--all-agents`, `--dual`, daemon autostart, memory/RAG)

## Parent governance

[`AGENT_OS.md`](../../AGENT_OS.md) remains canonical for firmware session rules.
This directory governs **agent-stack rollout** (lane-orthogonal to firmware branches).
Ratified contract applies from Phase 0 exit.
