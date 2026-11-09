---
abstract: "Safety change request to the FW lead: bytes of a malformed or truncated PRSM frame fall through to the single-byte hotkey handler, which includes noise-calibration arm/confirm (N, Y), preset-slot saves (! to )), show save (S) and delayed config saves. Smallest fix: drop would-be hotkey bytes while an authored stream is live or a frame was just broken. About 6 lines in serial_menu.cpp. Bench rule until fixed: never send a bad-magic frame that contains hotkey bytes."
---

# CR-A3 — PRSM bytes can reach persisting and calibration hotkeys

Raised by Lane A, K1-FE-SHOW-M1 Rev 2, 9 November 2026. Source basis: HEAD `407fdf6f` (identical in the working tree for every file cited).

## Mechanism (FACT)

`check_serial()` (`serial/serial_menu.cpp:4121–4190`), outside `:` command mode, offers every byte to `k1_prsm_scanner_push()` first; anything that returns `K1_PRSM_SCAN_NONE` goes to `serial_hotkey_is_immediate()` / `serial_handle_hotkey()` (`:4155–4178`). The scanner (`audio/k1_prsm.cpp:50–84`) returns NONE for any byte while hunting for `P`, including the byte that breaks a partial magic (`:63–67`, it re-hunts on that byte). So:

1. **Bad magic** (e.g. `PRSX…`): `P`,`R`,`S` are consumed, then the breaking byte and all 30 following bytes are seen while hunting → each one that is a hotkey fires.
2. **Truncated frame** (host write aborted part-way, or USB receive overflow): the scanner keeps its partial fill; the next frame's first bytes complete the old frame, which then parses as a valid frame with garbage values (`:73–83`), and the rest of the new frame falls through to hotkeys. PRISM.studio's `writeCdcPort` can throw after a partial write (`PRISM.studio/src/cdc.js:131–142`). The USB-Serial-JTAG receive queue is 256 bytes and the interrupt drops bytes when it is full (Arduino-ESP32 3.2.0 `cores/esp32/HWCDC.cpp:123`, `:309`); at 4,080 B/s that is about 63 ms of main-loop stall.
3. Valid frames and bad-version or bad-hz frames are safe: all 34 bytes are consumed (`k1_prsm.cpp:73–83`; hz is checked after parse in `k1_authored_map_prim8`).

Immediate hotkeys in the FE builds (`serial/serial_menu.cpp:1730–1815`, with `K1_LOOK_LIB_V1` / `K1_LOOK_LIB_WS2812_V1` and `K1_VIVID_PRECOMP_V1` on, `ENABLE_MOTION_PROBE` off): `g G u y m - = _ +` space `h ; N Y [ ] 0–9 ! @ # $ % ^ & * ( ) \ U i I o O p P j J k K l L q Q w W e E r R t T , . / a s S d f z Z v`. Consequences (handler `:1998–2290`):
- `N` arms and `Y` confirms noise calibration (`:2014–2019`, `control/k1_noise_cal_arm.cpp:32–43`) — a calibration that assumes silence, run during music. Captain rule: calibration is never auto-fired.
- `!`…`)` save preset slots (`:2078–2108`); `S` saves show state for next boot (`:2231–2246`); `q Q w W` call `save_config_delayed()` (`:2154–2172`); digits load preset slots and the primary commit queues a delayed config save (`control/k1_effect_queue.cpp:137–141`).

So A3's "PRSM frames never touch persistence" holds only for well-formed frames.

## Requested change (smallest)

`serial/serial_menu.cpp`, `check_serial()`, at the hotkey branch (`:4176`):

```
const bool prsm_guard = k1_authored_suppresses_live_update() || prsm_recent_break;
if (!prsm_guard && serial_hotkey_is_immediate(char(byte))) serial_handle_hotkey(char(byte));
```

with `prsm_recent_break` a static set when the scanner returns `K1_PRSM_SCAN_FRAME_BAD` or when a byte breaks a partial magic (scanner fill > 0 before the push and 0 after), and cleared when the next valid frame is parsed or after 100 ms without PRSM bytes. `:` commands are unaffected. Count dropped bytes for CR-A8. Estimated 6–8 lines. Optional hardening (larger, FW lead's call): `USBSerial.setRxBufferSize(1024)` before `begin()` in `system/system.h:194–201`.

## Bench rule until the CR lands (Lane C / Lane D)

- Rejected-input tests use **bad hz** (e.g. hz=20 or 250) and **bad version** (byte 4 ≠ 1): both are fully consumed and safe.
- A **bad-magic** test frame must be built from bytes outside the hotkey set and not `:` (0x3A), checked byte by byte before sending; bytes 0x00–0x1F and 0x80–0xFF are not hotkeys in these builds (CR and LF are ignored).
- The host writes each 34-byte frame in one write and never abandons a frame part-way; on stop or seek, finish the current frame first.
- After any PRSM session, read `:dump` and compare against the pre-session settings (the 45-field comparison already used in `_scratch/s3-repair-20261105/followup/`).

Changelog
- 2026-11-09 Lane A: created.
