#include "lightshow_modes.h"
#include "k1_tempo.h"
#include "k1_audio_snapshot.h"
#include "easing.h"
#include "beat_pulse_math.h"
#include <math.h>

// ============================================================================
// light_mode_beat_pulse — faithful port of firmware-v3 BeatPulseResonant (0x1404).
// ----------------------------------------------------------------------------
// Two rings CONTRACT edge -> centre on every beat: a white ~280 ms attack snap
// chased by a warm ~480 ms Gaussian body. The ONLY inward transport in the gem
// set. Pure closed-form of the time since the last beat — no trail buffer,
// deterministic, scalar state only. Beat source is the tempo tracker with a
// 128 BPM metronome fallback when tempo confidence is low; true silence is
// handled globally by the go-dark layer, so no per-effect silence gate here.
//
// The ring MATHS lives in beat_pulse_math.h (host-unit-tested); this file does
// the fork-specific SQ15x16 render + centre-origin mirror. British English.
// ============================================================================

// Body hue travels a palette-bounded amount as the ring contracts, so the warm
// body shades across its inward sweep without a free-running hue (no-rainbow).
static const float BEAT_PULSE_BODY_HUE_TRAVEL = 0.18f;
// Per-beat warm/cool offset from the beat's band balance — consecutive beats
// differ in colour (part of the de-bland fix).
static const float BEAT_PULSE_PERBEAT_HUE     = 0.15f;
// Continuous bass-breathing centre glow gain — the plate is ALIVE between beats
// instead of dark-flash-dark. Eased, centre-weighted, bass-driven.
static const float BEAT_PULSE_GLOW_GAIN       = 0.34f;

void light_mode_beat_pulse(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;  // 80: author upper half, mirror down

  const uint32_t now_ms = millis();
  const float dt = k1ease::safe_dt(now_ms, fx.bpulse_last_ms);

  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  K1TempoEvent tempo = k1_tempo_read();

  // --- Beat timing: tempo-confidence gate + 128 BPM metronome fallback --------
  const bool tick = beat_pulse::computeBeatTick(
      /*audioAvailable=*/true, tempo.confidence, tempo.beat_tick,
      now_ms, fx.bpulse_last_beat_ms);
  if (tick) {
    // PER-BEAT VARIATION — the fix for "every beat identical / bland". The beat's
    // STRENGTH sets both its punch and its contraction SPEED (strong beat snaps in
    // faster = visible motion variation), and the band balance at the beat sets its
    // colour warmth — so no two beats look the same.
    const float bs = beat_pulse::clamp01(tempo.beat_strength);
    fx.bpulse_intensity = 0.40f + 0.60f * bs;                       // punch 0.40..1.0
    fx.bpulse_travel    = 1.30f - 0.55f * bs;                       // strong beat contracts faster (0.75..1.30)
    const float lo = beat_pulse::clamp01(snap.low_energy);
    const float hi = beat_pulse::clamp01(snap.high_energy);
    fx.bpulse_hue       = beat_pulse::clamp01(hi / (lo + hi + 0.001f));  // warm(bass) -> cool(treble)
  }

  // Age since the last beat; dark until the first beat has occurred.
  const float age_ms = (fx.bpulse_last_beat_ms == 0)
                         ? 999999.0f
                         : float(now_ms - fx.bpulse_last_beat_ms);
  const float intensity = fx.bpulse_intensity;
  const float travel    = (fx.bpulse_travel > 0.3f) ? fx.bpulse_travel : 1.0f;

  // CONTINUOUS BASS-BREATHING GLOW — the fix for "dark-flash-dark deadness". A soft
  // centre bed breathes with bass BETWEEN beats so the plate is alive, not dead
  // until the next hit. Eased (fast attack / slow release, no raw audio -> pixel);
  // true silence is darkened globally by the go-dark layer, so no gate needed here.
  const float bass_now = beat_pulse::clamp01(0.6f * snap.low_energy + 0.4f * snap.vu_level);
  fx.bpulse_glow = k1ease::follow(fx.bpulse_glow, bass_now, dt, 0.06f, 0.35f);
  const float glow_gain = BEAT_PULSE_GLOW_GAIN * beat_pulse::clamp01(fx.bpulse_glow);

  // --- Frame-constant body colour (sampled ONCE; scaled per-LED below) --------
  // Palette position travels with the (per-beat scaled) ring, plus the per-beat
  // warm/cool offset — a richer colour sweep than the near-static original.
  const float palette_pos = beat_pulse::bodyPalettePos(age_ms, beat_pulse::BODY_TRAVEL_MS * travel);
  const float hue_off = palette_pos * BEAT_PULSE_BODY_HUE_TRAVEL
                      + fx.bpulse_hue * BEAT_PULSE_PERBEAT_HUE;
  const CRGB16 body_base = effect_particle_colour(rp, render_secondary, hue_off, SQ15x16(1.0f));

  // Lower half is authored black; the mirror folds the upper half down onto it.
  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0;
  }

  // --- Closed-form field: overwrite the upper half fresh each frame -----------
  const SQ15x16 kHalf = SQ15x16(0.5f);
  for (uint16_t dist = 0; dist < HALF; dist++) {
    const float dist01 = (float(dist) + 0.5f) / float(HALF);  // ~0=centre, ~1=edge
    const float a_hit = beat_pulse::attackHit(dist01, age_ms, intensity,
                                              beat_pulse::ATTACK_TRAVEL_MS * travel);
    const float b_hit = beat_pulse::bodyHit(dist01, age_ms, intensity,
                                            beat_pulse::BODY_TRAVEL_MS * travel);

    // Continuous centre-weighted glow bed (brightest at 79/80, fades to the edge)
    // folded into the body level so the plate breathes between beats.
    const float edge = 1.0f - dist01;
    const float glow = glow_gain * edge * edge;
    const float body_level = beat_pulse::clamp01(b_hit + glow);

    const SQ15x16 bh  = SQ15x16(body_level);
    const SQ15x16 awf = SQ15x16(a_hit * beat_pulse::ATTACK_WHITE);  // neutral white snap

    // Composite = per-channel AVERAGE of body and white attack (firmware-v3
    // ColourUtil::additive is an average, not a sum — avoids white wash-out).
    CRGB16& px = leds_16[HALF + dist];
    px.r = (body_base.r * bh + awf) * kHalf;
    px.g = (body_base.g * bh + awf) * kHalf;
    px.b = (body_base.b * bh + awf) * kHalf;
  }

  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/false);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
