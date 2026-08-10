# K1 Tab5 Firmware

This directory is the canonical in-repo PlatformIO project for the M5Stack Tab5 controller firmware.

The previous standalone checkout is historical only. Build, flash, and source
edits for Tab5 firmware now happen from this directory:

```bash
cd tab5_firmware
```

## Current Contract

- Transport direction: BLE MIDI controller for K1, not STA Wi-Fi and not OSC.
- `src/ble_midi_transport.cpp` owns BLE-MIDI packet/program-change/control-change output.
- The production P4 application does not compile the retired SoftAP/OSC path.
- The UI stays usable without a host connection; the blocking "waiting for host" overlay is disabled.
- Screen rotation is set for inverse landscape on the Tab5.
- Berkeley Mono is the active LVGL font path.

## Bearer Boundary

The Tab5 P4 build compiles the hosted NimBLE GATT path when
`CONFIG_ESP_HOSTED_ENABLE_BT_NIMBLE`, `CONFIG_NIMBLE_ENABLED`, and
`host/ble_gap.h` are available (ESP-IDF NimBLE host includes via the Arduino+ESP-IDF
framework). Runtime still requires ESP-Hosted SDIO (P4↔C6) to come up before
`BLEDevice::init("K1 Tab5")`.

Expected boot markers when the C6 HCI pipe is healthy:

```text
[ble-midi] SDIO transport TX ready after …
[ble-midi] GATT advertising service=03B80E5A-EDE8-4B33-A751-6CE34EC4C700 characteristic=7772E5DB-3868-4112-A1A9-F2669D106BF3
[net] disabled SoftAP/OSC; transport=BLE MIDI gatt=hosted-nimble
```

If SDIO stays down:

```text
[ble-midi] bearer=pending (SDIO not up); skipping BLEDevice::init
```

Observed on silicon (2026-08-07): SDIO TX can be ready and Host BT VHCI enabled while the
on-board ESP32-C6 still fails HCI Reset (`BLE_HS_ETIMEOUT_HCI` / controller unresponsive).
That means the P4 host path is live but the C6 BLE controller firmware/path is not —
GATT advertising will not start until a BT-capable ESP-Hosted C6 image is flashed via the
C6 download header (USB-TTL), or the dedicated ESP32-S3 radio fallback is activated
(`K1_DECK16_TAB5_BLE_R1`).

Historical compile-time pending marker (stale once GATT is compiled in):

```text
[ble-midi] bearer=pending-p4-c6-ble-host; Wi-Fi/STA disabled
```

## Build

```bash
cd tab5_firmware
~/.platformio/penv/bin/pio run -e tab5_p4
```

The main firmware image is emitted at:

```bash
.pio/build/tab5_p4/firmware.bin
```

## Flash Tab5

Use the explicit port. For the currently connected Tab5:

```bash
cd tab5_firmware
scripts/flash_tab5_p4.sh --port /dev/tty.usbmodem11401 --baud 1500000
```

## Serial Proof

```bash
~/.platformio/penv/bin/python - <<'PY'
import serial, time, sys

port = '/dev/tty.usbmodem11401'
ser = serial.Serial(port, baudrate=115200, timeout=0.1)
try:
    ser.write(b'status\n')
    deadline = time.time() + 1.0
    while time.time() < deadline:
        data = ser.read(4096)
        if data:
            sys.stdout.write(data.decode('utf-8', errors='replace'))
finally:
    ser.close()
PY
```

Useful encoderless stop-gap commands:

- `status`
- `e+`, `e-`, `e=<0..127>`
- `b+`, `b-`, `b=<0..1|0..100>`
- `p1+`, `p1-`, `p1=<v>`
- `p2+`, `p2-`, `p2=<v>`
- `p6+`, `p6-`, `p6=<v>`
- `m` or `p7=<0|1>` for the mirror stop-gap.

## Build Options

- `env:tab5_p4`: active Tab5 ESP32-P4 firmware.
- `env:tab5_p4_hci_diag`: non-shippable hosted-HCI diagnostic build.
- `env:native_sdl`: host simulator and transaction-test surface.
- `env:diag_display`: display-only smoke target.

## Local Config

`include/tab5_config.h` contains non-secret UI and persistence defaults for this BLE-MIDI build. The old Wi-Fi credential workflow is no longer part of the active Tab5 firmware direction.
