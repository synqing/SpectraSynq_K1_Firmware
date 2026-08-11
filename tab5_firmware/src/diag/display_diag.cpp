#ifdef TAB5_DIAG_DISPLAY

#include <Arduino.h>
#include <M5Unified.h>

void setup() {
  auto cfg = M5.config();
  cfg.serial_baudrate = 115200;
  M5.begin(cfg);

  M5.Display.startWrite();
  M5.Display.fillScreen(TFT_BLACK);
  M5.Display.endWrite();

  for (int i = 0; i <= 255; i += 8) {
    M5.Display.setBrightness(i);
    delay(10);
  }

  M5.Display.setTextDatum(textdatum_t::middle_center);
  M5.Display.setTextColor(TFT_WHITE, TFT_BLACK);
  M5.Display.drawString("TAB5 Display OK", M5.Display.width()/2, M5.Display.height()/2);
}

void loop() {
  // no-op
}

#endif
