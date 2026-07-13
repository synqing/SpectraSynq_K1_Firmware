#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "easing.h"
#include "shockwave_math.h"
#include <math.h>

// ============================================================================
// light_mode_shockwave — LIGHT_MODE_SHOCKWAVE: pure-AGE expanding concentric
// shells (captivation-families-build-spec §2 Shockwave; 00b §5 EXPAND family).
// ----------------------------------------------------------------------------
// An onset BIRTHS a finite-lived ring at radius 0. The ring's radius is the
// time-integral of a FIXED velocity — radius(age) = vel·age = f(AGE) ONLY — so
// several shells coexist, each born / expanding / thinning / dying by AGE. This
// is the deliberate contrast to light_mode_pulse_prism, whose ring velocity is
// amplitude-coupled (vel = reach/beat_s, reach ∝ spawn_strength). pulse_prism is
// left UNTOUCHED; Shockwave tests 00b's pure-age hypothesis with zero regression.
//
// AMPLITUDE drives BRIGHTNESS / THICKNESS / spawn density — NEVER radius or
// velocity (the single most important break, 00b §4.2). The physics core lives in
// shockwave_math.h (host-unit-tested: radius ⟂ amplitude is the load-bearing
// assertion); this file does the SQ15x16 render, colour, trail, and silence gate.
//
// Colour is the ONE family broken off harmony→hue toward TIMBRE (00b §2.6): the
// palette coordinate is the spectral tilt high/(low+high), sampled per shell via
// palette_manual_colour on the SELECTED gradient — palette-bounded, no rainbow.
//
// Shared coherence contract (all obeyed): k1ease dt + asymmetric easing (no raw
// audio→pixel); eased silence gate → honest dark on silence + a breathe-not-blink
// 0.4+0.6·env floor (routed SPATIALLY via shells + a slow centre bed, so no
// 5–20 Hz global-brightness flicker); centre-origin author of the upper half
// [HALF, NATIVE_RESOLUTION) then mirror_image_downwards (origin 79/80); no heap /
// no String; hoisted colour (per shell, never per LED); < 2.0 ms/frame. Per-frame
// shell displacement is vel·dt ≈ 0.6 px @120 fps (≪ the ~28 px fusion floor), so
// the ageing redraw + persistent wake read as a liquid ripple with no sub-stepping.
// British English throughout.
// ============================================================================

static const float SHOCK_TRAIL_DECAY   = 0.10f;   // wake fade per 120fps-frame (short so shells stay crisp)
static const float SHOCK_MIN_STRENGTH  = 0.10f;   // onset gate — below this, no shell is born
static const float SHOCK_BRIGHT_FLOOR  = 0.35f;   // even a quiet onset lights a visible shell
static const float SHOCK_BRIGHT_GAIN   = 0.65f;   // loud-onset brightness headroom
static const float SHOCK_SHELL_GAIN    = 0.78f;   // peak additive weight (white-out guard)
static const float SHOCK_BED_GAIN      = 0.22f;   // breathing centre bed magnitude
static const float SHOCK_ENV_ATT_TAU   = 0.05f;   // breathe envelope attack
static const float SHOCK_ENV_REL_TAU   = 0.35f;   // breathe envelope release (>5× attack)
static const float SHOCK_SIL_ATT_TAU   = 0.05f;   // silence gate fast-in
static const float SHOCK_SIL_REL_TAU   = 0.30f;   // silence gate slow-out

static inline float shock_clamp01(float v) {
  if (!(v >= 0.0f)) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

// Slow, centre-anchored breathing bed so the plate never hard-blinks between
// onsets while music plays, and eases to honest dark in silence. Reactivity is
// spatial (a soft centre glow), and `bed` is heavily smoothed (< 3 Hz), so this
// never enters the 5–20 Hz global-brightness flicker band.
static void shock_draw_centre_bed(const RenderParams* rp, bool render_secondary,
                                  float bed, uint16_t half) {
  if (bed <= 0.01f) return;
  const CRGB16 col = effect_particle_colour(rp, render_secondary, 0.0f,
                                            SQ15x16(bed * SHOCK_BED_GAIN));
  const float reach = 4.0f + 10.0f * bed;
  for (uint16_t k = 0; k < half; k++) {
    if (float(k) > reach) break;
    const float u = float(k) / reach;
    const float w = (1.0f - u * u) * bed * SHOCK_BED_GAIN;
    if (w <= 0.008f) continue;
    const SQ15x16 weight = SQ15x16(w);
    const uint16_t idx = half + k;
    leds_16[idx].r += col.r * weight;
    leds_16[idx].g += col.g * weight;
    leds_16[idx].b += col.b * weight;
  }
}

void light_mode_shockwave(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;  // == 80; centre origin 79/80 after mirror

  // ---- dt (frame-rate independent, clamped) --------------------------------
  const float dt = k1ease::safe_dt(millis(), fx.shock_last_ms);
  const float frame = dt * 120.0f;

  // ---- audio (value-copy snapshots) ----------------------------------------
  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const K1OnsetBeatEvent ev  = k1_onset_beat_read();

  // Breathe envelope (asymmetric follower — fast attack, slow release). Drives the
  // 0.4+0.6·env brightness floor spatially, never as a raw audio→pixel pulse.
  const float env_target = shock_clamp01(0.60f * snap.vu_level + 0.40f * snap.low_energy);
  fx.shock_env = k1ease::follow(fx.shock_env, env_target, dt, SHOCK_ENV_ATT_TAU, SHOCK_ENV_REL_TAU);
  // Eased silence gate → honest dark on true silence, fast-in / slow-out.
  const float sil_target = snap.silence ? 0.0f : 1.0f;
  fx.shock_sil = k1ease::follow(fx.shock_sil, sil_target, dt, SHOCK_SIL_ATT_TAU, SHOCK_SIL_REL_TAU);
  const float env  = shock_clamp01(fx.shock_env);
  const float sil  = shock_clamp01(fx.shock_sil);
  // Breathe-not-blink floor (00b §2.7): 0.4 + 0.6·env, gated to dark by silence.
  const float gain = sil * (0.4f + 0.6f * env);
  const float bed  = env * sil;  // centre-bed presence

  // ---- trail: seed persistent wake, reactive eased fade, upper half only ----
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
  float fade_f = 1.0f - SHOCK_TRAIL_DECAY * frame * (0.85f + 0.30f * env);
  if (fade_f < 0.78f)  fade_f = 0.78f;
  if (fade_f > 0.965f) fade_f = 0.965f;
  const SQ15x16 fade = SQ15x16(fade_f);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }
  // Author the upper half [HALF, NATIVE_RESOLUTION); the lower half is
  // regenerated by mirror_image_downwards, so clear it before drawing.
  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  shock_draw_centre_bed(rp, render_secondary, bed, HALF);

  // ---- spawn a shell on a FRESH onset (amplitude → brightness/thickness) -----
  const bool fresh = (ev.event_id != fx.shock_last_event_id);
  fx.shock_last_event_id = ev.event_id;
  if (fresh && ev.onset) {
    float amp = ev.onset_strength;
    if (!(amp > 0.0f)) amp = shock_clamp01(snap.peak_scaled);  // fallback if strength unset
    amp = shock_clamp01(amp);
    if (amp >= SHOCK_MIN_STRENGTH) {
      // Choose the slot closest to death (largest age/life), or a dead slot.
      uint8_t slot = 0;
      float worst = -1.0f;
      for (uint8_t i = 0; i < SHOCK_MAX; i++) {
        const float ratio = (fx.shock_life[i] <= 0.0f)
                              ? 2.0f
                              : shockwave::ageNorm(fx.shock_age[i], fx.shock_life[i]);
        if (ratio > worst) { worst = ratio; slot = i; }
      }
      fx.shock_age[slot]    = 0.0f;
      fx.shock_life[slot]   = shockwave::DEFAULT_LIFE_S;
      fx.shock_vel[slot]    = shockwave::DEFAULT_VEL_PXS;  // FIXED — never amplitude
      fx.shock_bright[slot] = shockwave::spawnBrightness(amp, SHOCK_BRIGHT_FLOOR, SHOCK_BRIGHT_GAIN);
      fx.shock_hue[slot]    = shockwave::timbreHue(snap.low_energy, snap.high_energy);
    }
  }

  // ---- advance + draw each live shell (annulus at radius = vel·age) ----------
  // Colour is hoisted OUT of the per-LED loop: one palette sample per shell, at
  // the shell's timbre-tilt coordinate on the SELECTED gradient (palette-bounded).
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  for (uint8_t i = 0; i < SHOCK_MAX; i++) {
    if (fx.shock_life[i] <= 0.0f) continue;
    fx.shock_age[i] += dt;
    if (!shockwave::alive(fx.shock_age[i], fx.shock_life[i])) {
      fx.shock_life[i] = 0.0f;   // died exactly at age >= life
      continue;
    }

    const float r = shockwave::radius(fx.shock_age[i], fx.shock_vel[i]);
    // Amplitude → thickness: louder (brighter) shells are fatter. Radius untouched.
    const float base_th = shockwave::BASE_THICKNESS * (0.75f + 0.55f * fx.shock_bright[i]);
    const float th = shockwave::thickness(fx.shock_age[i], fx.shock_life[i], base_th);
    if ((r - th) >= float(HALF)) {   // whole annulus expanded past the strip edge
      fx.shock_life[i] = 0.0f;
      continue;
    }

    const float shell_bright = fx.shock_bright[i] * shockwave::brightEnv(fx.shock_age[i], fx.shock_life[i]) * gain;
    if (shell_bright <= 0.004f) continue;

    // One palette sample per shell (full brightness); scaled per LED below.
    const CRGB16 base_col = palette_manual_colour(pal, SQ15x16(fx.shock_hue[i]), SQ15x16(1.0));

    const float centre = float(HALF) + r;
    const int lo = int(centre - th - 1.0f);
    const int hi = int(centre + th + 1.0f);
    for (int idx = lo; idx <= hi; idx++) {
      if (idx < int(HALF) || idx >= int(NATIVE_RESOLUTION)) continue;
      const float p = shockwave::shellProfile(float(idx), centre, th);
      if (p <= 0.0f) continue;
      const float w = p * shell_bright * SHOCK_SHELL_GAIN;
      if (w <= 0.004f) continue;
      const SQ15x16 weight = SQ15x16(w);
      leds_16[idx].r += base_col.r * weight;
      leds_16[idx].g += base_col.g * weight;
      leds_16[idx].b += base_col.b * weight;
    }
  }

  // ---- finalise (persistent wake) + centre-origin mirror --------------------
  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
