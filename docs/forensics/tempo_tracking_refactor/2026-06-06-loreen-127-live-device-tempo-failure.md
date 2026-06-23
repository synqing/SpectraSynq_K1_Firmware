---
abstract: "Forensic evidence packet for Loreen - My Heart Is Refusing Me, verified 127 BPM: live K1 AP_STREAM selected wrong tempos while the same source file replayed through host sb_tempo.cpp with production V2 flags settled correctly at 127 BPM. Separates source/selector behaviour from device front-end/state behaviour and records the remaining diagnostic gap: production serial surfaces do not expose the exact novelty ring consumed by sb_tempo."
---

# Loreen 127 BPM Live-Device Tempo Failure

## Scope

- [FACT] This memo records evidence only. No firmware was edited, flashed, calibrated, or committed for this packet.
- [FACT] Device serial identity was verified before live captures: `/dev/cu.usbmodem2101`, `USB VID:PID=303A:1001 SER=B4:3A:45:A5:87:F8 LOCATION=2-1`.
- [FACT] Source track supplied by Captain: `/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3`.
- [FACT] Source track SHA-256: `a62e1f095de9c3e06563b40d0842acf64ca1bf6fece341a15190cb1c11ab9b0f`.
- [FACT] Source track media facts from local `ffprobe`: MP3, 223.910023 s, 44100 Hz, stereo, bit rate 364373.
- [FACT] Captain identified the track as verified 127 BPM.

## Evidence 1: Live AP_STREAM Capture, Known 127 BPM

- [FACT] Capture start: 2026-06-06T00:00:37.
- [FACT] Duration requested/observed: 90.0 s / 90.045 s.
- [FACT] AP rows captured: 88.
- [FACT] Artefacts:
  - Raw log: `build/audio-semantic-metrics/apstream/known_127bpm_20260606_000037__raw.log`
  - AP log: `build/audio-semantic-metrics/apstream/known_127bpm_20260606_000037__device.aplog`
  - Metadata: `build/audio-semantic-metrics/apstream/known_127bpm_20260606_000037__meta.json`
  - Summary: `build/audio-semantic-metrics/apstream/known_127bpm_20260606_000037__summary.md`
- [FACT] BPM samples: n=88, min=87.000, median=87.000, mean=89.455, max=114.000.
- [FACT] BPM run sequence: 108 x1, 102 x4, 87 x15, 114 x5, 87 x63.
- [FACT] BPM count distribution: 87 x78, 114 x5, 102 x4, 108 x1.
- [FACT] Confidence samples: n=88, min=0.000, median=0.240, mean=0.384, max=0.990.
- [FACT] High-confidence rows, using conf >= 0.60: 29/88; all 29 reported 87 BPM.
- [FACT] Locked rows, using lock >= 0.5: 9/88; all 9 reported 87 BPM.
- [FACT] AP_STREAM sampled `beat=0` in every row.
- [INFERENCE] The all-zero sampled `beat` field does not prove no beat ticks occurred, because AP_STREAM is low-cadence relative to the beat stream.
- [INFERENCE] This is a live-device tempo-selection failure against the verified 127 BPM source: the device selected 87 BPM for most of the capture, including every high-confidence and locked AP_STREAM sample.

## Evidence 2: Host Replay of the Same Source File

- [FACT] MP3 was converted offline to the harness input format:
  - WAV: `build/audio-semantic-metrics/source-replay/Loreen-My-Heart-Is-Refusing-Me_12k8_mono.wav`
  - WAV SHA-256: `162d64932db95b763321ab53b1b25bc037a3d95767a9a446b0807205427a7d76`
  - WAV media facts: PCM s16le, 12800 Hz, mono, 223.910078 s.
- [FACT] Host novelty CSV: `build/audio-semantic-metrics/source-replay/Loreen-My-Heart-Is-Refusing-Me_12k8_mono.novelty.csv`, 29850 frames.
- [FACT] Host replay compiled the real `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp` with production tempo flags from `platformio.ini`: `SB_TEMPO_CONF_V2` and `SB_TEMPO_FLYWHEEL_V2`.
- [FACT] Host replay artefacts:
  - Summary JSON: `build/audio-semantic-metrics/source-replay/Loreen-My-Heart-Is-Refusing-Me_host_prodflags_summary.json`
  - Trajectory: `build/audio-semantic-metrics/source-replay/Loreen-My-Heart-Is-Refusing-Me_host_prodflags_trajectory.txt`
- [FACT] Full-file host replay: median BPM 127, settled mode BPM 127, lock fraction 0.923, high-confidence top BPM 127 x26052.
- [FACT] Full-file host replay ACF ceiling from the same novelty: 126.984126984127 BPM.
- [FACT] Every tested 90 s reset window settled to 127 BPM:
  - 0-90 s: host settled 127, final 127, conf 0.984, lock 1.
  - 15-105 s: host settled 127, final 127, conf 0.973, lock 1.
  - 30-120 s: host settled 127, final 127, conf 0.956, lock 1.
  - 45-135 s: host settled 127, final 127, conf 0.971, lock 1.
  - 60-150 s: host settled 127, final 98, conf 0.362, lock 0; settled mode still 127.
  - 75-165 s: host settled 127, final 127, conf 0.933, lock 1.
  - 90-180 s: host settled 127, final 127, conf 0.944, lock 1.
  - 105-195 s: host settled 127, final 127, conf 0.975, lock 1.
  - 120-210 s: host settled 127, final 127, conf 0.977, lock 1.
  - 133-223 s: host settled 127, final 127, conf 0.000, lock 0; settled mode still 127.
- [INFERENCE] The track file itself and the production `sb_tempo.cpp` selector are not sufficient to reproduce the 87 BPM live failure when fed the host-modelled spectral-flux novelty.
- [INFERENCE] The failure is therefore in one or more of: live acoustic input, I2S extraction/scaling, GDFT/AGC front-end, novelty generation from AGC-clamped spectrograms, or carried runtime state entering the capture.

## Evidence 3: Second Live AP + AGC Debug Capture

- [FACT] Capture start: 2026-06-06T00:14:37.
- [FACT] Duration requested/observed: 60.0 s / 60.177 s.
- [FACT] AP rows captured: 59. AGC debug rows captured: 52.
- [FACT] Artefacts:
  - Raw log: `build/audio-semantic-metrics/apstream/known_127bpm_agc_ap_20260606_001437__raw.log`
  - AP log: `build/audio-semantic-metrics/apstream/known_127bpm_agc_ap_20260606_001437__device.aplog`
  - AGC log: `build/audio-semantic-metrics/apstream/known_127bpm_agc_ap_20260606_001437__agc.log`
  - Summary JSON: `build/audio-semantic-metrics/apstream/known_127bpm_agc_ap_20260606_001437__summary.json`
- [FACT] AP BPM samples: n=59, min=68.000, median=101.000, mean=97.475, max=147.000.
- [FACT] AP BPM count distribution: 106 x11, 74 x8, 68 x7, 71 x6, 101 x5, 147 x5, 96 x5, 115 x4, 100 x3, plus singletons.
- [FACT] Locked BPM count distribution: 74 x8, 147 x4, 115 x4, 105 x1, 68 x1.
- [FACT] AP confidence samples: n=59, min=0.000, median=0.400, mean=0.423, max=0.800.
- [FACT] AP lock fraction over this capture: 0.305.
- [FACT] Peak-scaled samples: n=59, min=-0.044, median=0.382, mean=0.392, max=1.064.
- [FACT] AGC debug all-slot energy: n=208, min=0.010, median=0.045, mean=0.6975, max=14.080.
- [FACT] AGC debug all-slot gain: n=208, min=0.100, median=2.335, mean=3.063, max=9.960.
- [FACT] AGC debug floor field was constant 32768.0 across rows.
- [INFERENCE] The second live window did not remain pinned to 87 BPM; it wandered across multiple wrong lanes and locked on several of them. This supports a live device front-end/state instability diagnosis rather than a single clean source-file ambiguity.
- [INFERENCE] The AGC telemetry shows large gain/energy excursions during the wrong-tempo live window, but the current AGC debug surface is not sufficient to prove exact causality for the 87/74/147 selections.

## Source-Code Boundary

- [FACT] `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` calls `process_GDFT()`, then `calculate_novelty(t_now)`, then `sb_audio_snapshot_update(t_now)`, then `sb_tempo_update(sb_audio_snapshot)`.
- [FACT] `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp` sets `SBAudioSnapshot::novelty` from `novelty_curve[sb_previous_spectral_history_index()]`.
- [FACT] `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` computes `novelty_curve[...]` as `sqrtf(mean(max(0, spectrogram[i] - previous_spectrogram[i])))`.
- [FACT] The spectrogram feeding that novelty has already passed through broadband AGC and is clamped to `[0, 1]` in `process_GDFT()`.
- [FACT] The host replay novelty is `novelty_from_wav.py` dB spectral flux with drift removal and p99 scaling. It is a host-modelled front-end, not a bit-exact device GDFT/AGC novelty.
- [FACT] Production serial `[AP]` exposes tempo/onset plus waveform peak fields, but does not expose the exact novelty ring consumed by `sb_tempo`.
- [FACT] Production `ap_capture=<ms>` is compiled only under `ENABLE_AP_STREAM`; the current `k1_hardware` build flags do not define `ENABLE_AP_STREAM`.

## Evidence 4: Tempo-Probe Diagnostic Instrumentation

- [FACT] Added non-shippable diagnostic output behind the existing `ENABLE_TEMPO_STREAM` gate used by `k1_tempo_probe`.
- [FACT] Files touched:
  - `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.h`
  - `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp`
  - `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h`
- [FACT] New stream line: `TEMPO_DBG,...`.
- [FACT] New `TEMPO_DBG` fields include the decimated novelty sample (`nov`), scaled novelty (`nov_scaled`), novelty scale, winner/candidate bins, top-1/top-2 selection bins and scores, ACF validity, winner comb/point/prior/conf-score terms, and V2 confidence components.
- [FACT] Build verification:
  - `pio run -e k1_tempo_probe` passed.
  - `pio run -e k1_hardware` passed.
  - `strings .pio/build/k1_tempo_probe/firmware.elf | rg 'TEMPO_DBG|TEMPO,t='` found both `TEMPO,t=` and `TEMPO_DBG,t=`.
  - `strings .pio/build/k1_hardware/firmware.elf | rg 'TEMPO_DBG|TEMPO,t='` found no matches.
- [FACT] Therefore the diagnostic stream is present in the non-shippable probe build and absent from the production build.
- [FACT] Uploaded `k1_tempo_probe` to verified target `/dev/tty.usbmodem2101` after confirming USB serial `B4:3A:45:A5:87:F8`.

## Evidence 5: Immediate Post-Flash Probe Capture

- [FACT] Capture start: 2026-06-06T00:22:46.
- [FACT] Duration requested/observed: 75.0 s / 75.018 s.
- [FACT] Rows captured: raw 2798, `TEMPO` 1347, `TEMPO_DBG` 1346, `[AP]` 75.
- [FACT] Artefacts:
  - Raw log: `build/audio-semantic-metrics/tempo-probe/loreen_127_tempo_probe_20260606_002246__raw.log`
  - TEMPO log: `build/audio-semantic-metrics/tempo-probe/loreen_127_tempo_probe_20260606_002246__tempo.log`
  - TEMPO_DBG log: `build/audio-semantic-metrics/tempo-probe/loreen_127_tempo_probe_20260606_002246__tempo_dbg.log`
  - AP log: `build/audio-semantic-metrics/tempo-probe/loreen_127_tempo_probe_20260606_002246__ap.log`
  - Summary JSON: `build/audio-semantic-metrics/tempo-probe/loreen_127_tempo_probe_20260606_002246__summary.json`
- [FACT] `TEMPO` BPM samples: n=1347, min=0.000, median=96.000, mean=99.048, max=149.000.
- [FACT] `TEMPO` BPM count distribution: 96 x428, 94 x245, 95 x211, 97 x201, 124 x112, 98 x73, 110 x44, 149 x15, 108 x8, 77 x7.
- [FACT] `TEMPO_DBG` winner BPM count distribution: 96 x428, 94 x245, 95 x210, 97 x201, 124 x112, 98 x73, 110 x44, 149 x15, 108 x9, 77 x7.
- [FACT] `TEMPO_DBG` top-1 BPM count distribution: 96 x365, 95 x351, 97 x236, 94 x213, 110 x35, 122 x33, 124 x22, 98 x11, plus smaller counts.
- [FACT] `TEMPO_DBG` showed ACF valid on 1335/1346 rows.
- [FACT] `TEMPO_DBG` internal novelty-silence flag was true on 825/1346 rows, while `[AP]` `silence` was 0 on all 75 AP rows.
- [FACT] `[AP]` BPM samples in the same capture: n=75, min=94.000, median=96.000, mean=99.720, max=149.000.
- [INFERENCE] This post-flash probe capture proves the diagnostic stream works and can expose the selector surface.
- [INFERENCE] This capture cannot be treated as a clean reproduction of the original Loreen 127 BPM failure unless the track start/section is re-controlled after the probe upload.
- [INFERENCE] Within this capture, the wrong published BPM is not only output hysteresis: the live top selection surface itself is dominated by ~94-97 BPM rather than 127 BPM.
- [INFERENCE] The disagreement between `TEMPO_DBG` internal novelty-silence and AP `silence` points at a novelty-contrast/front-end problem worth testing on a clean restart.

## Evidence 6: Controlled Restart Tempo-Probe Capture

- [FACT] Captain restarted the verified 127 BPM track immediately before this capture.
- [FACT] Capture start: 2026-06-06T00:28:06.
- [FACT] Duration requested/observed: 105.0 s / 105.011 s.
- [FACT] Rows captured: raw 3912, `TEMPO` 1890, `TEMPO_DBG` 1889, `[AP]` 103.
- [FACT] Artefacts:
  - Raw log: `build/audio-semantic-metrics/tempo-probe/loreen_127_restarted_tempo_probe_20260606_002806__raw.log`
  - TEMPO log: `build/audio-semantic-metrics/tempo-probe/loreen_127_restarted_tempo_probe_20260606_002806__tempo.log`
  - TEMPO_DBG log: `build/audio-semantic-metrics/tempo-probe/loreen_127_restarted_tempo_probe_20260606_002806__tempo_dbg.log`
  - AP log: `build/audio-semantic-metrics/tempo-probe/loreen_127_restarted_tempo_probe_20260606_002806__ap.log`
  - Summary JSON: `build/audio-semantic-metrics/tempo-probe/loreen_127_restarted_tempo_probe_20260606_002806__summary.json`
- [FACT] Full capture `TEMPO` BPM samples: n=1890, min=0.000, median=96.000, mean=96.645, max=143.000.
- [FACT] Full capture `TEMPO` BPM count distribution: 96 x940, 95 x588, 84 x87, 143 x58, 80 x52, 120 x49, 82 x39, 113 x27, 121 x16.
- [FACT] Warm section, after 15 s, `TEMPO` BPM count distribution: 96 x940, 95 x424, 84 x87, 80 x52, 120 x49, 82 x39, 113 x27, 121 x16.
- [FACT] Warm section, after 15 s, `TEMPO_DBG` winner BPM count distribution: 96 x940, 95 x423, 84 x87, 80 x52, 120 x49, 82 x39, 113 x27, 121 x16.
- [FACT] Warm section, after 15 s, `TEMPO_DBG` top-1 BPM count distribution: 96 x667, 95 x608, 80 x53, 84 x50, 98 x49, 120 x44, 113 x37, 121 x32, 123 x29.
- [FACT] Warm section, after 15 s, `TEMPO_DBG` top-2 BPM count distribution: 96 x544, 95 x481, 97 x149, 94 x129, 80 x47, 112 x44, 98 x41, 120 x40, 121 x34, 122 x31.
- [FACT] Near-127 row counts, using rounded 124-130 BPM inclusive:
  - `TEMPO` published BPM: 0/1890; warm rows: 0/1634.
  - `TEMPO_DBG` winner BPM: 0/1889; warm rows: 0/1633.
  - `TEMPO_DBG` top-1 BPM: 0/1889; warm rows: 0/1633.
  - `TEMPO_DBG` top-2 BPM: 2/1889; warm rows: 2/1633.
- [FACT] In 15 s segments, the stream settled mostly as follows:
  - 0-15 s: `TEMPO` top counts 95 x164, 143 x58, 72 x11, 77 x10.
  - 15-30 s: 96 x59, 95 x53, 80 x52, 120 x49.
  - 30-45 s: 96 x273.
  - 45-60 s: 96 x273.
  - 60-75 s: 96 x158, 84 x87, 113 x27.
  - 75-90 s: 96 x177, 95 x98.
  - 90-105 s: 95 x272.
- [FACT] `TEMPO_DBG` ACF validity after 15 s was 1.0 across all warm debug rows.
- [FACT] `TEMPO_DBG` internal novelty-silence after 15 s was true on 977/1633 rows, while AP `silence` remained 0 across AP rows.
- [INFERENCE] This controlled restart reproduces the failure under the diagnostic stream: the device selector surface never seriously presents 127 BPM as the winner/top-1 lane.
- [INFERENCE] The failure is upstream of consumer/effect interpretation and not merely AP_STREAM sampling: the internal tempo selection surface itself is dominated by wrong lanes.
- [INFERENCE] Because `top1_sel` is the post-prior selection score, this capture does not yet prove whether the raw ACF at 127 is absent or whether the prior/comb score suppresses it below 95/96. It does prove the existing selection signal entering winner choice is wrong on device.

## Evidence 7: Agent-Triggered Raw-ACF Probe Capture

- [FACT] Added one more non-shippable `TEMPO_DBG` field set, compiled only under `ENABLE_TEMPO_STREAM`:
  - Raw top comb bin/BPM/score: `top_comb`, `top_comb_bpm`, `top_comb_score`.
  - Raw top point bin/BPM/score: `top_point`, `top_point_bpm`, `top_point_score`.
  - Fixed-lane raw comb values: `comb95`, `comb96`, `comb120`, `comb123`, `comb127`.
  - Fixed-lane raw point values: `point95`, `point96`, `point120`, `point123`, `point127`.
  - Fixed-lane selection prior values: `prior95`, `prior96`, `prior120`, `prior123`, `prior127`.
- [FACT] Rebuild/leak check after adding those fields:
  - `pio run -e k1_tempo_probe` passed.
  - `pio run -e k1_hardware` passed.
  - `strings .pio/build/k1_tempo_probe/firmware.elf | rg 'TEMPO_DBG|TEMPO,t='` found both `TEMPO,t=` and `TEMPO_DBG,t=`.
  - `strings .pio/build/k1_hardware/firmware.elf | rg 'TEMPO_DBG|TEMPO,t='` found no matches.
- [FACT] Uploaded `k1_tempo_probe` to `/dev/tty.usbmodem2101` after confirming `/dev/cu.usbmodem2101` exposed USB serial `B4:3A:45:A5:87:F8`.
- [FACT] Capture start/end: 2026-06-06T00:38:16 / 2026-06-06T00:40:12.
- [FACT] Duration requested: 115.0 s.
- [FACT] Playback was agent-triggered with `/usr/bin/afplay /Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3` immediately after AP streaming was enabled.
- [FACT] Capture caveat: the script used the Mac default audio output path; concurrent room playback, if present, was not controlled by this script.
- [FACT] Rows captured after corrected AP parser: raw 4279, `TEMPO` 2069, `TEMPO_DBG` 2068, `[AP]` 113.
- [FACT] Artefacts:
  - Raw log: `build/audio-semantic-metrics/tempo-probe/loreen_127_agentplay_rawacf_tempo_probe_20260606_003816__raw.log`
  - TEMPO log: `build/audio-semantic-metrics/tempo-probe/loreen_127_agentplay_rawacf_tempo_probe_20260606_003816__tempo.log`
  - TEMPO_DBG log: `build/audio-semantic-metrics/tempo-probe/loreen_127_agentplay_rawacf_tempo_probe_20260606_003816__tempo_dbg.log`
  - AP log: `build/audio-semantic-metrics/tempo-probe/loreen_127_agentplay_rawacf_tempo_probe_20260606_003816__ap.log`
  - Summary JSON: `build/audio-semantic-metrics/tempo-probe/loreen_127_agentplay_rawacf_tempo_probe_20260606_003816__summary.json`
- [FACT] Warm section, after 15 s, `TEMPO` BPM count distribution: 107 x571, 106 x327, 108 x281, 105 x230, 89 x171, 87 x151, 133 x36, 120 x29.
- [FACT] `[AP]` BPM count distribution: 107 x31, 106 x18, 108 x16, 120 x15, 105 x13, 89 x9, 87 x8, 133 x2, 155 x1.
- [FACT] Warm section, after 15 s, raw top-comb BPM count distribution: 107 x587, 106 x384, 105 x181, 108 x166, 131 x88, 132 x74, 133 x72, 141 x54, 134 x35, 130 x34.
- [FACT] Warm section, after 15 s, raw top-point BPM count distribution: 106 x501, 107 x450, 140 x172, 66 x114, 64 x104, 108 x80, 144 x60, 65 x52, 145 x42, 143 x42.
- [FACT] Near-127 row counts, using rounded 124-130 BPM inclusive:
  - `TEMPO` published BPM: 0/2069; warm rows: 0/1796.
  - `TEMPO_DBG` winner BPM after warm-up: 0/1795.
  - `TEMPO_DBG` top-1 BPM after warm-up: 0/1795.
  - `TEMPO_DBG` top-2 BPM after warm-up: 2/1795.
  - Raw top-comb BPM after warm-up: 34/1795.
  - Raw top-point BPM after warm-up: 0/1795.
- [FACT] Warm fixed-lane medians:
  - Comb: `comb95` 0.1779, `comb96` 0.2109, `comb120` 0.1980, `comb123` 0.1804, `comb127` 0.2753.
  - Point: `point95` 0.1019, `point96` 0.1519, `point120` 0.1863, `point123` 0.0665, `point127` 0.0611.
  - Prior: `prior95` 0.9892, `prior96` 0.9861, `prior120` 0.8370, `prior123` 0.8127, `prior127` 0.7796.
- [FACT] Warm median ratios:
  - `comb127 / comb96` = 1.327.
  - `comb127 / comb95` = 1.508.
  - `comb127 / comb120` = 1.501.
  - `point127 / point96` = 0.604.
  - `point127 / point120` = 0.782.
- [FACT] Among only the fixed lanes 95/96/120/123/127, the per-row `comb * prior` selection product after warm-up chose 127 on 887/1795 rows, 96 on 572/1795, 95 on 213/1795, 120 on 102/1795, and 123 on 21/1795.
- [FACT] Segment medians show `point127` was initially high, then collapsed late in the capture:
  - 0-15 s: `comb127` median 0.9224, `point127` median 0.9543.
  - 15-30 s: `comb127` median 0.5136, `point127` median 0.5737.
  - 30-45 s: `comb127` median 0.4955, `point127` median 0.2314.
  - 45-60 s: `comb127` median 0.2049, `point127` median 0.0291.
  - 75-120 s: `point127` median 0.0 in each logged segment.
- [INFERENCE] This agent-triggered run is not the exact same acoustic condition as Captain's controlled restart; it produced a dominant 105-108 BPM wrong lane rather than the earlier 95/96 lane.
- [INFERENCE] It still reproduces the load-bearing failure: a verified 127 BPM source produces zero near-127 published/winner/top-1 rows after warm-up on the live device.
- [INFERENCE] The raw 127 comb lane is not simply absent. Within the suspect fixed lanes, `comb127 * prior127` wins nearly half the warm rows despite the lower 127 prior.
- [INFERENCE] The live selector is instead being beaten by stronger global raw comb/point lanes around 105-108 and related high/low periodicities, while the 127 point ACF weakens or collapses as the track continues.
- [INFERENCE] Therefore the current evidence does not support a blind "lower the 88/96 prior" fix. The bottleneck is device-front-end novelty and raw ACF semantics, plus how the comb/point split feeds global winner selection.

## Conclusion

- [FACT] The same verified 127 BPM source file replays to 127 BPM through host `sb_tempo.cpp` with production tempo flags.
- [FACT] The live K1 selected wrong tempos on that source, including a 90 s capture dominated by high-confidence/locked 87 BPM.
- [FACT] The controlled restart tempo-probe capture shows the live selection surface dominated by 95/96 BPM, with zero near-127 winner/top-1 rows after warm-up.
- [FACT] The agent-triggered raw-ACF capture shows another wrong selection mode, dominated by 105-108 BPM, again with zero near-127 published/winner/top-1 rows after warm-up.
- [FACT] In that raw-ACF capture, the fixed `comb127` lane is stronger than 95/96/120 by median, but the global raw top-comb/top-point lanes remain dominated by wrong periods.
- [INFERENCE] The next bottleneck is device-front-end novelty plus raw ACF/selection semantics, not another confidence-metric adjustment.
- [INFERENCE] A fix should not tune the tactus prior blindly from AP_STREAM alone. The immediate missing evidence is why the device novelty stream produces stronger global 105-108/95-96 periodicities than the host replay of the same source.

## Next Diagnostic Action

- [FACT] The non-shippable diagnostic build now streams the decimated `sb_tempo` novelty sample plus winner-bin, top competing bins, and selection/confidence scores.
- [FACT] A clean restart capture of the verified 127 BPM source under `k1_tempo_probe` reproduced the wrong selection surface.
- [FACT] The raw-ACF field set now exists and is captured in `loreen_127_agentplay_rawacf_tempo_probe_20260606_003816`.
- [HYPOTHESIS] Next non-shippable diagnostic should compare the live device novelty stream itself against the host novelty stream for the same playback section, before any winner tuning. The goal is to determine whether the wrong 105-108/95-96 periodicities enter at GDFT/AGC/novelty generation or inside the ACF/selector stage.
- [HYPOTHESIS] If live novelty already carries dominant wrong periodicities while host novelty does not, the fix lane is front-end novelty quality.
- [HYPOTHESIS] If live novelty resembles host novelty but raw ACF still favours wrong global bins, the fix lane is ACF lag band/comb normalisation/global selector semantics.
- [FACT] Any such diagnostic build is non-shippable instrumentation and must stay out of `k1_hardware` production flags.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-06-06 | agent:Codex | Created from live AP_STREAM captures, host replay of the exact MP3, and source cross-check of the novelty path. |
| 2026-06-06 | agent:Codex | Added non-shippable `TEMPO_DBG` instrumentation evidence and immediate post-flash probe capture, with clean-track-start caveat. |
| 2026-06-06 | agent:Codex | Added controlled restart tempo-probe capture showing wrong internal selection surface: 95/96 dominant, zero near-127 winner/top-1 rows after warm-up. |
| 2026-06-06 | agent:Codex | Added raw-ACF agent-triggered playback capture: wrong 105-108 global selection, fixed 127 comb lane present, 127 point ACF collapses late. |
