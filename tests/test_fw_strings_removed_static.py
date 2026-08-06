import re
import unittest
from pathlib import Path

from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
RENDER_REPLAY = ROOT / "scripts" / "regression-harness" / "render_replay.py"


class TestFwStringsRemovedStatic(unittest.TestCase):
    def test_fw_strings_header_is_removed_from_live_firmware_and_harness(self):
        self.assertFalse((FW / "fw_strings.h").exists(), "fw_strings.h must not exist")

        scanned_paths = list(FW.iterdir()) + [RENDER_REPLAY]
        survivors = []
        for path in scanned_paths:
            if path.suffix not in {".h", ".cpp", ".ino", ".py"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "fw_strings" in text or "strings.h" in text:
                survivors.append(str(path.relative_to(ROOT)))

        self.assertEqual([], survivors, "fw_strings/strings.h references must be gone")

    def test_status_tokens_are_owned_by_globals_definition_unit(self):
        globals_h = (FW / "globals.h").read_text()
        globals_cpp = (FW / "globals.cpp").read_text()

        self.assertIn("extern const char K1_PASS[];", globals_h)
        self.assertIn("extern const char K1_FAIL[];", globals_h)
        self.assertRegex(globals_cpp, r'\bconst\s+char\s+K1_PASS\[\]\s*=\s*"PASS"\s*;')
        self.assertRegex(
            globals_cpp,
            r'\bconst\s+char\s+K1_FAIL\[\]\s*=\s*"FAIL ###################"\s*;',
        )

    def test_dead_note_label_tables_do_not_survive(self):
        offenders = []
        for path in FW.iterdir():
            if path.suffix not in {".h", ".cpp", ".ino"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\b(notes_chromatic|sharps)\b", text):
                offenders.append(str(path.relative_to(ROOT)))

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
