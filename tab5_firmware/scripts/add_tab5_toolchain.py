"""
Ensure the Tab5 deck build uses vendored toolchains and a predictable python.

This script runs as an `extra_script` before build tasks so we can mutate the
SCons environment without relying on global PlatformIO state.
"""

from pathlib import Path
import sys

Import("env")  # type: ignore

project_dir = Path(env["PROJECT_DIR"])
vendor_dir = project_dir / "vendor"
package_root = vendor_dir / "pio_packages"

# Prefer the vendored python shim so Espressif's tooling finds `python`.
python_dir = vendor_dir / "python"
python_exe = python_dir / "python"
if python_exe.exists():
    env.PrependENVPath("PATH", str(python_dir))
    resolved_python = str(python_exe.resolve())
else:
    resolved_python = sys.executable

env.Replace(PYTHONEXE=resolved_python)
env["ENV"]["PYTHONEXE"] = resolved_python
env["ENV"]["PYTHON"] = resolved_python
env["ENV"].setdefault("IDF_COMPONENT_MANAGER", "0")

# Make sure build tools find the vendored binaries before anything else.
bin_dirs = [
    package_root / "toolchain-riscv32-esp" / "bin",
    package_root / "toolchain-xtensa-esp-elf" / "bin",
    package_root / "toolchain-esp32ulp" / "bin",
    package_root / "tool-cmake" / "bin",
    package_root / "tool-ninja",
]
for path in bin_dirs:
    print(f"[tab5_toolchain] checking tool path: {path}")
    if path.exists():
        env.PrependENVPath("PATH", str(path))
    else:
        print(f"[tab5_toolchain] missing expected tool path: {path}")
