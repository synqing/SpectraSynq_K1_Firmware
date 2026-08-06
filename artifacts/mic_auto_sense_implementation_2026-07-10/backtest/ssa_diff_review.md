# MAS-DIFF-REVIEW-20260710 - Mic Auto-Sense Diff Review

Date: 2026-07-10  
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`  
Live checkout verified read-only: `lane/dual-sync-phase0 @ cc970810436febb12293697e626991f83569c1c1`  
Scope: current changed/untracked mic auto-sense diff plus immediate parser/build/guard dependencies. Source/test files were not modified.

## Verdict

STATUS: NOT_VERIFIED

The patch is a telemetry-only scaffold with useful guard shape, but the current diff still has load-bearing review failures: stale/short I2S reads can be reported as `mas_reason=OK`, the "shadow" field/env is only a hard-coded placeholder, the parser/schema tests do not lock the real AP line shape, and the implementation artifacts claim verification while a required byte gate is recorded as blocked/failing.

## Findings

### BLOCKER - Correctness: `mas_reason=OK` can hide stale or short I2S reads

`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:329-335` zero-fills the tail on IM73D I2S read fault or short read. `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:352-359` only records `i2s_read_status` and `bytes_read` behind `ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`; otherwise both are explicitly discarded. The new auto-sense enum defines `K1_MIC_AUTO_REASON_STALE_I2S` at `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h:20`, but the implementation sets `K1_MIC_AUTO_REASON_OK` at `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:70-73` and only overrides it for raw-unavailable, invalid calibration, headroom, or non-finite values at `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:75-99`.

Why it matters: a DMA/read fault can look like silence or partial silence while MAS reports telemetry OK. That weakens any shadow/acceptance capture and is dangerous if these state fields later gate applied auto-scale.

Suggestion: expose the last read status/bytes-read to the MAS update path, set `K1_MIC_AUTO_REASON_STALE_I2S` on non-OK/short reads or stale frame age, and add a static or host fixture proving short-read zero-fill cannot produce `mas_reason=OK`.

Re-run:

```bash
/opt/homebrew/bin/rg -n "i2s_read_status|bytes_read|K1_MIC_AUTO_REASON_STALE_I2S|reason = K1_MIC_AUTO_REASON" SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.*
```

### BLOCKER - Contract: `mas_shadow_scale` is not a shadow recommendation

The new env is named `k1_bench_im73d_mic_auto_shadow` and labelled "MIC AUTO-SENSE SHADOW" at `platformio.ini:222-225`, and AP exports `mas_shadow_scale` at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:832-838`. But `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:17-20` seeds both `applied_scale` and `shadow_scale` to `1.0f`, `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:39` re-seeds them every update, and `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp:108-110` returns only `1.0f`.

The governing design says shadow proof should compute `auto_state`, `auto_reason`, and recommended `auto_scale` while leaving applied scale at `1.0f` (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:420-426`). Current tests reinforce the placeholder instead of detecting missing recommendation logic: `tests/test_mic_auto_sense_static.py:73-75` checks only that fixed strings exist, and `tests/test_im73d_audio_eval_harness.py:53-58` asserts the parser reads `mas_shadow_scale=1.000`.

Why it matters: if the orchestrator treats this env as shadow recommendation proof, the data is false confidence. If this is intentionally Phase-1 telemetry only, the env/field naming and closeout need to say "placeholder/no recommendation" and should not be used for any auto-scale decision.

Suggestion: either rename/downgrade the surface to telemetry-only, or implement a real shadow recommendation with explicit tests for weak, healthy, loud, invalid-calibration, and stale-I2S cases.

Re-run:

```bash
nl -ba platformio.ini | sed -n '222,232p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp | sed -n '17,40p;70,110p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '420,426p'
```

### SUGGESTION - Tests: AP schema/parser coverage is synthetic and misses real ordering drift

The actual firmware emits AP fields in this order: base/front-end plus tempo/onset at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:806-812`, optional raw IM73D fields at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:813-818`, optional loud-guard fields at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:819-830`, then MAS fields at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:832-838`.

The parser test fixture puts MAS before `response_gain` and before the loud-guard segment (`tests/test_im73d_audio_eval_harness.py:45-50`), which is not the firmware line shape. The schema test only asserts token presence in source text (`tests/test_audio_telemetry_schema_static.py:65-73`), so it would still pass if the AP line were split, reordered unexpectedly, or placed in a context the harness never sees.

Why it matters: the named failure mode for this review was accepting token-only tests and missing AP parser ordering/schema drift. The parser is order-insensitive today (`scripts/regression-harness/im73d_audio_eval.py:80-86`), so this is not a current parser crash, but it is weak coverage for a load-bearing telemetry contract.

Suggestion: add a fixture that mirrors the firmware AP order exactly, including base, tempo/onset, raw_i16, loud-guard, and MAS segments. Keep token-presence tests as secondary, not the primary schema gate.

Re-run:

```bash
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '806,838p'
nl -ba tests/test_im73d_audio_eval_harness.py | sed -n '42,60p'
nl -ba tests/test_audio_telemetry_schema_static.py | sed -n '65,73p'
```

### BLOCKER - Validation: required byte gate is not green in the implementation record

The design requires the telemetry implementation gate to run `bash scripts/regression-harness/mic_stable_byte_gate.sh` (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:467-473`). The current implementation artifacts record the phase as "complete-with-known-blocker" and say that `mic_stable_byte_gate.sh` fails for all three stable-section references (`artifacts/mic_auto_sense_implementation_2026-07-10/task_plan.md:24`, `artifacts/mic_auto_sense_implementation_2026-07-10/task_plan.md:56`; also `artifacts/mic_auto_sense_implementation_2026-07-10/findings.md:49-55`).

Why it matters: even if the drift is pre-existing, the required preservation oracle is red. The patch should not be reported as fully verified unless the orchestrator explicitly accepts the stale-reference blocker, updates the byte reference under the appropriate review process, or changes the gate contract.

I did not run this gate in the review because the script invokes `pio run` and writes `.pio/build/...` (`scripts/regression-harness/mic_stable_byte_gate.sh:75-82`), outside the brief's write-scratch-only constraint.

Re-run:

```bash
bash scripts/regression-harness/mic_stable_byte_gate.sh
```

## Commands Run

```bash
git status --short --branch && git rev-parse HEAD && git branch --show-current
git diff --stat
git diff -- SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h platformio.ini scripts/agent/pio-build.sh scripts/platformio/k1_upload_guard.py tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_eval_harness.py tests/test_k1_upload_guard.py
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_mic_auto_sense_static.py tests/test_im73d_audio_eval_harness.py::test_ap_parser_captures_mic_auto_sense_shadow_fields tests/test_audio_telemetry_schema_static.py::test_ap_stream_schema_keeps_front_end_and_loud_guard_fields tests/test_k1_upload_guard.py
git diff --check
```

Validation result: targeted pytest passed (`19 passed in 0.03s`) and `git diff --check` passed. Firmware builds, full pytest, device actions, and byte gate were not run in this review because of the read-only/write-scratch-only constraint.

## Method Risk

The main way this review could be wrong is if "shadow" is intentionally defined by the orchestrator as "no recommendation, fixed `1.0f` placeholder" for this slice. In that case, the shadow-scale finding should be downgraded from blocker to naming/documentation risk, but the stale-I2S false-OK path and weak AP schema tests still stand.
