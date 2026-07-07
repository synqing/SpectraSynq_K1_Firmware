#ifndef K1_PIN_EVIDENCE_H
#define K1_PIN_EVIDENCE_H

#include <stdint.h>
#include "constants.h"
#include "diagnostic_capture.h"

#ifdef K1_PIN_EVIDENCE_V1

enum K1PinEvidenceStateBits : uint32_t {
  K1_PIN_STATE_LOUD_GUARD_ENABLED = 1UL << 0,
  K1_PIN_STATE_VIVID_ENABLED = 1UL << 1,
  K1_PIN_STATE_AGC_GATED = 1UL << 2,
  K1_PIN_STATE_SECONDARY_ENABLED = 1UL << 3,
};

enum K1PinEvidenceDbaBucket : uint8_t {
  K1_PIN_DBA_UNKNOWN = 0,
  K1_PIN_DBA_NORMAL_52_62 = 1,
  K1_PIN_DBA_THRESHOLD_63_66 = 2,
  K1_PIN_DBA_LOUD_67_72 = 3,
  K1_PIN_DBA_EXTREME_73_PLUS = 4,
};

struct K1PinEvidencePayload {
  uint8_t version;
  uint8_t channel;
  uint16_t mode;
  uint32_t ap_ms;
  uint32_t chroma_seq;
  uint32_t state_bits;
  uint16_t conditioned_peak_q;
  uint16_t post_sensitivity_peak_q;
  uint16_t clip_count;
  uint16_t near_rail_count;
  uint16_t sample_count;
  uint16_t agc_gain_q;
  uint16_t agc_envelope_q;
  uint16_t spectral_saturation_q;
  uint16_t chroma_pre_max_q;
  uint16_t chroma_pre_mean_q;
  uint16_t chroma_gate_q;
  uint8_t agc_gated;
  uint8_t dba_bucket;
  uint8_t held_hue_valid;
  uint16_t held_hue_q;
  uint16_t centroid_strength_q;
  uint8_t dominant_bin;
  uint8_t palette_index;
  uint16_t chroma_norm_max_q;
  uint16_t chroma_norm_mean_q;
  uint16_t chroma_final_max_q;
  uint16_t chroma_final_mean_q;
  uint16_t chroma_flatness_q;
  uint16_t loud_input_trim_q;
  uint16_t loud_gdft_trim_q;
  uint16_t vivid_chroma_q;
  uint16_t vivid_black_q;
  uint8_t chroma_profile;
  uint16_t colour_entropy_q;
  uint16_t top_colour_dwell_q;
  uint16_t top_hue_q;
  uint16_t active_led_pct_q;
  uint16_t saturation_avg_q;
  uint16_t white_bias_avg_q;
  uint16_t com_q;
  uint16_t motion_delta_q;
} __attribute__((packed));

static_assert(sizeof(K1PinEvidencePayload) <= DIAG_CAPTURE_MAX_PAYLOAD_BYTES,
              "K1PinEvidencePayload exceeds diagnostic payload capacity");

void k1_pin_evidence_set_ap_metrics(uint32_t t_now);
void k1_pin_evidence_push_frame(uint32_t frame, uint32_t t_us);
bool k1_pin_evidence_set_dba_bucket_name(const char* name);
const char* k1_pin_evidence_dba_bucket_name();
void k1_pin_evidence_print_status();

#endif

#endif
