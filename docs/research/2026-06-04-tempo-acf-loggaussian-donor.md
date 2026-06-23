---
abstract: "RECON (provisional, no edits) for porting ACF-salience + log-Gaussian tempo prior + half/double octave arbiter into the K1 fork's sb_tempo. KEY EDGE FINDING: the three designs do NOT all come from one donor. The v3 donor (firmware-v3 src/audio/tempo/TempoTracker) is a GOERTZEL resonator bank over log1p-conditioned, running-max-normalised-to-[0,1] novelty — it has NO ACF, NO log-Gaussian prior, NO octave arbiter. The log-Gaussian prior + half/double arbiter FORMS live in the FORK's docs/architecture/tempo-lock-hardening-plan.md (Stage A/B) and are ALREADY implemented in SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp (prior live; arbiter NOT yet). The ACF design is plan option (b), NOT YET IMPLEMENTED anywhere in firmware; the only running ACF is the host-harness CEILING estimator (scripts/regression-harness/tempo_accuracy.py:ac_ceiling_bpm). LOAD-BEARING domain mismatch: donor conditions novelty as log1p→running-max÷0.5→clamp[0,1]; harness as dB-flux→sqrt→p99-clip; live fork as clamp[0,1]→peak-hold-decimate→clamp[4.0]. A constant lifted from any one is wrong in the others. Read before any sb_tempo ACF/prior/arbiter port."
---

# Tempo ACF-salience + log-Gaussian prior + octave arbiter — donor recon

**Status: PROVISIONAL (recon only; no edits/flash/commit). British English.**
**Boundary crossed:** v3 donor `firmware-v3/src/audio/tempo` (Goertzel bank) AND the
fork's own `docs/architecture/tempo-lock-hardening-plan.md` (the ACF + prior + arbiter
DESIGN) → into `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp` (raw ~133.33→/3→44.44 Hz
novelty domain).

## 0 · The headline edge — which artefact actually owns each FORM

The brief assumes "the v3 donor computes ACF-salience + log-Gaussian prior + octave
arbiter." It does **not**. Provenance, verified by reading the producing regions:

| FORM | Where the FORM actually lives | Implemented? |
|------|------------------------------|--------------|
| ACF-salience over novelty | **Plan option (b)** (`tempo-lock-hardening-plan.md:108-111`) as a *design*; the only running ACF is the host **ceiling** estimator (`tempo_accuracy.py:159-176`). Donor has **none**. | **No** (design only) |
| log-Gaussian tempo prior | Plan **Stage A** (`:19`, `:85`); FORM live in fork `sb_tempo.cpp:380-385` + `sb_sel_score:219-223` | **Yes** (fork, committed) |
| half/double octave arbiter | Plan **Stage B** (`:20`) | **No** (planned; not in `sb_tempo.cpp`) |

The v3 donor `TempoTracker` is a **Goertzel resonator bank** (`TempoTracker.cpp:44-92`
init, `:330-388` IIR step) — a Fourier-family tempogram, the *same class* the plan says
caps ≈30% Acc2 and that ACF (50% ceiling) is meant to beat. So the donor is the
reference for the **novelty conditioning the prior/ACF presuppose**, not for the three
FORMs themselves. (§4 is where the failure-mode risk concentrates.)

---

## 1 · ACF-salience

### FORM (the only running implementation — host ceiling, `tempo_accuracy.py:159-176`)
```
x   = nov - mean(nov)                      # DC-remove the whole novelty vector
ac  = correlate(x, x, "full")[N-1:]        # one-sided biased autocorrelation, lag 0..N-1
ac[0] = 0                                  # kill the zero-lag spike
fps = SAMPLE_RATE/HOP = 12800/96 = 133.33  # << NOTE: ceiling runs on the 133.33 Hz curve
lo  = round(fps*60/hi_bpm)  (hi_bpm=210)   # shortest lag = fastest BPM
hi  = round(fps*60/lo_bpm)  (lo_bpm=55)    # longest  lag = slowest BPM
lag = lo + argmax(ac[lo:hi])               # single dominant lag — NO sub-harmonic merge
bpm = 60*fps/lag
```
This is a **lag-domain salience**: salience(lag)=ac[lag], picked by raw argmax over the
[55,210] BPM lag window. It is *biased* autocorrelation (np.correlate "full", no
1/(N−lag) unbiasing), so long lags are attenuated — a mild built-in bias *towards faster
tempi / shorter lags*, opposite to what a tactus prior wants.

### Plan's intended firmware ACF (option b, `:108-111`) — DESIGN, not yet coded
"ACF/comb tempo salience inside `sb_tempo` (Goertzel kept for phase). ACF reaches Acc2
50% but Acc1 only 17% (the sub-harmonic mode-lock) → ACF salience **multiplied by the
log-Gaussian prior** to pin the octave is the principled hybrid." So the production FORM
is `salience(bpm_i) = acf_at_lag(bpm_i) * prior[i]`, winner = argmax — NOT the bare argmax
the ceiling uses.

### LOAD-BEARING EDGES for ACF
- **Lag domain = frame rate.** `bpm = 60*fps/lag` is only correct if `fps` is the rate of
  the curve actually autocorrelated. The **ceiling autocorrelates the 133.33 Hz curve**
  (`fps=SAMPLE_RATE/HOP`, no /3). The **fork's Goertzel bank runs at 44.44 Hz** (post /3
  decimation, `sb_tempo.cpp:24`). If ACF is added inside `sb_tempo` it must run on the
  **same 44.44 Hz decimated ring** the Goertzel reads (`sb_spectral_curve`), so
  `fps_acf = 44.444`, and the lag window becomes `lag∈[round(44.444*60/210),
  round(44.444*60/55)] = [13, 48]` — only ~36 integer lags span 55–210 BPM. **EDGE: at
  44.44 Hz the lag grid is coarse — ±1 lag near 174 BPM is ≈±13 BPM.** Sub-bin
  (parabolic) lag interpolation is likely required to hit Acc1; the ceiling dodges this by
  running at 3× the rate. UNCERTAIN whether 44.44 Hz ACF alone preserves the 50% ceiling —
  the 50% was measured at 133.33 Hz.
- **Mean-removal scale.** `x = nov - nov.mean()` presupposes a **bounded, roughly
  stationary** novelty so the mean is meaningful. The donor's curve is `log1p`-compressed
  and running-max-normalised (§4); the fork's live curve is `[0,1]`-clamped then
  peak-hold-decimated (§4). ACF salience MAGNITUDE is not comparable across these — only
  the *argmax lag* transfers. **EDGE: port the lag-pick, re-derive any salience threshold
  in the fork's own domain.**
- **Biased vs unbiased.** The ceiling uses biased ACF (no `/(N−lag)`); a firmware port
  that "fixes" this to unbiased will shift the balance toward slow tempi and change which
  octave wins — i.e. it interacts with the prior. **EDGE: the prior was tuned against
  biased-ACF / Goertzel behaviour; changing the ACF normalisation re-opens octave tuning.**
- **Window length.** Ceiling uses the whole replayed novelty vector (whole track). In
  firmware the ring is finite (`SB_SPECTRAL_HISTORY` — donor `SPECTRAL_HISTORY_LENGTH`
  ~128 samples ≈ 2.9 s at 44.4 Hz). **EDGE: a 2.9 s window at 44.4 Hz only holds ~2.5
  cycles of a 55 BPM beat → low-BPM ACF salience is statistically thin; the donor's
  Goertzel sidesteps this with per-bin adaptive block sizes (`TempoTracker.cpp:74-79`).**

---

## 2 · log-Gaussian tempo prior

### FORM (live in fork, `sb_tempo.cpp:380-385`; design `plan:19`)
```
# precomputed once per bin, BPM domain:
l2        = log2f(bpm_i / SB_TACTUS_BPM) / SB_TACTUS_SIGMA
prior[i]  = expf(-0.5f * l2 * l2)                    # Gaussian in log2-BPM space
# applied ONLY in winner selection (sb_sel_score:219-223):
sel_score(i) = sqrtf(sqrtf(sb_tempi_smooth[i])) * prior[i]
```
- **Centre:** `SB_TACTUS_BPM = 120.0` BPM (perceptual tactus). Plan: ~120 (`:19,:85`).
- **Sigma:** `SB_TACTUS_SIGMA = 0.9f` **octaves** (log2 units), plan says 0.9–1.0 oct
  (`:19`). Symmetric in log2 ⇒ ÷2 and ×2 penalised equally; ≈1.0 @120, ≈0.85 @60/156.
- **Critical companion edge — the quartic de-sharpen.** The prior is multiplied onto
  `sqrtf(sqrtf(sb_tempi_smooth[i]))` i.e. `m^0.25`, NOT onto `m`. `sb_tempi_smooth` was
  raised to x⁴ in `sb_update_tempo` (`:283`), so `^0.25` undoes it back to ~linear
  magnitude *for selection only*; confidence/beat_strength still read the x⁴ value
  (`:365`). **The prior is described as "≈1 multiply/bin" but is INERT without this
  de-sharpen** — on raw x⁴ magnitude the tallest bin dominates by 4 orders and the gentle
  prior cannot move it (`plan:59` "the prior is powerless against x⁴ alone"). This is the
  load-bearing FORM edge: *prior ⇒ de-quartic precondition*.

### LOAD-BEARING EDGES for the prior
- **Domain of the constant is BPM, not novelty-amplitude.** `120` and `0.9` live in
  `log2(BPM)` space and are **independent of the novelty conditioning / frame rate** — this
  is the one constant family that ports cleanly across the 133→44 Hz change, because it is
  computed from `bpm_i = TEMPO_LOW + i` (`:47` donor / fork bin BPM table), not from the
  signal. **EDGE: SIGMA is octaves; never re-derive it from a frame-rate change.** It only
  needs retuning if the BPM *range/spacing* changes (fork range, see below).
- **Multiplicative weight, not additive.** It scales magnitudes pre-argmax; it cannot
  create a peak, only break ties / re-weight existing peaks (`plan:19` "breaks ties toward
  the tactus, never forces"). **EDGE: presupposes the true-tempo bin already has non-trivial
  magnitude — useless if the spectrum has no peak there (the ACF-vs-Fourier gap §1).**
- **Range coupling.** Donor BPM range is 48–143 (`TempoTracker.h:50-53`, single-octave
  guard); plan cites a 60–156 effective band (`:19`). The fork's `SB_NUM_TEMPI`/`TEMPO_LOW`
  set the actual grid. **EDGE: prior shape (≈0.85 at the band edges) was chosen for that
  span; widening the range past one octave re-admits the octave ambiguity the prior alone
  cannot resolve — that is exactly why Stage B (arbiter) exists.** UNCERTAIN: exact fork
  `TEMPO_LOW`/`SB_NUM_TEMPI` not read in this pass; verify before assuming 120 sits mid-band.

---

## 3 · octave (half/double) arbiter

### FORM (plan Stage B, `:20`; NOT implemented in `sb_tempo.cpp`)
```
after Stage-A picks winner w, IF confidence > CONF_GATE (~0.5):
    compare prior-weighted sel_score of bin(bpm_w / 2) and bin(bpm_w * 2)  [if in range]
                                          vs sel_score(w)
    switch to the half/double candidate with the SAME +10% / persistence
    hysteresis used by the main winner search (best > current*1.1, 5 consecutive ticks)
```
- **Ratio test:** only the two exact octave-related bins (÷2, ×2) are challengers, not all
  bins — a targeted octave correction anchored by the prior (`plan:20` "anchored by the
  prior — what firmware-v3 lacks").
- **Two tunables only:** `SIGMA` (shared with Stage A) and `CONF_GATE` (~0.5)
  (`plan:21`). Resolution rule = prior-weighted score comparison + existing hysteresis.

### LOAD-BEARING EDGES for the arbiter
- **`confidence` is a GATE, not a calibrated salience.** `CONF_GATE≈0.5` reads the fork's
  out-of-lobe confidence `peak²/(peak²+Σ out-of-lobe bin²)` (`sb_tempo.cpp:36,304-315`),
  which the plan flags as **partly an artefact of the x⁴ pre-emphasis** (`:28` "the
  out-of-lobe 0.999 is partly an artefact of x⁴; treat confidence as a GATE, not a
  calibrated salience"). **EDGE: CONF_GATE's numeric value is meaningful ONLY against this
  exact x⁴-inflated confidence; if Step-2's de-quartic or SW4's octave-aware confidence
  (`plan:23`, fold half/double bins INTO the lobe) lands, the confidence distribution
  shifts and 0.5 must be re-derived.** Do not transcribe 0.5 verbatim if confidence form
  changes.
- **Bin-existence at ÷2/×2.** `bin(bpm_w/2)` and `bin(bpm_w*2)` must be IN the BPM grid;
  with a ~60–156 single-octave range many winners have only ONE octave neighbour in range.
  **EDGE: the arbiter's reach is bounded by the same range coupling as the prior (§2);
  it presupposes the grid actually contains the octave partner.**
- **Double-counting interaction (SW4).** Plan `:23` separately proposes folding ÷2/×2 bins
  into the confidence lobe-exclusion so octave *agreement* stops depressing confidence.
  **EDGE: Stage B (arbiter) and SW4 (octave-aware confidence) both touch the ÷2/×2 bins;
  landing one changes the input to the other — sequence and re-measure, do not land blind.**

---

## 4 · The 3–4 edges that MUST be re-derived for the fork (each with its assumed domain)

The failure mode this recon exists to prevent: lifting a constant out of the conditioning
regime it was tuned in. There are **three incompatible novelty regimes** in play:

| Regime | Conditioning chain | Domain seen by ACF/prior |
|--------|--------------------|--------------------------|
| **Donor** (`TempoTracker.cpp:203,206-211,295-312,350-353`) | `log1p(mean half-wave flux)` → ×NOVELTY_DECAY(0.999) → `normalizeBuffer` (running-max ÷0.5, tau=0.3 EMA of scale) → **clamp [0,1]** | log-compressed, running-normalised, [0,1] |
| **Harness** (`novelty_from_wav.py:85-117`) | **dB**-magnitude spectrogram (20·log10, TOP_DB=80 floor) → half-wave flux → drift-remove (3 s box) → **sqrt** → p99-clip | dB-flux, sqrt-compressed, p99-bounded |
| **Live fork** (`sb_tempo.cpp:437,450,467; 162,196`) | `audio.novelty` → **clamp [0,1]** → peak-hold /3 decimate → Goertzel reads clamp [0,1] (`:162`) but un-clamp lane uses **clamp [4.0]** (`:196`) | **bounded, NOT log-conditioned**, peak-held |

**Re-derive these before porting (each names the domain/scale it assumes):**

1. **ACF `fps` / lag window — assumes the rate of the curve being correlated.** Ceiling
   assumes **133.33 Hz**; an in-`sb_tempo` ACF runs at **44.44 Hz** → lag window collapses
   to ~[13,48] integer lags for 55–210 BPM. Re-derive `lo/hi` from 44.444, add sub-lag
   interpolation, and re-confirm the 50% ceiling survives at 44.4 Hz (it was measured at
   133.33). **Do NOT copy lo=55/hi=210 BPM as if the lag count were the same.**

2. **Novelty conditioning the ACF/prior presuppose — assumes log-compression + running
   normalisation.** The 50% ACF ceiling and the donor's whole tempo bank were measured on
   **log-/dB-compressed, normalised** novelty (donor `log1p`+`normalizeBuffer`; harness
   `dB`+`sqrt`). The **live fork feeds raw `[0,1]`-clamped, peak-held** novelty — *not*
   log-conditioned (the plan's SW3/Step-4 GDFT log-novelty fix is **still open**,
   `plan:29-30,112`). **An ACF salience threshold or peak-prominence cut tuned on the
   compressed curve will mis-fire on the bounded raw curve.** Re-derive any ACF
   salience/prominence threshold in the fork's own clamp[0,1]/peak-hold domain, or first
   land the log-novelty (SW3) so the regimes match. THIS is the canonical edge-drop risk.

3. **`CONF_GATE` (octave arbiter) — assumes the x⁴-inflated out-of-lobe confidence.**
   0.5 is calibrated against `peak²/(peak²+Σout²)` on x⁴ magnitudes (`sb_tempo.cpp:304-315`,
   `plan:28`). Any change to the quartic or to octave-aware confidence (SW4) shifts the
   confidence distribution → re-derive 0.5. **It is NOT a physical 50%-probability gate.**

4. **The de-quartic precondition for the prior — assumes magnitudes were x⁴-pre-emphasised.**
   `sb_sel_score` applies `m^0.25` *because* `sb_tempi_smooth` is x⁴ (`:283`). If a port
   feeds the prior raw/linear magnitude (e.g. an ACF salience that was never quartic'd),
   the `^0.25` is WRONG and will over-flatten. **EDGE: the prior's exponent on its input is
   coupled to whatever pre-emphasis produced that input — re-derive the de-sharpen for the
   ACF path; do not reuse `sqrtf(sqrtf())` blindly.**

(Range coupling — fork `TEMPO_LOW`/`SB_NUM_TEMPI` vs donor 48–143 / plan 60–156 — is a
fifth edge to confirm but is UNCERTAIN in this pass; it bounds both the prior band-edge
weight and the arbiter's ÷2/×2 reach.)

---

## 5 · Clean port, or condition first?

**NOT a clean drop-in.** The log-Gaussian **prior is already ported and is the cleanest
piece** (its constants live in BPM/log2 space, frame-rate-independent) — but only because
it carries its de-quartic precondition. The **ACF-salience is the opposite**: its FORM is
trivial, but its load-bearing edges (lag-rate, biased-vs-unbiased, and above all the
**log/normalised novelty conditioning the 50% ceiling was measured on**) all assume a
domain the **live fork does not currently produce** — the fork feeds raw, `[0,1]`-clamped,
peak-held, **un-log-conditioned** novelty. Porting ACF onto that raw domain without first
either (a) landing the log-novelty (SW3/GDFT.h, plan Step 4) or (b) re-deriving every ACF
salience/lag/threshold constant in the fork's bounded domain will reproduce exactly the
edge-incomplete failure the brief warns about: the FORM will be right and the constants
will be silently in the wrong domain. **Recommendation: treat the prior as ported (CANON
once re-measured on the fork range), but treat ACF as PROVISIONAL — condition the novelty
(or re-derive in-domain) BEFORE trusting any lifted ACF constant.**

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:T2-recon | Created — load-bearing-edges recon of ACF-salience / log-Gaussian prior / half-double arbiter for the sb_tempo port. Provenance corrected (donor is Goertzel-only; ACF+arbiter are plan-only, prior is fork-live); three incompatible novelty conditioning regimes identified; four+ edges flagged for re-derivation onto the fork's raw 133.33→44.44 Hz domain. PROVISIONAL — no edits/flash/commit. |
