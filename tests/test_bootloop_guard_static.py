"""N2b boot-loop guard — structural characterization gate (LOCK -> FIX).

Two-commit anti-gaming shape (as Lane N1 / N2):

  LOCK commit  (GUARD_WIRED = False): asserts the pre-N2b reality — no build flag,
                no RTC_NOINIT crash counter, no safe-mode branch, decision-core
                header untracked. Green against untouched firmware; the LOCK commit
                touches ZERO firmware source.
  FIX commit   (GUARD_WIRED = True):  flips the constant and asserts the guard is
                wired — flag present, RTC_NOINIT var + k1_bootloop_eval() in the
                .ino, the BOOT_LOOP_GUARD boot log, a non-destructive safe-mode
                branch in load_config(), the k1_boot_safe_mode global, and the
                tracked decision-core header (carrying the CTO-required version field).

The single-constant flip is the coupling proof: every assertion reads real firmware
files, so the FIX cannot land the wiring without also flipping this gate — and the
two-commit split means the firmware change lives only in the FIX commit.

The decision LOGIC itself (the 8 crash scenarios) is pinned separately by the
host-compile oracle `oracle_k1_bootloop` (golden master), not here. This file pins
the INTEGRATION wiring; the oracle pins the BEHAVIOUR.
"""
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FW = REPO / "SPECTRASYNQ_K1_FIRMWARE"
INO = FW / "SPECTRASYNQ_K1_FIRMWARE.ino"
BRIDGE_FS = FW / "persistence" / "bridge_fs.h"
GLOBALS_H = FW / "system" / "globals.h"
PLATFORMIO = REPO / "platformio.ini"
GUARD_HEADER_REL = "SPECTRASYNQ_K1_FIRMWARE/system/k1_bootloop_guard.h"

# FIX flips this to True (in the same commit that wires the guard).
GUARD_WIRED = False


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def _is_tracked(rel: str) -> bool:
    r = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "--error-unmatch", rel],
        capture_output=True, text=True,
    )
    return r.returncode == 0


def test_production_build_flag():
    """`-DK1_BOOTLOOP_GUARD_V1` ships in [env:k1_hardware] (bench inherits) iff wired."""
    present = "K1_BOOTLOOP_GUARD_V1" in _read(PLATFORMIO)
    assert present == GUARD_WIRED, (
        f"platformio.ini K1_BOOTLOOP_GUARD_V1 present={present}, expected {GUARD_WIRED}"
    )


def test_rtc_noinit_crash_counter_in_ino():
    """The crash counter lives in RTC_NOINIT memory, defined in the single .ino TU."""
    present = "RTC_NOINIT_ATTR" in _read(INO)
    assert present == GUARD_WIRED, (
        f".ino RTC_NOINIT_ATTR present={present}, expected {GUARD_WIRED}"
    )


def test_guard_evaluated_in_setup():
    """setup() evaluates the boot-loop decision core before the first heap alloc."""
    present = "k1_bootloop_eval(" in _read(INO)
    assert present == GUARD_WIRED, (
        f".ino k1_bootloop_eval() call present={present}, expected {GUARD_WIRED}"
    )


def test_boot_log_token_in_ino():
    """A visible BOOT_LOOP_GUARD serial line reports reset_reason / streak / safe_mode."""
    present = "BOOT_LOOP_GUARD" in _read(INO)
    assert present == GUARD_WIRED, (
        f".ino BOOT_LOOP_GUARD log present={present}, expected {GUARD_WIRED}"
    )


def test_safe_mode_branch_in_load_config():
    """load_config() honours safe mode (non-destructive defaults-in-RAM) iff wired."""
    present = "k1_boot_safe_mode" in _read(BRIDGE_FS)
    assert present == GUARD_WIRED, (
        f"bridge_fs.h k1_boot_safe_mode branch present={present}, expected {GUARD_WIRED}"
    )


def test_safe_mode_global_declared():
    """The safe-mode flag is a global (globals.h extern), visible to setup + load_config."""
    present = "k1_boot_safe_mode" in _read(GLOBALS_H)
    assert present == GUARD_WIRED, (
        f"globals.h k1_boot_safe_mode decl present={present}, expected {GUARD_WIRED}"
    )


def test_decision_core_header_tracked():
    """The host-proven decision-core header ships only in the FIX commit, and then
    carries the CTO-required `version` field (magic+version RTC validity guard)."""
    tracked = _is_tracked(GUARD_HEADER_REL)
    assert tracked == GUARD_WIRED, (
        f"{GUARD_HEADER_REL} tracked={tracked}, expected {GUARD_WIRED}"
    )
    if GUARD_WIRED:
        hdr = _read(REPO / GUARD_HEADER_REL)
        assert "uint32_t version" in hdr, "FIX: header must carry the version field (CTO)"
        assert "k1_bootloop_eval" in hdr, "FIX: header must define the decision core"
