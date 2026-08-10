"""Apply the declared Tab5 overlay to the official Arduino-ESP32 3.3.1.

The live Tab5 framework was forensic-matched to the official 3.3.1 tree for
the complete Arduino core and BLE library. Its relevant deltas are a two-line
soft-AP guard and the CMake include/link wiring for the pinned ESP-Hosted
archives. Fail closed on any unexpected source so a future package cannot be
silently patched at the wrong location.
"""

from hashlib import sha256
from pathlib import Path

Import("env")  # type: ignore

WIFI_PRISTINE_SHA256 = "b659b03c38f65ddb6e4a98312812644354820c286969687ef1f136a18eb31d5d"
WIFI_PATCHED_SHA256 = "df813832ed42383ea6be7912e1d2f51df6665c0c66bf0c16a7c41309a2f672b7"
CMAKE_PRISTINE_SHA256 = "7a398958c10bc6c8e2c5c0dc5f4d4f4d0f7a21f5d3947322bd2e6e915fdd0678"
CMAKE_PATCHED_SHA256 = "daa88106af9d04ef5852905ce69c493bb8bb286415e335c7d9ad9ff06deb496d"
HOSTED_C_SHA256 = "c3dd9080dbae6a6d2ea79e93c22f7a052fffcba5eb6e79a7d6e1e810e3a39fbb"
HOSTED_H_SHA256 = "d465214411ed910f10a691be9ee5a008d785c7339f4e37f912a112f29eb8fe2b"

PRISTINE = """      if (esp_netifs[ESP_IF_WIFI_AP] == NULL) {
        esp_netifs[ESP_IF_WIFI_AP] = esp_netif_create_default_wifi_ap();
      }
"""

PATCHED = """#if CONFIG_ESP_WIFI_SOFTAP_SUPPORT
      if (esp_netifs[ESP_IF_WIFI_AP] == NULL) {
        esp_netifs[ESP_IF_WIFI_AP] = esp_netif_create_default_wifi_ap();
      }
#endif
"""

CMAKE_INCLUDE_PRISTINE = (
    "set(includedirs variants/${CONFIG_ARDUINO_VARIANT}/ cores/esp32/ "
    "${ARDUINO_LIBRARIES_INCLUDEDIRS})"
)

CMAKE_INCLUDE_PATCHED = """set(TAB5_P4_LIBS "${CMAKE_SOURCE_DIR}/.pio/tab5_framework_libs/esp32p4")
set(TAB5_P4_INCLUDEDIRS
  "${TAB5_P4_LIBS}/include/espressif__esp_wifi_remote/idf_v5.4/include/injected"
  "${TAB5_P4_LIBS}/include/espressif__esp_hosted/host"
  "${TAB5_P4_LIBS}/include/espressif__esp_hosted/host/api/include"
  "${TAB5_P4_LIBS}/include/espressif__esp_hosted/host/port/esp/freertos/include")
set(includedirs variants/${CONFIG_ARDUINO_VARIANT}/ cores/esp32/ ${ARDUINO_LIBRARIES_INCLUDEDIRS} ${TAB5_P4_INCLUDEDIRS})"""

CMAKE_REGISTER_PRISTINE = (
    "idf_component_register(INCLUDE_DIRS ${includedirs} "
    "PRIV_INCLUDE_DIRS ${priv_includes} SRCS ${srcs} REQUIRES ${requires} "
    "PRIV_REQUIRES ${priv_requires})"
)

CMAKE_REGISTER_PATCHED = CMAKE_REGISTER_PRISTINE + """

target_link_libraries(${COMPONENT_LIB} PUBLIC
  "${CMAKE_SOURCE_DIR}/.pio/generated/tab5_p4/libespressif__esp_hosted_tab5.a"
  "${CMAKE_SOURCE_DIR}/.pio/generated/tab5_p4/libespressif__esp_wifi_remote_tab5.a"
  "${TAB5_P4_LIBS}/lib/libespressif__esp_serial_slave_link.a"
  "${TAB5_P4_LIBS}/lib/libespressif__eppp_link.a")"""


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


framework_dir = env.PioPlatform().get_package_dir("framework-arduinoespressif32")
framework_libs_dir = env.PioPlatform().get_package_dir("framework-arduinoespressif32-libs")
if not framework_dir or not framework_libs_dir:
    raise RuntimeError("Pinned framework-arduinoespressif32 package was not resolved")

framework = Path(framework_dir)
hosted_c = framework / "cores" / "esp32" / "esp32-hal-hosted.c"
hosted_h = framework / "cores" / "esp32" / "esp32-hal-hosted.h"
if digest(hosted_c) != HOSTED_C_SHA256 or digest(hosted_h) != HOSTED_H_SHA256:
    raise RuntimeError("Arduino-ESP32 hosted HAL does not match the frozen 3.3.1 source")

wifi = framework / "libraries" / "WiFi" / "src" / "WiFiGeneric.cpp"
wifi_actual = digest(wifi)
if wifi_actual == WIFI_PRISTINE_SHA256:
    text = wifi.read_text(encoding="utf-8")
    if text.count(PRISTINE) != 1:
        raise RuntimeError("Arduino-ESP32 3.3.1 guard anchor is not unique")
    wifi.write_text(text.replace(PRISTINE, PATCHED), encoding="utf-8")
elif wifi_actual != WIFI_PATCHED_SHA256:
    raise RuntimeError(f"Refusing unexpected WiFiGeneric.cpp sha256={wifi_actual}")
if digest(wifi) != WIFI_PATCHED_SHA256:
    raise RuntimeError("Arduino-ESP32 P4 soft-AP patch checksum mismatch")

cmake = framework / "CMakeLists.txt"
cmake_actual = digest(cmake)
if cmake_actual == CMAKE_PRISTINE_SHA256:
    text = cmake.read_text(encoding="utf-8")
    if text.count(CMAKE_INCLUDE_PRISTINE) != 1:
        raise RuntimeError("Arduino-ESP32 include anchor is not unique")
    if text.count(CMAKE_REGISTER_PRISTINE) != 1:
        raise RuntimeError("Arduino-ESP32 component anchor is not unique")
    text = text.replace(CMAKE_INCLUDE_PRISTINE, CMAKE_INCLUDE_PATCHED)
    text = text.replace(CMAKE_REGISTER_PRISTINE, CMAKE_REGISTER_PATCHED)
    cmake.write_text(text, encoding="utf-8")
elif cmake_actual != CMAKE_PATCHED_SHA256:
    raise RuntimeError(f"Refusing unexpected Arduino CMakeLists.txt sha256={cmake_actual}")
if digest(cmake) != CMAKE_PATCHED_SHA256:
    raise RuntimeError("Arduino-ESP32 CMake overlay checksum mismatch")

project_link = Path(env["PROJECT_DIR"]) / ".pio" / "tab5_framework_libs"
resolved_libs = Path(framework_libs_dir).resolve()
if project_link.is_symlink():
    if project_link.resolve() != resolved_libs:
        project_link.unlink()
        project_link.symlink_to(resolved_libs, target_is_directory=True)
elif project_link.exists():
    raise RuntimeError(f"Refusing to replace non-symlink framework path: {project_link}")
else:
    project_link.parent.mkdir(parents=True, exist_ok=True)
    project_link.symlink_to(resolved_libs, target_is_directory=True)

print("[tab5_framework] verified frozen Arduino-ESP32 3.3.1 Tab5 overlay")
