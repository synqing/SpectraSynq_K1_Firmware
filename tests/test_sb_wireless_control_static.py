import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
CONTROL_CPP = FW / "control" / "sb_wireless_control.cpp"
FACADE_CPP = FW / "control" / "sb_k1_control_facade.cpp"
NETWORK_CPP = FW / "network" / "sb_k1_wireless.cpp"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
PLATFORMIO = ROOT / "platformio.ini"
CONTRACT = ROOT / "docs" / "protocol" / "k1-ws-contract.yaml"


class K1WirelessControlStaticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.control = CONTROL_CPP.read_text()
        cls.facade = FACADE_CPP.read_text()
        cls.network = NETWORK_CPP.read_text()
        cls.ino = INO.read_text()
        cls.platformio = PLATFORMIO.read_text()
        cls.contract = CONTRACT.read_text()

    def _function_body(self, source, name):
        match = re.search(rf"\b[\w:<>]+\s+{name}\s*\([^)]*\)\s*\{{", source)
        self.assertIsNotNone(match, f"{name}() must exist")
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
        self.assertEqual(depth, 0, f"{name}() body must be balanced")
        return source[start:index - 1]

    def test_k1_wireless_is_ap_only(self):
        self.assertIn("WiFi.mode(WIFI_AP)", self.network)
        self.assertIn("WiFi.softAP(", self.network)
        self.assertNotIn("WiFi.begin(", self.network)
        self.assertNotIn("WIFI_STA", self.network)

    def test_wireless_control_delegates_to_facade(self):
        self.assertIn("sb_k1_control_is_allowed", self.control)
        self.assertIn("sb_k1_control_apply", self.control)
        self.assertIn("sb_k1_control_snapshot", self.control)

    def test_wireless_control_allowlist_in_facade(self):
        for control in [
            "primary.mode",
            "primary.palette",
            "primary.palette_mode",
            "primary.photons",
            "primary.chroma",
            "primary.mood",
            "secondary.mode",
            "secondary.palette",
            "secondary.enabled",
            "secondary.photons",
            "secondary.chroma",
            "secondary.mood",
            "scene.smart",
            "calibration.noise.arm",
            "calibration.noise.confirm",
            "calibration.noise.status",
            "calibration.noise.clear",
            "vp.profile",
            "vp.bloom.alpha",
        ]:
            self.assertIn(f'"{control}"', self.facade)
        allowlist_start = self.facade.index("static const char* const kAllowedControls[]")
        allowlist_end = self.facade.index("};", allowlist_start)
        allowlist = self.facade[allowlist_start:allowlist_end]
        for forbidden in [
            "set_" + "mode",
            "palette_" + "index",
            "secondary_" + "mode",
            "secondary_palette_" + "index",
            "smart_" + "scene",
            "start_noise_cal",
            "clear_noise_cal",
            "factory_reset",
            "restore_defaults",
            "reset",
            "ota",
            "erase",
        ]:
            self.assertNotIn(f'"{forbidden}"', allowlist)

    def test_calibration_noise_start_is_rejected(self):
        body = self._function_body(self.facade, "sb_k1_control_apply")
        self.assertIn('"calibration.noise.start"', body)
        self.assertIn('"start_noise_cal"', body)
        self.assertIn("calibration.noise.arm then calibration.noise.confirm", body)

    def test_wireless_callbacks_only_enqueue_commands(self):
        handler = re.search(
            r"void\s+handle_ws_event\s*\([^)]*\)\s*\{(?P<body>.*?)\n\}",
            self.network,
            re.S,
        )
        self.assertIsNotNone(handler)
        body = handler.group("body")
        self.assertIn("enqueue_request", body)
        self.assertIn("queue_control_error", body)
        self.assertIn("queue_error", body)
        self.assertNotIn("g_ws.sendTXT", body)
        self.assertNotIn("CONFIG.", body)
        self.assertNotIn("SECONDARY_", body)
        self.assertNotIn("save_config_delayed", body)

    def test_wireless_queue_drains_next_to_serial(self):
        serial_index = self.ino.index("check_serial(t_now)")
        wireless_index = self.ino.index("sb_k1_wireless_poll(t_now)")
        audio_index = self.ino.index("acquire_sample_chunk(t_now)")
        self.assertLess(serial_index, wireless_index)
        self.assertLess(wireless_index, audio_index)

        poll_body = self._function_body(self.network, "sb_k1_wireless_poll")
        self.assertIn("dequeue_request", poll_body)
        self.assertIn("k1_wireless_control_apply", poll_body)
        self.assertIn("queue_control_result", poll_body)
        self.assertIn("queue_state", poll_body)
        self.assertNotIn("g_ws.loop", poll_body)
        self.assertNotIn("g_ws.sendTXT", poll_body)

    def test_websocket_loop_is_low_priority_task_not_ap_loop(self):
        ws_task = self._function_body(self.network, "k1_ws_task")
        poll_body = self._function_body(self.network, "sb_k1_wireless_poll")

        self.assertIn("g_ws.loop()", ws_task)
        self.assertIn("vTaskDelay(pdMS_TO_TICKS(WS_TASK_DELAY_MS))", ws_task)
        self.assertNotIn("g_ws.loop()", poll_body)
        self.assertIn("WS_TASK_PRIORITY", self.network)
        self.assertIn("tskIDLE_PRIORITY", self.network)

    def test_ap_loop_yields_idle_when_wireless_client_connected(self):
        helper = self._function_body(self.network, "yield_ap_idle_if_client_connected")
        poll_body = self._function_body(self.network, "sb_k1_wireless_poll")

        self.assertIn("WiFi.softAPgetStationNum()", helper)
        self.assertIn("AP_IDLE_YIELD_INTERVAL_MS", helper)
        self.assertIn("vTaskDelay(1)", helper)
        self.assertIn("yield_ap_idle_if_client_connected(now_ms)", poll_body)

    def test_wireless_never_runs_on_led_render_core(self):
        self.assertIn("-DARDUINO_RUNNING_CORE=0", self.platformio)
        self.assertIn("-DSB_LED_TASK_CORE=1", self.platformio)
        self.assertNotIn("-DSB_K1_WS_TASK_CORE=0", self.platformio)
        self.assertNotIn("-DWEBSOCKETS_TCP_TIMEOUT=20", self.platformio)
        self.assertIn("ARDUINO_RUNNING_CORE == SB_LED_TASK_CORE", self.ino)
        self.assertIn("K1 timing invariant violation", self.ino)
        self.assertIn("#define SB_K1_WIRELESS_TASK_CORE 0", self.network)
        self.assertIn("K1 wireless task must not run on the LED render core", self.network)
        self.assertIn("xTaskCreatePinnedToCore", self.network)
        self.assertIn("k1_ws_task", self.network)
        self.assertIn("#ifdef SB_K1_WIRELESS_ENABLED\n#include \"sb_k1_wireless.h\"", self.ino)
        self.assertIn("#ifdef SB_K1_WIRELESS_ENABLED\n\n#include \"sb_k1_wireless.h\"", self.network)

        setup_body = self._function_body(self.ino, "setup")
        led_body = self._function_body(self.ino, "led_thread")
        loop_body = self._function_body(self.ino, "loop")
        ws_task_body = self._function_body(self.network, "k1_ws_task")

        self.assertIn("#ifdef SB_K1_WIRELESS_ENABLED\n  sb_k1_wireless_begin();\n#endif", setup_body)
        self.assertIn("#ifdef SB_K1_WIRELESS_ENABLED\n  sb_k1_wireless_poll(t_now);\n#endif", loop_body)
        self.assertIn("g_ws.loop()", ws_task_body)
        self.assertIn("vTaskDelay", ws_task_body)
        self.assertNotIn("sb_k1_wireless_begin", led_body)
        self.assertNotIn("sb_k1_wireless_poll", led_body)
        self.assertNotIn("g_ws.loop", led_body)

    def test_k1_protocol_replaces_legacy_wire_names(self):
        self.assertIn('"k1.hello"', self.network)
        self.assertIn('"k1.state.get"', self.network)
        self.assertIn('"k1.capabilities.get"', self.network)
        self.assertIn('"k1.control.set"', self.network)
        self.assertIn("K1_WS_PROTOCOL_V2", self.network)
        self.assertIn("K1_REQUEST_CAPABILITIES_GET", self.network)
        self.assertIn("k1.control.result", self.network)
        self.assertIn("k1.error", self.network)
        self.assertIn("request.kind == K1_REQUEST_CONTROL_SET", self.network)
        self.assertIn("K1_CONTROL_TOKEN", self.network)
        self.assertIn("-DK1_CONTROL_TOKEN=\\\"k1-tab5\\\"", self.platformio)
        self.assertNotIn('"sb' + '.command"', self.network)
        self.assertNotIn('"sb' + '.ack"', self.network)

    def test_k1_ws_parser_rejects_ambiguous_json_payloads(self):
        parse_body = self._function_body(self.network, "parse_request_payload")

        self.assertIn("memchr(payload, '\\0', length)", parse_body)
        self.assertIn("looks_like_json_object(json)", parse_body)
        self.assertIn("has_duplicate_json_protocol_keys(json)", parse_body)
        self.assertLess(parse_body.index("memchr(payload, '\\0', length)"), parse_body.index("memcpy(json, payload, length)"))
        self.assertLess(parse_body.index("looks_like_json_object(json)"), parse_body.index('read_json_string(json, "type"'))
        read_u32_body = self._function_body(self.network, "read_json_u32")
        self.assertIn("*p == '-' || *p == '+'", read_u32_body)
        self.assertIn("value > UINT32_MAX", read_u32_body)
        self.assertIn("duplicate_json_key_count", self.network)
        self.assertIn('{"type", "v", "id", "token", "control", "value"}', self.network)
        self.assertIn('if (strcmp(code, "json") == 0)', self.network)
        self.assertIn("json: unsupported JSON payload", self.contract)
        self.assertIn("replay: stale or replayed request id", self.contract)
        self.assertIn("id_encoding: unsigned decimal integer", self.contract)

    def test_k1_ws_request_ids_are_fresh_per_connected_client(self):
        handler = self._function_body(self.network, "handle_ws_event")

        self.assertIn("uint32_t g_last_client_request_id[QUEUE_CAPACITY]", self.network)
        self.assertIn("reset_client_request_tracker", self.network)
        self.assertEqual(handler.count("reset_client_request_tracker(client_num);"), 2)
        self.assertIn("bool request_id_is_fresh", self.network)
        self.assertIn("void commit_client_request_id", self.network)
        self.assertIn('"replay"', handler)
        self.assertIn("queue_control_error", handler)
        self.assertIn("queue_error", handler)
        self.assertLess(handler.index("if (!request_id_is_fresh"), handler.index("if (request.kind == K1_REQUEST_HELLO)"))
        self.assertIn("queue_hello(client_num, request.id, request.protocol_version)", handler)
        self.assertIn("if (enqueue_request(request)) {\n        commit_client_request_id(client_num, request.id);", handler)
        self.assertIn("id_scope: websocket_client", self.contract)
        self.assertIn("failure_code: replay", self.contract)

    def test_k1_ws_reports_tx_drops_and_does_not_ignore_response_queue_failures(self):
        poll_body = self._function_body(self.network, "sb_k1_wireless_poll")

        self.assertNotIn("(void)enqueue_frame_payload", self.network)
        for name in [
            "queue_control_error",
            "queue_error",
            "queue_control_result",
            "queue_hello",
            "queue_state",
            "queue_capabilities",
        ]:
            self.assertIn(f"bool {name}(", self.network)
        self.assertIn("g_tx_drop_count", self.network)
        self.assertIn("g_reserved_frame_count", self.network)
        self.assertIn("bool reserve_frame_capacity", self.network)
        self.assertIn("void release_frame_reservation", self.network)
        self.assertIn("bool enqueue_frame_payload(uint8_t client_num, const char* payload, bool reserved = false)", self.network)
        self.assertIn("g_frame_count + g_reserved_frame_count", self.network)
        self.assertIn('\\"tx_dropped\\":%lu', self.network)
        self.assertIn("tx_dropped: monotonic K1-side count", self.contract)
        self.assertLess(poll_body.index("reserve_frame_capacity()"), poll_body.index("dequeue_request(&request)"))
        self.assertLess(poll_body.index("reserve_frame_capacity()"), poll_body.index("k1_wireless_control_apply"))
        self.assertIn("release_frame_reservation();\n      break;", poll_body)
        self.assertIn("queue_control_result(request.client_num", poll_body)
        self.assertIn("request.protocol_version", poll_body)
        self.assertIn("queue_state(request.client_num, request.id, request.protocol_version, true)", poll_body)
        self.assertIn("queue_capabilities(request.client_num, request.id, request.protocol_version, true)", poll_body)
        self.assertIn("release_frame_reservation();\n    }", poll_body)
        self.assertIn("response queue full after request", poll_body)

    def test_wireless_state_snapshot_is_available_for_tab5(self):
        self.assertIn("k1_wireless_control_snapshot", self.control)
        self.assertIn("primary_mode", self.facade)
        self.assertIn("secondary_mode", self.facade)
        self.assertIn("secondary_enabled", self.facade)
        self.assertIn("primary_palette_mode", self.facade)
        self.assertIn("scene_smart", self.facade)
        self.assertIn("tempo_bpm", self.facade)
        self.assertIn("tempo_locked", self.facade)
        self.assertIn("sb_tempo_read()", self.facade)
        self.assertIn('"off"', self.facade)
        self.assertIn('"assist"', self.facade)
        self.assertIn('"l1"', self.facade)
        self.assertIn('"auto"', self.facade)

    def test_wireless_state_snapshot_exposes_tempo_only_as_bpm_and_locked(self):
        self.assertIn('#include "sb_tempo.h"', self.facade)
        self.assertIn("const SBTempoEvent tempo = sb_tempo_read();", self.facade)
        self.assertIn("state->tempo_bpm = isfinite(tempo.bpm)", self.facade)
        self.assertIn("state->tempo_locked = tempo.locked;", self.facade)
        self.assertIn('\\"tempo\\":{\\"bpm\\":%.1f,\\"locked\\":%s}', self.network)
        self.assertIn("palette_mode", self.network)
        self.assertIn("double(state.tempo_bpm)", self.network)
        self.assertIn('state.tempo_locked ? "true" : "false"', self.network)
        self.assertNotIn("tempo_confidence", self.network)
        self.assertNotIn("phase01", self.network)

    def test_production_build_excludes_wireless_modules_and_websockets(self):
        # control/ stays in the build: sb_noise_cal_arm.cpp is linked by the
        # production serial arm/confirm path (undefined-reference if excluded).
        self.assertIn("+<control/sb_*.cpp>", self.platformio)
        # Wireless exclusion is scoped to the PRODUCTION env section: the
        # k1_wireless_ab_probe bench env (2026-06-11, interference A/B) is the
        # ONLY place the wireless stack may be enabled, and it is NON-SHIPPABLE.
        prod = self.platformio.split("[env:k1_hardware]")[1].split("[env:")[0]
        for tok in ("+<network/sb_*.cpp>", "links2004/WebSockets",
                    "SB_K1_WIRELESS_ENABLED", "SB_K1_WS_TASK_CORE",
                    "WEBSOCKETS_TCP_TIMEOUT"):
            self.assertNotIn(tok, prod)
        # The wireless define exists nowhere except the bench env.
        before_bench, _, after = self.platformio.partition("[env:k1_wireless_ab_probe]")
        after_bench = after.split("[env:")[0] if after else ""
        self.assertNotIn("SB_K1_WIRELESS_ENABLED", before_bench)
        self.assertIn("-DSB_K1_WIRELESS_ENABLED", after_bench)
        self.assertIn("NON-SHIPPABLE", after_bench)
        remainder = after[len(after_bench):] if after else ""
        self.assertNotIn("SB_K1_WIRELESS_ENABLED", remainder)

    def test_scalar_controls_reject_out_of_range_instead_of_clamping(self):
        self.assertIn("needs_number_range", self.facade)
        for token in [
            '"Primary photons out of range"',
            '"Primary chroma out of range"',
            '"Primary mood out of range"',
            '"Secondary photons out of range"',
            '"Secondary chroma out of range"',
            '"Secondary mood out of range"',
        ]:
            self.assertIn(token, self.facade)

        scalar_body = self.facade[
            self.facade.index('if (strcmp(record.control, "primary.photons") == 0)'):
            self.facade.index('if (strcmp(record.control, "scene.smart") == 0)')
        ]
        self.assertNotIn("constrain(record.number_value", scalar_body)
        self.assertIn("0.05f, 1.0f", scalar_body)


if __name__ == "__main__":
    unittest.main()
