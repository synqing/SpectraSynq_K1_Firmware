# Phase 5 — Headroom Kompress `compress()` retest

**Date:** 2026-07-13  
**Prior blocker:** session `dc9e23a7` / miniforge — `transformers` import tripped `importlib_metadata.version("torchaudio")` → `TypeError: 'NoneType' object is not subscriptable` (broken or partial `torchaudio` install metadata on shared host env).  
**Mitigation:** isolated venv only (no changes to repo or miniforge Python).

## Environment

| Item | Value |
|------|--------|
| Venv | `/tmp/headroom-bench-venv` |
| Python | 3.12 (`/opt/homebrew/bin/python3.12`) |
| Install | `pip install 'headroom-ai[ml]==0.31.0' onnxruntime` |
| `headroom-ai` | 0.31.0 |
| `transformers` | 5.13.1 |
| `torch` | 2.13.0 |
| `onnxruntime` | 1.27.0 |
| `tokenizers` | 0.22.2 |
| `importlib_metadata` | 8.9.0 |

## Probe results

```text
import transformers  → OK (5.13.1)
is_kompress_available() → True
```

Smoke `headroom.compress(..., optimize=True)` on synthetic `role: tool` payload:

- tokens: 1859 → 72 (~96.1% ratio in harness units)
- canaries `k1_hardware`, `F887A500` preserved

## Full harness (`compress()` API, Kompress path)

Command (repo root):

```bash
/tmp/headroom-bench-venv/bin/python3 scripts/agent/phase5-headroom-ab.py
```

`git_head_at_run`: `e67da587c78c31a3c056a8dfab74fe8e5a5708f2`

| Task ID | Tokens baseline | Tokens compressed | % reduction | Identifiers |
|---------|-----------------|-------------------|-------------|-------------|
| T-DEBUG | 41,769 | 7,104 | 82.99% | OK |
| T-IMPLEMENT | 37,440 | 7,098 | 81.04% | OK |
| T-REVIEW | 37,592 | 7,104 | 81.10% | OK |

Artifact refreshed: [`phase5-ab-metrics.json`](./phase5-ab-metrics.json).

**Verdict:** **UNBLOCKED** — full library `compress()` / Kompress stack runs in isolated venv. Prior ~50% TextCrusher-only partial path superseded for token metrics by ~81–83% via router + Kompress on same synthetic tasks.

## Phase gate impact (preliminary)

| Item | Status |
|------|--------|
| P5-03 full `compress()` API | **PASS** (isolated venv) |
| P5-04 human quality | still **DEFERRED** |
| P5-05 stack promotion | still **NO** until P5-04 + rollout review |

## Reproduce

See [`headroom-compression-benchmark.md`](../runbooks/headroom-compression-benchmark.md) for full steps. Summary:

```bash
rm -rf /tmp/headroom-bench-venv
/opt/homebrew/bin/python3.12 -m venv /tmp/headroom-bench-venv
/tmp/headroom-bench-venv/bin/pip install --upgrade pip
/tmp/headroom-bench-venv/bin/pip install 'headroom-ai[ml]==0.31.0' onnxruntime
cd /path/to/SpectraSynq_K1_Firmware
/tmp/headroom-bench-venv/bin/python3 scripts/agent/phase5-headroom-ab.py
```
