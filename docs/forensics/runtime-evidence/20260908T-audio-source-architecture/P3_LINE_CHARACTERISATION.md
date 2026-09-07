---
abstract: "P3 partial 2026-09-08. Mac External Headphones → PCM1808 route PASS. DMA slot 0 = physical RIGHT, slot 1 = physical LEFT. Noise floor ~2400 RMS (~−71 dBFS). Crosstalk ~28–30 dB. All END_TO_END_LINE_LANE_METRIC. THD/FR/SINAD UNMEASURED until a fixture-aligned raw 48k dump exists. No Line conditioner frozen."
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

**DMA slot 0 (first 24-bit sample) = physical RIGHT**  
**DMA slot 1 (second 24-bit sample) = physical LEFT**

Probe default mono `s_channel=0` therefore follows **physical RIGHT**. Do not ship that as “left”.

## Noise — MEASURED_ON_SILICON (end-to-end)

Quiet RMS ≈ 2400 on signed-24 ≈ −71 dBFS. Repeatable across silence and pre-tone guards. DC/PSD/mains spurs **UNMEASURED** (need raw dump).

## Crosstalk — MEASURED_ON_SILICON (end-to-end)

Left-only: idle slot / active ≈ 2379/62518 → **−28.4 dB**  
Right-only: 1977/66266 → **−30.5 dB**

## Not yet measured (need fixture-aligned 48 kHz snapshot)

THD, THD+N, SINAD, ENOB, sweep 20 Hz–20 kHz, phase, IM products, staircase linearity, impulse. PCMSNAP today dumps once at boot, not during a fixture.

No Line-In conditioning constant is frozen.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | Route + L/R map + noise/crosstalk from exclusive External Headphones. |
