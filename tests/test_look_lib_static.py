"""Static isolation + ABI locks for K1_LOOK_LIB_V1 (Phase A)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INI = (ROOT / "platformio.ini").read_text(encoding="utf-8")
EMIT = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_lever2_emit.h"
).read_text(encoding="utf-8")
LOOK_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_look.h"
CODEC = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "persistence" / "bridge_fs_config_codec.h"
).read_text(encoding="utf-8")
CONFIG_TYPES = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
).read_text(encoding="utf-8")
AUDIO_DIR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"
LED = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h"
).read_text(encoding="utf-8")

FLAG = "K1_LOOK_LIB_V1"
# led150 is the WS2812 sibling owner later; it must never inherit RPL look/Lever-2.
BANNED_ENVS = (
    "k1_hardware",
    "k1_bench_im69d",
    "k1_bench_reference",
    "k1_bench_im69d_led150",
)
LOCKED_TYPES = {
    "IDENTITY": 0,
    "SHARED_1D_256": 1,
    "RGB_1D_256": 2,
    "MATRIX_3X4": 3,
    "CUBE_17": 4,
    "CUBE_33": 5,
    "SHAPER_CUBE": 6,
}


def _sections():
    out = {}
    for m in re.finditer(r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", INI, re.M | re.S):
        out[m.group(1)] = m.group(2)
    return out


def _effective_flags(env, sections, seen=None):
    seen = seen or set()
    if env in seen or env not in sections:
        return set()
    seen.add(env)
    body = sections[env]
    uncommented = "\n".join(
        l for l in body.splitlines() if not l.lstrip().startswith(("#", ";"))
    )
    flags = set(re.findall(r"-D([A-Za-z0-9_]+)", uncommented))
    ext = re.search(r"^extends\s*=\s*env:([^\s]+)", body, re.M)
    if ext:
        flags |= _effective_flags(ext.group(1), sections, seen)
    return flags


def _fn_body(src: str, name: str) -> str:
    m = re.search(rf"static inline \w+ {name}\s*\(", src)
    assert m, f"{name} not found"
    brace = src.index("{", m.start())
    depth = 0
    for i, c in enumerate(src[brace:], brace):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[brace : i + 1]
    raise AssertionError(f"unbalanced braces for {name}")


def test_look_lib_flag_rpl_only():
    sections = _sections()
    assert FLAG in _effective_flags("k1_main_rpl_im69d", sections)
    rpl = sections["k1_main_rpl_im69d"]
    uncommented = "\n".join(
        l for l in rpl.splitlines() if not l.lstrip().startswith(("#", ";"))
    )
    assert "-DK1_LOOK_LIB_V1" in uncommented
    assert "-DK1_WS2816_DEGAMMA_V1" not in uncommented
    for env in BANNED_ENVS:
        assert FLAG not in _effective_flags(env, sections), env
    led150 = _effective_flags("k1_bench_im69d_led150", sections)
    assert FLAG not in led150
    assert "K1_WS2816_LEVER2_V1" not in led150
    assert "K1_WS2816_DEGAMMA_V1" not in led150
    assert "K1_LOOK_LIB_WS2812_V1" in led150
    for env in ("k1_hardware", "k1_bench_im69d", "k1_bench_reference", "k1_main_rpl_im69d"):
        assert "K1_LOOK_LIB_WS2812_V1" not in _effective_flags(env, sections), env


def test_packer_has_no_degamma_ifdef_on_convert():
    assert "#ifdef K1_WS2816_DEGAMMA_V1" not in EMIT
    convert = _fn_body(EMIT, "k1_lever2_sq_to_u16")
    assert "k1_ws2816_degamma_u16" not in convert


def test_look_apply_called_from_pack_frame_after_limiter_before_pack():
    pack = _fn_body(EMIT, "k1_lever2_pack_frame")
    assert "k1_look_apply_u16" in pack
    apply_at = pack.index("k1_look_apply_u16")
    pack_at = pack.index("ws2816_pack_pixel")
    assert apply_at < pack_at
    # Identity-budget path still applies look (not only the tight-budget loop).
    assert pack.count("k1_look_apply_u16") >= 2


def test_pack_frame_snapshots_slot_once():
    pack = _fn_body(EMIT, "k1_lever2_pack_frame")
    assert "look_slot" in pack
    assert pack.count("k1_look_slot") <= 1 or "const uint8_t look_slot" in pack


def test_no_look_include_from_core0_audio():
    hits = []
    for path in AUDIO_DIR.rglob("*"):
        if path.suffix not in {".h", ".cpp", ".c"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "k1_look" in text:
            hits.append(str(path.relative_to(ROOT)))
    assert hits == []


def test_type_enum_values_locked():
    src = LOOK_H.read_text(encoding="utf-8")
    for name, value in LOCKED_TYPES.items():
        assert re.search(rf"K1_LOOK_{name}\s*=\s*{value}\b", src), name


def test_config_look_fields_at_end():
    m = re.search(r"struct conf \{(.*?)\};", CONFIG_TYPES, flags=re.S)
    assert m
    tail = m.group(1).strip().splitlines()[-6:]
    joined = "\n".join(tail)
    assert "uint8_t LOOK;" in joined
    assert "uint8_t SECONDARY_LOOK;" in joined


def test_pre_look_sizeof_recorded_for_migrate():
    assert "CONFIG_BLOB_PRE_LOOK_CONF_SIZE 112" in CODEC
    assert "CONFIG_BLOB_VERSION 2U" in CODEC or "CONFIG_BLOB_VERSION 2" in CODEC


def test_dump_and_help_are_flag_gated():
    menu = (
        ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"
    ).read_text(encoding="utf-8")
    assert "LOOK: slot=" in menu
    assert "K1_LOOK_LIB_V1" in menu
    assert "K1_LOOK_LIB_WS2812_V1" in menu
    assert "serial_look_cycle_hotkey" in menu


def test_both_din_pack_sites_share_emit_header():
    assert LED.count("k1_lever2_pack_frame(") >= 2
    assert "leds_scaled_secondary" in LED
    assert "ws2816_wire_secondary" in LED


def test_slot0_is_identity_and_proof_cube_is_slot8():
    src = LOOK_H.read_text(encoding="utf-8")
    # Compiled table starts identity at 0; slot 8 stays EMPTY until boot fills.
    assert "{K1_LOOK_IDENTITY, nullptr}" in src
    assert "k1_look_table[16]" in src
    assert "k1_look_install_proof_cube" in src
    assert "k1_look_xfade_u16" in src
    boot = _fn_body(src, "k1_look_boot_from_config")
    assert "k1_look_install_proof_cube" in boot
    install_at = boot.index("k1_look_install_proof_cube")
    pub_at = boot.index("k1_look_publish")
    assert install_at < pub_at
    table_m = re.search(r"k1_look_table\[16\] = \{?(.*?)\};", src, flags=re.S)
    assert table_m
    rows = [ln.strip() for ln in table_m.group(1).splitlines() if ln.strip().startswith("{")]
    assert rows[0].startswith("{K1_LOOK_IDENTITY")
    assert rows[8].startswith("{K1_LOOK_EMPTY")


def test_look_cycle_is_a_hotkey():
    menu = (
        ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"
    ).read_text(encoding="utf-8")
    assert "serial_look_cycle_hotkey" in menu
    assert "z cycle look" in menu
    assert "case 'z':" in menu


def test_tab5_reuses_typed_look_command():
    typed = (
        ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_typed_cmd_table.def"
    ).read_text(encoding="utf-8")
    assert 'SERIAL_TYPED_CMD("look"' in typed
    assert 'SERIAL_TYPED_CMD("palette_index"' in typed
    assert "K1_LOOK_LIB_V1" in typed

