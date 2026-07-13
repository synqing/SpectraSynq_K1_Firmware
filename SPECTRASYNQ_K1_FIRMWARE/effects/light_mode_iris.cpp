#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
#include "easing.h"
#include "iris_math.h"
#include <math.h>

// ============================================================================
// light_mode_iris — mode 36 LIGHT_MODE_IRIS (DILATE + recoil in place).
// ----------------------------------------------------------------------------
// The deliberately-3rd captivation engine class (00b §5 Iris row): a parametric,
// IN-PLACE, scalar-envelope membrane with NO advection. A single damped spring
// governs one radius r about the fixed plate centre (LED 79/80). The membrane is
// a luminous DISC filled from the centre out to r with a soft edge — no scroll,
// no travelling particle, no comet wake.
//
//   * IMPACT  — a fresh onset (k1_onset_beat event_id edge) sets the spring
//               TARGET = baseline + gain*onset_strength. Amplitude drives the
//               EXTENT of the bounded membrane, never the position of a moving
//               point. The underdamped spring OVERSHOOTS then RECOILS about the
//               centre — the reversing boundary is the percept a scroll cannot
//               make.
//   * BREATHE — the LIVE beat axis (k1_tempo_read().phase01) inflates the
//               baseline toward the beat and recoils after: baseline =
//               base + amp*(0.5 - 0.5*cos(2*pi*phase01)). Iris claims the beat
//               axis natively.
//   * TARGET  — between impacts the target eases back to the (breathing)
//               baseline so the membrane recoils; a fresh impact only ever
//               pushes the target OUT (max), never cuts it short.
//
// Shared coherence contract (00b §1): eased silence gate -> honest dark; a
// breathe-not-blink 0.4 + 0.6*env brightness floor (reactivity routed SPATIALLY
// via r, never as a 5-20 Hz global brightness pulse); centre-origin author of
// the upper half [HALF, NATIVE_RESOLUTION) + mirror_image_downwards;
// finalize_additive_frame(store_history=true); no heap/new/String; < 2.0 ms;
// chroma-anchored palette-bounded colour (no rainbow). British English.
// ============================================================================

// Silence / presence envelope taus (shared-contract eased gate).
static const float IRIS_TAU_SIL_UP   = 0.05f;   // signal returns -> recover fast
static const float IRIS_TAU_SIL_DN   = 0.30f;   // true silence -> darken slowly (breathe, not blink)
static const float IRIS_TAU_ENV_UP   = 0.04f;   // audio-presence envelope attack
static const float IRIS_TAU_ENV_DN   = 0.35f;   // audio-presence envelope release
static const float IRIS_PRESENCE_FLR = 0.02f;

// Beat-breathing gate: how much of BEAT_AMP is expressed, scaled by tempo
// confidence and audio presence (no phantom breathing in silence).
static const float IRIS_BREATHE_CONF_FLOOR = 0.30f;  // min share even when tempo unlocked

// Colour: chroma-anchored, subtly beat-modulated hue shimmer (palette-bounded).
static const float IRIS_HUE_BEAT     = 0.03f;   // +/- palette-position wobble across the beat

// Trail: a light eased fade so the recoiling edge reads a soft after-glow; the
// disc is re-filled every frame, so this only softens the boundary motion.
static const float IRIS_TRAIL_DECAY  = 12.0f;   // per second (tau ~83 ms)

static inline float iris_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

void light_mode_iris(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;   // == 80; centre origin

  // ---- dt (frame-rate independent, clamped) --------------------------------
  const float dt = k1ease::safe_dt(millis(), fx.iris_last_ms);

  // ---- audio (value-copy snapshots) ----------------------------------------
  const K1AudioSnapshot snap  = k1_audio_snapshot_read();
  const K1OnsetBeatEvent ev   = k1_onset_beat_read();
  const K1TempoEvent     tempo = k1_tempo_read();

  const float peak = iris_clamp01(snap.peak_scaled);
  const bool  silence = snap.silence;

  // Eased silence gate -> honest dark on true silence, fast recovery.
  const float sil_target = silence ? 0.0f : 1.0f;
  fx.iris_sil = k1ease::follow(fx.iris_sil, sil_target, dt, IRIS_TAU_SIL_UP, IRIS_TAU_SIL_DN);
  const float sil_scale = iris_clamp01(fx.iris_sil);

  // Audio-presence envelope for the breathe-not-blink floor.
  const float env_target =
      (peak > IRIS_PRESENCE_FLR || snap.vu_level > IRIS_PRESENCE_FLR)
        ? iris_clamp01(0.5f * peak + 0.5f * snap.vu_level) : 0.0f;
  fx.iris_env = k1ease::follow(fx.iris_env, env_target, dt, IRIS_TAU_ENV_UP, IRIS_TAU_ENV_DN);
  const float env = iris_clamp01(fx.iris_env);

  // ---- baseline: LIVE beat-axis breathing ----------------------------------
  // Express BEAT_AMP scaled by tempo confidence and audio presence so the plate
  // breathes with the beat when locked, and stays calm in silence.
  const float conf = iris_clamp01(tempo.confidence);
  const float breathe_gate =
      env * (IRIS_BREATHE_CONF_FLOOR + (1.0f - IRIS_BREATHE_CONF_FLOOR) * conf);
  fx.iris_baseline = iris_math::baseline(iris_math::BASE_R,
                                         iris_math::BEAT_AMP * breathe_gate,
                                         tempo.phase01);

  // ---- target: recoil toward baseline, dilate on a fresh onset -------------
  fx.iris_target = k1ease::ema(fx.iris_target, fx.iris_baseline, dt, iris_math::TARGET_RELAX_S);
  if (ev.onset && ev.event_id != fx.iris_last_event) {
    fx.iris_last_event = ev.event_id;
    const float hit = iris_math::impact_target(fx.iris_baseline,
                                               iris_math::IMPACT_GAIN,
                                               ev.onset_strength);
    if (hit > fx.iris_target) fx.iris_target = hit;   // impact only pushes OUT
  }
  fx.iris_target = iris_math::clampf(fx.iris_target, iris_math::R_MIN, iris_math::R_MAX);

  // ---- spring integrate (pure, sub-stepped) --------------------------------
  iris_math::spring_step(fx.iris_r, fx.iris_v, fx.iris_target, dt);
  const float r = iris_math::clampf(fx.iris_r, 0.0f, float(HALF));

  // ==========================================================================
  // DRAW — in-place luminous membrane, centre-origin upper half only
  // ==========================================================================
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);

  // Light eased trail fade (softens the recoiling boundary; disc is re-filled).
  const SQ15x16 fade = SQ15x16(expf(-IRIS_TRAIL_DECAY * dt));
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }
  // Author upper half [HALF, NATIVE_RESOLUTION); the lower half is regenerated
  // by mirror_image_downwards, so clear it before drawing.
  for (uint16_t i = 0; i < HALF; ++i) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  // Global brightness: honest-dark silence gate * breathe-not-blink floor.
  // Reactivity is routed SPATIALLY (through r), never as a global pulse.
  const float global_gain = iris_clamp01(sil_scale * (0.4f + 0.6f * env));

  // HOIST colour out of the per-LED loop: one chroma-anchored, beat-shimmered,
  // palette-bounded sample scaled by the global gain.
  const float hue_offset = IRIS_HUE_BEAT * (iris_math::breathe(tempo.phase01) - 0.5f);
  const CRGB16 disc_col =
      effect_particle_colour(rp, render_secondary, hue_offset, SQ15x16(global_gain));

  // Fill from centre (d==0 -> LED HALF) out to r with a soft edge. d is the
  // pixel distance from the centre-origin slot; membrane() is a pure scalar.
  const float soft = iris_math::EDGE_SOFT;
  const int hi = int(r + soft) + 1;   // last pixel the soft edge can touch
  for (uint16_t k = 0; k < HALF; ++k) {
    if (int(k) > hi) break;           // beyond the soft edge -> fully dark
    const float w = iris_math::membrane(float(k), r, soft);
    if (w <= 0.004f) continue;
    const SQ15x16 weight = SQ15x16(w);
    const uint16_t idx = HALF + k;
    leds_16[idx].r += disc_col.r * weight;
    leds_16[idx].g += disc_col.g * weight;
    leds_16[idx].b += disc_col.b * weight;
  }

  // ==========================================================================
  // FINALISE + MIRROR (store history for the soft after-glow trail)
  // ==========================================================================
  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
