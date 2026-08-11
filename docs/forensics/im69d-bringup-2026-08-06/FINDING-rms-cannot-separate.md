# FINDING: RMS cannot separate music from this room's noise floor — in any gain domain

Orchestrator measurement, 2026-08-06, bench `B489A500`, `k1_bench_im69d` @ G=4 (`git=e4a1288`).
Raw log: `music_capture_45s.log` (50 AP frames / 45 s, music at Captain's normal listening level)
and `ambient_rms_20s.log` (26 frames / 20 s, quiet room).

## 1. The reported symptom, mechanism confirmed

```
rms_raw during MUSIC:  p50 0.0027 · p90 0.0128 · p95 0.0171 · max 0.0289
frames >= K1_SILENCE_RMS_ENTER (0.04):  0 / 50
frames >= K1_SILENCE_RMS_EXIT  (0.08):  0 / 50
silence flag latched:                  50 / 50
```

Music never reaches within 1.4x of the *enter* line. The lockout is fully explained.

## 2. The finding that invalidates the planned fix

| statistic | ambient | music |
|---|---|---|
| `rms_raw` p50 | 0.0072 | **0.0027** |
| `rms_raw` p95 | 0.0085 | 0.0171 |
| `rms_raw` max | 0.0092 | 0.0289 |
| `raw_i16_rms` p50 (pre-gain) | 25.8 | **15.0** |

**Music's median RMS is LOWER than ambient's median RMS**, in both the post-gain and the pre-gain
domain. ~75 % of music frames read at or below the loudest ambient frame.

Cause (Captain's own brief names the input without drawing the conclusion): the room floor is
**narrowband hum, crest ~1.26** — RMS ~= peak. Music is peaky, crest ~3-5 — RMS << peak.
**RMS is the single statistic on which steady hum beats music.**

Therefore **no threshold on RMS separates music from this room, at any gain, in any domain.**

## 3. Two consequences

**(a) Reverting to G=8 does not fix the gate.** Projection x2, same acoustics:
music p90 `rms_raw` 0.0256 (< ENTER 0.04); peak frame 0.0578 (< EXIT 0.08). Lockout survives.
Making this gate see music needs ~G=16 — the gain that overflowed the SSL learn window.
**Contradiction: the RMS gate needs high gain to see music; SSL calibration needs low gain to
learn a floor. Same chain, opposite requirements.**

**(b) Decision gate 2 as specified does not fix it.** Moving to pre-gain `raw_i16_rms` buys
gain-invariance (correct, worth keeping) but the crest problem is identical there — see the table.
Gain-invariant and still blind.

## 4. What does separate

Upper-tail PEAK, not per-frame RMS:

```
max_raw  ambient max ~505      music p90 933 · max 1331
```

A tail statistic (p90/peak over a short window) separates ~2x. Per-frame medians overlap and
invert in every RMS measure tested. The pipeline also already computes onset/spectral-flux
structure, which is a discriminator hum cannot fake.

## 5. Correction to an earlier orchestrator claim

I previously reported the calibration backstop as "defeated". Measured, it is **partially** down
and **volume-dependent**:

```
music p90 max_raw  933 vs TRUSTED_P90_MAX_RAW 650  -> still REJECTS  (backstop holds)
music max         1331 vs PHASE_B_MAX_RAW   1500  -> ADMITS          (backstop fails)
```

The lane receipt's "528, passes every gate" came from a quieter stimulus. At G=8 the same music
projects to p90 1866 / max 2662 and both gates fire robustly — which is the strongest remaining
argument for the gain revert, on safety grounds alone rather than as a fix for the lockout.

## 6. Implication for remediation

W3 (go-dark gate) must not ship as a gain-invariant RMS comparison. The statistic has to change
before the domain does. W1 (cal-gate corridor) is unaffected and remains the correct first step.
