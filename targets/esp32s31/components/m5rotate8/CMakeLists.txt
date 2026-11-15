# libraries/M5ROTATE8 (the same copy PlatformIO uses via lib_deps file://libraries/M5ROTATE8).
get_filename_component(K1_REPO "${CMAKE_CURRENT_LIST_DIR}/../../../.." ABSOLUTE)
idf_component_register(SRCS "${K1_REPO}/libraries/M5ROTATE8/m5rotate8.cpp"
                       INCLUDE_DIRS "${K1_REPO}/libraries/M5ROTATE8"
                       REQUIRES arduino-esp32)
