#include "lightshow_modes.h"
#include "easing.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"
#include <math.h>

// ============================================================================
// light_mode_moire_cathedral — LGP Moire Cathedral (5L-AR), ported from
// firmware-v3 effect 0x1C08 (LGPMoireCathedralAREffect).
// ----------------------------------------------------------------------------
// Two close-pitch sinusoidal gratings interfere to form arch-like ribs. The
// two gratings drift in OPPOSITE directions over time, so their interference
// pattern (the moire) slowly MIGRATES outward/inward from the centre — the
// travelling-moire signature of this GEM. Audio drives rib brightness directly:
// bass energy sets the base level, mid energy shifts the grating pitch, a beat
// impact sharpens and boosts the arch peaks, and silence fades the plate dark.
//
// Fork adaptation notes (vs. the donor):
//  - Donor drew both strip halves via SET_CENTER_PAIR; the fork authors ONLY
//    the upper half [HALF,160) and lets mirror_image_downwards() reflect it.
//  - This is a FIELD, recomputed in full every frame — NO trail history, so
//    finalize_additive_frame() is called with store_history=false and the
//    prev buffer is never read.
//  - Donor hue came from a chroma-angle EMA plus a FREE-RUNNING gHue rainbow.
//    The free-running gHue is DROPPED here (no rainbow). Hue is anchored purely
//    by effect_particle_colour()'s internal chroma centroid, sampled ONCE per
//    frame (palette/chroma-bounded, inherently no-rainbow), then scaled per-LED
//    by the moire field. This also keeps the internal chroma-centroid trig off
//    the per-LED hot path.
// ============================================================================

static constexpr float MOIRE_TWO_PI = 6.28318530717958647692f;

// Band envelopes: fast attack, SLOW release (asymmetric) so the rib field eases
// out over ~350 ms instead of hard-cutting on the off-beat — EFFECT_DEVELOPMENT
// _STANDARD §7.1 / fork STROBE LAW (no raw audio -> pixel).
static constexpr float MOIRE_BAND_ATTACK_TAU  = 0.05f;
static constexpr float MOIRE_BAND_RELEASE_TAU = 0.35f;

// Beat-strength envelope: same asymmetric easing so beat_mod glides rather than
// pumping the whole plate 0.4<->1.0 at beat rate.
static constexpr float MOIRE_BEAT_ATTACK_TAU  = 0.04f;
static constexpr float MOIRE_BEAT_RELEASE_TAU = 0.35f;

// Max-follower (peak-normalisation) attack/decay + floor — donor kFollower*.
static constexpr float MOIRE_FOLLOW_ATTACK_TAU = 0.058f;
static constexpr float MOIRE_FOLLOW_DECAY_TAU  = 0.500f;
static constexpr float MOIRE_FOLLOW_FLOOR      = 0.04f;

// Beat-impact decay + smoothed silence gate time-constants.
static constexpr float MOIRE_IMPACT_DECAY_TAU = 0.200f;
static constexpr float MOIRE_SILENCE_TAU      = 0.250f;

// Field floors — the fix for Captain's "black-line segmenting / cheap sparse-strip
// look". The interference nodes (|g1-g2|==0) used to render pure BLACK, so ribs
// read as sparse lit bars on black. MOIRE_FLOOR is the node level (ribs swell
// above it to 1.0) so the plate is a continuous luminous bed with arches on top.
// MOIRE_AUDIO_FLOOR keeps a quiet passage dim rather than collapsing the arches
// into black. Both are the primary A/B knobs.
static constexpr float MOIRE_FLOOR       = 0.30f;   // node (between-rib) level [0..1]
static constexpr float MOIRE_AUDIO_FLOOR = 0.35f;   // quiet-passage bed level [0..1]

// Temporal persistence trail — restores the donor's fadeToBlackByDt anti-strobe
// mechanism the fork port had DROPPED (store_history was false). A departing rib
// fades gracefully instead of snapping to black per frame; louder bass = longer
// trail (donor scaled fadeAmt by 1-normBass). Instant attack via MAX-composite.
static constexpr float MOIRE_TRAIL_MIN   = 4.0f;    // fade rate (per s) at loud bass -> long trail (~250 ms)
static constexpr float MOIRE_TRAIL_SCALE = 8.0f;    // + (1-normBass) * this -> quiet = short trail (~83 ms)

static inline float moire_clamp01(float x) {
  if (!isfinite(x) || x < 0.0f) return 0.0f;
  if (x > 1.0f) return 1.0f;
  return x;
}
static inline float moire_clampf(float x, float lo, float hi) {
  if (x < lo) return lo;
  if (x > hi) return hi;
  return x;
}

void light_mode_moire_cathedral(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;  // == 80

  // --- Frame-rate-independent dt (kit idiom) --------------------------------
  const uint32_t now_ms = millis();
  float dt = (fx.moire_last_ms != 0) ? float(now_ms - fx.moire_last_ms) * 0.001f
                                     : (1.0f / 120.0f);
  fx.moire_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;

  // --- Audio (value-copy snapshots) -----------------------------------------
  K1AudioSnapshot snap = k1_audio_snapshot_read();
  K1TempoEvent tempo   = k1_tempo_read();

  const float raw_bass  = moire_clamp01(snap.low_energy);   // donor bass()
  const float raw_mid   = moire_clamp01(snap.mid_energy);   // donor mid()
  const float beat_str  = moire_clamp01(tempo.beat_strength);

  // Smoothed silence gate: soft fade to dark in silence (fork silentScale
  // stand-in — snap.silence is a hard boolean, so we ramp it).
  const float sil_target = snap.silence ? 0.0f : 1.0f;
  fx.moire_sil += (sil_target - fx.moire_sil) * (1.0f - expf(-dt / MOIRE_SILENCE_TAU));
  const float sil_scale = moire_clamp01(fx.moire_sil);

  // --- Asymmetric band envelopes (fast attack, slow release) ----------------
  // Transients light instantly, then the rib field decays gracefully over
  // ~350 ms — replaces the old symmetric 50 ms EMA that dropped near-black
  // between beats (the "stutter / on-off" Captain rejected).
  fx.moire_bass = k1ease::follow(fx.moire_bass, raw_bass, dt, MOIRE_BAND_ATTACK_TAU, MOIRE_BAND_RELEASE_TAU);
  fx.moire_mid  = k1ease::follow(fx.moire_mid,  raw_mid,  dt, MOIRE_BAND_ATTACK_TAU, MOIRE_BAND_RELEASE_TAU);

  // --- Max-follower normalisation (donor pattern) ---------------------------
  {
    const float aA = 1.0f - expf(-dt / MOIRE_FOLLOW_ATTACK_TAU);
    const float dA = 1.0f - expf(-dt / MOIRE_FOLLOW_DECAY_TAU);
    if (fx.moire_bass > fx.moire_bass_max) fx.moire_bass_max += (fx.moire_bass - fx.moire_bass_max) * aA;
    else                                   fx.moire_bass_max += (fx.moire_bass - fx.moire_bass_max) * dA;
    if (fx.moire_bass_max < MOIRE_FOLLOW_FLOOR) fx.moire_bass_max = MOIRE_FOLLOW_FLOOR;
    if (fx.moire_mid > fx.moire_mid_max) fx.moire_mid_max += (fx.moire_mid - fx.moire_mid_max) * aA;
    else                                 fx.moire_mid_max += (fx.moire_mid - fx.moire_mid_max) * dA;
    if (fx.moire_mid_max < MOIRE_FOLLOW_FLOOR) fx.moire_mid_max = MOIRE_FOLLOW_FLOOR;
  }
  const float norm_bass = moire_clamp01(fx.moire_bass / fx.moire_bass_max);
  const float norm_mid  = moire_clamp01(fx.moire_mid  / fx.moire_mid_max);

  // --- Beat impact envelope (arch-peak boost; already a graceful decay) -----
  if (beat_str > fx.moire_impact) fx.moire_impact = beat_str;
  fx.moire_impact *= expf(-dt / MOIRE_IMPACT_DECAY_TAU);

  // --- Beat modulation: eased, with a 0.4 floor (never blackout off-phase) --
  // Previously 0.3 + 0.7 * RAW beat_strength multiplied the whole field — a
  // hard 0.3<->1.0 pump at beat rate. Now the beat strength is asymmetrically
  // smoothed and the floor is 0.4 (STANDARD §4.4), so the plate breathes.
  fx.moire_beat_env = k1ease::follow(fx.moire_beat_env, beat_str, dt, MOIRE_BEAT_ATTACK_TAU, MOIRE_BEAT_RELEASE_TAU);
  const float beat_mod = 0.4f + 0.6f * fx.moire_beat_env;

  // --- Speed: MOOD-mapped drift (donor used ctx.speed/50; the kit signature
  // exposes no per-effect speed param, so MOOD is the fork's mood/speed knob).
  const float speed_norm = 0.4f + 1.2f * moire_clamp01(rp->MOOD);

  // Grating pitches: mid energy nudges the pitch (donor p1/p2). Widened from the
  // donor's ~7.5 px to ~13 px so the half-strip carries ~6 BROAD arches instead of
  // ~11 thin ribs — the fork's thin-rib pitch was a big part of the "sparse strip"
  // read. p2 stays a hair off p1 so the two gratings still beat into a slow moire.
  const float p1 = moire_clampf(13.0f + 4.0f * (norm_mid - 0.5f), 11.0f, 16.0f);
  const float p2 = p1 + 0.6f;

  // Opposite-direction angular speeds — this is what makes the moire TRAVEL.
  const float w1 = 0.65f + 0.40f * speed_norm;
  const float w2 = 0.58f + 0.35f * speed_norm;

  // Advance the migration phase accumulator (donor m_t += tRate * dtVis).
  const float t_rate = 0.85f + 3.5f * speed_norm;
  fx.moire_t += t_rate * dt;

  // Rib sharpening: bass sharpens, beat impact boosts (donor ribPow). SOFTENED
  // from the donor's 1.30-2.50 to 1.00-1.70 so ribs stay BROAD (not thin spikes
  // on black) — part of the fix for the "sparse strip" read. The raised floor
  // below carries the between-rib bed; the sharpening only shapes the arch peaks.
  const float rib_pow = moire_clampf(1.0f + 0.35f * norm_bass + 0.25f * fx.moire_impact, 1.0f, 1.7f);

  // --- Base colour: sampled ONCE per frame (palette/chroma-anchored, no
  // rainbow). A small mid-driven hue offset keeps it musically alive without
  // a free-running hue. Per-LED we only scale this colour by the field level.
  const float hue_offset01 = 0.08f * norm_mid;
  const CRGB16 base_col = effect_particle_colour(rp, render_secondary, hue_offset01, SQ15x16(1.0f));

  // --- Temporal-persistence field (restores the donor fadeToBlackByDt trail) --
  // Copy the previous frame forward and decay it toward black; the new rib field
  // is MAX-composited on top per LED (instant attack, graceful release) so a
  // departing arch fades out over ~83-250 ms instead of snapping black per frame
  // — the anti-strobe the fork port had dropped. Louder bass = slower fade.
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
  const float trail_rate = MOIRE_TRAIL_MIN + MOIRE_TRAIL_SCALE * (1.0f - norm_bass);
  const SQ15x16 trail_fade = SQ15x16(expf(-trail_rate * dt));
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
    leds_16[i].r *= trail_fade;
    leds_16[i].g *= trail_fade;
    leds_16[i].b *= trail_fade;
  }
  // Author the upper half [HALF, NATIVE_RESOLUTION); the lower half is regenerated
  // by mirror_image_downwards, so clear it (it must not carry a stale faded trail).
  for (uint16_t i = 0; i < HALF; ++i) {
    leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0;
  }

  // --- Per-frame hot-path setup (peak-timing optimisation) ------------------
  // (1) Grating phase recurrence. Each grating's argument advances by a
  //     CONSTANT step as the LED index x increments (donor evaluated a fresh
  //     sinf per LED — ~160 sinf/frame). We instead seed sin/cos at x=0 and
  //     rotate a unit vector one step per LED:
  //         sin(t+d) = sin(t)cos(d) + cos(t)sin(d)
  //         cos(t+d) = cos(t)cos(d) - sin(t)sin(d)
  //     This is mathematically the SAME grating arguments — identical
  //     travelling-moire look — but costs 8 trig seeds/frame plus a handful of
  //     mults per LED. Magnitude drift over 80 steps is < 0.1 %, invisible.
  const float d1  =  MOIRE_TWO_PI / p1;   // g1 per-LED phase increment
  const float d2  =  MOIRE_TWO_PI / p2;   // g2 per-LED phase increment
  const float th1 =  fx.moire_t * w1;     // g1 phase at x=0 (+t drift)
  const float th2 = -fx.moire_t * w2;     // g2 phase at x=0 (-t drift, opposite)
  float s1 = sinf(th1), c1 = cosf(th1);
  float s2 = sinf(th2), c2 = cosf(th2);
  const float cd1 = cosf(d1), sd1 = sinf(d1);
  const float cd2 = cosf(d2), sd2 = sinf(d2);

  // (2) Rib sharpening without powf. rib_pow is a per-frame CONSTANT in
  //     [1.30, 2.50], so wave^rib_pow is approximated by a fixed blend of
  //     wave / wave^2 / wave^3 whose weights are computed ONCE here (exact at
  //     integer exponents, visually indistinguishable between them). Replaces
  //     80 per-LED powf/frame — the peak-timing offender — with 3 mults + 2
  //     adds per LED.
  float sh1, sh2, sh3;   // sharp = sh1*wave + sh2*wave^2 + sh3*wave^3
  if (rib_pow <= 2.0f) {
    const float f = rib_pow - 1.0f;      // 0.30 .. 1.00
    sh1 = 1.0f - f; sh2 = f;        sh3 = 0.0f;
  } else {
    const float f = rib_pow - 2.0f;      // 0.00 .. 0.50
    sh1 = 0.0f;     sh2 = 1.0f - f; sh3 = f;
  }

  // Note: the donor added a small per-LED hue ramp (progress*12) on top of the
  // per-frame hue; the fork drops it to keep the palette-centroid trig off the
  // per-LED path (one colour sample per frame, scaled by the field level).
  for (uint16_t dist = 0; dist < HALF; dist++) {
    // Grating values at this LED = current recurrence state.
    const float g1 = s1;
    const float g2 = s2;

    // Moire interference -> rib mask, GENTLY sharpened (broad arches, not spikes).
    const float wave  = moire_clamp01(fabsf(g1 - g2) * 0.55f);
    const float wave2 = wave * wave;
    const float wave3 = wave2 * wave;
    const float sharp = sh1 * wave + sh2 * wave2 + sh3 * wave3;

    // Continuous luminous bed + ribs on TOP: the plate reads as a flowing
    // cathedral of light rather than lit ribs on black. rib_field never falls
    // below MOIRE_FLOOR (nodes are DIM, not black -> kills the "black-line
    // segmenting"); audio_level keeps a quiet passage as a dim bed, not black.
    const float rib_field   = MOIRE_FLOOR + (1.0f - MOIRE_FLOOR) * sharp;
    const float audio_level = MOIRE_AUDIO_FLOOR + (1.0f - MOIRE_AUDIO_FLOOR) * norm_bass;
    const float impact_add  = fx.moire_impact * sharp * 0.30f;
    float brightness = (rib_field * audio_level + impact_add) * beat_mod * sil_scale;
    brightness = moire_clamp01(brightness);

    // MAX-composite the new field over the decayed trail (instant attack, graceful
    // release). Colour is the per-frame palette-anchored base scaled by the field.
    const SQ15x16 b = SQ15x16(brightness);
    const SQ15x16 nr = base_col.r * b;
    const SQ15x16 ng = base_col.g * b;
    const SQ15x16 nb = base_col.b * b;
    CRGB16& px = leds_16[HALF + dist];
    if (nr > px.r) px.r = nr;
    if (ng > px.g) px.g = ng;
    if (nb > px.b) px.b = nb;

    // Advance both grating phases by one LED step (unit-vector rotation).
    const float n1 = s1 * cd1 + c1 * sd1;
    c1 = c1 * cd1 - s1 * sd1;
    s1 = n1;
    const float n2 = s2 * cd2 + c2 * sd2;
    c2 = c2 * cd2 - s2 * sd2;
    s2 = n2;
  }

  // Store the composited field as history so the persistence trail carries to the
  // next frame (restores the donor's temporal smoothing).
  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
