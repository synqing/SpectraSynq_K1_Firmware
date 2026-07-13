# Phase 5 — Headroom compression-only benchmark plan

**Date:** 2026-07-13  
**Authority:** [`docs/agent-stack/PHASED-ROLLOUT.md`](../../docs/agent-stack/PHASED-ROLLOUT.md) Phase 5 · [`AUTHORITY-CONTRACT.md`](../../docs/agent-stack/AUTHORITY-CONTRACT.md)  
**Status:** Exit gate **PASS** (2026-07-13); P5-05 promotion **DEFERRED** — [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md)

## Goal

Measure whether **Headroom compression library** reduces tool-heavy context size without corrupting identifiers, under **compression-only** scope.

## Package resolution (P5 install)

| Source | Name | Notes |
|--------|------|-------|
| PyPI (primary) | `headroom-ai` | Ships `headroom` CLI + Python `compress()` |
| npm | `headroom-ai` | TypeScript SDK only — **no** CLI |
| GitHub | `headroomlabs-ai/headroom` | Upstream product repo / docs |

Pin for reproducibility: **`headroom-ai==0.31.0`**.

## Host environment (`[ml]` / Kompress)

On this host, **do not** run Kompress / `headroom-ai[ml]` benchmarks against the shared **miniforge** Python (`~/miniforge3/bin/python3`). A partial or broken `torchaudio` install in that env causes `transformers` import failure (`importlib_metadata.version("torchaudio")` → `TypeError: 'NoneType' object is not subscriptable`) and `is_kompress_available()` → **False**.

| Requirement | Value |
|-------------|--------|
| Isolated venv | **Required** for `[ml]` / Kompress on this host |
| Venv path | `/tmp/headroom-bench-venv` |
| Python | `/opt/homebrew/bin/python3.12` (or any clean 3.12+ not sharing miniforge site-packages) |
| Install | `pip install 'headroom-ai[ml]==0.31.0' onnxruntime` |

Retest evidence (session `bd2c1225`, 2026-07-13): [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md). Reproduce steps: [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md).

## In scope

- `headroom.compress()` with `optimize=True` on synthetic tool JSON payloads
- Offline `headroom evals adversarial` (optional robustness grid)
- Payloads from `knowledge/` + `docs/agent-stack/` + committed adversarial JSON

## Explicitly excluded (forbidden)

| Capability | Reason |
|------------|--------|
| `headroom memory` | Memory authority = OpenKnowledge / claude-mem routing |
| `headroom learn` | Instruction writes forbidden |
| Instruction / AGENTS.md writes | No stack mutation |
| Output shaping | Out of scope |
| `headroom proxy` + provider routing | No OmniRoute |
| `headroom wrap` | No production agent wrapping in benchmark |

## A/B protocol (P5-01)

### Task archetypes

| Task ID | Type | Payload |
|---------|------|---------|
| T-DEBUG | debug | JSON tool body: firmware paths, constants, adversarial grid |
| T-IMPLEMENT | implement | JSON tool body: rollout + OpenKnowledge proof excerpts |
| T-REVIEW | review | JSON tool body: ACTIONABLE-TASKS + Phase 4 exit summary |

### Canary identifiers (must survive compression)

Per-task lists in harness; include `git_head` (40-char), `k1_hardware`, `F887A500`, `session-bootstrap.sh`, `AUTHORITY-CONTRACT`, DSP symbols, and repo-relative paths.

### Variants

| Variant | Method |
|---------|--------|
| **A (baseline)** | `CompressResult.tokens_before` on message list with raw tool JSON |
| **B (compressed)** | `headroom.compress(..., optimize=True)` → `tokens_after` |

### Acceptance criteria

| ID | Criterion | Threshold |
|----|-----------|-----------|
| AC-1 | Install | `headroom-ai==0.31.0` importable; `headroom --version` |
| AC-2 | Three task types | debug / implement / review |
| AC-3 | Reduction reported | Per-task tokens in `phase5-ab-metrics.json` |
| AC-4 | Identifier integrity | 0 canaries lost / 3 tasks; full `git_head` present |
| AC-5 | Adversarial grid (optional) | Artifact `phase5-adversarial-eval.json` |
| AC-6 | Human quality (P5-04) | Reviewer confirms no unacceptable loss on real task replay |

## Reproduce

**Canonical (Kompress / full `compress()` path):** isolated venv — see [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md).

```bash
rm -rf /tmp/headroom-bench-venv
/opt/homebrew/bin/python3.12 -m venv /tmp/headroom-bench-venv
/tmp/headroom-bench-venv/bin/pip install --upgrade pip
/tmp/headroom-bench-venv/bin/pip install 'headroom-ai[ml]==0.31.0' onnxruntime
cd /path/to/SpectraSynq_K1_Firmware
/tmp/headroom-bench-venv/bin/python3 scripts/agent/phase5-headroom-ab.py
# optional adversarial grid (same venv):
/tmp/headroom-bench-venv/bin/headroom evals adversarial --json-output knowledge/research/phase5-adversarial-eval.json
```

**Legacy / router-only (miniforge):** `pip install 'headroom-ai==0.31.0'` without `[ml]` may still run the harness on structured JSON via router/mixed, but Kompress ONNX is **unverified** on polluted miniforge — prefer isolated venv above.

Artifacts:

- [`phase5-exit-gate-summary.md`](./phase5-exit-gate-summary.md)
- [`phase5-ab-metrics.json`](./phase5-ab-metrics.json)
- [`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md)
- [`headroom-ab.md`](./headroom-ab.md)

## Phase gate mapping

| Task | Result |
|------|--------|
| P5-01 | **DONE** — this document |
| P5-02 | **DONE** — baselines in metrics JSON |
| P5-03 | **DONE** — ~81–83% on JSON via isolated venv + Kompress ([`phase5-headroom-kompress-retest.md`](./phase5-headroom-kompress-retest.md); miniforge Kompress blocked — see Host environment) |
| P5-04 | **IN PROGRESS** — automated canaries 3/3 PASS; human replay **DEFERRED** |
| P5-05 | **DEFERRED** — **no promote** — [`agent-stack-headroom-partial-2026-07-13.md`](../decisions/agent-stack-headroom-partial-2026-07-13.md) |
