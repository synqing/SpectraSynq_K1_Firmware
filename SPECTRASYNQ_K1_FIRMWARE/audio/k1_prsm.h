#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* PRSM FeatureFrame wire formats.
 *
 * Version 1 (34 bytes) — layout verified against PRISM
 * k1_usb_uac_cdc_bridge/main/k1_feature_frame.h (transport reference only).
 * Product K1 copies the wire format, not the bridge renderer.
 *   0..3   'P','R','S','M'
 *   4      version = 1
 *   5      hz
 *   6..9   seq   (u32 LE)
 *   10..17 t_us  (u64 LE)
 *   18..33 prim8 (8 x u16 LE)
 * Version 1 has no integrity check. The scanner therefore refuses any v1 frame
 * whose body contains the next frame's header ('P','R','S','M' + a known
 * version byte): that is what a frame cut short on the wire looks like once the
 * following frame arrives. The scanner restarts on the embedded header, so the
 * cut frame is dropped and the following frame is kept.
 *
 * Version 2 (39 bytes) — the same fields behind a length and a CRC:
 *   0..3   'P','R','S','M'
 *   4      version = 2
 *   5      payload length = 29 (bytes 6..34)
 *   6      hz
 *   7..10  seq   (u32 LE)
 *   11..18 t_us  (u64 LE)
 *   19..34 prim8 (8 x u16 LE)
 *   35..38 CRC-32 (IEEE 802.3, reflected, init and final XOR 0xFFFFFFFF — the
 *          value zlib.crc32 returns) over bytes 0..34, u32 LE
 * A v2 frame is handed on only when its length byte and CRC are both right. */

#define K1_PRSM_PACKET_LEN 34
#define K1_PRSM_MAGIC_0 'P'
#define K1_PRSM_MAGIC_1 'R'
#define K1_PRSM_MAGIC_2 'S'
#define K1_PRSM_MAGIC_3 'M'
#define K1_PRSM_VERSION 1

#define K1_PRSM_VERSION_2 2
#define K1_PRSM_V2_PAYLOAD_LEN 29
#define K1_PRSM_V2_PACKET_LEN 39
#define K1_PRSM_MAX_PACKET_LEN K1_PRSM_V2_PACKET_LEN

typedef struct {
  uint8_t version;
  uint8_t hz;
  uint32_t seq;
  uint64_t t_us;
  uint16_t prim8_u16[8];
} k1_prsm_frame_t;

/* Version 1 only. */
bool k1_prsm_parse(const uint8_t *buf, int len, k1_prsm_frame_t *out);
/* Version 2 only: checks magic, version, length byte and CRC. */
bool k1_prsm_parse_v2(const uint8_t *buf, int len, k1_prsm_frame_t *out);

uint32_t k1_prsm_crc32(const uint8_t *data, int len);

typedef enum {
  K1_PRSM_SCAN_NONE = 0,     /* byte is not part of a PRSM frame */
  K1_PRSM_SCAN_CONSUMED,     /* byte consumed by hunter/filler; not a complete frame */
  K1_PRSM_SCAN_FRAME_OK,     /* complete valid frame in *out */
  K1_PRSM_SCAN_FRAME_BAD     /* a candidate frame was rejected; resynchronising */
} k1_prsm_scan_result_t;

typedef struct {
  uint8_t buf[K1_PRSM_MAX_PACKET_LEN];
  uint8_t fill;
  uint8_t need;   /* total length of the frame being filled; 0 until known */
  uint8_t embed;  /* v1 body: bytes of an embedded frame header matched so far */
  uint8_t pending; /* a complete v1 frame is held until the next byte settles it */
} k1_prsm_scanner_t;

void k1_prsm_scanner_reset(k1_prsm_scanner_t *s);
k1_prsm_scan_result_t k1_prsm_scanner_push(k1_prsm_scanner_t *s, uint8_t byte,
                                           k1_prsm_frame_t *out);
/* A v1 frame whose last bytes could be the start of the next frame's header
 * ('P', 'PR', 'PRS' or 'PRSM') is held back: only the following byte tells a
 * whole frame from one cut short just before its end. Call this when the
 * receive burst has ended; it releases a held frame (FRAME_OK) or returns
 * NONE. */
k1_prsm_scan_result_t k1_prsm_scanner_flush(k1_prsm_scanner_t *s,
                                            k1_prsm_frame_t *out);

#ifdef __cplusplus
}
#endif
