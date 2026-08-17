#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include <math.h>
#include "k1_vp_audio_access.h"

// ============================================================================
// light_mode_wfhyb_k1_variants — mode-32 colour-novelty COMPARISON PACK
// (Captain 2026-08-17). Bench A/B surface, modes 33–37.
// ----------------------------------------------------------------------------
// Diagnosis (2026-08-17 palette-utilisation lane): mode 32 reads the same
// chromagram as the lively mode 7, but collapses all 12 bins into ONE palette
// coordinate — the circular-mean centroid — offset only by a double-EMA'd
// loudness walk (peak_last * 0.25), then smooths the result with a tau-0.080 s
// RGB EMA. The wake is the history of that one slowly drifting coordinate,
// which reads as a single sheet of colour. NOT an AP defect: mode 7 proves the
// chroma varies on the same silicon/track/palette.
//
// Instead of tuning one lever blind, each variant below isolates ONE
// colour-coordinate strategy on an otherwise IDENTICAL mode-32 chassis
// (presence/silence envelopes, peak EMAs, trail fade, outward scroll,
// amplitude dot, mirror — all verbatim from light_mode_waveform_hybrid_k1.cpp)
// so Captain can attribute any visual difference to the colour strategy alone
// by cycling modes on ONE flash:
//
//   33 FLUX — walk offset kicked by chroma NOVELTY (per-frame flux vs a short
//             EMA of the recent chromagram); decays tau ~2 s between changes.
//             Chord changes ride out as distinct bands; steady music drifts.
//   34 NOTE — coordinate = strongest chroma note /12 with switch hysteresis;
//             chord-root changes produce discrete palette jumps.
//   35 WIDE — parametric-only control: same centroid+loudness walk as mode 32
//             but 4x the spread (1.0) and a lighter colour EMA (tau 0.020).
//             Answers "was it just gain?".
//   36 SUM  — the mode-7 colour idiom on this chassis: colour is the SUM of
//             all 12 notes' palette samples (coordinate c/12, weight bin^2),
//             so simultaneous notes show simultaneous palette colours.
//   37 STEP — golden-ratio (0.382) palette step latched per musical event
//             (flux threshold + 180 ms refractory); holds between events so
//             each event deposits a crisp new colour band in the wake.
//
// SELECTABILITY: bodies compile in every build (light_mode_*.cpp filter) but
// light_mode_is_enabled() keeps 33–37 unselectable unless
// K1_WFHYB_M32_VARIANTS_V1 is defined (bench env k1_bench_im69d_wfhyb_fade
// only). Production cycling and the director never reach them.
// REVERT = delete this file + the enum/dispatch/name/registry rows + env flag.
// ============================================================================

// ── Chassis constants — verbatim from light_mode_waveform_hybrid_k1.cpp ─────
static const float WFVAR_MIN_DECAY_RATE   = 0.8f;
static const float WFVAR_DECAY_SCALE      = 3.5f;
static const float WFVAR_SILENCE_DECAY    = 10.0f;
static const float WFVAR_QUIET_KNEE       = 0.9f;
static const float WFVAR_SCROLL_RATE      = 405.0f;
static const int   WFVAR_MAX_SCROLL_STEP  = 8;
static const float WFVAR_DOT_GAIN         = 0.7f;
static const float WFVAR_SENSITIVITY      = 1.0f;
static const float WFVAR_BRIGHT_BOOST     = 1.5f;
static const float WFVAR_LED_SHARE        = 0.25f;
static const float WFVAR_TAU_COLOUR       = 0.080f;   // mode-32 default (FLUX/NOTE/SUM)
static const float WFVAR_TAU_PEAK1        = 0.016f;
static const float WFVAR_TAU_PEAK2        = 0.023f;
static const float WFVAR_PRESENCE_FLOOR   = 0.02f;
static const float WFVAR_TAU_PRESENCE_UP  = 0.02f;
static const float WFVAR_TAU_PRESENCE_DN  = 0.50f;
static const float WFVAR_TAU_SIL_UP       = 0.05f;
static const float WFVAR_TAU_SIL_DN       = 0.30f;

// ── Variant-specific tuning ──────────────────────────────────────────────────
static const float WFVAR_FLUX_PREV_TAU    = 0.25f;    // recent-chroma reference EMA
static const float WFVAR_FLUX_WALK_GAIN   = 0.9f;     // palette span kicked per unit flux
static const float WFVAR_FLUX_WALK_TAU    = 2.0f;     // walk relax time constant (s)
static const float WFVAR_FLUX_WALK_MAX    = 1.5f;     // wraps in the palette anyway
static const float WFVAR_NOTE_HYSTERESIS  = 0.12f;    // challenger must beat holder by this
static const float WFVAR_WIDE_HUE_SPREAD  = 1.0f;     // vs mode 32's 0.25
static const float WFVAR_WIDE_TAU_COLOUR  = 0.020f;   // vs mode 32's 0.080
static const float WFVAR_SUM_NOTE_SHARE   = 0.25f;    // per-note weight scale (kLedShare)
static const float WFVAR_STEP_SIZE        = 0.381966f; // golden-ratio conjugate: maximal spread
static const float WFVAR_STEP_FLUX_GATE   = 0.35f;    // event threshold on chroma flux
static const uint32_t WFVAR_STEP_REFRACT_MS = 180;    // min gap between steps
static const float WFVAR_STEP_TAU_COLOUR  = 0.030f;   // crisp band edges

enum WfhybVariant : uint8_t {
  WFVAR_FLUX = 0,
  WFVAR_NOTE,
  WFVAR_WIDE,
  WFVAR_SUM,
  WFVAR_STEP,
};

// Per-channel variant state. Statics (not ChannelEffectState) because the pack
// is a bench-only comparison surface; primary/secondary render on distinct
// instances selected by vp_render_secondary_channel (precedent: sat_ema pair in
// light_mode_waveform_hybrid_k1.cpp).
struct WfhybVariantState {
  float    prev_chroma[12];  // FLUX/STEP: recent-chroma EMA reference
  float    flux_walk;        // FLUX: decaying walk offset
  uint8_t  held_note;        // NOTE: current argmax holder
  float    step_u;           // STEP: latched palette coordinate
  uint32_t last_step_ms;     // STEP: refractory clock
  bool     initialised;
};
static WfhybVariantState s_wfvar_primary;
static WfhybVariantState s_wfvar_secondary;

static inline float wfvar_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static inline float wfvar_ema(float current, float target, float dt, float tau) {
  float a = 1.0f - expf(-dt / tau);
  if (!isfinite(a) || a < 0.0f) a = 0.0f;
  if (a > 1.0f) a = 1.0f;
  return current + (target - current) * a;
}

static inline float wfvar_follow(float current, float target, float dt,
                                 float tau_up, float tau_dn) {
  return wfvar_ema(current, target, dt, (target > current) ? tau_up : tau_dn);
}

// Chroma flux: positive per-frame change of the chromagram against a short EMA
// of its recent past. Updates the reference in place.
static float wfvar_chroma_flux(WfhybVariantState& vs, const float* bins, float dt) {
  float flux = 0.0f;
  const float a = 1.0f - expf(-dt / WFVAR_FLUX_PREV_TAU);
  for (uint8_t c = 0; c < 12; ++c) {
    const float d = bins[c] - vs.prev_chroma[c];
    if (d > 0.0f) flux += d;
    vs.prev_chroma[c] += d * a;
  }
  return flux;
}

static void wfhyb_variant_render(WfhybVariant variant, CRGB16* leds_prev_buffer,
                                 ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;
  WfhybVariantState& vs = render_secondary ? s_wfvar_secondary : s_wfvar_primary;

  // ---- dt (chassis verbatim) ------------------------------------------------
  const uint32_t now_ms = millis();
  float dt = (fx.wfhyb_last_ms != 0) ? float(now_ms - fx.wfhyb_last_ms) * 0.001f
                                     : (1.0f / 120.0f);
  fx.wfhyb_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;

  // ---- audio snapshot + envelopes (chassis verbatim) ------------------------
  const K1AudioSnapshot snap = k1_vp_audio_snapshot_read();
  const float peak = wfvar_clamp01(fmaxf(snap.peak_scaled, waveform_peak_scaled));
  const bool  silence = snap.silence && (peak < WFVAR_PRESENCE_FLOOR);

  const float presence_target =
      (peak > WFVAR_PRESENCE_FLOOR || snap.vu_level > WFVAR_PRESENCE_FLOOR) ? 1.0f : 0.0f;
  fx.wfhyb_hold_env = wfvar_follow(fx.wfhyb_hold_env, presence_target, dt,
                                   WFVAR_TAU_PRESENCE_UP, WFVAR_TAU_PRESENCE_DN);
  const float sil_target = silence ? 0.0f : 1.0f;
  fx.wfhyb_sil_scale = wfvar_follow(fx.wfhyb_sil_scale, sil_target, dt,
                                    WFVAR_TAU_SIL_UP, WFVAR_TAU_SIL_DN);
  const float confidence = wfvar_clamp01(fx.wfhyb_hold_env);
  const float sil_scale  = wfvar_clamp01(fx.wfhyb_sil_scale);

  fx.wfhyb_peak_ema1 = wfvar_ema(fx.wfhyb_peak_ema1, peak, dt, WFVAR_TAU_PEAK1);
  fx.wfhyb_peak_last = wfvar_ema(fx.wfhyb_peak_last, fx.wfhyb_peak_ema1, dt, WFVAR_TAU_PEAK2);

  // ---- chroma read + brightness (chassis verbatim) --------------------------
  float bins[12];
  float total_mag = 0.0f;
  float chroma_energy = 0.0f;
  for (uint8_t c = 0; c < 12; ++c) {
    bins[c] = wfvar_clamp01(float(chromagram_smooth[c]));
    chroma_energy += bins[c];
    float bright = bins[c] * bins[c] * WFVAR_BRIGHT_BOOST;
    if (bright > 1.0f) bright = 1.0f;
    total_mag += bright;
  }
  chroma_energy *= (1.0f / 12.0f);
  float bright_raw = total_mag * WFVAR_LED_SHARE;
  float bright01 = wfvar_clamp01(1.0f - expf(-bright_raw));

  // ---- seed envelope + fallback brightness (chassis verbatim) ---------------
  float blend = wfvar_clamp01(chroma_energy * VP_WAVEFORM_CHROMA_BLEND_GAIN);
  if (chroma_energy < 0.15f && peak > WFVAR_PRESENCE_FLOOR) {
    if (blend > 0.25f) blend = 0.25f;
  }
  float seed_level = peak;
  if (fx.wfhyb_peak_last > seed_level) seed_level = fx.wfhyb_peak_last;
  const float vu = wfvar_clamp01(snap.vu_level);
  if (vu > seed_level) seed_level = vu;
  seed_level = wfvar_clamp01(seed_level);
  const bool seed_active =
      (peak > WFVAR_PRESENCE_FLOOR) || (vu > WFVAR_PRESENCE_FLOOR);
  const float fallback_bright =
      seed_active ? wfvar_clamp01(seed_level * VP_WAVEFORM_FALLBACK_BRIGHTNESS) : 0.0f;

  // ==========================================================================
  // COLOUR — the ONLY stage that differs between variants
  // ==========================================================================
  const float centroid = chromagram_centroid_hue();

  if (!vs.initialised) {
    for (uint8_t c = 0; c < 12; ++c) vs.prev_chroma[c] = bins[c];
    uint8_t amax = 0;
    for (uint8_t c = 1; c < 12; ++c) if (bins[c] > bins[amax]) amax = c;
    vs.held_note = amax;
    vs.flux_walk = 0.0f;
    vs.step_u = centroid;
    vs.last_step_ms = now_ms;
    vs.initialised = true;
  }

  float u = centroid;                 // palette coordinate (wraps downstream)
  float tau_colour = WFVAR_TAU_COLOUR;

  switch (variant) {
    case WFVAR_FLUX: {
      const float flux = wfvar_chroma_flux(vs, bins, dt);
      vs.flux_walk += flux * WFVAR_FLUX_WALK_GAIN;
      vs.flux_walk *= expf(-dt / WFVAR_FLUX_WALK_TAU);
      if (vs.flux_walk > WFVAR_FLUX_WALK_MAX) vs.flux_walk = WFVAR_FLUX_WALK_MAX;
      u = centroid + vs.flux_walk;
      break;
    }
    case WFVAR_NOTE: {
      uint8_t amax = 0;
      for (uint8_t c = 1; c < 12; ++c) if (bins[c] > bins[amax]) amax = c;
      if (amax != vs.held_note &&
          bins[amax] > bins[vs.held_note] + WFVAR_NOTE_HYSTERESIS) {
        vs.held_note = amax;
      }
      u = float(vs.held_note) / 12.0f;
      break;
    }
    case WFVAR_WIDE: {
      u = centroid + fx.wfhyb_peak_last * WFVAR_WIDE_HUE_SPREAD;
      tau_colour = WFVAR_WIDE_TAU_COLOUR;
      break;
    }
    case WFVAR_SUM:
      // Colour assembled below without a single coordinate; u only steers the
      // thin-chroma fallback sample.
      break;
    case WFVAR_STEP: {
      const float flux = wfvar_chroma_flux(vs, bins, dt);
      if (flux > WFVAR_STEP_FLUX_GATE &&
          (now_ms - vs.last_step_ms) >= WFVAR_STEP_REFRACT_MS) {
        vs.step_u += WFVAR_STEP_SIZE;
        vs.step_u -= floorf(vs.step_u);
        vs.last_step_ms = now_ms;
      }
      u = vs.step_u;
      tau_colour = WFVAR_STEP_TAU_COLOUR;
      break;
    }
  }

  const bool palette_owns = render_params_palette_owns_colour(rp, render_secondary);
  CRGB16 chroma_col;
  if (palette_owns) {
    const CRGBPalette16& pal =
        cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
    if (variant == WFVAR_SUM) {
      // Mode-7 idiom: every sounding note samples the SELECTED palette at its
      // own coordinate; the wake carries their blend, so simultaneous notes
      // show simultaneous palette colours instead of one averaged hue.
      CRGB16 acc; acc.r = 0; acc.g = 0; acc.b = 0;
      for (uint8_t c = 0; c < 12; ++c) {
        float w = bins[c] * bins[c] * WFVAR_BRIGHT_BOOST;
        if (w > 1.0f) w = 1.0f;
        w *= WFVAR_SUM_NOTE_SHARE;
        if (w <= 0.001f) continue;
        const CRGB16 note_col =
            palette_manual_colour(pal, SQ15x16(float(c) / 12.0f), SQ15x16(w));
        acc.r += note_col.r;
        acc.g += note_col.g;
        acc.b += note_col.b;
      }
      chroma_col = clamp_crgb16(acc);
    } else {
      chroma_col = clamp_crgb16(
          palette_manual_colour(pal, SQ15x16(u), SQ15x16(bright01)));
    }
  } else {
    // Chromatic mode: identical to mode 32 (the proven note-sum HSV authority).
    chroma_col = effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(bright01));
  }

  // Thin-chroma / peak fallback colour (chassis idiom, coordinate = u so the
  // fallback tracks the variant's own palette position).
  CRGB16 fallback_col;
  if (palette_owns) {
    const CRGBPalette16& pal =
        cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
    fallback_col = clamp_crgb16(
        palette_manual_colour(pal, SQ15x16(u), SQ15x16(fallback_bright)));
    const float fb_max = fmaxf(fmaxf(float(fallback_col.r), float(fallback_col.g)),
                               float(fallback_col.b));
    if (fallback_bright > 0.0f && fb_max < 0.02f) {
      fallback_col = hsv(SQ15x16(rp->CHROMA), SQ15x16(rp->SATURATION), SQ15x16(fallback_bright));
    }
  } else {
    fallback_col = hsv(SQ15x16(rp->CHROMA), SQ15x16(rp->SATURATION), SQ15x16(fallback_bright));
  }

  const SQ15x16 blend_fx = SQ15x16(blend);
  const SQ15x16 inv_blend_fx = SQ15x16(1.0f - blend);
  CRGB16 raw_col;
  raw_col.r = chroma_col.r * blend_fx + fallback_col.r * inv_blend_fx;
  raw_col.g = chroma_col.g * blend_fx + fallback_col.g * inv_blend_fx;
  raw_col.b = chroma_col.b * blend_fx + fallback_col.b * inv_blend_fx;
  raw_col = clamp_crgb16(raw_col);

  // Temporal RGB EMA — variant-specific tau (chassis mechanism).
  const float a_col = 1.0f - expf(-dt / tau_colour);
  fx.wfhyb_dot_r += (float(raw_col.r) - fx.wfhyb_dot_r) * a_col;
  fx.wfhyb_dot_g += (float(raw_col.g) - fx.wfhyb_dot_g) * a_col;
  fx.wfhyb_dot_b += (float(raw_col.b) - fx.wfhyb_dot_b) * a_col;

  // ---- confidence gating (chassis verbatim) ----------------------------------
  const float quiet_factor =
      fmaxf(fminf(confidence, sil_scale), seed_active ? seed_level : 0.0f);
  float col_gain = confidence * sil_scale;
  if (seed_active && col_gain < seed_level) col_gain = seed_level;
  CRGB16 dot_col;
  dot_col.r = SQ15x16(fx.wfhyb_dot_r * col_gain);
  dot_col.g = SQ15x16(fx.wfhyb_dot_g * col_gain);
  dot_col.b = SQ15x16(fx.wfhyb_dot_b * col_gain);

  // ==========================================================================
  // TRAIL + SCROLL + DOT + FINALISE — chassis verbatim from mode 32
  // ==========================================================================
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);

  const float abs_amp = wfvar_clamp01(peak);
  float decay_rate = WFVAR_MIN_DECAY_RATE + WFVAR_DECAY_SCALE * abs_amp;
  if (quiet_factor < WFVAR_QUIET_KNEE) {
    decay_rate += WFVAR_SILENCE_DECAY * (1.0f - quiet_factor);
  }
  const SQ15x16 fade = SQ15x16(expf(-decay_rate * dt));
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }
  for (uint16_t i = 0; i < HALF; ++i) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  fx.wfhyb_scroll_accum += WFVAR_SCROLL_RATE * dt;
  int steps = int(fx.wfhyb_scroll_accum);
  fx.wfhyb_scroll_accum -= float(steps);
  if (steps > WFVAR_MAX_SCROLL_STEP) steps = WFVAR_MAX_SCROLL_STEP;
  for (int s = 0; s < steps; ++s) {
    for (int i = NATIVE_RESOLUTION - 1; i > int(HALF); --i) {
      leds_16[i] = leds_16[i - 1];
    }
    leds_16[HALF].r = 0;
    leds_16[HALF].g = 0;
    leds_16[HALF].b = 0;
  }

  float amp = fx.wfhyb_peak_last * (WFVAR_DOT_GAIN / WFVAR_SENSITIVITY);
  if (amp > 1.0f) amp = 1.0f;
  if (amp < 0.0f) amp = 0.0f;
  float pos_f = float(HALF) + amp * float(HALF);
  const float pos_max = float(NATIVE_RESOLUTION - 1);
  if (pos_f > pos_max) pos_f = pos_max;
  const int pos_i = int(pos_f);
  const float frac = pos_f - float(pos_i);
  if (pos_i >= int(HALF) && pos_i < int(NATIVE_RESOLUTION)) {
    const SQ15x16 w0 = SQ15x16(1.0f - frac);
    leds_16[pos_i].r += dot_col.r * w0;
    leds_16[pos_i].g += dot_col.g * w0;
    leds_16[pos_i].b += dot_col.b * w0;
  }
  if ((pos_i + 1) >= int(HALF) && (pos_i + 1) < int(NATIVE_RESOLUTION)) {
    const SQ15x16 w1 = SQ15x16(frac);
    leds_16[pos_i + 1].r += dot_col.r * w1;
    leds_16[pos_i + 1].g += dot_col.g * w1;
    leds_16[pos_i + 1].b += dot_col.b * w1;
  }

  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}

void light_mode_wfhyb_k1_flux(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  wfhyb_variant_render(WFVAR_FLUX, leds_prev_buffer, fx);
}

void light_mode_wfhyb_k1_note(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  wfhyb_variant_render(WFVAR_NOTE, leds_prev_buffer, fx);
}

void light_mode_wfhyb_k1_wide(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  wfhyb_variant_render(WFVAR_WIDE, leds_prev_buffer, fx);
}

void light_mode_wfhyb_k1_sum(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  wfhyb_variant_render(WFVAR_SUM, leds_prev_buffer, fx);
}

void light_mode_wfhyb_k1_step(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  wfhyb_variant_render(WFVAR_STEP, leds_prev_buffer, fx);
}
