---
abstract: "Parallel SSA Level 1 research dossier for FixedPoints/SQ15x16 modernisation. Captures viable exploration vectors that can proceed while the main K1 refactor continues, without changing firmware source or reopening the locked native_vp boundary."
---

# FixedPoints Level 1 Research Vectors

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Mode | Read-only research/evaluation |
| Parent dossier | `docs/forensics/2026-05-25-fixedpoints-modernisation-options.md` |
| Main refactor boundary | Do not patch/replace FixedPoints inside Rows 3-4-2. Do not reopen `native_vp` without Captain approval. |
| Runtime boundary | This read-only research pass did not require direct device interaction. Future runtime work may use serial/capture directly when needed after verifying the hardware target by port plus stable device identity. |
| SSA scouts | A usage inventory, B ecosystem, C ESP32-S3 performance/toolchain, D gates, E architecture/API, F licence/governance |

## 1. Level 1 Viability Rule

A FixedPoints exploration vector is Level 1 viable only if it can run while the active refactor continues and it does not require production firmware adoption. Each vector must answer:

1. What K1 capability does this unlock?
2. What unsafe failure mode does this remove?
3. What regression gate proves behaviour was preserved?
4. What line prevents it from contaminating the active refactor?

If a vector cannot answer those four questions, it is not Level 1. It can remain a note, but not a funded research lane.

## 2. Current Hard Evidence

- [FACT] `config_types.h` keeps the public config aggregate dependency-light and pure POD; it explicitly references no `SQ15x16`, `CRGB16`, or FastLED types. Source: `SPECTRASYNQ_K1_FIRMWARE/config_types.h:13-20`.
- [FACT] Public/operator controls such as `PHOTONS`, `CHROMA`, `MOOD`, `SENSITIVITY`, `SATURATION`, `PRISM_COUNT`, and `BASE_COAT_INTENSITY` are `float` fields in `struct conf`. Source: `SPECTRASYNQ_K1_FIRMWARE/config_types.h:82-123`.
- [FACT] `lightshow_modes.h` uses `SQ15x16` at the colour-conversion boundary (`crgb_to_crgb16`, `clamp01_fixed`, `palette_manual_colour`, `palette_chroma_colour`) and also converts back to `float` for palette sampling and trigonometric chroma-vector work. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:63-172`.
- [FACT] VP Tier A hashes quantise `CRGB16` channels after clamping to 0..1 and multiplying by 65535; this is the current strongest automated guard for render numeric drift. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:352-379`.
- [FACT] VP Tier B frame dumping emits hash, energy, centre-of-mass, and FPS under `ENABLE_FRAME_DUMP`. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:391-423`.
- [FACT] `vp_probe_prepare_render` resets render state and seeds deterministic conditions for probe renders, but `quantum_collapse` is explicitly non-Tier-A. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:450-530`.
- [FACT] The probe saves/restores `SQ15x16`, `CRGB16`, `float`, DOT, and CONFIG state around probe output. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:584-650`.
- [FACT] GDFT/AGC currently crosses between float magnitudes and `SQ15x16` envelope/gain/spectrogram state. Source: `SPECTRASYNQ_K1_FIRMWARE/GDFT.h:170-180`, `221-285`, `295-320`.
- [FACT] Scout A confirmed `SQ15x16` spans eight buckets: colour accumulation, audio energy/GDFT, smoothing/control coefficients, spatial/position, random/probability fields, UI/config-control, lookup tables, and build/include hygiene.
- [FACT] Scout A identified additional audio fixed-point surfaces in `i2s_audio.h` and `bridge_fs.h`: waveform normalisation, RMS/VU, and persisted calibration/noise paths.
- [FACT] `SQ15x16` appears in 26 firmware files. A current `rg -c` count shows the densest sites are `led_utilities.h` (208), `globals.h` (50), `lightshow_modes.h` (39), `light_mode_quantum_collapse.cpp` (30), `GDFT.h` (28), and `system.h` (27).
- [FACT] `SQ15x16` is `SFixed<15,16>`. Source: `libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h:19-23`.
- [FACT] The vendored FixedPoints library is declared as Apache-2.0 version 1.1.2 from `Pharap/FixedPointsArduino`. Source: `libraries/FixedPoints/library.json:1-17`.
- [FACT] The vendored FixedPoints README says redistribution must package `LICENCE` and `NOTICE`, and modified source files must state modifications prominently. Source: `libraries/FixedPoints/README.md:28-49`.
- [FACT] The local vendored FixedPoints folder contains `LICENCE` but no `NOTICE` file by `find libraries/FixedPoints -maxdepth 2 -iname 'NOTICE*' -o -iname 'LICENSE*' -o -iname 'LICENCE*'`.
- [FACT] The ESP32-S3 datasheet lists a dual-core Xtensa 32-bit LX7 CPU up to 240 MHz, 128-bit data bus/SIMD instructions, single-precision FPU, 32-bit multiplier, and 32-bit divider. Source: Espressif ESP32-S3 datasheet.
- [FACT] ESP-IDF FreeRTOS documents lazy FPU context switching, automatic task pinning when `float` appears in a call flow, and no hardware acceleration for `double`; `double` may consume significantly more CPU time than `float`. Source: ESP-IDF FreeRTOS SMP guide.
- [FACT] ESP-DSP provides ESP32-S3-targeted DSP functions including FFT, FIR/IIR, dot product, vector math, and implementations for 32-bit float and 16-bit signed integers, but it is an ESP-IDF component. Source: Espressif ESP-DSP registry/docs, checked 2026-05-25.
- [FACT] The current release resource envelope is RAM 83064 bytes and flash 559314 bytes. Source: `docs/refactor/baseline-envelope.json:8-20`.
- [FACT] The current harness documentation lists `ap_diff.py`, `run_diff.sh`, and `vp_semantics_classifier.py`, but the live `scripts/regression-harness/` directory currently contains `ap_capture_leg.py`, `derive_bands.py`, `parse_serial.py`, `vp_capture.py`, and `vp_diff.py` only. Source: `docs/k1-refactor-2026-05/03-hardware-gate-package.md:74-84`; `rg --files scripts/regression-harness`.

## 2.1 External Source Check

These facts were rechecked from current external sources on 2026-05-25. They are candidate-research inputs, not adoption decisions.

| Source | Current fact | Level 1 implication |
|---|---|---|
| `fpm` docs: `https://mikelankamp.github.io/fpm/` | C++ header-only fixed-point library; requires C++11; provides `fpm::fixed` and `fixed_16_16`. | Best direct replacement spike candidate, but only behind parity tests because construction, rounding, overflow, and conversion semantics may differ from Pharap. |
| FR_Math docs/repo: `https://deftio.github.io/fr_math/`, `https://github.com/deftio/fr_math` | C embedded fixed-radix library with no FPU dependency, variable radix, trig/log/exp/sqrt/2D-transform surfaces, BSD-2-Clause. | Strong explicit-kernel spike candidate; weak as an unwrapped `SQ15x16` type replacement. |
| ESP-DSP registry: `https://components.espressif.com/components/espressif/esp-dsp/versions/1.8.2/readme` | Latest registry version checked is 1.8.2; official Espressif DSP component; Apache-2.0; IDF component; 32-bit float and 16-bit signed integer implementations. | Audio-kernel research candidate only; not a render accumulator or `CRGB16` replacement. |
| IQMath registry: `https://components.espressif.com/components/espressif/iqmath/versions/1.11.0~1/readme` | Latest registry version checked is `1.11.0~1`; 32-bit signed IQ1-IQ30 formats; `_iq16` matches the Q16.16 scale/range class; licence is listed as `Custom`. | Promising ESP-native fixed-kernel spike only after licence review and Arduino/PlatformIO integration proof. |
| libfixmath repo: `https://github.com/PetteriAimonen/libfixmath` | MIT, C Q16.16 library; README says not actively maintained; default caches can reserve 32 KB exp and 80 KB trig unless disabled. | Useful benchmark/control candidate; weak product replacement. |
| CNL repo: `https://github.com/johnmcfarlane/cnl` | Boost licence; current mainline requires C++20, while version 1.x supported C++11. | Design reference only for current K1 PlatformIO/Arduino path. |

## 3. Level 1 Vectors

### L1-01: Numeric-Domain Inventory

| Field | Assessment |
|---|---|
| Status | Viable now |
| Type | Read-only source analysis |
| Capability unlocked | Agents can reason by domain (`ColourAccum`, `AudioEnergy`, `UnitControl`, `Position`, `RandomField`) instead of treating every `SQ15x16` as equivalent. |
| Unsafe failure removed | Prevents a later backend swap from flattening all numeric contracts into one broad type migration. |
| Regression gate | Inventory must classify every `SQ15x16` site; unknown bucket count must be zero before any FP-0 implementation plan. |
| Active-refactor boundary | Generates docs only. No source edit. |

Why it matters: current `SQ15x16` spans colour accumulation, AGC/audio energy, spectrogram history, UI mask, hue/motion state, lookup tables, and random quantum fields. Those domains should not share one replacement decision.

Scout A bucket split to preserve:

- Colour accumulation: `CRGB16`, render buffers, palette conversion, HSV/desaturation, blend/prism, final quantisation.
- Audio energy/GDFT: spectrogram, chromagram, novelty, noise samples, AGC envelope/gain, waveform fixed-point.
- Smoothing/control: attack/release, VU, waveform fades, hue shift, UI mask, knob change rate.
- Spatial/position: DOT/KNOB positions, interpolation, draw helpers, centre-origin symmetry, VP COM/hash maths.
- Random/probability fields: `quantum_collapse`, kaleidoscope noise, hue-destination randomness.
- UI/config-control: public config remains float/int; encoder/knob/UI render internals use fixed-point.
- Lookup tables: dither, note colours, hue lookup, incandescent lookup, spectral tilt.
- Build/include hygiene: `FixedPointsCommon.h` self-containment and `file://libraries/FixedPoints` vendoring.

### L1-02: Colour Accumulator Contract

| Field | Assessment |
|---|---|
| Status | Viable now as a spec/test design; implementation deferred |
| Type | Architecture + parity test design |
| Capability unlocked | A future `ColourAccum` domain can preserve high-resolution colour memory without leaking vendor fixed-point details into every mode. |
| Unsafe failure removed | Prevents accidental changes to fade, bloom, waveform trail persistence, or final quantisation during a library swap. |
| Regression gate | `vp_probe_hash_leds`, `vp_probe_energy`, Tier A hashes, and targeted colour helper parity tests. |
| Active-refactor boundary | Do not rename or wrap `CRGB16` during Rows 3-4-2. |

Evidence: `CRGB16` currently holds three `SQ15x16` channels, and VP hashing quantises after clamp to 16-bit per channel. Any candidate must preserve this semantic boundary before it earns source changes.

### L1-03: Audio Energy / AGC Numeric Probe

| Field | Assessment |
|---|---|
| Status | Viable now as design; measured run waits for stable hardware capture lane |
| Type | Audio-path microbench and conformance design |
| Capability unlocked | Separates "fixed point is required for GDFT/AGC" from "fixed point is inherited everywhere". |
| Unsafe failure removed | Prevents replay of the silence/max-gain and AGC instability class by forcing envelope/gain/noise-floor parity before any numeric backend change. |
| Regression gate | AP capture metrics plus exact conformance cases for `agc_envelope`, `agc_noise_floor`, `agc_gain`, `spectrogram[]`, and `novelty_curve`. |
| Active-refactor boundary | No calibration command, no silence-window action, no serial access by agent. |

The viable first step is to specify vectors from existing captures or synthetic arrays, not to run hardware.

### L1-04: Candidate Library Spike Queue

| Candidate | Level 1 Ruling | Reason |
|---|---|---|
| `fpm` | Primary fixed-point replacement spike | C++11, header-only, modern API posture, plausible `fixed_16_16` analogue. Main risk is call-site churn plus rounding/overflow/conversion mismatch against Pharap. |
| FR_Math | Secondary explicit-C fixed-radix spike | Embedded C library with broad math functions and selectable radix; useful for explicit kernel experiments, less natural for C++ render-domain types. |
| Espressif IQMath | Secondary ESP-native fixed-point spike after governance review | 32-bit IQ formats align conceptually with Q16.16; licence is `Custom` with TI provenance, and Arduino/PlatformIO fit is unproven. |
| libfixmath | Baseline/benchmark only | Q16.16 C library, MIT, known but not actively maintained; useful as reference, weak as long-term architecture. Static caches must be disabled or budgeted if tested. |
| CNL | Design reference, not immediate firmware candidate | Modern numeric design and Boost licence, but latest requires C++20 and is likely too heavy for the current PlatformIO/Arduino path. |
| johnmcfarlane/fixed_point | Reject as direct candidate | Archived/deprecated in favour of CNL. Useful only as historical design context. |
| ESP-DSP | Audio-kernel candidate only | Strong candidate for FFT/FIR/vector/audio exploration, not a direct `CRGB16` or render fixed-point replacement. |
| ETL | Adjacent infrastructure only | Embedded containers/type utilities may help no-heap architecture, but not a FixedPoints replacement. |

### L1-05: Host-Compiler Risk Containment

| Field | Assessment |
|---|---|
| Status | Viable only as isolated research |
| Type | Throwaway worktree/compiler probe |
| Capability unlocked | Quantifies whether a modern host compiler can ever become useful again for numeric-only conformance tests without reintroducing `native_vp`. |
| Unsafe failure removed | Prevents future agents from rediscovering the same `SFixed.h:136` blocker and calling it a fresh surprise. |
| Regression gate | AppleClang/GCC compile of a tiny FixedPoints-only probe, not VP render equivalence. |
| Active-refactor boundary | Must not add `[env:native_vp]`, shims, or vendored patches to active repo. |

This is not a recommendation to reopen native VP. It is a narrow information-gathering lane.

### L1-05b: Build/Disassembly Numeric Audit

| Field | Assessment |
|---|---|
| Status | Viable now |
| Type | Build artefact inspection; no source edit |
| Capability unlocked | Finds accidental `double`, soft-float helpers, and symbol-size hotspots before debating fixed vs float. |
| Unsafe failure removed | Prevents a later numeric spike from optimising the wrong operation or hiding a `double` regression behind fixed-point arguments. |
| Regression gate | `pio run -e k1_hardware`; inspect `.elf` symbols/disassembly for soft-double calls around GDFT, render, quantisation, and show paths. |
| Active-refactor boundary | Read build artefacts only. No firmware edit and no runtime claim. |

Scout C ranked this as a high-value, no-source-edit experiment.

### L1-06: Test Harness Extension Design

| Field | Assessment |
|---|---|
| Status | Viable now |
| Type | Test design, no firmware edit |
| Capability unlocked | Defines the minimum proof package for any later numeric lane before implementation starts. |
| Unsafe failure removed | Stops candidate-library discussions from becoming taste debates. |
| Regression gate | Numeric conformance corpus + Tier A hashes + Tier B bands + release/harness build envelope. |
| Active-refactor boundary | Design only until current freeze/hardware gate state is stable. |

Existing harness scripts already encode useful principles: `derive_bands.py` makes VP Tier A the primary regression detector, `vp_diff.py` excludes nondeterministic mode 6 from Tier A, and `vp_capture.py` documents why the probe is independent of acoustic environment. Source: `scripts/regression-harness/derive_bands.py:5-11`, `80-82`; `vp_diff.py:1-10`, `40-70`; `vp_capture.py:2-15`.

Minimum FP-0 proof package before any source migration:

- Complete `SQ15x16` inventory with zero unknown buckets.
- Numeric golden corpus passing against current Pharap and K1 helper semantics.
- Candidate/facade spike proving parity on that corpus before call-site migration.
- `pio run -e k1_hardware` and `pio run -e k1_hardware_harness` passing, with RAM/flash delta checked against `docs/refactor/baseline-envelope.json`.
- VP Tier A: 11 deterministic modes bit-identical by `vp_diff.py`.
- VP Tier B: COM, FPS, and energy inside sealed bands; `quantum_collapse` requires Captain visual smoke.
- Runtime perf: render path remains inside the 2.0 ms ceiling and FPS remains inside the gate band.
- Harness-script gap closed or explicitly documented with a manual equivalent for `ap_diff.py`, `run_diff.sh`, and `vp_semantics_classifier.py`.

### L1-06b: `:vp_perf` Capture Parsing

| Field | Assessment |
|---|---|
| Status | Viable when Captain has a capture window |
| Type | Runtime evidence parsing; capture source must be labelled and hardware identity must be verified before direct serial access |
| Capability unlocked | Separates GDFT, primary render, secondary render, quantisation, show, and frame timing before any numeric backend spike. |
| Unsafe failure removed | Stops microbench-only conclusions from being mistaken for K1 timing proof. |
| Regression gate | Parse `:vp_perf` logs for `gdft_us`, `pri_render_us`, `sec_render_us`, quantisation, show, frame, heap, over-budget, and dropped-frame fields. |
| Active-refactor boundary | Parse existing captures when available; direct capture is allowed only for a runtime validation lane after target identity is verified. |

Scout C identified this as the best existing no-source-edit timing surface.

### L1-07: Public API / Internal Numeric Boundary

| Field | Assessment |
|---|---|
| Status | Viable now as architecture design |
| Type | Boundary model |
| Capability unlocked | Keeps serial/API/operator controls human-scale while allowing render/audio internals to specialise. |
| Unsafe failure removed | Prevents accidental conversion of public controls into fixed-point internals or leaking vendor numeric types over control surfaces. |
| Regression gate | Config schema/wire outputs remain float/int compatible; numeric conversion tested at internal boundary only. |
| Active-refactor boundary | No wire/API changes in active refactor. |

Evidence: `conf` is already dependency-light and float/int/public-stable. That is the correct outer boundary to preserve.

### L1-08: Licence and Vendoring Audit

| Field | Assessment |
|---|---|
| Status | Viable now |
| Type | Governance/read-only audit |
| Capability unlocked | Makes future patch/replace decisions legally and operationally clean. |
| Unsafe failure removed | Prevents silent dependency-fork risk and missing attribution/NOTICE obligations. |
| Regression gate | Licence matrix with local files present, upstream licence, modification policy, NOTICE requirement, and replacement licence compatibility. |
| Active-refactor boundary | Audit only. No vendored-source edit. |

Evidence: local `libraries/FixedPoints/library.json` says Apache-2.0 version 1.1.2 and repo `Pharap/FixedPointsArduino`; local files include `LICENCE` but no obvious top-level `NOTICE` in the vendored folder listing.

### L1-09: Lookup Table Parity Corpus

| Field | Assessment |
|---|---|
| Status | Viable now |
| Type | Numeric conformance design |
| Capability unlocked | Creates a low-blast-radius proof surface before touching mode bodies. |
| Unsafe failure removed | Prevents silent drift in dither, note hue, hue lookup, incandescent, or spectral tilt constants. |
| Regression gate | Golden construction/parity tests for fixed lookup tables and generated `spectral_tilt_lut`. |
| Active-refactor boundary | Test/spec lane only; no source edit until FP-0 approval. |

Scout A ranked this as immediately viable because lookup tables are central enough to matter but narrow enough to measure.

### L1-10: Numeric Golden Corpus

| Field | Assessment |
|---|---|
| Status | Viable now as test design; implementation waits for FP-0 approval |
| Type | Behavioural conformance design |
| Capability unlocked | Lets K1 judge candidate libraries by existing behaviour rather than by API appeal. |
| Unsafe failure removed | Prevents a replacement from silently changing literal construction, rounding, overflow, helper functions, or final LED quantisation. |
| Regression gate | Golden outputs for Pharap `SQ15x16` plus K1 helpers: `fromInternal`, `getInternal`, casts, add/sub/mul/div, comparisons, clamp/min/max, `fabs_fixed`, `fmod_fixed`, interpolation, low-pass, HSV, palette conversion, and `CRGB16` quantisation. |
| Active-refactor boundary | Corpus definition only in this pass; no test harness source edits without FP-0 approval. |

This is the highest-leverage Level 1 test vector from Scout D. It turns "could we replace the library?" into a measurable parity question.

### L1-11: Dependency Governance / SBOM Ledger

| Field | Assessment |
|---|---|
| Status | Viable now |
| Type | Licence, provenance, and release-governance audit |
| Capability unlocked | Makes later vendoring, patching, or replacement decisions auditable. |
| Unsafe failure removed | Prevents an invisible fork, missing notices, or a candidate with unresolved licence posture from entering product firmware. |
| Regression gate | Ledger includes dependency name, version/tag/hash, source URL, local diff status, licence, notice requirement, modification policy, and release-packaging action. |
| Active-refactor boundary | Documentation only. No vendored-source edit. |

Scout F found the current Pharap vendored state is low modification risk but incomplete as a release-governance story: metadata and licence are present, but the README requires a `NOTICE` package and no local `NOTICE` file exists. This should be resolved as a packaging policy before a product release, not by patching the library during Rows 3-4.

### L1-12: Sandbox Package Resolution

| Field | Assessment |
|---|---|
| Status | Viable now outside the repo |
| Type | `/tmp` PlatformIO/ESP-IDF package-resolution probe |
| Capability unlocked | Separates "candidate looks good on paper" from "candidate can actually be built under the K1 toolchain family". |
| Unsafe failure removed | Prevents build-system churn or IDF component plumbing from entering the active firmware before the candidate has earned attention. |
| Regression gate | Throwaway sandbox resolves and compiles a tiny numeric-only program for `fpm`, FR_Math, libfixmath, ESP-DSP, and IQMath where applicable; no active `platformio.ini` edits. |
| Active-refactor boundary | Sandbox path only; do not add dependencies to this repo. |

This is especially important for ESP-DSP and IQMath because they are ESP-IDF component-registry packages, while the active firmware is Arduino/PioArduino through PlatformIO.

## 4. Explicit Deferrals

- Replacing `SQ15x16` globally: deferred. Too much behavioural blast radius.
- Patching vendored FixedPoints in active repo: deferred. Conflicts with the locked current `native_vp` boundary.
- Rewriting GDFT around ESP-DSP or FFT: separate audio architecture lane, not a FixedPoints cleanup task.
- Moving public config to fixed-point: rejected at Level 1. Public config is already dependency-light and human-scale.
- Using host-native VP equivalence as a gate: rejected unless Captain explicitly reopens the strategic decision.

## 5. Remaining Questions

- Which `SQ15x16` buckets are memory-footprint hot spots versus only semantic hot spots?
- Does any candidate library exactly preserve Pharap's construction/truncation/overflow behaviour, or must the K1 facade deliberately emulate Pharap?
- Can IQMath and ESP-DSP be used from the current Arduino/PlatformIO setup without converting this work into an ESP-IDF component migration?
- What is the correct product-release policy for Pharap's README-level `NOTICE` requirement when upstream appears not to ship a `NOTICE` file?
- Scout E architecture/API boundary report did not return before synthesis cutoff. The current boundary assessment therefore comes from local source review plus Scouts A/C/D/F, not a completed Scout E report.

## 6. Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-25 | Codex | Created draft Level 1 vector dossier while SSA scouts ran in parallel. |
| 2026-05-25 | Scout A + Codex | Merged usage/domain inventory and added lookup-table parity vector. |
| 2026-05-25 | Scout C + Codex | Merged ESP32-S3/toolchain findings, build/disassembly audit, and `:vp_perf` timing vector. |
| 2026-05-25 | Scout B + Codex | Merged ecosystem shortlist and current external source check. |
| 2026-05-25 | Scout D + Codex | Merged parity, VP/AP gate, and FP-0 approval-evidence requirements. |
| 2026-05-25 | Scout F + Codex | Merged licence, vendoring, NOTICE, and candidate-governance findings. |
