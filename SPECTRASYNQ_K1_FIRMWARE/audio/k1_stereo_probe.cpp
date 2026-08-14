// k1_stereo_probe.cpp — Stage 2 IM69D130 stereo capture instrument.
// See k1_stereo_probe.h. Gate sits BEFORE every include so this TU preprocesses
// to NOTHING in any env without K1_MIC_IM69D_STEREO_V1 (no global-ctor leak —
// production byte-identity preserved by construction).
#ifdef K1_MIC_IM69D_STEREO_V1

#include <Arduino.h>
#include <string.h>
#include <stdlib.h>
#include "esp_crc.h"
#include "esp32-hal-psram.h"
#include "../system/globals.h"
#include "k1_stereo_probe.h"

// 24 s ceiling: 24 s × 12800 Hz × 2 ch × 2 B = 2,457,600 B of 8 MB PSRAM.
static const uint32_t K1_SCAP_MAX_SECONDS = 24;

static int16_t*  s_buf = nullptr;          // PSRAM, interleaved ESP-IDF RIGHT/LEFT frames
static uint32_t  s_capacity_frames = 0;    // total frames the buffer can hold
static uint32_t  s_target_frames = 0;      // armed capture length
static volatile uint32_t s_filled_frames = 0;
static volatile bool s_armed = false;

void k1_stereo_probe_init() {
  if (s_buf != nullptr) return;
  const uint32_t sr = (CONFIG.SAMPLE_RATE > 0) ? (uint32_t)CONFIG.SAMPLE_RATE : 12800U;
  s_capacity_frames = K1_SCAP_MAX_SECONDS * sr;
  s_buf = (int16_t*)ps_malloc((size_t)s_capacity_frames * 2U * sizeof(int16_t));
  if (s_buf == nullptr) {
    // Loud failure per the invisible-kill-switch rule: a probe that silently
    // has no buffer would report "0 frames" and read as a quiet room.
    USBSerial.println("[SCAP] INIT FAIL: ps_malloc returned NULL — capture disabled");
    s_capacity_frames = 0;
  } else {
    USBSerial.printf("[SCAP] INIT PASS: %lu frames capacity (%lu s)\n",
                     (unsigned long)s_capacity_frames, (unsigned long)K1_SCAP_MAX_SECONDS);
  }
}

void k1_stereo_probe_on_chunk(const int16_t* interleaved, uint16_t frames) {
  if (!s_armed || s_buf == nullptr) return;
  uint32_t filled = s_filled_frames;
  if (filled >= s_target_frames) { s_armed = false; return; }
  uint32_t take = s_target_frames - filled;
  if (take > frames) take = frames;
  memcpy(&s_buf[(size_t)filled * 2U], interleaved, (size_t)take * 2U * sizeof(int16_t));
  s_filled_frames = filled + take;
  if (s_filled_frames >= s_target_frames) s_armed = false;
}

static void scap_status() {
  USBSerial.printf("[SCAP] armed=%d filled=%lu target=%lu capacity=%lu buf=%s "
                   "idf_right_rms=%.1f idf_right_peak=%u "
                   "idf_left_rms=%.1f idf_left_peak=%u\n",
                   s_armed ? 1 : 0,
                   (unsigned long)s_filled_frames,
                   (unsigned long)s_target_frames,
                   (unsigned long)s_capacity_frames,
                   (s_buf != nullptr) ? "ok" : "NULL",
                   (double)im69d_raw_i16_rms, (unsigned)im69d_raw_i16_abs_peak,
                   (double)im69d_left_raw_i16_rms, (unsigned)im69d_left_raw_i16_abs_peak);
}

static void scap_arm(uint32_t seconds) {
  if (s_buf == nullptr) { USBSerial.println("[SCAP] ARM FAIL: no buffer"); return; }
  if (seconds < 1) seconds = 1;
  if (seconds > K1_SCAP_MAX_SECONDS) seconds = K1_SCAP_MAX_SECONDS;
  const uint32_t sr = (CONFIG.SAMPLE_RATE > 0) ? (uint32_t)CONFIG.SAMPLE_RATE : 12800U;
  s_armed = false;                 // order matters: stop the writer before reset
  s_filled_frames = 0;
  s_target_frames = seconds * sr;
  if (s_target_frames > s_capacity_frames) s_target_frames = s_capacity_frames;
  s_armed = true;
  USBSerial.printf("[SCAP] ARMED: %lu frames (%lu s)\n",
                   (unsigned long)s_target_frames, (unsigned long)seconds);
}

static void scap_dump() {
  if (s_buf == nullptr || s_filled_frames == 0) {
    USBSerial.println("[SCAP-BEGIN len=0 crc32=0]");
    USBSerial.println("[SCAP-END]");
    return;
  }
  s_armed = false;  // never dump a moving buffer
  const uint32_t frames = s_filled_frames;
  const size_t total_bytes = (size_t)frames * 2U * sizeof(int16_t);
  const uint32_t crc = esp_crc32_le(0, (const uint8_t*)s_buf, total_bytes);
  // Header carries everything the decoder needs; sample_rate pins the time axis.
  USBSerial.printf("[SCAP-BEGIN len=%u crc32=%08lx frames=%lu sr=%lu fmt=le_i16_RL]\n",
                   (unsigned)total_bytes, (unsigned long)crc,
                   (unsigned long)frames, (unsigned long)CONFIG.SAMPLE_RATE);
  const uint8_t* bytes = (const uint8_t*)s_buf;
  char line[129];
  for (size_t off = 0; off < total_bytes; off += 64) {
    size_t n = total_bytes - off;
    if (n > 64) n = 64;
    for (size_t i = 0; i < n; i++) {
      static const char* hex = "0123456789abcdef";
      line[i * 2]     = hex[bytes[off + i] >> 4];
      line[i * 2 + 1] = hex[bytes[off + i] & 0x0F];
    }
    line[n * 2] = '\0';
    USBSerial.println(line);
    // Feed the idle task / watchdog every 256 lines (~16 KiB) — the dump is
    // post-leg and allowed to starve audio, but never the WDT (N2 lesson).
    if (((off >> 6) & 0xFF) == 0xFF) vTaskDelay(1);
  }
  USBSerial.println("[SCAP-END]");
}

bool k1_stereo_probe_dispatch(const char* command_type, char* command_data) {
  if (strcmp(command_type, "scap_arm") == 0) {
    scap_arm((uint32_t)atoi(command_data));
    return true;
  }
  if (strcmp(command_type, "scap_status") == 0) {
    scap_status();
    return true;
  }
  if (strcmp(command_type, "scap_dump") == 0) {
    scap_dump();
    return true;
  }
  return false;
}

#endif  // K1_MIC_IM69D_STEREO_V1
