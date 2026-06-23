---
abstract: "Codex Run-2 (2026-06-04): implement sb_musical_saliency from the self-contained Run-1 SPEC + validate on HarmonixSet against the metric. Read-light (spec + only the fork files edited; NO v3 re-reads — that caused the 249k overflow). Additive only, no main-rate change. Codex does NOT commit (sandbox blocks .git); orchestrator commits after review."
---

# Codex Run-2 — implement + validate the saliency primitive

## Read-budget (mandatory — prior all-in-one run overflowed at 249k)
Read ONLY: the spec `docs/research/2026-06-04-sb-musical-saliency-IMPL-SPEC.md` (self-contained — it captured the v3 algorithm; do NOT re-read the v3 repo at all), plus the exact fork files you must edit/reference: `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h`, `audio/sb_onset_beat.h`, the `render_lightshow_for_channel`/post-line-575 region of `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`, and `scripts/regression-harness/` (the harness + HarmonixSet fixtures). Do NOT explore broadly.

## Guardrails
You are on branch `wip/audio-saliency-recovery`. ADDITIVE only — nothing existing altered, NO main-sample-rate change. **Do NOT git commit** (your sandbox blocks `.git` writes; the orchestrator commits after review) — just leave all files on disk. NO flash. Emit the change-gate preflight first.

## Task
1. **Implement** per the spec: create `SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.{h,cpp}` (the 4-axis `MusicalSaliencyFrame` + `SaliencyTuning` constants + per-hop compute + asymmetric smoothing + weighted `overallSaliency` + salient-event threshold), wire `sb_musical_saliency_update(sb_audio_snapshot_read())` additively after `.ino:575`, expose `sb_musical_saliency_read()` (value-copy via portMUX). State isolated; no heap in AP path; tau in seconds.
   - **Field-reality check:** if a field the spec names (`chroma_strength`/`novelty`/`spectral_energy`/`beat`/`beat_confidence`) does NOT exist in the fork, the build will fail — adapt to the REAL field present in `sb_audio_snapshot.h`/`sb_onset_beat.h` and note the substitution. Do NOT fabricate fields.
2. **Validate on real music:** extend `scripts/regression-harness/` with a host scorer that runs HarmonixSet WAVs through the fork's GDFT→saliency producer (host g++ build) and scores the salient-event output vs HarmonixSet beat/downbeat annotations. Metric: event precision ≥0.65; beat/downbeat recall ≥0.45 within ±70 ms; 40–180 events/min on music; <12/min in silence. Deterministic; report ACTUAL numbers per criterion.
3. **Gate:** `~/.local/bin/pio run -e k1_hardware` and `python3 -m pytest tests/` — run both, report GREEN/RED. (Do not commit.)
4. **Write** `docs/research/2026-06-04-audio-saliency-phase2-RESULT.md`: change-gate block, files added, MEASURED metric vs target (PASS/FAIL per criterion), any field substitutions, build/test results, deviations.

## Final message (≤8 lines)
Files written; build + pytest result; the MEASURED metric verdict (PASS/FAIL per criterion); any spec field that didn't exist + what you substituted; confirm no existing behaviour changed and no commit made.

## Constraints
Read-light (spec + named fork files only; NO v3 reads). Additive, no main-rate change, no commit, no flash. If the metric is NOT met, report it honestly — a measured shortfall is the point of this run.
