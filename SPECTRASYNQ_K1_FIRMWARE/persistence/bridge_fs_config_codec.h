/*----------------------------------------
  K1 PERSISTED-CONFIG BLOB CODEC (N1 config integrity)
  ----------------------------------------

  The LIVE persisted-config path (save_config()/load_config() in bridge_fs.h)
  historically wrote/read a RAW byte image of `struct conf` with NO integrity
  metadata: a truncated, corrupt, or stale-layout file was memcpy'd straight into
  the live CONFIG and trusted. This header is the integrity + recovery decision
  layer for that path.

  It is deliberately FS-FREE and self-contained (only <stdint.h>/<stddef.h>/
  <string.h>) so the decision logic host-compiles and can be locked by a behavioural
  oracle (scripts/regression-harness/golden/oracle_bridge_fs_codec.py) — the real
  N1 proof — independently of LittleFS/FreeRTOS.

  ON-DISK LAYOUT written by save_config():
      [ ConfigBlobHeader (12 bytes, packed) ][ sizeof(conf) raw CONFIG bytes ]
  zero-padded to the existing 512-byte file size.

  RECOVERY POLICY (anti-brick — the whole point of N1): a failed/legacy load
  decides between LOAD / MIGRATE / FALLBACK in RAM only. bridge_fs.h NEVER reacts
  to a bad blob by deleting files or rebooting (factory_reset()/restore_defaults()
  both delete + reboot and risk a boot loop on a persistently-bad file). FALLBACK
  copies the in-RAM compiled defaults and re-saves a valid blob.
*/

#ifndef BRIDGE_FS_CONFIG_CODEC_H
#define BRIDGE_FS_CONFIG_CODEC_H

#include <stdint.h>
#include <stddef.h>
#include <string.h>

// "K1CF" little-endian. A persisted blob that begins with this magic is a
// headered K1 config blob; anything else is treated as headerless legacy.
#define CONFIG_BLOB_MAGIC 0x4B314346UL
// Bump whenever the on-disk meaning of the raw CONFIG image changes. A header
// whose version != CONFIG_BLOB_VERSION is rejected (FALLBACK), never blindly
// memcpy'd into a struct that may have been re-laid-out.
#define CONFIG_BLOB_VERSION 1U

// 12 bytes, no padding (4 + 2 + 2 + 4, all naturally aligned). Mirrors the
// magic+version header pattern already used by the calibration profile in
// bridge_fs.h (save_calibration_profile / load_calibration_profile_if_config_invalid).
struct ConfigBlobHeader {
  uint32_t magic;    // CONFIG_BLOB_MAGIC
  uint16_t version;  // CONFIG_BLOB_VERSION
  uint16_t length;   // == sizeof(conf) at save time (layout-size guard)
  uint32_t crc32;    // bridge_fs_crc32() over the raw CONFIG bytes that follow
};

// Standard reflected CRC-32 (poly 0xEDB88320, init/final 0xFFFFFFFF). Table-less
// bit-at-a-time form — `struct conf` is small and saved rarely, so the loop cost
// is irrelevant and a 1 KiB table is not worth the flash. POD `conf` (all
// float/uintN/int32/bool, no pointers) makes a CRC-over-bytes stable.
static inline uint32_t bridge_fs_crc32(const uint8_t* data, size_t len) {
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

// The three outcomes load_config() acts on. Kept as small ints so the oracle
// records them directly.
enum ConfigLoadDecision {
  CFG_LOAD     = 0,  // headered + magic/version/length/crc all valid -> trust payload
  CFG_MIGRATE  = 1,  // headerless legacy raw image, long enough -> adopt + re-save headered
  CFG_FALLBACK = 2   // header present but invalid, OR too short to be usable -> RAM defaults
};

// Classify a persisted file's bytes into a recovery decision WITHOUT touching the
// filesystem. `file_bytes`/`file_len` are what was read off disk; `config_size`
// is sizeof(conf) on this build.
//
// DECISION TABLE (exact):
//   * file_len >= sizeof(ConfigBlobHeader)+config_size AND the header validates
//     (magic==MAGIC && version==VERSION && length==config_size &&
//      crc32==crc(payload))                                  -> CFG_LOAD
//   * else if first 4 bytes == MAGIC (a header is present but failed validation:
//     bad crc / wrong version / wrong length / truncated payload) -> CFG_FALLBACK
//     (do NOT migrate a corrupt headered blob — a flipped CRC must not be
//      reinterpreted as legacy and trusted)
//   * else (no magic at offset 0 = headerless legacy image):
//       - file_len >= config_size                            -> CFG_MIGRATE
//       - else (too short to even be a legacy image)         -> CFG_FALLBACK
//
// The header is read via memcpy into a local (not a pointer-cast) so an unaligned
// `file_bytes` cannot invoke alignment UB.
static inline ConfigLoadDecision bridge_fs_classify_config(const uint8_t* file_bytes,
                                                           size_t file_len,
                                                           size_t config_size) {
  const size_t header_size = sizeof(ConfigBlobHeader);

  // Path 1: enough bytes for a full headered blob — validate it.
  if (file_len >= header_size + config_size) {
    ConfigBlobHeader header;
    memcpy(&header, file_bytes, header_size);  // alignment-safe header read
    if (header.magic == CONFIG_BLOB_MAGIC &&
        header.version == CONFIG_BLOB_VERSION &&
        header.length == (uint16_t)config_size &&
        bridge_fs_crc32(file_bytes + header_size, config_size) == header.crc32) {
      return CFG_LOAD;
    }
  }

  // Path 2: a header is present at offset 0 but the blob did NOT validate above
  // (bad crc / version / length, or truncated after the magic). Recover to
  // defaults — never trust or migrate a corrupt headered blob.
  if (file_len >= 4) {
    uint32_t leading_magic;
    memcpy(&leading_magic, file_bytes, 4);  // alignment-safe magic probe
    if (leading_magic == (uint32_t)CONFIG_BLOB_MAGIC) {
      return CFG_FALLBACK;
    }
  }

  // Path 3: headerless legacy image (no magic at offset 0). Adopt it if it is at
  // least a full raw CONFIG image; otherwise it is too short to use -> defaults.
  if (file_len >= config_size) {
    return CFG_MIGRATE;
  }
  return CFG_FALLBACK;
}

// Stamp a ConfigBlobHeader for `config_bytes` (the raw sizeof(conf) image) so
// save_config() can prepend it. length is the layout-size guard; crc32 is the
// integrity guard load_config() re-checks.
static inline void bridge_fs_fill_header(ConfigBlobHeader* h,
                                         const uint8_t* config_bytes,
                                         size_t config_size) {
  h->magic   = CONFIG_BLOB_MAGIC;
  h->version = CONFIG_BLOB_VERSION;
  h->length  = (uint16_t)config_size;
  h->crc32   = bridge_fs_crc32(config_bytes, config_size);
}

#endif // BRIDGE_FS_CONFIG_CODEC_H
