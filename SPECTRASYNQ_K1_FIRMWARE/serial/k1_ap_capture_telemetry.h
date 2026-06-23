/*----------------------------------------
  K1 AP CAPTURE / TELEMETRY (diagnostics)
  ----------------------------------------
  Extracted verbatim from serial_menu.h (Phase A Lane 2, S1).
  Owns the AP novelty-capture + cadence-capture + cadence-soak diagnostic
  buffers and their dump/status/arm/tick handlers. The entire unit is gated
  on `ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`, which is set ONLY in
  the non-shippable probe envs (k1_ap_frontend_probe & siblings) — never in
  k1_hardware — so this TU compiles to NOTHING in production.

  Behaviour-preserving move: the buffers/counters that were file-scope
  `static` inside the single-include serial_menu.h header are now defined
  (with external linkage) in k1_ap_capture_telemetry.cpp and declared `extern`
  here, so the call sites that stayed in serial_menu.h (parse_command apcap/
  apcad/apsoak handlers, the stop_streams reset block, and the check_serial
  tick) continue to reference the same storage.
*/

#ifndef K1_AP_CAPTURE_TELEMETRY_H
#define K1_AP_CAPTURE_TELEMETRY_H

#include "globals.h"                // USBSerial, CONFIG
#include "constants.h"
#include "sb_i2s_capture_types.h"   // SBAudioI2SReadDebug + SB_I2S_* (guarded; used by APCadenceFrameInput / ap_cad_make_sample)
#include "sb_tempo.h"               // SBTempoDebugSnapshot, sb_tempo_debug_read()
#include <stdint.h>
#include <math.h>                   // isfinite

// NOTE: the full i2s_audio.h is a guard-less *implementation* header that only
// compiles inside the .ino's include context; this TU pulls only the shared
// type/constant header above, never i2s_audio.h itself.

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
#include <esp_heap_caps.h>

// Serial TX-envelope helpers defined in serial_menu.h (Unit B). Declared here
// so the extracted capture handlers can call them across the TU boundary; the
// definitions (with the same default arguments) live once in serial_menu.h.
void tx_begin(bool error = false);
void tx_end(bool error = false);
const char* vp_bool_text(bool value);

// ---- Capacity / bound macros (verbatim from serial_menu.h) -----------------
#ifndef AP_NOV_CAPTURE_CAPACITY
#define AP_NOV_CAPTURE_CAPACITY 6144
#endif
#ifndef AP_NOV_CAPTURE_MAX_MS
#define AP_NOV_CAPTURE_MAX_MS 180000UL
#endif
#ifndef AP_CAD_CAPTURE_CAPACITY
#define AP_CAD_CAPTURE_CAPACITY 2304
#endif
#ifndef AP_CAD_CAPTURE_MAX_MS
#define AP_CAD_CAPTURE_MAX_MS 20000UL
#endif
#ifndef AP_CAD_SOAK_MAX_MS
#define AP_CAD_SOAK_MAX_MS 600000UL
#endif
#ifndef AP_CAD_SOAK_WORST_COUNT
#define AP_CAD_SOAK_WORST_COUNT 16
#endif
#ifndef AP_CAD_SOAK_HIST_BUCKET_US
#define AP_CAD_SOAK_HIST_BUCKET_US 128UL
#endif
#ifndef AP_CAD_SOAK_HIST_BUCKETS
#define AP_CAD_SOAK_HIST_BUCKETS 128
#endif

// ---- Sample structs (verbatim from serial_menu.h) --------------------------
struct APNovCaptureSample {
  uint32_t t_ms;
  uint32_t emit_count;
  uint16_t novelty_q16;
  uint16_t scaled_novelty_q8_8;
  uint16_t scale_q8_8;
  uint8_t flags;
  uint8_t reserved;
};

struct APCadenceFrameInput {
  uint32_t boot_ms;
  uint32_t frame_index;
  uint32_t frame_ms;
  uint32_t gdft_elapsed_us;
  uint32_t novelty_elapsed_us;
  uint32_t total_ap_loop_elapsed_us;
  uint8_t stage;
  int8_t ap_core_id;
  int8_t vp_core_id;
  SBAudioI2SReadDebug i2s;
  SBTempoDebugSnapshot tempo;
};

struct APCadenceCaptureSample {
  uint32_t boot_ms;
  uint32_t frame_index;
  uint32_t frame_ms;
  uint32_t emit_count;
  uint32_t emit_ms;
  uint32_t i2s_read_elapsed_us;
  uint32_t gdft_elapsed_us;
  uint32_t novelty_elapsed_us;
  uint32_t total_ap_loop_elapsed_us;
  uint16_t sample_rate;
  uint16_t samples_per_chunk;
  uint16_t dma_frame_num;
  uint16_t bytes_requested;
  uint16_t bytes_read;
  uint16_t emit_delta_ms;
  uint16_t declared_ap_hz_q8_8;
  uint16_t declared_nov_hz_q8_8;
  uint16_t novelty_q16;
  uint16_t scaled_novelty_q8_8;
  uint16_t winner_bpm_q8_8;
  uint16_t top1_bpm_q8_8;
  uint16_t v2_conf_ema_q16;
  uint16_t v2_quality_q16;
  uint16_t v2_hist_share_q16;
  uint16_t v2_prominence_q16;
  uint16_t v2_periodicity_q16;
  uint16_t v2_peak_share_q16;
  uint16_t tempo_silence_elapsed_us;
  uint16_t tempo_acf_elapsed_us;
  uint16_t tempo_update_elapsed_us;
  uint16_t tempo_phase_elapsed_us;
  uint16_t tempo_publish_elapsed_us;
  uint16_t tempo_emit_elapsed_us;
  uint16_t acf_lag_cursor;
  uint32_t acf_publish_count;
  int16_t i2s_status;
  int8_t ap_core_id;
  int8_t vp_core_id;
  uint8_t stage;
  uint8_t slot_bit_width;
  uint8_t slot_mode;
  uint8_t dma_desc_num;
  uint8_t sb_frame_ctr;
  uint8_t tempo_decimation;
  uint8_t flags;
};

// ---- Capture state (moved from serial_menu.h `static` -> external linkage) --
extern bool AP_FRONTEND_DEBUG_ENABLED;
extern APNovCaptureSample AP_NOV_CAPTURE_BUFFER[AP_NOV_CAPTURE_CAPACITY];
extern uint16_t AP_NOV_CAPTURE_COUNT;
extern uint32_t AP_NOV_CAPTURE_DROPPED;
extern uint32_t AP_NOV_CAPTURE_START_MS;
extern uint32_t AP_NOV_CAPTURE_END_MS;
extern uint32_t AP_NOV_CAPTURE_LAST_EMIT;
extern bool AP_NOV_CAPTURE_ACTIVE;
extern APCadenceCaptureSample* AP_CAD_CAPTURE_BUFFER;
extern uint16_t AP_CAD_CAPTURE_COUNT;
extern uint32_t AP_CAD_CAPTURE_DROPPED;
extern uint32_t AP_CAD_CAPTURE_START_MS;
extern uint32_t AP_CAD_CAPTURE_END_MS;
extern uint32_t AP_CAD_CAPTURE_LAST_EMIT;
extern uint32_t AP_CAD_CAPTURE_LAST_EMIT_MS;
extern bool AP_CAD_CAPTURE_ACTIVE;
extern bool AP_CAD_CAPTURE_ALLOC_FAILED;
extern bool AP_CAD_SOAK_ACTIVE;
extern uint32_t AP_CAD_SOAK_START_MS;
extern uint32_t AP_CAD_SOAK_END_MS;
extern uint32_t AP_CAD_SOAK_FIRST_FRAME_MS;
extern uint32_t AP_CAD_SOAK_LAST_FRAME_MS;
extern uint32_t AP_CAD_SOAK_FIRST_EMIT_MS;
extern uint32_t AP_CAD_SOAK_LAST_EMIT_MS;
extern uint32_t AP_CAD_SOAK_LAST_EMIT;
extern uint32_t AP_CAD_SOAK_PREV_FRAME;
extern uint32_t AP_CAD_SOAK_PREV_FRAME_MS;
extern uint32_t AP_CAD_SOAK_ROW_COUNT;
extern uint32_t AP_CAD_SOAK_EMITTED_COUNT;
extern uint32_t AP_CAD_SOAK_I2S_NOT_OK;
extern uint32_t AP_CAD_SOAK_BYTES_MISMATCH;
extern uint32_t AP_CAD_SOAK_FRAME_GAPS;
extern uint32_t AP_CAD_SOAK_TIMESTAMP_REGRESSIONS;
extern uint32_t AP_CAD_SOAK_CORE_BAD;
extern uint32_t AP_CAD_SOAK_ACTIVE_OVER_7500;
extern uint32_t AP_CAD_SOAK_EMITTED_ACTIVE_OVER_7500;
extern uint32_t AP_CAD_SOAK_ACTIVE_MAX_US;
extern uint16_t AP_CAD_SOAK_WORST_USED;
extern bool AP_CAD_SOAK_HAVE_PREV;
extern APCadenceCaptureSample AP_CAD_SOAK_WORST[AP_CAD_SOAK_WORST_COUNT];
extern uint32_t AP_CAD_SOAK_ACTIVE_HIST[AP_CAD_SOAK_HIST_BUCKETS];

// ---- Capture handler prototypes (bodies in k1_ap_capture_telemetry.cpp) -----
uint16_t ap_nov_capture_q16(float value);
uint16_t ap_nov_capture_q8_8(float value);
void ap_nov_capture_print_q16(uint16_t value);
void ap_nov_capture_print_q8_8(uint16_t value);
void ap_nov_capture_status();
void ap_nov_capture_clear();
bool ap_nov_capture_arm(uint32_t duration_ms);
void ap_nov_capture_tick(uint32_t t_now, const SBTempoDebugSnapshot& td);
void ap_nov_capture_dump();
uint16_t ap_capture_u16_sat(uint32_t value);
int16_t ap_capture_i16_sat(int32_t value);
bool ap_cad_capture_ensure_buffer();
void ap_cad_capture_status();
void ap_cad_capture_clear();
bool ap_cad_capture_arm(uint32_t duration_ms);
APCadenceCaptureSample ap_cad_make_sample(const APCadenceFrameInput& frame, bool emitted, uint32_t emit_delta_ms);
uint32_t ap_cad_active_work_us(const APCadenceCaptureSample& sample);
void ap_cad_capture_tick(const APCadenceFrameInput& frame);
void ap_cad_soak_reset();
bool ap_cad_soak_arm(uint32_t duration_ms);
void ap_cad_soak_record_worst(const APCadenceCaptureSample& sample, uint32_t active_us);
void ap_cad_soak_tick(const APCadenceFrameInput& frame);
uint32_t ap_cad_soak_hist_percentile(uint8_t percentile);
void ap_cad_soak_print_worst_sample(uint8_t rank, const APCadenceCaptureSample& sample);
void ap_cad_soak_status();
float ap_cad_q8_8_to_float(uint16_t value);
bool ap_cad_rate_within_2pct(float measured_hz, float declared_hz);
void ap_cad_capture_print_health();
void ap_cad_capture_dump();

#endif  // ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG

#endif  // K1_AP_CAPTURE_TELEMETRY_H
