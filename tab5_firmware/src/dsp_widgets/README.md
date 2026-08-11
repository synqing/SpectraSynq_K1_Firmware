# DSP Widgets for Tab5

## Overview

This directory contains 9 DSP-oriented UI widgets for the Tab5 LVGL interface, designed for music/audio applications with real-time visualization needs.

## Implemented Widgets (Phase 1)

### 1. PPM Meter (`ppm_meter.cpp`)
Broadcast-style peak program meter with stereo L/R channels.

**Features:**
- 3-zone color coding: Green (-60 to -12 dB), Yellow (-12 to -3 dB), Red (-3 to 0 dB)
- Peak-hold indicators with 1.5s decay
- 30Hz update rate recommended

**Usage:**
```c
ppm_meter_t* meter = ppm_meter_create(screen, 1000, 20, 260, 150);
ppm_meter_update(meter, -15.0f, -12.0f);  // left_db, right_db
ppm_meter_tick(meter);  // Call every frame for peak decay
```

### 2. Mixer Strip (`mixer_strip.cpp`)
DAW-style vertical channel strip with touch interaction.

**Features:**
- Touch-drag value control
- Tick marks at 10% intervals
- Smooth value transitions
- Callback support for value changes

**Usage:**
```c
mixer_strip_t* strip = mixer_strip_create(screen, 20, 200, 100, 400, "SPEED");
mixer_strip_update(strip, 0.75f);  // Set value 0.0-1.0
mixer_strip_tick(strip);  // Call every frame for smooth animation
```

### 3. RTA Footer (`rta_footer.cpp`)
31-band real-time spectrum analyzer.

**Features:**
- ISO 1/3 octave bands
- Color gradient by frequency (blue→green→yellow→red)
- Peak-hold indicators with 1s decay
- 40px footer design

**Usage:**
```c
rta_footer_t* rta = rta_footer_create(screen, 0, 680, 1280, 40);
float spectrum[31] = { /* 31 normalized values */ };
rta_footer_update(rta, spectrum);
rta_footer_tick(rta);  // Call every frame for peak decay
```

## Planned Widgets (Phase 2 & 3)

### Phase 2 (Beat/Tempo)
- **Beat Grid Rail**: Beat/phase visualization synced to BPM
- **Tempo Scope**: Circular phase meter (Pioneer CDJ style)
- **Sparkline**: Tufte-style parameter history

### Phase 3 (Advanced)
- **Harmonic Wheel**: Camelot key wheel for DJ mixing
- **ADSR Envelope**: Synthesizer envelope visualization
- **Filter Curve**: Frequency response preview

## Integration Example

See `dsp_demo.cpp` for complete integration example.

### Quick Start

```c
// 1. Include header
#include "dsp_widgets/dsp_widgets.h"

// 2. Initialize widgets after LVGL setup
void Deck_UI_Init(lv_display_t* disp) {
    lv_obj_t* screen = lv_display_get_screen_active(disp);

    // Create widgets
    ppm_meter_t* ppm = ppm_meter_create(screen, 1000, 20, 260, 150);
    mixer_strip_t* speed = mixer_strip_create(screen, 20, 200, 100, 400, "SPEED");
    rta_footer_t* rta = rta_footer_create(screen, 0, 680, 1280, 40);
}

// 3. Update from transport data
void MIDI_Handle_PPM(float left_db, float right_db) {
    ppm_meter_update(g_ppm_meter, left_db, right_db);
}

// 4. Call tick functions in main loop
void Deck_UI_Tick() {
    ppm_meter_tick(g_ppm_meter);
    mixer_strip_tick(g_speed_strip);
    rta_footer_tick(g_rta_footer);
}
```

## OSC Protocol

### Incoming Messages

```
/deck/ppm <float:left_db> <float:right_db>
    Update PPM meter levels (-60.0 to 0.0 dB)
    Rate: 30 Hz

/deck/param <int:id> <float:value>
    Update mixer strip parameter (0.0 to 1.0)
    Rate: 20 Hz

/deck/spectrum <blob:31_floats>
    Update RTA spectrum data (31 normalized values)
    Rate: 15 Hz
```

## Memory Budget

- PPM Meter: ~512 bytes
- Mixer Strip: ~512 bytes
- RTA Footer: ~1.5 KB

Total for Phase 1: ~2.5 KB (well within 200KB LVGL heap)

## Build Configuration

Ensure these LVGL widgets are enabled in `lv_conf.h`:

```c
#define LV_USE_BAR 1      // For PPM, Mixer, RTA
#define LV_USE_ARC 1      // For Harmonic Wheel, Tempo Scope
#define LV_USE_CHART 1    // For ADSR, Filter curves
#define LV_USE_METER 1    // For Tempo Scope
#define LV_USE_CANVAS 1   // For Sparkline, custom drawing
```

## Testing

Use `dsp_demo_generate_test_data()` to see animated widgets without OSC:

```c
void setup() {
    // ... LVGL init ...
    dsp_demo_init(screen);
}

void loop() {
    dsp_demo_generate_test_data();  // Animated test data
    dsp_demo_tick();                // Widget updates
    lv_task_handler();              // LVGL tasks
    delay(16);                      // ~60 FPS
}
```

## Next Steps

1. Test build with Phase 1 widgets
2. Integrate with existing `deck_ui.cpp`
3. Add OSC handlers for real-time data
4. Implement Phase 2 widgets (Beat Grid, Tempo Scope, Sparkline)
5. Performance profiling at 60 FPS
6. Implement Phase 3 widgets (Harmonic Wheel, ADSR, Filter Curve)
