"""Host gates G4.1 — K1DS packet encode/decode + HELLO session_generation."""

from __future__ import annotations

import binascii
import struct
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NETWORK = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "network"
STATE_CPP = NETWORK / "k1_deck_state_v1.cpp"
IDENTITY_CPP = NETWORK / "k1_deck_identity_v1.cpp"


def _crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def _compile() -> Path:
    driver = textwrap.dedent(
        r"""
        #include <cstdio>
        #include <cstring>
        #include "k1_deck_identity_v1.h"
        #include "k1_deck_state_v1.h"

        int main() {
          K1DeckStateHello hello{};
          hello.protocol_min = 1;
          hello.protocol_max = 1;
          hello.session_generation = 42;
          hello.short_id = K1_DECK_IDENTITY_BENCH_SHORT_ID;
          k1_deck_identity_parse_hex(K1_DECK_IDENTITY_REGISTRY_MD5_HEX, hello.ble_midi_registry_md5, 16);
          k1_deck_identity_parse_hex(K1_DECK_IDENTITY_LAYOUT_SHA256_HEX, hello.deck16_layout_sha256, 32);
          const uint8_t deck_id[16] = K1_DECK_IDENTITY_BENCH_DECK_ID_INIT;
          std::memcpy(hello.deck_id, deck_id, 16);
          uint8_t hello_payload[K1_DECK_STATE_HELLO_PAYLOAD_SIZE]{};
          if (k1_deck_state_encode_hello_payload(&hello, hello_payload, sizeof(hello_payload)) < 0) return 2;
          uint8_t packet[K1_DECK_STATE_MAX_PACKET]{};
          const int n = k1_deck_state_build_single_record_packet(
              0, 7, K1_DECK_STATE_REC_HELLO, 0, 0, hello_payload,
              K1_DECK_STATE_HELLO_PAYLOAD_SIZE, packet, sizeof(packet));
          if (n < 0) return 3;
          K1DeckStatePacketHeader hdr{};
          const uint8_t* blob = nullptr;
          size_t blob_len = 0;
          if (k1_deck_state_parse_packet(packet, static_cast<size_t>(n), &hdr, &blob, &blob_len) != K1_DECK_STATE_OK) {
            return 4;
          }
          size_t cursor = 0;
          K1DeckStateRecordView rec{};
          if (k1_deck_state_next_record(blob, blob_len, &cursor, &rec) != K1_DECK_STATE_OK) return 5;
          K1DeckStateHello decoded{};
          if (k1_deck_state_decode_hello_payload(rec.payload, rec.payload_len, &decoded) != K1_DECK_STATE_OK) return 6;
          if (decoded.session_generation != 42) return 7;
          // corrupt CRC
          packet[12] ^= 0xFF;
          const auto bad = k1_deck_state_parse_packet(packet, static_cast<size_t>(n), &hdr, &blob, &blob_len);
          std::printf("HELLO_OK session=%u crc_status=%s\n",
                      static_cast<unsigned>(decoded.session_generation),
                      k1_deck_state_status_name(bad));
          return 0;
        }
        """
    )
    build = Path(tempfile.mkdtemp(prefix="k1ds_"))
    (build / "driver.cpp").write_text(driver)
    exe = build / "driver"
    subprocess.check_call(
        [
            "c++",
            "-std=c++17",
            "-I",
            str(NETWORK),
            str(build / "driver.cpp"),
            str(STATE_CPP),
            str(IDENTITY_CPP),
            "-o",
            str(exe),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    return exe


class TestDeckStateV1(unittest.TestCase):
    def test_hello_roundtrip_and_bad_crc(self):
        exe = _compile()
        out = subprocess.check_output([str(exe)], text=True).strip()
        self.assertEqual(out, "HELLO_OK session=42 crc_status=CRC")

    def test_protocol_doc_has_session_generation(self):
        text = (ROOT / "docs" / "protocol" / "k1-deck-state-v1.md").read_text()
        self.assertIn("session_generation:u32", text)

    def test_ack_tx_hard_gated(self):
        src = (ROOT / "tab5_firmware" / "src" / "deck_state.cpp").read_text()
        self.assertIn("optimistic TX confirm removed", src)
        tx = (ROOT / "tab5_firmware" / "src" / "deck_tx.cpp").read_text()
        self.assertIn("deck_state_rx_armed", tx)
        self.assertNotIn("deck_state_ack_tx(id)", tx)

    def test_uuid_literals(self):
        hdr = (NETWORK / "k1_deck_state_v1.h").read_text()
        self.assertIn("9f3e5c20-1c7a-46b0-8d43-6d66e10a6d16", hdr)
        self.assertIn("9f3e5c21-1c7a-46b0-8d43-6d66e10a6d16", hdr)

    def test_snapshot_includes_softkey_lamp_paths(self):
        """Task 1.1 — HELLO+SNAPSHOT must cover soft-key lamp sources."""
        tx = (NETWORK / "k1_deck_state_tx.cpp").read_text()
        for path in (
            "edge.enabled",
            "director.enabled",
            "scene.smart",
            "vp.profile",
        ):
            self.assertIn(f'"{path}"', tx)
        # Inventory must sit in send_snapshot_image kPaths, not only comments.
        snap = tx[tx.index("send_snapshot_image") : tx.index("clear_delta_queue")]
        for path in (
            "edge.enabled",
            "director.enabled",
            "scene.smart",
            "vp.profile",
        ):
            self.assertIn(f'"{path}"', snap)
        self.assertIn("k1_edgemixer_config()", tx)
        self.assertIn("k1_smart_director_config()", tx)
        self.assertIn("k1_wireless_control_snapshot", tx)

    def test_tab5_apply_value_drives_key_lamps(self):
        rx = (ROOT / "tab5_firmware" / "src" / "deck_state_rx.cpp").read_text()
        self.assertIn('strcmp(e.path, "edge.enabled")', rx)
        self.assertIn("deck_ui_set_key_lamp(DECK_SHEET_EDGE", rx)
        self.assertIn("deck_ui_set_key_lamp(DECK_SHEET_DIRECTOR", rx)
        self.assertIn("deck_ui_set_key_lamp(DECK_SHEET_SMART", rx)
        self.assertIn("deck_ui_set_key_lamp(DECK_SHEET_RENDER", rx)
        self.assertIn("deck_ui_sheets_apply_bool", rx)

    def test_vivid_softkey_non_open_and_glass_forbidden(self):
        """Task 1.3 — VIVID non-open; chroma/sat remain glass-forbidden."""
        ui = (ROOT / "tab5_firmware" / "src" / "deck_ui.cpp").read_text()
        self.assertIn("opens_sheet", ui)
        self.assertIn("DECK_SHEET_VIVID, false, false, false)", ui)
        self.assertIn("if (!k->opens_sheet) return;", ui)
        tx = (ROOT / "tab5_firmware" / "src" / "deck_tx.cpp").read_text()
        self.assertIn("glass_path_forbidden", tx)
        self.assertIn('"primary.chroma"', tx)
        self.assertIn('"primary.saturation"', tx)
        sheets = (ROOT / "tab5_firmware" / "src" / "deck_ui_sheets.cpp").read_text()
        self.assertNotIn("SERIAL ONLY — chroma/sat dead on glass", sheets)
        manifest = (ROOT / "ui" / "spec" / "deck_softkey_manifest.json").read_text()
        self.assertIn("DISABLED_NO_OPEN", manifest)
        self.assertIn("edge.enabled, director.enabled, scene.smart, vp.profile", manifest)
        # Hygiene: note may mention CONFIRMED_REMOTE only as forbidden — never as live policy.
        self.assertIn("never CONFIRMED_REMOTE", manifest)
        self.assertNotIn('"ack_policy": "CONFIRMED_REMOTE"', manifest)

    def test_sheet_bool_pending_logic_without_look_tokens(self):
        """Task 1.2 — pending/confirm logic present; look chrome deferred."""
        sheets = (ROOT / "tab5_firmware" / "src" / "deck_ui_sheets.cpp").read_text()
        self.assertIn("pending_active", sheets)
        self.assertIn("deck_ui_sheets_apply_bool", sheets)
        self.assertIn("SKIP_LOOK_BLOCKED", sheets)


if __name__ == "__main__":
    unittest.main()
