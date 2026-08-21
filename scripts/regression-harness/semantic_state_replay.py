#!/usr/bin/env python3
"""AudioSemanticState spine host harness — REAL firmware C++ on scripted events.

Proves `audio_semantic_read()` (audio/k1_semantic_state.cpp, behind
K1_SEMANTIC_STATE) packs the produced fields correctly by driving the REAL
underlying producers and reading the aggregate back:

  - tempo  : the REAL k1_tempo.cpp is fed a clean synthetic beat train; the
             packed bpm / tempo_confidence / tempo_locked / beat_phase01 /
             beat_strength MUST equal k1_tempo_read() field-for-field.
  - onset  : the REAL k1_onset_beat.cpp (-DK1_ONSET_V2) is driven with band-
             localised hits; the packed onset / *_level channels MUST equal
             k1_onset_beat_read() field-for-field.
  - chord  : a host snapshot stub runs the REAL k1_chord_detect.cpp on a labelled
             chroma; the packed chord_root / chord_type / chord_confidence MUST
             equal the detected chord.
  - rate   : the self-described diagnostics MUST equal the firmware derivation
             (12800/96 = 133.33 Hz AP, /3 = 44.44 Hz novelty, 7.5 ms frame).

The snapshot PRODUCER (k1_audio_snapshot.cpp) is replaced by a tiny host stub
because the real producer needs firmware globals (FastLED/FixedPoints). The
spine only ever calls k1_audio_snapshot_READ(), so the stub faithfully models
the read surface (and runs the REAL chord detector on the chroma we inject).
tempo + onset use the REAL producers — those are what the spine forwards.

NON-SHIPPING. Host-only. K1_SEMANTIC_STATE / K1_SEMANTIC_HOST_TEST never enter a
PlatformIO env. Run: python3 scripts/regression-harness/semantic_state_replay.py
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# Minimal Arduino stub: only the portMUX critical-section surface the producer
# TUs touch. k1_tempo.cpp / k1_onset_beat.cpp are otherwise stdint/math-only and
# self-clock from audio.frame_ms (no millis()).
ARDUINO_STUB = r"""
#pragma once
#include <stdint.h>
#include <math.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""

# Host snapshot stub: stands in for k1_audio_snapshot.cpp (whose real producer
# needs firmware globals). Stores a settable snapshot and, under K1_CHORD_V2,
# runs the REAL k1_detect_chord on the injected chroma so the chord the spine
# forwards is genuinely produced, not hand-set.
SNAPSHOT_STUB = r"""
#include "k1_audio_snapshot.h"
static K1AudioSnapshot g_snap = {};
void k1_audio_snapshot_update(uint32_t frame_ms) { g_snap.frame_ms = frame_ms; }
void k1_audio_snapshot_publish(const K1AudioSnapshot& next) { g_snap = next; }
K1AudioSnapshot k1_audio_snapshot_read() { return g_snap; }
// host-test entry points used by the driver to inject a snapshot
extern "C" void host_set_snapshot_frame_ms(uint32_t ms) { g_snap.frame_ms = ms; }
#ifdef K1_CHORD_V2
extern "C" void host_set_snapshot_chroma(const float* chroma_pc) {
  for (int i = 0; i < K1_CHROMA_PC_BINS; i++) g_snap.chroma_pc[i] = chroma_pc[i];
  k1_detect_chord(g_snap.chroma_pc, g_snap.chord);
}
#endif
"""

DRIVER_MAIN = r"""
#include "k1_semantic_state.h"
#include <cmath>
#include <cstdio>

extern "C" void host_set_snapshot_frame_ms(uint32_t ms);
#ifdef K1_CHORD_V2
extern "C" void host_set_snapshot_chroma(const float* chroma_pc);
#endif

static int failures = 0;
static void check(bool c, const char* m){ if(!c){ std::printf("FAIL: %s\n", m); failures++; } }
static void feq(float a, float b, const char* m){
  if (std::fabs(a-b) > 1e-5f){ std::printf("FAIL: %s (%.6f != %.6f)\n", m, a, b); failures++; }
}

// Drive the real tempo producer with one AP frame.
static void tempo_frame(uint32_t ms, float novelty) {
  K1AudioSnapshot a = {};
  a.frame_ms = ms; a.novelty = novelty; a.peak_scaled = novelty;
  a.spectral_energy = novelty > 0.0f ? 0.5f : 0.0f;
  a.vu_level = novelty > 0.0f ? 0.3f : 0.0f;
  k1_tempo_update(a);
}

// Drive the real onset producer (V2) with a band-localised hit / quiet frame.
static void onset_drive(uint32_t ms, bool hit, int lo, int hi) {
  K1AudioSnapshot a = {};
  a.frame_ms = ms; a.silence = false; a.spectral_energy = 0.3f;
  a.vu_level = 0.3f;
  for (int i=0;i<K1_ONSET_SPECTRUM_BINS;i++) a.spectrum[i] = 0.02f;
  if (hit) for (int i=lo;i<hi;i++) a.spectrum[i] = 0.85f;
  k1_onset_beat_update(a);
}

int main() {
  k1_tempo_init();
  k1_tempo_reset();
  k1_onset_beat_reset();

  // --- 1) RATE DIAGNOSTICS (no producer state needed) -----------------------
  AudioSemanticState s = {};
  host_set_snapshot_frame_ms(1234);
  audio_semantic_read(&s);
  feq(s.sample_rate_hz, 12800.0f, "sample_rate_hz == 12800");
  check(s.samples_per_chunk == 96, "samples_per_chunk == 96");
  feq(s.ap_frame_hz, 12800.0f/96.0f, "ap_frame_hz == 133.333");
  feq(s.novelty_rate_hz, (12800.0f/96.0f)/3.0f, "novelty_rate_hz == 44.444");
  feq(s.frame_ms_nominal, 1000.0f/(12800.0f/96.0f), "frame_ms_nominal == 7.5 ms");
  check(s.frame_ms == 1234, "frame_ms forwarded from snapshot");

  // --- 2) TEMPO PACKING: real producer -> spine must match field-for-field --
  // Clean 120 BPM train: a novelty impulse every 500 ms = every 66.6 AP frames.
  // Feed enough frames to warm the ACF ring and let the metric settle.
  const float dt_ms = 1000.0f/(12800.0f/96.0f);  // 7.5 ms
  uint32_t ms_acc = 0;
  float beat_acc = 0.0f;
  const float beat_period_ms = 500.0f;            // 120 BPM
  for (int f=0; f<4000; f++) {
    float nov = 0.0f;
    beat_acc += dt_ms;
    if (beat_acc >= beat_period_ms) { beat_acc -= beat_period_ms; nov = 1.0f; }
    tempo_frame(ms_acc, nov);
    ms_acc += (uint32_t)(dt_ms + 0.5f);
  }
  K1TempoEvent te = k1_tempo_read();
  audio_semantic_read(&s);
  feq(s.bpm, te.bpm, "spine.bpm == k1_tempo_read().bpm");
  feq(s.tempo_confidence, te.confidence, "spine.tempo_confidence == tempo.confidence");
  feq(s.beat_phase01, te.phase01, "spine.beat_phase01 == tempo.phase01");
  feq(s.beat_strength, te.beat_strength, "spine.beat_strength == tempo.beat_strength");
  check(s.tempo_locked == te.locked, "spine.tempo_locked == tempo.locked");
  check(s.beat_tick == te.beat_tick, "spine.beat_tick == tempo.beat_tick");
  // The clean train must actually drive a non-zero BPM (producer is alive).
  check(s.bpm > 0.0f, "tempo producer reported a non-zero BPM on a clean train");

#ifdef K1_ONSET_V2
  // --- 3) ONSET PACKING: real producer -> spine must match field-for-field --
  uint32_t t = 0;
  for (int i=0;i<40;i++){ onset_drive(t, false, 0, 0); t += 8; }   // warm past warmup
  onset_drive(t, true, 1, 25); t += 8;                              // bass-only attack -> kick
  onset_drive(t, false, 0, 0); t += 8;                             // band trigger fires (delayed)
  K1OnsetBeatEvent oe = k1_onset_beat_read();
  audio_semantic_read(&s);
  check(s.onset == oe.onset, "spine.onset == onset.onset");
  feq(s.onset_strength, oe.onset_strength, "spine.onset_strength == onset.onset_strength");
  check(s.kick == oe.kick, "spine.kick == onset.kick");
  check(s.snare == oe.snare, "spine.snare == onset.snare");
  check(s.hihat == oe.hihat, "spine.hihat == onset.hihat");
  check(s.transient == oe.transient, "spine.transient == onset.transient");
  feq(s.kick_level, oe.kick_level, "spine.kick_level == onset.kick_level");
  feq(s.snare_level, oe.snare_level, "spine.snare_level == onset.snare_level");
  feq(s.hihat_level, oe.hihat_level, "spine.hihat_level == onset.hihat_level");
  feq(s.transient_level, oe.transient_level, "spine.transient_level == onset.transient_level");
  check(oe.kick_event_id > 0, "onset producer actually fired a kick (sanity)");
#endif

#ifdef K1_CHORD_V2
  // --- 4) CHORD PACKING: real detector via snapshot stub -> spine ------------
  // A-origin A-major triad: A(0)=1.0, C#(4)=0.8, E(7)=0.7, floor 0.05.
  float chroma[12]; for (int i=0;i<12;i++) chroma[i]=0.05f;
  chroma[0]=1.0f; chroma[4]=0.8f; chroma[7]=0.7f;
  host_set_snapshot_chroma(chroma);
  audio_semantic_read(&s);
  check(s.chord_root == 0, "spine.chord_root == 0 (A-origin A)");
  check(s.chord_type == 1, "spine.chord_type == MAJOR(1)");
  check(s.chord_confidence > 0.60f, "spine.chord_confidence > 0.60 on clean A-major");
#endif

  if (failures != 0) { std::printf("SEMANTIC_STATE_REPLAY_FAIL failures=%d\n", failures); return 1; }
  std::printf("SEMANTIC_STATE_REPLAY_OK rate=1 tempo=1 onset=%d chord=%d\n",
#ifdef K1_ONSET_V2
              1
#else
              0
#endif
              ,
#ifdef K1_CHORD_V2
              1
#else
              0
#endif
  );
  return 0;
}
"""


def run_replay(compiler="clang++", keep_dir=None, defines=None):
    defines = defines if defines is not None else ["K1_SEMANTIC_STATE", "K1_SEMANTIC_HOST_TEST",
                                                   "K1_ONSET_V2", "K1_CHORD_V2"]
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
        main_cpp = workdir / "semantic_state_replay_main.cpp"
        snap_cpp = workdir / "snapshot_stub.cpp"
        main_cpp.write_text(DRIVER_MAIN, encoding="utf-8")
        snap_cpp.write_text(SNAPSHOT_STUB, encoding="utf-8")
        binary = workdir / "semantic_state_replay"

        compile_cmd = [
            compiler, "-std=c++17", "-Wall", "-Wextra",
            *[f"-D{d}" for d in defines],
            "-I", str(stub_dir),
            "-I", str(FW),
            *[a for d in ("audio", "visual", "effects", "director", "serial",
                          "system", "persistence", "calibration", "diag", "platform")
              for a in ("-I", str(FW / d))],
            str(FW / "audio" / "k1_semantic_state.cpp"),
            str(FW / "audio" / "k1_tempo.cpp"),
            str(FW / "audio" / "k1_onset_beat.cpp"),
            str(FW / "audio" / "k1_chord_detect.cpp"),
            str(snap_cpp),
            str(main_cpp),
            "-o", str(binary),
        ]
        cr = subprocess.run(compile_cmd, cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cr.returncode != 0:
            return {"ok": False, "stage": "compile", "returncode": cr.returncode,
                    "stdout": cr.stdout, "stderr": cr.stderr, "workdir": str(workdir)}
        rr = subprocess.run([str(binary)], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {"ok": rr.returncode == 0, "stage": "run", "returncode": rr.returncode,
                "stdout": rr.stdout, "stderr": rr.stderr, "workdir": str(workdir)}
    finally:
        if temp_owner is not None:
            temp_owner.cleanup()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--compiler", default="clang++")
    p.add_argument("--keep-dir")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
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
