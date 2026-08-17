#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
#include "k1_vp_audio_access.h"

// ============================================================================
// light_mode_chroma_constellation — "Chroma Constellation" (mode 25): the
// chord's SHAPE rendered as a spatial pattern, flowed outward.
// ----------------------------------------------------------------------------
// METHOD SUMMARY (Pass 1–6, compact — see docs/architecture/effect-decomposition):
//
// Pass 1 · What it is: the only mode that renders HARMONY as space. The 12
//   pitch classes (snap.chroma_pc, A-origin) are pinned to 12 fixed positions
//   on the upper half, ordered by CIRCLE-OF-FIFTHS rank so harmonically
//   adjacent pitch classes are spatially adjacent — a triad reads as a tight
//   cluster of stars, a dissonant cluster as scattered points. Each frame the
//   live constellation is injected and the whole image is transported outward,
//   leaving a flowing river of harmonic history. Spectrum-River class
//   (frequency-as-space lineage), with the spatial axis re-keyed from raw
//   frequency to pitch class on the circle of fifths.
//
// Pass 2 · The verbs: Flow (draw_sprite outward, audio-driven drift) →
//   Smooth (per-pitch-class EMA) → Inject constellation (12 fixed points,
//   palette colour by pitch class, brightness by chroma energy) → Clear lower
//   half → Finalise (clamp + snapshot) → Mirror.
//
// Pass 3 · Six layers (inline): L1 Feature = chroma_pc[12] (A-origin, [0,1])
//   + spectral_energy/novelty/silence gates; L2 State = leds_prev_buffer (the
//   transported trail IS the memory) + fx.cc_chroma_smooth[12] EMA +
//   fx.cc_last_ms; L3 Spatial = pc → HALF + ((cof_rank+0.5)/12)·(HALF−1),
//   cof_rank=(pc·7)%12 (gcd(7,12)=1 → bijective, 12 distinct stars ~6.6 px
//   apart); L4 Colour = palette-native, hue = pc/12 (A-origin wheel, the same
//   convention as chromagram_centroid_hue), NEVER raw HSV; L5 Temporal =
//   drift = base · (0.4 + 0.6·spectral_energy), dt-stable via frame=dt·120,
//   trail alpha 0.90 (0.82 in quiet); L6 Clamps = EMA floor gate 0.06, inject
//   gain 0.90, finalize_additive_frame overflow clamp.
//
// Pass 4 · Levers: CC_DRIFT_BASE (history speed), CC_TRANSPORT_ALPHA (trail
//   length — >0.90 risks mechanical hold), CC_EMA (star attack/release),
//   CC_FLOOR (constellation sparsity), CC_INJECT_GAIN (white-out headroom).
//
// Pass 5 · Maths → perception: the circle-of-fifths permutation turns
//   harmonic distance into spatial distance, so chord QUALITY becomes a
//   visible cluster shape; the EMA (~0.15/frame) makes stars swell and fade
//   like bowed notes instead of flickering with the raw chroma; the outward
//   transport turns chord changes into departing constellations — harmony
//   history you can watch leave.
//
// Pass 6 · Reusable principle: ANY low-dimensional musical vector can become
//   a constellation — fix its components to perceptually-ordered positions,
//   EMA the energies, inject, transport. The circle-of-fifths re-rank is the
//   key move: order the axis by PERCEPTUAL adjacency, not index adjacency.
//
// Laws honoured: Strobe Law — no global full-field brightness modulation;
// every brightness is a per-star chroma energy. Organic Law — no autonomous
// wall-clock oscillator; the only motion is the transport, and its speed is
// audio-mapped (spectral energy). Audio reads ONLY via k1_vp_audio_snapshot_read().
// Persistent state ONLY in ChannelEffectState (cc_* fields) — no heap, no
// file-scope mutable statics.
// ============================================================================

static const float CC_DRIFT_BASE      = 0.35f;  // outward px-equivalents/frame at NR=128
static const float CC_TRANSPORT_ALPHA = 0.90f;  // trail persistence (Spectrum-River canon)
static const float CC_QUIET_ALPHA     = 0.82f;  // faster fade when presence is lost
static const float CC_EMA             = 0.15f;  // per-frame chroma smoothing coefficient
static const float CC_FLOOR           = 0.06f;  // skip near-silent pitch classes
static const float CC_INJECT_GAIN     = 0.90f;  // additive white-out headroom

static float cc_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static bool cc_presence_ok(const K1AudioSnapshot& snap) {
  return !(snap.spectral_energy < 0.08f && snap.novelty < 0.08f);
}

void light_mode_chroma_constellation(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  // dt — computed and clamped exactly as dense_forge_chord (frame-rate stable).
  const uint32_t prev_ms = fx.cc_last_ms;
  const uint32_t now_ms = millis();
  float dt = (prev_ms != 0) ? float(now_ms - prev_ms) * 0.001f : (1.0f / 120.0f);
  fx.cc_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;

  K1AudioSnapshot snap = k1_vp_audio_snapshot_read();

  const float energy = cc_clamp01(snap.spectral_energy);
  const bool hard_gate = snap.silence;
  const bool presence_ok = cc_presence_ok(snap);
  const float inject_scale = (presence_ok && !hard_gate) ? 1.0f : 0.0f;

  // MAPPING source: 12-bin pitch-class chroma (A-origin, [0,1]).
#ifdef K1_CHORD_V2
  float chroma[12];
  for (uint8_t pc = 0; pc < 12; pc++) {
    chroma[pc] = cc_clamp01(snap.chroma_pc[pc]);
  }
#else
  // Fallback without K1_CHORD_V2: chromagram_smooth[12] is the SAME A-origin
  // pitch-class fold (globals.h, fed by make_smooth_chromagram), so the mode
  // renders identically-shaped output — only the smoothing lineage differs.
  float chroma[12];
  for (uint8_t pc = 0; pc < 12; pc++) {
    chroma[pc] = cc_clamp01(float(chromagram_smooth[pc]));
  }
#endif

  // Per-pitch-class EMA — the stars swell and fade rather than flicker.
  for (uint8_t pc = 0; pc < 12; pc++) {
    fx.cc_chroma_smooth[pc] += (chroma[pc] - fx.cc_chroma_smooth[pc]) * CC_EMA;
    fx.cc_chroma_smooth[pc] = cc_clamp01(fx.cc_chroma_smooth[pc]);
  }

  // MOTION: pure transport — drift speed audio-mapped to spectral energy
  // (Organic Law: no autonomous oscillator; quiet music drifts slowly, loud
  // music streams). dt-stable and resolution-independent like dense_forge.
  const float frame = dt * 120.0f;
  const float nr_scale = float(NATIVE_RESOLUTION) / 128.0f;
  const float drift = CC_DRIFT_BASE * (0.4f + 0.6f * energy) * nr_scale * frame;

  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  if (!hard_gate) {
    const SQ15x16 transport_alpha =
        SQ15x16(presence_ok ? CC_TRANSPORT_ALPHA : CC_QUIET_ALPHA);
    draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION,
                drift, transport_alpha);
  }

  // Inject the constellation: pitch class pc → circle-of-fifths rank
  // (pc·7 mod 12) → fixed position on the upper half. Hue = pc/12 on the
  // A-origin palette wheel (matches chromagram_centroid_hue convention);
  // brightness = EMA-smoothed chroma energy. Per-star only — never global.
  for (uint8_t pc = 0; pc < 12; pc++) {
    const float level = fx.cc_chroma_smooth[pc];
    if (level < CC_FLOOR) continue;  // floor gate: constellation stays sparse
    const uint8_t cof_rank = (uint8_t)((pc * 7) % 12);
    const uint16_t idx =
        HALF + (uint16_t)(((float(cof_rank) + 0.5f) / 12.0f) * float(HALF - 1));
    const float b = level * CC_INJECT_GAIN * inject_scale;
    if (b <= 0.0f) continue;
    const float hue = float(pc) / 12.0f;
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(b));
    leds_16[idx].r += col.r;
    leds_16[idx].g += col.g;
    leds_16[idx].b += col.b;
  }

  // Keep the constellation in the mirror-authoritative upper half only.
  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  finalize_additive_frame(leds_16, leds_prev_buffer, true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
