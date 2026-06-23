#pragma once

#include <stdint.h>

#include "sb_audio_snapshot.h"
#include "sb_onset_beat.h"

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
  uint8_t dominantType;
};

struct SaliencyTuning {
  float harmonicRiseTime = 0.15f;
  float harmonicFallTime = 0.80f;
  float rhythmicRiseTime = 0.05f;
  float rhythmicFallTime = 0.30f;
  float timbralRiseTime = 0.10f;
  float timbralFallTime = 0.50f;
  float dynamicRiseTime = 0.08f;
  float dynamicFallTime = 0.40f;

  float harmonicChangeThreshold = 0.5f;
  float fluxDerivativeThreshold = 0.05f;
  float rmsDerivativeThreshold = 0.02f;
  float beatVarianceThreshold = 0.15f;

  float harmonicWeight = 0.25f;
  float rhythmicWeight = 0.30f;
  float timbralWeight = 0.20f;
  float dynamicWeight = 0.25f;
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
