# ESP32-S3 Migration Prep

Date: 2026-05-22

## Current Result

The current SB Arduino source has an ESP32-S3 compile-only baseline. No source-level compile blocker was found during the first S3 probe.

The K1 hardware bring-up profile in this checkout is `SB_K1_HARDWARE`. Its GPIO map is taken directly from the active `Lightwave-Ledstrip/firmware-v3` K1 hardware production build flags.

Compile target used:

```text
esp32:esp32:esp32s3:USBMode=hwcdc,CDCOnBoot=cdc,MSCOnBoot=default,DFUOnBoot=default,UploadMode=default,CPUFreq=240,FlashMode=qio,FlashSize=8M,PartitionScheme=min_spiffs,DebugLevel=none,PSRAM=enabled,LoopCore=0,EventsCore=0,EraseFlash=none
```

Re-run the S3 compile-only check with:

```sh
bash tools/compile-s3-arduino.sh
```

Re-run the K1 hardware GPIO-profile compile-only check with:

```sh
bash tools/compile-k1-arduino.sh
```

The wrapper only calls `arduino-cli compile`. It does not upload, erase flash, reboot a device, or send serial commands.

## K1 hardware Firmware-v3 GPIO Source

Active firmware-v3 source:

```text
/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3/platformio.ini
```

The active K1 hardware production environment is `esp32dev_audio_esv11_k1v2`. Its build flags set:

```text
K1_LED_STRIP1_DATA=6
K1_LED_STRIP2_DATA=7
K1_I2S_LRCL=11
K1_I2S_DOUT=14
K1_I2S_BCLK=13
```

The `SB_K1_HARDWARE` profile maps those into SB as:

| Function | GPIO |
| --- | ---: |
| I2S BCLK | 13 |
| I2S LRCLK | 11 |
| I2S DIN | 14 |
| SB primary LED data / firmware-v3 strip1 | 6 |
| SB secondary LED data / firmware-v3 strip2 | 7 |
| I2C SDA/SCL | 17 / 18 |
| physical knobs/buttons/sweet-spot LEDs | disabled |

Do not use the stale K1 hardware comment in `Lightwave-Ledstrip/firmware-v3/platformio.ini` that mentions I2S GPIO 37/38/39. The active K1 hardware production build flags in that file use LED GPIO 6/7 and I2S GPIO 11/14/13.

Compile result on 2026-05-22:

```text
SB_K1_HARDWARE compile-only passed.
Sketch uses 503737 bytes (25%) of program storage space.
Global variables use 92876 bytes (28%) of dynamic memory.
```

## K1 hardware Upload Evidence

K1 hardware appeared as:

```text
/dev/cu.usbmodem1301
USB VID:PID=303A:1001
SER=B4:3A:45:A5:87:F8
Description: USB JTAG/serial debug unit
```

The SB K1 hardware build was uploaded to that explicit port only. Upload proof:

```text
Chip is ESP32-S3 (revision v0.2)
MAC: b4:3a:45:a5:87:f8
Hash of data verified.
Hard resetting via RTS pin.
New upload port: /dev/cu.usbmodemB43A45A587F82
```

The S2 capture unit remained separate as:

```text
/dev/cu.usbmodem02 - ESP32S2_DEV
```

Serial sanity after upload at 230400 baud:

```text
FIRMWARE_VERSION: 40102
CHIP ID: F887A500
CONFIG.LED_COUNT: 160
CONFIG.SAMPLE_RATE: 12800
I2S_PORT: 0
SECONDARY_ENABLED: true
SECONDARY_MODE: 3 (BLOOM)
```

## What This Proves

- Arduino CLI can compile the current firmware for `esp32:esp32:esp32s3`.
- The legacy I2S include path compiles for the S3 target.
- The existing S2-only I2S register adjustments are guarded by `CONFIG_IDF_TARGET_ESP32S2` and do not block an S3 compile.
- The current FastLED dependency compiles for the selected S3 board profile.
- The current PSRAM allocation path for `waveform_history` compiles with PSRAM enabled.

## What This Does Not Prove

- It does not prove the current GPIO map is electrically correct for the chosen S3 board.
- It does not prove I2S microphone capture works on S3 hardware.
- It does not prove FastLED timing, RMT/I2S LED output, or dual-strip signal integrity on S3 hardware.
- It does not prove button, encoder, potentiometer, or ROTATE8 wiring on S3 hardware.
- It does not prove 120 FPS runtime headroom on S3 hardware.

## Source Areas To Validate On Hardware

- `constants.h`: pin assignments for LEDs, I2S, buttons, potentiometers, sweet-spot controls, and ROTATE8 I2C.
- `i2s_audio.h`: microphone initialisation and sample capture behaviour.
- `SPECTRASYNQ_K1_FIRMWARE.ino`: PSRAM allocation, core pinning, LED task timing, and setup order.
- `serial_menu.h`: serial-only verification commands once an S3 device is dedicated to testing.

## Bring-Up Order

1. Keep S2 compile-only while the S2 remains a content-capture device.
2. Confirm the exact ESP32-S3 board module, flash size, PSRAM type, and final GPIO map.
3. Compile S2 and S3 from the same source tree before any S3 hardware test.
4. Use `SB_K1_HARDWARE` for the first SB-on-K1 hardware attempt.
5. Flash only the dedicated S3 bring-up device, never the active S2 capture unit.
6. Pass `--upload-port <K1_PORT>` explicitly; do not rely on a stale default port.
7. Validate serial boot and PSRAM allocation before enabling LEDs.
8. Validate I2S sample capture before judging any audio-reactive mode.
9. Validate LED output at low brightness/current before full render load.
10. Measure render timing and audio-to-visual latency before calling the port ready.
