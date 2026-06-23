import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "smart_auto_product_ab_capture.py"


def load_module():
    spec = importlib.util.spec_from_file_location("smart_auto_product_ab_capture", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SmartAutoProductABCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = load_module()

    def test_default_devices_follow_current_bench_assignment(self):
        devices = self.capture.default_devices()
        self.assertEqual(devices[0]["name"], "main-k1v2")
        self.assertEqual(devices[0]["port"], "/dev/tty.usbmodem12201")
        self.assertEqual(devices[0]["scene"], "l1")
        self.assertEqual(devices[1]["name"], "bench-k1-2nd")
        self.assertEqual(devices[1]["port"], "/dev/tty.usbmodem1401")
        self.assertEqual(devices[1]["scene"], "auto")

    def test_commands_never_include_calibration_or_destructive_operations(self):
        commands = self.capture.commands_for_scene("auto")
        joined = "\n".join(commands)
        forbidden = (
            "start_noise_cal",
            "noise_cal",
            "erase",
            "factory_reset",
            "restore_defaults",
            "reset=CONFIRM",
        )
        hits = [token for token in forbidden if token in joined]
        self.assertEqual(hits, [])
        self.assertIn(":smart_scene=auto", commands)
        self.assertIn(":ap_stream=on", commands)
        self.assertIn(":vp_stream=on", commands)

    def test_parse_identity_extracts_version_and_chip_id(self):
        lines = [
            "[1.0] sbr{{",
            "[1.0] VERSION: 40103",
            "[1.0] }}",
            "[1.5] sbr{{",
            "[1.5] F887A500",
            "[1.5] }}",
        ]
        identity = self.capture.extract_identity(lines)
        self.assertEqual(identity["version"], "40103")
        self.assertEqual(identity["chip_id"], "F887A500")

    def test_clip_definitions_are_the_product_ab_corpus(self):
        clips = self.capture.default_clips()
        self.assertEqual([clip["id"] for clip in clips], [
            "steady-groove",
            "kick-drop-heavy",
            "sparse-breakdown-build",
        ])
        self.assertEqual(clips[0]["start"], 125)
        self.assertEqual(clips[1]["start"], 75)
        self.assertEqual(clips[2]["start"], 20)
        self.assertTrue(all(clip["duration"] == 25 for clip in clips))

    def test_load_clip_manifest_accepts_custom_clip_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = Path(tmpdir) / "clip.mp3"
            audio.write_bytes(b"not-real-audio")
            manifest = Path(tmpdir) / "clips.json"
            manifest.write_text(json.dumps({
                "clips": [
                    {
                        "id": "custom-steady",
                        "track": "clip.mp3",
                        "path": str(audio),
                        "start": 12,
                        "duration": 20,
                        "coverage": "steady groove",
                    }
                ]
            }), encoding="utf-8")

            clips = self.capture.load_clip_manifest(manifest)

        self.assertEqual(clips[0]["id"], "custom-steady")
        self.assertEqual(clips[0]["start"], 12.0)
        self.assertEqual(clips[0]["duration"], 20.0)
        self.assertEqual(clips[0]["coverage"], "steady groove")

    def test_load_clip_manifest_rejects_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "clips.json"
            manifest.write_text(json.dumps({"clips": [{"id": "bad"}]}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing required fields"):
                self.capture.load_clip_manifest(manifest)

    def test_finish_video_capture_kills_process_after_repeated_timeout(self):
        class StuckProcess:
            def __init__(self):
                self.returncode = -9
                self.terminated = False
                self.killed = False
                self.calls = 0

            def communicate(self, timeout=None):
                self.calls += 1
                if self.calls < 3:
                    raise subprocess.TimeoutExpired(["ffmpeg"], timeout)
                return ("", "forced kill")

            def terminate(self):
                self.terminated = True

            def kill(self):
                self.killed = True

        proc = StuckProcess()
        stdout, stderr, killed = self.capture.finish_video_capture(proc, timeout=0.01)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "forced kill")
        self.assertTrue(killed)
        self.assertTrue(proc.terminated)
        self.assertTrue(proc.killed)


if __name__ == "__main__":
    unittest.main()
