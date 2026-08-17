/*----------------------------------------
  K1 FILESYSTEM ACCESS
  ----------------------------------------*/

#include "globals.h"
#include "constants.h"
#include "Palettes.h" // Include for gGradientPaletteCount
#include "k1_effect_queue.h" // K1_PRESET_SLOTS_FILE (factory_reset enumeration)
#include "k1_show_state.h"   // K1_SHOW_STATE_FILE + boot restore after load_config
#include "bridge_fs_config_codec.h" // N1: ConfigBlobHeader + bridge_fs_classify_config()
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h" // registry_sanitize_persisted() (R2b NVS sanitiser)
#endif
#include <esp_heap_caps.h> // heap_caps_* — internal-RAM precondition for LittleFS opens
#include "k1_persistence_request.h"

extern void reboot(); // system.h

#ifdef K1_MIC_IM73D_PDM_V1
// PDM persistence namespace (cal 2026-07-03, config 2026-07-04): everything the
// PDM build persists lives in its OWN files (/CONFIG_PDM_*.BIN, /cal_profile_pdm.bin)
// so the SPH0645 baseline (/CONFIG_*.BIN, /cal_profile.bin, /noise_cal.bin) stays
// frozen and untouchable on disk. Same record formats; different namespace.
// PDM noise_samples persist INSIDE the cal profile (the cal-profile save path) —
// there is deliberately no /noise_cal_pdm.bin.
#define CAL_PROFILE_FILE "/cal_profile_pdm.bin"
#elif defined(K1_MIC_IM69D_PDM_V1)
// IM69D130 persistence namespace (2026-08-05): MUST stay distinct from IM73D
// /cal_profile_pdm.bin — shared namespace would poison the IM73D cal profile.
#define CAL_PROFILE_FILE "/cal_profile_im69d.bin"
#else
#define CAL_PROFILE_FILE "/cal_profile.bin"
#endif
#define CAL_PROFILE_MAGIC 0x314C4143UL
#define CAL_PROFILE_VERSION 1U

// --- Internal-RAM precondition for LittleFS writes (crash-safety, 2026-07-05) ---
// A LittleFS.open() allocates a stdio FILE plus its recursive mutex (a FreeRTOS
// queue — INTERNAL RAM only) plus the lfs file cache. If the internal 8-bit heap
// cannot satisfy the mutex allocation, newlib calls abort() from INSIDE fopen()
// (newlib locks.c: lock_init_generic) — this fires BEFORE open() returns, so the
// `if (!file)` guards below can never catch it; the device hard-reboots.
// Root incident: bench K1 (k1_bench_im73d_ble) aborted on core 0 during the first
// accepted noise-cal after config persistence was un-frozen (e2b62b5). BLE is
// pinned to core 0 and leaves internal DRAM tight, so save_config()'s open aborted.
// This precondition turns that fatal path into a graceful, logged, retryable
// deferral. It is inert on a healthy device (tens of KB largest free block).
#ifndef K1_FS_MIN_INTERNAL_BLOCK
#define K1_FS_MIN_INTERNAL_BLOCK 8192  // bytes: conservative headroom for one open
#endif

static inline bool bridge_fs_internal_heap_ok(const char* who) {
  const size_t largest = heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL);
  const size_t freeb   = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  if (largest >= K1_FS_MIN_INTERNAL_BLOCK) {
    return true;
  }
  // LOUD on every trip (never silent): surfaces the exact headroom so the true
  // internal-RAM budget can be closed. free vs largest separates exhaustion from
  // fragmentation, and repeated lines across cals expose any leak.
  USBSerial.print("[fs] SKIP ");
  USBSerial.print(who);
  USBSerial.print(": internal heap too low for LittleFS open (free=");
  USBSerial.print((uint32_t)freeb);
  USBSerial.print("B largest=");
  USBSerial.print((uint32_t)largest);
  USBSerial.print("B need>=");
  USBSerial.print((uint32_t)K1_FS_MIN_INTERNAL_BLOCK);
  USBSerial.println("B) - deferring to avoid fopen abort");
  return false;
}

void update_config_filename(uint32_t input) {
#ifdef K1_MIC_IM73D_PDM_V1
  // Single choke point for the PDM config namespace: every config reader/writer
  // (load_config, save_config, factory_reset, restore_defaults) goes through
  // config_filename, so this one branch keeps the SPH /CONFIG_*.BIN unreachable
  // under the flag. Missing PDM file at boot -> compiled defaults (load_config
  // open-fail path), NEVER the SPH config.
  snprintf(config_filename, 24, "/CONFIG_PDM_%05lu.BIN", input);
#elif defined(K1_MIC_IM69D_PDM_V1)
  // IM69 namespace — distinct from both SPH (/CONFIG_*.BIN) and IM73D (/CONFIG_PDM_*).
  snprintf(config_filename, 24, "/CONFIG_IM69_%05lu.BIN", input);
#else
  snprintf(config_filename, 24, "/CONFIG_%05lu.BIN", input);
#endif
}

// Restore all defaults defined in globals.h by removing saved data and rebooting.
// Under K1_MIC_IM73D_PDM_V1 (un-frozen 2026-07-04): config_filename and
// CAL_PROFILE_FILE are PDM-namespaced, so this clears ONLY the PDM state.
// The SPH-domain files (/noise_cal.bin, /CONFIG_*.BIN, /cal_profile.bin) and the
// shared preset slots stay untouched until the SPH path is retired — with SPH
// saves frozen under the flag, a deletion there would be unrecoverable.
void factory_reset() {
  lock_leds();
  USBSerial.print("Deleting ");
  USBSerial.print(config_filename);
  USBSerial.print(": ");

  if (LittleFS.remove(config_filename)) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }

#ifndef K1_MIC_PDM_RX_ANY_V1
  USBSerial.print("Deleting noise_cal.bin: ");
  if (LittleFS.remove("/noise_cal.bin")) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }
#endif

  USBSerial.print("Deleting " CAL_PROFILE_FILE ": ");
  if (LittleFS.remove(CAL_PROFILE_FILE)) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }

#ifndef K1_MIC_PDM_RX_ANY_V1
  USBSerial.print("Deleting " K1_PRESET_SLOTS_FILE ": ");
  if (LittleFS.remove(K1_PRESET_SLOTS_FILE)) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }
  USBSerial.print("Deleting " K1_SHOW_STATE_FILE ": ");
  if (LittleFS.remove(K1_SHOW_STATE_FILE)) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }
#else
  USBSerial.println("[PDM] preserved: /noise_cal.bin, SPH config/profile, preset slots (non-PDM files)");
#endif

  reboot();
}

// Restore only configuration defaults. Safe under K1_MIC_IM73D_PDM_V1
// (un-frozen 2026-07-04): config_filename is the PDM-namespaced file, so the
// SPH config is unreachable here.
void restore_defaults() {
  lock_leds();
  USBSerial.print("Deleting ");
  USBSerial.print(config_filename);
  USBSerial.print(": ");

  if (LittleFS.remove(config_filename)) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }

  reboot();
}

// Save configuration to LittleFS. Under K1_MIC_IM73D_PDM_V1 this writes the
// PDM-namespaced config_filename (un-frozen 2026-07-04); the SPH config stays
// untouchable. The whole CONFIG struct is saved, including live PDM cal fields —
// those on-disk cal fields are informational only: the boot force-invalidate in
// system.h scrubs them and the cal profile file is the cal authority.
void save_config() {
  // Crash-safety: never open the config file when internal RAM can't afford it
  // (would abort() inside fopen, before the `if (!file)` guard). Re-arm the
  // check_settings() deferred-save so it retries once heap recovers.
  if (!bridge_fs_internal_heap_ok("save_config")) {
    next_save_time = millis() + 5000;
    settings_updated = true;
    return;
  }
  lock_leds();
  if (debug_mode) {
    USBSerial.print("LITTLEFS: ");
  }
  File file = LittleFS.open(config_filename, FILE_WRITE);
  if (!file) {
    if (debug_mode) {
      USBSerial.print("Failed to open ");
      USBSerial.print(config_filename);
      USBSerial.println(" for writing!");
    }
    unlock_leds();
    return;
  } else {
    file.seek(0);
    // N1: write [ConfigBlobHeader][raw CONFIG bytes] zero-padded to 512. The
    // header (magic+version+length+crc32) lets load_config() detect a truncated
    // or corrupt file instead of memcpy'ing garbage into the live CONFIG. File
    // size stays 512 for compatibility with the existing fixed-size read.
    uint8_t config_buffer[512];
    memset(config_buffer, 0, sizeof(config_buffer));
    ConfigBlobHeader header;
    bridge_fs_fill_header(&header, reinterpret_cast<const uint8_t*>(&CONFIG), sizeof(CONFIG));
    memcpy(config_buffer, &header, sizeof(header));
    memcpy(config_buffer + sizeof(header), &CONFIG, sizeof(CONFIG));

    for (uint16_t i = 0; i < 512; i++) {
      file.write(config_buffer[i]);
    }

    if (debug_mode) {
      USBSerial.print("WROTE ");
      USBSerial.print(config_filename);
      USBSerial.println(" SUCCESSFULLY");
    }
  }
  file.close();
  unlock_leds();
}

// Save configuration to LittleFS a few seconds from now
void save_config_delayed() {
  if(debug_mode == true){
    USBSerial.println("CONFIG SAVE QUEUED");
  }
  next_save_time = millis()+5000;
  settings_updated = true;
  static uint32_t s_persist_seq = 0;
  K1PersistRequest req = {};
  req.sequence = ++s_persist_seq;
  req.op = K1_PERSIST_OP_SAVE_CONFIG;
  req.idempotent = 1;
  req.arg = 0;
  (void)k1_persist_request_push(req);
}

// Load configuration from LittleFS
// Boot palette lock (Captain standing order, 2026-08-05): every K1, bench and main,
// starts on K1_Naberius_Gold_gp with palette mode ON for both channels.
//
// The compiled defaults alone cannot deliver this. CONFIG.PALETTE_INDEX and
// CONFIG.PALETTE_MODE_ENABLED are inside the persisted blob, so any device that has
// ever saved a config would restore its old palette over the new default and boot
// the wrong colour. Forcing after the load — on every exit path, including boot-loop
// safe mode and a missing/corrupt config file — is what makes "always" true rather
// than "true on a freshly erased device".
//
// The secondary channel's globals are not in the blob (save_configuration() /
// load_configuration() have no callers), so they already reset each boot; they are
// set here too so one function states the whole boot contract.
static inline void k1_apply_boot_palette_lock() {
  CONFIG.PALETTE_INDEX = K1_BOOT_PALETTE_INDEX;
  CONFIG.PALETTE_MODE_ENABLED = true;
  SECONDARY_PALETTE_INDEX = K1_BOOT_PALETTE_INDEX;
  SECONDARY_PALETTE_MODE_ENABLED = true;
}

void load_config() {
  lock_leds();
#ifdef K1_BOOTLOOP_GUARD_V1
  // N2b boot-loop safe mode: skip the persisted blob entirely and boot compiled
  // defaults IN RAM ONLY. The config file is NEVER deleted and defaults are NEVER
  // written back to flash — safe mode protects a boot-looping device without erasing
  // user config. The led lock is held across the CONFIG write (as on the normal path)
  // and released before the early return.
  if (k1_boot_safe_mode) {
    memcpy(&CONFIG, &CONFIG_DEFAULTS, sizeof(CONFIG));
    k1_apply_boot_palette_lock();
    USBSerial.println("BOOT_LOOP_GUARD: safe_mode_config=DEFAULTS (RAM only, file intact)");
    unlock_leds();
    return;
  }
#endif
  if (debug_mode) {
    USBSerial.print("LITTLEFS: ");
  }

  File file = LittleFS.open(config_filename, FILE_READ);
  if (!file) {
    if (debug_mode) {
      USBSerial.print("Failed to open ");
      USBSerial.print(config_filename);
      USBSerial.println(" for reading!");
    }
    k1_apply_boot_palette_lock();
    unlock_leds();
    return;
  }

  // N1: read the whole 512-byte record and classify it BEFORE trusting any of it.
  // file.size() tells us how many real bytes exist so a truncated file is detected
  // (CFG_FALLBACK) instead of memcpy'ing read()=-1 padding into CONFIG.
  file.seek(0);
  uint8_t config_buffer[512];
  size_t file_len = (size_t)file.size();
  size_t bytes_read = file_len < 512 ? file_len : 512;
  for (size_t i = 0; i < bytes_read; i++) {
    config_buffer[i] = file.read();
  }
  file.close();

  // Decide LOAD / MIGRATE / FALLBACK from header magic+version+length+crc32.
  // Recovery is RAM-ONLY (copy in-RAM defaults) — we deliberately do NOT call
  // factory_reset()/restore_defaults()/reboot() on a bad blob, because those
  // delete files and reboot and a persistently-corrupt file would boot-loop the
  // device. Anti-brick recovery is the whole point of N1.
  bool need_resave = false;
  ConfigLoadDecision decision = bridge_fs_classify_config(config_buffer, bytes_read, sizeof(CONFIG));
  if (decision == CFG_LOAD) {
    // Headered + validated: payload sits AFTER the header.
    memcpy(&CONFIG, config_buffer + sizeof(ConfigBlobHeader), sizeof(CONFIG));
    if (debug_mode) {
      USBSerial.println("READ CONFIG SUCCESSFULLY");
    }
  } else if (decision == CFG_MIGRATE) {
    // Headerless legacy image at offset 0: adopt it, then re-save with a header.
    memcpy(&CONFIG, config_buffer, sizeof(CONFIG));
    need_resave = true;
    if (debug_mode) {
      USBSerial.println("MIGRATED LEGACY CONFIG");
    }
  } else { // CFG_FALLBACK
    // Corrupt/truncated/wrong-version blob: recover to compiled defaults in RAM
    // (NO file delete, NO reboot), then re-save a valid headered blob.
    memcpy(&CONFIG, &CONFIG_DEFAULTS, sizeof(CONFIG));
    need_resave = true;
    if (debug_mode) {
      USBSerial.println("CONFIG INVALID -> DEFAULTS (no reboot)");
    }
  }

#ifdef K1_EFFECT_REGISTRY_V1
  CONFIG.LIGHTSHOW_MODE = k1::effects::framework::registry_sanitize_persisted(CONFIG.LIGHTSHOW_MODE);
  SECONDARY_LIGHTSHOW_MODE = k1::effects::framework::registry_sanitize_persisted(SECONDARY_LIGHTSHOW_MODE);
#else
  CONFIG.LIGHTSHOW_MODE = light_mode_sanitize_persisted(CONFIG.LIGHTSHOW_MODE);
  SECONDARY_LIGHTSHOW_MODE = light_mode_sanitize_persisted(SECONDARY_LIGHTSHOW_MODE);
#endif

  // Applied AFTER the persisted blob is adopted, so a stored palette cannot win.
  k1_apply_boot_palette_lock();

  unlock_leds();
  // save_config() takes its own lock_leds()/unlock_leds(); lock_leds() is a
  // flag-set (not a recursive counter), so call it only AFTER unlocking to avoid
  // unlock_leds() inside save_config() clearing the lock while we still hold it.
  if (need_resave) {
    save_config();
  }
}

// Save noise calibration to LittleFS
void save_ambient_noise_calibration() {
#ifdef K1_MIC_PDM_RX_ANY_V1
  // STAYS frozen under PDM flags (decision 2026-07-04 / IM69 2026-08-05):
  // /noise_cal.bin is SPH-domain; PDM noise_samples[] persist inside
  // CAL_PROFILE_FILE via save_calibration_profile().
  return;
#endif
  // Crash-safety: skip the open under internal-RAM pressure (non-PDM builds).
  // noise_samples[] stay live in RAM; a later accepted cal re-attempts the save.
  if (!bridge_fs_internal_heap_ok("save_ambient_noise_calibration")) {
    return;
  }
  lock_leds();
  if (debug_mode) {
    USBSerial.print("SAVING AMBIENT_NOISE PROFILE... ");
  }
  File file = LittleFS.open("/noise_cal.bin", FILE_WRITE);
  if (!file) {
    if (debug_mode) {
      USBSerial.println("Failed to open file for writing!");
    }
    unlock_leds();
    return;
  }

  bytes_32 temp;

  file.seek(0);
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    float in_val = float(noise_samples[i]);

    temp.long_val_float = in_val;

    file.write(temp.bytes[0]);
    file.write(temp.bytes[1]);
    file.write(temp.bytes[2]);
    file.write(temp.bytes[3]);
  }

  file.close();
  if (debug_mode) {
    USBSerial.println("SAVE COMPLETE");
  }

  unlock_leds();
}

// Load noise calibration from LittleFS
void load_ambient_noise_calibration() {
#ifdef K1_MIC_PDM_RX_ANY_V1
  // Never read the SPH-domain /noise_cal.bin under a PDM flag: with no PDM
  // profile on disk it would leave SPH noise floors live in noise_samples[]
  // (wrong domain). PDM noise comes from CAL_PROFILE_FILE (or stays zero).
  return;
#endif
  lock_leds();
  if (debug_mode) {
    USBSerial.print("LOADING AMBIENT_NOISE PROFILE... ");
  }
  File file = LittleFS.open("/noise_cal.bin", FILE_READ);
  if (!file) {
    if (debug_mode) {
      USBSerial.println("Failed to open file for reading!");
    }
    unlock_leds();
    return;
  }

  bytes_32 temp;

  file.seek(0);
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    temp.bytes[0] = file.read();
    temp.bytes[1] = file.read();
    temp.bytes[2] = file.read();
    temp.bytes[3] = file.read();

    noise_samples[i] = SQ15x16(temp.long_val_float);
  }

  file.close();
  if (debug_mode) {
    USBSerial.println("LOAD COMPLETE");
  }

  unlock_leds();
}

static bool write_cal_profile_bytes(File& file, const void* data, size_t len) {
  return file.write(reinterpret_cast<const uint8_t*>(data), len) == len;
}

static bool read_cal_profile_bytes(File& file, void* data, size_t len) {
  return file.read(reinterpret_cast<uint8_t*>(data), len) == len;
}

bool save_calibration_profile(uint8_t source) {
  // Under K1_MIC_IM73D_PDM_V1 this writes CAL_PROFILE_FILE = /cal_profile_pdm.bin
  // (PDM-namespaced; the SPH profile is untouchable). Un-stubbed 2026-07-03 after
  // the graft + cal-gate window were device-proven (NOISE CAL ACCEPTED, SSL=887).
  // Crash-safety: under internal-RAM pressure this open would abort() inside fopen
  // one line after save_config() in the cal-complete burst. Return false instead;
  // the accepted cal stays live in RAM for the session (log surfaces the shortfall).
  if (!bridge_fs_internal_heap_ok("save_calibration_profile")) {
    return false;
  }
  lock_leds();
  if (!calibration_profile_valid()) {
    calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
    unlock_leds();
    return false;
  }

  File file = LittleFS.open(CAL_PROFILE_FILE, FILE_WRITE);
  if (!file) {
    unlock_leds();
    return false;
  }

  uint32_t magic = CAL_PROFILE_MAGIC;
  uint16_t version = CAL_PROFILE_VERSION;
  uint16_t freq_count = NUM_FREQS;
  uint8_t saved_source = source;
  uint8_t reserved[3] = { 0, 0, 0 };
  int32_t dc_offset = CONFIG.DC_OFFSET;
  uint32_t sweet_spot_min = CONFIG.SWEET_SPOT_MIN_LEVEL;
  uint32_t sweet_spot_max = CONFIG.SWEET_SPOT_MAX_LEVEL;
  bool ok = true;

  ok = ok && write_cal_profile_bytes(file, &magic, sizeof(magic));
  ok = ok && write_cal_profile_bytes(file, &version, sizeof(version));
  ok = ok && write_cal_profile_bytes(file, &freq_count, sizeof(freq_count));
  ok = ok && write_cal_profile_bytes(file, &saved_source, sizeof(saved_source));
  ok = ok && write_cal_profile_bytes(file, reserved, sizeof(reserved));
  ok = ok && write_cal_profile_bytes(file, &dc_offset, sizeof(dc_offset));
  ok = ok && write_cal_profile_bytes(file, &sweet_spot_min, sizeof(sweet_spot_min));
  ok = ok && write_cal_profile_bytes(file, &sweet_spot_max, sizeof(sweet_spot_max));

  bytes_32 temp;
  for (uint16_t i = 0; ok && i < NUM_FREQS; i++) {
    temp.long_val_float = float(noise_samples[i]);
    ok = file.write(temp.bytes[0]) == 1;
    ok = ok && file.write(temp.bytes[1]) == 1;
    ok = ok && file.write(temp.bytes[2]) == 1;
    ok = ok && file.write(temp.bytes[3]) == 1;
  }

  file.close();
  if (ok) {
    calibration_profile_loaded = true;
    calibration_refresh_status(source);
  }
#ifdef K1_MIC_PDM_RX_ANY_V1
  else {
    // A failed PDM file write must never cost an accepted cal: keep the RAM-only
    // semantic success (cal_valid reflects the in-RAM learned values).
    calibration_profile_loaded = false;
    calibration_refresh_status(source);
  }
#endif
  unlock_leds();
  return ok;
}

bool load_calibration_profile_if_config_invalid() {
  if (calibration_profile_valid()) {
    calibration_profile_loaded = false;
    calibration_refresh_status(CAL_SOURCE_CONFIG);
#ifndef K1_MIC_PDM_RX_ANY_V1
    // PDM: NEVER seed the PDM profile from CONFIG here — at this point CONFIG
    // holds SPH-domain values loaded from the frozen SPH config.bin.
    if (!LittleFS.exists(CAL_PROFILE_FILE)) {
      save_calibration_profile(CAL_SOURCE_CONFIG);
    }
#endif
    return false;
  }

  lock_leds();
  File file = LittleFS.open(CAL_PROFILE_FILE, FILE_READ);
  if (!file) {
    unlock_leds();
    calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
    return false;
  }

  uint32_t magic = 0;
  uint16_t version = 0;
  uint16_t freq_count = 0;
  uint8_t saved_source = CAL_SOURCE_DEFAULT_INVALID;
  uint8_t reserved[3] = { 0, 0, 0 };
  int32_t dc_offset = 0;
  uint32_t sweet_spot_min = 0;
  uint32_t sweet_spot_max = 0;
  SQ15x16 loaded_noise[NUM_FREQS];
  bool ok = true;

  ok = ok && read_cal_profile_bytes(file, &magic, sizeof(magic));
  ok = ok && read_cal_profile_bytes(file, &version, sizeof(version));
  ok = ok && read_cal_profile_bytes(file, &freq_count, sizeof(freq_count));
  ok = ok && read_cal_profile_bytes(file, &saved_source, sizeof(saved_source));
  ok = ok && read_cal_profile_bytes(file, reserved, sizeof(reserved));
  ok = ok && read_cal_profile_bytes(file, &dc_offset, sizeof(dc_offset));
  ok = ok && read_cal_profile_bytes(file, &sweet_spot_min, sizeof(sweet_spot_min));
  ok = ok && read_cal_profile_bytes(file, &sweet_spot_max, sizeof(sweet_spot_max));

  bytes_32 temp;
  for (uint16_t i = 0; ok && i < NUM_FREQS; i++) {
    ok = file.read(temp.bytes, 4) == 4;
    if (ok) {
      loaded_noise[i] = SQ15x16(temp.long_val_float);
    }
  }
  file.close();

  if (!ok ||
      magic != CAL_PROFILE_MAGIC ||
      version != CAL_PROFILE_VERSION ||
      freq_count != NUM_FREQS) {
    unlock_leds();
    calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
    return false;
  }

  CONFIG.DC_OFFSET = dc_offset;
  CONFIG.SWEET_SPOT_MIN_LEVEL = sweet_spot_min;
  if (sweet_spot_max > 0) {
    CONFIG.SWEET_SPOT_MAX_LEVEL = sweet_spot_max;
  }
  for (uint16_t i = 0; i < NUM_FREQS; i++) {
    noise_samples[i] = loaded_noise[i];
  }
  noise_complete = true;
  noise_iterations = 0;
  calibration_profile_loaded = true;
  unlock_leds();

  calibration_refresh_status(CAL_SOURCE_PERSISTED_PROFILE);
  return calibration_valid;
}

bool clear_calibration_profile() {
  // Under K1_MIC_IM73D_PDM_V1, CAL_PROFILE_FILE is /cal_profile_pdm.bin — this
  // clears only the PDM cal; the SPH profile is unreachable under the flag.
  lock_leds();
  bool removed = LittleFS.remove(CAL_PROFILE_FILE);
  calibration_profile_loaded = false;
  calibration_refresh_status(CAL_SOURCE_DEFAULT_INVALID);
  unlock_leds();
  return removed;
}

// Initialize LittleFS
void init_fs() {
  lock_leds();
  USBSerial.print("INIT FILESYSTEM: ");
  USBSerial.println(LittleFS.begin(true) == true ? K1_PASS : K1_FAIL);

  update_config_filename(FIRMWARE_VERSION);

  load_ambient_noise_calibration();
  load_config();
  // Soft restore of secondary/edge/show overlay; missing or corrupt file is a
  // no-op (primary CONFIG from load_config() remains authoritative alone).
  (void)k1_show_state_load();
  load_calibration_profile_if_config_invalid();
  unlock_leds();
}

int save_configuration() {
  File conf_file = LittleFS.open(config_filename, FILE_WRITE);
  if (!conf_file) {
    USBSerial.println("ERROR: Failed to open configuration file for writing!");
    return -1;
  }
  
  conf_file.write(reinterpret_cast<uint8_t*>(&CONFIG.BASE_COAT_INTENSITY), sizeof(CONFIG.BASE_COAT_INTENSITY));

  // --- Save Palette Settings --- 
  conf_file.write(reinterpret_cast<uint8_t*>(&CONFIG.PALETTE_INDEX), sizeof(CONFIG.PALETTE_INDEX));
  conf_file.write(reinterpret_cast<uint8_t*>(&CONFIG.PALETTE_MODE_ENABLED), sizeof(CONFIG.PALETTE_MODE_ENABLED));
  
  // --- Save Secondary Palette Settings ---
  conf_file.write(reinterpret_cast<uint8_t*>(&SECONDARY_PALETTE_INDEX), sizeof(SECONDARY_PALETTE_INDEX));
  conf_file.write(reinterpret_cast<uint8_t*>(&SECONDARY_PALETTE_MODE_ENABLED), sizeof(SECONDARY_PALETTE_MODE_ENABLED));

  conf_file.close();
  return 0;
}

int load_configuration() {
  bool config_error = false;
  
  File conf_file = LittleFS.open(config_filename, FILE_READ);
  if (!conf_file) {
    USBSerial.println("ERROR: Failed to open configuration file for reading!");
    return -1;
  }
  
  if (conf_file.read(reinterpret_cast<uint8_t*>(&CONFIG.BASE_COAT_INTENSITY), sizeof(CONFIG.BASE_COAT_INTENSITY)) != sizeof(CONFIG.BASE_COAT_INTENSITY)) {
    USBSerial.println("CONF ERR: BASE_COAT_INTENSITY");
    config_error = true;
  }

  // --- Load Palette Settings --- 
  if (conf_file.read(reinterpret_cast<uint8_t*>(&CONFIG.PALETTE_INDEX), sizeof(CONFIG.PALETTE_INDEX)) != sizeof(CONFIG.PALETTE_INDEX)) { 
    USBSerial.println("CONF ERR: PALETTE_INDEX"); 
    config_error = true; 
  }
  
  if (conf_file.read(reinterpret_cast<uint8_t*>(&CONFIG.PALETTE_MODE_ENABLED), sizeof(CONFIG.PALETTE_MODE_ENABLED)) != sizeof(CONFIG.PALETTE_MODE_ENABLED)) { 
    USBSerial.println("CONF ERR: PALETTE_MODE_ENABLED"); 
    config_error = true; 
  }

  // --- Load Secondary Palette Settings ---
  if (conf_file.read(reinterpret_cast<uint8_t*>(&SECONDARY_PALETTE_INDEX), sizeof(SECONDARY_PALETTE_INDEX)) != sizeof(SECONDARY_PALETTE_INDEX)) { 
    USBSerial.println("CONF ERR: SECONDARY_PALETTE_INDEX"); 
    config_error = true; 
  }
  
  if (conf_file.read(reinterpret_cast<uint8_t*>(&SECONDARY_PALETTE_MODE_ENABLED), sizeof(SECONDARY_PALETTE_MODE_ENABLED)) != sizeof(SECONDARY_PALETTE_MODE_ENABLED)) { 
    USBSerial.println("CONF ERR: SECONDARY_PALETTE_MODE_ENABLED"); 
    config_error = true; 
  }

  conf_file.close();

  // Validate loaded palette index
  if (CONFIG.PALETTE_INDEX >= gGradientPaletteCount) {
    USBSerial.print("CONF WARN: Invalid PALETTE_INDEX (");
    USBSerial.print(CONFIG.PALETTE_INDEX);
    USBSerial.print("), resetting to 0. Max is ");
    USBSerial.println(gGradientPaletteCount - 1);
    CONFIG.PALETTE_INDEX = 0; // Reset to default if out of bounds
    config_error = true; // Mark as error to force a save later if desired
  }
  
  // Validate secondary palette index
  if (SECONDARY_PALETTE_INDEX >= gGradientPaletteCount) {
    USBSerial.print("CONF WARN: Invalid SECONDARY_PALETTE_INDEX (");
    USBSerial.print(SECONDARY_PALETTE_INDEX);
    USBSerial.print("), resetting to 0. Max is ");
    USBSerial.println(gGradientPaletteCount - 1);
    SECONDARY_PALETTE_INDEX = 0; // Reset to default if out of bounds
    config_error = true; // Mark as error to force a save later if desired
  }
  
  if (config_error == true) {
    return -2;
  }
  
  return 0;
}
