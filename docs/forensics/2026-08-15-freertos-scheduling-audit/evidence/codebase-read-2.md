# FRTOS-10 — Codebase full-read evidence, chunk 2

## Scope and identity

| Item | Evidence |
|---|---|
| Delegation | FRTOS-10 / `codebase-read-2` |
| Source manifest | `/tmp/k1-source-manifest.WdLSdO/chunk_2.txt` |
| Manifest SHA-256 | `c5fe5a1c059b9bbdb256a9814ddb1a282427985cc6a3946ab43f247c903b7fb7` |
| Manifest entries | 77 |
| Files read in full | 77 |
| Read failures | 0 |
| Write scope | This evidence file only |

Every manifest entry below was read from first line to end of file. Grouped reads whose terminal output reached an output boundary were not accepted as proof; affected files were subsequently read individually in full.

## Architectural findings relevant to scheduling, publication, and timing

### 1. `AudioSemanticState` is individually coherent but not an atomic multi-producer epoch

`k1_get_semantic_state()` invokes three separately protected accessors and deliberately adds no enclosing lock (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.h:7-15`). This preserves the coherence of each producer-owned object, but it does not guarantee that tempo, onset, and audio-snapshot fields came from the same audio frame. The composite contains a one-read `beat_tick` edge (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.h:53`) alongside snapshot timing/frame fields (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.h:85`). Consumers must therefore treat it as a best-effort cross-domain view, not a transactional publication.

This is visible in an effect consumer: waveform-tempo reads tempo and audio snapshot through separate accessors (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp:163-175`). A pre-emption or producer publish between those reads can construct a mixed epoch even though neither individual read is torn.

**Scheduling implication:** any hard temporal relationship between onset, phase, beat edge, and spectrum needs a publisher-owned generation/sequence contract or one atomic aggregate snapshot. Increasing task priority cannot repair a publication-epoch ambiguity.

### 2. The one-update beat edge can be sampled twice or missed

The semantic contract describes `beat_tick` as true for one read (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.h:53`). Tempo River Walk explicitly avoids relying on that edge and detects a beat through phase wrap because a render task can observe an AP update twice or miss it (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river_walk.cpp:128-140`).

Visual hooks deduplicate events by `event_id`, age-gate them, and only confirm the boundary when an eligible event still carries `event.beat` (`SPECTRASYNQ_K1_FIRMWARE/director/k1_visual_hooks.cpp:77-126`). That is robust only if the publisher retains the event identity and beat indication for the entire eligibility window.

**Scheduling implication:** edges crossing unequal-rate tasks should be represented as monotonic sequence/event identifiers with explicit acknowledgement or age semantics, not as a one-poll boolean.

### 3. The effect queue has a sound single-owner frame-boundary contract

The effect queue documents that loop/Core 0 may publish pending state and commit requests, while Core 1 consumes and applies them before channel construction at a frame boundary; file I/O remains on the loop core (`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.h:8-16`). A commit is published as a request (`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.h:129-135`), and the render owner consumes it and initiates transition/application (`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.h:156-170`).

**Scheduling implication:** this is the preferred pattern for scheduler hardening: bounded cross-core publication, sole mutation by the render owner, and expensive persistence excluded from the render task.

### 4. Diagnostic capture uses a bounded but payload-sized critical section

Diagnostic capture enters a spinlock before writing the slot header and copying the payload, and releases it only after the copy (`SPECTRASYNQ_K1_FIRMWARE/diag/diagnostic_capture.cpp:133-174`). Static storage bounds the operation, but lock hold time still scales with payload length. If this producer is called from a timing-critical task, the other core or any participant sharing the mux can stall for the complete copy.

The drain accessor returns a pointer after releasing the lock (`SPECTRASYNQ_K1_FIRMWARE/diag/diagnostic_capture.cpp:183-198`). Its lifetime is safe only while the capture remains frozen/draining according to the surrounding state contract.

**Scheduling implication:** keep diagnostic capture out of hard real-time paths, measure worst-case lock hold time, and preserve the frozen-buffer lifetime invariant explicitly.

### 5. EdgeMixer mostly follows snapshot-compute-publish discipline

EdgeMixer copies configuration/matrix inputs under its mux, performs costly floating-point work outside the critical section, then atomically publishes the derived matrix (`SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp:76-117`, `SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp:834-920`, `SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp:1042-1054`, `SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp:1102-1119`). The render-side lock is limited to copying 18 coefficients. This is a strong publication pattern.

The lazy LUT initialisation uses an unguarded static `ready` flag (`SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp:935-1003`). It is safe only under a single render-owner call contract; concurrent first calls would race.

**Scheduling implication:** retain the short-copy lock boundary, and encode/assert single-owner initialisation or initialise the LUT before task start.

### 6. The dual-sync probe is isolated from Core 0, but its transport assumptions are explicit risks

The source is gated as probe-only (`SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:4-25`). It creates one dedicated Core 1 task at priority 1 with a 4096-byte stack (`SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:1317-1328`) and uses a 5 ms task delay in its service loop (`SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:1185-1258`). Static tests enforce the Core 1 / priority 1 / single-task source contract (`tests/test_dual_sync_probe_firmware_static.py:189-207`).

BLE callbacks enqueue into a fixed queue without blocking and count drops (`SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:789-805`); the queue depth is 16 and statically allocated (`SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:205-210`). The ISR ring is drop-on-full and uses volatile producer/consumer indices (`SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:87-113`), but contains no explicit atomic ordering or memory barrier. It relies on the ESP32 single-producer/single-consumer execution and compiler-ordering assumptions.

Connection/subscription can delay for 250 ms and retry with 100 ms delays (`SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:966-986`), but that blocking work is confined to the low-priority Core 1 sync task.

**Scheduling implication:** production promotion would require measured contention against rendering, explicit memory-order justification for the ISR ring, queue saturation/drop telemetry, and confirmation that BLE stack work cannot inherit a priority that disturbs audio.

### 7. Loop-core services contain bounded polling plus synchronous jitter sources

Encoder service uses a 5 ms polling/recovery cadence and synchronous I2C operations (`SPECTRASYNQ_K1_FIRMWARE/persistence/encoders.h:137-165`), delayed persistence (`SPECTRASYNQ_K1_FIRMWARE/persistence/encoders.h:769-772`), and a 100 ms LED/I2C update cadence (`SPECTRASYNQ_K1_FIRMWARE/persistence/encoders.h:839-911`). Its initialisation also contains a 300 ms boot delay (`SPECTRASYNQ_K1_FIRMWARE/persistence/encoders.h:62-81`).

Serial polling is bounded to 32 bytes per invocation and rate-limited to a greater-than-10 ms cadence (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp:3732-3787`). The poller is bounded, but dispatched commands can still perform synchronous persistence, reboot, or substantial serial output. Serial initialisation's 250 ms wait/yield is boot-only (`SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp:623-647`).

**Scheduling implication:** scheduler hardening must inventory handler execution time, not only poll-loop byte bounds. Persistence and I2C should remain outside hard real-time audio/render ownership.

### 8. Render effects use dt correction, but clamp away long stalls

River Surge derives delta time from `millis()` and clamps it to 1–50 ms before dt-correct smoothing (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_river_surge.cpp:89-126`). Tempo River Walk applies the same 1–50 ms clamp (`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river_walk.cpp:91-100`). This prevents unstable catch-up after a stall, but deliberately loses elapsed simulation time beyond 50 ms.

Transition Overlay converts a full strip into its internal format, updates the transition engine, and converts the strip back on each seam call (`SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionOverlay.cpp:90-130`). If invoked independently for both channels in one frame, both the transition update and full-strip conversion cost can occur twice. Its allocations are confined to initialisation and fail closed (`SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionOverlay.cpp:45-65`).

Beat Pulse Resonant uses a raw-time metronome fallback when tempo is unlocked (`SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_beat_pulse_resonant.cpp:107-126`) and performs full per-pixel exponential shaping (`SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_beat_pulse_resonant.cpp:138-239`). `render_params` stores mutable global stack/fallback state without synchronisation, which is valid only under sole render-task ownership (`SPECTRASYNQ_K1_FIRMWARE/visual/render_params.cpp:60-88`).

**Scheduling implication:** measure per-effect worst-case execution, especially dual-channel transition seams and exponentials; document the intentional 50 ms time-loss policy; assert the sole render-owner rule.

### 9. Cadence contracts are encoded in analysis tooling, not established as runtime proof

The AV layer classifier pins AP0 to 12.8 kHz / 96 samples / decimation 3 and VP1/DMA3 classification (`scripts/regression-harness/k1_av_layer_classifier.py:11-17`, `scripts/regression-harness/k1_av_layer_classifier.py:76-106`). This is useful drift detection, but it validates source/evidence classification rather than live scheduling latency or deadline adherence.

Several probe and regression tools intentionally hard-code ports, capture cadence, or replay fixtures. Those scripts are evidence tooling and must not be treated as proof of the production scheduler unless their acquisition provenance matches the target firmware and device.

### 10. Host gates do not exercise cross-core scheduling semantics

Host shims reduce critical sections to no-ops (`scripts/regression-harness/edgemixer_host_shim/Arduino.h:11-15`; the generated shim in `scripts/regression-harness/golden/oracle_hostcompile.py:25-33` follows the same model). Visual-hooks replay is single-threaded, and `tests/test_visual_hooks_replay.py` delegates to that replay. The dual-sync static test checks source shape and explicitly does not execute the firmware scheduler.

**Proof boundary:** these tests can establish logic, source-policy, and deterministic replay properties. They cannot establish ESP32 cross-core memory ordering, contention, mux hold time, priority inversion, task starvation, missed one-update edges, stack headroom, or audio-to-visual deadline compliance. Those require target instrumentation and device evidence in a separately authorised lane.

## Per-path full-read ledger

1. `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` — `READ_IN_FULL`
2. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.h` — `READ_IN_FULL`
3. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_health.cpp` — `READ_IN_FULL`
4. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.h` — `READ_IN_FULL`
5. `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm_fft512_bench.h` — `READ_IN_FULL`
6. `SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.h` — `READ_IN_FULL`
7. `SPECTRASYNQ_K1_FIRMWARE/diag/diagnostic_capture.cpp` — `READ_IN_FULL`
8. `SPECTRASYNQ_K1_FIRMWARE/diag/k1_trace.h` — `READ_IN_FULL`
9. `SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer.cpp` — `READ_IN_FULL`
10. `SPECTRASYNQ_K1_FIRMWARE/director/k1_visual_hooks.cpp` — `READ_IN_FULL`
11. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectParameter.h` — `READ_IN_FULL`
12. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/K1BufferView.h` — `READ_IN_FULL`
13. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionOverlay.cpp` — `READ_IN_FULL`
14. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_beat_pulse_resonant.cpp` — `READ_IN_FULL`
15. `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_harmonic_tide.h` — `READ_IN_FULL`
16. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_bloom.cpp` — `READ_IN_FULL`
17. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_ember.cpp` — `READ_IN_FULL`
18. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_river_surge.cpp` — `READ_IN_FULL`
19. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_river_walk.cpp` — `READ_IN_FULL`
20. `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp` — `READ_IN_FULL`
21. `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.cpp` — `READ_IN_FULL`
22. `SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp` — `READ_IN_FULL`
23. `SPECTRASYNQ_K1_FIRMWARE/persistence/encoders.h` — `READ_IN_FULL`
24. `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp` — `READ_IN_FULL`
25. `SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_dispatch.cpp` — `READ_IN_FULL`
26. `SPECTRASYNQ_K1_FIRMWARE/system/k1_bootloop_guard.h` — `READ_IN_FULL`
27. `SPECTRASYNQ_K1_FIRMWARE/visual/Palettes.cpp` — `READ_IN_FULL`
28. `SPECTRASYNQ_K1_FIRMWARE/visual/render_params.cpp` — `READ_IN_FULL`
29. `scripts/agent/repo-truth.sh` — `READ_IN_FULL`
30. `scripts/dual_sync_probe/correlate.py` — `READ_IN_FULL`
31. `scripts/dual_sync_probe/f2_status.py` — `READ_IN_FULL`
32. `scripts/dual_sync_probe/run_f2_ports.sh` — `READ_IN_FULL`
33. `scripts/hooks/wip-checkpoint.sh` — `READ_IN_FULL`
34. `scripts/platformio/k1_upload_guard.py` — `READ_IN_FULL`
35. `scripts/regression-harness/analyse_smart_edge_runtime_capture.py` — `READ_IN_FULL`
36. `scripts/regression-harness/beat_aware_director_boundary_proof.py` — `READ_IN_FULL`
37. `scripts/regression-harness/compile_stm_host.sh` — `READ_IN_FULL`
38. `scripts/regression-harness/edgemixer_host_shim/Arduino.h` — `READ_IN_FULL`
39. `scripts/regression-harness/foote_ssm_boundary_lift.py` — `READ_IN_FULL`
40. `scripts/regression-harness/golden/oracle_ble_midi_diff.py` — `READ_IN_FULL`
41. `scripts/regression-harness/golden/oracle_hostcompile.py` — `READ_IN_FULL`
42. `scripts/regression-harness/golden/oracle_tempo.py` — `READ_IN_FULL`
43. `scripts/regression-harness/k1_av_layer_classifier.py` — `READ_IN_FULL`
44. `scripts/regression-harness/k1_loud_guard_ab_capture.py` — `READ_IN_FULL`
45. `scripts/regression-harness/k1_serial_safety.py` — `READ_IN_FULL`
46. `scripts/regression-harness/lgp_optics.py` — `READ_IN_FULL`
47. `scripts/regression-harness/noise_cal_quality_model.py` — `READ_IN_FULL`
48. `scripts/regression-harness/p5b_matrix_leg.py` — `READ_IN_FULL`
49. `scripts/regression-harness/render_host_globals.cpp` — `READ_IN_FULL`
50. `scripts/regression-harness/sample_rate_32k_migration_model.py` — `READ_IN_FULL`
51. `scripts/regression-harness/smart_edge_runtime_capture.py` — `READ_IN_FULL`
52. `scripts/regression-harness/spectral_honesty_probe.cpp` — `READ_IN_FULL`
53. `scripts/regression-harness/stubs/FastLED.h` — `READ_IN_FULL`
54. `scripts/regression-harness/tempo_accuracy.py` — `READ_IN_FULL`
55. `scripts/regression-harness/visual_hooks_replay.py` — `READ_IN_FULL`
56. `scripts/regression-harness/vpab_post_switch_capture.py` — `READ_IN_FULL`
57. `scripts/regression-harness/vpml_run_console.py` — `READ_IN_FULL`
58. `scripts/release/make_unit_nvs.py` — `READ_IN_FULL`
59. `tests/tab5_harness_spec/__init__.py` — `READ_IN_FULL`
60. `tests/test_audio_telemetry_schema_static.py` — `READ_IN_FULL`
61. `tests/test_build_config_policy_static.py` — `READ_IN_FULL`
62. `tests/test_commit_gate_classification.py` — `READ_IN_FULL`
63. `tests/test_dual_sync_probe_firmware_static.py` — `READ_IN_FULL`
64. `tests/test_f2_ports_reboot.py` — `READ_IN_FULL`
65. `tests/test_gdft_int64_recurrence.py` — `READ_IN_FULL`
66. `tests/test_im73d_audio_purity_static.py` — `READ_IN_FULL`
67. `tests/test_k1_paired_snappiness_capture.py` — `READ_IN_FULL`
68. `tests/test_k1_stm_replay.py` — `READ_IN_FULL`
69. `tests/test_loop.py` — `READ_IN_FULL`
70. `tests/test_noise_cal_quality_model.py` — `READ_IN_FULL`
71. `tests/test_palette_hd_static.py` — `READ_IN_FULL`
72. `tests/test_serial_hotkeys_static.py` — `READ_IN_FULL`
73. `tests/test_smart_edge_runtime_analysis.py` — `READ_IN_FULL`
74. `tests/test_tab5_dispatch_replay.py` — `READ_IN_FULL`
75. `tests/test_visual_hooks_replay.py` — `READ_IN_FULL`
76. `tests/test_vpml_evidence_page.py` — `READ_IN_FULL`
77. `tests/test_waveform_hybrid_k1_static.py` — `READ_IN_FULL`

## Exact count reconciliation

| Counter | Count |
|---|---:|
| Manifest entries | 77 |
| Ledger entries | 77 |
| `READ_IN_FULL` | 77 |
| Failures | 0 |

The manifest count, evidence-ledger count, and successful full-read count reconcile exactly at **77**.

## Action boundary

Actions were limited to read-only file inspection, line/count inspection, manifest hashing, and creation of this evidence document. No build, test, Git, device, upload, serial, or runtime action was performed.
