#include "k1_pin_evidence.h"

#ifdef K1_PIN_EVIDENCE_V1

#include <Arduino.h>
#include <FastLED.h>
#include <math.h>
#include <string.h>
#include "globals.h"

struct K1PinEvidenceApMetrics {
  uint32_t ap_ms;
  uint16_t conditioned_peak_q;
  uint16_t post_sensitivity_peak_q;
  uint16_t clip_count;
  uint16_t near_rail_count;
  uint16_t sample_count;
  uint16_t agc_gain_q;
  uint16_t agc_envelope_q;
  uint16_t spectral_saturation_q;
  uint8_t agc_gated;
};

struct K1PinEvidenceChannelHistory {
  bool valid;
  float previous_com;
};

static K1PinEvidenceApMetrics k1_pin_ap_metrics = {};
static K1PinEvidencePayload k1_pin_evidence_scratch;
static K1PinEvidenceChannelHistory k1_pin_channel_history[2] = {
  { false, 79.5f },
  { false, 79.5f },
};
static uint8_t k1_pin_dba_bucket = K1_PIN_DBA_UNKNOWN;

static uint16_t k1_pin_q16(float value) {
  if (!isfinite(value) || value <= 0.0f) {
    return 0;
  }
  if (value >= 1.0f) {
    return 65535U;
  }
  return uint16_t((value * 65535.0f) + 0.5f);
}

static uint16_t k1_pin_q8_8(float value) {
  if (!isfinite(value) || value <= 0.0f) {
    return 0;
  }
  if (value >= 255.996f) {
    return 65535U;
  }
  return uint16_t((value * 256.0f) + 0.5f);
}

static uint8_t k1_pin_min3(uint8_t a, uint8_t b, uint8_t c) {
  uint8_t m = (a < b) ? a : b;
  return (m < c) ? m : c;
}

static uint8_t k1_pin_max3(uint8_t a, uint8_t b, uint8_t c) {
  uint8_t m = (a > b) ? a : b;
  return (m > c) ? m : c;
}

static uint8_t k1_pin_sat8(const CRGB& c) {
  uint8_t max_c = k1_pin_max3(c.r, c.g, c.b);
  if (max_c == 0) {
    return 0;
  }
  uint8_t min_c = k1_pin_min3(c.r, c.g, c.b);
  return uint8_t((uint16_t(max_c - min_c) * 255U) / max_c);
}

static uint8_t k1_pin_white_bias8(const CRGB& c) {
  uint8_t max_c = k1_pin_max3(c.r, c.g, c.b);
  if (max_c == 0) {
    return 0;
  }
  uint8_t min_c = k1_pin_min3(c.r, c.g, c.b);
  return uint8_t((uint16_t(min_c) * 255U) / max_c);
}

static uint8_t k1_pin_hue8(const CRGB& c) {
  uint8_t max_c = k1_pin_max3(c.r, c.g, c.b);
  uint8_t min_c = k1_pin_min3(c.r, c.g, c.b);
  uint8_t delta = max_c - min_c;
  if (delta == 0) {
    return 0;
  }

  int16_t hue = 0;
  if (max_c == c.r) {
    hue = int16_t(43 * (int16_t(c.g) - int16_t(c.b)) / int16_t(delta));
  } else if (max_c == c.g) {
    hue = int16_t(85 + (43 * (int16_t(c.b) - int16_t(c.r)) / int16_t(delta)));
  } else {
    hue = int16_t(171 + (43 * (int16_t(c.r) - int16_t(c.g)) / int16_t(delta)));
  }

  while (hue < 0) {
    hue += 256;
  }
  while (hue > 255) {
    hue -= 256;
  }
  return uint8_t(hue);
}

static void k1_pin_fill_final_metrics(const CRGB* leds, uint16_t count,
                                      uint8_t channel,
                                      K1PinEvidencePayload& out) {
  if (leds == nullptr || count == 0) {
    return;
  }
  if (count > LED_COUNT_VALUE) {
    count = LED_COUNT_VALUE;
  }

  uint16_t hue_hist[16] = {};
  uint16_t active = 0;
  uint32_t sat_sum = 0;
  uint32_t white_sum = 0;
  uint32_t energy_sum = 0;
  double weighted_sum = 0.0;

  for (uint16_t i = 0; i < count; i++) {
    const CRGB c = leds[i];
    uint16_t energy = uint16_t(c.r) + uint16_t(c.g) + uint16_t(c.b);
    energy_sum += energy;
    weighted_sum += double(i) * double(energy);
    if (energy > 0) {
      active++;
      uint8_t hue_bin = uint8_t(k1_pin_hue8(c) >> 4);
      if (hue_bin > 15) {
        hue_bin = 15;
      }
      hue_hist[hue_bin]++;
    }
    sat_sum += k1_pin_sat8(c);
    white_sum += k1_pin_white_bias8(c);
  }

  uint16_t top_count = 0;
  uint8_t top_bin = 0;
  for (uint8_t i = 0; i < 16; i++) {
    if (hue_hist[i] > top_count) {
      top_count = hue_hist[i];
      top_bin = i;
    }
  }

  float entropy = 0.0f;
  if (active > 0) {
    for (uint8_t i = 0; i < 16; i++) {
      if (hue_hist[i] == 0) {
        continue;
      }
      float p = float(hue_hist[i]) / float(active);
      entropy -= p * (logf(p) / logf(2.0f));
    }
    entropy /= 4.0f;
  }

  float com = (energy_sum > 0)
                ? float(weighted_sum / double(energy_sum))
                : (float(count - 1U) * 0.5f);
  K1PinEvidenceChannelHistory& history = k1_pin_channel_history[channel == 1 ? 1 : 0];
  float motion_delta = history.valid ? fabsf(com - history.previous_com) : 0.0f;
  history.previous_com = com;
  history.valid = true;

  out.colour_entropy_q = k1_pin_q16(entropy);
  out.top_colour_dwell_q = (active > 0) ? k1_pin_q16(float(top_count) / float(active)) : 0;
  out.top_hue_q = k1_pin_q16(float(top_bin) / 15.0f);
  out.active_led_pct_q = k1_pin_q16(float(active) / float(count));
  out.saturation_avg_q = (count > 0) ? k1_pin_q16((float(sat_sum) / float(count)) / 255.0f) : 0;
  out.white_bias_avg_q = (count > 0) ? k1_pin_q16((float(white_sum) / float(count)) / 255.0f) : 0;
  out.com_q = k1_pin_q8_8(com);
  out.motion_delta_q = k1_pin_q8_8(motion_delta);
}

void k1_pin_evidence_set_ap_metrics(uint32_t t_now) {
  uint16_t saturated_bins = 0;
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    if (float(spectrogram[i]) >= 0.92f) {
      saturated_bins++;
    }
  }

  k1_pin_ap_metrics.ap_ms = t_now;
  k1_pin_ap_metrics.conditioned_peak_q = k1_pin_q16(waveform_peak_scaled);
  k1_pin_ap_metrics.post_sensitivity_peak_q = k1_pin_q16(waveform_peak_scaled);
#ifdef K1_LOUD_GUARD_V1
  k1_pin_ap_metrics.clip_count = k1_loud_frame_clip_count;
  k1_pin_ap_metrics.near_rail_count = k1_loud_frame_near_rail_count;
  k1_pin_ap_metrics.sample_count = k1_loud_frame_sample_count;
  k1_pin_ap_metrics.spectral_saturation_q = k1_pin_q16(k1_loud_spec_sat_fraction);
#else
  k1_pin_ap_metrics.clip_count = 0;
  k1_pin_ap_metrics.near_rail_count = 0;
  k1_pin_ap_metrics.sample_count = CONFIG.SAMPLES_PER_CHUNK;
  k1_pin_ap_metrics.spectral_saturation_q = k1_pin_q16(float(saturated_bins) / float(NUM_FREQS));
#endif
  k1_pin_ap_metrics.agc_gain_q = k1_pin_q16(float(agc_bands[0].gain));
  k1_pin_ap_metrics.agc_envelope_q = k1_pin_q16(float(agc_bands[0].energy));
  k1_pin_ap_metrics.agc_gated = agc_gated ? 1 : 0;
}

static void k1_pin_fill_common(uint8_t channel, uint16_t mode, K1PinEvidencePayload& out) {
  memset(&out, 0, sizeof(out));
  out.version = K1_PIN_EVIDENCE_PAYLOAD_VERSION;
  out.channel = channel;
  out.mode = mode;
  out.ap_ms = k1_pin_ap_metrics.ap_ms;
  out.chroma_seq = vp_dbg_chroma_seq;
  out.state_bits = 0;
#ifdef K1_LOUD_GUARD_V1
  if (k1_loud_guard_enabled) {
    out.state_bits |= K1_PIN_STATE_LOUD_GUARD_ENABLED;
  }
#endif
#ifdef K1_VIVID_PRECOMP_V1
  if (VP_VIVID_PRECOMP) {
    out.state_bits |= K1_PIN_STATE_VIVID_ENABLED;
  }
#endif
  if (agc_gated) {
    out.state_bits |= K1_PIN_STATE_AGC_GATED;
  }
  if (ENABLE_SECONDARY_LEDS) {
    out.state_bits |= K1_PIN_STATE_SECONDARY_ENABLED;
  }

  out.conditioned_peak_q = k1_pin_ap_metrics.conditioned_peak_q;
  out.post_sensitivity_peak_q = k1_pin_ap_metrics.post_sensitivity_peak_q;
  out.clip_count = k1_pin_ap_metrics.clip_count;
  out.near_rail_count = k1_pin_ap_metrics.near_rail_count;
  out.sample_count = k1_pin_ap_metrics.sample_count;
  out.agc_gain_q = k1_pin_ap_metrics.agc_gain_q;
  out.agc_envelope_q = k1_pin_ap_metrics.agc_envelope_q;
  out.spectral_saturation_q = k1_pin_ap_metrics.spectral_saturation_q;
  out.chroma_pre_max_q = k1_pin_q16(float(vp_dbg_chroma_pre_max));
  out.chroma_pre_mean_q = k1_pin_q16(float(vp_dbg_chroma_pre_mean));
  out.chroma_gate_q = k1_pin_q16(float(vp_dbg_chroma_gate_gain));
  out.agc_gated = k1_pin_ap_metrics.agc_gated;
  out.dba_bucket = k1_pin_dba_bucket;
  out.held_hue_valid = k1_pin_palette_held_hue_valid ? 1 : 0;
  out.held_hue_q = k1_pin_q16(k1_pin_palette_held_hue);
  out.centroid_strength_q = k1_pin_q16(k1_pin_palette_centroid_strength);
  out.dominant_bin = k1_pin_palette_dominant_bin;
  out.palette_index = k1_pin_palette_index;
  out.chroma_norm_max_q = k1_pin_q16(float(vp_dbg_chroma_norm_max));
  out.chroma_norm_mean_q = k1_pin_q16(float(vp_dbg_chroma_norm_mean));
  out.chroma_final_max_q = k1_pin_q16(float(vp_dbg_chroma_final_max));
  out.chroma_final_mean_q = k1_pin_q16(float(vp_dbg_chroma_final_mean));
  out.chroma_flatness_q = k1_pin_q16(float(vp_dbg_chroma_flatness));
#ifdef K1_LOUD_GUARD_V1
  out.loud_input_trim_q = k1_pin_q16(k1_loud_input_trim);
  out.loud_gdft_trim_q = k1_pin_q16(k1_loud_gdft_trim);
#else
  out.loud_input_trim_q = 65535U;
  out.loud_gdft_trim_q = 65535U;
#endif
#ifdef K1_VIVID_PRECOMP_V1
  out.vivid_chroma_q = k1_pin_q16(VP_VIVID_CHROMA_LEVEL);
  out.vivid_black_q = k1_pin_q16(VP_VIVID_BLACK_LEVEL);
#endif
  out.chroma_profile = vp_dbg_chroma_profile;
}

static void k1_pin_push_channel(uint8_t channel, const CRGB* leds, uint16_t count,
                                uint16_t mode, uint32_t frame, uint32_t t_us) {
  if (!diag_capture_can_push(sizeof(k1_pin_evidence_scratch))) {
    return;
  }

  k1_pin_fill_common(channel, mode, k1_pin_evidence_scratch);
  k1_pin_fill_final_metrics(leds, count, channel, k1_pin_evidence_scratch);
  diag_capture_try_push(DIAG_KIND_K1_PIN_EVIDENCE, 0, frame, t_us,
                        &k1_pin_evidence_scratch,
                        sizeof(k1_pin_evidence_scratch));
}

void k1_pin_evidence_push_frame(uint32_t frame, uint32_t t_us) {
  if (!diag_capture_is_capturing()) {
    return;
  }
  k1_pin_push_channel(0, leds_out, CONFIG.LED_COUNT, CONFIG.LIGHTSHOW_MODE, frame, t_us);
  if (ENABLE_SECONDARY_LEDS && leds_out_secondary != nullptr) {
    k1_pin_push_channel(1, leds_out_secondary, SECONDARY_LED_COUNT, SECONDARY_LIGHTSHOW_MODE, frame, t_us);
  }
}

bool k1_pin_evidence_set_dba_bucket_name(const char* name) {
  if (name == nullptr || name[0] == 0 || strcmp(name, "unknown") == 0) {
    k1_pin_dba_bucket = K1_PIN_DBA_UNKNOWN;
    return true;
  }
  if (strcmp(name, "normal_52_62") == 0) {
    k1_pin_dba_bucket = K1_PIN_DBA_NORMAL_52_62;
    return true;
  }
  if (strcmp(name, "threshold_63_66") == 0) {
    k1_pin_dba_bucket = K1_PIN_DBA_THRESHOLD_63_66;
    return true;
  }
  if (strcmp(name, "loud_67_72") == 0) {
    k1_pin_dba_bucket = K1_PIN_DBA_LOUD_67_72;
    return true;
  }
  if (strcmp(name, "extreme_73_plus") == 0) {
    k1_pin_dba_bucket = K1_PIN_DBA_EXTREME_73_PLUS;
    return true;
  }
  return false;
}

const char* k1_pin_evidence_dba_bucket_name() {
  switch (k1_pin_dba_bucket) {
    case K1_PIN_DBA_NORMAL_52_62: return "normal_52_62";
    case K1_PIN_DBA_THRESHOLD_63_66: return "threshold_63_66";
    case K1_PIN_DBA_LOUD_67_72: return "loud_67_72";
    case K1_PIN_DBA_EXTREME_73_PLUS: return "extreme_73_plus";
    case K1_PIN_DBA_UNKNOWN:
    default:
      return "unknown";
  }
}

void k1_pin_evidence_print_status() {
  USBSerial.println("sbr{{");
  USBSerial.print("K1_PIN_EVIDENCE: dba_bucket=");
  USBSerial.println(k1_pin_evidence_dba_bucket_name());
  USBSerial.print("K1_PIN_AP_MS: ");
  USBSerial.println(k1_pin_ap_metrics.ap_ms);
  USBSerial.print("K1_PIN_CHROMA_SEQ: ");
  USBSerial.println(vp_dbg_chroma_seq);
  USBSerial.println("}}");
}

#endif
