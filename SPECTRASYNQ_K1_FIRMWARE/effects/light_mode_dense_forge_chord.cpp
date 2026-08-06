#include "lightshow_modes.h"
#include "k1_audio_snapshot.h"
#include "k1_onset_beat.h"
#include "k1_tempo.h"

// ============================================================================
// light_mode_dense_forge_chord — "Dense Forge Chord": Dense Forge variant with
// a chord→hue anchor (Tier 1 item 1, 2026-06-11 hardened re-run).
// ----------------------------------------------------------------------------
// VARIANT CONTRACT (Captain 2026-06-11): original effects are never modified —
// new behaviour lands as a new mode. This file is a self-contained copy of
// light_mode_dense_forge with ONE addition: the inject hue base is pulled
// toward the held chord root (same A-origin hue wheel as
// chromagram_centroid_hue) instead of using the raw centroid alone.
// Hue-only — brightness/motion identical to Dense Forge (Strobe-Law-clean).
// With K1_CHORD_HUE_V1 undefined this renders identically to Dense Forge.
// Recon + liveness evidence: _scratch/fix-investigation/window-audit/
// 08-tier1-chord-recon.md (conf 98.4% ≥0.70 real material; raw root flicker
// 5.25/s → 250 ms hold → 0.83/s).
// Shares fx.dforge_* lattice state with Dense Forge (one mode per channel at a
// time; per-channel state — no cross-talk).
// ============================================================================

static const float DFORGE_TRANSPORT_BASE  = 0.50f;
static const float DFORGE_TRANSPORT_FLOOR = 0.88f;
static const float DFORGE_TRANSPORT_SURGE = 0.80f;
static const float DFORGE_TRANSPORT_ALPHA = 0.90f;
static const float DFORGE_QUIET_ALPHA     = 0.82f;
static const float DFORGE_SPRING_K     = 22.0f;
static const float DFORGE_DAMPING      = 7.5f;
static const float DFORGE_KAPPA0       = 2.2f;
static const float DFORGE_IMPULSE      = 5.0f;
static const float DFORGE_MAX_VEL      = 0.32f;   // normalised / sec
static const float DFORGE_POS_EPS      = 0.02f;
static const float DFORGE_POS_MAX      = 0.98f;
static const float DFORGE_MOIRE_GAIN   = 0.48f;
static const float DFORGE_STREAK_GAIN  = 0.55f;
static const float DFORGE_ACTIVITY_EMA = 0.05f;
static const float DFORGE_FLOOR        = 0.008f;

static const float DFORGE_OMEGA[DFORGE_LATTICE_N] = {
  1.00f, 1.12f, 1.25f, 1.33f, 1.50f, 1.67f, 1.85f, 2.00f
};

static float dforge_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static bool dforge_presence_ok(const K1AudioSnapshot& snap) {
  return !(snap.spectral_energy < 0.08f && snap.novelty < 0.08f);
}

static float dforge_band_target(uint8_t band, uint8_t bands, uint8_t bins_per_band,
                                uint8_t analysis_bins) {
  float sum = 0.0f;
  const uint16_t start = uint16_t(band) * bins_per_band;
  const uint16_t end = start + bins_per_band;
  for (uint16_t k = start; k < end && k < analysis_bins; k++) {
    float e = float(spectrogram_smooth[k]);
    if (!isfinite(e) || e < 0.0f) e = 0.0f;
    if (e > 1.0f) e = 1.0f;
    sum += e;
  }
  return dforge_clamp01(sum / float(bins_per_band));
}

static float dforge_strip_norm(uint16_t half_index) {
  return float(half_index) / float(NATIVE_RESOLUTION - 1);
}

static void dforge_streak_px(CRGB16* layer, float pos_norm, float last_norm, CRGB16 colour) {
  if (pos_norm < 0.0f) pos_norm = 0.0f;
  if (pos_norm > 1.0f) pos_norm = 1.0f;
  if (last_norm < 0.0f) last_norm = 0.0f;
  if (last_norm > 1.0f) last_norm = 1.0f;
  SQ15x16 p0 = SQ15x16(last_norm);
  SQ15x16 p1 = SQ15x16(pos_norm);
  SQ15x16 d = fabs_fixed(p1 - p0);
  SQ15x16 min_step = SQ15x16(1.0f / float(NATIVE_RESOLUTION - 1));
  if (d < min_step) d = min_step;
  draw_line(layer, p0, p1, colour, SQ15x16(1.0f));
}

void light_mode_dense_forge_chord(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const CRGBPalette16& pal =
      cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
  const uint16_t HALF = NATIVE_RESOLUTION / 2;
  const uint8_t bands = DFORGE_LATTICE_N;
  const uint8_t analysis_bins =
      sb_gdft_nyquist_safe_bin_hi(CONFIG.SAMPLE_RATE, CONFIG.NOTE_OFFSET);
  const uint8_t bins_per_band = (analysis_bins + bands - 1) / bands;

  const uint32_t prev_ms = fx.dense_last_ms;
  const uint32_t now_ms = millis();
  float dt = (prev_ms != 0) ? float(now_ms - prev_ms) * 0.001f : (1.0f / 120.0f);
  fx.dense_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;

  K1AudioSnapshot snap = k1_audio_snapshot_read();
  K1OnsetBeatEvent ev = k1_onset_beat_read();
  K1TempoEvent tempo = k1_tempo_read();

  const float novelty = dforge_clamp01(snap.novelty);
  const float energy = dforge_clamp01(snap.spectral_energy);
  const float conf = dforge_clamp01(tempo.confidence);
  const float conf_scale = 0.40f + 0.60f * conf;  // lattice coupling only — not inject
  const bool hard_gate = snap.silence;
  const bool presence_ok = dforge_presence_ok(snap);
  const float inject_scale =
      (presence_ok && !hard_gate) ? 1.0f : 0.0f;

#ifdef K1_ONSET_V2
  const float transient = dforge_clamp01(ev.transient_level);
#else
  const float transient = ev.onset ? dforge_clamp01(ev.onset_strength) : 0.0f;
#endif

  const float instant = 0.30f * novelty + 0.35f * energy + 0.35f * transient;
  fx.dense_activity_env += (instant - fx.dense_activity_env) * DFORGE_ACTIVITY_EMA;
  const float activity = dforge_clamp01(fx.dense_activity_env);

  if (prev_ms == 0) {
    for (uint8_t i = 0; i < bands; i++) {
      fx.dforge_lat_pos[i] = float(i + 1) / float(bands + 1);
      fx.dforge_lat_last[i] = fx.dforge_lat_pos[i];
    }
  }

  fx.dforge_carrier += dt * (1.2f + 7.0f * novelty + 3.0f * transient);

  float tau[DFORGE_LATTICE_N];
  for (uint8_t i = 0; i < bands; i++) {
    tau[i] = dforge_band_target(i, bands, bins_per_band, analysis_bins);
  }

  const float kappa = DFORGE_KAPPA0 * novelty * conf_scale * (0.35f + 0.65f * activity);

  for (uint8_t i = 0; i < bands; i++) {
    fx.dforge_lat_last[i] = fx.dforge_lat_pos[i];

    float force = DFORGE_SPRING_K * (tau[i] - fx.dforge_lat_pos[i]);
    force -= DFORGE_DAMPING * fx.dforge_lat_vel[i];
    force += DFORGE_IMPULSE * transient * (tau[i] - fx.dforge_lat_pos[i]);

    if (kappa > 0.001f) {
      float coupling = 0.0f;
      for (uint8_t j = 0; j < bands; j++) {
        if (j == i) continue;
        coupling += sinf(fx.dforge_lat_pos[j] - fx.dforge_lat_pos[i]);
      }
      force += kappa * coupling / float(bands - 1);
    }

    force *= DFORGE_OMEGA[i];
    fx.dforge_lat_vel[i] += force * dt;
    if (fx.dforge_lat_vel[i] > DFORGE_MAX_VEL)  fx.dforge_lat_vel[i] = DFORGE_MAX_VEL;
    if (fx.dforge_lat_vel[i] < -DFORGE_MAX_VEL) fx.dforge_lat_vel[i] = -DFORGE_MAX_VEL;

    fx.dforge_lat_pos[i] += fx.dforge_lat_vel[i] * dt;
    if (fx.dforge_lat_pos[i] < DFORGE_POS_EPS) {
      fx.dforge_lat_pos[i] = DFORGE_POS_EPS;
      fx.dforge_lat_vel[i] *= -0.35f;
    }
    if (fx.dforge_lat_pos[i] > DFORGE_POS_MAX) {
      fx.dforge_lat_pos[i] = DFORGE_POS_MAX;
      fx.dforge_lat_vel[i] *= -0.35f;
    }
  }

  const float frame = dt * 120.0f;
  const float mood = dforge_clamp01(float(rp->MOOD));
  const float nr_scale = float(NATIVE_RESOLUTION) / 128.0f;
  const float transport_drift =
      DFORGE_TRANSPORT_BASE *
      (DFORGE_TRANSPORT_FLOOR + DFORGE_TRANSPORT_SURGE * activity) *
      (0.85f + 0.30f * mood) *
      nr_scale *
      frame;

  // MOTION: transport previous frame every valid rendered frame.
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  if (!hard_gate) {
    const SQ15x16 transport_alpha =
        SQ15x16(presence_ok ? DFORGE_TRANSPORT_ALPHA : DFORGE_QUIET_ALPHA);
    draw_sprite(leds_16, leds_prev_buffer, NATIVE_RESOLUTION, NATIVE_RESOLUTION,
                transport_drift, transport_alpha);
  }

  const float centroid = chromagram_centroid_hue();
#ifdef K1_CHORD_HUE_V1
  // CHORD→HUE ANCHOR: pull the chromagram centroid toward the held chord root
  // on the same A-origin hue wheel (rootNote/12 and chromagram_centroid_hue
  // share origin and direction). Hue-only — brightness and motion untouched.
  float hue_base;
  {
    const uint8_t root = snap.chord.rootNote;
    const bool chord_ok = (snap.chord.type != K1ChordType::NONE);
    // 250 ms hold: a new root must persist before it takes the anchor (raw root
    // changes ~5.25/s on real material; held root measured ~0.83/s).
    if (chord_ok && root != fx.dforge_chord_held_root) {
      if (root == fx.dforge_chord_cand_root) {
        fx.dforge_chord_cand_ms += dt * 1000.0f;
        if (fx.dforge_chord_cand_ms >= 250.0f) {
          fx.dforge_chord_held_root = root;
          fx.dforge_chord_cand_ms = 0.0f;
        }
      } else {
        fx.dforge_chord_cand_root = root;
        fx.dforge_chord_cand_ms = 0.0f;
      }
    }
    // Confidence remapped above its 0.625 structural floor (flat chroma scores
    // 3/12 / 0.4 by construction) → blend depth capped at 0.6 so the centroid
    // always keeps a voice.
    float k = (snap.chord.confidence - 0.625f) / 0.375f;
    if (k < 0.0f) k = 0.0f;
    if (k > 1.0f) k = 1.0f;
    k *= chord_ok ? 0.6f : 0.0f;
    const float anchor = float(fx.dforge_chord_held_root) / 12.0f;
    // Shortest-arc pull of centroid toward the held anchor.
    float d = anchor - centroid;
    d -= floorf(d + 0.5f);  // wrap to [-0.5, 0.5)
    const float target = centroid + d * k;
    // 0.5 rev/s hue slew so harmony changes glide instead of snapping.
    float sd = target - fx.dforge_chord_hue;
    sd -= floorf(sd + 0.5f);
    const float max_step = 0.5f * dt;
    if (sd > max_step) sd = max_step;
    if (sd < -max_step) sd = -max_step;
    fx.dforge_chord_hue += sd;
    fx.dforge_chord_hue -= floorf(fx.dforge_chord_hue);
    hue_base = fx.dforge_chord_hue;
  }
#else
  const float hue_base = centroid;
#endif
  const float phase_b = tempo.phase01 * conf * 6.2831853f;

  // Moiré interference inject — spatial texture without advection.
  for (uint16_t k = 0; k < HALF; k++) {
    const float u = float(k) / float(HALF > 1 ? HALF - 1 : 1);
    const float moire =
        sinf(6.2831853f * (u * 2.17f + fx.dforge_carrier)) *
        sinf(6.2831853f * (u * 3.61f - phase_b));
    const float envelope = (0.35f + 0.65f * activity) * (0.5f + 0.5f * moire);
    float e = float(spectrogram_smooth[k < analysis_bins ? k : (analysis_bins > 0 ? analysis_bins - 1 : 0)]);
    if (!isfinite(e)) e = 0.0f;
    e = dforge_clamp01(e) * envelope * DFORGE_MOIRE_GAIN * inject_scale;
    if (e < DFORGE_FLOOR) continue;
    // PALETTE-CRUSH FIX (2026-06-11): spread widened 0.16 -> 0.30 so the inject
    // layer traverses enough of the gradient for palettes to keep their identity.
    const float hue = hue_base + u * 0.30f;
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(e));
    const uint16_t idx = HALF + k;
    leds_16[idx].r += col.r;
    leds_16[idx].g += col.g;
    leds_16[idx].b += col.b;
  }

  // Spring-lattice streak agents — differential slip (Whitney detune).
  for (uint8_t i = 0; i < bands; i++) {
    const float u_pos = fx.dforge_lat_pos[i];
    const float u_last = fx.dforge_lat_last[i];
    const float pos_norm = dforge_strip_norm(HALF + uint16_t(u_pos * float(HALF - 1)));
    const float last_norm = dforge_strip_norm(HALF + uint16_t(u_last * float(HALF - 1)));
    const float speed = fabsf(fx.dforge_lat_vel[i]);
    float b = (0.25f + 0.55f * tau[i] + 0.35f * speed) * DFORGE_STREAK_GAIN * inject_scale;
    if (b < DFORGE_FLOOR) continue;
    // PALETTE-CRUSH FIX (2026-06-11): band spread widened 0.22 -> 0.35.
    const float hue = hue_base + float(i) / float(bands) * 0.35f;
    CRGB16 col = palette_manual_colour(pal, SQ15x16(hue), SQ15x16(b));
    dforge_streak_px(leds_16, pos_norm, last_norm, col);
  }

  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  finalize_additive_frame(leds_16, leds_prev_buffer, true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
