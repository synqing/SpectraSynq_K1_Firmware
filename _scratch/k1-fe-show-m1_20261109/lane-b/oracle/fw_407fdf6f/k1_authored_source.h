#pragma once

#include <stdint.h>
#include <stdbool.h>

#include "k1_prsm.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Source arbitration — one writer at a time to the audio snapshot.
 * Freshness 50 ms is derived in spine docs/K1_SOURCE_ARBITRATION.md.
 * Do not copy the USB-bridge 250 ms GPIO fallback. */

#define K1_AUTHORED_FRESHNESS_MS 50u
#define K1_AUTHORED_HZ_MIN 30u
#define K1_AUTHORED_HZ_MAX 240u
#define K1_AUTHORED_SEQ_GAP_MAX 3u

typedef enum {
  K1_SRC_STANDALONE = 0,
  K1_SRC_AUTHORED_ACQUIRE,
  K1_SRC_AUTHORED,
  K1_SRC_AUTHORED_DRAIN,
  K1_SRC_RECOVERY
} k1_authored_state_t;

typedef struct {
  float vu_level;
  float peak_scaled;
  float spectral_energy;
  float novelty;
  float low_energy;
  float mid_energy;
  float high_energy;
  bool silence;
  uint32_t frame_ms;
  uint32_t seq;
  uint64_t t_us;
} k1_authored_intent_t;

void k1_authored_reset(void);
void k1_authored_on_frame(const k1_prsm_frame_t *frame, uint32_t now_ms);
void k1_authored_tick(uint32_t now_ms);

k1_authored_state_t k1_authored_state(void);
bool k1_authored_suppresses_live_update(void);
bool k1_authored_intent(k1_authored_intent_t *out);

/* Map Prim8 u16 → snapshot scalars. Returns false if hz is out of range
 * (caller must reject the frame). u16 inputs are always finite. */
bool k1_authored_map_prim8(const k1_prsm_frame_t *frame, uint32_t now_ms,
                           k1_authored_intent_t *out);

#ifdef __cplusplus
}
#endif
