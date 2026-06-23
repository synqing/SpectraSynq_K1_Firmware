#ifndef ENCODERS_H
#define ENCODERS_H

#include <Arduino.h>
#include <Wire.h>
#include <stdint.h>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>
#include "m5rotate8.h"
#include <USB.h>
#include <math.h> // For fabs
#include "constants.h" // For NUM_MODES
#include "globals.h"   // For conf, KNOB, other externs
#include "Palettes.h"  // For gGradientPaletteCount, paletteNames


// Forward declarations if needed (assuming defined elsewhere)
// enum lightshow_modes : uint8_t; // Assuming defined in lightshow_modes.h or similar
struct conf;
struct KNOB;
void attempt_rotate8_init(bool verbose);


extern M5ROTATE8 rotate8;
extern uint32_t g_last_encoder_activity_time;
extern uint8_t g_last_active_encoder;
extern conf CONFIG;
extern bool settings_updated;
extern bool debug_mode;
// extern bool mode_transition_queued; // No longer directly set here
extern uint32_t next_save_time;
// extern enum lightshow_modes; // Declaration moved or assumed included
extern KNOB knob_photons;
extern KNOB knob_chroma;
extern KNOB knob_mood;
extern uint8_t SECONDARY_PALETTE_INDEX;    // Secondary channel palette index
extern bool SECONDARY_PALETTE_MODE_ENABLED; // Secondary channel palette mode flag

// New global variables for encoder state management
extern bool g_rotate8_available; // Track whether the encoder is available
extern uint32_t g_next_recovery_attempt; // When to attempt reconnection
extern bool encoder3_in_contrast_mode; // Track when encoder 3 is in contrast mode
extern uint32_t encoder3_button_hold_start; // For detecting long-press

// Move these to file scope if needed by multiple functions:
static bool encoder_error_state = false;
static uint32_t error_recovery_time = 0;

// --- Fixed-Point Type Alias ---
using ConfigFixed = SQ15x16; // Alias for the fixed-point type used in config

// --- Encoder 0 State ---
static bool encoder0_in_base_intensity_mode = false;
static uint32_t encoder0_last_press_time = 0;
static uint8_t encoder0_press_count = 0;
static const uint32_t double_press_window = 300; // Double-press time window (ms)

void init_encoders();
void check_encoders(uint32_t t_now);
void update_encoder_leds();

void init_encoders() {
    // --- I2C Bus Clearing Logic ---
    // Attempt to free up the I2C bus if a slave device is holding SDA low
    const int SDA_PIN = I2C_SDA_PIN;
    const int SCL_PIN = I2C_SCL_PIN; // Bit-banged below to clear the bus
    pinMode(SCL_PIN, OUTPUT);
    digitalWrite(SCL_PIN, HIGH);
    for (int i = 0; i < 9; i++) { // Toggle SCL 9 times
        digitalWrite(SCL_PIN, LOW);
        delayMicroseconds(5); // Small delay
        digitalWrite(SCL_PIN, HIGH);
        delayMicroseconds(5);
    }
    // SCL is left HIGH, which is the idle state
    // Now initialize the Wire library

    Wire.begin(SDA_PIN, SCL_PIN); // Use defined SDA/SCL pins
    delay(300); // Keep the existing delay
    attempt_rotate8_init(true);
}

void check_encoders(uint32_t t_now) {
    if (!g_rotate8_available) return;

    // Move static variable declarations to the top of the function
    static const uint32_t button_debounce_time = 400;
    static const uint32_t button_stable_time = 30;
    static const uint32_t long_press_threshold = 800;

    static bool switch_initialized = false;
    static uint8_t switch_raw_state = 0;
    static uint8_t switch_stable_state = 0;
    static uint32_t switch_last_change_time = 0;

    uint8_t sw = rotate8.inputSwitch();
    if (sw <= 1) {
        if (!switch_initialized) {
            switch_initialized = true;
            switch_raw_state = sw;
            switch_stable_state = sw;
            secondaryMode = (switch_stable_state == 1);
        } else if (sw != switch_raw_state) {
            switch_raw_state = sw;
            switch_last_change_time = t_now;
        } else if (switch_stable_state != sw && (t_now - switch_last_change_time) >= button_stable_time) {
            switch_stable_state = sw;
            secondaryMode = (switch_stable_state == 1);
        }
    }

    // --- Fixed-Point Sensitivity Divisors ---
    // Adjust these values as needed for sensitivity tuning with fixed-point
    const ConfigFixed sensitivity_divisor = ConfigFixed(120.0); // Reverted from 60.0 back to original 120.0
    const ConfigFixed sensitivity_divisor_contrast = ConfigFixed(25.0); // Reverted from 12.5 back to original 25.0

    // --- Fixed-Point Limits ---
    const ConfigFixed limit_0_0 = ConfigFixed(0.0);
    const ConfigFixed limit_1_0 = ConfigFixed(1.0);
    const ConfigFixed limit_5_0 = ConfigFixed(5.0);
    const ConfigFixed limit_8_0 = ConfigFixed(8.0);


    static uint32_t last_encoder_check = 0;
    static uint32_t encoder_error_count = 0;
    static int32_t last_encoder_values[8] = {0};
    static int32_t accumulated_values[8] = {0};

    static uint32_t last_encoder_change_time[8] = {0};
    static uint8_t last_active_encoder_id = 255;
    static const uint32_t encoder_lockout_time = 20; // was 50 to allow faster successive inputs
    static int32_t prism_rel_accumulator = 0;
    static int8_t prism_rel_direction = 0;

    bool activity_detected = false;

    if (t_now - last_encoder_check < 5) { // reduced from 20ms to 5ms for quicker reads
        return;
    }
    last_encoder_check = t_now;

    if (encoder_error_state) {
        if (t_now - error_recovery_time < 1000) {
            return;
        }

        g_rotate8_available = false;
        attempt_rotate8_init(false);

        if (!g_rotate8_available) {
            error_recovery_time = t_now;
            g_next_recovery_attempt = t_now + 10000;
            return;
        }

        encoder_error_state = false;
        encoder_error_count = 0;
        for (int i = 0; i < 8; i++) {
            accumulated_values[i] = 0;
            last_encoder_values[i] = 0;
            last_encoder_change_time[i] = 0;
        }
        last_active_encoder_id = 255;
        USBSerial.println("M5Rotate8 recovered via check_encoders.");
    }

    auto safeGetRelCounter = [&](uint8_t channel) -> int32_t {
        int32_t value = 0;
        bool read_successful = false;

        if (last_active_encoder_id != 255 &&
            last_active_encoder_id != channel &&
            (t_now - last_encoder_change_time[last_active_encoder_id] < encoder_lockout_time)) {
            return 0;
        }

        value = rotate8.getRelCounter(channel);
        read_successful = true;

        if (read_successful) {
            if (value > 40 || value < -40) {
                encoder_error_count++;
                value = 0;
            } else if (value != 0) {
                accumulated_values[channel] += value;

                if (accumulated_values[channel] > 100) accumulated_values[channel] = 100;
                if (accumulated_values[channel] < -100) accumulated_values[channel] = -100;

                last_encoder_change_time[channel] = t_now;
                last_active_encoder_id = channel;

                value = accumulated_values[channel];
                accumulated_values[channel] = 0;

                encoder_error_count = 0;
            } else {
                // Value is 0, potentially reset accumulator if needed, but currently reset on non-zero read.
                // Reset error counter if value is 0? Maybe not, could mask intermittent issues.
            }
        } else {
            // Treat read failure as an error (if we had a way to detect it explicitly)
            // encoder_error_count++;
            // value = 0;
        }

        if (encoder_error_count > 5) {
            encoder_error_state = true;
            error_recovery_time = t_now;
            g_rotate8_available = false;
            g_next_recovery_attempt = t_now + 5000;
            USBSerial.println("WARNING: Encoder communication errors detected. Entering recovery mode.");
            for (int i = 0; i < 8; i++) {
                accumulated_values[i] = 0;
            }
            return 0;
        }

        return value;
    };

    static uint32_t last_debug_time = 0;
    auto debugEncoder = [&](uint8_t channel, int32_t value, const char* name, ConfigFixed new_value) {
        if (value != 0 && (t_now - last_debug_time) > 100) {
            USBSerial.print("[DBG E");
            USBSerial.print(channel);
            USBSerial.print("] [");
            USBSerial.print(secondaryMode ? "Channel 2" : "Channel 1"); // Add channel info
            USBSerial.print("] Raw: ");
            USBSerial.print(value);
            USBSerial.print(" | New ");
            USBSerial.print(name);
            USBSerial.print(": ");
            USBSerial.println(float(new_value)); // Cast fixed-point to float for printing
            last_debug_time = t_now;
        }
    };

    struct ButtonDebounceState {
        bool initialized;
        bool raw_state;
        bool stable_state;
        uint32_t last_raw_change_time;
        uint32_t last_release_event_time;
    };
    static ButtonDebounceState button_states[8] = {};

    auto updateButton = [&](uint8_t channel) -> int8_t {
        ButtonDebounceState& state = button_states[channel];
        bool raw_state = rotate8.getKeyPressed(channel);

        if (!state.initialized) {
            state.initialized = true;
            state.raw_state = raw_state;
            state.stable_state = raw_state;
            state.last_raw_change_time = t_now;
            return 0;
        }

        if (raw_state != state.raw_state) {
            state.raw_state = raw_state;
            state.last_raw_change_time = t_now;
            return 0;
        }

        if (state.stable_state != raw_state && (t_now - state.last_raw_change_time) >= button_stable_time) {
            state.stable_state = raw_state;
            return raw_state ? 1 : -1;
        }

        return 0;
    };

    auto releaseAllowed = [&](uint8_t channel) -> bool {
        ButtonDebounceState& state = button_states[channel];
        if (t_now - state.last_release_event_time <= button_debounce_time) {
            return false;
        }
        state.last_release_event_time = t_now;
        return true;
    };

    // --- Check for single press timeout on Encoder 0 ---
    if (encoder0_press_count == 1 && (t_now - encoder0_last_press_time > double_press_window)) {
        // Double press window expired, treat as single press
        activity_detected = true;
        g_last_active_encoder = 0;
        
        // --- Temporary Debug for Mode 5 Base Coat Bug ---
        bool is_mode5_ch1 = (!secondaryMode && CONFIG.LIGHTSHOW_MODE == LIGHT_MODE_KALEIDOSCOPE);
        if (is_mode5_ch1) {
             if (true) {
                 USBSerial.println("[DBG E0 KALEIDO]: Single press detected (Base Coat toggle bypassed)");
             }
        } else {
        // --- Original Base Coat Toggle Logic ---
            if (!secondaryMode) {
                CONFIG.BASE_COAT = !CONFIG.BASE_COAT;
            } else {
                SECONDARY_BASE_COAT = !SECONDARY_BASE_COAT;
            }
            settings_updated = true;
            if (true) {
                USBSerial.print("[DBG E0] Single Press Timeout | BASE_COAT: ");
                USBSerial.println((secondaryMode ? SECONDARY_BASE_COAT : CONFIG.BASE_COAT) ? "ON" : "OFF");
            }
        } // --- End of temporary debug block ---

        encoder0_press_count = 0; // Reset press count
    }

    // Channel 0: Photons OR Base Coat Intensity
    int32_t encoder0_rel = safeGetRelCounter(0);
    if (encoder0_rel != 0) {
        activity_detected = true;
        g_last_active_encoder = 0;
        if (!secondaryMode) {
            // --- PRIMARY CHANNEL 0 --- 
            if (encoder0_in_base_intensity_mode) {
                // --- Adjust Base Coat Intensity --- 
                ConfigFixed change = ConfigFixed(encoder0_rel) / sensitivity_divisor;
                ConfigFixed current_val = CONFIG.BASE_COAT_INTENSITY;
                ConfigFixed new_value = current_val + change;
                if (new_value > limit_1_0) new_value = limit_1_0;
                if (new_value < limit_0_0) new_value = limit_0_0;
                if (new_value != current_val) {
                    CONFIG.BASE_COAT_INTENSITY = float(new_value);
                    settings_updated = true;
                    debugEncoder(0, encoder0_rel, "BASE_INTENSITY", new_value);
                }
            } else {
                // --- Adjust Photons --- 
                ConfigFixed change = ConfigFixed(encoder0_rel) / sensitivity_divisor;
                ConfigFixed current_val = CONFIG.PHOTONS;
                ConfigFixed new_value = current_val + change;
                if (new_value > limit_1_0) new_value = limit_1_0;
                if (new_value < limit_0_0) new_value = limit_0_0;
                if (new_value != current_val) {
                    CONFIG.PHOTONS = float(new_value);
                    settings_updated = true;
                    debugEncoder(0, encoder0_rel, "PHOTONS", new_value);
                }
            }
        } else {
            // --- SECONDARY CHANNEL 0 --- 
             if (encoder0_in_base_intensity_mode) {
                // --- Adjust Secondary Base Coat Intensity --- 
                ConfigFixed change = ConfigFixed(encoder0_rel) / sensitivity_divisor;
                ConfigFixed current_val = SECONDARY_BASE_COAT_INTENSITY;
                ConfigFixed new_value = current_val + change;
                if (new_value > limit_1_0) new_value = limit_1_0;
                if (new_value < limit_0_0) new_value = limit_0_0;
                if (new_value != current_val) {
                    SECONDARY_BASE_COAT_INTENSITY = float(new_value);
                    settings_updated = true;
                    debugEncoder(0, encoder0_rel, "SEC_BASE_INTENSITY", new_value);
                }
            } else {
                // --- Adjust Secondary Photons ---
                ConfigFixed change = ConfigFixed(encoder0_rel) / sensitivity_divisor;
                ConfigFixed current_val = SECONDARY_PHOTONS;
                ConfigFixed new_value = current_val + change;
                if (new_value > limit_1_0) new_value = limit_1_0;
                // Floor at 0.05 (not 0.0): prevents secondary channel from going completely
                // dark via accumulated CCW encoder ticks. At 0 PHOTONS, apply_brightness_secondary
                // multiplies every secondary LED by 0² × silent_scale = 0 → uniform black until
                // factory_reset. Floor 0.05 → bright_val ≈ 0.0025, a faint glow that confirms
                // the encoder is still alive and the channel is recoverable with a CW tick.
                const ConfigFixed limit_sec_photons_floor = ConfigFixed(0.05);
                if (new_value < limit_sec_photons_floor) new_value = limit_sec_photons_floor;
                if (new_value != current_val) {
                    SECONDARY_PHOTONS = float(new_value);
                    settings_updated = true;
                    debugEncoder(0, encoder0_rel, "SEC_PHOTONS", new_value);
                }
            }
        }
    }

    // Channel 1: Chroma
    int32_t chroma_rel = safeGetRelCounter(1);
    if (chroma_rel != 0) {
        ConfigFixed change = ConfigFixed(chroma_rel) / sensitivity_divisor;
        ConfigFixed current_val = secondaryMode ? SECONDARY_CHROMA : CONFIG.CHROMA;
        ConfigFixed new_value = current_val + change;

        if (new_value > limit_1_0) new_value = limit_1_0;
        if (new_value < limit_0_0) new_value = limit_0_0;

        if (new_value != current_val) {
            activity_detected = true;
            g_last_active_encoder = 1;
            if (!secondaryMode) CONFIG.CHROMA = float(new_value);
            else SECONDARY_CHROMA = float(new_value);
            settings_updated = true;
            debugEncoder(1, chroma_rel, "CHROMA", new_value);
        }
    }

    // Add button handling for encoder 0 to toggle BASE_COAT / Base Intensity Mode
    static uint32_t encoder0_button_hold_start = 0; // Keep for potential future long-press?
    int8_t encoder0_button_event = updateButton(0);

    if (encoder0_button_event == 1) {
        // Button Down
        encoder0_button_hold_start = t_now; // Record time for potential long press
    }
    else if (encoder0_button_event == -1) {
        // Button Up (Release)
        if (releaseAllowed(0)) { // Debounce on release
            encoder0_press_count++;
            if (encoder0_press_count == 1) {
                // First press, record time and wait for potential second press
                encoder0_last_press_time = t_now;
            } else if (encoder0_press_count == 2) {
                // Second press within window? (Check time diff)
                if (t_now - encoder0_last_press_time <= double_press_window) {
                    // --- Double Press Detected --- 
                    encoder0_in_base_intensity_mode = !encoder0_in_base_intensity_mode;
                    activity_detected = true;
                    g_last_active_encoder = 0;
                    settings_updated = true;
                    if (true) {
                        USBSerial.print("[DBG E0] Double Press | Base Intensity Mode: ");
                        USBSerial.println(encoder0_in_base_intensity_mode ? "ON" : "OFF");
                    }
                    encoder0_press_count = 0; // Reset count
                } else {
                    // Second press occurred *after* double press window - treat as first press of a new sequence
                    encoder0_press_count = 1;
                    encoder0_last_press_time = t_now;
                }
            }
        } else {
            // Debounced out, ignore this release
        }
    }

    // Add button handling for encoder 1 to toggle AUTO_COLOR_SHIFT
    static uint32_t encoder1_button_hold_start = 0;
    int8_t encoder1_button_event = updateButton(1);
    if (encoder1_button_event == 1) {
        encoder1_button_hold_start = t_now;
    }
    else if (encoder1_button_event == -1) {
        if (releaseAllowed(1)) {
            activity_detected = true;
            g_last_active_encoder = 1;
            if (!secondaryMode) {
                CONFIG.AUTO_COLOR_SHIFT = !CONFIG.AUTO_COLOR_SHIFT;
            } else {
                SECONDARY_AUTO_COLOR_SHIFT = !SECONDARY_AUTO_COLOR_SHIFT;
            }
            settings_updated = true;
            if (true) {
                USBSerial.print("[DBG E1] Button Press | AUTO_COLOR_SHIFT: ");
                USBSerial.println((secondaryMode ? SECONDARY_AUTO_COLOR_SHIFT : CONFIG.AUTO_COLOR_SHIFT) ? "ON" : "OFF");
            }
        }
    }

    // Channel 2: Mood
    int32_t mood_rel = safeGetRelCounter(2);
    if (mood_rel != 0) {
        ConfigFixed change = ConfigFixed(mood_rel) / sensitivity_divisor;
        ConfigFixed current_val = secondaryMode ? SECONDARY_MOOD : CONFIG.MOOD;
        ConfigFixed new_value = current_val + change;

        if (new_value > limit_1_0) new_value = limit_1_0;
        if (new_value < limit_0_0) new_value = limit_0_0;

        if (new_value != current_val) {
            activity_detected = true;
            g_last_active_encoder = 2;
            if (!secondaryMode) CONFIG.MOOD = float(new_value);
            else SECONDARY_MOOD = float(new_value);
            settings_updated = true;
            debugEncoder(2, mood_rel, "MOOD", new_value);
        }
    }

    static uint32_t encoder3_last_press_time = 0;
    static uint8_t encoder3_press_count = 0;

    // --- Check for single press timeout on Encoder 3 ---
    if (encoder3_press_count == 1 && (t_now - encoder3_last_press_time > double_press_window)) {
        // Double press window expired, treat as single press
        activity_detected = true;
        g_last_active_encoder = 3;
        
        if (encoder3_in_contrast_mode) {
            // Reset contrast to default float value for the primary channel
            // (Contrast mode only affects primary for now)
            CONFIG.SQUARE_ITER = 1.0f; 
            settings_updated = true;
            if (true){
                USBSerial.print("[DBG E3] Single Press Timeout (in Contrast) | Reset Contrast [Ch1] to: ");
                USBSerial.println(CONFIG.SQUARE_ITER);
            }
        } else {
            // Cycle lightshow mode for the appropriate channel(s)
            if (!secondaryMode) {
                // Primary channel is active, cycle primary mode
                CONFIG.LIGHTSHOW_MODE = (CONFIG.LIGHTSHOW_MODE + 1) % NUM_MODES;
                if (true){
                    USBSerial.print("[DBG E3] Single Press Timeout | New Light Mode [Ch1]: ");
                    USBSerial.print(mode_names + (CONFIG.LIGHTSHOW_MODE * 32)); 
                    USBSerial.print(" ("); USBSerial.print(CONFIG.LIGHTSHOW_MODE); USBSerial.println(")");
                }
            } else {
                // Secondary channel is active, cycle secondary mode
                SECONDARY_LIGHTSHOW_MODE = (SECONDARY_LIGHTSHOW_MODE + 1) % NUM_MODES;
                 if (true){
                    USBSerial.print("[DBG E3] Single Press Timeout | New Light Mode [Ch2]: ");
                    USBSerial.print(mode_names + (SECONDARY_LIGHTSHOW_MODE * 32)); 
                    USBSerial.print(" ("); USBSerial.print(SECONDARY_LIGHTSHOW_MODE); USBSerial.println(")");
                }
            }
            settings_updated = true;
        }
        encoder3_press_count = 0; // Reset press count
    }

    // --- Encoder 3 Button Press/Release Handling ---
    int8_t encoder3_button_event = updateButton(3);

    if (encoder3_button_event == 1) {
        // Button Down
        // No need to record hold start time anymore
    }
    else if (encoder3_button_event == -1) {
        // Button Up (Release)
        if (releaseAllowed(3)) { // Debounce on release
            encoder3_press_count++;
            if (encoder3_press_count == 1) {
                // First press, record time and wait for potential second press
                encoder3_last_press_time = t_now;
            } else if (encoder3_press_count == 2) {
                // Second press within window?
                if (t_now - encoder3_last_press_time <= double_press_window) {
                    // --- Double Press Detected --- 
                    // Toggle contrast mode (affects primary only for now)
                    encoder3_in_contrast_mode = !encoder3_in_contrast_mode;
                    activity_detected = true;
                    g_last_active_encoder = 3;
                    settings_updated = true; // Config might not change, but state does
                    if (true) {
                        USBSerial.print("[DBG E3] Double Press | Contrast Mode: ");
                        USBSerial.println(encoder3_in_contrast_mode ? "ON" : "OFF");
                    }
                    encoder3_press_count = 0; // Reset count
                } else {
                    // Second press occurred *after* double press window - treat as first press of a new sequence
                    encoder3_press_count = 1;
                    encoder3_last_press_time = t_now;
                }
            }
        } else {
            // Debounced out, ignore this release
        }
    }

    // --- Encoder 3 Rotation Handling ---
    if (encoder3_in_contrast_mode) {
        int32_t contrast_rel = safeGetRelCounter(3);
        if (contrast_rel != 0) {
            ConfigFixed contrast_change = ConfigFixed(contrast_rel) / sensitivity_divisor_contrast;
            // Read the current float value
            ConfigFixed current_val = ConfigFixed(CONFIG.SQUARE_ITER);
            ConfigFixed new_value = current_val + contrast_change;

            // Constrain using fixed-point values
            if (new_value > limit_5_0) new_value = limit_5_0;
            if (new_value < limit_0_0) new_value = limit_0_0;

            if (new_value != current_val) {
                activity_detected = true;
                g_last_active_encoder = 3;
                // Store the new value as float
                CONFIG.SQUARE_ITER = float(new_value);
                settings_updated = true;
                if (true) {
                    USBSerial.print("[DBG E3 ROT] Raw: "); USBSerial.print(contrast_rel);
                    USBSerial.print(" | New Contrast: "); USBSerial.println(CONFIG.SQUARE_ITER);
                }
            }
        }
    } else {
        // --- Adjust Mood (Speed) ---
        int32_t mood_rel_enc3 = safeGetRelCounter(3); // Use channel 3
        if (mood_rel_enc3 != 0) {
            ConfigFixed change = ConfigFixed(mood_rel_enc3) / sensitivity_divisor; // Use standard divisor
            ConfigFixed current_val = secondaryMode ? SECONDARY_MOOD : CONFIG.MOOD;
            ConfigFixed new_value = current_val + change;

            if (new_value > limit_1_0) new_value = limit_1_0;
            if (new_value < limit_0_0) new_value = limit_0_0;

            if (new_value != current_val) {
                activity_detected = true;
                g_last_active_encoder = 3; // Encoder 3 is active
                if (!secondaryMode) CONFIG.MOOD = float(new_value);
                else SECONDARY_MOOD = float(new_value);
                settings_updated = true;
                // Use existing debugEncoder function, note it's Encoder 3 controlling MOOD
                debugEncoder(3, mood_rel_enc3, "MOOD", new_value);
            }
        }
    }

    // Channel 4: Saturation
    int32_t sat_rel = safeGetRelCounter(4);
    if (sat_rel != 0) {
        ConfigFixed change = ConfigFixed(sat_rel) / sensitivity_divisor;
        ConfigFixed current_val = secondaryMode ? SECONDARY_SATURATION : CONFIG.SATURATION;
        ConfigFixed new_val = current_val + change;

        if (new_val > limit_1_0) new_val = limit_1_0;
        if (new_val < limit_0_0) new_val = limit_0_0;

        if (new_val != current_val) {
            activity_detected = true;
            g_last_active_encoder = 4;
            if (!secondaryMode) CONFIG.SATURATION = float(new_val);
            else SECONDARY_SATURATION = float(new_val);
            settings_updated = true;
            debugEncoder(4, sat_rel, "SATURATION", new_val);
        }
    }

    // Channel 5: Prism count
    int32_t encoder5_rel = safeGetRelCounter(5);
    if (encoder5_rel != 0) {
        int8_t direction = (encoder5_rel > 0) ? 1 : -1;
        if (prism_rel_direction != 0 && direction != prism_rel_direction) {
            prism_rel_accumulator = 0;
        }
        prism_rel_direction = direction;
        prism_rel_accumulator += encoder5_rel;

        const int32_t prism_detent_counts = 2;
        int32_t prism_steps = 0;
        while (prism_rel_accumulator >= prism_detent_counts) {
            prism_steps++;
            prism_rel_accumulator -= prism_detent_counts;
        }
        while (prism_rel_accumulator <= -prism_detent_counts) {
            prism_steps--;
            prism_rel_accumulator += prism_detent_counts;
        }

        if (prism_steps != 0) {
            activity_detected = true;
            g_last_active_encoder = 5;
            ConfigFixed change = ConfigFixed(prism_steps) * ConfigFixed(0.25);
            ConfigFixed current_val = secondaryMode ? ConfigFixed(SECONDARY_PRISM_COUNT) : ConfigFixed(CONFIG.PRISM_COUNT);
            ConfigFixed new_val = current_val + change;

            if (new_val > limit_8_0) new_val = limit_8_0;
            if (new_val < limit_0_0) new_val = limit_0_0;

            if (new_val != current_val) {
                if (!secondaryMode) {
                    CONFIG.PRISM_COUNT = float(new_val);
                } else {
                    SECONDARY_PRISM_COUNT = float(new_val);
                }
                settings_updated = true;
                if ((t_now - last_debug_time) > 100) {
                    USBSerial.print("[DBG E5] [");
                    USBSerial.print(secondaryMode ? "Channel 2" : "Channel 1");
                    USBSerial.print("] Step: ");
                    USBSerial.print(prism_steps);
                    USBSerial.print(" | Candidate PRISM_COUNT: ");
                    USBSerial.print(float(new_val), 2);
                    USBSerial.print(" | Stored PRISM_COUNT: ");
                    USBSerial.println(secondaryMode ? SECONDARY_PRISM_COUNT : CONFIG.PRISM_COUNT, 2);
                    last_debug_time = t_now;
                }
            }
        }
    }

    // Channel 6: Palette index; rotating enables palette mode for the active channel
    int32_t palette_rel = safeGetRelCounter(6);
    if (palette_rel != 0) {
        activity_detected = true;
        g_last_active_encoder = 6;

        uint8_t current_palette = secondaryMode ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
        uint8_t new_palette = current_palette;

        if (palette_rel > 0) {
            new_palette = (current_palette + 1) % gGradientPaletteCount;
        } else {
            new_palette = (current_palette + gGradientPaletteCount - 1) % gGradientPaletteCount;
        }

        if (!secondaryMode) {
            if (!CONFIG.PALETTE_MODE_ENABLED) {
                CONFIG.PALETTE_MODE_ENABLED = true;
                settings_updated = true;
                USBSerial.println("[DBG E6 ROT] Palette Mode Enabled [Ch1]");
            }
            CONFIG.PALETTE_INDEX = new_palette;
        } else {
            if (!SECONDARY_PALETTE_MODE_ENABLED) {
                SECONDARY_PALETTE_MODE_ENABLED = true;
                settings_updated = true;
                USBSerial.println("[DBG E6 ROT] Palette Mode Enabled [Ch2]");
            }
            SECONDARY_PALETTE_INDEX = new_palette;
        }

        if (new_palette != current_palette) {
            settings_updated = true;
            USBSerial.print("[DBG E6 ROT] Palette Index [Ch");
            USBSerial.print(secondaryMode ? "2" : "1");
            USBSerial.print("]: ");
            USBSerial.print(new_palette);
            char buffer[32];
            strcpy_P(buffer, (const char *)pgm_read_ptr(&(paletteNames[new_palette])));
            USBSerial.print(" ("); USBSerial.print(buffer); USBSerial.println(")");
        }
    }

    // Encoder 6 button toggles incandescent mode for the active channel
    int8_t encoder6_button_event = updateButton(6);

    if (encoder6_button_event == 1) {
        // Button Down
    }
    else if (encoder6_button_event == -1) {
        if (releaseAllowed(6)) {
            activity_detected = true;
            g_last_active_encoder = 6;
            if (!secondaryMode) {
                CONFIG.INCANDESCENT_MODE = !CONFIG.INCANDESCENT_MODE;
                USBSerial.print("[DBG E6 BTN] Incandescent Mode [Ch1]: ");
                USBSerial.println(CONFIG.INCANDESCENT_MODE ? "ON" : "OFF");
            } else {
                SECONDARY_INCANDESCENT_MODE = !SECONDARY_INCANDESCENT_MODE;
                USBSerial.print("[DBG E6 BTN] Incandescent Mode [Ch2]: ");
                USBSerial.println(SECONDARY_INCANDESCENT_MODE ? "ON" : "OFF");
            }
            settings_updated = true;
        }
    }

    // Channel 7: Bulb opacity (Does not have a secondary equivalent)
    int32_t bulb_rel = safeGetRelCounter(7);
    if (bulb_rel != 0) {
        ConfigFixed change = ConfigFixed(bulb_rel) / sensitivity_divisor;
        ConfigFixed current_val = CONFIG.BULB_OPACITY; // Assumes this is ConfigFixed
        ConfigFixed new_value = current_val + change;

        if (new_value > limit_1_0) new_value = limit_1_0;
        if (new_value < limit_0_0) new_value = limit_0_0;

        if (new_value != current_val) {
            activity_detected = true;
            g_last_active_encoder = 7;
            CONFIG.BULB_OPACITY = float(new_value);
            settings_updated = true;
            debugEncoder(7, bulb_rel, "BULB_OPACITY", new_value);
        }
    }

    if (activity_detected) {
        g_last_encoder_activity_time = t_now;
        next_save_time = t_now + 3000;
    }

    if (activity_detected) {
        if (g_last_active_encoder == 0) knob_photons.last_change = g_last_encoder_activity_time;
        if (g_last_active_encoder == 1) knob_chroma.last_change = g_last_encoder_activity_time;
        if (g_last_active_encoder == 2) knob_mood.last_change = g_last_encoder_activity_time;
    }
}

void update_encoder_leds() {
    if (!g_rotate8_available) return;

    static const uint8_t active_colors[8][3] = {
        {64, 64, 64},
        {0, 128, 128},
        {128, 128, 0},
        {0, 128, 0},
        {128, 0, 128},
        {192, 192, 0},
        {0, 128, 128},
        {192, 96, 0}
    };

    // Define colours for different modes
    const uint8_t contrast_color[3] = {0, 200, 0}; // Bright Green for Contrast
    const uint8_t base_intensity_color[3] = {150, 150, 150}; // White for Base Intensity
    const uint8_t palette_mode_color[3] = {0, 0, 200}; // Bright Blue for Palette Mode
    
    static uint8_t mode_indicator_brightness = 0; // For pulsing effect
    static uint32_t last_pulse_time = 0;
    static bool pulse_direction = true;
    static const uint32_t pulse_interval = 20;
    
    // --- Base Intensity Mode Indicator Pulse ---
    static uint8_t base_intensity_indicator = 0;
    static uint32_t last_base_pulse_time = 0;
    static bool base_pulse_direction = true;
    static const uint32_t base_pulse_interval = 25; // Slightly different pulse rate

    // Pulse for Contrast Mode (Encoder 3)
    if (encoder3_in_contrast_mode && (millis() - last_pulse_time > pulse_interval)) {
        if (pulse_direction) {
            mode_indicator_brightness = min(mode_indicator_brightness + 8, 128);
            if (mode_indicator_brightness == 128) pulse_direction = false;
        } else {
            mode_indicator_brightness = max(mode_indicator_brightness - 8, 10);
            if (mode_indicator_brightness == 10) pulse_direction = true;
        }
        last_pulse_time = millis();
    }

    // Pulse for Base Intensity Mode (Encoder 0)
    if (encoder0_in_base_intensity_mode && (millis() - last_base_pulse_time > base_pulse_interval)) {
        if (base_pulse_direction) {
            base_intensity_indicator = min(base_intensity_indicator + 10, 150); // Brighter pulse maybe?
            if (base_intensity_indicator == 150) base_pulse_direction = false;
        } else {
            base_intensity_indicator = max(base_intensity_indicator - 10, 15);
            if (base_intensity_indicator == 15) base_pulse_direction = true;
        }
        last_base_pulse_time = millis();
    }

    static uint8_t inactive_r = 0;
    static uint8_t inactive_g = 0;
    static uint8_t inactive_b = 4;

    static uint32_t last_led_update_check_time = 0;
    static uint8_t current_active_encoder = 255;
    static uint8_t last_written_states[9] = {255};
    static const uint32_t led_update_interval = 100;

    uint32_t current_millis = millis();
    if (current_millis - last_led_update_check_time > led_update_interval) {
        last_led_update_check_time = current_millis;

        const uint32_t active_timeout = 2000;
        if (current_millis - g_last_encoder_activity_time < active_timeout) {
            current_active_encoder = g_last_active_encoder;
        } else {
            current_active_encoder = 255;
            encoder3_in_contrast_mode = false;
        }

        for (uint8_t i = 0; i < 8; i++) {
            uint8_t desired_state;

            if (i == 3 && encoder3_in_contrast_mode) {
                desired_state = 2;
            } else if (i == 0 && encoder0_in_base_intensity_mode) {
                desired_state = 3;
            } else if (i == 6 && ((secondaryMode && SECONDARY_PALETTE_MODE_ENABLED) ||
                                  (!secondaryMode && CONFIG.PALETTE_MODE_ENABLED))) {
                desired_state = 4;
            } else if (i == current_active_encoder) {
                desired_state = 1;
            } else {
                desired_state = 0;
            }

            if (desired_state != last_written_states[i]) {
                bool write_success = false;
                if (desired_state == 2) {
                    write_success = rotate8.writeRGB(i, contrast_color[0], mode_indicator_brightness, contrast_color[2]);
                } else if (desired_state == 3) {
                     write_success = rotate8.writeRGB(i, mode_indicator_brightness, mode_indicator_brightness, mode_indicator_brightness);
                } else if (desired_state == 4) {
                     write_success = rotate8.writeRGB(i, palette_mode_color[0], palette_mode_color[1], mode_indicator_brightness); 
                } else if (desired_state == 1) {
                    write_success = rotate8.writeRGB(i, active_colors[i][0], active_colors[i][1], active_colors[i][2]);
                } else {
                    write_success = rotate8.writeRGB(i, inactive_r, inactive_g, inactive_b);
                }

                if (write_success) {
                    last_written_states[i] = desired_state;
                } else {
                    g_rotate8_available = false;
                    g_next_recovery_attempt = current_millis + 5000;
                    encoder_error_state = true;
                    error_recovery_time = current_millis;
                    USBSerial.println("WARNING: Encoder LED write error. Entering recovery mode.");
                    return;
                }
            }
        }

        if (last_written_states[8] != 0) {
            bool write_success = rotate8.writeRGB(8, 0, 0, 0);
            if (write_success) {
                last_written_states[8] = 0;
            } else {
                g_rotate8_available = false;
                g_next_recovery_attempt = current_millis + 5000;
                encoder_error_state = true;
                error_recovery_time = current_millis;
                USBSerial.println("WARNING: Encoder LED 8 write error. Entering recovery mode.");
            }
        }
    }
}

#endif
