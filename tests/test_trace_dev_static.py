import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
FIRMWARE = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
INO = FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino"
SERIAL_MENU = FIRMWARE / "serial_menu.h"
SERIAL_TABLE = FIRMWARE / "serial_cmd_table.def"
K1_TRACE = FIRMWARE / "k1_trace.h"


def read(path):
    return path.read_text(encoding="utf-8")


def strip_ini_comments(text):
    return "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith(";")
    )


def platformio_sections():
    text = read(PLATFORMIO)
    matches = list(re.finditer(r"^\[(?P<name>[^\]]+)\]\s*$", text, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("name")] = text[start:end]
    return sections


class TraceDevStaticTest(unittest.TestCase):
    def test_trace_dev_env_is_non_shippable_mabutrace_lane(self):
        sections = platformio_sections()
        self.assertIn("env:k1_hardware_trace_dev", sections)
        trace_dev = strip_ini_comments(sections["env:k1_hardware_trace_dev"]).lower()
        raw = sections["env:k1_hardware_trace_dev"].lower()

        self.assertIn("non-shippable", raw)
        self.assertIn("extends = env:k1_hardware_harness", trace_dev)
        self.assertIn("-dfeature_mabutrace=1", trace_dev)
        self.assertIn("-dfeature_trace_render=1", trace_dev)
        self.assertRegex(trace_dev, r"mabuware/mabutrace@[\^~]?\d+\.\d+\.\d+")

    def test_sb_trace_wrapper_owns_mabutrace_and_noop_macros(self):
        text = read(K1_TRACE)
        self.assertIn("#pragma once", text)
        self.assertRegex(text, r"#ifndef\s+FEATURE_MABUTRACE")
        self.assertRegex(text, r"#define\s+FEATURE_MABUTRACE\s+0")
        self.assertIn("#if FEATURE_MABUTRACE", text)
        self.assertIn("#include <mabutrace.h>", text)
        for name in (
            "K1_TRACE_SCOPE",
            "K1_TRACE_COUNTER",
            "K1_TRACE_INSTANT",
            "K1_TRACE_INIT",
            "K1_TRACE_DUMP_JSON",
        ):
            self.assertIn(name, text)
        self.assertRegex(text, r"#define\s+K1_TRACE_SCOPE\(name\)\s+do\s+\{\s*\}\s+while\(0\)")
        self.assertRegex(text, r"#define\s+K1_TRACE_COUNTER\(name,\s*value\).*?\(void\)\(value\)", re.DOTALL)

    def test_trace_dev_initialises_and_marks_secondary_render_spans(self):
        ino = read(INO)
        self.assertIn('#include "k1_trace.h"', ino)
        self.assertIn("K1_TRACE_INIT(64);", ino)
        self.assertIn('K1_TRACE_SCOPE("vp_secondary_snapshot")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_secondary_effect")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_secondary_store_clip")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_secondary_restore")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_channel_seed_history")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_waveform_fast_body")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_waveform_fast_history_store")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_bus_read")', ino)
        self.assertIn('K1_TRACE_SCOPE("vp_visual_hooks_tick")', ino)
        self.assertIn('K1_TRACE_COUNTER("vp_primary_render_us"', ino)
        self.assertIn('K1_TRACE_COUNTER("vp_secondary_render_us"', ino)

    def test_trace_command_is_trace_dev_only_and_typed_only(self):
        menu = read(SERIAL_MENU)
        table = read(SERIAL_TABLE)
        self.assertRegex(
            table,
            r'(?s)#if\s+FEATURE_MABUTRACE.*?SERIAL_CMD\("trace",\s*0,\s*cmd_trace_dump,\s*SC_TYPED_ONLY,\s*CMD_HARNESS,\s*IS_TYPED_ONLY\s*\).*?#endif',
        )
        self.assertRegex(
            menu,
            r'(?s)#if\s+FEATURE_MABUTRACE\s*\nvoid cmd_trace_dump\(\).*?K1_TRACE_DUMP_JSON\(USBSerial\).*?#endif',
        )
        self.assertRegex(
            menu,
            r'(?s)#if\s+FEATURE_MABUTRACE\s*\n\s*USBSerial\.println\(".*trace.*"\);\s*\n#endif',
        )


if __name__ == "__main__":
    unittest.main()
