#include "lightshow_modes.h"
#include "cannonade_math.h"
#include "easing.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include <math.h>

// ============================================================================
// light_mode_cannonade — "Cannonade": ballistic LOB, arc-and-return, centre CRACK.
// ----------------------------------------------------------------------------
// A NEW captivating family built to carry Waveform's captivation DNA WITHOUT
// looking like Waveform (design: docs/effect-craft/captivation-families-build-
// spec.md §2 Cannonade; docs/architecture/effect-decomposition/00b-captivation-
// transposition.md §5). Engine = Particle-integration (the cleanest escape from
// the outward-scroll collapse); the anti-Waveform SIGNATURE is the strong-gravity
// RETURN + a bright centre CRACK on impact — a percept the outward-scroll family
// cannot produce.
//
// Physics (pure, host-tested in tests/native/test_cannonade_math.cpp via
// effects/cannonade_math.h): a bass onset FIRES a projectile from the centre with
// v0 = f(bass_onset_strength) — amplitude drives VELOCITY, never position (the
// oscilloscope leak is severed). A constant inward "gravity" decelerates the
// climb, the shot apexes, falls back, and on returning to the centre injects an
// eased CRACK flash at LED 79/80. The projectile is integrated with dt sub-
// stepping so no draw jumps more than the ~28 px fusion floor (swept path, never
// a teleport).
//
// Shared coherence contract (spec §1): leds_16 IS the persisted wake (faded in
// place via leds_prev_buffer + finalize_additive_frame store_history=true);
// author the UPPER half [HALF, NATIVE_RESOLUTION) only, then mirror -> centre
// origin 79/80. Every audio level is EASED (k1ease); an eased silence gate fades
// to honest dark on snap.silence with a breathe-not-blink 0.4+0.6·env floor;
// reactivity is spatial (discrete projectiles), never a global brightness pulse.
// No heap / new / String; static consts only; colour hoisted out of per-LED loops.
//
// Colour: warm impact palette, palette-position by launch strength, harmony-
// anchored via effect_particle_colour (palette-bounded -> inherently no-rainbow).
// The centre CRACK is a warm near-white impact flash (not a hue-wheel sweep).
//
// British English throughout.
// ============================================================================

// --- Launch / gravity (px, px/s, px/s^2 at HALF == 80) ----------------------
// Chosen so a weak kick apexes ~18 px and a strong kick ~72 px (< the 80 px edge),
// with a musical ~0.4–0.8 s hang time. Amplitude sets v0 ONLY (never position).
static const float CANNA_V0_MIN     = 180.0f;  // px/s at strength 0
static const float CANNA_V0_SPAN    = 180.0f;  // + strength * this  (=> 180..360 px/s)
static const float CANNA_GRAVITY    = 900.0f;  // px/s^2 constant inward pull
static const float CANNA_MIN_STRENGTH = 0.06f; // low floor: catch every clear kick

// --- Impact / crack ---------------------------------------------------------
static const float CANNA_IMPACT_NORM = 360.0f; // |v_impact| that maps to a full crack
static const float CANNA_CRACK_TAU   = 0.12f;  // crack-flash release (s) — a fast bright snap
static const int   CANNA_CRACK_HALFW  = 4;     // crack half-width (px) about the centre
static const float CANNA_CRACK_GAIN   = 1.10f; // crack additive weight (white-out guarded by clamp)

// --- Head + wake ------------------------------------------------------------
static const float CANNA_HEAD_RADIUS = 2.4f;   // projectile head core radius (px)
static const int   CANNA_HEAD_GLOW   = 2;      // soft halo px beyond the head
static const float CANNA_HEAD_GAIN    = 0.90f; // head additive weight

// --- Trail persistence (reactive fade DEPTH — spatial, not a brightness pulse) --
static const float CANNA_TRAIL_MIN   = 1.4f;   // decay rate (per s) when quiet -> long wake
static const float CANNA_TRAIL_SCALE = 3.0f;   // + peak * this -> louder = punchier/shorter wake

// --- Colour (warm impact palette) -------------------------------------------
static const float CANNA_HUE_BASE    = 0.02f;  // warm palette anchor
static const float CANNA_HUE_SPREAD  = 0.12f;  // + launch strength -> walk the warm end

// --- Silence gate + presence floor (spec §1: honest dark, breathe not blink) --
static const float CANNA_SIL_ATTACK  = 0.05f;  // fade-in to dark (s)
static const float CANNA_SIL_RELEASE = 0.30f;  // fade-out from dark (s)
static const float CANNA_ENV_ATTACK  = 0.05f;
static const float CANNA_ENV_RELEASE = 0.40f;
static const float CANNA_PRESENCE_FLOOR = 0.02f;

static inline float canna_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

void light_mode_cannonade(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;  // == 80; centre origin at 79/80 post-mirror

  // ---- dt (frame-rate independent, clamped) --------------------------------
  const float dt = k1ease::safe_dt(millis(), fx.canna_last_ms);

  // ---- audio (value-copy snapshots) ----------------------------------------
  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const K1OnsetBeatEvent ev  = k1_onset_beat_read();
  const float peak = canna_clamp01(snap.peak_scaled);

  // ---- silence gate + breathe-not-blink presence floor ---------------------
  // Eased silence gate -> honest dark on true silence (fast in, slow out).
  const float sil_target = snap.silence ? 0.0f : 1.0f;
  fx.canna_sil = k1ease::follow(fx.canna_sil, sil_target, dt, CANNA_SIL_ATTACK, CANNA_SIL_RELEASE);
  // Presence envelope (holds through inter-beat gaps) -> 0.4+0.6·env floor so
  // the plate BREATHES rather than blinks; reactivity stays spatial (projectiles).
  const float env_target =
      (peak > CANNA_PRESENCE_FLOOR || snap.vu_level > CANNA_PRESENCE_FLOOR) ? 1.0f : 0.0f;
  fx.canna_hold_env = k1ease::follow(fx.canna_hold_env, env_target, dt,
                                     CANNA_ENV_ATTACK, CANNA_ENV_RELEASE);
  const float floor_gain  = 0.4f + 0.6f * canna_clamp01(fx.canna_hold_env);
  const float master_gain = canna_clamp01(fx.canna_sil) * floor_gain;  // gate at SOURCE (no global buffer pulse)

  // ---- spawn a shot on a fresh BASS onset ----------------------------------
  // bass_onset is the clean low-band ATTACK the detector already gates; every
  // shot == a kick, so the read is trivial and never wrong (Comet's lesson).
  const bool fresh = (ev.event_id != fx.canna_last_event_id);
  fx.canna_last_event_id = ev.event_id;
  if (fresh && ev.bass_onset && fx.canna_sil > 0.05f) {
    float strength = canna_clamp01(ev.bass_onset_strength);
    if (strength >= CANNA_MIN_STRENGTH) {
      // Recycle the oldest/free slot (min remaining life).
      uint8_t slot = 0;
      float min_life = fx.canna_life[0];
      for (uint8_t i = 1; i < CANNA_MAX; ++i) {
        if (fx.canna_life[i] < min_life) { min_life = fx.canna_life[i]; slot = i; }
      }
      const float v0 = cannonade::launchVelocity(strength, CANNA_V0_MIN, CANNA_V0_SPAN);
      fx.canna_pos[slot]  = 0.0f;
      fx.canna_prev[slot] = 0.0f;
      fx.canna_vel[slot]  = v0;                         // amplitude -> VELOCITY only
      fx.canna_hue[slot]  = CANNA_HUE_BASE + CANNA_HUE_SPREAD * strength;  // palette pos by launch strength
      // Life budget = 1.5x the analytic flight time (safety recycle if never impacts).
      fx.canna_life[slot] = cannonade::flightTime(v0, CANNA_GRAVITY) * 1.5f + 0.10f;
    }
  }

  // ==========================================================================
  // TRAIL — seed persisted wake, reactive-depth fade, hold upper half only
  // ==========================================================================
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
  float decay_rate = CANNA_TRAIL_MIN + CANNA_TRAIL_SCALE * peak;  // fade DEPTH ∝ intensity (spatial, not a global pulse)
  const SQ15x16 fade = SQ15x16(expf(-decay_rate * dt));
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }
  // Author the upper half only; the lower half is regenerated by the mirror.
  for (uint16_t i = 0; i < HALF; ++i) {
    leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0;
  }

  // ==========================================================================
  // INTEGRATE + DRAW each live projectile (swept head + wake), collect impacts
  // ==========================================================================
  const float half_px = float(HALF);
  for (uint8_t i = 0; i < CANNA_MAX; ++i) {
    if (fx.canna_life[i] <= 0.001f) continue;

    // --- physics step (pure, host-tested) ---
    cannonade::Projectile p{ fx.canna_pos[i], fx.canna_vel[i], true };
    const cannonade::StepResult r = cannonade::step(p, CANNA_GRAVITY, dt, half_px);
    fx.canna_prev[i] = r.prev_pos;
    fx.canna_pos[i]  = p.pos;
    fx.canna_vel[i]  = p.vel;
    fx.canna_life[i] -= dt;  // countdown safety-recycle

    if (r.impacted) {
      // impact_flash ∝ |v_impact| -> peak-hold into the eased centre CRACK.
      const float flash = canna_clamp01(r.impact_speed / CANNA_IMPACT_NORM);
      if (flash > fx.canna_crack) fx.canna_crack = flash;
      fx.canna_life[i] = 0.0f;   // consumed on impact
      continue;                  // head is gone this frame; the crack carries it
    }
    if (fx.canna_life[i] <= 0.001f) continue;  // expired without impact (rare)

    // --- colour (hoisted: computed once per projectile, never per-LED) ---
    const CRGB16 col = effect_particle_colour(rp, render_secondary, fx.canna_hue[i], SQ15x16(1.0));

    // --- swept wake from prev->pos + bright head at pos (never teleport) ---
    const float head = float(HALF) + fx.canna_pos[i];   // upper-half index of the head
    const float tail = float(HALF) + fx.canna_prev[i];  // frame-start position
    int lo = int(tail < head ? tail : head);
    int hi = int(tail < head ? head : tail);
    lo -= (CANNA_HEAD_GLOW + 1);
    hi += (int)CANNA_HEAD_RADIUS + CANNA_HEAD_GLOW + 1;
    if (lo < int(HALF)) lo = int(HALF);
    if (hi >= int(NATIVE_RESOLUTION)) hi = int(NATIVE_RESOLUTION) - 1;
    const int head_i = int(head + 0.5f);
    for (int idx = lo; idx <= hi; ++idx) {
      const float d = fabsf(float(idx) - head);          // distance from the head
      // Sharp leading head + soft falloff back along the swept segment.
      float f = 1.0f - (d / (CANNA_HEAD_RADIUS + CANNA_HEAD_GLOW + 1.0f));
      if (f < 0.0f) f = 0.0f;
      // Anything between prev and pos gets a wake floor so the path is continuous.
      const float seg_lo = (tail < head) ? tail : head;
      const float seg_hi = (tail < head) ? head : tail;
      if (float(idx) >= seg_lo - 1.0f && float(idx) <= seg_hi + 1.0f && f < 0.35f) f = 0.35f;
      if (idx == head_i) f = 1.0f;                        // bright core
      const SQ15x16 w = SQ15x16(f * CANNA_HEAD_GAIN * master_gain);
      leds_16[idx].r += col.r * w;
      leds_16[idx].g += col.g * w;
      leds_16[idx].b += col.b * w;
    }
  }

  // ==========================================================================
  // CENTRE CRACK — eased warm-white impact flash at 79/80 (the anti-Waveform beat)
  // ==========================================================================
  if (fx.canna_crack > 0.001f) {
    const float crack = canna_clamp01(fx.canna_crack);
    // Warm near-white flash (palette-bounded: no hue wheel).
    const CRGB16 crack_col = { SQ15x16(1.00f), SQ15x16(0.86f), SQ15x16(0.62f) };
    for (int d = 0; d <= CANNA_CRACK_HALFW; ++d) {
      float f = 1.0f - (float(d) / float(CANNA_CRACK_HALFW + 1));  // brightest at the centre
      const SQ15x16 w = SQ15x16(crack * f * CANNA_CRACK_GAIN * master_gain);
      const int idx = int(HALF) + d;  // author the upper half; mirror completes it
      if (idx < int(NATIVE_RESOLUTION)) {
        leds_16[idx].r += crack_col.r * w;
        leds_16[idx].g += crack_col.g * w;
        leds_16[idx].b += crack_col.b * w;
      }
    }
    // Eased release of the crack envelope (fast bright snap -> graceful fade).
    fx.canna_crack = k1ease::decay(fx.canna_crack, dt, CANNA_CRACK_TAU);
    if (fx.canna_crack < 0.001f) fx.canna_crack = 0.0f;
  }

  // ==========================================================================
  // FINALISE + MIRROR (store history for the persistent wake)
  // ==========================================================================
  finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
