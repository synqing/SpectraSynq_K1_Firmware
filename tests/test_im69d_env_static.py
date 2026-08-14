"""Static locks for the non-shippable k1_bench_im69d env (2026-08-05).

Locks the Captain-approved pin/flag/cal-namespace contract so the IM69 lane
cannot silently reuse IM73D macros or poison /cal_profile_pdm.bin.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = ROOT / "platformio.ini"
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
I2S = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h"
BRIDGE_FS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "persistence" / "bridge_fs.h"
GUARD = ROOT / "scripts" / "platformio" / "k1_upload_guard.py"
PIO_BUILD = ROOT / "scripts" / "agent" / "pio-build.sh"

PROD_ENVS = (
    "k1_hardware",
    "k1_bench_reference",
    "k1_bench_im73d",
    "k1_prod_im73d",
)


def _env_block(text: str, env_name: str) -> str:
    pattern = rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)"
    match = re.search(pattern, text, flags=re.S)
    assert match, f"missing [env:{env_name}] in platformio.ini"
    return match.group(1)


def _env_sections(text: str) -> dict[str, str]:
    return {
        match.group(1): match.group(2)
        for match in re.finditer(
            r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", text, flags=re.M | re.S
        )
    }


def _option_defines(block: str, option: str) -> set[str]:
    match = re.search(
        rf"^{re.escape(option)}\s*=\s*(.*(?:\n[ \t]+.*)*)",
        block,
        flags=re.M,
    )
    if not match:
        return set()
    uncommented = "\n".join(
        line for line in match.group(1).splitlines()
        if not line.lstrip().startswith(("#", ";"))
    )
    return set(re.findall(r"-D([A-Za-z0-9_]+)", uncommented))


def _effective_defines(
    env_name: str, sections: dict[str, str], seen: set[str] | None = None
) -> set[str]:
    seen = set() if seen is None else seen
    assert env_name in sections, f"missing [env:{env_name}]"
    assert env_name not in seen, f"extends cycle at [env:{env_name}]"
    seen.add(env_name)
    block = sections[env_name]
    flags: set[str] = set()
    extends = re.search(r"^extends\s*=\s*env:(\S+)", block, flags=re.M)
    if extends:
        flags = _effective_defines(extends.group(1), sections, seen)
    flags |= _option_defines(block, "build_flags")
    flags -= _option_defines(block, "build_unflags")
    return flags


def _validate_im69d_slot_contract(text: str) -> None:
    """Every active IM69D env must resolve to the ratified mono source or stereo."""
    sections = _env_sections(text)
    retired = {
        "k1_bench_im69d_micb",
        "k1_bench_im69d_hpf_slotr",
        "k1_bench_im69d_calfix_dsr16",
    }
    assert retired.isdisjoint(sections), (
        "retired IM69D aliases/no-op probes must not return as active envs"
    )

    checked = 0
    for env_name in sections:
        flags = _effective_defines(env_name, sections)
        if "K1_MIC_IM69D_PDM_V1" not in flags:
            continue
        checked += 1
        mono_slots = flags & {
            "K1_MIC_IM69D_SLOT_LEFT",
            "K1_MIC_IM69D_SLOT_RIGHT",
        }
        if "K1_MIC_IM69D_STEREO_V1" in flags:
            assert not mono_slots, (
                f"{env_name}: stereo must unflag every inherited mono slot"
            )
        else:
            assert mono_slots == {"K1_MIC_IM69D_SLOT_RIGHT"}, (
                f"{env_name}: mono IM69D must resolve only to G1-ratified "
                "physical IM1 / ESP-IDF RIGHT"
            )
    assert checked > 0, "ratchet found no IM69D environments"


def test_im69d_env_exists_and_extends_bench_reference():
    text = PLATFORMIO.read_text(encoding="utf-8")
    block = _env_block(text, "k1_bench_im69d")
    assert "extends = env:k1_bench_reference" in block
    assert "-DK1_MIC_IM69D_PDM_V1" in block
    assert "-DK1_MIC_IM69D_DSR_16S_V1" in block
    assert "K1_MIC_IM73D_PDM_V1" not in block


def test_im69d_ble_env_extends_im69d_and_uses_only_ble_deltas():
    text = PLATFORMIO.read_text(encoding="utf-8")
    block = _env_block(text, "k1_bench_im69d_ble")
    assert "extends = env:k1_bench_im69d" in block
    assert "+<network/ble_remoted_central.cpp>" in block
    assert "+<network/k1_ble_midi_decoder.cpp>" in block
    assert "-DK1_BLE_REMOTED" in block
    assert "-DK1_MIC_IM73D_PDM_V1" not in block
    assert "NimBLE-Arduino@^2.5.0" in block


def test_im69d_flag_absent_from_production_and_im73d_envs():
    text = PLATFORMIO.read_text(encoding="utf-8")
    for env_name in PROD_ENVS:
        block = _env_block(text, env_name)
        # Comments between env stanzas may mention the flag; lock the build_flags.
        assert "-DK1_MIC_IM69D_PDM_V1" not in block, (
            f"{env_name} must not define -DK1_MIC_IM69D_PDM_V1"
        )


def test_im69d_pins_are_clk14_din13_no_lr_drive():
    constants = CONSTANTS.read_text(encoding="utf-8")
    i2s = I2S.read_text(encoding="utf-8")

    assert "#define K1_PDM_CLK_PIN 14" in constants
    assert "#define K1_PDM_DIN_PIN 13" in constants
    # Bench-reference IM69 block must not introduce an LR drive pin.
    assert "K1_IM69_PDM_SEL_PIN 12" in constants
    # Under IM69 ifdef near the pin defines, K1_PDM_LR_PIN must be absent.
    pin_region = constants[
        constants.index("IM69D130 dual-mic PCB3") : constants.index(
            "K1_IM69_PDM_SEL_PIN 12"
        )
        + 40
    ]
    assert "K1_PDM_LR_PIN" not in pin_region

    im69_init = re.search(
        r"#elif defined\(K1_MIC_IM69D_PDM_V1\)(.*?)#else",
        i2s,
        flags=re.S,
    )
    assert im69_init, "missing IM69 init_i2s elif branch"
    init_text = im69_init.group(1)
    assert "gpio_set_level" not in init_text
    assert "K1_PDM_LR_PIN" not in init_text
    assert "I2S_PDM_DSR_16S" in init_text


def test_im69d_cal_namespace_distinct_from_im73d():
    bridge = BRIDGE_FS.read_text(encoding="utf-8")
    assert '"/cal_profile_im69d.bin"' in bridge
    assert '"/cal_profile_pdm.bin"' in bridge
    assert "CONFIG_IM69_" in bridge
    constants = CONSTANTS.read_text(encoding="utf-8")
    assert "mutually exclusive" in constants


def test_im69d_registered_in_upload_guard_and_pio_build_allowlist():
    import json

    manifest = json.loads(
        (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
            encoding="utf-8"
        )
    )
    wrapper = PIO_BUILD.read_text(encoding="utf-8")
    bench_envs = next(
        e["envs"] for e in manifest["authorized"] if e["chip_id"] == "B489A500"
    )
    main_envs = next(
        e["envs"] for e in manifest["authorized"] if e["chip_id"] == "F887A500"
    )
    assert "k1_bench_im69d" in bench_envs
    assert "k1_bench_im69d_ble" in bench_envs
    assert "k1_bench_im69d" not in main_envs
    assert "k1_bench_im69d_ble" not in main_envs
    assert "k1_bench_im69d" in wrapper
    assert "k1_bench_im69d_ble" in wrapper


def test_every_active_im69d_env_has_an_identity_registry_disposition():
    import json

    text = PLATFORMIO.read_text(encoding="utf-8")
    sections = _env_sections(text)
    manifest = json.loads(
        (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
            encoding="utf-8"
        )
    )
    authorised = {
        env_name
        for device in manifest["authorized"]
        for env_name in device["envs"]
    }
    blocked = set(manifest["blocked_envs"])
    active_im69d = {
        env_name for env_name in sections
        if "K1_MIC_IM69D_PDM_V1" in _effective_defines(env_name, sections)
    }
    assert active_im69d <= authorised | blocked
    assert {
        "k1_bench_im69d_micb",
        "k1_bench_im69d_hpf_slotr",
        "k1_bench_im69d_calfix_dsr16",
    }.isdisjoint(authorised | blocked)


def test_im69d_not_alias_of_im73d_flag():
    """IM69 must never #define or silently enable K1_MIC_IM73D_PDM_V1."""
    constants = CONSTANTS.read_text(encoding="utf-8")
    i2s = I2S.read_text(encoding="utf-8")
    # No aliasing define.
    assert not re.search(
        r"#\s*define\s+K1_MIC_IM73D_PDM_V1",
        constants + i2s,
    )
    # Env must not set the IM73D flag.
    block = _env_block(PLATFORMIO.read_text(encoding="utf-8"), "k1_bench_im69d")
    assert "-DK1_MIC_IM73D_PDM_V1" not in block


def test_joint_silence_gate_is_scoped_to_im69d():
    """The joint break-path must not compile into non-IM69D builds.

    Both its constants (K1_SILENCE_PEAKINESS_BREAK, K1_SILENCE_JOINT_LEVEL_SSL_FRAC)
    were measured on IM69D130 silicon. Until 2026-08-12 the decision that consumes
    them sat behind NO #ifdef and compiled into every environment including
    k1_hardware, the SPH0645 production K1 — the same escape-the-measurement-context
    defect GATE 0.1 (1bdf54d0) was created to stop. SPH0645's RMS Schmitt is
    separately calibrated on the HarmonixSet corpus and must keep its own behaviour.
    """
    i2s = I2S.read_text(encoding="utf-8")
    m = re.search(
        r"#if\s+defined\(K1_MIC_IM69D_PDM_V1\)(.*?)#endif",
        i2s,
        re.DOTALL,
    )
    assert m, (
        "The joint silence break-path must be wrapped in "
        "`#if defined(K1_MIC_IM69D_PDM_V1)` in i2s_audio.h."
    )
    block = m.group(1)
    assert "K1_SILENCE_JOINT_LEVEL_SSL_FRAC" in block, (
        "K1_SILENCE_JOINT_LEVEL_SSL_FRAC is consumed OUTSIDE the IM69D guard — it "
        "would apply IM69D-measured values to SPH0645 production."
    )
    assert "K1_SILENCE_PEAKINESS_BREAK" in block, (
        "K1_SILENCE_PEAKINESS_BREAK is consumed OUTSIDE the IM69D guard."
    )
    # The plain RMS Schmitt must remain reachable for non-IM69D builds.
    assert "K1_SILENCE_RMS_EXIT" in i2s and "K1_SILENCE_RMS_ENTER" in i2s


# ── Stage 1b / Stage 2 locks (2026-08-12, runbook P3.B/P3.C) ─────────────────

def test_all_im69d_envs_resolve_to_the_g1_slot_contract():
    text = PLATFORMIO.read_text(encoding="utf-8")
    _validate_im69d_slot_contract(text)


def test_im69d_slot_ratchet_observably_rejects_the_historical_default():
    """Mutation proof: removing the base RIGHT flag must make the ratchet go RED."""
    text = PLATFORMIO.read_text(encoding="utf-8")
    broken = text.replace("    -DK1_MIC_IM69D_SLOT_RIGHT\n", "", 1)
    assert broken != text, "mutation failed to remove the base RIGHT flag"
    with pytest.raises(AssertionError, match="mono IM69D must resolve only"):
        _validate_im69d_slot_contract(broken)


def test_stereo_env_sets_stereo_flag_and_no_mono_slot():
    """Stereo explicitly removes inherited RIGHT before selecting both slots."""
    text = PLATFORMIO.read_text(encoding="utf-8")
    block = _env_block(text, "k1_bench_im69d_stereo")
    assert "extends = env:k1_bench_im69d" in block
    assert "-DK1_MIC_IM69D_STEREO_V1" in block
    assert "build_unflags" in block
    assert "-DK1_MIC_IM69D_SLOT_RIGHT" in block
    assert "-DK1_MIC_IM69D_SLOT_LEFT" not in block
    flags = _effective_defines("k1_bench_im69d_stereo", _env_sections(text))
    assert "K1_MIC_IM69D_STEREO_V1" in flags
    assert "K1_MIC_IM69D_SLOT_RIGHT" not in flags
    assert "K1_MIC_IM69D_SLOT_LEFT" not in flags


def test_stereo_flag_absent_from_production_and_all_other_envs():
    """K1_MIC_IM69D_STEREO_V1 may appear in exactly one env: the stereo probe."""
    text = PLATFORMIO.read_text(encoding="utf-8")
    sections = _env_sections(text)
    stereo_envs = {
        env_name for env_name in sections
        if "K1_MIC_IM69D_STEREO_V1" in _effective_defines(env_name, sections)
    }
    assert stereo_envs == {"k1_bench_im69d_stereo"}


def test_stereo_init_mutually_excludes_mono_slot_selects():
    """i2s_audio.h must #error when stereo is combined with a mono slot flag."""
    text = I2S.read_text(encoding="utf-8")
    assert re.search(
        r"#if\s+defined\(K1_MIC_IM69D_STEREO_V1\)\s*&&\s*\(defined\(K1_MIC_IM69D_SLOT_LEFT\)\s*\|\|\s*defined\(K1_MIC_IM69D_SLOT_RIGHT\)\)",
        text,
    ), "stereo × mono-slot mutual exclusion #error missing from i2s_audio.h"
    assert "I2S_SLOT_MODE_STEREO)" in text
    assert "I2S_PDM_SLOT_BOTH" in text


def test_g1_driver_clock_and_buffer_order_are_frozen_in_source():
    """G1 relies on exact active-driver identity, electrical names and DMA order."""
    pio = PLATFORMIO.read_text(encoding="utf-8")
    i2s = I2S.read_text(encoding="utf-8")
    globals_h = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" /
                 "globals.h").read_text(encoding="utf-8")
    probe = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" /
             "k1_stereo_probe.cpp").read_text(encoding="utf-8")
    decoder = (ROOT / "scripts" / "regression-harness" /
               "stereo_probe_decode.py").read_text(encoding="utf-8")

    assert "54.03.20/platform-espressif32.zip" in pio
    assert "ESP_IDF_VERSION != ESP_IDF_VERSION_VAL(5, 4, 1)" in i2s
    assert "#include <driver/i2s_pdm.h>" in i2s
    assert "i2s_channel_init_pdm_rx_mode" in i2s
    assert "static_assert((int)I2S_PDM_SLOT_RIGHT == 1" in i2s
    assert "static_assert((int)I2S_PDM_SLOT_LEFT == 2" in i2s
    assert "#define K1_IM69D_PDM_CLK_INV false" in i2s
    assert ".clk_inv = K1_IM69D_PDM_CLK_INV" in i2s
    assert "order=RIGHT,LEFT clk_inv=false" in i2s

    assert "im69d_samples_i16_left" in globals_h
    assert "im69d_samples_i16_right" not in globals_h
    assert "fmt=le_i16_RL" in probe
    assert '"buffer_order": ["ESP_IDF_RIGHT", "ESP_IDF_LEFT"]' in decoder
    assert "hand-occlusion" not in decoder


def test_scap_commands_are_gated_and_harness_class():
    """scap_* typed rows exist only under the stereo flag, CMD_HARNESS class."""
    table = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" /
             "serial_typed_cmd_table.def").read_text(encoding="utf-8")
    m = re.search(r"#ifdef\s+K1_MIC_IM69D_STEREO_V1(.*?)#endif", table, re.S)
    assert m, "scap_* rows must sit under #ifdef K1_MIC_IM69D_STEREO_V1"
    block = m.group(1)
    for cmd in ("scap_arm", "scap_status", "scap_dump"):
        assert f'"{cmd}"' in block, f"missing typed row for {cmd}"
        assert "CMD_HARNESS" in block
    # And never outside the gate.
    outside = table.replace(m.group(0), "")
    assert "scap_" not in outside, "scap_* leaked outside the stereo gate"


def test_stereo_probe_tu_preprocesses_to_nothing_when_flag_off():
    """The gate must sit BEFORE every #include (no global-ctor leak, lesson S1)."""
    cpp = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" /
           "k1_stereo_probe.cpp").read_text(encoding="utf-8")
    first_directive = next(
        line.strip() for line in cpp.splitlines()
        if line.strip().startswith("#")
    )
    assert first_directive == "#ifdef K1_MIC_IM69D_STEREO_V1", (
        "k1_stereo_probe.cpp must open with the flag gate before any include"
    )


def test_scap_dispatch_reaches_the_parse_command_ladder():
    """The .def table is safety METADATA; live type=value dispatch is the
    strcmp ladder in serial_menu.cpp. A row without a ladder call-site compiles
    clean and answers `Bad command` on device (caught live 2026-08-12 — this
    ratchet pins the fix)."""
    menu = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" /
            "serial_menu.cpp").read_text(encoding="utf-8")
    m = re.search(
        r"#ifdef\s+K1_MIC_IM69D_STEREO_V1\s*\n(.*?)#endif",
        menu[menu.find("parse_command"):],
        re.S,
    )
    assert m, "parse_command must carry a K1_MIC_IM69D_STEREO_V1-gated hop"
    assert "k1_stereo_probe_dispatch(command_type, command_data)" in m.group(1), (
        "the gated hop must call k1_stereo_probe_dispatch — the table row alone "
        "does not dispatch"
    )
