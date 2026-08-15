/*----------------------------------------
  K1 AP CAPTURE / TELEMETRY (diagnostics) — implementation
  ----------------------------------------
  Bodies lifted verbatim from serial_menu.h (Phase A Lane 2, S1). The whole
  unit is gated on `ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`, set only
  in the non-shippable probe envs, so this TU compiles to NOTHING in
  production. The capture buffers/counters (formerly file-scope `static` in the
  single-include serial_menu.h) are defined here with external linkage and
  declared `extern` in the header, so the call sites remaining in serial_menu.h
  reference the same storage.
*/

// Gate FIRST, BEFORE any #include. In production (k1_hardware) the probe gate
// is OFF, so this TU preprocesses to NOTHING — no "globals.h" pull-in, hence no
// static-initialiser constructor (`_GLOBAL__sub_I_…`) added to the production
// link. (Including the header unconditionally added +160 B of global-ctor code
// to k1_hardware even with the body gated out — globals.h declares
// non-trivially-constructed globals whose guard inits emit per-TU.)
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG

#include "k1_ap_capture_telemetry.h"
#include "serial_parse_helpers.h"   // vp_parse_bool
#include <stdlib.h>                 // atol
#include <string.h>                 // strcmp

// ---- Capture state (external linkage; initialisers verbatim from serial_menu.h)
bool AP_FRONTEND_DEBUG_ENABLED = false;
APNovCaptureSample AP_NOV_CAPTURE_BUFFER[AP_NOV_CAPTURE_CAPACITY];
uint16_t AP_NOV_CAPTURE_COUNT = 0;
uint32_t AP_NOV_CAPTURE_DROPPED = 0;
uint32_t AP_NOV_CAPTURE_START_MS = 0;
uint32_t AP_NOV_CAPTURE_END_MS = 0;
uint32_t AP_NOV_CAPTURE_LAST_EMIT = 0;
bool AP_NOV_CAPTURE_ACTIVE = false;
APCadenceCaptureSample* AP_CAD_CAPTURE_BUFFER = nullptr;
uint16_t AP_CAD_CAPTURE_COUNT = 0;
uint32_t AP_CAD_CAPTURE_DROPPED = 0;
uint32_t AP_CAD_CAPTURE_START_MS = 0;
uint32_t AP_CAD_CAPTURE_END_MS = 0;
uint32_t AP_CAD_CAPTURE_LAST_EMIT = 0;
uint32_t AP_CAD_CAPTURE_LAST_EMIT_MS = 0;
bool AP_CAD_CAPTURE_ACTIVE = false;
bool AP_CAD_CAPTURE_ALLOC_FAILED = false;
bool AP_CAD_SOAK_ACTIVE = false;
uint32_t AP_CAD_SOAK_START_MS = 0;
uint32_t AP_CAD_SOAK_END_MS = 0;
uint32_t AP_CAD_SOAK_FIRST_FRAME_MS = 0;
uint32_t AP_CAD_SOAK_LAST_FRAME_MS = 0;
uint32_t AP_CAD_SOAK_FIRST_EMIT_MS = 0;
uint32_t AP_CAD_SOAK_LAST_EMIT_MS = 0;
uint32_t AP_CAD_SOAK_LAST_EMIT = 0;
uint32_t AP_CAD_SOAK_PREV_FRAME = 0;
uint32_t AP_CAD_SOAK_PREV_FRAME_MS = 0;
uint32_t AP_CAD_SOAK_ROW_COUNT = 0;
uint32_t AP_CAD_SOAK_EMITTED_COUNT = 0;
uint32_t AP_CAD_SOAK_I2S_NOT_OK = 0;
uint32_t AP_CAD_SOAK_BYTES_MISMATCH = 0;
uint32_t AP_CAD_SOAK_FRAME_GAPS = 0;
uint32_t AP_CAD_SOAK_TIMESTAMP_REGRESSIONS = 0;
uint32_t AP_CAD_SOAK_CORE_BAD = 0;
uint32_t AP_CAD_SOAK_ACTIVE_OVER_7500 = 0;
uint32_t AP_CAD_SOAK_EMITTED_ACTIVE_OVER_7500 = 0;
uint32_t AP_CAD_SOAK_ACTIVE_MAX_US = 0;
uint16_t AP_CAD_SOAK_WORST_USED = 0;
bool AP_CAD_SOAK_HAVE_PREV = false;
APCadenceCaptureSample AP_CAD_SOAK_WORST[AP_CAD_SOAK_WORST_COUNT];
uint32_t AP_CAD_SOAK_ACTIVE_HIST[AP_CAD_SOAK_HIST_BUCKETS];

// ---- Capture handlers (verbatim from serial_menu.h 644-1397) ---------------
uint16_t ap_nov_capture_q16(float value) {
  if (!isfinite(value) || value <= 0.0f) {
    return 0;
  }
  if (value >= 1.0f) {
    return 65535U;
  }
  return (uint16_t)(value * 65535.0f + 0.5f);
}

uint16_t ap_nov_capture_q8_8(float value) {
  if (!isfinite(value) || value <= 0.0f) {
    return 0;
  }
  if (value >= 255.996f) {
    return 65535U;
  }
  return (uint16_t)(value * 256.0f + 0.5f);
}

void ap_nov_capture_print_q16(uint16_t value) {
  USBSerial.print((float)value / 65535.0f, 5);
}

void ap_nov_capture_print_q8_8(uint16_t value) {
  USBSerial.print((float)value / 256.0f, 5);
}

void ap_nov_capture_status() {
  tx_begin();
  USBSerial.print("NOV_CAPTURE: active=");
  USBSerial.print(vp_bool_text(AP_NOV_CAPTURE_ACTIVE));
  USBSerial.print(" count=");
  USBSerial.print(AP_NOV_CAPTURE_COUNT);
  USBSerial.print(" capacity=");
  USBSerial.print(AP_NOV_CAPTURE_CAPACITY);
  USBSerial.print(" dropped=");
  USBSerial.print(AP_NOV_CAPTURE_DROPPED);
  USBSerial.print(" start_ms=");
  USBSerial.print(AP_NOV_CAPTURE_START_MS);
  USBSerial.print(" end_ms=");
  USBSerial.println(AP_NOV_CAPTURE_END_MS);
  tx_end();
}

void ap_nov_capture_clear() {
  AP_NOV_CAPTURE_ACTIVE = false;
  AP_NOV_CAPTURE_COUNT = 0;
  AP_NOV_CAPTURE_DROPPED = 0;
  AP_NOV_CAPTURE_START_MS = 0;
  AP_NOV_CAPTURE_END_MS = 0;
  AP_NOV_CAPTURE_LAST_EMIT = k1_tempo_debug_read().emit_count;
}

bool ap_nov_capture_arm(uint32_t duration_ms) {
  if (duration_ms == 0 || duration_ms > AP_NOV_CAPTURE_MAX_MS) {
    return false;
  }
  AP_NOV_CAPTURE_COUNT = 0;
  AP_NOV_CAPTURE_DROPPED = 0;
  AP_NOV_CAPTURE_START_MS = millis();
  AP_NOV_CAPTURE_END_MS = AP_NOV_CAPTURE_START_MS + duration_ms;
  AP_NOV_CAPTURE_LAST_EMIT = k1_tempo_debug_read().emit_count;
  AP_NOV_CAPTURE_ACTIVE = true;
  return true;
}

void ap_nov_capture_tick(uint32_t t_now, const K1TempoDebugSnapshot& td) {
  if (!AP_NOV_CAPTURE_ACTIVE) {
    return;
  }
  if ((int32_t)(t_now - AP_NOV_CAPTURE_END_MS) >= 0) {
    AP_NOV_CAPTURE_ACTIVE = false;
    return;
  }
  if (td.emit_count == AP_NOV_CAPTURE_LAST_EMIT) {
    return;
  }
  AP_NOV_CAPTURE_LAST_EMIT = td.emit_count;
  if (AP_NOV_CAPTURE_COUNT >= AP_NOV_CAPTURE_CAPACITY) {
    AP_NOV_CAPTURE_DROPPED++;
    return;
  }

  APNovCaptureSample& sample = AP_NOV_CAPTURE_BUFFER[AP_NOV_CAPTURE_COUNT++];
  sample.t_ms = td.last_emit_ms;
  sample.emit_count = td.emit_count;
  sample.novelty_q16 = ap_nov_capture_q16(td.last_novelty);
  sample.scaled_novelty_q8_8 = ap_nov_capture_q8_8(td.last_scaled_novelty);
  sample.scale_q8_8 = ap_nov_capture_q8_8(td.novelty_scale);
  sample.flags = (td.silence_detected ? 0x01 : 0x00) | (td.acf_valid ? 0x02 : 0x00);
  sample.reserved = 0;
}

void ap_nov_capture_dump() {
  AP_NOV_CAPTURE_ACTIVE = false;
  USBSerial.print("NOV_CAPTURE_BEGIN,count=");
  USBSerial.print(AP_NOV_CAPTURE_COUNT);
  USBSerial.print(",capacity=");
  USBSerial.print(AP_NOV_CAPTURE_CAPACITY);
  USBSerial.print(",dropped=");
  USBSerial.print(AP_NOV_CAPTURE_DROPPED);
  USBSerial.print(",start_ms=");
  USBSerial.print(AP_NOV_CAPTURE_START_MS);
  USBSerial.print(",end_ms=");
  USBSerial.println(AP_NOV_CAPTURE_END_MS);
  for (uint16_t i = 0; i < AP_NOV_CAPTURE_COUNT; i++) {
    const APNovCaptureSample& sample = AP_NOV_CAPTURE_BUFFER[i];
    USBSerial.print("NOV,t=");
    USBSerial.print(sample.t_ms);
    USBSerial.print(",emit=");
    USBSerial.print(sample.emit_count);
    USBSerial.print(",nov=");
    ap_nov_capture_print_q16(sample.novelty_q16);
    USBSerial.print(",nov_scaled=");
    ap_nov_capture_print_q8_8(sample.scaled_novelty_q8_8);
    USBSerial.print(",scale=");
    ap_nov_capture_print_q8_8(sample.scale_q8_8);
    USBSerial.print(",sil=");
    USBSerial.print((sample.flags & 0x01) ? 1 : 0);
    USBSerial.print(",acf=");
    USBSerial.print((sample.flags & 0x02) ? 1 : 0);
    USBSerial.println(",src=buf");
  }
  USBSerial.print("NOV_CAPTURE_DONE,count=");
  USBSerial.print(AP_NOV_CAPTURE_COUNT);
  USBSerial.print(",dropped=");
  USBSerial.println(AP_NOV_CAPTURE_DROPPED);
}

uint16_t ap_capture_u16_sat(uint32_t value) {
  return value > 0xFFFFUL ? 0xFFFFU : (uint16_t)value;
}

int16_t ap_capture_i16_sat(int32_t value) {
  if (value > 32767L) return 32767;
  if (value < -32768L) return -32768;
  return (int16_t)value;
}

bool ap_cad_capture_ensure_buffer() {
  AP_CAD_CAPTURE_ALLOC_FAILED = false;
  if (AP_CAD_CAPTURE_BUFFER != nullptr) {
    return true;
  }
  AP_CAD_CAPTURE_BUFFER = (APCadenceCaptureSample*)heap_caps_malloc(
    sizeof(APCadenceCaptureSample) * AP_CAD_CAPTURE_CAPACITY,
    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (AP_CAD_CAPTURE_BUFFER == nullptr) {
    AP_CAD_CAPTURE_BUFFER = (APCadenceCaptureSample*)heap_caps_malloc(
      sizeof(APCadenceCaptureSample) * AP_CAD_CAPTURE_CAPACITY,
      MALLOC_CAP_8BIT);
  }
  AP_CAD_CAPTURE_ALLOC_FAILED = (AP_CAD_CAPTURE_BUFFER == nullptr);
  return !AP_CAD_CAPTURE_ALLOC_FAILED;
}

void ap_cad_capture_status() {
  tx_begin();
  USBSerial.print("APCAD_CAPTURE: active=");
  USBSerial.print(vp_bool_text(AP_CAD_CAPTURE_ACTIVE));
  USBSerial.print(" count=");
  USBSerial.print(AP_CAD_CAPTURE_COUNT);
  USBSerial.print(" capacity=");
  USBSerial.print(AP_CAD_CAPTURE_CAPACITY);
  USBSerial.print(" dropped=");
  USBSerial.print(AP_CAD_CAPTURE_DROPPED);
  USBSerial.print(" start_ms=");
  USBSerial.print(AP_CAD_CAPTURE_START_MS);
  USBSerial.print(" end_ms=");
  USBSerial.print(AP_CAD_CAPTURE_END_MS);
  USBSerial.print(" alloc=");
  USBSerial.println(AP_CAD_CAPTURE_ALLOC_FAILED ? "fail" : (AP_CAD_CAPTURE_BUFFER ? "ok" : "none"));
  tx_end();
}

void ap_cad_capture_clear() {
  AP_CAD_CAPTURE_ACTIVE = false;
  AP_CAD_CAPTURE_COUNT = 0;
  AP_CAD_CAPTURE_DROPPED = 0;
  AP_CAD_CAPTURE_START_MS = 0;
  AP_CAD_CAPTURE_END_MS = 0;
  K1TempoDebugSnapshot td = k1_tempo_debug_read();
  AP_CAD_CAPTURE_LAST_EMIT = td.emit_count;
  AP_CAD_CAPTURE_LAST_EMIT_MS = td.last_emit_ms;
}

bool ap_cad_capture_arm(uint32_t duration_ms) {
  if (duration_ms == 0 || duration_ms > AP_CAD_CAPTURE_MAX_MS) {
    return false;
  }
  if (!ap_cad_capture_ensure_buffer()) {
    return false;
  }
  AP_CAD_CAPTURE_COUNT = 0;
  AP_CAD_CAPTURE_DROPPED = 0;
  AP_CAD_CAPTURE_START_MS = millis();
  AP_CAD_CAPTURE_END_MS = AP_CAD_CAPTURE_START_MS + duration_ms;
  K1TempoDebugSnapshot td = k1_tempo_debug_read();
  AP_CAD_CAPTURE_LAST_EMIT = td.emit_count;
  AP_CAD_CAPTURE_LAST_EMIT_MS = td.last_emit_ms;
  AP_CAD_CAPTURE_ACTIVE = true;
  return true;
}

APCadenceCaptureSample ap_cad_make_sample(const APCadenceFrameInput& frame, bool emitted, uint32_t emit_delta_ms) {
  APCadenceCaptureSample sample = {};
  sample.i2s_read_start_us = frame.i2s.read_start_us;
  sample.i2s_read_return_us = frame.i2s.read_return_us;
  sample.newest_sample_estimate_us = frame.i2s.newest_sample_estimate_us;
  sample.oldest_sample_estimate_us = frame.i2s.oldest_sample_estimate_us;
  sample.ap_publish_us = frame.i2s.ap_publish_us;
  sample.boot_ms = frame.boot_ms;
  sample.frame_index = frame.frame_index;
  sample.capture_sequence = frame.i2s.capture_sequence;
  sample.frame_ms = frame.frame_ms;
  sample.emit_count = frame.tempo.emit_count;
  sample.emit_ms = frame.tempo.last_emit_ms;
  sample.i2s_read_elapsed_us = frame.i2s.elapsed_us;
  sample.gdft_elapsed_us = frame.gdft_elapsed_us;
  sample.novelty_elapsed_us = frame.novelty_elapsed_us;
  sample.total_ap_loop_elapsed_us = frame.total_ap_loop_elapsed_us;
  sample.stage = frame.stage;
  sample.sample_rate = ap_capture_u16_sat(CONFIG.SAMPLE_RATE);
  sample.samples_per_chunk = ap_capture_u16_sat(CONFIG.SAMPLES_PER_CHUNK);
  sample.dma_frame_num = ap_capture_u16_sat(CONFIG.SAMPLES_PER_CHUNK);
  sample.bytes_requested = ap_capture_u16_sat(frame.i2s.bytes_requested);
  sample.bytes_read = ap_capture_u16_sat(frame.i2s.bytes_read);
  sample.samples_read = ap_capture_u16_sat(frame.i2s.samples_read);
  sample.emit_delta_ms = ap_capture_u16_sat(emit_delta_ms);
  sample.declared_ap_hz_q8_8 = ap_nov_capture_q8_8(frame.tempo.declared_ap_frame_hz);
  sample.declared_nov_hz_q8_8 = ap_nov_capture_q8_8(frame.tempo.declared_novelty_rate_hz);
  sample.novelty_q16 = ap_nov_capture_q16(frame.tempo.last_novelty);
  sample.scaled_novelty_q8_8 = ap_nov_capture_q8_8(frame.tempo.last_scaled_novelty);
  sample.winner_bpm_q8_8 = ap_nov_capture_q8_8(frame.tempo.winner_bpm);
  sample.top1_bpm_q8_8 = ap_nov_capture_q8_8(frame.tempo.top1_bpm);
  sample.v2_conf_ema_q16 = ap_nov_capture_q16(frame.tempo.v2_conf_ema);
  sample.v2_quality_q16 = ap_nov_capture_q16(frame.tempo.v2_quality);
  sample.v2_hist_share_q16 = ap_nov_capture_q16(frame.tempo.v2_hist_share_norm);
  sample.v2_prominence_q16 = ap_nov_capture_q16(frame.tempo.v2_prominence);
  sample.v2_periodicity_q16 = ap_nov_capture_q16(frame.tempo.v2_periodicity);
  sample.v2_peak_share_q16 = ap_nov_capture_q16(frame.tempo.v2_peak_share);
  sample.tempo_silence_elapsed_us = ap_capture_u16_sat(frame.tempo.silence_elapsed_us);
  sample.tempo_acf_elapsed_us = ap_capture_u16_sat(frame.tempo.acf_elapsed_us);
  sample.tempo_update_elapsed_us = ap_capture_u16_sat(frame.tempo.update_elapsed_us);
  sample.tempo_phase_elapsed_us = ap_capture_u16_sat(frame.tempo.phase_elapsed_us);
  sample.tempo_publish_elapsed_us = ap_capture_u16_sat(frame.tempo.publish_elapsed_us);
  sample.tempo_emit_elapsed_us = ap_capture_u16_sat(frame.tempo.emit_elapsed_us);
  sample.acf_lag_cursor = ap_capture_u16_sat(frame.tempo.acf_lag_cursor);
  sample.acf_publish_count = frame.tempo.acf_publish_count;
  sample.i2s_status = ap_capture_i16_sat(frame.i2s.status);
  sample.ap_core_id = frame.ap_core_id;
  sample.vp_core_id = frame.vp_core_id;
  sample.slot_bit_width = K1_I2S_SLOT_BIT_WIDTH_BITS;
  sample.slot_mode = K1_I2S_SLOT_MODE_STEREO;
  sample.dma_desc_num = K1_I2S_DMA_DESC_NUM;
  sample.k1_frame_ctr = (uint8_t)frame.tempo.frame_ctr;
  sample.tempo_decimation = (uint8_t)frame.tempo.novelty_decimation;
  sample.flags = (emitted ? 0x01 : 0x00)
    | (frame.tempo.silence_detected ? 0x02 : 0x00)
    | (frame.tempo.acf_valid ? 0x04 : 0x00)
    | (frame.i2s.status == 0 ? 0x08 : 0x00)
    | (frame.i2s.bytes_read == frame.i2s.bytes_requested ? 0x10 : 0x00)
    | ((frame.ap_core_id >= 0 && frame.vp_core_id >= 0 && frame.ap_core_id != frame.vp_core_id) ? 0x20 : 0x00)
    | (frame.tempo.v2_locked ? 0x40 : 0x00)
    | (frame.tempo.acf_spread_active ? 0x80 : 0x00);
  sample.sample_time_assumption_id = frame.i2s.sample_time_assumption_id;
  return sample;
}

uint32_t ap_cad_active_work_us(const APCadenceCaptureSample& sample) {
  return (sample.total_ap_loop_elapsed_us >= sample.i2s_read_elapsed_us)
    ? (sample.total_ap_loop_elapsed_us - sample.i2s_read_elapsed_us)
    : sample.total_ap_loop_elapsed_us;
}

void ap_cad_capture_tick(const APCadenceFrameInput& frame) {
  if (!AP_CAD_CAPTURE_ACTIVE) {
    return;
  }
  if ((int32_t)(frame.frame_ms - AP_CAD_CAPTURE_END_MS) >= 0) {
    AP_CAD_CAPTURE_ACTIVE = false;
    return;
  }
  if (AP_CAD_CAPTURE_BUFFER == nullptr || AP_CAD_CAPTURE_COUNT >= AP_CAD_CAPTURE_CAPACITY) {
    AP_CAD_CAPTURE_DROPPED++;
    return;
  }

  const bool emitted = frame.tempo.emit_count != AP_CAD_CAPTURE_LAST_EMIT;
  uint32_t emit_delta_ms = 0;
  if (emitted) {
    emit_delta_ms = (frame.tempo.last_emit_ms >= AP_CAD_CAPTURE_LAST_EMIT_MS)
      ? (frame.tempo.last_emit_ms - AP_CAD_CAPTURE_LAST_EMIT_MS)
      : 0;
    AP_CAD_CAPTURE_LAST_EMIT = frame.tempo.emit_count;
    AP_CAD_CAPTURE_LAST_EMIT_MS = frame.tempo.last_emit_ms;
  }

  AP_CAD_CAPTURE_BUFFER[AP_CAD_CAPTURE_COUNT++] = ap_cad_make_sample(frame, emitted, emit_delta_ms);
}

void ap_cad_soak_reset() {
  AP_CAD_SOAK_ACTIVE = false;
  AP_CAD_SOAK_START_MS = 0;
  AP_CAD_SOAK_END_MS = 0;
  AP_CAD_SOAK_FIRST_FRAME_MS = 0;
  AP_CAD_SOAK_LAST_FRAME_MS = 0;
  AP_CAD_SOAK_FIRST_EMIT_MS = 0;
  AP_CAD_SOAK_LAST_EMIT_MS = 0;
  AP_CAD_SOAK_PREV_FRAME = 0;
  AP_CAD_SOAK_PREV_FRAME_MS = 0;
  AP_CAD_SOAK_ROW_COUNT = 0;
  AP_CAD_SOAK_EMITTED_COUNT = 0;
  AP_CAD_SOAK_I2S_NOT_OK = 0;
  AP_CAD_SOAK_BYTES_MISMATCH = 0;
  AP_CAD_SOAK_FRAME_GAPS = 0;
  AP_CAD_SOAK_TIMESTAMP_REGRESSIONS = 0;
  AP_CAD_SOAK_CORE_BAD = 0;
  AP_CAD_SOAK_ACTIVE_OVER_7500 = 0;
  AP_CAD_SOAK_EMITTED_ACTIVE_OVER_7500 = 0;
  AP_CAD_SOAK_ACTIVE_MAX_US = 0;
  AP_CAD_SOAK_WORST_USED = 0;
  AP_CAD_SOAK_HAVE_PREV = false;
  for (uint16_t i = 0; i < AP_CAD_SOAK_HIST_BUCKETS; i++) {
    AP_CAD_SOAK_ACTIVE_HIST[i] = 0;
  }
  K1TempoDebugSnapshot td = k1_tempo_debug_read();
  AP_CAD_SOAK_LAST_EMIT = td.emit_count;
  AP_CAD_SOAK_LAST_EMIT_MS = td.last_emit_ms;
}

bool ap_cad_soak_arm(uint32_t duration_ms) {
  if (duration_ms == 0 || duration_ms > AP_CAD_SOAK_MAX_MS) {
    return false;
  }
  ap_cad_soak_reset();
  AP_CAD_SOAK_START_MS = millis();
  AP_CAD_SOAK_END_MS = AP_CAD_SOAK_START_MS + duration_ms;
  AP_CAD_SOAK_ACTIVE = true;
  return true;
}

void ap_cad_soak_record_worst(const APCadenceCaptureSample& sample, uint32_t active_us) {
  uint16_t insert_at = AP_CAD_SOAK_WORST_USED;
  if (AP_CAD_SOAK_WORST_USED < AP_CAD_SOAK_WORST_COUNT) {
    AP_CAD_SOAK_WORST_USED++;
  } else {
    uint32_t smallest_us = ap_cad_active_work_us(AP_CAD_SOAK_WORST[0]);
    insert_at = 0;
    for (uint16_t i = 1; i < AP_CAD_SOAK_WORST_COUNT; i++) {
      uint32_t value = ap_cad_active_work_us(AP_CAD_SOAK_WORST[i]);
      if (value < smallest_us) {
        smallest_us = value;
        insert_at = i;
      }
    }
    if (active_us <= smallest_us) {
      return;
    }
  }
  AP_CAD_SOAK_WORST[insert_at] = sample;
}

void ap_cad_soak_tick(const APCadenceFrameInput& frame) {
  if (!AP_CAD_SOAK_ACTIVE) {
    return;
  }
  if ((int32_t)(frame.frame_ms - AP_CAD_SOAK_END_MS) >= 0) {
    AP_CAD_SOAK_ACTIVE = false;
    return;
  }

  const bool emitted = frame.tempo.emit_count != AP_CAD_SOAK_LAST_EMIT;
  uint32_t emit_delta_ms = 0;
  if (emitted) {
    emit_delta_ms = (frame.tempo.last_emit_ms >= AP_CAD_SOAK_LAST_EMIT_MS)
      ? (frame.tempo.last_emit_ms - AP_CAD_SOAK_LAST_EMIT_MS)
      : 0;
    if (AP_CAD_SOAK_EMITTED_COUNT == 0) {
      AP_CAD_SOAK_FIRST_EMIT_MS = frame.tempo.last_emit_ms;
    }
    AP_CAD_SOAK_LAST_EMIT = frame.tempo.emit_count;
    AP_CAD_SOAK_LAST_EMIT_MS = frame.tempo.last_emit_ms;
    AP_CAD_SOAK_EMITTED_COUNT++;
  }

  const APCadenceCaptureSample sample = ap_cad_make_sample(frame, emitted, emit_delta_ms);
  const uint32_t active_us = ap_cad_active_work_us(sample);
  if (AP_CAD_SOAK_ROW_COUNT == 0) {
    AP_CAD_SOAK_FIRST_FRAME_MS = frame.frame_ms;
  }
  AP_CAD_SOAK_LAST_FRAME_MS = frame.frame_ms;
  if (AP_CAD_SOAK_HAVE_PREV) {
    if (frame.frame_index != AP_CAD_SOAK_PREV_FRAME + 1) {
      AP_CAD_SOAK_FRAME_GAPS++;
    }
    if (frame.frame_ms <= AP_CAD_SOAK_PREV_FRAME_MS) {
      AP_CAD_SOAK_TIMESTAMP_REGRESSIONS++;
    }
  }
  AP_CAD_SOAK_PREV_FRAME = frame.frame_index;
  AP_CAD_SOAK_PREV_FRAME_MS = frame.frame_ms;
  AP_CAD_SOAK_HAVE_PREV = true;

  AP_CAD_SOAK_ROW_COUNT++;
  if ((sample.flags & 0x08) == 0) AP_CAD_SOAK_I2S_NOT_OK++;
  if ((sample.flags & 0x10) == 0) AP_CAD_SOAK_BYTES_MISMATCH++;
  if ((sample.flags & 0x20) == 0) AP_CAD_SOAK_CORE_BAD++;
  if (active_us > 7500UL) {
    AP_CAD_SOAK_ACTIVE_OVER_7500++;
    if (emitted) AP_CAD_SOAK_EMITTED_ACTIVE_OVER_7500++;
  }
  if (active_us > AP_CAD_SOAK_ACTIVE_MAX_US) {
    AP_CAD_SOAK_ACTIVE_MAX_US = active_us;
  }
  uint16_t bucket = (uint16_t)(active_us / AP_CAD_SOAK_HIST_BUCKET_US);
  if (bucket >= AP_CAD_SOAK_HIST_BUCKETS) {
    bucket = AP_CAD_SOAK_HIST_BUCKETS - 1;
  }
  AP_CAD_SOAK_ACTIVE_HIST[bucket]++;
  ap_cad_soak_record_worst(sample, active_us);
}

uint32_t ap_cad_soak_hist_percentile(uint8_t percentile) {
  if (AP_CAD_SOAK_ROW_COUNT == 0) {
    return 0;
  }
  uint32_t target = (AP_CAD_SOAK_ROW_COUNT * (uint32_t)percentile + 99UL) / 100UL;
  if (target == 0) target = 1;
  uint32_t seen = 0;
  for (uint16_t i = 0; i < AP_CAD_SOAK_HIST_BUCKETS; i++) {
    seen += AP_CAD_SOAK_ACTIVE_HIST[i];
    if (seen >= target) {
      return ((uint32_t)i + 1UL) * AP_CAD_SOAK_HIST_BUCKET_US;
    }
  }
  return AP_CAD_SOAK_HIST_BUCKETS * AP_CAD_SOAK_HIST_BUCKET_US;
}

void ap_cad_soak_print_worst_sample(uint8_t rank, const APCadenceCaptureSample& sample) {
  USBSerial.print("APCAD_SOAK_WORST,ver=1,rank=");
  USBSerial.print(rank);
  USBSerial.print(",frame=");
  USBSerial.print(sample.frame_index);
  USBSerial.print(",t=");
  USBSerial.print(sample.frame_ms);
  USBSerial.print(",active_us=");
  USBSerial.print(ap_cad_active_work_us(sample));
  USBSerial.print(",total_us=");
  USBSerial.print(sample.total_ap_loop_elapsed_us);
  USBSerial.print(",i2s_us=");
  USBSerial.print(sample.i2s_read_elapsed_us);
  USBSerial.print(",gdft_us=");
  USBSerial.print(sample.gdft_elapsed_us);
  USBSerial.print(",novelty_us=");
  USBSerial.print(sample.novelty_elapsed_us);
  USBSerial.print(",tempo_acf_us=");
  USBSerial.print(sample.tempo_acf_elapsed_us);
  USBSerial.print(",tempo_update_us=");
  USBSerial.print(sample.tempo_update_elapsed_us);
  USBSerial.print(",tempo_emit_us=");
  USBSerial.print(sample.tempo_emit_elapsed_us);
  USBSerial.print(",emitted=");
  USBSerial.print((sample.flags & 0x01) ? 1 : 0);
  USBSerial.print(",acf_spread=");
  USBSerial.print((sample.flags & 0x80) ? 1 : 0);
  USBSerial.print(",acf_lag_cursor=");
  USBSerial.print(sample.acf_lag_cursor);
  USBSerial.print(",acf_pub=");
  USBSerial.print(sample.acf_publish_count);
  USBSerial.print(",win_bpm=");
  ap_nov_capture_print_q8_8(sample.winner_bpm_q8_8);
  USBSerial.print(",top1_bpm=");
  ap_nov_capture_print_q8_8(sample.top1_bpm_q8_8);
  USBSerial.println();
}

void ap_cad_soak_status() {
  float measured_ap_hz = 0.0f;
  float measured_nov_hz = 0.0f;
  if (AP_CAD_SOAK_ROW_COUNT >= 2 && AP_CAD_SOAK_LAST_FRAME_MS > AP_CAD_SOAK_FIRST_FRAME_MS) {
    measured_ap_hz = 1000.0f * (float)(AP_CAD_SOAK_ROW_COUNT - 1) /
      (float)(AP_CAD_SOAK_LAST_FRAME_MS - AP_CAD_SOAK_FIRST_FRAME_MS);
  }
  if (AP_CAD_SOAK_EMITTED_COUNT >= 2 && AP_CAD_SOAK_LAST_EMIT_MS > AP_CAD_SOAK_FIRST_EMIT_MS) {
    measured_nov_hz = 1000.0f * (float)(AP_CAD_SOAK_EMITTED_COUNT - 1) /
      (float)(AP_CAD_SOAK_LAST_EMIT_MS - AP_CAD_SOAK_FIRST_EMIT_MS);
  }

  USBSerial.print("APCAD_SOAK_DONE,ver=1,active=");
  USBSerial.print(AP_CAD_SOAK_ACTIVE ? 1 : 0);
  USBSerial.print(",rows=");
  USBSerial.print(AP_CAD_SOAK_ROW_COUNT);
  USBSerial.print(",emitted=");
  USBSerial.print(AP_CAD_SOAK_EMITTED_COUNT);
  USBSerial.print(",start_ms=");
  USBSerial.print(AP_CAD_SOAK_START_MS);
  USBSerial.print(",end_ms=");
  USBSerial.print(AP_CAD_SOAK_END_MS);
  USBSerial.print(",sample_rate=");
  USBSerial.print(CONFIG.SAMPLE_RATE);
  USBSerial.print(",samples_per_chunk=");
  USBSerial.print(CONFIG.SAMPLES_PER_CHUNK);
  USBSerial.print(",tempo_decim=");
  USBSerial.print(K1_TEMPO_NOVELTY_DECIMATION);
  USBSerial.print(",meas_ap_hz=");
  USBSerial.print(measured_ap_hz, 3);
  USBSerial.print(",meas_nov_hz=");
  USBSerial.print(measured_nov_hz, 3);
  USBSerial.print(",i2s_not_ok=");
  USBSerial.print(AP_CAD_SOAK_I2S_NOT_OK);
  USBSerial.print(",bytes_mismatch=");
  USBSerial.print(AP_CAD_SOAK_BYTES_MISMATCH);
  USBSerial.print(",frame_gap=");
  USBSerial.print(AP_CAD_SOAK_FRAME_GAPS);
  USBSerial.print(",timestamp_regression=");
  USBSerial.print(AP_CAD_SOAK_TIMESTAMP_REGRESSIONS);
  USBSerial.print(",core_bad=");
  USBSerial.print(AP_CAD_SOAK_CORE_BAD);
  USBSerial.print(",active_over_7500=");
  USBSerial.print(AP_CAD_SOAK_ACTIVE_OVER_7500);
  USBSerial.print(",emitted_active_over_7500=");
  USBSerial.print(AP_CAD_SOAK_EMITTED_ACTIVE_OVER_7500);
  USBSerial.print(",active_p95_us=");
  USBSerial.print(ap_cad_soak_hist_percentile(95));
  USBSerial.print(",active_max_us=");
  USBSerial.print(AP_CAD_SOAK_ACTIVE_MAX_US);
  USBSerial.print(",worst_count=");
  USBSerial.println(AP_CAD_SOAK_WORST_USED);

  for (uint16_t i = 0; i < AP_CAD_SOAK_WORST_USED; i++) {
    ap_cad_soak_print_worst_sample((uint8_t)i, AP_CAD_SOAK_WORST[i]);
  }
}

float ap_cad_q8_8_to_float(uint16_t value) {
  return (float)value / 256.0f;
}

bool ap_cad_rate_within_2pct(float measured_hz, float declared_hz) {
  if (measured_hz <= 0.0f || declared_hz <= 0.0f) {
    return false;
  }
  float ratio = measured_hz / declared_hz;
  if (ratio < 0.0f) ratio = -ratio;
  float drift = ratio - 1.0f;
  if (drift < 0.0f) drift = -drift;
  return drift <= 0.02f;
}

void ap_cad_capture_print_health() {
  float measured_ap_hz = 0.0f;
  float measured_nov_hz = 0.0f;
  uint16_t emitted_rows = 0;
  uint32_t first_emit_ms = 0;
  uint32_t last_emit_ms = 0;
  bool core_ok = (AP_CAD_CAPTURE_COUNT > 0);
  bool i2s_ok = (AP_CAD_CAPTURE_COUNT > 0);
  bool bytes_ok = (AP_CAD_CAPTURE_COUNT > 0);

  if (AP_CAD_CAPTURE_COUNT >= 2) {
    const APCadenceCaptureSample& first = AP_CAD_CAPTURE_BUFFER[0];
    const APCadenceCaptureSample& last = AP_CAD_CAPTURE_BUFFER[AP_CAD_CAPTURE_COUNT - 1];
    if (last.frame_ms > first.frame_ms) {
      measured_ap_hz = 1000.0f * (float)(AP_CAD_CAPTURE_COUNT - 1) / (float)(last.frame_ms - first.frame_ms);
    }
  }

  for (uint16_t i = 0; i < AP_CAD_CAPTURE_COUNT; i++) {
    const APCadenceCaptureSample& sample = AP_CAD_CAPTURE_BUFFER[i];
    if ((sample.flags & 0x20) == 0) {
      core_ok = false;
    }
    if ((sample.flags & 0x08) == 0) {
      i2s_ok = false;
    }
    if ((sample.flags & 0x10) == 0) {
      bytes_ok = false;
    }
    if ((sample.flags & 0x01) != 0) {
      if (emitted_rows == 0) {
        first_emit_ms = sample.emit_ms;
      }
      last_emit_ms = sample.emit_ms;
      emitted_rows++;
    }
  }
  if (emitted_rows >= 2 && last_emit_ms > first_emit_ms) {
    measured_nov_hz = 1000.0f * (float)(emitted_rows - 1) / (float)(last_emit_ms - first_emit_ms);
  }

  const APCadenceCaptureSample* ref = (AP_CAD_CAPTURE_COUNT > 0) ? &AP_CAD_CAPTURE_BUFFER[0] : nullptr;
  const float declared_ap_hz = (ref != nullptr) ? ap_cad_q8_8_to_float(ref->declared_ap_hz_q8_8) : 0.0f;
  const float declared_nov_hz = (ref != nullptr) ? ap_cad_q8_8_to_float(ref->declared_nov_hz_q8_8) : 0.0f;
  const bool ap_rate_ok = ap_cad_rate_within_2pct(measured_ap_hz, declared_ap_hz);
  const bool nov_rate_ok = ap_cad_rate_within_2pct(measured_nov_hz, declared_nov_hz);
  const bool health_ok = ap_rate_ok && nov_rate_ok && core_ok && i2s_ok && bytes_ok;

  USBSerial.print("APCAD_HEALTH,ver=1,health_ok=");
  USBSerial.print(health_ok ? 1 : 0);
  USBSerial.print(",sample_rate=");
  USBSerial.print(ref != nullptr ? ref->sample_rate : 0);
  USBSerial.print(",samples_per_chunk=");
  USBSerial.print(ref != nullptr ? ref->samples_per_chunk : 0);
  USBSerial.print(",tempo_decim=");
  USBSerial.print(ref != nullptr ? ref->tempo_decimation : 0);
  USBSerial.print(",decl_ap_hz=");
  USBSerial.print(declared_ap_hz, 3);
  USBSerial.print(",decl_nov_hz=");
  USBSerial.print(declared_nov_hz, 3);
  USBSerial.print(",meas_ap_hz=");
  USBSerial.print(measured_ap_hz, 3);
  USBSerial.print(",meas_nov_hz=");
  USBSerial.print(measured_nov_hz, 3);
  USBSerial.print(",ap_rate_ok=");
  USBSerial.print(ap_rate_ok ? 1 : 0);
  USBSerial.print(",nov_rate_ok=");
  USBSerial.print(nov_rate_ok ? 1 : 0);
  USBSerial.print(",core_ok=");
  USBSerial.print(core_ok ? 1 : 0);
  USBSerial.print(",i2s_ok=");
  USBSerial.print(i2s_ok ? 1 : 0);
  USBSerial.print(",bytes_ok=");
  USBSerial.print(bytes_ok ? 1 : 0);
  USBSerial.print(",dma_desc=");
  USBSerial.print(ref != nullptr ? ref->dma_desc_num : 0);
  USBSerial.print(",ap_core=");
  USBSerial.print(ref != nullptr ? ref->ap_core_id : -1);
  USBSerial.print(",vp_core=");
  USBSerial.println(ref != nullptr ? ref->vp_core_id : -1);
}

void ap_cad_capture_dump() {
  AP_CAD_CAPTURE_ACTIVE = false;
  USBSerial.print("APCAD_CAPTURE_BEGIN,count=");
  USBSerial.print(AP_CAD_CAPTURE_COUNT);
  USBSerial.print(",capacity=");
  USBSerial.print(AP_CAD_CAPTURE_CAPACITY);
  USBSerial.print(",dropped=");
  USBSerial.print(AP_CAD_CAPTURE_DROPPED);
  USBSerial.print(",start_ms=");
  USBSerial.print(AP_CAD_CAPTURE_START_MS);
  USBSerial.print(",end_ms=");
  USBSerial.println(AP_CAD_CAPTURE_END_MS);
  ap_cad_capture_print_health();
  for (uint16_t i = 0; i < AP_CAD_CAPTURE_COUNT; i++) {
    const APCadenceCaptureSample& sample = AP_CAD_CAPTURE_BUFFER[i];
    USBSerial.print("APCAD,boot_ms=");
    USBSerial.print(sample.boot_ms);
    USBSerial.print(",frame=");
    USBSerial.print(sample.frame_index);
    USBSerial.print(",t=");
    USBSerial.print(sample.frame_ms);
    USBSerial.print(",sample_rate=");
    USBSerial.print(sample.sample_rate);
    USBSerial.print(",samples_per_chunk=");
    USBSerial.print(sample.samples_per_chunk);
    USBSerial.print(",slot_bits=");
    USBSerial.print(sample.slot_bit_width);
    USBSerial.print(",slot_mode=");
    USBSerial.print(sample.slot_mode);
    USBSerial.print(",dma_desc=");
    USBSerial.print(sample.dma_desc_num);
    USBSerial.print(",dma_frame=");
    USBSerial.print(sample.dma_frame_num);
    USBSerial.print(",bytes_req=");
    USBSerial.print(sample.bytes_requested);
    USBSerial.print(",bytes_read=");
    USBSerial.print(sample.bytes_read);
    USBSerial.print(",samples_read=");
    USBSerial.print(sample.samples_read);
    USBSerial.print(",i2s_status=");
    USBSerial.print(sample.i2s_status);
    USBSerial.print(",stage=");
    USBSerial.print(sample.stage);
    USBSerial.print(",ap_core=");
    USBSerial.print(sample.ap_core_id);
    USBSerial.print(",vp_core=");
    USBSerial.print(sample.vp_core_id);
    USBSerial.print(",i2s_us=");
    USBSerial.print(sample.i2s_read_elapsed_us);
    USBSerial.print(",capture_seq=");
    USBSerial.print(sample.capture_sequence);
    USBSerial.print(",i2s_read_start_us=");
    USBSerial.print((unsigned long long)sample.i2s_read_start_us);
    USBSerial.print(",i2s_read_return_us=");
    USBSerial.print((unsigned long long)sample.i2s_read_return_us);
    USBSerial.print(",newest_sample_estimate_us=");
    USBSerial.print((unsigned long long)sample.newest_sample_estimate_us);
    USBSerial.print(",oldest_sample_estimate_us=");
    USBSerial.print((unsigned long long)sample.oldest_sample_estimate_us);
    USBSerial.print(",ap_publish_us=");
    USBSerial.print((unsigned long long)sample.ap_publish_us);
    USBSerial.print(",sample_time_assumption_id=");
    USBSerial.print(sample.sample_time_assumption_id);
    USBSerial.print(",newest_to_publish_us=");
    USBSerial.print((sample.ap_publish_us >= sample.newest_sample_estimate_us)
                      ? (unsigned long long)(sample.ap_publish_us - sample.newest_sample_estimate_us)
                      : 0ULL);
    USBSerial.print(",oldest_to_publish_us=");
    USBSerial.print((sample.ap_publish_us >= sample.oldest_sample_estimate_us)
                      ? (unsigned long long)(sample.ap_publish_us - sample.oldest_sample_estimate_us)
                      : 0ULL);
    USBSerial.print(",gdft_us=");
    USBSerial.print(sample.gdft_elapsed_us);
    USBSerial.print(",novelty_us=");
    USBSerial.print(sample.novelty_elapsed_us);
    USBSerial.print(",total_us=");
    USBSerial.print(sample.total_ap_loop_elapsed_us);
    USBSerial.print(",k1_frame_ctr=");
    USBSerial.print(sample.k1_frame_ctr);
    USBSerial.print(",tempo_decim=");
    USBSerial.print(sample.tempo_decimation);
    USBSerial.print(",decl_ap_hz=");
    ap_nov_capture_print_q8_8(sample.declared_ap_hz_q8_8);
    USBSerial.print(",decl_nov_hz=");
    ap_nov_capture_print_q8_8(sample.declared_nov_hz_q8_8);
    USBSerial.print(",emit=");
    USBSerial.print(sample.emit_count);
    USBSerial.print(",emit_ms=");
    USBSerial.print(sample.emit_ms);
    USBSerial.print(",emit_dt=");
    USBSerial.print(sample.emit_delta_ms);
    USBSerial.print(",emitted=");
    USBSerial.print((sample.flags & 0x01) ? 1 : 0);
    USBSerial.print(",nov=");
    ap_nov_capture_print_q16(sample.novelty_q16);
    USBSerial.print(",nov_scaled=");
    ap_nov_capture_print_q8_8(sample.scaled_novelty_q8_8);
    USBSerial.print(",win_bpm=");
    ap_nov_capture_print_q8_8(sample.winner_bpm_q8_8);
    USBSerial.print(",top1_bpm=");
    ap_nov_capture_print_q8_8(sample.top1_bpm_q8_8);
    USBSerial.print(",v2_ema=");
    ap_nov_capture_print_q16(sample.v2_conf_ema_q16);
    USBSerial.print(",v2_q=");
    ap_nov_capture_print_q16(sample.v2_quality_q16);
    USBSerial.print(",v2_h=");
    ap_nov_capture_print_q16(sample.v2_hist_share_q16);
    USBSerial.print(",v2_pr=");
    ap_nov_capture_print_q16(sample.v2_prominence_q16);
    USBSerial.print(",v2_per=");
    ap_nov_capture_print_q16(sample.v2_periodicity_q16);
    USBSerial.print(",v2_ps=");
    ap_nov_capture_print_q16(sample.v2_peak_share_q16);
    USBSerial.print(",tempo_silence_us=");
    USBSerial.print(sample.tempo_silence_elapsed_us);
    USBSerial.print(",tempo_acf_us=");
    USBSerial.print(sample.tempo_acf_elapsed_us);
    USBSerial.print(",tempo_update_us=");
    USBSerial.print(sample.tempo_update_elapsed_us);
    USBSerial.print(",tempo_phase_us=");
    USBSerial.print(sample.tempo_phase_elapsed_us);
    USBSerial.print(",tempo_publish_us=");
    USBSerial.print(sample.tempo_publish_elapsed_us);
    USBSerial.print(",tempo_emit_us=");
    USBSerial.print(sample.tempo_emit_elapsed_us);
    USBSerial.print(",acf_spread=");
    USBSerial.print((sample.flags & 0x80) ? 1 : 0);
    USBSerial.print(",acf_lag_cursor=");
    USBSerial.print(sample.acf_lag_cursor);
    USBSerial.print(",acf_pub=");
    USBSerial.print(sample.acf_publish_count);
    USBSerial.print(",v2_lock=");
    USBSerial.print((sample.flags & 0x40) ? 1 : 0);
    USBSerial.print(",sil=");
    USBSerial.print((sample.flags & 0x02) ? 1 : 0);
    USBSerial.print(",acf=");
    USBSerial.print((sample.flags & 0x04) ? 1 : 0);
    USBSerial.print(",i2s_ok=");
    USBSerial.print((sample.flags & 0x08) ? 1 : 0);
    USBSerial.print(",bytes_ok=");
    USBSerial.print((sample.flags & 0x10) ? 1 : 0);
    USBSerial.print(",core_ok=");
    USBSerial.print((sample.flags & 0x20) ? 1 : 0);
    USBSerial.println(",src=buf");
    if ((i & 0x0F) == 0x0F) {
      vTaskDelay(1);
    }
  }
  USBSerial.print("APCAD_CAPTURE_DONE,count=");
  USBSerial.print(AP_CAD_CAPTURE_COUNT);
  USBSerial.print(",dropped=");
  USBSerial.println(AP_CAD_CAPTURE_DROPPED);
}

// ---------------------------------------------------------------------------
// serial_diag_ap_dispatch — lifted verbatim from parse_command() Stage-B ladder.
// Handles the 11 AP-frontend-debug handlers (ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG).
// tempo_stream is NOT here — it is ENABLE_TEMPO_STREAM-only (a broader gate) and
// stays inline in serial_menu.h so this dispatcher straddles a single gate level.
// The `if (false) {}` opener keeps every real branch as `else if (strcmp(...))`,
// statement-identical to the serial_menu.h@HEAD source. Returns true iff handled.
// ---------------------------------------------------------------------------
bool serial_diag_ap_dispatch(const char* command_type, char* command_data) {
    if (false) {}

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    else if (strcmp(command_type, "ap_frontend_debug") == 0 || strcmp(command_type, "apdbg") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        AP_FRONTEND_DEBUG_ENABLED = value;
        tx_begin();
        USBSerial.print("AP_FRONTEND_DEBUG: ");
        USBSerial.println(vp_bool_text(AP_FRONTEND_DEBUG_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "nov_capture") == 0) {
      long ms = (command_data && command_data[0]) ? atol(command_data) : 0;
      if (ms > 0 && (uint32_t)ms <= AP_NOV_CAPTURE_MAX_MS && ap_nov_capture_arm((uint32_t)ms)) {
        tx_begin();
        USBSerial.print("NOV_CAPTURE: armed ");
        USBSerial.print(ms);
        USBSerial.print(" ms capacity=");
        USBSerial.println(AP_NOV_CAPTURE_CAPACITY);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "nov_dump") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        ap_nov_capture_dump();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "nov_clear") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        ap_nov_capture_clear();
        ap_nov_capture_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "nov_status") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        ap_nov_capture_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "apcad_capture") == 0) {
      long ms = (command_data && command_data[0]) ? atol(command_data) : 0;
      if (ms > 0 && (uint32_t)ms <= AP_CAD_CAPTURE_MAX_MS && ap_cad_capture_arm((uint32_t)ms)) {
        tx_begin();
        USBSerial.print("APCAD_CAPTURE: armed ");
        USBSerial.print(ms);
        USBSerial.print(" ms capacity=");
        USBSerial.println(AP_CAD_CAPTURE_CAPACITY);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "apcad_dump") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        ap_cad_capture_dump();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "apcad_clear") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        ap_cad_capture_clear();
        ap_cad_capture_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "apcad_status") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        ap_cad_capture_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "apcad_soak") == 0) {
      long ms = (command_data && command_data[0]) ? atol(command_data) : 0;
      if (ms > 0 && (uint32_t)ms <= AP_CAD_SOAK_MAX_MS && ap_cad_soak_arm((uint32_t)ms)) {
        tx_begin();
        USBSerial.print("APCAD_SOAK: armed ");
        USBSerial.print(ms);
        USBSerial.println(" ms compact=1");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "apcad_soak_status") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        ap_cad_soak_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "apcad_abort") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value) && value) {
        AP_CAD_CAPTURE_ACTIVE = false;
        AP_CAD_SOAK_ACTIVE = false;
        tx_begin();
        USBSerial.println("APCAD_ABORT: stopped");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif  // ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG

    else {
      return false;  // not a diag-AP handler — let parse_command's ladder continue
    }

    return true;
}

#endif  // ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
