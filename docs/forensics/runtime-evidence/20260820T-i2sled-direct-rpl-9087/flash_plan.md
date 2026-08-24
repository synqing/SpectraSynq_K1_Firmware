# Full-chain flash plan — Main RPL I2S direct probe (9087A500)

Evidence root: `docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/`

All commands below are from the **repository root**. `esptool.py` is
`~/.platformio/penv/bin/esptool.py` (not on PATH). `boot_app0.bin` is always
`common/boot_app0.bin` — never a bare filename.

Device: `/dev/cu.usbmodem1401`  
MAC must be `b4:3a:45:a5:87:90`  
Chip: `9087A500`

## Staged images

### Restore (proven silicon — do not rebuild into `restore/`)

- git **`d276fd68`** `k1_main_rpl_im69d`
- `restore/firmware.bin` SHA256 `c5c860ab1b974234488a7060fae23e5a60ebc4b6f9ddf7affb6b250eddfd5344`
- esptool: Checksum `0x94 (valid)`, Validation hash `baeeab65…260ec6c4 (valid)`
- `strings restore/firmware.bin` hits `d276fd68`

### Probe (this lane)

- git **`293490b4`** `k1_main_rpl_i2sled_probe`
- `probe/firmware.bin` SHA256 `f04828d33bcedae03338153c7df0908d018adbfd7092ed9b5b6275604566c44a`
- esptool: Checksum `0xcc (valid)`, Validation hash `33e163cf…9539b03f (valid)`
- `strings probe/firmware.bin` hits `293490b4`
- Flash mode DIO / 80 MHz / 16 MB — same header class as restore

### Common

- `common/boot_app0.bin` SHA256 `f94c5d786a7a8fab06ac5d10e33bf37711a6697636dc037559ea19cc410a17f0`

Offsets (fact 0.6, brick postmortem): bootloader `0x0`, partitions `0x8000`,
`boot_app0` `0xe000`, app `0x10000`. NVS at `0x9000` is **not** erased.

**Flash size:** `--flash_size keep` only (host diagnosis 2026-08-21). `16MB`
rewrites bootloader SHA and this USB-JTAG S3 then XOR-rejects the app.
See `DIAGNOSIS.md`. Do not flash this probe without a new named GO.

## 4.2 Identity preflight

```bash
~/.platformio/penv/bin/esptool.py --chip esp32s3 --port /dev/cu.usbmodem1401 read_mac
```

Must print `b4:3a:45:a5:87:90`. Mismatch = STOP. Do not write.

## 4.4 Probe flash (never app-only)

```bash
~/.platformio/penv/bin/esptool.py --chip esp32s3 --port /dev/cu.usbmodem1401 --baud 460800 write_flash \
  --flash_mode dio --flash_freq 80m --flash_size keep \
  0x0 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/probe/bootloader.bin \
  0x8000 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/probe/partitions.bin \
  0xe000 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/common/boot_app0.bin \
  0x10000 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/probe/firmware.bin
```

## 4.5 Verify

```bash
~/.platformio/penv/bin/esptool.py --chip esp32s3 --port /dev/cu.usbmodem1401 --baud 460800 \
  verify_flash 0x10000 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/probe/firmware.bin
```

Fail = 4.8 restore immediately.

## 4.6 Boot gate (within 30 s of CDC coming back)

Require:

- `IDENTITY OK: env=k1_main_rpl_i2sled_probe`
- full line `I2S_EMIT: init core=1 lanes=4 slots=160` (not `INIT_LEDS: PASS`
  alone — that is a Core-0 show skip; see `DIAGNOSIS.md`)
- no `Guru Meditation` / `esp_image` / `Checksum failed` in the next 5 s

Any `esp_image` / `Checksum failed` / boot loop / `I2S_EMIT: FAIL psram` = 4.8.

## 4.8 Auto-restore (paste-ready)

```bash
~/.platformio/penv/bin/esptool.py --chip esp32s3 --port /dev/cu.usbmodem1401 --baud 460800 write_flash \
  --flash_mode dio --flash_freq 80m --flash_size keep \
  0x0 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/restore/bootloader.bin \
  0x8000 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/restore/partitions.bin \
  0xe000 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/common/boot_app0.bin \
  0x10000 docs/forensics/runtime-evidence/20260820T-i2sled-direct-rpl-9087/restore/firmware.bin
```

Then verify `0x10000 restore/firmware.bin` and boot-gate against
`IDENTITY OK: git=d276fd68 env=k1_main_rpl_im69d`.
