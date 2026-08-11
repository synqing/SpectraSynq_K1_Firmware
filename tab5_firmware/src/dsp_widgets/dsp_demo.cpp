/**
 * dsp_demo.cpp
 * Example integration demonstrating how to use DSP widgets in Tab5
 *
 * This file shows:
 * 1. How to create DSP widgets in the UI initialization
 * 2. How to update widgets with OSC data
 * 3. How to integrate tick functions into the main loop
 */

#include "dsp_widgets.h"
#include <math.h>

// Example: Global widget instances
static ppm_meter_t* g_ppm_meter = nullptr;
static mixer_strip_t* g_mixer_strips[3] = {nullptr};  // Speed, Hue, Intensity
static rta_footer_t* g_rta_footer = nullptr;

/**
 * Initialize DSP widgets demo
 * Call this after LVGL display initialization
 */
void dsp_demo_init(lv_obj_t* screen) {
    // Create PPM meter (top-right corner)
    g_ppm_meter = ppm_meter_create(screen, 1000, 20, 260, 150);

    // Create mixer strips (3 parameters: Speed, Hue, Intensity)
    const char* strip_labels[] = {"SPEED", "HUE", "INTENS"};
    for (int i = 0; i < 3; i++) {
        g_mixer_strips[i] = mixer_strip_create(
            screen,
            20 + i * 120,  // X position
            200,            // Y position
            100,            // Width
            400,            // Height
            strip_labels[i]
        );

        // Set initial values
        mixer_strip_update(g_mixer_strips[i], 0.5f);
    }

    // Create RTA footer (bottom of screen)
    g_rta_footer = rta_footer_create(screen, 0, 680, 1280, 40);
}

/**
 * Update DSP widgets with simulated/OSC data
 * Call this when OSC messages arrive
 */
void dsp_demo_update_ppm(float left_db, float right_db) {
    if (g_ppm_meter) {
        ppm_meter_update(g_ppm_meter, left_db, right_db);
    }
}

void dsp_demo_update_param(int param_index, float value) {
    if (param_index >= 0 && param_index < 3 && g_mixer_strips[param_index]) {
        mixer_strip_update(g_mixer_strips[param_index], value);
    }
}

void dsp_demo_update_spectrum(const float* spectrum_data) {
    if (g_rta_footer) {
        rta_footer_update(g_rta_footer, spectrum_data);
    }
}

/**
 * Tick function for animations and peak decay
 * Call this every frame (60 FPS)
 */
void dsp_demo_tick() {
    // PPM peak-hold decay
    if (g_ppm_meter) {
        ppm_meter_tick(g_ppm_meter);
    }

    // Mixer strip smooth animations
    for (int i = 0; i < 3; i++) {
        if (g_mixer_strips[i]) {
            mixer_strip_tick(g_mixer_strips[i]);
        }
    }

    // RTA peak-hold decay
    if (g_rta_footer) {
        rta_footer_tick(g_rta_footer);
    }
}

/**
 * Example: Generate test data for widgets
 * Call this periodically to see animated demo without OSC
 */
void dsp_demo_generate_test_data() {
    static uint32_t frame_count = 0;
    frame_count++;

    // Simulate PPM levels (sine wave)
    float t = frame_count * 0.02f;
    float left_db = -20.0f + 15.0f * sinf(t);
    float right_db = -20.0f + 15.0f * sinf(t + 0.5f);
    dsp_demo_update_ppm(left_db, right_db);

    // Simulate mixer strip changes
    for (int i = 0; i < 3; i++) {
        float value = 0.5f + 0.3f * sinf(t * (i + 1) * 0.3f);
        dsp_demo_update_param(i, value);
    }

    // Simulate spectrum data (frequency bands)
    float spectrum[RTA_NUM_BANDS];
    for (int i = 0; i < RTA_NUM_BANDS; i++) {
        // Create animated spectrum with peaks at different frequencies
        float freq_pos = (float)i / (float)RTA_NUM_BANDS;
        spectrum[i] = 0.3f + 0.5f * sinf(t * 2.0f + freq_pos * 6.28f);
        if (spectrum[i] < 0.0f) spectrum[i] = 0.0f;
        if (spectrum[i] > 1.0f) spectrum[i] = 1.0f;
    }
    dsp_demo_update_spectrum(spectrum);
}

/**
 * Cleanup DSP widgets
 */
void dsp_demo_destroy() {
    if (g_ppm_meter) {
        ppm_meter_destroy(g_ppm_meter);
        g_ppm_meter = nullptr;
    }

    for (int i = 0; i < 3; i++) {
        if (g_mixer_strips[i]) {
            mixer_strip_destroy(g_mixer_strips[i]);
            g_mixer_strips[i] = nullptr;
        }
    }

    if (g_rta_footer) {
        rta_footer_destroy(g_rta_footer);
        g_rta_footer = nullptr;
    }
}

// ============================================================
// INTEGRATION EXAMPLE WITH EXISTING deck_ui.cpp
// ============================================================

/*
// Add to deck_ui.cpp initialization (in Deck_UI_Init function):

void Deck_UI_Init(lv_display_t* disp) {
    gScreen = lv_display_get_screen_active(disp);

    // ... existing code ...

    // Initialize DSP demo widgets
    dsp_demo_init(gScreen);
}

// Add to main loop tick function:

void Deck_UI_Tick() {
    // Call DSP widget tick functions
    dsp_demo_tick();

    // Optional: Generate test data if no OSC connection
    // dsp_demo_generate_test_data();
}

// Add OSC handlers for real-time data:

void OSC_Handle_PPM(float left_db, float right_db) {
    dsp_demo_update_ppm(left_db, right_db);
}

void OSC_Handle_Param(int param_index, float value) {
    dsp_demo_update_param(param_index, value);
}

void OSC_Handle_Spectrum(const float* spectrum_data) {
    dsp_demo_update_spectrum(spectrum_data);
}
*/
