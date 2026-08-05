# Gate B waiver — Track B spike-only (2026-07-29)

**Authority:** Captain green-lit Reference gate (B) for **spike-only** execution.

## Scope

- Firmware: `k1_hardware_fft512_bench` (`-DK1_STM_FFT512_BENCH=1`, **no** `-DK1_STM`).
- Deliverables: 512-pt kiss FFT microbenchmark, live-hop Core-0 integration hook, serial `:fft512_bench=*` reporting.
- **Out of scope for this packet:** TB-1..TB-4 independent reference attestation, `stm_vp_compare.py` reference-vs-candidate closure.

## Deferred (unchanged INDETERMINATE)

| Item | Status |
|------|--------|
| TB-1..TB-4 reference oracle | INDETERMINATE |
| VP parity | Skipped per waiver |
| Core-0 Phase B/C full matrix | Partial — live_hop stats only until formal soak |

## Revisit trigger

Captain requests H2 parity closure or production FFT STM path.
