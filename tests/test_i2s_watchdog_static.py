"""N2 freeze-guard — host structural gate (FIXED-state: pins the landed N2 fix).

Production-readiness Lane N2 fixes an UNRECOVERABLE audio-core freeze:
`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` `acquire_sample_chunk()` used to read
I2S with `portMAX_DELAY` (blocking the audio `loopTask` forever on a mic/DMA stall),
and NO task watchdog was subscribed anywhere to catch it — so a stall was never reset.

THIS IS THE FIXED-STATE GATE. The N2 fix has landed, gated by the single revert flag
`K1_AUDIO_FREEZE_GUARD_V1` (default ON in production). These assertions pin the fixed
structure: the production I2S read is BOUNDED (`pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS)`,
NOT `portMAX_DELAY`) with a zero-fill degrade-to-silence on timeout/short read; the
`#else` revert path keeps the original `portMAX_DELAY` blocking read byte-for-byte; and
`esp_task_wdt` / loop-WDT subscribe+feed exists on both the audio `loopTask` and the
render `led_task`. They go RED if the fix is ever reverted in part.

Efficacy itself is RUNTIME (FreeRTOS — the host cannot run it) and is proven
on-device: a deliberately-hung task must reset within the watchdog timeout, and a
normal soak must produce zero false resets. This gate only pins the structure so a
silent regression cannot land host-green.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
I2S_AUDIO = FIRMWARE / "audio" / "i2s_audio.h"
INO = FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino"
PLATFORMIO_INI = ROOT / "platformio.ini"


def _strip_line_comments(text: str) -> str:
    """Drop // line comments so prose mentioning portMAX_DELAY / esp_task_wdt does
    not get confused with code. (The two comment-only portMAX_DELAY at i2s_audio.h
    :30 and :276 must NOT count as the blocking read.)"""
    return "\n".join(ln.split("//", 1)[0] for ln in text.splitlines())


def _i2s_read_calls(text: str):
    """Every i2s_channel_read(...) call in code (comments stripped), in source
    order. After N2 there are two: the bounded production read (#ifdef branch) and
    the portMAX_DELAY revert read (#else branch)."""
    code = _strip_line_comments(text)
    calls = re.findall(r"i2s_channel_read\s*\([^;{}]*\)\s*;", code, re.S)
    assert calls, "expected at least one i2s_channel_read(...) call in i2s_audio.h"
    return calls


def test_i2s_read_is_bounded():
    """FIXED: the production read (under K1_AUDIO_FREEZE_GUARD_V1) is BOUNDED with
    pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS), NOT portMAX_DELAY; the #else revert read
    still uses portMAX_DELAY (revert path intact)."""
    calls = _i2s_read_calls(I2S_AUDIO.read_text(encoding="utf-8"))

    bounded = [c for c in calls if "pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS)" in c]
    assert bounded, (
        "expected the production i2s_channel_read to use "
        "pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS) (bounded read); none found."
    )
    assert all("portMAX_DELAY" not in c for c in bounded), (
        "the bounded production read must NOT use portMAX_DELAY."
    )

    revert = [c for c in calls if "portMAX_DELAY" in c]
    assert revert, (
        "expected the #else revert path to keep a portMAX_DELAY i2s_channel_read "
        "(revert path must stay intact)."
    )


def test_i2s_degrade_present():
    """FIXED: a zero-fill degrade-to-silence exists, guarded by the
    timeout/short-read condition."""
    code = _strip_line_comments(I2S_AUDIO.read_text(encoding="utf-8"))
    assert "i2s_read_status != ESP_OK || bytes_read < bytes_requested" in code, (
        "expected the degrade guard "
        "(i2s_read_status != ESP_OK || bytes_read < bytes_requested)."
    )
    assert re.search(r"i2s_samples_raw\[[^\]]+\]\s*=\s*0\s*;", code), (
        "expected a zero-fill of i2s_samples_raw[...] (degrade-to-silence)."
    )


def test_loop_watchdog_subscribed_and_fed():
    """FIXED: the .ino reconfigures the TWDT, subscribes the audio loopTask, and
    feeds it every loop iteration."""
    code = _strip_line_comments(INO.read_text(encoding="utf-8"))
    for sym in ("esp_task_wdt_reconfigure", "enableLoopWDT()", "feedLoopWDT()"):
        assert sym in code, f"expected {sym} in {INO.name}"


def test_led_task_watchdog():
    """FIXED: led_thread subscribes itself (esp_task_wdt_add(NULL)) and feeds the
    render-task watchdog (esp_task_wdt_reset())."""
    code = _strip_line_comments(INO.read_text(encoding="utf-8"))
    m = re.search(r"void\s+led_thread\s*\(", code)
    assert m, "expected a led_thread() definition in the .ino"
    region = code[m.start():]
    assert "esp_task_wdt_add(NULL)" in region, (
        "expected esp_task_wdt_add(NULL) inside led_thread (self-subscribe)."
    )
    assert "esp_task_wdt_reset()" in region, (
        "expected esp_task_wdt_reset() inside led_thread (per-frame feed)."
    )


def test_freeze_guard_flag_enabled():
    """FIXED: platformio.ini [env:k1_hardware] build_flags enable
    -DK1_AUDIO_FREEZE_GUARD_V1 (default ON; k1_bench_reference inherits it)."""
    text = PLATFORMIO_INI.read_text(encoding="utf-8")
    m = re.search(r"^\[env:k1_hardware\]\s*$", text, re.M)
    assert m, "expected an [env:k1_hardware] section in platformio.ini"
    # Section body runs until the next [section] header (or EOF).
    nxt = re.search(r"^\[", text[m.end():], re.M)
    body = text[m.end():] if not nxt else text[m.end(): m.end() + nxt.start()]
    body = _strip_line_comments(body)
    assert "-DK1_AUDIO_FREEZE_GUARD_V1" in body, (
        "expected -DK1_AUDIO_FREEZE_GUARD_V1 in [env:k1_hardware] build_flags "
        "(N2 freeze-guard default ON)."
    )
