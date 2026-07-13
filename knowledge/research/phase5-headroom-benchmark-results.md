---
title: Phase 5 — Headroom compression-only benchmark results (superseded)
status: verified
last_verified: 2026-07-13
superseded_by: knowledge/research/phase5-exit-gate-summary.md
sources:
  - docs/agent-stack/ACTIONABLE-TASKS.md P5-01..P5-05
  - knowledge/research/phase5-headroom-benchmark-plan.md
  - knowledge/research/phase5-headroom-kompress-retest.md
  - knowledge/research/phase5-ab-metrics.json
owner: agent:cursor (autonomous Phase 5)
---

> **Canonical metrics + reconciliation (2026-07-13):** Exit gate summary [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md). **Composite = PASS** (compression benchmark); P5-05 promotion **DEFERRED**.

# Phase 5 Headroom benchmark — results (2026-07-13)

## Executive verdict

| Layer | Verdict | Notes |
|-------|---------|-------|
| **P5 install / package resolution** | **PASS** | PyPI `headroom-ai==0.31.0` (`headroom` CLI). npm `headroom-ai@0.22.4` is TypeScript SDK only (no CLI). Upstream org repo: `headroomlabs-ai/headroom` (same product family as `chopratejas/headroom` docs). |
| **P5-01 protocol** | **PASS** | [`phase5-headroom-benchmark-plan.md`](./phase5-headroom-benchmark-plan.md) |
| **P5-02 baselines** | **PASS** | Three archetypes (debug / implement / review) |
| **P5-03 compression A/B** | **PASS** | ~81–83% via harness `compress()` on JSON; Kompress verified in isolated venv ([`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md), session `bd2c1225`) |
| **P5-04 quality (automated)** | **PASS** | 18/18 canary strings + full `git_head` present post-compression (3/3 tasks) |
| **P5-04 quality (human / task outcome)** | **DEFERRED** | No live LLM task replay with compressed context in this run |
| **P5-05 standard-stack promotion** | **DEFERRED** | Preliminary **no promote** — default unchanged per rollout |
| **Phase 5 composite** | **PASS** | See [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md) |


## Evidence reconciliation — first attempt vs canonical harness

| Pass | Ref | Result | Detail |
|------|-----|--------|--------|
| First attempt | `dc9e23a7` | Probe **PARTIAL** | Kompress ONNX probe failed on miniforge deps; **TextCrusher-only** ~50% savings on tool bodies |
| Canonical | `58e73eb7` + tiebreaker | **PASS** | Harness `compress()` ~81–83% on JSON via miniforge router/mixed path |
| Kompress retest | `bd2c1225` | **PASS** | Full `[ml]` stack in `/tmp/headroom-bench-venv`; `is_kompress_available()` True — [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md) |

**Run (repo root) — canonical for Kompress:**

```bash
# see knowledge/runbooks/headroom-compression-benchmark.md
/tmp/headroom-bench-venv/bin/python3 scripts/agent/phase5-headroom-ab.py
```

Do **not** use miniforge for `[ml]` / Kompress on this host (broken `torchaudio` metadata). Miniforge without `[ml]` may still reproduce router/mixed metrics only.

## Install coordinates

| Channel | Package | Version | Role |
|---------|---------|---------|------|
| PyPI | `headroom-ai` | **0.31.0** | CLI + `from headroom import compress` |
| npm | `headroom-ai` | 0.22.4 | TS SDK import only (not used in this harness) |
| GitHub | `headroomlabs-ai/headroom` | main | Product/docs reference |

```bash
pip install 'headroom-ai==0.31.0'   # or existing miniforge install
headroom --version                  # 0.31.0
npm view headroom-ai version        # 0.22.4 (SDK)
```

## A/B metrics (P5-02 / P5-03)

Harness: [`scripts/agent/phase5-headroom-ab.py`](../../scripts/agent/phase5-headroom-ab.py)  
Artifact: [`phase5-ab-metrics.json`](./phase5-ab-metrics.json)  
`git_head_at_run`: `e67da587c78c31a3c056a8dfab74fe8e5a5708f2`

| Task ID | Type | Tokens baseline | Tokens compressed | % reduction | Identifier check |
|---------|------|-----------------|-------------------|-------------|------------------|
| T-DEBUG | debug | 41,769 | 7,104 | 83.0% | PASS |
| T-IMPLEMENT | implement | 37,440 | 7,098 | 81.0% | PASS |
| T-REVIEW | review | 37,509 | 7,104 | 81.1% | PASS |

**Method:** Synthetic multi-file tool JSON (knowledge + agent-stack excerpts + `phase5-adversarial-eval.json` grid + repeated build/log lines). **Variant B** = library `compress()` with `CompressConfig(protect_recent=0, protect_analysis_context=False)`. Transforms observed: `router:mixed` / SmartCrusher path on JSON.

**Plain-text grep payloads:** At smaller sizes, `compress()` may report **0%** reduction (router no-op). Benchmark uses **tool-heavy JSON** representative of structured tool returns.

## Integrity checks (paths / hashes)

- Full 40-char `git_head` retained in compressed tool body for all three tasks.
- Paths including `docs/agent-stack/AUTHORITY-CONTRACT.md`, `scripts/agent/session-bootstrap.sh`, env `k1_hardware`, chip id `F887A500` retained as substrings.
- **Caveat:** Prose and log bodies are summarized aggressively; automated check does not prove semantic equivalence for debugging.

## Adversarial robustness (offline, optional)

```bash
headroom evals adversarial --json-output knowledge/research/phase5-adversarial-eval.json
```

Artifact present from prior run; no payload class beat benign baseline in summary rows (see JSON).

## Forbidden scope — confirmed not used

`headroom memory`, `learn`, `proxy`, `wrap`, `mcp` (live), output-savings dashboards, OmniRoute, AGENTS.md / instruction writes.

## P5-05 go / no-go (preliminary)

| Decision | Outcome |
|----------|---------|
| Add Headroom to standard agent stack | **NO** (default unchanged) |
| Keep compression benchmark evidence | **YES** — archive in [`headroom-ab.md`](./headroom-ab.md) |
| Re-run after env change | Use isolated venv — [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md) |

## Related

- Plan: [`phase5-headroom-benchmark-plan.md`](./phase5-headroom-benchmark-plan.md)
- Kompress retest (isolated venv, session `bd2c1225`): [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md)
- Runbook: [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md)
- Archive table: [`headroom-ab.md`](./headroom-ab.md)
