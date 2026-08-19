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
#ifdef K1_BLE_REMOTED
#include "ble_remoted_central.h"
#endif
#ifdef SB_K1_SYNC_PROBE
#include "k1_sync_link.h"  // k1_sync::set_fault for the gated sync_fault command (non-shippable)
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
void serial_print_k1_mic_auto_status();
#endif

#ifdef K1_EFFECT_FRAMEWORK_V1
// beat_director serial helper — DEFINITION moved to serial/serial_menu.cpp
// (M2.1 R1 batch 4). serial_cmd_handlers.cpp already forward-declares + calls it.
void serial_print_beat_director_status();
// ---------------------------------------------------------------------------
// beat_director serial helpers (P6 eyes-on toggle — isolated, separable block)
// ---------------------------------------------------------------------------
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
// k1_edge_echo_if_coerced). Behaviour-preserving: goldens reproduce byte-for-byte.
// ---------------------------------------------------------------------------
void k1_print_edge_status();
void k1_edge_echo_if_coerced(const K1EdgeMixerConfig& requested);
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

void show_skip_command(const char* command_type, const char* command_data);

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

#ifndef K1_SERIAL_REPLAY_HOST
#include <esp_app_desc.h>
#include <esp_random.h>
#include <esp_system.h>
#endif

inline void cmd_image_id() {
  tx_begin();
  USBSerial.print("IMAGE_ID: app_elf_sha256=");
#ifndef K1_SERIAL_REPLAY_HOST
  const esp_app_desc_t* const description = esp_app_get_description();
  if (description == nullptr) {
    USBSerial.println("unavailable");
  } else {
    for (size_t index = 0; index < sizeof(description->app_elf_sha256);
         ++index) {
      USBSerial.printf(
          "%02x",
          static_cast<unsigned>(description->app_elf_sha256[index]));
    }
    USBSerial.println();
  }
#else
  USBSerial.println("unavailable");
#endif
  tx_end();
}

inline void cmd_runtime_id() {
#ifndef K1_SERIAL_REPLAY_HOST
  static const uint32_t boot_nonce_hi = esp_random();
  static const uint32_t boot_nonce_lo = esp_random();
#endif
  tx_begin();
  char line[128];
#ifndef K1_SERIAL_REPLAY_HOST
  const int written = snprintf(
      line, sizeof(line),
      "RUNTIME_ID: boot_nonce=%08lx%08lx uptime_ms=%lu reset_reason=%d\n",
      static_cast<unsigned long>(boot_nonce_hi),
      static_cast<unsigned long>(boot_nonce_lo),
      static_cast<unsigned long>(millis()),
      static_cast<int>(esp_reset_reason()));
#else
  const int written = snprintf(
      line, sizeof(line),
      "RUNTIME_ID: boot_nonce=0000000000000000 uptime_ms=0 reset_reason=0\n");
#endif
  if (written > 0 && static_cast<size_t>(written) < sizeof(line)) {
    USBSerial.print(line);
  } else {
    USBSerial.println("RUNTIME_ID: ERROR format_overflow");
  }
  tx_end();
}

#ifdef K1_BLE_REMOTED
inline void cmd_dial_status() {
  k1_ble_remoted_status();
}
#endif

void cmd_help();

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

void cmd_save_show();

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
