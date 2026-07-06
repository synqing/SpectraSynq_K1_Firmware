# R2 Main K1 SPH0645 to IM73D Decision Handoff - Superseded 2026-07-07

## Verdict

This handoff's original "main-K1 physical swap" blocker is superseded.

The bench K1 and main K1 use identical ESP32-S3 K1 hardware. Captain already
ratified the production IM73D pin map as the bench-proven `clk13/din12/LR14`
map. Therefore, the bench K1 with IM73D on pins `13/12/14` is a valid
production-shape IM73D proof unit.

Do not treat "swap the main K1's SPH0645 to IM73D" as a firmware or
production-shape proof blocker.

## Current State

- Main K1 `F887A500`: SPH0645 reference/control on `k1_hardware @ 67227da`.
- Bench K1 `B489A500`: IM73D production-shape proof unit on radio-free
  `k1_bench_im73d @ 9d14463`.
- Bench hardware: identical K1 hardware to the main unit, with IM73D on the
  ratified production pin map.
- DSR status: DSR16 rejected after controlled-audio measurement; keep `DSR_8S`.

## Corrected Gate

The remaining production proof gate is not a main-unit mic swap. It is:

1. Build/guard/flash the production IM73D env only to a MAC-verified IM73D unit
   with the production K1 hardware map.
2. Use the bench K1 as that IM73D unit unless Captain explicitly asks to convert
   the main K1.
3. Keep the main K1 as the SPH reference/control unless a product-unit swap is
   explicitly requested.

## What Still Needs Care

`k1_prod_im73d` remains upload-guard blocked until the guard policy is updated
deliberately. The correction is not "flash it anywhere"; the correction is that
the allow-list target can be the bench IM73D unit because it is production-shape
hardware.

Expected follow-up for a production-IM73D proof:

- Update `scripts/platformio/k1_upload_guard.py` so `k1_prod_im73d` is allowed
  only on the intended IM73D proof unit.
- Add/update guard tests for that policy.
- Build `k1_prod_im73d`.
- Flash only after live USB MAC verification.
- Read-only `:build` proves `env=k1_prod_im73d` and the expected git.
- Raw pre-conditioning evidence is sane and non-railed.
- Any silence calibration still requires Captain's explicit silence-go.
- `:stream_agc` after 10 s shows all four gains below 10.
- Captain eyes-on accepts the production response before any default-env flip.

## Optional Main-K1 Swap

Converting the main K1 from SPH0645 to IM73D is optional product-unit validation
or product configuration work. It is not required to prove the production pin
map or firmware path, because the bench IM73D unit already represents identical
K1 hardware on the ratified pin map.

If Captain later chooses to convert the main K1, the old swap checklist can be
reused as a hardware-work checklist only. It must not be treated as the gate
that blocks firmware proof on the bench IM73D unit.
