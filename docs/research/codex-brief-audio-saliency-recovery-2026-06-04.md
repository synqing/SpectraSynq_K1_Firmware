---
abstract: "Codex Phase-1 brief (2026-06-04): scope recovery of ONE reliable, musically-salient audio primitive from firmware-v3's MusicalSaliency layer into the live SensoryBridge fork. READ-ONLY on both trees; output is a recovery PLAN doc only — no firmware edits. The fix for 'all tempo/onset output is corrupted on music' that perceptual_bloom exposed. Offloaded to Codex to preserve Claude budget."
---

# Codex task — scope the recovery of a reliable musical audio primitive

## Why this exists
The K1 is a music-reactive LED product. On 2026-06-04, the reference effect `perceptual_bloom` proved on-device that the **renderer is right** (alive, cohesive, "8.5 character") but the **audio feature layer is the wall**: raw onset/energy fire cleanly on isolated transients (clap, snap, shout) yet produce **chaos on continuous music**; the tempo tracker is ~14% accurate. Founder decision (load-bearing): **no effect may be wired to beat/tempo/onset until at least ONE audio primitive is reliable ON REAL MUSIC.** The Sensory-Bridge-derived fork lost firmware-v3's **musical-saliency** layer — the thing that turns raw loudness/onset into musically-meaningful events. Recover it.

## Task — PHASE 1: SCOPING / PLAN ONLY
**Do NOT modify any firmware.** Read-only on both trees; produce ONE plan document.

1. **Study v3's saliency layer (read-only)** at `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3/`:
   - `src/audio/contracts/MusicalSaliency.h`
   - `docs/audio-visual/SALIENCY_ARCHITECTURE_REVIEW.md`, `audio-visual-semantic-mapping.md`, `AUDIO_FEATURE_SURFACE_V2_CONTRACT.md`, `AUDIO_SYSTEM_ARCHITECTURE_VISUAL.md`
   - `src/audio/` (the AudioActor pipeline), `testbed/evaluation/l2_audiovisual.py`
   Extract **what musical-saliency computes** that converts raw loud/onset into musically-meaningful events (adaptive thresholding, musical-context gating, flux/novelty normalisation, AGC interplay, per-band saliency, etc.).
2. **Study the current fork's audio path (read-only)** at `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/audio/`: `sb_audio_snapshot.*`, `GDFT.h`, `i2s_audio.h`, `sb_onset_beat.*`, `sb_tempo.*`. Identify **exactly why it is clean on transients but chaotic on music** (the saliency gap) and what it already exposes.
3. **Pick the ONE primitive to recover FIRST** — the single most reliable-on-music, highest-leverage channel (candidates: a musically-salient onset/novelty; a normalised bass/energy envelope; a flux-saliency). Justify the pick over the alternatives.
4. **Spec the port:** how v3 computes it → how it maps onto the fork's single **~133 Hz** audio loop (NO main-sample-rate change — that is a STOP condition), which files, the minimal additive wiring, the cross-core/threading contract.
5. **Define VALIDATION ON REAL MUSIC** (the "calibrated scales" test): how to prove the primitive tracks the music, not noise, on the host harness (`scripts/regression-harness/`: `render_replay`, `novelty_from_wav.py`, the real-music fixtures / HarmonixSet wavs already in-repo) with a **concrete pass metric** — and this must pass BEFORE any effect is wired to it.
6. **Risks, blast radius (AP-class), and a sequenced plan** (Phase 2 = implement + validate, later, gated by the change-gate + on-device proof).

## Output
Write to `/Users/spectrasynq/SensoryBridge-main 9/docs/research/2026-06-04-audio-saliency-recovery-plan.md`:
the saliency gap; the chosen primitive + why; the port spec; the real-music validation method + pass metric; risks; the sequenced plan. Anchor every claim (file:line / commit / doc§). Flag if `MusicalSaliency` turns out richer or poorer than expected.

## Constraints
Read-only on the v3 repo AND on the live `SPECTRASYNQ_K1_FIRMWARE/` audio path — PLAN only, zero firmware edits this phase. British English. If a claim can't be grounded, mark it UNCERTAIN rather than asserting.
