# R2 Main K1 SPH0645 to IM73D Decision Handoff - Superseded 2026-07-07

## Verdict

This handoff's original "main-K1 physical swap" blocker is superseded.

The bench K1 and main K1 use identical ESP32-S3 K1 hardware. Captain already
ratified the production IM73D pin map as the bench-proven `clk13/din12/LR14`
mic map. Therefore, the bench K1 with IM73D on pins `13/12/14` is a valid
IM73D PDM proof unit.

Do not treat "swap the main K1's SPH0645 to IM73D" as a mic-path firmware proof
blocker. Do treat env choice as explicit configuration:
`k1_bench_im73d` drives GPIO `4/5`, while `k1_prod_im73d` drives GPIO `6/7`.
A 2026-07-07 bench flash of `k1_prod_im73d` made both LED channels dark because
that was the wrong env for the restored bench configuration, not evidence of
different K1 hardware.

## Current State

- Main K1 `F887A500`: SPH0645 reference/control on `k1_hardware @ 67227da`.
- Bench K1 `B489A500`: IM73D mic/PDM proof unit on radio-free
  `k1_bench_im73d`; after the 2026-07-07 dark-output incident it was uploaded
  back to `k1_bench_im73d @ f2f7c45` and read-only `:build`/`:dump` proved the
  restored env, chip `B489A500`, `CONFIG.CHROMA: 0.100000`, and persisted
  calibration validity.
- Bench hardware: identical K1 hardware to the main unit, with IM73D on the
  ratified PDM mic pin map.
- DSR status: DSR16 rejected after controlled-audio measurement; keep `DSR_8S`.

## Corrected Gate

The remaining production proof gate is not a main-unit mic swap. It is:

1. Use `k1_bench_im73d` for the bench/reference LED map (`4/5`).
2. Use `k1_prod_im73d` for the main/prod LED map (`6/7`).
3. Device-prove the selected env before any default-env flip.
4. Keep the main K1 as the SPH reference/control unless a product-unit swap is
   explicitly requested.

## What Still Needs Care

`k1_prod_im73d` is upload-guard mapped to the main K1 MAC. The correction is
not "flash it anywhere"; the correction is that mic-pin equivalence is not
env/LED-map equivalence.

Expected follow-up for a production-IM73D proof:

- Choose the existing env that matches the intended LED configuration.
- Add/update guard tests for that policy.
- Build the selected proof env.
- Flash only after live USB MAC verification.
- Read-only `:build` proves the selected env and expected git.
- Raw pre-conditioning evidence is sane and non-railed.
- Any silence calibration still requires Captain's explicit silence-go.
- `:stream_agc` after 10 s shows all four gains below 10.
- Captain eyes-on accepts the production response before any default-env flip.

## Optional Main-K1 Swap

Converting the main K1 from SPH0645 to IM73D is optional product-unit validation
or product configuration work for the mic path. It is not the current blocker.

If Captain later chooses to convert the main K1, the old swap checklist can be
reused as a hardware-work checklist only. It must not be treated as the gate
that blocks firmware proof on the bench IM73D unit.
