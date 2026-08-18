---
abstract: "Main RPL IM69D SELECT / RIGHT-capsule close. Firmware treats the live mono path as ESP-IDF PDM RIGHT. GPIO12 SEL is unused-by-design and is never driven. Dual-capsule electrical identity is CLOSED-AS (single PDM pair DATA=8 CLK=9), not proven as two live capsules."
---

# Main RPL — IM69D SELECT close (2026-08-18)

**Stamp:** `MAIN_RPL_SELECT_CLOSED_AS`  
**Device:** Main RPL USB `B4:3A:45:A5:87:90` `/dev/cu.usbmodem1401`  
**Chip (live `:dump`):** `CHIP ID: 9087A500`  
**Env:** `k1_main_rpl_im69d` @ `cd18d89c` (epoch `1787028551`)

## Verdict

| Question | Close |
|---|---|
| Which capsule does firmware treat as RIGHT? | **ESP-IDF PDM RIGHT.** Env flag `-DK1_MIC_IM69D_SLOT_RIGHT` sets `pdm_cfg.slot_cfg.slot_mask = I2S_PDM_SLOT_RIGHT` in `i2s_audio.h`. Init prints `I2S PDM RX INIT: … slot=RIGHT`. |
| Is SEL GPIO12 driven? | **No. Unused-by-design.** `K1_IM69_PDM_SEL_PIN` is 12. Grep of the IM69 init branch: no `gpio_set_level`, no `K1_PDM_LR_PIN`, no write of `K1_IM69_PDM_SEL_PIN`. Same rule as PCB3 and Unit 2. |
| Hardware strap? | **Assumed hard-strapped** (Captain: SEL not driven). Do not invent a host SELECT GPIO. |
| Second capsule electrically proven? | **No.** Complementary SELECT states, shared-DATA contention, and per-capsule VDD/clock were not measured on this unit. |
| Docs / firmware debt? | **CLOSED-AS:** SEL unused, `SLOT_RIGHT`, single PDM pair **DATA=GPIO8 / CLK=GPIO9**. Do not leave the pin receipt Open forever. |

On B489 G1, ESP-IDF RIGHT maps to physical IM1 / board-left / SELECT HIGH. That
mapping is **not transferred** to Main RPL silk or capsule position. Main RPL
closes the *software path* and the *do-not-drive-SEL* rule only.

## Evidence

1. **Source.** `platformio.ini` `[env:k1_main_rpl_im69d]` carries
   `-DK1_MIC_IM69D_SLOT_RIGHT`. `constants.h` `K1_MAIN_RPL_PINMAP_V1` defines
   `K1_PDM_DIN_PIN 8`, `K1_PDM_CLK_PIN 9`, `K1_IM69_PDM_SEL_PIN 12` with
   `unused on Main RPL; do not drive as LR`.
2. **Host lock.** `tests/test_main_rpl_env_static.py::test_main_rpl_im69d_slot_right_sel_unused`.
3. **Live identity (this session, pre-reset `:dump`).**
   `BUILD: version=40103 git=cd18d89c epoch=1787028551 env=k1_main_rpl_im69d`  
   `CHIP ID: 9087A500` · `CAL_SOURCE: measured` · SSL=173 · DC=−265.
   That env *is* the RIGHT-slot binary. AP stream was alive (`raw_i16_*` non-zero).
4. **esptool MAC (ROM, this session):** `b4:3a:45:a5:87:90` — matches USB serial.
   `--after hard_reset` recovered the app. Post-reset `:dump` still
   `git=cd18d89c env=k1_main_rpl_im69d`, SSL=173, DC=−265,
   `CAL_SOURCE: persisted_profile` (NVS reload of the accepted measured cal).
   Boot `I2S PDM RX INIT … slot=RIGHT` was **not captured** — serial reopened
   after init. Slot is compile-time locked by the env that `:build` reported.
5. **Not done (and not required to close this debt):** driving GPIO12;
   complementary SELECT measurement; naming which physical capsule is IM1.

## Do not

- Drive SELECT / GPIO12.
- Re-fire `start_noise_cal` (accepted SSL=173 DC=−265).
- Treat this stamp as B489 G1 physical-IM1 proof on Main RPL silk.
- Leave pin-receipt Open as “SELECT unmeasured forever”.
