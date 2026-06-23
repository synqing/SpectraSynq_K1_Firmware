"""PlatformIO pre-build hook: add the K1 firmware source subfolders to CPPPATH.

Phase 1 of the firmware restructure (docs/refactor/k1-firmware-restructure-and-
rebrand-plan.md) moved the formerly-flat sources into functional subdirs. Bare
`#include "x.h"` is preserved unchanged; this script puts every subdir on the
compiler include path so those includes resolve regardless of which subdir the
includer lives in.

CPPPATH entries are appended as SCons list members (NOT space-split build_flags),
so they survive the space in the repo path ("SensoryBridge-main 9"). All envs
extend env:k1_hardware, so registering here covers the whole build matrix.
"""
import os

Import("env")  # noqa: F821  (injected by PlatformIO/SCons)

_SRC = env.subst("$PROJECT_SRC_DIR")  # noqa: F821
_SUBDIRS = (
    "audio", "visual", "effects", "director", "control", "network",
    "serial", "system", "persistence", "calibration", "diag",
)
env.Append(CPPPATH=[os.path.join(_SRC, d) for d in _SUBDIRS])  # noqa: F821

# pioarduino 54.x splits ESP-IDF headers from the memory-type sdkconfig root.
# Clean builds compile FastLED library files before sketch objects; make the
# selected sdkconfig.h visible there too.
_FRAMEWORK_LIBS = env.PioPlatform().get_package_dir("framework-arduinoespressif32-libs")  # noqa: F821
_BOARD_MCU = env.BoardConfig().get("build.mcu", "esp32s3")  # noqa: F821
_MEMORY_TYPE = env.GetProjectOption("board_build.arduino.memory_type") or "qio_qspi"  # noqa: F821

if _FRAMEWORK_LIBS:
    _SDKCONFIG_DIR = os.path.join(_FRAMEWORK_LIBS, _BOARD_MCU, _MEMORY_TYPE, "include")
    if os.path.exists(os.path.join(_SDKCONFIG_DIR, "sdkconfig.h")):
        env.Append(CPPPATH=[_SDKCONFIG_DIR])  # noqa: F821
