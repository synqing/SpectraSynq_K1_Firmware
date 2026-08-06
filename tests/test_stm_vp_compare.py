"""Tests for stm_vp_compare fail-closed STM VP manifest gate."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts" / "regression-harness" / "stm_vp_compare.py"


def _run(manifest: dict) -> dict:
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(manifest, fh)
        path = fh.name
    proc = subprocess.run(
        [sys.executable, str(TOOL), path, "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _base_manifest(**overrides):
    data = {
        "schema_version": 1,
        "claim": "parity",
        "reference": {
            "algorithm_id": "ref-512",
            "executable_hash": "aaa",
            "source_hash": "src-a",
            "fft_size": 512,
            "stm_bins": 42,
        },
        "candidate": {
            "algorithm_id": "k1-40",
            "executable_hash": "bbb",
            "source_hash": "src-b",
            "stm_bins": 40,
        },
        "streams": [{"reference_energy": 0.5, "candidate_energy": 0.5}],
        "metrics_within_threshold": True,
    }
    data.update(overrides)
    return data


def test_empty_streams_indeterminate():
    m = _base_manifest(streams=[])
    out = _run(m)
    assert out["decision"] == "INDETERMINATE"
    assert any(r["code"] == "no_streams" for r in out["reasons"])


def test_identical_executable_indeterminate():
    m = _base_manifest(
        candidate={
            "algorithm_id": "k1-40",
            "executable_hash": "aaa",
            "source_hash": "src-b",
            "stm_bins": 40,
        }
    )
    out = _run(m)
    assert out["decision"] == "INDETERMINATE"
    assert any(r["code"] == "identical_executable" for r in out["reasons"])


def test_blank_both_indeterminate():
    m = _base_manifest(
        streams=[{"reference_energy": 0.0, "candidate_energy": 0.0}],
    )
    out = _run(m)
    assert out["decision"] == "INDETERMINATE"
    assert any(r["code"] == "blank_both" for r in out["reasons"])


def test_self_shadow_parity_indeterminate():
    m = _base_manifest(controls={"scenario": "self_shadow", "shadow": "self"})
    out = _run(m)
    assert out["decision"] == "INDETERMINATE"
    assert any(r["code"] == "self_shadow" for r in out["reasons"])


def test_reference_active_candidate_blank_fail():
    m = _base_manifest(
        streams=[{"reference_energy": 0.8, "candidate_energy": 0.0}],
    )
    out = _run(m)
    assert out["decision"] == "FAIL"
    assert any(r["code"] == "candidate_blank" for r in out["reasons"])


def test_negative_control_divergence_fail():
    m = _base_manifest(
        negative_control={
            "injected": True,
            "expected_fail": True,
            "metrics_within_threshold": True,
        }
    )
    out = _run(m)
    assert out["decision"] == "FAIL"
    assert any(r["code"] == "scorer_insensitive" for r in out["reasons"])


def test_valid_independent_pass():
    out = _run(_base_manifest())
    assert out["decision"] == "PASS"
