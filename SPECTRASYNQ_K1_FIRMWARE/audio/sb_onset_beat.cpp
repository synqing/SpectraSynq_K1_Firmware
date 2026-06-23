#include "sb_onset_beat.h"

#include <Arduino.h>
#include <math.h>

static portMUX_TYPE sb_onset_mux = portMUX_INITIALIZER_UNLOCKED;
static SBOnsetBeatEvent sb_onset_event = {};

#ifdef SB_ONSET_V2
// ============================================================================
// SB_ONSET_V2 — donor-shaped (Lightwave OnsetDetector) front-end over the fork's
// per-note spectrogram[80]. Log-spectral flux + median-adaptive threshold +
// causal peak-pick + independent per-band kick/snare/hihat triggers.
//
// INVARIANT (carried verbatim from the donor): the activity/warmup gate is
// OUTPUT-PERMISSION-ONLY. Detector statistics (flux median ring, per-band EMA,
// envelope ring) ALWAYS track real flux. The gate only suppresses the EMITTED
// event/trigger — it never injects zeros, never scales flux, never rewrites the
// baseline. This is the property the legacy dual-EMA path violated.
//
// Rate: AP/onset frame rate = 12800/96 = 133.333 Hz (NOT the 44.4 Hz tempo
// rate). The detector runs every AP frame; dt ~= 7.5 ms. Donor params were at
// 125 Hz; constants below are re-derived for 133.333 Hz (see each comment).
//
// Bin->band mapping uses the runtime target table:
// bin i == notes[i + CONFIG.NOTE_OFFSET] (constants.h). The snapshot producer
// reports nyquist_safe_bin_hi, and high-band ranges below are clamped before flux
// is computed; at the
// default 12800 Hz / NOTE_OFFSET=12 this excludes bins 71..79.
//   transient (full musical): [1, 76)  skip sub-rumble; Nyquist-clamped
//   kick  (bass)            : [1, 25)  kick fundamental/body
//   snare (mid)             : [25, 50) snare body
//   hihat (high)            : [70, 80) hat/cymbal; Nyquist-clamped
// ============================================================================

namespace {

constexpr uint8_t SBV2_BINS = SB_ONSET_SPECTRUM_BINS;  // 80

// --- band bin ranges [lo, hi) ---
constexpr uint8_t SBV2_TRANS_LO = 1,  SBV2_TRANS_HI = 76;
constexpr uint8_t SBV2_KICK_LO  = 1,  SBV2_KICK_HI  = 25;
constexpr uint8_t SBV2_SNARE_LO = 25, SBV2_SNARE_HI = 50;
constexpr uint8_t SBV2_HIHAT_LO = 70, SBV2_HIHAT_HI = 80;

// --- full-band median-adaptive threshold (Dixon 2006) ---
// Donor: 13-frame median @125Hz (=104 ms). At 133.33 Hz, 104 ms = 13.9 -> 14.
constexpr uint8_t SBV2_FLUX_RING   = 16;   // donor FLUX_RING_SIZE
constexpr uint8_t SBV2_MEDIAN_WIN  = 14;   // 104 ms @ 133.33 Hz
// Threshold scales relative to median flux. spectrogram[] is in [0,1], so the
// per-bin log magnitudes are <= 0; the raw donor offset of 1.0 log-unit is far
// too large for this normalised, ~75-bin flux. Calibrated data-driven (see the
// host metrics report): mult 1.6, offset 0.05, floor 0.02 yields P~R balance
// without flooding on dense passages.
constexpr float   SBV2_THRESH_MUL  = 1.6f;
constexpr float   SBV2_THRESH_OFF  = 0.05f;
constexpr float   SBV2_THRESH_FLOOR= 0.02f;

// --- causal peak-pick ---
// Donor preMax=4 / peakWait=4 frames @125Hz (=32 ms). At 133.33 Hz, 32 ms = 4.3
// -> 4 (30 ms). Transient refractory = peakWait (NOT the legacy 240 ms).
constexpr uint8_t SBV2_ENV_RING    = 16;
constexpr uint8_t SBV2_PRE_MAX     = 4;    // ~30 ms
constexpr uint8_t SBV2_PEAK_WAIT   = 4;    // ~30 ms refractory

// --- per-band trigger params ---
// Refractory (frames): donor kick 6/48ms, snare 5/40ms, hihat 3/24ms @125Hz.
// At 133.33 Hz: 48ms->6.4->6, 40ms->5.3->5, 24ms->3.2->3 (time-equivalent).
constexpr uint8_t SBV2_KICK_REFR   = 6;    // 45 ms
constexpr uint8_t SBV2_SNARE_REFR  = 5;    // 37.5 ms
constexpr uint8_t SBV2_HIHAT_REFR  = 3;    // 22.5 ms
// EMA alpha (tau->alpha re-derivation). Donor alphas at 125 Hz (dt=8 ms) give
// tau = dt*(1-a)/a: kick 525 ms, snare 792 ms, hihat 1592 ms. At 133.33 Hz
// (dt=7.5 ms): a = dt/(tau+dt) -> kick 0.0141, snare 0.0094, hihat 0.0047.
constexpr float   SBV2_KICK_ALPHA  = 0.0141f;
constexpr float   SBV2_SNARE_ALPHA = 0.0094f;
constexpr float   SBV2_HIHAT_ALPHA = 0.0047f;
// Threshold-K (band fires when prevFlux > mean*(1+K)). Donor 0.8/1.0/1.2.
constexpr float   SBV2_KICK_K      = 0.8f;
constexpr float   SBV2_SNARE_K     = 1.0f;
constexpr float   SBV2_HIHAT_K     = 1.2f;

// --- output gate (permission only) ---
// Warmup: suppress emission for the first frames while the median ring fills.
// Donor warmup is VU-AGC-driven (1000f). Here the spectrogram is already
// AGC-settled upstream, so warmup only needs to cover the median window.
constexpr uint32_t SBV2_WARMUP_FR  = 14;
// Activity gate: emission requires the per-frame spectral ENERGY LEVEL (a slow,
// non-flux signal — audio.spectral_energy in [0,1]) to exceed a small floor.
// CRITICAL: the gate must key on a LEVEL, never on instantaneous flux. Flux is
// high only on the attack frame and ~0 on the immediately-following frame — but
// the causal band trigger fires on the PREVIOUS frame's flux, i.e. on that
// following frame. Gating on instantaneous flux would suppress every band hit.
// This floor is a no-emit gate only; it never touches detector statistics.
constexpr float   SBV2_ACT_FLOOR   = 0.004f;
// Open-quiet taped-mic input can report silence=false while carrying too little
// musical energy for trustworthy onset emission. Keep this as output permission
// only; detector statistics still track real flux below.
constexpr float   SBV2_QUIET_SPECTRAL_FLOOR = 0.08f;
constexpr float   SBV2_QUIET_NOVELTY_FLOOR  = 0.08f;

constexpr float   SBV2_EPS         = 1e-6f;
constexpr float   SBV2_LEVEL_DECAY = 0.86f;  // ~per-frame held-level fade for trails

struct BandState {
  float    flux_mean        = 0.0f;
  float    prev_flux        = 0.0f;
  float    prev2_flux       = 0.0f;
  uint32_t last_trigger_fr  = 0;
};

struct DetectorV2 {
  float    prev_spec[SBV2_BINS] = {};
  bool     has_prev            = false;

  float    flux_ring[SBV2_FLUX_RING] = {};
  uint8_t  flux_widx          = 0;
  uint8_t  flux_count         = 0;

  float    env_ring[SBV2_ENV_RING] = {};
  uint8_t  env_widx           = 0;
  uint32_t last_event_fr      = 0;
  uint32_t frame_count        = 0;

  BandState bass, mid, high;

  float    trans_level = 0.0f, kick_level = 0.0f, snare_level = 0.0f, hihat_level = 0.0f;
  uint32_t trans_id = 0, kick_id = 0, snare_id = 0, hihat_id = 0;
};

DetectorV2 g_v2;

float sbv2_band_flux(const float* spec, const float* prev, uint8_t lo, uint8_t hi) {
  // Log-spectral flux: sum_k max(0, log m[t,k] - log m[t-1,k]) over [lo,hi).
  float flux = 0.0f;
  for (uint8_t k = lo; k < hi; ++k) {
    float diff = logf(fmaxf(SBV2_EPS, spec[k])) - logf(fmaxf(SBV2_EPS, prev[k]));
    if (diff > 0.0f) flux += diff;
  }
  return flux;
}

float sbv2_band_normalise(float flux, uint8_t lo, uint8_t hi) {
  if (hi <= lo) {
    return 0.0f;
  }
  return flux / float(hi - lo);
}

uint8_t sbv2_clamp_hi_to_snapshot_nyquist(uint8_t lo, uint8_t hi, uint8_t safe_hi) {
  if (safe_hi == 0 || safe_hi > SBV2_BINS) {
    safe_hi = SBV2_BINS;
  }
  if (safe_hi < lo) {
    return lo;
  }
  return safe_hi < hi ? safe_hi : hi;
}

float sbv2_median(const float* ring, uint8_t n) {
  if (n == 0) return 0.0f;
  float tmp[SBV2_FLUX_RING];
  for (uint8_t i = 0; i < n; ++i) tmp[i] = ring[i];
  for (uint8_t i = 1; i < n; ++i) {  // insertion sort (n<=16)
    float key = tmp[i];
    int j = int(i) - 1;
    while (j >= 0 && tmp[j] > key) { tmp[j + 1] = tmp[j]; --j; }
    tmp[j + 1] = key;
  }
  return (n & 1) ? tmp[n / 2] : 0.5f * (tmp[n / 2 - 1] + tmp[n / 2]);
}

// Adaptive threshold. ALWAYS pushes real flux into the ring (gate-independent).
float sbv2_threshold_env(float flux) {
  g_v2.flux_ring[g_v2.flux_widx] = flux;
  g_v2.flux_widx = (g_v2.flux_widx + 1) % SBV2_FLUX_RING;
  if (g_v2.flux_count < SBV2_FLUX_RING) ++g_v2.flux_count;

  uint8_t win = (g_v2.flux_count < SBV2_MEDIAN_WIN) ? g_v2.flux_count : SBV2_MEDIAN_WIN;
  float median = sbv2_median(g_v2.flux_ring, win);
  float th = median * SBV2_THRESH_MUL + SBV2_THRESH_OFF;
  if (th < SBV2_THRESH_FLOOR) th = SBV2_THRESH_FLOOR;
  float env = flux - th;
  return (env > 0.0f) ? env : 0.0f;
}

// Causal local-max peak-pick. ALWAYS updates env ring; emits only when allowed.
float sbv2_peak_pick(float env, bool emit) {
  uint8_t cand = g_v2.env_widx;
  g_v2.env_ring[cand] = env;
  g_v2.env_widx = (g_v2.env_widx + 1) % SBV2_ENV_RING;

  if (!emit) return 0.0f;
  if (env <= 0.0f) return 0.0f;
  if (g_v2.frame_count < SBV2_PRE_MAX) return 0.0f;
  for (uint8_t i = 1; i <= SBV2_PRE_MAX; ++i) {
    int idx = (int(cand) - i + SBV2_ENV_RING) % SBV2_ENV_RING;
    if (g_v2.env_ring[idx] >= env) return 0.0f;
  }
  if (g_v2.frame_count - g_v2.last_event_fr < SBV2_PEAK_WAIT) return 0.0f;
  g_v2.last_event_fr = g_v2.frame_count;
  return env;
}

// Per-band trigger. ALWAYS updates band stats on real flux; emits only when
// allowed. Returns the TRIGGERING flux magnitude (prev_flux, i.e. the attack
// frame's flux) on a fire, else 0 — so the reported strength matches the frame
// that actually peaked, not the (near-zero) post-attack frame the causal
// local-max test fires on. 0 == no fire.
float sbv2_band_trigger(BandState& st, float flux, float k, float alpha,
                        uint8_t refr, bool emit) {
  st.flux_mean += alpha * (flux - st.flux_mean);
  float th = st.flux_mean * (1.0f + k);
  bool local_max = (st.prev_flux > st.prev2_flux) && (st.prev_flux > flux);
  bool above     = (st.prev_flux > th);
  bool refr_open = (g_v2.frame_count - st.last_trigger_fr) >= uint32_t(refr);
  float fired_flux = st.prev_flux;
  st.prev2_flux = st.prev_flux;
  st.prev_flux  = flux;
  if (!emit) return 0.0f;
  if (local_max && above && refr_open) {
    st.last_trigger_fr = g_v2.frame_count;
    return fired_flux;
  }
  return 0.0f;
}

void sbv2_reset() {
  g_v2 = DetectorV2{};
}

// Run the V2 detector for one frame and write the additive channels onto `event`.
// Also drives the LEGACY onset/bass_onset/onset_strength from the V2 detector
// (the ON-02 recovery): the V2 transient -> legacy onset, V2 kick -> legacy
// bass_onset. Beat/beat_phase/beat_confidence are NOT touched here (sb_tempo /
// the legacy IOI path own those). Returns true if a fresh transient fired.
bool sbv2_run(const SBAudioSnapshot& audio, SBOnsetBeatEvent& event) {
  const float* spec = audio.spectrum;

  // Silence / first frame: force a clean re-prime on the NEXT real frame (donor
  // m_hasPrevMag=false semantics) rather than comparing against a stale/zero
  // spectrum. Crucially this injects NO zeros into the median ring or band EMA
  // (gate-permission-only invariant) AND leaves prev_spec untouched so a brief
  // gate does not fabricate a giant post-gate flux spike against zeros.
  if (!g_v2.has_prev || audio.silence) {
    if (audio.silence) {
      g_v2.has_prev = false;          // next real frame re-primes, no flux
    } else {
      for (uint8_t i = 0; i < SBV2_BINS; ++i) g_v2.prev_spec[i] = spec[i];
      g_v2.has_prev = true;
    }
    g_v2.frame_count++;
    // decay held levels so trails fade during silence
    g_v2.trans_level *= SBV2_LEVEL_DECAY;
    g_v2.kick_level  *= SBV2_LEVEL_DECAY;
    g_v2.snare_level *= SBV2_LEVEL_DECAY;
    g_v2.hihat_level *= SBV2_LEVEL_DECAY;
    event.transient = event.kick = event.snare = event.hihat = false;
    event.transient_strength = event.kick_strength = event.snare_strength = event.hihat_strength = 0.0f;
    event.transient_level = g_v2.trans_level;
    event.kick_level  = g_v2.kick_level;
    event.snare_level = g_v2.snare_level;
    event.hihat_level = g_v2.hihat_level;
    event.transient_event_id = g_v2.trans_id;
    event.kick_event_id  = g_v2.kick_id;
    event.snare_event_id = g_v2.snare_id;
    event.hihat_event_id = g_v2.hihat_id;
    return false;
  }

  uint8_t trans_hi = sbv2_clamp_hi_to_snapshot_nyquist(SBV2_TRANS_LO, SBV2_TRANS_HI,
                                                       audio.nyquist_safe_bin_hi);
  uint8_t hihat_hi = sbv2_clamp_hi_to_snapshot_nyquist(SBV2_HIHAT_LO, SBV2_HIHAT_HI,
                                                       audio.nyquist_safe_bin_hi);

  float full_flux  = sbv2_band_flux(spec, g_v2.prev_spec, SBV2_TRANS_LO, trans_hi);
  float kick_flux  = sbv2_band_flux(spec, g_v2.prev_spec, SBV2_KICK_LO,  SBV2_KICK_HI);
  float snare_flux = sbv2_band_flux(spec, g_v2.prev_spec, SBV2_SNARE_LO, SBV2_SNARE_HI);
  float hihat_flux = sbv2_band_flux(spec, g_v2.prev_spec, SBV2_HIHAT_LO, hihat_hi);

  // normalise band flux by bin count so the EMA threshold is bin-count-agnostic
  float kick_n  = sbv2_band_normalise(kick_flux,  SBV2_KICK_LO,  SBV2_KICK_HI);
  float snare_n = sbv2_band_normalise(snare_flux, SBV2_SNARE_LO, SBV2_SNARE_HI);
  float hihat_n = sbv2_band_normalise(hihat_flux, SBV2_HIHAT_LO, hihat_hi);

  // OUTPUT-PERMISSION-ONLY gate: warmup + activity floor. Decides emission only;
  // stats updates below run regardless. Activity keys on the spectral ENERGY
  // LEVEL (slow), NOT flux (which is ~0 on the post-attack frame the causal band
  // trigger fires on). See SBV2_ACT_FLOOR comment.
  bool warmup   = g_v2.frame_count < SBV2_WARMUP_FR;
  bool open_quiet = audio.spectral_energy < SBV2_QUIET_SPECTRAL_FLOOR &&
                    audio.novelty < SBV2_QUIET_NOVELTY_FLOOR;
  bool inactive = audio.spectral_energy < SBV2_ACT_FLOOR || open_quiet;
  bool emit     = !warmup && !inactive;

  // Full-band onset envelope + peak-pick (stats always real).
  float env       = sbv2_threshold_env(full_flux);
  float onset_env = sbv2_peak_pick(env, emit);
  bool  fired     = onset_env > 0.0f;

  // Per-band triggers (stats always real). Returned value = triggering flux (the
  // attack-frame magnitude) on a fire, 0 otherwise.
  float kick_flx_fire  = sbv2_band_trigger(g_v2.bass, kick_n,  SBV2_KICK_K,  SBV2_KICK_ALPHA,  SBV2_KICK_REFR,  emit);
  float snare_flx_fire = sbv2_band_trigger(g_v2.mid,  snare_n, SBV2_SNARE_K, SBV2_SNARE_ALPHA, SBV2_SNARE_REFR, emit);
  float hihat_flx_fire = sbv2_band_trigger(g_v2.high, hihat_n, SBV2_HIHAT_K, SBV2_HIHAT_ALPHA, SBV2_HIHAT_REFR, emit);
  bool kick_fired  = kick_flx_fire  > 0.0f;
  bool snare_fired = snare_flx_fire > 0.0f;
  bool hihat_fired = hihat_flx_fire > 0.0f;

  // Strengths: thresholded envelope (full) / triggering band flux, clamped [0,1].
  float trans_str = onset_env > 1.0f ? 1.0f : onset_env;
  float kick_str  = kick_fired  ? (kick_flx_fire  > 1.0f ? 1.0f : kick_flx_fire)  : 0.0f;
  float snare_str = snare_fired ? (snare_flx_fire > 1.0f ? 1.0f : snare_flx_fire) : 0.0f;
  float hihat_str = hihat_fired ? (hihat_flx_fire > 1.0f ? 1.0f : hihat_flx_fire) : 0.0f;

  // Held levels (decay + set-on-fire) for motion-memory trails.
  g_v2.trans_level *= SBV2_LEVEL_DECAY;
  g_v2.kick_level  *= SBV2_LEVEL_DECAY;
  g_v2.snare_level *= SBV2_LEVEL_DECAY;
  g_v2.hihat_level *= SBV2_LEVEL_DECAY;
  if (fired       && trans_str > g_v2.trans_level) g_v2.trans_level = trans_str;
  if (kick_fired  && kick_str  > g_v2.kick_level)  g_v2.kick_level  = kick_str;
  if (snare_fired && snare_str > g_v2.snare_level) g_v2.snare_level = snare_str;
  if (hihat_fired && hihat_str > g_v2.hihat_level) g_v2.hihat_level = hihat_str;

  if (fired)       g_v2.trans_id++;
  if (kick_fired)  g_v2.kick_id++;
  if (snare_fired) g_v2.snare_id++;
  if (hihat_fired) g_v2.hihat_id++;

  event.transient = fired;
  event.kick      = kick_fired;
  event.snare     = snare_fired;
  event.hihat     = hihat_fired;
  event.transient_strength = trans_str;
  event.kick_strength      = kick_str;
  event.snare_strength     = snare_str;
  event.hihat_strength     = hihat_str;
  event.transient_level = g_v2.trans_level;
  event.kick_level  = g_v2.kick_level;
  event.snare_level = g_v2.snare_level;
  event.hihat_level = g_v2.hihat_level;
  event.transient_event_id = g_v2.trans_id;
  event.kick_event_id  = g_v2.kick_id;
  event.snare_event_id = g_v2.snare_id;
  event.hihat_event_id = g_v2.hihat_id;

  // store spectrum for next frame's flux (gate-independent)
  for (uint8_t i = 0; i < SBV2_BINS; ++i) g_v2.prev_spec[i] = spec[i];
  g_v2.frame_count++;
  return fired;
}

}  // namespace
#endif  // SB_ONSET_V2

static uint32_t sb_onset_last_ms = 0;
static uint32_t sb_last_accept_ms = 0;
static uint32_t sb_last_interval_ms = 0;
static uint32_t sb_interval_estimate_ms = 0;
static uint8_t sb_stable_intervals = 0;
static float sb_novelty_fast = 0.0f;
static float sb_novelty_slow = 0.0f;
static float sb_low_fast = 0.0f;
static float sb_low_slow = 0.0f;
static float sb_peak_fast = 0.0f;
static float sb_peak_slow = 0.0f;
static float sb_prev_novelty = 0.0f;
static float sb_prev_low_energy = 0.0f;
static float sb_prev_peak = 0.0f;
static bool sb_onset_primed = false;
static const uint32_t SB_ONSET_EVENT_WINDOW_MS = 80UL;
// Legacy full-band refractory — unused on the V2 path (V2 owns per-band/peak refractory).
[[maybe_unused]] static const uint32_t SB_ONSET_REFRACTORY_MS = 240UL;
static const uint32_t SB_BEAT_INTERVAL_MIN_MS = 300UL;
static const uint32_t SB_BEAT_INTERVAL_MAX_MS = 1000UL;
static const uint8_t SB_INTERVAL_TOLERANCE_DIVISOR = 4U;
static const uint8_t SB_STABLE_INTERVAL_MAX = 4U;

static float sb_ob_clamp(float value, float low, float high) {
  if (!isfinite(value)) {
    return low;
  }
  if (value < low) {
    return low;
  }
  if (value > high) {
    return high;
  }
  return value;
}

static float sb_ob_alpha(uint32_t dt_ms, float tau_ms) {
  if (tau_ms <= 0.0f) {
    return 1.0f;
  }
  float dt = float(dt_ms);
  return sb_ob_clamp(dt / (tau_ms + dt), 0.0f, 1.0f);
}

static void sb_publish_event(const SBOnsetBeatEvent& event) {
  portENTER_CRITICAL(&sb_onset_mux);
  sb_onset_event = event;
  portEXIT_CRITICAL(&sb_onset_mux);
}

static uint32_t sb_event_age(uint32_t now_ms, uint32_t event_ms) {
  if (event_ms == 0 || now_ms < event_ms) {
    return UINT32_MAX;
  }
  return now_ms - event_ms;
}

static void sb_decay_beat_lock() {
  if (sb_stable_intervals > 0) {
    sb_stable_intervals--;
  }
  if (sb_stable_intervals == 0) {
    sb_interval_estimate_ms = 0;
    sb_last_interval_ms = 0;
  }
}

static bool sb_interval_close(uint32_t interval_ms, uint32_t reference_ms) {
  if (interval_ms == 0 || reference_ms == 0) {
    return false;
  }
  uint32_t bigger = interval_ms > reference_ms ? interval_ms : reference_ms;
  uint32_t smaller = interval_ms > reference_ms ? reference_ms : interval_ms;
  return (bigger - smaller) <= (bigger / SB_INTERVAL_TOLERANCE_DIVISOR);
}

static void sb_note_accepted_interval(uint32_t interval_ms) {
  if (interval_ms < SB_BEAT_INTERVAL_MIN_MS || interval_ms > SB_BEAT_INTERVAL_MAX_MS) {
    sb_decay_beat_lock();
    sb_stable_intervals = 0;
    return;
  }

  if (sb_interval_estimate_ms == 0) {
    sb_interval_estimate_ms = interval_ms;
    sb_last_interval_ms = interval_ms;
    return;
  }

  bool close_interval = sb_interval_close(interval_ms, sb_interval_estimate_ms);
  bool half_time_alias = sb_interval_close(interval_ms * 2UL, sb_interval_estimate_ms);
  bool double_time_alias = sb_interval_close(interval_ms, sb_interval_estimate_ms * 2UL);
  if (close_interval && !half_time_alias && !double_time_alias) {
    sb_interval_estimate_ms = (sb_interval_estimate_ms * 3UL + interval_ms) / 4UL;
    sb_last_interval_ms = interval_ms;
    if (sb_stable_intervals < SB_STABLE_INTERVAL_MAX) {
      sb_stable_intervals++;
    }
  } else {
    sb_decay_beat_lock();
    sb_stable_intervals = 0;
    sb_interval_estimate_ms = interval_ms;
    sb_last_interval_ms = interval_ms;
  }
}

void sb_onset_beat_reset() {
  sb_onset_last_ms = 0;
  sb_last_accept_ms = 0;
  sb_last_interval_ms = 0;
  sb_interval_estimate_ms = 0;
  sb_stable_intervals = 0;
  sb_novelty_fast = 0.0f;
  sb_novelty_slow = 0.0f;
  sb_low_fast = 0.0f;
  sb_low_slow = 0.0f;
  sb_peak_fast = 0.0f;
  sb_peak_slow = 0.0f;
  sb_prev_novelty = 0.0f;
  sb_prev_low_energy = 0.0f;
  sb_prev_peak = 0.0f;
  sb_onset_primed = false;
#ifdef SB_ONSET_V2
  sbv2_reset();
#endif
  SBOnsetBeatEvent empty = {};
  sb_publish_event(empty);
}

void sb_onset_beat_update(const SBAudioSnapshot& audio) {
  uint32_t now_ms = audio.frame_ms;
  uint32_t dt_ms = (sb_onset_last_ms == 0 || now_ms < sb_onset_last_ms) ? 0 : now_ms - sb_onset_last_ms;
  sb_onset_last_ms = now_ms;

  SBOnsetBeatEvent event = sb_onset_beat_read();
  event.event_age_ms = sb_event_age(now_ms, event.event_ms);
  bool event_active = event.event_age_ms <= SB_ONSET_EVENT_WINDOW_MS;
  if (!event_active) {
    event.onset = false;
    event.bass_onset = false;
    event.beat = false;
    event.onset_strength = 0.0f;
    event.bass_onset_strength = 0.0f;
  }

  float novelty = sb_ob_clamp(audio.novelty, 0.0f, 1.0f);
  float low_energy = sb_ob_clamp(audio.low_energy, 0.0f, 1.0f);
  float peak_scaled = sb_ob_clamp(audio.peak_scaled, 0.0f, 1.0f);

  if (!sb_onset_primed) {
    sb_novelty_fast = novelty;
    sb_novelty_slow = novelty;
    sb_low_fast = low_energy;
    sb_low_slow = low_energy;
    sb_peak_fast = peak_scaled;
    sb_peak_slow = peak_scaled;
    sb_prev_novelty = novelty;
    sb_prev_low_energy = low_energy;
    sb_prev_peak = peak_scaled;
    sb_onset_primed = true;
  }

  float novelty_attack = sb_ob_clamp(novelty - sb_novelty_slow, 0.0f, 1.0f);
  float low_attack = sb_ob_clamp(low_energy - sb_low_slow, 0.0f, 1.0f);
  float peak_attack = sb_ob_clamp(peak_scaled - sb_peak_slow, 0.0f, 1.0f);
  float novelty_rise = novelty - sb_prev_novelty;
  float low_rise = low_energy - sb_prev_low_energy;
  float peak_rise = peak_scaled - sb_prev_peak;

  float fast_alpha = sb_ob_alpha(dt_ms, 80.0f);
  float slow_alpha = sb_ob_alpha(dt_ms, 1200.0f);
  sb_novelty_fast += (novelty - sb_novelty_fast) * fast_alpha;
  sb_novelty_slow += (novelty - sb_novelty_slow) * slow_alpha;
  sb_low_fast += (low_energy - sb_low_fast) * fast_alpha;
  sb_low_slow += (low_energy - sb_low_slow) * slow_alpha;
  sb_peak_fast += (peak_scaled - sb_peak_fast) * fast_alpha;
  sb_peak_slow += (peak_scaled - sb_peak_slow) * slow_alpha;

  if (audio.silence) {
    sb_last_accept_ms = 0;
    sb_decay_beat_lock();
    sb_stable_intervals = 0;
    event.event_age_ms = sb_event_age(now_ms, event.event_ms);
    event.onset = false;
    event.bass_onset = false;
    event.beat = false;
    event.onset_strength = 0.0f;
    event.bass_onset_strength = 0.0f;
    event.beat_phase = 0.0f;
    event.beat_confidence = 0.0f;
#ifdef SB_ONSET_V2
    // Silence is inert for V2 too: re-primes prev-spectrum, decays held levels,
    // emits no channel events. Detector stats are NOT zero-injected.
    (void)sbv2_run(audio, event);
#endif
    sb_prev_novelty = novelty;
    sb_prev_low_energy = low_energy;
    sb_prev_peak = peak_scaled;
    sb_publish_event(event);
    return;
  }

#ifdef SB_ONSET_V2
  // --- V2 onset front-end drives onset/bass_onset + the accept decision. ---
  // The donor-shaped detector (log-flux + median-adaptive threshold + per-band
  // triggers over spectrogram[80]) supersedes the legacy scalar-EMA candidate
  // gates. Legacy onset == V2 transient; legacy bass_onset == V2 kick. The IOI /
  // beat-lock machinery below is UNCHANGED and now feeds on V2 onset times.
  bool v2_transient = sbv2_run(audio, event);  // also writes the additive channels
  float onset_strength = event.transient_strength;
  float bass_strength  = event.kick_strength;
  bool novelty_candidate = v2_transient;          // legacy `onset` source
  bool bass_candidate    = event.kick;            // legacy `bass_onset` source
  bool refractory_open = true;                    // V2 owns its own refractory
  bool accepted = v2_transient || event.kick;     // any percussive hit advances the IOI clock
  (void)novelty_attack; (void)low_attack; (void)peak_attack;
  (void)novelty_rise; (void)low_rise; (void)peak_rise;

  if (accepted) {
    uint32_t interval_ms = (sb_last_accept_ms == 0) ? 0 : now_ms - sb_last_accept_ms;
    if (interval_ms > 0) {
      sb_note_accepted_interval(interval_ms);
    }

    sb_last_accept_ms = now_ms;
    event.event_id++;
    event.event_ms = now_ms;
    event.event_age_ms = 0;
    event.onset_strength = onset_strength;
    event.bass_onset_strength = bass_strength;
    event.onset = novelty_candidate;
    event.bass_onset = bass_candidate;
    event_active = true;
  }
  (void)refractory_open;
#else
  float novelty_delta = sb_novelty_fast - sb_novelty_slow;
  float low_delta = sb_low_fast - sb_low_slow;
  float peak_delta = sb_peak_fast - sb_peak_slow;
  float novelty_strength = sb_ob_clamp(novelty_delta * 3.5f, 0.0f, 1.0f);
  float peak_strength = sb_ob_clamp(peak_delta * 2.8f, 0.0f, 1.0f);
  float onset_strength = novelty_strength > peak_strength ? novelty_strength : peak_strength;
  float bass_strength = sb_ob_clamp(low_delta * 4.0f, 0.0f, 1.0f);
  bool refractory_open = (sb_last_accept_ms == 0) || (now_ms - sb_last_accept_ms >= SB_ONSET_REFRACTORY_MS);
  bool novelty_candidate = novelty_strength > 0.14f && novelty_attack > 0.03f && novelty_rise > 0.018f;
  bool peak_candidate = peak_strength > 0.20f && peak_attack > 0.06f && peak_rise > 0.05f;
  bool bass_candidate = bass_strength > 0.16f && low_attack > 0.03f && low_rise > 0.018f;
  bool accepted = refractory_open && (novelty_candidate || peak_candidate || bass_candidate);

  if (accepted) {
    uint32_t interval_ms = (sb_last_accept_ms == 0) ? 0 : now_ms - sb_last_accept_ms;
    if (interval_ms > 0) {
      sb_note_accepted_interval(interval_ms);
    }

    sb_last_accept_ms = now_ms;
    event.event_id++;
    event.event_ms = now_ms;
    event.event_age_ms = 0;
    event.onset_strength = onset_strength;
    event.bass_onset_strength = bass_strength;
    event.onset = novelty_candidate || peak_candidate;
    event.bass_onset = bass_candidate;
    event_active = true;
  }
#endif  // SB_ONSET_V2

  if (sb_interval_estimate_ms >= SB_BEAT_INTERVAL_MIN_MS && sb_last_accept_ms > 0) {
    uint32_t age_ms = now_ms - sb_last_accept_ms;
    float phase = float(age_ms % sb_interval_estimate_ms) / float(sb_interval_estimate_ms);
    event.beat_phase = sb_ob_clamp(phase, 0.0f, 1.0f);
    event.beat_confidence = sb_ob_clamp(float(sb_stable_intervals) / 2.0f, 0.0f, 1.0f);
    if (accepted && event.beat_confidence >= 0.5f) {
      event.beat = true;
    } else if (!event_active) {
      event.beat = false;
    }
  } else {
    event.beat_phase = 0.0f;
    event.beat_confidence = 0.0f;
    if (!event_active) {
      event.beat = false;
    }
  }

  if (!accepted) {
    event.event_age_ms = sb_event_age(now_ms, event.event_ms);
  }
  sb_prev_novelty = novelty;
  sb_prev_low_energy = low_energy;
  sb_prev_peak = peak_scaled;
  sb_publish_event(event);
}

SBOnsetBeatEvent sb_onset_beat_read() {
  SBOnsetBeatEvent event;
  portENTER_CRITICAL(&sb_onset_mux);
  event = sb_onset_event;
  portEXIT_CRITICAL(&sb_onset_mux);
  return event;
}
