# SSA Evidence Note: Tab5 Battery Header Reference

Task ID: `tab5-battery-header-reference`

Verdict: `PARTIALLY_VERIFIED`

- Verified from local source: SensoryBridge Tab5 has a concrete M5Unified power API wrapper in `sb-tab5-wireless-controller/src/hal/EspHal.h:34-47` and `sb-tab5-wireless-controller/src/hal/EspHal.cpp:29-39`: `EspHal::getBatteryLevel()` calls `M5.Power.getBatteryLevel()`, `EspHal::isCharging()` calls `M5.Power.isCharging()`, and `EspHal::getBatteryVoltage()` returns `M5.Power.getBatteryVoltage() / 1000.0f`.
- Important build caveat: current `env:tab5` defines `K1_TAB5_TOUCH_CONTROLLER=1` and compiles only `main.cpp`, `network/K1WebSocketClient.cpp`, `ui/LightComposerUI.cpp`, `ui/lvgl_bridge.cpp`, and fonts via `sb-tab5-wireless-controller/platformio.ini:31-45`. `src/hal/EspHal.cpp`, `src/ui/DisplayUI.cpp`, and `src/ui/widgets/UIHeader.cpp` are not in the active build unless `build_src_filter` changes.
- Existing SensoryBridge UI precedent, but inactive for current build: `UIHeader::setPower(int8_t batteryPercent, bool isCharging, float voltage)` stores power state and marks dirty in `sb-tab5-wireless-controller/src/ui/widgets/UIHeader.cpp:38-45`; `UIHeader::drawPowerBar()` draws voltage, percentage, bar, low-battery colour, and charging text in `sb-tab5-wireless-controller/src/ui/widgets/UIHeader.cpp:128-190`.
- Existing SensoryBridge footer precedent, also inactive for current build: `DisplayUI::loop()` reads `EspHal::getBatteryLevel()` at 1 Hz and updates `_footer_battery` / `_footer_battery_bar` in `sb-tab5-wireless-controller/src/ui/DisplayUI.cpp:1435-1472`.
- Active SensoryBridge Tab5 seam: `main.cpp` constructs `LightComposerUI` after `M5.begin(cfg)` in `sb-tab5-wireless-controller/src/main.cpp:173-183` and calls `g_ui->loop()` each main loop in `sb-tab5-wireless-controller/src/main.cpp:229-245`. The active header is created in `LightComposerUI::createHeader()` with right-side pills at `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:337-359`, and refreshed in `LightComposerUI::refreshStatus()` at `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:657-665`.
- PIPdeck-Tab5 has only a simulated UI precedent, not a hardware power API: `DeviceHealth` contains `battery_pct` in `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/simulation_data.h:31`, `ui_refresh_apply_utility_strip()` renders `"BAT %ld%%"` from that field in `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/ui_refresh.cpp:78-80`, and `simulation_data.cpp:19` seeds it locally. This should not be treated as actual Tab5 battery truth.
- PIPdeck hardware-reference evidence is non-authoritative for runtime battery: `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/prototype/tab5_stats_prototype/tab5_stats_prototype.ino:82-83` only says `display.init()` powers the panel/touch; `/Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5/Git-Examples/M5Stack_Tab5_Arduino_Basic_LVGL_Demo/tab5_arduino_basic/pins_config.h:45-46` only carries a commented `BATTERY_VOLTAGE_ADC_DATA -1` note, not a working API.

Required rerun command:

```bash
rg -n "Battery|battery|Power|power|AXP|PMU|getBattery|isCharging|voltage|percent" /Users/spectrasynq/SensoryBridge-main\ 9/sb-tab5-wireless-controller /Users/spectrasynq/Workspace_Management/Software/PIPdeck-Tab5 -S
```

Recommended implementation seam:

Wire the header power remaining bar inside active `LightComposerUI`, not `DisplayUI` or `UIHeader`, unless the build filter is intentionally expanded. Add LVGL refs for a compact battery percentage label/bar in `LightComposerUI.h`, create them in `LightComposerUI::createHeader()` near the existing right-side status pills, and update them from `LightComposerUI::refreshStatus()` or a new 1 Hz `refreshPowerStatus()` throttle. Source the values from `M5.Power.*` directly or, preferably, add `+<hal/EspHal.cpp>` to `env:tab5` and reuse `EspHal::*`; keep unknown readings as `--`, clamp 0-100 before `lv_bar_set_value`, and use the existing low/yellow/green/charging behaviour as visual precedent only after confirming it does not crowd the three active header pills.
