#ifndef K1_BOOTLOOP_GUARD_H
#define K1_BOOTLOOP_GUARD_H

// K1 boot-loop guard (production-readiness N2b, item 1).
//
// Detects N consecutive crash-reboots before the device reaches a stable uptime and,
// on the Nth, enters a NON-DESTRUCTIVE safe mode: load_config() skips the persisted
// blob (the most common recoverable boot-crash cause) and boots compiled defaults —
// the config file is NEVER deleted and defaults are NEVER written back to flash. A
// clean uptime of K1_BOOTLOOP_STABLE_MS clears the streak.
//
// State lives in RTC_NOINIT memory (the var is defined in the .ino, exactly one TU):
// it survives a crash / panic / task-WDT / brownout reset but is re-seeded on a clean
// ESP_RST_POWERON. A `magic` + `version` validity pair covers BOTH RTC-RAM garbage
// after a full power loss AND a stale record from an older record layout, so an
// uninitialised or outdated counter can never spuriously trip safe mode.
//
// The decision logic (k1_bootloop_eval / k1_bootloop_mark_stable) is PURE — no I/O,
// no globals, no ESP headers — so it host-compiles and is pinned off-device by the
// golden-master oracle scripts/regression-harness/golden/oracle_k1_bootloop.py. The
// reset-reason classifier + the RTC var + the boot orchestration live behind
// #if defined(ESP_PLATFORM) and in the .ino.

#include <stdint.h>

#ifndef K1_BOOTLOOP_MAGIC
#define K1_BOOTLOOP_MAGIC 0x4B31424CUL  // "K1BL"
#endif
#ifndef K1_BOOTLOOP_VERSION
#define K1_BOOTLOOP_VERSION 1U  // RTC record layout version; bump invalidates a stale record
#endif
#ifndef K1_BOOTLOOP_THRESHOLD
#define K1_BOOTLOOP_THRESHOLD 4U  // safe mode once this many consecutive crash-reboots accrue
#endif
#ifndef K1_BOOTLOOP_STABLE_MS
#define K1_BOOTLOOP_STABLE_MS 10000U  // uptime (ms) that clears the crash streak
#endif

struct K1BootloopState {
  uint32_t magic;
  uint32_t version;
  uint32_t fail_count;
};

enum K1BootDecision {
  K1_BOOT_NORMAL = 0,
  K1_BOOT_SAFE_MODE = 1
};

// PURE decision core. `is_poweron` = clean power-on OR uninitialised RTC; `is_crash`
// = this reset followed a crash (panic / task-WDT / int-WDT / brownout). Re-seeds the
// record (zeroing the streak) when the magic OR version is wrong, or on a clean
// power-on — so RTC garbage and stale layouts can never trip safe mode — otherwise
// increments on a crash and returns whether to boot safe mode. No I/O — host-testable.
static inline enum K1BootDecision k1_bootloop_eval(struct K1BootloopState* s,
                                                   int is_poweron,
                                                   int is_crash,
                                                   uint32_t threshold) {
  if (s->magic != K1_BOOTLOOP_MAGIC || s->version != K1_BOOTLOOP_VERSION || is_poweron) {
    s->magic = K1_BOOTLOOP_MAGIC;
    s->version = K1_BOOTLOOP_VERSION;
    s->fail_count = 0;
    return K1_BOOT_NORMAL;
  }
  if (is_crash) {
    s->fail_count++;
  }
  return (s->fail_count >= threshold) ? K1_BOOT_SAFE_MODE : K1_BOOT_NORMAL;
}

// Clear the crash streak after a stable uptime (called once from loop()).
static inline void k1_bootloop_mark_stable(struct K1BootloopState* s) {
  s->fail_count = 0;
}

#if defined(ESP_PLATFORM) || defined(ARDUINO)
#include "esp_system.h"  // esp_reset_reason / esp_reset_reason_t
#include "esp_attr.h"    // RTC_NOINIT_ATTR

// An intentional software restart (restore_defaults / reboot) is ESP_RST_SW and must
// NOT count as a crash; deep-sleep / SDIO / USB / JTAG / external resets are likewise
// benign. Only true faults accrue toward the boot-loop threshold.
static inline int k1_bootloop_reason_is_crash(esp_reset_reason_t r) {
  return r == ESP_RST_PANIC || r == ESP_RST_TASK_WDT ||
         r == ESP_RST_INT_WDT || r == ESP_RST_WDT || r == ESP_RST_BROWNOUT;
}
#endif  // ESP_PLATFORM

#endif  // K1_BOOTLOOP_GUARD_H
