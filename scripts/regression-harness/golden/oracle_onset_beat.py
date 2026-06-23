#!/usr/bin/env python3
"""Golden-master oracle: sb_onset_beat (compiled -DSB_ONSET_V2, production-matching).

Drives the real onset/beat DSP through a fixed, deterministic input trace and
emits one JSON record per frame capturing EVERY public output field. The frozen
capture of this stream (tests/golden/onset_beat.golden.jsonl) is the behaviour
contract: any refactor that changes a number here changed behaviour.

Run standalone to (re)emit the stream:  python oracle_onset_beat.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_hostcompile import host_compile_run  # noqa: E402

NAME = "onset_beat"
MODULE_CPPS = ["sb_onset_beat.cpp"]
DEFINES = ["SB_ONSET_V2"]

# Behaviour-changing edits PROVEN to shift this oracle's golden, spanning distinct
# detector mechanisms (per-band threshold, per-band refractory, transient
# peak-wait). The harness self-test (harness_selftest.py) applies each and asserts
# the golden diverges — proving the oracle is not blind. Verified diverged lines:
# KICK_K=228, KICK_REFR=264, HIHAT_REFR=171, PEAK_WAIT=67.
MUTATIONS = [
    (r"SBV2_KICK_K\s*=\s*0\.8f", "SBV2_KICK_K = 6.0f", "raise kick threshold factor (0.8->6.0)"),
    (r"SBV2_KICK_REFR\s*=\s*6;", "SBV2_KICK_REFR = 12;", "widen kick refractory (6->12 frames)"),
    (r"SBV2_HIHAT_REFR\s*=\s*3;", "SBV2_HIHAT_REFR = 9;", "widen hihat refractory (3->9 frames)"),
    (r"SBV2_PEAK_WAIT\s*=\s*4;", "SBV2_PEAK_WAIT = 16;", "widen transient peak-wait (4->16 frames)"),
]

DRIVER = r"""
#include "sb_onset_beat.h"
#include <cstdio>
#include <cmath>

static void emit(const char* tag, unsigned ms, const SBOnsetBeatEvent& e) {
  std::printf("{\"tag\":\"%s\",\"ms\":%u,\"event_id\":%u,\"event_ms\":%u,\"age\":%u,"
              "\"onset\":%d,\"bass\":%d,\"beat\":%d,\"conf\":%.5f,\"phase\":%.5f,"
              "\"trans\":%.5f,\"kick\":%u,\"hihat\":%u}\n",
              tag, ms,
              (unsigned)e.event_id, (unsigned)e.event_ms, (unsigned)e.event_age_ms,
              (int)e.onset, (int)e.bass_onset, (int)e.beat,
              (double)e.beat_confidence, (double)e.beat_phase, (double)e.transient_strength,
              (unsigned)e.kick_event_id, (unsigned)e.hihat_event_id);
}

static SBAudioSnapshot mk(unsigned ms, bool sil, float bass, float high, float scalar) {
  SBAudioSnapshot a = {};
  a.frame_ms = ms;
  a.silence = sil;
  a.spectral_energy = sil ? 0.0f : 0.3f;
  a.vu_level = sil ? 0.0f : 0.3f;
  for (int i = 0; i < 80; i++) a.spectrum[i] = sil ? 0.0f : 0.02f;
  for (int i = 1; i < 25; i++) a.spectrum[i] = bass > 0.0f ? bass : (sil ? 0.0f : 0.02f);
  for (int i = 70; i < 80; i++) a.spectrum[i] = high > 0.0f ? high : (sil ? 0.0f : 0.02f);
  a.novelty = scalar;
  a.low_energy = bass;
  a.peak_scaled = scalar;
  return a;
}

static void step(const char* tag, unsigned ms, bool sil, float bass, float high, float scalar) {
  SBAudioSnapshot a = mk(ms, sil, bass, high, scalar);
  sb_onset_beat_update(a);
  emit(tag, ms, sb_onset_beat_read());
}

int main() {
  sb_onset_beat_reset();
  unsigned t = 0;
  for (int i = 0; i < 48; i++) { step("warm", t, false, 0, 0, 0); t += 8; }   // fill median ring

  // Dense sustained bass train: builds the per-band flux_mean into the regime
  // where SBV2_KICK_K / SBV2_KICK_ALPHA actually gate firing (so a change to
  // them flips the kick count — i.e. the golden is sensitive to them).
  for (int i = 0; i < 96; i++) {
    bool hit = (i % 3 == 0);
    step(hit ? "bk" : "bq", t, false, hit ? 0.30f : 0.0f, 0, 0); t += 8;
  }
  for (int i = 0; i < 96; i++) {                             // dense sustained hihat train
    bool hit = (i % 3 == 0);
    step(hit ? "hk" : "hq", t, false, 0, hit ? 0.30f : 0.0f, 0); t += 8;
  }
  // Amplitude ramp across the generic-onset threshold (sensitive to THRESH_OFF).
  const float amps[] = {0.03f, 0.05f, 0.08f, 0.12f, 0.18f, 0.27f, 0.40f, 0.60f};
  const int NA = (int)(sizeof(amps) / sizeof(amps[0]));
  for (int i = 0; i < NA; i++) {
    step("kramp", t, false, amps[i], 0, 0); t += 8;
    for (int j = 0; j < 5; j++) { step("kgap", t, false, 0, 0, 0); t += 8; }
  }
  for (int i = 0; i < 30; i++) { step("sil", t, true, 0, 0, 0); t += 8; }     // silence gate
  {                                                          // invalid inputs clamp inert
    SBAudioSnapshot a = mk(t, false, 0, 0, 0);
    a.novelty = NAN; a.low_energy = -5.0f; a.peak_scaled = NAN;
    sb_onset_beat_update(a);
    emit("nan", t, sb_onset_beat_read());
  }
  return 0;
}
"""


def capture(firmware_root=None) -> str:
    rc, out, err = host_compile_run(MODULE_CPPS, DRIVER, defines=DEFINES, firmware_root=firmware_root)
    if rc != 0:
        raise RuntimeError(f"oracle '{NAME}' failed (rc={rc}):\n{err}")
    return out


if __name__ == "__main__":
    sys.stdout.write(capture())
