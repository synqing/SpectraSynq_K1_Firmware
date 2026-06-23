---
abstract: "Codex bounded search (2026-06-04): WHY does the MusicalSaliency 4-axis detector track music in v3's AP but score near-zero on the fork (precision 0.21, recall 0.003, fires more in silence than music)? Find the SPECIFIC v3 AP-design property (feature conditioning / scale calibration / frame-rate / gating stage) the fork's port omitted. Read-only, read-budgeted, no firmware edits."
---

# Codex — why v3's AP makes saliency work (and the fork doesn't)

## The puzzle
We ported v3's `MusicalSaliency` 4-axis math (harmonic/rhythmic/timbral/dynamic) onto the fork verbatim, with verbatim `SaliencyTuning` constants. On 36 HarmonixSet WAVs it FAILED: precision 0.21, recall 0.003, and it fires MORE in silence (24/min) than music (18/min). In v3 the SAME saliency drove real shipped effects (Saliency Bloom, the Enhanced pack). **So the difference is in the AP that FEEDS saliency, not the saliency formula.** Find the specific v3 AP property the fork lacks.

## READ-BUDGET (mandatory — a prior run overflowed at 249k; stay bounded)
Read ONLY:
1. v3 `firmware-v3/docs/audio-visual/SALIENCY_ARCHITECTURE_REVIEW.md` (full) and `firmware-v3/docs/audio-visual/AUDIO_FEATURE_SURFACE_V2_CONTRACT.md` (the feature-definition sections).
2. v3 `firmware-v3/src/audio/contracts/ControlBus.cpp` — ONLY the regions that COMPUTE/CONDITION the saliency inputs (flux, rms, fast_flux, chord). Find them with `grep -nE "flux|rms|fast_flux|chord|agc|normali|log|gate|clamp"` then read only those line-windows. Do NOT full-read the file.
3. v3 feature producer: `grep -rnE "flux|rms|fast_flux|novelty|agc|normali|log2|silence" firmware-v3/src/audio/` to find how the ESV11/32kHz AP computes + conditions these (AGC? log-domain? fixed-scale normalisation? silence gate? frame rate 32kHz/125Hz?). Read only the key producer.
4. Fork contrast: `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h` + `grep -nE "novelty|chroma_strength|spectral_energy|agc|normali|log|silence|clamp"` across `SPECTRASYNQ_K1_FIRMWARE/audio/{GDFT.h,sb_audio_snapshot.cpp,i2s_audio.h}` — to see how the fork's features are scaled/conditioned (12800Hz/133Hz).

## Answer these specifically
1. Are v3's saliency inputs CONDITIONED before saliency — AGC, log-domain, fixed-scale normalisation, silence-gating — in a way the fork's raw `novelty`/`chroma_strength`/`spectral_energy` are NOT?
2. Is `SaliencyTuning` (the derivative thresholds + weights) calibrated to v3's feature SCALES/UNITS, such that transcribing it verbatim onto the fork's differently-scaled features makes every threshold wrong → misfire (explains silence>music)?
3. Does v3's 32kHz/125Hz framing vs the fork's 12800Hz/133Hz materially change the flux/novelty statistics the thresholds assume?
4. Is there a v3 AP stage BETWEEN raw features and saliency (adaptive/normalising threshold, confidence, false-positive gate) that the port omitted?

## Output
Write `docs/research/2026-06-04-why-v3-AP-saliency-works.md`: the SPECIFIC v3 AP property/properties that make saliency track music, the precise fork gap, and the concrete fix (what to normalise / log / gate / re-scale / re-tune so the fork's features match what the saliency thresholds expect). Anchor every claim. Final message ≤6 lines: the ONE key AP difference + the concrete fix.

## Constraints
Read-only, bounded reads (no overflow), NO firmware edits, British English. If the cause is ambiguous, give the ranked most-likely with evidence.
