#pragma once
// ─────────────────────────────────────────────────────────────────────────────
// K1 OTA receiver (lane N7) — DEFAULT-OFF, flag-gated DRAFT.
//
// Captain decision D3: this file is flag-OFF scaffold ONLY. It is NOT enabled in
// any shipping build (SB_ENABLE_OTA defaults 0 in constants.h). Enabling OTA in
// the field is blocked on THREE explicit Captain STOPs (see the D3 memo):
//   (a) is on-device OTA in v1 scope at all?
//   (b) image-signing key custody (no key/secret lives in this repo);
//   (c) a distribution / update server (none exists; none is created here).
//
// N7-ENABLE PREREQUISITES (do at enablement, not now):
//   - Pin CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y in sdkconfig.defaults so the
//     bootloader arms rollback-on-failed-boot. k1_ota_mark_app_valid_after_boot()
//     below cancels that pending rollback once a boot is proven healthy.
//   - Use a partition table with two app/OTA slots (default_16MB.csv must gain
//     ota_0/ota_1 + otadata). Without it esp_ota_get_next_update_partition()
//     returns nullptr at runtime (k1_ota_begin() returns false) — link is fine.
//   - Wire a real chunk transport: the shipping product has NO AP webserver
//     (network/sb_*.cpp is held out of k1_hardware pending the wireless A/B), so
//     ingress here is a serial-command DRAFT. The HTTP/body ingress is the
//     enablement-time wiring once the wireless stack is re-admitted.
// ─────────────────────────────────────────────────────────────────────────────

#include "constants.h"  // SB_ENABLE_OTA
#include <stddef.h>
#include <stdint.h>

#if SB_ENABLE_OTA

// Begin a new OTA session into the next OTA update partition. total_size may be
// 0 (treated as OTA_SIZE_UNKNOWN). Returns true on success.
bool k1_ota_begin(size_t total_size);

// Stream a chunk into the active session. Returns true on success; on failure
// the session is aborted. Every byte streamed here is also folded into a running
// SHA-256 used for signature verification at k1_ota_end().
bool k1_ota_write(const uint8_t* data, size_t len);

// Supply the detached image signature for the active session. This is an
// RSA-3072 / PKCS#1 v1.5 signature over the SHA-256 of the exact image bytes
// streamed via k1_ota_write(), produced offline by the operator's PRIVATE key
// (e.g. `openssl dgst -sha256 -sign k1_ota_signing_PRIVATE.pem image.bin`).
// len must equal the RSA modulus size (384 bytes for RSA-3072). Returns false if
// no session is open or the length is out of range. Without a signature that
// verifies against the embedded PUBLIC key, k1_ota_end() REFUSES the image.
// This REPLACES any accumulated signature (natural for a whole-body HTTP transport).
bool k1_ota_set_signature(const uint8_t* sig, size_t len);

// Append a fragment of the detached signature to the active session. Provided
// because a line-based serial transport cannot carry a 384-byte signature in one
// frame (the command buffer is short); the operator streams the signature across
// several fragments which are concatenated in order. Returns false if no session
// is open or the running total would exceed the signature buffer.
bool k1_ota_append_signature(const uint8_t* part, size_t len);

// Finalise: validate the written image AND verify its detached signature against
// the embedded operator PUBLIC key. The boot partition is switched ONLY if the
// signature verifies. Returns true on success — the caller is expected to reboot
// to run it. Any unsigned, mis-signed, or tampered image is rejected here and the
// session is aborted; the running image is untouched.
bool k1_ota_end();

// Abort the active session and release the handle.
void k1_ota_abort();

// True while an OTA session is open.
bool k1_ota_active();

// Serial ingress (DRAFT): handles the `ota_*` verbs. Returns true iff handled.
// Same contract as the serial_cmd_dispatch_* family in serial_cmd_handlers.cpp.
bool serial_cmd_dispatch_ota(const char* command_type, char* command_data);

// Boot-health / anti-brick: cancel the bootloader's pending rollback once the
// app has proven it boots. Safe to call unconditionally — it is a no-op unless
// the running slot is in the PENDING_VERIFY state (i.e. rollback was armed).
void k1_ota_mark_app_valid_after_boot();

#endif  // SB_ENABLE_OTA
