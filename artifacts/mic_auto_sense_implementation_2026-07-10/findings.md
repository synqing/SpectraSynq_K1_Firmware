# Mic Auto-Sense Findings

## 2026-07-10 Authority Read

- Session bootstrap PASS: repo root `/Users/spectrasynq/SpectraSynq_K1_Firmware`, branch `lane/dual-sync-phase0`, HEAD `cc97081`, dirty/untracked, claude-mem reachable.
- Current AGENT/CLAUDE rules prohibit auto calibration and require identity verification before any device-write/serial-write action.
- Prior forensic synthesis established: the K1 auto-sensing design exists as docs-only research/handoff, not implemented source.
- The strongest design artifact requires telemetry first, default-off, no persistence writes, no auto calibration, and shadow proof before applied controller.

## Model Selection Notes

- Cynefin: firmware implementation seam is complicated; perceptual result is complex. Use expert analysis for source/tests; use safe-to-fail telemetry/shadow probes before behaviour changes.
- Systems thinking: auto-scale interacts with fixed mic gain, base sensitivity, loud guard, clamp/DC, Waveform-Fast floor, GDFT AGC, telemetry, and persistence. Treat it as a supervisory layer, not a replacement for any existing loop.
- Map-territory: `[AP]`, AGC, and semantic surfaces are conditioned maps; raw/pre-conditioning telemetry is the territory needed for mic health decisions.
- TRIZ contradiction: the system must adapt to room/playback levels for visual usefulness but must not mutate measurement truth or user/base sensitivity. Separation by condition/time: telemetry/shadow first, default-off; applied only when explicitly enabled; measurement modes bypass it; v1 runtime-only.

## Known Implementation Direction

Recommended first slice remains telemetry-only:

1. Add read-only raw/pre-conditioning metrics and controller state fields.
2. Keep applied auto scale at `1.0f`.
3. Add tests that prove no config save, no calibration firing, no hot-path unsafe constructs, and flag-off behaviour preservation.
4. Reassess after SSA results and branch authority resolution.

## SSA Synthesis

- MAS-CODE-01 verified the safe seam: use `audio/i2s_audio.h` raw/front-end telemetry and `[AP]` emission boundaries; do not touch sensitivity writes, response gain, calibration, persistence, GDFT/AGC control, or loud-guard formulas for Phase 1.
- MAS-TEST-01 verified the gate matrix: static/schema/parser tests, IM73D purity ordering, no calibration/persistence, no hot-path unsafe constructs, loud-guard layering, flag-off byte stability, guarded builds, and no device-proof claim for telemetry-only.
- MAS-DESIGN-01 verified the minimal design: default-off `audio/k1_mic_auto_sense.{h,cpp}` shadow observer, applied scale fixed at `1.0f`, and bypass/observe-only state for purity, calibration, DSR, stale I2S, and protection-pressure conditions.
- MAS-RISK-01 deliberately kept the feature `NOT_VERIFIED` until branch authority, hot-path safety, calibration/persistence boundaries, measurement honesty, flag-off proof, and device-proof boundaries are closed.

## Implementation Gate State

- Research confidence for a telemetry-only Phase 1 is high.
- Research confidence for an applied controller is low by design; it is explicitly out of scope until telemetry/shadow evidence exists.
- Implementation was initially blocked by branch authority. Captain selected `lane/dual-sync-phase0 @ cc97081` and telemetry-shadow Phase 1 before firmware edits began.
- The next controller phase remains blocked until telemetry/shadow evidence and device proof gates exist.

## Implementation Result

- Captain selected live `lane/dual-sync-phase0 @ cc97081` and the safe first slice: telemetry-only mic auto-sense observation.
- Added default-off `K1_MIC_AUTO_SENSE_V1` support through `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h` and `.cpp`.
- Added explicit non-shippable `k1_bench_im73d_mic_auto_telemetry` env. Default envs exclude `audio/k1_mic_auto_sense.cpp`; the telemetry env includes it and defines `K1_MIC_AUTO_SENSE_V1=1`.
- Added AP telemetry fields behind the feature flag: `mas_state`, `mas_reason`, `mas_window_age_sec`, `mas_applied_scale`.
- Removed the earlier fake `mas_shadow_scale`/shadow-env naming after review: there is no recommendation scale in this slice.
- `mas_applied_scale` is fixed at `1.0f`; the effective sensitivity function remains `CONFIG.SENSITIVITY * k1_loud_input_trim`.
- Wired I2S read status/short-read evidence into MAS via `k1_mic_auto_sense_note_i2s_result(...)`; read faults now drive `K1_MIC_AUTO_REASON_STALE_I2S`.
- Replaced the first-pass `isfinite()` guard in MAS with a bit-level IEEE exponent check so this module does not rely on `isfinite()` under `-ffast-math`.
- Added upload-guard mapping for the new bench-only telemetry env.

## Red-Team Corrections

- First-pass defect: pre-first-update telemetry could expose `applied_scale=0.0`; fixed by seeding `applied_scale=1.0f` on reset, read, and update.
- First-pass defect: I2S timeout/short-read zero-fill could still report MAS OK; fixed with the read-result hook and stale-I2S reason.
- First-pass defect: `mas_shadow_scale=1.0f` looked like a shadow recommendation but was only a placeholder; removed and renamed the env to telemetry-only.
- First-pass defect: AP parser/schema tests did not mirror real firmware order; added production-row and telemetry-row fixtures in firmware order.
- First-pass weakness: `isfinite()` in this module was not robust under the build's fast-math posture; replaced inside MAS only.

## Verification Result

- RED observed: focused TDD gate failed on missing telemetry env/module/AP fields/update call.
- GREEN focused/static after red-team fixes: `49 passed` across MAS static, AP schema/parser, upload guard, stable-byte static, IM73D purity, and I2S watchdog static tests.
- GREEN full pytest after red-team fixes: `688 passed, 1 skipped`.
- GREEN builds after red-team fixes: `bash scripts/agent/pio-build.sh k1_hardware`, `k1_bench_im73d`, and `k1_bench_im73d_mic_auto_telemetry`.
- Object containment verified: only `.pio/build/k1_bench_im73d_mic_auto_telemetry` contains `k1_mic_auto_sense.cpp.o/.d`.
- BLOCKED pre-existing gate: `bash scripts/regression-harness/mic_stable_byte_gate.sh` fails all three stable-section references. Detached clean `HEAD` reproduced the exact same wanted/got hashes, so this is not attributable to the new feature but remains a stale-reference blocker for that gate.
- No device flash, serial write, calibration trigger, or hardware proof was performed in this pass.

## Knowledge-Agent Status

- `build_corpus name=k1_mic_auto_sense_impl_20260710 ... query="IM73D sensitivity calibration profile loud guard raw telemetry Waveform-Fast auto-sense CONFIG.SENSITIVITY"` returned `observation_count: 0`.
- `build_corpus name=k1_im73d_sensitivity_broad_20260710 ... query="IM73D"` also returned `observation_count: 0`.
- Treat corpus build as degraded for this lane. Do not infer absence of memory from these empty corpora; prior direct forensic fetches found relevant observations and are captured in `artifacts/self_calibrating_sensitivity_forensics_2026-07-10/`.
