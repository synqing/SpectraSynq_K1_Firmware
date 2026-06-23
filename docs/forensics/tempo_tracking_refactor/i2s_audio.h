/*----------------------------------------
  Sensory Bridge I2S FUNCTIONS
  ----------------------------------------*/
#include "sb_tempo.h"        // AP_STREAM tempo fields (bpm/conf/lock/phase/beat) — header-guarded
#include "sb_onset_beat.h"   // AP_STREAM onset fields (onset/bass) — header-guarded

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
// DMA sizing preserved 1:1 from legacy (dma_desc_num=2, dma_frame_num=96).
// portMAX_DELAY blocking and read size (SAMPLES_PER_CHUNK*sizeof(int32_t)=384 B)
// preserved verbatim. Init keeps void return + PASS/FAIL print contract; NO
// ESP_ERROR_CHECK (init failure must not panic-reboot). Lines below
// (acquire_sample_chunk extraction, DC calibration, sweet-spot, AGC,
// calculate_vu) byte-identical to pre-migration except the single
// i2s_read → i2s_channel_read substitution.
//
// See: docs/forensics/2026-05-24-doctrine-gate-pio-migration.md
//      MIGRATION_PLAN-v2-rebaselined.md §8 Stage 3
//      https://github.com/Lixie-Labs/Emotiscope/blob/HEAD/src/microphone.h
#include <driver/i2s_std.h>

static i2s_chan_handle_t rx_chan = NULL;

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

void init_i2s() {
  esp_err_t result;

  // RX channel — mirror legacy dma_buf_count=2, dma_buf_len=SAMPLES_PER_CHUNK.
  i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_PORT, I2S_ROLE_MASTER);
  chan_cfg.dma_desc_num  = 2;
  chan_cfg.dma_frame_num = CONFIG.SAMPLES_PER_CHUNK;   // 96
  chan_cfg.auto_clear    = false;
  result = i2s_new_channel(&chan_cfg, NULL, &rx_chan); // tx=NULL → RX-only
  USBSerial.print("INIT I2S (channel): ");
  USBSerial.println(result == ESP_OK ? SB_PASS : SB_FAIL);

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
  USBSerial.println(result == ESP_OK ? SB_PASS : SB_FAIL);

  result = i2s_channel_enable(rx_chan);   // new driver does NOT auto-start
  USBSerial.print("I2S ENABLE: ");
  USBSerial.println(result == ESP_OK ? SB_PASS : SB_FAIL);
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
  // PIO-MIGRATION-STAGE-3 (2026-05-24): i2s_read → i2s_channel_read (rx_chan handle).
  // Read size unchanged (96 * 4 = 384 B). portMAX_DELAY blocking unchanged.
  i2s_channel_read(rx_chan, i2s_samples_raw, CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t), &bytes_read, portMAX_DELAY);

  // One-shot raw frame dump (see serial_menu.h dump_raw handler). Prints the
  // first 32 raw int32 samples as zero-padded hex, tagged for analyst parsing.
  // ~0.5ms total cost (32 USBSerial.printf calls, async USB CDC TX), safely
  // under the 7.5ms / 3ms audio chunk window @ 12.8kHz / 32kHz Fs respectively.
  if (raw_dump_request != 0) {
    const char* tag = (raw_dump_request == 1) ? "[DUMP-SILENCE]" : "[DUMP-TONE-1KHZ]";
    USBSerial.println(tag);
    uint16_t dump_n = CONFIG.SAMPLES_PER_CHUNK < 32 ? CONFIG.SAMPLES_PER_CHUNK : 32;
    for (uint16_t i = 0; i < dump_n; i++) {
      USBSerial.printf("  %08lx\n", (unsigned long)(uint32_t)i2s_samples_raw[i]);
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
  waveform_history_index++;
  if (waveform_history_index >= 4) {
    waveform_history_index = 0;
  }

  for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
    int32_t sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120;

    sample = sample >> 2;  // Helps prevent overflow in fixed-point math coming up
    sample *= CONFIG.SENSITIVITY;  // Set sensitivity gain

    if (sample > 32767) {
      sample = 32767;
    } else if (sample < -32767) {
      sample = -32767;
    }

    waveform[i] = sample - CONFIG.DC_OFFSET;
    if (waveform_history != nullptr) {
      waveform_history[waveform_history_index][i] = waveform[i];
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
    //   Phase A (iters 0..127):  accumulate dc_offset_sum from DC-biased waveform[0].
    //                            DO NOT sample SSL — waveform[i] is not yet AC-corrected.
    //   At iter 128:             stamp CONFIG.DC_OFFSET = dc_offset_sum / 128. From the
    //                            NEXT frame onward, waveform[i] = sample - DC_OFFSET is
    //                            AC-corrected and max_waveform_val_raw lives in AC domain.
    //   Phase B (iters 129..240): sample SSL from AC-corrected max_waveform_val_raw.
    //   At iter 256 (GDFT.h):    cal completes. DC_OFFSET and SSL are both already
    //                            correctly stamped — no further correction needed.
    if (noise_iterations < 128) {
      // Fix-D Layer 2 (2026-05-24): gate the DC accumulator. Reject samples at
      // or near the post-extraction clip rail (±32767) — those measure the
      // clipping ceiling, not the noise floor, and averaging them in produces
      // the rail-pinned poisoned calibration that breaks the audio pipeline on
      // the next boot. waveform[0] is post-clip (DC_OFFSET=0 in Phase A per
      // noise_cal.h start_noise_cal), so abs(waveform[0]) is the true post-math
      // magnitude this iteration.
      if (abs(waveform[0]) <= SAMPLE_RAIL_THRESHOLD) {
        dc_offset_sum += waveform[0];
        dc_offset_samples++;
      }
    } else if (noise_iterations == 128) {
      // Fix-D Layer 2: divide by the count of VALID samples, not the iter count.
      // If zero valid samples were observed (entire 128-iter Phase A was
      // rail-pinned — likely cal fired during loud audio), refuse to update
      // CONFIG.DC_OFFSET. The reset value of 0 from start_noise_cal stays in
      // place; the boot-time Layer 1 guard in system.h will then treat the
      // device as uncalibrated and surface a clear "run start_noise_cal under
      // silence" cue, rather than persisting a poisoned average.
      if (dc_offset_samples > 0) {
        CONFIG.DC_OFFSET = dc_offset_sum / dc_offset_samples;  // provisional stamp; locked from here
      } else {
        USBSerial.println("DC_OFFSET cal: 0 valid samples (Phase A was entirely rail-pinned) — refusing to update; rerun start_noise_cal under confirmed silence.");
      }
    }
    if (noise_iterations >= 129 && noise_iterations <= 240) {
      // max_waveform_val_raw is now AC-corrected (DC_OFFSET stamped, waveform[i] re-derived).
      // SSL = silence-floor * 1.10 in AC domain.
      if (max_waveform_val_raw * 1.10 > CONFIG.SWEET_SPOT_MIN_LEVEL) {
        CONFIG.SWEET_SPOT_MIN_LEVEL = max_waveform_val_raw * 1.10;
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
    float threshold_silence = dynamic_agc_floor_scaled;

    max_waveform_val = (max_waveform_val_raw - (CONFIG.SWEET_SPOT_MIN_LEVEL));

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
    float waveform_peak_scaled_raw = max_waveform_val / max_waveform_val_follower;

    if (waveform_peak_scaled_raw > waveform_peak_scaled) {
      float delta = waveform_peak_scaled_raw - waveform_peak_scaled;
      waveform_peak_scaled += delta * 0.25;
    } else if (waveform_peak_scaled_raw < waveform_peak_scaled) {
      float delta = waveform_peak_scaled - waveform_peak_scaled_raw;
      waveform_peak_scaled -= delta * 0.25;
    }

    // Use the maximum amplitude of the captured frame to set
    // the Sweet Spot state. Think of this like a coordinate
    // space where 0 is the center LED, -1 is the left, and
    // +1 is the right. See run_sweet_spot() in led_utilities.h
    // for how this value translates to the final LED brightnesses

    int8_t potential_next_state = sweet_spot_state; // Assume current state initially

    // *** Use the SMOOTHED value for state decision ***
    if (max_waveform_val_raw_smooth <= threshold_silence) { // Use pre-calculated threshold
        potential_next_state = -1;
    } else if (max_waveform_val_raw_smooth >= CONFIG.SWEET_SPOT_MAX_LEVEL) {
        potential_next_state = 1;
    } else {
        potential_next_state = 0;
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

    // *** Use RAW value for loud sound detection ***
    bool loud_sound_detected = (max_waveform_val_raw > threshold_loud_break); // Use pre-calculated threshold

    if (loud_sound_detected) {
        if (silence && debug_mode) {
             USBSerial.println("DEBUG: Silence broken by loud sound");
        }
        silence = false;
        silence_temp = false;
        silence_switched = t_now;
    } else if (sweet_spot_state == -1) {
         silence_temp = true;
         if (t_now - silence_switched >= 10000) {
            if (!silence && debug_mode) {
                USBSerial.println("DEBUG: Extended silence detected (10s)");
            }
            silence = true;
         }
    } else {
        silence = false;
        silence_temp = false;
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
      float silent_scale_raw = silence ? 0.0 : 1.0;
      silent_scale = silent_scale_raw * 0.1 + silent_scale_last * 0.9;
      silent_scale_last = silent_scale;
    } else {
      silent_scale = 1.0;
    }

    for (int i = 0; i < SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i++) {
      sample_window[i] = sample_window[i + CONFIG.SAMPLES_PER_CHUNK];
    }
    for (int i = SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK; i < SAMPLE_HISTORY_LENGTH; i++) {
      sample_window[i] = waveform[i - (SAMPLE_HISTORY_LENGTH - CONFIG.SAMPLES_PER_CHUNK)];
    }

    // Pre-calculate reciprocal for fixed-point conversion
    const SQ15x16 RECIP_32768 = SQ15x16(1.0 / 32768.0);
    for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK; i++) {
      // Convert using multiplication instead of division
      waveform_fixed_point[i] = SQ15x16(waveform[i]) * RECIP_32768;
    }

    sweet_spot_state_last = sweet_spot_state;

    if (debug_mode && (t_now % 2000 == 0)) {
        USBSerial.print("DEBUG (State): sweet_spot_state="); USBSerial.print(sweet_spot_state);
        USBSerial.print(" | max_waveform_val_raw="); USBSerial.print(max_waveform_val_raw);
        USBSerial.print(" | silence_threshold="); USBSerial.println(threshold_silence); // Use pre-calculated threshold
    }
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
  if (AP_STREAM_ENABLED && millis() - last_ap_dbg > 1000) {
    SBTempoEvent     tev = sb_tempo_read();
    SBOnsetBeatEvent oev = sb_onset_beat_read();
    USBSerial.printf("[AP] SSL=%u DC=%d max_raw=%.0f follower=%.0f peak_scaled=%.3f silent_scale=%.3f silence=%d cal_source=%s cal_valid=%d | bpm=%.1f conf=%.2f lock=%d phase=%.2f beat=%d bstr=%.2f | onset=%d bass=%d ostr=%.2f\n",
      CONFIG.SWEET_SPOT_MIN_LEVEL, (int)CONFIG.DC_OFFSET, (float)max_waveform_val_raw,
      (float)max_waveform_val_follower, (float)waveform_peak_scaled, (float)silent_scale,
      silence ? 1 : 0, calibration_source_name(), calibration_valid ? 1 : 0,
      (float)tev.bpm, (float)tev.confidence, tev.locked ? 1 : 0, (float)tev.phase01, tev.beat_tick ? 1 : 0, (float)tev.beat_strength,
      oev.onset ? 1 : 0, oev.bass_onset ? 1 : 0, (float)oev.bass_onset_strength);
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
    USBSerial.printf("[APCAP] frames=%lu max_raw=%.0f/%.0f peak_scaled=%.3f/%.3f follower_mean=%.1f spec_argmax=%u chroma_mean=%.4f silence=%d SSL=%u DC=%d cal_source=%s cal_valid=%d\n",
      (unsigned long)ap_capture_frames,
      ap_capture_max_raw_min, ap_capture_max_raw_max,
      ap_capture_peak_min, ap_capture_peak_max,
      follower_mean, (unsigned)argmax, chroma_mean,
      ap_capture_silence_any ? 1 : 0,
      (unsigned)CONFIG.SWEET_SPOT_MIN_LEVEL,
      (int)CONFIG.DC_OFFSET,
      calibration_source_name(),
      calibration_valid ? 1 : 0);
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

  if (!noise_complete) {
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
