"""Pre-registered lock verdict (lane R1, DEF-002). Both truth values for each criterion:
enough right locks with few wrong passes; low coverage, too many wrong, or a moved BPM fails (exit 1)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/regression-harness/tempo_lock_verdict.py"
pytestmark = pytest.mark.tempo_gates


def _case(tmp_path, n, right, wrong, move_bpm=False):
    clips = {f"c{i}": {"gen": [1, 2], "bpm": [120.0, 120.0], "lock": [1, 1]} for i in range(n)}
    cand = json.loads(json.dumps(clips))
    if move_bpm:
        cand["c0"]["bpm"] = [80.0, 80.0]
    summ = {"n": n, "locked": right + wrong, "locked_correct": right, "locked_wrong": wrong}
    files = {}
    for name, doc in (("rep", {"baseline": summ, "candidate": summ}), ("base", {"clips": clips}),
                      ("cand", {"clips": cand})):
        files[name] = tmp_path / f"{name}.json"
        files[name].write_text(json.dumps(doc))
    r = subprocess.run([sys.executable, str(TOOL), "--report", str(files["rep"]), "--baseline-traj",
                        str(files["base"]), "--candidate-traj", str(files["cand"])], capture_output=True, text=True)
    return r.returncode, json.loads(r.stdout) if r.stdout.strip().startswith("{") else None


def test_many_right_locks_and_none_wrong_pass(tmp_path):
    code, out = _case(tmp_path, 100, 40, 0)
    assert code == 0 and out["met"]


@pytest.mark.parametrize("n,right,wrong,failing", [(100, 20, 0, "C2_right_lock_coverage"),   # 20 % < 25 %
                                                   (100, 40, 4, "C1_wrong_wilson_upper"),    # upper bound > 10 %
                                                   (100, 1, 0, "C1_wrong_wilson_upper")])    # too few locks
def test_low_coverage_or_wrong_locks_fail(tmp_path, n, right, wrong, failing):
    code, out = _case(tmp_path, n, right, wrong)
    assert code == 1 and not out[failing]["met"]


def test_a_gate_that_moves_the_bpm_fails_c3(tmp_path):
    code, out = _case(tmp_path, 100, 40, 0, move_bpm=True)
    assert code == 1 and not out["C3_bpm_passthrough"]["met"]
