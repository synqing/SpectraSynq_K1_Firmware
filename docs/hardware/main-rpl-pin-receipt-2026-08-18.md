---
abstract: "Pin receipt for Main RPL (main K1 replacement): USB B4:3A:45:A5:87:90 on /dev/cu.usbmodem1401, chip 9087A500. Dual 160-px WS2816 PCBs — each one continuous strip, DIN-A leds 1–80 / DIN-B leds 81–160 — primary GPIO17/18, secondary GPIO15/16; dual IM69D130 PDM DATA=GPIO9 CLK=GPIO8. On silicon k1_main_rpl_im69d @ 31668e16. I2C on 17/18 is displaced by LED DINs."
---

# Main RPL — Pin Receipt (2026-08-18)

**Device name:** Main RPL (main K1 replacement)  
**USB serial:** `B4:3A:45:A5:87:90`  
**Chip ID (derived from USB serial pattern):** `9087A500` — confirm with `:chip_id` after first bring-up flash  
**Port at registration:** `/dev/cu.usbmodem1401`  
**Date:** 2026-08-18 (AWST)  
**Captain unit name:** `Main RPL`  
**Pin statement:** Captain verbal pin map 2026-08-18 (this receipt)

## Relation to F887

| | Offsite main | Main RPL |
|---|---|---|
| Chip | `F887A500` | `9087A500` (derived) |
| USB serial | `B4:3A:45:A5:87:F8` | `B4:3A:45:A5:87:90` |
| Status | OFFSITE (consultancy) | Flashed `k1_main_rpl_im69d` @ `31668e16` |

Do **not** flash Main RPL as F887. Do **not** treat F887 standing auth as covering this serial.

## Authorised physical map (Captain)

| Function | GPIO | Notes |
|---|---|---|
| Primary DIN-A | **17** | LEDs **1–80** of the primary 160-LED strip |
| Primary DIN-B | **18** | LEDs **81–160** of the same primary strip |
| Secondary DIN-A | **15** | LEDs **1–80** of the secondary 160-LED strip |
| Secondary DIN-B | **16** | LEDs **81–160** of the same secondary strip |
| LED geometry | 2× 160 px WS2816 PCBs | Each PCB = one continuous strip, two data lines |
| IM69D130 DATA | **9** | Dual capsule board |
| IM69D130 CLK | **8** | Dual capsule board |

Firmware: Main RPL fail-closed init — native FastLED **WS2816** (48-bit GRB)
controllers, `addLeds<WS2816>(DIN-A, 0, 80)` + `addLeds<WS2816>(DIN-B, 80, 80)`
per channel (bench-proven split `aa0b57c2`, Captain-ratified 2026-07-16).
Never WS2812B on these pins — 24-bit frames halve the strip.

## Conflicts with existing firmware pinmaps

| Existing assignment | Conflict |
|---|---|
| `I2C_SDA_PIN=17` / `I2C_SCL_PIN=18` | **Displaced** — LED DIN-A/B now own 17/18. No encoder I2C on this unit until remapped. |
| `RNG_SEED_PIN=8` | **Collides** with PDM CLK — seed pin must move or be unused under Main RPL pinmap. |
| Prod LEDs `6/7` / bench LEDs `4/5` | **Wrong** for this board — single-wire WS2812B maps do not drive 17/18+15/16. |
| Bench IM69D `CLK=14/DATA=13` / Unit 2 `39/38` | **Wrong** — this board is `CLK=8/DATA=9`. |
| Production `#error` on `K1_MIC_IM69D_PDM_V1` | IM69D on a “main” role needs a **new** pinmap branch, not `k1_hardware` as-is. |

## Firmware status

- Env **`k1_main_rpl_im69d`** only (`K1_MAIN_RPL_PINMAP_V1`).
- Fail-closed init: native `WS2816` controllers, `addLeds<WS2816>(DIN-A, 0, 80)` +
  `addLeds<WS2816>(DIN-B, 80, 80)` per channel.
- **Scar:** `31668e16` / `5fb237ae` registered `WS2812B` (24-bit) on these pins —
  wrong wire format for WS2816 (48-bit/pixel). Corrected to the bench-proven
  `WS2816` split from `aa0b57c2`.

## Open (not blocking registration)

- IM69D SELECT strap / which capsule is mono RIGHT — unmeasured (same class of debt as Unit 2 dual-capsule UNPROVEN).  
- Whether encoders return on alternate I2C GPIOs.  
- Lever-2 / `K1_WS2816_LEVER2_V1` vs bring-up WS2812B compatibility path for first light.
