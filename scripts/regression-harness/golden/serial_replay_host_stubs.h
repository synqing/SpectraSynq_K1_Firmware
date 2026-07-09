// ============================================================================
// serial_replay_host_stubs.h — HOST-ONLY symbol stubs for oracle_serial_replay
// ============================================================================
// The serial-command->output replay oracle (oracle_serial_replay.py, Phase A
// Lane 2 S3.0) drives the REAL parse_command() by #including serial_menu.h. That
// compiles the WHOLE 188 KB header — not just parse_command — so every symbol the
// header's OTHER functions reference (init_serial, dump_info, cmd_reset_reason,
// the serial_cmd_table.def destructive handlers, the I2S_PORT echo) must resolve.
//
// NONE of those functions are in the S3.0 corpus (24->23 pure CONFIG setters); they
// only need to COMPILE + LINK. This header supplies them as no-op / macro stubs,
// included by the driver BEFORE globals.h/serial_menu.h. Design §2/§7 hazard #1
// explicitly anticipates stubbing this set (FIRMWARE_VERSION/.ino coupling, the
// pgmspace shims, the device handlers).
//
// Two hard rules this header obeys:
//   1. It is included ONLY by the serial_replay driver (gated -DK1_SERIAL_REPLAY_HOST
//      and a manual include in the driver). It never enters any other oracle's TU,
//      so the other 6 goldens stay byte-identical.
//   2. It must NOT clash with a real definition. serial_menu.h does NOT
//      transitively include bridge_fs.h / system.h / presets.h / i2s_audio.h
//      (recon §4), so these are the SOLE definitions of the device handlers.
//      save_config / save_config_delayed / reboot / set_preset /
//      check_current_function are defined in the DRIVER (not here) because the
//      driver also records their fired-flags.
//
// NON-SHIPPING. Host-only. Absent from every PlatformIO env.
// ============================================================================
#ifndef SERIAL_REPLAY_HOST_STUBS_H
#define SERIAL_REPLAY_HOST_STUBS_H

#include <cstdint>
#include <cstring>

// --- FIRMWARE_VERSION (.ino #define; serial_menu.h init_serial/dump_info echo it)
// Value mirrors the .ino's current 40103 so the banner text, IF it were ever
// captured, matches device. init_serial/dump_info are NOT in the corpus, so this
// only needs to make the header compile.
#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION 40103
#endif

// --- AVR pgmspace shims (serial_print_palette_line: pgm_read_ptr + strcpy_P) ---
// On host, PROGMEM is plain memory (stubs/Arduino.h #defines PROGMEM empty), so a
// flash read is a normal dereference and strcpy_P is strcpy.
#ifndef pgm_read_ptr
#define pgm_read_ptr(addr) (*(const void* const*)(addr))
#endif
#ifndef strcpy_P
#define strcpy_P(dst, src) strcpy((dst), (const char*)(src))
#endif

// --- ESP-IDF I2S port id (constants.h: #define I2S_PORT I2S_NUM_0; the bare
//     `dump_info` body echoes I2S_PORT). Provide the enum value the macro names.
#ifndef I2S_NUM_0
#define I2S_NUM_0 0
#endif

// --- ESP reset-reason API (cmd_reset_reason switch in serial_menu.h:2098) -------
// Not in the corpus; only needs to compile/link.
#ifndef ESP_RST_UNKNOWN
enum esp_reset_reason_t {
  ESP_RST_UNKNOWN = 0, ESP_RST_POWERON, ESP_RST_EXT, ESP_RST_SW, ESP_RST_PANIC,
  ESP_RST_INT_WDT, ESP_RST_TASK_WDT, ESP_RST_WDT, ESP_RST_DEEPSLEEP,
  ESP_RST_BROWNOUT, ESP_RST_SDIO
};
static inline esp_reset_reason_t esp_reset_reason() { return ESP_RST_POWERON; }
#endif

// --- device-handler forward symbols referenced by serial_menu.h's whole body ---
// (init_serial / dump_info / the serial_cmd_table.def destructive handlers /
//  set_chroma_profile). None reachable from the S3.0 corpus; no-op for link.
// raw_dump_request is an int flag (i2s_audio.h on device); a writable global here.
static inline void print_chip_id() {}
static inline void factory_reset() {}
static inline void restore_defaults() {}
static inline void clear_noise_cal() {}
// blocking_flash takes a CRGB16 colour (real inline def at led_utilities.h:1129,
// which serial_menu.h does NOT pull in). cmd_identify() calls it with a CRGB16
// literal. Stub by template to match without naming the FastLED-host colour type.
template <typename T> static inline void blocking_flash(const T& /*colour*/) {}
inline int raw_dump_request = 0;
// apply_chroma_profile is CONFIG-only on device (set_chroma_profile setter, which
// IS excluded from the corpus as reboot-bearing). Stub returns "no note-offset
// change" so the excluded branch links without rebooting. Signature must match the
// serial_menu.h call: bool apply_chroma_profile(<profile>). The profile arg type
// is an enum from config_types.h (already included via globals.h before this is
// USED); we take it by a templated param to avoid naming the enum here.
template <typename T> static inline bool apply_chroma_profile(T /*profile*/) { return false; }

// --- k1_effect_queue.* config symbols ------------------------------------------
// The k1_queue_* config setters/getters (k1_effect_queue.h:134-140) are stubbed as
// EXTERNAL (non-inline) definitions in the driver (oracle_serial_replay.py), next to
// the other k1_queue_* externals (k1_queue_any_armed etc.) — NOT here. Reason: the
// queue command handlers were lifted out of serial_menu.h (driver TU) into
// serial_cmd_handlers.cpp (a SEPARATE oracle TU). A `static inline` stub here has
// internal linkage (invisible to the handlers TU); a plain `inline` is only emitted
// by a TU that odr-uses it, so the setters used ONLY by the handlers TU (which sees
// just the declaration via k1_effect_queue.h) are emitted by nobody -> link error.
// A single guaranteed-emitted external definition in the driver binds BOTH TUs. The
// queue family is not in the replay corpus, so the stub values never affect the golden.

#endif  // SERIAL_REPLAY_HOST_STUBS_H
