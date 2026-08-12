---
abstract: "P4.A IM69D consumer baseline (Unit 2 0C54FC00, dual IM69D130 RIGHT, SSL=167 measured) — CLOSED 2026-08-13. Silence floor: joint gate 1.75×SSL shipped + eyes-on. Bose-SPL legs (canonical fixture PioneerDJ Demo Track 1, vol 40/55/70): awake 100% at all volumes; music conf med 0.39/0.81/0.75, p75 up to 0.97; lock duty 9–27% (FSM-dynamics-limited, not floor-limited). Lock floor 0.60 RETAINED, now cited to IM69D measurement (ambient-quiet p95 0.58 below, music p75 above). K1_AUDIO_PROFILE_IM69D130_UNIT2 POPULATED; UNCHARACTERISED_ACK removed from the IM69D env chain. Behavioural table gate: tests/test_im69d_consumer_floors_behavioural.py."
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
| Lock acquire/hold | **CLOSED 2026-08-13** — 0.60 retained, measurement-cited (see Update below); lock DUTY routed to the tempo lane |
| DF presence | **CLOSED** — gate proven live in quiet-live and product-SPL music legs |
| `K1_AUDIO_PROFILE_IM69D130_UNIT2` | **POPULATED 2026-08-13** (first-principles, per the tombstone contract) |

### Update — 2026-08-13: Bose-SPL legs run — floors CLOSED, profile 2 populated

**Fixture correction:** the interim legs above used an ad-hoc track picked by file search.
The canonical fixture is **`~/Music/PioneerDJ/Demo Tracks/Demo Track 1.mp3`** (the
`transfer_leg.py` default used by every verified transfer-test leg). All 2026-08-13 legs
below use it; both leg runners now default to it.

**Bose legs (Unit 2, 90 s each, witnessed):**

| leg | witness mean | awake | conf med | conf p25 | conf p75 | lock % | max_raw med (SSL=167) |
|---|---|---|---|---|---|---|---|
| vol 40 | −50.9 dBFS | **100%** | 0.39 | 0.24 | 0.62 | 9% | 363 (2.2×SSL) |
| vol 55 | −41.3 dBFS | **100%** | 0.81 | 0.56 | 0.97 | 27% | 912 (5.5×SSL) |
| vol 70 | −33.0 dBFS | **100%** | 0.75 | 0.61 | 0.87 | 18% | 1950 (11.7×SSL) |

**Floors closure:**

- **Wake behaviour:** the 1.75 joint gate wakes on 100% of frames from vol 40 up — no
  fails-to-wake margin concern at any tested product volume.
- **Lock floor:** `K1_LOCK_CONFIDENCE = 0.60` **retained and now measurement-cited**:
  ambient-quiet conf p95 (0.58) sits just below it; music conf p75 (0.87–0.97 at
  vol 55/70) sits well above. Lowering it would admit ambient false-locks; raising it
  starves real locks. The low lock **duty** (9–27% despite conf medians 0.75–0.81) is a
  tempo-FSM acquire/hold dynamics question, not a mic-floor question — routed to the
  tempo lane, not tuned here.
- **DF presence:** gate proven live in both quiet-live and music legs (`mx_dfinj` 1.0);
  no separate floor change required.
- **`K1_AUDIO_PROFILE_IM69D130_UNIT2` POPULATED** (`k1_audio_profile.h`) per its own
  populate-condition (transfer test closed); `K1_AUDIO_PROFILE_UNCHARACTERISED_ACK`
  removed from the IM69D env chain. IM73D envs keep their fail-closed ACK.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-13 | agent:claude-code | Bose-SPL legs (canonical fixture) — floors CLOSED, lock 0.60 measurement-cited, profile 2 populated, ACK removed; fixture correction recorded. |
| 2026-08-12 | agent:claude-code | Created — quiet-ambient + laptop-music distributions with witnesses, silence floor closed, lock/DF floors explicitly BLOCKED-ON-SPL, behavioural table gate landed. |
