# SB Forensic Reconstruction Findings

## Evidence Lanes

- Git history in `/Users/spectrasynq/SensoryBridge-main 9`.
- Current dirty tree after K1 hardware LEDC/sweet-spot fix.
- Committed docs: `docs/s3-migration-prep.md`, `docs/superpowers/plans/*`, `docs/config-snapshots/*`, `audit/understanding/*`.
- `claude-mem` observations for prior Bloom/Waveform repair, K1 hardware GPIO/compile/upload work, serial strategy, Rotate8, LEDC, and PSRAM.
- Reused existing SSA pool because new spawns hit the thread limit.

## Early Ground Truth

- `git status --short` showed current uncommitted K1 hardware work in firmware files plus `tools/compile-k1-arduino.sh`.
- Recent committed history contains secondary render isolation, p2p removal, recovery roadmap docs, perfect config snapshot, S3 compile prep, K1.Lightwave reference, K1 hardware GPIO profile, and K1 hardware upload evidence.
- Existing SSA outputs already contained useful prior K1 hardware source-truth notes, but fresh read-only tasks were also queued on those same agents.

## Reconstructed Findings

- Bloom/Waveform repair commits are not individually represented in local git; the relevant `lightshow_modes.h` state enters as part of the root checkpoint `de4fc48`.
- `lightshow_modes.h` currently proves the Bloom history fix: the `leds_prev_buffer` snapshot sits immediately after centre insert and before `fade_width` / `mirror_image_downwards()`.
- Palette-owned Bloom/Waveform branches now resolve colour via `palette_chroma_colour()` rather than summing multiple palette RGB samples into grey/white.
- WAVEFORM-FAST and WAVEFORM mirror repair in current source uses upper-half authoritative trace plus conditional `mirror_image_downwards()`, while non-mirrored operation preserves the full-strip oscilloscope path.
- WAVEFORM-HYBRID remains a separate centre-outward path using `waveform_shift_outward()` and optional `waveform_history`; the probe seeds waveform history when present.
- S2-S3 migration history split into: protected S2 content-capture boundary, generic S3 compile prep, K1.Lightwave reference detour, correction to firmware-v3 K1 hardware GPIOs, K1 hardware compile/upload evidence, and current dirty K1 hardware hardening.
- Current dirty K1 hardware hardening likely addresses absent Rotate8 and sweet-spot LEDC crash paths, but runtime proof remains incomplete for serial boot, PSRAM, I2S, LED output, and 120 FPS timing.
- `docs/s3-migration-prep.md` is stale against `tools/compile-k1-arduino.sh` for `LoopCore` / `EventsCore`.

## Artefact

- Created `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html`.
