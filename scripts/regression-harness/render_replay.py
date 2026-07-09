#!/usr/bin/env python3
"""Compile and run host-side render replays for a real K1 light mode (Tier 1 of
the VE-Auto-Loop). Generalises tempo_replay.py from k1_tempo.cpp to a real
light_mode_*.cpp + render_params.cpp.

WHAT IT DOES
  Host-compiles the REAL firmware render path (bloom + waveform + waveform_fast +
  spectrum_river + comet) against a curated Arduino/ESP/FastLED/FixedPoints stub
  set (scripts/regression-harness/stubs/), drives it with synthetic frames, and
  dumps the leds_16 working buffer per frame in the EXACT VPABBytesPayload byte
  LAYOUT (uint8 R,G,B x LED_COUNT_VALUE) so host (Tier 1) and device (vpab_capture,
  Tier 2) share one frame schema.

  Mode-specific wiring is DATA, not new code paths: each MODES entry carries the
  firmware sources it needs, a C++ decls fragment (extra host state/buffers), a
  per-frame `frame_apply` fragment (writes that mode's inputs into firmware
  globals), and an `entry` fragment (the per-frame call + any pre/post memcpy).
  CPP_REPLAY is assembled per mode from a common skeleton + these fragments.

RICH FIXTURE SCHEMA (single schema, every mode reads its subset)
  Each NDJSON frame may carry: ms (int), chromagram[12], spectrogram[80],
  waveform_peak_scaled (float), max_waveform_val_raw (float), bass_onset (0/1),
  bass_onset_strength (float), silence (bool). The Python stdin emitter writes a
  fixed-width, mode-aware line; the C++ parser reads exactly the fields the mode
  consumes. chromagram values are preserved BIT-IDENTICALLY when a fixture is
  enriched, so bloom's render is unchanged.

EPISTEMIC STATUS  [MECHANISM], NOT [MEASURED]
  The host reproduces the effect MATHS + motion memory only. The CRGB16->byte
  reduction here is a PRE-GAMMA / PRE-DITHER / PRE-INCANDESCENT linear quantise:
  byte LAYOUT matches the device (invariant I3) but VALUES differ from device by
  the gamma/incandescent/dither stack (led_utilities.h:324-387), which is Tier-2
  [MEASURED] territory by design (PRD 01 sec.11 / R-FASTLED). Host-vs-host
  determinism (acceptance A2) is the hard invariant and holds regardless.

HOST COMPILER = GCC (g++), not clang.
  The K1's vendored FixedPoints (SQ15x16 = SFixed<15,16>, R-FP: must NOT be
  float-substituted) declares `static constexpr SFixed` members of its own
  still-incomplete type; Apple clang rejects this, GCC (the firmware's xtensa-gcc
  lineage) accepts it. So this harness defaults to a g++ on PATH.

NO HARDWARE, NO BENCH, NO SOUND. Closes edit -> render -> capture autonomously.
NON-SHIPPING: -DK1_RENDER_HOST_TEST + the dump hook live only here.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
STUBS = ROOT / "scripts" / "regression-harness" / "stubs"
FIXEDPOINTS = ROOT / "libraries" / "FixedPoints" / "src"
HOST_GLOBALS = ROOT / "scripts" / "regression-harness" / "render_host_globals.cpp"

LED_COUNT = 160          # NATIVE_RESOLUTION / LED_COUNT_VALUE (constants.h:23 / config_types.h:52)
BYTE_COUNT = LED_COUNT * 3

# Firmware source subdirs (Phase 1 restructure 2026-06-03, docs/refactor/
# k1-firmware-restructure-and-rebrand-plan.md). Added to -I so bare #includes
# resolve regardless of subdir; also prefixed onto the compiled .cpp paths.
FW_SUBDIRS = ("audio", "visual", "effects", "director", "serial", "system",
              "persistence", "calibration", "diag")

# Common firmware sources every mode needs (render-param boundary + palette data
# + the Row-3 data TU). globals.cpp is the firmware's own hand-written data
# translation unit (Phase-B refactor 2026-06-03): it DEFINES the extern globals
# the render path ODR-uses — K1_PASS/K1_FAIL, chromagram_smooth, spectrogram_smooth,
# audio_vu_level*, chroma_val, hue_position, vp_render_secondary_channel,
# note_chromagram, palette_owns_colour_source — and includes ONLY FastLED +
# FixedPoints + config_types.h (NO audio/I2S/hardware tree, PRD R-GLOBAL). Compiling
# it (instead of hand-mirroring those defs in render_host_globals.cpp) tracks the
# firmware automatically and survives the K1_PASS/K1_FAIL macro→extern migration.
COMMON_SOURCES = ["visual/render_params.cpp", "visual/Palettes.cpp",
                  "system/globals.cpp"]

# Candidate host compilers, in preference order (GCC required — see module docstring).
GPP_CANDIDATES = ["g++-15", "g++-14", "g++-13", "g++-12", "g++"]


# ============================================================================
# MODE REGISTRY — per-mode C++ fragments + fixture-key declaration.
# ----------------------------------------------------------------------------
# Each entry:
#   sources       : firmware .cpp(s) compiled in addition to COMMON_SOURCES
#   fixture_keys  : the rich-fixture fields this mode consumes (doc/intent only)
#   decls         : C++ pasted at file scope (extra host buffers / per-mode state).
#                   Must define `static void mode_reset()` seeding all state.
#   frame_apply   : C++ pasted INSIDE the per-frame loop, BEFORE the entry call.
#                   Writes the parsed frame fields into the firmware globals this
#                   mode reads. `fr` is the in-scope parsed-frame struct.
#   entry         : C++ pasted INSIDE the per-frame loop — the actual mode call,
#                   including any pre/post memcpy the dispatch does on device.
#   silence_black : (optional) assert silence fixture -> all-black in self_test.
#                   Only bloom guarantees this (others hold a fading trail).
# ============================================================================
MODES = {
    "bloom": {
        "sources": ["effects/light_mode_bloom.cpp"],
        "fixture_keys": ["chromagram"],
        "silence_black": True,
        "decls": r"""
static CRGB16 g_leds_prev[NATIVE_RESOLUTION];
static void mode_reset() { std::memset(g_leds_prev, 0, sizeof(g_leds_prev)); }
""",
        "frame_apply": r"""
    for (int i = 0; i < 12; i++) chromagram_smooth[i] = SQ15x16(fr.chroma[i]);
""",
        "entry": r"""
    light_mode_bloom_fast(g_leds_prev);
""",
    },

    "waveform": {
        "sources": ["effects/light_mode_waveform.cpp"],
        "fixture_keys": ["chromagram", "waveform_peak_scaled"],
        "decls": r"""
static CRGB16   g_leds_prev[NATIVE_RESOLUTION];
static CRGB16   g_last_color = {0,0,0};
static float    g_wf_peak_last = 0.0f;
static float    g_wf_shift_accum = 0.0f;
static uint32_t g_wf_last_ms = 0;
static void mode_reset() {
  std::memset(g_leds_prev, 0, sizeof(g_leds_prev));
  g_last_color = CRGB16{0,0,0};
  g_wf_peak_last = 0.0f; g_wf_shift_accum = 0.0f; g_wf_last_ms = 0;
}
""",
        # waveform IGNORES leds_previous/shift_accum/last_frame_ms internally (always
        # shifts 1 LED). It reads chromagram_smooth + global waveform_peak_scaled
        # (+ audio_vu_level fallback, left 0). Dispatch does memcpy(leds_16,
        # leds_16_prev) BEFORE the call; we round-trip g_leds_prev for motion memory.
        "frame_apply": r"""
    for (int i = 0; i < 12; i++) chromagram_smooth[i] = SQ15x16(fr.chroma[i]);
    waveform_peak_scaled = fr.waveform_peak_scaled;
""",
        "entry": r"""
    std::memcpy(leds_16, g_leds_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_waveform(g_leds_prev, g_last_color, g_wf_peak_last, g_wf_shift_accum, g_wf_last_ms);
    std::memcpy(g_leds_prev, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
""",
    },

    "waveform_fast": {
        "sources": ["effects/light_mode_waveform_fast.cpp"],
        "fixture_keys": ["chromagram", "waveform_peak_scaled", "max_waveform_val_raw"],
        "decls": r"""
static CRGB16   g_leds_prev[NATIVE_RESOLUTION];
static CRGB16   g_last_color = {0,0,0};
static float    g_wf_peak_last = 0.0f;
static float    g_wf_shift_accum = 0.0f;
static uint32_t g_wf_last_ms = 0;
static void mode_reset() {
  std::memset(g_leds_prev, 0, sizeof(g_leds_prev));
  g_last_color = CRGB16{0,0,0};
  g_wf_peak_last = 0.0f; g_wf_shift_accum = 0.0f; g_wf_last_ms = 0;
}
""",
        # waveform_fast integrates VP_WAVEFORM_SHIFT_RATE*dt via millis()
        # (g_sb_host_millis is set per frame in the skeleton; frame 1 ms==0 warms up
        # last_frame_ms). Reads chromagram_smooth + global waveform_peak_scaled +
        # global max_waveform_val_raw (GATES the reactive dot — must be plausibly
        # nonzero or the trail stays blank). Dispatch memcpy before.
        "frame_apply": r"""
    for (int i = 0; i < 12; i++) chromagram_smooth[i] = SQ15x16(fr.chroma[i]);
    waveform_peak_scaled = fr.waveform_peak_scaled;
    max_waveform_val_raw = fr.max_waveform_val_raw;
""",
        "entry": r"""
    std::memcpy(leds_16, g_leds_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_waveform_fast(g_leds_prev, g_last_color, g_wf_peak_last, g_wf_shift_accum, g_wf_last_ms);
    std::memcpy(g_leds_prev, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
""",
    },

    "spectrum_river": {
        "sources": ["effects/light_mode_spectrum_river.cpp"],
        "fixture_keys": ["spectrogram"],
        "decls": r"""
static CRGB16 g_leds_prev[NATIVE_RESOLUTION];
static void mode_reset() { std::memset(g_leds_prev, 0, sizeof(g_leds_prev)); }
""",
        # spectrum_river's SOLE audio read is global spectrogram_smooth[NUM_FREQS].
        # It manages its own history (writes leds_prev_buffer at end) — NO pre-memcpy.
        "frame_apply": r"""
    for (int i = 0; i < NUM_FREQS; i++) spectrogram_smooth[i] = SQ15x16(fr.spectro[i]);
""",
        "entry": r"""
    light_mode_spectrum_river(g_leds_prev);
""",
    },

    "comet": {
        "sources": ["effects/light_mode_comet.cpp"],
        "fixture_keys": ["chromagram", "bass_onset", "bass_onset_strength"],
        # comet reads chromagram_smooth (via effect_palette_or_chroma_colour) + onset
        # via k1_onset_beat_read() (host-stubbed in render_host_globals.cpp returning
        # g_host_onset_event). effect_state_primary is inline-defined by globals.h.
        # Dispatch does memcpy(leds_16, leds_16_prev) BEFORE and the reverse AFTER.
        "decls": r"""
#include "k1_onset_beat.h"     // K1OnsetBeatEvent (lightshow_modes.h doesn't pull it)
extern K1OnsetBeatEvent g_host_onset_event;   // set per frame; the onset stub returns it
static CRGB16 g_leds_prev[NATIVE_RESOLUTION];
static void mode_reset() {
  std::memset(g_leds_prev, 0, sizeof(g_leds_prev));
  std::memset(&effect_state_primary, 0, sizeof(effect_state_primary));
  effect_state_primary.vu_dot_max_level = SQ15x16(0.01);
  std::memset(&g_host_onset_event, 0, sizeof(g_host_onset_event));
}
""",
        "frame_apply": r"""
    for (int i = 0; i < 12; i++) chromagram_smooth[i] = SQ15x16(fr.chroma[i]);
    if (fr.bass_onset) {
      g_host_onset_event.event_id += 1u;           // fresh edge => comet fires
      g_host_onset_event.event_ms = fr.ms;
      g_host_onset_event.bass_onset = true;
      g_host_onset_event.bass_onset_strength = fr.bass_onset_strength;
    } else {
      g_host_onset_event.bass_onset = false;       // same event_id => no fresh fire
    }
""",
        "entry": r"""
    std::memcpy(leds_16, g_leds_prev, sizeof(CRGB16) * NATIVE_RESOLUTION);
    light_mode_comet(effect_state_primary);
    std::memcpy(g_leds_prev, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
""",
    },
}

# --- Pivot 2026-06-03: BLOOM-ONLY gate (deploy + test bloom FIRST) -----------
# waveform / waveform_fast / spectrum_river / comet are fully implemented above
# and render deterministically on host, but they are PARKED on branch
# wip/ve-auto-loop-4modes (commit ba4abd1) per Captain's redirect to certify
# bloom before including other modes. Default behaviour remains bloom-only, but
# broad resolution sweeps can opt in to the parked host modes without editing this
# file again:
#
#   K1_RENDER_REPLAY_ALL_MODES=1 python3 scripts/regression-harness/render_replay.py ...
#
# The parked definitions above are still non-shipping host harness entries; this
# environment switch only affects the Python harness mode registry.
ALL_MODES = dict(MODES)
if os.environ.get("K1_RENDER_REPLAY_ALL_MODES") == "1":
    MODES = ALL_MODES
else:
    MODES = {"bloom": MODES["bloom"]}


# ============================================================================
# CPP_REPLAY skeleton — assembled per mode. {DECLS}/{FRAME_APPLY}/{ENTRY} are the
# mode-specific holes; {SECONDARY_*} holes are EMPTY for the default single-channel
# path (so the generated TU is byte-identical to the pre-dual harness and the
# committed champion/self-test shas are unchanged) and only filled when --dual is
# requested. The param-header parse + k1_render_host_dump are common.
# ----------------------------------------------------------------------------
# Per-frame stdin line (fixed width, mode-agnostic; modes read their subset):
#   F <ms> <c0..c11> <s0..s79> <wf_peak> <max_wf_raw> <bass_onset> <bass_strength> <silence>
#
# DUAL-CHANNEL (opt-in, --dual): the same one fixture drives BOTH LED channels per
# frame, mirroring the firmware's two-channel render (SPECTRASYNQ_K1_FIRMWARE.ino
# ~620-744). The PRIMARY mode renders into leds_16 first and is dumped as `R0 <hex>`;
# then leds_16 is snapshotted, build_secondary_render_params() is pushed,
# vp_render_secondary_channel is set true, the SECONDARY mode renders into leds_16
# from its OWN history buffer, that is dumped as `R1 <hex>`, and leds_16 + the params
# stack + the flag are restored. Single-channel (default) still emits one `R <hex>`.
#
# REVERSAL: both channels are dumped in render-index order (0..159). The harness
# does NOT reverse: the firmware reverses only at the 8-bit output stage when
# *_REVERSE_ORDER is set (led_utilities.h), and the top-channel reversal is a
# downstream viewer concern — keeping render order here makes the host bytes a
# clean pre-output [MECHANISM] capture for both channels.
# ============================================================================
_CPP_SKELETON = r"""
// render_replay_main.cpp  (HOST-ONLY, -DK1_RENDER_HOST_TEST)
// Generated by render_replay.py for mode: {MODE}{DUAL_MODE_COMMENT}. Drives a real
// K1 light mode with synthetic frames and dumps leds_16 as a pre-gamma [MECHANISM]
// byte reduction.
#include "lightshow_modes.h"   // light modes + render params + leds_16 + chromagram_smooth + NATIVE_RESOLUTION

#include <cstdio>
#include <cstring>
#include <cstdlib>

// ---- parsed-frame struct (the single rich schema; modes read their subset) ----
struct HostFrame {{
  unsigned int ms;
  float chroma[12];
  float spectro[NUM_FREQS];
  float waveform_peak_scaled;
  float max_waveform_val_raw;
  int   bass_onset;
  float bass_onset_strength;
  int   silence;
}};

// ---- primary mode decls (extra host buffers / per-mode state + mode_reset) ----
{DECLS}
// ---- secondary mode decls (DUAL only; EMPTY in single-channel) ----
// The secondary channel gets its OWN history buffer + its own per-mode state via a
// renamed copy of the mode's decls/reset (mode_reset_secondary). This mirrors the
// firmware's separate leds_16_prev_secondary / effect_state_secondary families.
{SECONDARY_DECLS}

// k1_render_host_dump: the device's canonical path is
//   leds_16 (CRGB16) -> quantise(gamma+incandescent+dither) -> CRGB -> bytes.
// The host deliberately does a PRE-gamma/dither LINEAR reduction (PRD 01 sec.11):
// clamp each SQ15x16 channel to [0,1], scale to 0..255 with rounding. Byte LAYOUT
// == VPABBytesPayload (I3); values are [MECHANISM], certified on-device (Tier 2).
static void k1_render_host_dump(unsigned char* out_bytes) {{
  for (int i = 0; i < NATIVE_RESOLUTION; i++) {{
    float ch[3] = {{ float(leds_16[i].r), float(leds_16[i].g), float(leds_16[i].b) }};
    for (int c = 0; c < 3; c++) {{
      float v = ch[c];
      if (v < 0.0f) v = 0.0f;
      if (v > 1.0f) v = 1.0f;
      int q = (int)(v * 255.0f + 0.5f);
      if (q < 0) q = 0; if (q > 255) q = 255;
      out_bytes[i * 3 + c] = (unsigned char)q;
    }}
  }}
}}

// Parse one 'F' frame line into HostFrame. Returns false if the line is not a frame.
static bool parse_frame(const char* line, HostFrame& fr) {{
  if (line[0] != 'F') return false;
  std::memset(&fr, 0, sizeof(fr));
  const char* p = line + 1;
  char* end = nullptr;
  fr.ms = (unsigned int)std::strtoul(p, &end, 10); p = end;
  for (int i = 0; i < 12; i++)        {{ fr.chroma[i]  = std::strtof(p, &end); p = end; }}
  for (int i = 0; i < NUM_FREQS; i++) {{ fr.spectro[i] = std::strtof(p, &end); p = end; }}
  fr.waveform_peak_scaled = std::strtof(p, &end); p = end;
  fr.max_waveform_val_raw = std::strtof(p, &end); p = end;
  fr.bass_onset           = (int)std::strtol(p, &end, 10); p = end;
  fr.bass_onset_strength  = std::strtof(p, &end); p = end;
  fr.silence              = (int)std::strtol(p, &end, 10); p = end;
  return true;
}}

int main(int /*argc*/, char** /*argv*/) {{
  // ---- stdin line 1: render params ----
  //   P <mood> <sat> <square_iter> <chroma> <palette_mode> <palette_index>
  //     <auto_shift> <hue_position> <chroma_val> <chromatic_mode>
  char line[4096];
  RenderParams rp;
  std::memset(&rp, 0, sizeof(rp));
  rp.MOOD = 0.5f; rp.SATURATION = 0.9f; rp.SQUARE_ITER = 1.0f; rp.CHROMA = 1.0f;
  rp.PALETTE_MODE_ENABLED = false; rp.PALETTE_INDEX = 0; rp.AUTO_COLOR_SHIFT = false;
  rp.INCANDESCENT_FILTER = 0.0f; rp.INCANDESCENT_MODE = false; rp.MIRROR_ENABLED = true;
  rp.SENSITIVITY = 1.0f; rp.SAMPLES_PER_CHUNK = 96;
  // PHOTONS is the firmware brightness scalar (CONFIG.PHOTONS -> RenderParams).
  // light_mode_waveform multiplies its colour by it; a zero default would render
  // waveform fully black. 1.0 == full brightness. bloom / waveform_fast /
  // spectrum_river / comet do not read PHOTONS, so this is byte-neutral to them.
  rp.PHOTONS = 1.0f;

  if (std::fgets(line, sizeof(line), stdin)) {{
    if (line[0] == 'P') {{
      float mood = 0.5f, sat = 0.9f, sq = 1.0f, chroma = 1.0f, hue_pos = 0.0f, chroma_v = 0.0f;
      int pal_mode = 0, pal_idx = 0, auto_shift = 0, chromatic = 1;
      std::sscanf(line + 1, "%f %f %f %f %d %d %d %f %f %d",
                  &mood, &sat, &sq, &chroma, &pal_mode, &pal_idx, &auto_shift,
                  &hue_pos, &chroma_v, &chromatic);
      rp.MOOD = mood; rp.SATURATION = sat; rp.SQUARE_ITER = sq; rp.CHROMA = chroma;
      rp.PALETTE_MODE_ENABLED = pal_mode != 0; rp.PALETTE_INDEX = (uint8_t)pal_idx;
      rp.AUTO_COLOR_SHIFT = auto_shift != 0;
      rp.hue_position = SQ15x16(hue_pos); rp.chroma_val = SQ15x16(chroma_v);
      rp.chromatic_mode = chromatic != 0;
      // colour-state globals the modes read directly (not via rp)
      hue_position = SQ15x16(hue_pos);
      chroma_val = SQ15x16(chroma_v);
      chromatic_mode = chromatic != 0;
      vp_render_secondary_channel = false;
    }}
  }}
  push_render_params(&rp);

  // ---- optional stdin line 2 (DUAL only): secondary param overrides ----
  //   S <photons> <chroma> <mood> <saturation> <incand_filter> <incand_mode>
  //     <auto_shift> <mirror> <palette_mode> <palette_index>
  // These write the firmware's SECONDARY_* inline globals so that the device's own
  // build_secondary_render_params() (NOT a host re-implementation) produces the
  // secondary RenderParams = (primary snapshot + the 9 SECONDARY_* overrides).
{SECONDARY_PARAM_PARSE}
  // Seed all per-mode state to a deterministic black/zero start.
  mode_reset();
{SECONDARY_RESET}

  unsigned char bytes[NATIVE_RESOLUTION * 3];
  unsigned long n = 0;
  HostFrame fr;

  // ---- stdin lines 2..N: frames ----
  while (std::fgets(line, sizeof(line), stdin)) {{
    if (line[0] == '\n' || line[0] == '\0') continue;
    if (!parse_frame(line, fr)) continue;
    g_sb_host_millis = fr.ms;

    // mode-specific: write this frame's inputs into the firmware globals it reads
{FRAME_APPLY}
    // mode-specific: the per-frame entry call (+ any pre/post memcpy)
{ENTRY}

    k1_render_host_dump(bytes);
    std::printf("{PRIMARY_TAG}");
    for (int i = 0; i < NATIVE_RESOLUTION * 3; i++) std::printf("%02x", bytes[i]);
    std::printf("\n");
{SECONDARY_FRAME_BLOCK}
    n++;
  }}
  std::printf("RENDER_DONE frames=%lu leds=%d\n", n, NATIVE_RESOLUTION);
  return 0;
}}
"""


# File-local identifiers a mode's decls/reset/entry may declare. For the SECONDARY
# channel the firmware keeps a parallel state family (leds_16_prev_secondary,
# effect_state_secondary, ...); on host we mirror that by renaming each per-mode
# identifier to a *_secondary copy so the two channels never share motion memory.
# Order matters: longer names first so substrings don't get partially rewritten.
# NOTE: g_host_onset_event is `extern` (render_host_globals.cpp). It is NOT in this
# map — comet-dual would need a secondary onset symbol there; bloom (the only
# enabled mode) declares only g_leds_prev + mode_reset, both file-local, so the
# rename is fully self-contained for the shipped deliverable.
_SECONDARY_RENAME = [
    ("effect_state_primary", "effect_state_secondary"),
    ("g_leds_prev", "g_leds_prev_secondary"),
    ("g_last_color", "g_last_color_secondary"),
    ("g_wf_peak_last", "g_wf_peak_last_secondary"),
    ("g_wf_shift_accum", "g_wf_shift_accum_secondary"),
    ("g_wf_last_ms", "g_wf_last_ms_secondary"),
    ("mode_reset", "mode_reset_secondary"),
]


def _rename_secondary(fragment):
    """Rewrite a mode's C++ fragment to its secondary-channel twin (own buffers/state).
    effect_state_primary -> effect_state_secondary tracks the firmware's per-channel
    ChannelEffectState; the g_* host buffers get a _secondary suffix."""
    for src, dst in _SECONDARY_RENAME:
        fragment = fragment.replace(src, dst)
    return fragment


# Per-frame DUAL block: snapshot leds_16 (primary render output, already dumped as
# R0), push secondary params (build_secondary_render_params == primary snapshot + 9
# SECONDARY_* overrides), flip vp_render_secondary_channel, render the SECONDARY mode
# into leds_16 from its OWN history, dump as R1, then restore leds_16 + pop params +
# clear the flag. Mirrors SPECTRASYNQ_K1_FIRMWARE.ino ~700-744 (sans device-only
# prism/edgemix/clip, which are out of the host [MECHANISM] reduction).
_DUAL_FRAME_BLOCK_TMPL = r"""    // ---- secondary channel (DUAL) ----
    {{
      // 1) snapshot the primary render so leds_16 can be restored afterwards
      static CRGB16 leds_16_snapshot[NATIVE_RESOLUTION];
      std::memcpy(leds_16_snapshot, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
      // 2) build + push the secondary params, flip the channel flag (device parity)
      RenderParams sp = build_secondary_render_params();
      push_render_params(&sp);
      vp_render_secondary_channel = true;
      // 3) render the secondary mode into leds_16 from its OWN history buffer
{SECONDARY_FRAME_APPLY}
{SECONDARY_ENTRY}
      // 4) dump leds_16 as the SECONDARY channel (render-index order; no reversal)
      k1_render_host_dump(bytes);
      std::printf("R1 ");
      for (int i = 0; i < NATIVE_RESOLUTION * 3; i++) std::printf("%02x", bytes[i]);
      std::printf("\n");
      // 5) restore: pop params, restore leds_16, clear the channel flag
      pop_render_params();
      std::memcpy(leds_16, leds_16_snapshot, sizeof(CRGB16) * NATIVE_RESOLUTION);
      vp_render_secondary_channel = false;
    }}
"""

# Secondary param-override parse (DUAL only). Writes the firmware SECONDARY_* inline
# globals; build_secondary_render_params() then consumes them on-device-identically.
_SECONDARY_PARAM_PARSE_TMPL = r"""  if (std::fgets(line, sizeof(line), stdin)) {{
    if (line[0] == 'S') {{
      float s_phot = 1.0f, s_chroma = 0.0f, s_mood = 0.05f, s_sat = 1.0f, s_inc = 0.5f;
      int s_inc_mode = 0, s_auto = 1, s_mirror = 1, s_pal_mode = 0, s_pal_idx = 0;
      std::sscanf(line + 1, "%f %f %f %f %f %d %d %d %d %d",
                  &s_phot, &s_chroma, &s_mood, &s_sat, &s_inc,
                  &s_inc_mode, &s_auto, &s_mirror, &s_pal_mode, &s_pal_idx);
      SECONDARY_PHOTONS             = s_phot;
      SECONDARY_CHROMA              = s_chroma;
      SECONDARY_MOOD                = s_mood;
      SECONDARY_SATURATION          = s_sat;
      SECONDARY_INCANDESCENT_FILTER = s_inc;
      SECONDARY_INCANDESCENT_MODE   = s_inc_mode != 0;
      SECONDARY_AUTO_COLOR_SHIFT    = s_auto != 0;
      SECONDARY_MIRROR_ENABLED      = s_mirror != 0;
      SECONDARY_PALETTE_MODE_ENABLED = s_pal_mode != 0;
      SECONDARY_PALETTE_INDEX       = (uint8_t)s_pal_idx;
    }}
  }}
"""


def _render_cpp(mode, secondary_mode=None):
    """Assemble the per-mode harness TU.

    secondary_mode is None  -> single-channel (default). Every {SECONDARY_*}/dual hole
    is empty and {PRIMARY_TAG}=='R ', so the generated C++ is byte-identical to the
    pre-dual harness (committed champion + --self-test shas unchanged).

    secondary_mode set -> DUAL: primary dumped as 'R0 ', secondary mode rendered into
    a parallel state family and dumped as 'R1 ' per frame."""
    spec = MODES[mode]
    if secondary_mode is None:
        return _CPP_SKELETON.format(
            MODE=mode,
            DUAL_MODE_COMMENT="",
            DECLS=spec["decls"],
            SECONDARY_DECLS="",
            SECONDARY_PARAM_PARSE="",
            SECONDARY_RESET="",
            FRAME_APPLY=spec["frame_apply"],
            ENTRY=spec["entry"],
            PRIMARY_TAG="R ",
            SECONDARY_FRAME_BLOCK="",
        )

    sec = MODES[secondary_mode]
    secondary_block = _DUAL_FRAME_BLOCK_TMPL.format(
        SECONDARY_FRAME_APPLY=_rename_secondary(sec["frame_apply"]),
        SECONDARY_ENTRY=_rename_secondary(sec["entry"]),
    )
    return _CPP_SKELETON.format(
        MODE=mode,
        DUAL_MODE_COMMENT=" + secondary: " + secondary_mode,
        DECLS=spec["decls"],
        SECONDARY_DECLS=_rename_secondary(sec["decls"]),
        SECONDARY_PARAM_PARSE=_SECONDARY_PARAM_PARSE_TMPL,
        SECONDARY_RESET="  mode_reset_secondary();\n",
        FRAME_APPLY=spec["frame_apply"],
        ENTRY=spec["entry"],
        PRIMARY_TAG="R0 ",
        SECONDARY_FRAME_BLOCK=secondary_block,
    )


def detect_compiler(explicit=None):
    if explicit:
        return explicit
    for cand in GPP_CANDIDATES:
        if shutil.which(cand):
            return cand
    return "g++"


def build_binary(workdir, mode="bloom", compiler=None, secondary_mode=None):
    """Write the harness main into workdir and compile the real firmware render
    path against the stub set. Returns (ok, binary_path, result_dict). Caller owns
    workdir so the binary can be reused across many replay runs (compile once).

    secondary_mode None -> single-channel (default, byte-identical to pre-dual).
    secondary_mode set  -> dual: also compile the secondary mode's sources."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    main_cpp = workdir / "render_replay_main.cpp"
    main_cpp.write_text(_render_cpp(mode, secondary_mode=secondary_mode), encoding="utf-8")
    binary = workdir / "render_replay"
    cc = detect_compiler(compiler)

    # Dedup mode sources: in DUAL with primary==secondary (e.g. bloom+bloom) the
    # mode .cpp must be compiled exactly once (ODR / duplicate-symbol).
    mode_sources = list(MODES[mode]["sources"])
    if secondary_mode is not None:
        for s in MODES[secondary_mode]["sources"]:
            if s not in mode_sources:
                mode_sources.append(s)

    sources = [str(FIRMWARE / s) for s in COMMON_SOURCES]
    sources += [str(FIRMWARE / s) for s in mode_sources]
    sources += [str(HOST_GLOBALS), str(main_cpp)]

    compile_cmd = [
        cc, "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-DK1_RENDER_HOST_TEST",
        # Lane item 2 (K1_PALETTE_ENERGY_EXCURSION_V1) measured mixed via the
        # coverage gate and is OFF in k1_hardware — keep host replay matched.
        # Re-add the -D here AND in platformio.ini together when re-tuning.
        # K1_PASS / K1_FAIL are now `extern const char[]` (declared in globals.h,
        # defined in globals.cpp which is compiled in COMMON_SOURCES) — no longer
        # macros, so the old serial string-header force-include is gone.
        "-I", str(STUBS),
        "-I", str(FIXEDPOINTS),
        "-I", str(FIRMWARE),
        *[arg for d in FW_SUBDIRS for arg in ("-I", str(FIRMWARE / d))],
        *sources,
        "-o", str(binary),
    ]
    r = subprocess.run(compile_cmd, cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ok = r.returncode == 0
    return ok, binary, {
        "ok": ok, "stage": "compile", "compiler": cc, "returncode": r.returncode,
        "stdout": r.stdout, "stderr": r.stderr, "workdir": str(workdir),
    }


def _params_line(params):
    p = params or {}
    return "P {mood} {sat} {sq} {chroma} {pal_mode} {pal_idx} {auto_shift} {hue} {chroma_v} {chromatic}\n".format(
        mood=p.get("mood", 0.5), sat=p.get("saturation", 0.9), sq=p.get("square_iter", 1.0),
        chroma=p.get("chroma", 1.0), pal_mode=int(p.get("palette_mode", False)),
        pal_idx=int(p.get("palette_index", 0)), auto_shift=int(p.get("auto_color_shift", False)),
        hue=p.get("hue_position", 0.0), chroma_v=p.get("chroma_val", 0.0),
        chromatic=int(p.get("chromatic_mode", True)),
    )


def _secondary_params_line(params):
    """Emit the secondary 'S' override line (DUAL only). Defaults mirror the firmware
    SECONDARY_* globals (globals.h ~669-683): photons 1.0, chroma 0.0, mood 0.05,
    sat 1.0, incand_filter 0.5, auto_color_shift on, mirror on."""
    p = params or {}
    return ("S {photons} {chroma} {mood} {sat} {inc} {inc_mode} "
            "{auto_shift} {mirror} {pal_mode} {pal_idx}\n").format(
        photons=p.get("photons", 1.0), chroma=p.get("chroma", 0.0),
        mood=p.get("mood", 0.05), sat=p.get("saturation", 1.0),
        inc=p.get("incandescent_filter", 0.5), inc_mode=int(p.get("incandescent_mode", False)),
        auto_shift=int(p.get("auto_color_shift", True)), mirror=int(p.get("mirror_enabled", True)),
        pal_mode=int(p.get("palette_mode", False)), pal_idx=int(p.get("palette_index", 0)),
    )


def _frames_to_stdin(frames):
    """Emit one fixed-width 'F' line per frame carrying the full rich schema. Modes
    read only their subset; absent fields default to 0 so the line is deterministic
    and mode-agnostic. chromagram values pass through unchanged (bloom-bit-stable)."""
    out = []
    for fr in frames:
        chroma = (list(fr.get("chromagram", [])) + [0.0] * 12)[:12]
        spectro = (list(fr.get("spectrogram", [])) + [0.0] * 80)[:80]
        ms = int(fr.get("ms", 0))
        wf_peak = float(fr.get("waveform_peak_scaled", 0.0))
        max_wf = float(fr.get("max_waveform_val_raw", 0.0))
        bass = int(bool(fr.get("bass_onset", 0)))
        bass_str = float(fr.get("bass_onset_strength", 0.0))
        sil = int(bool(fr.get("silence", False)))
        fields = [str(ms)]
        fields += ["{:.6f}".format(float(x)) for x in chroma]
        fields += ["{:.6f}".format(float(x)) for x in spectro]
        fields += ["{:.6f}".format(wf_peak), "{:.6f}".format(max_wf),
                   str(bass), "{:.6f}".format(bass_str), str(sil)]
        out.append("F " + " ".join(fields))
    return "\n".join(out) + "\n"


def replay_frames(binary, frames, params=None, dual=False, secondary_params=None):
    """Run the compiled harness, feeding the param header + frame lines on stdin.

    Single-channel (dual=False, default): emits 'P' + frames, parses 'R ' lines.
    Returns (ok, list_of_primary_hex, raw_result) — UNCHANGED contract.

    Dual (dual=True): also emits the secondary 'S' override line and parses the
    channel-tagged 'R0 '/'R1 ' lines. The raw_result carries 'secondary_hexes' (the
    R1 list); the returned hex list is the PRIMARY (R0) channel so the single-channel
    callers' shape is preserved. Per-frame the binary emits R0 then R1, so the two
    lists are frame-aligned."""
    text = _params_line(params)
    if dual:
        text += _secondary_params_line(secondary_params)
    text += _frames_to_stdin(frames)
    r = subprocess.run([str(binary)], cwd=ROOT, text=True, input=text,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    hexes = []
    sec_hexes = []
    for ln in r.stdout.splitlines():
        if dual:
            if ln.startswith("R0 "):
                hexes.append(ln[3:].strip())
            elif ln.startswith("R1 "):
                sec_hexes.append(ln[3:].strip())
        elif ln.startswith("R "):
            hexes.append(ln[2:].strip())
    return r.returncode == 0, hexes, {
        "ok": r.returncode == 0, "stage": "run", "returncode": r.returncode,
        "stderr": r.stderr, "secondary_hexes": sec_hexes,
    }


def load_fixture(path):
    """Load an NDJSON fixture: one frame object per line."""
    frames = []
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        frames.append(json.loads(ln))
    return frames


def run_replay(frames, params=None, mode="bloom", compiler=None, keep_dir=None,
               secondary_mode=None, secondary_params=None):
    """Compile + drive the harness over `frames`.

    Single-channel (secondary_mode None, default): the envelope is UNCHANGED — one
    `frames` list of primary bytes + `sha256_of_all_frames` over the primary channel.

    Dual (secondary_mode set): renders BOTH channels per frame. The envelope adds:
      channels=2, secondary_mode, secondary_frames (R1 byte records),
      sha256_primary / sha256_secondary (per-channel digests), and
      sha256_of_all_frames = sha256(primary ++ secondary) (whole-output digest).
    `frames` stays the PRIMARY channel so single-channel consumers are unaffected.

    Importable per-channel access: callers wanting raw hex can read
    res["frames"][i]["bytes"] (primary) and res["secondary_frames"][i]["bytes"]
    (secondary), or use run_replay_dual() for a (primary_hexes, secondary_hexes)
    tuple directly."""
    temp_owner = None
    if keep_dir:
        workdir = Path(keep_dir)
    else:
        temp_owner = tempfile.TemporaryDirectory()
        workdir = Path(temp_owner.name)
    dual = secondary_mode is not None
    try:
        ok, binary, comp = build_binary(workdir, mode=mode, compiler=compiler,
                                        secondary_mode=secondary_mode)
        if not ok:
            return comp
        run_ok, hexes, run_meta = replay_frames(binary, frames, params, dual=dual,
                                                secondary_params=secondary_params)
        digest = hashlib.sha256("".join(hexes).encode("ascii")).hexdigest()
        out_frames = [
            {"frame": i, "leds": LED_COUNT, "byte_count": BYTE_COUNT,
             "bytes": h, "render_us": 0, "schema": "VPABBytesPayload", "tier": "host"}
            for i, h in enumerate(hexes)
        ]
        if not dual:
            return {
                "ok": run_ok and len(hexes) == len(frames),
                "stage": "run", "mode": mode, "compiler": comp["compiler"],
                "frame_count": len(hexes), "expected_frames": len(frames),
                "sha256_of_all_frames": digest, "frames": out_frames,
                "returncode": run_meta["returncode"], "stderr": run_meta["stderr"],
                "workdir": str(workdir),
            }

        sec_hexes = run_meta.get("secondary_hexes", [])
        sec_frames = [
            {"frame": i, "channel": 1, "leds": LED_COUNT, "byte_count": BYTE_COUNT,
             "bytes": h, "render_us": 0, "schema": "VPABBytesPayload", "tier": "host"}
            for i, h in enumerate(sec_hexes)
        ]
        for f in out_frames:
            f["channel"] = 0
        sha_primary = digest
        sha_secondary = hashlib.sha256("".join(sec_hexes).encode("ascii")).hexdigest()
        sha_all = hashlib.sha256(("".join(hexes) + "".join(sec_hexes)).encode("ascii")).hexdigest()
        return {
            "ok": run_ok and len(hexes) == len(frames) and len(sec_hexes) == len(frames),
            "stage": "run", "mode": mode, "secondary_mode": secondary_mode,
            "channels": 2, "compiler": comp["compiler"],
            "frame_count": len(hexes), "secondary_frame_count": len(sec_hexes),
            "expected_frames": len(frames),
            "sha256_primary": sha_primary, "sha256_secondary": sha_secondary,
            "sha256_of_all_frames": sha_all,
            "frames": out_frames, "secondary_frames": sec_frames,
            "returncode": run_meta["returncode"], "stderr": run_meta["stderr"],
            "workdir": str(workdir),
        }
    finally:
        if temp_owner is not None:
            temp_owner.cleanup()


def run_replay_dual(frames, mode="bloom", secondary_mode="bloom", params=None,
                    secondary_params=None, compiler=None, keep_dir=None):
    """Importable dual-channel convenience wrapper. Returns
    (ok, primary_hexes, secondary_hexes, envelope). Each *_hexes is a list of
    per-frame 480-char hex strings (160 LEDs x RGB), render-index order, no reversal."""
    res = run_replay(frames, params=params, mode=mode, compiler=compiler,
                     keep_dir=keep_dir, secondary_mode=secondary_mode,
                     secondary_params=secondary_params)
    if res.get("channels") != 2:
        return False, [], [], res
    primary = [f["bytes"] for f in res.get("frames", [])]
    secondary = [f["bytes"] for f in res.get("secondary_frames", [])]
    return res.get("ok", False), primary, secondary, res


FIXTURE_DIR = ROOT / "scripts" / "regression-harness" / "fixtures"
DEFAULT_PARAMS = {"mood": 0.5, "saturation": 0.9, "square_iter": 1.0, "chroma": 1.0}


def _run_unit_test(compiler=None):
    """R-SCALE8: compile + run fastled_stub_test.cpp (scale8 / hsv2rgb / palette
    vs known FastLED 3.10.3 reference values)."""
    cc = detect_compiler(compiler)
    src = ROOT / "scripts" / "regression-harness" / "fastled_stub_test.cpp"
    with tempfile.TemporaryDirectory() as td:
        binary = Path(td) / "fl_test"
        c = subprocess.run([cc, "-std=c++17", "-O2", "-Wall", "-Wextra",
                            "-I", str(STUBS), str(src), "-o", str(binary)],
                           cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if c.returncode != 0:
            return False, "unit-test compile failed: " + c.stderr[:400]
        r = subprocess.run([str(binary)], cwd=ROOT, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ok = r.returncode == 0 and "FASTLED_STUB_TEST_OK" in r.stdout
        return ok, r.stdout.strip()


def _max_byte(sample):
    import binascii
    return max((max(binascii.unhexlify(f["bytes"])) for f in sample["frames"]), default=0)


def self_test(mode="bloom", compiler=None):
    """Per-mode A1-A5 gate + regression baseline. Returns (ok, report_lines).
      A2 determinism: 3 independent build+run -> identical sha per fixture.
      sanity: some non-silence fixture must NOT be all-identical frames (the effect
              actually moves). bloom additionally asserts silence -> all-black (its
              golden A4 anchor); other modes legitimately hold a fading trail.
    Emits the per-fixture sha256 baseline (champion-precursor)."""
    lines = []
    spec = MODES[mode]

    ut_ok, ut_msg = _run_unit_test(compiler)
    lines.append("R-SCALE8 unit test : %s  (%s)" % ("PASS" if ut_ok else "FAIL", ut_msg))
    if not ut_ok:
        return False, lines

    fixtures = sorted(FIXTURE_DIR.glob("*.ndjson"))
    if not fixtures:
        return False, lines + ["no fixtures found in %s" % FIXTURE_DIR]

    all_ok = True
    nonsilence_moved = False
    for fx in fixtures:
        frames = load_fixture(fx)
        # A2: determinism across 3 independent builds+runs
        shas, sample = set(), None
        for _ in range(3):
            res = run_replay(frames, params=DEFAULT_PARAMS, mode=mode, compiler=compiler)
            if not res.get("ok"):
                lines.append("%-22s BUILD/RUN FAIL: %s" % (fx.name, (res.get("stderr") or "")[:200]))
                all_ok = False
                break
            shas.add(res["sha256_of_all_frames"]); sample = res
        else:
            mx = _max_byte(sample)
            det = len(shas) == 1
            distinct = len({f["bytes"] for f in sample["frames"]})
            if fx.name != "silence.ndjson" and distinct > 1:
                nonsilence_moved = True
            all_ok = all_ok and det
            lines.append("%-22s frames=%-3d max_byte=%-3d distinct=%-3d det=%s sha=%s" % (
                fx.name, sample["frame_count"], mx, distinct,
                "OK" if det else "VARIED!", next(iter(shas))[:12]))

    # sanity: SOME non-silence fixture must visibly move (the effect renders motion)
    lines.append("sanity non-silence moves : %s" % ("PASS" if nonsilence_moved else "FAIL"))
    all_ok = all_ok and nonsilence_moved

    # mode-specific silence assertion
    sil = run_replay(load_fixture(FIXTURE_DIR / "silence.ndjson"),
                     params=DEFAULT_PARAMS, mode=mode, compiler=compiler)
    if not sil.get("ok"):
        lines.append("silence render : FAIL (%s)" % ((sil.get("stderr") or "")[:160]))
        all_ok = False
    elif spec.get("silence_black"):
        black = all(set(f["bytes"]) == {"0"} for f in sil["frames"])
        lines.append("A4 silence->all-black : %s" % ("PASS" if black else "FAIL"))
        all_ok = all_ok and black
    else:
        lines.append("silence render valid  : PASS (frames=%d, max_byte=%d) [trail may persist]"
                     % (sil["frame_count"], _max_byte(sil)))
    return all_ok, lines


# Two deliberately-distinct param sets so the dual self-test proves the two channels
# render DIFFERENT looks (not just two copies). Primary = bright/full chroma; secondary
# = the firmware's dim/low-mood defaults but forced to a different palette+saturation.
_DUAL_PRIMARY_PARAMS = {"mood": 0.9, "saturation": 0.9, "square_iter": 1.0, "chroma": 1.0}
_DUAL_SECONDARY_PARAMS = {"photons": 1.0, "chroma": 1.0, "mood": 0.05, "saturation": 0.4,
                          "incandescent_filter": 0.5, "auto_color_shift": True,
                          "palette_mode": False, "palette_index": 0}


def dual_self_test(mode="bloom", secondary_mode="bloom", compiler=None):
    """Dual-channel gate. For each fixture, 3 independent build+run must yield an
    identical per-channel sha (A2 determinism for BOTH R0 and R1), and at least one
    non-silence fixture must produce DISTINCT primary vs secondary channel hashes
    (proving the two param sets render two different looks, not duplicates).
    Emits the per-fixture per-channel sha baseline."""
    lines = []
    fixtures = sorted(FIXTURE_DIR.glob("*.ndjson"))
    if not fixtures:
        return False, ["no fixtures found in %s" % FIXTURE_DIR]

    all_ok = True
    saw_distinct_channels = False
    for fx in fixtures:
        frames = load_fixture(fx)
        p_shas, s_shas, sample = set(), set(), None
        for _ in range(3):
            ok, p_hex, s_hex, res = run_replay_dual(
                frames, mode=mode, secondary_mode=secondary_mode,
                params=_DUAL_PRIMARY_PARAMS, secondary_params=_DUAL_SECONDARY_PARAMS,
                compiler=compiler)
            if not ok:
                lines.append("%-22s BUILD/RUN FAIL: %s" % (fx.name, (res.get("stderr") or "")[:200]))
                all_ok = False
                break
            p_shas.add(res["sha256_primary"]); s_shas.add(res["sha256_secondary"]); sample = res
        else:
            p_det = len(p_shas) == 1
            s_det = len(s_shas) == 1
            distinct_ch = next(iter(p_shas)) != next(iter(s_shas))
            if fx.name != "silence.ndjson" and distinct_ch:
                saw_distinct_channels = True
            all_ok = all_ok and p_det and s_det
            lines.append("%-22s frames=%-3d/%-3d Pdet=%s Sdet=%s ch0!=ch1=%s P=%s S=%s" % (
                fx.name, sample["frame_count"], sample["secondary_frame_count"],
                "OK" if p_det else "VARIED!", "OK" if s_det else "VARIED!",
                "Y" if distinct_ch else "N",
                next(iter(p_shas))[:12], next(iter(s_shas))[:12]))

    lines.append("two distinct channel looks : %s" % ("PASS" if saw_distinct_channels else "FAIL"))
    all_ok = all_ok and saw_distinct_channels
    return all_ok, lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--compiler", default=None, help="host C++ compiler (default: first g++ on PATH)")
    ap.add_argument("--mode", default="bloom", choices=sorted(MODES.keys()))
    ap.add_argument("--frames", help="NDJSON fixture path (one frame object per line)")
    ap.add_argument("--keep-dir")
    ap.add_argument("--out", help="write per-frame NDJSON here (default stdout)")
    ap.add_argument("--json", action="store_true", help="emit the machine envelope")
    ap.add_argument("--self-test", action="store_true", help="run the per-mode A2 determinism + sanity check")
    ap.add_argument("--dual-self-test", action="store_true",
                    help="dual-channel A2: 3x identical per-channel sha + two DISTINCT channel hashes")
    # RenderParams sweep knobs (MVP-0 'edit' surface)
    ap.add_argument("--mood", type=float, default=0.5)
    ap.add_argument("--saturation", type=float, default=0.9)
    ap.add_argument("--square-iter", type=float, default=1.0)
    ap.add_argument("--chroma", type=float, default=1.0)
    ap.add_argument("--palette-mode", action="store_true")
    ap.add_argument("--palette-index", type=int, default=0)
    # --- DUAL-CHANNEL (opt-in). Default OFF -> single-channel output unchanged. ---
    ap.add_argument("--dual", action="store_true",
                    help="render BOTH LED channels per frame (R0=primary, R1=secondary)")
    ap.add_argument("--secondary-mode", default=None, choices=sorted(MODES.keys()),
                    help="secondary channel mode (implies --dual; default: same as --mode)")
    # Secondary RenderParams overrides -> firmware SECONDARY_* globals
    # (consumed by the device's own build_secondary_render_params()).
    ap.add_argument("--secondary-photons", type=float, default=1.0)
    ap.add_argument("--secondary-chroma", type=float, default=0.0)
    ap.add_argument("--secondary-mood", type=float, default=0.05)
    ap.add_argument("--secondary-saturation", type=float, default=1.0)
    ap.add_argument("--secondary-incandescent-filter", type=float, default=0.5)
    ap.add_argument("--secondary-incandescent-mode", action="store_true")
    ap.add_argument("--secondary-palette-mode", action="store_true")
    ap.add_argument("--secondary-palette-index", type=int, default=0)
    ap.add_argument("--secondary-no-auto-color-shift", action="store_true",
                    help="disable SECONDARY_AUTO_COLOR_SHIFT (default on, per firmware)")
    ap.add_argument("--secondary-no-mirror", action="store_true",
                    help="disable SECONDARY_MIRROR_ENABLED (default on, per firmware)")
    args = ap.parse_args(argv)

    # --dual or --secondary-mode either one turns dual on; secondary mode defaults
    # to the primary mode (bloom-only today: primary params vs secondary params).
    dual_on = args.dual or (args.secondary_mode is not None)
    secondary_mode = (args.secondary_mode or args.mode) if dual_on else None

    if args.self_test:
        ok, lines = self_test(mode=args.mode, compiler=args.compiler)
        print("=== self-test mode=%s ===" % args.mode)
        for ln in lines:
            print(ln)
        print("RENDER_REPLAY_OK" if ok else "RENDER_REPLAY_FAIL")
        return 0 if ok else 1

    if args.dual_self_test:
        ok, lines = dual_self_test(mode=args.mode, secondary_mode=secondary_mode or args.mode,
                                   compiler=args.compiler)
        print("=== dual-self-test primary=%s secondary=%s ===" % (args.mode, secondary_mode or args.mode))
        for ln in lines:
            print(ln)
        print("RENDER_REPLAY_OK" if ok else "RENDER_REPLAY_FAIL")
        return 0 if ok else 1

    if not args.frames:
        ap.error("--frames is required (or use --self-test / --dual-self-test)")

    params = {
        "mood": args.mood, "saturation": args.saturation, "square_iter": args.square_iter,
        "chroma": args.chroma, "palette_mode": args.palette_mode, "palette_index": args.palette_index,
    }
    secondary_params = {
        "photons": args.secondary_photons, "chroma": args.secondary_chroma,
        "mood": args.secondary_mood, "saturation": args.secondary_saturation,
        "incandescent_filter": args.secondary_incandescent_filter,
        "incandescent_mode": args.secondary_incandescent_mode,
        "palette_mode": args.secondary_palette_mode, "palette_index": args.secondary_palette_index,
        "auto_color_shift": not args.secondary_no_auto_color_shift,
        "mirror_enabled": not args.secondary_no_mirror,
    }
    frames = load_fixture(args.frames)
    res = run_replay(frames, params=params, mode=args.mode,
                     compiler=args.compiler, keep_dir=args.keep_dir,
                     secondary_mode=secondary_mode, secondary_params=secondary_params)

    if args.json or not res.get("ok"):
        # On failure, surface the compile/run diagnostics (tempo_replay contract).
        # In dual, drop both per-channel frame lists from the envelope summary.
        envelope = {k: v for k, v in res.items() if k not in ("frames", "secondary_frames")}
        print(json.dumps(envelope, indent=2, sort_keys=True))
        if not res.get("ok"):
            return res.get("returncode") or 1
        return 0

    # NDJSON output: single-channel emits the primary frames (unchanged). Dual emits
    # both channels interleaved per frame (each record carries {channel:0|1}).
    if res.get("channels") == 2:
        out_records = []
        for pf, sf in zip(res["frames"], res["secondary_frames"]):
            out_records.append(pf)
            out_records.append(sf)
        lines = "\n".join(json.dumps(f, sort_keys=True) for f in out_records)
        summary = "wrote %d frames x2 channels -> %s (primary=%s secondary=%s all=%s)" % (
            res["frame_count"], args.out or "stdout",
            res["sha256_primary"][:12], res["sha256_secondary"][:12],
            res["sha256_of_all_frames"][:12])
    else:
        lines = "\n".join(json.dumps(f, sort_keys=True) for f in res["frames"])
        summary = "wrote %d frames -> %s (sha256=%s)" % (
            res["frame_count"], args.out, res["sha256_of_all_frames"][:12])

    if args.out:
        Path(args.out).write_text(lines + "\n", encoding="utf-8")
        print(summary)
    else:
        print(lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
