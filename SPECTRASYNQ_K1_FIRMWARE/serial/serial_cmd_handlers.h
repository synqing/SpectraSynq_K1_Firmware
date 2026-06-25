/*----------------------------------------
  SERIAL CONFIG-SETTER HANDLERS (pure + reboot-bearing CONFIG setters)
  ----------------------------------------
  Extracted verbatim from serial_menu.h parse_command() Stage-B ladder
  (Phase A Lane 2: S4 / Unit H — first slice: the 23 PURE CONFIG setters;
   S4.1 — second slice: the 7 CLEAN reboot-bearing CONFIG setters).

  A "pure" setter is the lock corpus the S3.0 serial_replay golden froze:
  parse -> CONFIG.<field> write -> save_config[_delayed]() -> echo, with NO
  reboot() and NO subsystem coupling.

  A "reboot" setter (S4.1) extends that shape with save_config() (IMMEDIATE) +
  reboot(): parse -> CONFIG.<field> write -> save_config() -> echo -> reboot().
  The S3.1 serial_replay golden extended its corpus to cover these 7 BEFORE the
  move (each captured with reboot:true + save_config:true): sample_rate,
  note_offset, led_type, led_count, led_color_order, samples_per_chunk,
  boot_animation. The other 2 of the design's 9 reboot-bearing setters
  (set_chroma_profile + bass_mode) reboot CONDITIONALLY on apply_chroma_profile()
  — an inline in led_utilities.h the host can't compile — so they stay in
  serial_menu.h's ladder and are NOT moved here. set_mode (async; save_config_delayed,
  no reboot) also stays.

  Each dispatcher preserves the original else-if ladder STRUCTURE
  (an `if (false) {} else if (strcmp(command_type, "<name>") == 0) { ... }` chain)
  so the lifted setter bodies are statement-identical to serial_menu.h@HEAD — only
  relocated. parse_command() calls each once; each returns true iff command_type
  matched one of its setters (the ladder then short-circuits), false otherwise
  (the ladder falls through to its remaining non-extracted branches and
  bad_command). Within Stage B the branch order is immaterial (each branch tests a
  unique command_type string, terminating in bad_command), so hoisting the branches
  into the dispatchers preserves behaviour.

  The S3.0/S3.1 serial_replay golden (tests/golden/serial_replay.golden.jsonl) gates
  these moves: it must reproduce byte-for-byte after the bodies relocate — that
  identity IS the proof of behaviour-preservation.
*/

#ifndef SERIAL_CMD_HANDLERS_H
#define SERIAL_CMD_HANDLERS_H

// Dispatch the 23 pure CONFIG setters. Returns true iff command_type named one of
// them (and the body ran); false to let parse_command's ladder continue. command_data
// is the raw value token (non-const to match the parse_command local buffer type).
bool serial_cmd_dispatch_pure_setter(const char* command_type, char* command_data);

// Dispatch the 7 CLEAN reboot-bearing CONFIG setters (sample_rate, note_offset,
// led_type, led_count, led_color_order, samples_per_chunk, boot_animation). Returns
// true iff command_type named one of them (and the body ran — including its reboot());
// false to let parse_command's ladder continue. Same contract as the pure dispatcher.
bool serial_cmd_dispatch_reboot_setter(const char* command_type, char* command_data);

// Dispatch the 17 production-live VP-tuning handlers (vp_fix1/vp_agc_soft,
// vp_fix2/vp_chroma_gate, vp_fix3/vp_prism_off, vp_fix4/vp_bloom_decay,
// vp_fix5/vp_hsv_source_sat, vp_secondary_clean, vp_bloom_alpha, vp_bloom_shift,
// vp_bloom_force_sat, vp_wave_idle_fade, vp_wave_raw_margin, vp_wave_peak_floor,
// vp_wave_active_fade, vp_wave_blend_gain, vp_wave_fallback, vp_wave_vu_floor,
// vp_wave_shift). Each writes a VP inline global via vp_set_flag/float_command —
// no save_config, no reboot. Returns true iff command_type named one of them;
// false to let parse_command's ladder continue. Gated by the Fα serial_replay golden.
bool serial_cmd_dispatch_vp_tuning(const char* command_type, char* command_data);

// Dispatch the response_gain handler — writes the audio_response_gain inline global
// (globals.h:48, UNGATED) via serial_clamp_float (MIN 0.25, MAX 4.0, DEFAULT 1.0).
// No save_config, no reboot, no bad_command (atof() fallback clamps garbage to MIN).
// Returns true iff command_type == "response_gain"; false to let parse_command's
// ladder continue. Gated by the Fα serial_replay golden — it must reproduce
// byte-for-byte after the body relocates from serial_menu.h's ungated ladder branch.
bool serial_cmd_dispatch_response_gain(const char* command_type, char* command_data);

// Dispatch the effects-queue / transition family (queue_mode, transition_style,
// transition_dip_ms, transition_xfade_ms, commit_quantise). Each calls the
// host-stubbed sb_queue_* subsystem (sb_effect_queue.h) — a FUNCTION-CALL family the
// replay oracle is blind to; behaviour-preservation across this verbatim lift is
// proven by the structural-contract gate (oracle_serial_struct.py), not replay.
// Returns true iff command_type named one of the five; false to let parse_command's
// ladder continue. UNGATED.
bool serial_cmd_dispatch_queue(const char* command_type, char* command_data);

// Dispatch the 4 vivid pre-comp handlers (vivid, vivid_level, vivid_chroma,
// vivid_black). Each writes VP_VIVID_* inline globals — no save_config, no reboot.
// Returns true iff command_type named one of them; false to let parse_command's
// ladder continue. Gated by the Fα serial_replay golden — it must reproduce
// byte-for-byte after the bodies relocate from serial_menu.h's SB_VIVID_PRECOMP_V1
// block (lines 2521-2574). Definition is guarded by the same flag: the dispatcher
// decl, def, and call-site all use #ifdef SB_VIVID_PRECOMP_V1 — single gate.
#ifdef SB_VIVID_PRECOMP_V1
bool serial_cmd_dispatch_vivid(const char* command_type, char* command_data);
#endif // SB_VIVID_PRECOMP_V1

#endif // SERIAL_CMD_HANDLERS_H
