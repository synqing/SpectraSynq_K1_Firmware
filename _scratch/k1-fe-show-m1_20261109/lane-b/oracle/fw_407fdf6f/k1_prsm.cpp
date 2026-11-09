#include "k1_prsm.h"

#include <string.h>

static uint32_t rd_u32_le(const uint8_t *p) {
  return (uint32_t)p[0]
       | ((uint32_t)p[1] << 8)
       | ((uint32_t)p[2] << 16)
       | ((uint32_t)p[3] << 24);
}

static uint64_t rd_u64_le(const uint8_t *p) {
  uint64_t lo = (uint64_t)rd_u32_le(p);
  uint64_t hi = (uint64_t)rd_u32_le(p + 4);
  return lo | (hi << 32);
}

static uint16_t rd_u16_le(const uint8_t *p) {
  return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

bool k1_prsm_parse(const uint8_t *buf, int len, k1_prsm_frame_t *out) {
  if (!buf || !out) return false;
  if (len < K1_PRSM_PACKET_LEN) return false;
  if (buf[0] != K1_PRSM_MAGIC_0 ||
      buf[1] != K1_PRSM_MAGIC_1 ||
      buf[2] != K1_PRSM_MAGIC_2 ||
      buf[3] != K1_PRSM_MAGIC_3) {
    return false;
  }
  if (buf[4] != K1_PRSM_VERSION) return false;

  out->version = buf[4];
  out->hz = buf[5];
  out->seq = rd_u32_le(buf + 6);
  out->t_us = rd_u64_le(buf + 10);
  const uint8_t *p = buf + 18;
  for (int i = 0; i < 8; i++) {
    out->prim8_u16[i] = rd_u16_le(p);
    p += 2;
  }
  return true;
}

void k1_prsm_scanner_reset(k1_prsm_scanner_t *s) {
  if (!s) return;
  memset(s, 0, sizeof(*s));
}

k1_prsm_scan_result_t k1_prsm_scanner_push(k1_prsm_scanner_t *s, uint8_t byte,
                                           k1_prsm_frame_t *out) {
  if (!s) return K1_PRSM_SCAN_NONE;

  if (s->fill == 0) {
    if (byte != K1_PRSM_MAGIC_0) return K1_PRSM_SCAN_NONE;
    s->buf[0] = byte;
    s->fill = 1;
    return K1_PRSM_SCAN_CONSUMED;
  }

  static const uint8_t magic[4] = {
      K1_PRSM_MAGIC_0, K1_PRSM_MAGIC_1, K1_PRSM_MAGIC_2, K1_PRSM_MAGIC_3};
  if (s->fill < 4) {
    if (byte != magic[s->fill]) {
      /* Broken magic. Re-hunt; this byte may itself be 'P'. */
      s->fill = 0;
      return k1_prsm_scanner_push(s, byte, out);
    }
    s->buf[s->fill++] = byte;
    return K1_PRSM_SCAN_CONSUMED;
  }

  s->buf[s->fill++] = byte;
  if (s->fill < K1_PRSM_PACKET_LEN) return K1_PRSM_SCAN_CONSUMED;

  s->fill = 0;
  if (!out) return K1_PRSM_SCAN_FRAME_BAD;
  if (!k1_prsm_parse(s->buf, K1_PRSM_PACKET_LEN, out)) {
    /* Payload after a valid-looking header failed. Resync from scratch.
     * Do not re-feed the last byte: it is inside a rejected frame. */
    return K1_PRSM_SCAN_FRAME_BAD;
  }
  return K1_PRSM_SCAN_FRAME_OK;
}
