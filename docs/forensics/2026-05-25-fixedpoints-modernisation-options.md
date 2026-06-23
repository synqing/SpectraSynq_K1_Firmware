---
abstract: "Read-only decision dossier for the K1 FixedPoints/SQ15x16 dependency. Maps current usage, known compiler and include-order risks, external modernisation candidates, architecture options, and the regression gates required before any replacement or containment work is approved."
---

# FixedPoints / SQ15x16 Modernisation Options

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Scope | `libraries/FixedPoints`, `SQ15x16`, render/audio numeric contracts |
| Mode | Read-only analysis. No firmware source edit, no serial, no upload, no commit. |
| Current branch evidence | `5681cab refactor(modes): Row 2 - split lightshow_modes.h into per-mode translation units` |
| Build evidence | `pio run -e k1_hardware` PASS compile-only; `pio run -e k1_hardware_harness` PASS compile-only. Not runtime proof. |

## 1. Doctrine Gate

### Relevant Rules

- [FACT] K1 numeric changes cross doctrine Rule 8: for the existing 96-bin Goertzel workload, Q15 fixed-point is a proven historical win, but this is explicitly not a blanket verdict against the ESP32-S3 LX7 single-precision FPU. Re-test triggers include `NUM_FREQS`, sample rate, chunk size, single-core constraint, or `esp_dsp` / FFT replacement. Source: `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official/docs/agent-outputs/analysis/sensory-bridge-lessons-doctrine.md:66-70`.
- [FACT] Current refactor gate requires every split or library change to name the K1 capability unlocked, the unsafe failure mode removed, and the regression gate that proves preservation. Source: memory and `docs/k1-refactor-2026-05/02-SPLIT-JUSTIFICATION-MATRIX.md:327-333`.
- [FACT] Native VP gating is locked out of the current refactor plan. Source: `docs/k1-refactor-2026-05/03-hardware-gate-package.md:11-15`.
- [FACT] Agents must not open the serial port. Runtime proof must come from Captain-provided captures. Source: `docs/k1-refactor-2026-05/03-hardware-gate-package.md:29-32`.

### K1 Evidence Touched

- [FACT] `constants.h` includes both `<FixedPoints.h>` and `<FixedPointsCommon.h>`, because `SQ15x16` lives in `FixedPointsCommon.h`. Source: `SPECTRASYNQ_K1_FIRMWARE/constants.h:4-5`.
- [FACT] `globals.h` also includes both headers and then uses `SQ15x16` in spectrogram, chromagram, novelty, colour, AGC, VU, UI mask, and hue state. Source: `SPECTRASYNQ_K1_FIRMWARE/globals.h:6-15`, `80-85`, `153-160`, `225-231`, `480-489`, `559-579`.
- [FACT] `CRGB16` is declared with three `SQ15x16` channels, while its comment still says "Unsigned Q8.8". Source: `SPECTRASYNQ_K1_FIRMWARE/constants.h:141-145`.
- [FACT] `SQ15x16` appears in 26 firmware files. Densest current use by `rg -c`: `led_utilities.h` 208, `globals.h` 50, `lightshow_modes.h` 39, `light_mode_quantum_collapse.cpp` 30, `GDFT.h` 28, `system.h` 27.

### North-Star Impact

- [INFERENCE] This dependency is not just a math utility. It currently defines the intermediate colour-memory surface (`CRGB16`), audio-feature smoothing state, AGC state, mode-local render maths, and probe/harness risk classification. A careless swap can preserve compilation while changing visual decay, brightness accumulation, chroma blend, and per-mode motion memory.
- [INFERENCE] The potential upside is real: a cleaner numeric boundary would make mode code easier to split, test, benchmark, and reason about. But the library must not be replaced on style grounds. It must be replaced only if it improves one or more of: deterministic testability, host compiler compatibility, hot-path timing, memory footprint, or visual control.

### Re-Test Triggers Crossed by Any Future Change

- Any change to `SQ15x16` representation, rounding, overflow, construction from float literals, or `CRGB16` channel type.
- Any change to `GDFT.h`, AGC smoothing, `spectrogram_smooth`, `chromagram_smooth`, or `novelty_curve`.
- Any change to `hsv`, `palette_*`, `show_leds`, dither, `hue_lookup`, or render mode colour accumulation.
- Any attempt to reintroduce native VP gating, host compiler parity, or vendored FixedPoints patching into the current refactor.

### Runtime Proof Required

- Compile-only gates: `pio run -e k1_hardware` and `pio run -e k1_hardware_harness`.
- Numeric parity gate: unit/golden tests for construction, rounding, conversion, comparison, multiply/divide, modulo helper, HSV/palette conversion, and `CRGB16` quantisation.
- K1 hardware gate: Captain capture using the locked bounded-bisect harness. Agent reads logs only.
- Visual gate: Tier A hashes where deterministic, Tier B energy/centre-of-mass/FPS where not, and Captain visual smoke for modes whose perceptual behaviour cannot be reduced to hashes.

### Minimal Edit Plan If Approved Later

No firmware edit is approved by this dossier. The smallest safe next step is a separate FP-0 research lane that measures current behaviour and proposes a containment boundary before changing any call site.

### Explicit Non-Goals

- Do not patch vendored FixedPoints during the current Row 2 / Rows 3-4-2 refactor unless Captain explicitly reopens the dead native VP gate decision.
- Do not replace `SQ15x16` directly across the tree.
- Do not change wire/API contracts.
- Do not treat compile success as runtime proof.

## 2. Current State

### What FixedPoints Provides Here

- [FACT] The vendored README says core types are provided by `FixedPoints.h`, while common aliases are provided by `FixedPointsCommon.h`. Source: `libraries/FixedPoints/README.md:73-80`.
- [FACT] The vendored README defines `SQ15x16` as `SFixed<15, 16>`, a 32-bit signed fixed-point Q15.16 alias. Source: `libraries/FixedPoints/README.md:90-92`.
- [FACT] The actual alias is `using SQ15x16 = SFixed<15, 16>;`. Source: `libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h:19-23`.
- [FACT] `SFixed<Integer, Fraction>` sets `LogicalSize = Integer + Fraction`, `Scale = 1 << Fraction`, and `InternalType = LeastInt<LogicalSize>`. For `SFixed<15,16>`, the logical size is 31 bits, so the selected internal type is the least signed integer type that can hold that logical size. Source: `libraries/FixedPoints/src/FixedPoints/SFixed.h:33-45`.

### What It Does Not Provide

- [FACT] K1 helper functions such as `fabs_fixed`, `fmin_fixed`, `fmax_fixed`, `fmod_fixed`, `interpolate`, and `random_float` are project utilities, not Pharap library APIs. They live in `SPECTRASYNQ_K1_FIRMWARE/utilities.h`.
- [INFERENCE] Replacing FixedPoints does not just mean finding arithmetic operators. The replacement must match K1's local helper semantics and all implicit construction/conversion behaviour at call sites.

### Known Active Risk

- [FACT] Spike #1 reached `libraries/FixedPoints/src/FixedPoints/SFixed.h:136-144`, where in-class `static constexpr SFixed` members are initialised while the enclosing type is incomplete. AppleClang 17 and GCC-15 reject this. Source: `docs/k1-refactor-2026-05/spike-1-native-compile-outcome.md:138-150`, `162-177`.
- [FACT] The locked hardware gate package says no native build, shim layer, vendored FixedPoints patch, or `[env:native_vp]` may re-enter the plan. Source: `docs/k1-refactor-2026-05/03-hardware-gate-package.md:11-15`.
- [INFERENCE] The production build is currently dependent on xtensa-gcc accepting a pattern stricter modern host compilers reject. That is a governance and testability risk even if the current hardware binary builds.

### Current Build Boundary

- [FACT] `platformio.ini` pins the K1 hardware env to pioarduino 54.03.20 / arduino-esp32 3.2.0 / ESP-IDF 5.4.1, uses `-O3` and `-ffast-math`, and depends on `file://libraries/FixedPoints`. Source: `platformio.ini:18-23`, `47-55`, `71-74`.
- [FACT] Harness builds extend release builds and add `ENABLE_AP_STREAM`, `ENABLE_FRAME_DUMP`, and `ENABLE_VP_PROBE_CMD`; release builds keep those flags off. Source: `platformio.ini:76-91`.
- [INFERENCE] Any host-based numeric proof must account for `-ffast-math` and compiler-family divergence. The current accepted fallback avoids this by comparing captures from the same target class rather than pretending native equals hardware.

## 3. Modernisation Options

| Option | Decision Use | Pros | Cons | Required Gate |
|---|---|---|---|---|
| 0. Keep Pharap as-is during current refactor | Recommended immediate state | Zero behavioural churn; current builds pass; aligns with locked hardware-gate plan | Leaves host compiler incompatibility and global type leakage in place | Continue current bounded-bisect hardware gate |
| 1. Contain behind K1 numeric facade | Recommended next research lane | Stops library names leaking through architecture; enables later backend swaps; documents domain semantics | Requires careful staged edits; can become empty indirection if not paired with tests | Golden numeric parity + compile + hardware capture for touched modes |
| 2. Patch vendored Pharap | Only if native-gate decision is explicitly reopened | Small local patch could unblock modern host compilers | Violates current `native_vp is DEAD` plan; permanent dependency fork; still may not deliver bit-identical host/hardware output | Captain approval + library patch review + xtensa parity + host compiler matrix |
| 3. Replace with another fixed-point library | Research only | May improve maintenance, math API breadth, or compiler compatibility | High semantic risk: rounding, overflow, literal construction, conversion, and operator behaviour may change | Candidate spike with no production adoption until parity and hardware proof |
| 4. Selective float conversion | Research only | ESP32-S3 has an FPU; may simplify render-colour code or remove fixed-point overhead where not needed | Could destabilise deterministic colour memory; `-ffast-math` makes host parity harder | Per-domain microbenchmarks, visual hashes, and perf envelope |
| 5. In-house minimal Q15.16 core | Last resort | Total semantic control; small surface if scoped only to what K1 uses | We own every edge case forever; high proof burden; least desirable unless all libraries fail | Exhaustive parity corpus and code-review gate before adoption |
| 6. Use Espressif DSP/IQ libraries selectively | Audio-kernel candidate, not CRGB16 drop-in | Official ESP ecosystem; optimised DSP/math primitives for ESP chips | C APIs / component assumptions; not a direct Pharap replacement for typed C++ render state | Isolated audio benchmark spike only |

## 4. External Candidate Notes

| Candidate | Current Source Notes | K1 Fit |
|---|---|---|
| Pharap FixedPointsArduino | Portable Arduino-oriented fixed-point library; C++11; Apache-2.0; `SQ15x16` alias in `FixedPointsCommon.h`; upstream docs also require packaging licence and notice. | Operational on K1 toolchain, but known host-compiler blocker and broad type leakage. |
| CNL | Modern compositional numeric C++ library; latest version requires C++20, with older 1.x supporting C++11. | Useful as design inspiration for safer numeric types; likely too heavy / toolchain-misaligned for immediate K1 firmware adoption. |
| fpm | C++ header-only fixed-point math library; requires C++11; designed as a float-like fixed-point type and guards against accidental float conversion. | Worth a throwaway spike. Stronger modern C++ posture than Pharap, but conversion strictness may cause large call-site churn. |
| libfixmath | C Q16.16 library; MIT; not actively maintained; optional caches can consume large static memory unless disabled. | Good baseline for simple Q16.16 arithmetic benchmarks; not a clean architectural fit for typed C++ render-domain code. |
| FR_Math | C fixed-point/fixed-radix library for embedded systems with broader math functions and BSD-2-Clause licence. | Worth a small spike if K1 wants C-style explicit fixed math; needs proof on PlatformIO/Arduino-S3 integration. |
| Espressif ESP-DSP | Official Espressif DSP library with optimised functions for ESP32, ESP32-S3, and ESP32-P4; includes matrix, dot product, FFT, IIR/FIR, vector math, Kalman. | Candidate for audio feature extraction or future FFT/FIR work, not a direct `SQ15x16` colour-memory replacement. |
| Espressif IQMath | ESP Component Registry library for 32-bit signed fixed-point IQ formats (`IQ1` to `IQ30`), targeting speed/accuracy/energy on ESP chips. | Interesting for audio/math kernels. Needs Arduino/PlatformIO integration check and licence review before any serious adoption. |

External source links used:

- Pharap FixedPointsArduino: https://github.com/Pharap/FixedPointsArduino
- CNL: https://github.com/johnmcfarlane/cnl
- fpm: https://github.com/MikeLankamp/fpm
- libfixmath: https://github.com/PetteriAimonen/libfixmath
- FR_Math: https://deftio.github.io/fr_math/
- Espressif ESP-DSP: https://github.com/espressif/esp-dsp and https://docs.espressif.com/projects/esp-dsp/en/latest/esp32/index.html
- Espressif IQMath: https://components.espressif.com/components/espressif/iqmath

## 5. API and Boundary Considerations

- [FACT] `config_types.h` keeps public/user configuration values such as `PHOTONS`, `CHROMA`, `MOOD`, `SENSITIVITY`, and `SATURATION` as `float`, not `SQ15x16`. Source: `SPECTRASYNQ_K1_FIRMWARE/config_types.h:82-114`.
- [INFERENCE] The healthiest boundary is likely not "make all public config fixed-point". The external control/API layer should stay human-readable and wire-stable. Numeric specialisation belongs at the render/audio boundary where timing, determinism, and range are load-bearing.
- [HYPOTHESIS] A future facade should express domain intent, not vendor type names:
  - `UnitQ` for 0.0-1.0 brightness/chroma/mix values.
  - `SignedUnitQ` for signed motion/offset values.
  - `ColourAccum` for high-resolution RGB accumulation before FastLED quantisation.
  - `AudioEnergyQ` for spectrogram/chromagram/AGC values.
- [INFERENCE] This would let future agents ask a better question than "is this `SQ15x16`?" They can ask "is this a unit interval, signed control, colour accumulator, or audio energy value?"

## 6. Testing Strategy

### FP-0 Inventory Tests

- Map every `SQ15x16` site into a domain bucket: colour accumulation, audio energy, smoothing coefficient, position, random field, UI mask, config-derived control, or lookup table.
- Record whether each bucket needs exact fixed-point determinism, range clamping, signedness, or only convenient fractional arithmetic.
- Fail the inventory if any site remains "unknown".

### Numeric Conformance Tests

- Construction from integer, float, and double literals used by K1.
- `fromInternal`, `getInternal`, integer/fraction extraction, cast to `float`.
- Add/sub/mul/div around 0, 1, negatives, tiny coefficients, and values near current K1 maxima.
- Current helper semantics: `fabs_fixed`, `fmod_fixed`, `interpolate`, fixed low-pass, min/max clamps.
- `CRGB16` accumulation and final `CRGB` quantisation for representative palette/hsv paths.

### Build Matrix

- Release: `pio run -e k1_hardware`.
- Harness: `pio run -e k1_hardware_harness`.
- Host compiler spike only if Captain explicitly reopens it; otherwise do not reintroduce `native_vp`.
- Regenerate `compile_commands.json` after any library/build-flag change.

### Performance Gates

- Measure GDFT / AGC hot path separately from render-colour accumulation.
- Measure per-mode frame time under the 2.0 ms ceiling.
- Track flash/RAM deltas versus the release baseline.
- Treat `-ffast-math` changes as high-risk because they may change float render behaviour even when fixed-point code is unchanged.

### Visual Behaviour Gates

- Tier A deterministic hashes for modes that can be reset and seeded.
- Tier B energy / centre-of-mass / brightness / FPS bands for modes with legitimate non-determinism.
- Mandatory Captain visual smoke for `quantum_collapse` and any mode whose source touches random fields, `SQ15x16` mode arrays, or shared colour helpers.

## 7. Recommendation

### Immediate Decision

[INFERENCE] Do not replace or patch FixedPoints inside the active Row 2 / Rows 3-4-2 refactor. The dependency is currently too load-bearing, the current branch builds, the `native_vp` path is explicitly dead, and any numeric backend change would expand the refactor blast radius into visual semantics.

### Next Useful Lane

[INFERENCE] Open a separate FP-0 research lane after the current hardware gates are stable:

1. Freeze a numeric inventory by domain, not by file.
2. Add a non-invasive facade proposal and parity tests around existing Pharap behaviour.
3. Benchmark status quo versus one fixed-point candidate and one selective-float path on K1 hardware.
4. Decide only from measured timing, RAM/flash delta, numeric parity, and visual capture evidence.

### Most Plausible End State

[HYPOTHESIS] The best end state is not "rip out FixedPoints". It is likely:

- Keep external config/API values as floats/ints.
- Contain render/audio internal fixed-point behind K1 domain types.
- Preserve fixed-point where it materially supports deterministic timing or accumulated colour memory.
- Replace or specialise only the narrow buckets where proof shows the current library blocks testing, costs performance, or obscures domain semantics.
- Consider Espressif DSP/IQ components for future audio kernels independently of the render-colour `CRGB16` surface.

## 8. Approval / Rescope Decisions for Captain

1. Approve or reject a separate FP-0 research lane after the current refactor gate.
2. Decide whether host-native compiler parity remains strategically valuable, despite the current `native_vp is DEAD` ruling.
3. Pick spike candidates: status quo vs `fpm`, FR_Math/libfixmath, Espressif IQMath, selective float, or a minimal in-house Q15.16 core.
4. Decide whether to correct the `CRGB16` comment mismatch as hygiene inside a later approved edit.
5. Decide whether Apache-2.0 NOTICE/licence packaging hygiene for the vendored Pharap library should be audited now or deferred.

## 9. Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-25 | Codex | Created read-only FixedPoints modernisation decision dossier. |
