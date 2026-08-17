#include "lightshow_modes.h"
#include "k1_tempo.h"
#include <math.h>
#include "k1_vp_audio_access.h"

// ============================================================================
// light_mode_tempo_comet_anticipate — "Tempo Comet Anticipate" (mode 27):
// comets that DECELERATE INTO the next beat instead of merely launching on it.
// ----------------------------------------------------------------------------
// VARIANT COPY of light_mode_tempo_comet (2026-06-04 v2). Same beat flywheel
// (PLL), same lock/coast stand-down, same spawn cadence, same pool size, same
// live colour helper, same trail/clamp/mirror — ONE mechanism changed (TRIZ
// separation-in-time; the unused lever is beat phase as a POSITION TARGET):
//
//   ORIGINAL: a comet launches on the internal beat tick with a fixed velocity
//   (reach / beat_s) and coasts linearly until it exits or fades.
//   VARIANT:  a comet launched on beat N is given a TARGET — arrive at its full
//   travel distance D exactly when beat N+1 fires. Position follows a quadratic
//   ease-out  pos(t) = launch + D · (1 − (1 − t/T)²)  with T = 60/bpm, so the
//   head launches FAST and DECELERATES into arrival. Each frame t advances by
//   dt and is gently slewed toward the flywheel's ideal t_ideal = phase01 · T
//   (max ~15%/frame of the wrapped error), so phase drift and tempo changes
//   glide instead of snapping. On arrival (t ≥ T) the head parks at D and its
//   residual fades exactly as the original's end-of-life decay does.
//
// COMPACT PASS 1–6 (per the decomposition method):
//   P1 WHAT: beat-grid-locked travelling comets whose ARRIVAL, not launch, is
//      the beat-synchronous event. The eye predicts the music.
//   P2 VERBS: Fade → Flywheel → Spawn(target) → Ease+Slew → Decay → Draw →
//      Clamp → Mirror. Purely audio-derived clocking; no wall-clock oscillator
//      beyond the original's beat flywheel.
//   P3 LAYERS: L1 = k1_vp_tempo_read() (bpm/phase01/confidence/beat_strength);
//      L2 = per-channel tcanta_* pool + own flywheel copies; L3 = centre spawn,
//      eased outward travel, mirror fold; L4 = live shared colour helper every
//      frame (trail encodes chromatic history); L5 = ease-out transport + fixed
//      exponential trail/life decay; L6 = dt clamp, confidence gate, coast
//      stand-down, strength floor, preserve-sat clamp.
//   P4 LEVERS: identical dials to the original (TCA_* mirrors of TC_*) plus
//      TCA_T_SLEW (phase-correction gain, 0.15/frame).
//   P5 MATHS → PERCEPTION: ease-out means v(0) = 2D/T (fast launch reads as
//      attack) and v(T) = 0 (the light visibly "lands" on the beat). [MECHANISM]
//      arrival time is pinned to the flywheel phase wrap, so deceleration is a
//      countdown to the next beat. [PERCEPTION] the listener feels PREDICTION,
//      not reaction — the slowing head telegraphs where the beat will fall, and
//      the simultaneous land-and-relaunch confirms it. Deceleration is motion
//      (transport through the plate), never a global amplitude — Strobe Law safe.
//   P6 REUSABLE: beat phase as a position target (separation-in-time) is a
//      portable mapping for ANY transport effect: pin the journey's END to the
//      grid and the whole travel becomes anticipatory.
//
// No heap; no file-scope mutable statics; per-channel pool + flywheel state in
// ChannelEffectState (NEW tcanta_* fields — fully independent of tcomet_* so
// both modes switch without state cross-talk). Deterministic under
// led_thread_halt: frozen tempo + fixed dt + NO spawn, like the original.
// ============================================================================

static const float TCA_TRAIL_DECAY = 0.05f;   // trail fade per 120fps-frame
static const float TCA_LIFE_DECAY  = 0.018f;  // head life fade per frame
static const int   TCA_GLOW        = 2;       // soft halo px beyond radius
static const float TCA_WAKE_STRETCH= 2.0f;    // trailing-wake span vs sharp leading edge
static const float TCA_HEAD_GAIN   = 0.85f;   // peak additive weight (white-out guard)
static const float TCA_PALETTE_SPREAD = 0.35f; // palette-position span over a comet's travel (crush fix)
static const float TCA_SIZE        = 3.5f;    // base head radius (px)
static const float TCA_CONF_LO     = 0.30f;
static const float TCA_CONF_HI     = 0.60f;
// Flywheel knobs (identical to the original's dials):
static const float TCA_RESYNC_HZ   = 2.0f;    // phase-lock rate to the tracker (higher=tighter/jitterier, lower=stiffer)
static const int   TCA_COAST_BEATS = 8;       // coast ~2 bars through confidence dips before standing down
static const float TCA_BPM_EMA     = 0.05f;   // smoothing of the learned locked BPM
static const float TCA_REACH_FRAC  = 0.92f;   // STRONG-beat reach (fraction of half-strip) -> long landing run
static const float TCA_REACH_MIN   = 0.45f;   // WEAK-beat reach -> short skipping-stone
static const float TCA_STRENGTH_FLOOR = 0.35f;// keep coasting/weak comets visible
// THE ONE NEW DIAL — anticipation phase-correction:
static const float TCA_T_SLEW      = 0.15f;   // max fraction of wrapped (t_ideal - t) absorbed per 120fps-frame

static inline float tca_smoothstep(float lo, float hi, float x) {
  if (hi <= lo) return (x >= hi) ? 1.0f : 0.0f;
  float t = (x - lo) / (hi - lo);
  if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;
  return t * t * (3.0f - 2.0f * t);
}

void light_mode_tempo_comet_anticipate(ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;

  // ── dt + frozen, deterministic path under the VP probe ───────────────────────
  const bool probe = led_thread_halt;
  uint32_t now_ms = probe ? 0u : millis();
  float dt = (fx.tcanta_last_ms != 0) ? float(now_ms - fx.tcanta_last_ms) * 0.001f : (1.0f / 120.0f);
  if (probe) dt = 1.0f / 120.0f; else fx.tcanta_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f; else if (dt > 0.05f) dt = 0.05f;
  const float frame = dt * 120.0f;

  K1TempoEvent t;
  if (probe) {
    t.bpm = 120.0f; t.phase01 = 0.0f; t.confidence = 1.0f;
    t.beat_tick = false; t.locked = true; t.beat_strength = 1.0f;
  } else {
    t = k1_vp_tempo_read();
  }

  // 1. Fade the persisted trail in place.
  float fade_f = 1.0f - (TCA_TRAIL_DECAY * frame);
  if (fade_f < 0.0f) fade_f = 0.0f; if (fade_f > 0.999f) fade_f = 0.999f;
  const SQ15x16 fade = SQ15x16(fade_f);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade; leds_16[i].g *= fade; leds_16[i].b *= fade;
  }

  // 2. BEAT FLYWHEEL (own copy — identical mechanism to the original) ──────────
  const float gate   = tca_smoothstep(TCA_CONF_LO, TCA_CONF_HI, t.confidence);
  const bool  confident = gate >= 0.5f;
  float bpm = t.bpm; if (bpm < 40.0f) bpm = 40.0f; if (bpm > 200.0f) bpm = 200.0f;

  // Learn/hold the locked BPM only when confident; HOLD through octave flips (ratio
  // guard) so 72<->144 jumps don't whipsaw the clock.
  if (confident) {
    if (fx.tcanta_locked_bpm <= 0.0f) {
      fx.tcanta_locked_bpm = bpm;
    } else {
      const float ratio = bpm / fx.tcanta_locked_bpm;
      if (ratio > 0.70f && ratio < 1.40f) {                 // same tempo octave -> track
        fx.tcanta_locked_bpm += (bpm - fx.tcanta_locked_bpm) * TCA_BPM_EMA;
      }
      // else: octave flip / spurious -> hold the established tempo (flywheel inertia)
    }
    fx.tcanta_coast_beats = 0;                               // confident now -> reset coast
  }
  const float run_bpm = (fx.tcanta_locked_bpm > 0.0f) ? fx.tcanta_locked_bpm : bpm;

  // Advance the internal beat phase at run_bpm.
  fx.tcanta_beat_phase += (run_bpm / 60.0f) * dt;

  // Gentle phase-lock to the tracker ONLY when confident (low gain filters the
  // re-anchor jitter that breaks naive wrap-detection). Error wrapped to [-0.5,0.5).
  if (confident) {
    float err = t.phase01 - fx.tcanta_beat_phase;
    err -= floorf(err);
    if (err > 0.5f) err -= 1.0f;
    fx.tcanta_beat_phase += (TCA_RESYNC_HZ * dt) * err;
  }

  // Internal-clock beat wrap.
  bool internal_beat = false;
  if (fx.tcanta_beat_phase >= 1.0f) { fx.tcanta_beat_phase -= floorf(fx.tcanta_beat_phase); internal_beat = true; }
  if (fx.tcanta_beat_phase < 0.0f) fx.tcanta_beat_phase = 0.0f;

  // 3. Spawn on the internal beat, coasting through dips; stand down + forget after
  //    ~2 bars with no confidence (re-locks fresh on the next section).
  //    [THE ONE CHANGE] the slot is given a TARGET, not a velocity: travel distance
  //    D and beat period T, so it ARRIVES at D exactly when the NEXT beat fires.
  if (internal_beat && !probe) {
    if (!confident) fx.tcanta_coast_beats++;
    const bool have_lock = (fx.tcanta_locked_bpm > 0.0f) && (fx.tcanta_coast_beats <= (uint16_t)TCA_COAST_BEATS);
    if (have_lock) {
      float strength = t.beat_strength; if (strength < 0.0f) strength = 0.0f; if (strength > 1.0f) strength = 1.0f;
      if (strength < TCA_STRENGTH_FLOOR) strength = TCA_STRENGTH_FLOOR;   // keep weak/coasting comets visible
      const float beat_s   = 60.0f / run_bpm;                            // T: the anticipation window
      const float reach_fr = TCA_REACH_MIN + (TCA_REACH_FRAC - TCA_REACH_MIN) * strength; // weak=skip, strong=zoom
      const float reach    = reach_fr * (float(NATIVE_RESOLUTION) * 0.5f); // D: target distance (px)
      uint8_t slot = 0; float min_life = fx.tcanta_life[0];
      for (uint8_t i = 1; i < COMET_MAX; i++) {
        if (fx.tcanta_life[i] < min_life) { min_life = fx.tcanta_life[i]; slot = i; }
      }
      const uint16_t centre_px = NATIVE_RESOLUTION / 2;
      fx.tcanta_launch[slot] = float(centre_px);
      fx.tcanta_target[slot] = reach;
      fx.tcanta_period[slot] = beat_s;
      fx.tcanta_t[slot]      = 0.0f;
      fx.tcanta_size[slot]   = TCA_SIZE * (0.80f + 0.40f * strength);
      fx.tcanta_life[slot]   = 1.0f;
    } else {
      // stood down: forget the tempo so the flywheel re-locks cleanly on the next section
      fx.tcanta_locked_bpm = 0.0f;
    }
  }

  // 4. Advance (ease-out toward the beat) + draw each live comet.
  // PALETTE-CRUSH FIX (2026-06-11): colour is per-comet, not per-frame — each
  // comet samples the palette at (live centroid + travel-progress offset), so
  // concurrent comets render different palette colours and a comet's colour
  // ripens across the palette as it decelerates into the beat. The old single
  // effect_palette_or_chroma_colour() call collapsed palette identity to one
  // centroid coordinate per frame (audit: 2026-06-11-palette-crush-audit.md).
  for (uint8_t i = 0; i < COMET_MAX; i++) {
    if (fx.tcanta_life[i] <= 0.01f) continue;
    const float T = fx.tcanta_period[i];
    if (T <= 0.0f) { fx.tcanta_life[i] = 0.0f; continue; }   // guard: never seeded

    // [THE ONE CHANGE] advance the particle's beat-time t by dt, then slew it
    // gently toward the flywheel's ideal t_ideal = phase01 * T so phase drift /
    // tempo changes glide instead of snapping. Error is wrapped to [-T/2, T/2)
    // so the flywheel's wrap (phase 1 -> 0 at arrival) does not yank t backward.
    if (fx.tcanta_t[i] < T) {
      fx.tcanta_t[i] += dt;
      const float t_ideal = fx.tcanta_beat_phase * T;
      float terr = t_ideal - fx.tcanta_t[i];
      terr -= T * floorf(terr / T + 0.5f);
      float slew = TCA_T_SLEW * frame;
      if (slew > 1.0f) slew = 1.0f;
      fx.tcanta_t[i] += terr * slew;
      if (fx.tcanta_t[i] < 0.0f) fx.tcanta_t[i] = 0.0f;
      if (fx.tcanta_t[i] >= T) fx.tcanta_t[i] = T;           // arrived: park at the target
    }

    // Quadratic ease-out: fast launch, decelerating arrival — the light LANDS
    // on the beat. pos(t) = launch + D * (1 - (1 - t/T)^2). Travel is always
    // outward (+) from centre; the mirror folds it, as the original does.
    float u = fx.tcanta_t[i] / T;
    if (u < 0.0f) u = 0.0f; else if (u > 1.0f) u = 1.0f;
    const float inv  = 1.0f - u;
    const float ease = 1.0f - inv * inv;
    const float pos  = fx.tcanta_launch[i] + fx.tcanta_target[i] * ease;
    if (pos < 0.0f || pos >= float(NATIVE_RESOLUTION)) {
      fx.tcanta_life[i] = 0.0f; continue;
    }
    const CRGB16 col = effect_particle_colour(rp, render_secondary,
                                              u * TCA_PALETTE_SPREAD, SQ15x16(1.0f));
    const float life   = fx.tcanta_life[i];
    const float radius = fx.tcanta_size[i];
    const int   dir    = 1;                                   // eased travel is monotonically outward
    const int   centre = int(pos + 0.5f);
    const int   reach  = int(radius) + TCA_GLOW;
    for (int d = -reach; d <= reach; d++) {
      const int idx = centre + d;
      if (idx < 0 || idx >= NATIVE_RESOLUTION) continue;
      const float ad = (d < 0) ? float(-d) : float(d);
      const bool  trailing = (d * dir) < 0;
      const float span = trailing ? (radius * TCA_WAKE_STRETCH) : (radius * 0.7f);
      float f = 1.0f - (ad / (span + 1.0f));
      if (f < 0.0f) f = 0.0f;
      if (d == 0) f = 1.0f;                                   // bright leading core
      const SQ15x16 w = SQ15x16(life * f * TCA_HEAD_GAIN);
      leds_16[idx].r += col.r * w; leds_16[idx].g += col.g * w; leds_16[idx].b += col.b * w;
    }
    fx.tcanta_life[i] *= (1.0f - TCA_LIFE_DECAY * frame);     // residual fades as the original's end-of-life does
  }

  // 5. Hue-preserving clamp (additive heads can exceed 1.0).
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) leds_16[i] = clamp_crgb16_preserve_sat(leds_16[i]);

  // 6. Centre-origin mirror.
  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);
}
