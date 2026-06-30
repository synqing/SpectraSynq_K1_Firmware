// K1 OTA receiver (lane N7) — DEFAULT-OFF, flag-gated DRAFT. See k1_ota.h for
// the Captain decision D3 framing and the N7-enable prerequisites. The ENTIRE
// translation unit is behind #if SB_ENABLE_OTA, so with the flag OFF (every
// shipping build) this compiles to an empty object: zero behaviour change.
#include "k1_ota.h"

#if SB_ENABLE_OTA

#include "globals.h"  // USBSerial
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include <string.h>
#include <stdlib.h>

namespace {
esp_ota_handle_t g_ota_handle = 0;
const esp_partition_t* g_ota_part = nullptr;
bool g_ota_open = false;
size_t g_ota_written = 0;
}  // namespace

bool k1_ota_active() {
  return g_ota_open;
}

bool k1_ota_begin(size_t total_size) {
  if (g_ota_open) {
    return false;  // a session is already open
  }
  const esp_partition_t* next = esp_ota_get_next_update_partition(nullptr);
  if (next == nullptr) {
    return false;  // no OTA slot in the partition table (N7-enable prerequisite)
  }
  const size_t image_size = total_size ? total_size : OTA_SIZE_UNKNOWN;
  if (esp_ota_begin(next, image_size, &g_ota_handle) != ESP_OK) {
    return false;
  }
  g_ota_part = next;
  g_ota_open = true;
  g_ota_written = 0;
  return true;
}

bool k1_ota_write(const uint8_t* data, size_t len) {
  if (!g_ota_open || data == nullptr || len == 0) {
    return false;
  }
  if (esp_ota_write(g_ota_handle, data, len) != ESP_OK) {
    k1_ota_abort();
    return false;
  }
  g_ota_written += len;
  return true;
}

bool k1_ota_end() {
  if (!g_ota_open) {
    return false;
  }
  const esp_err_t end_err = esp_ota_end(g_ota_handle);
  g_ota_open = false;
  if (end_err != ESP_OK) {
    g_ota_part = nullptr;  // image failed validation — do NOT flip boot partition
    return false;
  }
  const esp_err_t set_err = esp_ota_set_boot_partition(g_ota_part);
  g_ota_part = nullptr;
  return set_err == ESP_OK;
}

void k1_ota_abort() {
  if (!g_ota_open) {
    return;
  }
  esp_ota_abort(g_ota_handle);
  g_ota_open = false;
  g_ota_part = nullptr;
  g_ota_written = 0;
}

void k1_ota_mark_app_valid_after_boot() {
  // Cancels the bootloader's pending-rollback flag once we have proven a healthy
  // boot. Returns ESP_ERR_OTA_ROLLBACK_INVALID_STATE (ignored) when the running
  // app is not PENDING_VERIFY, i.e. rollback was never armed — so this is a
  // harmless no-op on a normally-flashed image.
  (void)esp_ota_mark_app_valid_cancel_rollback();
}

bool serial_cmd_dispatch_ota(const char* command_type, char* command_data) {
  if (strcmp(command_type, "ota_begin") == 0) {
    const size_t sz = (command_data && command_data[0] != '\0')
                          ? (size_t)strtoul(command_data, nullptr, 10)
                          : 0;
    const bool ok = k1_ota_begin(sz);
    USBSerial.printf("[ota] begin %s (size=%u)\n", ok ? "ok" : "fail", (unsigned)sz);
    return true;
  } else if (strcmp(command_type, "ota_status") == 0) {
    USBSerial.printf("[ota] active=%d written=%u\n", (int)g_ota_open,
                     (unsigned)g_ota_written);
    return true;
  } else if (strcmp(command_type, "ota_abort") == 0) {
    k1_ota_abort();
    USBSerial.println("[ota] aborted");
    return true;
  } else if (strcmp(command_type, "ota_end") == 0) {
    const bool ok = k1_ota_end();
    USBSerial.printf("[ota] end %s — reboot to run the new image\n",
                     ok ? "ok" : "fail");
    return true;
  }
  // NOTE (DRAFT): raw image-chunk streaming (`ota_write`) needs a binary/base64
  // transport that a line-based serial parser cannot carry cleanly; the chunk
  // ingress is enablement-time wiring (HTTP body or framed serial). k1_ota_write()
  // is exposed + link-proven for that wiring.
  return false;
}

#endif  // SB_ENABLE_OTA
