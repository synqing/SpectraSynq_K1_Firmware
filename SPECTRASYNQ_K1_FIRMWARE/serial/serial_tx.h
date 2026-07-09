/*----------------------------------------
  SERIAL TX ENVELOPE (protocol framing)
  ----------------------------------------
  Extracted verbatim from serial_menu.h (Phase A Lane 2, S2 / Unit B).
  Owns the serial protocol envelope: the tx_begin/tx_end frame markers, the
  ack/bad_command responders, the stop_streams reset, and init_serial boot
  banner. These are PRODUCTION-ON leaf utilities (compiled into k1_hardware),
  so unlike S1 this TU is a real translation unit in every build — the moved
  bodies are statement-identical to serial_menu.h@HEAD.

  tx_begin/tx_end carry their default arguments HERE (the single source). The
  AP-capture telemetry header (k1_ap_capture_telemetry.h) now includes this
  header for those declarations instead of repeating them, so the
  "one default per TU" rule is preserved across both probe and production.
*/

#ifndef SERIAL_TX_H
#define SERIAL_TX_H

#include "globals.h"    // USBSerial, Serial, stream_* flags, AP/VP_STREAM_ENABLED, FIRMWARE_VERSION
#include "constants.h"  // K1_PASS / K1_FAIL
#include <stdint.h>

// ---- Serial protocol envelope (verbatim from serial_menu.h Unit B) ----------
// NOTE: init_serial() is intentionally NOT moved here — its body references the
// FIRMWARE_VERSION macro, which is #define'd in the .ino TU (not a header), so
// it only compiles inside the .ino include context. It stays in serial_menu.h.
void tx_begin(bool error = false);
void tx_end(bool error = false);
void ack();
void bad_command(const char* command_type, const char* command_data);
void stop_streams();

#endif // SERIAL_TX_H
