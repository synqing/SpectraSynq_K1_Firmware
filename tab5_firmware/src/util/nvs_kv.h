#pragma once
/**
 * Minimal NVS key-value helper (IDF NVS), safe for Arduino/ESP-IDF hybrids.
 */
#include <Arduino.h>
#include <nvs.h>
#include <nvs_flash.h>

namespace NvsKV {

bool init();  // idempotent
bool setFloat(const char* key, float value);
bool getFloat(const char* key, float& outValue);

} // namespace NvsKV
