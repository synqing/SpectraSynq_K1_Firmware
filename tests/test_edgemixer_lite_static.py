import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
EDGE_CPP = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE") / "sb_edgemixer_lite.cpp"
EDGE_H = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE") / "sb_edgemixer_lite.h"


def read(path):
    return path.read_text(encoding="utf-8")


class EdgeMixerLiteStaticTest(unittest.TestCase):
    def test_invalid_modes_are_sanitised_to_off(self):
        source = read(EDGE_CPP)
        self.assertIn("sb_edge_mode_or_off", source)
        self.assertRegex(
            source,
            r"default:\s*return\s+SB_EDGE_MIXER_OFF;",
            "Unexpected EdgeMixer mode values must fail closed to OFF.",
        )
        self.assertRegex(
            source,
            r"next\.mode\s*=\s*sb_edge_mode_or_off\(config\.mode\);",
            "Stored EdgeMixer config staging must not retain invalid enum values.",
        )
        self.assertIn("sb_edge_config = next;", source)
        self.assertRegex(
            source,
            r"SBEdgeMixerMode\s+mode\s*=\s*sb_edge_mode_or_off\(config\.mode\);",
            "Render-callable apply path must also fail closed for caller-provided config.",
        )

    def test_centre_mask_is_k1_native_centre_origin(self):
        source = read(EDGE_CPP)
        self.assertIn("79.5f", source)
        self.assertIn("NATIVE_RESOLUTION", source)
        self.assertNotIn("CENTRE_GRADIENT", source)

    def test_all_declared_modes_are_handled(self):
        header = read(EDGE_H)
        source = read(EDGE_CPP)
        modes = re.findall(r"\b(SB_EDGE_MIXER_[A-Z0-9_]+)\b", header)
        modes = [mode for mode in modes if mode != "SB_EDGE_MIXER_OFF"]
        missing = [mode for mode in modes if f"case {mode}:" not in source]
        self.assertEqual(missing, [])

    def test_render_callable_source_has_no_io_heap_or_wifi(self):
        source = read(EDGE_CPP)
        forbidden = (
            r"\bnew\s*(?:\(|[A-Za-z_])",
            r"\bmalloc\s*\(",
            r"\bcalloc\s*\(",
            r"\brealloc\s*\(",
            r"\bfree\s*\(",
            r"\bString\b",
            r"\bstd::",
            r"\bSerial\.",
            r"\bUSBSerial\.",
            r"\bFastLED\.show\s*\(",
            r"#\s*include\s*[<\"].*WiFi",
            r"\bPreferences\b",
        )
        hits = [pattern for pattern in forbidden if re.search(pattern, source)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
