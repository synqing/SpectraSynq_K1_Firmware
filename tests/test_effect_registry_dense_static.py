"""Static gate for the EffectRegistry DENSE navigation index (R5).

The persisted runtime-ordinal space has HOLES: disabled legacy modes keep their
ordinal for NVS id-stability but are unselectable, so a user stepping through
modes sees gaps (… 9, 11, 12 …) and the natives sit beyond NUM_MODES. The dense
index is the gap-free menu position over ENABLED runtime ordinals only
(legacy-enabled in enum order, then the natives), so the user-facing numbering
is 0 .. dense_count-1 with no holes. It is a PRESENTATION layer: the persisted
field stays the real uint8 ordinal — presets are never renumbered.

This test mirrors the three C++ helpers from source (registry_dense_count /
registry_dense_to_ordinal / registry_ordinal_to_dense) and proves the mapping is
gap-free, monotonic, round-trips for enabled ordinals, reaches every native, and
re-homes disabled ordinals to the next enabled effect. It also asserts the
helpers exist and are wired into the serial surfaces. Enum, disabled set, and
native count are parsed from source (mirrors test_effect_registry_sanitize).
"""

from __future__ import annotations

import re
from pathlib import Path
from _fwpath import FwDir, read_serial_menu_surface

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
FW_DIR = FwDir(FW)
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text()
REGISTRY_CPP = (FW / "effects" / "framework" / "EffectRegistry.cpp").read_text()
REGISTRY_H = (FW / "effects" / "framework" / "EffectRegistry.h").read_text()
SERIAL_MENU = read_serial_menu_surface(FW_DIR)


# ─── Source parsing (shared shape with the sanitize gate) ───────────────────
def _enum_modes() -> list[str]:
    body = CONFIG_TYPES.split("enum lightshow_modes {", 1)[1].split("};", 1)[0]
    body = body.split("NUM_MODES", 1)[0]
    return re.findall(r"\b(LIGHT_MODE_[A-Z0-9_]+)\b", body)


def _num_modes() -> int:
    return len(_enum_modes())


def _disabled_ordinals() -> set[int]:
    block = CONFIG_TYPES.split("inline bool light_mode_is_enabled", 1)[1]
    block = block.split("return false;", 1)[0]
    names = set(re.findall(r"case\s+(LIGHT_MODE_[A-Z0-9_]+):", block))
    ords = {name: i for i, name in enumerate(_enum_modes())}
    return {ords[n] for n in names}


def _native_count() -> int:
    table = REGISTRY_CPP.split("EffectEntry g_registry[] = {", 1)[1].split("};", 1)[0]
    return len(re.findall(r"\{\s*0x[0-9A-Fa-f]{4}\s*,.*?kNoLegacy", table))


def _runtime_enabled(ordinal: int, num_modes: int, native: int, disabled: set[int]) -> bool:
    """registry_mode_is_enabled(): legacy ords gated by the disabled set, native
    runtime ordinals (>= num_modes) always enabled (their rows are enabled)."""
    if ordinal < num_modes:
        return ordinal not in disabled
    return ordinal < num_modes + native


# ─── Host re-implementation of the three C++ dense helpers ──────────────────
def _enabled_ordinals() -> list[int]:
    n, native, dis = _num_modes(), _native_count(), _disabled_ordinals()
    span = n + native
    return [o for o in range(span) if _runtime_enabled(o, n, native, dis)]


def _dense_count() -> int:
    return len(_enabled_ordinals())


def _dense_to_ordinal(idx: int) -> int:
    enabled = _enabled_ordinals()
    bloom = _enum_modes().index("LIGHT_MODE_BLOOM")
    return enabled[idx] if 0 <= idx < len(enabled) else bloom


def _ordinal_to_dense(ordinal: int) -> int:
    n, native, dis = _num_modes(), _native_count(), _disabled_ordinals()
    span = n + native
    dense = 0
    for o in range(span):
        if o == ordinal:
            return dense
        if _runtime_enabled(o, n, native, dis):
            dense += 1
    return dense


# ─── Tests ──────────────────────────────────────────────────────────────────
def test_helpers_declared_and_defined():
    for sym in ("registry_dense_count", "registry_dense_to_ordinal", "registry_ordinal_to_dense"):
        assert sym in REGISTRY_H, f"{sym} not declared in EffectRegistry.h"
        assert f"{sym}(" in REGISTRY_CPP, f"{sym} not defined in EffectRegistry.cpp"


def test_serial_surfaces_use_the_dense_layer():
    """The user-facing serial surfaces map through the dense helpers under the
    registry flag (input via dense_to_ordinal, display via ordinal_to_dense)."""
    assert "registry_dense_to_ordinal" in SERIAL_MENU      # set_mode / secondary_mode / get_mode_name
    assert "registry_ordinal_to_dense" in SERIAL_MENU      # mode-line display / get_mode
    assert "registry_dense_count" in SERIAL_MENU           # get_num_modes + input bounds


def test_dense_count_is_enabled_legacy_plus_natives():
    n, native, dis = _num_modes(), _native_count(), _disabled_ordinals()
    expected = (n - len(dis)) + native
    assert _dense_count() == expected


def test_dense_index_is_gap_free_and_monotonic():
    ords = [_dense_to_ordinal(i) for i in range(_dense_count())]
    assert ords == sorted(ords), "dense order must be ascending in ordinal"
    assert len(ords) == len(set(ords)), "no ordinal repeated"
    # Every produced ordinal is a real, enabled runtime ordinal (never a hole).
    dis = _disabled_ordinals()
    for o in ords:
        assert o not in dis, f"dense index resolved to a DISABLED ordinal {o}"


def test_enabled_ordinals_round_trip():
    for o in _enabled_ordinals():
        assert _dense_to_ordinal(_ordinal_to_dense(o)) == o, o


def test_every_native_is_reachable_at_the_tail():
    n, native = _num_modes(), _native_count()
    count = _dense_count()
    # Natives occupy the final `native` dense slots, in ordinal order.
    for k in range(native):
        dense_idx = count - native + k
        assert _dense_to_ordinal(dense_idx) == n + k, (dense_idx, n + k)


def test_disabled_ordinal_maps_to_next_enabled_dense():
    """A disabled ordinal has no slot of its own; it displays as the dense index
    of the next enabled effect (never a negative / phantom number)."""
    enabled = _enabled_ordinals()
    for o in _disabled_ordinals():
        dense = _ordinal_to_dense(o)
        assert 0 <= dense <= len(enabled)
        # The ordinal at that dense slot is the first enabled ordinal > o.
        nxt = next((e for e in enabled if e > o), None)
        if nxt is not None:
            assert _dense_to_ordinal(dense) == nxt, (o, dense, nxt)


def test_first_dense_is_first_enabled_mode():
    """Sanity anchor: dense 0 is the lowest enabled ordinal (BLOOM=3 today, but
    derived, not hardcoded)."""
    assert _dense_to_ordinal(0) == _enabled_ordinals()[0]
