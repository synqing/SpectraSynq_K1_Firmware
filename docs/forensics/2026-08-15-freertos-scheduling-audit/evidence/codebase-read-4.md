# FRTOS-12 exhaustive codebase read — manifest chunk 4

## Scope and result

- Contract: `docs/forensics/2026-08-15-freertos-scheduling-audit/DELEGATION_CONTRACTS.md`, FRTOS-12.
- Repository path used: `/Users/spectrasynq/SpectraSynq_K1_Firmware` (the parent task expressly prohibited git commands, so the contract's `git rev-parse` command was not run).
- Manifest: `/tmp/k1-source-manifest.WdLSdO/chunk_4.txt`
- Manifest/chunk SHA-256: `90fbce9d50fcbc314ca85d2b5de9e8fd35f432c12a20ccb4d8afa2e8a7709290`
- Assigned entries: **76**
- `READ_IN_FULL`: **76**
- Failures: **0**
- Final count: **76 / 76**, matching the chunk.
- Boundary: source priming and architectural evidence only. No build, tests, git action, device action, firmware edit, or edit outside this evidence file was performed.

## Scheduling, publication, and timing findings

### 1. The production timing tuple makes Core 0 the audio/main-loop side and Core 1 the LED side

The shipping `k1_hardware` environment removes Arduino's Core-1 loop default, sets `ARDUINO_RUNNING_CORE=0`, and sets `K1_LED_TASK_CORE=1`. Its production audio tuple is 12,800 samples/s, 96 samples/chunk, DMA descriptor count 3, and tempo novelty decimation 3. This implies a nominal AP frame period of **7.5 ms** and AP rate of **133.33 Hz** before the tempo decimator. The same production environment deliberately enables int64 magnitude and recurrence inside the GDFT hot loop; its own source comments identify Core-0 cadence measurement as a pre-promotion concern (`platformio.ini:59-98`).

This source chunk does not contain the complete main sketch or LED task implementation, so the full task priority/stack/call-chain must be reconciled with the other manifest readers. The core affinity and audio tuple above are direct production flags, not architecture-prose inference.

### 2. I2S acquisition is bounded in production, but its default 100 ms bound is far larger than one AP period

`acquire_sample_chunk()` requests one 96-sample chunk and uses a production-enabled freeze guard. The guard replaces `portMAX_DELAY` with `pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS)`, zero-filling any short or failed read instead of reusing stale DMA bytes (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:406-488`). The default timeout is **100 ms**, explicitly described as much greater than the 7.5 ms chunk period (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:45-53`, `:86-88`).

Consequences:

- The guard closes an infinite freeze, not an AP-deadline miss. One worst-case timed-out read can span roughly 13 nominal AP periods.
- Timeout/short-read recovery preserves forward progress and publication liveness by producing a silence chunk, but downstream state can still be stale for the duration of the blocked read.
- The flag-off branch remains an indefinite `portMAX_DELAY` path and must remain excluded from any production-hardening conclusion.

### 3. Core-0 active work contains more than DMA wait and GDFT

After acquisition, the audio path performs de-interleave where applicable, raw-domain telemetry/accounting, conditioning, calibration state updates, silence classification, rolling-window copies, and fixed-point conversion before later AP stages (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:489-520`, `:1120-1213`). The 1 Hz AP stream is serial-gated, but when enabled it reads tempo/onset publication and formats a long USB record from the AP path (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:1215-1240`).

The cadence probe defines **active AP work** separately from I2S waiting and fails/counts work above 7,500 us. Its soak path tracks frame gaps, timestamp regressions, core mismatches, active-work histograms and worst samples (`SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.cpp:430-483`). This distinction is essential: chunk duration, wall-clock AP-loop time, I2S wait, active compute time, and end-to-end publication latency are not interchangeable.

### 4. Accepted calibration performs synchronous persistence and serial output from the GDFT/AP execution path

`process_GDFT()` completes calibration inside the audio/GDFT path. It prints a multi-field quality record, resets AGC state, then synchronously calls `save_ambient_noise_calibration()`, `save_config()`, and `save_calibration_profile()` before printing acceptance (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:240-300`). A rejected calibration also prints and restores the previous profile.

This is a distinct scheduling hazard from steady-state DSP: flash/filesystem persistence and serial formatting are exceptional but potentially long Core-0 work. Hardening should move persistence out of the AP deadline path or explicitly treat calibration as a controlled degraded-real-time state with measured publication/render consequences. It should not be hidden by steady-state cadence percentiles.

### 5. The GDFT is a full-bin, per-frame hot loop; production widens its arithmetic

The assigned GDFT source computes magnitude and smoothing for every safe bin, and production enables int64 recurrence and magnitude paths (`platformio.ini:78-98`; `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:168-219`). The assigned deterministic GDFT harness documents that this fork processes all 80 bins each call and that the apparent interlace state is inert (`SPECTRASYNQ_K1_FIRMWARE/diag/gdft_harness.h:42-48`).

The harness is not production capacity evidence: it is a non-shipping, synthetic procedure that halts the LED thread, snapshots global buffers, repeatedly calls unmodified GDFT until convergence, and restores link-visible state; two function-local statics are explicitly not restorable (`SPECTRASYNQ_K1_FIRMWARE/diag/gdft_harness.h:20-28`, `:65-72`, `:430-488`). It proves algorithm behaviour under its boundary, not concurrent AP/VP scheduling safety.

### 6. Musical-saliency continuous state is value-copied atomically; its event surface is only a single overwriteable slot

The saliency module holds one axis frame, one event, and one valid bit behind a `portMUX_TYPE`. Both publication and read copy the complete struct inside the critical section (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_musical_saliency.cpp:25-64`, `:253-269`). This is suitable as a latest-state snapshot: readers cannot observe a torn struct.

The event contract is weaker. A new salient event overwrites the single stored event and leaves the valid bit true; a reader may optionally clear it (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_musical_saliency.cpp:249-250`, `:260-269`). Therefore:

- multiple producer events between reads collapse to the latest one;
- clear-after-read is a consume operation, not a broadcast;
- the primitive is not a counted edge queue and cannot promise exactly-once delivery to multiple consumers.

Any unified publication design must keep latest continuous state separate from edge/event semantics. A VP-local copy can solve snapshot lifetime/torn-read hazards, but it does not by itself solve overwritten or multiply-consumed events.

### 7. Tempo's declared cross-core contract is also value-copy under a critical section

`k1_tempo.h` declares Core 0 as the tempo-state owner and describes a `K1TempoEvent` value-copy publication under a `portMUX` spinlock for Core-1 reads. The event includes continuous fields and the one-frame `beat_tick`. Because the implementation file is outside this chunk, the exact publish/read interleavings must be verified by its assigned reader. The header contract nevertheless reinforces the need to distinguish a latest snapshot containing an edge flag from a durable edge-delivery mechanism.

### 8. Production is wireless-free; the WebSocket task and its Core-0 interference are bench-only in this source truth

`k1_wireless.cpp` is included only by `k1_wireless_ab_probe`, which is explicitly non-shippable; `k1_hardware` remains wireless-free (`platformio.ini:727-747`). In that probe build:

- the WebSocket task defaults to Core 0 and compilation rejects placing it on the LED core;
- it runs at `tskIDLE_PRIORITY + 1`, with stack 6144 and a 5 ms delay;
- request and outbound queues each have capacity 8;
- the WebSocket task drains at most four outbound frames per tick;
- `k1_wireless_poll()` drains at most four control requests per AP tick and yields one tick every 250 ms while a station is connected (`SPECTRASYNQ_K1_FIRMWARE/network/k1_wireless.cpp:20-50`, `:835-866`, `:875-951`).

These are real interference mechanisms for the A/B probe, but they must not be reported as shipping production load. They are useful adversarial cases for queue bounds and Core-0 contention.

### 9. BLE Deck state publication is bounded in normal draining but has synchronous overflow recovery

The BLE-only Deck state transmitter uses a fixed 32-entry delta ring (`SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_tx.cpp:3-43`). Its poll drains at most four deltas to avoid starving audio (`:447-459`). However, `publish_apply()` attempts immediate ATT delivery when the queue is empty. On queue overflow it clears the queue, marks resnapshot required, and calls `k1_deck_state_tx_resnapshot()` synchronously before re-enqueueing the latest delta (`:400-444`). A resnapshot emits HELLO plus a complete snapshot, fragmented into ATT-sized writes (`:55-74`, `:378-397`).

Therefore the queue is memory-bounded, but producer execution time is not bounded merely by its depth. Immediate writes and synchronous resnapshot are radio/transport latency risks if invoked in an AP-owned path. This build is non-shipping radio scope in the current `platformio.ini`, and the complete caller/core ownership must be reconciled with the BLE implementation files outside this chunk.

### 10. Diagnostic capture is deliberately outside the production scheduling envelope

`k1_ap_capture_telemetry.cpp` is compiled only when both tempo stream and AP frontend debug are enabled; its preprocessor gate intentionally makes the translation unit empty in production (`SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.cpp:1-19`). The probe allocates its cadence buffer from PSRAM/heap when armed (`:210-224`) and its dump prints every buffered row, yielding once per 16 rows (`:780-817`).

Those allocations and yields are valid evidence-tool behaviour, not production hot-path behaviour. Conversely, capture results can measure production-like algorithms only to the extent that the probe flags, buffering, timers, and serial activity are accounted for. The code correctly subtracts I2S wait for active-work classification, but observer overhead remains a required evidence boundary.

### 11. VP Motion Lab is a single-owner frame harness, not an alternate production scheduler

The VP Motion Lab is explicitly non-shippable, fixed-programme, no-audio, no-persistence, and no-wireless (`SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h:1-13`). It owns inline global harness state, snapshots/overrides render configuration, clears buffers, and restores state on stop (`:64-80`, `:381-426`). This is useful proof machinery for final-byte and render timing evidence, but it removes the normal audio-driven producer/consumer schedule and cannot validate publication freshness or AP-to-VP latency.

### 12. The assigned tests encode useful hardening invariants but are mostly structural/host gates

The assigned test corpus pins several scheduling-relevant contracts:

- AP cadence evidence distinguishes I2S wait from active compute and requires the production 12.8k/96 and probe 16k/120 tuples.
- production ACF work-spreading is source-pinned and was promoted only after device evidence; matrix environments remain non-shippable.
- the microphone auto-sense module is required to be heap-free, blocking-free, serial-silent, persistence-free, and executed after GDFT/loud-guard rather than inside the per-sample loop.
- VP Motion Lab render functions are statically forbidden from delay, serial, heap, filesystem, Wi-Fi, and `show_leds()` inside the per-frame renderer.
- replay harnesses test tempo flywheel tick density and phase, but host Arduino stubs make critical sections no-ops; they prove algorithm semantics, not cross-core exclusion.

These gates are reusable for Gate 0, but none substitutes for on-device timing under the exact production binary and exact task topology.

## Required per-path ledger

1. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`
2. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp`
3. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/audio/k1_musical_saliency.cpp`
4. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stereo_probe.cpp`
5. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.h`
6. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/control/k1_noise_cal_arm.h`
7. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/diag/gdft_harness.h`
8. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/diag/vp_motion_lab.h`
9. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/director/k1_edgemixer_lite.h`
10. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/framework/BlendMode.h`
11. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectRegistry.h`
12. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/framework/LegacyEffectAdapter.h`
13. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/framework/TransitionTypes.h`
14. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_beat_prism.cpp`
15. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_transient_lattice.h`
16. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_chromagram_dots.cpp`
17. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_gdft.cpp`
18. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_spectrum_river.cpp`
19. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_vu_dot.cpp`
20. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.h`
21. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_tx.cpp`
22. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/network/k1_wireless.cpp`
23. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/serial/k1_ap_capture_telemetry.cpp`
24. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/serial/serial_parse_helpers.cpp`
25. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h`
26. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/system/k1_tunables_generated.h`
27. `READ_IN_FULL` — `SPECTRASYNQ_K1_FIRMWARE/visual/channel_effect_state.h`
28. `READ_IN_FULL` — `platformio.ini`
29. `READ_IN_FULL` — `scripts/agent/tab5_protocol_parity_gate.py`
30. `READ_IN_FULL` — `scripts/dual_sync_probe/f2_flash.py`
31. `READ_IN_FULL` — `scripts/dual_sync_probe/logfmt.py`
32. `READ_IN_FULL` — `scripts/dual_sync_probe/run_gate0_segments.sh`
33. `READ_IN_FULL` — `scripts/install-thinking-skills.sh`
34. `READ_IN_FULL` — `scripts/refactor/extract_typed_handlers.py`
35. `READ_IN_FULL` — `scripts/regression-harness/ap_drive_contract_test.cpp`
36. `READ_IN_FULL` — `scripts/regression-harness/beat_semantic_metrics.py`
37. `READ_IN_FULL` — `scripts/regression-harness/device_ap_cadence_capture.py`
38. `READ_IN_FULL` — `scripts/regression-harness/edgemixer_oklab_probe.cpp`
39. `READ_IN_FULL` — `scripts/regression-harness/gdft_center_honesty_model.py`
40. `READ_IN_FULL` — `scripts/regression-harness/golden/oracle_bridge_fs_codec.py`
41. `READ_IN_FULL` — `scripts/regression-harness/golden/oracle_onset_beat.py`
42. `READ_IN_FULL` — `scripts/regression-harness/high_bin_alias_audit.py`
43. `READ_IN_FULL` — `scripts/regression-harness/k1_device_identity_guard.py`
44. `READ_IN_FULL` — `scripts/regression-harness/k1_paired_snappiness_capture.py`
45. `READ_IN_FULL` — `scripts/regression-harness/k1_stm_replay.py`
46. `READ_IN_FULL` — `scripts/regression-harness/mic_ab_compare.py`
47. `READ_IN_FULL` — `scripts/regression-harness/novelty_from_wav.py`
48. `READ_IN_FULL` — `scripts/regression-harness/palette_reference.py`
49. `READ_IN_FULL` — `scripts/regression-harness/render_via_nbconvert.py`
50. `READ_IN_FULL` — `scripts/regression-harness/serial_menu_odr_driver.cpp`
51. `READ_IN_FULL` — `scripts/regression-harness/spaces/lgp_animate.py`
52. `READ_IN_FULL` — `scripts/regression-harness/stm_k1_native_host.py`
53. `READ_IN_FULL` — `scripts/regression-harness/stubs/Ticker.h`
54. `READ_IN_FULL` — `scripts/regression-harness/tempo_replay.py`
55. `READ_IN_FULL` — `scripts/regression-harness/vp_capture.py`
56. `READ_IN_FULL` — `scripts/regression-harness/vpab_semantic_presentation.py`
57. `READ_IN_FULL` — `scripts/regression-harness/vpml_runtime_summary.py`
58. `READ_IN_FULL` — `scripts/setup_global_git.sh`
59. `READ_IN_FULL` — `tests/tab5_harness_spec/replay_dispatch.py`
60. `READ_IN_FULL` — `tests/test_beat_aware_director_static.py`
61. `READ_IN_FULL` — `tests/test_calibration_profile_static.py`
62. `READ_IN_FULL` — `tests/test_deck_identity_v1.py`
63. `READ_IN_FULL` — `tests/test_edgemixer_parity_native.py`
64. `READ_IN_FULL` — `tests/test_factory_tooling_static.py`
65. `READ_IN_FULL` — `tests/test_harness_selftest.py`
66. `READ_IN_FULL` — `tests/test_k1_av_regression_static.py`
67. `READ_IN_FULL` — `tests/test_k1_pin_evidence_parser.py`
68. `READ_IN_FULL` — `tests/test_k1_upload_guard.py`
69. `READ_IN_FULL` — `tests/test_mic_auto_sense_static.py`
70. `READ_IN_FULL` — `tests/test_nyquist_bin_hygiene_static.py`
71. `READ_IN_FULL` — `tests/test_phase345_runtime_proof.py`
72. `READ_IN_FULL` — `tests/test_serial_typed_dispatch_table_static.py`
73. `READ_IN_FULL` — `tests/test_smart_visuals_gate.py`
74. `READ_IN_FULL` — `tests/test_tab5_harness_transcript_replay.py`
75. `READ_IN_FULL` — `tests/test_vp_motion_lab_static.py`
76. `READ_IN_FULL` — `tests/test_vpml_live_runner.py`

## Exact read-only rerun commands

```bash
shasum -a 256 /tmp/k1-source-manifest.WdLSdO/chunk_4.txt
wc -l /tmp/k1-source-manifest.WdLSdO/chunk_4.txt
while IFS= read -r path; do
  test -f "$path" || printf 'MISSING %s\n' "$path"
done < /tmp/k1-source-manifest.WdLSdO/chunk_4.txt
```

The complete-read status above was produced by paginated full-file reads, not by grep-only inspection. The targeted `rg`/`nl` commands used after those reads were solely for relocating exact findings and line citations.
