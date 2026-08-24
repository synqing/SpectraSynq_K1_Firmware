# Host diagnosis — probe ROM XOR vs stored `0xcc` (no device write)

**Date:** 2026-08-21  
**Scope:** named remaining agent step in `RESULT.md`. Host-only. No flash.  
**Staged bins:** SHA256SUMS still match the files on disk.

## Verdict

The probe `.bin` is a **valid ESP32-S3 image**. Host `image_info` Checksum `0xcc (valid)` and Validation hash `33e163cf…9539b03f (valid)` are not a lie. ROM `Checksum failed. Calculated <varies> read 0xcc` is **not** “the linker emitted a bad XOR.”

Two stacked failures, already in this pack’s logs:

| # | When | What actually failed |
|---|------|----------------------|
| 1 | First probe write (`probe_write_flash.log`) | `write_flash --flash_size 16MB` printed **`SHA digest in image updated`** (bootloader blob patched). Next boot: partition-table MD5 fail, then app XOR with **varying** calculated byte, stored still `0xcc`. `verify_flash` of the **app** was OK — it does not gate a patched bootloader. |
| 2 | Keep rewrite (`probe_keep_write.log`, no SHA-update line) | Same probe ELF **did boot**. `BOOT_GATE_KEEP.txt` ELF SHA256 prefix `5b23f25c6` = probe `image_info` (`5b23f25c6b9fcf09…`). Then Core 1 LoadProhibited on the first VP `show_leds()`. After that, the same XOR storm (`read 0xcc`). |

Restore later looped `Calculated 0xfa read 0x94` (`0x94` is the restore footer) until a full-chain rewrite with **`--flash_size keep`** + watchdog reset. Same class as row 1, on the **proven** image.

## Host image (not the bug)

`image_info_probe.txt` / `image_info_restore.txt` in this directory.

| | Probe (`293490b4`) | Restore (`d276fd68`) |
|--|--------------------|----------------------|
| Size | 691 568 B | 700 192 B |
| Header | DIO / 80 MHz / 16 MB | same |
| Checksum | `0xcc` valid | `0x94` valid |
| ELF SHA256 | `5b23f25c6b9f…` | `bc8fe4701745…` |
| Bootloader / partitions | **byte-identical** | **byte-identical** |
| ota_0 | `0x10000` len `0x640000` (6.25 MiB) | same; both apps fit |

Six segments, same classes: DROM `0x3c07_0020`, DRAM, IRAM `0x4037_4000`, IROM `0x4200_0020`, more IRAM, RTC `0x600f_e100` (28 B). Probe IRAM ends `0x4038_546c` — **no overlap** with bootloader IRAM `0x403c_8700`. Coredump partition is `0xff0000` / 64 KiB — **no overlap** with ota_0.

Varying calculated XOR with a **stable** stored `0xcc` is a **read-side** failure (MMU / patched bootloader / flash controller after a crash), not a static footer mismatch. A wrong image would fail with a **repeatable** calculated byte.

`invalid segment length 0x1999` (once in `BOOT_GATE.txt`) sits next to the probe’s first IRAM length `0x195c` — consistent with a flaky header read, not a linker length of `0x1999`.

## Why `INIT_LEDS: PASS` did not mean I2S was up

`K1_RMT_ALLOC_ON_VP_CORE_V1` makes `show_leds()` **return on Core 0**. `init_leds()` under `K1_LED_I2S_DIRECT_V1` allocates the wire buffer, calls `show_leds()` from setup (Core 0), then prints PASS anyway. Yves `initled` / `show` are lazy: first Core 1 `show_leds()`.

`BOOT_GATE_KEEP.txt` order:

1. `INIT_LEDS: PASS` (buffer only; Yves not started)
2. `INIT_SECONDARY_LEDS: PASS`
3. `RMT_ALLOC: first_show core=1`
4. truncated ` slots=160` (tail of `I2S_EMIT: init core=… slots=160` — `initled()` had returned far enough to print)
5. `Guru Meditation` Core 1, `EXCCAUSE=0x1c` (LoadProhibited), `EXCVADDR=0x8202851c` (windowed RA used as a load address; unwindowed `0x4202851c`), `PC=0x4203f7df`
6. core-dump re-enter, then XOR loop `read 0xcc`

The boot gate in `flash_and_gate.py` treating `INIT_LEDS: PASS` as success is a **false positive**. The script already required `I2S_EMIT: init core=1`; KEEP never delivered a full line of that, then paniced.

## What this does not close

- Yves / LCD_CAM `show()` on Core 1 is still a crash. Do not flash `k1_main_rpl_i2sled_probe` to “try keep again” without a new named GO **and** a driver/stack change.
- No T0H / clock tuning. The app either never stayed up (row 1) or died on first show (row 2).
- Production RMT look on `9087A500` is unchanged: `k1_main_rpl_im69d` @ `d276fd68`.

## Durable pin in this pack

`flash_and_gate.py` and `flash_plan.md` now use `--flash_size keep` (not `16MB`). That is the write recipe that booted the probe and that unbricked restore. It does not make Yves safe.
