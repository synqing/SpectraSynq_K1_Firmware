#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
#include <math.h>

// ============================================================================
// light_mode_waveform_hybrid_k1 — faithful port of firmware-v3 effect 0x1313
// "K1 Waveform Hybrid" (SbK1WaveformHybridEffect).
// ----------------------------------------------------------------------------
// This is NOT the generic waveform scroll. Its SIGNATURE is the amplitude-
// mapped BOUNCING DOT: louder audio pushes a bright sub-pixel dot further from
// centre; the dot leaves an exponentially-fading wake that scrolls outward
// (centre -> edge). Colour is a heavily EMA'd (tau 0.163 s ~= 20-frame inertia)
// chroma-anchored palette sample, giving slow organic colour drift over a fast,
// alive-every-frame dot. Faithful transcription of the source render body:
//
//   1. Colour   : contrast-squared 1.5x-boosted 12-note chroma sum -> soft-knee
//                 brightness -> chroma-anchored palette colour -> 0.163 s RGB EMA
//                 -> gated by a signal-presence / silence envelope.
//   2. Fade     : decayRate = 0.8 + 3.5*|peak|  (+10*(1-quiet) on true silence);
//                 fade = exp(-decayRate*dt); multiply the whole trail.
//   3. Scroll   : outward integer sub-pixel scroll of the wake (kBaseScrollRate
//                 150 px/s at the Captain-locked native speed 27 -> 405 px/s).
//   4. Dot      : amp = peakLast*0.7/sensitivity; posF = HALF + amp*HALF; the dot
//                 is split sub-pixel across posI / posI+1 and ADDED to the trail.
//   5. Mirror   : upper half mirrored downward (centre origin at index 80).
//
// Fork-idiom differences from the source (all documented in the handover):
//   - The source's private trailBuffer[160] is replaced by the fork's global
//     leds_16 + leds_prev_buffer with finalize_additive_frame(store_history=true)
//     — the previous finalised frame IS the persistent wake. No per-effect PSRAM
//     buffer is needed.
//   - The source pulls raw waveform samples to build wfPeakScaled/wfPeakLast; the
//     fork snapshot exposes only `peak_scaled`, so the two-stage smoothing chain
//     (tau 0.016 -> 0.023) that produced wfPeakLast is reconstructed here from
//     `peak_scaled`.
//   - The source's ControlBus audioConfidence + silentScale envelopes do not
//     exist in the fork; they are synthesised from peak/vu presence (hold) and
//     snap.silence, preserving the "hold through inter-beat gaps, dark on true
//     silence" behaviour.
//   - Colour uses the fork's chroma-anchored effect_particle_colour() (palette-
//     bounded, base hue = chromagram_centroid_hue) so it is inherently no-rainbow;
//     global PHOTONS is applied downstream, so the source's photons compensation
//     is intentionally not re-applied here.
// ============================================================================

// Trail dynamics — verbatim from SbK1WaveformHybridEffect.cpp.
static const float WFHYB_MIN_DECAY_RATE   = 0.8f;   // kMinDecayRate
static const float WFHYB_DECAY_SCALE      = 3.5f;   // kDecayScale
static const float WFHYB_SILENCE_DECAY    = 10.0f;  // +accel when quiet
static const float WFHYB_QUIET_KNEE       = 0.9f;

// Scroll — kBaseScrollRate 150 px/s at kSpeedMidpoint 10, locked to the
// Captain-calibrated native waveform speed of 27 (150 * 27/10 = 405 px/s).
static const float WFHYB_SCROLL_RATE      = 405.0f;
static const int   WFHYB_MAX_SCROLL_STEP  = 8;      // per-frame clamp

// Dot amplitude mapping — verbatim (amp = peakLast * 0.7 / sensitivity).
static const float WFHYB_DOT_GAIN         = 0.7f;
static const float WFHYB_SENSITIVITY      = 1.0f;   // source default param

// Colour synthesis — verbatim character (contrast square, 1.5x boost, 1/4 share).
static const float WFHYB_BRIGHT_BOOST     = 1.5f;
static const float WFHYB_LED_SHARE        = 0.25f;  // kLedShare (LGP tuning)
static const float WFHYB_TAU_COLOUR       = 0.080f; // temporal RGB EMA (lighter: harmony hue MOVES -> colour ribbon, not one hue)
static const float WFHYB_HUE_SPREAD       = 0.25f;  // amplitude-driven palette walk: louder/richer -> more of the selected palette displayed

// wfPeakLast reconstruction — the source's two-stage EMA (tau 0.016 -> 0.023).
static const float WFHYB_TAU_PEAK1        = 0.016f;
static const float WFHYB_TAU_PEAK2        = 0.023f;

// Signal-presence / silence envelope taus (synthesised confidence + silentScale).
static const float WFHYB_PRESENCE_FLOOR   = 0.02f;
static const float WFHYB_TAU_PRESENCE_UP  = 0.02f;
static const float WFHYB_TAU_PRESENCE_DN  = 0.50f;  // ~500 ms hold
static const float WFHYB_TAU_SIL_UP       = 0.05f;
static const float WFHYB_TAU_SIL_DN       = 0.30f;

static inline float wfhyb_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static inline float wfhyb_ema(float current, float target, float dt, float tau) {
  float a = 1.0f - expf(-dt / tau);
  if (!isfinite(a) || a < 0.0f) a = 0.0f;
  if (a > 1.0f) a = 1.0f;
  return current + (target - current) * a;
}

static inline float wfhyb_follow(float current, float target, float dt,
                                 float tau_up, float tau_dn) {
  return wfhyb_ema(current, target, dt, (target > current) ? tau_up : tau_dn);
}

void light_mode_waveform_hybrid_k1(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;  // == 80; centre origin

  // ---- dt (frame-rate independent, clamped) --------------------------------
  const uint32_t now_ms = millis();
  float dt = (fx.wfhyb_last_ms != 0) ? float(now_ms - fx.wfhyb_last_ms) * 0.001f
                                     : (1.0f / 120.0f);
  fx.wfhyb_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;

  // ---- audio (value-copy snapshots) ----------------------------------------
  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const float peak = wfhyb_clamp01(snap.peak_scaled);
  const bool  silence = snap.silence;

  // Signal-presence envelope (audioConfidence analogue): fast rise, ~500 ms
  // hold-decay so the effect does not cut during inter-beat gaps.
  const float presence_target =
      (peak > WFHYB_PRESENCE_FLOOR || snap.vu_level > WFHYB_PRESENCE_FLOOR) ? 1.0f : 0.0f;
  fx.wfhyb_hold_env = wfhyb_follow(fx.wfhyb_hold_env, presence_target, dt,
                                   WFHYB_TAU_PRESENCE_UP, WFHYB_TAU_PRESENCE_DN);
  // silentScale analogue: eases to 0 on true silence, darkening the plate.
  const float sil_target = silence ? 0.0f : 1.0f;
  fx.wfhyb_sil_scale = wfhyb_follow(fx.wfhyb_sil_scale, sil_target, dt,
                                    WFHYB_TAU_SIL_UP, WFHYB_TAU_SIL_DN);
  const float confidence = wfhyb_clamp01(fx.wfhyb_hold_env);
  const float sil_scale  = wfhyb_clamp01(fx.wfhyb_sil_scale);
  const float quiet_factor = fminf(confidence, sil_scale);

  // ---- reconstruct wfPeakLast (source's two-stage EMA tau 0.016 -> 0.023) ---
  fx.wfhyb_peak_ema1 = wfhyb_ema(fx.wfhyb_peak_ema1, peak, dt, WFHYB_TAU_PEAK1);
  fx.wfhyb_peak_last = wfhyb_ema(fx.wfhyb_peak_last, fx.wfhyb_peak_ema1, dt, WFHYB_TAU_PEAK2);

  // ==========================================================================
  // COLOUR SYNTHESIS — SB 3.0.0 parity character (chroma sum, heavy RGB EMA)
  // ==========================================================================
  float total_mag = 0.0f;
  for (uint8_t c = 0; c < 12; ++c) {
    float bin = wfhyb_clamp01(float(chromagram_smooth[c]));
    // Contrast (square) then SB's 1.5x dominant-note boost, capped.
    float bright = bin * bin * WFHYB_BRIGHT_BOOST;
    if (bright > 1.0f) bright = 1.0f;
    total_mag += bright;
  }
  // Soft-knee brightness (preserves ratios, no hard clip) — 1/4 led-share
  // scaling matches the source's LGP tuning; saturating knee mirrors the
  // source's soft cap of the summed note colours.
  float bright_raw = total_mag * WFHYB_LED_SHARE;
  float bright01 = 1.0f - expf(-bright_raw);
  bright01 = wfhyb_clamp01(bright01);

  // Chroma-anchored palette colour (base hue = chromagram_centroid_hue) + an
  // amplitude-driven walk into the SELECTED palette: louder/richer moments step
  // further along the palette so its nuance is actually displayed, while the
  // lighter colour EMA below lets the harmony hue MOVE across chord changes ->
  // the wake reads as a continuous coloured ribbon, not one hue. Palette-bounded
  // (no free hue wheel) -> inherently no-rainbow.
  const float hue_walk = fx.wfhyb_peak_last * WFHYB_HUE_SPREAD;
  CRGB16 raw_col = effect_particle_colour(rp, render_secondary, hue_walk, SQ15x16(bright01));

  // Temporal RGB EMA (tau 0.163 s) — THE hybrid signature. dt-corrected.
  const float a_col = 1.0f - expf(-dt / WFHYB_TAU_COLOUR);
  fx.wfhyb_dot_r += (float(raw_col.r) - fx.wfhyb_dot_r) * a_col;
  fx.wfhyb_dot_g += (float(raw_col.g) - fx.wfhyb_dot_g) * a_col;
  fx.wfhyb_dot_b += (float(raw_col.b) - fx.wfhyb_dot_b) * a_col;

  // Gate the smoothed dot by confidence * silentScale (source order).
  const float col_gain = confidence * sil_scale;
  CRGB16 dot_col;
  dot_col.r = SQ15x16(fx.wfhyb_dot_r * col_gain);
  dot_col.g = SQ15x16(fx.wfhyb_dot_g * col_gain);
  dot_col.b = SQ15x16(fx.wfhyb_dot_b * col_gain);

  // ==========================================================================
  // TRAIL — seed persistent wake, fade, hold upper half only
  // ==========================================================================
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);

  // Dynamic decay: loud = punchier (shorter) wake; true silence accelerates it.
  const float abs_amp = wfhyb_clamp01(peak);  // |wfPeakScaled| analogue
  float decay_rate = WFHYB_MIN_DECAY_RATE + WFHYB_DECAY_SCALE * abs_amp;
  if (quiet_factor < WFHYB_QUIET_KNEE) {
    decay_rate += WFHYB_SILENCE_DECAY * (1.0f - quiet_factor);
  }
  const SQ15x16 fade = SQ15x16(expf(-decay_rate * dt));
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }
  // Author the upper half [HALF, NATIVE_RESOLUTION); the lower half is
  // regenerated by mirror_image_downwards, so clear it before drawing.
  for (uint16_t i = 0; i < HALF; ++i) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  // ==========================================================================
  // SCROLL — integer outward (centre -> edge) sub-pixel scroll of the wake
  // ==========================================================================
  fx.wfhyb_scroll_accum += WFHYB_SCROLL_RATE * dt;
  int steps = int(fx.wfhyb_scroll_accum);
  fx.wfhyb_scroll_accum -= float(steps);
  if (steps > WFHYB_MAX_SCROLL_STEP) steps = WFHYB_MAX_SCROLL_STEP;
  for (int s = 0; s < steps; ++s) {
    for (int i = NATIVE_RESOLUTION - 1; i > int(HALF); --i) {
      leds_16[i] = leds_16[i - 1];
    }
    leds_16[HALF].r = 0;  // inject empty at the centre-origin slot
    leds_16[HALF].g = 0;
    leds_16[HALF].b = 0;
  }

  // ==========================================================================
  // DOT — amplitude-mapped bouncing point, sub-pixel additive (source verbatim)
  // ==========================================================================
  float amp = fx.wfhyb_peak_last * (WFHYB_DOT_GAIN / WFHYB_SENSITIVITY);
  if (amp > 1.0f) amp = 1.0f;
  if (amp < 0.0f) amp = 0.0f;  // peak envelope is non-negative -> dot in upper half
  float pos_f = float(HALF) + amp * float(HALF);
  // At amp==1 the verbatim port yields pos_f==NATIVE_RESOLUTION, whose pos_i and
  // pos_i+1 both fail the `< NATIVE_RESOLUTION` guards below, making the dot
  // vanish at peak amplitude. Clamp onto the last physical pixel so the peak dot
  // is always drawn.
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

  // ==========================================================================
  // FINALISE + MIRROR (store history for the persistent wake)
  // ==========================================================================
  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
