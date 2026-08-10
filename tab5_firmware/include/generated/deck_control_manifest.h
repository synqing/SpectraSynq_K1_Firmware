/* Auto-generated — Precision Bay R1 G2 manifest stub.
 * Source sha256: d63af679b686fee4c431491b7f5342483854aeb35b3c599983cd471e75c4c9b8
 * DO NOT hand-edit; regenerate via scripts/gen_deck_control_manifest.py
 */
#ifndef DECK_CONTROL_MANIFEST_H
#define DECK_CONTROL_MANIFEST_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define DECK_MANIFEST_KEY_COUNT 7
#define DECK_MANIFEST_SHA256 "d63af679b686fee4c431491b7f5342483854aeb35b3c599983cd471e75c4c9b8"

typedef struct {
  const char* key_id;
  const char* label;
  const char* sheet_id;
  uint8_t control_count;
} DeckManifestKey;

typedef struct {
  const char* key_id;
  const char* path;
  const char* kind;
  const char* ack_policy;
} DeckManifestControl;

const DeckManifestKey* deck_manifest_keys(uint8_t* out_count);
const DeckManifestControl* deck_manifest_controls(uint8_t* out_count);
int deck_manifest_validate_runtime(void);

#ifdef __cplusplus
}
#endif

#endif /* DECK_CONTROL_MANIFEST_H */
