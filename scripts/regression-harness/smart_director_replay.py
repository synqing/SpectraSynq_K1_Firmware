#!/usr/bin/env python3
"""Compile and run host-side replay tests for sb_smart_director.cpp."""

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
  LIGHT_MODE_AURORA,
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

enum SBMusicState : uint8_t {
  SB_MUSIC_SILENCE = 0,
  SB_MUSIC_AMBIENT,
  SB_MUSIC_STEADY,
  SB_MUSIC_BUILD,
  SB_MUSIC_DROP,
  SB_MUSIC_BREAKDOWN,
  SB_MUSIC_DENSE
};

struct SBAudioSnapshot {
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
"""


MODE_SELECTION_STUB = r"""
#pragma once
#include <stdint.h>
#include "config_types.h"

enum SBModeIntentReason : uint8_t {
  SB_MODE_REASON_HOLD = 0,
  SB_MODE_REASON_SILENCE,
  SB_MODE_REASON_AMBIENT,
  SB_MODE_REASON_STEADY,
  SB_MODE_REASON_BUILD,
  SB_MODE_REASON_DROP,
  SB_MODE_REASON_BREAKDOWN,
  SB_MODE_REASON_DENSE,
  SB_MODE_REASON_MANUAL_OWNERSHIP,
  SB_MODE_REASON_COOLDOWN,
  SB_MODE_REASON_DENIED
};

struct SBModeIntent {
  uint8_t requested_mode;
  SBModeIntentReason reason;
  float confidence;
  bool wants_switch;
};

struct SBModeSelectionConfig {
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
#include "sb_audio_snapshot.h"
#include "sb_mode_selection.h"

struct SBSmartDirectorConfig {
  bool enabled;
  bool assist_switching_enabled;
  bool director_autonomy_enabled;
  float confidence_floor;
  uint32_t min_dwell_ms;
  uint32_t cooldown_ms;
  uint32_t switch_window_ms;
  uint8_t max_switches_per_window;
};

struct SBSmartDirectorOutput {
  SBMusicState state;
  SBModeIntent mode_intent;
  float speed_scalar;
  float photons_scalar;
  float chroma_scalar;
  float saturation_scalar;
  bool palette_overlay_enabled;
  uint8_t palette_index;
  bool auto_colour_shift;
};

enum SBSmartManualControlReason : uint8_t {
  SB_MANUAL_REASON_NONE = 0,
  SB_MANUAL_REASON_SERIAL_HOTKEY,
  SB_MANUAL_REASON_SERIAL_COMMAND,
  SB_MANUAL_REASON_ENCODER
};

void sb_smart_director_init();
SBSmartDirectorOutput sb_smart_director_tick(
  const SBAudioSnapshot& audio,
  uint32_t now_ms,
  const SBOnsetBeatEvent* event = nullptr
);
SBSmartDirectorOutput sb_smart_director_read_output();
void sb_smart_director_apply_render_params(const SBSmartDirectorOutput& output, RenderParams* params);
SBSmartDirectorConfig sb_smart_director_config();
void sb_smart_director_set_config(const SBSmartDirectorConfig& config);
SBModeSelectionConfig sb_smart_director_mode_selection_config(uint32_t now_ms);
void sb_smart_director_mark_manual_control(uint32_t now_ms, SBSmartManualControlReason reason);
void sb_smart_director_clear_manual_control();
bool sb_smart_director_manual_owner_active(uint32_t now_ms);
"""


GLOBALS_STUB = r"""
#pragma once
#include <stdint.h>
extern bool mode_transition_queued;
extern int mode_destination;
extern uint32_t g_last_encoder_activity_time;
"""


CPP_REPLAY = r"""
#include "sb_smart_director.h"

#include <cmath>
#include <cstdio>

bool mode_transition_queued = false;
int mode_destination = -1;
uint32_t g_last_encoder_activity_time = 0;

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

static SBAudioSnapshot audio(uint32_t ms, float spectral, float novelty, float peak,
                             float low, float mid, float high, bool silence = false) {
  SBAudioSnapshot snapshot = {};
  snapshot.frame_ms = ms;
  snapshot.spectral_energy = spectral;
  snapshot.novelty = novelty;
  snapshot.peak_scaled = peak;
  snapshot.low_energy = low;
  snapshot.mid_energy = mid;
  snapshot.high_energy = high;
  snapshot.silence = silence;
  return snapshot;
}

static SBOnsetBeatEvent music_event(uint32_t ms, bool onset, bool bass_onset, bool beat,
                                    float onset_strength, float bass_strength,
                                    float beat_confidence) {
  SBOnsetBeatEvent event = {};
  event.event_id = ms;
  event.event_ms = ms;
  event.onset = onset;
  event.bass_onset = bass_onset;
  event.beat = beat;
  event.onset_strength = onset_strength;
  event.bass_onset_strength = bass_strength;
  event.beat_confidence = beat_confidence;
  return event;
}

static SBSmartDirectorConfig config(bool enabled, bool switching, bool autonomy, float floor = 0.08f) {
  SBSmartDirectorConfig c = {};
  c.enabled = enabled;
  c.assist_switching_enabled = switching;
  c.director_autonomy_enabled = autonomy;
  c.confidence_floor = floor;
  c.min_dwell_ms = 12000;
  c.cooldown_ms = 12000;
  c.switch_window_ms = 90000;
  c.max_switches_per_window = 3;
  return c;
}

static void reset(bool enabled, bool switching, bool autonomy, float floor = 0.08f) {
  mode_transition_queued = false;
  mode_destination = -1;
  g_last_encoder_activity_time = 0;
  sb_smart_director_init();
  sb_smart_director_set_config(config(enabled, switching, autonomy, floor));
}

static void test_disabled_is_materially_inert() {
  reset(false, false, false);
  SBSmartDirectorOutput output = sb_smart_director_tick(audio(1000, 0.80f, 0.85f, 0.90f, 0.6f, 0.5f, 0.4f), 1000);
  check(!output.mode_intent.wants_switch, "disabled Smart does not request a switch");
  check_close(output.speed_scalar, 1.0f, 0.0001f, "disabled Smart keeps speed scalar neutral");
  check_close(output.photons_scalar, 1.0f, 0.0001f, "disabled Smart keeps photons scalar neutral");
  check_close(output.chroma_scalar, 1.0f, 0.0001f, "disabled Smart keeps chroma scalar neutral");
  check_close(output.saturation_scalar, 1.0f, 0.0001f, "disabled Smart keeps saturation scalar neutral");
  check(!output.palette_overlay_enabled, "disabled Smart does not emit palette overlay");
}

static void test_assist_drop_switches_without_palette_overlay() {
  reset(true, true, false);
  sb_smart_director_tick(audio(1000, 0.08f, 0.04f, 0.04f, 0.02f, 0.02f, 0.02f), 1000);
  SBSmartDirectorOutput output = sb_smart_director_tick(audio(1250, 0.80f, 0.82f, 0.90f, 0.55f, 0.45f, 0.35f), 1250);
  check(output.state == SB_MUSIC_DROP, "drop snapshot classifies as drop");
  check(output.mode_intent.requested_mode == LIGHT_MODE_COMET, "drop maps to Comet (kick tracker)");
  check(output.mode_intent.wants_switch, "drop wants bounded mode switch when confidence clears floor");
  check(output.speed_scalar > 1.0f, "drop increases speed/mood scalar");
  check(output.photons_scalar > 1.0f, "drop increases photons scalar");
  check(output.chroma_scalar > 1.0f, "drop increases chroma scalar");
  check(output.saturation_scalar > 1.0f, "drop increases saturation scalar");
  check(!output.palette_overlay_enabled, "plain Assist does not own palette overlay");
}

static void test_autonomy_drop_adds_frame_local_palette_overlay() {
  reset(true, true, true);
  sb_smart_director_tick(audio(2000, 0.08f, 0.04f, 0.04f, 0.02f, 0.02f, 0.02f), 2000);
  SBSmartDirectorOutput output = sb_smart_director_tick(audio(2250, 0.80f, 0.82f, 0.90f, 0.55f, 0.45f, 0.35f), 2250);
  check(output.palette_overlay_enabled, "director autonomy enables palette overlay");
  check(output.palette_index == 24, "drop maps to fire palette");
  check(output.auto_colour_shift, "drop enables transient auto-colour phase");

  RenderParams params = {};
  params.PHOTONS = 0.50f;
  params.CHROMA = 0.50f;
  params.MOOD = 0.25f;
  params.SATURATION = 0.70f;
  params.PALETTE_MODE_ENABLED = false;
  params.PALETTE_INDEX = 29;
  params.AUTO_COLOR_SHIFT = false;
  sb_smart_director_apply_render_params(output, &params);
  check(params.PHOTONS > 0.50f, "render params photons are modulated");
  check(params.CHROMA > 0.50f, "render params chroma are modulated");
  check(params.MOOD > 0.25f, "render params mood/speed are modulated");
  check(params.SATURATION > 0.70f, "render params saturation is modulated");
  check(params.PALETTE_MODE_ENABLED, "palette overlay is render-param local");
  check(params.PALETTE_INDEX == 24, "render params carry palette index overlay");
  check(params.AUTO_COLOR_SHIFT, "render params carry auto-colour overlay");
}

static void test_autonomy_steady_uses_deliberate_demo_policy() {
  reset(true, true, false);
  SBSmartDirectorOutput reference = sb_smart_director_tick(audio(8000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f), 8000);
  check(reference.mode_intent.requested_mode == LIGHT_MODE_SPECTRUM_RIVER, "reference steady maps to Spectrum River");
  check(reference.palette_index == 29, "reference steady maps to palette 29");

  reset(true, true, true);
  SBSmartDirectorOutput first = sb_smart_director_tick(audio(10000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f), 10000);
  SBSmartDirectorOutput second = sb_smart_director_tick(audio(19000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f), 19000);
  SBSmartDirectorOutput third = sb_smart_director_tick(audio(35000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f), 35000);
  check(first.state == SB_MUSIC_STEADY, "steady snapshot classifies as steady");
  check(second.state == SB_MUSIC_STEADY, "steady follow-up remains steady");
  check(third.state == SB_MUSIC_STEADY, "third steady sample remains steady");
  check(first.mode_intent.requested_mode != LIGHT_MODE_SPECTRUM_RIVER &&
        second.mode_intent.requested_mode != LIGHT_MODE_SPECTRUM_RIVER &&
        third.mode_intent.requested_mode != LIGHT_MODE_SPECTRUM_RIVER,
        "autonomy steady avoids the assist reference (Spectrum River) across the policy");
  check(first.mode_intent.requested_mode == second.mode_intent.requested_mode,
        "autonomy steady holds mode inside a 20-30s trajectory");
  check(third.mode_intent.requested_mode != first.mode_intent.requested_mode,
        "autonomy steady still has a deliberate long-arc transition");
  check(first.palette_overlay_enabled, "autonomy steady owns palette overlay");
  check(first.palette_index != 29 && second.palette_index != 29 && third.palette_index != 29,
        "autonomy steady avoids reference palette 29 across the policy");
  check(first.palette_index == second.palette_index,
        "autonomy steady holds palette inside a 20-30s trajectory");
  check(third.palette_index != first.palette_index,
        "autonomy steady has a deliberate long-arc palette transition");
  check(!first.auto_colour_shift, "autonomy steady avoids auto-colour washout");
}

static void test_autonomy_drop_gets_intentional_high_energy_trajectory() {
  reset(true, true, true, 0.07f);
  sb_smart_director_tick(audio(2000, 0.08f, 0.04f, 0.04f, 0.02f, 0.02f, 0.02f), 2000);
  SBSmartDirectorOutput early = sb_smart_director_tick(audio(2250, 0.80f, 0.82f, 0.90f, 0.55f, 0.45f, 0.35f), 2250);
  SBSmartDirectorOutput late = sb_smart_director_tick(audio(26500, 0.80f, 0.82f, 0.90f, 0.55f, 0.45f, 0.35f), 26500);
  check(early.state == SB_MUSIC_DROP, "drop snapshot classifies as drop");
  check(late.state == SB_MUSIC_DROP, "late drop snapshot remains drop");
  check(early.mode_intent.requested_mode == LIGHT_MODE_COMET, "early drop maps to Comet kick impact");
  check(late.mode_intent.requested_mode == LIGHT_MODE_BLOOM_FAST, "late drop maps to Bloom Fast trajectory");
  check(early.palette_index == 24, "early drop uses fire palette");
  check(late.palette_index == 31, "late drop uses compressed heat palette");
  check(early.auto_colour_shift && late.auto_colour_shift, "drop owns bounded auto-colour phase");
  check(early.mode_intent.wants_switch && late.mode_intent.wants_switch, "drop clears the demo confidence floor");
}

static void test_autonomy_sparse_build_lifts_without_colour_washout() {
  reset(true, true, true, 0.07f);
  sb_smart_director_tick(audio(5000, 0.10f, 0.05f, 0.12f, 0.04f, 0.04f, 0.02f), 5000);
  SBSmartDirectorOutput output = sb_smart_director_tick(audio(5500, 0.42f, 0.36f, 0.46f, 0.20f, 0.18f, 0.10f), 5500);
  check(output.state == SB_MUSIC_BUILD, "sparse/build snapshot classifies as build");
  check(output.mode_intent.requested_mode == LIGHT_MODE_WAVEFORM_HYBRID, "build maps to controlled Waveform Hybrid");
  check(output.palette_index == 29, "build starts from visible lift palette");
  check(output.photons_scalar > 1.0f, "build increases photons");
  check(output.chroma_scalar > 1.0f, "build increases chroma");
  check(output.saturation_scalar <= 1.04f, "build saturation lift stays bounded");
  check(output.auto_colour_shift, "build can own bounded auto-colour phase");
}

static void test_confidence_floor_blocks_switch_but_not_scalar_policy() {
  reset(true, true, true, 1.0f);
  sb_smart_director_tick(audio(3000, 0.08f, 0.04f, 0.04f, 0.02f, 0.02f, 0.02f), 3000);
  SBSmartDirectorOutput output = sb_smart_director_tick(audio(3250, 0.60f, 0.30f, 0.45f, 0.30f, 0.30f, 0.20f), 3250);
  check(!output.mode_intent.wants_switch, "confidence floor blocks switching");
  check(output.speed_scalar != 1.0f || output.photons_scalar != 1.0f || output.chroma_scalar != 1.0f,
        "scalar modulation remains explicit when switch is blocked");
}

static void test_scene_boundary_requires_music_event_when_event_stream_is_present() {
  reset(true, true, true, 0.07f);
  SBOnsetBeatEvent confirmed = music_event(10000, true, false, true, 0.34f, 0.05f, 0.28f);
  SBOnsetBeatEvent quiet = music_event(35000, false, false, false, 0.0f, 0.0f, 0.0f);
  SBSmartDirectorOutput first = sb_smart_director_tick(
    audio(10000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f),
    10000,
    &confirmed
  );
  SBSmartDirectorOutput held = sb_smart_director_tick(
    audio(35000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f),
    35000,
    &quiet
  );
  check(first.mode_intent.requested_mode == held.mode_intent.requested_mode,
        "event-present autonomy holds trajectory when boundary is not confirmed");
  check(!held.mode_intent.wants_switch, "event-present autonomy suppresses switch without boundary event");
}

static void test_scene_boundary_advances_on_confirmed_music_event() {
  reset(true, true, true, 0.07f);
  SBOnsetBeatEvent first_event = music_event(10000, true, false, true, 0.30f, 0.05f, 0.24f);
  SBOnsetBeatEvent next_event = music_event(35000, false, true, true, 0.05f, 0.32f, 0.30f);
  SBSmartDirectorOutput first = sb_smart_director_tick(
    audio(10000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f),
    10000,
    &first_event
  );
  SBSmartDirectorOutput advanced = sb_smart_director_tick(
    audio(35000, 0.18f, 0.05f, 0.24f, 0.10f, 0.10f, 0.05f),
    35000,
    &next_event
  );
  check(first.mode_intent.requested_mode != advanced.mode_intent.requested_mode,
        "confirmed event advances the 20-30s scene trajectory");
  check(first.palette_index != advanced.palette_index,
        "confirmed event advances the palette trajectory");
}

static void test_low_energy_false_onset_stays_idle_in_autonomy() {
  reset(true, true, true, 0.07f);
  SBOnsetBeatEvent false_onset = music_event(90000, true, true, true, 0.60f, 0.45f, 0.40f);
  SBSmartDirectorOutput output = sb_smart_director_tick(
    audio(90000, 0.02f, 0.10f, 0.05f, 0.01f, 0.01f, 0.01f),
    90000,
    &false_onset
  );
  check(output.state == SB_MUSIC_SILENCE, "low-energy false onset is treated as idle scene input");
  check(output.mode_intent.requested_mode == LIGHT_MODE_BLOOM, "low-energy false onset stays on Bloom");
  check(!output.palette_overlay_enabled, "low-energy false onset does not own palette overlay");
  check(!output.mode_intent.wants_switch, "low-energy false onset does not request a scene switch");
}

static void test_manual_owner_surfaces_in_mode_selection_config() {
  reset(true, true, true);
  sb_smart_director_mark_manual_control(4000, SB_MANUAL_REASON_SERIAL_COMMAND);
  check(sb_smart_director_manual_owner_active(4500), "recent serial command marks manual owner active");
  SBModeSelectionConfig selection = sb_smart_director_mode_selection_config(4500);
  check(selection.enabled, "selection remains enabled for downstream resolver");
  check(selection.manual_owner_active, "selection config exposes manual owner gate");
  check(selection.min_dwell_ms == 12000, "selection config carries dwell");
  check(selection.cooldown_ms == 12000, "selection config carries cooldown");
  check(selection.switch_window_ms == 90000, "selection config carries switch window");
  check(selection.max_switches_per_window == 3, "selection config carries rate limit");
  sb_smart_director_clear_manual_control();
  check(!sb_smart_director_manual_owner_active(4500), "smart scene can explicitly hand ownership back to Smart");
}

static void test_silence_never_owns_palette_overlay() {
  reset(true, true, true);
  SBSmartDirectorOutput output = sb_smart_director_tick(audio(14000, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, true), 14000);
  check(output.state == SB_MUSIC_SILENCE, "silence classifies as silence");
  check(!output.palette_overlay_enabled, "silence does not emit palette overlay");
  check(!output.mode_intent.wants_switch || output.mode_intent.requested_mode == LIGHT_MODE_BLOOM,
        "silence does not request a non-idle smart mode");
}

int main() {
  test_disabled_is_materially_inert();
  test_assist_drop_switches_without_palette_overlay();
  test_autonomy_drop_adds_frame_local_palette_overlay();
  test_autonomy_steady_uses_deliberate_demo_policy();
  test_autonomy_drop_gets_intentional_high_energy_trajectory();
  test_autonomy_sparse_build_lifts_without_colour_washout();
  test_confidence_floor_blocks_switch_but_not_scalar_policy();
  test_scene_boundary_requires_music_event_when_event_stream_is_present();
  test_scene_boundary_advances_on_confirmed_music_event();
  test_low_energy_false_onset_stays_idle_in_autonomy();
  test_manual_owner_surfaces_in_mode_selection_config();
  test_silence_never_owns_palette_overlay();
  if (failures != 0) {
    std::printf("SMART_DIRECTOR_REPLAY_FAIL failures=%d\n", failures);
    return 1;
  }
  std::printf("SMART_DIRECTOR_REPLAY_OK cases=12\n");
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
        source_copy = workdir / "sb_smart_director.cpp"
        shutil.copy2(next(FIRMWARE.rglob("sb_smart_director.cpp")), source_copy)
        (workdir / "Arduino.h").write_text(ARDUINO_STUB, encoding="utf-8")
        (workdir / "config_types.h").write_text(CONFIG_TYPES_STUB, encoding="utf-8")
        (workdir / "sb_audio_snapshot.h").write_text(AUDIO_SNAPSHOT_STUB, encoding="utf-8")
        (workdir / "sb_mode_selection.h").write_text(MODE_SELECTION_STUB, encoding="utf-8")
        (workdir / "render_params.h").write_text(RENDER_PARAMS_STUB, encoding="utf-8")
        (workdir / "sb_smart_director.h").write_text(SMART_DIRECTOR_HEADER_STUB, encoding="utf-8")
        (workdir / "globals.h").write_text(GLOBALS_STUB, encoding="utf-8")
        main_cpp = workdir / "smart_director_replay_main.cpp"
        binary = workdir / "smart_director_replay"
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
