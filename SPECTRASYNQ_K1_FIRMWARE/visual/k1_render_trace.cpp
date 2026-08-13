// k1_render_trace.cpp — colour-fix-lane LED-level render capture.
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

// 3000 frames × 480 B = 1.44 MB of 8 MB PSRAM (+ ~15 KB sidecars).
// At every_n=4 (≈25 FPS of the 100 FPS render) that is ~120 s of capture.
static const uint32_t K1_RTRACE_MAX_FRAMES = 3000;
static const uint16_t K1_RTRACE_PX = 160;               // native render canvas
static const size_t   K1_RTRACE_FRAME_BYTES = (size_t)K1_RTRACE_PX * 3U;

static uint8_t*  s_buf = nullptr;        // PSRAM, [frame][480] rgb8
static uint32_t* s_ms = nullptr;         // PSRAM sidecar: millis() per frame
static uint8_t*  s_mode = nullptr;       // PSRAM sidecar: LIGHTSHOW_MODE per frame
static volatile uint32_t s_frames = 0;   // frames captured
static volatile bool s_armed = false;
static uint32_t  s_end_ms = 0;
static uint16_t  s_every_n = 4;
static uint32_t  s_tick = 0;
static uint16_t  s_px = K1_RTRACE_PX;    // captured pixels (<= K1_RTRACE_PX)

static bool rtrace_init() {
  if (s_buf != nullptr) return true;
  s_buf = (uint8_t*)ps_malloc((size_t)K1_RTRACE_MAX_FRAMES * K1_RTRACE_FRAME_BYTES);
  s_ms = (uint32_t*)ps_malloc((size_t)K1_RTRACE_MAX_FRAMES * sizeof(uint32_t));
  s_mode = (uint8_t*)ps_malloc((size_t)K1_RTRACE_MAX_FRAMES);
  if (s_buf == nullptr || s_ms == nullptr || s_mode == nullptr) {
    // Loud failure per the invisible-kill-switch rule: a trace that silently
    // has no buffer would report "0 frames" and read as a dark plate.
    USBSerial.println("[RTRACE] INIT FAIL: ps_malloc returned NULL — capture disabled");
    if (s_buf) { free(s_buf); s_buf = nullptr; }
    if (s_ms) { free(s_ms); s_ms = nullptr; }
    if (s_mode) { free(s_mode); s_mode = nullptr; }
    return false;
  }
  USBSerial.printf("[RTRACE] INIT PASS: %lu frames capacity (%u px/frame)\n",
                   (unsigned long)K1_RTRACE_MAX_FRAMES, (unsigned)K1_RTRACE_PX);
  return true;
}

void k1_render_trace_on_frame(const uint8_t* rgb_bytes, uint16_t led_count,
                              uint8_t lightshow_mode) {
  if (!s_armed || s_buf == nullptr) return;
  if (++s_tick % s_every_n != 0) return;
  const uint32_t f = s_frames;
  if (f >= K1_RTRACE_MAX_FRAMES || (int32_t)(millis() - s_end_ms) >= 0) {
    s_armed = false;
    return;
  }
  uint16_t px = led_count < K1_RTRACE_PX ? led_count : K1_RTRACE_PX;
  uint8_t* dst = &s_buf[(size_t)f * K1_RTRACE_FRAME_BYTES];
  memcpy(dst, rgb_bytes, (size_t)px * 3U);
  if (px < K1_RTRACE_PX) {
    memset(dst + (size_t)px * 3U, 0, ((size_t)K1_RTRACE_PX - px) * 3U);
  }
  s_ms[f] = millis();
  s_mode[f] = lightshow_mode;
  if (px < s_px) s_px = px;
  s_frames = f + 1;
}

static void rtrace_status() {
  USBSerial.printf("[RTRACE] armed=%d frames=%lu capacity=%lu every=%u px=%u buf=%s\n",
                   s_armed ? 1 : 0, (unsigned long)s_frames,
                   (unsigned long)K1_RTRACE_MAX_FRAMES, (unsigned)s_every_n,
                   (unsigned)s_px, (s_buf != nullptr) ? "ok" : "NULL");
}

static void rtrace_arm(char* args) {
  if (!rtrace_init()) { USBSerial.println("[RTRACE] ARM FAIL: no buffer"); return; }
  long seconds = 30; long every = 4;
  if (args != nullptr && args[0] != '\0') {
    char* comma = strchr(args, ',');
    seconds = atol(args);
    if (comma != nullptr) every = atol(comma + 1);
  }
  if (seconds < 1) seconds = 1;
  if (seconds > 600) seconds = 600;
  if (every < 1) every = 1;
  if (every > 100) every = 100;
  s_armed = false;                 // order matters: stop the writer before reset
  s_frames = 0;
  s_tick = 0;
  s_px = K1_RTRACE_PX;
  s_every_n = (uint16_t)every;
  s_end_ms = millis() + (uint32_t)seconds * 1000U;
  s_armed = true;
  USBSerial.printf("[RTRACE] ARMED: %ld s, every %ld frames (cap %lu)\n",
                   seconds, every, (unsigned long)K1_RTRACE_MAX_FRAMES);
}

static void rtrace_dump() {
  s_armed = false;  // never dump a moving buffer
  const uint32_t frames = s_frames;
  if (s_buf == nullptr || frames == 0) {
    USBSerial.println("[RTRACE-BEGIN frames=0 crc32=0]");
    USBSerial.println("[RTRACE-END]");
    return;
  }
  const size_t total_bytes = (size_t)frames * K1_RTRACE_FRAME_BYTES;
  const uint32_t crc = esp_crc32_le(0, s_buf, total_bytes);
  USBSerial.printf("[RTRACE-BEGIN frames=%lu every=%u px=%u fmt=rgb8hex crc32=%08lx]\n",
                   (unsigned long)frames, (unsigned)s_every_n, (unsigned)s_px,
                   (unsigned long)crc);
  static const char* hexc = "0123456789abcdef";
  // One frame per line: F,<idx>,<ms>,<mode>,<hex of px*3 bytes>.
  char line[K1_RTRACE_PX * 6 + 1];
  for (uint32_t f = 0; f < frames; f++) {
    const uint8_t* src = &s_buf[(size_t)f * K1_RTRACE_FRAME_BYTES];
    const size_t n = (size_t)s_px * 3U;
    for (size_t i = 0; i < n; i++) {
      line[i * 2]     = hexc[src[i] >> 4];
      line[i * 2 + 1] = hexc[src[i] & 0x0F];
    }
    line[n * 2] = '\0';
    USBSerial.printf("F,%lu,%lu,%u,", (unsigned long)f, (unsigned long)s_ms[f],
                     (unsigned)s_mode[f]);
    USBSerial.println(line);
    // Feed the idle task / watchdog every 64 frames (~62 KiB) — the dump is
    // post-capture and allowed to starve render, but never the WDT.
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
