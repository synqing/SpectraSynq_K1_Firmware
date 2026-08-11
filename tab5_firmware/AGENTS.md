# Tab5 firmware agent contract

This file applies to everything below `tab5_firmware/` and overrides generic K1
guidance where the target is the Tab5 ESP32-P4 dashboard.

## Read first

For any BLE/state, LVGL, display, typography, palette, animation, build, or flash
task, read:

1. `../docs/canon/TAB5_SESSION_FAILURES_AND_ENGINEERING_CANON_2026-08-11.md`
2. `../docs/receipts/tab5-hardening-20260811/G2_BEHAVIOURAL_HARDENING.md`
3. `.claude/skills/tab5-embedded-ui-motion-gate/SKILL.md` from the repository
   root when procedural UI motion is in scope.

## Hard stops

- Ask: **Can I be absolutely sure this is not busy work?** If the next action
  cannot change the product, falsify a live hypothesis, or prevent recurrence,
  stop.
- LVGL and confirmed-state mutation belong to loopTask only. Callbacks enqueue
  bounded records and return.
- Production display is full-frame direct RGB565 -> PPA -> hidden double DSI
  framebuffer -> VSYNC. No partial presentation and no RGB565 byte swap.
- Primary and Secondary palette previews consume one shared 2D coordinate/light
  field. No independent phases, integer widget translation, or hard-stop bands.
- No heap or `String` in callbacks, palette animation, or render hot paths.
- Never claim a perceptual adjective from source/tests alone. `fluid`, `organic`,
  `smooth`, `blended`, `tearing-free`, `best`, and `fixed` require current native
  sequence evidence plus eyes-on device confirmation.
- A Captain eyes-on rejection reopens the perceptual gate even when all host
  tests are green.

## Device identity

The authorised Tab5 target is ESP32-P4 MAC `30:ed:a0:e0:c1:a0`. Port names may
change. Enumerate, pass the port explicitly, and run:

```sh
scripts/flash_tab5_p4.sh --port /dev/cu.usbmodem12401 --verify-only
```

The session port was `usbmodem12401`; that observation never replaces the MAC
guard. Do not flash the C6, main K1, or another P4.

## Minimum proof

Routine local builds may use the existing core. Any source-closure or release
proof must use a unique explicit `PLATFORMIO_CORE_DIR` outside the shared global
cache; this session proved another project can replace that cache's framework
metadata while a Tab5 build is in progress.

```sh
cd /Users/spectrasynq/SpectraSynq_K1_Tab5_Hardening
python3 -m pytest tab5_firmware/tests -q
pio run -d tab5_firmware -e native_sdl
PLATFORMIO_CORE_DIR=/tmp/tab5_pio_core_<receipt-id> \
  ~/.platformio/penv/bin/pio run -d tab5_firmware -e tab5_p4
```

For motion changes also run the palette motion mutation gate and inspect a
continuous sequence on the named device. For display changes inspect page
transitions for stagger, tearing, colour corruption, and buffer reuse. Report
files changed, exact commands, tests/builds, visual/device evidence, blockers,
and the next physical truth.
