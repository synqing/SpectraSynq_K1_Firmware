---
abstract: "Phase-1 read-only recovery plan for restoring one real-music-reliable audio saliency primitive into the live SensoryBridge audio path. Chooses musically-salient novelty/onset strength first; specifies minimal future port, validation metric, risks, and gates. No firmware changes in this phase."
---

# Audio Saliency Recovery Plan

Date: 2026-06-04  
Scope: PHASE-1 SCOPING ONLY, read-only on `/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3` and `SPECTRASYNQ_K1_FIRMWARE/audio/`.  
Donor tree observed: `Lightwave-Ledstrip @ 08532b0a`, branch `main`, dirty worktree.  
Live tree observed: `SensoryBridge-main 9 @ e017793`, branch `wf/integration`, dirty worktree.  

## Gate Outputs

Current truth:

- [FACT] Live firmware audio loop order is `acquire_sample_chunk()` -> `calculate_vu()` -> `process_GDFT()` -> `calculate_novelty()` -> `sb_audio_snapshot_update()` -> `sb_onset_beat_update()` -> `sb_tempo_update()` in `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:517-575`.
- [FACT] Live defaults are `SAMPLE_RATE=12800` and `SAMPLES_PER_CHUNK=96`, yielding `12800 / 96 = 133.33 Hz`; the default macros/initialiser are in `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:36` and `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:57-64`.
- [FACT] The donor v3 saliency surface exists as `MusicalSaliencyFrame` with harmonic, rhythmic, timbral, dynamic, overall, and dominant-type outputs in `firmware-v3/src/audio/contracts/MusicalSaliency.h:42-101`.
- [FACT] The requested protocol docs named by AGENTS.md are missing from this live checkout at `docs/protocol/k1-ws-contract.yaml` and `docs/protocol/k1-rest-contract.yaml`; no plan claim depends on them.

Change class:

- Phase-1 research plan only. No firmware implementation, upload, serial interaction, calibration, or runtime proof claim.

Files/seams touched:

- This document only: `docs/research/2026-06-04-audio-saliency-recovery-plan.md`.
- Future Phase-2 seams would be `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.*`, `sb_onset_beat.*`, possibly a new `sb_salient_novelty.*`, and host harness files under `scripts/regression-harness/`. No future sample-rate change is allowed.

Known breakage avoided:

- [FACT] No calibration command was run. Calibration commands require confirmed silence under the standing policy.
- [FACT] No v3 PipelineCore path is proposed; AGENTS.md states PipelineCore is broken and ESV11 is production-active.
- [FACT] No raw `bins256` promotion is proposed; v3 AFS v2 says `bins256` may remain internal/diagnostic/research but is not normal effect-authoring API in `firmware-v3/docs/audio-visual/AUDIO_FEATURE_SURFACE_V2_CONTRACT.md:34-57`.

State ownership:

- Future saliency state must be Core-0/audio-owned and value-copied to render consumers only. The live fork already uses this contract for onset/tempo with state on the Core-0 audio loop and value-copy reads under `portMUX` in `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.h:12-18`, `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp:134-137`, and `SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.cpp:52-55`.

Runtime proof required:

- Phase 2 cannot wire any effect to the recovered primitive until the host real-music metric in this plan passes. On-device/video proof remains later and separate from host proof.

Minimal edit plan:

- Add one audio-owned semantic primitive and host harness validation first. Do not rewire effects, AP mode, VP state, sample rate, or render code in the first implementation pass.

Explicit non-goals:

- No beat/tempo effect wiring.
- No main sample-rate or chunk-size change.
- No donor architecture wholesale import.
- No calibration, upload, serial monitor, or hardware write in Phase 1.

Stop conditions:

- Any requirement to change `SAMPLE_RATE` / `SAMPLES_PER_CHUNK`.
- Any need for silence calibration.
- Any validation result that passes synthetic/clap cases but fails real-music fixtures.
- Any attempt to promote raw FFT/bin arrays as the effect-facing API without the field-contract gate in `firmware-v3/docs/audio-visual/AUDIO_FEATURE_SURFACE_V2_CONTRACT.md:106-131`.

Relevant doctrine rules:

- [FACT] Tune I2S DMA/audio timing before algorithm tuning when sample rate/chunk/audio source changes; doctrine Rule 7 has that re-test trigger in `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official/docs/agent-outputs/analysis/sensory-bridge-lessons-doctrine.md:60-64`.
- [FACT] For this Goertzel workload, Q15/fixed-point performance claims are workload-bound; re-test if `NUM_FREQS`, sample rate, chunk size, or DSP method changes, per doctrine Rule 8 in `sensory-bridge-lessons-doctrine.md:66-70`.
- [FACT] Reference doctrine should live beside the code, not inside production build targets, per doctrine Rule 12 in `sensory-bridge-lessons-doctrine.md:90-94`.

K1 evidence touched:

- [FACT] Prior onset/beat-lite runtime evidence accepted Stage A event cadence but explicitly preserved broad-genre and human-perception risks in `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md:72-80` and `docs/forensics/2026-05-28-onset-beat-lite-runtime-evidence.md:120-128`.

North-star impact:

- This protects musical responsiveness by recovering one event/envelope that is stable on continuous music before any visual effect consumes beat/tempo/onset. That is directly aligned with the product north star: audio should drive meaningful visual behaviour, not merely make patterns busier.

Re-test triggers crossed:

- None in Phase 1 because no firmware changed. Phase 2 crosses AP/audio and host-harness gates, and later on-device proof if an effect consumes the primitive.

## Saliency Gap

[FACT] Donor v3 defines saliency as "what is perceptually important" across harmonic, rhythmic, timbral, and dynamic dimensions, with effects responding to the dominant type rather than to all signals equally (`firmware-v3/src/audio/contracts/MusicalSaliency.h:5-7`, `firmware-v3/src/audio/contracts/MusicalSaliency.h:31-41`, `firmware-v3/src/audio/contracts/MusicalSaliency.h:87-101`).

[FACT] Donor v3's semantic mapping document says raw audio should become musical saliency first: harmonic novelty via chord/key changes, rhythmic novelty via beat-pattern changes, timbral novelty via spectral flux/instrument changes, and dynamic novelty via RMS envelope/crescendo changes (`firmware-v3/docs/audio-visual/audio-visual-semantic-mapping.md:114-126`).

[FACT] Donor v3's `ControlBus::computeSaliency()` derives:

- harmonic novelty from chord confidence/root/type change (`firmware-v3/src/audio/contracts/ControlBus.cpp:875-895`);
- timbral novelty from absolute spectral-flux derivative against previous flux (`firmware-v3/src/audio/contracts/ControlBus.cpp:897-904`);
- dynamic novelty from absolute RMS derivative (`firmware-v3/src/audio/contracts/ControlBus.cpp:906-913`);
- rhythmic novelty from tempo lock/confidence/beat tick, or fallback fast flux when unlocked (`firmware-v3/src/audio/contracts/ControlBus.cpp:915-931`);
- smoothed outputs, overall weighted saliency, and dominant type (`firmware-v3/src/audio/contracts/ControlBus.cpp:933-984`).

[FACT] The live fork currently exposes a snapshot of peak/VU/novelty/spectral energy/low-mid-high/chroma strength/silence (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h:15-26`) and computes those from `waveform_peak_scaled`, `audio_vu_level`, `novelty_curve`, `spectrogram[]`, and simple thirds of `NUM_FREQS` (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp:24-70`).

[FACT] Live novelty is positive frame-to-frame spectrogram difference averaged over `NUM_FREQS`, square-rooted, and written to `novelty_curve` (`SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h:290-325`). That is a raw change detector, not a musical saliency field.

[FACT] Live onset acceptance combines fast/slow novelty, low-energy, and peak deltas with fixed thresholds plus a 240 ms refractory (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.cpp:167-213`). It does not maintain a median/adaptive programme threshold, per-band saliency confidence, or a real-music false-positive metric before publishing events.

[FACT] Live tempo explicitly consumes the novelty scalar, documents the exact 133.33 Hz AP loop and /3 decimation, and documents real-music weakness: host-measured Acc2 about 14 percent versus about 50 percent autocorrelation ceiling on the same novelty (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp:14-24`, `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp:50-54`).

[INFERENCE] This explains "clean on isolated transients but chaotic on music": isolated claps produce large single positive deltas that fixed threshold/refractory logic can accept, while continuous music produces dense spectral and peak deltas without a programme-level adaptive threshold, context confidence, or precision/recall gate.

## Chosen Primitive

Recover first: **MusicalSaliencyFrame-style four-axis saliency**.

Field name for Phase 2 contract draft: `sb_musical_saliency` plus optional event wrapper `sb_musical_saliency_event`.

Category:

- `sb_musical_saliency`: frame output, raw+smoothed harmonic/rhythmic/timbral/dynamic, plus overall saliency.
- `sb_musical_saliency_event`: event, strength/confidence/age/flags if promoted beyond the existing `SBOnsetBeatEvent` shape.

Why this first:

- [FACT] v3 treats flux/novelty as a reactive control surface: `flux` and `novelty` are listed as energy/reactive signals in `firmware-v3/docs/audio-visual/audio-visual-semantic-mapping.md:184-191`.
- [FACT] v3's richer onset detector uses log-spectral flux, median adaptive thresholding, causal peak picking, refractory gating, and per-band triggers (`firmware-v3/src/audio/onset/OnsetDetector.cpp:11-23`; `firmware-v3/src/audio/onset/OnsetDetector.h:93-130`).
- [FACT] The live fork already has the necessary low-risk integration seam: `SBAudioSnapshot` feeds both `sb_onset_beat_update()` and `sb_tempo_update()` after `calculate_novelty()` (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:564-575`).
- [FACT] The host harness already computes representative real-music spectral-flux novelty at 133.33 Hz from 12.8 kHz WAVs and states the exact native frame-rate relationship (`scripts/regression-harness/novelty_from_wav.py:17-29`, `scripts/regression-harness/novelty_from_wav.py:43-49`, `scripts/regression-harness/novelty_from_wav.py:60-120`).
- [INFERENCE] A reliable four-axis novelty/onset primitive is higher leverage than immediate tempo recovery because tempo already depends on novelty quality (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp:435-483`) and the brief blocks all beat/tempo/onset consumption until at least one primitive is reliable on real music.

Why not first:

- `tempo`: [FACT] the current tempo path has a documented real-music accuracy problem and its validation script scores Acc1/Acc2 against gold BPM (`scripts/regression-harness/tempo_accuracy.py:1-33`, `scripts/regression-harness/tempo_accuracy.py:150-176`). [INFERENCE] Tempo is downstream of novelty quality and will remain fragile if the input event stream is noisy.
- `normalised bass/energy envelope`: [FACT] live snapshot already exposes `low_energy`, `spectral_energy`, and `peak_scaled` (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h:17-23`). [INFERENCE] It helps intensity but does not solve the false event storm problem that blocks onset/tempo effects.
- `harmonic/chord saliency`: [FACT] donor harmonic saliency depends on chord root/type/confidence (`firmware-v3/src/audio/contracts/ControlBus.cpp:875-895`). [INFERENCE] The live fork's `chroma_strength` is only a max-over-sum bucketed chroma scalar (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp:56-70`), too thin for first recovery.

## Port Spec

### Donor Computation To Recover

Recover the **principle**, not the full v3 frame:

- [FACT] v3 `MusicalSaliencyFrame` mixes output fields with history/smoothing state (`firmware-v3/src/audio/contracts/MusicalSaliency.h:42-158`).
- [FACT] v3's own review calls that state pollution and recommends output-only frames with history/smoothing private to the producer (`firmware-v3/docs/audio-visual/SALIENCY_ARCHITECTURE_REVIEW.md:20-56`).
- [FACT] The same review says smoothing must use `alpha = 1 - exp(-dt / tau)` rather than hop-dependent alphas (`firmware-v3/docs/audio-visual/SALIENCY_ARCHITECTURE_REVIEW.md:59-103`).

Therefore Phase 2 should implement a live-fork-native producer whose private state is not published:

1. Input each AP frame: `SBAudioSnapshot` fields `novelty`, `low_energy`, `mid_energy`, `high_energy`, `spectral_energy`, `peak_scaled`, `silence`.
2. Maintain private Core-0 history:
   - rolling/EMA local floor for raw novelty;
   - local adaptive threshold or moving-mean subtraction, mirroring the host harness principle in `scripts/regression-harness/novelty_from_wav.py:93-110`;
   - dt-correct attack/release smoothing using `frame_ms` deltas;
   - refractory/holdoff separate from confidence.
3. Output one scalar:
   - `salient_novelty = clamp01(compressed(max(0, novelty - local_context_floor)) / adaptive_scale)`;
   - `confidence = contrast / (contrast + floor_energy + epsilon)` or equivalent, only after host metric selection;
   - `age_ms` if promoted to an event.

### Live Mapping At 133 Hz

- [FACT] The live loop produces one `SBAudioSnapshot` after `calculate_novelty()` per AP frame (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:564-575`).
- [FACT] `sb_tempo.cpp` already treats this as `CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK = 12800 / 96 = 133.33 Hz` and forbids coefficient mismatch by exact frame-count decimation (`SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp:14-24`, `SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp:452-465`).

Phase 2 mapping:

- Do not change `DEFAULT_SAMPLE_RATE`, `CONFIG.SAMPLE_RATE`, or `CONFIG.SAMPLES_PER_CHUNK`.
- Run `sb_musical_saliency_update()` once per AP frame immediately after `sb_audio_snapshot_update()` and before existing onset/tempo consumers, or inside `sb_onset_beat_update()` if the chosen implementation is strictly contained there.
- Keep per-frame cost O(1) or O(small fixed bands); do not scan raw 80-bin/256-bin arrays from render code.
- Publish by value under the existing spinlock pattern if a new read API is needed.

### Minimal Additive Wiring

Preferred Phase-2 minimal path:

1. Add `sb_musical_saliency.h/.cpp` or extend `sb_onset_beat.*` only if that keeps the public surface smaller.
2. Add a struct:

```cpp
struct SBSaliencyAxisFrame {
  float harmonicNovelty;
  float rhythmicNovelty;
  float timbralNovelty;
  float dynamicNovelty;
  float harmonicNoveltySmooth;
  float rhythmicNoveltySmooth;
  float timbralNoveltySmooth;
  float dynamicNoveltySmooth;
  float overallSaliency;
  uint8_t dominantType;
};

struct SBSaliencyEvent {
  uint32_t frame_ms;
  float overallSaliency;
  bool salient;
  float confidence;
  uint16_t age_ms;
  uint16_t flags;
};
```

3. Call update from the Core-0 audio loop using the current `SBAudioSnapshot`.
4. Initially consume only in host harness and telemetry/debug evidence; no effect reads it until the metric passes.
5. If later promoted to effect-facing API, draft the required field contract from `AUDIO_FEATURE_SURFACE_V2_CONTRACT.md:106-131`.

Cross-core/threading contract:

- Producer state remains private to Core-0.
- Renderer reads only a value-copy snapshot.
- No heap, `String`, `new`, `malloc`, or render-path extraction.
- If timing/causality proof is claimed later, MabuTrace trace-dev is required by the repository instrumentation boundary; scalar host metrics alone do not prove audio-to-render causality.

## Real-Music Validation

Validation must prove the primitive tracks music, not isolated transients.

Existing substrate:

- [FACT] `novelty_from_wav.py` converts 12.8 kHz mono WAV into one novelty sample per 96-sample hop, i.e. 133.33 Hz, and refuses sample-rate mismatch (`scripts/regression-harness/novelty_from_wav.py:17-29`, `scripts/regression-harness/novelty_from_wav.py:69-72`).
- [FACT] `tempo_accuracy.py` already joins HarmonixSet WAVs to gold BPM metadata and beat/downbeat files, then scores Acc1/Acc2 (`scripts/regression-harness/tempo_accuracy.py:1-33`, `scripts/regression-harness/tempo_accuracy.py:60-117`, `scripts/regression-harness/tempo_accuracy.py:150-176`).
- [FACT] This checkout has 36 local `audio_12k8/*.wav` files under the path used by the harness.
- [FACT] The L2 evaluator contains salience-weighted correlation and onset response concepts for visual validation later (`firmware-v3/testbed/evaluation/l2_audiovisual.py:197-245`, `firmware-v3/testbed/evaluation/l2_audiovisual.py:151-194`).

Phase-2 host harness addition:

- Add a replay script that runs the exact future `sb_musical_saliency` logic on the `novelty_from_wav.py` output plus optional RMS/silence.
- Use HarmonixSet beat/downbeat annotations as real-music event ground truth through the same GT directory used by `tempo_accuracy.py`.
- Score only frames after warmup and outside silence.

Concrete pass metric:

1. **Event precision:** at least 0.65 of emitted salient-onset events fall within +/-70 ms of a gold beat or downbeat on the 36 HarmonixSet WAVs.
2. **Beat recall:** at least 0.45 of gold beats/downbeats have one salient event within +/-70 ms.
3. **Storm control:** emitted events stay between 40 and 180 events/minute on non-silent music and below 12 events/minute in silence/control windows. The existing event-storm threshold is 240 events/minute in `scripts/regression-harness/onset_beat_event_metrics.py:24`.
4. **Tempo uplift control:** feeding `sb_tempo` with the new salient novelty must improve `tempo_accuracy.py` in-range Acc2 by at least +20 percentage points over the current novelty baseline, or the primitive is not good enough to unblock tempo/effect wiring. The existing tempo script reports Acc1/Acc2 and the detector-vs-autocorrelation ceiling (`scripts/regression-harness/tempo_accuracy.py:251-345`).

This is deliberately stricter than "looks responsive to claps". A primitive passes only if it survives continuous real music and improves a downstream musical task before visual consumers are wired.

## Risks And Blast Radius

AP-class risks:

- [FACT] The future work touches AP/audio code in the live loop. That crosses the K1 AP/audio gate; Phase 2 requires host tests and then on-device proof.
- [FACT] v3 review says saliency state must not be leaked inside published frames (`firmware-v3/docs/audio-visual/SALIENCY_ARCHITECTURE_REVIEW.md:20-56`).
- [FACT] AFS v2 requires any new production field to have a field contract, fixture test, failure behaviour, validity flags, and promotion gate (`firmware-v3/docs/audio-visual/AUDIO_FEATURE_SURFACE_V2_CONTRACT.md:106-131`).

Failure modes:

- Over-fitting to HarmonixSet and missing live room/mic artefacts.
- Suppressing valid syncopated or off-beat musical events by using beat annotations too narrowly.
- Inflating tempo accuracy by smoothing so heavily that latency becomes visually late.
- Accidentally changing `sb_tempo` rather than proving the primitive independently.
- Copying donor v3's state-in-frame design rather than porting the saliency idea.

Mitigations:

- Keep Phase 2 additive and default-unconsumed.
- Use precision, recall, event-rate, and tempo-uplift together; no single metric closes the gate.
- Preserve raw current novelty in the harness so before/after comparisons are deterministic.
- Treat on-device validation as later evidence, not implied by host metrics.

## Sequenced Plan

Phase 2A - contract and harness:

1. Draft `sb_musical_saliency` field contract from `AUDIO_FEATURE_SURFACE_V2_CONTRACT.md:106-131`.
2. Add host replay for the candidate algorithm using existing HarmonixSet 12.8 kHz WAVs and gold beat/downbeat files.
3. Produce a baseline report for current raw `novelty_curve` as the control.

Phase 2B - implementation:

1. Add producer-private saliency state in audio-owned code only.
2. Add a value-copy read API or extend `SBOnsetBeatEvent` only after the host harness is green.
3. Do not wire any effect.
4. Run unit/host harness and `pio run -e k1_hardware`.

Phase 2C - validation gate:

1. Run the real-music metric above.
2. Run the tempo uplift control through `tempo_accuracy.py`.
3. If scalar/timing questions become causal, capture trace-dev evidence; do not substitute scalar logs for causality.

Phase 3 - on-device proof:

1. Verify hardware identity before any serial/upload action.
2. Capture runtime scalar evidence under real music.
3. Only after the primitive passes, choose one low-risk visual consumer for A/B.
4. Require Captain/video perceptual judgement before claiming musical improvement.

## Richer Or Poorer Than Expected

[FACT] `MusicalSaliency` is richer than a raw onset detector because it models four novelty dimensions, overall saliency, and dominant saliency type (`firmware-v3/src/audio/contracts/MusicalSaliency.h:24-41`, `firmware-v3/src/audio/contracts/MusicalSaliency.h:87-101`).

[FACT] It is also poorer/less production-ready than a clean port target because the donor frame carries derivative history and smoothing state inside the published frame (`firmware-v3/src/audio/contracts/MusicalSaliency.h:103-158`), and the v3 review explicitly calls that a state-pollution issue (`firmware-v3/docs/audio-visual/SALIENCY_ARCHITECTURE_REVIEW.md:20-56`).

[INFERENCE] The right recovery is not "import MusicalSaliency.h"; it is "recover one producer-owned, dt-correct, real-music-validated saliency primitive first".

## One Primitive Decision

Recover **musically-salient novelty/onset strength** first. It is the primitive most directly upstream of onset, beat, tempo, and visual accent decisions, and it has an existing live seam plus an existing real-music host fixture path.
