---
abstract: "Forensic reconstruction of how the 2026-08-05 IM69D130 bringup produced the noise-gate lockout Captain reported 2026-08-06, plus the latent-defect sweep it triggered. Root cause: the Phase 0 device-proof doc traced a RETIRED silence path (threshold_loud_break = SSL x1.2, computed but never read) and the mic gain was walked 16->8->4 on that basis, costing 4x of music headroom above absolute RMS thresholds that were never re-derived. SAFETY: the same walk-down silently defeated the machine backstop that rejects music-contaminated noise calibration. Also documents the STM gate stuck at 0 on k1_hardware_stm, a dead-variable set in the Core-0 hot path, mic-override asymmetry inherited from SPH0645, and the device-proven AP cadence promotion now parked in stash@{0}. Every claim re-run by the orchestrator; inferences labelled."
---

# IM69D130 bringup → audio-pipeline regression: forensic reconstruction

**Date:** 2026-08-06 · **Tree:** `db300db` (+ lane commits) · **Device:** bench `B489A500`
**Method:** four read-only specialist probes, every load-bearing claim personally re-run by the
orchestrator against live source and the live device. `[FACT]` = visible in a diff, source line, or
device capture. `[INFERENCE]` = reasoned, labelled, not measured.

## 1. Reported symptom

The noise gate blocks ambient correctly, but stays latched; only a loud transient (finger snap)
releases it, and it re-latches within seconds **even while music is playing**.

## 2. Verdict

The lockout is not a tuning error. It is the downstream consequence of a **microphone gain reduction
justified by a code path that does not execute**. The same reduction also disabled a calibration
safety guard. Both were invisible to every gate in the repo: clean build, green host suite, no
warning, no log line.

## 3. Timeline — 2026-08-05, all times +0800

| Time | Commit | Event | Evidence relied on at the time |
|---|---|---|---|
| — | `8335b7f` | dual-K1 sync shelved; lane routed to IM69D130 mic eval | — |
| 22:45 | `70b03e5` | IM69D env born at **G=16**. Chosen by linear extrapolation from ONE device observation at G=1 toward an SPH-band target, deliberately under-stepped as a "conservative first step" | one G=1 sample + extrapolation |
| 22:49 | `7741dd3` | **G=16 → 8.** Quiet `max_raw` 307–1190 overflowed the SSL learn window [50,720]. The G=16 prediction (256–416) was already wrong by ~3x | measured quiet band vs window |
| — | `9013ed9` | G=8 recorded as **GATE FAIL** on silence latch | device receipt |
| 23:26 | `1ae9d4a` | **G=8 → 4.** Stated cause: ambient `max_raw` ~214–296 "stayed above SSL x1.2 (~133) so silence never latched" | `max_raw` / `ssl_p90` telemetry only |

**Process finding [FACT]:** `7741dd3` — a 2x microphone gain change — shipped under a
`docs(lane):` subject with `constants.h | 11 ++-` in its diffstat. Invisible to any history
filtered on `feat`/`fix`, and to the commit gate's change-class reasoning.

**Nothing in the chain audited the constants sitting downstream of the multiply.** Every step's
evidence was `max_raw` / `ssl_p90` telemetry.

## 4. The pivot: the proof document traced the wrong code path

`docs/hardware/im69d130-phase0-gain8-device-proof-2026-08-05.md` contains a section titled
**"## Silence latch path (code)"** asserting:

> `threshold_loud_break = CONFIG.SWEET_SPOT_MIN_LEVEL * 1.20`
> "Any `max_waveform_val_raw > threshold_loud_break` **immediately** clears silence and resets the timer"
> `| Loud-break (SSL x1.2) | ~133 | 88.8 |` · **"Phase 0 complete: YES"**

`threshold_loud_break` occurs **twice in the entire firmware**: the assignment at
`audio/i2s_audio.h:686` and a comment at `:853`. **Zero reads.** [FACT]

The flag it claims to govern is written solely by the RMS Schmitt at `i2s_audio.h:857-879`, and the
source comment at `:849-856` states the RMS gate *"Replaces the SSL/sweet_spot_state==-1 gate"* and
*"deliberately does NOT re-use the peak-based loud_sound_detected veto (threshold_loud_break =
SSL*1.2 … which would veto silence every frame)."* [FACT]

So the one document in the chain that examined the silence path **documented the retired path as
live**, and the gain was halved to move a threshold that gates nothing.

## 5. Why the lockout follows

The live gate compares a **post-gain** RMS against **absolute** constants:

```
i2s_audio.h:530   sample = im69d_samples_i16[i] * K1_MIC_IM69D_INPUT_GAIN   (gain at acquisition)
i2s_audio.h:1130  k1_silence_rms_raw = rms(waveform_fixed_point[])          (POST-gain)
globals.h:704-705 K1_SILENCE_RMS_ENTER = 0.04f / EXIT = 0.08f
                  comment: "Bench-calibrated 2026-07-10"  <- IM73D era, gain 16
```

`git diff main...HEAD -- system/globals.h | grep SILENCE_RMS` is **empty**: gain moved 16→8→4;
the thresholds never did. [FACT]

Orchestrator measurement, bench ambient, 20 s / 26 AP frames:

```
rms_raw  min 0.0030  p50 0.0072  p95 0.0085  max 0.0092
ENTER 0.04 = 4.7x above ambient p95      EXIT 0.08 = 9.4x above ambient p95
silence latched 26/26 frames             STANDBY_DIMMING = 0
```

A 9.4x barrier is a transient, not a passage of music. `SILENCE_DWELL_MS = 5000` re-arms it.

**Correction to an earlier reading.** `f87709d` (2026-07-10) records its own calibration floor as
`<= 0.008`, which matches today's measured 0.0072–0.0085. The noise floor did **not** move, so
"the gain halved the whole domain" is too coarse. The ENTER side still behaves as designed; the
defect is that **EXIT was never validated against music** — that commit's evidence is
*"silence latches in a quiet room"*, the opposite direction from the reported symptom. [FACT]

Scaling ambient back up the ladder gives ~0.029 (G=16) / ~0.014 (G=8) / ~0.0072 (G=4) — all below
ENTER=0.04, so the RMS latch would have engaged at **any** of those gains. [INFERENCE, strong]
The walk-down was not required by the mechanism it cited, and cost 4x of music headroom.

**Because `STANDBY_DIMMING = 0`, the plate never fades.** The visible symptom is effects freezing,
not darkness — `silence` gates `k1_onset_beat.cpp:245,535`, `k1_smart_director.cpp:101,217,434`,
`beat_aware_director.cpp:147`, `k1_tempo.cpp:1334`.

## 6. SAFETY — the calibration backstop is down

IM69D compiles the **SPH0645 base** admission gates. The IM73D widening (`constants.h:72-76`) sits
behind a flag *mutually exclusive* with IM69D (`:45-47`), so it never compiles for this build: [FACT]

```
NOISE_CAL_SSL_PHASE_B_MAX_RAW     1500.0f
NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW  650.0f    // comment: "Flag-off SPH builds keep 650/720 untouched"
NOISE_CAL_SSL_MIN_VALID_RAW         50U
NOISE_CAL_SSL_MAX_VALID_RAW        720U
```

From the lane's own receipts: at **G=8** music `max_raw = 1785` exceeded 1500 → music frames were
**rejected** from calibration. At **G=4** the same music reads **528** → passes both 1500 and 650. [FACT]

Those guards exist to refuse a music-contaminated noise calibration. They are the machine half of
the **Calibration Command Policy** — the load-bearing rule created after an agent poisoned
`SWEET_SPOT_MIN_LEVEL` 281 → 745 by running `start_noise_cal` during music. On the current bench
build only Captain's verbal confirmation remains. Accept-margin is squeezed from below too:
accept needs p90 >= 45.5; G=8 gave 101 (2.2x), G=4 gives 67 (1.47x).

## 7. Defect inventory

| # | Defect | Location | Severity | Status |
|---|---|---|---|---|
| 1 | Cal admission guards 4x too permissive → music can contaminate a noise cal | `constants.h:34-40, 45-47, 72-76` | **SAFETY** | confirmed |
| 2 | Silence gate absolute thresholds never re-derived across mic + 4x gain change | `globals.h:704-705` | high | confirmed |
| 3 | Gain walk-down justified by `threshold_loud_break`, which is never read | `i2s_audio.h:686`; proof doc §"Silence latch path" | high (root cause) | confirmed |
| 4 | STM loudness gate identically 0 on `k1_hardware_stm` (`#if/#elif`, no `#else`) → EdgeMixer modes 7/8 modulate by nothing on the MAIN K1 | `i2s_audio.h` K1_STM block; `platformio.ini` env | high | confirmed |
| 5 | Retired SSL gate still writes `silence_switched`, the live gate's dwell anchor | `i2s_audio.h:797` vs `:870/:873` | medium | confirmed |
| 6 | Dead values recomputed every frame on Core 0: `threshold_loud_break`, `dynamic_agc_floor_*`, `min_silent_level_tracker`, `silence_temp` | `i2s_audio.h:686-692, 346` | medium (misdiagnosis risk) | confirmed |
| 7 | Device-proven AP cadence promotion `96/d3 → 128/d2` parked in `stash@{0}`; bench silently reverted. Stash targets pre-rename `sb_*` paths and cannot simply be popped | `stash@{0}`, `config_types.h:41,59` | high | confirmed |
| 8 | Frame-count literals (`K1V2_MEDIAN_WIN=14`, `K1V2_WARMUP_FR=14`, `K1V2_*_REFR`, `STM_TEMPORAL_FRAMES=17`) gain ~33% real duration if 128/d2 is restored | `k1_onset_beat.cpp`, `k1_stm.cpp` | forward risk | confirmed |
| 9 | `NOISE_CAL_SSL_BOOT_FALLBACK_RAW=120U` sized for G=16; learned SSL now 74 → uncalibrated boot floor sits ABOVE the calibrated one | `constants.h:99` | low | confirmed |

Refuted, recorded so they are not re-litigated: the retired SSL gate is **not** dead weight
(`sweet_spot_state` still drives `run_sweet_spot()` and defect 5); there is **no feedback loop**
whereby silence suppresses the signal that would clear it — all consumers are strictly downstream.

## 8. The structural pattern

Every defect is one shape: **a value that stopped meaning what it meant, consumed by code with no
way to notice.** Absolute thresholds surviving a mic swap. A `#if/#elif` with no `#else` on a third
hardware path. A rationale written in the units of a retired gate. A gain change filed as `docs`.

None produce a build error, a test failure, or a log line. The host suite (950 tests) passes on all
of it, because every one of these is a *semantic* mismatch between a number and its hardware
context — precisely the class no host gate can see. This is why four consecutive agents shipped
confidently on top of one another.

## 9. Not established

- `rms_raw` during real music at normal listening level — **the decisive missing datum.** Requires
  Captain to play a track while an AP capture runs.
- Defect 4 not closed by compilation (`pio run -e k1_hardware_stm` + one AP line would settle it).
- `k1_tempo.cpp` / `k1_gdft_core.cpp` not audited in depth; the AP surface beyond the
  silence/gain/STM chain remains unexamined.
- Whether G=4 is the correct operating point at all, given its justification was a dead comparison.

## 10. Recommended remediation order

1. **Restore the cal backstop** — explicit IM69D arms for `TRUSTED_P90_MAX_RAW` / `MAX_VALID_RAW` /
   `PHASE_B_MAX_RAW` scaled to G=4. Safety net, currently down, cheapest fix.
2. **Delete the dead variables.** They misled the last agent and will mislead the next.
3. **Make the silence gate floor-relative**, as `SILENCE_ENTER/EXIT_SSL_FRAC` already are — those
   are ratio-based and self-scaling, and are the pattern the RMS gate should have followed.
4. **Add the missing `#else` arms** (STM gate; `k1_mic_auto_sense` has the same shape, done right —
   copy it).
5. **Reconcile `stash@{0}`** against the `sb_*` → `k1_*` renames before it rots.
6. **Re-open the gain question** once music RMS is measured.

## 11. Delegation ledger

| ID | Probe | Claim | Class | Orchestrator re-run | Consumed as |
|---|---|---|---|---|---|
| SSA-1 | constants provenance | 3 further constants lack IM69D overrides | load-bearing | confirmed (override blocks asymmetric) | verified evidence |
| SSA-2 | cadence tuple | 128/d2 never landed in a shipping env | load-bearing | confirmed; its "no doc claim" sub-finding was a too-narrow grep — promotion is in `stash@{0}` | verified, one sub-claim corrected |
| SSA-3 | timeline | ladder is 16→8→4; proof doc traced retired path; cal guards now permissive | load-bearing | confirmed all three | verified evidence |
| SSA-4 | red-team | STM gate ≡ 0; dead-variable set; refuted 2 orchestrator seeds | load-bearing | confirmed; its refutations accepted | verified evidence |

No SSA edited, built, flashed, or committed. All device actions, builds and re-runs were the
orchestrator's.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-06 | agent:claude-fable-5 | Created — IM69D bringup forensic reconstruction: gain ladder 16→8→4 justified by a never-read comparison, calibration backstop defeated, 9-defect inventory, delegation ledger. |
