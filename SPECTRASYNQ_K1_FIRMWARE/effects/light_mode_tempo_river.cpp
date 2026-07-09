#include "lightshow_modes.h"
#include "k1_tempo.h"
#include <math.h>

// ============================================================================
// light_mode_tempo_river — "Tempo River": the Spectrum-River transport with its
// outward FLOW VELOCITY locked to musical tempo and phase.
// ----------------------------------------------------------------------------
// NEW STANDALONE MODE (2026-06-04). Composes a NEW MAPPING (tempo-phase -> drift
// velocity) onto the OWNED Spectrum-River Transport engine. It does NOT modify
// light_mode_spectrum_river.* — the proven 10/10 mode is untouched; this is a
// separate file and a separate mode ID.
//
// MAPPING (the {where,colour,intensity} seam — River's identity, unchanged):
//   where     = frequency -> position  (bin k -> pixel HALF+k; bass centre, treble edge)
//   colour    = frequency -> palette position (palette_manual_colour; auto-shift folded in)
//   intensity = contrast-enhanced bin energy (spectrogram_smooth)
// The NEW tempo mapping: the OUTWARD DRIFT VELOCITY surges on the beat (phase01==0)
// and eases between beats — the whole spectral river visibly breathes in time.
//
// THE DESIGN LAW [MEASURED] (docs/measurements/apparent-motion-on-k1.md §8):
//   Lock modulates the CONTINUOUS per-frame scroll VELOCITY (draw_sprite's sub-pixel
//   drift, stepping every render frame), NEVER a per-beat position jump and NEVER a
//   global brightness pulse. The eye reads the lock from the per-beat flow SURGE.
//   => It is structurally incapable of strobing: brightness is never globally
//      modulated; content continuously enters at centre and flows out (Transport).
//
// CONFIDENCE BLEND: drift = idle_drift + (tempo_drift - idle_drift) * smoothstep(conf).
//   Low confidence -> plain Spectrum-River flow (the proven baseline), never garbage.
//   t.confidence is already silence-scaled; in true silence the spectrum is ~0 so
//   nothing injects and the river fades gracefully (never frozen, never random).
//   A hard drift floor guarantees the river never stops (Organic Law clause 1).
//
// vp-probe: NOT in the Tier-A vp_run_output_probe roster (nondeterministic-EXCLUDED,
// like River / Comet / waveform_tempo). Belt-and-braces: under led_thread_halt use a
// frozen tempo event + fixed dt so a probe render is reproducible.
//
// Discipline: no heap; per-channel dt state in ChannelEffectState (tempo_river_last_ms);
// reads via active_render_params(); centre-origin + mirror-safe.
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

static inline float tr_smoothstep(float lo, float hi, float x) {
  if (hi <= lo) return (x >= hi) ? 1.0f : 0.0f;
  float t = (x - lo) / (hi - lo);
  if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;
  return t * t * (3.0f - 2.0f * t);
}

void light_mode_tempo_river(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
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
    dt = (fx.tempo_river_last_ms == 0) ? (1.0f / 120.0f) : (now - fx.tempo_river_last_ms) * 0.001f;
    fx.tempo_river_last_ms = now;
    if (dt < 0.001f) dt = 0.001f; else if (dt > 0.050f) dt = 0.050f;
  }

  K1TempoEvent t;
  if (probe) {
    t.bpm = 120.0f; t.phase01 = 0.0f; t.confidence = 1.0f;
    t.beat_tick = false; t.locked = true; t.beat_strength = 1.0f;
  } else {
    t = k1_tempo_read();
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

  // 1. Flow the previous river OUTWARD by the tempo-locked drift, with decay.
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION,
              drift, SQ15x16(TR_TRAIL_ALPHA));

  // Keep the river in the upper (mirror-authoritative) half; clear cross-centre bleed.
  for (uint16_t i = 0; i < HALF; i++) { leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0; }

  // 2. Inject the live spectrum: bin k -> pixel HALF+k, colour BY FREQUENCY.
  uint8_t iters = (uint8_t)rp->SQUARE_ITER; if (iters > TR_MAX_ITERS) iters = TR_MAX_ITERS;
  for (uint16_t k = 0; k < NUM_FREQS && k < HALF; k++) {
    float e = float(spectrogram_smooth[k]);
    if (!isfinite(e) || e < 0.0f) e = 0.0f; if (e > 1.0f) e = 1.0f;
    for (uint8_t s = 0; s < iters; s++) e *= e;               // contrast (square-iter)
    if (e < TR_FLOOR) continue;
    const float hue = float(k) / float(NUM_FREQS - 1);        // frequency -> palette position
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(e * TR_INJECT_GAIN));
    const uint16_t idx = HALF + k;
    leds_16[idx].r += col.r; leds_16[idx].g += col.g; leds_16[idx].b += col.b;
  }

  // 3. Bound additive overflow before it becomes next frame's trail state.
  finalize_additive_frame(leds_16, leds_prev_buffer, true);

  // 4. Centre-origin mirror (upper half -> lower half).
  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);
}
