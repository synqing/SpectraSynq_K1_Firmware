/**
 * PNG writer for simulator screenshots.
 *
 * Emits a truecolour 8-bit PNG whose IDAT is a zlib stream built entirely from
 * stored (uncompressed) deflate blocks. Files are larger than a compressed
 * encoder would produce, but the simulator gains no third-party dependency and
 * the output is a standard PNG that any viewer opens.
 */

#include "sim_png.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace {

uint32_t crc32_of(const uint8_t* data, size_t len, uint32_t crc)
{
  static uint32_t table[256];
  static bool built = false;
  if (!built) {
    for (uint32_t n = 0; n < 256; ++n) {
      uint32_t c = n;
      for (int k = 0; k < 8; ++k) c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
      table[n] = c;
    }
    built = true;
  }
  crc ^= 0xFFFFFFFFu;
  for (size_t i = 0; i < len; ++i) crc = table[(crc ^ data[i]) & 0xFF] ^ (crc >> 8);
  return crc ^ 0xFFFFFFFFu;
}

void put_be32(uint8_t* p, uint32_t v)
{
  p[0] = uint8_t(v >> 24);
  p[1] = uint8_t(v >> 16);
  p[2] = uint8_t(v >> 8);
  p[3] = uint8_t(v);
}

bool write_chunk(FILE* f, const char tag[4], const uint8_t* payload, uint32_t len)
{
  uint8_t hdr[8];
  put_be32(hdr, len);
  memcpy(hdr + 4, tag, 4);
  if (fwrite(hdr, 1, 8, f) != 8) return false;
  if (len && fwrite(payload, 1, len, f) != len) return false;

  uint32_t crc = crc32_of(reinterpret_cast<const uint8_t*>(tag), 4, 0);
  if (len) crc = crc32_of(payload, len, crc);
  uint8_t crc_be[4];
  put_be32(crc_be, crc);
  return fwrite(crc_be, 1, 4, f) == 4;
}

}  // namespace

bool sim_png_write_rgb(const char* path, const uint8_t* rgb, uint32_t w, uint32_t h)
{
  if (!path || !rgb || w == 0 || h == 0) return false;

  /* Raw (pre-deflate) stream: one filter byte (0 = None) per scanline. */
  const size_t row_bytes = size_t(w) * 3u + 1u;
  const size_t raw_len = row_bytes * size_t(h);
  uint8_t* raw = static_cast<uint8_t*>(malloc(raw_len));
  if (!raw) return false;
  for (uint32_t y = 0; y < h; ++y) {
    uint8_t* dst = raw + row_bytes * y;
    dst[0] = 0;
    memcpy(dst + 1, rgb + size_t(w) * 3u * y, size_t(w) * 3u);
  }

  /* zlib: 0x78 0x01 header, stored deflate blocks, adler32 trailer. */
  const size_t max_block = 65535;
  const size_t block_count = (raw_len + max_block - 1) / max_block;
  const size_t zlen = 2 + block_count * 5 + raw_len + 4;
  uint8_t* z = static_cast<uint8_t*>(malloc(zlen));
  if (!z) {
    free(raw);
    return false;
  }

  size_t zi = 0;
  z[zi++] = 0x78;
  z[zi++] = 0x01;
  for (size_t off = 0; off < raw_len; off += max_block) {
    const size_t n = (raw_len - off < max_block) ? (raw_len - off) : max_block;
    z[zi++] = (off + n >= raw_len) ? 1 : 0;  /* BFINAL on the last block */
    z[zi++] = uint8_t(n & 0xFF);
    z[zi++] = uint8_t(n >> 8);
    z[zi++] = uint8_t(~n & 0xFF);
    z[zi++] = uint8_t((~n >> 8) & 0xFF);
    memcpy(z + zi, raw + off, n);
    zi += n;
  }

  uint32_t a = 1, b = 0;
  for (size_t i = 0; i < raw_len; ++i) {
    a = (a + raw[i]) % 65521u;
    b = (b + a) % 65521u;
  }
  put_be32(z + zi, (b << 16) | a);
  zi += 4;
  free(raw);

  FILE* f = fopen(path, "wb");
  if (!f) {
    free(z);
    return false;
  }

  static const uint8_t sig[8] = {0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A};
  bool ok = fwrite(sig, 1, 8, f) == 8;

  uint8_t ihdr[13];
  put_be32(ihdr + 0, w);
  put_be32(ihdr + 4, h);
  ihdr[8] = 8;   /* bit depth */
  ihdr[9] = 2;   /* colour type: truecolour */
  ihdr[10] = 0;  /* deflate */
  ihdr[11] = 0;  /* adaptive filtering */
  ihdr[12] = 0;  /* no interlace */
  ok = ok && write_chunk(f, "IHDR", ihdr, sizeof(ihdr));
  ok = ok && write_chunk(f, "IDAT", z, uint32_t(zi));
  ok = ok && write_chunk(f, "IEND", nullptr, 0);

  fclose(f);
  free(z);
  return ok;
}
