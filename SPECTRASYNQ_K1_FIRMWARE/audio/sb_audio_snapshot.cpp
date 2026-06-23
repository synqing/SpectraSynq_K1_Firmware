#include "sb_audio_snapshot.h"

#include <Arduino.h>
#include "constants.h"
#include "globals.h"

static portMUX_TYPE sb_audio_snapshot_mux = portMUX_INITIALIZER_UNLOCKED;
static SBAudioSnapshot sb_audio_snapshot_current = {};

static float sb_clamp_nonnegative(float value) {
  if (!isfinite(value) || value < 0.0f) {
    return 0.0f;
  }
  return value;
}

static uint8_t sb_previous_spectral_history_index() {
  if (spectral_history_index == 0) {
    return SPECTRAL_HISTORY_LENGTH - 1;
  }
  return spectral_history_index - 1;
}

// sb_detect_chord (SB_CHORD_V2) lives in sb_chord_detect.cpp — a stdint/math-only
// TU with no heavy firmware-globals include surface, so the real detector is
// host-unit-testable on Apple clang. Declared in sb_audio_snapshot.h.

void sb_audio_snapshot_update(uint32_t frame_ms) {
  SBAudioSnapshot next = {};
  next.frame_ms = frame_ms;
  next.peak_scaled = sb_clamp_nonnegative(waveform_peak_scaled);
  next.vu_level = sb_clamp_nonnegative(float(audio_vu_level));
  next.novelty = sb_clamp_nonnegative(float(novelty_curve[sb_previous_spectral_history_index()]));
  next.silence = silence;

  float low_sum = 0.0f;
  float mid_sum = 0.0f;
  float high_sum = 0.0f;

  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    float value = sb_clamp_nonnegative(float(spectrogram[i]));
    if (i < NUM_FREQS / 3) {
      low_sum += value;
    } else if (i < (NUM_FREQS * 2) / 3) {
      mid_sum += value;
    } else {
      high_sum += value;
    }
  }

  static const float LOW_COUNT = float(NUM_FREQS / 3);
  static const float MID_COUNT = float((NUM_FREQS * 2) / 3 - NUM_FREQS / 3);
  static const float HIGH_COUNT = float(NUM_FREQS - (NUM_FREQS * 2) / 3);

  next.low_energy = low_sum / LOW_COUNT;
  next.mid_energy = mid_sum / MID_COUNT;
  next.high_energy = high_sum / HIGH_COUNT;
  next.spectral_energy = (low_sum + mid_sum + high_sum) / float(NUM_FREQS);

  const uint8_t nyquist_safe_bin_hi =
      sb_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET);

#ifdef SB_ONSET_V2
  // Carry the per-note spectrum into the V2 onset detector. Same clamped values
  // the band scalars above are derived from — no extra read of the live array
  // (snapshot consistency). Production build omits this entirely.
  static_assert(SB_ONSET_SPECTRUM_BINS == NUM_FREQS,
                "SB_ONSET_SPECTRUM_BINS must equal NUM_FREQS");
  next.nyquist_safe_bin_hi = nyquist_safe_bin_hi;
  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    next.spectrum[i] = sb_clamp_nonnegative(float(spectrogram[i]));
  }
#endif

  float chroma_bucket[12] = {};
  for (uint8_t i = 0; i < nyquist_safe_bin_hi; i++) {
    chroma_bucket[i % 12] += sb_clamp_nonnegative(float(spectrogram[i]));
  }

  float chroma_sum = 0.0f;
  float chroma_max = 0.0f;
  for (uint8_t i = 0; i < 12; i++) {
    float value = chroma_bucket[i];
    chroma_sum += value;
    if (value > chroma_max) {
      chroma_max = value;
    }
  }
  next.chroma_strength = (chroma_sum > 0.0001f) ? (chroma_max / chroma_sum) : 0.0f;

#ifdef SB_CHORD_V2
  // Carry the pitch-class-aligned 12-bin chroma (not just the scalar peakiness)
  // so the chord detector sees the harmonic distribution. This is the same
  // (bin % 12) pitch-class fold the scalar above used (chroma_bucket), restricted
  // to Nyquist-valid target bins for the current sample rate and NOTE_OFFSET. The
  // fork notes[] table is semitone-spaced from A1=55 Hz, so bin % 12 is a genuine
  // pitch class (A-origin).
  static_assert(SB_CHROMA_PC_BINS == 12, "SB_CHROMA_PC_BINS must be 12");
  for (uint8_t i = 0; i < SB_CHROMA_PC_BINS; i++) {
    next.chroma_pc[i] = chroma_bucket[i];
  }
  sb_detect_chord(next.chroma_pc, next.chord);
#endif

  portENTER_CRITICAL(&sb_audio_snapshot_mux);
  sb_audio_snapshot_current = next;
  portEXIT_CRITICAL(&sb_audio_snapshot_mux);
}

SBAudioSnapshot sb_audio_snapshot_read() {
  SBAudioSnapshot snapshot;
  portENTER_CRITICAL(&sb_audio_snapshot_mux);
  snapshot = sb_audio_snapshot_current;
  portEXIT_CRITICAL(&sb_audio_snapshot_mux);
  return snapshot;
}
