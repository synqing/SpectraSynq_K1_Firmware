# Gate 2 — Cross40 × Lane-4 promotion evidence

**Date:** 2026-08-16  
**Branch:** `feat/k1-scheduling-generation-hardening`  
**Authority:** Captain restamp 2026-08-16 (`AP_SERVICE_P99_LIMIT_US = 8000`, `G2_GDFT_CONTRACT = CROSS40_PLUS_LANE4`)

## Status

```text
G2_HOST_PROMOTION     = CLOSED
G2_DEVICE_CONFIRM     = CLOSED
G2_UNIT_STATUS        = CLOSED
G2_DEVICE             = CLOSED
HOLD_REASON           = none
G3_UNBLOCK            = YES
```

Captain 2026-08-17: eyes-on PASS on bench K1v2 `B489A500` running `k1_bench_im69d` @ `e911f86d` (epoch `1786903366`). Live `:build` identity confirmed 2026-08-17 before the stamp.

2026-08-17 B489 package A/B soak (`docs/forensics/runtime-evidence/20260817T-g2g3-e2e-ab-b489/`): eight admissible legs, contract p99 **8000 µs**. Arm B (`e911f86d` Cross40+Lane4 full probe) quiet p99_high **7680 µs** / music **7776 µs**, consecutive over-period **1**, sample_age STABLE, drops 0, generation discontinuities 0. Arm A (pre-restamp Cross0 full probe) quiet **11840 µs** / music mean **11984 µs**. Historical G2 music 7712 µs remains `REFERENCE_ONLY_NOT_AN_ABBA_LEG`. Numeric probe PASS plus Captain eyes-on PASS stamp `G2_DEVICE = CLOSED`.

## Production flags added to `env:k1_hardware`

```ini
-DK1_GDFT_X2_CROSSOVER_BIN=40u
-DK1_GDFT_LANE4_V1=1
```

Revert = delete those two lines (restores Cross0 scalar).

## Alias contract

- Production selector: `K1_GDFT_LANE4_V1`
- Compatibility alias: `K1_GDFT_LANE4_PROBE` still selects the identical backend when V1 is unset
- Host bit-identity under Cross40: `tests/test_gdft_lane4_cross40_combined.py`

## Binary identity (post-promotion build)

| Artefact | SHA-256 | Size |
|---|---|---:|
| `.pio/build/k1_hardware/firmware.bin` | `8e0007d47f9e5d3edcbae61f2c8bdfa3f8c25d5054ed86fe2197415c7efbcfb7` | 701360 |
| `.pio/build/k1_hardware/firmware.elf` | `8b0f1bd9deca1236d0d71f082e85a51d4fe1c3f7fd539cc755afad89ace54008` | — |

Build HEAD at capture: `8f53c48e5f6635474d4a07b01ac0cfff9df173b3` (tree dirty with this promotion work).

## Probe evidence (map ≠ territory)

Re-scored pack: `docs/forensics/runtime-evidence/20260816T-g2-lane4-cross40/`  
Environment: `k1_bench_scheduling_gdft_cross40_lane4_full_probe` (not `k1_hardware`).

Caveats carried forward:

1. Probe music compact soak p99 may pass 8000 µs while still exceeding the 7500 µs hop on emit frames.
2. Music-leg single-frame max above 8000 µs is judged against the measured DMA cushion, not against the p99 ceiling.
3. Map≠territory: probe pass ≠ production close until `k1_hardware` is confirmed on B489 under a named GO.
4. Growing sample-age on any no-playback leg remains a live risk for the device close predicate.

## Host gate

- `tests/test_gdft_cross40_lane4_production_promotion.py`
- `tests/test_g2_production_gdft_contract.py`
- `tests/test_gdft_lane4_exact_probe.py`
- `tests/test_gdft_lane4_cross40_combined.py`
- `tests/test_scheduling_gdft_service_matrix.py` (Cross0 baseline via `build_unflags`)

## Device close predicate — CLOSED 2026-08-17

**Already promoted:** Cross40+Lane-4 flags are in `k1_hardware`. Bench silicon is `k1_bench_im69d` @ `e911f86d` (epoch `1786903366`). Probe numeric gate PASS (quiet 7680 µs, music 7776 µs vs 8000). Captain eyes-on PASS. `G2_DEVICE = CLOSED`.

**Remaining ship path after G2:**

1. G3–G7A host units on this branch (this session). No F887 flash.
2. G7B needs a named `B489_G7B_FLASH` GO.
3. G8 + a **separate Captain GO** flashes main K1 (`F887A500`). That is main-unit promote.
