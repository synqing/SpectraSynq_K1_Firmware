"""PlatformIO pre-build hook: add the effect-framework dir to CPPPATH.

Used ONLY by the `k1_effect_framework` env (the P1 effect-framework graft probe
build). It registers `SPECTRASYNQ_K1_FIRMWARE/effects/framework` on the compiler
include path so the framework headers resolve when compiled from the env's
extended build_src_filter, regardless of the including TU's location.

CPPPATH is appended as a SCons list member (NOT a space-split build_flag) so it
survives the space in the repo path ("SensoryBridge-main 9"). This script is
NOT registered by env:k1_hardware, so the shipping default build is unaffected.
"""
import os

Import("env")  # noqa: F821  (injected by PlatformIO/SCons)

_SRC = env.subst("$PROJECT_SRC_DIR")  # noqa: F821
env.Append(CPPPATH=[os.path.join(_SRC, "effects", "framework")])  # noqa: F821
