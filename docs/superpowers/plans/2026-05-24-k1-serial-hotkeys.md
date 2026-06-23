# K1 Serial Hotkeys Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immediate serial keystrokes for fast K1 hardware tuning while preserving the existing typed serial menu.

**Architecture:** Keep the feature contained in `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`. Add an explicit hotkey allowlist, a single hotkey dispatcher, compact help/status output, a `:` command prefix for slow typed commands, and bounded adjustment helpers that mutate only the same runtime/config variables already exposed by typed commands or encoder controls.

**Tech Stack:** Arduino ESP32-S3, PlatformIO `k1_hardware`, USB CDC serial, Python static regression tests.

---

### Task 1: Static Hotkey Contract Test

**Files:**
- Create: `tests/test_serial_hotkeys_static.py`
- Modify: none

- [x] **Step 1: Write the failing test**

Create a Python unittest that requires the new hotkey helper names, checks the proposed key surface, and blocks hazardous commands from the immediate dispatcher.

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_serial_hotkeys_static.py`

Expected: FAIL because `serial_hotkey_is_immediate`, `serial_handle_hotkey`, and the proposed help/status strings do not exist yet.

### Task 2: Serial Hotkey Layer

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`
- Test: `tests/test_serial_hotkeys_static.py`

- [x] **Step 1: Implement helpers**

Add bounded helper functions above `parse_command()`:
- `serial_hotkey_is_immediate(char key)`
- `serial_handle_hotkey(char key)`
- compact status/help printers
- float/mode/palette adjustment helpers

- [x] **Step 2: Preserve typed commands**

Update `check_serial()` so normal serial input is hotkey-first and never reaches `parse_command()`. If the first byte is `:`, enter command mode and buffer the following bytes until CR/LF so slow typed commands such as `:dump` and `:vp_status` remain available without being stolen by hotkeys.

- [x] **Step 3: Verify static contract**

Run: `python3 -m unittest tests/test_serial_hotkeys_static.py`

Expected: PASS.

### Task 3: Firmware Build Gate

**Files:**
- Modify: none

- [x] **Step 1: Build active K1 firmware**

Run: `pio run -e k1_hardware`

Expected: SUCCESS. This is compile-only proof unless the binary is uploaded and serial behaviour is observed on the K1.

### Task 4: Optional Hardware Runtime Smoke

**Files:**
- Modify: none

- [x] **Step 1: Upload to the intended K1 only**

Run: `pio run -e k1_hardware -t upload`

Expected: Upload succeeds to the intended K1 target. Do not target the protected S2 content-capture unit.

- [x] **Step 2: Serial smoke**

Representative runtime smoke performed on `/dev/tty.usbmodem1101`: verified `h` help, `;` status, `]`/`[` mode step and restore, `i`/`I` photons adjustment and restore, Space target-channel toggle and restore, `f` stop streams, and `:vp_status` legacy parser access. Noise calibration uses a two-keystroke safety gate: `N` arms calibration with a silence warning, then `Y` confirms within 5 seconds and queues the existing calibration path.
