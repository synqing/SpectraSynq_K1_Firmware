---
abstract: "AP-1 Lane 3 root-cause analysis: K1 SB init_i2s() in SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h omits ESP32-S3 SPH0645 register tweaks (gated behind #if CONFIG_IDF_TARGET_ESP32S2), uses I2S_CHANNEL_FMT_ONLY_RIGHT instead of RIGHT_LEFT, defaults dma_buf_count=2 (vs firmware-v3's 4), and explicitly drops use_apll/tx_desc_auto_clear/intr_alloc_flags/mclk_multiple/bits_per_chan fields. Hypothesis ranking: H1 missing I2S_RX_MSB_SHIFT/TIMING register tweaks for SPH0645 on S3 is the dominant suspect for garbage samples post-cal (sample frame shifted one bit, sign of DC inverts). Read this before touching i2s_audio.h or before declaring noise_cal mutex bug 'fixed'."
---

# Lane 3 — init_i2s K1 driver-config analysis

**SSA Lane:** AP-1 Root Cause Investigation, Lane 3 of 10
**Scope:** I2S peripheral driver configuration only (driver_install + set_pin + post-pin register tweaks).
**Verdict:** **DEGRADED-MODE** — SB init_i2s() is structurally different from firmware-v3 (known-working on the same bench), and the most critical SPH0645 fix-up registers are gated to `CONFIG_IDF_TARGET_ESP32S2` only.

## Files inspected (SB + firmware-v3)

| Repo | File | Lines | Role |
|------|------|------:|------|
| SB | `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` | 1–37 | `init_i2s()` definition; primary capture init |
| SB | `SPECTRASYNQ_K1_FIRMWARE/constants.h` | 108, 165–186, 16 | `I2S_PORT`, `I2S_*_PIN` K1 block, `DEFAULT_SAMPLE_RATE` |
| SB | `SPECTRASYNQ_K1_FIRMWARE/globals.h` | 27, 73, 80 | `CONFIG.SAMPLE_RATE`, `CONFIG.SAMPLES_PER_CHUNK` defaults |
| SB | `SPECTRASYNQ_K1_FIRMWARE/audio_transfer.h` | 148–190 | `init_i2s_for_data()` — sidecar Goertzel data-link path (separate use) |
| firmware-v3 | `src/audio/AudioCapture.cpp` | 695–748 | Legacy-driver branch (ESP32-S3 K1 path) |
| firmware-v3 | `src/config/audio_config.h` | 41–125, 153–155 | `MicType::SPH0645`, `SAMPLE_RATE`, mic comments |
| firmware-v3 | `src/config/chip_esp32s3.h` | 74–135 | K1 GPIO map (overridable), `i2s::SAMPLE_RATE`, `DMA_BUFFER_COUNT`, `DMA_BUFFER_SAMPLES` |
| firmware-v3 | `platformio.ini` | 181–231 | `esp32dev_audio_esv11_k1v2[_32khz]` env: `K1_I2S_LRCL=11`, `K1_I2S_DOUT=14`, `K1_I2S_BCLK=13` |
| firmware-v3 | `src/audio/backends/esv11/EsV11_32kHz_Shim.h` | 19–20 | `#define SAMPLE_RATE 32000`, `CHUNK_SIZE 128` |

## Pin map confirmation (K1 canonical = 13/11/14)

| Repo | BCLK | LRCLK/WS | DIN/DOUT | Source |
|------|-----:|---------:|---------:|--------|
| K1 hardware definition (doctrine) | 13 | 11 | 14 | docs/hardware/k1-hardware-definition.md (per Captain spec) |
| **SB on K1** | **13** | **11** | **14** | `constants.h:165–170` under `#if defined(SB_K1_HARDWARE)` |
| firmware-v3 K1 build env | 13 | 11 | 14 | `platformio.ini:200–202` `K1_I2S_BCLK=13 K1_I2S_LRCL=11 K1_I2S_DOUT=14` |
| firmware-v3 default chip header | 14 | 12 | 13 | `chip_esp32s3.h:74–89` (only used if env doesn't override — irrelevant for K1) |

**Pin mapping: GROUNDED. SB and firmware-v3 use the same physical pins on K1. Pin assignment is not the bug.**

## SB init_i2s on K1 (i2s_audio.h:7–37)

| Setting | Value | Source line |
|---|---|---|
| `mode` | `I2S_MODE_MASTER \| I2S_MODE_RX` | 8 |
| `sample_rate` | `CONFIG.SAMPLE_RATE` → `DEFAULT_SAMPLE_RATE = 12800` | 9, constants.h:16, globals.h:73 |
| `bits_per_sample` | `I2S_BITS_PER_SAMPLE_32BIT` | 10 |
| `channel_format` | **`I2S_CHANNEL_FMT_ONLY_RIGHT`** | 11 |
| `communication_format` | `I2S_COMM_FORMAT_STAND_I2S` | 12 |
| `intr_alloc_flags` | **(not specified — zero-init = 0)** | (missing) |
| `dma_buf_count` | **2** | 13 |
| `dma_buf_len` | `CONFIG.SAMPLES_PER_CHUNK = 96` | 14, globals.h:80 |
| `use_apll` | **(not specified — zero-init = false)** | (missing) |
| `tx_desc_auto_clear` | **(not specified — zero-init = false)** | (missing) |
| `fixed_mclk` | **(not specified — zero-init = 0)** | (missing) |
| `mclk_multiple` | **(not specified — zero-init = 0 = `I2S_MCLK_MULTIPLE_DEFAULT`)** | (missing) |
| `bits_per_chan` | **(not specified — zero-init = 0 = `I2S_BITS_PER_CHAN_DEFAULT`)** | (missing) |
| `bck_io_num` | `I2S_BCLK_PIN = 13` | 18 |
| `ws_io_num` | `I2S_LRCLK_PIN = 11` | 19 |
| `data_out_num` | `-1` | 20 |
| `data_in_num` | `I2S_DIN_PIN = 14` | 21 |
| `mck_io_num` | **(not specified — zero-init = 0)** | (missing — note: GPIO 0 is the ESP32-S3 boot strapping pin, but `i2s_pin_config_t` zero-init may be re-interpreted as `I2S_PIN_NO_CHANGE` by `i2s_set_pin`; not verified for arduino-esp32 2.0.9) |
| Post-pin register tweak | **GATED behind `#if defined(CONFIG_IDF_TARGET_ESP32S2)`** | 29–32 |
| └ `REG_SET_BIT(I2S_TIMING_REG, BIT(9))` | Only on S2 | 30 |
| └ `REG_SET_BIT(I2S_CONF_REG, I2S_RX_MSB_SHIFT)` | Only on S2 | 31 |

**Order:** `i2s_driver_install` → (S2-only register tweak) → `i2s_set_pin`. NB: the S2 path applies tweaks BEFORE `i2s_set_pin`. firmware-v3 applies them AFTER. The IDF docs are not strict on this for legacy driver, but the difference is recorded.

## firmware-v3 init for same hardware (AudioCapture.cpp:695–748)

| Setting | Value | Source line |
|---|---|---|
| `mode` | `I2S_MODE_MASTER \| I2S_MODE_RX` | 696 |
| `sample_rate` | `SAMPLE_RATE` → 12800 (default) / **32000 (k1v2_32khz shim)** | 697; chip_esp32s3.h:126; EsV11_32kHz_Shim.h:19 |
| `bits_per_sample` | `I2S_BITS_PER_SAMPLE_32BIT` | 698 |
| `channel_format` | **`I2S_CHANNEL_FMT_RIGHT_LEFT`** (both channels in DMA frame; code keeps odd indices for SPH0645 RIGHT) | 699; see also line 270 |
| `communication_format` | **`I2S_COMM_FORMAT_STAND_MSB`** | 700 |
| `intr_alloc_flags` | **`ESP_INTR_FLAG_LEVEL1`** | 701 |
| `dma_buf_count` | **`DMA_BUFFER_COUNT = 4`** | 702, chip_esp32s3.h:130 |
| `dma_buf_len` | `DMA_BUFFER_SAMPLES * 2 = 1024` (samples; both channels) | 703, chip_esp32s3.h:133 |
| `use_apll` | **`false`** (explicit) | 704 |
| `tx_desc_auto_clear` | **`false`** (explicit) | 705 |
| `fixed_mclk` | **`0`** (explicit) | 706 |
| `mclk_multiple` | **`I2S_MCLK_MULTIPLE_256`** (explicit) | 707 |
| `bits_per_chan` | **`I2S_BITS_PER_CHAN_32BIT`** (explicit) | 708 |
| `mck_io_num` | `I2S_PIN_NO_CHANGE` (explicit) | 718 |
| `bck_io_num` | `I2S_BCLK_PIN = 13` | 719 |
| `ws_io_num` | `I2S_LRCL_PIN = 11` | 720 |
| `data_out_num` | `I2S_PIN_NO_CHANGE` | 721 |
| `data_in_num` | `I2S_DOUT_PIN = 14` | 722 |
| Post-pin register tweak (SPH0645 branch, **always runs on S3**) | | 740–747 |
| └ `REG_CLR_BIT(I2S_RX_CONF_REG, I2S_RX_MSB_SHIFT)` | clear MSB_SHIFT (SPH0645 is NOT delayed) | 742 |
| └ `REG_CLR_BIT(I2S_RX_CONF_REG, I2S_RX_WS_IDLE_POL)` | WS idle polarity | 743 |
| └ `REG_SET_BIT(I2S_RX_CONF_REG, I2S_RX_LEFT_ALIGN)` | left-align in 32-bit slot | 744 |
| └ `REG_SET_BIT(I2S_RX_TIMING_REG, BIT(9))` | timing fix-up (bit 9 = RX_SD_IN_DELAY) | 745 |

**Order:** `i2s_driver_install` → `i2s_set_pin` → SPH0645 post-pin register tweaks. Tweaks fire on the legacy driver path for ESP32-S3 unconditionally (no `CONFIG_IDF_TARGET_*` guard).

## Deltas — SB vs firmware-v3 on the same K1 hardware

| # | Field | SB | firmware-v3 | Material? |
|---|---|---|---|---|
| 1 | `channel_format` | `ONLY_RIGHT` | `RIGHT_LEFT` | **YES — DMA frame layout differs.** SB packs only RIGHT into the DMA buffer (one int32 per sample). firmware-v3 packs BOTH and keeps odd indices. Different driver wiring → different MCLK/WS framing internally. SPH0645 datasheet wires its SEL pin to GND/VDD selecting L or R slot; if the SB-side bit is misaligned vs the slot the driver enables, the captured int32 lands in the wrong half of the I2S frame and the sign/magnitude is garbage. **Suspect.** |
| 2 | `communication_format` | `STAND_I2S` | `STAND_MSB` | **YES.** `STAND_I2S` has a 1-bit shift relative to BCLK; `STAND_MSB` aligns MSB with the first BCLK after WS. SPH0645 outputs data with one BCLK delay → which standard you pick determines whether the post-pin `I2S_RX_MSB_SHIFT` fix-up is needed to compensate. SB combines `STAND_I2S` with **missing** MSB_SHIFT correction (gated to S2) → sign-bit may land in the wrong position → garbage / wrong-sign DC subtraction. **Highly suspect.** |
| 3 | Post-pin SPH0645 register tweaks on S3 | **NOT APPLIED** (`#if defined(CONFIG_IDF_TARGET_ESP32S2)` guard at i2s_audio.h:29) | Applied unconditionally in legacy-driver branch | **YES — primary suspect.** The S2 fix-ups `REG_SET_BIT(I2S_TIMING_REG, BIT(9))` + `REG_SET_BIT(I2S_CONF_REG, I2S_RX_MSB_SHIFT)` were the canonical SPH0645 workaround on S2. On S3, the equivalents are `I2S_RX_TIMING_REG` and `I2S_RX_CONF_REG` (note `_RX_` prefix). SB simply doesn't run them on S3, so the SPH0645 frame shift is uncorrected. This matches the "max_raw was a rail-constant 24465 (consistent with wrong-sign DC subtraction)" symptom — bit-shifted samples produce a constant offset that looks like a DC rail. |
| 4 | `intr_alloc_flags` | 0 (unspecified) | `ESP_INTR_FLAG_LEVEL1` | Probably immaterial for correctness; may affect ISR priority and dropped-sample behaviour under load. **Watchlist.** |
| 5 | `dma_buf_count` | 2 | 4 | DMA latency / under-run robustness only. Not a correctness bug at low load. **Watchlist.** |
| 6 | `dma_buf_len` | 96 samples (per `SAMPLES_PER_CHUNK`) | 1024 samples (`512 * 2`) | Different buffering strategy; SB sized to per-chunk i2s_read with `portMAX_DELAY`. Not the bug. |
| 7 | `use_apll`, `tx_desc_auto_clear`, `fixed_mclk`, `mclk_multiple`, `bits_per_chan` | Unspecified (zero-init) | Explicitly set | Zero-init equivalence to firmware-v3 holds for `use_apll=false`, `tx_desc_auto_clear=false`, `fixed_mclk=0`. **But** `mclk_multiple=0` ≠ `I2S_MCLK_MULTIPLE_256` (likely `_DEFAULT` = 256 on most IDF builds, but unverified for arduino-esp32 2.0.9) and `bits_per_chan=0` ≠ `I2S_BITS_PER_CHAN_32BIT` (likely `_DEFAULT` derived from `bits_per_sample`; may differ on S3). **Possible, secondary.** |
| 8 | `sample_rate` value | 12800 | 12800 (default) **or** 32000 (k1v2_32khz shim — Captain's known-working env) | **Possibly material.** The "known-working on this exact bench" reference (per task brief) is `esp32dev_audio_esv11_k1v2_32khz`, i.e. SAMPLE_RATE = 32000. SB at 12800 forces BCLK = 12800 × 64 = 819.2 kHz, which is **below the SPH0645 datasheet minimum of 2.048 MHz BCLK**. See §"SPH0645 datasheet conformance" below. **Highly suspect — independent root-cause candidate alongside #3.** |
| 9 | `mck_io_num` | Not in struct literal (zero-init = 0 = GPIO0) | Explicitly `I2S_PIN_NO_CHANGE` | **Possibly material.** `i2s_pin_config_t` field order matters under C99 designated init; SB's struct literal omits `mck_io_num`. If the arduino-esp32 2.0.9 `i2s_pin_config_t` definition places `mck_io_num` first (the IDF 4.4 layout) the zero-init defaults it to GPIO 0 which is the S3 boot strapping pin. Behaviour depends on whether `i2s_set_pin` treats 0 as NO_CHANGE or as a literal GPIO assignment. **Verify against the exact `i2s.h` shipped with esp32:esp32@2.0.9.** |

## SPH0645 datasheet conformance check

SPH0645LM4H-B I2S MEMS microphone, Knowles datasheet (rev January 2017):

| Requirement | Datasheet value | SB on K1 | firmware-v3 K1 (`_32khz`) | Status |
|---|---|---|---|---|
| BCLK frequency | **2.048 MHz min, 4.096 MHz max** | `SAMPLE_RATE × 64 = 12800 × 64 = 819,200 Hz` ≈ **0.819 MHz** ❌ | `32000 × 64 = 2,048,000 Hz` ≈ **2.048 MHz** ✅ | **SB BELOW MIN** |
| Bits per sample slot | 32-bit I2S slot, 18-bit data, MSB-first | 32-bit slot ✅, but no >>10 shift applied in `init_i2s`; shift applied later in `acquire_sample_chunk` line 66 as `* 0.000512` (≈ /1953 ≈ /2^10.93) | 32-bit slot ✅, `MICROPHONE_TYPE == SPH0645` branch applies bit shift in pipeline | SB shift is approximated, not bit-exact >>10; but this is a math layer, not a driver-init issue |
| Data delay | 1 BCLK cycle after WS edge (i.e. MSB-not-delayed mode requires MSB_SHIFT clear; classic I2S adds an extra 1-cycle delay) | `STAND_I2S` + no MSB tweak on S3 → 2 BCLK delay net → MSB lands in bit-30 instead of bit-31 | `STAND_MSB` + `MSB_SHIFT` cleared → MSB aligns at bit-31 | **SB has frame-misalignment risk on S3** |
| Channel select (SEL pin) | SEL=GND → data on WS=LOW (LEFT slot); SEL=VDD → data on WS=HIGH (RIGHT slot). K1 wiring: per firmware-v3 source comment "SPH0645: RIGHT channel" | `ONLY_RIGHT` → driver only delivers RIGHT slot | `RIGHT_LEFT` → driver delivers both; code reads odd indices = RIGHT | Both arguably correct IF SEL is tied high. If SEL is tied low (LEFT), SB gets zeros forever — matches "max_raw=0 sustained post-cal" symptom. **Verify SEL wiring on K1 schematic.** |
| Power supply settling | First ~50 ms after BCLK start contains startup noise | Not specifically discarded in SB | Not specifically discarded in firmware-v3 either | Not the bug — noise_cal discards first 256 iters anyway |

**At 12.8 kHz on a stock SB build the SPH0645 BCLK is 2.5× too slow.** Below 2.048 MHz the part is out of datasheet spec; output behaviour is unspecified and varies by die lot. Possible failure modes: stuck zeros, stuck rails, garbled bits, or "valid-looking but DC-shifted samples". All three observed symptoms (max_raw=0 post-cal, rail-constant 24465 pre-cal, DC=-32767 sentinel) are consistent with this.

## ESP32-S3 / arduino-esp32 2.0.9 known quirks

| Quirk | Effect on SB on K1 | Confidence |
|---|---|---|
| `I2S_TIMING_REG` macro: on S2 maps to `I2S_TIMING_REG` (combined RX/TX); on S3 split into `I2S_RX_TIMING_REG` and `I2S_TX_TIMING_REG`. SB's `#if defined(CONFIG_IDF_TARGET_ESP32S2)`-gated tweak therefore wouldn't even **compile** correctly on S3 if the guard were removed without re-targeting the register name. | The S2-only guard is hiding the fact that the fix-up was never ported to S3. Removing the guard naïvely → compile error. Captain-level: **a real port is needed, not a guard removal.** | HIGH (cross-referenced firmware-v3 line 745 uses `I2S_RX_TIMING_REG` for the S3 equivalent) |
| arduino-esp32 2.0.9 ships IDF 4.4.7. The legacy `driver/i2s.h` API is deprecated as of IDF 4.4; the new `driver/i2s_std.h` API is recommended on S3. SB uses the legacy API. This is fine — firmware-v3 also uses legacy on S3 in its K1 build (see `chip_esp32s3.h:119 DRIVER_TYPE = "legacy"`) — but check that the i2s_config_t literal in SB matches the legacy struct layout in 2.0.9 specifically (not the IDF 5.x layout). | If struct layout differs, designated initialisers without all members produce silently wrong results. | MEDIUM — needs `~/.platformio/packages/framework-arduinoespressif32@2.0.9/tools/sdk/esp32s3/include/driver/include/driver/i2s.h` cross-check |
| ESP32-S3 has **two** I2S peripherals (I2S0, I2S1). `I2S_PORT = I2S_NUM_0` — correct. | Not a bug. | HIGH |
| ESP32-S3 GPIO 11 strapping note: GPIO 11 is **VDD_SPI** (formerly U0RXD on some pinouts). On WROOM-1U/WROOM-1, GPIO 11 is exposed; on WROOM-2 (octal PSRAM), GPIO 33–37 are reserved. K1 uses N16R8 = ESP32-S3-WROOM-1 (quad PSRAM), so GPIO 11 should be safe. firmware-v3 originally avoided GPIO 11 (see anchor map: observation #36743 "Fixed GPIO 11 Boot Conflict by Moving I2S DIN to GPIO 12") but the current K1 env explicitly uses GPIO 11 for LRCL via `K1_I2S_LRCL=11`. **Pin works at runtime; boot-time hold may matter — out of scope for this lane.** | Watchlist for boot-loop issues, not for sample-data issues. | LOW priority for AP-1 |
| arduino-esp32 2.0.x legacy `i2s_pin_config_t` field order: declared in `tools/sdk/esp32s3/include/driver/include/driver/i2s_types.h` as `{mck_io_num, bck_io_num, ws_io_num, data_out_num, data_in_num}` per IDF 4.4. SB uses **non-designated** order with `mck_io_num` missing — C99 zero-init fills `mck_io_num = 0` = GPIO0. | If `i2s_set_pin` interprets 0 as GPIO0 rather than NO_CHANGE, it would try to configure GPIO0 as MCLK out, which fights the boot strap. This usually fails silently and may explain odd post-cal behaviour. | MEDIUM — needs source verification of `i2s_set_pin` |

## Hypothesis ranking

**H1 (PRIMARY) — BCLK below SPH0645 datasheet minimum.**
At `SAMPLE_RATE = 12800`, BCLK = 819 kHz, which is **40% of the SPH0645's specified minimum 2.048 MHz**. The part is out of spec; output is undefined. firmware-v3's known-working build is at 32 kHz precisely because it brings BCLK back into spec (≈ 2.048 MHz exactly). Symptom fit: explains "max_raw=0 post-cal" (mic outputs static / zeros once it sees out-of-spec clock), "max_raw rail-constant 24465 pre-cal" (mic outputs partial init pattern), and the DC=-32767 sentinel (cal sees no signal). **Highest confidence; cheapest test (bump SAMPLE_RATE to 32000 and retry).**

**H2 (PRIMARY-EQUAL) — SPH0645 register fix-ups gated to S2 only.**
`#if defined(CONFIG_IDF_TARGET_ESP32S2)` at i2s_audio.h:29 means the MSB_SHIFT and TIMING_REG tweaks **never run on K1's ESP32-S3**. Without these, the SPH0645 frame is shifted one bit relative to where the driver reads it. Combined with `STAND_I2S` (which itself adds a 1-cycle shift), the MSB lands in the wrong bit position → wrong-sign and DC-biased samples. Symptom fit: "rail-constant 24465 pre-cal (consistent with wrong-sign DC subtraction)". **High confidence; firmware-v3 line 740–747 is the canonical S3 port.**

H1 and H2 are independent failure modes — both could be true simultaneously, and either alone would produce the observed garbage. Captain bench has firmware-v3 working on the same hardware with both H1 (32 kHz) and H2 (S3 register tweaks applied) addressed.

**H3 (SECONDARY) — `channel_format = ONLY_RIGHT` + ambiguous SEL pin wiring.**
If K1's SPH0645 has SEL tied to GND (LEFT slot), `ONLY_RIGHT` returns zeros forever. firmware-v3 uses `RIGHT_LEFT` and is robust to either wiring. **Needs schematic confirmation.** Symptom fit: "max_raw = 0 sustained".

**H4 (SECONDARY) — `mck_io_num` zero-init lands on GPIO 0.**
If `i2s_set_pin` interprets `mck_io_num = 0` as GPIO 0 rather than NO_CHANGE, MCLK output would conflict with the S3 boot strap pin. Usually silently ignored, but worth verifying the 2.0.9 source. Lower probability than H1/H2.

**H5 (WATCHLIST) — `communication_format = STAND_I2S` without MSB_SHIFT.**
Closely coupled with H2; together they form the canonical "SB on S3 reads SPH0645 wrong" pattern.

**H6 (DOWNSTREAM, NOT IN THIS LANE) — `acquire_sample_chunk` shift formula.**
Line 66: `int32_t sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120;` — this isn't a bit-exact `>> 10` and combines floating-point gain, DC bias add, and bias offset in one expression. If H1/H2 are fixed and noise_cal still misbehaves, look here. **Out of scope for Lane 3.**

## Open questions

1. **What does the K1 SPH0645 module wiring actually do with the SEL pin?** Need schematic (`docs/hardware/k1-hardware-definition.md` or breakboard pic). H3 vs H1/H2 ranking depends on this.
2. **What is the exact `i2s_pin_config_t` field order in arduino-esp32@2.0.9 `tools/sdk/esp32s3/.../driver/i2s_types.h`?** If `mck_io_num` is field 0, SB's struct literal silently puts BCLK in the MCLK slot. (Unlikely — the SB code clearly assigns `.bck_io_num` by designator — but worth verifying that all 2.0.9 headers accept the legacy field order.)
3. **Does `i2s_set_pin` in 2.0.9 treat `mck_io_num = 0` as NO_CHANGE or as GPIO 0?** Source-truth check in `tools/sdk/esp32s3/.../driver/i2s.c` `i2s_check_set_mclk()`.
4. **Has the SB project ever been tested at SAMPLE_RATE=32000 on K1?** The forensic record (observation #54122, "K1v2 SB-S3 Port Compile Results and Pin Map Documented") notes compile-only validation; no runtime evidence at 32 kHz appears in the lane brief.
5. **Was the S2-gated register tweak removed deliberately at any point**, or is it a copy-paste fossil from the original S2 build? Anchor: file timeline at i2s_audio.h shows AP instrumentation 2026-05-20 (observation #53445) and root-cause observation 2026-05-20 (observation #53470) — the gate predates this lane's investigation.

## Recommended Captain-decision-grade summary

Two independent, high-confidence root-cause candidates explain the observed symptoms; neither has been ruled out by Lane 3.

- **H1: SAMPLE_RATE = 12800 puts BCLK below SPH0645's datasheet minimum.** Fix: change `DEFAULT_SAMPLE_RATE` to `32000` (and update `SAMPLES_PER_CHUNK` to keep frame timing sane).
- **H2: SPH0645 frame-alignment register tweaks are gated to ESP32-S2 and never run on K1's S3.** Fix: port the S3 equivalents from firmware-v3 AudioCapture.cpp:740–746 (`I2S_RX_CONF_REG` / `I2S_RX_TIMING_REG`, `MSB_SHIFT` clear, `LEFT_ALIGN` set, timing BIT(9) set).

H3–H5 are secondary and contingent on schematic / 2.0.9 source verification. H6 is downstream and out of Lane 3 scope.

The noise_cal mutex bug (FIRMWARE_VERSION 40102 fix, observation #53470 / 2026-05-21 captain note) is a real bug at the sample-math layer, but it operates on samples that are themselves suspect. Fixing only the cal logic without fixing the driver-init root cause cannot restore correct visual behaviour on K1.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:opus-4.7 (SSA Lane 3) | Created — AP-1 Lane 3 root-cause analysis of K1 init_i2s vs firmware-v3 reference; SB H1 (BCLK below SPH0645 min) and H2 (S3 register tweaks gated to S2) identified as primary suspects |
