# The K1 firmware sources, exactly the PlatformIO env's build_src_filter (k1_profile.cmake),
# plus the sketch converted to C++ the way PlatformIO does it (tools/k1_ino_to_cpp.py).
set(k1_requires arduino-esp32 fastled fixedpoints m5rotate8 esp_driver_pcnt)
if(CMAKE_BUILD_EARLY_EXPANSION)
    idf_component_register(REQUIRES ${k1_requires})
    return()
endif()

idf_build_get_property(k1_profile_cmake K1_PROFILE_CMAKE)
idf_build_get_property(k1_s31_flags K1_S31_FLAGS)
idf_build_get_property(k1_s31_dir K1_S31_DIR)
include("${k1_profile_cmake}")

set(k1_sketch_cpp "${CMAKE_BINARY_DIR}/k1_sketch.ino.cpp")
execute_process(
    COMMAND python3 "${k1_s31_dir}/tools/k1_ino_to_cpp.py" "${K1_INO}" "${k1_sketch_cpp}"
    RESULT_VARIABLE k1_ino_rc)
if(NOT k1_ino_rc EQUAL 0)
    message(FATAL_ERROR "k1_ino_to_cpp.py failed for ${K1_INO}")
endif()
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${K1_INO}")

idf_component_register(
    SRCS ${K1_SOURCES} "${k1_sketch_cpp}"
    INCLUDE_DIRS ${K1_INCLUDE_DIRS}
    REQUIRES ${k1_requires})

target_compile_options(${COMPONENT_LIB} PRIVATE ${K1_FLAGS} ${k1_s31_flags} ${K1_PROVENANCE} ${K1_SRC_FLAGS})
