---
abstract: "T1 recon for periodicity lane task #7 (ACF-salience + log-Gaussian hybrid). Documents the current sb_tempo algorithm, every internal constant, the full state struct, insertion points for ACF-salience and the log-Gaussian prior, and the #6-vs-#7 prerequisite verdict. Read before writing a line of task-#7 code."
---

# sb_tempo Algorithm Recon — Task #7 Insertion Points

**Date:** 2026-06-04  
**Branch:** `feat/gdft-harness`  
**Recon SSA:** T1 (read-only; no firmware edits, no commits)  
**Bounded sources:** `sb_tempo.h`, `sb_tempo.cpp`, `.ino` wiring grep, `docs/architecture/tempo-lock-hardening-plan.md`

---

## 1. Detector class and internal rate

**Class:** Scheirer '98 / Klapuri '06 / Emotiscope-derived **Goertzel resonator bank over a scalar novelty curve** (single-rate K1 fork; the donor was dual-rate).

**Rate chain:**
- AP frame rate: `12800 / 96 = 133.333 Hz` (`SB_AP_FRAME_HZ`)
- Decimation: every `SB_NOVELTY_DECIMATION = 3` AP frames, peak-hold accumulate into one novelty sample
- True Goertzel input rate: `133.333 / 3 = 44.444 Hz` (`SB_NOVELTY_RATE_HZ`) — exact frame-count gate, NOT a wall-clock ms gate (the prior ms gate caused a ~1.13× BPM scaling error)
- History window: 512 novelty samples ≈ 11.5 s at 44.444 Hz
- Per-emit decay on history: `SB_NOVELTY_DECAY = 0.999`

**Entry point in .ino:** `sb_tempo_update(sb_audio_snapshot)` called once per AP frame at `.ino:514` (Core-0 audio loop). Init at `.ino:384`.

---

## 2. Candidate set and winner-selection logic

**Candidate set:** 96 bins, `SB_TEMPO_LOW = 60.0 BPM` … `155.0 BPM`, 1 BPM resolution.

**Goertzel magnitude computation** (`sb_compute_magnitude`): standard finite-block recompute of IIR resonator state. Input novelty is scaled by `sb_novelty_scale` and clamped to `[0, 4.0]` (Step 2 raised the ceiling from `[0,1]` — the un-clamp that delivered the real ~2× Acc2 gain, 17%→28%).

**Smoothing:** `sb_tempi_smooth[i]` — EMA of `magnitude_raw^4` (the quartic exaggeration at `sb_update_tempo`; pre-emphasis that amplifies the tallest bin, including sub-harmonics on real music).

**Winner selection** (`sb_update_winner`): argmax over `sb_tempi_smooth` with a **+10% challenger margin + 5-frame persistence hysteresis** before `sb_winner_bin` is updated.

**Step 2 log-Gaussian layer** (committed, inside `sb_update_winner` only): before the argmax, a local search uses `sb_tempi_smooth[i]^0.25 * sb_tempo_prior[i]` (de-sharpen undoes quartic; prior reweights). This affects winner *selection* only — the stored `sb_tempi_smooth` magnitudes, confidence, and phase are all untouched, preserving metronome lock at conf 0.999.

**Confidence** (`sb_update_tempo`): `peak² / (peak² + Σ out-of-lobe bin²)` where the main lobe is `±SB_CONF_LOBE = 6` bins around the winner. Lock threshold `SB_LOCK_CONFIDENCE = 0.60`.

---

## 3. State struct and key fields

### `SBTempoBin` (per-bin, `sb_tempi[96]`)

| Field | Type | Purpose |
|---|---|---|
| `target_bpm` | `float` | bin centre in BPM |
| `target_hz` | `float` | bin centre in Hz |
| `coeff` | `float` | Goertzel coefficient `2·cos(ω)` |
| `sine` | `float` | `sin(ω)` — for magnitude extraction |
| `cosine` | `float` | `cos(ω)` |
| `block_size` | `uint32_t` | novelty samples per finite-block recompute |
| `phase` | `float` | measured/extrapolated beat phase `[−π, +π]` |
| `phase_radians_per_sec` | `float` | `2π·hz` |
| `magnitude` | `float` | normalised `[0,1]` |
| `magnitude_raw` | `float` | pre-normalisation |

### Module-level state

| Symbol | Type | Purpose |
|---|---|---|
| `sb_tempi_smooth[96]` | `float[]` | EMA of `magnitude_raw^4` — the smoothed spectrum fed to winner selection |
| `sb_winner_bin` | `uint16_t` | current winning bin index |
| `sb_candidate_bin` | `uint16_t` | challenger accumulating hysteresis frames |
| `sb_candidate_frames` | `uint8_t` | hysteresis frame counter (needs ≥5 to promote) |
| `sb_confidence` | `float` | out-of-lobe concentration score |
| `sb_current_phase` | `float` | running beat phase |
| `sb_beat_tick` | `bool` | true for one update at the beat instant |
| `sb_silence_detected` | `bool` | low-contrast novelty gate |
| `sb_frame_ctr` | `uint16_t` | AP frames since last novelty emit (decimation counter) |
| `sb_tempo_prior[96]` | `float[]` | precomputed log-Gaussian tactus weights |

### Log-Gaussian prior constants (committed Step 2)

```
SB_TACTUS_BPM   = 120.0  // preferred centre in BPM
SB_TACTUS_SIGMA = 0.9    // width in octaves
prior[i] = exp(-0.5 * (log2(bpm_i / 120.0) / 0.9)^2)
```

Symmetric in log₂ → half-tempo and double-tempo penalised equally. Gentle at the range edges (~0.85 at 60/155 BPM); breaks ties only, never forces.

### Public API (sb_tempo.h)

```cpp
void         sb_tempo_init();                              // compute Goertzel coeffs + prior, clear state
void         sb_tempo_update(const SBAudioSnapshot& audio);// once per AP frame, Core-0
SBTempoEvent sb_tempo_read();                              // spinlock value-copy, any core
void         sb_tempo_reset();                             // clear runtime state, keep coeffs
```

### `SBTempoEvent` (published cross-core under portMUX)

```cpp
struct SBTempoEvent {
  float bpm;           // winner bin centre
  float phase01;       // beat phase [0,1); 0 == beat instant
  float confidence;    // [0,1] out-of-lobe concentration
  bool  beat_tick;     // true for one update at beat instant
  bool  locked;        // confidence > 0.60 && !silence
  float beat_strength; // smoothed magnitude of winning bin
};
```

---

## 4. Insertion point — ACF-salience

**What it replaces/augments:** the Goertzel resonator bank (`sb_compute_magnitude` + `sb_tempi_smooth`) as the **tempo-spectrum source**. The plan identifies this as option (b): keep Goertzel for phase, replace the amplitude/salience signal fed into `sb_update_winner` with an ACF-derived comb salience.

**Concrete insertion:**

1. **New function `sb_compute_acf_salience()`** — after every novelty emit (i.e. once per 3 AP frames, inside the `sb_frame_ctr == 0` branch of `sb_tempo_update`):
   - Compute autocorrelation of `sb_spectral_curve[]` (512 samples @ 44.444 Hz) at each of the 96 lag values corresponding to `SB_TEMPO_LOW + i` BPM.
   - Output: a 96-element salience array replacing or augmenting `sb_tempi_smooth` for the purpose of winner selection.

2. **`sb_update_winner` augmentation** — feed the ACF salience in place of (or fused with) `sb_tempi_smooth[i]` in the argmax search. The log-Gaussian prior (`sb_tempo_prior[i]`) already present in Step 2 then pins the octave, completing the ACF + prior hybrid the plan recommends.

3. **Phase still from Goertzel** — `sb_tempi[i].phase` and the phase-tracking path in `sb_update_tempo` are untouched; only the salience/amplitude signal changes.

**Plan note on compute:** ACF salience over 512 samples × 96 lags ≈ 1% CPU @ 240 MHz per the plan's estimate; a perf read is recommended before committing on-device.

---

## 5. Insertion point — log-Gaussian prior

**Already committed (Step 2).** `sb_tempo_prior[96]` is precomputed in `sb_tempo_init()` using `SB_TACTUS_BPM = 120.0` and `SB_TACTUS_SIGMA = 0.9` octaves. It is applied inside `sb_update_winner` on the de-sharpened score `sb_tempi_smooth[i]^0.25 * sb_tempo_prior[i]` before the argmax.

**For task #7 (ACF-salience hybrid):** the prior needs only to be re-applied to the ACF salience array in the same location — `sb_update_winner`, same multiply, same constants. No new insertion point is needed for the prior itself; the ACF salience replaces the signal it weights, not the prior.

**If SIGMA tuning is needed:** `SB_TACTUS_SIGMA` is the single tunable for octave-error rate vs. range coverage. The plan mandates host-only validation via `tempo_accuracy.py` before changing it.

---

## 6. Task #6 / #7 prerequisite verdict

**Independent.** The plan's "Implementation order" section lists:

1. Real-music host pipe (done ✓, commit `134c872`)
2. Octave defence — log-Gaussian prior + quartic de-sharpen + Goertzel un-clamp (done ✓, Step 2)
3. **Octave-aware confidence + Schmitt lock state machine** (SW4 — this is task #6)
4. Log-domain novelty in GDFT.h (SW3 — separate, highest blast radius)
5. On-device eyes-on

Task #7 (ACF-salience) is option (b) under "The remaining gap is ARCHITECTURAL" — it is **not sequenced after task #6** in the plan. The plan explicitly positions ACF-salience as the next architectural step after Step 2, with task #6 (Schmitt lock / octave-aware confidence) listed as a **parallel improvement** to the lock state machine that is independent of the salience computation path.

**Verdict: independent.** Task #7 operates entirely within `sb_compute_magnitude` → `sb_tempi_smooth` → `sb_update_winner` (the salience pipeline). Task #6 operates on `sb_confidence` and `e.locked` (the lock state machine). Neither modifies the other's state. They can be implemented and host-validated on the same branch without ordering constraints.

---

## 7. Measured baselines (for validation gate)

| Metric | `684a547` (pre-Step-2) | Step 2 (committed) | ACF ceiling |
|---|---|---|---|
| Acc1 in-range (±4%) | 9.4% | **25.0%** | ~17% (ACF alone) |
| Acc2 octave-tolerant | 15.6% | **28.1%** | **~50%** |
| Octave-error rate | 6.2% | 3.1% | — |

The ACF-salience + prior hybrid (task #7) is the only path the data shows reaching the ~50% Acc2 ceiling. Validation: `python3 scripts/regression-harness/tempo_accuracy.py` (host, digital, no bench required).

---

**Document Changelog**

| Date | Author | Change |
|---|---|---|
| 2026-06-04 | agent:T1 (claude-sonnet-4-6) | Created — full recon of sb_tempo algorithm and ACF/prior insertion points for task #7 |
