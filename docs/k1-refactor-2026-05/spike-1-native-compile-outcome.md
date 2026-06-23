---
abstract: "Spike #1 outcome record — native-compile feasibility for vp_probe + light_mode_gdft. Per Captain ratification 2026-05-25 (matrix path B), this is the DECISION GATE for the VP regression gate model. PASS → native VP per-commit gate (agent-executed, ~0 Captain-time, full per-commit bisection). FAIL → bounded-bisect hardware VP gating + per-commit static classification of VP-semantics commits. Per-commit hardware gating throughout is NEITHER branch. Binary pass criterion: (a) vp_probe TU compiles under [env:native_vp], (b) light_mode_gdft produces deterministic CRGB output from synthetic spectrogram input that matches a hardware-captured reference for the same input within Tier B tolerance. Agent-time timebox: 2 working days. Captain hardware reference capture is the final pass-criterion step (queued for when convenient). Throwaway worktree at /Users/spectrasynq/SB-spike1-native-vp on branch spike/native-vp-attempt — NO commit/push/tag without explicit Captain approval."
---

# Spike #1 — Native-Compile Feasibility Outcome

| Field | Value |
|---|---|
| Spike start | 2026-05-25 |
| Spike status | **CLOSED — VERDICT: FAIL (Captain ruling 2026-05-25, option B).** Native VP per-commit gate is abandoned. Bounded-bisect hardware fallback is active. Worktree preserved as evidence; no vendored patch; no Option C. See §8 Final Verdict. |
| Branch | `spike/native-vp-attempt` (created from `00a0fcb` — current HEAD) |
| Worktree | `/Users/spectrasynq/SB-spike1-native-vp/` |
| Authority | Captain ratification 2026-05-25 (matrix path B + path A continuation): authorised native-only, no serial, no hardware capture by agent, no commit/push/tag without explicit approval |
| Agent-time timebox | 2 working days (~6-8 iterations expected before either PASS or "cannot reasonably shim" FAIL verdict) |
| Verdict | **FAIL.** Class E (vendored FixedPoints in-class `static constexpr SFixed` non-literal) is rejected by AppleClang 17 AND GCC-15; only lenient xtensa-gcc accepts it. A native compiler cannot be trusted as a compiler-equivalent gate. Bounded-bisect hardware VP gating adopted (Captain ruling 2026-05-25). |
| PIO env | `pio platform list` shows espressif32 5.3.0 / 5.4.0 / 6.0.0 / 7.0.1 / pioarduino 54.03.20 / tasmota 2024.06.0 installed; `platform = native` worked out-of-box on first `pio run -e native_vp` invocation |

## 1. The binary pass criterion (locked from matrix)

Both must hold for PASS:

1. **(a)** `vp_probe` TU compiles under `[env:native_vp]` — meaning `vp_probe_seed_inputs` + `vp_probe_prepare_render` + `vp_probe_render_hash` build natively (no Arduino, no ESP-IDF, no FastLED RMT — shim only what `millis()`/`micros()`/FastLED palette helpers genuinely require).
2. **(b)** `light_mode_gdft` produces deterministic CRGB output from synthetic spectrogram input that **matches** a hardware-captured reference for the same input within Tier B tolerance (energy / COM / FPS bands TBD; bit-identical hash via Tier A is the strongest test).

A FAIL can come from: (i) build won't compile after exhausting reasonable shim effort, (ii) build compiles but output is non-deterministic, (iii) build compiles and is deterministic but does not match hardware reference within tolerance.

## 2. Iteration log

### Iteration 0 — Scaffold (2026-05-25)

**Actions:**
- Created throwaway worktree `/Users/spectrasynq/SB-spike1-native-vp/` on branch `spike/native-vp-attempt` off current HEAD `00a0fcb`.
- Added `[env:native_vp]` section to worktree `platformio.ini` (lines added at end of file; pure additive; does NOT affect `[env:k1_hardware]`).
- Created directory `SPECTRASYNQ_K1_FIRMWARE/_spike_native_vp/shims/`.
- Created `_spike_native_vp/main.cpp` with trivial smoke-test main (just prints status).
- Build attempt: NOT YET ATTEMPTED THIS ITERATION (next iteration verifies PIO env config parses + trivial main builds).

**Open at iteration end:** PIO env validity, trivial native build success.

### Iteration 1.0 — Trivial main + PIO env validation (2026-05-25)

**Actions:**
- `pio run -e native_vp` (from worktree) on trivial main with no spike includes.

**Evidence [FACT, captured from pio run output]:**
```
Processing native_vp (platform: native)
Compiling .pio/build/native_vp/src/_spike_native_vp/main.o
Linking .pio/build/native_vp/program
========================= [SUCCESS] Took 0.41 seconds =========================
```

**Verdict:** `[env:native_vp]` parses correctly; `platform = native` works without manual install; trivial main builds and links in 0.41s. Foundation valid.

### Iteration 1.1 — Add `#include "lightshow_modes.h"` to main.cpp (2026-05-25)

**Actions:**
- Edited `_spike_native_vp/main.cpp` to add `#include "lightshow_modes.h"` (resolved via `-I SPECTRASYNQ_K1_FIRMWARE` in build_flags).
- Re-ran `pio run -e native_vp`.

**Evidence [FACT]:**
```
In file included from SPECTRASYNQ_K1_FIRMWARE/_spike_native_vp/main.cpp:10:
SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:1:10: fatal error: 'Arduino.h' file not found
    1 | #include <Arduino.h>
```

**Verdict:** Failure class A1 — missing system header `Arduino.h` (expected). PIO build did find `lightshow_modes.h` and started compiling it; cascade-stop at first system include.

**Side observation:** LSP/clangd diagnostic claimed `'lightshow_modes.h' file not found` — false positive. clangd doesn't read PIO's `build_flags` `-I` paths without an explicit `compile_commands.json`. The PIO build is the source of truth here; LSP diagnostics for this spike should be ignored or `pio run -t compiledb` should be run if LSP fidelity matters.

### Iteration 1.2 — Empty `Arduino.h` shim (2026-05-25)

**Actions:**
- Created `_spike_native_vp/shims/Arduino.h` with just `#pragma once`.
- Re-ran build.

**Evidence [FACT]:**
```
SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:2:10: fatal error: 'FastLED.h' file not found
    2 | #include <FastLED.h>
```

**Verdict:** Empty shim cleared. Next failure class A2 — missing system header `FastLED.h`. Loop confirmed working.

### Iteration 1.3 — Empty `FastLED.h` shim (2026-05-25)

**Actions:**
- Created `_spike_native_vp/shims/FastLED.h` with just `#pragma once`.
- Re-ran build.

**Evidence [FACT]:**
```
SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:3:10: fatal error: 'FixedPoints.h' file not found
    3 | #include <FixedPoints.h>
```

**Verdict:** Next system header. FixedPoints is real (header-only template lib at `libraries/FixedPoints/src/`); attempting include path before shim.

### Iteration 1.4 — Add `-I libraries/FixedPoints/src` to build_flags (2026-05-25)

**Actions:**
- Added `-I libraries/FixedPoints/src` to `[env:native_vp]` build_flags.
- Re-ran build.

**Evidence [FACT, multi-class — first substantive failure batch]:**
```
SPECTRASYNQ_K1_FIRMWARE/constants.h:136:3: error: unknown type name 'SQ15x16'
SPECTRASYNQ_K1_FIRMWARE/constants.h:137:3: error: unknown type name 'SQ15x16'
...10 occurrences total in constants.h at lines 136, 137, 141, 142, 146, 147, 148, 327, 342, 357...
SPECTRASYNQ_K1_FIRMWARE/constants.h:255:15: error: default initialization of an object of const type
  'const uint8_t[256]' (aka 'const unsigned char[256]')
  255 | const uint8_t gamma8_lut[256] PROGMEM = {
SPECTRASYNQ_K1_FIRMWARE/constants.h:255:30: error: expected ';' after top level declarator
SPECTRASYNQ_K1_FIRMWARE/globals.h:7:10: fatal error: 'Ticker.h' file not found
    7 | #include <Ticker.h>
```

**Verdict — THREE failure classes simultaneously:**

- **Class A continuing — missing system header:** `Ticker.h` (transitive via `globals.h` which is included from `lightshow_modes.h:5`).
- **Class B — Arduino macro undefined:** `PROGMEM` (used at `constants.h:255` for `gamma8_lut[256] PROGMEM = {...}`). Native build has no `PROGMEM` macro; it's an AVR/ESP-IDF concept (place in program memory). On native, `PROGMEM` should be a no-op `#define PROGMEM`.
- **Class C — typedef out of scope:** `SQ15x16` (10 occurrences in `constants.h`). Root cause [INFERENCE]: `lightshow_modes.h` `#include`s `<FixedPoints.h>` but NOT `<FixedPointsCommon.h>` (the latter defines `SQ15x16`/`UQ15x16` etc. typedefs). In single-TU build, `SPECTRASYNQ_K1_FIRMWARE.ino` includes `FixedPointsCommon.h` before `lightshow_modes.h` (and therefore before `constants.h`), putting the typedef in scope. **This is direct evidence of single-TU implicit coupling: `lightshow_modes.h` does not self-bootstrap its dependency chain.**

**Decision implication — load-bearing for Row 2:** Class C is exactly the kind of include-hygiene work per-mode TUs (Row 2) will require. Each `light_mode_X.cpp` will need to include its actual dependencies explicitly rather than relying on `.ino` preloading. The fix surface is small (add `FixedPointsCommon.h` to `lightshow_modes.h`'s includes, or to each per-mode `.cpp`). **This may also affect Row 4 scope**: when 58 led_utilities.h functions move to `led_utilities.cpp`, that `.cpp` will also need to bootstrap its includes (currently led_utilities.h's includes are: `<Arduino.h>, <FastLED.h>, <FixedPoints.h>, <FixedPointsCommon.h> (likely missing), <math.h>, "globals.h", "constants.h"`).

### Iteration 2 — Source-hygiene patch + batch structural/empty shims + macros (2026-05-25)

**Actions:**
- **Source-hygiene patch (the correct owner, NOT a harness prelude — per Captain Finding 1):** `constants.h:4` patched to add `#include <FixedPointsCommon.h>`. The original line `#include <FixedPoints.h> // Include for SQ15x16 type used within` is **wrong** — `SQ15x16` is defined in `FixedPointsCommon.h`, not `FixedPoints.h`. Single-TU build masked this because `.ino` preloads `FixedPointsCommon.h`. Recorded in §3.1 source-hygiene patch list. **This is a real defect Row 2/Row 4 must fix.**
- Added `PROGMEM` + `F(x)` + `pgm_read_byte*` macro no-ops to `Arduino.h` shim (Class B fix).
- Batch shims created with category tags:
  - **structural:** `freertos/task.h` (`typedef void* TaskHandle_t`), `Ticker.h` (stub class), `FirmwareMSC.h` (stub class), `USB.h` (`USBCDC` with `.print()`→stdout so VPO output is capturable, `USBClass`).
  - **empty:** `FS.h`, `LittleFS.h`, `Wire.h`, `m5rotate8.h`.
  - **structural-RNG:** `esp_random.h` (`esp_random()`→`std::rand()`).
- Re-ran build (AppleClang default).

**Evidence [FACT] — two new failure classes:**
```
libraries/FixedPoints/src/FixedPoints/SFixed.h:136:26: error: constexpr variable cannot have
  non-literal type 'const SFixed<15, 16>'
  136 | static constexpr SFixed Epsilon = SFixed::fromInternal(1);
SPECTRASYNQ_K1_FIRMWARE/constants.h:140:11: note: in instantiation of template class 'SFixed<15, 16>'
  requested here:  140 |   SQ15x16 r;
  ...same for MinValue, MaxValue, Pi, E, Phi, Tau (7 members)...
SPECTRASYNQ_K1_FIRMWARE/Palettes.h:17:1: error: unknown type name 'DEFINE_GRADIENT_PALETTE'
  17 | DEFINE_GRADIENT_PALETTE(ib_jul01_gp){
```

- **Class E (SIGNIFICANT) — vendored FixedPoints rejected:** `SFixed<15,16>` (= `SQ15x16`) has in-class `static constexpr SFixed Epsilon/MinValue/MaxValue/Pi/E/Phi/Tau` members initialised with the enclosing type before it is complete. The C++ standard requires the type to be *literal* for a `constexpr` variable; `SFixed` is incomplete at that point → ill-formed. The source-hygiene patch worked (SQ15x16 now resolves), which is exactly why the build now reaches the FixedPoints template body and surfaces this.
- **Class F (render-semantic) — FastLED palette macro:** `DEFINE_GRADIENT_PALETTE` is a FastLED macro used at file scope in `Palettes.h` to define gradient palette data feeding `ColorFromPalette`. Render-semantic; empty FastLED shim cannot cover it.

### Iteration 3 — Force GCC-15 via extra_scripts (DECISION-CRITICAL test of Class E) (2026-05-25)

**Hypothesis:** Class E is AppleClang strictness; xtensa-esp32 GCC accepts it, so desktop GCC-15 (same family) likely does too. GCC-15 + `gcc-15` confirmed present at `/opt/homebrew/bin/`.

**Actions:**
- Created `_spike_native_vp/use_gcc.py` extra_script: `env.Replace(CC="gcc-15", CXX="g++-15", LINK="g++-15")`.
- Added `extra_scripts = pre:...use_gcc.py` to `[env:native_vp]`.
- Clean rebuild.

**Evidence [FACT] — hypothesis FALSIFIED:**
```
>>> spike1 use_gcc.py: CC/CXX/LINK forced to gcc-15/g++-15      <- override confirmed active
libraries/FixedPoints/src/FixedPoints/SFixed.h:136:26: error: constexpr variable cannot have
  non-literal type 'const SFixed<15, 16>'                        <- IDENTICAL error under GCC-15
```

**Verdict: Class E is rejected by BOTH AppleClang 17 AND GCC-15.** Only the older xtensa-esp32 GCC (~GCC 12/13 bundled with IDF 5.4.1) is lenient about this ill-formed pattern. Modern desktop compilers of either family enforce the standard.

### STOP — failure-accountability rule (2026-05-25)

Per operating contract: "After two failures of the same type, STOP — state what was attempted, the actual failure mechanism, and the proposed alternative."

- **Two same-type failures:** Class E rejected by AppleClang 17 (iter 2) and GCC-15 (iter 3).
- **Actual failure mechanism:** vendored FixedPoints library (`libraries/FixedPoints/src/FixedPoints/SFixed.h:136-144`, and almost certainly the parallel `UFixed.h`) uses in-class `static constexpr SelfType Member = ...` initialisers that are ill-formed under any standard-conformant compiler because the enclosing type is not yet a literal type. The K1 firmware only compiles because xtensa-gcc is lenient.
- **This is not shimmable.** It is in the library's own template definition, reached the moment `SQ15x16` is instantiated (which `constants.h` does immediately). No shim avoids it.

## 7. Verdict trajectory + decision options (STOP point, 2026-05-25)

**Native compile of the unmodified render path is NOT achievable** with shims alone. Two compounding obstacles:

**Obstacle 1 — vendored FixedPoints patch required (confirmed blocker).** To compile natively, `SFixed`/`UFixed` must be patched to relocate the offending `static constexpr` members (e.g., to out-of-line `static const` definitions, or accessor functions). ~7 members × 2 template classes ≈ 14 sites. This is a **vendored-library modification** that would need to be permanent (or guarded) and verified behavior-preserving on xtensa-gcc too. Small in LOC, real in governance (touches a dependency).

**Obstacle 2 — bit-identical Tier A across compiler families is uncertain (structural risk, not yet measured).** Even after Obstacle 1 is patched and FastLED color math is ported/compiled, the native VP gate's value depends on its output matching hardware. The firmware builds with `-O3 -ffast-math`. Fixed-point `SQ15x16` ops are deterministic integer math (should match). But the render path also uses `float` (HSV conversion, several modes) and `-ffast-math` permits reassociation / non-IEEE behavior that **differs across compiler families and architectures** (xtensa-gcc-12 vs native-gcc-15). Whether the post-quantisation Tier A hash matches bit-for-bit is unverified and at material risk for any float-using path. If it doesn't match, the native gate degrades from bit-identical Tier A to a looser Tier-B-tolerance gate — weaker than the hardware gate it was meant to cheaply replace.

**This changes the Q1 cost/benefit.** Captain's Q1 Option-1 attraction was "native VP gate = agent-run, ~0 Captain-time, full per-commit bisection, bit-identical." That ideal is now in question: it requires vendored patching AND may only deliver a tolerance-gate, not a bit-identical gate.

### Decision options (Captain owns this strategic fork)

| Option | What it is | Cost | Risk | When it wins |
|---|---|---|---|---|
| **A — Invest** | Patch FixedPoints (vendored) + port/compile FastLED color math + measure actual native↔hardware divergence on `light_mode_gdft` | ~1-2 more agent-days; permanent vendored patch | Bit-identical may still fail under -ffast-math → fall back anyway after spending the effort | If a cheap per-commit VP gate is worth a vendored patch AND divergence turns out to be zero/absorbed-by-quantisation |
| **B — Declare FAIL → bounded-bisect hardware fallback (Q1 FAIL branch)** | Adopt the pre-committed fallback: per-sub-phase hardware VP gating + per-commit static classification of VP-semantics commits to bound bisect window | 0 further spike effort; ~15-22 Captain hardware sessions across the refactor | Larger bisect windows than per-commit native; more Captain hardware time | If the vendored patch + float-divergence risk aren't worth it — the fallback is already safe and well-defined |
| **C — Hybrid (de-risk first)** | Patch FixedPoints ONLY to confirm full compilation is achievable (answers "can it compile at all" definitively); defer the bit-identical question to ONE hardware-diff probe; then choose A or B with real data | ~0.5 agent-day + 1 Captain hardware capture | Minimal — buys information before committing | If Captain wants the compilation + divergence questions answered empirically before ruling |

**Agent (CTO/CPO) recommendation:** lean **B**, with **C** as the cheap de-risk if you want the empirical answer before committing. Reasoning: the bit-identical-float risk under `-ffast-math` is structural, not incidental — it's the reason a native gate is unlikely to deliver the bit-identical Tier A guarantee that made Option 1 attractive. A Tier-B-tolerance native gate is materially weaker than hardware and may not justify a permanent vendored-library patch when the bounded-bisect hardware fallback is already defined and safe. **B keeps the refactor moving on a known-good gate model; C spends ~0.5 day + 1 capture to convert the recommendation from [INFERENCE] to [FACT] before you commit.** Either way, this does not block Rows 1/3/4/2 — those gate on hardware under the fallback regardless.

**Note on the `-ffast-math` risk being real for the whole refactor, not just the spike:** even the *hardware* harness self-baselines at the Freeze commit, so cross-compiler divergence does NOT affect the hardware gate (same binary, same chip, deterministic). The divergence risk is *specific to* a native gate trying to mirror hardware. The hardware fallback is immune to it.

## 3. Shim list (running, status as of iteration 1.4)

| Shim | Status | Type | Notes |
|---|---|---|---|
| `Arduino.h` | ✅ empty stub created | empty shim | Iteration 2 will add `PROGMEM` + `F()` macros |
| `FastLED.h` | ✅ empty stub created | empty shim | Iteration 2+ will add `CRGB`/`CRGBPalette16`/`ColorFromPalette` stubs (Class D work) |
| `FixedPoints.h` | ✅ real source via `-I libraries/FixedPoints/src` | real | Header-only template library — compiles native |
| `FixedPointsCommon.h` | ⚠️ same `-I` path; needs explicit include in main.cpp (single-TU coupling exposed) | real | See iteration 1.4 Class C |
| `Ticker.h` | ⏳ iteration 2 | empty shim | Transitive via `globals.h:7` |
| `<freertos/task.h>` | ⏳ iteration 2 | empty shim (then `TaskHandle_t` stub) | Used by `globals.h` for task handles |
| `FS.h`, `LittleFS.h`, `Ticker.h`, `USB.h`, `FirmwareMSC.h`, `Wire.h` | ⏳ iteration 2 | empty shims | Transitive via globals.h includes; not used by vp_probe + light_mode_gdft directly |
| `esp_random.h` | ⏳ iteration 2 | small shim | Provides `esp_random()`; map to `std::rand()` for native |
| `m5rotate8.h` | ⏳ iteration 2 | empty shim | Encoder lib; not used by vp_probe + light_mode_gdft |
| `constants.h` (local) | ✅ source-used (after Class C fix) | real source | Will compile once `SQ15x16` + `PROGMEM` resolved |
| `globals.h` (local) | ⏳ depends on iteration 2 shims | real source | Will likely need targeted Class D stubs for the types it declares |
| `led_utilities.h` (local) | ⏳ pending | real source | 58 plain function defs; Class D risk = functions called by light_mode_gdft may have unportable bodies (esp32-specific math intrinsics, etc.) |
| `GDFT.h`, `presets.h`, `bridge_fs.h`, `utilities.h`, `i2s_audio.h`, `noise_cal.h`, `buttons.h`, `knobs.h`, `serial_menu.h`, `system.h` | ⏳ iteration 3+ | source or stub | Pulled in transitively; most should be empty-stubable for vp_probe path; `GDFT.h` defines spectrogram structures `light_mode_gdft` consumes — likely needs real source |

## 3.1 Source-hygiene patch list (real defects in K1 source — NOT harness-only workarounds)

Per Captain Finding 1 (2026-05-25): patch the owning header, do not mask defects via spike-`main.cpp` preludes. These are genuine include-hygiene defects that Row 2/Row 4 per-TU splits must fix in the real source.

| File:line | Defect | Patch applied (worktree) | Row impact |
|---|---|---|---|
| `constants.h:4` | Includes `<FixedPoints.h>` with comment "for SQ15x16" but `SQ15x16` is actually in `<FixedPointsCommon.h>`. Single-TU build masks this because `.ino` preloads `FixedPointsCommon.h` before `constants.h`. | Added `#include <FixedPointsCommon.h>` to `constants.h` | Row 2/Row 4: each per-TU `.cpp` that transitively uses `SQ15x16` needs the owning header to self-bootstrap. This is the canonical example of the include-hygiene sub-task. |

**Anticipated (not yet hit):** similar owner-include defects likely exist in other headers that use FastLED/FixedPoints/Arduino types without including their definers (masked by `.ino` preload order). The native-compile loop is an effective detector for these — each one surfaces as an "unknown type" / "not found" the moment a header is compiled outside the `.ino` prelude.

## 4. Macro stub list (Arduino-isms, running)

| Macro | Native value | Status |
|---|---|---|
| `PROGMEM` | `#define PROGMEM` (no-op) | ⏳ iteration 2 |
| `F(x)` | `#define F(x) (x)` (no-op string literal wrap) | ⏳ iteration 2 (anticipated; not yet observed in cascade) |
| `pgm_read_byte_near`, etc. | possibly needed by gamma8_lut consumers | ⏳ iteration N |

## 5. Decision implications (running notes, post-iteration-1.4)

- **Single-TU implicit coupling confirmed [FACT].** Iteration 1.4's Class C error (`SQ15x16` undeclared in `constants.h` despite `lightshow_modes.h` `#include`ing `<FixedPoints.h>`) is direct evidence: the existing source assumes `.ino`-driven include ordering. Per-mode TUs (Row 2) will hit this for every transitively-required symbol that the current include order silently resolves. **Row 2 execution must include an include-hygiene pass per `.cpp` file**, not just rely on `#include "lightshow_modes.h"` at the top.
- **Row 4 scope refinement informed by iteration 1+.** If light_mode_gdft's body calls functions in led_utilities.h that themselves call ESP-IDF/FastLED intrinsics that can't be cleanly stubbed (e.g., RMT5 driver calls, FreeRTOS task handles, hardware timer APIs), those specific functions become C3-extraction-blockers — meaning Row 4 minimal scope (`led_utilities.h` definitions → `led_utilities.cpp`) is necessary for ODR but not sufficient for native VP. Additional Row 4 work (further partition of unportable functions vs portable functions; potentially behind a `#ifdef NATIVE_VP` guard within `led_utilities.cpp`) would be needed.
- **If the shim list stays mostly empty** (most system headers are empty shims because vp_probe + light_mode_gdft don't use those symbols), Spike #1 PASS is achievable with modest shim work — and that **proves the existing single-TU code is mostly portable**, just badly include-coupled. PASS → native VP gate is the cheap, agent-run per-commit gate Captain wanted as Option 1.
- **If the shim list balloons** to include substantive content stubs for FastLED palette helpers, FreeRTOS task primitives, USB CDC, etc. — that's evidence the codebase's Arduino/ESP-IDF coupling runs deep and a native gate is impractical without substantial pre-Row-2 work. FAIL → bounded-bisect hardware VP gating with per-commit static classification of VP-semantics commits.

The classification — PASS-via-modest-shims vs FAIL-via-deep-coupling — is the decision gate's actual purpose. Iterations 2-N will produce evidence one way or the other.

## 6. Captain decision points

- **Hardware reference capture** (final pass criterion step): when iteration N has produced deterministic native CRGB output for synthetic spectrogram input, Captain captures the same synthetic-input → hardware CRGB output via `:vp_probe=all` (or a dedicated test command) → file. Agent diffs native vs hardware → PASS/FAIL ruling.
- **Tier B tolerance band** for native↔hardware diff: TBD; recommend Captain rule at first diff attempt based on what magnitudes the differences actually take.
- **Continue vs abort spike**: if iteration progress stalls (e.g., a header chain is fundamentally Arduino-coupled in ways shims can't fix within remaining timebox), Captain rules continue (extend timebox) vs abort (declare FAIL with documented blocker list).
- **Row 2 include-hygiene scope-add ratification** (when Spike #1 completes): the Class C finding in iteration 1.4 implies Row 2 execution carries an include-hygiene sub-task. Captain ratifies this as Row 2 scope at Phase 2 ratification time or earlier.

---

## 8. FINAL VERDICT — FAIL (Captain ruling 2026-05-25, option B)

**Spike #1 verdict: FAIL.** Native-compile cannot serve as a compiler-equivalent VP regression gate for this firmware.

**Blocking failure — Class E [FACT]:**
- The vendored `FixedPoints` library (`libraries/FixedPoints/src/FixedPoints/SFixed.h:136-144`, and the parallel `UFixed.h`) declares in-class `static constexpr SFixed Epsilon / MinValue / MaxValue / Pi / E / Phi / Tau` — `constexpr` of the enclosing type before it is a complete literal type. This is ill-formed under the C++ standard.
- **AppleClang 17 rejects it** (iteration 2).
- **GCC-15 rejects it identically** (iteration 3, with `g++-15` override confirmed active via `use_gcc.py`).
- **xtensa-esp32 GCC (IDF 5.4.1 toolchain) is lenient** and accepts it — which is the only reason the firmware builds.
- **Consequence:** the compiler that builds the firmware is *more permissive than any modern desktop compiler*. A native build is therefore not a trustworthy mirror of the firmware's compilation — even setting aside the separate `-ffast-math` float-divergence risk. A gate that compiles under different rules than the target cannot certify equivalence.

**Not pursued (per Captain ruling):** vendored FixedPoints patch (Option A), hybrid compile-confirmation probe (Option C). The bit-identical-Tier-A risk under `-O3 -ffast-math` for float-using paths (Obstacle 2, §7) compounded the verdict but was not the deciding factor — Class E alone is disqualifying.

**Active gate model — bounded-bisect hardware VP gating (Spike #1 FAIL branch):**
1. **Hardware Freeze Baseline** — captured on-device at the Freeze commit; immutable; "any divergence = regression" semantics (WAVEFORM_FAST is the only intentional VP-output change, lands pre-Freeze as commit 1).
2. **Bounded-bisect hardware VP gates** — per-sub-phase hardware capture (Captain), NOT per-commit native.
3. **Per-commit static classification for VP-semantics commits** — agent flags any commit whose diff touches `light_mode_*` bodies, `render/`, `color/`, or shared `vp_*` state; flagged commits get an additional in-sub-phase hardware gate to keep the bisect window small.
4. **Deliberate WAVEFORM_FAST regression injection test on the hardware gate** — Phase 4 hardening: revert the WAVEFORM_FAST fix on a throwaway branch, Captain captures Tier B for mode 7, confirm the COM-slope gate returns FAIL. Proves the hardware harness is a detector.

**Evidence preserved:** worktree `/Users/spectrasynq/SB-spike1-native-vp` on branch `spike/native-vp-attempt` is retained as evidence. No commit, push, tag, or deletion. The `[env:native_vp]`, shims, and `use_gcc.py` remain in the worktree as the reproducible failure record.

**Downstream:** the bit-identical-across-compilers risk never threatened the hardware gate — the hardware harness self-baselines at the Freeze commit (same binary, same chip, deterministic). The FAIL costs ~15-22 Captain hardware sessions across the refactor (vs the ~8-10 a native gate would have allowed) but on a known-good, trustworthy gate. Captain-time is the calendar critical path; this is a real cost, accepted knowingly.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) + Captain Yeap | Created. Spike #1 outcome record. Iteration 0 scaffold: worktree + [env:native_vp] + trivial main + outcome doc. Iteration 1+ pending. |
| 2026-05-25 | claude-code (Opus 4.7) | Iterations 1.0-1.4 evidence captured (per Captain path-A authorisation). PIO env config valid; native platform installed; trivial main builds 0.41s; empty shims for Arduino.h + FastLED.h cleared cascade; -I libraries/FixedPoints/src added; iteration 1.4 surfaced 3 simultaneous failure classes: A (missing system header Ticker.h, transitive), B (Arduino macro PROGMEM undefined), C (SQ15x16 typedef undeclared in constants.h — single-TU implicit coupling exposed because lightshow_modes.h #include <FixedPoints.h> but not <FixedPointsCommon.h>; .ino preloads the latter). Shim list table + macro stub list + decision implications written. Loop is working as expected. Pattern proven; ready for iteration 2+ batch-shim + Class D content-bearing type stubs work. Captain hardware capture: still queued (pending deterministic native CRGB output). |
| 2026-05-25 | claude-code (Opus 4.7) | Iterations 2-3 + STOP. Source-hygiene patch (constants.h += FixedPointsCommon.h, correct owner per Captain Finding 1, in §3.1) + batch structural/empty shims categorised per Captain Finding 3. Surfaced Class E (vendored FixedPoints in-class static constexpr SFixed non-literal, SFixed.h:136-144) + Class F (FastLED DEFINE_GRADIENT_PALETTE render-semantic). Iteration 3 forced GCC-15 via extra_scripts (confirmed active) -> Class E persists identically. STOP per failure-accountability (2 same-type failures: AppleClang 17 + GCC-15 both reject). Verdict trajectory in section 7: native compile requires vendored FixedPoints patch (Obstacle 1, confirmed) + faces bit-identical-Tier-A risk across compiler families under -O3 -ffast-math for float paths (Obstacle 2, unmeasured). Options A/B/C tabled; agent recommends B (FAIL -> bounded-bisect hardware fallback) with C (hybrid de-risk) as cheap alternative. Awaiting Captain ruling. No commit/push/tag; worktree intact. |
