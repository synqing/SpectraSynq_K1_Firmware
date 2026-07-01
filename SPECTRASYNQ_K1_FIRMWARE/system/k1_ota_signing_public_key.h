#pragma once
// ─────────────────────────────────────────────────────────────────────────────
// K1 OTA image-signing PUBLIC key — embedded verify key (lane N7).
//
// PROVENANCE: this is the exact byte content of certs/k1_ota_signing_PUBLIC.pem
// (RSA-3072, Secure Boot v2 keypair scheme). Committing a PUBLIC key is safe —
// it can only VERIFY, never sign. The matching PRIVATE key is a Class-D operator
// secret held OUTSIDE this repository and is never referenced by the firmware.
//
// This header is #included ONLY from inside the `#if SB_ENABLE_OTA` block in
// system/k1_ota.cpp, so with the shipping flag OFF it is never compiled and the
// k1_hardware binary is byte-unchanged.
//
// The device parses this PEM at OTA-finalise time (mbedtls_pk_parse_public_key)
// and uses it to verify a detached RSA-3072 / PKCS#1 v1.5 SHA-256 signature over
// the received image before any boot-partition switch. See k1_ota.cpp.
// ─────────────────────────────────────────────────────────────────────────────

// NUL-terminated PEM. mbedtls_pk_parse_public_key() requires the length passed to
// INCLUDE the terminating NUL byte, i.e. pass sizeof(K1_OTA_SIGNING_PUBLIC_KEY_PEM).
static const char K1_OTA_SIGNING_PUBLIC_KEY_PEM[] =
    "-----BEGIN PUBLIC KEY-----\n"
    "MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAr0C3uNTLvpcDW3/RVPxE\n"
    "UXIFXdB8cr/YoSYNgIoJZXrZ7NvpiWvSY81vywMZba6tZ8TNzllj1bGGZQw+0ikN\n"
    "qF2WXRUqVoDTOIqLeL1AZnIunf6Q0vEwpZqwAeJwkC/km/w3IueNzBlf00mV1cWI\n"
    "J7gOMFb5/zTpXU99DSzlGD0Q8AX9AY98TrLEOLOOV+bkYgMvz7k1MHBmn9nk1cDX\n"
    "QjvfSuJVEKmHIODMW11eknLJ5CCc+ywEZf1jyq/ePT46/HXCzxy7iqjvSel3MwpQ\n"
    "okIwMuoWDAnt0bhWlYoBDzdajEtSk9edBynmQct3NzMLgsPEZEijF7hdaecq6PGn\n"
    "79YsP0IyfsNMG03VPkfGHLf6F/L6GFgZnN/htclMDD7aOLeQoWVwganj+0iG0rt5\n"
    "VB2s9gjn0rKiqxoMvLXH01zIousQrU9VH1YYwqEOpuCzPD+C4/a95ujuFtzXZHoE\n"
    "8NZoMalg4SoCsK9OTk2z7+3RTCCloSrNyIUp26MhdNqXAgMBAAE=\n"
    "-----END PUBLIC KEY-----\n";
