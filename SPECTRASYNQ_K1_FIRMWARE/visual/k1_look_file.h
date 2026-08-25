#pragma once

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include "k1_look.h"
#include "bridge_fs_config_codec.h"

// K1LT look file (Phase B). Magic 'K1LT' little-endian 0x4B314C54.
// FS-free parse so host tests can lock the ABI. LittleFS I/O is Arduino-only.

#define K1LT_MAGIC 0x4B314C54UL
#define K1LT_VERSION 1U
#define K1LT_HEADER_SIZE 16U

struct K1LTHeader {
  uint32_t magic;
  uint16_t version;
  uint8_t type;
  uint8_t flags;
  uint16_t node_n;
  uint16_t reserved;
  uint32_t payload_bytes;
};

struct K1LookParsed {
  uint8_t type;
  uint8_t flags;
  uint16_t node_n;
  uint32_t payload_bytes;
  const uint8_t *payload;
};

static inline bool k1_look_parse_k1lt(const uint8_t *data, size_t len, K1LookParsed *out) {
  if (out == nullptr || data == nullptr) {
    return false;
  }
  memset(out, 0, sizeof(*out));
  if (len < K1LT_HEADER_SIZE + 4U) {
    return false;
  }
  K1LTHeader h;
  memcpy(&h, data, sizeof(h));
  if (h.magic != K1LT_MAGIC) {
    return false;
  }
  if (h.version != K1LT_VERSION) {
    return false;
  }
  if (h.type == K1_LOOK_IDENTITY || h.type == K1_LOOK_EMPTY) {
    return false;
  }
  if (h.type > K1_LOOK_SHAPER_CUBE) {
    return false;
  }
  if (len < K1LT_HEADER_SIZE + 4U + (size_t)h.payload_bytes) {
    return false;
  }
  const uint8_t *payload = data + K1LT_HEADER_SIZE;
  uint32_t crc_stamped;
  memcpy(&crc_stamped, payload + h.payload_bytes, 4);
  if (bridge_fs_crc32(payload, h.payload_bytes) != crc_stamped) {
    return false;
  }
  out->type = h.type;
  out->flags = h.flags;
  out->node_n = h.node_n;
  out->payload_bytes = h.payload_bytes;
  out->payload = payload;
  return true;
}

static inline bool k1_look_build_k1lt(uint8_t type, uint16_t node_n, const uint8_t *payload,
                                      uint32_t payload_bytes, uint8_t *out, size_t out_n,
                                      size_t *written) {
  if (type == K1_LOOK_IDENTITY || payload == nullptr || out == nullptr) {
    return false;
  }
  const size_t need = K1LT_HEADER_SIZE + (size_t)payload_bytes + 4U;
  if (out_n < need) {
    return false;
  }
  K1LTHeader h;
  h.magic = K1LT_MAGIC;
  h.version = K1LT_VERSION;
  h.type = type;
  h.flags = 0;
  h.node_n = node_n;
  h.reserved = 0;
  h.payload_bytes = payload_bytes;
  memcpy(out, &h, sizeof(h));
  memcpy(out + K1LT_HEADER_SIZE, payload, payload_bytes);
  const uint32_t crc = bridge_fs_crc32(payload, payload_bytes);
  memcpy(out + K1LT_HEADER_SIZE + payload_bytes, &crc, 4);
  if (written != nullptr) {
    *written = need;
  }
  return true;
}

#ifdef ARDUINO

#include <Arduino.h>
#include <LittleFS.h>
#include <esp_heap_caps.h>

#ifndef K1_LOOK_RX_MAX
#define K1_LOOK_RX_MAX 32768
#endif

inline uint8_t *k1_look_slot_ram[16] = {};
inline size_t k1_look_slot_ram_n[16] = {};
inline uint8_t k1_look_rx_slot = 0;
inline uint32_t k1_look_rx_need = 0;
inline uint32_t k1_look_rx_got = 0;
inline uint8_t *k1_look_rx_buf = nullptr;

#ifndef K1_LOOK_FS_MIN_INTERNAL_BLOCK
#define K1_LOOK_FS_MIN_INTERNAL_BLOCK 8192
#endif

static inline bool k1_look_heap_ok(const char *who) {
  const size_t largest = heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL);
  if (largest >= (size_t)K1_LOOK_FS_MIN_INTERNAL_BLOCK) {
    return true;
  }
  USBSerial.print("[fs] SKIP ");
  USBSerial.print(who);
  USBSerial.println(": internal heap too low for LittleFS open");
  return false;
}

static inline void k1_look_slot_path(uint8_t slot, char *out, size_t n) {
  if (out == nullptr || n < 14) {
    return;
  }
  snprintf(out, n, "/look/%02u.klut", (unsigned)slot);
}

static inline void k1_look_free_slot_ram(uint8_t slot) {
  if (slot > 15) {
    return;
  }
  if (k1_look_slot_ram[slot] != nullptr) {
    heap_caps_free(k1_look_slot_ram[slot]);
    k1_look_slot_ram[slot] = nullptr;
    k1_look_slot_ram_n[slot] = 0;
  }
}

// Core 1 applies k1_look_table[slot] every pack frame. EMPTY the table
// BEFORE freeing slot RAM so dyn_rgb / cube pointers never dangle under
// the render path. Does not change k1_look_slot / k1_look_slot_sec —
// EMPTY apply is a no-op (identity) for the gap until reinstall.
static inline void k1_look_detach_slot_payload(uint8_t slot) {
  if (slot > 15) {
    return;
  }
  k1_look_table[slot].type = K1_LOOK_EMPTY;
  k1_look_table[slot].payload = nullptr;
  k1_look_free_slot_ram(slot);
}

static inline void k1_look_retire_slot(uint8_t slot) {
  if (slot > 15) {
    return;
  }
  if (k1_look_slot == slot) {
    k1_look_slot = 0;
  }
  if (k1_look_slot_sec == slot) {
    k1_look_slot_sec = 255;
  }
  k1_look_detach_slot_payload(slot);
}

static inline bool k1_look_payload_installable(const K1LookParsed *live) {
  if (live == nullptr) {
    return false;
  }
  if (live->type == K1_LOOK_RGB_1D_256 && live->node_n == 256 &&
      live->payload_bytes >= (uint32_t)(256u * 2u * 4u)) {
    return true;
  }
  if (live->type == K1_LOOK_MATRIX_3X4 && live->payload_bytes >= 48) {
    return true;
  }
  if (live->type == K1_LOOK_CUBE_17 &&
      live->payload_bytes >= (17u * 17u * 17u * 3u * 2u)) {
    return true;
  }
  if (live->type == K1_LOOK_SHARED_1D_256) {
    return true;
  }
  return false;
}

static inline bool k1_look_install_parsed(uint8_t slot, const uint8_t *file_bytes, size_t file_len) {
  if (!k1_look_slot_loadable(slot)) {
    return false;
  }
  K1LookParsed parsed;
  if (!k1_look_parse_k1lt(file_bytes, file_len, &parsed)) {
    return false;
  }
  if (!k1_look_payload_installable(&parsed)) {
    return false;
  }
  uint8_t *copy = (uint8_t *)heap_caps_malloc(file_len, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (copy == nullptr) {
    copy = (uint8_t *)heap_caps_malloc(file_len, MALLOC_CAP_8BIT);
  }
  if (copy == nullptr) {
    return false;
  }
  memcpy(copy, file_bytes, file_len);
  K1LookParsed live;
  if (!k1_look_parse_k1lt(copy, file_len, &live) || !k1_look_payload_installable(&live)) {
    heap_caps_free(copy);
    return false;
  }
  // Validate succeeded — only now EMPTY the live table entry and free old RAM.
  k1_look_detach_slot_payload(slot);
  k1_look_slot_ram[slot] = copy;
  k1_look_slot_ram_n[slot] = file_len;
  if (live.type == K1_LOOK_RGB_1D_256) {
    static K1LookRgb1d dyn_rgb[16];
    const uint16_t *base = reinterpret_cast<const uint16_t *>(live.payload);
    dyn_rgb[slot].x = base;
    dyn_rgb[slot].r = base + 256;
    dyn_rgb[slot].g = base + 512;
    dyn_rgb[slot].b = base + 768;
    k1_look_table[slot].type = K1_LOOK_RGB_1D_256;
    k1_look_table[slot].payload = &dyn_rgb[slot];
    return true;
  }
  if (live.type == K1_LOOK_MATRIX_3X4) {
    k1_look_table[slot].type = K1_LOOK_MATRIX_3X4;
    k1_look_table[slot].payload = live.payload;
    return true;
  }
  if (live.type == K1_LOOK_CUBE_17) {
    static K1LookCube17 dyn_cube[16];
    dyn_cube[slot].rgb = reinterpret_cast<const uint16_t *>(live.payload);
    k1_look_table[slot].type = K1_LOOK_CUBE_17;
    k1_look_table[slot].payload = &dyn_cube[slot];
    return true;
  }
  // SHARED_1D_256
  k1_look_table[slot].type = K1_LOOK_SHARED_1D_256;
  k1_look_table[slot].payload = nullptr;
  return true;
}

static inline bool k1_look_fs_load(uint8_t slot) {
  if (!k1_look_slot_loadable(slot)) {
    return false;
  }
  if (!k1_look_heap_ok("look_load")) {
    return false;
  }
  char path[24];
  k1_look_slot_path(slot, path, sizeof(path));
  File file = LittleFS.open(path, FILE_READ);
  if (!file) {
    return false;
  }
  const size_t n = (size_t)file.size();
  if (n < (K1LT_HEADER_SIZE + 4U) || n > K1_LOOK_RX_MAX) {
    file.close();
    return false;
  }
  uint8_t *buf = (uint8_t *)heap_caps_malloc(n, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (buf == nullptr) {
    buf = (uint8_t *)heap_caps_malloc(n, MALLOC_CAP_8BIT);
  }
  if (buf == nullptr) {
    file.close();
    return false;
  }
  size_t got = 0;
  while (got < n) {
    int b = file.read();
    if (b < 0) {
      break;
    }
    buf[got++] = (uint8_t)b;
  }
  file.close();
  const bool ok = (got == n) && k1_look_install_parsed(slot, buf, n);
  heap_caps_free(buf);
  return ok;
}

static inline bool k1_look_fs_save(uint8_t slot, const uint8_t *bytes, size_t n) {
  if (!k1_look_slot_loadable(slot) || bytes == nullptr) {
    return false;
  }
  if (!k1_look_heap_ok("look_save")) {
    return false;
  }
  LittleFS.mkdir("/look");
  char path[24];
  k1_look_slot_path(slot, path, sizeof(path));
  File file = LittleFS.open(path, FILE_WRITE);
  if (!file) {
    return false;
  }
  const size_t wrote = file.write(bytes, n);
  file.close();
  return wrote == n;
}

static inline bool k1_look_fs_clear(uint8_t slot) {
  if (!k1_look_slot_loadable(slot)) {
    return false;
  }
  char path[24];
  k1_look_slot_path(slot, path, sizeof(path));
  LittleFS.remove(path);
  // Retarget + EMPTY before free — same Core-1 UAF gate as install.
  k1_look_retire_slot(slot);
  return true;
}

static inline bool k1_look_rx_arm(uint8_t slot, uint32_t nbytes) {
  if (!k1_look_slot_loadable(slot) || nbytes < (K1LT_HEADER_SIZE + 4U) ||
      nbytes > K1_LOOK_RX_MAX) {
    return false;
  }
  if (k1_look_rx_buf != nullptr) {
    heap_caps_free(k1_look_rx_buf);
    k1_look_rx_buf = nullptr;
  }
  k1_look_rx_buf = (uint8_t *)heap_caps_malloc(nbytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (k1_look_rx_buf == nullptr) {
    k1_look_rx_buf = (uint8_t *)heap_caps_malloc(nbytes, MALLOC_CAP_8BIT);
  }
  if (k1_look_rx_buf == nullptr) {
    return false;
  }
  k1_look_rx_slot = slot;
  k1_look_rx_need = nbytes;
  k1_look_rx_got = 0;
  return true;
}

static inline bool k1_look_rx_push(uint8_t byte) {
  if (k1_look_rx_buf == nullptr || k1_look_rx_got >= k1_look_rx_need) {
    return false;
  }
  k1_look_rx_buf[k1_look_rx_got++] = byte;
  if (k1_look_rx_got < k1_look_rx_need) {
    return true;
  }
  const bool ok = k1_look_install_parsed(k1_look_rx_slot, k1_look_rx_buf, k1_look_rx_need) &&
                  k1_look_fs_save(k1_look_rx_slot, k1_look_rx_buf, k1_look_rx_need);
  heap_caps_free(k1_look_rx_buf);
  k1_look_rx_buf = nullptr;
  k1_look_rx_need = 0;
  k1_look_rx_got = 0;
  return ok;
}

#endif  // ARDUINO
