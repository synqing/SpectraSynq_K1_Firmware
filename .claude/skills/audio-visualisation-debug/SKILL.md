---
name: audio-visualisation-debug
description: Use when debugging unexpected DSP behaviour and need to visually inspect signals - generates waveform plots, spectrum views, spectrograms, filter response curves, and beat detection overlays from raw buffer data
---

# Audio Visualisation Debug

## Overview

When a DSP function produces wrong results, looking at numbers is often insufficient. Visualising the signal reveals problems that are invisible in raw data: spectral leakage, windowing artifacts, phase discontinuities, transient smearing.

**Core principle:** See the signal before diagnosing the algorithm. A spectrum plot in 10 seconds saves 30 minutes of numerical debugging.

## When to Use

- Signal verification fails and you need to understand WHY
- Output "sounds wrong" or "looks wrong" in numerical comparison
- Investigating spectral leakage, aliasing, or windowing artifacts
- Comparing two algorithm variants visually
- Verifying filter frequency response shape
- Debugging beat/onset detection (overlay detections on waveform)

## When NOT to Use

- Production code paths -- visualisation is debug-only
- Automated CI pipelines -- use `/signal-processing-verification` instead
- As a replacement for measurement -- plots inform intuition; numbers prove correctness

## Visualisation Types

### 1. Waveform (Time Domain)

**Shows:** Signal amplitude over time. Good for: clipping, DC offset, transient shape, silence gaps.

```python
import matplotlib.pyplot as plt
import numpy as np

def plot_waveform(signal, sample_rate, title="Waveform"):
    t = np.arange(len(signal)) / sample_rate
    fig, ax = plt.subplots(figsize=(12, 3))
    ax.plot(t, signal, linewidth=0.5)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title(title)
    ax.set_ylim(-1.1, 1.1)
    plt.tight_layout()
    plt.savefig("/tmp/waveform.png", dpi=150)
    plt.close()
    return "/tmp/waveform.png"
```

### 2. Spectrum (Frequency Domain)

**Shows:** Magnitude per frequency bin. Good for: harmonic content, noise floor, spectral leakage, bin accuracy.

```python
def plot_spectrum(signal, sample_rate, fft_size=None, title="Spectrum"):
    if fft_size is None:
        fft_size = len(signal)
    window = np.hanning(len(signal))
    spectrum = np.fft.rfft(signal * window, n=fft_size)
    magnitude_db = 20 * np.log10(np.abs(spectrum) + 1e-12)
    freqs = np.fft.rfftfreq(fft_size, 1.0 / sample_rate)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(freqs, magnitude_db, linewidth=0.8)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    ax.set_title(title)
    ax.set_xlim(0, sample_rate / 2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("/tmp/spectrum.png", dpi=150)
    plt.close()
    return "/tmp/spectrum.png"
```

### 3. Spectrogram (Time-Frequency)

**Shows:** How frequency content changes over time. Good for: beat tracking visualisation, onset detection, frequency sweeps, time-varying signals.

```python
def plot_spectrogram(signal, sample_rate, fft_size=1024, hop_size=256, title="Spectrogram"):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.specgram(signal, NFFT=fft_size, Fs=sample_rate, noverlap=fft_size - hop_size,
                cmap='magma', vmin=-80, vmax=0)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig("/tmp/spectrogram.png", dpi=150)
    plt.close()
    return "/tmp/spectrogram.png"
```

### 4. Filter Frequency Response

**Shows:** Gain and phase vs frequency. Good for: verifying passband, stopband, transition width, phase linearity.

```python
def plot_filter_response(b, a, sample_rate, title="Filter Response"):
    from scipy.signal import freqz
    w, h = freqz(b, a, worN=2048, fs=sample_rate)
    magnitude_db = 20 * np.log10(np.abs(h) + 1e-12)
    phase_deg = np.degrees(np.unwrap(np.angle(h)))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))
    ax1.plot(w, magnitude_db, linewidth=1.0)
    ax1.set_ylabel("Magnitude (dB)")
    ax1.set_title(title)
    ax1.grid(True, alpha=0.3)

    ax2.plot(w, phase_deg, linewidth=1.0)
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Phase (degrees)")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("/tmp/filter_response.png", dpi=150)
    plt.close()
    return "/tmp/filter_response.png"
```

### 5. Beat Detection Overlay

**Shows:** Waveform with detected beats marked. Good for: visualising false positives, false negatives, timing accuracy.

```python
def plot_beat_overlay(signal, sample_rate, detected_beats, reference_beats=None,
                      title="Beat Detection"):
    t = np.arange(len(signal)) / sample_rate
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(t, signal, linewidth=0.3, alpha=0.6, color='gray')

    for beat in detected_beats:
        ax.axvline(x=beat, color='red', linewidth=0.8, alpha=0.7, label='_detected')

    if reference_beats is not None:
        for beat in reference_beats:
            ax.axvline(x=beat, color='green', linewidth=0.8, alpha=0.5,
                       linestyle='--', label='_reference')

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.set_title(title)
    # Manual legend
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], color='red', label='Detected'),
                       Line2D([0], [0], color='green', linestyle='--', label='Reference')]
    ax.legend(handles=legend_elements, loc='upper right')
    plt.tight_layout()
    plt.savefig("/tmp/beat_overlay.png", dpi=150)
    plt.close()
    return "/tmp/beat_overlay.png"
```

## Process

1. **Identify what to visualise.** What signal or stage of the pipeline is suspicious?
2. **Dump the raw buffer.** Save the intermediate signal to a file (binary or WAV).
3. **Generate the appropriate plot.** Waveform for time-domain, spectrum for frequency-domain.
4. **Compare to expectation.** What should this look like? Compare to golden reference plot if available.
5. **Identify the anomaly.** Spectral leakage? Wrong frequency? Phase issue? Clipping?
6. **Return to `/systematic-debugging`.** The visualisation is evidence for root cause analysis.
7. **Clean up.** Remove debug dumps and plot files when done.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Leaving visualisation code in production | Mark with `// DEBUG:` and remove before commit |
| Plotting without windowing | Apply window function before FFT for spectrum plots |
| Linear frequency axis hiding low-frequency detail | Use log scale for wide-range spectra |
| Not saving to file (only showing) | Always `savefig` so it persists across sessions |
| Plotting entire file when only a section matters | Slice to the region of interest first |

## Red Flags

- Using visualisation AS verification -- plots are for intuition; `/signal-processing-verification` is for proof
- Debug plot code committed to main -- clean up before merge
- Spending more than 15 minutes on visualisation without forming a hypothesis -- switch to `/systematic-debugging`

## Integration

**Called from:** `/systematic-debugging` (when investigating DSP issues)
**Pairs with:** `/signal-processing-verification` (plots inform; verification proves)
**Clean up required:** Remove all generated plot files and debug dump code before `/finishing-a-development-branch`
