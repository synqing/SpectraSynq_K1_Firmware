# R2 Main K1 SPH0645 to IM73D Decision Handoff - 2026-07-06

## Current State

IM73D productionisation firmware is ready to prove on production-shape hardware,
but the main K1 still physically carries an SPH0645.

The production IM73D build path remains guard-blocked:

- Env: `k1_prod_im73d`
- Pin map: production/main K1 GPIO map with IM73D PDM on `clk13/din12/LR14`
- Upload status: blocked in `scripts/platformio/k1_upload_guard.py`
- Reason: flashing this env to the SPH-equipped main K1 would run PDM firmware
  against the wrong physical microphone.

## Decision Required

Choose one:

1. Physically swap the main K1 microphone from SPH0645 to IM73D on pins
   `13/12/14`, matching the bench wiring.
2. Keep the current main K1 on SPH0645 and provide a dedicated production-shape
   IM73D K1 for proving `k1_prod_im73d`.
3. Defer R2. In that case R3-R5 stay blocked and `k1_hardware` remains SPH.

## Recommendation

Swap the main K1 when convenient.

Rationale:

- IM73D is already Captain-ratified as the K1 production mic.
- Bench IM73D uses the same pin map intended for production.
- Firmware can remain waiting at zero cost; SPH flag-off paths remain protected.
- The swap is reversible by hardware rework plus reflash to SPH `k1_hardware`.

## Blast Radius

After the swap, the main K1 becomes an IM73D unit.

Expected follow-up:

- `k1_prod_im73d` moves from blocked envs into the main-K1 allow-list.
- Upload guard tests update with that allow-list change.
- Main K1 is flashed only after MAC verification:
  - main MAC `B4:3A:45:A5:87:F8`
  - chip `F887A500`
- Device proof then checks raw samples, gain state, calibration, AGC, and eyes-on
  behaviour before any default-env flip.

## Accept Criteria After Captain Confirms Swap

1. `pio device list` shows main MAC `B4:3A:45:A5:87:F8`.
2. `k1_prod_im73d` is removed from `BLOCKED_UPLOAD_ENVS` and added only to the
   main K1 target tuple.
3. Static guard tests prove `k1_prod_im73d` cannot flash to bench.
4. `k1_prod_im73d` builds clean.
5. Main K1 flash is guard-verified by MAC/chip.
6. Read-only `:build` proves `env=k1_prod_im73d` and the expected git.
7. Raw pre-conditioning evidence is sane and non-railed.
8. Captain explicitly authorises any silence calibration window; no automatic
   `start_noise_cal`, `N`, or `Y`.
9. `:stream_agc` after 10 s shows all four gains below 10.
10. Captain eyes-on A/B accepts the production response.

## Reject Criteria

Reject or stop the R3 proof if any of these happen:

- Main MAC does not match `B4:3A:45:A5:87:F8`.
- `k1_prod_im73d` attempts to target bench or any unknown device.
- Raw samples are zero, stuck, or near rail.
- `input_trim` reduces under the test condition.
- `clip_pct` or `near_pct` is nonzero.
- The device needs calibration but Captain has not explicitly given a silence-go.
- Eyes-on reports washed colour, clipped dynamics, noise-floor flicker, or
  worse response than SPH.

## Default If No Action

R2-R5 remain blocked. The main K1 stays SPH on `k1_hardware`. The bench remains
available for IM73D radio-free measurement and BLE-demo reflashes when explicitly
requested.
