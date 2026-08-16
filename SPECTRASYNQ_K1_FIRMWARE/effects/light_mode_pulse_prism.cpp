#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
#include <math.h>
#include "k1_vp_audio_access.h"

// ============================================================================
// light_mode_pulse_prism — rhythm-first centre shockwave rings for dense EDM.
// ----------------------------------------------------------------------------
// Kick/onset edges spawn outward rings; beat strength controls impact, chroma
// controls colour, and a quiet bed keeps the centre alive between impacts.
// ============================================================================

static const float PRISM_TRAIL_DECAY    = 0.075f;
static const float PRISM_LIFE_DECAY     = 0.58f;   // per second; slower so the ring front stays bright to the strip edge
static const float PRISM_RING_WIDTH     = 3.6f;
static const float PRISM_RING_GAIN      = 0.70f;
static const float PRISM_BED_ATTACK_TAU = 0.035f;
static const float PRISM_BED_REL_TAU    = 0.32f;
static const float PRISM_BED_GAIN       = 0.36f;
static const float PRISM_MIN_STRENGTH   = 0.28f;
static const float PRISM_HUE_STEP       = 0.055f;

static inline float prism_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static inline float prism_follow(float current, float target, float dt, float attack_tau, float release_tau) {
  const float tau = (target > current) ? attack_tau : release_tau;
  float a = 1.0f - expf(-dt / tau);
  if (!isfinite(a) || a < 0.0f) a = 0.0f;
  if (a > 1.0f) a = 1.0f;
  return current + (target - current) * a;
}

static void prism_draw_center_bed(const RenderParams* rp, bool render_secondary, float bed, uint16_t half) {
  if (bed <= 0.01f) return;
  const CRGB16 col = effect_particle_colour(rp, render_secondary, 0.0f, SQ15x16(bed * PRISM_BED_GAIN));
  const float reach = 5.0f + 13.0f * bed;
  for (uint16_t k = 0; k < half; k++) {
    if (float(k) > reach) break;
    const float u = float(k) / reach;
    const float w = (1.0f - u * u) * bed * PRISM_BED_GAIN;
    if (w <= 0.008f) continue;
    const SQ15x16 weight = SQ15x16(w);
    const uint16_t idx = half + k;
    leds_16[idx].r += col.r * weight;
    leds_16[idx].g += col.g * weight;
    leds_16[idx].b += col.b * weight;
  }
}

void light_mode_pulse_prism(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  const uint32_t now_ms = millis();
  float dt = (fx.prism_last_ms != 0) ? float(now_ms - fx.prism_last_ms) * 0.001f : (1.0f / 120.0f);
  fx.prism_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;
  const float frame = dt * 120.0f;

  K1AudioSnapshot snap = k1_vp_audio_snapshot_read();
  K1OnsetBeatEvent ev = k1_vp_onset_beat_read();
  K1TempoEvent tempo = k1_vp_tempo_read();

  const float beat_strength = prism_clamp01(tempo.beat_strength);
  const float beat_mod = 0.40f + 0.60f * beat_strength;
  const float bed_target = prism_clamp01(0.55f * snap.vu_level + 0.45f * snap.low_energy);
  fx.prism_bed_env = prism_follow(fx.prism_bed_env, bed_target, dt, PRISM_BED_ATTACK_TAU, PRISM_BED_REL_TAU);

  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
  float fade_f = 1.0f - PRISM_TRAIL_DECAY * frame * (0.75f + 0.25f * beat_mod);
  if (fade_f < 0.80f) fade_f = 0.80f;
  if (fade_f > 0.965f) fade_f = 0.965f;
  const SQ15x16 fade = SQ15x16(fade_f);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }
  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  prism_draw_center_bed(rp, render_secondary, fx.prism_bed_env, HALF);

  bool spawn = false;
  float spawn_strength = 0.0f;
  uint32_t kick_id = 0;
#ifdef K1_ONSET_V2
  kick_id = ev.kick_event_id;
  if (ev.kick && kick_id != fx.prism_last_kick_id) {
    spawn = true;
    spawn_strength = prism_clamp01(ev.kick_strength);
    fx.prism_last_kick_id = kick_id;
  }
  if (!spawn && ev.transient && ev.transient_strength > 0.72f && ev.transient_event_id != fx.prism_last_kick_id) {
    spawn = true;
    spawn_strength = prism_clamp01(ev.transient_strength) * 0.72f;
    fx.prism_last_kick_id = ev.transient_event_id;
  }
#else
  kick_id = ev.event_id;
  if (ev.bass_onset && kick_id != fx.prism_last_kick_id) {
    spawn = true;
    spawn_strength = prism_clamp01(ev.bass_onset_strength);
    fx.prism_last_kick_id = kick_id;
  }
#endif
  if (!spawn && tempo.locked && tempo.beat_tick && beat_strength > 0.55f) {
    spawn = true;
    spawn_strength = beat_strength * 0.62f;
  }

  if (spawn) {
    spawn_strength = spawn_strength * beat_mod;
    if (spawn_strength < PRISM_MIN_STRENGTH) spawn_strength = PRISM_MIN_STRENGTH;
    if (spawn_strength > 1.0f) spawn_strength = 1.0f;

    uint8_t slot = 0;
    float min_life = fx.prism_life[0];
    for (uint8_t i = 1; i < PRISM_RING_MAX; i++) {
      if (fx.prism_life[i] < min_life) {
        min_life = fx.prism_life[i];
        slot = i;
      }
    }

    float bpm = tempo.bpm;
    if (bpm < 70.0f) bpm = 120.0f;
    if (bpm > 190.0f) bpm = 190.0f;
    const float beat_s = 60.0f / bpm;
    // Velocity target: even a minimum-strength kick crosses the full half-strip
    // within ~one beat, so the bright ring front reaches the physical edge (159).
    const float reach = float(HALF - 2) * (0.90f + 0.10f * spawn_strength);
    fx.prism_r[slot] = 0.0f;
    fx.prism_vel[slot] = reach / beat_s;
    fx.prism_life[slot] = spawn_strength;
    fx.prism_hue[slot] = chromagram_centroid_hue() + PRISM_HUE_STEP * float(slot);
  }

  for (uint8_t i = 0; i < PRISM_RING_MAX; i++) {
    if (fx.prism_life[i] <= 0.01f) continue;
    fx.prism_r[i] += fx.prism_vel[i] * dt;
    if (fx.prism_r[i] >= float(HALF)) {
      fx.prism_life[i] = 0.0f;
      continue;
    }

    const CRGB16 col = effect_particle_colour(rp, render_secondary, fx.prism_hue[i] - chromagram_centroid_hue(), SQ15x16(fx.prism_life[i]));
    const float centre = float(HALF) + fx.prism_r[i];
    const int lo = int(centre - PRISM_RING_WIDTH - 1.0f);
    const int hi = int(centre + PRISM_RING_WIDTH + 1.0f);
    for (int idx = lo; idx <= hi; idx++) {
      if (idx < int(HALF) || idx >= int(NATIVE_RESOLUTION)) continue;
      const float d = fabsf(float(idx) - centre);
      const float u = d / PRISM_RING_WIDTH;
      if (u > 1.0f) continue;
      float w = (1.0f - u * u) * fx.prism_life[i] * PRISM_RING_GAIN;
      if (w <= 0.006f) continue;
      const SQ15x16 weight = SQ15x16(w);
      leds_16[idx].r += col.r * weight;
      leds_16[idx].g += col.g * weight;
      leds_16[idx].b += col.b * weight;
    }

    fx.prism_life[i] *= expf(-PRISM_LIFE_DECAY * dt);
  }

  finalize_additive_frame(leds_16, leds_prev_buffer, true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
