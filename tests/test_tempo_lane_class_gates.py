"""M1 (veto observability, I1) and M2 (contrast invariance, I2) gates — lane R1, DEF-001.

Input: the R3 music passage's tempo input captured from the real emulated firmware
(tests/fixtures/tempo_corpus/streams/, I7), replayed through the unmodified k1_tempo.cpp.
Both truth values: the lane flag set must pass; the shipped build (the DEF-001 baseline) must fail,
and hand-made rows that hide a lock must fail.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/regression-harness"
GATES = HARNESS / "tempo_lane_gates.py"
REPLAY = HARNESS / "tempo_lane_replay.py"
STREAMS = ROOT / "tests/fixtures/tempo_corpus/streams/index.json"
sys.path.insert(0, str(HARNESS))

pytestmark = [pytest.mark.tempo_gates,
              pytest.mark.skipif(shutil.which("clang++") is None, reason="host tempo build needs clang++")]


def _run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


def _replay(tmp_path, variant, clip):
    out = tmp_path / f"{variant}.json"
    r = _run(REPLAY, "replay", "--fixtures", STREAMS, "--variant", variant, "--debug", "--only", clip, "--out", out)
    assert r.returncode == 0, r.stderr
    return out


def test_m1_holds_for_the_lane_flag_set(tmp_path):
    traj = _replay(tmp_path, "l1", "r3:r3_music_linear")
    r = _run(GATES, "m1", "--traj", traj)
    assert r.returncode == 0, r.stdout


def test_m1_catches_the_shipped_hidden_silence_veto(tmp_path):
    traj = _replay(tmp_path, "shipped", "r3:r3_music_sqrt")
    r = _run(GATES, "m1", "--traj", traj)
    assert r.returncode == 1, r.stdout
    assert "VIOLATION at generation" in r.stdout


def test_m1_rule_flags_a_hidden_lock_and_accepts_a_named_one():
    import tempo_lane_gates as g
    assert g.m1_check([(10, 0, 1, 0, 0)]) == 10            # locked inside, hidden, no veto -> violation
    assert g.m1_check([(10, 0, 1, 0, 4)]) is None          # hidden but named -> allowed
    assert g.m1_check([(10, 1, 1, 0, 0)]) is None          # producer silence owns it
    assert g.m1_check([(10, 0, 1, 1, 0)]) is None          # published


def test_m2_lane_lock_is_invariant_to_scale_and_compression():
    r = _run(GATES, "m2", "--fixtures", STREAMS, "--clip", "r3:r3_music_linear", "--variant", "l1")
    assert r.returncode == 0, r.stdout


def test_m2_catches_the_shipped_compression_dependence():
    r = _run(GATES, "m2", "--fixtures", STREAMS, "--clip", "r3:r3_music_sqrt", "--variant", "shipped")
    assert r.returncode == 1, r.stdout


def test_m2_spectral_presence_build_is_invariant_with_the_spectrum_transformed():
    # Same transforms on the novelty AND on every per-note spectrum bin (the whole producer output).
    r = _run(GATES, "m2", "--fixtures", STREAMS, "--clip", "r3:r3_music_spec", "--variant", "l1sp")
    assert r.returncode == 0, r.stdout
    import json
    assert json.loads(r.stdout)["spectrum_transformed"] is True


def test_m2_sees_the_spectrum_path_erased_evidence_must_fail():
    # Broken input: spectrum zeroed, novelty kept. A gate that did not exercise the presence path would pass.
    r = _run(GATES, "m2", "--fixtures", STREAMS, "--clip", "r3:r3_music_spec", "--variant", "l1sp",
             "--transforms", "speczero:1")
    assert r.returncode == 1, r.stdout


# ---------------------------------------------------------------- rule 3.3 lock-off (K1_TEMPO_LOCK_OFF_V1)
def test_rule33_lockoff_withholds_lock_and_ticks_and_names_the_gate(tmp_path):
    out = tmp_path / "lockoff.json"
    r = _run(REPLAY, "replay", "--fixtures", STREAMS, "--variant", "l1sp_lockoff", "--debug",
             "--only", "r3:r3_music_spec", "--out", out)
    assert r.returncode == 0, r.stderr
    g = _run(GATES, "lockoff", "--traj", out)
    assert g.returncode == 0, g.stdout
    import json
    assert json.loads(g.stdout)["clips"][0]["tentative_frac_scored"] > 0.5   # music still reads TENTATIVE
    assert _run(GATES, "m1", "--traj", out).returncode == 0                   # internal lock is named (I1)


def test_rule33_gate_fails_on_the_lock_publishing_build(tmp_path):
    out = _replay(tmp_path, "l1sp", "r3:r3_music_spec")
    g = _run(GATES, "lockoff", "--traj", out)
    assert g.returncode == 1, g.stdout


def test_rule33_rule_flags_each_withheld_output():
    import tempo_lane_gates as g
    ok = {"gen": [1, 2], "lock": [0, 0], "tick": [0, 0], "conf": [0.0, 0.5999], "veto": [0, 128 | 4], "emit_count": [0, 1]}
    assert g.lockoff_check(ok) is None
    assert "lock" in g.lockoff_check(dict(ok, lock=[0, 1]))
    assert "tick" in g.lockoff_check(dict(ok, tick=[0, 1]))
    assert "LOCKED band" in g.lockoff_check(dict(ok, conf=[0.0, 0.6]))
    assert "veto bit missing" in g.lockoff_check(dict(ok, veto=[0, 4]))


# ---------------------------------------------------------------- M5 metrical trap suite (I6)
TRAPS = HARNESS / "tempo_trap_suite.py"
TRAP_BASELINE = ROOT / "tests/fixtures/tempo_corpus/traps/baseline_shipped_selection.json"


def test_m5_lane_flag_set_adds_no_new_attractor_ratio(tmp_path):
    cand = tmp_path / "lane.json"
    r = _run(TRAPS, "run", "--variant", "l1", "--out", cand)
    assert r.returncode in (0, 1), r.stderr          # 1 = some trap fails (the baseline already does)
    c = _run(TRAPS, "compare", "--baseline", TRAP_BASELINE, "--candidate", cand)
    assert c.returncode == 0, c.stdout


def test_m5_flags_a_new_attractor_ratio(tmp_path):
    import json
    base = json.loads(TRAP_BASELINE.read_text())
    bad = dict(base, failing=base["failing"] + [["clean", 120.0, "FAIL_3/2"]],
               failing_ratio_classes=sorted(set(base["failing_ratio_classes"]) | {"FAIL_3/2"}))
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad))
    c = _run(TRAPS, "compare", "--baseline", TRAP_BASELINE, "--candidate", p)
    assert c.returncode == 1, c.stdout


def test_m5_suite_can_see_the_def002_mechanism():
    import json
    base = json.loads(TRAP_BASELINE.read_text())
    assert "FAIL_2/3" in base["failing_ratio_classes"], "the trap suite must reproduce the 3:2 attractor"
