---
abstract: "Read-only audit of VP palette mode, auto colour shift, and chromatic mode in the K1 SensoryBridge firmware. Finds that the incomplete colour-range symptom is mostly design-level: palette mode has per-mode semantics, Bloom/Waveform collapse palette output to one chroma-centroid sample per frame, the candidate chromagram sparsity gate can zero dense/flat chroma and force CHROMA fallback, and auto-colour phase is global/novelty-driven rather than a bounded per-channel palette target. No serial port was opened and no runtime capture was parsed in this pass."
---

# VP Palette / Auto Colour / Chromatic Audit

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Branch observed | `feat/pio-core-bump` |
| Scope | Read-only source audit of palette mode, auto colour shift, chromatic mode, and VP colour integration |
| Runtime proof | Not captured in this pass. Agent did not open serial. |

## Doctrine Gate

[FACT] Project law requires centre-origin visual behaviour, no rainbow cycling, no heap in render, 120 FPS / 2.0 ms render ceiling, dt-correct smoothing, sub-8 ms audio-to-visual latency, AP-only WiFi, British English, serial-port discipline, and no compile/upload-as-runtime-proof claims. Sources: `AGENTS.md`, `.claude/CLAUDE.md`, `.claude/skills/sensorybridge-doctrine/SKILL.md`.

[FACT] K1-local north star: architecture is subordinate to visual/musical output; regressions include weaker musical responsiveness, independent dual-channel behaviour, colour clarity, or motion memory.

[FACT] This pass touched source and docs only. No calibration command, serial command, commit, tag, branch, push, or firmware edit was performed.

Runtime proof required before any fix can be called successful:
- `vp_status` or `vp` stream showing chroma gate metrics before/after.
- `vp_out_test` hashes/energy if the output-probe path is used.
- Eyes-on capture for at least Bloom/Bloom Fast, Waveform Hybrid, GDFT, Chromagram Gradient, and Chromagram Dots with palette mode and auto colour shift exercised.

## Root Cause Summary

[FACT] Palette mode is not one behaviour. It is a flag that lets each mode choose its own palette-index mapping through `palette_owns_render_colour_source()` (`SPECTRASYNQ_K1_FIRMWARE/globals.h:665-670`) and per-mode `ColorFromPalette()` calls in `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h`.

[FACT] Some modes can show most or all of a palette in one frame: `kaleidoscope` and `chromagram_gradient` map LED position over `0..255` (`lightshow_modes.h:667-668`, `lightshow_modes.h:765-767`). `gdft` and `vu` map nearly all of the range, ending at index 251 because the denominator is 80 (`lightshow_modes.h:258-260`, `lightshow_modes.h:449-450`).

[FACT] Other modes cannot show the full palette by design:
- `vu_dot` samples one palette index from brightness (`lightshow_modes.h:505-510`).
- `chromagram_dots` samples 12 note positions, so its highest direct note index is about 233, not 255 (`lightshow_modes.h:825-827`, `lightshow_modes.h:844-845`).
- `bloom`, `bloom_fast`, `waveform_fast`, `waveform`, and `waveform_hybrid` use `palette_chroma_colour()` for palette ownership (`lightshow_modes.h:919`, `lightshow_modes.h:1253-1255`, `lightshow_modes.h:1406-1407`, `lightshow_modes.h:1528-1529`). That helper intentionally chooses one palette position from the 12-bin chromagram centroid and brightness separately (`lightshow_modes.h:121-165`).

[INFERENCE] If Captain is seeing palette mode not display the complete colour range during Bloom/Waveform-family use, the most likely mechanism is not a bad palette table. The active design samples one palette colour per frame, then moves that sample only if chromagram centroid or global auto-colour phase moves. It will not reveal a full palette spatially in those modes.

[FACT] The candidate VP profile enables chromagram sparsity gating by default (`globals.h:347-351`). `make_smooth_chromagram()` zeroes the chromagram when normalized output is quiet or flat, then subtracts `0.1` and multiplies by `gate_gain` (`led_utilities.h:1543-1562`).

[INFERENCE] Dense chords, broadband material, or weak/flat chroma can therefore make `palette_chroma_colour()` hit its fallback path (`lightshow_modes.h:143-147`) and sample the selected palette at `CONFIG.CHROMA` rather than across the palette. That makes palette mode feel locked to a narrow colour region even though the selected palette itself contains more colours.

[FACT] Auto colour shift is driven by positive spectrogram novelty (`GDFT.h:289-324`) and mutates global `hue_position` / `hue_shifting_mix` (`led_utilities.h:1426-1475`). The main loop only calls `process_color_shift()` when primary `CONFIG.AUTO_COLOR_SHIFT` is true; otherwise it resets `hue_position` to 0 (`SPECTRASYNQ_K1_FIRMWARE.ino:452-460`).

[INFERENCE] The secondary channel has its own `SECONDARY_AUTO_COLOR_SHIFT` flag and palette-index phase checks that flag (`lightshow_modes.h:98-103`), but there is only one global `hue_position`. If primary auto colour shift is off, the main loop resets the phase even when secondary auto shift is enabled. If both are on, the channels share the same phase. That weakens independent dual-channel colour behaviour.

## Per-Mode Palette Coverage

| Mode | Palette mapping | Full range in one frame? | Evidence |
|---|---|---:|---|
| GDFT | `freq_prog * 255`, brightness from spectral bin | Almost, 0..251 | `lightshow_modes.h:258-260` |
| VU | bar position over half-strip | Almost, 0..251, but only lit up to current bar level | `lightshow_modes.h:449-450` |
| VU Dot | one brightness-derived index | No, one point per frame | `lightshow_modes.h:505-510` |
| Kaleidoscope | half-strip position over `0..255` | Yes when pixels are bright enough | `lightshow_modes.h:667-668` |
| Chromagram Gradient | half-strip position over `0..255` | Yes, and has a 10% magnitude floor | `lightshow_modes.h:739`, `lightshow_modes.h:765-767` |
| Chromagram Dots | 12 note indices | No, 12 discrete samples | `lightshow_modes.h:825-827`, `lightshow_modes.h:844-845` |
| Bloom / Bloom Fast | chromagram centroid | No, one colour insertion per frame | `lightshow_modes.h:919`, `lightshow_modes.h:944-948` |
| Quantum Collapse | position plus brightness term | Partial, biased toward 63..253 in source formula | `lightshow_modes.h:1114-1121` |
| Waveform Fast | chromagram centroid blended with fallback | No, one trail colour per frame | `lightshow_modes.h:1253-1282` |
| Waveform | chromagram centroid if active | No, one trail colour per frame | `lightshow_modes.h:1406-1420` |
| Waveform Hybrid | chromagram centroid blended with fallback | No, one trail colour per frame | `lightshow_modes.h:1528-1553` |

## Additional Design/UX Findings

[FACT] `Palettes.h` defines 33 palettes and parallel `gGradientPalettes[]` / `paletteNames[]` arrays (`Palettes.h:484-566`). Earlier audit work already identified non-monotonic luminance palettes and redundant magenta/vintage entries in `audit/PALETTE_AUDIT.md` and `audit/understanding/07_palette_library_history.md`.

[INFERENCE] Palette-list quality can contribute to perceived incompleteness, especially where a palette contains dark luminance valleys. It is secondary to the source-mapping issue above: even a perfect palette will look incomplete if the mode only samples one centroid colour.

[FACT] The old `save_configuration()` / `load_configuration()` functions include secondary palette fields (`bridge_fs.h:217-294`) but are not referenced elsewhere. The live `save_config()` / `load_config()` path writes and reads only the `CONFIG` struct (`bridge_fs.h:55-84`, `bridge_fs.h:96-125`), which does not contain secondary palette, secondary palette-mode, or secondary auto-shift fields.

[INFERENCE] Secondary palette UX is runtime-only unless another save path exists outside this grep scope. That means Captain can tune a strong dual-channel palette state and lose part of it after reboot. This matches prior memory that `preset=`/config persistence did not fully restore secondary/VP state.

[FACT] Hotkeys expose palette previous/next/mode and auto colour shift (`serial_menu.h:661-715`, `serial_menu.h:967-974`), but hotkey status does not print palette mode/index, auto colour shift, or chromatic mode state (`serial_menu.h:721-770`).

[INFERENCE] UX currently makes it easy to enter palette/chromatic/auto-colour combinations and hard to confirm the exact combined state without other commands. That raises the chance of misdiagnosing a design-limit as a palette-table failure.

## Improvement Options

### Option A — Minimal Correctness Patch

Keep current architecture and fix the obvious integration gaps:
- Give secondary auto colour shift its own phase state, or at least stop primary-auto-off from resetting a secondary-enabled phase.
- Add palette/chromatic/auto-colour state to hotkey status and `vp_status`.
- Persist secondary palette index/mode and secondary auto colour shift in the live config/preset path.

Pros: low blast radius and directly improves UX/debuggability.  
Cons: does not change the fact that Bloom/Waveform palette mode samples one colour per frame.

### Option B — Palette Policy Layer

Extract palette mapping into a small policy boundary with named strategies:
- `spatial_full_range`: full gradient across centre-origin geometry.
- `note_discrete`: 12 pitch-class samples.
- `chroma_centroid`: one musically-selected palette colour.
- `energy_window`: a bounded moving window around the active centroid.
- `dual_channel_complement`: primary and secondary offsets selected as a pair.

Pros: makes mode semantics explicit and testable; avoids each mode reinventing palette mapping.  
Cons: medium refactor risk in render code and must be guarded by native VP probe plus hardware visual proof.

### Option C — High-Impact Palette Redesign

Treat palette mode as product-level colour direction:
- Keep palette tables stable by appending rather than reordering.
- Add 4-6 K1-specific cinematic palettes with controlled luminance and warm/cool intent.
- Add a curated "K1 palette lane" separate from the full legacy CPT-city catalogue.
- For Bloom/Waveform, use a bounded palette window around the chroma centroid rather than a single point, so the mode stays musical while showing more of the palette.

Pros: best visual impact and better Captain-facing UX.  
Cons: needs eyes-on palette auditions; cannot be validated by build or hashes alone.

## Recommended Direction

[INFERENCE] The best next step is Option A plus the smallest slice of Option B: define a palette mapping policy table and migrate only Bloom/Waveform-family palette output first. The goal is not "show every colour always"; it is "make each mode's palette behaviour intentional and observable."

Concrete first implementation target, if approved later:
1. Add serial/native probe output for palette strategy, source index, phase, chroma final max/mean, and fallback-vs-centroid decision.
2. Split `hue_position` into primary/secondary palette phase state.
3. Replace Bloom/Waveform centroid-only output with a bounded centroid-window strategy that can show adjacent palette colours while preserving centre-origin motion and avoiding rainbow-wheel sweeps.
4. Persist and report secondary palette/autocolour state.

## Non-Goals For This Pass

- No firmware patch.
- No palette table rewrite.
- No calibration or serial command.
- No claim that the hardware visual symptom is proven resolved.
- No change to audio pipeline, AP behaviour, WiFi, or build configuration.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-25 | Codex | Created read-only VP palette/auto-colour/chromatic audit and improvement options. |
