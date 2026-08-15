"""Gate 1 parser checks for AP freshness and capture identity."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "device_ap_cadence_capture.py"


def load_capture_module():
    spec = importlib.util.spec_from_file_location("device_ap_cadence_capture", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_row(sequence: int, newest_to_publish: int = 5000):
    read_return = 1_000_000 + sequence * 7500
    newest = read_return
    oldest = newest - 7421
    publish = newest + newest_to_publish
    return {
        "frame": sequence,
        "t": sequence * 8,
        "sample_rate": 12800,
        "samples_per_chunk": 96,
        "tempo_decim": 3,
        "capture_seq": sequence,
        "i2s_read_start_us": read_return - 100,
        "i2s_read_return_us": read_return,
        "newest_sample_estimate_us": newest,
        "oldest_sample_estimate_us": oldest,
        "ap_publish_us": publish,
        "newest_to_publish_us": newest_to_publish,
        "oldest_to_publish_us": newest_to_publish + 7421,
        "sample_time_assumption_id": 1,
        "i2s_ok": 1,
        "bytes_ok": 1,
        "i2s_status": 0,
        "i2s_us": 100,
        "gdft_us": 3000,
        "novelty_us": 100,
        "total_us": 5000,
    }


def test_summary_reports_freshness_identity_and_assumption():
    module = load_capture_module()
    summary = module.summarise_rows(
        [make_row(1), make_row(2), make_row(3)], {}, 12800, 96, 3
    )
    assert summary["timestamp_identity_row_count"] == 3
    assert summary["capture_sequence_gap_count"] == 0
    assert summary["timestamp_order_failure_count"] == 0
    assert summary["sample_time_assumption_ids"] == [1]
    freshness = summary["timing_us"]["newest_sample_to_ap_publish_us"]
    assert freshness["median"] == 5000
    assert freshness["p99"] == 5000


def test_summary_fails_visible_on_sequence_gap_and_timestamp_inversion():
    module = load_capture_module()
    rows = [make_row(1), make_row(3)]
    rows[1]["ap_publish_us"] = rows[1]["newest_sample_estimate_us"] - 1
    summary = module.summarise_rows(rows, {}, 12800, 96, 3)
    assert summary["capture_sequence_gap_count"] == 1
    assert summary["timestamp_order_failure_count"] == 1
