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

#endif // SERIAL_CMD_HANDLERS_H
