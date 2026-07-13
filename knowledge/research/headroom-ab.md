# Headroom compression A/B — Phase 5 archive

**Date:** 2026-07-13  
**Package:** `headroom-ai==0.31.0`  
**Interpreter (canonical):** `/tmp/headroom-bench-venv/bin/python3` — isolated `[ml]` venv on this host (Homebrew 3.12); **do not** use miniforge for Kompress  
**Scope:** Compression library only (no memory, learn, proxy, output shaping)  
**Exit gate (canonical):** [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md) · Decision: [`agent-stack-headroom-partial-2026-07-13.md`](../decisions/agent-stack-headroom-partial-2026-07-13.md)  
**Runbook:** [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md) · Kompress retest: [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md)

## Executive result

| Gate | Verdict | Evidence |
|------|---------|----------|
| Install | **PASS** | PyPI `headroom-ai[ml]==0.31.0` in `/tmp/headroom-bench-venv` |
| P5-01 protocol | **PASS** | [`phase5-headroom-benchmark-plan.md`](./phase5-headroom-benchmark-plan.md) |
| P5-02 baselines | **PASS** | 3 task types in [`phase5-ab-metrics.json`](./phase5-ab-metrics.json) |
| P5-03 compression variant | **PASS** | Harness ~81–83% on JSON; canaries 18/18; Kompress **UNBLOCKED** in isolated venv (session `bd2c1225`) |
| Identifier integrity (automated) | **PASS** | 18/18 canaries retained; full `git_head` on 3/3 tasks |
| Adversarial robustness (offline) | **PASS** | [`phase5-adversarial-eval.json`](./phase5-adversarial-eval.json) |
| P5-04 human quality | **PASS (automated)** / **DEFERRED (human)** | Automated canaries PASS; human task replay **DEFERRED** |
| P5-05 standard stack | **DEFERRED** | **No promote** — default unchanged |

**Phase 5 composite:** **PASS** — compression benchmark closed; standard-stack promotion **not** granted (P5-05 DEFERRED).

## A/B metrics table (P5-03)

| Task ID | Type | Tokens baseline | Tokens compressed | % saved | Identifiers |
|---------|------|-----------------|-------------------|---------|-------------|
| T-DEBUG | debug | 41,769 | 7,104 | 83.0% | OK |
| T-IMPLEMENT | implement | 37,846 | 7,098 | 81.3% | OK |
| T-REVIEW | review | 37,807 | 7,102 | 81.2% | OK |

**Harness:** [`scripts/agent/phase5-headroom-ab.py`](../../scripts/agent/phase5-headroom-ab.py)

Reproduce: `/tmp/headroom-bench-venv/bin/python3 scripts/agent/phase5-headroom-ab.py` (see runbook).

## Host environment (this machine)

| Env | Kompress | Notes |
|-----|----------|-------|
| `~/miniforge3` | **BLOCKED** | `torchaudio` metadata / `transformers` import failure (sessions `dc9e23a7`, `6e3211e1`) |
| `/tmp/headroom-bench-venv` | **UNBLOCKED** | `is_kompress_available() → True`; full `compress()` — session `bd2c1225` |

Prior ~50% TextCrusher-only path is **archived**, not the Phase 5 exit criterion.

## Adversarial eval (offline)

```bash
/tmp/headroom-bench-venv/bin/headroom evals adversarial --json-output knowledge/research/phase5-adversarial-eval.json
```

## Note on payload shape

Markdown-only `<tool_result>` bodies at modest size may show **0%** `compress()` savings. This benchmark uses **structured JSON tool returns** (router/mixed), matching high-volume agent tool traffic.

## Forbidden features — not exercised

`headroom memory`, `headroom learn`, `headroom proxy`, `headroom mcp`, output-savings, provider wrap.

## Go / no-go (P5-05 preliminary)

| Option | Recommendation |
|--------|----------------|
| Promote to standard stack | **NO** |
| Archive benchmark | **YES** |
| Human P5-04 replay | **DEFERRED** — before any promotion debate |

## Related

- Exit summary: [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md)
- Results archive: [`phase5-headroom-benchmark-results.md`](./phase5-headroom-benchmark-results.md)
- Plan: [`phase5-headroom-benchmark-plan.md`](./phase5-headroom-benchmark-plan.md)

## Evidence reconciliation

| Session | Outcome | Role |
|---------|---------|------|
| `dc9e23a7` | TextCrusher ~50%; Kompress probe failed | First attempt — **not** exit verdict |
| `6e3211e1` | Kompress blocked on shared miniforge | Superseded by isolated venv |
| `58e73eb7` | Harness ~81% PASS | Canonical harness pass |
| `bd2c1225` | Kompress UNBLOCKED in `/tmp/headroom-bench-venv` | Host env proof — [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md) |
| 2026-07-13 tiebreaker | Re-run harness; metrics refreshed | [`phase5-ab-metrics.json`](./phase5-ab-metrics.json) |
