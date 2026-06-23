# K1 Mode 18 VPAB Music Capture - Semantic Brief

Date: 2026-06-07

## Evidence Boundary

This is audio-conditioned visual evidence, not a reconstruction of the raw music signal.
The capture proves framed VPAB transport integrity, mode 18 primary/secondary coverage,
actual final LED-byte payload availability, and timing health during live music.

It does not prove raw PCM content, named-track repeatability, full AudioSemanticState
tempo/chord history, or current-vs-VME final-byte equivalence.

## Runtime Transport Result

- Gate result: `PASS`
- Records/chunks: `44` / `176`
- Issues/failures: `0` / `0`
- Dropped/corrupt/overflowed: `0` / `0` / `0`
- Coverage: mode `[18]`, channels `['primary', 'secondary']`, kinds `['vpab_bytes', 'vpab_metrics']`

## Runtime Timing

- Frame avg/max: `3975us / 5552us`
- Frame budget: `8333us`
- Over/dropped frames: `0` / `0`
- Heap: `191520`

## Channel Semantics From Final Bytes

| Channel | Samples | Mean energy | Peak energy | Active LEDs | Mean centre | Mean centre distance | Saturation | White bias |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | 11 | 243 | 1,434 | 31.1% | 79.0 | 0.7 | 79.0 | 0.4 |
| secondary | 11 | 2,415 | 5,692 | 42.0% | 79.5 | 0.1 | 92.7 | 14.4 |

## Interpretation

Mode 18 was driven by live programme material while Smart Scene and AP/VP text
streams were disabled. The audio pipeline remains the upstream cause of visual
state, but the evidence captured here sits at the visual-pipeline boundary:
final channel bytes after rendering and quantisation, plus timing counters.

The significance for K1 is that the proof transport now reaches the perceptual
surface rather than survivor CSV rows. It can show whether the visual result is
energetic, spatially moving, colour-saturated, balanced between channels, and
inside timing budget. The next VME L1 step is to put candidate VME bytes beside
these canonical bytes and compare them at this same boundary.

## Source Ledger

- Gate summary: `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.frame-gate.json`
- Raw capture log: `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.raw.log`
- Framed records: `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.frames.log`
- Payload schema: `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.h`
- Payload producer: `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp`
- Lane closeout: `docs/forensics/vme_l1/2026-06-07-vpab-framed-transport-ready.md`

## Generated Outputs

- HTML presentation: `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-presentation.html` (dark scalar colour-map heatmaps plus animated final-byte waterfall)
- Semantic summary JSON: `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.semantic-summary.json`
