#ifndef LED_UTILITIES_H
#define LED_UTILITIES_H

#include <Arduino.h>
#include <FastLED.h>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
#include <math.h> // For standard math functions if needed
#include "globals.h" // Assuming globals contains necessary definitions
#include "constants.h" // Assuming constants contains necessary definitions
#include "utilities.h" // Row 2: led_utilities uses fabs_fixed/fmod_fixed/random_float (after globals/constants so SQ15x16 is visible)
#ifdef K1_DROP_CUT_V1
#include "k1_audio_snapshot.h" // drop-cut detector reads the published AP snapshot (Core-1 read idiom)
#endif
#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"
#endif
#ifdef K1_BLE_REMOTED
#include "ble_remoted_central.h" // k1_ble_remoted_is_linked() — BLE standby-dim pin
#endif

extern void start_noise_cal();

// Effects-queue DIP transition scalars (control/k1_effect_queue.cpp). Composed
// by multiplication into the final brightness of each channel, at the same
// application points as drop_cut_scale. 1.0 whenever no dip is active.
extern float k1_queue_transition_scale_primary;
extern float k1_queue_transition_scale_secondary;

#ifdef ENABLE_MOTION_PROBE
// NON-SHIPPING: apparent-motion probe state (defined inline in motion_probe.h,
// which is included AFTER this header in the .ino). Forward-declared here so the
// gated silent_scale pin in apply_brightness() can reference it. Compatible with
// the later `inline bool mp_active` definition.
extern bool mp_active;
#endif

#ifdef ENABLE_VP_MOTION_LAB
// NON-SHIPPABLE: VP Motion Lab state is defined inline in vp_motion_lab.h.
// Forward-declared here so apply_brightness() can pin silence dimming only while
// the lab owns the frame.
extern bool vpml_active;
#endif

// Forward declarations for secondary LED functions
void scale_to_secondary_strip();
void apply_brightness_secondary();
void show_secondary_leds();
void init_secondary_leds();
void quantize_color_secondary(bool temporal_dither);

// Forward declarations for internal functions needed before their implementations
CRGB16 adjust_hue_and_saturation(CRGB16 color, SQ15x16 hue, SQ15x16 saturation);

enum blending_modes {
  BLEND_MIX,
  BLEND_ADD,
  BLEND_MULTIPLY,

  NUM_BLENDING_MODES  // used to know the length of this list if it changes in the future
};


inline CRGB16 interpolate_hue(SQ15x16 hue) {
  // Compute hue directly via HSV math — no precomputed table required.
  // Wrap hue into [0,1) so callers that pass cumulative offsets still work.
  float h = float(hue);
  h -= floorf(h);
  if (h < 0.0f) h += 1.0f;

  float h6 = h * 6.0f;
  int sector = int(h6);
  if (sector > 5) sector = 5;
  float f = h6 - float(sector);

  float r = 0.0f, g = 0.0f, b = 0.0f;
  switch (sector) {
    case 0: r = 1.0f;       g = f;          b = 0.0f;       break;  // red    -> yellow
    case 1: r = 1.0f - f;   g = 1.0f;       b = 0.0f;       break;  // yellow -> green
    case 2: r = 0.0f;       g = 1.0f;       b = f;          break;  // green  -> cyan
    case 3: r = 0.0f;       g = 1.0f - f;   b = 1.0f;       break;  // cyan   -> blue
    case 4: r = f;          g = 0.0f;       b = 1.0f;       break;  // blue   -> magenta
    case 5: r = 1.0f;       g = 0.0f;       b = 1.0f - f;   break;  // magenta-> red
  }

  CRGB16 output;
  output.r = SQ15x16(r);
  output.g = SQ15x16(g);
  output.b = SQ15x16(b);
  return output;
}


inline CRGB16 desaturate(CRGB16 input_color, SQ15x16 amount) {
  SQ15x16 luminance = SQ15x16(0.2126) * input_color.r + SQ15x16(0.7152) * input_color.g + SQ15x16(0.0722) * input_color.b;
  SQ15x16 amount_inv = SQ15x16(1.0) - amount;

  CRGB16 output;
  output.r = input_color.r * amount_inv + luminance * amount;
  output.g = input_color.g * amount_inv + luminance * amount;
  output.b = input_color.b * amount_inv + luminance * amount;

  return output;
}

inline SQ15x16 vivid_luminance(CRGB16 input_color) {
  return SQ15x16(0.2126) * input_color.r + SQ15x16(0.7152) * input_color.g + SQ15x16(0.0722) * input_color.b;
}

#ifdef K1_VIVID_PRECOMP_V1
inline void apply_vivid_precomp_count(CRGB16* buffer, uint16_t count) {
  if (!VP_VIVID_PRECOMP) return;
  float chroma_level_float = VP_VIVID_CHROMA_LEVEL;
  if (chroma_level_float < 0.0f) chroma_level_float = 0.0f;
  if (chroma_level_float > 1.0f) chroma_level_float = 1.0f;
  float black_level_float = VP_VIVID_BLACK_LEVEL;
  if (black_level_float < 0.0f) black_level_float = 0.0f;
  if (black_level_float > 1.0f) black_level_float = 1.0f;
  const SQ15x16 chroma_gain = SQ15x16(VIVID_CHROMA_GAIN_MAX) * SQ15x16(chroma_level_float);
  const SQ15x16 luma_cut = SQ15x16(VIVID_LUMA_CUT_MAX) * SQ15x16(black_level_float);
  for (uint16_t i = 0; i < count; i++) {
    CRGB16 vivid = desaturate(buffer[i], -chroma_gain);
    const SQ15x16 common_cut = vivid_luminance(vivid) * luma_cut;
    vivid.r -= common_cut;
    vivid.g -= common_cut;
    vivid.b -= common_cut;
    buffer[i] = vivid;
  }
}
#else
inline void apply_vivid_precomp_count(CRGB16*, uint16_t) {}
#endif

inline CRGB16 hsv(SQ15x16 h, SQ15x16 s, SQ15x16 v) {
  while (h > 1.0) { h -= 1.0; }
  while (h < 0.0) { h += 1.0; }

  CRGB base_color = CHSV(uint8_t(h * 255.0), uint8_t(s * 255.0), 255);

  CRGB16 col = { base_color.r / 255.0, base_color.g / 255.0, base_color.b / 255.0 };
  //col = desaturate(col, SQ15x16(1.0) - s);

  col.r *= v;
  col.g *= v;
  col.b *= v;

  return col;
}

inline void clip_led_values_count(CRGB16* buffer, uint16_t count) {
#if ENABLE_HSV_SOFT_CLIP
  // Phase 2 Change 9 (2026-05-20): hue-preserving soft-clip.
  // When any channel exceeds KNEE, ALL channels scale down so max approaches
  // but never quite reaches 1.0. This preserves the hue ratio at peaks instead
  // of letting per-channel clipping desaturate toward white.
  static const SQ15x16 KNEE = SQ15x16(SOFT_CLIP_KNEE);
  static const SQ15x16 ROLLOFF = SQ15x16(SOFT_CLIP_ROLLOFF);
  static const SQ15x16 ONE = SQ15x16(1.0);
  static const SQ15x16 ZERO = SQ15x16(0.0);
  static const SQ15x16 EPSILON = SQ15x16(0.001);

  for (uint16_t i = 0; i < count; i++) {
    // Floor at zero (same as original)
    if (buffer[i].r < ZERO) buffer[i].r = ZERO;
    if (buffer[i].g < ZERO) buffer[i].g = ZERO;
    if (buffer[i].b < ZERO) buffer[i].b = ZERO;

    // Find max channel
    SQ15x16 m = buffer[i].r;
    if (buffer[i].g > m) m = buffer[i].g;
    if (buffer[i].b > m) m = buffer[i].b;

    if (m > KNEE) {
      // Compress: above knee, compressed_m = KNEE + (m - KNEE) * ROLLOFF
      SQ15x16 compressed_m = KNEE + (m - KNEE) * ROLLOFF;
      if (compressed_m > ONE) compressed_m = ONE;
      // Scale all channels by ratio (guarded against div-by-near-zero)
      if (m > EPSILON) {
        SQ15x16 scale = compressed_m / m;
        buffer[i].r *= scale;
        buffer[i].g *= scale;
        buffer[i].b *= scale;
      }
    }
  }
#else
  // Original hard-clamp (prior behavior)
  for (uint16_t i = 0; i < count; i++) {
    if (buffer[i].r < 0.0) { buffer[i].r = 0.0; }
    if (buffer[i].g < 0.0) { buffer[i].g = 0.0; }
    if (buffer[i].b < 0.0) { buffer[i].b = 0.0; }

    if (buffer[i].r > 1.0) { buffer[i].r = 1.0; }
    if (buffer[i].g > 1.0) { buffer[i].g = 1.0; }
    if (buffer[i].b > 1.0) { buffer[i].b = 1.0; }
  }
#endif
}

inline void clip_led_values(CRGB16* buffer) {
  clip_led_values_count(buffer, NATIVE_RESOLUTION);
}

inline void reverse_leds(CRGB arr[], uint16_t size) {
  uint16_t start = 0;
  uint16_t end = size - 1;
  while (start < end) {
    CRGB temp = arr[start];
    arr[start] = arr[end];
    arr[end] = temp;
    start++;
    end--;
  }
}

static inline void write_sweet_spot_pwm(uint8_t channel, uint32_t duty) {
#if K1_HAS_SWEET_SPOT_LEDS
  ledcWrite(channel, duty);
#else
  (void)channel;
  (void)duty;
#endif
}

inline void run_sweet_spot() {
#if K1_HAS_SWEET_SPOT_LEDS
  static float sweet_spot_brightness = 0.0;  // init to zero for first fade in

  if (sweet_spot_brightness < 1.0) {
    sweet_spot_brightness += 0.05;
  }
  if (sweet_spot_brightness > 1.0) {
    sweet_spot_brightness = 1.0;
  }

  sweet_spot_state_follower = (sweet_spot_state*0.05) + (sweet_spot_state_follower*0.95);

  uint16_t led_power[3] = { 0, 0, 0 };
  for (float i = -1; i <= 1; i++) {
    float position_delta = fabs(i - sweet_spot_state_follower);
    if (position_delta > 1.0) {
      position_delta = 1.0;
    }

    float led_level = 1.0 - position_delta;
    led_level *= led_level;
    //                                                Never fully dim
    led_power[uint8_t(i + 1)] = 256 * led_level * (0.1 + silent_scale * 0.9) * sweet_spot_brightness * (CONFIG.PHOTONS * CONFIG.PHOTONS);
  }

  write_sweet_spot_pwm(SWEET_SPOT_LEFT_CHANNEL, led_power[0]);
  write_sweet_spot_pwm(SWEET_SPOT_CENTER_CHANNEL, led_power[1]);
  write_sweet_spot_pwm(SWEET_SPOT_RIGHT_CHANNEL, led_power[2]);
#endif
}


// Returns the linear interpolation of a floating point index in a CRGB array
// index is in the range of 0.0-1.0
inline CRGB lerp_led_NEW(float index, CRGB* led_array) {
  const uint16_t NUM_LEDS_NATIVE = NATIVE_RESOLUTION - 1;  // count from zero
  uint32_t index_fp = (uint32_t)(index * (float)NUM_LEDS_NATIVE * 256.0f);

  if (index_fp > (NUM_LEDS_NATIVE << 8)) {
    return CRGB::Black;
  }

  uint16_t index_i = index_fp >> 8;
  uint8_t index_f_frac = index_fp & 0xFF;

  // Use FastLED built-in lerp8by8 function for interpolation
  CRGB out_col;
  out_col.r = lerp8by8(led_array[index_i].r, led_array[index_i + 1].r, index_f_frac);
  out_col.g = lerp8by8(led_array[index_i].g, led_array[index_i + 1].g, index_f_frac);
  out_col.b = lerp8by8(led_array[index_i].b, led_array[index_i + 1].b, index_f_frac);

  return out_col;
}

// Returns the linear interpolation of a floating point index in a CRGB16 array
// index is in the range of 0.0 - float(NATIVE_RESOLUTION)
inline CRGB16 lerp_led_16(SQ15x16 index, CRGB16* led_array) {
  int32_t index_whole = index.getInteger();
  SQ15x16 index_fract = index - (SQ15x16)index_whole;

  int32_t index_left = index_whole + 0;
  int32_t index_right = index_whole + 1;

  // Bounds guard (audit M1.3): every CRGB16 buffer is NATIVE_RESOLUTION-sized, so
  // an out-of-range index must not read one past the buffer. LATENT in ALL current
  // configs — SECONDARY_LED_COUNT is hardcoded == NATIVE_RESOLUTION (globals.h) so
  // the only caller's lerp else-branch is dead, and the custom-224 build drops the
  // secondary channel. This is defensive hardening that becomes LIVE only if a
  // secondary strip with SECONDARY_LED_COUNT > NATIVE_RESOLUTION, or a new
  // out-of-range caller, is ever added. No-op for valid in-range indices
  // (byte-identical for the shipping 160 config); at the top edge it clamps to the
  // edge pixel, matching scale_to_strip's existing index_right guard.
  if (index_left  < 0) index_left  = 0;
  if (index_right < 0) index_right = 0;
  if (index_left  > NATIVE_RESOLUTION - 1) index_left  = NATIVE_RESOLUTION - 1;
  if (index_right > NATIVE_RESOLUTION - 1) index_right = NATIVE_RESOLUTION - 1;

  SQ15x16 mix_left = SQ15x16(1.0) - index_fract;
  SQ15x16 mix_right = SQ15x16(1.0) - mix_left;

  CRGB16 out_col;
  out_col.r = led_array[index_left].r * mix_left + led_array[index_right].r * mix_right;
  out_col.g = led_array[index_left].g * mix_left + led_array[index_right].g * mix_right;
  out_col.b = led_array[index_left].b * mix_left + led_array[index_right].b * mix_right;

  return out_col;
}

#ifdef K1_DROP_CUT_V1
// ── DROP-CUT (2026-06-11, Captain-directed) ──────────────────────────────────
// When a song deliberately cuts to silence (pre-drop gap, breakdown stop), the
// plate must ACTUALLY go dark — trails included — and relight instantly when
// the music returns. The legacy silence path needs 10 s; this works in ~120 ms.
// STROBE-SAFE BY DESIGN (sidechain pumping must never trigger it):
//   - engage only after energy stays below ENTER for 120 ms straight,
//   - AND only when the music was recently loud (decaying ~2 s peak-hold),
//   - exit INSTANTLY on any energy above EXIT (hysteresis),
//   - after exit, re-cut locked out for 1000 ms.
// Failure stance: fail OPEN (scale = 1.0) — a missed cut is a lost flourish;
// a false cut is a broken product. Core-1 only (called from apply_brightness,
// once per frame, before the secondary channel reads the value).
// REVERT = delete the -D flag; off-flag is byte-identical.
inline float drop_cut_scale = 1.0f;

inline void drop_cut_update() {
  static float recent_peak = 0.0f;
  static uint32_t below_since_ms = 0;
  static uint32_t rearm_until_ms = 0;
  static uint32_t last_ms = 0;
  static bool cutting = false;

  const K1AudioSnapshot snap = k1_audio_snapshot_read();
  const uint32_t now = millis();
  float dt = (last_ms != 0) ? float(now - last_ms) * 0.001f : 0.01f;
  if (dt < 0.001f) dt = 0.001f;
  if (dt > 0.05f) dt = 0.05f;
  last_ms = now;

  float e = snap.spectral_energy;
  if (!isfinite(e) || e < 0.0f) e = 0.0f;

  // Decaying peak-hold (~2 s): "was the music recently loud?"
  recent_peak -= recent_peak * 0.5f * dt;
  if (e > recent_peak) recent_peak = e;

  static const float DC_ENTER = 0.025f;   // true-cut energy ceiling
  static const float DC_EXIT  = 0.08f;    // any signal above this relights
  static const float DC_PEAK  = 0.30f;    // required recent loudness
  static const float DC_RAMP  = 12.0f;    // /s → ~80 ms to full dark

  if (cutting) {
    if (e > DC_EXIT) {
      cutting = false;
      drop_cut_scale = 1.0f;              // relight INSTANTLY — the payoff
      rearm_until_ms = now + 1000;        // anti-strobe lockout
      below_since_ms = 0;
    } else {
      drop_cut_scale -= DC_RAMP * dt;
      if (drop_cut_scale < 0.0f) drop_cut_scale = 0.0f;
    }
    return;
  }

  if (e < DC_ENTER && recent_peak > DC_PEAK && now >= rearm_until_ms) {
    if (below_since_ms == 0) below_since_ms = now;
    if (now - below_since_ms >= 120) cutting = true;   // sustained quiet only
  } else {
    below_since_ms = 0;
  }
  if (drop_cut_scale < 1.0f) {
    drop_cut_scale += DC_RAMP * dt;       // recover from any aborted ramp
    if (drop_cut_scale > 1.0f) drop_cut_scale = 1.0f;
  }
}
#endif  // K1_DROP_CUT_V1

inline void apply_brightness() {
  // This is only used to fade in when booting!
  if (millis() >= 1000 && noise_transition_queued == false && mode_transition_queued == false) {
    if (MASTER_BRIGHTNESS < 1.0) {
      MASTER_BRIGHTNESS += 0.005;
    }
    if (MASTER_BRIGHTNESS > 1.0) {
      MASTER_BRIGHTNESS = 1.00;
    }
  }

  // Phase 1 2026-05-20: PHOTONS knob curve (Captain default Mode 2 = sqrt, perceptual).
  // Per-frame call, not per-pixel — soft-float cost on S2 (~1µs) is acceptable.
#if PHOTONS_CURVE_MODE == 0
  SQ15x16 photons_curve = CONFIG.PHOTONS * CONFIG.PHOTONS;                       // quadratic (prior)
#elif PHOTONS_CURVE_MODE == 1
  SQ15x16 photons_curve = CONFIG.PHOTONS;                                        // linear
#elif PHOTONS_CURVE_MODE == 2
  SQ15x16 photons_curve = SQ15x16(sqrtf(CONFIG.PHOTONS));                        // sqrt (perceptual; CONFIG.PHOTONS is already float)
#endif
#ifdef ENABLE_MOTION_PROBE
  // NON-SHIPPING: pin the silence-AGC fade to unity while the apparent-motion
  // probe is armed, so the stimulus luminance is never dimmed by silent_scale.
  // silent_scale is recomputed upstream every frame, so it must be pinned here
  // at its point of use. Un-pins automatically when mp_active goes false.
  if (mp_active) silent_scale = 1.0f;
#endif
#ifdef ENABLE_VP_MOTION_LAB
  // NON-SHIPPABLE: VPML built-in previews are controlled VP stimuli, so silence
  // dimming must not alter the final-byte proof while the lab owns the frame.
  if (vpml_active) silent_scale = 1.0f;
#endif
#ifdef K1_BLE_REMOTED
  // Core-0 write-site fix (i2s_audio.h) is the PRIMARY guard for K1_BLE_REMOTED:
  // silent_scale and silent_scale_last are pinned to 1.0 there unconditionally,
  // eliminating the IIR race and the link-flap hole. This belt-and-suspenders
  // write here is retained as a defense-in-depth measure only.
  silent_scale = 1.0f;
#endif
#ifdef K1_DROP_CUT_V1
  drop_cut_update();
  SQ15x16 brightness = MASTER_BRIGHTNESS * photons_curve * silent_scale * SQ15x16(drop_cut_scale);
#else
  SQ15x16 brightness = MASTER_BRIGHTNESS * photons_curve * silent_scale;
#endif
  // Effects-queue DIP transition scalar (control/k1_effect_queue.cpp): COMPOSES
  // with drop_cut_scale by multiplication at the same application point — never
  // replaces or reorders the existing brightness factors. 1.0 when idle.
  brightness *= SQ15x16(k1_queue_transition_scale_primary);

  if (debug_mode && (millis() % 5000 == 0)) {
    USBSerial.print("DEBUG: Brightness components - MASTER_BRIGHTNESS: ");
    USBSerial.print(float(MASTER_BRIGHTNESS));
    USBSerial.print(" PHOTONS²: ");
    USBSerial.print(float(CONFIG.PHOTONS * CONFIG.PHOTONS));
    USBSerial.print(" silent_scale: ");
    USBSerial.print(float(silent_scale));
    USBSerial.print(" Final brightness: ");
    USBSerial.println(float(brightness));
  }

  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r *= brightness;
    leds_16[i].g *= brightness;
    leds_16[i].b *= brightness;
  }

  clip_led_values(leds_16);
}

inline void quantize_color(bool temporal_dithering) {
  if (temporal_dithering) {
    dither_step++;
    if (dither_step >= 4) {
      dither_step = 0;
    }

    static uint8_t noise_origin_r = 0;  // 0
    static uint8_t noise_origin_g = 0;  // 2
    static uint8_t noise_origin_b = 0;  // 4

    noise_origin_r += 1;
    noise_origin_g += 1;
    noise_origin_b += 1;

    for (uint16_t i = 0; i < CONFIG.LED_COUNT; i += 1) {
      // RED #####################################################
      SQ15x16 decimal_r = leds_scaled[i].r * SQ15x16(254);
      SQ15x16 whole_r = decimal_r.getInteger();
      SQ15x16 fract_r = decimal_r - whole_r;

      if (fract_r >= dither_table[(noise_origin_r + i) % 4]) {
        whole_r += SQ15x16(1);
      }

      // Phase 1 2026-05-20: apply output gamma at the final uint8 write.
      leds_out[i].r = apply_gamma8(whole_r.getInteger());

      // GREEN ###################################################
      SQ15x16 decimal_g = leds_scaled[i].g * SQ15x16(254);
      SQ15x16 whole_g = decimal_g.getInteger();
      SQ15x16 fract_g = decimal_g - whole_g;

      if (fract_g >= dither_table[(noise_origin_g + i) % 4]) {
        whole_g += SQ15x16(1);
      }

      leds_out[i].g = apply_gamma8(whole_g.getInteger());

      // BLUE ####################################################
      SQ15x16 decimal_b = leds_scaled[i].b * SQ15x16(254);
      SQ15x16 whole_b = decimal_b.getInteger();
      SQ15x16 fract_b = decimal_b - whole_b;

      if (fract_b >= dither_table[(noise_origin_b + i) % 4]) {
        whole_b += SQ15x16(1);
      }

      leds_out[i].b = apply_gamma8(whole_b.getInteger());
    }
  } else {
    for (uint16_t i = 0; i < CONFIG.LED_COUNT; i += 1) {
      // Phase 1 2026-05-20: gamma at non-dither final write too.
      leds_out[i].r = apply_gamma8(uint8_t(leds_scaled[i].r * 255));
      leds_out[i].g = apply_gamma8(uint8_t(leds_scaled[i].g * 255));
      leds_out[i].b = apply_gamma8(uint8_t(leds_scaled[i].b * 255));
    }
  }
}

inline void apply_incandescent_filter() {
  SQ15x16 mix = CONFIG.INCANDESCENT_FILTER;
  SQ15x16 inv_mix = 1.0 - mix;

  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    SQ15x16 filtered_r = leds_16[i].r * incandescent_lookup.r;
    SQ15x16 filtered_g = leds_16[i].g * incandescent_lookup.g;
    SQ15x16 filtered_b = leds_16[i].b * incandescent_lookup.b;

    leds_16[i].r = (leds_16[i].r * inv_mix) + (filtered_r * mix);
    leds_16[i].g = (leds_16[i].g * inv_mix) + (filtered_g * mix);
    leds_16[i].b = (leds_16[i].b * inv_mix) + (filtered_b * mix);

    /*
    SQ15x16 max_val = 0;
    if (leds_16[i].r > max_val) { max_val = leds_16[i].r; }
    if (leds_16[i].g > max_val) { max_val = leds_16[i].g; }
    if (leds_16[i].b > max_val) { max_val = leds_16[i].b; }

    SQ15x16 leakage = (max_val >> 2) * mix;

    CRGB base_col = CRGB(
      (uint16_t(leds[i].r * (255 - leakage)) >> 8),
      (uint16_t(leds[i].g * (255 - leakage)) >> 8),
      (uint16_t(leds[i].b * (255 - leakage)) >> 8));

    CRGB leak_col = CRGB(
      uint16_t((uint16_t(incandescent_lookup.r * (leakage)) >> 8) * max_val) >> 8,
      uint16_t((uint16_t(incandescent_lookup.g * (leakage)) >> 8) * max_val) >> 8,
      uint16_t((uint16_t(incandescent_lookup.b * (leakage)) >> 8) * max_val) >> 8);

    leds[i].r = base_col.r + leak_col.r;
    leds[i].g = base_col.g + leak_col.g;
    leds[i].b = base_col.b + leak_col.b;
    */
  }
}

inline void force_incandescent_colour(CRGB16* layer, uint16_t count) {
  for (uint16_t i = 0; i < count; i++) {
    SQ15x16 max_val = layer[i].r;
    if (layer[i].g > max_val) max_val = layer[i].g;
    if (layer[i].b > max_val) max_val = layer[i].b;

    layer[i].r = incandescent_lookup.r * max_val;
    layer[i].g = incandescent_lookup.g * max_val;
    layer[i].b = incandescent_lookup.b * max_val;
  }
}

inline void set_dot_position(uint16_t dot_index, SQ15x16 new_pos) {
  dots[dot_index].last_position = dots[dot_index].position;
  dots[dot_index].position = new_pos;
}

inline void draw_line(CRGB16* layer, SQ15x16 x1, SQ15x16 x2, CRGB16 color, SQ15x16 alpha) {
  bool lighten = true;
  if (color.r == 0 && color.g == 0 && color.b == 0) {
    lighten = false;
  }

  x1 *= (SQ15x16)(NATIVE_RESOLUTION - 1);
  x2 *= (SQ15x16)(NATIVE_RESOLUTION - 1);

  if (x1 > x2) {  // Ensure x1 <= x2
    SQ15x16 temp = x1;
    x1 = x2;
    x2 = temp;
  }

  SQ15x16 ix1 = floorFixed(x1);
  SQ15x16 ix2 = ceilFixed(x2);

  // start pixel
  if (ix1 >= 0 && ix1 < NATIVE_RESOLUTION) {
    SQ15x16 coverage = 1.0 - (x1 - ix1);
    SQ15x16 mix = alpha * coverage;

    if (lighten == true) {
      layer[ix1.getInteger()].r += color.r * mix;
      layer[ix1.getInteger()].g += color.g * mix;
      layer[ix1.getInteger()].b += color.b * mix;
    } else {
      layer[ix1.getInteger()].r = layer[ix1.getInteger()].r * (1.0 - mix) + color.r * mix;
      layer[ix1.getInteger()].g = layer[ix1.getInteger()].g * (1.0 - mix) + color.g * mix;
      layer[ix1.getInteger()].b = layer[ix1.getInteger()].b * (1.0 - mix) + color.b * mix;
    }
  }

  // end pixel
  if (ix2 >= 0 && ix2 < NATIVE_RESOLUTION) {
    SQ15x16 coverage = x2 - floorFixed(x2);
    SQ15x16 mix = alpha * coverage;

    if (lighten == true) {
      layer[ix2.getInteger()].r += color.r * mix;
      layer[ix2.getInteger()].g += color.g * mix;
      layer[ix2.getInteger()].b += color.b * mix;
    } else {
      layer[ix2.getInteger()].r = layer[ix2.getInteger()].r * (1.0 - mix) + color.r * mix;
      layer[ix2.getInteger()].g = layer[ix2.getInteger()].g * (1.0 - mix) + color.g * mix;
      layer[ix2.getInteger()].b = layer[ix2.getInteger()].b * (1.0 - mix) + color.b * mix;
    }
  }

  // pixels in between
  for (SQ15x16 i = ix1 + 1; i < ix2; i++) {
    if (i >= 0 && i < NATIVE_RESOLUTION) {
      layer[i.getInteger()].r += color.r * alpha;
      layer[i.getInteger()].g += color.g * alpha;
      layer[i.getInteger()].b += color.b * alpha;

      if (lighten == true) {
        layer[i.getInteger()].r += color.r * alpha;
        layer[i.getInteger()].g += color.g * alpha;
        layer[i.getInteger()].b += color.b * alpha;
      } else {
        layer[i.getInteger()].r = layer[i.getInteger()].r * (1.0 - alpha) + color.r * alpha;
        layer[i.getInteger()].g = layer[i.getInteger()].g * (1.0 - alpha) + color.g * alpha;
        layer[i.getInteger()].b = layer[i.getInteger()].b * (1.0 - alpha) + color.b * alpha;
      }
    }
  }
}

inline void draw_dot(CRGB16* layer, uint16_t dot_index, CRGB16 color) {
  SQ15x16 position = dots[dot_index].position;
  SQ15x16 last_position = dots[dot_index].last_position;

  SQ15x16 positional_distance = fabs_fixed(position - last_position);
  if (positional_distance < 1.0) {
    positional_distance = 1.0;
  }

  SQ15x16 net_brightness_per_pixel = 1.0 / positional_distance;
  if (net_brightness_per_pixel > 1.0) {
    net_brightness_per_pixel = 1.0;
  }

  draw_line(
    layer,
    position,
    last_position,
    color,
    net_brightness_per_pixel);
}

inline void render_photons_graph() {
  // Draw graph ticks
  uint8_t ticks = 5;
  SQ15x16 tick_distance = (0.425 / (ticks - 1));
  SQ15x16 tick_pos = 0.025;

  CRGB16 background = { 0.0, 0.0, 0.0 };
  CRGB16 needle_color = { incandescent_lookup.r * incandescent_lookup.r * 0.9, incandescent_lookup.g * incandescent_lookup.g * 0.9, incandescent_lookup.b * incandescent_lookup.b * 0.9 };

  //draw_line(leds_16_ui, 0.0, 0.5, background, 1.0);

  memset(leds_16_ui, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

  for (uint8_t i = 0; i < ticks; i++) {
    SQ15x16 prog = i / float(ticks);
    SQ15x16 tick_brightness = 0.2 + 0.4 * prog;
    tick_brightness *= tick_brightness;
    tick_brightness *= tick_brightness;
    CRGB16 tick_color = { 1.0 * tick_brightness, 0, 0 };

    set_dot_position(GRAPH_DOT_1 + i, tick_pos);
    draw_dot(leds_16_ui, GRAPH_DOT_1 + i, tick_color);
    tick_pos += tick_distance;
  }

  SQ15x16 needle_pos = 0.025 + (0.425 * CONFIG.PHOTONS);

  // Draw needle
  set_dot_position(GRAPH_NEEDLE, needle_pos);
  draw_dot(leds_16_ui, GRAPH_NEEDLE, needle_color);
}

inline void render_chroma_graph() {
  memset(leds_16_ui, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

  SQ15x16 half_height = NATIVE_RESOLUTION >> 1;
  SQ15x16 quarter_height = NATIVE_RESOLUTION >> 2;

  if (chromatic_mode == false) {
    for (SQ15x16 i = 5; i < half_height - 5; i++) {
      SQ15x16 prog = i / half_height;

      SQ15x16 distance_to_center = fabs_fixed(i - quarter_height);
      SQ15x16 brightness;  // = SQ15x16(1.0) - distance_to_center / quarter_height;

      if (distance_to_center < 3) {
        brightness = 1.0;
      } else if (distance_to_center < 5) {
        brightness = 0.0;
      } else {
        brightness = 0.20;
      }

      leds_16_ui[i.getInteger()] = hsv((SQ15x16(chroma_val + hue_position) - 0.48) + prog, CONFIG.SATURATION, brightness * brightness);
    }
  } else {
    SQ15x16 dot_pos = 0.025;
    SQ15x16 dot_distance = (0.425 / (12 - 1));

    static float radians = 0.0;
    radians -= 0.025;

    for (uint8_t i = 0; i < 12; i++) {
      SQ15x16 wave = sin(radians + (i * 0.5)) * 0.4 + 0.6;

      CRGB16 dot_color = hsv(SQ15x16(i / 12.0), CONFIG.SATURATION, wave * wave);
      set_dot_position(MAX_DOTS - 1 - i, dot_pos);
      draw_dot(leds_16_ui, MAX_DOTS - 1 - i, dot_color);

      dot_pos += dot_distance;
    }
  }
}

inline void render_mood_graph() {
  // Draw graph ticks
  uint8_t ticks = 5;
  SQ15x16 tick_distance = (0.425 / (ticks - 1));
  SQ15x16 tick_pos = 0.025;

  CRGB16 background = { 0.0, 0.0, 0.0 };
  CRGB16 needle_color = { incandescent_lookup.r * incandescent_lookup.r * 0.9, incandescent_lookup.g * incandescent_lookup.g * 0.9, incandescent_lookup.b * incandescent_lookup.b * 0.9 };

  //draw_line(leds_16_ui, 0.0, 0.5, background, 1.0);

  memset(leds_16_ui, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);

  static float radians = 0.0;
  radians -= 0.02;

  for (uint8_t i = 0; i < ticks; i++) {
    SQ15x16 tick_brightness = 0.1;  // + (0.025 * sin(radians * (1 << i)));  // + (0.04 * sin(radians * ((i<<1)+1)));
    SQ15x16 mix = i / float(ticks - 1);

    CRGB16 tick_color = { tick_brightness * mix, 0.05 * tick_brightness, tick_brightness * (1.0 - mix) };

    set_dot_position(GRAPH_DOT_1 + i, tick_pos + (0.008 * sin(radians * (1 << i))));
    draw_dot(leds_16_ui, GRAPH_DOT_1 + i, tick_color);
    tick_pos += tick_distance;
  }

  SQ15x16 needle_pos = 0.025 + (0.425 * CONFIG.MOOD);

  // Draw needle
  set_dot_position(GRAPH_NEEDLE, needle_pos);
  draw_dot(leds_16_ui, GRAPH_NEEDLE, needle_color);
}

inline void transition_ui_mask_to_height(SQ15x16 target_height) {
  SQ15x16 distance = fabs_fixed(ui_mask_height - target_height);
  if (ui_mask_height > target_height) {
    ui_mask_height -= distance * 0.05;
  } else if (ui_mask_height < target_height) {
    ui_mask_height += distance * 0.05;
  }

  if (ui_mask_height < 0.0) {
    ui_mask_height = 0.0;
  } else if (ui_mask_height > 1.0) {
    ui_mask_height = 1.0;
  }

  memset(ui_mask, 0, sizeof(SQ15x16) * NATIVE_RESOLUTION);
  for (uint8_t i = 0; i < NATIVE_RESOLUTION * ui_mask_height; i++) {
    ui_mask[i] = SQ15x16(1.0);
  }
}

inline void render_noise_cal() {
  // Noise cal UI
  float noise_cal_progress = (float)noise_iterations / 256.0f; // Ensure float division

  uint16_t half_res = NATIVE_RESOLUTION >> 1;
  uint16_t prog_led_index = half_res * noise_cal_progress;
  float max_val = 0.0;
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    if (noise_samples[i] > max_val) {
      max_val = float(noise_samples[i]);
    }
  }
  for (uint16_t i = 0; i < half_res; i++) {
    if (i < prog_led_index) {
      float led_level = 0.1f;
      if (max_val > 0.0f) {
        led_level = (float(noise_samples[i]) / max_val) * 0.9f + 0.1f;
      }
      leds_16_ui[half_res + i] = hsv(0.859, CONFIG.SATURATION, led_level * led_level);
      leds_16_ui[half_res - 1 - i] = leds_16_ui[half_res + i]; // Corrected mirror index
    } else if (i == prog_led_index) {
      leds_16_ui[half_res + i] = hsv(0.875, 1.0, 1.0);
      leds_16_ui[half_res - 1 - i] = leds_16_ui[half_res + i]; // Corrected mirror index

      ui_mask[half_res + i] = 1.0;
      ui_mask[half_res - 1 - i] = ui_mask[half_res + i]; // Corrected mirror index
    } else {
      leds_16_ui[half_res + i] = {0,0,0}; // Use CRGB16 zero initializer
      leds_16_ui[half_res - 1 - i] = leds_16_ui[half_res + i]; // Corrected mirror index
    }
  }

  if (noise_iterations > 192) {  // fade out towards end of calibration
    uint16_t iters_left = 256 - noise_iterations; // Fade over last 64 iterations
    float brightness_level = (float)iters_left / 64.0f; // Ensure float division
    brightness_level *= brightness_level;
  }
}

inline void render_ui() {
  if (noise_complete == true) {
    if (current_knob == K_NONE) {
      // Close UI if open
      if (ui_mask_height > 0.005) {
        transition_ui_mask_to_height(0.0);
      }
    } else {
      if (current_knob == K_PHOTONS) {
        render_photons_graph();
      } else if (current_knob == K_CHROMA) {
        render_chroma_graph();
      } else if (current_knob == K_MOOD) {
        render_mood_graph();
      }

      // Open UI if closed
      transition_ui_mask_to_height(0.5);
    }
  } else {
    render_noise_cal();
  }

  if (ui_mask_height > 0.005 || noise_complete == false) {
    for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
      SQ15x16 mix = ui_mask[i];
      SQ15x16 mix_inv = SQ15x16(1.0) - mix;

      if (mix > 0.0) {
        leds_16[i].r = leds_16[i].r * mix_inv + leds_16_ui[i].r * mix;
        leds_16[i].g = leds_16[i].g * mix_inv + leds_16_ui[i].g * mix;
        leds_16[i].b = leds_16[i].b * mix_inv + leds_16_ui[i].b * mix;
      }
    }
  }
}

struct LerpParams {
    int32_t index_left;
    int32_t index_right;
    SQ15x16 mix_left;
    SQ15x16 mix_right;
};
inline LerpParams* led_lerp_params = NULL;       // Row 2: multi-TU-safe (C++17 inline var)
inline bool lerp_params_initialized = false;     // Row 2: multi-TU-safe (C++17 inline var)

inline void init_lerp_params() {
    if (CONFIG.LED_COUNT != NATIVE_RESOLUTION && !lerp_params_initialized) {
        if (led_lerp_params) delete[] led_lerp_params;
        led_lerp_params = new LerpParams[CONFIG.LED_COUNT];
        
        for (uint16_t i = 0; i < CONFIG.LED_COUNT; i++) {
            SQ15x16 prog = SQ15x16(i) / SQ15x16(CONFIG.LED_COUNT);
            SQ15x16 index = prog * SQ15x16(NATIVE_RESOLUTION);
            
            led_lerp_params[i].index_left = index.getInteger();
            led_lerp_params[i].index_right = led_lerp_params[i].index_left + 1;
#ifdef K1_CUSTOM_LED_V1
            // UPSAMPLING guard (CONFIG.LED_COUNT > NATIVE_RESOLUTION, i.e. the 224 custom
            // build): the top output pixel resolves index_right == NATIVE_RESOLUTION, a
            // 1-element OOB read of leds_16[NATIVE_RESOLUTION]. Clamp it. The shipping
            // 61/91/160 (down/equal) modes never reach index_left == NR-1, so this is
            // flag-gated to keep those builds byte-identical.
            if (led_lerp_params[i].index_right >= NATIVE_RESOLUTION) {
                led_lerp_params[i].index_right = NATIVE_RESOLUTION - 1;
            }
#endif
            SQ15x16 index_fract = index - SQ15x16(led_lerp_params[i].index_left);
            led_lerp_params[i].mix_left = SQ15x16(1.0) - index_fract;
            led_lerp_params[i].mix_right = index_fract;
        }
        lerp_params_initialized = true;
    }
}


inline void scale_to_strip() {
    if (CONFIG.LED_COUNT == NATIVE_RESOLUTION) {
        memcpy(leds_scaled, leds_16, sizeof(CRGB16)*NATIVE_RESOLUTION);
    } else {
        if (!lerp_params_initialized) {
            init_lerp_params();
        }
        
        for (uint16_t i = 0; i < CONFIG.LED_COUNT; i++) {
            int32_t index_left = led_lerp_params[i].index_left;
            int32_t index_right = led_lerp_params[i].index_right;
            SQ15x16 mix_left = led_lerp_params[i].mix_left;
            SQ15x16 mix_right = led_lerp_params[i].mix_right;
            
            leds_scaled[i].r = leds_16[index_left].r * mix_left + leds_16[index_right].r * mix_right;
            leds_scaled[i].g = leds_16[index_left].g * mix_left + leds_16[index_right].g * mix_right;
            leds_scaled[i].b = leds_16[index_left].b * mix_left + leds_16[index_right].b * mix_right;
        }
    }
}

inline void show_leds() {
#if ENABLE_VP_PERF_AUDIT
  int64_t vp_perf_primary_prep_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
  apply_brightness();

  if (CONFIG.INCANDESCENT_MODE) {
    force_incandescent_colour(leds_16, NATIVE_RESOLUTION);
  } else if (CONFIG.INCANDESCENT_FILTER > 0.0) {
    apply_incandescent_filter();
  }

  if (CONFIG.BASE_COAT == true) {
    const bool base_coat_visible = CONFIG.BASE_COAT_INTENSITY > 0.0f;
    if (!base_coat_visible || CONFIG.PHOTONS <= 0.05) {
      base_coat_width_target = 0.0;
    } else {
      base_coat_width_target = 1.0;
    }

    SQ15x16 transition_speed = 0.05;
    if (base_coat_width < base_coat_width_target) {
      base_coat_width += (base_coat_width_target - base_coat_width) * transition_speed;
    } else if (base_coat_width > base_coat_width_target) {
      base_coat_width -= (base_coat_width - base_coat_width_target) * transition_speed;
    }

    SQ15x16 backdrop_divisor = 256.0;
    SQ15x16 base_intensity = SQ15x16(CONFIG.BASE_COAT_INTENSITY); // Get intensity

    // Scale color by intensity
    SQ15x16 bottom_value_r = (1 / backdrop_divisor) * base_intensity;
    SQ15x16 bottom_value_g = (1 / backdrop_divisor) * base_intensity;
    SQ15x16 bottom_value_b = (1 / backdrop_divisor) * base_intensity;

    CRGB16 backdrop_color = { bottom_value_r, bottom_value_g, bottom_value_b };

    SQ15x16 base_coat_width_scaled = base_coat_width * silent_scale;

    if (base_coat_visible && base_coat_width_scaled > 0.01) {
      draw_line(leds_16, 0.5 - (base_coat_width_scaled * 0.5), 0.5 + (base_coat_width_scaled * 0.5), backdrop_color, 1.0);
    }

    /*
    for (uint8_t i = 0; i < 128; i++) {
      if (leds_16[i].r < bottom_value_r) { leds_16[i].r = bottom_value_r; }
      if (leds_16[i].g < bottom_value_g) { leds_16[i].g = bottom_value_g; }
      if (leds_16[i].b < bottom_value_b) { leds_16[i].b = bottom_value_b; }
    }
    */
  }

  render_ui();
  apply_vivid_precomp_count(leds_16, NATIVE_RESOLUTION);
  clip_led_values(leds_16);

#if ENABLE_AMBIENT_FLOOR
  // Phase 2 Change 10 (2026-05-20): per-channel ambient floor (warm-biased).
  // Keeps lamp visibly lit during silent moments. Applied AFTER clip so the
  // floor is the final minimum before strip scaling. Disable by setting
  // ENABLE_AMBIENT_FLOOR=0 in constants.h.
  {
    static const SQ15x16 FLOOR_R = SQ15x16(AMBIENT_FLOOR_R);
    static const SQ15x16 FLOOR_G = SQ15x16(AMBIENT_FLOOR_G);
    static const SQ15x16 FLOOR_B = SQ15x16(AMBIENT_FLOOR_B);
    for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
      if (leds_16[i].r < FLOOR_R) leds_16[i].r = FLOOR_R;
      if (leds_16[i].g < FLOOR_G) leds_16[i].g = FLOOR_G;
      if (leds_16[i].b < FLOOR_B) leds_16[i].b = FLOOR_B;
    }
  }
#endif

  scale_to_strip();
#if ENABLE_VP_PERF_AUDIT
  if (vp_perf.running && vp_perf_primary_prep_start_us != 0) {
    vp_perf_record(vp_perf.primary_prep, uint32_t(esp_timer_get_time() - vp_perf_primary_prep_start_us));
  }
#endif
  
  // Only attempt to use secondary LEDs if explicitly enabled AND buffers exist.
  // k1_show_state_load() can set ENABLE_SECONDARY_LEDS=true during init_fs(),
  // before init_secondary_leds() runs (after init_system). C++ try/catch does
  // not catch null deref on ESP32 — guard the pointer explicitly.
  if (ENABLE_SECONDARY_LEDS && leds_scaled_secondary != nullptr &&
      leds_out_secondary != nullptr) {
    show_secondary_leds();
  }
  
#if ENABLE_VPAB_PROBE
  uint32_t vpab_primary_quant_us = 0;
#endif
#if ENABLE_VP_PERF_AUDIT || ENABLE_VPAB_PROBE
  int64_t vp_perf_quant_start_us = esp_timer_get_time();
#endif
  quantize_color(CONFIG.TEMPORAL_DITHERING);
#if ENABLE_VP_PERF_AUDIT || ENABLE_VPAB_PROBE
  uint32_t vp_perf_primary_quant_us = uint32_t(esp_timer_get_time() - vp_perf_quant_start_us);
#endif
#if ENABLE_VP_PERF_AUDIT
  if (vp_perf.running) {
    vp_perf_record(vp_perf.quant_primary, vp_perf_primary_quant_us);
  }
#endif
#if ENABLE_VPAB_PROBE
  vpab_primary_quant_us = vp_perf_primary_quant_us;
#endif

  if (CONFIG.REVERSE_ORDER == true) {
    reverse_leds(leds_out, CONFIG.LED_COUNT);
  }

#if ENABLE_VPAB_PROBE
  vpab_capture_tick(vpab_primary_quant_us);
#endif

  if (debug_mode && (millis() % 10000 == 0)) {
    bool has_light = false;
    uint16_t first_nonzero = NATIVE_RESOLUTION;
    uint16_t last_nonzero = 0;
    
    for (uint16_t i = 0; i < CONFIG.LED_COUNT; i++) {
      if (leds_out[i].r > 0 || leds_out[i].g > 0 || leds_out[i].b > 0) {
        has_light = true;
        if (i < first_nonzero) first_nonzero = i;
        if (i > last_nonzero) last_nonzero = i;
      }
    }
    
    USBSerial.print("DEBUG: LED Output - HasLight: ");
    USBSerial.print(has_light ? "YES" : "NO");
    if (has_light) {
      USBSerial.print(" Range: ");
      USBSerial.print(first_nonzero);
      USBSerial.print("-");
      USBSerial.print(last_nonzero);
      USBSerial.print(" (");
      USBSerial.print(last_nonzero - first_nonzero + 1);
      USBSerial.print(" LEDs)");
    }
    USBSerial.println();
  }

#if ENABLE_FASTLED_DITHER
  FastLED.setDither(BINARY_DITHER);
#else
  FastLED.setDither(DISABLE_DITHER);
#endif
#if ENABLE_VP_PERF_AUDIT
  int64_t vp_perf_show_start_us = vp_perf.running ? esp_timer_get_time() : 0;
#endif
  FastLED.show(); // This will update both LED strips
#if ENABLE_VP_PERF_AUDIT
  if (vp_perf.running && vp_perf_show_start_us != 0) {
    vp_perf_record(vp_perf.show, uint32_t(esp_timer_get_time() - vp_perf_show_start_us));
  }
#endif

  // Add inside show_leds() function, just before FastLED.show()
  if (debug_mode && (millis() % 5000 == 0)) {
    USBSerial.print("DEBUG: Using modes - Primary: ");
    USBSerial.print(CONFIG.LIGHTSHOW_MODE);
    USBSerial.print(" (");
    USBSerial.print(mode_names + (CONFIG.LIGHTSHOW_MODE * 32));
    USBSerial.print(")");
    
    if (ENABLE_SECONDARY_LEDS) {
      USBSerial.print(", Secondary: ");
      USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
      USBSerial.print(" (");
      USBSerial.print(mode_names + (SECONDARY_LIGHTSHOW_MODE * 32));
      USBSerial.print(")");
    }
    
    USBSerial.println();
  }
}

inline void init_leds() {
  bool leds_started = false;

  leds_scaled = new CRGB16[CONFIG.LED_COUNT];
  leds_out = new CRGB[CONFIG.LED_COUNT];
  
  // Initialize the lerp parameters for scale_to_strip optimization
  init_lerp_params();

  if (CONFIG.LED_TYPE == LED_NEOPIXEL) {
    if (CONFIG.LED_COLOR_ORDER == RGB) {
      FastLED.addLeds<WS2812B, LED_DATA_PIN, RGB>(leds_out, CONFIG.LED_COUNT);
    } else if (CONFIG.LED_COLOR_ORDER == GRB) {
      FastLED.addLeds<WS2812B, LED_DATA_PIN, GRB>(leds_out, CONFIG.LED_COUNT);
    } else if (CONFIG.LED_COLOR_ORDER == BGR) {
      FastLED.addLeds<WS2812B, LED_DATA_PIN, BGR>(leds_out, CONFIG.LED_COUNT);
    }
  }

  else if (CONFIG.LED_TYPE == LED_NEOPIXEL_X2) {
    if (CONFIG.LED_COLOR_ORDER == RGB) {
      FastLED.addLeds< WS2812B, LED_DATA_PIN,  RGB >(leds_out, 0, CONFIG.LED_COUNT / 2);
      FastLED.addLeds< WS2812B, LED_CLOCK_PIN, RGB >(leds_out, CONFIG.LED_COUNT / 2, CONFIG.LED_COUNT / 2);
    } else if (CONFIG.LED_COLOR_ORDER == GRB) {
      FastLED.addLeds< WS2812B, LED_DATA_PIN,  GRB >(leds_out, 0, CONFIG.LED_COUNT / 2);
      FastLED.addLeds< WS2812B, LED_CLOCK_PIN, GRB >(leds_out, CONFIG.LED_COUNT / 2, CONFIG.LED_COUNT / 2);
    } else if (CONFIG.LED_COLOR_ORDER == BGR) {
      FastLED.addLeds< WS2812B, LED_DATA_PIN,  BGR >(leds_out, 0, CONFIG.LED_COUNT / 2);
      FastLED.addLeds< WS2812B, LED_CLOCK_PIN, BGR >(leds_out, CONFIG.LED_COUNT / 2, CONFIG.LED_COUNT / 2);
    }
  }

  else if (CONFIG.LED_TYPE == LED_DOTSTAR) {
    if (CONFIG.LED_COLOR_ORDER == RGB) {
      FastLED.addLeds<DOTSTAR, LED_DATA_PIN, LED_CLOCK_PIN, RGB>(leds_out, CONFIG.LED_COUNT);
    } else if (CONFIG.LED_COLOR_ORDER == GRB) {
      FastLED.addLeds<DOTSTAR, LED_DATA_PIN, LED_CLOCK_PIN, GRB>(leds_out, CONFIG.LED_COUNT);
    } else if (CONFIG.LED_COLOR_ORDER == BGR) {
      FastLED.addLeds<DOTSTAR, LED_DATA_PIN, LED_CLOCK_PIN, BGR>(leds_out, CONFIG.LED_COUNT);
    }
  }

  FastLED.setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA);

  for (uint16_t x = 0; x < CONFIG.LED_COUNT; x++) {
    leds_out[x] = CRGB(0, 0, 0);
  }
  show_leds();

  leds_started = true;

  USBSerial.print("INIT_LEDS: ");
  USBSerial.println(leds_started == true ? K1_PASS : K1_FAIL);
}

inline void blocking_flash(CRGB16 col) {
  led_thread_halt = true;
  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i] = { 0, 0, 0 };
  }

  const uint8_t flash_times = 2;
  for (uint8_t f = 0; f < flash_times; f++) {
    for (uint8_t i = 0 + 48; i < NATIVE_RESOLUTION - 48; i++) {
      leds_16[i] = col;
    }
    show_leds();
    FastLED.delay(150);

    for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
      leds_16[i] = { 0, 0, 0 };
    }
    show_leds();
    FastLED.delay(150);
  }
  led_thread_halt = false;
}

inline void clear_all_led_buffers() {
  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i] = { 0, 0, 0 };
    leds_16_temp[i] = { 0, 0, 0 };
    leds_16_fx[i] = { 0, 0, 0 };
  }

  for (uint16_t i = 0; i < CONFIG.LED_COUNT; i++) {
    leds_scaled[i] = { 0, 0, 0 };
    leds_out[i] = CRGB(0, 0, 0);
  }
}

inline void scale_image_to_half(CRGB16* led_array) {
  for (uint16_t i = 0; i < (NATIVE_RESOLUTION >> 1); i++) {
    leds_16_temp[i].r = led_array[i << 1].r * SQ15x16(0.5) + led_array[(i << 1) + 1].r * SQ15x16(0.5);
    leds_16_temp[i].g = led_array[i << 1].g * SQ15x16(0.5) + led_array[(i << 1) + 1].g * SQ15x16(0.5);
    leds_16_temp[i].b = led_array[i << 1].b * SQ15x16(0.5) + led_array[(i << 1) + 1].b * SQ15x16(0.5);
    // Clear the second half of the temp buffer
    leds_16_temp[(NATIVE_RESOLUTION >> 1) + i] = { 0, 0, 0 };
  }

  memcpy(led_array, leds_16_temp, sizeof(CRGB16) * NATIVE_RESOLUTION);
}

inline void unmirror() {
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {  // Interpolation
    SQ15x16 index = (NATIVE_RESOLUTION >> 1) + (i / 2.0);

    int32_t index_whole = index.getInteger();
    SQ15x16 index_fract = index - (SQ15x16)index_whole;

    int32_t index_left = index_whole + 0;
    int32_t index_right = index_whole + 1;

    // Bounds guard (audit M1.3): same OOB class as lerp_led_16 (index_right could
    // reach NATIVE_RESOLUTION on a NATIVE_RESOLUTION-sized buffer). unmirror() has
    // no live callers today, so this is dead-code hardening for class completeness;
    // no-op for valid in-range indices.
    if (index_left  < 0) index_left  = 0;
    if (index_right < 0) index_right = 0;
    if (index_left  > NATIVE_RESOLUTION - 1) index_left  = NATIVE_RESOLUTION - 1;
    if (index_right > NATIVE_RESOLUTION - 1) index_right = NATIVE_RESOLUTION - 1;

    SQ15x16 mix_left = SQ15x16(1.0) - index_fract;
    SQ15x16 mix_right = SQ15x16(1.0) - mix_left;

    CRGB16 out_col;
    out_col.r = leds_16[index_left].r * mix_left + leds_16[index_right].r * mix_right;
    out_col.g = leds_16[index_left].g * mix_left + leds_16[index_right].g * mix_right;
    out_col.b = leds_16[index_left].b * mix_left + leds_16[index_right].b * mix_right;

    leds_16_temp[i] = out_col;
  }

  memcpy(leds_16, leds_16_temp, sizeof(CRGB16) * NATIVE_RESOLUTION);
}

inline void shift_leds_up(CRGB16* led_array, uint16_t offset) {
  // Underflow guard (audit M1.3): offset > NATIVE_RESOLUTION makes the unsigned
  // (NATIVE_RESOLUTION - offset) wrap to a huge size -> catastrophic OOB memcpy,
  // and led_array + offset / memset(offset) overrun the buffer. Clamp to a
  // full-buffer scroll (everything shifted off -> all black). No-op for today's
  // bounded callers (offset <= NATIVE_RESOLUTION/2).
  if (offset > NATIVE_RESOLUTION) offset = NATIVE_RESOLUTION;
  memcpy(leds_16_temp, led_array, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memcpy(led_array + offset, leds_16_temp, (NATIVE_RESOLUTION - offset) * sizeof(CRGB16));
  memset(led_array, 0, offset * sizeof(CRGB16));
}

inline void shift_leds_down(CRGB* led_array, uint16_t offset) {
  // Underflow guard (audit M1.3): mirror of shift_leds_up — an offset past the
  // buffer would wrap (NATIVE_RESOLUTION - offset) and OOB-memcpy/memset.
  if (offset > NATIVE_RESOLUTION) offset = NATIVE_RESOLUTION;
  memcpy(led_array, led_array + offset, (NATIVE_RESOLUTION - offset) * sizeof(CRGB));
  memset(led_array + (NATIVE_RESOLUTION - offset), 0, offset * sizeof(CRGB));
}

inline void mirror_image_downwards(CRGB16* led_array) {
  uint16_t half_res = NATIVE_RESOLUTION >> 1;
  for (uint16_t i = 0; i < half_res; i++) { // Loop up to half resolution
    // Copy the pixel from the second half
    leds_16_temp[half_res + i] = led_array[half_res + i];
    // Mirror it to the first half (e.g., index 159 mirrors to 0, 158 to 1, etc.)
    leds_16_temp[half_res - 1 - i] = led_array[half_res + i];
  }

  memcpy(led_array, leds_16_temp, sizeof(CRGB16) * NATIVE_RESOLUTION);
}

inline float intro_clamp01(float value) {
  if (!isfinite(value) || value < 0.0f) return 0.0f;
  if (value > 1.0f) return 1.0f;
  return value;
}

inline float intro_smooth01(float value) {
  value = intro_clamp01(value);
  return value * value * (3.0f - 2.0f * value);
}

inline float intro_bounce_radius(float t, float half_extent, float launch_end, float return_end) {
  const float launch = intro_smooth01(t / launch_end);
  const float retreat = intro_smooth01((t - launch_end) / (return_end - launch_end));
  return half_extent * intro_clamp01(launch - retreat);
}

inline float intro_triangle01(float value) {
  value -= floorf(value);
  if (value < 0.0f) value += 1.0f;
  return value < 0.5f ? value * 2.0f : (1.0f - value) * 2.0f;
}

struct VPMLRenderParams {
  uint16_t frames;
  float secondary_phase;
  float primary_width;
  float secondary_width;
  float tail_scale;
  float primary_level_base;
  float primary_level_gain;
  float secondary_level_base;
  float secondary_level_gain;
  float edge_level;
  float centre_level;
  float primary_red;
  float primary_green;
  float primary_blue;
  float secondary_red;
  float secondary_green;
  float secondary_blue;
  float impact_red;
  float impact_green;
  float impact_blue;
};

inline VPMLRenderParams vpml_default_render_params(uint16_t frames) {
  VPMLRenderParams params = {
    frames,
    0.10f,
    5.5f,
    6.8f,
    1.0f,
    0.64f,
    0.30f,
    0.58f,
    0.34f,
    0.56f,
    0.38f,
    1.00f,
    0.38f,
    0.04f,
    1.00f,
    0.76f,
    0.10f,
    1.00f,
    0.20f,
    0.02f,
  };
  return params;
}

inline VPMLRenderParams vpml_runtime_params = vpml_default_render_params(112);

inline VPMLRenderParams& vpml_mutable_params() {
  return vpml_runtime_params;
}

inline const VPMLRenderParams& vpml_current_params() {
  return vpml_runtime_params;
}

inline void vpml_reset_render_params(uint16_t frames) {
  vpml_runtime_params = vpml_default_render_params(frames);
}

inline CRGB16 intro_make_colour(float red, float green, float blue, float level) {
  const SQ15x16 gain = SQ15x16(intro_clamp01(level));
  CRGB16 colour = { SQ15x16(intro_clamp01(red)), SQ15x16(intro_clamp01(green)), SQ15x16(intro_clamp01(blue)) };
  colour.r *= gain;
  colour.g *= gain;
  colour.b *= gain;
  return colour;
}

inline CRGB16 intro_primary_colour(float level) {
  const VPMLRenderParams& params = vpml_current_params();
  return intro_make_colour(params.primary_red, params.primary_green, params.primary_blue, level);
}

inline CRGB16 intro_secondary_colour(float level) {
  const VPMLRenderParams& params = vpml_current_params();
  return intro_make_colour(params.secondary_red, params.secondary_green, params.secondary_blue, level);
}

inline CRGB16 intro_impact_colour(float level) {
  const VPMLRenderParams& params = vpml_current_params();
  return intro_make_colour(params.impact_red, params.impact_green, params.impact_blue, level);
}

inline void intro_add_weighted(CRGB16* buffer, uint16_t index, CRGB16 colour, float weight) {
  if (buffer == nullptr || index >= NATIVE_RESOLUTION) return;
  const SQ15x16 gain = SQ15x16(intro_clamp01(weight));
  buffer[index].r += colour.r * gain;
  buffer[index].g += colour.g * gain;
  buffer[index].b += colour.b * gain;
}

inline void intro_draw_centre_band(CRGB16* buffer, float radius, float width, CRGB16 colour, float gain) {
  if (buffer == nullptr || width <= 0.01f || gain <= 0.0f) return;
  const uint16_t centre_left = (NATIVE_RESOLUTION / 2) - 1;
  const uint16_t centre_right = NATIVE_RESOLUTION / 2;
  const uint16_t half = NATIVE_RESOLUTION / 2;

  for (uint16_t offset = 0; offset < half; offset++) {
    const float distance = fabsf(float(offset) - radius);
    if (distance > width) continue;
    float weight = 1.0f - (distance / width);
    weight = weight * weight * gain;
    intro_add_weighted(buffer, centre_left - offset, colour, weight);
    intro_add_weighted(buffer, centre_right + offset, colour, weight);
  }
}

inline void clear_intro_led_buffers() {
  clear_all_led_buffers();
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16_secondary[i] = { 0, 0, 0 };
  }
  if (leds_scaled_secondary != nullptr) {
    for (uint16_t i = 0; i < SECONDARY_LED_COUNT; i++) {
      leds_scaled_secondary[i] = { 0, 0, 0 };
    }
  }
  if (leds_out_secondary != nullptr) {
    for (uint16_t i = 0; i < SECONDARY_LED_COUNT; i++) {
      leds_out_secondary[i] = CRGB(0, 0, 0);
    }
  }
}

inline void clear_intro_history_buffers() {
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16_prev[i] = { 0, 0, 0 };
    leds_16_prev_secondary[i] = { 0, 0, 0 };
    leds_16_primary_snapshot[i] = { 0, 0, 0 };
  }
}

inline void vp_intro_render_frame(uint16_t frame, uint16_t frame_count) {
  if (frame_count < 2) frame_count = 2;
  if (frame >= frame_count) frame = frame_count - 1;

  const VPMLRenderParams& params = vpml_current_params();
  const float half_extent = float((NATIVE_RESOLUTION / 2) - 1);
  const float t = float(frame) / float(frame_count - 1);
  const float fade_in = intro_smooth01(t / 0.16f);
  const float fade_out = 1.0f - intro_smooth01((t - 0.90f) / 0.10f);
  const float envelope = intro_clamp01(fade_in * fade_out);
  const float return_mix = intro_smooth01((t - 0.48f) / 0.32f);
  const float primary_radius = intro_bounce_radius(t, half_extent, 0.48f, 0.90f);
  const float secondary_radius = intro_bounce_radius(t - (params.secondary_phase * 0.60f), half_extent, 0.48f, 0.92f);
  const float primary_tail = (-10.0f + (20.0f * return_mix)) * params.tail_scale;
  const float secondary_tail = (-13.0f + (24.0f * return_mix)) * params.tail_scale;
  const float edge_hit = intro_smooth01((t - 0.42f) / 0.08f) * (1.0f - intro_smooth01((t - 0.58f) / 0.16f)) * envelope * (params.edge_level / 0.56f);
  const float centre_catch = intro_smooth01((t - 0.76f) / 0.14f) * (1.0f - intro_smooth01((t - 0.96f) / 0.08f)) * envelope * (params.centre_level / 0.38f);
  const float primary_peak = params.primary_level_base + params.primary_level_gain;
  const float secondary_peak = params.secondary_level_base + params.secondary_level_gain;

  clear_intro_led_buffers();
  MASTER_BRIGHTNESS = 1.0f;

  write_sweet_spot_pwm(SWEET_SPOT_LEFT_CHANNEL, uint16_t(envelope * (1.0f - return_mix * 0.30f) * 4096.0f));
  write_sweet_spot_pwm(SWEET_SPOT_CENTER_CHANNEL, uint16_t(envelope * 4096.0f));
  write_sweet_spot_pwm(SWEET_SPOT_RIGHT_CHANNEL, uint16_t(envelope * (0.70f + return_mix * 0.30f) * 4096.0f));

  // Aurora/Bloom lineage: centre-origin bed, rendered separately per channel.
  intro_draw_centre_band(leds_16, primary_radius, params.primary_width, intro_primary_colour(primary_peak * envelope), 1.00f);
  intro_draw_centre_band(leds_16, primary_radius + primary_tail, 10.0f, intro_primary_colour(0.36f * envelope), 0.76f);
  intro_draw_centre_band(leds_16, primary_radius + (primary_tail * 1.9f), 15.0f, intro_secondary_colour(0.18f * envelope), 0.56f);
  intro_draw_centre_band(leds_16, half_extent, 3.0f, intro_impact_colour(edge_hit), 1.00f);
  intro_draw_centre_band(leds_16, 0.0f, 4.0f, intro_secondary_colour((0.18f + 0.50f * centre_catch) * envelope), 1.00f);

  // Waveform/visual-memory lineage: delayed secondary transport, not copied primary pixels.
  intro_draw_centre_band(leds_16_secondary, secondary_radius, params.secondary_width, intro_secondary_colour(secondary_peak * envelope), 1.00f);
  intro_draw_centre_band(leds_16_secondary, secondary_radius + secondary_tail, 12.0f, intro_secondary_colour(0.34f * envelope), 0.76f);
  intro_draw_centre_band(leds_16_secondary, secondary_radius + (secondary_tail * 1.8f), 17.0f, intro_primary_colour(0.16f * envelope), 0.58f);
  intro_draw_centre_band(leds_16_secondary, half_extent, 4.0f, intro_impact_colour(edge_hit * 0.72f), 0.86f);
  intro_draw_centre_band(leds_16_secondary, 0.0f, 5.5f, intro_primary_colour((0.16f + 0.42f * centre_catch) * envelope), 1.00f);

  // Pulse Prism lineage: a short centre shockwave to mark handoff into live render.
  const float impact_a = intro_smooth01((t - 0.72f) / 0.18f);
  const float impact_b = 1.0f - intro_smooth01((t - 0.90f) / 0.10f);
  const float impact = intro_clamp01(impact_a * impact_b * envelope);
  if (impact > 0.01f) {
    const float impact_radius = half_extent * (1.0f - impact_a);
    intro_draw_centre_band(leds_16, impact_radius, 3.8f, intro_impact_colour(impact), 0.88f);
    intro_draw_centre_band(leds_16_secondary, impact_radius + 3.0f, 4.8f, intro_secondary_colour(impact * 0.72f), 0.72f);
  }

  clip_led_values(leds_16);
  clip_led_values(leds_16_secondary);
}

inline void vp_intro_render_loop_frame(uint16_t frame, uint16_t frame_count) {
  if (frame_count < 2) frame_count = 2;

  const VPMLRenderParams& params = vpml_current_params();
  const float half_extent = float((NATIVE_RESOLUTION / 2) - 1);
  const float phase = float(frame % frame_count) / float(frame_count);
  const float primary_travel = intro_smooth01(intro_triangle01(phase));
  const float secondary_travel = intro_smooth01(intro_triangle01(phase + params.secondary_phase));
  const float return_mix = intro_smooth01(intro_clamp01((phase - 0.50f) * 2.0f));
  const float primary_radius = half_extent * primary_travel;
  const float secondary_radius = half_extent * secondary_travel;
  const float primary_level = params.primary_level_base + (params.primary_level_gain * primary_travel);
  const float secondary_level = params.secondary_level_base + (params.secondary_level_gain * secondary_travel);
  const float edge_hit = intro_smooth01((primary_travel - 0.78f) / 0.18f) * (1.0f - intro_smooth01((primary_travel - 0.98f) / 0.04f));
  const float centre_catch = 1.0f - intro_smooth01(primary_travel / 0.28f);

  clear_intro_led_buffers();
  MASTER_BRIGHTNESS = 1.0f;

  write_sweet_spot_pwm(SWEET_SPOT_LEFT_CHANNEL, uint16_t((0.42f + (0.36f * primary_travel)) * 4096.0f));
  write_sweet_spot_pwm(SWEET_SPOT_CENTER_CHANNEL, uint16_t((0.48f + (0.34f * centre_catch)) * 4096.0f));
  write_sweet_spot_pwm(SWEET_SPOT_RIGHT_CHANNEL, uint16_t((0.42f + (0.36f * secondary_travel)) * 4096.0f));

  intro_draw_centre_band(leds_16, primary_radius, params.primary_width, intro_primary_colour(primary_level), 1.00f);
  intro_draw_centre_band(leds_16, primary_radius - ((8.0f + 7.0f * return_mix) * params.tail_scale), 10.0f, intro_secondary_colour(0.30f + 0.22f * primary_travel), 0.72f);
  intro_draw_centre_band(leds_16, primary_radius - ((18.0f - 6.0f * return_mix) * params.tail_scale), 15.0f, intro_primary_colour(0.16f + 0.12f * centre_catch), 0.50f);
  intro_draw_centre_band(leds_16, half_extent, 3.0f, intro_impact_colour(0.14f + params.edge_level * edge_hit), 0.88f);
  intro_draw_centre_band(leds_16, 0.0f, 4.0f, intro_secondary_colour(0.18f + params.centre_level * centre_catch), 0.90f);

  intro_draw_centre_band(leds_16_secondary, secondary_radius, params.secondary_width, intro_secondary_colour(secondary_level), 1.00f);
  intro_draw_centre_band(leds_16_secondary, secondary_radius - ((10.0f - 4.0f * return_mix) * params.tail_scale), 12.0f, intro_secondary_colour(0.26f + 0.24f * secondary_travel), 0.74f);
  intro_draw_centre_band(leds_16_secondary, secondary_radius - ((20.0f - 8.0f * return_mix) * params.tail_scale), 17.0f, intro_primary_colour(0.14f + 0.14f * centre_catch), 0.54f);
  intro_draw_centre_band(leds_16_secondary, half_extent, 4.2f, intro_impact_colour(0.10f + (params.edge_level * 0.75f) * edge_hit), 0.78f);
  intro_draw_centre_band(leds_16_secondary, 0.0f, 5.2f, intro_primary_colour(0.16f + (params.centre_level * 0.84f) * centre_catch), 0.88f);

  clip_led_values(leds_16);
  clip_led_values(leds_16_secondary);
}

inline void intro_animation() {
  MASTER_BRIGHTNESS = 1.0f;
  write_sweet_spot_pwm(SWEET_SPOT_LEFT_CHANNEL, 0);
  write_sweet_spot_pwm(SWEET_SPOT_CENTER_CHANNEL, 0);
  write_sweet_spot_pwm(SWEET_SPOT_RIGHT_CHANNEL, 0);

  const uint16_t frame_count = 112;

  for (uint16_t frame = 0; frame < frame_count; frame++) {
    vp_intro_render_frame(frame, frame_count);
    show_leds();
    FastLED.delay(2);
  }

  clear_intro_led_buffers();
  clear_intro_history_buffers();
  MASTER_BRIGHTNESS = 1.0f;
  show_leds();
  MASTER_BRIGHTNESS = 0.0f;
  write_sweet_spot_pwm(SWEET_SPOT_LEFT_CHANNEL, 0);
  write_sweet_spot_pwm(SWEET_SPOT_CENTER_CHANNEL, 0);
  write_sweet_spot_pwm(SWEET_SPOT_RIGHT_CHANNEL, 0);
}

inline void run_transition_fade() {
  if (MASTER_BRIGHTNESS > 0.0) {
    MASTER_BRIGHTNESS -= 0.02;

    if (MASTER_BRIGHTNESS < 0.0) {
      MASTER_BRIGHTNESS = 0.0;
    }
  } else {
    if (mode_transition_queued == true) {  // If transition for MODE button press
      mode_transition_queued = false;
      if (mode_destination == -1) {  // Triggered via button
        CONFIG.LIGHTSHOW_MODE++;
        if (CONFIG.LIGHTSHOW_MODE >= NUM_MODES) {
          CONFIG.LIGHTSHOW_MODE = 0;
        }
      } else {  // Triggered via Serial
        CONFIG.LIGHTSHOW_MODE = mode_destination;
        mode_destination = -1;
      }
    }

    if (noise_transition_queued == true) {  // If transition for NOISE button press
      noise_transition_queued = false;
      // start noise cal
      if (debug_mode) {
        USBSerial.println("COLLECTING AMBIENT NOISE SAMPLES...");
      }
      start_noise_cal();
    }
  }
}

/*
void distort_exponential() {
  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    float prog = i / float(NATIVE_RESOLUTION - 1);
    float prog_distorted = prog * prog;
    leds_fx[i] = lerp_led_NEW(prog_distorted, leds);
  }
  load_leds_from_fx();
}

void distort_logarithmic() {
  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    float prog = i / float(NATIVE_RESOLUTION - 1);
    float prog_distorted = sqrt(prog);
    leds_fx[i] = lerp_led_NEW(prog_distorted, leds);
  }
  load_leds_from_fx();
}

void increase_saturation(uint8_t amount) {
  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    CHSV hsv = rgb2hsv_approximate(leds[i]);
    hsv.s = qadd8(hsv.s, amount);
    leds[i] = hsv;
  }
}

void fade_top_half(bool shifted = false) {
  int16_t shift = 0;
  if (shifted == true) {
    shift -= (NATIVE_RESOLUTION >> 1); // Use half resolution
  }
  for (uint8_t i = 0; i < (NATIVE_RESOLUTION >> 1); i++) {
    float fade = i / float(NATIVE_RESOLUTION >> 1);

    leds[(NATIVE_RESOLUTION - 1 - i) + shift].r *= fade;
    leds[(NATIVE_RESOLUTION - 1 - i) + shift].g *= fade;
    leds[(NATIVE_RESOLUTION - 1 - i) + shift].b *= fade;
  }
}
*/

inline float apply_contrast_float(float value, float intensity) {
  float mid_point = 0.5;
  float factor = (intensity * 2.0) + 1.0;

  float contrasted_value = (value - mid_point) * factor + mid_point;
  contrasted_value = constrain(contrasted_value, 0.0, 1.0);

  return contrasted_value;
}

inline SQ15x16 apply_contrast_fixed(SQ15x16 value, SQ15x16 intensity) {
  SQ15x16 mid_point = 0.5;
  SQ15x16 factor = (intensity * 2.0) + 1.0;

  SQ15x16 contrasted_value = (value - mid_point) * factor + mid_point;
  if (contrasted_value > SQ15x16(1.0)) {
    contrasted_value = 1.0;
  } else if (contrasted_value < SQ15x16(0.0)) {
    contrasted_value = 0.0;
  }

  return contrasted_value;
}

#include <stdint.h>

inline uint8_t apply_contrast(uint8_t value, uint8_t intensity) {
  uint16_t mid_point = NATIVE_RESOLUTION;
  uint16_t factor = (uint16_t)intensity + 1;

  int16_t contrasted_value = (int16_t)value - mid_point;
  contrasted_value = (contrasted_value * factor) + (mid_point << 8);
  contrasted_value >>= 8;

  if (contrasted_value < 0) {
    contrasted_value = 0;
  } else if (contrasted_value > 255) {
    contrasted_value = 255;
  }

  return (uint8_t)contrasted_value;
}

/*
void force_incandescent_output() {
  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    uint8_t max_val = 0;
    if (leds[i].r > max_val) { max_val = leds[i].r; }
    if (leds[i].g > max_val) { max_val = leds[i].g; }
    if (leds[i].b > max_val) { max_val = leds[i].b; }

    leds[i] = CRGB(
      uint16_t(incandescent_lookup.r * max_val) >> 8,
      uint16_t(incandescent_lookup.g * max_val) >> 8,
      uint16_t(incandescent_lookup.b * max_val) >> 8);
  }
}
*/

inline void render_bulb_cover() {
  SQ15x16 cover[4] = { 0.25, 1.00, 0.25, 0.00 };

  for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
    CRGB16 covered_color = {
      leds_16[i].r * cover[i % 4],
      leds_16[i].g * cover[i % 4],
      leds_16[i].b * cover[i % 4],
    };

    SQ15x16 bulb_opacity = CONFIG.BULB_OPACITY;
    SQ15x16 bulb_opacity_inv = 1.0 - bulb_opacity;

    leds_16[i].r = leds_16[i].r * bulb_opacity_inv + covered_color.r * bulb_opacity;
    leds_16[i].g = leds_16[i].g * bulb_opacity_inv + covered_color.g * bulb_opacity;
    leds_16[i].b = leds_16[i].b * bulb_opacity_inv + covered_color.b * bulb_opacity;
  }
}

inline CRGB force_saturation(CRGB input, uint8_t saturation) {
  CHSV out_col_hsv = rgb2hsv_approximate(input);
  CHSV out_col_hsv_sat = out_col_hsv;
  out_col_hsv_sat.setHSV(out_col_hsv.h, saturation, out_col_hsv.v);

  return CRGB(out_col_hsv_sat);
}

inline CRGB force_hue(CRGB input, uint8_t hue) {
  CHSV out_col_hsv = rgb2hsv_approximate(input);
  CHSV out_col_hsv_hue = out_col_hsv;
  out_col_hsv_hue.setHSV(hue, out_col_hsv.s, out_col_hsv.v);

  return CRGB(out_col_hsv_hue);
}

inline void blend_buffers(CRGB16* output_array, CRGB16* input_a, CRGB16* input_b, uint8_t blend_mode, SQ15x16 mix) {
  if (blend_mode == BLEND_MIX) {
    for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
      output_array[i].r = input_a[i].r * (1.0 - mix) + input_b[i].r * (mix);
      output_array[i].g = input_a[i].g * (1.0 - mix) + input_b[i].g * (mix);
      output_array[i].b = input_a[i].b * (1.0 - mix) + input_b[i].b * (mix);
    }
  } else if (blend_mode == BLEND_ADD) {
    for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
      output_array[i].r = input_a[i].r + (input_b[i].r * mix);
      output_array[i].g = input_a[i].g + (input_b[i].g * mix);
      output_array[i].b = input_a[i].b + (input_b[i].b * mix);
    }
  } else if (blend_mode == BLEND_MULTIPLY) {
    for (uint8_t i = 0; i < NATIVE_RESOLUTION; i++) {
      output_array[i].r = input_a[i].r * input_b[i].r;
      output_array[i].g = input_a[i].g * input_b[i].g;
      output_array[i].b = input_a[i].b * input_b[i].b;
    }
  }
}

inline void apply_prism_effect(float iterations, SQ15x16 opacity) {
  // Handle the whole number part of iterations
  uint8_t whole_iterations = (uint8_t)iterations;
  
  // Store original values that we need to preserve
  SQ15x16 original_hue_position = hue_position;
  
  // Apply full iterations
  for (uint8_t i = 0; i < whole_iterations; i++) {
    memcpy(leds_16_fx, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);

    scale_image_to_half(leds_16_fx);
    shift_leds_up(leds_16_fx, (NATIVE_RESOLUTION >> 1));
    mirror_image_downwards(leds_16_fx);
    
    // Apply color shift to this prism iteration
    // Each successive prism gets a slight hue shift
    float hue_shift = (i * 0.05); // 5% hue shift per prism
    
    // Apply the hue shift to the prism
    for (uint8_t j = 0; j < NATIVE_RESOLUTION; j++) {
      // Only shift colors if there's actual color data
      if (leds_16_fx[j].r > 0 || leds_16_fx[j].g > 0 || leds_16_fx[j].b > 0) {
        leds_16_fx[j] = adjust_hue_and_saturation(
          leds_16_fx[j], 
          fmod_fixed(hue_position + hue_shift, 1.0), 
          CONFIG.SATURATION
        );
      }
    }

    // memcpy(leds_16_fx_2, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION); // No longer needed
    blend_buffers(leds_16, leds_16, leds_16_fx, BLEND_ADD, opacity); // Blend original (leds_16) with processed (leds_16_fx)
  }
  
  // Handle the fractional part if any
  float fractional_part = iterations - whole_iterations;
  if (fractional_part > 0.01) { // Only process if the fractional part is significant
    memcpy(leds_16_fx, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);

    scale_image_to_half(leds_16_fx);
    shift_leds_up(leds_16_fx, (NATIVE_RESOLUTION >> 1));
    mirror_image_downwards(leds_16_fx);
    
    // Apply color shift to the fractional prism as well
    float hue_shift = (whole_iterations * 0.05);
    
    // Apply the hue shift to the prism
    for (uint8_t j = 0; j < NATIVE_RESOLUTION; j++) {
      // Only shift colors if there's actual color data
      if (leds_16_fx[j].r > 0 || leds_16_fx[j].g > 0 || leds_16_fx[j].b > 0) {
        leds_16_fx[j] = adjust_hue_and_saturation(
          leds_16_fx[j], 
          fmod_fixed(hue_position + hue_shift, 1.0), 
          CONFIG.SATURATION
        );
      }
    }

    // memcpy(leds_16_fx_2, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION); // No longer needed
    // Apply the effect with reduced opacity based on the fractional part
    blend_buffers(leds_16, leds_16, leds_16_fx, BLEND_ADD, opacity * fractional_part); // Blend original (leds_16) with processed (leds_16_fx)
  }
  
  // Restore the original values to prevent side effects
  hue_position = original_hue_position;
}

inline void clear_leds() {
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
}

inline void process_color_shift() {
  int16_t rounded_index = spectral_history_index - 1;
  while (rounded_index < 0) {
    rounded_index += SPECTRAL_HISTORY_LENGTH;
  }

  SQ15x16 novelty_now = novelty_curve[rounded_index];

  // Remove bottom 10%, stretch values to still occupy full 0.0-1.0 range
  novelty_now -= SQ15x16(0.10);
  if (novelty_now < 0.0) {
    novelty_now = 0.0;
  }
  novelty_now *= SQ15x16(1.111111);  // ---- 1.0 / (1.0 - 0.10)

  novelty_now = novelty_now * novelty_now * novelty_now;  // Square the novelty value
  //novelty_now = (novelty_now)*0.5 + (novelty_now*novelty_now)*0.5; // "half-square" it again

  if (novelty_now > 0.05) {
    novelty_now = 0.05;
  }

  if (novelty_now > hue_shift_speed) {
    hue_shift_speed = novelty_now * SQ15x16(0.25); // Reduced factor from 0.75 to slow down shift
  } else {
    hue_shift_speed *= SQ15x16(0.99);
  }

  // Add and wrap
  hue_position += (hue_shift_speed * hue_push_direction);
  while (hue_position < 0.0) {
    hue_position += 1.0;
  }
  while (hue_position >= 1.0) {
    hue_position -= 1.0;
  }

  if (fabs_fixed(hue_position - hue_destination) <= 0.01) {
    hue_push_direction *= -1.0;
    hue_shifting_mix_target *= -1.0;
    hue_destination = random_float();
    //printf("###################################### NEW DEST: %f\n", hue_destination);
  }

  SQ15x16 hue_shifting_mix_distance = fabs_fixed(hue_shifting_mix - hue_shifting_mix_target);
  if (hue_shifting_mix < hue_shifting_mix_target) {
    hue_shifting_mix += hue_shifting_mix_distance * 0.01;
  } else if (hue_shifting_mix > hue_shifting_mix_target) {
    hue_shifting_mix -= hue_shifting_mix_distance * 0.01;
  }

  /*
    if(chance(0.2) == true){ //0.2% of loops
        hue_push_direction *= -1.0;
        printf("###################################### SWITCH DIR: %f\n", hue_push_direction);
    }
    */
}

// apply_chroma_profile() — clean front-end for the NOTE_OFFSET + CHROMAGRAM_RANGE
// pair (Stage 2 items 18-20). The chromagram is shared/global audio analysis, so
// this mutates the single global CONFIG, NOT any per-channel RenderParams.
//
//   DEFAULT → NOTE_OFFSET = CONFIG_DEFAULTS.NOTE_OFFSET (12),
//             CHROMAGRAM_RANGE = CONFIG_DEFAULTS.CHROMAGRAM_RANGE (60)  [= v40102]
//   BASS    → NOTE_OFFSET = 0,  CHROMAGRAM_RANGE = 24                   [bass-mode alias]
//   FULL    → NOTE_OFFSET = 0,  CHROMAGRAM_RANGE = NUM_FREQS
//
// Returns true if NOTE_OFFSET changed. NOTE_OFFSET re-seeds the GDFT frequency
// table at init (system.h), so a true return means the caller must reboot (or, in
// a future Stage 3, live-recompute the GDFT table). A pure CHROMAGRAM_RANGE change
// is read fresh by make_smooth_chromagram() every frame and needs no reboot.
inline bool apply_chroma_profile(uint8_t profile) {
  uint8_t prev_note_offset = CONFIG.NOTE_OFFSET;

  uint8_t new_note_offset;
  uint8_t new_chroma_range;

  switch (profile) {
    case CHROMA_PROFILE_BASS:
      new_note_offset  = 0;
      new_chroma_range = 24;
      break;
    case CHROMA_PROFILE_FULL:
      new_note_offset  = 0;
      new_chroma_range = NUM_FREQS;
      break;
    case CHROMA_PROFILE_DEFAULT:
    default:
      profile          = CHROMA_PROFILE_DEFAULT;  // normalise any unknown value to DEFAULT
      new_note_offset  = CONFIG_DEFAULTS.NOTE_OFFSET;     // 12 (= v40102)
      new_chroma_range = CONFIG_DEFAULTS.CHROMAGRAM_RANGE; // 60 (= v40102)
      break;
  }

  CONFIG.CHROMA_PROFILE   = profile;
  CONFIG.NOTE_OFFSET      = new_note_offset;
  CONFIG.CHROMAGRAM_RANGE = new_chroma_range;

  return (new_note_offset != prev_note_offset);
}

inline void make_smooth_chromagram() {
  memset(chromagram_smooth, 0, sizeof(SQ15x16) * 12);

  uint8_t chroma_range = CONFIG.CHROMAGRAM_RANGE;
  if (chroma_range < 1) chroma_range = 1;
  if (chroma_range > NUM_FREQS) chroma_range = NUM_FREQS;
  SQ15x16 chroma_bin_divisor = SQ15x16(float(chroma_range) / 12.0f);

  for (uint8_t i = 0; i < chroma_range; i++) {
    SQ15x16 note_magnitude = spectrogram_smooth[i];

    if (note_magnitude > 1.0) {
      note_magnitude = 1.0;
    } else if (note_magnitude < 0.0) {
      note_magnitude = 0.0;
    }

    uint8_t chroma_bin = i % 12;
    chromagram_smooth[chroma_bin] += note_magnitude / chroma_bin_divisor;
  }

  SQ15x16 pre_max = SQ15x16(0.0);
  SQ15x16 pre_mean = SQ15x16(0.0);
  for (uint8_t i = 0; i < 12; i++) {
    pre_mean += chromagram_smooth[i];
    if (chromagram_smooth[i] > pre_max) pre_max = chromagram_smooth[i];
  }
  pre_mean /= SQ15x16(12.0);

  static SQ15x16 max_peak = 0.001;

  max_peak *= 0.999;
  if (max_peak < 0.01) {
    max_peak = 0.01;
  }

  for (uint16_t i = 0; i < 12; i++) {
    if (chromagram_smooth[i] > max_peak) {
      SQ15x16 distance = chromagram_smooth[i] - max_peak;
      max_peak += distance *= SQ15x16(0.05);
    }
  }

  SQ15x16 multiplier = 1.0 / max_peak;

  for (uint8_t i = 0; i < 12; i++) {
    chromagram_smooth[i] *= multiplier;
  }

  SQ15x16 norm_max = SQ15x16(0.0);
  SQ15x16 norm_mean = SQ15x16(0.0);
  for (uint8_t i = 0; i < 12; i++) {
    norm_mean += chromagram_smooth[i];
    if (chromagram_smooth[i] > norm_max) norm_max = chromagram_smooth[i];
  }
  norm_mean /= SQ15x16(12.0);
  SQ15x16 flatness = norm_max - norm_mean;

#ifdef K1_PALETTE_VIBRANCY_V1
  // K1 PALETTE VIBRANCY (2026-07-02): export the POST-normalize, PRE-gate
  // chromagram for the palette-coordinate engine. The sparseness gate below
  // exists to stop grey-summing in CHROMATIC modes (summed hsv()); the PALETTE
  // path only uses chroma as a coordinate selector, where the gate's zeroing
  // (flatness<=0.08 fires on live dense music — device-proven 2026-07-02) and
  // the -0.1 floor destroy the relative shape and freeze the palette
  // coordinate ("every palette renders a handful of colours"). Quiet guard:
  // below quiet_max the export zeroes so true silence still engages the
  // held-hue hold (the 2026-06-11 palette-crush protection is preserved).
  {
    const SQ15x16 vib_quiet_max = SQ15x16(0.08);
    for (uint8_t i = 0; i < 12; i++) {
      chromagram_pregate[i] = (norm_max > vib_quiet_max) ? chromagram_smooth[i] : SQ15x16(0.0);
    }
  }
#endif

  if (VP_FIX_CHROMAGRAM_SPARSENESS) {
    SQ15x16 gate_gain = SQ15x16(0.0);
    const SQ15x16 gate_floor = SQ15x16(0.08);
    const SQ15x16 gate_full = SQ15x16(0.28);
    const SQ15x16 quiet_max = SQ15x16(0.08);

    if (norm_max <= quiet_max || flatness <= gate_floor) {
      gate_gain = SQ15x16(0.0);
    } else if (flatness >= gate_full) {
      gate_gain = SQ15x16(1.0);
    } else {
      gate_gain = (flatness - gate_floor) / (gate_full - gate_floor);
    }

    vp_dbg_chroma_gate_gain = gate_gain;  // item 21 telemetry: capture finalised gate gain

    for (uint8_t i = 0; i < 12; i++) {
      chromagram_smooth[i] -= SQ15x16(0.1);
      if (chromagram_smooth[i] < SQ15x16(0.0)) chromagram_smooth[i] = SQ15x16(0.0);
      chromagram_smooth[i] *= gate_gain;
      if (chromagram_smooth[i] > SQ15x16(1.0)) chromagram_smooth[i] = SQ15x16(1.0);
    }
  }

  SQ15x16 final_max = SQ15x16(0.0);
  SQ15x16 final_mean = SQ15x16(0.0);
  for (uint8_t i = 0; i < 12; i++) {
    final_mean += chromagram_smooth[i];
    if (chromagram_smooth[i] > final_max) final_max = chromagram_smooth[i];
  }
  final_mean /= SQ15x16(12.0);

  vp_dbg_chroma_range = chroma_range;
  vp_dbg_chroma_pre_max = pre_max;
  vp_dbg_chroma_pre_mean = pre_mean;
  vp_dbg_chroma_norm_max = norm_max;
  vp_dbg_chroma_norm_mean = norm_mean;
  vp_dbg_chroma_final_max = final_max;
  vp_dbg_chroma_final_mean = final_mean;
  vp_dbg_chroma_flatness = flatness;
  vp_dbg_chroma_profile = CONFIG.CHROMA_PROFILE;  // item 21 telemetry: active preset
  vp_dbg_chroma_seq++;
}


inline void draw_sprite(CRGB16 dest[], CRGB16 sprite[], uint32_t dest_length, uint32_t sprite_length, float position, SQ15x16 alpha) {
  int32_t position_whole = position;  // Downcast to integer accuracy
  float position_fract = position - position_whole;
  SQ15x16 mix_right = position_fract;
  SQ15x16 mix_left = 1.0 - mix_right;

  for (uint16_t i = 0; i < sprite_length; i++) {
    int32_t pos_left = i + position_whole;
    int32_t pos_right = i + position_whole + 1;

    bool skip_left = false;
    bool skip_right = false;

    if (pos_left < 0) {
      pos_left = 0;
      skip_left = true;
    }
    if (pos_left > dest_length - 1) {
      pos_left = dest_length - 1;
      skip_left = true;
    }

    if (pos_right < 0) {
      pos_right = 0;
      skip_right = true;
    }
    if (pos_right > dest_length - 1) {
      pos_right = dest_length - 1;
      skip_right = true;
    }

    if (skip_left == false) {
      dest[pos_left].r += sprite[i].r * mix_left * alpha;
      dest[pos_left].g += sprite[i].g * mix_left * alpha;
      dest[pos_left].b += sprite[i].b * mix_left * alpha;
    }

    if (skip_right == false) {
      dest[pos_right].r += sprite[i].r * mix_right * alpha;
      dest[pos_right].g += sprite[i].g * mix_right * alpha;
      dest[pos_right].b += sprite[i].b * mix_right * alpha;
    }
  }
}

inline CRGB16 force_saturation_16(CRGB16 rgb, SQ15x16 saturation) {
  // Convert RGB to HSV
  SQ15x16 max_val = fmax_fixed(rgb.r, fmax_fixed(rgb.g, rgb.b));
  SQ15x16 min_val = fmax_fixed(rgb.r, fmax_fixed(rgb.g, rgb.b));
  SQ15x16 delta = max_val - min_val;

  SQ15x16 hue, saturation_value, value;
  value = max_val;

  if (delta == 0) {
    // The color is achromatic (gray)
    hue = 0;
    saturation_value = 0;
  } else {
    // Calculate hue and saturation
    if (max_val == rgb.r) {
      hue = (rgb.g - rgb.b) / delta;
    } else if (max_val == rgb.g) {
      hue = 2 + (rgb.b - rgb.r) / delta;
    } else {
      hue = 4 + (rgb.r - rgb.g) / delta;
    }

    hue *= 60;
    if (hue < 0) {
      hue += 360;
    }

    saturation_value = delta / max_val;
  }

  // Set the saturation to the input value
  saturation_value = saturation;

  // Convert back to RGB
  SQ15x16 c = saturation_value * value;
  SQ15x16 x = c * (1 - fabs_fixed(fmod_fixed(hue / 60, 2) - 1));
  SQ15x16 m = value - c;

  CRGB16 modified_rgb;
  if (hue >= 0 && hue < 60) {
    modified_rgb.r = c;
    modified_rgb.g = x;
    modified_rgb.b = 0;
  } else if (hue >= 60 && hue < 120) {
    modified_rgb.r = x;
    modified_rgb.g = c;
    modified_rgb.b = 0;
  } else if (hue >= 120 && hue < 180) {
    modified_rgb.r = 0;
    modified_rgb.g = c;
    modified_rgb.b = x;
  } else if (hue >= 180 && hue < 240) {
    modified_rgb.r = 0;
    modified_rgb.g = x;
    modified_rgb.b = c;
  } else if (hue >= 240 && hue < 300) {
    modified_rgb.r = x;
    modified_rgb.g = 0;
    modified_rgb.b = c;
  } else {
    modified_rgb.r = c;
    modified_rgb.g = 0;
    modified_rgb.b = x;
  }

  modified_rgb.r += m;
  modified_rgb.g += m;
  modified_rgb.b += m;

  return modified_rgb;
}

inline CRGB16 adjust_hue_and_saturation(CRGB16 color, SQ15x16 hue, SQ15x16 saturation) {
  // Store the RGB values
  SQ15x16 r = color.r, g = color.g, b = color.b;

  // Calculate maximum and minimum values of r, g, b
  SQ15x16 max_val = fmax_fixed(r, fmax_fixed(g, b));
  SQ15x16 min_val = fmin_fixed(r, fmin_fixed(g, b));
  SQ15x16 delta = max_val - min_val;

  // Calculate the value of the HSV color
  SQ15x16 v = max_val;

  SQ15x16 source_s = SQ15x16(0.0);
  if (max_val > SQ15x16(0.001)) {
    source_s = delta / max_val;
  }

  // Candidate path preserves existing source saturation instead of forcing grey peaks to vivid hues.
  SQ15x16 s = VP_FIX_HSV_SOURCE_SAT ? source_s * saturation : saturation;
  if (s < SQ15x16(0.0)) s = SQ15x16(0.0);
  if (s > SQ15x16(1.0)) s = SQ15x16(1.0);

  // Prepare to convert HSV back to RGB
  SQ15x16 c = v * s;  // chroma
  SQ15x16 h_prime = fmod_fixed(hue * SQ15x16(6.0), SQ15x16(6.0));
  SQ15x16 x = c * (SQ15x16(1.0) - fabs_fixed(fmod_fixed(h_prime, SQ15x16(2.0)) - SQ15x16(1.0)));

  // Recalculate r, g, b based on the new hue and saturation
  if (h_prime >= 0 && h_prime < 1) {
    r = c;
    g = x;
    b = 0;
  } else if (h_prime >= 1 && h_prime < 2) {
    r = x;
    g = c;
    b = 0;
  } else if (h_prime >= 2 && h_prime < 3) {
    r = 0;
    g = c;
    b = x;
  } else if (h_prime >= 3 && h_prime < 4) {
    r = 0;
    g = x;
    b = c;
  } else if (h_prime >= 4 && h_prime < 5) {
    r = x;
    g = 0;
    b = c;
  } else if (h_prime >= 5 && h_prime < 6) {
    r = c;
    g = 0;
    b = x;
  }

  // Add the calculated difference to get the final RGB values
  SQ15x16 m = v - c;
  r += m;
  g += m;
  b += m;

  // Clamp the values between 0.0 and 1.0 to account for rounding errors
  r = fmax_fixed(SQ15x16(0.0), fmin_fixed(SQ15x16(1.0), r));
  g = fmax_fixed(SQ15x16(0.0), fmin_fixed(SQ15x16(1.0), g));
  b = fmax_fixed(SQ15x16(0.0), fmin_fixed(SQ15x16(1.0), b));

  // Return the resulting color
  CRGB16 result = { r, g, b };
  return result;
}

inline void init_secondary_leds() {
  leds_scaled_secondary = new CRGB16[SECONDARY_LED_COUNT];
  leds_out_secondary = new CRGB[SECONDARY_LED_COUNT];

  // Use constants for FastLED template arguments
  FastLED.addLeds<WS2812B, SECONDARY_LED_DATA_PIN, GRB>(leds_out_secondary, SECONDARY_LED_COUNT);
  
  for (uint16_t x = 0; x < SECONDARY_LED_COUNT; x++) {
    leds_out_secondary[x] = CRGB(0, 0, 0);
  }
  
  USBSerial.print("INIT_SECONDARY_LEDS: ");
  USBSerial.println(K1_PASS);
}

inline void scale_to_secondary_strip() {
  if (leds_scaled_secondary == nullptr || leds_16_secondary == nullptr) {
    return;
  }
  if (SECONDARY_LED_COUNT == NATIVE_RESOLUTION) {
    memcpy(leds_scaled_secondary, leds_16_secondary, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else {
    for (SQ15x16 i = 0; i < SECONDARY_LED_COUNT; i++) {
      SQ15x16 prog = i / SQ15x16(SECONDARY_LED_COUNT);
      leds_scaled_secondary[i.getInteger()] = lerp_led_16(prog * SQ15x16(NATIVE_RESOLUTION), leds_16_secondary);
    }
  }
}

inline void apply_brightness_secondary() {
  // Apply the same silence scaling used for the primary LEDs
  // Phase 1 2026-05-20: PHOTONS curve for secondary matches primary. Float type matches existing code.
#if PHOTONS_CURVE_MODE == 0
  float photons_curve_s = SECONDARY_PHOTONS * SECONDARY_PHOTONS;   // quadratic (prior)
#elif PHOTONS_CURVE_MODE == 1
  float photons_curve_s = SECONDARY_PHOTONS;                       // linear
#elif PHOTONS_CURVE_MODE == 2
  float photons_curve_s = sqrtf(SECONDARY_PHOTONS);                // sqrt (perceptual)
#endif
  float bright_val = photons_curve_s * silent_scale;
#ifdef K1_DROP_CUT_V1
  // Same musical-cut scaler as the primary channel (updated once per frame
  // in apply_brightness; primary always renders first in show_leds()).
  bright_val *= drop_cut_scale;
#endif
  // Effects-queue DIP transition scalar (control/k1_effect_queue.cpp): the
  // SECONDARY channel's independent dip, composed by multiplication at the
  // same application point as drop_cut_scale. 1.0 when idle.
  bright_val *= k1_queue_transition_scale_secondary;

  if (debug_mode && (millis() % 5000 == 0)) {
    USBSerial.print("DEBUG: Secondary brightness curve = f(PHOTONS=");
    USBSerial.print(SECONDARY_PHOTONS);
    USBSerial.print(", mode=");
    USBSerial.print(PHOTONS_CURVE_MODE);
    USBSerial.print(") × silent_scale(");
    USBSerial.print(silent_scale);
    USBSerial.print(") = ");
    USBSerial.println(bright_val);
  }
  
  for (uint16_t i = 0; i < SECONDARY_LED_COUNT; i++) {
    leds_scaled_secondary[i].r *= bright_val;
    leds_scaled_secondary[i].g *= bright_val;
    leds_scaled_secondary[i].b *= bright_val;
  }
}

inline void show_secondary_leds() {
#if ENABLE_VP_PERF_AUDIT
  int64_t vp_perf_secondary_prep_start_us = vp_perf.running ? esp_timer_get_time() : 0;
  uint32_t vp_perf_secondary_quant_us = 0;
#endif
#if ENABLE_VPAB_PROBE
  vp_secondary_quant_us_last = 0;
#endif
  apply_vivid_precomp_count(leds_16_secondary, NATIVE_RESOLUTION);
  clip_led_values_count(leds_16_secondary, NATIVE_RESOLUTION);
  scale_to_secondary_strip();
  apply_brightness_secondary();
  if (SECONDARY_INCANDESCENT_MODE) {
    force_incandescent_colour(leds_scaled_secondary, SECONDARY_LED_COUNT);
  }
  // Quantization needs to happen *after* filtering if filter uses scaled values
  // quantize_color_secondary(CONFIG.TEMPORAL_DITHERING); // Moved down

  // Check SECONDARY specific incandescent settings
  float effective_secondary_filter = (VP_FIX_SECONDARY_CLEAN || SECONDARY_INCANDESCENT_MODE) ? 0.0f : SECONDARY_INCANDESCENT_FILTER;
  if (effective_secondary_filter > 0.0) { 
    SQ15x16 filter_strength = effective_secondary_filter; // Use fixed-point
    for (uint16_t i = 0; i < SECONDARY_LED_COUNT; i++) {
      // Direct fixed-point to uint8_t conversion (assuming 0.0-1.0 maps to 0-255)
      // Note: Clamping might be needed depending on exact fixed-point behavior
      uint8_t r_raw = (leds_scaled_secondary[i].r * 255).getInteger(); 
      uint8_t g_raw = (leds_scaled_secondary[i].g * 255).getInteger();
      uint8_t b_raw = (leds_scaled_secondary[i].b * 255).getInteger();

      // Apply incandescent color correction using integer/fixed-point math
      // Ensure filter_strength doesn't exceed 1.0 before calculations
      if (filter_strength > SQ15x16(1.0)) filter_strength = SQ15x16(1.0);
      
      uint16_t blue_reduction_fp = uint16_t(b_raw) * uint16_t((filter_strength * 255).getInteger());
      uint8_t blue_reduction = blue_reduction_fp >> 8; // Divide by 256

      // Scale green reduction based on blue reduction using integer math
      uint16_t green_reduction_fp = uint16_t(g_raw) * uint16_t(blue_reduction) * uint16_t((filter_strength * 255).getInteger());
      // Need to divide by 255*256 - approximate by dividing by 2^16 (>> 16)
      uint8_t green_reduction = (green_reduction_fp >> 16);

      leds_out_secondary[i].r = r_raw; // Red remains unchanged in this simple filter
      leds_out_secondary[i].g = (g_raw > green_reduction) ? g_raw - green_reduction : 0;
      leds_out_secondary[i].b = (b_raw > blue_reduction) ? b_raw - blue_reduction : 0;
    }
  } else {
    // If filter is off, just quantize directly
#if ENABLE_VP_PERF_AUDIT || ENABLE_VPAB_PROBE
    int64_t vp_perf_secondary_quant_start_us = esp_timer_get_time();
#endif
    quantize_color_secondary(CONFIG.TEMPORAL_DITHERING);
#if ENABLE_VP_PERF_AUDIT || ENABLE_VPAB_PROBE
    uint32_t vp_perf_secondary_quant_sample_us = uint32_t(esp_timer_get_time() - vp_perf_secondary_quant_start_us);
#endif
#if ENABLE_VP_PERF_AUDIT
    if (vp_perf.running) {
      vp_perf_secondary_quant_us = vp_perf_secondary_quant_sample_us;
      vp_perf_record(vp_perf.quant_secondary, vp_perf_secondary_quant_us);
    }
#endif
#if ENABLE_VPAB_PROBE
    vp_secondary_quant_us_last = vp_perf_secondary_quant_sample_us;
#endif
  }
  
  // If filter was applied, quantize *after* filtering (using the calculated leds_out_secondary)
  // This assumes quantize_color_secondary can work directly on leds_out_secondary if filter applied
  // OR that the filtered values should be quantized. If quantization should happen first,
  // the logic needs adjustment. Let's assume quantization happens last based on original structure.
  if (effective_secondary_filter <= 0.0) { 
      // Quantization was already called if filter is off.
  } else {
      // We need to manually copy the filtered uint8_t values from leds_out_secondary 
      // back to leds_scaled_secondary if quantize_color_secondary *requires* scaled input,
      // OR modify quantize_color_secondary to work on leds_out_secondary.
      // Simpler for now: assume filter output IS the final uint8_t value before base coat/reverse.
      // So, skip re-quantizing if filter was applied.
  }
  
  // --- Secondary Base Coat --- 
  if (SECONDARY_BASE_COAT && !VP_FIX_SECONDARY_CLEAN) {
    // Apply base coat to secondary LEDs, considering intensity
    SQ15x16 base_intensity_secondary = SQ15x16(SECONDARY_BASE_COAT_INTENSITY); // Get secondary intensity
    SQ15x16 base_value_secondary = (SQ15x16(2.0) / SQ15x16(255.0)) * base_intensity_secondary; // Calculate scaled base value (approx 2/255 * intensity)
    uint8_t base_add_secondary = uint8_t( (base_value_secondary * SQ15x16(255.0)).getInteger() ); // Convert back to uint8

    // Clamp base_add_secondary to avoid issues (e.g., if intensity is huge)
    if (base_add_secondary > 20) base_add_secondary = 20; // Max add value
    if (base_add_secondary < 0) base_add_secondary = 0; // Min add value

    for (uint16_t i = 0; i < SECONDARY_LED_COUNT; i++) {
      // Add the intensity-scaled base value, clamping at 255
      leds_out_secondary[i].r = min(255, int(leds_out_secondary[i].r) + base_add_secondary);
      leds_out_secondary[i].g = min(255, int(leds_out_secondary[i].g) + base_add_secondary);
      leds_out_secondary[i].b = min(255, int(leds_out_secondary[i].b) + base_add_secondary);
    }
  }
  
  if (SECONDARY_REVERSE_ORDER) {
    reverse_leds(leds_out_secondary, SECONDARY_LED_COUNT);
  }
#if ENABLE_VP_PERF_AUDIT
  if (vp_perf.running && vp_perf_secondary_prep_start_us != 0) {
    uint32_t total_us = uint32_t(esp_timer_get_time() - vp_perf_secondary_prep_start_us);
    uint32_t prep_us = (total_us >= vp_perf_secondary_quant_us) ? (total_us - vp_perf_secondary_quant_us) : total_us;
    vp_perf_record(vp_perf.secondary_prep, prep_us);
  }
#endif
}

// Function to apply visual enhancements that make the display "POP" more
inline void apply_enhanced_visuals() {
  // Only apply if there's actual visual data
  bool has_content = false;
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    if (leds_16[i].r > 0.01 || leds_16[i].g > 0.01 || leds_16[i].b > 0.01) {
      has_content = true;
      break;
    }
  }
  
  if (!has_content) return;
  
  // Store original content
  memcpy(leds_16_fx, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  
  // 1. Add subtle bloom/glow effect based on audio_vu_level
  float bloom_intensity = 0.15 + float(audio_vu_level) * 0.2;
  
  // Create a blurred version in leds_16_temp
  for (uint16_t i = 1; i < NATIVE_RESOLUTION-1; i++) {
    // Simple 3-pixel box blur
    leds_16_temp[i].r = (leds_16_fx[i-1].r + leds_16_fx[i].r + leds_16_fx[i+1].r) / 3.0;
    leds_16_temp[i].g = (leds_16_fx[i-1].g + leds_16_fx[i].g + leds_16_fx[i+1].g) / 3.0;
    leds_16_temp[i].b = (leds_16_fx[i-1].b + leds_16_fx[i].b + leds_16_fx[i+1].b) / 3.0;
  }
  
  // Edge pixels
  leds_16_temp[0] = leds_16_temp[1];
  leds_16_temp[NATIVE_RESOLUTION-1] = leds_16_temp[NATIVE_RESOLUTION-2];
  
  // Mix original and bloom
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r = leds_16_fx[i].r + leds_16_temp[i].r * bloom_intensity;
    leds_16[i].g = leds_16_fx[i].g + leds_16_temp[i].g * bloom_intensity;
    leds_16[i].b = leds_16_fx[i].b + leds_16_temp[i].b * bloom_intensity;
  }
  
  // 2. Add subtle wave-like modulation effect
  static float wave_position = 0.0;
  wave_position += 0.03; // Speed of wave
  
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    float position = float(i) / NATIVE_RESOLUTION;
    float wave = sin(wave_position + position * 6.28) * 0.5 + 0.5;
    
    // Apply subtle wave effect only where there's actual color
    if (leds_16[i].r > 0.05 || leds_16[i].g > 0.05 || leds_16[i].b > 0.05) {
      // Increase brightness slightly with wave
      float boost = 1.0 + (wave * 0.15); 
      leds_16[i].r *= boost;
      leds_16[i].g *= boost;
      leds_16[i].b *= boost;
    }
  }
  
  // 3. Dynamic color enhancement - make colors more vibrant during beats
  if (audio_vu_level > audio_vu_level_average * 1.2) {
    float enhancement = (float(audio_vu_level) / float(audio_vu_level_average) - 1.0) * 0.4;
    if (enhancement > 0.25) enhancement = 0.25;
    
    for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
      if (leds_16[i].r > 0.05 || leds_16[i].g > 0.05 || leds_16[i].b > 0.05) {
        // Find dominant color and enhance it
        if (leds_16[i].r > leds_16[i].g && leds_16[i].r > leds_16[i].b) {
          leds_16[i].r *= (1.0 + enhancement);
        } else if (leds_16[i].g > leds_16[i].r && leds_16[i].g > leds_16[i].b) {
          leds_16[i].g *= (1.0 + enhancement);
        } else if (leds_16[i].b > leds_16[i].r && leds_16[i].b > leds_16[i].g) {
          leds_16[i].b *= (1.0 + enhancement);
        }
      }
    }
  }
  
  // Clip values to ensure they stay in valid range
  clip_led_values(leds_16);
}

// Add a quantization function for the secondary strip similar to primary
inline void quantize_color_secondary(bool temporal_dither) {
  if (temporal_dither) {
    static uint8_t noise_origin_r_s = 0, noise_origin_g_s = 0, noise_origin_b_s = 0;
    noise_origin_r_s++;
    noise_origin_g_s++;
    noise_origin_b_s++;
    for (uint16_t i = 0; i < SECONDARY_LED_COUNT; i++) {
      SQ15x16 decimal_r = leds_scaled_secondary[i].r * SQ15x16(254);
      SQ15x16 whole_r = decimal_r.getInteger();
      SQ15x16 fract_r = decimal_r - whole_r;
      if (fract_r >= dither_table[(noise_origin_r_s + i) % 4]) whole_r += SQ15x16(1);
      // Phase 1 2026-05-20: gamma applied at final uint8 write (secondary, dither path).
      leds_out_secondary[i].r = apply_gamma8(whole_r.getInteger());

      SQ15x16 decimal_g = leds_scaled_secondary[i].g * SQ15x16(254);
      SQ15x16 whole_g = decimal_g.getInteger();
      SQ15x16 fract_g = decimal_g - whole_g;
      if (fract_g >= dither_table[(noise_origin_g_s + i) % 4]) whole_g += SQ15x16(1);
      leds_out_secondary[i].g = apply_gamma8(whole_g.getInteger());

      SQ15x16 decimal_b = leds_scaled_secondary[i].b * SQ15x16(254);
      SQ15x16 whole_b = decimal_b.getInteger();
      SQ15x16 fract_b = decimal_b - whole_b;
      if (fract_b >= dither_table[(noise_origin_b_s + i) % 4]) whole_b += SQ15x16(1);
      leds_out_secondary[i].b = apply_gamma8(whole_b.getInteger());
    }
  } else {
    for (uint16_t i = 0; i < SECONDARY_LED_COUNT; i++) {
      // Phase 1 2026-05-20: gamma applied at final uint8 write (secondary, non-dither path).
      leds_out_secondary[i].r = apply_gamma8(uint8_t(leds_scaled_secondary[i].r * 255));
      leds_out_secondary[i].g = apply_gamma8(uint8_t(leds_scaled_secondary[i].g * 255));
      leds_out_secondary[i].b = apply_gamma8(uint8_t(leds_scaled_secondary[i].b * 255));
    }
  }
}

#endif // LED_UTILITIES_H
