---
abstract: "Pin receipt for Main RPL (main K1 replacement): USB B4:3A:45:A5:87:90 on /dev/cu.usbmodem1401, CHIP ID 9087A500 locked live. Dual 160-px WS2816 PCBs — each one continuous strip, DIN-A leds 1–80 / DIN-B leds 81–160 — primary GPIO15/16, secondary GPIO17/18; dual IM69D130 PDM DATA=GPIO8 CLK=GPIO9 SLOT_RIGHT. MAIN_RPL_FIRST_LIGHT_PASS. CAL measured SSL=173 DC=-265. Encoders stay dead; I2C 17/18 displaced."
---

# Main RPL — Pin Receipt (2026-08-18)

**Device name:** Main RPL (main K1 replacement)  
**USB serial:** `B4:3A:45:A5:87:90`  
**Chip ID (locked live 2026-08-18):** `9087A500` — `:chip_id` / `:dump` on `/dev/cu.usbmodem1401` printed `CHIP ID: 9087A500`  
**Port at registration:** `/dev/cu.usbmodem1401`  
**Date:** 2026-08-18 (AWST)  
**Captain unit name:** `Main RPL`  
**Pin statement:** Captain verbal pin map 2026-08-18 (this receipt)

## Relation to F887

| | Offsite main | Main RPL |
|---|---|---|
| Chip | `F887A500` | `9087A500` (live `:dump` lock) |
| USB serial | `B4:3A:45:A5:87:F8` | `B4:3A:45:A5:87:90` |
| Status | OFFSITE (consultancy) | Flashed `k1_main_rpl_im69d` @ `cd18d89c`; **`MAIN_RPL_FIRST_LIGHT_PASS`** |

Do **not** flash Main RPL as F887. Do **not** treat F887 standing auth as covering this serial.

## Authorised physical map (Captain)

| Function | GPIO | Notes |
|---|---|---|
| Primary DIN-A | **15** | LEDs **1–80** of the primary 160-LED strip |
| Primary DIN-B | **16** | LEDs **81–160** of the same primary strip |
| Secondary DIN-A | **17** | LEDs **1–80** of the secondary 160-LED strip |
| Secondary DIN-B | **18** | LEDs **81–160** of the same secondary strip |
| LED geometry | 2× 160 px WS2816 PCBs | Each PCB = one continuous strip, two data lines |
| IM69D130 DATA | **8** | Dual capsule board |
| IM69D130 CLK | **9** | Dual capsule board |

Firmware: Main RPL fail-closed init — native FastLED **WS2816** (48-bit GRB)
controllers, `addLeds<WS2816>(DIN-A, 0, 80)` + `addLeds<WS2816>(DIN-B, 80, 80)`
per channel (bench-proven split `aa0b57c2`, Captain-ratified 2026-07-16).
Never WS2812B on these pins — 24-bit frames halve the strip.

## Conflicts with existing firmware pinmaps

| Existing assignment | Conflict |
|---|---|
| `I2C_SDA_PIN=17` / `I2C_SCL_PIN=18` | **Displaced** — secondary LED DIN-A/B now own 17/18. No encoder I2C on this unit until remapped. |
| `RNG_SEED_PIN=8` | **Collides** with PDM DATA — seed is already remapped to GPIO10 under this pinmap. |
| Prod LEDs `6/7` / bench LEDs `4/5` | **Wrong** for this board — single-wire WS2812B maps do not drive 15/16+17/18. |
| Bench IM69D `CLK=14/DATA=13` / Unit 2 `39/38` | **Wrong** — this board is `DATA=8/CLK=9`. |
| Production `#error` on `K1_MIC_IM69D_PDM_V1` | IM69D on a “main” role needs a **new** pinmap branch, not `k1_hardware` as-is. |

## Firmware status

- Env **`k1_main_rpl_im69d`** only (`K1_MAIN_RPL_PINMAP_V1`).
- Fail-closed init: native `WS2816` controllers, `addLeds<WS2816>(DIN-A, 0, 80)` +
  `addLeds<WS2816>(DIN-B, 80, 80)` per channel (`aa0b57c2` shape).
- Live identity 2026-08-18: `BUILD: version=40103 git=cd18d89c epoch=1787028551 env=k1_main_rpl_im69d`.
- **`CHIP ID: 9087A500`** locked from live `:dump` (not a USB-serial guess).
- **`MAIN_RPL_FIRST_LIGHT_PASS`** — Captain item 1: primary and secondary channels work.
- **CAL_SOURCE measured**, SSL=173, DC=−265, `cal_valid=1`, `NOISE_CAL_REASON: none`
  (Captain item 2 — accepted; do **not** re-fire `start_noise_cal`).
- Encoders stay dead. I2C 17/18 remains displaced by secondary LED DIN-A/B
  (Captain item 6 — do not remap).
- **Scar:** `31668e16` / `5fb237ae` registered `WS2812B` (24-bit) on these pins —
  wrong wire format for WS2816 (48-bit/pixel). Corrected at `02cc2f54` to the
  bench-proven `WS2816` split. Pair swap `cd18d89c` is the first-light binary.

## Open (not blocking first light)

- Lever-2 / `K1_WS2816_LEVER2_V1` 16-bit emit annex onto this branch (Captain item 7).

## SELECT / capsule close (2026-08-18)

**Stamp:** `MAIN_RPL_SELECT_CLOSED_AS` — SEL unused, `SLOT_RIGHT`, single PDM pair 8/9.

Firmware treats the live mono path as **ESP-IDF PDM RIGHT**
(`-DK1_MIC_IM69D_SLOT_RIGHT` → `I2S_PDM_SLOT_RIGHT`). `K1_IM69_PDM_SEL_PIN` is
GPIO12 and is **unused-by-design** — never driven (hard-strap assumed; same rule
as PCB3 / Unit 2). The second capsule is **not electrically proven** on this
unit. Receipt:
[`main-rpl-im69d-select-close-2026-08-18.md`](./main-rpl-im69d-select-close-2026-08-18.md).
