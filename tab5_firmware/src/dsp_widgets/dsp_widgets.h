#pragma once
/**
 * dsp_widgets.h
 * DSP-oriented UI widget library for Tab5 LVGL interface
 *
 * Features 9 music/DSP visualization motifs:
 * 1. PPM Meter - Broadcast-style peak program meter
 * 2. Beat Grid Rail - Beat/phase visualization
 * 3. Harmonic Wheel - Camelot key wheel for DJ mixing
 * 4. Mixer Strip - DAW-style channel strip
 * 5. Sparkline - Tufte-style parameter history
 * 6. ADSR Envelope - Synthesizer envelope visualization
 * 7. Filter Curve - Frequency response preview
 * 8. Tempo Scope - Circular phase meter
 * 9. RTA Footer - 31-band spectrum analyzer
 */

#include <lvgl.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

// ============================================================
// 1. PPM METER (Peak Program Meter)
// ============================================================

typedef struct {
    lv_obj_t* container;        // Base container
    lv_obj_t* bar_left;         // Left channel bar
    lv_obj_t* bar_right;        // Right channel bar
    lv_obj_t* peak_left;        // Peak-hold indicator
    lv_obj_t* peak_right;       // Peak-hold indicator
    lv_obj_t* label_left;       // "L" label
    lv_obj_t* label_right;      // "R" label
    float peak_left_value;      // Peak value (-60 to 0 dB)
    float peak_right_value;     // Peak value (-60 to 0 dB)
    uint32_t peak_left_time;    // Peak hold timestamp
    uint32_t peak_right_time;   // Peak hold timestamp
} ppm_meter_t;

/**
 * Create PPM meter widget
 * @param parent Parent LVGL object
 * @param x X position
 * @param y Y position
 * @param width Total width (includes both channels)
 * @param height Bar height
 * @return Pointer to ppm_meter_t structure
 */
ppm_meter_t* ppm_meter_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height);

/**
 * Update PPM meter values
 * @param meter Meter instance
 * @param left_db Left channel level (-60.0 to 0.0 dB)
 * @param right_db Right channel level (-60.0 to 0.0 dB)
 */
void ppm_meter_update(ppm_meter_t* meter, float left_db, float right_db);

/**
 * Tick function for peak-hold decay (call every frame)
 * @param meter Meter instance
 */
void ppm_meter_tick(ppm_meter_t* meter);

/**
 * Destroy PPM meter and free resources
 * @param meter Meter instance
 */
void ppm_meter_destroy(ppm_meter_t* meter);

// ============================================================
// 2. BEAT GRID RAIL
// ============================================================

#define BEAT_GRID_MAX_BEATS 16

typedef struct {
    lv_obj_t* container;              // Horizontal container
    lv_obj_t* beat_markers[BEAT_GRID_MAX_BEATS]; // Beat position markers
    lv_obj_t* phase_indicator;        // Current position indicator
    lv_obj_t* bar_labels[4];          // Bar number labels
    float phase;                      // Current phase 0.0-1.0
    uint8_t beats_per_bar;            // Typically 4
    uint8_t num_beats;                // Total beats to display
} beat_grid_t;

/**
 * Create beat grid rail widget
 * @param parent Parent LVGL object
 * @param x X position
 * @param y Y position
 * @param width Total width
 * @param height Rail height
 * @param beats_per_bar Beats per bar (typically 4)
 * @param num_beats Total beats to display
 * @return Pointer to beat_grid_t structure
 */
beat_grid_t* beat_grid_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height, uint8_t beats_per_bar, uint8_t num_beats);

/**
 * Update beat grid phase
 * @param grid Grid instance
 * @param phase Current phase 0.0-1.0 (within current bar)
 * @param bar_number Current bar number
 */
void beat_grid_update(beat_grid_t* grid, float phase, int bar_number);

/**
 * Destroy beat grid and free resources
 * @param grid Grid instance
 */
void beat_grid_destroy(beat_grid_t* grid);

// ============================================================
// 3. HARMONIC WHEEL (Camelot)
// ============================================================

#define HARMONIC_WHEEL_SEGMENTS 12

typedef struct {
    lv_obj_t* container;                      // Circular container
    lv_obj_t* arc_segments[HARMONIC_WHEEL_SEGMENTS]; // 12 key segments
    lv_obj_t* key_labels[HARMONIC_WHEEL_SEGMENTS];   // Key name labels
    lv_obj_t* center_label;                   // Current key display
    uint8_t active_key;                       // 0-11 major, 12-23 minor
    void (*on_key_change)(uint8_t key);       // Callback for key changes
} harmonic_wheel_t;

/**
 * Create harmonic wheel widget
 * @param parent Parent LVGL object
 * @param x X position (center)
 * @param y Y position (center)
 * @param diameter Wheel diameter
 * @return Pointer to harmonic_wheel_t structure
 */
harmonic_wheel_t* harmonic_wheel_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t diameter);

/**
 * Set active key
 * @param wheel Wheel instance
 * @param key_index 0-11 for major (C, C#, D...), 12-23 for minor (Cm, C#m...)
 */
void harmonic_wheel_set_key(harmonic_wheel_t* wheel, uint8_t key_index);

/**
 * Destroy harmonic wheel and free resources
 * @param wheel Wheel instance
 */
void harmonic_wheel_destroy(harmonic_wheel_t* wheel);

// ============================================================
// 4. MIXER STRIP
// ============================================================

#define MIXER_STRIP_TICK_MARKS 11

typedef struct {
    lv_obj_t* container;                      // Vertical container
    lv_obj_t* value_label;                    // Current value label
    lv_obj_t* slider_track;                   // Background track
    lv_obj_t* slider_fill;                    // Filled portion
    lv_obj_t* tick_marks[MIXER_STRIP_TICK_MARKS]; // Scale marks
    lv_obj_t* param_label;                    // Parameter name label
    float value;                              // Current value 0.0-1.0
    float target_value;                       // Target for smooth animation
    bool is_touched;                          // True while user is actively touching
    void (*on_value_change)(float value);     // Callback for value changes
} mixer_strip_t;

/**
 * Create mixer strip widget
 * @param parent Parent LVGL object
 * @param x X position
 * @param y Y position
 * @param width Strip width
 * @param height Strip height
 * @param label Parameter name (e.g., "SPEED", "HUE")
 * @return Pointer to mixer_strip_t structure
 */
mixer_strip_t* mixer_strip_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height, const char* label);

/**
 * Update mixer strip value
 * @param strip Strip instance
 * @param value New value 0.0-1.0
 */
void mixer_strip_update(mixer_strip_t* strip, float value);

/**
 * Tick function for smooth animation (call every frame)
 * @param strip Strip instance
 */
void mixer_strip_tick(mixer_strip_t* strip);

/**
 * Destroy mixer strip and free resources
 * @param strip Strip instance
 */
void mixer_strip_destroy(mixer_strip_t* strip);

// ============================================================
// 5. SPARKLINE
// ============================================================

#define SPARKLINE_HISTORY_SIZE 64

typedef struct {
    lv_obj_t* container;                      // Container
    lv_obj_t* canvas;                         // Canvas for custom drawing
    float values[SPARKLINE_HISTORY_SIZE];     // Value ring buffer
    uint8_t write_idx;                        // Ring buffer write index
    float min_value;                          // Auto-scale min
    float max_value;                          // Auto-scale max
} sparkline_t;

/**
 * Create sparkline widget
 * @param parent Parent LVGL object
 * @param x X position
 * @param y Y position
 * @param width Sparkline width
 * @param height Sparkline height
 * @return Pointer to sparkline_t structure
 */
sparkline_t* sparkline_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height);

/**
 * Push new value to sparkline
 * @param sparkline Sparkline instance
 * @param value New value (auto-scales)
 */
void sparkline_push(sparkline_t* sparkline, float value);

/**
 * Destroy sparkline and free resources
 * @param sparkline Sparkline instance
 */
void sparkline_destroy(sparkline_t* sparkline);

// ============================================================
// 6. ADSR ENVELOPE
// ============================================================

typedef enum {
    ADSR_PHASE_OFF = 0,
    ADSR_PHASE_ATTACK,
    ADSR_PHASE_DECAY,
    ADSR_PHASE_SUSTAIN,
    ADSR_PHASE_RELEASE
} adsr_phase_t;

typedef struct {
    lv_obj_t* container;        // Container
    lv_obj_t* canvas;           // Canvas for envelope curve
    lv_obj_t* phase_dot;        // Current position indicator
    float attack_ms;            // Attack time (ms)
    float decay_ms;             // Decay time (ms)
    float sustain_level;        // Sustain level 0.0-1.0
    float release_ms;           // Release time (ms)
    adsr_phase_t current_phase; // Current phase
} adsr_envelope_t;

/**
 * Create ADSR envelope widget
 * @param parent Parent LVGL object
 * @param x X position
 * @param y Y position
 * @param width Envelope width
 * @param height Envelope height
 * @return Pointer to adsr_envelope_t structure
 */
adsr_envelope_t* adsr_envelope_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height);

/**
 * Update ADSR parameters
 * @param envelope Envelope instance
 * @param attack_ms Attack time (ms)
 * @param decay_ms Decay time (ms)
 * @param sustain_level Sustain level 0.0-1.0
 * @param release_ms Release time (ms)
 */
void adsr_envelope_update(adsr_envelope_t* envelope, float attack_ms, float decay_ms, float sustain_level, float release_ms);

/**
 * Set current phase (for visualization)
 * @param envelope Envelope instance
 * @param phase Current phase
 */
void adsr_envelope_set_phase(adsr_envelope_t* envelope, adsr_phase_t phase);

/**
 * Destroy ADSR envelope and free resources
 * @param envelope Envelope instance
 */
void adsr_envelope_destroy(adsr_envelope_t* envelope);

// ============================================================
// 7. FILTER CURVE
// ============================================================

typedef enum {
    FILTER_TYPE_LOWPASS = 0,
    FILTER_TYPE_HIGHPASS,
    FILTER_TYPE_BANDPASS,
    FILTER_TYPE_NOTCH,
    FILTER_TYPE_BELL,
    FILTER_TYPE_LOWSHELF,
    FILTER_TYPE_HIGHSHELF
} filter_type_t;

#define FILTER_CURVE_POINTS 32

typedef struct {
    lv_obj_t* container;        // Container
    lv_obj_t* canvas;           // Canvas for curve
    float frequency;            // Center/cutoff frequency (Hz)
    float resonance;            // Q factor
    float gain_db;              // Gain in dB (for bell/shelf)
    filter_type_t filter_type;  // Filter type
} filter_curve_t;

/**
 * Create filter curve widget
 * @param parent Parent LVGL object
 * @param x X position
 * @param y Y position
 * @param width Curve width
 * @param height Curve height
 * @return Pointer to filter_curve_t structure
 */
filter_curve_t* filter_curve_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height);

/**
 * Update filter parameters
 * @param curve Curve instance
 * @param frequency Center/cutoff frequency (Hz)
 * @param resonance Q factor
 * @param gain_db Gain in dB
 * @param filter_type Filter type
 */
void filter_curve_update(filter_curve_t* curve, float frequency, float resonance, float gain_db, filter_type_t filter_type);

/**
 * Destroy filter curve and free resources
 * @param curve Curve instance
 */
void filter_curve_destroy(filter_curve_t* curve);

// ============================================================
// 8. TEMPO SCOPE
// ============================================================

typedef struct {
    lv_obj_t* container;        // Circular container
    lv_obj_t* arc_bg;           // Background arc
    lv_obj_t* phase_needle;     // Rotating needle
    lv_obj_t* bpm_label;        // BPM display
    lv_obj_t* beat_markers[4];  // Quarter note markers
    float phase;                // 0.0-1.0 phase
    float bpm;                  // Current BPM
} tempo_scope_t;

/**
 * Create tempo scope widget
 * @param parent Parent LVGL object
 * @param x X position (center)
 * @param y Y position (center)
 * @param diameter Scope diameter
 * @return Pointer to tempo_scope_t structure
 */
tempo_scope_t* tempo_scope_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t diameter);

/**
 * Update tempo scope
 * @param scope Scope instance
 * @param bpm Current BPM
 * @param phase Current phase 0.0-1.0
 */
void tempo_scope_update(tempo_scope_t* scope, float bpm, float phase);

/**
 * Destroy tempo scope and free resources
 * @param scope Scope instance
 */
void tempo_scope_destroy(tempo_scope_t* scope);

// ============================================================
// 9. RTA FOOTER (Real-Time Analyzer)
// ============================================================

#define RTA_NUM_BANDS 31

typedef struct {
    lv_obj_t* container;              // Horizontal container
    lv_obj_t* bars[RTA_NUM_BANDS];    // Frequency bars
    lv_obj_t* peak_dots[RTA_NUM_BANDS]; // Peak indicators
    float values[RTA_NUM_BANDS];      // Current values (0.0-1.0)
    float peaks[RTA_NUM_BANDS];       // Peak values
    uint32_t peak_times[RTA_NUM_BANDS]; // Peak timestamps
} rta_footer_t;

/**
 * Create RTA footer widget
 * @param parent Parent LVGL object
 * @param x X position
 * @param y Y position
 * @param width Total width
 * @param height Footer height (typically 40px)
 * @return Pointer to rta_footer_t structure
 */
rta_footer_t* rta_footer_create(lv_obj_t* parent, lv_coord_t x, lv_coord_t y, lv_coord_t width, lv_coord_t height);

/**
 * Update RTA spectrum data
 * @param rta RTA instance
 * @param values Array of 31 float values (0.0-1.0 normalized)
 */
void rta_footer_update(rta_footer_t* rta, const float* values);

/**
 * Tick function for peak-hold decay (call every frame)
 * @param rta RTA instance
 */
void rta_footer_tick(rta_footer_t* rta);

/**
 * Destroy RTA footer and free resources
 * @param rta RTA instance
 */
void rta_footer_destroy(rta_footer_t* rta);

#ifdef __cplusplus
}
#endif
