#include "lightshow_modes.h"
#include "k1_tempo.h"
#include <math.h>

// ============================================================================
// light_mode_tempo_comet — "Tempo Comet": beat-grid-locked travelling comets,
// driven by an internal BEAT FLYWHEEL (a phase-locked loop), not raw detection.
// ----------------------------------------------------------------------------
// NEW STANDALONE MODE (2026-06-04, v2). Composes a NEW MAPPING (a tempo-locked
// flywheel -> comet spawn) onto the OWNED Comet PARTICLE engine. Does NOT modify
// light_mode_comet.* — its own per-channel pool (tcomet_*).
//
// WHY A FLYWHEEL (the v1 lesson, Captain 2026-06-04): the confidence-from-ACF fix
// made the CONTINUOUS tempo effects (River, Waveform Tempo) steadier, but NOT this
// one — because a DISCRETE/particle effect has NO graceful degradation. A continuous
// effect maps tempo to flow VELOCITY, so any tracker wobble is an imperceptible
// nudge; a discrete effect maps tempo to a spawn EVENT, so every imperfect beat
// decision is a VISIBLE miss or spurious comet (the causality contract). The
// k1_tempo phase jitter (the 50 Hz re-anchor at k1_tempo.cpp:392-395, plus octave
// flips) is invisible in a flow but fatal in a comet sampled once per beat. v1 fired
// on a render-loop phase WRAP — maximally exposed -> "lost in the woods".
//
// THE FLYWHEEL (gives the discrete effect graceful degradation):
//   - Run an internal beat phase at the SMOOTHED LOCKED BPM (learned only when
//     confident; HELD through octave flips via a ratio guard -> inertia).
//   - GENTLY phase-lock it to the tracker's phase01 (low gain -> filters the
//     re-anchor jitter, still tracks real drift).
//   - Fire ONE comet per internal-clock beat. COAST up to TC_COAST_BEATS (~2 bars)
//     through confidence dips, then stand down (and forget the tempo so it re-locks
//     fresh on the next song section). No random firing in genuine no-beat passages.
//
// CHARACTER PRESERVED (Captain rated v1 7.7 for its character — do not flatten it):
//   velocity + size scale with beat_strength -> strong beats ZOOM to the edge ("show
//   of force"), weak beats SKIP short ("skipping-stone"). The multiple identities
//   emerge from ONE reliable mechanism; live colour + trail give the rest.
//
// THE DESIGN LAW [MEASURED]: the lock is read from a TRAVELLING object (continuous
// per-frame position integration), never a global flash -> cannot strobe. vp-probe
// excluded-by-roster; under led_thread_halt: frozen tempo + fixed dt + NO spawn ->
// deterministic. No heap; per-channel pool + flywheel state in ChannelEffectState.
// ============================================================================

static const float TC_TRAIL_DECAY = 0.05f;   // trail fade per 120fps-frame
static const float TC_LIFE_DECAY  = 0.018f;  // head life fade per frame
static const int   TC_GLOW        = 2;       // soft halo px beyond radius
static const float TC_WAKE_STRETCH= 2.0f;    // trailing-wake span vs sharp leading edge
static const float TC_HEAD_GAIN   = 0.85f;   // peak additive weight (white-out guard)
static const float TC_PALETTE_SPREAD = 0.32f; // palette-position span over a comet's travel
static const float TC_SIZE        = 3.5f;    // base head radius (px)
static const float TC_CONF_LO     = 0.30f;
static const float TC_CONF_HI     = 0.60f;
// Flywheel knobs (the dials for Captain's eye):
static const float TC_RESYNC_HZ   = 2.0f;    // phase-lock rate to the tracker (higher=tighter/jitterier, lower=stiffer)
static const int   TC_COAST_BEATS = 8;       // coast ~2 bars through confidence dips before standing down
static const float TC_BPM_EMA     = 0.05f;   // smoothing of the learned locked BPM
static const float TC_REACH_FRAC  = 0.92f;   // STRONG-beat reach (fraction of half-strip) by next beat -> fast zoom
static const float TC_REACH_MIN   = 0.45f;   // WEAK-beat reach -> short skipping-stone
static const float TC_STRENGTH_FLOOR = 0.35f;// keep coasting/weak comets visible

static inline float tc_smoothstep(float lo, float hi, float x) {
  if (hi <= lo) return (x >= hi) ? 1.0f : 0.0f;
  float t = (x - lo) / (hi - lo);
  if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;
  return t * t * (3.0f - 2.0f * t);
}

void light_mode_tempo_comet(ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;

  // ── dt + frozen, deterministic path under the VP probe ───────────────────────
  const bool probe = led_thread_halt;
  uint32_t now_ms = probe ? 0u : millis();
  float dt = (fx.tcomet_last_ms != 0) ? float(now_ms - fx.tcomet_last_ms) * 0.001f : (1.0f / 120.0f);
  if (probe) dt = 1.0f / 120.0f; else fx.tcomet_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f; else if (dt > 0.05f) dt = 0.05f;
  const float frame = dt * 120.0f;

  K1TempoEvent t;
  if (probe) {
    t.bpm = 120.0f; t.phase01 = 0.0f; t.confidence = 1.0f;
    t.beat_tick = false; t.locked = true; t.beat_strength = 1.0f;
  } else {
    t = k1_tempo_read();
  }

  // 1. Fade the persisted trail in place.
  float fade_f = 1.0f - (TC_TRAIL_DECAY * frame);
  if (fade_f < 0.0f) fade_f = 0.0f; if (fade_f > 0.999f) fade_f = 0.999f;
  const SQ15x16 fade = SQ15x16(fade_f);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade; leds_16[i].g *= fade; leds_16[i].b *= fade;
  }

  // 2. BEAT FLYWHEEL ──────────────────────────────────────────────────────────
  const float gate   = tc_smoothstep(TC_CONF_LO, TC_CONF_HI, t.confidence);
  const bool  confident = gate >= 0.5f;
  float bpm = t.bpm; if (bpm < 40.0f) bpm = 40.0f; if (bpm > 200.0f) bpm = 200.0f;

  // Learn/hold the locked BPM only when confident; HOLD through octave flips (ratio
  // guard) so 72<->144 jumps don't whipsaw the clock.
  if (confident) {
    if (fx.tcomet_locked_bpm <= 0.0f) {
      fx.tcomet_locked_bpm = bpm;
    } else {
      const float ratio = bpm / fx.tcomet_locked_bpm;
      if (ratio > 0.70f && ratio < 1.40f) {                 // same tempo octave -> track
        fx.tcomet_locked_bpm += (bpm - fx.tcomet_locked_bpm) * TC_BPM_EMA;
      }
      // else: octave flip / spurious -> hold the established tempo (flywheel inertia)
    }
    fx.tcomet_coast_beats = 0;                               // confident now -> reset coast
  }
  const float run_bpm = (fx.tcomet_locked_bpm > 0.0f) ? fx.tcomet_locked_bpm : bpm;

  // Advance the internal beat phase at run_bpm.
  fx.tcomet_beat_phase += (run_bpm / 60.0f) * dt;

  // Gentle phase-lock to the tracker ONLY when confident (low gain filters the
  // re-anchor jitter that breaks naive wrap-detection). Error wrapped to [-0.5,0.5).
  if (confident) {
    float err = t.phase01 - fx.tcomet_beat_phase;
    err -= floorf(err);
    if (err > 0.5f) err -= 1.0f;
    fx.tcomet_beat_phase += (TC_RESYNC_HZ * dt) * err;
  }

  // Internal-clock beat wrap.
  bool internal_beat = false;
  if (fx.tcomet_beat_phase >= 1.0f) { fx.tcomet_beat_phase -= floorf(fx.tcomet_beat_phase); internal_beat = true; }
  if (fx.tcomet_beat_phase < 0.0f) fx.tcomet_beat_phase = 0.0f;

  // 3. Spawn on the internal beat, coasting through dips; stand down + forget after
  //    ~2 bars with no confidence (re-locks fresh on the next section).
  if (internal_beat && !probe) {
    if (!confident) fx.tcomet_coast_beats++;
    const bool have_lock = (fx.tcomet_locked_bpm > 0.0f) && (fx.tcomet_coast_beats <= (uint16_t)TC_COAST_BEATS);
    if (have_lock) {
      float strength = t.beat_strength; if (strength < 0.0f) strength = 0.0f; if (strength > 1.0f) strength = 1.0f;
      if (strength < TC_STRENGTH_FLOOR) strength = TC_STRENGTH_FLOOR;     // keep weak/coasting comets visible
      const float beat_s   = 60.0f / run_bpm;
      const float reach_fr = TC_REACH_MIN + (TC_REACH_FRAC - TC_REACH_MIN) * strength; // weak=skip, strong=zoom
      const float reach    = reach_fr * (float(NATIVE_RESOLUTION) * 0.5f);
      const float vel_px_s = reach / beat_s;                              // lands by next beat
      uint8_t slot = 0; float min_life = fx.tcomet_life[0];
      for (uint8_t i = 1; i < COMET_MAX; i++) {
        if (fx.tcomet_life[i] < min_life) { min_life = fx.tcomet_life[i]; slot = i; }
      }
      const uint16_t centre_px = NATIVE_RESOLUTION / 2;
      fx.tcomet_pos[slot]  = float(centre_px);
      fx.tcomet_vel[slot]  = vel_px_s;
      fx.tcomet_size[slot] = TC_SIZE * (0.80f + 0.40f * strength);
      fx.tcomet_life[slot] = 1.0f;
    } else {
      // stood down: forget the tempo so the flywheel re-locks cleanly on the next section
      fx.tcomet_locked_bpm = 0.0f;
    }
  }

  // 4. Advance + draw each live comet (bright core + trailing wake + glow).
  for (uint8_t i = 0; i < COMET_MAX; i++) {
    if (fx.tcomet_life[i] <= 0.01f) continue;
    fx.tcomet_pos[i] += fx.tcomet_vel[i] * dt;
    if (fx.tcomet_pos[i] < 0.0f || fx.tcomet_pos[i] >= float(NATIVE_RESOLUTION)) {
      fx.tcomet_life[i] = 0.0f; continue;
    }
    const float life   = fx.tcomet_life[i];
    const float radius = fx.tcomet_size[i];
    const int   dir    = (fx.tcomet_vel[i] >= 0.0f) ? 1 : -1;
    const int   centre = int(fx.tcomet_pos[i] + 0.5f);
    const int   reach  = int(radius) + TC_GLOW;
    float u_raw = fabsf(fx.tcomet_pos[i] - float(NATIVE_RESOLUTION / 2)) / (float(NATIVE_RESOLUTION) * 0.5f);
    if (u_raw < 0.0f) u_raw = 0.0f; else if (u_raw > 1.0f) u_raw = 1.0f;
    const float u = u_raw;
    const CRGB16 col = effect_particle_colour(rp, render_secondary,
                                              u * TC_PALETTE_SPREAD, SQ15x16(1.0f));
    for (int d = -reach; d <= reach; d++) {
      const int idx = centre + d;
      if (idx < 0 || idx >= NATIVE_RESOLUTION) continue;
      const float ad = (d < 0) ? float(-d) : float(d);
      const bool  trailing = (d * dir) < 0;
      const float span = trailing ? (radius * TC_WAKE_STRETCH) : (radius * 0.7f);
      float f = 1.0f - (ad / (span + 1.0f));
      if (f < 0.0f) f = 0.0f;
      if (d == 0) f = 1.0f;                                               // bright leading core
      const SQ15x16 w = SQ15x16(life * f * TC_HEAD_GAIN);
      leds_16[idx].r += col.r * w; leds_16[idx].g += col.g * w; leds_16[idx].b += col.b * w;
    }
    fx.tcomet_life[i] *= (1.0f - TC_LIFE_DECAY * frame);
  }

  // 5. Hue-preserving clamp (additive heads can exceed 1.0).
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) leds_16[i] = clamp_crgb16_preserve_sat(leds_16[i]);

  // 6. Centre-origin mirror.
  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);
}
