# Torch Workflows Reference

## Contents
- DSP Regression Validation Workflow
- A/B Audio Analysis Workflow
- Adding a New Torch Gate to the Test Suite
- Checklist: New Torch Baseline Gate

---

## DSP Regression Validation Workflow

Use this when the K1 audio pipeline changes (Goertzel tuning, AGC scalar, onset flux weights) and you need to confirm the new behaviour against an audio ground truth.

**Iterate-until-pass pattern:**

```
1. Capture K1 frame output with `k1_hardware_harness` build environment
2. Run torch baseline against the same fixture
3. Compare correlation — must exceed gate threshold
4. If below threshold, inspect which frequency bands diverge
5. Fix firmware or update gate with Captain approval
6. Re-run pytest — only proceed when gate passes
```

```python
# new code to add — example regression script
import torch, torchaudio, json, pathlib

def run_gdft_regression(fixture_dir: str, k1_output_json: str) -> None:
    fixtures = list(pathlib.Path(fixture_dir).glob("*.wav"))
    k1_data = json.loads(pathlib.Path(k1_output_json).read_text())
    
    results = []
    for wav in fixtures:
        waveform, sr = torchaudio.load(str(wav))
        if sr != 48000:
            waveform = torchaudio.functional.resample(waveform, sr, 48000)
        
        stem = wav.stem
        if stem not in k1_data:
            continue
        
        k1_bins = k1_data[stem]["gdft_bins"]  # 80 floats from K1 frame capture
        stft = torch.stft(waveform[0], n_fft=1024, return_complex=True)
        mag = stft.abs().mean(dim=-1)
        indices = torch.linspace(0, mag.shape[0] - 1, 80).long()
        corr = torch.corrcoef(torch.stack([
            torch.tensor(k1_bins),
            mag[indices]
        ]))[0, 1].item()
        
        results.append({"fixture": stem, "correlation": corr, "pass": corr > 0.65})
        print(f"{stem}: corr={corr:.3f} {'PASS' if corr > 0.65 else 'FAIL'}")
    
    failed = [r for r in results if not r["pass"]]
    if failed:
        raise SystemExit(f"{len(failed)} fixture(s) failed correlation gate")
```

---

## A/B Audio Analysis Workflow

Maps to the wireless A/B bench methodology documented in `docs/forensics/`. Use when comparing two firmware versions' audio response.

```python
# new code to add
import torch, torchaudio

def ab_onset_comparison(
    fixture_a: str,  # reference firmware capture
    fixture_b: str,  # candidate firmware capture
    sr: int = 48000,
) -> dict:
    """Returns onset envelope comparison between two K1 captures."""
    import torchaudio.transforms as T
    
    def load_mono(path):
        w, s = torchaudio.load(path)
        if s != sr:
            w = torchaudio.functional.resample(w, s, sr)
        return w.mean(dim=0, keepdim=True)
    
    hop = sr // 133  # K1 AP rate
    mel_tf = T.MelSpectrogram(sample_rate=sr, n_mels=24, n_fft=512, hop_length=hop)
    
    def onset_env(w):
        log_mel = torch.log1p(mel_tf(w))
        return torch.relu(log_mel[:, :, 1:] - log_mel[:, :, :-1]).sum(dim=1).squeeze()
    
    env_a = onset_env(load_mono(fixture_a))
    env_b = onset_env(load_mono(fixture_b))
    
    min_len = min(len(env_a), len(env_b))
    delta = (env_b[:min_len] - env_a[:min_len])
    
    return {
        "onset_delta_mean": delta.mean().item(),
        "onset_delta_peak": delta.abs().max().item(),
        "a_peak": env_a.max().item(),
        "b_peak": env_b.max().item(),
        "relative_peak_change_pct": ((env_b.max() - env_a.max()) / env_a.max() * 100).item(),
    }
```

**Interpretation:** `relative_peak_change_pct` below -10% is a regression (matches the -17.6% peak_scaled threshold from the wireless bench run documented in `docs/forensics/`).

---

## Adding a New Torch Gate to the Test Suite

When a new DSP feature needs a torch validation gate, follow this workflow.

**Copy this checklist and track progress:**
- [ ] Step 1: Add fixture `.wav` to `tests/fixtures/tab5/` or `scripts/regression-harness/fixtures/`
- [ ] Step 2: Write torch baseline function in `tests/` (not inline in test)
- [ ] Step 3: Add `@torch_available` skip marker so CI without torch doesn't break
- [ ] Step 4: Assert on correlation or delta, not exact values — firmware and torch will differ
- [ ] Step 5: Run `pytest tests/ -v -k "torch"` and confirm gate passes on current firmware
- [ ] Step 6: Document the gate threshold in the test docstring with the reasoning
- [ ] Step 7: Add the test file to the regression matrix in `CLAUDE.md` if it covers a new DSP surface

**Gate threshold guidance:**

| DSP Feature | Recommended Correlation Gate | Notes |
|-------------|------------------------------|-------|
| GDFT bin energies | > 0.65 | Goertzel vs STFT will naturally diverge |
| Onset envelope | > 0.70 | Per-band log-flux vs mel diff |
| Beat period | ±5% of ground truth | Use peak-finding, not correlation |

See the **pytest** skill for the project's fixture conventions and gate registration patterns. See the **python** skill for import discipline and test file naming.