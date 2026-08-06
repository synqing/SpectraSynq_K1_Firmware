"""Host mirror test for SERIAL_TYPED_CMD_TABLE (.def shared with firmware)."""
from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts" / "regression-harness" / "serial_typed_dispatch_table_test.cpp"


class SerialTypedDispatchTableStaticTest(unittest.TestCase):
    def test_host_mirror_compiles_and_passes(self):
        cc = shutil.which("g++-15") or shutil.which("g++-14") or shutil.which("g++")
        self.assertIsNotNone(cc)
        binary = ROOT / ".pytest_cache" / "serial_typed_dispatch_table_test"
        r = subprocess.run([cc, "-std=c++17", "-Wall", "-Wextra", str(SRC), "-o", str(binary)],
                           cwd=str(ROOT), text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        run = subprocess.run([str(binary)], cwd=str(ROOT), text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("typed_table_rows=", run.stdout)


if __name__ == "__main__":
    unittest.main()
