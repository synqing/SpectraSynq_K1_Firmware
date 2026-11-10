#include "k1_authored_source.h"

#include <string.h>

static k1_authored_state_t s_state = K1_SRC_STANDALONE;
static k1_authored_intent_t s_intent;
static bool s_have_intent = false;
static uint32_t s_last_prsm_ms = 0;
static uint32_t s_last_seq = 0;
static uint64_t s_last_t_us = 0;
static uint8_t s_last_hz = 0;
static bool s_have_seq = false;
static uint32_t s_epoch = 0;
static uint32_t s_frames_applied = 0;
static uint32_t s_frames_rejected = 0;
static uint32_t s_frames_duplicate = 0;
static uint32_t s_seq_gaps = 0;

void k1_authored_reset(void) {
  s_state = K1_SRC_STANDALONE;
  memset(&s_intent, 0, sizeof(s_intent));
  s_have_intent = false;
  s_last_prsm_ms = 0;
  s_last_seq = 0;
  s_last_t_us = 0;
  s_last_hz = 0;
  s_have_seq = false;
  s_epoch = 0;
  s_frames_applied = 0;
  s_frames_rejected = 0;
  s_frames_duplicate = 0;
  s_seq_gaps = 0;
}

static float u16_01(uint16_t v) {
  return (float)v / 65535.0f;
}

bool k1_authored_map_prim8(const k1_prsm_frame_t *frame, uint32_t now_ms,
                           k1_authored_intent_t *out) {
  if (!frame || !out) return false;
  if (frame->hz < K1_AUTHORED_HZ_MIN || frame->hz > K1_AUTHORED_HZ_MAX) {
    return false;
  }
  /* Prim8 order: pressure, impact, mass, momentum, heat, space, texture, gravity */
  const float pressure = u16_01(frame->prim8_u16[0]);
  const float impact = u16_01(frame->prim8_u16[1]);
  const float mass = u16_01(frame->prim8_u16[2]);
  const float momentum = u16_01(frame->prim8_u16[3]);
  const float texture = u16_01(frame->prim8_u16[6]);

  memset(out, 0, sizeof(*out));
  out->vu_level = pressure;
  out->peak_scaled = pressure;
  out->spectral_energy = pressure;
  out->novelty = impact;
  out->low_energy = mass;
  out->mid_energy = momentum;
  out->high_energy = texture;
  out->silence = (frame->prim8_u16[0] == 0 && frame->prim8_u16[1] == 0 &&
                  frame->prim8_u16[2] == 0);
  out->frame_ms = now_ms;
  out->seq = frame->seq;
  out->t_us = frame->t_us;
  return true;
}

/* True when this frame follows the last applied one on the same timeline:
 * the sequence number advanced by 1..(1 + gap) and the show time advanced by
 * the matching number of ticks. Anything else is a seek or a new stream. */
static bool frame_continues(const k1_prsm_frame_t *frame) {
  if (!s_have_seq) return false;
  const uint32_t forward = frame->seq - s_last_seq;
  if (forward == 0 || forward > 1u + K1_AUTHORED_SEQ_GAP_MAX) return false;
  if (frame->hz != s_last_hz) return false;
  const uint64_t expected = s_last_t_us + ((uint64_t)forward * 1000000u) / frame->hz;
  const uint64_t diff = (frame->t_us > expected) ? (frame->t_us - expected)
                                                 : (expected - frame->t_us);
  return diff <= K1_AUTHORED_SEEK_T_US;
}

k1_authored_frame_result_t k1_authored_on_frame(const k1_prsm_frame_t *frame,
                                                uint32_t now_ms) {
  if (!frame) return K1_AUTHORED_FRAME_REJECTED;
  k1_authored_intent_t mapped;
  if (!k1_authored_map_prim8(frame, now_ms, &mapped)) {
    s_frames_rejected++;
    return K1_AUTHORED_FRAME_REJECTED; /* reject; do not sanitise into zeros */
  }

  const bool live = (s_state == K1_SRC_STANDALONE || s_state == K1_SRC_RECOVERY);
  if (!live && s_have_seq && frame->seq == s_last_seq) {
    /* The same frame again (a repeated packet). The first copy stands. */
    s_frames_duplicate++;
    return K1_AUTHORED_FRAME_DUPLICATE;
  }

  if (live || !frame_continues(frame)) {
    /* Playback start or seek: a new epoch. The renderer rebuilds its
     * prepared-playback state from this frame on. */
    s_epoch++;
  } else if (frame->seq - s_last_seq > 1u) {
    s_seq_gaps += (frame->seq - s_last_seq) - 1u;
  }

  s_intent = mapped;
  s_have_intent = true;
  s_last_prsm_ms = now_ms;
  s_last_seq = frame->seq;
  s_last_t_us = frame->t_us;
  s_last_hz = frame->hz;
  s_have_seq = true;
  s_frames_applied++;
  s_state = K1_SRC_AUTHORED;
  return K1_AUTHORED_FRAME_APPLIED;
}

void k1_authored_tick(uint32_t now_ms) {
  if (s_state == K1_SRC_STANDALONE) return;
  if (!s_have_intent) {
    s_state = K1_SRC_STANDALONE;
    return;
  }
  const uint32_t age = now_ms - s_last_prsm_ms;
  if (age > K1_AUTHORED_FRESHNESS_MS) {
    if (s_state == K1_SRC_AUTHORED || s_state == K1_SRC_AUTHORED_DRAIN ||
        s_state == K1_SRC_AUTHORED_ACQUIRE) {
      s_state = K1_SRC_RECOVERY;
    } else if (s_state == K1_SRC_RECOVERY) {
      s_state = K1_SRC_STANDALONE;
      s_have_intent = false;
      s_have_seq = false;
    }
  }
}

k1_authored_state_t k1_authored_state(void) { return s_state; }

bool k1_authored_suppresses_live_update(void) {
  return s_state == K1_SRC_AUTHORED ||
         s_state == K1_SRC_AUTHORED_ACQUIRE ||
         s_state == K1_SRC_AUTHORED_DRAIN;
}

bool k1_authored_intent(k1_authored_intent_t *out) {
  if (!out || !s_have_intent) return false;
  if (!k1_authored_suppresses_live_update()) return false;
  *out = s_intent;
  return true;
}

void k1_authored_status(k1_authored_status_t *out) {
  if (!out) return;
  memset(out, 0, sizeof(*out));
  out->state = s_state;
  out->epoch = s_epoch;
  out->applied_seq = s_last_seq;
  out->applied_t_us = s_last_t_us;
  out->applied_ms = s_last_prsm_ms;
  out->applied_hz = s_last_hz;
  out->frames_applied = s_frames_applied;
  out->frames_rejected = s_frames_rejected;
  out->frames_duplicate = s_frames_duplicate;
  out->seq_gaps = s_seq_gaps;
}
