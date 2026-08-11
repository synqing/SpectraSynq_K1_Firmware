#pragma once
/** Minimal RGB888 -> PNG writer (stored deflate blocks; no zlib dependency). */

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @param path   destination file
 * @param rgb    w*h*3 bytes, row-major, 8 bits per channel
 * @return true on success
 */
bool sim_png_write_rgb(const char* path, const uint8_t* rgb, uint32_t w, uint32_t h);

#ifdef __cplusplus
}
#endif
