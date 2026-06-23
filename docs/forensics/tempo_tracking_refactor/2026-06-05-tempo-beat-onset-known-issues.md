---
abstract: "Consolidated known-issues register for the K1 tempo + beat + onset tracking stack (onset/novelty path, sb_tempo ACF/comb/prior/confidence, beat-phase flywheel) as of HEAD e226b25 on wip/audio-saliency-recovery. 38 issues, file:line-grounded, graded CODE-VERIFIED/MEASURED/SUSPECTED, cross-confirmed across four independent audits. Headline: tempo RANKING is decent (host in-range Acc1 56.2%, true overall 50.0%) but the BEAT-PHASE and ONSET layers that effects actually ride are structurally weak AND entirely unmeasured — beat is an onset-gated phase tick (not a beat tracker), onsets flatline under device AGC, and we have no beat-F/CMLt/AMLt/onset-F harness. Includes the 14 'off' track breakdown and the REFUTED/CLOSED claims that must NOT be re-listed as bugs."
---

# Tempo + Beat + Onset Tracking — Consolidated Known-Issues Register

**Date:** 2026-06-05 · **Branch/HEAD:** `wip/audio-saliency-recovery` @ `e226b25` · **Author:** agent:CTO
**Method:** four independent read-only audits (onset/novelty code · sb_tempo tempo+beat code · measurement harness · documented-issue trail), cross-confirmed, with the orchestrator's own re-run of the two tempo gates and a grep-anchor of the load-bearing onset claims on this branch. Per `/ssa-management`: no sub-agent prose was canonised without the cited file:line / measurement.

> **Read this first (the one-paragraph truth).** The tempo *ranking* engine is genuinely competent — on real music it picks the right tactus often enough (host, in-range, ±4%) and the octave-doubling failure that dominated last week is gone. **But that is the smallest part of the problem.** The layer that makes an effect *visibly lock to the music* — the **beat phase** and the **onset** stream — is both structurally weak (beat is an onset-gated periodic *tick*, not a beat tracker; onsets are computed on three pre-summed scalars and **flatline under the device AGC clamp**) and **entirely unmeasured** (we score steady-state BPM only; there is no beat-F / continuity / onset-F harness). "Tempo is strong" is true of *ranking* and misleading about *the product promise*.

## Severity scale & status labels
- **P0** product-blocker for the beat-reactive promise · **P1** high · **P2** medium · **P3** low/polish.
- **CODE-VERIFIED** traced to arithmetic at file:line · **MEASURED** confirmed by a harness run · **SUSPECTED** reasoned, needs a HW/harness run to confirm.
- Line numbers read at HEAD `e226b25`; re-grep before editing (code moves).

---

## 0 · Measured ground truth (orchestrator re-run, this session)
| Metric | Value | Note |
|---|---|---|
| Real-music Acc1 (overall, n=36) | **50.0%** | the honest top-line |
| Real-music Acc2 (overall) | 52.8% | octave-tolerant |
| Real-music **in-range** Acc1/Acc2 (n=32) | **56.2% / 56.2%** | excludes 4 out-of-range tracks → bends up ~6 pts |
| Octave classes (in-range) | `{off:14, x1:21, x1/2:1}` | doubling≈gone, but 14 gross misses |
| `tempo_replay.py` (synthetic) | **TEMPO_REPLAY_FAIL, failures=2** | 144 clean-train halves → 72 |
| Beat-phase / onset quality | **UNMEASURED** | no F-measure / continuity harness exists |

---

## 1 · ONSET & NOVELTY  (`audio/GDFT.h`, `audio/sb_onset_beat.cpp`, `audio/sb_audio_snapshot.cpp`)
All CODE-VERIFIED. Anchored on this branch (clamp/novelty/refractory greps confirmed).

| ID | Severity | Issue | file:line | User-perceived failure |
|----|----|------|-----------|------------------------|
| ON-01 | P1 | Novelty = **raw energy spectral-flux**, not whitened/log-musical | GDFT.h:302-310 | reacts to loudness, not musical events |
| ON-02 | **P1** | **AGC clamp to [0,1] flattens onset contrast on loud input → host-vs-device divergence** (loud bins saturate at 1.0, frame-Δ→0, novelty flatlines) | GDFT.h:227,269-278; onset:150-152 | onsets *stop firing* on loud real-world audio; effects go dead on device but look fine on host |
| ON-03 | P2 | Single-frame Δ, **no adaptive-median floor** | GDFT.h:298-308 | drift/background changes leak into novelty |
| ON-04 | P2 | Only sqrt compression; **bass-dominated** 80-bin mean | GDFT.h:325 | kicks swamp everything else |
| ON-05 | P3 | 5-slot history ring, reads `[prev]` (~7.5 ms stale) — too short to be a real curve | snapshot:17-29 | weak temporal context |
| ON-06 | **P1** | **Onset detected on 3 pre-summed scalars (low/mid/high), not per-band flux → polyphonic onsets architecturally invisible** | snapshot:32-54; onset:202-213 | misses simultaneous/layered hits |
| ON-07 | P1 | **Fixed magic thresholds** (0.14/0.20/0.16), non-adaptive | onset:205-212 | wrong sensitivity across genres/levels |
| ON-08 | P2 | Triple-AND gate (delta∧attack∧rise) **drops soft onsets** | onset:167-172,210-212 | quiet/legato passages register nothing |
| ON-09 | P2 | Global **240 ms refractory** caps onset rate ≈4.2 Hz | onset:25,209 | fast hi-hat/snare rolls under-counted |
| ON-10 | **P1** | **"beat" is an onset-gated tempo-phase tick, NOT a beat tracker** *(= T11)* | onset:97-112,232-241 | beats don't land on the music's beats |
| ON-11 | P2 | **±25% interval tolerance** → wrong-tempo lock / half-double flap | onset:75-112 (divisor 4 :28) | locks to a plausible-but-wrong pulse |
| ON-12 | P3 | `onset_strength` excludes bass (kicks only in `bass_strength`) | onset:207,225 | kick-driven music under-triggers the main onset |
| ON-13 | P3 | 80 ms event *window*, not an edge | onset:24,141 | consumers may double-fire per onset |
| ON-14 | P2 | low/mid/high = **index-thirds of bins, not Hz**; "low" ≠ bass | snapshot:36-53 | band semantics don't match perception |
| ON-15 | P2 | Onset latency ~15–30 ms+ (chunk + stale read + 80 ms fast-EMA) | onset:174,24 | visible lag beat-to-light |
| ON-16 | P2 | No HFC / high-freq emphasis; bass dominance unmitigated | snapshot:32-54 | cymbals/transients under-weighted |
| ON-17 | P3 (SUSPECTED) | Silence decays lock 1 step/frame → mis-phase on resume | onset:65-73,183-200 | wrong phase when music restarts |

---

## 2 · TEMPO TRACKING — selection, range, prior, comb, latency  (`audio/sb_tempo.cpp`)
All CODE-VERIFIED unless noted. Mechanisms themselves are correctly implemented (verified separately) — these are *limitations/brittleness*, not "doesn't work".

| ID | Severity | Issue | file:line | User-perceived failure |
|----|----|------|-----------|------------------------|
| T1 | P1 | **BPM cap 60–155**; out-of-range tempi (DnB ~170, slow <60) **unrepresentable / silently aliased** | cpp:11-12,580 | whole genres mis-tracked; 3 corpus tracks out of range |
| T2 | P2 | Edge bins 60/155 have **no guard band** → self-neighbour → rail pile-up | cpp:594-603 | tempi near the rails bias inward |
| T3 | P1 | **Fixed tactus prior (88 BPM, σ0.75 log2)** biases vs fast/slow; a fast peak must be **1.57–1.81× dominant** to beat the 88-bin | cpp:73-79,587,379 | genuinely fast/slow songs pulled toward 88 |
| T4 | P1 (MEASURED) | **Comb weights hand-tuned; structurally weak on clean-periodic** signals (144 synthetic halves — comb needs real harmonic asymmetry to break the octave) | cpp:281-296,351-356 | degenerate/electronic pulses can halve |
| T6 | P1 | **Lock threshold 0.60 synthetic-tuned** vs the broad real-music confidence distribution | cpp:35-40,569 | real music under-locks |
| T7 | P2 | **Warm-up Goertzel fallback** (weaker estimator) for ~sec; winner **jumps** at the `acf_valid` seam | cpp:376-383,497-523 | first seconds wrong then a visible jump |
| T10 | P1 | **Tempo-change latency ~2–6 s** (EMA 0.975 + 5-tick hysteresis + 11.5 s ring inertia) | cpp:405-444,467-475 | slow to follow tempo changes/transitions |
| T13 | P1 (SUSPECTED attribution) | ACF window = **11.52 s** (512/44.44 Hz). Captain's "gap = window length": window is a **secondary** knob, **not** the dominant ceiling cause | cpp:27,315-337 | — (see ceiling note below) |
| T14 | P2 | Novelty fed to ACF is a **single broadband scalar**, peak-hold ÷3-decimated (44.44 Hz), clamp[0,4] — an **upstream quality cap** *(= ON-01/ON-06)* | cpp:648-661,237 | the ceiling is built in before the ACF runs |

**On the ceiling (the Captain's hypothesis, tested):** the window is already long (11.52 s ≈ 17–29 beats; typical tempo-ACF is 4–8 s). Window length is **exonerated as the primary ceiling driver**. The stronger suspects for the ~56% ceiling are **T14 novelty quality** (one blended broadband scalar), **fast-tempo lag coarseness** (integer-lag ACF spacing blows to ±5–8 BPM at 120–155, so the parabolic interp is load-bearing), and **T3 the fixed prior**. **Cheap falsification:** sweep `SB_HISTORY_LENGTH` 256/512/768 through `tempo_accuracy.py` — flat Acc1 across the sweep exonerates the window and points the work at novelty + interp + prior.

---

## 3 · BEAT-PHASE / FLYWHEEL / CONFIDENCE  (`audio/sb_tempo.cpp`, `sb_tempo.h`)
**This is the highest user-facing risk cluster — the bridge from "ranks correctly" to "visibly locks".** It is where effects have historically died and is the least HW-proven.

| ID | Severity | Issue | file:line | User-perceived failure |
|----|----|------|-----------|------------------------|
| T5 | **P0** (SUSPECTED) | **Confidence MAGNITUDE as an effect gate is unproven on HW** (history: 0.05–0.14 → flywheel never acquired → Tempo Comet dead on device). Post-fix (sel_score) the *ranking* is fixed; is the *absolute scale* now usable as a gate? | cpp:495-526,393-403 | beat effects silently never trigger on device |
| T8 | P1 | **"PLL" is open-loop phase extrapolation + a HARD re-anchor (~1.08 s)** — no phase-error integration | cpp:535-553,528-531 | audible/visible **beat jump** at each re-anchor |
| T9 | P1 | **Phase drifts between detections**; on a confidence drop the flywheel keeps ticking a **stale** tempo | cpp:540-552,555-571 | beats wander off the music, then snap back |
| T11 | P1 | **Beat tick is a periodic sinusoid phase + fixed 0.08π offset, NOT onset-aligned** (ignores `sb_onset_beat`) *(= ON-10)* | cpp:246,535-553 | the "beat" is a metronome guess, not the actual beat |
| T12 | P2 | **No downbeat / meter / bar phase** — tactus only; `SBTempoEvent` has no bar field | header:13,22-29 | no "1", no bar-aware effects possible |

---

## 4 · MEASUREMENT & VALIDATION  (`scripts/regression-harness/`)
What our numbers can and cannot be trusted to mean.

| ID | Severity | Issue | evidence | Consequence |
|----|----|------|----------|-------------|
| M1 | P1 | **In-range bias**: headline 56.2% excludes 4 tracks (58/167/172/200 BPM) | tempo_accuracy.py:57 | true overall is **50.0%**; 56.2% bends up ~6 pts |
| M2 | P1 | **Host clean-novelty ≠ device**: harness models no AGC/GDFT/clamp chain *(root = ON-02)* | :217 | **no device tempo number exists**; host figures are an upper bound |
| M3 | P2 | **GT itself half-tempo on 4 tracks** (0331/0353/0680/0666; beat-file IBI = 2× metadata) | tracks csv | overstates winner-selection error |
| M4 | P2 | **Octave class is integer-ratio only** `{1/3,1/2,1,2,3}` — no 3/2, 2/3, 4/3 | :180 | real ~1.3×/0.66× slips dumped into "off"; "oct-doubling 0%" is misleading, not "solved" |
| M5 | P1 | **The 14 "off" tracks** classified (see §5) | tracks csv | the ~1.3× cluster = low-bin pinning / quartic-reduction failure, not clean doubling |
| M6 | P1 (MEASURED) | **`tempo_replay` is RED** (failures=2); tests only degenerate synthetic fixtures — no real-music, no range/octave sweep, no phase | :202-205 | the only synthetic gate is broken-by-design (`amend-broken-gates` applies) |
| M7 | **P0** | **COVERAGE GAP** — zero beat-F / CMLt / AMLt / continuity / onset-F anywhere; gold beat times exist on disk but are used only for an IBI sanity check, never to score | grep (0 hits) | **beat phase, beat continuity, onset quality, and device behaviour are entirely unmeasured** — for a beat-reactive product, correct BPM + wrong phase still looks wrong, and we'd never see it |

---

## 5 · The 14 "off" tracks (real-music misses, from the corpus CSV)
- **3 OUT-OF-RANGE** (T1): 0331, 0068, 0199 — outside 60–155, unrepresentable.
- **4 GT-SUSPECT half-tempo** (M3): 0353 (74/148), 0680 (80/160), 0666 (96/192), 0331 — beat-file IBI agrees with the *faster* pulse the detector tracked, yet scored wrong.
- **6 in-range METRICAL slips** at 4:3 / 3:2 / 2:3 / 0.72 (0435, 0333, 0272, 0585, 0423, …) — the ~1.3×/0.66× cluster; low-bin pinning + quartic-reduction failure, **not** clean doubling (so the comb can't catch them).
- **3 GENUINELY wrong**, no clean ratio: 0705 (+17%), 0741 (+11%), 0877 (−12.5%).

*(Classification is ratio-inferred, not perceptually verified per track — method risk.)*

---

## 6 · REFUTED / CLOSED — do NOT re-list as bugs
These were investigated and are settled. Re-opening them is the stale-claim trap.
- **"ACF is flat (std 0.029), barely functioning"** — **REFUTED** (actual std ≈0.28; `acf_only` 40.6% vs `prior_only` 15.6%). Nearly drove a revert of a real +15.6 pp gain. Re-run: `python3 scripts/regression-harness/bt_acf_4way.py`. Source: `RECONCILIATION.md §1`.
- **"v3 is Goertzel-only"** — **REFUTED** (v3 ships `esv11_pick_top_tempo_bin_octave_aware` + a BeatTracker ACF). Source: `RECONCILIATION.md §1`.
- **"53% is the ACF ceiling"** — **REFUTED** (53.1% is the 44 Hz-parabolic *sub*-ceiling; the real figure is the 133 Hz path). Source: `RECONCILIATION.md §1`.
- **Naive half-ratio octave arbiter fixes doubling** — **REVERTED** (`8121521`; broke the clean 144 metronome). Replaced by the harmonic-comb (`270ba72`). **Do not re-attempt the ratio arbiter.**
- **Octave-doubling on real music** — **CLOSED** by harmonic-comb + prior (`270ba72`): octave-err 12.5%→0.0%, x2 errors 5→0. *(The remaining misses are range/metrical/GT, not doubling — see §5.)*

---

## 7 · Priority read (where to spend effort, given the product promise)
1. **M7 + T5 (P0):** build the missing **beat-F / CMLt / AMLt + onset-F harness** against the on-disk gold beat times, and **measure the confidence magnitude on hardware**. Until these exist we are flying blind on exactly the layer the product is sold on. Everything below should be judged by that new harness, not by BPM accuracy.
2. **ON-02 / M2 (P1):** the **device-AGC onset flatline** is the most likely reason beat effects "die on device but look fine on host". Confirm on HW, then give the novelty path headroom (un-clamped flux / log-domain) so onsets survive loud input.
3. **T8/T9/T11 + ON-10 (P1):** make the beat **onset-aligned with a real phase-locked loop** (error-integrating), not an open-loop periodic tick with hard re-anchors. This is the "visibly locks" payoff.
4. **ON-06 / ON-01 / T14 (P1):** the novelty is one broadband scalar on three pre-summed bands — a quality cap *upstream* of the ACF; per-band flux + whitening raises the ceiling more than window tuning.
5. **M6 (P1):** fix the red synthetic gate (de-degenerate the 144 fixture) so it's honestly green and actually tests what hardware sees.
6. **T1/T3 (P1):** widen/parameterise the BPM range and reconsider the fixed 88-prior for genre breadth — only after the harness can score it.

---

## 8 · Re-inspect commands (verify any line before acting)
```
# tempo gates (the orchestrator's anchors)
python3 scripts/regression-harness/tempo_accuracy.py      # Acc1/Acc2 + octave classes
python3 scripts/regression-harness/tempo_replay.py        # synthetic locks (currently RED)
python3 scripts/regression-harness/bt_acf_4way.py         # ACF vs prior ablation (refutes "flat ACF")
# onset / novelty
grep -n "calculate_novelty\|spectrogram\[i\] = out\|spectral_history" SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h
grep -n "REFRACTORY\|INTERVAL\|TOLERANCE\|phase\|sb_stable_intervals" SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.cpp
# tempo / beat
grep -n "SB_TEMPO_MIN_BPM\|SB_TEMPO_MAX_BPM\|prior\|comb\|sb_conf_score\|sb_advance_phase\|SB_HISTORY_LENGTH" SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp
# coverage gap (expect zero hits)
grep -rn "CMLt\|AMLt\|continuity\|f_measure\|onset.*F" scripts/regression-harness/
```
**Method risk (honest):** the code issues are CODE-VERIFIED at file:line; the off-track classifications are ratio-inferred (not per-track perceptual); **T5 (confidence scale) and T13 (ceiling attribution) are SUSPECTED and need a HW/harness run to confirm.** Source scratch files: `docs/_scratch/ISS-{onset,tempo-beat,harness,docs}.md`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:CTO | Created — consolidated tempo/beat/onset known-issues register (38 issues across onset/novelty, tempo, beat-phase, measurement) from four independent read-only audits + the orchestrator's own gate re-run, verified at HEAD e226b25. Carries the 14-off-track breakdown and the REFUTED/CLOSED set. Headline: ranking decent, beat-phase + onset layers structurally weak AND unmeasured. |
