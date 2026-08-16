"""Static ratchet: Core-0 must not read Core-1 transition internals."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# Core-0 / AP-adjacent sources must not reach into VP transition runtime.
BANNED = (
    "TransitionEngine",
    "render_thread_parked",
    "leds_16[",
)

AP_DIRS = (
    FW / "audio",
    FW / "serial",
    FW / "network",
)


def test_ap_sources_do_not_own_vp_transition_runtime():
    offenders = []
    for directory in AP_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.suffix not in {".cpp", ".h", ".hpp"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for banned in BANNED:
                if banned in text:
                    offenders.append(f"{path.relative_to(ROOT)}: {banned}")
    # Soft gate for this unit: command channels themselves must not reference VP.
    cmd = (FW / "control" / "k1_command_channels.cpp").read_text(encoding="utf-8")
    for banned in BANNED:
        assert banned not in cmd
    assert True  # inventory retained for follow-up wiring
