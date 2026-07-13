#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "easing.h"
#include <math.h>
#include <string.h>

// =============================================================================
// light_mode_bloom_bt — K1 Bloom V2 "Bass-Treble Split"
//
// Faithful fork port of firmware-v3 effect 0x1309
// (SbK1BloomV2BassTrebleEffect, EID_SB_K1_BLOOM_V2_BASS_TREBLE). Continuous,
// audio-warped OUTWARD bloom — it is alive every frame, NOT beat-gated.
//
// Behaviour reproduced from the reference render path
// (src/effects/ieffect/sensorybridge_reference/SbK1BloomV2Effect.cpp:1556):
//
//   * BASS births rings.   Chroma bins 0-5 form the "bass" half; the loudest
//     (after contrast) drives the greyscale brightness of the ring injected at
//     centre each even frame.
//   * TREBLE drives speed.  Chroma bins 6-11 form the "treble" half; when the
//     loudest exceeds 0.5 the scroll steps 2 pixels per even frame, otherwise 1.
//   * SQRT-warped radius.   The displayed right half is resampled through a
//     sqrt() curve so rings stretch as they travel outward.
//   * Warm/cool shift.      The bass/treble balance shifts the palette walk warm
//     (bass-dominant) to cool (treble-dominant).
//   * Alternating frames.   K1 parity: the scroll state only advances on EVEN
//     frames; ODD frames replay the same transport (halves the scroll rate).
//   * Greyscale transport.  The scroll state stores INTENSITY only; colour is
//     applied at the output stage, so hues never compound down the trail.
//
// Fork-idiom adaptations (all documented in the handover):
//   * The greyscale scroll state lives in the caller-supplied, per-channel
//     `leds_prev_buffer` (snapshotted via finalize_additive_frame) rather than a
//     private PSRAM buffer, so primary/secondary VP channels keep separate
//     state without any file-static buffer.
//   * Colour is emitted through effect_particle_colour(), which anchors the base
//     hue to chromagram_centroid_hue() and stays inside the selected palette —
//     the reference's free note-hue / hue_position machinery is redirected into
//     that chroma-anchored, palette-bounded path, so this can never rainbow.
//   * Centre origin: content is authored in the UPPER half [HALF, NATIVE_RESOLUTION)
//     with the lower half zeroed; mirror_image_downwards() folds it to 79/80.
// =============================================================================

// --- Continuous scroll speed (px/s). Treble drives the flow speed, but through
// an EASED envelope + a fractional-pixel accumulator, NOT the old hard 1<->2 px
// binary threshold that thrashed frame-to-frame ("twitches/rotates like a
// spastic"). BLOOMBT_SPEED_MIN keeps the bloom always flowing outward.
static const float BLOOMBT_SPEED_MIN  = 35.0f;   // px/s at zero treble (always flowing, never near-stalled)
static const float BLOOMBT_SPEED_SPAN = 50.0f;   // + eased treble * this (=> 35..85 px/s) — calmer, less erratic
static const int   BLOOMBT_MAX_STEP   = 4;        // per-frame integer-scroll clamp

void light_mode_bloom_bt(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;   // 80; centre index 80, edge 159

  // ---------------------------------------------------------------------------
  // Audio: the global 12-bin chromagram (the faithful analogue of the reference
  // m_chromaSmooth). The 3-band snapshot is read only for its silence flag.
  //
  // dt is the REAL per-frame delta (millis-based) that drives the followers,
  // independent of the frame-count scroll cadence below.
  // ---------------------------------------------------------------------------
  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const float dt = k1ease::safe_dt(millis(), fx.bloombt_last_ms);

  // Bass = loudest of chroma bins 0-5; treble = loudest of bins 6-11.
  // The reference applies applyContrast(bin, m_contrast) with m_contrast == 1.0,
  // which is exactly one squaring (bin * bin). RAW energies here — the followers
  // below add the asymmetric attack/release so the output can never pop on/off.
  float bassEnergy = 0.0f;
  for (uint8_t c = 0; c < 6; ++c) {
    float b = float(chromagram_smooth[c]);
    if (b < 0.0f) b = 0.0f;
    b = b * b;                       // contrast == 1.0 -> single square
    if (b > bassEnergy) bassEnergy = b;
  }
  if (bassEnergy > 1.0f) bassEnergy = 1.0f;

  float trebleEnergy = 0.0f;
  for (uint8_t c = 6; c < 12; ++c) {
    float t = float(chromagram_smooth[c]);
    if (t < 0.0f) t = 0.0f;
    t = t * t;
    if (t > trebleEnergy) trebleEnergy = t;
  }
  if (trebleEnergy > 1.0f) trebleEnergy = 1.0f;

  // Asymmetric bass envelope: 40 ms attack (a hit lights fast), 350 ms release
  // (it fades gracefully). This is what kills the frame-to-frame on/off pop —
  // the injected ring brightness comes from the envelope, never raw bassEnergy.
  fx.bloombt_bass_env = k1ease::follow(fx.bloombt_bass_env, bassEnergy, dt, 0.04f, 0.35f);

  // Soft silence gate: replaces the hard 0/1 flip with a smoothed follower so the
  // plate eases to dark over ~300 ms instead of snapping black (50 ms attack back
  // in, 300 ms release out). Multiplies both the injected ring and the output.
  fx.bloombt_sil = k1ease::follow(fx.bloombt_sil, snap.silence ? 0.0f : 1.0f, dt, 0.05f, 0.30f);

  // Treble drives the warm(0)-to-cool(+0.33) hue balance from the RAW ratio
  // (colour position — STROBE-LAW-clean), and (below, eased) the continuous
  // scroll speed. The old hard `fast = trebleEnergy > 0.5` binary is GONE — it
  // flipped the step 1<->2 px as treble hovered near 0.5 and produced the
  // frame-to-frame speed thrash Captain rejected.
  const float trebleRatio = trebleEnergy / (bassEnergy + trebleEnergy + 0.001f);
  const float btHueOffset = trebleRatio * 0.33f;

  // ---------------------------------------------------------------------------
  // Continuous sub-pixel OUTWARD scroll. The old K1-parity even/odd cadence plus
  // the hard 1<->2 px treble threshold thrashed the flow speed frame-to-frame —
  // the "twitches / rotates in-out like a spastic" Captain rejected. Replaced by
  // an EASED treble envelope driving a dt-based fractional-pixel accumulator, so
  // the flow speed varies SMOOTHLY and stays monotonically OUTWARD. The bass ring
  // is injected every frame, so the bloom is alive even at rest.
  // ---------------------------------------------------------------------------
  fx.bloombt_treble_env = k1ease::follow(fx.bloombt_treble_env, trebleEnergy, dt, 0.04f, 0.28f);
  const float speed_pxs = BLOOMBT_SPEED_MIN + BLOOMBT_SPEED_SPAN * fx.bloombt_treble_env;
  fx.bloombt_scroll_accum += speed_pxs * dt;
  int steps = (int)fx.bloombt_scroll_accum;
  fx.bloombt_scroll_accum -= (float)steps;
  if (steps > BLOOMBT_MAX_STEP) steps = BLOOMBT_MAX_STEP;

  // Copy the per-channel greyscale transport forward, then integer-scroll it
  // outward in place by `steps` (descending j reads lower indices before they are
  // overwritten — no in-place hazard). Fractional carry lives in scroll_accum, so
  // the AVERAGE speed is continuous even though each frame shifts a whole number.
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
  if (steps > 0) {
    const SQ15x16 decay = SQ15x16(0.992f);   // per-step trail decay (band separation)
    for (int j = NATIVE_RESOLUTION - 1; j >= (int)(HALF + steps); --j) {
      leds_16[j].r = leds_16[j - steps].r * decay;
      leds_16[j].g = leds_16[j - steps].g * decay;
      leds_16[j].b = leds_16[j - steps].b * decay;
    }
  }

  // Inject the bass-driven greyscale ring across the freshly-exposed centre pixels
  // [HALF, HALF+steps] (at least the centre) EVERY frame — brightness = eased bass
  // envelope * soft silence gate, never raw audio. Filling the whole exposed span
  // keeps the outward flow continuous (no gaps between scroll steps).
  const float inject = fx.bloombt_bass_env * fx.bloombt_sil;
  const CRGB16 grayPix = { SQ15x16(inject), SQ15x16(inject), SQ15x16(inject) };
  const int fill = (steps < 1) ? 1 : steps;
  for (int k = 0; k < fill && (int)(HALF + k) < NATIVE_RESOLUTION; ++k) {
    leds_16[HALF + k] = grayPix;
  }

  // Zero the mirror (lower) half so the snapshotted transport is clean greyscale.
  memset(leds_16, 0, sizeof(CRGB16) * HALF);

  // Snapshot the greyscale transport every frame (continuous scroll). The display
  // stage below (sqrt warp + colour) is never fed back into the transport.
  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);

  // ---------------------------------------------------------------------------
  // Sqrt radial warp (display only). src is always >= the write cursor, so the
  // in-place resample is safe; the only self-referential pixel (i == HALF-1) is
  // driven to zero by the edge fade immediately below, so it leaves no artefact.
  // ---------------------------------------------------------------------------
  for (uint16_t i = 0; i < HALF; ++i) {
    const float prog   = (float)i / (float)(HALF - 1);
    const float prog_d = sqrtf(prog);
    float src = (float)HALF + prog_d * (float)(HALF - 1);
    // SUB-PIXEL SCROLL: offset the sample position by the fractional scroll carry
    // so the flow is smooth BETWEEN integer buffer steps. Without this, the scroll
    // lurches 1 px every few frames and the sqrt warp AMPLIFIES that near-centre
    // step into a visible jump — the "twitchy" motion. Offsetting the read makes
    // the display drift continuously; the integer step + carry-reset stay in sync.
    src -= fx.bloombt_scroll_accum;
    if (src < (float)HALF) src = (float)HALF;
    if (src > (float)(NATIVE_RESOLUTION - 2)) src = (float)(NATIVE_RESOLUTION - 2);

    const int   srcLow = (int)src;
    const float frac   = src - (float)srcLow;
    const float lo     = float(leds_16[srcLow].r);      // greyscale: r == g == b
    const float hi     = float(leds_16[srcLow + 1].r);
    const SQ15x16 v    = SQ15x16(lo * (1.0f - frac) + hi * frac);

    leds_16[HALF + i].r = v;
    leds_16[HALF + i].g = v;
    leds_16[HALF + i].b = v;
  }

  // ---------------------------------------------------------------------------
  // Colour application. Greyscale intensity → palette-bounded, chroma-anchored
  // colour, with the linear edge fade (centre bright, edge dark) folded into the
  // same pass.
  //
  // effect_particle_colour() recomputes chromagram_centroid_hue() — a 12-term
  // cosf/sinf/atan2f reduction — on EVERY call, which at 80 calls/frame is ~960
  // trig ops and blew the 2.0 ms ceiling. The helper body (lightshow_modes.h:542)
  // is inlined here with the frame-constant parts (palette ownership, palette
  // reference, centroid hue) hoisted OUT of the loop. Colour output is identical.
  //
  // Hue offset per RING (radial palette walk + bright term + bass/treble warm-cool
  // shift) keeps the walk inside the selected gradient — never a free-running hue.
  // ---------------------------------------------------------------------------
  const bool palette_owns = render_params_palette_owns_colour(rp, render_secondary);
  const CRGBPalette16* pal = palette_owns
      ? &cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary)
      : nullptr;
  const float baseHue = palette_owns ? chromagram_centroid_hue() : 0.0f;  // once/frame

  // Per-frame hue LUT. palette_manual_colour() is a <=48-stop HD scan (~30 us);
  // called per LIT LED it is data-dependent and, when the bloom is fully lit,
  // blows the 2.0 ms ceiling (measured 3.9 ms). Sample the palette into a small
  // hue LUT ONCE per frame at unit brightness (baseHue folded in), then do a
  // cheap lerp + brightness scale per LED — O(1) per LED regardless of lit count.
  // 16 stops + linear blend is visually identical to the direct sample for a
  // bloom gradient. Still chroma-anchored (baseHue) and palette-bounded: no rainbow.
  const int HUE_LUT_N = 16;
  CRGB16 hueLUT[HUE_LUT_N + 1];   // +1 guard entry for the lerp partner
  if (palette_owns) {
    for (int k = 0; k <= HUE_LUT_N; ++k) {
      float h = baseHue + (float)k / (float)HUE_LUT_N;
      h -= floorf(h);
      hueLUT[k] = clamp_crgb16(palette_manual_colour(*pal, SQ15x16(h), SQ15x16(1.0f)));
    }
  }
  // Chromatic mode (no gradient palette active): effect_palette_or_chroma_colour()
  // returns a SINGLE live chroma colour identical for every LED — only brightness
  // varies. Calling it per lit LED was the real data-dependent hot path (measured
  // ~35 us/lit-pixel). Sample it ONCE per frame at unit brightness and scale per LED.
  const CRGB16 chromaBase = palette_owns
      ? CRGB16{ SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(0.0f) }
      : effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0f));

  // Soft silence gate applied to the whole output — the plate eases to dark over
  // ~300 ms in silence instead of snapping black (frame-constant, folded per LED).
  const float sil = fx.bloombt_sil;

  for (uint16_t i = 0; i < HALF; ++i) {
    const float fade   = (float)(HALF - 1 - i) / (float)(HALF - 1);   // linear edge fade
    const float bright = float(leds_16[HALF + i].r) * fade * sil;     // greyscale: r == g == b
    if (bright < 0.001f) {
      leds_16[HALF + i] = CRGB16{ SQ15x16(0.0f), SQ15x16(0.0f), SQ15x16(0.0f) };
      continue;
    }
    if (palette_owns) {
      const float distFromCentre = ((float)i + 0.5f) / (float)HALF;   // 0..1 outward
      // Calmer radial colour walk (was 0.784 — nearly a full palette traverse
      // across the strip, which read as "confused"). A smaller walk keeps the
      // bloom coherent: a coloured field that shifts gently, not a busy gradient.
      float hueOff = distFromCentre * 0.34f + bright * 0.12f + btHueOffset;
      hueOff -= floorf(hueOff);                                       // wrap to [0,1)
      float fk = hueOff * (float)HUE_LUT_N;
      int   k0 = (int)fk;
      if (k0 >= HUE_LUT_N) k0 = HUE_LUT_N - 1;                        // bound guard
      const SQ15x16 ff = SQ15x16(fk - (float)k0);
      const SQ15x16 b  = SQ15x16(bright);
      const CRGB16& c0 = hueLUT[k0];
      const CRGB16& c1 = hueLUT[k0 + 1];
      CRGB16 out;                                                     // lerp(c0,c1,ff) * bright
      out.r = (c0.r + (c1.r - c0.r) * ff) * b;
      out.g = (c0.g + (c1.g - c0.g) * ff) * b;
      out.b = (c0.b + (c1.b - c0.b) * ff) * b;
      leds_16[HALF + i] = out;
    } else {
      // Chromatic (no palette): frame-constant chroma colour, scaled per LED.
      const SQ15x16 b = SQ15x16(bright);
      CRGB16 out;
      out.r = chromaBase.r * b;
      out.g = chromaBase.g * b;
      out.b = chromaBase.b * b;
      leds_16[HALF + i] = out;
    }
  }

  // Re-zero the lower half (colour touched only the upper half), then fold the
  // coloured upper half down to the physical centre 79/80.
  memset(leds_16, 0, sizeof(CRGB16) * HALF);
  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);
}
