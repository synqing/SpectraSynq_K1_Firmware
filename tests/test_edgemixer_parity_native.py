"""EdgeMixer -> K1 colour-port parity (Step 1 acceptance gate).

Compiles the REAL firmware colour module
SPECTRASYNQ_K1_FIRMWARE/director/sb_edgemixer_lite.cpp on the host (via the probe
scripts/regression-harness/edgemixer_parity_probe.cpp) and drives its actual
sb_edgemixer_lite_apply() against the frozen LightwaveOS EdgeMixer golden vectors
(tests/golden/edgemixer_golden.csv, 810 rows). No Python re-implementation of the
transform, so the test cannot drift from the firmware.

Acceptance: every golden vector reproduced within +/-1 LSB per channel; near-black
inputs passed through unchanged; and an injected one-coefficient fault breaks
parity (fault-evidence — a harness that cannot fail is worthless). Mirrors the
test_spectral_honesty.py host-probe convention.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
MODULE_CPP = FW / "director" / "sb_edgemixer_lite.cpp"
PROBE = ROOT / "scripts" / "regression-harness" / "edgemixer_parity_probe.cpp"
SHIM_DIR = ROOT / "scripts" / "regression-harness" / "edgemixer_host_shim"
FIXEDPOINTS_SRC = ROOT / "libraries" / "FixedPoints" / "src"
GOLDEN_CSV = ROOT / "tests" / "golden" / "edgemixer_golden.csv"

# 6 harmony modes x 5 spreads x 27 probes.
EXPECTED_ROWS = 810
# 6 modes x 5 spreads x 3 near-black probes.
EXPECTED_NEARBLACK = 90


# The vendored FixedPoints header declares in-class `static constexpr SFixed`
# members of its own (still-incomplete) type. Apple clang rejects this under
# -std=c++17; real GCC (the firmware's xtensa-gcc lineage) accepts it. So, exactly
# like scripts/regression-harness/render_replay.py, this gate requires a real g++
# and refuses an Apple-clang shim masquerading as g++.
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
            continue  # Apple clang aliased as g++ cannot build FixedPoints
        return cand
    return None


def _build_and_run():
    cc = _gnu_compiler()
    if cc is None:
        raise unittest.SkipTest(
            "no real GNU g++ found; FixedPoints host build needs GCC, not clang "
            "(see render_replay.py)"
        )
    with tempfile.TemporaryDirectory() as td:
        exe = Path(td) / "edgemixer_parity_probe"
        compile_cmd = [
            cc, "-std=c++17", "-O2",
            "-DSB_EDGEMIXER_HOST_TEST=1",
            f"-I{SHIM_DIR}",
            f"-I{FIXEDPOINTS_SRC}",
            f"-I{FW / 'director'}",
            str(PROBE), str(MODULE_CPP),
            "-o", str(exe),
        ]
        subprocess.run(compile_cmd, check=True, capture_output=True, text=True)
        proc = subprocess.run(
            [str(exe), str(GOLDEN_CSV)],
            check=True, capture_output=True, text=True,
        )
    out = {}
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[0]] = int(parts[1])
    return out


class EdgeMixerParityNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert GOLDEN_CSV.is_file(), f"missing golden fixture: {GOLDEN_CSV}"
        cls.v = _build_and_run()

    def test_full_golden_vector_set_present(self):
        self.assertEqual(self.v["PARITY_COUNT"], EXPECTED_ROWS)

    def test_parity_within_one_lsb(self):
        # The proven +/-1 LSB gate. Do NOT loosen — a wider bound would hide a
        # silent colour-port defect. Worst-case locator is reported for triage.
        self.assertLessEqual(
            self.v["PARITY_WORST_LSB"], 1,
            "max |K1 - golden| exceeds 1 LSB "
            f"(mode {self.v['PARITY_WORST_MODE']}, spread {self.v['PARITY_WORST_SPREAD']})",
        )

    def test_near_black_passthrough(self):
        self.assertEqual(self.v["NEARBLACK_CHECKED"], EXPECTED_NEARBLACK)
        self.assertEqual(self.v["NEARBLACK_FAIL"], 0)

    def test_fault_evidence_perturbation_breaks_parity(self):
        # Restored matrix holds the parity gate...
        self.assertLessEqual(self.v["FAULT_RESTORED_LSB"], 1)
        # ...and an injected one-coefficient fault provably breaks it (> 1 LSB).
        self.assertGreater(
            self.v["FAULT_PERTURBED_LSB"], 1,
            "injected coefficient fault MUST break parity by > 1 LSB",
        )


if __name__ == "__main__":
    unittest.main()
