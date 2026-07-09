import re
import unittest
from pathlib import Path
from _fwpath import FwDir


ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
PLATFORMIO = ROOT / "platformio.ini"
PLAN = ROOT / "docs" / "superpowers" / "plans" / "2026-05-27-smart-visual-engine-e2e-execution.md"
STRATEGY = ROOT / "docs" / "forensics" / "2026-05-27-smart-director-edgemixer-onset-import-strategy.md"

SMART_MODULE_PREFIXES = (
    "sb_audio_snapshot",
    "sb_mode_selection",
    "sb_smart_director",
    "k1_edgemixer",
    "sb_onset_beat",
    "sb_visual_hooks",
)

FORBIDDEN_SMART_SOURCE_PATTERNS = (
    re.compile(r"\bnew\s*(?:\(|[A-Za-z_])"),
    re.compile(r"\bmalloc\s*\("),
    re.compile(r"\bcalloc\s*\("),
    re.compile(r"\brealloc\s*\("),
    re.compile(r"\bfree\s*\("),
    re.compile(r"\bString\b"),
    re.compile(r"\bstd::vector\b"),
    re.compile(r"\bstd::map\b"),
    re.compile(r"\bPreferences\b"),
    re.compile(r"\bFastLED\b"),
    re.compile(r"\bSerial\b"),
    re.compile(r"\bUSBSerial\b"),
    re.compile(r"\bWiFi\b"),
    re.compile(r"\bFastLED\.show\s*\("),
    re.compile(r"\bSerial\.print"),
    re.compile(r"\bUSBSerial\.print"),
    re.compile(r"#\s*include\s*[<\"].*WiFi"),
)

FORBIDDEN_DONOR_TOKENS = (
    "ControlBusFrame",
    "RendererActor",
    "EffectId",
    "SynqMatrixHandlers",
    "SynqMatrixWs",
    "ESPAsyncWebServer",
    "AsyncTCP",
)

PRODUCTION_FORBIDDEN_TOKENS = (
    "mabutrace",
    "feature_mabutrace",
    "trace_dev",
    "enable_diag_capture",
    "enable_vpab_probe",
    "enable_vp_perf_audit",
    "enable_ap_stream",
    "enable_frame_dump",
    "enable_vp_probe_cmd",
    "enable_gdft_harness",
    "feature_trace_render",
    "diagnostic_capture.cpp",
    "vpab_capture.cpp",
)


def read(path):
    return path.read_text(encoding="utf-8")


def platformio_sections():
    text = read(PLATFORMIO)
    matches = list(re.finditer(r"^\[(?P<name>[^\]]+)\]\s*$", text, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("name")] = text[start:end]
    return sections


def strip_ini_comments(text):
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(";"):
            continue
        lines.append(line)
    return "\n".join(lines)


def smart_source_files():
    files = []
    for path in FIRMWARE.iterdir():
        if path.suffix not in {".h", ".cpp"}:
            continue
        if any(path.stem == prefix for prefix in SMART_MODULE_PREFIXES):
            files.append(path)
    return sorted(files)


def function_body(source, name):
    match = re.search(rf"\b(?:bool|void)\s+{name}\s*\([^)]*\)\s*\{{", source)
    if match is None:
        return None
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
    if depth != 0:
        return None
    return source[start:index - 1]


class SmartVisualEngineStaticTest(unittest.TestCase):
    def test_production_build_filter_includes_smart_modules(self):
        sections = platformio_sections()
        production = strip_ini_comments(sections["env:k1_hardware"]).lower()
        self.assertIn("+<audio/sb_*.cpp>", production)
        self.assertIn("+<director/sb_*.cpp>", production)

    def test_production_env_excludes_dev_and_trace_flags(self):
        sections = platformio_sections()
        production = strip_ini_comments(sections["env:k1_hardware"]).lower()
        hits = [token for token in PRODUCTION_FORBIDDEN_TOKENS if token in production]
        self.assertEqual(hits, [])

    def test_smart_sources_have_no_render_or_dev_forbidden_tokens(self):
        offenders = []
        for path in smart_source_files():
            text = read(path)
            for pattern in FORBIDDEN_SMART_SOURCE_PATTERNS:
                if pattern.search(text):
                    offenders.append(f"{path.relative_to(ROOT)}: {pattern.pattern}")
            for token in FORBIDDEN_DONOR_TOKENS:
                if token in text:
                    offenders.append(f"{path.relative_to(ROOT)}: {token}")
        self.assertEqual(offenders, [])

    def test_audio_snapshot_contract_exists_and_is_post_novelty(self):
        header = read(FIRMWARE / "sb_audio_snapshot.h")
        source = read(FIRMWARE / "sb_audio_snapshot.cpp")
        ino = read(FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino")

        for token in (
            "enum SBMusicState",
            "struct SBAudioSnapshot",
            "struct SBOnsetBeatEvent",
            "void sb_audio_snapshot_update(uint32_t frame_ms)",
            "SBAudioSnapshot sb_audio_snapshot_read()",
        ):
            self.assertIn(token, header)

        self.assertIn("portENTER_CRITICAL", source)
        self.assertIn("portEXIT_CRITICAL", source)
        self.assertNotIn("chromagram_smooth", source)
        self.assertLess(ino.index("calculate_novelty(t_now);"), ino.index("sb_audio_snapshot_update(t_now);"))

    def test_edgemixer_future_contract_keeps_centre_79_80_when_present(self):
        edge_path = FIRMWARE / "k1_edgemixer.cpp"
        if not edge_path.exists():
            self.skipTest("EdgeMixer not implemented yet")
        text = read(edge_path)
        self.assertTrue("79.5f" in text or ("79" in text and "80" in text))
        # Gate-3 (Captain 2026-07-09): EdgeMixer now ships ENABLED by default at the
        # BALANCED intensity, so the shipping default is `{ true, ...` (was `{ false,`
        # byte-inert). The centre-79/80 contract asserted above still holds (masked spatial).
        self.assertRegex(text, r"static\s+K1EdgeMixerConfig\s+k1_edge_config\s*=\s*\{\s*true,")
        self.assertIn("k1_edgemixer_set_config", text)
        self.assertIn("k1_edgemixer_apply", text)

    def test_edgemixer_does_not_create_light_from_dark_pixels(self):
        edge_path = FIRMWARE / "k1_edgemixer.cpp"
        if not edge_path.exists():
            self.skipTest("EdgeMixer not implemented yet")
        text = read(edge_path)
        forbidden = (
            "SQ15x16(1.0f) - r",
            "SQ15x16(1.0f) - g",
            "SQ15x16(1.0f) - b",
            "SQ15x16(1) - r",
            "SQ15x16(1) - g",
            "SQ15x16(1) - b",
        )
        hits = [token for token in forbidden if token in text]
        self.assertEqual(hits, [])
        self.assertIn("Preserve luminance", text)

    def test_edge_serial_controls_do_not_auto_enable_mixer(self):
        # The edge handlers were lifted VERBATIM into serial_cmd_dispatch_edge_mixer()
        # in serial_cmd_handlers.cpp (structural-contract gate, oracle_serial_struct.py);
        # the no-auto-enable invariant is asserted against their new home.
        text = read(FIRMWARE / "serial_cmd_handlers.cpp")
        edge_enabled_body = re.search(
            r'else if \(strcmp\(command_type, "edge_enabled"\) == 0\).*?'
            r'else if \(strcmp\(command_type, "edge_mode"\) == 0\)',
            text,
            re.S,
        )
        edge_mode_body = re.search(
            r'else if \(strcmp\(command_type, "edge_mode"\) == 0\).*?'
            r'else if \(strcmp\(command_type, "edge_strength"\) == 0\)',
            text,
            re.S,
        )
        edge_strength_body = re.search(
            r'else if \(strcmp\(command_type, "edge_strength"\) == 0\).*?'
            r'return true;',  # edge_mixer dispatcher terminal (was #if ENABLE_DIAG_CAPTURE inline)
            text,
            re.S,
        )
        self.assertIsNotNone(edge_enabled_body)
        self.assertIsNotNone(edge_mode_body)
        self.assertIsNotNone(edge_strength_body)
        self.assertNotIn("config.mode = K1_EDGE_MIXER_ANALOGOUS", edge_enabled_body.group(0))
        self.assertNotIn("config.enabled = mode != K1_EDGE_MIXER_OFF", edge_mode_body.group(0))
        self.assertNotIn("config.mode = K1_EDGE_MIXER_ANALOGOUS", edge_strength_body.group(0))
        self.assertIn("config.enabled = false", edge_mode_body.group(0))

    def test_runtime_capture_scripts_restore_safe_state(self):
        capture = read(ROOT / "scripts" / "regression-harness" / "smart_edge_runtime_capture.py")
        post_switch = read(ROOT / "scripts" / "regression-harness" / "vpab_post_switch_capture.py")
        restore_body = re.search(
            r"def restore_safe_runtime_state\(ser, lines\):(?P<body>.*?)\n\n\ndef run_vpab_leg",
            capture,
            re.S,
        )
        self.assertIsNotNone(restore_body)
        for token in (
            "def restore_safe_runtime_state",
            '":set_mode=3"',
            '":mood=0.250"',
            '":palette_mode=on"',
            '":palette_index=29"',
            '":secondary_enabled=true"',
            '":secondary_control=false"',
            '":secondary_mode=7"',
            '":secondary_palette_mode=true"',
            '":secondary_palette_index=24"',
            '":edge_enabled=off"',
            '":edge_mode=off"',
            '":edge_strength=0"',
            '":smart_hooks=off"',
            '":smart_switching=off"',
            '":smart_assist=off"',
            "SMART_REFERENCE_CONFIDENCE_FLOOR = 0.080",
            "smart_confidence_command(SMART_REFERENCE_CONFIDENCE_FLOOR)",
            "finally:",
            "restore_safe_runtime_state(ser, lines)",
        ):
            self.assertIn(token, capture)
        for token in (
            "def stop_capture_only",
            '":vpab=stop"',
            '":vp_perf=stop"',
            "finally:",
            "stop_capture_only(ser, lines)",
        ):
            self.assertIn(token, post_switch)

    def test_runtime_capture_script_has_explicit_smart_floor_override(self):
        capture = read(ROOT / "scripts" / "regression-harness" / "smart_edge_runtime_capture.py")
        self.assertIn("def smart_confidence_command(value):", capture)
        self.assertIn("SMART_REFERENCE_CONFIDENCE_FLOOR = 0.080", capture)
        self.assertIn('"--smart-confidence-floor"', capture)
        self.assertIn("default=SMART_REFERENCE_CONFIDENCE_FLOOR", capture)
        self.assertIn("smart_confidence_command(smart_confidence_floor)", capture)
        self.assertIn("smart_confidence_command(SMART_REFERENCE_CONFIDENCE_FLOOR)", capture)
        self.assertNotIn('":smart_confidence_floor=0.620"', capture)
        self.assertNotIn('":smart_confidence_floor=0.180"', capture)

    def test_smart_director_default_floor_matches_runtime_evidence(self):
        smart_source = read(FIRMWARE / "sb_smart_director.cpp")
        self.assertIn("0.08f", smart_source)
        self.assertNotIn("0.62f", smart_source)

    def test_smart_runtime_configs_are_critical_section_snapshots(self):
        smart_header = read(FIRMWARE / "sb_smart_director.h")
        smart_source = read(FIRMWARE / "sb_smart_director.cpp")
        hooks_source = read(FIRMWARE / "sb_visual_hooks.cpp")
        edge_source = read(FIRMWARE / "k1_edgemixer.cpp")
        mode_source = read(FIRMWARE / "sb_mode_selection.cpp")
        serial_source = read(FIRMWARE / "serial_menu.h")

        self.assertIn("SBSmartDirectorConfig sb_smart_director_config();", smart_header)
        self.assertNotIn("const SBSmartDirectorConfig& sb_smart_director_config()", smart_header)
        self.assertNotIn("const SBSmartDirectorConfig& smart", serial_source)
        for text, mux in (
            (smart_source, "sb_director_config_mux"),
            (hooks_source, "sb_hook_config_mux"),
            (edge_source, "k1_edge_config_mux"),
            (mode_source, "sb_mode_state_mux"),
        ):
            self.assertIn("portMUX_TYPE", text)
            self.assertIn(mux, text)
            self.assertIn("portENTER_CRITICAL", text)
            self.assertIn("portEXIT_CRITICAL", text)

    def test_serial_visual_mutations_mark_manual_owner(self):
        smart_header = read(FIRMWARE / "sb_smart_director.h")
        smart_source = read(FIRMWARE / "sb_smart_director.cpp")
        serial_source = read(FIRMWARE / "serial_menu.h")

        self.assertIn("sb_smart_director_mark_manual_control", smart_header)
        self.assertIn("sb_smart_director_clear_manual_control", smart_header)
        self.assertIn("sb_smart_director_manual_owner_active", smart_header)
        self.assertIn("sb_manual_control_last_ms", smart_source)
        self.assertIn("serial_hotkey_marks_manual_visual_control", serial_source)
        self.assertIn("serial_command_marks_manual_visual_control", serial_source)
        self.assertIn("SB_MANUAL_REASON_SERIAL_HOTKEY", serial_source)
        self.assertIn("SB_MANUAL_REASON_SERIAL_COMMAND", serial_source)
        self.assertIn('"set_mode"', serial_source)
        self.assertIn('"secondary_"', serial_source)
        self.assertIn('"edge_"', serial_source)
        self.assertIn('"smart_"', serial_source)
        smart_guard = re.search(
            r'if \(strncmp\(command_type, "smart_", 6\) == 0\) \{\s*return false;\s*\}',
            serial_source,
            re.S,
        )
        self.assertIsNotNone(smart_guard, "Smart control commands must not self-mark manual ownership")
        self.assertIn("SMART_MANUAL_OWNER_ACTIVE", serial_source)
        self.assertNotIn('strcmp(command_type, "smart_scene") != 0', serial_source)

    def test_manual_owner_audit_covers_operator_surfaces(self):
        serial_source = read(FIRMWARE / "serial_menu.h")
        body = function_body(serial_source, "serial_command_marks_manual_visual_control")
        self.assertIsNotNone(body)

        for command in (
            '"set_mode"',
            '"auto_color_shift"',
            '"photons"',
            '"chroma"',
            '"mood"',
            '"palette_mode"',
            '"palette_index"',
            '"preset"',
        ):
            self.assertIn(command, body)

        for command in (
            '"secondary_"',
            '"edge_"',
            '"vp_bloom_"',
            '"vp_wave_"',
        ):
            self.assertIn(command, body)

        for read_only_or_smart_control in (
            'strcmp(command_type, "secondary_status") == 0',
            'strcmp(command_type, "edge_status") != 0',
            'strncmp(command_type, "smart_", 6) == 0',
        ):
            self.assertIn(read_only_or_smart_control, body)

        hotkey_body = function_body(serial_source, "serial_hotkey_marks_manual_visual_control")
        self.assertIsNotNone(hotkey_body)
        for hotkey in ("'2'", "','", "'.'", "'/'", "'['", "']'"):
            self.assertIn(hotkey, hotkey_body)
        for non_visual_hotkey in ("'a'", "'s'", "'d'", "'f'", "'N'", "'Y'"):
            self.assertNotIn(non_visual_hotkey, hotkey_body)

    def test_smart_scene_preset_reproduces_l1_ab_runtime_recipe(self):
        serial_source = read(FIRMWARE / "serial_menu.h")
        self.assertIn("smart_scene=[off/assist/l1/auto]", serial_source)
        self.assertIn("sb_apply_smart_scene", serial_source)
        # The smart_scene HANDLER branch moved to serial_cmd_dispatch_smart_director()
        # in serial_cmd_handlers.cpp; sb_apply_smart_scene() (the scene recipe asserted
        # below) stays in serial_menu.h. Assert the handler branch against its new home.
        self.assertIn('strcmp(command_type, "smart_scene") == 0',
                      read(FIRMWARE / "serial_cmd_handlers.cpp"))
        self.assertIn('strcmp(scene, "assist") == 0', serial_source)
        self.assertIn('strcmp(scene, "control") == 0', serial_source)
        self.assertIn('strcmp(scene, "l1") == 0', serial_source)
        self.assertIn('strcmp(scene, "accent") == 0', serial_source)
        self.assertIn('strcmp(scene, "auto") == 0', serial_source)
        self.assertIn('strcmp(scene, "autonomy") == 0', serial_source)
        self.assertIn('strcmp(scene, "demo") == 0', serial_source)

        body = function_body(serial_source, "sb_apply_smart_scene")
        self.assertIsNotNone(body)
        for token in (
            "smart.enabled = true",
            "smart.assist_switching_enabled = true",
            "smart.director_autonomy_enabled = false",
            "smart.director_autonomy_enabled = true",
            "smart.confidence_floor = 0.080f",
            "smart.confidence_floor = 0.070f",
            "smart.min_dwell_ms = 12000UL",
            "smart.cooldown_ms = 12000UL",
            "smart.switch_window_ms = 90000UL",
            "smart.max_switches_per_window = 3",
            "hooks.enabled = true",
            "edge.enabled = true",
            "edge.mode = K1_EDGE_MIXER_COMPLEMENTARY",
            "edge.strength = 0.350f",
            "edge.strength = 0.650f",
            "edge.mode = K1_EDGE_MIXER_OFF",
            "edge.strength = 0.0f",
            "sb_smart_director_set_config(smart)",
            "sb_visual_hooks_set_config(hooks)",
            "k1_edgemixer_set_config(edge)",
            "sb_mode_selection_init(CONFIG.LIGHTSHOW_MODE, millis())",
            "sb_smart_director_clear_manual_control()",
        ):
            self.assertIn(token, body)
        self.assertNotIn("sb_smart_director_mark_manual_control", body)
        for forbidden in (
            "noise_transition_queued",
            "start_noise_cal",
            "CONFIG.PALETTE_INDEX =",
            "CONFIG.LIGHTSHOW_MODE =",
            "CONFIG.MOOD =",
            "save_config",
            "write_config",
        ):
            self.assertNotIn(forbidden, body)

    def test_primary_visual_typed_commands_are_colon_settable(self):
        # Phase A Lane 2, S4: the 23 pure CONFIG setters (incl. these primary
        # visual ones) were lifted VERBATIM out of parse_command's ladder into
        # serial/serial_cmd_handlers.cpp. Repointed (not weakened) — same command
        # strings and same CONFIG-write/clamp tokens, sourced from where the bodies
        # now live. The S3.0 serial_replay golden gates the behaviour-preservation.
        serial_source = read(FIRMWARE / "serial_cmd_handlers.cpp")
        for command in (
            '"photons"',
            '"chroma"',
            '"mood"',
            '"palette_mode"',
            '"palette_index"',
        ):
            self.assertIn(command, serial_source)
        for token in (
            "CONFIG.PHOTONS = constrain(value, 0.05f, 1.0f)",
            "CONFIG.CHROMA = constrain(value, 0.0f, 1.0f)",
            "CONFIG.MOOD = constrain(value, 0.0f, 1.0f)",
            "CONFIG.PALETTE_MODE_ENABLED = value",
            "CONFIG.PALETTE_INDEX = index",
            "serial_print_palette_line(\"PALETTE\", CONFIG.PALETTE_INDEX)",
        ):
            self.assertIn(token, serial_source)

    def test_smart_director_future_contract_avoids_parameter_only_assist_when_present(self):
        director_path = FIRMWARE / "sb_smart_director.cpp"
        mode_path = FIRMWARE / "sb_mode_selection.cpp"
        if not director_path.exists():
            self.skipTest("Smart Director Assist not implemented yet")
        text = read(director_path) + "\n" + read(mode_path)
        for token in (
            "SBModeIntent",
            "sb_mode_selection_resolve",
            "assist_switching_enabled",
            "director_autonomy_enabled",
            "palette_overlay_enabled",
            "sb_palette_for_state",
            "sb_autonomy_palette_for_state",
            "sb_autonomy_mode_for_state",
            "sb_auto_colour_for_state",
            "PALETTE_MODE_ENABLED",
            "PALETTE_INDEX",
            "AUTO_COLOR_SHIFT",
            "sb_smart_director_read_output",
            "sb_smart_director_manual_owner_active",
            "g_last_encoder_activity_time",
            "mode_transition_queued",
            "fallback_mode != sb_mode_state.fallback_mode",
            "LIGHT_MODE_BLOOM",
            "LIGHT_MODE_BLOOM_FAST",
            "LIGHT_MODE_WAVEFORM",
            "LIGHT_MODE_WAVEFORM_FAST",
            "LIGHT_MODE_WAVEFORM_HYBRID",
            "LIGHT_MODE_SPECTRUM_RIVER",
            "LIGHT_MODE_COMET",
            "8000UL",
            "20000UL",
            "60000UL",
        ):
            self.assertIn(token, text)
        for excluded in (
            "LIGHT_MODE_QUANTUM_COLLAPSE:",
            "LIGHT_MODE_KALEIDOSCOPE:",
            "LIGHT_MODE_GDFT:",
            "LIGHT_MODE_GDFT_CHROMAGRAM:",
            "LIGHT_MODE_GDFT_CHROMAGRAM_DOTS:",
        ):
            self.assertNotIn(excluded, text)
        self.assertNotIn("parameter-only", text.lower())
        self.assertNotIn("no mode switching", text.lower())

        ino_text = read(FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino")
        self.assertIn("smart_boundary_gate_required", ino_text)
        self.assertIn("!smart_director_config.director_autonomy_enabled", ino_text)
        self.assertRegex(
            text,
            r"if\s*\(\s*!intent\.wants_switch\s*\)\s*\{[^}]*resolved_mode\s*=\s*sb_mode_state\.applied_mode;[^}]*return\s+resolved_mode;",
            "Enabled-but-no-switch frames must hold the last smart-applied mode.",
        )

    def test_smart_autonomy_palette_overlay_is_renderparams_local(self):
        smart_header = read(FIRMWARE / "sb_smart_director.h")
        smart_source = read(FIRMWARE / "sb_smart_director.cpp")
        serial_source = read(FIRMWARE / "serial_menu.h")
        combined = smart_header + "\n" + smart_source

        for token in (
            "bool palette_overlay_enabled;",
            "uint8_t palette_index;",
            "bool auto_colour_shift;",
            "output.palette_overlay_enabled",
            "params->PALETTE_MODE_ENABLED = true",
            "params->PALETTE_INDEX = output.palette_index",
            "params->AUTO_COLOR_SHIFT = output.auto_colour_shift",
            "SMART_PALETTE_OVERLAY",
            "SMART_PALETTE_INDEX",
            "SMART_AUTO_COLOUR_SHIFT",
        ):
            self.assertIn(token, combined + "\n" + serial_source)

        apply_body = re.search(
            r"void\s+sb_smart_director_apply_render_params\s*\([^)]*\)\s*\{(?P<body>.*?)\n\}",
            smart_source,
            re.S,
        )
        self.assertIsNotNone(apply_body)
        for forbidden in (
            "CONFIG.PALETTE_INDEX =",
            "CONFIG.PALETTE_MODE_ENABLED =",
            "CONFIG.AUTO_COLOR_SHIFT =",
        ):
            self.assertNotIn(forbidden, apply_body.group("body"))

    def test_supported_smart_modes_honour_renderparams_palette_overlay(self):
        for filename in (
            "light_mode_bloom.cpp",
            "light_mode_waveform.cpp",
            "light_mode_waveform_fast.cpp",
            "light_mode_waveform_hybrid.cpp",
            "light_mode_vu.cpp",
        ):
            text = read(FIRMWARE / filename)
            self.assertIn("render_params_palette_owns_colour(rp, render_secondary)", text, filename)
            self.assertIn("render_params_palette_index(rp, render_secondary)", text, filename)

        helpers = read(FIRMWARE / "lightshow_modes.h")
        self.assertIn("render_params_auto_colour_shift", helpers)
        self.assertIn("palette_index_with_phase(uint8_t palette_index, const RenderParams* rp, bool render_secondary)", helpers)

    @staticmethod
    def _strip_onset_v2_blocks(text):
        """Remove #ifdef SB_ONSET_V2 ... [#else ...] #endif regions, keeping only
        the PRODUCTION (no-flag) path. The donor-shaped SB_ONSET_V2 detector is an
        intentional, flag-gated addition; this guard test asserts the PRODUCTION
        onset path stays decoupled from donor internals, so it must scope its
        checks to the non-V2 code (mirrors the byte-identical-production contract).
        """
        out = []
        # depth>0 means inside an SB_ONSET_V2 #ifdef; in_else means the #else
        # (production) arm of such a block, which we KEEP.
        skip_depth = 0
        keep_else = []
        lines = text.splitlines()
        i = 0
        nest = 0  # generic #if nesting inside a skipped region
        while i < len(lines):
            ln = lines[i]
            stripped = ln.strip()
            if skip_depth == 0 and re.match(r"#ifdef\s+SB_ONSET_V2\b", stripped):
                skip_depth = 1
                nest = 0
                i += 1
                continue
            if skip_depth > 0:
                if re.match(r"#if(def|ndef)?\b", stripped):
                    nest += 1
                elif re.match(r"#endif\b", stripped):
                    if nest == 0:
                        skip_depth = 0
                    else:
                        nest -= 1
                elif re.match(r"#else\b", stripped) and nest == 0:
                    # production arm of the SB_ONSET_V2 block -> keep what follows
                    skip_depth = 0
                    i += 1
                    # keep lines until the matching #endif
                    en = 0
                    while i < len(lines):
                        s2 = lines[i].strip()
                        if re.match(r"#if(def|ndef)?\b", s2):
                            en += 1
                        elif re.match(r"#endif\b", s2):
                            if en == 0:
                                break
                            en -= 1
                        out.append(lines[i])
                        i += 1
                    i += 1
                    continue
                i += 1
                continue
            out.append(ln)
            i += 1
        return "\n".join(out)

    def test_onset_future_contract_is_novelty_first_when_present(self):
        onset_path = FIRMWARE / "sb_onset_beat.cpp"
        audio_header = FIRMWARE / "sb_audio_snapshot.h"
        if not onset_path.exists():
            self.skipTest("Onset/beat lane not implemented yet")
        full_text = read(onset_path)
        # Decoupling checks apply to the PRODUCTION path only; the SB_ONSET_V2
        # donor-shaped detector is flag-gated and legitimately references the
        # per-note spectrum + donor algorithm by name in its comments.
        text = self._strip_onset_v2_blocks(full_text)
        header = self._strip_onset_v2_blocks(read(audio_header))
        for token in (
            "audio.novelty",
            "audio.low_energy",
            "audio.peak_scaled",
            "audio.silence",
            "80UL",
            "event_age_ms",
            "beat_confidence",
            "sb_novelty_fast",
            "sb_novelty_slow",
            "sb_low_fast",
            "sb_low_slow",
            "sb_peak_fast",
            "sb_peak_slow",
            "sb_interval_estimate_ms",
            "sb_interval_close",
            "sb_note_accepted_interval",
            "portENTER_CRITICAL",
            "portEXIT_CRITICAL",
        ):
            self.assertIn(token, text + "\n" + header)
        for forbidden in (
            "OnsetDetector",
            "BeatTracker",
            "TempoTracker",
            "MusicalGrid",
            "ControlBusFrame",
            "spectrogram",
            "chromagram",
            "NUM_FREQS",
            "Serial.print",
            "USBSerial.print",
            "FastLED.show",
            "malloc",
            "new ",
            "String",
        ):
            self.assertNotIn(forbidden, text)
        # Silence branch: check on the V2-stripped (production) text so the
        # non-greedy brace match isn't tripped by nested V2 blocks. The shared
        # production silence semantics (no event_ms write, beat cleared) are what
        # this guard protects.
        silence_branch = re.search(
            r"if\s*\(\s*audio\.silence\s*\)\s*\{(?P<body>.*?)\n\s*\}",
            text,
            re.S,
        )
        self.assertIsNotNone(silence_branch)
        self.assertNotIn("event.event_ms = now_ms", silence_branch.group("body"))
        self.assertIn("event.beat_confidence = 0.0f", silence_branch.group("body"))
        self.assertIn("event.beat = false", silence_branch.group("body"))
        self.assertNotIn("else {\n    event.event_ms = now_ms;", text)

    def test_visual_hooks_l1_accent_contract_is_three_lane_and_default_off(self):
        hooks_path = FIRMWARE / "sb_visual_hooks.cpp"
        if not hooks_path.exists():
            self.skipTest("Visual hooks not implemented yet")
        hooks_header = read(FIRMWARE / "sb_visual_hooks.h")
        text = read(hooks_path)
        self.assertRegex(text, r"static\s+SBVisualHookConfig\s+sb_hook_config\s*=\s*\{\s*false,")
        self.assertIn("sb_visual_hooks_set_config", text)
        self.assertIn("80UL", text)
        self.assertIn("event.event_age_ms", text)
        self.assertIn("sb_visual_hooks_apply_render_params", text)
        self.assertIn("sb_visual_hooks_apply_edge_config", text)
        combined = hooks_header + "\n" + text
        for token in (
            "onset_tau_ms",
            "bass_tau_ms",
            "beat_tau_ms",
            "onset_to_photons",
            "bass_to_edge",
            "beat_to_chroma",
            "scalar_ceiling",
            "photon_scalar",
            "chroma_scalar",
            "edge_scalar",
            "sb_accent_onset_pulse",
            "sb_accent_bass_pulse",
            "sb_accent_beat_pulse",
            "sb_accent_last_onset_event_id",
            "sb_accent_last_bass_event_id",
            "sb_accent_last_beat_event_id",
        ):
            self.assertIn(token, combined)
        for legacy_token in (
            "sb_hook_pulse",
            "primary_pulse_strength",
            "secondary_edge_strength",
            "primary_pulse_scalar",
            "secondary_edge_strength_scalar",
            "output.primary_pulse_scalar",
        ):
            self.assertNotIn(legacy_token, combined)
        self.assertIn("event.event_age_ms", text)
        self.assertNotIn("now_ms - event.event_ms", text)
        self.assertIn("output.confirm_switch_boundary = true", text)
        beat_branch = text.index("if (eligible && event.beat")
        boundary_write = text.index("output.confirm_switch_boundary = true")
        self.assertLess(beat_branch, boundary_write)
        ino = read(FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino")
        self.assertIn("SBVisualHookOutput visual_hook_output = { 1.0f, 1.0f, 1.0f, false }", ino)

    def test_serial_smart_status_exposes_v2_percussive_channels(self):
        text = read(FIRMWARE / "serial_menu.h")
        for token in (
            "SMART_TRANSIENT:",
            "SMART_KICK:",
            "SMART_SNARE:",
            "SMART_HIHAT:",
            "SMART_TRANSIENT_LEVEL:",
            "SMART_KICK_LEVEL:",
            "SMART_SNARE_LEVEL:",
            "SMART_HIHAT_LEVEL:",
            "SMART_SNARE_EVENT_ID:",
            "SMART_HIHAT_EVENT_ID:",
        ):
            self.assertIn(token, text)
        self.assertIn("#ifdef SB_ONSET_V2", text)

    def test_render_integration_gates_switches_and_disabled_edgemixer(self):
        ino = read(FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino")
        self.assertIn("visual_hook_output.confirm_switch_boundary", ino)
        self.assertIn("smart_output.mode_intent.wants_switch = false", ino)
        self.assertIn("sb_smart_director_mode_selection_config(smart_now_ms)", ino)
        self.assertRegex(
            ino,
            r"if\s*\(\s*edge_config\.enabled\s*\)\s*\{[^}]*k1_edgemixer_apply",
            "Disabled EdgeMixer must not add an unconditional secondary render-path call.",
        )

    def test_plan_and_strategy_encode_assist_switching(self):
        combined = (read(PLAN) + "\n" + read(STRATEGY)).lower()
        self.assertIn("assist includes mode switching", combined)
        self.assertIn("mode switching is part of assist", combined)
        self.assertIn("parameter modulation", combined)
        self.assertNotIn("no mode switching", combined)
        self.assertNotIn("without changing modes", combined)


if __name__ == "__main__":
    unittest.main()
