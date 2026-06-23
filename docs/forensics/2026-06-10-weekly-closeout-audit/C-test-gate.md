---
abstract: "2026-06-10 host gate audit: 308 collected, 4 FAILED, 300 passed, 4 skipped. Gate is RED. Last-week feature tests all individually PASS. Failures are in boot_intro_static, rate_consistency (numpy missing), and vpml_motion_lab_static (signature mismatch)."
---

# C-test-gate: Host Gate Inventory — 2026-06-10

## Run Environment

- **pytest binary:** `/opt/homebrew/bin/pytest` (Python 3.11)
- **Working directory:** `/Users/spectrasynq/SensoryBridge-main 9`
- **Note:** `.venv/bin/python` does NOT have pytest installed — homebrew Python used.

## Full Suite Result

Command: `pytest tests/ -q --ignore=tests/test_k1_ws_registry_codegen.py`

```
4 failed, 300 passed, 4 skipped in 13.97s
```

**Collection note:** `tests/test_k1_ws_registry_codegen.py` blocked collection entirely (`ModuleNotFoundError: No module named 'yaml'`). Excluded with `--ignore` to get real gate numbers. 308 tests collected (minus yaml-blocked file).

Total collected (with exclusion): **308 tests**

## Gate: RED — 4 failures

### FAIL 1: `tests/test_boot_intro_static.py::TestBootIntroStatic::test_intro_has_warm_centre_origin_bounce`
- **Cause:** `assertIn("secondary_radius…", ...)` — test expects specific secondary_radius string not found in current `led_utilities.h` boot intro region.
- **Category:** Firmware / VPML boot intro static assertion — likely stale test after VPML intro bounce refactor.

### FAIL 2 & 3: `tests/test_rate_consistency.py::RateConsistencyTest::test_acf_ceiling_sweep_rates_match_firmware` and `test_novelty_from_wav_frame_rate_matches_firmware`
- **Cause:** `ModuleNotFoundError: No module named 'numpy'` — `scripts/regression-harness/novelty_from_wav.py` imports numpy which is not in the homebrew Python 3.11 environment.
- **Category:** Missing dependency in test runtime (numpy absent from current Python).

### FAIL 4: `tests/test_vp_motion_lab_static.py::VPMotionLabStaticTest::test_vpml_header_is_non_shippable_and_render_safe`
- **Cause:** Test asserts `vp_intro_render_frame(vpml_frame, VPML_INTRO_BOUNCE_FRAMES)` but the firmware now uses `vp_intro_render_frame(vpml_frame, frame_count)` (dynamic frame count via `vpml_frame_count_for_program`). Stale hardcoded constant in test assertion.
- **Category:** Test assertion stale after VPML frame-count refactor (VPML Motion Lab work from last-week commits).

## Collection-Blocking Error

`tests/test_k1_ws_registry_codegen.py`: `ModuleNotFoundError: No module named 'yaml'`
- Blocks the entire test suite collection if not excluded.
- Must be resolved (install `pyyaml` or add to venv) to run the canonical `pytest tests/ -q`.

## Per-Feature Test Results (Last-Week Features)

| Feature File | Test File | Individual Result |
|---|---|---|
| `sb-tab5-wireless-controller/src/main.cpp` | `test_sb_tab5_wireless_controller_static.py` | PASS (21/21) |
| `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp/.h` | `test_sb_tab5_wireless_controller_static.py` | PASS (covered at lines 57,63-64,169-170,209-210 etc.) |
| `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp` | `test_sb_tab5_wireless_controller_static.py` | PASS (21/21) |
| `tools/tab5_k1_dashboard_harness.py` | `test_tab5_dashboard_harness.py` | PASS (9/9) |
| `scripts/regression-harness/vpml_live_runner.py` | `test_vpml_live_runner.py` | PASS (5/5) |
| `scripts/regression-harness/vpml_run_console.py` | `test_vpml_run_console.py` | PASS (6/6) |
| `scripts/regression-harness/vpml_run_console.py` (server) | `test_vpml_run_console_server.py` + `_smoke.py` | PASS (7/7) |
| `scripts/platformio/k1_upload_guard.py` | `test_k1_upload_guard.py` | PASS (5/5) |
| `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` | `test_vp_motion_lab_static.py`, `test_boot_intro_static.py`, `test_dev_instrumentation_boundary.py` | FAIL (2 of 3 test files fail on stale assertions post-VPML refactor) |

## Coverage Gap Analysis

### Changed modules WITH host tests:
- `sb-tab5-wireless-controller/src/main.cpp` — covered by `test_sb_tab5_wireless_controller_static.py`
- `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp/.h` — covered (multiple test functions in static test)
- `sb-tab5-wireless-controller/src/harness/Tab5SerialHarness.cpp` — covered
- `scripts/platformio/k1_upload_guard.py` — covered by `test_k1_upload_guard.py`
- `scripts/regression-harness/vpml_live_runner.py` — covered by `test_vpml_live_runner.py`
- `scripts/regression-harness/vpml_run_console.py` — covered by `test_vpml_run_console.py`
- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` — covered by `test_boot_intro_static.py`, `test_vp_motion_lab_static.py`, `test_dev_instrumentation_boundary.py` (but 2 are currently failing)

### Changed modules with NO host test:
- **NONE identified** — all last-week changed modules have corresponding test coverage.

### Stale test assertions (gate RED contributors):
- `test_boot_intro_static.py` — asserts old secondary_radius string form (stale after led_utilities.h edit)
- `test_vp_motion_lab_static.py` — asserts `VPML_INTRO_BOUNCE_FRAMES` constant (stale after vpml frame_count refactor)
- `test_rate_consistency.py` — runtime dependency gap (numpy not installed in active Python env)

## Firmware Build Gate (NOT RUN)

Per commit-gate doctrine (`scripts/hooks/pre-commit`, tiered gate), firmware build verification requires:
```
pytest tests/ && pio run -e k1_hardware
```
`pio run` was NOT executed — requires full ESP32 toolchain (pioarduino/xtensa) not available in this audit scope.

**Tab5 is a SEPARATE PlatformIO project:** `sb-tab5-wireless-controller/platformio.ini` exists as its own independent project (`[env:tab5]`, `platform = pioarduino/platform-espressif32`, `board = esp32-p4-evboard`). It is NOT part of the `k1_hardware` build. Per pre-commit gate, Tab5 changes trigger `pytest + run_tab5_build` (separate tier from K1 firmware tier).

## Pre-Commit Gate Tiers (from scripts/hooks/pre-commit)

```
docs / md / instructions / skills    → no build, no test  (instant)
tests/**.py + scripts/regression-harness/**.py → pytest only
sb-tab5-wireless-controller/** + Tab5 harness  → pytest + tab5 build
SPECTRASYNQ_K1_FIRMWARE/** + platformio.ini    → pytest + k1 build
any tier                                        → binary / oversize guard
wip/* branch                                    → build+test SKIPPED
```

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-10 | agent:claude-code (SSA) | Created — host gate audit for closeout evidence |
