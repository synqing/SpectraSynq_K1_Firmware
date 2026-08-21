// k1_render_trace.cpp — LED-level render capture.
// See k1_render_trace.h. Gate sits BEFORE every include so this TU preprocesses
// to NOTHING in any env without K1_RENDER_TRACE_V1 (no global-ctor leak —
// production byte-identity preserved by construction).
#ifdef K1_RENDER_TRACE_V1

#include <Arduino.h>
#include <string.h>
#include <stdlib.h>
#include "esp_crc.h"
#include "esp32-hal-psram.h"
#include "../system/globals.h"
#include "k1_render_trace.h"

// 3000 frames × 960 B = 2.88 MB of 8 MB PSRAM (+ ~15 KB sidecars).
// Stride is always 6 bytes/px so Lever-2 packed wire fits; RGB8 uses the
// first 3 bytes/px. At every_n=4 (≈25 FPS of the 100 FPS render) that is
// ~120 s of capture.
static const uint32_t K1_RTRACE_MAX_FRAMES = 3000;
static const uint16_t K1_RTRACE_PX = 160;
static const size_t   K1_RTRACE_FRAME_BYTES = (size_t)K1_RTRACE_PX * 6U;

static uint8_t*  s_buf = nullptr;
static uint32_t* s_ms = nullptr;
static uint8_t*  s_mode = nullptr;
static volatile uint32_t s_frames = 0;
static volatile bool s_armed = false;
static uint32_t  s_end_ms = 0;
static uint16_t  s_every_n = 4;
static uint32_t  s_tick = 0;
static uint16_t  s_px = K1_RTRACE_PX;
static uint8_t   s_bpp = 0;  // 8 or 16; 0 until first captured frame
static volatile bool s_stim = false;

static bool rtrace_init() {
  if (s_buf != nullptr) return true;
  s_buf = (uint8_t*)ps_malloc((size_t)K1_RTRACE_MAX_FRAMES * K1_RTRACE_FRAME_BYTES);
  s_ms = (uint32_t*)ps_malloc((size_t)K1_RTRACE_MAX_FRAMES * sizeof(uint32_t));
  s_mode = (uint8_t*)ps_malloc((size_t)K1_RTRACE_MAX_FRAMES);
  if (s_buf == nullptr || s_ms == nullptr || s_mode == nullptr) {
    USBSerial.println("[RTRACE] INIT FAIL: ps_malloc returned NULL — capture disabled");
    if (s_buf) { free(s_buf); s_buf = nullptr; }
    if (s_ms) { free(s_ms); s_ms = nullptr; }
    if (s_mode) { free(s_mode); s_mode = nullptr; }
    return false;
  }
  USBSerial.printf("[RTRACE] INIT PASS: %lu frames capacity (%u px/frame, stride=6)\n",
                   (unsigned long)K1_RTRACE_MAX_FRAMES, (unsigned)K1_RTRACE_PX);
  return true;
}

static void rtrace_store(const uint8_t* src, uint16_t led_count, uint8_t mode,
                         uint8_t bpp) {
  if (!s_armed || s_buf == nullptr) return;
  if (++s_tick % s_every_n != 0) return;
  if (s_bpp != 0 && s_bpp != bpp) return;
  const uint32_t f = s_frames;
  if (f >= K1_RTRACE_MAX_FRAMES || (int32_t)(millis() - s_end_ms) >= 0) {
    s_armed = false;
    return;
  }
  uint16_t px = led_count < K1_RTRACE_PX ? led_count : K1_RTRACE_PX;
  uint8_t* dst = &s_buf[(size_t)f * K1_RTRACE_FRAME_BYTES];
  const size_t copy = (size_t)px * (bpp == 16 ? 6U : 3U);
  memcpy(dst, src, copy);
  if (copy < K1_RTRACE_FRAME_BYTES) {
    memset(dst + copy, 0, K1_RTRACE_FRAME_BYTES - copy);
  }
  s_ms[f] = millis();
  s_mode[f] = mode;
  if (px < s_px) s_px = px;
  s_bpp = bpp;
  s_frames = f + 1;
}

void k1_render_trace_on_frame(const uint8_t* rgb_bytes, uint16_t led_count,
                              uint8_t lightshow_mode) {
  rtrace_store(rgb_bytes, led_count, lightshow_mode, 8);
}

void k1_render_trace_on_frame16(const uint8_t* packed6, uint16_t led_count,
                                uint8_t lightshow_mode) {
  rtrace_store(packed6, led_count, lightshow_mode, 16);
}

bool k1_render_trace_stim_active(void) {
  return s_stim && s_armed;
}

static void rtrace_status() {
  USBSerial.printf("[RTRACE] armed=%d frames=%lu capacity=%lu every=%u px=%u bpp=%u buf=%s\n",
                   s_armed ? 1 : 0, (unsigned long)s_frames,
                   (unsigned long)K1_RTRACE_MAX_FRAMES, (unsigned)s_every_n,
                   (unsigned)s_px, (unsigned)s_bpp,
                   (s_buf != nullptr) ? "ok" : "NULL");
}

static void rtrace_arm(char* args) {
  if (!rtrace_init()) { USBSerial.println("[RTRACE] ARM FAIL: no buffer"); return; }
  long seconds = 30; long every = 4;
  bool stim = false;
  if (args != nullptr && args[0] != '\0') {
    char* comma = strchr(args, ',');
    seconds = atol(args);
    if (comma != nullptr) {
      every = atol(comma + 1);
      char* comma2 = strchr(comma + 1, ',');
      if (comma2 != nullptr && strstr(comma2, "stim") != nullptr) stim = true;
    }
  }
  if (seconds < 1) seconds = 1;
  if (seconds > 600) seconds = 600;
  if (every < 1) every = 1;
  if (every > 100) every = 100;
  s_armed = false;
  s_frames = 0;
  s_tick = 0;
  s_px = K1_RTRACE_PX;
  s_bpp = 0;
  s_stim = stim;
  s_every_n = (uint16_t)every;
  s_end_ms = millis() + (uint32_t)seconds * 1000U;
  s_armed = true;
  USBSerial.printf("[RTRACE] ARMED: %ld s, every %ld frames (cap %lu)%s\n",
                   seconds, every, (unsigned long)K1_RTRACE_MAX_FRAMES,
                   stim ? " stim=1" : "");
}

static void rtrace_dump() {
  s_armed = false;
  const uint32_t frames = s_frames;
  if (s_buf == nullptr || frames == 0) {
    USBSerial.println("[RTRACE-BEGIN frames=0 crc32=0]");
    USBSerial.println("[RTRACE-END]");
    return;
  }
  const size_t total_bytes = (size_t)frames * K1_RTRACE_FRAME_BYTES;
  const uint32_t crc = esp_crc32_le(0, s_buf, total_bytes);
  const char* fmt = (s_bpp == 16) ? "rgb16hex" : "rgb8hex";
  USBSerial.printf("[RTRACE-BEGIN frames=%lu every=%u px=%u fmt=%s bpp=%u crc32=%08lx]\n",
                   (unsigned long)frames, (unsigned)s_every_n, (unsigned)s_px,
                   fmt, (unsigned)s_bpp, (unsigned long)crc);
  static const char* hexc = "0123456789abcdef";
  // rgb8: 6 hex chars/px. rgb16 unpacked R16BE G16BE B16BE: 12 hex chars/px.
  char line[K1_RTRACE_PX * 12 + 1];
  for (uint32_t f = 0; f < frames; f++) {
    const uint8_t* src = &s_buf[(size_t)f * K1_RTRACE_FRAME_BYTES];
    size_t nhex = 0;
    if (s_bpp == 16) {
      for (uint16_t i = 0; i < s_px; i++) {
        const uint8_t* p = src + (size_t)i * 6U;
        // packed wire: G_hi G_lo R_hi R_lo B_hi B_lo → dump R16 G16 B16
        const uint8_t out[6] = {p[2], p[3], p[0], p[1], p[4], p[5]};
        for (size_t b = 0; b < 6; b++) {
          line[nhex++] = hexc[out[b] >> 4];
          line[nhex++] = hexc[out[b] & 0x0F];
        }
      }
    } else {
      const size_t n = (size_t)s_px * 3U;
      for (size_t i = 0; i < n; i++) {
        line[nhex++] = hexc[src[i] >> 4];
        line[nhex++] = hexc[src[i] & 0x0F];
      }
    }
    line[nhex] = '\0';
    USBSerial.printf("F,%lu,%lu,%u,", (unsigned long)f, (unsigned long)s_ms[f],
                     (unsigned)s_mode[f]);
    USBSerial.println(line);
    if ((f & 0x3F) == 0x3F) vTaskDelay(1);
  }
  USBSerial.println("[RTRACE-END]");
}

bool k1_render_trace_dispatch(const char* command_type, char* command_data) {
  if (strcmp(command_type, "rtrace_arm") == 0) {
    rtrace_arm(command_data);
    return true;
  }
  if (strcmp(command_type, "rtrace_status") == 0) {
    rtrace_status();
    return true;
  }
  if (strcmp(command_type, "rtrace_dump") == 0) {
    rtrace_dump();
    return true;
  }
  return false;
}

#endif  // K1_RENDER_TRACE_V1
