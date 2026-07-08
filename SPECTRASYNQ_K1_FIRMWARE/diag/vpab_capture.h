#ifndef VPAB_CAPTURE_H
#define VPAB_CAPTURE_H

#include <FastLED.h>
#include <stdint.h>
#include "constants.h"

enum VPABCaptureMode : uint8_t {
  VPAB_CAPTURE_METRICS = 0,
  VPAB_CAPTURE_BYTES = 1,
  VPAB_CAPTURE_BOTH = 2,
};

struct VPABCaptureConfig {
  bool active;
  bool once;
  uint16_t every_n;
  uint32_t frame;
  uint32_t seq;
  uint32_t last_emit_us;
  VPABCaptureMode mode;
};

struct VPABMetricPayload {
  uint8_t channel;
  uint8_t mode;
  uint8_t scenario;
  uint8_t shadow;
  uint8_t memory_metrics;
  uint8_t dither_step_value;
  uint8_t fastled_dither;
  uint8_t truncated;
  uint16_t leds;
  uint32_t t_ms;
  uint32_t dt_us;
  uint32_t quant_us;
  float mae8;
  uint8_t p95_abs8;
  uint8_t max_abs8;
  float changed_led_pct;
  float changed_channel_pct;
  uint32_t energy_a;
  uint32_t energy_b;
  float energy_delta_pct;
  float com_a;
  float com_b;
  float com_delta_leds;
  float com_slope_delta_pct;
  uint8_t hue_delta_p95;
  uint8_t sat_delta_p95;
  float white_bias_score;
  float flicker_score;
  uint32_t render_us;
  uint32_t frame_us;
  uint32_t show_us;
  uint32_t over;
  uint32_t dropped;
  uint32_t heap;
};

struct VPABBytesPayload {
  uint8_t channel;
  uint8_t mode;
  uint8_t dither_step_value;
  uint8_t fastled_dither;
  uint16_t leds;
  uint16_t byte_count;
  uint32_t render_us;
  uint32_t quant_us;
  uint32_t frame_us;
  uint32_t show_us;
  uint32_t over;
  uint32_t dropped;
  uint8_t bytes[LED_COUNT_VALUE * 3];
};

struct VPABRenderContext {
  uint8_t primary_mode;
  uint8_t primary_config_mode;
  uint8_t secondary_mode;
  uint8_t smart_enabled;
  uint8_t hooks_enabled;
  uint8_t edge_enabled;
  uint8_t edge_mode;
  uint8_t manual_owner_active;
  uint16_t edge_strength_milli;
  uint16_t edge_effective_strength_milli;
  // Symmetric dual-edge (A lane). edge_dual_mode: SBEdgeMixerDualEdge (0 one-sided /
  // 1 split / 2 mirror). edge_primary_enabled: 1 when the primary-edge transform
  // actually ran this frame (dual mode active AND edge enabled).
  uint8_t edge_dual_mode;
  uint8_t edge_primary_enabled;
};

void vpab_capture_reset();
void vpab_capture_arm(bool once, uint16_t every_n, VPABCaptureMode mode);
void vpab_capture_stop();
void vpab_capture_set_render_context(const VPABRenderContext& context);
void vpab_capture_tick(uint32_t primary_quant_us);
void vpab_capture_print_status();
void vpab_capture_dump();
void vpab_capture_dump_frames();
VPABCaptureMode vpab_capture_parse_mode(const char* text, VPABCaptureMode fallback);

#endif
