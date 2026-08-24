---
abstract: "SensoryBridge K1 firmware (ESP32-S3): audio-reactive LEDs via Goertzel GDFT (80-bin frequency spectrum + 24 perceptual bands) + tempo tracking (PLL flywheel), onset detection (per-band log-flux), chord saliency, AGC. Dual-core: Core 0 = hard real-time audio pipeline; Core 1 = 100 FPS visual render. 30 enumerated lightshow modes, with 22 currently enabled by light_mode_is_enabled(). PlatformIO build (pioarduino 54.03.20, FastLED 3.10.3), comprehensive pytest host gate (54 test files, 427 tests at 2026-06-15). Audio-semantic forward-graft promoted to production (2026-06-05); device eyes-on is final gate. Code naming: sb_*() DSP functions, SB* structs, light_mode_* effects, snake_case actions. Load-bearing rules at .claude/CLAUDE.md."
---

# SensoryBridge K1 Firmware

Real-time audio-responsive lighting system that translates music into visual effects on dual-channel edge-lit LGP hardware. Powered by Goertzel-based spectral analysis, beat detection, and harmonic saliency tracking—delivering synchronized visual shows with <50ms latency.

## Quick Navigation

- **Agent OS (all tools):** Read **[`AGENT_OS.md`](./AGENT_OS.md)** first — session bootstrap, source-of-truth hierarchy, safety gates, thinking gate, skill awareness. Tool-agnostic; this is the canonical agent manual.
- **Build & Test:** See [Quick Start](#quick-start)
- **Load-Bearing Rules:** Read **[`.claude/CLAUDE.md`](./.claude/CLAUDE.md)** first (doctrine, discipline, gates)
- **Active Spec Index:** Read **[`docs/spec-index.md`](./docs/spec-index.md)** before firmware or forensic work (lane authority, handovers, recall)
- **Session Handoff:** [`.claude/handoff.md`](./.claude/handoff.md) — active lane pointer
- **Rolling Status:** [`progress.md`](./progress.md) — last 7 days
- **Architecture:** See [Architecture Overview](#architecture-overview)
- **Code Patterns:** See [Development Guidelines](#development-guidelines)
- **Hardware Details:** ESP32-S3-DevKitC-1-N16R8 (dual-core @ 240 MHz, 16 MB flash)

## Active Spec Index

Before firmware changes, device validation, or forensic lanes: read **[`docs/spec-index.md`](./docs/spec-index.md)** for the authoritative handover map, device identity table, and claude-mem recall conventions. On-disk handover beats memory for **current lane status**.

<!-- SPECKIT START -->
Active plan: none (no `specs/*/plan.md` in repo). Spec authority: [docs/spec-index.md](./docs/spec-index.md).
For additional context about technologies, project structure, and shell commands, see AGENTS.md and `.claude/CLAUDE.md`.
<!-- SPECKIT END -->

## What This Project Does

SensoryBridge is **not generic audio-reactive LEDs**. This firmware achieves perceptual impact through:

- **Real-time audio analysis:** Goertzel-based Discrete Fourier Transform (GDFT) at 133 Hz, computing 80 frequency bins across 24 perceptual bands
- **Beat and onset detection:** Periodicity-based tempo tracking with PLL phase-lock + per-band transient detection
- **Harmonic analysis:** Chord saliency tracking across root + 9 harmonics for musical responsiveness
- **Dual-channel independent effects:** Primary + secondary edge lighting with diffused plate emission
- **Adaptive gain:** AGC and silence-based noise calibration for home/live venue acoustics
- **Latency-critical rendering:** 100 FPS visual pipeline synced to audio (latency budget: <50ms audio-to-LED)

**The architecture is subordinate to perceptual impact.** Visual correctness, musical responsiveness, and colour clarity are non-negotiable. Before any changes to audio pipeline, visual rendering, or core timing, invoke the `/sensorybridge-doctrine` skill (see [Load-Bearing Rules](#load-bearing-rules)).

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Processor** | ESP32-S3 Xtensa dual-core | 240 MHz | Core 0 = audio pipeline (hard real-time); Core 1 = visual rendering (soft real-time) |
| **Memory** | 16 MB Flash (OPI PSRAM), 8 MB PSRAM + 512 KB SRAM | QIO mode | Full firmware + persistent state + diagnostic pools |
| **Build System** | PlatformIO + pioarduino | 6.1.19+, 54.03.20 | Canonical build (migrated from arduino-cli 2026-05-24) |
| **Framework** | Arduino | 3.2.0 (pioarduino) | ESP32-S3 HAL, I2S audio, GPIO, USB CDC |
| **I/O Driver** | Arduino ESP-IDF layer | 5.4.1 | I2S DMA, RMT5 LED protocol, FreeRTOS primitives |
| **LED Library** | FastLED | 3.10.3 | WS2812B/APA102 addressable strips via RMT5 DMA |
| **Language** | C++ | 17 standard | Firmware core, DSP algorithms, visual effects |
| **DSP Core** | Goertzel GDFT (custom) | v2 (2026-06-05) | Real-time spectrum (24 octave bands), onset, tempo, chord |
| **Audio I/O** | I2S peripheral | 12.8 kHz build contract | Hardware DMA circular buffer (non-blocking) |
| **Audio Pipeline Rate** | Goertzel frames | 133 Hz (96-sample chunks @ 12.8 kHz) | Beat, onset, chord updates; 100 FPS visual sync |
| **Testing** | pytest + custom harness | 3.x | Host regression (54 test files, 427 tests across static/replay/gates, offline metrics, A/B validation) |
| **Diagnostics** | MabuTrace (dev-only) | Custom | Timeline instrumentation for causal debugging |
| **Styling** | FastLED palettes + custom effects | Dynamic | Colour lookup, adaptive brightness, mode selection |

## Hardware Platform

**Target Device:** ESP32-S3-DevKitC-1-N16R8 (K1 reference)

- **CPU:** Dual-core Xtensa LX7 @ 240 MHz (simultaneous audio + rendering, independent Core assignments)
- **Flash:** 16 MB (OPI PSRAM, QIO mode for full bandwidth; full firmware footprint ~10–12 MB)
- **PSRAM:** 8 MB (effect state, diagnostic pools, audio snapshots)
- **Internal RAM:** 512 KB SRAM (audio buffers, hot DSP state, stack)
- **Audio Input:** I2S + MEMS microphone (PDM, or I2C ADC for alternative boards)
- **LED Output:** RMT5 peripheral to WS2812B/APA102 addressable strips (dual-channel, 128+ LEDs, DMA-driven)
- **USB:** CDC serial (commands, hotkeys, serial monitor; 115200 baud)
- **GPIO:** Control buttons (mode, noise calibration), status LEDs (sweet spot indicator)
- **Power:** 5V/2A (LED strip power draw limits available brightness)

## Quick Start

### Prerequisites

```bash
# PlatformIO environment
PlatformIO IDE or CLI (>=6.1.19)
pioarduino 54.03.20 (auto-installed by PIO)

# Python testing
Python 3.9+ with pytest (local host regression)

# Development
USB-C cable, 5V/2A power supply, compatible LED strip (WS2812B or APA102)

# Toolchain (auto-installed by PIO)
esp-idf 5.4.1, arduino-esp32 3.2.0, xtensa-esp32s3-elf
```

### Build & Upload

```bash
# Clone and navigate
git clone [repo-url]
cd "SensoryBridge-main 9"

# Build firmware (default: k1_hardware — production audio-semantic forward-graft)
pio run

# Upload to device (verifies USB MAC + chip ID via k1_upload_guard.py pre-script)
pio run --target upload

# Monitor serial output (115200 baud, live status + hotkey input)
pio device monitor

# Run full regression harness (host-only, no device needed)
pytest tests/ -v
```

### Build Environments

| Environment | Purpose | Status |
|-------------|---------|--------|
| `k1_hardware` | **Production** — audio-semantic forward-graft (v2 DSP, 2026-06-05) | Default, device eyes-on gate pending |
| `k1_bench_reference` | Alternative bench K1v2 GPIO map (same DSP, different pinout) | No instrumentation |
| `k1_hardware_trace_dev` | Development + MabuTrace timeline capture (non-shippable) | Dev-only |
| `k1_hardware_harness` | Diagnostic capture mode (AP/VP evidence surfaces) | Dev-only |
| `k1_ap_frontend_probe` | AP frontend diagnostics + replayable tempo input (2026-06-06) | Dev-only |
| `k1_motion_probe` | Apparent-motion perceptual test harness | Non-shippable |
| `k1_tempo_probe` | Beat/tempo-phase lock proof harness | Non-shippable |

**Current Status (2026-06-15):** Audio-semantic forward-graft (SB_TEMPO_CONF_V2, SB_TEMPO_FLYWHEEL_V2, SB_ONSET_V2, SB_CHORD_V2, SB_SEMANTIC_STATE, SB_CHORD_HUE_V1, SB_DROP_CUT_V1) promoted to k1_hardware default. Host regression gate PASS (427 tests across 54 test files; static, replay, and gates validated in the release-gate run). Tier 1 chord-hue consumer and impact-lane (drop-cut + attack-snap) additions hardened 2026-06-11. Device eyes-on testing is the one remaining gate before production release.

### Testing

```bash
# Full regression harness (metrics, replay, gates)
pytest tests/ -v

# Single test file (e.g., onset/beat validation)
pytest tests/test_onset_beat_replay.py -v

# Skip device-specific tests (host-only validation)
pytest tests/ -k "not device" -v

# Verbose output with timing breakdown
pytest tests/ -vv --durations=10

# Run only static analysis tests (no replay)
pytest tests/test_*_static.py -v
```

## Project Structure

```
project/
├── SPECTRASYNQ_K1_FIRMWARE/               # Main firmware source
│   ├── SPECTRASYNQ_K1_FIRMWARE.ino        # Arduino sketch entry point
│   ├── audio/                              # Audio pipeline (DSP modules)
│   │   ├── sb_tempo.cpp/.h                # Beat tracking, PLL flywheel, periodicity (v2)
│   │   ├── sb_onset_beat.cpp/.h           # Per-band onset detection, log-flux (v2)
│   │   ├── sb_chord_saliency.cpp/.h       # Chord root + harmonic tracking (v2)
│   │   ├── sb_audio_snapshot.cpp/.h       # AudioSemanticState publish surface
│   │   └── [additional DSP modules]
│   ├── visual/                             # LED rendering, colour, animation
│   │   ├── render_params.cpp/.h           # Brightness, chroma, smoothing control
│   │   ├── Palettes.cpp/.h                # FastLED colour lookup tables
│   │   └── [rendering utilities]
│   ├── effects/                            # 30 enumerated modes; 22 enabled by light_mode_is_enabled()
│   │   ├── light_mode_gdft.cpp           # Spectrum (octave display)
│   │   ├── light_mode_chromagram*.cpp    # Chord/chromagram variants
│   │   ├── light_mode_spectrum_river*.cpp # Streaming spectrum variants
│   │   ├── light_mode_tempo_river.cpp    # Beat-locked river (mode 19)
│   │   ├── light_mode_tempo_comet*.cpp   # Beat-locked comet variants (modes 20-21)
│   │   ├── light_mode_dense_forge*.cpp   # Chord-hue (Dense Forge, audio-semantic)
│   │   ├── light_mode_bloom.cpp          # Bloom/stargate effect
│   │   ├── light_mode_vu*.cpp            # VU meter variants (dot/bar)
│   │   ├── light_mode_aurora.cpp         # Aurora waves
│   │   └── [14 more: snapwave, pulse_prism, kaleidoscope, ember variants, etc.]
│   ├── director/                           # Effect selection, composition
│   │   ├── sb_smart_director.cpp/.h       # Mode routing, tempo sync logic
│   │   ├── sb_visual_hooks.cpp/.h         # Per-frame render callbacks
│   │   ├── sb_mode_selection.cpp/.h       # Mode enumeration and indexing
│   │   └── sb_edgemixer_lite.cpp/.h       # Dual-channel blending (primary + secondary)
│   ├── control/                            # User controls, effects queuing
│   │   └── [effect queue management, control dispatch]
│   ├── network/                            # Wireless communication
│   │   └── sb_k1_wireless.cpp/.h          # K1 AP-only WebSocket bridge for Tab5 control
│   ├── system/                             # Core system, config, utilities
│   │   ├── globals.cpp/.h                 # Global state, CONFIG defaults
│   │   ├── globals_config.cpp             # Relocated aggregate-init data
│   │   ├── utilities.h                    # Math, clamp, lerp, interpolation
│   │   ├── presets.h                      # Effect preset tables
│   │   └── user_config.h                  # User-facing config (if applicable)
│   ├── diag/                               # Diagnostics, instrumentation
│   │   ├── sb_trace.h                     # MabuTrace timeline capture (dev-only)
│   │   ├── diagnostic_capture.cpp/.h      # VPAB packet collection
│   │   ├── vpab_capture.cpp/.h            # Visual-pipeline A/B snapshots
│   │   └── [additional diagnostic tools]
│   ├── calibration/                        # Noise calibration, AGC baseline
│   │   └── noise_cal.h                    # Silence-based learning (non-auto)
│   ├── persistence/                        # Flash NVS storage, presets
│   │   └── [knob state, brightness, colour, preset slots (10 presets added 2026-06-06)]
│   ├── serial/                             # USB CDC commands, hotkeys
│   │   └── [command parser, serial I/O, hotkey dispatch]
│   └── [libraries, includes]
├── libraries/                              # Vendored dependencies
│   ├── FixedPoints/                        # Fixed-point arithmetic (I0F15, etc.)
│   ├── M5ROTATE8/                          # Rotary encoder I/O
│   └── _FastLED.disabled/                  # Legacy FastLED source (disabled; using lib_deps)
├── tests/                                  # Host regression harness (pytest)
│   ├── test_onset_beat_replay.py           # Offline onset/beat validation
│   ├── test_chord_saliency_replay.py       # Chord state replay
│   ├── test_smart_director_replay.py       # Effect selection logic
│   ├── test_semantic_state_replay.py       # AudioSemanticState validation
│   ├── test_vpab_gate.py                   # VPAB packet structure
│   ├── test_dev_instrumentation_boundary.py # No-instrumentation checks
│   ├── test_rate_consistency.py             # Audio pipeline rate audit
│   ├── test_*_static.py                    # Static analysis tests (23 total files)
│   └── [regression, integration, gates]
├── scripts/                                # Build and diagnostic scripts
│   ├── platformio/                         # PIO pre-scripts
│   │   ├── k1_src_includes.py              # Dynamic CPPPATH generation
│   │   └── k1_upload_guard.py              # USB MAC/chip ID verification
│   ├── regression-harness/                 # Offline analysis tools
│   │   ├── apstream_ingest.py              # Parse AudioPipeline snapshots
│   │   ├── render_diagnostics.py           # Generate visual diagnostics HTML
│   │   └── [metrics, replay, validation]
│   ├── hooks/                              # Git pre-commit gate
│   │   ├── pre-commit                      # Main gate (tests + build)
│   │   ├── install.sh                      # Gate installation
│   │   └── wip-checkpoint.sh               # WIP branch checkpoint
│   └── [other utilities]
├── notebooks/                              # Jupyter notebooks (analysis)
│   ├── audio_semantic_diagnostics.ipynb    # DSP analysis, replay, metrics
│   ├── diag_helpers.py                     # Shared helpers
│   └── [research, measurement notebooks]
├── docs/                                   # Project documentation
│   ├── forensics/                          # Technical investigations
│   │   ├── tempo_tracking_refactor/        # Audio semantic forward-graft evidence
│   │   │   ├── 2026-06-05-audio-semantic-forward-graft.md
│   │   │   └── [metrics, validation, ledger]
│   │   └── [other forensic docs]
│   ├── architecture/                       # System design & diagrams
│   ├── research/                           # Audio DSP, colour theory research
│   ├── measurements/                       # Performance baselines, metrics
│   ├── refactor/                           # Restructure planning docs
│   ├── git/                                # Git workflows and discipline
│   └── [hardware, config documentation]
├── platformio.ini                          # PlatformIO configuration (build, upload, flags)
├── .claude/CLAUDE.md                       # Load-bearing rules (READ FIRST)
├── .pre-commit-config.yaml                 # Pre-commit hook registry
├── README.md                               # User-facing project overview
├── NOTICE                                  # Notices file
├── LICENSE                                 # GNU GPL v3.0 (derivative of Sensory Bridge)
└── progress.md                             # Current development status
```

## Architecture Overview

### Audio-to-Visual Data Flow

```
Physical Audio (12.8 kHz I2S microphone build contract)
    ↓
I2S Peripheral (DMA circular buffer, Core 0)
    ↓
Goertzel GDFT (133 Hz frames, 96-sample chunks)
    ├→ Magnitude spectrum (80 frequency bins → 24 octave perceptual bands)
    ├→ Per-band onset (log-flux adaptive threshold, v2)
    ├→ Tempo/beat (prominence + periodicity, PLL flywheel v2)
    └→ Chord saliency (root + 9 harmonics, v2)
    ↓
AudioSemanticState (published each frame, read-only)
    ↓
Smart Director (effect routing, tempo sync)
    ↓
Effect Render (Core 1, 100 FPS loop)
    ├→ FastLED colour lookup
    ├→ Brightness scaling (AGC + user control)
    └→ Dual-channel composition (primary + secondary edge)
    ↓
FastLED RMT5 DMA Protocol
    ↓
WS2812B / APA102 Addressable LEDs
    ↓
Dual-channel diffused plate emission (physical light show)
```

### Core Timing

- **Audio Frame Rate:** 133 Hz (96-sample chunks @ 12.8 kHz)
- **Visual Render Rate:** 100 FPS (10 ms per frame, soft real-time)
- **Target Latency:** <50 ms (audio capture → LED update)
- **Core 0 (audio):** Hard real-time, non-blocking I2S DMA (no mutex)
- **Core 1 (visual):** Soft real-time, graceful frame-drop if behind

### Key Architectural Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Goertzel over FFT** | 80-bin frequency analysis mapped to 24 perceptual bands (music-relevant), lower latency, deterministic cost | Fixed resolution; trade perceptual grouping vs raw frequency bins |
| **Per-band onset** | Transient detection per frequency range (bass drops independent of snare hits) | Higher DSP cost; compensated by v2 adaptive threshold |
| **PLL tempo sync** | Stable beat phase lock under tempo fluctuations (human drummers, rubato) | Requires phase-lock convergence time (~3–5 frames) |
| **Dual-core split** | Core 0 = audio (hard real-time), Core 1 = visual (soft real-time, frame drop graceful) | Mutex-free state sharing requires volatile reads; no write contention |
| **No on-device animation** | Effects are music-driven (not time-driven); simplifies testing and replay validation | No time-only effects (e.g., pure sweep, breathing) |
| **VPAB diagnostic packets** | Offline validation: pair audio semantic state with visual output for forensic replay | Requires device storage/serial bandwidth for evidence capture |
| **AudioSemanticState read-only** | Core 1 never writes audio state; Core 0 never reads render state (zero contention) | Requires explicit pass-through if visual feedback to audio needed |

## UI/UX Quality Contract

For frontend, mobile, desktop, CLI, form, dashboard, onboarding, account/settings, or visual polish tasks:

1. Inspect nearby screens/components, the component library, design tokens, and existing density before creating new structure or styles.
2. Reuse existing components and hooks for repeated UI jobs such as tables, FAQs/accordions, forms, sticky CTAs, pricing, checkout, navigation, and analytics-triggered controls.
3. Choose a surface-appropriate direction: dashboard/tooling should be quiet, dense, and scannable; marketing can be more memorable; CLI/Ink should prioritize stable layout, truncation, and keyboard clarity.
4. Avoid generic AI slop, template-looking screens, random gradient/card stacks, and UI that ignores the product context.
5. For changed interactive flows, define the state matrix before coding: loading, empty, error, disabled, pending, success, retry/recovery, and long-text cases.
6. Verify accessibility basics: labels, focus states, keyboard path, semantic controls, contrast, ARIA state for disclosure widgets, and non-hover-only guidance.
7. Keep UX distinct from product strategy: UX covers concrete journeys, states, affordances, microcopy, and accessibility; product strategy covers activation, adoption, experiments, and metrics.

## Skill Advantage Contract

When skills, generated instructions, or project guidance are available, use them as a quality multiplier to outperform an unskilled baseline:

1. Preserve normal collaboration: ask clarifying questions when ambiguity or user preference can change architecture, UX, data shape, security posture, analytics, or external side effects. When asked to surface data that no existing code path captures, state up front the assumption that capture starts now (no backfill) or ask if a backfill source exists — do not silently build net-new storage without surfacing this.
2. Inspect the nearest real repo patterns before inventing structure: routes/pages, components, tests, schema, infra, copy, analytics, and existing workflows.
3. Identify the task's highest-leverage success criteria, such as user-visible correctness, integration quality, accessibility, security, reliability, maintainability, operability, or speed of future change.
4. Reuse existing product primitives before reimplementing: components, hooks, helpers, formatting/utility functions, data registries, metadata builders, analytics, pricing, checkout, auth, routing utilities, and API procedures/data sources. Before adding a new API procedure or query, reuse one that already returns this data — a surface that fetches data and only logs it is a reuse target, not an absent one; do not author a parallel endpoint. Before importing for a data fetch, grep the screen for the call it already makes and reuse that exact client/singleton import path and endpoint/procedure name; never create a second client, transport, or parallel endpoint for data an existing call returns, and confirm every imported path and symbol actually exists before writing it.
5. Prefer semantic, accessible structures for core content and controls: tables for tabular comparisons, lists for lists, forms for forms, buttons for actions, and project accessibility primitives for complex UI.
6. Centralize repeated facts, labels, claims, and product defaults in shared registries or helpers when multiple surfaces need the same answer; prevent copy/data drift by construction.
7. Synthesize the strongest repo-consistent parts of available approaches instead of blindly choosing one.
8. Ground product copy and docs in implemented behavior; do not imply automation, integrations, refresh cadence, security, metrics, counts, or data flow that does not exist in code. Any claim that one component writes, records, updates, calls, or is the source of truth for another is allowed only if the edit performing it is in this same change; before finishing, check each such cross-component claim in comments/docstrings/copy against the actual edits and downgrade unbacked ones to an explicit TODO or implement them now.
9. Ship the complete slice when relevant: wiring, state handling, validation, analytics, tests, docs, migrations, or infra updates that make the behavior usable and maintainable. When a task asks to show, display, or list user data, deliver the full vertical slice and do not stop at an internal/API/CLI layer: the data-model/schema change AND its migration, the code path that writes or populates the data, an authenticated API endpoint scoped to the current user that mirrors the project's existing procedures, and the primary user-facing surface wired through the project's typed data-fetching client. Interpret "show the user" as the app's main UI by default, not an internal or CLI-only endpoint. Before declaring done, trace one record end-to-end (triggering event → write → read → render); if any hop exists only in a comment or docstring rather than edited code, the slice is NOT done. Shipping only the persistence layer (a schema/migration with no writer, reader, or surface) is an incomplete slice, not a milestone.

## Development Guidelines

### Code Style

**File Naming (firmware):**
- Audio DSP modules: **new K1-specific code uses `k1_<module>.cpp` / `k1_<module>.h`** (e.g., `k1_spectral_honesty.h`, matching the existing `k1_loud_guard` / `K1_LOUD_GUARD_V1` naming). The `sb_<module>` prefix is **reserved for inherited Sensory Bridge heritage** (`sb_tempo.cpp`, `sb_onset_beat.h`, `sb_audio_snapshot.*`, …) and is NOT bulk-renamed.
- Visual effects: `light_mode_<effect>.cpp` (e.g., `light_mode_spectrogram.cpp`)
- System utilities: `utilities.h`, `globals.h`, `presets.h`
- Tests: `test_<module>_<scenario>.py` (e.g., `test_onset_beat_replay.py`)

**Code Naming (C++17):**
- Classes/structs: `PascalCase` (e.g., `AudioSemanticState`, `SmartDirector`, `ChordState`)
- Functions: `camelCase` with verb (e.g., `processBeat()`, `renderFrame()`, `publishAudioState()`)
- Variables: `camelCase` (e.g., `sampleBuffer`, `beatConfidence`, `onsetThreshold`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `MAX_TEMPO_BPM`, `GDFT_BANDS=24`, `SAMPLE_RATE=48000`)
- Private members: `_prefixed` (e.g., `_internalState`, `_buffer`)
- Booleans: `is/has/should` prefix (e.g., `isLocked`, `hasOnset`, `shouldPublish`)

**Import Order (C++):**
1. System headers (`Arduino.h`, `esp_idf.h`)
2. FastLED headers
3. Project headers (grouped by domain: audio, visual, system, diag)
4. Local includes (end of file, if any)

### Key Patterns

**Audio Pipeline (Core 0 — hard real-time):**
- I2S DMA circular buffer (non-blocking, continuous)
- Goertzel frame boundary triggers AudioSemanticState publish
- No direct rendering (publish-only architecture, no write contention)
- Mutex-free via shared volatile struct with frame counter
- No blocking calls, no FreeRTOS synchronization (no stalls on Core 1)

**Visual Rendering (Core 1 — soft real-time):**
- Subscribe to AudioSemanticState (read volatile, no write)
- 100 FPS render loop (not audio-locked; graceful skip if behind)
- FastLED.show() at frame boundary (RMT5 DMA, non-blocking)
- Effects are stateless (pure function: audio state → visual LED values)

**Testing Strategy:**
- **Host regression:** Offline pytest (54 test files, 427 tests across static analysis, replay, and gates), replay binary audio captures, validate metrics against expected ranges
- **Device validation:** VPAB packet capture, serial timing probes, eyes-on visual inspection for perceptual impact
- **Host gate ≠ Device proof:** Host validates compile + metrics correctness; device validates visual + latency + perceptual feel
- **Current status:** Host gate GREEN (pytest 427 tests pass). Device eyes-on is the final gate before production release.

**Commit Gate (load-bearing — see `.claude/CLAUDE.md`):**
```bash
# Docs-only changes → no gate required
git commit -m "docs: ..."

# Changes to tests/ or scripts/ → pytest must pass
pytest tests/ && git commit -m "test: ..."

# Changes to firmware or platformio.ini → pytest AND build must pass
pytest tests/ && pio run -e k1_hardware && git commit -m "feat: ..."

# Unstaged binaries or files >5 MB → automatically rejected
```

### Build Configuration Reference

**platformio.ini (active flags for k1_hardware, 2026-06-11):**
```ini
# Audio semantic forward-graft (v2 DSP, fully validated 2026-06-05)
-DSB_TEMPO_CONF_V2       # Stable prominence/periodicity confidence + lock FSM
-DSB_TEMPO_FLYWHEEL_V2   # PLL beat phase + 3x beat-tick republish fix
-DSB_ONSET_V2            # Donor log-flux + median-adaptive + per-band
-DSB_CHORD_V2            # ChordState + harmonic saliency
-DSB_SEMANTIC_STATE      # AudioSemanticState read surface

# Tier 1 consumers (audio-semantic effects, 2026-06-11)
-DSB_CHORD_HUE_V1        # Dense Forge chord→hue anchor (first chord consumer)

# Impact lane (visual enhancement, 2026-06-11)
-DSB_DROP_CUT_V1         # Musical silence → dark in ~200ms, strobe-safe

# Hardware target
-DSB_K1_HARDWARE         # K1-specific pin map, behaviour

# Compiler optimizations
-O3 -ffast-math          # Fast math enabled (acceptable per 2026-05-26 gate)

# Legacy v1 paths gated under #ifndef SB_*_V2 (revertible)
# Dev instrumentation (trace_dev env only, non-shippable)
# -DMABU_TRACE_ENABLED    # Non-shippable, development only
```

## Platform-Native Production Patterns

Before implementing production behavior, identify the runtime, hosting platform, database, queue, storage, auth, payment, analytics, and email systems involved. Inspect the provider service catalog, official docs, runtime config, and project docs before choosing a fallback implementation.

For changes touching abuse protection, rate limits, background work, scheduled jobs, queues, caching, shared state, secrets, file/object storage, database connectivity, webhooks, payments, auth/session flows, email sending, analytics events, or externally visible side effects:

1. Prefer managed/platform-native primitives over in-process memory, local timers, singleton clients, ad hoc counters, or frontend-only controls.
2. Wire platform capabilities through the repository's infrastructure/config layer, runtime environment, and typed app/context boundary.
3. Place guards before expensive or externally visible side effects such as payment APIs, auth mutations, email sends, analytics events, storage writes, or database mutations.
4. Preserve privacy and anti-enumeration behavior in auth, recovery, invite, checkout, and email flows.
5. Decide and document the failure stance: fail open, fail closed, retry, or degrade gracefully.
6. Check concurrency, retries, serverless/edge isolates, transaction boundaries, and multi-instance behavior before choosing a storage or coordination pattern.
7. Keep the change consistent with the repo's existing deployment/runtime setup rather than introducing a parallel mechanism.

Precedence: follow a clear user instruction first, then explicit project docs, then provider best practices. When a fallback is explicitly required, state the provider-native alternative and make the chosen path durable, multi-instance safe, and atomic under concurrency. Do not present module-scope mutable state, frontend-only checks, detached timers, untyped env access, or non-atomic select-then-update counters as production-ready.

For ESP32-S3 firmware, production patterns prioritize real-time safety, determinism, and hardware integration.

**Core Patterns:**

1. **Hard real-time audio (Core 0):** Prefer hardware DMA (I2S) over blocking I/O. Use FreeRTOS primitives for synchronization only where unavoidable; prefer volatile/atomic primitives for cross-core state. Never use mutexes, malloc, or blocking calls on Core 0.
2. **Soft real-time visual (Core 1):** Graceful frame-drop if behind schedule (100 FPS render is target, not hard deadline). Use FastLED's native RMT5 DMA for LED updates.
3. **Persistent state:** Use ESP-IDF NVS (Non-Volatile Storage) through Arduino abstractions for knob position, brightness, preset state. Prefer EEPROM wear-leveling over raw flash writes.
4. **Serial communication:** CDC-over-USB (USB_CDC_ON_BOOT flag) for commands, diagnostics. 115200 baud, non-blocking TX/RX (serial.read() will return -1 if no data, no stalls).
5. **Wireless integration:** K1 runs WiFi AP-only; the Tab5 joins the K1 AP as the control client. Use WebSockets for low-latency effect/parameter updates. Do not add K1 STA fallback.
6. **State sharing across cores:** AudioSemanticState published by Core 0, read-only on Core 1 (no contention). Frame counter ensures consistent snapshots.
7. **Power and thermal:** Monitor Core 0 current under audio load + Core 1 under 100 FPS render. Thermal throttling at 100°C (device-reported); prioritize audio over visual if throttled.

**Before adding features touching audio timing, visual latency, flash wear, wireless state, or cross-core synchronization:**
- Inspect the canonical platform docs (ESP-IDF docs, Arduino-ESP32 specs, FastLED driver notes)
- Verify against existing patterns in audio/ and visual/ subdirectories
- Test on real hardware (K1 reference board, USB connection)
- Confirm no new mutexes or blocking calls on Core 0
- Validate latency impact (measure audio-to-LED end-to-end with device probe)

### For **ESP32 Firmware**, Production Behavior Must Use Hardware-Native Primitives

Before implementing production behavior for timing, performance, frame-drop recovery, race conditions, background work, or externally visible side effects:

1. **Prefer hardware-native primitives:**
   - I2S DMA for audio capture (not polling, not blocking)
   - RMT5 peripheral for LED protocol (not bit-banging, DMA-driven)
   - FreeRTOS task priorities and semaphores (not spinlocks)
   - Flash NVS for persistent state (not emulated EEPROM)
   - Hardware timers for timing-critical operations (not software millis)

2. **Place guards before expensive or external side effects:**
   - Audio-to-LED latency budget (audit with MabuTrace on trace_dev)
   - AGC and noise calibration (require silence confirmation, never auto-fire)
   - LED power draw (brightness limiting to prevent brownout; 5V/2A budget)
   - Flash wear (batch writes, verify NVS checksums)
   - VPAB diagnostic packet writes (gate on flash space availability)

3. **Decide and document failure stance:**
   - **Timing miss:** Graceful degrade (skip frame, don't block Core 0)
   - **Audio buffer overrun:** Drop oldest samples (not future)
   - **Calibration error:** Preserve prior state, report to serial
   - **Flash corruption:** Reset to defaults, log incident to UART
   - **VPAB overflow:** Stop capture, warn to serial

4. **Check concurrency and multi-core (critical for dual-core design):**
   - Core 0 writes AudioSemanticState; Core 1 reads (mutex-free via volatile read)
   - No spinlocks; use FreeRTOS primitives (queues, semaphores, mutexes) for inter-core sync
   - Audio pipeline is hard real-time; visual is soft real-time (frame drops acceptable)
   - Never block Core 0 on I/O, Flash, or Core 1 activity
   - **Volatile semantics:** AudioSemanticState uses `volatile` keyword to prevent compiler optimization across core boundaries. Core 1 must read the full struct atomically (frame counter guards consistency).
   - **No blocking on shared state:** If Core 1 needs audio state, it polls the volatile struct. Never add mutexes on the audio path.

5. **Keep changes consistent with deployment setup:**
   - Arduino sketch entry point (`SPECTRASYNQ_K1_FIRMWARE.ino`)
   - PlatformIO build and serial monitor integration
   - Git pre-commit gate (tests + build)
   - VPAB diagnostic format (offline validation substrate)
   - Device identity verification before upload (USB MAC, chip ID)

6. **Failure handling precedence:**
   - Follow a clear user instruction first
   - Then explicit project docs (this CLAUDE.md, .claude/CLAUDE.md)
   - Then ESP-IDF / Arduino best practices
   - When a fallback is explicitly required, state the native alternative and make the path durable, multi-instance safe, and atomic under concurrency

## Commands Reference

| Command | Description |
|---------|-------------|
| `pio run` | Build firmware (default: k1_hardware, production) |
| `pio run -e <env>` | Build specific environment (k1_hardware, k1_bench_reference, etc.) |
| `pio run --target upload` | Upload to device (USB MAC verified by k1_upload_guard.py) |
| `pio run --verbose` | Build with verbose output (check warnings) |
| `pio device monitor -b 115200` | Serial monitor (live output + hotkey input) |
| `pytest tests/ -v` | Full regression harness (54 test files, 427 tests across static/replay/gates) |
| `pytest tests/test_name.py -v` | Single test file |
| `pytest tests/ -k keyword` | Filter tests by name |
| `pytest tests/ -vv --durations=10` | Verbose with timing breakdown |
| `pio run -e k1_hardware_trace_dev` | Build with MabuTrace (dev-only) |
| `./scripts/hooks/install.sh` | Install pre-commit gate |
| `git log --oneline -10` | Recent commits |
| `git status` | Verify staged files before commit |

## Deployment

**Production Build Verification:**
```bash
# Build firmware (k1_hardware is production)
pio run -e k1_hardware

# Verify no instrumentation leaks
grep -r "MABU_TRACE\|trace_dev" SPECTRASYNQ_K1_FIRMWARE/ || true
# Should return empty

# Check binary size (must fit in 16 MB total)
ls -lh .pio/build/k1_hardware/firmware.bin
# Expected: ~10–12 MB

# Run full gate before pushing
pytest tests/ && pio run -e k1_hardware
```

**Serial Hotkeys (on running device, 115200 baud):**
```
'c' → start_noise_cal (requires Captain silence confirmation first)
'm' → cycle effect mode (SmartDirector)
'n' → noise button (recalibrate AGC baseline)
```

**Device Identity Verification (before upload):**

> **Canonical device↔env↔build truth: [`docs/hardware/device-build-registry.md`](./docs/hardware/device-build-registry.md) — READ IT before any flash, erase, or serial-write.** 1401 (chip `F887A500`) takes env `k1_hardware` ONLY; 12201 (chip `B489A500`) takes env `k1_bench_reference` ONLY — the envs differ by GPIO map, never cross-flash. The registry's deployed-state table records what each device currently runs; update it after every flash.

```bash
# Check USB ports before upload (port names drift; identity = chip ID)
ls /dev/cu.usbmodem*
# Typical: /dev/cu.usbmodem1401 (main K1) or /dev/cu.usbmodem12201 (bench K1v2)
# USB MAC + chip ID auto-verified by k1_upload_guard.py — but consult the
# registry first; the guard is the last line of defence, not the first.
```

## Load-Bearing Rules

**READ `.claude/CLAUDE.md` FIRST.** It contains non-negotiable discipline rules:

1. **Sensory Bridge Doctrine** — Architecture subordinate to perceptual impact; invoke `/sensorybridge-doctrine` before AP/VP changes
2. **Developer Instrumentation Boundary** — Developer, harness, trace, benchmark, probe, and diagnostic code never ships with production firmware; MabuTrace is mandatory developer-only escalation for timeline/causality, and scalar diagnostics do not close causal attribution
3. **Calibration Command Policy** — `start_noise_cal` requires verbal silence confirmation (never auto-fire)
4. **Hardware Target Discipline** — Always verify device identity (USB MAC, chip ID) before upload/erase
5. **Git Discipline** — Use branches and commits for recovery checkpoints; pre-commit gate prevents broken code
6. **Parallel-Agent Orchestration** — Parallel work requires delegation contracts with classification and evidence rules
7. **Commit Cadence** — Commit frequently (every green checkpoint), but only after verification
8. **Ship path required (Captain 2026-08-17)** — Never say a result does not mean ship / promote / close without the remaining numbered ship path in the same answer (`/ship-path-required`)
9. **Plain English work summaries (Captain 2026-08-22)** — Summary of agent work MUST be plain English (`/plain-english-work-summaries`)

Full rules and rationale: **[`.claude/CLAUDE.md`](./.claude/CLAUDE.md)**

## Additional Resources

- **Audio Forensics:** `@docs/forensics/tempo_tracking_refactor/` (beat tracking evidence, metrics, v2 validation)
- **Architecture Docs:** `@docs/architecture/` (system design, module dependencies)
- **Research Notes:** `@docs/research/` (DSP theory, colour science, psychoacoustics)
- **Measurement Baselines:** `@docs/measurements/` (performance benchmarks, tempo accuracy, latency)
- **Git Discipline:** `@docs/git/commit-gate.md` (pre-commit gate structure, cadence rules)
- **Hardware References:** `@docs/hardware/` (pinouts, electrical specs, if available)
- **Development Status:** `@progress.md` (current lanes, blockers, next steps)

## Related Projects

- **Lightwave LedStrip:** `@Lightwave-Ledstrip/` (variant for LED strip targets, legacy S2 reference)
- **Original Firmware:** `@Light_Crystals_Wireless.ino` (legacy S2 reference, do not use)

---

## Skill Usage Guide

When working on tasks involving these technologies, invoke the corresponding skill to access domain-specific guidance:

| Skill | Invoke When |
|-------|-------------|
| **platformio** | Manages build configuration, compilation, device upload, serial monitoring |
| **esp32** | Configures ESP32-S3 microcontroller, peripherals, I2S, RMT5, FreeRTOS |
| **cpp** | Develops firmware in C++17 with modern features, memory management, templates |
| **esp-idf** | Uses ESP32 SDK, low-level hardware abstraction, driver APIs |
| **fastled** | Controls WS2812B/APA102 addressable LEDs, colour lookup, animations |
| **python** | Runs testing, diagnostics, analysis, regression harness |
| **pytest** | Automates Python testing and regression validation (54 test files, 427 tests: static analysis, replay, gates) |
| **numpy** | Performs numerical computing, spectral DSP analysis, audio metrics |
| **scipy** | Implements signal processing, Goertzel, windowing, spectral algorithms |
| **pandas** | Handles data analysis, frame manipulation, CSV processing |
| **plotly** | Creates interactive plots, data visualizations, diagnostic dashboards |
| **jupyter** | Provides interactive notebook environment for audio_semantic_diagnostics |
| **matplotlib** | Generates 2D plots, analysis charts, offline diagnostics |
| **arduino** | Enables Arduino framework compatibility on ESP32-S3 via pioarduino |
| **cmake** | Manages C++ build configuration (if applicable) |
| **ninja** | Accelerates build compilation speed (optional) |
| **pydantic** | Validates and serializes data models, VPAB packets, metrics |
| **dash** | Builds web-based diagnostic dashboards (optional, for render_diagnostics.py) |
| **click** | Creates command-line interfaces for diagnostic scripts |
| **aiofiles** | Provides async file I/O operations (diagnostic harness, optional) |
| **websockets** | Implements real-time WebSocket communication (optional, if remote diagnostics) |
| **httpx** | Handles async HTTP requests for remote uploads/monitoring (optional) |
| **uv** | Manages Python dependencies and virtual environments (testing) |

---

## Prompt-Aware Production Contract

Before coding, scan the user's prompt for relevant skills and production-risk signals.

1. **Load or inspect the relevant skill** when the task matches a skill name, its use case, or nearby technology terms
2. **Use skills as a quality multiplier**, not a checklist — inspect nearby repo patterns and identify the task's highest-leverage success criteria
3. **Reuse existing product primitives** before reimplementing effects, colours, configurations, or diagnostic logic
4. **Synthesize the strongest repo-consistent approaches** instead of blindly choosing one
5. **Ground product claims in implemented behavior** — do not imply automation, integrations, or latency that does not exist in code
6. **Ask clarifying questions** if the task is ambiguous, underspecified, or depends on user preference
7. **For production-risk signals** (timing, race conditions, latency, power, flash wear, concurrency), create a short task contract before coding: likely skills, provider/hardware docs to inspect, preferred native service, wiring surfaces, side-effect barriers, fallback policy, and verification criteria

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-21 | agent:claude-code | File-naming convention: new K1-specific firmware code uses the `k1_`/`K1_` prefix (e.g. `k1_spectral_honesty.h`); `sb_` is reserved for inherited Sensory Bridge heritage modules and is not bulk-renamed. Origin: Captain standing order during the AP measurement-honesty lane. |
| 2026-06-15 | agent:codex | Corrected root authority docs after Tab5 strict harness/gate commits: restored spec-index routing, updated pytest count to 54 files / 427 tests, corrected audio timing to 96-sample chunks at 12.8 kHz, described 30 enumerated / 22 enabled lightshow modes from config_types.h, and removed contradictory K1 STA fallback wording. |
| 2026-06-11 | agent:claude-code | Fixed critical inaccuracies: corrected test file count from 23 to 53; corrected effect count from 20 to 25; clarified GDFT as 80-bin spectrum mapped to 24 perceptual octaves (not "24 octave bands"); added network and control directories to structure; updated build flags to include SB_CHORD_HUE_V1 and SB_DROP_CUT_V1 (impact lane); updated Platform-Native Production Patterns section to be ESP32-specific (hard real-time audio, soft real-time visual, DMA, FreeRTOS, volatile primitives); verified all technical claims against platformio.ini build_flags, directory listing, and git history |
| 2026-06-06 | agent:claude-code | Improved CLAUDE.md: updated abstract to clarify "136-test pytest" and "23 test files" distinction; confirmed 20 effects count; added k1_ap_frontend_probe environment (2026-06-06); expanded Platform-Native Production Patterns with multi-core concurrency details (volatile semantics, non-blocking Core 0 guarantee); added effect mode examples (Tempo River 19, Tempo Comet 20); verified all technical details match current platformio.ini and git history |
| 2026-06-05 | agent:claude-code | Created comprehensive root CLAUDE.md: tech stack, architecture, quick start, development guidelines, platform patterns, and load-bearing rule references |

---

Spec Kit integration: This project includes Spec Kit for manual specification work. Repository instructions, source code, runtime evidence, and hardware proof remain higher authority than generated Spec Kit artefacts. Use generated `speckit` skills for `specs/` artefacts only; do not run implementation, automation, or hooks without explicit Captain approval.
