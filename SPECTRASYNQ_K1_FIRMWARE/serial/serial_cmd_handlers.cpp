/*----------------------------------------
  SERIAL CONFIG-SETTER HANDLERS (pure CONFIG setters) — implementation
  ----------------------------------------
  Bodies lifted VERBATIM from serial_menu.h parse_command() Stage-B ladder
  (Phase A Lane 2, S4 / Unit H first slice). Statement-identical to
  serial_menu.h@HEAD; declarations live in serial_cmd_handlers.h.

  Gated by the S3.0 serial_replay golden — it must reproduce byte-for-byte after
  this move (tests/test_golden_master.py + harness_selftest.py Gate-Fα).
*/

#include "serial_cmd_handlers.h"

#include "globals.h"               // CONFIG, CONFIG_DEFAULTS, USBSerial, FastLED, gGradientPaletteCount
#include "constants.h"             // NUM_FREQS, CHROMA_PROFILE_*, SAMPLE_HISTORY_LENGTH
#include "serial_tx.h"             // tx_begin / tx_end / bad_command
#include "serial_parse_helpers.h"  // vp_parse_bool / vp_parse_float

#include <stdint.h>
#include <stdlib.h>                // atol / atoi / atof
#include <string.h>                // strcmp

// Cross-TU edges (static -> extern): the device-persistence side-effects are
// header-body functions in persistence/bridge_fs.h (save_config:77,
// save_config_delayed:110), visible in the .ino include context. Forward-declare
// them here — same pattern as audio/k1_gdft_core.cpp:48 and
// control/sb_effect_queue.cpp:34 — so the moved bodies link against that storage.
extern void save_config();
extern void save_config_delayed();

// reboot() is the device restart entry point (defined in the driver / .ino TU;
// declared extern at serial_menu.h:47). The 7 reboot-bearing setters (S4.1) end
// with reboot() after persisting + echoing — forward-declare it here so the moved
// bodies link against that single definition (host-stubbed in the serial_replay
// oracle, which records the fire instead of restarting).
extern void reboot();

// serial_print_palette_line() is an external-linkage free function defined in
// serial_menu.h:962 (palette name echo). The palette_index setter calls it; forward
// declare so this TU links against that single definition.
void serial_print_palette_line(const char* label, uint8_t index);

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_pure_setter — the 23 pure CONFIG setters, lifted verbatim
// from parse_command()'s else-if ladder. The `if (false) {}` opener lets every
// real branch keep its original `else if (strcmp(command_type, "<name>") == 0)`
// text (statement-identical to serial_menu.h@HEAD). Returns true iff a branch
// matched; false routes parse_command back to its remaining ladder + bad_command.
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_pure_setter(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "photons") == 0) {
      float value = 0.0f;
      if (vp_parse_float(command_data, &value)) {
        CONFIG.PHOTONS = constrain(value, 0.05f, 1.0f);
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.PHOTONS: ");
        USBSerial.println(CONFIG.PHOTONS, 6);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "chroma") == 0) {
      float value = 0.0f;
      if (vp_parse_float(command_data, &value)) {
        CONFIG.CHROMA = constrain(value, 0.0f, 1.0f);
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.CHROMA: ");
        USBSerial.println(CONFIG.CHROMA, 6);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "mood") == 0) {
      float value = 0.0f;
      if (vp_parse_float(command_data, &value)) {
        CONFIG.MOOD = constrain(value, 0.0f, 1.0f);
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.MOOD: ");
        USBSerial.println(CONFIG.MOOD, 6);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "palette_mode") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        CONFIG.PALETTE_MODE_ENABLED = value;
        save_config_delayed();
        tx_begin();
        USBSerial.print("PALETTE_MODE: ");
        USBSerial.println(CONFIG.PALETTE_MODE_ENABLED ? "on" : "off");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "palette_index") == 0) {
      int index = atoi(command_data);
      if (index >= 0 && index < gGradientPaletteCount) {
        CONFIG.PALETTE_INDEX = index;
        CONFIG.PALETTE_MODE_ENABLED = true;
        save_config_delayed();
        tx_begin();
        serial_print_palette_line("PALETTE", CONFIG.PALETTE_INDEX);
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    // Set Square Iterations ----------------------------------
    else if (strcmp(command_type, "square_iter") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.SQUARE_ITER = CONFIG_DEFAULTS.SQUARE_ITER;
      } else {
        CONFIG.SQUARE_ITER = constrain(atol(command_data), 0, 10);
      }
      save_config_delayed();

      tx_begin();
      USBSerial.print("CONFIG.SQUARE_ITER: ");
      USBSerial.println(CONFIG.SQUARE_ITER);
      tx_end();
    }

    // Set LED Interpolation ----------------------------
    else if (strcmp(command_type, "led_interpolation") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.LED_INTERPOLATION = CONFIG_DEFAULTS.LED_INTERPOLATION;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.LED_INTERPOLATION = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.LED_INTERPOLATION = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.LED_INTERPOLATION: ");
        USBSerial.println(CONFIG.LED_INTERPOLATION);
        tx_end();
      }
    }

    // Set Base Coat ----------------------------
    else if (strcmp(command_type, "base_coat") == 0) {
      bool good = false;
      if (strcmp(command_data, "true") == 0) {
        CONFIG.BASE_COAT = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.BASE_COAT = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.BASE_COAT: ");
        USBSerial.println(CONFIG.BASE_COAT);
        tx_end();
      }
    }

    // Set LED Temporal Dithering ----------------------------
    else if (strcmp(command_type, "temporal_dithering") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.TEMPORAL_DITHERING = CONFIG_DEFAULTS.TEMPORAL_DITHERING;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.TEMPORAL_DITHERING = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.TEMPORAL_DITHERING = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.TEMPORAL_DITHERING: ");
        USBSerial.println(CONFIG.TEMPORAL_DITHERING);
        tx_end();
      }
    }

    // Set Audio Sensitivity ----------------------------
    else if (strcmp(command_type, "sensitivity") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.SENSITIVITY = CONFIG_DEFAULTS.SENSITIVITY;
      } else {
        CONFIG.SENSITIVITY = atof(command_data);
      }

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.SENSITIVITY: ");
      USBSerial.println(CONFIG.SENSITIVITY);
      tx_end();
    }

    // Toggle Lightshow Mirroring ---------------------
    else if (strcmp(command_type, "mirror_enabled") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.MIRROR_ENABLED = CONFIG_DEFAULTS.MIRROR_ENABLED;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.MIRROR_ENABLED = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.MIRROR_ENABLED = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.MIRROR_ENABLED: ");
        USBSerial.println(CONFIG.MIRROR_ENABLED);
        tx_end();
      }
    }

    // Set Sweet Spot LOW threshold -------------------
    else if (strcmp(command_type, "sweet_spot_min") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.SWEET_SPOT_MIN_LEVEL = CONFIG_DEFAULTS.SWEET_SPOT_MIN_LEVEL;
      } else {
        CONFIG.SWEET_SPOT_MIN_LEVEL = constrain(atof(command_data), 0, uint32_t(-1));
      }

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.SWEET_SPOT_MIN_LEVEL: ");
      USBSerial.println(CONFIG.SWEET_SPOT_MIN_LEVEL);
      tx_end();
    }

    // Set Sweet Spot HIGH threshold ------------------
    else if (strcmp(command_type, "sweet_spot_max") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.SWEET_SPOT_MAX_LEVEL = CONFIG_DEFAULTS.SWEET_SPOT_MAX_LEVEL;
      } else {
        CONFIG.SWEET_SPOT_MAX_LEVEL = constrain(atof(command_data), 0, uint32_t(-1));
      }

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.SWEET_SPOT_MAX_LEVEL: ");
      USBSerial.println(CONFIG.SWEET_SPOT_MAX_LEVEL);
      tx_end();
    }

    // Set Chromagram Range ---------------
    else if (strcmp(command_type, "chromagram_range") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.CHROMAGRAM_RANGE = CONFIG_DEFAULTS.CHROMAGRAM_RANGE;
      } else {
        CONFIG.CHROMAGRAM_RANGE = constrain(atof(command_data), 1, NUM_FREQS);
      }

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.CHROMAGRAM_RANGE: ");
      USBSerial.println(CONFIG.CHROMAGRAM_RANGE);
      tx_end();
    }

    // Set Standby Dimming behavior -------
    else if (strcmp(command_type, "standby_dimming") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.STANDBY_DIMMING = CONFIG_DEFAULTS.STANDBY_DIMMING;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.STANDBY_DIMMING = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.STANDBY_DIMMING = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.STANDBY_DIMMING: ");
        USBSerial.println(CONFIG.STANDBY_DIMMING);
        tx_end();
      }
    }

    // Set if image should be reversed ------------------------
    else if (strcmp(command_type, "reverse_order") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.REVERSE_ORDER = CONFIG_DEFAULTS.REVERSE_ORDER;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.REVERSE_ORDER = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.REVERSE_ORDER = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.REVERSE_ORDER: ");
        USBSerial.println(CONFIG.REVERSE_ORDER);
        tx_end();
      }
    }

    // Set max LED current ----------------------------
    else if (strcmp(command_type, "max_current_ma") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.MAX_CURRENT_MA = CONFIG_DEFAULTS.MAX_CURRENT_MA;
      } else {
        CONFIG.MAX_CURRENT_MA = constrain(atof(command_data), 0, uint32_t(-1));
      }

      FastLED.setMaxPowerInVoltsAndMilliamps(5.0, CONFIG.MAX_CURRENT_MA);

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.MAX_CURRENT_MA: ");
      USBSerial.println(CONFIG.MAX_CURRENT_MA);
      tx_end();
    }

    // Toggle Color Shift ---------------------------------
    else if (strcmp(command_type, "auto_color_shift") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.AUTO_COLOR_SHIFT = CONFIG_DEFAULTS.AUTO_COLOR_SHIFT;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.AUTO_COLOR_SHIFT = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.AUTO_COLOR_SHIFT = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.AUTO_COLOR_SHIFT: ");
        USBSerial.println(CONFIG.AUTO_COLOR_SHIFT);
        tx_end();
      }
    }

    // Set Incandescent LUT intensity ----------------------------
    else if (strcmp(command_type, "incandescent_filter") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.INCANDESCENT_FILTER = CONFIG_DEFAULTS.INCANDESCENT_FILTER;
      } else {
        CONFIG.INCANDESCENT_FILTER = atof(command_data);
        if (CONFIG.INCANDESCENT_FILTER < 0.0) {
          CONFIG.INCANDESCENT_FILTER = 0.0;
        } else if (CONFIG.INCANDESCENT_FILTER > 1.0) {
          CONFIG.INCANDESCENT_FILTER = 1.0;
        }
      }

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.INCANDESCENT_FILTER: ");
      USBSerial.println(CONFIG.INCANDESCENT_FILTER);
      tx_end();
    }

    // Toggle Incandescent Mode ----------------------------
    else if (strcmp(command_type, "incandescent_mode") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.INCANDESCENT_MODE = CONFIG_DEFAULTS.INCANDESCENT_MODE;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.INCANDESCENT_MODE = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.INCANDESCENT_MODE = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config_delayed();
        tx_begin();
        USBSerial.print("CONFIG.INCANDESCENT_MODE: ");
        USBSerial.println(CONFIG.INCANDESCENT_MODE);
        tx_end();
      }
    }

    // Set Bulb Cover Opacity ----------------------------
    else if (strcmp(command_type, "bulb_opacity") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.BULB_OPACITY = CONFIG_DEFAULTS.BULB_OPACITY;
      } else {
        CONFIG.BULB_OPACITY = atof(command_data);
        if (CONFIG.BULB_OPACITY < 0.0) {
          CONFIG.BULB_OPACITY = 0.0;
        } else if (CONFIG.BULB_OPACITY > 1.0) {
          CONFIG.BULB_OPACITY = 1.0;
        }
      }

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.BULB_OPACITY: ");
      USBSerial.println(CONFIG.BULB_OPACITY);
      tx_end();
    }

    // Set Saturation ----------------------------
    else if (strcmp(command_type, "saturation") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.SATURATION = CONFIG_DEFAULTS.SATURATION;
      } else {
        CONFIG.SATURATION = atof(command_data);
        if (CONFIG.SATURATION < 0.0) {
          CONFIG.SATURATION = 0.0;
        } else if (CONFIG.SATURATION > 1.0) {
          CONFIG.SATURATION = 1.0;
        }
      }

      save_config_delayed();
      tx_begin();
      USBSerial.print("CONFIG.SATURATION: ");
      USBSerial.println(CONFIG.SATURATION);
      tx_end();
    }

    // Set Prism Count ----------------------------------------
    else if (strcmp(command_type, "prism_count") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        good = true;
        CONFIG.PRISM_COUNT = CONFIG_DEFAULTS.PRISM_COUNT;
      } else {
        good = true;
        CONFIG.PRISM_COUNT = constrain(atol(command_data), 0, 10);
      }

      if (good) {
        save_config();
        tx_begin();
        USBSerial.print("CONFIG.PRISM_COUNT: ");
        USBSerial.println(CONFIG.PRISM_COUNT);
        tx_end();
      }
    }

    else {
      return false;  // not a pure setter — let parse_command's ladder continue
    }

    return true;
}

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_reboot_setter — the 7 CLEAN reboot-bearing CONFIG setters,
// lifted verbatim from parse_command()'s else-if ladder (S4.1). Same `if (false) {}`
// opener + per-branch `else if (strcmp(...) == 0)` structure as the pure dispatcher,
// so each body is statement-identical to serial_menu.h@HEAD. Each ends with reboot()
// after save_config() (IMMEDIATE) + echo. Returns true iff a branch matched; false
// routes parse_command back to its remaining ladder + bad_command. Gated by the S3.1
// serial_replay golden (reboot:true + save_config:true on all 7) — it must reproduce
// byte-for-byte after this move.
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_reboot_setter(const char* command_type, char* command_data) {
    if (false) {}

    // Set Sample Rate ----------------------------------------
    else if (strcmp(command_type, "sample_rate") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        good = true;
        CONFIG.SAMPLE_RATE = CONFIG_DEFAULTS.SAMPLE_RATE;
      } else {
        good = true;
        CONFIG.SAMPLE_RATE = constrain(atol(command_data), 6400, 44100);
      }

      if (good) {
        save_config();
        tx_begin();
        USBSerial.print("CONFIG.SAMPLE_RATE: ");
        USBSerial.println(CONFIG.SAMPLE_RATE);
        tx_end();
        reboot();
      }
    }

    // Set Note Offset ----------------------------------------
    else if (strcmp(command_type, "note_offset") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.NOTE_OFFSET = CONFIG_DEFAULTS.NOTE_OFFSET;
      } else {
        CONFIG.NOTE_OFFSET = constrain(atol(command_data), 0, 32);
      }
      save_config();
      tx_begin();
      USBSerial.print("CONFIG.NOTE_OFFSET: ");
      USBSerial.println(CONFIG.NOTE_OFFSET);
      tx_end();
      reboot();
    }

    // Set LED Type ---------------------------------------
    else if (strcmp(command_type, "led_type") == 0) {
      bool good = false;
      if (strcmp(command_data, "neopixel") == 0) {
        CONFIG.LED_TYPE = LED_NEOPIXEL;
        CONFIG.LED_COLOR_ORDER = GRB;
        good = true;
      }
      else if (strcmp(command_data, "neopixel_x2") == 0) {
        CONFIG.LED_TYPE = LED_NEOPIXEL_X2;
        CONFIG.LED_COLOR_ORDER = GRB;
        good = true;
      } else if (strcmp(command_data, "dotstar") == 0) {
        CONFIG.LED_TYPE = LED_DOTSTAR;
        CONFIG.LED_COLOR_ORDER = BGR;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config();
        tx_begin();
        USBSerial.print("CONFIG.LED_TYPE: ");
        USBSerial.println(CONFIG.LED_TYPE);
        tx_end();
        reboot();
      }
    }

    // Set LED Count ------------------------------------
    else if (strcmp(command_type, "led_count") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.LED_COUNT = CONFIG_DEFAULTS.LED_COUNT;
      } else {
        CONFIG.LED_COUNT = constrain(atol(command_data), 1, 10000);
      }

      save_config();
      tx_begin();
      USBSerial.print("CONFIG.LED_COUNT: ");
      USBSerial.println(CONFIG.LED_COUNT);
      tx_end();
      reboot();
    }

    // Set LED Color Order ----------------------------
    else if (strcmp(command_type, "led_color_order") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.LED_COLOR_ORDER = CONFIG_DEFAULTS.LED_COLOR_ORDER;
        good = true;
      } else if (strcmp(command_data, "GRB") == 0) {
        CONFIG.LED_COLOR_ORDER = GRB;
        good = true;
      } else if (strcmp(command_data, "RGB") == 0) {
        CONFIG.LED_COLOR_ORDER = RGB;
        good = true;
      } else if (strcmp(command_data, "BGR") == 0) {
        CONFIG.LED_COLOR_ORDER = BGR;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config();
        tx_begin();
        USBSerial.print("CONFIG.LED_COLOR_ORDER: ");
        USBSerial.println(CONFIG.LED_COLOR_ORDER);
        tx_end();
        reboot();
      }
    }

    // Set Samples Per Chunk ---------------------------
    else if (strcmp(command_type, "samples_per_chunk") == 0) {
      if (strcmp(command_data, "default") == 0) {
        CONFIG.SAMPLES_PER_CHUNK = CONFIG_DEFAULTS.SAMPLES_PER_CHUNK;
      } else {
        CONFIG.SAMPLES_PER_CHUNK = constrain(atol(command_data), 0, SAMPLE_HISTORY_LENGTH);
      }

      save_config();
      tx_begin();
      USBSerial.print("CONFIG.SAMPLES_PER_CHUNK: ");
      USBSerial.println(CONFIG.SAMPLES_PER_CHUNK);
      tx_end();
      reboot();
    }

    // Toggle Boot Animation --------------------------
    else if (strcmp(command_type, "boot_animation") == 0) {
      bool good = false;
      if (strcmp(command_data, "default") == 0) {
        CONFIG.BOOT_ANIMATION = CONFIG_DEFAULTS.BOOT_ANIMATION;
        good = true;
      } else if (strcmp(command_data, "true") == 0) {
        CONFIG.BOOT_ANIMATION = true;
        good = true;
      } else if (strcmp(command_data, "false") == 0) {
        CONFIG.BOOT_ANIMATION = false;
        good = true;
      } else {
        bad_command(command_type, command_data);
      }

      if (good) {
        save_config();
        tx_begin();
        USBSerial.print("CONFIG.BOOT_ANIMATION: ");
        USBSerial.println(CONFIG.BOOT_ANIMATION);
        tx_end();
        reboot();
      }
    }

    else {
      return false;  // not a reboot setter — let parse_command's ladder continue
    }

    return true;
}
