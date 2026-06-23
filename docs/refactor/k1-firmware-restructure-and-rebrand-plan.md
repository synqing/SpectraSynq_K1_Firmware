---
abstract: "Canonical end-to-end plan to restructure SPECTRASYNQ_K1_FIRMWARE/ (68 flat files) into grouped PIO subfolders and rebrand the firmware from Sensory Bridge → SpectraSynq/K1, while preserving the upstream MIT copyright (legal). 5 phases, each build-gated on both shipping envs + host tests + git mv for history. Captain decisions (2026-06-03): rebrand-but-keep-MIT-notice; grouped-subfolders-staged; execute Phase 1 (restructure) this session, plan the rest. Read before any structure/rename/brand work on the firmware."
---

# K1 Firmware — Restructure & Rebrand Execution Plan

**Status:** ACTIVE. Phase 1 executing 2026-06-03; Phases 0,2–4 pending Captain greenlight.
**Branch:** `feat/gdft-harness`. **Pre-work checkpoint:** `df7699e` (0-key hotkey).
**Authority:** Captain decisions 2026-06-03 (AskUserQuestion): (1) rebrand product → SpectraSynq/K1 but **keep the MIT copyright notice**; (2) **grouped subfolders, staged**; (3) this session = **full plan + execute Phase 1**.

## 1. Why
`SPECTRASYNQ_K1_FIRMWARE/` is 68 dead-flat files (34 `.h`, 30 `.cpp`, 1 `.ino`, 1 `.def`) — unsustainable for continued development. Separately, the firmware must become a first-class **SpectraSynq / K1** product (Kickstarter → ship) rather than a visibly-forked "Sensory Bridge" tree. These are two workstreams (structure + identity) sequenced to never break the build, lose git history, or breach the upstream licence.

## 2. Legal constraint (load-bearing — governs all brand work)
Upstream **Sensory Bridge** (`@lixielabs` / Connor Nishijima) is **MIT-licensed**; this fork currently has **no `LICENSE` file** (a compliance gap independent of rebranding). MIT requires the copyright + permission notice be retained **when the software is distributed** — and K1 *will* be distributed. Therefore the Lixie/Connor references split three ways:

| Class | Examples | Action |
|---|---|---|
| **Product/brand naming** | `Sensory Bridge`, ASCII banner, `sb_*`, `SENSORY_BRIDGE_*`, mode strings, folder name | **Rebrand** → SpectraSynq / K1 |
| **MIT copyright / authorship** | `by @lixielabs (2022–2023)` | **Preserve** in a consolidated root `NOTICE` + add `LICENSE` (MIT). Required on distribution. |
| **Technical-provenance citations** | `i2s_audio.h` documenting why the I2S config matches Emotiscope's proven SPH0645 setup; GDFT lineage notes | **Keep** (may de-brand the label, but retain the *why* — removing it is a knowledge-loss footgun) |

> ⚠ Confirm the exact upstream licence (assumed MIT from upstream repo) before finalising the `LICENSE` text in Phase 0.

## 3. Target architecture (grouped subfolders within the sketch dir)
`src_dir` stays `SPECTRASYNQ_K1_FIRMWARE` until Phase 4 (folder rename). The `.ino` **stays at the sketch-dir root** (Arduino convention; `build_src_filter` keeps `+<*.ino>`). All `.h`/`.cpp` move into functional subdirs. Bare `#include "x.h"` is preserved unchanged — every subdir is added to the compiler include path via `-I`, so includes resolve regardless of which subdir the includer lives in (no `#include` rewrites). Non-shipping instrumentation is cleaved into `diag/` (Developer Instrumentation Boundary).

| Subdir | Files |
|---|---|
| **(root)** | `SPECTRASYNQ_K1_FIRMWARE.ino` |
| **audio/** | `i2s_audio.h` `GDFT.h` `audio_transfer.h` `sb_audio_snapshot.{cpp,h}` `sb_onset_beat.{cpp,h}` `sb_tempo.{cpp,h}` |
| **visual/** | `led_utilities.h` `render_params.{cpp,h}` `Palettes.{cpp,h}` `channel_effect_state.h` `lightshow_modes.h` |
| **effects/** | `light_mode_*.cpp` (17) |
| **director/** | `sb_smart_director.{cpp,h}` `sb_mode_selection.{cpp,h}` `sb_visual_hooks.{cpp,h}` `sb_edgemixer_lite.{cpp,h}` |
| **serial/** | `serial_menu.h` `serial_cmd_table.def` `strings.h` |
| **system/** | `globals.{cpp,h}` `globals_config.cpp` `config_types.h` `constants.h` `system.h` `utilities.h` `user_config.h` `presets.h` |
| **persistence/** | `bridge_fs.h` `knobs.h` `buttons.h` `encoders.h` |
| **calibration/** | `noise_cal.h` |
| **diag/** (NON-SHIPPING) | `motion_probe.h` `gdft_harness.h` `vpab_capture.{cpp,h}` `diagnostic_capture.{cpp,h}` `sb_trace.h` |

Untouched: `light_mode_waveform_tempo.cpp.wip` (untracked, breaks build — leave at root), `*.code-workspace`.

## 4. Build coupling that MUST move in lockstep (the blast radius)
**platformio.ini** — `build_src_filter` (line 40) globs `.cpp` relative to `src_dir` root; rewrite to subdir paths. Add per-subdir `-I` to the shared `build_flags`. Update `k1_hardware_harness` filter (`+<diag/diagnostic_capture.cpp> +<diag/vpab_capture.cpp>`). Five envs extend `k1_hardware` (`k1_bench_reference`, `k1_hardware_harness`, `k1_hardware_trace_dev`, `k1_motion_probe`, `k1_tempo_probe`) — all inherit the filter/flags.

**Host harnesses** (`-I SPECTRASYNQ_K1_FIRMWARE` + per-file paths): `scripts/regression-harness/render_replay.py` (FIRMWARE sources `render_params.cpp`/`Palettes.cpp`/`light_mode_bloom.cpp` + `-I`), `tempo_replay.py` (`sb_tempo.cpp`), `row1_dispatch_table_test.cpp` (includes `serial_cmd_table.def`) + `run_row1_dispatch_table_test.sh`.

**Tests** (7): `tests/test_{trace_dev,serial_hotkeys,edgemixer_lite,dev_instrumentation_boundary,diag_capture,calibration_profile,smart_visual_engine}_static.py` reference `SPECTRASYNQ_K1_FIRMWARE/<file>`.

**Tooling/docs:** `tools/compile-{k1,s3}-arduino.sh`; `.claude/skills/k1-firmware-change-gate/SKILL.md`; ~10 `docs/forensics/*`; architecture-analysis docs. (Docs are descriptive — update the change-gate skill + tools; forensics are historical, leave with a note.)

## 5. Phases (each: change-gate → `git mv` → build BOTH shipping envs → host tests → commit)
- **Phase 0 — Legal hygiene.** Add root `LICENSE` (MIT, upstream copyright preserved) + `NOTICE` (Lixie/Connor attribution + the SpectraSynq derivative notice). Build-neutral. *Gate: builds unchanged.*
- **Phase 1 — Folder restructure (THIS SESSION).** Create subdirs; `git mv` all 64 sources per §3; rewrite `build_src_filter` + add `-I` subdir flags; fix harnesses/tests/tools/skill paths. **No behaviour change, no rename of symbols/strings.** *Gate: k1_hardware + k1_bench_reference SUCCESS; row1 dispatch 27/27; render_replay `--self-test` green; firmware.bin size unchanged ±negligible.*
- **Phase 2 — Brand strings (user-facing).** `Sensory Bridge`→`K1`/`SpectraSynq K1` in serial output + mode names + the ASCII banner. Preserve the NOTICE. *Gate: builds green; serial smoke; no licence text removed.*
- **Phase 3 — Symbol rename.** `sb_*`→`k1_*` (24 files, all call-sites), `SB_*` macros→`K1_*`, `SENSORY_BRIDGE_*` macros. High-churn; mechanical (`git grep` + scripted rename) but every TU + host harness + test recompiled. *Gate: full build matrix + all host tests.*
- **Phase 4 — Folder + `.ino` rename.** `SPECTRASYNQ_K1_FIRMWARE/` → `K1_FIRMWARE/`, `.ino` likewise; update `src_dir` + every external reference (§4). *Gate: clean checkout builds from scratch; harnesses green.*
- **(Phase 5 — repo-root rename: OUT OF SCOPE here; separate job — git remote, all absolute paths, this plan's own path.)**

## 6. Token map (Phases 2–4 reference)
`Sensory Bridge`/`SensoryBridge` → `SpectraSynq K1` (full) / `K1` (short) · `SPECTRASYNQ_K1_FIRMWARE` → `K1_FIRMWARE` · `sb_` → `k1_` · `SB_` macros → `K1_` (note: `SB_K1_HARDWARE`→`K1_HARDWARE`) · `@lixielabs`/`connornishijima`/`Lixie Labs` → **NOTICE only** (de-branded out of product surfaces, retained as MIT attribution). ASCII banner `SENSORY BRIDGE` → `SPECTRASYNQ K1`.

## 7. Safety / rollback
Per-phase atomic commits on `feat/gdft-harness`; tag before Phase 3 + Phase 4 (the irreversible-feeling ones). `git mv` preserves blame. Both bench units already carry `df7699e`; a broken build only blocks *re-flash*, not the running units. No `start_noise_cal`, no device writes in this lane. Each phase independently revertable.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | Created — full 5-phase restructure+rebrand plan. Captain decisions: rebrand+keep-MIT-notice / grouped-subfolders / execute Phase 1 this session. Architecture mapping (§3), build-coupling blast radius (§4), phase gates (§5), token map (§6). |
