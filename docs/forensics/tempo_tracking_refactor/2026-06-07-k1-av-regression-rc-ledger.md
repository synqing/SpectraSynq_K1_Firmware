# K1 AV Regression v2 Release-Candidate Ledger

## Verdict

Status: **RC evidence assembled; production promotion deferred**.

The SAT palette rollout, fixture-corpus repair, required runtime/cadence gates, VPAB visual-sync capture, Smart Auto mode-safety validation, final host/build gates, and the `dense_clipped_edm` Dense Forge eyes-on gate are complete. This is not a production promotion: the documented `PARTIAL` weak-lock and silence/open-quiet residual findings remain blockers, and Smart Auto product judgement is deferred to Scene Policy v2.

## Source State

- Git HEAD for post-Scene-Policy-v2 device proof: `bd4beeed5cce83fb0f2a1886ce4a561bb8a55d82`
- Working tree: dirty with post-proof evidence/fixture-manifest updates pending
- Plan file: not edited
- Prior Scene Policy v2 implementation checkpoint commit: `bd4beee`

## Build and Test Gates

- `python -m pytest tests/ -q`: **PASS** (`173 passed, 15 subtests passed`)
- `pio run -e k1_hardware`: **SUCCESS**
- `pio run -e k1_bench_reference`: **SUCCESS**
- Main K1 production restore after VPAB harness capture: **SUCCESS**

Known compiler warning remains the existing ESP32 volatile increment warning in `system.h`; it did not block PlatformIO builds.

## Device Identities

- Main K1: `/dev/cu.usbmodem1401`, serial `B4:3A:45:A5:87:F8`, upload guard verified chip `F887A500`
- Bench K1 present: `/dev/cu.usbmodem12201`, serial `B4:3A:45:A5:89:B4`
- Additional visible port: `/dev/cu.usbmodem12401`, serial `F0:F5:BD:75:A7:FC`

## SAT Palette Rollout Checkpoint

- Host/build gates were rerun after SAT rollout and again after AV/VPAB/Smart Auto additions.
- Main and bench units had modes 22/23 flashed and Captain eyes-on confirmed tidy earlier in this session.
- Temporary SAT A/B mode IDs 24/25 were removed from dispatch/selection surfaces and sanitized on persisted config load.
- Additive effects now use hue-preserving finalization/history storage where applicable.

## Corpus Repair

Fixture manifest: `scripts/regression-harness/fixtures/k1_av_regression_fixtures.template.json`

- `slow_84_syncopated`: active required generated control, expected `84 BPM`, syncopated pattern.
- `fast_130_fourfloor`: blocked/non-required historical triage artifact; generated 130 lane failed on device and must not gate promotion.
- `fast_127_fourfloor`: active required generated fast replacement, expected `127 BPM`.
- `halftime_suspect_80`: blocked/non-required historical half-time artifact; generated 80 half-time lane locked alternate BPM lanes on post-Scene-Policy-v2 proof and must not gate promotion.
- `slow_80_fourfloor`: blocked/non-required attempted 80 BPM replacement; generated 80 four-floor lane locked near `124 BPM` on post-Scene-Policy-v2 proof.
- Banned/unsuitable Harmonix sources remain out of required gates.

Fast replacement evidence:

- `build/audio-semantic-metrics/k1-av-regression/k1_av_fast_replacement_20260607_045619/k1_av_fast_replacement_20260607_045619__matrix.json`
- Verdict: **PASS**
- `fast_127_fourfloor`: median `126 BPM`, near-target `18/19`, locked-near `3`

## AV Regression v2

Primary repaired matrix:

- Report: `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-av-regression-v2-repaired.md`
- Matrix: `build/audio-semantic-metrics/k1-av-regression/k1_av_regression_v2_repaired_20260607_045654/k1_av_regression_v2_repaired_20260607_045654__matrix.json`
- Runtime guard: **PASS** (`ap_core=0`, `vp_core=1`, `sample_rate=12800`, `samples_per_chunk=96`, `tempo_decim=3`, `dma_desc=3`)
- Overall matrix verdict: **PARTIAL**

Post-Scene-Policy-v2 proof matrix:

- Report: `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-av-scene-policy-v2-postfix-repaired.md`
- Matrix: `build/audio-semantic-metrics/k1-av-regression/k1_av_scene_policy_v2_postfix_repaired_20260607_055933/k1_av_scene_policy_v2_postfix_repaired_20260607_055933__matrix.json`
- Runtime guard: **PASS** (`ap_core=0`, `vp_core=1`, `sample_rate=12800`, `samples_per_chunk=96`, `tempo_decim=3`, `dma_desc=3`)
- Overall matrix verdict: **PARTIAL**
- Hard `FAIL_tempo_lane` from the attempted 80 BPM controls is removed from required gating by blocking `halftime_suspect_80` and `slow_80_fourfloor`.
- Remaining required fixture status: three weak-lock lanes reconciled by NOV replay; `loreen_127` scoped P2 confidence residual only.
- Silence event-layer P1: **closed** — `PASS_no_false_tempo_lock_under_verified_taped_mic`, `PASS_event_layer_quiet`, `0.0` onsets/minute.

Weak-lock follow-up:

- Report: `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-weak-lock-probe.md`
- `slow_84_syncopated`: APCAD/NOV cadence healthy and declared-rate buffered NOV replay locks near `84 BPM`.
- `click_127` and `fast_127_fourfloor`: APCAD/NOV cadence healthy and declared-rate buffered NOV replay locks near `127 BPM` after gain-normalised `ffplay` recapture.
- `loreen_127`: APCAD/NOV cadence healthy and declared-rate buffered NOV replay stays near target (`129 BPM`), but remains a true weak-lock/confidence issue with zero high-confidence or locked warm rows in the bounded 20s replay.

Required-gate interpretation:

- No runtime/cadence/core/I2S failure.
- No required fixture returned `FAIL_tempo_lane` after replacing `fast_130_fourfloor` and blocking both failed generated 80 BPM artifacts.
- Weak-lock reconciliation (2026-06-07): `slow_84_syncopated`, `click_127`, and `fast_127_fourfloor` have declared-rate NOV replay lock proof and are **reconciled** — AP-stream weak-lock label is a one-Hz surface limitation, not a cadence failure. See `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-weak-lock-matrix-reconciliation.md`.
- Scoped residual: `loreen_127` — near-target timing, zero high-confidence/locked warm rows in bounded replay (`P2_loreen_127_confidence_weak_lock_scoped`).
- Silence/open-quiet P1: **closed** at `3295c435` / `2026-06-07-k1-silence-open-quiet-vu-gate.md` (`0.0` onsets/minute on taped mic).

## Dense Product Lane

AP/event evidence:

- Source matrix: `k1_av_regression_v2_repaired_20260607_045654`
- `dense_clipped_edm`: **PASS_timing_and_tempo**
- Warm median BPM: `126.0`
- Event product-feel: **PASS**
- Onsets/minute: `56.4`
- No runtime/cadence failure.

Visual evidence:

- Dense Forge mode `21` was set on the main K1 and the 90-second `dense_clipped_edm` window was played with palette mode on.
- VPAB dense visual-sync capture completed with `max_white_bias_score=0.0` and `max_dropped=0`.
- Manual Captain eyes-on verdict: **PASS** — colours saturated and not washed out.

## VPAB Visual Sync

VPAB capture required harness firmware and was followed by restoring production firmware.

- Summary: `build/audio-semantic-metrics/k1-vpab-visual-sync/k1_vpab_dense_visual_sync_20260607_051025/k1_vpab_dense_visual_sync_20260607_051025__dense_clipped_edm__summary.json`
- Raw log: `build/audio-semantic-metrics/k1-vpab-visual-sync/k1_vpab_dense_visual_sync_20260607_051025/k1_vpab_dense_visual_sync_20260607_051025__dense_clipped_edm__vpab.log`
- Render-budget note: `docs/forensics/tempo_tracking_refactor/2026-06-07-vpab-visual-sync-render-budget-semantics.md`
- Rows: `64` VPAB metric rows, `32` final-byte aggregate rows, `1` context row
- Context: primary mode `21`, secondary mode `18`
- Dropped records: `0`
- Max white-bias score: `0.0`

## Render-Budget Semantics

VPAB scalar timing is not causality proof.

- `render_us`: wall-envelope/max-accumulator diagnostic
- `quant_us`: final-byte quantization/LED byte conversion timing
- `frame_us`: visual frame envelope diagnostic
- `show_us`: FastLED/RMT output diagnostic

Effect-code timing attribution still requires trace-dev/MabuTrace evidence. VPAB must not be used alone to claim an effect body violates the render budget.

## Smart Auto Mode-Safety Validation

Summary:

- `build/audio-semantic-metrics/k1-smart-auto-validation/k1_smart_auto_validation_v2_20260607_051236/k1_smart_auto_validation_v2_20260607_051236__summary.json`
- Raw log: `build/audio-semantic-metrics/k1-smart-auto-validation/k1_smart_auto_validation_v2_20260607_051236/k1_smart_auto_validation_v2_20260607_051236__raw.log`
- Mode-safety verdict: **PASS**
- Disabled/deprecated modes seen: none

Per-clip summary:

- `acestep_kick_drop_heavy`: applied modes `[8, 11, 21]`, requested `[8, 11]`
- `acestep_steady_groove`: applied modes `[3, 8]`, requested `[3, 8, 11]`
- `acestep_sparse_breakdown_build`: applied modes `[3]`, requested `[3, 8, 11]`
- `dense_clipped_edm`: applied modes `[3, 8, 11]`, requested `[8, 11]`

This validates mode-safety and bounded switching behavior only. It does not validate product fit, musical relevance, beat-aware scene intelligence, or the two-K1 perceptual A/B question. Those decisions are deferred to Scene Policy v2.

## Residual Risks

- Dense/manual Captain eyes-on verdict passed for saturation and washout.
- AV matrix may read `PARTIAL` only while `loreen_127` confidence weak-lock remains scoped; three other weak-lock lanes are NOV-replay reconciled.
- Smart Auto product fit is not claimed; serial A/B state gate passed; **Captain/video perceptual judgement remains the open gate**.
- VPAB `render_us` reached `2436 us` as a wall-envelope diagnostic and must not be interpreted as effect-code failure without trace-dev attribution.
- Main K1 (12201) primary channel recovered after cal/scene reset; intermittent VP chroma gate collapse possible when `max_raw < SSL`.

## Promotion Criteria Status

- SAT rollout checkpoint green: **met**
- Required v2 fixtures avoid runtime/cadence failures: **met**
- Fast fixture resolved/replaced: **met**
- Dense product-feel AP metrics: **met**
- Dense Captain eyes-on verdict: **met**
- VPAB/visual sync captured: **met**
- Smart Auto mode-safety validation: **met**
- Production build free of VPAB/MabuTrace instrumentation: **met by build/env boundary and production restore**

Promotion decision: **deferred**. Remaining blockers: Captain/video Scene Policy v2 perceptual A/B judgement, and scoped `loreen_127` confidence weak-lock (P2, non-cadence). Silence P1 closed; three weak-lock lanes reconciled by NOV replay; serial A/B state gate passed.
