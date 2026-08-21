/*----------------------------------------
  SERIAL TYPED COMMAND DISPATCH (Stage B `type=value` handlers)
  ----------------------------------------*/
#ifndef SERIAL_TYPED_DISPATCH_H
#define SERIAL_TYPED_DISPATCH_H

#include <stdbool.h>
#include <stdint.h>

// Forward-declare safety_class_t from serial_menu.h — included after serial_cmd_row_t
// is defined when building the table in serial_menu.h.

typedef bool (*serial_typed_handler_t)(const char* command_type, char* command_data);

// ---- dispatcher family wrappers ----
bool serial_typed_wrap_pure_setter(const char* command_type, char* command_data);
bool serial_typed_wrap_reboot_setter(const char* command_type, char* command_data);
bool serial_typed_wrap_vp_tuning(const char* command_type, char* command_data);
bool serial_typed_wrap_response_gain(const char* command_type, char* command_data);
bool serial_typed_wrap_queue(const char* command_type, char* command_data);
bool serial_typed_wrap_smart_director(const char* command_type, char* command_data);
bool serial_typed_wrap_smart_visual(const char* command_type, char* command_data);
bool serial_typed_wrap_edge_mixer(const char* command_type, char* command_data);
bool serial_typed_wrap_preset(const char* command_type, char* command_data);
bool serial_typed_wrap_secondary(const char* command_type, char* command_data);
bool serial_typed_wrap_mode(const char* command_type, char* command_data);
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
bool serial_typed_wrap_ap_diag(const char* command_type, char* command_data);
#endif
#ifdef K1_AP_TWITCH_ORACLE_V1
bool serial_typed_ap_twitch(const char* command_type, char* command_data);
#endif
#if K1_VIVID_PRECOMP_V1
bool serial_typed_wrap_vivid(const char* command_type, char* command_data);
#endif
#if ENABLE_GDFT_HARNESS
bool serial_typed_wrap_gdft_harness(const char* command_type, char* command_data);
#endif
#ifdef K1_MIC_IM69D_STEREO_V1
bool serial_typed_wrap_stereo_probe(const char* command_type, char* command_data);
#endif
#ifdef K1_RENDER_TRACE_V1
bool serial_typed_wrap_render_trace(const char* command_type, char* command_data);
#endif
#if K1_EFFECT_FRAMEWORK_V1
bool serial_typed_wrap_beat_director(const char* command_type, char* command_data);
#endif

// ---- inline-extracted typed handlers ----
bool serial_typed_vp_profile(const char* command_type, char* command_data);
bool serial_typed_vp_all(const char* command_type, char* command_data);
bool serial_typed_ap_stream(const char* command_type, char* command_data);
#ifdef K1_MIC_HEALTH_V1
bool serial_typed_mic_health(const char* command_type, char* command_data);
#ifdef K1_MIC_HEALTH_FAULT_INJECT_V1
bool serial_typed_mic_health_fault(const char* command_type, char* command_data);
#endif
#endif
#if ENABLE_TEMPO_STREAM
bool serial_typed_tempo_stream(const char* command_type, char* command_data);
#endif
#if ENABLE_AP_STREAM
bool serial_typed_ap_capture(const char* command_type, char* command_data);
#endif
#if ENABLE_FRAME_DUMP
bool serial_typed_frame_dump(const char* command_type, char* command_data);
#endif
#if ENABLE_VP_PROBE_CMD
bool serial_typed_vp_probe(const char* command_type, char* command_data);
#endif
#if ENABLE_MOTION_PROBE
bool serial_typed_mp_step(const char* command_type, char* command_data);
bool serial_typed_mp_flash(const char* command_type, char* command_data);
bool serial_typed_mp_off(const char* command_type, char* command_data);
bool serial_typed_mp_status(const char* command_type, char* command_data);
#endif
bool serial_typed_dump_raw(const char* command_type, char* command_data);
bool serial_typed_vp_stream(const char* command_type, char* command_data);
bool serial_typed_ble_stream(const char* command_type, char* command_data);
bool serial_typed_vp_perf(const char* command_type, char* command_data);
bool serial_typed_show_skip(const char* command_type, char* command_data);
#ifdef K1_SCHEDULING_TRACE_V1
bool serial_typed_scheduling_trace(const char* command_type, char* command_data);
#endif
#if ENABLE_DIAG_CAPTURE
bool serial_typed_diag(const char* command_type, char* command_data);
#endif
#if ENABLE_VPAB_PROBE
bool serial_typed_vpab(const char* command_type, char* command_data);
#endif
#if K1_PIN_EVIDENCE_V1
bool serial_typed_k1_pin_evidence(const char* command_type, char* command_data);
#endif
#if ENABLE_VP_MOTION_LAB
bool serial_typed_vpml(const char* command_type, char* command_data);
#endif
bool serial_typed_debug(const char* command_type, char* command_data);
bool serial_typed_get_mode_name(const char* command_type, char* command_data);
#if K1_LOUD_GUARD_V1
bool serial_typed_k1_loud_guard(const char* command_type, char* command_data);
#endif
bool serial_typed_standby_dimming(const char* command_type, char* command_data);
bool serial_typed_silence_enter(const char* command_type, char* command_data);
bool serial_typed_silence_exit(const char* command_type, char* command_data);
bool serial_typed_silence_dwell(const char* command_type, char* command_data);
bool serial_typed_silence_rms_enter(const char* command_type, char* command_data);
bool serial_typed_silence_rms_exit(const char* command_type, char* command_data);
bool serial_typed_set_chroma_profile(const char* command_type, char* command_data);
bool serial_typed_bass_mode(const char* command_type, char* command_data);
bool serial_typed_stream(const char* command_type, char* command_data);
bool serial_typed_slot_save(const char* command_type, char* command_data);
bool serial_typed_slot_load(const char* command_type, char* command_data);
bool serial_typed_save_show(const char* command_type, char* command_data);
bool serial_typed_show_state(const char* command_type, char* command_data);
bool serial_typed_chromatic(const char* command_type, char* command_data);
bool serial_typed_secondary_status(const char* command_type, char* command_data);
bool serial_typed_start_benchmark(const char* command_type, char* command_data);
bool serial_typed_stream_spectrogram(const char* command_type, char* command_data);
bool serial_typed_stream_agc(const char* command_type, char* command_data);
bool serial_typed_stream_chromagram(const char* command_type, char* command_data);

#ifdef K1_LOOK_LIB_V1
bool serial_typed_wrap_look(const char* command_type, char* command_data);
#endif

#endif // SERIAL_TYPED_DISPATCH_H
