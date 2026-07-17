

#define FIRMWARE_VERSION 40103  // Try "V" on the Serial port for this!  // 2026-05-26: bumped for CHROMA_PROFILE conf field add (Stage 2 items 18-21) — config byte layout shifted after CHROMAGRAM_RANGE; forces fresh /CONFIG_*.BIN, orphans stale 40102 blob (values re-seed to identical defaults: NOTE_OFFSET=12/CHROMAGRAM_RANGE=60/CHROMA_PROFILE=DEFAULT)  // 2026-05-20: single-domain noise_cal fix


// Lightshow modes by name -----------------------------------------------------------
// PIO-SPIKE2 (2026-05-25): the `enum lightshow_modes { ... NUM_MODES }` definition
// moved to constants.h (included above at line 92, before globals.h). It was inline
// here only because the single-TU include order made it visible to the headers that
// reference LIGHT_MODE_*/NUM_MODES. Header-visibility is required to relocate CONFIG's
// aggregate initialiser (which uses LIGHT_MODE_GDFT) into globals_config.cpp.

// External dependencies -------------------------------------------------------------
#include <esp_random.h>   // RNG Functions
#include <FastLED.h>      // Handles LED color data and display
#include <FS.h>           // Filesystem functions (bridge_fs.h below)
#include <LittleFS.h>     // LittleFS implementation
#include <Ticker.h>       // Scheduled tasks library
#include <USB.h>          // USB Connection handling
#include <FirmwareMSC.h>  // Allows firmware updates via USB MSC
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
#include <Wire.h>
#include "esp_task_wdt.h"  // N2: raw Task-WDT API (esp_task_wdt_reconfigure/_add/_reset/_status) + esp_task_wdt_config_t
#include "m5rotate8.h"

#ifndef K1_TASK_WDT_TIMEOUT_MS
#define K1_TASK_WDT_TIMEOUT_MS 5000  // N2: task-watchdog timeout (>> worst-case legit block: render flash window <1s, DMA 7.5ms)
#endif

// Include K1 firmware files, sorted high to low, by boringness ;) -------
#include "user_config.h"      // Nothing for now
#include "constants.h"        // Global constants
#include "globals.h"          // Global variables
#include "k1_trace.h"         // Developer-only MabuTrace wrapper (no-op outside trace_dev)
#include "presets.h"          // Configuration presets by name
#include "bridge_fs.h"        // Filesystem access (save/load configuration)
#include "utilities.h"        // Misc. math and other functions
#include "i2s_audio.h"        // I2S Microphone audio capture
#include "led_utilities.h"    // LED color/transform utility functions
#include "noise_cal.h"        // Background noise removal
#include "buttons.h"          // Watch the status of buttons
#include "knobs.h"            // Watch the status of knobs...
#include "serial_menu.h"      // Watch the Serial port... *sigh*
#include "system.h"           // Watch how fast I can check if settings were updated... yada yada..
#include "GDFT.h"             // Conversion to (and post-processing of) frequency data! (hey, something cool!)
#include "k1_audio_snapshot.h" // Smart Visual Engine AP snapshot (post-VU/GDFT/novelty)
#include "k1_onset_beat.h"    // Smart Visual Engine AP onset/beat event lane
#include "k1_musical_saliency.h"  // Smart Visual Engine AP saliency state and events
#include "k1_tempo.h"         // Smart Visual Engine AP tempo / beat-phase tracker (Core-0)
#include "k1_smart_director.h" // Smart Visual Engine Assist mode intent + render modulation
#include "k1_edgemixer.h" // Smart Visual Engine secondary colour differentiation
#include "k1_visual_hooks.h"  // Smart Visual Engine event-gated visual hooks
#include "k1_effect_queue.h"  // Effects queuing + preset slots (frame-boundary commit engine)
#ifdef K1_WIRELESS_ENABLED
#include "k1_wireless.h"   // K1 AP-only WebSocket command ingress
#endif
#ifdef K1_BLE_REMOTED
#include "ble_remoted_central.h"  // Remoted dial BLE-MIDI central (gated; interference A/B)
#endif
#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"     // Harness-only final-byte evidence context
#endif
#ifdef K1_PIN_EVIDENCE_V1
#include "k1_pin_evidence.h"  // Harness-only loud-pinning AP/VP/final-byte evidence
#endif
#ifdef ENABLE_GDFT_HARNESS
#include "gdft_harness.h"     // Item 22 — synthetic sine/sweep Goertzel probe (harness env only; needs process_GDFT from GDFT.h)
#endif
#ifdef ENABLE_MOTION_PROBE
#include "motion_probe.h"     // Apparent-motion perceptual test harness (motion-probe env only; needs show_leds from led_utilities.h)
#endif
#ifdef ENABLE_VP_MOTION_LAB
#include "vp_motion_lab.h"    // NON-SHIPPABLE VP Motion Lab built-in preview harness
#endif
#include "lightshow_modes.h"  // --- FINALLY, the FUN STUFF!
#ifdef K1_EFFECT_FRAMEWORK_V1
#include "LegacyEffectAdapter.h"  // P3: route render path through IEffect dispatch (flag-gated)
#include "TransitionOverlay.h"    // P4: centre-origin TransitionEngine on the xfade seam (flag-gated)
#include "beat_aware_director.h"  // P6: K1-native beat-aware director (flag-gated, opt-in)
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h"       // R2-core: route dispatch through the single-source-of-truth registry
#endif
#endif
#include "encoders.h"         // M5Stack Rotate8 encoder handling

#ifdef K1_BOOTLOOP_GUARD_V1
#include "k1_bootloop_guard.h"  // N2b: boot-loop crash-streak guard (pure core host-proven)
// The crash counter lives in RTC_NOINIT memory: it survives a crash/panic/WDT/brownout
// reset and is re-seeded on a clean power-on. Defined here in exactly ONE translation
// unit — never in the header, which would multiply the global across TUs.
RTC_NOINIT_ATTR K1BootloopState k1_bootloop_rtc;
#endif

// Define benchmark state variables (declared extern in serial_menu.h)
bool benchmark_running = false;
uint32_t benchmark_start_time = 0;
uint32_t system_fps_sum = 0;
uint32_t led_fps_sum = 0;
uint32_t benchmark_sample_count = 0;

// Add at the top of the file, near other global variables
uint32_t last_frame_us = 0;
M5ROTATE8 rotate8; // Global M5Rotate8 object - Defined here, declared extern in encoders.h

#ifndef K1_LED_TASK_CORE
#define K1_LED_TASK_CORE 1
#endif

#ifndef K1_ACQUISITION_ONLY_PROBE
#define K1_ACQUISITION_ONLY_PROBE 0
#endif

#define K1_AP_STAGE_FULL 0
#define K1_AP_STAGE_ACQUISITION 1
#define K1_AP_STAGE_GDFT 2
#define K1_AP_STAGE_NOVELTY 3
#define K1_AP_STAGE_SNAPSHOT 4
#define K1_AP_STAGE_ONSET 5
#define K1_AP_STAGE_SALIENCY 6
#define K1_AP_STAGE_TEMPO 7

#ifndef K1_AP_STAGE_PROBE_STOP_STAGE
#define K1_AP_STAGE_PROBE_STOP_STAGE K1_AP_STAGE_FULL
#endif

#if defined(K1_HARDWARE) && defined(ARDUINO_RUNNING_CORE) && (ARDUINO_RUNNING_CORE == K1_LED_TASK_CORE) && !defined(K1_ALLOW_AP_VP_SAME_CORE_FOR_PROBE)
#error "K1 timing invariant violation: AP loop and VP/render task must not share a core"
#endif

#if K1_ACQUISITION_ONLY_PROBE && !(ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG)
#error "K1_ACQUISITION_ONLY_PROBE requires ENABLE_TEMPO_STREAM and ENABLE_AP_FRONTEND_DEBUG"
#endif

#if K1_AP_STAGE_PROBE_STOP_STAGE && !(ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG)
#error "K1_AP_STAGE_PROBE_STOP_STAGE requires ENABLE_TEMPO_STREAM and ENABLE_AP_FRONTEND_DEBUG"
#endif

#if K1_ACQUISITION_ONLY_PROBE && K1_AP_STAGE_PROBE_STOP_STAGE
#error "K1_ACQUISITION_ONLY_PROBE and K1_AP_STAGE_PROBE_STOP_STAGE are mutually exclusive"
#endif

#if K1_AP_STAGE_PROBE_STOP_STAGE > K1_AP_STAGE_TEMPO
#error "Unsupported K1_AP_STAGE_PROBE_STOP_STAGE"
#endif

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
static volatile int8_t k1_ap_cadence_vp_core_id = -1;
#endif

// Encoder state globals (must be defined exactly once)
bool g_rotate8_available = false;
uint32_t g_next_recovery_attempt = 0;
uint32_t encoder3_button_hold_start = 0;
bool encoder3_in_contrast_mode = false;

struct RenderChannelState {
  CRGB16* history;
  CRGB16* output;
  bool seed_history_before_render;
  CRGB16* waveform_fast_last_color;
  float* waveform_fast_peak_scaled_last;
  float* waveform_fast_shift_accum;
  uint32_t* waveform_fast_last_frame_ms;
  CRGB16* waveform_last_color;
  float* waveform_peak_scaled_last;
  float* waveform_shift_accum;
  uint32_t* waveform_last_frame_ms;
  CRGB16* waveform_hybrid_last_color;
  float* waveform_hybrid_peak_scaled_last;
  float* waveform_hybrid_shift_accum;
  uint32_t* waveform_hybrid_last_frame_ms;
  SQ15x16* vu_level_smooth;
  SQ15x16* vu_max_level;
  ChannelEffectState* effect;
};

struct RenderRuntimeSnapshot {
  // RenderParams core: the secondary render pass no longer mutates global
  // CONFIG, so CONFIG is no longer captured/restored here (the 9 SECONDARY_*
  // overrides now flow through the RenderParams stack). The remaining fields
  // are still-global render state that the secondary pass touches.
  SQ15x16 hue_position;
  SQ15x16 chroma_val;
  bool chromatic_mode;
  SQ15x16 hue_shifting_mix;
  SQ15x16 base_coat_width;
  SQ15x16 base_coat_width_target;
  bool vp_render_secondary_channel;
};

RenderChannelState make_primary_channel() {
  RenderChannelState channel;
  channel.history = leds_16_prev;
  channel.output = leds_16;
  channel.seed_history_before_render = false;
  channel.waveform_fast_last_color = &waveform_fast_last_color_primary;
  channel.waveform_fast_peak_scaled_last = &waveform_fast_peak_scaled_last_primary;
  channel.waveform_fast_shift_accum = &waveform_fast_shift_accum_primary;
  channel.waveform_fast_last_frame_ms = &waveform_fast_last_frame_ms_primary;
  channel.waveform_last_color = &waveform_last_color_primary;
  channel.waveform_peak_scaled_last = &waveform_peak_scaled_last_primary;
  channel.waveform_shift_accum = &waveform_shift_accum_primary;
  channel.waveform_last_frame_ms = &waveform_last_frame_ms_primary;
  channel.waveform_hybrid_last_color = &waveform_hybrid_last_color_primary;
  channel.waveform_hybrid_peak_scaled_last = &waveform_hybrid_peak_scaled_last_primary;
  channel.waveform_hybrid_shift_accum = &waveform_hybrid_shift_accum_primary;
  channel.waveform_hybrid_last_frame_ms = &waveform_hybrid_last_frame_ms_primary;
  channel.vu_level_smooth = &vu_level_smooth_primary;
  channel.vu_max_level = &vu_max_level_primary;
  channel.effect = &effect_state_primary;
  return channel;
}

RenderChannelState make_secondary_channel() {
  RenderChannelState channel;
  channel.history = leds_16_prev_secondary;
  channel.output = leds_16_secondary;
  channel.seed_history_before_render = true;
  channel.waveform_fast_last_color = &waveform_fast_last_color_secondary;
  channel.waveform_fast_peak_scaled_last = &waveform_fast_peak_scaled_last_secondary;
  channel.waveform_fast_shift_accum = &waveform_fast_shift_accum_secondary;
  channel.waveform_fast_last_frame_ms = &waveform_fast_last_frame_ms_secondary;
  channel.waveform_last_color = &waveform_last_color_secondary;
  channel.waveform_peak_scaled_last = &waveform_peak_scaled_last_secondary;
  channel.waveform_shift_accum = &waveform_shift_accum_secondary;
  channel.waveform_last_frame_ms = &waveform_last_frame_ms_secondary;
  channel.waveform_hybrid_last_color = &waveform_hybrid_last_color_secondary;
  channel.waveform_hybrid_peak_scaled_last = &waveform_hybrid_peak_scaled_last_secondary;
  channel.waveform_hybrid_shift_accum = &waveform_hybrid_shift_accum_secondary;
  channel.waveform_hybrid_last_frame_ms = &waveform_hybrid_last_frame_ms_secondary;
  channel.vu_level_smooth = &vu_level_smooth_secondary;
  channel.vu_max_level = &vu_max_level_secondary;
  channel.effect = &effect_state_secondary;
  return channel;
}

RenderRuntimeSnapshot capture_render_runtime() {
  RenderRuntimeSnapshot snapshot;
  snapshot.hue_position = hue_position;
  snapshot.chroma_val = chroma_val;
  snapshot.chromatic_mode = chromatic_mode;
  snapshot.hue_shifting_mix = hue_shifting_mix;
  snapshot.base_coat_width = base_coat_width;
  snapshot.base_coat_width_target = base_coat_width_target;
  snapshot.vp_render_secondary_channel = vp_render_secondary_channel;
  return snapshot;
}

void restore_render_runtime(const RenderRuntimeSnapshot& snapshot) {
  hue_position = snapshot.hue_position;
  chroma_val = snapshot.chroma_val;
  chromatic_mode = snapshot.chromatic_mode;
  hue_shifting_mix = snapshot.hue_shifting_mix;
  base_coat_width = snapshot.base_coat_width;
  base_coat_width_target = snapshot.base_coat_width_target;
  vp_render_secondary_channel = snapshot.vp_render_secondary_channel;
}

// apply_secondary_render_config() removed (RenderParams core): the secondary
// render pass no longer mutates global CONFIG. The 9 SECONDARY_* overrides now
// flow through build_secondary_render_params() / the RenderParams stack.

// Mode-keyed legacy lightshow dispatch. This is the ORIGINAL if/else body,
// extracted verbatim from render_lightshow_for_channel() so both the legacy
// caller and the K1_EFFECT_FRAMEWORK_V1 LegacyEffectAdapter execute the same
// code path. `history_seeded` reports whether the seed-before-render prologue
// already copied this channel's history into leds_16 (waveform-family modes
// re-seed lazily if it has not). Behaviour is identical to the prior inline
// chain; nothing about the per-mode orchestration changed.
void dispatch_legacy_lightshow(uint8_t mode, RenderChannelState& channel, bool history_seeded) {
  if (mode == LIGHT_MODE_GDFT) {
    light_mode_gdft();
  } else if (mode == LIGHT_MODE_GDFT_CHROMAGRAM) {
    light_mode_chromagram_gradient();
  } else if (mode == LIGHT_MODE_GDFT_CHROMAGRAM_DOTS) {
    light_mode_chromagram_dots();
  } else if (mode == LIGHT_MODE_BLOOM) {
    light_mode_bloom(channel.history);
  } else if (mode == LIGHT_MODE_BLOOM_FAST) {
    light_mode_bloom_fast(channel.history);
  } else if (mode == LIGHT_MODE_VU_DOT) {
    light_mode_vu_dot(*channel.effect);
  } else if (mode == LIGHT_MODE_KALEIDOSCOPE) {
    light_mode_kaleidoscope(*channel.effect);
  } else if (mode == LIGHT_MODE_QUANTUM_COLLAPSE) {
    light_mode_quantum_collapse();
  } else if (mode == LIGHT_MODE_WAVEFORM_FAST) {
    if (!history_seeded) {
      {
        K1_TRACE_SCOPE("vp_channel_seed_history");
        memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
      }
    }
    {
      K1_TRACE_SCOPE("vp_waveform_fast_body");
      light_mode_waveform_fast(channel.history, *channel.waveform_fast_last_color, *channel.waveform_fast_peak_scaled_last,
                               *channel.waveform_fast_shift_accum, *channel.waveform_fast_last_frame_ms);
    }
    {
      K1_TRACE_SCOPE("vp_waveform_fast_history_store");
      memcpy(channel.history, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
  } else if (mode == LIGHT_MODE_WAVEFORM) {
    if (!history_seeded) {
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    light_mode_waveform(channel.history, *channel.waveform_last_color, *channel.waveform_peak_scaled_last,
                        *channel.waveform_shift_accum, *channel.waveform_last_frame_ms);
    memcpy(channel.history, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_WAVEFORM_HYBRID) {
    if (!history_seeded) {
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    light_mode_waveform_hybrid(channel.history, *channel.waveform_hybrid_last_color, *channel.waveform_hybrid_peak_scaled_last,
                               *channel.waveform_hybrid_shift_accum, *channel.waveform_hybrid_last_frame_ms);
    memcpy(channel.history, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_VU) {
    light_mode_vu(*channel.vu_level_smooth, *channel.vu_max_level);
  } else if (mode == LIGHT_MODE_AURORA) {
    light_mode_aurora(channel.history);
  } else if (mode == LIGHT_MODE_COMET) {
    if (!history_seeded) {
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    light_mode_comet(*channel.effect);
    memcpy(channel.history, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_SPECTRUM_RIVER) {
    light_mode_spectrum_river(channel.history);
  } else if (mode == LIGHT_MODE_SPECTRUM_RIVER_V2) {
    light_mode_spectrum_river_v2(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_EMBER) {
    light_mode_ember(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_EMBER_V2) {
    light_mode_ember_v2(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_WAVEFORM_TEMPO) {
    // WAVEFORM-family scroll transport: seed leds_16 from this channel's history,
    // render the tempo-locked scroll, then store the result back (mirrors Comet).
    if (!history_seeded) {
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    light_mode_waveform_tempo(*channel.effect);
    memcpy(channel.history, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_TEMPO_RIVER) {
    // Transport (Spectrum-River lineage): manages its own leds_16/history internally.
    light_mode_tempo_river(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_TEMPO_COMET) {
    // Particle (Comet lineage): trail lives in leds_16 — seed from history, render, store back.
    if (!history_seeded) {
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    light_mode_tempo_comet(*channel.effect);
    memcpy(channel.history, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_DENSE_FORGE) {
    light_mode_dense_forge(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_SNAPWAVE) {
    light_mode_snapwave(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_PULSE_PRISM) {
    light_mode_pulse_prism(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_DENSE_FORGE_CHORD) {
    light_mode_dense_forge_chord(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_CHROMA_CONSTELLATION) {
    light_mode_chroma_constellation(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_PERCUSSION_BURST) {
    light_mode_percussion_burst(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_TEMPO_COMET_ANTICIPATE) {
    // Particle (Comet lineage): trail lives in leds_16 — seed from history, render, store back.
    if (!history_seeded) {
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    light_mode_tempo_comet_anticipate(*channel.effect);
    memcpy(channel.history, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_RIVER_SURGE) {
    light_mode_river_surge(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_TEMPO_RIVER_WALK) {
    light_mode_tempo_river_walk(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_BEAT_PULSE) {
    // Closed-form inward rings: authors its own leds_16 fresh each frame (no trail).
    light_mode_beat_pulse(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_BLOOM_BT) {
    // Bloom BassTreble: greyscale scroll transport self-managed in channel.history.
    light_mode_bloom_bt(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_WAVEFORM_HYBRID_K1) {
    // Waveform Hybrid: bouncing dot + trail, self-managed history.
    light_mode_waveform_hybrid_k1(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_MOIRE_CATHEDRAL) {
    // Moire Cathedral: overwrite-per-frame grating field.
    light_mode_moire_cathedral(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_CANNONADE) {
    // Cannonade: ballistic lob + arc-return + centre crack; self-managed wake.
    light_mode_cannonade(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_SHOCKWAVE) {
    // Shockwave: pure-age expanding shells; self-managed wake.
    light_mode_shockwave(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_IRIS) {
    // Iris: in-place spring dilate-recoil membrane; self-managed after-glow.
    light_mode_iris(channel.history, *channel.effect);
  } else if (mode == LIGHT_MODE_MELODIC_BLOOM) {
    // Melodic Bloom: mid-forward presence bloom; greyscale scroll transport self-managed.
    light_mode_melodic_bloom(channel.history, *channel.effect);
  }
}

// Seed-prologue + dispatch. Unchanged contract: callers pass the resolved mode
// and the per-channel state; the secondary channel seeds its history into
// leds_16 up front (seed_history_before_render). The body delegates to
// dispatch_legacy_lightshow() so the K1 effect-framework adapter can reuse the
// identical code path (see effects/framework/LegacyEffectAdapter).
void render_lightshow_for_channel(uint8_t mode, RenderChannelState& channel) {
  bool history_seeded = false;
  if (channel.seed_history_before_render) {
    {
      K1_TRACE_SCOPE("vp_channel_seed_history");
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    history_seeded = true;
  }
  dispatch_legacy_lightshow(mode, channel, history_seeded);
}

#ifdef K1_EFFECT_FRAMEWORK_V1
// ── K1 effect-framework dispatch (flag-gated; default build never sees this) ──
// Renders a channel through IEffect::render() instead of calling the legacy
// dispatch directly. The wrapped effect is a LegacyEffectAdapter that forwards to
// dispatch_legacy_lightshow() with the SAME inputs, so on-plate output is
// byte-identical to render_lightshow_for_channel(). This is the proof-of-seam for
// the framework: same looks, new spine.
//
// We replicate render_lightshow_for_channel()'s seed-before-render prologue here
// (so the adapter sees the correct history_seeded state) and bind the live audio
// snapshot + this channel's CRGB16 strips + real frame dt into the EffectContext.
void render_channel_via_framework(uint8_t mode, RenderChannelState& channel) {
  using namespace k1::effects::framework;

  // Same seed prologue as the legacy path (identical memcpy under the same gate).
  bool history_seeded = false;
  if (channel.seed_history_before_render) {
    {
      K1_TRACE_SCOPE("vp_channel_seed_history");
      memcpy(leds_16, channel.history, sizeof(CRGB16) * NATIVE_RESOLUTION);
    }
    history_seeded = true;
  }

  // Live audio surface (read-only adapter over K1's own snapshot + onset event).
  static K1AudioSnapshot fw_audio_snapshot;
  static K1OnsetBeatEvent fw_beat_event;
  fw_audio_snapshot = k1_audio_snapshot_read();
  fw_beat_event = k1_onset_beat_read();

  // Real frame delta (P2 NEXT item): measured µs since the last VP frame.
  const int64_t now_us = esp_timer_get_time();
  const int64_t dt_us = (last_frame_us > 0) ? (now_us - (int64_t)last_frame_us) : 8000;
  const float dt_s = (dt_us > 0) ? (float)dt_us / 1000000.0f : 0.008f;

  EffectContext ctx;
  ctx.audio.bind(&fw_audio_snapshot, &fw_beat_event);
  ctx.k1Buffer.bind(leds_16, leds_16_secondary, NATIVE_RESOLUTION);
  ctx.deltaTimeMs = (uint32_t)(dt_us / 1000);
  ctx.deltaTimeSeconds = dt_s;
  ctx.rawDeltaTimeMs = ctx.deltaTimeMs;
  ctx.rawDeltaTimeSeconds = dt_s;

  // Legacy-bridge fields: hand the adapter the live channel + resolved mode.
  ctx.legacyChannel = &channel;
  ctx.legacyMode = mode;
  ctx.legacyHistorySeeded = history_seeded;

#ifdef K1_EFFECT_REGISTRY_V1
  // R2-core: resolve the renderer through the EffectRegistry — the single
  // source of truth. The runtime ordinal covers both the legacy modes
  // (< NUM_MODES, ordinal aliases the stable id) AND the appended native
  // ordinals (NUM_MODES..registry_mode_count()-1, which reach the v3 IEffects
  // that have no legacy ordinal). The legacy adapter still forwards to the
  // identical dispatch_legacy_lightshow() for legacy rows, so on-plate output
  // for those is byte-identical to the non-registry path. Fail-safe: if the
  // boot self-check failed, or no row owns this ordinal, drop to the legacy
  // adapter (which clamps an out-of-range mode to its fallback). The native
  // ordinals carry their own stable id in ctx.legacyMode is irrelevant — native
  // IEffects ignore the legacy-bridge fields.
  IEffect* effect = nullptr;
  if (registry_is_healthy()) {
    const EffectEntry* entry = entry_for_runtime_ordinal(mode);
    if (entry != nullptr) {
      effect = entry->effect;
    }
  }
  if (effect == nullptr) {
    effect = legacy_effect_for_mode(mode);  // fail-safe to the legacy spine
  }
  effect->render(ctx);
#else
  IEffect* effect = legacy_effect_for_mode(mode);
  effect->render(ctx);  // → LegacyEffectAdapter → dispatch_legacy_lightshow(mode, channel, seeded)
#endif  // K1_EFFECT_REGISTRY_V1
}
#endif  // K1_EFFECT_FRAMEWORK_V1

void store_render_channel_output(RenderChannelState& channel) {
  if (channel.output != leds_16) {
    memcpy(channel.output, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  }
}

// Effects-queue CROSSFADE overlay (spec §2): while a channel is crossfading,
// render the INCOMING state a second time on the dedicated TRANSITION SCRATCH
// block (never the live block) and blend it equal-power into leds_16 over the
// outgoing frame. Runs inside the channel's own render pass, so the shared
// k1_queue_xfade_out_buf snapshot is never contended between channels. The
// params stack is depth-2: primary overlay pushes at depth 0; secondary
// overlay pushes above the already-pushed secondary params.
void render_queue_xfade_overlay(bool secondary) {
  float gain_out = 1.0f;
  float gain_in = 0.0f;
  uint8_t incoming_mode = 0;
  float incoming_prism = 0.0f;
  const uint32_t now_ms = uint32_t(esp_timer_get_time() / 1000);
  if (!k1_queue_xfade_overlay_begin(secondary, now_ms, &gain_out, &gain_in,
                                    &incoming_mode, &incoming_prism)) {
    return;
  }

  // Snapshot the outgoing frame, then render the incoming state into leds_16.
  memcpy(k1_queue_xfade_out_buf, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);

  K1QueueXfadeScratch* scratch = k1_queue_xfade_scratch(secondary);
  RenderChannelState channel;
  channel.history = scratch->history;
  channel.output = leds_16;  // blended in place; the live pass stores afterwards
  channel.seed_history_before_render = secondary;  // mirrors the live channels
  channel.waveform_fast_last_color = &scratch->wf_fast_last_color;
  channel.waveform_fast_peak_scaled_last = &scratch->wf_fast_peak_scaled_last;
  channel.waveform_fast_shift_accum = &scratch->wf_fast_shift_accum;
  channel.waveform_fast_last_frame_ms = &scratch->wf_fast_last_frame_ms;
  channel.waveform_last_color = &scratch->wf_last_color;
  channel.waveform_peak_scaled_last = &scratch->wf_peak_scaled_last;
  channel.waveform_shift_accum = &scratch->wf_shift_accum;
  channel.waveform_last_frame_ms = &scratch->wf_last_frame_ms;
  channel.waveform_hybrid_last_color = &scratch->wf_hybrid_last_color;
  channel.waveform_hybrid_peak_scaled_last = &scratch->wf_hybrid_peak_scaled_last;
  channel.waveform_hybrid_shift_accum = &scratch->wf_hybrid_shift_accum;
  channel.waveform_hybrid_last_frame_ms = &scratch->wf_hybrid_last_frame_ms;
  channel.vu_level_smooth = &scratch->vu_level_smooth;
  channel.vu_max_level = &scratch->vu_max_level;
  channel.effect = &scratch->effect;

  // The incoming fields were temp-applied by overlay_begin(), so a freshly
  // built params snapshot carries the TARGET configuration for this pass.
  RenderParams xfade_params = secondary ? build_secondary_render_params()
                                        : build_primary_render_params();
  push_render_params(&xfade_params);
  render_lightshow_for_channel(incoming_mode, channel);
  if (!VP_FIX_PRISM_DEFAULT_OFF && incoming_prism > 0) {
    apply_prism_effect(incoming_prism, 0.25);
  }
  pop_render_params();
  k1_queue_xfade_overlay_end(secondary);  // restore the outgoing live fields

#ifdef K1_EFFECT_FRAMEWORK_V1
  // P4: centre-origin TransitionEngine drives the crossfade. Source = outgoing
  // snapshot, target = incoming frame (just rendered into leds_16), output =
  // leds_16 (blended in place). The queue's xfade duration is honoured; the
  // equal-power gains are no longer used on this path. If the engine is not ready
  // (PSRAM alloc failed at boot) we fall through to the legacy equal-power blend.
  if (k1::effects::framework::transitionBlendChannel(
          secondary, k1_queue_xfade_out_buf, leds_16, leds_16,
          k1_queue_xfade_ms())) {
    return;
  }
#endif

  // Equal-power blend: outgoing snapshot + incoming frame.
  const SQ15x16 g_out = SQ15x16(gain_out);
  const SQ15x16 g_in = SQ15x16(gain_in);
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r = k1_queue_xfade_out_buf[i].r * g_out + leds_16[i].r * g_in;
    leds_16[i].g = k1_queue_xfade_out_buf[i].g * g_out + leds_16[i].g * g_in;
    leds_16[i].b = k1_queue_xfade_out_buf[i].b * g_out + leds_16[i].b * g_in;
  }
}

void attempt_rotate8_init(bool verbose) {
#if K1_HAS_ROTATE8
  bool rotate8_initialized = false;
  const int max_attempts = verbose ? 3 : 1;
  for (int attempt = 0; attempt < max_attempts && !rotate8_initialized; attempt++) {
    if (verbose) {
      USBSerial.print("Attempting to initialize M5Rotate8 (Attempt ");
      USBSerial.print(attempt + 1);
      USBSerial.print("/");
      USBSerial.print(max_attempts);
      USBSerial.println(")...");
    }
    Wire.end();
    delay(50);
    Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
    delay(50);
    rotate8_initialized = rotate8.begin();
    if (rotate8_initialized) {
      g_rotate8_available = true;
      if (verbose) {
        USBSerial.println("M5Rotate8 Initialized Successfully.");
        uint8_t version = rotate8.getVersion();
        USBSerial.print("Firmware Version: ");
        USBSerial.println(version);
      } else {
        USBSerial.println("M5Rotate8 recovered successfully!");
      }
      for (uint8_t i = 0; i < 9; i++) {
        rotate8.writeRGB(i, 0, 0, 0);
      }
    } else {
      g_rotate8_available = false;
      if (verbose) {
        USBSerial.println("M5Rotate8 Initialization FAILED. Retrying...");
      }
      delay(200);
    }
  }
  if (!rotate8_initialized) {
    if (verbose) {
      USBSerial.println("WARNING: M5Rotate8 failed to initialize after multiple attempts!");
      USBSerial.println("System will continue in fallback mode without encoders.");
      USBSerial.println("Encoders will be checked periodically for reconnection.");
    }
    g_next_recovery_attempt = millis() + 10000;
  }
#else
  (void)verbose;
  g_rotate8_available = false;
  g_next_recovery_attempt = 0;
#endif
}

// Setup, runs only one time ---------------------------------------------------------
void setup() {
#ifdef K1_BOOTLOOP_GUARD_V1
  // N2b boot-loop guard: evaluate the crash streak BEFORE the first heap alloc below
  // (which can itself crash) and BEFORE init_system()/load_config() consume safe mode.
  // USBSerial is not up yet here (init_serial runs inside init_system); the visible
  // BOOT_LOOP_GUARD line is emitted just after init_system() returns.
  {
    const esp_reset_reason_t k1_rr = esp_reset_reason();
    const int k1_is_poweron = (k1_rr == ESP_RST_POWERON || k1_rr == ESP_RST_UNKNOWN);
    const int k1_is_crash = k1_bootloop_reason_is_crash(k1_rr);
    k1_boot_safe_mode =
        (k1_bootloop_eval(&k1_bootloop_rtc, k1_is_poweron, k1_is_crash,
                          K1_BOOTLOOP_THRESHOLD) == K1_BOOT_SAFE_MODE);
  }
#endif
  const size_t wh_bytes = sizeof(short) * 4 * 1024;
  waveform_history = (short(*)[1024])heap_caps_malloc(wh_bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!waveform_history) {
    waveform_history = (short(*)[1024])malloc(wh_bytes);
  }
  if (waveform_history) {
    memset(waveform_history, 0, wh_bytes);
  }

  init_system();  // (system.h) Initialize all hardware and arrays
#ifdef K1_BOOTLOOP_GUARD_V1
  // N2b: report the boot-loop decision now that init_serial() (inside init_system)
  // has brought USBSerial up. The eval ran at the top of setup(); load_config() has
  // already honoured safe mode during init_fs().
  USBSerial.print("BOOT_LOOP_GUARD: reset_reason=");
  USBSerial.print((int)esp_reset_reason());
  USBSerial.print(" fail_count=");
  USBSerial.print(k1_bootloop_rtc.fail_count);
  USBSerial.print(" safe_mode=");
  USBSerial.println(k1_boot_safe_mode ? 1 : 0);
#endif
  k1_tempo_init(); // (k1_tempo.h) compute tempo Goertzel coeffs once — REQUIRED or tempo never locks

  // Snap any saved-but-disabled light mode to the nearest enabled one (2026-06-02:
  // GDFT/VU_DOT/KALEIDOSCOPE/QUANTUM_COLLAPSE/VU removed as unfit for purpose).
  CONFIG.LIGHTSHOW_MODE = light_mode_next_enabled(CONFIG.LIGHTSHOW_MODE, 1);
  SECONDARY_LIGHTSHOW_MODE = light_mode_next_enabled(SECONDARY_LIGHTSHOW_MODE, 1);
  K1_TRACE_INIT(64);

  // Compute the EdgeMixer colour maps for the shipping default at boot. The static
  // k1_edge_config bypasses k1_edgemixer_set_config() — which builds the OKLab fused
  // map + harmony matrix — so enable-by-default would otherwise render the first frames
  // through identity/uncomputed maps. This one call makes the boot render correct from
  // frame 1 (gate-3 enable-by-default, Captain 2026-07-09).
  k1_edgemixer_set_config(k1_edgemixer_config());

  USBSerial.print("WAVEFORM_HISTORY: ");
  if (waveform_history) {
    USBSerial.print("OK @ 0x");
    USBSerial.println((uint32_t)waveform_history, HEX);
  } else {
    USBSerial.println("FAIL (alloc returned NULL — feature disabled)");
  }

#if K1_HAS_ROTATE8
  init_encoders();
#else
  g_rotate8_available = false;
#endif

  init_secondary_leds();
  ENABLE_SECONDARY_LEDS = true;   // Dual-channel (incl. K1_CUSTOM_LED_V1 dual-214 wall build)
#ifdef K1_WIRELESS_ENABLED
  k1_wireless_begin();
#endif
#ifdef K1_BLE_REMOTED
  k1_ble_remoted_begin();
#endif

#if ENABLE_FASTLED_COLOR_CORRECTION
  // Phase 1 Change 2: apply WS2812 channel correction globally (both strips)
  // after both addLeds<> registrations have run. TypicalLEDStrip scales channels
  // to compensate WS2812B's brighter green channel — "white" becomes warm.
  FastLED.setCorrection(TypicalLEDStrip);
#endif

  if (CONFIG.BOOT_ANIMATION == true) {
    intro_animation();
  }

  for (uint16_t x = 0; x < CONFIG.LED_COUNT; x++) {
    leds_out[x] = CRGB(0, 0, 0);
  }
  for (uint16_t x = 0; x < SECONDARY_LED_COUNT; x++) {
    leds_out_secondary[x] = CRGB(0, 0, 0);
  }
  FastLED.show();

  // Create thread specifically for LED updates
  BaseType_t led_task_create_result = xTaskCreatePinnedToCore(
    led_thread, "led_task", 8192, NULL, tskIDLE_PRIORITY + 1, &led_task, K1_LED_TASK_CORE);
  const int ap_core = xPortGetCoreID();
  const bool ledTaskCreated = (led_task_create_result == pdPASS);
  const bool timingOk = (CONFIG.SAMPLE_RATE == DEFAULT_SAMPLE_RATE)
    && (CONFIG.SAMPLES_PER_CHUNK == DEFAULT_SAMPLES_PER_CHUNK);
  const bool coreOk = ledTaskCreated && (ap_core != K1_LED_TASK_CORE);
  USBSerial.print("RUNTIME_TIMING_GUARD: timing_ok=");
  USBSerial.print(timingOk ? 1 : 0);
  USBSerial.print(" sample_rate=");
  USBSerial.print(CONFIG.SAMPLE_RATE);
  USBSerial.print(" samples_per_chunk=");
  USBSerial.print(CONFIG.SAMPLES_PER_CHUNK);
  USBSerial.print(" tempo_decim=");
  USBSerial.print((uint16_t)K1_TEMPO_NOVELTY_DECIMATION);
  USBSerial.print(" declared_ap_hz=");
  USBSerial.print((float)CONFIG.SAMPLE_RATE / (float)CONFIG.SAMPLES_PER_CHUNK, 3);
  USBSerial.print(" declared_nov_hz=");
  USBSerial.print(((float)CONFIG.SAMPLE_RATE / (float)CONFIG.SAMPLES_PER_CHUNK) / (float)K1_TEMPO_NOVELTY_DECIMATION, 3);
  USBSerial.print(" response_gain=");
  USBSerial.print(audio_response_gain_clamped(), 3);
  USBSerial.print(" dma_desc=");
  USBSerial.print(K1_I2S_DMA_DESC_NUM);
  USBSerial.print(" ap_core=");
  USBSerial.print(ap_core);
  USBSerial.print(" vp_core=");
  USBSerial.print(K1_LED_TASK_CORE);
  USBSerial.print(" core_ok=");
  USBSerial.print(coreOk ? 1 : 0);
  USBSerial.print(" vp_task_created=");
  USBSerial.println(ledTaskCreated ? 1 : 0);

#ifdef K1_AUDIO_FREEZE_GUARD_V1
  // N2: pin the task-watchdog timeout (IDF auto-inits TWDT at boot; reconfigure
  // makes our 5s contract explicit + independent of the arduino default, keeping
  // the stock core-0 idle check), then subscribe the audio loopTask. led_thread
  // subscribes itself at entry.
  {
    esp_task_wdt_config_t k1_wdt_cfg = { K1_TASK_WDT_TIMEOUT_MS, 0x1u, true }; // {timeout_ms, idle_core_mask, trigger_panic}
    esp_task_wdt_reconfigure(&k1_wdt_cfg);
  }
  enableLoopWDT();  // subscribe loopTask (core 0, audio) to the TWDT
#endif
}

#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
static void k1_ap_cadence_capture_frame(uint32_t t_now,
                                        uint32_t frame_index,
                                        int64_t loop_start_us,
                                        uint32_t gdft_elapsed_us,
                                        uint32_t novelty_elapsed_us,
                                        uint8_t stage) {
  APCadenceFrameInput ap_cadence_frame = {};
  ap_cadence_frame.boot_ms = t_now;
  ap_cadence_frame.frame_index = frame_index;
  ap_cadence_frame.frame_ms = t_now;
  ap_cadence_frame.gdft_elapsed_us = gdft_elapsed_us;
  ap_cadence_frame.novelty_elapsed_us = novelty_elapsed_us;
  ap_cadence_frame.total_ap_loop_elapsed_us = (uint32_t)(esp_timer_get_time() - loop_start_us);
  ap_cadence_frame.stage = stage;
  ap_cadence_frame.ap_core_id = (int8_t)xPortGetCoreID();
  ap_cadence_frame.vp_core_id = k1_ap_cadence_vp_core_id;
  ap_cadence_frame.i2s = k1_audio_i2s_read_debug_read();
  ap_cadence_frame.tempo = k1_tempo_debug_read();
  ap_cad_capture_tick(ap_cadence_frame);
  ap_cad_soak_tick(ap_cadence_frame);
}
#endif

// Loop, runs forever after setup() --------------------------------------------------
void loop() {
#ifdef K1_AUDIO_FREEZE_GUARD_V1
  feedLoopWDT();  // N2: feed the audio-loop watchdog every iteration (~133 Hz << 5s)
#endif
  uint32_t t_now_us = micros();        // Timestamp for this loop, used by some core functions
  uint32_t t_now = t_now_us / 1000.0;  // Millisecond version
#ifdef K1_BOOTLOOP_GUARD_V1
  // N2b: once the device has run K1_BOOTLOOP_STABLE_MS without crashing, this boot is
  // "good" — clear the crash streak so the next reboot starts clean. Fires once, and
  // never on the first tick (clearing too early would defeat the guard).
  static bool k1_bootloop_marked_stable = false;
  if (!k1_bootloop_marked_stable && t_now > K1_BOOTLOOP_STABLE_MS) {
    k1_bootloop_mark_stable(&k1_bootloop_rtc);
    k1_bootloop_marked_stable = true;
    USBSerial.println("BOOT_LOOP_GUARD: stable_clear=1");
  }
#endif
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  static uint32_t ap_cadence_frame_index = 0;
  const uint32_t ap_cadence_frame_index_now = ap_cadence_frame_index++;
  const int64_t ap_cadence_loop_start_us = esp_timer_get_time();
  uint32_t ap_cadence_gdft_us = 0;
  uint32_t ap_cadence_novelty_us = 0;
#endif

  function_id = 0;     // These are for debug_function_timing() in system.h to see what functions take up the most time
  check_knobs(t_now);  // (knobs.h)
  // Check if the knobs have changed

  function_id = 1;
  check_buttons(t_now);  // (buttons.h)
  // Check if the buttons have changed

  function_id = 2;
  check_settings(t_now);  // (system.h)
  // Check if the settings have changed

  function_id = 3;
  check_serial(t_now);  // (serial_menu.h)
  // Check if UART commands are available
#ifdef K1_WIRELESS_ENABLED
  k1_wireless_poll(t_now);
#endif
#ifdef K1_BLE_REMOTED
  k1_ble_remoted_poll(t_now);
#endif

  function_id = 5;
#if ENABLE_VP_PERF_AUDIT
  int64_t vp_perf_stage_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
  acquire_sample_chunk(t_now);  // (i2s_audio.h)
#if ENABLE_VP_PERF_AUDIT
  if (vp_perf.running && vp_perf_stage_start_us != 0) {
    vp_perf_record(vp_perf.audio_acq, uint32_t(esp_timer_get_time() - vp_perf_stage_start_us));
  }
#endif
  // Capture a frame of I2S audio (holy crap, FINALLY something about sound)

  function_id = 6;
  run_sweet_spot();  // (led_utilities.h)
  // Based on the current audio volume, alter the Sweet Spot indicator LEDs

  // Calculates audio loudness (VU) using RMS, adjusting for noise floor based on calibration
#if ENABLE_VP_PERF_AUDIT
  vp_perf_stage_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
  calculate_vu();
#if ENABLE_VP_PERF_AUDIT
  if (vp_perf.running && vp_perf_stage_start_us != 0) {
    vp_perf_record(vp_perf.vu, uint32_t(esp_timer_get_time() - vp_perf_stage_start_us));
  }
#endif

#if K1_ACQUISITION_ONLY_PROBE && ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  k1_ap_cadence_capture_frame(t_now,
                              ap_cadence_frame_index_now,
                              ap_cadence_loop_start_us,
                              0,
                              0,
                              K1_AP_STAGE_ACQUISITION);
  vTaskDelay(1);
  return;
#endif

  function_id = 7;
#if ENABLE_VP_PERF_AUDIT
  vp_perf_stage_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  int64_t ap_cadence_stage_start_us = esp_timer_get_time();
#endif
  process_GDFT();  // (GDFT.h)
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  ap_cadence_gdft_us = (uint32_t)(esp_timer_get_time() - ap_cadence_stage_start_us);
#endif
#ifdef K1_LOUD_GUARD_V1
  k1_loud_guard_update(t_now);
#endif
#ifdef K1_PIN_EVIDENCE_V1
  k1_pin_evidence_set_ap_metrics(t_now);
#endif
#if ENABLE_VP_PERF_AUDIT
  if (vp_perf.running && vp_perf_stage_start_us != 0) {
    vp_perf_record(vp_perf.gdft, uint32_t(esp_timer_get_time() - vp_perf_stage_start_us));
  }
#endif
#if K1_AP_STAGE_PROBE_STOP_STAGE == K1_AP_STAGE_GDFT && ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  k1_ap_cadence_capture_frame(t_now,
                              ap_cadence_frame_index_now,
                              ap_cadence_loop_start_us,
                              ap_cadence_gdft_us,
                              0,
                              K1_AP_STAGE_GDFT);
  vTaskDelay(1);
  return;
#endif
  // Execute GDFT and post-process
  // (If you're wondering about that weird acronym, check out the source file)

  // Send AGC debug data if enabled
  stream_agc_data(t_now);
  stream_vp_data(t_now);
  stream_vp_perf_data(t_now);
#ifdef ENABLE_AP_STREAM
  ap_capture_tick();   // PIO-APCAP: sample windowed AP capture here — post-GDFT, spectrogram/chromagram fresh
#endif

  // Watches the rate of change in the Goertzel bins to guide decisions for auto-colour shifting.
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  ap_cadence_stage_start_us = esp_timer_get_time();
#endif
  calculate_novelty(t_now);
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  ap_cadence_novelty_us = (uint32_t)(esp_timer_get_time() - ap_cadence_stage_start_us);
#endif
#if K1_AP_STAGE_PROBE_STOP_STAGE == K1_AP_STAGE_NOVELTY && ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  k1_ap_cadence_capture_frame(t_now,
                              ap_cadence_frame_index_now,
                              ap_cadence_loop_start_us,
                              ap_cadence_gdft_us,
                              ap_cadence_novelty_us,
                              K1_AP_STAGE_NOVELTY);
  vTaskDelay(1);
  return;
#endif
  K1SmartDirectorConfig ap_smart_config = k1_smart_director_config();
  K1VisualHookConfig ap_hook_config = k1_visual_hooks_config();
  // Always refresh the AP snapshot + onset/beat stream so onset-driven effects
  // (e.g. Comet) work even when the Smart-Director/hooks are disabled. Cost is
  // negligible; the director still only READS this stream when enabled.
  (void)ap_smart_config;
  (void)ap_hook_config;
  {
    k1_audio_snapshot_update(t_now);
    const K1AudioSnapshot k1_audio_snapshot = k1_audio_snapshot_read();
#if K1_AP_STAGE_PROBE_STOP_STAGE == K1_AP_STAGE_SNAPSHOT && ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    k1_ap_cadence_capture_frame(t_now,
                                ap_cadence_frame_index_now,
                                ap_cadence_loop_start_us,
                                ap_cadence_gdft_us,
                                ap_cadence_novelty_us,
                                K1_AP_STAGE_SNAPSHOT);
    vTaskDelay(1);
    return;
#endif
    k1_onset_beat_update(k1_audio_snapshot);
    const K1OnsetBeatEvent k1_onset_beat_event = k1_onset_beat_read();
#if K1_AP_STAGE_PROBE_STOP_STAGE == K1_AP_STAGE_ONSET && ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    k1_ap_cadence_capture_frame(t_now,
                                ap_cadence_frame_index_now,
                                ap_cadence_loop_start_us,
                                ap_cadence_gdft_us,
                                ap_cadence_novelty_us,
                                K1_AP_STAGE_ONSET);
    vTaskDelay(1);
    return;
#endif
    k1_musical_saliency_update(k1_audio_snapshot, &k1_onset_beat_event);
#if K1_AP_STAGE_PROBE_STOP_STAGE == K1_AP_STAGE_SALIENCY && ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    k1_ap_cadence_capture_frame(t_now,
                                ap_cadence_frame_index_now,
                                ap_cadence_loop_start_us,
                                ap_cadence_gdft_us,
                                ap_cadence_novelty_us,
                                K1_AP_STAGE_SALIENCY);
    vTaskDelay(1);
    return;
#endif
    k1_tempo_update(k1_audio_snapshot);  // beat/tempo-phase tracker (Core-0; self-clocks to 50 Hz, read-only consumer of novelty)
#if K1_AP_STAGE_PROBE_STOP_STAGE == K1_AP_STAGE_TEMPO && ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    k1_ap_cadence_capture_frame(t_now,
                                ap_cadence_frame_index_now,
                                ap_cadence_loop_start_us,
                                ap_cadence_gdft_us,
                                ap_cadence_novelty_us,
                                K1_AP_STAGE_TEMPO);
    vTaskDelay(1);
    return;
#endif
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    {
      k1_ap_cadence_capture_frame(t_now,
                                  ap_cadence_frame_index_now,
                                  ap_cadence_loop_start_us,
                                  ap_cadence_gdft_us,
                                  ap_cadence_novelty_us,
                                  K1_AP_STAGE_FULL);
    }
#endif
#if ENABLE_TEMPO_STREAM
    stream_tempo_data(t_now);   // NON-SHIPPABLE: post-update tempo-lock proof CSV (k1_tempo_probe only)
#endif
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
    stream_ap_frontend_debug(t_now);  // NON-SHIPPABLE: full-rate accepted novelty + same-frame AP/AGC/tempo state
#endif
  }

  if (CONFIG.AUTO_COLOR_SHIFT == true) {  // Automatically cycle colour or palette phase based on spectral changes
    // Use the "novelty" findings of the above function to affect colour shifting when auto-colour shifts are enabled
    process_color_shift();
  } else {
    hue_position = 0;
    hue_shifting_mix = -0.35;
  }

  function_id = 8;
  //lookahead_smoothing();  // (GDFT.h)
  // Peek at upcoming frames to study/prevent flickering

  function_id = 8;
  log_fps(t_now_us);  // (system.h)
  // Log the audio system FPS

  // --- BENCHMARK LOGIC --- 
  if (benchmark_running) {
    uint32_t current_time = millis();
    if (current_time - benchmark_start_time < benchmark_duration) {
      // Accumulate FPS data
      system_fps_sum += SYSTEM_FPS; // Assumes SYSTEM_FPS is updated before this point
      led_fps_sum += LED_FPS;       // Assumes LED_FPS is updated before this point
      benchmark_sample_count++;
    } else {
      // Benchmark finished
      benchmark_running = false;
      float avg_system_fps = (benchmark_sample_count > 0) ? (float)system_fps_sum / benchmark_sample_count : 0.0f;
      float avg_led_fps = (benchmark_sample_count > 0) ? (float)led_fps_sum / benchmark_sample_count : 0.0f;
      
      tx_begin(); // Use the tx_begin/end functions from serial_menu.h for formatted output
      USBSerial.println("Benchmark Complete!");
      USBSerial.print("  Average System FPS: ");
      USBSerial.println(avg_system_fps, 2);
      USBSerial.print("  Average LED FPS: ");
      USBSerial.println(avg_led_fps, 2);
      USBSerial.print("  Samples collected: ");
      USBSerial.println(benchmark_sample_count);
      tx_end();

      // Reset sums and count for next run
      system_fps_sum = 0;
      led_fps_sum = 0;
      benchmark_sample_count = 0;
    }
  }
  // --- END BENCHMARK LOGIC ---

#if K1_HAS_ROTATE8
  check_encoders(t_now); // Check wired encoders
  update_encoder_leds(); // Update wired encoder LEDs
#endif

  if (debug_mode == true) {
    function_id = 31;
    debug_function_timing(t_now);
  }

  // N2c: give CPU0's IDLE task a real FreeRTOS slot. yield() can immediately
  // reschedule loopTask and does not reliably feed the watched IDLE0 task.
  vTaskDelay(1);
}

// Run the lights in their own thread! -------------------------------------------------------------
void led_thread(void* arg) {
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
  k1_ap_cadence_vp_core_id = (int8_t)xPortGetCoreID();
#endif
#ifdef K1_EFFECT_FRAMEWORK_V1
  // P4: allocate the two per-channel TransitionEngine instances + CRGB scratch
  // ONCE, here on the render task before the frame loop, after init_system() has
  // brought up PSRAM. If allocation fails the overlay reports not-ready and the
  // crossfade seam keeps the legacy equal-power blend (graceful degrade).
  k1::effects::framework::transitionOverlayInit(NATIVE_RESOLUTION);
#ifdef K1_EFFECT_REGISTRY_V1
  // R2-core: bind + self-check the EffectRegistry ONCE on the render task before
  // the frame loop. registry_boot() latches the health result; on failure
  // registry_is_healthy() stays false and render_channel_via_framework() drops
  // to the legacy adapter spine (fail-safe, no crash). Logged for evidence.
  {
    const bool registry_ok = k1::effects::framework::registry_boot();
    USBSerial.print("K1_EFFECT_REGISTRY_V1 boot self-check: ");
    USBSerial.println(registry_ok ? "PASS" : "FAIL (legacy fallback)");
  }
#endif
#endif
#ifdef K1_AUDIO_FREEZE_GUARD_V1
  if (esp_task_wdt_status(NULL) != ESP_OK) {
    esp_task_wdt_add(NULL);  // N2: subscribe led_task (core 1) to the TWDT
  }
#endif
  while (true) {
#ifdef K1_AUDIO_FREEZE_GUARD_V1
    esp_task_wdt_reset();  // N2: feed the render-task watchdog each frame
#endif
#ifdef K1_EFFECT_FRAMEWORK_V1
    // CL-1 ack-barrier: when the flash/preset path requests a halt, park here at
    // frame-top and publish the acknowledgement BEFORE touching any PSRAM. The
    // framework render reads/writes PSRAM, which faults during a flash-write
    // cache-disable window; parking guarantees we are idle for that window.
    // Self-heal watchdog: a missed unlock_leds() (e.g. an early-return on the
    // flash path) must NEVER freeze the show. If parked far longer than any
    // legitimate flash-write window, force-resume — no LittleFS/NVS write runs
    // anywhere near this long, so the residual fault window is negligible.
    static int64_t led_park_start_us = 0;
    if (led_thread_halt == true) {
      render_thread_parked = true;
      const int64_t park_now_us = esp_timer_get_time();
      if (led_park_start_us == 0) {
        led_park_start_us = park_now_us;
      } else if (park_now_us - led_park_start_us > 1000000) {  // 1 s self-heal
        led_thread_halt = false;  // force-resume; a stuck halt must not freeze the plate
        led_park_start_us = 0;
      }
      if (led_thread_halt == true) {
        vTaskDelay(1);
        continue;
      }
    }
    led_park_start_us = 0;
    render_thread_parked = false;
#endif
    if (led_thread_halt == false) {
      int64_t vp_frame_start_us = esp_timer_get_time();
      int64_t vp_render_start_us = vp_frame_start_us;
#if ENABLE_VP_PERF_AUDIT
      if (vp_perf.running) {
        vp_perf_note_frame_start(uint32_t(vp_frame_start_us));
      }
#endif

#ifdef ENABLE_MOTION_PROBE
      // NON-SHIPPING: apparent-motion test harness. When armed it OWNS the frame
      // — it writes the stimulus into leds_16[] and reuses the SAME canonical
      // show path (show_leds) as the normal render, then yields. The shipping
      // visual roster is never reached while the probe is active.
      if (mp_active) {
        motion_probe_render_frame();
        show_leds();
        LED_FPS = 0.95 * LED_FPS + 0.05 * (1000000.0 / (esp_timer_get_time() - last_frame_us));
        last_frame_us = esp_timer_get_time();
        vTaskDelay(1);
        continue;
      }
#endif

#ifdef ENABLE_VP_MOTION_LAB
      // NON-SHIPPABLE: VP Motion Lab built-in preview harness. It owns the frame
      // only while armed, writes both VP buffers, sets VPAB context, then uses the
      // canonical show path. The shipping visual roster is skipped for that frame.
      if (vpml_is_active()) {
        vpml_render_frame();

        uint32_t vpml_render_elapsed_us = (uint32_t)(esp_timer_get_time() - vp_render_start_us);
        vp_render_us_last = vpml_render_elapsed_us;
        if (vpml_render_elapsed_us > vp_render_us_max) {
          vp_render_us_max = vpml_render_elapsed_us;
        }
        vp_render_us_avg = (vp_render_us_avg == 0) ? vpml_render_elapsed_us : ((vp_render_us_avg * 15) + vpml_render_elapsed_us) / 16;

        vpml_set_vpab_context();
        show_leds();
#if ENABLE_VP_PERF_AUDIT
        if (vp_perf.running) {
          vp_perf_note_frame_total(uint32_t(esp_timer_get_time() - vp_frame_start_us));
        }
#endif
        LED_FPS = 0.95 * LED_FPS + 0.05 * (1000000.0 / (esp_timer_get_time() - last_frame_us));
        last_frame_us = esp_timer_get_time();
        vTaskDelay(1);
        continue;
      }
#endif

      if (mode_transition_queued == true || noise_transition_queued == true) {
        run_transition_fade();
      }

      // Effects-queue frame-boundary engine: consumes commit requests armed by
      // the serial side, advances dip/crossfade transitions, and lands all
      // committed per-channel field swaps BEFORE channel construction — never
      // mid-frame (mode_transition_queued precedent).
      k1_effect_queue_frame_tick(uint32_t(vp_frame_start_us / 1000));

#if ENABLE_VP_PERF_AUDIT || FEATURE_TRACE_RENDER
      int64_t vp_perf_stage_start_us = 0;
#if FEATURE_TRACE_RENDER
      vp_perf_stage_start_us = esp_timer_get_time();
#else
      vp_perf_stage_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
#endif
      get_smooth_spectrogram();
      make_smooth_chromagram();
#if ENABLE_VP_PERF_AUDIT
      if (vp_perf.running && vp_perf_stage_start_us != 0) {
        vp_perf_record(vp_perf.smooth, uint32_t(esp_timer_get_time() - vp_perf_stage_start_us));
      }
#endif

      // Render primary channel through the shared channel dispatcher.
      vp_render_secondary_channel = false;
#if ENABLE_VP_PERF_AUDIT || FEATURE_TRACE_RENDER
      vp_perf_stage_start_us = 0;
#if FEATURE_TRACE_RENDER
      vp_perf_stage_start_us = esp_timer_get_time();
#else
      vp_perf_stage_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
#endif
		      RenderChannelState primary_channel = make_primary_channel();
		      K1VisualHookOutput visual_hook_output = { 1.0f, 1.0f, 1.0f, false };
		      K1SmartDirectorConfig smart_director_config = k1_smart_director_config();
		      K1VisualHookConfig visual_hook_config = k1_visual_hooks_config();
		      uint8_t vpab_primary_render_mode = CONFIG.LIGHTSHOW_MODE;
#ifdef K1_EDGEMIXER_AB_DEMO
		      // BENCH-ONLY: force + cycle the EdgeMixer mode BEFORE the config read
		      // below, so vpab_edge_base_config picks up the forced config. The only
		      // later mutation (k1_visual_hooks_apply_edge_config) scales strength
		      // only, so the forced mode/spread reach k1_edgemixer_apply intact.
		      k1_edgemixer_ab_demo_tick();
#endif
		      K1EdgeMixerConfig vpab_edge_base_config = k1_edgemixer_config();
		      K1EdgeMixerConfig vpab_edge_effective_config = vpab_edge_base_config;
#ifdef K1_EFFECT_FRAMEWORK_V1
		      // P6: when the K1-native beat-aware director is enabled (flag-ON,
		      // opt-in) it OWNS primary mode selection. It un-whitelists across the
		      // full enabled-mode set and, on a beat-quantised switch, arms the
		      // effects queue in XFADE style so render_queue_xfade_overlay() drives
		      // the centre-origin TransitionEngine with tempo-derived timing. The
		      // queue's frame tick (already called above) lands the swap; we render
		      // the director's current mode here. Falls through to SmartDirector /
		      // legacy when disabled (default), keeping flag-OFF byte-unchanged.
		      if (bad_director_enabled()) {
		        uint32_t bad_now_ms = uint32_t(vp_frame_start_us / 1000);
		        uint8_t bad_primary_mode = bad_director_tick(bad_now_ms);
		        vpab_primary_render_mode = bad_primary_mode;
		        RenderParams bad_pp = build_primary_render_params();
		        push_render_params(&bad_pp);
		        render_channel_via_framework(bad_primary_mode, primary_channel);
		        pop_render_params();
		      } else
#endif
		      if (smart_director_config.enabled || visual_hook_config.enabled) {
	        K1AudioSnapshot smart_audio = {};
	        K1OnsetBeatEvent smart_event = {};
	        {
	          K1_TRACE_SCOPE("vp_bus_read");
	          smart_audio = k1_audio_snapshot_read();
	          smart_event = k1_onset_beat_read();
	        }
	        uint32_t smart_now_ms = uint32_t(vp_frame_start_us / 1000);
	        K1SmartDirectorOutput smart_output = k1_smart_director_tick(smart_audio, smart_now_ms, &smart_event);
	        {
	          K1_TRACE_SCOPE("vp_visual_hooks_tick");
	          visual_hook_output = k1_visual_hooks_tick(smart_event, smart_now_ms);
	        }
        bool smart_boundary_gate_required = visual_hook_config.enabled &&
                                            !smart_director_config.director_autonomy_enabled;
        if (smart_boundary_gate_required && !visual_hook_output.confirm_switch_boundary) {
          smart_output.mode_intent.wants_switch = false;
        }
	        uint8_t smart_primary_mode = k1_mode_selection_resolve(
	          smart_output.mode_intent,
	          k1_smart_director_mode_selection_config(smart_now_ms),
	          CONFIG.LIGHTSHOW_MODE,
	          smart_now_ms
	        );
	        vpab_primary_render_mode = smart_primary_mode;
	        RenderParams pp = build_primary_render_params();
        k1_smart_director_apply_render_params(smart_output, &pp);
        k1_visual_hooks_apply_render_params(visual_hook_output, &pp);
        push_render_params(&pp);
#ifdef K1_EFFECT_FRAMEWORK_V1
        render_channel_via_framework(smart_primary_mode, primary_channel);
#else
        render_lightshow_for_channel(smart_primary_mode, primary_channel);
#endif
        pop_render_params();
      } else {
#ifdef K1_EFFECT_FRAMEWORK_V1
        render_channel_via_framework(CONFIG.LIGHTSHOW_MODE, primary_channel);
#else
        render_lightshow_for_channel(CONFIG.LIGHTSHOW_MODE, primary_channel);
#endif
      }

      if (!VP_FIX_PRISM_DEFAULT_OFF && CONFIG.PRISM_COUNT > 0) {
        apply_prism_effect(CONFIG.PRISM_COUNT, 0.25);
      }

      // Effects-queue crossfade: blend the incoming primary state over the
      // outgoing frame while a primary crossfade is active (no-op otherwise).
      render_queue_xfade_overlay(false);

      if (CONFIG.BULB_OPACITY > 0.00) {
        render_bulb_cover();
      }
#if ENABLE_VP_PERF_AUDIT
      if (vp_perf.running) {
        vp_perf_record(vp_perf.primary_render, uint32_t(esp_timer_get_time() - vp_perf_stage_start_us));
      }
#endif
#if FEATURE_TRACE_RENDER
      K1_TRACE_COUNTER("vp_primary_render_us", uint32_t(esp_timer_get_time() - vp_perf_stage_start_us));
#endif
      
      // Render secondary channel with its own state and restore primary runtime afterwards.
      if (ENABLE_SECONDARY_LEDS) {
#if ENABLE_VP_PERF_AUDIT || FEATURE_TRACE_RENDER
        int64_t vp_perf_secondary_start_us = 0;
#if FEATURE_TRACE_RENDER
        vp_perf_secondary_start_us = esp_timer_get_time();
#else
        vp_perf_secondary_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
#endif
        RenderRuntimeSnapshot render_snapshot;
        RenderChannelState secondary_channel;
        RenderParams sp;

        {
          K1_TRACE_SCOPE("vp_secondary_snapshot");
          render_snapshot = capture_render_runtime();
          memcpy(leds_16_primary_snapshot, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
        }

        {
          K1_TRACE_SCOPE("vp_secondary_effect");
          secondary_channel = make_secondary_channel();
          // RenderParams core: secondary render reads its params through the
          // params stack instead of mutating global CONFIG. The modes pull the
          // 9 SECONDARY_* overrides (and primary values for everything else) from
          // active_render_params().
          sp = build_secondary_render_params();
          push_render_params(&sp);
          vp_render_secondary_channel = true;
#ifdef K1_EFFECT_FRAMEWORK_V1
          render_channel_via_framework(SECONDARY_LIGHTSHOW_MODE, secondary_channel);
#else
          render_lightshow_for_channel(SECONDARY_LIGHTSHOW_MODE, secondary_channel);
#endif

          if (!VP_FIX_PRISM_DEFAULT_OFF && SECONDARY_PRISM_COUNT > 0) {
            apply_prism_effect(SECONDARY_PRISM_COUNT, 0.25);
          }

          // Effects-queue crossfade: blend the incoming secondary state over
          // the outgoing frame while a secondary crossfade is active.
          render_queue_xfade_overlay(true);
        }

        {
	          K1_TRACE_SCOPE("vp_secondary_store_clip");
	          store_render_channel_output(secondary_channel);
	          K1EdgeMixerConfig edge_config = vpab_edge_base_config;
	          if (edge_config.enabled) {
	            edge_config = k1_visual_hooks_apply_edge_config(visual_hook_output, edge_config);
	            vpab_edge_effective_config = edge_config;
	            k1_edgemixer_apply(leds_16_secondary, NATIVE_RESOLUTION, edge_config);
	          }
          clip_led_values(leds_16_secondary); // Clip the secondary buffer values
        }

        {
          K1_TRACE_SCOPE("vp_secondary_restore");
          pop_render_params();
          memcpy(leds_16, leds_16_primary_snapshot, sizeof(CRGB16) * NATIVE_RESOLUTION);
          restore_render_runtime(render_snapshot);
        }

        // Symmetric dual-edge (A lane): the primary frame is now restored into
        // leds_16, so apply the PRIMARY-edge transform to it — making BOTH edges
        // shift about the 79/80 centre instead of only the secondary. Gated on the
        // dual-edge mode (ONE_SIDED = primary untouched = byte-inert default) and on
        // the edge being enabled. NEVER touches leds_16_secondary; uses the SAME
        // frozen colour transform baked at the mirrored primary angle, with the same
        // strength scaling the secondary got (vpab_edge_effective_config). Its cost
        // lands in the vp_perf.secondary_render bucket (both edge transforms) and the
        // total vp_render_us frame time.
        bool k1_stm_needs_primary = false;
#ifdef K1_STM
        // STM modes modulate BOTH strips (STM_DUAL: primary <- temporal energy);
        // they run even under ONE_SIDED, so the primary transform must fire for
        // them independently of the dual-edge gate.
        k1_stm_needs_primary =
            (vpab_edge_effective_config.mode == K1_EDGE_MIXER_STM_DUAL ||
             vpab_edge_effective_config.mode == K1_EDGE_MIXER_STM_SPECTRAL_MAP);
#endif
        if (vpab_edge_effective_config.enabled &&
            (vpab_edge_effective_config.dualEdge != K1_EDGE_DUAL_ONE_SIDED ||
             k1_stm_needs_primary)) {
          K1_TRACE_SCOPE("vp_primary_edge");
          k1_edgemixer_apply_primary(leds_16, NATIVE_RESOLUTION, vpab_edge_effective_config);
          clip_led_values(leds_16);
        }

#if ENABLE_VP_PERF_AUDIT
        if (vp_perf.running) {
          vp_perf_record(vp_perf.secondary_render, uint32_t(esp_timer_get_time() - vp_perf_secondary_start_us));
        }
#endif
#if FEATURE_TRACE_RENDER
	        K1_TRACE_COUNTER("vp_secondary_render_us", uint32_t(esp_timer_get_time() - vp_perf_secondary_start_us));
#endif
	      }

#if ENABLE_VPAB_PROBE
	      VPABRenderContext vpab_context = {
	        vpab_primary_render_mode,
	        uint8_t(CONFIG.LIGHTSHOW_MODE),
	        uint8_t(SECONDARY_LIGHTSHOW_MODE),
	        smart_director_config.enabled ? uint8_t(1) : uint8_t(0),
	        visual_hook_config.enabled ? uint8_t(1) : uint8_t(0),
	        vpab_edge_effective_config.enabled ? uint8_t(1) : uint8_t(0),
	        uint8_t(vpab_edge_effective_config.mode),
	        k1_smart_director_manual_owner_active(uint32_t(vp_frame_start_us / 1000)) ? uint8_t(1) : uint8_t(0),
	        uint16_t(constrain(vpab_edge_base_config.strength, 0.0f, 1.0f) * 1000.0f),
	        uint16_t(constrain(vpab_edge_effective_config.strength, 0.0f, 1.0f) * 1000.0f),
		        uint8_t(vpab_edge_effective_config.dualEdge),
		        (vpab_edge_effective_config.enabled &&
		         vpab_edge_effective_config.dualEdge != K1_EDGE_DUAL_ONE_SIDED) ? uint8_t(1) : uint8_t(0),
	      };
	      vpab_capture_set_render_context(vpab_context);
#endif
	      
	      uint32_t vp_render_elapsed_us = (uint32_t)(esp_timer_get_time() - vp_render_start_us);
      vp_render_us_last = vp_render_elapsed_us;
      if (vp_render_elapsed_us > vp_render_us_max) {
        vp_render_us_max = vp_render_elapsed_us;
      }
      vp_render_us_avg = (vp_render_us_avg == 0) ? vp_render_elapsed_us : ((vp_render_us_avg * 15) + vp_render_elapsed_us) / 16;

#ifdef ENABLE_FRAME_DUMP
      frame_dump_tick();   // PIO-FDUMP: sample primary render (leds_16) before display transform
#endif
      show_leds();
#if ENABLE_VP_PERF_AUDIT
      if (vp_perf.running) {
        vp_perf_note_frame_total(uint32_t(esp_timer_get_time() - vp_frame_start_us));
      }
#endif
      
      LED_FPS = 0.95 * LED_FPS + 0.05 * (1000000.0 / (esp_timer_get_time() - last_frame_us));
      last_frame_us = esp_timer_get_time();
    }
    vTaskDelay(1);
  }
}

// // Add this new function to update encoder LEDs - REMOVED
// void update_encoder_leds() {
//   // ... function body ...
// }

// External functions from other files
extern void run_sweet_spot();
extern void show_leds();
extern void stream_agc_data(uint32_t t_now); // Add declaration for AGC debug visualization
extern void stream_vp_data(uint32_t t_now);
