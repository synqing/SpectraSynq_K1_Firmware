# MAS-TEST-01 - Mic Auto-Sense Telemetry Test Plan

Date: 2026-07-10
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`
SSA: MAS-TEST-01
Verdict: VERIFIED as a required test plan; tests were not implemented or run.

## Scope Notes

- This was a read-only planning pass plus this single artifact write.
- No full pytest suite, PlatformIO build, byte gate, serial monitor, flash, or calibration command was run.
- `AGENT_OS.md` asks agents to run `scripts/agent/session-bootstrap.sh`, but that script writes `.devin/last-bootstrap.json`; it was not run because this brief allowed writing exactly this artifact path.
- Current read-only `git status --short --branch` showed `lane/dual-sync-phase0`; some handoff/spec text still names `lane/im73d-pdm-eval`, so branch-status claims in older handoffs are stale unless re-verified.
- `docs/agent/AGENT_EXECUTION_STANDARD.md` is referenced by AGENTS, but it is absent in this checkout.

## Source Truth

- The design requires telemetry before control and names minimum fields: `raw_abs_peak`, `raw_rms`, `raw_clip_pct` or `raw_near_rail_pct`, `post_gain_peak`, `auto_scale`, `auto_state`, `auto_reason`, and `auto_window_sec` (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:127-142`).
- Non-negotiable safety boundaries are no automatic `start_noise_cal`/`N`/`Y`, no hidden adaptive scale during raw/purity work, no v1 persistence, no Core 0 heap/String/blocking/serial prints, and default-off `K1_MIC_AUTO_SENSE_V1` (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:20-34`).
- The telemetry implementation phase explicitly requires schema/parser tests, read-only harness extension only, and build/test/byte-gate with auto-sense behaviour absent (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:320-339`).
- The later shadow phase computes recommendations but leaves applied scale at `1.0f`, and requires no persistence writes from the auto-sense path (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:424-432`).
- The prior synthesis says the next repo-authorised slice is default-off read-only telemetry, applied scale `1.0f`, no calibration firing, no `CONFIG.SENSITIVITY`/NVS writes, and host/static/byte proof before any applied controller (`artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md:69-77`).

## Test Matrix

| ID | Risk Covered | Existing Test Surface To Extend | Proposed New/Changed Tests | Required Assertions | File:Line Anchors |
| --- | --- | --- | --- | --- | --- |
| T1 | Telemetry schema regression or missing fields | Extend `tests/test_audio_telemetry_schema_static.py` | Add `test_ap_stream_schema_includes_mic_auto_sense_shadow_fields()` or, if a new read-only status command is used, add `tests/test_mic_auto_sense_static.py::test_status_schema_fields_are_locked()` | Lock the exact emitted field tokens for `raw_abs_peak`, `raw_rms`, `raw_near_rail_pct` or `raw_clip_pct`, `post_gain_peak`, `auto_scale`, `auto_state`, `auto_reason`, and `auto_window_sec`; keep existing AP fields intact. | Existing AP schema lock: `tests/test_audio_telemetry_schema_static.py:15-63`; current AP emit: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:800-826`; required fields: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:127-142`. |
| T2 | Parser/harness silently drops new telemetry or treats conditioned fields as raw | Extend `tests/test_im73d_audio_eval_harness.py` and `scripts/regression-harness/im73d_audio_eval.py` only if the command stays read-only | Add parser fixture row with all mic-auto-sense fields; add summary/quality checks that raw near-rail/clip fields remain the required verdict inputs; assert no calibration tokens are introduced. | `parse_ap_line()` captures new fields as numeric/string values; missing raw fields still invalid for mic-domain verdicts; harness remains read-only and does not send `start_noise_cal`, `N`, or `Y`. | Parser fixture: `tests/test_im73d_audio_eval_harness.py:21-40`; raw rail reject: `tests/test_im73d_audio_eval_harness.py:63-79`; DSR raw-metric requirement: `tests/test_im73d_audio_eval_harness.py:141-237`; design harness rule: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:54-56`, `:328-330`. |
| T3 | Raw/purity contamination by post-gain or auto-scale values | Extend `tests/test_im73d_audio_purity_static.py` | Add `test_mic_auto_sense_raw_metrics_are_pre_conditioning_and_not_ap_max_raw()` | New raw metrics must be computed before fixed IM73D gain, base sensitivity, any auto-sense state, loud guard, clamp, DC removal, response gain, GDFT, and AGC; `post_gain_peak` must be named/treated as conditioned, not raw. | Existing ordering tests: `tests/test_im73d_audio_purity_static.py:20-54`; current raw metric placement: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-376`; gain/sensitivity/clamp sequence: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:417-441`; design warning about AP/APCAP not raw: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:20-24`. |
| T4 | Telemetry-only slice accidentally applies auto-scale | Extend `tests/test_k1_loud_guard_static.py`; add `tests/test_mic_auto_sense_static.py` | Add `test_telemetry_phase_applied_scale_stays_one()` and `test_flag_off_effective_sensitivity_is_existing_path()` | In telemetry phase, applied scale remains `1.0f`; with flag off, effective sensitivity remains the current `CONFIG.SENSITIVITY * k1_loud_input_trim` path; no sample multiply by `auto_scale` is allowed until a later controller/shadow phase is explicitly scoped. | Current sensitivity path: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-117`, `:407-430`; existing loud-guard placement tests: `tests/test_k1_loud_guard_static.py:65-73`, `:138-145`; shadow requirement: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:424-432`. |
| T5 | Calibration firing by telemetry, serial, or wireless path | Extend `tests/test_serial_hotkeys_static.py`; add static auto-sense scan in `tests/test_mic_auto_sense_static.py` | Add `test_mic_auto_sense_never_calls_calibration_arm_confirm_or_start()` | Auto-sense source and integration call-sites must not reference `start_noise_cal`, `serial_arm_noise_cal`, `serial_confirm_noise_cal`, `sb_noise_cal_arm`, `sb_noise_cal_confirm`, `clear_noise_cal`, `noise_transition_queued`, bare `N`, or bare `Y`; any new command must be colon-prefixed/read-only. | Existing hotkey guard: `tests/test_serial_hotkeys_static.py:52-87`; current typed command table marks `start_noise_cal` armed/typed-only: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def:46-49`; wireless rejects direct start: `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:471-478`; WS registry rejection: `docs/protocol/k1-ws-controls-registry.yaml:78-84`; design stop condition: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:506-520`. |
| T6 | Persistence writes or sensitivity/config mutation from auto-sense | Extend `tests/test_calibration_profile_static.py`; add `tests/test_mic_auto_sense_static.py` | Add `test_mic_auto_sense_has_no_persistence_or_config_writes()` | Auto-sense files and integration region must not contain `CONFIG.SENSITIVITY =`, `save_config`, `save_config_delayed`, `save_ambient_noise_calibration`, `save_calibration_profile`, `LittleFS`, `Preferences`, `NVS`, or profile/calibration clear calls. Manual `global.sensitivity` remains the only sensitivity persistence path. | Existing calibration no-persist failure guard: `tests/test_calibration_profile_static.py:156-170`; heap/persistence helper scan pattern: `tests/test_calibration_profile_static.py:217-238`; current `start_noise_cal` and `clear_noise_cal` write surfaces: `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:53-94`; manual wireless sensitivity write: `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:747-751`; design no-persistence rule: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:28-31`, `:410-418`. |
| T7 | Core 0 hot-path heap/String/blocking/serial output | Add `tests/test_mic_auto_sense_static.py`; reuse strip-comment helper style from `tests/test_i2s_watchdog_static.py` | Add `test_mic_auto_sense_hot_path_is_heap_free_blocking_free_and_silent()` | New auto-sense source and any function called from `acquire_sample_chunk()` must not contain `String`, `std::string`, `std::vector`, `new`, `malloc`, `calloc`, `realloc`, `free`, `pvPortMalloc`, `heap_caps_`, `delay(`, `vTaskDelay`, `USBSerial`, `Serial.print`, `sort`, or production `portMAX_DELAY`; telemetry emission is allowed only in existing 1 Hz AP/status surfaces, not in the hot update path. | Design Core 0 rule: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:28-34`, `:410-418`; existing raw telemetry comment: `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-363`; watchdog/static style: `tests/test_i2s_watchdog_static.py:31-80`; current bounded-read structural gate: `tests/test_i2s_watchdog_static.py:48-67`. |
| T8 | Feature flag off drift and unreviewed build-surface change | Extend `tests/test_mic_stable_byte_gate_static.py` only if env/reference set changes; otherwise rely on existing byte gate | Add `tests/test_mic_auto_sense_static.py::test_auto_sense_flag_is_default_off()` and, if a new flag-on env is introduced, add a static wrapper/allowlist test for that env | `K1_MIC_AUTO_SENSE_V1` must not be in `[env:k1_hardware]` by default; flag-off SPH and IM73D invariant envs must stay stable-section byte-identical; a flag-on telemetry env must be explicit and non-default if needed for compile coverage. | Current build flags area: `platformio.ini:87-125`; IM73D envs: `platformio.ini:207-244`; byte gate reference test: `tests/test_mic_stable_byte_gate_static.py:1-52`; byte gate script envs/sections: `scripts/regression-harness/mic_stable_byte_gate.sh:35-40`, `:75-115`; wrapper allowlist: `scripts/agent/pio-build.sh:20-30`. |
| T9 | Serial/control surface accidentally adds write semantics | If adding a colon command, extend serial static tests; if adding wireless control, extend `tests/test_golden_master.py`/serial replay only when the surface is modelled there | Add `tests/test_mic_auto_sense_static.py::test_telemetry_phase_has_no_write_control_surface()`; if a read-only status command is added, assert `SC_SAFE` and no persistence/calibration calls | Telemetry phase should prefer AP stream or a read-only colon status command. No REST endpoint, no parallel `global.sensitivity` control, no write control, and no auto-sense entry in WS registry unless explicitly read-only and tested. Serial/control-surface changes that alter parsed command behaviour must also run golden serial replay. | Existing serial golden gate: `tests/test_golden_master.py:1-11`, `:54-80`; current WS control registry allowed/rejected sensitivity/calibration surface: `docs/protocol/k1-ws-controls-registry.yaml:35-84`; design serial/control note: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:485-490`. |
| T10 | Build compiles host-green but firmware fails | Build gate, not a Python test | No new test file unless a new env is added; if added, update `scripts/agent/pio-build.sh` allowlist and static-lock that change | After telemetry tests are written and implementation lands, compile `k1_hardware` and `k1_bench_im73d` through the guarded wrapper; if a dedicated flag-on telemetry env exists, compile that env too after adding it to the wrapper allowlist. Do not claim device proof from compile-only. | Design build commands: `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:493-501`; guarded wrapper: `scripts/agent/pio-build.sh:1-53`; current wrapper lacks `k1_prod_im73d`, so do not list it as a wrapper command unless the wrapper is intentionally updated. |

## Proposed New Test Files

1. `tests/test_mic_auto_sense_static.py`
   - Own the default-off flag, telemetry-only applied-scale invariant, no calibration calls, no persistence/config writes, hot-path safety, and no write-control-surface assertions.
   - Keep this static file source-text based, matching the style of `tests/test_im73d_audio_purity_static.py`, `tests/test_k1_loud_guard_static.py`, and `tests/test_i2s_watchdog_static.py`.

2. `tests/test_mic_auto_sense_controller.py`
   - Not required for the telemetry-only slice.
   - Required only for the later controller phase described in the design doc (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:370-396`, `:475-483`).

No device-proof test is required before the telemetry-only host slice. Bench shadow captures and Captain eyes-on belong to later shadow/controller phases (`docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:420-448`, `:522-535`).

## Gate Command Sequence

Minimum focused gate after writing failing tests and before/after telemetry implementation:

```bash
git diff --check
python3 -m pytest tests/test_audio_telemetry_schema_static.py tests/test_im73d_audio_purity_static.py tests/test_im73d_audio_eval_harness.py -q
python3 -m pytest tests/test_mic_auto_sense_static.py tests/test_k1_loud_guard_static.py tests/test_i2s_watchdog_static.py -q
python3 -m pytest tests/test_serial_hotkeys_static.py tests/test_calibration_profile_static.py tests/test_mic_stable_byte_gate_static.py -q
bash scripts/agent/pio-build.sh k1_hardware
bash scripts/agent/pio-build.sh k1_bench_im73d
bash scripts/regression-harness/mic_stable_byte_gate.sh
```

Conditional gate:

```bash
python3 -m pytest tests/test_golden_master.py -q
```

Run the conditional gate only if the slice changes serial/control parsing, command routing, or a modelled serial/control surface. If the implementation adds a dedicated flag-on telemetry env, add that env to `scripts/agent/pio-build.sh` intentionally, static-lock the allowlist, and compile it through the wrapper; do not bypass the wrapper with raw `pio run` in agent flow.

## Required Re-run Commands

Run these from `/Users/spectrasynq/SpectraSynq_K1_Firmware` to verify the test-surface claims and line anchors:

```bash
command rg --files tests
command rg -n "K1_MIC_AUTO_SENSE|k1_mic_auto|auto_scale|auto_state|auto_reason|raw_abs_peak|raw_rms|raw_clip_pct|raw_near_rail_pct|post_gain_peak|auto_window_sec" SPECTRASYNQ_K1_FIRMWARE tests scripts docs platformio.ini artifacts/self_calibrating_sensitivity_forensics_2026-07-10 docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md
command rg -n "raw_i16|raw_abs|raw_rms|raw_near|clip_pct|near_pct|input_trim|stream_agc|schema|telemetry|APCAP|AP\\]|dump_raw" tests scripts/regression-harness SPECTRASYNQ_K1_FIRMWARE/serial SPECTRASYNQ_K1_FIRMWARE/audio SPECTRASYNQ_K1_FIRMWARE/diag docs/protocol
command rg -n "start_noise_cal|noise_cal|calibration\\.noise|save_config|save_config_delayed|save_ambient_noise_calibration|save_calibration_profile|LittleFS|NVS|CONFIG\\.SENSITIVITY|sensitivity" tests SPECTRASYNQ_K1_FIRMWARE/serial SPECTRASYNQ_K1_FIRMWARE/control SPECTRASYNQ_K1_FIRMWARE/audio SPECTRASYNQ_K1_FIRMWARE/calibration SPECTRASYNQ_K1_FIRMWARE/persistence docs/protocol
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '18,56p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '127,142p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '320,339p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '410,432p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '459,501p'
nl -ba artifacts/self_calibrating_sensitivity_forensics_2026-07-10/orchestrator_synthesis.md | sed -n '69,77p'
nl -ba tests/test_audio_telemetry_schema_static.py | sed -n '1,120p'
nl -ba tests/test_im73d_audio_purity_static.py | sed -n '1,90p'
nl -ba tests/test_im73d_audio_eval_harness.py | sed -n '1,242p'
nl -ba tests/test_k1_loud_guard_static.py | sed -n '56,154p'
nl -ba tests/test_calibration_profile_static.py | sed -n '156,238p'
nl -ba tests/test_serial_hotkeys_static.py | sed -n '52,87p'
nl -ba tests/test_mic_stable_byte_gate_static.py | sed -n '1,56p'
nl -ba scripts/regression-harness/mic_stable_byte_gate.sh | sed -n '35,115p'
nl -ba scripts/agent/pio-build.sh | sed -n '1,53p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '100,210p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '359,441p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '780,826p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h | sed -n '53,94p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '471,478p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '747,751p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def | sed -n '46,49p'
nl -ba docs/protocol/k1-ws-controls-registry.yaml | sed -n '35,84p'
```

## Method Risk

The main way this can be wrong is if implementation chooses a different telemetry surface than `[AP]` or a colon-prefixed read-only status command. In that case, keep the same safety tests, but move the schema/parser assertions to the actual emitted surface and add a static routing test for that surface.
