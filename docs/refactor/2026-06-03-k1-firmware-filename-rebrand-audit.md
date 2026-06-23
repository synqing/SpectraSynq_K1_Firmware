---
abstract: "Read-only filename rebrand audit for SPECTRASYNQ_K1_FIRMWARE. Identifies which active firmware paths should change for a SpectraSynq K1 identity pass, which should remain functional/provenance names, and the sequencing required to avoid breaking PlatformIO, host harnesses, tests, and licence attribution."
---

# K1 Firmware Filename Rebrand Audit

Date: 2026-06-03
Branch: `feat/gdft-harness`
Source root inspected: `SPECTRASYNQ_K1_FIRMWARE/`
HEAD during audit: `7bcccff`
Tracked active firmware files inspected: 66
Untracked firmware WIP observed: `SPECTRASYNQ_K1_FIRMWARE/light_mode_waveform_tempo.cpp.wip`

## Gate Notes

- This is a read-only audit artefact. No firmware source was renamed.
- The perception-first skill referenced by `AGENTS.md` was missing at `/Users/spectrasynq/.agents/skills/perception-first-engineering/SKILL.md`; this audit proceeds from the available K1 gate, doctrine, existing rebrand plan, and live source evidence.
- Existing plan source: `docs/refactor/k1-firmware-restructure-and-rebrand-plan.md` already defines the high-level token map: `SPECTRASYNQ_K1_FIRMWARE -> K1_FIRMWARE`, `sb_ -> k1_`, `SB_ -> K1_`, and upstream attribution retained in NOTICE.
- Captain's requested target folder name for the next rebrand pass is `SpectraSynq-K1-Firmware`. PlatformIO can be pointed at that via `src_dir`; Arduino IDE sketch-name portability should be treated as non-governing unless Arduino IDE support is deliberately restored.

## Current Brand-Bearing Filename Debt

These filenames should change in the rebrand lane.

| Current path | Recommended target | Class | Notes |
|---|---|---|---|
| `SPECTRASYNQ_K1_FIRMWARE/` | `SpectraSynq-K1-Firmware/` | Product root | Captain-selected product identity. Update `platformio.ini src_dir`, hooks, tests, scripts, docs, and absolute/local references. |
| `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` | `SpectraSynq-K1-Firmware/SpectraSynq-K1-Firmware.ino` | Product entrypoint | Keeps sketch entrypoint aligned with folder identity. PlatformIO should tolerate hyphens; Arduino IDE portability is the only concern. |
| `SPECTRASYNQ_K1_FIRMWARE/SensoryBridge-main 8.code-workspace` | Delete or move to repo tooling | Stray workspace file | Not firmware source. Best action: remove from firmware source tree. If retained, move/rename outside the firmware root. |
| `persistence/bridge_fs.h` | `persistence/k1_fs.h` | Product term | Only direct firmware include found in `.ino`; tests also reference it. Minimal rename. |
| `audio/sb_audio_snapshot.cpp` | `audio/k1_audio_snapshot.cpp` | `sb_` filename | Filename rename can be separate from symbol rename. |
| `audio/sb_audio_snapshot.h` | `audio/k1_audio_snapshot.h` | `sb_` filename | Also imported by onset, tempo, smart director, visual hooks, and `.ino`. |
| `audio/sb_onset_beat.cpp` | `audio/k1_onset_beat.cpp` | `sb_` filename | Host replay compiles this directly. |
| `audio/sb_onset_beat.h` | `audio/k1_onset_beat.h` | `sb_` filename | Used by render replay host globals and visual hooks. |
| `audio/sb_tempo.cpp` | `audio/k1_tempo.cpp` | `sb_` filename | PlatformIO currently builds `audio/sb_*.cpp`; host tempo replay compiles this directly. |
| `audio/sb_tempo.h` | `audio/k1_tempo.h` | `sb_` filename | Tempo docs/scripts have many textual references; source includes are limited. |
| `diag/sb_trace.h` | `diag/k1_trace.h` | `sb_` filename | Trace wrapper owns MabuTrace boundary; tests explicitly special-case `sb_trace.h`. |
| `director/sb_edgemixer_lite.cpp` | `director/k1_edgemixer_lite.cpp` | `sb_` filename | Static tests and serial menu references. |
| `director/sb_edgemixer_lite.h` | `director/k1_edgemixer_lite.h` | `sb_` filename | Used by visual hooks and `.ino`. |
| `director/sb_mode_selection.cpp` | `director/k1_mode_selection.cpp` | `sb_` filename | Smart director dependency. |
| `director/sb_mode_selection.h` | `director/k1_mode_selection.h` | `sb_` filename | Included by smart director. |
| `director/sb_smart_director.cpp` | `director/k1_smart_director.cpp` | `sb_` filename | Host smart-director replay compiles this directly. |
| `director/sb_smart_director.h` | `director/k1_smart_director.h` | `sb_` filename | Included by `.ino`; tests assert API strings. |
| `director/sb_visual_hooks.cpp` | `director/k1_visual_hooks.cpp` | `sb_` filename | Host visual-hooks replay copies this directly. |
| `director/sb_visual_hooks.h` | `director/k1_visual_hooks.h` | `sb_` filename | Included by `.ino`; depends on onset + edge mixer. |

Count: 18 tracked file/path renames plus the firmware root folder rename.

## Filenames To Keep In This Rebrand Pass

These are not product-brand filenames and should not be renamed just to purge upstream identity.

| Path group | Decision | Rationale |
|---|---|---|
| `effects/light_mode_*.cpp` | Keep | Functional effect names. No `SensoryBridge`, `bridge`, or `sb_` filename debt. |
| `audio/GDFT.h` | Keep filename | `GDFT` is an algorithm/mechanism name. Comments still contain product/provenance text and should be handled in the later text-symbol pass. |
| `audio/i2s_audio.h` | Keep filename | Functional hardware path. Lixie/Emotiscope comments are technical provenance; keep the why, debrand wording carefully. |
| `audio/audio_transfer.h` | Keep | Functional I2S register helper. |
| `calibration/noise_cal.h` | Keep | Functional calibration name. |
| `diag/diagnostic_capture.*`, `diag/gdft_harness.h`, `diag/motion_probe.h`, `diag/vpab_capture.*` | Keep | Diagnostic function names. No product brand debt. |
| `serial/serial_menu.h`, `serial/serial_cmd_table.def` | Keep | Functional command surface names. |
| `system/*.h`, `system/*.cpp` | Keep | Generic system names. Symbol-level `SB_*` inside these files is separate. |
| `visual/led_utilities.h`, `visual/lightshow_modes.h`, `visual/render_params.*`, `visual/channel_effect_state.h` | Keep for now | Functional names. `lightshow_modes.h` may later become `effect_dispatch.h`, but that is architecture/style debt, not rebrand debt. |
| `visual/Palettes.*` | Keep for now | Case/style debt only. A lowercase `palettes.*` pass is optional and should not be bundled with brand removal. |
| `persistence/buttons.h`, `persistence/knobs.h`, `persistence/encoders.h` | Keep filename | Functional names, although comments still say Sensory Bridge. |

## Coupling That Must Move With The Renames

Path/folder rename coupling:

- `platformio.ini`
  - `src_dir = SPECTRASYNQ_K1_FIRMWARE`
  - `build_src_filter = ... +<audio/sb_*.cpp> +<director/sb_*.cpp>`
- `scripts/hooks/pre-commit`
  - hard-coded `SPECTRASYNQ_K1_FIRMWARE/*.cpp|*.h|*.ino` patterns only cover root files today and already miss subdir firmware changes; the folder rename is the right time to fix this to recursive globs.
- `tests/_fwpath.py`
  - central firmware root helper. Update first, then simplify individual tests.
- Tests with hard-coded file/module names:
  - `tests/test_trace_dev_static.py`
  - `tests/test_dev_instrumentation_boundary.py`
  - `tests/test_calibration_profile_static.py`
  - `tests/test_edgemixer_lite_static.py`
  - `tests/test_smart_visual_engine_static.py`
  - `tests/test_diag_capture_static.py`
  - `tests/test_serial_hotkeys_static.py`
  - `tests/test_fw_strings_removed_static.py`
- Host harnesses:
  - `scripts/regression-harness/render_replay.py`
  - `scripts/regression-harness/render_host_globals.cpp`
  - `scripts/regression-harness/tempo_replay.py`
  - `scripts/regression-harness/tempo_accuracy.py`
  - `scripts/regression-harness/novelty_from_wav.py`
  - `scripts/regression-harness/onset_beat_replay.py`
  - `scripts/regression-harness/smart_director_replay.py`
  - `scripts/regression-harness/visual_hooks_replay.py`
  - `scripts/regression-harness/row1_dispatch_table_test.cpp`
  - `scripts/regression-harness/loop.py`
  - `scripts/regression-harness/spaces/**` source refs where they are intended to track live paths rather than historical evidence.
- Build include helper:
  - `scripts/platformio/k1_src_includes.py` uses `$PROJECT_SRC_DIR`, so it should survive the root folder rename without path edits. Its comments mention the rebrand plan only.
- Docs/skills:
  - `.claude/skills/k1-firmware-change-gate/SKILL.md` references `SPECTRASYNQ_K1_FIRMWARE.ino`.
  - Historical forensics can keep old paths if they are evidence records; current instructions/plans should update.

## Source-Text Debt Adjacent To Filename Renames

Filename rebrand alone will not remove internal `SB` identity. Current source still has a large symbol surface:

- Public types/functions in audio/director: `SBAudioSnapshot`, `SBOnsetBeatEvent`, `SBTempoEvent`, `SBSmartDirectorConfig`, `SBModeIntent`, `SBEdgeMixerConfig`, `SBVisualHookConfig`, and `sb_*` functions.
- Trace macros: `SB_TRACE_SCOPE`, `SB_TRACE_COUNTER`, `SB_TRACE_INSTANT`, `SB_TRACE_INIT`, `SB_TRACE_DUMP_JSON`.
- Build flags: `SB_K1_HARDWARE`, `SB_K1_BENCH_REFERENCE_PINMAP`, host-test flags such as `SB_TEMPO_HOST_TEST`.
- Status tokens: `SB_PASS`, `SB_FAIL`.
- User-visible/product strings still found in `.ino`, `serial_menu.h`, `bridge_fs.h`, `buttons.h`, `knobs.h`, `user_config.h`, `GDFT.h`, and `i2s_audio.h`.

Recommendation: do not mix filename renames with symbol renames in the same commit unless there is an automated rename script plus full build/test matrix. Filename-only renames are mechanically smaller and preserve behaviour. Symbol renames are high-churn but ultimately necessary for a clean SpectraSynq K1 source identity.

## Recommended Execution Order

### Phase A - Root folder and entrypoint

Rename:

- `SPECTRASYNQ_K1_FIRMWARE/` -> `SpectraSynq-K1-Firmware/`
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` -> `SpectraSynq-K1-Firmware/SpectraSynq-K1-Firmware.ino`
- Remove or relocate `SensoryBridge-main 8.code-workspace`

Required edits:

- `platformio.ini src_dir`
- `scripts/hooks/pre-commit` recursive firmware path classification
- `tests/_fwpath.py` and direct INO references
- host harness `FIRMWARE = ROOT / ...` constants
- row1 dispatch include path
- current docs/skills only; leave historical forensics unless they are current instructions

Gate:

- `python3 -m pytest tests -q`
- `python3 scripts/regression-harness/render_replay.py --self-test`
- `python3 scripts/regression-harness/tempo_replay.py`
- `python3 scripts/regression-harness/onset_beat_replay.py`
- `python3 scripts/regression-harness/smart_director_replay.py`
- `python3 scripts/regression-harness/visual_hooks_replay.py`
- `pio run -e k1_hardware`
- `pio run -e k1_bench_reference`
- `pio run -e k1_hardware_harness`

### Phase B - Filename-level `sb_` and `bridge_fs` purge

Rename the 15 `sb_*` files to `k1_*` and `bridge_fs.h` to `k1_fs.h`. Update includes and direct harness paths. Keep existing public `SB*` types/functions for this phase unless Captain explicitly wants the high-churn symbol pass bundled.

Required build edit:

- `platformio.ini build_src_filter`: replace `+<audio/sb_*.cpp> +<director/sb_*.cpp>` with the `k1_*` equivalent or explicit source entries.

Gate: same as Phase A.

### Phase C - Symbol-level source identity

Rename public and private source symbols:

- `sb_*` -> `k1_*`
- `SB*` types/enums/macros -> `K1*`
- `SB_TRACE_*` -> `K1_TRACE_*`
- build flags `SB_K1_*` -> `K1_*`

This is not just cosmetic. It crosses source, tests, harnesses, docs, and preprocessor flags. Run the full host/build matrix and inspect binary symbol leftovers with `nm`/`rg`.

### Phase D - User-visible strings and provenance cleanup

Replace product strings in serial/banner/comments:

- `Sensory Bridge` user-facing strings -> `SpectraSynq K1` or `K1`
- ASCII banner -> `SPECTRASYNQ K1`
- Keep upstream MIT authorship in `NOTICE`/`LICENSE`
- Keep technical provenance where it explains a mechanism, especially `i2s_audio.h` Emotiscope microphone config notes and GDFT lineage notes.

## Decision

[FACT] The active filename set contains 18 tracked paths that should change for a SpectraSynq K1 rebrand: the root entrypoint/workspace, one `bridge_*` file, and 15 `sb_*` files.

[INFERENCE] The safest implementation is staged: root path first, filename purge second, symbol purge third, user-visible text/provenance last. This preserves rollback boundaries and isolates build failures.

[DO NOT DO] Do not remove upstream legal attribution while rebranding. Do not rename `GDFT.h` or `i2s_audio.h` as part of the brand purge; those filenames are mechanism names, not upstream product identity.

---

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-06-03 | Codex | Created read-only filename rebrand audit for `SPECTRASYNQ_K1_FIRMWARE/`. |
