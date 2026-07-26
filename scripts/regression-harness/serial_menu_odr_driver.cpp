// Host ODR driver: primary TU that #includes serial_menu.h and links serial_menu.cpp.
// Paired with serial_menu_second_tu_smoke.cpp (second TU) in test_serial_menu_odr_static.py.
#include <cstring>
#include "globals.h"
#include "serial_replay_host_stubs.h"

void save_config() {}
void save_config_delayed() {}
void reboot() {}
void set_preset(char*) {}
void check_current_function() {}
void factory_reset() {}
void restore_defaults() {}
void clear_noise_cal() {}
float k1_queue_transition_scale_primary = 1.0f;
float k1_queue_transition_scale_secondary = 1.0f;
int raw_dump_request = 0;

#include "serial_menu.h"

void k1_noise_cal_arm() {}
void k1_noise_cal_disarm() {}
bool k1_noise_cal_confirm(uint32_t) { return false; }
bool k1_queue_any_armed() { return false; }
K1ChannelPreset* k1_queue_arm_begin(bool) { return nullptr; }
void k1_queue_arm_preset(bool, const K1ChannelPreset&) {}
void k1_queue_request_commit(bool, uint32_t) {}
bool k1_queue_mode_enabled() { return false; }
uint8_t k1_queue_transition_style() { return 0; }
uint16_t k1_queue_dip_ms() { return 0; }
bool k1_queue_set_dip_ms(uint32_t) { return true; }
uint16_t k1_queue_xfade_ms() { return 0; }
bool k1_queue_set_xfade_ms(uint32_t) { return true; }
uint8_t k1_queue_commit_quantise() { return 0; }
void k1_queue_set_commit_quantise(uint8_t) {}
void k1_queue_set_transition_style(uint8_t) {}
void k1_queue_set_mode_enabled(bool) {}
bool k1_preset_slot_save(uint8_t, bool) { return false; }
bool k1_preset_slot_get(uint8_t, K1ChannelPreset*) { return false; }
void vp_run_output_probe() {}
void vp_print_secondary_state() {}
K1AudioSnapshot k1_audio_snapshot_read() { return {}; }
bool benchmark_running = false;
uint32_t benchmark_start_time = 0;
uint32_t system_fps_sum = 0;
uint32_t led_fps_sum = 0;
uint32_t benchmark_sample_count = 0;

void serial_menu_odr_driver_anchor() {
  (void)serial_cmd_lookup("help");
}

extern void serial_menu_second_tu_smoke_anchor();

int main() {
  serial_menu_odr_driver_anchor();
  serial_menu_second_tu_smoke_anchor();
  return 0;
}
