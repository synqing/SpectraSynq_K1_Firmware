---
abstract: "Verbatim output of Plan Agent 2 (2026-05-24) — post-refactor architectural target design for K1 SensoryBridge firmware. Module list, dependency DAG, header/source split rules, file organization, globals strategy, build structure, anti-patterns forbidden, current-file→new-module migration table, acceptance criteria. AUDIT-FLAGGED on several specific claims (incandescent_lookup file location, lightshow mode count, serial command count). Treat as design draft, not as ratified architecture."
---

# Plan Agent 2 — Architectural Target (Verbatim Draft)

> Recorded verbatim from the 2026-05-24 Phase 2 design dispatch. Audit flagged several source-location claims as wrong; K1-rooted session must re-verify.

---

## 0. Design constraints carried from current code

Before listing modules, the facts the design has to respect (verified against current source by Plan Agent 2 — note: that verification was done via the agent's read access, not by the orchestrator; subsequent audit identified some claims as inaccurate):

- `setup()` at line 338 of the `.ino` allocates `waveform_history` via `heap_caps_malloc(MALLOC_CAP_SPIRAM)` *before* `init_system()` — startup heap allocation must remain legal in the `setup()` path even though render-time heap is banned.
- `i2s_samples_raw[1024]` is `DRAM_ATTR`; `process_GDFT()` and `interpolate()` are `IRAM_ATTR`. Hot-path placement attributes survive the split.
- LED buffers (`leds_16`, `leds_16_prev`, `leds_16_prev_secondary`, `leds_16_temp`, `leds_16_ui`, `leds_16_fx`, `leds_16_secondary`) and dynamic pointers (`leds_scaled`, `leds_out`, `leds_scaled_secondary`) are *shared* between the audio core (loop) and the render core (`led_thread` pinned to core 1). The boundary between "audio-loop owned" and "render-thread owned" state is real and must be made explicit.
- `ENABLE_VP_PERF_AUDIT` is a build flag with macro fences sprinkled through `loop()`. Macros must move to one header and remain compile-fenced — never resolved at runtime in the render path.
- **141 strcmp dispatch arms in `serial_menu.h`** (corrected count vs. the 125 figure from Agent 2). All on a single 80 KB header. **AUDIT-CONTRADICTED — audit found 186 strcmp lines. K1-rooted session re-verifies.**
- `setup()` does a banned-during-runtime thing: it `heap_caps_malloc()`s. This is allowed because it runs before the render task is created. Document the lifecycle rule rather than blanket-banning the API.

---

## 1. Module list

Modules are grouped by their layer in the dependency DAG. "HOT" = runs every audio chunk or every LED frame (no heap, no log spam, no exceptions). "WARM" = runs on user input / periodic check (1 Hz–100 Hz). "COLD" = boot / serial command / persistence only.

### Layer 0 — Platform & types (leaf, depends on nothing in-project)

**`platform/hardware_constants.h`** — COLD/leaf
- Responsibility: board pin map, derived flags, build-time feature flags.
- Public interface: `constexpr` pin numbers, `#define SB_K1_HARDWARE`, `SB_HAS_ROTATE8`, `SB_USB_CUSTOM_DESCRIPTORS`, `NUM_FREQS`, `NATIVE_RESOLUTION`, `NUM_AGC_BANDS`, AGC band boundaries, `VP_PERF_*` budget macros.
- Private: none (header-only).
- Globals owned: none.
- Current files mapping: all of `constants.h` (lines 1–~120) plus the build-flag fences currently sprinkled in headers.

**`platform/types.h`** — leaf
- Responsibility: project-wide value types.
- Public interface: `struct CRGB16`, `struct DOT`, `struct KNOB`, `enum lightshow_modes` (currently in `.ino` — moves here), `enum agc_band_t`, `enum knob_names`, `enum led_types`, `enum blending_modes`, `enum VPProfileMode`.
- Private: none.
- Globals owned: none — definitions only, no instances.
- Current files mapping: type sections of `constants.h` lines 134–end, enum at top of `.ino`, `enum blending_modes` from `led_utilities.h` line 24, `enum VPProfileMode` from `globals.h` line 340.

**`platform/fixed_math.h`** — leaf
- Responsibility: thin wrapper around vendored FixedPoints + the `SQ15x16` and `CRGB16` arithmetic helpers used everywhere.
- Public interface: include FixedPoints, declare `interpolate()` (IRAM_ATTR), `clip_float`, `random_float`.
- Globals owned: none.
- Current files mapping: `utilities.h` (math-only portion).

### Layer 1 — Configuration

**`config/config.h` / `config/config.cpp`** — WARM
- Responsibility: define `struct conf`, expose `CONFIG`, `CONFIG_DEFAULTS`, provide `restore_defaults()`.
- Public interface: `struct conf` definition; `extern conf CONFIG;`, `extern conf CONFIG_DEFAULTS;`, `void restore_defaults();`, `void apply_preset(const char* name);`.
- `.cpp` holds: the actual `conf CONFIG = { ... }` aggregate initializer (load-bearing — moves byte-identical from current `globals.h` line 64), `restore_defaults()`, `set_preset()` body.
- Globals owned: `CONFIG`, `CONFIG_DEFAULTS`, `mode_names[NUM_MODES*32]`.
- Current files mapping: `globals.h` lines 18–117, all of `presets.h`.

**`config/persistence.h` / `config/persistence.cpp`** — COLD
- Responsibility: LittleFS save/load of CONFIG, noise calibration, ambient noise.
- Public interface: `void init_fs();`, `int save_configuration();`, `int load_configuration();`, `void save_config_delayed();`, `void save_ambient_noise_calibration();`, `void load_ambient_noise_calibration();`, `void factory_reset();`.
- Globals owned: filesystem handle state.
- Current files mapping: all of `bridge_fs.h` (301 LOC).

### Layer 2 — Core state

**`core/state.cpp` + `core/state.h`** — split-purpose
- Responsibility: the *one TU* that defines globals shared across module boundaries. `state.h` is `extern`-only.
- Public interface: `extern` declarations for everything in §5 (Globals strategy).
- Globals owned: shared cross-module state only (LED buffers, audio buffers, current spectrogram, hue position, FPS counters, debug flags). **Not** module-internal accumulators.
- Static-init-order rule: aggregate initializers preserved byte-identical from current source. No constructor calls in static-init that depend on `CONFIG` (this is exactly the `clk_rate=12800` class of bug). Anything CONFIG-dependent moves to `init_system()`.

### Layer 3 — Audio hot path

**`audio/capture.h` / `audio/capture.cpp`** — HOT
- Responsibility: I2S driver init, sample acquisition, DC-offset handling, AGC v2, sweet-spot level computation, VU calculation.
- Public interface: `void init_i2s();`, `void acquire_sample_chunk(uint32_t t_now);`, `void calculate_vu();`, `void init_cochlear_agc();`.
- Private impl: I2S driver setup, DMA queue management, the 2-layer DC_OFFSET guard (Fix-D), AGC v2 internals.
- Globals owned (module-private statics or true shared exports):
  - Private statics: I2S handle, AGC state arrays.
  - Exported via `state.h`: `i2s_samples_raw[1024]` (DRAM_ATTR), `sample_window`, `silence`, `silent_scale`, `current_punch`, `dc_offset_sum`, `dc_offset_samples`.
- Current files mapping: all of `i2s_audio.h` (500 LOC).

**`audio/analysis.h` / `audio/analysis.cpp`** — HOT
- Responsibility: GDFT, post-processing, spectrogram smoothing, chromagram, novelty.
- Public interface: `void process_GDFT();` (IRAM_ATTR), `void calculate_novelty(uint32_t t_now);`, `void get_smooth_spectrogram();`, `void precompute_goertzel_constants();`, `void generate_a_weights();`, `void generate_window_lookup();`.
- Private impl: Goertzel inner loops, spectral history rolling buffer.
- Globals owned: `spectrogram`, `spectrogram_smooth`, `chromagram_smooth`, `spectral_history`, `novelty_curve`, `note_spectrogram[*]`, `note_chromagram[12]`, `chromagram_max_val`, `frequencies[NUM_FREQS]`, `window_lookup[4096]`, `a_weight_table[13][2]`.
- Current files mapping: all of `GDFT.h` + the spectrogram/chromagram block of `globals.h` lines 160–185 + `precompute_*` from `system.h`.

**`audio/noise_cal.h` / `audio/noise_cal.cpp`** — WARM (only runs during cal)
- Responsibility: noise calibration state machine, ambient noise capture, calibration command policy gate.
- Public interface: `void start_noise_cal();`, `void clear_noise_cal();`, `bool noise_cal_in_progress();`.
- Globals owned: `noise_iterations`, calibration accumulator arrays.
- Current files mapping: `noise_cal.h` (27 LOC — trivial) + the noise-cal globals currently in `globals.h`.

**`audio/dump_raw.h` / `audio/dump_raw.cpp`** — COLD (diagnostic only)
- Responsibility: raw-PCM dump command implementation. Isolated because it's a diagnostic that touches hot-path buffers but runs from the serial command surface.
- Public interface: `void dump_raw_command();`, `void dump_command();`.
- Current files mapping: `dump_raw` arm extracted from `serial_menu.h` line 966 and from `i2s_audio.h`'s dump helpers.

### Layer 4 — Color & render hot path

**`color/pipeline.h` / `color/pipeline.cpp`** — HOT
- Responsibility: HSV→RGB, hue interpolation, desaturation, incandescent filter, clipping, dithering quantization.
- Public interface: `CRGB16 hsv(SQ15x16 h, SQ15x16 s, SQ15x16 v);`, `CRGB16 interpolate_hue(SQ15x16 hue);`, `CRGB16 desaturate(...);`, `CRGB16 adjust_hue_and_saturation(...);`, `void clip_led_values(CRGB16* buf);`, `void apply_incandescent_filter();`, `void force_incandescent_colour(CRGB16* layer, uint16_t count);`, `void apply_brightness();`, `void quantize_color(bool temporal_dithering);`.
- Private impl: `incandescent_lookup[]` table (load-bearing — keep aggregate init byte-identical; this is the 2025-09-19 incident anchor).
- Globals owned: color lookup tables, `hue_position`, `chroma_val`, `chromatic_mode`, `hue_shifting_mix`.
- Current files mapping: top half of `led_utilities.h` (lines ~30–500).

**AUDIT-FLAGGED: Plan Agent 2 claimed `incandescent_lookup` lives in `led_utilities.h`. Audit found it at `constants.h:439`. K1-rooted session must re-locate the table and any others claimed at incorrect locations.**

**`color/palettes.h` / `color/palettes.cpp`** — leaf (read-only tables)
- Responsibility: palette table storage.
- Public interface: `extern const TProgmemPalette16 sb_palettes[N];`, `void set_palette(uint8_t idx);`.
- Globals owned: 33 gradient palette tables (PROGMEM).
- Current files mapping: all of `Palettes.h` (567 LOC) — split table definitions into `.cpp`, leave `extern` and accessor in `.h`.

**`render/buffers.h`** — leaf
- Responsibility: declare LED buffer ownership semantics. Header-only `extern` declarations + comments documenting which thread reads/writes each buffer.
- Globals owned (extern only): all `CRGB`/`CRGB16` arrays from `globals.h` lines 224–280 and 640–650. Actual definitions live in `core/state.cpp`.

**`render/modes/`** — HOT, one TU per mode
- Each of the 9 modes (per the `lightshow_modes` enum at `.ino` line 58) gets its own `.cpp`:
  - `modes/gdft.cpp` — `light_mode_gdft()`
  - `modes/gdft_chromagram.cpp` — `light_mode_gdft_chromagram()`, `light_mode_chromagram_gradient()`
  - `modes/gdft_chromagram_dots.cpp` — `light_mode_chromagram_dots()`
  - `modes/bloom.cpp` — both overloads of `light_mode_bloom()`, `light_mode_bloom_fast()`
  - `modes/vu.cpp` — `light_mode_vu()`, `light_mode_vu_dot()`
  - `modes/waveform_fast.cpp` — `light_mode_waveform_fast()` + `waveform_shift_upper_half_up()`
  - `modes/waveform.cpp` — `light_mode_waveform()` + `waveform_shift_outward()`
  - `modes/waveform_hybrid.cpp` — `light_mode_waveform_hybrid()`
  - `modes/kaleidoscope.cpp` and `modes/quantum_collapse.cpp` — *Captain decides: keep or delete*; the enum currently lists more than 9 active modes. Mark these as "candidates for strip phase."
- Public interface: one header `render/modes/modes.h` with all mode entry-point declarations.

**AUDIT-FLAGGED: Audit confirms 13 distinct `light_mode_*` definitions. Plan Agent 2 partially caught this ("more than 9 active modes") but final plan used 9 as the count. K1-rooted session: re-verify exact list.**

**`render/pipeline.h` / `render/pipeline.cpp`** — HOT
- Responsibility: post-FX chain, dual-strip scaling, FastLED `show()`, mirror/unmirror, `scale_to_strip`, `scale_to_secondary_strip`, `apply_brightness_secondary`, `show_secondary_leds`, dispatch (calls the active mode renderer).
- Public interface: `void render_lightshow_for_channel(uint8_t mode, RenderChannelState& ch);`, `void store_render_channel_output(RenderChannelState& ch);`, `void show_leds();`, `void show_secondary_leds();`, `void run_transition_fade();`, `void render_ui();`, `void render_noise_cal();`.
- Private impl: `RenderChannelState` and `RenderRuntimeSnapshot` structs (currently in `.ino` lines 125–152), the LED thread body `led_thread()`.
- Globals owned: `leds_scaled`, `leds_scaled_secondary`, transition state, UI overlay state.
- Current files mapping: bottom half of `led_utilities.h` (lines ~500–2045), render plumbing currently in the `.ino`.

**`render/sweet_spot.h` / `render/sweet_spot.cpp`** — WARM
- Responsibility: PWM L/C/R sweet-spot indicator LEDs. Isolated because it's optional and depends on Captain's keep/delete ruling.
- Public interface: `void init_sweet_spot();`, `void run_sweet_spot();`, `void write_sweet_spot_pwm(uint8_t channel, uint32_t duty);`.
- Current files mapping: sweet-spot block of `led_utilities.h` lines ~153–195 + init from `system.h`.

**NOTE FROM HANDOFF AUTHOR: Captain clarified separately that the SS AP algorithm is a separate concern from the SS LED output and must be investigated before any strip decision. Plan Agent 2's module split correctly separated `render/sweet_spot` (LED output) — but did NOT separately identify the SS AP algorithm location. K1-rooted session: source-trace where the SS AP algorithm lives (likely in `audio_transfer.h` or in `audio/capture.cpp` equivalent post-split) and ensure it's NOT confused with `render/sweet_spot`.**

### Layer 5 — System orchestration

**`system/boot.h` / `system/boot.cpp`** — COLD
- Responsibility: ordered init sequence. Owns the static-init-order safety contract.
- Public interface: `void init_system();`, `void init_usb();`, `void init_leds();`, `void init_secondary_leds();`, `void enable_usb_update_mode();`.
- Private impl: the exact sequence currently in `system.h`'s `init_system()` (line 318). This is where CONFIG-dependent setup happens *after* CONFIG has been loaded — protecting against the `clk_rate=12800` class of bug.
- Globals owned: none (orchestrator only).
- Current files mapping: `init_*` functions in `system.h` (lines 102, 160, 178, 191, 227, 239, 318), all of `presets.h`'s init paths.

**`system/runtime.h` / `system/runtime.cpp`** — WARM
- Responsibility: per-loop settings check, mode transitions, FPS logging, debug timing.
- Public interface: `void check_settings(uint32_t t_now);`, `void log_fps(uint32_t t_now_us);`, `void run_transition_fade();`, `void process_color_shift();`.
- Globals owned: `mode_transition_queued`, `noise_transition_queued`, `SYSTEM_FPS`, `LED_FPS`, `last_frame_us`, `debug_mode`.
- Current files mapping: balance of `system.h` not absorbed by `boot.cpp`.

**`system/input.h` / `system/input.cpp`** — WARM
- Responsibility: knobs + buttons polling.
- Public interface: `void check_knobs(uint32_t t_now);`, `void check_buttons(uint32_t t_now);`.
- Current files mapping: all of `knobs.h` + `buttons.h`.

### Layer 6 — Optional peripherals (gated)

**`peripherals/encoders.h` / `peripherals/encoders.cpp`** — guarded by `SB_HAS_ROTATE8`
- Responsibility: M5ROTATE8 encoder polling + LEDs.
- The header always exists; the `.cpp` is a no-op stub when `SB_HAS_ROTATE8 == 0`. Current K1 build: `SB_HAS_ROTATE8 == 0` — the entire module compiles to empty TUs but the link symbols stay so the dispatcher doesn't need ifdefs at call sites.

### Layer 7 — UI surface

**`ui/serial/dispatch.h` / `ui/serial/dispatch.cpp`** — COLD
- Responsibility: command parser, tx framing, `parse_command()` shell, dispatch table.
- Public interface: `void init_serial(uint32_t baud);`, `void check_serial(uint32_t t_now);`, `void tx_begin(bool error)`, `void tx_end(bool error)`, `void ack()`, `void bad_command(...)`, `void stop_streams()`, `void dump_info()`.
- Internal: `parse_command()` becomes a dispatch on a **command table** (`{ const char* name; void (*handler)(const char* data); }`) rather than 141 chained `else if (strcmp(...))`. Each handler lives in the module it touches.

**AUDIT-FLAGGED: 141 strcmp arms per Plan Agent 2 vs 186 per audit. K1-rooted session re-counts.**

**`ui/serial/commands_audio.cpp`, `commands_render.cpp`, `commands_config.cpp`, `commands_vp.cpp`, `commands_debug.cpp`, `commands_diag.cpp`** — COLD
- Plan Agent 2 grouped the 141 handlers as: commands_audio (~25), commands_render (~30), commands_config (~35), commands_vp (~30+), commands_debug (~15), commands_diag (streaming). Total ~141 per Plan Agent 2.

### Layer 8 — Instrumentation

**`debug/vp_perf.h` / `debug/vp_perf.cpp`** — HOT (when enabled), COLD (when disabled)
- Responsibility: VP_PERF_AUDIT instrumentation. Macros centralized here.

**`debug/probes.h` / `debug/probes.cpp`** — COLD
- Responsibility: VP output probe (`vp_run_output_probe`, `vp_probe_*`).
- Current files mapping: `vp_probe_*` functions at lines 1679–1879 of `lightshow_modes.h`.

### Layer 9 — Entry point

**`main.cpp`** — Arduino sketch entry. `SPECTRASYNQ_K1_FIRMWARE.ino` renamed.

---

## 2. Dependency DAG (Plan Agent 2's proposal)

```
                      platform/hardware_constants  ──┐
                      platform/types               ──┤  (leaves)
                      platform/fixed_math          ──┘
                                  ▲
                      core/state  ◄──┐
                                  ▲   │
                  ┌───────────────┤   │
                  │               │   │
         config/config        debug/vp_perf
                  ▲               ▲
                  │               │
         config/persistence       │
                  ▲               │
        ┌─────────┴───────────┐   │
        │                     │   │
  audio/capture          audio/analysis ◄── audio/noise_cal
        ▲                     ▲
        │                     │
        └──────────┬──────────┘
                   │
          color/palettes ◄── color/pipeline
                              ▲
                       render/modes/*  (one TU per mode)
                              ▲
                       render/pipeline ◄── render/sweet_spot
                              ▲
                       system/runtime ◄── system/input
                              ▲
                       system/boot
                              ▲
                       peripherals/encoders  (optional)
                              ▲
                       ui/serial/dispatch
                              ▲
                  ┌───────────┼───────────┬─────────────┬──────────────┐
        cmd_audio   cmd_render   cmd_config   cmd_vp   cmd_debug   cmd_diag
                              ▲
                          main.cpp
                              ▲
                       (audio/dump_raw, debug/probes — diagnostic leaves)
```

---

## 3. Header/source split rules

**Allowed in `.h`:** forward decls, `extern` decls for globals, struct/class definitions (layout only), `constexpr` constants, `inline` accessors ≤5 lines no side effects, `#define` for compile-time config, `IRAM_ATTR`/`DRAM_ATTR` decorations on declarations.

**MUST be in `.cpp`:** any function body >5 lines, all global definitions, all lookup table definitions, anything with static-init dependence, all `DRAM_ATTR`/`IRAM_ATTR` storage definitions, anything that calls `Serial.print`.

**Aggregate-init preservation rule (LOAD-BEARING, the 2025-09-19 incident):** byte-identical initializer expression when moving globals header→cpp. Do NOT add explicit type constructors. Verify via `xtensa-esp32s3-elf-objdump -s -j .rodata` diff before vs after.

---

## 4. File organization (Plan Agent 2's proposal)

```
SPECTRASYNQ_K1_FIRMWARE/
├── main.cpp                          (was SPECTRASYNQ_K1_FIRMWARE.ino)
│
├── platform/
│   ├── hardware_constants.h, types.h, fixed_math.h, fixed_math.cpp
├── core/
│   ├── state.h (extern decls), state.cpp (THE one TU with shared global defs)
├── config/
│   ├── config.h, config.cpp, persistence.h, persistence.cpp
├── audio/
│   ├── capture.h, capture.cpp, analysis.h, analysis.cpp,
│   ├── noise_cal.h, noise_cal.cpp, dump_raw.h, dump_raw.cpp
├── color/
│   ├── pipeline.h, pipeline.cpp, palettes.h, palettes.cpp
├── render/
│   ├── buffers.h, pipeline.h, pipeline.cpp, sweet_spot.h, sweet_spot.cpp
│   └── modes/
│       ├── modes.h, gdft.cpp, gdft_chromagram.cpp, gdft_chromagram_dots.cpp,
│       ├── bloom.cpp, vu.cpp, waveform.cpp, waveform_fast.cpp, waveform_hybrid.cpp
├── system/
│   ├── boot.h, boot.cpp, runtime.h, runtime.cpp, input.h, input.cpp
├── peripherals/
│   ├── encoders.h, encoders.cpp
├── ui/serial/
│   ├── dispatch.h, dispatch.cpp,
│   ├── commands_audio.cpp, commands_render.cpp, commands_config.cpp,
│   ├── commands_vp.cpp, commands_debug.cpp, commands_diag.cpp
└── debug/
    ├── vp_perf.h, vp_perf.cpp, probes.h, probes.cpp
```

---

## 5. Globals strategy (Plan Agent 2's recommendation: hybrid)

Three buckets:

1. **Shared cross-module state** → `core/state.cpp` (defs) + `core/state.h` (`extern` decls). ~80 globals.
2. **Module-internal state mis-named as global** → `static`-scope inside the module's `.cpp`, NOT exported via any header. ~150 globals collapse here.
3. **Configuration state** → `config/config.cpp` defines `CONFIG`, `CONFIG_DEFAULTS`, `mode_names[]`.

**Rule revision:** "Every global has exactly one definition. Shared globals (referenced by `extern` from > 1 module's headers) live in `core/state.cpp`. Module-internal state lives `static`-scoped in the module's own `.cpp` and is never `extern`-declared in any header. `CONFIG` is the sole non-state.cpp shared global, defined in `config/config.cpp` because it's a domain concept, not raw state."

---

## 6. Build structure

```ini
[platformio]
default_envs = k1_hardware

[env:k1_hardware]                ; production
build_src_filter = +<**/*.cpp>   ; (was: +<*.ino> +<*.ino.cpp>)

[env:native]                     ; new — host unit tests
platform = native
build_src_filter = +<color/pipeline.cpp> +<audio/analysis.cpp> +<config/config.cpp>
test_framework = unity
build_flags = -DSB_NATIVE_BUILD -DUNIT_TEST
```

**`compile_commands.json` regeneration:** add `pio run -t compiledb` alias, document in `CLAUDE.md`.

**Build envelope acceptance:** flash within ±2% of 552 622 B; RAM within ±2% of 83 024 B. Consider adding `-flto` for size parity insurance.

---

## 7. Anti-patterns forbidden post-refactor

1. No function bodies in headers (except `inline` accessors ≤5 lines).
2. No global variable definitions in headers (extern only).
3. No `#include` of `.cpp` files.
4. No reaching across module boundaries by `extern` in a `.cpp`. Use `#include "module/header.h"`.
5. No `Serial.print` in hot-path `.cpp` files. Diagnostic dumps go through `debug/probes`.
6. No `new` / `malloc` / `heap_caps_malloc` outside `init_*()` and `setup()` allocation.
7. No `String` (Arduino) class. `const char*` and fixed `char[]` only.
8. No file-scope objects whose constructors read `CONFIG`.
9. No `#ifdef SB_HAS_ROTATE8` outside `peripherals/encoders.cpp` and `main.cpp`'s loop body. Use stub-TU pattern.
10. No `else if (strcmp(...))` chains > 5 arms. Use dispatch table.
11. No mutual `#include` cycles. Enforced via CI.
12. No silent shadowing. Compile with `-Wshadow`.

---

## 8. Migration table (Plan Agent 2's proposal)

| Current file (LOC per agent) | Splits into |
|---|---|
| `SPECTRASYNQ_K1_FIRMWARE.ino` (625) | `main.cpp` (~80 LOC) + `render/pipeline.cpp` + `peripherals/encoders.cpp` + `platform/types.h` |
| `serial_menu.h` (2351) | `ui/serial/dispatch.{h,cpp}` + 6 `commands_*.cpp` files |
| `led_utilities.h` (2045) | `color/pipeline.{h,cpp}` + `render/pipeline.{h,cpp}` + `render/sweet_spot.{h,cpp}`. `incandescent_lookup` → `color/pipeline.cpp` (byte-identical). **AUDIT: incandescent_lookup actually lives in constants.h:439, not led_utilities.h. K1-rooted session re-locates.** |
| `lightshow_modes.h` (1910) | 8 separate `render/modes/*.cpp` (per Plan Agent 2; audit suggests 13 actual modes) + `debug/probes.{h,cpp}` |
| `encoders.h` (914) | `peripherals/encoders.{h,cpp}` |
| `audio_transfer.h` (740) | Captain ruling needed: keep → `audio/transfer.{h,cpp}` or delete entirely. **Tentative: keep, isolate. ALSO: SS AP algorithm likely lives here — must not be confused with SS LED output module.** |
| `globals.h` (684) | `config/config.{h,cpp}` + `core/state.{h,cpp}` + `audio/capture.cpp` static-scope + `audio/analysis.cpp` static-scope + `debug/vp_perf.{h,cpp}` |
| `system.h` (585) | `system/boot.{h,cpp}` + `system/runtime.{h,cpp}` |
| `Palettes.h` (567) | `color/palettes.{h,cpp}` |
| `i2s_audio.h` (499) | `audio/capture.{h,cpp}` + `audio/dump_raw.{h,cpp}` |
| `bridge_fs.h` (301) | `config/persistence.{h,cpp}` |
| `GDFT.h` (332) | `audio/analysis.{h,cpp}` |
| `constants.h` (453) | `platform/hardware_constants.h` + `platform/types.h`. **Must also rehome incandescent_lookup if audit's location is right.** |
| `utilities.h` (108) | `platform/fixed_math.{h,cpp}` |
| `knobs.h` (85), `buttons.h` (83) | `system/input.{h,cpp}` |
| `presets.h` (47) | `config/config.cpp` |
| `noise_cal.h` (27) | `audio/noise_cal.{h,cpp}` |

---

## 9. Rationale (verbatim from Plan Agent 2)

**Why one TU per lightshow mode** — edits to `bloom.cpp` don't trigger rebuild of `gdft.cpp`. Captain deletes a mode by deleting one file. Cost (one `#include` per file) negligible; win (parallel compile + edit isolation + clean diffs) large.

**Why audio/color/render are sibling folders** — render calls into color and audio; color is reusable for UI overlays and noise-cal renderer; keeping siblings preserves reuse.

**Why per-module statics for 277+ globals instead of one big state.cpp** — the bug class isn't "globals exist," it's "anyone can touch any global." Mega-`state.cpp` doesn't fix that; it relocates the problem. Hiding AGC accumulators inside `audio/capture.cpp` as TU-local statics makes them physically unreachable from `render/`.

**Why dispatch table instead of strcmp chain** — 141 arms is O(N) per command and unreadable. Static dispatch table is O(log N) or O(1). Migration risk: strcmp behaves slightly differently from table lookup on edge cases — harness phase needs a regression test that fires all 141 commands.

**Why `native` env** — forcing function: a module that can't compile native has hidden Arduino/ESP-IDF coupling.

**Why UI at top, hot path at bottom** — serial commands call into modules they touch; modules don't know about serial. Inversion lets us swap UI surface later (e.g., BLE channel) without touching audio/render.

**Why `.ino` → `main.cpp`** — K1 build is PIO-only; `.ino` preprocess step was a migration footgun. Renaming eliminates preprocessing and `build_src_filter` complexity.

---

## 10. Acceptance criteria (Plan Agent 2's 22-item checklist — see final plan at `~/.claude/plans/transient-cuddling-wirth.md` for the canonical refined list)

A. Structural (6 items): zero function bodies in headers; no global defs in headers; no extern in cpp; no `.ino`; zero dependency cycles; size targets per file.

B. Build (4 items): clean `pio run -e k1_hardware`; ±2% envelope; clean `pio run -e native`; compile_commands.json regenerates.

C. Behavioral (4 items): K1 AP equivalence to commit `99a730b7`; 9 modes ≥50 FPS dual-strip; dump_raw byte-identical; ≤1% deadline-miss.

**AUDIT-FLAGGED: equivalence claim, 9-mode count both contradicted.**

D. Serial (2 items): 141 commands respond; vp_perf + start_noise_cal + dump_raw + restore_defaults + factory_reset functional parity.

E. Invariants (4 items): Fix-D preserved; VP_PERF_AUDIT zero symbols when disabled; `incandescent_lookup` byte-identical in `.rodata`; build flag policy documented.

F. Aspirational (3 items): fresh contributor can navigate; new mode = single-file add; new serial command = single-file add.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | claude-code (Opus 4.7) | Persisted Plan Agent 2's architectural target verbatim. Audit-flagged claims inline. Created during handoff to K1-rooted session. |
