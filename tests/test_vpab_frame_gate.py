import binascii
import importlib.util
import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "vpab_frame_gate.py"
CAPTURE_SCRIPT = ROOT / "scripts" / "regression-harness" / "vpab_frame_capture.py"

spec = importlib.util.spec_from_file_location("vpab_frame_gate", SCRIPT)
vpab_frame_gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vpab_frame_gate)


def crc32(data):
    return binascii.crc32(data) & 0xFFFFFFFF


def frame_log(records, dropped=0, corrupt=0, overflowed=0):
    lines = [
        "K1DF_BEGIN,ver=1,records=%d,captured=%d,dropped=%d,corrupt=%d,overflowed=%d,payload_max=512,chunk_bytes=96"
        % (len(records), len(records), dropped, corrupt, overflowed)
    ]
    total_chunks = 0
    for seq, kind, frame, payload in records:
        chunk_size = 4
        chunks = [payload[i:i + chunk_size] for i in range(0, len(payload), chunk_size)]
        lines.append(
            "K1DFR,ver=1,seq=%d,kind=%d,frame=%d,t_us=%d,flags=0,len=%d,crc=0x%08X,chunks=%d"
            % (seq, kind, frame, 1000 + frame, len(payload), crc32(payload), len(chunks))
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
        "K1DF_END,ver=1,records=%d,chunks=%d,dropped=%d,corrupt=%d,overflowed=%d"
        % (len(records), total_chunks, dropped, corrupt, overflowed)
    )
    return "\n".join(lines) + "\n"


class VPABFrameGateTest(unittest.TestCase):
    def test_valid_framed_stream_passes_with_coverage(self):
        text = frame_log(
            [
                (1, 1, 1, bytes([0, 7, 0, 0, 1, 2, 3])),
                (2, 2, 1, bytes([1, 18, 9, 8, 7, 6, 5, 4, 3])),
            ]
        )
        result = vpab_frame_gate.evaluate_text(
            text,
            require_modes={7, 18},
            require_channels={"primary", "secondary"},
            require_kinds={"vpab_metrics", "vpab_bytes"},
        )
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["counts"]["assembled_records"], 2)

    def test_k1_pin_payload_coverage_uses_version_channel_mode_schema(self):
        payload = struct.pack("<BBH", 1, 0, 18) + bytes(78)
        text = frame_log([(1, 4, 12, payload)])
        result = vpab_frame_gate.evaluate_text(
            text,
            require_modes={18},
            require_channels={"primary"},
            require_kinds={"k1_pin_evidence"},
        )
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["coverage"]["records"][0]["channel"], "primary")
        self.assertEqual(result["coverage"]["records"][0]["mode"], 18)

    def test_suffix_fragment_fails_closed(self):
        text = frame_log([(1, 1, 1, bytes([0, 18, 1, 2]))])
        result = vpab_frame_gate.evaluate_text(text.replace("K1DFC", "vu=0.1\nK1DFC", 1))
        self.assertFalse(result["passed"])
        self.assertGreater(result["counts"]["issues"], 0)

    def test_truncated_chunk_fails_closed(self):
        text = frame_log([(1, 1, 1, bytes([0, 18, 1, 2, 3, 4]))])
        text = text.replace("hex=00120102", "hex=001201", 1)
        result = vpab_frame_gate.evaluate_text(text)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["field"] in {"len", "crc"} for item in result["issues"]))

    def test_record_crc_mismatch_fails_closed(self):
        text = frame_log([(1, 1, 1, bytes([0, 18, 1, 2, 3, 4]))])
        text = text.replace("crc=0x%08X" % crc32(bytes([0, 18, 1, 2, 3, 4])), "crc=0x00000000", 1)
        result = vpab_frame_gate.evaluate_text(text)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["metric"] == "crc" for item in result["failures"]))

    def test_sequence_gap_fails_closed(self):
        text = frame_log(
            [
                (1, 1, 1, bytes([0, 18, 1, 2])),
                (3, 1, 2, bytes([1, 18, 3, 4])),
            ]
        )
        result = vpab_frame_gate.evaluate_text(text)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["metric"] == "seq" for item in result["failures"]))

    def test_diag_drop_counter_fails_closed(self):
        text = frame_log([(1, 1, 1, bytes([0, 18, 1, 2]))], dropped=1)
        result = vpab_frame_gate.evaluate_text(text)
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["metric"] == "dropped" for item in result["failures"]))

    def test_missing_required_channel_fails(self):
        text = frame_log([(1, 1, 1, bytes([0, 18, 1, 2]))])
        result = vpab_frame_gate.evaluate_text(text, require_channels={"primary", "secondary"})
        self.assertFalse(result["passed"])
        self.assertTrue(any(item["metric"] == "coverage.channel" for item in result["failures"]))

    def test_cli_returns_two_on_failed_gate(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "-", "--require-channel", "secondary"],
            input=frame_log([(1, 1, 1, bytes([0, 18, 1, 2]))]),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)

    def test_capture_runner_uses_framed_dump_and_no_calibration_commands(self):
        text = CAPTURE_SCRIPT.read_text()
        self.assertIn('":vpab=frames"', text)
        self.assertIn('":chip_id"', text)
        self.assertIn('":smart_scene=off"', text)
        self.assertNotIn("start_noise_cal", text)
        self.assertNotIn("clear_noise_cal", text)
        self.assertNotIn("factory_reset", text)
        self.assertNotIn("restore_defaults", text)


if __name__ == "__main__":
    unittest.main()
