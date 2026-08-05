"""Boot palette lock: every K1 starts on K1_Naberius_Gold_gp, both channels.

Captain standing order, 2026-08-05. The risk this file exists to remove is a
SILENT one: K1_BOOT_PALETTE_INDEX is a bare number, and the palette it names is
decided purely by position in two arrays in visual/Palettes.h. Insert or reorder a
palette and index 40 quietly becomes a different colour -- the firmware still
builds, still boots, still lights up, and nothing anywhere reports that the boot
colour changed. These tests turn that into a build failure.
"""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PALETTES_H = FW / "visual" / "Palettes.h"
CONFIG_TYPES_H = FW / "system" / "config_types.h"
GLOBALS_CONFIG_CPP = FW / "system" / "globals_config.cpp"
GLOBALS_H = FW / "system" / "globals.h"
BRIDGE_FS_H = FW / "persistence" / "bridge_fs.h"

EXPECTED_PALETTE = "K1_Naberius_Gold_gp"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_array(source: str, pattern: str) -> list[str]:
    match = re.search(pattern, source, re.S)
    assert match, f"could not locate array with pattern {pattern!r}"
    return [entry.strip().strip('"') for entry in match.group(1).split(",") if entry.strip()]


def gradient_palettes() -> list[str]:
    return parse_array(read(PALETTES_H), r"gGradientPalettes\[\]\s*=\s*\{(.*?)\};")


def palette_names() -> list[str]:
    return parse_array(read(PALETTES_H), r"paletteNames\[\]\s*PROGMEM\s*=\s*\{(.*?)\};")


def boot_palette_index() -> int:
    match = re.search(r"#define\s+K1_BOOT_PALETTE_INDEX\s+(\d+)", read(CONFIG_TYPES_H))
    assert match, "K1_BOOT_PALETTE_INDEX is not defined in config_types.h"
    return int(match.group(1))


def test_boot_index_names_naberius_gold_in_the_data_array():
    palettes = gradient_palettes()
    index = boot_palette_index()

    assert index < len(palettes), (
        f"K1_BOOT_PALETTE_INDEX={index} is out of range for "
        f"gGradientPalettes[] ({len(palettes)} entries)"
    )
    assert palettes[index] == EXPECTED_PALETTE, (
        f"K1_BOOT_PALETTE_INDEX={index} now selects {palettes[index]!r}, not "
        f"{EXPECTED_PALETTE!r}. The palette array was reordered -- update "
        f"K1_BOOT_PALETTE_INDEX to {palettes.index(EXPECTED_PALETTE)} "
        if EXPECTED_PALETTE in palettes
        else f"K1_BOOT_PALETTE_INDEX={index} does not select {EXPECTED_PALETTE!r} "
        "and that palette no longer exists at all."
    )


def test_name_table_and_data_array_stay_in_lockstep():
    """The index is only meaningful because both arrays share one ordering."""
    palettes = gradient_palettes()
    names = palette_names()

    assert len(palettes) == len(names), (
        f"gGradientPalettes[] has {len(palettes)} entries but paletteNames[] has "
        f"{len(names)}; the index-to-name mapping is no longer trustworthy"
    )
    assert palettes == names, (
        "gGradientPalettes[] and paletteNames[] disagree at: "
        + ", ".join(
            f"index {i}: data={d!r} name={n!r}"
            for i, (d, n) in enumerate(zip(palettes, names))
            if d != n
        )
    )


def test_compiled_defaults_select_the_boot_palette_on_both_channels():
    config_defaults = read(GLOBALS_CONFIG_CPP)
    assert re.search(
        r"K1_BOOT_PALETTE_INDEX,\s*//\s*PALETTE_INDEX", config_defaults
    ), "CONFIG_DEFAULTS.PALETTE_INDEX must be K1_BOOT_PALETTE_INDEX"
    assert re.search(
        r"true,\s*//\s*PALETTE_MODE_ENABLED", config_defaults
    ), "CONFIG_DEFAULTS.PALETTE_MODE_ENABLED must default to true"

    globals_h = read(GLOBALS_H)
    assert re.search(
        r"SECONDARY_PALETTE_INDEX\s*=\s*K1_BOOT_PALETTE_INDEX", globals_h
    ), "SECONDARY_PALETTE_INDEX must default to K1_BOOT_PALETTE_INDEX"
    assert re.search(
        r"SECONDARY_PALETTE_MODE_ENABLED\s*=\s*true", globals_h
    ), "SECONDARY_PALETTE_MODE_ENABLED must default to true"


def test_boot_lock_is_applied_after_the_persisted_config_is_adopted():
    """Defaults alone are not enough -- the persisted blob would override them."""
    source = read(BRIDGE_FS_H)

    assert "void k1_apply_boot_palette_lock()" in source, (
        "k1_apply_boot_palette_lock() is missing; without it a device with a saved "
        "config boots its stored palette instead of the locked one"
    )

    lock_body = re.search(
        r"k1_apply_boot_palette_lock\(\)\s*\{(.*?)\}", source, re.S
    )
    assert lock_body, "could not read the body of k1_apply_boot_palette_lock()"
    body = lock_body.group(1)
    for field in (
        "CONFIG.PALETTE_INDEX",
        "CONFIG.PALETTE_MODE_ENABLED",
        "SECONDARY_PALETTE_INDEX",
        "SECONDARY_PALETTE_MODE_ENABLED",
    ):
        assert field in body, f"boot palette lock does not set {field}"

    load_config = re.search(r"void load_config\(\)\s*\{(.*?)\n\}", source, re.S)
    assert load_config, "could not isolate load_config()"
    load_body = load_config.group(1)

    calls = load_body.count("k1_apply_boot_palette_lock();")
    returns = load_body.count("return;")
    assert calls >= returns + 1, (
        f"load_config() has {returns} early return(s) and {calls} boot-lock call(s). "
        "Every exit path -- safe mode, missing config file, and the normal path -- "
        "must apply the lock, or some boot routes come up on the wrong palette."
    )

    # The lock must run AFTER the blob is copied into CONFIG, otherwise the
    # persisted palette overwrites it.
    last_memcpy = load_body.rfind("memcpy(&CONFIG")
    last_lock = load_body.rfind("k1_apply_boot_palette_lock();")
    assert last_lock > last_memcpy, (
        "k1_apply_boot_palette_lock() must be called after the persisted config is "
        "copied into CONFIG, or the stored palette wins"
    )
