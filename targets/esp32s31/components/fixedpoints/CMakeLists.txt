# libraries/FixedPoints (the same copy PlatformIO uses via lib_deps file://libraries/FixedPoints).
get_filename_component(K1_REPO "${CMAKE_CURRENT_LIST_DIR}/../../../.." ABSOLUTE)
idf_component_register(INCLUDE_DIRS "${K1_REPO}/libraries/FixedPoints/src")
