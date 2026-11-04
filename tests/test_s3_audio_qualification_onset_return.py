"""Actual onset producer regression: empty-spectrum return is not a log attack."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio"
STUB = """#pragma once
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""
CPP = r"""
#include "k1_onset_beat.h"
#include <cstdio>
static unsigned frame = 0;
static int failures = 0;
static void check(bool ok, const char* msg) {
  if (!ok) { std::printf("FAIL: %s\n", msg); ++failures; }
}
static K1OnsetBeatEvent step(float level, bool silent=false) {
  K1AudioSnapshot a = {};
  a.frame_ms = (++frame * 15u) / 2u;
  a.silence = silent; a.nyquist_safe_bin_hi = 71;
  for (int i=0; i<71; ++i) a.spectrum[i] = level;
  a.spectral_energy = level * 71.0f / 80.0f;
  a.low_energy = level; a.vu_level = level;
  k1_onset_beat_update(a); return k1_onset_beat_read();
}
static void recovery(bool explicit_silence) {
  k1_onset_beat_reset(); frame=0;
  for (int i=0; i<100; ++i) step(.10f);
  const auto before = k1_onset_beat_read();
  for (int i=0; i<800; ++i) step(0, explicit_silence);
  check(k1_onset_beat_read().event_id == before.event_id,
        "digital quiet emits no onset");
  for (int i=0; i<8; ++i) step(.10f);
  check(k1_onset_beat_read().event_id == before.event_id,
        "return to a steady spectrum emits no fabricated attack");
  step(.101f); const auto hit = step(.10f);
  check(hit.kick_event_id == before.kick_event_id + 1,
        "real attack immediately after return is detected");
  check(hit.kick && hit.bass_onset, "causal bass trigger follows attack by one hop");
  const auto id = hit.kick_event_id;
  for (int i=0; i<100; ++i) step(.10f);
  check(k1_onset_beat_read().kick_event_id == id,
        "steady programme generates no extra kick");
}
int main() {
  recovery(false); recovery(true);
  k1_onset_beat_reset(); frame=0;
  for(int i=0;i<100;++i) step(.10f);
  step(.101f); const auto hit=step(.10f);
  check(hit.kick_event_id == 1, "continuous programme retains one-hop onset timing");
  return failures ? 1 : 0;
}
"""

def run_replay(source=AUDIO / "k1_onset_beat.cpp"):
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        (work / "Arduino.h").write_text(STUB)
        (work / "main.cpp").write_text(CPP)
        subprocess.run(["clang++", "-std=c++17", "-DK1_ONSET_V2",
                        "-I" + str(work), "-I" + str(AUDIO),
                        str(work / "main.cpp"), str(source), "-o", str(work / "run")],
                       check=True, capture_output=True, text=True)
        return subprocess.run([str(work / "run")], capture_output=True, text=True)

def test_actual_onset_recovers_without_fabricated_attack():
    result = run_replay()
    assert result.returncode == 0, result.stdout + result.stderr
