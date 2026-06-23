# Secondary Channel + Release Recovery Onwards Handover

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resume the remaining Secondary Channel Renderer work and then continue the SB Release Feature Recovery Roadmap without reintroducing known AP/VP/render/colour/encoder regressions.

**Architecture:** Treat `refactor/main` as the protected post-refactor base. Implement secondary-state isolation first, then resume visual feature recovery. The session output is code first, with validation notes attached to the patch.

**Tech Stack:** PlatformIO `k1_hardware` / `k1_hardware_harness`, ESP32-S3 N16R8, Arduino, FastLED 3.10.3, `CRGB16`, `SQ15x16`, existing K1 harness scripts.

---

## 0. Current Truth

[FACT] Latest verified base at handover creation:

```bash
git status --short --branch
git rev-parse --short HEAD
git rev-parse --short origin/refactor/main
```

Expected at creation time:

```text
## refactor/main
HEAD = ed22d33
origin/refactor/main = ed22d33
```

[FACT] Completed ratified refactor scope:

- Spike #2 aggregate-init check.
- Row 3 globals subset relocation.
- Row 4 render/LED multi-TU safety.
- Row 2 per-mode `light_mode_*.cpp` split.
- Row 1 A+B serial dispatch table and safety guards.

[FACT] Not completed and not currently authorised as broad housekeeping:

- Full monolith teardown.
- Rows 5/6/7: `system.h`, AP/GDFT/audio headers, persistence/knob/button leftovers, `.ino -> main.cpp`.
- Full independent visual processors.
- Full release feature recovery.

[FACT] Current build surface is not the stale ESP32-S2 Arduino CLI path from the 2026-05-22 plans. Current `platformio.ini` uses:

```text
default_envs = k1_hardware
board = esp32-s3-devkitc1-n16r8
upload_port = /dev/tty.usbmodem1101
monitor_port = /dev/tty.usbmodem1101
build_src_filter = +<*.ino> +<*.ino.cpp> +<globals_config.cpp> +<globals.cpp> +<Palettes.cpp> +<light_mode_*.cpp>
```

Do not use the old ESP32-S2 Arduino CLI compile command from `2026-05-22-secondary-channel-renderer.md` unless Captain explicitly asks to reproduce that old checkpoint.

## 1. Mandatory Read Order

Before editing code, read in this order:

1. `.claude/CLAUDE.md`
2. `.claude/skills/k1-firmware-change-gate/SKILL.md`
3. `.claude/skills/sensorybridge-doctrine/SKILL.md`
4. `AGENTS.md`
5. `docs/refactor/harness-baselines/freeze-88428a2/CANONICAL.md`
6. `docs/superpowers/plans/2026-05-22-secondary-channel-renderer.md`
7. `docs/superpowers/plans/2026-05-22-release-feature-recovery-roadmap.md`
8. `docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md`

Then output the K1 firmware gate before touching firmware:

```markdown
Current truth:
Change class:
Files/seams touched:
Known breakage avoided:
State ownership:
Runtime validation required:
Minimal edit plan:
Explicit non-goals:
Stop conditions:
```

## 2. Operating Rules

- Serial capture, upload/flash, erase, and device-write actions are allowed when validation requires them, but verify the target by port plus stable hardware identity before interacting with the device.
- Never auto-run `start_noise_cal`. It remains `N` arm -> `Y` confirm under Captain-confirmed silence.
- Use branches, commits, and tags as rollback tools after diff review and relevant tests/builds. Never commit untested or unreviewed work; remote push, destructive history changes, and release tags require explicit Captain instruction or an active publication lane.
- Build success is not a functional result.
- Runtime claims require matching source commit, binary/env, serial/timing/video capture, and board identity.
- If the task touches secondary render, palette/manual/auto-colour ownership, Bloom/Waveform history, Kaleidoscope/Quantum/Dot state, AP/GDFT, destructive serial commands, or LED output quantisation, apply the K1 firmware gate strictly.
- After two failures of the same kind, stop and report the failure mechanism.

## 3. Immediate Recommendation

Do not jump straight to Bloom, Kaleidoscope, Waveform polish, new modes, GDFT changes, or UI transitions.

Next authorised engineering lane is implementation-first:

1. Implement `RenderParams` containment so secondary render stops overwriting global `CONFIG`.
2. Implement `ChannelEffectState` for VU Dot and Kaleidoscope so stateful modes stop sharing function-local statics.
3. Run the smallest build/runtime acceptance for those patches.
4. Resume release feature recovery.

Rationale:

- The old secondary plan completed shared channel dispatch only.
- Current source still snapshots/restores global `CONFIG` for secondary render.
- Stateful modes still retain local statics or global state.
- Runtime budget with secondary enabled is measured as part of implementation acceptance, not as a standalone deliverable.

## 4. Current Secondary Render Shape

[FACT] Current source already contains:

- `RenderChannelState` in `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- `RenderRuntimeSnapshot`
- `make_primary_channel()`
- `make_secondary_channel()`
- `apply_secondary_render_config()`
- `render_lightshow_for_channel(...)`
- per-channel Waveform / Waveform Fast / Waveform Hybrid / VU state entry points

[FACT] Current secondary pass still does this:

```cpp
RenderRuntimeSnapshot render_snapshot = capture_render_runtime();
memcpy(leds_16_primary_snapshot, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
RenderChannelState secondary_channel = make_secondary_channel();
apply_secondary_render_config();
vp_render_secondary_channel = true;
render_lightshow_for_channel(SECONDARY_LIGHTSHOW_MODE, secondary_channel);
store_render_channel_output(secondary_channel);
memcpy(leds_16, leds_16_primary_snapshot, sizeof(CRGB16) * NATIVE_RESOLUTION);
restore_render_runtime(render_snapshot);
```

[INFERENCE] This is a useful containment layer, not final independence. It prevents many obvious branch divergences, but secondary output still depends on global render parameters during each mode body.

## 5. Known Shared-State Hotspots

Source scan at handover creation found these specific remaining hazards:

| Area | Evidence | Risk | First treatment |
|---|---|---|---|
| Secondary config | `apply_secondary_render_config()` mutates `CONFIG.*` | secondary render is scoped by save/restore, not immutable params | introduce `RenderParams` and mode read helpers |
| Kaleidoscope | `light_mode_kaleidoscope.cpp` has `static pos_r/g/b` and `brightness_low/mid/high` | primary/secondary can share motion state | move to channel-owned state before relying on dual-channel Kaleidoscope |
| Quantum | `light_mode_quantum_collapse.cpp` has static arrays and random updates | non-deterministic, shared state, high memory if duplicated blindly | keep nondet gate; do not dual-channel-trust until explicitly isolated |
| VU Dot | `light_mode_vu_dot.cpp` has static dot/level/max state | channel bleed/reset risk | move into `ChannelEffectState` |
| Dot/global state | `dots[]` saved in probe; chromagram dots use shared dot helpers | possible cross-channel dot motion bleed | map exact dot ownership before code |
| Colour authority | palette/manual/auto-colour paths read channel flag + globals | palette and auto-colour can fight if ownership is unclear | preserve single authority per frame |
| Bloom/Waveform history | history buffers are channel-owned but display/transport history can be polluted by later edits | loss of motion memory | keep display-only fades/mirror out of transport history |

## 6. Task 0: Implement RenderParams Containment

**Goal:** Remove secondary render's dependence on mutating global `CONFIG` as the source of truth.

**Files likely touched:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h`
- Modify: selected `SPECTRASYNQ_K1_FIRMWARE/light_mode_*.cpp`
- Test: `pio run -e k1_hardware`
- Test: `pio run -e k1_hardware_harness`
- Runtime: existing VP harness only if Captain authorises upload/serial

Implementation constraint:

- Do not convert every mode and every global in one commit.
- First pass should carry existing behaviour, not change visuals.
- Keep `CONFIG` as persisted primary config.
- Add an active render parameter view for modes to read while rendering.
- Preserve `vp_render_secondary_channel` until all palette/ownership call sites have a better context.

Function list to implement:

```cpp
struct RenderParams;
RenderParams make_primary_render_params();
RenderParams make_secondary_render_params();
RenderParams make_probe_render_params();
void set_active_render_params(const RenderParams* params);
const RenderParams& active_render_params();
```

Fields required in `RenderParams`:

```text
lightshow_mode
photons
chroma
mood
mirror_enabled
saturation
auto_color_shift
incandescent_filter
incandescent_mode
palette_index
palette_mode_enabled
prism_count
```

- [ ] Add `RenderParams` where every `light_mode_*.cpp` can include it.
- [ ] Add primary/secondary/probe builders in `SPECTRASYNQ_K1_FIRMWARE.ino`.
- [ ] Replace secondary-pass `apply_secondary_render_config()` dependency for converted modes with `active_render_params()`.
- [ ] Convert GDFT, chromagram gradient, and chromagram dots first.
- [ ] Convert Bloom, Waveform, and VU after the low-risk modes compile and pass probe checks.
- [ ] Leave Kaleidoscope, Quantum, and VU Dot on current path until `ChannelEffectState` exists.

Acceptance:

- No visual-intent changes.
- `CONFIG` no longer needs to be overwritten for secondary render in the converted subset.
- Primary render output remains within the freeze gate.
- Secondary render still works with different mode/palette/mood/chroma/saturation.

## 7. Task 1: Implement ChannelEffectState For VU Dot And Kaleidoscope

**Goal:** Move stateful mode internals out of shared function-local statics where dual-channel bleed is possible.

**Files likely touched:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/light_mode_kaleidoscope.cpp`
- Modify: `SPECTRASYNQ_K1_FIRMWARE/light_mode_vu_dot.cpp`
- Modify: later only if approved: `SPECTRASYNQ_K1_FIRMWARE/light_mode_quantum_collapse.cpp`

Function list to implement:

```cpp
struct ChannelEffectState;
ChannelEffectState& primary_effect_state();
ChannelEffectState& secondary_effect_state();
ChannelEffectState& active_effect_state();
void reset_channel_effect_state(ChannelEffectState& state);
```

State fields required now:

```text
VU Dot:
- dot position / previous position
- smoothed VU level
- max level / decay memory

Kaleidoscope:
- pos_r / pos_g / pos_b
- brightness_low / brightness_mid / brightness_high
```

Implementation order:

1. VU Dot state: small and contained.
2. Kaleidoscope state: visible and load-bearing.
3. Quantum state: hold unless Captain explicitly wants it; it is nondeterministic and memory-heavy.

Required rule:

- `ChannelEffectState` must not allocate heap in render.
- State arrays must be static/global storage or owned by existing channel structs.
- If Quantum arrays are duplicated, estimate memory before code and report it.

Acceptance:

- Primary and secondary can run VU Dot/Kaleidoscope separately without shared phase or brightness state.
- VP Tier A remains valid for deterministic modes.
- Quantum remains explicitly nondeterministic unless redesigned.

## 8. Task 2: Secondary Runtime Acceptance

**Goal:** Prove Stage 1 exit from the roadmap: primary and secondary can run different stateful modes for 120 seconds without visible bleed or state reset.

Required cases:

```text
primary BLOOM + secondary WAVEFORM_FAST
primary WAVEFORM_HYBRID + secondary BLOOM_FAST
primary KALEIDOSCOPE + secondary VU_DOT
primary CHROMAGRAM + secondary BLOOM
palette mode primary on / secondary off
palette mode secondary on / primary off
auto colour primary on / secondary palette on
```

Acceptance inputs:

- `vp_perf=start` for at least 120 seconds with secondary enabled.
- `vp_perf=status` after the run.
- `vp_status` and `secondary_status` before and after.
- Video or Captain hardware-visible report for state bleed/reset.

Pass condition:

- No visible cross-channel state reset or bleed.
- No render budget regression beyond Captain-approved threshold.
- No palette/manual/auto-colour authority fight.
- No display-only fade/mirror feeding transport history.

## 9. Task 3: Resume Release Feature Recovery

Only start after Task 2 passes or Captain explicitly overrides the risk.

Order:

1. Bass/range/notation colour.
2. GDFT correctness and measured profile.
3. Waveform/DC offset.
4. Bloom Stargate.
5. Kaleidoscope reclaim.
6. Transitions/UI.

Hard holds:

- Do not resurrect old 8-bit Bloom wholesale.
- Do not simply uncomment `lookahead_smoothing()`.
- Do not blindly re-enable Hann/interlacing.
- Do not spend feature budget on full UI graph before headroom validation.
- Do not make Auto Colour Shift an uncontrolled hue-wheel sweep.
- Do not use historical release notes as product truth without source and runtime validation.

## 10. New Light Mode Checklist

Use this only after Stage 1 secondary isolation or for a deliberately small sandbox mode.

Required touches:

```text
SPECTRASYNQ_K1_FIRMWARE/config_types.h
SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h
SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
SPECTRASYNQ_K1_FIRMWARE/system.h
SPECTRASYNQ_K1_FIRMWARE/light_mode_<name>.cpp
SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h vp_probe roster
```

Rules:

- Append enum only; never reorder existing IDs.
- Add exactly one `light_mode_<name>.cpp`.
- Centre-origin by default.
- No default rainbow/full hue-wheel sweep.
- No heap in render.
- Add VP probe coverage, or explicit nondeterministic exclusion.
- Measure secondary-enabled perf before promotion.

## 11. Final Handover Standard For The Next Agent

The next agent's final response must state:

```text
STATUS:
SOURCE STATE:
FILES CHANGED:
BUILDS/TESTS:
VALIDATION:
SECONDARY INDEPENDENCE VERDICT:
FEATURE ROADMAP POSITION:
HELD RISKS:
NEXT SINGLE ACTION:
```

Do not split implementation into a standalone validation task. Build, probe, and hardware checks belong to the acceptance section of the code patch that required them.
