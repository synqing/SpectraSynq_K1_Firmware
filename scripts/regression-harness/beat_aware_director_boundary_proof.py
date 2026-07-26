#!/usr/bin/env python3
"""BeatAwareDirector beat-boundary proof (host / synthetic fixture).

Proposal 3 host gate: when tempo is locked+confident, every committed switch
must land on a beat tick (beat_quantised=true AND coincident with beat_tick).
When unlocked, switches must use the gentle time fallback (beat_quantised=false).

Compiles the ALWAYS-ON pure decision core (no K1_EFFECT_FRAMEWORK_V1) with a
small C++ driver — same surface as tests/test_beat_aware_director_static.py —
and emits a JSON summary for the audit/control plane.

No device, no flash, no tempo DSP edits.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
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
    // Shorten dwell for a denser fixture without changing production defaults.
    cfg.min_dwell_beats = 8;
    cfg.min_dwell_ms = 2000;
    cfg.fallback_switch_ms = 5000;

    int locked_switches = 0;
    int locked_on_beat = 0;
    int locked_off_beat = 0;
    int unlocked_switches = 0;
    int unlocked_beat_q = 0;

    // Locked 120 BPM stream: beat every 500 ms. Tick every 50 ms for 40 s.
    {
        BeatAwareDirectorState st = {};
        st.current_mode = 7;
        st.initialised = false;
        for (uint32_t t = 0; t < 40000; t += 50) {
            bool beat = (t % 500) == 0;
            BeatAwareAudioView v = view(false, 0.5f, 120.0f, 0.9f, true, beat);
            BeatAwareDecision d = bad_director_decide(&st, v, cfg, t);
            if (d.wants_switch) {
                locked_switches++;
                if (d.beat_quantised && beat) locked_on_beat++;
                else locked_off_beat++;
            }
        }
    }

    // Unlocked energetic stream: no beat ticks, low confidence.
    {
        BeatAwareDirectorState st = {};
        st.current_mode = 7;
        st.initialised = false;
        for (uint32_t t = 0; t < 40000; t += 50) {
            BeatAwareAudioView v = view(false, 0.5f, 0.0f, 0.1f, false, false);
            BeatAwareDecision d = bad_director_decide(&st, v, cfg, t);
            if (d.wants_switch) {
                unlocked_switches++;
                if (d.beat_quantised) unlocked_beat_q++;
            }
        }
    }

    CHECK(locked_switches > 0, "locked stream produces switches");
    CHECK(locked_off_beat == 0, "no locked switch off the beat grid");
    CHECK(locked_on_beat == locked_switches, "all locked switches beat-quantised");
    CHECK(unlocked_switches > 0, "unlocked stream uses time fallback");
    CHECK(unlocked_beat_q == 0, "fallback switches are not beat-quantised");

    // Machine-readable summary for the harness / audit plane.
    printf("BAD_BOUNDARY_PROOF "
           "locked_switches=%d locked_on_beat=%d locked_off_beat=%d "
           "unlocked_switches=%d unlocked_beat_q=%d failures=%d\n",
           locked_switches, locked_on_beat, locked_off_beat,
           unlocked_switches, unlocked_beat_q, failures);

    if (failures == 0) {
        printf("BEAT_AWARE_DIRECTOR_BOUNDARY_OK\n");
        return 0;
    }
    printf("BEAT_AWARE_DIRECTOR_BOUNDARY_FAIL\n");
    return 1;
}
"""


def run_proof() -> dict:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        driver = td_path / "driver.cpp"
        driver.write_text(DRIVER)
        binary = td_path / "bad_boundary_proof"
        cmd = [
            "g++",
            "-std=c++17",
            "-O2",
            "-I",
            str(DIRECTOR_DIR),
            "-I",
            str(AUDIO_DIR),
            "-I",
            str(SYSTEM_DIR),
            str(DIRECTOR_DIR / "beat_aware_director.cpp"),
            str(driver),
            "-o",
            str(binary),
        ]
        compile_res = subprocess.run(
            cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if compile_res.returncode != 0:
            return {
                "status": "FAIL",
                "stage": "compile",
                "stdout": compile_res.stdout,
                "stderr": compile_res.stderr,
            }
        run_res = subprocess.run(
            [str(binary)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        ok = run_res.returncode == 0 and "BEAT_AWARE_DIRECTOR_BOUNDARY_OK" in run_res.stdout
        summary = {
            "status": "PASS" if ok else "FAIL",
            "stage": "host_synthetic",
            "returncode": run_res.returncode,
            "stdout": run_res.stdout.strip(),
            "stderr": run_res.stderr.strip(),
            "device_status": "PENDING_DEVICE",
            "residual": (
                "Host beat-boundary contract PASS. Device VERIFIED PASS still "
                "depends on Proposal 1 tempo lock occupancy + Captain eyes-on "
                "with :beat_director on under k1_bench_im73d_bad / k1_prod_im73d_bad."
            ),
        }
        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write the JSON summary",
    )
    args = parser.parse_args()
    result = run_proof()
    text = json.dumps(result, indent=2)
    print(text)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
