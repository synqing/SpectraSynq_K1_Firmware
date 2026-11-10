# Lane B byte-safety oracle re-pointed at FE release head 8b202f46

Date: 2026-11-10. Subject: the differential oracle written against firmware `407fdf6f` (see `B-P1-contract.md`, "Differential oracle" and "USB packet-loss exposure"), re-run unchanged against `8b202f46ac6fa612b914ea54cbf773e31be96531` (lane `lane/k1-fe-release`, K1-FE-Gx, `fe-1.0.0-rc2`).

## Verdict

**No verdict differs from 407fdf6f.** 163 tests pass, both show streams are bench-eligible with guard 30, the `bad_magic` leak counts are identical, and the loss-exposure counts match the 407fdf6f results exactly (full JSON equality). The result is expected rather than lucky: the four PRSM source files are byte-identical, and `check_serial`, `serial_hotkey_is_immediate` and `serial_handle_hotkey` are text-identical (proof below). The receiver-isolation fix can therefore be judged against this oracle with the same meaning the oracle had at 407fdf6f.

## What was changed in lane-b (nothing else was touched)

- Created `oracle/fw_8b202f46/` (four firmware files, `SHA256SUMS`, hotkey excerpt lines 1730-1800). Layout identical to `oracle/fw_407fdf6f/`. `SHA256SUMS` is byte-identical to the 407fdf6f one (`diff` clean, `shasum -c` OK).
- Selector, two environment variables, defaults unchanged (a run with neither set behaves exactly as before):
  - `LANE_B_FW` (default `fw_407fdf6f`): `test_validate_prim8_stream.py` line 30, `audit_prsm_bytes.py` line 45 (plus `import os` in each).
  - `LANE_B_RAW` (default `raw`): `test_validate_prim8_stream.py` line 28. Needed because the suite rewrites `raw/oracle_c_output.json`, `raw/device_leak_report.json` and `raw/a02_timebase.json`; without it a run against 8b202f46 would overwrite the 407fdf6f evidence. 8b202f46 evidence is in `raw_8b202f46/`.
- Originals of the two edited scripts were saved in the session scratchpad before editing. `fw_407fdf6f/`, `fixtures/`, `prim8_stream.py`, `validate_prim8_stream.py`, `raw/` were not modified. No git write command was run; no device or serial port was opened.

## Task 2: snapshot files at 8b202f46 vs 407fdf6f

Blob ids from `/usr/bin/git rev-parse <commit>:SPECTRASYNQ_K1_FIRMWARE/<path>`.

| File | Snapshotted | Blob 407fdf6f | Blob 8b202f46 | Result |
|---|---|---|---|---|
| `audio/k1_prsm.cpp` | yes | 081dbeb4b9 | 081dbeb4b9 | identical blob |
| `audio/k1_prsm.h` | yes | 36ef874bf1 | 36ef874bf1 | identical blob |
| `audio/k1_authored_source.cpp` | yes | 03bb92ef8f | 03bb92ef8f | identical blob |
| `audio/k1_authored_source.h` | yes | b7e65556c5 | b7e65556c5 | identical blob |
| `serial/serial_menu.cpp` (excerpt 1730-1800 only) | yes | e99b8fb4ee | bd6c65b68a | CHANGED, but only inside `parse_command` (below); excerpt byte-identical (`cmp`) |
| `serial/serial_menu.h` | no | b3e46c2e96 | b3e46c2e96 | identical blob |
| `serial/serial_typed_cmd_table.def` | no | 1036d29e3c | 1036d29e3c | identical blob |
| `serial/serial_cmd_table.def` | no | 7d13ad05ee | 7d13ad05ee | identical blob |
| `control/k1_noise_cal_arm.{cpp,h}` | no | ad50268701 / ec69d93939 | ad50268701 / ec69d93939 | identical blobs |
| `serial/serial_cmd_handlers.cpp` | no | ea3ad9f57a | b99d1f16a8 | CHANGED (silence setters; set_mode body shifted +100 lines) |
| `serial/serial_typed_dispatch.cpp` | no | bb15f84530 | 9ea4e37884 | CHANGED (silence setters only) |
| `serial/serial_parse_helpers.{cpp,h}` | no | 71910f030b / 9a6aefc73e | 0c537e6c43 / 3f585ae5d6 | CHANGED (adds `vp_parse_float`, `vp_parse_u32`) |
| `calibration/noise_cal.h` | no | fe6561e5b9 | 38dbe64545 | CHANGED (see "Noise calibration" below) |
| `visual/led_utilities.h` | no | 1fc5c86419 | 1239be7f84 | CHANGED (Gx LED power; noise-cal trigger hand-off) |

The `fw_8b202f46` copies are also `cmp`-identical to the `fw_407fdf6f` copies, so the compiled oracle binary inputs are the same. The audit helper names its cached binary by a hash of the sources: `laneb_byte_audit_658dc988df246ef7` is the same name for both snapshots.

## Task 3: serial_menu.cpp, check_serial and the hotkey set

`/usr/bin/git diff -U0 407fdf6f 8b202f46 -- SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp` has nine hunks, all between old line 2963 and old line 3712, all inside `parse_command` (starts line 2876 in both; ends 4122 old / 4152 new). The hunks are:

1. `command_type[32]` and `command_data[94]` copy loops now stop one byte short (`sizeof(...) - 1`), so the terminator survives a 127-byte line.
2. `silence_enter`, `silence_exit`, `silence_dwell`, `silence_rms_enter`, `silence_rms_exit` now validate with `vp_parse_float` / `vp_parse_u32` and call `bad_command()` on rejection instead of `atof`/`atol`.

No command was added or removed: the `strcmp(command_type, ...)` name set is identical in `serial_menu.cpp`, `serial_cmd_handlers.cpp` and `serial_typed_dispatch.cpp`, and both `.def` tables are identical blobs. `analyze_loss.py` considers 231 command names at both commits.

Byte-level proof that the demux and hotkey code are unchanged (scratch copies via `/usr/bin/git show`, compared with `cmp`):

- Old lines 1-2963 == new lines 1-2963: IDENTICAL. This covers `serial_hotkey_is_immediate` (line 1730, unchanged position), `serial_handle_hotkey` and the hotkey helpers (about 1998-2260, unchanged position).
- Old lines 3713-4690 == new lines 3743-4720: IDENTICAL (shifted by exactly +30). This covers `check_serial`: **407fdf6f 4123-4214, 8b202f46 4153-4244**, including the PRSM scanner-first demux (`k1_prsm_scanner_push`, new 4186-4187), the `:` command-mode entry (new 4195), CR/LF skip (4202), the immediate-hotkey dispatch (`serial_hotkey_is_immediate` then `serial_handle_hotkey`, 4206-4207), and the command-line terminator and 127-byte overflow (4213-4234). The `K1_LOOK_LIB_V1` `:look_load` branch at the top of `check_serial` (4169) is also in the identical region.

Hotkey set: `case '...'` labels extracted from `serial_hotkey_is_immediate` at 8b202f46 (lines 1730-1980) against `oracle/py_device_model.py` `IMMEDIATE_HOTKEYS | CONDITIONAL_HOTKEYS`: every modelled key is present in the source; the only source keys not in the model are `b c n x`, which are inside `#ifdef ENABLE_MOTION_PROBE` (lines 1814-1824). `ENABLE_MOTION_PROBE` is defined only in the motion-probe env (`platformio.ini:1561`), not in `k1_fe`. This gap is pre-existing (the function text is identical at 407fdf6f) and not a regression. `z Z v` are build-conditional; `k1_fe` inherits `K1_LOOK_LIB_V1` (`platformio.ini:314`) and `K1_VIVID_PRECOMP_V1` (`:157`), and the audit already counts them as actionable.

Competing serial readers: a scan of every added and removed line in `SPECTRASYNQ_K1_FIRMWARE/` between the commits finds no `USBSerial.read/available/peek`, no `check_serial`, no `k1_prsm` change, and no HWCDC or RX-buffer configuration. The only `.ino` change is one line, `service_noise_cal_start_request();` at line 983. `platformio.ini` changes for `k1_fe` are a comment rewrite and the added `-DK1_FE_BOARD_GX`.

`set_mode` persistence flag (change request "metadata", rev 2):
- `serial/serial_typed_cmd_table.def:141` at 8b202f46 is `SERIAL_TYPED_CMD("set_mode", serial_typed_wrap_mode, SC_TYPED_ONLY, 0)`. Flag is still `0` (not `CMD_PERSISTS`). The file is an identical blob to 407fdf6f; line 142 is `secondary_mode`, also flag `0`.
- The handler is `serial_cmd_dispatch_mode` (`serial_cmd_handlers.cpp:1719` at 8b202f46, 1619 at 407fdf6f). The `set_mode` branch starts at **1723** (407fdf6f: 1623) and calls `save_config_delayed();` at **1740** (407fdf6f: 1640). The change request's `:1638` does not match either commit (1640 at 407fdf6f); the construct is the same, the number is stale by two lines. `serial_typed_wrap_mode` is defined at `serial_typed_dispatch.cpp:138` (both commits).
- So the discrepancy the change request describes still exists at 8b202f46: the table says "does not persist", the handler schedules a config save.

Noise calibration (affects the meaning of the `CAL_QUEUED` class, not its count): the arm and confirm path (`control/k1_noise_cal_arm.cpp`, `serial_menu.cpp:1359-1362`) is identical. What changed is the consumer. At 407fdf6f the render task's `noise_transition_queued` handler (`led_utilities.h:2104`) called `start_noise_cal()` directly. At 8b202f46 it clears `ui_mask`, then calls `request_noise_cal_start()` (`led_utilities.h:2177`), and `loop()` runs `service_noise_cal_start_request()` (`.ino:983`) between hops, which calls `start_noise_cal()`. A leaked `N` then `Y` within 5 s still ends in a started calibration, so `CAL_QUEUED` stays a correct "critical" class; only the thread that starts it moved to core 0.

## Task 4: results

All runs: `LANE_B_FW=fw_8b202f46`, `TMPDIR` pointed at a fresh scratch directory (the test fixtures compiled the oracle there from the 8b202f46 snapshot; the audit CLI then reused that binary, which carries the same source-hash name as the 407fdf6f one). Evidence is in `raw_8b202f46/`.

| Check | 407fdf6f | 8b202f46 | Same? |
|---|---|---|---|
| Full lane-b pytest suite | 163 passed, exit 0 (`raw/pytest_run3.txt`) | **163 passed, exit 0**, 9.34 s (`raw_8b202f46/pytest_run.txt`) | yes |
| Differential oracle JSON output (28 fixtures) | `raw/oracle_c_output.json` | `raw_8b202f46/oracle_c_output.json` | `cmp` identical |
| Device leak report (28 fixtures) | `raw/device_leak_report.json` | `raw_8b202f46/device_leak_report.json` | `cmp` identical |
| A02 timebase | `raw/a02_timebase.json` | `raw_8b202f46/a02_timebase.json` | `cmp` identical |
| `bad_magic` oracle demux leak (from the identical report) | 87 leaked bytes, `N` x6, `)`, 5 garbage commands, 18 valid frames lost (contract table) | same file contents | yes |
| `bad_magic` byte audit, no guard | exit 1; hotkeys 26, `:` entries 6, swallowed 550, executed 5, frames 5/24 | **exit 1**; hotkeys 26, `:` entries 6, swallowed 550, executed 5, frames 5/24 (`raw_8b202f46/audit_bad_magic_run.txt`) | yes |
| Byte audit `loreen_post_edit_120hz.prsm`, `--guard 30` | not run at 407fdf6f (stream is new) | **exit 0** BENCH-ELIGIBLE, frames 26870/26870, hotkeys 0, `:` entries 0, swallowed 0, executed 0, preamble 64 B | n/a (same binary inputs) |
| Byte audit `loreen_75_155_120hz_v2.prsm`, `--guard 30` | not run at 407fdf6f (stream is new) | **exit 0** BENCH-ELIGIBLE, frames 9600/9600, hotkeys 0, `:` entries 0, swallowed 0, executed 0, preamble 64 B | n/a |
| Loss exposure, bench stream `loreen_75_155_120hz.prsm` (sha256 `ea4b8f45...55af`, unchanged), guard 0 | 326,366 events; 287,970 dirty; CAL_QUEUED 110; PERSIST 178,135; command mode entered 8,476; commands executed 30 (`h` x24, `H` x6); 8,811 bad commands; garbage frame accepted 278,371 | identical: full JSON equal (`raw_8b202f46/loss_exposure_cemu_guard0.json` vs `raw/loss_exposure_cemu_guard0.json`) | yes |
| Loss exposure, bench stream, guard 30 | 614,336 events; 249,394 dirty; all `garbage_frame_accepted`; 0 hotkey bytes; 0 command-mode entries; 0 commands | identical: full JSON equal | yes |
| Loss exposure guard 30, `loreen_post_edit_120hz.prsm` (new, 8b202f46 only) | n/a | 1,719,616 events; 685,574 dirty, all `garbage_frame_accepted`; 0 hotkey bytes; 0 commands; 0 unresolved (`raw_8b202f46/loss_exposure_post_edit_guard30.json`) | n/a |
| Loss exposure guard 30, `loreen_75_155_120hz_v2.prsm` (new, 8b202f46 only) | n/a | 614,336 events; 249,394 dirty, all `garbage_frame_accepted`; 0 hotkey bytes; 0 commands; 0 unresolved (`raw_8b202f46/loss_exposure_v2_guard30.json`) | n/a |
| Induction step (all fills x all prefixes, guard 30) | passed in 407fdf6f suite | passed inside the 163 (`test_guard_induction_step_all_fills_all_prefixes`) | yes |

Stream identities: post-edit sha256 `116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3`, v2 sha256 `eafb72aecbccedba880364930898420a727d284dbe21182f18c6bff3f1258fdd`. Loss exposure took about 2 s per run, so it was re-run in full.

Path note: the brief's two relative paths resolve from different bases. `../k1-fe-show-m2_20261110/m2-compose/...` resolves from `_scratch/k1-fe-show-m1_20261109/` (to `_scratch/k1-fe-show-m2_20261110/`). `../lane-c-emu/stream/...` does not exist from that base (`_scratch/lane-c-emu` is absent); it resolves from `lane-b/`, i.e. `_scratch/k1-fe-show-m1_20261109/lane-c-emu/stream/`. Absolute paths were used.

## Findings

None that change a verdict. Three notes for whoever reads this next:

1. The oracle's `check_serial` demux is a hand-written replica of the firmware control flow (`device_oracle.cpp`, `byte_audit.cpp`, `loss_exposure.cpp`), not compiled firmware. It remains faithful at 8b202f46 only because `check_serial` is text-identical (proven above). Any future change to `check_serial`, `serial_hotkey_is_immediate` or `serial_handle_hotkey` makes the replica stale and needs this comparison repeated. The receiver-isolation fix, if it touches `check_serial` (for example CR-5: ESC/CAN abort, scanner reset on idle), will invalidate the demux replica and `analyze_loss.py` tables by design; the fix must come with an updated replica.
2. `py_device_model.py` omits `b c n x` (motion-probe only, not in `k1_fe`); pre-existing, harmless for `k1_fe`.
3. `set_mode` flag/handler mismatch (above) still exists; line numbers given.

## Re-run commands

```
cd /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-b
M1=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109
SCR=$(mktemp -d)        # fresh TMPDIR so the oracle is rebuilt from the selected snapshot
mkdir -p raw_8b202f46

# 1. test suite (python3 = 3.14.8, pytest 8.4.2; the venv python at lane-c-emu/.venv also works)
TMPDIR=$SCR LANE_B_FW=fw_8b202f46 LANE_B_RAW=raw_8b202f46 python3 -m pytest -p no:cacheprovider test_validate_prim8_stream.py -q

# 2. byte audits (exit 0 = bench-eligible)
for s in $M1/../k1-fe-show-m2_20261110/m2-compose/projects/loreen/stream/loreen_post_edit_120hz.prsm \
         $M1/lane-c-emu/stream/loreen_75_155_120hz_v2.prsm; do
  TMPDIR=$SCR LANE_B_FW=fw_8b202f46 /opt/homebrew/opt/python@3.13/bin/python3.13 audit_prsm_bytes.py $s --guard 30; echo "exit=$?"
done

# 3. loss exposure (about 2 s each) then classify against the 8b202f46 serial sources
c++ -std=c++17 -O2 -Ioracle/fw_8b202f46 oracle/loss_exposure.cpp oracle/fw_8b202f46/k1_prsm.cpp \
    oracle/fw_8b202f46/k1_authored_source.cpp -o $SCR/loss_exposure
mkdir -p $SCR/serial && for f in serial_cmd_table.def serial_typed_cmd_table.def serial_menu.cpp; do
  /usr/bin/git -C /Users/spectrasynq/SpectraSynq_K1_Firmware show 8b202f46:SPECTRASYNQ_K1_FIRMWARE/serial/$f > $SCR/serial/$f; done
for g in 0 30; do
  $SCR/loss_exposure $M1/lane-c-emu/stream/loreen_75_155_120hz.prsm $g > $SCR/ev_g$g.jsonl
  /opt/homebrew/opt/python@3.13/bin/python3.13 oracle/analyze_loss.py $SCR/ev_g$g.jsonl $SCR/serial raw_8b202f46/loss_exposure_cemu_guard$g.json
done
python3 -c "import json;[print(g, json.load(open(f'raw/loss_exposure_cemu_guard{g}.json'))==json.load(open(f'raw_8b202f46/loss_exposure_cemu_guard{g}.json'))) for g in (0,30)]"

# 4. identity of the demux and hotkey code between the two commits
cd /Users/spectrasynq/SpectraSynq_K1_Firmware && P=SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp
/usr/bin/git show 407fdf6f:$P > $SCR/a.cpp; /usr/bin/git show 8b202f46:$P > $SCR/b.cpp
cmp <(sed -n 1,2963p $SCR/a.cpp) <(sed -n 1,2963p $SCR/b.cpp) && cmp <(sed -n '3713,$p' $SCR/a.cpp) <(sed -n '3743,$p' $SCR/b.cpp) && echo IDENTICAL
```

Default behaviour (no environment variables) still selects `fw_407fdf6f` and `raw/`.
