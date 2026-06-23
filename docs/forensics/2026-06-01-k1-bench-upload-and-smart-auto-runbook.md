---
abstract: "Operational runbook for the two-K1 bench mapping, upload guard, Smart Auto demo state, and manual-owner safety checks."
evidence-tier: "operator-runbook"
created: "2026-06-01"
---

# K1 Bench Upload And Smart Auto Runbook

## When To Use

Use this before any two-K1 upload, Smart Auto A/B run, harness run, or recovery
work on the current bench.

This runbook exists because the two K1s expose the same ESP32-S3 USB product
name. Port name alone is not a safe identity signal.

## Current Bench Truth

| Physical unit | Port | USB serial | Chip ID | PlatformIO env | GPIO pin map |
|---|---|---|---|---|---|
| Main K1v2 | `/dev/tty.usbmodem12201` | `B4:3A:45:A5:89:B4` | `B489A500` | `k1_bench_reference` | bench-reference |
| Second bench K1 | `/dev/tty.usbmodem1401` | `B4:3A:45:A5:87:F8` | `F887A500` | `k1_hardware` | default hardware |

`k1_hardware_harness` and `k1_hardware_trace_dev` inherit the default
`k1_hardware` GPIO pin map. They therefore belong on the second bench K1 unless
a future lane explicitly changes the pin-map contract.

## Guarded Upload Commands

```bash
pio run -e k1_bench_reference -t upload --upload-port /dev/tty.usbmodem12201
pio run -e k1_hardware -t upload --upload-port /dev/tty.usbmodem1401
```

Harness/trace-dev, only when the active lane calls for them:

```bash
pio run -e k1_hardware_harness -t upload --upload-port /dev/tty.usbmodem1401
pio run -e k1_hardware_trace_dev -t upload --upload-port /dev/tty.usbmodem1401
```

Do not bypass `scripts/platformio/k1_upload_guard.py`. The guard is installed
through `platformio.ini` and refuses env/port/USB-serial mismatches before
firmware is written.

## Identity Preflight

Read USB identity:

```bash
python3 - <<'PY'
from serial.tools import list_ports
for p in list_ports.comports():
    if "usbmodem" in p.device:
        print(p.device, p.serial_number, p.location, p.hwid)
PY
```

Read firmware identity:

```bash
python3 - <<'PY'
import serial, time
for port in ("/dev/tty.usbmodem12201", "/dev/tty.usbmodem1401"):
    with serial.Serial(port, 115200, timeout=0.25, write_timeout=1) as ser:
        time.sleep(0.3)
        ser.reset_input_buffer()
        for cmd in (":version", ":chip_id"):
            ser.write((cmd + "\n").encode())
            ser.flush()
            time.sleep(0.25)
        deadline = time.time() + 2
        print("==", port, "==")
        while time.time() < deadline:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if line:
                print(line)
PY
```

Expected:

- `/dev/tty.usbmodem12201`: `VERSION: 40103`, chip ID `B489A500`
- `/dev/tty.usbmodem1401`: `VERSION: 40103`, chip ID `F887A500`

## Smart Auto Current Demo State

Current status: `product-validation-passed-for-current-demo`.

Evidence:

- `docs/forensics/runtime-evidence/2026-06-01T203320-smart-auto-ab-manifest.json`
- `docs/forensics/runtime-evidence/2026-06-01-smart-auto-product-ab-closeout-v2.md`

The demo pass means the current Smart Auto policy passed Captain live visual
judgement on at least two of the three fixed clips. It does not claim product
finality across a larger corpus.

## Smart Auto A/B Procedure

```bash
python3 -B scripts/regression-harness/smart_auto_product_ab_capture.py \
  --main-port /dev/tty.usbmodem12201 \
  --bench-port /dev/tty.usbmodem1401
```

The script assigns:

- main K1v2 / `12201`: `:smart_scene=l1`
- second bench K1 / `1401`: `:smart_scene=auto`

The script does not issue calibration, erase, upload, or destructive commands.

Promotion rule:

- pass if Auto clearly wins at least two of three clips without flooding,
  strobing, colour washout, or arbitrary mode thrash;
- otherwise keep the result in `review` and continue policy tuning.

## Manual-Owner Safety Rules

Smart autonomy must yield to operator-owned visual changes. The current rule is:

- hotkeys for mode, palette, auto-colour, photons, chroma, mood, saturation,
  prism, base coat, VP bloom/wave controls, and visual toggles mark manual owner;
- typed visual controls mark manual owner: `set_mode`, `photons`, `chroma`,
  `mood`, `palette_mode`, `palette_index`, `auto_color_shift`, `preset`,
  `secondary_*` mutation commands, `edge_*` mutation commands, `vp_bloom_*`, and
  `vp_wave_*`;
- read-only `secondary_status` and `edge_status` do not mark manual owner;
- `smart_*` commands do not self-mark manual owner, because they are the control
  surface for enabling, disabling, and handing ownership back to Smart;
- `smart_scene` explicitly clears manual owner after applying the selected
  runtime recipe.

Audit coverage:

```bash
python3 -B -m unittest tests.test_smart_visual_engine_static
```

## Recovery Notes

If a unit appears bricked after upload, first assume wrong pin map or USB CDC
state before assuming permanent hardware failure.

1. Stop all capture/playback/upload processes.
2. Verify `/dev/tty.usbmodem*` and `/dev/cu.usbmodem*` enumeration.
3. Verify USB serials with `serial.tools.list_ports`.
4. If both ports exist, restore the guarded mapping with the upload commands
   above.
5. If a unit does not enumerate, power-cycle it. If required, use BOOT mode to
   re-enumerate before flashing the correct env.
6. Do not run erase unless Captain explicitly requests erase as the recovery
   path.

## Hard Stops

- Do not run `start_noise_cal` or `N`/`Y` unless Captain confirms a silence
  window.
- Do not flash when USB serial does not match the env mapping.
- Do not push, release-tag, erase, or rewrite history from this runbook.
- Do not treat a build or upload as runtime proof.

## Changelog

| Date | Change |
|---|---|
| 2026-06-01 | Created after upload-guard recovery and Smart Auto current-demo pass. |
