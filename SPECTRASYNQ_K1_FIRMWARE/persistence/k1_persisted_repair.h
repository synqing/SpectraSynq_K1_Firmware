#pragma once
// ============================================================================
// k1_persisted_repair.h — repair non-finite floats at the saved-state adoption
// boundaries (Modernes C++ next phase, Stage C, 10 Nov 2026).
//
// Before e28dd927 several setters let NaN/Inf reach CONFIG and the per-channel
// presets, and a normal save wrote those bytes under a correct CRC. The loaders
// check format and integrity, then adopt raw values, so a CRC-valid old file can
// still carry NaN into live consumers. These helpers run where saved values are
// adopted — load_config(), k1_show_state_load() and the preset-slot file — and
// replace ONLY non-finite floats. Finite values, integers, booleans, schema,
// CRC handling and missing/corrupt-file behaviour are unchanged; no range is
// tightened. Recovery is RAM-only (no file write, delete or reboot here).
//
// The finite test reads the exponent bits, so it stays a real test under
// -ffast-math / -ffinite-math-only (an isfinite() there may fold to true).
// Templates keep this header free of firmware globals so the host tests use it
// with the real struct conf and K1ChannelPreset.
// ============================================================================

#include <stdint.h>
#include <string.h>

static inline bool k1_persist_float_finite(float v) {
  uint32_t bits;
  memcpy(&bits, &v, sizeof(bits));
  return (bits & 0x7F800000u) != 0x7F800000u;
}

// Replace a non-finite value with `fallback`. Returns 1 when it repaired.
static inline uint8_t k1_persist_repair_float(float &v, float fallback) {
  if (k1_persist_float_finite(v)) {
    return 0;
  }
  v = fallback;
  return 1;
}

// Every float in struct conf (system/config_types.h). Fallback: CONFIG_DEFAULTS.
template <typename Conf>
static inline uint8_t k1_config_repair_nonfinite(Conf &c, const Conf &defaults) {
  uint8_t n = 0;
  n += k1_persist_repair_float(c.PHOTONS, defaults.PHOTONS);
  n += k1_persist_repair_float(c.CHROMA, defaults.CHROMA);
  n += k1_persist_repair_float(c.MOOD, defaults.MOOD);
  n += k1_persist_repair_float(c.SQUARE_ITER, defaults.SQUARE_ITER);
  n += k1_persist_repair_float(c.SENSITIVITY, defaults.SENSITIVITY);
  n += k1_persist_repair_float(c.INCANDESCENT_FILTER, defaults.INCANDESCENT_FILTER);
  n += k1_persist_repair_float(c.BULB_OPACITY, defaults.BULB_OPACITY);
  n += k1_persist_repair_float(c.SATURATION, defaults.SATURATION);
  n += k1_persist_repair_float(c.PRISM_COUNT, defaults.PRISM_COUNT);
  n += k1_persist_repair_float(c.VU_LEVEL_FLOOR, defaults.VU_LEVEL_FLOOR);
  n += k1_persist_repair_float(c.BASE_COAT_INTENSITY, defaults.BASE_COAT_INTENSITY);
  return n;
}

// Every float in K1ChannelPreset (control/k1_effect_queue.h). Fallback: the
// channel's current live value (for the primary that is the already-repaired
// CONFIG; for the secondary, its boot value), so a bad overlay field leaves the
// channel as it was rather than inventing a new value.
template <typename Preset>
static inline uint8_t k1_preset_repair_nonfinite(Preset &p, const Preset &fallback) {
  uint8_t n = 0;
  n += k1_persist_repair_float(p.photons, fallback.photons);
  n += k1_persist_repair_float(p.chroma, fallback.chroma);
  n += k1_persist_repair_float(p.mood, fallback.mood);
  n += k1_persist_repair_float(p.saturation, fallback.saturation);
  n += k1_persist_repair_float(p.prism_count, fallback.prism_count);
  n += k1_persist_repair_float(p.incandescent_filter, fallback.incandescent_filter);
  n += k1_persist_repair_float(p.base_coat_intensity, fallback.base_coat_intensity);
  return n;
}
