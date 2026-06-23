import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "k1_response_normalisation_gate.py"


def load_gate():
    spec = importlib.util.spec_from_file_location("k1_response_normalisation_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ap_line(max_raw, peak_scaled, *, dc=-100, ssl=180, lock=1, conf=0.8):
    return (
        "[AP] SSL={ssl} DC={dc} max_raw={max_raw} follower={max_raw} "
        "peak_scaled={peak_scaled:.3f} silent_scale=1.000 silence=0 "
        "cal_source=measured cal_valid=1 | bpm=120.0 conf={conf:.2f} "
        "lock={lock} phase=0.20 beat=0 bstr=0.30 | onset=1 bass=0 ostr=0.25"
    ).format(ssl=ssl, dc=dc, max_raw=max_raw, peak_scaled=peak_scaled, conf=conf, lock=lock)


def write_log(path, rows):
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def tone_device(name, expected, observed, decoded, *, dc=0, ssl=180, sensitivity=2.3):
    return {
        "name": name,
        "expected_chip_id": expected,
        "observed_chip_id": observed,
        "port": f"/dev/cu.{name}",
        "dump": {
            "config": {
                "DC_OFFSET": dc,
                "SWEET_SPOT_MIN_LEVEL": ssl,
                "SAMPLE_RATE": 12800,
                "SAMPLES_PER_CHUNK": 96,
                "SENSITIVITY": sensitivity,
            },
            "decoded": decoded,
            "word_count": len(decoded),
        },
    }


def ap_device(name, expected, log_path, *, cal_source="measured", sample_rate=12800):
    return {
        "name": name,
        "expected_chip_id": expected,
        "chip_id": expected,
        "env": "k1_hardware" if name.startswith("main") else "k1_bench_reference",
        "port": f"/dev/cu.{name}",
        "log": str(log_path),
        "summary": {
            "identity": {"chip_id": expected, "version": "40103"},
            "dump": {
                "CAL_SOURCE": cal_source,
                "CAL_VALID": 1,
                "CAL_PROFILE_LOADED": 1,
                "CONFIG.SAMPLE_RATE": sample_rate,
                "CONFIG.SAMPLES_PER_CHUNK": 96,
                "CONFIG.DC_OFFSET": -100,
                "CONFIG.SWEET_SPOT_MIN_LEVEL": 180,
                "CONFIG.SENSITIVITY": 2.3,
                "AUDIO_RESPONSE_GAIN": 1.0,
            },
        },
    }


def write_runner(tmp_path, *, main_weak=True, main_cal_source="measured", main_sample_rate=12800):
    main_log = tmp_path / "main.log"
    bench_log = tmp_path / "bench.log"
    if main_weak:
        write_log(main_log, [ap_line(250, 0.30, lock=0) for _ in range(12)])
        write_log(bench_log, [ap_line(900, 0.90, lock=1) for _ in range(12)])
        main_decoded = [-10, 0, 10]
        bench_decoded = [-50, 0, 50]
    else:
        write_log(main_log, [ap_line(800, 0.80, lock=1) for _ in range(12)])
        write_log(bench_log, [ap_line(900, 0.90, lock=1) for _ in range(12)])
        main_decoded = [-45, 0, 45]
        bench_decoded = [-50, 0, 50]

    tone_manifest = tmp_path / "tone.json"
    tone_manifest.write_text(
        json.dumps(
            {
                "failure": None,
                "devices": [
                    tone_device("main-1401", "F887A500", "F887A500", main_decoded),
                    tone_device("bench-12201", "B489A500", "B489A500", bench_decoded),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    ap_manifest = tmp_path / "ap.json"
    ap_manifest.write_text(
        json.dumps(
            {
                "failure": None,
                "comparison": {"timing_parity": True},
                "devices": [
                    ap_device(
                        "main-1401",
                        "F887A500",
                        main_log,
                        cal_source=main_cal_source,
                        sample_rate=main_sample_rate,
                    ),
                    ap_device("bench-12201", "B489A500", bench_log),
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner_manifest = tmp_path / "runner.json"
    runner_manifest.write_text(
        json.dumps(
            {
                "failure": None,
                "label": "unit-test",
                "tone_manifest": str(tone_manifest),
                "ap_manifest": str(ap_manifest),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return runner_manifest


class K1ResponseNormalisationGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = load_gate()

    def test_classifies_main_response_gap_from_runner_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = write_runner(Path(tmpdir), main_weak=True)

            result = self.gate.evaluate_runner_manifest(runner)

            self.assertTrue(result["capture_valid"])
            self.assertEqual(result["decision"], "response_normalisation_required")
            self.assertLess(result["ratios"]["tone_ac_peak_to_peak"], 0.65)
            self.assertLess(result["ratios"]["ap_peak_scaled_mean"], 0.75)
            self.assertEqual(result["recommended_post_dc_gain"]["placement"], "post_dc")
            self.assertGreater(result["recommended_post_dc_gain"]["gain"], 1.0)
            self.assertLessEqual(
                result["recommended_post_dc_gain"]["gain"],
                result["thresholds"]["max_recommended_gain"],
            )
            self.assertIn("upstream of tempo lock", " ".join(result["interpretation"]))

    def test_accepts_response_parity_when_subject_tracks_reference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = write_runner(Path(tmpdir), main_weak=False)

            result = self.gate.evaluate_runner_manifest(runner)

            self.assertTrue(result["capture_valid"])
            self.assertEqual(result["decision"], "response_parity_accept")
            self.assertGreaterEqual(result["ratios"]["tone_ac_peak_to_peak"], 0.65)
            self.assertGreaterEqual(result["ratios"]["ap_peak_scaled_mean"], 0.75)
            self.assertGreaterEqual(result["recommended_post_dc_gain"]["gain"], 1.0)

    def test_invalidates_unmatched_calibration_or_timing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = write_runner(
                Path(tmpdir),
                main_weak=False,
                main_cal_source="default_invalid",
                main_sample_rate=16000,
            )

            result = self.gate.evaluate_runner_manifest(runner)

            self.assertFalse(result["capture_valid"])
            self.assertEqual(result["decision"], "invalid_capture")
            joined = "\n".join(result["hard_failures"])
            self.assertIn("calibration provenance", joined)
            self.assertIn("timing mismatch", joined)

    def test_cli_writes_json_and_markdown_and_nonzeroes_for_gap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            runner = write_runner(tmp_path, main_weak=True)
            out_json = tmp_path / "summary.json"
            out_md = tmp_path / "summary.md"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(runner),
                    "--out",
                    str(out_json),
                    "--markdown-out",
                    str(out_md),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["decision"], "response_normalisation_required")
            self.assertIn("K1 Response Normalisation Gate", out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
