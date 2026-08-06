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

## Bench spike procedure (Track B — documentation step)

Execute only on a **separate** worktree/branch from Track A; flash is mutually exclusive.

1. **Gate 0:** clangd smoke clean on spike branch (`GATE0_CLANGD_BLOCKER.md`).
2. **Reference:** Satisfy `WB3_REFERENCE_ATTESTATION.md` Track B checklist (or stop — spike stays host-only).
3. **Branch:** `bench/wb3-track-b-fft512` (or Captain-named) from `origin/main`; bench env with FFT flag **only** (no `K1_STM`).
4. **Static buffers:** Pre-allocate PCM ring (512 samples), window, FFT workspace in init — **no heap** in audio hot path.
5. **Microbenchmark:** Log `esp_timer_get_time()` around 512-pt FFT + envelope + 42-bin LUT for N≥1000 frames; export CSV to `artifacts/stm-track-b/<run-id>/fft_microbench.csv`.
6. **Core-0:** Follow `WB3_CORE0_BENCH_PROCEDURE.md` with treatment = FFT bench image, baseline = `k1_hardware` or Captain-named rollback.
7. **VP:** When reference valid, `stm_vp_compare.py` reference vs candidate captures → `artifacts/stm-track-b/<run-id>/vp/`.
8. **Registry:** MAC, rollback commit, env name in `manifest.json`.

**Host-only fallback:** Steps 4–5 can run as native/off-device prototype **without** flash if reference is host Python — still publish under `artifacts/stm-track-b/` with `flash_required: false`.

## Bench spike procedure (Track B)

1. **Worktree:** Branch from `origin/main`; confirm `K1_STM` **undefined** in spike env.
2. **Flag:** Add bench-only `-DK1_STM_FFT512_BENCH=1` (name as implemented) — **mutually exclusive** with `-DK1_STM`.
3. **Buffers:** Static PCM ring 512 samples + FFT workspace in PSRAM or DRAM at init — **no heap** in audio hop callback.
4. **Microbenchmark:** `esp_timer_get_time()` around FFT + envelope + 42-bin LUT; log p50/p95 over ≥1000 hops to `artifacts/stm-track-b/<run-id>/fft_microbench.json`.
5. **Core-0:** Same treatment/control protocol as Track A (`WB3_CORE0_BENCH_PROCEDURE.md`) with FFT flag on.
6. **VP:** Only when `WB3_REFERENCE_ATTESTATION.md` TB-1–TB-4 close; run `stm_vp_compare.py` reference vs FFT candidate.
7. **Rollback:** Record bench MAC + prior image in `flash_manifest.yaml` before any upload.

**Captain blockers:** device allocation, playback fixtures, reference source approval.

## Explicit non-actions this programme

- No `FEATURE_FFT_STM` in `k1_hardware`.
- No second producer enabled alongside native STM in production.
- No claim that ESTIMATED µs figures substitute for Phase 4 measurement.
