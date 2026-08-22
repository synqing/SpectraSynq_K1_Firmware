/*
 * P4 LED adapter encoder — donor copy of P4-Nano main/ws2812_encode.h.
 * Lives under platform/ so shared K1 types are not wire-protocol-shaped (ADR-0007).
 *
 * Captain 2026-08-22: lab loom is two physically separate WS2812 strips,
 * 160 pixels each, single data line per strip (GPIO4 primary, GPIO5 secondary).
 * Not WS2816C-1313 dual-DIN.
 *
 * Each WS2812 data bit is three SPI symbols at 2.5 MHz:
 *   0 -> 100  (T0H 0.4 us, T0L 0.8 us)
 *   1 -> 110  (T1H 0.8 us, T1L 0.4 us)
 */
#ifndef K1_P4_WS2812_ENCODE_H
#define K1_P4_WS2812_ENCODE_H

#include <stdint.h>

#define WS2812_SPI_HZ            2500000
#define WS2812_SPI_BYTES_PER_U8  3U
#define WS2812_SPI_BYTES_PER_PX  9U
#define WS2812_LATCH_US          280U

static inline void ws2812_encode_byte(uint8_t value, uint8_t out[3])
{
    uint32_t encoded = 0U;
    for (int bit = 7; bit >= 0; bit--) {
        encoded = (encoded << 3U) |
                  (((value >> bit) & 1U) != 0U ? 0x6U : 0x4U);
    }
    out[0] = (uint8_t)(encoded >> 16U);
    out[1] = (uint8_t)(encoded >> 8U);
    out[2] = (uint8_t)encoded;
}

static inline void ws2812_encode_pixel(uint8_t red,
                                       uint8_t green,
                                       uint8_t blue,
                                       uint8_t out[WS2812_SPI_BYTES_PER_PX])
{
    /* WS2812 wire order is GRB, most-significant bit first. */
    ws2812_encode_byte(green, &out[0]);
    ws2812_encode_byte(red, &out[3]);
    ws2812_encode_byte(blue, &out[6]);
}

#endif
