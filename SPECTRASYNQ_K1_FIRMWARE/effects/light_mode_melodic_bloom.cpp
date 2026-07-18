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
// is a 27-bin band-mean that rests well below 1.0, so it is auto-ranged against a
// SLOW EMA (tau ~4 s) — NEVER an instant-rise peak, which would re-snap the eased
// signal and pump (the twitch fixed 2026-07-18; findings/MELODIC_BLOOM_MOTION_DIAGNOSIS.md).
//
// MOTION (the-method 4.1 + 00b 2): presence is eased, then routed through three followers —
// a 0.4+0.6*env breathing floor on CORE brightness (breathe, never blink), plus a calm SURGE
// speed and a slow REACH envelope that grow the bloom's SPATIAL EXTENT with energy (reactivity
// on transport, out of the 5-20 Hz global-brightness flicker band), not a brightness strobe.
//
// STRUCTURE: a peer of light_mode_bloom_bt — the same proven, budget-verified centre-origin
// OUTWARD greyscale scroll + sqrt radial warp + palette/chroma colour + mirror_image_downwards.
// Centre-origin, no rainbow, no heap in render, dt-timed, silence-gated — all K1 laws honoured.
// =============================================================================

static const float MELODIC_SPEED_MIN    = 35.0f;   // px/s drift floor — always flowing outward, never stalls
static const float MELODIC_SPEED_SPAN   = 40.0f;   // + calm surge envelope * this (=> 35..75 px/s), grow-not-pulse
static const int   MELODIC_MAX_STEP     = 4;        // per-frame integer-scroll clamp
static const float MELODIC_RANGE_TAU_S  = 4.0f;     // SLOW auto-range time constant (s) — must NOT instant-rise (pumps = twitch)
static const float MELODIC_RANGE_FLOOR  = 0.03f;    // auto-range floor (measured mid_energy p50 ~0.03..0.08 across corpus)
static const float MELODIC_BRIGHT_FLOOR = 0.40f;    // breathing floor: core = 0.4 + 0.6*env (breathes, never blinks — the-method 4.1)
static const float MELODIC_REACH_MIN_PX = 22.0f;    // bloom half-extent (px) at rest — a small central core that GROWS with presence

void light_mode_melodic_bloom(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;   // 80; centre 79/80, edge 159

  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const float dt = k1ease::safe_dt(millis(), fx.melodicbloom_last_ms);

  // Presence = post-AGC mid-band energy, eased (50 ms attack / 400 ms release), then
  // auto-ranged against a SLOW EMA range (tau ~4 s) so the bloom is visible regardless of
  // programme level. The old code divided by an INSTANT-RISE running max, which re-snapped the
  // eased signal on every mid onset — that is the raw-level->intensity strobe (the-method
  // 4.1(b), the #1 amateur failure) laundered back in AFTER the easing, and it drove BOTH
  // brightness and speed (the "twitchy / flips on a dime" Captain rejected, 2026-07-18). A slow
  // range is ~constant over the envelope's timescale, so presence now inherits mid_env's grace.
  float mid = float(snap.mid_energy);
  if (mid < 0.0f) mid = 0.0f;
  fx.melodicbloom_mid_env = k1ease::follow(fx.melodicbloom_mid_env, mid, dt, 0.05f, 0.40f);
  fx.melodicbloom_mid_max = k1ease::ema(fx.melodicbloom_mid_max, fx.melodicbloom_mid_env, dt, MELODIC_RANGE_TAU_S);
  if (fx.melodicbloom_mid_max < MELODIC_RANGE_FLOOR) fx.melodicbloom_mid_max = MELODIC_RANGE_FLOOR;
  float presence = fx.melodicbloom_mid_env / fx.melodicbloom_mid_max;
  if (presence > 1.0f) presence = 1.0f;
  if (presence < 0.0f) presence = 0.0f;

  // Soft silence gate (eases to dark over ~300 ms instead of snapping black).
  fx.melodicbloom_sil = k1ease::follow(fx.melodicbloom_sil, snap.silence ? 0.0f : 1.0f, dt, 0.05f, 0.30f);

  // Three eased characters from the one presence (00b 2.5). Brightness carries the breathing
  // floor (0.4 + 0.6*env -> never blinks); speed and reach carry the "grow, not pulse" energy
  // read as SPATIAL extent (00b 4.8: reactivity routed to transport, OUT of the 5-20 Hz
  // global-brightness flicker band). Each is eased, so none can twitch even on hard onsets.
  fx.melodicbloom_bright_env = k1ease::follow(fx.melodicbloom_bright_env, presence, dt, 0.05f, 0.40f);
  fx.melodicbloom_speed_env  = k1ease::follow(fx.melodicbloom_speed_env,  presence, dt, 0.08f, 0.60f);
  fx.melodicbloom_reach_env  = k1ease::follow(fx.melodicbloom_reach_env,  presence, dt, 0.12f, 0.80f);
  const float bright_core = MELODIC_BRIGHT_FLOOR + (1.0f - MELODIC_BRIGHT_FLOOR) * fx.melodicbloom_bright_env;

  // Continuous sub-pixel OUTWARD scroll; the calm surge envelope drives an energy-linked speed
  // (the medium accelerates under load, Ember 6.4) with SPEED_MIN as the no-stall drift floor.
  const float speed_pxs = MELODIC_SPEED_MIN + MELODIC_SPEED_SPAN * fx.melodicbloom_speed_env;
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

  // Inject the eased, FLOORED greyscale core across the freshly-exposed centre. Brightness is
  // the breathing-floor envelope * silence gate — raw presence never touches brightness.
  const float inject = bright_core * fx.melodicbloom_sil;
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
  const float presenceHue = fx.melodicbloom_bright_env * 0.10f;   // eased warm shift (no per-frame twitch)
  // Reach/extent (Tier 2, grow-not-pulse): the display half-extent breathes with the SLOW reach
  // envelope — a small central core at rest (REACH_MIN_PX) that grows toward the edge as presence
  // rises. Display-only (post-snapshot), so it never feeds the transport (bloom 5.8).
  const float reach_px = MELODIC_REACH_MIN_PX
      + (float)((uint16_t)HALF - (uint16_t)MELODIC_REACH_MIN_PX) * fx.melodicbloom_reach_env;

  for (uint16_t i = 0; i < HALF; ++i) {
    float fade = 1.0f - (float)i / reach_px;                          // 1 at centre, 0 at the reach front
    if (fade < 0.0f) fade = 0.0f;
    fade *= fade;                                                     // soft quadratic falloff — no hard boundary (Ember 5.2)
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
