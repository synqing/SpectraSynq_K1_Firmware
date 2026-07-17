#include <stdint.h>
#include <USB.h> // For USBSerial
#include <FastLED.h>
#include <esp_system.h> // For ESP.restart()
#include "globals.h" // For global variables like MASTER_BRIGHTNESS, debug_mode, frequencies etc.
#include "constants.h" // For band definitions, NUM_FREQS etc.
#include "k1_spectral_honesty.h" // Shared Hann + DFT measurement-honesty primitives
#include "led_utilities.h" // For lock_leds, show_leds

uint32_t timing_start = 0;
extern void run_sweet_spot();
extern void show_leds();

// Forward declarations
void init_cochlear_agc();

void reboot() {
  lock_leds();
  USBSerial.println("--- ! REBOOTING to apply changes (You may need to restart the Serial Monitor)");
  USBSerial.flush();
  for(float i = 1.0; i >= 0.0; i-=0.05){
    MASTER_BRIGHTNESS = i;
    run_sweet_spot();
    show_leds();
    FastLED.delay(12); // Takes ~250ms total
  }
  FastLED.setBrightness(0);
  FastLED.show();
  ESP.restart();
}

void start_timing(const char* func_name) {
  USBSerial.print(func_name);
  USBSerial.print(": ");
  USBSerial.flush();
  timing_start = micros();
}

void end_timing() {
  uint32_t timing_end = micros();
  uint32_t t_delta = timing_end - timing_start;

  USBSerial.print("DONE IN ");
  USBSerial.print(t_delta / 1000.0, 3);
  USBSerial.println(" MS");
}

void check_current_function() {
  function_hits[function_id]++;
}

static void usb_event_callback(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
  if (event_base == ARDUINO_USB_EVENTS) {
    //arduino_usb_event_data_t * data = (arduino_usb_event_data_t*)event_data;
    switch (event_id) {
      case ARDUINO_USB_STARTED_EVENT:
        //Serial0.println("USB PLUGGED");
        break;
      case ARDUINO_USB_STOPPED_EVENT:
        //Serial0.println("USB UNPLUGGED");
        break;
      case ARDUINO_USB_SUSPEND_EVENT:
        //Serial0.printf("USB SUSPENDED: remote_wakeup_en: %u\n", data->suspend.remote_wakeup_en);
        break;
      case ARDUINO_USB_RESUME_EVENT:
        //Serial0.println("USB RESUMED");
        break;

      default:
        break;
    }
  }
#if K1_ENABLE_USB_MSC_UPDATE
  else if (event_base == ARDUINO_FIRMWARE_MSC_EVENTS) {
    //arduino_firmware_msc_event_data_t * data = (arduino_firmware_msc_event_data_t*)event_data;
    switch (event_id) {
      case ARDUINO_FIRMWARE_MSC_START_EVENT:
        //Serial0.println("MSC Update Start");
        msc_update_started = true;
        break;
      case ARDUINO_FIRMWARE_MSC_WRITE_EVENT:
        //HWSerial.printf("MSC Update Write %u bytes at offset %u\n", data->write.size, data->write.offset);
        //Serial0.print(".");
        break;
      case ARDUINO_FIRMWARE_MSC_END_EVENT:
        //Serial0.printf("\nMSC Update End: %u bytes\n", data->end.size);
        break;
      case ARDUINO_FIRMWARE_MSC_ERROR_EVENT:
        //Serial0.printf("MSC Update ERROR! Progress: %u bytes\n", data->error.size);
        break;
      case ARDUINO_FIRMWARE_MSC_POWER_EVENT:
        //Serial0.printf("MSC Update Power: power: %u, start: %u, eject: %u", data->power.power_condition, data->power.start, data->power.load_eject);
        break;

      default:
        break;
    }
  }
#endif
}

#if K1_ENABLE_USB_MSC_UPDATE
void enable_usb_update_mode() {
  USB.onEvent(usb_event_callback);

  MSC_Update.onEvent(usb_event_callback);
  MSC_Update.begin();

  MASTER_BRIGHTNESS = 1.0;

  uint8_t led_index = 0;
  uint8_t sweet_index = 0;

  const uint8_t sweet_order[3][3] = {
    {1, 0, 0},
    {0, 1, 0},
    {0, 0, 1}
  };

  while (true) {
    for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
      leds_16[i] = {0, 0, 0};
    }

    if (msc_update_started == false) {
      leds_16[led_index] = {0, 0, 0.25};
#if K1_HAS_SWEET_SPOT_LEDS
      ledcWrite(SWEET_SPOT_LEFT_CHANNEL,   sweet_order[sweet_index][0] * 512);
      ledcWrite(SWEET_SPOT_CENTER_CHANNEL, sweet_order[sweet_index][1] * 512);
      ledcWrite(SWEET_SPOT_RIGHT_CHANNEL,  sweet_order[sweet_index][2] * 512);
#endif
    }
    else {
      leds_16[NATIVE_RESOLUTION-1-led_index] = {0, 0.25, 0};
#if K1_HAS_SWEET_SPOT_LEDS
      ledcWrite(SWEET_SPOT_LEFT_CHANNEL,   sweet_order[sweet_index][2] * 4095);
      ledcWrite(SWEET_SPOT_CENTER_CHANNEL, sweet_order[sweet_index][1] * 4095);
      ledcWrite(SWEET_SPOT_RIGHT_CHANNEL,  sweet_order[sweet_index][0] * 4095);
#endif
    }


    show_leds();

    if(led_index == 0 || led_index == NATIVE_RESOLUTION/2){
      sweet_index++;
      if (sweet_index >= 3) {
        sweet_index = 0;
      }
    }

    led_index++;
    if (led_index >= NATIVE_RESOLUTION) {
      led_index = 0;      
    }
    yield();
  }
}
#endif

void init_usb() {
#if K1_USB_CUSTOM_DESCRIPTORS
  USB.productName("SpectraSynq SB");
  USB.manufacturerName("SpectraSynq");
  USB.VID(0x1209); // This works though, god damn I hate USB
  USB.PID(0xABED); // Cool, cool cool cool https://pid.codes/1209/ABED/
#endif

#if defined(K1_HARDWARE)
  USBSerial.setTxBufferSize(4096);
  USBSerial.setTxTimeoutMs(20);
  USBSerial.begin(SERIAL_BAUD);
#else
  USB.begin();
  USBSerial.begin();
#endif
}

void init_sweet_spot() {
#if K1_HAS_SWEET_SPOT_LEDS
  ledcSetup(SWEET_SPOT_LEFT_CHANNEL, 500, 12);
  ledcAttachPin(SWEET_SPOT_LEFT_PIN, SWEET_SPOT_LEFT_CHANNEL);

  ledcSetup(SWEET_SPOT_CENTER_CHANNEL, 500, 12);
  ledcAttachPin(SWEET_SPOT_CENTER_PIN, SWEET_SPOT_CENTER_CHANNEL);

  ledcSetup(SWEET_SPOT_RIGHT_CHANNEL, 500, 12);
  ledcAttachPin(SWEET_SPOT_RIGHT_PIN, SWEET_SPOT_RIGHT_CHANNEL);
#endif
}

void generate_a_weights() {
  start_timing("GENERATING A-WEIGHTS");
  for (uint8_t i = 0; i < 13; i++) {
    float decibels = a_weight_table[i][1];
    float bels = decibels / 10.0;
    float ratio = pow(10, bels);
    a_weight_table[i][1] = ratio;
  }

  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    float frequency = notes[i];
    uint8_t low_index = 0;
    uint8_t high_index = 0;
    for (uint8_t x = 0; x < 13; x++) {
      float table_freq = a_weight_table[x][0];
      if (frequency >= table_freq) {
        low_index = x;
        high_index = x + 1;
      }
    }

    float low_freq = a_weight_table[low_index][0];
    float high_freq = a_weight_table[high_index][0];

    float freq_position = (frequency - low_freq) / (high_freq - low_freq);

    float interpolated_weight = (a_weight_table[low_index][1] * (1.0 - freq_position)) + (a_weight_table[high_index][1] * (freq_position));

    frequencies[i].a_weighting_ratio = interpolated_weight;
    if (frequencies[i].a_weighting_ratio > 1.0) {
      frequencies[i].a_weighting_ratio = 1.0;
    }
  }
  end_timing();
}

void generate_window_lookup() {
  start_timing("GENERATING HANN WINDOW LOOKUP TABLE");
  // Correct, normalised Hann (coherent gain 0.5), single source of truth shared
  // with the gated GDFT spectral-window path and the host tests via
  // k1_hann_window_gain(). The previous 0.54*(1-cos) raised-cosine peaked at
  // 1.08 and OVERFLOWED int16 at the centre (32767 * 1.08 wraps); it was also
  // dead code (window_lookup was never read by the Goertzel loop), so fixing it
  // has no production effect with K1_SPECTRAL_WINDOW_V1 off.
  for (uint16_t i = 0; i < 4096; i++) {
    window_lookup[i] = (int16_t)lroundf(32767.0f * k1_hann_window_gain(i, 4096));
  }
  end_timing();
}

void precompute_goertzel_constants() {
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    int16_t n = i;
    frequencies[i].target_freq = notes[n + CONFIG.NOTE_OFFSET];

    float neighbor_left;
    float neighbor_right;

    if (i == 0) {
      neighbor_left = notes[n + CONFIG.NOTE_OFFSET];
      neighbor_right = notes[n + CONFIG.NOTE_OFFSET + 1];
    } else if (i == NUM_FREQS - 1) {
      neighbor_left = notes[n + CONFIG.NOTE_OFFSET - 1];
      neighbor_right = notes[n + CONFIG.NOTE_OFFSET];
    } else {
      neighbor_left = notes[n + CONFIG.NOTE_OFFSET - 1];
      neighbor_right = notes[n + CONFIG.NOTE_OFFSET + 1];
    }

    float neighbor_left_distance_hz = fabs(neighbor_left - frequencies[i].target_freq);
    float neighbor_right_distance_hz = fabs(neighbor_right - frequencies[i].target_freq);
    float max_distance_hz = 0;
    if (neighbor_left_distance_hz > max_distance_hz) {
      max_distance_hz = neighbor_left_distance_hz;
    }
    if (neighbor_right_distance_hz > max_distance_hz) {
      max_distance_hz = neighbor_right_distance_hz;
    }

    frequencies[i].block_size = CONFIG.SAMPLE_RATE / (max_distance_hz * 2.0);

    if(frequencies[i].block_size > 2000){
        frequencies[i].block_size = 2000;
    }

    // Calculate the inverse for optimization
    if (frequencies[i].block_size > 0) {
        frequencies[i].inv_block_size_half = 2.0 / frequencies[i].block_size; // Equivalent to 1.0 / (block_size / 2.0)
    } else {
        frequencies[i].inv_block_size_half = 0.0; // Avoid division by zero
    }

    frequencies[i].block_size_recip = 1.0 / float(frequencies[i].block_size);

#if K1_GDFT_TRUE_CENTER_V1
    // True-centre: representable bins resonate at the EXACT note frequency via the
    // generalized (non-integer-k) Goertzel. Magnitude q2*q2 + q1*q1 - coeff*q1*q2
    // stays valid for any real coeff in (-2, 2). Above Nyquist the note is not
    // physically representable (its raw centre folds), so keep rounded-k there —
    // un-rounding would not create real >Nyquist sensitivity. A/B flag only.
    if (frequencies[i].target_freq <= CONFIG.SAMPLE_RATE * 0.5f) {
      float w = (2.0 * PI * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE;
      frequencies[i].coeff_q14 = (1 << 14) * (2.0 * cos(w));
    } else {
      float k = (int)(0.5 + ((frequencies[i].block_size * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE));
      float w = (2.0 * PI * k) / frequencies[i].block_size;
      frequencies[i].coeff_q14 = (1 << 14) * (2.0 * cos(w));
    }
#else
    float k = (int)(0.5 + ((frequencies[i].block_size * frequencies[i].target_freq) / CONFIG.SAMPLE_RATE));
    float w = (2.0 * PI * k) / frequencies[i].block_size;
    float cosine = cos(w);
    float sine = sin(w);
    float coeff = 2.0 * cosine;
    frequencies[i].coeff_q14 = (1 << 14) * coeff;
#endif

    // Map sample n in [0, block_size) onto the shared 4096-entry Hann table so
    // the first/last block samples hit both Hann zero endpoints (index 0/4095).
    frequencies[i].window_mult = k1_hann_window_mult(frequencies[i].block_size);
    frequencies[i].zone = (i / float(NUM_FREQS)) * NUM_ZONES;
  }
}

void debug_function_timing(uint32_t t_now) {
    static uint32_t last_timing_print = t_now;

    if (t_now - last_timing_print >= 30000) {
        // Removed debug prints of function timing to avoid clutter
        // USBSerial.println("------------");
        // for (uint8_t i = 0; i < 16; i++) {
        //     USBSerial.print(i);
        //     USBSerial.print(": ");
        //     USBSerial.println(function_hits[i]);
        //     function_hits[i] = 0;
        // }
        last_timing_print = t_now;
    }
}

void set_mode_name(uint16_t index, const char* mode_name) {
  uint8_t len = strlen(mode_name);
  for (uint8_t i = 0; i < len; i++) {
    mode_names[32 * index + i] = mode_name[i];
  }
}

void enforce_compiled_audio_timing_config() {
  bool repaired = false;
  if (CONFIG.SAMPLE_RATE != DEFAULT_SAMPLE_RATE) {
    USBSerial.print("TIMING_CONFIG_GUARD: rejected persisted sample_rate=");
    USBSerial.print(CONFIG.SAMPLE_RATE);
    USBSerial.print(" -> ");
    USBSerial.println(DEFAULT_SAMPLE_RATE);
    CONFIG.SAMPLE_RATE = DEFAULT_SAMPLE_RATE;
    repaired = true;
  }
  if (CONFIG.SAMPLES_PER_CHUNK != DEFAULT_SAMPLES_PER_CHUNK) {
    USBSerial.print("TIMING_CONFIG_GUARD: rejected persisted samples_per_chunk=");
    USBSerial.print(CONFIG.SAMPLES_PER_CHUNK);
    USBSerial.print(" -> ");
    USBSerial.println(DEFAULT_SAMPLES_PER_CHUNK);
    CONFIG.SAMPLES_PER_CHUNK = DEFAULT_SAMPLES_PER_CHUNK;
    repaired = true;
  }
  if (repaired) {
    USBSerial.print("TIMING_CONFIG_GUARD: compiled_map sample_rate=");
    USBSerial.print(DEFAULT_SAMPLE_RATE);
    USBSerial.print(" samples_per_chunk=");
    USBSerial.print(DEFAULT_SAMPLES_PER_CHUNK);
    USBSerial.print(" tempo_decimation=");
    USBSerial.println((uint16_t)K1_TEMPO_NOVELTY_DECIMATION);
    save_config();
  }
}

void init_system() {
  noise_button.pin = NOISE_CAL_PIN;
  mode_button.pin = MODE_PIN;

#if defined(K1_HARDWARE)
  init_usb();
#endif

#if NOISE_CAL_PIN >= 0
  pinMode(noise_button.pin, INPUT_PULLUP);
#endif
#if MODE_PIN >= 0
  pinMode(mode_button.pin, INPUT_PULLUP);
#endif

  memcpy(&CONFIG_DEFAULTS, &CONFIG, sizeof(CONFIG)); // Copy defaults values to second CONFIG object

  set_mode_name(0, "GDFT");
  set_mode_name(1, "CHROMAGRAM");
  set_mode_name(2, "CHROMAGRAM DOTS");
  set_mode_name(3, "BLOOM");
  set_mode_name(4, "VU DOT");
  set_mode_name(5, "KALEIDOSCOPE");
  set_mode_name(6, "QUANTUM COLLAPSE");
  set_mode_name(7, "WAVEFORM-FAST");
  set_mode_name(8, "WAVEFORM");
  set_mode_name(9, "BLOOM (FAST)");
  set_mode_name(10, "VU");
  set_mode_name(11, "WAVEFORM_HYBRID");
  set_mode_name(12, "AURORA");
  set_mode_name(13, "COMET");
  set_mode_name(14, "SPECTRUM RIVER");
  set_mode_name(15, "SPECTRUM RIVER 2");
  set_mode_name(16, "EMBER FIELD");
  set_mode_name(17, "EMBER FIELD 2");
  set_mode_name(18, "WAVEFORM TEMPO");
  set_mode_name(19, "TEMPO RIVER");
  set_mode_name(20, "TEMPO COMET");
  set_mode_name(21, "DENSE FORGE");
  set_mode_name(22, "SNAPWAVE");
  set_mode_name(23, "PULSE PRISM");
  set_mode_name(24, "DENSE FORGE CHORD");
  set_mode_name(25, "CHROMA CONSTELLATION");
  set_mode_name(26, "PERCUSSION BURST");
  set_mode_name(27, "TEMPO COMET ANTICIPATE");
  set_mode_name(28, "RIVER SURGE");
  set_mode_name(29, "TEMPO RIVER WALK");
  set_mode_name(30, "BEAT PULSE");
  set_mode_name(31, "BLOOM BASSTREBLE");
  set_mode_name(32, "WAVEFORM HYBRID K1");
  set_mode_name(33, "MOIRE CATHEDRAL");
  set_mode_name(34, "CANNONADE");
  set_mode_name(35, "SHOCKWAVE");
  set_mode_name(36, "IRIS");
  set_mode_name(37, "MELODIC BLOOM");

  init_serial(SERIAL_BAUD);
  init_sweet_spot();
  
  init_fs();
  // PDM adjacency (load-bearing): init_fs() can transiently mark the STALE SPH cal
  // valid (load_calibration_profile_if_config_invalid refreshes with CONFIG/PERSISTED
  // source) until the K1_MIC_IM73D_PDM_V1 force-invalidate below scrubs it. Do NOT
  // insert any calibration consumer between init_fs() and that block.
  CONFIG.LED_COUNT = LED_COUNT_VALUE;  // Force compile-time LED count to win over any stale saved config
#ifdef K1_CUSTOM_LED_V1
  // Dual-214 wall build: Captain-locked 2.5 A total PSU budget. Force over any
  // persisted CONFIG.MAX_CURRENT_MA so a prior 1500 mA product save cannot leave
  // FastLED's power limiter undersized (or a stale higher value over-budget).
  CONFIG.MAX_CURRENT_MA = 2500;
#endif
  enforce_compiled_audio_timing_config();

#ifdef K1_MIC_IM73D_PDM_V1
  // IM73D PDM boot force-invalidate (bench eval, 2026-07-02). A stale SPH0645 profile
  // (DC≈-4714, SSL≈350) is IN-range and would otherwise be applied to the PDM signal
  // (wrong DC bias + wrong domain). Force RAM cal invalid on EVERY PDM boot, BEFORE the
  // two sanity blocks below — seeding a PDM-domain SSL (never 0) and a non-zero follower
  // so the peak-scaled division can never be 0/0. Persistence under the flag is
  // PDM-namespaced (bridge_fs.h): /CONFIG_PDM_*.BIN + /cal_profile_pdm.bin; the SPH
  // files stay frozen. Config cal fields loaded by init_fs() are scrubbed here
  // regardless — the PDM cal profile below is the sole cal authority.
  CONFIG.DC_OFFSET = 0;                                          // legal-invalid for PDM (HPF, DC≈0)
  CONFIG.SWEET_SPOT_MIN_LEVEL = NOISE_CAL_SSL_BOOT_FALLBACK_RAW; // PDM domain (120); NEVER 0
  CONFIG.VU_LEVEL_FLOOR = 0.0f;
  CONFIG.STANDBY_DIMMING = false;                               // else silent_scale*0 blanks the plate
  for (uint8_t i = 0; i < NUM_FREQS; i++) noise_samples[i] = 0;
  calibration_profile_loaded = false;
  calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
  max_waveform_val = 0.0f;
  max_waveform_val_raw = 0.0f;
  waveform_peak_scaled = 0.0f;
  max_waveform_val_follower = (float)CONFIG.SWEET_SPOT_MIN_LEVEL;  // seed the division denominator

  // PDM cal persistence (2026-07-03): the scrub above removed every trace of the
  // SPH-file-derived state; now restore the LAST ACCEPTED PDM cal from
  // /cal_profile_pdm.bin (CAL_PROFILE_FILE under this flag — never an SPH file).
  // The loader only reads when the RAM config is invalid, so drop SSL to the
  // invalid sentinel first; on any miss/corruption restore the fallback seed.
  CONFIG.SWEET_SPOT_MIN_LEVEL = 0;
  if (load_calibration_profile_if_config_invalid()) {
    max_waveform_val_follower = (float)CONFIG.SWEET_SPOT_MIN_LEVEL;  // persisted SSL (cal_valid=1, source=persisted_profile)
  } else {
    CONFIG.SWEET_SPOT_MIN_LEVEL = NOISE_CAL_SSL_BOOT_FALLBACK_RAW;   // no/invalid profile -> fallback, NEVER 0
    max_waveform_val_follower = (float)CONFIG.SWEET_SPOT_MIN_LEVEL;
    calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
  }
#endif

  // Fix-D Layer 1 (2026-05-24) — DC_OFFSET sanity clamp at boot.
  //
  // Two failure modes covered by one guard:
  //   (a) CONFIG.DC_OFFSET == 0       — sentinel meaning "never calibrated"
  //                                      (fresh flash, post-restore_defaults,
  //                                      or post-start_noise_cal-that-refused-
  //                                      to-update per Layer 2).
  //   (b) abs(CONFIG.DC_OFFSET) > NOISE_CAL_DC_MAX_VALID_ABS — outside the
  //       supported MEMS DC-bias band for this signal chain. Treat it as a
  //       rail-pinned calibration artefact, contaminated calibration window, or
  //       flash corruption.
  //
  // Either case: invalidate the runtime profile and prevent the value being
  // reported as a trusted calibration. The next successful noise_cal will save
  // a measured profile; until then cal_valid remains false.
#ifndef K1_MIC_IM73D_PDM_V1
  if (CONFIG.DC_OFFSET == 0 || calibration_abs_i32(CONFIG.DC_OFFSET) > NOISE_CAL_DC_MAX_VALID_ABS) {
#else
  // PDM: DC==0 is legal (HPF), so it must NOT re-trigger this wipe (which would zero SSL).
  // Only a truly out-of-band |DC| is an artefact here. The force-invalidate above already
  // set DC=0, so this stays inert on a clean PDM boot.
  if (calibration_abs_i32(CONFIG.DC_OFFSET) > NOISE_CAL_DC_MAX_VALID_ABS) {
#endif
    USBSerial.print("DC_OFFSET sanity clamp: stored value ");
    USBSerial.print(CONFIG.DC_OFFSET);
    USBSerial.println(" rejected -> calibration invalidated; run `start_noise_cal` under confirmed silence to learn the true bias.");
    CONFIG.DC_OFFSET = 0;
    CONFIG.SWEET_SPOT_MIN_LEVEL = 0;
    CONFIG.VU_LEVEL_FLOOR = 0.0f;
    for (uint8_t i = 0; i < NUM_FREQS; i++) {
      noise_samples[i] = 0;
    }
    calibration_profile_loaded = false;
    calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
    save_config();
    save_ambient_noise_calibration();
    clear_calibration_profile();
  }

  // Sanity-clamp SWEET_SPOT_MIN_LEVEL: prior broken or contaminated noise-cal
  // runs persisted SSL too high, jamming max_waveform_val_follower at an
  // inflated floor and starving WAVEFORM-family AP drive. AC-units SSL should
  // stay inside the shared validity band. If loaded value is out of range,
  // drop to a degraded fallback and mark the calibration invalid instead of
  // pretending a default value is measured room truth.
  if (CONFIG.SWEET_SPOT_MIN_LEVEL < NOISE_CAL_SSL_MIN_VALID_RAW ||
      CONFIG.SWEET_SPOT_MIN_LEVEL > NOISE_CAL_SSL_MAX_VALID_RAW) {
    USBSerial.print("SSL sanity reset: was ");
    USBSerial.print(CONFIG.SWEET_SPOT_MIN_LEVEL);
    USBSerial.print(" -> ");
    CONFIG.SWEET_SPOT_MIN_LEVEL = NOISE_CAL_SSL_BOOT_FALLBACK_RAW;
    USBSerial.println(CONFIG.SWEET_SPOT_MIN_LEVEL);
    CONFIG.DC_OFFSET = 0;
    CONFIG.VU_LEVEL_FLOOR = 0.0f;
    // Same broken cal sequence that inflates SSL also leaves STANDBY_DIMMING=true persisted —
    // force OFF so silent_scale stays at 1.0 (otherwise apply_brightness multiplies every pixel by 0).
    CONFIG.STANDBY_DIMMING = false;
    USBSerial.println("STANDBY_DIMMING force-disabled (broken-cal corruption detected)");
    // Also wipe persisted noise floor — if cal was bad, the 1.5x oversubtraction in GDFT.h
    // would kill the spectrogram and zero out chromagram → no audio reactivity in any mode.
    for (uint8_t i = 0; i < NUM_FREQS; i++) {
      noise_samples[i] = 0;
    }
    USBSerial.println("noise_samples[] cleared (suspected over-cal contamination)");
    calibration_profile_loaded = false;
    calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
    save_config();
    save_ambient_noise_calibration();
    clear_calibration_profile();
  }
  calibration_refresh_status(calibration_source);

  // NOISE and MODE held down on boot
#if NOISE_CAL_PIN >= 0 && MODE_PIN >= 0
  if (digitalRead(noise_button.pin) == LOW && digitalRead(mode_button.pin) == LOW) {
    restore_defaults();
  }
#endif

  init_leds();
#if !defined(K1_HARDWARE)
  init_usb();
#endif

  // MODE held down on boot
#if K1_ENABLE_USB_MSC_UPDATE && MODE_PIN >= 0
  if (digitalRead(mode_button.pin) == LOW) {
    enable_usb_update_mode();
  }
#endif

  init_i2s();
  generate_a_weights();
  generate_window_lookup();
  precompute_goertzel_constants();
  init_cochlear_agc();

  USBSerial.println("SYSTEM INIT COMPLETE!");

  // Boot intro runs from setup() after both LED channels are registered.
}

void log_fps(uint32_t t_now_us) {
  static uint32_t t_last = t_now_us;
  static float fps_history[10] = {0};
  static uint8_t fps_history_index = 0;

  uint32_t frame_delta_us = t_now_us - t_last;
  float fps_now = 1000000.0 / float(frame_delta_us);

  fps_history[fps_history_index] = fps_now;

  fps_history_index++;
  if (fps_history_index >= 10) {
    fps_history_index = 0;
  }

  float fps_sum = 0;
  for (uint8_t i = 0; i < 10; i++) {
    fps_sum += fps_history[i];
  }

  SYSTEM_FPS = fps_sum / 10.0;

  if (stream_fps == true) {
    USBSerial.print("sbs((fps=");
    USBSerial.print(SYSTEM_FPS);
    USBSerial.println("))");
  }

  t_last = t_now_us;
}

// This is to prevent overuse of internal flash writes!
// Instead of writing every single setting change to
// LittleFS, we wait until no settings have been altered
// for more than 3 seconds before attempting to update
// the flash with changes. This helps in scenarios where
// you're rapidly cycling through modes for example.
void check_settings(uint32_t t_now) {
  if (settings_updated) {
    if (t_now >= next_save_time) {
      if(debug_mode == true){
        USBSerial.println("QUEUED CONFIG SAVE TRIGGERED");
      }
      // Clear BEFORE the save: if save_config() defers on low internal RAM it
      // re-arms settings_updated + next_save_time, and that re-arm must survive
      // this cycle so the write retries. Clearing after would cancel the retry.
      settings_updated = false;
      save_config();
    }
  }
}

void init_cochlear_agc() {
  start_timing("INITIALIZING COCHLEAR AGC");
  
  // Initialize frequency bin to AGC band mapping
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    float freq = frequencies[i].target_freq;
    
    // Determine which band this frequency belongs to
    if (freq < BAND_BASS_HIGH) {
      freq_to_band_map[i] = BAND_BASS;
    } 
    else if (freq < BAND_LOW_MID_HIGH) {
      freq_to_band_map[i] = BAND_LOW_MID;
    }
    else if (freq < BAND_HIGH_MID_HIGH) {
      freq_to_band_map[i] = BAND_HIGH_MID;
    }
    else {
      freq_to_band_map[i] = BAND_TREBLE;
    }
    
    // Debug output for bin mapping (uncomment if needed)
    /*
    if (debug_mode) {
      USBSerial.print("Freq bin ");
      USBSerial.print(i);
      USBSerial.print(" (");
      USBSerial.print(frequencies[i].target_freq);
      USBSerial.print(" Hz) mapped to band ");
      USBSerial.println(freq_to_band_map[i]);
    }
    */
  }
  
  // Initialize parameters for Bass band
  agc_bands[BAND_BASS].attack_rate = SQ15x16(1.0 / (AGC_BASS_ATTACK_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_BASS].release_rate = SQ15x16(1.0 / (AGC_BASS_RELEASE_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_BASS].gain = SQ15x16(1.0); // Start at unity gain
  agc_bands[BAND_BASS].target_gain = SQ15x16(1.0);
  agc_bands[BAND_BASS].max_gain = SQ15x16(AGC_BASS_MAX_GAIN);
  agc_bands[BAND_BASS].threshold = SQ15x16(0.1); // Initial threshold, will be adjusted dynamically
  
  // Initialize parameters for Low-Mid band
  agc_bands[BAND_LOW_MID].attack_rate = SQ15x16(1.0 / (AGC_LOW_MID_ATTACK_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_LOW_MID].release_rate = SQ15x16(1.0 / (AGC_LOW_MID_RELEASE_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_LOW_MID].gain = SQ15x16(1.0);
  agc_bands[BAND_LOW_MID].target_gain = SQ15x16(1.0);
  agc_bands[BAND_LOW_MID].max_gain = SQ15x16(AGC_LOW_MID_MAX_GAIN);
  agc_bands[BAND_LOW_MID].threshold = SQ15x16(0.15);
  
  // Initialize parameters for High-Mid band
  agc_bands[BAND_HIGH_MID].attack_rate = SQ15x16(1.0 / (AGC_HIGH_MID_ATTACK_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_HIGH_MID].release_rate = SQ15x16(1.0 / (AGC_HIGH_MID_RELEASE_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_HIGH_MID].gain = SQ15x16(1.0);
  agc_bands[BAND_HIGH_MID].target_gain = SQ15x16(1.0);
  agc_bands[BAND_HIGH_MID].max_gain = SQ15x16(AGC_HIGH_MID_MAX_GAIN);
  agc_bands[BAND_HIGH_MID].threshold = SQ15x16(0.2);
  
  // Initialize parameters for Treble band
  agc_bands[BAND_TREBLE].attack_rate = SQ15x16(1.0 / (AGC_TREBLE_ATTACK_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_TREBLE].release_rate = SQ15x16(1.0 / (AGC_TREBLE_RELEASE_RATE * CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK));
  agc_bands[BAND_TREBLE].gain = SQ15x16(1.0);
  agc_bands[BAND_TREBLE].target_gain = SQ15x16(1.0);
  agc_bands[BAND_TREBLE].max_gain = SQ15x16(AGC_TREBLE_MAX_GAIN);
  agc_bands[BAND_TREBLE].threshold = SQ15x16(0.25);
  
  // ---- Broadband AGC v2 init: spectral tilt LUT + reset envelope/gate state ----
  // Static tilt curve preserves the bass-emphasis / treble-protection intent of the old
  // per-band design WITHOUT feedback. Computed once from frequency table; no runtime cost.
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    float freq = frequencies[i].target_freq;
    float tilt;
    if (freq < 200.0f)        tilt = 1.30f;  // bass emphasis (was AGC_BASS_MAX_GAIN=8 intent)
    else if (freq > 3000.0f)  tilt = 0.85f;  // treble protection (was AGC_TREBLE_MAX_GAIN=4 intent)
    else                       tilt = 1.00f; // mids neutral
    spectral_tilt_lut[i] = SQ15x16(tilt);
  }
  agc_envelope = SQ15x16(0.0);
  agc_noise_floor = SQ15x16(0.001);
  agc_gated = true;

  if (debug_mode) {
    USBSerial.println("Broadband AGC v2 initialized (tilt LUT loaded, gate armed).");
  }

  end_timing();
}
