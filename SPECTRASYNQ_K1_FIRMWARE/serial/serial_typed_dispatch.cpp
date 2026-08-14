/*----------------------------------------
  SERIAL TYPED COMMAND DISPATCH (Stage B table handlers)
  ----------------------------------------*/
#include "serial_typed_dispatch.h"
#include "serial_cmd_handlers.h"
#include "serial_tx.h"
#include "serial_parse_helpers.h"
#include "globals.h"
#include "constants.h"
#include "led_utilities.h"
#include "k1_smart_director.h"
#include "k1_effect_queue.h"
#include "k1_show_state.h"
#include "k1_edgemixer.h"
#include "k1_ap_capture_telemetry.h"
#if ENABLE_DIAG_CAPTURE
#include "diagnostic_capture.h"
#endif
#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"
#endif
#if K1_PIN_EVIDENCE_V1
#include "k1_pin_evidence.h"
#endif
#if ENABLE_VP_MOTION_LAB
#include "vp_motion_lab.h"
#endif
#if K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h"
#endif
#ifdef K1_MIC_IM69D_STEREO_V1
#include "k1_stereo_probe.h"
#endif
#ifdef K1_RENDER_TRACE_V1
#include "k1_render_trace.h"
#endif
#ifdef K1_MIC_HEALTH_V1
#include "k1_mic_health.h"
#endif
#ifdef K1_AP_TWITCH_ORACLE_V1
#include "k1_ap_twitch_oracle.h"
#endif

#include <string.h>
#include <stdlib.h>
#include <math.h>

extern void check_current_function();
extern void reboot();
extern void save_config();
extern void save_config_delayed();
extern void serial_queue_slot_save(uint8_t slot, bool from_secondary);
extern void serial_queue_slot_load(uint8_t slot, bool target_secondary);
extern void serial_queue_slot_arm(uint8_t slot, bool target_secondary);
extern void vp_print_status();
extern void vp_run_output_probe();
extern void vp_run_secondary_bleed_probe();
extern void vp_perf_command(const char* command_type, const char* command_data);
extern void motion_probe_arm_step(float interval_ms, int size_px, float lum);
extern void motion_probe_arm_flash(int a_px, int b_px, float gap_ms, float lum, float on_ms);
extern void motion_probe_off();
extern void motion_probe_status();
extern void ap_capture_arm(uint32_t ms);
extern void serial_print_k1_loud_guard_status();
extern void serial_cycle_k1_loud_guard_mode();
extern void serial_set_k1_loud_guard(bool value);
extern const char* serial_mode_name(uint8_t mode);
extern char mode_names[];
extern uint8_t light_mode_next_enabled(uint8_t mode, int dir);
extern bool benchmark_running;
extern uint32_t benchmark_start_time;
extern uint32_t system_fps_sum;
extern uint32_t led_fps_sum;
extern uint32_t benchmark_sample_count;
extern const uint32_t benchmark_duration;
extern bool stream_spectrogram;
extern bool stream_chromagram;
extern bool stream_agc_debug;
extern void vp_apply_profile(uint8_t profile);
extern const char* vp_bool_text(bool value);
extern uint8_t raw_dump_request;
#if ENABLE_VPAB_PROBE
extern void vpab_command(const char* command_type, const char* command_data);
#endif


// ---- dispatcher family wrappers ----
bool serial_typed_wrap_pure_setter(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_pure_setter(command_type, command_data);
}
bool serial_typed_wrap_reboot_setter(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_reboot_setter(command_type, command_data);
}
bool serial_typed_wrap_vp_tuning(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_vp_tuning(command_type, command_data);
}
bool serial_typed_wrap_response_gain(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_response_gain(command_type, command_data);
}
bool serial_typed_wrap_queue(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_queue(command_type, command_data);
}
bool serial_typed_wrap_smart_director(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_smart_director(command_type, command_data);
}
bool serial_typed_wrap_smart_visual(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_smart_visual(command_type, command_data);
}
bool serial_typed_wrap_edge_mixer(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_edge_mixer(command_type, command_data);
}
bool serial_typed_wrap_preset(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_preset(command_type, command_data);
}
bool serial_typed_wrap_secondary(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_secondary(command_type, command_data);
}
bool serial_typed_wrap_mode(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_mode(command_type, command_data);
}
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
bool serial_typed_wrap_ap_diag(const char* command_type, char* command_data) {
  return serial_diag_ap_dispatch(command_type, command_data);
}
#endif
#if K1_VIVID_PRECOMP_V1
bool serial_typed_wrap_vivid(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_vivid(command_type, command_data);
}
#endif
#if ENABLE_GDFT_HARNESS
bool serial_typed_wrap_gdft_harness(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_gdft_harness(command_type, command_data);
}
#endif
#ifdef K1_MIC_IM69D_STEREO_V1
bool serial_typed_wrap_stereo_probe(const char* command_type, char* command_data) {
  return k1_stereo_probe_dispatch(command_type, command_data);
}
#endif
#ifdef K1_RENDER_TRACE_V1
bool serial_typed_wrap_render_trace(const char* command_type, char* command_data) {
  return k1_render_trace_dispatch(command_type, command_data);
}
#endif
#if K1_EFFECT_FRAMEWORK_V1
bool serial_typed_wrap_beat_director(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_beat_director(command_type, command_data);
}
#endif

bool serial_typed_vp_profile(const char* command_type, char* command_data) {
  if (strcmp(command_data, "original") == 0) {
        vp_apply_profile(VP_PROFILE_ORIGINAL);
        vp_print_status();
      } else if (strcmp(command_data, "clean") == 0) {
        vp_apply_profile(VP_PROFILE_CLEAN);
        vp_print_status();
      } else if (strcmp(command_data, "candidate") == 0) {
        vp_apply_profile(VP_PROFILE_CANDIDATE);
        vp_print_status();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}

bool serial_typed_vp_all(const char* command_type, char* command_data) {
  bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        vp_apply_profile(value ? VP_PROFILE_CANDIDATE : VP_PROFILE_ORIGINAL);
        vp_print_status();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}

bool serial_typed_ap_stream(const char* command_type, char* command_data) {
  bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        AP_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("AP_STREAM: ");
        USBSerial.println(vp_bool_text(AP_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}

#ifdef K1_MIC_HEALTH_V1
static void serial_print_mic_health() {
  const K1MicHealthContext health = k1_mic_health_read();
  tx_begin();
  USBSerial.print("MIC_HEALTH state=");
  USBSerial.print(k1_mic_health_state_name(health.state));
  USBSerial.print(" reason=");
  USBSerial.print(k1_mic_health_reason_name(health.reason));
  USBSerial.print(" liveness=");
  USBSerial.print(health.liveness_proven ? 1 : 0);
  USBSerial.print(" challenge=");
  USBSerial.print(health.challenge_active ? 1 : 0);
  USBSerial.print(" inject=");
  USBSerial.print(k1_mic_health_injection_name(health.injection));
  USBSerial.print(" epoch=");
  USBSerial.print(health.epoch);
  USBSerial.print(" frames=");
  USBSerial.print(health.frame_count);
  USBSerial.print(" raw_peak_i16=");
  USBSerial.print(health.last_raw_peak_i16);
  USBSerial.print(" raw_rms_i16=");
  USBSerial.print(health.last_raw_rms_i16, 2);
  USBSerial.print(" challenge_baseline_peak_i16=");
  USBSerial.print(health.challenge_baseline_peak_i16);
  USBSerial.print(" challenge_baseline_rms_i16=");
  USBSerial.println(health.challenge_baseline_rms_i16, 2);
  tx_end();
}

bool serial_typed_mic_health(const char* command_type, char* command_data) {
  const char* value = command_data == nullptr ? "" : command_data;
  if (value[0] == '\0' || strcmp(value, "status") == 0) {
    serial_print_mic_health();
  } else if (strcmp(value, "challenge") == 0) {
    k1_mic_health_begin_challenge(millis());
    serial_print_mic_health();
  } else if (strcmp(value, "fail_challenge") == 0) {
    k1_mic_health_fail_challenge();
    serial_print_mic_health();
  } else if (strcmp(value, "reset") == 0) {
    k1_mic_health_reset(millis());
    serial_print_mic_health();
  } else {
    bad_command(command_type, command_data);
  }
  return true;
}

#ifdef K1_MIC_HEALTH_FAULT_INJECT_V1
bool serial_typed_mic_health_fault(const char* command_type, char* command_data) {
  const char* value = command_data == nullptr ? "" : command_data;
  K1MicHealthFaultInjection injection = K1_MIC_INJECT_NONE;
  bool valid = true;
  if (strcmp(value, "none") == 0) {
    injection = K1_MIC_INJECT_NONE;
  } else if (strcmp(value, "stale") == 0) {
    injection = K1_MIC_INJECT_STALE_I2S;
  } else if (strcmp(value, "repeat") == 0) {
    injection = K1_MIC_INJECT_REPEATED_BUFFER;
  } else if (strcmp(value, "constant") == 0) {
    injection = K1_MIC_INJECT_CONSTANT_BUFFER;
  } else if (strcmp(value, "rail") == 0) {
    injection = K1_MIC_INJECT_RAIL_LOCK;
  } else {
    valid = false;
  }
  if (!valid) {
    bad_command(command_type, command_data);
    return true;
  }
  k1_mic_health_set_fault_injection(injection);
  serial_print_mic_health();
  return true;
}
#endif
#endif

#ifdef K1_AP_TWITCH_ORACLE_V1
bool serial_typed_ap_twitch(const char* command_type, char* command_data) {
  const char* value = command_data == nullptr ? "" : command_data;
  if (value[0] == '\0' || strcmp(value, "status") == 0) {
    tx_begin();
    k1_ap_twitch_oracle_print_status();
    tx_end();
    return true;
  }
  if (strcmp(value, "reset") == 0) {
    k1_ap_twitch_oracle_reset();
    tx_begin();
    k1_ap_twitch_oracle_print_status();
    tx_end();
    return true;
  }
  unsigned long duration_value = 0UL;
  unsigned long warmup_value = 30UL;
  if (sscanf(value, "start,%lu,%lu", &duration_value, &warmup_value) >= 1 &&
      duration_value >= 1000UL && duration_value <= 60000UL && warmup_value <= 1000UL) {
    k1_ap_twitch_oracle_start(millis(), uint32_t(duration_value), uint32_t(warmup_value));
    tx_begin();
    k1_ap_twitch_oracle_print_status();
    tx_end();
    return true;
  }
  bad_command(command_type, command_data);
  return true;
}
#endif

#if ENABLE_TEMPO_STREAM
bool serial_typed_tempo_stream(const char* command_type, char* command_data) {
  bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        TEMPO_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("TEMPO_STREAM: ");
        USBSerial.println(vp_bool_text(TEMPO_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_AP_STREAM
bool serial_typed_ap_capture(const char* command_type, char* command_data) {
  long ms = (command_data && command_data[0]) ? atol(command_data) : 0;
      if (ms > 0 && ms <= 60000) {
        ap_capture_arm((uint32_t)ms);
        tx_begin();
        USBSerial.print("AP_CAPTURE: armed ");
        USBSerial.print(ms);
        USBSerial.println(" ms");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_FRAME_DUMP
bool serial_typed_frame_dump(const char* command_type, char* command_data) {
  char metric[12] = {0};
      int mode = 0; long dur = 0; int every = 1;
      int parsed = (command_data && command_data[0])
                     ? sscanf(command_data, "%11[^,],%d,%ld,%d", metric, &mode, &dur, &every) : 0;
      if (parsed >= 3 && dur > 0 && dur <= 60000 && mode >= 0 && mode < NUM_MODES) {
        if (every < 1) every = 1;
        frame_dump_every_n = (uint16_t)every;
        frame_dump_frame = 0;
        frame_dump_end_ms = millis() + (uint32_t)dur;
        frame_dump_active = true;
        tx_begin();
        USBSerial.printf("[FDUMP] start metric=%s mode=%d dur=%ld every=%d\n", metric, mode, dur, every);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_VP_PROBE_CMD
bool serial_typed_vp_probe(const char* command_type, char* command_data) {
  if (command_data && strcmp(command_data, "all") == 0) {
        vp_run_output_probe();
      } else if (command_data && strcmp(command_data, "secondary") == 0) {
        vp_run_secondary_bleed_probe();   // item 17 — secondary bleed test (VPB)
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_MOTION_PROBE
bool serial_typed_mp_step(const char* command_type, char* command_data) {
  if (command_data && command_data[0] != '\0') {
        char buf[64];
        strncpy(buf, command_data, sizeof(buf) - 1);
        buf[sizeof(buf) - 1] = '\0';
        char* tok_iv  = strtok(buf, ",");
        char* tok_sz  = strtok(nullptr, ",");
        char* tok_lum = strtok(nullptr, ",");   // optional luminance 0..255
        if (tok_iv && tok_sz) {
          float interval_ms = strtof(tok_iv, nullptr);
          int   size_px     = atoi(tok_sz);
          float lum         = 1.0f;             // default full brightness
          if (tok_lum) {
            int l = atoi(tok_lum);
            if (l < 0) l = 0; if (l > 255) l = 255;
            lum = (float)l / 255.0f;
          }
          if (isfinite(interval_ms) && interval_ms > 0.0f && size_px >= 1) {
            motion_probe_arm_step(interval_ms, size_px, lum);
          } else {
            bad_command(command_type, command_data);
          }
        } else {
          bad_command(command_type, command_data);
        }
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_MOTION_PROBE
bool serial_typed_mp_flash(const char* command_type, char* command_data) {
  if (command_data && command_data[0] != '\0') {
        char buf[64];
        strncpy(buf, command_data, sizeof(buf) - 1);
        buf[sizeof(buf) - 1] = '\0';
        char* tok_a   = strtok(buf, ",");
        char* tok_b   = strtok(nullptr, ",");
        char* tok_gap = strtok(nullptr, ",");
        char* tok_lum = strtok(nullptr, ",");
        char* tok_on  = strtok(nullptr, ",");
        if (tok_a && tok_b && tok_gap && tok_lum && tok_on) {
          int   a_px   = atoi(tok_a);
          int   b_px   = atoi(tok_b);
          float gap_ms = strtof(tok_gap, nullptr);
          int   lum_i  = atoi(tok_lum);
          float on_ms  = strtof(tok_on, nullptr);
          if (lum_i < 0) lum_i = 0; if (lum_i > 255) lum_i = 255;
          float lum = (float)lum_i / 255.0f;
          if (isfinite(gap_ms) && isfinite(on_ms) && gap_ms >= 0.0f && on_ms > 0.0f
              && a_px >= 0 && b_px >= 0) {
            motion_probe_arm_flash(a_px, b_px, gap_ms, lum, on_ms);
          } else {
            bad_command(command_type, command_data);
          }
        } else {
          bad_command(command_type, command_data);
        }
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_MOTION_PROBE
bool serial_typed_mp_off(const char* command_type, char* command_data) {
  motion_probe_off();
  return true;
}
#endif

#if ENABLE_MOTION_PROBE
bool serial_typed_mp_status(const char* command_type, char* command_data) {
  motion_probe_status();
  return true;
}
#endif

bool serial_typed_dump_raw(const char* command_type, char* command_data) {
  if (strcmp(command_data, "silence") == 0) {
        raw_dump_request = 1;
        tx_begin();
        USBSerial.println("DUMP_RAW: armed (silence)");
        tx_end();
      } else if (strcmp(command_data, "tone") == 0) {
        raw_dump_request = 2;
        tx_begin();
        USBSerial.println("DUMP_RAW: armed (tone-1kHz)");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}

bool serial_typed_vp_stream(const char* command_type, char* command_data) {
  bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        VP_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("VP_STREAM: ");
        USBSerial.println(vp_bool_text(VP_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}

bool serial_typed_ble_stream(const char* command_type, char* command_data) {
  bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        BLE_STREAM_ENABLED = value;
        tx_begin();
        USBSerial.print("BLE_STREAM: ");
        USBSerial.println(vp_bool_text(BLE_STREAM_ENABLED));
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}

bool serial_typed_vp_perf(const char* command_type, char* command_data) {
  vp_perf_command(command_type, command_data);
  return true;
}

#if ENABLE_DIAG_CAPTURE
bool serial_typed_diag(const char* command_type, char* command_data) {
  if (strcmp(command_data, "status") == 0 || command_data[0] == 0) {
        diag_capture_print_status();
      } else if (strcmp(command_data, "clear") == 0 || strcmp(command_data, "reset") == 0) {
        diag_capture_reset();
        diag_capture_print_status();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_VPAB_PROBE
bool serial_typed_vpab(const char* command_type, char* command_data) {
  vpab_command(command_type, command_data);
  return true;
}
#endif

#if K1_PIN_EVIDENCE_V1
bool serial_typed_k1_pin_evidence(const char* command_type, char* command_data) {
  if (command_data == nullptr || command_data[0] == 0 || strcmp(command_data, "status") == 0) {
        k1_pin_evidence_print_status();
      } else if (strncmp(command_data, "dba,", 4) == 0) {
        if (k1_pin_evidence_set_dba_bucket_name(command_data + 4)) {
          k1_pin_evidence_print_status();
        } else {
          bad_command(command_type, command_data);
        }
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

#if ENABLE_VP_MOTION_LAB
bool serial_typed_vpml(const char* command_type, char* command_data) {
  if (!vpml_command(command_type, command_data)) {
        bad_command(command_type, command_data);
      }
  return true;
}
#endif

bool serial_typed_debug(const char* command_type, char* command_data) {
  bool good = false;
      if (strcmp(command_data, "true") == 0) {
        good = true;
        debug_mode = true;
        cpu_usage.attach_ms(5, check_current_function);
      } else if (strcmp(command_data, "false") == 0) {
        good = true;
        debug_mode = false;
        cpu_usage.detach();
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        tx_begin();
        USBSerial.print("debug_mode: ");
        USBSerial.println(debug_mode);
        tx_end();
      }
  return true;
}

bool serial_typed_get_mode_name(const char* command_type, char* command_data) {
  uint16_t mode_id = atol(command_data);

#ifdef K1_EFFECT_REGISTRY_V1
      // Under the registry flag the ID argument is the gap-free DENSE menu index
      // (same numbering as set_mode / the MODE line), which covers the native
      // effects. Convert it to the real runtime ordinal before the name lookup
      // (registry row → display name). Falls back to the legacy span when the
      // registry is unhealthy.
      const bool registry_ok = k1::effects::framework::registry_is_healthy();
      const uint16_t mode_id_limit = registry_ok
                                         ? k1::effects::framework::registry_dense_count()
                                         : (uint16_t)NUM_MODES;
      if (mode_id < mode_id_limit) {
        const uint16_t ordinal =
            registry_ok ? k1::effects::framework::registry_dense_to_ordinal(mode_id) : mode_id;
        char buf[32] = { 0 };
        const char* src = serial_mode_name((uint8_t)ordinal);
        for (uint8_t i = 0; i < 32; i++) {
          char c = src[i];
          if (c != 0) {
            buf[i] = c;
          } else {
            break;
          }
        }

        tx_begin();
        USBSerial.print("MODE_NAME: ");
        USBSerial.println(buf);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
#else
      if (mode_id < NUM_MODES) {
        char buf[32] = { 0 };
        for (uint8_t i = 0; i < 32; i++) {
          char c = mode_names[32 * mode_id + i];
          if (c != 0) {
            buf[i] = c;
          } else {
            break;
          }
        }

        tx_begin();
        USBSerial.print("MODE_NAME: ");
        USBSerial.println(buf);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
#endif
  return true;
}

#if K1_LOUD_GUARD_V1
bool serial_typed_k1_loud_guard(const char* command_type, char* command_data) {
  if (strcmp(command_data, "status") == 0) {
        tx_begin();
        serial_print_k1_loud_guard_status();
        tx_end();
      } else if (strcmp(command_data, "cycle") == 0) {
        tx_begin();
        serial_cycle_k1_loud_guard_mode();
        serial_print_k1_loud_guard_status();
        tx_end();
      } else if (strncmp(command_data, "mode", 4) == 0 &&
                 command_data[4] >= '0' && command_data[4] <= '2' && command_data[5] == '\0') {
        k1_loud_guard_mode = (uint8_t)(command_data[4] - '0');   // A/B retune matrix select
        tx_begin();
        serial_print_k1_loud_guard_status();
        tx_end();
      } else {
        bool value = false;
        if (vp_parse_bool(command_data, &value)) {
          serial_set_k1_loud_guard(value);
          tx_begin();
          serial_print_k1_loud_guard_status();
          tx_end();
        } else {
          bad_command(command_type, command_data);
        }
      }
  return true;
}
#endif

bool serial_typed_standby_dimming(const char* command_type, char* command_data) {
  // STRUCK 2026-08-09: not operator-selectable; reject any legacy typed call.
  (void)command_data;
  bad_command(command_type, "struck");
  return true;
}

bool serial_typed_silence_enter(const char* command_type, char* command_data) {
  SILENCE_ENTER_SSL_FRAC = (float)atof(command_data);
      tx_begin(); USBSerial.print("SILENCE_ENTER_SSL_FRAC: "); USBSerial.println(SILENCE_ENTER_SSL_FRAC, 3); tx_end();
  return true;
}

bool serial_typed_silence_exit(const char* command_type, char* command_data) {
  SILENCE_EXIT_SSL_FRAC = (float)atof(command_data);
      tx_begin(); USBSerial.print("SILENCE_EXIT_SSL_FRAC: "); USBSerial.println(SILENCE_EXIT_SSL_FRAC, 3); tx_end();
  return true;
}

bool serial_typed_silence_dwell(const char* command_type, char* command_data) {
  SILENCE_DWELL_MS = (uint32_t)atol(command_data);
      tx_begin(); USBSerial.print("SILENCE_DWELL_MS: "); USBSerial.println(SILENCE_DWELL_MS); tx_end();
  return true;
}

bool serial_typed_silence_rms_enter(const char* command_type, char* command_data) {
  K1_SILENCE_RMS_ENTER = (float)atof(command_data);
      tx_begin(); USBSerial.print("K1_SILENCE_RMS_ENTER: "); USBSerial.println(K1_SILENCE_RMS_ENTER, 3); tx_end();
  return true;
}

bool serial_typed_silence_rms_exit(const char* command_type, char* command_data) {
  K1_SILENCE_RMS_EXIT = (float)atof(command_data);
      tx_begin(); USBSerial.print("K1_SILENCE_RMS_EXIT: "); USBSerial.println(K1_SILENCE_RMS_EXIT, 3); tx_end();
  return true;
}

bool serial_typed_set_chroma_profile(const char* command_type, char* command_data) {
  bool good = false;
      uint8_t profile = CHROMA_PROFILE_DEFAULT;
      if (strcmp(command_data, "default") == 0) {
        profile = CHROMA_PROFILE_DEFAULT;
        good = true;
      } else if (strcmp(command_data, "bass") == 0) {
        profile = CHROMA_PROFILE_BASS;
        good = true;
      } else if (strcmp(command_data, "full") == 0) {
        profile = CHROMA_PROFILE_FULL;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        bool note_offset_changed = apply_chroma_profile(profile);
        save_config();
        tx_begin();
        USBSerial.print("CONFIG.CHROMA_PROFILE: ");
        USBSerial.print(command_data);
        USBSerial.print(" (NOTE_OFFSET=");
        USBSerial.print(CONFIG.NOTE_OFFSET);
        USBSerial.print(" CHROMAGRAM_RANGE=");
        USBSerial.print(CONFIG.CHROMAGRAM_RANGE);
        USBSerial.println(")");
        tx_end();
        // Reboot ONLY if NOTE_OFFSET changed — it re-seeds the GDFT freq table at
        // init. A pure CHROMAGRAM_RANGE change is picked up live each frame.
        if (note_offset_changed) {
          reboot();
        }
      }
  return true;
}

bool serial_typed_bass_mode(const char* command_type, char* command_data) {
  bool good = false;
      uint8_t profile = CHROMA_PROFILE_DEFAULT;
      if (strcmp(command_data, "true") == 0) {
        profile = CHROMA_PROFILE_BASS;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        profile = CHROMA_PROFILE_DEFAULT;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        bool note_offset_changed = apply_chroma_profile(profile);
        save_config();
        tx_begin();
        USBSerial.println(profile == CHROMA_PROFILE_BASS ? "BASS MODE ENABLED" : "BASS MODE DISABLED");
        tx_end();
        // Reboot ONLY if NOTE_OFFSET changed (matches set_chroma_profile + the
        // original mechanism: bass<->default always flips NOTE_OFFSET 0<->12).
        if (note_offset_changed) {
          reboot();
        }
      }
  return true;
}

bool serial_typed_stream(const char* command_type, char* command_data) {
  stop_streams();  // Stop any current streams
      if (strcmp(command_data, "audio") == 0) {
        stream_audio = true;
        ack();
      } else if (strcmp(command_data, "fps") == 0) {
        stream_fps = true;
        ack();
      } else if (strcmp(command_data, "max_mags") == 0) {
        stream_max_mags = true;
        ack();
      } else if (strcmp(command_data, "max_mags_followers") == 0) {
        stream_max_mags_followers = true;
        ack();
      } else if (strcmp(command_data, "magnitudes") == 0) {
        stream_magnitudes = true;
        ack();
      } else if (strcmp(command_data, "spectrogram") == 0) {
        stream_spectrogram = true;
        ack();
      } else if (strcmp(command_data, "chromagram") == 0) {
        stream_chromagram = true;
        ack();
      } else {
        bad_command(command_type, command_data);
      }
  return true;
}

bool serial_typed_slot_save(const char* command_type, char* command_data) {
  // :slot_save=N[,primary|secondary]
      // Default channel = the ACTIVE serial target, matching the shift+digit
      // hotkeys; explicit suffix exists for automated proof without relying on
      // mutable target-channel RAM state.
      bool from_secondary = secondaryMode;
      bool channel_ok = true;
      char* comma = strchr(command_data, ',');
      if (comma != nullptr) {
        *comma = '\0';
        const char* channel_name = comma + 1;
        if (strcmp(channel_name, "primary") == 0) {
          from_secondary = false;
        } else if (strcmp(channel_name, "secondary") == 0) {
          from_secondary = true;
        } else {
          channel_ok = false;
        }
      }
      int slot_number = atoi(command_data);
      if (!channel_ok || slot_number < 1 || slot_number > K1_PRESET_SLOT_COUNT) {
        bad_command(command_type, command_data);
      } else {
        tx_begin();
        serial_queue_slot_save(uint8_t(slot_number - 1), from_secondary);
        tx_end();
      }
  return true;
}

bool serial_typed_slot_load(const char* command_type, char* command_data) {
  // :slot_load=N[,primary|secondary] / :slot_arm=N[,primary|secondary]
      // Default channel = the ACTIVE serial target (space hotkey).
      bool target_secondary = secondaryMode;
      bool channel_ok = true;
      char* comma = strchr(command_data, ',');
      if (comma != nullptr) {
        *comma = '\0';
        const char* channel_name = comma + 1;
        if (strcmp(channel_name, "primary") == 0) {
          target_secondary = false;
        } else if (strcmp(channel_name, "secondary") == 0) {
          target_secondary = true;
        } else {
          channel_ok = false;
        }
      }
      int slot_number = atoi(command_data);
      if (!channel_ok || slot_number < 1 || slot_number > K1_PRESET_SLOT_COUNT) {
        bad_command(command_type, command_data);
      } else {
        tx_begin();
        if (strcmp(command_type, "slot_arm") == 0) {
          serial_queue_slot_arm(uint8_t(slot_number - 1), target_secondary);
        } else {
          serial_queue_slot_load(uint8_t(slot_number - 1), target_secondary);
        }
        tx_end();
      }
  return true;
}

bool serial_typed_slot_arm(const char* command_type, char* command_data) {
  return serial_typed_slot_load(command_type, command_data);
}

bool serial_typed_save_show(const char* command_type, char* command_data) {
  (void)command_data;
  const bool ok = k1_show_state_save();
  tx_begin();
  USBSerial.print("SHOW_STATE_SAVED");
  if (!ok) {
    USBSerial.print(" FAIL");
  }
  USBSerial.print(" primary_mode=");
  USBSerial.print(CONFIG.LIGHTSHOW_MODE);
  USBSerial.print(" primary_palette=");
  USBSerial.print(CONFIG.PALETTE_INDEX);
  USBSerial.print(" secondary_mode=");
  USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
  USBSerial.print(" secondary_palette=");
  USBSerial.println(SECONDARY_PALETTE_INDEX);
  tx_end();
  (void)command_type;
  return true;
}

bool serial_typed_show_state(const char* command_type, char* command_data) {
  (void)command_type;
  (void)command_data;
  const K1EdgeMixerConfig edge = k1_edgemixer_config();
  tx_begin();
  USBSerial.println("SHOW_STATE");
  USBSerial.print("  primary_mode=");
  USBSerial.print(CONFIG.LIGHTSHOW_MODE);
  USBSerial.print(" palette=");
  USBSerial.println(CONFIG.PALETTE_INDEX);
  USBSerial.print("  secondary_mode=");
  USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
  USBSerial.print(" palette=");
  USBSerial.print(SECONDARY_PALETTE_INDEX);
  USBSerial.print(" enabled=");
  USBSerial.println(ENABLE_SECONDARY_LEDS ? "on" : "off");
  USBSerial.print("  edge enabled=");
  USBSerial.print(edge.enabled ? "on" : "off");
  USBSerial.print(" mode=");
  USBSerial.print(static_cast<int>(edge.mode));
  USBSerial.print(" strength=");
  USBSerial.println(edge.strength, 3);
  tx_end();
  return true;
}

bool serial_typed_chromatic(const char* command_type, char* command_data) {
  // Former '1' hotkey (global chromatic colour mode toggle); RAM-only
      // state, exactly like the hotkey it replaces.
      bool good = false;
      if (strcmp(command_data, "true") == 0 || strcmp(command_data, "on") == 0) {
        chromatic_mode = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0 || strcmp(command_data, "off") == 0) {
        chromatic_mode = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }
      if (good) {
        tx_begin();
        USBSerial.print("CHROMATIC_MODE: ");
        USBSerial.println(chromatic_mode ? "on" : "off");
        tx_end();
      }
  return true;
}

bool serial_typed_secondary_status(const char* command_type, char* command_data) {
  tx_begin();
      USBSerial.print("SECONDARY_ENABLED: ");
      USBSerial.println(ENABLE_SECONDARY_LEDS ? "true" : "false");
      USBSerial.print("SECONDARY_CONTROL: ");
      USBSerial.println(secondaryMode ? "true (encoders control secondary channel)" : "false (encoders control primary channel)");
      USBSerial.print("SECONDARY_MODE: ");
      USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
      USBSerial.print(" (");
      USBSerial.print(serial_mode_name(SECONDARY_LIGHTSHOW_MODE));
      USBSerial.println(")");
      USBSerial.print("SECONDARY_PHOTONS: ");
      USBSerial.println(SECONDARY_PHOTONS, 6);
      USBSerial.print("SECONDARY_CHROMA: ");
      USBSerial.println(SECONDARY_CHROMA, 6);
      USBSerial.print("SECONDARY_MOOD: ");
      USBSerial.println(SECONDARY_MOOD, 6);
      USBSerial.print("SECONDARY_SATURATION: ");
      USBSerial.println(SECONDARY_SATURATION, 6);
      USBSerial.print("SECONDARY_PRISM_COUNT: ");
      USBSerial.println(SECONDARY_PRISM_COUNT, 2);
      USBSerial.print("SECONDARY_MIRROR_ENABLED: ");
      USBSerial.println(SECONDARY_MIRROR_ENABLED ? "true" : "false");
      USBSerial.print("SECONDARY_REVERSE_ORDER: ");
      USBSerial.println(SECONDARY_REVERSE_ORDER ? "true" : "false");
      USBSerial.print("SECONDARY_BASE_COAT: ");
      USBSerial.println(SECONDARY_BASE_COAT ? "true" : "false");
      USBSerial.print("SECONDARY_PALETTE_MODE_ENABLED: ");
      USBSerial.println(SECONDARY_PALETTE_MODE_ENABLED ? "true" : "false");
      USBSerial.print("SECONDARY_PALETTE_INDEX: ");
      USBSerial.print(SECONDARY_PALETTE_INDEX);
      if (SECONDARY_PALETTE_MODE_ENABLED) {
        char buffer[32];
        strcpy_P(buffer, (const char *)pgm_read_ptr(&(paletteNames[SECONDARY_PALETTE_INDEX])));
        USBSerial.print(" ("); USBSerial.print(buffer); USBSerial.println(")");
      } else {
        USBSerial.println();
      }
      USBSerial.println("NOTE: This command is deprecated, please use secondary_status instead");
      tx_end();
  return true;
}

bool serial_typed_start_benchmark(const char* command_type, char* command_data) {
  if (!benchmark_running) {
        benchmark_running = true;
        benchmark_start_time = millis();
        system_fps_sum = 0;
        led_fps_sum = 0;
        benchmark_sample_count = 0;
        ack();
        tx_begin();
        USBSerial.print("Benchmark started (Duration: ");
        USBSerial.print(benchmark_duration / 1000);
        USBSerial.println(" seconds)...");
        tx_end();
      } else {
        tx_begin(true);
        USBSerial.println("Benchmark already running.");
        tx_end(true);
      }
  return true;
}

bool serial_typed_stream_spectrogram(const char* command_type, char* command_data) {
  stream_spectrogram = !stream_spectrogram;
      USBSerial.print("STREAM_SPECTROGRAM: ");
      USBSerial.println(stream_spectrogram);
  return true;
}

bool serial_typed_stream_agc(const char* command_type, char* command_data) {
  stream_agc_debug = !stream_agc_debug;
      USBSerial.print("STREAM_AGC_DEBUG: ");
      USBSerial.println(stream_agc_debug ? "ON" : "OFF");
  return true;
}

bool serial_typed_stream_chromagram(const char* command_type, char* command_data) {
  stream_chromagram = !stream_chromagram;
      USBSerial.print("STREAM_CHROMAGRAM: ");
      USBSerial.println(stream_chromagram);
  return true;
}
