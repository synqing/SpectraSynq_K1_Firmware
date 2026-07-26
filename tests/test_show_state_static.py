"""Static + host round-trip contract for Shift+S show-state persistence.

Covers k1_show_state.{h,cpp}: LittleFS /SHOW_STATE_V1.BIN, 'S' immediate hotkey,
:save_show / :show_state typed commands, and boot restore after load_config().
No device flash required.
"""

from __future__ import annotations

import binascii
import re
import struct
import unittest
from pathlib import Path

from _fwpath import FwDir, read_serial_menu_surface, read_serial_dispatch_surface, typed_command_registered


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
SHOW_H = FW / "control" / "k1_show_state.h"
SHOW_CPP = FW / "control" / "k1_show_state.cpp"
QUEUE_H = FW / "control" / "k1_effect_queue.h"
BRIDGE = FW / "persistence" / "bridge_fs.h"
TYPED_DEF = FW / "serial" / "serial_typed_cmd_table.def"


def _crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def pack_preset(
    *,
    lightshow_mode: int = 3,
    mirror: bool = True,
    photons: float = 0.5,
    chroma: float = 0.6,
    mood: float = 0.7,
    saturation: float = 0.8,
    prism_count: float = 2.0,
    incandescent_filter: float = 0.1,
    incandescent_mode: bool = False,
    base_coat: bool = True,
    reverse_order: bool = False,
    auto_color_shift: bool = True,
    base_coat_intensity: float = 0.25,
    palette_index: int = 4,
    palette_mode_enabled: bool = True,
) -> bytes:
    parts = [
        struct.pack("<B", lightshow_mode & 0xFF),
        struct.pack("<B", 1 if mirror else 0),
        struct.pack("<f", photons),
        struct.pack("<f", chroma),
        struct.pack("<f", mood),
        struct.pack("<f", saturation),
        struct.pack("<f", prism_count),
        struct.pack("<f", incandescent_filter),
        struct.pack("<B", 1 if incandescent_mode else 0),
        struct.pack("<B", 1 if base_coat else 0),
        struct.pack("<B", 1 if reverse_order else 0),
        struct.pack("<B", 1 if auto_color_shift else 0),
        struct.pack("<f", base_coat_intensity),
        struct.pack("<B", palette_index & 0xFF),
        struct.pack("<B", 1 if palette_mode_enabled else 0),
    ]
    return b"".join(parts)


def unpack_preset(data: bytes, offset: int = 0):
    o = offset
    lightshow_mode = data[o]
    o += 1
    mirror = data[o]
    o += 1
    photons, chroma, mood, saturation, prism, incand_f = struct.unpack_from("<ffffff", data, o)
    o += 24
    incand_mode = data[o]
    o += 1
    base_coat = data[o]
    o += 1
    reverse = data[o]
    o += 1
    auto_shift = data[o]
    o += 1
    (base_intensity,) = struct.unpack_from("<f", data, o)
    o += 4
    palette_index = data[o]
    o += 1
    palette_mode = data[o]
    o += 1
    return {
        "lightshow_mode": lightshow_mode,
        "mirror": mirror,
        "photons": photons,
        "chroma": chroma,
        "mood": mood,
        "saturation": saturation,
        "prism_count": prism,
        "incandescent_filter": incand_f,
        "incandescent_mode": incand_mode,
        "base_coat": base_coat,
        "reverse_order": reverse,
        "auto_color_shift": auto_shift,
        "base_coat_intensity": base_intensity,
        "palette_index": palette_index,
        "palette_mode_enabled": palette_mode,
    }, o


def pack_edge(
    *,
    enabled: bool = True,
    mode: int = 2,
    strength: float = 0.75,
    spread: int = 30,
    rotation: int = 1,
    spatial: bool = False,
    dual: int = 0,
) -> bytes:
    return b"".join(
        [
            struct.pack("<B", 1 if enabled else 0),
            struct.pack("<B", mode & 0xFF),
            struct.pack("<f", strength),
            struct.pack("<B", spread & 0xFF),
            struct.pack("<B", rotation & 0xFF),
            struct.pack("<B", 1 if spatial else 0),
            struct.pack("<B", dual & 0xFF),
        ]
    )


def encode_show_state(primary: bytes, secondary: bytes, edge: bytes, enable_secondary: bool) -> bytes:
    magic = struct.pack("<I", 0x53534253)  # 'SBSS'
    version = struct.pack("<H", 1)
    reserved = struct.pack("<H", 0)
    payload = primary + secondary + edge + struct.pack("<B", 1 if enable_secondary else 0)
    crc = struct.pack("<I", _crc32(payload))
    return magic + version + reserved + payload + crc


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b(?:bool|void|size_t|K1ShowState)\s+{name}\s*\([^)]*\)\s*\{{", source)
    assert match is not None, f"{name}() must exist"
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth:
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"{name}() body must be balanced"
    return source[start : index - 1]


class ShowStateStaticContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.menu = read_serial_menu_surface(FW)
        cls.dispatch = read_serial_dispatch_surface(FW)
        cls.show_h = SHOW_H.read_text()
        cls.show_cpp = SHOW_CPP.read_text()
        cls.bridge = BRIDGE.read_text()
        cls.queue_h = QUEUE_H.read_text()
        cls.typed_def = TYPED_DEF.read_text()

    def test_file_magic_version_constants(self):
        self.assertIn('K1_SHOW_STATE_FILE "/SHOW_STATE_V1.BIN"', self.show_h)
        self.assertIn("K1_SHOW_STATE_MAGIC 0x53534253UL", self.show_h)
        self.assertIn("K1_SHOW_STATE_VERSION 1U", self.show_h)

    def test_hotkey_s_is_immediate_and_saves(self):
        immediate = function_body(self.menu, "serial_hotkey_is_immediate")
        handler = function_body(self.menu, "serial_handle_hotkey")
        self.assertIn("case 'S':", immediate)
        self.assertIn("case 's':", immediate)
        self.assertIn("k1_show_state_save()", handler)
        self.assertIn("SHOW_STATE_SAVED", handler)
        # lowercase 's' remains VP stream
        s_case = re.search(r"case 's':(?P<body>.*?)case 'S':", handler, re.S)
        self.assertIsNotNone(s_case, "'s' must precede 'S' and stay VP stream")
        self.assertIn("VP_STREAM_ENABLED", s_case.group("body"))

    def test_help_mentions_save_show_state(self):
        help_body = function_body(self.menu, "serial_print_hotkey_help")
        self.assertIn("save show state", help_body.lower())
        self.assertIn("primary+secondary+edge", help_body)

    def test_typed_commands_registered(self):
        self.assertIn('SERIAL_TYPED_CMD("save_show"', self.typed_def)
        self.assertIn('SERIAL_TYPED_CMD("show_state"', self.typed_def)
        self.assertTrue(typed_command_registered(self.dispatch, "save_show"))
        self.assertTrue(typed_command_registered(self.dispatch, "show_state"))

    def test_boot_calls_load_after_load_config(self):
        init = function_body(self.bridge, "init_fs")
        self.assertIn("load_config()", init)
        self.assertIn("k1_show_state_load()", init)
        self.assertLess(init.index("load_config()"), init.index("k1_show_state_load()"))

    def test_save_calls_immediate_save_config(self):
        save = function_body(self.show_cpp, "k1_show_state_save")
        self.assertIn("save_config()", save)
        self.assertNotIn("save_config_delayed()", save)

    def test_apply_uses_fields_without_delayed_save(self):
        apply = function_body(self.show_cpp, "k1_show_state_apply")
        self.assertIn("k1_queue_apply_fields(false", apply)
        self.assertIn("k1_queue_apply_fields(true", apply)
        self.assertIn("k1_edgemixer_set_config", apply)
        self.assertIn("ENABLE_SECONDARY_LEDS", apply)
        self.assertNotIn("save_config_delayed", apply)
        self.assertIn("void k1_queue_apply_fields", self.queue_h)

    def test_secondary_persistence_only_via_show_state_module(self):
        # Policy: secondary hotkey path must not gain accidental CONFIG bleed;
        # only show-state writes SECONDARY_* into the blob / applies them on load.
        self.assertIn("k1_queue_capture_live(true)", self.show_cpp)
        self.assertIn("k1_queue_apply_fields(true", self.show_cpp)
        # apply_preset_live still skips delayed save for secondary.
        queue_cpp = (FW / "control" / "k1_effect_queue.cpp").read_text()
        live = function_body(queue_cpp, "apply_preset_live")
        self.assertIn("if (!secondary)", live)
        self.assertIn("save_config_delayed()", live)


class ShowStateHostRoundTripTest(unittest.TestCase):
    def test_encode_decode_round_trip(self):
        primary = pack_preset(lightshow_mode=5, palette_index=7, photons=0.42)
        secondary = pack_preset(lightshow_mode=11, palette_index=2, photons=0.18, mirror=False)
        edge = pack_edge(mode=3, strength=0.55, spread=25, dual=1)
        blob = encode_show_state(primary, secondary, edge, enable_secondary=True)

        magic, version, reserved = struct.unpack_from("<IHH", blob, 0)
        self.assertEqual(magic, 0x53534253)
        self.assertEqual(version, 1)
        self.assertEqual(reserved, 0)

        payload = blob[8:-4]
        crc = struct.unpack_from("<I", blob, len(blob) - 4)[0]
        self.assertEqual(crc, _crc32(payload))

        pri, o = unpack_preset(payload, 0)
        sec, o = unpack_preset(payload, o)
        enabled, mode = payload[o], payload[o + 1]
        (strength,) = struct.unpack_from("<f", payload, o + 2)
        spread, rotation, spatial, dual = payload[o + 6 : o + 10]
        enable_sec = payload[o + 10]

        self.assertEqual(pri["lightshow_mode"], 5)
        self.assertAlmostEqual(pri["photons"], 0.42, places=5)
        self.assertEqual(sec["lightshow_mode"], 11)
        self.assertEqual(sec["mirror"], 0)
        self.assertEqual(enabled, 1)
        self.assertEqual(mode, 3)
        self.assertAlmostEqual(strength, 0.55, places=5)
        self.assertEqual(spread, 25)
        self.assertEqual(dual, 1)
        self.assertEqual(enable_sec, 1)

    def test_corrupt_crc_rejected_by_contract(self):
        primary = pack_preset()
        secondary = pack_preset(lightshow_mode=1)
        edge = pack_edge()
        blob = bytearray(encode_show_state(primary, secondary, edge, True))
        blob[-1] ^= 0xFF
        payload = bytes(blob[8:-4])
        crc = struct.unpack_from("<I", blob, len(blob) - 4)[0]
        self.assertNotEqual(crc, _crc32(payload))


if __name__ == "__main__":
    unittest.main()
