# MAS-RISK-01 Risk Review - Mic Auto-Sense Telemetry/Controller

Date: 2026-07-10  
Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`  
Live checkout observed: `lane/dual-sync-phase0 @ cc97081`  
Verdict: `NOT_VERIFIED`

## Scope

Read-only red-team of what can go wrong with mic auto-sense telemetry/controller work. No source edits, no device/serial/flash/calibration/audio playback actions were run. This artefact is the only write for this task.

Important source-truth drift:

- `docs/agent/AGENT_EXECUTION_STANDARD.md` is referenced by repo instructions but is absent in this checkout.
- `docs/reference/codebase-map.md` and `docs/reference/fsm-reference.md` are absent in this checkout.
- The mic auto-sense design was drafted on `lane/im73d-pdm-eval`, while live bootstrap reports `lane/dual-sync-phase0 @ cc97081`.
- Firmware source has no current `K1_MIC_AUTO_SENSE_V1` / `k1_mic_auto_scale` implementation; matching hits are design/planning docs and artefacts only.

Default assumption stands: the feature is unsafe until host tests, branch authority, measurement proof, and authorised device proof say otherwise.

## Risk Register

| ID | Severity | Failure mode | Evidence anchor | Prevention test/gate | Implementation stop conditions |
| --- | --- | --- | --- | --- | --- |
| R1 | BLOCKER | Branch/lane drift causes an implementation against stale authority. The design doc was written for `lane/im73d-pdm-eval`, but current repo truth is `lane/dual-sync-phase0`; spec-index also preserves older IM73D status. | `AGENT_OS.md:36-47` defines branch/working tree as Tier 0; bootstrap output reported `lane/dual-sync-phase0 @ cc97081`; design doc says drafted on `lane/im73d-pdm-eval` at `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:3-6`; task plan records this as an open decision at `artifacts/mic_auto_sense_implementation_2026-07-10/task_plan.md:35-39`. | Before any implementation, record `git status --short --branch`, `git log --oneline -8`, and an orchestrator branch decision in the task plan. | Stop if implementation starts before Captain/orchestrator confirms whether `lane/dual-sync-phase0` or an IM73D lane is the target. Stop if spec/handoff claims are used without live git verification. |
| R2 | BLOCKER | Core 0 real-time regression: putting rolling statistics, sorting, serial output, LittleFS, heap, or blocking work in the audio acquisition/hot path can cause missed AP frames, watchdog trips, or audio-to-visual latency spikes. | Design forbids heap/String/blocking I/O/serial/sorting in Core 0 at `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:28-34` and directs the controller outside the per-sample loop at `:95-102`; current raw telemetry is already O(n), heap-free, and AP-stream-only at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-376`; the per-sample conditioning loop is `:417-465`; AP printing is 1 Hz at `:797-827`. | Add static tests that scan any `k1_mic_auto_sense*` code and `i2s_audio.h` touchpoint for `String`, `new`, `malloc`, `LittleFS`, `save_config`, `USBSerial.print`, sorting, and loops inside the per-sample loop beyond a single scalar multiply. Run `python3 -m pytest tests/test_mic_auto_sense_controller.py tests/test_k1_loud_guard_static.py tests/test_i2s_watchdog_static.py -q` after implementation. Timing claims require the repo's trace/dev timing gate, not scalar AP logs alone. | Stop if auto-sense update code is called per sample except for applying a precomputed scalar. Stop if any telemetry/controller path prints serial or touches persistence from Core 0. Stop if timing is claimed from compile/static proof only. |
| R3 | BLOCKER | Calibration poisoning: auto-sense could trigger or indirectly queue `start_noise_cal`, `N`, `Y`, or clear calibration without Captain-confirmed silence, corrupting `DC_OFFSET`, `SWEET_SPOT_MIN_LEVEL`, and spectral floors. | `.claude/CLAUDE.md:45-49` permanently forbids agent-auto-fired calibration; `start_noise_cal()` resets runtime calibration fields at `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:53-78`; `clear_noise_cal()` writes config/cal files at `:80-95`; wireless direct `start_noise_cal` is rejected at `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:471-475`; arm/confirm/clear are explicit controls at `:1015-1039`; render loop consumes `noise_transition_queued` and calls `start_noise_cal()` at `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1532-1539`. | Extend `tests/test_serial_hotkeys_static.py` and add auto-sense static tests proving no auto-sense file references `start_noise_cal`, `clear_noise_cal`, `noise_transition_queued`, `sb_noise_cal_confirm`, `calibration.noise.confirm`, or `Y`/`N` command emission. Run `python3 -m pytest tests/test_serial_hotkeys_static.py tests/test_calibration_profile_static.py -q`. | Stop if auto-sense can start, confirm, clear, or persist calibration. Stop if an implementation says it can "self calibrate" without the existing arm/confirm silence contract. |
| R4 | BLOCKER | Measurement dishonesty: conditioned `[AP] max_raw`, `peak_scaled`, `agc_debug`, APCAP, or semantic state could be treated as raw mic evidence, hiding clipping, bad wiring, or bad DSR comparisons. | Purity audit verdict says `[AP]`, `[APCAP]`, `agc_debug`, and semantic state are conditioned, not raw, at `docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md:21-31`; pipeline classification shows raw dump/telemetry before gain and AP `max_raw` after gain/clamp/DC at `:73-101`; current source computes raw IM73D telemetry before gain at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:359-376`, then applies IM73D gain/sensitivity/clamp/DC and updates `max_waveform_val_raw` at `:417-464`; AP output labels both raw_i16 and conditioned fields at `:800-825`. | Extend `tests/test_im73d_audio_purity_static.py` and `tests/test_audio_telemetry_schema_static.py` so controller inputs include raw/pre-conditioning metrics and reject AP-only raw claims. Measurement reports must record `CONFIG.SENSITIVITY`, `AUDIO_RESPONSE_GAIN`, `input_trim`, `gdft_trim`, `CAL_SOURCE`, `CAL_VALID`, `SWEET_SPOT_MIN_LEVEL`, and `DC_OFFSET` per audit `:120-123`. | Stop if any acceptance claim says "raw mic" from AP/AGC/semantic fields alone. Stop if auto-sense is enabled for DSR/SNR/purity captures unless explicitly shadowed/bypassed and recorded. |
| R5 | BLOCKER | Persistence/flash-wear and config corruption: implementing auto-scale by changing `CONFIG.SENSITIVITY` or calling save paths would churn LittleFS, mutate user/base product intent, and risk low-internal-RAM failures. | Design forbids v1 persistence at `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:28-29` and names runtime-only scale at `:95-102`; serial sensitivity persists via `CONFIG.SENSITIVITY` and `save_config_delayed()` at `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp:259-280`; wireless `global.sensitivity` persists at `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:747-752`; `save_config()` writes the whole config blob and has an internal-RAM guard at `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:31-65` and `:146-205`. | Static gate: auto-sense controller source must not contain `CONFIG.SENSITIVITY =`, `save_config`, `save_config_delayed`, `LittleFS`, or `global.sensitivity`. Run `python3 -m pytest tests/test_im73d_audio_purity_static.py tests/test_calibration_profile_static.py -q` plus a new persistence-negative test. | Stop if auto-scale persists, writes `CONFIG.SENSITIVITY`, overloads `audio_response_gain`, or routes through `global.sensitivity`. Stop if v1 survives reboot as anything other than reset-to-1.0 RAM state. |
| R6 | BLOCKER | Controller fights loud guard / AGC loops: auto-scale could increase gain while loud guard is trimming, or misread downstream AGC compensation as permission to boost, causing clipping, washed-out chroma, or oscillation. | Current effective sensitivity is `CONFIG.SENSITIVITY * k1_loud_input_trim` when loud guard is on at `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:115-118`; loud guard records clip/near duty and adjusts input/GDFT trim at `:130-193`; design requires PROTECT/downscale on clip, near, raw near-rail, `input_trim < 0.999`, or sustained saturation at `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:208-229`; loud guard thresholds live at `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:78-96`. | Host controller oracle fixtures must cover quiet/no music, weak active music, sudden transient, sustained loud, raw near-rail, conditioned peak pin without raw clipping, reduced input trim, invalid calibration, stale telemetry, and alternating quiet/loud as required by design `:373-397`. | Stop if controller can scale up when `input_trim < 0.999`, `clip_pct > 0`, `near_pct > 0`, raw near-rail is nonzero, calibration is invalid, telemetry is stale, or silence is detected. Stop if no hysteresis/dwell tests exist. |
| R7 | BLOCKER | Feature escapes default-off / flag-off invariance: telemetry/controller behaviour silently alters production SPH or IM73D baselines. | Design requires default-off `K1_MIC_AUTO_SENSE_V1` until host tests, bench proof, and Captain eyes-on at `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:32-34`; current `platformio.ini` has no `K1_MIC_AUTO` flag in source envs, and IM73D is currently isolated to specific envs at `platformio.ini:207-244`; stable-section byte gate protects `k1_hardware`, `k1_bench_reference`, and `k1_bench_im73d` at `scripts/regression-harness/mic_stable_byte_gate.sh:35-40` and `tests/test_mic_stable_byte_gate_static.py:40-52`. | Add flag boundary tests proving production/default envs do not define the feature flag until explicitly chosen. With flag off, run `bash scripts/regression-harness/mic_stable_byte_gate.sh` and relevant static tests. | Stop if the feature is ungated, enabled in `k1_hardware` by default, or changes stable-section byte fingerprints while nominally off. |
| R8 | BLOCKER | Wrong-device flash/proof decisions: auto-sense proof could be run on the wrong K1/env or on blocked `k1_prod_im73d`, producing dark LEDs or invalid mic conclusions. | `.claude/CLAUDE.md:51-69` requires port plus stable identity before device writes; spec-index says identity is chip ID, not port name at `docs/spec-index.md:70-81`; device registry makes identity non-negotiable and notes port drift at `docs/hardware/device-build-registry.md:16-43`; upload guard blocks `k1_prod_im73d` until a correctly wired production IM73D unit exists at `scripts/platformio/k1_upload_guard.py:101-113`; the block is tested at `tests/test_k1_upload_guard.py:108-120`. | Device proof, when in scope, must begin with registry read, live identity capture, explicit env/port, and guard result. For this read-only SSA, no device proof was run. | Stop if a plan uses `k1_prod_im73d` now, uses port names as identity, skips `k1_upload_guard.py`, or claims device proof from build success. |
| R9 | SUGGESTION | Protocol/control-surface drift: adding a REST endpoint or hidden WebSocket control would violate the AP-only WS contract and create untested persistence/control paths. | WebSocket controls are enumerated at `docs/protocol/k1-ws-contract.yaml:35-88`; REST contract is explicitly empty/not implemented at `docs/protocol/k1-rest-contract.yaml:1-8`; current control facade allowlist has no auto-sense controls at `SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp:379-451`. | If exposed, add only explicit WS state/control fields and matching contract/static tests. Do not add REST unless a future feature explicitly requires it. | Stop if auto-sense is controlled by REST or by an undocumented WebSocket field, or if it reuses `global.sensitivity` for hidden persistence. |
| R10 | SUGGESTION | False product acceptance: host green or compile green may be misreported as runtime/perceptual proof, while the feature changes music response and visual feel. | `.claude/CLAUDE.md:16-17` says compile/upload is not runtime proof and architecture is not success if visual impact regresses; design phases require shadow mode, bench A/B, and Captain eyes-on at `docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md:420-448`; firmware/build gates are listed separately at `:459-502`. | Report proof labels separately: source/static, host oracle, compile, shadow telemetry, bench A/B, Captain eyes-on. Do not collapse them. | Stop if an implementation closeout says verified without the phase label and evidence. Stop if Captain eyes-on is omitted for any claim that auto-sense "feels better" or improves visuals. |

## Required Implementation Stops

These are hard stops, not preferences:

1. Branch authority unresolved (`lane/dual-sync-phase0` vs IM73D handoff lane).
2. Any auto-sense path starts/confirms/clears calibration.
3. Any auto-sense path writes `CONFIG.SENSITIVITY`, calls persistence, or survives reboot in v1.
4. Any hot path work adds heap, `String`, serial output, LittleFS, sorting, unbounded loops, or blocking I/O.
5. Any measurement/purity claim uses conditioned AP/AGC/semantic fields as raw mic proof.
6. Any scale-up is possible during silence, invalid calibration, stale telemetry, clip/near/raw-near-rail, or loud-guard input trim.
7. Feature is not default-off or flag-off byte/stable-section proof is missing.
8. Device proof is attempted on blocked `k1_prod_im73d`, by port name alone, or without guard/identity evidence.

## Prevention Gate Stack

Minimum before applied controller:

```bash
python3 -m pytest tests/test_im73d_audio_purity_static.py tests/test_audio_telemetry_schema_static.py -q
python3 -m pytest tests/test_serial_hotkeys_static.py tests/test_calibration_profile_static.py -q
python3 -m pytest tests/test_k1_loud_guard_static.py tests/test_agc_perband_independence.py -q
python3 -m pytest tests/test_mic_auto_sense_controller.py -q
bash scripts/regression-harness/mic_stable_byte_gate.sh
scripts/agent/pio-build.sh k1_hardware
scripts/agent/pio-build.sh k1_bench_im73d
```

Device proof remains out of scope for this SSA. If later authorised, it must use registry + live chip/USB identity + upload guard, and must be labelled device proof rather than compile proof.

## Exact Re-run Commands For Decisive Claims

Run from `/Users/spectrasynq/SpectraSynq_K1_Firmware`.

```bash
nl -ba .claude/CLAUDE.md | sed -n '45,69p'
nl -ba AGENT_OS.md | sed -n '36,47p'
nl -ba AGENT_OS.md | sed -n '186,220p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '18,56p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '95,150p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '208,239p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '388,418p'
nl -ba docs/hardware/k1-auto-sensing-mic-sensitivity-scaling-design-2026-07-06.md | sed -n '420,512p'
nl -ba docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md | sed -n '21,31p'
nl -ba docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md | sed -n '73,123p'
nl -ba docs/hardware/im73d-audio-pipeline-purity-audit-2026-07-06.md | sed -n '125,190p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '115,193p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '359,465p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '482,570p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '797,827p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '213,267p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h | sed -n '53,95p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '379,451p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '471,475p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/control/sb_k1_control_facade.cpp | sed -n '1015,1039p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h | sed -n '31,65p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h | sed -n '146,205p'
nl -ba platformio.ini | sed -n '207,244p'
nl -ba scripts/platformio/k1_upload_guard.py | sed -n '101,113p'
nl -ba scripts/platformio/k1_upload_guard.py | sed -n '162,195p'
nl -ba tests/test_k1_upload_guard.py | sed -n '108,120p'
nl -ba scripts/regression-harness/mic_stable_byte_gate.sh | sed -n '35,40p'
nl -ba tests/test_mic_stable_byte_gate_static.py | sed -n '40,52p'
rg -n "K1_MIC_AUTO|auto_sense|mic_auto|auto-scale|auto_scale|k1_mic_auto_scale" SPECTRASYNQ_K1_FIRMWARE tests scripts docs artifacts/mic_auto_sense_implementation_2026-07-10
rg -n "start_noise_cal|clear_noise_cal|noise_transition_queued|sb_noise_cal_confirm|save_config\\(|save_config_delayed\\(|CONFIG\\.SENSITIVITY|LittleFS|USBSerial\\.|String|malloc|new " SPECTRASYNQ_K1_FIRMWARE/audio SPECTRASYNQ_K1_FIRMWARE/control SPECTRASYNQ_K1_FIRMWARE/serial SPECTRASYNQ_K1_FIRMWARE/persistence tests
```

## Method Risk

The main way this review can be wrong is by judging a planned feature from current seams rather than reviewing an actual implementation diff. That is why the verdict remains `NOT_VERIFIED`, and why the stop conditions focus on gates that must exist before any applied controller is accepted.
