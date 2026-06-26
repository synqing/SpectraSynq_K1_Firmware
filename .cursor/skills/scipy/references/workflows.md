# SciPy Workflows Reference

## Contents
- Offline DSP Validation Workflow
- A/B Comparison Pipeline
- Building Test Fixtures from Reference Audio
- Integrate with pytest Gates

---

## Offline DSP Validation Workflow

Use this when validating a firmware audio change without a device (host-only).

```
Copy this checklist and track progress:
- [ ] Collect AP-stream capture (scripts/regression-harness/apstream_ingest.py)
- [ ] Load into numpy arrays via diag_helpers.py
- [ ] Compute scipy spectrum / onset / tempo reference
- [ ] Compare against firmware logged values
- [ ] Assert within tolerance via pytest
- [ ] Commit fixture + assertion to tests/
```

```python
# new code to add — typical notebook/harness entry point
import numpy as np
from scipy.fft import rfft, rfftfreq
from scipy.signal import find_peaks, welch

# Load from apstream capture (see diag_helpers.py)
# frames: (N_frames, frame_len) float32 array
frames = np.load("capture.npy")

FS = 48_000
novelty = np.array([rfft(f).__abs__().sum() for f in frames])  # crude onset proxy
f_psd, psd = welch(novelty, fs=133.0 / 3, nperseg=128)        # 44.4 Hz novelty rate
dominant_bpm = f_psd[np.argmax(psd)] * 60.0
print(f"Dominant BPM: {dominant_bpm:.1f}")
```

---

## A/B Comparison Pipeline

When comparing baseline vs. candidate firmware builds (e.g., validating the forward-graft tempo changes), follow this structure:

```python
# new code to add
from scipy.stats import pearsonr, ks_2samp
from scipy.signal import find_peaks
import numpy as np

def compare_tempo_streams(baseline_bpm: np.ndarray,
                          candidate_bpm: np.ndarray) -> dict:
    r, p = pearsonr(baseline_bpm, candidate_bpm)
    ks_stat, ks_p = ks_2samp(baseline_bpm, candidate_bpm)
    mae = np.mean(np.abs(baseline_bpm - candidate_bpm))
    return {"pearson_r": r, "pearson_p": p,
            "ks_stat": ks_stat, "ks_p": ks_p, "mae_bpm": mae}
```

**Iterate-until-pass:**
1. Run A/B comparison: `python scripts/run_ab_compare.py`
2. Check `pearson_r >= 0.90` and `mae_bpm < 5.0`
3. If either fails, inspect the novelty curve and onset alignment, not just the BPM scalar
4. Repeat after adjusting firmware parameters or Python extraction logic

---

## Building Test Fixtures from Reference Audio

```python
# new code to add — generates deterministic fixture for pytest
from scipy.io import wavfile
from scipy.signal import resample_poly
import numpy as np
import json

def build_fixture(wav_path: str, expected_bpm: float,
                  out_path: str = "tests/fixtures/tempo_ref.npz") -> None:
    rate, data = wavfile.read(wav_path)
    if rate != 48_000:
        # Resample to firmware rate without changing duration
        data = resample_poly(data, 48_000, rate).astype(np.float32)
    np.savez(out_path, audio=data / 32768.0, expected_bpm=expected_bpm)
    print(f"Fixture saved: {out_path}  ({len(data)/48000:.1f}s, {expected_bpm} BPM)")
```

**Why `resample_poly` not `resample`:** `resample` uses FFT-based resampling that introduces ringing on transients. `resample_poly` uses polyphase FIR, which preserves onset sharpness — critical for beat tracking fixture accuracy.

---

## Integrate with pytest Gates

```python
# new code to add — tests/test_tempo_scipy_gate.py
import numpy as np
import pytest
from scipy.signal import find_peaks, welch

NOVELTY_FS = 44.4  # Hz — AP rate / 3

@pytest.fixture
def novelty_stream(tmp_path):
    # Replace with actual apstream_ingest output in CI
    return np.load("tests/fixtures/novelty_baseline.npy")

def test_dominant_bpm_within_tolerance(novelty_stream):
    f, psd = welch(novelty_stream, fs=NOVELTY_FS, nperseg=256)
    mask = (f >= 0.5) & (f <= 4.0)
    bpm = f[mask][np.argmax(psd[mask])] * 60.0
    assert abs(bpm - 120.0) < 5.0, f"BPM {bpm:.1f} outside 115–125 tolerance"

def test_onset_density_in_band(novelty_stream):
    peaks, _ = find_peaks(novelty_stream,
                          height=np.percentile(novelty_stream, 70),
                          distance=int(NOVELTY_FS * 0.2))
    density = len(peaks) / (len(novelty_stream) / NOVELTY_FS)
    assert density >= 1.5, f"Onset density {density:.2f}/s too low (expected ≥1.5)"
```

**Gate iteration protocol:**
1. Run: `pytest tests/test_tempo_scipy_gate.py -v`
2. On failure, plot `novelty_stream` with `find_peaks` markers before adjusting thresholds
3. Never relax the tolerance — widen the fixture window instead
4. See the **pytest** skill for fixture organisation patterns

---

## DO / DON'T

| DO | DON'T |
|----|-------|
| Use `rfft` for real audio | Use `np.fft.fft` (wastes half the output) |
| Use `sosfilt` + `sos` output | Use `lfilter` with `ba` on high-order filters |
| Set `distance` on `find_peaks` | Call `find_peaks` without `distance` on noisy curves |
| Match `FS = 48_000` everywhere | Use 44100 or 22050 (firmware is 48 kHz) |
| Pin scipy version in `pyproject.toml` | Rely on transitive version from numpy |