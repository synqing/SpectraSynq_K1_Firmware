"""Gate-7B: production persist/cache park without enabling the effect framework."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIO = ROOT / "platformio.ini"
GLOBALS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals.h"
BRIDGE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "persistence" / "bridge_fs.h"
INO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino"
PERSIST_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "persistence" / "k1_persistence_request.cpp"
SYSTEM_H = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "system.h"
SHOW_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control" / "k1_show_state.cpp"
QUEUE_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "control" / "k1_effect_queue.cpp"


def _k1_hardware_section() -> str:
    text = PIO.read_text(encoding="utf-8")
    start = text.index("[env:k1_hardware]\n")
    end = text.find("\n[env:", start + 1)
    return text[start : end if end >= 0 else len(text)]


def _fn_body(src: str, signature: str) -> str:
    idx = src.index(signature)
    brace = src.index("{", idx)
    depth = 0
    for i, ch in enumerate(src[brace:], brace):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[brace : i + 1]
    raise AssertionError(f"unbalanced body for {signature}")


def test_k1_hardware_enables_persist_park_not_effect_framework():
    section = _k1_hardware_section()
    assert "-DK1_PERSIST_PARK_V1=1" in section
    assert "-DK1_EFFECT_FRAMEWORK_V1" not in section


def test_park_macro_covers_framework_or_persist_park():
    text = GLOBALS.read_text(encoding="utf-8")
    assert "defined(K1_EFFECT_FRAMEWORK_V1) || defined(K1_PERSIST_PARK_V1)" in text
    assert "#ifdef K1_LED_PARK_V1" in text
    assert "inline volatile bool render_thread_parked" in text
    lock = _fn_body(text, "inline void lock_leds()")
    assert "led_thread_halt = true" in lock
    assert "render_thread_parked" in lock
    assert "led_task == nullptr" in lock


def test_led_task_parks_under_k1_led_park_v1():
    text = INO.read_text(encoding="utf-8")
    assert "#ifdef K1_LED_PARK_V1" in text
    assert "render_thread_parked = true" in text
    assert "vTaskDelay(1)" in text


def _failed_open_unlocks(body: str) -> bool:
    idx = body.find("if (!file)")
    if idx < 0:
        idx = body.find("if(!file)")
    if idx < 0:
        return False
    window = body[idx : idx + 600]
    return "unlock_leds();" in window


def test_save_config_unlocks_on_failed_open():
    body = _fn_body(BRIDGE.read_text(encoding="utf-8"), "void save_config()")
    assert _failed_open_unlocks(body)


def test_load_and_noise_cal_unlock_on_failed_open():
    text = BRIDGE.read_text(encoding="utf-8")
    assert _failed_open_unlocks(_fn_body(text, "void load_config()"))
    assert _failed_open_unlocks(_fn_body(text, "void save_ambient_noise_calibration()"))
    assert _failed_open_unlocks(_fn_body(text, "void load_ambient_noise_calibration()"))


def test_g7a_mailbox_is_not_the_flash_writer():
    persist = PERSIST_CPP.read_text(encoding="utf-8")
    for banned in ("LittleFS", "fopen", "SPIFFS", "nvs_set", "EEPROM"):
        assert banned not in persist
    system = SYSTEM_H.read_text(encoding="utf-8")
    settings = _fn_body(system, "void check_settings(uint32_t t_now)")
    assert "save_config();" in settings
    ino = INO.read_text(encoding="utf-8")
    assert "check_settings(t_now);" in ino
    assert "k1_persist_service_stub_once();" in ino


def test_runtime_littlefs_writers_park_core1():
    """Shift+S / preset-slot saves must park Core 1 like save_config.

    G7B closed the config debounce path; SHOW_STATE and PRESETS writers were
    still bare LittleFS opens while Core 1 could be mid-frame in PSRAM.
    """
    show = SHOW_CPP.read_text(encoding="utf-8")
    save = _fn_body(show, "bool k1_show_state_save()")
    assert "lock_leds();" in save
    assert _failed_open_unlocks(save)
    assert save.index("unlock_leds();") < save.index("save_config();")
    load = _fn_body(show, "bool k1_show_state_load()")
    assert "lock_leds();" in load
    assert _failed_open_unlocks(load)

    queue = QUEUE_CPP.read_text(encoding="utf-8")
    write = _fn_body(queue, "bool slots_write_file()")
    assert "lock_leds();" in write
    assert _failed_open_unlocks(write)
    ensure = _fn_body(queue, "void slots_ensure_loaded()")
    assert "lock_leds();" in ensure
    assert "unlock_leds();" in ensure
