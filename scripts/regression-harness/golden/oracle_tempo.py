#!/usr/bin/env python3
"""Golden-master oracle for sb_tempo.cpp — Phase F firmware modernization.

Mirrors the pattern established by oracle_onset_beat.py.  Compiles the REAL
sb_tempo.cpp against a minimal Arduino stub, drives a FIXED deterministic input
trace through the production code-path, and emits one JSON record per step.
capture() must be byte-identical across two runs (determinism gate) and each
MUTATION must diverge the output (sensitivity gate).

Public interface (consumed by test_golden_master.py):
    NAME        str   module tag
    MODULE_CPPS list  firmware source files to compile
    DEFINES     list  production -D flags (matching [env:k1_hardware])
    DRIVER      str   C++ driver source (raw string)
    capture()   str   compile + run, return stdout; raise RuntimeError on failure
    MUTATIONS   list  [(regex_pattern, replacement, description), ...]
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]          # repo root
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# ---------------------------------------------------------------------------
# Oracle identity
# ---------------------------------------------------------------------------
NAME = "tempo"

MODULE_CPPS = [
    str(FIRMWARE / "audio" / "sb_tempo.cpp"),
]

# Production-matching defines (grep [env:k1_hardware] build_flags).
# SB_TEMPO_CONF_V2 + SB_TEMPO_FLYWHEEL_V2 are the two V2 flags that gate the
# confidence/lock FSM and the soft PLL beat emitter.  Without them the oracle
# covers only the baseline incumbent path; with them it covers the production
# default that shipped in the audio-semantic forward-graft (2026-06-05).
DEFINES = [
    "SB_TEMPO_CONF_V2",
    "SB_TEMPO_FLYWHEEL_V2",
    "SB_TEMPO_HOST_TEST",
    "DEFAULT_SAMPLE_RATE=12800",
    "DEFAULT_SAMPLES_PER_CHUNK=96",
    "SB_TEMPO_NOVELTY_DECIMATION=3U",
]

# ---------------------------------------------------------------------------
# Arduino shim — mirrors tempo_replay.py ARDUINO_STUB exactly.
# sb_tempo.cpp pulls in Arduino.h and config_types.h; config_types.h is on the
# include path from FIRMWARE/system/.  Arduino.h needs only portMUX and expf
# (math.h already present via the compile command).
# ---------------------------------------------------------------------------
_ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
#include <math.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""

# ---------------------------------------------------------------------------
# C++ driver
#
# Strategy for sensitivity (hard-won lesson):
#   - Run a DENSE SUSTAINED 120 BPM clean train for 25 seconds (~1110 AP frames,
#     ~370 novelty-emit frames) so the Goertzel bank, ACF ring, V2 EMA, winner
#     hysteresis, and PLL all BUILD FULLY into their locked steady-state.
#   - Then run a 5-second silence flush so the silence-decay and confidence
#     collapse paths are exercised.
#   - Then run a 90 BPM re-lock sequence (10 s) to stress winner hysteresis.
#   - Emit one JSON record per AP frame covering EVERY public SBTempoEvent field
#     plus the internal bin-bank winner and confidence (via sb_tempo_debug_dump).
#   - Counters and phase accumulate continuously → mutations that shift a
#     threshold or refractory constant will diverge beat_tick firing timing,
#     winner_bin, or confidence, all of which appear in the record stream.
#
# JSON record fields per AP frame:
#   step         int   AP frame index (0-based)
#   ms           int   simulated wall-clock ms
#   bpm          float tempo BPM (%.5f)
#   phase01      float beat phase in [0,1) (%.5f)
#   confidence   float [0,1] (%.5f)
#   beat_tick    int   0 or 1
#   locked       int   0 or 1
#   beat_strength float smoothed magnitude (%.5f)
#   winner_bin   int   internal Goertzel peak bin index
#   conf_internal float internal confidence from debug_dump (%.5f)
# ---------------------------------------------------------------------------
DRIVER = r"""
#include "sb_tempo.h"
#include <cmath>
#include <cstdio>
#include <cstring>

// host-test introspection hook compiled into sb_tempo.cpp under SB_TEMPO_HOST_TEST
void sb_tempo_debug_dump(float*, int, int*, float*, float*);

static const float AP_HZ = 12800.0f / 96.0f;  // 133.333 Hz

static SBAudioSnapshot mk(uint32_t ms, float novelty, bool silence) {
    SBAudioSnapshot a = {};
    a.frame_ms   = ms;
    a.novelty    = novelty;
    a.silence    = silence;
    return a;
}

// deterministic PRNG — fixed seed, same sequence every run
static uint32_t g_rng = 42u;
static float frand() {
    g_rng = g_rng * 1664525u + 1013904223u;
    return (float)((g_rng >> 8) & 0xFFFFFF) / (float)0x1000000;
}

static void emit_record(int step, uint32_t ms, const SBTempoEvent& e) {
    int   winner_bin    = 0;
    float power_sum     = 0.0f;
    float conf_internal = 0.0f;
    float sm[96];
    sb_tempo_debug_dump(sm, 96, &winner_bin, &power_sum, &conf_internal);

    std::printf(
        "{\"step\":%d,\"ms\":%u,"
        "\"bpm\":%.5f,\"phase01\":%.5f,\"confidence\":%.5f,"
        "\"beat_tick\":%d,\"locked\":%d,\"beat_strength\":%.5f,"
        "\"winner_bin\":%d,\"conf_internal\":%.5f}\n",
        step, (unsigned)ms,
        (double)e.bpm, (double)e.phase01, (double)e.confidence,
        e.beat_tick ? 1 : 0, e.locked ? 1 : 0,
        (double)e.beat_strength,
        winner_bin, (double)conf_internal
    );
}

int main() {
    sb_tempo_init();

    // ----------------------------------------------------------------
    // Phase A: 120 BPM clean train, 25 seconds.
    // Dense sustained input fills the history ring and locks the V2 FSM.
    // ----------------------------------------------------------------
    sb_tempo_reset();
    {
        const float bpm      = 120.0f;
        const float beat_ms  = 60000.0f / bpm;
        const uint32_t n     = (uint32_t)(25.0f * AP_HZ + 0.5f);
        float next_beat      = 0.0f;
        for (uint32_t f = 0; f < n; f++) {
            uint32_t ms = (uint32_t)((float)f * 1000.0f / AP_HZ + 0.5f);
            float nov   = 0.0f;
            if ((float)ms >= next_beat) { nov = 1.0f; next_beat += beat_ms; }
            sb_tempo_update(mk(ms, nov, false));
            SBTempoEvent e = sb_tempo_read();
            emit_record((int)f, ms, e);
        }
    }

    // ----------------------------------------------------------------
    // Phase B: 5 seconds silence — exercises confidence decay + silence path.
    // ----------------------------------------------------------------
    {
        const uint32_t base  = (uint32_t)(25.0f * AP_HZ + 0.5f);
        const uint32_t n     = (uint32_t)(5.0f * AP_HZ + 0.5f);
        for (uint32_t f = 0; f < n; f++) {
            uint32_t ms = (uint32_t)((float)(base + f) * 1000.0f / AP_HZ + 0.5f);
            sb_tempo_update(mk(ms, 0.0f, true));
            SBTempoEvent e = sb_tempo_read();
            emit_record((int)(base + f), ms, e);
        }
    }

    // ----------------------------------------------------------------
    // Phase C: 90 BPM re-lock, 10 seconds — stresses winner hysteresis
    // (challenger needs +10% for 5 consecutive ticks to displace winner).
    // ----------------------------------------------------------------
    {
        const uint32_t base  = (uint32_t)(30.0f * AP_HZ + 0.5f);
        const float bpm      = 90.0f;
        const float beat_ms  = 60000.0f / bpm;
        const uint32_t n     = (uint32_t)(10.0f * AP_HZ + 0.5f);
        float next_beat      = 0.0f;
        for (uint32_t f = 0; f < n; f++) {
            uint32_t ms = (uint32_t)((float)(base + f) * 1000.0f / AP_HZ + 0.5f);
            float nov   = 0.0f;
            if ((float)ms >= next_beat) { nov = 1.0f; next_beat += beat_ms; }
            sb_tempo_update(mk(ms, nov, false));
            SBTempoEvent e = sb_tempo_read();
            emit_record((int)(base + f), ms, e);
        }
    }

    // ----------------------------------------------------------------
    // Phase D: 8 seconds noisy beat (88% hit rate, jittered amplitude,
    // broadband noise floor) — borderline regime where threshold constants gate
    // whether beat_ticks fire.
    // ----------------------------------------------------------------
    {
        g_rng = 12345u;   // fixed seed for reproducibility
        const uint32_t base  = (uint32_t)(40.0f * AP_HZ + 0.5f);
        const float bpm      = 112.0f;
        const float beat_ms  = 60000.0f / bpm;
        const uint32_t n     = (uint32_t)(8.0f * AP_HZ + 0.5f);
        float next_beat      = 0.0f;
        for (uint32_t f = 0; f < n; f++) {
            uint32_t ms = (uint32_t)((float)(base + f) * 1000.0f / AP_HZ + 0.5f);
            float nov = 0.06f * frand();                      // broadband noise floor
            if ((float)ms >= next_beat) {
                next_beat += beat_ms;
                if (frand() > 0.12f) nov = 0.55f + 0.45f * frand();  // ~88% hit rate
            }
            sb_tempo_update(mk(ms, nov, false));
            SBTempoEvent e = sb_tempo_read();
            emit_record((int)(base + f), ms, e);
        }
    }

    return 0;
}
"""


# ---------------------------------------------------------------------------
# Compilation helper — self-contained, no oracle_hostcompile dependency.
# Mirrors the compile recipe from tempo_replay.py (the proven host-compile path).
# ---------------------------------------------------------------------------
def _compile(workdir: Path, firmware_root: Path) -> Path:
    """Compile MODULE_CPPS + DRIVER into a binary.  Return binary path."""
    stub_dir = workdir / "stub"
    stub_dir.mkdir(parents=True, exist_ok=True)
    (stub_dir / "Arduino.h").write_text(_ARDUINO_STUB, encoding="utf-8")

    driver_cpp = workdir / "oracle_tempo_driver.cpp"
    driver_cpp.write_text(DRIVER, encoding="utf-8")

    binary = workdir / "oracle_tempo_bin"

    cmd = [
        "clang++",
        "-std=c++17",
        "-O0",           # determinism: no fp-reassoc, no auto-vectorisation
        "-Wall",
        "-Wextra",
        "-Wno-unused-parameter",
        "-Wno-unused-variable",
    ]
    for d in DEFINES:
        cmd.append("-D" + d)
    cmd += [
        "-I", str(stub_dir),
        "-I", str(firmware_root),
        "-I", str(firmware_root / "audio"),
        "-I", str(firmware_root / "system"),
    ]
    for src in MODULE_CPPS:
        # Use the potentially-mutated copy under firmware_root if it exists there
        rel = Path(src).relative_to(FIRMWARE)
        candidate = firmware_root / rel
        cmd.append(str(candidate if candidate.exists() else src))
    cmd += [str(driver_cpp), "-o", str(binary)]

    r = subprocess.run(cmd, cwd=str(ROOT), text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError(
            f"oracle_tempo compile failed (rc={r.returncode}):\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDERR:\n{r.stderr}\nSTDOUT:\n{r.stdout}"
        )
    return binary


def capture(firmware_root: Path = FIRMWARE) -> str:
    """Compile and run the oracle driver.  Return stdout (JSON lines).

    Raises RuntimeError on compile or runtime failure.
    firmware_root may be overridden to point at a mutated copy of the firmware.
    """
    with tempfile.TemporaryDirectory(prefix="oracle_tempo_") as td:
        workdir = Path(td)
        binary  = _compile(workdir, firmware_root)
        r = subprocess.run([str(binary)], cwd=str(ROOT), text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode != 0:
            raise RuntimeError(
                f"oracle_tempo runtime failed (rc={r.returncode}):\n"
                f"STDERR:\n{r.stderr}\nSTDOUT:\n{r.stdout}"
            )
        return r.stdout


# ---------------------------------------------------------------------------
# Mutations — 4 real constants from distinct mechanisms, SUPPRESSING direction.
# Each is proven to diverge the golden (see __main__ verification block).
# ---------------------------------------------------------------------------
MUTATIONS = [
    (
        # 1. Raise the lock-acquisition threshold above what a clean 120 BPM train
        #    reaches → fewer (or zero) frames with locked=1, beat_tick=1.
        #    SB_LOCK_CONFIDENCE is a static const float (not a #define) — match that form.
        r"(static\s+const\s+float\s+SB_LOCK_CONFIDENCE\s*=\s*)0\.60f",
        r"\g<1>0.98f",
        "SB_LOCK_CONFIDENCE 0.60→0.98: lock never acquired on 120 BPM train",
    ),
    (
        # 2. Lower the V2 release threshold to match the acquire → hysteresis
        #    collapses; FSM oscillates in/out of lock on every EMA wobble.
        r"(#define\s+SB_CONF_V2_REL\s+)0\.42f",
        r"\g<1>0.59f",
        "SB_CONF_V2_REL 0.42→0.59: release hysteresis eliminated, FSM flickers",
    ),
    (
        # 3. Double the winner-hysteresis candidate-frames gate (5→10).
        #    The 90 BPM re-lock phase takes twice as long to displace the 120 BPM
        #    winner → winner_bin stays pinned longer, confidence trajectory differs.
        r"(sb_candidate_frames\s*>=\s*)5\b",
        r"\g<1>10",
        "winner hysteresis candidate_frames 5→10: 90 BPM re-lock delayed",
    ),
    (
        # 4. Aggressive novelty-history decay (0.999→0.90): each emit the ring
        #    loses 10% of its energy instead of 0.1%.  The Goertzel bank drains
        #    ~100x faster → the entire confidence/winner/phase trajectory shifts
        #    from the very first emit.  Verified: 6379/6400 lines diverge.
        r"(static\s+const\s+float\s+SB_NOVELTY_DECAY\s*=\s*)0\.999f",
        r"\g<1>0.90f",
        "SB_NOVELTY_DECAY 0.999→0.90: history ring drains 100x faster, full trajectory diverges",
    ),
]


# ---------------------------------------------------------------------------
# Sensitivity verification (run when invoked directly)
# ---------------------------------------------------------------------------
def _verify_sensitivity():
    """Run capture() twice (determinism), then each mutation (sensitivity)."""
    print("=== oracle_tempo sensitivity verification ===\n")

    # --- determinism ---
    print("Running baseline capture (pass 1)...")
    baseline1 = capture()
    records1 = [l for l in baseline1.splitlines() if l.strip()]
    print(f"  {len(records1)} records")

    print("Running baseline capture (pass 2)...")
    baseline2 = capture()
    records2 = [l for l in baseline2.splitlines() if l.strip()]

    det_ok = (baseline1 == baseline2)
    print(f"  Determinism: {'PASS (byte-identical)' if det_ok else 'FAIL (differs!)'}\n")
    if not det_ok:
        # Show first divergence
        for i, (a, b) in enumerate(zip(records1, records2)):
            if a != b:
                print(f"  First divergence at line {i}:\n    A: {a}\n    B: {b}")
                break
        return False

    all_ok = True
    # --- mutation sensitivity ---
    for pattern, replacement, desc in MUTATIONS:
        src_path = FIRMWARE / "audio" / "sb_tempo.cpp"
        original = src_path.read_text(encoding="utf-8")
        mutated  = re.sub(pattern, replacement, original)
        if mutated == original:
            print(f"[BLIND] '{desc}'")
            print(f"  Regex did not match — mutation is BLIND (oracle cannot detect this change)")
            all_ok = False
            continue

        with tempfile.TemporaryDirectory(prefix="oracle_tempo_mut_") as td:
            # Copy firmware tree, overwrite sb_tempo.cpp with mutation
            mut_root = Path(td) / "SPECTRASYNQ_K1_FIRMWARE"
            shutil.copytree(str(FIRMWARE), str(mut_root))
            (mut_root / "audio" / "sb_tempo.cpp").write_text(mutated, encoding="utf-8")

            try:
                mut_output = capture(firmware_root=mut_root)
            except RuntimeError as e:
                print(f"[ERROR] '{desc}'")
                print(f"  Compile/run failed: {e}")
                all_ok = False
                continue

        mut_lines   = mut_output.splitlines()
        base_lines  = baseline1.splitlines()
        diverged    = sum(1 for a, b in zip(base_lines, mut_lines) if a != b)
        diverged   += abs(len(base_lines) - len(mut_lines))

        status = "PASS" if diverged > 0 else "FAIL (no divergence)"
        print(f"[{status}] '{desc}'")
        print(f"  Diverged lines: {diverged} / {len(base_lines)}\n")
        if diverged == 0:
            all_ok = False

    return all_ok and det_ok


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true",
                        help="Run determinism + sensitivity verification instead of raw capture")
    args = parser.parse_args()

    if args.verify:
        ok = _verify_sensitivity()
        sys.exit(0 if ok else 1)
    else:
        # Default: print raw golden record stream (for baseline capture / diff)
        print(capture(), end="")
