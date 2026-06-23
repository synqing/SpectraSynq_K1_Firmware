# Smart Visual Engine E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the K1 Smart Visual Engine as five bounded product functions: EdgeMixer-lite, SynqMatrix Assist mode selection plus parameter modulation, onset/beat event extraction, beat-gated visual hooks, and later Director autonomy.

**Architecture:** Do not bulk-port donor `ControlBus`, `RendererActor`, REST/WS, NVS, PipelineCore, or donor effect registry. Extract the perceptual primitives into SB-native modules: AP creates a compact audio snapshot, a smart director classifies state and emits bounded mode intent plus `RenderParams` modulation, VP applies the selected mode and optional secondary colour differentiation, and beat/onset events later improve hit-lock and switch timing. Assist includes mode switching; Director means broader autonomy beyond Assist's bounded allow-list.

**Tech Stack:** ESP32-S3 Arduino / PlatformIO, FastLED 3.10.3, existing `CRGB16`/`SQ15x16`, existing `RenderParams`, Python `unittest` static gates, PlatformIO `k1_hardware` / `k1_hardware_harness` / `k1_hardware_trace_dev`.

## 2026-05-28 Execution Status

**Implemented/build-proven/hardware-exercised in this phase:**

- `SBAudioSnapshot` cross-core AP scalar publication.
- `SBOnsetBeat` novelty/bass-onset event lane and beat-confidence scalar.
- `SBSmartDirectorAssist` bounded mode switching plus `RenderParams` modulation.
- `SBVisualHooks` event-age gated primary pulse, EdgeMixer strength scalar, and switch-boundary confirmation.
- `SBEdgeMixerLite` secondary-only colour-interest transform.
- Typed colon-framed primary visual controls: `photons`, `chroma`, `mood`, `palette_mode`, `palette_index`.
- Runtime script restore/reference state: primary Bloom mode 3, primary mood `0.250`, primary palette 29, secondary Waveform Fast mode 7, secondary palette 24, Smart off, Edge off, Smart confidence floor `0.080`.

**Evidence captured:**

- Host tests: `python3 -B -m unittest discover -s tests` passed with `69` tests.
- Build targets: `k1_hardware`, `k1_hardware_harness`, and `k1_bench_reference` passed after typed-control changes.
- Trace-dev compile check: `k1_hardware_trace_dev` passed as a non-shippable build lane.
- Main K1 `/dev/tty.usbmodem101` flashed with `k1_hardware`.
- Bench K1 `/dev/tty.usbmodem2101` flashed with `k1_bench_reference`.
- VPABB/VPABC product-floor proof: `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-context-product-floor-v2-summary.json`.
- Full VPABB/VPABC proof: `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-v1-summary.json`.
- Final production/reference-state proof: `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-smart-edge-reference-state-v2.log` and `docs/forensics/runtime-evidence/2026-05-28-k1-bench-reference-production-smart-edge-reference-state-v2.log`.
- Final restored production proof: `docs/forensics/runtime-evidence/2026-05-28-k1-main-production-final-restore-v1.log` and `docs/forensics/runtime-evidence/2026-05-28-k1-bench-production-final-restore-v1.log`.
- Final restored parsed summaries: `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-final-main-restore-v1-summary.json` and `docs/forensics/runtime-evidence/2026-05-28-k1-smart-edge-full-test-final-bench-restore-v1-summary.json`.
- Decision/checkpoint doc: `docs/forensics/2026-05-28-smart-edge-forced-floor-runtime-evidence.md`.

**Full-test close-out:**

- Main K1 was restored from the temporary harness image to production `k1_hardware`.
- Bench K1 was re-flashed with `k1_bench_reference`.
- Final production captures completed after restore: main `662` lines / `AP=36`; bench `646` lines / `AP=20`.
- Harness final-byte proof reported no visual safety failures, Smart primary mode counts `3:13` and `8:11`, and `dropped=0` / `overflowed=0`.
- Final restored production logs on both devices ended with Bloom mode 3, palette 29, secondary Waveform Fast mode 7, secondary palette 24, Smart off, Edge off, and Smart confidence floor `0.080`.

**Explicitly not promoted:**

- `SBDirectorAutonomy` remains deferred. The plan's own prerequisite is accepted Assist/Edge/Onset/Hook proof plus Captain visual judgement. The current evidence proves the mechanism runs and switches on hardware; it does not prove a broader autonomous policy is perceptually better than Assist.

---

## Scope Interpretation

Captain asked for the "full e2e execution plan for all 4 functions previously listed + the updated SynqMatrix Assist". This plan treats the implementation as five execution functions so no capability is lost:

1. `SBEdgeMixerLite`: secondary-channel colour differentiation and edge interest.
2. `SBSmartDirectorAssist`: music-state classification, bounded mode switching, and parameter modulation.
3. `SBOnsetBeat`: AP-side onset and beat semantic events.
4. `SBBeatVisualHooks`: event-gated visual accents and Assist switch-boundary confirmation.
5. `SBDirectorAutonomy`: broader auto behaviour after Assist switching and event quality are proven.

## Firmware Gate Output

Current truth:

- Active repo: `/Users/spectrasynq/SensoryBridge-main 9`.
- Current observed branch during the research pass: `feat/gdft-harness`, dirty tree.
- Current production env: `k1_hardware`.
- Current build filter includes `.ino`, `globals_config.cpp`, `globals.cpp`, `Palettes.cpp`, `render_params.cpp`, and `light_mode_*.cpp`. It does not include future `sb_*.cpp` files.
- Last-known-safe rollback anchor is `9423ea0`, recorded in `docs/forensics/2026-05-27-last-known-safe-pre-refactor-state.md`.

Change class:

- Multi-file AP/VP/render/LED-output feature work.
- Build-system change class for adding product `sb_*.cpp` modules to PlatformIO.
- Serial/control-surface change only if Captain approves typed runtime controls after kernel proof.

Files/seams touched:

- AP seam: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` after `process_GDFT()` / `calculate_novelty()`.
- VP seam: primary render selection and `RenderParams` stack in `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`.
- Secondary output seam: `leds_16_secondary` after `store_render_channel_output()` and before `clip_led_values()`.
- Build seam: `platformio.ini` build filter.
- Static tests: `tests/test_smart_visual_engine_static.py`.
- Runtime evidence parsing: existing `scripts/regression-harness/vpab_gate.py`; new parsers only if the emitted evidence format changes.

Known breakage avoided:

- No donor `ControlBusFrame` or `RendererActor` import.
- No donor REST/WS/STA/NVS import.
- No `start_noise_cal` or silence assumption.
- No render heap, `String`, dynamic containers, or blocking I/O.
- No persistent `CONFIG.LIGHTSHOW_MODE` mutation inside render.
- No linear sweeps or rainbow/default hue-wheel behaviour.
- No secondary state bleed through shared statics.
- No dev instrumentation in production envs.

State ownership:

- AP owns `SBAudioSnapshot` and `SBOnsetBeatEvent`.
- Director owns state classification, confidence, mode intent, and assist scalar output.
- `ModeSelectionGate` owns applied-mode selection, dwell/cooldown/rate limit, and manual/show ownership.
- VP owns per-frame `RenderParams` overlay and render output.
- EdgeMixer owns secondary CRGB16 colour transform only.

Runtime proof required:

- Compile proof for `k1_hardware` and `k1_hardware_harness`.
- Static proof that production env excludes diagnostic/dev-only code and that smart visual render paths allocate no heap.
- VPAB/final-byte A/B captures for EdgeMixer-lite, Assist mode switching, and beat-gated hooks.
- AP event logs for onset/beat false positives, event age, and confidence.
- Captain visual smoke on reference effects.
- MabuTrace `k1_hardware_trace_dev` only for timeline/causality claims; it remains non-shippable.

Minimal edit plan:

- Add small SB-native modules under `SPECTRASYNQ_K1_FIRMWARE/sb_*.h/.cpp`.
- Add `+<sb_*.cpp>` to the build filter after files exist.
- Integrate AP snapshot update after novelty is calculated.
- Integrate primary applied-mode selection before `render_lightshow_for_channel(...)`.
- Integrate EdgeMixer-lite after secondary render store and before secondary clipping.
- Keep all runtime controls typed and non-destructive if Captain approves control-surface exposure.

Explicit non-goals:

- No donor architecture migration.
- No web/API work.
- No calibration change.
- No AP sample-rate/I2S/GDFT rewrite.
- No full Director autonomy until Assist switching is proven.
- No automatic persistence of smart-selected modes.

Stop conditions:

- The feature needs serial access by the agent.
- The feature needs `start_noise_cal` or a silence-window assumption.
- The feature requires widening existing VP/AP tolerances to pass.
- The feature touches `i2s_audio.h`, `GDFT.h`, `noise_cal.h`, or destructive serial commands.
- Assist switching looks random or weakens Bloom/Waveform motion memory.
- A production build contains MabuTrace, diagnostic capture, VPAB capture, or trace-dev flags.

## Perception-First Gates

| Function | Mechanism | Perceived output | Collapse points | Survival paths | Simpler alternative | Materiality threshold | Decision |
|---|---|---|---|---|---|---|---|
| EdgeMixer-lite | Secondary CRGB16 colour matrix / veil / centre mask | More LGP depth and edge interest | WS2812 final bytes, gamma/dither, wrong donor centre LUT | Secondary final-byte changes before quantisation | Centre-corrected secondary hue/saturation/veil transform | >= 5 percent of nonblack secondary pixels change by >= 2 final-byte LSB, no primary mutation | Build SB-native, default-off, then A/B |
| SynqMatrix Assist | Music-state classifier, mode intent, parameter modulation | K1 appears to listen, not merely react | Donor mode IDs absent, user/manual ownership, quantisation, over-switching | Applied mode changes and scalar changes alter final byte sequences and motion memory | SB six-state classifier from current AP globals | <= 2 Assist switches/min first pass, switch reasons recorded, blind clips read as more musical | Build SB-native Assist with switching |
| Onset/Beat | AP event detector and beat confidence | Visual hits lock to musical events | False positives, tempo lock delay, AP CPU cost | Events gate accents and switch boundaries | Existing novelty derivative before donor FFT | Silence false event rate near zero; visible hit alignment within bounded frame window | Backtest simple first, import heavier only if it wins |
| Beat Visual Hooks | Event-gated accents and switch confirmation | Drops, kicks, and phrase turns feel intentional | Over-flashing, late events, render jitter | RenderParams pulse, EdgeMixer strength gate, bounded switch confirmation | Use onset event age only, no tempo phase | Final-byte hit appears within configured event age, no extra dropped frames | Add after event quality proof |
| Director Autonomy | Broader auto mode policy | Device feels smart across whole songs | Randomness, manual override conflict, weak mode map | Long-form stateful song traversal and restrained transitions | Assist switching only | Real music proof shows better perceived musical relevance than Assist alone | Defer until earlier functions pass |

## Core Interfaces

Create the following common product interfaces before feature-specific work. These are small, copyable value types; no heap and no ownership of donor objects.

```cpp
// SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.h
#pragma once

#include <stdint.h>
#include "config_types.h"

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
  float onset_strength;
  float bass_onset_strength;
  float beat_phase;
  float beat_confidence;
  bool onset;
  bool bass_onset;
  bool beat;
};
```

```cpp
// SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.h
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
  SB_MODE_REASON_COOLDOWN
};

struct SBModeIntent {
  uint8_t requested_mode;
  SBModeIntentReason reason;
  float confidence;
  bool wants_switch;
};

struct SBModeSelectionState {
  uint8_t applied_mode;
  uint8_t last_requested_mode;
  uint32_t last_switch_ms;
  uint32_t window_start_ms;
  uint8_t switches_in_window;
  SBModeIntentReason last_reason;
};
```

```cpp
// SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.h
#pragma once

#include "render_params.h"
#include "sb_audio_snapshot.h"
#include "sb_mode_selection.h"

struct SBSmartDirectorConfig {
  bool enabled;
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
};

void sb_smart_director_init();
SBSmartDirectorOutput sb_smart_director_tick(const SBAudioSnapshot& audio, uint32_t now_ms);
void sb_smart_director_apply_render_params(const SBSmartDirectorOutput& output, RenderParams* params);
```

## File Structure

Create:

- `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.h` / `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.cpp`
  - AP snapshot extraction and cross-core publication.
- `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.h` / `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.cpp`
  - Assist applied-mode gate, allow-list, dwell/cooldown/rate limit, manual/show ownership checks.
- `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.h` / `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp`
  - Classifier, confidence/coast logic, mode intent, `RenderParams` scalar modulation.
- `SPECTRASYNQ_K1_FIRMWARE/sb_edgemixer_lite.h` / `SPECTRASYNQ_K1_FIRMWARE/sb_edgemixer_lite.cpp`
  - Secondary CRGB16 transform and centre-corrected mask.
- `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.h` / `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp`
  - Novelty onset first, beat/event state later.
- `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h` / `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp`
  - Event-gated accents and Assist switch-boundary confirmation.
- `tests/test_smart_visual_engine_static.py`
  - Source/build static gates.
- `tests/test_smart_visual_engine_plan.py`
  - Guard the plan-critical contracts that can be checked textually before hardware proof.
- Optional after source proof: `scripts/regression-harness/smart_visuals_gate.py`
  - Parse smart-director/event logs if a new evidence format is emitted.

Modify:

- `platformio.ini`
  - Add product modules to `build_src_filter` as `+<sb_*.cpp>`.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
  - Include new headers.
  - Update AP snapshot after novelty.
  - Choose applied primary mode before primary render.
  - Push primary `RenderParams` overlay around primary render.
  - Apply EdgeMixer-lite on `leds_16_secondary` after secondary store and before clipping.
- `SPECTRASYNQ_K1_FIRMWARE/globals.h` / `SPECTRASYNQ_K1_FIRMWARE/globals.cpp`
  - Add only fixed-size state if shared publication cannot stay file-local.
- `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h` / `SPECTRASYNQ_K1_FIRMWARE/serial_cmd_table.def`
  - Only after Captain approves typed controls and after kernel proof.

Do not modify in this feature lane unless Captain explicitly reopens those seams:

- `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h`
- `SPECTRASYNQ_K1_FIRMWARE/GDFT.h`
- `SPECTRASYNQ_K1_FIRMWARE/noise_cal.h`
- Donor `Lightwave-Ledstrip/firmware-v3` source files

## Execution Topology

Use isolated subagent worktrees at execution time. Do not let multiple workers mutate the same file set concurrently.

| Lane | Worker ownership | Can run in parallel after |
|---|---|---|
| A: Baseline and shared types | `platformio.ini`, `sb_audio_snapshot.*`, `tests/test_smart_visual_engine_static.py` | Start |
| B: EdgeMixer-lite | `sb_edgemixer_lite.*`, secondary render insertion | Lane A interfaces |
| C: SynqMatrix Assist | `sb_smart_director.*`, `sb_mode_selection.*`, primary render insertion | Lane A interfaces |
| D: Onset/Beat | `sb_onset_beat.*`, AP snapshot/event tests | Lane A interfaces |
| E: Visual hooks | `sb_visual_hooks.*`, Assist/Event integration | Lanes C and D |
| F: Director autonomy | policy-only expansion, docs, tests | Lanes B-E with runtime proof |

## Task 0: Freeze Base And Evidence Boundary

**Files:**

- Read: `AGENTS.md`
- Read: `.claude/CLAUDE.md`
- Read: `.claude/skills/k1-firmware-change-gate/SKILL.md`
- Read: `.claude/skills/sensorybridge-doctrine/SKILL.md`
- Read: `docs/forensics/2026-05-27-smart-director-edgemixer-onset-import-strategy.md`
- Read: `docs/refactor/harness-baselines/freeze-88428a2/CANONICAL.md`

- [ ] **Step 1: Verify live repo state**

Run:

```bash
git status --short --branch
git rev-parse --short HEAD
```

Expected: current branch and dirty files are explicitly listed in the worker log. If unrelated dirty files exist, do not revert them.

- [ ] **Step 2: Verify baseline commands still work before feature edits**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_dev_instrumentation_boundary.py'
python3 -B -m unittest discover -s tests -p 'test_vpab_gate.py'
pio run -e k1_hardware
```

Expected: tests pass and production build succeeds. If the build fails before feature edits, stop and diagnose baseline drift.

- [ ] **Step 3: Declare the runtime proof boundary**

Record in the task log:

```text
No serial port opened by agent.
No calibration command will be sent by agent.
Build success is compile proof only.
Runtime proof requires Captain-provided serial/video/timing captures.
```

## Task 1: Add Smart Visual Build And Static Guard Substrate

**Files:**

- Modify: `platformio.ini`
- Create: `tests/test_smart_visual_engine_static.py`

- [ ] **Step 1: Write failing static tests**

Create `tests/test_smart_visual_engine_static.py` with checks for:

- `platformio.ini` includes `+<sb_*.cpp>` only after product modules exist.
- Production env does not contain `mabutrace`, `trace_dev`, `ENABLE_VPAB_PROBE`, `ENABLE_DIAG_CAPTURE`, or `FEATURE_TRACE_RENDER`.
- `sb_*.cpp` / `sb_*.h` sources contain no `new`, `malloc`, `calloc`, `realloc`, `free`, `String`, `std::vector`, `std::map`, `Preferences`, `FastLED.show`, `Serial.print`, or WiFi includes.
- `sb_edgemixer_lite` centre mask mentions both `79` and `80` or uses `79.5f`.
- `sb_smart_director` contains no donor `EffectId`, `ControlBusFrame`, `RendererActor`, REST, WS, or NVS tokens.

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
```

Expected before implementation: failure because files and build-filter entries do not exist.

- [ ] **Step 2: Add build filter for product smart modules**

Modify `platformio.ini` production filter:

```ini
build_src_filter = +<*.ino> +<*.ino.cpp> +<globals_config.cpp> +<globals.cpp> +<Palettes.cpp> +<render_params.cpp> +<light_mode_*.cpp> +<sb_*.cpp>
```

Harness and trace-dev envs inherit this production product-code inclusion. Do not add diagnostic flags to `k1_hardware`.

- [ ] **Step 3: Add empty product module files only when their tasks create real interfaces**

Do not add dummy `.cpp` files just to satisfy the build filter. Each `sb_*.cpp` must compile because the owning task creates its header and implementation.

- [ ] **Step 4: Run production contamination tests**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_dev_instrumentation_boundary.py'
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
```

Expected after all module files exist: tests pass.

## Task 2: Shared AP Snapshot And Cross-Core Publication

**Files:**

- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Test: `tests/test_smart_visual_engine_static.py`

- [ ] **Step 1: Define `SBAudioSnapshot` and `SBOnsetBeatEvent`**

Use the interface in the "Core Interfaces" section. Keep the structs plain-old-data and fixed-size.

- [ ] **Step 2: Implement AP snapshot extraction**

In `sb_audio_snapshot.cpp`, implement:

```cpp
void sb_audio_snapshot_update(uint32_t frame_ms);
SBAudioSnapshot sb_audio_snapshot_read();
```

Rules:

- Read existing AP globals only after `calculate_vu()`, `process_GDFT()`, and `calculate_novelty()`.
- Compute low/mid/high summaries from existing `spectrogram` or `spectrogram_smooth`.
- Use a file-local `portMUX_TYPE` or equivalent fixed-size critical section for publication.
- Copy no arrays across cores in render; publish only compact scalar summaries.

- [ ] **Step 3: Insert AP update point**

In `SPECTRASYNQ_K1_FIRMWARE.ino`, after `calculate_novelty(t_now);`, call:

```cpp
sb_audio_snapshot_update(t_now);
```

Do not call it before novelty exists.

- [ ] **Step 4: Verify compile and static constraints**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
pio run -e k1_hardware
```

Expected: no heap/String/static guard failures; production compile succeeds.

## Task 3: EdgeMixer-Lite Shadow Evaluation

**Files:**

- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_edgemixer_lite.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_edgemixer_lite.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Test: `tests/test_smart_visual_engine_static.py`

- [ ] **Step 1: Define EdgeMixer-lite config and modes**

Create:

```cpp
enum SBEdgeMixerMode : uint8_t {
  SB_EDGE_MIXER_OFF = 0,
  SB_EDGE_MIXER_ANALOGOUS,
  SB_EDGE_MIXER_COMPLEMENTARY,
  SB_EDGE_MIXER_SPLIT_COMPLEMENTARY,
  SB_EDGE_MIXER_SATURATION_VEIL,
  SB_EDGE_MIXER_TRIADIC,
  SB_EDGE_MIXER_TETRADIC
};

struct SBEdgeMixerConfig {
  bool enabled;
  SBEdgeMixerMode mode;
  float strength;
};
```

Default config is disabled.

- [ ] **Step 2: Implement centre-corrected mask**

Implement a mask derived from `fabsf(float(i) - 79.5f)`. Indices 79 and 80 are the centre minimum. Edges are the maximum. Do not copy donor `CENTRE_GRADIENT`.

- [ ] **Step 3: Implement secondary-only CRGB16 transform**

Implement:

```cpp
void sb_edgemixer_lite_apply(CRGB16* secondary, uint16_t count, const SBEdgeMixerConfig& config);
```

Rules:

- Return immediately when disabled.
- Mutate only the `secondary` buffer passed by caller.
- Clamp every channel to `[0, 1]`.
- Do not call `ColorFromPalette`, `FastLED.show`, `Serial`, or `Preferences`.
- Do not use dynamic allocation.

- [ ] **Step 4: Insert secondary render hook**

In `SPECTRASYNQ_K1_FIRMWARE.ino`, inside the secondary render block, call EdgeMixer-lite after:

```cpp
store_render_channel_output(secondary_channel);
```

and before:

```cpp
clip_led_values(leds_16_secondary);
```

The first integration keeps `SBEdgeMixerConfig.enabled == false` unless a harness/test build explicitly enables it.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
pio run -e k1_hardware
pio run -e k1_hardware_harness
```

Expected: builds pass; static tests confirm no production diagnostic contamination and no forbidden render tokens.

- [ ] **Step 6: Runtime proof requirement**

Do not claim visual value until Captain provides VPAB/final-byte evidence comparing EdgeMixer off/on under the reference Bloom/Waveform state.

Acceptance:

- At least 5 percent of nonblack secondary pixels change by >= 2 final-byte LSB.
- Primary bytes remain unchanged except shared global visual state already present in baseline.
- Centre COM stays inside baseline tolerance.
- No visible washout or rainbow cycling.

## Task 4: SynqMatrix Assist With Mode Switching And Parameter Modulation

**Files:**

- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.cpp`
- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Test: `tests/test_smart_visual_engine_static.py`

- [ ] **Step 1: Implement SB mode allow-list**

Initial Assist allow-list:

- `LIGHT_MODE_BLOOM`
- `LIGHT_MODE_BLOOM_FAST`
- `LIGHT_MODE_WAVEFORM`
- `LIGHT_MODE_WAVEFORM_FAST`
- `LIGHT_MODE_WAVEFORM_HYBRID`
- `LIGHT_MODE_VU`

Excluded until separately proven:

- `LIGHT_MODE_QUANTUM_COLLAPSE`
- `LIGHT_MODE_KALEIDOSCOPE`
- GDFT chromagram variants as automatic switch targets

- [ ] **Step 2: Implement state-to-mode map**

Initial map:

| State | Requested mode | Parameter intent |
|---|---|---|
| Silence | hold current or `LIGHT_MODE_BLOOM` | reduce photons and saturation |
| Ambient | `LIGHT_MODE_BLOOM` | slow, low contrast |
| Steady | `LIGHT_MODE_WAVEFORM` | moderate photons and chroma |
| Build | `LIGHT_MODE_WAVEFORM_HYBRID` | increase photons/chroma gradually |
| Drop | `LIGHT_MODE_BLOOM_FAST` or `LIGHT_MODE_WAVEFORM_FAST` | short high-impact scalar |
| Breakdown | `LIGHT_MODE_BLOOM` | reduce speed and brightness |
| Dense | `LIGHT_MODE_WAVEFORM_HYBRID` | reduce saturation to avoid mush |

Do not use random selection in the first pass.

- [ ] **Step 3: Implement `ModeSelectionGate`**

Gate rules:

- Assist disabled returns `CONFIG.LIGHTSHOW_MODE`.
- Manual/show ownership returns `CONFIG.LIGHTSHOW_MODE`.
- Requested mode outside allow-list is denied.
- Minimum dwell starts at `8000 ms`.
- Cooldown starts at `20000 ms`.
- Switch window starts at `60000 ms`.
- Maximum switches per window starts at `2`.
- Every denial returns a reason code.

- [ ] **Step 4: Implement classifier**

Use only `SBAudioSnapshot` fields. Do not import donor `ControlBusFrame`.

Classifier first-pass rules:

- `silence == true` -> `SB_MUSIC_SILENCE`.
- High novelty plus high peak -> `SB_MUSIC_DROP`.
- Rising novelty/energy over the recent window -> `SB_MUSIC_BUILD`.
- Low novelty and low energy -> `SB_MUSIC_AMBIENT`.
- High energy and high broad-band spread -> `SB_MUSIC_DENSE`.
- Energy drop after build/drop -> `SB_MUSIC_BREAKDOWN`.
- Else -> `SB_MUSIC_STEADY`.

Use dt-correct smoothing from elapsed milliseconds; no frame-count smoothing.

- [ ] **Step 5: Implement parameter modulation**

Implement:

```cpp
void sb_smart_director_apply_render_params(const SBSmartDirectorOutput& output, RenderParams* params);
```

Rules:

- Apply bounded scalar changes to `PHOTONS`, `CHROMA`, `MOOD`, and `SATURATION`.
- Clamp to existing safe ranges.
- Do not mutate global `CONFIG`.
- Do not change secondary render params unless a later explicit policy enables it.

- [ ] **Step 6: Insert primary render integration**

In `led_thread()`, before primary render:

1. Read `SBAudioSnapshot`.
2. Tick `SBSmartDirector`.
3. Resolve applied primary mode through `ModeSelectionGate`.
4. Build primary `RenderParams`.
5. Apply director param overlay.
6. Push params.
7. Render the applied mode.
8. Pop params.

The code shape must preserve `RenderChannelState primary_channel = make_primary_channel();` and must not create heap objects.

- [ ] **Step 7: Preserve history character on mode switch**

For Bloom/Waveform-family transitions, do not blindly clear `leds_16_prev`. First pass policy:

- Hold shared history on `BLOOM` <-> `BLOOM_FAST`.
- Hold shared history on `WAVEFORM` <-> `WAVEFORM_FAST` <-> `WAVEFORM_HYBRID`.
- When crossing Bloom family to Waveform family, allow one frame of existing history but record the transition reason for visual review.
- If VPAB shows ugly carryover, add a bounded one-frame fade/seed policy in a later patch.

- [ ] **Step 8: Verify**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
pio run -e k1_hardware
pio run -e k1_hardware_harness
```

Expected: compile succeeds, no forbidden donor symbols, no production diagnostic contamination.

- [ ] **Step 9: Runtime proof requirement**

Captain-provided evidence must show:

- switch-intent timeline;
- applied-mode timeline;
- no more than 2 Assist switches per 60 seconds;
- no switch during manual/show ownership;
- VPAB/final-byte deltas are visible but centre-safe;
- reference Bloom/Waveform character is not degraded.

## Task 5: Onset-Lite And Beat Event Lane

**Files:**

- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_onset_beat.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_audio_snapshot.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Test: `tests/test_smart_visual_engine_static.py`

- [ ] **Step 1: Implement novelty onset backend first**

Use current `SBAudioSnapshot` summaries. Do not import donor FFT detector in the first firmware pass.

Rules:

- Keep onset state AP-side.
- Use adaptive baseline and refractory interval.
- Start refractory at `80 ms`.
- Publish event age and confidence.
- Silence suppresses event output but does not corrupt baseline tracking.

- [ ] **Step 2: Implement beat confidence as experimental scalar**

First pass:

- Track intervals between accepted bass/onset events.
- Emit `beat_confidence` only after repeated intervals are within tolerance.
- Do not drive mode switching directly from tempo until later proof.

- [ ] **Step 3: Publish compact event**

Publish `SBOnsetBeatEvent` through the same fixed-size cross-core pattern as `SBAudioSnapshot`.

- [ ] **Step 4: Verify**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
pio run -e k1_hardware
```

Expected: compile succeeds; no render path dependency on onset internals.

- [ ] **Step 5: Backtest requirement before promotion**

Use synthetic and captured AP logs. Acceptance:

- silence false event rate near zero after calibration;
- noisy-room false events bounded before visual hooks;
- synthetic impulse train produces one event per impulse after refractory;
- synthetic 120/128 BPM patterns produce stable event intervals;
- AP CPU overhead does not threaten latency.

Donor FFT `OnsetDetector` is allowed only if this novelty backend fails a materiality gate and the donor detector proves better.

## Task 6: Beat-Gated Visual Hooks

**Files:**

- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h`
- Create: `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_edgemixer_lite.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`

- [ ] **Step 1: Define visual hook output**

Create a fixed-size value:

```cpp
struct SBVisualHookOutput {
  float primary_pulse_scalar;
  float secondary_edge_strength_scalar;
  bool confirm_switch_boundary;
};
```

- [ ] **Step 2: Implement event-age gate**

Rules:

- Accepted event window starts at `0 ms` and ends at `80 ms`.
- Events older than the window do not trigger a pulse.
- Refractory is owned by onset lane, not render.
- Hook output fades by dt, not frame count.

- [ ] **Step 3: Apply hooks**

Apply in two places:

- Primary `RenderParams` overlay: short `PHOTONS` / `CHROMA` pulse.
- EdgeMixer-lite config: short secondary strength bump.

Do not add new final-byte effects directly in `show_leds()`.

- [ ] **Step 4: Assist switch-boundary confirmation**

Use onset/beat events to confirm switch timing only when `ModeSelectionGate` already permits a switch. Do not let beat events bypass dwell/cooldown/ownership gates.

- [ ] **Step 5: Verify**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
pio run -e k1_hardware
pio run -e k1_hardware_harness
```

Runtime acceptance:

- visible hit appears within bounded event age;
- no extra dropped frames;
- no false-hit storm under silence;
- Assist switch timing improves or stays neutral on reference tracks.

## Task 7: Director Autonomy

**Files:**

- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.h`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_smart_director.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_mode_selection.cpp`
- Modify: docs in `docs/forensics/` after runtime proof

- [ ] **Step 1: Promote only after Assist proof**

Prerequisites:

- EdgeMixer-lite visual proof accepted.
- Assist switching proof accepted.
- Onset/beat false-positive proof accepted.
- Beat-gated hooks proof accepted.

- [ ] **Step 2: Expand policy, not architecture**

Director autonomy may expand:

- state dwell windows;
- mode family allow-list;
- secondary-channel policy;
- longer phrase-level transition confidence.

It must not add donor `ControlBus`, donor effect registry, REST/WS, NVS, or STA.

- [ ] **Step 3: Runtime acceptance**

Director must beat Assist-only in Captain visual review on fixed music sections. If it does not, keep Assist and do not promote Director.

## Task 8: Optional Typed Control Surface

**Files:**

- Modify only after Captain approval: `SPECTRASYNQ_K1_FIRMWARE/serial_cmd_table.def`
- Modify only after Captain approval: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h`
- Test: existing serial/static tests plus new `tests/test_smart_visual_engine_static.py`

- [ ] **Step 1: Add typed commands only**

Allowed command families:

```text
smart assist on|off
smart assist profile subtle|balanced|high
smart status
edge mode off|analogous|complementary|split|veil|triadic|tetradic
edge strength <0.0-1.0>
beat status
```

No single-byte hotkeys. No destructive commands. No calibration command.

- [ ] **Step 2: Guard parser compatibility**

Preserve existing `:` parser requirement and `N`/`Y` noise-cal arm/confirm safety.

- [ ] **Step 3: Verify**

Run:

```bash
python3 -B -m unittest discover -s tests -p 'test_serial_hotkeys_static.py'
python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'
pio run -e k1_hardware
```

Runtime command proof requires Captain-provided serial capture.

## Task 9: E2E Verification Matrix

| Gate | Command / evidence | Pass condition |
|---|---|---|
| Static smart visual guards | `python3 -B -m unittest discover -s tests -p 'test_smart_visual_engine_static.py'` | no forbidden render/dev/donor tokens |
| Existing dev boundary | `python3 -B -m unittest discover -s tests -p 'test_dev_instrumentation_boundary.py'` | production remains clean |
| VPAB parser | `python3 -B -m unittest discover -s tests -p 'test_vpab_gate.py'` | parser gates pass |
| Production compile | `pio run -e k1_hardware` | exit 0 |
| Harness compile | `pio run -e k1_hardware_harness` | exit 0 |
| Timeline/causality only | `pio run -e k1_hardware_trace_dev` | non-shippable compile only; use only when causality proof is required |
| EdgeMixer visual proof | Captain VPAB/final-byte capture | secondary deltas visible, primary unchanged, centre-safe |
| Assist switch proof | Captain runtime capture | <= 2 switches/min, reasons emitted, no manual/show override |
| Onset proof | AP event logs | low false positives, bounded event age |
| Beat hook proof | VPAB/video | hit-lock improves without dropped frames |
| Director proof | fixed real music sections | better perceived musical relevance than Assist-only |

## Task 10: Documentation And Promotion Review

**Files:**

- Create after implementation proof: `docs/forensics/2026-05-27-smart-visual-engine-runtime-proof.md`
- Update after implementation proof: `docs/forensics/2026-05-27-smart-director-edgemixer-onset-import-strategy.md`

- [ ] **Step 1: Write runtime proof document**

Record:

- source SHA;
- build env;
- feature flags/runtime settings;
- capture files;
- final-byte / VPAB deltas;
- AP event stats;
- timing/perf;
- Captain visual verdict;
- production contamination result;
- unresolved risks.

- [ ] **Step 2: Promotion decision**

Promotion choices:

- `keep_disabled`: code compiles but feature remains off.
- `promote_edge_only`: EdgeMixer-lite ships, smart switching stays disabled.
- `promote_assist`: Assist switching plus parameter modulation ships.
- `promote_assist_with_hooks`: Assist and beat hooks ship.
- `director_experiment_only`: Director remains demo-only.
- `remove_or_simplify`: feature did not pass perception gate.

No promotion without product-perception evidence.

## SSA Execution Plan

Use this handoff when Captain authorises implementation:

1. Worker A owns Task 0-2 and the shared interfaces.
2. Worker B owns Task 3 only.
3. Worker C owns Task 4 only.
4. Worker D owns Task 5 only.
5. Worker E owns Task 6 and evidence parser changes only after C/D return.
6. Worker F owns Task 7-10 after all prior runtime proof exists.

Each worker must:

- read `AGENTS.md`, `.claude/CLAUDE.md`, k1 firmware gate, doctrine, and this plan;
- write current truth before editing;
- use serial capture, upload/flash, erase, and device-write actions when validation requires them, after verifying the target by port plus stable hardware identity;
- not auto-run calibration; commands that assume silence require Captain's explicit silence-window confirmation;
- branch, commit, and tag only as tested/reviewed rollback checkpoints; never commit untested work, and do not push, rewrite history, or create public release tags without Captain's explicit instruction or an active publication lane;
- list changed files and proof commands before returning.

## Self-Review

Spec coverage:

- EdgeMixer-lite is covered in Task 3.
- Updated SynqMatrix Assist with mode switching plus parameter modulation is covered in Task 4.
- Onset/beat event extraction is covered in Task 5.
- Beat-gated visual hooks are covered in Task 6.
- Full Director autonomy is covered in Task 7.
- Control/status surfaces are isolated in Task 8 and require Captain approval.
- End-to-end proof is covered in Tasks 9-10.

Placeholder scan:

- No placeholder markers remain.
- Deferred work is named as gated promotion, not hidden missing work.

Type consistency:

- `SBAudioSnapshot`, `SBOnsetBeatEvent`, `SBModeIntent`, `SBModeSelectionState`, `SBSmartDirectorOutput`, and `SBVisualHookOutput` are the shared type names used throughout.
