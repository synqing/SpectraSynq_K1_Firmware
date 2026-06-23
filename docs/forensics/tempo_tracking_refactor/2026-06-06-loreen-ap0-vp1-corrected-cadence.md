# 2026-06-06 Loreen AP0/VP1 Corrected-Cadence Run

## Verdict

[FACT] Loreen was rerun on the main K1 at `/dev/cu.usbmodem1401` with the corrected current timing map:

```text
sample_rate: 12800
samples_per_chunk: 96
tempo_decimation: 3
AP core: 0
VP core: 1
DMA desc: 3
declared AP rate: 133.333 Hz
declared accepted NOV rate: 44.444 Hz
```

[FACT] The corrected APCAD proof measured `133.378 Hz` AP cadence and `44.444 Hz` accepted-NOV cadence, with clean I2S status and stable byte reads.

[FACT] The 120 second Loreen buffered NOV capture replayed at the declared `44.444 Hz` contract locks near the verified `127 BPM` tempo.

[INFERENCE] For this Loreen fixture, AP0/VP1 core isolation resolves the cadence contamination that previously pushed the device NOV/replay evidence into the low-tempo lanes. The remaining result is not a front-end impossibility: the corrected device novelty contains enough 127 BPM evidence for the production tempo core to lock under declared-rate replay.

[INFERENCE] This does not promote AP0/VP1 to production by itself. It promotes the next engineering rule to test and encode: AP and VP must not share the same core, and production must expose a runtime cadence drift guard.

## Source Fixture

[FACT] Track used:

```text
build/audio-semantic-metrics/ad_hoc_corpus/loreen_my_heart_is_refusing_me_12k8.wav
sha256: 162d64932db95b763321ab53b1b25bc037a3d95767a9a446b0807205427a7d76
```

[FACT] Main K1 serial identity:

```text
port: /dev/cu.usbmodem1401
USB VID:PID=303A:1001
SER: B4:3A:45:A5:87:F8
LOCATION: 0-1.4
```

[FACT] Non-target boards were visible but not used:

```text
/dev/cu.usbmodem12201 SER=B4:3A:45:A5:89:B4
/dev/cu.usbmodem12401 SER=F0:F5:BD:75:A7:FC
```

## Invalid First Loreen APCAD Attempt

[FACT] The first APCAD Loreen attempt after flashing AP0/VP1 was invalid because the runtime config was still persisted from the prior `16k / 160` probe:

```text
artifact: build/audio-semantic-metrics/device-ap-cadence-capture/loreen_ap0vp1_apcad_20260606_213640__summary.json
classification: A_persisted_runtime_config_drift
active config: 16000 / 160 / 3
measured AP rate: 99.987 Hz
measured NOV rate: 33.340 Hz
AP core: 0
VP core: 1
```

[FACT] The runtime config was then reset to `12800 / 96` before the valid Loreen run.

## Valid APCAD Proof

[FACT] Valid APCAD artifact:

```text
build/audio-semantic-metrics/device-ap-cadence-capture/loreen_ap0vp1_12800_96_apcad_20260606_213755__summary.json
```

[FACT] The same raw APCAD log was reclassified after the classifier wording fix:

```text
build/audio-semantic-metrics/device-ap-cadence-capture/loreen_ap0vp1_12800_96_apcad_reclassified_20260606_214703__summary.json
classification: D_legacy_nov_capture_not_comparable
```

| Field | Value |
| --- | ---: |
| active sample rate | `12800` |
| active samples per chunk | `96` |
| active tempo decimation | `3` |
| declared AP rate from binary | `133.33203 Hz` |
| declared NOV rate from binary | `44.44531 Hz` |
| expected AP rate from active config | `133.333333 Hz` |
| measured AP rate | `133.377793 Hz` |
| expected NOV rate from active config | `44.444444 Hz` |
| measured NOV rate | `44.444444 Hz` |
| AP core IDs | `[0]` |
| VP core IDs | `[1]` |
| DMA desc | `[3]` |
| DMA frame | `[96]` |
| I2S status counts | `{0: 2001}` |
| I2S not-OK count | `0` |
| byte mismatch count | `0` |
| frame gaps | `0` |
| timestamp regressions | `0` |

[FACT] Timing fields from the same capture:

| Stage | Median | p95 | Max |
| --- | ---: | ---: | ---: |
| frame dt | `5 ms` | `14 ms` | `15 ms` |
| accepted NOV dt | `23 ms` | `25 ms` | `26 ms` |
| I2S read | `33 us` | `3768 us` | `5286 us` |
| GDFT | `3220 us` | `3519 us` | `3561 us` |
| novelty | `33 us` | `54 us` | `75 us` |
| total AP loop packet interval | `4963 us` | `13842 us` | `15102 us` |

[INFERENCE] `total_ap_loop_elapsed_us` is still a mixed wall interval that includes I2S wait/polling dynamics. It must not be used as a pure compute reject gate until the packet splits wait time from compute-only AP work. The cadence and replay result are the higher-authority facts for this run.

## Buffered NOV Capture

[FACT] Buffered NOV artifact stem:

```text
build/audio-semantic-metrics/device-nov-capture-buffered/loreen_ap0vp1_12800_96_nov_buffered_20260606_214043
```

[FACT] Capture summary:

```text
duration requested: 120000 ms
duration observed: 120000 ms
NOV rows: 5333
source mode: buffer
actions: nov_clear=1, apdbg=off, tempo_stream=off, ap_stream=off, nov_capture=120000, nov_dump=1, afplay playback
non-actions: no device firmware constant tuning, no calibration command
```

[FACT] NOV audit from declared-rate replay:

| Field | Value |
| --- | ---: |
| replay injection mode | `B_AP_FRAME_RECONSTRUCTION` |
| accepted NOV rate used | `44.444444444 Hz` |
| AP frame Hz used | `133.333333333 Hz` |
| reconstruction decimation | `3` |
| measured accepted NOV rate | `44.444074 Hz` |
| row count | `5333` |
| duration | `119971 ms` |
| cadence median | `22 ms` |
| cadence p5 | `20 ms` |
| cadence p95 | `25 ms` |
| cadence max | `27 ms` |
| emit gaps | `0` |
| timestamp regressions | `0` |
| large dt count | `0` |

## Declared-Rate Replay Matrix

[FACT] Raw NOV replay artifact:

```text
build/audio-semantic-metrics/device-nov-capture-buffered/loreen_ap0vp1_12800_96_nov_buffered_20260606_214043__declared_44p444_replay.json
```

[FACT] Scaled NOV replay artifact:

```text
build/audio-semantic-metrics/device-nov-capture-buffered/loreen_ap0vp1_12800_96_nov_buffered_20260606_214043__declared_44p444_scaled_replay.json
```

| Replay | Input | Rate used | Injection | Warm median BPM | Warm near-127 rows | High-conf near-127 | Locked near-127 | Warm locked rows | Warm beat ticks |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| declared-rate raw | `nov` | `44.444 Hz` | Mode B | `127` | `11745 / 14000` | `1380` | `3438` | `4150` | `75` |
| declared-rate scaled | `nov_scaled` | `44.444 Hz` | Mode B | `127` | `11592 / 14000` | `402` | `1479` | `2101` | `49` |

[FACT] Raw warm BPM counts:

```text
127: 11745
119: 864
85: 391
155: 234
114: 231
64: 129
79: 132
87: 112
120: 93
112: 69
```

[FACT] Scaled warm BPM counts:

```text
127: 10713
126: 879
118: 792
85: 370
155: 354
112: 375
79: 201
80: 129
81: 112
64: 75
```

## Comparison Against Prior Loreen Failure

[FACT] Prior non-isolated Loreen baseline:

```text
artifact stem: build/audio-semantic-metrics/device-nov-capture-buffered/loreen_fixed_novonly_nov_buffered_20260606_035751
row_count: 3902
duration_ms: 119999
measured NOV rate: 32.5086 Hz
cadence median: 31 ms
emit gaps: 0
timestamp regressions: 0
large dt count: 0
```

[FACT] Prior declared-rate replay results:

| Prior replay | Warm median BPM | Warm near-127 rows | High-or-locked near-127 | Locked near-127 |
| --- | ---: | ---: | ---: | ---: |
| old raw NOV | `84` | `165 / 10227` | `0 / 123` | `0 / 123` |
| old scaled NOV | `112` | `0 / 10227` | `0 / 81` | `0 / 81` |

[FACT] Prior measured-rate forensic replay moved Loreen upward but still did not lock confidently:

```text
warm median: 123 BPM
warm near-127 rows: 1719 / 10227
high-confidence/locked near-127: 0
```

[INFERENCE] The old Loreen result should be treated as stale/non-isolated AP1/VP1-era evidence, not as proof of a front-end novelty-quality failure under the corrected AP0/VP1 runtime contract.

## Root-Cause Classification

[INFERENCE] For the 127 BPM click-control and this Loreen fixture, the dominant proven failure mode is:

```text
same-core AP/VP contention/interference caused accepted-NOV cadence drift,
which corrupted tempo interpretation downstream.
```

[INFERENCE] The corrected Loreen run does not support the stronger claim that the device front-end necessarily destroys 127 BPM evidence. Under AP0/VP1, the device-captured Loreen novelty replays to a strong 127 BPM lock at the declared rate.

[HYPOTHESIS] Real-music front-end/selector quality may still need broader corpus testing after AP0/VP1 is encoded, but Loreen is no longer a failing exemplar under the corrected timing contract.

## Next Action

One highest-information next step:

```text
Encode AP0/VP1 as a non-production candidate rule with a runtime cadence drift guard,
then rerun the 127 BPM click and Loreen gates from a clean boot on that build.
```

Do not tune tempo, tactus prior, confidence, AGC, GDFT, BPM range, or Loreen-specific logic from this run.
