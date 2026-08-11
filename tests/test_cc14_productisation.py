"""Host gates G3.1–G3.3 — CC14 50 ms pairing + malformed_cc14.

Uses the firmware decoder TU (same path as test_ble_midi_firmware_decoder).
"""

from __future__ import annotations

import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECODER_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network" / "k1_ble_midi_decoder.cpp"
NETWORK = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network"


def _compile() -> Path:
    driver = textwrap.dedent(
        r"""
        #include <cstdio>
        #include <cstdlib>
        #include <cstring>
        #include <string>
        #include <vector>

        #include "k1_ble_midi_decoder.h"

        static std::vector<uint8_t> parse_hex_line(const char* line) {
          std::vector<uint8_t> out;
          const char* p = line;
          while (*p) {
            while (*p == ' ') ++p;
            if (!*p) break;
            unsigned v = 0;
            if (std::sscanf(p, "%2x", &v) != 1) break;
            out.push_back(static_cast<uint8_t>(v));
            p += 2;
          }
          return out;
        }

        int main() {
          K1BleMidiDecoderState state;
          k1_ble_midi_decoder_reset(&state);
          char line[512];
          while (std::fgets(line, sizeof(line), stdin)) {
            if (line[0] == '#') continue;
            if (std::strncmp(line, "NOW ", 4) == 0) {
              k1_ble_midi_decoder_set_now_ms(&state, static_cast<uint32_t>(std::strtoul(line + 4, nullptr, 10)));
              continue;
            }
            if (std::strncmp(line, "RESET", 5) == 0) {
              k1_ble_midi_decoder_reset(&state);
              continue;
            }
            // BLE-MIDI packet: header 80 80 + MIDI bytes
            auto body = parse_hex_line(line);
            std::vector<uint8_t> packet = {0x80, 0x80};
            packet.insert(packet.end(), body.begin(), body.end());
            K1WirelessControlRecord records[K1_BLE_MIDI_MAX_RECORDS_PER_PACKET];
            size_t count = 0;
            const auto st = k1_ble_midi_decode_packet(
                &state, packet.data(), packet.size(), records,
                K1_BLE_MIDI_MAX_RECORDS_PER_PACKET, &count);
            std::printf("%s|%zu|malformed=%lu",
                        k1_ble_midi_decode_status_name(st), count,
                        static_cast<unsigned long>(k1_ble_midi_decoder_malformed_cc14(&state)));
            for (size_t i = 0; i < count; ++i) {
              std::printf("|%s", records[i].control);
            }
            std::printf("\n");
          }
          return 0;
        }
        """
    )
    build = Path(tempfile.mkdtemp(prefix="cc14_"))
    (build / "driver.cpp").write_text(driver)
    exe = build / "driver"
    subprocess.check_call(
        [
            "c++",
            "-std=c++17",
            "-I",
            str(NETWORK),
            "-I",
            str(ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control"),
            str(build / "driver.cpp"),
            str(DECODER_CPP),
            "-o",
            str(exe),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return exe


def _run(exe: Path, script: str) -> list[str]:
    out = subprocess.check_output([str(exe)], input=script, text=True)
    return [ln for ln in out.splitlines() if ln.strip()]


class TestCc14Productisation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exe = _compile()

    def test_msb_only_no_emit_no_malformed(self):
        # primary.photons = ch0 CC MSB 1 / LSB 33
        lines = _run(self.exe, "NOW 1000\nB0 01 40\n")
        self.assertEqual(lines[-1], "OK|0|malformed=0")

    def test_full_pair_one_emit(self):
        lines = _run(self.exe, "NOW 1000\nB0 01 40\nB0 21 00\n")
        self.assertTrue(lines[-1].startswith("OK|1|malformed=0|primary.photons"))

    def test_lsb_without_msb_malformed(self):
        lines = _run(self.exe, "NOW 1000\nB0 21 00\n")
        self.assertEqual(lines[-1], "OK|0|malformed=1")

    def test_expired_msb_malformed(self):
        lines = _run(
            self.exe,
            "NOW 1000\nB0 01 40\nNOW 1051\nB0 21 00\n",
        )
        self.assertEqual(lines[-1], "OK|0|malformed=1")

    def test_within_window_ok(self):
        lines = _run(
            self.exe,
            "NOW 1000\nB0 01 40\nNOW 1050\nB0 21 00\n",
        )
        self.assertTrue(lines[-1].startswith("OK|1|malformed=0|primary.photons"))

    def test_second_msb_replaces(self):
        lines = _run(
            self.exe,
            "NOW 1000\nB0 01 10\nNOW 1010\nB0 01 7F\nB0 21 7F\n",
        )
        self.assertTrue(lines[-1].startswith("OK|1|malformed=0|primary.photons"))

    def test_packet_boundary_accumulation(self):
        lines = _run(self.exe, "NOW 2000\nB0 01 20\nNOW 2010\nB0 21 10\n")
        self.assertTrue(lines[-1].startswith("OK|1|malformed=0|primary.photons"))

    def test_expiry_constant_is_50ms(self):
        hdr = (NETWORK / "k1_ble_midi_decoder.h").read_text()
        self.assertIn("K1_BLE_MIDI_CC14_PAIR_EXPIRY_MS 50u", hdr)


if __name__ == "__main__":
    unittest.main()
