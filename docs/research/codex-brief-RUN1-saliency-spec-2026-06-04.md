---
abstract: "Codex Run-1 (2026-06-04): BOUNDED spec pass. Read ONLY the small donor excerpt + fork audio header (the prior run overflowed at 249k tokens by reading too much), revise the saliency recovery plan to the verified MusicalSaliency donor, and write a SELF-CONTAINED sb_musical_saliency implementation spec so a later run can implement without re-reading the v3 architecture. Read-only; no firmware edits."
---

# Codex Run-1 — bounded SPEC for the MusicalSaliency recovery

## Why bounded
The prior run **overflowed its context window** (249k tokens → `context_length_exceeded`) by reading the whole v3 audio architecture + the fork + trying to implement + validate at once. This run does ONLY the read-light spec work.

## READ-BUDGET DISCIPLINE (mandatory — do NOT exceed)
Read ONLY the following. **Do NOT** open entire large files, **do NOT** explore the tree, **do NOT** read ControlBus.cpp in full.
1. v3 donor struct: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3/src/audio/contracts/MusicalSaliency.h` — full (it is small).
2. v3 producer block: `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3/src/audio/contracts/ControlBus.cpp` — **ONLY lines 855–980** (`sed -n '855,980p' <file>`). This is the saliency compute. Do NOT read the rest of that file.
3. fork available inputs: `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h` — full (small), to see the fields the fork exposes.
4. fork input mapping: `grep -nE "flux|rms|energy|chroma|centroid|onset|novelty|bass" /Users/spectrasynq/SensoryBridge-main\ 9/SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h /Users/spectrasynq/SensoryBridge-main\ 9/SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.h` — grep only, do not full-read.

## Task (read-only; write 2 docs; NO firmware edits)
You are on branch `wip/audio-saliency-recovery` already. 
1. **Revise** `docs/research/2026-06-04-audio-saliency-recovery-plan.md`: replace the phantom `sb_salient_novelty`/`sb_salient_onset` with the verified donor — `MusicalSaliencyFrame` (4 axes harmonic/rhythmic/timbral/dynamic, each raw + smoothed, + `overallSaliency`) + `SaliencyTuning`, producer at `ControlBus.cpp:855–980`. Keep the validation metric.
2. **Write a SELF-CONTAINED implementation spec** to `docs/research/2026-06-04-sb-musical-saliency-IMPL-SPEC.md` that a later implementer can follow using ONLY the spec + the named fork files (no re-reading v3). It must contain:
   - the exact `sb_musical_saliency.h` struct (4 axes + smoothed + `overallSaliency`) and the `SaliencyTuning` constants **with v3's actual values** (rise/fall times, thresholds, weights — transcribe them);
   - the per-hop compute as concrete C/pseudocode: harmonic←chord/chroma-centroid change, timbral←flux derivative, dynamic←rms/energy derivative, rhythmic←beat-spike/fast-flux; asymmetric smooth each; `overallSaliency` = weighted sum;
   - **the fork input mapping** resolved: which `sb_audio_snapshot` field feeds each axis; where the fork LACKS a v3 input, the documented PROXY (e.g. chromagram-centroid change for harmonic) — flagged;
   - the salient-EVENT output definition (overallSaliency adaptive-threshold crossing) for validation;
   - the wiring point (`SPECTRASYNQ_K1_FIRMWARE.ino` after line 575, additive) + the read API (`sb_musical_saliency_read()`, portMUX);
   - the validation metric (carry it forward verbatim).

## Constraints
v3 repo READ-ONLY. NO firmware edits this run (spec only). Stay within the read budget above. Commit both docs to `wip/audio-saliency-recovery`. British English; anchor claims. Final message ≤6 lines: spec doc path, the 4 axes + their fork-input mapping, any proxy used, and confirm read budget respected.
