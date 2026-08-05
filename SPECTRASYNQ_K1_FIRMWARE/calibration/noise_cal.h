void clear_spectral_noise_samples() {
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    noise_samples[i] = 0;
  }
}

void noise_cal_snapshot_current_profile() {
  noise_cal_previous_valid = calibration_valid && calibration_profile_valid();
  noise_cal_previous_profile_loaded = calibration_profile_loaded;
  noise_cal_previous_source = calibration_source;
  noise_cal_previous_dc_offset = CONFIG.DC_OFFSET;
  noise_cal_previous_sweet_spot_min = CONFIG.SWEET_SPOT_MIN_LEVEL;
  noise_cal_previous_vu_floor = CONFIG.VU_LEVEL_FLOOR;
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    noise_cal_previous_noise_samples[i] = noise_samples[i];
  }
}

void noise_cal_restore_previous_or_invalidate() {
  if (noise_cal_previous_valid) {
    CONFIG.DC_OFFSET = noise_cal_previous_dc_offset;
    CONFIG.SWEET_SPOT_MIN_LEVEL = noise_cal_previous_sweet_spot_min;
    CONFIG.VU_LEVEL_FLOOR = noise_cal_previous_vu_floor;
    for (uint16_t i = 0; i < NUM_FREQS; i++) {
      noise_samples[i] = noise_cal_previous_noise_samples[i];
    }
    noise_complete = true;
    noise_iterations = 0;
    calibration_profile_loaded = noise_cal_previous_profile_loaded;
    calibration_refresh_status(noise_cal_previous_source);
    USBSerial.println("NOISE CAL RESTORED PREVIOUS VALID PROFILE");
    return;
  }

  CONFIG.DC_OFFSET = 0;
#ifdef K1_MIC_PDM_RX_ANY_V1
  CONFIG.SWEET_SPOT_MIN_LEVEL = NOISE_CAL_SSL_BOOT_FALLBACK_RAW;  // PDM: never 0 at runtime
#else
  CONFIG.SWEET_SPOT_MIN_LEVEL = 0;
#endif
  CONFIG.VU_LEVEL_FLOOR = 0.0f;
  clear_spectral_noise_samples();
  noise_complete = true;
  noise_iterations = 0;
  calibration_profile_loaded = false;
  calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
#ifdef K1_MIC_PDM_RX_ANY_V1
  max_waveform_val_follower = (float)CONFIG.SWEET_SPOT_MIN_LEVEL;  // seed division denominator (NaN guard)
#endif
  USBSerial.println("NOISE CAL HAS NO PREVIOUS VALID PROFILE");
}

void start_noise_cal() {
  noise_cal_snapshot_current_profile();
  noise_complete = false;
  max_waveform_val = 0;
  max_waveform_val_raw = 0;
  noise_iterations = 0;
  dc_offset_sum = 0;
  dc_offset_samples = 0;
  dc_offset_rejected_samples = 0;
  ssl_cal_samples = 0;
  ssl_cal_rejected_samples = 0;
  ssl_cal_p50_raw = 0.0f;
  ssl_cal_p90_raw = 0.0f;
  noise_cal_dc_valid = false;
  noise_cal_ssl_valid = false;
  noise_cal_reject_reason = NOISE_CAL_REJECT_NONE;
  CONFIG.DC_OFFSET = 0;
  CONFIG.VU_LEVEL_FLOOR = 0.0;
  CONFIG.SWEET_SPOT_MIN_LEVEL = 0;
  calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
  clear_spectral_noise_samples();
  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    ui_mask[i] = 0;
  }
  USBSerial.println("STARTING NOISE CAL");
}

void clear_noise_cal() {
  clear_spectral_noise_samples();
  CONFIG.DC_OFFSET = 0;
#ifdef K1_MIC_PDM_RX_ANY_V1
  CONFIG.SWEET_SPOT_MIN_LEVEL = NOISE_CAL_SSL_BOOT_FALLBACK_RAW;  // PDM: never 0 at runtime
  max_waveform_val_follower = (float)CONFIG.SWEET_SPOT_MIN_LEVEL;  // seed division denominator (NaN guard)
#else
  CONFIG.SWEET_SPOT_MIN_LEVEL = 0;
#endif
  CONFIG.VU_LEVEL_FLOOR = 0.0f;
  calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
  save_config();
  save_ambient_noise_calibration();
  clear_calibration_profile();
  USBSerial.println("NOISE CAL CLEARED");
}
