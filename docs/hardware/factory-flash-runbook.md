---
abstract: "Step-by-step factory provisioning runbook for K1 units: build the k1_hardware target, assemble a single flashable factory image with make_factory_image.py (esptool merge_bin), optionally generate a per-unit NVS partition with make_unit_nvs.py, verify the unit by CHIP-ID (never by port) against device-build-registry.md, then flash and confirm 'Hash of data verified' + 'Hard resetting'. Per-unit serial/SKU scheme is Captain decision D4 — UNDECIDED; the NVS template is a placeholder. The tooling assembles and provisions only — it never flashes; the operator runs the single esptool write_flash command by hand."
---

# K1 Factory Flash Runbook

This runbook covers assembling and flashing a complete K1 firmware image at the
bench. The tooling **assembles and provisions only — it never flashes**. The
operator runs the single `esptool write_flash` command by hand after verifying
the unit's identity.

> **Identity is the chip-ID, never the port.** The two bench K1 units enumerate
> with the same USB product name, so the serial-port path (`/dev/tty.usbmodem…`)
> is not a safe identity. Always confirm the chip-ID before any write. See
> [`device-build-registry.md`](./device-build-registry.md) for the canonical
> device ↔ build ↔ chip-ID map.

> **Captain decision D4 — UNDECIDED.** The per-unit serial / SKU scheme is not
> yet decided. The NVS template (`scripts/release/unit_nvs_template.csv`) is a
> clearly-marked placeholder. Do **not** mint real production units from
> placeholder NVS output — generate the NVS step only once D4 is resolved and the
> template carries the agreed scheme.

## Flash layout (ESP32-S3, default_16MB.csv)

| Offset    | Artefact         | Source                                        |
|-----------|------------------|-----------------------------------------------|
| `0x0`     | `bootloader.bin` | build dir (S3 bootloader offset is `0x0`)     |
| `0x8000`  | `partitions.bin` | build dir (partition table)                   |
| `0x9000`  | NVS partition    | optional — `make_unit_nvs.py` (size `0x5000`) |
| `0xe000`  | `boot_app0.bin`  | arduino-esp32 framework package (OTA-data)     |
| `0x10000` | `firmware.bin`   | build dir (application)                        |

The assembled factory image is a single binary written at `0x0`.

## Step 1 — Build the production target

Build the canonical production environment. Use an isolated build dir if you are
working in a worktree:

```bash
export PLATFORMIO_BUILD_DIR=/path/to/.pio_isolated   # optional, for worktrees
pio run -e k1_hardware
```

This produces `bootloader.bin`, `partitions.bin`, and `firmware.bin` under the
env build dir (`$PLATFORMIO_BUILD_DIR/k1_hardware`, or `.pio/build/k1_hardware`
by default).

## Step 2 — (Optional, D4-gated) Generate a per-unit NVS partition

Only once decision D4 is resolved and the template carries the real scheme:

```bash
python3 scripts/release/make_unit_nvs.py \
    --serial <DEVICE-SERIAL> --sku <SKU> [--calibration <TAG>] \
    --output build/unit-<serial>.nvs.bin
```

The generator substitutes the template tokens, runs ESP-IDF
`nvs_partition_gen.py`, and writes a `0x5000` NVS binary. It never touches a
device. Omit this step to flash an unprovisioned image (the unit provisions NVS
at first boot).

> `nvs_partition_gen.py` (this ESP-IDF vintage) imports `distutils`, removed in
> Python 3.12+. The generator therefore runs the tool under the PlatformIO penv
> interpreter by default; override with `--python <path>` if your IDF Python
> lives elsewhere.

## Step 3 — Assemble the factory image

```bash
# Unprovisioned image:
python3 scripts/release/make_factory_image.py

# Provisioned image (folds the per-unit NVS in at 0x9000):
python3 scripts/release/make_factory_image.py --nvs build/unit-<serial>.nvs.bin
```

The assembler resolves the build artefacts, locates `boot_app0.bin` in the
framework package, runs `esptool merge_bin`, and prints the output image path
plus the exact `write_flash` command. It **does not flash**.

## Step 4 — Verify the unit by chip-ID (before any write)

Read the chip-ID of the connected unit and confirm it matches the unit you intend
to flash, per [`device-build-registry.md`](./device-build-registry.md):

```bash
esptool --chip esp32s3 --port <PORT> chip_id
```

If the chip-ID does not match the intended unit, **stop** — do not flash. Cross-
flashing a unit with the wrong GPIO pin map silences its output.

## Step 5 — Flash (operator-run)

Run the command the assembler printed:

```bash
esptool --chip esp32s3 --port <PORT> write_flash 0x0 <build-dir>/k1_factory.bin
```

## Step 6 — Confirm success

Confirm esptool reports **both** of the following before unplugging:

- `Hash of data verified`
- `Hard resetting`

If either is absent, the write did not complete — re-seat the cable, re-verify
the chip-ID, and re-flash. Do not record the unit as provisioned until both
markers are observed.

## Update the registry

After a successful flash, update the deployed-state table in
[`device-build-registry.md`](./device-build-registry.md) with the unit, commit,
env, and (when D4 is live) the per-unit serial/SKU.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:ssa (lane N4) | Created — factory image assembly + per-unit NVS provisioning + chip-ID-first flash runbook. D4 NVS scheme noted as pending. |
