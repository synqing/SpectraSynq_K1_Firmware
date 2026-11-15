# K1 Founders' Edition firmware for the ESP32-S31 (Waveshare ESP32-S31-Zero), plain ESP-IDF v6.1.
#
# Same sources, same flags as a PlatformIO env (default k1_fe), read from platformio.ini at
# configure time by tools/k1_pio_profile.py. The S31 adds only -DK1_PLATFORM_S31 (system/
# k1_platform.h) and what this file declares. Arduino runs as an ESP-IDF component
# (espressif/arduino-esp32 4.0.0-rc1); FastLED 3.10.3 is a git component.
#
#   . ~/esp/esp-idf-v6.1/export.sh
#   idf.py --preview -B build/k1_fe     -DK1_PROFILE=k1_fe     -DSDKCONFIG=build/k1_fe/sdkconfig     build
#   idf.py --preview -B build/k1_fe_emu -DK1_PROFILE=k1_fe_emu -DSDKCONFIG=build/k1_fe_emu/sdkconfig build
#
# NOT authorised to flash: no S31 board is qualified and the pin map is unproven on silicon.

cmake_minimum_required(VERSION 3.22)

set(K1_PROFILE "k1_fe" CACHE STRING "PlatformIO env whose sources and flags this S31 image mirrors")
get_filename_component(K1_S31_DIR "${CMAKE_CURRENT_LIST_DIR}" ABSOLUTE)
get_filename_component(K1_REPO "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(K1_PROFILE_CMAKE "${CMAKE_BINARY_DIR}/k1_profile.cmake")

find_program(K1_PYTHON NAMES python3 REQUIRED)
execute_process(
    COMMAND "${K1_PYTHON}" "${K1_S31_DIR}/tools/k1_pio_profile.py" --env "${K1_PROFILE}" --cmake "${K1_PROFILE_CMAKE}"
    WORKING_DIRECTORY "${K1_REPO}"
    RESULT_VARIABLE k1_profile_rc)
if(NOT k1_profile_rc EQUAL 0)
    message(FATAL_ERROR "k1_pio_profile.py failed for env ${K1_PROFILE}")
endif()

# The S31 additions on top of the PlatformIO env. Nothing else differs.
set(K1_S31_FLAGS -DK1_PLATFORM_S31)

set(EXTRA_COMPONENT_DIRS "${K1_S31_DIR}/components")
set(SDKCONFIG_DEFAULTS "${K1_S31_DIR}/sdkconfig.defaults")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
idf_build_set_property(K1_PROFILE_CMAKE "${K1_PROFILE_CMAKE}")
idf_build_set_property(K1_S31_FLAGS "${K1_S31_FLAGS}")
idf_build_set_property(K1_S31_DIR "${K1_S31_DIR}")
project(k1_s31)

# PlatformIO compiles the Arduino core and FastLED with build_flags too, so the same flags go
# onto those components here (after IDF's own options, so -O3 wins). FixedPoints is
# header-only and takes the flags of whichever file includes it, as on the S3.
# PlatformIO compiles the Arduino core, FastLED and the K1 sources without -Werror. IDF 6.1
# keeps -Werror=all even with CONFIG_COMPILER_DISABLE_DEFAULT_ERRORS, and GCC 15 lets no
# later -Wno-error override it, so it is removed from the build-wide options here. This
# changes which warnings stop the build, not the generated code.
idf_build_replace_option_from_property(COMPILE_OPTIONS "-Werror=all" "")
include("${K1_PROFILE_CMAKE}")
foreach(k1_comp espressif__arduino-esp32 fastled m5rotate8)
    idf_component_get_property(k1_lib ${k1_comp} COMPONENT_LIB)
    target_compile_options(${k1_lib} PRIVATE ${K1_FLAGS} ${K1_S31_FLAGS})
endforeach()

# FastLED 3.10.3 on ESP-IDF 6.1 misses two declarations (S31 probe, 12 Nov 2026,
# docs/forensics/runtime-evidence/20261112-s31-port-probe/). Supplied by a forced include on
# FastLED only; the FastLED sources are not edited.
idf_component_get_property(k1_fastled fastled COMPONENT_LIB)
target_compile_options(${k1_fastled} PRIVATE -include "${K1_S31_DIR}/compat/fastled_idf61_compat.h")
