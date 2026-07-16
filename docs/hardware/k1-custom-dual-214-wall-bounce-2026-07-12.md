---
abstract: "Canonical record for env:k1_custom. SUPERSEDED 2026-07-12: the 2026-07-06 single-channel 224-LED wall test bed was overwritten by a dual-channel 214-LED/channel wall-bounce build (bare WS2812B 5V, no LGP, 2.5 A total, extends k1_bench_im73d_ble). This file retains provenance for the original decision + the overwrite. See body."
---

# Custom dual-214 wall-bounce build — `k1_custom` (overwrite 2026-07-12)

## Current definition (authoritative)

| | |
|---|---|
| **Env** | `[env:k1_custom]` extends `k1_bench_im73d_ble` |
| **Flag** | `-DK1_CUSTOM_LED_V1` |
| **LEDs** | **214 + 214** WS2812B 5V (primary GPIO4, secondary GPIO5) |
| **Optics** | Bare bulbs, **no LGP** — viewer sees white-wall bounce |
| **Canvas** | `NATIVE_RESOLUTION` stays **160**; upsample 160→214 both channels |
| **Power** | `CONFIG.MAX_CURRENT_MA = 2500` (2.5 A total @ 5 V), forced at boot |
| **Target** | Bench K1 `B489A500` only — NON-SHIPPABLE |
| **Control** | IM73D PDM mic + NimBLE BLE-MIDI (K718 Remoted) |

Captain manually counted both strips = **214 each** (2026-07-12). The prior single-channel 224 test bed is retired in place (same env name / same flag).

## Architecture decision — resample, NOT native-214 canvas

Same load-bearing choice as the 2026-07-06 investigation, re-validated for dual-214 + wall wash:

- **Approach 1 (CHOSEN): resample.** Keep `NATIVE_RESOLUTION=160`; set `LED_COUNT_VALUE=214` + `SECONDARY_LED_COUNT=214`; existing `scale_to_strip()` / `scale_to_secondary_strip()` upsample. Near-zero risk; production envs stay byte-identical when the flag is off.
- **Approach 2 (REJECTED): native-214 canvas.** Rebuild ~16 hardcoded `[160]` buffers, decouple `NUM_FREQS=80` from canvas half, fix ~40 mirror/centre sites across ~20 effects, uint8_t audits, per-effect revalidation — **and the wall bounce still erases the only benefit** (finer internal detail).

Wall wash + bare dies: the viewer never resolves per-LED structure; spending the native-canvas rewrite buys nothing perceptible and risks the effect corpus.

### Why dual-channel changes nothing about the canvas decision

Production already renders two independent 160-px canvases and resamples onto physical counts. Dual-214 is the same composition model with a longer physical strip. Secondary upsample reuses `lerp_led_16` — which needed the same OOB clamp the primary lerp-params path already had under this flag.

## Change surface (all gated on `K1_CUSTOM_LED_V1`)

| File | Edit |
|------|------|
| `system/config_types.h` | `LED_COUNT_VALUE 214` |
| `system/globals.h` | `SECONDARY_LED_COUNT = 214` |
| `system/globals_config.cpp` | `MAX_CURRENT_MA` default `2500` |
| `system/system.h` | Boot-force `CONFIG.MAX_CURRENT_MA = 2500` |
| `SPECTRASYNQ_K1_FIRMWARE.ino` | Dual-channel restored (retired `#ifndef` secondary drop) |
| `visual/led_utilities.h` | Primary lerp-params upsample clamp; `lerp_led_16` secondary upsample clamp |
| `platformio.ini` | `[env:k1_custom]` comment rewrite |
| `tests/test_custom_led_static.py` | Dual-214 / 2.5 A / dual-channel invariants |

**Revert** = delete the env block + guard-manifest line + all `K1_CUSTOM_LED_V1` guards + the test.

## Power note (2.5 A @ 428 LEDs)

Theoretical full-white WS2812 draw far exceeds 2.5 A. FastLED `setMaxPowerInVoltsAndMilliamps(5.0, 2500)` is mandatory — expect aggressive content-aware dimming. That is correct for a wall wash: average current per LED ≈ 5.8 mA at the hard ceiling.

## Historical (2026-07-06 single-channel 224 test bed)

Originally: one WS2812B channel of 224 LEDs on GPIO4, secondary dropped, wall bounce, resample 160→224, extends `k1_bench_im73d_ble`. Eyes-on PASS ("looks fucking great"). Captain later directed overwrite to dual-214 (this document's current section). The 7-SSA investigation that justified Approach 1 still applies; only the physical topology changed (1×224 → 2×214, secondary kept).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-12 | agent:cursor-grok | Overwrite: dual-214 wall-bounce (bare WS2812B 5V, 2.5 A, keep secondary); retire single-channel 224 test bed in place; reaffirm NATIVE_RESOLUTION=160 resample. |
| 2026-07-06 | agent:claude-opus-4-8 | Created — `k1_custom` 224-LED single-channel wall build (now historical). |
