import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
SERIAL_MENU = (FW / "serial_menu.h").read_text()
SERIAL_TABLE = (FW / "serial_cmd_table.def").read_text()
I2S = (FW / "audio" / "i2s_audio.h").read_text()
SNAPSHOT = (FW / "audio" / "k1_audio_snapshot.h").read_text()


def function_body(source, name):
    match = re.search(rf"\bvoid\s+{name}\s*\([^)]*\)\s*\{{", source)
    assert match is not None, f"{name}() must exist"
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth:
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"{name}() body must be balanced"
    return source[start:index - 1]


class PercussionEventStatusStaticTest(unittest.TestCase):
    def test_event_status_is_safe_read_only_table_command(self):
        self.assertIn(
            'SERIAL_CMD("event_status",    0, cmd_event_status,            SC_SAFE,                  0,                                 IS_BOTH       )',
            SERIAL_TABLE,
        )
        self.assertIn("event_status | Print current onset/kick/snare/hihat event state", SERIAL_MENU)

    def test_event_status_prints_all_percussion_channels_without_streaming(self):
        body = function_body(SERIAL_MENU, "cmd_event_status")
        self.assertIn("k1_audio_snapshot_read()", body)
        self.assertIn("k1_onset_beat_read()", body)
        self.assertIn("EVENT_STATUS,t=", body)
        for token in (
            "onset=",
            "bass=",
            "beat=",
            "kick=",
            "snare=",
            "hihat=",
            "tid=",
            "kid=",
            "sid=",
            "hid=",
            "tlvl=",
            "klvl=",
            "slvl=",
            "hlvl=",
            "tstr=",
            "kstr=",
            "sstr=",
            "hstr=",
            "energy=",
            "nov=",
            "sil=",
        ):
            self.assertIn(token, body)

    def test_event_status_does_not_expand_the_core0_ap_stream(self):
        # The 1 Hz AP stream remains the small legacy scalar line; the richer
        # percussive proof surface is a pull command from the serial loop.
        self.assertNotIn("snare_event_id", I2S)
        self.assertNotIn("hihat_event_id", I2S)
        self.assertNotIn("kick_strength", I2S)

    def test_percussive_snapshot_contract_stays_event_id_based(self):
        for token in (
            "bool  kick;",
            "bool  snare;",
            "bool  hihat;",
            "uint32_t kick_event_id;",
            "uint32_t snare_event_id;",
            "uint32_t hihat_event_id;",
        ):
            self.assertIn(token, SNAPSHOT)


if __name__ == "__main__":
    unittest.main()
