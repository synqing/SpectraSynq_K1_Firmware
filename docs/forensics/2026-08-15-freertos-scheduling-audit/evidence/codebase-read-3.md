# FRTOS-11 — exhaustive source reader 3

## Scope and integrity

- Contract: `docs/forensics/2026-08-15-freertos-scheduling-audit/DELEGATION_CONTRACTS.md`, FRTOS-11.
- Repository resolved by `pwd -P`: `/Users/spectrasynq/SpectraSynq_K1_Firmware`.
- Whole first-party manifest: `/tmp/k1-source-manifest.WdLSdO/first_party_sources.txt`.
- Whole-manifest SHA-256: `06b03c3d0a3c6352e5383ffea151f579636adc66394c73b556add68f74c5e0b7`.
- Assigned chunk: `/tmp/k1-source-manifest.WdLSdO/chunk_3.txt`.
- Chunk SHA-256: `70f0423060fb2c1226267b88a91104857e9b7db6af6a88eda82cdf7769a60786`.
- Method: every assigned file was read from first through last line. Search was used only after the full reads to recover exact citation lines.
- Constraint observed: no build, test, Git, device, upload, flash, serial, or network action was performed.

## Exact completion count

| Measure | Count |
|---|---:|
| Assigned paths | 77 |
| `READ_IN_FULL` | 77 |
| Failures | 0 |

The final count matches the 77 non-empty lines in the assigned chunk.

## Per-file full-read ledger

| # | Assigned path | Lines | Status |
|---:|---|---:|---|
| 1 | `SPECTRASYNQ_K1_FIRMWARE/audio/audio_transfer.h` | 740 | `READ_IN_FULL` |
| 2 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_chord_detect.cpp` | 92 | `READ_IN_FULL` |
| 3 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_health.h` | 145 | `READ_IN_FULL` |
| 4 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_spectral_honesty.h` | 215 | `READ_IN_FULL` |
| 5 | `SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp` | 1682 | `READ_IN_FULL` |
| 6 | `SPECTRASYNQ_K1_FIRMWARE/control/k1_noise_cal_arm.cpp` | 47 | `READ_IN_FULL` |
| 7 | `SPECTRASYNQ_K1_FIRMWARE/diag/diagnostic_capture.h` | 69 | `READ_IN_FULL` |
| 8 | `SPECTRASYNQ_K1_FIRMWARE/diag/motion_probe.h` | 554 | `READ_IN_FULL` |
| 9 | `SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.h` | 133 | `READ_IN_FULL` |
| 10 | `SPECTRASYNQ_K1_FIRMWARE/director/k1_visual_hooks.h` | 31 | `READ_IN_FULL` |
| 11 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectRegistry.cpp` | 441 | `READ_IN_FULL` |
| 12 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/LegacyEffectAdapter.cpp` | 68 | `READ_IN_FULL` |
| 13 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionOverlay.h` | 85 | `READ_IN_FULL` |
| 14 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_beat_pulse_resonant.h` | 94 | `READ_IN_FULL` |
| 15 | `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_transient_lattice.cpp` | 423 | `READ_IN_FULL` |
| 16 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_chroma_constellation.cpp` | 168 | `READ_IN_FULL` |
| 17 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_ember_v2.cpp` | 76 | `READ_IN_FULL` |
| 18 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_snapwave.cpp` | 133 | `READ_IN_FULL` |
| 19 | `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_vu.cpp` | 63 | `READ_IN_FULL` |
| 20 | `SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp` | 1309 | `READ_IN_FULL` |
| 21 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.h` | 103 | `READ_IN_FULL` |
| 22 | `SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.h` | 50 | `READ_IN_FULL` |
| 23 | `SPECTRASYNQ_K1_FIRMWARE/persistence/knobs.h` | 85 | `READ_IN_FULL` |
| 24 | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` | 697 | `READ_IN_FULL` |
| 25 | `SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_dispatch.h` | 118 | `READ_IN_FULL` |
| 26 | `SPECTRASYNQ_K1_FIRMWARE/system/k1_tunables.h` | 84 | `READ_IN_FULL` |
| 27 | `SPECTRASYNQ_K1_FIRMWARE/visual/Palettes.h` | 180 | `READ_IN_FULL` |
| 28 | `SPECTRASYNQ_K1_FIRMWARE/visual/render_params.h` | 66 | `READ_IN_FULL` |
| 29 | `scripts/agent/session-bootstrap.sh` | 141 | `READ_IN_FULL` |
| 30 | `scripts/dual_sync_probe/f2_capture.py` | 2030 | `READ_IN_FULL` |
| 31 | `scripts/dual_sync_probe/gate_eval.py` | 542 | `READ_IN_FULL` |
| 32 | `scripts/dual_sync_probe/run_f2_reboot.sh` | 9 | `READ_IN_FULL` |
| 33 | `scripts/install-claude-mem-skills.sh` | 193 | `READ_IN_FULL` |
| 34 | `scripts/refactor/build_serial_typed_dispatch.py` | 276 | `READ_IN_FULL` |
| 35 | `scripts/regression-harness/ap_capture_leg.py` | 111 | `READ_IN_FULL` |
| 36 | `scripts/regression-harness/beat_aware_director_device_proof.py` | 368 | `READ_IN_FULL` |
| 37 | `scripts/regression-harness/derive_bands.py` | 86 | `READ_IN_FULL` |
| 38 | `scripts/regression-harness/edgemixer_host_shim/constants.h` | 26 | `READ_IN_FULL` |
| 39 | `scripts/regression-harness/gate0_selftest.py` | 207 | `READ_IN_FULL` |
| 40 | `scripts/regression-harness/golden/oracle_ble_midi_map.py` | 507 | `READ_IN_FULL` |
| 41 | `scripts/regression-harness/golden/oracle_k1_bootloop.py` | 272 | `READ_IN_FULL` |
| 42 | `scripts/regression-harness/golden/serial_replay_host_stubs.h` | 108 | `READ_IN_FULL` |
| 43 | `scripts/regression-harness/k1_av_manifest.py` | 268 | `READ_IN_FULL` |
| 44 | `scripts/regression-harness/k1_optics.py` | 221 | `READ_IN_FULL` |
| 45 | `scripts/regression-harness/k1_smart_auto_validation.py` | 212 | `READ_IN_FULL` |
| 46 | `scripts/regression-harness/loop.py` | 1116 | `READ_IN_FULL` |
| 47 | `scripts/regression-harness/novelty_decimation_model.py` | 76 | `READ_IN_FULL` |
| 48 | `scripts/regression-harness/palette_coverage_gate.py` | 278 | `READ_IN_FULL` |
| 49 | `scripts/regression-harness/render_replay.py` | 1054 | `READ_IN_FULL` |
| 50 | `scripts/regression-harness/semantic_state_replay.py` | 268 | `READ_IN_FULL` |
| 51 | `scripts/regression-harness/smart_visuals_gate.py` | 268 | `READ_IN_FULL` |
| 52 | `scripts/regression-harness/stereo_probe_decode.py` | 111 | `READ_IN_FULL` |
| 53 | `scripts/regression-harness/stubs/FirmwareMSC.h` | 10 | `READ_IN_FULL` |
| 54 | `scripts/regression-harness/tempo_confv2_calibrate.py` | 326 | `READ_IN_FULL` |
| 55 | `scripts/regression-harness/vp_bleed_check.py` | 115 | `READ_IN_FULL` |
| 56 | `scripts/regression-harness/vpab_runtime_matrix.py` | 119 | `READ_IN_FULL` |
| 57 | `scripts/regression-harness/vpml_run_console_server.py` | 654 | `READ_IN_FULL` |
| 58 | `scripts/setup-project-skills.sh` | 187 | `READ_IN_FULL` |
| 59 | `tests/tab5_harness_spec/mock_ui_state.py` | 52 | `READ_IN_FULL` |
| 60 | `tests/test_beat_aware_director_boundary_proof.py` | 82 | `READ_IN_FULL` |
| 61 | `tests/test_build_provenance_static.py` | 147 | `READ_IN_FULL` |
| 62 | `tests/test_custom_led_static.py` | 237 | `READ_IN_FULL` |
| 63 | `tests/test_edgemixer_oklab_native.py` | 205 | `READ_IN_FULL` |
| 64 | `tests/test_f2_status.py` | 463 | `READ_IN_FULL` |
| 65 | `tests/test_golden_master.py` | 84 | `READ_IN_FULL` |
| 66 | `tests/test_impact_lane_static.py` | 82 | `READ_IN_FULL` |
| 67 | `tests/test_k1_palette_registry_static.py` | 170 | `READ_IN_FULL` |
| 68 | `tests/test_k1_trace_l1_gate.py` | 79 | `READ_IN_FULL` |
| 69 | `tests/test_mic_auto_sense_controller.py` | 569 | `READ_IN_FULL` |
| 70 | `tests/test_novelty_decimation_smoothing.py` | 100 | `READ_IN_FULL` |
| 71 | `tests/test_percussion_event_status_static.py` | 90 | `READ_IN_FULL` |
| 72 | `tests/test_serial_menu_odr_static.py` | 85 | `READ_IN_FULL` |
| 73 | `tests/test_smart_visual_engine_static.py` | 777 | `READ_IN_FULL` |
| 74 | `tests/test_tab5_harness_strict_mode.py` | 103 | `READ_IN_FULL` |
| 75 | `tests/test_vivid_precomp_static.py` | 179 | `READ_IN_FULL` |
| 76 | `tests/test_vpml_host_surface.py` | 151 | `READ_IN_FULL` |
| 77 | `tests/test_wireless_ab_bench_static.py` | 330 | `READ_IN_FULL` |

## Architectural findings — production-relevant source

### 1. Tempo publication is individually coherent, but the heavy ACF refresh is bursty

`K1TempoEvent` has a dedicated `portMUX_TYPE`; both whole-struct publication and reads are enclosed by the same critical section (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp:458-475`, `:1486-1491`). That prevents torn reads of this object.

The default ACF refresh linearises and mean-subtracts the 512-entry history, then computes every selected lag row in one call. The lag count is capped at 200, and each row performs a history-length-dependent inner product (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp:620-695`). This is deterministic but burst-shaped Core-0 work. A spread implementation exists and defaults to 16 lag rows per emit, but it is compiled only under `K1_TEMPO_ACF_SPREAD_PROBE` (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp:65-69`, `:697-728`). Therefore this chunk supports measuring the default refresh as a concentrated execution-time contributor; it does **not** support treating the spread probe as production behaviour.

### 2. Novelty cadence is frame-counted; phase advancement is wall-clock-corrected

Novelty is peak-held and emitted exactly once per `K1_NOVELTY_DECIMATION` audio calls, rather than from a wall-clock gate (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp:1352-1384`). On an emit, phase `delta_sec` uses actual elapsed wall time with a bounded fallback (`:1386-1390`). This separates throughput cadence from phase advancement. Any scheduler redesign must preserve both the exact input-frame decimation contract and elapsed-time phase semantics.

### 3. The beat tick is a one-shot only because non-emit frames republish a cleared event

Under `K1_TEMPO_FLYWHEEL_V2`, the two non-emit audio frames inspect the last event and republish it with `beat_tick=false` (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp:1368-1381`). The source comment records the former three-read stale-tick failure. Event lifecycle therefore depends on those cheap non-emit calls still running; coalescing, skipping, or changing publisher cadence without an explicit event-ID/acknowledgement contract can resurrect or lose ticks.

### 4. Separate coherent objects can still form an incoherent aggregate

Snapwave independently reads an audio snapshot and a tempo event, with no shared generation check between them (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_snapwave.cpp:48-61`). Each object may be internally coherent while the pair represents different producer instants. The serial percussion status contract similarly requires separate `k1_audio_snapshot_read()` and `k1_onset_beat_read()` calls (`tests/test_percussion_event_status_static.py:40-44`). This is a publication-coherence gap for any consumer that treats the pair as one logical audio frame.

The host semantic-state replay does not close this gap: it substitutes a host snapshot stub and verifies field forwarding from separately read producer objects (`scripts/regression-harness/semantic_state_replay.py:20-24`, `:57-69`, `:137-178`). It proves mapping, not concurrent cross-object epoch coherence.

### 5. Several effects remain update-rate-dependent

- Chroma Constellation calculates and clamps `dt`, but its per-pitch-class EMA uses the fixed per-frame constant `CC_EMA=0.15` and does not use that `dt` (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_chroma_constellation.cpp:65`, `:86-94`, `:117-120`).
- Ember v2 advances the flow by a per-call drift value with no elapsed-time factor (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_ember_v2.cpp:38-50`).
- VU smoothing and maximum decay are fixed per invocation, including `max_level *= 0.9999` (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_vu.cpp:3-17`).
- Snapwave is a useful counterexample: it computes bounded elapsed `dt` and passes it into its envelope follower (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_snapwave.cpp:48-61`).

Consequently, render rescheduling or deliberate frame dropping can change Chroma Constellation, Ember v2 and VU temporal behaviour even if their source inputs are unchanged.

### 6. The immutable RenderParams boundary removes one class of cross-pass mutation

`RenderParams` is documented as an immutable per-channel snapshot replacing secondary-pass mutation of global `CONFIG`; its stack is fixed-depth and heap-free (`SPECTRASYNQ_K1_FIRMWARE/visual/render_params.h:5-17`, `:50-62`). This is a positive scheduling/concurrency boundary: primary and secondary render passes can consume isolated parameter snapshots instead of temporarily rewriting shared configuration.

### 7. Untyped tunable writes and noise-calibration arm state need caller-context proof

`k1_tunables.h` stores pointers to live variables and applies parsed values by direct pointer assignment (`SPECTRASYNQ_K1_FIRMWARE/system/k1_tunables.h:16-35`, `:56-84`). `k1_noise_cal_arm.cpp` also uses plain module globals for its armed/queued state (`SPECTRASYNQ_K1_FIRMWARE/control/k1_noise_cal_arm.cpp:8-47`). Neither file establishes atomicity or an owning task. These are **candidate** shared-state hazards, not confirmed races from this chunk alone; use-site/task-affinity evidence is required before classification.

## Architectural findings — flagged probes and legacy paths

### 8. BLE Remoted has bounded ingress but an unbounded per-poll drain

The gated BLE Remoted build uses a static queue of 16 records (`SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:63`, `:113-115`, `:952-963`). The notification path uses zero-wait `xQueueSend` and records drops rather than blocking (`:270-287`). Its dedicated Core-1 task runs at priority 1 and sleeps 150 ms in the steady loop, with longer retry delays (`:907-947`, `:960-963`). However, `k1_ble_remoted_poll()` drains until the queue is empty and performs control application, publication and serial output for each record (`:980-1076`). Thus ingress is bounded in memory and non-blocking at callback time, but one main-loop poll has no explicit record/time budget and may acquire burst-dependent latency.

The task also performs synchronous GATT work with `delay(4)`/`delay(8)` (`SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:523-543`). This behaviour is explicitly labelled a gated A/B build (`:973-975`); it must not be generalised to the production scheduler without confirming active build flags.

### 9. The transfer and motion-probe paths deliberately violate production timing expectations

`audio_transfer.h` contains a blocking `i2s_read(..., portMAX_DELAY)`, a 10 ms delay, busy animation loops with repeated LED shows, and an infinite acquire/process/render/yield loop (`SPECTRASYNQ_K1_FIRMWARE/audio/audio_transfer.h:204-206`, `:407-414`, `:569-640`, `:727-739`). These are mode-specific legacy/transfer semantics, not evidence of the production audio actor.

The motion probe reads `millis()`, emits serial diagnostics during the effect path, and tells its caller to yield once per loop (`SPECTRASYNQ_K1_FIRMWARE/diag/motion_probe.h:400-402`, `:407-514`). It can perturb the timing it observes. Treat it as a non-shipping perceptual probe, never as an unbiased runtime-timing oracle.

### 10. The framework lattice effect has a sound render-time lifecycle but edge-trigger assumptions

The transient lattice allocates/frees its PSRAM trail in init/destruction rather than render (`SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_transient_lattice.cpp:207-225`, `:390-399`). Render uses `dt`-based phase, envelopes and trail decay (`:264-320`). Snare and hi-hat events are de-duplicated with armed booleans that only re-arm after the sampled event becomes false (`:287-306`); a producer that republishes true continuously, or a consumer that misses the false state, changes lifecycle semantics. The effect is framework/flag-bound, so this is a reusable event-contract lesson rather than a confirmed production defect.

## Existing evidence surfaces and blind spots

### 11. Existing tests check locking syntax and event contracts, not task interleavings

`test_smart_visual_engine_static.py` requires critical-section snapshot patterns in the Smart Director, hooks, EdgeMixer and mode-state configuration (`tests/test_smart_visual_engine_static.py:288-309`) and checks that audio snapshot publication occurs after novelty work (`:151-168`). It also enforces event-age and last-event-ID fields in visual hooks (`:687-735`). `test_percussion_event_status_static.py` locks the monotonically changing event-ID contract (`tests/test_percussion_event_status_static.py:77-86`). These are valuable source invariants, but they do not execute adversarial Core-0/Core-1 interleavings or prove a shared aggregate epoch.

### 12. Peak-hold decimation is tested; missed/deferred scheduler calls are not

The novelty model and test explicitly prove peak-hold aggregation and preservation of a spike between emit frames (`tests/test_novelty_decimation_smoothing.py:58-96`). Tempo calibration assumes a steady 44.44 Hz novelty update stream and applies EMA per update (`scripts/regression-harness/tempo_confv2_calibrate.py:41-44`, `:127-148`). The mic auto-sense oracle likewise uses a fixed EMA alpha per controller update while dwell is wall-clock-based (`tests/test_mic_auto_sense_controller.py:158-165`). These gates cover expected update sequences; they do not establish invariance when the scheduler skips or defers calls.

### 13. Host render replay is functional proof, not timing proof

The replay harness compiles a host fixture with synthetic state rather than running FreeRTOS. Its emitted primary and secondary records set `render_us` to zero (`scripts/regression-harness/render_replay.py:720-756`). It can prove deterministic mapping and event behaviour but cannot establish render WCET, deadline misses, task starvation or cross-core publication ordering.

The semantic replay advances its model clock by rounded 8 ms steps via `(uint32_t)(7.5 + 0.5)` (`scripts/regression-harness/semantic_state_replay.py:126-136`). It therefore cannot prove a precise 7.5 ms audio cadence or scheduler jitter bounds.

### 14. Device/dual-sync gates are useful but retain explicit measurement boundaries

The dual-sync evaluator gates clock-error p95, lateness p99.9 and maximum leader-to-follower consume latency (`scripts/dual_sync_probe/gate_eval.py:239-332`), then checks FPS, heap, AP p95 and loss (`:343-400`). It explicitly marks physical WS2812 glitches as unmeasured (`:389-393`). `test_k1_trace_l1_gate.py` checks the existence of p99 hook-tail and primary/secondary render counters (`tests/test_k1_trace_l1_gate.py:19-75`), but not scheduling causality or starvation. These surfaces should be retained as downstream evidence, with the stated gaps filled by task-runtime and publication-epoch oracles rather than inferred away.

### 15. Wireless A/B cadence metrics are host-observed proxies

The wireless bench test constructs host-timestamped 1 Hz `[AP]` lines and validates that an injected 400 ms stall appears in p95 jitter (`tests/test_wireless_ab_bench_static.py:118-181`). It checks VPF sequence gaps and frame-time surfaces (`:183-196`) and labels the comparison “not causal proof” (`:287-290`). This is correctly bounded regression evidence; it is not a direct measurement of the audio task's 133 Hz execution cadence.

## Reader verdict

This chunk exposes four load-bearing scheduling concerns for synthesis:

1. preserve the distinction between exact audio-frame decimation and wall-clock phase advancement;
2. budget or spread the concentrated ACF work using production-enabled code and measured WCET;
3. give multi-producer consumers a shared epoch or transactional aggregate instead of relying on separately coherent reads; and
4. make effect dynamics and event delivery invariant to permitted render skips, task jitter and publication coalescing.

It also contains useful bounded machinery—critical-section whole-struct reads, immutable render parameters, static BLE ingress, peak-hold decimation and explicit evidence boundaries—but none of the host/static surfaces in this chunk alone prove FreeRTOS schedulability or cross-core aggregate coherence.
