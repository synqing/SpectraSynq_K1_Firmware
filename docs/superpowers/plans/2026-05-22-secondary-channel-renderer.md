# Secondary Channel Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the duplicated primary/secondary render branches with one shared channel render path that keeps primary and secondary state independent.

**Architecture:** Keep the existing global-effect implementation intact for this pre-S3 step, but isolate channel state at the dispatch boundary. Each channel owns its trail/history buffer and per-mode state; the global `leds_16` buffer becomes a scratch render target that is copied into the selected channel output.

**Tech Stack:** Arduino C++ firmware, FastLED, fixed-point `SQ15x16`, existing `CRGB16` buffers.

---

## File Structure

- Modify `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
  - Add `RenderChannelState`, `RenderRuntimeSnapshot`, and channel render helpers after the global benchmark variables.
  - Replace duplicated primary/secondary lightshow dispatch in `led_thread()` with the shared helpers.
- Verify with clean `arduino-cli compile --clean` using the existing ESP32-S2 FQBN.

## Staging Strategy

- Commit 1: existing checkpoint before the refactor. Completed as `de4fc48 chore: checkpoint sensory bridge firmware state`.
- Commit 2: secondary channel renderer refactor only. Stage `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` and this plan.
- Commit 3: research/onwards plan artefacts only, after the SSA audit returns.

### Task 1: Shared Channel Render Dispatch

**Files:**
- Modify: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino`
- Test: clean Arduino compile

- [x] **Step 1: Add channel state structs**

Add this after the benchmark state variables:

```cpp
struct RenderChannelState {
  CRGB16* history;
  CRGB16* output;
  bool seed_history_before_render;
  CRGB16* waveform_fast_last_color;
  float* waveform_fast_peak_scaled_last;
  CRGB16* waveform_last_color;
  float* waveform_peak_scaled_last;
  float* waveform_shift_accum;
  uint32_t* waveform_last_frame_ms;
  CRGB16* waveform_hybrid_last_color;
  float* waveform_hybrid_peak_scaled_last;
  float* waveform_hybrid_shift_accum;
  uint32_t* waveform_hybrid_last_frame_ms;
  SQ15x16* vu_level_smooth;
  SQ15x16* vu_max_level;
};
```

- [x] **Step 2: Add shared dispatch helper**

Add a `render_lightshow_for_channel(uint8_t mode, RenderChannelState& channel)` function. It must call the existing lightshow functions exactly once per mode and must pass the channel-owned waveform/VU state into waveform/VU modes.

- [x] **Step 3: Add secondary config snapshot helper**

Add a `RenderRuntimeSnapshot` struct that stores the global render state currently saved inline in `led_thread()`: `CONFIG`, `hue_position`, `chroma_val`, `chromatic_mode`, `hue_shifting_mix`, `base_coat_width`, `base_coat_width_target`, and `vp_render_secondary_channel`.

- [x] **Step 4: Replace primary dispatch**

Replace the primary `if/else` mode ladder in `led_thread()` with:

```cpp
RenderChannelState primary_channel = make_primary_channel();
vp_render_secondary_channel = false;
render_lightshow_for_channel(CONFIG.LIGHTSHOW_MODE, primary_channel);
```

Keep primary prism and bulb-cover post-processing unchanged.

- [x] **Step 5: Replace secondary dispatch**

Replace the secondary `if/else` mode ladder and manual config restore with:

```cpp
RenderRuntimeSnapshot snapshot = capture_render_runtime();
memcpy(leds_16_primary_snapshot, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
RenderChannelState secondary_channel = make_secondary_channel();
apply_secondary_render_config();
vp_render_secondary_channel = true;
render_lightshow_for_channel(SECONDARY_LIGHTSHOW_MODE, secondary_channel);
if (!VP_FIX_PRISM_DEFAULT_OFF && SECONDARY_PRISM_COUNT > 0) {
  apply_prism_effect(SECONDARY_PRISM_COUNT, 0.25);
}
memcpy(leds_16_secondary, leds_16, sizeof(CRGB16) * NATIVE_RESOLUTION);
clip_led_values(leds_16_secondary);
memcpy(leds_16, leds_16_primary_snapshot, sizeof(CRGB16) * NATIVE_RESOLUTION);
restore_render_runtime(snapshot);
```

- [x] **Step 6: Verify**

Run:

```bash
rm -rf SPECTRASYNQ_K1_FIRMWARE/build
arduino-cli compile --clean --fqbn "esp32:esp32:esp32s2:CDCOnBoot=cdc,MSCOnBoot=default,DFUOnBoot=default,UploadMode=cdc,FlashSize=4M,PartitionScheme=min_spiffs,PSRAM=enabled,CPUFreq=240,UploadSpeed=921600,DebugLevel=none" --libraries "/Users/spectrasynq/SensoryBridge-main 9/libraries" --libraries "/Users/spectrasynq/Documents/Arduino/libraries" --build-path "/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/build" "/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE"
```

Expected: compile exits `0`.

- [x] **Step 7: Commit**

```bash
git add docs/superpowers/plans/2026-05-22-secondary-channel-renderer.md SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
git commit -m "refactor: isolate secondary channel render dispatch"
```

## Result

- Commit: `039c78a refactor: isolate secondary channel render dispatch`
- Build: clean Arduino compile exited `0` for the ESP32-S2 FQBN used by this checkout.
- Scope completed: duplicated primary/secondary mode ladders were replaced with shared channel dispatch, and Bloom/Waveform/VU state now enters through `RenderChannelState`.
- Remaining truth: this is a pre-S3 containment refactor, not proof of full independent visual processors. Several effect internals still use shared globals or static state and must be isolated in the next render-context pass before claiming complete dual-personality behaviour.
