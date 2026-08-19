"""Palette-safe EdgeMixer resolver — LED-buffer rtrace gate.

Compiles the REAL firmware k1_edgemixer.cpp + k1_palette_edge_bridge.cpp with
K1_EDGE_PALETTE_HONOUR_V1, dumps 160-px frames in the device rtrace hex
layout, and scores them with score_palette_resolver_rtrace.py (same decoder
as hue_coverage.py rtrace mode). Replaces Captain eyes-on for this lane.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PROBE = ROOT / "scripts" / "regression-harness" / "edgemixer_palette_resolver_probe.cpp"
SCORER = ROOT / "scripts" / "regression-harness" / "score_palette_resolver_rtrace.py"
SHIM_DIR = ROOT / "scripts" / "regression-harness" / "edgemixer_host_shim"
FIXEDPOINTS_SRC = ROOT / "libraries" / "FixedPoints" / "src"
MODULE_CPP = FW / "director" / "k1_edgemixer.cpp"
BRIDGE_CPP = FW / "director" / "k1_palette_edge_bridge.cpp"

GPP_CANDIDATES = ["g++-15", "g++-14", "g++-13", "g++-12", "g++"]


def _gnu_compiler():
    for cand in GPP_CANDIDATES:
        if not shutil.which(cand):
            continue
        try:
            ver = subprocess.run([cand, "--version"], capture_output=True, text=True)
        except OSError:
            continue
        if "clang" in (ver.stdout + ver.stderr).lower():
            continue
        return cand
    return None


def _build_run_score():
    cc = _gnu_compiler()
    if cc is None:
        raise unittest.SkipTest(
            "no real GNU g++ found; FixedPoints host build needs GCC, not clang"
        )
    with tempfile.TemporaryDirectory() as td:
        exe = Path(td) / "edgemixer_palette_resolver_probe"
        dump = Path(td) / "dump.log"
        score = Path(td) / "score.json"
        subprocess.run(
            [
                cc, "-std=c++17", "-O2",
                "-DK1_EDGEMIXER_HOST_TEST=1",
                "-DK1_EDGE_PALETTE_HONOUR_V1",
                f"-I{SHIM_DIR}",
                f"-I{FIXEDPOINTS_SRC}",
                f"-I{FW / 'director'}",
                str(PROBE), str(MODULE_CPP), str(BRIDGE_CPP),
                "-o", str(exe),
            ],
            check=True, capture_output=True, text=True,
        )
        dumped = subprocess.run(
            [str(exe)], check=True, capture_output=True, text=True,
        )
        dump.write_text(dumped.stdout)
        scored = subprocess.run(
            ["python3", str(SCORER), str(dump), str(score)],
            check=False, capture_output=True, text=True,
        )
        return scored.returncode, scored.stdout, score.read_text() if score.is_file() else ""


class EdgeMixerPaletteResolverRtraceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.stdout, cls.score_raw = _build_run_score()

    def test_rtrace_score_passes(self):
        self.assertEqual(
            self.rc, 0,
            "palette-resolver rtrace score must PASS\n" + self.stdout,
        )
        self.assertIn('"verdict": "PASS"', self.score_raw)
