// k1_effect_queue.cpp
// ============================================================================
// Effects Queuing + Preset Slots implementation (spec 2026-06-11).
//
// Threading: see k1_effect_queue.h. Serial side writes pending/arm state and
// the commit-request flag; k1_effect_queue_frame_tick() (Core 1, frame
// boundary) is the ONLY place committed values land on the live per-channel
// fields. This copies the existing tolerated cross-core pattern
// (mode_destination -> mode_transition_queued in globals.h).
//
// Core-0 isolation: this module never touches the audio pipeline. Its only
// audio-adjacent call is k1_tempo_read(), which is documented any-core safe
// (value copy under portMUX) and is used purely to HOLD a commit until the
// next beat tick when commit_quantise=beat.
// ============================================================================

#include "k1_effect_queue.h"

#include <Arduino.h>
#include <math.h>
#include <string.h>

#include <FS.h>
#include <LittleFS.h>

#include "Palettes.h"   // gGradientPaletteCount (slot-load palette clamp)
#include "k1_tempo.h"   // k1_tempo_read() — any-core-safe value copy
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h" // registry_sanitize_persisted() (R2b NVS sanitiser)
#endif

// bridge_fs.h (single-TU .ino header): queue the existing delayed CONFIG save
// after a committed PRIMARY change, mirroring the hotkey behaviour.
void save_config_delayed();

// --- Dip scalars (composed with drop_cut_scale in led_utilities.h) -----------
float k1_queue_transition_scale_primary = 1.0f;
float k1_queue_transition_scale_secondary = 1.0f;

CRGB16 k1_queue_xfade_out_buf[NATIVE_RESOLUTION];

namespace {

constexpr uint8_t K1Q_PRIMARY = 0;
constexpr uint8_t K1Q_SECONDARY = 1;

inline uint8_t channel_index(bool secondary) { return secondary ? K1Q_SECONDARY : K1Q_PRIMARY; }

// --- Pending (armed) state per channel (spec §1 state model) ------------------
struct ChannelPendingState {
  bool armed;
  K1ChannelPreset preset;
};

ChannelPendingState g_pending[2] = {};

bool g_queue_mode = false;  // RAM-only; not persisted (spec §5)

// --- Transition configuration (RAM-only this slice; spec §5) ------------------
uint8_t  g_transition_style = K1_QUEUE_TRANSITION_DIP;
uint16_t g_dip_ms = K1_QUEUE_DIP_MS_DEFAULT;
uint16_t g_xfade_ms = K1_QUEUE_XFADE_MS_DEFAULT;
uint8_t  g_quantise = K1_QUEUE_QUANTISE_OFF;

// --- Commit request (serial writes, Core 1 consumes) --------------------------
// Plain-store ordering matches the existing mode_transition_queued tolerance:
// the serial side fully writes g_pending BEFORE raising the request flag.
volatile bool g_commit_request = false;
volatile bool g_commit_cued = false;       // true = honour quantise + style
volatile uint32_t g_commit_request_ms = 0;

// --- Per-channel transition runtime (Core 1 only) ------------------------------
enum K1QueueTransitionPhase : uint8_t {
  K1Q_IDLE = 0,
  K1Q_DIP_DOWN,  // scalar ramps 1 -> 0 (monotonic); swap at black; instant relight
  K1Q_XFADE,     // dual render + equal-power blend; scratch -> live on completion
};

struct ChannelTransition {
  K1QueueTransitionPhase phase;
  K1ChannelPreset target;
  uint32_t start_ms;
};

ChannelTransition g_transition[2] = {};

K1QueueXfadeScratch g_xfade_scratch[2];

// Crossfade overlay temp-apply bookkeeping (Core 1 render scope only).
K1ChannelPreset g_xfade_saved_live[2];
bool g_xfade_overlay_applied[2] = { false, false };

// --- Field application helpers -------------------------------------------------

// Write the 15 fields to the live channel WITHOUT persistence side effects
// (used both by the frame-boundary commit and the crossfade temp-apply).
void apply_preset_fields(bool secondary, const K1ChannelPreset& p) {
  if (!secondary) {
    CONFIG.LIGHTSHOW_MODE       = p.lightshow_mode;
    CONFIG.MIRROR_ENABLED       = p.mirror_enabled;
    CONFIG.PHOTONS              = p.photons;
    CONFIG.CHROMA               = p.chroma;
    CONFIG.MOOD                 = p.mood;
    CONFIG.SATURATION           = p.saturation;
    CONFIG.PRISM_COUNT          = p.prism_count;
    CONFIG.INCANDESCENT_FILTER  = p.incandescent_filter;
    CONFIG.INCANDESCENT_MODE    = p.incandescent_mode;
    CONFIG.BASE_COAT            = p.base_coat;
    CONFIG.REVERSE_ORDER        = p.reverse_order;
    CONFIG.AUTO_COLOR_SHIFT     = p.auto_color_shift;
    CONFIG.BASE_COAT_INTENSITY  = p.base_coat_intensity;
    CONFIG.PALETTE_INDEX        = p.palette_index;
    CONFIG.PALETTE_MODE_ENABLED = p.palette_mode_enabled;
  } else {
    SECONDARY_LIGHTSHOW_MODE       = p.lightshow_mode;
    SECONDARY_MIRROR_ENABLED       = p.mirror_enabled;
    SECONDARY_PHOTONS              = p.photons;
    SECONDARY_CHROMA               = p.chroma;
    SECONDARY_MOOD                 = p.mood;
    SECONDARY_SATURATION           = p.saturation;
    SECONDARY_PRISM_COUNT          = p.prism_count;
    SECONDARY_INCANDESCENT_FILTER  = p.incandescent_filter;
    SECONDARY_INCANDESCENT_MODE    = p.incandescent_mode;
    SECONDARY_BASE_COAT            = p.base_coat;
    SECONDARY_REVERSE_ORDER        = p.reverse_order;
    SECONDARY_AUTO_COLOR_SHIFT     = p.auto_color_shift;
    SECONDARY_BASE_COAT_INTENSITY  = p.base_coat_intensity;
    SECONDARY_PALETTE_INDEX        = p.palette_index;
    SECONDARY_PALETTE_MODE_ENABLED = p.palette_mode_enabled;
  }
}

// Frame-boundary commit application: fields + persistence parity with the
// existing hotkeys (primary edits queue the delayed save; secondary edits are
// never persisted — unchanged behaviour, recon §3).
void apply_preset_live(bool secondary, const K1ChannelPreset& p) {
  apply_preset_fields(secondary, p);
  if (!secondary) {
    save_config_delayed();
  }
}

void reset_xfade_scratch(uint8_t ch) {
  memset(&g_xfade_scratch[ch], 0, sizeof(K1QueueXfadeScratch));
  // Mirror the live ChannelEffectState boot init (globals.h): everything 0
  // except vu_dot_max_level = 0.01. Effects self-heal from zeroed state
  // (last_ms==0 first-frame convention, channel_effect_state.h).
  g_xfade_scratch[ch].effect.vu_dot_max_level = SQ15x16(0.01f);
  g_xfade_scratch[ch].vu_max_level = SQ15x16(0.01f);
}

// Crossfade completion: the incoming state becomes the live channel state.
// Runs at the frame boundary (Core 1) only.
void finish_xfade_now(uint8_t ch, bool apply_fields_now) {
  ChannelTransition& tr = g_transition[ch];
  const bool secondary = (ch == K1Q_SECONDARY);
  if (apply_fields_now) {
    apply_preset_live(secondary, tr.target);
  }
  K1QueueXfadeScratch& sc = g_xfade_scratch[ch];
  if (!secondary) {
    memcpy(leds_16_prev, sc.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    waveform_fast_last_color_primary = sc.wf_fast_last_color;
    waveform_fast_peak_scaled_last_primary = sc.wf_fast_peak_scaled_last;
    waveform_fast_shift_accum_primary = sc.wf_fast_shift_accum;
    waveform_fast_last_frame_ms_primary = sc.wf_fast_last_frame_ms;
    waveform_last_color_primary = sc.wf_last_color;
    waveform_peak_scaled_last_primary = sc.wf_peak_scaled_last;
    waveform_shift_accum_primary = sc.wf_shift_accum;
    waveform_last_frame_ms_primary = sc.wf_last_frame_ms;
    waveform_hybrid_last_color_primary = sc.wf_hybrid_last_color;
    waveform_hybrid_peak_scaled_last_primary = sc.wf_hybrid_peak_scaled_last;
    waveform_hybrid_shift_accum_primary = sc.wf_hybrid_shift_accum;
    waveform_hybrid_last_frame_ms_primary = sc.wf_hybrid_last_frame_ms;
    vu_level_smooth_primary = sc.vu_level_smooth;
    vu_max_level_primary = sc.vu_max_level;
    effect_state_primary = sc.effect;
  } else {
    memcpy(leds_16_prev_secondary, sc.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    waveform_fast_last_color_secondary = sc.wf_fast_last_color;
    waveform_fast_peak_scaled_last_secondary = sc.wf_fast_peak_scaled_last;
    waveform_fast_shift_accum_secondary = sc.wf_fast_shift_accum;
    waveform_fast_last_frame_ms_secondary = sc.wf_fast_last_frame_ms;
    waveform_last_color_secondary = sc.wf_last_color;
    waveform_peak_scaled_last_secondary = sc.wf_peak_scaled_last;
    waveform_shift_accum_secondary = sc.wf_shift_accum;
    waveform_last_frame_ms_secondary = sc.wf_last_frame_ms;
    waveform_hybrid_last_color_secondary = sc.wf_hybrid_last_color;
    waveform_hybrid_peak_scaled_last_secondary = sc.wf_hybrid_peak_scaled_last;
    waveform_hybrid_shift_accum_secondary = sc.wf_hybrid_shift_accum;
    waveform_hybrid_last_frame_ms_secondary = sc.wf_hybrid_last_frame_ms;
    vu_level_smooth_secondary = sc.vu_level_smooth;
    vu_max_level_secondary = sc.vu_max_level;
    effect_state_secondary = sc.effect;
  }
  tr.phase = K1Q_IDLE;
}

// Start (or merge into) a transition for one channel.
void start_transition(uint8_t ch, const K1ChannelPreset& preset, uint32_t now_ms, bool cued) {
  ChannelTransition& tr = g_transition[ch];

  if (tr.phase == K1Q_DIP_DOWN) {
    // Latest-wins WITHOUT oscillation: keep the monotonic down-ramp and simply
    // retarget — the swap at black picks up the newest preset. (Snapping a dip
    // to its end state mid-ramp would relight and immediately re-dip = an
    // up-down flash, which the Strobe Law forbids. Documented spec deviation.)
    tr.target = preset;
    return;
  }

  if (tr.phase == K1Q_XFADE) {
    // Latest-wins (spec §1): snap the active crossfade to its end state, then
    // start the new transition.
    finish_xfade_now(ch, true);
  }

  // Queue-mode-OFF immediate changes always go through the dip (spec §1);
  // cued commits use the configured style.
  const uint8_t style = cued ? g_transition_style : (uint8_t)K1_QUEUE_TRANSITION_DIP;

  tr.target = preset;
  tr.start_ms = now_ms;
  if (style == K1_QUEUE_TRANSITION_XFADE) {
    tr.phase = K1Q_XFADE;
    reset_xfade_scratch(ch);
  } else {
    tr.phase = K1Q_DIP_DOWN;
  }
}

void advance_transition(uint8_t ch, uint32_t now_ms) {
  ChannelTransition& tr = g_transition[ch];
  float& scale = (ch == K1Q_PRIMARY) ? k1_queue_transition_scale_primary
                                     : k1_queue_transition_scale_secondary;

  switch (tr.phase) {
    case K1Q_DIP_DOWN: {
      if (scale <= 0.0f) {
        // The previous frame rendered fully dark: land the whole 15-field swap
        // at black, then relight INSTANTLY (monotonic down + instant up only).
        apply_preset_live(ch == K1Q_SECONDARY, tr.target);
        tr.phase = K1Q_IDLE;
        scale = 1.0f;  // instant relight — never ramped back up
        break;
      }
      const uint32_t elapsed = now_ms - tr.start_ms;
      const uint16_t dip_ms = (g_dip_ms > 0) ? g_dip_ms : 1;
      float s = 1.0f - (float(elapsed) / float(dip_ms));
      if (s < 0.0f) s = 0.0f;
      if (s < scale) scale = s;  // monotonic down only; no oscillation possible
      break;
    }
    case K1Q_XFADE: {
      scale = 1.0f;  // crossfade visibility is handled by the blend, not the scalar
      if (now_ms - tr.start_ms >= g_xfade_ms) {
        finish_xfade_now(ch, true);
      }
      break;
    }
    case K1Q_IDLE:
    default:
      scale = 1.0f;
      break;
  }
}

// --- Preset slot storage (RAM table + /PRESETS_V1.BIN, cal_profile pattern) ---

struct PresetSlot {
  bool valid;
  K1ChannelPreset preset;
};

PresetSlot g_slots[K1_PRESET_SLOT_COUNT] = {};
bool g_slots_loaded = false;

bool write_slot_bytes(File& file, const void* data, size_t len) {
  return file.write(reinterpret_cast<const uint8_t*>(data), len) == len;
}

bool read_slot_bytes(File& file, void* data, size_t len) {
  return file.read(reinterpret_cast<uint8_t*>(data), len) == len;
}

bool write_preset_record(File& file, const PresetSlot& slot) {
  const K1ChannelPreset& p = slot.preset;
  uint8_t valid = slot.valid ? 1 : 0;
  uint8_t mirror = p.mirror_enabled ? 1 : 0;
  uint8_t incand_mode = p.incandescent_mode ? 1 : 0;
  uint8_t base_coat = p.base_coat ? 1 : 0;
  uint8_t reverse = p.reverse_order ? 1 : 0;
  uint8_t auto_shift = p.auto_color_shift ? 1 : 0;
  uint8_t palette_mode = p.palette_mode_enabled ? 1 : 0;
  bool ok = true;
  ok = ok && write_slot_bytes(file, &valid, sizeof(valid));
  ok = ok && write_slot_bytes(file, &p.lightshow_mode, sizeof(p.lightshow_mode));
  ok = ok && write_slot_bytes(file, &mirror, sizeof(mirror));
  ok = ok && write_slot_bytes(file, &p.photons, sizeof(p.photons));
  ok = ok && write_slot_bytes(file, &p.chroma, sizeof(p.chroma));
  ok = ok && write_slot_bytes(file, &p.mood, sizeof(p.mood));
  ok = ok && write_slot_bytes(file, &p.saturation, sizeof(p.saturation));
  ok = ok && write_slot_bytes(file, &p.prism_count, sizeof(p.prism_count));
  ok = ok && write_slot_bytes(file, &p.incandescent_filter, sizeof(p.incandescent_filter));
  ok = ok && write_slot_bytes(file, &incand_mode, sizeof(incand_mode));
  ok = ok && write_slot_bytes(file, &base_coat, sizeof(base_coat));
  ok = ok && write_slot_bytes(file, &reverse, sizeof(reverse));
  ok = ok && write_slot_bytes(file, &auto_shift, sizeof(auto_shift));
  ok = ok && write_slot_bytes(file, &p.base_coat_intensity, sizeof(p.base_coat_intensity));
  ok = ok && write_slot_bytes(file, &p.palette_index, sizeof(p.palette_index));
  ok = ok && write_slot_bytes(file, &palette_mode, sizeof(palette_mode));
  return ok;
}

bool read_preset_record(File& file, PresetSlot& slot) {
  K1ChannelPreset p = {};
  uint8_t valid = 0, mirror = 0, incand_mode = 0, base_coat = 0;
  uint8_t reverse = 0, auto_shift = 0, palette_mode = 0;
  bool ok = true;
  ok = ok && read_slot_bytes(file, &valid, sizeof(valid));
  ok = ok && read_slot_bytes(file, &p.lightshow_mode, sizeof(p.lightshow_mode));
  ok = ok && read_slot_bytes(file, &mirror, sizeof(mirror));
  ok = ok && read_slot_bytes(file, &p.photons, sizeof(p.photons));
  ok = ok && read_slot_bytes(file, &p.chroma, sizeof(p.chroma));
  ok = ok && read_slot_bytes(file, &p.mood, sizeof(p.mood));
  ok = ok && read_slot_bytes(file, &p.saturation, sizeof(p.saturation));
  ok = ok && read_slot_bytes(file, &p.prism_count, sizeof(p.prism_count));
  ok = ok && read_slot_bytes(file, &p.incandescent_filter, sizeof(p.incandescent_filter));
  ok = ok && read_slot_bytes(file, &incand_mode, sizeof(incand_mode));
  ok = ok && read_slot_bytes(file, &base_coat, sizeof(base_coat));
  ok = ok && read_slot_bytes(file, &reverse, sizeof(reverse));
  ok = ok && read_slot_bytes(file, &auto_shift, sizeof(auto_shift));
  ok = ok && read_slot_bytes(file, &p.base_coat_intensity, sizeof(p.base_coat_intensity));
  ok = ok && read_slot_bytes(file, &p.palette_index, sizeof(p.palette_index));
  ok = ok && read_slot_bytes(file, &palette_mode, sizeof(palette_mode));
  if (!ok) {
    return false;
  }
  p.mirror_enabled = (mirror != 0);
  p.incandescent_mode = (incand_mode != 0);
  p.base_coat = (base_coat != 0);
  p.reverse_order = (reverse != 0);
  p.auto_color_shift = (auto_shift != 0);
  p.palette_mode_enabled = (palette_mode != 0);
  // Sanitize persisted values (fail-to-safe, cal_profile pattern).
#ifdef K1_EFFECT_REGISTRY_V1
  p.lightshow_mode = k1::effects::framework::registry_sanitize_persisted(p.lightshow_mode);
#else
  p.lightshow_mode = light_mode_sanitize_persisted(p.lightshow_mode);
#endif
  if (p.palette_index >= gGradientPaletteCount) {
    p.palette_index = 0;
  }
  slot.valid = (valid != 0);
  slot.preset = p;
  return true;
}

bool slots_write_file() {
  // G7B: park Core 1 across LittleFS (same crash class as save_config).
  lock_leds();
  File file = LittleFS.open(K1_PRESET_SLOTS_FILE, FILE_WRITE);
  if (!file) {
    unlock_leds();
    return false;
  }
  uint32_t magic = K1_PRESET_SLOTS_MAGIC;
  uint16_t version = K1_PRESET_SLOTS_VERSION;
  uint16_t slot_count = K1_PRESET_SLOT_COUNT;
  bool ok = true;
  ok = ok && write_slot_bytes(file, &magic, sizeof(magic));
  ok = ok && write_slot_bytes(file, &version, sizeof(version));
  ok = ok && write_slot_bytes(file, &slot_count, sizeof(slot_count));
  for (uint8_t i = 0; ok && i < K1_PRESET_SLOT_COUNT; i++) {
    ok = write_preset_record(file, g_slots[i]);
  }
  file.close();
  unlock_leds();
  return ok;
}

void slots_ensure_loaded() {
  if (g_slots_loaded) {
    return;
  }
  g_slots_loaded = true;  // attempt once per boot; absent file = all-invalid

  lock_leds();
  File file = LittleFS.open(K1_PRESET_SLOTS_FILE, FILE_READ);
  if (!file) {
    unlock_leds();
    return;  // no slots saved yet — every slot stays invalid
  }

  uint32_t magic = 0;
  uint16_t version = 0;
  uint16_t slot_count = 0;
  bool ok = true;
  ok = ok && read_slot_bytes(file, &magic, sizeof(magic));
  ok = ok && read_slot_bytes(file, &version, sizeof(version));
  ok = ok && read_slot_bytes(file, &slot_count, sizeof(slot_count));
  if (!ok || magic != K1_PRESET_SLOTS_MAGIC ||
      version != K1_PRESET_SLOTS_VERSION ||
      slot_count != K1_PRESET_SLOT_COUNT) {
    file.close();
    unlock_leds();
    return;  // unrecognised file — fail to defaults (all slots invalid)
  }
  PresetSlot loaded[K1_PRESET_SLOT_COUNT] = {};
  for (uint8_t i = 0; ok && i < K1_PRESET_SLOT_COUNT; i++) {
    ok = read_preset_record(file, loaded[i]);
  }
  file.close();
  unlock_leds();
  if (!ok) {
    return;
  }
  for (uint8_t i = 0; i < K1_PRESET_SLOT_COUNT; i++) {
    g_slots[i] = loaded[i];
  }
}

}  // namespace

// =============================================================================
// Serial-side API
// =============================================================================

bool k1_queue_mode_enabled() { return g_queue_mode; }

void k1_queue_set_mode_enabled(bool on) {
  g_queue_mode = on;
  if (!on) {
    k1_queue_disarm_all();
  }
}

void k1_queue_apply_fields(bool secondary, const K1ChannelPreset& preset) {
  apply_preset_fields(secondary, preset);
}

K1ChannelPreset k1_queue_capture_live(bool secondary) {
  K1ChannelPreset p;
  if (!secondary) {
    p.lightshow_mode       = CONFIG.LIGHTSHOW_MODE;
    p.mirror_enabled       = CONFIG.MIRROR_ENABLED;
    p.photons              = CONFIG.PHOTONS;
    p.chroma               = CONFIG.CHROMA;
    p.mood                 = CONFIG.MOOD;
    p.saturation           = CONFIG.SATURATION;
    p.prism_count          = CONFIG.PRISM_COUNT;
    p.incandescent_filter  = CONFIG.INCANDESCENT_FILTER;
    p.incandescent_mode    = CONFIG.INCANDESCENT_MODE;
    p.base_coat            = CONFIG.BASE_COAT;
    p.reverse_order        = CONFIG.REVERSE_ORDER;
    p.auto_color_shift     = CONFIG.AUTO_COLOR_SHIFT;
    p.base_coat_intensity  = CONFIG.BASE_COAT_INTENSITY;
    p.palette_index        = CONFIG.PALETTE_INDEX;
    p.palette_mode_enabled = CONFIG.PALETTE_MODE_ENABLED;
  } else {
    p.lightshow_mode       = SECONDARY_LIGHTSHOW_MODE;
    p.mirror_enabled       = SECONDARY_MIRROR_ENABLED;
    p.photons              = SECONDARY_PHOTONS;
    p.chroma               = SECONDARY_CHROMA;
    p.mood                 = SECONDARY_MOOD;
    p.saturation           = SECONDARY_SATURATION;
    p.prism_count          = SECONDARY_PRISM_COUNT;
    p.incandescent_filter  = SECONDARY_INCANDESCENT_FILTER;
    p.incandescent_mode    = SECONDARY_INCANDESCENT_MODE;
    p.base_coat            = SECONDARY_BASE_COAT;
    p.reverse_order        = SECONDARY_REVERSE_ORDER;
    p.auto_color_shift     = SECONDARY_AUTO_COLOR_SHIFT;
    p.base_coat_intensity  = SECONDARY_BASE_COAT_INTENSITY;
    p.palette_index        = SECONDARY_PALETTE_INDEX;
    p.palette_mode_enabled = SECONDARY_PALETTE_MODE_ENABLED;
  }
  return p;
}

K1ChannelPreset* k1_queue_arm_begin(bool secondary) {
  ChannelPendingState& pending = g_pending[channel_index(secondary)];
  if (!pending.armed) {
    // Seed from the EFFECTIVE channel value so rapid stepping during an active
    // transition (queue-off dip in flight) does not lose steps: prefer the
    // in-flight transition target over the not-yet-swapped live fields.
    const ChannelTransition& tr = g_transition[channel_index(secondary)];
    pending.preset = (tr.phase != K1Q_IDLE) ? tr.target
                                            : k1_queue_capture_live(secondary);
    pending.armed = true;
  }
  return &pending.preset;
}

void k1_queue_arm_preset(bool secondary, const K1ChannelPreset& preset) {
  ChannelPendingState& pending = g_pending[channel_index(secondary)];
  pending.preset = preset;
  pending.armed = true;
}

bool k1_queue_channel_armed(bool secondary) {
  return g_pending[channel_index(secondary)].armed;
}

bool k1_queue_any_armed() {
  return g_pending[K1Q_PRIMARY].armed || g_pending[K1Q_SECONDARY].armed;
}

void k1_queue_disarm_all() {
  g_pending[K1Q_PRIMARY].armed = false;
  g_pending[K1Q_SECONDARY].armed = false;
}

void k1_queue_request_commit(bool cued, uint32_t now_ms) {
  g_commit_cued = cued;
  g_commit_request_ms = now_ms;
  g_commit_request = true;  // raised LAST: pending structs are already complete
}

bool k1_queue_commit_pending() { return g_commit_request; }

uint8_t k1_queue_transition_style() { return g_transition_style; }

void k1_queue_set_transition_style(uint8_t style) {
  g_transition_style = (style == K1_QUEUE_TRANSITION_XFADE)
                           ? (uint8_t)K1_QUEUE_TRANSITION_XFADE
                           : (uint8_t)K1_QUEUE_TRANSITION_DIP;
}

uint16_t k1_queue_dip_ms() { return g_dip_ms; }

bool k1_queue_set_dip_ms(uint32_t ms) {
  if (ms < K1_QUEUE_DIP_MS_MIN || ms > K1_QUEUE_DIP_MS_MAX) {
    return false;
  }
  g_dip_ms = (uint16_t)ms;
  return true;
}

uint16_t k1_queue_xfade_ms() { return g_xfade_ms; }

bool k1_queue_set_xfade_ms(uint32_t ms) {
  if (ms < K1_QUEUE_XFADE_MS_MIN || ms > K1_QUEUE_XFADE_MS_MAX) {
    return false;
  }
  g_xfade_ms = (uint16_t)ms;
  return true;
}

uint8_t k1_queue_commit_quantise() { return g_quantise; }

void k1_queue_set_commit_quantise(uint8_t mode) {
  g_quantise = (mode == K1_QUEUE_QUANTISE_BEAT)
                   ? (uint8_t)K1_QUEUE_QUANTISE_BEAT
                   : (uint8_t)K1_QUEUE_QUANTISE_OFF;
}

bool k1_preset_slot_save(uint8_t slot_index, bool from_secondary) {
  if (slot_index >= K1_PRESET_SLOT_COUNT) {
    return false;
  }
  slots_ensure_loaded();
  g_slots[slot_index].preset = k1_queue_capture_live(from_secondary);
  g_slots[slot_index].valid = true;
  // Immediate write (spec §3: rare operation, no debounce). Runs on the
  // serial/loop core — never on the render task.
  return slots_write_file();
}

bool k1_preset_slot_get(uint8_t slot_index, K1ChannelPreset* out) {
  if (slot_index >= K1_PRESET_SLOT_COUNT || out == nullptr) {
    return false;
  }
  slots_ensure_loaded();
  if (!g_slots[slot_index].valid) {
    return false;
  }
  *out = g_slots[slot_index].preset;
  return true;
}

bool k1_preset_slot_valid(uint8_t slot_index) {
  if (slot_index >= K1_PRESET_SLOT_COUNT) {
    return false;
  }
  slots_ensure_loaded();
  return g_slots[slot_index].valid;
}

// =============================================================================
// Core-1 API
// =============================================================================

void k1_effect_queue_frame_tick(uint32_t now_ms) {
  // 1. Consume the commit request (with optional beat-quantise hold).
  if (g_commit_request) {
    bool fire = true;
    const bool cued = g_commit_cued;
    if (cued && g_quantise == K1_QUEUE_QUANTISE_BEAT) {
      const K1TempoEvent tempo = k1_tempo_read();
      const bool on_beat = tempo.beat_tick && tempo.locked;
      const bool timed_out =
          (now_ms - g_commit_request_ms) >= K1_QUEUE_QUANTISE_TIMEOUT_MS;
      fire = on_beat || timed_out;  // 2000 ms fallback: commit anyway (spec §2)
    }
    if (fire) {
      g_commit_request = false;
      // `\` commits ALL armed channels in the same frame (scene-flip support).
      for (uint8_t ch = 0; ch < 2; ch++) {
        if (g_pending[ch].armed) {
          g_pending[ch].armed = false;
          start_transition(ch, g_pending[ch].preset, now_ms, cued);
        }
      }
    }
  }

  // 2. Advance per-channel transitions (dip ramps, swaps at black, crossfade
  //    completion). All live-field writes happen here, at the frame boundary.
  advance_transition(K1Q_PRIMARY, now_ms);
  advance_transition(K1Q_SECONDARY, now_ms);
}

bool k1_queue_xfade_overlay_begin(bool secondary, uint32_t now_ms,
                                  float* gain_out, float* gain_in,
                                  uint8_t* incoming_mode, float* incoming_prism) {
  const uint8_t ch = channel_index(secondary);
  ChannelTransition& tr = g_transition[ch];
  if (tr.phase != K1Q_XFADE) {
    return false;
  }
  const uint16_t xfade_ms = (g_xfade_ms > 0) ? g_xfade_ms : 1;
  float t = float(now_ms - tr.start_ms) / float(xfade_ms);
  if (t < 0.0f) t = 0.0f;
  if (t > 1.0f) t = 1.0f;
  // Equal-power blend (spec §2): sqrt ramps keep perceived energy constant.
  *gain_out = sqrtf(1.0f - t);
  *gain_in = sqrtf(t);
  *incoming_mode = tr.target.lightshow_mode;
  *incoming_prism = tr.target.prism_count;

  // Temp-apply the incoming fields to the live param sources so the incoming
  // render pass (build_*_render_params + the SECONDARY_* global reads) sees
  // the target configuration. Restored in k1_queue_xfade_overlay_end().
  g_xfade_saved_live[ch] = k1_queue_capture_live(secondary);
  apply_preset_fields(secondary, tr.target);
  g_xfade_overlay_applied[ch] = true;
  return true;
}

void k1_queue_xfade_overlay_end(bool secondary) {
  const uint8_t ch = channel_index(secondary);
  if (!g_xfade_overlay_applied[ch]) {
    return;
  }
  apply_preset_fields(secondary, g_xfade_saved_live[ch]);
  g_xfade_overlay_applied[ch] = false;
}

K1QueueXfadeScratch* k1_queue_xfade_scratch(bool secondary) {
  return &g_xfade_scratch[channel_index(secondary)];
}
