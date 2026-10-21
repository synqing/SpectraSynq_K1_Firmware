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

## Update — 2026-10-20: Main RPL "weak lock" is a false silence inside the tracker; input-contrast fix measured, not merged

Measured on `k1_main_rpl_im69d` (k1_tempo.cpp: ACF spread + CONF_V2 + flywheel; novelty
from `calculate_novelty()` in `audio/k1_gdft_core.cpp`, which replaced the `GDFT.h` lines
cited above). Firmware `aaa1f307`; emulator replay `tools/esp_emulator` (esp-emu 0.49.0);
host replay = unmodified `k1_tempo.cpp` with the product defines.

**Mechanism (FACT).** On the R3 music passage (loreen_127, scored hops 1600-2933) the
tracker *does* lock internally: `k1_locked_v2` is true on 100 % of scored frames at 127 BPM,
`k1_conf_ema` 0.81 mean / 0.95 max. Its own novelty-contrast silence detector
(`k1_tempo.cpp` ~509-535: `1-(max-min) > 0.5` over the last 128 normalised emits) declares
silence on 100 % of those frames although the producer's silence flag is 0 throughout. The
output gates then hide everything: `locked && !silence`, `beat_tick && !silence`, confidence
× `(1 - silence_level)`. Result: 0 published locks, 0 ticks, max published confidence 0.664 —
the retained `PASS_timing_but_weak_lock`. Instrumented with `ENABLE_TEMPO_STREAM` debug
fields on the host; host replay of the emulator's captured novelty reproduces the emulator's
published tempo exactly.

**Why the contrast is low (FACT).** The tempo input is `sqrtf(novelty_now)`
(`k1_gdft_core.cpp:737`). The square root compresses the onset/steady contrast (p90/p10
6.9 → 2.6 on this passage); the loud-guard GDFT trim (mean 0.62 here) already squeezes the
spectrogram it is computed from. Without the square root the silence detector stays off.

**Candidate measured (FACT).** `K1_TEMPO_NOVELTY_LINEAR_V1`: the pre-sqrt `novelty_now` in a
separate snapshot field read only by `k1_tempo_update`; `novelty_curve`, spectrogram, AGC,
onset, director and colour shift untouched. Patch:
`_scratch/esp-emulator/next-phase-tempo-candidate-001/candidate-K1_TEMPO_NOVELTY_LINEAR_V1.patch`
(sha256 76df3146…; local evidence, not committed). Emulator, music case:
`PASS_timing_and_tempo`, lock 1323/1334 near 127 BPM, 21 beat ticks all received by the
render thread at the producer's generation (median spacing 483.75 ms vs 472 ms per beat),
edge A (BLOOM) byte-identical to baseline, only edge B (WAVEFORM_TEMPO, the confidence/phase
consumer) changes, shared render state unchanged, exact repeat.

**Corpus gate (FACT) — fails.** 36 HarmonixSet clips (gold BPM), each run through the real
emulated firmware, captured tempo input replayed as shipped (A) and pre-sqrt (B):

| | Acc1 | Acc2 | locked (lock ≥ 0.5 of scored window) | locked correct | locked wrong |
|---|---|---|---|---|---|
| A shipped | 17/36 | 19/36 | 2 | 1 | 1 |
| B pre-sqrt | 17/36 | 19/36 | 27 | 13 | 14 |

Host-vs-emulator fidelity 36/36. B chooses the same tempi as A; it only stops the false
silence, so it publishes the tracker's choice — right about half the time. Confidence does
not separate right from wrong (AUC ≈ 0.5 for A and B, model study). Merging B would make the
lamp lock confidently to a wrong beat on roughly 4 in 10 songs. **Not merged.**

**Next decision.** The input fix is only safe together with better winner selection (or a
confidence term that tracks correctness): this plan's option (b), ACF-salience + prior
hybrid, is the recorded route and is a tracker change with its own gate. Thresholds were not
touched. Stale facts corrected here: the tempo history is 512 emits at 44.44 Hz = 11.52 s
(not 10.24 s at 50 Hz), so the emulator's 12 s preroll clears warm-up by ~0.5 s.

## Update — 2026-10-21: lane R1 Phase 0 and Phase 1 (DEF-001 / DEF-002)

Branch `lane/k1-tempo-lock-r1`. Receipts: `docs/receipts/tempo-lock-r1/` (each = exit status of the
real command). All measurements are simulated (emulator, esp-emu 0.49.0) or host; none is silicon.

**Phase 0.** (a) Level sweep R9, R3 music case 0 to -24 dB through the real emulated firmware:
clipping 11 % of hops at 0 dB and 0 % from -6 dB, loud-guard input trim back to 1.0 from -12 dB, yet
tracker-internal silence 100 %, internal lock 100 % and published lock 0 at every level. The false
silence is not a fixture-clipping artefact. (b) Cost, shipped tracker, emulated time: emit p50 547 us,
p95 633 us, max 662 us (the 2x ceiling). (c) Frozen scorer + dev manifest reproduce the corpus exactly
(shipped 19/36 correct, 2 locks 1/1; pre-sqrt 27 locks 13 right 14 wrong); 3:2 among the wrong locks
is 7, not 8 (one clip at 6.4 % from 2/3). (d) Draft AGENTS.md invariants I1-I10:
`docs/patches/agents-md-tempo-invariants.patch` (Captain applies).

**Phase 1 (flags K1_TEMPO_NOVELTY_LINEAR_V1 + K1_TEMPO_SILENCE_FROM_PRODUCER_V1, emulator env
`k1_main_rpl_emu_tempo_r1`).** Every gating constant moved to `audio/k1_tempo_spec.h` with provenance
(byte-identical, provenance pinned). Veto bits (K1TempoVeto) on every output gate; WARMUP also holds
published confidence at 0 until the history is full. Results:
- R3 music: PASS_timing_and_tempo, lock 1.00 at 127 BPM, 21 ticks. Silence: no lock, confidence 0.
- M1 veto observability holds on 43 emulator streams; the shipped build violates it at generation 2047.
- M2 contrast invariance holds (x1/2, x1/4, ^2, ^1/2 keep lock and 127 BPM); shipped fails at ^2.
- Host replay equals the emulated firmware on 120,024 generations (lock, tick, BPM, veto).
- Dev corpus: 27 locks, 13 right / 14 wrong (the known state; DEF-002 is selection).
- Cost: emit p50 493 us, max 608 us (cheaper than shipped: the contrast loop is gone).
- **Red at L1:** white noise confidence 0.46, pink drone 0.52 (limit 0.30); a 3.3-octave log sweep
  (one semitone bin every 0.75 s, an 80 BPM onset train in GDFT space) locks; release after music
  5.94 s (the producer's SILENCE_DWELL_MS = 5000 plus the EMA; limit 3 s). In the shipped build these
  were suppressed only by the hidden contrast gate (`confidence x (1 - silence_level)`).

**Emotiscope 1.2 reference (Captain pointer).** Emotiscope's `check_silence` takes ONE sqrt of linear
spectral-flux novelty; K1 applied it to novelty already sqrt-compressed by the producer (the porting
defect behind DEF-001). Replaying the lane streams with the tap and the contrast gate kept (Emotiscope
-faithful) passes noise 0.22, drone 0.25, sweep 0.25 (no lock) and releases in 2.83 s, with the same
27/13/14 dev result — but fails M2 at ^1/2 (one more compression anywhere upstream re-creates DEF-001)
and conflicts with ruling R7 / I9. Recommended route: keep R7, and deliver noise/drone/release
rejection through the Phase 3 beat-prediction hit-rate term, which reads peak positions relative to
predicted beats and is invariant to scale and compression. Decision with the Captain.

## Update — 2026-10-21 (later): lane R1 Phase 2 and Phase 3, development side only

No held-out data has been run (the corpus awaits the Captain's approval, rule R8).

**Trap suite (M5).** 32 synthetic trains (72/96/120/144 BPM x clean, swing, triplet fills, dotted,
tresillo, hemiola, backbeat, tempo change). The shipped selection fails hemiola at 96/120/144 by
locking at 2/3 of the truth with lock 1.00 — DEF-002's 3:2 mechanism reproduced synthetically.

**Selection ablation (dev, 36 linear streams from the lane emulator image).** Shipped selection: Acc2
19/36, 27 locks, 13 right / 14 wrong (7 at 3:2). Geometric comb 16 / 13-15; min-tooth comb 16 / 12-10
(4 at 3:2); prior 110/0.9 14 / 12-18; flat prior 16 / 13-16; anti-3:2 17 / 15-16; anti-3:2+geometric
17 / 15-13. No variant raises Acc2; every variant still fails the hemiola trap; clean trains lock at
warm-up end under all of them. Dev pick by the R1 order (fewest wrong locks): min-tooth comb
(K1_TEMPO_COMB_PRODUCT_V1=2), which already trips the "Acc2 falls" falsifier on dev. Selection by comb
shape does not close DEF-002; the joint tempo+phase estimator (2.6) is the next measurement if the
held-out run confirms.

**Correctness terms (3.1, dev).** Track AUC right-vs-wrong: hit-rate 0.51, estimator agreement 0.44,
winner stability 0.61, CONF_V2 0.53 (emit AUC 0.49 / 0.55 / 0.67 / 0.58). None reaches the 0.8 bar.
Unless a better-formed term clears 0.8 on dev and held-out, rule 3.3 applies: lock stays OFF under
the flag set, the tentative band is published, no threshold is lowered.

## Captain rulings — 2026-10-21 (Phase 0.6 stop)

- Held-out corpus: Ballroom (698) + GiantSteps Tempo (661) approved in principle as the full
  1,359-clip acceptance corpus; no subsample. Acceptance execution is HELD until the development entry
  gates pass; then freeze candidate, scorer, configuration and manifest and run all 1,359 clips once
  under the declared evaluation plan.
- Silence: keep R7 (producer owns silence). Keep the compression-invariance requirement (M2). Develop a
  qualified confidence for noise / drone rejection. The Emotiscope-faithful contrast route is rejected
  (fails M2, overrides R7/I9).
- Release: keep the 3 s requirement; leave the producer's shared 5 s SILENCE_DWELL_MS unchanged.
- K1TempoEvent: unchanged (R5). Veto reasons stay in K1TempoGate, the debug snapshot and emulator K lines.
- Development entry gates before the held-out run: Phase 1.5 behaviour green; a confidence term with
  dev AUC >= 0.8 (or the lock-OFF outcome of rule 3.3 documented); the min-tooth comb trade-off
  (fewer wrong locks, lower Acc2) resolved; the deferred tooth-consistency term (3.1b) measured.

## Update — 2026-10-21 (evening): A7 cost, M2 with spectrum, Phase 2.6 joint estimator, rule 3.3, entry gates

All numbers are simulated (emulator) or host; none is silicon. Development data only; no held-out clip has
been run. Receipts: `docs/receipts/tempo-lock-r1/` (a7-*, p3-m2-l1sp-*, p2.6-*, p3.3-*).

**A7 cost (FACT, emulated time).** The spectral-presence step runs on every AP frame, outside the emit stage
timer, so the Phase 0.2 method could not see it. Probe builds now sum it per emit window (17th G field).
Lane image (linear tap + producer silence + spectral presence), music-a: emit + presence p50 525 us, max 646 us
(presence alone p50 32 us) against shipped 547 / 662 us: ratio 0.96 / 0.98, ceiling 2.0. Comparator
`tempo_lane_cost.py`; must-fail at a 0.5x ceiling exits 1.

**M2 with the spectrum (FACT, host).** The R3 capture with the per-note spectrum is committed
(`r3:r3_music_spec`); the M2 transforms now move every spectrum bin as well as the novelty. The l1sp build
holds (x1/2, x1/4, ^1/2: lock 1.00; ^2: 0.985; all 127 BPM; tolerance 0.05). Erasing the spectrum
(`speczero:1`) drops lock to 0 and fails the gate, so the gate exercises the presence path.

**Phase 2.6 joint tempo-and-phase estimator (host-only prototype, `tempo_joint_estimator.py`).**
- First state space (fractional phase shift at the 44.4 Hz emit rate) drifted to 60-75 BPM: its linear
  interpolation blurs phase more per beat at slow tempi, which makes slow hypotheses more forgiving
  (dev Acc2 9/36). Replaced by a bar pointer at the AP frame rate (Krebs/Boeck/Widmer 2015): exact
  integer periods 52-133 frames, 7,585 states, tempo steps only at a beat, rank-normalised novelty
  (invariant to monotonic transforms by construction), Gaussian beat window of exactly 1/lambda of the
  period at every tempo (a rounded hard window covered 9.6 % of a fast period but 6.8 % of a slow one,
  a second slow bias).
- Dev result, best of a 108-point grid (in-sample, so optimistic): Acc2 20/36 with 1 detected at 3:2,
  against the lane tracker's 19/36 with 7. It does not raise Acc2; it changes the error type away from
  3:2. Low-band (110-208 Hz) and full spectral flux observations did not beat the novelty.
- Correctness (bar 0.8, dev). As a term for the lane tracker's own choices, the best is tracker-estimator
  agreement (same tempo within 4 % up to an octave), track AUC 0.75 (15 right / 5 wrong agree); nothing
  reaches 0.8. On the estimator's own choices, 2 of the grid's 648 AUC values reach the bar: posterior
  mass with low-band (110-208 Hz) flux input, 0.819 and 0.838 (p2.6-joint-lowflux-auc-dev). Read with
  care: (1) it is the maximum of 648 correlated comparisons on 36 clips; a random-label simulation with
  648 independent comparisons puts the chance maximum at a median of 0.80 (5th percentile 0.76), and
  correlation lowers that, so 0.838 is not clearly separated from selection noise; (2) that setting picks
  the right tempo on only 14/36; (3) the right and wrong means are 0.991 and 0.969, so a lock needs a
  threshold near 0.98, where it publishes 14 right / 7 wrong (0.985: 12 / 5). It meets the dev bar
  literally and fails rule R1 in practice. Held-out data would settle it (admission needs >= 0.8 on both).
- Agreement-gated lock (the lane's published lock kept only on emits where the two agree), frozen scorer,
  dev: 10 locks, 8 right / 2 wrong (1 at 3:2), against the lane's 22 locks, 11 / 11, and shipped 1 / 1.
- Host cost (C, same state space, window weights quantised to 1/16): 6.3 us per AP frame on the host
  (about 19 us per emit) with a naive modulo-per-state loop and full renormalisation; 42.6 KB of floats.
  ESP32-S3 not measured; arithmetic estimate with incremental slot pointers and lazy normalisation
  160-220 us per emit, inside the 2x headroom (about 570 us). Not on silicon, not in the emulator.

**Rule 3.3 implemented (K1_TEMPO_LOCK_OFF_V1, default OFF).** No term for the lane tracker reached AUC
0.8 on dev (the one estimator-side value above 0.8 is the selection-noise case described above), so the
flag withholds the LOCKED band: `locked` and `beat_tick` stay false, confidence is capped at
K1_CONF_BAND_TENTATIVE_TOP (0.5999), and the new K1_TEMPO_VETO_NO_VALIDATED_LOCK bit is set on every emit;
the internal lock, tempo and phase keep running (M1 holds). Bands documented in `k1_tempo.h`. Host
replays: music-a 100 % of the scored window TENTATIVE; silence, white/pink noise, tone, chord, sweeps 0;
brown noise 62 % TENTATIVE (the known limit). Dev: 0 locks; right tracks sit TENTATIVE 66.7 % of the
window, wrong tracks 68.6 %: the tentative band says "a beat is present", not "this tempo is right".
Under this flag A1 (PASS_timing_and_tempo needs a lock) cannot pass, and DEF-001 closure depends on A1.
**STOP: lock-ON versus lock-OFF is the Captain's decision before the freeze.**

**Development entry gates (Captain rulings 2026-10-21).**
- (a) Phase 1.5 behaviour: green (p3-sp-p15-behaviour).
- (b) Confidence term with dev AUC >= 0.8: no term for the lane tracker meets it (best 0.75, agreement
  with the joint estimator); one estimator-side setting meets it literally (0.838, best of 648, fails R1
  in practice, see above). The rule 3.3 outcome is implemented and documented; which branch the gate
  closes on (lock-OFF, or carrying a candidate term into the held-out run) is the Captain's call.
- (c) Minimum-tooth comb (K1_TEMPO_COMB_PRODUCT_V1=2): REJECTED. It cuts wrong locks 14 -> 10 but Acc2
  falls 19 -> 16, which trips the brief's own falsifier (2.5: "Acc2 falls"), and it still fails the
  hemiola trap. The flag stays in source, default OFF, for the record.
- (d) Tooth consistency 3.1b: measured, AUC 0.70.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-10-21 | agent:claude-code (lane R1, evening) | Update: A7 cost incl. per-frame presence (0.96x shipped), M2 with the spectrum transformed, Phase 2.6 joint estimator (dev Acc2 20/36, 3:2 1; agreement-gated lock 8/2), rule 3.3 implemented behind K1_TEMPO_LOCK_OFF_V1, entry gates (b) lock-OFF documented, (c) min-tooth comb rejected; STOP for the Captain's lock decision. |
| 2026-06-03 | agent:claude-opus | Created — tempo-lock hardening spec from the prior-art trawl + algorithm-design swarm (3/5 reports). Captures the COMBINE plan (out-of-lobe confidence + octave defence + lock state machine + log-novelty) and the on-disk HarmonixSet real-music validation path, before context compaction. |
| 2026-10-21 | agent:claude-code (lane R1, later) | Update: Phase 2 trap suite + dev selection ablation (no variant raises Acc2) and Phase 3.1 dev AUCs (none >= 0.8). |
| 2026-10-21 | agent:claude-code (lane R1) | Update: Phase 0 (level sweep, cost, frozen scorer) and Phase 1 (linear tap + producer silence + veto bits): music passes, noise/drone/sweep/release red at L1; Emotiscope 1.2 comparison and recommended route. |
| 2026-10-20 | agent:claude-code (next phase) | Update: Main RPL weak lock = tracker-internal false silence on sqrt-compressed novelty; pre-sqrt candidate fixes the music passage end to end but fails the 36-track corpus gate (wrong-tempo locks 1→14); not merged. |
| 2026-06-03 | agent:claude-opus | Update (PM): real-music baseline MEASURED via the digital pipe — premise revised. Dominant failure is the Goertzel tempo SPECTRUM (Acc2 14–17% vs autocorrelation ceiling 50% on the same novelty), not octave error (~6%). Step 2 implemented in sb_tempo.cpp: log-Gaussian tactus prior (octave-err→0) + Goertzel un-clamp (the real ~2× win: in-range Acc1 9.4→25%, Acc2 15.6→28%). Metronome lock preserved; ESP32 build SUCCESS. Remaining gap is architectural (Fourier vs ACF); recommend ACF-salience+prior hybrid next. |
