# WB-3 512-point FFT feasibility fact sheet

**Scope:** Bounded analysis only — **no production FFT integration** (plan Phase 5).

**RBDO:** **DEGRADED-MODE** — CPU estimates are **ESTIMATED** from architecture facts, not measured on-device.

## Raw-PCM seam (VERIFIED from product architecture)

| Fact | Implication |
|------|-------------|
| K1 AP path uses Goertzel / spectrogram @ 12.8 kHz, hop 96 (~133.33 Hz) | 512-pt FFT needs **parallel** history buffer on raw PCM |
| Donor STM used 512-pt real FFT → 256 mags → envelope → 42 bins | Not present on K1 today |
| `k1_stm.h` documents re-derivation from 80-note spectrogram | Native path avoids FFT entirely |

**Seam options (conceptual):**

1. **Side-chain tap** from I2S ring (512 samples) — extra Core-0 work per hop; must not block existing AP budget.
2. **Offline reference only** — host Python for H2 reference attestation; zero firmware cost.

## Resource envelope (ESTIMATED)

| Resource | Order of magnitude | Notes |
|----------|-------------------|--------|
| PCM history | 512 × 2 bytes min (int16) | Plus window coefficients |
| FFT workspace | ~2–4 KB static | ESP-DSP / kissfft-class; **no heap in hot path** |
| CPU per frame | **ESTIMATED 200–800 µs** class for 512 real FFT on S3 @ 240 MHz | **Must measure** before Path B |
| Latency | +1 FFT window vs current AP | Conflicts with sub-8 ms AV goal if duplicated |
| Flash | +10–40 KB | Depends on library |

## Opportunity cost

- Duplicates frequency analysis already embodied in `spectrogram[80]`.
- Path B requires **mutually exclusive** bench flag vs native `K1_STM` (plan §14).
- Authority-chain work (single snapshot, LUT, serial bounds) largely **shared** with Path A.

## Feasibility verdict (engineering, not product)

| Criterion | Assessment |
|-----------|------------|
| Technically possible on ESP32-S3 | **Likely yes** with static buffers and bench flag |
| Bounded without violating hard RT | **INDETERMINATE** until Core-0 measure |
| Delivers independent 42-bin oracle | **Yes** if built separately from `k1_stm.cpp` |
| Worth product cost vs native 40-bin | **Captain decision (H5 + Path B)** |

## Explicit non-actions this programme

- No `FEATURE_FFT_STM` in `k1_hardware`.
- No second producer enabled alongside native STM in production.
- No claim that ESTIMATED µs figures substitute for Phase 4 measurement.
