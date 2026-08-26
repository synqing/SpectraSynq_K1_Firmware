"""Static ratchets for the K1_RENDER_TRACE_V1 LED-level capture instrument.

Clones of the scap ratchet pair — each pins a trap class that already bit a
session:

- TU gate-first (S1 lesson): a global-ctor leak from an ungated include breaks
  production byte-identity.
- .def row without a parse_command ladder hop compiles clean and answers
  `Bad command` live (caught 2026-08-12).
- The diag flag must not leak into shippable envs.
- Lever-2 occupancy cannot be proven from RGB8 leds_out (Captain 2026-08-22).
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
SHIPPABLE = {
    "k1_hardware",
    "k1_prod_im73d",
    "k1_bench_reference",
    "k1_main_rpl_im69d",
}
RTRACE_DIAG_ENVS = {
    "env:k1_bench_im69d_hueaud]",
    "env:k1_main_rpl_rtrace_probe]",
    "env:k1_bench_im69d_led150_rtrace]",
}


def _flag_carriers(ini: str, flag: str):
    sections = re.split(r"^\[", ini, flags=re.M)
    return [
        s.splitlines()[0]
        for s in sections
        if re.search(rf"^\s*-D{flag}\s*$", s, re.M)
    ]


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
    outside = table.replace(block, "")
    assert "rtrace_" not in outside, "rtrace rows leaked outside the flag gate"


def test_rtrace_flag_only_on_diag_envs():
    """K1_RENDER_TRACE_V1 is hueaud (RGB8), the RPL Lever-2 probe, and the
    led150 WS2812 probe. K1_HUE_AUDIT_V1 stays hueaud-only. None reach a
    shippable env."""
    ini = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    rtrace = set(_flag_carriers(ini, "K1_RENDER_TRACE_V1"))
    assert rtrace == RTRACE_DIAG_ENVS, f"K1_RENDER_TRACE_V1 carriers: {rtrace}"
    hue = set(_flag_carriers(ini, "K1_HUE_AUDIT_V1"))
    assert hue == {"env:k1_bench_im69d_hueaud]"}, f"K1_HUE_AUDIT_V1 carriers: {hue}"
    for env in SHIPPABLE:
        block_m = re.search(
            rf"\[env:{re.escape(env)}\](.*?)(?=\n\[env:|\Z)",
            ini,
            flags=re.S,
        )
        assert block_m, f"missing [env:{env}]"
        assert "-DK1_RENDER_TRACE_V1" not in block_m.group(1), (
            f"{env} must not compile K1_RENDER_TRACE_V1"
        )


def test_rtrace_rgb8_hook_still_sits_on_leds_out():
    """WS2812 path still captures leds_out (hueaud)."""
    led = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
    blocks = re.findall(r"#ifdef\s+K1_RENDER_TRACE_V1\s*\n(.*?)#endif", led, re.S)
    assert blocks, "led_utilities.h must carry a K1_RENDER_TRACE_V1-gated hook"
    assert any("k1_render_trace_on_frame((const uint8_t*)leds_out" in b
               for b in blocks), (
        "the WS2812 hook must still capture leds_out"
    )


def test_rtrace_lever2_hook_sits_before_early_return():
    """Occupancy tap is packed WS2816 wire, before the Lever-2 return.
    leds_out is never filled on that path — capturing it cannot close KEEP/KILL.
    """
    led = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
    pack = led.find("k1_lever2_pack_frame")
    assert pack > 0, "missing k1_lever2_pack_frame"
    hook = led.find("k1_render_trace_on_frame16", pack)
    ret = led.find("    return;", pack)
    assert pack < hook < ret, (
        "k1_render_trace_on_frame16 must sit after pack_frame and before "
        f"the Lever-2 return (pack={pack} hook={hook} return={ret})"
    )
    assert "ws2816_wire" in led[hook:hook + 200]


def test_rtrace_on_frame16_is_declared_and_gated():
    header = (FW / "visual" / "k1_render_trace.h").read_text(encoding="utf-8")
    cpp = (FW / "visual" / "k1_render_trace.cpp").read_text(encoding="utf-8")
    first_h = next(
        line.strip() for line in header.splitlines() if line.strip().startswith("#")
    )
    assert first_h == "#ifdef K1_RENDER_TRACE_V1"
    assert "void k1_render_trace_on_frame16(" in header
    assert "void k1_render_trace_on_frame16(" in cpp
    assert "fmt=rgb16hex" in cpp or '"rgb16hex"' in cpp


def test_rtrace_stim_paints_before_pack():
    led = (FW / "visual" / "led_utilities.h").read_text(encoding="utf-8")
    stim = led.find("k1_render_trace_stim_active")
    pack = led.find("k1_lever2_pack_frame")
    assert 0 < stim < pack, "stim ramp must overwrite leds_scaled before pack"
    header = (FW / "visual" / "k1_render_trace.h").read_text(encoding="utf-8")
    assert "k1_render_trace_stim_active" in header
    cpp = (FW / "visual" / "k1_render_trace.cpp").read_text(encoding="utf-8")
    assert "stim" in cpp and "s_stim" in cpp


def test_rtrace_probe_env_is_non_shippable_and_allowlisted():
    ini = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    wrapper = (ROOT / "scripts" / "agent" / "pio-build.sh").read_text(encoding="utf-8")
    identities = (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
        encoding="utf-8"
    )
    m = re.search(
        r"\[env:k1_main_rpl_rtrace_probe\](.*?)(?=\n\[env:|\Z)",
        ini,
        flags=re.S,
    )
    assert m, "missing [env:k1_main_rpl_rtrace_probe]"
    block = m.group(0)
    assert "NON-SHIPPABLE" in block
    assert "extends = env:k1_main_rpl_im69d" in block
    assert "-DK1_RENDER_TRACE_V1" in block
    assert "k1_main_rpl_rtrace_probe" in wrapper
    assert "k1_main_rpl_rtrace_probe" in identities


def test_led150_rtrace_probe_env_is_non_shippable_and_allowlisted():
    ini = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    wrapper = (ROOT / "scripts" / "agent" / "pio-build.sh").read_text(encoding="utf-8")
    m = re.search(
        r"\[env:k1_bench_im69d_led150_rtrace\](.*?)(?=\n\[env:|\Z)",
        ini,
        flags=re.S,
    )
    assert m, "missing [env:k1_bench_im69d_led150_rtrace]"
    block = m.group(0)
    assert "NON-SHIPPABLE" in block
    assert "extends = env:k1_bench_im69d_led150" in block
    assert "-DK1_RENDER_TRACE_V1" in block
    assert "k1_bench_im69d_led150_rtrace" in wrapper
