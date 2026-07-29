# STM visual-parity (VP) measurement specification

**Version:** 1.0.0 (2026-07-29)  
**Scorer:** `scripts/regression-harness/stm_vp_compare.py`  
**Tests:** `tests/test_stm_vp_compare.py`

## Purpose

Fail-closed comparison of **reference** vs **candidate** STM producer outputs and optional final LED byte streams for EdgeMixer modes 7–8. Extends existing VP infrastructure (`render_replay.py`, `vpab_frame_capture.py`, `vpab_frame_gate.py`) — does not replace Tier-2 device capture.

## Epistemic tiers

| Tier | Source | STM claim |
|------|--------|-----------|
| Host mechanism | `k1_stm_replay.py` | H1 only |
| Host VP bytes | `render_replay.py` + STM fixtures | H2 partial (no gamma parity) |
| Device VPAB | `vpab_frame_capture.py` | H2/H3 when authorised |

## Manifest schema (`manifest.json`)

Required top-level keys:

- `experiment_version` (string)
- `threshold_set_hash` (string, must match scorer input)
- `fixture_hash` (hex sha256)
- `reference` — `{ "algorithm_id", "source_hash", "executable_hash", "fft_size", "stm_bins" }`
- `candidate` — `{ "algorithm_id", "source_hash", "executable_hash", "stm_bins" }`
- `streams` — paths to NDJSON frame files
- `alignment` — `{ "method", "lag_samples", "uncertainty_samples", "ready_frames_excluded" }`
- `controls` — list of control IDs executed

`reference.fft_size` **must** be `512` for parity claims against donor semantics. `candidate` **must** attest `native_80_to_40`.

## Stream record schema (NDJSON per frame)

```json
{
  "t_ms": 0,
  "ready": false,
  "temporal_energy": 0.0,
  "spectral_energy": 0.0,
  "spectral": [0.0],
  "bytes_hex": null
}
```

- `spectral` length must match declared bin count for that stream.
- `bytes_hex` optional — 480 hex chars (160×RGB) for final-byte metrics.

## Alignment rules (frozen)

1. Align on `t_ms` monotonic + source sample index — **no** per-fixture best-lag search, **no** DTW.
2. Score only after both streams report `ready=true` for ≥ `min_ready_frames`.
3. Fixed lag estimated once from sync marker; if `uncertainty_samples` > half capture interval → **INDETERMINATE**.

## Active-data gates

Reject parity credit when, after readiness:

- Both streams all-zero or constant below activity floor.
- Identical `reference.source_hash` and `candidate.source_hash`.
- Identical `executable_hash` (self-shadow).
- `self_shadow: true` in manifest — may emit instrumentation smoke only, **never** PASS.

## Metrics layers

**Producer:** readiness timing, temporal/spectral energy error, cosine similarity on common axis, centroid/peak displacement.

**Final-byte (when `bytes_hex` present):** MAE8, p95, max, changed-LED %, centre-of-mass Δ, trail Δ, tail-integral Δ — vs provisional thresholds in `WB3_HYPOTHESES_AND_CLAIMS.md`.

## Artefact layout

```
artifacts/stm-vp/<run-id>/
  manifest.json
  reference.ndjson
  candidate.ndjson
  alignment_report.json
  metrics.json
  verdict.json
```

## Machine verdict object (`verdict.json`)

```json
{
  "state": "PASS|FAIL|INDETERMINATE",
  "claim": "H2_visual_semantic",
  "reasons": [],
  "threshold_set_hash": "..."
}
```

## Captain review HTML

Generated only when `state != INDETERMINATE` and active-data gates pass. Fixed exposure scale; no per-variant auto-exposure. Diagnostic until Captain sign-off.

## Host qualification sequence (plan §8.8)

1. All `test_stm_vp_compare.py` cases green.
2. Reference-vs-reference ≥3 runs PASS (when reference exists).
3. Negative controls fail as designed.
4. Hardware matrix only after device allocation + playback approval.
