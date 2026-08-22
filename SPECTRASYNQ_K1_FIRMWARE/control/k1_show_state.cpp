// k1_show_state.cpp
// ============================================================================
// LittleFS show-state blob: primary + secondary presets, EdgeMixer config, and
// ENABLE_SECONDARY_LEDS. Explicit save only ('S' / :save_show); boot load is a
// soft no-op on missing/corrupt files.
// ============================================================================

#include "k1_show_state.h"

#include <Arduino.h>
#include <string.h>

#include <FS.h>
#include <LittleFS.h>

#include "globals.h"  // ENABLE_SECONDARY_LEDS, CONFIG / SECONDARY_* via capture
#include "Palettes.h" // gGradientPaletteCount
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h"
#endif

void save_config();  // persistence/bridge_fs.h (single-TU .ino header)

namespace {

// Same reflected CRC-32 as bridge_fs_config_codec.h (table-less).
uint32_t show_crc32(const uint8_t* data, size_t len) {
  uint32_t crc = 0xFFFFFFFFUL;
  for (size_t i = 0; i < len; i++) {
    crc ^= (uint32_t)data[i];
    for (int b = 0; b < 8; b++) {
      uint32_t mask = (uint32_t)(-(int32_t)(crc & 1U));
      crc = (crc >> 1) ^ (0xEDB88320UL & mask);
    }
  }
  return crc ^ 0xFFFFFFFFUL;
}

bool write_bytes(uint8_t*& cursor, size_t& remaining, const void* src, size_t n) {
  if (remaining < n) {
    return false;
  }
  memcpy(cursor, src, n);
  cursor += n;
  remaining -= n;
  return true;
}

bool read_bytes(const uint8_t*& cursor, size_t& remaining, void* dst, size_t n) {
  if (remaining < n) {
    return false;
  }
  memcpy(dst, cursor, n);
  cursor += n;
  remaining -= n;
  return true;
}

bool write_preset(uint8_t*& cursor, size_t& remaining, const K1ChannelPreset& p) {
  uint8_t mirror = p.mirror_enabled ? 1 : 0;
  uint8_t incand_mode = p.incandescent_mode ? 1 : 0;
  uint8_t base_coat = p.base_coat ? 1 : 0;
  uint8_t reverse = p.reverse_order ? 1 : 0;
  uint8_t auto_shift = p.auto_color_shift ? 1 : 0;
  uint8_t palette_mode = p.palette_mode_enabled ? 1 : 0;
  bool ok = true;
  ok = ok && write_bytes(cursor, remaining, &p.lightshow_mode, sizeof(p.lightshow_mode));
  ok = ok && write_bytes(cursor, remaining, &mirror, sizeof(mirror));
  ok = ok && write_bytes(cursor, remaining, &p.photons, sizeof(p.photons));
  ok = ok && write_bytes(cursor, remaining, &p.chroma, sizeof(p.chroma));
  ok = ok && write_bytes(cursor, remaining, &p.mood, sizeof(p.mood));
  ok = ok && write_bytes(cursor, remaining, &p.saturation, sizeof(p.saturation));
  ok = ok && write_bytes(cursor, remaining, &p.prism_count, sizeof(p.prism_count));
  ok = ok && write_bytes(cursor, remaining, &p.incandescent_filter, sizeof(p.incandescent_filter));
  ok = ok && write_bytes(cursor, remaining, &incand_mode, sizeof(incand_mode));
  ok = ok && write_bytes(cursor, remaining, &base_coat, sizeof(base_coat));
  ok = ok && write_bytes(cursor, remaining, &reverse, sizeof(reverse));
  ok = ok && write_bytes(cursor, remaining, &auto_shift, sizeof(auto_shift));
  ok = ok && write_bytes(cursor, remaining, &p.base_coat_intensity, sizeof(p.base_coat_intensity));
  ok = ok && write_bytes(cursor, remaining, &p.palette_index, sizeof(p.palette_index));
  ok = ok && write_bytes(cursor, remaining, &palette_mode, sizeof(palette_mode));
  return ok;
}

bool read_preset(const uint8_t*& cursor, size_t& remaining, K1ChannelPreset& p) {
  uint8_t mirror = 0, incand_mode = 0, base_coat = 0;
  uint8_t reverse = 0, auto_shift = 0, palette_mode = 0;
  bool ok = true;
  ok = ok && read_bytes(cursor, remaining, &p.lightshow_mode, sizeof(p.lightshow_mode));
  ok = ok && read_bytes(cursor, remaining, &mirror, sizeof(mirror));
  ok = ok && read_bytes(cursor, remaining, &p.photons, sizeof(p.photons));
  ok = ok && read_bytes(cursor, remaining, &p.chroma, sizeof(p.chroma));
  ok = ok && read_bytes(cursor, remaining, &p.mood, sizeof(p.mood));
  ok = ok && read_bytes(cursor, remaining, &p.saturation, sizeof(p.saturation));
  ok = ok && read_bytes(cursor, remaining, &p.prism_count, sizeof(p.prism_count));
  ok = ok && read_bytes(cursor, remaining, &p.incandescent_filter, sizeof(p.incandescent_filter));
  ok = ok && read_bytes(cursor, remaining, &incand_mode, sizeof(incand_mode));
  ok = ok && read_bytes(cursor, remaining, &base_coat, sizeof(base_coat));
  ok = ok && read_bytes(cursor, remaining, &reverse, sizeof(reverse));
  ok = ok && read_bytes(cursor, remaining, &auto_shift, sizeof(auto_shift));
  ok = ok && read_bytes(cursor, remaining, &p.base_coat_intensity, sizeof(p.base_coat_intensity));
  ok = ok && read_bytes(cursor, remaining, &p.palette_index, sizeof(p.palette_index));
  ok = ok && read_bytes(cursor, remaining, &palette_mode, sizeof(palette_mode));
  if (!ok) {
    return false;
  }
  p.mirror_enabled = (mirror != 0);
  p.incandescent_mode = (incand_mode != 0);
  p.base_coat = (base_coat != 0);
  p.reverse_order = (reverse != 0);
  p.auto_color_shift = (auto_shift != 0);
  p.palette_mode_enabled = (palette_mode != 0);
#ifdef K1_EFFECT_REGISTRY_V1
  p.lightshow_mode = k1::effects::framework::registry_sanitize_persisted(p.lightshow_mode);
#else
  p.lightshow_mode = light_mode_sanitize_persisted(p.lightshow_mode);
#endif
  if (p.palette_index >= gGradientPaletteCount) {
    p.palette_index = 0;
  }
  return true;
}

bool write_edge(uint8_t*& cursor, size_t& remaining, const K1EdgeMixerConfig& e) {
  uint8_t enabled = e.enabled ? 1 : 0;
  uint8_t mode = static_cast<uint8_t>(e.mode);
  uint8_t rotation = static_cast<uint8_t>(e.rotationSpace);
  uint8_t spatial = e.spatialUniform ? 1 : 0;
  uint8_t dual = static_cast<uint8_t>(e.dualEdge);
  bool ok = true;
  ok = ok && write_bytes(cursor, remaining, &enabled, sizeof(enabled));
  ok = ok && write_bytes(cursor, remaining, &mode, sizeof(mode));
  ok = ok && write_bytes(cursor, remaining, &e.strength, sizeof(e.strength));
  ok = ok && write_bytes(cursor, remaining, &e.spreadDegrees, sizeof(e.spreadDegrees));
  ok = ok && write_bytes(cursor, remaining, &rotation, sizeof(rotation));
  ok = ok && write_bytes(cursor, remaining, &spatial, sizeof(spatial));
  ok = ok && write_bytes(cursor, remaining, &dual, sizeof(dual));
  return ok;
}

bool read_edge(const uint8_t*& cursor, size_t& remaining, K1EdgeMixerConfig& e) {
  uint8_t enabled = 0, mode = 0, rotation = 0, spatial = 0, dual = 0;
  bool ok = true;
  ok = ok && read_bytes(cursor, remaining, &enabled, sizeof(enabled));
  ok = ok && read_bytes(cursor, remaining, &mode, sizeof(mode));
  ok = ok && read_bytes(cursor, remaining, &e.strength, sizeof(e.strength));
  ok = ok && read_bytes(cursor, remaining, &e.spreadDegrees, sizeof(e.spreadDegrees));
  ok = ok && read_bytes(cursor, remaining, &rotation, sizeof(rotation));
  ok = ok && read_bytes(cursor, remaining, &spatial, sizeof(spatial));
  ok = ok && read_bytes(cursor, remaining, &dual, sizeof(dual));
  if (!ok) {
    return false;
  }
  e.enabled = (enabled != 0);
  e.mode = static_cast<K1EdgeMixerMode>(mode);
  e.rotationSpace = static_cast<K1EdgeMixerRotationSpace>(rotation);
  e.spatialUniform = (spatial != 0);
  e.dualEdge = static_cast<K1EdgeMixerDualEdge>(dual);
  return true;
}

}  // namespace

K1ShowState k1_show_state_capture_live() {
  K1ShowState state;
  state.primary = k1_queue_capture_live(false);
  state.secondary = k1_queue_capture_live(true);
  state.edge = k1_edgemixer_config();
  state.enable_secondary = ENABLE_SECONDARY_LEDS;
  return state;
}

void k1_show_state_apply(const K1ShowState& state) {
  k1_queue_apply_fields(false, state.primary);
  k1_queue_apply_fields(true, state.secondary);
  k1_edgemixer_set_config(state.edge);
  ENABLE_SECONDARY_LEDS = state.enable_secondary;
}

size_t k1_show_state_encode(const K1ShowState& state, uint8_t* out, size_t out_cap) {
  if (out == nullptr || out_cap < 16) {
    return 0;
  }
  uint8_t* cursor = out;
  size_t remaining = out_cap;
  uint32_t magic = K1_SHOW_STATE_MAGIC;
  uint16_t version = K1_SHOW_STATE_VERSION;
  uint16_t reserved = 0;
  if (!write_bytes(cursor, remaining, &magic, sizeof(magic)) ||
      !write_bytes(cursor, remaining, &version, sizeof(version)) ||
      !write_bytes(cursor, remaining, &reserved, sizeof(reserved))) {
    return 0;
  }
  uint8_t* payload_start = cursor;
  uint8_t enable = state.enable_secondary ? 1 : 0;
  if (!write_preset(cursor, remaining, state.primary) ||
      !write_preset(cursor, remaining, state.secondary) ||
      !write_edge(cursor, remaining, state.edge) ||
      !write_bytes(cursor, remaining, &enable, sizeof(enable))) {
    return 0;
  }
  const size_t payload_len = static_cast<size_t>(cursor - payload_start);
  const uint32_t crc = show_crc32(payload_start, payload_len);
  if (!write_bytes(cursor, remaining, &crc, sizeof(crc))) {
    return 0;
  }
  return static_cast<size_t>(cursor - out);
}

bool k1_show_state_decode(const uint8_t* data, size_t len, K1ShowState* out) {
  if (data == nullptr || out == nullptr || len < 16) {
    return false;
  }
  const uint8_t* cursor = data;
  size_t remaining = len;
  uint32_t magic = 0;
  uint16_t version = 0;
  uint16_t reserved = 0;
  if (!read_bytes(cursor, remaining, &magic, sizeof(magic)) ||
      !read_bytes(cursor, remaining, &version, sizeof(version)) ||
      !read_bytes(cursor, remaining, &reserved, sizeof(reserved))) {
    return false;
  }
  if (magic != K1_SHOW_STATE_MAGIC || version != K1_SHOW_STATE_VERSION) {
    return false;
  }
  (void)reserved;
  const uint8_t* payload_start = cursor;
  K1ShowState state = {};
  uint8_t enable = 0;
  if (!read_preset(cursor, remaining, state.primary) ||
      !read_preset(cursor, remaining, state.secondary) ||
      !read_edge(cursor, remaining, state.edge) ||
      !read_bytes(cursor, remaining, &enable, sizeof(enable))) {
    return false;
  }
  const size_t payload_len = static_cast<size_t>(cursor - payload_start);
  uint32_t crc = 0;
  if (!read_bytes(cursor, remaining, &crc, sizeof(crc))) {
    return false;
  }
  if (show_crc32(payload_start, payload_len) != crc) {
    return false;
  }
  // Trailing bytes are ignored (forward-compat padding).
  state.enable_secondary = (enable != 0);
  *out = state;
  return true;
}

bool k1_show_state_save() {
  K1ShowState state = k1_show_state_capture_live();
  uint8_t buf[512];
  const size_t n = k1_show_state_encode(state, buf, sizeof(buf));
  if (n == 0) {
    return false;
  }
  // G7B: park Core 1 across this LittleFS write. save_config() takes its own
  // lock/unlock pair — release before calling it (lock_leds is not recursive).
  lock_leds();
  File file = LittleFS.open(K1_SHOW_STATE_FILE, FILE_WRITE);
  if (!file) {
    unlock_leds();
    return false;
  }
  const size_t wrote = file.write(buf, n);
  file.close();
  unlock_leds();
  if (wrote != n) {
    return false;
  }
  // Immediate primary CONFIG flush (not delayed) so reboot sees both blobs.
  save_config();
  return true;
}

bool k1_show_state_load() {
  lock_leds();
  File file = LittleFS.open(K1_SHOW_STATE_FILE, FILE_READ);
  if (!file) {
    unlock_leds();
    return false;
  }
  uint8_t buf[512];
  const size_t n = file.read(buf, sizeof(buf));
  file.close();
  unlock_leds();
  if (n == 0) {
    return false;
  }
  K1ShowState state = {};
  if (!k1_show_state_decode(buf, n, &state)) {
    return false;
  }
  k1_show_state_apply(state);
  return true;
}
