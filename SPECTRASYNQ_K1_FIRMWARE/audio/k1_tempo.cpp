#include "k1_tempo.h"

#include <Arduino.h>
#include <math.h>
#include "config_types.h"

#if ENABLE_TEMPO_STREAM
#if __has_include(<esp_timer.h>)
#include <esp_timer.h>
static inline int64_t k1_tempo_diag_time_us() {
  return esp_timer_get_time();
}
#else
static inline int64_t k1_tempo_diag_time_us() {
  return 0;
}
#endif
#endif

// ============================================================================
// Configuration — single-rate Goertzel-over-novelty (K1 adaptation)
// ============================================================================

// 96 tempo bins from TEMPO_LOW upward, 1 BPM resolution -> 60..156 BPM.
static const uint16_t K1_NUM_TEMPI = 96;
static const float    K1_TEMPO_LOW = 60.0f;

// Novelty sample rate — MUST equal the rate novelty samples are ACTUALLY produced,
// or every Goertzel tempo bin resonates at the wrong BPM. k1_tempo_update() is called
// once per AP frame at CONFIG.SAMPLE_RATE / CONFIG.SAMPLES_PER_CHUNK = 12800/96 =
// 133.33 Hz. We emit one novelty sample every K1_NOVELTY_DECIMATION-th frame by an
// EXACT frame count (NOT a wall-clock ms gate — that landed at ~44 Hz while the
// coefficients assumed 50 Hz → a ~1.13x BPM scaling error: a 120 BPM click read ~139).
// NOTE: K1_AP_FRAME_HZ tracks the compiled audio timing map. Runtime CONFIG may be
// loaded from LittleFS before tempo starts, so system.h rejects/restores stale
// SAMPLE_RATE / SAMPLES_PER_CHUNK values before k1_tempo_init(). Probe builds may
// override these constants to test an alternate declared timing map.
#ifndef K1_TEMPO_AP_FRAME_HZ
#define K1_TEMPO_AP_FRAME_HZ ((float)DEFAULT_SAMPLE_RATE / (float)DEFAULT_SAMPLES_PER_CHUNK)
#endif
static const float    K1_AP_FRAME_HZ        = K1_TEMPO_AP_FRAME_HZ;                         // default: 133.333 Hz
static const uint16_t K1_NOVELTY_DECIMATION = K1_TEMPO_NOVELTY_DECIMATION;                  // default: every 3rd AP frame
static const float    K1_NOVELTY_RATE_HZ    = K1_AP_FRAME_HZ / (float)K1_NOVELTY_DECIMATION; // 44.444 Hz (TRUE emit rate)

// 512 samples @ 50 Hz ~= 10.2 s novelty window.
static const uint16_t K1_HISTORY_LENGTH = 512;

#ifndef K1_TEMPO_ACF_REFRESH_DECIMATION
#define K1_TEMPO_ACF_REFRESH_DECIMATION 1U
#endif
#if K1_TEMPO_ACF_REFRESH_DECIMATION < 1U
#error "K1_TEMPO_ACF_REFRESH_DECIMATION must be >= 1"
#endif
#ifndef K1_TEMPO_ACF_SPREAD_PROBE
// Production alias: K1_TEMPO_ACF_SPREAD_V1 enables the same work-spreading
// mechanism under a clean (non-probe) name for shipping builds. Absent any flag
// the source still defaults the spread OFF; probe envs that set
// K1_TEMPO_ACF_SPREAD_PROBE=1 directly are unaffected.
#if defined(K1_TEMPO_ACF_SPREAD_V1) && K1_TEMPO_ACF_SPREAD_V1
#define K1_TEMPO_ACF_SPREAD_PROBE 1
#else
#define K1_TEMPO_ACF_SPREAD_PROBE 0
#endif
#endif
#ifndef K1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT
#define K1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT 16U
#endif
#if K1_TEMPO_ACF_SPREAD_PROBE && (K1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT < 1U)
#error "K1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT must be >= 1 when K1_TEMPO_ACF_SPREAD_PROBE is enabled"
#endif
#ifndef K1_TEMPO_ACF_SKIP_UPDATE_ON_PUBLISH
#define K1_TEMPO_ACF_SKIP_UPDATE_ON_PUBLISH 0
#endif

// Per-emit decay so the Goertzel weights recent novelty more (fades stale beats).
static const float    K1_NOVELTY_DECAY = 0.999f;

// Phase shift for beat alignment (fraction of pi).
static const float    K1_BEAT_SHIFT_PERCENT = 0.08f;

// Lock threshold on confidence. Confidence is an OUT-OF-LOBE spectral-concentration measure
// (peak^2 / (peak^2 + Sum of bin^2 OUTSIDE the winner's +/-K1_CONF_LOBE main lobe); see
// k1_update_tempo). A real tempo is an isolated peak -> ~1.0; a flat/drone or scattered
// spectrum -> low. HOST-MEASURED (tempo_replay.py): clean beat 0.999 vs flat/drone 0.47, so
// this threshold sits in the wide gap and a clean beat reads near-maximal (the metronome bar).
static const float    K1_LOCK_CONFIDENCE = 0.60f;

// Confidence main-lobe half-width (bins). The tempo Goertzel's main lobe spans ~5 BPM, so
// bins within +/-this of the winner are the SAME peak; only energy OUTSIDE counts against
// confidence. Lets a real isolated tempo read ~1.0 while a broad/flat spectrum reads low.
static const int      K1_CONF_LOBE = 6;

// ----------------------------------------------------------------------------------------
// Log-Gaussian tactus prior (winner SELECTION only — Step 2 octave defence)
// ----------------------------------------------------------------------------------------
// The committed detector locks flawlessly on synthetic metronomes but is largely lost on
// real music: host-measured Acc2 ~14% vs a ~50% autocorrelation ceiling on the SAME
// novelty (docs/measurements/tempo-octave-baseline.md). The failure is LOW-BIN PINNING —
// the quartic winner-exaggeration (k1_update_tempo) amplifies whatever raw bin is tallest,
// which on real music is often a sub-harmonic / low bin, and the smoothing locks it in.
//
// Fix — "comb-plus-prior" (2026-06-04). Two principled, stacked terms, SELECTION-only:
//   1. HARMONIC-COMB ACF salience (k1_compute_acf_salience): scores each candidate by the
//      WEIGHTED ACF over its harmonic ladder (T,2T,3T,4T), so the fundamental beats its own
//      sub-multiples by construction. This is the octave-doubling defence; it cannot halve a
//      clean train (the fastest bin has the most in-band teeth). See that function's header.
//   2. Log-Gaussian TACTUS PRIOR (this constant): weights bins toward the perceptual tactus.
//      Symmetric in log2 -> half/double penalised equally; the comb decides the octave, the
//      prior just breaks residual ties and pulls scattered off-bins toward the tactus band.
//      Host-tuned on the HarmonixSet corpus (in-range GT median ~98 BPM) to centre 88 / sigma
//      0.75 oct — a robustness PLATEAU (neighbouring centres/sigmas all hold ~50-56% Acc1), not
//      a brittle spike. NOT firmware-v3's magic-number patches.
// Measured (scripts/regression-harness/tempo_accuracy.py, 32 in-range HarmonixSet tracks):
//   in-range Acc1 28.1% -> 56.2%, Acc2 40.6% -> 56.2%, octave-error 12.5% -> 0.0% (x2 5 -> 0).
// CONFIDENCE is preserved unchanged: it reads a SEPARATE broad 120-centred prior on the POINT
// (un-spread) ACF salience (k1_conf_score), so the comb's ladder-spreading does not dilute the
// concentration metric and the tempo_replay clean cases lock exactly as before (120 conf 0.83).
#ifndef K1_TACTUS_BPM
#define K1_TACTUS_BPM   88.0f
#endif
#ifndef K1_TACTUS_SIGMA
#define K1_TACTUS_SIGMA 0.75f
#endif
static const float    K1_TACTUS_BPM_V   = K1_TACTUS_BPM;
static const float    K1_TACTUS_SIGMA_V = K1_TACTUS_SIGMA;   // octaves
static float          k1_tempo_prior[K1_NUM_TEMPI];

// CONFIDENCE prior — separate from the SELECTION prior on purpose. Selection is pushed low/narrow
// for real-music octave defence (it decides WHICH octave is the tactus); confidence answers a
// different question ("is the winner an isolated peak?") and must read near-maximal for ANY clean
// lock, so it keeps the broad, tactus-centred shape that symmetrically suppresses a clean train's
// sub/super-multiple ACF peaks WITHOUT the selection prior's low-centre bias against fast tempi.
#ifndef K1_CONF_BPM
#define K1_CONF_BPM   120.0f
#endif
#ifndef K1_CONF_SIGMA
#define K1_CONF_SIGMA 0.9f
#endif
static const float    K1_CONF_BPM_V   = K1_CONF_BPM;
static const float    K1_CONF_SIGMA_V = K1_CONF_SIGMA;
static float          k1_conf_prior[K1_NUM_TEMPI];

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
static const float K1_PI = (float)M_PI;
static const float K1_TWO_PI = 2.0f * (float)M_PI;

// ============================================================================
// State (Core-0 owned)
// ============================================================================

struct K1TempoBin {
  float target_bpm;
  float target_hz;
  float coeff;                  // 2 * cos(w)
  float sine;                   // sin(w)
  float cosine;                 // cos(w)
  uint32_t block_size;          // novelty samples integrated
  float phase;                  // measured/extrapolated phase [-pi, +pi]
  float phase_radians_per_sec;  // 2*pi*hz
  float magnitude;              // normalized [0,1]
  float magnitude_raw;          // pre-normalization
};

static K1TempoBin k1_tempi[K1_NUM_TEMPI];
static float      k1_tempi_smooth[K1_NUM_TEMPI];

// Task #7: ACF-salience winner selection. Host-verified (docs/research/2026-06-04-acf-ceiling-
// characterization.md): autocorrelation of the novelty ring picks tempo at ~53% Acc2 vs the
// Goertzel-only 28% -- it bypasses the quartic low-bin pinning that is the dominant failure.
// At the firmware-native 44.44 Hz, integer lags collapse Acc1 (±1 lag ≈ ±13 BPM near fast
// tempi); 3-point parabolic sub-lag interpolation restores the 53% ceiling. Raw novelty (log1p
// hurt at 44.44 Hz). This REPLACES the Goertzel magnitude as the winner-selection signal only;
// confidence / phase / beat_strength still read the quartic'd k1_tempi_smooth, unchanged.
static float      k1_acf_salience[K1_NUM_TEMPI];   // HARMONIC-COMB salience (winner SELECTION)
static float      k1_acf_point[K1_NUM_TEMPI];      // POINT ACF salience (CONFIDENCE only — un-spread)
static float      k1_acf_work[K1_HISTORY_LENGTH];
static float      k1_acf_lag_table[200];
static bool       k1_acf_valid = false;
static uint8_t    k1_acf_refresh_ctr = 0;
#if K1_TEMPO_ACF_SPREAD_PROBE
static bool       k1_acf_spread_active = false;
static bool       k1_acf_spread_publish_pending = false;
static uint16_t   k1_acf_spread_cursor = 0;
static uint16_t   k1_acf_spread_nlag = 0;
static int        k1_acf_spread_lag_min = 0;
static uint32_t   k1_acf_publish_count = 0;
#endif

static float    k1_spectral_curve[K1_HISTORY_LENGTH];
static uint16_t k1_spectral_index = 0;
static float    k1_novelty_scale = 1.0f;
static uint8_t  k1_scale_count = 0;
static uint16_t k1_calc_bin = 0;

static uint16_t k1_winner_bin = K1_NUM_TEMPI / 2;
static uint16_t k1_candidate_bin = K1_NUM_TEMPI / 2;
static uint8_t  k1_candidate_frames = 0;
static float    k1_power_sum = 0.0f;
static float    k1_confidence = 0.0f;

#ifdef K1_TEMPO_CONF_V2
// ============================================================================
// V2 confidence / lock metric (compile-gated — replaces ONLY confidence+locked).
// ============================================================================
// Adapted from the donor BeatTracker.cpp:325-335 quality blend, but FED BY THE
// FORK'S OWN octave-defended winner/comb/ACF (NOT a wholesale donor port). The
// incumbent confidence (peak^2/(peak^2+Σ out-of-lobe sel^2) over ~83 normalised
// competitors) is structurally floored on real music — a dense squared-sum
// denominator drives a genuine lock to ~0.04 while a momentary peaky frame or
// white noise spikes it to 1.0 (volatile, no sustained lock). V2 replaces that
// ratio with a blend of three concentration cues read off the EXISTING selection
// machinery, then smooths + runs a hysteretic lock FSM with a watchdog.
//
// peak       = winner bin's POINT salience k1_conf_score (un-spread ACF×conf-prior). We use the
//              POINT salience, NOT the comb sel_score, for peakShare/prominence: the comb
//              DELIBERATELY co-activates the winner's harmonic ladder (octave defence), so the
//              comb peak's share and its peak-above-rivals are tiny on real music by construction.
//              The point salience is the sharp concentration the donor's blend assumes.
// peakShare  = peak / Σ(point salience over all bins).
// histShareNorm = clamp01((peakShare - LO)/(HI - LO))    [LO/HI CALIBRATED on this fork's
//                 corpus — NOT the donor's 0.04/0.24, which are donor-rate-specific].
// prominence = clamp01((peak - background)/(peak + 1e-9)), background = MEAN point salience
//              OUTSIDE the winner's ±K1_CONF_LOBE lobe. CORRECTION vs the literal donor form
//              (peak - SECOND): on this fork's salience, peak-vs-single-rival prominence collapses
//              to ~0 on real music (multiple comparable ACF peaks) and cannot reach 0.60. The
//              donor's INTENT is "peak above background"; peak-vs-MEAN-out-of-lobe is that intent
//              and is the cue that separates music (BGprom p50 0.66) from noise (0.065). Calibrated
//              on the 36-track corpus + synthetic silence/noise (tempo_confv2_calibrate.py).
// periodicity= clamp01(comb_at_winner / comb_max). k1_acf_salience[] is the comb already
//              normalised to max=1 (k1_compute_acf_salience), so comb_at_winner/comb_max ==
//              k1_acf_salience[winner] directly — reuses the selection comb, no recompute.
// quality    = clamp01(W1*histShareNorm + W2*prominence + W3*periodicity).
// conf_ema   = conf_ema*(1-alpha) + quality*alpha, alpha RATE-DERIVED (see K1_CONF_V2_ALPHA).
//
// Lock FSM: acquire when conf_ema>=K1_LOCK_CONFIDENCE AND warmup done AND >=2 beats seen;
// hold; release when conf_ema<K1_CONF_V2_REL (hysteresis); watchdog forces unlock after
// K1_CONF_V2_WATCHDOG_N consecutive updates with conf_ema<K1_CONF_V2_FLOOR.
// K1_LOCK_CONFIDENCE (0.60) is NOT lowered — the new metric must REACH it on real music.

// --- calibratable constants (all -D-overridable so the harness can sweep them) ---
// CALIBRATED on the 36-track HarmonixSet corpus + synthetic silence/white-noise by
// scripts/regression-harness/tempo_confv2_calibrate.py (data-driven grid sweep maximising the
// fraction of in-range music whose settled conf crosses 0.60 while holding noise/silence conf
// below 0.60). Chosen point: LO=0.01 HI=0.04 W=0.40/0.35/0.25 -> 69% of in-range tracks settle
// >=0.60, music median settled conf 0.041 -> ~0.71, worst-case synthetic-negative conf 0.468.
#ifndef K1_CONF_V2_LO
#define K1_CONF_V2_LO 0.01f          // point-peakShare at quality-floor (CALIBRATED)
#endif
#ifndef K1_CONF_V2_HI
#define K1_CONF_V2_HI 0.04f          // point-peakShare at quality-ceiling (CALIBRATED)
#endif
#ifndef K1_CONF_V2_W1
#define K1_CONF_V2_W1 0.40f          // histShareNorm weight (CALIBRATED)
#endif
#ifndef K1_CONF_V2_W2
#define K1_CONF_V2_W2 0.35f          // prominence (peak-above-background) weight (CALIBRATED)
#endif
#ifndef K1_CONF_V2_W3
#define K1_CONF_V2_W3 0.25f          // periodicity weight (CALIBRATED)
#endif
#ifndef K1_CONF_V2_REL
#define K1_CONF_V2_REL 0.42f         // lock-release threshold (hysteresis below 0.60; CALIBRATED)
#endif
#ifndef K1_CONF_V2_FLOOR
#define K1_CONF_V2_FLOOR 0.20f       // watchdog conf floor (above worst settled-music dips,
                                     // below the noise/silence band so a dead winner unlocks)
#endif
#ifndef K1_CONF_V2_WATCHDOG_N
#define K1_CONF_V2_WATCHDOG_N 12     // consecutive sub-floor updates -> force unlock + reset
#endif
// EMA smoothing time-constant 150 ms (donor used 0.12/update @50 Hz; that is donor-rate-
// specific). At the fork's K1_NOVELTY_RATE_HZ (44.44 Hz) emit rate, the rate-derived alpha is
//   alpha = 1 - exp(-(1/44.44)/0.150) = 1 - exp(-0.1500) ≈ 0.1393.
// If a per-call dt is available we use 1 - exp(-dt/0.150) per update; this constant is the
// nominal fallback. STATED, not a hardcoded donor 0.12. (Rounded to 0.139.)
#ifndef K1_CONF_V2_TAU_S
#define K1_CONF_V2_TAU_S 0.150f      // EMA time-constant (seconds)
#endif
static const float K1_CONF_V2_ALPHA_NOMINAL =
    1.0f - expf(-(1.0f / K1_NOVELTY_RATE_HZ) / K1_CONF_V2_TAU_S);  // ≈0.1393 @44.44 Hz

static float    k1_conf_ema = 0.0f;
static bool     k1_locked_v2 = false;
static uint16_t k1_v2_updates = 0;        // total V2 confidence updates (warmup counter)
static uint16_t k1_v2_subfloor = 0;       // consecutive sub-FLOOR updates (watchdog)
static uint16_t k1_v2_beats_seen = 0;     // beat_tick observations since reset (>=2 to acquire)
#ifndef K1_CONF_V2_WARMUP_UPDATES
// Warmup: the ACF ring must fill before the comb/sel salience is meaningful. History is 512
// novelty samples; require that many V2 updates (1 per emit) before a lock can acquire.
#define K1_CONF_V2_WARMUP_UPDATES 512
#endif
// Last-computed raw components, for -DK1_TEMPO_CONF_DUMP introspection / calibration.
static float    k1_v2_histShareNorm = 0.0f;
static float    k1_v2_prominence    = 0.0f;
static float    k1_v2_periodicity   = 0.0f;
static float    k1_v2_peakShare     = 0.0f;
static float    k1_v2_quality       = 0.0f;
#ifdef K1_TEMPO_CONF_DUMP
// Calibration-only: point-ACF-based peakShare/prominence (k1_conf_score, the un-spread
// sharper salience) so the calibrator can compare comb-vs-point conditioning before the
// design is frozen. NOT used by the metric; compiled only under K1_TEMPO_CONF_DUMP.
static float    k1_v2_point_peakShare  = 0.0f;
static float    k1_v2_point_prominence = 0.0f;
// Calibration-only: peak-above-background prominence — winner's point salience vs the MEAN
// out-of-lobe point salience (donor's actual "peak above background" intent; robust on this
// fork's DENSE comb salience where peak-vs-single-rival prominence collapses to ~0 on music).
static float    k1_v2_bg_prominence    = 0.0f;
#endif
#endif  // K1_TEMPO_CONF_V2

static float    k1_current_phase = 0.0f;
static bool     k1_beat_tick = false;
static uint32_t k1_last_tick_ms = 0;
static uint32_t k1_time_ms = 0;

#ifdef K1_TEMPO_FLYWHEEL_V2
// ============================================================================
// FLYWHEEL V2 — soft phase-locked beat tracker (compile-gated). Phase 3.
// ============================================================================
// REPLACES the open-loop free-run phase oscillator (k1_advance_phase) + the hard
// re-anchor (k1_update_tempo:757-759) with a soft PLL fed by INTERNALLY-derived
// onset evidence, lock-gated by V2 confidence, with bounded coast on lock loss.
//
// DESIGN (concepts from the donor BeatTracker CBSS, NOT a port; fed by the fork's
// octave-defended winner + V2 lock):
//   - Phase accumulator k1_fw_phase01 in [0,1) advances each EMIT at the winner's
//     instantaneous frequency (run_bpm/60 * dt). The winner OWNS the tempo; the PLL
//     never re-picks the octave.
//   - Onset evidence: peak-pick the SAME novelty ring k1_tempo already consumes
//     (k1_compute_onset_phase) — a novelty sample that is a local maximum AND above
//     an adaptive threshold (running mean + k*MAD) is an onset; its fractional phase
//     within the current beat period is the measurement.
//   - Correction: phase_err = wrap(onset_phase - predicted_phase) in (-0.5,0.5];
//     k1_fw_phase01 += Kp*phase_err (BOUNDED, |corr|<=K1_FW_MAX_CORR per onset =
//     inertia). Optional Ki slews run_bpm within +/-K1_FW_FREQ_PULL of the winner
//     ONLY (so the PLL cannot drift to another octave).
//   - Beat tick = upward wrap of k1_fw_phase01 (one-shot per beat period); emitted
//     ONLY when locked (or in a bounded coast window after lock loss). No hard jump.
//
// RATE DERIVATIONS (all at K1_NOVELTY_RATE_HZ = 44.444 Hz emit rate):
//   - Onset adaptive-threshold EMA tau 0.30 s (slow floor tracker):
//       alpha_floor = 1 - exp(-(1/44.444)/0.30) = 1 - exp(-0.0750) ~= 0.0723.
//   - Coast window: K1_FW_COAST_BEATS beats * (60/run_bpm) seconds; expressed in beats
//     so it is tempo-relative (a "bounded ~2-bar flywheel" the donor uses), NOT a fixed
//     ms constant. Converted to emit-frames at run-time from run_bpm.
//   - Kp / Ki / max-corr / onset k-threshold are DATA-CALIBRATED on the corpus
//     (tempo_flywheel_calibrate.py); the values below are the calibrated point.

// --- calibratable constants (all -D-overridable so the harness can sweep) ---
#ifndef K1_FW_KP
#define K1_FW_KP 0.25f            // proportional phase-correction gain per onset (CALIBRATED:
                                  // synthetic clean-train phase-lock needs Kp>=0.20 to converge
                                  // the steady-state onset offset to <70 ms; 0.25 gives beat-F
                                  // 1.000 on 90/120 trains; corpus density-in-band holds 97%.)
#endif
#ifndef K1_FW_KI
#define K1_FW_KI 0.002f           // integral freq-slew gain per onset (CALIBRATED; tiny — kills
                                  // residual phase drift without leaving the winner's octave)
#endif
#ifndef K1_FW_MAX_CORR
#define K1_FW_MAX_CORR 0.10f      // |phase correction| cap per onset, in beats (inertia; CALIBRATED:
                                  // 0.10 lets the PLL acquire in a few beats yet rejects single
                                  // spurious onsets — one bad onset moves the grid <=0.10 beat)
#endif
#ifndef K1_FW_FREQ_PULL
#define K1_FW_FREQ_PULL 0.04f     // max fractional run_bpm deviation from the winner (+/-4%; octave-safe)
#endif
#ifndef K1_FW_ONSET_K
#define K1_FW_ONSET_K 1.20f       // onset threshold = floor_mean + K*floor_mad (CALIBRATED)
#endif
#ifndef K1_FW_ONSET_FLOOR_TAU_S
#define K1_FW_ONSET_FLOOR_TAU_S 0.30f   // adaptive onset-floor EMA time-constant (seconds)
#endif
#ifndef K1_FW_COAST_BEATS
#define K1_FW_COAST_BEATS 8       // coast this many beats after lock loss, then stop emitting (flywheel)
#endif
#ifndef K1_FW_REFRACTORY
#define K1_FW_REFRACTORY 0.45f    // min phase advance (in beats) since last tick before another can fire
#endif
static const float K1_FW_FLOOR_ALPHA =
    1.0f - expf(-(1.0f / K1_NOVELTY_RATE_HZ) / K1_FW_ONSET_FLOOR_TAU_S);  // ~0.0723 @44.44 Hz

static float    k1_fw_phase01      = 0.0f;   // PLL beat phase [0,1); 0 == beat instant
static float    k1_fw_run_bpm      = 0.0f;   // PLL running tempo (winner +/- Ki slew, bounded)
static bool     k1_fw_beat_tick    = false;  // one-shot: true on exactly the emit frame of a beat
static float    k1_fw_onset_floor  = 0.0f;   // adaptive onset-strength mean (EMA)
static float    k1_fw_onset_dev    = 0.0f;   // adaptive onset-strength mean-abs-dev (EMA)
static float    k1_fw_prev_nov     = 0.0f;   // previous emit's novelty sample (peak-pick)
static float    k1_fw_prev_prev    = 0.0f;   // novelty two emits ago (3-point local-max test)
static bool     k1_fw_have_prev    = false;
static float    k1_fw_since_tick   = 1.0f;   // phase (beats) advanced since the last emitted tick
static uint16_t k1_fw_coast_left   = 0;      // emit-frames of coast remaining after lock loss
static bool     k1_fw_was_locked   = false;  // previous-update lock state (edge detect for coast)
static bool     k1_fw_primed       = false;  // run_bpm/phase initialised from first valid winner
static float    k1_fw_last_adv     = 0.0f;   // last emit's phase advance (beats) — onset lag correction
static uint32_t k1_fw_onset_count  = 0;      // diagnostic: total onsets detected (host introspection)
static float    k1_fw_last_onset_phase = -1.0f; // diagnostic: last detected onset phase
#endif  // K1_TEMPO_FLYWHEEL_V2

static bool     k1_silence_detected = false;
static float    k1_silence_level = 0.0f;

// Downsample accumulator (peak-hold preserves onset transients).
static bool     k1_tempo_primed = false;
static float    k1_accum = 0.0f;
static uint32_t k1_last_emit_ms = 0;
static uint16_t k1_frame_ctr = 0;   // AP frames since the last novelty emit

#if ENABLE_TEMPO_STREAM
static uint32_t k1_dbg_last_emit_ms = 0;
static uint32_t k1_dbg_emit_count = 0;
static float    k1_dbg_last_sample = 0.0f;
static float    k1_dbg_last_scaled_sample = 0.0f;
static float    k1_dbg_last_scale = 1.0f;
static uint32_t k1_dbg_silence_elapsed_us = 0;
static uint32_t k1_dbg_acf_elapsed_us = 0;
static uint32_t k1_dbg_update_elapsed_us = 0;
static uint32_t k1_dbg_phase_elapsed_us = 0;
static uint32_t k1_dbg_publish_elapsed_us = 0;
static uint32_t k1_dbg_emit_elapsed_us = 0;
#endif

static portMUX_TYPE k1_tempo_mux = portMUX_INITIALIZER_UNLOCKED;
static K1TempoEvent k1_tempo_event = {};

// ============================================================================
// Helpers
// ============================================================================

static float k1_t_clamp(float v, float lo, float hi) {
  if (!isfinite(v)) return lo;
  if (v < lo) return lo;
  if (v > hi) return hi;
  return v;
}

static void k1_tempo_publish(const K1TempoEvent& e) {
  portENTER_CRITICAL(&k1_tempo_mux);
  k1_tempo_event = e;
  portEXIT_CRITICAL(&k1_tempo_mux);
}

static uint16_t k1_validate_winner() {
  if (k1_winner_bin >= K1_NUM_TEMPI) return K1_NUM_TEMPI / 2;
  return k1_winner_bin;
}

// EMA of 1/(max*0.5) for stable normalization of the novelty buffer.
static void k1_update_scale(float tau) {
  float max_val = 0.0f;
  for (uint16_t i = 0; i < K1_HISTORY_LENGTH; i++) {
    if (k1_spectral_curve[i] > max_val) max_val = k1_spectral_curve[i];
  }
  if (max_val < 1e-10f) max_val = 1e-10f;
  float target = 1.0f / (max_val * 0.5f);
  k1_novelty_scale = k1_novelty_scale * (1.0f - tau) + target * tau;
}

// Silence = low contrast across the recent novelty window.
static void k1_check_silence() {
  float min_val = 1.0f;
  float max_val = 0.0f;
  for (uint16_t i = 0; i < 128; i++) {
    uint16_t idx = (uint16_t)((K1_HISTORY_LENGTH + k1_spectral_index - 128 + i) % K1_HISTORY_LENGTH);
    float scaled = k1_t_clamp(k1_spectral_curve[idx] * k1_novelty_scale, 0.0f, 1.0f);
    float processed = (scaled < 0.5f ? scaled : 0.5f) * 2.0f;
    float s = sqrtf(processed);
    if (s > max_val) max_val = s;
    if (s < min_val) min_val = s;
  }
  float contrast = fabsf(max_val - min_val);
  float silence_raw = 1.0f - contrast;
  if (silence_raw > 0.5f) {
    k1_silence_detected = true;
    k1_silence_level = k1_t_clamp((silence_raw - 0.5f) * 2.0f, 0.0f, 1.0f);
  } else {
    k1_silence_detected = false;
    k1_silence_level = 0.0f;
  }
}

// Goertzel magnitude + phase for one bin over the novelty ring.
static float k1_compute_magnitude(uint16_t bin) {
  uint32_t block_size = k1_tempi[bin].block_size;
  if (block_size > K1_HISTORY_LENGTH) block_size = K1_HISTORY_LENGTH;

  float q1 = 0.0f;
  float q2 = 0.0f;
  const float coeff = k1_tempi[bin].coeff;

  for (uint32_t i = 0; i < block_size; i++) {
    uint16_t idx = (uint16_t)((K1_HISTORY_LENGTH + k1_spectral_index - block_size + i) % K1_HISTORY_LENGTH);
    // Goertzel input headroom. The autoranger scales the curve so its running max maps to
    // ~2.0; the OLD 1.0f upper clamp therefore soft-limited the top half of every onset
    // peak into a near-square wave, distorting the tempo spectrum (host-measured: real-music
    // Acc2 17%, below even a clean Fourier tempogram). A 4.0f ceiling (2x the autoranged max)
    // keeps a sane limiter against pathological spikes while leaving onset peaks intact
    // (Acc2 17% -> 25%, metronome lock preserved). See docs/measurements/tempo-octave-baseline.md.
    float sample = k1_t_clamp(k1_spectral_curve[idx] * k1_novelty_scale, 0.0f, 4.0f);
    float q0 = coeff * q1 - q2 + sample;
    q2 = q1;
    q1 = q0;
  }

  float real = q1 - q2 * k1_tempi[bin].cosine;
  float imag = q2 * k1_tempi[bin].sine;

  float phase = atan2f(imag, real) + (K1_PI * K1_BEAT_SHIFT_PERCENT);
  if (phase > K1_PI)        phase -= K1_TWO_PI;
  else if (phase < -K1_PI)  phase += K1_TWO_PI;
  k1_tempi[bin].phase = phase;

  float mag_sq = q1 * q1 + q2 * q2 - q1 * q2 * coeff;
  if (mag_sq < 0.0f) mag_sq = 0.0f;
  return sqrtf(mag_sq) / ((float)block_size * 0.5f);
}

// ----------------------------------------------------------------------------------------
// Harmonic-comb ACF salience (octave defence — "comb-plus-prior", task 2026-06-04)
// ----------------------------------------------------------------------------------------
// The committed POINT ACF salience samples each bin at ITS lag only, so a sub-multiple of the
// true tactus (the 8th-note / "double" lag, or a slow sub-harmonic at the low end) — which on
// real music often carries the tallest single ACF peak — wins, then the smoothing/hysteresis
// pin it. Host evidence (tempo-octave-baseline.tracks.csv): the in-range failures are a SLOW-GT
// x2 cluster (gt71->140, gt74->148, gt75->152, gt80->155) AND a mid-band fast-pin cluster
// (gt90->121, gt91->133, gt96->148) — i.e. the detector systematically prefers the FASTER bin.
//
// FIX — comb-filter the ACF in the LAG domain. A genuine tactus period T implies correlation
// not only at lag T but at every integer-multiple lag 2T,3T,4T (every-other-beat, every-third).
// Scoring each candidate period by the WEIGHTED SUM of ACF at its harmonic ladder
//     comb(T) = Σ_{k=1..K} w_k * acf(k*T)   (w slowly-decaying, see K1_COMB_W*)
// rewards the candidate whose WHOLE ladder lands on real ACF peaks. The true fundamental
// maximises this; a faster sub-multiple (T/2) keeps the acf(T),acf(2T)... teeth but spends its
// score on extra half-integer-of-T lags that a real tactus does NOT reinforce, so it loses.
// METRONOME GUARD (the trap that reverted the previous octave arbiter): for a CLEAN periodic
// train every integer-lag ACF peak is ~equal, so the FUNDAMENTAL has the most in-band teeth and
// its comb is the LARGEST — the comb cannot halve a clean 120/90/144 train by construction (it
// over-weights, never under-weights, the fastest bin). Verified on tempo_replay clean cases.
//
// Teeth lags reach K * lag(60 BPM) ~= 4*44 = 178 samples; the ACF band is widened to cover them.
// acf(k*T) is read by 3-point parabolic interpolation off the integer-lag ACF (sub-lag interp is
// load-bearing at 44.44 Hz — see the array comment), so fractional ladder lags are sampled cleanly.
#ifndef K1_COMB_TEETH
#define K1_COMB_TEETH 4             // harmonic ladder depth (T,2T,3T,4T)
#endif
// Tooth weights — FLATTER than 1/k (host-swept: 1/k gave Acc1 34%, this gives 37%+ then the
// prior reshape lifts it further). A slow decay keeps the every-other-/-third-/-fourth-beat
// teeth heavy enough to assert the fundamental over a sub-multiple, without over-weighting a
// long noisy tail (steeper than this collapsed back toward the point-ACF doubling).
#ifndef K1_COMB_W2
#define K1_COMB_W2 0.8f            // every-other-beat tooth (2T)
#endif
#ifndef K1_COMB_W3
#define K1_COMB_W3 0.7f            // every-third-beat tooth (3T)
#endif
#ifndef K1_COMB_W4
#define K1_COMB_W4 0.6f            // every-fourth-beat tooth (4T)
#endif

// 3-point parabolic sample of the integer-lag ACF table at a real lag (table covers
// [lag_lo .. lag_lo+nlag-1]); returns 0 outside the table. Shared by the comb teeth.
static inline float k1_acf_at(const float* ac, int nlag, int lag_lo, float lag_real) {
  int L0 = (int)floorf(lag_real);
  float frac = lag_real - (float)L0;
  int c = L0 - lag_lo;
  if (c >= 1 && c < nlag - 1) {
    float ym = ac[c - 1], y0 = ac[c], yp = ac[c + 1];
    return y0 + 0.5f * frac * (yp - ym) + 0.5f * frac * frac * (yp - 2.0f * y0 + ym);
  }
  if (c >= 0 && c < nlag) return ac[c];
  return 0.0f;
}

static int k1_acf_lag_min() {
  return (int)floorf(K1_NOVELTY_RATE_HZ * 60.0f / 160.0f) - 1;
}

static int k1_acf_nlag(int lag_min) {
  const int lag_max = (int)ceilf(K1_COMB_TEETH * K1_NOVELTY_RATE_HZ * 60.0f / 55.0f) + 1;
  int nlag = lag_max - lag_min + 1;
  if (nlag > 200) nlag = 200;
  if (nlag < 1) nlag = 1;
  return nlag;
}

static void k1_acf_prepare_work() {
  // Linearise the ring oldest->newest and mean-subtract (autocorr needs zero-mean).
  float mean = 0.0f;
  for (uint16_t k = 0; k < K1_HISTORY_LENGTH; k++) {
    float v = k1_spectral_curve[(uint16_t)((k1_spectral_index + k) % K1_HISTORY_LENGTH)] * k1_novelty_scale;
    k1_acf_work[k] = v;
    mean += v;
  }
  mean /= (float)K1_HISTORY_LENGTH;
  for (uint16_t k = 0; k < K1_HISTORY_LENGTH; k++) k1_acf_work[k] -= mean;
}

static uint16_t k1_acf_compute_lag_rows(float* ac, int lag_min, int nlag, uint16_t cursor, uint16_t rows) {
  uint16_t next = cursor;
  const uint16_t limit = (rows < 1U) ? 1U : rows;
  const uint16_t end = (uint16_t)((next + limit < (uint16_t)nlag) ? (next + limit) : (uint16_t)nlag);
  for (; next < end; next++) {
    int lag = lag_min + (int)next;
    float s = 0.0f;
    for (uint16_t t = (uint16_t)lag; t < K1_HISTORY_LENGTH; t++) s += k1_acf_work[t] * k1_acf_work[t - lag];
    ac[next] = s;
  }
  return next;
}

static void k1_acf_publish_salience(const float* ac, int nlag, int lag_min) {
  // Biased ACF over the lag band that now spans BOTH the BPM range AND the harmonic-comb
  // teeth: the slowest bin (60 BPM ~= lag 44 @ 44.44 Hz) needs teeth out to K*lag ~= 178,
  // so the band runs lag_min(160 BPM) .. K*lag(55 BPM). Capped at 200 (history is 512, so
  // even the longest tooth still sums over >300 products — biased ACF stays well-conditioned).
  // Per-bin HARMONIC-COMB salience: weighted ACF over the period's integer-multiple ladder.
  // Each tooth is read with parabolic sub-lag interpolation; teeth that fall past the table
  // contribute 0 (the comb naturally shortens for slow bins, which keeps the fundamental ahead).
  const float tooth_w[K1_COMB_TEETH] = { 1.0f, K1_COMB_W2, K1_COMB_W3, K1_COMB_W4 };
  float smax = 1e-12f;   // comb max (for selection)
  float pmax = 1e-12f;   // point max (for confidence)
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
    float bpm = k1_tempi[i].target_bpm;
    if (bpm < 1.0f) { k1_acf_salience[i] = 0.0f; k1_acf_point[i] = 0.0f; continue; }
    float lag_real = K1_NOVELTY_RATE_HZ * 60.0f / bpm;
    float comb = 0.0f;
    float point = 0.0f;
    for (int k = 0; k < K1_COMB_TEETH; k++) {
      float v = k1_acf_at(ac, nlag, lag_min, lag_real * (float)(k + 1));
      if (v < 0.0f) v = 0.0f;                 // rectify (anti-correlation is not evidence)
      if (k == 0) point = v;                  // k=1 tooth IS the point ACF salience
      comb += tooth_w[k] * v;
    }
    k1_acf_salience[i] = comb;
    k1_acf_point[i]    = point;
    if (comb  > smax) smax = comb;
    if (point > pmax) pmax = point;
  }
  // Normalise BOTH to max=1. The COMB feeds winner selection (octave defence); the POINT
  // salience feeds confidence, so the comb's deliberate harmonic-ladder spreading does NOT
  // dilute the concentration metric — a clean isolated tempo keeps reading near-maximal
  // confidence (the metronome bar the tempo_replay gate asserts), unchanged from pre-comb.
  const float inv  = 1.0f / smax;
  const float invp = 1.0f / pmax;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) { k1_acf_salience[i] *= inv; k1_acf_point[i] *= invp; }
  k1_acf_valid = (smax > 1e-6f);
}

static void k1_compute_acf_salience() {
  k1_acf_prepare_work();
  const int lag_min = k1_acf_lag_min();
  const int nlag = k1_acf_nlag(lag_min);
  (void)k1_acf_compute_lag_rows(k1_acf_lag_table, lag_min, nlag, 0, (uint16_t)nlag);
  k1_acf_publish_salience(k1_acf_lag_table, nlag, lag_min);
}

#if K1_TEMPO_ACF_SPREAD_PROBE
static bool k1_compute_acf_salience_spread(bool start_refresh) {
  if (k1_acf_spread_publish_pending) {
    k1_acf_publish_salience(k1_acf_lag_table, (int)k1_acf_spread_nlag, k1_acf_spread_lag_min);
    k1_acf_spread_publish_pending = false;
    if (k1_acf_publish_count < 0xFFFFFFFFUL) k1_acf_publish_count++;
    return true;
  }

  if (start_refresh && !k1_acf_spread_active) {
    k1_acf_prepare_work();
    k1_acf_spread_lag_min = k1_acf_lag_min();
    k1_acf_spread_nlag = (uint16_t)k1_acf_nlag(k1_acf_spread_lag_min);
    k1_acf_spread_cursor = 0;
    k1_acf_spread_active = true;
  }

  if (!k1_acf_spread_active) return false;

  k1_acf_spread_cursor = k1_acf_compute_lag_rows(
      k1_acf_lag_table,
      k1_acf_spread_lag_min,
      (int)k1_acf_spread_nlag,
      k1_acf_spread_cursor,
      (uint16_t)K1_TEMPO_ACF_SPREAD_LAGS_PER_EMIT);

  if (k1_acf_spread_cursor >= k1_acf_spread_nlag) {
    k1_acf_spread_active = false;
    k1_acf_spread_publish_pending = true;
  }
  return false;
}
#endif

// Selection score for winner choice: de-sharpen the quartic pre-emphasis (^0.25 ~= back to
// linear magnitude, restoring the tempo-spectrum shape x^4 collapses) and apply the
// log-Gaussian tactus prior. Confidence/beat_strength still read the quartic'd
// k1_tempi_smooth directly, so the metronome lock is unaffected (its raw max IS the winner).
static inline float k1_sel_score(uint16_t i) {
  // Task #7: ACF salience is the winner signal once primed; fall back to the Goertzel
  // de-quartic score during warm-up (before the novelty ring has filled enough for a stable ACF).
  if (k1_acf_valid) return k1_acf_salience[i] * k1_tempo_prior[i];
  float m = k1_tempi_smooth[i];
  if (m < 0.0f) m = 0.0f;
  return sqrtf(sqrtf(m)) * k1_tempo_prior[i];
}

// Confidence score — the SAME prior, but on the POINT (un-spread) ACF salience instead of the
// harmonic comb. Confidence is a concentration measure: a real isolated tempo is one sharp peak.
// The comb DELIBERATELY co-activates the winner's half/double ladder bins (that is how it defends
// the octave), so scoring confidence on the comb would count the winner's OWN ladder as competing
// energy and under-report a genuine lock (host-measured: clean 120 conf 0.83 -> 0.62, tripping the
// tempo_replay metronome-bar gate). The point salience has no such spreading, so a clean lock reads
// near-maximal confidence exactly as before the comb — winner SELECTION gains the comb, the
// confidence METRIC is preserved unchanged.
static inline float k1_conf_score(uint16_t i) {
  // Point (un-spread) ACF salience x the BROAD CONFIDENCE prior (NOT the aggressive selection
  // prior). The prior is still needed to suppress a clean train's own sub/super-multiple ACF
  // peaks (without it, lags 2T/3T/4T are equally tall and the concentration collapses); but it is
  // the broad tactus-centred one, so a clean lock reads near-maximal independent of how low the
  // selection prior is tuned — decoupling real-music octave defence from the metronome-bar gate.
  if (k1_acf_valid) return k1_acf_point[i] * k1_conf_prior[i];
  float m = k1_tempi_smooth[i];
  if (m < 0.0f) m = 0.0f;
  return sqrtf(sqrtf(m)) * k1_conf_prior[i];
}

#ifdef K1_TEMPO_CONF_V2
// V2 confidence + lock. Computes quality from the EXISTING selection machinery, smooths it
// (rate-derived EMA), and runs the hysteretic lock FSM + watchdog. Sets k1_confidence (=
// conf_ema) and k1_locked_v2. Selection/winner/comb/ACF are NOT touched. `dt_sec` is the
// real per-emit elapsed (so alpha is dt-aware); pass <=0 to use the nominal alpha.
static void k1_update_confidence_v2(float dt_sec) {
  const uint16_t wbin = k1_validate_winner();

  if (k1_acf_valid) {
    // peak = winner's POINT salience (k1_conf_score = un-spread ACF×conf-prior); background =
    // MEAN point salience outside the winner's ±K1_CONF_LOBE lobe; sum = Σ point salience.
    // (Point, not comb: the comb co-activates the winner's harmonic ladder, so a comb peakShare/
    // prominence is structurally tiny on real music — see header CORRECTION.)
    const float peak = k1_conf_score(wbin);
    float out_sum = 0.0f;
    float ssum    = 0.0f;
    int   out_n   = 0;
    for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
      const float s = k1_conf_score(i);
      ssum += s;
      int d = (int)i - (int)wbin; if (d < 0) d = -d;
      if (d > K1_CONF_LOBE) { out_sum += s; out_n++; }
    }
    const float peakShare = (ssum > 1e-9f) ? (peak / ssum) : 0.0f;
    const float histShareNorm =
        k1_t_clamp((peakShare - K1_CONF_V2_LO) / (K1_CONF_V2_HI - K1_CONF_V2_LO), 0.0f, 1.0f);
    const float background = (out_n > 0) ? (out_sum / (float)out_n) : 0.0f;
    const float prominence = k1_t_clamp((peak - background) / (peak + 1e-9f), 0.0f, 1.0f);
    // k1_acf_salience[] is the comb already normalised to max=1, so comb_at_winner/comb_max
    // == k1_acf_salience[winner] (the selection comb, reused — no recompute).
    const float periodicity = k1_t_clamp(k1_acf_salience[wbin], 0.0f, 1.0f);
    const float quality = k1_t_clamp(
        K1_CONF_V2_W1 * histShareNorm + K1_CONF_V2_W2 * prominence + K1_CONF_V2_W3 * periodicity,
        0.0f, 1.0f);

    k1_v2_histShareNorm = histShareNorm;
    k1_v2_prominence    = prominence;
    k1_v2_periodicity   = periodicity;
    k1_v2_peakShare     = peakShare;
    k1_v2_quality       = quality;

#ifdef K1_TEMPO_CONF_DUMP
    // Calibration-only: also compute point-ACF-based peak/second/sum (sharper, un-spread).
    {
      const float ppeak = k1_conf_score(wbin);
      float psecond = 0.0f, psum = 0.0f, out_sum = 0.0f; int out_n = 0;
      for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
        const float s = k1_conf_score(i);
        psum += s;
        int d = (int)i - (int)wbin; if (d < 0) d = -d;
        if (d > K1_CONF_LOBE) { if (s > psecond) psecond = s; out_sum += s; out_n++; }
      }
      k1_v2_point_peakShare  = (psum > 1e-9f) ? (ppeak / psum) : 0.0f;
      k1_v2_point_prominence = k1_t_clamp((ppeak - psecond) / (ppeak + 1e-9f), 0.0f, 1.0f);
      const float out_mean = (out_n > 0) ? (out_sum / (float)out_n) : 0.0f;
      k1_v2_bg_prominence = k1_t_clamp((ppeak - out_mean) / (ppeak + 1e-9f), 0.0f, 1.0f);
    }
#endif

    const float alpha = (dt_sec > 0.0f && dt_sec < 1.0f)
        ? (1.0f - expf(-dt_sec / K1_CONF_V2_TAU_S))
        : K1_CONF_V2_ALPHA_NOMINAL;
    k1_conf_ema = k1_conf_ema * (1.0f - alpha) + quality * alpha;
  } else {
    // Warm-up / flat / silence: no valid ACF yet. Decay conf toward 0 with the same EMA so a
    // stale lock can never persist into silence; do NOT inject the Goertzel-spectrum number
    // (that path is what made the incumbent volatile). quality target = 0.
    const float alpha = (dt_sec > 0.0f && dt_sec < 1.0f)
        ? (1.0f - expf(-dt_sec / K1_CONF_V2_TAU_S))
        : K1_CONF_V2_ALPHA_NOMINAL;
    k1_conf_ema = k1_conf_ema * (1.0f - alpha);
    k1_v2_histShareNorm = k1_v2_prominence = k1_v2_periodicity = k1_v2_peakShare = k1_v2_quality = 0.0f;
  }

  if (k1_conf_ema > 1.0f) k1_conf_ema = 1.0f;
  if (k1_conf_ema < 0.0f) k1_conf_ema = 0.0f;
  k1_confidence = k1_conf_ema;

  if (k1_v2_updates < 0xFFFF) k1_v2_updates++;

  // --- lock FSM (hysteresis + watchdog) ---
  const bool warmup_done = (k1_v2_updates >= K1_CONF_V2_WARMUP_UPDATES);

  // Sub-floor watchdog counter — ONLY runs after warmup AND once a lock has been acquired. It
  // exists to release a DEAD lock (winner collapsed mid-track), NOT to gate acquisition: during
  // the initial ramp conf_ema climbs through the sub-floor band one alpha-step at a time, so
  // counting sub-floor frames before lock would reset the EMA every WATCHDOG_N frames and the
  // confidence could never ramp to 0.60 (the acquire bug this guard avoids).
  if (k1_locked_v2 && warmup_done && k1_conf_ema < K1_CONF_V2_FLOOR) {
    if (k1_v2_subfloor < 0xFFFF) k1_v2_subfloor++;
  } else {
    k1_v2_subfloor = 0;
  }

  if (!k1_locked_v2) {
    if (k1_conf_ema >= K1_LOCK_CONFIDENCE && warmup_done && k1_v2_beats_seen >= 2) {
      k1_locked_v2 = true;
    }
  } else {
    if (k1_conf_ema < K1_CONF_V2_REL) k1_locked_v2 = false;
  }
  // Watchdog: a long sub-floor run while LOCKED forces unlock and resets the EMA so a dead winner
  // cannot hold a stale lock (and re-acquisition restarts from scratch).
  if (k1_v2_subfloor >= K1_CONF_V2_WATCHDOG_N) {
    k1_locked_v2 = false;
    k1_conf_ema = 0.0f;
    k1_confidence = 0.0f;
    k1_v2_subfloor = 0;
  }
}
#endif  // K1_TEMPO_CONF_V2

// Winner selection with hysteresis: challenger needs +10% for 5 consecutive ticks.
static void k1_update_winner() {
  if (k1_winner_bin >= K1_NUM_TEMPI) {
    k1_winner_bin = K1_NUM_TEMPI / 2;
    k1_candidate_bin = k1_winner_bin;
    k1_candidate_frames = 0;
  }

  uint16_t best_bin = 0;
  float best_mag = -1.0f;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
    float s = k1_sel_score(i);
    if (s > best_mag) {
      best_mag = s;
      best_bin = i;
    }
  }

  if (best_bin != k1_winner_bin) {
    float current_mag = k1_sel_score(k1_winner_bin);
    if (best_mag > current_mag * 1.1f) {
      if (best_bin == k1_candidate_bin) {
        if (k1_candidate_frames < 255) k1_candidate_frames++;
        if (k1_candidate_frames >= 5) {
          k1_winner_bin = best_bin;
          k1_candidate_frames = 0;
        }
      } else {
        k1_candidate_bin = best_bin;
        k1_candidate_frames = 1;
      }
    } else {
      k1_candidate_frames = 0;
    }
  } else {
    k1_candidate_frames = 0;
  }

  if (k1_winner_bin >= K1_NUM_TEMPI) k1_winner_bin = K1_NUM_TEMPI / 2;
}

// One full-spectrum tempo step (interleaved 2 bins/tick to spread CPU).
static void k1_update_tempo(float delta_sec) {
  uint16_t bin0 = k1_calc_bin;
  uint16_t bin1 = (uint16_t)((k1_calc_bin + 1) % K1_NUM_TEMPI);
  k1_tempi[bin0].magnitude_raw = k1_compute_magnitude(bin0);
  k1_tempi[bin1].magnitude_raw = k1_compute_magnitude(bin1);
  k1_calc_bin = (uint16_t)((k1_calc_bin + 2) % K1_NUM_TEMPI);

  float max_val = 0.01f;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
    if (k1_tempi[i].magnitude_raw > max_val) max_val = k1_tempi[i].magnitude_raw;
  }
  float autoranger = 1.0f / max_val;
  k1_power_sum = 1e-8f;

  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
    float scaled = k1_tempi[i].magnitude_raw * autoranger;
    scaled = scaled * scaled;          // quartic winner exaggeration
    scaled = scaled * scaled;
    k1_tempi[i].magnitude = scaled;

    if (k1_tempi[i].magnitude > 0.005f) {
      k1_tempi_smooth[i] = k1_tempi_smooth[i] * 0.975f + k1_tempi[i].magnitude * 0.025f;
      k1_power_sum += k1_tempi_smooth[i];
      k1_tempi[i].phase += k1_tempi[i].phase_radians_per_sec * delta_sec;
      while (k1_tempi[i].phase > K1_PI)  k1_tempi[i].phase -= K1_TWO_PI;
      while (k1_tempi[i].phase < -K1_PI) k1_tempi[i].phase += K1_TWO_PI;
    } else {
      k1_tempi_smooth[i] *= 0.995f;
    }
  }

  // Winner FIRST, then confidence — so confidence is measured around the tempo we actually
  // report (the ACF/sel_score winner), not a separately-chosen Goertzel peak.
  k1_update_winner();

  // Confidence (task 2026-06-04, Captain "fix at the source"): dominance of the WINNER's
  // SELECTION SCORE k1_sel_score = (ACF salience x log-Gaussian tactus prior) — the SAME signal
  // that chose the winner — over its out-of-lobe remainder:
  //     conf = peak^2 / (peak^2 + Σ sel^2 OUTSIDE the winner's ±K1_CONF_LOBE lobe).
  // WHY: the OLD form measured the Goertzel spectrum around the GOERTZEL peak bin, a DIFFERENT
  // bin than the reported (ACF) winner whenever the two disagree (which the ACF exists to do).
  // On real music that under-reported genuine ACF locks, so consumers' confidence gates
  // flickered — Captain 2026-06-04: Tempo Comet "hits 3-4 beats then takes a 2-bar break".
  // Winner and confidence now come from ONE signal -> the mismatch is gone by construction. The
  // tactus prior suppresses the ACF's sub-multiple (half/double) lobes so a clean lock still
  // reads near-maximal. During warm-up / flat / silence the ACF is not yet valid; we fall back
  // to the proven Goertzel-spectrum concentration (clean beat ~1.0, flat ~0.0) so the
  // no-false-lock behaviour the tempo_replay gate asserts is preserved unchanged.
#ifndef K1_TEMPO_CONF_V2
  {
    const uint16_t wbin = k1_validate_winner();
    if (k1_acf_valid) {
      // Concentration of the WINNER's POINT salience (k1_conf_score = point ACF x prior) over its
      // out-of-lobe remainder. Point (not comb) so the winner's own harmonic ladder is not counted
      // as competing energy — preserves the pre-comb metronome-bar confidence (see k1_conf_score).
      const float peak = k1_conf_score(wbin);
      float out_ssq = 0.0f;
      for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
        int d = (int)i - (int)wbin; if (d < 0) d = -d;
        if (d > K1_CONF_LOBE) { float s = k1_conf_score(i); out_ssq += s * s; }
      }
      const float peak_sq = peak * peak;
      k1_confidence = peak_sq / (peak_sq + out_ssq + 1e-12f);
    } else {
      // Warm-up / flat / silence fallback: Goertzel-spectrum concentration around its own peak
      // (HOST-MEASURED tempo_replay.py: clean beat ~0.999, flat/drone ~0.0 — no false lock).
      float max_contribution = 1e-8f; uint16_t max_bin = 0;
      for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
        if (k1_tempi_smooth[i] > max_contribution) { max_contribution = k1_tempi_smooth[i]; max_bin = i; }
      }
      float out_ssq = 0.0f;
      for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
        int d = (int)i - (int)max_bin; if (d < 0) d = -d;
        if (d > K1_CONF_LOBE) out_ssq += k1_tempi_smooth[i] * k1_tempi_smooth[i];
      }
      const float peak_sq = max_contribution * max_contribution;
      k1_confidence = peak_sq / (peak_sq + out_ssq + 1e-12f);
    }
    if (k1_confidence > 1.0f) k1_confidence = 1.0f;
    if (k1_confidence < 0.0f) k1_confidence = 0.0f;
  }
#else
  // V2 confidence/lock metric (compile-gated). Replaces ONLY the confidence value + lock state;
  // winner/selection above is untouched, so Acc1/Acc2 are identical to the incumbent path.
  k1_update_confidence_v2(delta_sec);
#endif

#ifndef K1_TEMPO_FLYWHEEL_V2
  // Hard re-anchor of the open-loop phase to the freshly measured Goertzel phase. Under the
  // flywheel flag the PLL (k1_advance_phase_flywheel) OWNS the phase via a bounded onset
  // correction — a hard jump would defeat the flywheel inertia, so it is compiled out there.
  uint16_t w = k1_validate_winner();
  if ((w == bin0 || w == bin1) && k1_tempi[w].magnitude_raw > 0.005f) {
    k1_current_phase = k1_tempi[w].phase;  // re-anchor to freshly measured phase
  }
#else
  (void)bin0; (void)bin1;
#endif
}

#ifdef K1_TEMPO_FLYWHEEL_V2
// ----------------------------------------------------------------------------------------
// FLYWHEEL V2 — onset-fed soft PLL (replaces k1_advance_phase under the flag).
// ----------------------------------------------------------------------------------------
// Returns the onset PHASE measurement for this emit if the freshest novelty sample is a
// peak above the adaptive threshold, else <0 (no onset this emit). Self-contained: reads
// only the novelty already written to the ring this emit (passed as `nov_now`), peak-picked
// against the two previous emits. The adaptive floor (mean + K*MAD) is updated every emit so
// the threshold tracks the track's loudness without a new cross-module dependency.
static float k1_compute_onset_phase(float nov_now) {
  // Update adaptive floor (mean + mean-abs-dev), EMA at K1_FW_FLOOR_ALPHA (tau 0.30 s).
  const float d = nov_now - k1_fw_onset_floor;
  k1_fw_onset_floor += K1_FW_FLOOR_ALPHA * d;
  const float ad = (d < 0.0f) ? -d : d;
  k1_fw_onset_dev += K1_FW_FLOOR_ALPHA * (ad - k1_fw_onset_dev);

  float onset_phase = -1.0f;
  if (k1_fw_have_prev) {
    // 3-point local max: prev is a peak vs prev_prev and nov_now.
    const bool is_peak = (k1_fw_prev_nov >= k1_fw_prev_prev) && (k1_fw_prev_nov > nov_now);
    const float thresh = k1_fw_onset_floor + K1_FW_ONSET_K * k1_fw_onset_dev;
    if (is_peak && k1_fw_prev_nov > thresh && !k1_silence_detected) {
      // The peak (k1_fw_prev_nov) occurred ONE emit ago, so its true phase is the phase the
      // PLL held one emit back = current phase minus one emit's advance. Subtracting the lag is
      // load-bearing: without it the measured phase is biased late by one emit (~0.023 s), which
      // on a clean train is a ~0.05–0.09-beat steady-state offset the bounded Kp cannot remove.
      onset_phase = k1_fw_phase01 - k1_fw_last_adv;
      while (onset_phase < 0.0f)  onset_phase += 1.0f;
      while (onset_phase >= 1.0f) onset_phase -= 1.0f;
    }
  }
  k1_fw_prev_prev = k1_fw_prev_nov;
  k1_fw_prev_nov  = nov_now;
  k1_fw_have_prev = true;
  return onset_phase;
}

// Advance the PLL one emit: free-run the phase at run_bpm, soft-correct toward onset
// evidence (bounded), Ki-slew run_bpm within +/-K1_FW_FREQ_PULL of the winner, and emit a
// one-shot beat_tick on the upward phase wrap. Lock-gated: emits only while locked or within
// the bounded post-lock coast. `nov_now` is this emit's novelty sample (for the onset pick).
static void k1_advance_phase_flywheel(float delta_sec, float nov_now) {
  const uint16_t w = k1_validate_winner();
  const float winner_bpm = k1_tempi[w].target_bpm;

  // Prime run_bpm/phase from the first valid winner so the PLL starts on-tempo.
  if (!k1_fw_primed && winner_bpm > 1.0f) {
    k1_fw_run_bpm = winner_bpm;
    k1_fw_phase01 = 0.0f;
    k1_fw_primed = true;
  }
  if (k1_fw_run_bpm < 1.0f) k1_fw_run_bpm = (winner_bpm > 1.0f) ? winner_bpm : 1.0f;

  // The WINNER owns tempo. run_bpm tracks the winner with a tiny EMA (smooths bin hops); the
  // Ki integral term then nudges it by at most +/-K1_FW_FREQ_PULL to kill any residual
  // phase-drift, and a hard clamp guarantees the PLL can NEVER leave the winner's octave.
  k1_fw_run_bpm += (winner_bpm - k1_fw_run_bpm) * 0.10f;

  // 1. Free-run the phase.
  const float adv = (k1_fw_run_bpm / 60.0f) * delta_sec;   // beats this emit
  k1_fw_last_adv = adv;                                     // for the onset one-emit-lag correction
  k1_fw_phase01 += adv;
  k1_fw_since_tick += adv;

  // 2. Onset-fed soft correction (PLL), ONLY when locked (the lock gates trust in onsets).
  //    GOAL: drive the phase the PLL reads AT an onset to 0 (so the beat wrap coincides with
  //    the onset). If the onset is observed at phase p (wrapped to (-0.5,0.5]), then ADDING c
  //    to the accumulator makes the SAME real onset read phase (p+c) next period — so to pull p
  //    toward 0 the correction is c = -Kp*err. A persistent err also means run_bpm is fractionally
  //    off, so an integral (Ki) term slews run_bpm to eliminate the steady-state offset.
  const float onset_phase = k1_compute_onset_phase(nov_now);
  if (onset_phase >= 0.0f) { k1_fw_onset_count++; k1_fw_last_onset_phase = onset_phase; }  // diag
  if (k1_locked_v2 && onset_phase >= 0.0f) {
    float err = onset_phase;                   // observed onset phase in [0,1)
    if (err > 0.5f) err -= 1.0f;               // wrap to (-0.5, 0.5]: signed offset from beat 0
    float corr = -K1_FW_KP * err;
    if (corr >  K1_FW_MAX_CORR) corr =  K1_FW_MAX_CORR;     // inertia cap
    if (corr < -K1_FW_MAX_CORR) corr = -K1_FW_MAX_CORR;
    k1_fw_phase01 += corr;
    // Ki integral freq slew: a persistent late onset (err<0) means the clock runs slow -> speed
    // up (and vice-versa). Bounded immediately to the winner's +/-K1_FW_FREQ_PULL octave band.
    k1_fw_run_bpm += K1_FW_KI * (-err) * winner_bpm;
  }
  // Hard octave clamp (after both the winner-track EMA and the Ki slew).
  const float lo = winner_bpm * (1.0f - K1_FW_FREQ_PULL);
  const float hi = winner_bpm * (1.0f + K1_FW_FREQ_PULL);
  if (k1_fw_run_bpm < lo) k1_fw_run_bpm = lo;
  else if (k1_fw_run_bpm > hi) k1_fw_run_bpm = hi;

  // 3. Wrap phase to [0,1) and detect the upward beat boundary.
  bool wrapped = false;
  while (k1_fw_phase01 >= 1.0f) { k1_fw_phase01 -= 1.0f; wrapped = true; }
  while (k1_fw_phase01 < 0.0f)  { k1_fw_phase01 += 1.0f; }

  // 4. Coast bookkeeping: on the locked->unlocked edge, open a bounded coast window
  //    (K1_FW_COAST_BEATS beats, converted to emit-frames at run_bpm).
  if (k1_fw_was_locked && !k1_locked_v2) {
    const float beat_s = 60.0f / k1_fw_run_bpm;
    const float emits_per_beat = beat_s * K1_NOVELTY_RATE_HZ;
    float coast = emits_per_beat * (float)K1_FW_COAST_BEATS;
    if (coast > 65000.0f) coast = 65000.0f;
    k1_fw_coast_left = (uint16_t)coast;
  }
  k1_fw_was_locked = k1_locked_v2;
  if (!k1_locked_v2 && k1_fw_coast_left > 0) k1_fw_coast_left--;

  // 5. Beat boundary. A phase WRAP is a candidate beat. Count candidate beats for the V2
  //    lock-acquire guard (>=2 beats) DECOUPLED from emission — otherwise the lock (which
  //    needs >=2 beats) and emission (which needs the lock) deadlock: the free-running phase
  //    wraps regardless of lock, so beats_seen always climbs and a lock can acquire. EMISSION
  //    of the one-shot beat_tick is still lock-or-coast gated + refractory gated.
  k1_time_ms += (uint32_t)(delta_sec * 1000.0f + 0.5f);   // internal clock always advances
  k1_fw_beat_tick = false;
  if (wrapped && k1_fw_since_tick >= K1_FW_REFRACTORY) {
#ifdef K1_TEMPO_CONF_V2
    if (!k1_silence_detected && k1_v2_beats_seen < 0xFFFF) k1_v2_beats_seen++;
#endif
    const bool may_emit = (k1_locked_v2 || k1_fw_coast_left > 0) && !k1_silence_detected;
    if (may_emit) {
      k1_fw_beat_tick = true;
      k1_fw_since_tick = 0.0f;
    }
  }

  // Publish phase/tick through the SAME globals k1_build_output reads, so downstream is
  // unchanged structurally. k1_current_phase carries radian phase for phase01 mapping; map
  // the flywheel's [0,1) phase to the radian convention k1_build_output expects (0 == beat).
  k1_current_phase = k1_fw_phase01 * K1_TWO_PI;
  if (k1_current_phase > K1_PI) k1_current_phase -= K1_TWO_PI;
  k1_beat_tick = k1_fw_beat_tick;
}
#endif  // K1_TEMPO_FLYWHEEL_V2

// Free-run the winner phase between measurements; emit a debounced beat tick.
static void k1_advance_phase(float delta_sec) {
  uint16_t w = k1_validate_winner();
  float last_phase = k1_current_phase;

  k1_time_ms += (uint32_t)(delta_sec * 1000.0f + 0.5f);
  k1_current_phase += k1_tempi[w].phase_radians_per_sec * delta_sec;
  while (k1_current_phase > K1_PI)  k1_current_phase -= K1_TWO_PI;
  while (k1_current_phase < -K1_PI) k1_current_phase += K1_TWO_PI;

  k1_beat_tick = (last_phase < 0.0f && k1_current_phase >= 0.0f);
  if (k1_beat_tick) {
    float beat_period_ms = 60000.0f / k1_tempi[w].target_bpm;
    if (k1_time_ms - k1_last_tick_ms < (uint32_t)(beat_period_ms * 0.6f)) {
      k1_beat_tick = false;  // too soon, suppress
    } else {
      k1_last_tick_ms = k1_time_ms;
#ifdef K1_TEMPO_CONF_V2
      // Count observed beats for the V2 lock-acquire guard (>=2 beats before a lock can fire).
      // Read-only here; does NOT alter beat_tick/phase01 (Phase 3 owns those) — A/B unconfounded.
      if (!k1_silence_detected && k1_v2_beats_seen < 0xFFFF) k1_v2_beats_seen++;
#endif
    }
  }
}

static K1TempoEvent k1_build_output() {
  uint16_t w = k1_validate_winner();
  float conf = k1_confidence;
  if (k1_silence_detected) conf *= (1.0f - k1_silence_level);

  K1TempoEvent e;
  e.bpm = k1_tempi[w].target_bpm;
#ifdef K1_TEMPO_FLYWHEEL_V2
  // Flywheel owns the [0,1) beat phase directly (0 == beat instant); no radian round-trip.
  e.phase01 = k1_t_clamp(k1_fw_phase01, 0.0f, 1.0f);
#else
  // phase01: 0 == beat instant. beat_tick fires when k1_current_phase crosses 0
  // upward, so map radian 0 -> phase01 0 (the old (phase+PI)/2PI put the beat at 0.5).
  float p01 = (k1_current_phase >= 0.0f) ? (k1_current_phase / K1_TWO_PI)
                                         : (k1_current_phase / K1_TWO_PI + 1.0f);
  e.phase01 = k1_t_clamp(p01, 0.0f, 1.0f);
#endif
  e.confidence = k1_t_clamp(conf, 0.0f, 1.0f);
  e.beat_tick = k1_beat_tick && !k1_silence_detected;
#ifndef K1_TEMPO_CONF_V2
  e.locked = (conf > K1_LOCK_CONFIDENCE) && !k1_silence_detected;
#else
  // V2 lock comes from the hysteretic FSM (k1_update_confidence_v2); silence still force-releases
  // at the output, matching the incumbent's !silence gate and the tempo_replay silence-release case.
  e.locked = k1_locked_v2 && !k1_silence_detected;
#endif
  e.beat_strength = k1_tempi_smooth[w];
  return e;
}

// ============================================================================
// Public API
// ============================================================================

void k1_tempo_init() {
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
    float bpm = K1_TEMPO_LOW + (float)i;
    float hz = bpm / 60.0f;
    k1_tempi[i].target_bpm = bpm;
    k1_tempi[i].target_hz = hz;
    k1_tempi[i].phase_radians_per_sec = K1_TWO_PI * hz;

    // Log-Gaussian tactus prior for this bin (winner-SELECTION weight; see header).
    float l2 = log2f(bpm / K1_TACTUS_BPM_V) / K1_TACTUS_SIGMA_V;
    k1_tempo_prior[i] = expf(-0.5f * l2 * l2);
    // Broad CONFIDENCE prior (separate centre/sigma; suppresses clean-train sub/super-multiples).
    float lc = log2f(bpm / K1_CONF_BPM_V) / K1_CONF_SIGMA_V;
    k1_conf_prior[i] = expf(-0.5f * lc * lc);

    // Neighbour spacing -> adaptive block size (clamped to the ring length).
    float left_hz  = (K1_TEMPO_LOW + (float)((i == 0) ? 0 : (i - 1))) / 60.0f;
    float right_hz = (K1_TEMPO_LOW + (float)((i == K1_NUM_TEMPI - 1) ? (K1_NUM_TEMPI - 1) : (i + 1))) / 60.0f;
    float dl = fabsf(left_hz - hz);
    float dr = fabsf(right_hz - hz);
    float max_dist_hz = (dl > dr) ? dl : dr;
    if (max_dist_hz < 1e-6f) max_dist_hz = 1e-6f;
    uint32_t block = (uint32_t)(K1_NOVELTY_RATE_HZ / (max_dist_hz * 0.5f));
    if (block > K1_HISTORY_LENGTH) block = K1_HISTORY_LENGTH;
    if (block < 32U) block = 32U;
    k1_tempi[i].block_size = block;

    float w = (K1_TWO_PI * hz) / K1_NOVELTY_RATE_HZ;
    k1_tempi[i].cosine = cosf(w);
    k1_tempi[i].sine = sinf(w);
    k1_tempi[i].coeff = 2.0f * k1_tempi[i].cosine;

    k1_tempi[i].phase = 0.0f;
    k1_tempi[i].magnitude = 0.0f;
    k1_tempi[i].magnitude_raw = 0.0f;
  }
  k1_tempo_reset();
}

void k1_tempo_reset() {
  for (uint16_t i = 0; i < K1_HISTORY_LENGTH; i++) k1_spectral_curve[i] = 0.0f;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) k1_tempi_smooth[i] = 0.0f;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) k1_acf_salience[i] = 0.0f;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) k1_acf_point[i] = 0.0f;
  k1_acf_valid = false;
  k1_acf_refresh_ctr = 0;
#if K1_TEMPO_ACF_SPREAD_PROBE
  k1_acf_spread_active = false;
  k1_acf_spread_publish_pending = false;
  k1_acf_spread_cursor = 0;
  k1_acf_spread_nlag = 0;
  k1_acf_spread_lag_min = 0;
  k1_acf_publish_count = 0;
#endif
  k1_spectral_index = 0;
  k1_novelty_scale = 1.0f;
  k1_scale_count = 0;
  k1_calc_bin = 0;
  k1_winner_bin = K1_NUM_TEMPI / 2;
  k1_candidate_bin = K1_NUM_TEMPI / 2;
  k1_candidate_frames = 0;
  k1_power_sum = 0.0f;
  k1_confidence = 0.0f;
#ifdef K1_TEMPO_CONF_V2
  k1_conf_ema = 0.0f;
  k1_locked_v2 = false;
  k1_v2_updates = 0;
  k1_v2_subfloor = 0;
  k1_v2_beats_seen = 0;
  k1_v2_histShareNorm = k1_v2_prominence = k1_v2_periodicity = k1_v2_peakShare = k1_v2_quality = 0.0f;
#endif
  k1_current_phase = 0.0f;
  k1_beat_tick = false;
  k1_last_tick_ms = 0;
  k1_time_ms = 0;
#ifdef K1_TEMPO_FLYWHEEL_V2
  k1_fw_phase01 = 0.0f;
  k1_fw_run_bpm = 0.0f;
  k1_fw_beat_tick = false;
  k1_fw_onset_floor = 0.0f;
  k1_fw_onset_dev = 0.0f;
  k1_fw_prev_nov = 0.0f;
  k1_fw_prev_prev = 0.0f;
  k1_fw_have_prev = false;
  k1_fw_since_tick = 1.0f;
  k1_fw_coast_left = 0;
  k1_fw_was_locked = false;
  k1_fw_primed = false;
  k1_fw_last_adv = 0.0f;
  k1_fw_onset_count = 0;
  k1_fw_last_onset_phase = -1.0f;
#endif
  k1_silence_detected = false;
  k1_silence_level = 0.0f;
  k1_tempo_primed = false;
  k1_accum = 0.0f;
  k1_last_emit_ms = 0;
  k1_frame_ctr = 0;
#if ENABLE_TEMPO_STREAM
  k1_dbg_last_emit_ms = 0;
  k1_dbg_emit_count = 0;
  k1_dbg_last_sample = 0.0f;
  k1_dbg_last_scaled_sample = 0.0f;
  k1_dbg_last_scale = 1.0f;
  k1_dbg_silence_elapsed_us = 0;
  k1_dbg_acf_elapsed_us = 0;
  k1_dbg_update_elapsed_us = 0;
  k1_dbg_phase_elapsed_us = 0;
  k1_dbg_publish_elapsed_us = 0;
  k1_dbg_emit_elapsed_us = 0;
#endif
  K1TempoEvent empty = {};
  k1_tempo_publish(empty);
}

void k1_tempo_update(const K1AudioSnapshot& audio) {
  uint32_t now_ms = audio.frame_ms;
  float novelty = k1_t_clamp(audio.novelty, 0.0f, 1.0f);
  if (audio.silence) novelty = 0.0f;

  // Prime on first call so the downsample window starts clean.
  if (!k1_tempo_primed) {
    k1_tempo_primed = true;
    k1_last_emit_ms = now_ms;
    k1_accum = novelty;
    k1_frame_ctr = 0;
    return;
  }

  // Peak-hold downsample accumulator (preserves onset spikes).
  if (novelty > k1_accum) k1_accum = novelty;

  // Emit one novelty sample every K1_NOVELTY_DECIMATION-th AP frame by an EXACT frame
  // count. The audio loop is hardware-clocked (one chunk per call), so this yields a
  // jitter-free K1_NOVELTY_RATE_HZ feed that MATCHES the Goertzel coefficients
  // (replaces the >=20 ms wall-clock gate that produced the 120→139 scaling error).
  if (++k1_frame_ctr < K1_NOVELTY_DECIMATION) {
#ifdef K1_TEMPO_FLYWHEEL_V2
    // STALE-REPUBLISH CLEAR (flywheel only). The production path returns here WITHOUT
    // republishing, so the last-published event (with beat_tick possibly true) is re-read on
    // every non-emit AP frame — a consumer reading at the 133 Hz AP/render rate sees ONE beat
    // as ~3 ticks (host-measured raw/dedup density ratio == 3.000). The flywheel's beat_tick is
    // a true one-shot, so on the 2 non-emit frames between emits we re-publish the SAME event
    // with beat_tick FORCED false: every beat now reads exactly once regardless of read rate.
    if (k1_tempo_event.beat_tick) {
      K1TempoEvent held = k1_tempo_event;
      held.beat_tick = false;
      k1_tempo_publish(held);
    }
#endif
    return;  // not an emit frame — cheap path (still peak-holding novelty)
  }
  k1_frame_ctr = 0;

  // delta_sec (phase advance) uses the REAL wall-clock elapsed between emits.
  uint32_t elapsed = (now_ms >= k1_last_emit_ms) ? (now_ms - k1_last_emit_ms) : 0;
  float delta_sec = (float)elapsed / 1000.0f;
  if (delta_sec <= 0.0f || delta_sec > 1.0f) delta_sec = 1.0f / K1_NOVELTY_RATE_HZ;
  k1_last_emit_ms = now_ms;

  float sample = k1_accum;
  k1_accum = 0.0f;

  // Decay history then write the new sample (so the new value is undecayed).
  for (uint16_t i = 0; i < K1_HISTORY_LENGTH; i++) k1_spectral_curve[i] *= K1_NOVELTY_DECAY;
  k1_spectral_curve[k1_spectral_index] = sample;
  k1_spectral_index = (uint16_t)((k1_spectral_index + 1) % K1_HISTORY_LENGTH);

  if (++k1_scale_count >= 3) {
    k1_update_scale(0.3f);
    k1_scale_count = 0;
  }

#if ENABLE_TEMPO_STREAM
  k1_dbg_last_emit_ms = now_ms;
  if (k1_dbg_emit_count < 0xFFFFFFFFUL) k1_dbg_emit_count++;
  k1_dbg_last_sample = sample;
  k1_dbg_last_scale = k1_novelty_scale;
  k1_dbg_last_scaled_sample = sample * k1_novelty_scale;
#endif

#if ENABLE_TEMPO_STREAM
  const int64_t k1_dbg_emit_start_us = k1_tempo_diag_time_us();
  int64_t k1_dbg_stage_start_us = k1_dbg_emit_start_us;
#endif

  k1_check_silence();
#if ENABLE_TEMPO_STREAM
  int64_t k1_dbg_stage_end_us = k1_tempo_diag_time_us();
  k1_dbg_silence_elapsed_us = (uint32_t)(k1_dbg_stage_end_us - k1_dbg_stage_start_us);
  k1_dbg_stage_start_us = k1_dbg_stage_end_us;
#endif

  bool k1_acf_refresh_now = !k1_acf_valid;
#if K1_TEMPO_ACF_REFRESH_DECIMATION <= 1U
  k1_acf_refresh_now = true;
#else
  if (!k1_acf_refresh_now) {
    if (++k1_acf_refresh_ctr >= K1_TEMPO_ACF_REFRESH_DECIMATION) {
      k1_acf_refresh_ctr = 0;
      k1_acf_refresh_now = true;
    }
  }
#endif
#if K1_TEMPO_ACF_SPREAD_PROBE
  const bool k1_acf_published_now = k1_compute_acf_salience_spread(k1_acf_refresh_now);
#else
  if (k1_acf_refresh_now) {
    // Task #7: refresh the ACF winner signal BEFORE winner selection.
    // Probe builds may amortise this expensive step; production leaves the
    // decimation macro at 1 and therefore refreshes on every accepted emit.
    k1_compute_acf_salience();
  }
#endif
#if ENABLE_TEMPO_STREAM
  k1_dbg_stage_end_us = k1_tempo_diag_time_us();
  k1_dbg_acf_elapsed_us = (uint32_t)(k1_dbg_stage_end_us - k1_dbg_stage_start_us);
  k1_dbg_stage_start_us = k1_dbg_stage_end_us;
#endif

#if K1_TEMPO_ACF_SPREAD_PROBE && K1_TEMPO_ACF_SKIP_UPDATE_ON_PUBLISH
  if (!k1_acf_published_now) {
    k1_update_tempo(delta_sec);
  }
#else
  k1_update_tempo(delta_sec);
#endif
#if ENABLE_TEMPO_STREAM
  k1_dbg_stage_end_us = k1_tempo_diag_time_us();
  k1_dbg_update_elapsed_us = (uint32_t)(k1_dbg_stage_end_us - k1_dbg_stage_start_us);
  k1_dbg_stage_start_us = k1_dbg_stage_end_us;
#endif

#ifdef K1_TEMPO_FLYWHEEL_V2
  // Flywheel PLL owns phase/beat_tick (lock-gated, onset-fed). `sample` is this emit's
  // peak-held novelty — the onset peak-pick reads it directly (self-contained, no new dep).
  k1_advance_phase_flywheel(delta_sec, sample * k1_novelty_scale);
#else
  k1_advance_phase(delta_sec);
#endif
#if ENABLE_TEMPO_STREAM
  k1_dbg_stage_end_us = k1_tempo_diag_time_us();
  k1_dbg_phase_elapsed_us = (uint32_t)(k1_dbg_stage_end_us - k1_dbg_stage_start_us);
  k1_dbg_stage_start_us = k1_dbg_stage_end_us;
#endif

  k1_tempo_publish(k1_build_output());
#if ENABLE_TEMPO_STREAM
  k1_dbg_stage_end_us = k1_tempo_diag_time_us();
  k1_dbg_publish_elapsed_us = (uint32_t)(k1_dbg_stage_end_us - k1_dbg_stage_start_us);
  k1_dbg_emit_elapsed_us = (uint32_t)(k1_dbg_stage_end_us - k1_dbg_emit_start_us);
#endif
}

K1TempoEvent k1_tempo_read() {
  K1TempoEvent e;
  portENTER_CRITICAL(&k1_tempo_mux);
  e = k1_tempo_event;
  portEXIT_CRITICAL(&k1_tempo_mux);
  return e;
}

#if ENABLE_TEMPO_STREAM
K1TempoDebugSnapshot k1_tempo_debug_read() {
  K1TempoDebugSnapshot d = {};
  d.last_emit_ms = k1_dbg_last_emit_ms;
  d.emit_count = k1_dbg_emit_count;
  d.frame_ctr = k1_frame_ctr;
  d.novelty_decimation = K1_NOVELTY_DECIMATION;
  d.declared_ap_frame_hz = K1_AP_FRAME_HZ;
  d.declared_novelty_rate_hz = K1_NOVELTY_RATE_HZ;
  d.last_novelty = k1_dbg_last_sample;
  d.last_scaled_novelty = k1_dbg_last_scaled_sample;
  d.novelty_scale = k1_dbg_last_scale;
  d.acf_valid = k1_acf_valid;
  d.silence_detected = k1_silence_detected;

  const uint16_t wbin = k1_validate_winner();
  d.winner_bin = wbin;
  d.candidate_bin = k1_candidate_bin;
  d.candidate_frames = k1_candidate_frames;
  d.winner_bpm = k1_tempi[wbin].target_bpm;
  d.candidate_bpm = (k1_candidate_bin < K1_NUM_TEMPI) ? k1_tempi[k1_candidate_bin].target_bpm : 0.0f;
  d.winner_sel_score = k1_sel_score(wbin);
  d.winner_acf_comb = k1_acf_salience[wbin];
  d.winner_acf_point = k1_acf_point[wbin];
  d.winner_prior = k1_tempo_prior[wbin];
  d.winner_conf_score = k1_conf_score(wbin);

  float top1 = -1.0f;
  float top2 = -1.0f;
  uint16_t top1_bin = 0;
  uint16_t top2_bin = 0;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
    const float score = k1_sel_score(i);
    if (score > top1) {
      top2 = top1;
      top2_bin = top1_bin;
      top1 = score;
      top1_bin = i;
    } else if (score > top2) {
      top2 = score;
      top2_bin = i;
    }
  }
  d.top1_bin = top1_bin;
  d.top2_bin = top2_bin;
  d.top1_bpm = k1_tempi[top1_bin].target_bpm;
  d.top2_bpm = k1_tempi[top2_bin].target_bpm;
  d.top1_sel_score = top1;
  d.top2_sel_score = top2;

  float top_comb = -1.0f;
  float top_point = -1.0f;
  uint16_t top_comb_bin = 0;
  uint16_t top_point_bin = 0;
  for (uint16_t i = 0; i < K1_NUM_TEMPI; i++) {
    const float comb = k1_acf_salience[i];
    const float point = k1_acf_point[i];
    if (comb > top_comb) {
      top_comb = comb;
      top_comb_bin = i;
    }
    if (point > top_point) {
      top_point = point;
      top_point_bin = i;
    }
  }
  d.top_comb_bin = top_comb_bin;
  d.top_point_bin = top_point_bin;
  d.top_comb_bpm = k1_tempi[top_comb_bin].target_bpm;
  d.top_point_bpm = k1_tempi[top_point_bin].target_bpm;
  d.top_comb_score = top_comb;
  d.top_point_score = top_point;

  const uint16_t bin95 = (uint16_t)(95U - (uint16_t)K1_TEMPO_LOW);
  const uint16_t bin96 = (uint16_t)(96U - (uint16_t)K1_TEMPO_LOW);
  const uint16_t bin120 = (uint16_t)(120U - (uint16_t)K1_TEMPO_LOW);
  const uint16_t bin123 = (uint16_t)(123U - (uint16_t)K1_TEMPO_LOW);
  const uint16_t bin127 = (uint16_t)(127U - (uint16_t)K1_TEMPO_LOW);
  d.comb_95 = k1_acf_salience[bin95];
  d.comb_96 = k1_acf_salience[bin96];
  d.comb_120 = k1_acf_salience[bin120];
  d.comb_123 = k1_acf_salience[bin123];
  d.comb_127 = k1_acf_salience[bin127];
  d.point_95 = k1_acf_point[bin95];
  d.point_96 = k1_acf_point[bin96];
  d.point_120 = k1_acf_point[bin120];
  d.point_123 = k1_acf_point[bin123];
  d.point_127 = k1_acf_point[bin127];
  d.prior_95 = k1_tempo_prior[bin95];
  d.prior_96 = k1_tempo_prior[bin96];
  d.prior_120 = k1_tempo_prior[bin120];
  d.prior_123 = k1_tempo_prior[bin123];
  d.prior_127 = k1_tempo_prior[bin127];

#ifdef K1_TEMPO_CONF_V2
  d.v2_hist_share_norm = k1_v2_histShareNorm;
  d.v2_prominence = k1_v2_prominence;
  d.v2_periodicity = k1_v2_periodicity;
  d.v2_peak_share = k1_v2_peakShare;
  d.v2_quality = k1_v2_quality;
  d.v2_conf_ema = k1_conf_ema;
  d.v2_locked = k1_locked_v2;
  d.v2_beats_seen = k1_v2_beats_seen;
#endif
  d.silence_elapsed_us = k1_dbg_silence_elapsed_us;
  d.acf_elapsed_us = k1_dbg_acf_elapsed_us;
  d.update_elapsed_us = k1_dbg_update_elapsed_us;
  d.phase_elapsed_us = k1_dbg_phase_elapsed_us;
  d.publish_elapsed_us = k1_dbg_publish_elapsed_us;
  d.emit_elapsed_us = k1_dbg_emit_elapsed_us;
#if K1_TEMPO_ACF_SPREAD_PROBE
  d.acf_spread_active = k1_acf_spread_active;
  d.acf_lag_cursor = k1_acf_spread_cursor;
  d.acf_publish_count = k1_acf_publish_count;
#else
  d.acf_spread_active = false;
  d.acf_lag_cursor = 0;
  d.acf_publish_count = 0;
#endif
  return d;
}
#endif

#ifdef K1_TEMPO_HOST_TEST
// Host-test-only introspection (compile-gated by -DK1_TEMPO_HOST_TEST; NEVER compiled into
// any firmware env). Exposes the internal tempo-bank state so the regression harness can
// inspect the real bin distribution + winner + power sum + confidence on synthetic input —
// i.e. validate the lock/confidence maths off-bench instead of on the founder's hardware.
void k1_tempo_debug_dump(float* out_smooth, int n, int* winner_bin,
                         float* power_sum_out, float* confidence_out) {
  int w = 0; float mx = -1.0f;
  for (int i = 0; i < (int)K1_NUM_TEMPI; i++) {
    if (out_smooth && i < n) out_smooth[i] = k1_tempi_smooth[i];
    if (k1_tempi_smooth[i] > mx) { mx = k1_tempi_smooth[i]; w = i; }
  }
  if (winner_bin)     *winner_bin = w;
  if (power_sum_out)  *power_sum_out = k1_power_sum;
  if (confidence_out) *confidence_out = k1_confidence;
}

// Dump the RAW (pre-quartic, pre-smooth) Goertzel magnitudes so the host harness can see
// where the tempo bank's energy actually concentrates — isolating Goertzel-spectrum quality
// from the quartic/smoothing/selection stages downstream.
void k1_tempo_debug_dump_raw(float* out_raw, int n) {
  for (int i = 0; i < (int)K1_NUM_TEMPI && i < n; i++) out_raw[i] = k1_tempi[i].magnitude_raw;
}

#ifdef K1_TEMPO_FLYWHEEL_V2
// Flywheel introspection (host-test only): onset count, last onset phase, current PLL phase,
// run_bpm. Lets the calibrator see whether the onset detector fires and where the PLL settles.
void k1_tempo_debug_dump_flywheel(uint32_t* onset_count, float* last_onset_phase,
                                  float* fw_phase01, float* run_bpm) {
  if (onset_count)      *onset_count      = k1_fw_onset_count;
  if (last_onset_phase) *last_onset_phase = k1_fw_last_onset_phase;
  if (fw_phase01)       *fw_phase01       = k1_fw_phase01;
  if (run_bpm)          *run_bpm          = k1_fw_run_bpm;
}
#endif

#ifdef K1_TEMPO_CONF_V2
// V2-only: expose the last-computed raw quality components + EMA + lock-FSM state so the
// harness can dump the component distributions for calibration (LO/HI/weights/REL/FLOOR).
// histShareNorm/prominence/periodicity are the three blended cues; peakShare is the raw
// peak/Σ (pre-LO/HI mapping) used to pick LO/HI; quality is the pre-EMA blend.
void k1_tempo_debug_dump_v2(float* histShareNorm, float* prominence, float* periodicity,
                            float* peakShare, float* quality, float* conf_ema,
                            int* locked, int* beats_seen,
                            float* point_peakShare, float* point_prominence,
                            float* bg_prominence) {
  if (histShareNorm) *histShareNorm = k1_v2_histShareNorm;
  if (prominence)    *prominence    = k1_v2_prominence;
  if (periodicity)   *periodicity   = k1_v2_periodicity;
  if (peakShare)     *peakShare     = k1_v2_peakShare;
  if (quality)       *quality       = k1_v2_quality;
  if (conf_ema)      *conf_ema       = k1_conf_ema;
  if (locked)        *locked         = k1_locked_v2 ? 1 : 0;
  if (beats_seen)    *beats_seen     = (int)k1_v2_beats_seen;
#ifdef K1_TEMPO_CONF_DUMP
  if (point_peakShare)  *point_peakShare  = k1_v2_point_peakShare;
  if (point_prominence) *point_prominence = k1_v2_point_prominence;
  if (bg_prominence)    *bg_prominence    = k1_v2_bg_prominence;
#else
  if (point_peakShare)  *point_peakShare  = 0.0f;
  if (point_prominence) *point_prominence = 0.0f;
  if (bg_prominence)    *bg_prominence    = 0.0f;
#endif
}
#endif
#endif
