# VPAB Framed Transport Ready

Date: 2026-06-07
Device: K1 1401, chip `F887A500`, USB MAC `B4:3A:45:A5:87:F8`
Build used for device proof: `k1_hardware_harness`

## Scope

This closes the failed VMEWT evidence-transport lane by replacing render-path CSV survivor rows with a deferred, framed VPAB drain path.

The production firmware surface remains clean: the framed stream is available only in diagnostic capture builds, and the production `k1_hardware` ELF contains no `K1DF`, `vpab_capture_dump_frames`, or `DIAG_FRAME` symbols/strings.

## Implementation

- `SPECTRASYNQ_K1_FIRMWARE/diag/vpab_capture.cpp`
  - Adds `vpab_capture_dump_frames()`.
  - Drains a stopped diagnostic pool only.
  - Emits `K1DF_BEGIN`, `K1DFR`, `K1DFC`, and `K1DF_END`.
  - Includes sequence, payload length, record CRC32, chunk CRC32, diagnostic dropped/corrupt/overflow counters, and fixed 96-byte chunks.
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h`
  - Adds `:vpab=frames` and alias `:vpab=dump_frames`.
- `scripts/regression-harness/vpab_frame_gate.py`
  - Fails closed on malformed rows, fragments, unknown kinds, sequence gaps, chunk mismatch, CRC mismatch, dropped/corrupt/overflow counters, and missing mode/channel/kind coverage.
- `scripts/regression-harness/vpab_frame_capture.py`
  - Captures from hardware using colon-framed runtime commands only.
  - Verifies chip ID before device-write commands.
  - Does not send calibration, erase, factory reset, restore default, or noise-cal commands.

## Build And Test Evidence

- `python3 -B -m py_compile scripts/regression-harness/vpab_frame_gate.py scripts/regression-harness/vpab_frame_capture.py` PASS
- `python3 -B -m unittest tests.test_vpab_frame_gate` PASS, 9 tests
- `PYTHONPATH=tests python3 -B -m unittest tests.test_diag_capture_static tests.test_dev_instrumentation_boundary tests.test_serial_hotkeys_static` PASS, 21 tests
- `pio run -e k1_hardware` PASS
- `pio run -e k1_hardware_harness` PASS
- `pio run -e k1_hardware_trace_dev` PASS
- Production leak check on `k1_hardware` ELF: PASS, no `K1DF`, `vpab_capture_dump_frames`, or `DIAG_FRAME` symbols/strings

Full host unittest discovery was also run and remains red on unrelated existing SB_ONSET_V2 replay tests. This VME transport lane does not touch audio/onset/semantic-state source or replay fixtures.

## Hardware Evidence

First controlled smoke at `every=180` failed closed because the diagnostic pool overflowed. This is retained as a useful negative-control record:

- Raw log: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-smoke.raw.log`
- Framed log: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-smoke.frames.log`
- Gate summary: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-smoke.frame-gate.json`
- Result: FAIL
- Records: 64
- Issues: 0
- Failures: 4
- Diagnostic counters: dropped `24`, corrupt `0`, overflowed `1`

Second controlled capture at `every=360` passed the fail-closed gate:

- Raw log: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-transport-pass.raw.log`
- Framed log: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-transport-pass.frames.log`
- Gate summary: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-transport-pass.frame-gate.json`
- Result: PASS
- Records: 44
- Chunks: 176
- Issues: 0
- Failures: 0
- Diagnostic counters: dropped `0`, corrupt `0`, overflowed `0`
- Coverage: mode `18`, primary and secondary, `vpab_metrics` and `vpab_bytes`

Captain live-music capture also passed against the same fail-closed gate:

- Raw log: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.raw.log`
- Framed log: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.frames.log`
- Gate summary: `docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.frame-gate.json`
- Result: PASS
- Records: 44
- Chunks: 176
- Issues: 0
- Failures: 0
- Diagnostic counters: dropped `0`, corrupt `0`, overflowed `0`
- Coverage: mode `18`, primary and secondary, `vpab_metrics` and `vpab_bytes`

## Ready Command

For another real music/audio proof run on the already-flashed harness build:

```bash
python3 scripts/regression-harness/vpab_frame_capture.py \
  --port /dev/tty.usbmodem1401 \
  --expect-chip F887A500 \
  --seconds 20 \
  --every 360 \
  --primary-mode 18 \
  --secondary-mode 18 \
  --capture-mode both \
  --prefix 2026-06-07-vpab-frame-mode18-1401-music
```

Acceptance is binary: `result=PASS`, `issues=0`, `failures=0`, dropped/corrupt/overflowed all `0`, and coverage includes mode `18`, primary, secondary, `vpab_metrics`, and `vpab_bytes`.
