#include "lightshow_modes.h"
#include "k1_onset_beat.h"
#include "k1_vp_audio_access.h"

// ============================================================================
// light_mode_comet — "Comet": onset-driven traveling heads with palette trails.
// ----------------------------------------------------------------------------
// Reference lineage: WAVEFORM family — leds_16 IS the persisted trail (faded in
// place; the dispatch seeds/stores it via channel.history), centre-origin,
// mirror-safe. The novelty (vs every current mode) is DISCRETE MOVING OBJECTS:
// each audio onset launches a bright "comet" head from the centre with momentum,
// leaving a fading trail. Bass onsets = slower/heavier; sharper onsets = faster.
//
// Colour (2026-06-02 fix v2): sampled LIVE every frame via
// effect_palette_or_chroma_colour — the SAME colour authority as BLOOM (palette
// mode -> selected palette; chromatic default -> note-sum HSV +
// force_hue(chroma_val + hue_position) auto-shift). Colour is NOT frozen at
// launch: a per-comet frozen colour (v1) made every comet one flat colour, since
// the chromagram centroid is stable across onsets. Like BLOOM/WAVEFORM, the
// single live colour evolves over time and the faded trail preserves the colour
// history, so the strip sweeps the palette. Comets supply MOTION; colour matches
// the reference family exactly.
//
// v5 (2026-06-02) — BASS/KICK-ONLY (Captain: "tune comet just to track bass/kick
// /hits — at least that way it can do ONE THING right"). A discrete/high-salience
// effect demands a perfect, decodable lock-on; trying to track everything (v4's
// bass/snare/hat grammar + broadband onset) still read as "not tracking properly".
// So Comet now does exactly ONE thing:
//  - Fire on `bass_onset` ONLY (ignore broadband `onset`, which also fires on
//    pads/sweeps/vocals). bass_onset is the low-band ATTACK — the cleanest,
//    most-unambiguous "hit" — and the detector already gates it on real transients.
//  - ONE class: every comet is a warm, big, slow, long-dwell kick. The viewer's
//    rule is trivial ("comet == kick") and therefore never wrong. Loud kicks are
//    simply bigger. No relative gate — catch EVERY clear kick (low absolute floor).
//  - SPEED is driven by the MOOD knob (v6 fix — like BLOOM/WAVEFORM/Aurora; v5's
//    fixed 0.45 px/fr crawl ignored MOOD entirely). MOOD=0 slow/dwelly .. MOOD=1
//    fast zip; the user dials the pace.
//  Comet-shaped head (bright core + trailing wake + glow) + mirror-safe spawn +
//  COMET_HEAD_GAIN white-out guard retained.
//  On kick-less material Comet is intentionally quiet (it's a kick visualiser —
//  honest, not broken). Deferred: continuous baseline; beat-lock (lite-stub tracker).
//
// Discipline: per-channel comet pool lives in ChannelEffectState (no statics, no
// heap); dt-scaled motion (fps-independent); reads via active_render_params().
// Comets launch toward the +end; with MIRROR_ENABLED (default) the mirror makes
// a symmetric centre-origin burst.
// ============================================================================

static const float   COMET_TRAIL_DECAY  = 0.05f;  // trail fade per 120fps-frame (lower => longer tail)
static const float   COMET_LIFE_DECAY   = 0.018f; // head life fade per frame
static const int     COMET_GLOW         = 2;      // soft halo px beyond radius
static const float   COMET_WAKE_STRETCH = 2.0f;   // trailing-wake span vs sharp leading edge (the "tail")
static const float   COMET_HEAD_GAIN    = 0.85f;  // peak additive weight (white-out guard)

// --- v5 BASS/KICK-ONLY lock-on (2026-06-02, Captain: "do ONE thing right") ---
// Comet visualises the KICK and nothing else: fire on bass_onset only (a clean
// low-band transient the detector already gates), one decodable class. Every
// comet == a kick, so the viewer's rule is trivial and never wrong.
static const float   COMET_MIN_STRENGTH = 0.06f;  // low floor: catch every clear kick
static const float   COMET_HUE_BASS     = 0.04f;  // warm/low palette position
// Speed is driven by the MOOD knob (like BLOOM/WAVEFORM/Aurora — MOOD is the
// universal motion control). MOOD=0 => slow/dwelly, MOOD=1 => fast zip. Scaled by
// NR/128 so visual speed is strip-length independent.
static const float   COMET_SPEED_MIN    = 0.60f;  // px/frame @120fps at MOOD=0
static const float   COMET_SPEED_MOOD   = 2.80f;  // + MOOD * this
static const float   COMET_SIZE_BASS    = 3.5f;   // head radius (px); loud kicks scale bigger
static const float   COMET_LIFE_BASS    = 1.00f;

void light_mode_comet(ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;

  // dt -> fps-independent frame scale (matches the waveform-family convention).
  const uint32_t now_ms = millis();
  float dt = (fx.comet_last_ms != 0) ? float(now_ms - fx.comet_last_ms) * 0.001f : (1.0f / 120.0f);
  fx.comet_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;
  const float frame = dt * 120.0f;

  // 1. Fade the persisted trail in place.
  float fade_f = 1.0f - (COMET_TRAIL_DECAY * frame);
  if (fade_f < 0.0f)   fade_f = 0.0f;
  if (fade_f > 0.999f) fade_f = 0.999f;
  const SQ15x16 fade = SQ15x16(fade_f);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }

  // 2. Launch a comet on a fresh BASS/KICK onset ONLY. Comet does ONE thing and
  //    does it right: visualise the kick. `bass_onset` is the low-band ATTACK (the
  //    detector already requires a real bass transient — bass_strength + attack +
  //    rise), so it is the most perceptually-unambiguous "hit". Broadband `onset`
  //    (which also fires on pads/sweeps/vocals) is deliberately IGNORED so EVERY
  //    comet == a kick: the viewer's rule is trivial and never wrong.
  const K1OnsetBeatEvent ev = k1_vp_onset_beat_read();
  const bool fresh = (ev.event_id != fx.comet_last_event_id);
  fx.comet_last_event_id = ev.event_id;
  if (fresh && ev.bass_onset) {
    float strength = ev.bass_onset_strength;
    if (strength < 0.0f) strength = 0.0f;
    if (strength > 1.0f) strength = 1.0f;
    if (strength >= COMET_MIN_STRENGTH) {  // low floor: catch EVERY clear kick (no relative gate)
      uint8_t slot = 0;
      float min_life = fx.comet_life[0];
      for (uint8_t i = 1; i < COMET_MAX; i++) {
        if (fx.comet_life[i] < min_life) { min_life = fx.comet_life[i]; slot = i; }
      }
      // Single KICK class: warm palette colour, big, slow, long dwell. Loud kicks
      // are simply BIGGER — the only modulation, so "comet == kick" stays pure.
      const uint16_t centre_px = NATIVE_RESOLUTION / 2;
      fx.comet_pos[slot]  = float(centre_px + (ev.event_id % 4u));
      fx.comet_vel[slot]  = (COMET_SPEED_MIN + COMET_SPEED_MOOD * float(rp->MOOD)) * (float(NATIVE_RESOLUTION) / 128.0f);
      fx.comet_hue[slot]  = COMET_HUE_BASS;
      fx.comet_size[slot] = COMET_SIZE_BASS * (0.80f + 0.40f * strength);
      fx.comet_life[slot] = COMET_LIFE_BASS;
    }
  }

  // 3. Advance + draw each live comet head. Colour is CLASS-CODED: palette mode
  //    samples the SELECTED gradient at the comet's fixed class position (so the
  //    viewer can decode bass vs snare vs hat; auto-shift folded in), chromatic
  //    mode falls back to the single live colour. Shape = bright leading core +
  //    long trailing wake (behind travel) + soft glow halo.
  const bool palette_owns = render_params_palette_owns_colour(rp, render_secondary);
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  for (uint8_t i = 0; i < COMET_MAX; i++) {
    if (fx.comet_life[i] <= 0.01f) continue;
    fx.comet_pos[i] += fx.comet_vel[i] * frame;
    if (fx.comet_pos[i] < 0.0f || fx.comet_pos[i] >= float(NATIVE_RESOLUTION)) {
      fx.comet_life[i] = 0.0f;
      continue;
    }

    const CRGB16 col = palette_owns
        ? clamp_crgb16(palette_manual_colour(pal, SQ15x16(fx.comet_hue[i]), SQ15x16(1.0)))
        : effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0));
    const float  life   = fx.comet_life[i];
    const float  radius = fx.comet_size[i];
    const int    dir    = (fx.comet_vel[i] >= 0.0f) ? 1 : -1;
    const int    centre = int(fx.comet_pos[i] + 0.5f);
    const int    reach  = int(radius) + COMET_GLOW;

    for (int d = -reach; d <= reach; d++) {
      const int idx = centre + d;
      if (idx < 0 || idx >= NATIVE_RESOLUTION) continue;
      const float ad = (d < 0) ? float(-d) : float(d);
      // Trailing side (behind the direction of travel) gets a long wake; the
      // leading edge is sharp => reads as a comet head + tail, not a fuzzy dot.
      const bool  trailing = (d * dir) < 0;
      const float span = trailing ? (radius * COMET_WAKE_STRETCH) : (radius * 0.7f);
      float f = 1.0f - (ad / (span + 1.0f));
      if (f < 0.0f) f = 0.0f;
      if (d == 0) f = 1.0f;                       // bright leading core
      const SQ15x16 w = SQ15x16(life * f * COMET_HEAD_GAIN);
      leds_16[idx].r += col.r * w;
      leds_16[idx].g += col.g * w;
      leds_16[idx].b += col.b * w;
    }
    fx.comet_life[i] *= (1.0f - COMET_LIFE_DECAY * frame);
  }

  // 4. Hue-preserving clamp (additive heads can exceed 1.0).
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i] = clamp_crgb16_preserve_sat(leds_16[i]);
  }

  // 5. Centre-origin mirror (respects the user MIRROR param).
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
