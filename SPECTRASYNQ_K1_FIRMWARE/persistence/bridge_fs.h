/*----------------------------------------
  Sensory Bridge FILESYSTEM ACCESS
  ----------------------------------------*/

#include "globals.h"
#include "constants.h"
#include "Palettes.h" // Include for gGradientPaletteCount
#include "sb_effect_queue.h" // SB_PRESET_SLOTS_FILE (factory_reset enumeration)
#include "bridge_fs_config_codec.h" // N1: ConfigBlobHeader + bridge_fs_classify_config()
#ifdef K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h" // registry_sanitize_persisted() (R2b NVS sanitiser)
#endif

extern void reboot(); // system.h

#define CAL_PROFILE_FILE "/cal_profile.bin"
#define CAL_PROFILE_MAGIC 0x314C4143UL
#define CAL_PROFILE_VERSION 1U

void update_config_filename(uint32_t input) {
  snprintf(config_filename, 24, "/CONFIG_%05lu.BIN", input);
}

// Restore all defaults defined in globals.h by removing saved data and rebooting
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

  USBSerial.print("Deleting noise_cal.bin: ");
  if (LittleFS.remove("/noise_cal.bin")) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }

  USBSerial.print("Deleting cal_profile.bin: ");
  if (LittleFS.remove(CAL_PROFILE_FILE)) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }

  USBSerial.print("Deleting " SB_PRESET_SLOTS_FILE ": ");
  if (LittleFS.remove(SB_PRESET_SLOTS_FILE)) {
    USBSerial.println("file deleted");
  } else {
    USBSerial.println("delete failed");
  }

  reboot();
}

// Restore only configuration defaults
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

// Save configuration to LittleFS
void save_config() {
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

// Save configuration to LittleFS 10 seconds from now
void save_config_delayed() {
  if(debug_mode == true){
    USBSerial.println("CONFIG SAVE QUEUED");
  }
  next_save_time = millis()+5000;
  settings_updated = true;
}

// Load configuration from LittleFS
void load_config() {
  lock_leds();
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
  lock_leds();
  if (debug_mode) {
    USBSerial.print("SAVING AMBIENT_NOISE PROFILE... ");
  }
  File file = LittleFS.open("/noise_cal.bin", FILE_WRITE);
  if (!file) {
    if (debug_mode) {
      USBSerial.println("Failed to open file for writing!");
    }
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
  lock_leds();
  if (debug_mode) {
    USBSerial.print("LOADING AMBIENT_NOISE PROFILE... ");
  }
  File file = LittleFS.open("/noise_cal.bin", FILE_READ);
  if (!file) {
    if (debug_mode) {
      USBSerial.println("Failed to open file for reading!");
    }
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
  unlock_leds();
  return ok;
}

bool load_calibration_profile_if_config_invalid() {
  if (calibration_profile_valid()) {
    calibration_profile_loaded = false;
    calibration_refresh_status(CAL_SOURCE_CONFIG);
    if (!LittleFS.exists(CAL_PROFILE_FILE)) {
      save_calibration_profile(CAL_SOURCE_CONFIG);
    }
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
  USBSerial.println(LittleFS.begin(true) == true ? SB_PASS : SB_FAIL);

  update_config_filename(FIRMWARE_VERSION);

  load_ambient_noise_calibration();
  load_config();
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
