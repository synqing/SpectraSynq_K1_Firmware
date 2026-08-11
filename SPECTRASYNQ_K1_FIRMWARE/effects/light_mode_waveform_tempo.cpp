// ============================================================================
// light_mode_waveform_tempo.cpp — Beat/Tempo-Phase-Locked Motion (WIP-1)
// ----------------------------------------------------------------------------
// Landed from light_mode_waveform_tempo.cpp.wip (wip/tempo-waveform-checkpoint
// @ 8767589). QUARANTINED branch wf/wip-tempo — for Captain on-device validation;
// NOT merged into integration, NOT flashed this run.
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
//   - K1AudioSnapshot.silence halts tempo scroll in true silence; without an active
//     dark gate (presence loss / silence) the reactive fade also stops
//     when peak≈0 (fade→1.0), which freezes the last frame — see dark_gate below.
//
// Bench Unit 2 / IM73D dark-plate (2026-08-09 Captain correction — mode 18):
//   Prior agents chased WAVEFORM_HYBRID_K1 (32). On WAVEFORM TEMPO the glass
//   stayed dead while AP peak_scaled/lock were healthy because (1) presence
//   required vu_level≥0.05 (IM73D vu often ~0.01) so dark_gate never painted,
//   and (2) effect_palette_or_chroma_colour() is chromagram-only in chromatic
//   mode → near-black inject when chroma is thin. Same colour-level fallback
//   pattern as mode 11 / hybrid_k1; presence now keys on peak|vu.
//
// VP-PROBE DETERMINISM (change-gate: freeze tempo / deterministic clock during the
// probe, OR mark nondeterministic-excluded):
//   - This mode is NOT in the Tier-A vp_run_output_probe roster (lightshow_modes.h)
//     — like AURORA / COMET / SPECTRUM_RIVER* / EMBER* it is omitted, i.e.
//     nondeterministic-EXCLUDED from the bit-hash gate by construction. The roster
//     ends at QUANTUM_COLLAPSE; only the Tier-A core is hashed.
//   - BELT AND BRACES: should it ever be added to a probe, the effect itself is
//     made reproducible — when led_thread is halted (vp_run_output_probe sets
//     led_thread_halt=true before rendering) the effect uses a FIXED dt and a
//     FROZEN synthetic tempo event instead of millis()/k1_tempo_read(), so two
//     probe runs produce an identical frame. (cf. the Quantum Collapse lesson:
//     the probehalts led_thread but NOT Core-0/k1_tempo, so live reads diverge.)
//
// COLOUR (gate-compliant): uses effect_palette_or_chroma_colour() — the PROVEN
// BLOOM-lineage colour authority (lightshow_modes.h §213) — so palette mode,
// chromatic note-sum, and auto-colour-shift are all honoured identically to the
// reference. When that path yields near-black under thin chroma, a peak-seeded
// fallback (mode-11 idiom) keeps the plate lit. It does NOT roll free rainbow.
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

static const float TEMPO_QUIET_ALPHA = 0.82f;  // history drain when presence lost (matches Dense Forge)
static const float TEMPO_PRESENCE_FLOOR = 0.02f;

static inline float tempo_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static bool tempo_presence_ok(const K1AudioSnapshot& snap, float peak) {
  // Peak OR vu — IM73D often shows vu≈0.01 while peak_scaled is 0.5–0.9. The
  // prior vu≥0.05 hard floor latched dark_gate and starved the glass (2026-08-09).
  const float level = fmaxf(peak, snap.vu_level);
  if (level < TEMPO_PRESENCE_FLOOR) return false;
  // Soft spectral/novelty veto only when level is also thin (Dense Forge contract
  // without the obsolete vu floor).
  if (snap.spectral_energy < 0.08f && snap.novelty < 0.08f && level < 0.08f) {
    return false;
  }
  return true;
}

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

// Peak-seeded colour when chromagram-only colour is near-black (mode 11 / hybrid_k1).
static CRGB16 tempo_peak_fallback_colour(const RenderParams* rp, bool render_secondary,
                                         float peak) {
  const float fb = tempo_clamp01(peak * VP_WAVEFORM_FALLBACK_BRIGHTNESS);
  CRGB16 fallback_col;
  if (render_params_palette_owns_colour(rp, render_secondary)) {
    const CRGBPalette16& pal =
        cached_gradient_palette(render_params_palette_index(rp, render_secondary),
                                render_secondary);
    fallback_col = clamp_crgb16(
        palette_manual_colour(pal, SQ15x16(rp->CHROMA), SQ15x16(fb)));
    const float fb_max = fmaxf(fmaxf(float(fallback_col.r), float(fallback_col.g)),
                               float(fallback_col.b));
    if (fb > 0.0f && fb_max < 0.02f) {
      fallback_col = hsv(SQ15x16(rp->CHROMA), SQ15x16(rp->SATURATION), SQ15x16(fb));
    }
  } else {
    fallback_col = hsv(SQ15x16(rp->CHROMA), SQ15x16(rp->SATURATION), SQ15x16(fb));
  }
  return clamp_crgb16(fallback_col);
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
#if defined(K1_MIC_IM73D_PDM_V1)
  // IM73D lock floor is 0.28; SPH-calibrated TEMPO_CONF_HI=0.60 leaves gate≈0
  // while lock=1 and conf sits ~0.28–0.42. Prefer lock as velocity authority.
  if (t.locked) {
    float lock_gate = t_smoothstep(0.20f, 0.40f, t.confidence);
    if (lock_gate < 0.55f) lock_gate = 0.55f;
    if (gate < lock_gate) gate = lock_gate;
  }
#endif
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
  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  // OR live global peak so a torn/stale snapshot cannot black the plate while
  // AP peak_scaled is hot (same Unit-2 lesson as hybrid_k1).
  const float peak =
      tempo_clamp01(fmaxf(snap.peak_scaled, (float)waveform_peak_scaled));
  const bool presence = tempo_presence_ok(snap, peak);
  // True silence only when silence latch AND no live peak — a latched silence
  // flag must never zero a live signal (hybrid_k1 2026-08-09).
  const bool dark_gate = (snap.silence && peak < TEMPO_PRESENCE_FLOOR) || !presence;

  // MOTION — reactive persistence (canon §4.3): the trail breathes shorter when
  // louder, so a busy passage keeps a tight head while a sparse one leaves a tail.
  // When presence is lost, switch to a fixed drain alpha so scroll halt does not
  // leave a painted frame frozen (2026-06-07 secondary dark-state verdict).
  SQ15x16 fade;
  if (dark_gate) {
    fade = SQ15x16(TEMPO_QUIET_ALPHA);
  } else {
    float abs_amp = peak;
    fade = SQ15x16(1.0f - 0.10f * abs_amp);
  }
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade; leds_16[i].g *= fade; leds_16[i].b *= fade;
  }

  // MOTION — the tempo-locked continuous scroll velocity (steps every frame).
  tempo_scroll_step(fx.tempo_scroll_accum, fx.tempo_last_ms, rp);

  if (dark_gate) {
#ifdef M18_DARK_DIAG
    if (!render_secondary) {
      static uint32_t m18_dbg_last_ms = 0;
      const uint32_t now_ms = millis();
      if (now_ms - m18_dbg_last_ms >= 1000) {
        m18_dbg_last_ms = now_ms;
        const K1TempoEvent te = k1_tempo_read();
        USBSerial.printf(
            "[M18] ledmax=0.0000 dark=1 peak=%.3f vu=%.3f gpeak=%.3f "
            "silence=%d presence=%d conf=%.2f lock=%d phase=%.2f bpm=%.1f\n",
            peak, snap.vu_level, (float)waveform_peak_scaled,
            snap.silence ? 1 : 0, presence ? 1 : 0, te.confidence,
            te.locked ? 1 : 0, te.phase01, te.bpm);
      }
    }
#endif
    return;  // drain only — do not repaint stale history from chroma/palette
  }

  // MAPPING — sanctioned palette/chroma authority, with peak-seeded fallback when
  // chromagram energy collapses (IM73D quiet floor / gate_gain≪1).
  CRGB16 col = effect_palette_or_chroma_colour(rp, render_secondary, SQ15x16(1.0f));
  const float col_max =
      fmaxf(fmaxf(float(col.r), float(col.g)), float(col.b));
  if (col_max < 0.02f && peak >= TEMPO_PRESENCE_FLOOR) {
    col = tempo_peak_fallback_colour(rp, render_secondary, peak);
  }

  // Draw the sample into the upper-half source position so the mirror reflects it
  // for free (centre-origin). Un-mirrored: full-strip amplitude position.
  float amp = peak;
  uint16_t pos = rp->MIRROR_ENABLED ? waveform_upper_half_source_position(amp)
                                    : waveform_full_strip_position(amp);
  leds_16[pos] = col;

  if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);

#ifdef M18_DARK_DIAG
  // Opt-in 1 Hz LED-buffer probe (bench only):
  //   PLATFORMIO_BUILD_FLAGS=-DM18_DARK_DIAG bash scripts/agent/pio-build.sh k1_custom
  if (!render_secondary) {
    static uint32_t m18_dbg_last_ms = 0;
    const uint32_t now_ms = millis();
    if (now_ms - m18_dbg_last_ms >= 1000) {
      m18_dbg_last_ms = now_ms;
      float led_max = 0.0f;
      for (uint16_t i = 0; i < NATIVE_RESOLUTION; ++i) {
        const float r = float(leds_16[i].r);
        const float g = float(leds_16[i].g);
        const float b = float(leds_16[i].b);
        if (r > led_max) led_max = r;
        if (g > led_max) led_max = g;
        if (b > led_max) led_max = b;
      }
      const K1TempoEvent te = k1_tempo_read();
      USBSerial.printf(
          "[M18] ledmax=%.4f dark=0 peak=%.3f vu=%.3f gpeak=%.3f amp=%.3f "
          "pos=%u col=%.3f/%.3f/%.3f colmax=%.3f silence=%d presence=%d "
          "conf=%.2f lock=%d phase=%.2f bpm=%.1f mirror=%d\n",
          led_max, peak, snap.vu_level, (float)waveform_peak_scaled, amp,
          (unsigned)pos, float(col.r), float(col.g), float(col.b), col_max,
          snap.silence ? 1 : 0, presence ? 1 : 0, te.confidence,
          te.locked ? 1 : 0, te.phase01, te.bpm, rp->MIRROR_ENABLED ? 1 : 0);
    }
  }
#endif
}
