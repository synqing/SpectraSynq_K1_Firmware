"""Static locks for fps/agc clock decoupling (handover hybrid r1)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
MANIFEST = ROOT / "scripts" / "platformio" / "k1_device_identities.json"
LED = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h"
I2S = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h"
GDFT = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_gdft_core.cpp"
INO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino"
SERIAL = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp"
TYPED_DEF = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_typed_cmd_table.def"
PROBE = "k1_main_rpl_fps_agc_probe"


def _env_block(text: str, env_name: str) -> str:
    pattern = rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)"
    match = re.search(pattern, text, flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_probe_env_is_non_shippable_rpl_only():
    ini = PLATFORMIO.read_text(encoding="utf-8")
    block = _env_block(ini, PROBE)
    assert "NON-SHIPPABLE" in block
    assert "extends = env:k1_main_rpl_im69d" in block
    assert "-DENABLE_VP_PERF_AUDIT=1" in block
    assert "-DK1_SHOW_SKIP_DISCRIMINATOR_V1=1" in block
    assert "-DK1_AGC_DT_CLOCK_V1=0" in block
    assert "-DK1_RMT_ALLOC_ON_VP_CORE_V1=1" in block
    assert "-DENABLE_AP_FRONTEND_DEBUG=1" in block
    rpl = _env_block(ini, "k1_main_rpl_im69d")
    assert "-DENABLE_VP_PERF_AUDIT" not in rpl
    assert "-DK1_SHOW_SKIP_DISCRIMINATOR" not in rpl
    assert "-DK1_RMT_ALLOC_ON_VP_CORE_V1=1" in rpl
    hw = _env_block(ini, "k1_hardware")
    assert "-DK1_RMT_ALLOC_ON_VP_CORE_V1" not in hw


def test_probe_identity_is_9087_only():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_chip = {a["chip_id"]: a["envs"] for a in data["authorized"]}
    assert PROBE in by_chip["9087A500"]
    assert PROBE not in by_chip["F887A500"]
    assert PROBE not in by_chip["B489A500"]


def test_lever2_pack_show_timers_are_before_return():
    led = LED.read_text(encoding="utf-8")
    start = led.index("#ifdef K1_WS2816_LEVER2_V1")
    ret = led.index("return;", led.index("k1_lever2_pack_frame", start))
    block = led[start:ret]
    assert "vp_perf_record" in block
    assert "vp_perf.pack" in block
    assert "vp_perf.show" in block
    assert "FastLED.show()" in block


def test_rmt_alloc_on_vp_core_skips_core0_show():
    led = LED.read_text(encoding="utf-8")
    ino = INO.read_text(encoding="utf-8")
    assert "K1_RMT_ALLOC_ON_VP_CORE_V1" in led
    assert "xPortGetCoreID() != K1_LED_TASK_CORE" in led
    assert "RMT_ALLOC: first_show core=" in led
    assert "#if K1_RMT_ALLOC_ON_VP_CORE_V1" in ino
    assert "#if !K1_RMT_ALLOC_ON_VP_CORE_V1" in ino
    assert "FastLED.show();" in ino
    setup = ino[ino.index("void setup()") : ino.index("void led_thread")]
    led_head = ino[ino.index("void led_thread") : ino.index("while (true) {", ino.index("void led_thread"))]
    assert "intro_animation();" in setup
    assert setup.index("#else") < setup.index("intro_animation();")
    assert "intro_animation();" in led_head
    assert 'INTRO: vp_core' in led_head


def test_show_skip_command_and_render_gate_exist():
    typed = TYPED_DEF.read_text(encoding="utf-8")
    assert 'SERIAL_TYPED_CMD("show_skip"' in typed
    serial = SERIAL.read_text(encoding="utf-8")
    assert "void show_skip_command" in serial
    assert 'strcmp(command_type, "show_skip") == 0' in serial
    ino = INO.read_text(encoding="utf-8")
    assert "K1_SHOW_SKIP_DISCRIMINATOR_V1" in ino
    assert "k1_show_skip_until_ms" in ino


def test_agc_env_print_is_four_decimals_and_comments_are_live():
    i2s = I2S.read_text(encoding="utf-8")
    gdft = GDFT.read_text(encoding="utf-8")
    assert "agc_env=%.4f" in i2s
    assert "agc_env=%.3f" not in i2s
    assert "dead code on hardware" not in i2s
    assert "effectively inert on hardware" not in gdft
    assert "Bidirectional dumps" in gdft


def test_vpf_stream_prints_pack_us_before_show_us():
    serial = SERIAL.read_text(encoding="utf-8")
    pack_at = serial.index(",pack_us=")
    show_at = serial.index(",show_us=")
    assert pack_at < show_at


def test_low_pass_array_not_dt_warped():
    gdft = GDFT.read_text(encoding="utf-8")
    assert "low_pass_array(magnitudes_final, magnitudes_last, NUM_FREQS, SYSTEM_FPS" in gdft
