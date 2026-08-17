---
abstract: "Pin receipt for Main RPL (main K1 replacement): USB B4:3A:45:A5:87:90 on /dev/cu.usbmodem1401, chip-id guess 9087A500. Captain-named 2026-08-18. Dual 160-px WS2816 PCBs on primary DIN-A/B GPIO17/18 and secondary DIN-A/B GPIO15/16; dual IM69D130 PDM DATA=GPIO9 CLK=GPIO8. No firmware env yet — flash FREEZE until a dedicated pinmap ships. I2C on 17/18 is displaced by LED DINs."
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
| Status | OFFSITE (consultancy) | Assembled; **not flashed** |

Do **not** flash Main RPL as F887. Do **not** treat F887 standing auth as covering this serial.

## Authorised physical map (Captain)

| Function | GPIO | Notes |
|---|---|---|
| Primary WS2816 DIN-A | **17** | Dual-data lane A |
| Primary WS2816 DIN-B | **18** | Dual-data lane B |
| Secondary WS2816 DIN-A | **15** | Dual-data lane A |
| Secondary WS2816 DIN-B | **16** | Dual-data lane B |
| LED geometry | 2× 160 px WS2816 PCBs | Primary + secondary channels |
| IM69D130 DATA | **9** | Dual capsule board |
| IM69D130 CLK | **8** | Dual capsule board |

## Conflicts with existing firmware pinmaps

| Existing assignment | Conflict |
|---|---|
| `I2C_SDA_PIN=17` / `I2C_SCL_PIN=18` | **Displaced** — LED DIN-A/B now own 17/18. No encoder I2C on this unit until remapped. |
| `RNG_SEED_PIN=8` | **Collides** with PDM CLK — seed pin must move or be unused under Main RPL pinmap. |
| Prod LEDs `6/7` / bench LEDs `4/5` | **Wrong** for this board — single-wire WS2812B maps do not drive 17/18+15/16. |
| Bench IM69D `CLK=14/DATA=13` / Unit 2 `39/38` | **Wrong** — this board is `CLK=8/DATA=9`. |
| Production `#error` on `K1_MIC_IM69D_PDM_V1` | IM69D on a “main” role needs a **new** pinmap branch, not `k1_hardware` as-is. |

## Firmware status

- Identity registered in `scripts/platformio/k1_device_identities.json` with **`envs: []`**.
- Upload guard will **refuse every K1 env** for this serial until a dedicated env is mapped.
- WS2816 dual-DIN emit (true DIN-A + DIN-B per edge) is **not** a pin remap of `LED_DATA_PIN` / `LED_CLOCK_PIN` alone.

## Flash freeze

**No flash** until:

1. Dedicated pinmap + env (proposed name: `k1_main_rpl_im69d_ws2816` or similar).  
2. Captain `CAPTAIN_FLASH_AUTH` / named token (e.g. `MAIN_RPL_BRINGUP_FLASH`).  
3. Post-flash stamp: `IDENTITY OK: git=<sha> env=<env> epoch=…` on USB `B4:3A:45:A5:87:90`.

## Open (not blocking registration)

- IM69D SELECT strap / which capsule is mono RIGHT — unmeasured (same class of debt as Unit 2 dual-capsule UNPROVEN).  
- Whether encoders return on alternate I2C GPIOs.  
- Lever-2 / `K1_WS2816_LEVER2_V1` vs bring-up WS2812B compatibility path for first light.
