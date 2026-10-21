"""Validation corpus (lane R1, DEF-002): GTZAN manifest builder and the scorer's validation role.
Both truth values: rows land in the pre-registered split and fold by octave; clips without audio or tempo are
excluded, not scored; an acceptance verdict over validation clips is refused (exit 3) exactly like dev.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/regression-harness"
sys.path.insert(0, str(HARNESS))
import tempo_validation_corpus as tvc  # noqa: E402

pytestmark = pytest.mark.tempo_gates


def _run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


def _corpus(tmp_path):
    ann, aud = tmp_path / "tempo", tmp_path / "genres"
    ann.mkdir(); (aud / "jazz").mkdir(parents=True)
    for num, bpm in (("00000", "45.0"), ("00001", "240.0"), ("00002", "120.5"), ("00003", "100")):
        (ann / f"gtzan_jazz_{num}.bpm").write_text(f"{bpm}\n")
    for num in ("00000", "00001", "00002", "00004"):           # 00003 has no audio, 00004 no tempo
        (aud / "jazz" / f"jazz.{num}.au").write_bytes(num.encode())
    v1, v2, ex = tmp_path / "v1.json", tmp_path / "v2.json", tmp_path / "ex.json"
    r = _run(HARNESS / "tempo_validation_corpus.py", "prepare", "--audio", aud, "--annotations", ann,
             "--out-v1", v1, "--out-v2", v2, "--excluded", ex)
    assert r.returncode == 0, r.stderr
    return json.loads(v1.read_text()), json.loads(v2.read_text()), json.loads(ex.read_text())


def test_rows_follow_the_preregistered_split_and_fold_by_octave(tmp_path):
    v1, v2, _ = _corpus(tmp_path)
    rows = {r["id"]: r for r in v1["rows"] + v2["rows"]}
    assert set(rows) == {"gz:jazz_00000", "gz:jazz_00001", "gz:jazz_00002"}
    for rid, r in rows.items():
        want = "V1" if hashlib.sha256(rid.encode()).digest()[0] % 2 == 0 else "V2"
        assert r["split"] == want and r in (v1 if want == "V1" else v2)["rows"]
        assert r["role"] == "validation" and 60.0 <= r["gold_bpm"] <= 155.0
    assert rows["gz:jazz_00000"]["gold_bpm"] == 90.0 and rows["gz:jazz_00001"]["gold_bpm"] == 120.0


def test_clips_without_audio_or_tempo_are_excluded(tmp_path):
    _, _, ex = _corpus(tmp_path)
    reasons = {e["id"]: e["reason"] for e in ex}
    assert reasons == {"gz:jazz_00003": "no audio file", "gz:jazz_00004": "no tempo annotation"}


def _traj(path, rid, bpm, lock):
    n = 3334
    path.write_text(json.dumps({"variant": "t", "clips": {rid: {
        "gen": list(range(1, n + 1)), "bpm": [bpm] * n, "lock": [lock] * n, "conf": [0.7] * n}}}))
    return path


@pytest.mark.parametrize("role,expect", [("validation", 3), ("heldout", 0)])
def test_scorer_refuses_acceptance_over_validation_like_dev(tmp_path, role, expect):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"rows": [{"id": "x:1", "path": "-", "sha256": "-", "gold_bpm": 120.0,
                                       "role": role, "source": "synthetic"}]}))
    r = _run(HARNESS / "tempo_lane_scorer.py", "compare", "--manifest", m, "--baseline",
             _traj(tmp_path / "b.json", "x:1", 80.0, 0), "--candidate", _traj(tmp_path / "c.json", "x:1", 120.0, 1),
             "--acceptance")
    assert r.returncode == expect, r.stdout + r.stderr
