---
title: Agent stack — Phase 4 exit gate (pilots PASS with documented debt)
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/ACTIONABLE-TASKS.md P4-E01..P4-R08, P4-08
  - docs/agent-stack/PHASED-ROLLOUT.md § Phase 4 exit gate
  - knowledge/research/phase4-exit-gate-summary.md
  - Captain ratification 2026-07-13 (P4-08 autonomous go)
owner: knowledge-curator
---

# Decision: Phase 4 exit gate PASS with documented debt (P4-08)

## Context

Phase 4 scoped **isolated pilots** for Entire (commit provenance) and Ruflo (orchestration-only)
on `SpectraSynq_K1_Firmware`. P4-08 required composite Captain sign-off before Phase 5 entry
criteria treat Phase 4 as closed.

## Decision

1. **Phase 4 exit gate = PASS with documented debt** — Captain ratified **autonomous go** on 2026-07-13.
2. **Entire** — Continue local-only pilot (`--local --skip-push-sessions --telemetry=false`);
   P4-E01–E05 DONE; live `entire rewind` **unpromoted** (npm `entire-cli@0.0.3` hook CLI gap; enable via `entire enable --agent claude-code`
   gap in 0.0.3 + dual-path git hooks).
3. **Ruflo** — Orchestration-only pilot **COMPLETE** (P4-R01–R08); do **not** run `ruflo init` on
   main `lane/*` firmware branches; full swarm coordinate deferred.
4. **Phase 5 entry** — Headroom **compression-only** benchmark may proceed **autonomously** per `PHASED-ROLLOUT.md` § Phase 5 and `AUTHORITY-CONTRACT.md` § Benchmark later (no Captain spend gate).

## Exit criteria evidence

| Criterion | Evidence | Status |
|-----------|----------|--------|
| Entire enable + boundaries | [`phase4-entire-pilot-proof.md`](../research/phase4-entire-pilot-proof.md) | **PASS** |
| Entire 5-session lineage (shell) | [`phase4-entire-lineage-proof.md`](../research/phase4-entire-lineage-proof.md) | **PASS** (deferred `rewind`) |
| Entire Captain go | [`agent-stack-entire-hooks-dual-path.md`](./agent-stack-entire-hooks-dual-path.md) | **PASS** |
| Ruflo forbidden-features absent | [`phase4-ruflo-pilot-proof.md`](../research/phase4-ruflo-pilot-proof.md) §3 | **PASS** |
| Ruflo Eval 1–3 + scorecard | Same proof §4–§10 | **PASS** |
| Ruflo teardown | Same proof §11 | **PASS** |
| Composite sign-off | P4-08; this decision | **PASS** |

## Documented debt (non-blocking)

- Entire live checkpoint lineage (`entire rewind` ≥1 point) — follow-up when Entire CLI > npm `0.0.3`; pilot enable path documented.
- Entire Codex agent enable — not in `entire-cli@0.0.3`.
- Ruflo full swarm/API execution — out of orchestration-only pilot scope.

## Rollback trigger

- Entire remote session push enabled → **disable** (`entire disable`) and revert hooks ADR.
- Ruflo daemon/memory on main firmware lane → **stop**; remove artifacts; re-run P4-R03 checklist.
- Either tool promoted without Phase 6 standard-stack manifest → **reject** per authority contract.

## Related

- Canonical summary: [`phase4-exit-gate-summary.md`](../research/phase4-exit-gate-summary.md)
- Phase 3 exit (prerequisite): [`agent-stack-phase3-exit-gate-2026-07-13.md`](./agent-stack-phase3-exit-gate-2026-07-13.md)
