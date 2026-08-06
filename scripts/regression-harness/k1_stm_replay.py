#!/usr/bin/env python3
"""Compile and run host-side replay tests for the REAL k1_stm.cpp producer.

Mirrors onset_beat_replay.py: compiles audio/k1_stm.cpp with -DK1_STM against a
generated main that drives SYNTHETIC spectra with KNOWN modulation, then asserts
the STM producer's response. No Arduino stub is needed — k1_stm.cpp is a pure
stdint/math translation unit.

Cases (emit K1_STM_REPLAY_OK cases=5):
  1. warm-up gate      — ready=false + exactly-zero outputs for the first 16
                         frames; ready=true at frame 17 (127.5 ms @133.33 Hz).
  2. steady input      — a static spectral shape yields ~0 temporal modulation.
  3. modulated input   — a 4 Hz antiphase shape modulation yields HIGH temporal
                         energy, strictly greater than the steady case.
  4. spectral ripple   — a K-cycle frequency-axis ripple localises to spectral
                         bin (K-1) (argmax) with non-trivial spectral energy.
  5. silence honesty   — warm on silence still reaches ready and reports EXACT
                         zeros (a real "no modulation" measurement, never a
                         fabricated absence — k1_semantic_state doctrine).
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


CPP_REPLAY = r"""
#include "k1_stm.h"

#include <cmath>
#include <cstdio>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static int failures = 0;
static void check(bool c, const char* m) {
  if (!c) { std::printf("FAIL: %s\n", m); failures++; }
}

static const int   NB = 80;
static const float FS = 133.3333f;   // K1 AP frame rate (12800/96)

static void fill(float* s, float v) { for (int i = 0; i < NB; i++) s[i] = v; }

// ---- case 1: warm-up gate -------------------------------------------------
static void test_warmup_gate() {
  k1_stm_reset();
  float s[NB]; fill(s, 0.5f);
  K1StmResult r;
  for (int f = 1; f <= 16; f++) {
    k1_stm_process(s, NB, false, &r);
    check(!r.ready, "not ready during the 17-frame warm-up");
    check(r.temporal_energy == 0.0f && r.spectral_energy == 0.0f,
          "warm-up energies are EXACTLY zero (no fabricated measurement)");
    bool allz = true;
    for (int k = 0; k < K1_STM_SPECTRAL_BINS; k++) if (r.spectral[k] != 0.0f) allz = false;
    check(allz, "warm-up spectral vector is exactly zero");
  }
  k1_stm_process(s, NB, false, &r);   // frame 17
  check(r.ready, "ready at frame 17 (temporal window warm)");
}

// ---- cases 2 & 3: temporal modulation -------------------------------------
// Static spectral shape -> no temporal modulation.
static float run_steady(int frames) {
  k1_stm_reset();
  float s[NB];
  for (int i = 0; i < NB; i++) s[i] = 0.2f + 0.6f * (float)i / (float)(NB - 1);  // static ramp
  K1StmResult r{};
  for (int f = 0; f < frames; f++) k1_stm_process(s, NB, false, &r);
  return r.temporal_energy;
}

// Antiphase two-group SHAPE modulation at exactly 4 Hz -> strong temporal mod.
// Modulating the shape (not overall level) survives the per-frame peak-normalise.
static float run_modulated(int frames) {
  k1_stm_reset();
  K1StmResult r{};
  for (int f = 0; f < frames; f++) {
    float s[NB];
    float phase = 2.0f * (float)M_PI * 4.0f * (float)f / FS;
    float mod = 0.4f * std::sin(phase);
    for (int i = 0; i < NB; i++) {
      float v = (i < NB / 2) ? (0.5f + mod) : (0.5f - mod);
      if (v < 0.0f) v = 0.0f; if (v > 1.0f) v = 1.0f;
      s[i] = v;
    }
    k1_stm_process(s, NB, false, &r);
  }
  return r.temporal_energy;
}

static void test_temporal_discrimination() {
  // 120 frames >> the ~50-frame EMA settling time (attack alpha 0.0591).
  float steady    = run_steady(120);
  float modulated = run_modulated(120);
  check(steady < 0.01f, "static input yields an honest ~0 temporal energy");
  check(modulated > 0.40f, "4 Hz shape modulation yields high temporal energy");
  check(modulated > steady + 0.30f, "modulated clearly exceeds steady (discrimination)");
}

// ---- case 4: spectral ripple localisation ---------------------------------
static void test_spectral_ripple_localises() {
  k1_stm_reset();
  const int K = 5;                    // 5 ripple cycles across the 80-bin axis
  K1StmResult r{};
  for (int f = 0; f < 120; f++) {     // settle the EMA
    float s[NB];
    for (int i = 0; i < NB; i++)
      s[i] = 0.5f + 0.4f * std::sin(2.0f * (float)M_PI * (float)K * (float)i / (float)NB);
    k1_stm_process(s, NB, false, &r);
  }
  check(r.ready, "spectral case reached ready");
  int argmax = 0; float peak = -1.0f;
  for (int k = 0; k < K1_STM_SPECTRAL_BINS; k++) {
    if (r.spectral[k] > peak) { peak = r.spectral[k]; argmax = k; }
  }
  // spectral[j] carries ripple cycle (j+1), so K cycles -> index K-1.
  check(argmax == K - 1, "spectral ripple localises to bin (K-1)");
  check(r.spectral_energy > 0.02f, "rippled spectrum yields non-trivial spectral energy");
}

// ---- case 5: silence is an honest exact zero ------------------------------
static void test_silence_is_honest_zero() {
  k1_stm_reset();
  float z[NB]; fill(z, 0.0f);
  K1StmResult r{};
  for (int f = 1; f <= 20; f++) k1_stm_process(z, NB, true, &r);
  check(r.ready, "warm on silence still reaches ready (silence is a real measurement)");
  check(r.temporal_energy == 0.0f, "silence temporal energy is EXACTLY zero (not fabricated)");
  check(r.spectral_energy == 0.0f, "silence spectral energy is EXACTLY zero");
  bool allz = true;
  for (int k = 0; k < K1_STM_SPECTRAL_BINS; k++) if (r.spectral[k] != 0.0f) allz = false;
  check(allz, "silence spectral vector is exactly zero");
}

int main() {
  test_warmup_gate();
  test_temporal_discrimination();
  test_spectral_ripple_localises();
  test_silence_is_honest_zero();
  if (failures != 0) { std::printf("K1_STM_REPLAY_FAIL failures=%d\n", failures); return 1; }
  std::printf("K1_STM_REPLAY_OK cases=5\n");
  return 0;
}
"""


def run_replay(compiler="clang++", keep_dir=None):
    temp_owner = None
    if keep_dir:
        workdir = Path(keep_dir)
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        temp_owner = tempfile.TemporaryDirectory()
        workdir = Path(temp_owner.name)

    try:
        main_cpp = workdir / "k1_stm_replay_main.cpp"
        binary = workdir / "k1_stm_replay"
        main_cpp.write_text(CPP_REPLAY, encoding="utf-8")

        compile_cmd = [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-DK1_STM",
            "-I",
            str(FIRMWARE),
            *[a for d in ("audio", "system") for a in ("-I", str(FIRMWARE / d))],
            str(next(FIRMWARE.rglob("k1_stm.cpp"))),
            str(main_cpp),
            "-o",
            str(binary),
        ]
        compile_result = subprocess.run(
            compile_cmd, cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if compile_result.returncode != 0:
            return {
                "ok": False, "stage": "compile",
                "returncode": compile_result.returncode,
                "stdout": compile_result.stdout, "stderr": compile_result.stderr,
                "workdir": str(workdir),
            }

        run_result = subprocess.run(
            [str(binary)], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {
            "ok": run_result.returncode == 0, "stage": "run",
            "returncode": run_result.returncode,
            "stdout": run_result.stdout, "stderr": run_result.stderr,
            "workdir": str(workdir),
        }
    finally:
        if temp_owner is not None:
            temp_owner.cleanup()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="clang++")
    parser.add_argument("--keep-dir")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of replay stdout")
    args = parser.parse_args(argv)

    result = run_replay(compiler=args.compiler, keep_dir=args.keep_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result.get("stdout"):
            print(result["stdout"], end="")
        if result.get("stderr"):
            print(result["stderr"], end="", file=sys.stderr)
    return 0 if result["ok"] else result["returncode"] or 1


if __name__ == "__main__":
    sys.exit(main())
