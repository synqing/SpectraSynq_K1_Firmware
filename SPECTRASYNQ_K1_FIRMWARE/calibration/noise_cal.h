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

#ifdef K1_CAL_PARTIAL_COMMIT_V1
// Re-stamp a Phase-A-validated DC over whatever the rollback just restored, and
// persist it if the resulting profile is self-consistent. Persistence matters:
// the cal profile file overwrites CONFIG.DC_OFFSET at boot (bridge_fs.h), so a
// RAM-only partial commit would be undone by the next reboot (four-way identity).
void noise_cal_commit_partial_dc(int32_t dc_value) {
  CONFIG.DC_OFFSET = dc_value;
  USBSerial.print("NOISE CAL PARTIAL: dc_committed=");
  USBSerial.print(dc_value);
  USBSerial.print(" ssl_kept=");
  USBSerial.print(CONFIG.SWEET_SPOT_MIN_LEVEL);
  USBSerial.print(" reason=");
  USBSerial.print(noise_cal_reject_reason_name(noise_cal_reject_reason));
  if (calibration_profile_valid()) {
    save_config();
    save_calibration_profile(CAL_SOURCE_MEASURED);
    calibration_refresh_status(CAL_SOURCE_MEASURED);
    USBSerial.println(" persisted=1");
  } else {
    // SSL is out of its valid band, so the profile as a whole cannot be written.
    // The DC still stands for this session; say so rather than implying a save.
    USBSerial.println(" persisted=0 (profile invalid: SSL out of band)");
  }
}
#endif

void noise_cal_restore_previous_or_invalidate() {
#ifdef K1_CAL_PARTIAL_COMMIT_V1
  // PARTIAL COMMIT (2026-08-14). A multi-quantity calibration must be able to
  // land the quantities that measured cleanly even when a sibling quantity
  // legitimately refuses, otherwise it cannot self-heal.
  //
  // DC and SSL are measured independently and in that order: start_noise_cal()
  // zeroes CONFIG.DC_OFFSET, Phase A (iters 0..127) learns the true mean from
  // that zeroed base, and the result is stamped at iter 128 BEFORE Phase B
  // samples SSL. So a Phase-B/SSL refusal says nothing about the DC's validity.
  // The all-or-nothing rollback nevertheless discarded the good DC, and the
  // runtime then kept animating on a stale DC pedestal. The room only has to be
  // quiet enough for SSL to pass, never for DC — so under a persistently noisy
  // ambient the DC could never be refreshed at all.
  //
  // Keep the freshly measured DC; restore everything else; report loudly.
  const int32_t partial_dc_value = CONFIG.DC_OFFSET;
  const bool partial_dc_commit =
      noise_cal_dc_valid && !noise_cal_ssl_valid &&
      calibration_abs_i32(partial_dc_value) <= NOISE_CAL_DC_MAX_VALID_ABS;
#endif
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
#ifdef K1_CAL_PARTIAL_COMMIT_V1
    if (partial_dc_commit) {
      noise_cal_commit_partial_dc(partial_dc_value);
    }
#endif
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
#ifdef K1_CAL_PARTIAL_COMMIT_V1
  if (partial_dc_commit) {
    noise_cal_commit_partial_dc(partial_dc_value);
  }
#endif
}

void start_noise_cal() {
#ifdef K1_MIC_HEALTH_V1
  if (!k1_mic_health_allows_calibration()) {
    const K1MicHealthContext health = k1_mic_health_read();
    USBSerial.print("NOISE CAL REFUSED: mic_health=");
    USBSerial.print(k1_mic_health_state_name(health.state));
    USBSerial.print(" reason=");
    USBSerial.println(k1_mic_health_reason_name(health.reason));
    return;
  }
#endif
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
