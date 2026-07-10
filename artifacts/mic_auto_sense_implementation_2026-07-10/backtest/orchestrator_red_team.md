# MAS Red-Team Backtest

Date: 2026-07-10

## Verdict

The first implementation was not acceptable. It had real errors: stale I2S read faults could be reported as OK, the shadow-scale field was misleading, one first-read path could expose an unseeded scale, and tests were too synthetic.

The corrected version is still telemetry-only. It does not auto-calibrate, persist, save config, trigger noise calibration, apply sensitivity scaling, or claim device proof.

## Corrections Applied

- Renamed `k1_bench_im73d_mic_auto_shadow` to `k1_bench_im73d_mic_auto_telemetry`.
- Removed `mas_shadow_scale` and all `shadow_scale` state.
- Added `k1_mic_auto_sense_note_i2s_result(...)` and stale-I2S reason handling.
- Seeded `applied_scale=1.0f` on reset, read, and update.
- Replaced MAS `isfinite()` use with a bit-level exponent check.
- Strengthened AP parser/schema/static tests to cover production rows, telemetry rows in firmware order, no shadow field, no non-1.0 applied-scale writes, and stale-I2S wiring.

## Validation

- `python3 -m py_compile scripts/regression-harness/im73d_audio_eval.py scripts/platformio/k1_upload_guard.py tests/test_mic_auto_sense_static.py tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py tests/test_k1_upload_guard.py`: pass.
- `git diff --check`: pass.
- `python3 -m pytest tests/test_mic_auto_sense_static.py tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py tests/test_k1_upload_guard.py tests/test_mic_stable_byte_gate_static.py tests/test_im73d_audio_purity_static.py tests/test_i2s_watchdog_static.py -q`: 49 passed.
- `python3 -m pytest tests/ -q`: 688 passed, 1 skipped.
- `bash scripts/agent/pio-build.sh k1_hardware`: pass.
- `bash scripts/agent/pio-build.sh k1_bench_im73d`: pass.
- `bash scripts/agent/pio-build.sh k1_bench_im73d_mic_auto_telemetry`: pass.
- `find .pio/build/k1_hardware .pio/build/k1_bench_im73d .pio/build/k1_bench_im73d_mic_auto_telemetry -path '*k1_mic_auto_sense*' -type f`: only telemetry env contains MAS object/dependency files.
- `bash scripts/regression-harness/mic_stable_byte_gate.sh`: fail in live checkout.
- Same stable-byte gate in detached clean `cc97081` worktree: same wanted/got hashes fail for `k1_hardware`, `k1_bench_reference`, and `k1_bench_im73d`; classify as baseline stale-reference blocker, not patch-caused.

## Remaining Limits

- MAS AP telemetry is previous closed-frame telemetry because AP printing happens during acquisition and MAS update happens after GDFT/loud-guard.
- Bench device flash and AP capture are now complete: `k1_bench_im73d_mic_auto_telemetry` on chip `B489A500`, 40 MAS AP rows, no crash markers.
- No calibration command was performed.
- Main K1 was not flashed.
- Stable-byte references remain stale and need an explicit reference-refresh decision before that gate can be used as a green preservation oracle.
