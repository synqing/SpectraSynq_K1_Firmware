import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
VPAB_CAPTURE = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE") / "vpab_capture.cpp"
DIAG_CAPTURE = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE") / "diagnostic_capture.cpp"


def extract_function_body(text, name):
    marker = f"{name}("
    start = text.find(marker)
    if start == -1:
        raise AssertionError(f"{name} definition not found")
    brace = text.find("{", start)
    if brace == -1:
        raise AssertionError(f"{name} body not found")
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:index]
    raise AssertionError(f"{name} body did not close")


class DiagnosticCaptureStaticTest(unittest.TestCase):
    def test_render_reachable_vpab_capture_functions_have_no_serial_or_heap_calls(self):
        text = VPAB_CAPTURE.read_text()
        forbidden = (
            "USBSerial",
            "Serial.",
            "ESP_LOG",
            "ESP.getFreeHeap",
            "String",
            "std::string",
            "std::vector",
            "malloc(",
            "calloc(",
            "realloc(",
            "free(",
            "pvPortMalloc",
            "heap_caps_",
            "new ",
            "delete ",
            "DynamicJsonDocument",
            "SPIFFS",
            "LittleFS",
            "SD.",
            "File ",
            "delay(",
            "vTaskDelay(",
        )
        functions = (
            "vpab_capture_tick",
            "vpab_push_metrics",
            "vpab_push_bytes",
            "vpab_fill_self_shadow_metrics",
        )
        failures = []
        for function in functions:
            body = extract_function_body(text, function)
            for token in forbidden:
                if token in body:
                    failures.append(f"{function}: {token}")
        self.assertEqual(failures, [])

    def test_render_reachable_payload_buffers_are_file_scope_static(self):
        text = VPAB_CAPTURE.read_text()
        for function in ("vpab_push_metrics", "vpab_push_bytes"):
            body = extract_function_body(text, function)
            self.assertNotIn("VPABMetricPayload payload", body)
        self.assertNotIn("VPABBytesPayload payload", body)
        self.assertIn("static VPABMetricPayload vpab_metric_scratch;", text)
        self.assertIn("static VPABBytesPayload vpab_bytes_scratch;", text)

    def test_diagnostic_pool_uses_critical_sections_and_preflight(self):
        diag_text = DIAG_CAPTURE.read_text()
        vpab_text = VPAB_CAPTURE.read_text()
        self.assertIn("static portMUX_TYPE diag_capture_mux", diag_text)
        self.assertIn("bool diag_capture_can_push(uint16_t payload_bytes)", diag_text)
        self.assertIn("portENTER_CRITICAL(&diag_capture_mux)", diag_text)
        self.assertIn("diag_capture_can_push(sizeof(vpab_metric_scratch))", vpab_text)
        self.assertIn("diag_capture_can_push(sizeof(vpab_bytes_scratch))", vpab_text)

    def test_vpab_capture_state_is_critical_section_protected(self):
        text = VPAB_CAPTURE.read_text()
        self.assertIn("static portMUX_TYPE vpab_capture_mux = portMUX_INITIALIZER_UNLOCKED;", text)
        for function in (
            "vpab_capture_reset",
            "vpab_capture_arm",
            "vpab_capture_stop",
            "vpab_capture_tick",
            "vpab_capture_print_status",
        ):
            with self.subTest(function=function):
                body = extract_function_body(text, function)
                self.assertIn("portENTER_CRITICAL(&vpab_capture_mux)", body)
                self.assertIn("portEXIT_CRITICAL(&vpab_capture_mux)", body)

        tick_body = extract_function_body(text, "vpab_capture_tick")
        self.assertIn("VPABCaptureMode mode = VPAB_CAPTURE_METRICS;", tick_body)
        self.assertIn("bool once = false;", tick_body)
        self.assertIn("mode = vpab_capture_state.mode;", tick_body)
        self.assertIn("once = vpab_capture_state.once;", tick_body)

    def test_vpab_render_us_is_channel_specific_not_combined_envelope(self):
        text = VPAB_CAPTURE.read_text()
        self.assertIn("static uint32_t vpab_channel_render_us(uint8_t channel)", text)
        self.assertIn("vp_perf.primary_render.max_us", text)
        self.assertIn("vp_perf.secondary_render.max_us", text)

        fill_body = extract_function_body(text, "vpab_fill_self_shadow_metrics")
        bytes_body = extract_function_body(text, "vpab_push_bytes")
        self.assertIn("vpab_channel_render_us(channel)", fill_body)
        self.assertIn("vpab_channel_render_us(channel)", bytes_body)
        self.assertNotIn("vp_render_us_last", fill_body)
        self.assertNotIn("vp_render_us_last", bytes_body)

    def test_vpab_byte_dump_emits_final_byte_aggregate_rows(self):
        text = VPAB_CAPTURE.read_text()
        self.assertIn("struct VPABByteAggregate", text)
        self.assertIn("static VPABByteAggregate vpab_aggregate_bytes(const VPABBytesPayload& bytes)", text)
        self.assertIn("struct VPABRenderContext", (FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE") / "vpab_capture.h").read_text())
        self.assertIn("void vpab_capture_set_render_context(const VPABRenderContext& context)", text)
        self.assertIn("static void vpab_emit_context_row()", text)
        self.assertIn('"VPABC,ver=1,primary_mode="', text)
        self.assertIn("vpab_emit_context_row();", text)
        emit_body = extract_function_body(text, "vpab_emit_bytes_as_metric_row")
        for token in (
            '"VPABB,ver=1,seq="',
            '",hash=0x"',
            '",energy="',
            '",r_sum="',
            '",g_sum="',
            '",b_sum="',
            '",nonzero_led_pct="',
            '",com="',
            '",sat_avg="',
            '",white_bias_avg="',
        ):
            self.assertIn(token, emit_body)

    def test_vpab_mode_field_uses_render_context_not_config_directly(self):
        text = VPAB_CAPTURE.read_text()
        mode_body = extract_function_body(text, "vpab_mode_for_channel")
        self.assertIn("VPABRenderContext context = vpab_capture_read_render_context();", mode_body)
        self.assertIn("context.secondary_mode", mode_body)
        self.assertIn("context.primary_mode", mode_body)
        self.assertNotIn("CONFIG.LIGHTSHOW_MODE", mode_body)
        self.assertNotIn("SECONDARY_LIGHTSHOW_MODE", mode_body)


if __name__ == "__main__":
    unittest.main()
