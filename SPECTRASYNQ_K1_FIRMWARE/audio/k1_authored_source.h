#pragma once

#include <stdint.h>
#include <stdbool.h>

#include "k1_prsm.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Source arbitration — one writer at a time to the audio snapshot.
 *
 * Freshness: a prepared frame is fresh for 50 ms (spine
 * docs/K1_SOURCE_ARBITRATION.md). Past that the source is HOLDING: no frame
 * has arrived, the last applied frame stays in the snapshot and the live
 * microphone stays out, for up to K1_AUTHORED_HOLD_MS. Only then does the
 * source hand back to the microphone.
 *
 * Why hold (change request R3-1, 10 Nov 2026): on the bench a loaded host
 * stalled USB writes for 83 to 233 ms mid-show. Handing back at 50 ms put live
 * microphone frames into the show and then restarted it (new epoch, trails
 * cleared) when the stream came back. 1000 ms covers the longest measured
 * stall four times over; it is this firmware's own number, not the USB-bridge
 * 250 ms GPIO fallback.
 *
 * Continuity: a frame continues the running epoch when its sequence number
 * moved forward by no more than K1_AUTHORED_HOLD_MS of frames at the stream
 * rate and its show time moved by the matching amount. A backward step, a
 * show time that does not match the sequence step, a change of rate, or a
 * forward step longer than the hold starts a new epoch (a seek). */

#define K1_AUTHORED_FRESHNESS_MS 50u
#define K1_AUTHORED_HOLD_MS 1000u
#define K1_AUTHORED_HZ_MIN 30u
#define K1_AUTHORED_HZ_MAX 240u
/* A frame whose show time is further than this from where its sequence number
 * says it should be starts a new epoch (a seek), even if seq is contiguous. */
#define K1_AUTHORED_SEEK_T_US 50000u

typedef enum {
  K1_SRC_STANDALONE = 0,
  K1_SRC_AUTHORED_ACQUIRE,
  K1_SRC_AUTHORED,
  K1_SRC_AUTHORED_DRAIN, /* holding the last applied frame; live stays out */
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
  uint32_t seq_gaps;        /* frames missing inside an epoch (lost on the way) */
  uint32_t holds;           /* times the stream went quiet for more than 50 ms mid-show */
} k1_authored_status_t;

void k1_authored_reset(void);
k1_authored_frame_result_t k1_authored_on_frame(const k1_prsm_frame_t *frame,
                                                uint32_t now_ms);
void k1_authored_tick(uint32_t now_ms);
/* Explicit end of the prepared show (the receiver's exit transition): hand the
 * snapshot back to the microphone now instead of holding the last frame. */
void k1_authored_release(void);

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
