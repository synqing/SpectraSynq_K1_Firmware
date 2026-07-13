---
title: Agent stack — standard stack v1 promotion (Phase 6)
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/PHASED-ROLLOUT.md § Phase 6
  - docs/agent-stack/ACTIONABLE-TASKS.md P6-01..P6-06
  - knowledge/research/phase6-scorecard.md
  - Captain ratification 2026-07-13 (autonomous promotion doc; no tool installs beyond allowlist)
owner: knowledge-curator
---

# Decision: SpectraSynq standard agent stack v1 (P6-06)

## Context

Phases 0–5 of the agent-stack rollout completed between 2026-07-13 with recorded exit
gates. Phase 6 consolidates evidence into a single **standard stack manifest** for all
SpectraSynq repos. Captain ratified **autonomous promotion documentation** on 2026-07-13 —
**not** new tool installs beyond the existing allowlist.

## Decision

### Ships in standard stack v1 (ADOPT)

| Component | Phase | Rationale |
|-----------|-------|-----------|
| **Herdr** | 1 | Operator visibility; workspace live; AGPL scoped to operator machine |
| **Codex plugin (manual)** | 1 | Cross-tool review/adversarial; `reviewGateEnabled: false` verified |
| **sqlite-utils** | 1 | Read-only operator DB inspection |
| **OpenKnowledge MCP** | 2–3 | `@inkeep/open-knowledge@0.29.1` project-scoped; maturity risk accepted |
| **`knowledge/` scaffold** | 2 | Markdown-in-git authoritative; MCP optional accelerator |
| **Claude-mem coexistence** | 3 | Episodic recall; promotion-not-sync enforced |
| **Routing + promote-learning skills** | 3 | Tests 1–3 PASS; P3-07 zero auto-sync audit PASS |

Canonical manifest: [`docs/agent-stack/STANDARD-STACK.md`](../../docs/agent-stack/STANDARD-STACK.md).

### Closed pilots (not promoted)

| Tool | Outcome | Binding rule |
|------|---------|--------------|
| **Entire** | Phase 4 PASS **with debt** | Local-only pilot may continue; **not** standard stack; `entire rewind` deferred |
| **Ruflo** | Orchestration-only PASS in isolated worktree | Pilot **closed**; **never** `ruflo init` on main `lane/*` firmware branches |

### Deferred

| Item | Condition to revisit |
|------|---------------------|
| **Headroom compression** | P5-05 remains **no promote**; human P5-04 replay + new decision required |
| **Entire live lineage** | Entire CLI upgrade beyond npm `0.0.3` (enable: `entire enable --agent claude-code`) |
| **Second-repo OpenKnowledge** | P6-04 when Captain scopes sibling repo |

### Rejected (permanent unless Captain reopens)

- **pxpipe** — silent corruption
- **OmniRoute primary** — lab only
- **Ruflo full init** — memory/routing/daemon/federation
- **Claude-mem → OpenKnowledge auto-sync** — violates curation model
- **Codex auto stop-gate** — global intercept forbidden

## Exit criteria evidence (Phase 6)

| Task | Evidence | Status |
|------|----------|--------|
| P6-01 scorecard | [`phase6-scorecard.md`](../research/phase6-scorecard.md) | **DONE** |
| P6-02 manifest | [`STANDARD-STACK.md`](../../docs/agent-stack/STANDARD-STACK.md) | **DONE** |
| P6-03 AGENT_OS pointer | `AGENT_OS.md` §2 agent-stack table | **DONE** |
| P6-04 second repo | Not in autonomous scope | **DEFERRED** |
| P6-05 onboarding runbook | [`runbooks/agent-onboarding.md`](../runbooks/agent-onboarding.md) | **DONE** |
| P6-06 Captain sign-off | This decision (2026-07-13) | **DONE** |

## Rollback trigger

- Auto-sync pipeline discovered → disable OK MCP; revert to `AGENT_OS.md` + claude-mem only
- Standard-stack component causes authority collision → demote to pilot in scorecard + update manifest
- OpenKnowledge breaking change without pin update → disable MCP; retain `knowledge/` git docs

## Related

- Scorecard: [`phase6-scorecard.md`](../research/phase6-scorecard.md)
- Rollout closure: [`PHASED-ROLLOUT.md`](../../docs/agent-stack/PHASED-ROLLOUT.md) § Phase 6
- Prior gates: Phase 3 [`agent-stack-phase3-exit-gate-2026-07-13.md`](./agent-stack-phase3-exit-gate-2026-07-13.md); Phase 4 [`agent-stack-phase4-exit-gate-2026-07-13.md`](./agent-stack-phase4-exit-gate-2026-07-13.md); Phase 5 [`agent-stack-headroom-partial-2026-07-13.md`](./agent-stack-headroom-partial-2026-07-13.md)
