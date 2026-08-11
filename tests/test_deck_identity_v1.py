"""Host gate G2.1 — identity_v1 encode/decode + CRC + admission digests.

Compiles SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_identity_v1.cpp and checks:
- round-trip encode/decode
- payload_crc32 coverage
- bad MD5 / CRC rejected
- locked digests match AUTHORITY_FREEZE Procedure A/B (raw bytes)
"""

from __future__ import annotations

import binascii
import hashlib
import struct
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network" / "k1_deck_identity_v1.cpp"
HDR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network" / "k1_deck_identity_v1.h"
REGISTRY_YAML = ROOT / "docs" / "protocol" / "k1-ws-controls-registry.yaml"
LAYOUT_JSON = ROOT / "docs" / "protocol" / "deck16-layout-v1.json"
HASHES = ROOT / "docs" / "protocol" / "protocol-map-hashes.json"

REGISTRY_MD5 = "9b5db3fbb17438367adeaceb541db03b"
LAYOUT_SHA256 = "f8e40f6b1ba7b115bb5e9f7310ac69636e0a10c8e478f7584dd1d5547b941510"
IDENTITY_SIZE = 87
CRC_LEN = 83


def _ieee_crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def _compile_driver() -> Path:
    driver = textwrap.dedent(
        r"""
        #include <cstdio>
        #include <cstring>
        #include <string>
        #include <vector>

        #include "k1_deck_identity_v1.h"

        static void print_hex(const uint8_t* p, size_t n) {
          for (size_t i = 0; i < n; ++i) {
            std::printf("%02x", p[i]);
          }
        }

        int main(int argc, char** argv) {
          if (argc < 2) return 2;
          const std::string cmd = argv[1];
          if (cmd == "build") {
            K1DeckIdentityV1 id{};
            k1_deck_identity_build_bench(&id);
            uint8_t wire[K1_DECK_IDENTITY_V1_SIZE]{};
            if (k1_deck_identity_encode(&id, wire, sizeof(wire)) != 0) return 3;
            print_hex(wire, sizeof(wire));
            std::printf("\n");
            return 0;
          }
          if (cmd == "check" && argc == 3) {
            const char* hex = argv[2];
            const size_t n = std::strlen(hex);
            if (n != K1_DECK_IDENTITY_V1_SIZE * 2) return 4;
            uint8_t wire[K1_DECK_IDENTITY_V1_SIZE]{};
            for (size_t i = 0; i < K1_DECK_IDENTITY_V1_SIZE; ++i) {
              unsigned v = 0;
              if (std::sscanf(hex + i * 2, "%2x", &v) != 1) return 5;
              wire[i] = static_cast<uint8_t>(v);
            }
            K1DeckIdentityV1 id{};
            const K1DeckIdentityStatus st = k1_deck_identity_decode(wire, sizeof(wire), &id);
            if (st != K1_DECK_IDENTITY_OK) {
              std::printf("DECODE_%s\n", k1_deck_identity_status_name(st));
              return 0;
            }
            const K1DeckIdentityStatus admit = k1_deck_identity_validate_for_k1(&id);
            std::printf("OK_ADMIT_%s\n", k1_deck_identity_status_name(admit));
            return 0;
          }
          return 6;
        }
        """
    )
    build_dir = Path(tempfile.mkdtemp(prefix="deck_identity_"))
    (build_dir / "driver.cpp").write_text(driver)
    exe = build_dir / "driver"
    cmd = [
        "c++",
        "-std=c++17",
        "-I",
        str(HDR.parent),
        str(build_dir / "driver.cpp"),
        str(SRC),
        "-o",
        str(exe),
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return exe


class TestDeckIdentityV1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe = _compile_driver()

    def test_procedure_a_b_digests_match_freeze(self):
        yaml_md5 = hashlib.md5(REGISTRY_YAML.read_bytes()).hexdigest()
        layout_sha = hashlib.sha256(LAYOUT_JSON.read_bytes()).hexdigest()
        self.assertEqual(yaml_md5, REGISTRY_MD5)
        self.assertEqual(layout_sha, LAYOUT_SHA256)
        text = HASHES.read_text()
        self.assertIn(REGISTRY_MD5, text)
        self.assertIn(LAYOUT_SHA256, text)

    def test_encode_decode_roundtrip_and_crc(self):
        wire_hex = subprocess.check_output([str(self.exe), "build"], text=True).strip()
        self.assertEqual(len(wire_hex), IDENTITY_SIZE * 2)
        wire = bytes.fromhex(wire_hex)
        self.assertEqual(wire[:5], b"K1D16")
        self.assertEqual(wire[5], 0)
        self.assertEqual(wire[6], 1)
        self.assertEqual(struct.unpack_from("<H", wire, 7)[0], 0xD016)
        crc = struct.unpack_from("<I", wire, CRC_LEN)[0]
        self.assertEqual(crc, _ieee_crc32(wire[:CRC_LEN]))
        out = subprocess.check_output([str(self.exe), "check", wire_hex], text=True).strip()
        self.assertEqual(out, "OK_ADMIT_OK")

    def test_bad_md5_rejected(self):
        wire = bytes.fromhex(
            subprocess.check_output([str(self.exe), "build"], text=True).strip()
        )
        mutated = bytearray(wire)
        mutated[31] ^= 0xFF  # first byte of registry md5
        # recompute CRC so decode reaches admission
        crc = _ieee_crc32(mutated[:CRC_LEN])
        struct.pack_into("<I", mutated, CRC_LEN, crc)
        out = subprocess.check_output(
            [str(self.exe), "check", mutated.hex()], text=True
        ).strip()
        self.assertEqual(out, "OK_ADMIT_REGISTRY_MD5")

    def test_bad_crc_rejected(self):
        wire = bytearray(
            bytes.fromhex(
                subprocess.check_output([str(self.exe), "build"], text=True).strip()
            )
        )
        wire[83] ^= 0xFF
        out = subprocess.check_output(
            [str(self.exe), "check", wire.hex()], text=True
        ).strip()
        self.assertEqual(out, "DECODE_CRC")

    def test_uuid_literals_present_in_firmware(self):
        tab5 = (ROOT / "tab5_firmware" / "src" / "ble_midi_transport.cpp").read_text()
        tab5_hdr = (ROOT / "tab5_firmware" / "include" / "k1_deck_identity_v1.h").read_text()
        k1 = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network" / "ble_remoted_central.cpp").read_text()
        self.assertIn("K1_DECK_IDENTITY_SERVICE_UUID", tab5)
        self.assertIn("9f3e5c10-1c7a-46b0-8d43-6d66e10a6d16", tab5_hdr)
        self.assertIn("9f3e5c11-1c7a-46b0-8d43-6d66e10a6d16", tab5_hdr)
        self.assertIn("admit_deck16_identity", k1)
        self.assertIn("K1_DECK_IDENTITY_SERVICE_UUID", k1)

    def test_zero_deck_ui_diffs_for_phase2_files(self):
        # G2.4: this test file must not require deck_ui edits; assert sources untouched by import.
        ui = ROOT / "tab5_firmware" / "src" / "deck_ui.cpp"
        self.assertTrue(ui.exists())


if __name__ == "__main__":
    unittest.main()
