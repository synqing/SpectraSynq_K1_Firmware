---
abstract: "Manifest for the tempo-tracking-refactor working set: point-in-time COPIES (not moves) of the 9 audio firmware files that make up the K1 tempo + beat + onset stack, consolidated 2026-06-05 from SPECTRASYNQ_K1_FIRMWARE/audio/ at branch wip/audio-saliency-recovery HEAD e226b25. The LIVE, COMPILED source remains in SPECTRASYNQ_K1_FIRMWARE/audio/ — this folder is NEVER built (outside the PlatformIO src_filter); edit the live tree, use these for reference/diffing. Maps each file to the issue IDs from the 2026-06-05 known-issues register. Excludes sb_musical_saliency (closed RC-4 lane). Records the .ino integration seam (not copied)."
---

# Tempo-Tracking Refactor — Working-Set Manifest

**Created:** 2026-06-05 · **Source branch/HEAD:** `wip/audio-saliency-recovery` @ `e226b25`
**Consolidated by:** agent:CTO, on Captain's instruction to gather the affected audio files.

> ⚠️ **These are COPIES, not moves.** The originals are untouched in `SPECTRASYNQ_K1_FIRMWARE/audio/`
> and the firmware build is unchanged. **This `docs/forensics/` folder is outside the PlatformIO
> `build_src_filter` and is NEVER compiled.** Treat these as a point-in-time reference snapshot for
> the refactor. If you draft refactored versions here, they must be ported back into
> `SPECTRASYNQ_K1_FIRMWARE/audio/` to take effect. Re-sync from the live tree before relying on a copy
> (the live source moves; a forensic copy goes stale — verify against `SPECTRASYNQ_K1_FIRMWARE/audio/`).

## Files in this set (9)

### Core — the affected stack (issues live here; these get edited in the refactor)
| File | Bytes | Owns | Known-issue IDs (see register) |
|------|------|------|-------------------------------|
| `sb_tempo.cpp` | 34409 | tempo selection (ACF + harmonic-comb + tactus prior), confidence, beat-phase flywheel | T1–T14 (range cap, prior bias, comb, **T5 confidence P0**, T8/T9 PLL, T11 phase tick) |
| `sb_tempo.h` | 1835 | `SBTempoEvent` (bpm/phase01/confidence/locked), public API | T12 (no downbeat/bar field) |
| `sb_onset_beat.cpp` | 8883 | onset detection + onset-gated beat events | ON-07–ON-17 (fixed thresholds, refractory, ±25% interval, **ON-10 beat=phase tick**) |
| `sb_onset_beat.h` | 171 | `SBOnsetBeatEvent`, `sb_onset_beat_read()` | ON-13 (event window not edge) |
| `sb_audio_snapshot.cpp` | 2466 | per-frame audio snapshot, novelty read, low/mid/high band scalars | ON-05 (stale ring), **ON-06 (3 pre-summed scalars)**, ON-14 (bands not Hz) |
| `sb_audio_snapshot.h` | 772 | `SBAudioSnapshot` struct (the carrier into the Director — has NO beat fields) | ON-06; Director-wiring seam |
| `GDFT.h` | 13812 | spectrogram + AGC + `calculate_novelty()` (the novelty curve feeding tempo ACF) | **ON-01 (raw energy flux), ON-02 (AGC [0,1] clamp flattens onsets → host≠device)**, ON-03, ON-04, T14 |

### Signal-chain context (dependencies — read to refactor correctly, not necessarily edited)
| File | Bytes | Why included |
|------|------|--------------|
| `i2s_audio.h` | 27565 | I2S input + DC removal + AGC origin — upstream of the novelty/onset path; load-bearing for the ON-02 device-AGC fidelity fix |
| `audio_transfer.h` | 21398 | audio data carrier / cross-surface transfer struct — the path audio features travel to consumers |

## Excluded (deliberate)
- `sb_musical_saliency.{cpp,h}` — the **instantaneous-saliency lane, CLOSED at RC-4** (structure-blind, cross-confirmed). Not part of tempo/beat/onset tracking. Say the word and I'll add it.

## Integration seam (NOT copied — lives in the main sketch)
The tempo/beat/onset chain is wired in `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` (the file open in your IDE), not in `audio/`:
- AP-loop chain `snapshot → onset → tempo`: `.ino:498–532` (`sb_tempo_update()` at `:532`).
- Beat seam: `.ino:661–669` — `smart_event` (`SBOnsetBeatEvent`) is read for visual hooks but **dropped** at the `sb_smart_director_tick()` call (the Director is beat-blind).
- Consumer: `SPECTRASYNQ_K1_FIRMWARE/director/sb_smart_director.cpp` (selection ignores tempo/onset — register §3 / Director-wiring task).

## Cross-references
- **Known-issues register:** `docs/research/validation/2026-06-05-tempo-beat-onset-known-issues.md` (38 issues, the source of the ID columns above).
- **Corrected-truth record:** `docs/research/validation/2026-06-04-RECONCILIATION.md`.
- **Host gates** (separate, not in this folder): `scripts/regression-harness/{tempo_accuracy,tempo_replay,bt_acf_4way}.py`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:CTO | Created — manifest for the tempo-tracking-refactor working set; 9 audio files copied (not moved) from SPECTRASYNQ_K1_FIRMWARE/audio/ @ e226b25, mapped to known-issue IDs; saliency excluded; .ino integration seam recorded. Originals + build untouched. |
