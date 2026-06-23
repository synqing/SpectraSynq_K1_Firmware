# Visual Event Bus L1 Accent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for reviewed execution, but do not dispatch parallel writers against the canonical checkout. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing `sb_visual_hooks` consumer from one merged pulse into a three-lane Layer 1 Accent consumer: onset -> photons, bass onset -> edge strength, beat -> chroma plus switch-boundary confirmation.

**Architecture:** The audio/event bus remains producer-owned and snapshot-replace. The render thread reads `SBAudioSnapshot` and `SBOnsetBeatEvent` once per frame, then passes immutable copies into render-local consumers. L1 writes only to `RenderParams` and EdgeMixer config; L2/VME remains design-only and untouched.

**Tech Stack:** ESP32-S3 Arduino/PlatformIO, FastLED, FreeRTOS `portMUX`, existing SB smart modules, Python `unittest`, non-shippable MabuTrace trace-dev lane.

---

## PM Decision

Proceed with L1 only, but execute a corrected v0.4 plan rather than the supplied v0.3 text.

Key corrections:

- Build env is `k1_hardware_trace_dev`, not `k1_hardware_dev`.
- Fix setter typo before implementation: `config.bass_tau_ms == 0 ? 1 : config.bass_tau_ms`.
- Add host replay and static tests for visual hook semantics before implementation.
- Add minimal call-site `SB_TRACE_SCOPE(...)` spans for bus read and visual hook tick. These are no-op in production and active only through the existing `FEATURE_TRACE_RENDER`/MabuTrace wrapper.
- Do not trace `sb_publish_event` in this L1 pass. Full producer-to-render causality proof remains a separate trace expansion; without it, the strongest honest status is `consumer-trace-only` or `scalar-only`, not full `verified`.
- Treat beat-only `confirm_switch_boundary` as a deliberate behavioural change requiring explicit runtime observation because it can slow Smart Assist mode switching in weak beat-lock material.
- Use producer-owned `event.event_age_ms` for hook event freshness. Do not recompute age from render `now_ms` inside the consumer.
- Treat silence as decay-to-epsilon after the producer clears event flags; `sb_visual_hooks_tick` does not receive `SBAudioSnapshot.silence`, so immediate semantic reset is out of L1 scope.
- Use branches, commits, and tags as rollback tools after diff review and relevant tests/builds. Never commit untested or unreviewed work; remote push, destructive history changes, and release tags require explicit Captain instruction or an active publication lane.

## Doctrine / Change Gate

Current truth:
: Branch `feat/gdft-harness`, HEAD observed as `e63e5be`; working tree is already dirty with Smart Visual Engine source, harness, docs, and runtime evidence. Captain has authorised continuation on this current state. Do not reset, clean, revert, or discard untracked Smart Visual Engine files.

Change class:
: Render-local Smart Visual Engine consumer change. Touches render thread behaviour, EdgeMixer modulation, Smart Assist boundary gating, and trace/test evidence.

Files/seams touched:
: `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h`, `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp`, `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`, `tests/test_smart_visual_engine_static.py`, optionally `tests/test_trace_dev_static.py`, optionally a focused replay/static helper under `scripts/regression-harness/`.

Known breakage avoided:
: No bus field additions, no `sb_onset_beat.cpp`, no `sb_audio_snapshot.cpp`, no `sb_smart_director.*`, no VME, no pixel buffers, no FastLED/gamma/soft-clip changes, no serial command expansion, no calibration.

State ownership:
: Producer owns `SBOnsetBeatEvent`; render owns per-frame immutable copies; `sb_visual_hooks` owns its local pulse decay and per-band `event_id` watermarks; Smart Director owns mode intent; EdgeMixer owns secondary colour treatment.

Runtime proof required:
: Build matrix, host/static tests, trace-dev consumer timing if making timing claims, production MabuTrace symbol audit, and Captain-observed visual A/B on music clips. Compile alone is not runtime proof. Full bus causality proof requires producer trace scopes outside this L1 plan.

Minimal edit plan:
: Tests first, then header struct expansion, then implementation replacement, then `.ino` initialiser/call-site trace scope update, then focused tests/builds/symbol audit.

Explicit non-goals:
: L2 Memory implementation, VME port semantics, producer retuning, donor algorithm import, new serial controls, auto calibration, production instrumentation, broad refactor.

Stop conditions:
: Any required source change outside the declared seams except test/tooling and `.ino` call-site trace scopes, two repeated build failures of the same class, production MabuTrace symbol leakage, trace-dev not buildable, visual regression, or any need for calibration/silence-window commands.

Relevant doctrine rules:
: Preserve musical responsiveness, independent dual-channel behaviour, colour clarity, motion memory, and visual captivation. Developer instrumentation never ships with production. Timing/causality claims require MabuTrace trace-dev; scalar diagnostics do not close causality.

K1 evidence touched:
: L1 consumer code at `sb_visual_hooks.*`; render chain at `.ino:590-612`; EdgeMixer application at `.ino:672-676`; trace-dev env at `platformio.ini:117-126`.

North-star impact:
: Intended product gain is not "more code"; it is cleaner perceived musical causality: treble/snare attacks brighten without bass flooding, kicks press edges/secondary texture, stable beats breathe chroma and open mode boundaries.

Re-test triggers crossed:
: Render hot path, Smart Assist boundary gating, secondary EdgeMixer modulation, trace-dev instrumentation boundary, production shippability.

## File Map

### Production Firmware

- Modify `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h`
  - Replace `SBVisualHookConfig` with enabled/window/tau/coefficient/ceiling fields.
  - Replace `SBVisualHookOutput` with `photon_scalar`, `chroma_scalar`, `edge_scalar`, `confirm_switch_boundary`.
  - Keep public function signatures unchanged.

- Modify `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp`
  - Replace one pulse with onset/bass/beat pulses.
  - Add per-band `event_id` watermarks.
  - Decay pulses before enabled check.
  - Inject each pulse only once per event id.
  - Confirm switch boundary only on fresh `beat`.
  - Apply separated scalars.

- Modify `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
  - Update `SBVisualHookOutput` initialiser to four fields.
  - Optional trace scopes around bus read and `sb_visual_hooks_tick` only under existing `SB_TRACE_SCOPE` no-op/trace-dev wrapper.

### Tests / Tooling

- Modify `tests/test_smart_visual_engine_static.py`
  - Add static contract checks for new visual hook struct fields, default-off config, no forbidden hot-path tokens, and beat-only boundary semantics.

- Modify `tests/test_trace_dev_static.py` if trace scopes are added.
  - Assert new `SB_TRACE_SCOPE("vp_bus_read")` and `SB_TRACE_SCOPE("vp_visual_hooks_tick")` call-site scopes exist.

- Optional create `scripts/regression-harness/visual_hooks_contract_probe.py` and `tests/test_visual_hooks_contract_probe.py`
  - Only if a focused source-level or model-level contract test can be written without false confidence. Static tests are acceptable for L1 because the true behavioural proof is on hardware/video.

## SSA Deployment

No parallel source writers in the canonical checkout.

Read-only SSAs:

- Firmware hazard reviewer: checks render safety, ownership, and hidden source seams.
- Test/verification reviewer: checks tests, trace availability, and build commands.
- Reality checker: attacks evidence labels and verifies what status can honestly be claimed.

Integration rule:

- SSAs return data only.
- PM integrates deltas into this plan.
- Canonical code edits are applied once by the PM in this checkout.

## Task 1: Lock Plan Corrections From SSA Review

**Files:**
- Modify: `docs/superpowers/plans/2026-05-28-visual-event-bus-l1-accent-execution.md`
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`

- [ ] Wait for the three read-only SSA reports.
- [ ] Add only source-grounded corrections to this plan.
- [ ] Record plan deltas in `findings.md`.
- [ ] Mark Phase 11 planning progress in `task_plan.md`.

Expected result:

```text
Plan no longer contains env-name mismatch, setter typo, trace contradiction, or unbounded "verified" claim.
```

## Task 2: Write Host Replay And Static Contract Tests First

**Files:**
- Create: `scripts/regression-harness/visual_hooks_replay.py`
- Create: `tests/test_visual_hooks_replay.py`
- Modify: `tests/test_smart_visual_engine_static.py`
- Modify if adding trace scopes: `tests/test_trace_dev_static.py`

- [ ] Add `scripts/regression-harness/visual_hooks_replay.py` that compiles the real `sb_visual_hooks.cpp` with stubs for Arduino/FreeRTOS and validates the L1 consumer contract.

Required replay cases:

```text
1. onset event increases photon_scalar only.
2. bass_onset event increases edge_scalar only.
3. beat event increases chroma_scalar and confirms boundary.
4. Same event_id does not re-inject any pulse across repeated ticks.
5. New weaker event does not lower a stronger live pulse.
6. Disabled tick continues internal decay but returns baseline scalars.
7. Config setter clamps zero tau to 1 and coefficients/ceiling into bounds.
```

- [ ] Add `tests/test_visual_hooks_replay.py` wrapper:

```python
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regression-harness" / "visual_hooks_replay.py"


class VisualHooksReplayTest(unittest.TestCase):
    def test_host_replay_proves_l1_accent_semantics(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("VISUAL_HOOKS_REPLAY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] Add or update a `test_visual_hooks_l1_accent_contract_is_three_lane_and_default_off` test.

Required assertions:

```python
hooks_header = read(FIRMWARE / "sb_visual_hooks.h")
hooks_source = read(FIRMWARE / "sb_visual_hooks.cpp")
ino = read(FIRMWARE / "SPECTRASYNQ_K1_FIRMWARE.ino")

for token in (
    "onset_tau_ms",
    "bass_tau_ms",
    "beat_tau_ms",
    "onset_to_photons",
    "bass_to_edge",
    "beat_to_chroma",
    "scalar_ceiling",
    "photon_scalar",
    "chroma_scalar",
    "edge_scalar",
):
    self.assertIn(token, hooks_header + "\n" + hooks_source)

for token in (
    "sb_accent_onset_pulse",
    "sb_accent_bass_pulse",
    "sb_accent_beat_pulse",
    "sb_accent_last_onset_event_id",
    "sb_accent_last_bass_event_id",
    "sb_accent_last_beat_event_id",
):
    self.assertIn(token, hooks_source)

self.assertIn("output.confirm_switch_boundary = true", hooks_source)
self.assertLess(hooks_source.index("if (event.beat"), hooks_source.index("output.confirm_switch_boundary = true"))
self.assertNotIn("output.primary_pulse_scalar", hooks_source)
self.assertNotIn("secondary_edge_strength_scalar", hooks_source)
self.assertIn("SBVisualHookOutput visual_hook_output = { 1.0f, 1.0f, 1.0f, false }", ino)
self.assertIn("event.event_age_ms", hooks_source)
self.assertNotIn("now_ms - event.event_ms", hooks_source)
```

- [ ] Add a hot-path purity assertion if not already covered:

```python
for forbidden in ("malloc", "calloc", "realloc", "free", "new ", "String", "Serial", "USBSerial", "FastLED.show", "std::vector", "std::map"):
    self.assertNotIn(forbidden, hooks_source)
```

- [ ] If trace scopes are included in Task 5, update `test_trace_dev_static.py`:

```python
self.assertIn('SB_TRACE_SCOPE("vp_bus_read")', ino)
self.assertIn('SB_TRACE_SCOPE("vp_visual_hooks_tick")', ino)
```

- [ ] Run the focused replay and static tests and verify they fail before implementation:

```bash
python3 -B -m unittest tests.test_visual_hooks_replay
python3 -B -m unittest tests.test_smart_visual_engine_static.SmartVisualEngineStaticTest.test_visual_hooks_l1_accent_contract_is_three_lane_and_default_off
```

Expected:

```text
FAIL
```

## Task 3: Implement Header Contract

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.h`

- [ ] Replace `SBVisualHookConfig` with:

```cpp
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
```

- [ ] Replace `SBVisualHookOutput` with:

```cpp
struct SBVisualHookOutput {
  float photon_scalar;
  float chroma_scalar;
  float edge_scalar;
  bool confirm_switch_boundary;
};
```

- [ ] Do not alter function signatures.

Expected:

```text
Header exposes separated L1 accent lanes while keeping caller API shape stable.
```

## Task 4: Implement Three-Pulse Visual Hook Semantics

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/sb_visual_hooks.cpp`

- [ ] Replace single pulse state:

```cpp
static float sb_accent_onset_pulse = 0.0f;
static float sb_accent_bass_pulse = 0.0f;
static float sb_accent_beat_pulse = 0.0f;

static uint32_t sb_accent_last_onset_event_id = 0;
static uint32_t sb_accent_last_bass_event_id = 0;
static uint32_t sb_accent_last_beat_event_id = 0;
```

- [ ] Replace default config:

```cpp
static SBVisualHookConfig sb_hook_config = {
  false,
  80UL,
  100UL,
  180UL,
  250UL,
  0.16f,
  0.20f,
  0.12f,
  2.0f
};
```

- [ ] Update `sb_visual_hooks_set_config()`:

```cpp
void sb_visual_hooks_set_config(const SBVisualHookConfig& config) {
  SBVisualHookConfig next;
  next.enabled = config.enabled;
  next.event_window_ms = config.event_window_ms;
  next.onset_tau_ms = config.onset_tau_ms == 0 ? 1 : config.onset_tau_ms;
  next.bass_tau_ms = config.bass_tau_ms == 0 ? 1 : config.bass_tau_ms;
  next.beat_tau_ms = config.beat_tau_ms == 0 ? 1 : config.beat_tau_ms;
  next.onset_to_photons = sb_hook_clamp(config.onset_to_photons, 0.0f, 1.0f);
  next.bass_to_edge = sb_hook_clamp(config.bass_to_edge, 0.0f, 1.0f);
  next.beat_to_chroma = sb_hook_clamp(config.beat_to_chroma, 0.0f, 1.0f);
  next.scalar_ceiling = sb_hook_clamp(config.scalar_ceiling, 1.0f, 4.0f);

  portENTER_CRITICAL(&sb_hook_config_mux);
  sb_hook_config = next;
  portEXIT_CRITICAL(&sb_hook_config_mux);
}
```

- [ ] Add a file-local pulse decay helper:

```cpp
static void sb_decay_accent_pulse(float* pulse, uint32_t dt_ms, uint32_t tau_ms) {
  if (pulse == nullptr) {
    return;
  }
  float decay = sb_hook_clamp(float(dt_ms) / float(tau_ms == 0 ? 1 : tau_ms), 0.0f, 1.0f);
  *pulse *= (1.0f - decay);
  if (*pulse < 0.0001f) {
    *pulse = 0.0f;
  }
}
```

- [ ] Replace `sb_visual_hooks_tick()` body:

```cpp
SBVisualHookOutput sb_visual_hooks_tick(const SBOnsetBeatEvent& event, uint32_t now_ms) {
  SBVisualHookConfig config = sb_visual_hooks_config();
  SBVisualHookOutput output;
  output.photon_scalar = 1.0f;
  output.chroma_scalar = 1.0f;
  output.edge_scalar = 1.0f;
  output.confirm_switch_boundary = false;

  uint32_t dt_ms = (sb_hook_last_ms == 0 || now_ms < sb_hook_last_ms) ? 0 : now_ms - sb_hook_last_ms;
  sb_hook_last_ms = now_ms;
  sb_decay_accent_pulse(&sb_accent_onset_pulse, dt_ms, config.onset_tau_ms);
  sb_decay_accent_pulse(&sb_accent_bass_pulse, dt_ms, config.bass_tau_ms);
  sb_decay_accent_pulse(&sb_accent_beat_pulse, dt_ms, config.beat_tau_ms);

  if (!config.enabled) {
    return output;
  }

  uint32_t age_ms = event.event_age_ms;
  bool eligible = event.event_id != 0 && age_ms <= config.event_window_ms;

  if (eligible && event.onset && event.event_id != sb_accent_last_onset_event_id) {
    float strength = sb_hook_clamp(event.onset_strength, 0.0f, 1.0f);
    if (strength > sb_accent_onset_pulse) {
      sb_accent_onset_pulse = strength;
    }
    sb_accent_last_onset_event_id = event.event_id;
  }

  if (eligible && event.bass_onset && event.event_id != sb_accent_last_bass_event_id) {
    float strength = sb_hook_clamp(event.bass_onset_strength, 0.0f, 1.0f);
    if (strength > sb_accent_bass_pulse) {
      sb_accent_bass_pulse = strength;
    }
    sb_accent_last_bass_event_id = event.event_id;
  }

  if (eligible && event.beat && event.event_id != sb_accent_last_beat_event_id) {
    float strength = sb_hook_clamp(event.beat_confidence, 0.0f, 1.0f);
    if (strength > sb_accent_beat_pulse) {
      sb_accent_beat_pulse = strength;
    }
    sb_accent_last_beat_event_id = event.event_id;
    output.confirm_switch_boundary = true;
  }

  output.photon_scalar = sb_hook_clamp(1.0f + (sb_accent_onset_pulse * config.onset_to_photons), 1.0f, config.scalar_ceiling);
  output.chroma_scalar = sb_hook_clamp(1.0f + (sb_accent_beat_pulse * config.beat_to_chroma), 1.0f, config.scalar_ceiling);
  output.edge_scalar = sb_hook_clamp(1.0f + (sb_accent_bass_pulse * config.bass_to_edge), 1.0f, config.scalar_ceiling);
  return output;
}
```

- [ ] Replace `sb_visual_hooks_apply_render_params()`:

```cpp
void sb_visual_hooks_apply_render_params(const SBVisualHookOutput& output, RenderParams* params) {
  SBVisualHookConfig config = sb_visual_hooks_config();
  if (params == nullptr || !config.enabled) {
    return;
  }
  params->PHOTONS = sb_hook_clamp(params->PHOTONS * output.photon_scalar, 0.0f, 2.0f);
  params->CHROMA = sb_hook_clamp(params->CHROMA * output.chroma_scalar, 0.0f, 2.0f);
}
```

- [ ] Replace `sb_visual_hooks_apply_edge_config()`:

```cpp
SBEdgeMixerConfig sb_visual_hooks_apply_edge_config(const SBVisualHookOutput& output, SBEdgeMixerConfig config) {
  SBVisualHookConfig hook_config = sb_visual_hooks_config();
  if (!hook_config.enabled) {
    return config;
  }
  config.strength = sb_hook_clamp(config.strength * output.edge_scalar, 0.0f, 1.0f);
  return config;
}
```

Expected:

```text
Onset, bass, and beat produce separated, bounded output scalars with per-event watermarking.
```

## Task 5: Update Render Call Site And Optional Trace Scopes

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Modify if trace scopes are added: `tests/test_trace_dev_static.py`

- [ ] Change the default output initialiser:

```cpp
SBVisualHookOutput visual_hook_output = { 1.0f, 1.0f, 1.0f, false };
```

- [ ] If making trace-dev timing claims, wrap bus read and visual hook tick at the call site:

```cpp
{
  SB_TRACE_SCOPE("vp_bus_read");
  smart_audio = sb_audio_snapshot_read();
  smart_event = sb_onset_beat_read();
}
```

and:

```cpp
{
  SB_TRACE_SCOPE("vp_visual_hooks_tick");
  visual_hook_output = sb_visual_hooks_tick(smart_event, smart_now_ms);
}
```

Implementation note:

- If local variables are currently declared inline, hoist them above the trace scope as zero-initialised locals.
- Do not trace inside `sb_visual_hooks.cpp`; keep instrumentation in `.ino` call-site scopes where trace usage already exists.
- Do not touch `sb_onset_beat.cpp` in this phase. Producer publish timing remains out of L1 scope unless a separate trace plan is approved.
- These scopes support consumer timing and render placement only. They do not prove producer publish latency.

Expected:

```text
The call site compiles with the new output shape. Exact hook timing is trace-visible only in trace-dev builds.
```

## Task 6: Focused Verification Before Build Matrix

**Files:**
- Test: `tests/test_smart_visual_engine_static.py`
- Test: `tests/test_trace_dev_static.py`
- Test: `tests/test_dev_instrumentation_boundary.py`

- [ ] Run focused Smart Visual static test:

```bash
python3 -B -m unittest tests.test_smart_visual_engine_static
```

Expected:

```text
OK
```

- [ ] Run visual hooks host replay:

```bash
python3 -B -m unittest tests.test_visual_hooks_replay
```

Expected:

```text
OK
```

- [ ] Run trace-dev static test:

```bash
python3 -B -m unittest tests.test_trace_dev_static
```

Expected:

```text
OK
```

- [ ] Run developer instrumentation boundary test:

```bash
python3 -B -m unittest tests.test_dev_instrumentation_boundary
```

Expected:

```text
OK
```

- [ ] Run full Python regression suite:

```bash
python3 -B -m unittest discover -s tests
```

Expected:

```text
OK
```

## Task 7: PlatformIO Build Matrix

**Files:**
- Source build only.

- [ ] Build production:

```bash
pio run -e k1_hardware
```

Expected:

```text
SUCCESS
```

Known acceptable warning:

```text
SPECTRASYNQ_K1_FIRMWARE/system.h:48 volatile increment warning
```

- [ ] Build trace-dev:

```bash
pio run -e k1_hardware_trace_dev
```

Expected:

```text
SUCCESS
```

- [ ] Optional if bench pinmap confidence is needed:

```bash
pio run -e k1_bench_reference
```

Expected:

```text
SUCCESS
```

## Task 8: Production Shippability Symbol Audit

**Files:**
- Build artefacts only.

- [ ] Confirm production has no MabuTrace symbols:

```bash
nm .pio/build/k1_hardware/firmware.elf | grep -i mabutrace
```

Expected:

```text
No output. grep exit code 1 is PASS.
```

- [ ] Build harness and confirm harness also has no MabuTrace symbols:

```bash
pio run -e k1_hardware_harness
nm .pio/build/k1_hardware_harness/firmware.elf | grep -i mabutrace
```

Expected:

```text
Build SUCCESS. nm/grep no output. grep exit code 1 is PASS.
```

## Task 9: Trace-Dev Runtime Evidence Gate

**Files:**
- Runtime evidence under `docs/forensics/runtime-evidence/`
- Optional future analysis script if existing tooling cannot parse the new trace spans.

Precondition:

- Captain confirms hardware is available for trace-dev upload/capture or supplies trace logs.
- No calibration commands.

- [ ] Upload trace-dev only if Captain explicitly authorises the hardware run in the active turn.
- [ ] Capture trace containing `vp_visual_hooks_tick` and existing render counters.
- [ ] Compare trace-dev hook timing against a same-hardware pre-change baseline.

Pass thresholds:

```text
sb_visual_hooks_tick P99 widening <= 10 percent vs baseline
No primary/secondary render over-budget increase attributable to hooks
Bus-read to hook application remains inside the same render frame
```

Evidence status:

- If this is not run, final status cannot be `verified`; it is at most `scalar-only`.
- If trace scope is not added, do not claim exact consumer timing.
- Because producer publish is not traced in this L1 pass, do not claim full audio-to-render causality. Use `consumer-trace-only` for hook timing proof.

## Task 10: Visual A/B Gate

**Files:**
- Runtime evidence under `docs/forensics/runtime-evidence/`
- Forensic closeout doc.

Precondition:

- Captain controls music/capture.
- Production firmware restored after any harness/trace-dev run.

Clips:

1. Kick-heavy electronic with `edge_enabled=on`, non-off edge mode, and `edge_strength>0`: bass pulse should press edge/secondary without primary flood.
2. Snare/hat acoustic: onset pulse should accent snare cleanly; hats should not create plateau.
3. Locked tempo with tempo change: beat pulse should create subtle chroma breathing; boundary opens cleanly without repeated same-event injection.
4. Dense/no-strong-beat material: Smart Assist must not appear stuck due to beat-only boundary gating.

Pass:

```text
All clips show separated, musically plausible accents.
No cheap strobe.
No persistent plateau.
No secondary white flood.
No Smart Assist stagnation caused by beat-only boundary under expected demo material.
```

If mixed:

```text
Status = approval. Captain decides tune, keep, or roll back.
```

## Task 11: Evidence Closeout

**Files:**
- Create: `docs/forensics/2026-05-28-visual-event-bus-l1-accent-runtime-evidence.md`
- Modify: `task_plan.md`
- Modify: `findings.md`
- Modify: `progress.md`

- [ ] Create dated forensic doc with YAML frontmatter and changelog.
- [ ] Record:
  - files changed
  - tests run and outputs
  - build matrix
  - symbol audit result
  - trace-dev status
  - visual A/B status
  - exact status label
  - residual risks
- [ ] Update planning files.

Status labels:

- `verified`: Tasks 6, 7, 8, 9, and 10 pass, and a separate producer-to-render trace expansion proves full causality.
- `consumer-trace-only`: Tasks 6, 7, 8, and consumer trace scopes in Task 9 pass, but producer publish causality is not traced in this L1 pass.
- `scalar-only`: Tasks 6, 7, 8, and 10 pass, but Task 9 is not run or cannot support exact timing.
- `blocked`: Tasks 6, 7, or 8 fail and root cause is out of L1 scope.
- `approval`: visual A/B evidence is mixed or ambiguous.
- `visual-failed`: host/build/symbol gates pass but Captain-visible A/B regresses perceived output.
- `awaiting-captain-capture`: host/build/symbol gates pass, but hardware/video proof has not been supplied yet.

## Execution Notes

- This plan does not require a commit checkpoint until the diff has passed review and relevant tests/builds.
- This plan does not include automatic calibration commands. Any command that assumes silence requires Captain's explicit silence-window confirmation.
- If hardware execution is required later, trace-dev and production upload/capture are runtime proof tasks, not build tasks; verify target identity before serial, upload/flash, erase, or device-write actions.
