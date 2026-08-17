#include "lightshow_modes.h"
#include "k1_tempo.h"
#include <math.h>
#include "k1_vp_audio_access.h"

// ============================================================================
// light_mode_tempo_river_walk — "Tempo River Walk": Tempo River with its palette
// position WALKING one step per musical bar.
// ----------------------------------------------------------------------------
// NEW STANDALONE VARIANT (mode 29; 2026-06-11). A faithful variant copy of
// light_mode_tempo_river.cpp (which is NOT modified) plus exactly ONE added
// colour mechanism. It is the salvage of the killed "Beat Palette" idea — which
// died for global brightness-on-beat (a Strobe Law violation). Here the BAR
// drives the palette POSITION, never the amplitude: motion, brightness and
// injection are byte-for-byte the Tempo River behaviour.
//
// PASS 1 (what it is): the Spectrum-River transport, flow velocity locked to
//   beat phase (Tempo River, unchanged), whose colour mapping drifts +0.125
//   around the palette once per counted bar (4 beats).
// PASS 2 (verbs): Count beats -> Step target per bar -> Slew offset -> Flow ->
//   Clear centre -> Inject (palette position + offset) -> Clamp -> Mirror.
// PASS 3 (layers): L1 adds the tempo beat edge (phase01 wrap from k1_vp_tempo_read(),
//   the same event source Tempo River reads); L2 adds five fx.trwalk_* fields;
//   L4 (colour) is the ONLY layer altered — sample position = original + offset,
//   wrapped [0,1); L3/L5/L6 are identical to Tempo River.
// PASS 4 (levers): TRW_BEATS_PER_BAR=4 (bar length), TRW_STEP=0.125 (palette
//   walk per bar; 8 bars = full palette cycle), TRW_SLEW_PER_S=0.25 (max offset
//   glide rate; 0.125 step lands in ~0.5 s).
// PASS 5 (maths -> perception): one palette step per BAR means the river's
//   colour world evolves with the song's structure — a viewer reads "the music
//   has moved on" as the hues migrate, while frequency->relative-palette-order
//   stays an internally consistent contract (the whole map rotates rigidly).
//   The slew turns each step into a smooth DRIFT, never a snap — colour change
//   is felt, not seen as an event. Strobe Law: zero amplitude writes — the
//   added mechanism touches palette position ONLY.
// PASS 6 (reusable principle): bar-counting from the tempo phase wrap + a
//   slewed wrapped offset is a generic "musical-structure -> colour walk"
//   primitive any palette-native effect can adopt.
//
// BEAT COUNTING: Tempo River consumes tempo continuously via phase01 (it never
//   reads the one-AP-update-wide beat_tick, which a ~120 fps render loop can
//   sample twice or miss). The dt-robust equivalent tick-edge at render rate is
//   the phase01 WRAP (previous phase high -> current phase low), tracked in
//   fx.trwalk_last_phase — the same derivation Tempo Comet's pre-flywheel
//   wrap-detect used. Beats are counted only while the original's tempo
//   predicate has influence (confidence gate > 0: locked or the soft coast
//   band TR_CONF_LO..TR_CONF_HI); when standing down the walk FREEZES — the
//   offset is never reset, so colour stays where the music left it.
//
// vp-probe: like Tempo River, under led_thread_halt the tempo event is frozen
//   and dt fixed; the frozen phase cannot wrap, so the walk is inert and a
//   probe render stays reproducible.
//
// Discipline: no heap; no file-scope mutable statics; all persistent state in
// ChannelEffectState (trwalk_*, zero-reset canonical); dt clamped exactly as
// the original; reads via active_render_params(); centre-origin + mirror-safe.
// ============================================================================

static const float   TR_TWO_PI_F    = 6.28318530718f;
static const float   TR_PX_PER_BEAT = 22.0f;  // base flow distance per beat (px @ NR=128), dt-stable
static const float   TR_DEPTH       = 0.60f;  // intra-beat velocity surge depth (0..1) — the "feel" knob
static const float   TR_IDLE_DRIFT  = 0.55f;  // px/frame fallback == plain Spectrum-River base (the 10/10 flow)
static const float   TR_DRIFT_FLOOR = 0.30f;  // px/frame absolute floor — the river NEVER stops (Organic Law)
static const float   TR_DRIFT_MAX   = 3.00f;  // px/frame cap (draw_sprite sanity)
static const float   TR_CONF_LO     = 0.30f;
static const float   TR_CONF_HI     = 0.60f;  // == K1_LOCK_CONFIDENCE
static const float   TR_TRAIL_ALPHA = 0.90f;  // == River persistence (do NOT raise: "mechanical hold")
static const float   TR_FLOOR       = 0.015f; // skip near-silent bins
static const float   TR_INJECT_GAIN = 0.90f;  // additive white-out guard
static const uint8_t TR_MAX_ITERS   = 4;      // contrast cap (rp->SQUARE_ITER can be large)

// — The ONE added mechanism: bar-stepped palette walk (colour-position only) —
static const uint8_t TRW_BEATS_PER_BAR = 4;      // beats counted per bar
static const float   TRW_STEP          = 0.125f; // palette-walk target advance per bar (wraps [0,1))
static const float   TRW_SLEW_PER_S    = 0.25f;  // max offset glide rate (units/s) — 0.125 step ≈ 0.5 s drift

static inline float tr_smoothstep(float lo, float hi, float x) {
  if (hi <= lo) return (x >= hi) ? 1.0f : 0.0f;
  float t = (x - lo) / (hi - lo);
  if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;
  return t * t * (3.0f - 2.0f * t);
}

void light_mode_tempo_river_walk(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  const uint16_t HALF     = NATIVE_RESOLUTION / 2;            // 80
  const float    nr_scale = float(NATIVE_RESOLUTION) / 128.0f;

  // ── dt (fps-independent) + frozen, deterministic path under the VP probe ─────
  const bool probe = led_thread_halt;
  uint32_t now = probe ? 0u : millis();
  float dt;
  if (probe) {
    dt = 1.0f / 120.0f;
  } else {
    dt = (fx.trwalk_last_ms == 0) ? (1.0f / 120.0f) : (now - fx.trwalk_last_ms) * 0.001f;
    fx.trwalk_last_ms = now;
    if (dt < 0.001f) dt = 0.001f; else if (dt > 0.050f) dt = 0.050f;
  }

  K1TempoEvent t;
  if (probe) {
    t.bpm = 120.0f; t.phase01 = 0.0f; t.confidence = 1.0f;
    t.beat_tick = false; t.locked = true; t.beat_strength = 1.0f;
  } else {
    t = k1_vp_tempo_read();
  }

  // ── Tempo-locked outward drift VELOCITY (px THIS frame) ──────────────────────
  // Musical base flow (px/s) -> dt. Surged by a mean-preserving intra-beat envelope
  // that peaks ON the beat. Confidence-blended to the plain-River idle drift, then
  // floored so the river never stops.
  float bpm = t.bpm; if (bpm < 40.0f) bpm = 40.0f; if (bpm > 200.0f) bpm = 200.0f;
  float base_px_s = TR_PX_PER_BEAT * (bpm / 60.0f) * nr_scale;
  float env = 1.0f + TR_DEPTH * cosf(TR_TWO_PI_F * t.phase01);
  if (env < 0.0f) env = 0.0f;                                  // never scroll backward
  float tempo_drift = base_px_s * env * dt;                    // px this frame, tempo-locked
  float idle_drift  = TR_IDLE_DRIFT * nr_scale;                // px/frame, plain River
  float gate  = tr_smoothstep(TR_CONF_LO, TR_CONF_HI, t.confidence);
  float drift = idle_drift + (tempo_drift - idle_drift) * gate;
  const float floor_drift = TR_DRIFT_FLOOR * nr_scale;
  const float max_drift   = TR_DRIFT_MAX   * nr_scale;
  if (drift < floor_drift) drift = floor_drift;               // Organic Law: always flows
  if (drift > max_drift)   drift = max_drift;

  // ── THE ADDED MECHANISM: bar-stepped palette walk (colour-position ONLY) ─────
  // Beat tick edge = phase01 wrap (the render-rate-robust equivalent of the
  // tracker's one-AP-update beat_tick; see header). Counted only while the
  // tempo gate has influence (locked or coasting); frozen when standing down —
  // offset is never reset. Probe path is inert (frozen phase never wraps).
  const bool beat_wrap = (!probe) && (t.phase01 + 0.5f < fx.trwalk_last_phase);
  fx.trwalk_last_phase = t.phase01;                            // track always (no false wrap on re-lock)
  if (gate > 0.0f && beat_wrap) {
    fx.trwalk_beats++;
    if (fx.trwalk_beats >= TRW_BEATS_PER_BAR) {                // one bar elapsed
      fx.trwalk_beats = 0;
      fx.trwalk_target += TRW_STEP;
      fx.trwalk_target -= floorf(fx.trwalk_target);            // wrap [0,1)
    }
  }
  // Slew the live offset toward the target along the shortest wrapped path —
  // a smooth ~0.5 s colour DRIFT per bar step, never a snap.
  {
    float d = fx.trwalk_target - fx.trwalk_offset;
    d -= floorf(d + 0.5f);                                     // wrap to [-0.5, 0.5)
    const float max_step = TRW_SLEW_PER_S * dt;
    if (d >  max_step) d =  max_step;
    if (d < -max_step) d = -max_step;
    fx.trwalk_offset += d;
    fx.trwalk_offset -= floorf(fx.trwalk_offset);              // keep [0,1)
  }

  // 1. Flow the previous river OUTWARD by the tempo-locked drift, with decay.
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION,
              drift, SQ15x16(TR_TRAIL_ALPHA));

  // Keep the river in the upper (mirror-authoritative) half; clear cross-centre bleed.
  for (uint16_t i = 0; i < HALF; i++) { leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0; }

  // 2. Inject the live spectrum: bin k -> pixel HALF+k, colour BY FREQUENCY,
  //    palette position walked by the slewed bar offset (amplitude untouched).
  //    Nyquist ghosts retired — analysis_bins only.
  uint8_t iters = (uint8_t)rp->SQUARE_ITER; if (iters > TR_MAX_ITERS) iters = TR_MAX_ITERS;
  const uint8_t analysis_bins =
      sb_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET);
  const float hue_denom =
      float((analysis_bins > 1) ? (analysis_bins - 1) : 1);
  for (uint16_t k = 0; k < analysis_bins && k < HALF; k++) {
    float e = float(spectrogram_smooth[k]);
    if (!isfinite(e) || e < 0.0f) e = 0.0f; if (e > 1.0f) e = 1.0f;
    for (uint8_t s = 0; s < iters; s++) e *= e;               // contrast (square-iter)
    if (e < TR_FLOOR) continue;
    float hue = float(k) / hue_denom + fx.trwalk_offset;  // frequency -> palette position + walk
    hue -= floorf(hue);                                        // wrap [0,1)
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(e * TR_INJECT_GAIN));
    const uint16_t idx = HALF + k;
    leds_16[idx].r += col.r; leds_16[idx].g += col.g; leds_16[idx].b += col.b;
  }

  // 3. Bound additive overflow before it becomes next frame's trail state.
  finalize_additive_frame(leds_16, leds_prev_buffer, true);

  // 4. Centre-origin mirror (upper half -> lower half).
  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);
}
