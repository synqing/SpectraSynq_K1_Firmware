#pragma once

// sb_effect_queue.h
// ============================================================================
// Effects Queuing + Preset Slots (Captain-approved spec 2026-06-11,
// _scratch/effects-queue/01-spec.md).
//
// THREADING CONTRACT (mirrors the mode_transition_queued precedent):
//   - The serial/hotkey side (AP loop core) ONLY writes pending/arm state,
//     transition config and the commit-request flag. It NEVER touches the live
//     per-channel fields for queued operations.
//   - Core 1 (render task) applies committed state at the frame boundary via
//     sb_effect_queue_frame_tick(), called before channel construction in
//     led_thread(). Mode/palette/field swaps never happen mid-frame.
//   - Preset-slot file IO (LittleFS) runs on the serial/loop core only; the
//     render task reads RAM state exclusively.
//
// TRANSITIONS:
//   - DIP (default): per-channel scalar ramps 1 -> 0 over dip_ms, the full
//     15-field swap lands at black, INSTANT relight (drop-cut aesthetic).
//     The scalar COMPOSES with drop_cut_scale by multiplication at the same
//     application points (apply_brightness / apply_brightness_secondary in
//     led_utilities.h) — it never replaces or reorders existing factors.
//     Monotonic down + instant up only: strobe-safe by construction.
//   - CROSSFADE: the fading channel renders twice (outgoing live state +
//     incoming state on a dedicated static TRANSITION SCRATCH block), blended
//     equal-power (sqrt ramps) over xfade_ms. On completion the scratch state
//     is copied into the live channel block at the frame boundary.
// ============================================================================

#include <stdint.h>
#include <stddef.h>

#include "globals.h"  // CRGB16, ChannelEffectState, CONFIG, SECONDARY_*, NATIVE_RESOLUTION

// --- Transition styles / commit quantise -------------------------------------
#define SB_QUEUE_TRANSITION_DIP 0
#define SB_QUEUE_TRANSITION_XFADE 1

#define SB_QUEUE_QUANTISE_OFF 0
#define SB_QUEUE_QUANTISE_BEAT 1

// SNAPPY defaults (spec §2); serial-tunable within the spec ranges.
#define SB_QUEUE_DIP_MS_DEFAULT 120U
#define SB_QUEUE_DIP_MS_MIN 60U
#define SB_QUEUE_DIP_MS_MAX 1000U
#define SB_QUEUE_XFADE_MS_DEFAULT 400U
#define SB_QUEUE_XFADE_MS_MIN 100U
#define SB_QUEUE_XFADE_MS_MAX 3000U
#define SB_QUEUE_QUANTISE_TIMEOUT_MS 2000U

// --- Preset slot file constants (spec §3, cal_profile.bin pattern) -----------
#define SB_PRESET_SLOTS_FILE "/PRESETS_V1.BIN"
#define SB_PRESET_SLOTS_MAGIC 0x53504253UL  // 'SBPS' little-endian
#define SB_PRESET_SLOTS_VERSION 1U
#define SB_PRESET_SLOT_COUNT 10

// --- The 15 per-channel visual fields (recon §1 list; NO audio/cal fields) ---
struct SBChannelPreset {
  uint8_t lightshow_mode;       //  1 CONFIG.LIGHTSHOW_MODE      / SECONDARY_LIGHTSHOW_MODE
  bool    mirror_enabled;       //  2 CONFIG.MIRROR_ENABLED      / SECONDARY_MIRROR_ENABLED
  float   photons;              //  3 CONFIG.PHOTONS             / SECONDARY_PHOTONS
  float   chroma;               //  4 CONFIG.CHROMA              / SECONDARY_CHROMA
  float   mood;                 //  5 CONFIG.MOOD                / SECONDARY_MOOD
  float   saturation;           //  6 CONFIG.SATURATION          / SECONDARY_SATURATION
  float   prism_count;          //  7 CONFIG.PRISM_COUNT         / SECONDARY_PRISM_COUNT
  float   incandescent_filter;  //  8 CONFIG.INCANDESCENT_FILTER / SECONDARY_INCANDESCENT_FILTER
  bool    incandescent_mode;    //  9 CONFIG.INCANDESCENT_MODE   / SECONDARY_INCANDESCENT_MODE
  bool    base_coat;            // 10 CONFIG.BASE_COAT           / SECONDARY_BASE_COAT
  bool    reverse_order;        // 11 CONFIG.REVERSE_ORDER       / SECONDARY_REVERSE_ORDER
  bool    auto_color_shift;     // 12 CONFIG.AUTO_COLOR_SHIFT    / SECONDARY_AUTO_COLOR_SHIFT
  float   base_coat_intensity;  // 13 CONFIG.BASE_COAT_INTENSITY / SECONDARY_BASE_COAT_INTENSITY
  uint8_t palette_index;        // 14 CONFIG.PALETTE_INDEX       / SECONDARY_PALETTE_INDEX
  bool    palette_mode_enabled; // 15 CONFIG.PALETTE_MODE_ENABLED/ SECONDARY_PALETTE_MODE_ENABLED
};

// --- Crossfade TRANSITION SCRATCH block ---------------------------------------
// The incoming effect during a crossfade renders on this dedicated per-channel
// state (never the live block). One instance per channel so a `\` scene-flip
// (both channels committed in the same frame) can crossfade both at once.
struct SBQueueXfadeScratch {
  CRGB16   history[NATIVE_RESOLUTION];  // incoming channel history buffer
  CRGB16   wf_fast_last_color;
  float    wf_fast_peak_scaled_last;
  float    wf_fast_shift_accum;
  uint32_t wf_fast_last_frame_ms;
  CRGB16   wf_last_color;
  float    wf_peak_scaled_last;
  float    wf_shift_accum;
  uint32_t wf_last_frame_ms;
  CRGB16   wf_hybrid_last_color;
  float    wf_hybrid_peak_scaled_last;
  float    wf_hybrid_shift_accum;
  uint32_t wf_hybrid_last_frame_ms;
  SQ15x16  vu_level_smooth;
  SQ15x16  vu_max_level;
  ChannelEffectState effect;
};

// =============================================================================
// Serial-side API (AP loop core — arms/flags only, never live-field writes)
// =============================================================================

bool sb_queue_mode_enabled();
// Toggling queue mode OFF discards any armed-but-uncommitted state.
void sb_queue_set_mode_enabled(bool on);

// Snapshot the live 15 fields of a channel (primary = CONFIG fields,
// secondary = SECONDARY_* globals).
SBChannelPreset sb_queue_capture_live(bool secondary);

// Begin/continue arming a channel: on first arm the pending struct is seeded
// from the live channel, so relative stepping starts from reality. Returns the
// mutable pending preset for the caller to step mode/palette/etc.
SBChannelPreset* sb_queue_arm_begin(bool secondary);

// Overwrite the whole pending struct (slot load / slot arm).
void sb_queue_arm_preset(bool secondary, const SBChannelPreset& preset);

bool sb_queue_channel_armed(bool secondary);
bool sb_queue_any_armed();
void sb_queue_disarm_all();

// Request a commit of ALL armed channels.
//   cued=true  ('\' hotkey / :commit): honours commit_quantise and the
//              configured transition style.
//   cued=false (queue-mode-OFF immediate path): commits on the next frame
//              boundary and always uses the DIP transition (spec §1).
void sb_queue_request_commit(bool cued, uint32_t now_ms);
bool sb_queue_commit_pending();  // true while a commit request awaits Core 1

// Transition configuration (RAM-only this slice; CONFIG layout untouched).
uint8_t  sb_queue_transition_style();
void     sb_queue_set_transition_style(uint8_t style);
uint16_t sb_queue_dip_ms();
bool     sb_queue_set_dip_ms(uint32_t ms);     // false = out of spec range
uint16_t sb_queue_xfade_ms();
bool     sb_queue_set_xfade_ms(uint32_t ms);   // false = out of spec range
uint8_t  sb_queue_commit_quantise();
void     sb_queue_set_commit_quantise(uint8_t mode);

// --- Preset slots (file IO on the loop core only) ----------------------------
bool sb_preset_slot_save(uint8_t slot_index, bool from_secondary);
bool sb_preset_slot_get(uint8_t slot_index, SBChannelPreset* out);
bool sb_preset_slot_valid(uint8_t slot_index);

// =============================================================================
// Core-1 API (render task only)
// =============================================================================

// Frame-boundary tick: consumes commit requests (with beat-quantise hold via
// sb_tempo_read() + timeout), starts transitions, advances dip scalars, lands
// dip swaps at black and finalises crossfades (scratch -> live copy).
void sb_effect_queue_frame_tick(uint32_t now_ms);

// Crossfade overlay hooks, called from the render loop after the outgoing
// channel render. begin() returns false when the channel is not crossfading;
// on true it temp-applies the incoming fields to the live param sources,
// reports the equal-power gains + incoming mode/prism, and the caller renders
// the incoming pass on the scratch block. end() restores the outgoing fields.
bool sb_queue_xfade_overlay_begin(bool secondary, uint32_t now_ms,
                                  float* gain_out, float* gain_in,
                                  uint8_t* incoming_mode, float* incoming_prism);
void sb_queue_xfade_overlay_end(bool secondary);
SBQueueXfadeScratch* sb_queue_xfade_scratch(bool secondary);

// Shared outgoing-frame snapshot buffer for the crossfade blend. Safe to share
// between channels: the primary and secondary passes run sequentially and each
// blend completes within its own pass.
extern CRGB16 sb_queue_xfade_out_buf[NATIVE_RESOLUTION];

// Per-channel DIP transition scalar (1.0 when idle). Multiplied into the final
// brightness at the same application points as drop_cut_scale — composition by
// multiplication, never replacement.
extern float sb_queue_transition_scale_primary;
extern float sb_queue_transition_scale_secondary;
