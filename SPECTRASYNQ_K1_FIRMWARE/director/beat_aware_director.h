#pragma once

// ============================================================================
// BeatAwareDirector — K1-native, beat-aware effect director (R1-minimal)
// ----------------------------------------------------------------------------
// Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. The existing SmartDirector remains
// the flag-OFF default and is byte-unchanged; this director is the flag-ON,
// opt-in alternative that gives the ported P4 TransitionEngine its FIRST live,
// musical caller.
//
// WHY (the verified gap): K1's real weakness is a BEAT-BLIND director on a narrow
// 6-mode whitelist (Captain 2026-06-01), not effect-body count. This module:
//   1. UN-WHITELISTS  — draws from the full light_mode_is_enabled() set
//                       (~20 enabled), round-robin, no immediate repeat.
//   2. BEAT-AWARE     — reads K1's OWN AudioSemanticState fields directly
//                       (bpm / beat_phase01 / beat_tick / tempo_locked / energy /
//                       music state). NO firmware-v3 thresholds.
//   3. MUSICAL TIMING — transitions are quantised to the beat grid, their
//                       duration is derived from the LIVE tempo (N beats), an
//                       energy/phrase gate suppresses switches in quiet/uncertain
//                       passages, and a min-dwell frequency cap stops thrashing.
//                       Low confidence => gentle time-based fallback switching.
//   4. WIRES THE ENGINE — on a switch it arms the effects queue (XFADE style,
//                       tempo-derived duration) so render_queue_xfade_overlay()
//                       drives the centre-origin TransitionEngine. SAFE transition
//                       types only (the P4 SAFE_DEFAULT set); never NUCLEAR /
//                       STARGATE / PHASE_SHIFT.
//
// STROBE LAW: this director never touches global brightness. It selects modes and
// drives spatial centre-origin transitions only. No flash/NVS writes — the queue
// owns RAM-only transition config; preset file IO stays on the loop core.
//
// THREADING: the pure decision core (bad_director_decide) is stateless and
// host-unit-testable. The firmware tick (bad_director_tick) runs on the render
// task (Core 1) at the same site as the SmartDirector tick, reading the
// portMUX-guarded audio accessors and writing only queue arm/flag state.
// ============================================================================

#include <stdint.h>

#include "config_types.h"  // NUM_MODES, light_mode_is_enabled

// --- Tunables (compile-time; conservative musical defaults) ------------------
struct BeatAwareDirectorConfig {
  bool     enabled;              // master gate (flag-ON, default OFF until opt-in)
  float    energy_gate;         // min smoothed spectral energy to allow a switch
  float    confidence_floor;    // min tempo confidence for beat-quantised switching
  uint8_t  min_dwell_beats;     // frequency cap: minimum beats held before a switch
  uint32_t min_dwell_ms;        // wall-clock floor (covers slow tempi / unlocked)
  uint32_t fallback_switch_ms;  // gentle time-based switch interval when unlocked
  uint8_t  xfade_beats;         // transition duration in beats (tempo-derived)
  uint16_t xfade_ms_min;        // clamp floor for the derived duration (ms)
  uint16_t xfade_ms_max;        // clamp ceiling for the derived duration (ms)
};

// A pure, side-effect-free snapshot of the musical inputs the decision needs.
// Populated by the firmware tick from AudioSemanticState; passed verbatim to the
// host-testable decision core so the timing logic can be replayed offline.
struct BeatAwareAudioView {
  bool     silence;            // audio snapshot silence flag
  float    energy_smooth;      // caller-smoothed spectral energy [0,1]
  float    bpm;                // live tempo (BPM); 0 if unknown
  float    tempo_confidence;   // [0,1] dominance of the winning tempo
  bool     tempo_locked;       // tempo confidence above lock and not silent
  bool     beat_tick;          // true for one tick at the beat instant
  uint8_t  music_state;        // K1MusicState cast to uint8_t
};

// Persistent decision state (one instance; lives in the .cpp). Exposed so the
// host test can drive the core deterministically.
struct BeatAwareDirectorState {
  bool     initialised;
  uint8_t  current_mode;        // mode currently shown
  uint8_t  rotation_cursor;     // round-robin cursor over enabled modes
  uint32_t last_switch_ms;      // wall-clock of the last committed switch
  uint32_t beats_since_switch;  // beats counted since the last switch
  bool     pending_switch;      // a switch is latched, waiting for the next beat
  uint32_t last_beat_ms;        // wall-clock of the last observed beat tick
};

// The decision the core hands back to the firmware tick.
struct BeatAwareDecision {
  bool     wants_switch;        // commit a switch THIS tick
  uint8_t  next_mode;           // mode to switch to (valid only if wants_switch)
  uint16_t xfade_ms;            // tempo-derived crossfade duration (clamped)
  bool     beat_quantised;      // true = fired on a beat; false = time fallback
};

// Default conservative config (few transitions, SAFE types, musical timing).
BeatAwareDirectorConfig bad_director_default_config();

// --- Pure decision core (host-unit-testable; no Arduino, no globals) ---------
// Advances `state` from `view` at `now_ms` and returns whether to switch now,
// to what mode, and the tempo-derived crossfade duration. Deterministic: same
// (state, view, now_ms) in => same decision + state mutation out.
BeatAwareDecision bad_director_decide(BeatAwareDirectorState* state,
                                      const BeatAwareAudioView& view,
                                      const BeatAwareDirectorConfig& config,
                                      uint32_t now_ms);

// Derive a beat-locked crossfade duration (ms), clamped to [min,max]. Exposed
// for the host test. bpm <= 0 returns the clamp floor.
uint16_t bad_director_xfade_ms_for_tempo(float bpm,
                                         uint8_t xfade_beats,
                                         uint16_t ms_min,
                                         uint16_t ms_max);

// Pick the next enabled mode after `from`, scanning forward, never returning
// `from` itself unless no other enabled mode exists (un-whitelist + no-repeat).
uint8_t bad_director_next_enabled_mode(uint8_t from);

#ifdef K1_EFFECT_FRAMEWORK_V1
// --- Firmware integration (render task) --------------------------------------
void bad_director_init(uint8_t initial_mode, uint32_t now_ms);
BeatAwareDirectorConfig bad_director_config();
void bad_director_set_config(const BeatAwareDirectorConfig& config);
bool bad_director_enabled();
// Mutate only the enabled flag in the live config (portMUX-safe).
// Serial toggle for eyes-on A/B; does not persist across reboot.
void bad_director_set_enabled(bool on);

// PURE read-only status accessors for serial reporting. These NEVER tick the
// director, never arm a transition, and never advance any timer/selection
// state — safe to call from the serial task while the render task ticks.
uint8_t bad_director_current_mode();      // stored current/selected mode
bool    bad_director_tempo_locked();      // live tempo lock (read-only)
float   bad_director_bpm();               // live tempo (read-only)
float   bad_director_tempo_confidence();  // live tempo confidence (read-only)

// Device-proof counters (read-only). Updated only when a switch commits.
// Used by `:beat_director status` + host/device boundary proof scripts.
// No NVS; RAM-only; never touches brightness.
uint32_t bad_director_switch_count();
uint32_t bad_director_last_switch_ms();
uint8_t  bad_director_last_switch_mode();
bool     bad_director_last_switch_beat_quantised();
bool     bad_director_last_switch_tempo_locked();  // sticky lock AT switch commit
bool     bad_director_compile_opt_in();  // true iff K1_BEAT_AWARE_DIRECTOR_V1

// One render-task tick. Reads the live audio accessors, runs the decision core,
// and — on a switch — selects a SAFE transition type, sets the tempo-derived
// xfade duration, arms the effects queue with the new primary mode in XFADE
// style, and requests a commit (the queue's frame tick + crossfade overlay then
// drive the TransitionEngine). Returns the mode that should be shown this frame.
uint8_t bad_director_tick(uint32_t now_ms);
#endif  // K1_EFFECT_FRAMEWORK_V1
