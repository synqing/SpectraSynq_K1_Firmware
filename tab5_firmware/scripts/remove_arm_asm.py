#!/usr/bin/env python3
"""
Remove ARM-specific assembly files from LVGL for RISC-V builds.
These files cause linker errors on ESP32-P4 (RISC-V architecture).
"""

Import("env")
import os
import glob

def remove_arm_assembly_files(source, target, env):
    """Remove ARM assembly .S files and .o objects from LVGL library"""

    # Get the build directory
    build_dir = env.subst("$BUILD_DIR")
    libdeps_dir = os.path.join(build_dir, "..", "..", "libdeps", env["PIOENV"])

    # Patterns to remove
    patterns = [
        os.path.join(libdeps_dir, "lvgl", "src", "draw", "sw", "blend", "helium", "*.S"),
        os.path.join(libdeps_dir, "lvgl", "src", "draw", "sw", "blend", "helium", "*.o"),
        os.path.join(libdeps_dir, "lvgl", "src", "draw", "sw", "blend", "neon", "*.S"),
        os.path.join(libdeps_dir, "lvgl", "src", "draw", "sw", "blend", "neon", "*.o"),
        os.path.join(build_dir, "**/lvgl/**/helium/*.S.o"),
        os.path.join(build_dir, "**/lvgl/**/neon/*.S.o"),
    ]

    removed_files = []
    for pattern in patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    removed_files.append(file_path)
            except Exception as e:
                print(f"Warning: Could not remove {file_path}: {e}")

    if removed_files:
        print(f"Removed {len(removed_files)} ARM assembly files for RISC-V compatibility")

# Register the callback to run before linking
env.AddPreAction("$BUILD_DIR/${PROGNAME}.elf", remove_arm_assembly_files)
