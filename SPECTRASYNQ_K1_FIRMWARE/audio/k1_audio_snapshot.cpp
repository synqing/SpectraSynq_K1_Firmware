#include "k1_audio_snapshot.h"

#include <Arduino.h>
#include "constants.h"
#include "globals.h"

static portMUX_TYPE k1_audio_snapshot_mux = portMUX_INITIALIZER_UNLOCKED;
static K1AudioSnapshot k1_audio_snapshot_current = {};

static float k1_clamp_nonnegative(float value) {
  if (!isfinite(value) || value < 0.0f) {
    return 0.0f;
  }
  return value;
}

static uint8_t k1_previous_spectral_history_index() {
  if (spectral_history_index == 0) {
    return SPECTRAL_HISTORY_LENGTH - 1;
  }
  return spectral_history_index - 1;
}

// k1_detect_chord (K1_CHORD_V2) lives in k1_chord_detect.cpp — a stdint/math-only
// TU with no heavy firmware-globals include surface, so the real detector is
// host-unit-testable on Apple clang. Declared in k1_audio_snapshot.h.

void k1_audio_snapshot_update(uint32_t frame_ms) {
  K1AudioSnapshot next = {};
  next.frame_ms = frame_ms;
  next.peak_scaled = k1_clamp_nonnegative(waveform_peak_scaled);
  next.vu_level = k1_clamp_nonnegative(float(audio_vu_level));
  next.novelty = k1_clamp_nonnegative(float(novelty_curve[k1_previous_spectral_history_index()]));
  next.silence = silence;

  float low_sum = 0.0f;
  float mid_sum = 0.0f;
  float high_sum = 0.0f;

  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    float value = k1_clamp_nonnegative(float(spectrogram[i]));
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
      k1_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET);

#ifdef K1_ONSET_V2
  // Carry the per-note spectrum into the V2 onset detector. Same clamped values
  // the band scalars above are derived from — no extra read of the live array
  // (snapshot consistency). Production build omits this entirely.
  static_assert(K1_ONSET_SPECTRUM_BINS == NUM_FREQS,
                "K1_ONSET_SPECTRUM_BINS must equal NUM_FREQS");
  next.nyquist_safe_bin_hi = nyquist_safe_bin_hi;
  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    next.spectrum[i] = k1_clamp_nonnegative(float(spectrogram[i]));
  }
#endif

  float chroma_bucket[12] = {};
  for (uint8_t i = 0; i < nyquist_safe_bin_hi; i++) {
    chroma_bucket[i % 12] += k1_clamp_nonnegative(float(spectrogram[i]));
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

#ifdef K1_CHORD_V2
  // Carry the pitch-class-aligned 12-bin chroma (not just the scalar peakiness)
  // so the chord detector sees the harmonic distribution. This is the same
  // (bin % 12) pitch-class fold the scalar above used (chroma_bucket), restricted
  // to Nyquist-valid target bins for the current sample rate and NOTE_OFFSET. The
  // fork notes[] table is semitone-spaced from A1=55 Hz, so bin % 12 is a genuine
  // pitch class (A-origin).
  static_assert(K1_CHROMA_PC_BINS == 12, "K1_CHROMA_PC_BINS must be 12");
  for (uint8_t i = 0; i < K1_CHROMA_PC_BINS; i++) {
    next.chroma_pc[i] = chroma_bucket[i];
  }
  k1_detect_chord(next.chroma_pc, next.chord);
#endif

#ifdef K1_STM
  // Re-derived STM over the same post-AGC per-note spectrogram the band scalars
  // above are built from. One consistent read of spectrogram[] into a float
  // working buffer, then a single hot-path call that fills next.stm. Production
  // build (no K1_STM) omits this entirely so the struct + link are unchanged.
  static_assert(NUM_FREQS <= K1_STM_MAX_BINS,
                "NUM_FREQS must fit the STM producer bin bound");
  float k1_stm_spectrum[NUM_FREQS];
  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    k1_stm_spectrum[i] = k1_clamp_nonnegative(float(spectrogram[i]));
  }
  k1_stm_process(k1_stm_spectrum, (uint8_t)NUM_FREQS, silence, &next.stm);
#endif

  portENTER_CRITICAL(&k1_audio_snapshot_mux);
  k1_audio_snapshot_current = next;
  portEXIT_CRITICAL(&k1_audio_snapshot_mux);
}

K1AudioSnapshot k1_audio_snapshot_read() {
  K1AudioSnapshot snapshot;
  portENTER_CRITICAL(&k1_audio_snapshot_mux);
  snapshot = k1_audio_snapshot_current;
  portEXIT_CRITICAL(&k1_audio_snapshot_mux);
  return snapshot;
}

#ifdef K1_STM
K1StmResult k1_stm_read() {
  K1StmResult result;
  portENTER_CRITICAL(&k1_audio_snapshot_mux);
  result = k1_audio_snapshot_current.stm;
  portEXIT_CRITICAL(&k1_audio_snapshot_mux);
  return result;
}
#endif
