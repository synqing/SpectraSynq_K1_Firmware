---
title: Agent stack — Phase 5 Headroom partial exit (no standard-stack promotion)
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/ACTIONABLE-TASKS.md P5-01..P5-05
  - docs/agent-stack/PHASED-ROLLOUT.md § Phase 5 exit gate
  - knowledge/research/phase5-exit-gate-summary.md
  - knowledge/research/headroom-ab.md
  - knowledge/research/phase5-ab-metrics.json
  - knowledge/runbooks/headroom-compression-benchmark.md
  - knowledge/research/phase5-headroom-kompress-retest.md
owner: knowledge-curator
---

# Decision: Phase 5 Headroom partial exit — compression-only; no promote (P5-05)

## Context

Phase 5 scoped an **isolated Headroom compression-only** benchmark on
`SpectraSynq_K1_Firmware`. Scope excluded memory, learn, instruction writes,
output shaping, and provider routing per [`AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md)
§ Benchmark later and [`agent-stack-autonomous-execution.md`](./agent-stack-autonomous-execution.md).


Autonomous harness runs produced protocol docs, A/B metrics, adversarial eval, and
automated canary integrity checks. Evidence passes were reconciled:

1. **Early host probe** (`dc9e23a7`) — Kompress ONNX availability check failed on shared miniforge (`transformers` /
   `torchaudio` / `importlib_metadata`); TextCrusher fallback ~50% on tool bodies.
2. **Miniforge follow-up** (`6e3211e1`) — Kompress still **blocked** on `~/miniforge3`; superseded for harness runs.
3. **Canonical harness** (`58e73eb7`) — `headroom.compress()` ~81% token reduction on structured JSON; 18/18 canaries.
4. **Isolated venv retest** (`bd2c1225`) — `/tmp/headroom-bench-venv` + `headroom-ai[ml]==0.31.0`: Kompress **UNBLOCKED**;
   reproduce via [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md) and
   [`phase5-headroom-kompress-retest.md`](../research/phase5-headroom-kompress-retest.md).

Human qualitative review (P5-04) was not completed.

## Decision

1. **Phase 5 composite exit = PASS** (compression benchmark; filename retained for audit) — P5-01..P5-03 closed with documented
   compression evidence; P5-04 automated **PASS**, human **DEFERRED**.
2. **P5-05 = CLOSED (no promote).** Headroom is **not** in the standard stack. Label: **compression benchmark PASS; operational qualification pending**. No further Headroom testing in rollout v1.
3. **Compression-only scope honored** — No Headroom memory, learn, proxy, wrap, or
   instruction-write paths were exercised.
4. **Kompress ONNX path** — blocked on miniforge (`6e3211e1`); **UNBLOCKED** in isolated venv (`bd2c1225`). Harness PASS does not require promotion.
5. **Phase 6 entry** — Unblocked; Headroom scorecard row **PASS (pilot closed)** — benchmark evidence archived; not rollout debt.

## Exit criteria evidence

| Criterion | Evidence | Status |
|-----------|----------|--------|
| P5-01 protocol | [`phase5-headroom-benchmark-plan.md`](../research/phase5-headroom-benchmark-plan.md) | **PASS** |
| P5-02 baselines | [`phase5-ab-metrics.json`](../research/phase5-ab-metrics.json) | **PASS** |
| P5-03 compression A/B | [`headroom-ab.md`](../research/headroom-ab.md); [`phase5-exit-gate-summary.md`](../research/phase5-exit-gate-summary.md) | **PASS** |
| P5-04 quality | Automated canaries 3/3; human review open | **PASS (automated)** / **DEFERRED (human)** |
| P5-05 go/no-go | This decision | **CLOSED (no promote)** |
| Composite sign-off | [`phase5-exit-gate-summary.md`](../research/phase5-exit-gate-summary.md) | **PASS** |

## Preliminary go/no-go (P5-05)

| Option | Outcome |
|--------|---------|
| Promote Headroom to standard stack | **NO** |
| Archive benchmark evidence in `knowledge/research/` | **YES** |
| Operational qualification (human replay) | **Pending** — out of scope for rollout v1 closure |

## Documented debt (non-blocking)

- P5-04 human qualitative review on live task outcomes.
- Kompress ONNX explicit A/B after host venv fix.
- Semantic equivalence not proven by substring canaries alone.

## Rollback trigger

- Headroom memory/learn/proxy enabled on Captain machine → **disable** and audit scope violation.
- Headroom promoted without Phase 6 `STANDARD-STACK.md` + Captain sign-off → **reject** per authority contract.
- Instruction writes via Headroom learn path → **stop** immediately.

## Related

- Canonical summary: [`phase5-exit-gate-summary.md`](../research/phase5-exit-gate-summary.md)
- Phase 4 exit (prerequisite): [`agent-stack-phase4-exit-gate-2026-07-13.md`](./agent-stack-phase4-exit-gate-2026-07-13.md)
- Autonomous allowlist: [`agent-stack-autonomous-execution.md`](./agent-stack-autonomous-execution.md)
