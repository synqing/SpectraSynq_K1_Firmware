/* Auto-generated — Precision Bay R1 G2 manifest tables. */
#include "generated/deck_control_manifest.h"

static const DeckManifestKey kKeys[] = {
  {"F01_CALIBRATE", "CALIBRATE", "DECK_SHEET_CALIBRATE", 4},
  {"F02_EDGE", "EDGE", "DECK_SHEET_EDGE", 3},
  {"F03_RENDER", "RENDER", "DECK_SHEET_RENDER", 1},
  {"F04_SENSITIVITY", "SENSITIVITY", "DECK_SHEET_SENSITIVITY", 1},
  {"F05_SMART", "SMART", "DECK_SHEET_SMART", 1},
  {"F06_DIRECTOR", "DIRECTOR", "DECK_SHEET_DIRECTOR", 4},
  {"F07_VIVID", "VIVID", "DECK_SHEET_VIVID", 0},
};

static const DeckManifestControl kControls[] = {
  {"F01_CALIBRATE", "calibration.noise.arm", "COMMAND", "LOCAL_SEND_ONLY"},
  {"F01_CALIBRATE", "calibration.noise.confirm", "COMMAND", "LOCAL_SEND_ONLY"},
  {"F01_CALIBRATE", "calibration.noise.clear", "COMMAND", "LOCAL_SEND_ONLY"},
  {"F01_CALIBRATE", "calibration.noise.status", "COMMAND", "LOCAL_SEND_ONLY"},
  {"F02_EDGE", "edge.enabled", "BOOL", "SENT_UNCONFIRMED"},
  {"F02_EDGE", "edge.mode", "ENUM_TEXT", "SENT_UNCONFIRMED"},
  {"F02_EDGE", "edge.strength", "NUMBER", "SENT_UNCONFIRMED"},
  {"F03_RENDER", "vp.profile", "ENUM_TEXT", "SENT_UNCONFIRMED"},
  {"F04_SENSITIVITY", "global.sensitivity", "NUMBER", "SENT_UNCONFIRMED"},
  {"F05_SMART", "scene.smart", "ENUM_TEXT", "SENT_UNCONFIRMED"},
  {"F06_DIRECTOR", "director.enabled", "BOOL", "SENT_UNCONFIRMED"},
  {"F06_DIRECTOR", "director.assist", "BOOL", "SENT_UNCONFIRMED"},
  {"F06_DIRECTOR", "director.autonomy", "BOOL", "SENT_UNCONFIRMED"},
  {"F06_DIRECTOR", "director.confidence_floor", "NUMBER", "SENT_UNCONFIRMED"},
};

const DeckManifestKey* deck_manifest_keys(uint8_t* out_count)
{
  if (out_count) *out_count = (uint8_t)(sizeof(kKeys) / sizeof(kKeys[0]));
  return kKeys;
}

const DeckManifestControl* deck_manifest_controls(uint8_t* out_count)
{
  if (out_count) *out_count = (uint8_t)(sizeof(kControls) / sizeof(kControls[0]));
  return kControls;
}

int deck_manifest_validate_runtime(void)
{
  /* Embedded sha d63af679b686fee4c431491b7f5342483854aeb35b3c599983cd471e75c4c9b8 — host validator is authoritative. */
  uint8_t n = 0;
  deck_manifest_keys(&n);
  return (n == DECK_MANIFEST_KEY_COUNT) ? 0 : -1;
}
