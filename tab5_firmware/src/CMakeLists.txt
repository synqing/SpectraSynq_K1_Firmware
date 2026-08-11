# Tab5 app sources for the Arduino+ESP-IDF hybrid build.
# PlatformIO build_src_filter alone does NOT gate ESP-IDF component SRCS —
# this file is the quarantine authority for tab5_p4.

FILE(GLOB_RECURSE app_sources ${CMAKE_SOURCE_DIR}/src/*.*)

# A/B host 1.4.x ships stock vhci_drv.c; exclude our 2.0.13 stub replacement.
if(DEFINED ENV{TAB5_HOSTED_AB_VERSION})
  list(FILTER app_sources EXCLUDE REGEX "hosted_vhci_drv\\.c$")
  message(STATUS "Tab5 ESP-Hosted A/B: excluding src/hosted_vhci_drv.c")
endif()

# Precision Bay R1 G2 — quarantine legacy SoftAP/OSC UI path (Bay craft DEPRECATED).
# Kept on disk for archaeology; must not link into tab5_p4 / production.
list(FILTER app_sources EXCLUDE REGEX "/ui\\.cpp$")
list(FILTER app_sources EXCLUDE REGEX "/input\\.cpp$")
list(FILTER app_sources EXCLUDE REGEX "/lvgl_ui\\.cpp$")
list(FILTER app_sources EXCLUDE REGEX "/net\\.cpp$")
# Backup / hardened copies must never compile.
list(FILTER app_sources EXCLUDE REGEX "\\.bak$")
list(FILTER app_sources EXCLUDE REGEX "\\.orig$")
message(STATUS "Tab5 Deck16: legacy ui/input/lvgl_ui/net quarantined from idf component")

idf_component_register(SRCS ${app_sources})
