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

## Captain supplement — 2026-10-21 (after the evening stop), verbatim

> Proceed towards a qualified lock-off fallback. This supplements the original brief; it does not replace its assignments or acceptance criteria.
>
> 1. Before freezing, reproduce the consumer gap: Tempo Comet and Anticipate can reconstruct predicted beats from tentative confidence despite locked=false and beat_tick=false. Use the final lock-off emulator image and capture actual rendered output on wrong-tempo development clips, brown noise, the R3 music case and silence/release.
>
> 2. I authorise a narrow extension of R4 to make the affected tempo consumers honour the distinction between tentative motion and validated beat cues. Preserve useful reactive behaviour and the graded middle ground. No broad effect redesign. Demonstrate the failure before the repair and its removal afterwards.
>
> 3. Qualify that fallback with the required behaviour checks, host/emulator agreement, off-flag byte identity, 20 repeats under load with and without diagnostics, and clean export from the final commit. Keep DEF-001 FIX-IN-LANE and DEF-002 OPEN until their actual closure requirements are met.
>
> 4. Preserve A1/A2 and the untouched 1,359-clip acceptance corpus. Do not port the agreement estimator yet. Propose one bounded host-only experiment using separate development/validation material, aimed at improving reliable lock coverage while reducing wrong locks.
>
> 5. Once a tempo candidate clears development requirements, freeze it and run the full acceptance corpus once, without re-picking. Product defaults and deployment remain separate Captain decisions; this lane retains its no-hardware boundary.

## Update — 2026-10-21 (night): qualified lock-off fallback, consumer repair, experiment proposal

All emulator results are simulated (esp-emu 0.49.0) and host results are host; none is silicon. Receipts:
`docs/receipts/tempo-lock-r1/` (c1-*, c2-*, q-*).

**Images (emulator only, upload-blocked).** `k1_main_rpl_emu_tempo_r1_lockoff` = the lane flags +
K1_TEMPO_LOCK_OFF_V1 + K1_TEMPO_CONSUMER_BANDS_V1 + K1_EMU_ONSET_TRACE (the qualified fallback);
`..._lockoff_probe` = the same + stage timers / G lines; `..._lockoff_unrepaired` = lock-off + onset trace without
the consumer repair (the failure-demonstration image, kept so the "before" state reproduces from any commit).
K1_EMU_ONSET_TRACE prints, per captured frame, the onset event the effects read (O lines; fixture only).

**Item 1, the consumer gap, reproduced on rendered output (FACT, simulated).** Tempo Comet (mode 20) and Tempo
Comet Anticipate (mode 27) read only `confidence` and `phase01`: confidence >= 0.45 (the midpoint of their
0.30-0.60 ramp) counts as "confident", so they learn the tempo, phase-lock an internal beat clock and launch a
comet on every predicted beat, never reading `locked` or `beat_tick`. Lock-off caps confidence at 0.5999, so the
predicted beats continue. Suite `tempo_lane_emu.py --suite consumer` (A = Tempo Comet, B = Anticipate via
set_mode / secondary_mode at hop 0): R3 music, music then silence, brown noise, silence, the 11 dev clips the
lane tracker locks wrong and 3 it locks right. `tempo_consumer_cues.py` finds launches in the captured pixels and
ties each to the bass onset the effects read; a launch with lock 0 and no onset in the 60 ms before it is a
predicted cue. Unrepaired image: Tempo Comet 203 launches, 133 predicted without a lock; Anticipate 84 / 55;
gap visible on R3 and on 10 of the 11 wrong-tempo clips; brown noise 5; silence 0. Known detector limit: the
rule under-counts (it attributes 60 ms after a launch to the same head and requires the core on the spawn pixel);
on R3 it detects 0 of Anticipate's eased launches although the frames show them, so the R3 evidence rests on
Tempo Comet. The rule was refined twice on observed pixels (colour drift near the centre; off-centre colour
shifts) and is applied identically to both images.

**Item 2, the repair (R4 extension; K1_TEMPO_CONSUMER_BANDS_V1, default OFF).** In both effects the beat grid
(learned tempo, phase lock, launches on predicted beats, Anticipate's arrival pinned to the next beat) now follows
the published `locked`, not confidence. In the TENTATIVE band (each effect's own existing 0.30 edge, not locked)
a comet launches on a fresh bass onset (the original Comet's event) and the tentative tempo only sets its speed;
Anticipate's onset comets travel freely with no slew to the phase and no park-and-land. The NONE band is
unchanged (the effect stands down). A coast of up to 8 predicted beats after a real validated lock is lost is
kept, matching the tracker's own post-lock coast; it cannot occur under lock-off. Repaired image: Tempo Comet
204 launches, 204 on a bass onset, 0 predicted; Anticipate 205 / 205 / 0; the effects still launch on every
music case (reactive behaviour kept) and stay dark in silence. Other tempo consumers audited and left alone:
Pulse Prism and the effect queue already require `locked && beat_tick`; Tempo River, Snapwave, Dense Forge,
Dense Forge Chord and Waveform Tempo use phase / confidence as continuous motion; Tempo River Walk counts phase
wraps but only to glide its palette one step per bar (no beat event drawn) — a judgement recorded here.

**Item 3, qualification of the fallback (FACT, simulated / host).**
- Behaviour (`tempo_lane_gates.py p15 --lockoff`): music-a timing classification passes with 100 % of the scored
  window TENTATIVE and no lock or tick; silence, white / pink noise, tone, chord, both sweeps confidence 0;
  release: TENTATIVE ends 1.51 s after the music (limit 3 s); brown noise reaches TENTATIVE (known limit), no
  lock. Must-fail: the lock-publishing lane image fails the same gate.
- Host == emulator (`tempo_lane_gates.py fidelity`, lock, tick, BPM, veto and confidence): p15 27,868 and
  negatives 28,000 and dev 120,024 generations, 0 differing. Must-fail: the lock-on host build against the
  lock-off emulator runs differs on 27,847 generations.
- Cost (A7 method, probe image): emit + presence p50 524 us, max 645 us vs shipped 547 / 662 (0.96 / 0.97).
- Determinism under load (`stress_repeat.py`, R3 music-a with Tempo Comet on A and Anticipate on B, 20 runs at
  8 in parallel each): lock-off image with the trace_novelty diagnostic 0/20 diverged; without it 0/20; the probe
  image (stage timers + G lines) with the trace 0/20. All 60 runs give the same rendered payload. Rule of three:
  true divergence rate below about 0.15 per set at 95 %. Must-fail: one foreign run in the set is reported.
  The first attempt exposed a harness race, not a firmware one: parallel workers decoded the music asset into
  one shared file, so most runs started with no or truncated PCM (logs kept in stress/race-evidence).
  `stress_repeat.py` now decodes per run into its own folder and passes the PCM through run_case's asset cache;
  it also gains `--no-trace` for the without-diagnostics set.
- Off-flag byte identity (A6), base 0bddfaed against b1f48bbc, both as git-archive exports built with pinned
  provenance (git 0000000, epoch 1760000000): k1_main_rpl_im69d and k1_hardware, every allocated ELF section
  identical. Object level: 138 objects identical by path; the rest sit in two PlatformIO library folders whose
  names are a hash of the project path (the exports live at different paths): FastLED libe6f -> libe79 and one
  single-object library lib1e6 -> libf98 (k1_hardware: lib4d5 -> lib847, libe53 -> liba23). With those folders
  mapped, 261 of 261 objects identical (a6-byte-identity-*-normalised); unmapped receipts kept (a6-byte-identity-*).
- Clean export (A5) of b1f48bbc (git archive, no .git, all of .pio/libdeps copied in, source identity file,
  pinned esp-emu): `run.py` on s3_music_regression.json reports SOFTWARE COMPLETE, SW07 (host pytest 1665 passed,
  21 skipped, 8 git-history files run in the checkout; k1_hardware builds) and SW11 (clean export) PASS, all 22
  cases and 14 comparisons PASS (a5-export-r3-contract). Inside the export the lane also passes: tempo_gates
  pytest 28 passed, both lane images build, the consumer gap is visible on the unrepaired image and clean on the
  lock-off image, p15 --lockoff green (a5-export-*). The first attempt reported SOFTWARE INCOMPLETE: I had copied
  only five envs' libdeps, and tests/test_b489_legacy_power_host.py reads FastLED from k1_bench_im69d_led150's;
  copying the whole .pio/libdeps (as rule 7 says) fixed it, on a fresh export. Full pytest in the checkout at
  b1f48bbc: 1898 passed, 15 skipped (a8-full-pytest-b1f48bbc). Observation for the report tool's owner: at
  400 px the R3 report.html clips long evidence lines at the right edge (desktop is fine); not changed here.
- Correction: the b1f48bbc commit message says host == emulator on "176,892" generations; the correct total is
  175,892 (27,868 + 28,000 + 120,024), as the receipts show.

**Item 4, proposed bounded host-only experiment (PROPOSAL — NOT APPROVED).**
E1 "agreement-gated lock, frozen on development, judged once on separate validation".
- Question: does publishing a lock only while the comb tracker and the bar-pointer joint estimator agree (same
  tempo within 4 % up to an octave) continuously for D seconds raise reliable lock coverage above the fallback
  (0 locks) while keeping wrong locks rare? It is the one rule measured so far that moved the right/wrong ratio
  (dev 8 / 2 against the lane's 11 / 11), and its two halves fail differently (the estimator rarely lands on 3:2).
- Material: development = the 36 HarmonixSet clips (choose D in {0, 2, 4} s by "most right locks with at most
  1 wrong"; estimator settings stay as frozen in p2.6). Validation = a separate annotated set the Captain approves,
  disjoint from HarmonixSet, Ballroom and GiantSteps (candidates: SMC_MIREX, about 217 beat-annotated excerpts;
  or GTZAN with the published tempo annotations). Nothing on this machine qualifies today (GTZAN folder holds one
  file). Validation is used once and is not the acceptance corpus.
- Pre-registered success on validation: wrong locks <= 10 % of locked tracks at the upper 95 % (Wilson) bound,
  right locks >= 25 % of tracks, and no new trap-suite attractor. Otherwise the fallback stands.
- Bounds: host-only (emulator used only to capture the validation tracker input, as for dev); no firmware
  change, no port; one validation run; no re-pick; about half a day of compute.

**Item 5, the acceptance corpus (HELD).** No lock candidate has cleared the development requirements (no
correctness term >= 0.8; the fallback publishes no lock, so A1 and A2 cannot pass by construction). Spending the
single held-out run on the fallback would leave no untouched corpus for a lock candidate. Whether the fallback
alone should take the held-out run is put to the Captain.

## Update — 2026-10-22: E1 development side, and three corrections from an independent review

Host only, development data only. No held-out or validation clip has been run, and nothing was downloaded.
Receipts: `docs/receipts/tempo-lock-r1/e1-*`.

**Item 5 above is already answered.** The Captain's supplement (items 4 and 5, verbatim above) keeps the 1,359-clip
corpus untouched and sends a candidate to it only once it clears the development requirements. The lock-off
fallback publishes no lock, so it does not take the held-out run. Only the E1 validation set remains a decision,
and the result below changes what it is worth.

**E1 development pick (FACT, host).** `tempo_joint_estimator.py gate` gains `--hold-s D`: the lane tracker's lock is
published only after lock and estimator agreement have both held continuously for D seconds. With D = 0 the output
is byte-identical to the p2.6 agreement-gate trajectory (sha256 `bfaf3481…`), so the existing result reproduces.
Estimator settings are those frozen in p2.6 (`dev_joint_best`: pointer model, kappa 8, lambda 8, tempo_q 0.02).
Frozen scorer, 36 development clips:

| D | locked | right | wrong | wrong at 3:2 | eligible (at most 1 wrong) |
|---|---|---|---|---|---|
| 0 s | 10 | 8 | 2 | 1 | no |
| 2 s | 2 | 1 | 1 | 0 | yes |
| 4 s | 1 | 1 | 0 | 0 | yes |

The pick rule ("most right locks with at most 1 wrong") gives a tie between 2 s and 4 s that the proposal did not
pre-register a tie-break for. Either way the candidate locks right on **1 of 36 tracks (2.8 %)**. The pre-registered
validation bar is right locks on at least 25 % of tracks. Development numbers are in-sample and so optimistic, so
validation cannot be expected to do nine times better. Even D = 0, which is not eligible, covers only 22 %.
**E1 as proposed is falsified on development data. Spending a validation set on it would not answer anything.**

**Why the hold collapses coverage (FACT, host; INFERENCE on the mechanism).** The development clips leave a 13 s
scored window (25 s clip minus 12 s warm-up), and a track counts as LOCKED only at a lock fraction of at least 0.5. Each
run of agreement loses its first D seconds, so a 4 s hold removes about 31 % of the window per run. Agreement on
right tracks comes in runs of 2-13 s, but wrong tracks have long runs as well (6.65 s and 7.74 s on two wrong locks).
So D mostly removes locks through window length and does not separate right from wrong. D also would not transfer to
validation clips of other lengths (SMC_MIREX excerpts are about 40 s, GTZAN 30 s). This was a design flaw in the E1 proposal.

**Sample size the validation criterion needs (arithmetic).** For the two-sided 95 % Wilson upper bound on the
wrong-lock rate to fall to 10 % or below, a set needs at least 35 locked tracks with 0 wrong, 53 with 1, 69 with 2,
84 with 3. That is an observed wrong rate of about 2-4 %, against 20 % on development (2 of 10 at D = 0). At the
development lock rate (10 of 36) that is at least 126 validation clips just to reach 35 locks. Any future lock
experiment should state this calculation against the size of the proposed set before it asks for material.

**Recommendation (PROPOSAL — NOT APPROVED).** Do not approve validation material for E1. Keep the qualified
lock-off fallback as the baseline. A future lock candidate is worth a validation set only if (1) it meets its own
pre-registered success bar on development first, (2) it has a sample-size calculation like the one above, and
(3) its parameters are defined in a way that does not depend on clip length (for example a fraction of the window,
or scored on fixed-length windows).

**Corrections from the independent review of 325b87da.**
- Detector claim (`tempo_consumer_cues.py` docstring). The old text said the detector's biases could never hide
  predicted cues only after the repair, because the same rule judges both images. That does not follow: under-counting
  can also miss failures after a repair, if the repair changes how a launch looks. Reworded: a clean result supports
  "zero *detected* predicted cues". The stronger claim for the lock-off image rests on the code. Under
  K1_TEMPO_CONSUMER_BANDS_V1 the beat grid learns a tempo only while `locked` is set (`light_mode_tempo_comet.cpp:103-123`
  and the matching lines in Anticipate), lock-off never sets it, so the predicted-launch path cannot run.
- Lock-enabled images need their own consumer check. The repair keeps a coast of up to 8 predicted beats after a
  validated lock is lost. That cannot happen under lock-off, so none of the c2-* or q-* receipts exercises it. Before
  any lock-enabled image is qualified, the consumer suite must run on a lock-publishing build, including music
  followed by silence and a lock lost mid-track. Coast cues must be counted and judged against rule R1, not merged
  into the "0 predicted" figure.
- Commit-message total: 175,892 host-equals-emulator generations, not 176,892 (already corrected in the night update).

DEF-001 stays FIX-IN-LANE (A1 needs a lock, so it cannot close under the fallback); DEF-002 stays OPEN.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-10-22 | agent:claude-code (lane R1) | Update: E1 development pick (D 0/2/4 s → 8/2, 1/1, 1/0; best eligible covers 1 of 36 tracks against a 25 % bar), so E1 is falsified on development and no validation set is recommended; the clip-length flaw in D and the Wilson sample-size table are recorded; the held-out question is marked already answered by the supplement; the detector wording is corrected and a lock-enabled consumer check is made an entry requirement. |
| 2026-10-21 | agent:claude-code (lane R1, night) | Captain supplement recorded verbatim; consumer gap reproduced on rendered output and repaired behind K1_TEMPO_CONSUMER_BANDS_V1; lock-off fallback qualified (behaviour, host == emulator, cost, byte identity, repeats, clean export); experiment E1 proposed; held-out run held for the Captain. |
| 2026-10-21 | agent:claude-code (lane R1, evening) | Update: A7 cost incl. per-frame presence (0.96x shipped), M2 with the spectrum transformed, Phase 2.6 joint estimator (dev Acc2 20/36, 3:2 1; agreement-gated lock 8/2), rule 3.3 implemented behind K1_TEMPO_LOCK_OFF_V1, entry gates (b) lock-OFF documented, (c) min-tooth comb rejected; STOP for the Captain's lock decision. |
| 2026-06-03 | agent:claude-opus | Created — tempo-lock hardening spec from the prior-art trawl + algorithm-design swarm (3/5 reports). Captures the COMBINE plan (out-of-lobe confidence + octave defence + lock state machine + log-novelty) and the on-disk HarmonixSet real-music validation path, before context compaction. |
| 2026-10-21 | agent:claude-code (lane R1, later) | Update: Phase 2 trap suite + dev selection ablation (no variant raises Acc2) and Phase 3.1 dev AUCs (none >= 0.8). |
| 2026-10-21 | agent:claude-code (lane R1) | Update: Phase 0 (level sweep, cost, frozen scorer) and Phase 1 (linear tap + producer silence + veto bits): music passes, noise/drone/sweep/release red at L1; Emotiscope 1.2 comparison and recommended route. |
| 2026-10-20 | agent:claude-code (next phase) | Update: Main RPL weak lock = tracker-internal false silence on sqrt-compressed novelty; pre-sqrt candidate fixes the music passage end to end but fails the 36-track corpus gate (wrong-tempo locks 1→14); not merged. |
| 2026-06-03 | agent:claude-opus | Update (PM): real-music baseline MEASURED via the digital pipe — premise revised. Dominant failure is the Goertzel tempo SPECTRUM (Acc2 14–17% vs autocorrelation ceiling 50% on the same novelty), not octave error (~6%). Step 2 implemented in sb_tempo.cpp: log-Gaussian tactus prior (octave-err→0) + Goertzel un-clamp (the real ~2× win: in-range Acc1 9.4→25%, Acc2 15.6→28%). Metronome lock preserved; ESP32 build SUCCESS. Remaining gap is architectural (Fourier vs ACF); recommend ACF-salience+prior hybrid next. |
