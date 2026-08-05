# Reference attestation — host VP packet (2026-07-30)

## TB checklist

| ID | Status | Evidence |
|----|--------|----------|
| TB-1 | **DONE** | `scripts/regression-harness/stm_reference_512.py` (`wb3-ref-512-v1`) |
| TB-2 | **DONE** | Reference is NumPy-only; candidate uses `k1_stm.cpp` via `.pio/stm_host_shim.dylib` (separate code paths) |
| TB-3 | **DONE** | Fixture `cal_tone_1khz.wav` + device playback log (Captain authorised) |
| TB-4 | **DONE** | `packet_summary.json` / `manifest.json` executable hashes |
| TB-5 | **DONE** | `ref_ref_repeatability.json` → `all_identical: true` (3 runs) |
| TB-6 | **PARTIAL** | Device: `k1_hardware_stm` flash + `device_playback_cal_tone.log`; no VPAB byte capture |

## H2 machine verdict (ref 512 vs native 40)

**FAIL** (expected): different algorithms (`mean_relative_error` ~0.94). This **closes the VP pipeline**, not product parity.

## Captain sign-off still required

- Independent **human** reviewer line for TB-2
- H5 eyes-on modes 7/8
- Threshold calibration before any PASS claim
