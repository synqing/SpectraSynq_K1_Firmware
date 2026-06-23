# 2026-06-11 Effects Lane Recovery From Claude-Mem

## 2026-06-15 Supersession Note

This document is now historical for the original Claude-memory recovery. The
recommended repair slice has been applied in current source at the time of this
supersession (`HEAD=1d3939f` before this documentation update):

- Mode IDs 24/25 are no longer remapped to old Snapwave/Pulse Prism aliases.
  `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:82-88` records the old aliases
  as retired, and `light_mode_sanitize_persisted()` at
  `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:157-160` now only rejects
  out-of-range or disabled modes.
- AP chord telemetry is no longer in the production acquisition path.
  `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:563-573` reads tempo and onset
  events only; there is no `sb_audio_snapshot_read()` or `ch_root` field in the
  AP stream.
- Static guards now cover both contracts:
  `tests/test_snapwave_pulse_static.py:129-139` and
  `tests/test_chord_hue_consumer_static.py:72-79`.
- Focused verification passed:
  `38 passed` for the chord/new-effects/Snapwave/palette/impact static set.
  `pio run -e k1_hardware` and `pio run -e k1_bench_reference` passed with the
  known `system.h:48` volatile warning only.
- Partial live VP smoke for modes 24-27 passed on both registered K1s with no
  crash-marker matches. Evidence:
  `docs/forensics/2026-06-15-new-effects-mode24-27-partial-vp-smoke.md`.

Modes 28-29 were not completed in that live smoke. Do not treat this as a full
mode 24-29 product gate.

## Scope

Captain asked to recover what Claude Code learned and what it was planning before usage ran out while implementing new K1 effects.

This is a research handoff, not an implementation patch. No firmware code was changed in this recovery pass.

## Sources Read

- User-supplied Claude transcript: `/Users/spectrasynq/.codex/attachments/105cd206-e321-4d1c-ac92-092b17c57c6f/pasted-text.txt`
- Claude memory note: `/Users/spectrasynq/.claude/projects/-Users-spectrasynq-SensoryBridge-main-9/memory/project_sb_codex_breakage_restore.md`
- Current repo branch state: `rescue/1401-head-minus-killset`, `HEAD=0679a3b`
- Effect architecture method: `docs/architecture/effect-decomposition/00-the-method.md`, `docs/architecture/effect-decomposition/LEVERS-MATRIX.md`
- Current firmware seams: mode registry, render dispatch, AP telemetry, audio snapshot, effect implementations, and build flags
- Read-only subagent sidecars:
  - `EFFECT-RECOVER-A`: git/source archaeology
  - `EFFECT-RECOVER-B`: effect-method compliance review
  - `EFFECT-RECOVER-C`: seam and risk review

Retrieval note: the local `claude-mem status` command reported the worker alive, but the available MCP corpus query returned no observations for this lane. The useful Claude memory source was the on-disk project memory file listed above.

## Current Source Truth

The live worktree is clean on branch `rescue/1401-head-minus-killset`. Recent history is:

- `0679a3b` - K1-native palette registry additions
- `5f1a312` - `DENSE FORGE CHORD` mode 24
- `3147010` - tag `k1-rescue-baseline-20260611`

Dense Forge Chord is present in source as mode 24:

- `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:75-102` appends `LIGHT_MODE_DENSE_FORGE_CHORD` before `NUM_MODES`.
- `SPECTRASYNQ_K1_FIRMWARE/system/system.h:364-388` registers the mode name as `DENSE FORGE CHORD`.
- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge_chord.cpp:85-103` implements the mode and reads `SBAudioSnapshot`, `SBOnsetBeatEvent`, and `SBTempoEvent`.
- `platformio.ini:89-93` enables `SB_CHORD_HUE_V1` in the current build flags.

The chord mapping itself is narrow and hue-only:

- `light_mode_dense_forge_chord.cpp:191-238` pulls chromagram centroid toward held chord root.
- It uses a 250 ms root hold, a confidence remap above `0.625`, a blend cap of `0.6`, and a 0.5 rev/s hue slew.
- The file comment at `light_mode_dense_forge_chord.cpp:10-16` says the variant must not alter original Dense Forge brightness or motion.

Existing audio surfaces are already sufficient for the planned effects:

- `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h:57-79` publishes energy, spectrum, `chroma_pc[12]`, and chord state under the v2 flags.
- `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h:82-114` publishes onset, kick, snare, and hihat event fields under `SB_ONSET_V2`.
- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_comet.cpp:91-118` currently consumes only kick/bass onset, deliberately keeping Comet as one clear kick rule.
- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet.cpp:6-40` already owns a beat-grid-locked comet engine, so some "beat anticipation" ideas are variants/refinements rather than a blank-sheet engine.

API/control surfaces should not expand for this lane:

- `docs/protocol/k1-rest-contract.yaml:5-9` says REST is not implemented for this control slice and K1 Tab5 control uses the AP-only WebSocket contract.

## What Claude Learned

1. The strobe failure was global, not just a bad variant file.

   The Claude transcript says `5f1a312` strobed ON/OFF on mode 24 and original mode 21, then the strobe left after rollback to `k1-rescue-baseline-20260611` (`pasted-text.txt:11-16`, `pasted-text.txt:26-33`). The Claude memory repeats this and records the leading root cause as AP chord telemetry stack-allocating an approximately 428 byte `SBAudioSnapshot` inside `acquire_sample_chunk` on the 8 KB loopTask stack (`project_sb_codex_breakage_restore.md:19`).

   The current source still contains that telemetry path:

   - `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:521-539` appends `ch_root/ch_type/ch_conf` and creates a local `SBAudioSnapshot chord_dbg = sb_audio_snapshot_read();`.
   - `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:353-356` makes `AP_STREAM_ENABLED` default on unless overridden.
   - `platformio.ini:84-93` enables `SB_CHORD_V2` and `SB_CHORD_HUE_V1` in the production flags.

   Confidence: medium-high for the telemetry/stack hypothesis, matching Claude's own caveat. Proven facts are narrower: strobe arrived with the flash, affected original mode 21 too, and left with rollback.

2. "Do not modify original effects" means behaviour on the plate, not just unchanged files.

   Claude explicitly corrected itself: it left the original Dense Forge file byte-identical but still broke original Dense Forge behaviour via a global Core-0 AP telemetry addition (`pasted-text.txt:26-33`). The memory records this as a Captain-enforced lesson (`project_sb_codex_breakage_restore.md:19`).

3. Core-0 audio/AP telemetry is frozen for effect-consumer lanes.

   Claude's lesson was that the Core-0 audio path has the same protected status as colour helpers for effect work (`pasted-text.txt:32-39`, `project_sb_codex_breakage_restore.md:19`). Future effect variants should consume already-published surfaces from render-side code, not add production AP telemetry from inside audio acquisition.

4. A 30 second serial soak is mandatory before Captain eyes-on.

   Claude only observed one boot banner and two telemetry lines before asking for eyes-on; the postmortem made a 30s+ soak watching reboot markers mandatory (`pasted-text.txt:32-33`, `project_sb_codex_breakage_restore.md:19`).

5. The effect architecture method is the generator, not a side document.

   The method states every effect factors into `Motion(Mapping(audio), previous_pixels)` and the seam is `{ where, colour, intensity }` (`docs/architecture/effect-decomposition/00-the-method.md:35-60`). It also bans autonomous wall-clock oscillators in motion (`docs/architecture/effect-decomposition/00-the-method.md:196-213`). Claude learned to treat new effects as new mappings over owned motion engines, not new uncontrolled Field systems (`pasted-text.txt:47-48`, `pasted-text.txt:72-76`).

6. Chord hue is plausible, but raw chord root needs hold/slew.

   Claude recorded that Dense Forge Chord used a 250 ms held-root gate, confidence remap above `0.625`, and 0.5 rev/s slew (`pasted-text.txt:17-19`, `project_sb_codex_breakage_restore.md:20`). The current source matches those parameters at `light_mode_dense_forge_chord.cpp:191-238`.

7. Snare/hihat consumers are not authorised until substrate liveness is proven on-device.

   Claude listed percussion decomposition but explicitly gated snare/hihat on-device liveness before pixels (`pasted-text.txt:57-59`, `pasted-text.txt:72-73`). This matters because current Comet deliberately ignores broadband onset and only visualises kick/bass onset (`light_mode_comet.cpp:91-118`).

## What Claude Was Planning

Claude's immediate plan after Captain said "Implement ALL" was:

1. Re-land Dense Forge Chord minus toxic telemetry.
2. Draft five new effects in parallel against the per-class docs.
3. Own shared-surface registration, state struct changes, tests, gate, and soak-verified flash (`pasted-text.txt:80-84`).

Claude had listed seven opportunities, then answered "all six". Best interpretation: item 7, the chord-hue anchor family, was a family expansion of item 1 rather than a separate first-pass mode. Do not depend on that wording without Captain confirmation.

Planned effect opportunities:

1. True dual-channel split: harmony vs rhythm.

   Primary edge uses tonal/chord/chroma mapping; secondary edge uses percussive kick/snare/hihat transport pulses (`pasted-text.txt:50-52`). This is high impact if channel state remains isolated and centre-origin.

2. Chroma Constellation.

   Use `chroma_pc[12]`, map pitch-class energy to circle-of-fifths logical lanes, then flow outward (`pasted-text.txt:54-56`). Compliance caveat: the "positions" must be logical lanes inside centre-origin outward transport, not arbitrary non-centre strip origins.

3. Percussion spatial decomposition.

   Kick centre ring, snare outward particle burst, hihat short-life shimmer on an owned Comet-like pool (`pasted-text.txt:57-59`). Compliance caveat: snare/hihat liveness must be proven first, and "mid-strip" or "edge" must not become non-centre origins.

4. Beat anticipation.

   Use `phase01` as a target so particles arrive on the next beat, not merely fire after a beat tick (`pasted-text.txt:61-62`). The effect decomposition roadmap already names beat/tempo phase as the highest-leverage gap and calls out comets landing on the beat (`docs/architecture/effect-decomposition/LEVERS-MATRIX.md:191-201`).

5. Build/drop macro-structure.

   Compute a VP-side fast/slow EMA over `spectral_energy` to create a 20-30s song-arc axis, then compress/accelerate during builds and release on drops (`pasted-text.txt:64-65`). The levers matrix names structure-aware self-modulation as an empty row (`LEVERS-MATRIX.md:214-222`).

6. Tempo-locked palette walk.

   Salvage Beat Palette by changing palette blend once per bar, without amplitude changes (`pasted-text.txt:67-68`). Compliance caveat: no rainbow sweep, no free-running oscillator, no abrupt brightness/palette flash.

7. Chord-hue anchor family.

   Reuse the held-root/confidence/slew mapping from mode 24 on Spectrum River, Ember, or Waveform Tempo variants (`pasted-text.txt:70`).

## Blockers Before Any New Effects

1. Mode ID collision.

   `LIGHT_MODE_DENSE_FORGE_CHORD` is now ID 24 (`config_types.h:75-102`), but `light_mode_sanitize_persisted()` still treats persisted mode 24 as a former Snapwave A/B alias and remaps it to `LIGHT_MODE_SNAPWAVE` (`config_types.h:138-142`). Boot config load applies this sanitizer to primary and secondary mode (`persistence/bridge_fs.h:130-132`).

   This must be fixed before appending more modes. Either preserve old 24/25 migration semantics by moving Dense Forge Chord to a non-colliding append-only ID, or deliberately retire the old alias behaviour and update tests/docs accordingly.

2. AP chord telemetry is still in the production path.

   `i2s_audio.h:521-539` still allocates and prints chord telemetry under `SB_CHORD_V2`; `globals.h:353-356` defaults AP stream on; `platformio.ini:84-93` enables the relevant flags. This is the same class of change blamed for the strobe incident. Remove it or gate it behind a non-shippable diagnostic flag before more effect work.

3. Dense Forge Chord has no fresh proof in this recovery pass.

   I did not run `pytest`, `pio run`, upload, serial soak, or eyes-on. Commit messages and Claude memory mention prior gates, but current truth requires rerunning them after telemetry and mode-ID repair.

4. Tab5 exposure is not complete.

   Subagent archaeology found palette UI updates at HEAD, but the Tab5 mode list/cap still ended at mode 23 in its inspected files. Mode 24 may be manual/API selectable in firmware but not exposed through that UI.

5. Do not treat "snare/hihat available in structs" as proof they are good.

   The structs expose snare/hihat fields, but Claude's own plan gates their use on live substrate proof. Current Comet comments are explicit that it ignores non-kick onset because the viewer rule must remain trivial and reliable (`light_mode_comet.cpp:91-118`).

## Recommended Next Slice

Do this before implementing any additional effects:

1. Repair the mode registry and migration surface.

   Decide the ID policy for old 24/25 aliases versus new mode 24. Update `config_types.h`, `system.h`, render dispatch, tests, and any UI lists affected by the decision.

2. Remove or non-shippable-gate AP chord telemetry.

   The effect lane should not add stack-heavy snapshot reads or serial print expansion inside Core-0/AP acquisition. If substrate proof is still needed, put it in a harness/dev-only build or use an already safe diagnostic surface.

3. Re-run the existing gates.

   Minimum before device:

   - `pytest tests/ -v`
   - `pio run -e k1_hardware`
   - instrumentation/telemetry boundary check

   Minimum after upload:

   - verify target identity before flash
   - 30s+ serial soak watching for reboot markers
   - Captain eyes-on for mode 24 before item 2

4. Only then resume new variants.

   Safest order after the repair slice:

   - Dense Forge Chord retry, because it is mostly built and can prove the chord mapping.
   - Beat anticipation / Tempo Comet arrival variant, because the owned engine already exists and the levers matrix names it as high leverage.
   - Structure-aware macro variant, because it is VP-side and avoids Core-0 changes.
   - Dual-channel harmony/rhythm split, once per-channel state and balance are explicitly reviewed.
   - Chroma Constellation, keeping circle-of-fifths as logical lanes inside centre-origin transport.
   - Percussion decomposition, only after snare/hihat liveness is proven live.
   - Chord-hue anchor family, only if the first chord retry passes eyes-on.

## Thinking-Lens Synthesis

- Model router: this is primarily systems/debugging plus architecture, not greenfield effect design. The immediate constraint is risk removal.
- Bayesian update: the telemetry stack hypothesis is not proven, but it explains cross-mode strobe better than the variant render body. Treat it as the default risk until disproven by a clean telemetry-free retry.
- Systems view: a small "debug" addition in Core 0 can dominate every mode's observed behaviour. Effect lanes must not widen global producers.
- TRIZ: the contradiction is "need substrate liveness proof" versus "Core-0/AP telemetry is frozen". Resolve by separation by environment: dev/harness-only proof, production render consumers only.
- Second-order: adding six effects before the repair slice compounds ID, state, UI, and verification debt. The right acceleration is to first make the shared registry and telemetry surfaces boring again.
- Steelman: Claude's intended effect ideas are not bad. Most are good recombinations of existing signals and owned motion engines. The failure was unsafe shared-surface work and insufficient runtime proof, not the whole design direction.

## Paste-Ready Prompt For The Next Implementation Agent

Captain wants the K1 effects lane resumed from the Claude-memory recovery, but implementation must start with the repair slice, not new visual complexity.

Read first:

1. `.claude/CLAUDE.md`
2. `docs/spec-index.md`
3. `docs/handover/2026-06-11-effects-lane-claude-mem-recovery.md`
4. `docs/architecture/effect-decomposition/00-the-method.md`
5. `docs/architecture/effect-decomposition/LEVERS-MATRIX.md`

Hard boundaries:

- No new effect modes until mode registry and AP telemetry are repaired.
- Do not touch I2S DMA, sample rate, tempo/onset/chord producers, calibration, serial command semantics, Smart Director auto-selection, or WiFi/AP architecture.
- No Core-0/AP production telemetry additions for effect-consumer proof.
- Preserve centre-origin, no rainbows, no heap in render, dt-correct smoothing, and 2 ms render ceiling.
- British English in comments/logs/docs.

First slice:

1. Fix the mode 24/25 persistence collision around `light_mode_sanitize_persisted()`.
2. Remove or dev-only gate the chord AP telemetry in `i2s_audio.h`.
3. Update mode registry/name/dispatch/tests consistently.
4. Run `pytest tests/ -v` and `pio run -e k1_hardware`.
5. If uploading is authorised in the current task, verify target identity, flash, then run a 30s+ serial soak before asking Captain for eyes-on.

Deliverable:

- A concise source-backed report with exact files changed, gate outputs, whether device proof exists, and whether Dense Forge Chord is safe to retest.
