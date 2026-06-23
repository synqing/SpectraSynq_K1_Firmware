#pragma once

#include <stdint.h>

enum SBMusicState : uint8_t {
  SB_MUSIC_SILENCE = 0,
  SB_MUSIC_AMBIENT,
  SB_MUSIC_STEADY,
  SB_MUSIC_BUILD,
  SB_MUSIC_DROP,
  SB_MUSIC_BREAKDOWN,
  SB_MUSIC_DENSE
};

struct SBAudioSnapshot {
  uint32_t frame_ms;
  float peak_scaled;
  float vu_level;
  float novelty;
  float spectral_energy;
  float low_energy;
  float mid_energy;
  float high_energy;
  float chroma_strength;
  bool silence;
};

struct SBOnsetBeatEvent {
  uint32_t event_id;
  uint32_t event_ms;
  uint32_t event_age_ms;
  float onset_strength;
  float bass_onset_strength;
  float beat_phase;
  float beat_confidence;
  bool onset;
  bool bass_onset;
  bool beat;
};

void sb_audio_snapshot_update(uint32_t frame_ms);
SBAudioSnapshot sb_audio_snapshot_read();
