"""Experiment E1 hold rule (lane R1, DEF-002): `tempo_joint_estimator.py gate --hold-s D` publishes the
tracker's lock only once lock and estimator agreement have held continuously for D seconds.
Both truth values: a run long enough must publish from the D-second mark, a shorter or broken run must not,
disagreement must never publish, and D = 0 must equal the plain agreement gate (the p2.6 behaviour).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/regression-harness"
sys.path.insert(0, str(HARNESS))
import tempo_joint_estimator as tje  # noqa: E402

pytestmark = pytest.mark.tempo_gates
PER_S = round(1.0 / tje.GEN_S)          # 133 generations per second (7.5 ms each)


def test_hold_publishes_only_after_d_seconds_of_continuous_truth():
    cond = [True] * (2 * PER_S)
    out = tje.hold(cond, 1.0)
    first = out.index(1)
    assert abs(first * tje.GEN_S - 1.0) <= tje.GEN_S
    assert not any(out[:first]) and all(out[first:])


def test_a_break_resets_the_run_and_short_runs_never_publish():
    run = [True] * (PER_S // 2)
    cond = run + [False] + run + [False] + run
    assert not any(tje.hold(cond, 1.0))


def test_hold_zero_is_the_plain_condition():
    cond = [True, False, True, True, False]
    assert tje.hold(cond, 0.0) == [1, 0, 1, 1, 0]


def _traj(path, bpm, lock, n):
    path.write_text(json.dumps({"variant": "t", "clips": {"c": {
        "gen": list(range(1, n + 1)), "bpm": [bpm] * n, "lock": [lock] * n, "conf": [0.7] * n}}}))
    return path


def _gate(tmp_path, est_bpm, hold_s, n=3 * PER_S):
    trk = _traj(tmp_path / "trk.json", 120.0, 1, n)
    est = _traj(tmp_path / f"est{est_bpm}.json", est_bpm, 0, n)
    out = tmp_path / f"g{est_bpm}_{hold_s}.json"
    r = subprocess.run([sys.executable, str(HARNESS / "tempo_joint_estimator.py"), "gate", "--tracker-traj", str(trk),
                        "--estimator-traj", str(est), "--hold-s", str(hold_s), "--out", str(out)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    return json.loads(out.read_text())


def test_gate_cli_agreeing_estimator_publishes_after_the_hold(tmp_path):
    doc = _gate(tmp_path, 60.0, 2.0)                    # 60 = half of 120: agrees up to an octave
    lock = doc["clips"]["c"]["lock"]
    assert not any(lock[:2 * PER_S - 1]) and all(lock[2 * PER_S + 1:])
    assert doc["producer"]["hold_s"] == 2.0 and doc["variant"].endswith("-hold2s")


def test_gate_cli_disagreeing_estimator_never_publishes(tmp_path):
    doc = _gate(tmp_path, 80.0, 0.0)                    # 80 = 2/3 of 120: a 3:2 disagreement
    assert not any(doc["clips"]["c"]["lock"])


def test_gate_cli_hold_zero_output_has_no_hold_field(tmp_path):
    doc = _gate(tmp_path, 120.0, 0.0)
    assert "hold_s" not in doc["producer"] and all(doc["clips"]["c"]["lock"])
