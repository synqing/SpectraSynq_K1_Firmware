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
#include "sb_effect_queue.h"        // sb_queue_* setters/getters + SB_QUEUE_* enums (queue family)
#include "sb_smart_director.h"      // SBSmartDirectorConfig + sb_smart_director_config/set_config (smart_director)
#include "sb_mode_selection.h"      // sb_mode_selection_init (smart_switching)
#include "sb_visual_hooks.h"        // SBVisualHookConfig + sb_visual_hooks_config/set_config (smart_visual)
#include "sb_edgemixer_lite.h"      // SBEdgeMixerConfig/SBEdgeMixerMode + sb_edgemixer_lite_config/set_config (edge_mixer)

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

// set_preset() is an external-linkage header-body fn in system/presets.h (included
// ONLY by the .ino TU, so the firmware links that single definition). Forward-declare
// here — same cross-TU pattern as save_config_delayed above — so the moved preset body
// links against it. (Host: the serial_replay oracle driver provides void set_preset(char*){}.)
extern void set_preset(char* preset_name);

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

// vp_set_flag_command / vp_set_float_command are external-linkage free functions
// defined in serial_menu.h:876/893 (the VP tuning helpers). The VP-tuning dispatcher
// calls them; forward-declare here so this TU links against that single definition
// (same pattern as serial_print_palette_line above).
bool vp_set_flag_command(const char* command_type, const char* command_data, bool* flag);
bool vp_set_float_command(const char* command_type, const char* command_data, float* value, float min_value, float max_value);

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

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_vp_tuning — the 17 production-live VP-tuning handlers,
// lifted VERBATIM from parse_command()'s else-if ladder (lines 3038–3104).
// The `if (false) {}` opener keeps every real branch as a statement-identical
// `else if (strcmp(command_type, "<name>") == 0)`. No save_config, no reboot.
// Returns true iff a branch matched; false routes parse_command to its remaining
// ladder + bad_command. Gated by the Fα serial_replay golden — it must reproduce
// byte-for-byte after this move (tests/test_golden_master.py + harness_selftest.py).
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_vp_tuning(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "vp_agc_soft") == 0 || strcmp(command_type, "vp_fix1") == 0) {
      vp_set_flag_command(command_type, command_data, &VP_FIX_AGC_SOFT_KNEE);
    }

    else if (strcmp(command_type, "vp_chroma_gate") == 0 || strcmp(command_type, "vp_fix2") == 0) {
      vp_set_flag_command(command_type, command_data, &VP_FIX_CHROMAGRAM_SPARSENESS);
    }

    else if (strcmp(command_type, "vp_prism_off") == 0 || strcmp(command_type, "vp_fix3") == 0) {
      vp_set_flag_command(command_type, command_data, &VP_FIX_PRISM_DEFAULT_OFF);
    }

    else if (strcmp(command_type, "vp_bloom_decay") == 0 || strcmp(command_type, "vp_fix4") == 0) {
      vp_set_flag_command(command_type, command_data, &VP_FIX_BLOOM_DECAY);
    }

    else if (strcmp(command_type, "vp_hsv_source_sat") == 0 || strcmp(command_type, "vp_fix5") == 0) {
      vp_set_flag_command(command_type, command_data, &VP_FIX_HSV_SOURCE_SAT);
    }

    else if (strcmp(command_type, "vp_secondary_clean") == 0) {
      vp_set_flag_command(command_type, command_data, &VP_FIX_SECONDARY_CLEAN);
    }

    else if (strcmp(command_type, "vp_bloom_alpha") == 0) {
      vp_set_float_command(command_type, command_data, &VP_BLOOM_ALPHA, 0.80f, 1.00f);
    }

    else if (strcmp(command_type, "vp_bloom_shift") == 0) {
      vp_set_float_command(command_type, command_data, &VP_BLOOM_SHIFT_SCALE, 0.25f, 2.00f);
    }

    else if (strcmp(command_type, "vp_bloom_force_sat") == 0) {
      vp_set_flag_command(command_type, command_data, &VP_BLOOM_FORCE_SATURATION);
    }

    else if (strcmp(command_type, "vp_wave_idle_fade") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_IDLE_FADE, 0.50f, 0.999f);
    }

    else if (strcmp(command_type, "vp_wave_raw_margin") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_REACTIVE_RAW_MARGIN, 1.00f, 3.00f);
    }

    else if (strcmp(command_type, "vp_wave_peak_floor") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_REACTIVE_PEAK_FLOOR, 0.00f, 1.00f);
    }

    else if (strcmp(command_type, "vp_wave_active_fade") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_ACTIVE_FADE_REDUCTION, 0.00f, 0.50f);
    }

    else if (strcmp(command_type, "vp_wave_blend_gain") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_CHROMA_BLEND_GAIN, 0.00f, 4.00f);
    }

    else if (strcmp(command_type, "vp_wave_fallback") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_FALLBACK_BRIGHTNESS, 0.00f, 1.00f);
    }

    else if (strcmp(command_type, "vp_wave_vu_floor") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_VU_FLOOR, 0.00f, 1.00f);
    }

    else if (strcmp(command_type, "vp_wave_shift") == 0) {
      vp_set_float_command(command_type, command_data, &VP_WAVEFORM_SHIFT_RATE, 0.00f, 240.00f);
    }

    else {
      return false;  // not a VP-tuning handler — let parse_command's ladder continue
    }

    return true;
}

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_response_gain — the single response_gain handler, lifted
// VERBATIM from parse_command()'s ungated Stage-B branch (serial_menu.h, just
// after serial_cmd_dispatch_reboot_setter). Writes the audio_response_gain inline
// global (globals.h:48) via serial_clamp_float (MIN 0.25, MAX 4.0, DEFAULT 1.0) —
// no save_config, no reboot, and (unlike the pure setters) NO bad_command path
// (atof() fallback: garbage -> 0.0 -> clamp MIN). The `if (false) {}` opener keeps
// the single branch statement-identical. Returns true iff command_type ==
// "response_gain" (the body ran); false routes parse_command to its remaining
// ladder. UNGATED — declared, defined, and called with no #ifdef.
//
// All symbols used are already available in this TU: audio_response_gain /
// DEFAULT_AUDIO_RESPONSE_GAIN / audio_response_gain_clamped() /
// AUDIO_RESPONSE_GAIN_MIN/MAX via globals.h (+ config_types.h), serial_clamp_float
// via serial_parse_helpers.h, tx_begin/tx_end + USBSerial via serial_tx.h/globals.h,
// atof via <stdlib.h>. Gated by the Fα serial_replay golden — it must reproduce
// byte-for-byte after this move (tests/test_golden_master.py + harness_selftest.py).
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_response_gain(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "response_gain") == 0) {
      if (strcmp(command_data, "default") == 0) {
        audio_response_gain = DEFAULT_AUDIO_RESPONSE_GAIN;
      } else {
        audio_response_gain = serial_clamp_float(atof(command_data), AUDIO_RESPONSE_GAIN_MIN, AUDIO_RESPONSE_GAIN_MAX);
      }

      tx_begin();
      USBSerial.print("AUDIO_RESPONSE_GAIN: ");
      USBSerial.println(audio_response_gain_clamped(), 6);
      tx_end();
    }

    else {
      return false;  // not the response_gain handler — let parse_command's ladder continue
    }

    return true;
}

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_queue — the effects-queue / transition family (5 handlers),
// lifted VERBATIM from parse_command()'s ungated Stage-B ladder (serial_menu.h
// spec §4 block): queue_mode, transition_style, transition_dip_ms,
// transition_xfade_ms, commit_quantise. Each calls the sb_queue_* subsystem
// (sb_effect_queue.h) — a host-stubbed FUNCTION-CALL family the replay oracle is
// blind to. The `if (false) {}` opener keeps every branch statement-identical.
// Returns true iff command_type matched one of the five; false routes parse_command
// to its remaining ladder. UNGATED — decl/def/call-site carry no #ifdef.
//
// Behaviour-preservation is proven by the STRUCTURAL-CONTRACT gate (oracle_serial_
// struct.py): the normalized body + dispatch-routing are pinned in serial_struct.
// golden and must reproduce byte-for-byte after this verbatim lift (TRIZ #13/#22 —
// the stubbed sb_queue_* sees a byte-identical call, so its behaviour is irrelevant
// to the proof). All symbols are available in this TU: sb_queue_* + SB_QUEUE_* enums
// via sb_effect_queue.h, tx_begin/tx_end/bad_command via serial_tx.h, USBSerial via
// globals.h, atoi via <stdlib.h>.
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_queue(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "queue_mode") == 0) {
      if (strcmp(command_data, "on") == 0) {
        sb_queue_set_mode_enabled(true);
        tx_begin();
        USBSerial.println("QUEUE_MODE: on");
        tx_end();
      } else if (strcmp(command_data, "off") == 0) {
        sb_queue_set_mode_enabled(false);
        tx_begin();
        USBSerial.println("QUEUE_MODE: off");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "transition_style") == 0) {
      if (strcmp(command_data, "dip") == 0) {
        sb_queue_set_transition_style(SB_QUEUE_TRANSITION_DIP);
        tx_begin();
        USBSerial.println("TRANSITION_STYLE: dip");
        tx_end();
      } else if (strcmp(command_data, "xfade") == 0) {
        sb_queue_set_transition_style(SB_QUEUE_TRANSITION_XFADE);
        tx_begin();
        USBSerial.println("TRANSITION_STYLE: xfade");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "transition_dip_ms") == 0) {
      if (sb_queue_set_dip_ms((uint32_t)atoi(command_data))) {
        tx_begin();
        USBSerial.print("TRANSITION_DIP_MS: ");
        USBSerial.println(sb_queue_dip_ms());
        tx_end();
      } else {
        bad_command(command_type, command_data);  // valid range 60..1000
      }
    }

    else if (strcmp(command_type, "transition_xfade_ms") == 0) {
      if (sb_queue_set_xfade_ms((uint32_t)atoi(command_data))) {
        tx_begin();
        USBSerial.print("TRANSITION_XFADE_MS: ");
        USBSerial.println(sb_queue_xfade_ms());
        tx_end();
      } else {
        bad_command(command_type, command_data);  // valid range 100..3000
      }
    }

    else if (strcmp(command_type, "commit_quantise") == 0) {
      if (strcmp(command_data, "off") == 0) {
        sb_queue_set_commit_quantise(SB_QUEUE_QUANTISE_OFF);
        tx_begin();
        USBSerial.println("COMMIT_QUANTISE: off");
        tx_end();
      } else if (strcmp(command_data, "beat") == 0) {
        sb_queue_set_commit_quantise(SB_QUEUE_QUANTISE_BEAT);
        tx_begin();
        USBSerial.println("COMMIT_QUANTISE: beat");
        tx_end();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else {
      return false;  // not a queue/transition handler — let parse_command's ladder continue
    }

    return true;
}

// ---------------------------------------------------------------------------
// serial_menu.h-local helpers (EXTERNAL linkage; defined in serial_menu.h, included
// only by the .ino TU in firmware and the driver TU in the replay oracle) that the
// smart/edge dispatchers call. Forward-declared here (same pattern as the vivid
// helpers); resolved cross-TU at link. SBEdgeMixerMode comes from sb_edgemixer_lite.h
// (included above), so sb_parse_edge_mode's prototype is valid here.
// ---------------------------------------------------------------------------
void sb_print_smart_status();
void sb_print_edge_status();
bool sb_apply_smart_scene(const char* scene);
bool sb_parse_edge_mode(const char* text, SBEdgeMixerMode* out_mode);

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_smart_director — smart-director control (smart_assist /
// smart_switching / smart_confidence_floor / smart_scene), lifted VERBATIM from
// parse_command()'s ungated ladder. Calls sb_smart_director_* (director TU) +
// sb_mode_selection_init + the external serial_menu.h helpers. Behaviour-preservation
// proven by the serial_struct structural-contract golden (reproduces after this move).
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_smart_director(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "smart_assist") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        SBSmartDirectorConfig config = sb_smart_director_config();
        config.enabled = value;
        if (!value) {
          config.assist_switching_enabled = false;
          config.director_autonomy_enabled = false;
        }
        sb_smart_director_set_config(config);
        sb_print_smart_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "smart_switching") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        SBSmartDirectorConfig config = sb_smart_director_config();
        config.enabled = config.enabled || value;
        config.assist_switching_enabled = value;
        sb_smart_director_set_config(config);
        sb_mode_selection_init(CONFIG.LIGHTSHOW_MODE, millis());
        sb_print_smart_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "smart_confidence_floor") == 0) {
      float value = 0.0f;
      if (vp_parse_float(command_data, &value)) {
        SBSmartDirectorConfig config = sb_smart_director_config();
        config.confidence_floor = constrain(value, 0.0f, 1.0f);
        sb_smart_director_set_config(config);
        sb_print_smart_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "smart_scene") == 0) {
      if (sb_apply_smart_scene(command_data)) {
        sb_print_smart_status();
        sb_print_edge_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else {
      return false;  // not a smart-director handler — let parse_command's ladder continue
    }

    return true;
}

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_smart_visual — visual-hooks toggle (smart_hooks), lifted
// VERBATIM. Calls sb_visual_hooks_* (director TU) + sb_print_smart_status. Ungated.
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_smart_visual(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "smart_hooks") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        SBVisualHookConfig config = sb_visual_hooks_config();
        config.enabled = value;
        sb_visual_hooks_set_config(config);
        sb_print_smart_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else {
      return false;  // not the smart-visual handler — let parse_command's ladder continue
    }

    return true;
}

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_edge_mixer — edge-mixer control (edge_enabled / edge_mode /
// edge_strength), lifted VERBATIM. Calls sb_edgemixer_lite_* (director TU) +
// sb_parse_edge_mode + sb_print_edge_status. Ungated.
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_edge_mixer(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "edge_enabled") == 0) {
      bool value = false;
      if (vp_parse_bool(command_data, &value)) {
        SBEdgeMixerConfig config = sb_edgemixer_lite_config();
        config.enabled = value;
        sb_edgemixer_lite_set_config(config);
        sb_print_edge_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "edge_mode") == 0) {
      SBEdgeMixerMode mode = SB_EDGE_MIXER_OFF;
      if (sb_parse_edge_mode(command_data, &mode)) {
        SBEdgeMixerConfig config = sb_edgemixer_lite_config();
        config.mode = mode;
        if (mode == SB_EDGE_MIXER_OFF) {
          config.enabled = false;
        }
        sb_edgemixer_lite_set_config(config);
        sb_print_edge_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else if (strcmp(command_type, "edge_strength") == 0) {
      float value = 0.0f;
      if (vp_parse_float(command_data, &value)) {
        SBEdgeMixerConfig config = sb_edgemixer_lite_config();
        config.strength = constrain(value, 0.0f, 1.0f);
        sb_edgemixer_lite_set_config(config);
        sb_print_edge_status();
      } else {
        bad_command(command_type, command_data);
      }
    }

    else {
      return false;  // not an edge-mixer handler — let parse_command's ladder continue
    }

    return true;
}

// ---------------------------------------------------------------------------
// serial_cmd_dispatch_preset — the "Set CONFIG preset" handler, lifted VERBATIM
// from parse_command()'s ungated ladder (serial_menu.h "Set CONFIG preset"). The
// single "preset" command validates command_data against 5 theme names, then calls
// set_preset() (presets.h, forward-declared extern above) + save_config_delayed().
// The `if (false) {}` opener keeps the branch a statement-identical
// `else if (strcmp(command_type, "<name>") == 0)`. Returns true iff matched; false
// routes parse_command to its remaining ladder. UNGATED, facade-free.
// Behaviour-preservation across the verbatim lift is proven by the serial_struct
// structural-contract golden (reproduces byte-for-byte after this move).
// ---------------------------------------------------------------------------
bool serial_cmd_dispatch_preset(const char* command_type, char* command_data) {
    if (false) {}

    else if (strcmp(command_type, "preset") == 0) {
      bool good = false;

      if      (strcmp(command_data, "default")      == 0) { good = true; }
      else if (strcmp(command_data, "tinted_bulbs") == 0) { good = true; }
      else if (strcmp(command_data, "incandescent") == 0) { good = true; }
      else if (strcmp(command_data, "white")        == 0) { good = true; }
      else if (strcmp(command_data, "classic")      == 0) { good = true; }

      else { // Bad preset name
        bad_command(command_type, command_data);
      }

      if (good) {
        set_preset(command_data); // presets.h

        save_config_delayed();
        tx_begin();
        USBSerial.print("ENABLED PRESET: ");
        USBSerial.println(command_data);
        tx_end();
      }
    }

    else {
      return false;  // not the preset handler — let parse_command's ladder continue
    }

    return true;
}

#ifdef SB_VIVID_PRECOMP_V1
// ---------------------------------------------------------------------------
// serial_cmd_dispatch_vivid — the 4 vivid pre-comp handlers, lifted VERBATIM
// from parse_command()'s #ifdef SB_VIVID_PRECOMP_V1 block (serial_menu.h
// lines 2521-2574). The `if (false) {}` opener keeps every real branch as a
// statement-identical `else if (strcmp(command_type, "<name>") == 0)`. Each
// writes VP_VIVID_* inline globals — no save_config, no reboot.
// Returns true iff a branch matched; false routes parse_command to its remaining
// ladder + bad_command. Gated by the Fα serial_replay golden — it must reproduce
// byte-for-byte after this move (tests/test_golden_master.py + harness_selftest.py).
//
// Vivid helpers called here are external-linkage free functions defined in
// serial_menu.h (within #ifdef SB_VIVID_PRECOMP_V1):
//   serial_ensure_vivid_defaults()           serial_menu.h:420
//   serial_set_vivid_level(float)            serial_menu.h:427
//   serial_update_vivid_enabled_from_levels() serial_menu.h:416
//   serial_print_vivid_precomp_status()      serial_menu.h:434
// Forward-declared below (same pattern as serial_print_palette_line and
// vp_set_flag/float_command above). vp_parse_bool / vp_parse_float are already
// available via serial_parse_helpers.h (included at top of this TU).
// constrain is an Arduino macro pulled in transitively through globals.h.
// ---------------------------------------------------------------------------
void serial_ensure_vivid_defaults();
void serial_set_vivid_level(float value);
void serial_update_vivid_enabled_from_levels();
void serial_print_vivid_precomp_status();

bool serial_cmd_dispatch_vivid(const char* command_type, char* command_data) {
    if (false) {}

	    else if (strcmp(command_type, "vivid") == 0) {
	      bool value = false;
	      if (vp_parse_bool(command_data, &value)) {
	        VP_VIVID_PRECOMP = value;
	        if (VP_VIVID_PRECOMP) {
	          serial_ensure_vivid_defaults();
	        }
	        tx_begin();
	        serial_print_vivid_precomp_status();
	        tx_end();
	      } else {
	        bad_command(command_type, command_data);
	      }
	    }

	    else if (strcmp(command_type, "vivid_level") == 0) {
	      float value = 0.0f;
	      if (vp_parse_float(command_data, &value)) {
	        serial_set_vivid_level(value);
	        tx_begin();
	        serial_print_vivid_precomp_status();
	        tx_end();
	      } else {
	        bad_command(command_type, command_data);
	      }
	    }

	    else if (strcmp(command_type, "vivid_chroma") == 0) {
	      float value = 0.0f;
	      if (vp_parse_float(command_data, &value)) {
	        VP_VIVID_CHROMA_LEVEL = constrain(value, 0.0f, 1.0f);
	        serial_update_vivid_enabled_from_levels();
	        tx_begin();
	        serial_print_vivid_precomp_status();
	        tx_end();
	      } else {
	        bad_command(command_type, command_data);
	      }
	    }

	    else if (strcmp(command_type, "vivid_black") == 0) {
	      float value = 0.0f;
	      if (vp_parse_float(command_data, &value)) {
	        VP_VIVID_BLACK_LEVEL = constrain(value, 0.0f, 1.0f);
	        serial_update_vivid_enabled_from_levels();
	        tx_begin();
	        serial_print_vivid_precomp_status();
	        tx_end();
	      } else {
	        bad_command(command_type, command_data);
	      }
	    }

    else {
      return false;  // not a vivid handler — let parse_command's ladder continue
    }

    return true;
}
#endif // SB_VIVID_PRECOMP_V1
