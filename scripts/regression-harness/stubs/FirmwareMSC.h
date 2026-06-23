// stubs/FirmwareMSC.h — HOST-ONLY ESP32 USB-MSC stub for render_replay.
// globals.h includes <FirmwareMSC.h> for the firmware-update mass-storage
// object; never exercised by the render path. NON-SHIPPING.
#pragma once
class FirmwareMSC {
 public:
  bool begin() { return false; }
  void end() {}
  bool onEvent(void*) { return false; }
};
