"""Host-only static contract test for the P0.4 sync probe firmware.

No device, no compile — a grep-level proof that the firmware TU
(network/k1_sync_link.cpp) emits EXACTLY the serial grammar the P0.3 oracle
parses, that every .ino / serial_menu wiring point is #ifdef SB_K1_SYNC_PROBE
gated (so production stays radio-clean), and that the load-bearing hard rules
hold (no cal, ISR is IRAM_ATTR + Serial-free, the one added task is on Core 1).

The parse half is the strong link: each firmware printf template is turned into
a concrete line and fed through the oracle's own parser, so firmware↔oracle
grammar drift is caught here, before P0.5 ever flashes silicon.
"""

from __future__ import annotations

import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from dual_sync_probe import logfmt  # noqa: E402

_FW = os.path.join(_ROOT, "SPECTRASYNQ_K1_FIRMWARE")
_CPP = os.path.join(_FW, "network", "k1_sync_link.cpp")
_INO = os.path.join(_FW, "SPECTRASYNQ_K1_FIRMWARE.ino")
_MENU = os.path.join(_FW, "serial", "serial_menu.h")


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _gated_by_sync_probe(text: str, needle: str) -> bool:
    """True if ``needle`` sits inside a `#ifdef SB_K1_SYNC_PROBE ... #endif`
    block — the nearest preceding conditional directive opens that gate."""
    idx = text.index(needle)
    before = text[:idx]
    # nearest preceding preprocessor conditional
    matches = list(re.finditer(r"^\s*#(ifdef|ifndef|if|endif)\b.*$", before, re.M))
    if not matches:
        return False
    last = matches[-1].group(0)
    return "#ifdef SB_K1_SYNC_PROBE" in last


# --------------------------------------------------------------------------- #
# Firmware ↔ oracle grammar contract                                          #
# --------------------------------------------------------------------------- #

# (printf-template substring that MUST be in the TU, a concrete valid line,
#  the oracle record type that line must parse to)
_GRAMMAR = [
    ("[sync_oracle] trig_out seq=%u t_us=%llu",
     "[sync_oracle] trig_out seq=7 t_us=123456", logfmt.TrigOut),
    ("[sync_oracle] trig_in seq=%u t_us=%llu",
     "[sync_oracle] trig_in seq=7 t_us=123460", logfmt.TrigIn),
    ("[k1_sync] clk est_offset_us=%lld rtt_us=%u n=%u",
     "[k1_sync] clk est_offset_us=-42 rtt_us=8000 n=16", logfmt.Clk),
    ("[k1_sync] tx seq=%u t_leader_us=%llu",
     "[k1_sync] tx seq=3 t_leader_us=999", logfmt.Tx),
    ("[k1_sync] rx seq=%u t_leader_us=%llu t_local_us=%llu",
     "[k1_sync] rx seq=3 t_leader_us=999 t_local_us=5000999", logfmt.Rx),
    ("[k1_sync] apply seq=%u t_render_us=%llu",
     "[k1_sync] apply seq=3 t_render_us=5012000", logfmt.Apply),
]


def test_firmware_emits_oracle_grammar():
    cpp = _read(_CPP)
    for template, sample, rec_type in _GRAMMAR:
        assert template in cpp, f"firmware missing printf template: {template!r}"
        parsed = logfmt.parse_line(sample)
        assert isinstance(parsed, rec_type), (
            f"oracle cannot parse firmware line for {rec_type.__name__}: {sample!r}"
        )


def test_firmware_health_line_matches_grammar():
    cpp = _read(_CPP)
    # the health printf is split across two adjacent string literals
    for part in ("[k1_sync] health fps=%.2f heap_min=%u ap_p95_us=%u dial_linked=%d",
                 "loss=%u dup=%u"):
        assert part in cpp, f"firmware missing health template part: {part!r}"
    sample = ("[k1_sync] health fps=99.50 heap_min=60000 ap_p95_us=700 "
              "dial_linked=1 loss=0 dup=0")
    assert isinstance(logfmt.parse_line(sample), logfmt.Health)


# --------------------------------------------------------------------------- #
# Compile-gating (production stays radio-clean)                               #
# --------------------------------------------------------------------------- #


def test_tu_fully_gated():
    cpp = _read(_CPP)
    assert "#ifdef SB_K1_SYNC_PROBE" in cpp
    assert "#endif  // SB_K1_SYNC_PROBE" in cpp
    # the very first meaningful directive gates the whole body
    first_ifdef = cpp.index("#ifdef SB_K1_SYNC_PROBE")
    assert cpp.index("namespace k1_sync") > first_ifdef


def test_ino_wiring_is_gated():
    ino = _read(_INO)
    for needle in ('#include "network/k1_sync_link.h"',
                   "k1_sync::begin();",
                   "k1_sync::poll();"):
        assert needle in ino, f".ino missing wiring: {needle!r}"
        assert _gated_by_sync_probe(ino, needle), f".ino wiring not gated: {needle!r}"


def test_serial_menu_wiring_is_gated():
    menu = _read(_MENU)
    for needle in ('#include "k1_sync_link.h"',
                   'strcmp(command_type, "sync_fault")',
                   "k1_sync::set_fault(command_data)"):
        assert needle in menu, f"serial_menu missing wiring: {needle!r}"
        assert _gated_by_sync_probe(menu, needle), (
            f"serial_menu wiring not gated: {needle!r}"
        )


# --------------------------------------------------------------------------- #
# Load-bearing hard rules                                                      #
# --------------------------------------------------------------------------- #


def test_no_calibration_or_persistence():
    cpp = _read(_CPP)
    for forbidden in ("start_noise_cal", "save_config", "noise_cal"):
        assert forbidden not in cpp, f"sync TU must not touch {forbidden!r}"


def test_isr_is_iram_and_serial_free():
    cpp = _read(_CPP)
    m = re.search(r"void\s+IRAM_ATTR\s+trig_in_isr\s*\(\s*\)\s*\{(.*?)\n\}",
                  cpp, re.S)
    assert m, "trig_in_isr must be defined with IRAM_ATTR"
    body = m.group(1)
    assert "Serial" not in body, "ISR must not touch Serial"
    assert "malloc" not in body and "new " not in body, "ISR must not allocate"


def test_added_task_pinned_to_core1_low_prio():
    cpp = _read(_CPP)
    m = re.search(r"xTaskCreatePinnedToCore\(([^;]*)\)\s*;", cpp, re.S)
    assert m, "expected exactly one xTaskCreatePinnedToCore in the sync TU"
    args = [a.strip() for a in m.group(1).split(",")]
    # signature: fn, name, stack, param, priority, handle, coreID
    assert args[1].strip('"') == "k1_sync_scan"
    assert args[4] == "1", f"task priority must be 1, got {args[4]}"
    assert args[6] == "1", f"task must be pinned to Core 1, got {args[6]}"


def test_single_added_task_only():
    cpp = _read(_CPP)
    assert cpp.count("xTaskCreatePinnedToCore") == 1, (
        "sync TU must add exactly one FreeRTOS task (the follower scan loop)"
    )
