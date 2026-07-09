#!/usr/bin/env python3
"""Golden-master oracle for k1_smart_director — effect-routing / mode-selection logic.

Pattern mirrors oracle_onset_beat.py.  capture() compiles k1_smart_director.cpp
against the same stubs as smart_director_replay.py, drives a fixed deterministic
sequence of K1AudioSnapshot inputs through k1_smart_director_tick(), and emits
one JSON record per step covering every public output field.

MUTATIONS: four real constants from distinct routing mechanisms, each proven to
diverge the selected-mode sequence when changed.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

NAME = "smart_director"

MODULE_CPPS = ["SPECTRASYNQ_K1_FIRMWARE/director/k1_smart_director.cpp"]

# Matches production k1_hardware build_flags (no K1_ONSET_V2 so K1OnsetBeatEvent
# uses the base struct path only; -O0 for determinism).
DEFINES = [
    "K1_SEMANTIC_STATE",
    "K1_TEMPO_CONF_V2",
    "K1_TEMPO_FLYWHEEL_V2",
    "K1_CHORD_V2",
]

# ---------------------------------------------------------------------------
# Stubs — identical to smart_director_replay.py so the compilation environment
# is the same ground truth.
# ---------------------------------------------------------------------------

ARDUINO_STUB = r"""
#pragma once
#include <math.h>
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""

CONFIG_TYPES_STUB = r"""
#pragma once
#include <stdint.h>

enum lightshow_modes {
  LIGHT_MODE_GDFT,
  LIGHT_MODE_GDFT_CHROMAGRAM,
  LIGHT_MODE_GDFT_CHROMAGRAM_DOTS,
  LIGHT_MODE_BLOOM,
  LIGHT_MODE_VU_DOT,
  LIGHT_MODE_KALEIDOSCOPE,
  LIGHT_MODE_QUANTUM_COLLAPSE,
  LIGHT_MODE_WAVEFORM_FAST,
  LIGHT_MODE_WAVEFORM,
  LIGHT_MODE_BLOOM_FAST,
  LIGHT_MODE_VU,
  LIGHT_MODE_WAVEFORM_HYBRID,
  LIGHT_MODE_COMET,
  LIGHT_MODE_SPECTRUM_RIVER,
  LIGHT_MODE_SPECTRUM_RIVER_V2,
  LIGHT_MODE_EMBER,
  LIGHT_MODE_EMBER_V2,
  LIGHT_MODE_WAVEFORM_TEMPO,
  LIGHT_MODE_TEMPO_RIVER,
  LIGHT_MODE_TEMPO_COMET,
  LIGHT_MODE_DENSE_FORGE,
  LIGHT_MODE_SNAPWAVE,
  LIGHT_MODE_PULSE_PRISM,
  NUM_MODES
};
"""

AUDIO_SNAPSHOT_STUB = r"""
#pragma once
#include <stdint.h>

enum K1MusicState : uint8_t {
  K1_MUSIC_SILENCE = 0,
  K1_MUSIC_AMBIENT,
  K1_MUSIC_STEADY,
  K1_MUSIC_BUILD,
  K1_MUSIC_DROP,
  K1_MUSIC_BREAKDOWN,
  K1_MUSIC_DENSE
};

struct K1AudioSnapshot {
  uint32_t frame_ms;
  float peak_scaled;
  float vu_level;
  float novelty;
  float spectral_energy;
  float low_energy;
  float mid_energy;
  float high_energy;
  float chroma_strength;
  bool silence;
};

struct K1OnsetBeatEvent {
  uint32_t event_id;
  uint32_t event_ms;
  uint32_t event_age_ms;
  float onset_strength;
  float bass_onset_strength;
  float beat_phase;
  float beat_confidence;
  bool onset;
  bool bass_onset;
  bool beat;
};
"""

MODE_SELECTION_STUB = r"""
#pragma once
#include <stdint.h>
#include "config_types.h"

enum K1ModeIntentReason : uint8_t {
  K1_MODE_REASON_HOLD = 0,
  K1_MODE_REASON_SILENCE,
  K1_MODE_REASON_AMBIENT,
  K1_MODE_REASON_STEADY,
  K1_MODE_REASON_BUILD,
  K1_MODE_REASON_DROP,
  K1_MODE_REASON_BREAKDOWN,
  K1_MODE_REASON_DENSE,
  K1_MODE_REASON_MANUAL_OWNERSHIP,
  K1_MODE_REASON_COOLDOWN,
  K1_MODE_REASON_DENIED
};

struct K1ModeIntent {
  uint8_t requested_mode;
  K1ModeIntentReason reason;
  float confidence;
  bool wants_switch;
};

struct K1ModeSelectionConfig {
  bool enabled;
  bool manual_owner_active;
  uint32_t min_dwell_ms;
  uint32_t cooldown_ms;
  uint32_t switch_window_ms;
  uint8_t max_switches_per_window;
};
"""

RENDER_PARAMS_STUB = r"""
#pragma once
#include <stdint.h>

struct RenderParams {
  float PHOTONS;
  float CHROMA;
  float MOOD;
  float SATURATION;
  bool PALETTE_MODE_ENABLED;
  uint8_t PALETTE_INDEX;
  bool AUTO_COLOR_SHIFT;
};
"""

SMART_DIRECTOR_HEADER_STUB = r"""
#pragma once

#include "render_params.h"
#include "k1_audio_snapshot.h"
#include "k1_mode_selection.h"

struct K1SmartDirectorConfig {
  bool enabled;
  bool assist_switching_enabled;
  bool director_autonomy_enabled;
  float confidence_floor;
  uint32_t min_dwell_ms;
  uint32_t cooldown_ms;
  uint32_t switch_window_ms;
  uint8_t max_switches_per_window;
};

struct K1SmartDirectorOutput {
  K1MusicState state;
  K1ModeIntent mode_intent;
  float speed_scalar;
  float photons_scalar;
  float chroma_scalar;
  float saturation_scalar;
  bool palette_overlay_enabled;
  uint8_t palette_index;
  bool auto_colour_shift;
};

enum K1SmartManualControlReason : uint8_t {
  K1_MANUAL_REASON_NONE = 0,
  K1_MANUAL_REASON_SERIAL_HOTKEY,
  K1_MANUAL_REASON_SERIAL_COMMAND,
  K1_MANUAL_REASON_ENCODER
};

void k1_smart_director_init();
K1SmartDirectorOutput k1_smart_director_tick(
  const K1AudioSnapshot& audio,
  uint32_t now_ms,
  const K1OnsetBeatEvent* event = nullptr
);
K1SmartDirectorOutput k1_smart_director_read_output();
void k1_smart_director_apply_render_params(const K1SmartDirectorOutput& output, RenderParams* params);
K1SmartDirectorConfig k1_smart_director_config();
void k1_smart_director_set_config(const K1SmartDirectorConfig& config);
K1ModeSelectionConfig k1_smart_director_mode_selection_config(uint32_t now_ms);
void k1_smart_director_mark_manual_control(uint32_t now_ms, K1SmartManualControlReason reason);
void k1_smart_director_clear_manual_control();
bool k1_smart_director_manual_owner_active(uint32_t now_ms);
"""

GLOBALS_STUB = r"""
#pragma once
#include <stdint.h>
extern bool mode_transition_queued;
extern int mode_destination;
extern uint32_t g_last_encoder_activity_time;
"""

# ---------------------------------------------------------------------------
# C++ oracle driver
#
# Design: we drive a FIXED deterministic sequence of K1AudioSnapshot states
# spaced at dt=500ms (so alpha smoothing is non-trivial but bounded).  The
# sequence is chosen to cross every major routing boundary:
#
#   Phase 0: silence (2 frames)            → K1_MUSIC_SILENCE
#   Phase 1: quiet ambient (3 frames)      → K1_MUSIC_AMBIENT (low spectral+novelty)
#   Phase 2: energy ramp build (4 frames)  → K1_MUSIC_BUILD (energy_delta>0.035, novelty>0.18)
#   Phase 3: drop burst (3 frames)         → K1_MUSIC_DROP (novelty>0.45, peak>0.55)
#   Phase 4: breakdown decay (3 frames)    → K1_MUSIC_BREAKDOWN (energy_delta<-0.04, spectral<0.22)
#   Phase 5: dense wall (3 frames)         → K1_MUSIC_DENSE (spectral>0.42, all bands >thresholds)
#   Phase 6: steady (2 frames)             → K1_MUSIC_STEADY
#
# The assist+autonomy config is enabled (switching=true, autonomy=true),
# confidence_floor=0.08, min_dwell=0ms (so routing responds immediately),
# cooldown=0ms, switch_window_ms=0xFFFFFFFF, max_switches=255.
# This maximises sensitivity: every state transition immediately yields a
# wants_switch=true output, so the selected-mode sequence is directly
# observable and highly sensitive to routing thresholds.
#
# Each step emits one JSON record containing every public K1SmartDirectorOutput
# field plus the smoothed internal state predictors (confidence).
# ---------------------------------------------------------------------------

DRIVER = r"""
#include "k1_smart_director.h"

#include <cmath>
#include <cstdio>
#include <cstring>

bool mode_transition_queued = false;
int mode_destination = -1;
uint32_t g_last_encoder_activity_time = 0;

// Deterministic config: enabled, switching, autonomy, low floor, zero dwell/cooldown.
static K1SmartDirectorConfig make_config() {
  K1SmartDirectorConfig c = {};
  c.enabled = true;
  c.assist_switching_enabled = true;
  c.director_autonomy_enabled = true;
  c.confidence_floor = 0.08f;
  c.min_dwell_ms = 0;
  c.cooldown_ms = 0;
  c.switch_window_ms = 0xFFFFFFFFU;
  c.max_switches_per_window = 255;
  return c;
}

// Build one K1AudioSnapshot from flat parameters.
static K1AudioSnapshot make_audio(uint32_t ms, float spectral, float novelty,
                                  float peak, float low, float mid, float high,
                                  bool silence) {
  K1AudioSnapshot a = {};
  a.frame_ms = ms;
  a.spectral_energy = spectral;
  a.novelty = novelty;
  a.peak_scaled = peak;
  a.low_energy = low;
  a.mid_energy = mid;
  a.high_energy = high;
  a.silence = silence;
  return a;
}

// Emit one JSON line for the output record.
static void emit(int step, const K1SmartDirectorOutput& out) {
  std::printf(
    "{"
    "\"step\":%d,"
    "\"state\":%d,"
    "\"requested_mode\":%d,"
    "\"reason\":%d,"
    "\"confidence\":%.5f,"
    "\"wants_switch\":%s,"
    "\"speed_scalar\":%.5f,"
    "\"photons_scalar\":%.5f,"
    "\"chroma_scalar\":%.5f,"
    "\"saturation_scalar\":%.5f,"
    "\"palette_overlay_enabled\":%s,"
    "\"palette_index\":%d,"
    "\"auto_colour_shift\":%s"
    "}\n",
    step,
    (int)out.state,
    (int)out.mode_intent.requested_mode,
    (int)out.mode_intent.reason,
    (double)out.mode_intent.confidence,
    out.mode_intent.wants_switch ? "true" : "false",
    (double)out.speed_scalar,
    (double)out.photons_scalar,
    (double)out.chroma_scalar,
    (double)out.saturation_scalar,
    out.palette_overlay_enabled ? "true" : "false",
    (int)out.palette_index,
    out.auto_colour_shift ? "true" : "false"
  );
}

int main() {
  k1_smart_director_init();
  k1_smart_director_set_config(make_config());

  // Fixed time step: 500 ms between frames.  Large enough that alpha smoothing
  // (tau=180ms) converges rapidly; small enough that we can steer transitions
  // frame-by-frame.
  const uint32_t DT = 500;
  int step = 0;
  uint32_t now = DT;  // start at DT to avoid dt_ms==0 on first tick

  // ------------------------------------------------------------------
  // Phase 0: silence (2 frames)
  // Crossing: K1_MUSIC_SILENCE via audio.silence=true
  // ------------------------------------------------------------------
  for (int i = 0; i < 2; ++i, ++step, now += DT) {
    K1AudioSnapshot a = make_audio(now, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, true);
    emit(step, k1_smart_director_tick(a, now));
  }

  // ------------------------------------------------------------------
  // Phase 1: quiet ambient (3 frames)
  // Crossing: K1_MUSIC_AMBIENT via spectral_energy<0.08 && novelty<0.08
  // After silence drains, energy_smooth converges toward 0.04 quickly.
  // ------------------------------------------------------------------
  for (int i = 0; i < 3; ++i, ++step, now += DT) {
    K1AudioSnapshot a = make_audio(now, 0.04f, 0.03f, 0.05f, 0.01f, 0.01f, 0.01f, false);
    emit(step, k1_smart_director_tick(a, now));
  }

  // ------------------------------------------------------------------
  // Phase 2: energy ramp — build (4 frames)
  // Crossing: K1_MUSIC_BUILD via energy_delta>0.035 && novelty>0.18
  // We jump spectral_energy from 0.04 to 0.30 so delta exceeds 0.035
  // within one frame after smoothing has partially caught up.
  // ------------------------------------------------------------------
  for (int i = 0; i < 4; ++i, ++step, now += DT) {
    float e = 0.30f + (float)i * 0.05f;   // 0.30, 0.35, 0.40, 0.45
    K1AudioSnapshot a = make_audio(now, e, 0.35f, 0.40f, 0.12f, 0.14f, 0.10f, false);
    emit(step, k1_smart_director_tick(a, now));
  }

  // ------------------------------------------------------------------
  // Phase 3: drop burst (3 frames)
  // Crossing: K1_MUSIC_DROP via novelty>0.45 && peak_scaled>0.55
  // ------------------------------------------------------------------
  for (int i = 0; i < 3; ++i, ++step, now += DT) {
    K1AudioSnapshot a = make_audio(now, 0.60f, 0.60f, 0.75f, 0.30f, 0.28f, 0.20f, false);
    emit(step, k1_smart_director_tick(a, now));
  }

  // ------------------------------------------------------------------
  // Phase 4: breakdown decay (3 frames)
  // Crossing: K1_MUSIC_BREAKDOWN via energy_delta<-0.04 && spectral<0.22
  // After the 0.60 drop, we cut to 0.12; delta will be strongly negative.
  // ------------------------------------------------------------------
  for (int i = 0; i < 3; ++i, ++step, now += DT) {
    K1AudioSnapshot a = make_audio(now, 0.12f, 0.10f, 0.15f, 0.04f, 0.04f, 0.03f, false);
    emit(step, k1_smart_director_tick(a, now));
  }

  // ------------------------------------------------------------------
  // Phase 5: dense wall (3 frames)
  // Crossing: K1_MUSIC_DENSE via spectral>0.42 && low>0.18 && mid>0.18 && high>0.12
  // ------------------------------------------------------------------
  for (int i = 0; i < 3; ++i, ++step, now += DT) {
    K1AudioSnapshot a = make_audio(now, 0.70f, 0.20f, 0.55f, 0.25f, 0.25f, 0.20f, false);
    emit(step, k1_smart_director_tick(a, now));
  }

  // ------------------------------------------------------------------
  // Phase 6: steady (2 frames)
  // Falls through all classifiers → K1_MUSIC_STEADY
  // ------------------------------------------------------------------
  for (int i = 0; i < 2; ++i, ++step, now += DT) {
    K1AudioSnapshot a = make_audio(now, 0.20f, 0.15f, 0.25f, 0.07f, 0.08f, 0.06f, false);
    emit(step, k1_smart_director_tick(a, now));
  }

  return 0;
}
"""


# ---------------------------------------------------------------------------
# Mutations — each targets a distinct routing mechanism.
# All use regex replace on the copied k1_smart_director.cpp.
# Each is in the direction that CHANGES routing (flips classified state or
# mode selection in the input sequence above).
# ---------------------------------------------------------------------------

MUTATIONS: list[tuple[str, str, str]] = [
    # 1. DROP novelty threshold (k1_classify_audio): raise 0.45 → 0.65
    #    Effect: Phase 3 frames (novelty=0.60) no longer cross DROP, fall to
    #    BUILD/STEADY instead → different requested_mode sequence.
    (
        r"audio\.novelty > 0\.45f && audio\.peak_scaled > 0\.55f",
        "audio.novelty > 0.65f && audio.peak_scaled > 0.55f",
        "DROP novelty threshold 0.45→0.65 (classify_audio): Phase-3 drops become STEADY/BUILD",
    ),
    # 2. BUILD energy_delta threshold (k1_classify_audio): raise 0.035 → 0.20
    #    Effect: Phase 2 energy ramp (delta ~0.07–0.10 after smoothing) no
    #    longer crosses BUILD → frames fall to AMBIENT/STEADY instead.
    (
        r"energy_delta > 0\.035f && audio\.novelty > 0\.18f",
        "energy_delta > 0.20f && audio.novelty > 0.18f",
        "BUILD energy_delta threshold 0.035→0.20 (classify_audio): Phase-2 ramp stays AMBIENT/STEADY",
    ),
    # 3. DENSE spectral threshold (k1_classify_audio): raise 0.42 → 0.80
    #    Effect: Phase 5 frames (spectral=0.70) no longer cross DENSE, fall
    #    to STEADY → LIGHT_MODE_SPECTRUM_RIVER instead of DENSE_FORGE.
    (
        r"audio\.spectral_energy > 0\.42f && audio\.low_energy > 0\.18f",
        "audio.spectral_energy > 0.80f && audio.low_energy > 0.18f",
        "DENSE spectral threshold 0.42→0.80 (classify_audio): Phase-5 dense wall becomes STEADY",
    ),
    # 4. DROP photons_scalar (k1_set_scalars_for_state): change 1.24 → 0.50
    #    Effect: during Phase 3 (K1_MUSIC_DROP), photons_scalar in every
    #    emitted record changes from 1.24000 to 0.50000 — direct scalar drift.
    (
        r"(case K1_MUSIC_DROP:[\s\S]*?speed_scalar = 1\.28f;\s*output->photons_scalar = )1\.24f",
        r"\g<1>0.50f",
        "DROP photons_scalar 1.24→0.50 (set_scalars_for_state): Phase-3 brightness field changes",
    ),
]


# ---------------------------------------------------------------------------
# Core compile+run helper (mirrors smart_director_replay.py's run_replay)
# ---------------------------------------------------------------------------

def _compile_and_run(
    source_cpp: Path,
    workdir: Path,
    compiler: str = "clang++",
    extra_defines: list[str] | None = None,
) -> dict:
    """Compile source_cpp (already copied to workdir) and run the binary.

    Returns dict with keys: ok, stage, stdout, stderr, returncode.
    """
    # Write all stubs
    (workdir / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
    (workdir / "config_types.h").write_text(CONFIG_TYPES_STUB, encoding="utf-8")
    (workdir / "k1_audio_snapshot.h").write_text(AUDIO_SNAPSHOT_STUB, encoding="utf-8")
    (workdir / "k1_mode_selection.h").write_text(MODE_SELECTION_STUB, encoding="utf-8")
    (workdir / "render_params.h").write_text(RENDER_PARAMS_STUB, encoding="utf-8")
    (workdir / "k1_smart_director.h").write_text(SMART_DIRECTOR_HEADER_STUB, encoding="utf-8")
    (workdir / "globals.h").write_text(GLOBALS_STUB, encoding="utf-8")

    driver_cpp = workdir / "oracle_driver.cpp"
    driver_cpp.write_text(DRIVER, encoding="utf-8")

    binary = workdir / "oracle_smart_director"

    define_flags: list[str] = []
    for d in (extra_defines or []):
        define_flags += ["-D", d]
    for d in DEFINES:
        define_flags += ["-D", d]

    compile_cmd = [
        compiler,
        "-std=c++17",
        "-O0",           # determinism: no reordering / CSE
        "-I", str(workdir),
        *define_flags,
        str(source_cpp),
        str(driver_cpp),
        "-o", str(binary),
    ]

    cr = subprocess.run(
        compile_cmd,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if cr.returncode != 0:
        return {
            "ok": False,
            "stage": "compile",
            "returncode": cr.returncode,
            "stdout": cr.stdout,
            "stderr": cr.stderr,
        }

    rr = subprocess.run(
        [str(binary)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return {
        "ok": rr.returncode == 0,
        "stage": "run",
        "returncode": rr.returncode,
        "stdout": rr.stdout,
        "stderr": rr.stderr,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def capture(compiler: str = "clang++") -> str:
    """Compile and run the oracle driver; return newline-delimited JSON records.

    Determinism contract: two successive calls must return byte-identical output.
    """
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        source_cpp = workdir / "k1_smart_director.cpp"
        shutil.copy2(next(FIRMWARE.rglob("k1_smart_director.cpp")), source_cpp)

        result = _compile_and_run(source_cpp, workdir, compiler)
        if not result["ok"]:
            raise RuntimeError(
                f"oracle_smart_director capture failed at stage={result['stage']} "
                f"rc={result['returncode']}\n"
                f"stderr: {result['stderr']}\nstdout: {result['stdout']}"
            )
        return result["stdout"].rstrip("\n")


def verify_mutations(
    baseline: str,
    compiler: str = "clang++",
    verbose: bool = False,
) -> list[dict]:
    """Apply each mutation in turn, recompile, and confirm divergence from baseline.

    Returns a list of result dicts:
      {desc, diverged, diverged_lines, error}
    where diverged_lines is the count of output lines that differ.
    """
    results = []
    firmware_src = next(FIRMWARE.rglob("k1_smart_director.cpp"))
    original_text = firmware_src.read_text(encoding="utf-8")

    for pattern, replacement, desc in MUTATIONS:
        mutated_text = re.sub(pattern, replacement, original_text, count=1)
        if mutated_text == original_text:
            results.append({
                "desc": desc,
                "diverged": False,
                "diverged_lines": 0,
                "error": "regex did not match — mutation not applied",
            })
            continue

        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            source_cpp = workdir / "k1_smart_director.cpp"
            source_cpp.write_text(mutated_text, encoding="utf-8")

            result = _compile_and_run(source_cpp, workdir, compiler)

        if not result["ok"]:
            results.append({
                "desc": desc,
                "diverged": False,
                "diverged_lines": 0,
                "error": (
                    f"compile/run failed rc={result['returncode']} "
                    f"stderr={result['stderr'][:300]}"
                ),
            })
            continue

        mutated_out = result["stdout"].rstrip("\n")
        baseline_lines = baseline.splitlines()
        mutated_lines = mutated_out.splitlines()
        diverged = [
            i for i, (b, m) in enumerate(zip(baseline_lines, mutated_lines)) if b != m
        ]
        # Also count length difference
        len_diff = abs(len(baseline_lines) - len(mutated_lines))
        diverged_count = len(diverged) + len_diff

        if verbose:
            print(f"  mutation: {desc}")
            print(f"  diverged_lines={diverged_count}")
            for idx in diverged[:5]:
                print(f"    baseline : {baseline_lines[idx]}")
                print(f"    mutated  : {mutated_lines[idx]}")

        results.append({
            "desc": desc,
            "diverged": diverged_count > 0,
            "diverged_lines": diverged_count,
            "error": None,
        })

    return results


# ---------------------------------------------------------------------------
# CLI entry-point: capture() + determinism check + mutation proof
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Smart-director golden oracle")
    parser.add_argument("--compiler", default="clang++", help="C++ compiler")
    parser.add_argument("--verify-mutations", action="store_true",
                        help="Run mutation verification after capture")
    parser.add_argument("--json", action="store_true",
                        help="Emit capture output as raw JSON lines to stdout")
    args = parser.parse_args()

    print("=== oracle_smart_director: capture run 1 ===", file=sys.stderr)
    out1 = capture(compiler=args.compiler)

    print("=== oracle_smart_director: capture run 2 (determinism check) ===", file=sys.stderr)
    out2 = capture(compiler=args.compiler)

    records = [json.loads(line) for line in out1.splitlines() if line.strip()]
    print(f"records={len(records)}", file=sys.stderr)

    if out1 != out2:
        print("FAIL: capture() is NOT deterministic — runs 1 and 2 differ", file=sys.stderr)
        sys.exit(1)
    print("determinism=OK (byte-identical across two captures)", file=sys.stderr)

    if args.json:
        print(out1)

    if args.verify_mutations:
        print("\n=== mutation verification ===", file=sys.stderr)
        mut_results = verify_mutations(out1, compiler=args.compiler, verbose=True)
        all_pass = True
        for r in mut_results:
            status = "DIVERGED" if r["diverged"] else "NO-DIVERGENCE"
            err = f" error={r['error']}" if r["error"] else ""
            print(f"  [{status}] lines={r['diverged_lines']}{err}", file=sys.stderr)
            print(f"           {r['desc']}", file=sys.stderr)
            if not r["diverged"]:
                all_pass = False
        if not all_pass:
            print("\nFAIL: one or more mutations did not diverge", file=sys.stderr)
            sys.exit(1)
        print("\nAll mutations diverged — oracle is sensitive.", file=sys.stderr)

    print(f"\nNAME={NAME}", file=sys.stderr)
    print(f"MODULE_CPPS={MODULE_CPPS}", file=sys.stderr)
