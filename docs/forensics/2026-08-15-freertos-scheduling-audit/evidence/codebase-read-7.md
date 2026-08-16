# FRTOS-15 — Codebase read 7 evidence

## Scope and source identity

- Repository root verified before reading: `/Users/spectrasynq/SpectraSynq_K1_Firmware`.
- Governing contract read in full: `docs/forensics/2026-08-15-freertos-scheduling-audit/DELEGATION_CONTRACTS.md`.
- Agent execution standard read in full: `docs/agent/AGENT_EXECUTION_STANDARD.md`.
- Full first-party source manifest: `/tmp/k1-source-manifest.WdLSdO/first_party_sources.txt`.
- Full manifest SHA-256: `06b03c3d0a3c6352e5383ffea151f579636adc66394c73b556add68f74c5e0b7`.
- Full manifest entry count: `535`.
- Assigned chunk: `/tmp/k1-source-manifest.WdLSdO/chunk_7.txt`.
- Assigned chunk SHA-256: `4cddbe076aeba2199ad8f91be33eea7b69d82df35e1e89f0363d3d18a833c736`.
- Assigned entry count: `76`.
- Read method: every assigned file was read from first line through EOF, with large files paged into bounded, contiguous ranges. No grep-only classification was used.
- Result: `76/76 READ_IN_FULL`; `0` failures; ledger count exactly matches the assigned chunk count.
- Execution boundary: no build, test, firmware edit, Git mutation, upload, flash, serial connection, or device action was performed.

## Per-path read ledger

1. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_profile.h` — `READ_IN_FULL`
2. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_auto_sense.cpp` — `READ_IN_FULL`
3. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.h` — `READ_IN_FULL`
4. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.h` — `READ_IN_FULL`
5. `SPECTRASYNQ_K1_FIRMWARE/control/k1_control_facade.h` — `READ_IN_FULL`
6. `SPECTRASYNQ_K1_FIRMWARE/control/k1_wireless_control.cpp` — `READ_IN_FULL`
7. `SPECTRASYNQ_K1_FIRMWARE/diag/k1_pin_evidence.cpp` — `READ_IN_FULL`
8. `SPECTRASYNQ_K1_FIRMWARE/director/beat_aware_director.cpp` — `READ_IN_FULL`
9. `SPECTRASYNQ_K1_FIRMWARE/director/k1_smart_director.cpp` — `READ_IN_FULL`
10. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectId.h` — `READ_IN_FULL`
11. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/IEffect.h` — `READ_IN_FULL`
12. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionEngine.cpp` — `READ_IN_FULL`
13. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/ZoneDefinition.h` — `READ_IN_FULL`
14. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_flux_rift.h` — `READ_IN_FULL`
15. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/zone_composer_compile_probe.cpp` — `READ_IN_FULL`
16. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp` — `READ_IN_FULL`
17. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_pulse_prism.cpp` — `READ_IN_FULL`
18. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet_anticipate.cpp` — `READ_IN_FULL`
19. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid.cpp` — `READ_IN_FULL`
20. `SPECTRASYNQ_K1_FIRMWARE/network/k1_ble_midi_map.h` — `READ_IN_FULL`
21. `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_v1.h` — `READ_IN_FULL`
22. `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs_config_codec.h` — `READ_IN_FULL`
23. `SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_handlers.h` — `READ_IN_FULL`
24. `SPECTRASYNQ_K1_FIRMWARE/serial/serial_tx.h` — `READ_IN_FULL`
25. `SPECTRASYNQ_K1_FIRMWARE/system/globals.h` — `READ_IN_FULL`
26. `SPECTRASYNQ_K1_FIRMWARE/system/user_config.h` — `READ_IN_FULL`
27. `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` — `READ_IN_FULL`
28. `scripts/agent/k1-session-preflight.sh` — `READ_IN_FULL`
29. `scripts/dual_sync_probe/__init__.py` — `READ_IN_FULL`
30. `scripts/dual_sync_probe/f2_reboot.py` — `READ_IN_FULL`
31. `scripts/dual_sync_probe/run_f2_finalise.sh` — `READ_IN_FULL`
32. `scripts/hooks/framework-safety-gate.sh` — `READ_IN_FULL`
33. `scripts/platformio/k1_effect_framework_includes.py` — `READ_IN_FULL`
34. `scripts/regression-harness/acf_ceiling_sweep.py` — `READ_IN_FULL`
35. `scripts/regression-harness/ap_structured_evidence_test.cpp` — `READ_IN_FULL`
36. `scripts/regression-harness/chord_saliency_replay.py` — `READ_IN_FULL`
37. `scripts/regression-harness/device_novelty_replay.py` — `READ_IN_FULL`
38. `scripts/regression-harness/fastled_stub_test.cpp` — `READ_IN_FULL`
39. `scripts/regression-harness/golden/harness_selftest.py` — `READ_IN_FULL`
40. `scripts/regression-harness/golden/oracle_chord.py` — `READ_IN_FULL`
41. `scripts/regression-harness/golden/oracle_serial_struct.py` — `READ_IN_FULL`
42. `scripts/regression-harness/k1_audio_visual_regression.py` — `READ_IN_FULL`
43. `scripts/regression-harness/k1_godark_observe.py` — `READ_IN_FULL`
44. `scripts/regression-harness/k1_real_music_corpus_capture.py` — `READ_IN_FULL`
45. `scripts/regression-harness/k1_vpab_visual_sync.py` — `READ_IN_FULL`
46. `scripts/regression-harness/mirex_rescore.py` — `READ_IN_FULL`
47. `scripts/regression-harness/onset_v2_replay.py` — `READ_IN_FULL`
48. `scripts/regression-harness/registry_byte_gate.sh` — `READ_IN_FULL`
49. `scripts/regression-harness/run_fft512_bench_eval.py` — `READ_IN_FULL`
50. `scripts/regression-harness/smart_auto_product_ab_capture.py` — `READ_IN_FULL`
51. `scripts/regression-harness/spaces/lgp_real_render.py` — `READ_IN_FULL`
52. `scripts/regression-harness/stm_vp_run_packet.py` — `READ_IN_FULL`
53. `scripts/regression-harness/stubs/freertos/task.h` — `READ_IN_FULL`
54. `scripts/regression-harness/transfer_leg.py` — `READ_IN_FULL`
55. `scripts/regression-harness/vpab_frame_gate.py` — `READ_IN_FULL`
56. `scripts/regression-harness/vpml_host_surface.py` — `READ_IN_FULL`
57. `scripts/release/make_factory_image.py` — `READ_IN_FULL`
58. `tests/_fwpath.py` — `READ_IN_FULL`
59. `tests/test_audio_profile_tombstone_static.py` — `READ_IN_FULL`
60. `tests/test_boot_palette_lock_static.py` — `READ_IN_FULL`
61. `tests/test_chord_saliency_replay.py` — `READ_IN_FULL`
62. `tests/test_diag_capture_static.py` — `READ_IN_FULL`
63. `tests/test_effect_registry_dense_static.py` — `READ_IN_FULL`
64. `tests/test_gdft_harness_schema_static.py` — `READ_IN_FULL`
65. `tests/test_im69d_env_static.py` — `READ_IN_FULL`
66. `tests/test_k1_loud_guard_static.py` — `READ_IN_FULL`
67. `tests/test_k1_response_normalisation_gate.py` — `READ_IN_FULL`
68. `tests/test_k1_ws_registry_codegen.py` — `READ_IN_FULL`
69. `tests/test_mutation_anchor_uniqueness_static.py` — `READ_IN_FULL`
70. `tests/test_palette_authority_static.py` — `READ_IN_FULL`
71. `tests/test_render_trace_static.py` — `READ_IN_FULL`
72. `tests/test_smart_auto_product_ab_capture.py` — `READ_IN_FULL`
73. `tests/test_stm_vp_compare.py` — `READ_IN_FULL`
74. `tests/test_trace_dev_static.py` — `READ_IN_FULL`
75. `tests/test_vpab_gate.py` — `READ_IN_FULL`
76. `tests/test_vpml_run_console_server_smoke.py` — `READ_IN_FULL`

## Scheduling, publication, and timing findings

### Confirmed architecture and timing behaviour

1. **The source distinguishes the AP-frame cadence from the novelty/tempo-emission cadence.** `audio/k1_stm.h:18-37` identifies a 133.33 Hz AP update and a 17-frame, approximately 127.5 ms STM window. `scripts/regression-harness/acf_ceiling_sweep.py:32-40,63-97` models the accepted novelty stream as decimated by three, yielding approximately 44.44 Hz, and `scripts/regression-harness/device_novelty_replay.py:183-218` reconstructs three AP frames per accepted novelty record. Scheduler work must not collapse these into one generic “audio rate”.

2. **Render and director time evolution is mostly elapsed-time based, but not uniformly so.** `director/beat_aware_director.cpp:349-360`, `effects/light_mode_dense_forge.cpp:91-100`, `effects/light_mode_pulse_prism.cpp:60-69`, and `effects/light_mode_waveform_hybrid.cpp:9-22` derive `dt` from `millis()` and bound it. In contrast, `effects/light_mode_waveform_hybrid.cpp:9-22` also applies a fixed `0.08/0.92` peak smoothing step per render; `visual/led_utilities.h:385-453` advances boot fade by a fixed `0.005` per frame; `visual/led_utilities.h:1675-1705` advances a transition fade by `0.02` per frame; `visual/led_utilities.h:1937-2062` carries fixed per-frame colour-shift smoothing/advance; and `visual/led_utilities.h:2638-2641` advances an optional wave by `0.03` per frame. Those behaviours change with scheduler cadence or missed frames.

3. **The effect lifecycle explicitly crosses cores.** `effects/framework/IEffect.h:9-19,46-53` assigns `render()` to Core 1 but `init()` and `cleanup()` to Core 0, while allocating buffers larger than 64 bytes only during lifecycle calls. Any scheduler redesign must preserve a synchronisation/lifetime barrier between Core-0 lifecycle mutation and Core-1 render use; this chunk does not contain the complete orchestrator that proves that barrier.

4. **The framework transition engine is elapsed-time based and preallocates.** `effects/framework/TransitionEngine.cpp:65-93` allocates transition buffers at `begin()` using PSRAM only and fails closed to a hard cut if allocation fails. `TransitionEngine.cpp:97-123` snapshots both transition endpoints before activation, and `TransitionEngine.cpp:147-178` derives progress from elapsed milliseconds rather than frame count.

5. **The LED output path serialises substantial work in one call.** `visual/led_utilities.h:953-1208` performs primary preparation, secondary preparation, quantisation, diagnostics, and `FastLED.show()` in sequence, with timing taps around the stages. This source proves the call is synchronous at the C++ call site; it does not prove whether the underlying RMT driver blocks until physical wire completion. `tests/test_vpab_gate.py:157-188` deliberately treats effect render budget separately from the overall final-byte/frame gate unless strict render-budget mode is selected.

6. **Diagnostic capture has explicit concurrency protection and transport accounting.** `tests/test_diag_capture_static.py:81-109` requires critical sections for the diagnostic pool and VPAB capture state, preflight capacity checks before render-reachable pushes, and copying capture mode/once state while protected. `scripts/regression-harness/vpab_frame_gate.py:226-389` fails closed on framing, sequence, CRC, dropped, corrupt, and overflowed counters. These diagnostics can support scheduler validation, but self-shadow evidence remains instrumentation smoke rather than independent memory proof (`tests/test_vpab_gate.py:48-64,109-120`).

7. **A dedicated render-halt/park handshake exists, but not every blocking LED helper uses it.** `system/globals.h:488-505,1040-1071` defines volatile `led_thread_halt`/`render_thread_parked` flags and `lock_leds()`, which waits at most 100 ms in 1 ms delays and then fails open. `visual/led_utilities.h:1285-1306` implements `blocking_flash()` by setting the halt flag directly, calling `show_leds()`, and invoking `FastLED.delay(150)` twice, without using the park acknowledgement helper. This is a concrete scheduling collision surface if called after the render task is live.

8. **The director uses a frame-boundary commit model.** `director/beat_aware_director.cpp:379-409` records switch telemetry, starts transition state, arms a pending primary preset, and requests a commit; its own comment states the Core-1 frame tick lands the swap at the next frame boundary. `serial/serial_cmd_handlers.h:8-21,70-117` likewise distinguishes deferred mode/queue actions from immediate save-and-reboot commands. A scheduler hardening design must preserve those different command completion semantics.

9. **Host FreeRTOS stubs erase concurrency semantics by design.** `scripts/regression-harness/stubs/freertos/task.h:24-52` makes critical sections, task creation, delay, delete, current-task lookup, and stack-watermark calls no-ops or constants. Host compile/replay gates that use this stub cannot establish cross-core ordering, blocking behaviour, task priority correctness, or stack margin.

10. **Existing static safety coverage is narrower than a runtime scheduling proof.** `scripts/hooks/framework-safety-gate.sh:32-69` checks for flash helper symbols and a non-empty `lock_leds()` implementation, but does not validate acknowledgement ordering, timeout behaviour, caller compliance, task priority, or contention. `effects/framework/zone_composer_compile_probe.cpp:5-13` is explicitly compile-only. These surfaces must not be promoted into scheduler proof.

### Publication and coherence questions requiring the owning source chunk

1. **Separate audio read calls can produce a mixed-generation render view unless their publication APIs couple generations.** `director/beat_aware_director.cpp:349-373` reads `K1AudioSnapshot` and then `AudioSemanticState` separately. `effects/light_mode_dense_forge.cpp:91-100` and `effects/light_mode_pulse_prism.cpp:60-69` each perform three separate audio/event/tempo reads. The read APIs' implementation is outside this assigned chunk, so this is an audit question, not a confirmed torn-read defect.

2. **Mic auto-sense publication is plain static-field copy in this chunk.** `audio/k1_mic_auto_sense.cpp:17-23,47-67,134-145` stores telemetry/result fields in static state and copies them into an output struct without a mux, atomic sequence, or double-buffer protocol visible here. The caller and task ownership are outside this chunk; verify that all reads and writes are single-task, or add a publication protocol.

3. **Director status state is read outside its configuration mux.** `director/beat_aware_director.cpp:266-277` protects configuration with `g_bad_config_mux`, while serial-task status accessors at `:288-330` directly read director state and telemetry written by the render tick. Word-sized fields may be individually atomic on ESP32-S3, but a multi-field status sample is not shown to be coherent. The same audit should cover `director/k1_smart_director.cpp:298-373`, whose separate config/output/manual muxes do not by themselves prove a single coherent status generation.

4. **A render-time lazy-allocation fallback exists.** `visual/led_utilities.h:895-951` allows `scale_to_strip()` to call `init_lerp_params()` when uninitialised, and that initialiser allocates. Normal initialisation appears to call it before rendering, but a hard real-time gate should prove the lazy branch is unreachable after the render task starts or replace it with a fail-closed precondition.

5. **Published/global chromagram construction has no barrier visible in this chunk.** `visual/led_utilities.h:2107-2225` clears and rebuilds global chromagram/telemetry arrays. The owning producer/consumer schedule and publication barrier are outside this file; verify task ownership and snapshot coherence before changing cadence.

6. **Tempo event edge semantics matter to effect spawning.** `effects/light_mode_pulse_prism.cpp:94-120` deduplicates kick/transient events with IDs, while the tempo beat fallback has no local event-ID check. If `beat_tick` is a held state rather than a one-publication edge, multiple render frames could spawn from one beat. `effects/light_mode_tempo_comet_anticipate.cpp:110-176` avoids this class by advancing its own flywheel and spawning only on an internal phase wrap. Confirm the publisher's `beat_tick` lifetime.

## Hardening implications for the scheduling design

- Define each cadence independently: I2S/DMA chunk, AP frame, accepted novelty/tempo emission, semantic publication, visual render, LED output, and low-rate serial/diagnostic reporting.
- Establish one documented publication primitive per cross-core state, including generation/coherence semantics for compound structs and groups of related surfaces.
- Treat Core-0 effect lifecycle versus Core-1 rendering as a formal ownership transfer with an acknowledged park/quiescence barrier.
- Convert the listed fixed-per-frame temporal paths to elapsed-time behaviour before changing render cadence, or explicitly freeze their current cadence as a behavioural contract.
- Prove the render hot path cannot enter lazy allocation, blocking flash, serial output, filesystem work, or unacknowledged LED ownership paths.
- Keep diagnostic/probe overhead opt-in and measure its effect separately; host stubs and structural gates cannot prove scheduling safety.

## Exact completion count

`ASSIGNED=76; READ_IN_FULL=76; FAILED=0; COUNT_MATCH=YES`
