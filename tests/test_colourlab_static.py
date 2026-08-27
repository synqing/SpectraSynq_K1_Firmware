"""Static allowlist / clamp / profile gates for Colour Lab web core."""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from colourlab_node import CORE, call_core, require_core

ROOT = Path(__file__).resolve().parents[1]
SERIAL_MENU = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"
COLOUR_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_colour_lab.h"
COLOUR_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "k1_colour_lab.cpp"
CONFIG_TYPES = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "config_types.h"
PIO = ROOT / "platformio.ini"
WIRELESS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control" / "k1_control_facade.cpp"
CORE_SRC = require_core()
INDEX = ROOT / "tools" / "colourlab" / "index.html"
WORKBENCH_APP = ROOT / "tools" / "colourlab" / "colourlab-workbench.js"
GENERATOR = ROOT / "tests" / "generate_colourlab_fixtures.py"

COLOUR_LAB_NAMES = (
    "paint",
    "paint_target",
    "paint_rgb",
    "paint_sv",
    "paint_stops",
    "paint_status",
    "tune_gain",
    "tune_gamma",
    "tune_reset",
    "tune_save",
    "tune_status",
)


def _manual_commands() -> set[str]:
    text = SERIAL_MENU.read_text(encoding="utf-8")
    m = re.search(
        r"static const char\* const manual_commands\[\] = \{(.*?)\};",
        text,
        re.S,
    )
    assert m, "manual_commands array not found"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def test_core_is_umd_and_exports_colourlab():
    src = CORE_SRC.read_text(encoding="utf-8")
    assert "module.exports" in src
    assert "ColourLab" in src
    assert "Web Serial" not in src or "No Web Serial" in src
    assert "document." not in src
    assert "navigator.serial" not in src
    consts = call_core({"op": "constants"})
    assert consts["COLOUR_LAB_COMMANDS"] == list(COLOUR_LAB_NAMES)
    assert consts["COMMANDS"][:11] == list(COLOUR_LAB_NAMES)
    assert "chip_id" in consts["COMMANDS"]
    assert "build" in consts["COMMANDS"]
    assert "look_status" in consts["COMMANDS"]


def test_colour_lab_commands_are_on_serial_allowlist():
    allowed = _manual_commands()
    missing = [n for n in COLOUR_LAB_NAMES if n not in allowed]
    assert missing == [], f"not on manual_commands: {missing}"


def test_profiling_commands_exist_in_serial_source():
    menu = SERIAL_MENU.read_text(encoding="utf-8")
    assert "void cmd_chip_id()" in menu
    assert "void cmd_build()" in menu
    assert 'strcmp(command_buf, "look_status")' in menu


def test_clamps_match_firmware_header():
    header = COLOUR_H.read_text(encoding="utf-8")
    consts = call_core({"op": "constants"})
    assert "#define K1_COLOUR_LAB_GAIN_MIN 0.0f" in header
    assert "#define K1_COLOUR_LAB_GAIN_MAX 2.0f" in header
    assert "#define K1_COLOUR_LAB_GAMMA_MIN 0.20f" in header
    assert "#define K1_COLOUR_LAB_GAMMA_MAX 4.00f" in header
    assert "#define K1_COLOUR_LAB_BOTH_SCALE 0.30f" in header
    assert "#define K1_COLOUR_LAB_MAX_STOPS 8" in header
    assert consts["GAIN_MIN"] == 0.0
    assert consts["GAIN_MAX"] == 2.0
    assert consts["GAMMA_MIN"] == 0.20
    assert consts["GAMMA_MAX"] == 4.00
    assert consts["BOTH_SCALE"] == 0.30
    assert consts["MAX_STOPS"] == 8
    assert consts["PAINT_STOPS_MAX_CHARS"] == 158
    assert consts["SAFETY_TIMEOUT_MS"] == 800
    assert consts["DISCONNECT_WAIT_MS"] == 1200
    cpp = COLOUR_CPP.read_text(encoding="utf-8")
    assert "strlen(s) >= sizeof(buf) - 1" in cpp
    assert "char buf[160];" in cpp


def test_env_profiles_match_source():
    consts = call_core({"op": "constants"})
    profiles = consts["ENV_PROFILES"]
    cfg = CONFIG_TYPES.read_text(encoding="utf-8")
    pio = PIO.read_text(encoding="utf-8")

    main = profiles["k1_main_rpl_im69d"]
    assert main["chip_id"] == "9087A500"
    assert main["primary_led_count"] == 160
    assert main["secondary_led_count"] == 160
    assert main["both_scale_enabled"] is True
    assert main["both_scale"] == 0.30
    assert main["slot15_supported"] is True
    assert main["look_backend"] == "ws2816_u16"
    assert "-DK1_WS2816_LEVER2_V1" in pio
    assert "-DK1_LOOK_LIB_V1" in pio

    bench = profiles["k1_bench_im69d_led150"]
    assert bench["chip_id"] == "B489A500"
    assert bench["primary_led_count"] == 150
    assert bench["secondary_led_count"] == 150
    assert bench["both_scale_enabled"] is False
    assert bench["slot15_supported"] is False
    assert bench["look_backend"] == "ws2812_u8"
    assert "K1_BENCH_LED150_GPIO39_40_V1" in cfg
    assert "#define LED_COUNT_VALUE 150" in cfg
    assert "#define SECONDARY_LED_COUNT_VALUE 150" in cfg
    assert "-DK1_LOOK_LIB_WS2812_V1" in pio

    assert set(profiles) == {"k1_main_rpl_im69d", "k1_bench_im69d_led150"}


def test_no_wireless_colour_lab_path():
    wireless = WIRELESS.read_text(encoding="utf-8")
    for name in COLOUR_LAB_NAMES:
        assert f'"{name}"' not in wireless, f"{name} leaked onto wireless allowlist"


def test_no_firmware_or_platformio_edits():
    """The Colour Lab change set must not modify firmware.

    Scoped to the STAGED set (`--cached`), not the whole working tree. The claim
    this gate exists to defend is "this commit does not touch firmware" — not
    "nobody anywhere in the checkout has a dirty firmware file". Against the
    working tree it went red whenever an unrelated lane had an uncommitted
    firmware edit, which is a false failure with nothing to do with Colour Lab.
    At commit time the staged set is exactly the lane-owned change set.
    """
    proc = subprocess.run(
        [
            "git",
            "diff",
            "--cached",
            "--name-only",
            "HEAD",
            "--",
            "SPECTRASYNQ_K1_FIRMWARE",
            "platformio.ini",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "", (
        "staged change set modifies firmware or platformio.ini:\n" + proc.stdout
    )


def test_generator_can_emit_160_and_150():
    src = GENERATOR.read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "SUITES" in src
    assert "160" in src and "150" in src
    assert "--n" in src
    assert "both_scale_enabled" in src


def test_index_html_if_present_imports_core_without_duplicate_math():
    if not INDEX.is_file():
        return
    html = INDEX.read_text(encoding="utf-8")
    assert "colourlab-core.js" in html
    assert "colourlab_engine.js" not in html
    banned = (
        "function hsv(",
        "function curveU16(",
        "function lutLerp1d(",
        "function createLineParser(",
        "function createCommandQueue(",
    )
    for token in banned:
        assert token not in html, f"index.html must not re-derive {token}"


def test_preview_render_comparison_and_inspector_share_resolved_channel_frames():
    html = INDEX.read_text(encoding="utf-8")
    app = WORKBENCH_APP.read_text(encoding="utf-8")
    assert 'id="primaryPattern"' in html
    assert 'id="secondaryCorrection"' in html
    assert 'id="selectedLedInput"' in html
    assert "var stageFrames = { primary: null, secondary: null };" in app

    inspect = re.search(r"function renderInspector\(safetyBlocked\) \{(.*?)\n  \}", app, re.S)
    assert inspect, "renderInspector() missing"
    inspect_body = inspect.group(1)
    assert "CL.inspectStageFrame(stageFrames.primary, selectedLed)" in inspect_body
    assert "CL.inspectStageFrame(stageFrames.secondary, selectedLed)" in inspect_body
    assert "CL.stageFrame" not in inspect_body
    assert "CL.renderChannel" not in inspect_body

    assert 'stageFrames.primary = CL.stageFrame' in app
    assert 'stageFrames.secondary = CL.stageFrame' in app
    assert "CL.compareStageFrames(stageFrames.primary, stageFrames.secondary)" in app
    assert 'drawStrip($("primaryCanvas"), stageFrames.primary' in app
    assert 'drawStrip($("secondaryCanvas"), stageFrames.secondary' in app
    assert "function bindPreviewStrip(which)" in app
    assert "setSelectedLed(index, \"pointer\", false)" in app
    assert "device-reported LUT" not in html + app


def test_disconnect_waits_for_this_turn_stop_before_close():
    app = WORKBENCH_APP.read_text(encoding="utf-8")
    match = re.search(r"async function disconnect\(\) \{(.*?)\n  \}", app, re.S)
    assert match, "disconnect() missing"
    body = match.group(1)
    assert "classifyDisconnectShutdown" in body
    assert "enqueuePriorityStop" in body
    assert "port.close" in body
    assert body.index("enqueuePriorityStop") < body.index("port.close")
    assert body.index("classifyDisconnectShutdown") < body.index("port.close")
    assert 'paintStopped: stopped' not in body
    assert 'confirmed.paint && state.confirmed.paint.mode === "off"' not in body
