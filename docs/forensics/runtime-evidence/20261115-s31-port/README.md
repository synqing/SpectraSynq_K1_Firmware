---
abstract: "S31 port phase 1 (15 Nov 2026). The K1 FE firmware builds for the ESP32-S31 (Waveshare ESP32-S31-Zero, the Captain's official target) on plain ESP-IDF v6.1.1, boots in esp-emu --chip esp32s31, and gives bit-identical light frames to the S3 build in 27 of 28 maintained replay cases; the 28th differs only through its boot-time clock and is identical with the clock fixed. S3 binaries unchanged. Pins come from the ordered carrier K1-FE-S31-Gx2_black-gold-v6, which does not wire line-in data, I2C, CC sense, two buttons or the heartbeat to the S31. Simulated, not hardware; nothing was flashed."
---

# K1 FE on the ESP32-S31: port phase 1

Lane `lane/k1-s31-port` (worktree `/Users/spectrasynq/SpectraSynq_K1_Firmware-s31`), off `fcdefec5`. Port commit `7a36f8c7`.
Every simulator number here is **simulated, not hardware**. No S31 exists on the bench; nothing was flashed.

## Gates

| Gate | What was run | Result |
|---|---|---|
| G1 S3 unchanged | `scripts/regression-harness/mic_stable_byte_gate.sh k1_fe k1_main_rpl_im69d` in the worktree against fingerprints recorded there at `fcdefec5` before any edit (`runs/g1-head.reference`) | exit 0: both byte-identical (`runs/g1.json`). A first run on the uncommitted tree was exit 1 for `k1_fe` only: its release tag read `untagged-dirty` instead of `untagged`. Committed (provenance held constant): exit 0. |
| G2 S31 starts | S31 `k1_fe_emu` image through `tools/esp_emulator/run.py`, `esp-emu 0.49.0 --chip esp32s31` | boots, prints `EMU_BUILD ... env=k1_fe_emu@esp32s31 chip=esp32s31 idf=v6.1.1` (`runs/g2-build-line.txt`); 28/28 cases accepted by the unchanged `emu_capture.accept` |
| G3 same lights | `tools/esp_emulator/cross_chip_compare.py`: `emu_capture.deterministic_view` equality per case (both edges + frame metadata), no tolerance | exit 1: 27 MATCH, 1 DIFFER (`startup-sqr`), 0 not compared (`runs/cross-chip-s3head-vs-s31.json`) |

`startup-sqr` is the only case on the `boot_monotonic` epoch: its clock starts at the emulated boot time, 346,007 µs on the S3 image and 546,004 µs on the S31 image. The difference is on edge A only (114 of 1,067 frames, largest channel difference 9,666 of 65,535); `stress_repeat.localise` puts the first divergence on the render side (`LED_FPS`, frame 1), with identical audio meaning. Paired control (`tools/startup_epoch_control.py`): the same case with the clock declared at 1.0 s, as every other music case, is **identical** on both chips (1,067 frames; `runs/startup-sqr-fixed-clock-control.json`). So the first stage that differs is the render clock input, set by emulated boot duration; audio levels, tempo, render and pack do not diverge.

The S31 suite's own matrix shows SW07 FAIL. That was the suite's host pytest step: two repository tests failed on the port's first draft (`test_im69_idf_freeze_stays_on_s3_only`, and the `constants.h` reference hash in `k1_lightshow_acceptance.json`). Both were fixed before `7a36f8c7`; the product-build part of SW07 passed (no emulator flag or symbol in the S31 product image; emulator env upload-blocked). SW11 is proven only by a clean-export run.

### Independent re-run from clean exports (lane E, fresh agent that did not write the port)

`git archive` exports, no `.git` (`runs/laneE-driver.sh`):

| Gate | Result |
|---|---|
| G1 | exports of `fcdefec5` then `7a36f8c7` built at the same path: exit 0, `k1_fe` and `k1_main_rpl_im69d` byte-identical (`runs/laneE-g1.json`) |
| G2 | S31 suite from the export of `7a36f8c7`: **SOFTWARE COMPLETE**, every SW criterion PASS including SW07 and SW11 (clean export); `EMU_BUILD git=unknown env=k1_fe_emu@esp32s31 tag=untagged chip=esp32s31 idf=v6.1.1` (`runs/laneE-out-s31-result-summary.json`) |
| G3 | S3 suite from the same commit's export (SOFTWARE COMPLETE) against the S31 suite: exit 1, 27 MATCH, 1 DIFFER (`startup-sqr`, edge A 114 frames, max 9,666; edge B none; first divergence render, `LED_FPS`), 0 not compared (`runs/laneE-cross-chip-export-s3-vs-s31.json`) |

The worktree results above and the clean-export results agree exactly.

## How the port is built

- `targets/esp32s31/`: an ESP-IDF v6.1.1 project (`idf.py --preview`, target `esp32s31`). `tools/k1_pio_profile.py` reads `platformio.ini` at configure time: the same `build_src_filter` (77 sources, identical to PlatformIO's object list), the same `build_flags` (56 for `k1_fe`, 63 for `k1_fe_emu`), the same include folders and provenance defines. The only addition is `-DK1_PLATFORM_S31`. `tools/k1_ino_to_cpp.py` converts the sketch as PlatformIO does. `build.sh <env>` builds and stages outputs under the names the emulator runner uses.
- Arduino: `espressif/arduino-esp32 4.0.0-rc1` from the component registry (it lists the S31; it needs IDF >= 5.3, < 6.2). FastLED 3.10.3 from git, with its two missing IDF 6.1 declarations supplied by a forced include (`compat/fastled_idf61_compat.h`). `dependencies.lock` pins every component.
- Compile settings checked in `compile_commands.json`: `-O3 -ffast-math -fno-finite-math-only` reach the K1 sources, FastLED and the Arduino core (as PlatformIO), last `-O` wins. Newlib (IDF 6.1 defaults to picolibc; the S3 uses newlib). `-Werror=all`, which IDF 6.1 keeps even with `CONFIG_COMPILER_DISABLE_DEFAULT_ERRORS`, is removed so warnings do not stop the build, as under PlatformIO.
- Platform switch (`system/k1_platform.h`): every S31 source change sits behind `K1_PLATFORM_S31`, except one emulator-fixture line (`EMU_BUILD`, emulator builds only).
- Arduino-as-component worked first time at the API level; no compatibility layer was written. No ESP-IDF driver needed a stub.

## Pins (ordered carrier)

Board file `~/Downloads/K1-FE-S31-Gx2_black-gold-v6.epro2` (sha256 `5769d794…1e452`), the newest Gx2 file (14 Nov 22:42, Gerbers 23:00; RECEIPT-BUILD-G5 session 7). No fab-order receipt names the file: INFERENCE. Socket `J_S31` pad nets were read from the board document (`tools/epru_pad_nets.py`, `board/gx2-pad-nets.json`); the Zero's J2 contact to GPIO table from the Waveshare schematic (`board/zero-j2-schematic-crop.png`). Per-pin verdicts with sources: `pin-check.json`. Firmware: `SPECTRASYNQ_K1_FIRMWARE/system/k1_fe_board_s31_zero.h`.

- Fine: LED0-3 on GPIO22/23/25/24, MIC_CLK GPIO20, MIC_DATA GPIO16 (I2S0, the only PDM-to-PCM port), POWER_PERMIT 11, VBUS_PG 17, JACK_DET 12, ADC_SHDNZ 35, NAV 8/13/15, SW_USER3 14, USB 33/34.
- Firmware setting (done): LED_N_OE GPIO21 and LED_S_OE GPIO54 are pulled DOWN on Gx2 (R_PWR27/R_PWR33), so the firmware drives them high; GPIO54 is the MTDO pad, used as GPIO.
- Cannot work, needs a wire fix: PCM_LRCK and PCM_DOUT (line-in), I2C_SDA/SCL, CC1/CC2_SENSE, SW_USER1/2, ADC_DOUT (parked ADC), HEARTBEAT (no net). Checked twice: no pad binding and no copper end point on any J_S31 pad (`board/gx2-copper-vs-socket.txt`). Free contacts for wires are listed in `pin-check.json`.
- **Consequence of the missing CC sense: the LEDs stay dark.** With CC1 = CC2 = 0 mV, `k1_fe_gx_classify_cc` returns Invalid and `k1_fe_gx_source_led_ma` allows 0 mA (`system/k1_fe_gx_power_policy.h`); the Gx limiter then scales both edges to zero. Seen in the S31 product image's emulator boot: `[FEPWR] ... cc1_mv=0 cc2_mv=0 source=unqualified permit=0 led_budget_est_ma=0`. The power rule was not changed (a product safety rule); CC1/CC2 wires to free ADC pins (GPIO42-45) fix it.
- INFERENCE for the board lane: the LED_N_OE/LED_S_OE pull-downs (pull-ups on the S3 Gx board) may be deliberate. The S31 firmware drives them high at board start to keep S3 behaviour.

## S31 product image (no emulator hooks)

The staged S31 `k1_fe` image booted in `esp-emu --chip esp32s31 --console usb-jtag` for 60 s (`runs/s31-product-k1_fe-emu-boot-usb.txt`, simulated): serial, LittleFS (formatted on first boot), LEDs, I2S0 PDM RX (slot RIGHT) and I2S enable PASS; PCM1808 clock gate FAIL (pins unwired), line-in reported UNAVAILABLE and the source stays on the microphone (the emulator's jack pin reads "in"); `[FEBOARD] profile=Gx i2c=FAIL sda=-1 scl=-1`; the audio loop then runs (silent input). No panic. The image links FastLED's RMT5 controller (`fl::RmtController5`, `rmt_new_tx_channel`, `rmt_transmit`), `i2s_channel_init_pdm_rx_mode` and `pcnt_new_unit` (riscv32-esp-elf-nm).

## Not proven (needs a real S31-Zero)

Boot on silicon; IM69D PDM on I2S0 (slot order, level); the four WS2816 lines on the S31's four RMT TX channels (and RMT DMA); USB Serial/JTAG; LittleFS on real flash; PSRAM variant (N16R16 assumed); timing and core load; GPIO20-25 pad level; DIN-A/DIN-B order inside each LED edge (no LED bar board exists). The RMT waveform check was not done: `--rmt-loopback` needs an RX channel the K1 does not use.

## Re-run

```bash
cd <repo>
bash targets/esp32s31/build.sh k1_fe          # product image (build only)
export K1_ESP_EMU=<pinned esp-emu 0.49.0>
python3 tools/esp_emulator/run.py --scenario tools/esp_emulator/s31_music_regression.json --profile fe --output _scratch/esp-emulator/<s31>
python3 tools/esp_emulator/run.py --scenario tools/esp_emulator/s3_music_regression.json  --profile fe --output _scratch/esp-emulator/<s3>
python3 tools/esp_emulator/cross_chip_compare.py --base _scratch/esp-emulator/<s3> --other _scratch/esp-emulator/<s31> --output <s31>/cross-chip.json
python3 docs/forensics/runtime-evidence/20261115-s31-port/tools/startup_epoch_control.py --output <fresh>
```

Toolchain: ESP-IDF v6.1.1 shallow clone at `~/esp/esp-idf-v6.1`, commit `051e4c4eb20346e043cdd47bc388fde75ff8af63`, tools installed for esp32s31 only (Python 3.13 environment; Homebrew 3.14 cannot build it). v5.5.2 and PlatformIO untouched.

| Date | Author | Change |
|---|---|---|
| 2026-11-15 | agent:claude (S31 port lane) | Created. |
