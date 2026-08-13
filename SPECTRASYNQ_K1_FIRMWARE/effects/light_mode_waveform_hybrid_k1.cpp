#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
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
  // Snapshot is refreshed every AP frame via k1_audio_snapshot_update() in the
  // main .ino (not STM-gated). Still OR with the live global peak so a torn or
  // one-frame-stale snapshot cannot black the plate while AP peak_scaled is hot
  // (Bench Unit 2 2026-08-09: silence cleared, peak~0.7, glass still looked dead).
  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const float peak = wfhyb_clamp01(fmaxf(snap.peak_scaled, waveform_peak_scaled));
  const bool  silence = snap.silence && (peak < WFHYB_PRESENCE_FLOOR);

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

  // ---- reconstruct wfPeakLast (source's two-stage EMA tau 0.016 -> 0.023) ---
  fx.wfhyb_peak_ema1 = wfhyb_ema(fx.wfhyb_peak_ema1, peak, dt, WFHYB_TAU_PEAK1);
  fx.wfhyb_peak_last = wfhyb_ema(fx.wfhyb_peak_last, fx.wfhyb_peak_ema1, dt, WFHYB_TAU_PEAK2);

  // ==========================================================================
  // COLOUR SYNTHESIS — SB 3.0.0 parity character (chroma sum, heavy RGB EMA)
  // ==========================================================================
  float total_mag = 0.0f;
  float chroma_energy = 0.0f;
  for (uint8_t c = 0; c < 12; ++c) {
    float bin = wfhyb_clamp01(float(chromagram_smooth[c]));
    chroma_energy += bin;
    // Contrast (square) then SB's 1.5x dominant-note boost, capped.
    float bright = bin * bin * WFHYB_BRIGHT_BOOST;
    if (bright > 1.0f) bright = 1.0f;
    total_mag += bright;
  }
  chroma_energy *= (1.0f / 12.0f);
  // Soft-knee brightness (preserves ratios, no hard clip) — 1/4 led-share
  // scaling matches the source's LGP tuning; saturating knee mirrors the
  // source's soft cap of the summed note colours.
  float bright_raw = total_mag * WFHYB_LED_SHARE;
  float bright01 = 1.0f - expf(-bright_raw);
  bright01 = wfhyb_clamp01(bright01);

  // ── Peak/VU seed envelope (mirrors light_mode_waveform_hybrid.cpp:84–106) ──
  float blend = wfhyb_clamp01(chroma_energy * VP_WAVEFORM_CHROMA_BLEND_GAIN);
  // When the chromagram sparseness gate leaves only a thin residual, prefer the
  // peak-driven fallback colour. Otherwise particle colour stays near-black while
  // AP peak_scaled is healthy (IM73D quiet floor / chroma gate_gain≪1).
  if (chroma_energy < 0.15f && peak > WFHYB_PRESENCE_FLOOR) {
    if (blend > 0.25f) blend = 0.25f;
  }
  float seed_level = peak;
  if (fx.wfhyb_peak_last > seed_level) seed_level = fx.wfhyb_peak_last;
  const float vu = wfhyb_clamp01(snap.vu_level);
  if (vu > seed_level) seed_level = vu;
  seed_level = wfhyb_clamp01(seed_level);
  const bool seed_active =
      (peak > WFHYB_PRESENCE_FLOOR) || (vu > WFHYB_PRESENCE_FLOOR);
  const float fallback_bright =
      seed_active ? wfhyb_clamp01(seed_level * VP_WAVEFORM_FALLBACK_BRIGHTNESS) : 0.0f;

  // Chroma-anchored palette colour (base hue = chromagram_centroid_hue) + an
  // amplitude-driven walk into the SELECTED palette: louder/richer moments step
  // further along the palette so its nuance is actually displayed, while the
  // lighter colour EMA below lets the harmony hue MOVE across chord changes ->
  // the wake reads as a continuous coloured ribbon, not one hue. Palette-bounded
  // (no free hue wheel) -> inherently no-rainbow.
  const float hue_walk = fx.wfhyb_peak_last * WFHYB_HUE_SPREAD;
  CRGB16 chroma_col = effect_particle_colour(rp, render_secondary, hue_walk, SQ15x16(bright01));

  // ── CHROMA-INDEPENDENT COLOUR (the actual dark-plate defect) ───────────────
  // In chromatic mode — the K1 default (PALETTE_MODE_ENABLED == false) —
  // effect_particle_colour() routes to effect_palette_or_chroma_colour(), whose
  // base RGB is built ONLY from chromagram_smooth[] and which applies the passed
  // brightness as a FINAL MULTIPLIER (lightshow_modes.h:473–507). With null
  // chroma the base is (0,0,0), so even a perfectly healthy peak-derived
  // brightness multiplies to black. Blending peak/VU into `bright01` therefore
  // cannot light the plate: it fixes the multiplier while the multiplicand stays
  // zero. Mode 11 survives identical audio because its fallback SYNTHESISES a
  // colour — hsv(rp->CHROMA, SATURATION, fallback_brightness) — whose hue does
  // not depend on chroma at all (light_mode_waveform_hybrid.cpp:93–106).
  // So blend at the COLOUR level, exactly as mode 11 does, not at brightness.
  CRGB16 fallback_col;
  if (render_params_palette_owns_colour(rp, render_secondary)) {
    const CRGBPalette16& pal =
        cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
#ifdef K1_FALLBACK_HELD_U_V1
    // S1 fallback bound: seed from the LAST LIVE arc position (the engine's
    // held musical anchor), not the CHROMA knob — the knob parked every thin-
    // chroma frame at the palette's first colour (measured: the plate lived in
    // the blue band for a full minute while gold was never visited).
    const float fb_u = (k1_palette_held_u_valid ? k1_palette_held_u
                                                : float(rp->CHROMA)) + hue_walk;
    fallback_col = clamp_crgb16(
        palette_manual_colour(pal, SQ15x16(fb_u), SQ15x16(fallback_bright)));
#else
    fallback_col = clamp_crgb16(
        palette_manual_colour(pal, SQ15x16(rp->CHROMA + hue_walk), SQ15x16(fallback_bright)));
#endif
    // A gradient stop can itself be black at this coordinate; HSV-synthesise
    // rather than emit nothing while a real signal is present.
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

  // Temporal RGB EMA (tau 0.163 s) — THE hybrid signature. dt-corrected.
  const float a_col = 1.0f - expf(-dt / WFHYB_TAU_COLOUR);
#ifdef K1_POSITION_SMOOTH_V1
  // S-candidate: HUE-SAFE smoothing (design P1 applied to smoothing). RGB EMA
  // between distant palette colours passes through grey/red and is stage 1 of
  // the measured gold kill. Instead: EMA the LUMINANCE trajectory only, and
  // renormalise the smoothed colour back to the CURRENT frame's hue/sat ratios
  // — motion stays as smooth (same tau on perceived level), hue stays a
  // palette identity every frame.
  {
    const float cur_max = fmaxf(fmaxf(float(raw_col.r), float(raw_col.g)), float(raw_col.b));
    float prev_lum = fmaxf(fmaxf(fx.wfhyb_dot_r, fx.wfhyb_dot_g), fx.wfhyb_dot_b);
    const float lum = prev_lum + (cur_max - prev_lum) * a_col;
    if (cur_max > 0.001f) {
      const float k = lum / cur_max;
      fx.wfhyb_dot_r = float(raw_col.r) * k;
      fx.wfhyb_dot_g = float(raw_col.g) * k;
      fx.wfhyb_dot_b = float(raw_col.b) * k;
    } else {
      fx.wfhyb_dot_r *= (1.0f - a_col);
      fx.wfhyb_dot_g *= (1.0f - a_col);
      fx.wfhyb_dot_b *= (1.0f - a_col);
    }
  }
#else
  fx.wfhyb_dot_r += (float(raw_col.r) - fx.wfhyb_dot_r) * a_col;
  fx.wfhyb_dot_g += (float(raw_col.g) - fx.wfhyb_dot_g) * a_col;
  fx.wfhyb_dot_b += (float(raw_col.b) - fx.wfhyb_dot_b) * a_col;
#endif

  // Gate the smoothed dot by confidence * silentScale (source order), FLOORED
  // while a real signal is present. `silence` latches true after 10 s of
  // sweet_spot_state == -1 (i2s_audio.h:795–802) and is a purely multiplicative
  // kill here — a second, independent path to a black plate that survives any
  // colour fix. Modes 8/11 carry no such gate (they key on max_waveform_val_raw
  // / peak / VU), which is why they stayed lit on the very same audio. A latched
  // flag must never zero a live signal.
  const float quiet_factor =
      fmaxf(fminf(confidence, sil_scale), seed_active ? seed_level : 0.0f);
  float col_gain = confidence * sil_scale;
  if (seed_active && col_gain < seed_level) col_gain = seed_level;
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

#ifdef M32_DARK_DIAG
  // Opt-in dark-render diagnostic. M32_DARK_DIAG is defined by NO env in
  // platformio.ini — enable it for a bench session only via
  //   PLATFORMIO_BUILD_FLAGS=-DM32_DARK_DIAG bash scripts/agent/pio-build.sh <env>
  // so no instrumentation can reach production and mode 32 carries no mic/env
  // conditional. Primary channel only, 1 Hz, to keep it off the render hot path.
  if (!render_secondary) {
    static uint32_t wfhyb_dbg_last_ms = 0;
    if (now_ms - wfhyb_dbg_last_ms >= 1000) {
      wfhyb_dbg_last_ms = now_ms;
      float led_max = 0.0f;
      for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
        const float r = float(leds_16[i].r);
        const float g = float(leds_16[i].g);
        const float b = float(leds_16[i].b);
        if (r > led_max) led_max = r;
        if (g > led_max) led_max = g;
        if (b > led_max) led_max = b;
      }
      USBSerial.printf(
          "[M32] ledmax=%.4f bright01=%.3f chroma=%.4f blend=%.3f peak=%.3f "
          "vu=%.3f gpeak=%.3f amp=%.3f pos=%d colgain=%.3f conf=%.3f sil=%.3f "
          "silence=%d pal=%d dot=%.3f/%.3f/%.3f fb=%.3f mirror=%d\n",
          led_max, bright01, chroma_energy, blend, peak, vu,
          (float)waveform_peak_scaled, amp, pos_i,
          col_gain, confidence, sil_scale, silence ? 1 : 0,
          render_params_palette_owns_colour(rp, render_secondary) ? 1 : 0,
          float(dot_col.r), float(dot_col.g), float(dot_col.b), fallback_bright,
          rp->MIRROR_ENABLED ? 1 : 0);
    }
  }
#endif
}
