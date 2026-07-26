#!/usr/bin/env python3
"""Golden-master oracle for the serial command -> output replay behaviour-lock.

Phase A · Lane 2 · S3.0 + S3.1 — the pure-setter + reboot-setter replay lock that
gates ALL remaining serial_menu.h handler extractions (S4+). It compiles the REAL
`parse_command()` from SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h on the host,
drives it with a fixed deterministic corpus, and captures a JSON-lines golden
record that any refactor (S4 / S4.1 handler extraction) must reproduce byte-for-byte.

COVERAGE (corpus): 23 PURE CONFIG setters (S3.0) + 7 CLEAN reboot-bearing setters
(S3.1: sample_rate, note_offset, led_type, led_count, led_color_order,
samples_per_chunk, boot_animation). The design §4 named 9 reboot-bearing setters;
set_chroma_profile + bass_mode are EXCLUDED (see "S3.1 EXCLUSIONS" below) — their
reboot is CONDITIONAL on apply_chroma_profile()'s return, which lives in the
NOT-host-compiled led_utilities.h (stubbed to a no-op), so capturing them would
freeze WRONG behaviour. They are deferred like set_mode was in S3.0.

THE CAPTURE IS A TRIPLE PER COMMAND (design §1):
  (a) emitted serial text  — every char USBSerial/Serial.print(...)'d, in order
  (b) CONFIG field deltas   — the CONFIG.<field>(s) the setter writes, post-value
  (c) side-effect flags     — save_config / save_config_delayed / reboot fired,
                              plus bad_command (the parse-failure path)
Echo text alone is not enough: a handler that echoes the right text but writes the
wrong CONFIG field, or clamps differently, or swaps save_config_delayed for
save_config, is a real regression text misses. The triple closes that gap.

WHY THIS HOST-COMPILES (design §2, confirmed by first-hand recon):
  serial_menu.h #includes the full globals.h surface, so the substrate is the
  oracle_render / oracle_gdft one (render_host_globals.cpp + globals.cpp +
  Palettes.cpp + render_params.cpp + the stubs/ dir), NOT a minimal Arduino stub.
  parse_command is one monolithic if/else-if chain of ~132 branches; even though
  the corpus only drives ~23 of them, the WHOLE function body must compile + link.
  Under the production [env:k1_hardware] define set every harness/probe/registry
  branch is #ifdef-compiled-out, so the live link surface needs only these real
  pure-logic TUs (none drag audio/I2S/FreeRTOS/RMT):
      serial/serial_tx.cpp            (tx_begin/tx_end/bad_command/stop_streams)
      serial/serial_parse_helpers.cpp (vp_parse_bool/float, serial_clamp_float)
      director/k1_smart_director.cpp  (k1_smart_director_* config getters/setters)
      director/k1_edgemixer.cpp  (k1_edgemixer_* config)
      director/k1_visual_hooks.cpp    (k1_visual_hooks_* config)
      director/k1_mode_selection.cpp  (k1_mode_selection_init)
      control/k1_effect_queue.cpp     (k1_queue_* config)
  + the host-stubbed device side-effects: save_config / save_config_delayed /
    reboot / set_preset / check_current_function (defined in the driver — serial_menu.h
    does NOT transitively include bridge_fs.h / system.h / presets.h, so there is
    NO ODR clash; the only constraint is matching the `extern void reboot();` and
    `extern void check_current_function();` decls at serial_menu.h:46-47).

CORPUS = 23 PURE SETTERS, NOT 24 (load-bearing deviation, see CORPUS below):
  The design §4 named 24 pure setters. First-hand recon found `set_mode` is NOT a
  pure synchronous CONFIG setter — it queues mode_transition_queued/mode_destination
  and the real CONFIG.LIGHTSHOW_MODE write happens LATER in led_utilities.h:1517
  inside the visual transition state machine; it echoes mode_destination (a dense
  index), and under K1_EFFECT_REGISTRY_V1 couples to the registry. A golden that
  asserted a synchronous CONFIG.LIGHTSHOW_MODE round-trip for set_mode would be
  WRONG. set_mode is therefore EXCLUDED from S3.0 and deferred to a later slice that
  models the async transition. The other two design-flagged setters are KEPT and
  captured faithfully because the triple makes them fully lockable:
    - max_current_ma calls FastLED.setMaxPowerInVoltsAndMilliamps(...) (host no-op),
      so the parse->CONFIG->save->echo round-trip is still pure and capturable.
    - prism_count calls save_config() (IMMEDIATE), not save_config_delayed(); the
      triple's separate flags capture exactly that distinction.

S3.1 EXCLUSIONS — set_chroma_profile + bass_mode (2 of the design's 9 reboot setters):
  Both call apply_chroma_profile(profile) to mutate CONFIG.NOTE_OFFSET /
  CHROMAGRAM_RANGE / CHROMA_PROFILE, then reboot() ONLY IF note_offset changed
  (conditional reboot). apply_chroma_profile is an inline in visual/led_utilities.h
  (line ~1835) which the host build does NOT compile (it drags FastLED +
  k1_audio_snapshot.h + vpab_capture.h, and ODR-clashes the existing host stubs).
  serial_replay_host_stubs.h therefore stubs apply_chroma_profile to a no-op that
  returns false ("no note-offset change"). Under that stub these two setters would
  capture an EMPTY CONFIG delta and reboot:false ALWAYS — i.e. the exact opposite of
  their production behaviour. Locking that would freeze a BLIND, WRONG golden. They
  are EXCLUDED here (same precedent as set_mode) and deferred to a slice that either
  compiles the real apply_chroma_profile or mirrors it under a drift-pin. The 7 CLEAN
  reboot setters (no subsystem coupling, unconditional reboot) ARE captured: each is
  parse -> CONFIG write -> save_config() (IMMEDIATE) -> echo -> reboot(), and the
  triple locks (a) echo, (b) the CONFIG delta, (c) save_config:true + reboot:true.

NON-SHIPPING. Host-only. Run from the repo root or from within this directory.
Mirrors oracle_gdft.py / oracle_render.py PUBLIC INTERFACE: NAME / capture(firmware_root=None)
/ MUTATIONS, registered in harness_selftest.ORACLE_MODULES, gated by test_golden_master.py.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout (mirrors oracle_render.py / oracle_gdft.py)
# ---------------------------------------------------------------------------
ROOT        = Path(__file__).resolve().parents[3]            # SpectraSynq_K1_Firmware/
FIRMWARE    = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
STUBS       = ROOT / "scripts" / "regression-harness" / "stubs"
FIXEDPOINTS = ROOT / "libraries" / "FixedPoints" / "src"
HOST_GLOBALS = ROOT / "scripts" / "regression-harness" / "render_host_globals.cpp"

# Firmware subdirs added to -I (mirrors oracle_gdft.py FW_SUBDIRS — the full set a
# globals.h TU reaches).
FW_SUBDIRS = ("audio", "visual", "effects", "director", "serial", "system",
              "persistence", "calibration", "diag", "control", "network")

# COMMON substrate the render/GDFT oracles use to satisfy globals.h's data globals
# + palette tables + the host singletons (Serial/FastLED/ESP/CONFIG).
COMMON_SOURCES = [
    "system/globals.cpp",
    "visual/Palettes.cpp",
    "visual/render_params.cpp",
]

# The real pure-logic firmware TUs parse_command's full body link-references
# (recon §2). None drag audio/I2S/FreeRTOS/RMT. NOTE: control/k1_effect_queue.cpp
# is deliberately NOT compiled — it drags <FS.h>/<LittleFS.h>/EffectRegistry, and
# its only parse_command surface is the queue/dip/xfade config setters (LIVE but
# NOT in the S3.0 corpus). Those ~8 symbols are host-stubbed in
# serial_replay_host_stubs.h instead, so the link stays free of the flash stack.
MODULE_CPPS = [
    "serial/serial_tx.cpp",
    "serial/serial_parse_helpers.cpp",
    "serial/serial_cmd_handlers.cpp",  # S4: the 23 pure CONFIG setters lifted out of
                                       # parse_command's ladder. parse_command (in
                                       # serial_menu.h, #included by the driver) now
                                       # calls serial_cmd_dispatch_pure_setter() here;
                                       # the golden must reproduce byte-for-byte (the
                                       # identity IS the S4 behaviour-preservation proof).
    "serial/serial_menu.cpp",          # M2.1 R1: out-of-line home for serial_menu.h's
                                       # non-inline defs (ODR-bomb kill). The driver
                                       # #includes serial_menu.h (now the prototypes for
                                       # the moved fns); this TU supplies the definitions
                                       # the driver + serial_cmd_handlers.cpp link against.
                                       # Golden must reproduce byte-for-byte (behaviour
                                       # preserved by the verbatim move).
    "serial/serial_typed_dispatch.cpp",  # M2.1 R2: Stage-B typed table handlers.
    "director/k1_smart_director.cpp",
    "director/k1_edgemixer.cpp",
    "director/k1_visual_hooks.cpp",
    "director/k1_mode_selection.cpp",
]

# Compiler preference: GCC (FixedPoints SQ15x16 compound-literal compat; mirrors
# oracle_render.py / oracle_gdft.py).
_GPP_CANDIDATES = ["g++-15", "g++-14", "g++-13", "g++-12", "g++"]

# ---------------------------------------------------------------------------
# Oracle identity
# ---------------------------------------------------------------------------
NAME = "serial_replay"

# Production-matching defines: the [env:k1_hardware] flag set (so the golden pins
# PRODUCTION branch structure — every probe/harness/registry #ifdef compiles out
# exactly as it does in the shipped TU). K1_RENDER_HOST_TEST activates
# render_host_globals.cpp's host singletons. K1_SERIAL_REPLAY_HOST flips the
# Serial/USBSerial host sink from no-op to RECORDING (driver-local; does not touch
# the shared stubs, so the other 6 oracles stay byte-identical).
DEFINES = [
    "K1_HARDWARE",          # production: USBSerial #define'd to Serial; pin map
    "K1_RENDER_HOST_TEST",     # render_host_globals host singletons
    "K1_SERIAL_REPLAY_HOST",   # driver-local: make Serial recording (text = golden)
    "K1_TEMPO_CONF_V2",
    "K1_TEMPO_FLYWHEEL_V2",
    "K1_ONSET_V2",
    "K1_CHORD_V2",
    "K1_SEMANTIC_STATE",
    "K1_CHORD_HUE_V1",
    "K1_DROP_CUT_V1",
    "K1_VIVID_PRECOMP_V1",
    "K1_LOUD_GUARD_V1",
    "DEFAULT_SAMPLE_RATE=12800",
    "DEFAULT_SAMPLES_PER_CHUNK=96",
    "K1_TEMPO_NOVELTY_DECIMATION=3U",
]

# ---------------------------------------------------------------------------
# The corpus — a deterministic ordered list of command strings (design §4 S3.0).
# Three sub-classes: (1) valid pure sets, (2) clamp/boundary, (3) =default +
# malformed/bad_command. One representative per pure setter, plus the edge cases
# that catch the silent-drift targets (clamp bounds, the failure path).
#
# Format: each entry is the raw command buffer fed to parse_command, exactly as a
# typed "type=value" line arrives over serial.
# ---------------------------------------------------------------------------
CORPUS = [
    # ---- (1) valid pure sets: one representative value per pure setter --------
    "photons=0.8",
    "chroma=0.5",
    "mood=0.6",
    "palette_mode=true",
    "palette_index=2",
    "square_iter=4",
    "led_interpolation=true",
    "base_coat=true",
    "temporal_dithering=true",
    "sensitivity=2.5",
    "mirror_enabled=true",
    "sweet_spot_min=100",
    "sweet_spot_max=900",
    "chromagram_range=24",
    "standby_dimming=true",
    "reverse_order=true",
    "max_current_ma=1500",
    "auto_color_shift=true",
    "incandescent_filter=0.5",
    "incandescent_mode=true",
    "bulb_opacity=0.75",
    "saturation=0.25",
    "prism_count=3",

    # ---- (2) clamp / boundary: prove the constrain() / manual-clamp bounds -----
    "chroma=9.9",          # -> clamp 1.0
    "chroma=-1",           # -> clamp 0.0
    "photons=-1",          # -> clamp 0.05 (low bound is 0.05, not 0)
    "photons=2.0",         # -> clamp 1.0
    "square_iter=99",      # -> clamp 10
    "square_iter=-5",      # -> clamp 0
    "prism_count=99",      # -> clamp 10
    "chromagram_range=999",# -> clamp NUM_FREQS
    "chromagram_range=0",  # -> clamp 1 (low bound)
    "saturation=9.9",      # -> manual clamp 1.0
    "saturation=-1",       # -> manual clamp 0.0
    "bulb_opacity=2.0",    # -> manual clamp 1.0
    "incandescent_filter=2.0",  # -> manual clamp 1.0
    "sensitivity=99",     # -> clamp K1_SENSITIVITY_MAX

    # ---- (3) =default + malformed/bad_command: lock the failure path ----------
    "chroma=default",      # reads CONFIG_DEFAULTS.CHROMA
    "sensitivity=default", # reads CONFIG_DEFAULTS.SENSITIVITY
    "square_iter=default", # reads CONFIG_DEFAULTS.SQUARE_ITER
    "mirror_enabled=default",  # enum default branch
    "chroma=",             # empty -> vp_parse_float fails -> bad_command
    "photons=abc",         # non-numeric -> vp_parse_float fails -> bad_command
    "sensitivity=abc",     # non-numeric -> vp_parse_float fails -> bad_command
    "palette_mode=maybe",  # not a bool token -> bad_command
    "base_coat=default",   # base_coat has NO default token -> bad_command
    "unknown_cmd=1",       # unknown command_type -> bad_command
    "palette_index=9999",  # out of [0, gGradientPaletteCount) -> bad_command

    # ===================================================================
    # S3.1 EXTENSION — the 7 CLEAN reboot-bearing setters (design §4 named 9;
    # set_chroma_profile + bass_mode are EXCLUDED — see header docstring + report:
    # their reboot is CONDITIONAL on apply_chroma_profile()'s return, and that
    # function lives in led_utilities.h which the host build does NOT compile in
    # (it is stubbed to a no-op). Capturing them here would freeze the WRONG
    # behaviour — empty CONFIG delta + reboot:false always — exactly the blind-lock
    # trap. They are deferred like set_mode was in S3.0.).
    #
    # The 7 clean setters are each parse -> CONFIG write -> save_config() (IMMEDIATE)
    # -> echo -> reboot(). The triple captures: (a) echo text, (b) the CONFIG field
    # delta, (c) save_config:true + reboot:true. This is the load-bearing new
    # coverage: a botched extraction (S4.1) that drops the reboot, or mis-routes the
    # CONFIG write, or swaps save_config for save_config_delayed, diverges the golden.
    # ===================================================================
    # ---- (4) valid reboot sets: one representative per clean reboot setter -----
    "sample_rate=16000",        # CONFIG.SAMPLE_RATE write + save_config + reboot
    "note_offset=6",            # CONFIG.NOTE_OFFSET write + save_config + reboot
    "led_type=neopixel",        # CONFIG.LED_TYPE + LED_COLOR_ORDER(GRB) + reboot
    "led_type=dotstar",         # CONFIG.LED_TYPE + LED_COLOR_ORDER(BGR) + reboot
    "led_count=300",            # CONFIG.LED_COUNT write + save_config + reboot
    "led_color_order=RGB",      # CONFIG.LED_COLOR_ORDER write + save_config + reboot
    "samples_per_chunk=128",    # CONFIG.SAMPLES_PER_CHUNK write + save_config + reboot
    "boot_animation=false",     # CONFIG.BOOT_ANIMATION write + save_config + reboot

    # ---- (5) reboot-setter clamp / boundary + =default branches ---------------
    "sample_rate=100",          # -> constrain low bound 6400 + reboot
    "sample_rate=99999",        # -> constrain high bound 44100 + reboot
    "sample_rate=default",      # reads CONFIG_DEFAULTS.SAMPLE_RATE + reboot
    "note_offset=99",           # -> constrain high bound 32 + reboot
    "note_offset=default",      # reads CONFIG_DEFAULTS.NOTE_OFFSET + reboot
    "led_count=0",              # -> constrain low bound 1 + reboot
    "led_count=default",        # reads CONFIG_DEFAULTS.LED_COUNT + reboot
    "led_color_order=default",  # reads CONFIG_DEFAULTS.LED_COLOR_ORDER + reboot
    "samples_per_chunk=99999",  # -> constrain high bound SAMPLE_HISTORY_LENGTH + reboot
    "samples_per_chunk=default",# reads CONFIG_DEFAULTS.SAMPLES_PER_CHUNK + reboot
    "boot_animation=default",   # reads CONFIG_DEFAULTS.BOOT_ANIMATION + reboot
    "boot_animation=true",      # -> true branch + reboot

    # ---- (6) reboot-setter bad_command paths (no reboot fires) ----------------
    "led_type=foo",             # not a led-type token -> bad_command, NO reboot
    "led_color_order=XYZ",      # not a colour-order token -> bad_command, NO reboot
    "boot_animation=maybe",     # not a bool/default token -> bad_command, NO reboot

    # ===================================================================
    # Fα VP-TUNING EXTENSION — 17 production-live VP handlers (no save_config,
    # no reboot). Each writes a VP inline global via vp_set_flag/float_command.
    # config_delta now tracks the VP globals (snapshot extended above).
    # ===================================================================
    # ---- (7) valid VP flag sets: one representative per flag handler ----------
    "vp_fix1=false",            # alias -> VP_FIX_AGC_SOFT_KNEE = false
    "vp_agc_soft=true",         # primary name alias-routing check
    "vp_fix2=false",            # -> VP_FIX_CHROMAGRAM_SPARSENESS = false
    "vp_fix3=false",            # -> VP_FIX_PRISM_DEFAULT_OFF = false
    "vp_fix4=true",             # -> VP_FIX_BLOOM_DECAY = true
    "vp_fix5=false",            # -> VP_FIX_HSV_SOURCE_SAT = false
    "vp_secondary_clean=false", # -> VP_FIX_SECONDARY_CLEAN = false
    "vp_bloom_force_sat=false", # -> VP_BLOOM_FORCE_SATURATION = false

    # ---- (8) valid VP float sets: one representative per float handler --------
    "vp_bloom_alpha=0.90",      # VP_BLOOM_ALPHA = 0.90 (in [0.80, 1.00])
    "vp_bloom_shift=1.5",       # VP_BLOOM_SHIFT_SCALE = 1.5 (in [0.25, 2.00])
    "vp_wave_idle_fade=0.90",   # VP_WAVEFORM_IDLE_FADE = 0.90 (in [0.50, 0.999])
    "vp_wave_raw_margin=2.0",   # VP_WAVEFORM_REACTIVE_RAW_MARGIN = 2.0 (in [1.00, 3.00])
    "vp_wave_peak_floor=0.10",  # VP_WAVEFORM_REACTIVE_PEAK_FLOOR = 0.10 (in [0.00, 1.00])
    "vp_wave_active_fade=0.10", # VP_WAVEFORM_ACTIVE_FADE_REDUCTION = 0.10 (in [0.00, 0.50])
    "vp_wave_blend_gain=3.0",   # VP_WAVEFORM_CHROMA_BLEND_GAIN = 3.0 (in [0.00, 4.00])
    "vp_wave_fallback=0.5",     # VP_WAVEFORM_FALLBACK_BRIGHTNESS = 0.5 (in [0.00, 1.00])
    "vp_wave_vu_floor=0.05",    # VP_WAVEFORM_VU_FLOOR = 0.05 (in [0.00, 1.00])
    "vp_wave_shift=120",        # VP_WAVEFORM_SHIFT_RATE = 120.0 (in [0.00, 240.00])

    # ---- (9) VP float clamp boundary: prove the manual clamp bounds ----------
    "vp_bloom_alpha=0.79",      # below 0.80 -> clamped to 0.80 (VP_BLOOM_ALPHA)
    "vp_bloom_alpha=1.01",      # above 1.00 -> clamped to 1.00 (VP_BLOOM_ALPHA)

    # ===================================================================
    # Fα VIVID EXTENSION — 4 vivid handlers (K1_VIVID_PRECOMP_V1, gated in
    # parse_command by #ifdef). Each writes a VP_VIVID_* inline global.
    # config_delta now tracks the VP_VIVID_* globals (snapshot extended above).
    # ===================================================================
    # ---- (10) valid vivid sets: one representative per handler ----------
    "vivid=on",                 # VP_VIVID_PRECOMP = true + serial_ensure_vivid_defaults()
    "vivid=off",                # VP_VIVID_PRECOMP = false
    "vivid_level=0.7",          # serial_set_vivid_level(0.7) -> CHROMA=0.7, BLACK=scaled
    "vivid_chroma=0.5",         # VP_VIVID_CHROMA_LEVEL = constrain(0.5, 0.0, 1.0) = 0.5
    "vivid_black=0.3",          # VP_VIVID_BLACK_LEVEL = constrain(0.3, 0.0, 1.0) = 0.3

    # ---- (11) vivid clamp/boundary: prove the constrain() bounds ----------
    "vivid_chroma=1.5",         # above 1.0 -> clamped to 1.0 (VP_VIVID_CHROMA_LEVEL)
    "vivid_chroma=-0.1",        # below 0.0 -> clamped to 0.0 (VP_VIVID_CHROMA_LEVEL)
    "vivid_black=1.5",          # above 1.0 -> clamped to 1.0 (VP_VIVID_BLACK_LEVEL)

    # ---- (12) vivid failure path: bad_command -------------------------
    "vivid=maybe",              # not a bool token -> bad_command

    # ===================================================================
    # response_gain EXTENSION — 1 ungated production-live handler. Writes the
    # audio_response_gain inline global (globals.h:48) via serial_clamp_float
    # (MIN 0.25, MAX 4.0, DEFAULT 1.0). NO save_config, NO reboot, and — unlike the
    # pure setters — NO bad_command path (atof() fallback: garbage -> 0.0 -> clamp
    # MIN). config_delta tracks AUDIO_RESPONSE_GAIN (snapshot extended above); echo
    # reads audio_response_gain_clamped() at 6 dp.
    # ===================================================================
    # ---- (13) response_gain: nominal + clamp boundaries + default + atof-fallback
    "response_gain=2.0",        # audio_response_gain = 2.0 (in [0.25, 4.0])
    "response_gain=0.1",        # below 0.25 -> clamped to MIN 0.25
    "response_gain=9.9",        # above 4.0  -> clamped to MAX 4.0
    "response_gain=default",    # -> DEFAULT_AUDIO_RESPONSE_GAIN = 1.0
    "response_gain=abc",        # atof("abc")=0.0 -> clamp MIN 0.25, NO bad_command

    # ===================================================================
    # secondary_* EXTENSION — the 14 pure inline-global secondary-channel setters
    # (globals.h:796-823, UNGATED; NO save_config/reboot/subsystem calls). Bool handlers
    # accept ONLY "true"/"false" (NOT on/off) -> bad_command otherwise; float handlers use
    # constrain(atof(...)) with NO bad_command path (garbage -> 0.0 -> clamp low);
    # palette_index validates [0, gGradientPaletteCount). secondary_mode + secondary_status
    # are NOT extracted (see snapshot note). config_delta tracks the 14 globals.
    # ===================================================================
    # ---- (14) valid secondary sets: one representative per handler -------------
    "secondary_auto_color_shift=true",   # SECONDARY_AUTO_COLOR_SHIFT = true
    "secondary_incandescent_mode=true",  # SECONDARY_INCANDESCENT_MODE = true
    "secondary_enabled=true",            # ENABLE_SECONDARY_LEDS = true
    "secondary_photons=0.8",             # SECONDARY_PHOTONS = 0.8
    "secondary_chroma=0.5",              # SECONDARY_CHROMA = 0.5
    "secondary_mood=0.6",                # SECONDARY_MOOD = 0.6
    "secondary_saturation=0.25",         # SECONDARY_SATURATION = 0.25
    "secondary_prism_count=3",           # SECONDARY_PRISM_COUNT = 3.0
    "secondary_mirror_enabled=true",     # SECONDARY_MIRROR_ENABLED = true
    "secondary_reverse_order=true",      # SECONDARY_REVERSE_ORDER = true
    "secondary_control=true",            # secondaryMode = true
    "secondary_control=toggle",          # secondaryMode = !secondaryMode (toggle branch)
    "secondary_palette_mode=true",       # SECONDARY_PALETTE_MODE_ENABLED = true
    "secondary_palette_index=2",         # SECONDARY_PALETTE_INDEX = 2 (+ paletteNames echo)
    "secondary_base_coat=true",          # SECONDARY_BASE_COAT = true

    # ---- (15) secondary float clamp boundaries: constrain(atof(...), lo, hi) ----
    "secondary_photons=2.0",             # -> clamp 1.0
    "secondary_photons=-1",              # -> clamp 0.0
    "secondary_chroma=9.9",              # -> clamp 1.0
    "secondary_mood=-1",                 # -> clamp 0.0
    "secondary_saturation=9.9",          # -> clamp 1.0
    "secondary_prism_count=99",          # -> clamp 10.0
    "secondary_prism_count=-1",          # -> clamp 0.0
    "secondary_photons=abc",             # atof("abc")=0.0 -> clamp 0.0, NO bad_command

    # ---- (16) secondary bad_command paths (bool handlers accept ONLY true/false) -
    "secondary_auto_color_shift=on",     # "on" NOT accepted -> bad_command
    "secondary_enabled=maybe",           # -> bad_command
    "secondary_control=maybe",           # not true/false/toggle -> bad_command
    "secondary_palette_index=9999",      # out of [0, count) -> bad_command
    "secondary_palette_index=-1",        # index < 0 -> bad_command
]

# ---------------------------------------------------------------------------
# C++ driver.
#
# Drives the REAL parse_command (included from serial_menu.h) over the corpus,
# capturing the TRIPLE per command. Provides:
#   * a RECORDING serial sink (K1_SERIAL_REPLAY_HOST): a g_sb_replay_out string
#     accumulates every print()/println() exactly as Arduino's Print would format
#     it (int as int, float with N digits default 2 / explicit 6, "on"/"off"
#     literals as passed, Arduino half-away-from-zero float rounding). The text IS
#     the golden — consistency pre/post-S4 is the contract.
#   * recording-no-op stubs for the device side-effects (save_config /
#     save_config_delayed / reboot / set_preset / check_current_function): each
#     sets a fired flag and returns (reboot RETURNS — control flow identical, the
#     process never exits). No ODR clash (serial_menu.h pulls none of their headers).
#   * a per-command CONFIG snapshot/delta of the curated touched-field set.
#
# Emits one JSONL record per corpus command: {cmd, emitted, config_delta,
# save_config, save_config_delayed, reboot, bad_command}.
# ---------------------------------------------------------------------------
DRIVER = r"""
// oracle_serial_replay_driver.cpp  (HOST-ONLY, -DK1_SERIAL_REPLAY_HOST)
// Drives the REAL parse_command() over the S3.0 pure-setter corpus and dumps the
// capture triple per command. Compiled by oracle_serial_replay.py — NOT shipped.

#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
#include <cmath>

// The RECORDING serial sink lives in stubs/Arduino.h, gated by
// K1_SERIAL_REPLAY_HOST: under that flag HostSerial's print/println append to the
// shared inline accumulator g_sb_replay_out (declared there), formatted to match
// Arduino Print's contract. It must be ONE shared definition so every compiled TU
// records into the same buffer — the driver TU, AND serial_tx.cpp (tx_begin /
// tx_end / bad_command echo through USBSerial too). globals.h (under
// K1_HARDWARE) does `#define USBSerial Serial`, and `HostSerial Serial`'s
// storage is defined once in render_host_globals.cpp.
#include "globals.h"   // brings parse_command's whole world (USBSerial #def -> Serial)
// g_sb_replay_out is declared inline in stubs/Arduino.h (via globals.h -> Arduino.h).

// Host stubs for the symbols serial_menu.h's WHOLE body references (FIRMWARE_VERSION,
// pgmspace shims, I2S_NUM_0, esp_reset_reason, the device handlers, the k1_queue_*
// config entry points). Included AFTER globals.h (so config_types.h's enums exist
// for apply_chroma_profile) and BEFORE serial_menu.h. None are in the corpus; they
// only need to compile + link. See serial_replay_host_stubs.h header comment.
#include "serial_replay_host_stubs.h"

// ---------------------------------------------------------------------------
// Device side-effect RECORDING-NO-OP stubs. parse_command's pure setters call
// save_config_delayed (all but prism_count) / save_config (prism_count). The
// reboot-bearing setters are excluded from the corpus, but reboot() must still
// LINK (the branch compiles). Each sets a fired flag; reboot RETURNS (no exit).
// serial_menu.h does NOT include bridge_fs.h/system.h/presets.h, so these are the
// SOLE definitions — no ODR clash. Signatures match the extern decls at
// serial_menu.h:46-47 (void reboot(); void check_current_function();).
// ---------------------------------------------------------------------------
static bool g_save_config_fired = false;
static bool g_save_config_delayed_fired = false;
static bool g_reboot_fired = false;

void save_config()         { g_save_config_fired = true; }
void save_config_delayed() { g_save_config_delayed_fired = true; }
void reboot()              { g_reboot_fired = true; return; }
void set_preset(char*)     {}
void check_current_function() {}
void factory_reset()       {}
void restore_defaults()    {}
void clear_noise_cal()     {}
float k1_queue_transition_scale_primary = 1.0f;
float k1_queue_transition_scale_secondary = 1.0f;
int raw_dump_request = 0;

// bad_command() lives in serial_tx.cpp (compiled in) and prints via USBSerial; to
// detect that the parse-failure path was taken we sniff the recorded text for the
// "Bad command: " envelope it emits (serial_tx.cpp:49). Robust because that exact
// literal is emitted by bad_command and nowhere else in a pure-setter echo.
static bool emitted_bad_command(const std::string& before, const std::string& after) {
  return after.find("Bad command: ", before.size()) != std::string::npos;
}

#include "serial_menu.h"   // the REAL parse_command (+ serial_cmd_table machinery)

// ---------------------------------------------------------------------------
// LINK stubs for serial_menu.h whole-body symbols that need the firmware TYPES
// (K1ChannelPreset / K1AudioSnapshot), so they are DEFINED here, AFTER the header.
// All belong to handlers OUTSIDE the S3.0 corpus (noise-cal arm/disarm/confirm,
// preset slot save/get, queue arm/commit, the output probe, the audio snapshot
// read, the benchmark/FPS-stream globals). They only need to LINK; behaviour is
// irrelevant to the pure-setter golden. serial_menu.h forward-declares each, so
// these are the SOLE definitions (no ODR clash — the real TUs are not compiled).
// ---------------------------------------------------------------------------
// noise-cal arm FSM (control/k1_noise_cal_arm.cpp — not compiled)
void k1_noise_cal_arm() {}
void k1_noise_cal_disarm() {}
bool k1_noise_cal_confirm(uint32_t /*now_ms*/) { return false; }

// effect-queue surface beyond the config setters stubbed in the host-stub header
// (control/k1_effect_queue.cpp — not compiled; drags FS/LittleFS)
bool k1_queue_any_armed() { return false; }
K1ChannelPreset* k1_queue_arm_begin(bool /*secondary*/) { return nullptr; }
void k1_queue_arm_preset(bool /*secondary*/, const K1ChannelPreset& /*preset*/) {}
void k1_queue_request_commit(bool /*cued*/, uint32_t /*now_ms*/) {}
bool k1_queue_mode_enabled() { return false; }
uint8_t k1_queue_transition_style() { return 0; }
// k1_effect_queue.h config setters/getters (k1_effect_queue.h:134-140). EXTERNAL defs
// here (moved out of serial_replay_host_stubs.h) so the EXTRACTED
// serial_cmd_dispatch_queue() in serial_cmd_handlers.cpp — a separate TU that only
// sees the declaration — links them too. Values irrelevant (queue not in the corpus).
uint16_t k1_queue_dip_ms() { return 0; }
bool     k1_queue_set_dip_ms(uint32_t) { return true; }
uint16_t k1_queue_xfade_ms() { return 0; }
bool     k1_queue_set_xfade_ms(uint32_t) { return true; }
uint8_t  k1_queue_commit_quantise() { return 0; }
void     k1_queue_set_commit_quantise(uint8_t) {}
void     k1_queue_set_transition_style(uint8_t) {}
void     k1_queue_set_mode_enabled(bool) {}
bool k1_preset_slot_save(uint8_t /*slot*/, bool /*from_secondary*/) { return false; }
bool k1_preset_slot_get(uint8_t /*slot*/, K1ChannelPreset* /*out*/) { return false; }
void k1_queue_apply_fields(bool /*secondary*/, const K1ChannelPreset& /*preset*/) {}

// show-state (control/k1_show_state.cpp — not compiled; LittleFS). Hotkey 'S' /
// :save_show are not in the S3.0 corpus; stubs only need to link.
bool k1_show_state_save() { return false; }
bool k1_show_state_load() { return false; }

// vp output probe (visual/lightshow_modes.h inline — header not pulled) + audio
// snapshot read (audio/k1_audio_snapshot.cpp — not compiled)
void vp_run_output_probe() {}
void vp_print_secondary_state() {}
K1AudioSnapshot k1_audio_snapshot_read() { K1AudioSnapshot s = {}; return s; }

// benchmark / FPS-stream globals: serial_menu.h declares these extern (real
// storage is in the .ino TU). Provide host storage so the FPS-stream branches link.
bool     benchmark_running = false;
uint32_t benchmark_start_time = 0;
uint32_t system_fps_sum = 0;
uint32_t led_fps_sum = 0;
uint32_t benchmark_sample_count = 0;

// ---------------------------------------------------------------------------
// CONFIG field snapshot. We capture the curated set of fields the 23 pure setters
// touch, as a label->double map (printed at fixed precision so float drift is
// absorbed by the gate's FLOAT_TOL). A per-command delta = fields whose value
// changed vs the pre-command snapshot.
// ---------------------------------------------------------------------------
struct FieldSnap { const char* name; double value; };

static int snapshot(FieldSnap* out) {
  int n = 0;
  out[n++] = {"PHOTONS",              (double)CONFIG.PHOTONS};
  out[n++] = {"CHROMA",               (double)CONFIG.CHROMA};
  out[n++] = {"MOOD",                 (double)CONFIG.MOOD};
  out[n++] = {"PALETTE_MODE_ENABLED", (double)CONFIG.PALETTE_MODE_ENABLED};
  out[n++] = {"PALETTE_INDEX",        (double)CONFIG.PALETTE_INDEX};
  out[n++] = {"SQUARE_ITER",          (double)CONFIG.SQUARE_ITER};
  out[n++] = {"LED_INTERPOLATION",    (double)CONFIG.LED_INTERPOLATION};
  out[n++] = {"BASE_COAT",            (double)CONFIG.BASE_COAT};
  out[n++] = {"TEMPORAL_DITHERING",   (double)CONFIG.TEMPORAL_DITHERING};
  out[n++] = {"SENSITIVITY",          (double)CONFIG.SENSITIVITY};
  out[n++] = {"MIRROR_ENABLED",       (double)CONFIG.MIRROR_ENABLED};
  out[n++] = {"SWEET_SPOT_MIN_LEVEL", (double)CONFIG.SWEET_SPOT_MIN_LEVEL};
  out[n++] = {"SWEET_SPOT_MAX_LEVEL", (double)CONFIG.SWEET_SPOT_MAX_LEVEL};
  out[n++] = {"CHROMAGRAM_RANGE",     (double)CONFIG.CHROMAGRAM_RANGE};
  out[n++] = {"STANDBY_DIMMING",      (double)CONFIG.STANDBY_DIMMING};
  out[n++] = {"REVERSE_ORDER",        (double)CONFIG.REVERSE_ORDER};
  out[n++] = {"MAX_CURRENT_MA",       (double)CONFIG.MAX_CURRENT_MA};
  out[n++] = {"AUTO_COLOR_SHIFT",     (double)CONFIG.AUTO_COLOR_SHIFT};
  out[n++] = {"INCANDESCENT_FILTER",  (double)CONFIG.INCANDESCENT_FILTER};
  out[n++] = {"INCANDESCENT_MODE",    (double)CONFIG.INCANDESCENT_MODE};
  out[n++] = {"BULB_OPACITY",         (double)CONFIG.BULB_OPACITY};
  out[n++] = {"SATURATION",           (double)CONFIG.SATURATION};
  out[n++] = {"PRISM_COUNT",          (double)CONFIG.PRISM_COUNT};
  // S3.1: the 7 clean reboot-bearing setters' CONFIG fields. Without these in the
  // snapshot the config_delta channel would be BLIND to a mis-routed reboot-setter
  // write (the whole point of the new coverage).
  out[n++] = {"SAMPLE_RATE",          (double)CONFIG.SAMPLE_RATE};
  out[n++] = {"NOTE_OFFSET",          (double)CONFIG.NOTE_OFFSET};
  out[n++] = {"LED_TYPE",             (double)CONFIG.LED_TYPE};
  out[n++] = {"LED_COLOR_ORDER",      (double)CONFIG.LED_COLOR_ORDER};
  out[n++] = {"LED_COUNT",            (double)CONFIG.LED_COUNT};
  out[n++] = {"SAMPLES_PER_CHUNK",    (double)CONFIG.SAMPLES_PER_CHUNK};
  out[n++] = {"BOOT_ANIMATION",       (double)CONFIG.BOOT_ANIMATION};
  // Fα VP-tuning extension: 17 live VP globals written by vp_set_flag/float_command.
  // Without these the config_delta channel is BLIND to mis-routed VP writes (the
  // globals are not in CONFIG, so CONFIG delta stays empty on every VP command).
  out[n++] = {"VP_FIX_AGC_SOFT_KNEE",             (double)VP_FIX_AGC_SOFT_KNEE};
  out[n++] = {"VP_FIX_CHROMAGRAM_SPARSENESS",      (double)VP_FIX_CHROMAGRAM_SPARSENESS};
  out[n++] = {"VP_FIX_PRISM_DEFAULT_OFF",          (double)VP_FIX_PRISM_DEFAULT_OFF};
  out[n++] = {"VP_FIX_BLOOM_DECAY",                (double)VP_FIX_BLOOM_DECAY};
  out[n++] = {"VP_FIX_HSV_SOURCE_SAT",             (double)VP_FIX_HSV_SOURCE_SAT};
  out[n++] = {"VP_FIX_SECONDARY_CLEAN",            (double)VP_FIX_SECONDARY_CLEAN};
  out[n++] = {"VP_BLOOM_ALPHA",                    (double)VP_BLOOM_ALPHA};
  out[n++] = {"VP_BLOOM_SHIFT_SCALE",              (double)VP_BLOOM_SHIFT_SCALE};
  out[n++] = {"VP_BLOOM_FORCE_SATURATION",         (double)VP_BLOOM_FORCE_SATURATION};
  out[n++] = {"VP_WAVEFORM_IDLE_FADE",             (double)VP_WAVEFORM_IDLE_FADE};
  out[n++] = {"VP_WAVEFORM_REACTIVE_RAW_MARGIN",   (double)VP_WAVEFORM_REACTIVE_RAW_MARGIN};
  out[n++] = {"VP_WAVEFORM_REACTIVE_PEAK_FLOOR",   (double)VP_WAVEFORM_REACTIVE_PEAK_FLOOR};
  out[n++] = {"VP_WAVEFORM_ACTIVE_FADE_REDUCTION", (double)VP_WAVEFORM_ACTIVE_FADE_REDUCTION};
  out[n++] = {"VP_WAVEFORM_CHROMA_BLEND_GAIN",     (double)VP_WAVEFORM_CHROMA_BLEND_GAIN};
  out[n++] = {"VP_WAVEFORM_FALLBACK_BRIGHTNESS",   (double)VP_WAVEFORM_FALLBACK_BRIGHTNESS};
  out[n++] = {"VP_WAVEFORM_VU_FLOOR",              (double)VP_WAVEFORM_VU_FLOOR};
  out[n++] = {"VP_WAVEFORM_SHIFT_RATE",            (double)VP_WAVEFORM_SHIFT_RATE};
  // Fα vivid extension: 3 vivid inline globals written by the vivid handlers.
  // UNCONDITIONAL — VP_VIVID_PRECOMP/CHROMA_LEVEL/BLACK_LEVEL exist in globals.h
  // outside any #ifdef (lines 465-467). Without these the config_delta is BLIND
  // to mis-routed or wrong-clamp vivid writes (the whole point of the new coverage).
  out[n++] = {"VP_VIVID_PRECOMP",      (double)VP_VIVID_PRECOMP};
  out[n++] = {"VP_VIVID_CHROMA_LEVEL", (double)VP_VIVID_CHROMA_LEVEL};
  out[n++] = {"VP_VIVID_BLACK_LEVEL",  (double)VP_VIVID_BLACK_LEVEL};
  // response_gain extension: audio_response_gain inline global (globals.h:48,
  // UNGATED) written by the response_gain handler via serial_clamp_float (MIN 0.25,
  // MAX 4.0, DEFAULT 1.0). NOT a CONFIG field — read directly like the VP/vivid
  // globals. Without it the config_delta channel is BLIND to a mis-routed or
  // wrong-clamp response_gain write (the whole point of the new coverage).
  out[n++] = {"AUDIO_RESPONSE_GAIN",   (double)audio_response_gain};
  // secondary_* extension: the 14 inline globals (globals.h:796-823, UNGATED) written
  // by the 14 pure secondary-channel setters. NOT CONFIG fields — read directly like
  // the VP/vivid/response_gain globals. Without these the config_delta channel is BLIND
  // to a mis-routed or wrong-clamp secondary write (the whole point of the coverage).
  // SECONDARY_LIGHTSHOW_MODE is DELIBERATELY omitted — the secondary_mode handler is NOT
  // extracted (function-call + #ifdef K1_EFFECT_REGISTRY_V1; deferred with set_mode).
  out[n++] = {"SECONDARY_AUTO_COLOR_SHIFT",    (double)SECONDARY_AUTO_COLOR_SHIFT};
  out[n++] = {"SECONDARY_INCANDESCENT_MODE",   (double)SECONDARY_INCANDESCENT_MODE};
  out[n++] = {"ENABLE_SECONDARY_LEDS",         (double)ENABLE_SECONDARY_LEDS};
  out[n++] = {"SECONDARY_PHOTONS",             (double)SECONDARY_PHOTONS};
  out[n++] = {"SECONDARY_CHROMA",              (double)SECONDARY_CHROMA};
  out[n++] = {"SECONDARY_MOOD",                (double)SECONDARY_MOOD};
  out[n++] = {"SECONDARY_SATURATION",          (double)SECONDARY_SATURATION};
  out[n++] = {"SECONDARY_PRISM_COUNT",         (double)SECONDARY_PRISM_COUNT};
  out[n++] = {"SECONDARY_MIRROR_ENABLED",      (double)SECONDARY_MIRROR_ENABLED};
  out[n++] = {"SECONDARY_REVERSE_ORDER",       (double)SECONDARY_REVERSE_ORDER};
  out[n++] = {"secondaryMode",                 (double)secondaryMode};
  out[n++] = {"SECONDARY_PALETTE_MODE_ENABLED",(double)SECONDARY_PALETTE_MODE_ENABLED};
  out[n++] = {"SECONDARY_PALETTE_INDEX",       (double)SECONDARY_PALETTE_INDEX};
  out[n++] = {"SECONDARY_BASE_COAT",           (double)SECONDARY_BASE_COAT};
  return n;
}

// Escape a string for embedding in JSON (quotes, backslash, newline, control).
static std::string json_escape(const std::string& s) {
  std::string o;
  for (char c : s) {
    switch (c) {
      case '"':  o += "\\\""; break;
      case '\\': o += "\\\\"; break;
      case '\n': o += "\\n";  break;
      case '\r': o += "\\r";  break;
      case '\t': o += "\\t";  break;
      default:
        if ((unsigned char)c < 0x20) { char b[8]; std::snprintf(b,sizeof(b),"\\u%04x",c); o += b; }
        else o += c;
    }
  }
  return o;
}

// The corpus is injected by the Python harness as a C array literal.
static const char* CORPUS[] = {
__CORPUS_ARRAY__
};
static const int CORPUS_LEN = (int)(sizeof(CORPUS) / sizeof(CORPUS[0]));

int main() {
  // --- deterministic boot defaults -----------------------------------------
  // Zero-init CONFIG/CONFIG_DEFAULTS come from render_host_globals.cpp (conf
  // CONFIG = {}). We set CONFIG_DEFAULTS to fixed, documented values so the
  // "=default" branches are reproducible cross-machine (hazard §2). Everything
  // else stays zero. millis() is host-controlled (fixed at 0 -> deterministic).
  g_sb_host_millis = 0;

  CONFIG_DEFAULTS.CHROMA        = 1.0f;
  CONFIG_DEFAULTS.SENSITIVITY   = 1.0f;
  CONFIG_DEFAULTS.SQUARE_ITER   = 1.0f;
  CONFIG_DEFAULTS.MIRROR_ENABLED = false;

  // S3.1: fixed, documented defaults for the reboot-setter "=default" branches so
  // they are reproducible cross-machine (hazard §2). Values mirror the device
  // firmware defaults (DEFAULT_SAMPLE_RATE=12800, NOTE_OFFSET=12 per v40102,
  // LED_COUNT_VALUE=160, GRB colour order, DEFAULT_SAMPLES_PER_CHUNK=96).
  CONFIG_DEFAULTS.SAMPLE_RATE       = 12800;
  CONFIG_DEFAULTS.NOTE_OFFSET       = 12;
  CONFIG_DEFAULTS.LED_COUNT         = 160;
  CONFIG_DEFAULTS.LED_COLOR_ORDER   = GRB;
  CONFIG_DEFAULTS.SAMPLES_PER_CHUNK = 96;
  CONFIG_DEFAULTS.BOOT_ANIMATION    = true;

  FieldSnap before[96], after[96];   // 65 fields after the secondary_* extension (was 51); headroom for future families

  for (int i = 0; i < CORPUS_LEN; ++i) {
    // parse_command mutates its buffer in place -> use a writable copy.
    char buf[160];
    std::snprintf(buf, sizeof(buf), "%s", CORPUS[i]);

    int nb = snapshot(before);
    std::string text_before = g_sb_replay_out;
    g_save_config_fired = false;
    g_save_config_delayed_fired = false;
    g_reboot_fired = false;

    parse_command(buf);

    std::string emitted = g_sb_replay_out.substr(text_before.size());
    bool bad = emitted_bad_command(text_before, g_sb_replay_out);
    int na = snapshot(after);

    // --- emit one JSONL record (the triple) ---------------------------------
    std::printf("{\"cmd\":\"%s\",", json_escape(CORPUS[i]).c_str());
    std::printf("\"emitted\":\"%s\",", json_escape(emitted).c_str());

    // config_delta: only the fields that changed vs the pre snapshot.
    std::printf("\"config_delta\":{");
    bool first = true;
    for (int f = 0; f < na && f < nb; ++f) {
      if (before[f].value != after[f].value) {
        if (!first) std::printf(",");
        // 6-decimal fixed: ints are exact, floats absorbed by FLOAT_TOL=1e-3.
        std::printf("\"%s\":%.6f", after[f].name, after[f].value);
        first = false;
      }
    }
    std::printf("},");

    std::printf("\"save_config\":%s,",        g_save_config_fired ? "true" : "false");
    std::printf("\"save_config_delayed\":%s,",g_save_config_delayed_fired ? "true" : "false");
    std::printf("\"reboot\":%s,",             g_reboot_fired ? "true" : "false");
    std::printf("\"bad_command\":%s}\n",      bad ? "true" : "false");
  }
  return 0;
}
"""

# ---------------------------------------------------------------------------
# Mutations — >=3 real edits that MUST diverge the golden (Gate-Fα teeth). Each
# targets a DIFFERENT capture channel so the lock proves it is not blind to any of
# the triple:
#   1. clamp bound       -> diverges channel (b) CONFIG delta (and echo text)
#   2. mis-routed write  -> diverges channel (b) wrong field written
#   3. broken echo       -> diverges channel (a) emitted text
#   4. save-class swap   -> diverges channel (c) side-effect flags
#   5. broken bad_command-> diverges channel (a)+(d) failure path
# All are edits to serial_menu.h's setter handlers (the thing S4 will move).
# ---------------------------------------------------------------------------
MUTATIONS = [
    # 1. chroma clamp upper bound 1.0 -> 0.5. "chroma=9.9" now clamps to 0.5,
    #    diverging both the CONFIG delta AND the echoed value. Pins channel (b).
    (
        r"CONFIG\.CHROMA = constrain\(value, 0\.0f, 1\.0f\);",
        r"CONFIG.CHROMA = constrain(value, 0.0f, 0.5f);",
        "chroma_clamp_upper_1.0_to_0.5 (CONFIG-delta + echo divergence)",
    ),
    # 2. mis-route the photons write to CONFIG.MOOD. "photons=0.8" now writes the
    #    wrong field — echo still says PHOTONS but the CONFIG delta is on MOOD.
    #    This is EXACTLY the field-routing regression text alone misses. Channel (b).
    (
        r"CONFIG\.PHOTONS = constrain\(value, 0\.05f, 1\.0f\);",
        r"CONFIG.MOOD = constrain(value, 0.05f, 1.0f);",
        "photons_write_misrouted_to_MOOD (field-routing divergence text hides)",
    ),
    # 3. break the saturation echo label: "CONFIG.SATURATION: " -> "CONFIG.SAT: ".
    #    Pure emitted-text regression — the CONFIG write is unchanged, only the
    #    user-facing protocol text drifts. Channel (a).
    #    ANCHOR NOTE (red-team fix): the bare label appears TWICE in serial_menu.h —
    #    once in the dump_info status block (echoes every field, NOT in the corpus)
    #    at line ~272, once in the SETTER at ~4051. re.sub(count=1) hits the dump
    #    first => the golden would NOT change => a BLIND mutation. We anchor on the
    #    `tx_begin();` that immediately precedes ONLY the setter echo (the dump has
    #    no tx_begin), so the mutation lands on the corpus-exercised setter.
    (
        r'(tx_begin\(\);\s*\n\s*)USBSerial\.print\("CONFIG\.SATURATION: "\);',
        r'\1USBSerial.print("CONFIG.SAT: ");',
        "saturation_echo_label_broken (emitted-text divergence)",
    ),
    # 4. swap prism_count's IMMEDIATE save_config() for save_config_delayed().
    #    Echo + CONFIG identical; only the side-effect FLAG changes. Proves the
    #    lock catches the save-class behaviour. Channel (c).
    (
        r"(else if \(strcmp\(command_type, \"prism_count\"\) == 0\) \{(?:.|\n)*?)save_config\(\);",
        r"\1save_config_delayed();",
        "prism_count_save_class_swap_immediate_to_delayed (side-effect-flag divergence)",
    ),
    # 5. break the bad_command path on the chroma setter: drop the bad_command call
    #    in the parse-failure else. "chroma=abc"/"chroma=" now emit NOTHING and
    #    don't flag bad_command. Pins the failure path (channels a + d) — where a
    #    botched extraction most often regresses.
    (
        r"(else if \(strcmp\(command_type, \"chroma\"\) == 0\) \{(?:.|\n)*?)\} else \{\n\s*bad_command\(command_type, command_data\);\n\s*\}",
        r"\1} else {\n        /* bad_command removed by mutation */\n      }",
        "chroma_bad_command_path_removed (failure-path divergence)",
    ),
    # ===================================================================
    # S3.1 REBOOT-SETTER MUTATIONS — each MUST diverge the golden on the NEW
    # reboot-setter corpus, proving the extended coverage is not blind. Each
    # targets a DIFFERENT channel of the triple on a reboot-bearing setter.
    # ===================================================================
    # 6. SUPPRESS the reboot on note_offset: drop its trailing reboot() call. The
    #    echo + CONFIG delta + save_config are identical; ONLY the reboot side-effect
    #    flag flips true->false. This is the load-bearing reboot-setter regression:
    #    a botched extraction (S4.1) that drops the reboot leaves the device NOT
    #    re-seeding the GDFT freq table — silent, and text/CONFIG alone miss it.
    #    Channel (c) reboot flag. Anchored on the NOTE_OFFSET echo that uniquely
    #    precedes ONLY this reboot (NOT cmd_reset's bare reboot() at ~2029, NOT the
    #    other 8 setter reboots) so the mutation lands on the corpus-exercised branch.
    (
        r'(USBSerial\.println\(CONFIG\.NOTE_OFFSET\);\s*\n\s*tx_end\(\);\s*\n\s*)reboot\(\);',
        r'\1/* reboot suppressed by mutation */',
        "note_offset_reboot_suppressed (reboot side-effect-flag divergence)",
    ),
    # 7. MIS-ROUTE the sample_rate CONFIG write to CONFIG.LED_COUNT. "sample_rate=16000"
    #    now writes the WRONG field — the echo still says SAMPLE_RATE but the CONFIG
    #    delta lands on LED_COUNT (and SAMPLE_RATE no longer changes). Exactly the
    #    field-routing regression the echo-text channel cannot see. Channel (b).
    #    Anchored on the constrain bounds (6400, 44100) unique to sample_rate.
    (
        r"CONFIG\.SAMPLE_RATE = constrain\(atol\(command_data\), 6400, 44100\);",
        r"CONFIG.LED_COUNT = constrain(atol(command_data), 6400, 44100);",
        "sample_rate_write_misrouted_to_LED_COUNT (field-routing divergence text hides)",
    ),
    # 8. SWAP led_count's IMMEDIATE save_config() for save_config_delayed(). Echo +
    #    CONFIG + reboot identical; only the save-class FLAG changes (save_config
    #    true->false, save_config_delayed false->true). Proves the lock catches the
    #    persist-class behaviour on a reboot setter. Channel (c). Anchored inside the
    #    led_count branch so it does not collide with the 9 other save_config() sites.
    (
        r"(else if \(strcmp\(command_type, \"led_count\"\) == 0\) \{(?:.|\n)*?)save_config\(\);",
        r"\1save_config_delayed();",
        "led_count_save_class_swap_immediate_to_delayed (side-effect-flag divergence)",
    ),
    # ===================================================================
    # Fα VP-TUNING MUTATIONS — 2 edits that MUST diverge the golden on the
    # VP corpus entries. Each targets a DIFFERENT VP channel.
    # ===================================================================
    # 9. MIS-ROUTE the vp_bloom_alpha write to &VP_BLOOM_SHIFT_SCALE. "vp_bloom_alpha=0.90"
    #    now writes the WRONG VP global — the echo still says "vp_bloom_alpha: 0.9000" but
    #    the config_delta shows VP_BLOOM_ALPHA absent (unchanged) + VP_BLOOM_SHIFT_SCALE
    #    spuriously changed. Exactly the field-routing regression text alone misses. Channel (b).
    #    Anchored inside the vp_bloom_alpha branch (unique float bounds 0.80/1.00).
    (
        r"(else if \(strcmp\(command_type, \"vp_bloom_alpha\"\) == 0\) \{[^}]*)"
        r"vp_set_float_command\(command_type, command_data, &VP_BLOOM_ALPHA, 0\.80f, 1\.00f\);",
        r"\1vp_set_float_command(command_type, command_data, &VP_BLOOM_SHIFT_SCALE, 0.80f, 1.00f);",
        "vp_bloom_alpha_write_misrouted_to_VP_BLOOM_SHIFT_SCALE (field-routing divergence)",
    ),
    # 10. CHANGE the vp_bloom_alpha low clamp from 0.80f to 0.70f. "vp_bloom_alpha=0.79"
    #     now records VP_BLOOM_ALPHA=0.79 instead of the correct clamped value of 0.80.
    #     Diverges channel (b) config_delta for the boundary corpus entry. Channel (b).
    (
        r"(else if \(strcmp\(command_type, \"vp_bloom_alpha\"\) == 0\) \{[^}]*)"
        r"vp_set_float_command\(command_type, command_data, &VP_BLOOM_ALPHA, 0\.80f, 1\.00f\);",
        r"\1vp_set_float_command(command_type, command_data, &VP_BLOOM_ALPHA, 0.70f, 1.00f);",
        "vp_bloom_alpha_clamp_low_0.80_to_0.70 (CONFIG-delta divergence on boundary entry)",
    ),
    # ===================================================================
    # Fα VIVID MUTATIONS — 2 edits that MUST diverge the golden on the
    # vivid corpus entries. Each targets a DIFFERENT channel.
    # ===================================================================
    # M1. MIS-ROUTE the vivid_chroma write: change VP_VIVID_CHROMA_LEVEL ->
    #     VP_VIVID_BLACK_LEVEL. "vivid_chroma=0.5" now writes the WRONG global —
    #     config_delta shows VP_VIVID_CHROMA_LEVEL absent (unchanged) +
    #     VP_VIVID_BLACK_LEVEL spuriously changed. Field-routing regression that
    #     echo text alone misses. Channel (b).
    (
        r"(else if \(strcmp\(command_type, \"vivid_chroma\"\) == 0\) \{[^}]*)"
        r"VP_VIVID_CHROMA_LEVEL = constrain\(value, 0\.0f, 1\.0f\);",
        r"\1VP_VIVID_BLACK_LEVEL = constrain(value, 0.0f, 1.0f);",
        "vivid_chroma_write_misrouted_to_VP_VIVID_BLACK_LEVEL (field-routing divergence)",
    ),
    # M2. CHANGE the vivid_chroma upper clamp from 1.0f to 0.5f. "vivid_chroma=1.5"
    #     now records VP_VIVID_CHROMA_LEVEL=0.5 instead of the correct clamped value
    #     of 1.0. Diverges channel (b) config_delta on the boundary corpus entry.
    (
        r"(else if \(strcmp\(command_type, \"vivid_chroma\"\) == 0\) \{[^}]*)"
        r"VP_VIVID_CHROMA_LEVEL = constrain\(value, 0\.0f, 1\.0f\);",
        r"\1VP_VIVID_CHROMA_LEVEL = constrain(value, 0.0f, 0.5f);",
        "vivid_chroma_clamp_upper_1.0_to_0.5 (CONFIG-delta divergence on boundary entry)",
    ),
    # ===================================================================
    # response_gain MUTATIONS — 2 edits that MUST diverge the golden on the
    # response_gain corpus, proving the new coverage is not blind. Both anchor on
    # the SINGLE unique clamp-write line (serial_menu.h@HEAD ~3148; after extraction
    # it lives only in serial_cmd_handlers.cpp — the anchor stays unique either way).
    # ===================================================================
    # R1. CHANGE the response_gain upper clamp from AUDIO_RESPONSE_GAIN_MAX (4.0f) to
    #     2.0f. "response_gain=9.9" now records AUDIO_RESPONSE_GAIN=2.0 instead of the
    #     correct clamped 4.0 — diverges config_delta AND the echoed value on the
    #     boundary corpus entry. Channel (b).
    (
        r"audio_response_gain = serial_clamp_float\(atof\(command_data\), AUDIO_RESPONSE_GAIN_MIN, AUDIO_RESPONSE_GAIN_MAX\);",
        r"audio_response_gain = serial_clamp_float(atof(command_data), AUDIO_RESPONSE_GAIN_MIN, 2.0f);",
        "response_gain_clamp_upper_4.0_to_2.0 (CONFIG-delta + echo divergence on boundary entry)",
    ),
    # R2. MIS-ROUTE the response_gain write to VP_VIVID_BLACK_LEVEL. "response_gain=2.0"
    #     now writes the WRONG global — audio_response_gain keeps its prior value, so
    #     the echo (audio_response_gain_clamped()) AND config_delta both diverge
    #     (AUDIO_RESPONSE_GAIN absent + VP_VIVID_BLACK_LEVEL spuriously changed). This
    #     is exactly the field-routing regression echo text alone would miss were the
    #     echo not derived from the global. Channel (b).
    (
        r"audio_response_gain = serial_clamp_float\(atof\(command_data\), AUDIO_RESPONSE_GAIN_MIN, AUDIO_RESPONSE_GAIN_MAX\);",
        r"VP_VIVID_BLACK_LEVEL = serial_clamp_float(atof(command_data), AUDIO_RESPONSE_GAIN_MIN, AUDIO_RESPONSE_GAIN_MAX);",
        "response_gain_write_misrouted_to_VP_VIVID_BLACK_LEVEL (field-routing divergence)",
    ),
    # ===================================================================
    # secondary_* MUTATIONS — 3 LOCK teeth that MUST diverge the golden on the secondary
    # corpus, proving the new coverage is not blind. Each targets a DIFFERENT channel.
    # Anchored uniquely (count=1, enforced by test_mutation_anchor_uniqueness_static.py)
    # on the setter BODY: at LOCK these live inline in serial_menu.h; after EXTRACT they
    # move to serial_cmd_dispatch_secondary() in serial_cmd_handlers.cpp. The canonical
    # Gate Fα (harness_selftest.py) rglobs and finds them either home; the standalone
    # verify_mutations hardcodes serial_menu.h (known footgun) — trust harness_selftest.
    # The call-site-sever tooth is added with the EXTRACT (the call-site exists only then).
    # ===================================================================
    # S1. CHANGE the secondary_photons upper clamp 1.0 -> 0.5. "secondary_photons=2.0" now
    #     records SECONDARY_PHOTONS=0.5 instead of the correct clamped 1.0 — diverges
    #     config_delta AND the echoed value on the boundary entry. Channel (b).
    (
        r"SECONDARY_PHOTONS = constrain\(atof\(command_data\), 0\.0, 1\.0\);",
        r"SECONDARY_PHOTONS = constrain(atof(command_data), 0.0, 0.5);",
        "secondary_photons_clamp_upper_1.0_to_0.5 (CONFIG-delta + echo divergence)",
    ),
    # S2. MIS-ROUTE the secondary_chroma write to SECONDARY_MOOD. "secondary_chroma=0.5"
    #     now writes the WRONG global — echo still says SECONDARY_CHROMA but the delta
    #     lands on SECONDARY_MOOD (SECONDARY_CHROMA unchanged). Field-routing regression
    #     the echo channel cannot see. Channel (b).
    (
        r"SECONDARY_CHROMA = constrain\(atof\(command_data\), 0\.0, 1\.0\);",
        r"SECONDARY_MOOD = constrain(atof(command_data), 0.0, 1.0);",
        "secondary_chroma_write_misrouted_to_SECONDARY_MOOD (field-routing divergence)",
    ),
    # S3. BREAK the secondary_control echo label (the ENABLED arm — unique to the setter;
    #     secondary_status echoes "true (encoders control secondary channel)", different).
    #     "secondary_control=true" now emits the wrong text; the global write is unchanged.
    #     Pure emitted-text regression. Channel (a).
    (
        r'"ENABLED \(encoders control secondary channel\)"',
        r'"ENABLED (encoders control SECONDARY channel)"',
        "secondary_control_echo_label_broken (emitted-text divergence)",
    ),
    # S4. SEVER THE ROUTING (EXTRACT tooth — the call-site exists only after the lift).
    #     Disable the dispatcher call with a short-circuit `false &&` so parse_command
    #     never routes the 14 secondary commands to it; they fall through to bad_command.
    #     Every secondary record's config_delta empties + bad_command flips true -> massive
    #     divergence, proving the call-site is load-bearing. COMPILE-SAFE by design: the
    #     symbol stays referenced. A `_SEVERED` rename (the struct oracle's pure-parse
    #     trick) would FAIL the host compile, and harness_selftest._mutated_capture only
    #     catches TypeError — a RuntimeError from a broken build propagates and crashes the
    #     selftest instead of registering a clean catch. Bare-arg form `(command_type,
    #     command_data)` matches ONLY the call-site (the def/decl carry typed params).
    (
        r"serial_cmd_dispatch_secondary\(command_type, command_data\)",
        r"false && serial_cmd_dispatch_secondary(command_type, command_data)",
        "secondary_dispatcher_call_site_severed (routing/reachable divergence)",
    ),
]

# ---------------------------------------------------------------------------
# Compile + run helpers (mirror oracle_gdft.py / oracle_render.py)
# ---------------------------------------------------------------------------

def _detect_compiler():
    for cand in _GPP_CANDIDATES:
        if shutil.which(cand):
            return cand
    return "g++"


def _corpus_array_literal() -> str:
    """Render CORPUS as a C string-array body for injection into the driver."""
    return ",\n".join('  "' + c.replace("\\", "\\\\").replace('"', '\\"') + '"'
                      for c in CORPUS)


def _driver_source() -> str:
    return DRIVER.replace("__CORPUS_ARRAY__", _corpus_array_literal())


def _compile(workdir: Path, firmware_root=None) -> Path:
    fw = Path(firmware_root) if firmware_root else FIRMWARE
    main_cpp = workdir / "oracle_serial_replay_driver.cpp"
    main_cpp.write_text(_driver_source(), encoding="utf-8")
    binary = workdir / "oracle_serial_replay_bin"

    cc = _detect_compiler()

    sources = [str(fw / s) for s in COMMON_SOURCES]
    sources += [str(HOST_GLOBALS)]
    sources += [str(fw / s) for s in MODULE_CPPS]
    sources += [str(main_cpp)]

    cmd = [
        cc, "-std=c++17",
        # -O0 -fno-fast-math for strict, clean-IEEE determinism (the oracle locks
        # algorithm/branch structure; the command surface is int/string-dominated).
        "-O0", "-fno-fast-math",
        "-Wno-unused-parameter", "-Wno-unused-variable", "-Wno-unused-function",
        *[f"-D{d}" for d in DEFINES],
        "-I", str(STUBS),
        "-I", str(Path(__file__).resolve().parent),  # golden/ for serial_replay_host_stubs.h
        "-I", str(FIXEDPOINTS),
        "-I", str(fw),
        *[arg for d in FW_SUBDIRS for arg in ("-I", str(fw / d))],
        *sources,
        "-o", str(binary),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"oracle_serial_replay compile failed (rc={r.returncode}):\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDERR:\n{r.stderr}\nSTDOUT:\n{r.stdout}"
        )
    return binary


def _run(binary: Path) -> str:
    r = subprocess.run([str(binary)], cwd=str(ROOT), text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"oracle_serial_replay run failed (rc={r.returncode}):\n{r.stderr}")
    return r.stdout


def capture(firmware_root=None) -> str:
    """Compile + run; return deterministic JSON-lines golden string."""
    with tempfile.TemporaryDirectory(prefix="oracle_serial_replay_") as td:
        binary = _compile(Path(td), firmware_root=firmware_root)
        return _run(binary)


# ---------------------------------------------------------------------------
# Mutation verification helper (used by __main__; harness_selftest.py has its own
# central mutator that edits a firmware-tree COPY and re-runs capture()).
# ---------------------------------------------------------------------------

def verify_mutations(baseline: str, firmware_root=None) -> list:
    fw_src = Path(firmware_root) if firmware_root else FIRMWARE
    results = []
    for pattern, replacement, desc in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="oracle_serial_replay_mut_") as td:
            fw_copy = Path(td) / "fw"
            shutil.copytree(fw_src, fw_copy)
            target = None
            for f in fw_copy.rglob("*"):
                if f.suffix in (".cpp", ".h") and f.is_file():
                    text = f.read_text(encoding="utf-8", errors="ignore")
                    if re.search(pattern, text):
                        f.write_text(re.sub(pattern, replacement, text, count=1), encoding="utf-8")
                        target = f
                        break
            if target is None:
                results.append({"desc": desc, "diverged_lines": 0, "caught": False,
                                "error": "regex did not match"})
                continue
            try:
                mutant_out = capture(firmware_root=fw_copy)
            except RuntimeError as exc:
                results.append({"desc": desc, "diverged_lines": 0, "caught": False,
                                "error": str(exc)[:200]})
                continue
            base_lines = baseline.strip().splitlines()
            mut_lines = mutant_out.strip().splitlines()
            diverged = sum(1 for a, b in zip(base_lines, mut_lines) if a != b) \
                       + abs(len(base_lines) - len(mut_lines))
            results.append({"desc": desc, "diverged_lines": diverged, "caught": diverged > 0})
    return results


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="serial command->output replay golden-master oracle.")
    parser.add_argument("--verify-mutations", action="store_true")
    args = parser.parse_args()

    baseline = capture()
    print(baseline, end="")

    baseline2 = capture()
    if baseline != baseline2:
        print("DETERMINISM FAILURE: two runs differ.", file=sys.stderr)
        sys.exit(1)

    lines = baseline.strip().splitlines()
    print(f"\n# golden_record_count={len(lines)}", file=sys.stderr)
    print("# determinism=OK (two runs byte-identical)", file=sys.stderr)

    if args.verify_mutations:
        print("\n# --- Mutation verification ---", file=sys.stderr)
        all_caught = True
        for r in verify_mutations(baseline):
            status = "CAUGHT" if r["caught"] else "MISSED"
            err = f"  error={r.get('error','')}" if not r["caught"] else ""
            print(f"#  [{status}] {r['desc']} -> diverged_lines={r['diverged_lines']}{err}",
                  file=sys.stderr)
            all_caught = all_caught and r["caught"]
        print("# all mutations caught." if all_caught
              else "# WARNING: a mutation was not caught.", file=sys.stderr)
        sys.exit(0 if all_caught else 1)
