---
title: Headroom compression-only benchmark (Phase 5)
status: verified
last_verified: 2026-07-13
sources:
  - knowledge/research/phase5-headroom-benchmark-plan.md
  - knowledge/research/phase5-headroom-kompress-retest.md
  - scripts/agent/phase5-headroom-ab.py
  - docs/agent-stack/AUTHORITY-CONTRACT.md
owner: knowledge-curator
---

# Headroom compression-only benchmark

Reproduce Phase 5 A/B metrics for `headroom.compress()` on synthetic tool JSON payloads. **Compression-only** — forbidden: `memory`, `learn`, `proxy`, `wrap`, instruction writes.

## When to use

- Re-run P5-03 after `headroom-ai` pin change or host Python env drift
- Verify Kompress ONNX path after ML stack upgrades
- Refresh [`phase5-ab-metrics.json`](../research/phase5-ab-metrics.json) before promotion debate

## Host constraint (this machine)

| Item | Policy |
|------|--------|
| **miniforge** (`~/miniforge3/bin/python3`) | **Do not** use for `[ml]` / Kompress — broken `torchaudio` metadata blocks `transformers` import |
| **Isolated venv** | **Required** for full `compress()` + Kompress |
| **Venv path** | `/tmp/headroom-bench-venv` |
| **Python** | `/opt/homebrew/bin/python3.12` |

Retest proof: [`phase5-headroom-kompress-retest.md`](../research/phase5-headroom-kompress-retest.md) (session `bd2c1225`).

## Prerequisites

- Repo checkout at desired `git` HEAD (harness records `git_head_at_run`)
- Network for `pip install` (PyPI + Hugging Face model cache on first Kompress run)
- ~2 GB disk for venv + ONNX deps (first run)

## Reproduce (canonical)

From repo root:

```bash
rm -rf /tmp/headroom-bench-venv
/opt/homebrew/bin/python3.12 -m venv /tmp/headroom-bench-venv
/tmp/headroom-bench-venv/bin/pip install --upgrade pip
/tmp/headroom-bench-venv/bin/pip install 'headroom-ai[ml]==0.31.0' onnxruntime
cd /path/to/SpectraSynq_K1_Firmware
```

### Probe (optional)

```bash
/tmp/headroom-bench-venv/bin/python3 -c "
import transformers
from headroom.transforms.kompress_compressor import is_kompress_available
print('transformers', transformers.__version__)
print('is_kompress_available', is_kompress_available())
"
```

Expect `is_kompress_available True`.

### Full A/B harness

```bash
/tmp/headroom-bench-venv/bin/python3 scripts/agent/phase5-headroom-ab.py
```

**Pass criteria:**

- Exit code `0`
- All three tasks report `id_ok`
- [`phase5-ab-metrics.json`](../research/phase5-ab-metrics.json) updated with `identifier_ok: true` for T-DEBUG, T-IMPLEMENT, T-REVIEW
- Typical reduction: **~81–83%** on structured JSON tool payloads

### Adversarial grid (optional)

```bash
/tmp/headroom-bench-venv/bin/headroom evals adversarial \
  --json-output knowledge/research/phase5-adversarial-eval.json
```

## Artifacts

| File | Role |
|------|------|
| [`phase5-ab-metrics.json`](../research/phase5-ab-metrics.json) | Machine-readable A/B table |
| [`phase5-headroom-kompress-retest.md`](../research/phase5-headroom-kompress-retest.md) | Isolated-venv retest narrative |
| [`phase5-headroom-benchmark-plan.md`](../research/phase5-headroom-benchmark-plan.md) | Protocol (P5-01) |
| [`phase5-exit-gate-summary.md`](../research/phase5-exit-gate-summary.md) | Canonical Phase 5 exit gate |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `is_kompress_available() → False` | Running on miniforge or polluted site-packages | Recreate `/tmp/headroom-bench-venv` with Homebrew Python |
| `TypeError: 'NoneType' object is not subscriptable` on `torchaudio` | Broken `torchaudio` metadata in shared env | Use isolated venv; do not `pip install` into miniforge for this benchmark |
| `headroom-ai not installed` | Wrong interpreter | Activate venv or use full path `/tmp/headroom-bench-venv/bin/python3` |
| 0% reduction on small plain-text payloads | Router no-op on tiny bodies | Expected; harness uses tool-heavy JSON — see plan § A/B protocol |

## Scope guardrails

Do **not** invoke during this benchmark:

- `headroom memory`, `learn`, `proxy`, `wrap`
- AGENTS.md / instruction writes
- OmniRoute or live MCP wrapping

## Related

- Plan: [`phase5-headroom-benchmark-plan.md`](../research/phase5-headroom-benchmark-plan.md)
- Results archive: [`phase5-headroom-benchmark-results.md`](../research/phase5-headroom-benchmark-results.md)
