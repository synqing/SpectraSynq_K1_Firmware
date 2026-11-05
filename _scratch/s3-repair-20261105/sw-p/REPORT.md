# 1. Changed artefacts
- `4234aa2d` — `effects/light_mode_waveform_hybrid_k1.cpp`: silence gates new dots; existing outward history drains.
- `cc987e12` — `audio/k1_audio_input_state.h`, `effects/light_mode_waveform_fast.cpp`, `effects/light_mode_waveform_hybrid.cpp`, `audio/i2s_audio.h`, existing `tests/test_audio_input_correctness.py`: line-specific presence and normalised VU subtraction; saved microphone calibration unchanged.
- `f67f2b73` — existing trace counters expose line peak, floor, dwell age and silence result.
- `92f76c87` — line silence uses integer hop energy; sparse spikes no longer independently restart dwell.
- `62d93cca` — final line floor13 canonical counts, from measured lit post-stop signed24 peak39247 + RMS8033, converted through trim2048/32768 and24-to16 scaling plus rounding. Original dark-only RMS404/peak2263 implied floor2, but did not bound lit idle.
Firmware paths above are relative to `SPECTRASYNQ_K1_FIRMWARE/`. No producer, AGC, GDFT, tracker, globals or platform flags edited by P. Root integrated final tested image36607a8f.

# 2. Gates run
Full command arguments for independent final gate: `final-expected-gate.json`. Focused commands and all exits: `gates.json`.
| Gate | Command | Exit | Receipt |
|---|---|---|---|
| Initial mode32 static | `python3 -m pytest tests/test_waveform_hybrid_k1_static.py -q` |0|`section6-host.log`|
| Initial source/waveform focused | pytest six files listed in gates.json |0,29passed|`section7-host.log`|
| Approach1 nine windows | root existing line-presence capture |1|main `presence-line/result.json`|
| Normal APDBG availability | existing `:apdbg=on` | unavailable, Bad command |main `presence-line32-apdbg.txt`|
| Trace-only host | existing input + mode32 tests |0,11passed|`p2-trace-host.log`|
| Energy regression before fix | `python3 -m pytest tests/test_audio_input_correctness.py -k line_silence -q` |1|`p2-energy-red.log`|
| Energy focused after fix | pytest six files |0,29passed|`p2-energy-green.log`|
| Approach2 nine windows | root existing line-presence capture |1|main `presence-energy/result.json`|
| Measured-idle regression before floor13 | same focused line-silence test |1|`p3-floor-red.log`|
| Final floor focused | pytest six files |0,29passed|`p3-floor-green.log`|
| Approach3 nine windows | root existing capture |0|main `presence-final/result.json`|
| Microphone mode32 | root existing capture |0|main `mic-final/result.json`|
| Independent raw CRC/count/spec comparison | Python command verbatim in receipt JSON |0|`final-expected-gate.json`, `.log`|
| VU rendered mode | disabled product mode10; not re-enabled |OPEN|source `config_types.h`|
| Exact one-hop wake /1.5s silence-to-black timing | windows do not measure these exact transitions |OPEN|capture scope|

The independent final comparison reads original expected-result.md, checks its pre-recorded SHA256 fe577a11e8f2e1b41309c4541abc83b755981122a969687e41fd36a27de03375, decodes every raw RGB8 frame, recalculates CRC and lit counts, checks quiet=0/music>0 and extracts the original mode7/mode11 improvement thresholds from that file. It also checks source/settings restoration. No hand-written PASS.

# 3. Measured numbers
Final silicon preamble: B489; `k1_fe_bench_b489_trace_dev`; git36607a8f;240MHz; root `effective-build-flags.json`; firmware SHA2565454f9eb853c8f501fd1a06c752c4286e23b221d399e5e5e3199dc305d4a3369. These are measured RGB8 presence counts, not optical or cadence qualification.
|Source/mode|Quiet before lit/frames|Music lit/frames|Quiet after lit/frames|
|---|---:|---:|---:|
|Line7|0/94|89/89|0/95|
|Line11|0/95|84/84|0/95|
|Line32|0/90|83/83|0/90|
|Microphone32|0/92|81/84|0/92|
Mode7 and11 both exceed their original1/99 and27/99 music baselines. Mode11 is Waveform Hybrid, not disabled Quantum Collapse6. VU10 and VU_DOT4 remain disabled.

Failure history retained: approach1 mode32 quiet-after84/84lit; approach2 mode32 quiet-after82/82lit. Successful modes7/11 stayed quiet-dark in both attempts. First decision trace243hops: silencefalse229/true14, peaks1..7 at floor2. Second decision trace241hops: allsilencefalse, quiet age maximum915ms, below1000ms. Readback JSONs independently hash and summarise original traces. The classifier, not the corrected history drain, prevented sustained darkness. No fourth approach attempted.

# 4. Not verified
- Rendered VU output remains OPEN because existing product selection disables both VU modes. Source subtraction is changed and host checks pass; no claim of rendered VU or per-hop VU telemetry proof.
- Exact music return within one hop and exact1.5s silence-edge-to-black are not measured by settled windows. Source supports immediate above-floor energy wake and exact-zero outward history flush, but arithmetic is not a hardware latency measurement.
- Microphone regression capture covers mode32 only. Its calibration and source classifier remain unchanged; this is not all-mode microphone qualification.
- No candidate optical, musical-style, all-level line-input or broader noise qualification. Root owns final normal build, complete suite, final28-mode capture and settings restoration.
- Sections6/7 presence-window gates succeed; full stated acceptance retains the VU/transition timing OPEN boundaries above.

# 5. Open decisions for Captain
None. Root can finish the authorised final normal build and record the bounded OPEN checks without re-enabling removed modes or inventing latency evidence.
