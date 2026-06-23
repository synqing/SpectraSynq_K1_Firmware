#include "lightshow_modes.h"
#include "sb_audio_snapshot.h"

// ============================================================================
// light_mode_river_surge — "River Surge" (mode 28): Spectrum River v2 that
// feels the SONG ARC. Builds compress and accelerate the flow; the drop
// releases a single travelling wavefront.
// ----------------------------------------------------------------------------
// FAITHFUL VARIANT of light_mode_spectrum_river_v2: the entire winning loop is
// byte-for-byte (continuous 80-bin->80-px spectrum map, sub-pixel draw_sprite
// outward transport, frequency->palette colour, constant ALPHA=0.90 persistence,
// floor/contrast/inject caps, bass-tide drift breathing). ONE axis is added:
// macro-dynamics, computed ENTIRELY VP-side from the published snapshot — zero
// audio-pipeline changes.
//
// Compact 6-Pass summary (per docs/architecture/effect-decomposition):
//  P1 What: frequency-as-space river + a macro-dynamic (build/drop) overlay.
//  P2 Verbs: Update tide -> Update macro EMAs -> Flow -> Clear centre ->
//     Inject spectrum -> Inject wavefront -> Snapshot+Clamp -> Mirror.
//  P3 Layers: L1 adds snap.spectral_energy (broadband) beside low_energy;
//     L2 adds fx.rsurge_* (two EMAs, peak-hold, timers, one wavefront);
//     L3/L4 unchanged (1:1 bin->pixel, freq->palette); L5 gains the macro
//     transport multiplier m; L6 keeps all v2 clamps + silence hard gate on
//     the added axis.
//  P4 Levers: FAST_TAU/SLOW_TAU (arc bandwidth), BUILD_HOT/DROP_FLOOR
//     (trigger geometry), REFRACT_S, WF_SPEED_X/WF_LIFE_S/WF_HALF_W.
//  P5 Maths -> perception:
//     · build_ratio = fastEMA(E, tau 0.5 s) / max(slowEMA(E, tau 20 s), 0.05),
//       clamped [0.5, 2.0]. The slow EMA is the song's own energy baseline, so
//       the ratio is a self-normalising "where are we in the arc" readout:
//       >1 = building, <1 = relaxing. Transport multiplier
//       m = clamp(0.7 + 0.55*(build_ratio - 0.5), 0.7, 1.75) — [PERCEPTION]
//       a build visibly accelerates and tightens the river (history rushes
//       outward, trails shorten in space); a quiet verse relaxes it. Because
//       both EMAs use alpha = dt/tau the feel is frame-rate independent, and
//       because m never reaches 0 the Organic Law constant-refresh contract
//       holds — the river NEVER stops scrolling.
//     · Drop gesture: rolling ~4 s peak-hold of the fast EMA. Trigger when the
//       build was hot (build_ratio > 1.30 within the last 2 s) AND the energy
//       floor falls out (fast < 0.45 * rolling_peak). One ~6 px wavefront
//       spawns at centre and travels outward at 2.5x the river's own speed,
//       intensity decaying over a ~0.8 s life, coloured by the river's own
//       frequency->palette contract sampled at its position — [PERCEPTION] the
//       drop reads as a single bright wave SURGING DOWN the river, a spatial
//       transport gesture (Strobe-Law-clean: a localised travelling object,
//       NEVER a global flash). 4 s refractory: one drop, one wave.
//  P6 Reusable: dual-timescale EMA ratio = song-arc sensor from one published
//     scalar; decaying peak-hold + ratio-memory = drop detector with no audio-
//     pipeline change; "wavefront rides the transport" generalises to any
//     scroll-family effect.
//
// State: fx.rsurge_* only (no heap, no file-scope mutable statics). History in
// the passed leds_prev_buffer, exactly as SRv2. dt clamped like
// dense_forge_chord. Hard gate: in snap.silence the added axis never spawns a
// wavefront (the original's per-bin floor gating is preserved unchanged).
// ============================================================================

// --- byte-faithful SRv2 loop constants (renamed RSURGE_, values identical) ---
static const float   RSURGE_DRIFT_BASE   = 0.55f; // matches SR v1/v2 base
static const float   RSURGE_DRIFT_FLOOR  = 0.9f;  // always scroll >= 0.9x base (constant refresh — no holding)
static const float   RSURGE_DRIFT_SURGE  = 0.9f;  // drift = BASE*(FLOOR + SURGE*tide) => up to ~1.8x on bass
static const float   RSURGE_ALPHA        = 0.90f; // CONSTANT == SR v1/v2. Never raise (the "hold" bug).
static const float   RSURGE_TIDE_EMA     = 0.05f; // slow EMA on bass energy (organic)
static const float   RSURGE_FLOOR        = 0.015f;
static const float   RSURGE_INJECT_GAIN  = 0.90f; // == SR v1/v2 (do not raise)
static const uint8_t RSURGE_MAX_ITERS    = 4;

// --- added axis: macro-dynamics (song arc) ---
static const float   RSURGE_FAST_TAU_S   = 0.5f;  // fast energy EMA time constant
static const float   RSURGE_SLOW_TAU_S   = 20.0f; // slow energy EMA time constant (song baseline)
static const float   RSURGE_SLOW_MIN     = 0.05f; // ratio denominator floor
static const float   RSURGE_PEAK_TAU_S   = 4.0f;  // rolling peak-hold decay time
static const float   RSURGE_BUILD_HOT    = 1.30f; // build_ratio above this arms the drop
static const float   RSURGE_BUILD_MEM_S  = 2.0f;  // armed window after the build cools
static const float   RSURGE_DROP_FLOOR   = 0.45f; // fast < this fraction of peak = floor fell out
static const float   RSURGE_REFRACT_S    = 4.0f;  // minimum spacing between drop wavefronts
static const float   RSURGE_WF_SPEED_X   = 2.5f;  // wavefront speed as multiple of river drift
static const float   RSURGE_WF_LIFE_S    = 0.8f;  // wavefront lifetime
static const float   RSURGE_WF_HALF_W    = 3.0f;  // half-width in px (~6 px band)
static const float   RSURGE_WF_GAIN      = 0.95f; // wavefront injection brightness cap

void light_mode_river_surge(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  // dt — clamped exactly like dense_forge_chord (first frame uses a fixed dt).
  const uint32_t prev_ms = fx.rsurge_last_ms;
  const uint32_t now_ms = millis();
  float dt = (prev_ms != 0) ? float(now_ms - prev_ms) * 0.001f : (1.0f / 120.0f);
  fx.rsurge_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;

  SBAudioSnapshot snap = sb_audio_snapshot_read();

  // Tide envelope: slow EMA of bass energy -> breathing drift (byte-faithful
  // SRv2 maths; own rsurge_ field so the variant never bleeds into SRv2 state).
  float low = snap.low_energy;
  if (!isfinite(low) || low < 0.0f) low = 0.0f;
  if (low > 1.0f) low = 1.0f;
  fx.rsurge_tide_env += (low - fx.rsurge_tide_env) * RSURGE_TIDE_EMA;
  float tide = fx.rsurge_tide_env;
  if (tide < 0.0f) tide = 0.0f;
  if (tide > 1.0f) tide = 1.0f;

  // --- ADDED AXIS: macro-dynamics from the published broadband energy ---
  float energy = snap.spectral_energy;
  if (!isfinite(energy) || energy < 0.0f) energy = 0.0f;
  if (energy > 1.0f) energy = 1.0f;

  float a_fast = dt / RSURGE_FAST_TAU_S;
  float a_slow = dt / RSURGE_SLOW_TAU_S;
  if (a_fast > 1.0f) a_fast = 1.0f;
  if (a_slow > 1.0f) a_slow = 1.0f;
  if (prev_ms == 0) {
    // Seed on first frame so the slow baseline doesn't start at zero and
    // saturate build_ratio (which would fake a build at power-on).
    fx.rsurge_fast_env = energy;
    fx.rsurge_slow_env = energy;
    fx.rsurge_peak_env = energy;
  }
  fx.rsurge_fast_env += (energy - fx.rsurge_fast_env) * a_fast;
  fx.rsurge_slow_env += (energy - fx.rsurge_slow_env) * a_slow;

  float slow_floor = fx.rsurge_slow_env;
  if (slow_floor < RSURGE_SLOW_MIN) slow_floor = RSURGE_SLOW_MIN;
  float build_ratio = fx.rsurge_fast_env / slow_floor;
  if (build_ratio < 0.5f) build_ratio = 0.5f;
  if (build_ratio > 2.0f) build_ratio = 2.0f;

  // Transport multiplier: builds accelerate, verses relax. Never below 0.7 —
  // combined with DRIFT_FLOOR the river always scrolls (Organic Law).
  float m = 0.7f + 0.55f * (build_ratio - 0.5f);
  if (m < 0.7f)  m = 0.7f;
  if (m > 1.75f) m = 1.75f;

  // Rolling ~4 s decaying peak-hold of the fast EMA.
  float peak_decay = 1.0f - (dt / RSURGE_PEAK_TAU_S);
  if (peak_decay < 0.0f) peak_decay = 0.0f;
  fx.rsurge_peak_env *= peak_decay;
  if (fx.rsurge_fast_env > fx.rsurge_peak_env) fx.rsurge_peak_env = fx.rsurge_fast_env;

  // "Build was hot within the last 2 s" memory + refractory countdowns.
  if (build_ratio > RSURGE_BUILD_HOT) {
    fx.rsurge_build_recent_s = RSURGE_BUILD_MEM_S;
  } else if (fx.rsurge_build_recent_s > 0.0f) {
    fx.rsurge_build_recent_s -= dt;
    if (fx.rsurge_build_recent_s < 0.0f) fx.rsurge_build_recent_s = 0.0f;
  }
  if (fx.rsurge_refractory_s > 0.0f) {
    fx.rsurge_refractory_s -= dt;
    if (fx.rsurge_refractory_s < 0.0f) fx.rsurge_refractory_s = 0.0f;
  }

  // Drop trigger: recent build + the energy floor falls out. Hard-gated on
  // silence so end-of-track never fires a phantom drop.
  if (!fx.rsurge_wf_active && !snap.silence &&
      fx.rsurge_refractory_s <= 0.0f &&
      fx.rsurge_build_recent_s > 0.0f &&
      fx.rsurge_fast_env < RSURGE_DROP_FLOOR * fx.rsurge_peak_env) {
    fx.rsurge_wf_active = 1;
    fx.rsurge_wf_pos = float(HALF);  // born at centre, like every injection
    fx.rsurge_wf_life = 1.0f;
    fx.rsurge_refractory_s = RSURGE_REFRACT_S;
    fx.rsurge_build_recent_s = 0.0f;
  }

  // 1. Flow OUTWARD — ALWAYS scrolling (constant refresh); drift surges with
  //    bass tide AND the macro arc multiplier m. Persistence CONSTANT (== v2).
  const float drift = RSURGE_DRIFT_BASE * (RSURGE_DRIFT_FLOOR + RSURGE_DRIFT_SURGE * tide) * m * (float(NATIVE_RESOLUTION) / 128.0f);

  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION, drift, SQ15x16(RSURGE_ALPHA));
  for (uint16_t i = 0; i < HALF; i++) { leds_16[i].r = 0; leds_16[i].g = 0; leds_16[i].b = 0; }

  // 2. Inject the live spectrum (identical to SR v2: bin k -> pixel HALF+k,
  //    colour by frequency, brightness by contrast-enhanced energy).
  uint8_t iters = (uint8_t)rp->SQUARE_ITER;
  if (iters > RSURGE_MAX_ITERS) iters = RSURGE_MAX_ITERS;
  for (uint16_t k = 0; k < NUM_FREQS && k < HALF; k++) {
    float e = float(spectrogram_smooth[k]);
    if (!isfinite(e) || e < 0.0f) e = 0.0f;
    if (e > 1.0f) e = 1.0f;
    for (uint8_t s = 0; s < iters; s++) e *= e;
    if (e < RSURGE_FLOOR) continue;
    const float hue = float(k) / float(NUM_FREQS - 1);
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(e * RSURGE_INJECT_GAIN));
    const uint16_t idx = HALF + k;
    leds_16[idx].r += col.r;
    leds_16[idx].g += col.g;
    leds_16[idx].b += col.b;
  }

  // 2b. Drop wavefront: ONE localised ~6 px band riding outward at 2.5x the
  //     river's own speed, intensity decaying over its life, coloured by the
  //     river's frequency->palette contract at its position. Injected before
  //     the snapshot so its wake joins the flowing history — a travelling
  //     object, NEVER a global brightness gesture.
  if (fx.rsurge_wf_active) {
    fx.rsurge_wf_pos += RSURGE_WF_SPEED_X * drift;
    fx.rsurge_wf_life -= dt / RSURGE_WF_LIFE_S;
    if (fx.rsurge_wf_life <= 0.0f || fx.rsurge_wf_pos >= float(NATIVE_RESOLUTION - 1)) {
      fx.rsurge_wf_active = 0;
      fx.rsurge_wf_life = 0.0f;
    } else {
      const float inten = fx.rsurge_wf_life;  // 1 -> 0 over ~0.8 s
      float wf_hue = (fx.rsurge_wf_pos - float(HALF)) / float(NUM_FREQS - 1);
      if (wf_hue < 0.0f) wf_hue = 0.0f;
      if (wf_hue > 1.0f) wf_hue = 1.0f;
      const int centre = int(fx.rsurge_wf_pos + 0.5f);
      const int half_w = int(RSURGE_WF_HALF_W);
      for (int o = -half_w; o <= half_w; o++) {
        const int idx = centre + o;
        if (idx < int(HALF) || idx >= int(NATIVE_RESOLUTION)) continue;  // upper half only (mirror handles the rest)
        const float w = 1.0f - (float(o < 0 ? -o : o) / (RSURGE_WF_HALF_W + 1.0f));  // triangular profile
        CRGB16 col = palette_manual_colour(pal, SQ15x16(wf_hue), SQ15x16(inten * w * RSURGE_WF_GAIN));
        leds_16[idx].r += col.r;
        leds_16[idx].g += col.g;
        leds_16[idx].b += col.b;
      }
    }
  }

  // 3. Bound additive overflow before it becomes next frame's flow.
  finalize_additive_frame(leds_16, leds_prev_buffer, true);

  // 4. Mirror.
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
