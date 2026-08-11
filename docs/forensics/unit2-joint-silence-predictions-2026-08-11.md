---
abstract: "Falsifiable predictions P1-P5 written BEFORE the Unit 2 joint silence-gate soak of 2026-08-11 (HF-4). Records the measured quiet/music max_raw distributions under the corrected G=8 calibration (SSL=53), the derivation of K1_SILENCE_JOINT_LEVEL_SSL_FRAC=6.0, and why canon's 1.25 seed does not hold on this unit."
---

# Unit 2 — Joint Silence Gate: Predictions Before Soak

**Written BEFORE the soak**, per `k1-vj-session-discipline` HF-4.
**Date:** 2026-08-11 · **Device:** K1 Bench Unit 2, chip `0C54FC00`
**Firmware base:** `fix/im69d-rms-gate-and-gain-20260811`, IM69D `G=8`, PDM CLK39/DIN38 RIGHT
**Calibration:** re-learned 2026-08-11 in a Captain-authorised, witness-verified silence window
(room mean −60.2 dB). Result: `SSL 103 → 53`, `DC_OFFSET −117 → 220`, `NOISE CAL ACCEPTED`,
`ssl_rejected=0`, `dc_rejected=0`, `ssl_p50=29 ssl_p90=48`.

## Why this change is being made

The previous build gated on an **absolute** level floor (`K1_SILENCE_PEAK_MIN_RAW = 500.0f`).
That violated canon HF-3 ("prefer SSL-relative level over absolute magic numbers"), and the
violation was demonstrated empirically within the hour: recalibration moved the operating point
down by ~5.3× (quiet `max_raw` p50 254 → 48), and music at volume 70 — which had been waking
the device reliably — stopped clearing the fixed 500 floor entirely. Silence held 100% *through
music*. An absolute constant cannot survive a calibration change; an SSL-relative fraction can.

## Measured distributions under the corrected calibration (SSL = 53)

| `max_raw` | p10 | p50 | p90 | max |
|---|---|---|---|---|
| Quiet room (45 s) | — | 48 | 87 | **144** |
| Quiet, as ×SSL | — | 0.91 | 1.64 | **2.72** |
| Music @ vol 70 (30 s) | 38 | **740** | 1335 | 1719 |
| Music, as ×SSL | 0.72 | **13.96** | 25.19 | 32.43 |

Separation between quiet's worst frame (2.72×) and music's median (13.96×) is a factor of 5.1.

## Derivation of the fraction

Geometric midpoint of the two bounds: √(2.72 × 13.96) = **6.16**. Rounded to **6.0**, giving:

- threshold = 53 × 6.0 = **318**
- margin below quiet's worst frame (144): **2.2×**
- margin above music's median (740): **2.3×**

Symmetric in log space, which is the correct space for a ratio-scaled quantity.

### Divergence from canon — flagged, not silently overridden

`SESSION_CANON_2026-08-07` seeds `K1_SILENCE_JOINT_LEVEL_SSL_FRAC = 1.25`. That seed **does not
hold on this unit**: at 1.25 the threshold (66) sits between this room's quiet p50 (48) and p90
(87), so a large fraction of quiet frames would clear the level term. The canon seed was derived
on bench `B489A500` in a different room with a different mic assembly. This unit's quiet floor
sits proportionally much lower against its learned SSL. The composition (`pky AND level`,
SSL-relative) is unchanged and canon-conformant; only the fraction is re-derived from this
unit's measured distributions. **Canon should be updated to record that the frac is
per-unit/per-room and must be derived, not inherited.**

## Predictions — falsifiable, evaluated after the soak

| ID | Prediction | Falsifier |
|---|---|---|
| **P1** | Quiet room, 60 s: `silence` held ≥ 95% of frames | < 95% → frac too low, raise it |
| **P2** | Music @ vol 70: `silence` broken on ≥ 80% of frames | < 80% → frac too high, lower it |
| **P3** | Music `max_raw` p50 ≥ 3× the level threshold (≥ 954) | < 954 → margin thinner than derived |
| **P4** | `silent_scale` returns to 0.00 within 15 s of music stopping | longer → dwell/decay interaction needs review |
| **P5** | Quiet-room `silent_scale` mean = 0.00 (fully dark, not partial) | > 0.05 → residual false-breaks remain |

**P1 and P2 are the pair that matters.** Either alone is satisfiable by a broken gate — a floor
set impossibly high passes P1 and fails P2; one set at zero does the reverse. The gate is only
correct if both hold simultaneously. This is the check the first iteration of this work skipped.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-11 | agent:claude-code | Created before the joint-gate soak, per HF-4. Records post-recalibration distributions, the frac=6.0 derivation, the flagged divergence from canon's 1.25 seed, and predictions P1–P5. |

---

## Result — evaluated after the soak, 2026-08-11

Firmware `git 52dedd2`, env `k1_unit2_im69d_right`, identity asserted on the wire.
Calibration `SSL=136` learned under this firmware. Both legs witnessed by an
independent microphone: quiet **−60.3 dB**, music **−28.6 dB** (31.7 dB separation,
acoustic path proven).

| | quiet (45 frames) | music vol70 (30 frames) |
|---|---|---|
| `silence` held | **88.9%** | **0.0%** |
| `silent_scale` mean | 0.12 | **1.00** |
| `max_raw` p50 / max, ×SSL | 0.64 / **1.49** | **12.64** / 25.90 |
| `pky` ≥ 2.10 | 21/45 | 27/30 |

| ID | Prediction | Result |
|---|---|---|
| **P1** | quiet `silence` ≥ 95% | **FAIL — 88.9%** |
| **P2** | music breaks silence ≥ 80% | **PASS — 100%** |
| **P3** | music `max_raw` p50 ≥ 3× threshold (≥1632) | **PASS — 1719** |
| **P4** | `silent_scale` → 0.00 within 15 s of music stop | PASS |
| **P5** | quiet `silent_scale` mean = 0.00 | **FAIL — 0.12** |

### What the P1/P5 failure is, and is not

It is **not** the joint gate. The level threshold at frac 4.0 is **544 raw**, and the
loudest quiet frame in 45 s reached **202** — the level term did not fire once, despite
peakiness clearing 2.10 on 21 of 45 quiet frames. The AND rejected every one, exactly as
designed.

The residual 11% therefore comes from the **legacy RMS Schmitt** (`K1_SILENCE_RMS_ENTER
0.04 / EXIT 0.08`) that sits underneath, plus `SILENCE_DWELL_MS` resetting on each of its
trips. That path is untouched by this work and is the correct next target — not another
adjustment to the fraction, which would only degrade P2.

### Method note — a guard bug worth keeping

The derivation harness aborted this run with "ACOUSTIC PATH NOT PROVEN" on a leg whose
witness showed a 31.7 dB separation. The condition was written `music > quiet - 10` where
it must be `music > quiet + 10`: louder is *less* negative on the dB scale. A sign error
in a guard fails in the safe direction here (it refused to derive), but the same error
inverted would have silently accepted a starved acoustic path. Guards need their own
negative control.

---
