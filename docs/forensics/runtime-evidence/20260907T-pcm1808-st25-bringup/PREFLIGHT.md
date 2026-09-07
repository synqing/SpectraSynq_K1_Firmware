---
abstract: "2026-09-07 Main RPL PCM1808+ST25 preflight: live silicon 9087A500 / acaecaa8 / k1_main_rpl_im69d on usbmodem1101; I2S0=PDM mic 8/9; I2S1 free; candidate PCM 13/14/10 ACCEPT; candidate NFC 7/6/5/4/2 ACCEPT on this env only. No PCM firmware until default 96 kHz clocks are measured."
---

# PREFLIGHT — PCM1808 + ST25R3916B on Main RPL

**Gate:** hardware facts before firmware.  
**PCM firmware:** **NOT WRITTEN.** Waiting on default 96 kHz module measurement.

## 1. Repository provenance

| Item | Value |
|---|---|
| cwd / toplevel | `/Users/spectrasynq/SpectraSynq_K1_Firmware` |
| Lane branch | `lane/pcm1808-st25r3916b-bringup` (created this session from `lane/colourlab-bench`) |
| HEAD | `a3e1467c82ee5f45223f0f374c5e9197ea3a8635` |
| HEAD subject | `docs(handover): B5 — differential input loop is reversed; mag_i32 semantics a...` |
| Dirty (unrelated) | Colour Lab screenshots + BLE-iPhone probe (`K1_BLE_MIDI_PERIPHERAL`, gated). **Not stashed. Not this lane.** |
| Dirty firmware TUs | `.ino` / `serial_cmd_table.def` / `serial_menu.h` / `platformio.ini` — all `#ifdef K1_BLE_MIDI_PERIPHERAL` or a new `k1_ble_iphone_probe` env. Main RPL does **not** define that flag. |
| Sibling worktree | none created. Existing `.worktrees/effect-response-atlas` was not used as a write target. |
| AGENTS.md | repo root `./AGENTS.md` (libdeps copies ignored) |

`scripts/agent/repo-truth.sh` was **FAIL** on arrival because Colour Lab authority status was `ready_for_merge`. This lane's authority file is `docs/handover/HANDOVER_2026-09-07_PCM1808_ST25R3916B_BRINGUP.md` with `status: active`.

## 2. Live target identity

Discovered this session. **Not** taken from a stale port table.

| Item | Live value | Evidence |
|---|---|---|
| Port | `/dev/cu.usbmodem1101` | `serial.tools.list_ports` |
| USB | VID:PID `303A:1001`, serial `B4:3A:45:A5:87:90`, product `USB JTAG/serial debug unit` | same |
| Chip ID | `9087A500` | live `:dump` |
| Build | `version=40103 git=acaecaa8 epoch=1788173468 env=k1_main_rpl_im69d` | identity guard + `:build` |
| Identity guard | `IDENTITY OK` vs `--expect-git acaecaa8 --expect-env k1_main_rpl_im69d` | `k1_device_identity_guard.py` |

Registry row (2026-08-28) named the same git/env with epoch `1787773671` and factory SHA `4bd481f8…`. **Live epoch is `1788173468`.** Same commit, later rebuild/flash. Do not treat the August factory SHA as the bytes on this chip until a matching bin is found.

Raw capture: [`live-dump-preflight.txt`](./live-dump-preflight.txt)

## 3. Exact Main RPL environment (live `platformio.ini`)

| Item | Value | Evidence |
|---|---|---|
| Env | `k1_main_rpl_im69d` | `platformio.ini:291` |
| Extends | `k1_hardware` | `:292` |
| Board | `esp32-s3-devkitc1-n16r8` | `:21` |
| Platform | pioarduino `54.03.20` = Arduino 3.2.0 / ESP-IDF 5.4.1 | `:19-22` |
| PSRAM | OPI, `qio_opi`, `-DBOARD_HAS_PSRAM` | `:25-26`, `:67` |
| Flash | 16 MB QIO | `:27-30` |
| Audio source | microphone (defaults in `k1_audio_source.h`: MIC=1, USB=0) | `audio/k1_audio_source.h:7-18` |
| Mic flag | `-DK1_MIC_IM69D_PDM_V1` `-DK1_MIC_IM69D_DSR_16S_V1` `-DK1_MIC_IM69D_SLOT_RIGHT` | `platformio.ini:301-303` |
| Pinmap flag | `-DK1_MAIN_RPL_PINMAP_V1=1` | `:300` |
| I2S controller (mic) | `I2S_NUM_0` (`I2S_PORT`) PDM RX **master** | `constants.h:287`, `i2s_audio.h:294,325-360` |
| PDM GPIO | DATA=8 CLK=9; GPIO12 unused-by-design SEL | `constants.h:454-457` |
| LED GPIO | primary DIN-A/B **15/16**, secondary **17/18** | `constants.h:449-452` |
| LED driver | FastLED RMT + Lever-2; **not** LCD_CAM | default env; `K1_LED_I2S_DIRECT_V1` only on parked `k1_main_rpl_i2sled_probe` |
| USB | `-DARDUINO_USB_MODE=1` `-DARDUINO_USB_CDC_ON_BOOT=1`; GPIO19/20 live Serial-JTAG | `platformio.ini:64-65` + port probe |
| BLE / WiFi | **off** on this env. Do not add radio to make the coexistence test “complete”. | no NimBLE on `k1_main_rpl_im69d` |
| Encoders / I2C | `K1_HAS_ROTATE8=0`; SDA/SCL = -1 | `constants.h:212-214,462-463` |
| Upload guard | `scripts/platformio/k1_upload_guard.py` + `k1_device_identities.json` chip `9087A500` / USB `B4:3A:45:A5:87:90` | identities.json:58-72 |
| Flash method | `bash scripts/agent/k1-flash-verified.sh <env> --port /dev/cu.usbmodem1101` after identity. Refuses dirty `SPECTRASYNQ_K1_FIRMWARE` / `platformio.ini`. | `k1-flash-verified.sh:50-60` |
| Audio contract | `DEFAULT_SAMPLE_RATE=12800`, `DEFAULT_SAMPLES_PER_CHUNK=96`, tempo decimation 3 | `platformio.ini:76-78` |
| Live hop | `CONFIG.SAMPLE_RATE: 12800` `SAMPLES_PER_CHUNK: 96` | `:dump` |

USB-audio probe `k1_usb_audio_mac_probe` extends this env but **bumps the platform to 55.03.311** and takes the USB PHY. **Do not copy that platform bump** for PCM or NFC.

Parked I2S LED eval `k1_main_rpl_i2sled_probe` bricked this unit in August (`docs/forensics/runtime-evidence/20260820T-i2sled-rpl-brick/`). LCD_CAM/I2S LED remains **PARKED**. PCM uses **I2S1 standard slave RX**, not that driver.

## 4. Peripheral ownership

### I2S

| Controller | Owner on `k1_main_rpl_im69d` | Verdict |
|---|---|---|
| `I2S_NUM_0` | IM69D PDM RX, pins 8/9, 12.8 kHz | **occupied** — keep |
| `I2S_NUM_1` | no `I2S_NUM_1` reference in firmware `.h/.cpp/.ino` | **free** — PCM1808 slave RX |
| LCD_CAM / Yves I2S LED | compiled empty unless `K1_LED_I2S_DIRECT_V1` | **not in this env** |

`init_i2s()` returns immediately if `K1_AUDIO_SOURCE_MIC` is 0 (`i2s_audio.h:285-287`). Under IM69 PDM it inits **PDM** on 8/9, **not** `i2s_std` on leftover SPH macros 13/11/14 (`i2s_audio.h:325-360` vs `:373-420`).

Canonical 96-sample commit already exists: `k1_audio_commit_canonical_frame()` in `audio/k1_audio_ingress.h`. USB uses it. PCM must use the same seam, with a **new** exclusive source flag, not a splice into the PDM unpacker.

### SPI

No general-purpose SPI host is claimed on the S3 Main RPL image. The only `SPI2_HOST`/`SPI3_HOST` consumer is P4 LED transport (`platform/k1_p4_led_transport.cpp`). **SPI2_HOST (FSPI)** is the preferred ST25 host with matrix GPIOs.

### RNG

`RNG_SEED_PIN` is GPIO10 on this pinmap (`constants.h:474`). **No `analogRead(RNG_SEED_PIN)` consumer** in `SPECTRASYNQ_K1_FIRMWARE`. Soft reservation only.

## 5. Pin-conflict matrix (Main RPL / `k1_main_rpl_im69d` only)

**Do not use this table on `k1_hardware`.** GPIO6/7 are LEDs there.

Legend: **FREE** = usable for this bring-up; **KEEP** = do not steal; **NC** = do not wire this session.

| GPIO | Exposed? | Current net/function | Dir | Strap/boot | Flash/PSRAM | USB | LED | Audio | Debug | PCM role | NFC role | Verdict | Evidence |
|---:|:---:|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | header | boot strap | I | **strap** | no | no | no | no | no | — | — | **KEEP** | ESP32-S3 strap |
| 1 | header | unused | — | no | no | no | no | no | no | alt | alt | FREE spare | no firmware claim |
| 2 | header | unused | — | not S3 strap | no | no | no | no | no | — | **IRQ** | **ACCEPT NFC IRQ** | no firmware claim |
| 3 | header | strap | I | **strap** | no | no | no | no | no | — | — | **KEEP** | ESP32-S3 strap |
| 4 | header | unused (bench LED on other envs) | — | no | no | no | **no on RPL** | no | no | — | **CS** | **ACCEPT NFC CS** | RPL LEDs are 15-18 |
| 5 | header | unused (bench LED on other envs) | — | no | no | no | **no on RPL** | no | no | — | **MISO** | **ACCEPT NFC MISO** | same |
| 6 | header | unused (**LED on `k1_hardware`**) | — | no | no | no | **no on RPL** | no | no | — | **MOSI** | **ACCEPT NFC MOSI on RPL only** | `constants.h:449` vs `:540` |
| 7 | header | unused (**LED on `k1_hardware`**) | — | no | no | no | **no on RPL** | no | no | — | **SCLK** | **ACCEPT NFC SCLK on RPL only** | same |
| 8 | yes | IM69D PDM DATA | I | no | no | no | no | **yes** | no | — | — | **KEEP** | `constants.h:456` |
| 9 | yes | IM69D PDM CLK | O | no | no | no | no | **yes** | no | — | — | **KEEP** | `constants.h:455` |
| 10 | header | `RNG_SEED_PIN` (no consumer) | — | no | no | no | no | leftover name only | no | **DATA** | — | **ACCEPT PCM DATA** | `constants.h:474`; no analogRead |
| 11 | header | leftover `I2S_LRCLK_PIN` (unused under PDM) | — | no | no | no | no | leftover SPH macro | no | alt DATA | — | FREE spare | `constants.h:446`; PDM path does not init std I2S |
| 12 | reserved | `K1_IM69_PDM_SEL_PIN` unused-by-design | — | no | no | no | no | **reserved** | no | — | — | **KEEP** — never drive | `constants.h:457` |
| 13 | header | leftover `I2S_BCLK_PIN` (unused under PDM) | — | no | no | no | no | leftover SPH macro | no | **BCLK in** | — | **ACCEPT PCM BCLK** | `constants.h:445`; `i2s_audio.h:325-360` |
| 14 | header | leftover `I2S_DIN_PIN` (unused under PDM) | — | no | no | no | no | leftover SPH macro | no | **LRCK in** | — | **ACCEPT PCM LRCK** | `constants.h:447` |
| 15 | yes | primary LED DIN-A | O | no | no | no | **yes** | no | no | — | — | **KEEP** | `constants.h:449` |
| 16 | yes | primary LED DIN-B | O | no | no | no | **yes** | no | no | — | — | **KEEP** | `:450` |
| 17 | yes | secondary LED DIN-A (I2C displaced) | O | no | no | no | **yes** | no | no | — | — | **KEEP** | `:451` |
| 18 | yes | secondary LED DIN-B | O | no | no | no | **yes** | no | no | — | — | **KEEP** | `:452` |
| 19 | USB | USB D− | — | no | no | **yes** | no | no | Serial-JTAG | — | — | **KEEP** | live `303A:1001` |
| 20 | USB | USB D+ | — | no | no | **yes** | no | no | Serial-JTAG | — | — | **KEEP** | same |
| 21 | header | unused | — | no | no | no | no | no | no | **MCLK NC** | — | **NC this session** | brief reserve |
| 33-37 | module | OPI PSRAM | — | no | **yes** | no | no | no | no | — | — | **KEEP** | N16R8 OPI |
| 43 | UART | U0TXD | O | no | no | no | no | no | UART0 | — | — | **KEEP** | S3 DevKit |
| 44 | UART | U0RXD | I | no | no | no | no | no | UART0 | — | — | **KEEP** | S3 DevKit |
| 45 | — | strap / VDD_SPI | — | **strap** | related | no | no | no | no | — | — | **KEEP** | ESP32-S3 strap |
| 46 | — | strap | — | **strap** | no | no | no | no | no | — | — | **KEEP** | ESP32-S3 strap |

`k1-hardware-definition.md` still lists generic `k1_hardware` LED 6/7 + SPH 13/11/14. **That file is stale for Main RPL.** Live authority is `constants.h` `K1_MAIN_RPL_PINMAP_V1` + `docs/hardware/main-rpl-pin-receipt-2026-08-18.md` + this table.

## 6. Candidate maps vs live authority

### PCM1808 — ACCEPT on this env

| PCM | ESP32-S3 | Dir | Note |
|---|---|---|---|
| BCLK | GPIO13 | module → S3 | leftover SPH BCLK macro; unused at runtime |
| LRCK | GPIO14 | module → S3 | leftover SPH DIN macro; unused at runtime |
| DATA | GPIO10 | module → S3 | RNG seed name only; no consumer |
| MCLK | GPIO21 | **no wire** | reserved |
| GND | GND | common | first |

Peripheral: **I2S1** standard Philips slave RX, 48 kHz, 32-bit slots, 64 BCLK/frame.

Do not init `i2s_std` on I2S0 with `I2S_BCLK_PIN`/`I2S_DIN_PIN` while PCM owns 13/14.

### ST25R3916B — ACCEPT on this env only

| ST25 | ESP32-S3 | Note |
|---|---|---|
| SCLK | GPIO7 | **LED on `k1_hardware` — probe must extend `k1_main_rpl_im69d`** |
| MOSI | GPIO6 | same |
| MISO | GPIO5 | free on RPL |
| CS | GPIO4 | free on RPL |
| IRQ | GPIO2 | input; ISR flag/notify only, no SPI in ISR |

Host: **SPI2_HOST**. Do not base the NFC probe on `k1_hardware`.

## 7. Live runtime baseline (pre-change, product image)

No firmware feature edits this session. Serial was read-only (`:build`, `:dump`). No `start_noise_cal`. No flash.

| Field | Live |
|---|---|
| CHIP ID | `9087A500` |
| env / git / epoch | `k1_main_rpl_im69d` / `acaecaa8` / `1788173468` |
| SAMPLE_RATE / hop | 12800 / 96 |
| I2S_PORT | 0 |
| SYSTEM_FPS | 138.30 |
| LED_FPS | 139.26 |
| CAL | `persisted_profile` valid=1 SSL=157 DC=−238 reason=none |
| LOOK | slot=1 `SHARED_1D_256` sec=inherit (registry last parked slot 0 after Colour Lab; record live, do not “fix”) |
| lightshow | 18 |
| AUDIO_RESPONSE_GAIN | 1.0 |
| PHOTONS / CHROMA / MOOD | 1.0 / 0.05 / 0.65 |
| MAX_CURRENT_MA | 2500 |
| Mic | AP telemetry running; `raw_i16_abs_peak` 10–25 in this window; `silence=0` |
| WDT / reset | none observed during the identity+dump window |
| PSRAM | build has `BOARD_HAS_PSRAM`; dump does not print a heap line |

## 7b. Host compile / test (this working tree, no feature edits)

| Check | Result |
|---|---|
| `bash scripts/agent/pio-build.sh k1_main_rpl_im69d` | **SUCCESS** 34.24 s. RAM 117272/327680 (35.8%). Flash 727930/6553600 (11.1%). `firmware.bin` 728336 B SHA-256 `448748783a86876b08f353a7687c2cc18e46ee1cdb042aae013ee9d1ebf8aabc` |
| `python3 -m pytest tests/ -q --tb=line` | **4 failed**, 1694 passed, 1 skipped. Failures are **pre-existing dirty BLE-iPhone probe**, not this lane: `test_k1_serial_safety.py` (3) from `#ifdef K1_BLE_MIDI_PERIPHERAL` / `ble_iphone` in the dirty serial table; `test_k1_upload_guard.py::test_all_k1_chip_bound_envs_are_registered_in_guard` from untracked `[env:k1_ble_iphone_probe]`. **Not fixed here.** |
| Flash | **not performed** |

The Main RPL product image on silicon is still `acaecaa8` / epoch `1788173468`. The just-built `.pio` bin is a dirty-tree rebuild and is **not** a restore image.

## 8. Known-good restore path

| Asset | Status |
|---|---|
| Live product | already `k1_main_rpl_im69d` @ `acaecaa8` |
| Registry factory SHA `4bd481f8356055ff1ab728b93431f226d5361ac9492f397a25cb8965a383fd72` (728336 B, epoch `1787773671`) | **not present** in this checkout (`docs/`, `tools/webflash/`, `.pio/build`) |
| `tools/webflash/firmware/k1_main_rpl_im69d/firmware.bin` | **STALE** 708816 B SHA `fc35f45c…` dated 2026-08-26 — **do not flash** |
| `.worktrees/effect-response-atlas/.../firmware.bin` | 728336 B but SHA `857cc398…` ≠ factory |

**Restore after a probe:** rebuild `k1_main_rpl_im69d` from **clean commit `acaecaa8`** (not this dirty tree) and flash with:

```bash
bash scripts/agent/k1-flash-verified.sh k1_main_rpl_im69d --port /dev/cu.usbmodem1101
```

That script refuses dirty firmware source. Identity must still be USB `B4:3A:45:A5:87:90` / chip `9087A500`. NVS/cal inherited; do not erase; do not `start_noise_cal`.

## 9. Firmware architecture (planned, not implemented)

After 96 kHz then 48 kHz clock PASS and wiring:

- Probe env `k1_main_rpl_pcm1808_probe` extends `k1_main_rpl_im69d`.
- Flags: `K1_AUDIO_SOURCE_PCM1808=1` `K1_AUDIO_SOURCE_MIC=0` (fail-closed exclusivity in `k1_audio_source.h`).
- Files: `audio/k1_pcm1808_input.{h,cpp}`, `audio/k1_resample_48k_to_12k8.{h,cpp}`.
- I2S1 slave RX; I2S0 PDM left compiled but not canonical source.
- 360 stereo 48 kHz frames → 96 mono 12.8 kHz via stateful polyphase FIR (ratio 4/15).
- Commit via existing `k1_audio_commit_canonical_frame()`.
- No mic NVS writes in PCM mode.
- NFC later: `K1_NFC_ST25R3916B_BENCH` on a second probe env, then a combined env.
- Register new envs in `k1_device_identities.json` under chip `9087A500` only.

## 10. Stop — first physical measurement

**Do not write PCM firmware. Do not connect I2S to the S3.**

PCM module still in **untouched default**: OP1 open, OP2 open, OP3 open (96 kHz / 24-bit I2S / master).

Need, with **only the PCM board powered at 5.0 V** (current-limited), common GND to the scope, **no ESP32 signal wires**:

1. Visual: OP1/OP2/OP3 all open, no solder splash, polarity understood.
2. Supply current and no heating.
3. Logic level of LRCK/BCLK/DATA (must be 3.3 V-safe for the S3).
4. Frequencies:

| Net | Expected if table is right |
|---|---|
| LRCK | ≈ 96.000 kHz |
| BCLK | ≈ 6.144 MHz |
| BCLK/LRCK | ≈ 64 |
| MCLK header | ≈ 24.576 MHz **hypothesis — measure** |
| DATA | activity with/without analogue input |

PASS only if LRCK ≈ 96 kHz and BCLK stays 64× LRCK. If not: stop, record the frequencies, do not write firmware to “match” a mystery clock.

After that PASS: power off, **short OP2 only**, re-measure for LRCK ≈ 48 kHz / BCLK ≈ 3.072 MHz **before** any I2S jumper to the S3.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-09-07 | agent:grok | Created from live checkout, USB identity, `:dump`, and Main RPL pinmap. |
