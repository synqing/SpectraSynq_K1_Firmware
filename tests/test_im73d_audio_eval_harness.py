import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts" / "regression-harness" / "im73d_audio_eval.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("im73d_audio_eval", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ap_parser_captures_core_quality_fields():
    harness = load_harness()
    row = harness.parse_ap_line(
        "[AP] SSL=162 DC=0 max_raw=1224 follower=1240 peak_scaled=0.686 "
        "response_gain=1.000 | k1_loud=1 input_trim=1.000 gdft_trim=0.998 "
        "agc_gain=0.442 agc_env=0.000 clip_pct=0.000 near_pct=0.000 "
        "peak_pin=0.000 spec_sat=0.000 cal_source=persisted_profile cal_valid=1"
    )

    assert row is not None
    assert row["SSL"] == 162
    assert row["DC"] == 0
    assert row["max_raw"] == 1224
    assert row["peak_scaled"] == 0.686
    assert row["input_trim"] == 1.0
    assert row["cal_source"] == "persisted_profile"


def test_quality_gate_rejects_missing_rows_and_clipping():
    harness = load_harness()
    assert harness.assess_quality(harness.summarise_numeric([]), min_rows=1) == {
        "usable": False,
        "reasons": ["too_few_ap_rows:0<1"],
        "warnings": [],
    }

    clipped = {
        "max_raw": 1200,
        "peak_scaled": 0.5,
        "input_trim": 1.0,
        "clip_pct": 0.01,
        "near_pct": 0.0,
        "peak_pin": 0.0,
    }
    quality = harness.assess_quality(harness.summarise_numeric([clipped]), min_rows=1)
    assert quality["usable"] is False
    assert "clip_pct_nonzero" in quality["reasons"]


def test_quality_gate_warns_on_conditioned_peak_pin_without_rejecting_raw_capture():
    harness = load_harness()
    downstream_pinned = {
        "max_raw": 1200,
        "peak_scaled": 1.0,
        "input_trim": 1.0,
        "clip_pct": 0.0,
        "near_pct": 0.0,
        "peak_pin": 0.75,
    }

    quality = harness.assess_quality(harness.summarise_numeric([downstream_pinned]), min_rows=1)

    assert quality["usable"] is True
    assert quality["reasons"] == []
    assert quality["warnings"] == ["conditioned_peak_pin_high"]


def test_repeatability_gate_uses_characterised_variance():
    harness = load_harness()
    stable = harness.repeatability_report(
        [
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 1000}}}}},
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 1080}}}}},
        ],
        max_cv=0.15,
    )
    assert stable["repeatable"] is True

    drifting = harness.repeatability_report(
        [
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 1000}}}}},
            {"label": "music", "volume": 50, "devices": {"bench_im73d": {"summary": {"max_raw": {"p90": 2000}}}}},
        ],
        max_cv=0.15,
    )
    assert drifting["repeatable"] is False


def test_harness_self_test_runs():
    harness = load_harness()
    harness.run_self_test()
