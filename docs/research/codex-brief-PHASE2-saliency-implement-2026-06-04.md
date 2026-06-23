---
abstract: "Codex Phase-2 brief (2026-06-04): revise the saliency recovery plan with the VERIFIED donor (v3 MusicalSaliency 4-axis model / ControlBus producer), then implement it additively onto the live SensoryBridge fork on an isolated wip worktree, validate against the real-music pass metric, and report. AP-class — additive only, no main-rate change, no merge/flash. Founder-authorised autonomous Codex execution."
---

# Codex Phase-2 — recover the MusicalSaliency primitive into the live fork (revise → implement → validate)

## Authorisation + HARD GUARDRAILS (read first)
The founder authorised autonomous execution of this **AP-class** change on Codex. Non-negotiable:
- Work ONLY in an **isolated git worktree on a new branch** `wip/audio-saliency-recovery`, created from the CLEAN main line `feat/gdft-harness` (NOT `wf/integration`). Create it with:
  `git -C "/Users/spectrasynq/SensoryBridge-main 9" worktree add -b wip/audio-saliency-recovery "/Users/spectrasynq/sb-saliency-wt" feat/gdft-harness` — do ALL work, builds, and commits in `/Users/spectrasynq/sb-saliency-wt`. Leave the main checkout undisturbed.
- **ADDITIVE ONLY.** Add the saliency channel ALONGSIDE the existing audio path. Do NOT remove, replace, or alter existing onset/energy/novelty/tempo behaviour — nothing existing may regress.
- **NO change** to the main sample rate, `SAMPLES_PER_CHUNK`, or the GDFT lattice. That is a STOP condition.
- **Change-gate preflight** (emit before editing): change class · files/seams touched · known-breakage-avoided · state ownership · runtime-proof-required · minimal-edit-plan · explicit non-goals · stop-conditions. Doctrine: centre-origin/visual unaffected; no calibration command fired; read-only on v3.
- **compile ≠ runtime proof for AP changes.** The HOST metric (Step 3) is the objective gate; on-device is the founder's later eyes-on. **If the metric is NOT met, report the shortfall honestly — never fabricate success.** A failed metric is a valid, important outcome.
- NO merge, NO flash, NO push.

## Step 1 — Revise the plan (correct the donor)
`docs/research/2026-06-04-audio-saliency-recovery-plan.md` named phantom symbols `sb_salient_novelty`/`sb_salient_onset` that DO NOT EXIST in v3. Correct it to the VERIFIED donor (canonical build `esp32dev_audio_esv11_k1v2_32khz`, v3 `main` @ `08532b0a`):
- `firmware-v3/src/audio/contracts/MusicalSaliency.h` — `MusicalSaliencyFrame` (4 axes: harmonic/rhythmic/timbral/dynamic, each raw + smoothed, + `overallSaliency`), `SaliencyTuning` (per-axis rise/fall, thresholds, weights), `isSalient()`/`getNovelty()`.
- `firmware-v3/src/audio/contracts/ControlBus.cpp:872-970` — the ACTIVE producer: harmonicNovelty←chord-root/type change; timbralNovelty←spectral-flux derivative; dynamicNovelty←RMS derivative; rhythmicNovelty←beat-spike/fast_flux; each asymmetric-smoothed; `overallSaliency` = weighted sum.
Update the plan to cite these anchors and recover the **4-axis model** (not a single novelty/onset). Keep the validation metric.

## Step 2 — Implement (port the producer, additive)
- New fork files `SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.{h,cpp}`: the 4-axis `MusicalSaliencyFrame` + `SaliencyTuning` constants + the per-hop compute, sourcing inputs from the fork's existing `sb_audio_snapshot`/`GDFT.h` (flux/novelty, spectral_energy/RMS, chromagram, onset). Map v3's `frame.flux`/`frame.rms`/`chord` to the fork's equivalents; where the fork LACKS an input (e.g. explicit chord detection), derive a documented proxy (e.g. chromagram-centroid change for harmonic novelty) and MARK it.
- Wire `sb_musical_saliency_update(sb_audio_snapshot_read())` into the Core-0 AP loop ADDITIVELY (alongside `sb_onset_beat_update`/`sb_tempo_update`, after `.ino:575`); expose `sb_musical_saliency_read()` (value-copy via portMUX, never a semaphore). No existing call changed.
- Expose the candidate reliable primitive: a **salient-event** output (overallSaliency, or rhythmicNovelty, crossing an adaptive threshold) — this is what Step 3 validates.
- All state isolated (no shared file-scope statics that cross channels); no heap in any AP-called path; all time constants in SECONDS (rate-agnostic, 133.33 Hz).

## Step 3 — Validate ON REAL MUSIC (the calibrated-scales gate)
Extend `scripts/regression-harness/` with a host scorer: run HarmonixSet WAVs through the fork's GDFT→saliency producer (host g++ build) and score the salient-event output against HarmonixSet beat/downbeat annotations. **Pass metric (report ACTUAL numbers vs each):**
- event precision ≥ 0.65; beat/downbeat recall ≥ 0.45 within ±70 ms;
- 40–180 salient-events/min on non-silent music; < 12/min on silence/control;
- if saliency feeds tempo: +≥20 pp in-range Acc2 uplift.
Deterministic. Report per-fixture; if short, by how much + likely cause.

## Step 4 — Gate + commit + report
- `~/.local/bin/pio run -e k1_hardware` + `python3 -m pytest tests/` GREEN in the worktree. Commit to `wip/audio-saliency-recovery` (host-green; on-device eyes-on tracked, non-blocking). NO merge/flash/push.
- Write a result doc `docs/research/2026-06-04-audio-saliency-phase2-RESULT.md` (in the worktree): the change-gate block, files added, the MEASURED metric vs target (PASS/FAIL per criterion), any fork-input gaps + proxies, deviations.
- FINAL message (≤8 lines): worktree path + branch; new files; the measured metric verdict (PASS/FAIL per criterion); whether any v3 input was missing + how handled.

## Constraints
v3 repo READ-ONLY. Live fork: additive only, isolated wip worktree off `feat/gdft-harness`, no main-rate change, no merge/flash/push. British English; anchor every claim. If you cannot hit the metric, REPORT IT — do not fabricate.
