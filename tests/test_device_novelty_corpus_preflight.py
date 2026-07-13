import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))
SPEC = importlib.util.spec_from_file_location(
    "device_novelty_corpus_preflight", HARNESS / "device_novelty_corpus_preflight.py"
)
preflight = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(preflight)


def test_manifest_requires_product_critical_edm_band():
    errors = preflight.validate_manifest(
        {"tracks": [{"id": "slow", "genre": "Rock", "gt_bpm": 90.0}]}
    )
    assert any("120-135 BPM" in error for error in errors)


def test_manifest_accepts_unique_ground_truthed_edm_track():
    errors = preflight.validate_manifest(
        {"tracks": [{"id": "edm", "genre": "Techno", "gt_bpm": 135.0}]}
    )
    assert errors == []


def test_local_acf_peaks_include_periodic_signal_tempo():
    fps = preflight.novelty.SAMPLE_RATE / preflight.novelty.HOP
    expected_bpm = 128.0
    samples = np.arange(int(fps * 30.0))
    curve = 0.5 + 0.5 * np.cos(2.0 * np.pi * samples * expected_bpm / (60.0 * fps))
    peaks = preflight.local_acf_peaks(curve)
    assert any(abs(float(peak["bpm"]) - expected_bpm) / expected_bpm <= preflight.TOLERANCE for peak in peaks)
