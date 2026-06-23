# 2026-06-06 AP0/VP1 Implementation Handover

For: next implementation session with fresh context  
From: K1 tempo/NOV cadence forensic lane  
Classification: load-bearing handover for AP/VP scheduling and cadence guard work  
Scope: backstory, evidence, traps, lessons, and next implementation target  
Status: no production promotion yet

## One-Line Mission

Implement a candidate runtime rule that keeps the audio/AP pipeline off the VP/render core, add a runtime cadence drift guard, and validate click plus Loreen from clean boot without tuning tempo, prior, confidence, AGC, GDFT, BPM range, or Loreen-specific logic.

## Read First

Read these before touching source:

```text
.claude/CLAUDE.md
docs/forensics/tempo_tracking_refactor/2026-06-06-loreen-ap0-vp1-corrected-cadence.md
docs/forensics/tempo_tracking_refactor/2026-06-06-ap-cadence-probe-implementation.md
docs/forensics/tempo_tracking_refactor/2026-06-06-tempo-nov-cadence-contract-verdict.md
platformio.ini
SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
```

Important doctrine:

```text
- Verify device identity before serial/upload/device-write.
- Never auto-run calibration commands.
- Developer probes are non-shippable.
- Compile success is not runtime proof.
- Do not revert unrelated dirty-tree work.
```

## Backstory

The AP forward-graft had already reached host-green status, but real-device testing exposed a reproducible tempo selection failure. A verified `127 BPM` source could be reported near the low lanes, and a later simple `127 BPM` click control collapsed into the `87-89 BPM` region.

Early suspicion split across several plausible causes:

```text
1. replay harness semantics bug
2. wrong accepted-NOV cadence / time-base contract
3. front-end novelty corruption from mic/I2S/GDFT/AGC/clamp
4. tempo selector / prior / ACF semantics
5. mixed failure
```

The critical discipline was to avoid tuning the tracker. The work had to prove what `sb_tempo_update()` was actually receiving and at what cadence.

## Evidence Ladder

### 1. Host clean-file replay was not the territory

[FACT] Host clean-file replay of the Loreen source could settle at `127 BPM`. This proved the source file contains enough 127 BPM evidence and that the production tempo core can lock 127 when fed a clean host-modelled novelty stream.

[INFERENCE] That result did not prove the live K1 physical path preserves the same evidence after speaker, room, mic, I2S, GDFT, AGC, clamp, and novelty formation.

Lesson:

```text
Host clean-file success is a ceiling, not live-device proof.
```

### 2. Initial live AP/tempo surfaces were visibly wrong

[FACT] Live K1 telemetry on Loreen showed low lanes such as `87`, `96`, and adjacent values while the verified source was `127 BPM`.

[FACT] AP stream was too low-rate to prove beat truth by itself.

[INFERENCE] The issue was not just a display sampling artefact because higher-rate tempo/NOV captures also showed the wrong lanes.

Lesson:

```text
AP_STREAM is a coarse observer. Use buffered NOV/APCAD and replay for causal claims.
```

### 3. NOV-only click control exposed the cadence signature

[FACT] A simple `127 BPM` click control captured through the live K1 NOV path replayed to `87-89 BPM` at the hardcoded `44.444 Hz` accepted-NOV contract.

[FACT] The same NOV sequence replayed near `126-128 BPM` when interpreted at the measured accepted-NOV rate of about `32.048 Hz`.

[INFERENCE] The click NOV sequence contained 127 BPM evidence. The failure was cadence/time-base interpretation, not absence of 127-periodic novelty.

Key arithmetic:

```text
actual accepted-NOV rate ~= 32.048 Hz
tempo code assumed       = 44.444 Hz
scale                    = 44.444 / 32.048 ~= 1.387
127 * 1.387              ~= 176 BPM
176 / 2                  ~= 88 BPM half-time alias
```

Lesson:

```text
If the novelty sample rate is wrong, every Goertzel/ACF tempo label is wrong.
```

### 4. Replay harness was cleared as Mode B

[FACT] `device_novelty_replay.py` expands each accepted NOV row into reconstructed AP-frame rows before calling real `sb_tempo_update()`. It is Mode B: AP-frame reconstruction.

[FACT] It is not the forbidden Mode C path where accepted NOV rows are accidentally fed through the `/3` decimator again as if they were AP frames.

Lesson:

```text
Replay semantics were not the main bug after Mode B was proven.
```

### 5. APCAD proved the old `~32 Hz` symptom was real under one runtime map

[FACT] A bounded AP cadence/config/read-health probe measured the current source contract:

```text
active config: 12800 / 96
expected AP:  133.333 Hz
expected NOV:  44.444 Hz
```

[FACT] In the bad runtime placement, the device measured about:

```text
AP:  ~94.99-96.24 Hz
NOV: ~31.67-32.08 Hz
```

[FACT] I2S status and bytes read were clean in those captures.

[INFERENCE] The original diagnosis became "AP loop/cadence overrun under the observed runtime placement", not a tempo selector bug.

Lesson:

```text
Clean I2S status plus full bytes read does not prove the AP cadence contract is satisfied.
```

### 6. Live timing matrix isolated AP/VP core contention

[FACT] The decisive matrix compared the same timing map with different core placement:

| Run | Map | Cores | AP Hz | NOV Hz | Click replay |
| --- | --- | --- | ---: | ---: | --- |
| A | `12.8k / 96 /3`, DMA `3` | AP1 / VP1 | `96.238` | `32.079` | `87-88 BPM` |
| A2 | `12.8k / 96 /3`, DMA `3` | AP0 / VP1 | `133.311` | `44.447` | `126 BPM` |

[INFERENCE] The click-control failure was primarily same-core AP/VP contention/interference. The current `12.8k / 96 /3` map was not dead; it was failing under the wrong scheduling/core map.

Lesson:

```text
Do not demote a timing map before isolating task placement.
```

### 7. The 100 Hz maps passed click but are not the immediate next move

[FACT] Two 100 Hz AP candidates also passed click cadence/replay under AP0/VP1:

| Map | AP Hz | NOV Hz | Click replay |
| --- | ---: | ---: | --- |
| `12.8k / 128 /2` | `100.040` | `50.007` | dominant `126`, near-127 `1000 / 1000` |
| `16k / 160 /2` | `100.027` | `50.003` | dominant `126`, near-127 `1000 / 1000` |

[INFERENCE] They remain useful candidates, but running Loreen on them first would have confounded core isolation with sample-rate/chunk/decimation changes.

Lesson:

```text
Change one causal variable at a time.
```

### 8. Loreen AP0/VP1 closed the key question

[FACT] First Loreen APCAD attempt after flashing AP0/VP1 was invalid because runtime config still persisted from the prior `16k / 160` probe:

```text
active config: 16000 / 160 / 3
classification: A_persisted_runtime_config_drift
```

[FACT] Runtime config was reset to `12800 / 96`, then valid Loreen APCAD measured:

```text
AP:  133.378 Hz
NOV:  44.444 Hz
AP core: 0
VP core: 1
I2S status: clean
byte mismatches: 0
```

[FACT] The 120 second Loreen buffered NOV capture replayed at the declared `44.444 Hz` contract:

| Replay | Warm median BPM | Warm near-127 rows | Locked near-127 rows |
| --- | ---: | ---: | ---: |
| raw NOV | `127` | `11745 / 14000` | `3438` |
| scaled NOV | `127` | `11592 / 14000` | `1479` |

[INFERENCE] Loreen is no longer a failing exemplar under the corrected AP0/VP1 timing contract.

Lesson:

```text
The front-end was not proven innocent globally, but this Loreen failure was cadence contamination, not proof of destroyed 127 BPM novelty.
```

## Issues We Faced

### Runtime config drift

The device can persist `sample_rate` and `samples_per_chunk` across probe runs. A binary named for `12800 / 96` can still run with persisted `16000 / 160` until explicitly reset.

Implementation lesson:

```text
Do not trust env names or source defaults. Capture active runtime config in every proof packet.
```

### Same-core AP/VP contention

The old failure was reproduced when AP and VP both ran on Core 1. AP0/VP1 restored the source cadence on the same `12.8k / 96 /3` map.

Implementation lesson:

```text
AP and VP must not share the same core in candidate runtime builds.
```

### Misleading classifier labels

The old APCAD classifier emitted `D_probe_export_timestamp_bug` when APCAD matched the source contract but older NOV-only captures did not. That label implied a proven timestamp/export bug. It was corrected to:

```text
D_legacy_nov_capture_not_comparable
```

Implementation lesson:

```text
Labels must describe what is proven, not a convenient suspected seam.
```

### `total_us` was not pure compute

`total_ap_loop_elapsed_us` includes I2S wait/polling dynamics. It fails strict p95 budget gates even in runs that sustain correct AP/NOV cadence and replay correctly.

Implementation lesson:

```text
Split wait time from compute time before using total wall interval as a reject gate.
```

### Replay warm-up bug

The first matrix run used a 15 second replay warm-up on 15 second captures, leaving no useful warm replay rows. The matrix runner was corrected to use a 5 second replay warm-up for those short click controls.

Implementation lesson:

```text
Short fixtures need a scoring window that leaves post-warm-up data.
```

### C++ float literal bug in replay harness

The replay harness once emitted `100f`, which is not a valid C++ float literal. It was corrected to emit `100.0f`.

Implementation lesson:

```text
Harness compile details matter. A bad test binary can poison a good diagnostic plan.
```

### Environment naming smell

Some prepared 100 Hz matrix variants originally carried stale `d3` names while their declared maps were `/2`. This was cleaned before live use.

Implementation lesson:

```text
Build env names, compile defines, and runtime APCAD declarations must agree before flashing.
```

### Audio playback contamination risk

At one point multiple audio playback sources were suspected. Later capture scripts checked for `afplay`/capture process overlap and used controlled `afplay` playback of the fixture.

Implementation lesson:

```text
Verify no stray playback process before any acoustic capture.
```

### Hardware identity and port drift

The main K1 moved across port names during the session. The verified main target for the latest run was:

```text
/dev/cu.usbmodem1401
SER: B4:3A:45:A5:87:F8
```

Other boards were visible:

```text
/dev/cu.usbmodem12201 SER=B4:3A:45:A5:89:B4
/dev/cu.usbmodem12401 SER=F0:F5:BD:75:A7:FC
```

Implementation lesson:

```text
Never upload or send device-write commands based on port number alone.
```

## Current Relevant Source/Tooling State

[FACT] Probe envs in `platformio.ini` currently include:

```text
k1_ap_frontend_probe_matrix_12800_96_d3
k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1
k1_ap_frontend_probe_matrix_12800_128_d2
k1_ap_frontend_probe_matrix_12800_128_d2_ap0_vp1
k1_ap_frontend_probe_matrix_16000_160_d2
k1_ap_frontend_probe_matrix_16000_160_d2_ap0_vp1
```

[FACT] AP0/VP1 probe envs set:

```text
ARDUINO_RUNNING_CORE=0
SB_LED_TASK_CORE=1
```

[FACT] Relevant AP/VP instrumentation seams:

```text
SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
  - SB_LED_TASK_CORE default
  - xTaskCreatePinnedToCore(... SB_LED_TASK_CORE)
  - APCAD ap_core_id via xPortGetCoreID()
  - APCAD vp_core_id from LED task

SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h
  - APCAD buffered structs
  - APCAD dump fields: ap_core, vp_core, tempo_decim, decl_ap_hz, decl_nov_hz

scripts/regression-harness/device_ap_cadence_capture.py
  - capture/classify AP cadence/read-health packets
  - current comparable-cadence label: D_legacy_nov_capture_not_comparable

scripts/regression-harness/device_ap_cadence_matrix.py
  - live click matrix runner

scripts/regression-harness/device_novelty_replay.py
  - Mode B accepted-NOV replay via AP-frame reconstruction
```

## Implementation Target

Build the smallest candidate implementation that makes the AP0/VP1 rule and cadence guard explicit without changing DSP behaviour.

Required behaviour:

```text
1. AP audio/Arduino loop candidate runs on Core 0.
2. VP/render LED task runs on Core 1.
3. Runtime telemetry reports declared AP Hz, declared NOV Hz, measured AP/NOV cadence, AP core, VP core.
4. Runtime cadence drift guard flags when measured AP/NOV cadence departs from declared contract.
5. Guard is diagnostic/telemetry first. Do not auto-tune tempo constants from wall time.
```

Guard stance:

```text
FAIL or WARN if measured AP/NOV cadence drifts more than 1-2% from declared contract over a bounded window.
Do not silently compensate the tempo coefficients from measured wall cadence.
Do not mask AP starvation by making the tempo map chase an overloaded runtime.
```

Candidate threshold:

```text
AP rate within 1-2% of declared AP rate
NOV rate within 1-2% of declared NOV rate
AP core observed as 0
VP core observed as 1
I2S status clean
bytes_read stable
click declared-rate replay locks 126-128
Loreen declared-rate replay locks near 127
```

## Explicit Non-Goals

Do not:

```text
- tune SB_TACTUS_BPM
- tune confidence thresholds
- widen BPM range
- change AGC/GDFT/novelty constants
- add Loreen-specific handling
- use measured wall cadence as a tempo coefficient patch
- promote 16k/160 or 12.8k/128 before AP0/VP1 current-map clean-boot gates
- run calibration
- flash the bench K1 unless Captain explicitly redirects target identity
```

## Verification Plan For The Next Session

Host checks:

```bash
python3 -m py_compile scripts/regression-harness/device_ap_cadence_capture.py scripts/regression-harness/device_ap_cadence_matrix.py scripts/regression-harness/device_novelty_replay.py scripts/regression-harness/tempo_replay.py
python3 -m pytest tests/test_rate_consistency.py -q
python3 -m pytest tests/test_dev_instrumentation_boundary.py -q
pio run -e k1_hardware
```

If firmware/platformio changed, also run the relevant probe build:

```bash
pio run -e k1_ap_frontend_probe_matrix_12800_96_d3_ap0_vp1
```

Device gate, only after verifying target identity:

```text
target: main K1 only
expected identity: SER=B4:3A:45:A5:87:F8
recent port: /dev/cu.usbmodem1401
```

Clean-boot validation sequence:

```text
1. flash candidate build to verified main K1
2. reset/confirm runtime config is 12800 / 96
3. run 10-15 s 127 BPM click APCAD/capture/replay
4. run Loreen APCAD proof
5. run 120 s Loreen buffered NOV capture
6. replay raw and scaled NOV at declared 44.444 Hz
7. record AP core, VP core, AP/NOV cadence, I2S status, byte stability, near-127 rows, locked near-127 rows
```

## Fresh-Session Starter Prompt

Use this to start the next session:

```text
Implement AP0/VP1 candidate runtime rule plus cadence drift guard for K1.

Start by reading:
- .claude/CLAUDE.md
- docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-implementation-handover.md
- docs/forensics/tempo_tracking_refactor/2026-06-06-loreen-ap0-vp1-corrected-cadence.md
- docs/forensics/tempo_tracking_refactor/2026-06-06-ap-cadence-probe-implementation.md
- platformio.ini
- SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
- SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h

Known result:
- AP1/VP1 same-core reproduced ~96 Hz AP / ~32 Hz NOV and 87-88 BPM.
- AP0/VP1 restored 12.8k / 96 /3 to ~133 Hz AP / ~44 Hz NOV.
- 127 BPM click locks near 126 under AP0/VP1.
- Loreen AP0/VP1 declared-rate NOV replay locks 127.

Task:
- Encode AP0/VP1 as the candidate runtime rule.
- Add runtime cadence drift guard/telemetry.
- Preserve production DSP constants.
- Validate host gates.
- If main K1 is available, verify identity and run click plus Loreen clean-boot gates.

Hard constraints:
- no calibration command
- no tempo/prior/confidence/AGC/GDFT/BPM-range tuning
- no Loreen-specific logic
- no bench K1 unless explicitly redirected
- no promotion claim until clean-boot device gates pass
```

## Final Lesson

The failure looked like a tempo-selection or front-end-quality problem because BPM is where the symptom was visible. It was actually a scheduling/time-base contract problem. The next implementation must protect the timing contract first; only then is it meaningful to judge front-end novelty quality or selector behaviour on real music.
