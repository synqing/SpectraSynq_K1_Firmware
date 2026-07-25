// ============================================================================
// BeatAwareDirector implementation. See beat_aware_director.h for the contract.
//
// The pure decision core (bad_director_decide / *_xfade_ms_for_tempo /
// *_next_enabled_mode) is ALWAYS compiled so the host test can replay the
// musical-timing logic offline. The firmware integration (queue + transition
// wiring) is gated under K1_EFFECT_FRAMEWORK_V1.
// ============================================================================

#include "beat_aware_director.h"

#include <math.h>

#include "k1_semantic_state.h"  // K1MusicState
#ifdef K1_EFFECT_REGISTRY_V1
#include "../effects/framework/EffectRegistry.h"  // R2-core: registry-aware enabled scan (natives reachable)
#endif

// ----------------------------------------------------------------------------
// Pure helpers (host-testable; no Arduino, no globals)
// ----------------------------------------------------------------------------

static uint16_t bad_clamp_u16(uint32_t v, uint16_t lo, uint16_t hi) {
  if (v < lo) return lo;
  if (v > hi) return hi;
  return (uint16_t)v;
}

uint8_t bad_director_next_enabled_mode(uint8_t from) {
  // UN-WHITELIST: scan the FULL enabled-mode set, not the 6-mode SmartDirector
  // whitelist. Forward, no-immediate-repeat: return the first enabled mode
  // strictly after `from`, wrapping once. Falls back to `from` only if it is the
  // sole enabled mode.
#ifdef K1_EFFECT_REGISTRY_V1
  // R2-core: scan across the REGISTRY runtime-ordinal space (NUM_MODES + the
  // appended native ordinals) so the natives rotate onto the plate. Enable is
  // read from the registry row (single source of truth). Ordinals fit a uint8_t
  // (NUM_MODES + 5 native rows). When the registry boot self-check failed, fall
  // back to the legacy scan below (fail-safe).
  if (k1::effects::framework::registry_is_healthy()) {
    const uint16_t span = k1::effects::framework::registry_mode_count();
    for (uint16_t step = 1; step <= span; step++) {
      const uint16_t candidate = (uint16_t)((from + step) % span);
      if (candidate == from) continue;
      if (k1::effects::framework::registry_mode_is_enabled(candidate)) {
        return (uint8_t)candidate;
      }
    }
    return from;
  }
#endif
  for (uint8_t step = 1; step <= NUM_MODES; step++) {
    uint8_t candidate = (uint8_t)((from + step) % NUM_MODES);
    if (candidate == from) continue;
    if (light_mode_is_enabled(candidate)) {
      return candidate;
    }
  }
  return from;
}

uint16_t bad_director_xfade_ms_for_tempo(float bpm,
                                         uint8_t xfade_beats,
                                         uint16_t ms_min,
                                         uint16_t ms_max) {
  // MUSICAL DURATION: a crossfade spans N beats of the LIVE tempo, NOT a fixed
  // 500/1500/4000 ms tier. ms_per_beat = 60000 / bpm. Unknown tempo => floor.
  if (ms_max < ms_min) ms_max = ms_min;
  if (!(bpm > 1.0f) || !isfinite(bpm) || xfade_beats == 0) {
    return ms_min;
  }
  const float ms_per_beat = 60000.0f / bpm;
  const float span = ms_per_beat * (float)xfade_beats;
  if (!isfinite(span) || span <= 0.0f) {
    return ms_min;
  }
  return bad_clamp_u16((uint32_t)(span + 0.5f), ms_min, ms_max);
}

BeatAwareDirectorConfig bad_director_default_config() {
  // Conservative musical defaults: few transitions, long dwell, SAFE feel.
  BeatAwareDirectorConfig c;
  c.enabled            = false;   // opt-in even under the flag (default OFF)
  c.energy_gate        = 0.06f;   // suppress switches in quiet passages
  c.confidence_floor   = 0.45f;   // beat-quantise only when tempo is trustworthy
  c.min_dwell_beats    = 32;      // ~8 bars at 4/4 — never thrash
  c.min_dwell_ms       = 6000UL;  // wall-clock floor (slow tempi / unlocked)
  c.fallback_switch_ms = 20000UL; // gentle time-based switch when unlocked
  c.xfade_beats        = 2;       // two-beat crossfade rides the groove
  c.xfade_ms_min       = 200;     // within K1_QUEUE_XFADE_MS range [100,3000]
  c.xfade_ms_max       = 1600;
  return c;
}

// ----------------------------------------------------------------------------
// Pure decision core
// ----------------------------------------------------------------------------
//
// Two-stage timing so a switch always lands ON a musical boundary:
//   1) GATE  — energy/phrase gate + min-dwell frequency cap decide whether the
//              director is even *allowed* to want a switch right now.
//   2) FIRE  — when allowed AND tempo is locked/confident, LATCH a pending
//              switch and fire it on the NEXT beat tick (beat-quantised). When
//              tempo is NOT trustworthy, fall back to a gentle time-based switch
//              after fallback_switch_ms (no beat available to quantise to).
//
// The min-dwell cap is the AND of a beat count and a wall-clock floor, so it is
// safe at any tempo (and when unlocked, where beats_since_switch never advances).

BeatAwareDecision bad_director_decide(BeatAwareDirectorState* state,
                                      const BeatAwareAudioView& view,
                                      const BeatAwareDirectorConfig& config,
                                      uint32_t now_ms) {
  BeatAwareDecision decision;
  decision.wants_switch   = false;
  decision.next_mode      = (state != nullptr) ? state->current_mode : (uint8_t)0;
  decision.xfade_ms       = config.xfade_ms_min;
  decision.beat_quantised = false;
  if (state == nullptr) {
    return decision;
  }

  if (!state->initialised) {
    state->current_mode      = state->current_mode;  // caller seeds via init
    state->rotation_cursor   = state->current_mode;
    state->last_switch_ms    = now_ms;
    state->beats_since_switch = 0;
    state->pending_switch    = false;
    state->last_beat_ms      = now_ms;
    state->initialised       = true;
  }

  // Count beats since the last switch (drives the beat-based dwell cap). Only a
  // fresh beat tick advances it, and only while tempo is locked.
  const bool fresh_beat = view.beat_tick && view.tempo_locked;
  if (fresh_beat) {
    if (state->beats_since_switch < 0xFFFFFFFFUL) state->beats_since_switch++;
    state->last_beat_ms = now_ms;
  }

  const uint32_t dwell_ms = (now_ms >= state->last_switch_ms)
                            ? (now_ms - state->last_switch_ms) : 0u;

  // ── Stage 1: GATE ────────────────────────────────────────────────────────
  // PHRASE/ENERGY gate: never transition during silence or a quiet/uncertain
  // passage — those are the moments a switch reads as a glitch, not a cue.
  const bool energy_ok = !view.silence && (view.energy_smooth >= config.energy_gate);
  // FREQUENCY CAP (min dwell): both the wall-clock floor AND the beat count must
  // be satisfied. The beat count is only meaningful when locked; the wall-clock
  // floor covers the unlocked path.
  const bool dwell_ms_ok    = dwell_ms >= config.min_dwell_ms;
  const bool dwell_beats_ok = state->beats_since_switch >= config.min_dwell_beats;
  const bool may_switch     = energy_ok && dwell_ms_ok;

  // ── Stage 2: FIRE ────────────────────────────────────────────────────────
  const bool tempo_trustworthy =
      view.tempo_locked && (view.tempo_confidence >= config.confidence_floor);

  if (!may_switch) {
    // Gate closed — drop any latched intent so we re-evaluate cleanly.
    state->pending_switch = false;
    return decision;
  }

  if (tempo_trustworthy) {
    // BEAT-QUANTISED path. Require the beat dwell too, then latch and wait for
    // the next beat instant so the cut lands exactly on the groove.
    if (!dwell_beats_ok) {
      return decision;
    }
    if (!state->pending_switch) {
      state->pending_switch = true;  // latch; fire on the next beat
      return decision;
    }
    if (!fresh_beat) {
      return decision;  // hold the latch until a beat instant arrives
    }
    // Fire on the beat.
    decision.next_mode      = bad_director_next_enabled_mode(state->current_mode);
    decision.xfade_ms       = bad_director_xfade_ms_for_tempo(
                                  view.bpm, config.xfade_beats,
                                  config.xfade_ms_min, config.xfade_ms_max);
    decision.beat_quantised = true;
    decision.wants_switch   = (decision.next_mode != state->current_mode);
  } else {
    // FALLBACK: tempo not trustworthy — gentle time-based switch. No beat to
    // quantise to, so use a long wall-clock interval and a fixed gentle xfade.
    if (dwell_ms < config.fallback_switch_ms) {
      return decision;
    }
    decision.next_mode      = bad_director_next_enabled_mode(state->current_mode);
    decision.xfade_ms       = config.xfade_ms_min;  // gentle, tempo unknown
    decision.beat_quantised = false;
    decision.wants_switch   = (decision.next_mode != state->current_mode);
  }

  if (decision.wants_switch) {
    state->current_mode       = decision.next_mode;
    state->rotation_cursor    = decision.next_mode;
    state->last_switch_ms     = now_ms;
    state->beats_since_switch = 0;
    state->pending_switch     = false;
  } else {
    state->pending_switch = false;
  }
  return decision;
}

// ----------------------------------------------------------------------------
// Firmware integration (render task) — gated
// ----------------------------------------------------------------------------
#ifdef K1_EFFECT_FRAMEWORK_V1

#include <Arduino.h>

#include "globals.h"  // CONFIG, portMUX
#include "k1_audio_snapshot.h"
#include "k1_effect_queue.h"
#include "TransitionOverlay.h"
#include "TransitionTypes.h"

static BeatAwareDirectorConfig g_bad_config = bad_director_default_config();
static BeatAwareDirectorState  g_bad_state  = {};
static float                   g_bad_energy_smooth = 0.0f;
static uint32_t                g_bad_last_tick_ms  = 0;
static uint8_t                 g_bad_safe_cursor   = 0;  // SAFE transition rotation
static portMUX_TYPE            g_bad_config_mux    = portMUX_INITIALIZER_UNLOCKED;

// Proof telemetry (RAM-only; updated on switch commit; serial-readable).
static uint32_t g_bad_switch_count           = 0;
static uint32_t g_bad_last_switch_ms         = 0;
static uint8_t  g_bad_last_switch_mode       = 0;
static bool     g_bad_last_switch_beat_q     = false;

void bad_director_init(uint8_t initial_mode, uint32_t now_ms) {
  g_bad_state = {};
  g_bad_state.current_mode    = initial_mode;
  g_bad_state.rotation_cursor = initial_mode;
  g_bad_state.last_switch_ms  = now_ms;
  g_bad_state.last_beat_ms    = now_ms;
  g_bad_state.initialised     = true;
  g_bad_energy_smooth = 0.0f;
  g_bad_last_tick_ms  = now_ms;
  g_bad_safe_cursor   = 0;
  g_bad_switch_count       = 0;
  g_bad_last_switch_ms     = 0;
  g_bad_last_switch_mode   = initial_mode;
  g_bad_last_switch_beat_q = false;
}

BeatAwareDirectorConfig bad_director_config() {
  BeatAwareDirectorConfig c;
  portENTER_CRITICAL(&g_bad_config_mux);
  c = g_bad_config;
  portEXIT_CRITICAL(&g_bad_config_mux);
  return c;
}

void bad_director_set_config(const BeatAwareDirectorConfig& config) {
  portENTER_CRITICAL(&g_bad_config_mux);
  g_bad_config = config;
  portEXIT_CRITICAL(&g_bad_config_mux);
}

bool bad_director_enabled() { return bad_director_config().enabled; }

void bad_director_set_enabled(bool on) {
  BeatAwareDirectorConfig c = bad_director_config();
  c.enabled = on;
  bad_director_set_config(c);
}

// --- PURE read-only status accessors -----------------------------------------
// These read state only; they never tick the director, arm a transition, or
// advance a timer. Safe to call from the serial task.
uint8_t bad_director_current_mode() {
  // Stored selected mode once the director has been initialised; before that,
  // the director shows the configured lightshow mode.
  return g_bad_state.initialised ? g_bad_state.current_mode
                                 : (uint8_t)CONFIG.LIGHTSHOW_MODE;
}

bool bad_director_tempo_locked() {
  AudioSemanticState sem = {};
#ifdef K1_SEMANTIC_STATE
  audio_semantic_read(&sem);
#endif
  return sem.tempo_locked;
}

float bad_director_bpm() {
  AudioSemanticState sem = {};
#ifdef K1_SEMANTIC_STATE
  audio_semantic_read(&sem);
#endif
  return sem.bpm;
}

float bad_director_tempo_confidence() {
  AudioSemanticState sem = {};
#ifdef K1_SEMANTIC_STATE
  audio_semantic_read(&sem);
#endif
  return sem.tempo_confidence;
}

uint32_t bad_director_switch_count() { return g_bad_switch_count; }
uint32_t bad_director_last_switch_ms() { return g_bad_last_switch_ms; }
uint8_t  bad_director_last_switch_mode() { return g_bad_last_switch_mode; }
bool     bad_director_last_switch_beat_quantised() {
  return g_bad_last_switch_beat_q;
}
bool bad_director_compile_opt_in() {
#ifdef K1_BEAT_AWARE_DIRECTOR_V1
  return true;
#else
  return false;
#endif
}

uint8_t bad_director_tick(uint32_t now_ms) {
  BeatAwareDirectorConfig config = bad_director_config();
  if (!config.enabled) {
    return CONFIG.LIGHTSHOW_MODE;
  }

  if (!g_bad_state.initialised) {
    bad_director_init(CONFIG.LIGHTSHOW_MODE, now_ms);
  }

  // Read K1's OWN audio surface directly — no firmware-v3 thresholds.
  K1AudioSnapshot audio = k1_audio_snapshot_read();

  // Smooth spectral energy for the phrase/energy gate (frame-rate-independent
  // first-order EMA, ~180 ms tau — mirrors SmartDirector's energy smoothing).
  const uint32_t dt_ms = (g_bad_last_tick_ms == 0 || now_ms < g_bad_last_tick_ms)
                         ? 0u : (now_ms - g_bad_last_tick_ms);
  g_bad_last_tick_ms = now_ms;
  const float tau_ms = 180.0f;
  const float alpha = (tau_ms <= 0.0f) ? 1.0f
                      : (float)dt_ms / (tau_ms + (float)dt_ms);
  g_bad_energy_smooth += (audio.spectral_energy - g_bad_energy_smooth) * alpha;

  AudioSemanticState sem = {};
#ifdef K1_SEMANTIC_STATE
  audio_semantic_read(&sem);
#endif

  BeatAwareAudioView view;
  view.silence          = audio.silence;
  view.energy_smooth    = g_bad_energy_smooth;
  view.bpm              = sem.bpm;
  view.tempo_confidence = sem.tempo_confidence;
  view.tempo_locked     = sem.tempo_locked;
  view.beat_tick        = sem.beat_tick;
  view.music_state      = (uint8_t)K1_MUSIC_STEADY;  // reserved for future bias

  BeatAwareDecision decision =
      bad_director_decide(&g_bad_state, view, config, now_ms);

  if (decision.wants_switch) {
    using namespace k1::effects::framework;

    // Proof telemetry first (RAM-only) so serial status can confirm beat-q.
    g_bad_switch_count++;
    g_bad_last_switch_ms     = now_ms;
    g_bad_last_switch_mode   = decision.next_mode;
    g_bad_last_switch_beat_q = decision.beat_quantised;

    // SAFE transition type only (never NUCLEAR/STARGATE/PHASE_SHIFT). Rotate the
    // P4 SAFE_DEFAULT set so successive switches feel varied but stay spatial.
    const TransitionType type =
        kSafeDefaultTransitions[g_bad_safe_cursor % kSafeDefaultCount];
    g_bad_safe_cursor++;
    transitionStartChannel(false, type, decision.xfade_ms);

    // MUSICAL DURATION + XFADE style: tempo-derived crossfade through the queue,
    // which routes render_queue_xfade_overlay() into the TransitionEngine.
    k1_queue_set_xfade_ms((uint32_t)decision.xfade_ms);
    k1_queue_set_transition_style(K1_QUEUE_TRANSITION_XFADE);

    // Arm the primary channel's pending preset with the new mode and commit.
    // RAM-only arm/flag writes (no flash); Core 1 frame tick lands the swap and
    // starts the crossfade at the next frame boundary.
    K1ChannelPreset* pending = k1_queue_arm_begin(false);
    if (pending != nullptr) {
      pending->lightshow_mode = decision.next_mode;
      k1_queue_request_commit(true, now_ms);
    }
  }

  return g_bad_state.current_mode;
}

#endif  // K1_EFFECT_FRAMEWORK_V1
