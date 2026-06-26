# SciPy Patterns Reference

## Contents
- FFT and Spectral Analysis
- Filtering (IIR/FIR)
- Peak and Onset Detection
- Statistical Regression Testing
- Anti-Patterns

---

## FFT and Spectral Analysis

Use `scipy.fft.rfft` for real-valued audio — it's half the cost of the full FFT and avoids the redundant negative-frequency mirror.

```python
# new code to add
from scipy.fft import rfft, rfftfreq
import numpy as np

def octave_band_energy(frame: np.ndarray, fs: float = 48000.0,
                       n_bands: int = 24) -> np.ndarray:
    """Map FFT bins to 24 log-spaced octave bands (mirrors firmware GDFT layout)."""
    mag = np.abs(rfft(frame))
    freqs = rfftfreq(len(frame), d=1.0 / fs)
    f_min, f_max = 20.0, 20000.0
    edges = np.logspace(np.log10(f_min), np.log10(f_max), n_bands + 1)
    energy = np.array([
        mag[(freqs >= edges[i]) & (freqs < edges[i+1])].sum()
        for i in range(n_bands)
    ])
    return energy
```

**Why log-spaced edges matter:** the firmware Goertzel banks are octave-distributed. Using linear FFT bins for comparison will produce mismatched energy per band and false regression failures.

---

## Filtering (IIR/FIR)

Replicate firmware high-pass and AGC behaviours in Python for offline A/B validation.

```python
# new code to add
from scipy.signal import butter, sosfilt

def highpass_like_firmware(signal: np.ndarray, cutoff_hz: float = 80.0,
                            fs: float = 48000.0) -> np.ndarray:
    sos = butter(4, cutoff_hz / (fs / 2), btype='high', output='sos')
    return sosfilt(sos, signal)
```

**Always use `sos` (second-order sections) output, never `ba`.** Transfer function coefficients (`b, a`) are numerically unstable for high-order filters; `sos` avoids coefficient blow-up entirely. `lfilter(b, a, x)` on a 4th-order filter at 48 kHz WILL produce NaN on some audio.

---

## Peak and Onset Detection

```python
# new code to add
from scipy.signal import find_peaks

def detect_onsets(novelty_curve: np.ndarray, fs_novelty: float = 44.4,
                  min_gap_s: float = 0.15) -> np.ndarray:
    """
    Ground-truth onset extractor for test fixtures.
    fs_novelty = 44.4 Hz = AP rate 133 Hz / 3 (novelty decimation factor).
    """
    min_distance = int(min_gap_s * fs_novelty)
    threshold = np.percentile(novelty_curve[novelty_curve > 0], 65)
    peaks, props = find_peaks(novelty_curve, height=threshold,
                              distance=min_distance, prominence=threshold * 0.3)
    return peaks
```

### WARNING: Using `find_peaks` Without `distance`

**The Problem:**
```python
# BAD — returns hundreds of adjacent samples on a noisy novelty curve
peaks, _ = find_peaks(novelty, height=0.5)
```

**Why This Breaks:** On a 44.4 Hz novelty signal with any smoothing lag, a single beat onset produces 3–6 consecutive samples above threshold. Without `distance`, you get a cluster of "detections" for one beat, inflating your density metric and making A/B comparisons meaningless.

**The Fix:** Always set `distance=int(min_gap_s * fs_novelty)` — 0.15 s minimum gap (≈ 200 BPM maximum) is a safe floor.

---

## Statistical Regression Testing

Use `scipy.stats` for significance testing in pytest regression gates.

```python
# new code to add
from scipy.stats import pearsonr, ks_2samp
import numpy as np

def assert_tempo_regression(baseline: np.ndarray, candidate: np.ndarray,
                             r_threshold: float = 0.90) -> None:
    """Fail the test if correlation drops below threshold."""
    r, p = pearsonr(baseline, candidate)
    assert r >= r_threshold, (
        f"Tempo regression: r={r:.3f} < {r_threshold} (p={p:.4f})"
    )

def assert_distribution_stable(baseline: np.ndarray, candidate: np.ndarray,
                                alpha: float = 0.05) -> None:
    """KS test — fail if distributions diverge significantly."""
    stat, p = ks_2samp(baseline, candidate)
    assert p >= alpha, f"Distribution shift detected: KS={stat:.3f}, p={p:.4f}"
```

**Use `ks_2samp` for energy distributions, `pearsonr` for time-series tracking.** Don't use `np.corrcoef` in assertions — it doesn't give a p-value and silently passes on short arrays with random correlation.

---

## Anti-Patterns

### WARNING: `np.fft.fft` on Real Audio

**The Problem:** `np.fft.fft` computes complex output including the conjugate-symmetric negative half — double the memory and compute for no benefit on real signals.

**The Fix:** Always use `scipy.fft.rfft` / `rfftfreq` for real-valued audio frames.

### WARNING: `signal.lfilter` with High-Order `ba` Coefficients

Already covered above — use `sos` output from `butter`/`cheby2`/etc. and `sosfilt`. This is not optional.

### WARNING: Hardcoded Sample Rates

```python
# BAD
freqs = rfftfreq(4096, d=1/44100)

# GOOD — match the firmware constant
FS = 48_000  # I2S hardware rate; do not change (see CLAUDE.md)
freqs = rfftfreq(len(frame), d=1.0 / FS)
```

The firmware runs at 48 kHz. Using 44.1 kHz shifts every frequency bin by ~9%, producing systematic errors in octave-band energy comparisons.