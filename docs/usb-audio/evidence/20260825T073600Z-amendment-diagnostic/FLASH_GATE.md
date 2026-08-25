# FLASH_GATE — K1 USB-audio diagnostic probe

**FLASH: DONE**

Date: 2026-08-25 07:36 AWST (`2026-08-24T23:36:48Z`)
Lane: `k1_usb_audio_mac_probe` on Main RPL only.
Repo: `feat/k1-usb-audio-input` HEAD `0136de678ddf084aa8c174bb590a052294e4e2bb`.
Firmware source / `platformio.ini`: clean. Other working-tree dirt left unstaged.

## Bootstrap

- `session-bootstrap.sh` ran. `repo-truth` FAIL is the expected branch mismatch
  (`feat/k1-usb-audio-input` vs active_branch `feat/k1-scheduling-generation-hardening`).
  Captain already authorised this diagnostic flash; no production env was used.

## Identity (before write)

| Field | Measured |
|---|---|
| Port at write | `/dev/cu.usbmodem112401` |
| Product | USB JTAG/serial debug unit (Espressif `303A:1001`) |
| USB serial | `B4:3A:45:A5:87:90` |
| esptool `read_mac` | `b4:3a:45:a5:87:90` |
| Chip | ESP32-S3 QFN56 rev v0.2, PSRAM 8 MB |
| Match 9087 | **yes** |
| Not flashed | F887, B489, Unit 2, `k1_hardware` |

`:build` on JTAG before write did not answer — the chip was already in ROM
(`rst:0x15 USB_UART_CHIP_RESET`, `boot:0x0 DOWNLOAD`). Identity was MAC, not the
port string.

## Image

| Field | Value |
|---|---|
| Path | `.pio-usb-audio/build/k1_usb_audio_mac_probe/firmware.factory.bin` |
| Size | 791424 B |
| SHA-256 | `fc5854a5604c5a541d2c82bb17a3651edbdecd835c54a4a41f011762e5c42a54` |
| Rebuild | no (named image present and hash-matched) |
| NVS erase | no |

`k1-flash-verified.sh` was **not** used: it rebuilds with the default PIO root
and calls `pio run --target upload`. Last successful 9087 USB-probe write was
esptool `write_flash 0x0` + `verify_flash`.

## Write + verify

```
esptool --chip esp32s3 --port /dev/cu.usbmodem112401 --baud 460800
  --before default_reset --after no_reset
  write_flash --flash_mode dio --flash_freq 80m --flash_size 16MB
  0x0 firmware.factory.bin
```

- Wrote 791424 bytes (452224 compressed) at `0x0` in 5.8 s.
- Write: **Hash of data verified.**
- `verify_flash --diff yes 0x0`: **verify OK (digest matched).**
- MAC re-read on every esptool connect: `b4:3a:45:a5:87:90`.

RTS `--after hard_reset` left the chip in ROM download. App boot required:

```
esptool --after watchdog_reset chip_id
```

Then TinyUSB enumerated (do not open JTAG with DTR asserted; that re-enters
download).

## After reboot

| Field | Value |
|---|---|
| CDC | `/dev/cu.usbmodem9087A5453AB41` |
| USB serial | `9087A5453AB4` |
| Product | `SpectraSynq K1 USB Audio` |
| Host audio | `TinyUSB UAC1` (restored to Multi-Output Device after score) |
| Live `:build` | `BUILD: version=40103 git=c1b53860 epoch=1787613527 env=k1_usb_audio_mac_probe` |

The factory SHA is the immutable `0136de67` image. The baked provenance hash is
still `c1b53860` (build epoch `1787613527` is new vs the 2026-08-24 probe).

## Serial score (DTR on TinyUSB CDC, 115200)

Host played official 12800 Hz mono S16 fixture (`afplay -t 16`). Rate seen:
**12800 only**. Silence windows under `K1_USB_FORCE_PRESENT_DIAGNOSTIC` were
not treated as a pass.

Steady play window (t≈3.24–18.50): `valid_stream=1`, frames assembled = enqueued
= consumed, Δconsumed 2010 / ~15.3 s ≈ **131–134 /s**, `frames_dropped_oldest=0`,
`queue_high_water=1`, `rate_mismatches=0`, `stream_generation=11`. Underflows
held at **5** for the whole play window (startup/stream-change residue; not
growing under tone). One extra underflow at stream stop.

`[USB-WF]` raw/follow/peak_scaled moved with the 110/440/1000 Hz sections
(raw 0 ↔ ~8192, peak_scaled 0 ↔ 1.000). **`loudness=BLOCKED`** — `K1_STM` is
not on this probe env. That is a probe defect, not a flash miss.

### Representative lines

```
BUILD: version=40103 git=c1b53860 epoch=1787613527 env=k1_usb_audio_mac_probe
[UAC] usb_started=1 suspended=0 speaker_enabled=1 valid_stream=1 rate=12800 channels=1 bits=16 host_mute=0 host_volume_db=-2 callback_count=6863 bytes_received=351230 samples_received=175615 frames_assembled=1828 frames_enqueued=1828 frames_consumed=1828 queue_depth=0 queue_high_water=1 frames_dropped_oldest=0 enqueue_failures=0 underflows=5 rate_mismatches=0 stream_generation=11 partial_bytes=38 stale_generation_drops=0 queue_age_p50_us=35 queue_age_p95_us=42 queue_age_p99_us=45 queue_age_max_us=1065 heap_free=172352 reset_reason=1
[UAC] usb_started=1 suspended=0 speaker_enabled=1 valid_stream=1 rate=12800 channels=1 bits=16 host_mute=0 host_volume_db=-2 callback_count=13396 bytes_received=685668 samples_received=342834 frames_assembled=3570 frames_enqueued=3570 frames_consumed=3570 queue_depth=0 queue_high_water=1 frames_dropped_oldest=0 enqueue_failures=0 underflows=5 rate_mismatches=0 stream_generation=11 partial_bytes=12 stale_generation_drops=0 queue_age_p50_us=35 queue_age_p95_us=42 queue_age_p99_us=45 queue_age_max_us=1065 heap_free=172352 reset_reason=1
[USB-WF] raw=8191 follow=8192 peak_scaled=1.000 ssl=0 loudness=BLOCKED
[USB-WF] raw=0 follow=6379 peak_scaled=0.000 ssl=0 loudness=BLOCKED
[USB-WF] raw=8192 follow=8192 peak_scaled=1.000 ssl=0 loudness=BLOCKED
```

Full tap: `cdc_score.txt`. Summary: `score_summary.json`.

## Registry

Updated Main RPL deployed-state in `docs/hardware/device-build-registry.md`
(working tree only; not committed). Product restore remains
`k1_main_rpl_im69d` @ `b625e89a`.

## Captain close (2026-08-25)

```text
K1_USB_AUDIO_DIAGNOSTIC = PASS
DIAGNOSTIC_FINISHED     = YES
SECOND_K1_STM_PROBE     = NO
startup_underflows=5
steady_state_underflows=0
loudness=BLOCKED          N/A — K1_STM not compiled
USB_SHARED_FINALISER_UNIFICATION = OPEN
```

Do not rebuild this probe for `K1_STM` or a fresher `:build` banner.
Authoritative identity is the factory SHA, not the stale `git=c1b53860` string.
Full disposition: `RESULT.md`.

## Not done

- No `start_noise_cal`
- No plate/LED eyes
- No push
- No `platformio.ini` env behaviour change
- No sibling worktree
