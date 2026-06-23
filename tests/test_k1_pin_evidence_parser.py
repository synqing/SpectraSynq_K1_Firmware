import binascii
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "k1_pin_evidence_summary.py"

spec = importlib.util.spec_from_file_location("k1_pin_evidence_summary", SCRIPT)
k1_pin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k1_pin)


KIND_K1_PIN = 4


def crc32(data):
    return binascii.crc32(data) & 0xFFFFFFFF


def make_pin_payload(
    *,
    spectral_saturation=0.2,
    chroma_gate=0.1,
    chroma_final=0.03,
    top_colour_dwell=0.7,
    colour_entropy=0.8,
    dba_bucket=1,
):
    return struct.pack(
        "<BBHIII"
        "HHHHHHHH"
            "HHH?B"
            "?HHBB"
            "HHHHHHHHHB"
            "HHHHHHHH",
        1,  # version
        0,  # channel
        21,  # mode
        42,  # ap_ms
        7,  # chroma_seq
        3,  # state bits: loud + vivid enabled
        1000,  # raw_peak_q
        2000,  # post_sensitivity_peak_q
        0,  # clip_count
        1,  # near_rail_count
        96,  # sample_count
        32768,  # agc_gain_q
        18000,  # agc_envelope_q
        int(spectral_saturation * 65535),
        15000,  # chroma_pre_max
        10000,  # chroma_pre_mean
        int(chroma_gate * 65535),
        0,  # agc_gated
        dba_bucket,
        True,  # held hue valid
        17000,  # held hue q
        9000,  # centroid strength
        4,  # dominant bin
        7,  # palette index
        18000,  # chroma_norm_max
        14000,  # chroma_norm_mean
        int(chroma_final * 65535),
        3000,  # chroma_final_mean
        6000,  # flatness
        50000,  # loud input trim
        40000,  # loud gdft trim
        32000,  # vivid chroma
        12000,  # vivid black
        0,  # chroma profile
        int(colour_entropy * 65535),
        int(top_colour_dwell * 65535),
        140,  # top hue
        50000,  # active led pct
        18000,  # sat avg
        3000,  # white bias avg
        33000,  # com q
        2500,  # motion delta q
    )


def frame_log(payload, dropped=0, overflowed=0):
    payload_crc = crc32(payload)
    return (
        "K1DF_BEGIN,ver=1,records=1,captured=1,dropped=%d,corrupt=0,overflowed=%d,payload_max=512,chunk_bytes=96\n"
        "K1DFR,ver=1,seq=1,kind=%d,frame=12,t_us=34000,flags=0,len=%d,crc=0x%08X,chunks=1\n"
        "K1DFC,ver=1,seq=1,idx=0,off=0,len=%d,crc=0x%08X,hex=%s\n"
        "K1DF_END,ver=1,records=1,chunks=1,dropped=%d,corrupt=0,overflowed=%d\n"
    ) % (
        dropped,
        overflowed,
        KIND_K1_PIN,
        len(payload),
        payload_crc,
        len(payload),
        payload_crc,
        payload.hex().upper(),
        dropped,
        overflowed,
    )


class K1PinEvidenceParserTest(unittest.TestCase):
    def test_valid_log_and_manifest_emit_summary(self):
        text = frame_log(make_pin_payload())
        manifest = {
            "legs": [
                {
                    "dBA_bucket": "loud_67_72",
                    "track": "test",
                    "segment": "chorus",
                    "mode": 21,
                    "guard": True,
                    "vivid": True,
                }
            ]
        }
        result = k1_pin.evaluate_capture(text, manifest)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["classification"], "MIXED_BY_CONSUMER")
        self.assertGreater(result["metrics"]["top_colour_dwell_mean"], 0.65)

    def test_missing_manual_dba_label_fails_closed(self):
        result = k1_pin.evaluate_capture(frame_log(make_pin_payload()), {"legs": []})
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("manifest requires at least one leg", "\n".join(result["issues"]))

    def test_invalid_frame_transport_fails_closed(self):
        result = k1_pin.evaluate_capture(frame_log(make_pin_payload(), dropped=1, overflowed=1), {"dBA_bucket": "normal_52_62"})
        self.assertEqual(result["result"], "FAIL")
        self.assertIn("framed diagnostic gate failed", "\n".join(result["issues"]))

    def test_cli_writes_json_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "capture.log"
            manifest_path = Path(tmp) / "manifest.json"
            output_path = Path(tmp) / "summary.json"
            log_path.write_text(frame_log(make_pin_payload()), encoding="utf-8")
            manifest_path.write_text(json.dumps({"dBA_bucket": "normal_52_62"}), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--log",
                    str(log_path),
                    "--manifest",
                    str(manifest_path),
                    "--output",
                    str(output_path),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["schema"], "k1_pin_evidence_summary.v1")


if __name__ == "__main__":
    unittest.main()
