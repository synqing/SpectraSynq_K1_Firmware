#!/usr/bin/env python3
"""Compile and run host-side replay tests for sb_visual_hooks.cpp."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


ARDUINO_STUB = r"""
#pragma once
#include <math.h>
#include <stdint.h>
struct portMUX_TYPE {};
#define portMUX_INITIALIZER_UNLOCKED portMUX_TYPE{}
static inline void portENTER_CRITICAL(portMUX_TYPE*) {}
static inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
"""


HOOKS_HEADER_STUB = r"""
#pragma once
#include <stdint.h>

struct RenderParams {
  float PHOTONS;
  float CHROMA;
};

struct SBOnsetBeatEvent {
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

enum K1EdgeMixerMode : uint8_t {
  K1_EDGE_MIXER_OFF = 0,
  K1_EDGE_MIXER_ANALOGOUS,
};

struct K1EdgeMixerConfig {
  bool enabled;
  K1EdgeMixerMode mode;
  float strength;
};

struct SBVisualHookConfig {
  bool enabled;
  uint32_t event_window_ms;
  uint32_t onset_tau_ms;
  uint32_t bass_tau_ms;
  uint32_t beat_tau_ms;
  float onset_to_photons;
  float bass_to_edge;
  float beat_to_chroma;
  float scalar_ceiling;
};

struct SBVisualHookOutput {
  float photon_scalar;
  float chroma_scalar;
  float edge_scalar;
  bool confirm_switch_boundary;
};

SBVisualHookConfig sb_visual_hooks_config();
void sb_visual_hooks_set_config(const SBVisualHookConfig& config);
SBVisualHookOutput sb_visual_hooks_tick(const SBOnsetBeatEvent& event, uint32_t now_ms);
void sb_visual_hooks_apply_render_params(const SBVisualHookOutput& output, RenderParams* params);
K1EdgeMixerConfig sb_visual_hooks_apply_edge_config(const SBVisualHookOutput& output, K1EdgeMixerConfig config);
"""


CPP_REPLAY = r"""
#include "sb_visual_hooks.h"

#include <cmath>
#include <cstdio>

static int failures = 0;

static void check(bool condition, const char* message) {
  if (!condition) {
    std::printf("FAIL: %s\n", message);
    failures++;
  }
}

static void check_close(float actual, float expected, float tolerance, const char* message) {
  if (std::fabs(actual - expected) > tolerance) {
    std::printf("FAIL: %s actual=%.6f expected=%.6f\n", message, actual, expected);
    failures++;
  }
}

static SBVisualHookConfig enabled_config() {
  SBVisualHookConfig config = {};
  config.enabled = true;
  config.event_window_ms = 80;
  config.onset_tau_ms = 100;
  config.bass_tau_ms = 180;
  config.beat_tau_ms = 250;
  config.onset_to_photons = 0.16f;
  config.bass_to_edge = 0.20f;
  config.beat_to_chroma = 0.12f;
  config.scalar_ceiling = 2.0f;
  return config;
}

static SBOnsetBeatEvent event_base(uint32_t id) {
  SBOnsetBeatEvent event = {};
  event.event_id = id;
  event.event_ms = 100;
  event.event_age_ms = 0;
  return event;
}

static void drain(uint32_t now_ms) {
  SBOnsetBeatEvent empty = {};
  empty.event_age_ms = 1000;
  sb_visual_hooks_tick(empty, now_ms);
}

static void test_onset_routes_to_photons_only() {
  sb_visual_hooks_set_config(enabled_config());
  drain(1000);

  SBOnsetBeatEvent event = event_base(1);
  event.onset = true;
  event.onset_strength = 0.5f;
  SBVisualHookOutput first = sb_visual_hooks_tick(event, 1010);
  check(first.photon_scalar > 1.0f, "onset increases photon scalar");
  check_close(first.chroma_scalar, 1.0f, 0.0001f, "onset does not increase chroma scalar");
  check_close(first.edge_scalar, 1.0f, 0.0001f, "onset does not increase edge scalar");
  check(!first.confirm_switch_boundary, "onset does not confirm switch boundary");

  SBVisualHookOutput repeated = sb_visual_hooks_tick(event, 1020);
  check(repeated.photon_scalar < first.photon_scalar, "same onset event id decays instead of reinjecting");
}

static void test_bass_routes_to_edge_only() {
  drain(1400);

  SBOnsetBeatEvent event = event_base(2);
  event.bass_onset = true;
  event.bass_onset_strength = 0.75f;
  SBVisualHookOutput output = sb_visual_hooks_tick(event, 1410);
  check_close(output.photon_scalar, 1.0f, 0.0001f, "bass does not increase photon scalar");
  check_close(output.chroma_scalar, 1.0f, 0.0001f, "bass does not increase chroma scalar");
  check(output.edge_scalar > 1.0f, "bass increases edge scalar");
  check(!output.confirm_switch_boundary, "bass does not confirm switch boundary");
}

static void test_beat_routes_to_chroma_and_boundary_only() {
  drain(1900);

  SBOnsetBeatEvent event = event_base(3);
  event.beat = true;
  event.beat_confidence = 0.8f;
  SBVisualHookOutput first = sb_visual_hooks_tick(event, 1910);
  check_close(first.photon_scalar, 1.0f, 0.0001f, "beat does not increase photon scalar");
  check(first.chroma_scalar > 1.0f, "beat increases chroma scalar");
  check_close(first.edge_scalar, 1.0f, 0.0001f, "beat does not increase edge scalar");
  check(first.confirm_switch_boundary, "fresh beat confirms switch boundary");

  SBVisualHookOutput repeated = sb_visual_hooks_tick(event, 1920);
  check(!repeated.confirm_switch_boundary, "same beat event id does not reconfirm boundary");
  check(repeated.chroma_scalar < first.chroma_scalar, "same beat event id decays instead of reinjecting");
}

static void test_weaker_fresh_event_does_not_lower_live_pulse() {
  drain(2400);

  SBOnsetBeatEvent strong = event_base(4);
  strong.onset = true;
  strong.onset_strength = 0.9f;
  SBVisualHookOutput first = sb_visual_hooks_tick(strong, 2410);

  SBOnsetBeatEvent weak = event_base(5);
  weak.onset = true;
  weak.onset_strength = 0.1f;
  SBVisualHookOutput second = sb_visual_hooks_tick(weak, 2420);

  check(second.photon_scalar > 1.0f + (0.1f * 0.16f), "weaker fresh onset does not overwrite stronger live pulse");
  check(second.photon_scalar < first.photon_scalar, "stronger pulse still decays after weaker fresh event");
}

static void test_disabled_tick_outputs_baseline_but_decays_state() {
  SBVisualHookConfig config = enabled_config();
  config.enabled = false;
  sb_visual_hooks_set_config(config);

  SBOnsetBeatEvent event = event_base(6);
  event.onset = true;
  event.onset_strength = 1.0f;
  SBVisualHookOutput disabled = sb_visual_hooks_tick(event, 2430);
  check_close(disabled.photon_scalar, 1.0f, 0.0001f, "disabled hook returns baseline photon scalar");
  check_close(disabled.chroma_scalar, 1.0f, 0.0001f, "disabled hook returns baseline chroma scalar");
  check_close(disabled.edge_scalar, 1.0f, 0.0001f, "disabled hook returns baseline edge scalar");
  check(!disabled.confirm_switch_boundary, "disabled hook does not confirm boundary");

  sb_visual_hooks_set_config(enabled_config());
  SBOnsetBeatEvent empty = {};
  empty.event_age_ms = 1000;
  SBVisualHookOutput after = sb_visual_hooks_tick(empty, 3000);
  check_close(after.photon_scalar, 1.0f, 0.0001f, "disabled interval does not preserve stale onset pulse");
}

static void test_config_clamps() {
  SBVisualHookConfig config = {};
  config.enabled = true;
  config.event_window_ms = 80;
  config.onset_tau_ms = 0;
  config.bass_tau_ms = 0;
  config.beat_tau_ms = 0;
  config.onset_to_photons = 3.0f;
  config.bass_to_edge = -1.0f;
  config.beat_to_chroma = 2.0f;
  config.scalar_ceiling = 10.0f;
  sb_visual_hooks_set_config(config);
  SBVisualHookConfig stored = sb_visual_hooks_config();
  check(stored.onset_tau_ms == 1, "onset tau zero clamps to one");
  check(stored.bass_tau_ms == 1, "bass tau zero clamps to one");
  check(stored.beat_tau_ms == 1, "beat tau zero clamps to one");
  check_close(stored.onset_to_photons, 1.0f, 0.0001f, "onset coefficient clamps high");
  check_close(stored.bass_to_edge, 0.0f, 0.0001f, "bass coefficient clamps low");
  check_close(stored.beat_to_chroma, 1.0f, 0.0001f, "beat coefficient clamps high");
  check_close(stored.scalar_ceiling, 4.0f, 0.0001f, "scalar ceiling clamps high");
}

int main() {
  test_onset_routes_to_photons_only();
  test_bass_routes_to_edge_only();
  test_beat_routes_to_chroma_and_boundary_only();
  test_weaker_fresh_event_does_not_lower_live_pulse();
  test_disabled_tick_outputs_baseline_but_decays_state();
  test_config_clamps();
  if (failures != 0) {
    std::printf("VISUAL_HOOKS_REPLAY_FAIL failures=%d\n", failures);
    return 1;
  }
  std::printf("VISUAL_HOOKS_REPLAY_OK cases=6\n");
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
        source_copy = workdir / "sb_visual_hooks.cpp"
        shutil.copy2(next(FIRMWARE.rglob("sb_visual_hooks.cpp")), source_copy)
        (workdir / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
        (workdir / "sb_visual_hooks.h").write_text(HOOKS_HEADER_STUB, encoding="utf-8")
        main_cpp = workdir / "visual_hooks_replay_main.cpp"
        binary = workdir / "visual_hooks_replay"
        main_cpp.write_text(CPP_REPLAY, encoding="utf-8")

        compile_cmd = [
            compiler,
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-I",
            str(workdir),
            str(source_copy),
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
