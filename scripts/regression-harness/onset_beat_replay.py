#!/usr/bin/env python3
"""Compile and run host-side replay tests for sb_onset_beat.cpp."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""


CPP_REPLAY = r"""
#include "sb_onset_beat.h"

#include <cmath>
#include <cstdio>

static int failures = 0;

static void check(bool condition, const char* message) {
  if (!condition) {
    std::printf("FAIL: %s\n", message);
    failures++;
  }
}

static SBAudioSnapshot make_audio(uint32_t ms, float novelty, float low_energy, bool silence = false, float peak_scaled = -1.0f) {
  SBAudioSnapshot audio = {};
  audio.frame_ms = ms;
  audio.novelty = novelty;
  audio.low_energy = low_energy;
  audio.peak_scaled = peak_scaled < 0.0f ? novelty : peak_scaled;
  audio.silence = silence;
  return audio;
}

static SBOnsetBeatEvent step(uint32_t ms, float novelty, float low_energy, bool silence = false, float peak_scaled = -1.0f) {
  SBAudioSnapshot audio = make_audio(ms, novelty, low_energy, silence, peak_scaled);
  sb_onset_beat_update(audio);
  return sb_onset_beat_read();
}

static SBOnsetBeatEvent impulse(uint32_t ms) {
  if (ms > 120) {
    step(ms - 120, 0.0f, 0.0f);
  }
  return step(ms, 1.0f, 1.0f);
}

static void test_reset_and_silence_are_inert() {
  sb_onset_beat_reset();
  SBOnsetBeatEvent event = sb_onset_beat_read();
  check(event.event_id == 0, "reset clears event id");
  check(!event.onset && !event.bass_onset && !event.beat, "reset clears flags");

  step(1, 0.0f, 0.0f);
  event = step(100, 0.0f, 0.0f, true);
  check(event.event_id == 0, "silence does not create events");
  check(!event.onset && !event.bass_onset && !event.beat, "silence clears event flags");
  check(event.beat_confidence == 0.0f, "silence clears confidence");
}

static void test_refractory_and_event_age() {
  sb_onset_beat_reset();
  step(1, 0.0f, 0.0f);
  SBOnsetBeatEvent first = step(100, 1.0f, 1.0f);
  check(first.event_id == 1, "first impulse creates one event");
  check(first.event_ms == 100, "accepted event owns event_ms");
  check(first.event_age_ms == 0, "accepted event age is zero");

  SBOnsetBeatEvent blocked = step(150, 1.0f, 1.0f);
  check(blocked.event_id == 1, "refractory impulse does not create a new event");
  check(blocked.event_ms == 100, "refractory impulse does not move event_ms");

  SBOnsetBeatEvent aged = step(250, 0.0f, 0.0f);
  check(aged.event_id == 1, "quiet frame does not create a new event");
  check(aged.event_age_ms == 150, "quiet frame reports age from last accepted event");
  check(!aged.beat, "quiet frame does not emit a predicted beat tick");
}

static void test_real_event_only_beat_lock() {
  sb_onset_beat_reset();
  step(1, 0.0f, 0.0f);
  check(impulse(100).event_id == 1, "beat train event 1 accepted");
  check(impulse(600).event_id == 2, "beat train event 2 accepted");
  check(impulse(1100).event_id == 3, "beat train event 3 accepted");
  SBOnsetBeatEvent locked = impulse(1600);
  check(locked.event_id == 4, "beat train event 4 accepted");
  check(locked.beat_confidence >= 0.5f, "regular accepted intervals build beat confidence");
  check(locked.beat, "beat flag is true only on the accepted locked event");

  SBOnsetBeatEvent predicted = step(1850, 0.0f, 0.0f);
  check(predicted.event_id == 4, "post-event quiet frame keeps event id");
  check(!predicted.beat, "post-event quiet frame does not free-run beat=true");
}

static void test_silence_clears_locked_confidence() {
  sb_onset_beat_reset();
  step(1, 0.0f, 0.0f);
  impulse(100);
  impulse(600);
  impulse(1100);
  impulse(1600);
  SBOnsetBeatEvent silent = step(1800, 0.0f, 0.0f, true);
  check(!silent.onset && !silent.bass_onset && !silent.beat, "silence clears locked event flags");
  check(silent.beat_confidence == 0.0f, "silence clears locked confidence");
  check(silent.beat_phase == 0.0f, "silence clears beat phase");
  check(silent.event_ms == 1600, "silence does not rewrite last event time");
}

static void test_broken_interval_decays_lock() {
  sb_onset_beat_reset();
  step(1, 0.0f, 0.0f);
  impulse(100);
  impulse(600);
  impulse(1100);
  SBOnsetBeatEvent locked = impulse(1600);
  check(locked.beat_confidence >= 0.5f, "precondition: train is locked");
  SBOnsetBeatEvent broken = impulse(2600);
  check(broken.event_id == 5, "broken interval still records the real event");
  check(broken.beat_confidence < 0.5f, "broken interval decays beat confidence");
  check(!broken.beat, "broken interval is not reported as a locked beat");
}

static void test_peak_train_locks_without_spectral_novelty() {
  sb_onset_beat_reset();
  step(1, 0.0f, 0.0f, false, 0.0f);
  step(100, 0.0f, 0.0f, false, 0.85f);
  step(480, 0.0f, 0.0f, false, 0.0f);
  step(600, 0.0f, 0.0f, false, 0.85f);
  step(980, 0.0f, 0.0f, false, 0.0f);
  step(1100, 0.0f, 0.0f, false, 0.85f);
  step(1480, 0.0f, 0.0f, false, 0.0f);
  SBOnsetBeatEvent locked = step(1600, 0.0f, 0.0f, false, 0.85f);
  check(locked.event_id == 4, "peak-only train creates accepted events");
  check(locked.beat_confidence >= 0.5f, "peak-only train builds beat confidence");
  check(locked.beat, "peak-only locked train marks accepted beat");
}

static void test_invalid_inputs_clamp_to_inert() {
  sb_onset_beat_reset();
  step(1, 0.0f, 0.0f);
  SBOnsetBeatEvent event = step(100, NAN, -5.0f);
  check(event.event_id == 0, "NaN and negative inputs do not create events");
  check(event.beat_confidence == 0.0f, "invalid inputs do not create confidence");
}

int main() {
  test_reset_and_silence_are_inert();
  test_refractory_and_event_age();
  test_real_event_only_beat_lock();
  test_silence_clears_locked_confidence();
  test_broken_interval_decays_lock();
  test_peak_train_locks_without_spectral_novelty();
  test_invalid_inputs_clamp_to_inert();
  if (failures != 0) {
    std::printf("ONSET_BEAT_REPLAY_FAIL failures=%d\n", failures);
    return 1;
  }
  std::printf("ONSET_BEAT_REPLAY_OK cases=7\n");
  return 0;
}
"""


# ---------------------------------------------------------------------------
# SB_ONSET_V2 synthetic asserts. Separate main (compiled with -DSB_ONSET_V2) that
# proves: (1) per-band refractory adherence, (2) channel separation (kick fires on
# bass-only frames / hihat on high-only frames, NOT vice-versa), (3) the
# gate-permission-only invariant: a gated (silence) run must NOT shift the median
# threshold baseline -- the first onset envelope after the gate re-opens must equal
# the envelope from an identical never-gated run (the gate injects no zeros into
# detector stats). Emits ONSET_V2_REPLAY_OK cases=3.
# ---------------------------------------------------------------------------
CPP_REPLAY_V2 = r"""
#include "sb_onset_beat.h"
#include <cmath>
#include <cstdio>

static int failures = 0;
static void check(bool c, const char* m){ if(!c){ std::printf("FAIL: %s\n", m); failures++; } }

static SBAudioSnapshot frame(uint32_t ms, bool silence) {
  SBAudioSnapshot a = {};
  a.frame_ms = ms; a.silence = silence; a.spectral_energy = silence ? 0.0f : 0.3f;
  a.vu_level = silence ? 0.0f : 0.3f;
  return a;
}
static void band(SBAudioSnapshot& a, int lo, int hi, float v){ for(int i=lo;i<hi;i++) a.spectrum[i]=v; }
static void rest(SBAudioSnapshot& a, float v){ for(int i=0;i<80;i++) a.spectrum[i]=v; }

// Drive a single-frame-peaked hit in [lo,hi): attack frame at `v`, decay after.
static SBOnsetBeatEvent hit_band(uint32_t ms, int lo, int hi) {
  SBAudioSnapshot a = frame(ms, false);
  rest(a, 0.02f); band(a, lo, hi, 0.85f);
  sb_onset_beat_update(a);
  return sb_onset_beat_read();
}
static void quiet(uint32_t ms) {
  SBAudioSnapshot a = frame(ms, false); rest(a, 0.02f);
  sb_onset_beat_update(a);
}

// (1) per-band refractory: kick refractory = 6 frames @133Hz (~45 ms). Fire a
// kick, then attempt another kick 2 frames (~15 ms) later (inside refractory) ->
// no new kick id. A kick 8 frames (~60 ms) later -> a new kick id.
static void test_band_refractory() {
  sb_onset_beat_reset();
  uint32_t t=0;
  for (int i=0;i<40;i++){ quiet(t); t+=8; }        // warm up past warmup window
  hit_band(t, 1, 25); t+=8;                         // attack frame
  quiet(t); t+=8;                                   // band trigger fires here (delayed)
  uint32_t k1 = sb_onset_beat_read().kick_event_id;
  check(k1 > 0, "first kick fires");
  // second kick 2 frames after the fire -> inside the 6-frame refractory
  hit_band(t, 1, 25); t+=8;
  quiet(t); t+=8;
  check(sb_onset_beat_read().kick_event_id == k1,
        "kick inside refractory window does not produce a new kick id");
  // let refractory fully open, then a clean kick -> new id
  for (int i=0;i<10;i++){ quiet(t); t+=8; }
  hit_band(t, 1, 25); t+=8;
  quiet(t); t+=8;
  check(sb_onset_beat_read().kick_event_id > k1, "kick after refractory window fires again");
}

// (2) channel separation: bass-only hit -> kick fires, hihat does NOT; high-only
// hit -> hihat fires, kick does NOT.
static void test_channel_separation() {
  sb_onset_beat_reset();
  for (uint32_t t=0;t<200;t+=8) quiet(t);
  uint32_t kid0=sb_onset_beat_read().kick_event_id, hid0=sb_onset_beat_read().hihat_event_id;
  hit_band(200, 1, 25); quiet(208);               // bass-only
  SBOnsetBeatEvent eb=sb_onset_beat_read();
  check(eb.kick_event_id > kid0, "bass-only frame fires kick");
  check(eb.hihat_event_id == hid0, "bass-only frame does NOT fire hihat");
  for(uint32_t t=216;t<500;t+=8) quiet(t);
  uint32_t kid1=sb_onset_beat_read().kick_event_id, hid1=sb_onset_beat_read().hihat_event_id;
  hit_band(500, 70, 80); quiet(508);              // high-only
  SBOnsetBeatEvent eh=sb_onset_beat_read();
  check(eh.hihat_event_id > hid1, "high-only frame fires hihat");
  check(eh.kick_event_id == kid1, "high-only frame does NOT fire kick");
}

// (3) gate-permission-only: a long silence GATE must not corrupt the adaptive
// baseline. Run A: warm, then a measured hit. Run B: identical but with a silence
// burst inserted BEFORE the hit. The transient strength of the post-gate hit in B
// must equal the no-gate hit in A (median ring + band EMA untouched by the gate).
static float measure_hit_after(int gate_frames) {
  sb_onset_beat_reset();
  uint32_t t=0;
  for(int i=0;i<40;i++){ quiet(t); t+=8; }        // identical warm-up in both runs
  for(int i=0;i<gate_frames;i++){ SBAudioSnapshot a=frame(t,true); sb_onset_beat_update(a); t+=8; }
  // re-prime frame after gate (silence path re-seeds prev spectrum); then the hit.
  quiet(t); t+=8;
  SBOnsetBeatEvent e=hit_band(t, 1, 80);          // full-band hit
  return e.transient_strength;
}
static void test_gate_permission_only() {
  float no_gate   = measure_hit_after(0);
  float with_gate = measure_hit_after(60);        // 60-frame (~450 ms) silence gate
  // The gate is output-permission-only: it re-primes prev-spectrum but injects no
  // zeros into the median/EMA stats, so the measured onset strength is identical.
  check(std::fabs(no_gate - with_gate) < 1e-4f,
        "silence gate does not shift the adaptive onset baseline (permission-only)");
  check(no_gate > 0.0f, "baseline hit actually produced an onset (sanity)");
}

int main() {
  test_band_refractory();
  test_channel_separation();
  test_gate_permission_only();
  if (failures != 0) { std::printf("ONSET_V2_REPLAY_FAIL failures=%d\n", failures); return 1; }
  std::printf("ONSET_V2_REPLAY_OK cases=3\n");
  return 0;
}
"""


def run_replay(compiler="clang++", keep_dir=None, v2=False):
    temp_owner = None
    if keep_dir:
        workdir = Path(keep_dir)
        workdir.mkdir(parents=True, exist_ok=True)
    else:
        temp_owner = tempfile.TemporaryDirectory()
        workdir = Path(temp_owner.name)

    try:
        stub_dir = workdir / "stub"
        stub_dir.mkdir(exist_ok=True)
        (stub_dir / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
        main_cpp = workdir / "onset_beat_replay_main.cpp"
        binary = workdir / "onset_beat_replay"
        main_cpp.write_text(CPP_REPLAY_V2 if v2 else CPP_REPLAY, encoding="utf-8")

        compile_cmd = [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            *(["-DSB_ONSET_V2"] if v2 else []),
            "-I",
            str(stub_dir),
            "-I",
            str(FIRMWARE),
            *[a for d in ("audio","visual","effects","director","serial","system","persistence","calibration","diag") for a in ("-I", str(FIRMWARE / d))],
            str(next(FIRMWARE.rglob("sb_onset_beat.cpp"))),
            str(main_cpp),
            "-o",
            str(binary),
        ]
        compile_result = subprocess.run(
            compile_cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if compile_result.returncode != 0:
            return {
                "ok": False,
                "stage": "compile",
                "returncode": compile_result.returncode,
                "stdout": compile_result.stdout,
                "stderr": compile_result.stderr,
                "workdir": str(workdir),
            }

        run_result = subprocess.run(
            [str(binary)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return {
            "ok": run_result.returncode == 0,
            "stage": "run",
            "returncode": run_result.returncode,
            "stdout": run_result.stdout,
            "stderr": run_result.stderr,
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
    parser.add_argument("--v2", action="store_true",
                        help="compile with -DSB_ONSET_V2 and run the V2 synthetic asserts")
    args = parser.parse_args(argv)

    result = run_replay(compiler=args.compiler, keep_dir=args.keep_dir, v2=args.v2)
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
