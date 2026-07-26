/*----------------------------------------
  K1 UART COMMAND LINE
  ----------------------------------------*/

#ifndef SERIAL_MENU_H
#define SERIAL_MENU_H

#include "globals.h"  // For USBSerial and global variables
#include "constants.h" // For NUM_AGC_BANDS
#include "k1_trace.h"
#include <stdint.h>   // For uint32_t
#include <stdlib.h>   // For strtof, atoi
#include <string.h>   // For strtok, strncpy (gdft_sweep parse — item 22)
#include <math.h>     // For isfinite
#if ENABLE_DIAG_CAPTURE
#include "diagnostic_capture.h"
#endif
#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"
#endif
#ifdef K1_PIN_EVIDENCE_V1
#include "k1_pin_evidence.h"
#endif
#ifdef K1_EFFECT_FRAMEWORK_V1
#include "beat_aware_director.h"
#endif
#ifdef K1_MIC_AUTO_SENSE_V1
#include "k1_mic_auto_sense.h"
#endif
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h" // registry_display_name() (R2b serial name source of truth)
#endif
#include "k1_audio_snapshot.h"
#include "k1_edgemixer.h"
#include "k1_mode_selection.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
#include "k1_smart_director.h"
#include "k1_visual_hooks.h"
#include "k1_noise_cal_arm.h"
#include "k1_effect_queue.h"
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
#include <esp_heap_caps.h>
#endif

// These functions watch the Serial port for incoming commands,
// and perform actions based on whatis recieved.

extern void check_current_function();  // system.h
extern void reboot();                  // system.h
void vp_run_output_probe();            // lightshow_modes.h
void vp_run_secondary_bleed_probe();   // lightshow_modes.h (item 17)
void vp_print_secondary_state();       // lightshow_modes.h (item 16)
#ifdef ENABLE_GDFT_HARNESS
void gdft_run_single(float freq_hz);            // gdft_harness.h (item 22)
void gdft_run_sweep(float f0, float f1, int steps); // gdft_harness.h (item 22)
void gdft_run_agc_probe(float amp_scale);       // gdft_harness.h (item 22 — AGC A/B)
#endif
#ifdef ENABLE_MOTION_PROBE
void motion_probe_arm_step(float interval_ms, int size_px, float lum);     // motion_probe.h
void motion_probe_arm_flash(int a_px, int b_px, float gap_ms,
                            float lum, float on_ms);                       // motion_probe.h
void motion_probe_off();                                                   // motion_probe.h
void motion_probe_status();                                                // motion_probe.h
void motion_probe_hotkey_arm_step();                                       // motion_probe.h (hotkey z)
void motion_probe_hotkey_arm_flash();                                      // motion_probe.h (hotkey x)
void motion_probe_hotkey_knob_a(int dir);                                  // motion_probe.h (hotkey v/b)
void motion_probe_hotkey_knob_b(int dir);                                  // motion_probe.h (hotkey n/m)
#endif
#ifdef ENABLE_VP_MOTION_LAB
bool vpml_command(const char* command_type, const char* command_data);      // vp_motion_lab.h
#endif

// Benchmark state variables (defined in main .ino file)
extern bool benchmark_running;
extern uint32_t benchmark_start_time;
extern uint32_t system_fps_sum;
extern uint32_t led_fps_sum;
extern uint32_t benchmark_sample_count;
extern const uint32_t benchmark_duration; // ms — defined in serial/serial_menu.cpp (R1)

// Multi-band AGC debug flag
extern bool stream_agc_debug;

#if ENABLE_TEMPO_STREAM
#ifndef TEMPO_STREAM_DEFAULT_ON
#define TEMPO_STREAM_DEFAULT_ON 1
#endif
// External linkage (was static): the extracted stop_streams() in serial_tx.cpp
// references this flag under the ENABLE_TEMPO_STREAM gate (cross-TU edge:
// static -> extern, statement identical). serial_menu.h is the single-include
// owner of the definition.
extern bool TEMPO_STREAM_ENABLED;
#endif

// AP capture/telemetry state + handlers extracted to a dedicated TU
// (serial/k1_ap_capture_telemetry.{cpp,h}). Same ENABLE_TEMPO_STREAM &&
// ENABLE_AP_FRONTEND_DEBUG gate -> compiles to nothing in production.
#include "k1_ap_capture_telemetry.h"

// Serial protocol envelope (tx_begin/tx_end/ack/bad_command/stop_streams/
// init_serial) extracted to serial/serial_tx.{cpp,h} (Lane 2, S2 / Unit B).
// serial_tx.h is the single source of the tx_begin/tx_end default arguments.
#include "serial_tx.h"

// Command-parse leaf primitives (vp_parse_bool/float, serial_clamp_float,
// serial_wrap_index) extracted to serial/serial_parse_helpers.{cpp,h}
// (Lane 2, S2 / Unit C).
#include "serial_parse_helpers.h"

// The 23 pure CONFIG setters (parse -> CONFIG write -> save_config[_delayed] ->
// echo; no reboot, no subsystem coupling) extracted to
// serial/serial_cmd_handlers.{cpp,h} (Lane 2, S4 / Unit H first slice).
// parse_command() dispatches them via serial_cmd_dispatch_pure_setter(); the S3.0
// serial_replay golden gates the move (must reproduce byte-for-byte).
#include "serial_cmd_handlers.h"

// init_serial() is NOT extracted to serial_tx.cpp: its body references the
// FIRMWARE_VERSION macro, which is #define'd in the .ino TU (not a header), so
// it only compiles inside the .ino include context — it stays here (verbatim).
void init_serial(uint32_t baud_rate);

// This is for development purposes, and allows the user to dump
// the current values of many variables to the monitor at once
void dump_info();

// vp_parse_bool / vp_parse_float extracted to serial/serial_parse_helpers.cpp
// (Lane 2, S2 / Unit C) — declarations in serial_parse_helpers.h (included
// above).

const char* vp_bool_text(bool value);

#ifdef K1_LOUD_GUARD_V1
// K1 loud-guard serial helpers — DEFINITIONS moved to serial/serial_menu.cpp
// (M2.1 R1 batch 4). Gated declarations remain for the in-header command dispatch.
void serial_print_k1_loud_guard_status();
void serial_set_k1_loud_guard(bool enabled);
void serial_cycle_k1_loud_guard_mode();
#endif

#ifdef K1_MIC_AUTO_SENSE_V1
void serial_print_k1_mic_auto_status() {
  const K1MicAutoState& st = k1_mic_auto_sense_state();
  USBSerial.print("K1_MIC_AUTO: ");
  USBSerial.println(vp_bool_text(st.runtime_enabled));
  USBSerial.print("K1_MIC_AUTO_SHADOW: ");
  USBSerial.println(vp_bool_text(st.shadow_only));
  USBSerial.print("K1_MIC_AUTO_SCALE: ");
  USBSerial.println(k1_mic_auto_sense_applied_scale(), 6);
  USBSerial.print("K1_MIC_AUTO_REC: ");
  USBSerial.println(st.recommended_scale, 6);
  USBSerial.print("K1_MIC_AUTO_STATE: ");
  USBSerial.println((unsigned)st.state);
  USBSerial.print("K1_MIC_AUTO_REASON: ");
  USBSerial.println((unsigned)st.reason);
  USBSerial.println("K1_MIC_AUTO_NOTE: runtime-only; never NVS; purity=:mic_auto=off");
}
#endif

#ifdef K1_EFFECT_FRAMEWORK_V1
// beat_director serial helper — DEFINITION moved to serial/serial_menu.cpp
// (M2.1 R1 batch 4). serial_cmd_handlers.cpp already forward-declares + calls it.
void serial_print_beat_director_status();
// ---------------------------------------------------------------------------
// beat_director serial helpers (P6 eyes-on toggle — isolated, separable block)
// ---------------------------------------------------------------------------
void serial_print_beat_director_status() {
  // READ-ONLY: uses pure accessors only — never ticks the director or arms a
  // transition, so a status query never advances selection/dwell state.
  const bool enabled = bad_director_enabled();
  const bool locked  = bad_director_tempo_locked();
  USBSerial.print("BEAT_DIRECTOR: ");
  USBSerial.println(vp_bool_text(enabled));
  USBSerial.print("BEAT_DIRECTOR_OPT_IN: ");
  USBSerial.println(vp_bool_text(bad_director_compile_opt_in()));
  USBSerial.print("BEAT_DIRECTOR_MODE: ");
  USBSerial.println(bad_director_current_mode());
  USBSerial.print("BEAT_DIRECTOR_TEMPO_LOCKED: ");
  USBSerial.println(vp_bool_text(locked));
  USBSerial.print("BEAT_DIRECTOR_BPM: ");
  USBSerial.println(bad_director_bpm(), 1);
  USBSerial.print("BEAT_DIRECTOR_TEMPO_CONF: ");
  USBSerial.println(bad_director_tempo_confidence(), 3);
  USBSerial.print("BEAT_DIRECTOR_FALLBACK: ");
  USBSerial.println(vp_bool_text(!locked));  // time-fallback active when unlocked
  // Device-proof surface (Proposal 3): poll these after a known-BPM locked track
  // to confirm switches land beat-quantised. RAM-only; no NVS.
  USBSerial.print("BEAT_DIRECTOR_SWITCH_COUNT: ");
  USBSerial.println(bad_director_switch_count());
  USBSerial.print("BEAT_DIRECTOR_LAST_SWITCH_MS: ");
  USBSerial.println(bad_director_last_switch_ms());
  USBSerial.print("BEAT_DIRECTOR_LAST_SWITCH_MODE: ");
  USBSerial.println(bad_director_last_switch_mode());
  USBSerial.print("BEAT_DIRECTOR_LAST_SWITCH_BEAT_Q: ");
  USBSerial.println(vp_bool_text(bad_director_last_switch_beat_quantised()));
  // Sticky lock-at-commit (rework 2026-07-25): score against THIS, not poll-time lock.
  USBSerial.print("BEAT_DIRECTOR_LAST_SWITCH_LOCKED: ");
  USBSerial.println(vp_bool_text(bad_director_last_switch_tempo_locked()));
}
#endif  // K1_EFFECT_FRAMEWORK_V1

#ifdef K1_VIVID_PRECOMP_V1
// Vivid pre-comp helpers — DEFINITIONS moved to serial/serial_menu.cpp (M2.1 R1
// batch 3). Declarations stay (gated) so the extracted serial_cmd_dispatch_vivid
// (serial_cmd_handlers.cpp) and the in-header 'v' hotkey dispatch resolve against
// the single out-of-line definition. Behaviour-preserving: serial goldens reproduce.
void serial_update_vivid_enabled_from_levels();
void serial_ensure_vivid_defaults();
void serial_set_vivid_level(float value);
void serial_print_vivid_precomp_status();
void serial_toggle_vivid_precomp();
#endif


const char* vp_profile_name(uint8_t profile);

void vp_apply_profile(uint8_t profile);

void vp_print_status();

// ---------------------------------------------------------------------------
// Edge-mixer name/parse helpers — DEFINITIONS moved to serial/serial_menu.cpp
// (M2.1 Phase R1, batch 1: kill the serial_menu.h ODR bomb). Declarations stay
// here so the in-header status printers (k1_print_edge_status et al.) and the
// extracted serial_cmd_dispatch_edge_mixer() in serial_cmd_handlers.cpp resolve
// against the single out-of-line definition. Behaviour-preserving: the
// serial_replay + serial_struct goldens reproduce byte-for-byte after the move.
// ---------------------------------------------------------------------------
const char* k1_edge_mode_name(K1EdgeMixerMode mode);
bool k1_parse_edge_mode(const char* text, K1EdgeMixerMode* out_mode);
const char* k1_edge_rotation_name(K1EdgeMixerRotationSpace space);
const char* k1_edge_dual_name(K1EdgeMixerDualEdge dual);
bool k1_parse_edge_rotation(const char* text, K1EdgeMixerRotationSpace* out_space);
bool k1_parse_edge_dual(const char* text, K1EdgeMixerDualEdge* out_dual);
bool k1_parse_edge_uniform(const char* text, bool* out_uniform);

// k1_print_smart_status — DEFINITION moved to serial/serial_menu.cpp (M2.1 R1
// batch 5). serial_cmd_handlers.cpp already forward-declares + calls it; the
// declaration stays here for the in-header dispatch. Behaviour-preserving.
void k1_print_smart_status();

// ---------------------------------------------------------------------------
// Edge-mixer status + live-hotkey control — DEFINITIONS moved to
// serial/serial_menu.cpp (M2.1 Phase R1, batch 2). Declarations stay here for the
// in-header hotkey dispatch and the extracted serial_cmd_dispatch_edge_mixer
// (serial_cmd_handlers.cpp already forward-declares k1_print_edge_status /
// k1_edge_warn_if_collapsed). Behaviour-preserving: goldens reproduce byte-for-byte.
// ---------------------------------------------------------------------------
void k1_print_edge_status();
void k1_edge_warn_if_collapsed(const K1EdgeMixerConfig& e);
void serial_edge_toggle_enabled();
void serial_edge_cycle_mode();
void serial_edge_adjust_spread(int delta);
void serial_edge_adjust_strength(float delta);
void serial_edge_toggle_rotation();
void serial_edge_toggle_dual_edge();
void serial_edge_toggle_uniform();

bool k1_apply_smart_scene(const char* scene);

void vp_perf_print_status();

void vp_perf_command(const char* command_type, const char* command_data);

#if ENABLE_VPAB_PROBE
void vpab_command(const char* command_type, const char* command_data);
#endif

bool vp_set_flag_command(const char* command_type, const char* command_data, bool* flag);

bool vp_set_float_command(const char* command_type, const char* command_data, float* value, float min_value, float max_value);

// serial_clamp_float / serial_wrap_index extracted to
// serial/serial_parse_helpers.cpp (Lane 2, S2 / Unit C) — declarations in
// serial_parse_helpers.h (included above).

const char* serial_target_name();

void serial_disarm_noise_cal();

void serial_arm_noise_cal();

void serial_confirm_noise_cal();

// Display name for a lightshow ordinal. Under the registry flag the name is
// sourced from the EffectRegistry row that owns the ordinal (single source of
// truth, native ordinals included); when no row owns it (or the registry is
// unhealthy) it falls back to the legacy `mode_names + (mode * 32)` table.
// Without the flag this is exactly the legacy table lookup.
// External linkage (widened from `static inline` 2026-06-26): serial_cmd_dispatch_mode()
// in serial_cmd_handlers.cpp forward-declares + links against this single definition
// (serial_menu.h has one includer, the .ino TU) — same cross-TU pattern as
// serial_print_mode_line / serial_print_palette_line below. Statement-identical body.
const char* serial_mode_name(uint8_t mode);

void serial_print_mode_line(const char* label, uint8_t mode);

void serial_print_palette_line(const char* label, uint8_t index);

void serial_print_target_float(const char* name, float value, uint8_t precision);

void serial_print_target_bool(const char* name, bool value);

// Effects-queue routing (spec §1): mode browse never hard-cuts the live value
// any more. The serial side only writes pending/arm state; Core 1 applies at
// the frame boundary. Queue mode OFF = immediate commit THROUGH the dip
// transition; queue mode ON = arm only, '\' commits. Stepping is relative to
// the ARMED value (multi-step staging).
void serial_adjust_target_mode(int8_t delta);

#ifdef K1_BLE_REMOTED
// Confirmed committed light-show mode ordinal per channel — read by the gated BLE
// Remoted central (network/ble_remoted_central.cpp) to feed the knob's on-screen
// CONFIRMED mode display. Gated: exists only in the k1_ble_remoted_probe build.
uint8_t k1_confirmed_mode(bool secondary);
#endif

void serial_adjust_target_float(const char* name, float* primary_value, float* secondary_value, float primary_min, float secondary_min, float max_value, float step, uint8_t precision);

void serial_toggle_target_bool(const char* name, bool* primary_value, bool* secondary_value);

// Effects-queue routing (spec §1): palette browse arms the pending struct and
// commits via the queue engine — dip when queue mode is off, '\' when on.
void serial_adjust_target_palette(int8_t delta);

void serial_toggle_target_palette_mode();

// ---- Effects queue + preset slots (serial side: arm/flag only) --------------

const char* serial_queue_channel_name(bool secondary);

// Arm slot N (0-based) onto a channel WITHOUT committing (used by :slot_arm and
// the queue-mode-ON load path). Returns false if the slot is empty/invalid.
bool serial_queue_slot_arm(uint8_t slot_index, bool target_secondary);

// Load slot N (0-based): queue mode ON = arm; OFF = apply through the dip.
void serial_queue_slot_load(uint8_t slot_index, bool target_secondary);

// Save the ACTIVE channel's live 15 fields into slot N (0-based). File written
// immediately (rare op; loop core only — never the render task).
void serial_queue_slot_save(uint8_t slot_index, bool from_secondary);

// '\' / :commit — commit ALL armed channels in the same frame.
void serial_queue_commit();

void serial_queue_toggle_mode();

void serial_print_hotkey_help();

void serial_print_hotkey_status();

bool serial_hotkey_is_immediate(char key);

bool serial_hotkey_marks_manual_visual_control(char key);

bool serial_command_marks_manual_visual_control(const char* command_type);
	
void serial_handle_hotkey(char key);

// ============================================================================
//  ROW 1 — STATIC DISPATCH TABLE (control-plane safety surface)
// ----------------------------------------------------------------------------
//  Replaces the hand-rolled strcmp chain for the SAFETY-CRITICAL bare-command
//  surface (the destructive / calibration commands reachable via typed `:cmd`)
//  with a single const table in .rodata. The table — not 24 hand-written
//  `else if` arms — is the authority for the TYPED `:cmd` surface:
//    (a) whether a typed command needs a typed CONFIRM token,
//    (b) whether the command needs the silence ARM window,
//    (c) the safety class / flags / intended input surface of each command,
//    (d) (via #ifdef in serial_cmd_table.def's consumers) harness-only gating.
//  The single-byte immediate-hotkey path is SEPARATE (serial_hotkey_is_immediate
//  / serial_handle_hotkey) and is constrained there, not by this table; the
//  no-dangerous-keystroke static_assert below cross-checks the two surfaces.
//
//  Adding a command = adding a row with a safety class. There is no path to
//  wire a destructive command without choosing a class, and a compile-time
//  static_assert forbids binding a destructive/ARM class to a keystroke. This
//  is the C1 resolution from docs/k1-refactor-2026-05/04-row1-dispatch-table-
//  safety-class-sketch.md (Captain rulings D5/D6 folded in).
//
//  SIGNED behaviour deltas vs the pre-Row-1 strcmp chain (the ONLY changes):
//    D5 — typed `start_noise_cal` no longer fires calibration. It now prints
//         guidance. `N`(arm)->`Y`(confirm) is the sole calibration trigger.
//    D6 — `factory_reset` / `restore_defaults` / `clear_noise_cal` require a
//         typed `CONFIRM` token (e.g. `:factory_reset CONFIRM`). Bare/single-
//         byte invocation prints usage and does nothing.
//    D-harness — ap_capture / frame_dump / vp_probe stay #ifdef-gated behind
//         their existing ENABLE_* flags (absent from the release build).
//
//  The heterogeneous *typed* setters (`type=value`, 75 arms) keep their exact
//  value-interpretation bodies below — they are not keystroke-reachable and
//  rewriting their parsing into a uniform shape would be a behaviour-risk far
//  outside a control-plane refactor. The table owns ROUTING + SAFETY, not the
//  re-implementation of every setter.
// ============================================================================

typedef enum {
  SC_SAFE = 0,             // read-only or trivially reversible; hotkey + typed OK
  SC_TYPED_ONLY,           // not a one-keystroke action; typed-only (disruptive/recoverable)
  SC_ARM_REQUIRED,         // correctness needs the silence ARM window (cal); confirm leg only as hotkey
  SC_FORBIDDEN_SINGLE_BYTE // destructive/irreversible; typed CONFIRM token; never a keystroke
} safety_class_t;

// Command flags (bitfield) — descriptive metadata, surfaced to integrity checks.
#define CMD_PERSISTS     (1u << 0)  // writes config (save_config / save_config_delayed)
#define CMD_IRREVERSIBLE (1u << 1)  // deletes persisted state / no in-session undo
#define CMD_NEEDS_SILENCE (1u << 2) // correctness depends on acoustic silence
#define CMD_DISRUPTIVE   (1u << 3)  // reboots / interrupts the show
#define CMD_HARNESS      (1u << 4)  // #ifdef-gated debug surface (absent from release)

// Input surface a command row is allowed to be reached from.
typedef enum {
  IS_BOTH = 0,        // single-byte hotkey AND typed `:cmd`
  IS_TYPED_ONLY,      // only typed `:cmd`
  IS_HOTKEY_IMMEDIATE // only as a single-byte immediate hotkey
} input_surface_t;

typedef struct {
  const char*     name;          // typed command token (NUL-terminated, in flash)
  char            hotkey;        // single-byte form, or 0 if none
  void          (*handler)();    // bare-command handler (no args; typed-value setters live below)
  safety_class_t  safety_class;
  uint8_t         flags;
  input_surface_t input_surface;
} serial_cmd_row_t;

// ---- bare-command handlers (behaviour-identical extractions of the old arms) ----
// Each body is a verbatim move of the corresponding `else if (strcmp(command_buf,...))`
// arm. No behaviour change here; the deltas are enforced by the table + dispatcher.

void cmd_version();

// Lane N5: serial-readable build provenance. One line that ties a running unit
// back to the exact source it was built from — FIRMWARE_VERSION (coarse, shared
// across commits) plus the git short hash, build epoch, and PlatformIO env that
// scripts/platformio/k1_build_provenance.py stamps in at compile time. Each
// define is guarded with an #ifdef + sane default so a build WITHOUT the
// provenance pre-script (e.g. a bare host/IDE compile) still builds and answers.
// Kept separate from cmd_version() on purpose: the `version` output is locked by
// host goldens, so provenance gets its own `build` command rather than changing
// the VERSION line.
void cmd_build();

void cmd_help();
void cmd_help() {
  tx_begin();
  USBSerial.println("K1 - Serial Menu ------------------------------------------------------------------------------------");
  USBSerial.println();
  USBSerial.println("                                            v | Print firmware version number");
  USBSerial.println("                                        build | Print build provenance (version + git hash + epoch + env)");
  USBSerial.println("                                        reset | Reboot K1");
  USBSerial.println("                          factory_reset CONFIRM | Delete configuration, including noise cal, reboot (CONFIRM required)");
  USBSerial.println("                       restore_defaults CONFIRM | Delete configuration, reboot (CONFIRM required)");
  USBSerial.println("                                         dump | Print tons of useful variables in realtime");
  USBSerial.println("                                         stop | Stops the output of any enabled streams");
  USBSerial.println("                                          fps | Return the system FPS");
  USBSerial.println("                                      led_fps | Return the LED FPS");
  USBSerial.println("                                      chip_id | Return the chip id (MAC) of the CPU");
  USBSerial.println("                                     get_mode | Get lightshow mode's ID (index)");
  USBSerial.println("                                get_num_modes | Return the number of modes available");
  USBSerial.println("                  noise calibration | press N to arm, then Y within 5s (typed start_noise_cal is disabled)");
  USBSerial.println("                        clear_noise_cal CONFIRM | Clear the stored noise calibration (CONFIRM required)");
  USBSerial.println("                             start_benchmark | Start a timed benchmark (calculates avg FPS)");
  USBSerial.println("                                  stream_agc | Toggle multi-band AGC debug visualization");
  USBSerial.println("                                    vp_status | Print visual-pipeline diagnostic state");
  USBSerial.println("                                  vp_out_test | Render controlled VP frames and print output hashes");
  USBSerial.println("                      vp_profile=[original/clean/candidate] | Apply VP diagnostic profile");
  USBSerial.println("                         ap_stream=[on/off] | Stream 1 Hz audio-pipeline telemetry");
  USBSerial.println("                         vp_stream=[on/off] | Stream 1 Hz VP diagnostic telemetry");
  USBSerial.println("                         ble_stream=[on/off] | Stream 1 Hz [ble_remoted] counters + heap telemetry (bench BLE build)");
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  USBSerial.println("                         nov_capture=[ms] | Non-shippable buffered accepted-novelty capture");
  USBSerial.println("                         nov_dump=1 | Dump buffered NOV rows after capture");
  USBSerial.println("                         nov_clear=1 | Clear buffered NOV rows");
  USBSerial.println("                         nov_status=1 | Show buffered NOV capture status");
  USBSerial.println("                         apcad_capture=[ms] | Non-shippable buffered AP cadence/read-health capture");
  USBSerial.println("                         apcad_dump=1 | Dump buffered APCAD rows after capture");
  USBSerial.println("                         apcad_clear=1 | Clear buffered APCAD rows");
  USBSerial.println("                         apcad_status=1 | Show buffered APCAD capture status");
  USBSerial.println("                         apcad_soak=[ms] | Compact AP cadence/read-health soak without row dump");
  USBSerial.println("                         apcad_soak_status=1 | Print compact APCAD soak summary + worst rows");
  USBSerial.println("                         apcad_abort=1 | Stop APCAD capture/soak without dumping buffered rows");
#endif
	  USBSerial.println("                  vp_perf=[start/stop/reset/status] | Measure VP frame stages when compiled in");
	  USBSerial.println("                  smart_status | Runtime Smart Visual Engine status");
	  USBSerial.println("                  smart_assist=[on/off] | Runtime-enable Smart Assist modulation");
	  USBSerial.println("                  smart_switching=[on/off] | Runtime-enable bounded Assist mode switching");
	  USBSerial.println("                  smart_confidence_floor=[0.00-1.00] | Runtime Assist switch confidence floor");
	  USBSerial.println("                  smart_scene=[off/assist/l1/auto] | Apply runtime Smart A/B scene preset");
	  USBSerial.println("                  smart_hooks=[on/off] | Runtime-enable onset/beat visual hooks");
	  USBSerial.println("                  event_status | Print current onset/kick/snare/hihat event state");
	  USBSerial.println("                  edge_status | Runtime EdgeMixer status");
	  USBSerial.println("                  edge_enabled=[on/off] | Runtime-enable secondary EdgeMixer");
	  USBSerial.println("                  edge_mode=[off/analogous/complementary/split/veil/triadic/tetradic] | EdgeMixer mode");
	  USBSerial.println("                  edge_strength=[0.00-1.00] | EdgeMixer strength");
	  USBSerial.println("                  edge_spread=[0-60] | EdgeMixer harmony spread (degrees)");
	  USBSerial.println("                  edge_rotation=[faithful/luma/oklab] | EdgeMixer rotation space (faithful=grey-axis; luma=+BT.601 rescale; oklab=perceptual OKLab)");
	  USBSerial.println("                  edge_dual=[one_sided/split/mirror] | EdgeMixer symmetric dual-edge (one_sided=secondary only; split=both +/-theta/2; mirror=both +/-theta)");
	  USBSerial.println("                  edge_uniform=[uniform/masked] | EdgeMixer spatial weighting (uniform=even; masked=fades from the 79/80 centre to the ends) (ref E)");
	  USBSerial.println("     EdgeMixer keys: g on/off | G cycle mode | -/= spread -/+5 | _/+ strength -/+0.1 | u rotation faithful->luma->oklab | y dual one_sided->split->mirror | m spatial uniform<->masked");
#if ENABLE_VPAB_PROBE
	  USBSerial.println("                   vpab=[once/start,N/stop/status] | Harness-only final-byte VP A/B probe");
#endif
#ifdef K1_PIN_EVIDENCE_V1
	  USBSerial.println("        k1_pin_evidence=[status/dba,<bucket>] | Harness-only loud-pinning evidence label");
#endif
  USBSerial.println("                           vp_all=[on/off] | Enable candidate or original VP branches");
#ifdef K1_VIVID_PRECOMP_V1
	  USBSerial.println("                             vivid=[on/off] | Runtime output-stage chroma pre-comp");
	  USBSerial.println("                      vivid_level=[0.00-1.00] | Runtime vivid shortcut strength");
	  USBSerial.println("                     vivid_chroma=[0.00-1.00] | Runtime vivid chroma strength");
	  USBSerial.println("                      vivid_black=[0.00-1.00] | Runtime vivid black-depth strength");
#endif
  USBSerial.println("        vp_bloom_alpha=[0.80-1.00] | Runtime BLOOM history alpha");
  USBSerial.println("        vp_bloom_shift=[0.25-2.00] | Runtime BLOOM propagation scale");
  USBSerial.println("          vp_bloom_force_sat=[on/off] | Runtime BLOOM saturation restore");
  USBSerial.println("        vp_wave_idle_fade=[0.50-0.999] | Runtime WAVEFORM idle trail retention");
  USBSerial.println("          vp_wave_raw_margin=[1.00-3.00] | Runtime WAVEFORM raw gate margin");
  USBSerial.println("          vp_wave_peak_floor=[0.00-1.00] | Runtime WAVEFORM peak gate floor");
  USBSerial.println("          vp_wave_active_fade=[0.00-0.50] | Runtime WAVEFORM active fade penalty");
  USBSerial.println("          vp_wave_blend_gain=[0.00-4.00] | Runtime WAVEFORM chroma blend gain");
  USBSerial.println("          vp_wave_fallback=[0.00-1.00] | Runtime WAVEFORM fallback brightness");
  USBSerial.println("          vp_wave_vu_floor=[0.00-1.00] | Runtime WAVEFORM RMS/VU gate floor");
  USBSerial.println("          vp_wave_shift=[0.00-240.00] | Runtime WAVEFORM outward trail speed");
  USBSerial.println("                               set_mode=[int] | Set the mode number");
  USBSerial.println("                               photons=[0.00-1.00] | Set primary visual photons");
  USBSerial.println("                                chroma=[0.00-1.00] | Set primary visual chroma");
  USBSerial.println("                                  mood=[0.00-1.00] | Set primary visual mood");
  USBSerial.println("                     palette_mode=[on/off] | Runtime-enable primary palette mode");
  USBSerial.println("                         palette_index=[int] | Set primary gradient palette");
  USBSerial.println("          mirror_enabled=[true/false/default] | Remotely toggle lightshow mirroring");
  USBSerial.println("           reverse_order=[true/false/default] | Toggle whether image is flipped upside down before final rendering");
  USBSerial.println("                          get_mode_name=[int] | Get a mode's name by ID (index)");
  USBSerial.println("                                stream=[type] | Stream live data to a Serial Plotter.");
  USBSerial.println("                                                Options are: audio, fps, magnitudes, spectrogram, chromagram");
  USBSerial.println("led_type=['neopixel'/'neopixel_x2'/'dotstar'] | Sets which LED protocol to use, 3 wire, 4 wire, or dual-data mode");
  USBSerial.println("                 led_count=[int or 'default'] | Sets how many LEDs your display will use (native resolution is 160)");
  USBSerial.println("        led_color_order=[GRB/RGB/BGR/default] | Sets LED color ordering, default GRB");
  USBSerial.println("       led_interpolation=[true/false/default] | Toggles linear LED interpolation when running in a non-native resolution (slower)");
  USBSerial.println("                           debug=[true/false] | Enables debug mode, where functions are timed");
  USBSerial.println("                sample_rate=[hz or 'default'] | Sets the microphone sample rate");
  USBSerial.println("              note_offset=[0-32 or 'default'] | Sets the lowest note, as a positive offset from A1 (55.0Hz)");
  USBSerial.println("               square_iter=[int or 'default'] | Sets the number of times the LED output is squared (contrast)");
  USBSerial.println("         samples_per_chunk=[int or 'default'] | Sets the number of samples collected every frame");
  USBSerial.println("             sensitivity=[float or 'default'] | Sets the scaling of audio data (>1.0 is more sensitive, <1.0 is less sensitive)");
  USBSerial.println("           response_gain=[float or 'default'] | Runtime-only post-DC audio response gain for paired K1 response probes");
#ifdef K1_LOUD_GUARD_V1
  USBSerial.println("              k1_loud_guard=[on/off/status/mode0/mode1/mode2/cycle] | Loud-room guard + A/B retune matrix");
#ifdef K1_MIC_AUTO_SENSE_V1
  USBSerial.println("              mic_auto=[on/off/status/reset/shadow/live] | Slow mic auto-sense (RAM-only; purity=off)");
#endif
#endif
  USBSerial.println("          boot_animation=[true/false/default] | Enable or disable the boot animation");
  USBSerial.println("            sweet_spot_min=[int or 'default'] | Sets the minimum amplitude to be inside the 'Sweet Spot'");
  USBSerial.println("            sweet_spot_max=[int or 'default'] | Sets the maximum amplitude to be inside the 'Sweet Spot'");
  USBSerial.println("         chromagram_range=[1-80 or 'default'] | Range between 1 and 80, how many notes at the bottom of the");
  USBSerial.println("                                                spectrogram should be considered in chromagram sums");
  USBSerial.println("         standby_dimming=[true/false/default] | Toggle dimming during detected silence");
  USBSerial.println("    set_chroma_profile=[default/bass/full] | Chromagram preset (global): default=v40102 (12/60), bass=0/24, full=0/80. Reboots only if note_offset changes");
  USBSerial.println("                       bass_mode=[true/false] | (alias) Toggle bass-mode; true=bass profile, false=default. Alters note_offset and chromagram_range for bass-y tunes");
  USBSerial.println("            max_current_ma=[int or 'default'] | Sets the maximum current FastLED will attempt to limit the LED consumption to");
  USBSerial.println("      temporal_dithering=[true/false/default] | Toggle per-LED temporal dithering that simulates higher bit-depths");
  USBSerial.println("        auto_color_shift=[true/false/default] | Toggle automated color shifting based on positive spectral changes");
  USBSerial.println("     incandescent_filter=[float or 'default'] | Set the intensity of the incandescent LUT (reduces harsh blues)");
  USBSerial.println("       incandescent_mode=[true/false/default] | Force all output into monochrome and tint with 2700K incandescent color");
  USBSerial.println("               base_coat=[true/false/default] | Enable a dim gray backdrop to the LEDs (approves appearance in most modes)");
  USBSerial.println("            bulb_opacity=[float or 'default'] | Set opacity of a filter that portrays the output as 32 \"bulbs\" with separation and hot spots");
  USBSerial.println("              saturation=[float or 'default'] | Sets the saturation of internal hues");
  USBSerial.println("               prism_count=[int or 'default'] | Sets the number of times the \"prism\" effect is applied");
  USBSerial.println("                         preset=[preset_name] | Sets multiple configuration options at once to match a preset theme");
  USBSerial.println("                          chromatic=[on/off] | Toggle global chromatic colour mode (former '1' hotkey)");
  USBSerial.println();
  USBSerial.println("                         -- EFFECTS QUEUE + PRESET SLOTS --");
  USBSerial.println("                          queue_mode=[on/off] | Arm-then-commit mode for [/] ,/. and slot loads ('U' hotkey)");
  USBSerial.println("                                       commit | Commit ALL armed channels in the same frame ('\\' hotkey)");
  USBSerial.println("                  transition_style=[dip/xfade] | Transition used by committed changes (default dip)");
  USBSerial.println("                   transition_dip_ms=[60-1000] | Dip-to-dark duration in ms (default 120)");
  USBSerial.println("                 transition_xfade_ms=[100-3000] | Crossfade duration in ms (default 400)");
  USBSerial.println("                    commit_quantise=[off/beat] | Hold '\\' commits for the next beat tick (2s timeout)");
  USBSerial.println("        slot_save=[1-10][,primary|secondary] | Save channel visual fields to a slot (default ACTIVE target)");
  USBSerial.println("        slot_load=[1-10][,primary|secondary] | Load slot (queue on=arm, off=apply via dip; digit hotkeys)");
  USBSerial.println("         slot_arm=[1-10][,primary|secondary] | Arm slot without committing, regardless of queue mode");
  USBSerial.println("                                    slot_list | Dump slot validity + mode/palette summary");
  USBSerial.println();
  USBSerial.println("                         -- SECONDARY LED STRIP CONTROL --");
  USBSerial.println("         secondary_enabled=[true/false] | Enable or disable the secondary LED strip");
  USBSerial.println("                 secondary_mode=[0-NUM_MODES-1] | Set mode for secondary LED strip");
  USBSerial.println("              secondary_photons=[0-1.0] | Set brightness for secondary LED strip");
  USBSerial.println("               secondary_chroma=[0-1.0] | Set chroma value for secondary LED strip");
  USBSerial.println("                 secondary_mood=[0-1.0] | Set mood value for secondary LED strip");
  USBSerial.println("            secondary_saturation=[0-1.0] | Set saturation for secondary LED strip");
  USBSerial.println("          secondary_prism_count=[0-10] | Set prism count for secondary LED strip");
  USBSerial.println("   secondary_mirror_enabled=[true/false] | Toggle mirroring on secondary LED strip");
  USBSerial.println("    secondary_reverse_order=[true/false] | Toggle image flipping on secondary LED strip");
  USBSerial.println("              secondary_base_coat=[true/false] | Enable dim backdrop on secondary LED strip");
  USBSerial.println("                  secondary_status | Display current status of secondary LED strip");
#ifdef ENABLE_GDFT_HARNESS
  USBSerial.println();
  USBSerial.println("                         -- GDFT HARNESS (item 22, harness build only) --");
  USBSerial.println("                  gdft_probe=[freq_hz] | Inject a synthetic sine; print GDFTP argmax bin / chroma / peak (no mic, no cal)");
  USBSerial.println("       gdft_sweep=[f0],[f1],[steps] | Sweep synthetic sine; one GDFTP line per step (argmax bin must rise monotonically)");
  USBSerial.println("              gdft_agc_probe[=amp] | 3-tone AGC contrast A/B; GDFTAGC line with pre/post inter-note level ratios");
#endif
#if ENABLE_DIAG_CAPTURE
  USBSerial.println();
  USBSerial.println("                         -- DIAGNOSTIC CAPTURE (harness build only) --");
  USBSerial.println("                  diag=status|clear | Show or clear the static diagnostic pool");
  USBSerial.println("                  vpab=start[,N][,metrics|bytes|both] | Capture final-byte VPAB records without render-path serial");
  USBSerial.println("                  vpab=stop|dump|frames|reset|status | Freeze, drain, clear, or inspect VPAB capture");
#endif
#ifdef ENABLE_VP_MOTION_LAB
  USBSerial.println();
  USBSerial.println("                         -- VP MOTION LAB (NON-SHIPPABLE harness only) --");
  USBSerial.println("                  vpml=play_builtin,intro_bounce | Start built-in dual-channel intro preview");
  USBSerial.println("                  vpml=play_builtin,intro_bounce_loop | Start loop-safe built-in VPML preview");
  USBSerial.println("                  vpml=play_params,<programme>,frames=N,... | Start bounded VPML parameter preview");
  USBSerial.println("                  vpml=status|stop | Inspect or stop the built-in VPML preview");
#endif
#if FEATURE_MABUTRACE
  USBSerial.println("                                        trace | Dump MabuTrace Perfetto JSON (trace_dev only)");
#endif
  tx_end();
}

void cmd_sb_query();

void cmd_reset();

// D6: destructive trio require a typed CONFIRM token. The bare/keystroke form
// is structurally unreachable (no hotkey, FORBIDDEN class) and the dispatcher
// only invokes these handlers when the CONFIRM token was supplied, so reaching
// the handler body already proves the gate passed.
void cmd_factory_reset();

void cmd_restore_defaults();

void cmd_clear_noise_cal();

void cmd_chip_id();

#if defined(K1_BOOTLOOP_GUARD_V1) && defined(K1_BOOTLOOP_INJECT)
// N2b crash-streak DEVICE-PROOF ONLY. Deliberately triggers ESP_RST_PANIC via abort()
// so the boot-loop guard counts a real crash (benign/USB/SW resets are not counted).
// Gated to env:k1_bootloop_inject_probe — no shippable env defines K1_BOOTLOOP_INJECT,
// so this command cannot exist in production. Typed-only, single-byte-forbidden.
void cmd_bootloop_inject();
#endif

void cmd_identify();

// D5: typed start_noise_cal no longer fires calibration — it prints guidance.
// N (arm) -> Y (confirm) within the silence window is the sole cal trigger.
void cmd_start_noise_cal_guidance();

void cmd_get_num_modes();

void cmd_get_mode();

void cmd_reset_reason();

void cmd_dump();

void cmd_stop();

#if FEATURE_MABUTRACE
void cmd_trace_dump();
#endif

void cmd_fps();

void cmd_led_fps();

void cmd_vp_status();

void cmd_smart_status();

void cmd_edge_status();

void cmd_event_status();

void cmd_vp_out_test();

void cmd_get_knobs();

void cmd_get_buttons();

// Effects-queue bare commands (spec §4): typed `:commit` mirrors the '\' hotkey;
// `:slot_list` dumps slot validity + mode/palette summary.
void cmd_queue_commit();

void cmd_slot_list();

// ---- the table ----
// Rows live in serial_cmd_table.def (X-macro) — the SINGLE source of truth,
// shared verbatim with the host test (scripts/regression-harness/
// row1_dispatch_table_test.cpp) so the two can never diverge. `hotkey` is 0 for
// every row: the single-byte immediate-hotkey surface is a SEPARATE runtime path
// (serial_handle_hotkey), constrained there, not by this table. This table
// governs the typed `:cmd` surface only. `input_surface` is compile-time-only
// metadata feeding the no-dangerous-keystroke static_assert.
// `constexpr` (not just `const`) so the integrity static_asserts below can read
// the table during constant evaluation. Function-pointer and string-literal
// initialisers are constant expressions; the table still lands in .rodata.
inline constexpr serial_cmd_row_t SERIAL_CMD_TABLE[] = {
#define SERIAL_CMD(name, hotkey, handler, safety_class, flags, input_surface) \
  { name, hotkey, handler, safety_class, flags, input_surface },
#include "serial_cmd_table.def"
#undef SERIAL_CMD
};

#define SERIAL_CMD_TABLE_LEN (sizeof(SERIAL_CMD_TABLE) / sizeof(SERIAL_CMD_TABLE[0]))

// ---- compile-time integrity checks (constexpr; evaluated at build time) ----
// (a) Every row must carry a handler.
constexpr bool serial_table_all_have_handlers() {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    if (SERIAL_CMD_TABLE[i].handler == nullptr) return false;
    if (SERIAL_CMD_TABLE[i].name == nullptr) return false;
  }
  return true;
}

// constexpr strcmp (the C library strcmp is not constexpr).
constexpr bool serial_cstr_eq(const char* a, const char* b) {
  while (*a && (*a == *b)) { a++; b++; }
  return *a == *b;
}

// (b) No duplicate command names.
constexpr bool serial_table_no_duplicate_names() {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    for (size_t j = i + 1; j < SERIAL_CMD_TABLE_LEN; j++) {
      if (serial_cstr_eq(SERIAL_CMD_TABLE[i].name, SERIAL_CMD_TABLE[j].name)) return false;
    }
  }
  return true;
}

// (c) THE LOAD-BEARING INVARIANT: no destructive/calibration row may carry a
//     single-byte hotkey, and no such row may be reachable as an immediate
//     hotkey. A FORBIDDEN/ARM-REQUIRED class with hotkey != 0 fails the build.
constexpr bool serial_table_no_dangerous_hotkey() {
  for (size_t i = 0; i < SERIAL_CMD_TABLE_LEN; i++) {
    const safety_class_t sc = SERIAL_CMD_TABLE[i].safety_class;
    if (sc == SC_FORBIDDEN_SINGLE_BYTE || sc == SC_ARM_REQUIRED || sc == SC_TYPED_ONLY) {
      if (SERIAL_CMD_TABLE[i].hotkey != 0) return false;
      if (SERIAL_CMD_TABLE[i].input_surface == IS_HOTKEY_IMMEDIATE ||
          SERIAL_CMD_TABLE[i].input_surface == IS_BOTH) return false;
    }
  }
  return true;
}

static_assert(serial_table_all_have_handlers(),
              "Row 1: every serial_cmd_row_t must have a non-null name and handler");
static_assert(serial_table_no_duplicate_names(),
              "Row 1: duplicate command names in SERIAL_CMD_TABLE");
static_assert(serial_table_no_dangerous_hotkey(),
              "Row 1 INVARIANT: destructive/ARM/typed-only command bound to a keystroke or BOTH surface");

// Table lookup by typed token (NUL-terminated). Returns nullptr if not present.
const serial_cmd_row_t* serial_cmd_lookup(const char* name);

// Dispatch a table row arriving via a TYPED `:cmd` (optionally `:cmd CONFIRM`).
// Applies the safety gates (D5/D6) before invoking the handler.
//  - SC_FORBIDDEN_SINGLE_BYTE: requires args == "CONFIRM"; else prints usage.
//  - SC_ARM_REQUIRED: typed form is rejected with guidance (the N/Y hotkey pair
//    is the sole trigger; this covers D5's typed start_noise_cal removal).
//  - SC_SAFE / SC_TYPED_ONLY: invoke the handler directly.
void serial_dispatch_typed_row(const serial_cmd_row_t* row, const char* args);

// ---- Stage B typed `type=value` dispatch table (R2) ----
#include "serial_typed_dispatch.h"

typedef struct {
  const char*              name;
  serial_typed_handler_t   handler;
  safety_class_t           safety_class;
  uint8_t                  flags;
} serial_typed_cmd_row_t;

inline constexpr serial_typed_cmd_row_t SERIAL_TYPED_CMD_TABLE[] = {
#define SERIAL_TYPED_CMD(name, handler, safety_class, flags) \
  { name, handler, safety_class, flags },
#include "serial_typed_cmd_table.def"
#undef SERIAL_TYPED_CMD
};
  // COMMANDS WITHOUT METADATA ###############################
  // Row 1: the bare-command vocabulary routes through the dispatch table for the
  // typed `:cmd` surface. The table enforces the safety class (D5 cal guidance,
  // D6 CONFIRM trio). Commands carrying `=value` (typed setters) fall through to
  // the metadata parser below, unchanged.
  if (strchr(command_buf, '=') == nullptr) {
    // Exact-match (no trailing token): the common case for every bare command.
    const serial_cmd_row_t* row = serial_cmd_lookup(command_buf);
    if (row != nullptr) {
      serial_dispatch_typed_row(row, "");
      return;
    }
    // Trailing space+token, e.g. `factory_reset CONFIRM`. This branch is scoped
    // to SC_FORBIDDEN_SINGLE_BYTE rows ONLY — those are the only commands that
    // take an argument (the CONFIRM token, D6). For any other head row (SAFE /
    // TYPED_ONLY / ARM_REQUIRED) a trailing token is NOT meaningful: we must NOT
    // dispatch the head and silently drop the tail (that would turn `reset now`
    // into a reboot — an unsigned delta on a disruptive command). Instead we
    // restore the buffer and fall through to the metadata parser, which ends in
    // bad_command exactly as the pre-Row-1 base did.
    char* space = strchr(command_buf, ' ');
    if (space != nullptr) {
      *space = '\0';
      const serial_cmd_row_t* head = serial_cmd_lookup(command_buf);
      if (head != nullptr && head->safety_class == SC_FORBIDDEN_SINGLE_BYTE) {
        serial_dispatch_typed_row(head, space + 1);
        *space = ' ';
        return;
      }
      *space = ' ';
      // head was non-FORBIDDEN (or unknown): fall through to metadata parser.
    }
  }

  // The legacy bare-command strcmp chain has been REMOVED — its vocabulary now
  // lives in SERIAL_CMD_TABLE (serial_cmd_table.def) and dispatches above.
  // Provenance is the git history (diff 92cfa74..HEAD) + the equivalence matrix
  // at docs/k1-refactor-2026-05/row1-command-equivalence-matrix.md.

  // COMMANDS WITH METADATA ##################################
  // Reached for any token NOT consumed by the table above: i.e. `type=value`
  // typed setters, the deprecated SECONDARY_* aliases / SECONDARY_MODE prefix,
  // and unknown tokens (which fall through to bad_command).
  {  // Commands with metadata are parsed here

    // PARSER #############################
    // Parse command type
    char command_type[32] = { 0 };
    uint8_t reading_index = 0;
    for (uint8_t i = 0; i < 32; i++) {
      reading_index++;
      if (command_buf[i] != '=') {
        command_type[i] = command_buf[i];
      } else {
        break;
      }
    }

    // Then parse command data
    char command_data[94] = { 0 };
    for (uint8_t i = 0; i < 94; i++) {
      if (command_buf[reading_index + i] != 0) {
        command_data[i] = command_buf[reading_index + i];
      } else {
        break;
      }
	    }
	    // PARSER #############################

	    if (serial_command_marks_manual_visual_control(command_type)) {
	      k1_smart_director_mark_manual_control(millis(), K1_MANUAL_REASON_SERIAL_COMMAND);
	    }

	    // Now react accordingly:

    // Set if this K1 is a MAIN Unit --------------
    if (strcmp(command_type, "vp_profile") == 0) {
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
    }

    else if (strcmp(command_type, "vp_all") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        vp_apply_profile(value ? VP_PROFILE_CANDIDATE : VP_PROFILE_ORIGINAL);
        vp_print_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    // The 4 vivid pre-comp handlers (vivid, vivid_level, vivid_chroma, vivid_black)
    // were lifted VERBATIM into serial/serial_cmd_handlers.cpp (Lane 2, S4.3 /
    // vivid slice). Each writes a VP_VIVID_* inline global — no save_config, no
    // reboot. Dispatched here once: serial_cmd_dispatch_vivid() returns true iff
    // command_type named one of them (the body ran), false to fall through.
    // Proven byte-for-byte by the Fα serial_replay golden extension.
#ifdef K1_VIVID_PRECOMP_V1
    else if (serial_cmd_dispatch_vivid(command_type, command_data)) {
      // handled by an extracted vivid handler
    }
#endif // K1_VIVID_PRECOMP_V1

    else if (strcmp(command_type, "ap_stream") == 0) {
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
    }

// tempo_stream stays INLINE here (ENABLE_TEMPO_STREAM-only gate — a different
// gate level than the AP block, so keeping it inline avoids straddling two
// gates in the dispatcher). The 11 AP-frontend-debug handlers (combined gate)
// are lifted to serial/k1_ap_capture_telemetry.{cpp,h}; bodies statement-
// identical, gates identical, production preprocesses to nothing.
#if ENABLE_TEMPO_STREAM
    else if (strcmp(command_type, "tempo_stream") == 0) {
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
    }
#endif

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    else if (serial_diag_ap_dispatch(command_type, command_data)) { }
#endif

#ifdef ENABLE_AP_STREAM
    // ap_capture=<ms> — harness-only windowed structured AP capture (parallel to the
    // boolean ap_stream toggle above; does NOT change ap_stream's debug semantics).
    else if (strcmp(command_type, "ap_capture") == 0) {
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
    }
#endif

#ifdef ENABLE_FRAME_DUMP
    // frame_dump=<metric>,<mode>,<dur_ms>,<every_n> — VP Tier B live per-frame stream
    // (emits FNV hash + energy + COM + FPS; <metric> is recorded in the start header).
    else if (strcmp(command_type, "frame_dump") == 0) {
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
    }
#endif

#ifdef ENABLE_VP_PROBE_CMD
    // vp_probe=all — run the deterministic VP output probe (12-mode roster: 11 Tier A
    // hashes + the nondet quantum row). Canonical harness command; legacy bare command
    // `vp_out_test` triggers the same machinery and remains available.
    else if (strcmp(command_type, "vp_probe") == 0) {
      if (command_data && strcmp(command_data, "all") == 0) {
        vp_run_output_probe();
      } else if (command_data && strcmp(command_data, "secondary") == 0) {
        vp_run_secondary_bleed_probe();   // item 17 — secondary bleed test (VPB)
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#ifdef ENABLE_GDFT_HARNESS
    // gdft_probe / gdft_sweep / gdft_agc_probe lifted VERBATIM into
    // serial_cmd_dispatch_gdft_harness() in serial_cmd_handlers.cpp (gated-out probe lane).
    // GATE-MATCHED: decl/def/include/call-site all behind #ifdef ENABLE_GDFT_HARNESS
    // (production-OFF). Returns true iff command_type was one of the three. Behaviour-
    // preserving — proven by oracle_serial_struct.py; the GDFTP/GDFTP5/GDFTAGC schema by
    // tests/test_gdft_harness_schema_static.py.
    else if (serial_cmd_dispatch_gdft_harness(command_type, command_data)) {
      // handled by the extracted gdft_harness dispatcher
    }
#endif

#ifdef ENABLE_MOTION_PROBE
    // mp_step=<interval_ms>,<size_px>[,<lum_0_255>] — a single point that jumps
    // size_px pixels every interval_ms (measured by millis, wraps at strip ends).
    // Live-adjustable: re-issue to change params. The harness reports the ACHIEVED
    // interval (measured millis delta) and effective px/s, NOT the requested value.
    // Apparent-motion test harness; non-shipping (motion_probe.h).
    else if (strcmp(command_type, "mp_step") == 0) {
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
    }
    // mp_flash=<a_px>,<b_px>,<gap_ms>,<lum_0_255>,<on_ms> — two-flash apparent-
    // motion primitive looping until mp_off. Each cycle: A on for on_ms, dark for
    // gap_ms (ISI), B on for on_ms, dark for gap_ms, repeat. Reports A-B
    // separation and the ACHIEVED gap_ms + cycle each onset. Non-shipping.
    else if (strcmp(command_type, "mp_flash") == 0) {
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
    }
    // mp_off — stop the probe, restore the snapshotted CONFIG, resume rendering.
    else if (strcmp(command_type, "mp_off") == 0) {
      motion_probe_off();
    }
    // mp_status — print active state, params, measured LED_FPS + frame period,
    // and last achieved timings.
    else if (strcmp(command_type, "mp_status") == 0) {
      motion_probe_status();
    }
#endif

    // ----------------------------------------------------------------------
    //  dump_raw — SPH0645 raw I2S frame dump
    // ----------------------------------------------------------------------
    //
    //  Usage:
    //    dump_raw=silence   → next chunk printed under [DUMP-SILENCE]
    //    dump_raw=tone      → next chunk printed under [DUMP-TONE-1KHZ]
    //
    //  Prints the first 32 raw 32-bit samples from i2s_samples_raw as
    //  zero-padded hex, framed by [DUMP-*] / [DUMP-END] tags. One-shot —
    //  the flag (raw_dump_request, declared in i2s_audio.h) auto-clears
    //  after the next acquire_sample_chunk call fires the dump.
    //
    //  Origin — Test A, 2026-05-24 PIO toolchain migration:
    //    During the arduino-cli → PIO + arduino-esp32 3.2.0 + IDF 5.4.1
    //    migration, the SPH0645 mic's i2s_std unpacking had to be
    //    empirically verified against the datasheet's 24-bit MSB-aligned
    //    frame structure. This command captured the data that closed the
    //    last forensic gap:
    //      - silence: 32 samples clustered ~0xf924xxxx, lower 14 bits zero
    //        (matches SPH0645 18-bit effective resolution per Knowles
    //         Rev B/C Table 2), post-`>>14` DC = -6951
    //      - 1 kHz tone (afplay): clean 13-sample periodic structure at
    //        Fs=12800 = 984.6 Hz, amplitude in 18-bit signal range
    //    Decode integrity end-to-end PASS — slot_mask=LEFT + ws_pol=true
    //    correctly places the 24-bit data in bits [31..8] under IDF 5.4.1.
    //
    //  Why kept (not stripped post-migration):
    //    Doctrine Rule 4 (re-test on toolchain bumps) — preserves the
    //    measurement infrastructure for the next mic / sample-rate /
    //    driver change so the next forensic capture isn't built under
    //    fire. Cost: ~400 B flash, 1 byte RAM, zero CPU when idle.
    //    Hardware-specific (SPH0645 24-bit MSB-aligned frame); will need
    //    re-tuning if mic is swapped — that's the point.
    //
    //  Safety:
    //    ~0.5ms blocking total (32 USBSerial.printf calls, async USB CDC
    //    TX), well under the 7.5ms audio chunk window @ 12.8kHz Fs.
    //    No audio glitch risk. Manual fire only — agent must NOT
    //    auto-trigger (the dump itself is silence-agnostic, but the
    //    interpretation depends on Captain's verbal silence / tone
    //    confirmation per .claude/CLAUDE.md Calibration command policy).
    //
    //  Refs:
    //    docs/forensics/2026-05-24-stage7-handoff.md (Test A captures)
    //    Lixie-Labs/Emotiscope src/microphone.h (slot_cfg reference)
    //    ESP-IDF v5.4.1 components/hal/esp32s3/include/hal/i2s_ll.h
    //      (i2s_ll_tx_set_pdm_chan_mod doxygen — slot semantic table)
    // ----------------------------------------------------------------------
    else if (strcmp(command_type, "dump_raw") == 0) {
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
    }

    else if (strcmp(command_type, "vp_stream") == 0) {
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
    }

    else if (strcmp(command_type, "ble_stream") == 0) {
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
    }

	    else if (strcmp(command_type, "vp_perf") == 0) {
	      vp_perf_command(command_type, command_data);
	    }

	    // Extracted VERBATIM to serial_cmd_dispatch_smart_director() in
	    // serial_cmd_handlers.cpp (smart_assist / smart_switching /
	    // smart_confidence_floor / smart_scene). UNGATED. Behaviour-preserving —
	    // proven byte-for-byte by the serial_struct structural-contract gate.
	    else if (serial_cmd_dispatch_smart_director(command_type, command_data)) {
	      // handled by the extracted smart-director dispatcher
	    }

	    // Extracted VERBATIM to serial_cmd_dispatch_smart_visual() in
	    // serial_cmd_handlers.cpp (smart_hooks). UNGATED. Proven by serial_struct.
	    else if (serial_cmd_dispatch_smart_visual(command_type, command_data)) {
	      // handled by the extracted smart-visual dispatcher
	    }

	    // Extracted VERBATIM to serial_cmd_dispatch_edge_mixer() in
	    // serial_cmd_handlers.cpp (edge_enabled / edge_mode / edge_strength). UNGATED.
	    // Behaviour-preserving — proven byte-for-byte by the serial_struct gate.
	    else if (serial_cmd_dispatch_edge_mixer(command_type, command_data)) {
	      // handled by the extracted edge-mixer dispatcher
	    }

#if ENABLE_DIAG_CAPTURE
	    else if (strcmp(command_type, "diag") == 0) {
      if (strcmp(command_data, "status") == 0 || command_data[0] == 0) {
        diag_capture_print_status();
      } else if (strcmp(command_data, "clear") == 0 || strcmp(command_data, "reset") == 0) {
        diag_capture_reset();
        diag_capture_print_status();
      } else {
        bad_command(command_type, command_data);
      }
    }
#endif

#if ENABLE_VPAB_PROBE
    else if (strcmp(command_type, "vpab") == 0) {
      vpab_command(command_type, command_data);
    }
#endif

#ifdef K1_PIN_EVIDENCE_V1
    else if (strcmp(command_type, "k1_pin_evidence") == 0) {
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
    }
#endif

#ifdef ENABLE_VP_MOTION_LAB
    else if (strcmp(command_type, "vpml") == 0) {
      if (!vpml_command(command_type, command_data)) {
        bad_command(command_type, command_data);
      }
    }
#endif

    // The 17 VP-tuning handlers (vp_fix1/vp_agc_soft … vp_wave_shift) were lifted
    // VERBATIM into serial/serial_cmd_handlers.cpp (Lane 2, S4.2 / VP-tuning slice).
    // Each writes a VP inline global via vp_set_flag/float_command — no save_config,
    // no reboot. Dispatched here once: serial_cmd_dispatch_vp_tuning() returns true
    // iff command_type named one of them (the body ran), false to fall through.
    // Proven byte-for-byte by the Fα serial_replay golden extension.
    else if (serial_cmd_dispatch_vp_tuning(command_type, command_data)) {
      // handled by an extracted VP-tuning handler
    }

    // Toggle Debug Mode --------------------------------------
    else if (strcmp(command_type, "debug") == 0) {
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
    }

    // Set Mode Number + Secondary Mode -----------------------
    // set_mode + secondary_mode lifted VERBATIM into serial_cmd_dispatch_mode() in
    // serial_cmd_handlers.cpp (gated-families lane, Increment A). One call-site routes
    // both (UNGATED); returns true iff command_type was one of them. secondary_mode's
    // dispatch hoists here from its old position below — else-if order is immaterial
    // (unique command_type strings, no fallthrough). Behaviour-preserving — proven by
    // the structural-contract golden (oracle_serial_struct).
    else if (serial_cmd_dispatch_mode(command_type, command_data)) {
      // handled by the extracted set_mode / secondary_mode dispatcher
    }

    // Get Mode Name By ID ------------------------------------
    else if (strcmp(command_type, "get_mode_name") == 0) {
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
    }

    // The 23 PURE CONFIG setters (parse -> CONFIG write -> save_config[_delayed]
    // -> echo; no reboot, no subsystem coupling) were lifted VERBATIM into
    // serial/serial_cmd_handlers.cpp (Lane 2, S4 / Unit H first slice). Dispatched
    // here once: serial_cmd_dispatch_pure_setter() returns true iff command_type
    // named one of them (the body ran), false to fall through to the remaining
    // ladder branches below. Branch order within Stage B is immaterial (each tests
    // a unique command_type string), so hoisting the 23 into one call preserves
    // behaviour — proven byte-for-byte by the S3.0 serial_replay golden.
    else if (serial_cmd_dispatch_pure_setter(command_type, command_data)) {
      // handled by an extracted pure setter
    }

    // The 7 CLEAN reboot-bearing CONFIG setters (parse -> CONFIG write ->
    // save_config() [IMMEDIATE] -> echo -> reboot(); no conditional/subsystem
    // coupling) were lifted VERBATIM into serial/serial_cmd_handlers.cpp (Lane 2,
    // S4.1 / Unit H second slice): sample_rate, note_offset, led_type, led_count,
    // led_color_order, samples_per_chunk, boot_animation. Dispatched here once:
    // serial_cmd_dispatch_reboot_setter() returns true iff command_type named one
    // of them (the body ran, including its reboot()), false to fall through to the
    // remaining ladder branches below. Branch order within Stage B is immaterial
    // (each tests a unique command_type string), so hoisting the 7 into one call
    // preserves behaviour — proven byte-for-byte by the S3.1 serial_replay golden.
    // set_chroma_profile + bass_mode (conditional reboot via apply_chroma_profile,
    // uncompilable on host) and set_mode (async) stay in this ladder, below.
    else if (serial_cmd_dispatch_reboot_setter(command_type, command_data)) {
      // handled by an extracted reboot-bearing setter
    }

    // Set runtime post-DC audio response gain ----------------
    // Extracted VERBATIM to serial_cmd_dispatch_response_gain() in
    // serial_cmd_handlers.cpp. Returns true iff command_type == "response_gain"
    // (the body ran); false to fall through to the remaining ladder branches below.
    // UNGATED. Behaviour-preserving — proven byte-for-byte by the serial_replay golden.
    else if (serial_cmd_dispatch_response_gain(command_type, command_data)) {
      // handled by the extracted response_gain dispatcher
    }

#ifdef K1_LOUD_GUARD_V1
    else if (strcmp(command_type, "k1_loud_guard") == 0) {
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
    }
#endif

    // ── Silence go-dark A/B (2026-07-10) — runtime enable + tuning, no recompile. ──
    // K1 has NO indicator LEDs; the plate is the only output. STANDBY_DIMMING ships OFF
    // (dormant); enable it here to A/B the go-dark on hardware before the default flip.
    else if (strcmp(command_type, "standby_dimming") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        CONFIG.STANDBY_DIMMING = value;
        tx_begin();
        USBSerial.print("STANDBY_DIMMING: "); USBSerial.println(value ? "on" : "off");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }
    else if (strcmp(command_type, "silence_enter") == 0) {
      SILENCE_ENTER_SSL_FRAC = (float)atof(command_data);
      tx_begin(); USBSerial.print("SILENCE_ENTER_SSL_FRAC: "); USBSerial.println(SILENCE_ENTER_SSL_FRAC, 3); tx_end();
    }
    else if (strcmp(command_type, "silence_exit") == 0) {
      SILENCE_EXIT_SSL_FRAC = (float)atof(command_data);
      tx_begin(); USBSerial.print("SILENCE_EXIT_SSL_FRAC: "); USBSerial.println(SILENCE_EXIT_SSL_FRAC, 3); tx_end();
    }
    else if (strcmp(command_type, "silence_dwell") == 0) {
      SILENCE_DWELL_MS = (uint32_t)atol(command_data);
      tx_begin(); USBSerial.print("SILENCE_DWELL_MS: "); USBSerial.println(SILENCE_DWELL_MS); tx_end();
    }
    // Raw-RMS absolute go-dark thresholds (firmware-v3 pre-gate port). Calibrate live from
    // [AP] rms_raw in a quiet room, then set enter above the floor with margin (exit > enter).
    else if (strcmp(command_type, "silence_rms_enter") == 0) {
      K1_SILENCE_RMS_ENTER = (float)atof(command_data);
      tx_begin(); USBSerial.print("K1_SILENCE_RMS_ENTER: "); USBSerial.println(K1_SILENCE_RMS_ENTER, 3); tx_end();
    }
    else if (strcmp(command_type, "silence_rms_exit") == 0) {
      K1_SILENCE_RMS_EXIT = (float)atof(command_data);
      tx_begin(); USBSerial.print("K1_SILENCE_RMS_EXIT: "); USBSerial.println(K1_SILENCE_RMS_EXIT, 3); tx_end();
    }
#ifdef K1_MIC_AUTO_SENSE_V1
    // Runtime-only mic auto-sense supervisor. Never persists; never fires noise cal.
    else if (strcmp(command_type, "mic_auto") == 0) {
      if (strcmp(command_data, "status") == 0) {
        tx_begin();
        serial_print_k1_mic_auto_status();
        tx_end();
      } else if (strcmp(command_data, "reset") == 0) {
        k1_mic_auto_sense_reset(millis());
        tx_begin();
        serial_print_k1_mic_auto_status();
        tx_end();
      } else if (strcmp(command_data, "shadow") == 0) {
        k1_mic_auto_sense_set_shadow(true);
        tx_begin();
        serial_print_k1_mic_auto_status();
        tx_end();
      } else if (strcmp(command_data, "live") == 0) {
        k1_mic_auto_sense_set_shadow(false);
        tx_begin();
        serial_print_k1_mic_auto_status();
        tx_end();
      } else {
        bool value = false;
        if (vp_parse_bool(command_data, &value)) {
          k1_mic_auto_sense_set_enabled(value);
          tx_begin();
          serial_print_k1_mic_auto_status();
          tx_end();
        } else {
          bad_command(command_type, command_data);
        }
      }
    }
#endif

#ifdef K1_EFFECT_FRAMEWORK_V1
    // beat_director toggle lifted VERBATIM into serial_cmd_dispatch_beat_director() in
    // serial_cmd_handlers.cpp (gated-families lane, Increment B). GATE-MATCHED: decl/def/
    // call-site all behind #ifdef K1_EFFECT_FRAMEWORK_V1 (production-OFF). Returns true iff
    // command_type == "beat_director". Behaviour-preserving — proven by oracle_serial_struct.
    else if (serial_cmd_dispatch_beat_director(command_type, command_data)) {
      // handled by the extracted beat_director dispatcher
    }
#endif  // K1_EFFECT_FRAMEWORK_V1

    // boot_animation (reboot-bearing CONFIG setter) was lifted into
    // serial/serial_cmd_handlers.cpp (S4.1) and is dispatched above via
    // serial_cmd_dispatch_reboot_setter().

    // Set Chroma Profile -----------------
    // Clean front-end for the NOTE_OFFSET + CHROMAGRAM_RANGE pair (Stage 2 items 18-20).
    // Global setting (chromagram is shared audio analysis). DEFAULT == v40102 values.
    else if (strcmp(command_type, "set_chroma_profile") == 0) {
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
    }

    // Toggle bass mode (back-compat alias for set_chroma_profile) -------------------
    else if (strcmp(command_type, "bass_mode") == 0) {
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
    }

    // Stream a given value over Serial -----------------
    else if (strcmp(command_type, "stream") == 0) {
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
    }

    // Set CONFIG preset ----------------------------
    // Extracted VERBATIM to serial_cmd_dispatch_preset() in serial_cmd_handlers.cpp:
    // the single "preset" command (5 theme names -> set_preset() + save_config_delayed()).
    // Returns true iff command_type == "preset" (the body ran); false to fall through to
    // the remaining ladder. UNGATED. Behaviour-preserving — proven byte-for-byte by the
    // serial_struct structural-contract gate (the function-call families the replay
    // oracle cannot observe).
    else if (serial_cmd_dispatch_preset(command_type, command_data)) {
      // handled by the extracted preset dispatcher
    }

    // Effects queue + preset slots (spec §4, 2026-06-11) ----------------------
    // Extracted VERBATIM to serial_cmd_dispatch_queue() in serial_cmd_handlers.cpp:
    // queue_mode / transition_style / transition_dip_ms / transition_xfade_ms /
    // commit_quantise. Returns true iff command_type named one of the five (the body
    // ran); false to fall through to the remaining ladder. UNGATED. Behaviour-
    // preserving — proven byte-for-byte by the serial_struct structural-contract gate
    // (the function-call families the replay oracle cannot observe).
    else if (serial_cmd_dispatch_queue(command_type, command_data)) {
      // handled by the extracted effects-queue / transition dispatcher
    }

    else if (strcmp(command_type, "slot_save") == 0) {
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
    }

    else if (strcmp(command_type, "slot_load") == 0 ||
             strcmp(command_type, "slot_arm") == 0) {
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
    }

    // Typed equivalents for removed digit hotkeys (zero capability loss) -----
    else if (strcmp(command_type, "chromatic") == 0) {
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
    }

    // Secondary-channel setters ----------------------------
    // Extracted VERBATIM to serial_cmd_dispatch_secondary() in serial_cmd_handlers.cpp:
    // the 14 pure inline-global setters (auto_color_shift, incandescent_mode, enabled,
    // photons, chroma, mood, saturation, prism_count, mirror_enabled, reverse_order,
    // control, palette_mode, palette_index, base_coat). Returns true iff command_type
    // named one of the 14 (the body ran); false to fall through to the remaining ladder.
    // UNGATED. Behaviour-preserving — proven byte-for-byte by the serial_replay
    // behaviour-lock. secondary_mode (below) + secondary_status stay inline.
    else if (serial_cmd_dispatch_secondary(command_type, command_data)) {
      // handled by the extracted secondary-channel setter dispatcher
    }

    else if (strcmp(command_type, "secondary_status") == 0) {
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
    }
    
    // Add backward compatibility for old commands
    else if (strcmp(command_buf, "SECONDARY_ON") == 0) {
      ENABLE_SECONDARY_LEDS = true;
      USBSerial.println("Secondary LEDs enabled");
      USBSerial.println("NOTE: This command is deprecated, please use secondary_enabled=true instead");
    }
    else if (strcmp(command_buf, "SECONDARY_OFF") == 0) {
      ENABLE_SECONDARY_LEDS = false;
      USBSerial.println("Secondary LEDs disabled");
      USBSerial.println("NOTE: This command is deprecated, please use secondary_enabled=false instead");
    }
    else if (strncmp(command_buf, "SECONDARY_MODE", 14) == 0) {
      uint8_t mode = atoi(command_buf + 15);
      if (mode < NUM_MODES) {
        SECONDARY_LIGHTSHOW_MODE = light_mode_next_enabled(mode, 1);
        USBSerial.print("Secondary mode set to: ");
        USBSerial.println(serial_mode_name(mode));
        ENABLE_SECONDARY_LEDS = true;
        USBSerial.println("NOTE: This command is deprecated, please use secondary_mode=[int] instead");
      } else {
        USBSerial.println("Invalid mode number");
      }
    }
    else if (strcmp(command_buf, "SECONDARY_STATUS") == 0) {
      USBSerial.print("Secondary LEDs: ");
      USBSerial.println(ENABLE_SECONDARY_LEDS ? "ENABLED" : "DISABLED");
      USBSerial.print("  Mode: ");
      USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
      USBSerial.print(" (");
      USBSerial.print(serial_mode_name(SECONDARY_LIGHTSHOW_MODE));
      USBSerial.println(")");
      USBSerial.print("  Photons: ");
      USBSerial.println(SECONDARY_PHOTONS);
      USBSerial.print("  Chroma: ");
      USBSerial.println(SECONDARY_CHROMA);
      USBSerial.print("  Mood: ");
      USBSerial.println(SECONDARY_MOOD);
      USBSerial.print("  Palette Mode: ");
      USBSerial.println(SECONDARY_PALETTE_MODE_ENABLED ? "ON" : "OFF");
      USBSerial.print("  Palette Index: ");
      USBSerial.print(SECONDARY_PALETTE_INDEX);
      if (SECONDARY_PALETTE_MODE_ENABLED) {
        char buffer[32];
        strcpy_P(buffer, (const char *)pgm_read_ptr(&(paletteNames[SECONDARY_PALETTE_INDEX])));
        USBSerial.print(" ("); USBSerial.print(buffer); USBSerial.println(")");
      } else {
        USBSerial.println();
      }
      USBSerial.println("NOTE: This command is deprecated, please use secondary_status instead");
    }

    // Start system benchmark -----------------------------------
    else if (strcmp(command_type, "start_benchmark") == 0) {

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

    }

    // Toggle streaming spectrogram ---------------------
    else if (strcmp(command_type, "stream_spectrogram") == 0) {
      stream_spectrogram = !stream_spectrogram;
      USBSerial.print("STREAM_SPECTROGRAM: ");
      USBSerial.println(stream_spectrogram);
    }

#define SERIAL_TYPED_CMD_TABLE_LEN (sizeof(SERIAL_TYPED_CMD_TABLE) / sizeof(SERIAL_TYPED_CMD_TABLE[0]))

constexpr bool serial_typed_table_all_have_handlers() {
  for (size_t i = 0; i < SERIAL_TYPED_CMD_TABLE_LEN; i++) {
    if (SERIAL_TYPED_CMD_TABLE[i].handler == nullptr) return false;
    if (SERIAL_TYPED_CMD_TABLE[i].name == nullptr) return false;
  }
  return true;
}

constexpr bool serial_typed_table_no_duplicate_names() {
  for (size_t i = 0; i < SERIAL_TYPED_CMD_TABLE_LEN; i++) {
    for (size_t j = i + 1; j < SERIAL_TYPED_CMD_TABLE_LEN; j++) {
      if (serial_cstr_eq(SERIAL_TYPED_CMD_TABLE[i].name, SERIAL_TYPED_CMD_TABLE[j].name)) return false;
    }
  }
  return true;
}

static_assert(serial_typed_table_all_have_handlers(),
              "Stage B: every serial_typed_cmd_row_t must have a non-null name and handler");
static_assert(serial_typed_table_no_duplicate_names(),
              "Stage B: duplicate command names in SERIAL_TYPED_CMD_TABLE");

const serial_typed_cmd_row_t* serial_typed_cmd_lookup(const char* name);
bool serial_dispatch_typed_setter(const serial_typed_cmd_row_t* row,
                                  const char* command_type,
                                  char* command_data);

// This parses a completed command to decide how to handle it
void parse_command(char* command_buf);

// Called on every frame, collects incoming characters until
// potential commands are found
void check_serial(uint32_t t_now);

// New function to send AGC debug data to serial
void stream_agc_data(uint32_t t_now);

void stream_vp_data(uint32_t t_now);

#if ENABLE_TEMPO_STREAM
// NON-SHIPPABLE INSTRUMENTATION (compile-gated; -DENABLE_TEMPO_STREAM=1 → k1_tempo_probe
// env only). Per-frame CSV of the k1_tempo event so a click-track lock can be proven by
// eye: bpm should match the click; conf should sustain >=0.30 (lock); phase should sweep
// 0->1 each beat with beat=1 at the instant. Throttled so phase stays observable. Useless
// until k1_tempo_update() is wired into the Core-0 audio loop.
#ifndef TEMPO_STREAM_INTERVAL_MS
#define TEMPO_STREAM_INTERVAL_MS 50   // ~20 Hz
#endif
void stream_tempo_data(uint32_t t_now);

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
// NON-SHIPPABLE AP front-end truth stream. NOV emits exactly once per k1_tempo
// accepted novelty sample by keying off k1_tempo's emit_count, and this function is
// called only AFTER calculate_novelty() + k1_audio_snapshot_update() +
// k1_tempo_update() in the AP loop. APDBG is deliberately throttled; the compact
// NOV stream is the replayable "territory" surface.
#ifndef APDBG_STREAM_INTERVAL_MS
#define APDBG_STREAM_INTERVAL_MS 1000
#endif
void stream_ap_frontend_debug(uint32_t t_now);
#endif
#endif

void stream_vp_perf_data(uint32_t t_now);

#endif // SERIAL_MENU_H
