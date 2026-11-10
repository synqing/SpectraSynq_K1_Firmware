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

static bool magic_ok(const uint8_t *buf) {
  return buf[0] == K1_PRSM_MAGIC_0 && buf[1] == K1_PRSM_MAGIC_1 &&
         buf[2] == K1_PRSM_MAGIC_2 && buf[3] == K1_PRSM_MAGIC_3;
}

/* Fields from hz onward are laid out identically in both versions. */
static void read_fields(const uint8_t *p, k1_prsm_frame_t *out) {
  out->hz = p[0];
  out->seq = rd_u32_le(p + 1);
  out->t_us = rd_u64_le(p + 5);
  p += 13;
  for (int i = 0; i < 8; i++) {
    out->prim8_u16[i] = rd_u16_le(p);
    p += 2;
  }
}

bool k1_prsm_parse(const uint8_t *buf, int len, k1_prsm_frame_t *out) {
  if (!buf || !out) return false;
  if (len < K1_PRSM_PACKET_LEN) return false;
  if (!magic_ok(buf)) return false;
  if (buf[4] != K1_PRSM_VERSION) return false;

  out->version = buf[4];
  read_fields(buf + 5, out);
  return true;
}

uint32_t k1_prsm_crc32(const uint8_t *data, int len) {
  uint32_t crc = 0xFFFFFFFFu;
  for (int i = 0; i < len; i++) {
    crc ^= data[i];
    for (int b = 0; b < 8; b++) {
      crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
  }
  return crc ^ 0xFFFFFFFFu;
}

bool k1_prsm_parse_v2(const uint8_t *buf, int len, k1_prsm_frame_t *out) {
  if (!buf || !out) return false;
  if (len < K1_PRSM_V2_PACKET_LEN) return false;
  if (!magic_ok(buf)) return false;
  if (buf[4] != K1_PRSM_VERSION_2) return false;
  if (buf[5] != K1_PRSM_V2_PAYLOAD_LEN) return false;
  const int crc_at = K1_PRSM_V2_PACKET_LEN - 4;
  if (k1_prsm_crc32(buf, crc_at) != rd_u32_le(buf + crc_at)) return false;

  out->version = buf[4];
  read_fields(buf + 6, out);
  return true;
}

void k1_prsm_scanner_reset(k1_prsm_scanner_t *s) {
  if (!s) return;
  memset(s, 0, sizeof(*s));
}

/* Drop the candidate being filled. If the byte that ended it could begin a new
 * frame, keep it as the first magic byte. */
static void scanner_drop(k1_prsm_scanner_t *s, uint8_t byte) {
  s->fill = 0;
  s->need = 0;
  s->embed = 0;
  if (byte == K1_PRSM_MAGIC_0) {
    s->buf[0] = byte;
    s->fill = 1;
  }
}

k1_prsm_scan_result_t k1_prsm_scanner_push(k1_prsm_scanner_t *s, uint8_t byte,
                                           k1_prsm_frame_t *out) {
  if (!s) return K1_PRSM_SCAN_NONE;

  static const uint8_t magic[4] = {
      K1_PRSM_MAGIC_0, K1_PRSM_MAGIC_1, K1_PRSM_MAGIC_2, K1_PRSM_MAGIC_3};

  if (s->pending) {
    /* buf holds a whole v1 frame whose tail matched `embed` header bytes. */
    if (s->embed < 4 && byte == magic[s->embed]) {
      s->embed++;
      return K1_PRSM_SCAN_CONSUMED;
    }
    if (s->embed == 4 && (byte == K1_PRSM_VERSION || byte == K1_PRSM_VERSION_2)) {
      /* The tail was the next frame's header: the held frame was cut short. */
      s->pending = 0;
      memcpy(s->buf, magic, 4);
      s->buf[4] = byte;
      s->fill = 5;
      s->need = (byte == K1_PRSM_VERSION) ? K1_PRSM_PACKET_LEN : 0;
      s->embed = 0;
      return K1_PRSM_SCAN_FRAME_BAD;
    }
    /* The tail was payload after all. Release the frame; this byte can only
     * matter if it starts a new header. */
    const bool ok = out && k1_prsm_parse(s->buf, K1_PRSM_PACKET_LEN, out);
    s->pending = 0;
    scanner_drop(s, byte);
    return ok ? K1_PRSM_SCAN_FRAME_OK : K1_PRSM_SCAN_FRAME_BAD;
  }

  if (s->fill == 0) {
    if (byte != K1_PRSM_MAGIC_0) return K1_PRSM_SCAN_NONE;
    s->buf[0] = byte;
    s->fill = 1;
    s->need = 0;
    s->embed = 0;
    return K1_PRSM_SCAN_CONSUMED;
  }

  if (s->fill < 4) {
    if (byte != magic[s->fill]) {
      /* Broken magic. Re-hunt; this byte may itself be 'P'. */
      s->fill = 0;
      return k1_prsm_scanner_push(s, byte, out);
    }
    s->buf[s->fill++] = byte;
    return K1_PRSM_SCAN_CONSUMED;
  }

  if (s->fill == 4) {
    /* Version byte: unknown versions are refused here, not 30 bytes later. */
    if (byte == K1_PRSM_VERSION) {
      s->need = K1_PRSM_PACKET_LEN;
    } else if (byte == K1_PRSM_VERSION_2) {
      s->need = 0; /* known once the length byte arrives */
    } else {
      scanner_drop(s, byte);
      return K1_PRSM_SCAN_FRAME_BAD;
    }
    s->buf[s->fill++] = byte;
    s->embed = 0;
    return K1_PRSM_SCAN_CONSUMED;
  }

  const bool v2 = (s->buf[4] == K1_PRSM_VERSION_2);
  if (v2 && s->fill == 5) {
    if (byte != K1_PRSM_V2_PAYLOAD_LEN) {
      scanner_drop(s, byte);
      return K1_PRSM_SCAN_FRAME_BAD;
    }
    s->need = K1_PRSM_V2_PACKET_LEN;
    s->buf[s->fill++] = byte;
    return K1_PRSM_SCAN_CONSUMED;
  }

  if (!v2) {
    /* v1 has no checksum: a body that contains the next frame's header is a
     * frame cut short. Drop it and restart on the embedded header. */
    if (s->embed < 4) {
      if (byte == magic[s->embed]) {
        s->embed++;
      } else {
        s->embed = (byte == K1_PRSM_MAGIC_0) ? 1 : 0;
      }
    } else {
      if (byte == K1_PRSM_VERSION || byte == K1_PRSM_VERSION_2) {
        memcpy(s->buf, magic, 4);
        s->buf[4] = byte;
        s->fill = 5;
        s->need = (byte == K1_PRSM_VERSION) ? K1_PRSM_PACKET_LEN : 0;
        s->embed = 0;
        return K1_PRSM_SCAN_FRAME_BAD;
      }
      s->embed = (byte == K1_PRSM_MAGIC_0) ? 1 : 0;
    }
  }

  s->buf[s->fill++] = byte;
  if (s->fill < s->need) return K1_PRSM_SCAN_CONSUMED;

  if (!v2 && s->embed > 0) {
    /* Complete, but the tail looks like the start of a header. Hold it. */
    s->pending = 1;
    s->fill = 0;
    s->need = 0;
    return K1_PRSM_SCAN_CONSUMED;
  }

  s->fill = 0;
  s->need = 0;
  s->embed = 0;
  if (!out) return K1_PRSM_SCAN_FRAME_BAD;
  const bool ok = v2 ? k1_prsm_parse_v2(s->buf, K1_PRSM_V2_PACKET_LEN, out)
                     : k1_prsm_parse(s->buf, K1_PRSM_PACKET_LEN, out);
  /* Do not re-feed the last byte of a rejected frame: it is inside the frame. */
  return ok ? K1_PRSM_SCAN_FRAME_OK : K1_PRSM_SCAN_FRAME_BAD;
}

k1_prsm_scan_result_t k1_prsm_scanner_flush(k1_prsm_scanner_t *s,
                                            k1_prsm_frame_t *out) {
  if (!s || !s->pending) return K1_PRSM_SCAN_NONE;
  const bool ok = out && k1_prsm_parse(s->buf, K1_PRSM_PACKET_LEN, out);
  s->pending = 0;
  s->fill = 0;
  s->need = 0;
  s->embed = 0;
  return ok ? K1_PRSM_SCAN_FRAME_OK : K1_PRSM_SCAN_FRAME_BAD;
}
