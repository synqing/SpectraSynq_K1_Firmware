# K1 Tempo/NOV Cadence Contract Verdict

Date: 2026-06-06

Scope: replay semantics, accepted-NOV cadence, and 127 BPM control replay. No production DSP tuning.

Supersession note:

This document captured the NOV-only cadence-mismatch symptom before the AP cadence matrix existed. The later APCAD matrix supersedes its root-cause classification: the fixed NOV-only captures showed `~32 Hz` accepted-NOV cadence, but did not isolate config drift, AP frame cadence, I2S wait, export artefact, or AP/VP core contention. The matrix later directly measured AP cadence and isolated same-core AP1/VP1 contention/interference as the click-control failure mode; AP0/VP1 restores the same `12.8k / 96 /3` source contract.

## 1. Replay-Semantics Verdict

Verdict: **Mode B - AP-frame reconstruction before `sb_tempo_update()`**.

Evidence:

- `scripts/regression-harness/device_novelty_replay.py` parses `NOV,` rows, prefers `src=buf` rows when present, and dedupes by `emit` (`parse_nov_rows`, lines 63-90).
- `rows_to_ap_frame_stdin()` expands each accepted NOV row into three AP-frame stdin rows: two quiet frames plus the captured novelty sample on the third frame (`device_novelty_replay.py`, lines 180-204).
- `scripts/regression-harness/tempo_replay.py` reads each stdin AP frame and calls the real host-compiled `sb_tempo_update()` once per AP frame (`tempo_replay.py`, lines 282-290).
- The host compiler path still compiles `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp` by default; the new `tempo_source` hook is harness-only and used only for measured-rate experiments (`tempo_replay.py`, lines 417-454).
- Firmware decimation remains inside `sb_tempo_update()`: `SB_NOVELTY_DECIMATION = 3U`, return on non-emit frames, emit on the third frame (`sb_tempo.cpp`, lines 22-24 and 1171-1200).

Timing preservation:

- The accepted sample timestamp is preserved as `emit_ms = int(row["t"])` on the third reconstructed AP frame.
- The two prior AP frames are synthetic fixed-offset frames at `AP_FRAME_MS = 7.5 ms`.
- `monotonic_ms()` can nudge overlapping timestamps by `+1 ms`, so exact sub-frame spacing for synthetic preframes is not authoritative. The accepted-row device timestamp remains the cadence evidence.

Conclusion: replay is not the forbidden Mode C re-decimation bug. It is a valid AP-frame reconstruction replay, but the default replay still uses the firmware's hardcoded 44.444 Hz accepted-NOV coefficient contract.

## 2. Cadence-Contract Verdict

Verdict: **FAIL - accepted-NOV cadence in the fixed buffered captures materially differs from the source contract.**

Source contract:

- `DEFAULT_SAMPLE_RATE` is `12800` in `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h` line 36.
- Factory `CONFIG` sets `SAMPLE_RATE = DEFAULT_SAMPLE_RATE` and `SAMPLES_PER_CHUNK = 96` in `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp` lines 57 and 64.
- I2S uses `CONFIG.SAMPLES_PER_CHUNK` for DMA frame count and read size, and `CONFIG.SAMPLE_RATE` for clock config (`i2s_audio.h`, lines 62-84 and 133-136).
- `sb_tempo.cpp` assumes `SB_AP_FRAME_HZ = 12800 / 96 = 133.333 Hz`, `SB_NOVELTY_DECIMATION = 3`, and `SB_NOVELTY_RATE_HZ = 44.444 Hz` (`sb_tempo.cpp`, lines 14-24).

Runtime-config caveat:

- `sample_rate` and `samples_per_chunk` are runtime-settable serial commands that persist and reboot (`serial_menu.h`, lines 2781-2799 and 3085-3099).
- The fixed NOV capture logs include `VERSION: 40103` and NOV status, but they do not include a config dump. Therefore the persisted live `CONFIG.SAMPLE_RATE` and `CONFIG.SAMPLES_PER_CHUNK` during capture are not directly proven from the capture log.

Capture/export throttle check:

- The buffered sample stores `sample.t_ms = td.last_emit_ms` and `sample.emit_count = td.emit_count` at capture time (`serial_menu.h`, lines 81-89 and 466-490).
- Dumping later prints the stored timestamp and emit count with `src=buf` (`serial_menu.h`, lines 493-522).
- The replay parser used only buffer rows, with `ignored_non_buffer_rows=0`.

Therefore serial dump/export throttling does **not** explain the 31 ms cadence. The timestamps are stored device emit timestamps.

Measured accepted-NOV cadence:

| Capture | Rows | Duration ms | Median dt | p5 dt | p95 dt | Measured accepted-NOV rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| control127 fixed NOV-only | 2243 | 69957 | 31.0 ms | 29.0 ms | 33.0 ms | 32.048 Hz |
| Loreen fixed NOV-only | 3902 | 119999 | 31.0 ms | 28.0 ms | 33.0 ms | 32.509 Hz |

Expected from source contract:

| Quantity | Expected |
| --- | ---: |
| AP frame rate | 133.333 Hz |
| AP frame dt | 7.5 ms |
| Accepted NOV rate | 44.444 Hz |
| Accepted NOV dt | 22.5 ms |

Measured AP frame rate:

- Not directly measured by these NOV-only captures.
- If the firmware is truly emitting every third AP frame, the accepted-NOV rates imply AP rates of about 96.145 Hz for control127 and 97.526 Hz for Loreen.
- That is an inference from accepted emits, not a direct AP-frame measurement.

## 3. 127 Control Replay Matrix

Input: `build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__nov_dump.log`

| Replay | Input | Rate used | Injection mode | Median BPM | Near-127 rows | Lock near-127 | Verdict |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| hardcoded-rate | control127 NOV | 44.444 Hz | Mode B | 88 | 0 / 5291 warm | 0 / 5194 locked | Reproduces wrong 87-89 lane |
| measured-rate | control127 NOV | 32.048 Hz | Mode B | 128 | 5291 / 5291 warm | 5194 / 5194 locked | Recovers 126-128 lane |

Artefacts:

- Hardcoded summary: `build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__forensic_hardcoded_44p444.json`
- Measured-rate summary: `build/audio-semantic-metrics/device-nov-capture-buffered/control127_fixed_novonly_nov_buffered_20260606_041307__forensic_measured_32p048.json`

Secondary Loreen check:

- Hardcoded-rate Loreen replay remains wrong/unstable, warm median 84 BPM.
- Measured-rate Loreen replay moves upward to warm median 123 BPM, with 1719 near-127 warm rows, but zero high-confidence or locked rows.
- This supports cadence as a major causal factor while leaving a second music/front-end/selector-quality problem open for Loreen.
- Later AP0/VP1 Loreen recapture supersedes this concern for this fixture: declared-rate raw NOV replay has warm median 127 BPM, 11745 / 14000 warm near-127 rows, and 3438 locked near-127 rows.

## 4. Root-Cause Classification

Historical classification before APCAD matrix: **E. mixed failure overall**.

Superseding live-matrix classification for click-control: **same-core AP/VP contention/interference**.

Breakdown:

- For the simple 127 BPM click-control failure, the old NOV-only capture proved a cadence-mismatch symptom, not an invalid source contract. Live matrix result: AP1/VP1 violates the current map at `~96 Hz` AP / `~32 Hz` NOV / `87-88 BPM`; AP0/VP1 satisfies the same map at `~133 Hz` AP / `~44 Hz` NOV / `126 BPM`.
- The replay harness is **not invalid** on injection semantics. It is Mode B.
- The control captured novelty does **not** genuinely lack 127 evidence. It contains enough 127-periodic evidence once the coefficient rate matches the measured accepted-NOV cadence.
- For Loreen, the old measured-rate replay improved the lane but did not produce a confident lock. Later AP0/VP1 recapture showed this was stale/non-isolated evidence for this fixture.

## 5. Next Action

Superseded. Do not add another generic cadence probe for click-control.

Rerun click-control and Loreen from clean boot after AP0/VP1 is encoded as the candidate runtime rule with a cadence drift guard. Do not tune tempo, prior, confidence, AGC, GDFT, BPM range, or Loreen-specific logic from this historical NOV-only verdict.
