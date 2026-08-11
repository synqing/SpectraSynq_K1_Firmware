from pathlib import Path
from SCons.Script import Import  # type: ignore

Import("env")

_TARGET_FOLDERS = (
    ("helium", "lv_blend_helium.S"),
    ("neon", "lv_blend_neon.S"),
)


def disable_arm_specific_sources():
    project_dir = Path(env["PROJECT_DIR"])
    pioenv = env["PIOENV"]
    base = (
        project_dir
        / ".pio"
        / "libdeps"
        / pioenv
        / "lvgl"
        / "src"
        / "draw"
        / "sw"
        / "blend"
    )

    if not base.exists():
        return

    for folder, filename in _TARGET_FOLDERS:
        source = base / folder / filename
        if not source.exists():
            continue
        disabled = source.with_suffix(".S.disabled")
        if disabled.exists():
            continue
        source.rename(disabled)
        print(f"[disable_lvgl_asm] Disabled ARM assembly source: {disabled.name}")


disable_arm_specific_sources()
