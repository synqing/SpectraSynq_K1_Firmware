---
author: Codex
abstract: "Run-1 bound spec to recover v3 MusicalSaliency donor semantics in the SensoryBridge fork without implementation in this pass."
---

# SB Musical Saliency Implementation Spec (Run-1)

## Verified donor and fork sources
- Donor contract: `firmware-v3/src/audio/contracts/MusicalSaliency.h`.
- Donor compute: `firmware-v3/src/audio/contracts/ControlBus.cpp` (bounded slice `855-980`).
- Fork input surface: `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h`.
- Fork auxiliary: `SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.h` (`SBOnsetBeatEvent` and `sb_onset_beat_read()`), `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` novelty emission.

## 1) Public header: `sb_musical_saliency.h`

```cpp
#pragma once
#include <stdint.h>

enum class SBSaliencyType : uint8_t {
    HARMONIC = 0,
    RHYTHMIC = 1,
    TIMBRAL  = 2,
    DYNAMIC  = 3,
};

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
    uint8_t dominantType; // SBSaliencyType
};

struct SaliencyTuning {
    float harmonicRiseTime   = 0.15f;
    float harmonicFallTime   = 0.80f;
    float rhythmicRiseTime   = 0.05f;
    float rhythmicFallTime   = 0.30f;
    float timbralRiseTime    = 0.10f;
    float timbralFallTime    = 0.50f;
    float dynamicRiseTime    = 0.08f;
    float dynamicFallTime    = 0.40f;

    float harmonicChangeThreshold = 0.5f;
    float fluxDerivativeThreshold = 0.05f;
    float rmsDerivativeThreshold  = 0.02f;
    float beatVarianceThreshold   = 0.15f;

    float harmonicWeight = 0.25f;
    float rhythmicWeight = 0.30f;
    float timbralWeight  = 0.20f;
    float dynamicWeight  = 0.25f;
};

struct SBSaliencyEvent {
    uint32_t frameMs;
    bool salient;
    float overallSaliency;
    float adaptiveThreshold;
    uint16_t ageMs;
    uint16_t flags;
};

#ifdef __cplusplus
extern "C" {
#endif
void sb_musical_saliency_update(const SBAudioSnapshot& audio, const SBOnsetBeatEvent* onset);
SBSaliencyAxisFrame sb_musical_saliency_read();
bool sb_musical_saliency_read_event(SBSaliencyEvent* out, bool clear_after_read = false);
#ifdef __cplusplus
}
#endif
```

## 2) Fork-to-axis input mapping (with missing-input proxies)

- harmonic axis (`harmonicNovelty`):
  - direct v3 input: chord root/type change + confidence (`ControlBus.cpp` lines 875-895)
  - fork input: `SBAudioSnapshot::chroma_strength`
  - proxy: `abs(curr_chroma_strength - prev_chroma_strength)` (proxy for chroma-centroid change)
  - status: **PROXY** because fork lacks chord root/type and confidence.
- rhythmic axis (`rhythmicNovelty`):
  - direct v3 input: `tempoLocked`, `tempoConfidence`, `tempoBeatTick`, `fast_flux` (`ControlBus.cpp` 915-931)
  - fork input: `SBOnsetBeatEvent::beat`, `SBOnsetBeatEvent::beat_confidence`, `SBAudioSnapshot::novelty`
  - proxy: if onset beat is present use `beat + 0.5f*beat_confidence` else fallback `0.5f * abs(novelty - prev_novelty)`; this is **FAST_FLUX proxy**.
- timbral axis (`timbralNovelty`):
  - direct v3 input: spectral flux derivative (`ControlBus.cpp` 897-904)
  - fork input: `SBAudioSnapshot::novelty` (from GDFT novelty output)
  - status: direct use as `fluxDelta` surrogate.
- dynamic axis (`dynamicNovelty`):
  - direct v3 input: RMS derivative (`ControlBus.cpp` 906-913)
  - fork input: `SBAudioSnapshot::spectral_energy` (and optionally `peak_scaled`)
  - proxy: `abs(curr_spectral_energy - prev_spectral_energy)` / `rmsDerivativeThreshold` (RMS surrogate).

## 3) Per-hop compute (C/pseudocode)

```cpp
static float clamp01(float x) { return (x < 0.f ? 0.f : (x > 1.f ? 1.f : x)); }
static float asymmetricSmooth(float current, float target, float riseTime, float fallTime, float dtSeconds) {
    float riseAlpha = 1.0f - expf(-dtSeconds / riseTime);
    float fallAlpha = 1.0f - expf(-dtSeconds / fallTime);
    float alpha = (target >= current) ? riseAlpha : fallAlpha;
    return current + (target - current) * alpha;
}

void sb_musical_saliency_update(const SBAudioSnapshot& a, const SBOnsetBeatEvent* onset) {
    float nowMs = (float)millis(); // or passed-in frame_ms
    float dtMs = nowMs - g_saliencyState.prevFrameMs;
    float dtSeconds = dtMs > 1.f ? (dtMs * 0.001f) : 0.001f;

    // --- raw axis 1: harmonic ---
    float harmonicRaw = 0.0f;
    float chromaDelta = fabsf(a.chroma_strength - g_saliencyState.prevChromaStrength);
    if (chromaDelta > g_tuning.harmonicChangeThreshold) {
        harmonicRaw = clamp01(chromaDelta);
    }
    g_saliencyState.prevChromaStrength = a.chroma_strength;

    // --- raw axis 2: timbral (flux derivative proxy) ---
    float fluxDelta = fabsf(a.novelty - g_saliencyState.prevFlux);
    float timbralRaw = clamp01(fluxDelta / g_tuning.fluxDerivativeThreshold);
    g_saliencyState.prevFlux = a.novelty;

    // --- raw axis 3: dynamic (RMS/energy derivative proxy) ---
    float energyDelta = fabsf(a.spectral_energy - g_saliencyState.prevEnergy);
    float dynamicRaw = clamp01(energyDelta / g_tuning.rmsDerivativeThreshold);
    g_saliencyState.prevEnergy = a.spectral_energy;

    // --- raw axis 4: rhythmic (beat spike / fast-flux fallback) ---
    float rhythmicRaw = 0.0f;
    if (onset && onset->beat) {
        rhythmicRaw = clamp01(0.8f * onset->beat_confidence + 0.5f);
    } else {
        float fastFlux = fabsf(a.novelty - g_saliencyState.prevNoveltyForFastFlux);
        rhythmicRaw = clamp01(fastFlux * 0.5f);
    }
    g_saliencyState.prevNoveltyForFastFlux = a.novelty;

    // --- smoothing (dt-correct asymmetric) ---
    g_axis.harmonicNoveltySmooth = asymmetricSmooth(
        g_axis.harmonicNoveltySmooth, harmonicRaw,
        g_tuning.harmonicRiseTime, g_tuning.harmonicFallTime, dtSeconds);
    g_axis.rhythmicNoveltySmooth = asymmetricSmooth(
        g_axis.rhythmicNoveltySmooth, rhythmicRaw,
        g_tuning.rhythmicRiseTime, g_tuning.rhythmicFallTime, dtSeconds);
    g_axis.timbralNoveltySmooth = asymmetricSmooth(
        g_axis.timbralNoveltySmooth, timbralRaw,
        g_tuning.timbralRiseTime, g_tuning.timbralFallTime, dtSeconds);
    g_axis.dynamicNoveltySmooth = asymmetricSmooth(
        g_axis.dynamicNoveltySmooth, dynamicRaw,
        g_tuning.dynamicRiseTime, g_tuning.dynamicFallTime, dtSeconds);

    // --- raw fields for observability ---
    g_axis.harmonicNovelty = harmonicRaw;
    g_axis.rhythmicNovelty = rhythmicRaw;
    g_axis.timbralNovelty = timbralRaw;
    g_axis.dynamicNovelty = dynamicRaw;

    // --- overall saliency ---
    g_axis.overallSaliency = clamp01(
        g_axis.harmonicNoveltySmooth * g_tuning.harmonicWeight +
        g_axis.rhythmicNoveltySmooth * g_tuning.rhythmicWeight +
        g_axis.timbralNoveltySmooth * g_tuning.timbralWeight +
        g_axis.dynamicNoveltySmooth * g_tuning.dynamicWeight);

    // --- dominant axis ---
    g_axis.dominantType = static_cast<uint8_t>(SBSaliencyType::DYNAMIC);
    g_axis.dominantType = (g_axis.harmonicNoveltySmooth >= g_axis.rhythmicNoveltySmooth &&
                           g_axis.harmonicNoveltySmooth >= g_axis.timbralNoveltySmooth &&
                           g_axis.harmonicNoveltySmooth >= g_axis.dynamicNoveltySmooth)
                           ? static_cast<uint8_t>(SBSaliencyType::HARMONIC)
                           : g_axis.dominantType;
    g_axis.dominantType = (g_axis.rhythmicNoveltySmooth >= g_axis.harmonicNoveltySmooth &&
                           g_axis.rhythmicNoveltySmooth >= g_axis.timbralNoveltySmooth &&
                           g_axis.rhythmicNoveltySmooth >= g_axis.dynamicNoveltySmooth)
                           ? static_cast<uint8_t>(SBSaliencyType::RHYTHMIC)
                           : g_axis.dominantType;
    g_axis.dominantType = (g_axis.timbralNoveltySmooth >= g_axis.harmonicNoveltySmooth &&
                           g_axis.timbralNoveltySmooth >= g_axis.rhythmicNoveltySmooth &&
                           g_axis.timbralNoveltySmooth >= g_axis.dynamicNoveltySmooth)
                           ? static_cast<uint8_t>(SBSaliencyType::TIMBRAL)
                           : g_axis.dominantType;

    g_saliencyState.prevFrameMs = (uint32_t)nowMs;

    // --- event capture ---
    float adaptiveFloor = g_saliencyState.adaptiveFloor;
    g_saliencyState.adaptiveFloor = 0.99f * adaptiveFloor + 0.01f * g_axis.overallSaliency;
    float adaptiveThreshold = clamp01(g_saliencyState.adaptiveFloor * 2.0f);
    bool salientEvent = (g_axis.overallSaliency > adaptiveThreshold) &&
                       ((uint32_t)(nowMs - g_saliencyState.lastEventMs) > 120);
    if (salientEvent) {
        g_saliencyState.lastEventMs = (uint32_t)nowMs;
        g_lastEvent = { (uint32_t)nowMs, true, g_axis.overallSaliency, adaptiveThreshold, 0, 0 };
        g_lastEventValid = true;
    }
}

SBSaliencyAxisFrame sb_musical_saliency_read() {
    SBSaliencyAxisFrame out{};
    portENTER_CRITICAL(&g_saliencyMux);
    out = g_axis;
    portEXIT_CRITICAL(&g_saliencyMux);
    return out;
}
```

## 4) Fork wiring point (additive)

- Add producer call in `SPECTRASYNQ_K1_FIRMWARE.ino` immediately after line ~575 (`sb_audio_snapshot_update()` in the AP loop) and before tempo/onset consumers.
- Example additive call order:
  - `sb_audio_snapshot_update();`
  - `const SBOnsetBeatEvent event = sb_onset_beat_read();`
  - `SBAudioSnapshot snap = sb_audio_snapshot_read();`
  - `sb_musical_saliency_update(snap, &event);`

## 5) Read API and thread safety

- Use dedicated read API already declared above:
  - `SBSaliencyAxisFrame sb_musical_saliency_read()`
  - `bool sb_musical_saliency_read_event(SBSaliencyEvent* out, bool clear_after_read = false)`
- All shared reads/writes are guarded by one `portMUX_TYPE` spinlock around the cached `SBSaliencyAxisFrame` and event state.

## 6) Salient-event output definition

A salient event occurs when all are true:
- frame `overallSaliency` is above an adaptive threshold (`overallSaliency > adaptiveThreshold`),
- and at least 120 ms has elapsed since previous event.
- event payload includes `overallSaliency`, `adaptiveThreshold`, and `ageMs`.

This is the event definition to use for host validation and later effect-gating.

## 7) Validation metric (carry-forward)

1. **Event precision:** at least 0.65 of emitted salient-onset events fall within +/-70 ms of a gold beat or downbeat on the 36 HarmonixSet WAVs.
2. **Beat recall:** at least 0.45 of gold beats/downbeats have one salient event within +/-70 ms.
3. **Storm control:** emitted events stay between 40 and 180 events/minute on non-silent music and below 12 events/minute in silence/control windows.
4. **Tempo uplift control:** feeding `sb_tempo` with the new salient novelty must improve `tempo_accuracy.py` in-range Acc2 by at least +20 percentage points over the current novelty baseline.

