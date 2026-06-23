---
abstract: "Implementation spec + LIVE LOG for hardening SensoryBridge K1 tempo LOCK on real music. SEE THE 2026-06-03 (PM) UPDATE SECTION FIRST — it revises the original premise with real-music measurement. Original premise (now corrected): the gap is octave/half-tempo defence. MEASURED reality (digital HarmonixSet pipe, 36 tracks): the dominant failure is the GOERTZEL TEMPO SPECTRUM — committed detector Acc2 14-17% vs a 50% autocorrelation ceiling on the SAME novelty; octave error is only ~6%. Step 2 implemented in sb_tempo.cpp (host-validated, ESP32 build OK, metronome lock preserved): log-Gaussian tactus prior (octave-err->0) + Goertzel un-clamp (the real ~2x win: in-range Acc1 9.4->25%, Acc2 15.6->28%). Remaining gap is ARCHITECTURAL (Fourier-vs-autocorrelation); recommended next = ACF-salience + prior hybrid inside sb_tempo. Validation pipe: scripts/regression-harness/tempo_accuracy.py + the baseline report docs/measurements/tempo-octave-baseline.md. Read before touching sb_tempo."
---

# Tempo-Lock Hardening Plan (SensoryBridge K1, `feat/gdft-harness`)

## Where we are — committed `684a547` (host-validated, NOT yet real-music-validated)
- **Detector is correct & stable:** exact-frame-count novelty decimation (44.4 Hz, coeffs matched → 120 reads 120, on-device dead-locked); phase fixed (beat at phase≈0); **out-of-lobe confidence** `peak²/(peak²+Σ out-of-lobe bin²)`, lock threshold 0.60. Host harness `scripts/regression-harness/tempo_replay.py` — 7/7 cases pass (clean/noisy/tempo-change LOCK at conf≈0.99; drone 0.47 & silence reject).
- **Class is right** [SW1]: Scheirer'98 / Klapuri'06 / Emotiscope resonator-bank-over-novelty; rate discipline + finite-block recompute are textbook-correct. ACF rightly abandoned (sub-harmonic mode-lock).

## The gap (trawl + swarm, unanimous)
The detector measures **peakiness/continuity, not correctness**, and has **zero octave/half-tempo defence** — THE documented #1 failure of this algorithm class ("42 BPM beats true 114"; "85 BPM ghost on a 132 track"). A clean metronome never aliases, so synthetic tests can't surface it; **real music with strong off-beats will.** This is what must be closed before declaring the lock done.

## Prioritised fixes (the COMBINE)
1. **OCTAVE DEFENCE — load-bearing** [SW1 + trawl]
   - Add an **Ellis-style log-Gaussian tempo prior** (preferred ~120 BPM, ≈1 multiply/bin) weighting bin magnitudes before winner selection — biases against octave/half-tempo errors cheaply.
   - **Reduce/replace the ad-hoc quartic exaggeration** (`sb_tempo.cpp:245-246`): it discards tempo-spectrum shape and *amplifies whatever is tallest, including sub-harmonics*.
   - **SW2 design (USE THIS — do NOT copy firmware-v3's 5 magic-number patches in `vendor/tempo.h:372-443`, they're keyed to ESV11's confidence scale):** two stages, both O(96), in `sb_update_winner` only (leave magnitudes/phase/confidence untouched):
     - **Stage A — log-Gaussian tactus prior:** precompute `prior[i]=exp(-0.5*((log2(bpm_i)-log2(120))/SIGMA)^2)`, SIGMA≈0.9–1.0 octaves; multiply `sb_tempi_smooth[i]*prior[i]` in the winner search. Symmetric in log2 → ÷2 and ×2 penalised equally; gentle at 60–156 (≈1.0@120, ≈0.85@60/156) — breaks ties toward the tactus, never forces.
     - **Stage B — confidence-gated half/double arbiter:** after A picks w, if `confidence>~0.5`, compare prior-weighted scores of bin(bpm_w/2) and bin(bpm_w*2) (in-range) vs w; switch with the same +10%/persistence hysteresis. Anchored by the prior (what firmware-v3 lacks).
     - Two tunables only: SIGMA, CONF_GATE — perceptually motivated, not magic numbers.
   - Heavier option if ever needed: Klapuri harmonic summation across T/2,T,2T.
2. **OCTAVE-AWARE CONFIDENCE** [SW4]: fold the half/double-tempo bins into the lobe-exclusion so octave **agreement** isn't counted as competition (today it wrongly depresses confidence on strongly-metrical material). Keep the out-of-lobe form — it's sound (a band-limited energy-concentration / IPR / Rényi-2-family measure; beats 2 of firmware-v3's 3 confidence legs).
3. **LOCK STATE MACHINE** [SW4]: replace the bare `e.locked = conf>0.60` (`:326`) with searching→locking→locked:
   - **Schmitt thresholds**: enter at 0.60, **exit at ~0.40** (the measured drone floor). Between → stay locked.
   - **Minimum hold/dwell** (~5–8 frames, mirror the winner-bin hysteresis) before LOCKED and before unlock.
   - **Tempo change ≠ unlock**: let `sb_update_winner` re-elect the bin while `locked` stays true; only silence/true-collapse unlocks. (Delivers "lock and STAY".)
   - NOTE: the out-of-lobe 0.999 is partly an artefact of the x⁴ pre-emphasis — treat confidence as a GATE, not a calibrated salience.
4. **NOVELTY QUALITY** [SW3] — highest-impact input fix, but **AP-class (touches `GDFT.h`) → separate, careful, build+host-validate, full change-gate:**
   - Feed the tempo bank **log-domain flux on PRE-AGC / PRE-CLAMP magnitudes** (our own ADR-002), not the current AGC-saturated `[0,1]`-clamped linear one-frame-lag broadband flux (`GDFT.h:269-331`). Log gives 10–80× onset/steady contrast vs 5–20× linear; the `[0,1]` clamp removes the transient peaks tempo needs.
   - Optional: SuperFlux max-filter (vibrato), sliding-window-mean threshold (not EMA), bass-weighting (genre-dependent).

## Validation — "pipe real music through the code" [SW5 — design final]
- **100% DIGITAL — no mic, no speaker, no sound played, no player, no K1/bench.** The WAV's *samples* are processed by code on the dev machine; `sb_tempo` runs as a HOST binary and prints detected BPM. Acoustic/mic path bypassed entirely.
- **Why it's valid [SW5]:** `sb_tempo` consumes only the *temporal shape* of novelty (internally normalised) → host novelty just needs to be *representative*, NOT a bit-exact GDFT replica. Octave aliasing lives in onset periodicity, which spectral flux preserves. (Bit-exact GDFT replica / host-compiling GDFT = high effort, no extra value for tempo — defer as optional cross-check only.)
- **Pipe (option a, ~1 day):** `ffmpeg -i track -ac 1 -ar 12800 → WAV`; novelty = `onset_strength(sr=12800, hop_length=96, fmin=110, fmax=4186, aggregate=mean, lag=1)` then `sqrt(max(·,0))` = one value per 96-sample hop = native **133.33 Hz** frames; emit CSV `[frame_ms, novelty, silence]` (silence=1 when frame RMS<floor); **do NOT pre-decimate** (sb_tempo does its own ÷3). librosa (`pip install librosa soundfile`) OR hand-roll the same operator with scipy STFT (numpy 2.4.1/scipy 1.17.1/ffmpeg 8.0.1 already present; librosa/soundfile NOT).
- **Harness:** add `run_file(csv)` to `tempo_replay.py`'s C++ main, replaying frames through unmodified `sb_tempo.cpp` (reuse stub + `-DSB_TEMPO_HOST_TEST` + `sb_tempo_debug_dump`); emit BPM trajectory.
- **Score:** MIREX **Acc1 (±4%) + Acc2 (octave-tolerant)** + per-track octave ratio. **`Acc2−Acc1` IS the octave-error rate** — a correct octave fix raises Acc1 toward Acc2 with Acc2 flat.
- **Corpus:** start with self-generated stems (numpy/soundfile) at 90/120/140/174 BPM + deliberate half-time/double-time/offbeat traps (zero licensing). Then on-disk **HarmonixSet** `Lightwave-Ledstrip/firmware-v3/test/music_corpus/harmonixset/esv11_benchmark/audio_12k8/*.wav` (real, 12.8 kHz, ground-truth) + GiantSteps-EDM. Reggae/dub/DnB(~174)/hip-hop(~90) are the strongest octave traps.
- This is the ONLY thing that exposes octave aliasing → it gates "lock is done".

## Keep — do NOT regress
Out-of-lobe confidence (sound); exact-rate decimation; finite-block recompute (dodges Goertzel marginal-stability); silence release; phase-from-resonator + debounce; the 60–156 BPM range (implicit single-octave guard).

## Swarm status
COMPLETE — all 5 in (SW1 induction, SW2 octave, SW3 novelty, SW4 lock/confidence, SW5 validation). This doc IS the full implementation spec. Implement in one principled pass; validate on the corpus (host, digital, no bench).

## Implementation order (when resuming — all host-validated, no bench)
1. Build the real-music host pipe (SW5) — `novelty_from_wav.py` + `tempo_replay.py run_file()` + Acc1/Acc2 scorer + synthetic-trap stems. Establishes the BASELINE octave-error rate of the current detector (expect a wide Acc2−Acc1 gap).
2. Octave defence (SW2 Stage A log-Gaussian prior, then Stage B arbiter); reduce the quartic. Re-score → Acc1 should rise toward Acc2.
3. Octave-aware confidence (fold half/double into lobe) + Schmitt lock state machine (SW4: enter 0.60/exit 0.40 + dwell).
4. (Separate, AP-class, full change-gate) log-domain novelty (SW3) in GDFT.h — biggest input fix, highest blast radius; do last, build + host-validate.
5. Then on-device eyes-on (Captain) + the production light mode.

---

## Update — 2026-06-03 (PM): real-music baseline MEASURED + Step 2 implemented (host)

The digital pipe is built and run (Step 1 ✓, commit `134c872`); Step 2 is implemented and
host-validated. The measurement **revises this plan's premise**.

### What the real-music measurement showed (the premise revision)
The plan assumed "the detector class is right; the gap is octave/half-tempo defence." The
real-music corpus (which the plan lacked) says otherwise. Baseline of the committed detector
(`684a547`), 36 HarmonixSet tracks vs gold human BPM, digital host pipe:

| | committed `684a547` (before) | Step 2 (after) |
|---|---|---|
| in-range Acc1 (exact, ±4%) | 9.4% | **25.0%** |
| in-range Acc2 (octave-tolerant) | 15.6% | **28.1%** |
| octave-error rate (Acc2−Acc1) | 6.2% | 3.1% |
| autocorrelation ceiling (same novelty) | **Acc2 50%** | Acc2 50% |
| raw Goertzel-spectrum Acc2 (localiser) | 17% | — |

- **The dominant failure is NOT octave error (only ~6%) — it is the Goertzel TEMPO SPECTRUM.**
  A plain autocorrelation of the *same* novelty reaches Acc2 50%; the committed detector
  extracts 14–17%. The winner-selection/spectrum is the bottleneck, not the novelty (novelty
  ceiling is high) and not octave disambiguation (small). The detector that locks flawlessly on
  a synthetic metronome (conf 0.999) is **largely lost on real music.**
- Localised by dumping the raw (pre-quartic) Goertzel magnitudes: raw-spectrum Acc2 = 17% = the
  winner's 17%, i.e. the loss is upstream of the quartic/smoothing/selection, in the Goertzel
  computation itself — below even a clean Fourier tempogram (25%).

### Step 2 as implemented (in `sb_tempo.cpp` only; metronome lock preserved by construction)
1. **Log-Gaussian tactus prior** (~120 BPM, SIGMA 0.9 oct) applied in `sb_update_winner` on a
   **de-sharpened (^0.25, undo the quartic for SELECTION only)** magnitude. Confidence/phase/
   quartic untouched → the metronome's raw-max bin is unchanged → lock + conf 0.999 preserved.
   This was the planned octave defence; on its own it drove octave-error 6.2%→0 but barely moved
   Acc2 — because octave error was never the main problem.
2. **Goertzel un-clamp (NEW — not in the original plan).** The Goertzel input had a `[0,1]` clamp
   (`sb_compute_magnitude`) while the autoranger scales the curve's max to ~2.0, so it
   soft-limited the top half of every onset peak into a near-square wave, distorting the spectrum.
   Raising the ceiling to `4.0` (2× headroom, still a limiter) lifted Acc2 17%→25–28%. **This,
   not the prior, is what doubled accuracy.**

Both verified host-only (no bench): synthetic suite 7/7 (metronome still conf 0.999, lock=1),
corpus as table above, ESP32 `pio run -e k1_hardware` SUCCESS (Flash 9.0%, RAM 27.7%). On-device
runtime proof remains queued for the final Captain eyes-on (compile/host ≠ device runtime).

### The remaining gap is ARCHITECTURAL (the next decision)
Even fully tuned, a Goertzel/Fourier tempogram caps **~30% Acc2** on this corpus; autocorrelation
reaches **50%**. The residual ~20 pts is the Fourier-vs-autocorrelation gap (Fourier scatters a
beat's energy across harmonics; ACF concentrates it at the fundamental). Options to close it,
in rising effort/blast-radius:
- **(a) Harmonic summation** (Klapuri; the plan's deferred "heavier option"). Prototyped on the
  raw spectra: +3–6 pts Acc2 (→~30%). Within `sb_tempo.cpp`. Modest; carries a subharmonic-bias
  risk the prior must counter. **Not yet implemented.**
- **(b) ACF/comb tempo salience inside `sb_tempo`** (Goertzel kept for phase). ACF reaches Acc2
  50% but Acc1 only 17% (the sub-harmonic mode-lock the plan rightly feared) — so ACF salience +
  the log-Gaussian prior to pin the octave is the principled hybrid. Larger redesign; ~50× the
  per-emit compute of the current 2-bins/tick Goertzel (still ≈1% CPU @ 240 MHz, needs a perf read).
- **(c) Novelty quality (SW3 / Step 4, GDFT.h)** — separate, highest blast radius, still open.

**Recommendation:** ship Step 2 (prior + un-clamp) as a real ~2× win now (done, this commit), then
pursue **(b) ACF-salience + prior hybrid** as the next focused effort — it is the only path the
data shows reaching the ~50% ceiling, and it stays inside `sb_tempo.cpp`. (a) is a cheap interim if
a smaller step is wanted first. Re-run any time: `python3 scripts/regression-harness/tempo_accuracy.py`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | Created — tempo-lock hardening spec from the prior-art trawl + algorithm-design swarm (3/5 reports). Captures the COMBINE plan (out-of-lobe confidence + octave defence + lock state machine + log-novelty) and the on-disk HarmonixSet real-music validation path, before context compaction. |
| 2026-06-03 | agent:claude-opus | Update (PM): real-music baseline MEASURED via the digital pipe — premise revised. Dominant failure is the Goertzel tempo SPECTRUM (Acc2 14–17% vs autocorrelation ceiling 50% on the same novelty), not octave error (~6%). Step 2 implemented in sb_tempo.cpp: log-Gaussian tactus prior (octave-err→0) + Goertzel un-clamp (the real ~2× win: in-range Acc1 9.4→25%, Acc2 15.6→28%). Metronome lock preserved; ESP32 build SUCCESS. Remaining gap is architectural (Fourier vs ACF); recommend ACF-salience+prior hybrid next. |
