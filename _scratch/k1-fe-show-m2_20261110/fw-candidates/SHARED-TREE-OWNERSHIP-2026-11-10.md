---
abstract: "Who owns which uncommitted file in ~/SpectraSynq_K1_Firmware on 10 Nov 2026 ~17:20 AWST, when the FW lead (K1-FE-SHOW change requests, branch fe/k1-fe-show-fixes) and the Modernes C++ session were both writing the one checkout. Used to check that an FW-lead candidate commit contains only change-request files."
---

# Shared checkout ownership — 10 Nov 2026

Source: reply from the "MODERNES-CPP execution plan" session (cross-session message, ~17:20 AWST). It agreed not to commit, stash, reset or switch branches while the FW lead works. The FW lead runs headless and could not receive the collision warning (message held, undelivered).

## Modernes C++ session's files (NOT change-request work)
Firmware (`SPECTRASYNQ_K1_FIRMWARE/`):
- `visual/k1_look.h`, `visual/k1_look_file.h`, `visual/k1_colour_lab.cpp`, `visual/k1_lever2_emit.h`
- `visual/led_utilities.h` — **shared**. Modernes hunks only: `k1_fe_gx_prepare()` / `k1_b489_prepare_native()` use `const K1LookFrame look(look_slot)` / `look.apply(...)`; `run_transition_fade()` mode block calls `k1_mode_request_land()`. The FW lead's hunks: `apply_brightness`, `show_leds`, `K1_RTRACE_DUAL`.
- `persistence/k1_persisted_repair.h` (new), `persistence/bridge_fs.h`, `persistence/buttons.h`
- `control/k1_show_state.cpp`, `control/k1_effect_queue.cpp`, `control/k1_effect_queue.h`, `control/k1_control_facade.cpp`
- `director/k1_smart_director.cpp`
- `system/globals.h` (`mode_transition_queued` → `std::atomic<bool>`; `k1_mode_request_*` helpers), `system/system.h` (`check_settings`)
- `serial/serial_cmd_handlers.cpp` — `set_mode` body only (**possible overlap** with the change-request metadata fix)

Tests / harness:
- `tests/test_look_lifetime_native.py`, `tests/test_persisted_repair_native.py`, `tests/test_request_handoff_native.py` (new)
- `tests/test_colour_lab.py`, `tests/test_look_lib_static.py`
- `tests/golden/bridge_fs_config.golden.jsonl`, `tests/golden/serial_struct.golden.jsonl`, `tests/golden/MANIFEST.sha256` (two lines)
- `scripts/regression-harness/stubs/FS.h`, `LittleFS.h`, `esp_heap_caps.h` (new)
- `scripts/regression-harness/golden/oracle_smart_director.py`, `scripts/regression-harness/smart_director_replay.py`

Modernes says it does NOT touch: `serial_menu.cpp`, `k1_prsm*`, `k1_authored_source*`, effects, serial tables, `tools/esp_emulator`, `platformio.ini`.

## Open design difference (for the acceptance of change request 1)
Modernes Stage F wants an over-long text `:` line (> 127 chars) discarded through its CR/LF, executing nothing, with interactive control resuming at the next line. The FW lead's in-progress `k1_prsm_rx.cpp` instead treats it as entering the binary session (next command refused until `:prsm_exit`). Both execute nothing; the K1-FE-SHOW acceptance requires only that nothing executes and that the exit transition is defined. Modernes will apply its change on top after the FW lead commits, and must keep gates.py G1–G4 and the receiver acceptance green.

## Acceptance check on any FW-lead candidate commit
`/usr/bin/git show --stat <candidate>`: every file must be change-request scope. Any file in the Modernes list above (other than the FW lead's own hunks in `led_utilities.h` / `serial_cmd_handlers.cpp`, checked hunk by hunk) is a rejection finding.
