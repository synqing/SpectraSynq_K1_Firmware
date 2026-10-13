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

static const uint16_t K1_RTRACE_PX = 160;
static const size_t K1_RTRACE_EDGE_BYTES = (size_t)K1_RTRACE_PX * 6U;
#ifdef K1_B489_WS2816_V1
// B489: 2000 dual-edge frames × 1920 B = 3.84 MB (+ 10 KB sidecars).
static const uint32_t K1_RTRACE_MAX_FRAMES = 2000;
static const size_t K1_RTRACE_FRAME_BYTES = K1_RTRACE_EDGE_BYTES * 2U;
#else
// Preserve the existing single-edge allocation/capacity on every legacy env.
// 3000 × 960 B = 2.88 MB (+ 15 KB sidecars).
static const uint32_t K1_RTRACE_MAX_FRAMES = 3000;
static const size_t K1_RTRACE_FRAME_BYTES = K1_RTRACE_EDGE_BYTES;
#endif

static uint8_t*  s_buf = nullptr;
static uint32_t* s_ms = nullptr;
static uint8_t*  s_mode = nullptr;
static uint32_t s_frames = 0;
static bool s_armed = false;
static uint32_t  s_end_ms = 0;
static uint16_t  s_every_n = 4;
static uint32_t  s_tick = 0;
static uint16_t  s_px = K1_RTRACE_PX;
static uint8_t   s_bpp = 0;  // 8 or 16; 0 until first captured frame
static uint8_t   s_edges = 0;
static bool s_stim = false;

// Serial task owns arm/status/dump; the render task owns frame production.
// Protect publication and freeze against a frame copy already in progress.
// Never allocate, print or wait while holding this bounded copy lock.
static portMUX_TYPE s_capture_mux = portMUX_INITIALIZER_UNLOCKED;
class CaptureLock {
 public:
  CaptureLock() { portENTER_CRITICAL(&s_capture_mux); }
  ~CaptureLock() { portEXIT_CRITICAL(&s_capture_mux); }
  CaptureLock(const CaptureLock&) = delete;
  CaptureLock& operator=(const CaptureLock&) = delete;
};

#ifdef K1_B489_WS2816_V1
// The serial command runs on the audio owner. Drain on an idle-priority task,
// otherwise a multi-megabyte USB write would prevent new microphone hops.
// Created once from the command path; no task/heap operations in render.
static StaticTask_t s_drain_task_storage;
static StackType_t s_drain_stack[6144 / sizeof(StackType_t)];
static TaskHandle_t s_drain_task = nullptr;
static bool s_drain_busy = false;  // protected by s_capture_mux
static void rtrace_drain_once();
static void rtrace_drain_task(void*) {
  for (;;) {
    // Deliberate indefinite wait while idle; a dump notification is the owner.
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    rtrace_drain_once();
  }
}
static bool rtrace_init_drain() {
  if (s_drain_task == nullptr) {
    s_drain_task = xTaskCreateStaticPinnedToCore(
        rtrace_drain_task, "rtrace_drain", sizeof(s_drain_stack), nullptr,
        tskIDLE_PRIORITY, s_drain_stack, &s_drain_task_storage, 0);
  }
  return s_drain_task != nullptr;
}
#endif

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

static void rtrace_store(const uint8_t* primary, const uint8_t* secondary,
                         uint16_t led_count, uint8_t mode, uint8_t bpp) {
  const CaptureLock lock;
  if (!s_armed || s_buf == nullptr || primary == nullptr) return;
  if (++s_tick % s_every_n != 0) return;
#ifndef K1_B489_WS2816_V1
  if (secondary != nullptr) return;  // Legacy storage has only one edge slot.
#endif
  const uint8_t edges = (secondary != nullptr) ? 2u : 1u;
  if (s_bpp != 0 && (s_bpp != bpp || s_edges != edges)) return;
  const uint32_t f = s_frames;
  if (f >= K1_RTRACE_MAX_FRAMES || (int32_t)(millis() - s_end_ms) >= 0) {
    s_armed = false;
    return;
  }
  uint16_t px = led_count < K1_RTRACE_PX ? led_count : K1_RTRACE_PX;
  uint8_t* dst = &s_buf[(size_t)f * K1_RTRACE_FRAME_BYTES];
  const size_t copy = (size_t)px * (bpp == 16 ? 6U : 3U);
  memcpy(dst, primary, copy);
  memset(dst + copy, 0, K1_RTRACE_EDGE_BYTES - copy);
#ifdef K1_B489_WS2816_V1
  if (secondary != nullptr) {
    memcpy(dst + K1_RTRACE_EDGE_BYTES, secondary, copy);
    memset(dst + K1_RTRACE_EDGE_BYTES + copy, 0, K1_RTRACE_EDGE_BYTES - copy);
  } else {
    memset(dst + K1_RTRACE_EDGE_BYTES, 0, K1_RTRACE_EDGE_BYTES);
  }
#endif
  s_ms[f] = millis();
  s_mode[f] = mode;
  if (px < s_px) s_px = px;
  s_bpp = bpp;
  s_edges = edges;
  s_frames = f + 1;
}

void k1_render_trace_on_frame(const uint8_t* rgb_bytes, uint16_t led_count,
                              uint8_t lightshow_mode) {
  rtrace_store(rgb_bytes, nullptr, led_count, lightshow_mode, 8);
}

void k1_render_trace_on_frame16(const uint8_t* packed6, uint16_t led_count,
                                uint8_t lightshow_mode) {
  rtrace_store(packed6, nullptr, led_count, lightshow_mode, 16);
}

#ifdef K1_B489_WS2816_V1
void k1_render_trace_on_frame16_dual(const uint8_t* primary_packed6,
                                     const uint8_t* secondary_packed6,
                                     uint16_t led_count,
                                     uint8_t lightshow_mode) {
  if (primary_packed6 == nullptr || secondary_packed6 == nullptr) return;
  rtrace_store(primary_packed6, secondary_packed6, led_count, lightshow_mode, 16);
}
#endif

bool k1_render_trace_stim_active(void) {
  const CaptureLock lock;
  return s_stim && s_armed;
}

static void rtrace_status() {
  bool armed, buffer_ready;
  uint32_t frames;
  uint16_t every, px;
  uint8_t bpp, edges;
  {
    const CaptureLock lock;
    armed = s_armed;
    frames = s_frames;
    every = s_every_n;
    px = s_px;
    bpp = s_bpp;
    edges = s_edges;
    buffer_ready = s_buf != nullptr;
  }
  USBSerial.printf("[RTRACE] armed=%d frames=%lu capacity=%lu every=%u px=%u bpp=%u edges=%u buf=%s\n",
                   armed ? 1 : 0, (unsigned long)frames,
                   (unsigned long)K1_RTRACE_MAX_FRAMES, (unsigned)every,
                   (unsigned)px, (unsigned)bpp, (unsigned)edges,
                   buffer_ready ? "ok" : "NULL");
}

static void rtrace_arm(char* args) {
#ifdef K1_B489_WS2816_V1
  bool busy;
  { const CaptureLock lock; busy = s_drain_busy; }
  if (busy) { USBSerial.println("[RTRACE] ARM FAIL: drain busy"); return; }
  if (!rtrace_init_drain()) {
    USBSerial.println("[RTRACE] ARM FAIL: drain task unavailable");
    return;
  }
#endif
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
  {
    const CaptureLock lock;
    s_armed = false;
    s_frames = 0;
    s_tick = 0;
    s_px = K1_RTRACE_PX;
    s_bpp = 0;
    s_edges = 0;
    s_stim = stim;
    s_every_n = (uint16_t)every;
    s_end_ms = millis() + (uint32_t)seconds * 1000U;
    s_armed = true;
  }
  USBSerial.printf("[RTRACE] ARMED: %ld s, every %ld frames (cap %lu)%s\n",
                   seconds, every, (unsigned long)K1_RTRACE_MAX_FRAMES,
                   stim ? " stim=1" : "");
}

static void rtrace_write_dump() {
  uint32_t frames;
  {
    const CaptureLock lock;
    s_armed = false;
    frames = s_frames;
  }
  // Re-arm is excluded until this drain returns (serial ownership on legacy
  // builds, drain-busy on B489). Render continues with immutable capture data.
  if (s_buf == nullptr || frames == 0) {
    USBSerial.println("[RTRACE-BEGIN frames=0 crc32=0]");
    USBSerial.println("[RTRACE-END]");
    return;
  }
  // Legacy single-edge records keep their original 960-byte padded CRC stride.
  // Only the explicit edges=2 extension covers both edge slots (1920 bytes).
  uint32_t crc = 0;
  for (uint32_t f = 0; f < frames; ++f) {
    crc = esp_crc32_le(crc, &s_buf[(size_t)f * K1_RTRACE_FRAME_BYTES],
                      K1_RTRACE_EDGE_BYTES * s_edges);
  }
  const char* fmt = (s_bpp == 16) ? "rgb16hex" : "rgb8hex";
  if (s_edges == 2) {
    USBSerial.printf("[RTRACE-BEGIN frames=%lu every=%u px=%u fmt=%s bpp=%u edges=2 crc32=%08lx]\n",
                     (unsigned long)frames, (unsigned)s_every_n, (unsigned)s_px,
                     fmt, (unsigned)s_bpp, (unsigned long)crc);
  } else {
    USBSerial.printf("[RTRACE-BEGIN frames=%lu every=%u px=%u fmt=%s bpp=%u crc32=%08lx]\n",
                     (unsigned long)frames, (unsigned)s_every_n, (unsigned)s_px,
                     fmt, (unsigned)s_bpp, (unsigned long)crc);
  }
  static const char* hexc = "0123456789abcdef";
  // rgb8: 6 hex chars/px. rgb16 unpacked R16BE G16BE B16BE: 12 hex chars/px.
  static char line[K1_RTRACE_PX * 12 + 1];
  for (uint32_t f = 0; f < frames; f++) {
    USBSerial.printf("F,%lu,%lu,%u", (unsigned long)f, (unsigned long)s_ms[f],
                     (unsigned)s_mode[f]);
    for (uint8_t edge = 0; edge < s_edges; ++edge) {
      const uint8_t* src = &s_buf[(size_t)f * K1_RTRACE_FRAME_BYTES +
                                  (size_t)edge * K1_RTRACE_EDGE_BYTES];
      size_t nhex = 0;
      if (s_bpp == 16) {
        for (uint16_t i = 0; i < s_px; i++) {
          const uint8_t* p = src + (size_t)i * 6U;
          // packed wire: G_hi G_lo R_hi R_lo B_hi B_lo -> dump R16 G16 B16
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
      USBSerial.print(',');
      USBSerial.print(line);
    }
    USBSerial.println();
    if ((f & 0x3F) == 0x3F) vTaskDelay(1);
  }
  USBSerial.println("[RTRACE-END]");
}

#ifdef K1_B489_WS2816_V1
static void rtrace_drain_once() {
  rtrace_write_dump();
  const CaptureLock lock;
  s_drain_busy = false;
}
#endif

static void rtrace_dump() {
#ifdef K1_B489_WS2816_V1
  if (!rtrace_init_drain()) {
    USBSerial.println("[RTRACE] DUMP FAIL: drain task unavailable");
    return;
  }
  bool busy;
  {
    const CaptureLock lock;
    busy = s_drain_busy;
    if (!busy) {
      s_armed = false;
      s_drain_busy = true;
    }
  }
  if (busy) { USBSerial.println("[RTRACE] DUMP FAIL: drain busy"); return; }
  xTaskNotifyGive(s_drain_task);
#else
  rtrace_write_dump();
#endif
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
