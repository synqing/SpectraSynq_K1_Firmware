#!/usr/bin/env python3
"""Golden-master oracle for the serial command -> output replay behaviour-lock.

Phase A · Lane 2 · S3.0 — the 24-pure-setter (actually 23, see below) replay lock
that gates ALL remaining serial_menu.h handler extractions (S4+). It compiles the
REAL `parse_command()` from SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h on the
host, drives it with a fixed deterministic corpus of pure-CONFIG-setter commands,
and captures a JSON-lines golden record that any refactor (S4 handler extraction)
must reproduce byte-for-byte.

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
      director/sb_smart_director.cpp  (sb_smart_director_* config getters/setters)
      director/sb_edgemixer_lite.cpp  (sb_edgemixer_lite_* config)
      director/sb_visual_hooks.cpp    (sb_visual_hooks_* config)
      director/sb_mode_selection.cpp  (sb_mode_selection_init)
      control/sb_effect_queue.cpp     (sb_queue_* config)
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
# (recon §2). None drag audio/I2S/FreeRTOS/RMT. NOTE: control/sb_effect_queue.cpp
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
    "director/sb_smart_director.cpp",
    "director/sb_edgemixer_lite.cpp",
    "director/sb_visual_hooks.cpp",
    "director/sb_mode_selection.cpp",
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
# exactly as it does in the shipped TU). SB_RENDER_HOST_TEST activates
# render_host_globals.cpp's host singletons. SB_SERIAL_REPLAY_HOST flips the
# Serial/USBSerial host sink from no-op to RECORDING (driver-local; does not touch
# the shared stubs, so the other 6 oracles stay byte-identical).
DEFINES = [
    "SB_K1_HARDWARE",          # production: USBSerial #define'd to Serial; pin map
    "SB_RENDER_HOST_TEST",     # render_host_globals host singletons
    "SB_SERIAL_REPLAY_HOST",   # driver-local: make Serial recording (text = golden)
    "SB_TEMPO_CONF_V2",
    "SB_TEMPO_FLYWHEEL_V2",
    "SB_ONSET_V2",
    "SB_CHORD_V2",
    "SB_SEMANTIC_STATE",
    "SB_CHORD_HUE_V1",
    "SB_DROP_CUT_V1",
    "SB_VIVID_PRECOMP_V1",
    "K1_LOUD_GUARD_V1",
    "DEFAULT_SAMPLE_RATE=12800",
    "DEFAULT_SAMPLES_PER_CHUNK=96",
    "SB_TEMPO_NOVELTY_DECIMATION=3U",
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

    # ---- (3) =default + malformed/bad_command: lock the failure path ----------
    "chroma=default",      # reads CONFIG_DEFAULTS.CHROMA
    "sensitivity=default", # reads CONFIG_DEFAULTS.SENSITIVITY
    "square_iter=default", # reads CONFIG_DEFAULTS.SQUARE_ITER
    "mirror_enabled=default",  # enum default branch
    "chroma=",             # empty -> vp_parse_float fails -> bad_command
    "photons=abc",         # non-numeric -> vp_parse_float fails -> bad_command
    "palette_mode=maybe",  # not a bool token -> bad_command
    "base_coat=default",   # base_coat has NO default token -> bad_command
    "unknown_cmd=1",       # unknown command_type -> bad_command
    "palette_index=9999",  # out of [0, gGradientPaletteCount) -> bad_command
]

# ---------------------------------------------------------------------------
# C++ driver.
#
# Drives the REAL parse_command (included from serial_menu.h) over the corpus,
# capturing the TRIPLE per command. Provides:
#   * a RECORDING serial sink (SB_SERIAL_REPLAY_HOST): a g_sb_replay_out string
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
// oracle_serial_replay_driver.cpp  (HOST-ONLY, -DSB_SERIAL_REPLAY_HOST)
// Drives the REAL parse_command() over the S3.0 pure-setter corpus and dumps the
// capture triple per command. Compiled by oracle_serial_replay.py — NOT shipped.

#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <string>
#include <cmath>

// The RECORDING serial sink lives in stubs/Arduino.h, gated by
// SB_SERIAL_REPLAY_HOST: under that flag HostSerial's print/println append to the
// shared inline accumulator g_sb_replay_out (declared there), formatted to match
// Arduino Print's contract. It must be ONE shared definition so every compiled TU
// records into the same buffer — the driver TU, AND serial_tx.cpp (tx_begin /
// tx_end / bad_command echo through USBSerial too). globals.h (under
// SB_K1_HARDWARE) does `#define USBSerial Serial`, and `HostSerial Serial`'s
// storage is defined once in render_host_globals.cpp.
#include "globals.h"   // brings parse_command's whole world (USBSerial #def -> Serial)
// g_sb_replay_out is declared inline in stubs/Arduino.h (via globals.h -> Arduino.h).

// Host stubs for the symbols serial_menu.h's WHOLE body references (FIRMWARE_VERSION,
// pgmspace shims, I2S_NUM_0, esp_reset_reason, the device handlers, the sb_queue_*
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
// (SBChannelPreset / SBAudioSnapshot), so they are DEFINED here, AFTER the header.
// All belong to handlers OUTSIDE the S3.0 corpus (noise-cal arm/disarm/confirm,
// preset slot save/get, queue arm/commit, the output probe, the audio snapshot
// read, the benchmark/FPS-stream globals). They only need to LINK; behaviour is
// irrelevant to the pure-setter golden. serial_menu.h forward-declares each, so
// these are the SOLE definitions (no ODR clash — the real TUs are not compiled).
// ---------------------------------------------------------------------------
// noise-cal arm FSM (control/sb_noise_cal_arm.cpp — not compiled)
void sb_noise_cal_arm() {}
void sb_noise_cal_disarm() {}
bool sb_noise_cal_confirm(uint32_t /*now_ms*/) { return false; }

// effect-queue surface beyond the config setters stubbed in the host-stub header
// (control/sb_effect_queue.cpp — not compiled; drags FS/LittleFS)
bool sb_queue_any_armed() { return false; }
SBChannelPreset* sb_queue_arm_begin(bool /*secondary*/) { return nullptr; }
void sb_queue_arm_preset(bool /*secondary*/, const SBChannelPreset& /*preset*/) {}
void sb_queue_request_commit(bool /*cued*/, uint32_t /*now_ms*/) {}
bool sb_queue_mode_enabled() { return false; }
uint8_t sb_queue_transition_style() { return 0; }
bool sb_preset_slot_save(uint8_t /*slot*/, bool /*from_secondary*/) { return false; }
bool sb_preset_slot_get(uint8_t /*slot*/, SBChannelPreset* /*out*/) { return false; }

// vp output probe (visual/lightshow_modes.h inline — header not pulled) + audio
// snapshot read (audio/sb_audio_snapshot.cpp — not compiled)
void vp_run_output_probe() {}
SBAudioSnapshot sb_audio_snapshot_read() { SBAudioSnapshot s = {}; return s; }

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

  FieldSnap before[64], after[64];

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
            target = fw_copy / "serial" / "serial_menu.h"
            original = target.read_text(encoding="utf-8")
            mutated = re.sub(pattern, replacement, original, count=1)
            if mutated == original:
                results.append({"desc": desc, "diverged_lines": 0, "caught": False,
                                "error": "regex did not match"})
                continue
            target.write_text(mutated, encoding="utf-8")
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
