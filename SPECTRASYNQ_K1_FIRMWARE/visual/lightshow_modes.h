#include <Arduino.h>
#include <FastLED.h>
#include <FixedPoints.h>
#include "constants.h"
#include "globals.h"
#include "led_utilities.h"
#include "Palettes.h" // Needed for palettes
#include "render_params.h" // RenderParams visible to all light_mode_*.cpp
#include "channel_effect_state.h" // Per-channel effect state for vu_dot/kaleidoscope

// Row 2: tx_begin/tx_end have external linkage and are defined in serial_menu.h,
// compiled in the .ino TU. The inline vp_run_output_probe harness below calls them.
// Forward-declared here (NO default arg — callers pass it explicitly) so per-mode .cpp
// TUs that include this header can parse the inline probe without pulling serial_menu.h
// (a 41-function ODR hazard). The .ino's serial_menu.h definition supplies the default.
void tx_begin(bool error);
void tx_end(bool error);

inline void get_smooth_spectrogram() {
  static SQ15x16 spectrogram_smooth_last[NUM_FREQS];

  for (uint8_t bin = 0; bin < NUM_FREQS; bin++) {
    SQ15x16 note_brightness = spectrogram[bin];

    // Phase 1 2026-05-20: asymmetric attack/release (was symmetric 0.75/0.75 — flattened transients).
    if (spectrogram_smooth[bin] < note_brightness) {
      SQ15x16 distance = note_brightness - spectrogram_smooth[bin];
      spectrogram_smooth[bin] += distance * SQ15x16(SPECTROGRAM_SMOOTH_ATTACK);

    } else if (spectrogram_smooth[bin] > note_brightness) {
      SQ15x16 distance = spectrogram_smooth[bin] - note_brightness;
      spectrogram_smooth[bin] -= distance * SQ15x16(SPECTROGRAM_SMOOTH_RELEASE);
    }
  }
}

inline CRGB calc_chromagram_color() {
  CRGB sum_color = CRGB(0, 0, 0);
  for (uint8_t i = 0; i < 12; i++) {
    float prog = i / 12.0;

    float bright = note_chromagram[i];
    for (uint8_t s = 0; s < CONFIG.SQUARE_ITER + 1; s++) {
      bright *= bright;
    }
    bright *= 0.5;

    if (bright > 1.0) {
      bright = 1.0;
    }

    if (chromatic_mode == true) {
      CRGB out_col = CHSV(uint8_t(prog * 255), uint8_t(CONFIG.SATURATION * 255), uint8_t(bright * 255));
      sum_color += out_col;
    }
  }

  if (chromatic_mode == false) {
    sum_color = force_saturation(sum_color, uint8_t(CONFIG.SATURATION * 255));
  }

  return sum_color;
}

inline CRGB16 crgb_to_crgb16(CRGB rgb_color) {
  return { SQ15x16(rgb_color.r / 255.0f), SQ15x16(rgb_color.g / 255.0f), SQ15x16(rgb_color.b / 255.0f) };
}

inline SQ15x16 clamp01_fixed(SQ15x16 value) {
  if (value < SQ15x16(0.0)) return SQ15x16(0.0);
  if (value > SQ15x16(1.0)) return SQ15x16(1.0);
  return value;
}

inline CRGB16 clamp_crgb16(CRGB16 color) {
  color.r = clamp01_fixed(color.r);
  color.g = clamp01_fixed(color.g);
  color.b = clamp01_fixed(color.b);
  return color;
}

inline CRGB16 clamp_crgb16_preserve_sat(CRGB16 color) {
  if (color.r < SQ15x16(0.0)) color.r = SQ15x16(0.0);
  if (color.g < SQ15x16(0.0)) color.g = SQ15x16(0.0);
  if (color.b < SQ15x16(0.0)) color.b = SQ15x16(0.0);

  SQ15x16 max_channel = color.r;
  if (color.g > max_channel) max_channel = color.g;
  if (color.b > max_channel) max_channel = color.b;

  if (max_channel > SQ15x16(1.0)) {
    const SQ15x16 scale = SQ15x16(1.0) / max_channel;
    color.r *= scale;
    color.g *= scale;
    color.b *= scale;
  }
  return color;
}

inline void finalize_additive_frame(CRGB16* leds, CRGB16* leds_prev_buffer, bool store_history) {
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds[i] = clamp_crgb16_preserve_sat(leds[i]);
  }
  if (store_history && leds_prev_buffer) {
    memcpy(leds_prev_buffer, leds, sizeof(CRGB16) * NATIVE_RESOLUTION);
  }
}

// ── HD PALETTE SAMPLING (2026-06-11, palette-resolution lane item 1) ─────────
// CRGBPalette16 flattens every gradient to 16 entries, and the old sampler
// rounded the coordinate to uint8 and returned an 8-bit CRGB — three losses
// before the 16-bit render pipeline ever saw the colour. The HD cache unpacks
// the palette's FULL stop list once per palette switch (per channel), and
// palette_manual_colour interpolates the true gradient in float, emitting
// native CRGB16. Unpack is switch-time only; sampling is a <=48-stop scan.
#define PAL_HD_MAX_STOPS 48

struct PaletteStopsHD {
  uint16_t count = 0;
  float    pos[PAL_HD_MAX_STOPS];
  float    r[PAL_HD_MAX_STOPS];
  float    g[PAL_HD_MAX_STOPS];
  float    b[PAL_HD_MAX_STOPS];
};

inline PaletteStopsHD& palette_hd_for_channel(bool render_secondary) {
  static PaletteStopsHD primary_hd;
  static PaletteStopsHD secondary_hd;
  return render_secondary ? secondary_hd : primary_hd;
}

inline void palette_hd_unpack(uint8_t palette_index, PaletteStopsHD& out) {
  // Direct indexing is portable: ESP32 PROGMEM is memory-mapped (pgm_read_byte
  // is a plain dereference there) and the host harness has no PROGMEM at all.
  const TProgmemRGBGradientPalette_byte* p = gGradientPalettes[palette_index];
  uint16_t n = 0;
  while (n < PAL_HD_MAX_STOPS) {
    const uint8_t idx = p[4 * n + 0];
    out.pos[n] = float(idx) / 255.0f;
    out.r[n]   = float(p[4 * n + 1]) / 255.0f;
    out.g[n]   = float(p[4 * n + 2]) / 255.0f;
    out.b[n]   = float(p[4 * n + 3]) / 255.0f;
    n++;
    if (idx == 255) break;  // FastLED gradient terminator
  }
  out.count = n;
}

inline const CRGBPalette16& cached_gradient_palette(uint8_t palette_index, bool render_secondary) {
  static CRGBPalette16 primary_palette;
  static CRGBPalette16 secondary_palette;
  static uint8_t primary_index = 255;
  static uint8_t secondary_index = 255;

  if (palette_index >= gGradientPaletteCount) {
    palette_index = 0;
  }

  if (render_secondary) {
    if (secondary_index != palette_index) {
      secondary_palette = CRGBPalette16(gGradientPalettes[palette_index]);
      secondary_index = palette_index;
      palette_hd_unpack(palette_index, palette_hd_for_channel(true));
    }
    return secondary_palette;
  }

  if (primary_index != palette_index) {
    primary_palette = CRGBPalette16(gGradientPalettes[palette_index]);
    primary_index = palette_index;
    palette_hd_unpack(palette_index, palette_hd_for_channel(false));
  }
  return primary_palette;
}

inline bool render_params_palette_owns_colour(const RenderParams* rp, bool render_secondary) {
  return render_secondary ? SECONDARY_PALETTE_MODE_ENABLED : (rp != nullptr && rp->PALETTE_MODE_ENABLED);
}

inline uint8_t render_params_palette_index(const RenderParams* rp, bool render_secondary) {
  return render_secondary ? SECONDARY_PALETTE_INDEX : (rp != nullptr ? rp->PALETTE_INDEX : CONFIG.PALETTE_INDEX);
}

inline bool render_params_auto_colour_shift(const RenderParams* rp, bool render_secondary) {
  return render_secondary ? SECONDARY_AUTO_COLOR_SHIFT : (rp != nullptr ? rp->AUTO_COLOR_SHIFT : CONFIG.AUTO_COLOR_SHIFT);
}

inline uint8_t palette_index_with_phase(uint8_t palette_index, bool auto_shift) {
  if (!auto_shift) {
    return palette_index;
  }
  return palette_index + uint8_t(float(hue_position) * 255.0f);
}

inline uint8_t palette_index_with_phase(uint8_t palette_index) {
  const RenderParams* rp = active_render_params();
  bool auto_shift = render_params_auto_colour_shift(rp, vp_render_secondary_channel);
  return palette_index_with_phase(palette_index, auto_shift);
}

inline uint8_t palette_index_with_phase(uint8_t palette_index, const RenderParams* rp, bool render_secondary) {
  return palette_index_with_phase(palette_index, render_params_auto_colour_shift(rp, render_secondary));
}

inline CRGB16 palette_manual_colour(const CRGBPalette16& pal, SQ15x16 hue, SQ15x16 brightness) {
  // HD PALETTE SAMPLING (2026-06-11): evaluate the true gradient stops in float
  // (full stop list, native CRGB16 out) instead of the 16-entry CRGBPalette16 +
  // uint8 coordinate + 8-bit CRGB round-trip. Auto-shift phase is applied in
  // float too, preserving sub-byte coordinate resolution. The passed pal stays
  // for signature compatibility and as the fallback if the HD cache is cold;
  // every live caller passes the active channel's palette, which is exactly
  // what the per-channel HD cache mirrors.
  float h = float(hue);
  if (!isfinite(h)) h = 0.0f;
  {
    const RenderParams* rp_phase = active_render_params();
    if (render_params_auto_colour_shift(rp_phase, vp_render_secondary_channel)) {
      h += float(hue_position);
    }
  }
  h -= floorf(h);
  if (h < 0.0f) h += 1.0f;

  const PaletteStopsHD& hd = palette_hd_for_channel(vp_render_secondary_channel);
  CRGB16 color;
  if (hd.count == 0) {
    // Cold cache (no cached_gradient_palette call yet this boot): legacy path.
    CRGB rgb_color = ColorFromPalette(pal, uint8_t(h * 255.0f), 255, LINEARBLEND);
    color = crgb_to_crgb16(rgb_color);
  } else {
    uint16_t i = 0;
    while (i + 1 < hd.count && hd.pos[i + 1] < h) i++;
    float cr, cg, cb;
    if (i + 1 >= hd.count || h <= hd.pos[0]) {
      const uint16_t k = (h <= hd.pos[0]) ? 0 : (hd.count - 1);
      cr = hd.r[k]; cg = hd.g[k]; cb = hd.b[k];
    } else {
      const float span = hd.pos[i + 1] - hd.pos[i];
      float t = (span > 1e-6f) ? (h - hd.pos[i]) / span : 0.0f;
      if (t < 0.0f) t = 0.0f;
      if (t > 1.0f) t = 1.0f;
      cr = hd.r[i] + (hd.r[i + 1] - hd.r[i]) * t;
      cg = hd.g[i] + (hd.g[i + 1] - hd.g[i]) * t;
      cb = hd.b[i] + (hd.b[i + 1] - hd.b[i]) * t;
    }
    color.r = SQ15x16(cr);
    color.g = SQ15x16(cg);
    color.b = SQ15x16(cb);
  }

  SQ15x16 level = clamp01_fixed(brightness);
  color.r *= level;
  color.g *= level;
  color.b *= level;
  return clamp_crgb16(color);
}

#ifdef K1_PALETTE_VIBRANCY_V1
// K1 PALETTE VIBRANCY (2026-07-02): weak-centroid hue blend. Instead of hard-
// freezing the palette coordinate at centroid_strength < 0.08 (which pinned
// every palette to ONE slowly-auto-shifted colour on dense/loud material —
// device-proven collapse chain, see docs/forensics 2026-07-02 lane), blend the
// held anchor toward the LIVE centroid proportionally to strength. Continuous
// at the threshold (w→1 reduces to the live hue, w→0 to the old hold). The
// blend target is the live centroid, NEVER dominant-bin 0 — the dark-start
// palette crush (2026-06-11 bisect) cannot re-enter through this path.
inline float k1_vibrancy_blend_hue(float live_hue, float anchor_hue, float strength) {
  float w = strength / 0.08f;
  if (!isfinite(w) || w < 0.0f) w = 0.0f;
  if (w > 1.0f) w = 1.0f;
  float delta = live_hue - anchor_hue;
  if (delta > 0.5f) delta -= 1.0f;
  if (delta < -0.5f) delta += 1.0f;
  float out = anchor_hue + delta * w;
  out -= floorf(out);
  if (out < 0.0f) out += 1.0f;
  return out;
}
#endif

inline CRGB16 palette_chroma_colour_with_offset(const CRGBPalette16& pal, SQ15x16 fallback_brightness,
                                                float chroma, float hue_offset) {
  // Palette colour must be sampled once per rendered colour. Summing multiple
  // palette RGB samples collapses gradients toward grey/white.  Use the raw
  // chromagram to choose the palette position, and use brightness separately.
  float total_weight = 0.0f;
  float max_weight = 0.0f;
  uint8_t dominant_bin = 0;
  float x = 0.0f;
  float y = 0.0f;
  static const float TWO_PI_F = 6.2831853071795864769f;

  for (uint8_t c = 0; c < 12; c++) {
#ifdef K1_PALETTE_VIBRANCY_V1
    // K1 PALETTE VIBRANCY: coordinate selection reads the PRE-gate chromagram
    // (full relative shape survives dense/flat material; the sparseness gate
    // stays in force for chromatic-mode brightness/summing consumers).
    float raw_bin = float(chromagram_pregate[c]);
#else
    float raw_bin = float(chromagram_smooth[c]);
#endif
    if (!isfinite(raw_bin) || raw_bin < 0.0f) raw_bin = 0.0f;
    if (raw_bin > 1.0f) raw_bin = 1.0f;

    float angle = (float(c) / 12.0f) * TWO_PI_F;
    x += cosf(angle) * raw_bin;
    y += sinf(angle) * raw_bin;
    total_weight += raw_bin;
    if (raw_bin > max_weight) {
      max_weight = raw_bin;
      dominant_bin = c;
    }
  }

  SQ15x16 brightness = clamp01_fixed(fallback_brightness);

  // PALETTE-CRUSH FIX (2026-06-11, Captain-approved A): when the chromagram is
  // gated to zero (quiet / spectrally flat passages, see the VP sparseness gate
  // in led_utilities.h), fall back to the LAST LIVE centroid instead of the
  // fixed CHROMA coordinate (default 0.0). The fixed fallback collapsed every
  // palette to its first gradient colour identically — the dominant palette
  // "crush" path (docs/forensics/2026-06-11-palette-crush-audit.md). Core-1
  // render only; both channels share the same audio, so one held hue is sound.
  static float held_centroid_hue = 0.0f;
  static bool held_hue_valid = false;

  if (total_weight <= 0.0001f) {
#ifdef K1_PIN_EVIDENCE_V1
    k1_pin_palette_held_hue_valid = held_hue_valid;
    k1_pin_palette_held_hue = held_centroid_hue;
    k1_pin_palette_centroid_strength = 0.0f;
    k1_pin_palette_dominant_bin = dominant_bin;
    k1_pin_palette_index = vp_render_secondary_channel ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
#endif
    return palette_manual_colour(pal, SQ15x16(held_centroid_hue), brightness);
  }

  float hue = atan2f(y, x) / TWO_PI_F;
  if (!isfinite(hue)) hue = held_centroid_hue;
  if (hue < 0.0f) hue += 1.0f;

  // PALETTE-RESOLUTION SALVAGE (2026-06-11, recovered from the f23e438 Codex
  // tree — the GOOD half of that colour change, without its palette-data
  // damage; Captain remembers this as "significantly more palette resolution"):
  // dense or harmonically balanced material makes the circular centroid very
  // weak — a near-zero vector picks an arbitrary palette coordinate (the old
  // grey/white averaging trap). Sample the DOMINANT chroma bin instead: one
  // palette lookup per rendered colour, at a musically meaningful coordinate.
  const float centroid_mag = sqrtf((x * x) + (y * y));
  const float centroid_strength = centroid_mag / total_weight;
  float avg_weight = total_weight / 12.0f;
  float contrast = max_weight - avg_weight;
  if (contrast < 0.0f) contrast = 0.0f;
  // BISECT FIX (2026-06-11, Captain-approved "held-hue first"): on weak
  // centroids the dominant bin is 0 on dim/ambiguous frames, and coordinate
  // 0.0 is the BLACK head of dark-start palettes — it crushed the dim field
  // to true black (lit_fraction 0.569→0.239, _scratch/detail-gap/03-bisect.md).
  // Prefer the last LIVE centroid hue; sample the dominant bin only before any
  // strong centroid has ever been seen. Weak frames must NOT overwrite the
  // held hue, or one ambiguous frame poisons every quiet frame after it.
  if (!isfinite(centroid_strength) || centroid_strength < 0.08f) {
    const float dominant_hue = float(dominant_bin) / 12.0f;
#ifdef K1_LOUD_GUARD_V1
    const bool k1_loud_colour_unpin =
        k1_loud_guard_enabled &&
        (k1_loud_gdft_trim < 0.92f || k1_loud_peak_pin_duty > 0.10f || k1_loud_spec_sat_duty > 0.02f) &&
        contrast >= K1_LOUD_GUARD_CHROMA_UNPIN_MIN_CONTRAST;
    if (k1_loud_colour_unpin && held_hue_valid) {
      float delta = dominant_hue - held_centroid_hue;
      if (delta > 0.5f) delta -= 1.0f;
      if (delta < -0.5f) delta += 1.0f;
      hue = held_centroid_hue + (delta * K1_LOUD_GUARD_CHROMA_UNPIN_BLEND);
      hue -= floorf(hue);
      if (hue < 0.0f) hue += 1.0f;
      held_centroid_hue = hue;
    } else if (k1_loud_colour_unpin) {
      hue = dominant_hue;
      held_centroid_hue = hue;
      held_hue_valid = true;
    } else {
#ifdef K1_PALETTE_VIBRANCY_V1
      hue = held_hue_valid ? k1_vibrancy_blend_hue(hue, held_centroid_hue, centroid_strength) : dominant_hue;
#else
      hue = held_hue_valid ? held_centroid_hue : dominant_hue;
#endif
    }
#else
#ifdef K1_PALETTE_VIBRANCY_V1
    hue = held_hue_valid ? k1_vibrancy_blend_hue(hue, held_centroid_hue, centroid_strength) : dominant_hue;
#else
    hue = held_hue_valid ? held_centroid_hue : dominant_hue;
#endif
#endif
  } else {
    held_centroid_hue = hue;
    held_hue_valid = true;
  }

  if (!isfinite(hue_offset)) hue_offset = 0.0f;
  hue += hue_offset;
  hue -= floorf(hue);
  if (hue < 0.0f) hue += 1.0f;
#ifdef K1_PIN_EVIDENCE_V1
  k1_pin_palette_held_hue_valid = held_hue_valid;
  k1_pin_palette_held_hue = held_centroid_hue;
  k1_pin_palette_centroid_strength = centroid_strength;
  k1_pin_palette_dominant_bin = dominant_bin;
  k1_pin_palette_index = vp_render_secondary_channel ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
#endif

  // PALETTE-RESOLUTION SALVAGE (same recovery): contrast-boosted energy.
  // Old 0.75*max + 0.25*avg pinned dense/balanced material to full value —
  // every additive blend then clipped toward WHITE. The contrast term rewards
  // a clear dominant note (brighter peaks = "resolution") while balanced
  // chromagrams render ~30% dimmer, keeping palette colour instead of white.
  float energy = (max_weight * 0.62f) + (contrast * 0.30f) + (avg_weight * 0.08f);
  if (energy > 1.0f) energy = 1.0f;
  if (energy < 0.0f) energy = 0.0f;

  SQ15x16 energy_fixed = SQ15x16(energy);
  if (energy_fixed > brightness) brightness = energy_fixed;
  brightness = clamp01_fixed(brightness);

#ifdef K1_PALETTE_ENERGY_EXCURSION_V1
  // PALETTE-RESOLUTION lane item 2 ("value-ramp lite", 2026-06-11): chroma
  // energy sweeps the sampling coordinate UP-gradient from the harmonic anchor
  // (one-sided, 0..+0.20) — dynamics traverse the palette's authored arc during
  // crescendos while quiet passages hold the anchor. One-sided on purpose: a
  // centred ±excursion swept quiet moments into dark stops, double-dimming on
  // dark-heavy palettes (measured: bloom/palette-3 distinct colours 48→25 with
  // the centred form). The held centroid (above) stays the pure anchor.
  // REVERT = delete the -D flag; off-flag is byte-identical.
  hue += energy * 0.20f;
  hue -= floorf(hue);
  if (hue < 0.0f) hue += 1.0f;
#endif

  return palette_manual_colour(pal, SQ15x16(hue), brightness);
}

inline CRGB16 palette_chroma_colour(const CRGBPalette16& pal, SQ15x16 fallback_brightness, float chroma) {
  return palette_chroma_colour_with_offset(pal, fallback_brightness, chroma, 0.0f);
}

// ----------------------------------------------------------------------------
// effect_palette_or_chroma_colour — the PROVEN colour authority used by BLOOM.
// Returns the centre-injection colour, honouring (in priority): palette mode,
// then the chromatic/HSV note-sum with square-iter contrast + force_saturation,
// and — when chromatic_mode is off — force_hue toward (chroma_val + hue_position),
// where hue_position IS the auto-colour-shift phase. `brightness_scale` (clamped
// 0..1) multiplies the final colour: pass 1.0 for full brightness (Aurora) or a
// strength-derived value (Comet) to dim quieter events.
//
// Why this exists: BLOOM-lineage effects MUST NOT call palette_chroma_colour
// directly — that is the PALETTE-mode engine only. The K1 default is
// chromatic_mode==true with palette mode off, so a direct call pins the effect
// to one colour and ignores auto-colour-shift. This helper mirrors BLOOM exactly
// so new effects respect palette selection, chromatic colour, and auto-shift
// identically to the proven reference, in every colour-authority configuration.
inline CRGB16 effect_palette_or_chroma_colour(const RenderParams* rp, bool render_secondary, SQ15x16 brightness_scale) {
  const bool palette_owns_colour = render_params_palette_owns_colour(rp, render_secondary);
  const uint8_t palette_to_use   = render_params_palette_index(rp, render_secondary);
  const CRGBPalette16& pal       = cached_gradient_palette(palette_to_use, render_secondary);

  CRGB16 final_color;
  if (palette_owns_colour) {
    // Palette mode owns colour: sample the selected gradient via the proven
    // engine (chromagram-centroid hue + auto-shift phase).
    final_color = palette_chroma_colour(pal, SQ15x16(0.0), rp->CHROMA);
    if (final_color.r > SQ15x16(1.0)) final_color.r = SQ15x16(1.0); else if (final_color.r < SQ15x16(0.0)) final_color.r = SQ15x16(0.0);
    if (final_color.g > SQ15x16(1.0)) final_color.g = SQ15x16(1.0); else if (final_color.g < SQ15x16(0.0)) final_color.g = SQ15x16(0.0);
    if (final_color.b > SQ15x16(1.0)) final_color.b = SQ15x16(1.0); else if (final_color.b < SQ15x16(0.0)) final_color.b = SQ15x16(0.0);
  } else {
    // Chromatic mode (K1 default): note-summed HSV across the 12 chroma bins,
    // square-iter contrast, force_saturation, then (only when chromatic_mode is
    // off) force_hue toward chroma_val + hue_position. Identical to BLOOM.
    CRGB16 sum_color; memset(&sum_color, 0, sizeof(CRGB16));
    SQ15x16 share = SQ15x16(1.0) / SQ15x16(6.0);
    for (uint8_t i = 0; i < 12; i++) {
      SQ15x16 prog = SQ15x16(float(i) / 12.0f);
      SQ15x16 bin  = chromagram_smooth[i];
      CRGB16 add_color = hsv(prog, SQ15x16(rp->SATURATION), bin * bin * share);
      sum_color.r += add_color.r;
      sum_color.g += add_color.g;
      sum_color.b += add_color.b;
    }
    if (sum_color.r > SQ15x16(1.0)) sum_color.r = SQ15x16(1.0);
    if (sum_color.g > SQ15x16(1.0)) sum_color.g = SQ15x16(1.0);
    if (sum_color.b > SQ15x16(1.0)) sum_color.b = SQ15x16(1.0);
    for (uint8_t i = 0; i < uint8_t(rp->SQUARE_ITER); i++) {
      sum_color.r *= sum_color.r;
      sum_color.g *= sum_color.g;
      sum_color.b *= sum_color.b;
    }
    CRGB temp_col_rgb = { uint8_t(float(sum_color.r) * 255), uint8_t(float(sum_color.g) * 255), uint8_t(float(sum_color.b) * 255) };
    temp_col_rgb = force_saturation(temp_col_rgb, uint8_t(255 * float(rp->SATURATION)));
    if (chromatic_mode == false) {
      SQ15x16 led_hue = chroma_val + hue_position + SQ15x16(0.05);
      temp_col_rgb = force_hue(temp_col_rgb, uint8_t(255 * float(led_hue)));
    }
    final_color = CRGB16{ SQ15x16(temp_col_rgb.r / 255.0f), SQ15x16(temp_col_rgb.g / 255.0f), SQ15x16(temp_col_rgb.b / 255.0f) };
  }

  SQ15x16 scale = clamp01_fixed(brightness_scale);
  final_color.r *= scale;
  final_color.g *= scale;
  final_color.b *= scale;
  return clamp_crgb16(final_color);
}

// Live palette-position hue (0..1) from the chromagram centroid — the same
// centroid palette_chroma_colour() uses. Tracks harmony every frame.
inline float chromagram_centroid_hue() {
  static const float TWO_PI_F = 6.2831853071795864769f;
  float x = 0.0f, y = 0.0f;
  for (uint8_t c = 0; c < 12; c++) {
#ifdef K1_PALETTE_VIBRANCY_V1
    float b = float(chromagram_pregate[c]);  // K1 PALETTE VIBRANCY: particle palette coords read pre-gate chroma (consistent with palette_chroma_colour_with_offset)
#else
    float b = float(chromagram_smooth[c]);
#endif
    if (!isfinite(b) || b < 0.0f) b = 0.0f;
    if (b > 1.0f) b = 1.0f;
    float a = (float(c) / 12.0f) * TWO_PI_F;
    x += cosf(a) * b;
    y += sinf(a) * b;
  }
  if (x == 0.0f && y == 0.0f) return 0.0f;
  float h = atan2f(y, x) / TWO_PI_F;
  if (!isfinite(h)) h = 0.0f;
  if (h < 0.0f) h += 1.0f;
  return h;
}

// Per-PARTICLE colour for discrete-object effects (e.g. Comet). In palette mode
// it samples the SELECTED gradient at (live chromagram-centroid hue + a
// per-particle OFFSET), so concurrent particles render DIFFERENT palette colours
// while the base still tracks harmony + auto-shift (palette_manual_colour folds
// in the auto-shift phase). Chromatic mode (no palette active) returns the single
// live chromatic colour — no hand-rolled HSV hue travel. MUST be recomputed LIVE
// each frame; never freeze at launch (that was the v1 single-colour bug).
inline CRGB16 effect_particle_colour(const RenderParams* rp, bool render_secondary, float hue_offset, SQ15x16 brightness) {
  if (render_params_palette_owns_colour(rp, render_secondary)) {
    const CRGBPalette16& pal = cached_gradient_palette(render_params_palette_index(rp, render_secondary), render_secondary);
    return clamp_crgb16(palette_manual_colour(pal, SQ15x16(chromagram_centroid_hue() + hue_offset), brightness));
  }
  return effect_palette_or_chroma_colour(rp, render_secondary, brightness);
}

inline void avg_bins(uint8_t low_bin, uint8_t high_bin) {
  // TBD
}

inline void test_mode() {
  static float radians = 0.00;
  radians += CONFIG.MOOD;
  float position = sin(radians) * 0.5 + 0.5;
  set_dot_position(RESERVED_DOTS + 0, position);
  clear_leds();
  draw_dot(leds_16, RESERVED_DOTS + 0, hsv(chroma_val, CONFIG.SATURATION, CONFIG.PHOTONS * CONFIG.PHOTONS));
}

// Default mode!
void light_mode_gdft();

/*
void light_mode_gdft_chromagram() {
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    float prog = i / float(NATIVE_RESOLUTION);

    float bin = interpolate(prog, note_chromagram, 12) * 1.25;
    if (bin > 1.0) { bin = 1.0; };

    for (uint8_t s = 0; s < CONFIG.SQUARE_ITER + 1; s++) {
      bin = bin * bin;
    }

    bin *= 1.0 - CONFIG.BACKDROP_BRIGHTNESS;
    bin += CONFIG.BACKDROP_BRIGHTNESS;

    float led_brightness_raw = 254 * bin;  // -1 for temporal dithering below
    uint16_t led_brightness = led_brightness_raw;
    float fract = led_brightness_raw - led_brightness;

    if (CONFIG.TEMPORAL_DITHERING == true) {
      if (fract >= dither_table[dither_step]) {
        led_brightness += 1;
      }
    }

    float led_hue;
    if (chromatic_mode == true) {
      //led_hue = 255 * prog;
    } else {
      //led_hue = 255 * chroma_val + (i >> 1) + hue_shift;
    }

    //leds[i] = CHSV(led_hue + hue_shift, 255 * CONFIG.SATURATION, led_brightness);
  }
}
*/

/*
void light_mode_bloom(bool fast_scroll) {
  static uint32_t iter = 0;
  const float led_share = 1.0 / 12.0;
  iter++;

  if (bitRead(iter, 0) == 0) {
    CRGB sum_color = calc_chromagram_color();

    //sum_color = force_saturation(sum_color, 255 * CONFIG.SATURATION);

    if (fast_scroll == true) {  // Fast mode scrolls two LEDs at a time
      for (uint8_t i = 0; i < NATIVE_RESOLUTION - 2; i++) {
        leds_fx[(NATIVE_RESOLUTION - 1) - i] = leds_last[(NATIVE_RESOLUTION - 1) - i - 2];
      }

      leds_fx[0] = sum_color;  // New information goes here
      leds_fx[1] = sum_color;  // New information goes here

    } else {  // Slow mode only scrolls one LED at a time
      for (uint8_t i = 0; i < NATIVE_RESOLUTION - 1; i++) {
        leds_fx[(NATIVE_RESOLUTION - 1) - i] = leds_last[(NATIVE_RESOLUTION - 1) - i - 1];
      }

      leds_fx[0] = sum_color;  // New information goes here
    }

    load_leds_from_fx();
    save_leds_to_last();

    //fadeToBlackBy(leds, 128, 255-255*waveform_peak_scaled);

    distort_logarithmic();
    //distort_exponential();

    fade_top_half(CONFIG.MIRROR_ENABLED);  // fade at different location depending if mirroring is enabled
    //increase_saturation(32);

    save_leds_to_aux();
  } else {
    load_leds_from_aux();
  }
}
*/

void light_mode_vu(SQ15x16& level_smooth, SQ15x16& max_level);

void light_mode_vu_dot(ChannelEffectState& fx);

void light_mode_kaleidoscope(ChannelEffectState& fx);

void light_mode_chromagram_gradient();

void light_mode_chromagram_dots();

void light_mode_bloom(CRGB16* leds_prev_buffer, SQ15x16 shift_multiplier = SQ15x16(1.0));

void light_mode_quantum_collapse();

void light_mode_bloom_fast(CRGB16* leds_prev_buffer);

void light_mode_aurora(CRGB16* leds_prev_buffer);  // Aurora — colour-in-motion (BLOOM-family)
void light_mode_spectrum_river(CRGB16* leds_prev_buffer);  // Spectrum River — spectrum-as-space, flowed outward (WAVEFORM-family)
void light_mode_spectrum_river_v2(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // SRv2 — bass-energy breathing tide
void light_mode_ember(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Ember Field — centre-anchored energy-bloom glow
void light_mode_ember_v2(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Ember v2 — full-strip glow, MOOD-driven scroll

void light_mode_comet(ChannelEffectState& fx);     // Comet — onset-driven traveling heads (WAVEFORM-family)

void light_mode_waveform_tempo(ChannelEffectState& fx);  // Waveform Tempo — tempo-phase-locked continuous scroll velocity (WIP-1)
void light_mode_tempo_river(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Tempo River — River flow VELOCITY locked to beat phase (2026-06-04)
void light_mode_tempo_comet(ChannelEffectState& fx);  // Tempo Comet — beat-grid-locked travelling comets (2026-06-04)
void light_mode_dense_forge(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Dense Forge — clipped EDM intensity field (2026-06-07)
void light_mode_snapwave(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Snapwave — tonal chroma phase-interference oscillator (2026-06-07)
void light_mode_pulse_prism(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Pulse Prism — kick-primary centre shockwave rings (2026-06-07)
void light_mode_dense_forge_chord(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Dense Forge Chord — variant with chord-root hue anchor (2026-06-11)
void light_mode_chroma_constellation(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Chroma Constellation — pitch-class stars on outward transport (2026-06-11)
void light_mode_percussion_burst(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Percussion Burst — kick/snare/hihat spatial decomposition (2026-06-11)
void light_mode_tempo_comet_anticipate(ChannelEffectState& fx);  // Tempo Comet Anticipate — comets decelerate into the next beat (2026-06-11)
void light_mode_river_surge(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // River Surge — Spectrum River v2 + build/drop macro-dynamics (2026-06-11)
void light_mode_tempo_river_walk(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Tempo River Walk — palette walks one step per bar (2026-06-11)
void light_mode_beat_pulse(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Beat Pulse (Resonant) — twin rings contract edge->centre on each beat; firmware-v3 0x1404 port (2026-07-11)
void light_mode_bloom_bt(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Bloom BassTreble — bass births rings, treble drives speed, sqrt-warped bloom; firmware-v3 0x1309 port (2026-07-11)
void light_mode_waveform_hybrid_k1(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Waveform Hybrid — amplitude-bouncing dot + scroll trail; firmware-v3 0x1313 port (2026-07-11)
void light_mode_moire_cathedral(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Moire Cathedral — migrating detuned gratings; firmware-v3 0x1C08 port (2026-07-11)
void light_mode_cannonade(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Cannonade — ballistic lob, arc-and-return, centre crack (LIGHT_MODE_CANNONADE, 2026-07-11)
void light_mode_shockwave(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Shockwave — pure-age expanding shells (LIGHT_MODE_SHOCKWAVE, 2026-07-11)
void light_mode_iris(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Iris — in-place spring dilate-recoil membrane (LIGHT_MODE_IRIS, 2026-07-11)
void light_mode_melodic_bloom(CRGB16* leds_prev_buffer, ChannelEffectState& fx);  // Melodic Bloom — mid-forward presence bloom driven by post-AGC mid_energy (LIGHT_MODE_MELODIC_BLOOM, 2026-07-17)

inline uint16_t waveform_full_strip_position(float amp) {
  if (amp > 1.0f) amp = 1.0f;
  else if (amp < -1.0f) amp = -1.0f;

  const int center = NATIVE_RESOLUTION / 2;
  float pos_f = center + amp * (NATIVE_RESOLUTION / 2.0f);
  int pos = int(pos_f + (pos_f >= 0 ? 0.5f : -0.5f));
  if (pos < 0) pos = 0;
  if (pos >= NATIVE_RESOLUTION) pos = NATIVE_RESOLUTION - 1;
  return uint16_t(pos);
}

inline uint16_t waveform_upper_half_source_position(float amp) {
  uint16_t pos = waveform_full_strip_position(amp);
  const uint16_t half_res = NATIVE_RESOLUTION >> 1;
  if (pos < half_res) pos = half_res;
  return pos;
}

inline void waveform_shift_upper_half_up(CRGB16* led_array, uint8_t steps) {
  const uint16_t half_res = NATIVE_RESOLUTION >> 1;
  if (steps > half_res) steps = half_res;

  for (uint8_t step = 0; step < steps; step++) {
    for (int16_t i = NATIVE_RESOLUTION - 1; i > int16_t(half_res); i--) {
      led_array[i] = led_array[i - 1];
    }
    led_array[half_res] = {0,0,0};
  }
}

void light_mode_waveform_fast(CRGB16* leds_previous, CRGB16& last_color, float& waveform_peak_scaled_last,
                              float& shift_accum, uint32_t& last_frame_ms);

inline void waveform_shift_outward(CRGB16* led_array, uint8_t steps) {
  if (steps == 0) {
    return;
  }
  if (steps > (NATIVE_RESOLUTION / 2)) {
    steps = NATIVE_RESOLUTION / 2;
  }

  const uint16_t centre_left = (NATIVE_RESOLUTION / 2) - 1;
  const uint16_t centre_right = NATIVE_RESOLUTION / 2;

  for (uint8_t step = 0; step < steps; step++) {
    for (uint16_t i = 0; i < centre_left; i++) {
      led_array[i] = led_array[i + 1];
    }
    for (int16_t i = NATIVE_RESOLUTION - 1; i > int16_t(centre_right); i--) {
      led_array[i] = led_array[i - 1];
    }
    led_array[centre_left] = {0,0,0};
    led_array[centre_right] = {0,0,0};
  }
}

void light_mode_waveform(CRGB16* leds_previous, CRGB16& last_color, float& waveform_peak_scaled_last,
                         float& shift_accum, uint32_t& last_frame_ms);

void light_mode_waveform_hybrid(CRGB16* leds_previous, CRGB16& last_color, float& waveform_peak_scaled_last,
                                float& shift_accum, uint32_t& last_frame_ms);

inline uint16_t vp_probe_quantise_channel(SQ15x16 value) {
  float v = float(value);
  if (!isfinite(v)) v = 0.0f;
  if (v < 0.0f) v = 0.0f;
  if (v > 1.0f) v = 1.0f;
  return uint16_t((v * 65535.0f) + 0.5f);
}

inline void vp_probe_hash_byte(uint32_t& hash, uint8_t value) {
  hash ^= value;
  hash *= 16777619UL;
}

inline uint32_t vp_probe_hash_leds(CRGB16* buffer) {
  uint32_t hash = 2166136261UL;
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    uint16_t r = vp_probe_quantise_channel(buffer[i].r);
    uint16_t g = vp_probe_quantise_channel(buffer[i].g);
    uint16_t b = vp_probe_quantise_channel(buffer[i].b);
    vp_probe_hash_byte(hash, uint8_t(r & 0xff));
    vp_probe_hash_byte(hash, uint8_t(r >> 8));
    vp_probe_hash_byte(hash, uint8_t(g & 0xff));
    vp_probe_hash_byte(hash, uint8_t(g >> 8));
    vp_probe_hash_byte(hash, uint8_t(b & 0xff));
    vp_probe_hash_byte(hash, uint8_t(b >> 8));
  }
  return hash;
}

inline uint32_t vp_probe_energy(CRGB16* buffer) {
  uint32_t energy = 0;
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    energy += uint32_t(vp_probe_quantise_channel(buffer[i].r) >> 8);
    energy += uint32_t(vp_probe_quantise_channel(buffer[i].g) >> 8);
    energy += uint32_t(vp_probe_quantise_channel(buffer[i].b) >> 8);
  }
  return energy;
}

#ifdef ENABLE_FRAME_DUMP
// PIO-FDUMP (2026-05-25): VP Tier B per-frame metric stream.
// COM = luminance-weighted centre-of-mass (spatial moment); a drift in COM-slope over a
// window is the transport-drift detector (the WAVEFORM_FAST 1.60x class). Returns the
// strip centre for a dark frame so an idle frame doesn't read as edge bias.
inline float vp_com(CRGB16* buf) {
  double wsum = 0.0, isum = 0.0;
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    float l = (float)buf[i].r + (float)buf[i].g + (float)buf[i].b;
    wsum += l;
    isum += (double)i * l;
  }
  return (wsum > 0.0) ? (float)(isum / wsum) : (float)(NATIVE_RESOLUTION * 0.5f);
}

// Called once per render frame from led_thread (before show_leds), leds_16 = primary
// rendered frame. Emits FNV hash + total energy + COM + FPS every frame_dump_every_n frames.
inline void frame_dump_tick() {
  if (!frame_dump_active) return;
  frame_dump_frame++;
  if (frame_dump_every_n <= 1 || (frame_dump_frame % frame_dump_every_n) == 0) {
    uint32_t energy = vp_probe_energy(leds_16);
    uint32_t hash = vp_probe_hash_leds(leds_16);
    float com = vp_com(leds_16);
    USBSerial.printf("[FDUMP] mode=%u f=%lu com=%.3f energy=%lu hash=%lx fps=%.1f\n",
      (unsigned)CONFIG.LIGHTSHOW_MODE, (unsigned long)frame_dump_frame,
      com, (unsigned long)energy, (unsigned long)hash, (float)LED_FPS);
  }
  if (int32_t(millis() - frame_dump_end_ms) >= 0) {
    USBSerial.println("[FDUMP] end");
    frame_dump_active = false;
  }
}
#endif

inline void vp_probe_seed_inputs() {
  for (uint8_t i = 0; i < NUM_FREQS; i++) {
    float phase = float(i % 16) / 15.0f;
    spectrogram_smooth[i] = SQ15x16(0.08f + (phase * 0.62f));
  }
  for (uint8_t i = 0; i < 12; i++) {
    float phase = float((i * 5) % 12) / 11.0f;
    chromagram_smooth[i] = SQ15x16(0.10f + (phase * 0.70f));
  }
  max_waveform_val_raw = float(CONFIG.SWEET_SPOT_MIN_LEVEL) * 2.0f;
  waveform_peak_scaled = 0.45f;
  audio_vu_level_average = SQ15x16(0.35f);

  if (waveform_history != nullptr) {
    for (uint8_t frame = 0; frame < 4; frame++) {
      for (uint16_t i = 0; i < CONFIG.SAMPLES_PER_CHUNK && i < 1024; i++) {
        int16_t centred = int16_t((int32_t(i % 64) - 32) * 256);
        waveform_history[frame][i] = (frame & 1) ? -centred : centred;
      }
    }
  }
}

// PIO-VPRESET (2026-05-25): Deliverable #4 reset helper. Bumps the generation so
// modes with function-local statics (vu_dot, kaleidoscope) zero them on next entry.
// Global-static modes (waveform*, vu) are reset explicitly below. Quantum (mode 6)
// is non-Tier-A and intentionally NOT made deterministic here.
inline void vp_probe_reset_mode_statics() {
  vp_probe_reset_generation++;
}

inline void vp_probe_prepare_render(bool palette_mode, float chroma, float saturation, SQ15x16 hue_offset) {
  vp_probe_reset_mode_statics();
  memset(leds_16, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memset(leds_16_prev, 0, sizeof(CRGB16) * NATIVE_RESOLUTION);
  for (uint16_t i = 0; i < MAX_DOTS; i++) {
    dots[i].position = SQ15x16(0.5);
    dots[i].last_position = SQ15x16(0.5);
  }

  CONFIG.PALETTE_MODE_ENABLED = palette_mode;
  CONFIG.PALETTE_INDEX = 3;
  CONFIG.CHROMA = chroma;
  CONFIG.SATURATION = saturation;
  CONFIG.AUTO_COLOR_SHIFT = true;
  CONFIG.MIRROR_ENABLED = true;
  CONFIG.SQUARE_ITER = 1.0f;
  CONFIG.MOOD = 0.05f;

  hue_position = hue_offset;
  hue_shifting_mix = SQ15x16(0.35f);
  chromatic_mode = chroma >= 0.95f;
  chroma_val = chromatic_mode ? SQ15x16(1.0f) : SQ15x16(chroma * 1.05263157f);

  waveform_fast_last_color_primary = {0,0,0};
  waveform_last_color_primary = {0,0,0};
  waveform_hybrid_last_color_primary = {0,0,0};
  waveform_fast_peak_scaled_last_primary = 0.0f;
  waveform_peak_scaled_last_primary = 0.0f;
  waveform_hybrid_peak_scaled_last_primary = 0.0f;
  waveform_fast_shift_accum_primary = 0.0f;
  waveform_shift_accum_primary = 0.0f;
  waveform_hybrid_shift_accum_primary = 0.0f;
  waveform_fast_last_frame_ms_primary = 0;
  waveform_last_frame_ms_primary = 0;
  waveform_hybrid_last_frame_ms_primary = 0;
  vu_level_smooth_primary = 0.0;
  vu_max_level_primary = 0.01;

  // ChannelEffectState (items 9-15): reset the primary effect state to its
  // canonical init so probe determinism holds. This replaces the per-mode
  // vp_probe_reset_generation blocks formerly inside light_mode_vu_dot() /
  // light_mode_kaleidoscope(); the probe renders primary only.
  memset(&effect_state_primary, 0, sizeof(effect_state_primary));
  effect_state_primary.vu_dot_max_level = 0.01;
}

// Mode-dispatch + energy + hash, factored out of vp_probe_render_hash() so the
// secondary bleed probe (item 17) can hash a pushed-RenderParams render without
// re-running vp_probe_prepare_render() (which would reset the channel flag/CONFIG).
// PURE RELOCATION: the switch body, mode order, energy and hash are identical to
// what vp_probe_render_hash() ran inline before — :vp_probe=all stays byte-identical.
inline uint32_t vp_probe_dispatch_and_hash(uint8_t mode, uint32_t& energy) {
  if (mode == LIGHT_MODE_GDFT) {
    light_mode_gdft();
  } else if (mode == LIGHT_MODE_GDFT_CHROMAGRAM) {
    light_mode_chromagram_gradient();
  } else if (mode == LIGHT_MODE_GDFT_CHROMAGRAM_DOTS) {
    light_mode_chromagram_dots();
  } else if (mode == LIGHT_MODE_BLOOM) {
    light_mode_bloom(leds_16_prev);
  } else if (mode == LIGHT_MODE_BLOOM_FAST) {
    light_mode_bloom_fast(leds_16_prev);
  } else if (mode == LIGHT_MODE_VU) {
    light_mode_vu(vu_level_smooth_primary, vu_max_level_primary);
  } else if (mode == LIGHT_MODE_WAVEFORM_FAST) {
    memcpy(leds_16, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_waveform_fast(leds_16_prev, waveform_fast_last_color_primary, waveform_fast_peak_scaled_last_primary,
                             waveform_fast_shift_accum_primary, waveform_fast_last_frame_ms_primary);
  } else if (mode == LIGHT_MODE_WAVEFORM) {
    memcpy(leds_16, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_waveform(leds_16_prev, waveform_last_color_primary, waveform_peak_scaled_last_primary,
                        waveform_shift_accum_primary, waveform_last_frame_ms_primary);
  } else if (mode == LIGHT_MODE_WAVEFORM_HYBRID) {
    memcpy(leds_16, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_waveform_hybrid(leds_16_prev, waveform_hybrid_last_color_primary, waveform_hybrid_peak_scaled_last_primary,
                               waveform_hybrid_shift_accum_primary, waveform_hybrid_last_frame_ms_primary);
  } else if (mode == LIGHT_MODE_VU_DOT) {
    light_mode_vu_dot(effect_state_primary);   // probe renders primary only
  } else if (mode == LIGHT_MODE_KALEIDOSCOPE) {
    light_mode_kaleidoscope(effect_state_primary);   // probe renders primary only
  } else if (mode == LIGHT_MODE_QUANTUM_COLLAPSE) {
    light_mode_quantum_collapse();   // mode 6 — non-deterministic; marked nondet=1, NOT Tier A
  } else if (mode == LIGHT_MODE_AURORA) {
    light_mode_aurora(leds_16_prev);
  } else if (mode == LIGHT_MODE_COMET) {
    memcpy(leds_16, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_comet(effect_state_primary);
    memcpy(leds_16_prev, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_SPECTRUM_RIVER) {
    light_mode_spectrum_river(leds_16_prev);
  } else if (mode == LIGHT_MODE_SPECTRUM_RIVER_V2) {
    light_mode_spectrum_river_v2(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_EMBER) {
    light_mode_ember(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_EMBER_V2) {
    light_mode_ember_v2(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_WAVEFORM_TEMPO) {
    memcpy(leds_16, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_waveform_tempo(effect_state_primary);
    memcpy(leds_16_prev, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_TEMPO_RIVER) {
    light_mode_tempo_river(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_TEMPO_COMET) {
    memcpy(leds_16, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_tempo_comet(effect_state_primary);
    memcpy(leds_16_prev, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_DENSE_FORGE) {
    light_mode_dense_forge(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_SNAPWAVE) {
    light_mode_snapwave(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_PULSE_PRISM) {
    light_mode_pulse_prism(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_DENSE_FORGE_CHORD) {
    light_mode_dense_forge_chord(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_CHROMA_CONSTELLATION) {
    light_mode_chroma_constellation(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_PERCUSSION_BURST) {
    light_mode_percussion_burst(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_TEMPO_COMET_ANTICIPATE) {
    memcpy(leds_16, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_tempo_comet_anticipate(effect_state_primary);
    memcpy(leds_16_prev, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  } else if (mode == LIGHT_MODE_RIVER_SURGE) {
    light_mode_river_surge(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_TEMPO_RIVER_WALK) {
    light_mode_tempo_river_walk(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_BEAT_PULSE) {
    light_mode_beat_pulse(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_BLOOM_BT) {
    light_mode_bloom_bt(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_WAVEFORM_HYBRID_K1) {
    light_mode_waveform_hybrid_k1(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_MOIRE_CATHEDRAL) {
    light_mode_moire_cathedral(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_CANNONADE) {
    light_mode_cannonade(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_SHOCKWAVE) {
    light_mode_shockwave(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_IRIS) {
    light_mode_iris(leds_16_prev, effect_state_primary);
  } else if (mode == LIGHT_MODE_MELODIC_BLOOM) {
    light_mode_melodic_bloom(leds_16_prev, effect_state_primary);
  }

  energy = vp_probe_energy(leds_16);
  return vp_probe_hash_leds(leds_16);
}

inline uint32_t vp_probe_render_hash(uint8_t mode, bool palette_mode, float chroma, float saturation, SQ15x16 hue_offset, uint32_t& energy) {
  vp_render_secondary_channel = false;
  vp_probe_seed_inputs();
  vp_probe_prepare_render(palette_mode, chroma, saturation, hue_offset);

  return vp_probe_dispatch_and_hash(mode, energy);
}

inline void vp_probe_print_mode(uint8_t mode) {
  uint32_t pal_energy_a = 0;
  uint32_t pal_energy_b = 0;
  uint32_t manual_energy_a = 0;
  uint32_t manual_energy_b = 0;
  uint32_t pal_a = vp_probe_render_hash(mode, true, 0.20f, 0.25f, SQ15x16(0.00f), pal_energy_a);
  uint32_t pal_b = vp_probe_render_hash(mode, true, 1.00f, 1.00f, SQ15x16(0.37f), pal_energy_b);
  uint32_t manual_a = vp_probe_render_hash(mode, false, 0.20f, 0.25f, SQ15x16(0.00f), manual_energy_a);
  uint32_t manual_b = vp_probe_render_hash(mode, false, 0.70f, 1.00f, SQ15x16(0.37f), manual_energy_b);

  USBSerial.print("VPO,ver=1,mode=");
  USBSerial.print(mode);
  USBSerial.print(",name=");
  USBSerial.print(mode_names + (mode * 32));
  USBSerial.print(",pal_a=");
  USBSerial.print(pal_a, HEX);
  USBSerial.print(",pal_b=");
  USBSerial.print(pal_b, HEX);
  USBSerial.print(",manual_a=");
  USBSerial.print(manual_a, HEX);
  USBSerial.print(",manual_b=");
  USBSerial.print(manual_b, HEX);
  USBSerial.print(",pal_energy=");
  USBSerial.print(pal_energy_a);
  USBSerial.print("/");
  USBSerial.print(pal_energy_b);
  USBSerial.print(",manual_energy=");
  USBSerial.print(manual_energy_a);
  USBSerial.print("/");
  USBSerial.print(manual_energy_b);
  USBSerial.print(",palette_stable=");
  USBSerial.print(pal_a == pal_b ? 1 : 0);
  USBSerial.print(",manual_responsive=");
  USBSerial.print(manual_a != manual_b ? 1 : 0);
  // nondet=1 flags a non-deterministic mode (quantum_collapse, mode 6): emitted for
  // completeness but excluded from Tier A bit-identity by the diff scripts.
  USBSerial.print(",nondet=");
  USBSerial.println(mode == LIGHT_MODE_QUANTUM_COLLAPSE ? 1 : 0);
}

inline void vp_run_output_probe() {
  bool saved_halt = led_thread_halt;
  led_thread_halt = true;
  delay(10);

  conf saved_config = CONFIG;
  bool saved_secondary_render = vp_render_secondary_channel;
  SQ15x16 saved_hue_position = hue_position;
  SQ15x16 saved_hue_shifting_mix = hue_shifting_mix;
  SQ15x16 saved_chroma_val = chroma_val;
  bool saved_chromatic_mode = chromatic_mode;
  float saved_waveform_peak_scaled = waveform_peak_scaled;
  float saved_max_waveform_val_raw = max_waveform_val_raw;
  SQ15x16 saved_audio_vu = audio_vu_level_average;
  CRGB16 saved_waveform_fast_last = waveform_fast_last_color_primary;
  CRGB16 saved_waveform_last = waveform_last_color_primary;
  CRGB16 saved_waveform_hybrid_last = waveform_hybrid_last_color_primary;
  float saved_waveform_fast_peak_last = waveform_fast_peak_scaled_last_primary;
  float saved_waveform_peak_last = waveform_peak_scaled_last_primary;
  float saved_waveform_hybrid_peak_last = waveform_hybrid_peak_scaled_last_primary;
  float saved_waveform_shift_accum = waveform_shift_accum_primary;
  float saved_waveform_hybrid_shift_accum = waveform_hybrid_shift_accum_primary;
  uint32_t saved_waveform_last_frame = waveform_last_frame_ms_primary;
  uint32_t saved_waveform_hybrid_last_frame = waveform_hybrid_last_frame_ms_primary;
  SQ15x16 saved_vu_level_smooth = vu_level_smooth_primary;
  SQ15x16 saved_vu_max_level = vu_max_level_primary;

  memcpy(leds_16_temp, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memcpy(leds_16_fx, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
  static DOT saved_dots[MAX_DOTS];
  memcpy(saved_dots, dots, sizeof(DOT) * MAX_DOTS);

  tx_begin(false);
  USBSerial.println("VPO,ver=1,event=start");
  vp_probe_print_mode(LIGHT_MODE_GDFT);
  vp_probe_print_mode(LIGHT_MODE_GDFT_CHROMAGRAM);
  vp_probe_print_mode(LIGHT_MODE_GDFT_CHROMAGRAM_DOTS);
  vp_probe_print_mode(LIGHT_MODE_BLOOM);
  vp_probe_print_mode(LIGHT_MODE_BLOOM_FAST);
  vp_probe_print_mode(LIGHT_MODE_VU);
  vp_probe_print_mode(LIGHT_MODE_WAVEFORM_FAST);
  vp_probe_print_mode(LIGHT_MODE_WAVEFORM);
  vp_probe_print_mode(LIGHT_MODE_WAVEFORM_HYBRID);
  vp_probe_print_mode(LIGHT_MODE_VU_DOT);
  vp_probe_print_mode(LIGHT_MODE_KALEIDOSCOPE);
  vp_probe_print_mode(LIGHT_MODE_QUANTUM_COLLAPSE);  // mode 6 — nondet=1; Tier B/smoke only, not a Tier A hash
  vp_probe_print_mode(LIGHT_MODE_AURORA);
  vp_probe_print_mode(LIGHT_MODE_COMET);
  vp_probe_print_mode(LIGHT_MODE_SPECTRUM_RIVER);
  vp_probe_print_mode(LIGHT_MODE_SPECTRUM_RIVER_V2);
  vp_probe_print_mode(LIGHT_MODE_EMBER);
  vp_probe_print_mode(LIGHT_MODE_EMBER_V2);
  vp_probe_print_mode(LIGHT_MODE_WAVEFORM_TEMPO);
  vp_probe_print_mode(LIGHT_MODE_TEMPO_RIVER);
  vp_probe_print_mode(LIGHT_MODE_TEMPO_COMET);
  vp_probe_print_mode(LIGHT_MODE_DENSE_FORGE);
  vp_probe_print_mode(LIGHT_MODE_SNAPWAVE);
  vp_probe_print_mode(LIGHT_MODE_PULSE_PRISM);
  vp_probe_print_mode(LIGHT_MODE_DENSE_FORGE_CHORD);
  vp_probe_print_mode(LIGHT_MODE_CHROMA_CONSTELLATION);
  vp_probe_print_mode(LIGHT_MODE_PERCUSSION_BURST);
  vp_probe_print_mode(LIGHT_MODE_TEMPO_COMET_ANTICIPATE);
  vp_probe_print_mode(LIGHT_MODE_RIVER_SURGE);
  vp_probe_print_mode(LIGHT_MODE_TEMPO_RIVER_WALK);
  vp_probe_print_mode(LIGHT_MODE_BEAT_PULSE);
  vp_probe_print_mode(LIGHT_MODE_BLOOM_BT);
  vp_probe_print_mode(LIGHT_MODE_WAVEFORM_HYBRID_K1);
  vp_probe_print_mode(LIGHT_MODE_MOIRE_CATHEDRAL);
  vp_probe_print_mode(LIGHT_MODE_CANNONADE);
  vp_probe_print_mode(LIGHT_MODE_SHOCKWAVE);
  vp_probe_print_mode(LIGHT_MODE_IRIS);
  vp_probe_print_mode(LIGHT_MODE_MELODIC_BLOOM);
  USBSerial.println("VPO,ver=1,event=end");
  tx_end(false);

  memcpy(leds_16, leds_16_temp, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memcpy(leds_16_prev, leds_16_fx, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memcpy(dots, saved_dots, sizeof(DOT) * MAX_DOTS);
  CONFIG = saved_config;
  vp_render_secondary_channel = saved_secondary_render;
  hue_position = saved_hue_position;
  hue_shifting_mix = saved_hue_shifting_mix;
  chroma_val = saved_chroma_val;
  chromatic_mode = saved_chromatic_mode;
  waveform_peak_scaled = saved_waveform_peak_scaled;
  max_waveform_val_raw = saved_max_waveform_val_raw;
  audio_vu_level_average = saved_audio_vu;
  waveform_fast_last_color_primary = saved_waveform_fast_last;
  waveform_last_color_primary = saved_waveform_last;
  waveform_hybrid_last_color_primary = saved_waveform_hybrid_last;
  waveform_fast_peak_scaled_last_primary = saved_waveform_fast_peak_last;
  waveform_peak_scaled_last_primary = saved_waveform_peak_last;
  waveform_hybrid_peak_scaled_last_primary = saved_waveform_hybrid_peak_last;
  waveform_shift_accum_primary = saved_waveform_shift_accum;
  waveform_hybrid_shift_accum_primary = saved_waveform_hybrid_shift_accum;
  waveform_last_frame_ms_primary = saved_waveform_last_frame;
  waveform_hybrid_last_frame_ms_primary = saved_waveform_hybrid_last_frame;
  vu_level_smooth_primary = saved_vu_level_smooth;
  vu_max_level_primary = saved_vu_max_level;
  led_thread_halt = saved_halt;
}

// ITEM 16 — single-line secondary/dual-channel state dump (tag VPS). Reports the
// active primary/secondary mode+palette selection, which channel is rendering, the
// RenderParams stack depth/source, and the per-channel effect state. Harness only
// (called from gated vp_status). Emitted between an existing tx context.
inline void vp_print_secondary_state() {
  USBSerial.print("VPS,ver=1,prim_mode=");
  USBSerial.print(CONFIG.LIGHTSHOW_MODE);
  USBSerial.print(",prim_name=");
  USBSerial.print(mode_names + (CONFIG.LIGHTSHOW_MODE * 32));
  USBSerial.print(",sec_mode=");
  USBSerial.print(SECONDARY_LIGHTSHOW_MODE);
  USBSerial.print(",sec_name=");
  USBSerial.print(mode_names + (SECONDARY_LIGHTSHOW_MODE * 32));
  USBSerial.print(",prim_pal=");
  USBSerial.print(CONFIG.PALETTE_INDEX);
  USBSerial.print(",sec_pal=");
  USBSerial.print(SECONDARY_PALETTE_INDEX);
  USBSerial.print(",prim_pal_en=");
  USBSerial.print(CONFIG.PALETTE_MODE_ENABLED ? 1 : 0);
  USBSerial.print(",sec_pal_en=");
  USBSerial.print(SECONDARY_PALETTE_MODE_ENABLED ? 1 : 0);
  USBSerial.print(",active_chan=");
  USBSerial.print(vp_render_secondary_channel ? "secondary" : "primary");

  int rp_depth = active_render_params_depth();
  USBSerial.print(",rp_depth=");
  USBSerial.print(rp_depth);
  USBSerial.print(",rp_source=");
  if (rp_depth < 0) {
    USBSerial.print("live_config");
  } else if (rp_depth == 0) {
    USBSerial.print("stack:primary");
  } else {
    USBSerial.print("stack:secondary");
  }

  USBSerial.print(",fx_p_max=");
  USBSerial.print(float(effect_state_primary.vu_dot_max_level), 4);
  USBSerial.print(",fx_p_kal=");
  USBSerial.print(effect_state_primary.kal_pos_r, 4);
  USBSerial.print(",fx_s_max=");
  USBSerial.print(float(effect_state_secondary.vu_dot_max_level), 4);
  USBSerial.print(",fx_s_kal=");
  USBSerial.println(effect_state_secondary.kal_pos_r, 4);
}

// ITEM 17 — secondary-channel BLEED PROBE (tag VPB). Proves the RenderParams core:
// rendering a *different* secondary mode/params after a primary render must (a) leave
// global CONFIG unchanged (no mutation), and (b) produce a different frame hash. Mirrors
// vp_run_output_probe's halt/snapshot/restore frame. Harness only (gated caller).
inline void vp_run_secondary_bleed_probe() {
  bool saved_halt = led_thread_halt;
  led_thread_halt = true;
  delay(10);

  // FULL snapshot for restore (mirrors vp_run_output_probe exactly).
  conf saved_config = CONFIG;
  bool saved_secondary_render = vp_render_secondary_channel;
  SQ15x16 saved_hue_position = hue_position;
  SQ15x16 saved_hue_shifting_mix = hue_shifting_mix;
  SQ15x16 saved_chroma_val = chroma_val;
  bool saved_chromatic_mode = chromatic_mode;
  float saved_waveform_peak_scaled = waveform_peak_scaled;
  float saved_max_waveform_val_raw = max_waveform_val_raw;
  SQ15x16 saved_audio_vu = audio_vu_level_average;
  CRGB16 saved_waveform_fast_last = waveform_fast_last_color_primary;
  CRGB16 saved_waveform_last = waveform_last_color_primary;
  CRGB16 saved_waveform_hybrid_last = waveform_hybrid_last_color_primary;
  float saved_waveform_fast_peak_last = waveform_fast_peak_scaled_last_primary;
  float saved_waveform_peak_last = waveform_peak_scaled_last_primary;
  float saved_waveform_hybrid_peak_last = waveform_hybrid_peak_scaled_last_primary;
  float saved_waveform_shift_accum = waveform_shift_accum_primary;
  float saved_waveform_hybrid_shift_accum = waveform_hybrid_shift_accum_primary;
  uint32_t saved_waveform_last_frame = waveform_last_frame_ms_primary;
  uint32_t saved_waveform_hybrid_last_frame = waveform_hybrid_last_frame_ms_primary;
  SQ15x16 saved_vu_level_smooth = vu_level_smooth_primary;
  SQ15x16 saved_vu_max_level = vu_max_level_primary;

  memcpy(leds_16_temp, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memcpy(leds_16_fx, leds_16_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
  static DOT saved_dots[MAX_DOTS];
  memcpy(saved_dots, dots, sizeof(DOT) * MAX_DOTS);

  // Two distinct, deterministic modes exercising the commit-2 per-channel state.
  const uint8_t X = LIGHT_MODE_VU_DOT;
  const uint8_t Y = LIGHT_MODE_KALEIDOSCOPE;

  tx_begin(false);
  USBSerial.println("VPB,ver=1,event=start");

  // --- Primary render (palette off, deterministic args). vp_probe_render_hash()
  // calls vp_probe_seed_inputs() + vp_probe_prepare_render() which resets the primary
  // statics + effect_state_primary. Also zero effect_state_secondary up front so the
  // secondary hash below is reproducible (prepare_render only touches primary).
  effect_state_secondary.vu_dot_pos_last = 0.0;
  effect_state_secondary.vu_dot_audio_level_smooth = 0.0;
  effect_state_secondary.vu_dot_max_level = 0.01;
  effect_state_secondary.kal_pos_r = 0.0f;
  effect_state_secondary.kal_pos_g = 0.0f;
  effect_state_secondary.kal_pos_b = 0.0f;
  effect_state_secondary.kal_brightness_low = 0.0;
  effect_state_secondary.kal_brightness_mid = 0.0;
  effect_state_secondary.kal_brightness_high = 0.0;

  vp_render_secondary_channel = false;
  uint32_t energy_prim = 0;
  uint32_t hash_primary = vp_probe_render_hash(X, false, 0.20f, 0.25f, SQ15x16(0.00f), energy_prim);

  // Oracle: capture CONFIG after the primary render — the secondary render below
  // must NOT mutate it (that is the whole point of the RenderParams core).
  conf cfg_after_primary = CONFIG;

  // --- Secondary render via a deterministic pushed RenderParams. Deliberately a
  // different mode AND different chroma/sat so the frame differs from primary.
  // Do NOT call vp_probe_prepare_render here — it would reset the channel flag/CONFIG.
  RenderParams sp = build_primary_render_params();
  sp.LIGHTSHOW_MODE = Y;
  sp.CHROMA = 0.70f;
  sp.SATURATION = 1.00f;
  push_render_params(&sp);
  vp_render_secondary_channel = true;
  uint32_t energy_sec = 0;
  uint32_t hash_secondary = vp_probe_dispatch_and_hash(Y, energy_sec);
  pop_render_params();
  vp_render_secondary_channel = false;

  bool cfg_unchanged = (memcmp(&CONFIG, &cfg_after_primary, sizeof(conf)) == 0);
  bool hashes_differ = (hash_primary != hash_secondary);
  bool pass = cfg_unchanged && hashes_differ;

  USBSerial.print("VPB,ver=1,prim_mode=");
  USBSerial.print(X);
  USBSerial.print(",sec_mode=");
  USBSerial.print(Y);
  USBSerial.print(",hash_prim=");
  USBSerial.print(hash_primary, HEX);
  USBSerial.print(",hash_sec=");
  USBSerial.print(hash_secondary, HEX);
  USBSerial.print(",hashes_differ=");
  USBSerial.print(hashes_differ ? 1 : 0);
  USBSerial.print(",cfg_unchanged=");
  USBSerial.print(cfg_unchanged ? 1 : 0);
  USBSerial.print(",energy_prim=");
  USBSerial.print(energy_prim);
  USBSerial.print(",energy_sec=");
  USBSerial.print(energy_sec);
  USBSerial.print(",result=");
  USBSerial.println(pass ? "PASS" : "FAIL");

  USBSerial.println("VPB,ver=1,event=end");
  tx_end(false);

  // Restore the full snapshot.
  memcpy(leds_16, leds_16_temp, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memcpy(leds_16_prev, leds_16_fx, sizeof(CRGB16) * NATIVE_RESOLUTION);
  memcpy(dots, saved_dots, sizeof(DOT) * MAX_DOTS);
  CONFIG = saved_config;
  vp_render_secondary_channel = saved_secondary_render;
  hue_position = saved_hue_position;
  hue_shifting_mix = saved_hue_shifting_mix;
  chroma_val = saved_chroma_val;
  chromatic_mode = saved_chromatic_mode;
  waveform_peak_scaled = saved_waveform_peak_scaled;
  max_waveform_val_raw = saved_max_waveform_val_raw;
  audio_vu_level_average = saved_audio_vu;
  waveform_fast_last_color_primary = saved_waveform_fast_last;
  waveform_last_color_primary = saved_waveform_last;
  waveform_hybrid_last_color_primary = saved_waveform_hybrid_last;
  waveform_fast_peak_scaled_last_primary = saved_waveform_fast_peak_last;
  waveform_peak_scaled_last_primary = saved_waveform_peak_last;
  waveform_hybrid_peak_scaled_last_primary = saved_waveform_hybrid_peak_last;
  waveform_shift_accum_primary = saved_waveform_shift_accum;
  waveform_hybrid_shift_accum_primary = saved_waveform_hybrid_shift_accum;
  waveform_last_frame_ms_primary = saved_waveform_last_frame;
  waveform_hybrid_last_frame_ms_primary = saved_waveform_hybrid_last_frame;
  vu_level_smooth_primary = saved_vu_level_smooth;
  vu_max_level_primary = saved_vu_max_level;
  led_thread_halt = saved_halt;
}
