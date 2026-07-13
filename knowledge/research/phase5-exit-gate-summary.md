---
title: Phase 5 exit gate — summary
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/PHASED-ROLLOUT.md § Phase 5
  - docs/agent-stack/ACTIONABLE-TASKS.md § Phase 5
  - knowledge/research/phase5-headroom-benchmark-plan.md
  - knowledge/research/headroom-ab.md
  - knowledge/research/phase5-ab-metrics.json
  - knowledge/research/phase5-adversarial-eval.json
  - knowledge/runbooks/headroom-compression-benchmark.md
  - knowledge/research/phase5-headroom-kompress-retest.md
owner: knowledge-curator
---

# Phase 5 exit gate summary

**Theme:** Headroom **compression-only** benchmark (no memory, learn, proxy, instruction writes).  
**Exit date:** 2026-07-13  
**Verdict:** **PASS** — compression-only benchmark closed (canaries intact, ~81–83%); isolated `/tmp/headroom-bench-venv` for `[ml]` on this host; **standard-stack promotion DEFERRED** (P5-05)

---

## Composite verdict

| Track | Task range | Status | Outcome |
|-------|------------|--------|---------|
| **Protocol + baselines** | P5-01, P5-02 | **DONE** | Three task archetypes (debug / implement / review) |
| **Compression A/B** | P5-03 | **DONE** | `compress()` harness PASS ~81–83% on JSON tool payloads ([`phase5-headroom-benchmark-results.md`](./phase5-headroom-benchmark-results.md) § reconciliation) |
| **Quality review** | P5-04 | **PASS (automated)** / **DEFERRED (human)** | Automated canary integrity **3/3 PASS**; human qualitative review **DEFERRED** |
| **Standard stack** | P5-05 **CLOSED (no promote)** — compression benchmark PASS; operational qualification pending; not standard stack.
| **Phase 5 composite** | P5-01..05 | **PASS** | Phase 6 entry unblocked; Headroom **not** promoted until P5-05 closes |

Phase 5 is **not** a production adoption gate. It proves compression-only scope stayed isolated, forbidden Headroom features were not invoked, Standard-stack promotion remains blocked (P5-05 DEFERRED) until P5-04 human review; Kompress ONNX breakdown is optional follow-up debt.

---

## Task ledger

| ID | Deliverable | Result | Evidence |
|----|-------------|--------|----------|
| P5-01 | A/B protocol (compression-only) | **DONE** | [`phase5-headroom-benchmark-plan.md`](./phase5-headroom-benchmark-plan.md) |
| P5-02 | Baseline metrics (3 task types) | **DONE** | [`phase5-ab-metrics.json`](./phase5-ab-metrics.json) — T-DEBUG, T-IMPLEMENT, T-REVIEW |
| P5-03 | Headroom compression variant | **DONE** | [`headroom-ab.md`](./headroom-ab.md); harness [`scripts/agent/phase5-headroom-ab.py`](../../scripts/agent/phase5-headroom-ab.py) |
| P5-04 | Quality review | **PASS (automated)** / **DEFERRED (human)** | Automated canaries 18/18 retained (3/3 tasks); human task-outcome review **DEFERRED** |
| P5-05 | Go/no-go for standard stack | **DEFERRED** | [`agent-stack-headroom-partial-2026-07-13.md`](../decisions/agent-stack-headroom-partial-2026-07-13.md) — **no promote** |

---

## A/B metrics (authoritative JSON)

`git_head_at_run`: `e67da587c78c31a3c056a8dfab74fe8e5a5708f2`  
Package: `headroom-ai==0.31.0`

| Task ID | Type | Tokens baseline | Tokens compressed | % reduction | Identifier check |
|---------|------|-----------------|-------------------|-------------|------------------|
| T-DEBUG | debug | 41,769 | 7,104 | 83.0% | PASS |
| T-IMPLEMENT | implement | 37,846 | 7,098 | 81.3% | PASS |
| T-REVIEW | review | 37,807 | 7,102 | 81.2% | PASS |

**Method:** Synthetic multi-file JSON tool payloads from `knowledge/` + `docs/agent-stack/`. Variant B = library `compress(..., optimize=True)` with `CompressConfig(protect_recent=0, protect_analysis_context=False)`. Transforms observed: `router:protected:user_message`, `router:mixed`.

**Caveat:** Prose/log bodies are summarized aggressively. Automated checks prove **substring/canary survival**, not semantic equivalence for live debugging.

---



## Evidence reconciliation (superseded PARTIAL / Kompress-blocked docs)

| Pass | Session / ref | Outcome | Notes |
|------|---------------|---------|-------|
| **First attempt** | `dc9e23a7` | **ARCHIVED** | Kompress probe failed on shared env; TextCrusher-only ~50% — **not** exit verdict |
| **Miniforge probe** | `6e3211e1` | **BLOCKED (host)** | Kompress ONNX unavailable on `~/miniforge3`; superseded |
| **Canonical harness** | `58e73eb7` | **PASS** | [`scripts/agent/phase5-headroom-ab.py`](../../scripts/agent/phase5-headroom-ab.py); **~81%** on structured JSON; 18/18 canaries |
| **Isolated venv retest** | `bd2c1225` | **UNBLOCKED** | `/tmp/headroom-bench-venv` + `headroom-ai[ml]==0.31.0`; `is_kompress_available() → True` — [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md) |
| **Tiebreaker** | 2026-07-13 | **PASS** | Re-run: `/tmp/headroom-bench-venv/bin/python3 scripts/agent/phase5-headroom-ab.py` → [`phase5-ab-metrics.json`](./phase5-ab-metrics.json); runbook [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md) |

**Authority:** Harness PASS (~81–83%, compression-only, canaries intact) closes P5-03. Phase 5 composite **PASS** with P5-05 **CLOSED (no promote); operational qualification pending**. Human P5-04 remains open but does not downgrade composite to PARTIAL.

## Host dependency note (Kompress ONNX)

**Shared miniforge (`~/miniforge3`):** Kompress probe failed (`transformers` / broken `torchaudio` metadata) — sessions `dc9e23a7`, `6e3211e1`. **Do not** use miniforge for Phase 5 harness on this host.

**Isolated venv (canonical on this machine):** `/tmp/headroom-bench-venv` (Homebrew Python 3.12, `pip install 'headroom-ai[ml]==0.31.0' onnxruntime`). Session `bd2c1225`: `is_kompress_available() → True`; full harness PASS — see [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md) and [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md).

Exit criterion: **~81–83%** token reduction on structured JSON tool payloads with **18/18 automated canaries** retained (compression-only scope). Optional follow-up: explicit Kompress vs router breakdown before promotion debate (non-blocking).

---

## Adversarial robustness (offline)

```bash
headroom evals adversarial --json-output knowledge/research/phase5-adversarial-eval.json
```

Seven payload classes × 30 cells; **no** class beat benign baseline or suppressed compression. Instruction-override / fake-system-tag survival tracked at 93–100% (see JSON).

---

## Forbidden scope — confirmed not used

`headroom memory`, `learn`, `proxy`, `wrap`, `mcp` (live), output-savings dashboards, OmniRoute, AGENTS.md / instruction writes.

---

## Exit gate criteria (composite)

| Criterion | Status | Notes |
|-----------|--------|-------|
| Compression-only protocol published | **PASS** | P5-01 |
| Three task types measured | **PASS** | P5-02 |
| A/B table with tokens + integrity | **PASS** | P5-03 — harness `compress()` on JSON payloads |
| Quality review 3/3 acceptable | **PASS (automated)** | P5-04 — human task replay **DEFERRED** |
| Go/no-go for standard stack | **DEFERRED** | P5-05 — **no promote** |
| Composite Phase 5 sign-off | **PASS** | Compression benchmark closed; promotion deferred |

---

## Documented debt (non-blocking)

1. **P5-04 human qualitative review** — No live LLM task replay with compressed context; Captain/reviewer eyes on real task outcomes still open.
2. **Kompress ONNX path** — Host deps error on dc9e23a7 probe only; optional explicit Kompress A/B not required for P5-03 PASS.
3. **Plain-text tool payloads** — Smaller grep-style payloads may report 0% reduction (router no-op); benchmark uses tool-heavy JSON representative of structured returns.

---

## Authority model (post Phase 5)

```
Git history / PR truth     → source of record (unchanged)
knowledge/ markdown        → OpenKnowledge pilot (Phase 2–3)
Claude-mem                 → episodic recall (Phase 3 routing)
Headroom                   → compression-only benchmark evidence; NOT in standard stack
Human checkpoint           → Herdr + Captain
```

**Forbidden (unchanged):** Headroom memory/learn/proxy; standard-stack promotion without Phase 6 manifest + P5-04 PASS.

---

## Next phase pointer

Phase 6 — Evaluation gates & promotion to standard stack. See
[`PHASED-ROLLOUT.md`](../../docs/agent-stack/PHASED-ROLLOUT.md) § Phase 6.

Headroom enters Phase 6 scorecard as **benchmark PASS / no promote** until P5-05 closes (P5-04 human review still open).

---

## Artifact reconciliation (2026-07-13)

| Artifact | Role |
|----------|------|
| [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md) | **Canonical** Phase 5 exit gate (this file) |
| [`headroom-ab.md`](./headroom-ab.md) | Detailed A/B archive + host blocker notes |
| [`phase5-headroom-benchmark-plan.md`](./phase5-headroom-benchmark-plan.md) | Protocol (P5-01) |
| [`phase5-ab-metrics.json`](./phase5-ab-metrics.json) | Machine-readable metrics |
| [`phase5-headroom-benchmark-results.md`](./phase5-headroom-benchmark-results.md) | Detailed metrics + dc9e23a7 first-attempt archive |
| [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md) | Reproduce harness (isolated venv) |
| [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md) | Kompress UNBLOCKED proof (`bd2c1225`) |
