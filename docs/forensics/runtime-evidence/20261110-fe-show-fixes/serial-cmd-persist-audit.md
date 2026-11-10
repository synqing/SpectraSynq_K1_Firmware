---
abstract: "Audit of the CMD_PERSISTS flag on every row of serial_typed_cmd_table.def and serial_cmd_table.def against what each handler actually does (10 Nov 2026). 36 rows corrected: 7 gain CMD_PERSISTS (set_mode, look_load, look_clear, factory_reset, restore_defaults, clear_noise_cal, commit), 29 lose it (RAM-only handlers). Checked statically by tests/test_serial_cmd_persist_flags_static.py; k1_serial_safety.py regenerated from the corrected tables."
---

# Serial command persistence-flag audit (10 November 2026)

Rule applied: a row carries `CMD_PERSISTS` exactly when the code that runs for that
command name writes, deletes, or schedules a write of persistent storage
(`save_config`, `save_config_delayed`, show-state, preset slots, look files,
LittleFS deletes, the FE PD controller NVM). Where persistence depends on the
argument, the channel or the build, the row is flagged (conservative direction).
Only the flags column changed. Paths are relative to `SPECTRASYNQ_K1_FIRMWARE/`;
line numbers are as of this audit.

## Rows changed

| Command | Table | Old flags | New flags | Evidence (file:line) |
|---|---|---|---|---|
| set_mode | typed | 0 | CMD_PERSISTS | serial/serial_cmd_handlers.cpp:1740 `save_config_delayed()` |
| look_load | typed | CMD_DISRUPTIVE | CMD_DISRUPTIVE \| CMD_PERSISTS | serial/serial_typed_dispatch.cpp:1199 `k1_look_rx_arm()` for `N,bytes`; received bytes go to `k1_look_rx_push()` -> visual/k1_look_file.h:353 `k1_look_fs_save()` -> :285 `FILE_WRITE` (argument-dependent, flagged conservatively) |
| look_clear | typed | CMD_DISRUPTIVE | CMD_DISRUPTIVE \| CMD_PERSISTS | visual/k1_look_file.h:309 `LittleFS.remove(path)` (via serial/serial_typed_dispatch.cpp:1180) |
| factory_reset | bare | CMD_IRREVERSIBLE \| CMD_DISRUPTIVE | CMD_IRREVERSIBLE \| CMD_DISRUPTIVE \| CMD_PERSISTS | persistence/bridge_fs.h:132 `LittleFS.remove(config_filename)` (and :140, :148, :156, :162) |
| restore_defaults | bare | CMD_IRREVERSIBLE \| CMD_DISRUPTIVE | CMD_IRREVERSIBLE \| CMD_DISRUPTIVE \| CMD_PERSISTS | persistence/bridge_fs.h:184 `LittleFS.remove(config_filename)` |
| clear_noise_cal | bare | CMD_IRREVERSIBLE | CMD_IRREVERSIBLE \| CMD_PERSISTS | calibration/noise_cal.h:175 `save_config()` |
| commit | bare | 0 | CMD_PERSISTS | control/k1_effect_queue.cpp:139 `save_config_delayed()` in `apply_preset_live()`, reached from the commit request via the Core-1 frame tick (:597-602 -> :242); primary channel only (flagged conservatively) |
| vp_profile | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:187 -> serial/serial_menu.cpp:965 `vp_apply_profile()` sets RAM `VP_*` globals only |
| vp_all | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:203 -> same `vp_apply_profile()`, RAM only |
| response_gain | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:910 sets RAM `audio_response_gain` (system/globals.h:55) only |
| k1_loud_guard | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:693 -> serial/serial_menu.cpp:505 RAM `k1_loud_guard_*` only |
| silence_enter | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:741 sets RAM `SILENCE_ENTER_SSL_FRAC` only |
| silence_exit | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:749 sets RAM `SILENCE_EXIT_SSL_FRAC` only |
| silence_dwell | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:757 sets RAM `SILENCE_DWELL_MS` only |
| silence_rms_enter | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:768 sets RAM `K1_SILENCE_RMS_ENTER` only |
| silence_rms_exit | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:776 sets RAM `K1_SILENCE_RMS_EXIT` only |
| queue_mode | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:961 -> control/k1_effect_queue.cpp:423 RAM only |
| transition_style | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:977 -> control/k1_effect_queue.cpp:515 RAM only |
| transition_dip_ms | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:993 -> control/k1_effect_queue.cpp:523 RAM only |
| transition_xfade_ms | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1004 -> control/k1_effect_queue.cpp:533 RAM only |
| commit_quantise | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1015 -> control/k1_effect_queue.cpp:543 RAM only |
| slot_arm | typed | CMD_PERSISTS | 0 | serial/serial_typed_dispatch.cpp:931 -> serial/serial_menu.cpp:1526 `serial_queue_slot_arm()` arms only; the save happens on a later `commit` |
| secondary_auto_color_shift | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1442, RAM `SECONDARY_*` only |
| secondary_incandescent_mode | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1464, RAM only |
| secondary_enabled | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1485, RAM only |
| secondary_photons | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1505, RAM only |
| secondary_chroma | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1521, RAM only |
| secondary_mood | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1535, RAM only |
| secondary_saturation | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1549, RAM only |
| secondary_prism_count | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1563, RAM only |
| secondary_mirror_enabled | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1579, RAM only |
| secondary_reverse_order | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1599, RAM only |
| secondary_control | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1620, RAM `secondaryMode` only |
| secondary_palette_mode | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1643, RAM only |
| secondary_palette_index | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1663, RAM only |
| secondary_base_coat | typed | CMD_PERSISTS | 0 | serial/serial_cmd_handlers.cpp:1679, RAM only |

Secondary-channel values reach flash only through an explicit `save_show`
(`k1_show_state_save()`), which is its own row and keeps `CMD_PERSISTS`.

## Counts

- Rows audited: 188 in `serial_typed_cmd_table.def`, 37 in `serial_cmd_table.def` (225 rows; `#if` rows included).
- Rows changed: 36 (32 typed, 4 bare): 7 gained `CMD_PERSISTS`, 29 lost it.
- Rows hand-verified in the test: 5 (`commit`, `slot_load`, `look_load`, `pd_nvm_write`, `gdft_agc_probe`); the other 220 are checked by the automated handler walk.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude | Created: persistence-flag audit of both serial command tables, 36 rows corrected. |
| 2026-11-10 | agent:claude | Added bare row `authored_status` (after `event_status`; SC_SAFE, flags 0, IS_BOTH): `cmd_authored_status()` only prints counters, verified non-persisting by the automated walk; bare table now 38 rows; k1_serial_safety.py regenerated. |
