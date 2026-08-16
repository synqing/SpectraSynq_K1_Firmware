# FRTOS-14 — codebase read, chunk 6

## Scope and provenance

- Repository root gate: `PASS` — `/Users/spectrasynq/SpectraSynq_K1_Firmware`
- Source manifest: `/tmp/k1-source-manifest.WdLSdO/first_party_sources.txt`
- Source manifest SHA-256: `06b03c3d0a3c6352e5383ffea151f579636adc66394c73b556add68f74c5e0b7`
- Assigned chunk: `/tmp/k1-source-manifest.WdLSdO/chunk_6.txt`
- Assigned chunk SHA-256: `4e53ffd51eb6465a866436484677e23eecd2c8fa313309e39966094751208e56`
- Assigned path count: **76**
- `READ_IN_FULL` count: **76**
- Failure count: **0**

Each assigned file was read from first line through EOF. Large files were read in contiguous pages; any tool-output truncation was handled by re-reading the affected file in smaller contiguous pages. This was not a grep-only survey. No build, test, Git mutation/state operation, or device action was performed. The only Git invocation was the contract-mandated read-only repository-root identity gate.

## Per-file read ledger

| # | Assigned path | Status |
|---:|---|---|
| 1 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_ap_structured_evidence.h` | `READ_IN_FULL` |
| 2 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_i2s_capture_types.h` | `READ_IN_FULL` |
| 3 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.cpp` | `READ_IN_FULL` |
| 4 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.cpp` | `READ_IN_FULL` |
| 5 | `SPECTRASYNQ_K1_FIRMWARE/control/k1_control_facade.cpp` | `READ_IN_FULL` |
| 6 | `SPECTRASYNQ_K1_FIRMWARE/control/k1_show_state.h` | `READ_IN_FULL` |
| 7 | `SPECTRASYNQ_K1_FIRMWARE/diag/k1_ap_twitch_oracle.h` | `READ_IN_FULL` |
| 8 | `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.h` | `READ_IN_FULL` |
| 9 | `SPECTRASYNQ_K1_FIRMWARE/director/k1_mode_selection.h` | `READ_IN_FULL` |
| 10 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectContext.h` | `READ_IN_FULL` |
| 11 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/FrameBlend.h` | `READ_IN_FULL` |
| 12 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/RenderPrimitives.h` | `READ_IN_FULL` |
| 13 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/ZoneComposer.h` | `READ_IN_FULL` |
| 14 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_flux_rift.cpp` | `READ_IN_FULL` |
| 15 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/framework_compile_probe.cpp` | `READ_IN_FULL` |
| 16 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_comet.cpp` | `READ_IN_FULL` |
| 17 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_percussion_burst.cpp` | `READ_IN_FULL` |
| 18 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet.cpp` | `READ_IN_FULL` |
| 19 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp` | `READ_IN_FULL` |
| 20 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_decoder.h` | `READ_IN_FULL` |
| 21 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_v1.cpp` | `READ_IN_FULL` |
| 22 | `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h` | `READ_IN_FULL` |
| 23 | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.cpp` | `READ_IN_FULL` |
| 24 | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_tx.cpp` | `READ_IN_FULL` |
| 25 | `SPECTRASYNQ_K1_FIRMWARE/system/globals.cpp` | `READ_IN_FULL` |
| 26 | `SPECTRASYNQ_K1_FIRMWARE/system/system.h` | `READ_IN_FULL` |
| 27 | `SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.h` | `READ_IN_FULL` |
| 28 | `scripts/agent/k1-flash-verified.sh` | `READ_IN_FULL` |
| 29 | `scripts/ble_midi/guard_k1_radio_isolation.py` | `READ_IN_FULL` |
| 30 | `scripts/dual_sync_probe/f2_ports.py` | `READ_IN_FULL` |
| 31 | `scripts/dual_sync_probe/run_f2_create.sh` | `READ_IN_FULL` |
| 32 | `scripts/git_session_end.sh` | `READ_IN_FULL` |
| 33 | `scripts/platformio/k1_build_provenance.py` | `READ_IN_FULL` |
| 34 | `scripts/refactor/r1_move_serial_menu_defs.py` | `READ_IN_FULL` |
| 35 | `scripts/regression-harness/ap_input_twitch_oracle.py` | `READ_IN_FULL` |
| 36 | `scripts/regression-harness/captain_fixture_spot_check.py` | `READ_IN_FULL` |
| 37 | `scripts/regression-harness/device_novelty_buffer_capture.py` | `READ_IN_FULL` |
| 38 | `scripts/regression-harness/export_diagnostic_trajectories.py` | `READ_IN_FULL` |
| 39 | `scripts/regression-harness/gdft_true_center_scalloping.py` | `READ_IN_FULL` |
| 40 | `scripts/regression-harness/golden/oracle_build_config_policy.py` | `READ_IN_FULL` |
| 41 | `scripts/regression-harness/golden/oracle_serial_replay.py` | `READ_IN_FULL` |
| 42 | `scripts/regression-harness/im73d_audio_eval.py` | `READ_IN_FULL` |
| 43 | `scripts/regression-harness/k1_godark_measure.py` | `READ_IN_FULL` |
| 44 | `scripts/regression-harness/k1_pin_evidence_summary.py` | `READ_IN_FULL` |
| 45 | `scripts/regression-harness/k1_trace_l1_gate.py` | `READ_IN_FULL` |
| 46 | `scripts/regression-harness/mic_stable_byte_gate.sh` | `READ_IN_FULL` |
| 47 | `scripts/regression-harness/onset_beat_replay.py` | `READ_IN_FULL` |
| 48 | `scripts/regression-harness/recover_eval_summary.py` | `READ_IN_FULL` |
| 49 | `scripts/regression-harness/row1_dispatch_table_test.cpp` | `READ_IN_FULL` |
| 50 | `scripts/regression-harness/serial_typed_dispatch_table_test.cpp` | `READ_IN_FULL` |
| 51 | `scripts/regression-harness/spaces/lgp_real_measure.py` | `READ_IN_FULL` |
| 52 | `scripts/regression-harness/stm_vp_compare.py` | `READ_IN_FULL` |
| 53 | `scripts/regression-harness/stubs/esp_random.h` | `READ_IN_FULL` |
| 54 | `scripts/regression-harness/test_wireless_ab_gate0.py` | `READ_IN_FULL` |
| 55 | `scripts/regression-harness/vpab_frame_capture.py` | `READ_IN_FULL` |
| 56 | `scripts/regression-harness/vpml_evidence_page.py` | `READ_IN_FULL` |
| 57 | `scripts/regression-harness/wireless_ab_bench.py` | `READ_IN_FULL` |
| 58 | `scripts/tools/probe_diff.py` | `READ_IN_FULL` |
| 59 | `tests/test_ap_input_integrity_p2.py` | `READ_IN_FULL` |
| 60 | `tests/test_boot_intro_static.py` | `READ_IN_FULL` |
| 61 | `tests/test_chord_hue_consumer_static.py` | `READ_IN_FULL` |
| 62 | `tests/test_dev_instrumentation_boundary.py` | `READ_IN_FULL` |
| 63 | `tests/test_effect_queue_static.py` | `READ_IN_FULL` |
| 64 | `tests/test_gdft_center_honesty.py` | `READ_IN_FULL` |
| 65 | `tests/test_im69d_consumer_floors_behavioural.py` | `READ_IN_FULL` |
| 66 | `tests/test_k1_godark_static.py` | `READ_IN_FULL` |
| 67 | `tests/test_k1_real_music_corpus_capture.py` | `READ_IN_FULL` |
| 68 | `tests/test_k1_wireless_control_static.py` | `READ_IN_FULL` |
| 69 | `tests/test_mic_stable_byte_gate_static.py` | `READ_IN_FULL` |
| 70 | `tests/test_onset_beat_replay.py` | `READ_IN_FULL` |
| 71 | `tests/test_rate_consistency.py` | `READ_IN_FULL` |
| 72 | `tests/test_show_state_static.py` | `READ_IN_FULL` |
| 73 | `tests/test_spectral_honesty.py` | `READ_IN_FULL` |
| 74 | `tests/test_token_scrub_static.py` | `READ_IN_FULL` |
| 75 | `tests/test_vpab_frame_gate.py` | `READ_IN_FULL` |
| 76 | `tests/test_vpml_run_console_server.py` | `READ_IN_FULL` |

## Architectural findings relevant to scheduling, publication, and timing

### 1. The intended topology and rate domains are explicit, but the render contract is internally inconsistent

- The production structural gate expects Arduino/Core 0 for AP, a dedicated LED task on Core 1, three I2S DMA descriptors, a 12.8 kHz sample rate, 96-sample chunks, and novelty decimation by three (`tests/test_dev_instrumentation_boundary.py:147-159`). The rate-consistency gate correctly treats AP at 133.33 Hz and novelty at 44.44 Hz as distinct domains and mutation-tests 2x/0.5x drift (`tests/test_rate_consistency.py:1-21,261-305`). These are source/static contracts, not current device proof.
- Onset V2 runs every AP frame at 133.33 Hz and derives its frame-count windows/EMA constants from that cadence (`audio/k1_onset_beat.cpp:21-23,46-77`). STM similarly hard-codes a 17-frame/127.5 ms window, a 4 Hz coefficient, and EMA coefficients at 133.33 Hz (`audio/k1_stm.cpp:21-35`). Any AP cadence redesign must re-derive these constants rather than only changing task periods.
- `EffectContext` says the live render loop is free-running and measured at roughly 100–185 FPS, while also declaring `K1_TARGET_FPS = 100` and describing an 8,333 us budget as the target (`effects/framework/EffectContext.h:32-41,61-66`). 8,333 us is 120 FPS, not 100 FPS. `FrameBlend` and `RenderPrimitives` retain explicit TODOs around their 120-FPS persistence baseline (`effects/framework/FrameBlend.h:15-19,39-44`; `effects/framework/RenderPrimitives.h:20-25,73-82`). The hardening design needs one authoritative render cadence/budget and separate coefficient-reference semantics.

### 2. Onset publication is coherent per snapshot but intentionally latest-value, not lossless event delivery

- The onset producer owns one shared `K1OnsetBeatEvent`, and publish/read copy the complete struct inside the same `portMUX` critical section (`audio/k1_onset_beat.cpp:6-7,401-405,651-656`). This prevents torn struct reads.
- V2 increments monotonic IDs for transient/kick/snare/hihat and publishes the current IDs with the level flags (`audio/k1_onset_beat.cpp:326-346`). Consumers such as Comet and Percussion Burst detect only `id != last_id` and spawn at most once per render call (`effects/light_mode_comet.cpp:91-118`; `effects/light_mode_percussion_burst.cpp:156-188`). Therefore two or more AP events published during one delayed render interval collapse to one visible consumer action; an ID jump exposes that loss but does not replay the missing multiplicity. Scheduler stalls make this loss mode more likely.
- Percussion Burst explicitly advances each event cursor even when its bounded eight-slot pool cannot spawn, and drops snare/hihat first under occupancy pressure (`effects/light_mode_percussion_burst.cpp:93-100,156-188,190-231`). This is a deliberate lossy backpressure policy and should be documented as such in any end-to-end event-delivery guarantee.
- The older beat/onset fields are level-windowed for 80 ms and re-read before each update (`audio/k1_onset_beat.cpp:372-374,486-499`). A consumer that samples only boolean levels is inherently cadence-sensitive; event IDs are the stronger publication surface.
- `k1_ap_structured_evidence_tick()` is scheduler-stall defensive: it caps elapsed contribution at 50 ms so a pause cannot turn one sample into a completed wake decision (`audio/k1_ap_structured_evidence.h:12-41`). That is a sound bounded-catch-up pattern.

### 3. Control-state publication is not a coherent generation snapshot

- The control facade directly mutates individual `CONFIG`/secondary globals and queues persistence (`control/k1_control_facade.cpp:458-540`). Its sequence counter is a plain `uint32_t`; it increments only while constructing successful results (`control/k1_control_facade.cpp:23-31,44-59`).
- `k1_control_snapshot()` reads a large mixture of transition flags, primary globals, secondary globals, FPS, a separately protected tempo snapshot, scene text, and finally the plain sequence counter, without a facade lock or before/after generation validation (`control/k1_control_facade.cpp:1017-1045`). Consequently the returned `seq` does not prove that the aggregate state belongs to one atomic generation. A concurrent Core-1 read can also observe partially applied groups unless external serialisation exists outside this assigned source set.
- The queue tests preserve a better pattern for mode/palette browsing: command-side code arms pending state, and Core 1 applies it at a frame boundary (`tests/test_effect_queue_static.py:140-150`). That frame-boundary handoff should be the model for multi-field control publication, not direct piecemeal mutation.
- `ZoneComposer` uses release/acquire only for `m_enabled`; layout, per-zone state, pointers, and strip binding are otherwise ordinary fields (`effects/framework/ZoneComposer.h:96-112,147-169`). The comment says preceding command-path writes become visible after enable acquisition, but repeated setters while already enabled are not protected by that one boolean. This is a potential cross-core race unless external disable-before-mutate discipline is universally enforced.

### 4. Several visual paths still change behaviour with scheduler cadence

- Comet, Percussion Burst, Tempo Comet, and Waveform Fast calculate elapsed time from `millis()` and cap it at 50 ms (`effects/light_mode_comet.cpp:72-83`; `effects/light_mode_percussion_burst.cpp:119-126`; `effects/light_mode_tempo_comet.cpp:71-77`; `effects/light_mode_waveform_fast.cpp:10-24`). The cap prevents unstable catch-up, but a stall longer than 50 ms intentionally loses elapsed motion time.
- Tempo Comet advances phase and phase correction with `dt`, but learns BPM with a fixed per-render-call `TC_BPM_EMA = 0.05` (`effects/light_mode_tempo_comet.cpp:43-58,100-125`). Its lock-learning time constant therefore changes with render FPS.
- Waveform Fast transports with `dt` but smooths peak with fixed `0.05/0.95` per call (`effects/light_mode_waveform_fast.cpp:45-52`). This directly violates the repository's dt-correct temporal-smoothing constraint under a free-running scheduler.
- STM's smoothing is also fixed-per-AP-frame (`audio/k1_stm.cpp:29-35,195-217`). That is valid only while AP remains at the derived 133.33 Hz cadence.

### 5. A render-path serial/debug path can create jitter and corrupt framing

- Waveform Fast performs an O(N) previous-buffer sum and multiple synchronous `USBSerial.print()` calls from the render function every 500 ms in `debug_mode`; its rate limiter is one file-static timestamp shared by primary and secondary channels (`effects/light_mode_waveform_fast.cpp:28-43`). This is a direct render-path blocking/jitter hazard.
- The serial envelope implementation writes framing and payload directly and has no mutex/critical-section protection (`serial/serial_tx.cpp:27-58`). If render debug output and Core-0 serial responses overlap, output can interleave inside `sbr{{...}}`/`sberr[[...]]` envelopes. Removing render-path prints or routing all serial output through one bounded owner is a scheduler-hardening dependency, not cosmetic logging work.
- `stop_streams()` also writes a broad set of shared stream flags without synchronisation (`serial/serial_tx.cpp:60-80`). This is safe only if all readers/writers obey a single-owner or sufficiently atomic flag contract, which is not stated in this file.

### 6. LittleFS paths contain three confirmed LED-lock leaks and non-composable lock ownership

- `save_config()` calls `lock_leds()`, then returns on `LittleFS.open()` failure without `unlock_leds()` (`persistence/bridge_fs.h:165-185`).
- `load_config()` has the same failure shape: it takes the LED lock and returns after a missing/open-failed config without releasing it (`persistence/bridge_fs.h:243-271`).
- `save_ambient_noise_calibration()` likewise returns with the LED lock held if its file open fails (`persistence/bridge_fs.h:337-358`). The newer calibration-profile writer does release on its analogous open failure (`persistence/bridge_fs.h:431-452`), demonstrating the intended pattern.
- The file documents `lock_leds()` as a flag-set rather than a recursive counter (`persistence/bridge_fs.h:327-330`), yet `init_fs()` takes the flag and calls multiple helpers that take and release it themselves before the outer unlock (`persistence/bridge_fs.h:588-601`). Therefore the apparent outer critical region is not actually preserved across initialisation.
- Persistence is synchronous: `save_config()` writes 512 bytes one byte at a time while the LED lock is held (`persistence/bridge_fs.h:174-210`), and `check_settings()` invokes it inline when the deferred deadline expires (`system/system.h:625-643`). Whichever task owns that call can suffer unbounded filesystem latency; it must not be an AP/render deadline owner.

### 7. Network scheduling is structurally separated, but command application still sits in front of AP work

- The wireless structural test asserts that callbacks only enqueue, the WebSocket loop runs in a separate low-priority delayed task, and the main poll drains requests without running `g_ws.loop()` or sending directly (`tests/test_k1_wireless_control_static.py:112-151`). That callback/task separation is sound.
- The same test pins main-loop ordering as serial check → wireless poll/control apply → audio chunk acquisition (`tests/test_k1_wireless_control_static.py:128-141`). Consequently a large control-drain burst or an expensive facade action can delay the next AP acquisition even though the socket loop itself is offloaded. The scheduler design needs a per-iteration command budget or explicit audio-first deadline rule.
- The test also pins the WebSocket task to Core 0, off the LED core, and makes a connected-client AP path call `vTaskDelay(1)` periodically (`tests/test_k1_wireless_control_static.py:153-174`). That deliberate yield should be included in AP response-time analysis rather than treated as background noise.
- BLE-MIDI CC14 pairing is defined against a 50 ms wall-clock expiry and relies on the caller to inject `now_ms` (`network/k1_ble_midi_decoder.h:13-16,25-45`). A delayed poll can change a valid MSB/LSB pair into a malformed/expired one unless timestamps are captured at receipt rather than drain time.

### 8. Existing timing evidence is useful but does not yet prove deadline tails or causality

- VPAB payloads carry frame sequence/time plus render, quantisation, full-frame, show, over-budget, and dropped-frame fields (`diag/vpab_capture.h:14-22,24-74`). The framed gate rejects sequence gaps, corrupt records, and non-zero diagnostic drops (`tests/test_vpab_frame_gate.py:68-130`), providing a good integrity envelope.
- The wireless A/B bench is candid that `[AP]` is a 1 Hz sample, event counts are sampled proxies, sub-frame jitter is invisible, and VPF `p95` is a percentile over per-second averages rather than per-frame tails (`scripts/regression-harness/wireless_ab_bench.py:25-54,496-595`). It explicitly escalates cross-core ordering/causality to MabuTrace (`scripts/regression-harness/wireless_ab_bench.py:19-23`). These data must not be used as proof of worst-case scheduling latency.
- The assigned L1 trace gate covers only `vp_bus_read` and `vp_visual_hooks_tick`, enforcing 100 us and 50 us p99 ceilings respectively (`scripts/regression-harness/k1_trace_l1_gate.py:10-18,70-94`). It does not cover complete AP iteration, render frame, filesystem, serial, or cross-core publication latency.
- The build-policy oracle records a 5 s task watchdog and 300 ms interrupt watchdog, but explicitly states that it is only a drift detector and enforces nothing into the binary (`scripts/regression-harness/golden/oracle_build_config_policy.py:1-18,46-57`). Those watchdogs are crash/hang backstops, not real-time deadline guards.
- Render trace follows the correct diagnostic boundary: silent, heap-free O(N) copy while armed, and explicitly blocking only during post-capture dump (`visual/k1_render_trace.h:4-18,28-36`). This is the pattern future scheduler instrumentation should preserve.

## Read-count reconciliation

`chunk_6.txt` contains **76** newline-delimited assigned paths. The ledger above contains **76** entries marked `READ_IN_FULL`; there are **0** read failures. Count reconciles exactly: **76 / 76**.
