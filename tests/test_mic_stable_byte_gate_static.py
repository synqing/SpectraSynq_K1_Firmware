"""Static contract for the mic-lane stable-section byte gate.

The ESP-IDF/Arduino image is NOT bit-reproducible in .flash.text/.flash.rodata
(determinism finding 2026-07-06): two clean builds of identical source differ in
those two sections. mic_stable_byte_gate.sh therefore hashes ONLY the three
REPRODUCIBLE loadable sections. This test locks that contract so nobody
re-introduces a flaky section, and asserts the committed reference covers the
SPH behaviour-preservation invariant envs + the IM73D reference build.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "regression-harness" / "mic_stable_byte_gate.sh"
REF = ROOT / "scripts" / "regression-harness" / "results" / "mic_stable_byte_gate.reference"

REPRODUCIBLE = {".dram0.data", ".iram0.text", ".iram0.vectors"}
NON_REPRODUCIBLE = {".flash.text", ".flash.rodata"}


class MicStableByteGateStatic(unittest.TestCase):
    def test_gate_script_exists(self):
        self.assertTrue(GATE.exists(), f"missing {GATE}")

    def test_gate_hashes_only_reproducible_sections(self):
        text = GATE.read_text()
        m = re.search(r"SECTIONS=\(([^)]*)\)", text)
        self.assertIsNotNone(m, "SECTIONS=(...) array not found")
        sections = set(m.group(1).split())
        self.assertEqual(
            sections,
            REPRODUCIBLE,
            "mic byte gate must hash EXACTLY the 3 reproducible sections",
        )
        # Guard: the flaky sections must never be part of the hashed set.
        self.assertTrue(sections.isdisjoint(NON_REPRODUCIBLE))

    def test_reference_covers_invariant_envs(self):
        self.assertTrue(REF.exists(), f"missing reference {REF} (run --update)")
        entries = {}
        for line in REF.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            env, h = line.split()
            entries[env] = h
        # SPH behaviour-preservation invariant + the IM73D reference build.
        for env in ("k1_hardware", "k1_bench_reference", "k1_bench_im73d"):
            self.assertIn(env, entries, f"{env} missing from the byte reference")
            self.assertRegex(entries[env], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
