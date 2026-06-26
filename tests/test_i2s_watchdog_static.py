"""N2 freeze-guard — host structural gate (LOCK: characterizes the pre-N2 state).

Production-readiness Lane N2 fixes an UNRECOVERABLE audio-core freeze:
`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h` `acquire_sample_chunk()` reads I2S with
`portMAX_DELAY` (blocks the audio `loopTask` forever on a mic/DMA stall), and NO
task watchdog is subscribed anywhere to catch it — so a stall is never reset.

THIS IS THE LOCK COMMIT. It asserts the CURRENT (pre-fix) reality — the blocking
read is present and no watchdog exists — so it is GREEN now with ZERO firmware
source change. The N2 FIX commit REPLACES these two assertions with the fixed-state
invariants (bounded I2S timeout + zero-fill degrade + `esp_task_wdt` subscribe/feed
on `loopTask`+`led_task`); those go RED if the fix is ever reverted.

Efficacy itself is RUNTIME (FreeRTOS — the host cannot run it) and is proven
on-device: a deliberately-hung `loopTask` must reset within the watchdog timeout,
and a normal soak must produce zero false resets. This gate only pins the structure
so a silent regression cannot land host-green.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
I2S_AUDIO = FIRMWARE / "audio" / "i2s_audio.h"

_SRC_SUFFIXES = (".h", ".cpp", ".ino", ".c")
_WDT_SYMBOLS = ("esp_task_wdt", "enableLoopWDT", "feedLoopWDT")


def _strip_line_comments(text: str) -> str:
    """Drop // line comments so prose mentioning portMAX_DELAY / esp_task_wdt does
    not get confused with code. (The two comment-only portMAX_DELAY at i2s_audio.h
    :30 and :276 must NOT count as the blocking read.)"""
    return "\n".join(ln.split("//", 1)[0] for ln in text.splitlines())


def _production_i2s_read_call(text: str) -> str:
    code = _strip_line_comments(text)
    m = re.search(r"i2s_channel_read\s*\([^;{}]*\)\s*;", code, re.S)
    assert m, "expected a single i2s_channel_read(...) call in i2s_audio.h"
    return m.group(0)


def test_i2s_read_blocks_forever_pre_n2():
    """LOCK: the production I2S read still uses portMAX_DELAY (the freeze bug)."""
    call = _production_i2s_read_call(I2S_AUDIO.read_text(encoding="utf-8"))
    assert "portMAX_DELAY" in call, (
        "LOCK characterization failed: the i2s_channel_read no longer uses "
        "portMAX_DELAY. If the N2 FIX has landed, REPLACE this file's assertions "
        "with the fixed-state invariants (bounded timeout + zero-fill degrade + "
        "esp_task_wdt subscribe/feed)."
    )


def test_no_task_watchdog_pre_n2():
    """LOCK: zero esp_task_wdt / loop-WDT in firmware (the freeze is uncaught)."""
    hits = []
    for path in FIRMWARE.rglob("*"):
        if path.suffix in _SRC_SUFFIXES and path.is_file():
            code = _strip_line_comments(path.read_text(encoding="utf-8", errors="ignore"))
            for sym in _WDT_SYMBOLS:
                if sym in code:
                    hits.append(f"{path.relative_to(FIRMWARE)}:{sym}")
    assert hits == [], (
        f"LOCK characterization failed: expected ZERO watchdog symbols pre-N2, "
        f"found {hits}. If the N2 FIX has landed, replace these assertions with the "
        f"fixed-state invariants."
    )
