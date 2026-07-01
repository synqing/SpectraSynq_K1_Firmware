// K1 OTA receiver (lane N7) — DEFAULT-OFF, flag-gated DRAFT. See k1_ota.h for
// the Captain decision D3 framing and the N7-enable prerequisites. The ENTIRE
// translation unit is behind #if SB_ENABLE_OTA, so with the flag OFF (every
// shipping build) this compiles to an empty object: zero behaviour change.
#include "k1_ota.h"

#if SB_ENABLE_OTA

#include "globals.h"  // USBSerial
#include "k1_ota_signing_public_key.h"  // K1_OTA_SIGNING_PUBLIC_KEY_PEM (verify-only)
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "mbedtls/pk.h"
#include "mbedtls/sha256.h"
#include "mbedtls/base64.h"
#include <string.h>
#include <stdlib.h>

namespace {
// An RSA-3072 signature is 384 bytes; this buffer keeps headroom for larger keys.
// mbedtls_pk_verify() itself rejects any signature whose length does not match the
// key modulus, so this bound is purely a buffer guard.
constexpr size_t K1_OTA_SIG_MAX = 512;

esp_ota_handle_t g_ota_handle = 0;
const esp_partition_t* g_ota_part = nullptr;
bool g_ota_open = false;
size_t g_ota_written = 0;

// Running SHA-256 over the streamed image bytes, plus the detached signature that
// must verify against the embedded PUBLIC key before the boot partition is flipped.
mbedtls_sha256_context g_ota_sha;
uint8_t g_ota_sig[K1_OTA_SIG_MAX];
size_t g_ota_sig_len = 0;
bool g_ota_sig_present = false;

// Reset the per-session crypto state. Frees any live SHA context first.
void k1_ota_reset_crypto() {
  mbedtls_sha256_free(&g_ota_sha);
  g_ota_sig_len = 0;
  g_ota_sig_present = false;
  memset(g_ota_sig, 0, sizeof(g_ota_sig));
}

// Verify the streamed image's SHA-256 against the stored detached signature using
// the embedded operator PUBLIC key (RSA-3072, PKCS#1 v1.5). Returns true ONLY on a
// cryptographically valid signature. No RNG is needed for verification.
bool k1_ota_verify_signature(const uint8_t* digest, size_t digest_len) {
  if (!g_ota_sig_present || g_ota_sig_len == 0) {
    return false;  // no signature supplied — refuse
  }
  mbedtls_pk_context pk;
  mbedtls_pk_init(&pk);
  // Length passed to the PEM parser MUST include the terminating NUL.
  int rc = mbedtls_pk_parse_public_key(
      &pk, reinterpret_cast<const unsigned char*>(K1_OTA_SIGNING_PUBLIC_KEY_PEM),
      sizeof(K1_OTA_SIGNING_PUBLIC_KEY_PEM));
  if (rc != 0) {
    mbedtls_pk_free(&pk);
    return false;  // embedded key failed to parse — fail closed
  }
  if (mbedtls_pk_get_type(&pk) != MBEDTLS_PK_RSA) {
    mbedtls_pk_free(&pk);
    return false;  // unexpected key type — fail closed
  }
  rc = mbedtls_pk_verify(&pk, MBEDTLS_MD_SHA256, digest, digest_len, g_ota_sig,
                         g_ota_sig_len);
  mbedtls_pk_free(&pk);
  return rc == 0;
}
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
  // Arm the running image hash and clear any prior signature.
  k1_ota_reset_crypto();
  mbedtls_sha256_init(&g_ota_sha);
  if (mbedtls_sha256_starts(&g_ota_sha, /*is224=*/0) != 0) {
    k1_ota_abort();
    return false;
  }
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
  // Fold the exact streamed bytes into the running SHA-256 used for verification.
  if (mbedtls_sha256_update(&g_ota_sha, data, len) != 0) {
    k1_ota_abort();
    return false;
  }
  g_ota_written += len;
  return true;
}

bool k1_ota_set_signature(const uint8_t* sig, size_t len) {
  if (!g_ota_open || sig == nullptr) {
    return false;
  }
  if (len == 0 || len > K1_OTA_SIG_MAX) {
    return false;
  }
  memcpy(g_ota_sig, sig, len);
  g_ota_sig_len = len;
  g_ota_sig_present = true;
  return true;
}

bool k1_ota_end() {
  if (!g_ota_open) {
    return false;
  }

  // Finalise the running image hash BEFORE releasing the OTA handle, so the digest
  // covers exactly the bytes that were written.
  uint8_t digest[32];
  const bool sha_ok = (mbedtls_sha256_finish(&g_ota_sha, digest) == 0);

  // esp_ota_end() runs the IDF basic-format/integrity check (appended SHA + magic)
  // and releases the handle. On this precompiled arduino-esp32 build it does NOT
  // perform signature verification (CONFIG_SECURE_SIGNED_ON_UPDATE is compiled out
  // of the prebuilt libbootloader_support.a) — that is precisely why the
  // application-level RSA check below is the security boundary.
  const esp_err_t end_err = esp_ota_end(g_ota_handle);
  g_ota_open = false;

  if (!sha_ok || end_err != ESP_OK) {
    g_ota_part = nullptr;  // integrity failed — do NOT flip boot partition
    k1_ota_reset_crypto();
    return false;
  }

  // SECURITY BOUNDARY: refuse to activate any image whose detached signature does
  // not verify against the embedded operator PUBLIC key. Fail closed.
  if (!k1_ota_verify_signature(digest, sizeof(digest))) {
    g_ota_part = nullptr;  // unsigned / mis-signed / tampered — REJECT, do not boot
    k1_ota_reset_crypto();
    return false;
  }

  const esp_err_t set_err = esp_ota_set_boot_partition(g_ota_part);
  g_ota_part = nullptr;
  k1_ota_reset_crypto();
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
  k1_ota_reset_crypto();
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
  } else if (strcmp(command_type, "ota_datab64") == 0) {
    // Framed serial chunk ingress (device-proof): one base64 line -> image bytes.
    // Static decode buffer keeps this off the heap. The full AP/HTTP body ingress
    // remains enablement-time wiring; this is sufficient to push a good-vs-unsigned
    // image over serial for the signature-rejection proof.
    static uint8_t decoded[1024];
    if (command_data == nullptr || command_data[0] == '\0') {
      USBSerial.println("[ota] datab64 fail — empty");
      return true;
    }
    size_t olen = 0;
    const int rc = mbedtls_base64_decode(
        decoded, sizeof(decoded), &olen,
        reinterpret_cast<const unsigned char*>(command_data), strlen(command_data));
    if (rc != 0) {
      USBSerial.printf("[ota] datab64 fail — decode rc=%d\n", rc);
      return true;
    }
    const bool ok = k1_ota_write(decoded, olen);
    USBSerial.printf("[ota] datab64 %s (+%u bytes, total=%u)\n",
                     ok ? "ok" : "fail", (unsigned)olen, (unsigned)g_ota_written);
    return true;
  } else if (strcmp(command_type, "ota_sigb64") == 0) {
    // Supply the detached RSA-3072 signature (base64) for the active session.
    if (command_data == nullptr || command_data[0] == '\0') {
      USBSerial.println("[ota] sigb64 fail — empty");
      return true;
    }
    static uint8_t sigbuf[K1_OTA_SIG_MAX];
    size_t olen = 0;
    const int rc = mbedtls_base64_decode(
        sigbuf, sizeof(sigbuf), &olen,
        reinterpret_cast<const unsigned char*>(command_data), strlen(command_data));
    if (rc != 0) {
      USBSerial.printf("[ota] sigb64 fail — decode rc=%d\n", rc);
      return true;
    }
    const bool ok = k1_ota_set_signature(sigbuf, olen);
    USBSerial.printf("[ota] sigb64 %s (%u bytes)\n", ok ? "ok" : "fail",
                     (unsigned)olen);
    return true;
  } else if (strcmp(command_type, "ota_end") == 0) {
    const bool ok = k1_ota_end();
    USBSerial.printf("[ota] end %s — %s\n", ok ? "ok" : "REJECT",
                     ok ? "signature verified, reboot to run the new image"
                        : "image refused (unsigned/mis-signed/tampered or no slot)");
    return true;
  }
  // NOTE: the AP/HTTP body chunk ingress remains enablement-time wiring; the
  // base64 serial verbs above are the device-proof transport. k1_ota_write() and
  // k1_ota_set_signature() are the link-proven entry points for the HTTP wiring.
  return false;
}

#endif  // SB_ENABLE_OTA
