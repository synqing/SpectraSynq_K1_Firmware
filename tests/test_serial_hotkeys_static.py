import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
SERIAL_MENU = FW / "serial_menu.h"
NOISE_CAL_ARM = FW / "control" / "k1_noise_cal_arm.cpp"


class SerialHotkeyStaticContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SERIAL_MENU.read_text()

    def _function_body(self, name):
        match = re.search(rf"\b(?:bool|void)\s+{name}\s*\([^)]*\)\s*\{{", self.source)
        self.assertIsNotNone(match, f"{name}() must exist")
        start = match.end()
        depth = 1
        index = start
        while index < len(self.source) and depth:
            char = self.source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        self.assertEqual(depth, 0, f"{name}() body must be balanced")
        return self.source[start:index - 1]

    def test_hotkey_allowlist_contains_expected_lab_keys(self):
        # The shipping immediate-hotkey surface excludes the motion-probe live
        # keys (z/x/c/v/b/n/m): they compile only under ENABLE_MOTION_PROBE (the
        # non-shipping k1_motion_probe env; never defined for k1_hardware). Strip
        # that guarded block so this contract asserts the SHIPPING surface only —
        # text-grepping the raw body would false-fail on the guarded dev keys.
        body = re.sub(r"#ifdef\s+ENABLE_MOTION_PROBE\b.*?#endif", "",
                      self._function_body("serial_hotkey_is_immediate"), flags=re.S)
        for key in [" ", "h", ";", "N", "Y", "[", "]",
                    "i", "I", "o", "O", "p", "P",
                    "j", "J", "k", "K", "l", "L",
                    "q", "Q", "w", "W", "e", "E", "r", "R", "t", "T",
                    ",", ".", "/", "1", "2", "3", "4", "5", "6",
                    "a", "s", "d", "f",
                    "g", "G", "u", "y", "-", "=", "_", "+"]:
            self.assertIn(f"'{key}'", body)
        # 'm' is NO LONGER removed: it is the SHIPPING ref-E spatial toggle
        # (#ifndef ENABLE_MOTION_PROBE), reclaimed from the motion-probe "B knob +"
        # binding — the two are mutually exclusive by build.
        for removed_key in ["'~", "'c", "'C", "'M", "'n", "'b", "'B", "'x"]:
            self.assertNotIn(removed_key, body)

    def test_dispatcher_has_no_destructive_or_single_byte_calibration_hotkeys(self):
        body = self._function_body("serial_handle_hotkey")
        for forbidden in ["factory_reset", "restore_defaults", "start_noise_cal",
                          "clear_noise_cal", "reboot()", "reset"]:
            self.assertNotIn(forbidden, body)
        n_case = re.search(r"case 'N':(?P<body>.*?)case 'Y':", body, re.S)
        self.assertIsNotNone(n_case, "N hotkey must arm only")
        self.assertIn("serial_arm_noise_cal();", n_case.group("body"))
        self.assertNotIn("noise_transition_queued", n_case.group("body"))
        self.assertIn("case 'Y':", body)
        y_body = body.split("case 'Y':", 1)[1].split("case '[':", 1)[0]
        self.assertIn("serial_confirm_noise_cal();", y_body)
        self.assertNotIn("noise_transition_queued", y_body)

    def test_noise_cal_confirmation_is_guarded(self):
        serial_body = self._function_body("serial_confirm_noise_cal")
        self.assertIn("k1_noise_cal_confirm", serial_body)

        arm_source = NOISE_CAL_ARM.read_text()
        match = re.search(r"bool\s+k1_noise_cal_confirm\s*\([^)]*\)\s*\{", arm_source)
        self.assertIsNotNone(match, "k1_noise_cal_confirm() must exist")
        start = match.end()
        depth = 1
        index = start
        while index < len(arm_source) and depth:
            char = arm_source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            index += 1
        body = arm_source[start:index - 1]
        self.assertIn("k1_noise_cal_arm_active", body)
        self.assertIn("noise_transition_queued = true", body)
        self.assertIn("NOISE_CAL: not armed", body)

    def test_check_serial_preserves_line_buffer_for_multi_byte_commands(self):
        body = self._function_body("check_serial")
        self.assertIn("byte == ':'", body)
        self.assertIn("command_mode = true", body)
        self.assertIn("serial_hotkey_is_immediate", body)
        self.assertIn("parse_command(command_buf)", body)
        self.assertNotIn("USBSerial.available() == 0", body)
        self.assertIn("serial_handle_hotkey(char(byte))", body)

    def test_edge_hotkeys_are_all_sc_safe_allowlisted(self):
        # Gate<->handler consistency (the 'y' dual-edge dead-hotkey bug,
        # 2026-07-09): every EdgeMixer hotkey wired in serial_handle_hotkey
        # (case 'X' -> a serial_edge_* action) MUST also appear in the
        # serial_hotkey_is_immediate SC_SAFE allowlist, or the gate silently drops
        # the key BEFORE dispatch (it never reaches the handler). Handled edge keys
        # must be a SUBSET of allowlisted keys. This routes the key class through
        # the gate in CI so a future un-allowlisted hotkey fails here, not on-device.
        handler = self._function_body("serial_handle_hotkey")
        allowlist = self._function_body("serial_hotkey_is_immediate")
        edge_keys = set()
        for match in re.finditer(
                r"case '(?P<k>(?:\\.|[^'])+)':(?P<body>.*?)(?=\bcase '|\bdefault\s*:)",
                handler, re.S):
            if "serial_edge_" in match.group("body"):
                edge_keys.add(match.group("k"))
        self.assertTrue(
            edge_keys, "no EdgeMixer hotkeys found in serial_handle_hotkey")
        missing = sorted(k for k in edge_keys if f"'{k}'" not in allowlist)
        self.assertEqual(
            missing, [],
            "EdgeMixer hotkeys handled but NOT SC_SAFE-allowlisted (the gate drops "
            f"them before dispatch): {missing}",
        )

    def test_help_documents_targeted_controls_and_vp_shortcuts(self):
        self.assertIn("K1 HOTKEYS", self.source)
        self.assertIn("target channel", self.source)
        self.assertIn(": command prefix", self.source)
        self.assertIn("[ target mode previous", self.source)
        self.assertIn("] target mode next", self.source)
        self.assertIn("N arm noise calibration", self.source)
        self.assertIn("Y confirm armed noise calibration", self.source)
        self.assertIn("lowercase increases", self.source)
        self.assertIn("Space target channel", self.source)
        self.assertIn("i/I photons", self.source)
        self.assertIn("o/O chroma", self.source)
        self.assertIn("p/P mood", self.source)
        self.assertIn("l/L base coat intensity", self.source)
        self.assertIn("q/Q square_iter", self.source)
        self.assertIn("w/W sensitivity", self.source)
        self.assertIn("e/E waveform shift", self.source)
        self.assertIn("r/R bloom shift", self.source)
        self.assertIn("t/T bloom alpha", self.source)
        # Effects-queue key map (2026-06-11): digits are preset slots now; the
        # former digit toggles live on as typed ':' commands.
        self.assertIn("1-9,0 load/arm slot 1-10", self.source)
        self.assertIn("save slot 1-10", self.source)
        self.assertIn("\\\\ commit armed changes", self.source)
        self.assertIn("U queue mode toggle", self.source)
        self.assertIn("a AP stream", self.source)
        self.assertIn("s VP stream", self.source)
        self.assertIn("d AGC stream", self.source)
        self.assertIn("f stop streams", self.source)


if __name__ == "__main__":
    unittest.main()
