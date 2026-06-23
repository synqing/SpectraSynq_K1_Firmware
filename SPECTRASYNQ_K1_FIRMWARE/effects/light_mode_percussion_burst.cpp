#include "lightshow_modes.h"
#include "sb_audio_snapshot.h"
#include "sb_onset_beat.h"
#include <math.h>

// ============================================================================
// light_mode_percussion_burst — "Percussion Burst" (mode 26): the drum kit
// spatially decomposed. Kick owns the centre, snare the mid-field, hihat the
// edges. STRICTLY EVENT-GATED: every gesture is caused by a fresh percussive
// event-id change; a dead channel renders nothing, and that is correct.
// ----------------------------------------------------------------------------
// METHOD SUMMARY (Pass 1-6, per docs/architecture/effect-decomposition):
//  P1 WHAT: three decodable particle classes — one class per drum voice, each
//     with a fixed spatial territory and a fixed palette-class colour, so the
//     viewer can read WHICH drum fired from WHERE and what colour it is.
//  P2 VERBS: Transport(fade prev frame) → Gate(event-id edges) → Arbitrate
//     (kick > snare > hihat, free-slots only, never evict live) → Spawn →
//     Integrate(pos += vel·dt; life -= dt) → Draw(streak prev→curr pos) →
//     Clamp → History → Mirror.
//  P3 LAYERS: L1 = SBOnsetBeatEvent kick/snare/hihat ids + strengths (V2);
//     L2 = fx.pburst_* pool (N=8, struct-of-arrays, no heap, no statics);
//     L3 = class territory: kick centre→edge, snare mid-field split pair,
//     hihat outer-20% alternating sparkle; L4 = fixed class palette positions
//     (0.02 warm / 0.33 mid / 0.66 high) via effect_particle_colour;
//     L5 = particle integration + gentle persistent fade-transport (trails
//     breathe, never hard-cleared); L6 = dt clamp, snap.silence hard gate,
//     dense_forge presence gate, hihat intensity cap 0.4, clamp-preserve-sat.
//  P4 LEVERS: PBURST_*_LIFE/SPEED/FADE constants below — speed×life sets each
//     class's reach; FADE sets trail hangover; HAT_CAP keeps hats as texture.
//  P5 PERCEPTION: kick = one bright fast object zooming centre→edge (the
//     anchor); snare = a mid-field crack splitting both ways; hihat = dim,
//     short, alternating edge ticks. Spatial grammar = the kit, decodable.
//  P6 PRINCIPLES REUSED: event-id dedup (Comet §5.9); pool with NO eviction
//     of live slots — the pulse_prism lesson: multi-spawn against a small
//     pool starves/recycles live particles, so max ONE spawn per class per
//     frame plus a total occupancy guard; additive draw + fade = emergent
//     trails; fixed palette-class positions = viewer-decodable taxonomy.
// STROBE LAW: zero global amplitude writes — every gesture is a travelling /
// spatial object. ORGANIC LAW: no wall-clock oscillators — all motion is
// event-caused (spawn) or transport (fade/integration).
// State contract: persistent state ONLY in ChannelEffectState fx.pburst_*
// fields; this file has no file-scope mutable statics and no heap.
// ============================================================================

#define PBURST_MAX 8  // particle pool size (matches fx.pburst_* array length)

static const float PBURST_FADE        = 0.06f;  // trail fade per 120fps-frame (breathing persistence)
static const float PBURST_KICK_LIFE   = 0.45f;  // s — kick particle lifetime
static const float PBURST_SNARE_LIFE  = 0.35f;  // s — snare pair lifetime
static const float PBURST_HAT_LIFE    = 0.15f;  // s — hihat sparkle lifetime
static const float PBURST_KICK_SPEED  = 2.2f;   // half-strip-norm/s — fast, centre → edge in ~one life
static const float PBURST_SNARE_SPEED = 1.1f;   // half-strip-norm/s — medium, splits from mid-field
static const float PBURST_HAT_SPEED   = 0.5f;   // half-strip-norm/s — short outward drift
static const float PBURST_SNARE_POS   = 0.40f;  // snare spawn point (fraction of half-strip)
static const float PBURST_HAT_POS_A   = 0.84f;  // hihat alternating positions, outer 20%
static const float PBURST_HAT_POS_B   = 0.93f;
static const float PBURST_HAT_CAP     = 0.40f;  // LOW intensity cap — hats are texture, not flashes
static const float PBURST_HUE_KICK    = 0.02f;  // fixed palette-class positions (decodable taxonomy)
static const float PBURST_HUE_SNARE   = 0.33f;
static const float PBURST_HUE_HAT     = 0.66f;

static inline float pburst_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static inline bool pburst_presence_ok(const SBAudioSnapshot& snap) {
  // dense_forge presence gate: genuinely empty programme renders nothing new.
  return !(snap.spectral_energy < 0.08f && snap.novelty < 0.08f);
}

// Map a half-strip-normalised position [0,1] (0 = centre, 1 = edge) onto the
// full-strip [0,1] coordinate draw_line expects (upper half; mirror folds it).
static inline float pburst_strip_norm(float half_norm) {
  if (half_norm < 0.0f) half_norm = 0.0f;
  if (half_norm > 1.0f) half_norm = 1.0f;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;
  return float(HALF + uint16_t(half_norm * float(HALF - 1))) / float(NATIVE_RESOLUTION - 1);
}

// Streak the particle from its previous to its current position (the
// dforge_streak_px pattern): additive draw_line with a minimum 1px span.
static inline void pburst_streak_px(CRGB16* layer, float pos_norm, float last_norm, CRGB16 colour) {
  SQ15x16 p0 = SQ15x16(pburst_strip_norm(last_norm));
  SQ15x16 p1 = SQ15x16(pburst_strip_norm(pos_norm));
  SQ15x16 d = fabs_fixed(p1 - p0);
  SQ15x16 min_step = SQ15x16(1.0f / float(NATIVE_RESOLUTION - 1));
  if (d < min_step) d = min_step;
  draw_line(layer, p0, p1, colour, SQ15x16(1.0f));
}

// Claim the first FREE slot (never evict a live particle — the pulse_prism
// lesson). Returns PBURST_MAX when the pool is full.
static inline uint8_t pburst_claim(ChannelEffectState& fx) {
  for (uint8_t i = 0; i < PBURST_MAX; i++) {
    if (!fx.pburst_active[i]) return i;
  }
  return PBURST_MAX;
}

static inline void pburst_spawn(ChannelEffectState& fx, uint8_t slot, float pos, float vel,
                                float life, float intensity, float hue) {
  fx.pburst_pos[slot] = pos;
  fx.pburst_last_pos[slot] = pos;
  fx.pburst_vel[slot] = vel;
  fx.pburst_life[slot] = life;
  fx.pburst_life_max[slot] = life;
  fx.pburst_intensity[slot] = intensity;
  fx.pburst_hue[slot] = hue;
  fx.pburst_active[slot] = 1;
}

void light_mode_percussion_burst(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  // ── dt (dense_forge_chord clamp discipline) ────────────────────────────────
  const uint32_t prev_ms = fx.pburst_last_ms;
  const uint32_t now_ms = millis();
  float dt = (prev_ms != 0) ? float(now_ms - prev_ms) * 0.001f : (1.0f / 120.0f);
  fx.pburst_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;
  const float frame = dt * 120.0f;

  SBAudioSnapshot snap = sb_audio_snapshot_read();
  SBOnsetBeatEvent ev = sb_onset_beat_read();

  const bool hard_gate = snap.silence;
  const bool presence_ok = pburst_presence_ok(snap);

  // ── MOTION: gentle persistent fade-transport of the previous frame ────────
  // (NOT a hard clear — trails breathe). Under the silence hard gate the
  // history is dropped and the pool is stood down: black, honestly quiet.
  if (hard_gate) {
    memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
    for (uint8_t i = 0; i < PBURST_MAX; i++) {
      fx.pburst_active[i] = 0;
      fx.pburst_life[i] = 0.0f;
    }
  } else {
    memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
    float fade_f = 1.0f - PBURST_FADE * frame;
    if (fade_f < 0.0f) fade_f = 0.0f;
    if (fade_f > 0.999f) fade_f = 0.999f;
    const SQ15x16 fade = SQ15x16(fade_f);
    for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
      leds_16[i].r *= fade;
      leds_16[i].g *= fade;
      leds_16[i].b *= fade;
    }
  }

  // ── MAPPING: event-id edge detection (consume CHANGES, never levels) ──────
  bool kick_fresh = false, snare_fresh = false, hat_fresh = false;
  float kick_s = 0.0f, snare_s = 0.0f, hat_s = 0.0f;
#ifdef SB_ONSET_V2
  if (ev.kick && ev.kick_event_id != fx.pburst_kick_id) {
    kick_fresh = true;
    kick_s = pburst_clamp01(ev.kick_strength);
  }
  fx.pburst_kick_id = ev.kick_event_id;  // cursor advances even on dropped spawns
  if (ev.snare && ev.snare_event_id != fx.pburst_snare_id) {
    snare_fresh = true;
    snare_s = pburst_clamp01(ev.snare_strength);
  }
  fx.pburst_snare_id = ev.snare_event_id;
  if (ev.hihat && ev.hihat_event_id != fx.pburst_hihat_id) {
    hat_fresh = true;
    hat_s = pburst_clamp01(ev.hihat_strength);
  }
  fx.pburst_hihat_id = ev.hihat_event_id;
#else
  // Compiling fallback without the V2 percussive channels: bass_onset drives
  // the kick path only; snare/hihat stay silent (a dead channel is correct).
  if (ev.bass_onset && ev.event_id != fx.pburst_kick_id) {
    kick_fresh = true;
    kick_s = pburst_clamp01(ev.bass_onset_strength);
  }
  fx.pburst_kick_id = ev.event_id;
#endif

  // ── ARBITER (the pulse_prism lesson): max ONE spawn per class per frame,
  // free slots only (never evict live particles), and a total occupancy
  // guard: with fewer than 2 free slots kick takes priority, snare next,
  // hihat is dropped. ───────────────────────────────────────────────────────
  if (!hard_gate && presence_ok) {
    uint8_t free_slots = 0;
    for (uint8_t i = 0; i < PBURST_MAX; i++) {
      if (!fx.pburst_active[i]) free_slots++;
    }
    const bool starved = (free_slots < 2);

    // Kick — ONE bright fast particle from the centre travelling outward.
    if (kick_fresh) {
      const uint8_t slot = pburst_claim(fx);
      if (slot < PBURST_MAX) {
        const float intensity = 0.45f + 0.55f * kick_s;  // clamped, always legible
        pburst_spawn(fx, slot, 0.0f, PBURST_KICK_SPEED, PBURST_KICK_LIFE, intensity, PBURST_HUE_KICK);
        free_slots--;
      }
    }

    // Snare — symmetric PAIR splitting outward from the mid-field spawn point
    // (one toward the edge, one toward the centre; the mirror completes the
    // physical symmetry). Dropped when starved.
    if (snare_fresh && !starved) {
      const float intensity = 0.35f + 0.45f * snare_s;
      for (uint8_t half = 0; half < 2; half++) {
        const uint8_t slot = pburst_claim(fx);
        if (slot >= PBURST_MAX) break;
        const float vel = (half == 0) ? PBURST_SNARE_SPEED : -PBURST_SNARE_SPEED;
        pburst_spawn(fx, slot, PBURST_SNARE_POS, vel, PBURST_SNARE_LIFE, intensity, PBURST_HUE_SNARE);
        if (free_slots > 0) free_slots--;
      }
    }

    // Hihat — ONE short-lived dim sparkle in the outer 20%, position alternating
    // deterministically via the toggling fx bool (no RNG). Dropped when starved.
    if (hat_fresh && !starved) {
      const uint8_t slot = pburst_claim(fx);
      if (slot < PBURST_MAX) {
        const float pos = fx.pburst_hat_left ? PBURST_HAT_POS_A : PBURST_HAT_POS_B;
        fx.pburst_hat_left = !fx.pburst_hat_left;
        float intensity = 0.15f + 0.35f * hat_s;
        if (intensity > PBURST_HAT_CAP) intensity = PBURST_HAT_CAP;
        pburst_spawn(fx, slot, pos, PBURST_HAT_SPEED, PBURST_HAT_LIFE, intensity, PBURST_HUE_HAT);
      }
    }
  }

  // ── Integrate + draw each live particle (streak prev → current pos) ───────
  if (!hard_gate) {
    const float centroid = chromagram_centroid_hue();
    for (uint8_t i = 0; i < PBURST_MAX; i++) {
      if (!fx.pburst_active[i]) continue;

      fx.pburst_last_pos[i] = fx.pburst_pos[i];
      fx.pburst_pos[i] += fx.pburst_vel[i] * dt;
      fx.pburst_life[i] -= dt;

      if (fx.pburst_life[i] <= 0.0f ||
          fx.pburst_pos[i] < 0.0f || fx.pburst_pos[i] > 1.0f) {
        fx.pburst_active[i] = 0;
        fx.pburst_life[i] = 0.0f;
        continue;
      }

      // Intensity × life envelope (linear ramp-out over the particle's life).
      const float env = (fx.pburst_life_max[i] > 0.0f)
                            ? (fx.pburst_life[i] / fx.pburst_life_max[i])
                            : 0.0f;
      const float w = pburst_clamp01(fx.pburst_intensity[i] * env);
      if (w <= 0.008f) continue;

      // Fixed palette-class position (kick warm low index / snare mid / hihat
      // high) sampled LIVE each frame; chromatic fallback handled inside.
      const CRGB16 col = effect_particle_colour(
          rp, render_secondary, fx.pburst_hue[i] - centroid, SQ15x16(w));
      pburst_streak_px(leds_16, fx.pburst_pos[i], fx.pburst_last_pos[i], col);
    }
  }

  // Lower half stays authored-black pre-mirror (pulse_prism / dense_forge idiom).
  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  // History per the reference engine: clamp + store pre-mirror frame so the
  // standard no-memcpy dispatch works (dense_forge_chord pattern).
  finalize_additive_frame(leds_16, leds_prev_buffer, true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
