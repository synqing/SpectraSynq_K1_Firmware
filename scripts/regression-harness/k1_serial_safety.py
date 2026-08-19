#!/usr/bin/env python3
"""Machine-checkable safety classification for the K1 serial command surface.

WHY THIS EXISTS
---------------
2026-08-11: an agent sent ``:led_count`` to bench K1v2 (chip ``B489A500``)
intending a *read*.  ``led_count`` is a SETTER.  With no ``=value`` the legacy
metadata parser in ``serial_menu.cpp`` yields ``command_data == ""``, and
``serial_cmd_handlers.cpp`` does::

    CONFIG.LED_COUNT = constrain(atol(command_data), 1, 10000);  // atol("") -> 0 -> 1
    save_config();
    reboot();

The device replied ``CONFIG.LED_COUNT: 1`` and rebooted.  Nothing in the tooling
stopped it, because nothing in the tooling knew which command names are setters.
This module is that knowledge, generated from the firmware's own dispatch tables.

SOURCE OF TRUTH
---------------
Two X-macro tables, BOTH parsed (a guard that covers one table has a hole — the
incident command lives in the typed table, while ``dump`` / ``start_noise_cal`` /
``factory_reset`` live in the bare table):

  SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def
      git blob e83abf9eee23099a2b9b0a034d355350bf8aa9ce   (154 rows)
  SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def
      git blob 9246b0702f40f796eb0877bda2f8b8c1515ec009   (36 rows)

Verify with ``git hash-object <path>``.  ``tests/test_k1_serial_safety.py``
re-parses both files and fails if the literals below have drifted, so an edit to
a ``.def`` without regenerating this module is caught by the host gate.

Rows inside ``#if`` blocks are included unconditionally.  That is deliberate and
conservative: a command that is compiled out simply does not exist on the device
(the firmware answers ``bad_command``), whereas omitting it here could let a
dangerous name be classified as absent-and-therefore-fine.

READ THIS BEFORE TRUSTING ``SAFE_READONLY_COMMANDS``
----------------------------------------------------
"Flag-clean" is NOT the same as "read-only".  Many rows carry no flags yet still
mutate volatile runtime state (``set_mode``, ``debug``, the ``vp_*`` / ``edge_*``
/ ``smart_*`` tuning families) or drive the LEDs (``vp_out_test``, ``mp_flash``,
``vpml``).  ``SAFE_READONLY_COMMANDS`` means *"cannot persist to flash, cannot
reboot, cannot wipe calibration, does not assume silence"* — it does NOT promise
the device is unchanged.  ``FLAG_CLEAN_COMMANDS`` is the raw predicate the flags
alone support; ``SAFE_READONLY_COMMANDS`` additionally removes
``CMD_IRREVERSIBLE`` and ``CMD_NEEDS_SILENCE`` rows, because
``clear_noise_cal`` (wipes calibration) and ``start_noise_cal`` (Captain-gated
silence window, ``.claude/CLAUDE.md``) are flag-clean under the naive
disruptive/persists-only predicate and must never be reachable through a set
called "safe".

Genuinely read-only witnesses for device state: ``dump``, ``chip_id``,
``version``, ``build``, ``runtime_id``, ``image_id``, ``reset_reason``,
``fps``, ``led_fps``, ``get_mode``, ``get_num_modes``, ``slot_list``,
``vp_status``, ``smart_status``, ``edge_status``, ``event_status``.
``dump`` prints ``CONFIG.LED_COUNT`` (``serial_menu.cpp`` ``dump_info()``), which
is the correct way to read an LED count.
"""

from __future__ import annotations

__all__ = [
    "SAFE_READONLY_COMMANDS",
    "FLAG_CLEAN_COMMANDS",
    "DISRUPTIVE_COMMANDS",
    "PERSISTING_COMMANDS",
    "IRREVERSIBLE_COMMANDS",
    "SILENCE_GATED_COMMANDS",
    "ROW1_BARE_COMMANDS",
    "ALL_COMMANDS",
    "TYPED_DEF_BLOB_SHA",
    "BARE_DEF_BLOB_SHA",
    "assert_read_only",
    "assert_safe_to_send",
]

TYPED_DEF_PATH = "SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_cmd_table.def"
BARE_DEF_PATH = "SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def"
TYPED_DEF_BLOB_SHA = "49c31b7e648957cd089e8f006374cd704efa2df5"
BARE_DEF_BLOB_SHA = "7d13ad05eed1af875563d9d46a5e8515ebe3aac5"

# --------------------------------------------------------------------------
# Literals generated from the two .def files (see module docstring).
# --------------------------------------------------------------------------

#: Rows whose flags contain CMD_DISRUPTIVE — these reboot the device.
DISRUPTIVE_COMMANDS = frozenset({
    "bass_mode",
    "boot_animation",
    "bootloop_inject",
    "factory_reset",
    "led_color_order",
    "led_count",
    "led_type",
    "note_offset",
    "reset",
    "restore_defaults",
    "sample_rate",
    "samples_per_chunk",
    "set_chroma_profile",
})

#: Rows whose flags contain CMD_PERSISTS — these write flash (save_config /
#: show-state / preset slots) and survive a power cycle.
PERSISTING_COMMANDS = frozenset({
    "auto_color_shift",
    "base_coat",
    "bass_mode",
    "boot_animation",
    "bulb_opacity",
    "chroma",
    "chromagram_range",
    "commit_quantise",
    "incandescent_filter",
    "incandescent_mode",
    "k1_loud_guard",
    "led_color_order",
    "led_count",
    "led_interpolation",
    "led_type",
    "max_current_ma",
    "mirror_enabled",
    "mood",
    "note_offset",
    "palette_index",
    "palette_mode",
    "photons",
    "preset",
    "prism_count",
    "queue_mode",
    "response_gain",
    "reverse_order",
    "sample_rate",
    "samples_per_chunk",
    "saturation",
    "save_show",
    "secondary_auto_color_shift",
    "secondary_base_coat",
    "secondary_chroma",
    "secondary_control",
    "secondary_enabled",
    "secondary_incandescent_mode",
    "secondary_mirror_enabled",
    "secondary_mood",
    "secondary_palette_index",
    "secondary_palette_mode",
    "secondary_photons",
    "secondary_prism_count",
    "secondary_reverse_order",
    "secondary_saturation",
    "sensitivity",
    "set_chroma_profile",
    "silence_dwell",
    "silence_enter",
    "silence_exit",
    "silence_rms_enter",
    "silence_rms_exit",
    "slot_arm",
    "slot_load",
    "slot_save",
    "square_iter",
    "sweet_spot_max",
    "sweet_spot_min",
    "temporal_dithering",
    "transition_dip_ms",
    "transition_style",
    "transition_xfade_ms",
    "vp_all",
    "vp_profile",
})

#: Rows whose flags contain CMD_IRREVERSIBLE — destroy state that cannot be
#: recovered by re-sending a value.
IRREVERSIBLE_COMMANDS = frozenset({
    "clear_noise_cal",
    "factory_reset",
    "restore_defaults",
})

#: Rows whose flags contain CMD_NEEDS_SILENCE. Captain-verbal-gated, always —
#: see the calibration command policy in .claude/CLAUDE.md. Never agent-fired.
SILENCE_GATED_COMMANDS = frozenset({
    "start_noise_cal",
})

#: Every row in serial_cmd_table.def (the "Row 1" bare table). A name in this
#: set is a real bare command: sending ``:<name>`` with no value dispatches the
#: table row. A name NOT in this set falls through to the legacy metadata parser
#: and is handled as ``type=value`` with an EMPTY value — see VALUELESS_SETTER
#: below.
ROW1_BARE_COMMANDS = frozenset({
    "H",
    "SB?",
    "V",
    "bootloop_inject",
    "build",
    "chip_id",
    "clear_noise_cal",
    "commit",
    "dial_status",
    "dump",
    "edge_status",
    "event_status",
    "factory_reset",
    "fps",
    "get_buttons",
    "get_knobs",
    "get_mode",
    "get_num_modes",
    "h",
    "help",
    "identify",
    "image_id",
    "led_fps",
    "reset",
    "reset_reason",
    "restore_defaults",
    "runtime_id",
    "save_show",
    "slot_list",
    "smart_status",
    "start_noise_cal",
    "stop",
    "trace",
    "v",
    "version",
    "vp_out_test",
    "vp_status",
})

#: Rows carrying NEITHER CMD_DISRUPTIVE NOR CMD_PERSISTS. This is the raw
#: predicate the flags support — it still contains clear_noise_cal and
#: start_noise_cal. Prefer SAFE_READONLY_COMMANDS.
FLAG_CLEAN_COMMANDS = frozenset({
    "H",
    "SB?",
    "V",
    "ap_capture",
    "ap_frontend_debug",
    "ap_stream",
    "apcad_abort",
    "apcad_capture",
    "apcad_clear",
    "apcad_dump",
    "apcad_soak",
    "apcad_soak_status",
    "apcad_status",
    "apdbg",
    "beat_director",
    "ble_stream",
    "build",
    "chip_id",
    "chromatic",
    "clear_noise_cal",
    "commit",
    "debug",
    "diag",
    "dial_status",
    "dump",
    "dump_raw",
    "edge_bench",
    "edge_dual",
    "edge_enabled",
    "edge_mode",
    "edge_rotation",
    "edge_spread",
    "edge_status",
    "edge_stm",
    "edge_strength",
    "edge_uniform",
    "edge_xform",
    "event_status",
    "fps",
    "frame_dump",
    "gdft_agc_probe",
    "gdft_probe",
    "gdft_sweep",
    "get_buttons",
    "get_knobs",
    "get_mode",
    "get_mode_name",
    "get_num_modes",
    "h",
    "help",
    "identify",
    "image_id",
    "k1_pin_evidence",
    "led_fps",
    "mp_flash",
    "mp_off",
    "mp_status",
    "mic_health",
    "mic_health_fault",
    "mp_step",
    "nov_capture",
    "nov_clear",
    "nov_dump",
    "nov_status",
    "reset_reason",
    "rtrace_arm",
    "rtrace_dump",
    "rtrace_status",
    "runtime_id",
    "scheduling_trace",
    "secondary_mode",
    "secondary_status",
    "set_mode",
    "show_state",
    "show_skip",
    "scap_arm",
    "scap_dump",
    "scap_status",
    "slot_list",
    "smart_assist",
    "smart_confidence_floor",
    "smart_hooks",
    "smart_scene",
    "smart_status",
    "smart_switching",
    "start_benchmark",
    "start_noise_cal",
    "stop",
    "stream",
    "stream_agc",
    "stream_chromagram",
    "stream_spectrogram",
    "tempo_stream",
    "trace",
    "twitch",
    "v",
    "version",
    "vivid",
    "vivid_black",
    "vivid_chroma",
    "vivid_level",
    "vp_agc_soft",
    "vp_bloom_alpha",
    "vp_bloom_decay",
    "vp_bloom_force_sat",
    "vp_bloom_shift",
    "vp_chroma_gate",
    "vp_fix1",
    "vp_fix2",
    "vp_fix3",
    "vp_fix4",
    "vp_fix5",
    "vp_hsv_source_sat",
    "vp_out_test",
    "vp_perf",
    "vp_prism_off",
    "vp_probe",
    "vp_secondary_clean",
    "vp_status",
    "vp_stream",
    "vp_wave_active_fade",
    "vp_wave_blend_gain",
    "vp_wave_fallback",
    "vp_wave_idle_fade",
    "vp_wave_peak_floor",
    "vp_wave_raw_margin",
    "vp_wave_shift",
    "vp_wave_vu_floor",
    "vpab",
    "vpml",
})

#: Every command name known to either table.
ALL_COMMANDS = FLAG_CLEAN_COMMANDS | DISRUPTIVE_COMMANDS | PERSISTING_COMMANDS

#: The set an operator may send without risking flash, a reboot, a calibration
#: wipe, or a silence-gate violation. See the docstring caveat: this is not a
#: promise that device runtime state is unchanged.
SAFE_READONLY_COMMANDS = (
    FLAG_CLEAN_COMMANDS - IRREVERSIBLE_COMMANDS - SILENCE_GATED_COMMANDS
)

#: Flag names, in the order assert_read_only reports them.
_FLAG_SETS = (
    ("CMD_DISRUPTIVE", DISRUPTIVE_COMMANDS),
    ("CMD_PERSISTS", PERSISTING_COMMANDS),
    ("CMD_IRREVERSIBLE", IRREVERSIBLE_COMMANDS),
    ("CMD_NEEDS_SILENCE", SILENCE_GATED_COMMANDS),
)


def assert_read_only(name: str) -> None:
    """Raise RuntimeError unless ``name`` is in SAFE_READONLY_COMMANDS.

    The message names the offending flag(s) so the caller learns *why*, not just
    that it was refused. Unknown names are refused too — an unrecognised token
    reaches the legacy metadata parser, which is where the led_count incident
    happened.
    """
    if name in SAFE_READONLY_COMMANDS:
        return
    offenders = [flag for flag, members in _FLAG_SETS if name in members]
    if offenders:
        raise RuntimeError(
            f"{name!r} is NOT read-only: carries {' | '.join(offenders)} "
            f"(source: {TYPED_DEF_PATH} / {BARE_DEF_PATH}). "
            "Read device state with ':dump' instead."
        )
    raise RuntimeError(
        f"{name!r} is not a known K1 serial command. Unknown tokens fall through "
        "to the legacy 'type=value' parser and may be dispatched as a setter with "
        "an empty value. Refusing to send."
    )


def assert_safe_to_send(line: str) -> None:
    """Raise RuntimeError unless the raw serial line is safe to transmit.

    Encodes the two mechanics that made the 2026-08-11 incident possible:

    1. **The valueless-setter trap.** ``:led_count`` (no ``=``) is not a read.
       Any name absent from ``ROW1_BARE_COMMANDS`` falls through to the metadata
       parser in ``serial_menu.cpp``, arrives at its handler with
       ``command_data == ""``, and setters then apply ``atol("") == 0``.
       For ``led_count`` that is ``constrain(0, 1, 10000) == 1``, saved and
       rebooted.
    2. **Bare bytes are hotkeys.** A line with no ``':'`` prefix is sprayed at
       the single-byte hotkey surface, one keystroke per character.

    Accepts the leading ``':'`` with or without a trailing newline.
    """
    raw = line.strip()
    if not raw:
        raise RuntimeError("refusing to send an empty line")
    if not raw.startswith(":"):
        raise RuntimeError(
            f"{raw!r} has no ':' prefix — bare bytes are dispatched as single-byte "
            "hotkeys, one per character. Prefix with ':'."
        )
    body = raw[1:]
    name, sep, _value = body.partition("=")
    name = name.strip()
    if sep:
        assert_read_only(name)  # a value means an explicit write; caller opted in
        return
    if name in ROW1_BARE_COMMANDS:
        assert_read_only(name)
        return
    raise RuntimeError(
        f"{name!r} is not a bare (Row 1) command, so ':{name}' with no '=value' "
        "falls through to the legacy metadata parser and is dispatched as a "
        "SETTER with an empty value (atol(\"\") == 0). This is exactly the "
        "led_count incident. Send ':dump' to read state."
    )


def _main() -> None:
    for label, members in (
        ("SAFE_READONLY_COMMANDS", SAFE_READONLY_COMMANDS),
        ("DISRUPTIVE_COMMANDS", DISRUPTIVE_COMMANDS),
        ("PERSISTING_COMMANDS", PERSISTING_COMMANDS),
        ("IRREVERSIBLE_COMMANDS", IRREVERSIBLE_COMMANDS),
        ("SILENCE_GATED_COMMANDS", SILENCE_GATED_COMMANDS),
    ):
        print(f"{label} ({len(members)}):")
        for name in sorted(members):
            print(f"  {name}")
        print()
    print(f"ALL_COMMANDS: {len(ALL_COMMANDS)}")
    print(f"typed .def blob: {TYPED_DEF_BLOB_SHA}")
    print(f"bare  .def blob: {BARE_DEF_BLOB_SHA}")


if __name__ == "__main__":
    _main()
