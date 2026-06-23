/*----------------------------------------
  SERIAL TX ENVELOPE (protocol framing) — implementation
  ----------------------------------------
  Bodies lifted verbatim from serial_menu.h (Phase A Lane 2, S2 / Unit B).
  Statement-identical to serial_menu.h@HEAD; declarations live in serial_tx.h.
*/

#include "serial_tx.h"

// stop_streams() resets the AP-capture telemetry active flags, but only when
// the probe gate is on. Those flags live (with external linkage) in the S1
// telemetry TU; pull its header under the SAME gate so the references resolve.
// In production (gate OFF) this header preprocesses to nothing and the
// telemetry branch of stop_streams compiles out, exactly as before.
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
#include "k1_ap_capture_telemetry.h"
#endif

// TEMPO_STREAM_ENABLED is defined (with external linkage) in serial_menu.h and
// is referenced by stop_streams under the ENABLE_TEMPO_STREAM gate. Declared
// extern here so the moved body links against the same storage (cross-TU edge:
// static -> extern, statements identical).
#if ENABLE_TEMPO_STREAM
extern bool TEMPO_STREAM_ENABLED;
#endif

void tx_begin(bool error) {
  if (error == false) {
    USBSerial.println("sbr{{");
  } else {
    USBSerial.println("sberr[[");
  }
}

void tx_end(bool error) {
  if (error == false) {
    USBSerial.println("}}");
  } else {
    USBSerial.println("]]");
  }
}

void ack() {
  USBSerial.println("SBOK");
}

void bad_command(const char* command_type, const char* command_data) {
  tx_begin(true);
  USBSerial.print("Bad command: ");
  USBSerial.print(command_type);
  if (command_data[0] != 0) {
    USBSerial.print("=");
    USBSerial.print(command_data);
  }

  USBSerial.println();
  tx_end(true);
}

void stop_streams() {
  stream_audio = false;
  stream_fps = false;
  stream_max_mags = false;
  stream_max_mags_followers = false;
  stream_magnitudes = false;
  stream_spectrogram = false;
  stream_chromagram = false;
  stream_agc_debug = false;
  AP_STREAM_ENABLED = false;
#if ENABLE_TEMPO_STREAM
  TEMPO_STREAM_ENABLED = false;
#endif
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  AP_FRONTEND_DEBUG_ENABLED = false;
  AP_NOV_CAPTURE_ACTIVE = false;
  AP_CAD_CAPTURE_ACTIVE = false;
  AP_CAD_SOAK_ACTIVE = false;
#endif
  VP_STREAM_ENABLED = false;
}

// init_serial() stays in serial_menu.h: its body uses the .ino-local
// FIRMWARE_VERSION macro and only compiles inside the .ino include context.
