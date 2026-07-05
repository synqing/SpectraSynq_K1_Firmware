---
abstract: "Canonical record for the k1_custom build (2026-07-06): a single WS2812B data channel of 224 LEDs on the bench primary GPIO (GPIO4), secondary channel dropped, bounced off a white wall (fully diffused). Extends k1_bench_im73d_ble → IM73D PDM mic + NimBLE BLE-MIDI (K718 control) + the 224 single-channel LED change. KEY DECISION: keep NATIVE_RESOLUTION=160 and RESAMPLE (Approach 1), NOT rebuild the canvas at 224 (Approach 2) — the wall bounce makes native detail invisible. Flag-gated K1_CUSTOM_LED_V1; existing builds byte-identity PROVEN. NON-SHIPPABLE (radio + bench). 7-SSA investigation."
---

# Custom 224-LED Single-Channel Build — `k1_custom` (2026-07-06)

## What this is

Captain wants a bench K1 driving **one** WS2812B data channel of **224 LEDs** (up from the standard 160 dual-channel) on the **primary GPIO (GPIO4, bench pinmap)**, secondary channel **dropped** — the strip bounces light off a **white wall** (fully diffused, non-LGP). Extends `k1_bench_im73d_ble`, so it carries the **IM73D PDM mic + the NimBLE BLE-MIDI central** (K718 Remoted dial controls the wall live); everything else identical.

## The load-bearing decision — resample, NOT native canvas

There are two ways to get 224 LEDs, and they differ by ~10× in effort/risk:

- **Approach 1 (CHOSEN): resample.** Keep the 160-px render canvas (`NATIVE_RESOLUTION=160`); set the physical count `LED_COUNT_VALUE=224`; the existing `scale_to_strip()` upsamples 160→224 — the *same* path that already drives strip-modes 61/91/160. **~5 flag-gated edits, near-zero risk.**
- **Approach 2 (REJECTED): native 224 canvas.** Rebuild the canvas at 224 — resize ~16 hardcoded `[160]` buffers, decouple `NUM_FREQS=80` from the canvas half, fix ~40 mirror/centre sites across ~20 effects, uint8_t audit, per-effect revalidation.

Captain initially picked native-224 (as an even count), then clarified the output **bounces off a white wall** = maximum diffusion → per-pixel detail is invisible. That makes Approach 2's only benefit (finer internal detail) worthless here, so the decision flipped to **Approach 1**. (5 of 7 SSAs independently recommended Approach 1 on the merits regardless.)

## The 7-SSA injection-point investigation (all consumed per ssa-management)

Evidence files: `scratchpad/custom-led-225/ssa{A..G}-*.md`. Verdicts (orchestrator re-ran the decisive claims):
- **A buffers** — ~16 canvas buffers are literal `[160]`, not `[NATIVE_RESOLUTION]`; changing the canvas overflows them. Resample avoids all of it.
- **B topology** — primary is already a single WS2812B controller; the secondary is a *separate* GPIO7 strip force-enabled at boot (`.ino:670`), with an **unconditional boot-clear that NULL-derefs if secondary init is skipped** (`.ino:693`) — the crash edge.
- **C mapping / D effects** — the mirror/`NUM_FREQS` math breaks only if the canvas moves; resample keeps them on the untouched 160 canvas.
- **E timing/power** — 224 single-channel ≈ 140-148 FPS (fits); the power cap **exists** (`MAX_CURRENT_MA=1500`, content-aware); dropping the secondary *increases* per-LED headroom.
- **F config** — the persisted-count trap is closed (`system.h:424` forces `CONFIG.LED_COUNT=LED_COUNT_VALUE` at boot); the `#define`s are unconditional so a `-D` collides → source `#ifdef` gating required.
- **G build/gate** — env + flag-gated source edits; the upsample OOB is the latent defect; guard tuple mandatory.
- **Orchestrator re-run found a bug the SSAs missed:** `scale_to_strip`/`init_lerp_params` reads `leds_16[index_right]` where the top pixel resolves `index_right == NATIVE_RESOLUTION` (OOB by 1) — *only* on the upsample path (224 > 160). Fixed with a flag-gated clamp.

## The change (all gated on `K1_CUSTOM_LED_V1` → existing builds byte-identical)

| File | Edit |
|------|------|
| `system/config_types.h` | `#ifdef K1_CUSTOM_LED_V1 → #define LED_COUNT_VALUE 224` (else the 61/91/160 block) |
| `SPECTRASYNQ_K1_FIRMWARE.ino` (×2) | `#ifndef K1_CUSTOM_LED_V1` around `init_secondary_leds()`+`ENABLE_SECONDARY_LEDS=true`; and around the secondary boot-clear (the NULL-deref crash guard) |
| `visual/led_utilities.h` | `init_lerp_params` upsample `index_right` clamp (flag-gated, the OOB fix) |
| `platformio.ini` | `[env:k1_custom]` extends `k1_bench_im73d_ble` (IM73D + BLE-MIDI) + `-DK1_CUSTOM_LED_V1` |
| `scripts/platformio/k1_upload_guard.py` | `k1_custom` in the bench tuple (`B489A500`) |
| `tests/test_custom_led_static.py` | **NEW** — 7 static invariants: flag only on `k1_custom`, `224` only under the ifdef, default stays 160, `NATIVE_RESOLUTION` stays 160, guard-registered, secondary flag-guarded |

**Revert** = delete the env block + guard line + the `K1_CUSTOM_LED_V1` guards + the test.

## Evidence

- **Build:** `pio run -e k1_custom` → `[SUCCESS]`. Non-BLE variant RAM 32.8% / Flash 9.9%; BLE variant (final) RAM 38.0% / Flash 13.9% (NimBLE archived).
- **Host gate:** `pytest tests/` → pass; new `test_custom_led_static.py` → 7/7.
- **Byte-identity (PROVEN):** `k1_hardware` with vs stashed-baseline → **identical Flash/RAM (650386 B / 109496 B) and identical ELF sections** (text 468306 / data 182364 / bss 1258401). Production untouched.
- **Flash + eyes-on (non-BLE variant):** guard-verified `B489A500` on the drifted port, full image hash-verified, boots clean (AP streaming, `cal_valid=1`, no crash markers → the secondary-drop guards work), **wall eyes-on PASS (Captain, 2026-07-06): "looks fucking great."**

## Outstanding

1. **BLE variant on-device confirm (pending device replug):** the BLE-enabled `k1_custom` (extends `k1_bench_im73d_ble`) is built + byte-identity-clean but the bench K1 dropped off USB during the flash-race churn. On replug (and after freeing Cursor's serial-monitor port hold): flash `k1_custom` → confirm boots clean + `[ble_remoted] linked=1` (BLE-MIDI up) + the wall. BLE itself is already device-proven via the demo build; this is the composed-build confirmation.
2. **Cursor port contention:** Cursor's PlatformIO extension auto-connects the serial port and its ext-host respawn auto-cleans the build dir when killed — flash reliably needs the serial monitor closed in Cursor first.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-06 | agent:claude-opus-4-8 | Created — `k1_custom` 224-LED single-channel wall build: resample-vs-native decision, 7-SSA investigation, flag-gated edits, byte-identity proof, non-BLE wall eyes-on PASS, BLE variant built + pending device-replug reflash. |
