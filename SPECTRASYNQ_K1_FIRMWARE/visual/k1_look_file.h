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
  // Written as a subtraction: on the 32-bit target HEADER + 4 + payload_bytes
  // can wrap for a hostile payload_bytes and pass, then the CRC reads past the
  // buffer.
  if ((size_t)h.payload_bytes > len - (K1LT_HEADER_SIZE + 4U)) {
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

#ifdef K1_LOOK_LIB_V1
// ---------------------------------------------------------------------------
// Loadable slots 8-15: storage ownership (Stage B, 10 Nov 2026).
//
// Writer side only: the serial/control loop, or boot before the render task
// exists. Every installed table is one allocation (K1LookBundle) holding its
// immutable descriptor, its payload view and a copy of the file bytes. A
// replacement or clear swaps k1_look_desc[slot] in one store and retires the
// old bundle; a retired bundle is freed only once no render reader can hold it
// (see the protocol in k1_look.h). Nothing here runs on the render path and no
// lock is held across allocation, file I/O or logging.
//
// Outcomes are explicit. A failed replacement (bad slot, malformed or
// unsupported file, allocation failure, retire list full) changes nothing: the
// old table stays published and owned. There is no pending request: when an
// install returns OK the new table is the published one.
#ifndef K1_LOOK_ALLOC
#ifdef ARDUINO
#include <esp_heap_caps.h>
static inline void *k1_look_alloc_default(size_t n) {
  void *p = heap_caps_malloc(n, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  return p != nullptr ? p : heap_caps_malloc(n, MALLOC_CAP_8BIT);
}
#define K1_LOOK_ALLOC(n) k1_look_alloc_default(n)
#define K1_LOOK_FREE(p) heap_caps_free(p)
#else
#include <stdlib.h>
#define K1_LOOK_ALLOC(n) malloc(n)
#define K1_LOOK_FREE(p) free(p)
#endif
#endif

// Optional bounded poll for render quiescence after a swap. Off by default:
// the writer runs on the core-0 loop that also acquires audio, so it does not
// spin; a bundle still held by a reader stays retired and the next look
// operation (or :look_status) frees it.
#ifndef K1_LOOK_RECLAIM_WAIT_US
#define K1_LOOK_RECLAIM_WAIT_US 0u
#endif
#ifndef K1_LOOK_NOW_US
#ifdef ARDUINO
#include <esp_timer.h>
#define K1_LOOK_NOW_US() ((uint32_t)esp_timer_get_time())
#else
#define K1_LOOK_NOW_US() 0u
#endif
#endif

#ifndef K1_LOOK_RETIRE_MAX
#define K1_LOOK_RETIRE_MAX 4
#endif

struct K1LookBundle {
  K1LookSlot desc;  // what k1_look_desc[slot] points at while installed
  union {
    K1LookRgb1d rgb;
    K1LookCube17 cube;
  } view;
  size_t file_len;
  uint8_t *file;  // inside this allocation, 8-byte aligned
};

enum K1LookResult : uint8_t {
  K1_LOOK_OK = 0,
  K1_LOOK_ERR_SLOT,         // not a loadable slot
  K1_LOOK_ERR_FILE,         // malformed, bad CRC or unsupported table
  K1_LOOK_ERR_NO_MEMORY,    // allocation failed; old table kept
  K1_LOOK_ERR_BUSY          // retire list full while a reader holds old tables; old table kept
};

inline K1LookBundle *k1_look_bundle[16] = {};
inline K1LookBundle *k1_look_retired[K1_LOOK_RETIRE_MAX] = {};
inline uint8_t k1_look_retired_n = 0;
// Writer-side view of the installed file bytes (Colour Lab saves from these).
inline uint8_t *k1_look_slot_ram[16] = {};
inline size_t k1_look_slot_ram_n[16] = {};

// Frees every retired bundle if no reader is registered now. Returns how many
// remain retired.
static inline uint8_t k1_look_reclaim() {
  if (k1_look_retired_n == 0) {
    return 0;
  }
  if (k1_look_readers.load(std::memory_order_seq_cst) != 0) {
    return k1_look_retired_n;
  }
  for (uint8_t i = 0; i < k1_look_retired_n; i++) {
    K1_LOOK_FREE(k1_look_retired[i]);
    k1_look_retired[i] = nullptr;
  }
  k1_look_retired_n = 0;
  return 0;
}

static inline void k1_look_reclaim_bounded() {
  if (k1_look_reclaim() == 0) {
    return;
  }
  if (K1_LOOK_RECLAIM_WAIT_US == 0u) {
    return;
  }
  const uint32_t t0 = K1_LOOK_NOW_US();
  while (k1_look_reclaim() != 0 &&
         (uint32_t)(K1_LOOK_NOW_US() - t0) < (uint32_t)K1_LOOK_RECLAIM_WAIT_US) {
  }
}

// Point the bundle's descriptor at its own copy. False = table not supported.
static inline bool k1_look_bundle_bind(K1LookBundle *b, const K1LookParsed &p) {
  if (p.type == K1_LOOK_RGB_1D_256 && p.node_n == 256 &&
      p.payload_bytes >= (uint32_t)(256u * 2u * 4u)) {
    const uint16_t *base = reinterpret_cast<const uint16_t *>(p.payload);
    b->view.rgb = {base, base + 256, base + 512, base + 768};
    b->desc = {K1_LOOK_RGB_1D_256, &b->view.rgb};
    return true;
  }
  if (p.type == K1_LOOK_MATRIX_3X4 && p.payload_bytes >= 48) {
    b->desc = {K1_LOOK_MATRIX_3X4, p.payload};
    return true;
  }
  if (p.type == K1_LOOK_CUBE_17 && p.payload_bytes >= (17u * 17u * 17u * 3u * 2u)) {
    b->view.cube.rgb = reinterpret_cast<const uint16_t *>(p.payload);
    b->desc = {K1_LOOK_CUBE_17, &b->view.cube};
    return true;
  }
  if (p.type == K1_LOOK_SHARED_1D_256) {
    b->desc = {K1_LOOK_SHARED_1D_256, nullptr};
    return true;
  }
  return false;
}

// Install a validated table into a loadable slot. A selected slot stays
// selected and switches to the new table on the renderer's next edge.
static inline K1LookResult k1_look_install_parsed_ex(uint8_t slot, const uint8_t *file_bytes,
                                                     size_t file_len) {
  if (!k1_look_slot_loadable(slot)) {
    return K1_LOOK_ERR_SLOT;
  }
  K1LookParsed parsed;
  if (!k1_look_parse_k1lt(file_bytes, file_len, &parsed)) {
    return K1_LOOK_ERR_FILE;
  }
  K1LookBundle probe = {};
  if (!k1_look_bundle_bind(&probe, parsed)) {
    return K1_LOOK_ERR_FILE;
  }
  (void)k1_look_reclaim();
  if (k1_look_bundle[slot] != nullptr && k1_look_retired_n >= K1_LOOK_RETIRE_MAX) {
    return K1_LOOK_ERR_BUSY;
  }
  const size_t head = (sizeof(K1LookBundle) + 7u) & ~(size_t)7u;
  K1LookBundle *nb = static_cast<K1LookBundle *>(K1_LOOK_ALLOC(head + file_len));
  if (nb == nullptr) {
    return K1_LOOK_ERR_NO_MEMORY;
  }
  memset(nb, 0, sizeof(*nb));
  nb->file = reinterpret_cast<uint8_t *>(nb) + head;
  nb->file_len = file_len;
  memcpy(nb->file, file_bytes, file_len);
  K1LookParsed live;
  if (!k1_look_parse_k1lt(nb->file, file_len, &live) || !k1_look_bundle_bind(nb, live)) {
    K1_LOOK_FREE(nb);
    return K1_LOOK_ERR_FILE;
  }
  K1LookBundle *old = k1_look_bundle[slot];
  k1_look_desc[slot].store(&nb->desc, std::memory_order_seq_cst);  // the switch
  k1_look_bundle[slot] = nb;
  k1_look_slot_ram[slot] = nb->file;
  k1_look_slot_ram_n[slot] = file_len;
  if (old != nullptr) {
    k1_look_retired[k1_look_retired_n++] = old;
  }
  k1_look_reclaim_bounded();
  return K1_LOOK_OK;
}

static inline bool k1_look_install_parsed(uint8_t slot, const uint8_t *file_bytes, size_t file_len) {
  return k1_look_install_parsed_ex(slot, file_bytes, file_len) == K1_LOOK_OK;
}

// Empty a loadable slot in RAM. Repeating it is harmless. A selection on the
// cleared slot falls back as before (primary -> slot 0, secondary -> inherit).
static inline K1LookResult k1_look_ram_clear(uint8_t slot) {
  if (!k1_look_slot_loadable(slot)) {
    return K1_LOOK_ERR_SLOT;
  }
  (void)k1_look_reclaim();
  K1LookBundle *old = k1_look_bundle[slot];
  if (old != nullptr && k1_look_retired_n >= K1_LOOK_RETIRE_MAX) {
    return K1_LOOK_ERR_BUSY;
  }
  k1_look_desc[slot].store(&k1_look_empty_desc, std::memory_order_seq_cst);
  k1_look_bundle[slot] = nullptr;
  k1_look_slot_ram[slot] = nullptr;
  k1_look_slot_ram_n[slot] = 0;
  if (k1_look_slot == slot) {
    k1_look_publish(0);
  }
  if (k1_look_slot_sec == slot) {
    k1_look_publish_sec(255);
  }
  if (old != nullptr) {
    k1_look_retired[k1_look_retired_n++] = old;
  }
  k1_look_reclaim_bounded();
  return K1_LOOK_OK;
}
#endif  // K1_LOOK_LIB_V1

#ifdef ARDUINO

#include <Arduino.h>
#include <LittleFS.h>
#include <esp_heap_caps.h>

#ifndef K1_LOOK_RX_MAX
#define K1_LOOK_RX_MAX 32768
#endif

inline uint8_t k1_look_rx_slot = 0;
inline uint32_t k1_look_rx_need = 0;
inline uint32_t k1_look_rx_got = 0;
inline uint8_t *k1_look_rx_buf = nullptr;

// What one received byte did to an armed upload. A finished upload installs
// first and saves second, so "live" and "saved" are separate facts: a table
// can be live while its LittleFS save failed (flash keeps the slot's older
// file, if any; boot reloads only slot 15 from flash).
enum class K1LookRxOutcome : uint8_t {
  Idle,               // no upload armed: the byte was not taken
  Pending,            // byte stored; more bytes expected
  NotInstalled,       // finished; table refused, old table unchanged, nothing saved
  InstalledNotSaved,  // finished; table live now, save failed
  InstalledSaved,     // finished; table live and saved
};

// Serial reply word for a finished upload ("LOOK_LOAD: <word>"), or nullptr
// while there is nothing to report yet.
static inline const char *k1_look_rx_reply(K1LookRxOutcome outcome) {
  switch (outcome) {
    case K1LookRxOutcome::InstalledSaved:
      return "ok";
    case K1LookRxOutcome::InstalledNotSaved:
      return "installed, not saved";
    case K1LookRxOutcome::NotInstalled:
      return "fail";
    default:
      return nullptr;
  }
}

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
  char tmp[28];
  k1_look_slot_path(slot, path, sizeof(path));
  snprintf(tmp, sizeof(tmp), "/look/%02u.klut.tmp", (unsigned)slot);
  LittleFS.remove(tmp);
  File file = LittleFS.open(tmp, FILE_WRITE);
  if (!file) {
    return false;
  }
  const size_t wrote = file.write(bytes, n);
  file.close();
  if (wrote != n) {
    LittleFS.remove(tmp);
    return false;
  }
  LittleFS.remove(path);
  if (!LittleFS.rename(tmp, path)) {
    LittleFS.remove(tmp);
    return false;
  }
  return true;
}

static inline bool k1_look_fs_clear(uint8_t slot) {
  if (!k1_look_slot_loadable(slot)) {
    return false;
  }
  char path[24];
  k1_look_slot_path(slot, path, sizeof(path));
  // RAM first: a busy refusal leaves both the table and its file in place.
  if (k1_look_ram_clear(slot) != K1_LOOK_OK) {
    return false;
  }
  LittleFS.remove(path);
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

static inline K1LookRxOutcome k1_look_rx_push(uint8_t byte) {
  if (k1_look_rx_buf == nullptr || k1_look_rx_got >= k1_look_rx_need) {
    return K1LookRxOutcome::Idle;
  }
  k1_look_rx_buf[k1_look_rx_got++] = byte;
  if (k1_look_rx_got < k1_look_rx_need) {
    return K1LookRxOutcome::Pending;
  }
  // Install, then save. Once installed the table is published and the old one
  // may already be retired, so a failed save is reported, not rolled back.
  K1LookRxOutcome outcome = K1LookRxOutcome::NotInstalled;
  if (k1_look_install_parsed(k1_look_rx_slot, k1_look_rx_buf, k1_look_rx_need)) {
    outcome = k1_look_fs_save(k1_look_rx_slot, k1_look_rx_buf, k1_look_rx_need)
                  ? K1LookRxOutcome::InstalledSaved
                  : K1LookRxOutcome::InstalledNotSaved;
  }
  heap_caps_free(k1_look_rx_buf);
  k1_look_rx_buf = nullptr;
  k1_look_rx_need = 0;
  k1_look_rx_got = 0;
  return outcome;
}

#endif  // ARDUINO
