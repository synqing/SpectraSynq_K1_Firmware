#include "k1_authored_source.h"

#include <string.h>

static k1_authored_state_t s_state = K1_SRC_STANDALONE;
static k1_authored_intent_t s_intent;
static bool s_have_intent = false;
static uint32_t s_last_prsm_ms = 0;
static uint32_t s_last_seq = 0;
static bool s_have_seq = false;

void k1_authored_reset(void) {
  s_state = K1_SRC_STANDALONE;
  memset(&s_intent, 0, sizeof(s_intent));
  s_have_intent = false;
  s_last_prsm_ms = 0;
  s_last_seq = 0;
  s_have_seq = false;
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

static bool seq_acceptable(uint32_t seq) {
  if (!s_have_seq) return true;
  if (seq == s_last_seq + 1) return true;
  /* Seek / reconnect: large gap or reset. Acquire rather than mix. */
  const uint32_t forward = seq - s_last_seq;
  if (seq > s_last_seq && forward <= K1_AUTHORED_SEQ_GAP_MAX) return true;
  return false; /* treat as new stream via acquire */
}

void k1_authored_on_frame(const k1_prsm_frame_t *frame, uint32_t now_ms) {
  if (!frame) return;
  k1_authored_intent_t mapped;
  if (!k1_authored_map_prim8(frame, now_ms, &mapped)) {
    return; /* reject; do not sanitise into zeros */
  }

  const bool continuous = seq_acceptable(frame->seq);
  if (!continuous) {
    s_state = K1_SRC_AUTHORED_ACQUIRE;
  } else if (s_state == K1_SRC_STANDALONE || s_state == K1_SRC_RECOVERY) {
    s_state = K1_SRC_AUTHORED_ACQUIRE;
  }

  s_intent = mapped;
  s_have_intent = true;
  s_last_prsm_ms = now_ms;
  s_last_seq = frame->seq;
  s_have_seq = true;

  if (s_state == K1_SRC_AUTHORED_ACQUIRE || s_state == K1_SRC_AUTHORED_DRAIN) {
    s_state = K1_SRC_AUTHORED;
  } else if (s_state == K1_SRC_STANDALONE || s_state == K1_SRC_RECOVERY) {
    s_state = K1_SRC_AUTHORED;
  }
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
