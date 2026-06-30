"""N7 OTA receiver — host structural gate (DEFAULT-OFF DRAFT, Captain decision D3).

Lane N7 adds a flag-gated on-device OTA receiver (system/k1_ota.{h,cpp}) so backers
can patch field bugs at enablement. It is scaffold ONLY: SB_ENABLE_OTA defaults 0 on
every target and the entire receiver compiles to nothing in shipping builds. These
assertions pin that contract so OTA cannot silently go live, and so the esp_ota
rollback/anti-brick path stays wired:

  1. SB_ENABLE_OTA is defined 0 by default in system/constants.h (no unconditional
     `#define SB_ENABLE_OTA 1` anywhere in firmware source).
  2. The receiver TU system/k1_ota.cpp is fully behind `#if SB_ENABLE_OTA` — the only
     code before the guard is the header include.
  3. esp_ota rollback is referenced (esp_ota_mark_app_valid_cancel_rollback) and the
     boot-health mark is called from setup() behind `#if SB_ENABLE_OTA`.
  4. Gate integrity: the k1_ota_probe env flips the flag ON (-DSB_ENABLE_OTA=1),
     k1_ota.cpp is in the k1_hardware build_src_filter allowlist, and k1_ota_probe is
     registered in the upload guard (drift-catcher / anti-brick).

Efficacy (a real OTA write + rollback-on-failed-boot) is RUNTIME on hardware and
out of scope for D3 — this gate only proves the flag-OFF no-op and the link surface.
"""
import re
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _fwpath import FwDir  # noqa: E402

FW = FwDir(ROOT / "SPECTRASYNQ_K1_FIRMWARE")
CONSTANTS = FW / "constants.h"
OTA_CPP = FW / "k1_ota.cpp"
OTA_H = FW / "k1_ota.h"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
PLATFORMIO_INI = ROOT / "platformio.ini"
UPLOAD_GUARD = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"


def _strip_line_comments(text: str) -> str:
    return "\n".join(ln.split("//", 1)[0] for ln in text.splitlines())


def test_flag_defaults_off_in_constants():
    code = _strip_line_comments(CONSTANTS.read_text(encoding="utf-8"))
    assert re.search(r"#define\s+SB_ENABLE_OTA\s+0", code), \
        "SB_ENABLE_OTA must default to 0 in constants.h"
    # It must be a guarded default so a build flag can override it, never forced 0.
    assert re.search(r"#ifndef\s+SB_ENABLE_OTA", code), \
        "SB_ENABLE_OTA default must be #ifndef-guarded so -DSB_ENABLE_OTA=1 wins"


def test_no_unconditional_enable_in_firmware_source():
    # No firmware .cpp/.h/.ino may hard-enable OTA; only the probe env (platformio.ini)
    # may pass -DSB_ENABLE_OTA=1.
    offenders = []
    for path in FW.rglob("*"):
        if path.suffix not in {".cpp", ".h", ".ino"}:
            continue
        code = _strip_line_comments(path.read_text(encoding="utf-8", errors="ignore"))
        if re.search(r"#define\s+SB_ENABLE_OTA\s+1", code):
            offenders.append(path.name)
    assert offenders == [], f"firmware source must not force SB_ENABLE_OTA=1: {offenders}"


def test_receiver_tu_is_fully_flag_gated():
    text = OTA_CPP.read_text(encoding="utf-8")
    assert "#if SB_ENABLE_OTA" in text, "k1_ota.cpp must guard its body with #if SB_ENABLE_OTA"
    # Everything before the guard must be only #include / comments / blank — so the
    # flag-OFF object is empty (true no-op in shipping builds).
    pre_guard = text.split("#if SB_ENABLE_OTA", 1)[0]
    for ln in _strip_line_comments(pre_guard).splitlines():
        s = ln.strip()
        if not s:
            continue
        assert s.startswith("#include"), \
            f"only includes may precede the SB_ENABLE_OTA guard in k1_ota.cpp; found: {s!r}"


def test_esp_ota_rollback_referenced():
    text = OTA_CPP.read_text(encoding="utf-8")
    assert "esp_ota_mark_app_valid_cancel_rollback" in text, \
        "anti-brick rollback API must be referenced in the receiver"
    # core esp_ota receiver surface present (link proof under the probe env)
    for sym in ("esp_ota_begin", "esp_ota_write", "esp_ota_end", "esp_ota_set_boot_partition"):
        assert sym in text, f"receiver must reference {sym}"


def test_boot_health_mark_called_from_setup_gated():
    text = INO.read_text(encoding="utf-8")
    assert "k1_ota_mark_app_valid_after_boot()" in text, \
        "setup() must call the boot-health rollback mark"
    # the call site must sit inside an #if SB_ENABLE_OTA region
    assert re.search(
        r"#if\s+SB_ENABLE_OTA.*?k1_ota_mark_app_valid_after_boot\(\).*?#endif",
        text, re.S,
    ), "the setup() rollback-mark call must be behind #if SB_ENABLE_OTA"


def test_probe_env_and_build_src_filter():
    ini = PLATFORMIO_INI.read_text(encoding="utf-8")
    assert "[env:k1_ota_probe]" in ini, "k1_ota_probe env must exist"
    assert "-DSB_ENABLE_OTA=1" in ini, "k1_ota_probe must flip SB_ENABLE_OTA=1"
    assert "+<system/k1_ota.cpp>" in ini, \
        "k1_ota.cpp must be in the k1_hardware build_src_filter allowlist"


def test_probe_env_registered_in_upload_guard():
    guard = UPLOAD_GUARD.read_text(encoding="utf-8")
    assert '"k1_ota_probe"' in guard, \
        "k1_ota_probe must be registered in k1_upload_guard.py K1_TARGETS (anti-brick)"


def test_header_declares_receiver_under_guard():
    text = OTA_H.read_text(encoding="utf-8")
    assert "#if SB_ENABLE_OTA" in text
    assert "serial_cmd_dispatch_ota" in text
    assert "k1_ota_mark_app_valid_after_boot" in text


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
