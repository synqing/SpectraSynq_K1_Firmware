"""Host test for the BeatAwareDirector musical-timing core (P6).

Compiles the ALWAYS-ON pure decision core from beat_aware_director.cpp (the
non-flag-gated portion: bad_director_decide / *_xfade_ms_for_tempo /
*_next_enabled_mode) with a small C++ driver and asserts the four musical-timing
contract properties as pure functions:

  1. BEAT-QUANTISE  — a switch fires only on a beat tick, never mid-phase.
  2. MUSICAL DURATION — crossfade duration is derived from the live tempo
                        (N beats), clamped to the queue's XFADE range.
  3. ENERGY/PHRASE GATE — no switch while silent / below the energy gate.
  4. MIN-DWELL CAP   — a switch never fires before the dwell floor (ms + beats).
  5. FALLBACK        — unlocked tempo switches gently on a time interval, not a
                        beat (beat_quantised == false).

No device, no Arduino. The gated firmware integration is excluded by NOT
defining K1_EFFECT_FRAMEWORK_V1.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
DIRECTOR_DIR = FW / "director"
AUDIO_DIR = FW / "audio"
SYSTEM_DIR = FW / "system"

DRIVER = r"""
#include <cstdint>
#include <cstdio>
#include "beat_aware_director.h"

static int failures = 0;
#define CHECK(cond, msg) do { if(!(cond)){ printf("FAIL: %s\n", msg); failures++; } } while(0)

static BeatAwareAudioView view(bool silence, float energy, float bpm,
                               float conf, bool locked, bool beat) {
    BeatAwareAudioView v;
    v.silence = silence; v.energy_smooth = energy; v.bpm = bpm;
    v.tempo_confidence = conf; v.tempo_locked = locked; v.beat_tick = beat;
    v.music_state = 0;
    return v;
}

int main() {
    BeatAwareDirectorConfig cfg = bad_director_default_config();
    cfg.enabled = true;

    // --- (2) MUSICAL DURATION: N beats at the live tempo, clamped. ----------
    // 120 BPM => 500 ms/beat; xfade_beats=2 => 1000 ms (within [200,1600]).
    CHECK(bad_director_xfade_ms_for_tempo(120.0f, 2, 200, 1600) == 1000,
          "120bpm x2beats == 1000ms");
    // 200 BPM => 300 ms/beat; x2 => 600 ms.
    CHECK(bad_director_xfade_ms_for_tempo(200.0f, 2, 200, 1600) == 600,
          "200bpm x2beats == 600ms");
    // Very slow tempo clamps to the ceiling; unknown tempo -> floor.
    CHECK(bad_director_xfade_ms_for_tempo(40.0f, 2, 200, 1600) == 1600,
          "40bpm x2 clamps to 1600 ceiling");
    CHECK(bad_director_xfade_ms_for_tempo(0.0f, 2, 200, 1600) == 200,
          "unknown tempo -> floor");

    // --- (0) UN-WHITELIST: next enabled mode, no immediate repeat. -----------
    uint8_t nxt = bad_director_next_enabled_mode(7);
    CHECK(nxt != 7, "next enabled mode is not the same mode");

    // --- (3) ENERGY/PHRASE GATE: silence + below-gate never switch. ---------
    {
        BeatAwareDirectorState st = {}; st.current_mode = 7; st.initialised = false;
        // Long-running silent stream with beats present: must never switch.
        bool switched = false;
        for (uint32_t t = 0; t < 60000; t += 100) {
            BeatAwareAudioView v = view(true, 0.0f, 120.0f, 0.9f, true, (t % 500) == 0);
            BeatAwareDecision d = bad_director_decide(&st, v, cfg, t);
            if (d.wants_switch) switched = true;
        }
        CHECK(!switched, "no switch during silence");
    }
    {
        BeatAwareDirectorState st = {}; st.current_mode = 7; st.initialised = false;
        bool switched = false;
        for (uint32_t t = 0; t < 60000; t += 100) {
            // Energy below the gate (0.06) but audible: still gated off.
            BeatAwareAudioView v = view(false, 0.02f, 120.0f, 0.9f, true, (t % 500) == 0);
            BeatAwareDecision d = bad_director_decide(&st, v, cfg, t);
            if (d.wants_switch) switched = true;
        }
        CHECK(!switched, "no switch below energy gate");
    }

    // --- (1)+(4) BEAT-QUANTISE + MIN-DWELL: a lively locked stream switches  -
    // only ON a beat and never before the dwell floor. ----------------------
    {
        BeatAwareDirectorState st = {}; st.current_mode = 7; st.initialised = false;
        uint8_t mode0 = 7;
        int switch_count = 0;
        uint32_t first_switch_ms = 0;
        bool any_non_beat_switch = false;
        // 120 BPM => beat every 500 ms. Tick every 100 ms for 120 s.
        for (uint32_t t = 0; t < 120000; t += 100) {
            bool beat = (t % 500) == 0;
            BeatAwareAudioView v = view(false, 0.5f, 120.0f, 0.9f, true, beat);
            BeatAwareDecision d = bad_director_decide(&st, v, cfg, t);
            if (d.wants_switch) {
                if (first_switch_ms == 0) first_switch_ms = t;
                if (!d.beat_quantised) any_non_beat_switch = true;
                if (!beat) any_non_beat_switch = true;  // must coincide with a beat
                switch_count++;
            }
        }
        CHECK(switch_count > 0, "lively locked stream produces switches");
        CHECK(!any_non_beat_switch, "every switch is beat-quantised (on a beat tick)");
        // Dwell floor: min_dwell_ms=6000 AND min_dwell_beats=32 (=> 16000ms @120bpm).
        // So the first switch cannot land before ~16 s.
        CHECK(first_switch_ms >= 16000, "first switch respects beat dwell cap");
    }

    // --- (5) FALLBACK: unlocked tempo switches gently on time, not a beat. ---
    {
        BeatAwareDirectorState st = {}; st.current_mode = 7; st.initialised = false;
        bool switched = false;
        bool any_beat_quantised = false;
        for (uint32_t t = 0; t < 60000; t += 100) {
            // Audible, energetic, but tempo NOT locked / low confidence.
            BeatAwareAudioView v = view(false, 0.5f, 0.0f, 0.0f, false, false);
            BeatAwareDecision d = bad_director_decide(&st, v, cfg, t);
            if (d.wants_switch) { switched = true; if (d.beat_quantised) any_beat_quantised = true; }
        }
        CHECK(switched, "unlocked stream still switches (time fallback)");
        CHECK(!any_beat_quantised, "fallback switches are NOT beat-quantised");
    }

    // --- (6) LOCKED + LOW CONF: hold — never time-fallback while locked. -----
    // Autopsy 2026-07-25: locked_beat_q_bad when conf < floor took fallback.
    {
        BeatAwareDirectorState st = {}; st.current_mode = 7; st.initialised = false;
        bool switched = false;
        for (uint32_t t = 0; t < 60000; t += 100) {
            bool beat = (t % 500) == 0;
            // Locked but confidence below floor (0.45).
            BeatAwareAudioView v = view(false, 0.5f, 127.0f, 0.30f, true, beat);
            BeatAwareDecision d = bad_director_decide(&st, v, cfg, t);
            if (d.wants_switch) switched = true;
        }
        CHECK(!switched, "locked+low-conf must HOLD (no time fallback)");
    }

    if (failures == 0) {
        printf("BEAT_AWARE_DIRECTOR_OK checks=all\n");
        return 0;
    }
    printf("BEAT_AWARE_DIRECTOR_FAIL failures=%d\n", failures);
    return 1;
}
"""


class BeatAwareDirectorStaticTest(unittest.TestCase):
    def test_musical_timing_core(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            driver = td / "driver.cpp"
            driver.write_text(DRIVER)
            binary = td / "bad_test"
            cmd = [
                "g++", "-std=c++17", "-O2",
                "-I", str(DIRECTOR_DIR),
                "-I", str(AUDIO_DIR),
                "-I", str(SYSTEM_DIR),
                str(DIRECTOR_DIR / "beat_aware_director.cpp"),
                str(driver),
                "-o", str(binary),
            ]
            compile_res = subprocess.run(
                cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.assertEqual(
                compile_res.returncode, 0,
                "compile failed:\n" + compile_res.stdout + compile_res.stderr,
            )
            run_res = subprocess.run(
                [str(binary)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.assertEqual(
                run_res.returncode, 0,
                "run failed:\n" + run_res.stdout + run_res.stderr,
            )
            self.assertIn("BEAT_AWARE_DIRECTOR_OK", run_res.stdout)


if __name__ == "__main__":
    unittest.main()
