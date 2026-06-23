import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpab_semantic_presentation.py"
FRAMES = ROOT / "docs" / "forensics" / "runtime-evidence" / "2026-06-07-vpab-frame-mode18-1401-music.frames.log"
RAW = ROOT / "docs" / "forensics" / "runtime-evidence" / "2026-06-07-vpab-frame-mode18-1401-music.raw.log"
GATE = ROOT / "docs" / "forensics" / "runtime-evidence" / "2026-06-07-vpab-frame-mode18-1401-music.frame-gate.json"


spec = importlib.util.spec_from_file_location("vpab_semantic_presentation", SCRIPT)
vpab_semantic_presentation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpab_semantic_presentation)


class VPABSemanticPresentationTest(unittest.TestCase):
    def test_actual_music_capture_decodes_expected_payload_counts(self):
        frames_text = FRAMES.read_text(encoding="utf-8", errors="replace")
        gate, records = vpab_semantic_presentation.assemble_payloads(frames_text)
        metrics, bytes_rows = vpab_semantic_presentation.decode_records(records)

        self.assertTrue(gate["passed"], gate)
        self.assertEqual(gate["counts"]["records"], 44)
        self.assertEqual(len(metrics), 22)
        self.assertEqual(len(bytes_rows), 22)
        self.assertEqual(
            {"primary": 11, "secondary": 11},
            {
                channel: len([row for row in bytes_rows if row["channel"] == channel])
                for channel in ("primary", "secondary")
            },
        )

    def test_metric_and_byte_payload_schema_matches_capture(self):
        frames_text = FRAMES.read_text(encoding="utf-8", errors="replace")
        _, records = vpab_semantic_presentation.assemble_payloads(frames_text)
        metrics, bytes_rows = vpab_semantic_presentation.decode_records(records)

        first_metric = metrics[0]
        self.assertEqual(first_metric["channel"], "primary")
        self.assertEqual(first_metric["mode"], 18)
        self.assertEqual(first_metric["leds"], 160)
        self.assertEqual(first_metric["mae8"], 0.0)

        first_bytes = bytes_rows[0]
        self.assertEqual(first_bytes["channel"], "primary")
        self.assertEqual(first_bytes["mode"], 18)
        self.assertEqual(first_bytes["leds"], 160)
        self.assertEqual(first_bytes["byte_count"], 480)
        self.assertGreater(first_bytes["energy"], 0)

    def test_summary_preserves_evidence_boundary(self):
        built = vpab_semantic_presentation.build(
            {"frames": FRAMES, "raw": RAW, "gate": GATE}
        )
        summary = built["summary"]

        self.assertEqual(summary["gate"]["result"], "PASS")
        self.assertIn("framed VPAB transport integrity", summary["source_boundary"]["proves"])
        self.assertIn("current-vs-VME final-byte equivalence", summary["source_boundary"]["does_not_prove"])
        self.assertEqual(summary["payload_counts"]["samples_per_channel"]["primary"], 11)
        self.assertEqual(summary["payload_counts"]["samples_per_channel"]["secondary"], 11)

    def test_html_presentation_contains_scalar_maps_and_waterfall(self):
        built = vpab_semantic_presentation.build(
            {"frames": FRAMES, "raw": RAW, "gate": GATE}
        )
        html = vpab_semantic_presentation.render_html(
            built["summary"],
            built["bytes_rows"],
            {"frames": FRAMES, "raw": RAW, "gate": GATE},
        )

        self.assertIn("data-map=\"inferno\"", html)
        self.assertIn("data-map=\"viridis\"", html)
        self.assertIn("Final-Byte Waterfall", html)
        self.assertIn("display-interpolated line strips", html)
        self.assertIn("not raw audio spectrograms", html)
        self.assertIn("github.com/RaidenIV/3D-Spectrogram", html)


if __name__ == "__main__":
    unittest.main()
