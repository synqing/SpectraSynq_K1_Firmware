# Arduino Workflows Reference

## Contents
- Build → Upload → Monitor
- Upload Guard Behaviour
- Serial Diagnostic Workflow
- Peripheral Bring-Up Checklist
- Regression Gate Sequence

---

## Build → Upload → Monitor

```bash
# 1. Build (default k1_hardware env)
pio run

# 2. Upload — triggers k1_upload_guard.py (verifies USB MAC + chip ID)
pio run --target upload

# 3. Monitor
pio device monitor  # 115200 baud, USB CDC
```

See the **platformio** skill for environment flags (`-e k1_hardware`, `-e k1_bench_reference`, etc.).

---

## Upload Guard Behaviour

`k1_upload_guard.py` runs as a PlatformIO pre-upload script. It:
1. Reads USB MAC and ESP chip ID
2. Compares against the K1 reference device table
3. Aborts upload if device identity does not match

**If upload is rejected:** verify the correct USB port is selected and the device is the K1 reference unit. Do not bypass the guard—it prevents flashing wrong firmware onto non-K1 hardware.

---

## Serial Diagnostic Workflow

```
1. Connect: pio device monitor
2. Trigger noise calibration: send 'c' (requires verbal silence — see .claude/CLAUDE.md)
3. Observe MabuTrace lines for audio pipeline health (trace_dev build only)
4. Check AGC gain scalar — should stabilise within ~2s of audio input
5. Verify beat confidence: look for confidence > 0.60 in serial output
```

For offline replay diagnostics, use the pytest harness rather than serial capture:

```bash
pytest tests/test_onset_beat_replay.py -v
```

See the **pytest** skill for harness patterns.

---

## Peripheral Bring-Up Checklist

Copy this checklist when adding a new peripheral under Arduino framework:

- [ ] Confirm PIO board target supports the peripheral (check `platformio.ini` `board_build.*`)
- [ ] Verify IDF component version (5.4.1) has the driver; check ESP-IDF changelog if porting from 2.x pattern
- [ ] Assign a dedicated core if the peripheral uses DMA or interrupts
- [ ] Guard any shared GPIO against D5/D6 conflict (see init order in `globals.cpp`)
- [ ] Add a smoke test to `tests/` that exercises the peripheral path in host-sim mode
- [ ] Run `pio run` clean build — watch for redefined symbol or linker errors from IDF component overlap
- [ ] Flash and confirm via serial monitor before committing

---

## Regression Gate Sequence

Run after any Arduino HAL or peripheral change:

```
1. pio run                          # clean firmware build
2. pytest tests/ -v                 # host regression (136 tests)
3. pio run --target upload          # flash to K1
4. pio device monitor               # eyes-on: beat confidence, AGC, LED output
5. Only commit when all 4 pass
```

**Iterate-until-pass:**
1. Make changes
2. `pio run` — fix compile errors
3. `pytest tests/ -v` — fix regressions
4. Flash + serial confirm — fix device-only issues
5. Repeat from step 2 until all gates green

For audio-pipeline changes, also run the replay harness:

```bash
pytest tests/test_onset_beat_replay.py -v --tb=short
```

Beat density-in-band target: ≥ 97% (established post forward-graft 2026-06-05). Do not ship if this regresses below 90%.