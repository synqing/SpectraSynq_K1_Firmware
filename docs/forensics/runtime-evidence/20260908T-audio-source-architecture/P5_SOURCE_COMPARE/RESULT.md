# P5 — Line-In versus IM69 source comparison

Status: **MEASURED_ON_SILICON / P5 decision sufficient for P6**. Probe/research only.

## Fixture
Same 45 s deterministic WAV, SHA256 `2c561dacb4fbbd9dc3a4e071e8b5ec472f2cf3dc9f83d81ca89f21c18bd017d0`, routed through `Multi-Output Device` so LINE receives it electrically and IM69 receives it acoustically.

## Runtime timing
Admissible MIC baseline: 133.333 AP Hz, 44.444 novelty Hz, active AP mean 3549.2 us, p99 4640–4672 us, max 4785 us; no read/gap/core failures.

Admissible LINE baseline recovered from the retained compact-soak dump: 133.307 AP Hz, 44.439 novelty Hz, active AP mean 4083.1 us, p99 5248–5280 us, max 6596 us; zero I2S error, byte mismatch, frame gap, timestamp regression or core failure. The original serial status response lost rank 0; an immediate retained-status redump recovered all 16 worst rows without rerunning the measurement.

LINE cost versus MIC: +533.9 us mean and +608 us p99 (~13.1%). It remains below the 6 ms historical Gate-2 p99 CPU threshold at p99, though isolated max excursions exceed 6 ms and remain visible evidence.

PCM health during LINE: RX overflow 0, ring drop 0, acquisition == consumption ~47.99 kHz, SRC invariant PASS, ring high-water 1320 frames.

## Source-domain observation
The same programme's IM69 working-domain `max_raw` median was ~1121 (p95 ~2260) and fixed-point RMS median ~0.0153 (~501/32768). The unconditioned LINE stream commonly occupied ~0.58–2.04 M counts RMS in signed-24 telemetry, i.e. roughly 2.3–8.0 k counts after the existing 24->16 mapping, with programme peaks approaching the ADC's full-scale range.

Therefore unity Line-In mapping does not reproduce the microphone AP operating range. Candidate A (unity) is rejected. P6 will validate candidate B first: a fixed 1/16 canonical trim (`Q15=2048`, -24.08 dB) while preserving the untouched raw 48 kHz / 24-bit branch. Slow adaptive normalisation remains parked unless fixed trim proves inadequate across representative levels.

## Stereo ruling entering P6
Silicon mapping remains slot0=physical RIGHT, slot1=physical LEFT. A music-programme canonical source should not arbitrarily ship one channel. P6 candidate is physical MID `(L+R)/2`; raw stereo remains preserved. Hard anti-phase cancellation is an explicit edge case to evaluate, not a reason to silently reorder DMA packing.
