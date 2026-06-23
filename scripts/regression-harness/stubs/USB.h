// stubs/USB.h — HOST-ONLY ESP32 USB CDC stub for render_replay.
// globals.h declares the USB CDC serial object (USBSerial). On host all output
// is swallowed (the harness owns stdout for the NDJSON frame stream).
// NON-SHIPPING.
#pragma once
#include <cstddef>
#include <cstdint>

class USBCDC {
 public:
  USBCDC(int = 0) {}
  void begin(unsigned long = 0) {}
  void end() {}
  operator bool() const { return true; }
  size_t available() { return 0; }
  int read() { return -1; }
  void flush() {}
  template <typename... A> size_t print(A...) { return 0; }
  template <typename... A> size_t println(A...) { return 0; }
  template <typename... A> size_t printf(A...) { return 0; }
  template <typename... A> size_t write(A...) { return 0; }
};

class ESPUSB {
 public:
  bool begin() { return true; }
  void onEvent(void*) {}
  operator bool() const { return true; }
};
