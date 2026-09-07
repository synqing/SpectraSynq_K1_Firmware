---
abstract: "P3 partial. Route PASS. DMA0=physical RIGHT, DMA1=physical LEFT. Quiet ~2400 RMS (~−71 dBFS) at a ~−42.6 dBFS test tone. Crosstalk UNRESOLVED/NOISE-FLOOR-LIMITED (upper bound only). THD/FR pending timed raw 24-bit capture."
---

# P3 — Line-In characterisation (partial)

Label: **END_TO_END_LINE_LANE_METRIC** (Mac + cable + PCM module + S3). Not intrinsic PCM1808 silicon.

Output device for this run: **External Headphones** (not Multi-Output Device). Spotify paused. Quiet guards accepted.

## Route

`P3_ROUTE_PROOF.json` — 997 Hz both, guarded WAV.

| Window | rmsL | rmsR |
|---|---:|---:|
| quiet1 | 2395 | 2413 |
| stim | 55716 | 55933 |
| quiet2 | 5767 | 5843 |

stim/quiet1 = 23.2. **PASS.**

## Channel map — MEASURED_ON_SILICON

`P3_CHANNEL_MAP.json`

| Fixture | rms DMA0 (`rmsL`) | rms DMA1 (`rmsR`) |
|---|---:|---:|
| silence | 2304 | 2321 |
| Mac LEFT 997 Hz | 2379 | **62518** |
| Mac RIGHT 1499 Hz | **66266** | 1977 |
| Mac L+R | 62105 | 62365 |

Encode in source, do **not** swap DMA packing:

- `K1_PCM_SLOT0_PHYSICAL_RIGHT` — firmware slot 0 = physical RIGHT
- `K1_PCM_SLOT1_PHYSICAL_LEFT` — firmware slot 1 = physical LEFT
- Policy later: `LINE_LEFT → slot 1`, `LINE_RIGHT → slot 0`, `LINE_MID → (slot1+slot0)/2`

Probe default `s_channel=0` still follows **physical RIGHT**. That is not a LINE_LEFT decision.

## Noise — MEASURED_ON_SILICON (end-to-end), not SNR

Quiet RMS ≈ 2400 / 8388607 ≈ **−71 dBFS**.

The 997 Hz tone that mapped the channels was only ≈ 62500 / 8388607 ≈ **−42.6 dBFS RMS**. Signal-over-floor in that run was ~28–30 dB. This is not the ADC’s usable SNR. Drive level must be established with the amplitude staircase before THD/SINAD/FR.

## Crosstalk — UNRESOLVED / NOISE-FLOOR-LIMITED

Inactive slot on left-only ≈ 2379, on right-only ≈ 1977 — **indistinguishable from the ~2400 quiet baseline**.

This experiment establishes only an **upper bound** at the tested level:

- ≤ −28.4 dB (L stimulus)
- ≤ −30.5 dB (R stimulus)

True separation could be much better. Re-measure after a higher clean stimulus (a few dB below measured ADC clipping) and a timed raw capture. Do **not** report crosstalk = −28 / −30 dB.

## Not yet measured (need fixture-aligned 48 kHz snapshot)

THD, THD+N, SINAD, ENOB, sweep 20 Hz–20 kHz, phase, IM products, staircase linearity, impulse. PCMSNAP today dumps once at boot, not during a fixture.

No Line-In conditioning constant is frozen.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | Crosstalk reclassified NOISE-FLOOR-LIMITED; tone was only −42.6 dBFS. |
| 2026-09-08 | agent:grok | Route + L/R map + noise/crosstalk from exclusive External Headphones. |
