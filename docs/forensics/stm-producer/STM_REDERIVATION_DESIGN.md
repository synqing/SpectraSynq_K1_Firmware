# STM re-derivation design (K1 native 40-bin)

**Authority:** `SPECTRASYNQ_K1_FIRMWARE/audio/k1_stm.h` on `origin/main` (commit `d40114f` lineage).  
**Status:** Design record restored for WB-3 audit chain — not a shipping sign-off.

## Problem

Donor LightwaveOS STM required `bins256` from a 512-point FFT. K1's Goertzel-only AP path does not provide that vector. A transplant would fabricate or zero-fill — violating `k1_semantic_state` doctrine.

## Approach

Re-derive STM semantics from the **80-note post-AGC spectrogram** (uniform log-frequency / semitone axis):

| Axis | Mechanism |
|------|-----------|
| Temporal modulation | Goertzel over per-band history (~17 frames @ 133.33 Hz) |
| Spectral ripple | 40 bins (= Nyquist half of 80-note axis) |
| 4 Hz probe | Coefficient retuned from donor 125 Hz → 133.33 Hz |

## Published outputs (`K1StmResult`)

- `ready` — false during 17-frame warm-up; outputs **exactly zero** (not fabricated measurements)
- `temporal_energy`, `spectral_energy` — scalars in [0, 1]
- `spectral[40]` — ripple cycles coarse → fine

## Consumer mapping (EdgeMixer)

| K1 field | Mode usage |
|----------|------------|
| `temporal_energy` | STM_DUAL primary strip modulation |
| `spectral_energy` | STM_DUAL secondary |
| `spectral[]` + LED LUT | STM_SPECTRAL_MAP |

## Known debt (hypothesis until clangd)

- 80→40 bin reduction vs donor 42-bin FFT axis
- Centre LED bin mapping may not match centre-origin spec
- Dual read of producer state per frame (audit finding)
- IM73D-specific loudness gate in `a9ff00c` lineage

## Sign-off

**None.** Visual, timing, and production promotion remain open under WB-3.

## Cross-refs

- `WB3_AUTHORITY_MAP.md`
- `WB3_HYPOTHESES_AND_CLAIMS.md`
- Host proof: `scripts/regression-harness/k1_stm_replay.py`
