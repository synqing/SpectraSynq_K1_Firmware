---
abstract: "P4.A IM69D consumer baseline (Unit 2 0C54FC00, dual IM69D130 RIGHT, SSL=167 measured). Silence floor CLOSED: joint gate 1.75×SSL shipped + eyes-on (a8b1912a). Quiet/ambient + laptop-SPL music percentiles for conf/lock/pky/max_raw captured with witnesses. Lock and DF floors remain BLOCKED-ON-SPL: laptop playback (witness −48 dBFS) did not wake the device (silence held 75% of frames) — confirming the ~5× SPL trap — so K1_AUDIO_PROFILE_IM69D130_UNIT2 stays unpopulated until a Bose-SPL leg. Behavioural table gate: tests/test_im69d_consumer_floors_behavioural.py."
---

# P4.A — IM69D consumer baseline (Bench Unit 2)

**Date:** 2026-08-12 · **Device:** Unit 2 `0C54FC00`, dual IM69D130, RIGHT slot, `SSL=167` (`cal_source=measured`, final placement) · **Build:** `k1_unit2_im69d_right_matrix @ 947e2be8` (audio path identical to `k1_unit2_im69d_right`)
**Raw legs:** `raw/leg_quiet-ambient.json` (96 frames, witness −67.8 dBFS mean), `raw/leg_music-laptop100.json` (123 frames, witness −48.0 dBFS mean, moonlight-lyria fixture, laptop speakers @100%)

## Rule (binding, P2.B)

**IM69D floors are measured on IM69D silicon, calibrated at final placement.** Nothing here
derives from any Aug-9 IM73D ifdef. Provenance: this doc + the transfer-test forensics only.

## 1. Silence floor — CLOSED (shipped)

`K1_SILENCE_JOINT_LEVEL_SSL_FRAC = 1.75` + `K1_SILENCE_PEAKINESS_BREAK = 2.10`, IM69D-scoped
(`a8b1912a`), derived from the recalibrated joint window (worst quiet p95 1.03×SSL, worst
music p25 2.13×SSL), device-proven 100%/0% on both units, **Captain eyes-on PASS** (`5dcbfc07`).
Behavioural table gate: `tests/test_im69d_consumer_floors_behavioural.py` (hum rejection,
quiet-transient rejection, wake margins, usable-window ratchet, SPH Schmitt untouched).

## 2. Measured distributions (this session's legs)

### Quiet — ambient working room (witness −67.8 dBFS mean, −42.9 max; NOT a true-silence leg: keyboard + host fans present)

| field | med | p25 | p75 | p95 | max |
|---|---|---|---|---|---|
| tempo `conf` | 0.21 | 0.07 | 0.40 | **0.58** | 0.95 |
| `lock` | 0 | 0 | 0 | 0 | 1 |
| `pky` | 1.93 | 1.69 | 2.24 | 2.81 | 3.32 |
| `max_raw` | 155 | 76 | 255 | 452 | 824 |
| `peak_scaled` | 0.13 | 0.00 | 0.49 | 1.03 | 1.25 |
| `silence` | 0 (never latched) | | | | |

Quiet-ambient `conf` p95 = **0.58** with spurious lock excursions to 1 — the same
thin-margin exposure the `K1_AUDIO_PROFILE_UNCHARACTERISED_ACK` declares (lock threshold
0.60 vs median music conf 0.58 on this mic family). Any lock floor must clear 0.58 with
margin at product SPL.

### Music — laptop speakers @100% (witness −48.0 dBFS mean) — **FIXTURE INADEQUATE, kept as evidence of the trap**

| field | med | p25 | p75 | p95 | max |
|---|---|---|---|---|---|
| tempo `conf` | 0.00 | 0.00 | 0.24 | 0.52 | 0.87 |
| `lock` | 0 | 0 | 0 | 1 | 1 |
| `max_raw` | 95 | 56 | 1190 | 1915 | 2974 |
| `silence` | **latched 75% of frames** | | | | |

Laptop playback delivers ~5× too little SPL at the K1 (standing trap, re-confirmed
numerically): the joint gate correctly held silence for most of the leg, so tempo
conf/lock collapsed. **These columns must not seed floors.**

### Anchors at product SPL (Bose, prior verified evidence)

- Music @ vol 70 (2026-08-11 post-flash verification): `conf` mean **0.66**, `lock` **50%**,
  `max_raw` mean 2190, `silence=0` every frame.
- Transfer-test full gamut (2026-08-12): music response statistically identical across
  units (0.92, p=0.67, n=179/side).

## 3. Floors status

| Floor | Status |
|---|---|
| Silence enter/exit (IM69D) | **CLOSED** — joint gate 1.75/2.10, shipped, eyes-on |
| Lock acquire/hold | **BLOCKED-ON-SPL** — needs a Bose-SPL leg for the music `conf` distribution; quiet ceiling measured here (p95 0.58). Do NOT populate from the laptop leg. |
| DF presence | Gate mechanism proven live (`mx_dfinj` 1.0 on 32/32 non-latched quiet frames, P5.B leg); numeric floor for `dforge_presence_ok` likewise owed a product-SPL distribution. |
| `K1_AUDIO_PROFILE_IM69D130_UNIT2` | **Deliberately unpopulated** until the above close (first-principles derivation only, per the tombstone contract). |

**Next concrete step (one Bose press away):** re-run `p4_baseline_leg.py music-boseNN` at
vol 40/55/70, derive music `conf`/`lock` percentiles, set lock floor above quiet p95 0.58
with the measured margin, populate profile 2, remove the `UNCHARACTERISED_ACK`.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Created — quiet-ambient + laptop-music distributions with witnesses, silence floor closed, lock/DF floors explicitly BLOCKED-ON-SPL, behavioural table gate landed. |
