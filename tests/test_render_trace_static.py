"""Static ratchets for the K1_RENDER_TRACE_V1 LED-level capture instrument
(colour fix lane, 2026-08-13). Clones of the scap ratchet pair — each pins a
trap class that already bit a session:

- TU gate-first (S1 lesson): a global-ctor leak from an ungated include breaks
  production byte-identity.
- .def row without a parse_command ladder hop compiles clean and answers
  `Bad command` live (caught 2026-08-12).
- The diag flag must not leak into shippable envs.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


def test_render_trace_tu_preprocesses_to_nothing_when_flag_off():
    """The gate must sit BEFORE every #include (no global-ctor leak)."""
    cpp = (FW / "visual" / "k1_render_trace.cpp").read_text(encoding="utf-8")
    first_directive = next(
        line.strip() for line in cpp.splitlines()
        if line.strip().startswith("#")
    )
    assert first_directive == "#ifdef K1_RENDER_TRACE_V1", (
        "k1_render_trace.cpp must open with the flag gate before any include"
    )


def test_rtrace_dispatch_reaches_the_parse_command_ladder():
    """The .def table is safety METADATA; live type=value dispatch is the
    strcmp ladder in serial_menu.cpp. A row without a ladder call-site
    compiles clean and answers `Bad command` on device."""
    menu = (FW / "serial" / "serial_menu.cpp").read_text(encoding="utf-8")
    m = re.search(
        r"#ifdef\s+K1_RENDER_TRACE_V1\s*\n(.*?)#endif",
        menu[menu.find("parse_command"):],
        re.S,
    )
    assert m, "parse_command must carry a K1_RENDER_TRACE_V1-gated hop"
    assert "k1_render_trace_dispatch(command_type, command_data)" in m.group(1), (
        "the gated hop must call k1_render_trace_dispatch — the table row alone "
        "does not dispatch"
    )


def test_rtrace_def_rows_are_gated_and_complete():
    """All three rtrace_* rows exist inside a K1_RENDER_TRACE_V1 block."""
    table = (FW / "serial" / "serial_typed_cmd_table.def").read_text(encoding="utf-8")
    m = re.search(r"#ifdef\s+K1_RENDER_TRACE_V1\s*\n(.*?)#endif", table, re.S)
    assert m, "serial_typed_cmd_table.def must carry a K1_RENDER_TRACE_V1 block"
    block = m.group(0)
    for cmd in ("rtrace_arm", "rtrace_status", "rtrace_dump"):
        assert f'SERIAL_TYPED_CMD("{cmd}"' in block, f"missing gated row for {cmd}"
    # And nowhere outside the gate.
    outside = table.replace(block, "")
    assert "rtrace_" not in outside, "rtrace rows leaked outside the flag gate"


def test_rtrace_flag_only_in_the_hueaud_env():
    """K1_RENDER_TRACE_V1 (and K1_HUE_AUDIT_V1) are diag flags for
    k1_bench_im69d_hueaud only — never a shippable env."""
    ini = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    sections = re.split(r"^\[", ini, flags=re.M)
    for flag in ("K1_RENDER_TRACE_V1", "K1_HUE_AUDIT_V1"):
        carriers = [
            s.splitlines()[0] for s in sections
            if re.search(rf"^\s*-D{flag}\s*$", s, re.M)
        ]
        assert carriers == ["env:k1_bench_im69d_hueaud]"], (
            f"{flag} must be set ONLY in k1_bench_im69d_hueaud, found in: {carriers}"
        )


def test_rtrace_capture_hook_sits_at_the_post_gamma_boundary():
    """The capture hook must read leds_out (the FINAL post-gamma buffer the
    strip receives), gated, in led_utilities.h — measuring a pre-gamma buffer
    would measure the annotation, not the property."""
    led = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
    blocks = re.findall(r"#ifdef\s+K1_RENDER_TRACE_V1\s*\n(.*?)#endif", led, re.S)
    assert blocks, "led_utilities.h must carry a K1_RENDER_TRACE_V1-gated hook"
    assert any("k1_render_trace_on_frame((const uint8_t*)leds_out" in b
               for b in blocks), (
        "the hook must capture leds_out (post-gamma output), nothing earlier"
    )
