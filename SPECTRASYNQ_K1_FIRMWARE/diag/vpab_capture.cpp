#include "vpab_capture.h"

#include <Arduino.h>
#include <math.h>
#include <string.h>
#include "diagnostic_capture.h"
#include "globals.h"
#ifdef K1_PIN_EVIDENCE_V1
#include "k1_pin_evidence.h"
#endif

#if ENABLE_VPAB_PROBE

static_assert(sizeof(VPABMetricPayload) <= DIAG_CAPTURE_MAX_PAYLOAD_BYTES,
              "VPABMetricPayload exceeds diagnostic payload capacity");
static_assert(sizeof(VPABBytesPayload) <= DIAG_CAPTURE_MAX_PAYLOAD_BYTES,
              "VPABBytesPayload exceeds diagnostic payload capacity");

static VPABCaptureConfig vpab_capture_state = {
  false,
  false,
  DIAG_VPAB_DEFAULT_EVERY_N,
  0,
  0,
  0,
  VPAB_CAPTURE_METRICS,
};
static portMUX_TYPE vpab_capture_mux = portMUX_INITIALIZER_UNLOCKED;
static portMUX_TYPE vpab_render_context_mux = portMUX_INITIALIZER_UNLOCKED;
static VPABRenderContext vpab_render_context = {
  LIGHT_MODE_BLOOM,
  LIGHT_MODE_BLOOM,
  LIGHT_MODE_WAVEFORM_FAST,
  0,
  0,
  0,
  0,
  0,
  0,
  0,
};

struct VPABDrainHistory {
  bool prev_valid;
  float prev_com;
};

static VPABDrainHistory vpab_history_primary = { false, 0.0f };
static VPABDrainHistory vpab_history_secondary = { false, 0.0f };
static VPABMetricPayload vpab_metric_scratch;
static VPABBytesPayload vpab_bytes_scratch;
static uint16_t vpab_abs_hist[256];
static uint16_t vpab_hue_hist[256];
static uint16_t vpab_sat_hist[256];

static uint32_t vpab_crc32_update(uint32_t crc, uint8_t value) {
  crc ^= uint32_t(value);
  for (uint8_t bit = 0; bit < 8; bit++) {
    if ((crc & 1UL) != 0) {
      crc = (crc >> 1) ^ 0xEDB88320UL;
    } else {
      crc >>= 1;
    }
  }
  return crc;
}

static uint32_t vpab_crc32_bytes(const uint8_t* data, uint16_t count) {
  uint32_t crc = 0xFFFFFFFFUL;
  for (uint16_t i = 0; i < count; i++) {
    crc = vpab_crc32_update(crc, data[i]);
  }
  return ~crc;
}

static void vpab_print_u32_hex8(uint32_t value) {
  const char digits[] = "0123456789ABCDEF";
  for (int8_t shift = 28; shift >= 0; shift -= 4) {
    USBSerial.write(digits[(value >> shift) & 0x0F]);
  }
}

static void vpab_print_payload_hex(const uint8_t* data, uint16_t count) {
  const char digits[] = "0123456789ABCDEF";
  for (uint16_t i = 0; i < count; i++) {
    uint8_t value = data[i];
    USBSerial.write(digits[(value >> 4) & 0x0F]);
    USBSerial.write(digits[value & 0x0F]);
  }
}

static uint8_t vpab_abs8(uint8_t a, uint8_t b) {
  return (a >= b) ? uint8_t(a - b) : uint8_t(b - a);
}

static uint8_t vpab_min3(uint8_t a, uint8_t b, uint8_t c) {
  uint8_t m = (a < b) ? a : b;
  return (m < c) ? m : c;
}

static uint8_t vpab_max3(uint8_t a, uint8_t b, uint8_t c) {
  uint8_t m = (a > b) ? a : b;
  return (m > c) ? m : c;
}

static uint8_t vpab_sat8(const CRGB& c) {
  uint8_t max_c = vpab_max3(c.r, c.g, c.b);
  if (max_c == 0) {
    return 0;
  }
  uint8_t min_c = vpab_min3(c.r, c.g, c.b);
  return uint8_t((uint16_t(max_c - min_c) * 255U) / max_c);
}

static uint8_t vpab_white_bias8(const CRGB& c) {
  uint8_t max_c = vpab_max3(c.r, c.g, c.b);
  if (max_c == 0) {
    return 0;
  }
  uint8_t min_c = vpab_min3(c.r, c.g, c.b);
  return uint8_t((uint16_t(min_c) * 255U) / max_c);
}

static uint8_t vpab_hue8(const CRGB& c) {
  uint8_t max_c = vpab_max3(c.r, c.g, c.b);
  uint8_t min_c = vpab_min3(c.r, c.g, c.b);
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

static uint8_t vpab_hue_delta8(uint8_t a, uint8_t b) {
  uint8_t d = vpab_abs8(a, b);
  return (d > 128) ? uint8_t(256 - d) : d;
}

static uint8_t vpab_hist_p95(uint16_t* hist, uint32_t samples) {
  if (samples == 0) {
    return 0;
  }
  uint32_t target = (samples * 95U + 99U) / 100U;
  if (target == 0) {
    target = 1;
  }
  uint32_t seen = 0;
  for (uint16_t i = 0; i < 256; i++) {
    seen += hist[i];
    if (seen >= target) {
      return uint8_t(i);
    }
  }
  return 255;
}

static float vpab_delta_pct(uint32_t a, uint32_t b) {
  if (a == 0) {
    return (b == 0) ? 0.0f : 100.0f;
  }
  return ((float(b) - float(a)) * 100.0f) / float(a);
}

static float vpab_com_from_energy(double weighted_sum, uint32_t energy, uint16_t count) {
  if (energy == 0) {
    return (count > 0) ? (float(count - 1) * 0.5f) : 0.0f;
  }
  return float(weighted_sum / double(energy));
}

struct VPABByteAggregate {
  uint32_t hash;
  uint32_t energy;
  uint32_t r_sum;
  uint32_t g_sum;
  uint32_t b_sum;
  uint16_t nonzero_leds;
  uint8_t max_luma;
  float com;
  float saturation_avg;
  float white_bias_avg;
};

static void vpab_hash_byte(uint32_t& hash, uint8_t value) {
  hash ^= value;
  hash *= 16777619UL;
}

static VPABByteAggregate vpab_aggregate_bytes(const VPABBytesPayload& bytes) {
  VPABByteAggregate aggregate = {
    2166136261UL,
    0,
    0,
    0,
    0,
    0,
    0,
    0.0f,
    0.0f,
    0.0f,
  };

  uint16_t count = bytes.leds;
  if (count > LED_COUNT_VALUE) {
    count = LED_COUNT_VALUE;
  }

  double weighted_sum = 0.0;
  uint32_t saturation_sum = 0;
  uint32_t white_bias_sum = 0;
  for (uint16_t i = 0; i < count; i++) {
    uint16_t base = i * 3U;
    uint8_t r = bytes.bytes[base];
    uint8_t g = bytes.bytes[base + 1];
    uint8_t b = bytes.bytes[base + 2];
    CRGB c(r, g, b);
    vpab_hash_byte(aggregate.hash, r);
    vpab_hash_byte(aggregate.hash, g);
    vpab_hash_byte(aggregate.hash, b);

    uint16_t e = uint16_t(r) + uint16_t(g) + uint16_t(b);
    aggregate.energy += e;
    aggregate.r_sum += r;
    aggregate.g_sum += g;
    aggregate.b_sum += b;
    if (e > 0) {
      aggregate.nonzero_leds++;
    }
    uint8_t luma = uint8_t(e / 3U);
    if (luma > aggregate.max_luma) {
      aggregate.max_luma = luma;
    }
    weighted_sum += double(i) * double(e);
    saturation_sum += vpab_sat8(c);
    white_bias_sum += vpab_white_bias8(c);
  }

  aggregate.com = vpab_com_from_energy(weighted_sum, aggregate.energy, count);
  if (count > 0) {
    aggregate.saturation_avg = float(saturation_sum) / float(count);
    aggregate.white_bias_avg = float(white_bias_sum) / float(count);
  }
  return aggregate;
}

static const char* vpab_channel_name(uint8_t channel) {
  return channel == 1 ? "secondary" : "primary";
}

static VPABRenderContext vpab_capture_read_render_context() {
  VPABRenderContext context;
  portENTER_CRITICAL(&vpab_render_context_mux);
  context = vpab_render_context;
  portEXIT_CRITICAL(&vpab_render_context_mux);
  return context;
}

static uint8_t vpab_mode_for_channel(uint8_t channel) {
  VPABRenderContext context = vpab_capture_read_render_context();
  return channel == 1 ? context.secondary_mode : context.primary_mode;
}

static VPABDrainHistory& vpab_history_for_channel(uint8_t channel) {
  return channel == 1 ? vpab_history_secondary : vpab_history_primary;
}

static uint8_t vpab_fastled_dither_flag() {
#if ENABLE_FASTLED_DITHER
  return 1;
#else
  return 0;
#endif
}

static uint32_t vpab_channel_render_us(uint8_t channel) {
#if ENABLE_VP_PERF_AUDIT
  if (channel == 1) {
    if (vp_perf.secondary_render.count > 0) {
      return vp_perf.secondary_render.max_us;
    }
  } else if (vp_perf.primary_render.count > 0) {
    return vp_perf.primary_render.max_us;
  }
#endif
  return vp_render_us_last;
}

static void vpab_reset_histories() {
  vpab_history_primary.prev_valid = false;
  vpab_history_primary.prev_com = 0.0f;
  vpab_history_secondary.prev_valid = false;
  vpab_history_secondary.prev_com = 0.0f;
}

void vpab_capture_set_render_context(const VPABRenderContext& context) {
  portENTER_CRITICAL(&vpab_render_context_mux);
  vpab_render_context = context;
  portEXIT_CRITICAL(&vpab_render_context_mux);
}

static void vpab_fill_self_shadow_metrics(VPABMetricPayload& out, uint8_t channel,
                                          const CRGB* final_bytes, uint16_t requested_count,
                                          uint32_t dt_us, uint32_t quant_us) {
  uint16_t count = requested_count;
  bool truncated = false;
  if (count > LED_COUNT_VALUE) {
    count = LED_COUNT_VALUE;
    truncated = true;
  }

  memset(vpab_abs_hist, 0, sizeof(vpab_abs_hist));
  memset(vpab_hue_hist, 0, sizeof(vpab_hue_hist));
  memset(vpab_sat_hist, 0, sizeof(vpab_sat_hist));

  uint32_t energy = 0;
  double com_weighted = 0.0;
  uint32_t white_bias_delta_sum = 0;

  for (uint16_t i = 0; i < count; i++) {
    const CRGB& a = final_bytes[i];
    uint16_t e = uint16_t(a.r) + uint16_t(a.g) + uint16_t(a.b);
    energy += e;
    com_weighted += double(i) * double(e);

    vpab_abs_hist[0] += 3;
    vpab_hue_hist[0]++;
    vpab_sat_hist[0]++;
    white_bias_delta_sum += vpab_abs8(vpab_white_bias8(a), vpab_white_bias8(a));
    (void)vpab_hue_delta8(vpab_hue8(a), vpab_hue8(a));
    (void)vpab_sat8(a);
  }

  uint32_t byte_samples = uint32_t(count) * 3U;
  float com = vpab_com_from_energy(com_weighted, energy, count);
  VPABDrainHistory& history = vpab_history_for_channel(channel);
  float slope_delta_pct = 0.0f;
  if (history.prev_valid) {
    float slope_a = com - history.prev_com;
    float slope_b = slope_a;
    float denom = fabsf(slope_a);
    slope_delta_pct = (denom < 0.001f)
                        ? 0.0f
                        : ((fabsf(slope_b - slope_a) * 100.0f) / denom);
  }
  history.prev_com = com;
  history.prev_valid = true;

  out.channel = channel;
  out.mode = vpab_mode_for_channel(channel);
  out.scenario = 0;
  out.shadow = 0;
  out.memory_metrics = 0;
  out.dither_step_value = dither_step;
  out.fastled_dither = vpab_fastled_dither_flag();
  out.truncated = truncated ? 1 : 0;
  out.leds = count;
  out.t_ms = millis();
  out.dt_us = dt_us;
  out.quant_us = quant_us;
  out.mae8 = 0.0f;
  out.p95_abs8 = vpab_hist_p95(vpab_abs_hist, byte_samples);
  out.max_abs8 = 0;
  out.changed_led_pct = 0.0f;
  out.changed_channel_pct = 0.0f;
  out.energy_a = energy;
  out.energy_b = energy;
  out.energy_delta_pct = vpab_delta_pct(energy, energy);
  out.com_a = com;
  out.com_b = com;
  out.com_delta_leds = 0.0f;
  out.com_slope_delta_pct = slope_delta_pct;
  out.hue_delta_p95 = vpab_hist_p95(vpab_hue_hist, count);
  out.sat_delta_p95 = vpab_hist_p95(vpab_sat_hist, count);
  out.white_bias_score = (count > 0)
                           ? (float(white_bias_delta_sum) / (float(count) * 255.0f))
                           : 0.0f;
  out.flicker_score = 0.0f;
  out.render_us = vpab_channel_render_us(channel);
#if ENABLE_VP_PERF_AUDIT
  out.frame_us = vp_perf_avg(vp_perf.frame);
  out.show_us = vp_perf_avg(vp_perf.show);
  out.over = vp_perf.over_budget_frames;
  out.dropped = vp_perf.dropped_frames;
#else
  out.frame_us = 0;
  out.show_us = 0;
  out.over = 0;
  out.dropped = 0;
#endif
  out.heap = 0;
}

static void vpab_push_metrics(uint8_t channel, const CRGB* final_bytes, uint16_t count,
                              uint32_t frame, uint32_t now_us, uint32_t dt_us,
                              uint32_t quant_us) {
  if (!diag_capture_can_push(sizeof(vpab_metric_scratch))) {
    return;
  }
  memset(&vpab_metric_scratch, 0, sizeof(vpab_metric_scratch));
  vpab_fill_self_shadow_metrics(vpab_metric_scratch, channel, final_bytes, count, dt_us, quant_us);
  diag_capture_try_push(DIAG_KIND_VPAB_METRICS, 0, frame, now_us,
                        &vpab_metric_scratch, sizeof(vpab_metric_scratch));
}

static void vpab_push_bytes(uint8_t channel, const CRGB* final_bytes, uint16_t requested_count,
                            uint32_t frame, uint32_t now_us, uint32_t quant_us) {
  uint16_t count = requested_count;
  if (count > LED_COUNT_VALUE) {
    count = LED_COUNT_VALUE;
  }
  if (!diag_capture_can_push(sizeof(vpab_bytes_scratch))) {
    return;
  }
  memset(&vpab_bytes_scratch, 0, sizeof(vpab_bytes_scratch));
  vpab_bytes_scratch.channel = channel;
  vpab_bytes_scratch.mode = vpab_mode_for_channel(channel);
  vpab_bytes_scratch.dither_step_value = dither_step;
  vpab_bytes_scratch.fastled_dither = vpab_fastled_dither_flag();
  vpab_bytes_scratch.leds = count;
  vpab_bytes_scratch.byte_count = count * 3U;
  vpab_bytes_scratch.render_us = vpab_channel_render_us(channel);
  vpab_bytes_scratch.quant_us = quant_us;
#if ENABLE_VP_PERF_AUDIT
  vpab_bytes_scratch.frame_us = vp_perf_avg(vp_perf.frame);
  vpab_bytes_scratch.show_us = vp_perf_avg(vp_perf.show);
  vpab_bytes_scratch.over = vp_perf.over_budget_frames;
  vpab_bytes_scratch.dropped = vp_perf.dropped_frames;
#else
  vpab_bytes_scratch.frame_us = 0;
  vpab_bytes_scratch.show_us = 0;
  vpab_bytes_scratch.over = 0;
  vpab_bytes_scratch.dropped = 0;
#endif
  for (uint16_t i = 0; i < count; i++) {
    uint16_t base = i * 3U;
    vpab_bytes_scratch.bytes[base] = final_bytes[i].r;
    vpab_bytes_scratch.bytes[base + 1] = final_bytes[i].g;
    vpab_bytes_scratch.bytes[base + 2] = final_bytes[i].b;
  }
  diag_capture_try_push(DIAG_KIND_VPAB_BYTES, 0, frame, now_us,
                        &vpab_bytes_scratch, sizeof(vpab_bytes_scratch));
}

static void vpab_emit_metric_row(const DiagRecordHeader& header, const VPABMetricPayload& payload) {
  USBSerial.print("VPAB,ver=1,seq=");
  USBSerial.print(header.seq);
  USBSerial.print(",mode=");
  USBSerial.print(payload.mode);
  USBSerial.print(",channel=");
  USBSerial.print(vpab_channel_name(payload.channel));
  USBSerial.print(",scenario=self_shadow,shadow=self,memory_metrics=absent");
  USBSerial.print(",frame=");
  USBSerial.print(header.frame);
  USBSerial.print(",t_ms=");
  USBSerial.print(payload.t_ms);
  USBSerial.print(",dt_ms=");
  USBSerial.print(float(payload.dt_us) / 1000.0f, 2);
  USBSerial.print(",leds=");
  USBSerial.print(payload.leds);
  USBSerial.print(",truncated=");
  USBSerial.print(payload.truncated);
  USBSerial.print(",dither_step=");
  USBSerial.print(payload.dither_step_value);
  USBSerial.print(",fastled_dither=");
  USBSerial.print(payload.fastled_dither);
  USBSerial.print(",mae8=");
  USBSerial.print(payload.mae8, 3);
  USBSerial.print(",p95_abs8=");
  USBSerial.print(payload.p95_abs8);
  USBSerial.print(",max_abs8=");
  USBSerial.print(payload.max_abs8);
  USBSerial.print(",changed_led_pct=");
  USBSerial.print(payload.changed_led_pct, 2);
  USBSerial.print(",changed_channel_pct=");
  USBSerial.print(payload.changed_channel_pct, 2);
  USBSerial.print(",energy_a=");
  USBSerial.print(payload.energy_a);
  USBSerial.print(",energy_b=");
  USBSerial.print(payload.energy_b);
  USBSerial.print(",energy_delta_pct=");
  USBSerial.print(payload.energy_delta_pct, 2);
  USBSerial.print(",com_a=");
  USBSerial.print(payload.com_a, 2);
  USBSerial.print(",com_b=");
  USBSerial.print(payload.com_b, 2);
  USBSerial.print(",com_delta_leds=");
  USBSerial.print(payload.com_delta_leds, 2);
  USBSerial.print(",com_slope_delta_pct=");
  USBSerial.print(payload.com_slope_delta_pct, 2);
  USBSerial.print(",hue_delta_p95=");
  USBSerial.print(payload.hue_delta_p95);
  USBSerial.print(",sat_delta_p95=");
  USBSerial.print(payload.sat_delta_p95);
  USBSerial.print(",white_bias_score=");
  USBSerial.print(payload.white_bias_score, 4);
  USBSerial.print(",flicker_score=");
  USBSerial.print(payload.flicker_score, 4);
  USBSerial.print(",render_us=");
  USBSerial.print(payload.render_us);
  USBSerial.print(",quant_us=");
  USBSerial.print(payload.quant_us);
  USBSerial.print(",show_us=");
  USBSerial.print(payload.show_us);
  USBSerial.print(",frame_us=");
  USBSerial.print(payload.frame_us);
  USBSerial.print(",over=");
  USBSerial.print(payload.over);
  USBSerial.print(",dropped=");
  USBSerial.print(payload.dropped);
  USBSerial.print(",cal_source=");
  USBSerial.print(calibration_source_name());
  USBSerial.print(",cal_valid=");
  USBSerial.print(calibration_valid ? 1 : 0);
  USBSerial.print(",heap=");
  USBSerial.println(payload.heap);
}

static void vpab_emit_bytes_as_metric_row(const DiagRecordHeader& header, const VPABBytesPayload& bytes,
                                          uint32_t dt_us) {
  VPABByteAggregate aggregate = vpab_aggregate_bytes(bytes);
  uint16_t count = bytes.leds;
  if (count > LED_COUNT_VALUE) {
    count = LED_COUNT_VALUE;
  }

  USBSerial.print("VPABB,ver=1,seq=");
  USBSerial.print(header.seq);
  USBSerial.print(",mode=");
  USBSerial.print(bytes.mode);
  USBSerial.print(",channel=");
  USBSerial.print(vpab_channel_name(bytes.channel));
  USBSerial.print(",frame=");
  USBSerial.print(header.frame);
  USBSerial.print(",t_ms=");
  USBSerial.print(header.t_us / 1000U);
  USBSerial.print(",dt_ms=");
  USBSerial.print(float(dt_us) / 1000.0f, 2);
  USBSerial.print(",leds=");
  USBSerial.print(count);
  USBSerial.print(",bytes=");
  USBSerial.print(bytes.byte_count);
  USBSerial.print(",hash=0x");
  USBSerial.print(aggregate.hash, HEX);
  USBSerial.print(",energy=");
  USBSerial.print(aggregate.energy);
  USBSerial.print(",r_sum=");
  USBSerial.print(aggregate.r_sum);
  USBSerial.print(",g_sum=");
  USBSerial.print(aggregate.g_sum);
  USBSerial.print(",b_sum=");
  USBSerial.print(aggregate.b_sum);
  USBSerial.print(",nonzero_led_pct=");
  USBSerial.print((count > 0) ? (float(aggregate.nonzero_leds) * 100.0f / float(count)) : 0.0f, 2);
  USBSerial.print(",com=");
  USBSerial.print(aggregate.com, 2);
  USBSerial.print(",sat_avg=");
  USBSerial.print(aggregate.saturation_avg, 2);
  USBSerial.print(",white_bias_avg=");
  USBSerial.print(aggregate.white_bias_avg, 2);
  USBSerial.print(",max_luma=");
  USBSerial.print(aggregate.max_luma);
  USBSerial.print(",render_us=");
  USBSerial.print(bytes.render_us);
  USBSerial.print(",quant_us=");
  USBSerial.print(bytes.quant_us);
  USBSerial.print(",show_us=");
  USBSerial.print(bytes.show_us);
  USBSerial.print(",frame_us=");
  USBSerial.print(bytes.frame_us);
  USBSerial.print(",over=");
  USBSerial.print(bytes.over);
  USBSerial.print(",dropped=");
  USBSerial.println(bytes.dropped);

  CRGB scratch[LED_COUNT_VALUE];
  for (uint16_t i = 0; i < count; i++) {
    uint16_t base = i * 3U;
    scratch[i].r = bytes.bytes[base];
    scratch[i].g = bytes.bytes[base + 1];
    scratch[i].b = bytes.bytes[base + 2];
  }

  VPABMetricPayload metric = {};
  vpab_fill_self_shadow_metrics(metric, bytes.channel, scratch, count, 0, bytes.quant_us);
  metric.mode = bytes.mode;
  metric.dither_step_value = bytes.dither_step_value;
  metric.fastled_dither = bytes.fastled_dither;
  metric.t_ms = header.t_us / 1000U;
  metric.dt_us = dt_us;
  metric.render_us = bytes.render_us;
  metric.frame_us = bytes.frame_us;
  metric.show_us = bytes.show_us;
  metric.over = bytes.over;
  metric.dropped = bytes.dropped;
  vpab_emit_metric_row(header, metric);
}

static void vpab_emit_context_row() {
  VPABRenderContext context = vpab_capture_read_render_context();
  USBSerial.print("VPABC,ver=1,primary_mode=");
  USBSerial.print(context.primary_mode);
  USBSerial.print(",primary_config_mode=");
  USBSerial.print(context.primary_config_mode);
  USBSerial.print(",secondary_mode=");
  USBSerial.print(context.secondary_mode);
  USBSerial.print(",smart_enabled=");
  USBSerial.print(context.smart_enabled);
  USBSerial.print(",hooks_enabled=");
  USBSerial.print(context.hooks_enabled);
  USBSerial.print(",manual_owner_active=");
  USBSerial.print(context.manual_owner_active);
  USBSerial.print(",edge_enabled=");
  USBSerial.print(context.edge_enabled);
  USBSerial.print(",edge_mode=");
  USBSerial.print(context.edge_mode);
  USBSerial.print(",edge_strength_milli=");
  USBSerial.print(context.edge_strength_milli);
  USBSerial.print(",edge_effective_strength_milli=");
  USBSerial.println(context.edge_effective_strength_milli);
}

VPABCaptureMode vpab_capture_parse_mode(const char* text, VPABCaptureMode fallback) {
  if (text == nullptr || text[0] == 0 || strcmp(text, "metrics") == 0) {
    return fallback;
  }
  if (strcmp(text, "bytes") == 0) {
    return VPAB_CAPTURE_BYTES;
  }
  if (strcmp(text, "both") == 0) {
    return VPAB_CAPTURE_BOTH;
  }
  return fallback;
}

void vpab_capture_reset() {
  portENTER_CRITICAL(&vpab_capture_mux);
  vpab_capture_state.active = false;
  vpab_capture_state.once = false;
  vpab_capture_state.every_n = DIAG_VPAB_DEFAULT_EVERY_N;
  vpab_capture_state.frame = 0;
  vpab_capture_state.seq = 0;
  vpab_capture_state.last_emit_us = 0;
  vpab_capture_state.mode = VPAB_CAPTURE_METRICS;
  portEXIT_CRITICAL(&vpab_capture_mux);
  vpab_reset_histories();
  diag_capture_reset();
}

void vpab_capture_arm(bool once, uint16_t every_n, VPABCaptureMode mode) {
  if (every_n == 0) {
    every_n = 1;
  }
  if (every_n > DIAG_VPAB_MAX_EVERY_N) {
    every_n = DIAG_VPAB_MAX_EVERY_N;
  }
  uint8_t source = (calibration_source == CAL_SOURCE_DEFAULT_INVALID)
                     ? CAL_SOURCE_CONFIG
                     : calibration_source;
  calibration_refresh_status(source);
  if (!calibration_profile_valid()) {
    USBSerial.println("sberr[[");
    USBSerial.print("VPAB: calibration invalid CAL_SOURCE=");
    USBSerial.print(calibration_source_name());
    USBSerial.print(" CAL_VALID=");
    USBSerial.println(calibration_valid ? 1 : 0);
    USBSerial.println("]]");
    return;
  }
  diag_capture_reset();
  if (!diag_capture_start()) {
    portENTER_CRITICAL(&vpab_capture_mux);
    vpab_capture_state.active = false;
    portEXIT_CRITICAL(&vpab_capture_mux);
    return;
  }
  portENTER_CRITICAL(&vpab_capture_mux);
  vpab_capture_state.active = true;
  vpab_capture_state.once = once;
  vpab_capture_state.every_n = every_n;
  vpab_capture_state.frame = 0;
  vpab_capture_state.seq = 0;
  vpab_capture_state.last_emit_us = 0;
  vpab_capture_state.mode = mode;
  portEXIT_CRITICAL(&vpab_capture_mux);
  vpab_reset_histories();
  vpab_capture_print_status();
}

void vpab_capture_stop() {
  portENTER_CRITICAL(&vpab_capture_mux);
  vpab_capture_state.active = false;
  vpab_capture_state.once = false;
  portEXIT_CRITICAL(&vpab_capture_mux);
  diag_capture_stop();
}

void vpab_capture_tick(uint32_t primary_quant_us) {
  if (!diag_capture_is_capturing()) {
    return;
  }

  uint32_t now_us = uint32_t(esp_timer_get_time());
  uint32_t frame = 0;
  uint32_t dt_us = 0;
  VPABCaptureMode mode = VPAB_CAPTURE_METRICS;
  bool once = false;

  portENTER_CRITICAL(&vpab_capture_mux);
  if (!vpab_capture_state.active) {
    portEXIT_CRITICAL(&vpab_capture_mux);
    return;
  }
  vpab_capture_state.frame++;
  frame = vpab_capture_state.frame;
  uint16_t every = (vpab_capture_state.every_n == 0) ? 1 : vpab_capture_state.every_n;
  if (every > 1 && (frame % every) != 0) {
    portEXIT_CRITICAL(&vpab_capture_mux);
    return;
  }
  dt_us = (vpab_capture_state.last_emit_us == 0)
            ? 0
            : (now_us - vpab_capture_state.last_emit_us);
  vpab_capture_state.last_emit_us = now_us;
  vpab_capture_state.seq++;
  mode = vpab_capture_state.mode;
  once = vpab_capture_state.once;
  portEXIT_CRITICAL(&vpab_capture_mux);

  if (mode == VPAB_CAPTURE_METRICS ||
      mode == VPAB_CAPTURE_BOTH) {
    vpab_push_metrics(0, leds_out, CONFIG.LED_COUNT, frame,
                      now_us, dt_us, primary_quant_us);
  }
  if (mode == VPAB_CAPTURE_BYTES ||
      mode == VPAB_CAPTURE_BOTH) {
    vpab_push_bytes(0, leds_out, CONFIG.LED_COUNT, frame,
                    now_us, primary_quant_us);
  }

  if (ENABLE_SECONDARY_LEDS && leds_out_secondary != nullptr) {
    uint32_t secondary_quant_us = vp_secondary_quant_us_last;
    if (mode == VPAB_CAPTURE_METRICS ||
        mode == VPAB_CAPTURE_BOTH) {
      vpab_push_metrics(1, leds_out_secondary, SECONDARY_LED_COUNT, frame,
                        now_us, dt_us, secondary_quant_us);
    }
    if (mode == VPAB_CAPTURE_BYTES ||
        mode == VPAB_CAPTURE_BOTH) {
      vpab_push_bytes(1, leds_out_secondary, SECONDARY_LED_COUNT, frame,
                      now_us, secondary_quant_us);
    }
  }

#ifdef K1_PIN_EVIDENCE_V1
  k1_pin_evidence_push_frame(frame, now_us);
#endif

  if (once) {
    vpab_capture_stop();
  }
}

void vpab_capture_print_status() {
  DiagCaptureStatus st = diag_capture_status();
  VPABCaptureConfig snapshot;
  portENTER_CRITICAL(&vpab_capture_mux);
  snapshot = vpab_capture_state;
  portEXIT_CRITICAL(&vpab_capture_mux);
  USBSerial.println("sbr{{");
  USBSerial.print("VPAB: ");
  USBSerial.println(snapshot.active ? "running" : diag_capture_state_name(st.state));
  USBSerial.print("VPAB_SEQ: ");
  USBSerial.println(snapshot.seq);
  USBSerial.print("VPAB_FRAME: ");
  USBSerial.println(snapshot.frame);
  USBSerial.print("VPAB_EVERY_N: ");
  USBSerial.println(snapshot.every_n);
  USBSerial.print("VPAB_MODE: ");
  if (snapshot.mode == VPAB_CAPTURE_BYTES) {
    USBSerial.println("bytes");
  } else if (snapshot.mode == VPAB_CAPTURE_BOTH) {
    USBSerial.println("both");
  } else {
    USBSerial.println("metrics");
  }
  USBSerial.print("VPAB_RECORDS: captured=");
  USBSerial.print(st.captured);
  USBSerial.print(" dropped=");
  USBSerial.print(st.dropped);
  USBSerial.print(" high_water=");
  USBSerial.print(st.high_water);
  USBSerial.print(" overflowed=");
  USBSerial.println(st.overflowed ? 1 : 0);
  USBSerial.print("CAL_SOURCE: ");
  USBSerial.println(calibration_source_name());
  USBSerial.print("CAL_VALID: ");
  USBSerial.println(calibration_valid ? 1 : 0);
  USBSerial.print("CAL_PROFILE_LOADED: ");
  USBSerial.println(calibration_profile_loaded ? 1 : 0);
  USBSerial.println("VPAB_SCENARIO: self_shadow");
  USBSerial.println("VPAB_SHADOW: self");
  USBSerial.println("}}");
}

void vpab_capture_dump() {
  if (!diag_capture_begin_drain()) {
    USBSerial.println("sberr[[");
    USBSerial.println("VPAB_DUMP: capture must be stopped before dump");
    USBSerial.println("]]");
    return;
  }

  uint16_t rows = 0;
  uint16_t count = diag_capture_count();
  uint32_t bytes_prev_t_us[2] = { 0, 0 };
  bool bytes_prev_valid[2] = { false, false };
  vpab_emit_context_row();
  for (uint16_t i = 0; i < count; i++) {
    const DiagRecordSlot* slot = diag_capture_record_at(i);
    if (slot == nullptr) {
      continue;
    }
    if (slot->header.kind == DIAG_KIND_VPAB_METRICS &&
        slot->header.payload_bytes == sizeof(VPABMetricPayload)) {
      VPABMetricPayload payload;
      memcpy(&payload, slot->payload, sizeof(payload));
      vpab_emit_metric_row(slot->header, payload);
      rows++;
    } else if (slot->header.kind == DIAG_KIND_VPAB_BYTES &&
               slot->header.payload_bytes == sizeof(VPABBytesPayload)) {
      VPABBytesPayload payload;
      memcpy(&payload, slot->payload, sizeof(payload));
      uint8_t channel_index = (payload.channel == 1) ? 1 : 0;
      uint32_t dt_us = bytes_prev_valid[channel_index]
                         ? (slot->header.t_us - bytes_prev_t_us[channel_index])
                         : 0;
      bytes_prev_t_us[channel_index] = slot->header.t_us;
      bytes_prev_valid[channel_index] = true;
      vpab_emit_bytes_as_metric_row(slot->header, payload, dt_us);
      rows++;
    }
  }

  diag_capture_end_drain();
  DiagCaptureStatus st = diag_capture_status();
  USBSerial.println("sbr{{");
  USBSerial.print("VPAB_DUMP: rows=");
  USBSerial.print(rows);
  USBSerial.print(" records=");
  USBSerial.print(st.count);
  USBSerial.print(" dropped=");
  USBSerial.print(st.dropped);
  USBSerial.print(" corrupt=");
  USBSerial.print(st.corrupt);
  USBSerial.print(" overflowed=");
  USBSerial.println(st.overflowed ? 1 : 0);
  USBSerial.println("}}");
}

void vpab_capture_dump_frames() {
  if (!diag_capture_begin_drain()) {
    USBSerial.println("K1DF_ERROR,ver=1,reason=capture_not_stopped");
    return;
  }

  DiagCaptureStatus start_status = diag_capture_status();
  uint16_t count = diag_capture_count();
  uint16_t rows = 0;
  uint32_t chunks = 0;

  USBSerial.print("K1DF_BEGIN,ver=");
  USBSerial.print(DIAG_FRAME_STREAM_VERSION);
  USBSerial.print(",records=");
  USBSerial.print(count);
  USBSerial.print(",captured=");
  USBSerial.print(start_status.captured);
  USBSerial.print(",dropped=");
  USBSerial.print(start_status.dropped);
  USBSerial.print(",corrupt=");
  USBSerial.print(start_status.corrupt);
  USBSerial.print(",overflowed=");
  USBSerial.print(start_status.overflowed ? 1 : 0);
  USBSerial.print(",payload_max=");
  USBSerial.print(DIAG_CAPTURE_MAX_PAYLOAD_BYTES);
  USBSerial.print(",chunk_bytes=");
  USBSerial.println(DIAG_FRAME_CHUNK_BYTES);

  for (uint16_t i = 0; i < count; i++) {
    const DiagRecordSlot* slot = diag_capture_record_at(i);
    if (slot == nullptr) {
      continue;
    }

    uint16_t payload_len = slot->header.payload_bytes;
    const uint8_t* payload = slot->payload;
    uint16_t chunk_count = (payload_len == 0)
                             ? 0
                             : uint16_t((payload_len + DIAG_FRAME_CHUNK_BYTES - 1U) /
                                        DIAG_FRAME_CHUNK_BYTES);
    uint32_t payload_crc = vpab_crc32_bytes(payload, payload_len);

    USBSerial.print("K1DFR,ver=");
    USBSerial.print(DIAG_FRAME_STREAM_VERSION);
    USBSerial.print(",seq=");
    USBSerial.print(slot->header.seq);
    USBSerial.print(",kind=");
    USBSerial.print(slot->header.kind);
    USBSerial.print(",frame=");
    USBSerial.print(slot->header.frame);
    USBSerial.print(",t_us=");
    USBSerial.print(slot->header.t_us);
    USBSerial.print(",flags=");
    USBSerial.print(slot->header.flags);
    USBSerial.print(",len=");
    USBSerial.print(payload_len);
    USBSerial.print(",crc=0x");
    vpab_print_u32_hex8(payload_crc);
    USBSerial.print(",chunks=");
    USBSerial.println(chunk_count);

    uint16_t offset = 0;
    for (uint16_t chunk_index = 0; chunk_index < chunk_count; chunk_index++) {
      uint16_t remaining = payload_len - offset;
      uint16_t chunk_len = (remaining > DIAG_FRAME_CHUNK_BYTES)
                             ? DIAG_FRAME_CHUNK_BYTES
                             : remaining;
      uint32_t chunk_crc = vpab_crc32_bytes(payload + offset, chunk_len);
      USBSerial.print("K1DFC,ver=");
      USBSerial.print(DIAG_FRAME_STREAM_VERSION);
      USBSerial.print(",seq=");
      USBSerial.print(slot->header.seq);
      USBSerial.print(",idx=");
      USBSerial.print(chunk_index);
      USBSerial.print(",off=");
      USBSerial.print(offset);
      USBSerial.print(",len=");
      USBSerial.print(chunk_len);
      USBSerial.print(",crc=0x");
      vpab_print_u32_hex8(chunk_crc);
      USBSerial.print(",hex=");
      vpab_print_payload_hex(payload + offset, chunk_len);
      USBSerial.println();
      offset += chunk_len;
      chunks++;
    }
    rows++;
  }

  diag_capture_end_drain();
  DiagCaptureStatus end_status = diag_capture_status();
  USBSerial.print("K1DF_END,ver=");
  USBSerial.print(DIAG_FRAME_STREAM_VERSION);
  USBSerial.print(",records=");
  USBSerial.print(rows);
  USBSerial.print(",chunks=");
  USBSerial.print(chunks);
  USBSerial.print(",dropped=");
  USBSerial.print(end_status.dropped);
  USBSerial.print(",corrupt=");
  USBSerial.print(end_status.corrupt);
  USBSerial.print(",overflowed=");
  USBSerial.println(end_status.overflowed ? 1 : 0);
}

#else
VPABCaptureMode vpab_capture_parse_mode(const char*, VPABCaptureMode fallback) { return fallback; }
void vpab_capture_reset() {}
void vpab_capture_arm(bool, uint16_t, VPABCaptureMode) {}
void vpab_capture_stop() {}
void vpab_capture_set_render_context(const VPABRenderContext&) {}
void vpab_capture_tick(uint32_t) {}
void vpab_capture_print_status() {}
void vpab_capture_dump() {}
void vpab_capture_dump_frames() {}
#endif
