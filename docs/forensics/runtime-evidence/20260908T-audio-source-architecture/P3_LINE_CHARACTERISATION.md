---
abstract: "P3 closed enough for architecture. Route PASS. DMA0=physical RIGHT. VOL=56 peak-linear to digital 1.0. VOL=100 digital FS reaches −0.8 dBFS peak without ADC clip. 997 Hz H2/H3 ≈ −79/−81 dB. Crosstalk still noise-floor-limited, bound now ≤ −51/−56 dB. FR not done."
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

## Amplitude staircase — MEASURED_ON_SILICON (VOL=56, External Headphones)

`P3_STAIRCASE/P3_AMPLITUDE_STAIRCASE.json` — 997 Hz both, PID-owned `afplay`, pre/post quiet guards, timed signed-24 from the capture task. Label **END_TO_END_LINE_LANE_METRIC**.

| Digital amp | peak slot0 (RIGHT) | peak vs 0.20 | RMS dBFS | clip samples |
|---:|---:|---:|---:|---:|
| 0.20 | 249706 | 0.00 dB | −34.0 | 0 |
| 0.40 | 496437 | −0.05 dB | −28.1 | 0 |
| 0.60 | 742986 | −0.07 dB | −24.5 | 0 |
| 0.80 | 987266 | −0.10 dB | −22.0 | 0 |
| 1.00 | 1230508 | −0.13 dB | −21.4 | 0 |

Peak tracks digital amplitude through 1.0. ADC clipping **not reached**. Headroom to signed-24 FS ≈ **16.7 dB peak**. Subsequent sines should use this physical setup (External Headphones, recorded volume) and a higher Mac volume until clip onset is seen; do not treat fixture “−18 dBFS” as the operating point.

Quiet floor in the same captures ≈ 1.7k–2.0k RMS. Fill deltas: ovf=0, ring_drop=0. Lifetime ring_drop still climbs during hex dump because dump runs on the serial/AP core; that is a dump artefact, not a lost capture.

## Mac volume extension — MEASURED_ON_SILICON (digital amp 1.0)

| Mac volume | peak slot0 | RMS dBFS | clip samples |
|---:|---:|---:|---:|
| 56 | 1 230 508 | −21.4 | 0 |
| 80 | 3 536 401 | −10.6 | 0 |
| 100 | 7 643 706 | −4.34 | 0 |

Peak 7.64e6 / 8.39e6 ≈ **−0.81 dBFS**. ADC clipping **still not reached** on this Mac + cable + module path at max output volume. This is the highest clean level this fixture can produce. Subsequent line characterisation used VOL=100.

## Quiet PSD at VOL=100 setup (no stimulus)

RMS ≈ 2080, DC ≈ 193 counts, 50 Hz bin small, 60 Hz bin small, spectral peak at 1 Hz. Not a 50/60 Hz dominated floor.

## 997 Hz THD — END_TO_END_LINE_LANE_METRIC

At VOL=100, digital FS, peak ≈ 7.65e6:

- H2 ≈ −79.5 dB
- H3 ≈ −81.2 dB
- THD (H2…H7) ≈ −76.7 dB

A naive all-bin THD+N/SINAD (2.6 dB) is **rejected** — it sums every FFT bin of noise against one fundamental bin and is not a SINAD. Residual SINAD was not closed (1 s dump still lost hex to non-PCMRAW serial). Harmonic THD is the number that answers the architectural question: this line path is not the distortion limiter.

## Crosstalk at high clean level — still NOISE-FLOOR-LIMITED

VOL=100, digital FS:

| Stimulus | active RMS | inactive RMS | bound |
|---|---:|---:|---|
| Mac LEFT | slot1 681 194 | slot0 1 893 | ≤ −51.1 dB |
| Mac RIGHT | slot0 679 079 | slot1 1 024 | ≤ −56.4 dB |

Inactive slots remain at the quiet floor. True isolation may be much better. Bound improved from ≤ −28/−30 dB because the active level is ~20 dB higher, not because we resolved leakage.

## Frequency response

Not measured. Not required to close the architectural questions (lossless ingress, drive headroom, channel map, floor-limited isolation). Do not FR from coarse RMS telemetry. Log-sweep/deconvolution remains optional before product claims.

No Line-In conditioning constant is frozen.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-08 | agent:grok | VOL=100 near-FS, THD ~−77 dB, crosstalk bound ≤ −51/−56 dB still floor-limited. FR not done. |
| 2026-09-08 | agent:grok | Amplitude staircase VOL=56: peak-linear to digital 1.0, ADC clip not reached, 16.7 dB peak headroom. |
| 2026-09-08 | agent:grok | Crosstalk reclassified NOISE-FLOOR-LIMITED; tone was only −42.6 dBFS. |
| 2026-09-08 | agent:grok | Route + L/R map + noise/crosstalk from exclusive External Headphones. |
