"""Expose the exact toolchain packages resolved by PlatformIO."""

from pathlib import Path
import sys

Import("env")  # type: ignore

resolved_python = sys.executable

env.Replace(PYTHONEXE=resolved_python)
env["ENV"]["PYTHONEXE"] = resolved_python
env["ENV"]["PYTHON"] = resolved_python
env["ENV"].setdefault("IDF_COMPONENT_MANAGER", "0")

# Make sure build tools find PlatformIO's pinned packages before anything else.
platform = env.PioPlatform()
package_names = (
    "toolchain-riscv32-esp",
    "toolchain-xtensa-esp-elf",
    "toolchain-esp32ulp",
    "tool-cmake",
    "tool-ninja",
)
bin_dirs = []
for package_name in package_names:
    package_dir = platform.get_package_dir(package_name)
    if not package_dir:
        continue
    root = Path(package_dir)
    bin_dirs.append(root / "bin" if (root / "bin").exists() else root)
for path in bin_dirs:
    print(f"[tab5_toolchain] checking tool path: {path}")
    if path.exists():
        env.PrependENVPath("PATH", str(path))
    else:
        print(f"[tab5_toolchain] missing resolved tool path: {path}")
