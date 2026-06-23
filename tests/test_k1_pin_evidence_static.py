import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
DIAG_H = (FW / "diag" / "diagnostic_capture.h").read_text(encoding="utf-8")
DIAG_CPP = (FW / "diag" / "diagnostic_capture.cpp").read_text(encoding="utf-8")
PIN_H = FW / "diag" / "k1_pin_evidence.h"
PIN_CPP = FW / "diag" / "k1_pin_evidence.cpp"
INO = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text(encoding="utf-8")
SERIAL = (FW / "serial" / "serial_menu.h").read_text(encoding="utf-8")
VPAB = (FW / "diag" / "vpab_capture.cpp").read_text(encoding="utf-8")
CONSTANTS = (FW / "system" / "constants.h").read_text(encoding="utf-8")


def section(name):
    pattern = re.compile(rf"(?ms)^\[{re.escape(name)}\]\s*(.*?)(?=^\[|\Z)")
    match = pattern.search(PLATFORMIO)
    assert match is not None, f"missing PlatformIO section {name}"
    return match.group(1)


class K1PinEvidenceStaticTest(unittest.TestCase):
    def test_non_shippable_harness_owns_flag_and_source(self):
        production = section("env:k1_hardware")
        harness = section("env:k1_hardware_harness")

        self.assertNotIn("K1_PIN_EVIDENCE_V1", production)
        self.assertNotIn("k1_pin_evidence.cpp", production)
        self.assertIn("-DK1_PIN_EVIDENCE_V1", harness)
        self.assertIn("+<diag/k1_pin_evidence.cpp>", harness)
        self.assertIn("NON-SHIPPABLE", harness)

    def test_payload_kind_and_schema_are_registered(self):
        self.assertIn("DIAG_KIND_K1_PIN_EVIDENCE = 4", DIAG_H)
        self.assertIn('case DIAG_KIND_K1_PIN_EVIDENCE: return "k1_pin_evidence";', DIAG_CPP)
        self.assertIn("#define K1_PIN_EVIDENCE_PAYLOAD_VERSION 1", CONSTANTS)

    def test_header_declares_fixed_payload_without_legacy_prefix(self):
        text = PIN_H.read_text(encoding="utf-8")
        self.assertIn("struct K1PinEvidencePayload", text)
        self.assertIn("static_assert(sizeof(K1PinEvidencePayload) <= DIAG_CAPTURE_MAX_PAYLOAD_BYTES", text)
        self.assertIn("void k1_pin_evidence_set_ap_metrics", text)
        self.assertIn("void k1_pin_evidence_push_frame", text)
        self.assertNotIn("SB_PIN", text)
        self.assertNotIn("SB_LOUD", text)

    def test_render_reachable_push_has_no_serial_heap_or_delay(self):
        text = PIN_CPP.read_text(encoding="utf-8")
        start = text.index("static void k1_pin_push_channel(")
        body = text[start:text.index("\n}", start)]
        forbidden = (
            "USBSerial",
            "Serial.",
            "String",
            "std::string",
            "std::vector",
            "malloc(",
            "calloc(",
            "realloc(",
            "free(",
            "new ",
            "delete ",
            "delay(",
            "vTaskDelay(",
        )
        failures = [token for token in forbidden if token in body]
        self.assertEqual(failures, [])
        self.assertIn("diag_capture_can_push(sizeof(k1_pin_evidence_scratch))", body)
        self.assertIn("diag_capture_try_push(DIAG_KIND_K1_PIN_EVIDENCE", body)

    def test_ap_and_vp_paths_feed_the_same_evidence_payload(self):
        self.assertIn("k1_pin_evidence_set_ap_metrics(t_now);", INO)
        self.assertIn("k1_pin_evidence_push_frame(frame, now_us);", VPAB)
        self.assertLess(
            INO.index("process_GDFT();"),
            INO.index("k1_pin_evidence_set_ap_metrics(t_now);"),
        )

    def test_serial_command_is_harness_guarded(self):
        self.assertRegex(
            SERIAL,
            r'(?s)#ifdef\s+K1_PIN_EVIDENCE_V1\s*\n.*?else if \(strcmp\(command_type, "k1_pin_evidence"\) == 0\).*?#endif',
        )


if __name__ == "__main__":
    unittest.main()
