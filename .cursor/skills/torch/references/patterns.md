# Torch Patterns Reference

## Contents
- Audio Fixture Loading
- GDFT vs STFT Comparison
- Onset / Beat Baseline Patterns
- Anti-Patterns
- Pytest Integration

---

## Audio Fixture Loading

K1 test fixtures live in `tests/fixtures/tab5/` and `scripts/regression-harness/fixtures/`. Always assert sample rate before processing.

```python
# new code to add
import torch, torchaudio

def load_k1_fixture(path: str) -> tuple[torch.Tensor, int]:
    waveform, sr = torchaudio.load(path)
    assert sr == 48000, f"K1 fixture must be 48kHz, got {sr} for {path}"
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)  # force mono
    return waveform, sr
```

---

## GDFT vs STFT Comparison

The K1 Goertzel GDFT computes 80 frequency bins mapped to 24 perceptual octave bands at 133 Hz. A torch STFT is the validation baseline — they will differ (Goertzel is IIR per-bin, STFT is block DFT), so gate on **correlation**, not equality.

```python
# new code to add
import torch, torchaudio

def gdft_stft_correlation(
    waveform: torch.Tensor,
    k1_bin_energies: list[float],  # 80 values from K1 GDFT frame
    n_fft: int = 1024,
) -> float:
    stft = torch.stft(waveform[0], n_fft=n_fft, return_complex=True)
    mag = stft.abs().mean(dim=-1)  # average over time → (n_fft/2+1,)
    
    # Sub-sample STFT to match K1's 80-bin output
    indices = torch.linspace(0, mag.shape[0] - 1, 80).long()
    stft_sampled = mag[indices]
    
    k1 = torch.tensor(k1_bin_energies)
    corr = torch.corrcoef(torch.stack([k1, stft_sampled]))[0, 1]
    return corr.item()
```

**Gate:** correlation > 0.65 is a passing baseline. Below 0.5 indicates a DSP regression.

---

## Onset / Beat Baseline Patterns

K1 uses per-band log-flux onset. The torch equivalent uses a mel spectrogram with half-wave rectified first-difference.

```python
# new code to add
import torch
import torchaudio.transforms as T

def mel_onset_envelope(
    waveform: torch.Tensor,
    sr: int = 48000,
    n_mels: int = 24,   # match K1's 24 octave bands
    frame_rate: int = 133,  # match K1 AP rate
) -> torch.Tensor:
    hop = sr // frame_rate  # ~361 samples
    mel = T.MelSpectrogram(
        sample_rate=sr, n_mels=n_mels, n_fft=512, hop_length=hop
    )(waveform)
    log_mel = torch.log1p(mel)
    diff = torch.relu(log_mel[:, :, 1:] - log_mel[:, :, :-1])
    return diff.sum(dim=1).squeeze()  # (time_frames,)
```

---

## Anti-Patterns

### WARNING: GPU tensors passed to numpy

**The Problem:**
```python
# BAD — crashes if CUDA is available
arr = some_tensor.numpy()
```

**Why This Breaks:** `.numpy()` requires CPU tensors. On a dev machine with CUDA, this raises `RuntimeError`.

**The Fix:**
```python
# GOOD — always safe
arr = some_tensor.detach().cpu().numpy()
```

---

### WARNING: Using torch for on-device inference

**The Problem:** Importing torch in firmware or proposing torch-based inference on the ESP32.

**Why This Breaks:** The ESP32-S3 has 512 KB SRAM and 8 MB PSRAM. PyTorch requires gigabytes of runtime. Firmware DSP is Goertzel + PLL — no neural inference.

**The Fix:** Torch is host-only. If a model output is useful on-device, bake the result into a C++ lookup table or constant array.

---

### WARNING: 44.1 kHz fixtures used without resampling

```python
# BAD — silent mismatch, all frequency analysis is wrong
waveform, sr = torchaudio.load("fixture.wav")
stft = torch.stft(waveform[0], n_fft=1024, ...)  # sr may be 44100, not 48000
```

**The Fix:**
```python
# GOOD
waveform, sr = torchaudio.load("fixture.wav")
if sr != 48000:
    waveform = torchaudio.functional.resample(waveform, sr, 48000)
```

---

## Pytest Integration

Gate torch-based analysis inside `pytest.mark` so host regression runs don't fail on machines without torch.

```python
# new code to add
import pytest

torch_available = pytest.mark.skipif(
    not __import__("importlib").util.find_spec("torch"),
    reason="torch not installed"
)

@torch_available
def test_gdft_stft_correlation(audio_fixture_path, k1_gdft_frame):
    waveform, _ = load_k1_fixture(audio_fixture_path)
    corr = gdft_stft_correlation(waveform, k1_gdft_frame)
    assert corr > 0.65, f"GDFT/STFT correlation {corr:.3f} below gate"
```

See the **pytest** skill for fixture conventions and gate patterns used across this project.