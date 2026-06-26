---
name: spectrasynq-audio-pipeline
description: "Use when implementing, modifying, or debugging any audio analysis, beat detection, spectral analysis, or audio-reactive LED mapping across SpectraSynq K1/Emotiscope/Tab5 hardware"
---

# SpectraSynq Audio-Reactive Pipeline

## Overview

This skill codifies the audio-reactive pipeline architecture shared across 8 SpectraSynq projects: K1.LightwaveOS, Lightwave-Ledstrip, Tab5.DSP, Emotiscope.HIL, and others. It covers the full chain from audio input to perceptually-meaningful frequency data to beat-locked visual output.

**Core principle:** Audio-reactive systems are signal processing systems first, visual systems second. Get the signal right or the visuals will always look amateur.

## Goertzel vs FFT Decision Matrix

| Criterion | Goertzel | FFT |
|-----------|----------|-----|
| **Complexity** | O(1) per frequency | O(N log N) for all bins |
| **Use when** | Tracking specific known frequencies (semitone bins, tempo resonators) | Full broadband spectral analysis needed |
| **Typical use** | 64 semitone bins, beat resonator bank | Spectral flux calculation, broadband onset detection |
| **Memory** | Minimal — 3 state variables per detector | Requires N-point complex buffer |
| **Precision** | Exact center frequency — no bin leakage at target | Bin spacing fixed by N and sample rate |

**Decision rule:** If you know exactly which frequencies you care about, use Goertzel. If you need the full spectrum, use FFT.

**CRITICAL:** Never naively downsample 256 FFT bins to 64 Goertzel bins. FFT bins are linearly spaced (delta_f = Fs/N). Goertzel bins in this system are semitone-spaced (logarithmic). The frequency semantics are completely different. Mapping one to the other requires explicit frequency-domain resampling with proper energy distribution — not index mapping.

## Standard Bin Layout

64 bins, A1 (55 Hz) to C7 (2093 Hz), semitone-spaced.

```
Bin Range   Region          Musical Content
---------   ------          ---------------
 0 -  7     Sub-bass/Kick   Kick drum fundamental, bass synth sub
 8 - 15     Bass            Bass guitar, bass synth body
16 - 31     Mids            Vocals, guitar, snare body
32 - 47     Upper mids      Vocal presence, guitar bite, snare crack
48 - 63     Highs/Presence  Hi-hats, cymbals, vocal sibilance
```

**Access pattern in K1.LightwaveOS:**

```cpp
float magnitude = ctx.audio.bin(index);  // 0-63, semitone-spaced
```

Each bin center frequency: `f = 55.0 * pow(2.0, index / 12.0)` Hz.

## Beat Detection Architecture

Four-stage pipeline. Each stage feeds the next. Do not skip stages or combine them.

### Stage 1: Novelty Function (Spectral Flux)

Compute magnitude difference between consecutive frames. Only positive differences (onset energy, not offset).

```
novelty[t] = sum(max(0, |X[t][k]| - |X[t-1][k]|)) for all k
```

Operates on the 64 semitone bins, not raw FFT output. This ensures beat detection responds to musically relevant changes.

### Stage 2: Resonator Bank

Goertzel filters tuned to tempo candidates from 60 to 200 BPM. The novelty function is the input signal; the resonator frequencies correspond to beat periods.

```
resonator_freq = BPM / 60.0  (Hz)
```

Typical bank: ~30 resonators covering 60-200 BPM at ~5 BPM resolution.

### Stage 3: Tactus Resolver (Family Scoring)

Raw resonator output has harmonic ambiguity — a 120 BPM signal excites 60, 120, and 240 BPM resonators. The tactus resolver groups harmonically related tempos into families and scores each family.

```
family_score = sum(resonator_magnitude[member]) for member in family
tactus = family with highest score, weighted toward perceptual range (80-160 BPM)
```

### Stage 4: Phase-Locked Loop (PLL)

Locks to the phase of the selected tactus. Provides continuous beat phase (0.0 to 1.0) for visual synchronization.

- Phase advances at the locked BPM rate between beats
- Corrects on each detected onset
- Provides `beatPhase` and `tempoLocked` state to the render pipeline

## Sample Rate Reference

| Platform | Sample Rate | Notes |
|----------|-------------|-------|
| Emotiscope | 12.8 kHz | Nyquist 6.4 kHz — sufficient for 64-bin layout (max C7 = 2093 Hz) |
| Tab5.DSP | 16 kHz | Nyquist 8 kHz |
| Lightwave-Ledstrip ESV11 | 32 kHz | Nyquist 16 kHz — headroom for future high bins |
| PRISM | 44.1 kHz | Full audio bandwidth |

All platforms use the same 64-bin semitone layout. Higher sample rates do not change the bin count — they provide headroom, not more bins.

## Musical Saliency Principle

```
NEVER USE FFT DATA WITHOUT CHECKING SALIENCY FIRST.
Raw frequency data without musical context leads to amateur visualizations.
```

### Required Processing Before Visual Mapping

1. **Perceptual loudness weighting.** Apply A-weighting or equal-loudness contour correction. Raw magnitude at 100 Hz and 1 kHz are not perceptually equivalent even at identical levels.

2. **Temporal smoothing.** Apply attack/release envelope per bin. Fast attack (~5 ms) captures onsets. Slow release (~50-200 ms) prevents flickering.

3. **Beat phase cross-reference.** For rhythmic effects, modulate visual parameters by `beatPhase`, not raw magnitude. Magnitude tells you what is playing; beat phase tells you when.

4. **Normalization.** Normalize across the bin range per frame. Absolute magnitude varies wildly with input level — relative distribution is what matters for visualization.

## Anti-Patterns

Each of these has caused multi-session debugging incidents. Do not repeat them.

### 1. IOI Histogram for Tempo Detection

Inter-onset-interval histograms fail when the source material contains subdivisions (eighth notes, sixteenth notes). The histogram peaks at the subdivision interval, not the beat interval. Use the resonator bank approach instead.

### 2. Single-Bin Frequency Decisions

Never make a visual decision based on a single frequency bin. Bins are noisy. Always average 3-5 adjacent bins for any threshold or mapping decision.

### 3. Rigid Frequency-to-Visual Bindings

"Bass equals expansion" is a trap. It works for simple kick-driven music and fails for everything else. Visual mappings must be driven by saliency and beat phase, not fixed frequency bands.

### 4. Assuming `tempoLocked` on First Frame

`BeatTracker` defaults to 120 BPM before locking. The first several hundred milliseconds of `tempoLocked == true` may be a false positive. Require sustained lock (typically >2 seconds of consistent phase) before trusting tempo-dependent visual modes.

### 5. Lock-Dependent Terms in Confidence Formula

If your confidence metric includes a term that increases when `tempoLocked` is true, and `tempoLocked` depends on confidence exceeding a threshold, you have a positive feedback loop. Confidence will ratchet to maximum and never decrease. Confidence must be computed from signal evidence only.

### 6. Linear Interpolation for BPM Transitions

When the detected tempo changes (e.g., 120 to 130 BPM), linear interpolation creates perceptible phase jumps. Use exponential smoothing:

```cpp
smoothed_bpm += alpha * (detected_bpm - smoothed_bpm);  // alpha ~0.05
```

This converges asymptotically without phase discontinuity.

## Integration with Superpowers

### After Implementation

| Step | Skill | Purpose |
|------|-------|---------|
| 1 | `/signal-processing-verification` | Verify signal correctness against golden references |
| 2 | `/dsp-performance-profiling` | Confirm real-time viability on target hardware |
| 3 | `/dsp-test-fixtures` | Generate deterministic test signals for regression |

### Workflow

```
Implement → /signal-processing-verification → /dsp-performance-profiling → Ship
                    ↑                                    |
                    └──── Fix if signal is wrong ────────┘
                              or too slow
```

**Do not skip verification.** "It looks right on the LED strip" is not verification. Run the numbers.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-03-18 | agent:embedded-firmware-engineer | Created — codifies audio-reactive pipeline architecture across 8 SpectraSynq projects |
