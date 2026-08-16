# FRTOS-13 — codebase read, chunk 5

## Scope and provenance

- Repository root gate: `PASS` — `/Users/spectrasynq/SpectraSynq_K1_Firmware`
- Source manifest: `/tmp/k1-source-manifest.WdLSdO/first_party_sources.txt`
- Source manifest SHA-256: `06b03c3d0a3c6352e5383ffea151f579636adc66394c73b556add68f74c5e0b7`
- Assigned chunk: `/tmp/k1-source-manifest.WdLSdO/chunk_5.txt`
- Assigned chunk SHA-256: `cef3530e39e720c1f237622b4b6f088c91b88ccb3d53e1421cf5831173cb82ee`
- Assigned path count: **76**
- `READ_IN_FULL` count: **76**
- Failure count: **0**

Each assigned file was read from first line through EOF with line-numbered output. Large files were read in contiguous, non-overlapping pages; output truncation was handled by re-reading the affected file in smaller contiguous pages. This was not a grep-only survey. No build, test, Git mutation, or device action was performed.

## Per-file read ledger

| # | Assigned path | Status |
|---:|---|---|
| 1 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_ap_drive_contract.h` | `READ_IN_FULL` |
| 2 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.h` | `READ_IN_FULL` |
| 3 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_musical_saliency.h` | `READ_IN_FULL` |
| 4 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stereo_probe.h` | `READ_IN_FULL` |
| 5 | `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h` | `READ_IN_FULL` |
| 6 | `SPECTRASYNQ_K1_FIRMWARE/control/k1_show_state.cpp` | `READ_IN_FULL` |
| 7 | `SPECTRASYNQ_K1_FIRMWARE/diag/k1_ap_twitch_oracle.cpp` | `READ_IN_FULL` |
| 8 | `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp` | `READ_IN_FULL` |
| 9 | `SPECTRASYNQ_K1_FIRMWARE/director/k1_mode_selection.cpp` | `READ_IN_FULL` |
| 10 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EasingCurves.h` | `READ_IN_FULL` |
| 11 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/FrameBlend.cpp` | `READ_IN_FULL` |
| 12 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/RenderPrimitives.cpp` | `READ_IN_FULL` |
| 13 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/ZoneComposer.cpp` | `READ_IN_FULL` |
| 14 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_beat_prism.h` | `READ_IN_FULL` |
| 15 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_registry_compile_probe.cpp` | `READ_IN_FULL` |
| 16 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_chromagram_gradient.cpp` | `READ_IN_FULL` |
| 17 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_kaleidoscope.cpp` | `READ_IN_FULL` |
| 18 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_spectrum_river_v2.cpp` | `READ_IN_FULL` |
| 19 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform.cpp` | `READ_IN_FULL` |
| 20 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_decoder.cpp` | `READ_IN_FULL` |
| 21 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_tx.h` | `READ_IN_FULL` |
| 22 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_wireless.h` | `READ_IN_FULL` |
| 23 | `SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.h` | `READ_IN_FULL` |
| 24 | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_parse_helpers.h` | `READ_IN_FULL` |
| 25 | `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` | `READ_IN_FULL` |
| 26 | `SPECTRASYNQ_K1_FIRMWARE/system/presets.h` | `READ_IN_FULL` |
| 27 | `SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.cpp` | `READ_IN_FULL` |
| 28 | `scripts/agent/deck16-first-contact-gate.sh` | `READ_IN_FULL` |
| 29 | `scripts/ble_midi/gen_k1_ble_midi_header.py` | `READ_IN_FULL` |
| 30 | `scripts/dual_sync_probe/f2_image_set.py` | `READ_IN_FULL` |
| 31 | `scripts/dual_sync_probe/run_f2_abc.sh` | `READ_IN_FULL` |
| 32 | `scripts/dual_sync_probe/synth.py` | `READ_IN_FULL` |
| 33 | `scripts/loop/tempo_loop.py` | `READ_IN_FULL` |
| 34 | `scripts/refactor/gen_serial_typed_table.py` | `READ_IN_FULL` |
| 35 | `scripts/regression-harness/ap_input_integrity_device.py` | `READ_IN_FULL` |
| 36 | `scripts/regression-harness/bt_acf_4way.py` | `READ_IN_FULL` |
| 37 | `scripts/regression-harness/device_ap_cadence_matrix.py` | `READ_IN_FULL` |
| 38 | `scripts/regression-harness/edgemixer_parity_probe.cpp` | `READ_IN_FULL` |
| 39 | `scripts/regression-harness/gdft_check.py` | `READ_IN_FULL` |
| 40 | `scripts/regression-harness/golden/oracle_bridge_fs_config.py` | `READ_IN_FULL` |
| 41 | `scripts/regression-harness/golden/oracle_render.py` | `READ_IN_FULL` |
| 42 | `scripts/regression-harness/hue_coverage.py` | `READ_IN_FULL` |
| 43 | `scripts/regression-harness/k1_godark_darkproof.py` | `READ_IN_FULL` |
| 44 | `scripts/regression-harness/k1_phase345_runtime_proof.py` | `READ_IN_FULL` |
| 45 | `scripts/regression-harness/k1_trace_capture.py` | `READ_IN_FULL` |
| 46 | `scripts/regression-harness/mic_health_model_test.cpp` | `READ_IN_FULL` |
| 47 | `scripts/regression-harness/onset_beat_event_metrics.py` | `READ_IN_FULL` |
| 48 | `scripts/regression-harness/parse_serial.py` | `READ_IN_FULL` |
| 49 | `scripts/regression-harness/replay_device_apdbg.py` | `READ_IN_FULL` |
| 50 | `scripts/regression-harness/serial_menu_second_tu_smoke.cpp` | `READ_IN_FULL` |
| 51 | `scripts/regression-harness/spaces/lgp_bloom_sample.py` | `READ_IN_FULL` |
| 52 | `scripts/regression-harness/stm_reference_512.py` | `READ_IN_FULL` |
| 53 | `scripts/regression-harness/stubs/USB.h` | `READ_IN_FULL` |
| 54 | `scripts/regression-harness/test_acf_salience.cpp` | `READ_IN_FULL` |
| 55 | `scripts/regression-harness/vp_diff.py` | `READ_IN_FULL` |
| 56 | `scripts/regression-harness/vpml_compiler.py` | `READ_IN_FULL` |
| 57 | `scripts/regression-harness/vpml_workbench.py` | `READ_IN_FULL` |
| 58 | `scripts/tools/gen_tunables.py` | `READ_IN_FULL` |
| 59 | `tests/test_agc_perband_independence.py` | `READ_IN_FULL` |
| 60 | `tests/test_ble_midi_firmware_decoder.py` | `READ_IN_FULL` |
| 61 | `tests/test_cc14_productisation.py` | `READ_IN_FULL` |
| 62 | `tests/test_deck_state_v1.py` | `READ_IN_FULL` |
| 63 | `tests/test_edgemixer_static.py` | `READ_IN_FULL` |
| 64 | `tests/test_fw_strings_removed_static.py` | `READ_IN_FULL` |
| 65 | `tests/test_i2s_watchdog_static.py` | `READ_IN_FULL` |
| 66 | `tests/test_k1_device_identity_guard.py` | `READ_IN_FULL` |
| 67 | `tests/test_k1_pin_evidence_static.py` | `READ_IN_FULL` |
| 68 | `tests/test_k1_upload_guard_identity_static.py` | `READ_IN_FULL` |
| 69 | `tests/test_mic_health_model.py` | `READ_IN_FULL` |
| 70 | `tests/test_onset_beat_event_metrics.py` | `READ_IN_FULL` |
| 71 | `tests/test_probe_diff_tool.py` | `READ_IN_FULL` |
| 72 | `tests/test_session_canon_2026_08_07_static.py` | `READ_IN_FULL` |
| 73 | `tests/test_snapwave_pulse_static.py` | `READ_IN_FULL` |
| 74 | `tests/test_tab5_protocol_parity_gate.py` | `READ_IN_FULL` |
| 75 | `tests/test_vp_probe_mode_coverage_static.py` | `READ_IN_FULL` |
| 76 | `tests/test_vpml_run_console.py` | `READ_IN_FULL` |

## Architectural findings relevant to scheduling, publication, and timing

### 1. Real-time ownership and explicit scheduling contracts

- `process_GDFT()` is explicitly declared as an IRAM audio-processing entry point in `audio/k1_gdft_core.h:26-31`; the surrounding contract places GDFT/novelty on the Core-0 hard-real-time path. Any scheduler change has to preserve that ownership and IRAM/hot-path character.
- The bench stereo probe is carefully split: its audio hook is O(n), heap-free, and silent (`audio/k1_stereo_probe.h:26-31`), whereas serial dump is explicitly blocking and allowed to starve audio only post-leg (`audio/k1_stereo_probe.h:11-16`). That separation is a reusable rule for future instrumentation.
- The checked-in watchdog structural gate states that the audio loop must grant IDLE0 a real scheduling slot with `vTaskDelay(1)` rather than `yield()`, and that both audio and render tasks are watchdog-fed (`tests/test_i2s_watchdog_static.py:83-129`). This is source-structural evidence, not current on-device efficacy proof.
- Current diagnostic timing constants disable VP audit/probes by default and define an 8,333 us frame budget plus a 2,000 us render budget (`system/constants.h:176-202`). These source constants imply a 120 Hz budget even though some older comments/tools still describe 100 FPS; the audit should resolve that source-of-truth mismatch before changing cadence.

### 2. Cross-context publication and critical-section surfaces

- VPAB owns two independent `portMUX_TYPE` locks (`diag/vpab_capture.cpp:28-29`): one for capture state and one for render-context publication. Capture reset/arm/stop are protected (`diag/vpab_capture.cpp:655-715`), and each render tick increments cadence state inside the capture lock before performing metric/byte pushes outside it (`diag/vpab_capture.cpp:717-781`). This keeps long payload work outside the critical section, but the enabled probe still adds bounded work to the render path.
- Mode selection serialises the full resolve path under one `portMUX`, including initialisation, window/dwell/cooldown checks, and registry-backed allow lookup (`director/k1_mode_selection.cpp:18-36,74-153`). The source itself notes that live lock-state access is unavailable inside this lock (`director/k1_mode_selection.cpp:27-29`). This critical section should stay short and must not grow to include blocking publication or dynamic allocation.
- `ZoneComposer::setLayout()` disables the render path while mutating layout and republishes enablement using atomic release/acquire semantics (`effects/framework/ZoneComposer.cpp:84-102,165-169`). This is a deliberate cross-core publication pattern. Per-zone time is advanced from `deltaTimeSeconds` (`effects/framework/ZoneComposer.cpp:218-228`).
- A boundary risk remains in `ZoneComposer`: a new effect's one-time `effect->init(ctx)` can execute from `renderZone()` (`effects/framework/ZoneComposer.cpp:230-238`). The comment delegates safety to each effect. That is not enough to prove the global no-heap/no-blocking render contract unless every reachable `init()` is separately constrained or pre-initialised off the render path.
- The render primitive scratch buffer is file-static and explicitly relies on single-threaded Core-1 ownership rather than a guard (`effects/framework/RenderPrimitives.cpp:1-9,27-29`). Moving or parallelising render calls would introduce a data race unless that ownership is preserved.
- K1 render trace uses volatile arm/frame state with a single-writer assumption, copies RGB bytes on selected render frames, and increments publication state without a lock (`visual/k1_render_trace.cpp:21-29,50-69`). Arm ordering stops the writer before resetting state (`visual/k1_render_trace.cpp:78-98`), but `volatile` alone is not a formal cross-core publication guarantee if command dispatch and render run on different cores. This probe-only surface warrants an explicit ownership/atomicity statement.

### 3. Cadence-dependent visual behaviour

- Some framework effects are delta-time correct: frame blending exponentiates persistence by `dt * 120` (`effects/framework/FrameBlend.cpp:59-70`), and scrolled sprite alpha does the same (`effects/framework/RenderPrimitives.cpp:143-149`).
- Three assigned production effects remain invocation-rate dependent:
  - Kaleidoscope uses fixed per-call attack `0.1` and decay `0.99`, then advances position once per invocation (`effects/light_mode_kaleidoscope.cpp:47-55,63-80`).
  - Spectrum River v2 uses a fixed `0.05` per-call tide EMA and per-call drift (`effects/light_mode_spectrum_river_v2.cpp:30-34,46-61`).
  - Waveform ignores its `last_frame_ms`/shift accumulator inputs, smooths with fixed `0.08/0.92`, and shifts exactly one pixel per call (`effects/light_mode_waveform.cpp:3-10,92-96`).

  Changing render scheduling without converting these paths to elapsed-time semantics will change their apparent attack, decay, and speed. This is a concrete scheduler-hardening dependency, not visual polish.

### 4. Network/control publication depends on bounded poll cadence

- Deck state apply publication queues deltas, while `k1_deck_state_tx_poll()` drains the bounded queue and performs overflow recovery; HWM, overflow, and depth counters are exposed (`network/k1_deck_state_tx.h:17-34`). The scheduler therefore needs a documented upper bound on wireless poll latency, otherwise bursts can force resnapshot recovery.
- BLE-MIDI CC14 pairing stores the externally supplied `now_ms` on MSB receipt and rejects an LSB when age exceeds the pairing window (`network/k1_ble_midi_decoder.cpp:207-242,283-288`). The tests pin a 50 ms inclusive boundary (`tests/test_cc14_productisation.py:124-151`). Poll/controller cadence and timestamp update location are therefore semantically observable, not merely performance choices.
- `tests/test_deck_state_v1.py:145-171` pins a sound callback-to-task handoff on Tab5: NimBLE callbacks must enqueue link/payload events and the loop task drains them, avoiding direct state/LVGL calls from callback context. That is a useful counterpart for K1-side publication design.

### 5. Blocking persistence and diagnostics must remain outside hot paths

- Noise calibration mutates shared `CONFIG` and spectral state, emits serial output, and can synchronously persist configuration/profile data (`calibration/noise_cal.h:19-40,135-160`). It must remain command/calibration work rather than an AP-frame responsibility.
- Show-state save/load performs synchronous LittleFS open/read/write/close and an immediate `save_config()` flush (`control/k1_show_state.cpp:251-285`). These operations need explicit non-real-time ownership.
- The AP twitch oracle traverses/copies both LED arrays and updates histograms every active render tick while measuring its own maximum cost (`diag/k1_ap_twitch_oracle.cpp:108-149`). It is diagnostic work and should not be treated as production timing evidence without subtracting probe overhead.
- Render trace allocates PSRAM only when armed (`visual/k1_render_trace.cpp:31-47`); its dump disables capture, streams every frame, and yields every 64 frames because post-capture dumping is allowed to starve render (`visual/k1_render_trace.cpp:101-132`). This is a correct offline-dump boundary, not a pattern for live telemetry.

### 6. Existing timing oracles and their evidence boundary

- `device_ap_cadence_matrix.py` is the strongest assigned timing oracle. It defines AP/VP core-pinning variants (`scripts/regression-harness/device_ap_cadence_matrix.py:28-82`) and gates measured AP/novelty rates within 2%, p95 work under the AP period, maximum work under the DMA cushion, clean I2S, expected cores, and replay behaviour (`scripts/regression-harness/device_ap_cadence_matrix.py:167-228`). It is explicitly non-shippable and flashes/configures a device (`:2-7`), so it was not run here.
- `replay_device_apdbg.py` reconstructs three AP frames per accepted novelty event with `1000 / (12800 / 96)` timing (`scripts/regression-harness/replay_device_apdbg.py:35,81-82`). It is a temporal model for replay, not proof of actual FreeRTOS wake-up/jitter behaviour.
- Host render/oracle tools (`golden/oracle_render.py`, `vp_diff.py`, `hue_coverage.py`, `vpml_compiler.py`, `vpml_workbench.py`) provide deterministic output, structural, or command-boundary evidence. They do not establish task priority, core placement, jitter, or end-to-end device latency.
- The mic-health harness advances a synthetic fixed clock, and the ACF/replay tools contain copied or reconstructed algorithmic models. They are valuable mutation/property gates but must not be promoted to runtime scheduler proof.

## Read-count reconciliation

`chunk_5.txt` contains **76** newline-delimited assigned paths. The ledger above contains **76** entries marked `READ_IN_FULL`; there are **0** read failures. Count reconciles exactly: **76 / 76**.
