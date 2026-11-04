"""M4 gate (lane R1, DEF-002, invariant I5): the frozen tempo scorer refuses an acceptance verdict on
dev-role clips, and its definitions classify 3:2 / octave / no-lock cases correctly.

Both truth values are exercised: a held-out comparison must be able to pass AND to fail, and the
same comparison over a dev clip must be refused (exit 3).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCORER = ROOT / "scripts/regression-harness/tempo_lane_scorer.py"
MANIFEST = ROOT / "tests/fixtures/tempo_corpus/manifest.json"

pytestmark = pytest.mark.tempo_gates


def _traj(clips: dict) -> dict:
    n = 3334
    return {"variant": "synthetic", "clips": {cid: {"gen": list(range(1, n + 1)), "bpm": [bpm] * n,
                                                    "conf": [0.9] * n, "lock": [lock] * n}
                                              for cid, (bpm, lock) in clips.items()}}


def _run(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCORER), *map(str, args)], capture_output=True, text=True)


@pytest.fixture()
def manifest(tmp_path):
    rows = [
        {"id": "dev:x", "path": "-", "sha256": "-", "gold_bpm": 120.0, "role": "dev", "source": "synthetic"},
        {"id": "ho:y", "path": "-", "sha256": "-", "gold_bpm": 100.0, "role": "heldout", "source": "synthetic"},
    ]
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"rows": rows}))
    return p


def _write(tmp_path, name, clips):
    p = tmp_path / name
    p.write_text(json.dumps(_traj(clips)))
    return p


def test_scorer_self_test_passes():
    r = _run("self-test")
    assert r.returncode == 0, r.stdout + r.stderr


def test_acceptance_over_dev_clip_is_refused(tmp_path, manifest):
    base = _write(tmp_path, "a.json", {"dev:x": (80.0, 0)})
    cand = _write(tmp_path, "b.json", {"dev:x": (120.0, 1)})
    r = _run("compare", "--manifest", manifest, "--baseline", base, "--candidate", cand, "--role", "dev", "--acceptance")
    assert r.returncode == 3, r.stdout + r.stderr


def test_acceptance_over_heldout_can_pass_and_fail(tmp_path, manifest):
    worse = _write(tmp_path, "w.json", {"ho:y": (150.0, 0)})     # unlocked 3:2
    better = _write(tmp_path, "g.json", {"ho:y": (100.0, 1)})    # correct lock
    wrong = _write(tmp_path, "x.json", {"ho:y": (150.0, 1)})     # confident 3:2 lock
    ok = _run("compare", "--manifest", manifest, "--baseline", worse, "--candidate", better, "--role", "heldout", "--acceptance")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = _run("compare", "--manifest", manifest, "--baseline", worse, "--candidate", wrong, "--role", "heldout", "--acceptance")
    assert bad.returncode == 1, bad.stdout + bad.stderr


def test_role_all_acceptance_containing_dev_is_refused(tmp_path, manifest):
    base = _write(tmp_path, "a.json", {"dev:x": (80.0, 0), "ho:y": (150.0, 0)})
    cand = _write(tmp_path, "b.json", {"dev:x": (120.0, 1), "ho:y": (100.0, 1)})
    r = _run("compare", "--manifest", manifest, "--baseline", base, "--candidate", cand, "--role", "all", "--acceptance")
    assert r.returncode == 3, r.stdout + r.stderr


def test_committed_manifest_roles_are_well_formed():
    doc = json.loads(MANIFEST.read_text())
    roles = {r["role"] for r in doc["rows"]}
    assert roles <= {"dev", "heldout"}
    dev = [r for r in doc["rows"] if r["role"] == "dev"]
    assert len(dev) == 36, "the 36 HarmonixSet clips are the dev set"
    assert all(r["id"].startswith("hx:") for r in dev)
