#include "lightshow_modes.h"
#include "sb_audio_snapshot.h"
#include "sb_tempo.h"
#include <math.h>

// ============================================================================
// light_mode_snapwave — tonal chroma phase-interference oscillator.
// ----------------------------------------------------------------------------
// Snapwave's musical hook is not a beat flash: active pitch classes drive
// detuned sine phases, the summed motion snaps through tanh(), and peak energy
// controls reach/trail length. Beat phase only adds a small confident nudge.
// ============================================================================

static const float SNAP_BASE_OMEGA      = 0.001f;  // rad/ms, production Snapwave DNA
static const float SNAP_PHASE_SPREAD    = 0.5f;
static const float SNAP_NOTE_THRESHOLD  = 0.10f;
static const float SNAP_TANH_SCALE      = 2.0f;
static const float SNAP_AMPLITUDE_SCALE = 0.97f;  // peak swing reaches the strip edge (amp clamps at +-1)
static const float SNAP_DEADZONE        = 0.05f;
static const float SNAP_FADE_REDUCTION  = 0.10f;
static const float SNAP_ATTACK_TAU      = 0.05f;
static const float SNAP_RELEASE_TAU     = 0.28f;
static const float SNAP_AMP_TAU         = 0.08f;
static const float SNAP_BLOOM_RADIUS    = 5.0f;
static const float SNAP_BLOOM_FALLOFF   = 0.085f;
static const float SNAP_BRIGHT_FLOOR    = 0.012f;
static const float SNAP_PALETTE_SPREAD  = 0.30f;

static inline float snap_clamp01(float v) {
  if (!isfinite(v) || v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

static inline float snap_asym_follow(float current, float target, float dt, float attack_tau, float release_tau) {
  const float tau = (target > current) ? attack_tau : release_tau;
  float a = 1.0f - expf(-dt / tau);
  if (!isfinite(a) || a < 0.0f) a = 0.0f;
  if (a > 1.0f) a = 1.0f;
  return current + (target - current) * a;
}

void light_mode_snapwave(CRGB16* leds_prev_buffer, ChannelEffectState& fx) {
  const RenderParams* rp = active_render_params();
  const bool render_secondary = vp_render_secondary_channel;
  const uint16_t HALF = NATIVE_RESOLUTION / 2;

  const uint32_t now_ms = millis();
  float dt = (fx.snap_last_ms != 0) ? float(now_ms - fx.snap_last_ms) * 0.001f : (1.0f / 120.0f);
  fx.snap_last_ms = now_ms;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f)  dt = 0.05f;

  SBAudioSnapshot snap = sb_audio_snapshot_read();
  SBTempoEvent tempo = sb_tempo_read();

  const float peak = snap_clamp01(snap.peak_scaled);
  const float beat_strength = snap_clamp01(tempo.beat_strength);
  const float confidence = snap_clamp01(tempo.confidence);

  fx.snap_peak_env = snap_asym_follow(fx.snap_peak_env, peak, dt, SNAP_ATTACK_TAU, SNAP_RELEASE_TAU);

  float chroma_sum = 0.0f;
  float chroma_peak = 0.0f;
  float osc = 0.0f;
  const float t = float(now_ms) * SNAP_BASE_OMEGA;
  for (uint8_t i = 0; i < 12; i++) {
    float c = float(chromagram_smooth[i]);
    c = snap_clamp01(c);
    chroma_sum += c;
    if (c > chroma_peak) chroma_peak = c;
    if (c > SNAP_NOTE_THRESHOLD) {
      osc += c * sinf(t * (1.0f + float(i) * SNAP_PHASE_SPREAD));
    }
  }

  const float snap_scale = SNAP_TANH_SCALE + beat_strength;
  osc = tanhf(osc * snap_scale);

  float amp = osc * fx.snap_peak_env * SNAP_AMPLITUDE_SCALE;
  if (fx.snap_peak_env < SNAP_DEADZONE) amp = 0.0f;
  if (confidence > 0.5f) {
    amp *= (1.0f + 0.30f * beat_strength);
    amp += sinf(tempo.phase01 * 6.2831853f) * 0.10f * confidence;
  }
  if (amp > 1.0f) amp = 1.0f;
  if (amp < -1.0f) amp = -1.0f;

  fx.snap_amp_smooth = snap_asym_follow(fx.snap_amp_smooth, amp, dt, SNAP_AMP_TAU, SNAP_AMP_TAU);

  // Hold the pre-mirror history and fade dynamically: loud = shorter, punchier trail.
  memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16) * NATIVE_RESOLUTION);
  float fade_f = 1.0f - SNAP_FADE_REDUCTION * fx.snap_peak_env;
  if (fade_f < 0.86f) fade_f = 0.86f;
  if (fade_f > 0.965f) fade_f = 0.965f;
  const SQ15x16 fade = SQ15x16(fade_f);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= fade;
    leds_16[i].g *= fade;
    leds_16[i].b *= fade;
  }

  for (uint16_t i = 0; i < HALF; i++) {
    leds_16[i].r = 0;
    leds_16[i].g = 0;
    leds_16[i].b = 0;
  }

  const float pos = float(HALF) + fx.snap_amp_smooth * float(HALF - 1);
  float brightness = 0.18f + 0.52f * chroma_peak + 0.26f * fx.snap_peak_env + 0.20f * beat_strength;
  if (chroma_sum <= 0.001f) brightness *= 0.35f;
  brightness = snap_clamp01(brightness);

  const float snap_colour_offset = snap_clamp01(fabsf(fx.snap_amp_smooth)) * SNAP_PALETTE_SPREAD;
  const CRGB16 col = effect_particle_colour(rp, render_secondary, snap_colour_offset, SQ15x16(brightness));
  const int centre = int(pos + 0.5f);
  const int reach = int(SNAP_BLOOM_RADIUS + 0.5f);
  for (int d = -reach; d <= reach; d++) {
    const int idx = centre + d;
    if (idx < int(HALF) || idx >= int(NATIVE_RESOLUTION)) continue;
    const float w = expf(-float(d * d) * SNAP_BLOOM_FALLOFF) * brightness;
    if (w < SNAP_BRIGHT_FLOOR) continue;
    const SQ15x16 weight = SQ15x16(w);
    leds_16[idx].r += col.r * weight;
    leds_16[idx].g += col.g * weight;
    leds_16[idx].b += col.b * weight;
  }

  finalize_additive_frame(leds_16, leds_prev_buffer, true);
  if (rp->MIRROR_ENABLED) {
    mirror_image_downwards(leds_16);
  }
}
