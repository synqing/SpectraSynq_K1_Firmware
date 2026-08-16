# FRTOS-09 — exhaustive codebase read, chunk 1

## Completion and provenance

- Canonical first-party source manifest: `/tmp/k1-source-manifest.WdLSdO/first_party_sources.txt`
- Canonical manifest SHA-256: `06b03c3d0a3c6352e5383ffea151f579636adc66394c73b556add68f74c5e0b7`
- Assigned chunk: `/tmp/k1-source-manifest.WdLSdO/chunk_1.txt`
- Assigned chunk SHA-256: `b89ed181e769e9b572d705a97a69ad05eae6c2c2da08c9ce93e2a6413703787b`
- Assigned paths: **77**
- `READ_IN_FULL`: **77**
- Failures: **0**
- Final reconciliation: **77/77 assigned paths read in full**

Every file below was read from first line through EOF. Large files were read as contiguous,
non-overlapping ranges. Searches were used only after the full reads to relocate exact source
lines for citation. No build, test, Git, device, serial, upload, flash, dependency-install or
firmware action was performed.

## Complete file ledger

| # | Assigned path | Status |
|---:|---|---|
| 1 | `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` | `READ_IN_FULL` |
| 2 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp` | `READ_IN_FULL` |
| 3 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h` | `READ_IN_FULL` |
| 4 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.cpp` | `READ_IN_FULL` |
| 5 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm_fft512_bench.cpp` | `READ_IN_FULL` |
| 6 | `SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.cpp` | `READ_IN_FULL` |
| 7 | `SPECTRASYNQ_K1_FIRMWARE/control/k1_wireless_control.h` | `READ_IN_FULL` |
| 8 | `SPECTRASYNQ_K1_FIRMWARE/diag/k1_pin_evidence.h` | `READ_IN_FULL` |
| 9 | `SPECTRASYNQ_K1_FIRMWARE/director/beat_aware_director.h` | `READ_IN_FULL` |
| 10 | `SPECTRASYNQ_K1_FIRMWARE/director/k1_smart_director.h` | `READ_IN_FULL` |
| 11 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectMetadata.h` | `READ_IN_FULL` |
| 12 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/K1AudioContext.h` | `READ_IN_FULL` |
| 13 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionEngine.h` | `READ_IN_FULL` |
| 14 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/ZoneDemo.h` | `READ_IN_FULL` |
| 15 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_harmonic_tide.cpp` | `READ_IN_FULL` |
| 16 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_aurora.cpp` | `READ_IN_FULL` |
| 17 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge_chord.cpp` | `READ_IN_FULL` |
| 18 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_quantum_collapse.cpp` | `READ_IN_FULL` |
| 19 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river.cpp` | `READ_IN_FULL` |
| 20 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp` | `READ_IN_FULL` |
| 21 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_claim_adv_v1.h` | `READ_IN_FULL` |
| 22 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_enc8_identity_v1.h` | `READ_IN_FULL` |
| 23 | `SPECTRASYNQ_K1_FIRMWARE/persistence/buttons.h` | `READ_IN_FULL` |
| 24 | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def` | `READ_IN_FULL` |
| 25 | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def` | `READ_IN_FULL` |
| 26 | `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp` | `READ_IN_FULL` |
| 27 | `SPECTRASYNQ_K1_FIRMWARE/system/utilities.h` | `READ_IN_FULL` |
| 28 | `SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h` | `READ_IN_FULL` |
| 29 | `scripts/agent/pio-build.sh` | `READ_IN_FULL` |
| 30 | `scripts/dual_sync_probe/capture.py` | `READ_IN_FULL` |
| 31 | `scripts/dual_sync_probe/f2_run.py` | `READ_IN_FULL` |
| 32 | `scripts/dual_sync_probe/run_f2_flash.sh` | `READ_IN_FULL` |
| 33 | `scripts/hooks/install.sh` | `READ_IN_FULL` |
| 34 | `scripts/platformio/k1_src_includes.py` | `READ_IN_FULL` |
| 35 | `scripts/regression-harness/acf_gap_ablation.py` | `READ_IN_FULL` |
| 36 | `scripts/regression-harness/apstream_ingest.py` | `READ_IN_FULL` |
| 37 | `scripts/regression-harness/colour_baseline_capture.py` | `READ_IN_FULL` |
| 38 | `scripts/regression-harness/device_stm_telem_soak.py` | `READ_IN_FULL` |
| 39 | `scripts/regression-harness/fixtures/gen_fixtures.py` | `READ_IN_FULL` |
| 40 | `scripts/regression-harness/golden/oracle_agc_perband.py` | `READ_IN_FULL` |
| 41 | `scripts/regression-harness/golden/oracle_gdft.py` | `READ_IN_FULL` |
| 42 | `scripts/regression-harness/golden/oracle_smart_director.py` | `READ_IN_FULL` |
| 43 | `scripts/regression-harness/k1_av_event_quality.py` | `READ_IN_FULL` |
| 44 | `scripts/regression-harness/k1_godark_validate.py` | `READ_IN_FULL` |
| 45 | `scripts/regression-harness/k1_response_normalisation_gate.py` | `READ_IN_FULL` |
| 46 | `scripts/regression-harness/k1_ws_registry_codegen.py` | `READ_IN_FULL` |
| 47 | `scripts/regression-harness/musical_saliency_benchmark.py` | `READ_IN_FULL` |
| 48 | `scripts/regression-harness/p4_baseline_leg.py` | `READ_IN_FULL` |
| 49 | `scripts/regression-harness/render_diagnostics.py` | `READ_IN_FULL` |
| 50 | `scripts/regression-harness/run_row1_dispatch_table_test.sh` | `READ_IN_FULL` |
| 51 | `scripts/regression-harness/smart_director_replay.py` | `READ_IN_FULL` |
| 52 | `scripts/regression-harness/spaces/lgp_validate.py` | `READ_IN_FULL` |
| 53 | `scripts/regression-harness/stubs/Arduino.h` | `READ_IN_FULL` |
| 54 | `scripts/regression-harness/tab5_transcript_ingest.py` | `READ_IN_FULL` |
| 55 | `scripts/regression-harness/transfer_quiet_leg_dual.py` | `READ_IN_FULL` |
| 56 | `scripts/regression-harness/vpab_gate.py` | `READ_IN_FULL` |
| 57 | `scripts/regression-harness/vpml_live_runner.py` | `READ_IN_FULL` |
| 58 | `scripts/release/make_release.py` | `READ_IN_FULL` |
| 59 | `tests/conftest.py` | `READ_IN_FULL` |
| 60 | `tests/test_audio_response_gain_static.py` | `READ_IN_FULL` |
| 61 | `tests/test_bootloop_guard_static.py` | `READ_IN_FULL` |
| 62 | `tests/test_colour_fix_flags_static.py` | `READ_IN_FULL` |
| 63 | `tests/test_dual_sync_oracle.py` | `READ_IN_FULL` |
| 64 | `tests/test_effect_registry_sanitize_static.py` | `READ_IN_FULL` |
| 65 | `tests/test_gdft_int64_magnitude.py` | `READ_IN_FULL` |
| 66 | `tests/test_im73d_audio_eval_harness.py` | `READ_IN_FULL` |
| 67 | `tests/test_k1_optics_static.py` | `READ_IN_FULL` |
| 68 | `tests/test_k1_serial_safety.py` | `READ_IN_FULL` |
| 69 | `tests/test_led_index_bounds_static.py` | `READ_IN_FULL` |
| 70 | `tests/test_new_effects_batch_static.py` | `READ_IN_FULL` |
| 71 | `tests/test_palette_coverage_static.py` | `READ_IN_FULL` |
| 72 | `tests/test_semantic_state_replay.py` | `READ_IN_FULL` |
| 73 | `tests/test_smart_director_replay.py` | `READ_IN_FULL` |
| 74 | `tests/test_tab5_dashboard_harness.py` | `READ_IN_FULL` |
| 75 | `tests/test_tunables_registry.py` | `READ_IN_FULL` |
| 76 | `tests/test_vpab_semantic_presentation.py` | `READ_IN_FULL` |
| 77 | `tests/test_vpml_runtime_summary.py` | `READ_IN_FULL` |

## Scheduling, publication and timing findings

### 1. The production topology is two same-priority application loops, not a scheduler-controlled 120 Hz render task

The sketch pins `led_task` to Core 1 with an 8192-byte stack and priority
`tskIDLE_PRIORITY + 1`; Arduino's loop task remains the audio/control loop on the other core.
There is a compile-time same-core rejection and a boot-time core/timing report
(`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:109-132`,
`:721-752`). Both long-lived loops yield with `vTaskDelay(1)` (`:1080-1082`,
`:1464-1468`). The render loop has no `vTaskDelayUntil`, periodic timer, absolute deadline or
explicit 8.333 ms pacing at this layer: it performs all work, submits LEDs, updates an observed
FPS EMA, then delays one tick (`:1447-1468`). Therefore nominal 120 FPS and a 2 ms effect ceiling
must not be treated as scheduler-enforced cadence.

The watchdog is a 5 s freeze detector, not a real-time deadline guard: setup reconfigures and
subscribes the loop task (`:754-764`), while the render task feeds once per frame
(`:1107-1115`). It can detect gross stalls but cannot prove sub-8 ms latency, 120 Hz cadence or
2 ms render execution.

### 2. Control, radio and serial work precede every audio acquisition on the loop core

Each `loop()` iteration handles knobs, buttons, settings, serial, wireless, BLE and sync polling
before calling `acquire_sample_chunk()` (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:817-852`).
Any unbounded or occasionally long operation in those pollers lengthens the interval before the
next I2S acquisition. This chunk does not contain the acquisition implementation, so it cannot
establish whether DMA buffering absorbs that delay or when overflow begins. The safe finding is
the ordering and shared task, not a claimed measured overrun.

One concrete long operation is preset-slot persistence: it opens and synchronously writes a
LittleFS file (`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.cpp:359-375`), and the public save
path explicitly says the immediate write runs on the serial/loop core (`:549-558`). That puts a
flash/filesystem latency excursion on the same task that next reaches audio acquisition. A hardened
design needs a bounded handoff and a measured DMA-headroom contract, or an explicit audio pause
protocol, rather than assuming the rare call is harmless.

### 3. The effect queue's Core-0-to-Core-1 handoff is not a valid publication primitive

`g_pending[2]` is an ordinary non-atomic struct array. The producer writes the preset and `armed`,
then raises ordinary `volatile` request fields; the code documents this as plain-store ordering
(`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.cpp:49-70`, `:472-508`). Core 1 reads the flag,
then the ordinary `armed` and preset fields (`:585-605`). `volatile` does not make the compound
payload atomic and does not provide a C++ inter-core release/acquire relationship. The reader can
therefore observe a torn/stale preset or race a new arm while clearing `armed`. "Raised last" is
not sufficient publication proof.

This should be replaced by a primitive with explicit ownership and ordering, such as a FreeRTOS
queue carrying a complete desired-state command, or a versioned/seqlocked double buffer with a
single writer and a release/acquire generation commit. The command class is complete desired state,
so latest-wins coalescing is legitimate only before commit; a commit request itself must not be
silently lost.

### 4. Audio state is internally protected but not coherently aggregated

Snapshot production prepares `next` outside the critical section and performs the final struct
assignment inside a `portMUX` critical section; readers copy the complete struct under the same
mux (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp:105-129`). That prevents a torn
*individual* snapshot. It also means interrupt-disabled time includes copying the full live
snapshot, which is a measurement target if optional 80-bin/chord/STM fields enlarge it.

`audio_semantic_read()` then performs three independent accessor calls for tempo, onset and audio
snapshot (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.cpp:31-46`). No common generation or
retry protocol proves that the three values came from one AP publication. The composite can mix
adjacent producer frames. A scheduling hardening design should publish one immutable aggregate or
attach and verify a shared generation around all constituent reads.

### 5. Render-frame consumers can disagree with each other and with the SmartDirector within one frame

Framework dispatch reads snapshot and onset separately into static local copies on every channel
render call, then binds pointer-based `K1AudioContext` to those copies
(`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:431-448`). The pointer lifetime is safe for
the synchronous call because the copies have static storage, consistent with the adapter's explicit
caller-owned pointer contract (`SPECTRASYNQ_K1_FIRMWARE/effects/framework/K1AudioContext.h:14-17`,
`:98-110`). However, primary and secondary framework calls may read at different instants. The
SmartDirector likewise reads audio and onset as separate publications (`.ino:1264-1273`). One
render frame can therefore contain different AP generations across director, primary and secondary.

The robust shape is one VP-local immutable frame input captured once at frame top, with a coherent
generation, and passed by const reference to every consumer. Edge events need sequence counters or
latched consumption semantics; copying a momentary Boolean does not by itself guarantee exactly-once
delivery.

### 6. Beat-quantised queue commits depend on a sampled edge and have only a wall-clock escape hatch

Core 1 samples `tempo.beat_tick && tempo.locked` once per render-frame tick, otherwise waits until a
2 s timeout (`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.cpp:585-605`). Whether this can miss,
repeat or stale-reconsume an event depends on the tempo publisher's lifetime semantics, which are
outside this chunk. A Boolean edge transported between independently scheduled tasks is unsafe
unless it is latched until acknowledged or accompanied by a monotonically increasing event ID.

The timeout prevents an indefinitely stuck user command, but it does not preserve beat intent.
Recommended invariant: a consumer tracks `last_beat_event_id`; any larger ID is a new beat, and the
publisher never relies on overlap between event pulse width and VP polling cadence.

### 7. Crossfades multiply render work inside an unpaced frame

The queue's crossfade overlay temporarily applies incoming fields so the incoming effect is rendered
in addition to the outgoing one (`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.cpp:615-648`). The
main loop invokes that overlay for both primary and secondary (`SPECTRASYNQ_K1_FIRMWARE/
SPECTRASYNQ_K1_FIRMWARE.ino:1312-1315`, `:1368-1371`) before `show_leds()`. This can nearly double
effect execution for one or both channels and is not coupled here to an admission budget, degrade
path or skipped-transition policy. It is a prime workload for p95/p99.9 measurement under the
heaviest enabled effects, not just steady-state FPS.

`TransitionEngine` correctly declares one-time allocation and no heap during `update()`
(`SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionEngine.h:82-118`), but that addresses heap
safety rather than worst-case compute cost.

### 8. Several temporal paths remain frame-count dependent

The shared spectrogram smoother applies fixed per-call attack/release fractions and has no `dt`
input (`SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h:19-35`). Mic auto-sense likewise uses a
fixed EMA alpha of 0.08 per AP update (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.h:243-251`,
`:340-348`). Quantum Collapse advances phases by fixed amounts per render call
(`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_quantum_collapse.cpp:17-25`). Their time constants and
motion rates therefore change when scheduling jitter or dropped frames changes invocation rate.

This is distinct from wall-clock dwell/cooldown logic in mic auto-sense. Hardening the scheduler
without converting these smoothers/motion paths to `dt`-correct coefficients can make behaviour
change simply because cadence becomes more stable or is retargeted.

### 9. Existing host tests cannot establish cross-core memory correctness

The host Arduino stub forces `xPortGetCoreID()` to 0 and turns `portMUX` critical sections into
no-ops (`scripts/regression-harness/stubs/Arduino.h:100-130`). This is appropriate for deterministic
algorithm replay but cannot detect a missing release/acquire edge, a torn payload or a two-core
interleaving. The semantic replay test checks field forwarding and nominal rate derivation, not a
concurrent publication schedule (`tests/test_semantic_state_replay.py:9-25`).

Gate 0 therefore needs a purpose-built host concurrency model/property test for the versioned
publication algorithm plus device evidence under real two-core scheduling. Existing golden/replay
oracles should remain behaviour gates, not be relabelled as concurrency proof.

### 10. The available render-budget gate is opt-in, so a default PASS can contain a timing breach

`vpab_gate.py` declares 2,000 us render and 8,333.33 us frame ceilings
(`scripts/regression-harness/vpab_gate.py:85-96`). It always calculates render-budget failures, but
only adds them to the overall failure set when `strict_render_budget` is true (`:406-440`); the CLI
flag is optional (`:525-534`). Thus default invocation reports render breaches as WARN rather than
failing the gate. Any production scheduling gate must invoke strict mode explicitly, prove that
required timing fields are present, and fail closed when they are absent.

### 11. Nominal fixture timestamps and inferred serial timestamps are not scheduler evidence

Synthetic render fixtures derive `7.5 ms per AP frame` directly from `12800/96` and explicitly call
the stimuli synthetic (`scripts/regression-harness/fixtures/gen_fixtures.py:2-35`, `:42-45`). The AP
ingester invents timestamps from a nominal cadence when a log lacks explicit timestamps
(`scripts/regression-harness/apstream_ingest.py:400-437`). Those are useful modelling inputs, but
neither measures active CPU time, DMA wait, AP jitter or end-to-end latency. Scheduling decisions
must use explicit device timestamps and separate chunk period, wait time, compute time, queue age and
LED-submit time.

### 12. One assigned device harness defaults to a prohibited/non-representative stimulus

`device_stm_telem_soak.py` defaults to a generated 1 kHz calibration tone
(`scripts/regression-harness/device_stm_telem_soak.py:38-55`). That can be useful for narrow transfer
characterisation, but it is not Captain-confirmed audible real music and cannot validate production
audio-reactive scheduling or perceptual behaviour. Any reuse in Gate 0 must require an authorised
real-music path and preserve a separate silence leg.

## Boundary and priority summary

The most urgent source-backed implementation hazards from this chunk are:

1. replace the effect queue's plain-struct-plus-volatile-flag handoff;
2. capture one coherent VP-local audio/event input per frame with explicit event IDs;
3. remove synchronous filesystem work from the pre-acquisition loop path or provide a proven pause/
   headroom protocol;
4. introduce deadline-aware cadence and overrun accounting rather than relying on `vTaskDelay(1)`;
5. make timing gates fail closed and distinguish nominal periods from device-measured execution;
6. convert frame-count-dependent smoothing/motion where scheduler hardening would change cadence.

This chunk alone does **not** establish the implementation or blocking behaviour of I2S acquisition,
the tempo/onset publishers, FastLED/RMT submission, or every network poller. Those claims must be
reconciled with their owning source chunks before final architecture or severity decisions.
