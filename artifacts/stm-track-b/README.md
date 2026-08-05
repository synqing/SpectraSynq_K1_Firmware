# Track B — 512-point FFT STM evidence bundle

**Track:** WB-3 Track B (bench FFT producer, **mutually exclusive** with `K1_STM`).  
**Policy:** `docs/forensics/stm-producer/WB3_REFERENCE_ATTESTATION.md`, spike steps in `WB3_FFT512_FEASIBILITY.md`.

## Reference gate (Gate B)

**2026-07-29:** Captain **waived** TB-1..TB-4 for **spike-only** execution.  
Waiver: `reference_waiver_gate_b_2026-07-29.md` and `gate_b_spike_2026-07-29/reference_waiver_gate_b_2026-07-29.md`.

VP reference-vs-candidate closure is **out of scope** for this packet.

## Firmware

| Env | Flag | `K1_STM` |
|-----|------|----------|
| `k1_hardware_fft512_bench` | `K1_STM_FFT512_BENCH=1` | **off** |

Build: `pio run -e k1_hardware_fft512_bench`  
Flash (main K1 F887A500): `pio run -e k1_hardware_fft512_bench -t upload --upload-port /dev/cu.usbmodem112401`

### Serial (115200, `:` prefix)

- `:fft512_bench=report` — stats (p50/p95/us_max)
- `:fft512_bench=burst,1000` — synthetic 1 kHz burst microbench
- `:fft512_bench=live_hop,on|off` — Core-0 AP-frame integration hook
- `:fft512_bench=reset` — clear counters

## Run `gate_b_spike_2026-07-29`

| Artefact | Status |
|----------|--------|
| `manifest.json` | **GROUNDED** |
| `reference_waiver_gate_b_2026-07-29.md` | **GROUNDED** |
| `fft_microbench.json` | **CAPTURED** (burst n=1000; live_hop hop_count=0 at idle — AP path not ticking in soak) |
| `core0/` | **INDETERMINATE** — formal Phase B/C not run |
| `vp/` | **Skipped** per Gate B waiver |

See `gate_b_spike_2026-07-29/FLASH_AND_CAPTURE.md` for capture steps.
