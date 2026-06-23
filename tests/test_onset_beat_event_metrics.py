import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "onset_beat_event_metrics.py"


def load_metrics():
    spec = importlib.util.spec_from_file_location("onset_beat_event_metrics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def smart_block(event_id, age_ms, onset, bass_onset, confidence):
    return "\n".join(
        (
            "sbr{{",
            f"SMART_EVENT_ID: {event_id}",
            f"SMART_EVENT_AGE_MS: {age_ms}",
            f"SMART_ONSET: {onset}",
            f"SMART_BASS_ONSET: {bass_onset}",
            f"SMART_BEAT_CONFIDENCE: {confidence:.3f}",
            "}}",
        )
    )


class OnsetBeatEventMetricsTest(unittest.TestCase):
    def test_summarises_event_rate_age_and_confidence_from_smart_snapshots(self):
        metrics = load_metrics()
        text = "\n".join(
            (
                "#LEG music",
                "VPABB,ver=1,seq=1,t_ms=0,channel=primary",
                smart_block(0, 0, 0, 0, 0.0),
                smart_block(1, 10, 1, 0, 0.100),
                smart_block(2, 20, 0, 1, 0.200),
                smart_block(3, 30, 1, 0, 0.300),
                smart_block(4, 40, 0, 1, 0.400),
                smart_block(5, 50, 1, 0, 0.500),
                "VPABB,ver=1,seq=2,t_ms=60000,channel=primary",
            )
        )

        summary = metrics.summarise_text(text)

        self.assertTrue(summary["capture_valid"])
        self.assertEqual(summary["event_count_delta"], 5)
        self.assertEqual(summary["observed_event_snapshots"], 5)
        self.assertEqual(summary["events_per_min"], 5.0)
        self.assertEqual(summary["event_age_ms"]["p50"], 30)
        self.assertEqual(summary["event_age_ms"]["p95"], 50)
        self.assertAlmostEqual(summary["beat_confidence"]["mean"], 0.3)
        self.assertEqual(summary["beat_confidence"]["max"], 0.5)
        self.assertFalse(summary["event_storm"]["triggered"])

    def test_missing_required_smart_field_invalidates_capture(self):
        metrics = load_metrics()
        text = "\n".join(
            (
                "#LEG music",
                "SMART_EVENT_ID: 1",
                "SMART_EVENT_AGE_MS: 12",
                "SMART_ONSET: 1",
                "SMART_BEAT_CONFIDENCE: 0.250",
                "}}",
            )
        )

        summary = metrics.summarise_text(text)

        self.assertFalse(summary["capture_valid"])
        self.assertEqual(summary["missing_required_fields"], ["SMART_BASS_ONSET"])
        self.assertEqual(summary["snapshots_with_missing_required_fields"][0]["line"], 2)
        self.assertIn("missing required SMART fields", summary["invalidation_reasons"])

    def test_flags_false_events_in_marked_silence_or_control_windows_and_storms(self):
        metrics = load_metrics()
        text = "\n".join(
            (
                "#LEG music",
                "VPABB,ver=1,seq=1,t_ms=0,channel=primary",
                smart_block(0, 0, 0, 0, 0.0),
                "#LEG silence_control",
                smart_block(1, 10, 1, 0, 0.100),
                smart_block(2, 10, 1, 0, 0.100),
                smart_block(3, 10, 1, 0, 0.100),
                smart_block(4, 10, 1, 0, 0.100),
                smart_block(5, 10, 1, 0, 0.100),
                "VPABB,ver=1,seq=2,t_ms=1000,channel=primary",
            )
        )

        summary = metrics.summarise_text(text)

        self.assertEqual(summary["false_events"]["windows_present"], True)
        self.assertEqual(summary["false_events"]["count"], 5)
        self.assertEqual(summary["false_events"]["by_window"], {"silence_control": 5})
        self.assertTrue(summary["event_storm"]["triggered"])
        self.assertEqual(summary["event_storm"]["threshold_events_per_min"], 240.0)
        self.assertEqual(summary["events_per_min"], 300.0)

    def test_cli_writes_json_and_returns_nonzero_for_invalid_capture(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "capture.log"
            out_path = Path(tmpdir) / "summary.json"
            log_path.write_text(
                "\n".join(
                    (
                        "SMART_EVENT_ID: 1",
                        "SMART_EVENT_AGE_MS: 12",
                        "SMART_ONSET: 1",
                        "SMART_BEAT_CONFIDENCE: 0.250",
                        "}}",
                    )
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(log_path), "--out", str(out_path)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 2, result.stderr)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertFalse(payload["capture_valid"])
            self.assertEqual(payload["missing_required_fields"], ["SMART_BASS_ONSET"])


if __name__ == "__main__":
    unittest.main()
