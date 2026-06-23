/*----------------------------------------
  SERIAL CONFIG-SETTER HANDLERS (pure CONFIG setters)
  ----------------------------------------
  Extracted verbatim from serial_menu.h parse_command() Stage-B ladder
  (Phase A Lane 2, S4 / Unit H — first slice: the 23 PURE CONFIG setters).

  A "pure" setter is the lock corpus the S3.0 serial_replay golden froze:
  parse -> CONFIG.<field> write -> save_config[_delayed]() -> echo, with NO
  reboot() and NO subsystem coupling. The 9 reboot-bearing setters
  (note_offset/led_type/led_count/led_color_order/samples_per_chunk/sample_rate/
  boot_animation/set_chroma_profile/bass_mode) and set_mode (async, not a pure
  synchronous CONFIG write) stay in serial_menu.h's ladder and are NOT moved here.

  serial_cmd_dispatch_pure_setter() preserves the original else-if ladder STRUCTURE
  (an `if (false) {} else if (strcmp(command_type, "<name>") == 0) { ... }` chain)
  so the lifted setter bodies are statement-identical to serial_menu.h@HEAD — only
  relocated. parse_command() calls this once; it returns true iff command_type
  matched one of the 23 pure setters (the ladder then short-circuits), false
  otherwise (the ladder falls through to its remaining non-pure branches and
  bad_command). Within Stage B the branch order is immaterial (each branch tests a
  unique command_type string, terminating in bad_command), so hoisting the 23
  branches into one dispatcher preserves behaviour.

  The S3.0 serial_replay golden (tests/golden/serial_replay.golden.jsonl) gates
  this move: it must reproduce byte-for-byte after the bodies relocate — that
  identity IS the proof of behaviour-preservation.
*/

#ifndef SERIAL_CMD_HANDLERS_H
#define SERIAL_CMD_HANDLERS_H

// Dispatch the 23 pure CONFIG setters. Returns true iff command_type named one of
// them (and the body ran); false to let parse_command's ladder continue. command_data
// is the raw value token (non-const to match the parse_command local buffer type).
bool serial_cmd_dispatch_pure_setter(const char* command_type, char* command_data);

#endif // SERIAL_CMD_HANDLERS_H
