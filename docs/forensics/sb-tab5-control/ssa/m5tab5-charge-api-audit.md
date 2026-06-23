# SSA Evidence Note: M5Tab5 Charge API Audit

Task ID: `m5tab5-charge-api-audit`

Verdict: `VERIFIED_SOURCE_ONLY`

## Evidence Question

In the installed/current M5Unified/M5Stack Tab5 libraries, what API best distinguishes actively charging from merely externally powered/full, and what fallback is safest if no current-charge API exists?

## Required Search

Ran from repo root:

```bash
rg -n "isCharging|getBatteryLevel|getBattery|getCharge|charge|Battery|Power" sb-tab5-wireless-controller ~/.platformio/packages ~/.platformio/lib ~/.platformio/.cache 2>/dev/null
```

Result: 34,569 matches across 11,361 files; exit code 2 after broad package scan noise. The useful source-truth hits were narrowed to `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified` and the active Tab5 controller sources.

## Installed Dependency Truth

- `sb-tab5-wireless-controller/platformio.ini:48-50` pins `M5Unified` to `https://github.com/M5Stack/M5Unified.git#a625672` and `M5GFX` to `#53a7184`.
- Installed local dependency commit for `M5Unified`: `a6256725481f1bc366655fa48cf03b6095e30ad1`.
- `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/library.json:19` identifies the installed library as `M5Unified` version `0.2.13`.

## Current Tab5 App Behaviour

- Active Tab5 UI code reads `M5.Power.getBatteryLevel()` and `M5.Power.isCharging()` every 2 seconds in `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:802-808`.
- The active label renders `"CHG"` when `_batteryCharging` is true and `"POWER"` otherwise in `sb-tab5-wireless-controller/src/ui/LightComposerUI.cpp:814-818`.
- The older HAL wrapper also maps `EspHal::isCharging()` directly to `M5.Power.isCharging()` in `sb-tab5-wireless-controller/src/hal/EspHal.cpp:29-39`, and `DisplayUI::updateHeader()` passes that boolean into the header in `sb-tab5-wireless-controller/src/ui/DisplayUI.cpp:2478-2486`.
- `UIHeader::drawPowerBar()` draws `CHG` directly when `_isCharging` is true in `sb-tab5-wireless-controller/src/ui/widgets/UIHeader.cpp:200-208`.

Implication: the current UI can show `CHG` from `M5.Power.isCharging()` alone.

## M5Unified Tab5 Power Implementation

- `M5Unified` detects ESP32-P4 Tab5 as `board_M5Tab5` in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/M5Unified.cpp:1404-1413`.
- Tab5 power setup configures IO expander 1 bits including `CHG_EN`, `CHG_STAT`, `nCHG_QC_EN`, `PWROFF_PLUSE`, and `USB5V_EN` in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/Power_Class.cpp:65-110`.
- Tab5 initialises an `INA226` current/voltage monitor with shunt and bus conversion enabled in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/Power_Class.cpp:101-109`.
- The ESP32-P4 `Power_Class` member is `INA226_Class Ina226 = { 0x41 }` in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/Power_Class.hpp:220-221`.

## `isCharging()` Is Not Current Truth

- The public API says `isCharging()` gets whether the battery is currently charging in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/Power_Class.hpp:166-168`.
- For Tab5 specifically, `Power_Class::isCharging()` returns `is_charging` only from IO expander 1 pin 6, labelled `CHG_STAT`, in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/Power_Class.cpp:1725-1774`.
- That Tab5 path does not read `INA226`, battery current, or charge current. It reads only `M5.getIOExpander(1).digitalRead(6)`.

Conclusion: `M5.Power.isCharging()` is charger-status-pin truth for Tab5, not measured charge-current truth. It should not be the sole condition for a user-visible `CHG` claim if the product meaning is "actively charging now".

## Best Installed API For Active Charging

- The public API documents `getBatteryCurrent()` as battery current in mA with `+=charge / -=discharge` in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/Power_Class.hpp:179-181`.
- For Tab5, `Power_Class::getBatteryCurrent()` returns `1000.0f * Ina226.getShuntCurrent()` in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/Power_Class.cpp:1633-1672`.
- `INA226_Class::getShuntCurrent()` reads the signed INA226 current register and multiplies by `_cur_lsb` in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/power/INA226_Class.cpp:53-57`.
- The installed `INA226` config derives `_cur_lsb` from `max_expected_current / 32768.0f` and the configured shunt resistance in `sb-tab5-wireless-controller/.pio/libdeps/tab5/M5Unified/src/utility/power/INA226_Class.cpp:24-38`.

Recommended condition:

```cpp
const int32_t batteryCurrentMa = M5.Power.getBatteryCurrent();
const bool activelyCharging = batteryCurrentMa > 10;
```

Use a small positive deadband rather than `> 0` to avoid flicker/noise near full charge. If the header must be visually stable, use hysteresis, for example enter `CHG` above `+25 mA` and leave `CHG` below `+5 mA`. The sign recommendation follows the installed public API contract; a one-time live serial check should still record polarity on the actual Tab5 before treating the display as hardware-validated.

## Safest Fallback If Current Is Unavailable

If `M5.Power.getBatteryCurrent()` is unavailable, returns a constant unsupported value, or has unvalidated polarity, do not display `CHG`.

Fallback condition:

```cpp
const bool activelyCharging = false;
```

Fallback UI: render battery percentage/voltage plus neutral `POWER` or a plug/external-power indicator if a separate external-power API is proven. Do not infer active charging from `M5.Power.isCharging()` alone; at most treat it as advisory charger-status-pin evidence and label it neutrally. This avoids the load-bearing failure mode where the battery header lies with `CHG` when the device is externally powered, full, or not accepting charge current.

## Final Recommendation

For the Tab5 controller header, use `M5.Power.getBatteryCurrent()` with a positive mA deadband as the active-charge gate. Keep `M5.Power.isCharging()` out of the `CHG` condition unless it is combined with measured positive current and explicitly treated as an advisory consistency check.

Recommended display logic:

```cpp
const int32_t batteryCurrentMa = M5.Power.getBatteryCurrent();
const bool activelyCharging = batteryCurrentMa > 10;
const char* powerLabel = activelyCharging ? "CHG" : "POWER";
```

Verification boundary: this is source-verified against the installed M5Unified library and current Tab5 code. It is not live hardware-validated for current polarity or deadband size.
