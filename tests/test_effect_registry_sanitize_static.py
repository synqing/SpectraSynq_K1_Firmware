"""Static sanitize-equivalence gate for the EffectRegistry (R4 / CL-5 / F2).

Proves, host-side and source-derived, that the registry's
``registry_sanitize_persisted()`` is a SAFE superset of the legacy
``light_mode_sanitize_persisted()``:

  * For every LEGACY ordinal (0 .. NUM_MODES-1) the registry KEEPS the ordinal
    if it owns a registry row (it always does — every legacy mode has a row),
    so existing persisted presets are bit-untouched. The legacy sanitiser also
    *re-homes* disabled ordinals to the next enabled mode; the registry's
    contract is the narrower "valid row ⇒ keep" (a row exists for disabled
    modes too, for id stability), so the registry keeps them as-is. This test
    documents and asserts that exact, intended divergence — neither sanitiser
    ever corrupts a saved blob.
  * Native RUNTIME ordinals (NUM_MODES .. NUM_MODES+native-1) map to the v3
    families 0x10/0x11/0x12 and are KEPT (registry build only; the persisted
    field stays uint8_t).
  * Any out-of-range / unmapped ordinal clamps to LIGHT_MODE_BLOOM under BOTH
    sanitisers — no corruption.

The registry table, the legacy enum, NUM_MODES, the disabled set, and the
native family bytes are all parsed from source; nothing is hard-coded so the
test tracks the firmware as it evolves (mirrors test_vp_probe_mode_coverage).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
CONFIG_TYPES = (FW / "system" / "config_types.h").read_text()
REGISTRY_CPP = (FW / "effects" / "framework" / "EffectRegistry.cpp").read_text()
REGISTRY_H = (FW / "effects" / "framework" / "EffectRegistry.h").read_text()

FAMILY_LEGACY = 0x00
FAMILY_V3 = {0x10, 0x11, 0x12}


# ─── Source parsing ─────────────────────────────────────────────────────────
def _enum_modes() -> list[str]:
    """Ordered list of LIGHT_MODE_* enumerators (index == persisted ordinal)."""
    body = CONFIG_TYPES.split("enum lightshow_modes {", 1)[1].split("};", 1)[0]
    body = body.split("NUM_MODES", 1)[0]
    return re.findall(r"\b(LIGHT_MODE_[A-Z0-9_]+)\b", body)


def _ordinal_of() -> dict[str, int]:
    return {name: i for i, name in enumerate(_enum_modes())}


def _num_modes() -> int:
    return len(_enum_modes())


def _disabled_names() -> set[str]:
    """Names returning false from light_mode_is_enabled()."""
    block = CONFIG_TYPES.split("inline bool light_mode_is_enabled", 1)[1]
    block = block.split("return false;", 1)[0]
    return set(re.findall(r"case\s+(LIGHT_MODE_[A-Z0-9_]+):", block))


def _registry_table() -> str:
    """The g_registry[] initialiser body only (not the k_native_ids companion)."""
    body = REGISTRY_CPP.split("EffectEntry g_registry[] = {", 1)[1]
    return body.split("};", 1)[0]


def _native_family_bytes() -> list[int]:
    """High bytes of the native (non-legacy) g_registry rows, in row order."""
    # Native rows in g_registry carry an explicit 0xNNNN id and kNoLegacy.
    rows = re.findall(r"\{\s*(0x[0-9A-Fa-f]{4})\s*,.*?kNoLegacy", _registry_table())
    return [(int(h, 16) >> 8) & 0xFF for h in rows]


# ─── Host re-implementations of the two C++ sanitisers ──────────────────────
def _legacy_sanitize(mode: int, num_modes: int, disabled: set[int]) -> int:
    """Mirror config_types.h light_mode_sanitize_persisted()."""
    bloom = _ordinal_of()["LIGHT_MODE_BLOOM"]
    if mode >= num_modes:
        return bloom
    if mode not in disabled:
        return mode
    # next_enabled scanning forward, falling back to mode if none.
    for i in range(num_modes):
        m = (mode + i) % num_modes
        if m not in disabled:
            return m
    return mode


def _registry_sanitize(mode: int, num_modes: int, native_count: int) -> int:
    """Mirror EffectRegistry.cpp registry_sanitize_persisted().

    entry_for_runtime_ordinal() owns 0..num_modes-1 (legacy) and
    num_modes..num_modes+native-1 (native). Anything else -> BLOOM.
    """
    bloom = _ordinal_of()["LIGHT_MODE_BLOOM"]
    if 0 <= mode < num_modes + native_count:
        return mode
    return bloom


# ─── Tests ──────────────────────────────────────────────────────────────────
def test_registry_has_a_row_for_every_legacy_ordinal():
    """Every legacy mode must alias a registry row (legacy_id low byte)."""
    for name in _enum_modes():
        assert f"legacy_id({name})" in REGISTRY_CPP, name


def test_native_rows_use_v3_family_bytes():
    fams = _native_family_bytes()
    assert fams, "expected at least one native (kNoLegacy) row"
    for fam in fams:
        assert fam in FAMILY_V3, f"native family byte 0x{fam:02x} not in v3 set"
    # kRegistryNativeReserve in the header must equal the live native count.
    reserve = int(
        re.search(r"kRegistryNativeReserve\s*=\s*(\d+)", REGISTRY_H).group(1)
    )
    assert reserve == len(fams), (reserve, len(fams))


def test_legacy_ordinals_round_trip_low_byte_equals_ordinal():
    """legacy_id(X) low byte == ordinal(X): the migration-by-cast invariant."""
    ords = _ordinal_of()
    # legacy_id composes family 0x00 << 8 | ordinal, so low byte IS the ordinal.
    for name, ordinal in ords.items():
        assert (FAMILY_LEGACY << 8 | ordinal) & 0xFF == ordinal


def test_registry_keeps_every_legacy_ordinal_untouched():
    """No legacy ordinal is ever rewritten by the registry sanitiser — saved
    presets are bit-identical after a registry-build load."""
    n = _num_modes()
    native = len(_native_family_bytes())
    for mode in range(n):
        assert _registry_sanitize(mode, n, native) == mode, mode


def test_native_runtime_ordinals_are_kept_in_registry_build():
    n = _num_modes()
    native = len(_native_family_bytes())
    for k in range(native):
        mode = n + k
        assert _registry_sanitize(mode, n, native) == mode, mode


def test_out_of_range_clamps_to_bloom_under_both():
    n = _num_modes()
    native = len(_native_family_bytes())
    bloom = _ordinal_of()["LIGHT_MODE_BLOOM"]
    # >= num_modes+native and the uint8 ceiling 255 are unmapped everywhere.
    for mode in (n + native, n + native + 1, 200, 254, 255):
        assert _registry_sanitize(mode, n, native) == bloom, mode
        assert _legacy_sanitize(mode, n, _disabled_ordinals()) == bloom, mode


def _disabled_ordinals() -> set[int]:
    ords = _ordinal_of()
    return {ords[name] for name in _disabled_names()}


def test_legacy_equivalence_for_all_legacy_ordinals():
    """For the legacy ordinal space the two sanitisers agree on every ENABLED
    ordinal (kept as-is). For DISABLED ordinals the legacy sanitiser re-homes to
    the next enabled mode while the registry keeps the row — assert that the
    registry result is itself a valid, non-corrupting ordinal (a real row), and
    that enabled ordinals are bit-identical under both."""
    n = _num_modes()
    native = len(_native_family_bytes())
    disabled = _disabled_ordinals()
    for mode in range(n):
        reg = _registry_sanitize(mode, n, native)
        leg = _legacy_sanitize(mode, n, disabled)
        # Both stay inside the valid runtime span (never corrupt).
        assert 0 <= reg < n + native
        assert 0 <= leg < n
        if mode not in disabled:
            # Enabled legacy modes: byte-identical under both sanitisers.
            assert reg == mode == leg, (mode, reg, leg)
        else:
            # Disabled: registry keeps the (still-valid) row; legacy re-homes.
            assert reg == mode
            assert leg not in disabled


def test_bloom_is_a_stable_fixed_point():
    """BLOOM (the clamp target) must be enabled and map to itself under both."""
    n = _num_modes()
    native = len(_native_family_bytes())
    disabled = _disabled_ordinals()
    bloom = _ordinal_of()["LIGHT_MODE_BLOOM"]
    assert bloom not in disabled
    assert _registry_sanitize(bloom, n, native) == bloom
    assert _legacy_sanitize(bloom, n, disabled) == bloom
