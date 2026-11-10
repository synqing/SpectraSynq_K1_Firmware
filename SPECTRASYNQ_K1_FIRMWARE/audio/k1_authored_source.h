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
/* A frame whose show time is further than this from where its sequence number
 * says it should be starts a new epoch (a seek), even if seq is contiguous. */
#define K1_AUTHORED_SEEK_T_US 50000u

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

typedef enum {
  K1_AUTHORED_FRAME_APPLIED = 0,
  K1_AUTHORED_FRAME_REJECTED,  /* hz outside 30..240: not applied */
  K1_AUTHORED_FRAME_DUPLICATE  /* same sequence number as the last applied frame: dropped */
} k1_authored_frame_result_t;

/* Read-only record of what was applied. `epoch` counts playback starts and
 * seeks since boot; it changes exactly when the renderer must rebuild its
 * prepared-playback state. */
typedef struct {
  k1_authored_state_t state;
  uint32_t epoch;
  uint32_t applied_seq;
  uint64_t applied_t_us;
  uint32_t applied_ms;      /* device time the applied frame arrived */
  uint8_t applied_hz;
  uint32_t frames_applied;
  uint32_t frames_rejected;
  uint32_t frames_duplicate;
  uint32_t seq_gaps;        /* frames missing inside an epoch (gap of 1..3) */
} k1_authored_status_t;

void k1_authored_reset(void);
k1_authored_frame_result_t k1_authored_on_frame(const k1_prsm_frame_t *frame,
                                                uint32_t now_ms);
void k1_authored_tick(uint32_t now_ms);

k1_authored_state_t k1_authored_state(void);
bool k1_authored_suppresses_live_update(void);
bool k1_authored_intent(k1_authored_intent_t *out);
void k1_authored_status(k1_authored_status_t *out);

/* Map Prim8 u16 → snapshot scalars. Returns false if hz is out of range
 * (caller must reject the frame). u16 inputs are always finite. */
bool k1_authored_map_prim8(const k1_prsm_frame_t *frame, uint32_t now_ms,
                           k1_authored_intent_t *out);

#ifdef __cplusplus
}
#endif
