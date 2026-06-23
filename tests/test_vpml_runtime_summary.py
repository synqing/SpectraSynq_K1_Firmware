import binascii
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpml_runtime_summary.py"

spec = importlib.util.spec_from_file_location("vpml_runtime_summary", SCRIPT)
vpml_runtime_summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpml_runtime_summary)


def crc32(data):
    return binascii.crc32(data) & 0xFFFFFFFF


def vpab_bytes_payload(channel, mode=250, lit=True, over=0, dropped=0):
    payload = bytearray(512)
    payload[0] = channel
    payload[1] = mode
    payload[2] = 2
    payload[3] = 0
    payload[4:6] = (160).to_bytes(2, "little")
    payload[6:8] = (480).to_bytes(2, "little")
    payload[8:12] = (320).to_bytes(4, "little")
    payload[12:16] = (24).to_bytes(4, "little")
    payload[16:20] = (3920).to_bytes(4, "little")
    payload[20:24] = (3380).to_bytes(4, "little")
    payload[24:28] = over.to_bytes(4, "little")
    payload[28:32] = dropped.to_bytes(4, "little")
    if lit:
        for index in range(32, 512, 9):
            payload[index] = 128
            payload[index + 1] = 64
            payload[index + 2] = 8
    return bytes(payload)


def frame_log(records):
    lines = [
        "K1DF_BEGIN,ver=1,records=%d,captured=%d,dropped=0,corrupt=0,overflowed=0,payload_max=512,chunk_bytes=96"
        % (len(records), len(records))
    ]
    total_chunks = 0
    for seq, frame, payload in records:
        chunks = [payload[index:index + 96] for index in range(0, len(payload), 96)]
        lines.append(
            "K1DFR,ver=1,seq=%d,kind=2,frame=%d,t_us=%d,flags=0,len=%d,crc=0x%08X,chunks=%d"
            % (seq, frame, 100000 + frame, len(payload), crc32(payload), len(chunks))
        )
        offset = 0
        for index, chunk in enumerate(chunks):
            lines.append(
                "K1DFC,ver=1,seq=%d,idx=%d,off=%d,len=%d,crc=0x%08X,hex=%s"
                % (seq, index, offset, len(chunk), crc32(chunk), chunk.hex().upper())
            )
            offset += len(chunk)
            total_chunks += 1
    lines.append(
        "K1DF_END,ver=1,records=%d,chunks=%d,dropped=0,corrupt=0,overflowed=0"
        % (len(records), total_chunks)
    )
    return "\n".join(lines) + "\n"


class VPMLRuntimeSummaryTest(unittest.TestCase):
    def test_valid_dual_channel_byte_capture_passes(self):
        text = frame_log(
            [
                (1, 20, vpab_bytes_payload(0)),
                (2, 20, vpab_bytes_payload(1)),
            ]
        )
        result = vpml_runtime_summary.evaluate_text(text, require_mode=250)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["decoded_vpab_bytes"]["channel_counts"], {"primary": 1, "secondary": 1})
        self.assertEqual(result["decoded_vpab_bytes"]["mode_counts"], {"250": 2})
        self.assertEqual(result["decoded_vpab_bytes"]["dark_sample_records"], [])

    def test_dark_sample_is_observation_by_default(self):
        text = frame_log(
            [
                (1, 20, vpab_bytes_payload(0, lit=False)),
                (2, 20, vpab_bytes_payload(1, lit=False)),
                (3, 40, vpab_bytes_payload(0)),
                (4, 40, vpab_bytes_payload(1)),
            ]
        )
        result = vpml_runtime_summary.evaluate_text(text, require_mode=250)
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["decoded_vpab_bytes"]["dark_sample_records"][0]["channel"], "primary")
        self.assertEqual(result["observations"][0]["kind"], "dark_sample_records")

    def test_loop_safe_gate_can_fail_on_dark_sample(self):
        text = frame_log(
            [
                (1, 20, vpab_bytes_payload(0, lit=False)),
                (2, 20, vpab_bytes_payload(1, lit=False)),
                (3, 40, vpab_bytes_payload(0)),
                (4, 40, vpab_bytes_payload(1)),
            ]
        )
        result = vpml_runtime_summary.evaluate_text(text, require_mode=250, fail_on_dark_sample=True)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["metric"] == "dark_sample_records" for item in result["failures"]))

    def test_missing_secondary_channel_fails(self):
        text = frame_log([(1, 20, vpab_bytes_payload(0))])
        result = vpml_runtime_summary.evaluate_text(text, require_mode=250)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["metric"] == "coverage.channel" for item in result["failures"]))

    def test_cli_writes_summary_and_returns_zero(self):
        text = frame_log(
            [
                (1, 20, vpab_bytes_payload(0)),
                (2, 20, vpab_bytes_payload(1)),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            frames = Path(tmp) / "frames.log"
            out = Path(tmp) / "summary.json"
            frames.write_text(text)
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), str(frames), "--out", str(out), "--summary"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("VPML runtime summary PASS", proc.stderr)
            self.assertEqual(json.loads(out.read_text())["result"], "PASS")


if __name__ == "__main__":
    unittest.main()
