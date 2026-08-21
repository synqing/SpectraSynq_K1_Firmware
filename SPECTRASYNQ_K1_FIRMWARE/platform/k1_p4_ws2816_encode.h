/*
 * P4 LED adapter encoder — donor copy of P4-Nano main/ws2816_encode.h.
 * Lives under platform/ so shared K1 types are not WS2816-shaped (ADR-0007).
 * Protocol selection is an adapter compile flag, not product domain.
 */
#ifndef K1_P4_WS2816_ENCODE_H
#define K1_P4_WS2816_ENCODE_H

#include <stdint.h>

#define WS2816_SPI_HZ            4000000
#define WS2816_SPI_BITS_PER_BIT  5
#define WS2816_SPI_BYTES_PER_BYTE 5
#define WS2816_COLOR_BYTES        6
#define WS2816_SPI_BYTES_PER_PX  (WS2816_COLOR_BYTES * WS2816_SPI_BYTES_PER_BYTE)
#define WS2816_LATCH_US          280

#define WS2816_SYM_0 0x10u
#define WS2816_SYM_1 0x1Cu

static inline void ws2816_encode_byte(uint8_t v, uint8_t out[5])
{
    uint64_t acc = 0;
    for (int b = 7; b >= 0; b--) {
        acc = (acc << WS2816_SPI_BITS_PER_BIT) |
              (((v >> b) & 1u) ? WS2816_SYM_1 : WS2816_SYM_0);
    }
    for (int i = 0; i < 5; i++) {
        out[i] = (uint8_t)((acc >> (32 - 8 * i)) & 0xFFu);
    }
}

static inline void ws2816_build_lut(uint8_t lut[256][5])
{
    for (int v = 0; v < 256; v++) {
        ws2816_encode_byte((uint8_t)v, lut[v]);
    }
}

static inline void ws2816_encode_pixel(const uint8_t lut[256][5],
                                       uint16_t g, uint16_t r, uint16_t b,
                                       uint8_t *dst)
{
    const uint8_t seq[WS2816_COLOR_BYTES] = {
        (uint8_t)(g >> 8), (uint8_t)(g & 0xFF),
        (uint8_t)(r >> 8), (uint8_t)(r & 0xFF),
        (uint8_t)(b >> 8), (uint8_t)(b & 0xFF),
    };
    for (int i = 0; i < WS2816_COLOR_BYTES; i++) {
        const uint8_t *src = lut[seq[i]];
        uint8_t *o = dst + i * WS2816_SPI_BYTES_PER_BYTE;
        o[0] = src[0]; o[1] = src[1]; o[2] = src[2]; o[3] = src[3]; o[4] = src[4];
    }
}

#endif
