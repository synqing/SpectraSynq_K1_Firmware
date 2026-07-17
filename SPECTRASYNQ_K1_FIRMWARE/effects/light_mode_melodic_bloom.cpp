#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "easing.h"
#include <math.h>
#include <string.h>

// =============================================================================
// light_mode_melodic_bloom — "Melodic Bloom" (mid-forward presence bloom)
//
// Captain-signed rename of the launch-canon "Vocal Bloom" hero effect
// (2026-07-17, gap k1-vocal-bloom-firmware-gap-2026-07-15): a Goertzel engine
// cannot detect voice IDENTITY, so this ships as PRESENCE — it blooms on
// mid-forward tonal energy (voice AND prominent leads/piano alike), honestly.
//
// DRIVER: snap.mid_energy — the post-AGC mean of the middle-third GDFT band
// (bins 26..52 ~= 494..2217 Hz, k1_audio_snapshot.cpp:56). This is the signal
// host-scored in V.3a (findings/VOCAL_PROXY_V3A_RESULTS.md): the raw mid_energy
// meter, NOT the ratio+gate proxy (which V.3a killed as redundant). mid_energy
// is a 27-bin band-mean that rests well below 1.0, so it is auto-ranged against
// a slow running max before it drives brightness.
//
// STRUCTURE: a peer of light_mode_bloom_bt — the same proven, budget-verified
// centre-origin OUTWARD greyscale scroll + sqrt radial warp + palette/chroma
// colour + mirror_image_downwards. Only the audio drive differs (mid presence
// instead of bass/treble chroma). Centre-origin, no rainbow, no heap in render,
// dt-timed, silence-gated — all K1 effect laws honoured.
// =============================================================================

static const float MELODIC_SPEED_MIN     = 35.0f;   // px/s at zero presence (always flowing outward)
static const float MELODIC_SPEED_SPAN    = 50.0f;   // + presence * this (=> 35..85 px/s)
static const int   MELODIC_MAX_STEP      = 4;        // per-frame integer-scroll clamp
static const float MELODIC_MID_MAX_FLOOR = 0.06f;    // auto-range floor (mid_energy rests low)
static const float MELODIC_MID_MAX_FALL_S = 4.0f;    // running-max decay time constant (s)

void light_mode_melodic_bloom(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;   // 80; centre 79/80, edge 159

  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const float dt = k1ease::safe_dt(millis(), fx.melodicbloom_last_ms);

  // Presence = post-AGC mid-band energy, enveloped (40 ms attack / 350 ms release),
  // then auto-ranged against a slow running max so the bloom is visible regardless
  // of programme level (the band-mean rests well below full-scale).
  float mid = float(snap.mid_energy);
  if (mid < 0.0f) mid = 0.0f;
  fx.melodicbloom_mid_env = k1ease::follow(fx.melodicbloom_mid_env, mid, dt, 0.04f, 0.35f);
  if (fx.melodicbloom_mid_env > fx.melodicbloom_mid_max) {
    fx.melodicbloom_mid_max = fx.melodicbloom_mid_env;             // instant rise to the peak
  } else {
    float fall = dt / MELODIC_MID_MAX_FALL_S;
    if (fall > 1.0f) fall = 1.0f;
    fx.melodicbloom_mid_max += (fx.melodicbloom_mid_env - fx.melodicbloom_mid_max) * fall;
  }
  if (fx.melodicbloom_mid_max < MELODIC_MID_MAX_FLOOR) fx.melodicbloom_mid_max = MELODIC_MID_MAX_FLOOR;
  float presence = fx.melodicbloom_mid_env / fx.melodicbloom_mid_max;
  if (presence > 1.0f) presence = 1.0f;
  if (presence < 0.0f) presence = 0.0f;

  // Soft silence gate (eases to dark over ~300 ms instead of snapping black).
  fx.melodicbloom_sil = k1ease::follow(fx.melodicbloom_sil, snap.silence ? 0.0f : 1.0f, dt, 0.05f, 0.30f);

  // Continuous sub-pixel OUTWARD scroll; presence drives the flow speed.
  const float speed_pxs = MELODIC_SPEED_MIN + MELODIC_SPEED_SPAN * presence;
  fx.melodicbloom_scroll_accum += speed_pxs * dt;
  int steps = (int)fx.melodicbloom_scroll_accum;
  fx.melodicbloom_scroll_accum -= (float)steps;
  if (steps > MELODIC_MAX_STEP) steps = MELODIC_MAX_STEP;

  // Copy the per-channel greyscale transport forward, then integer-scroll outward.
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
  if (steps > 0) {
    const SQ15x16 decay = SQ15x16(0.992f);   // per-step trail decay
    for (int j = NATIVE_RESOLUTION - 1; j >= (int)(HALF + steps); --j) {
      leds_16[j].r = leds_16[j - steps].r * decay;
      leds_16[j].g = leds_16[j - steps].g * decay;
      leds_16[j].b = leds_16[j - steps].b * decay;
    }
  }

  // Inject the presence-driven greyscale ring across the freshly-exposed centre.
  const float inject = presence * fx.melodicbloom_sil;
  const CRGB16 grayPix = { SQ15x16(inject), SQ15x16(inject), SQ15x16(inject) };
  const int fill = (steps < 1) ? 1 : steps;
  for (int k = 0; k < fill && (int)(HALF + k) < NATIVE_RESOLUTION; ++k) {
    leds_16[HALF + k] = grayPix;
  }

  // Zero the mirror (lower) half so the snapshotted transport is clean greyscale.
  memset(leds_16, 0, sizeof(CRGB16) * HALF);
  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);

  // Sqrt radial warp (display only) — verbatim from the bloom_bt transport.
  for (uint16_t i = 0; i < HALF; ++i) {
    const float prog   = (float)i / (float)(HALF - 1);
    const float prog_d = sqrtf(prog);
    float src = (float)HALF + prog_d * (float)(HALF - 1);
    src -= fx.melodicbloom_scroll_accum;
    if (src < (float)HALF) src = (float)HALF;
    if (src > (float)(NATIVE_RESOLUTION - 2)) src = (float)(NATIVE_RESOLUTION - 2);
    const int   srcLow = (int)src;
    const float frac   = src - (float)srcLow;
    const float lo     = float(leds_16[srcLow].r);       // greyscale: r == g == b
    const float hi     = float(leds_16[srcLow + 1].r);
    const SQ15x16 v    = SQ15x16(lo * (1.0f - frac) + hi * frac);
    leds_16[HALF + i].r = v;
    leds_16[HALF + i].g = v;
    leds_16[HALF + i].b = v;
  }

  // Colour: greyscale intensity -> palette-bounded, chroma-anchored colour, with
  // the linear edge fade folded in. Per-frame hue LUT (never rainbow). A small
  // presence term warms the walk as the bloom opens.
  const bool palette_owns = render_params_palette_owns_colour(rp, render_secondary);
  const CRGBPalette16* pal = palette_owns
      ? &cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary)
      : nullptr;
  const float baseHue = palette_owns ? chromagram_centroid_hue() : 0.0f;   // once/frame

  const int HUE_LUT_N = 16;
  CRGB16 hueLUT[HUE_LUT_N + 1];
  if (palette_owns) {
    for (int k = 0; k <= HUE_LUT_N; ++k) {
      float h = baseHue + (float)k / (float)HUE_LUT_N;
      h -= floorf(h);
      hueLUT[k] = clamp_crgb16(palette_manual_colour(*pal, SQ15x16(h), SQ15x16(1.0f)));
    }
  }
  const CRGB16 chromaBase = palette_owns
      ? CRGB16{ SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(0.0f) }
      : effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0f));

  const float sil = fx.melodicbloom_sil;
  const float presenceHue = presence * 0.10f;   // gentle warm shift as presence rises

  for (uint16_t i = 0; i < HALF; ++i) {
    const float fade   = (float)(HALF - 1 - i) / (float)(HALF - 1);   // linear edge fade
    const float bright = float(leds_16[HALF + i].r) * fade * sil;     // greyscale: r == g == b
    if (bright < 0.001f) {
      leds_16[HALF + i] = CRGB16{ SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(0.0f) };
      continue;
    }
    if (palette_owns) {
      const float distFromCentre = ((float)i + 0.5f) / (float)HALF;   // 0..1 outward
      float hueOff = distFromCentre * 0.34f + bright * 0.12f + presenceHue;
      hueOff -= floorf(hueOff);                                       // wrap to [0,1)
      float fk = hueOff * (float)HUE_LUT_N;
      int   k0 = (int)fk;
      if (k0 >= HUE_LUT_N) k0 = HUE_LUT_N - 1;
      const SQ15x16 ff = SQ15x16(fk - (float)k0);
      const SQ15x16 b  = SQ15x16(bright);
      const CRGB16& c0 = hueLUT[k0];
      const CRGB16& c1 = hueLUT[k0 + 1];
      CRGB16 out;
      out.r = (c0.r + (c1.r - c0.r) * ff) * b;
      out.g = (c0.g + (c1.g - c0.g) * ff) * b;
      out.b = (c0.b + (c1.b - c0.b) * ff) * b;
      leds_16[HALF + i] = out;
    } else {
      const SQ15x16 b = SQ15x16(bright);
      CRGB16 out;
      out.r = chromaBase.r * b;
      out.g = chromaBase.g * b;
      out.b = chromaBase.b * b;
      leds_16[HALF + i] = out;
    }
  }

  // Re-zero the lower half, then fold the coloured upper half to the centre 79/80.
  memset(leds_16, 0, sizeof(CRGB16) * HALF);
  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);
}
