// ============================================================================
// light_mode_waveform_tempo.cpp — Beat/Tempo-Phase-Locked Motion (WIP-1)
// ----------------------------------------------------------------------------
// Landed from light_mode_waveform_tempo.cpp.wip (wip/tempo-waveform-checkpoint
// @ 8767589). NOW INTEGRATED + SHIPPING: dispatched (lightshow_modes.h + .ino),
// enum LIGHT_MODE_WAVEFORM_TEMPO (config_types.h), and the secondary boot default
// (globals.h). The "Captain on-device validation" this was landed for IS E1
// (docs/E1_SCOPE.md in k1-analysis-harness): vpab phase-lock + FEEL verdict.
//
// THE DESIGN LAW [MEASURED] (docs/measurements/apparent-motion-on-k1.md §8):
//   The K1 motion↔blink boundary is an INTER-STEP INTERVAL threshold (~36–60 ms),
//   NOT a px/s figure. A naïve beat-lock that JUMPS the trace forward on each beat
//   spaces its steps ~500 ms apart @120 BPM — ~10× past the fusion floor — so it
//   reads as a discrete TELEPORT/BLINK on every beat, not motion. ∴ this mode
//   modulates the CONTINUOUS per-frame scroll VELOCITY (tempo-locked rate, still
//   stepping every render frame ≈5.4 ms, deep in the smooth regime); the eye reads
//   the lock from the per-beat velocity SURGE, never from a position jump.
//
// FACTS from source [FACT]:
//   - k1_tempo IS wired into the Core-0 audio loop at this base (the .wip era it
//     was not): SPECTRASYNQ_K1_FIRMWARE.ino calls k1_tempo_init() in setup and
//     k1_tempo_update(k1_audio_snapshot_read()) per AP frame (~133 Hz; self-clocks
//     a 44.4 Hz novelty feed). So K1TempoEvent is live; this effect is a read-only
//     consumer (k1_tempo_read() — value-copy under a portMUX, safe from Core-1).
//   - K1TempoEvent (k1_tempo.h): bpm (60..156); phase01∈[0,1), 0==beat;
//     confidence∈[0,1] (already silence-scaled); locked; beat_tick; beat_strength.
//   - K1AudioSnapshot.silence gates the idle fallback so the strip halts in true
//     silence (graceful behaviour, not a frozen frame).
//
// VP-PROBE DETERMINISM (change-gate: deterministic under the probe):
//   - This mode IS in the Tier-A vp_run_output_probe roster (lightshow_modes.h) and
//     emits nondet=0 — it is HASHED, not excluded. (The earlier "NOT in the roster,
//     roster ends at QUANTUM_COLLAPSE" note was STALE: the roster was later expanded
//     to every mode. Trust the live roster in lightshow_modes.h, not this comment.)
//   - It is reproducible under the probe because when led_thread is halted
//     (vp_run_output_probe sets led_thread_halt=true before rendering) the effect
//     uses a FIXED dt and a FROZEN synthetic tempo event instead of millis()/
//     k1_tempo_read(), so two probe runs produce an identical frame. (cf. the
//     Quantum Collapse lesson: the probe halts led_thread but NOT Core-0/k1_tempo,
//     so naive live reads would diverge.)
//   - It is a float-output WAVEFORM-family mode, so the hash is codegen-sensitive
//     under -O3 -ffast-math (cf. WAVEFORM_HYBRID). The golden baseline row is
//     therefore fp_tolerant (energy-tolerant; hash = INFO), with motion validated
//     visually + by vpab, not by a strict bit-hash.
//
// COLOUR (gate-compliant): uses effect_palette_or_chroma_colour() — the PROVEN
// BLOOM-lineage colour authority (lightshow_modes.h §213) — so palette mode,
// chromatic note-sum, and auto-colour-shift are all honoured identically to the
// reference. It does NOT roll raw HSV and does NOT call palette_chroma_colour
// directly (that is the palette-only engine).
//
// CENTRE-ORIGIN: in the default MIRROR_ENABLED path the sample is drawn into the
// upper-half source position and mirror_image_downwards() reflects it → the motion
// radiates from centre (canon). The un-mirrored full-strip path is the explicit
// non-mirrored fallback.
//
// NO HEAP in the render path. NO shared static state (all per-frame state is the
// per-channel ChannelEffectState passed by reference). Scroll uses the global
// leds_16 history transport like the other WAVEFORM-family modes.
// ============================================================================

#include "lightshow_modes.h"
#include "k1_tempo.h"
#include "k1_audio_snapshot.h"
#include <math.h>

// ── Feel knobs (in-file constants; deliberately NOT RenderParams fields) ──────
// These are tuning constants, not runtime-tunable CONFIG, and need no SECONDARY_*
// override, so keeping them here avoids touching build_primary/secondary_render_
// params() and the CONFIG struct (lower blast radius for a quarantined branch).
static const float K1_TWO_PI_F      = 6.28318530718f;
static const float TEMPO_PX_PER_BEAT = 24.0f;  // px travelled per beat (base scroll distance)
static const float TEMPO_DEPTH       = 0.5f;   // intra-beat velocity surge depth (0..1) — the "feel" knob
static const float TEMPO_IDLE_RATE   = 30.0f;  // px/s fallback scroll when unlocked (and not silent)
static const float TEMPO_LEAD        = 0.0f;   // beat anticipation (0..~0.15); 0 = surge ON the beat
static const float TEMPO_CONF_LO     = 0.30f;  // confidence gate lower edge
static const float TEMPO_CONF_HI     = 0.60f;  // confidence gate upper edge (== K1_LOCK_CONFIDENCE)
static const int   TEMPO_STEP_CEIL   = 30;     // [MEASURED] correspondence ceiling (~28–32 px), px/frame cap

static inline float t_smoothstep(float lo, float hi, float x) {
  if (hi <= lo) return (x >= hi) ? 1.0f : 0.0f;
  float t = (x - lo) / (hi - lo);
  if (t < 0.0f) t = 0.0f; else if (t > 1.0f) t = 1.0f;
  return t * t * (3.0f - 2.0f * t);
}

// ── REUSABLE OWNED MOTION PRIMITIVE ──────────────────────────────────────────
// Scrolls the global leds_16 buffer by an integer step count derived from a
// continuous, tempo-locked, phase-shaped VELOCITY, stepping EVERY frame. Any
// MAPPING draws after. Feature-agnostic; this is the engine, the mode below is one
// demo of it.
static void tempo_scroll_step(float& accum, uint32_t& last_ms, const RenderParams* rp) {
  // ── Deterministic path under the VP probe (led_thread halted) ──────────────
  // Use a fixed dt and a frozen synthetic tempo so a probe render is reproducible.
  const bool probe = led_thread_halt;

  uint32_t now = probe ? 0u : millis();
  float dt;
  if (probe) {
    dt = 1.0f / 120.0f;                 // fixed nominal frame for reproducibility
  } else {
    dt = (last_ms == 0) ? (1.0f / 120.0f) : (now - last_ms) * 0.001f;
    last_ms = now;
    if (dt < 0.001f) dt = 0.001f; else if (dt > 0.050f) dt = 0.050f;
  }

  K1TempoEvent t;
  K1AudioSnapshot a;
  if (probe) {
    // Frozen, deterministic stand-ins (no millis(), no live AP state).
    t.bpm = 120.0f; t.phase01 = 0.0f; t.confidence = 1.0f;
    t.beat_tick = false; t.locked = true; t.beat_strength = 1.0f;
    a.frame_ms = 0; a.peak_scaled = 0.45f; a.vu_level = 0.35f; a.novelty = 0.5f;
    a.spectral_energy = 0.5f; a.low_energy = 0.5f; a.mid_energy = 0.5f;
    a.high_energy = 0.5f; a.chroma_strength = 0.5f; a.silence = false;
  } else {
    t = k1_tempo_read();
    a = k1_audio_snapshot_read();
  }

  float base_px_s = TEMPO_PX_PER_BEAT * (t.bpm / 60.0f);     // [FACT bpm ∈ 60..156]

  // Mean-preserving intra-beat velocity envelope — surge at the beat (phase01==0).
  float ph  = t.phase01 - TEMPO_LEAD;
  float env = 1.0f + TEMPO_DEPTH * cosf(K1_TWO_PI_F * ph);
  if (env < 0.0f) env = 0.0f;                                // never scroll backward
  float tempo_px_s = base_px_s * env;

  // Confidence gate + graceful fallback. t.confidence is already silence-scaled.
  float gate      = t_smoothstep(TEMPO_CONF_LO, TEMPO_CONF_HI, t.confidence);
  float idle_px_s = a.silence ? 0.0f : TEMPO_IDLE_RATE;      // halt in true silence
  float rate_px_s = idle_px_s + (tempo_px_s - idle_px_s) * gate;

  accum += rate_px_s * dt;
  int steps = (int)accum;
  if (steps > TEMPO_STEP_CEIL) steps = TEMPO_STEP_CEIL;
  if (steps > 0) {
    accum -= steps;
    if (rp->MIRROR_ENABLED) waveform_shift_upper_half_up(leds_16, (uint8_t)steps);
    else                    shift_leds_up(leds_16, (uint16_t)steps);
  }
}

// ── EXAMPLE MODE ──────────────────────────────────────────────────────────────
// Tempo-velocity MOTION + a palette-compliant chromagram MAPPING. The mapping is
// swappable; the engine above is the point.
void light_mode_waveform_tempo(ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;

  // MOTION — reactive persistence (canon §4.3): the trail breathes shorter when
  // louder, so a busy passage keeps a tight head while a sparse one leaves a tail.
  float abs_amp = fabsf(waveform_peak_scaled);
  if (abs_amp > 1.0f) abs_amp = 1.0f;
  SQ15x16 fade = SQ15x16(1.0f - 0.10f * abs_amp);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade; leds_16[i].g *= fade; leds_16[i].b *= fade;
  }

  // MOTION — the tempo-locked continuous scroll velocity (steps every frame).
  tempo_scroll_step(fx.tempo_scroll_accum, fx.tempo_last_ms, rp);

  // MAPPING — sanctioned palette/chroma authority (palette mode, chromatic
  // note-sum, and auto-colour-shift honoured identically to BLOOM/Aurora/Comet).
  // Brightness scales with the chroma energy folded inside the helper; pass full
  // scale and let the helper's chromagram energy modulate value.
  CRGB16 col = effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0f));

  // Draw the sample into the upper-half source position so the mirror reflects it
  // for free (centre-origin). Un-mirrored: full-strip amplitude position.
  float amp = waveform_peak_scaled;
  uint16_t pos = rp->MIRROR_ENABLED ? waveform_upper_half_source_position(amp)
                                    : waveform_full_strip_position(amp);
  leds_16[pos] = col;

  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);
}
