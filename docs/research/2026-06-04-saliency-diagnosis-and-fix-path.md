---
abstract: "Synthesis verdict on the ported 4-axis MusicalSaliency primitive (wip/audio-saliency-recovery). The 0.21/0.003/silence>music FAIL is REAL output (reproduced exactly in the live env: precision 0.2074, recall 0.0030, music 18.28 epm, silence 24.46 epm, 36 tracks) but is MIXED — a COMPOUND failure dominated by one firmware event-gate bug, not a weak detector. Measured discriminator: deleting the self-ratcheting 2*EMA(OA) gate + consulting audio.silence flips music_epm 18.28->55.94 (PASS) and silence_epm 24.46->0.0 (PASS) in one change, while precision stays ~0.21 (residual = AP-conditioning gap + single-axis harness collapse). Ranked root causes, sequenced fix-path, and the single next experiment."
---

# Musical-Saliency Diagnosis & Fix-Path — Synthesis Verdict

**Date:** 2026-06-04 · **Branch:** `wip/audio-saliency-recovery` (sb_musical_saliency files UNCOMMITTED on disk) · **Author:** agent:synthesiser
**Inputs:** 6 probe results + independent verification in the live environment (pio/python3/clang++ all functional).

---

## 0. TL;DR verdict

The fork's musical-primitive FAIL is **REAL output, not a sandbox artefact** — I reproduced codex's numbers byte-for-byte in the live env. But the *interpretation* "the detector is a weak primitive" is **MIXED / largely wrong**: the dominant cause is a **firmware event-gate bug** (a self-ratcheting `2*EMA(overallSaliency)` threshold the fork author invented, absent from the v3 donor), compounded by a real AP-conditioning gap and a benchmark that cannot exercise the 4-axis design. **A single gate-only change flips two of the four PASS criteria** (music-rate and silence-rate), proving the gate — not detector deadness — drives the headline failure.

---

## 1. Is the failure REAL or a measurement artefact? — MIXED (measured both ways)

### 1a. The metric is REAL output (reproduced in the live env, NOT codex's sandbox)
`python3 musical_saliency_benchmark.py --json` over the 36 HarmonixSet WAVs, built+run here:

| Metric | As-is (my run) | codex | Pass criterion |
|---|---|---|---|
| precision | **0.2074 (45/217)** | 0.21 | ≥0.65 → FAIL |
| recall | **0.0030 (45/14908)** | 0.003 | ≥0.45 → FAIL |
| music epm | **18.28** | 18.3 | 40–180 → FAIL |
| silence epm | **24.46** | 24.5 | <12 → FAIL |

Exact reproduction (`/tmp/sal_asis.json`, totals events=217, beats=14908, music_s=712.1, silence_s=186.4, silence_events=76). **5 of 6 probes independently reproduced these same numbers in the real env.** The build also compiles clean (probe-2: `pio run -e k1_hardware` SUCCESS 31.14s, RAM 27.7%, Flash 9.0%) and host tests pass (123/123). So **codex's "RED — build blocked / no pyserial" was a sandbox artefact; the metric itself is not.** The firmware is shippable-clean; the *behaviour* is what fails.

### 1b. But the metric mis-attributes the cause (the scorer also has real defects)
Two benchmark defects make the as-is numbers uninterpretable as a *detector* verdict:
- **Single-axis collapse** — `musical_saliency_benchmark.py:57-67` broadcasts the one host scalar `novelty` into all 8 SBAudioSnapshot fields (`spectral_energy`, `chroma_strength`, low/mid/high all = `novelty`). The 4-axis detector is fed three identical copies, so harmonic/timbral/dynamic discrimination — the entire reason the v3 primitive was ported — is structurally collapsed to one flux derivative. **The harness cannot exercise saliency as designed.**
- **Recall denominator is a category error** — `:332` `recall = recall_hits / total_beats` (total_beats=14908) against a `recall ≥ 0.45` pass bar (`:347`). With only 217 sparse section-change events, max achievable recall ≈ 217/14908 = 0.0146 — **0.45 is structurally impossible.** It also contradicts the harness's own `music_events_per_min` band of 40–180 (`:353`). A `segments/` ground-truth dir EXISTS at the GT root (verified: `dataset/segments/0001_12step.txt`…) — the correct sparse reference — but the loader only reads `beats_and_downbeats/` (`:198`). The right reference ships and is unused.

**Verdict on 1:** REAL output, MIXED attribution. The FAIL is genuine *behaviour* but the as-is benchmark over-indicts the detector and under-indicts the gate.

---

## 2. True root cause(s), ranked by evidence

### RC-1 (DOMINANT, measured) — Invented self-ratcheting firmware event gate · `sb_musical_saliency.cpp:165,168-169,181`
`adaptiveFloor` is a `0.99/0.01` EMA **of overallSaliency itself** (`:181`); the event threshold is `clamp01(adaptiveFloor * 2.0)` (`:165`). Because real overallSaliency carries a high DC floor (probe-1 measured meanOA=0.37, maxOA=0.64 on track 0FOjmV66zf8), the floor ratchets monotonically up and the 2× threshold rises until almost nothing clears it — events fire only in the warm-up window, then the gate slams shut (a clean synthetic spike-every-120ms over ~15s fires only 6 of ~120 expected). The engine **also never reads `audio.silence`** (grep: 0 matches in .cpp/.h, verified here) even though the snapshot carries it (`sb_audio_snapshot.cpp:30`) and the harness sets it (`benchmark.py:67`). In silence, AGC freezes and the floor decays toward ~0, so tiny uncorrelated jitter clears the collapsed threshold → **silence fires MORE per-minute than music.** This is the literal signature of the reported inversion.

**This gate does not exist in the v3 donor.** v3 `ControlBus.cpp:271-273` uses `threshold = max(expected * 0.15, threshold_floor=0.02)` — a **fixed-floor relative gate** — plus explicit silence hysteresis (`:749-775`). The fork author transcribed the axis math but **invented** the discrete-event gate.

**MEASURED DISCRIMINATOR (I ran this):** I surgically replaced only the gate — `adaptiveFloor*2` → `adaptiveFloor + 0.15` with a slower `0.995` floor EMA, and added `!audio.silence` — touching nothing else (no axis, no conditioning). Re-run on all 36 tracks:

| Metric | As-is | **Gate-only fix** | Δ |
|---|---|---|---|
| music epm | 18.28 (FAIL) | **55.94 (PASS)** | into 40–180 band |
| silence epm | 24.46 (FAIL) | **0.0 (PASS)** | inversion eliminated |
| events | 217 | 664 | 3× |
| recall | 0.0030 | 0.0093 | 3× |
| precision | 0.2074 | 0.2078 | unchanged |

(`/tmp/sal_gatefix.json`; file restored to original after.) **One firmware change flips two of four PASS criteria.** (My recall lift is 3× vs probe-1's 8× because I held a conservative fixed margin + silence gate; probe-1 used a looser flux-only variant. Direction and the two PASS flips are robust across both.) Precision staying flat at ~0.21 cleanly isolates the residual to RC-2/RC-3 — **not** to the gate.

### RC-2 (real, secondary, source-anchored) — AP-conditioning gap: raw features fed into v3-calibrated thresholds
The fork feeds **raw, un-conditioned** GDFT-domain features straight into thresholds copied verbatim from v3, where those thresholds were calibrated for a **bounded, log-compressed** domain. Verified against both sides:
- Fork snapshot writes raw: `novelty = clamp_nonnegative(raw)` (`sb_audio_snapshot.cpp:29`), `spectral_energy = (low+mid+high)/NUM_FREQS` raw mean (`:54`), `chroma_strength = chroma_max/chroma_sum` — a concentration ratio in [0.083, 1.0] (`:70`). Zero log/compression/Schmitt (grep confirmed).
- Host novelty is `sqrt(max(flux − local_mean, 0))` then per-file p99-normalised (`novelty_from_wav.py:105,110`) — also un-log-conditioned.
- v3 feeds `computeSaliency` PRE-conditioned fields: log1p-domain flux, `fluxScale=20`, bounded compression `f/(1+f)`, fixed-scale RMS, Schmitt silence gate.

Consequence (probe-3, source-anchored): `harmonicChangeThreshold=0.5` on a [0.083,1.0] ratio delta is **never crossed → harmonic axis is dead**; `fluxDerivativeThreshold=0.05` and `rmsDerivativeThreshold=0.02` are tuned for log-flux×20 / true-RMS deltas, not sqrt-novelty / normalised-mean deltas → **timbral/dynamic mis-scaled.** This is the WHY-v3-AP finding (`docs/research/2026-06-04-why-v3-AP-saliency-works.md`), confirmed not refuted. It explains the residual low precision after the gate fix.

### RC-3 (real, secondary) — Benchmark cannot exercise the design (single-axis collapse + wrong recall reference)
See §1b. Until the harness feeds distinct per-axis signals and scores against `segments/` boundaries, the per-axis question is **untestable** and any precision/recall verdict on the *detector* is unsafe. This is a measurement defect, not a detector defect — but it is load-bearing because it currently masks RC-2's true size.

### RC-4 (real, deepest, but not the headline blocker) — raw instantaneous novelty is low-SNR on continuous music
Probe-5 measured: novelty@beat 0.135 vs offbeat 0.134 (ratio 1.056) — near-zero instantaneous beat contrast ("clean on claps, chaos on songs"). BUT beat info lives in **periodicity**: ACF excess at the true beat-period lag = mean 0.133, positive on 86% of tracks. Implication: per-frame thresholding will never recover beats from this curve; a *beat/tempo-locked* primitive must be periodicity-based (the `sb_tempo.cpp` / ACF path). This bounds the ceiling of any instantaneous-saliency approach — but it is downstream of the headline FAIL and should be addressed only after RC-1/2/3.

**Debias check (both steelmen):** "Scorer is wrong" — TRUE in part (RC-3, impossible recall, axis collapse). "Detector is wrong" — TRUE in part (RC-1 gate is firmware; RC-2 mis-scale is firmware). The evidence does NOT support "irreducibly weak primitive": the gate-fix measurement falsifies that. It supports "concrete, fixable firmware bugs masked by a broken harness."

---

## 3. Concrete, sequenced FIX-PATH

Order is by measured leverage. Each step has a green checkpoint. saliency files are uncommitted — edit in place.

**Step 1 — RC-1 firmware gate (highest leverage, measured to flip 2 criteria).**
In `sb_musical_saliency.cpp`: (a) delete `adaptiveFloor`-as-EMA-of-OA + `threshold = 2*floor` (`:165,181`). Replace with EITHER (preferred) emit `overallSaliency` as a **continuous level** like the v3 donor and let the downstream consumer threshold, OR keep a discrete event but use a slow baseline floor (`0.995` EMA) + **fixed margin** (`th = floor + 0.15`) mirroring v3 `ControlBus.cpp:271-273`. (b) Add `if (audio.silence) { hold/zero axes; do not emit; }` at top of update. **Validated:** music_epm→55.94 PASS, silence_epm→0.0 PASS.

**Step 2 — RC-3 honest measurement (must precede any detector tuning).**
In the harness: (a) score events against `dataset/segments/*.txt` boundaries (parse col-0 like the beats loader at `:197-211`), not all 14908 beats; widen tol to ~1–2 s (section changes aren't beat-tight); make the 0.45/40–180 criteria mutually consistent. (b) Stop the single-scalar broadcast (`:57-67`) — derive distinct novelty / per-band energy / chroma-proxy columns from `novelty_from_wav.py`, OR down-scope the claim to a single-axis flux detector and label it as such. **Until this lands, do not trust any precision/recall number as a detector verdict.**

**Step 3 — RC-2 AP conditioning (the real detector repair).**
In `sb_audio_snapshot.cpp`, BEFORE writing fields: log-domain flux/novelty (`log1pf`), bounded compression `f/(1+f)`, fixed-scale RMS-style normalisation, and a Schmitt silence gate with hold (open ~0.02 / close ~0.005, per v3 `PipelineAdapter`/`ControlBus.cpp:749-775`). Then re-scale the three thresholds to the conditioned domain (do NOT keep v3's 0.5/0.05/0.02 verbatim): empirically set each from the music-clip distribution (p70–p85 of the measured per-frame delta), and rectify the **signed rising delta** instead of `|delta|` so events land on the onset, not the decay. Keep the saliency formula + asymmetric-smooth logic untouched — this is conditioning, not a formula rewrite.

**Step 4 — re-measure on the FIXED harness (Step 2), then validate on-device.**
Re-run `--json` after each step. compile ≠ runtime proof per project doctrine — close with serial/video evidence on K1. Do NOT change main `SAMPLE_RATE` (12800/96 = 133 Hz); use v3's decoupled-clock pattern if a separate novelty rate is needed.

**Step 5 (only if Step 4 still fails) — RC-4 periodicity primitive.**
If the conditioned instantaneous detector still can't carry musical relevance, move the musical primitive onto tempo/ACF tracking (`sb_tempo.cpp`), since instantaneous contrast is 1.056× but ACF is +0.13 on 86% of tracks.

---

## 4. Single highest-value next experiment

**Land Step 1 (the gate fix) and Step 2a (segments-based recall) together, then re-run `--json`.** Rationale: Step 1 is already measured to flip music/silence rate; pairing it with the segments reference is the *one* experiment that converts the benchmark from "structurally-failing, uninterpretable" into "honest detector measurement," and will size RC-2's true residual. If precision against segment boundaries clears ~0.4–0.5 after Steps 1+2 (gate + honest scorer, no conditioning yet), RC-2 is a tuning job; if it stays ~0.21, RC-2 conditioning (Step 3) is load-bearing and Step 5 (periodicity) becomes likely. Either outcome decisively re-ranks the remaining work — that is the maximum information per unit effort.

---

## 5. Delegation ledger (load-bearing parallel work consumed)

| Probe | Classification | Evidence produced | How consumed |
|---|---|---|---|
| benchmark-audit-fix | load-bearing | Reproduced metric; named RC-1 gate; corrected-gate re-run (8× recall, music PASS) | RC-1 (dominant); fix Step 1 — **independently re-measured by me** |
| REAL build+test+bench | load-bearing | pio SUCCESS, 123 tests pass; RC-3 axis collapse + recall category error | §1a (build real), RC-3 |
| scale-mismatch | load-bearing | Source-anchored 0.5/0.05/0.02 mis-scale; harmonic-dead | RC-2 |
| conditioning-gap | load-bearing | v3 log1p/compression/Schmitt vs fork raw; donor anchors | RC-2; Step 3 |
| proxy-weakness | load-bearing | Proxies SECONDARY; impossible-recall math; no silence gate | RC-1/RC-3 ranking |
| raw-feature-on-music | load-bearing | Instantaneous contrast 1.056×, ACF +0.13/86% | RC-4; Step 5 |

All six reproduced the headline metric in the live env; convergence is high. I verified the dominant claim by my own gate-only re-run (not transcription). No probe was missing/blocked.

## 6. Update — 2026-06-04: Steps 1+2a executed & measured (the decisive experiment)

Step 1 (gate) + Step 2a (segments reference + a new boundary-lift discriminator) landed on
`wip/audio-saliency-recovery` and re-ran on all 36 tracks. Real-env green: `pio run -e
k1_hardware` SUCCESS (21.2 s, RAM 27.7%, Flash 9.0%), `pytest tests/` 123 passed.

**Gate fix validated (RC-1 closed).** music_epm 18.28 → **75.41 (PASS)**, silence_epm 24.46 →
**0.0 (PASS)**, events 217 → 895 (all in music). The v3-faithful fixed-floor gate (`floor + 0.15`,
0.995 EMA) + the early `audio.silence` gate behave as the donor implies. Independent, keepable
improvement regardless of the structure verdict below.

**Decisive discriminator — boundary_lift = 0.977 (≈1.0; FAIL vs ≥1.5).** A NEW rate-free probe,
added to avoid a fresh bent scale: a dense ~75-epm event stream structurally caps
precision-vs-sparse-boundaries at ~0.2 regardless of detector quality, so segment-precision cannot
be a detector verdict. Lift = mean overallSaliency within ±1.5 s of a section boundary ÷ mean
elsewhere, music frames only: near 0.4271 / far 0.4372 over 18.7k / 76.2k frames. **overallSaliency
is NOT elevated at section boundaries** → the detector, as fed, carries ~zero musical-structure
signal. recall_segments 0.131 (56/428 boundaries hit within 1.5 s); precision_segments 0.063 and
precision_beats 0.2145 (unchanged — gate doesn't move precision, as predicted).

**Attribution (edge-honest).** Measured on the RC-3-collapsed harness (raw `novelty` broadcast into
all 4 axes). So it proves **novelty-flux is structure-blind** (confirms RC-4: instantaneous novelty
1.056× on beats, now ~0.98× on sections) — it does NOT yet test whether the real per-axis signals
(chroma-change=harmonic, energy-change=dynamic) lift at boundaries; the broadcast prevents it.

**Re-rank (the §4 decision, resolved):** precision did not clear 0.4–0.5 and lift ≈ 1.0, so
"RC-2 tuning-only is sufficient" is falsified. Next decisive sub-experiment is **Step 2b**: feed
distinct per-axis columns (novelty / per-band energy / chroma surrogate from `novelty_from_wav`)
and re-measure boundary_lift **per axis**. If a real axis lifts → RC-2 conditioning can recover the
primitive; if no axis lifts → the instantaneous approach is dead and the musical primitive moves to
**periodicity/ACF (Step 5, `sb_tempo`)** — the saliency result feeds the tempo lane (the "1 feeds 2"
sequencing). Evidence: `/tmp/sal_asis.json` (baseline), `/tmp/sal_fix.json` (this run).

## 7. Update — 2026-06-04: Step 2b executed — RC-2 vs RC-4 DECIDED (→ RC-4)

Step 2b fed the REAL per-axis signals (killed the RC-3 broadcast): `novelty_from_wav.wav_to_features`
now emits real `spectral_energy` (energy level) + `chroma_strength` (12-bin chroma concentration)
alongside novelty/silence, and the harness assigns each `SBAudioSnapshot` field from its own column.
Added the **RC-4 decider**: boundary-lift of each RAW per-feature delta (pre-threshold, so the engine's
thresholds cannot mask the signal), measured at a tight ±250 ms window (raw deltas are transient — a
wide window would dilute a real spike; I audited my own scale by also running ±1.5 s).

**Verdict — RC-4 confirmed; RC-2 falsified as the blocker.** No raw per-feature delta lifts at section
boundaries, at either window:

| feature delta | lift @±250 ms | lift @±1.5 s |
|---|---|---|
| chroma_strength | 1.031 | 1.024 |
| novelty | 0.976 | 1.015 |
| spectral_energy | 0.948 | 0.885 |

(all below the 1.2 "signal exists" bar). Engine overallSaliency boundary_lift with the real columns =
**0.9615** (still ≈1.0 — de-broadcasting did NOT help). Two independent measurements (raw deltas + the
smoothed engine output), two window widths — all flat.

**Meaning.** The instantaneous per-frame features the fork's saliency engine consumes carry ~zero
section-boundary structure. This is RC-4 (signal absent), **not** RC-2 (thresholds saturating a present
signal) — so conditioning/rescaling (Step 3) has nothing to extract. Instantaneous saliency cannot be
the musical-structure primitive. (Scope: this indicts the *instantaneous* approach; genuine structure
detectors use windowed/recurrence/periodicity methods — which is exactly the next lane.)

**The 1→2 hand-off, resolved with data.** The musical primitive moves to PERIODICITY/ACF (Step 5,
`sb_tempo`), where RC-4 already showed the signal lives (ACF excess +0.13 on 86% of tracks) — the
saliency result feeds the tempo lane (the Captain's "1 feeds 2"). Steps 3 (conditioning) + 4 (device)
of the original fix-path are **superseded for this primitive**: a conditioned instantaneous detector
would only sharpen contrast that isn't there. The RC-1 gate fix (§6) is kept as a correct, independent
improvement. Evidence: `/tmp/sal_2b2.json`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:synthesiser | Created — synthesis of 6 probes + independent live-env reproduction (as-is + gate-only re-run) into ranked diagnosis and sequenced fix-path |
| 2026-06-04 | agent:CTO | Update §6 — executed Steps 1+2a; RC-1 gate fix validated (music/silence epm PASS); boundary_lift 0.977 = novelty-flux is structure-blind; next = Step 2b per-axis, periodicity (Step 5) likely. |
| 2026-06-04 | agent:CTO | Update §7 — Step 2b decided RC-2 vs RC-4 → RC-4 (no raw feature delta lifts at boundaries @250ms/1.5s; engine real-column lift 0.96). Instantaneous saliency is structure-blind; primitive moves to periodicity/ACF (Step 5). Steps 3/4 superseded for this primitive. |
