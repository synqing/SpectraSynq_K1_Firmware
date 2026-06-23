---
abstract: "Alias-aware per-Goertzel-bin frequency honesty for K1 (DEFAULT profile, NOTE_OFFSET=12, fs=12800, Nyquist=6400). TWO truths: (1) representable bins (target<=Nyquist) resonate BELOW their note label due to rounded k - A4 440 Hz peaks ~420 Hz, worst ~-248 Hz at bin 70/~6.27 kHz; (2) 9 bins (71-79) are labelled ABOVE Nyquist and are NOT physically representable - their raw Goertzel centre folds into the real band (bin 76 '8870 Hz' -> raw 8533 -> effective 4267 Hz). raw_center_hz != effective_center_hz above Nyquist. Measurement-only host reconstruction; firmware is source of truth. Energy counterpart: high_bin_alias_audit.py. Read before un-rounding k or any window A/B."
---

# K1 GDFT Per-Bin Frequency Honesty (alias-aware, DEFAULT profile)

> Host reconstruction of `precompute_goertzel_constants()` (`system.h`). Measurement-only — **no coefficient change, no firmware change, no VP change.** Firmware is source of truth; validated by `tests/test_gdft_center_honesty.py`. Energy-side counterpart: `scripts/regression-harness/high_bin_alias_audit.py`.
> **Full 80-row table:** `python3 scripts/regression-harness/gdft_center_honesty_model.py`

## Config
`fs = 12800 Hz` · **`Nyquist = 6400 Hz`** · `NUM_FREQS = 80` · `NOTE_OFFSET = 12` (bins span `notes[12..91]`, 110 Hz → ~11.8 kHz) · `block_size_cap = 2000` (never reached on this profile).

## Sampling honesty first (the correction)

At `fs = 12800` the real-audio band is `[0, 6400] Hz`. A magnitude-only Goertzel on a **real** sampled signal cannot distinguish `f` from `fs − f`, so any centre or label above Nyquist **folds**: `f_eff = fs − (f mod fs)` when `(f mod fs) > Nyquist`. Therefore `raw_center_hz = k·fs/block_size` is **not** a physically distinct real-audio centre once it exceeds 6400 Hz — `effective_center_hz` (the fold) is.

- **9 bins (71–79) are labelled ABOVE Nyquist** (6645 Hz → 10548 Hz). These notes are **not representable** at 12.8 kHz. The firmware is aware: `sb_gdft_nyquist_safe_bin_hi()` (`constants.h`) clamps the downstream onset / `AudioSemanticState` consumers to the safe range (`sb_audio_snapshot.cpp`, `sb_onset_beat.cpp`). `process_GDFT` still computes all 80 magnitudes (consumed directly by VP effects), so their **aliased** response is real even though the label is not.
- Every `effective_center_hz ≤ 6400 Hz` by construction. Example: bin 76, label 8869.84 Hz → raw 8533 Hz → **effective 4267 Hz** (and the label itself folds to 3930 Hz).

## The rounded-k offset (representable bins, target ≤ Nyquist)

For bins whose note IS representable, the rounded integer `k` (block_size sized for resolution → `block_size·target/fs ≈ 8.4` → `k = 8` for every bin) still pulls the centre **below** the label:

- **440 Hz / A4 → resonates ~420 Hz (−20 Hz, ~0.8 semitone low).**
- Worst representable error **−248 Hz at bin 70 (label 6271.9 Hz**, just under Nyquist).
- Resolution cells widen with frequency: **13.1 Hz** (low) → **1280 Hz** (top); ≈ 2 semitones wide by mid-range.

This is the evidence for the next decision — **un-round k** for representable bins (a coefficient change, device A/B required). Above Nyquist, un-rounding does *not* create real >6.4 kHz sensitivity; it only changes the folded response.

## Representative bins

| bin | target_hz | >Nyq | target_folded_hz | block_size | k | raw_center_hz | effective_center_hz | label_error_hz | true_res_hz |
|----:|----------:|:---:|-----------------:|-----------:|--:|--------------:|--------------------:|---------------:|------------:|
| 0 | 110.00 | | 110.00 | 978 | 8 | 104.70 | 104.70 | -5.30 | 13.1 |
| 24 | 440.00 | | 440.00 | 244 | 8 | 419.67 | 419.67 | -20.33 | 52.5 |
| 60 | 3520.00 | | 3520.00 | 30 | 8 | 3413.33 | 3413.33 | -106.67 | 426.7 |
| 70 | 6271.93 | | 6271.93 | 17 | 8 | 6023.53 | 6023.53 | -248.40 | 752.9 |
| 71 | 6644.88 | yes | 6155.13 | 16 | 8 | 6400.00 | 6400.00 | n/a | 800.0 |
| 76 | 8869.84 | yes | 3930.16 | 12 | 8 | 8533.33 | 4266.67 | n/a | 1066.7 |
| 79 | 10548.08 | yes | 2251.92 | 10 | 8 | 10240.00 | 2560.00 | n/a | 1280.0 |

`label_error_hz = effective_center − target`, reported **only** where the label is representable; above Nyquist it is `n/a` (the note cannot be measured at this fs). For above-Nyquist bins compare `raw_center_hz` (bare Goertzel) vs `effective_center_hz` (folded real centre).

## Device verification — 2026-06-21 (bench K1 `B489A500`, synthetic GDFT harness)

Confirmed on hardware via the deterministic `gdft_probe` harness (`k1_bench_reference_harness`, no mic). The rounded-k centre offset is **product-visible**:

| sent tone | wins bin | bin label | observation |
|---|---|---|---|
| 415.3 Hz (G#4) | bin 24 | 440.00 (A4) | G#4 lights the A4-labelled bin |
| **440.0 Hz (A4)** | **bin 26** | **493.88 (B4)** | **A4 lights the B4-labelled bin** |
| 420.0 Hz | bin 24 | 440.00 (A4) | confirms bin 24 centre ≈ 420 |

`gdft_check.py` absolute-mapping FAILED on every probed tone (+60…+163 cents high); alias contamination confirmed (2509 & 2754 Hz → bin 78, label 9956 Hz, above Nyquist). This device evidence clears the gate for the exact-frequency-coefficient experiment (`feat/gdft-true-center-ab`).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-21 | agent:claude-code | Alias-aware correction: split representable (rounded-k offset) from above-Nyquist (folded, not representable); added Nyquist/fold fields; corrected the prior "bin 76 resonates at 8533 Hz" claim (folds to 4267 Hz). |
| 2026-06-21 | agent:claude-code | Created — host per-bin frequency-honesty reconstruction + findings (branch `feat/gdft-center-honesty`). |
