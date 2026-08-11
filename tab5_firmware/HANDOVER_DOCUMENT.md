# K1 Tab5 Deck UI - Comprehensive Handover Document

**Date:** October 16, 2025
**Session:** Footer Fix, Touch Implementation, and Boot Logging Reduction
**Device:** M5Stack Tab5 (ESP32-P4) at `/dev/cu.usbmodem21401` / `/dev/tty.usbmodem21401`

---

## Executive Summary

This session focused on fixing critical UI layout issues and implementing touch functionality for the K1-Lightwave Tab5 Deck UI. The primary deliverables were:

1. **Footer dimension correction** - Matched header height exactly (88px)
2. **Latency metrics relocation** - Moved from header to footer
3. **IP display enhancement** - Added port number display
4. **Touch event handlers** - Implemented working touch callbacks for all control buttons
5. **Boot logging reduction** - Disabled verbose ESP-IDF boot messages

All changes have been successfully built and are ready for upload to the device.

---

## 1. System Architecture Overview

### 1.1 Hardware Platform
- **Device:** M5Stack Tab5 (ESP32-P4 RISC-V dual-core)
- **Display:** 1280×720px landscape touchscreen
- **Framework:** Arduino + ESP-IDF
- **GUI:** LVGL 9.3.0
- **Serial Port:** `/dev/cu.usbmodem21401` (upload) / `/dev/tty.usbmodem21401` (monitor)

### 1.2 Project Structure
```
T-Keyboard-S3-Pro/K1.tab5/pio/deck/
├── platformio.ini              # Build configuration
├── include/
│   ├── deck_ui.h              # Main UI header (MODIFIED)
│   └── tab5_config.sample.h   # Configuration template
├── src/
│   ├── main.cpp               # Entry point (MODIFIED - 2 call sites)
│   ├── deck_ui.cpp            # Main UI implementation (COMPLETELY REWRITTEN)
│   ├── dsp_widgets/           # Audio visualization widgets
│   │   ├── mixer_strip.cpp    # 100px wide vertical sliders
│   │   ├── ppm_meter.cpp      # Peak meter display
│   │   └── rta_footer.cpp     # RTA spectrum display
│   └── fonts/                 # Bebas Neue font family
└── .pio/build/tab5_p4/        # Build artifacts
    └── firmware.bin           # Ready to upload
```

---

## 2. Implemented Changes - Detailed Breakdown

### 2.1 Footer Dimension Fix

**Problem:** Footer was 40px height instead of matching the 88px header height.

**Solution:**
- Changed `TAB5_FOOTER_HEIGHT` from `40` to `88` in `deck_ui.cpp:53`
- Updated footer Y position calculation: `const int footer_y = TAB5_SCREEN_HEIGHT - TAB5_FOOTER_HEIGHT - TAB5_GRID_MARGIN;` (720 - 88 - 24 = 608)
- Applied exact same styling as header:
  - 3px white border
  - 14px radius
  - Elevated surface color (`TAB5_COLOR_BG_SURFACE_ELEVATED`)

**File:** `src/deck_ui.cpp:267-307`

**Code:**
```cpp
#define TAB5_FOOTER_HEIGHT      88  // MUST match header height EXACTLY

static void create_footer(lv_obj_t* parent) {
  const int footer_y = TAB5_SCREEN_HEIGHT - TAB5_FOOTER_HEIGHT - TAB5_GRID_MARGIN;  // 720 - 88 - 24 = 608

  // Footer bar - EXACTLY matching header style
  gFooter = lv_obj_create(parent);
  lv_obj_set_size(gFooter, LV_PCT(100), TAB5_FOOTER_HEIGHT);
  lv_obj_set_pos(gFooter, 0, footer_y);
  lv_obj_set_style_bg_color(gFooter, lv_color_hex(TAB5_COLOR_BG_SURFACE_ELEVATED), LV_PART_MAIN);
  lv_obj_set_style_border_width(gFooter, 3, LV_PART_MAIN);
  lv_obj_set_style_border_color(gFooter, lv_color_hex(0xFFFFFF), LV_PART_MAIN);
  lv_obj_set_style_radius(gFooter, 14, LV_PART_MAIN);
  lv_obj_clear_flag(gFooter, LV_OBJ_FLAG_SCROLLABLE);

  // ... footer content ...
}
```

---

### 2.2 Latency Metrics Relocation

**Problem:** Latency metrics (latency and delta time) were displayed in the header, cluttering the status bar.

**Solution:**
- Removed `gStatusLatency` and `gStatusDeltaTime` label creation from `create_status_bar()`
- Added these labels to `create_footer()` on the left side
- Updated `Deck_UI_UpdateNetworkStatus()` to update footer labels instead of header labels

**Header Changes (src/deck_ui.cpp:103-127):**
```cpp
static void create_status_bar(lv_obj_t* parent) {
  // ... header creation ...

  // IP with PORT (left)
  gStatusIP = lv_label_create(gStatusBar);
  lv_label_set_text(gStatusIP, "IP: ---:----");
  lv_obj_set_style_text_font(gStatusIP, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gStatusIP, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_align(gStatusIP, LV_ALIGN_LEFT_MID, 30, 0);

  // K1-LIGHTWAVE (center)
  lv_obj_t* title = lv_label_create(gStatusBar);
  lv_label_set_text(title, "K1-LIGHTWAVE");
  lv_obj_set_style_text_font(title, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(title, lv_color_hex(TAB5_COLOR_FG_PRIMARY), LV_PART_MAIN);
  lv_obj_align(title, LV_ALIGN_CENTER, 0, 0);

  // HOST (right)
  gStatusHost = lv_label_create(gStatusBar);
  lv_label_set_text(gStatusHost, "HOST: Disconnected");
  lv_obj_set_style_text_font(gStatusHost, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gStatusHost, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_align(gStatusHost, LV_ALIGN_RIGHT_MID, -30, 0);
}
```

**Footer Changes (src/deck_ui.cpp:280-292):**
```cpp
  // Latency (left) - MOVED FROM HEADER
  gStatusLatency = lv_label_create(gFooter);
  lv_label_set_text(gStatusLatency, "---ms");
  lv_obj_set_style_text_font(gStatusLatency, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gStatusLatency, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_align(gStatusLatency, LV_ALIGN_LEFT_MID, 30, 0);

  // Delta time (left-center) - MOVED FROM HEADER
  gStatusDeltaTime = lv_label_create(gFooter);
  lv_label_set_text(gStatusDeltaTime, "Δt: ---ms");
  lv_obj_set_style_text_font(gStatusDeltaTime, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gStatusDeltaTime, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_set_pos(gStatusDeltaTime, 150, 32);
```

**Footer Layout:**
```
┌──────────────────────────────────────────────────────────────┐
│ [---ms]  [Δt: ---ms]    UPTIME: 0h 0m           FPS: --     │  88px height
└──────────────────────────────────────────────────────────────┘
```

---

### 2.3 IP Display with Port Number

**Problem:** IP display only showed IP address without port information.

**Solution:**
- Modified header IP label initial text from `"IP: ---"` to `"IP: ---:----"`
- Updated `Deck_UI_UpdateNetworkStatus()` function signature to accept `int port` parameter
- Changed IP display format to `"IP: %s:%d"` (e.g., "IP:192.168.1.100:9010")

**Function Signature Change (include/deck_ui.h:27):**
```cpp
// OLD:
void Deck_UI_UpdateNetworkStatus(const char* ip, bool hostConnected, int latencyMs, int deltaTimeMs);

// NEW:
void Deck_UI_UpdateNetworkStatus(const char* ip, int port, bool hostConnected, int latencyMs, int deltaTimeMs);
```

**Implementation (src/deck_ui.cpp:360-391):**
```cpp
void Deck_UI_UpdateNetworkStatus(const char* ip, int port, bool hostConnected, int latencyMs, int deltaTimeMs) {
  char buf[64];

  // Update IP with PORT
  if (ip) {
    snprintf(buf, sizeof(buf), "IP: %s:%d", ip, port);
    lv_label_set_text(gStatusIP, buf);
  }

  lv_label_set_text(gStatusHost, hostConnected ? "HOST: Connected" : "HOST: Disconnected");
  lv_obj_set_style_text_color(gStatusHost,
    hostConnected ? lv_color_hex(TAB5_COLOR_BRAND_PRIMARY) : lv_color_hex(TAB5_COLOR_FG_SECONDARY),
    LV_PART_MAIN);

  // Update FOOTER latencies (not header)
  if (gStatusLatency) {
    if (hostConnected && latencyMs >= 0) {
      snprintf(buf, sizeof(buf), "%dms", latencyMs);
      lv_label_set_text(gStatusLatency, buf);
    } else {
      lv_label_set_text(gStatusLatency, "---ms");
    }
  }

  if (gStatusDeltaTime) {
    if (hostConnected && deltaTimeMs >= 0) {
      snprintf(buf, sizeof(buf), "Δt: %dms", deltaTimeMs);
      lv_label_set_text(gStatusDeltaTime, buf);
    } else {
      lv_label_set_text(gStatusDeltaTime, "Δt: ---ms");
    }
  }
}
```

**Call Site Updates (src/main.cpp:563 and 565):**
```cpp
// Call site 1 (WiFi available):
String ip = WiFi.localIP().toString();
int latency = gHostAlive ? (int)(now - gLastHostSeenMs) : -1;
Deck_UI_UpdateNetworkStatus(ip.c_str(), TAB5_DECK_RX_PORT, gHostAlive, latency, gHostDeltaTimeMs);

// Call site 2 (WiFi unavailable):
Deck_UI_UpdateNetworkStatus("0.0.0.0", 0, gHostAlive, -1, -1);
```

**Port Configuration (include/tab5_config.sample.h:24-25):**
```cpp
#define TAB5_HOST_OSC_PORT    9000             // Host port where deck sends commands
#define TAB5_DECK_RX_PORT     9010             // Local UDP port the deck listens on
```

**Display Example:** `IP:192.168.1.100:9010`

---

### 2.4 Touch Event Handlers Implementation

**Problem:** UI had clickable buttons but no event callbacks registered, resulting in no touch functionality.

**Solution:**
- Added LOG macro definition to deck_ui.cpp for debugging output
- Implemented three touch event callback functions
- Registered callbacks with LVGL for LV_EVENT_CLICKED
- Added working local state change for direction toggle

**LOG Macro Addition (src/deck_ui.cpp:7-9):**
```cpp
// Simple logging helper (matches main.cpp LOG behavior)
#include <Arduino.h>
#define LOG(fmt, ...) Serial.printf("[deck_ui] " fmt "\n", ##__VA_ARGS__)
```

**Event Handler Declarations (src/deck_ui.cpp:309-327):**
```cpp
// Touch event handlers
static void effect_btn_event_cb(lv_event_t* e) {
  // TODO: Implement effect cycling (send OSC to host)
  LOG("[touch] EFFECT button clicked");
}

static void palette_btn_event_cb(lv_event_t* e) {
  // TODO: Implement palette cycling (send OSC to host)
  LOG("[touch] PALETTE button clicked");
}

static void direction_toggle_event_cb(lv_event_t* e) {
  // TODO: Toggle direction INWARD/OUTWARD (send OSC to host)
  LOG("[touch] DIRECTION toggle clicked");
  const char* current = lv_label_get_text(gDirectionLabel);
  if (strcmp(current, "[ INWARD ]") == 0) {
    lv_label_set_text(gDirectionLabel, "[ OUTWARD ]");
  } else {
    lv_label_set_text(gDirectionLabel, "[ INWARD ]");
  }
}
```

**Event Registration (src/deck_ui.cpp:177-179):**
```cpp
// In create_control_zone() after button creation:
lv_obj_add_event_cb(gEffectBtn, effect_btn_event_cb, LV_EVENT_CLICKED, nullptr);
lv_obj_add_event_cb(gPaletteBtn, palette_btn_event_cb, LV_EVENT_CLICKED, nullptr);
lv_obj_add_event_cb(gDirectionToggle, direction_toggle_event_cb, LV_EVENT_CLICKED, nullptr);
```

**Touch Functionality Status:**
- ✅ EFFECT button - Logs click event
- ✅ PALETTE button - Logs click event
- ✅ DIRECTION toggle - Logs click AND toggles label text locally
- ⚠️ OSC message sending - TODO (requires host communication implementation)
- ⚠️ Sliders - Have LVGL touch built-in but may need OSC integration

**Expected Serial Output:**
```
[deck_ui] [touch] EFFECT button clicked
[deck_ui] [touch] PALETTE button clicked
[deck_ui] [touch] DIRECTION toggle clicked
```

---

### 2.5 Boot Logging Reduction

**Problem:** ESP-IDF bootloader and PSRAM initialization printed excessive debug messages (e.g., "sdio_mempool_create free:32035968...") that stalled serial output during boot.

**Solution:**
Added three compiler flags to `platformio.ini` to suppress verbose boot messages:

**Changes (platformio.ini:46-48):**
```ini
[env:tab5_p4]
platform      = espressif32
board         = esp32-p4-evboard
framework     = ${common.framework}
monitor_speed = ${common.monitor_speed}
build_flags   =
    ${common.build_flags}
    -D CORE_P4=1
    -D LV_USE_DRAW_SW_ASM=0
    -D CONFIG_BOOTLOADER_LOG_LEVEL=0      # NEW - Disable bootloader verbose output
    -D CONFIG_LOG_DEFAULT_LEVEL=2         # NEW - Set default log level to WARN
    -D CORE_DEBUG_LEVEL=2                 # NEW - Set Arduino core debug to WARN
```

**Flag Meanings:**
- `CONFIG_BOOTLOADER_LOG_LEVEL=0` - Disables all bootloader logging (ESP-IDF bootloader stage)
- `CONFIG_LOG_DEFAULT_LEVEL=2` - Sets ESP-IDF log level to WARN (0=NONE, 1=ERROR, 2=WARN, 3=INFO, 4=DEBUG, 5=VERBOSE)
- `CORE_DEBUG_LEVEL=2` - Sets Arduino core debug level to WARN

**Expected Boot Output (Before Fix):**
```
ESP-ROM:esp32p4-eco2-20240710
Build:Jul 10 2024
rst:0x7 (HP_SYS_HP_WDT_RESET),boot:0x20c (SPI_FAST_FLASH_BOOT)
SPI mode:DIO, clock div:1
load:0x4ff33ce0,len:0x118c
load:0x4ff2abd0,len:0xcd0
load:0x4ff2cbd0,len:0x3304
entry 0x4ff2abd0
sdio_mempool_create free:32035968 min-free:32035968 lfb-def:31457268 lfb-8bit:31457268
[STALLS HERE]
```

**Expected Boot Output (After Fix):**
```
ESP-ROM:esp32p4-eco2-20240710
Build:Jul 10 2024
[Your application starts immediately]
```

---

## 3. Control Layout Reference

### 3.1 Screen Layout (1280×720px)
```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER (88px)                                                                          │
│ IP:192.168.1.100:9010        K1-LIGHTWAVE                    HOST: Connected          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│ ┌─────────────────────── CONTROL ZONE (896px) ─────────────────────┐ STATUS (384px)  │
│ │                                                                   │                  │
│ │  [SLIDER] [SLIDER] [SLIDER] [SLIDER]   [ EFFECT  ]              │  Status boxes    │
│ │  [  1  ]  [  2  ]  [  3  ]  [  4  ]    [ PALETTE ]              │  with metrics    │
│ │  100px    100px    100px    100px      [DIRECTION]              │                  │
│ │                                        180×120px                 │                  │
│ │                                                                   │                  │
│ └───────────────────────────────────────────────────────────────────┘                  │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ FOOTER (88px)                                                                          │
│ [23ms]  [Δt: 5ms]              UPTIME: 2h 34m                           FPS: 60       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Control Zone Details

**Vertical Sliders (4x):**
- Width: 100px (original DSP widget dimension)
- Height: 400px
- Spacing: Calculated gaps for even distribution
- Touch: LVGL built-in drag functionality
- Labels: "1", "2", "3", "4"

**Toggle Buttons (3x):**
- Position: Right side of sliders, stacked vertically
- Size: 180px × 120px (uniform)
- Spacing: 30px vertical gap
- Buttons:
  1. EFFECT - Cycles through visual effects
  2. PALETTE - Cycles through color palettes
  3. DIRECTION - Toggles "[ INWARD ]" / "[ OUTWARD ]"

**Layout Calculation (src/deck_ui.cpp:136-152):**
```cpp
#define SLIDER_WIDTH  100
#define SLIDER_HEIGHT 400
#define TOGGLE_WIDTH  180
#define TOGGLE_HEIGHT 120

const int control_width = TAB5_CONTROL_ZONE_WIDTH - 2 * TAB5_GRID_MARGIN;  // 896 - 48 = 848
const int slider_section_width = 4 * SLIDER_WIDTH + 100;  // 500px for sliders + gaps
const int slider_gap = (slider_section_width - 4 * SLIDER_WIDTH) / 5;  // Even spacing
const int toggles_x = start_x + slider_section_width + 60;  // 60px gap from sliders
const int toggle_gap = 30;  // 30px vertical gap between toggles
```

---

## 4. File Modifications Summary

### 4.1 Modified Files

| File | Lines Changed | Description |
|------|---------------|-------------|
| `platformio.ini` | 3 added | Added boot logging reduction flags |
| `include/deck_ui.h` | 1 modified | Updated function signature with port param |
| `src/main.cpp` | 2 modified | Updated call sites to pass port |
| `src/deck_ui.cpp` | COMPLETE REWRITE | New footer, touch handlers, LOG macro |

### 4.2 Deleted Files

| File | Reason |
|------|--------|
| `src/deck_ui_BROKEN.cpp` | Backup file causing linker conflicts (multiple definitions) |

### 4.3 Build Artifacts

| File | Size | Status |
|------|------|--------|
| `.pio/build/tab5_p4/firmware.bin` | 1.1 MB | ✅ Ready to upload |
| `.pio/build/tab5_p4/firmware.elf` | 21 MB | ✅ Built successfully |
| `.pio/build/tab5_p4/firmware.map` | 11 MB | ✅ Generated |

**Build Stats:**
- RAM Usage: 2.9% (14,892 bytes / 512,000 bytes)
- Flash Usage: 86.9% (1,139,041 bytes / 1,310,720 bytes)
- Build Time: ~20 seconds (clean build)

---

## 5. Testing & Validation

### 5.1 Build Verification
```bash
cd K1.tab5/pio/deck
export PATH="$HOME/.platformio/packages/toolchain-riscv32-esp@src-f96751ec4e9b59062ea536896ff4f77e/bin:$PATH"
platformio run
```

**Expected Output:**
```
Processing tab5_p4 (platform: espressif32; board: esp32-p4-evboard; framework: arduino)
...
Linking .pio/build/tab5_p4/firmware.elf
Successfully created ESP32P4 image.
========================= [SUCCESS] Took 20.06 seconds =========================
```

### 5.2 Upload Procedure

**IMPORTANT:** Close all serial monitors before uploading to prevent "Resource busy" errors.

```bash
cd K1.tab5/pio/deck
export PATH="$HOME/.platformio/packages/toolchain-riscv32-esp@src-f96751ec4e9b59062ea536896ff4f77e/bin:$PATH"
platformio run --target upload --upload-port /dev/cu.usbmodem21401
```

**Expected Upload Output:**
```
Looking for upload port...
Uploading .pio/build/tab5_p4/firmware.bin
esptool.py v5.0.0-dev1
Serial port /dev/cu.usbmodem21401:
Connecting...
Connected to ESP32-P4 on /dev/cu.usbmodem21401:
...
Wrote 1179584 bytes (643872 compressed) at 0x00010000 in 4.8 seconds
Hard resetting via RTS pin...
========================= [SUCCESS] Took 11.81 seconds =========================
```

### 5.3 Visual Testing Checklist

After upload, verify on device:

**Header:**
- [ ] IP displays with port (format: `IP:192.168.1.100:9010`)
- [ ] Title shows "K1-LIGHTWAVE" centered
- [ ] Host status shows "HOST: Connected" or "HOST: Disconnected"
- [ ] NO latency metrics in header

**Footer:**
- [ ] Footer height matches header height (88px)
- [ ] Footer has same styling as header (3px white border, 14px radius)
- [ ] Latency shows on left: "23ms" or "---ms"
- [ ] Delta time shows left-center: "Δt: 5ms" or "Δt: ---ms"
- [ ] Uptime shows center-right: "UPTIME: 2h 34m"
- [ ] FPS shows on right: "FPS: 60"

**Control Zone:**
- [ ] 4 vertical sliders are 100px wide (not 180px)
- [ ] Sliders respond to touch/drag
- [ ] 3 toggle buttons on right side, vertically stacked
- [ ] All toggles are same size (180×120px)
- [ ] EFFECT button logs "[touch] EFFECT button clicked" when pressed
- [ ] PALETTE button logs "[touch] PALETTE button clicked" when pressed
- [ ] DIRECTION button logs "[touch] DIRECTION toggle clicked" and changes text

**Boot Behavior:**
- [ ] Boot completes without stalling at "sdio_mempool_create"
- [ ] Minimal boot messages displayed
- [ ] UI appears quickly after reset

### 5.4 Serial Monitor Testing

```bash
platformio device monitor --port /dev/tty.usbmodem21401 --baud 115200
```

**Expected Touch Output:**
```
[deck_ui] [touch] EFFECT button clicked
[deck_ui] [touch] PALETTE button clicked
[deck_ui] [touch] DIRECTION toggle clicked
```

---

## 6. Known Issues & TODOs

### 6.1 Immediate TODOs

**Touch OSC Integration:**
- [ ] Implement OSC message sending in `effect_btn_event_cb()`
- [ ] Implement OSC message sending in `palette_btn_event_cb()`
- [ ] Implement OSC message sending in `direction_toggle_event_cb()`
- [ ] Add slider value change callbacks with OSC transmission
- [ ] Define OSC address patterns (e.g., `/k1/effect`, `/k1/palette`, `/k1/direction`)

**Network Integration:**
- [ ] Verify IP display updates correctly when WiFi connects
- [ ] Test port display with TAB5_DECK_RX_PORT value
- [ ] Verify latency metrics update in footer (not header)

**UI Polish:**
- [ ] Add visual feedback for button presses (color change, animation)
- [ ] Implement effect/palette cycling state management
- [ ] Add visual indicator for current effect/palette selection

### 6.2 Known Limitations

**Boot Logging:**
- ESP-ROM messages still appear (cannot be disabled)
- ROM messages: "ESP-ROM:esp32p4-eco2-20240710", "Build:Jul 10 2024", etc.
- Only post-ROM bootloader and application logging is reduced

**Touch Functionality:**
- Touch handlers log events but don't send OSC messages yet
- Direction toggle changes label but doesn't communicate to host
- No visual feedback when buttons are pressed

**Serial Port Conflict:**
- Cannot upload while serial monitor is open
- Must close monitor before running `platformio run --target upload`

---

## 7. Configuration Reference

### 7.1 Critical Constants

**Display Dimensions (src/deck_ui.cpp:20-31):**
```cpp
#define TAB5_SCREEN_WIDTH       1280
#define TAB5_SCREEN_HEIGHT      720
#define TAB5_STATUSBAR_HEIGHT   88      // Header height
#define TAB5_FOOTER_HEIGHT      88      // Footer height (MUST MATCH HEADER)
#define TAB5_GRID_MARGIN        24      // Screen edge padding
#define TAB5_CONTROL_ZONE_WIDTH 896     // 70% of screen
#define TAB5_STATUS_ZONE_WIDTH  384     // 30% of screen
```

**Widget Dimensions (src/deck_ui.cpp:33-38):**
```cpp
#define SLIDER_WIDTH            100     // Original DSP widget width
#define SLIDER_HEIGHT           400
#define TOGGLE_WIDTH            180
#define TOGGLE_HEIGHT           120
```

**Network Configuration (include/tab5_config.sample.h:22-25):**
```cpp
#define TAB5_HOST_IP            "192.168.1.42"   // Host (K1.juce) IP
#define TAB5_HOST_OSC_PORT      9000             // Port where deck sends OSC
#define TAB5_DECK_RX_PORT       9010             // Local UDP port deck listens on
```

**Colors (src/deck_ui.cpp:16-30):**
```cpp
#define TAB5_COLOR_BG_PAGE              0x0A0A0B
#define TAB5_COLOR_BG_SURFACE_BASE      0x121214
#define TAB5_COLOR_BG_SURFACE_ELEVATED  0x1A1A1D
#define TAB5_COLOR_BRAND_PRIMARY        0xF4B400    // Yellow accent
#define TAB5_COLOR_FG_PRIMARY           0xFFFFFF    // White text
#define TAB5_COLOR_FG_SECONDARY         0x9E9E9E    // Gray text
```

### 7.2 Font Family

**Bebas Neue (include/fonts/bebas_neue_fonts.h):**
- `bebas_neue_24px` - Status bar text, footer metrics
- `bebas_neue_32px` - Status zone values
- `bebas_neue_40px` - (Available)
- `bebas_neue_48px` - (Available)
- `bebas_neue_56px` - Large display text
- `bebas_neue_64px` - (Available)
- `bebas_neue_72px` - (Available)

---

## 8. Git Status & Version Control

### 8.1 Current Branch
```bash
feature/tab5-ui-grid-refinement
```

### 8.2 Modified Files (Uncommitted)
```
M  K1.tab5/pio/deck/platformio.ini
M  K1.tab5/pio/deck/include/deck_ui.h
M  K1.tab5/pio/deck/src/main.cpp
M  K1.tab5/pio/deck/src/deck_ui.cpp
D  K1.tab5/pio/deck/src/deck_ui_BROKEN.cpp
```

### 8.3 Suggested Commit Message
```
feat(tab5): fix footer layout and implement touch handlers

- Fixed footer height to match header (88px)
- Moved latency metrics from header to footer
- Added port number to IP display (IP:192.168.1.100:9010)
- Implemented touch event handlers for EFFECT, PALETTE, DIRECTION buttons
- Added LOG macro for touch event debugging
- Reduced boot logging verbosity (CONFIG_BOOTLOADER_LOG_LEVEL=0)
- Fixed slider width to original 100px (was incorrectly 180px)
- Removed backup file deck_ui_BROKEN.cpp causing linker conflicts

Modified files:
- platformio.ini: Added boot logging reduction flags
- include/deck_ui.h: Updated Deck_UI_UpdateNetworkStatus signature
- src/main.cpp: Updated call sites to pass port parameter
- src/deck_ui.cpp: Complete rewrite with all fixes

Touch functionality now logs events to serial. OSC integration pending.

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 9. Development Environment

### 9.1 Toolchain
- **PlatformIO:** Framework for ESP32-P4
- **Compiler:** riscv32-esp-elf-g++ 14.2.0
- **Platform:** espressif32 (54.3.21+sha.df45e99)
- **Framework:** arduino @ 3.2.1
- **Board Definition:** esp32-p4-evboard

### 9.2 Build Path
```bash
export PATH="$HOME/.platformio/packages/toolchain-riscv32-esp@src-f96751ec4e9b59062ea536896ff4f77e/bin:$PATH"
```

### 9.3 Dependencies
```ini
lib_deps =
    m5stack/M5Unified@^0.2.0
    m5stack/M5GFX@^0.2.0
    lvgl/lvgl@^9.2.0
    # OSC library vendored in lib/CNMAT_OSC directory
```

---

## 10. Troubleshooting

### 10.1 Upload Fails with "Resource busy"

**Problem:**
```
A fatal error occurred: Could not open /dev/cu.usbmodem21401, the port is busy
```

**Solution:**
1. Close all serial monitors (PlatformIO, screen, minicom, etc.)
2. Kill any process using the port: `lsof | grep usbmodem21401`
3. Try upload again

### 10.2 Build Fails with "multiple definition" Errors

**Problem:**
```
multiple definition of `Deck_UI_Init(_lv_display_t*)'
```

**Solution:**
- Delete `src/deck_ui_BROKEN.cpp` if it exists
- Run `platformio run --target clean`
- Rebuild: `platformio run`

### 10.3 Touch Events Not Logging

**Problem:** Touch buttons don't produce serial output

**Solution:**
1. Verify LOG macro is defined in deck_ui.cpp
2. Check serial monitor is open at correct baud (115200)
3. Ensure firmware was actually uploaded (check upload success message)
4. Verify buttons are actually being pressed (visual feedback may be missing)

### 10.4 Footer Still Wrong Size

**Problem:** Footer doesn't match header height

**Solution:**
1. Verify `TAB5_FOOTER_HEIGHT` is set to `88` in deck_ui.cpp
2. Check you're editing the correct file (not a backup)
3. Ensure clean build: `platformio run --target clean && platformio run`
4. Verify firmware upload completed successfully

### 10.5 IP Shows Without Port

**Problem:** IP displays as "IP:192.168.1.100" instead of "IP:192.168.1.100:9010"

**Solution:**
1. Verify deck_ui.h has updated function signature with `int port` parameter
2. Check both call sites in main.cpp pass port parameter
3. Verify TAB5_DECK_RX_PORT is defined in tab5_config.h (or tab5_config.sample.h)
4. Clean build and upload

---

## 11. Next Steps & Roadmap

### 11.1 Immediate Next Session
1. **Test firmware on device** - Close serial monitors and upload
2. **Verify visual layout** - Check footer matches header, sliders correct width
3. **Test touch functionality** - Press buttons and verify serial output
4. **Verify boot behavior** - Ensure no stalling at boot messages

### 11.2 Short-Term (Next 1-2 Sessions)
1. **OSC Integration:**
   - Implement OSC message sending in touch event handlers
   - Add slider value change callbacks
   - Test bidirectional communication with K1-Lightwave host

2. **Visual Feedback:**
   - Add button press animations (scale, color change)
   - Show active state for selected effect/palette
   - Add touch ripple effect

3. **Network Status:**
   - Test WiFi connection/disconnection
   - Verify latency metrics update correctly
   - Add connection quality indicator

### 11.3 Medium-Term (Next 3-5 Sessions)
1. **DSP Widget Integration:**
   - Connect PPM meter to audio levels
   - Wire RTA footer to spectrum data
   - Add visual feedback for audio activity

2. **Status Zone Enhancement:**
   - Populate status boxes with real metrics
   - Add effect/palette name display
   - Show BPM, key, tempo information

3. **Settings/Configuration:**
   - Add WiFi configuration UI
   - Implement brightness control
   - Add theme selection

### 11.4 Long-Term Goals
1. **Multiple Pages:**
   - Effects selection page
   - Settings page
   - Visualizer page

2. **Advanced Features:**
   - Scene presets
   - Timeline/automation
   - MIDI integration

3. **Performance Optimization:**
   - Reduce frame time
   - Optimize LVGL rendering
   - Minimize OSC latency

---

## 12. Contact & Support

### 12.1 Development Team
- **Hardware:** M5Stack Tab5 (ESP32-P4)
- **Software:** K1-Lightwave LED Control System
- **Framework:** PlatformIO + Arduino + LVGL

### 12.2 Documentation
- **LVGL Docs:** https://docs.lvgl.io/master/
- **ESP-IDF Docs:** https://docs.espressif.com/projects/esp-idf/
- **PlatformIO Docs:** https://docs.platformio.org/

### 12.3 Useful Commands Reference
```bash
# Build firmware
cd K1.tab5/pio/deck
export PATH="$HOME/.platformio/packages/toolchain-riscv32-esp@src-f96751ec4e9b59062ea536896ff4f77e/bin:$PATH"
platformio run

# Upload firmware (close serial monitors first!)
platformio run --target upload --upload-port /dev/cu.usbmodem21401

# Monitor serial output
platformio device monitor --port /dev/tty.usbmodem21401 --baud 115200

# Clean build
platformio run --target clean

# Check serial ports
ls /dev/tty.usb* /dev/cu.usb*

# Kill process using serial port
lsof | grep usbmodem21401
kill -9 <PID>
```

---

## 13. Appendix: Complete Code Snippets

### 13.1 Complete Footer Creation Function

**File:** `src/deck_ui.cpp:267-307`

```cpp
static void create_footer(lv_obj_t* parent) {
  const int footer_y = TAB5_SCREEN_HEIGHT - TAB5_FOOTER_HEIGHT - TAB5_GRID_MARGIN;  // 720 - 88 - 24 = 608

  // Footer bar - EXACTLY matching header style
  gFooter = lv_obj_create(parent);
  lv_obj_set_size(gFooter, LV_PCT(100), TAB5_FOOTER_HEIGHT);
  lv_obj_set_pos(gFooter, 0, footer_y);
  lv_obj_set_style_bg_color(gFooter, lv_color_hex(TAB5_COLOR_BG_SURFACE_ELEVATED), LV_PART_MAIN);
  lv_obj_set_style_border_width(gFooter, 3, LV_PART_MAIN);
  lv_obj_set_style_border_color(gFooter, lv_color_hex(0xFFFFFF), LV_PART_MAIN);
  lv_obj_set_style_radius(gFooter, 14, LV_PART_MAIN);
  lv_obj_clear_flag(gFooter, LV_OBJ_FLAG_SCROLLABLE);

  // Latency (left) - MOVED FROM HEADER
  gStatusLatency = lv_label_create(gFooter);
  lv_label_set_text(gStatusLatency, "---ms");
  lv_obj_set_style_text_font(gStatusLatency, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gStatusLatency, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_align(gStatusLatency, LV_ALIGN_LEFT_MID, 30, 0);

  // Delta time (left-center) - MOVED FROM HEADER
  gStatusDeltaTime = lv_label_create(gFooter);
  lv_label_set_text(gStatusDeltaTime, "Δt: ---ms");
  lv_obj_set_style_text_font(gStatusDeltaTime, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gStatusDeltaTime, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_set_pos(gStatusDeltaTime, 150, 32);

  // Uptime (center-right)
  gFooterUptime = lv_label_create(gFooter);
  lv_label_set_text(gFooterUptime, "UPTIME: 0h 0m");
  lv_obj_set_style_text_font(gFooterUptime, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gFooterUptime, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_align(gFooterUptime, LV_ALIGN_CENTER, 100, 0);

  // FPS (right)
  gFooterFPS = lv_label_create(gFooter);
  lv_label_set_text(gFooterFPS, "FPS: --");
  lv_obj_set_style_text_font(gFooterFPS, &bebas_neue_24px, LV_PART_MAIN);
  lv_obj_set_style_text_color(gFooterFPS, lv_color_hex(TAB5_COLOR_FG_SECONDARY), LV_PART_MAIN);
  lv_obj_align(gFooterFPS, LV_ALIGN_RIGHT_MID, -30, 0);
}
```

### 13.2 Complete Touch Event Handlers

**File:** `src/deck_ui.cpp:309-327`

```cpp
// Touch event handlers
static void effect_btn_event_cb(lv_event_t* e) {
  // TODO: Implement effect cycling (send OSC to host)
  LOG("[touch] EFFECT button clicked");
}

static void palette_btn_event_cb(lv_event_t* e) {
  // TODO: Implement palette cycling (send OSC to host)
  LOG("[touch] PALETTE button clicked");
}

static void direction_toggle_event_cb(lv_event_t* e) {
  // TODO: Toggle direction INWARD/OUTWARD (send OSC to host)
  LOG("[touch] DIRECTION toggle clicked");
  const char* current = lv_label_get_text(gDirectionLabel);
  if (strcmp(current, "[ INWARD ]") == 0) {
    lv_label_set_text(gDirectionLabel, "[ OUTWARD ]");
  } else {
    lv_label_set_text(gDirectionLabel, "[ INWARD ]");
  }
}
```

### 13.3 Complete Network Status Update Function

**File:** `src/deck_ui.cpp:360-391`

```cpp
void Deck_UI_UpdateNetworkStatus(const char* ip, int port, bool hostConnected, int latencyMs, int deltaTimeMs) {
  char buf[64];

  // Update IP with PORT
  if (ip) {
    snprintf(buf, sizeof(buf), "IP: %s:%d", ip, port);
    lv_label_set_text(gStatusIP, buf);
  }

  lv_label_set_text(gStatusHost, hostConnected ? "HOST: Connected" : "HOST: Disconnected");
  lv_obj_set_style_text_color(gStatusHost,
    hostConnected ? lv_color_hex(TAB5_COLOR_BRAND_PRIMARY) : lv_color_hex(TAB5_COLOR_FG_SECONDARY),
    LV_PART_MAIN);

  // Update FOOTER latencies (not header)
  if (gStatusLatency) {
    if (hostConnected && latencyMs >= 0) {
      snprintf(buf, sizeof(buf), "%dms", latencyMs);
      lv_label_set_text(gStatusLatency, buf);
    } else {
      lv_label_set_text(gStatusLatency, "---ms");
    }
  }

  if (gStatusDeltaTime) {
    if (hostConnected && deltaTimeMs >= 0) {
      snprintf(buf, sizeof(buf), "Δt: %dms", deltaTimeMs);
      lv_label_set_text(gStatusDeltaTime, buf);
    } else {
      lv_label_set_text(gStatusDeltaTime, "Δt: ---ms");
    }
  }
}
```

---

## Document Version

**Version:** 1.0
**Date:** October 16, 2025
**Author:** Claude (Anthropic)
**Session Duration:** 2 hours
**Lines of Code Modified:** ~500
**Files Modified:** 4
**Build Status:** ✅ SUCCESS
**Upload Status:** ⚠️ PENDING (serial port busy)

---

## END OF HANDOVER DOCUMENT

**READY FOR NEXT SESSION** ✅
