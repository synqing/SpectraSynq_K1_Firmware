#include "nvs_kv.h"
#include "tab5_config.h"

namespace {
  bool gNvsReady = false;
}

namespace NvsKV {

bool init() {
  if (gNvsReady) return true;
  esp_err_t err = nvs_flash_init();
  if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    nvs_flash_erase();
    err = nvs_flash_init();
  }
  gNvsReady = (err == ESP_OK);
  return gNvsReady;
}

bool setFloat(const char* key, float value) {
  if (!gNvsReady && !init()) return false;
  nvs_handle_t h;
  if (nvs_open(TAB5_NS_NAME, NVS_READWRITE, &h) != ESP_OK) return false;
  esp_err_t err = nvs_set_blob(h, key, &value, sizeof(float));
  if (err == ESP_OK) err = nvs_commit(h);
  nvs_close(h);
  return err == ESP_OK;
}

bool getFloat(const char* key, float& outValue) {
  if (!gNvsReady && !init()) return false;
  nvs_handle_t h;
  if (nvs_open(TAB5_NS_NAME, NVS_READONLY, &h) != ESP_OK) return false;
  size_t len = sizeof(float);
  esp_err_t err = nvs_get_blob(h, key, &outValue, &len);
  nvs_close(h);
  return (err == ESP_OK && len == sizeof(float));
}

} // namespace NvsKV
