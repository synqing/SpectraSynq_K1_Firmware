"""tempo_audition.py (lane R1): the WAV it writes is the exact PCM a run fed the firmware.
Both truth values: the run's recorded sha256 matches (exit 0); a different recorded sha256 is reported (exit 1)."""
import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/regression-harness/tempo_audition.py"
sys.path.insert(0, str(ROOT / "scripts/regression-harness"))
import tempo_lane_emu as tle  # noqa: E402

pytestmark = pytest.mark.tempo_gates
CASE = "white-noise-s99"                     # synthetic, deterministic seed, no audio file needed


def _expected_sha():
    case = next(c for c in tle.suite("neg") if c["id"] == CASE)
    return hashlib.sha256(tle.case_pcm(case, Path("."))[0]).hexdigest()


def _run(tmp_path, recorded):
    (tmp_path / "cases.json").write_text(json.dumps({"cases": [{"id": CASE, "pcm_sha256": recorded}]}))
    return subprocess.run([sys.executable, str(TOOL), "suite", "--suite", "neg", "--id", CASE, "--run", str(tmp_path),
                           "--no-play"], capture_output=True, text=True, cwd=ROOT)


def test_rebuilt_pcm_matches_the_recorded_run_and_is_written_as_wav(tmp_path):
    want = _expected_sha()
    r = _run(tmp_path, want)
    assert r.returncode == 0 and "MATCHES" in r.stdout, r.stdout + r.stderr
    wav = ROOT / "_scratch/esp-emulator/tempo-lock-r1/audition" / f"{CASE}.wav"
    with wave.open(str(wav)) as w:
        assert w.getframerate() == tle.RATE and w.getnchannels() == 1
        assert hashlib.sha256(w.readframes(w.getnframes())).hexdigest() == want


def test_a_different_recorded_hash_is_reported(tmp_path):
    r = _run(tmp_path, "0" * 64)
    assert r.returncode == 1 and "DIFFERS" in r.stdout, r.stdout + r.stderr
