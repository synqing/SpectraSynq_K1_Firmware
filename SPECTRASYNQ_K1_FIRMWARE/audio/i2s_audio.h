/*----------------------------------------
  K1 I2S FUNCTIONS
  ----------------------------------------*/
#include "k1_tempo.h"        // AP_STREAM tempo fields (bpm/conf/lock/phase/beat) — header-guarded
#include "k1_onset_beat.h"   // AP_STREAM onset fields (onset/bass) — header-guarded

// PIO-MIGRATION-STAGE-3 (2026-05-24): I2S driver migrated to ESP-IDF 5.x i2s_std.
// Was: legacy driver/i2s.h (i2s_driver_install + i2s_set_pin + i2s_read).
//      Deprecated under arduino-esp32 3.2.0 / IDF 5.4.1; shimmed but slated for
//      removal in IDF v6.0.
// Now: driver/i2s_std.h (i2s_new_channel + i2s_channel_init_std_mode +
//      i2s_channel_enable + i2s_channel_read).
//
// STAGE-7 SLOT-CFG RESOLUTION (2026-05-24): the Philips macro defaults
// (ws_pol=false, bit_shift=true, slot_mask=BOTH/LEFT-for-mono) do NOT produce
// correct SPH0645 data on ESP32-S3 with IDF 5.4.1. Five knob attempts on the
// Philips path (slot_mode, slot_bit_width, mclk_multiple, data_bit_width, then
// the Philips defaults verbatim) all left the [RAWR] hex pattern truncated to
// 17-bit-effective with the K1 R magnitudes pegged at the extraction-math
// negative clamp. The fix that works: hand-built slot_cfg with
// ws_pol=true + bit_shift=false ("School A" lineage; matches Lixie Labs'
// Emotiscope src/microphone.h) BUT with slot_mask=LEFT (not RIGHT) — because
// IDF 5.4.1's slot semantic inverts when ws_pol=true relative to Emotiscope's
// proven IDF 5.1 config. K1's SPH0645 SEL is wired to 3V3 (physical RIGHT
// slot) but reads correctly via slot_mask=LEFT under this driver version.
// Verified 2026-05-24: max_raw varying 4k-10k under music, peak_scaled 0.04-0.49,
// follower tracking, LEDs visibly responsive.
//
// DMA sizing is now the production-candidate AP0/VP1 cadence cushion
// (dma_desc_num=3, dma_frame_num=96). Read size
// (SAMPLES_PER_CHUNK*sizeof(int32_t)=384 B) is preserved. The blocking read is
// BOUNDED under K1_AUDIO_FREEZE_GUARD_V1 (N2: pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS)
// in acquire_sample_chunk, degrade-to-silence on timeout/short read); undefining
// the flag restores the original portMAX_DELAY blocking read. Init keeps void return + PASS/FAIL print contract; NO
// ESP_ERROR_CHECK (init failure must not panic-reboot). Lines below
// (acquire_sample_chunk extraction, DC calibration, sweet-spot, AGC,
// calculate_vu) byte-identical to pre-migration except the single
// i2s_read → i2s_channel_read substitution.
//
// See: docs/forensics/2026-05-24-doctrine-gate-pio-migration.md
//      MIGRATION_PLAN-v2-rebaselined.md §8 Stage 3
//      https://github.com/Lixie-Labs/Emotiscope/blob/HEAD/src/microphone.h
#include <driver/i2s_std.h>
#ifdef K1_MIC_IM73D_PDM_V1
#include <driver/i2s_pdm.h>   // IM73D122 PDM RX (bench eval); flag-OFF token stream unchanged
#include <driver/gpio.h>      // LR-select GPIO drive
#include <math.h>             // isfinite() for the PDM follower/NaN guard
#endif
#include <esp_timer.h>

#ifndef K1_I2S_READ_TIMEOUT_MS
#define K1_I2S_READ_TIMEOUT_MS 100  // N2: bounded audio read (>> 7.5ms/chunk DMA; bounds a mic/DMA stall)
#endif

static i2s_chan_handle_t rx_chan = NULL;

// K1_I2S_* slot constants + K1AudioI2SReadDebug moved to a tiny guarded header
// (Phase A Lane 2, S1) so the AP-capture telemetry TU can share the type/
// constants without including this monolithic impl header. Definitions are
// unchanged — exactly one definition each, here via the include.
#include "k1_i2s_capture_types.h"

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
static K1AudioI2SReadDebug k1_audio_i2s_read_debug = {};

K1AudioI2SReadDebug k1_audio_i2s_read_debug_read() {
  return k1_audio_i2s_read_debug;
}
#endif

// Raw I2S frame dump request flag (one-shot diagnostic, fires once and clears).
// Set by serial_menu.h `dump_raw=silence|tone` handler — see rationale block there.
//   0 = idle, 1 = silence-phase, 2 = 1 kHz tone-phase
volatile uint8_t raw_dump_request = 0;

// Fix-D Layer 2 — sample-rail rejection threshold for noise_cal DC accumulation.
// Post-extraction-math samples are clipped to ±32767 in acquire_sample_chunk; a
// sample at (or near) the rail is measuring the clipping ceiling, not the noise
// floor. Averaging rail-pinned samples into dc_offset_sum produces a calibration
// that points to ±FS, which on next boot subtracts a rail-magnitude offset from
// every incoming sample and breaks the audio pipeline ("DC_OFFSET poisoning").
// Threshold sits just below the ±32767 clip so we reject the clipped samples
// while still accepting all real loud-audio dynamics.
#define SAMPLE_RAIL_THRESHOLD 32000

#ifdef K1_LOUD_GUARD_V1
static inline float k1_loud_guard_clamp_float(float value, float min_value, float max_value) {
  if (!isfinite(value)) return min_value;
  if (value < min_value) return min_value;
  if (value > max_value) return max_value;
  return value;
}

static inline float k1_loud_guard_dt(uint32_t now_ms) {
  static uint32_t last_ms = 0;
  float dt = (last_ms != 0) ? float(now_ms - last_ms) * 0.001f : 0.01f;
  last_ms = now_ms;
  return k1_loud_guard_clamp_float(dt, 0.001f, 0.050f);
}

static inline float k1_loud_guard_alpha(float dt, float tau_sec) {
  if (tau_sec <= 0.0f) return 1.0f;
  return k1_loud_guard_clamp_float(dt / tau_sec, 0.0f, 1.0f);
}

static inline void k1_loud_guard_track(float* value, float target, float dt, float tau_sec) {
  *value += (target - *value) * k1_loud_guard_alpha(dt, tau_sec);
}

static inline float k1_loud_guard_approach(float current, float target, float dt, float attack_sec, float release_sec) {
  float tau = (target < current) ? attack_sec : release_sec;
  return current + (target - current) * k1_loud_guard_alpha(dt, tau);
}

// A/B retune: GDFT release select by k1_loud_guard_mode. Attack is never mode-switched
// (engage must stay fast; the invariant attack < release must hold). Mode 0 = baseline.
static inline float k1_loud_guard_gdft_release_sec() {
  switch (k1_loud_guard_mode) {
    case 1:  return K1_LOUD_GUARD_GDFT_RELEASE_SEC_CONS;
    case 2:  return K1_LOUD_GUARD_GDFT_RELEASE_SEC_AGGR;
    default: return K1_LOUD_GUARD_GDFT_RELEASE_SEC;
  }
}

static inline float k1_loud_guard_effective_sensitivity() {
  if (!k1_loud_guard_enabled) return CONFIG.SENSITIVITY;
  return CONFIG.SENSITIVITY * k1_loud_input_trim;
}

static inline float k1_audio_response_gain_effective() {
  return audio_response_gain_clamped();
}

static inline void k1_loud_guard_begin_frame() {
  k1_loud_frame_clip_count = 0;
  k1_loud_frame_near_rail_count = 0;
  k1_loud_frame_sample_count = 0;
}

static inline void k1_loud_guard_record_preclip(int32_t sample) {
  k1_loud_frame_sample_count++;
  const int32_t magnitude = sample < 0 ? -sample : sample;
  if (magnitude >= int32_t(K1_LOUD_GUARD_NEAR_RAIL_RAW)) {
    k1_loud_frame_near_rail_count++;
  }
  if (sample > 32767 || sample < -32767) {
    k1_loud_frame_clip_count++;
  }
}

static inline void k1_loud_guard_update(uint32_t t_now) {
  const float dt = k1_loud_guard_dt(t_now);

  if (!k1_loud_guard_enabled) {
    k1_loud_input_trim = 1.0f;
    k1_loud_gdft_trim = 1.0f;
    k1_loud_clip_duty = 0.0f;
    k1_loud_near_rail_duty = 0.0f;
    k1_loud_peak_pin_duty = 0.0f;
    k1_loud_spec_sat_duty = 0.0f;
    k1_loud_spec_sat_fraction = 0.0f;
    return;
  }

  const float sample_count = k1_loud_frame_sample_count > 0 ? float(k1_loud_frame_sample_count) : 1.0f;
  const float clip_now = float(k1_loud_frame_clip_count) / sample_count;
  const float near_now = float(k1_loud_frame_near_rail_count) / sample_count;
  const float peak_pin_now = (waveform_peak_scaled >= K1_LOUD_GUARD_PEAK_PIN_THRESHOLD) ? 1.0f : 0.0f;

  uint16_t spec_sat_bins = 0;
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    if (float(spectrogram[i]) >= K1_LOUD_GUARD_SPEC_SAT_THRESHOLD) {
      spec_sat_bins++;
    }
  }
  k1_loud_spec_sat_fraction = float(spec_sat_bins) / float(NUM_FREQS);
  const float spec_sat_now = (k1_loud_spec_sat_fraction >= K1_LOUD_GUARD_SPEC_SAT_FRACTION) ? 1.0f : 0.0f;

  k1_loud_guard_track(&k1_loud_clip_duty, clip_now, dt, K1_LOUD_GUARD_DUTY_TAU_SEC);
  k1_loud_guard_track(&k1_loud_near_rail_duty, near_now, dt, K1_LOUD_GUARD_DUTY_TAU_SEC);
  k1_loud_guard_track(&k1_loud_peak_pin_duty, peak_pin_now, dt, K1_LOUD_GUARD_DUTY_TAU_SEC);
  k1_loud_guard_track(&k1_loud_spec_sat_duty, spec_sat_now, dt, K1_LOUD_GUARD_DUTY_TAU_SEC);

  float input_target = 1.0f;
  if (clip_now > 0.0f) {
    input_target = K1_LOUD_GUARD_INPUT_TRIM_MIN;
  } else if (near_now > 0.020f) {
    input_target = 0.55f;
  } else if (near_now > 0.005f) {
    input_target = 0.75f;
  }

  float gdft_target = 1.0f;
  if (k1_loud_spec_sat_duty > 0.35f || k1_loud_peak_pin_duty > 0.60f) {
    gdft_target = K1_LOUD_GUARD_GDFT_TRIM_MIN;
  } else if (k1_loud_spec_sat_duty > 0.12f || k1_loud_peak_pin_duty > 0.30f) {
    gdft_target = 0.70f;
  } else if (k1_loud_spec_sat_duty > 0.04f || k1_loud_peak_pin_duty > 0.12f) {
    gdft_target = 0.85f;
  }

  k1_loud_input_trim = k1_loud_guard_approach(k1_loud_input_trim, input_target, dt, K1_LOUD_GUARD_INPUT_ATTACK_SEC, K1_LOUD_GUARD_INPUT_RELEASE_SEC);
  k1_loud_gdft_trim = k1_loud_guard_approach(k1_loud_gdft_trim, gdft_target, dt, K1_LOUD_GUARD_GDFT_ATTACK_SEC, k1_loud_guard_gdft_release_sec());
}
#else
static inline float k1_audio_response_gain_effective() {
  return audio_response_gain_clamped();
}
#endif

static inline int16_t audio_response_gain_apply_sample(int32_t sample) {
  float scaled = (float)sample * k1_audio_response_gain_effective();
  if (scaled > 32767.0f) return 32767;
  if (scaled < -32767.0f) return -32767;
  return (int16_t)scaled;
}

void init_i2s() {
  esp_err_t result;

  // RX channel — mirror legacy dma_buf_count=2, dma_buf_len=SAMPLES_PER_CHUNK.
  i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_PORT, I2S_ROLE_MASTER);
  chan_cfg.dma_desc_num  = K1_I2S_DMA_DESC_NUM;
  chan_cfg.dma_frame_num = CONFIG.SAMPLES_PER_CHUNK;   // 96
  chan_cfg.auto_clear    = false;
  result = i2s_new_channel(&chan_cfg, NULL, &rx_chan); // tx=NULL → RX-only
  USBSerial.print("INIT I2S (channel): ");
  USBSerial.println(result == ESP_OK ? K1_PASS : K1_FAIL);

#ifdef K1_MIC_IM73D_PDM_V1
  // IM73D122 PDM RX (bench eval, 2026-07-02) — replaces the SPH0645 i2s_std path below.
  // 16-bit mono, DSR_8S (clk 819.2 kHz), slot LEFT; pins clk=13/din=12/LR=14(LOW). Proven
  // on B489A500. Reuses the shared chan_cfg prologue above + the enable epilogue below;
  // assigns the EXISTING `result` (does NOT redeclare it — same function scope).
  gpio_reset_pin((gpio_num_t)K1_PDM_LR_PIN);                 // clear any residual STD BCLK binding
  gpio_set_direction((gpio_num_t)K1_PDM_LR_PIN, GPIO_MODE_OUTPUT);
  gpio_set_level((gpio_num_t)K1_PDM_LR_PIN, 0);             // static LEFT select / falling-edge data
  i2s_pdm_rx_config_t pdm_cfg = {
    .clk_cfg  = I2S_PDM_RX_CLK_DEFAULT_CONFIG(CONFIG.SAMPLE_RATE),   // 12800 -> DSR_8S default
    .slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
    .gpio_cfg = {
      .clk = (gpio_num_t)K1_PDM_CLK_PIN,
      .din = (gpio_num_t)K1_PDM_DIN_PIN,
      .invert_flags = { .clk_inv = 0 },
    },
  };
#ifdef K1_MIC_IM73D_DSR_16S_V1
  pdm_cfg.clk_cfg.dn_sample_mode = I2S_PDM_DSR_16S;  // DSR eval only: +2 dB SNR lever, bench-radio-free measurement gate.
#endif
  result = i2s_channel_init_pdm_rx_mode(rx_chan, &pdm_cfg); // assign existing result; NO redeclare
  USBSerial.print("I2S PDM RX INIT: ");
  USBSerial.println(result == ESP_OK ? K1_PASS : K1_FAIL);
#else
  // PIO-MIGRATION-STAGE-7-FIX-6 (2026-05-24): adopt Emotiscope hand-built slot_cfg verbatim.
  // After 4 failed knob tests on the Philips macro path (slot_mode, slot_bit_width,
  // mclk_multiple, data_bit_width), the [RAWR] hex pattern remained bits 31..15
  // active / bits 14..0 zero — confirming the fault is below the Philips-macro
  // surface. The Philips macro defaults (ws_pol=false, bit_shift=true) are NOT
  // what Lixie Labs' Emotiscope uses for the SAME SPH0645 mic on the SAME ESP32-S3
  // hardware with i2s_std. Emotiscope's proven config (Lixie-Labs/Emotiscope
  // src/microphone.h, commit at clone time 2026-05-24) is hand-built with the
  // OPPOSITE of Philips defaults: ws_pol=true, bit_shift=false ("School A"
  // pattern Captain referenced from K1.node2 lineage). Adopting verbatim.
  //
  // Reference: https://github.com/Lixie-Labs/Emotiscope/blob/HEAD/src/microphone.h
  i2s_std_config_t std_cfg = {
    .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(CONFIG.SAMPLE_RATE),
    .slot_cfg = {
      .data_bit_width  = I2S_DATA_BIT_WIDTH_32BIT,
      .slot_bit_width  = I2S_SLOT_BIT_WIDTH_32BIT,
      .slot_mode       = I2S_SLOT_MODE_STEREO,
      // SOURCE-VERIFIED (test D, 2026-05-24): ESP-IDF v5.4.1
      //   components/hal/esp32s3/include/hal/i2s_ll.h, doxygen on
      //   i2s_ll_tx_set_pdm_chan_mod tabulates: ws_idle_pol=0 → mod=1 = LEFT,
      //   ws_idle_pol=1 → mod=1 = RIGHT. Hardware-level slot inversion under
      //   ws_pol=true is Espressif-documented; LEFT-mask below is source-
      //   justified, not empirical. Full lane: LightwaveOS_Official/docs/
      //   agent-outputs/analysis/2026-05-24-sph0645-truncation-deep-dive/
      //   lane-D2-slot-mask-ws-pol.md
      .slot_mask       = I2S_STD_SLOT_LEFT,     // see header note — IDF 5.4.1 ws_pol=true inverts slot semantic; K1 mic (SEL=3V3 / physical RIGHT) is read via LEFT mask here
      .ws_width        = 32,
      .ws_pol          = true,                  // Emotiscope/K1.node2 School A lineage
      .bit_shift       = false,                 // School A: no Philips delay
      .left_align      = true,
      .big_endian      = false,
      .bit_order_lsb   = false,
    },
    .gpio_cfg = {
      .mclk = I2S_GPIO_UNUSED,
      .bclk = (gpio_num_t)I2S_BCLK_PIN,
      .ws   = (gpio_num_t)I2S_LRCLK_PIN,
      .dout = I2S_GPIO_UNUSED,
      .din  = (gpio_num_t)I2S_DIN_PIN,
      .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false },
    },
  };

  result = i2s_channel_init_std_mode(rx_chan, &std_cfg);
  USBSerial.print("I2S STD INIT: ");
  USBSerial.println(result == ESP_OK ? K1_PASS : K1_FAIL);
#endif  // K1_MIC_IM73D_PDM_V1 (mic driver mode select)

  result = i2s_channel_enable(rx_chan);   // new driver does NOT auto-start (shared PDM/STD epilogue)
  USBSerial.print("I2S ENABLE: ");
  USBSerial.println(result == ESP_OK ? K1_PASS : K1_FAIL);
}

void acquire_sample_chunk(uint32_t t_now) {
  static int8_t sweet_spot_state_last = 0;
  static bool silence_temp = false;
  static uint32_t silence_switched = 0;
  static float silent_scale_last = 1.0;
  static uint32_t last_state_change_time = 0;
  static const uint32_t MIN_STATE_DURATION_MS = 1500; // 1 second minimum in each state
  static float max_waveform_val_raw_smooth = 0.0; // Added for smoothing

  size_t bytes_read = 0;
#ifdef K1_MIC_IM73D_PDM_V1
  const size_t bytes_requested = CONFIG.SAMPLES_PER_CHUNK * sizeof(int16_t);  // PDM: 96*2 = 192 B
#else
  const size_t bytes_requested = CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t);  // SPH0645: 96*4 = 384 B
#endif
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  const int64_t i2s_read_start_us = esp_timer_get_time();
#endif
  // PIO-MIGRATION-STAGE-3 (2026-05-24): i2s_read → i2s_channel_read (rx_chan handle).
  // Read size unchanged (96 * 4 = 384 B). N2 (K1_AUDIO_FREEZE_GUARD_V1): the
  // read is now BOUNDED (pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS)) so the audio
  // loopTask can never block forever on a mic/DMA stall; the #else revert path
  // keeps the original portMAX_DELAY blocking read byte-for-byte.
#ifdef K1_AUDIO_FREEZE_GUARD_V1
  // N2: bounded read so the audio loopTask can never block forever on a mic/DMA
  // stall. On timeout/short read, degrade to a SILENCE frame (zero-fill the
  // unfilled tail) instead of re-processing stale DMA bytes.
  #ifdef K1_MIC_IM73D_PDM_V1
  const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, im73d_samples_i16, bytes_requested, &bytes_read, pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS));
  if (i2s_read_status != ESP_OK || bytes_read < bytes_requested) {
    const size_t samples_got = bytes_read / sizeof(int16_t);
    for (size_t z = samples_got; z < CONFIG.SAMPLES_PER_CHUNK; z++) {
      im73d_samples_i16[z] = 0;
    }
  }
  #else
  const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, i2s_samples_raw, bytes_requested, &bytes_read, pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS));
  if (i2s_read_status != ESP_OK || bytes_read < bytes_requested) {
    const size_t samples_got = bytes_read / sizeof(int32_t);
    for (size_t z = samples_got; z < CONFIG.SAMPLES_PER_CHUNK; z++) {
      i2s_samples_raw[z] = 0;
    }
  }
  #endif
#else
  #ifdef K1_MIC_IM73D_PDM_V1
  const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, im73d_samples_i16, bytes_requested, &bytes_read, portMAX_DELAY);
  #else
  const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, i2s_samples_raw, bytes_requested, &bytes_read, portMAX_DELAY);
  #endif
#endif
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  k1_audio_i2s_read_debug.bytes_requested = (uint32_t)bytes_requested;
  k1_audio_i2s_read_debug.bytes_read = (uint32_t)bytes_read;
  k1_audio_i2s_read_debug.status = (int32_t)i2s_read_status;
  k1_audio_i2s_read_debug.elapsed_us = (uint32_t)(esp_timer_get_time() - i2s_read_start_us);
#else
  (void)i2s_read_status;
  (void)bytes_read;
#endif

#ifdef K1_MIC_IM73D_PDM_V1
  // Raw pre-conditioning telemetry for mic-purity and DSR comparisons.
  // This is before K1_MIC_IM73D_INPUT_GAIN, CONFIG.SENSITIVITY, clamp, DC removal,
  // response_gain, GDFT, and AGC. Keep it O(n), heap-free, and silent except
  // through the existing 1 Hz AP stream.
  uint16_t im73d_raw_peak = 0;
  uint32_t im73d_raw_near_count = 0;
  uint64_t im73d_raw_sum_sq = 0;
  for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
    const int32_t raw_sample = (int32_t)im73d_samples_i16[i];
    const uint32_t raw_mag = (raw_sample < 0) ? (uint32_t)(-raw_sample) : (uint32_t)raw_sample;
    if (raw_mag > im73d_raw_peak) im73d_raw_peak = (raw_mag > 32768U) ? 32768U : (uint16_t)raw_mag;
    if (raw_mag >= K1_MIC_IM73D_RAW_I16_NEAR_RAIL) im73d_raw_near_count++;
    im73d_raw_sum_sq += (uint64_t)raw_mag * (uint64_t)raw_mag;
  }
  im73d_raw_i16_abs_peak = im73d_raw_peak;
  im73d_raw_i16_rms = sqrtf((float)im73d_raw_sum_sq / (float)CONFIG.SAMPLES_PER_CHUNK);
  im73d_raw_i16_near_pct = (float)im73d_raw_near_count / (float)CONFIG.SAMPLES_PER_CHUNK;
#ifdef K1_STM
  // STM reactivity gate from the LIVE pre-AGC mic RMS. The broadband AGC envelope
  // (agc_envelope) is dead code on hardware — measured stuck at 0, gate always
  // closed. This RMS is live and discriminating: ~8 in silence, ~32-60 under EDM,
  // ~144 on peaks (bench-measured). Normalise to [0,1]; it spikes on beats, so the
  // STM modulation pulses with the music.
  {
    float k1_stm_ln = (im73d_raw_i16_rms - 12.0f) / 50.0f;
    if (k1_stm_ln < 0.0f) k1_stm_ln = 0.0f;
    if (k1_stm_ln > 1.0f) k1_stm_ln = 1.0f;
    agc_loudness_norm = SQ15x16(k1_stm_ln);
  }
#endif
#endif

  // One-shot raw frame dump (see serial_menu.h dump_raw handler). Prints the
  // first 32 raw int32 samples as zero-padded hex, tagged for analyst parsing.
  // ~0.5ms total cost (32 USBSerial.printf calls, async USB CDC TX), safely
  // under the 7.5ms / 3ms audio chunk window @ 12.8kHz / 32kHz Fs respectively.
  if (raw_dump_request != 0) {
    const char* tag = (raw_dump_request == 1) ? "[DUMP-SILENCE]" : "[DUMP-TONE-1KHZ]";
    USBSerial.println(tag);
    uint16_t dump_n = CONFIG.SAMPLES_PER_CHUNK < 32 ? CONFIG.SAMPLES_PER_CHUNK : 32;
    for (uint16_t i = 0; i < dump_n; i++) {
#ifdef K1_MIC_IM73D_PDM_V1
      USBSerial.printf("  %d\n", (int)im73d_samples_i16[i]);   // PDM: int16 decimal (silence ±4-18 measured 2026-07-02 @G=16; ±20-40 was pre-characterization pessimism)
#else
      USBSerial.printf("  %08lx\n", (unsigned long)(uint32_t)i2s_samples_raw[i]);
#endif
    }
    USBSerial.println("[DUMP-END]");
    raw_dump_request = 0;
  }

  if (debug_mode && (t_now % 5000 == 0)) {
    USBSerial.print("DEBUG: Bytes read from I2S: ");
    USBSerial.print(bytes_read);
    USBSerial.print(" Max raw value: ");
    USBSerial.println(max_waveform_val_raw);
  }

  max_waveform_val = 0.0;
  max_waveform_val_raw = 0.0;
#ifdef K1_LOUD_GUARD_V1
  k1_loud_guard_begin_frame();
  const float k1_effective_sensitivity = k1_loud_guard_effective_sensitivity();
#endif
  const bool noise_cal_phase_a_active = (!noise_complete && noise_iterations < NOISE_CAL_DC_PHASE_A_FRAMES);
  waveform_history_index++;
  if (waveform_history_index >= 4) {
    waveform_history_index = 0;
  }

  for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
#ifdef K1_MIC_IM73D_PDM_V1
    // IM73D PDM: int16 PCM -> working domain via one characterized pre-sensitivity gain.
    // NO SPH0645 pedestal math (*0.000512 + 56000 - 5120; >>2). Everything below
    // (k1_effective_sensitivity, clamp, -DC_OFFSET, follower, GDFT) is shared/unchanged.
    int32_t sample = (int32_t)((float)im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN);
#else
    int32_t sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120;

    sample = sample >> 2;  // Helps prevent overflow in fixed-point math coming up
#endif
#ifdef K1_LOUD_GUARD_V1
    sample = (int32_t)((float)sample * k1_effective_sensitivity);
    k1_loud_guard_record_preclip(sample);
#else
    sample *= CONFIG.SENSITIVITY;  // Set sensitivity gain
#endif

    if (sample > 32767) {
      sample = 32767;
    } else if (sample < -32767) {
      sample = -32767;
    }

    waveform[i] = sample - CONFIG.DC_OFFSET;
    if (waveform_history != nullptr) {
      waveform_history[waveform_history_index][i] = waveform[i];
    }

    if (noise_cal_phase_a_active) {
      int32_t dc_sample_abs = abs((int32_t)waveform[i]);
      if (dc_sample_abs <= SAMPLE_RAIL_THRESHOLD) {
        dc_offset_sum += (int32_t)waveform[i];
        dc_offset_samples++;
      } else {
        dc_offset_rejected_samples++;
      }
    }

    // SINGLE-DOMAIN FIX (2026-05-20): track AC-corrected peak, not DC-biased peak.
    // Was abs(sample) which carried the MEMS DC bias (~8000 for SPH0645). That
    // poisoned SSL calibration (DC-domain) and post-cal follower math (AC-domain),
    // producing the WAVEFORM-kill mutex. After this change, max_waveform_val_raw
    // is always in the same domain as waveform[i] and downstream math (line 123).
    uint32_t sample_abs = abs(waveform[i]);
    if (sample_abs > max_waveform_val_raw) {
      max_waveform_val_raw = sample_abs;
    }
  }

  // Apply smoothing to the raw max value
  const float smoothing_factor = 0.2; // Adjust as needed (lower = smoother)
  max_waveform_val_raw_smooth = (max_waveform_val_raw * smoothing_factor) + (max_waveform_val_raw_smooth * (1.0 - smoothing_factor));

  if (stream_audio) {
    USBSerial.print("sbs((audio=");
    for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
      USBSerial.print(waveform[i]);
      if (i < CONFIG.SAMPLES_PER_CHUNK - 1) {
        USBSerial.print(',');
      }
    }
    USBSerial.println("))");
  }

  if (!noise_complete) {
    silent_scale = 1.0;  // Force LEDs on during calibration

    // SINGLE-DOMAIN CAL (2026-05-20): two phases so SSL is sampled AFTER DC_OFFSET
    // is established. Without this, SSL ends up in DC-biased units (~SSL=8800 for
    // an ~8000 MEMS bias) while post-cal max_waveform_val_raw is AC-corrected,
    // making max_waveform_val = max_raw - SSL go permanently negative and clamping
    // the follower floor up to SSL → waveform_peak_scaled ≈ 0 → WAVEFORM dies.
    //
    //   Phase A (iters 0..127):  accumulate dc_offset_sum from every non-rail
    //                            sample in the DC-biased chunk.
    //                            DO NOT sample SSL — waveform[i] is not yet AC-corrected.
    //   At iter 128:             stamp CONFIG.DC_OFFSET = dc_offset_sum / valid_samples.
    //                            From the NEXT frame onward, waveform[i] = sample - DC_OFFSET
    //                            is AC-corrected and max_waveform_val_raw lives in AC domain.
    //   Phase B (iters 129..240): sample SSL from AC-corrected max_waveform_val_raw,
    //                            rejecting frames that are too loud to be room silence.
    //   At iter 256 (GDFT.h):    cal completes. DC_OFFSET and SSL are both already
    //                            correctly stamped — no further correction needed.
    if (noise_iterations == NOISE_CAL_DC_PHASE_A_FRAMES) {
      const uint32_t expected_dc_samples = NOISE_CAL_DC_PHASE_A_FRAMES * (uint32_t)CONFIG.SAMPLES_PER_CHUNK;
      const uint32_t min_dc_samples = (expected_dc_samples * NOISE_CAL_DC_MIN_VALID_RATIO_NUM) / NOISE_CAL_DC_MIN_VALID_RATIO_DEN;
      if (dc_offset_samples >= min_dc_samples) {
        int32_t learned_dc_offset = (int32_t)(dc_offset_sum / (int64_t)dc_offset_samples);
        if (calibration_abs_i32(learned_dc_offset) <= NOISE_CAL_DC_MAX_VALID_ABS) {
          CONFIG.DC_OFFSET = learned_dc_offset;  // provisional stamp; locked from here
          noise_cal_dc_valid = true;
        } else {
          noise_cal_reject_once(NOISE_CAL_REJECT_DC_RANGE);
          USBSerial.print("DC_OFFSET cal: learned value out of range=");
          USBSerial.println(learned_dc_offset);
        }
      } else {
        noise_cal_reject_once(NOISE_CAL_REJECT_DC_SAMPLES);
        USBSerial.print("DC_OFFSET cal: insufficient valid samples=");
        USBSerial.print(dc_offset_samples);
        USBSerial.print("/");
        USBSerial.println(expected_dc_samples);
      }
    }
    static_assert(NOISE_CAL_SSL_PHASE_B_FRAMES == sizeof(ssl_cal_buf) / sizeof(ssl_cal_buf[0]),
                  "ssl_cal_buf size must match the Phase-B frame budget");
    if (noise_iterations >= 129 && noise_iterations <= 240 && noise_cal_dc_valid && noise_cal_reject_reason == NOISE_CAL_REJECT_NONE) {
      // max_waveform_val_raw is now AC-corrected (DC_OFFSET stamped, waveform[i] re-derived).
      // ROBUST-SSL (2026-06-11): collect per-frame silence peaks; SSL is stamped from
      // the 90th percentile at Phase-B end. The previous running-max ×1.10 latched on a
      // single transient anywhere in the 840 ms window (observed: one ~839 spike in
      // ~354 ambient → SSL=923 → negative drive). A percentile tolerates isolated
      // contamination; the coarse gate still rejects frames too loud to be silence.
      if (max_waveform_val_raw <= NOISE_CAL_SSL_PHASE_B_MAX_RAW) {
        if (ssl_cal_samples < NOISE_CAL_SSL_PHASE_B_FRAMES) {
          ssl_cal_buf[ssl_cal_samples] = max_waveform_val_raw;
        }
        ssl_cal_samples++;
      } else {
        ssl_cal_rejected_samples++;
      }
    } else if (noise_iterations == 241) {
      // Phase-B end: SSL = p90(silence peaks) * 1.10. One-shot insertion sort of
      // <=112 floats, cal-only (LEDs are forced on; nothing consumes audio here).
      uint16_t n = ssl_cal_samples;
      if (n > NOISE_CAL_SSL_PHASE_B_FRAMES) n = NOISE_CAL_SSL_PHASE_B_FRAMES;
      if (!noise_cal_dc_valid) {
        noise_cal_reject_once(NOISE_CAL_REJECT_DC_SAMPLES);
      } else if (n < NOISE_CAL_SSL_PHASE_B_MIN_ACCEPTED_FRAMES) {
        noise_cal_reject_once(NOISE_CAL_REJECT_SSL_SAMPLES);
      } else {
        for (uint16_t i = 1; i < n; i++) {
          float v = ssl_cal_buf[i];
          int16_t j = (int16_t)(i - 1);
          while (j >= 0 && ssl_cal_buf[j] > v) {
            ssl_cal_buf[j + 1] = ssl_cal_buf[j];
            j--;
          }
          ssl_cal_buf[j + 1] = v;
        }
        const float p50 = ssl_cal_buf[(uint16_t)(((uint32_t)(n - 1) * 5U) / 10U)];
        const float p90 = ssl_cal_buf[(uint16_t)(((uint32_t)(n - 1) * 9U) / 10U)];
        ssl_cal_p50_raw = p50;
        ssl_cal_p90_raw = p90;
        const float p90_to_p50 = (p50 > 1.0f) ? (p90 / p50) : p90;
        const uint32_t learned_ssl = (uint32_t)(p90 * 1.10f + 0.5f);
        if (p90 > NOISE_CAL_SSL_TRUSTED_P90_MAX_RAW) {
          noise_cal_reject_once(NOISE_CAL_REJECT_SSL_TOO_LOUD);
        } else if (p90_to_p50 > NOISE_CAL_SSL_MAX_P90_TO_P50_RATIO) {
          noise_cal_reject_once(NOISE_CAL_REJECT_SSL_UNSTABLE);
        } else if (learned_ssl < NOISE_CAL_SSL_MIN_VALID_RAW || learned_ssl > NOISE_CAL_SSL_MAX_VALID_RAW) {
          noise_cal_reject_once(NOISE_CAL_REJECT_SSL_RANGE);
        } else {
          CONFIG.SWEET_SPOT_MIN_LEVEL = learned_ssl;
          noise_cal_ssl_valid = true;
        }
      }
    }
  } else {
    // Pre-calculate thresholds used multiple times
    float threshold_loud_break = CONFIG.SWEET_SPOT_MIN_LEVEL * 1.20;
    float dynamic_agc_floor_raw = float(min_silent_level_tracker);
    if (dynamic_agc_floor_raw < AGC_FLOOR_MIN_CLAMP_RAW) dynamic_agc_floor_raw = AGC_FLOOR_MIN_CLAMP_RAW;
    if (dynamic_agc_floor_raw > AGC_FLOOR_MAX_CLAMP_RAW) dynamic_agc_floor_raw = AGC_FLOOR_MAX_CLAMP_RAW;
    float dynamic_agc_floor_scaled = dynamic_agc_floor_raw * AGC_FLOOR_SCALING_FACTOR;
    if (dynamic_agc_floor_scaled < AGC_FLOOR_MIN_CLAMP_SCALED) dynamic_agc_floor_scaled = AGC_FLOOR_MIN_CLAMP_SCALED;
    if (dynamic_agc_floor_scaled > AGC_FLOOR_MAX_CLAMP_SCALED) dynamic_agc_floor_scaled = AGC_FLOOR_MAX_CLAMP_SCALED;
    // Silence detection: SSL-derived Schmitt (2026-07-10). dynamic_agc_floor_scaled above
    // is DEAD (the min-tracker decay was commented out, pinning it at a static 100 that is
    // decoupled from the learned floor — a quiet room never fell below it, so silence never
    // latched and the plate never darkened). Derive the thresholds from the calibrated SSL
    // so they track the real ambient, with a Schmitt gap (enter < exit) to kill chatter.
    const float ssl_f = (float)CONFIG.SWEET_SPOT_MIN_LEVEL;
    float threshold_silence = SILENCE_ENTER_SSL_FRAC * ssl_f;        // enter-silence line (low)
    float threshold_silence_exit = SILENCE_EXIT_SSL_FRAC * ssl_f;    // exit-silence line (high)

    max_waveform_val = (max_waveform_val_raw - (CONFIG.SWEET_SPOT_MIN_LEVEL));

    // AP-DRIVE CLAMP (re-landed 2026-06-11 as the verified pair with ROBUST-SSL above):
    // sub-floor signal must map to ZERO drive, never negative — fabsf consumers invert
    // negative drive (quietest frame → brightest) and amplitude→position consumers
    // underflow. Safe now that Phase-B cal cannot latch SSL above the true floor.
    if (max_waveform_val < 0.0f) max_waveform_val = 0.0f;
    const float response_gain = k1_audio_response_gain_effective();
    max_waveform_val *= response_gain;

    if (max_waveform_val > max_waveform_val_follower) {
      float delta = max_waveform_val - max_waveform_val_follower;
      max_waveform_val_follower += delta * 0.25;
    } else if (max_waveform_val < max_waveform_val_follower) {
      float delta = max_waveform_val_follower - max_waveform_val;
      max_waveform_val_follower -= delta * 0.005;

      if (max_waveform_val_follower < CONFIG.SWEET_SPOT_MIN_LEVEL) {
        max_waveform_val_follower = CONFIG.SWEET_SPOT_MIN_LEVEL;
      }
    }
#ifdef K1_MIC_IM73D_PDM_V1
    // PDM cold-boot / failed-cal guard: the follower inits 0.0 and its floor-clamp only
    // runs in the decay branch, so cold-boot silence divides 0/0 -> NaN. A non-zero SSL
    // alone does NOT guarantee a non-zero follower. Force the denominator into the PDM
    // SSL domain (never 0), then clamp any residual non-finite result. Belt to the
    // SSL-never-0 suspenders in the boot/cal-fail/clear_noise_cal paths.
    if (!isfinite(max_waveform_val_follower) ||
        max_waveform_val_follower < (float)CONFIG.SWEET_SPOT_MIN_LEVEL) {
      max_waveform_val_follower = (float)CONFIG.SWEET_SPOT_MIN_LEVEL;
    }
    if (max_waveform_val_follower < 1.0f) max_waveform_val_follower = 1.0f;
#endif
    float waveform_peak_scaled_raw = max_waveform_val / max_waveform_val_follower;
#ifdef K1_MIC_IM73D_PDM_V1
    if (!isfinite(waveform_peak_scaled_raw)) waveform_peak_scaled_raw = 0.0f;
#endif

    if (waveform_peak_scaled_raw > waveform_peak_scaled) {
      float delta = waveform_peak_scaled_raw - waveform_peak_scaled;
#ifdef K1_PEAK_ASYM_ENV
      // ATTACK SNAP (2026-06-11, Captain-directed item 5): asymmetric envelope —
      // fast attack so transients reach the LEDs in ~1-2 AP frames (~8-15 ms vs
      // ~80 ms at the old symmetric 0.25), slow release below so trails keep
      // their grace. The method doc's "raw trigger + smoothed body" archetype,
      // applied at the shared drive signal. REVERT = delete the -D flag.
      waveform_peak_scaled += delta * 0.65;
#else
      waveform_peak_scaled += delta * 0.25;
#endif
    } else if (waveform_peak_scaled_raw < waveform_peak_scaled) {
      float delta = waveform_peak_scaled - waveform_peak_scaled_raw;
#ifdef K1_PEAK_ASYM_ENV
      waveform_peak_scaled -= delta * 0.15;
#else
      waveform_peak_scaled -= delta * 0.25;
#endif
    }

    // Use the maximum amplitude of the captured frame to set
    // the Sweet Spot state. Think of this like a coordinate
    // space where 0 is the center LED, -1 is the left, and
    // +1 is the right. See run_sweet_spot() in led_utilities.h
    // for how this value translates to the final LED brightnesses

    int8_t potential_next_state = sweet_spot_state; // Assume current state initially

    // *** Use the SMOOTHED value for state decision, with Schmitt hysteresis on the ***
    // *** silence boundary: enter -1 below threshold_silence; once silent, only leave ***
    // *** -1 when the smoothed peak rises above the higher threshold_silence_exit. ***
    const bool was_silent_state = (sweet_spot_state == -1);
    if (was_silent_state) {
        if (max_waveform_val_raw_smooth >= threshold_silence_exit) {
            potential_next_state = (max_waveform_val_raw_smooth >= CONFIG.SWEET_SPOT_MAX_LEVEL) ? 1 : 0;
        } else {
            potential_next_state = -1;   // stay silent until we clear the exit line
        }
    } else {
        if (max_waveform_val_raw_smooth <= threshold_silence) {
            potential_next_state = -1;
        } else if (max_waveform_val_raw_smooth >= CONFIG.SWEET_SPOT_MAX_LEVEL) {
            potential_next_state = 1;
        } else {
            potential_next_state = 0;
        }
    }

    if (potential_next_state != sweet_spot_state) {
        if ((t_now - last_state_change_time) > MIN_STATE_DURATION_MS) {
            int8_t previous_state = sweet_spot_state;
            sweet_spot_state = potential_next_state;
            last_state_change_time = t_now;

            if (sweet_spot_state == -1) {
                silence_temp = true;
                silence_switched = t_now;

                if (previous_state != -1) {
                     // *** Use RAW value for deadband check ***
                     float agc_delta = threshold_silence - max_waveform_val_raw; // Use pre-calculated threshold
                     if (agc_delta > 50.0) {
                         min_silent_level_tracker = SQ15x16(AGC_FLOOR_INITIAL_RESET);
                         if (debug_mode) {
                             USBSerial.print("DEBUG: AGC Floor Tracker Reset (deadband met): raw_val=");
                             USBSerial.print(max_waveform_val_raw);
                             USBSerial.print(" threshold=");
                             USBSerial.println(threshold_silence); // Use pre-calculated threshold
                         }
                     } else {
                         if (debug_mode) {
                             USBSerial.print("DEBUG: AGC Floor Tracker not reset due to deadband, delta=");
                             USBSerial.println(agc_delta);
                         }
                     }
                }

                if (debug_mode) {
                    USBSerial.println("DEBUG: Entered silent state (Hysteresis Passed)");
                    USBSerial.print("  max_waveform_val_raw: "); USBSerial.print(max_waveform_val_raw);
                    USBSerial.print("  MIN_LEVEL threshold: "); USBSerial.println(threshold_silence); // Use pre-calculated threshold
                }
            } else {
                if (debug_mode) {
                   USBSerial.print("DEBUG: Entered ");
                   USBSerial.print(sweet_spot_state == 1 ? "loud" : "normal");
                   USBSerial.print(" state (Hysteresis Passed), delta=");
                   USBSerial.println(max_waveform_val_raw - threshold_silence); // Use pre-calculated threshold
                }
            }
        }
    }

    if (sweet_spot_state == -1) {
        // --- REMOVED OLD SINGLE TRACKER UPDATE LOGIC ---
        // SQ15x16 current_raw_level = SQ15x16(max_waveform_val_raw);
        // if (current_raw_level < min_silent_level_tracker) {
        //     min_silent_level_tracker = current_raw_level;
        // } else {
        //     min_silent_level_tracker += SQ15x16(AGC_FLOOR_RECOVERY_RATE);
        //     min_silent_level_tracker = fmin_fixed(min_silent_level_tracker, SQ15x16(AGC_FLOOR_INITIAL_RESET));
        // }
        //  if (debug_mode && (t_now % 1000 == 0)) {
        //      USBSerial.print("DEBUG (Silence): AGC Floor Tracker Value: "); USBSerial.println(float(min_silent_level_tracker));
        //  }
        // --- END REMOVED --- 
    }

    // Go-dark quiet detection: RAW per-frame RMS vs an ABSOLUTE threshold with hysteresis
    // (firmware-v3 pre-gate port — pure RMS, cf. ControlBus.cpp Stage 7). Replaces the
    // SSL/sweet_spot_state==-1 gate (smoothed-peak floor sits above SSL in a normal room)
    // AND deliberately does NOT re-use the peak-based loud_sound_detected veto
    // (threshold_loud_break = SSL*1.2 ≈ 326 trips on quiet-room peaks 150-870, which would
    // veto silence every frame). A genuine loud sound spikes rms_raw well past the exit
    // threshold, so the RMS hysteresis breaks silence on its own. The long SILENCE_DWELL_MS
    // is what keeps genuinely quiet *music* from darkening the plate.
    static bool k1_rms_silent_state = false;
    if (k1_rms_silent_state) {
        k1_rms_silent_state = (k1_silence_rms_raw < K1_SILENCE_RMS_EXIT);   // stay silent until clearly above
    } else {
        k1_rms_silent_state = (k1_silence_rms_raw < K1_SILENCE_RMS_ENTER);  // enter when below
    }

    if (!k1_rms_silent_state) {
        if (silence && debug_mode) {
             USBSerial.println("DEBUG: Silence broken (audio detected)");
        }
        silence = false;
        silence_temp = false;
        silence_switched = t_now;
    } else {
         silence_temp = true;
         if (t_now - silence_switched >= SILENCE_DWELL_MS) {
            if (!silence && debug_mode) {
                USBSerial.println("DEBUG: Extended silence detected (dwell met)");
            }
            silence = true;
         }
    }

    if (debug_mode && (t_now % 10000 == 0)) {
      USBSerial.print("DEBUG: silent_scale=");
      USBSerial.print(float(silent_scale));
      USBSerial.print(" silence=");
      USBSerial.print(silence ? "true" : "false");
      USBSerial.print(" sweet_spot_state=");
      USBSerial.println(sweet_spot_state);
    }

    if (CONFIG.STANDBY_DIMMING) {
      // Asymmetric fade: slow to true black on sustained silence, near-instant wake on
      // the first sound. silent_scale multiplies MASTER_BRIGHTNESS on the plate
      // (led_utilities.h:399) → reaches 0 = fully dark. K1 has no indicator LEDs.
      const float fade_target = silence ? 0.0f : 1.0f;
      const float fade_a = (fade_target < silent_scale) ? SILENT_FADE_DOWN_ALPHA : SILENT_FADE_UP_ALPHA;
      silent_scale = fade_target * fade_a + silent_scale_last * (1.0f - fade_a);
      silent_scale_last = silent_scale;
    } else {
      silent_scale = 1.0;
    }

    sweet_spot_state_last = sweet_spot_state;

    if (debug_mode && (t_now % 2000 == 0)) {
        USBSerial.print("DEBUG (State): sweet_spot_state="); USBSerial.print(sweet_spot_state);
        USBSerial.print(" | max_waveform_val_raw="); USBSerial.print(max_waveform_val_raw);
        USBSerial.print(" | silence_threshold="); USBSerial.println(threshold_silence); // Use pre-calculated threshold
    }
  }

  for (int i = 0; i < SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i++) {
    sample_window[i] = sample_window[i + CONFIG.SAMPLES_PER_CHUNK];
  }
  for (int i = SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i < SAMPLE_HISTORY_LENGTH; i++) {
    sample_window[i] = audio_response_gain_apply_sample(waveform[i - (SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK)]);
  }

  const SQ15x16 RECIP_32768 = SQ15x16(1.0 / 32768.0);
  for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
    waveform_fixed_point[i] = SQ15x16(audio_response_gain_apply_sample(waveform[i])) * RECIP_32768;
  }

  // --- AP instrumentation (2026-05-20) — WAVEFORM-kill isolation telemetry ---
  // Serial-gated and rate-limited to 1 Hz. Reveals which AP variable
  // goes degenerate when WAVEFORM dies post-noise-cal. Pair with the AGC-
  // disabled GDFT.h to diagnose the kill mechanism.
  //   SSL          — sweet_spot_min_level (silence threshold; should ~hover, not drift)
  //   DC           — dc_offset (should be stable post-cal, ~8000 for SPH0645)
  //   max_raw      — peak amplitude this chunk
  //   follower     — slow-decay envelope (should follow max_raw with hysteresis)
  //   peak_scaled  — waveform_peak_scaled (the value WAVEFORM mode actually reads)
  //   silent_scale — silence-dimming multiplier (0.0..1.0; goes to 0 if STANDBY_DIMMING=true and silence==true)
  //   silence      — extended-silence flag (10 s timeout)
  //   CAL_SOURCE/CAL_VALID — calibration provenance for harness captures
  static uint32_t last_ap_dbg = 0;
  // [AP] stream cadence. Default 1 Hz (production). Override via -DK1_AP_STREAM_INTERVAL_MS
  // for higher-rate diagnostics (e.g. loud-guard limit-cycle A/B needs ~10 Hz to resolve a
  // ~1.5 s oscillation without aliasing). Production builds leave the default untouched.
#ifndef K1_AP_STREAM_INTERVAL_MS
#define K1_AP_STREAM_INTERVAL_MS 1000
#endif
  if (AP_STREAM_ENABLED && millis() - last_ap_dbg > K1_AP_STREAM_INTERVAL_MS) {
    K1TempoEvent     tev = k1_tempo_read();
    K1OnsetBeatEvent oev = k1_onset_beat_read();
    USBSerial.printf("[AP] SSL=%u DC=%d max_raw=%.0f follower=%.0f peak_scaled=%.3f response_gain=%.3f silent_scale=%.3f silence=%d sil_pk=%.0f rms_raw=%.4f dim=%d cal_source=%s cal_valid=%d cal_reason=%s | bpm=%.1f conf=%.2f lock=%d phase=%.2f beat=%d bstr=%.2f | onset=%d bass=%d ostr=%.2f",
      CONFIG.SWEET_SPOT_MIN_LEVEL, (int)CONFIG.DC_OFFSET, (float)max_waveform_val_raw,
      (float)max_waveform_val_follower, (float)waveform_peak_scaled, (float)k1_audio_response_gain_effective(), (float)silent_scale,
      silence ? 1 : 0, (float)max_waveform_val_raw_smooth, k1_silence_rms_raw, CONFIG.STANDBY_DIMMING ? 1 : 0,
      calibration_source_name(), calibration_valid ? 1 : 0,
      noise_cal_reject_reason_name(noise_cal_reject_reason),
      (float)tev.bpm, (float)tev.confidence, tev.locked ? 1 : 0, (float)tev.phase01, tev.beat_tick ? 1 : 0, (float)tev.beat_strength,
      oev.onset ? 1 : 0, oev.bass_onset ? 1 : 0, (float)oev.bass_onset_strength);
#ifdef K1_MIC_IM73D_PDM_V1
    USBSerial.printf(" | raw_i16_abs_peak=%u raw_i16_rms=%.1f raw_i16_near_pct=%.3f",
      im73d_raw_i16_abs_peak,
      im73d_raw_i16_rms,
      im73d_raw_i16_near_pct);
#endif
#ifdef K1_LOUD_GUARD_V1
    USBSerial.printf(" | k1_loud=%d input_trim=%.3f gdft_trim=%.3f agc_gain=%.3f agc_env=%.3f clip_pct=%.3f near_pct=%.3f peak_pin=%.3f spec_pin=%.3f spec_sat=%.3f mode=%d",
      k1_loud_guard_enabled ? 1 : 0,
      k1_loud_input_trim,
      k1_loud_gdft_trim,
      (float)agc_bands[0].gain,
      (float)agc_envelope,
      k1_loud_clip_duty,
      k1_loud_near_rail_duty,
      k1_loud_peak_pin_duty,
      k1_loud_spec_sat_duty,
      k1_loud_spec_sat_fraction,
      k1_loud_guard_mode);
#endif
#ifdef K1_STM
    {
      // STM producer readout on the [AP] line (bench K1_STM builds only): proves the
      // live spectrogram[] -> k1_stm_process -> snapshot wiring emits real spectral-
      // temporal modulation from the mic (ready + non-zero energies under audio;
      // ready=0 / zeros in silence). k1_stm_read() is visible via k1_tempo.h ->
      // k1_audio_snapshot.h. Runs on the AP (Core 0) path, gated to AP telemetry.
      K1StmResult stm_ap = k1_stm_read();
      USBSerial.printf(" | stm_loud=%.3f agc_env=%.4f agc_nf=%.4f agc_gated=%d stm_ready=%d stm_tE=%.4f stm_sE=%.4f",
        float(agc_loudness_norm), float(agc_envelope), float(agc_noise_floor), agc_gated ? 1 : 0,
        stm_ap.ready ? 1 : 0, stm_ap.temporal_energy, stm_ap.spectral_energy);
    }
#endif
    USBSerial.println();
    last_ap_dbg = millis();
  }
}

#ifdef ENABLE_AP_STREAM
// PIO-APCAP (2026-05-25): :ap_capture=<ms> windowed AP harness capture. ap_capture_tick()
// is called once per frame from loop() AFTER process_GDFT, where spectrogram_smooth /
// chromagram_smooth are fresh (the 1 Hz ap_stream emit above runs inside
// acquire_sample_chunk, one stage before GDFT, so those arrays are stale there).
void ap_capture_arm(uint32_t ms) {
  ap_capture_active = true;
  ap_capture_end_ms = millis() + ms;
  ap_capture_frames = 0;
  ap_capture_max_raw_min = 1e30f;
  ap_capture_max_raw_max = -1e30f;
  ap_capture_peak_min = 1e30f;
  ap_capture_peak_max = -1e30f;
  ap_capture_follower_sum = 0.0;
  ap_capture_chroma_sum = 0.0;
  ap_capture_silence_any = false;
  for (uint16_t i = 0; i < NUM_FREQS; i++) ap_capture_spec_sum[i] = 0.0f;
}

void ap_capture_tick() {
  if (!ap_capture_active) return;

  float mr = (float)max_waveform_val_raw;
  float pk = (float)waveform_peak_scaled;
  float fo = (float)max_waveform_val_follower;
  if (mr < ap_capture_max_raw_min) ap_capture_max_raw_min = mr;
  if (mr > ap_capture_max_raw_max) ap_capture_max_raw_max = mr;
  if (pk < ap_capture_peak_min) ap_capture_peak_min = pk;
  if (pk > ap_capture_peak_max) ap_capture_peak_max = pk;
  ap_capture_follower_sum += fo;
  float chroma_frame = 0.0f;
  for (uint8_t c = 0; c < 12; c++) chroma_frame += (float)chromagram_smooth[c];
  ap_capture_chroma_sum += (chroma_frame / 12.0f);
  for (uint16_t i = 0; i < NUM_FREQS; i++) ap_capture_spec_sum[i] += (float)spectrogram_smooth[i];
  if (silence) ap_capture_silence_any = true;
  ap_capture_frames++;

  if (int32_t(millis() - ap_capture_end_ms) >= 0) {
    uint16_t argmax = 0;
    float best = -1.0f;
    for (uint16_t i = 0; i < NUM_FREQS; i++) {
      if (ap_capture_spec_sum[i] > best) { best = ap_capture_spec_sum[i]; argmax = i; }
    }
    float follower_mean = ap_capture_frames ? (float)(ap_capture_follower_sum / ap_capture_frames) : 0.0f;
    float chroma_mean   = ap_capture_frames ? (float)(ap_capture_chroma_sum / ap_capture_frames) : 0.0f;
    USBSerial.printf("[APCAP] frames=%lu max_raw=%.0f/%.0f peak_scaled=%.3f/%.3f follower_mean=%.1f spec_argmax=%u chroma_mean=%.4f silence=%d SSL=%u DC=%d cal_source=%s cal_valid=%d cal_reason=%s\n",
      (unsigned long)ap_capture_frames,
      ap_capture_max_raw_min, ap_capture_max_raw_max,
      ap_capture_peak_min, ap_capture_peak_max,
      follower_mean, (unsigned)argmax, chroma_mean,
      ap_capture_silence_any ? 1 : 0,
      (unsigned)CONFIG.SWEET_SPOT_MIN_LEVEL,
      (int)CONFIG.DC_OFFSET,
      calibration_source_name(),
      calibration_valid ? 1 : 0,
      noise_cal_reject_reason_name(noise_cal_reject_reason));
    ap_capture_active = false;
  }
}
#endif

void calculate_vu() {
  /*
    Calculates perceived audio loudness or Volume Unit (VU). Uses root mean square (RMS) method 
    for accurate representation of perceived loudness and incorporates a noise floor calibration.
    If calibration is active, updates noise floor level. If not, subtracts the noise floor from
    the calculated volume and normalizes the volume level.

    Parameters:
    - audio_samples[]: Audio samples to process.
    - sample_count: Number of samples in audio_samples array.

    Global variables:
    - audio_vu_level: Current VU level.
    - audio_vu_level_last: Last calculated VU level.
    - CONFIG.VU_LEVEL_FLOOR: Quietest level considered as audio signal.
    - audio_vu_level_average: Average of the current and the last VU level.
    - noise_cal_active: Indicator of active noise floor calibration.
    */

  // Store last volume level
  audio_vu_level_last = audio_vu_level;

  float sum = 0.0;

  for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
    sum += float(waveform_fixed_point[i] * waveform_fixed_point[i]);
  }

  SQ15x16 rms = SQ15x16(sqrtf((float)(sum / CONFIG.SAMPLES_PER_CHUNK))); // Phase 1 2026-05-20: sqrt→sqrtf for S2 soft-float
  audio_vu_level = rms;
  k1_silence_rms_raw = (float)rms;   // raw pre-floor RMS for go-dark silence detection (firmware-v3 pre-gate port)

  if (!noise_complete) {
    if (!noise_cal_dc_valid ||
        noise_cal_reject_reason != NOISE_CAL_REJECT_NONE ||
        noise_iterations < 129 ||
        noise_iterations > 240 ||
        max_waveform_val_raw > NOISE_CAL_SSL_PHASE_B_MAX_RAW) {
      return;
    }
    if (float(audio_vu_level * 1.5) > CONFIG.VU_LEVEL_FLOOR) {
      CONFIG.VU_LEVEL_FLOOR = float(audio_vu_level * 1.5);
    }
  } else {
    audio_vu_level -= CONFIG.VU_LEVEL_FLOOR;

    if (audio_vu_level < 0.0) {
      audio_vu_level = 0.0;
    }

    CONFIG.VU_LEVEL_FLOOR = min(0.99f, CONFIG.VU_LEVEL_FLOOR);
    audio_vu_level /= (1.0 - CONFIG.VU_LEVEL_FLOOR);
  }

  audio_vu_level_average = (audio_vu_level + audio_vu_level_last) / (2.0);
}
