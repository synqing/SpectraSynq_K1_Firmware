---
name: dsp-test-fixtures
description: Use when writing tests for any DSP function and need deterministic audio signals - provides generators for sine, chirp, noise, impulse, click track, and multi-tone signals with fixed seeds for CI reproducibility
---

# DSP Test Fixtures

## Overview

Deterministic signal generators for DSP testing. Every signal is reproducible across runs -- no randomness, no recorded audio, no environmental variance.

**Core principle:** Test signals must be analytically predictable. If you cannot calculate the expected output by hand, you cannot verify the code.

## The Iron Law

```
NO RECORDED AUDIO IN UNIT TESTS
```

Recordings introduce: microphone variance, room acoustics, codec artifacts, level differences, timing jitter. Use synthetic signals for unit/integration tests. Reserve recorded audio for system-level validation only.

## When to Use

- Writing tests for any DSP function
- Need a known input to verify against expected output
- Building test fixtures for CI pipeline
- Creating benchmark inputs for performance profiling

## Signal Generators

### Quick Reference

| Signal | Function | Use for |
|--------|----------|---------|
| Single sine | `generate_sine` | FFT bin verification, filter passband |
| Multi-tone | `generate_multitone` | Goertzel selectivity, bin isolation |
| Chirp (sweep) | `generate_chirp` | Filter frequency response, full-band |
| White noise | `generate_noise("white", seed=N)` | Filter shape, statistical tests |
| Pink noise | `generate_noise("pink", seed=N)` | Perceptual weighting tests |
| Impulse | `generate_impulse` | Filter impulse response |
| Click track | `generate_click_track` | Beat detection |
| Transients | `generate_transient_test` | Onset detection |
| Silence | `generate_silence` | Noise floor, false positive testing |
| DC offset | `generate_dc` | DC removal filter testing |

### Generator Specifications

All generators share these properties:
- **Output type:** float32 array, normalised to [-1.0, 1.0]
- **Deterministic:** Same parameters always produce identical output
- **Documented:** Every parameter has units in the docstring
- **Sample-accurate:** Length is exact to the sample

```python
import numpy as np

def generate_sine(freq_hz, duration_s, sample_rate, amplitude=1.0, phase_rad=0.0):
    """Pure sine wave. Amplitude in [0, 1]. Phase in radians."""
    t = np.arange(int(duration_s * sample_rate)) / sample_rate
    return (amplitude * np.sin(2 * np.pi * freq_hz * t + phase_rad)).astype(np.float32)

def generate_multitone(freqs_hz, amplitudes, duration_s, sample_rate):
    """Sum of sines. freqs_hz and amplitudes are parallel arrays."""
    t = np.arange(int(duration_s * sample_rate)) / sample_rate
    signal = np.zeros_like(t, dtype=np.float32)
    for freq, amp in zip(freqs_hz, amplitudes):
        signal += amp * np.sin(2 * np.pi * freq * t)
    return signal

def generate_chirp(f_start_hz, f_end_hz, duration_s, sample_rate, method="linear"):
    """Frequency sweep. method: 'linear' or 'logarithmic'."""
    t = np.arange(int(duration_s * sample_rate)) / sample_rate
    if method == "linear":
        phase = 2 * np.pi * (f_start_hz * t + (f_end_hz - f_start_hz) / (2 * duration_s) * t**2)
    else:  # logarithmic
        k = (f_end_hz / f_start_hz) ** (1 / duration_s)
        phase = 2 * np.pi * f_start_hz * (k**t - 1) / np.log(k)
    return np.sin(phase).astype(np.float32)

def generate_noise(noise_type, duration_s, sample_rate, seed=42):
    """Deterministic noise. noise_type: 'white' or 'pink'. seed ensures reproducibility."""
    rng = np.random.default_rng(seed)
    n_samples = int(duration_s * sample_rate)
    if noise_type == "white":
        return rng.standard_normal(n_samples).astype(np.float32)
    elif noise_type == "pink":
        # Voss-McCartney algorithm for pink noise
        white = rng.standard_normal(n_samples)
        # Apply 1/f filtering via cumulative sum + highpass
        pink = np.cumsum(white)
        pink -= np.mean(pink)
        pink /= np.max(np.abs(pink)) + 1e-12
        return pink.astype(np.float32)

def generate_impulse(delay_samples, length_samples, sample_rate, amplitude=1.0):
    """Dirac delta at specified sample offset."""
    signal = np.zeros(length_samples, dtype=np.float32)
    if 0 <= delay_samples < length_samples:
        signal[delay_samples] = amplitude
    return signal

def generate_click_track(bpm, duration_s, sample_rate, click_duration_ms=5):
    """Click track with precise BPM. Returns (signal, beat_times_s)."""
    n_samples = int(duration_s * sample_rate)
    signal = np.zeros(n_samples, dtype=np.float32)
    interval_s = 60.0 / bpm
    click_len = int(click_duration_ms / 1000.0 * sample_rate)
    beat_times = []
    t = 0.0
    while t < duration_s:
        idx = int(t * sample_rate)
        if idx + click_len < n_samples:
            # Short burst of 1kHz sine
            click_t = np.arange(click_len) / sample_rate
            signal[idx:idx + click_len] = np.sin(2 * np.pi * 1000 * click_t)
            beat_times.append(t)
        t += interval_s
    return signal.astype(np.float32), np.array(beat_times)

def generate_silence(duration_s, sample_rate):
    """Pure silence. For noise floor and false positive testing."""
    return np.zeros(int(duration_s * sample_rate), dtype=np.float32)
```

## Fixture Organisation

```
tests/
  fixtures/
    signals/
      sine_440hz_1s_44100.wav       # Pre-generated for fast loading
      chirp_20_20000_5s_44100.wav
      noise_white_seed42_1s_44100.wav
    golden/
      fft_sine_440_1024.bin         # Expected FFT output
      fft_sine_440_1024.json        # Metadata: params, tolerance
      goertzel_440_response.json    # Expected Goertzel output
      beat_120bpm_detections.json   # Expected beat positions
    generators/
      signal_generators.py          # The functions above
      fixture_builder.py            # Script to regenerate all fixtures
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using `random.random()` without seed | Always pass explicit seed to generators |
| Generating in the test itself | Pre-generate and store as fixtures for speed |
| Using MP3/AAC compressed fixtures | Use WAV or raw float32 -- lossy compression changes the signal |
| Normalising after generation | Normalise during generation -- post-normalisation changes relative levels |
| Assuming sample rate | Every generator takes `sample_rate` explicitly |
| Testing with only one frequency | Use multi-tone and sweep to cover the full band |

## Red Flags

- Using `np.random.rand()` (not seeded) -- use `np.random.default_rng(seed)`
- Loading a `.mp3` or `.ogg` for testing -- use `.wav` or raw binary
- "Let me just record a quick test signal" -- NO. Generate it.
- Click track without returned beat times -- you need annotations to verify detection

## Integration

**Used by:** `/signal-processing-verification`, `/dsp-performance-profiling`
**Feeds into:** `/test-driven-development` (provides test inputs)
