#include "net.h"
#include "ble_midi_transport.h"
#include "ui.h"

#include <Arduino.h>

namespace {

static UI::Snapshot gLocal;

} // namespace

namespace Net {

void init()
{
  gLocal = UI::getLocal();
  BleMidiTransport::init();
  UI::setWifiOnline(false);
  UI::setHostOnline(BleMidiTransport::ready());
  Serial.printf("[net] disabled SoftAP/OSC; transport=BLE MIDI gatt=%s\n",
                BleMidiTransport::gattAvailable() ? "hosted-nimble" : "pending");
}

void tick()
{
  BleMidiTransport::tick();
  UI::setWifiOnline(false);
  UI::setHostOnline(BleMidiTransport::ready());
}

void sendSelectEffect(int effectIndex)
{
  if (effectIndex < 0) effectIndex = 0;
  if (effectIndex > 127) effectIndex = 127;
  gLocal.effectIndex = effectIndex;
  BleMidiTransport::sendPrimaryMode(static_cast<uint8_t>(effectIndex));
}

void sendBrightness(float value)
{
  if (value < 0.0f) value = 0.0f;
  if (value > 1.0f) value = 1.0f;
  gLocal.brightness = value;
  // Canonical: primary.photons = ch0 CC14 1/33 (never CC7 — that is incandescent_filter MSB).
  BleMidiTransport::sendPrimaryPhotons(value);
}

void sendParam(uint8_t index, float v)
{
  if (v < 0.0f) v = 0.0f;
  if (v > 1.0f) v = 1.0f;

  if (index == 1) gLocal.p1 = v;
  else if (index == 2) gLocal.p2 = v;

  switch (index) {
    case 1: // deck "speed" → primary.mood
      BleMidiTransport::sendPrimaryMood(v);
      break;
    case 2: // deck "scale" → secondary.mood
      BleMidiTransport::sendSecondaryMood(v);
      break;
    case 6: // palette/hue UI → primary.palette
      BleMidiTransport::sendPrimaryPalette(BleMidiTransport::unitToMidi7(v));
      break;
    case 7: // Mirror purged from BLE/Deck 2026-08-09
      Serial.printf("[net] param index=7 rejected (mirror purged from BLE)\n");
      break;
    default:
      Serial.printf("[net] unmapped param index=%u ignored (no invented CC)\n",
                    static_cast<unsigned>(index));
      break;
  }
}

bool wifiOnline() { return false; }
bool hostOnline() { return BleMidiTransport::ready(); }

} // namespace Net
