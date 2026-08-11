# ESP‑Hosted Co‑Processor (ESP32‑C6) — Update Guide

Your Tab5 (ESP32‑P4 host) uses ESP‑Hosted over SDIO to talk to the on‑board ESP32‑C6. If host and co‑processor (C6) run different ESP‑Hosted versions, you can see STA connect failures and warnings like:

> Version on Host is NEWER than version on co‑processor

This indicates a protocol/API mismatch. Fix by updating the C6 (slave) firmware to match the host’s ESP‑Hosted version.

## Host Stack Versions (detected from this repo)

From `vendor/pio_packages/framework-arduinoespressif32-libs/versions.txt`:

- `esp-idf`: release/v5.4
- `espressif__esp_hosted`: 2.0.13
- `espressif__esp_wifi_remote`: 0.13.0

These are the versions to target for the ESP32‑C6 build when using ESP‑Hosted over SDIO.

Tip: run `scripts/print_esp_hosted_versions.sh` to re‑print these quickly.

## Update Options

- Recommended: Use an official/prebuilt M5 Tab5 C6 (ESP‑Hosted) image if available from M5Stack.
- Otherwise: Build the ESP‑Hosted “slave” for ESP32‑C6 from source with ESP‑IDF release/v5.4 and ESP‑Hosted v2.0.13.

## Building ESP‑Hosted (ESP32‑C6, SDIO)

1) Install ESP‑IDF 5.4

- Follow Espressif’s install guide, or use `esp-idf` tools installer.
- Confirm: `idf.py --version` shows `v5.4`.

2) Get ESP‑Hosted v2.0.13

```bash
git clone https://github.com/espressif/esp-hosted.git
cd esp-hosted
git checkout v2.0.13
```

3) Select the ESP32‑C6 SDIO “slave” project

- In v2.0.13, the co‑processor (slave) IDF project lives under the repo’s `esp_hosted` examples. The exact path can vary by release; look for the ESP32‑C6 SDIO example/project (name often contains `sdio` and `slave`).
- If unsure, search in the repo for `CONFIG_ESP_HOSTED_TRANSPORT_SDIO` and `idf_component.yml` near an `esp32c6` target.

4) Configure for SDIO + ESP32‑C6

```bash
idf.py set-target esp32c6
idf.py menuconfig
```

In menuconfig, ensure:
- Transport: SDIO (CONFIG_ESP_HOSTED_TRANSPORT_SDIO=y)
- SDIO slave mode enabled
- Pins/HSPI interface per the Tab5 hardware design (often defaults are correct for the C6 on Tab5; do not change unless you know the board routing). 

5) Build and flash

```bash
idf.py -p /dev/ttyACM0 flash monitor   # adjust port
```

Power‑cycle the Tab5 after flashing the C6.

### Fast Path: Use the included helper script

You can automate the clone, build, and flash steps with:

```bash
K1.tab5/pio/deck/scripts/build_flash_c6_esp_hosted.sh \
  --port /dev/ttyACM0 --baud 1500000 --branch v2.0.13
```

Notes:
- Requires ESP‑IDF v5.4 available via `idf.py` in PATH or provide `--idf-path /path/to/esp-idf`.
- The script auto‑clones esp‑hosted into `K1.tab5/pio/deck/.thirdparty/` and attempts to detect the ESP32‑C6 SDIO slave project.
- If detection fails, pass `--project-dir` to the specific esp‑hosted slave project directory.

## Validate

On the P4 host (this deck firmware), open serial logs:

```bash
pio device monitor -b 115200
```

Expected after successful update:
- No “Version on Host is NEWER…” warning.
- SDIO init logs (mempool etc.) followed by Wi‑Fi STA connect progressing beyond 0x3007 failures.
- `[net] Wi‑Fi ready ip=…` and normal OSC traffic.

## Troubleshooting

- If the warning persists, confirm both sides are on the same major/minor (host: esp_hosted 2.0.13 / IDF v5.4; slave: built against the same).
- Ensure your SSID is 2.4 GHz only (ESP32‑C6 STA), no captive portal.
- Check that the C6 boots and doesn’t reset loop; monitor via its UART if possible.
- As a fallback, you could pin the host to older ESP‑Hosted/Wi‑Fi Remote libraries that match the current C6 image, but the preferred path is updating the C6.

## Notes

- The host initializes ESP‑Hosted via Arduino core for ESP32‑P4; SDIO pins are set in `src/main.cpp` with `WiFi.setPins(...)` before Wi‑Fi init.
- Do not try to mix Arduino Wi‑Fi and raw IDF Wi‑Fi on the host build; the Arduino‑only P4 platform already integrates ESP‑Hosted correctly.
