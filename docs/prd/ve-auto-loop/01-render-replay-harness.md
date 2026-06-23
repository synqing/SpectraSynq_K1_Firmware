---
abstract: "BUILD SPEC (software BoM) for the host `render_replay` harness — Tier 1 of the VE-Auto-Loop. Host-compiles ONE real K1 light mode (FIRST TARGET: light_mode_bloom) + render_params.cpp against an Arduino/FastLED/SQ15x16 stub set (modelled on scripts/regression-harness/tempo_replay.py's ARDUINO_STUB pattern), drives it with synthetic audio frames, and dumps the leds buffer per frame in the EXACT VPABBytesPayload byte layout (uint8 R,G,B × LED_COUNT_VALUE) so host (Tier 1) and device (vpab_capture Tier 2) share one schema. Contains: goal, full stub set with hard-dependency flags, file-by-file BoM (CREATE render_replay.py + stub headers + a -DSB_RENDER_HOST_TEST introspection hook mirroring sb_tempo_debug_dump; MODIFY one mode .cpp), first-target-mode rationale (bloom: chromagram-only audio reach-through, minimal globals), the clang++ -std=c++17 compile command + I/O contract, acceptance criteria (compiles clean / deterministic / byte-layout match / sane known output), risks/landmines (FastLED colour-correction + LGP + gamma NOT modelled on host → [MECHANISM] not [MEASURED]), and a step-by-step build checklist. Zero-context build target. Read before building render_replay or wiring the VE-Auto-Loop inner loop."
---

# VE-Auto-Loop · 01 — Render-Replay Harness (Tier 1 host BoM)

> **Design source of truth:** `docs/architecture/visual-effects-autonomous-loop-assessment.md`.
> **Proven pattern donor:** `scripts/regression-harness/tempo_replay.py` (host-compiles a real firmware `.cpp` with an Arduino stub + `-DSB_*_HOST_TEST`, feeds synthetic input, dumps structured output). This spec is `render_replay` = the same pattern generalised from `sb_tempo.cpp` to a real **light mode + render_params**.
> **British English. Software-only BoM. This file is WRITE-ONLY; everything it references is READ-ONLY.**

---

## 1. Goal

Host-compile **one real K1 light mode** plus `render_params.cpp` (no PlatformIO, no ESP32, no hardware), drive it with **synthetic `AudioDrive` frames** (a deterministic time series of the audio-feature globals a mode reads), and **dump the `leds` buffer per frame in the EXACT `VPABBytesPayload` byte layout** — `uint8` triples `R,G,B` for `LED_COUNT_VALUE` LEDs — so the host (Tier 1, fast inner loop) and the device (`vpab_capture`, Tier 2, [MEASURED] gate) emit **one identical frame schema**. The driver above this harness must not be able to tell which tier produced a frame.

This is **MVP-0** of the autonomous loop: it closes edit → render → capture with *zero* generative machinery. "Edit" at MVP-0 = a parameter sweep over the `RenderParams` knobs and the synthetic-audio fixture; no firmware write/flash. Tier-2 on-device confirmation is a separate document.

### Non-goals (explicit, load-bearing)
- **NOT** modelling FastLED colour-correction / temperature, LGP optics, gamma, or temporal dither. The host reproduces only the **render maths + the documented quantise-to-bytes step** (`CRGB16 → CRGB uint8`). Any colour/optics fidelity claim from host output is **[MECHANISM]**, never **[MEASURED]** (see §9).
- **NOT** flashing, uploading, or touching a device. Write scope stops at `scripts/regression-harness/` + the single instrumented mode `.cpp`.
- **NOT** scoring aesthetics. This harness is the *plant + sensor*; the proxy panel, champion regression, and Captain's eye gate live in later VE-Auto-Loop docs.

---

## 2. First target mode — `light_mode_bloom` (and why)

**Chosen: `light_mode_bloom` (`SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp`).**

Selection criterion (from the assessment §"easiest first targets"): *a mode whose inputs are fully captured by `RenderParams` + a single audio snapshot, with minimal global reach-through.* Bloom is the cleanest:

| Property | Bloom | Why it wins |
|---|---|---|
| Audio reach-through | **`chromagram_smooth[12]` only** (confirmed: the only audio global it reads) | A 12-float snapshot fully describes its audio input. No spectrogram, VU, waveform, sweet-spot, or novelty coupling. |
| Render params | reads `active_render_params()` (PHOTONS, SATURATION, INCANDESCENT_*, hue state) | Already on the clean `RenderParams` boundary — no direct `CONFIG` reach-through. |
| Working buffer | `leds_16[NATIVE_RESOLUTION]` (`CRGB16`, 160) + `leds_prev_buffer` (motion memory) | Standard; the one stateful input is the caller-owned `leds_prev_buffer`, trivially seeded. |
| Signature | `void light_mode_bloom(CRGB16* leds_prev_buffer, SQ15x16 shift_multiplier)`; thin wrapper `light_mode_bloom_fast(CRGB16* leds_prev_buffer)` | Two args, both host-constructible. |
| Helpers | `draw_sprite`, `mirror_image_downwards`, `memset/memcpy` on `CRGB16` | Pure maths over `CRGB16`/`SQ15x16`; vendor or stub once, reuse for all modes. |

**Rejected alternatives:**
- `light_mode_waveform_fast` — wider reach-through: takes 4 extra by-reference state args (`last_color`, `waveform_peak_scaled_last`, …) **and** reads the waveform buffer + `CONFIG.SWEET_SPOT_MIN_LEVEL` (`max_waveform_val_raw = SWEET_SPOT_MIN_LEVEL*2`). Good *second* target once the stub set is proven; more snapshot fields to wire.
- `light_mode_comet` / `spectrum_river_v2` / `ember` — pull `ChannelEffectState` (comet pool, tide env, shimmer phase) + onset/novelty streams. Higher state surface; defer to Ext phases.

> Bloom proves the rig end-to-end with the smallest input vector. The harness is **mode-parameterised** (§5.1) so adding waveform/comet later is "list the extra globals in the snapshot + add a fixture column", not a rewrite.

---

## 3. Dependency inventory & stub strategy

Modelled on `tempo_replay.py`'s `ARDUINO_STUB` (a single in-Python heredoc written to a temp `stub/` dir, then `-I stub`). `render_replay` needs a **larger** stub set because a light mode pulls FastLED colour types and fixed-point maths that `sb_tempo` did not. Each dependency below is classified **STUB** (write a minimal shim), **VENDOR** (compile the real firmware/library source as-is on host), or **HARD** (genuine fidelity/effort risk — flagged honestly).

| Dependency | Real source | Strategy | Notes / hardness |
|---|---|---|---|
| `Arduino.h` core (`uint8_t` etc.) | toolchain | **STUB** | Trivial — reuse tempo_replay's pattern; add `min`/`max`/`constrain`/`abs` macros, `millis()` returning a host clock the driver controls. |
| FreeRTOS / `portMUX` critical-section macros | toolchain | **STUB** | No-op (as in tempo_replay). Bloom touches none; include for shared-header buildability. |
| `FixedPointsCommon.h` / `SQ15x16` | `FixedPoints` library (already a PlatformIO dep) | **VENDOR** | Header-only; point `-I` at the installed library path (or vendor a copy under `scripts/regression-harness/vendor/FixedPoints/`). **Fixed-point parity is load-bearing** — do NOT substitute `float`. See §9 R-FP. |
| `FastLED.h` → `CRGB`, `CHSV`, `hsv2rgb_*`, `nblend`, scale helpers | FastLED library | **HARD → curated subset** | Bloom uses `CRGB`/`CRGB16` arithmetic + colour conversion. Do **not** vendor all of FastLED (pulls platform/SPI/clockless drivers that won't host-compile). Write `stub/FastLED.h` exposing ONLY: `struct CRGB {uint8_t r,g,b;}`, `struct CHSV {uint8_t h,s,v;}`, `hsv2rgb_rainbow`/`hsv2rgb_spectrum` (port the real FastLED implementation byte-for-byte — these are pure integer maths), `scale8`, `qadd8`, `qsub8`, `nblend`. **HARD because** the chosen conversion + scale8 maths must match FastLED's exact integer rounding or host frames diverge from device by ±1 LSB. Mitigation: copy the canonical `scale8`/`hsv2rgb` bodies from the pinned FastLED version; unit-check against a few known triples. |
| `CRGB16` (16-bit working colour) | firmware (`globals.h` / a firmware colour header) | **VENDOR** | The mode's working type. Vendor the real definition + its `CRGB16↔CRGB` conversion so the host quantise step is the firmware's, not a guess. Confirm where `CRGB16` is declared and compile that source. |
| `globals.h` audio/colour/buffer globals | `globals.h` (+ `globals.cpp` for `extern`s) | **VENDOR (trimmed) / SUPPLY** | Bloom needs: `leds_16[160]`, `chromagram_smooth[12]`, `hue_position`/`chroma_val`/`hue_shifting_mix`/`chromatic_mode` (now surfaced via `RenderParams`), `NATIVE_RESOLUTION`, `LED_COUNT_VALUE`. Strategy: compile `globals.cpp` for the `extern`-backed symbols **OR** define a small `render_host_globals.cpp` that provides exactly the symbols the linker reports missing. Prefer the latter to avoid dragging audio-pipeline `.cpp`s onto the host. **The driver writes `chromagram_smooth[]` each frame** — that is the synthetic-audio injection point. |
| `render_params.h` / `render_params.cpp` | firmware | **VENDOR** | Compile the real `render_params.cpp`. Host builds a `RenderParams` directly (params are the mutable knob surface for sweeps) and `push_render_params(&rp)` so `active_render_params()` returns it. Heap-free, depth-2 stack — host-safe as-is. |
| `config_types.h` (`struct conf`) | firmware | **VENDOR** | Pure POD; included by `render_params.h`. Compiles on host unchanged. |
| `constants.h` (`NATIVE_RESOLUTION`, `NUM_FREQS`, `LED_COUNT_VALUE`) | firmware | **VENDOR** | Pure `#define`s. Include directly. **`LED_COUNT_VALUE` is the byte-count divisor for the dump (§6).** |
| Palettes (`palettes*.h` / palette tables) | firmware | **VENDOR if pulled** | Bloom's confirmed path is chromagram→colour, not a palette LUT; include the palette header only if the linker demands it. Tables are `const` POD → host-safe. |
| `draw_sprite`, `mirror_image_downwards`, fade/blur helpers | firmware (lightshow_modes.h / utils) | **VENDOR** | Pure `CRGB16`/`SQ15x16` maths. Compile the real definitions so motion-memory + mirror match the device. |
| `lightshow_modes.h` dispatch table | firmware | **READ-ONLY reference; do NOT compile whole** | The host calls `light_mode_bloom_fast()` directly — it does **not** go through the mode dispatch (which drags every mode + AP). Use the header only to confirm the signature. |

**Honest hard-dependency summary (flag these before building):**
1. **FastLED subset (HARD).** The single biggest fidelity risk. The host MUST reproduce FastLED's exact integer `scale8`/`hsv2rgb`/quantise maths or frames diverge. Pin the FastLED version, copy the real bodies, unit-test triples.
2. **`CRGB16 → CRGB` quantise (HARD-adjacent).** The device's canonical path is `leds_16 (CRGB16) → leds_out (CRGB uint8) → VPABBytesPayload.bytes`. `vpab_capture.cpp` fills `bytes[base]=.r, [base+1]=.g, [base+2]=.b` from an already-quantised `CRGB final_bytes[]`. The host must perform the **same** `CRGB16→CRGB` reduction the firmware does before the strip — reuse the firmware's conversion, do not reinvent. This is what makes host bytes share the device schema.
3. **Fixed-point parity (HARD-adjacent).** `SQ15x16` must be the real `FixedPoints` type, not float. A float substitution changes rounding and breaks bit-determinism vs device.
4. **Global-symbol surface (MEDIUM).** Resolve missing `extern`s by adding to `render_host_globals.cpp`, not by pulling audio `.cpp`s. Each pulled `.cpp` risks dragging the whole AP onto the host.

---

## 4. Where in the firmware the bytes come from (the schema anchor)

The host output MUST match `VPABBytesPayload` (`vpab_capture.h`):

```c
struct VPABBytesPayload {
  uint8_t channel; uint8_t mode; uint8_t dither_step_value; uint8_t fastled_dither;
  uint16_t leds; uint16_t byte_count;
  uint32_t render_us, quant_us, frame_us, show_us, over, dropped;
  uint8_t bytes[LED_COUNT_VALUE * 3];   // <-- the frame payload, R,G,B per LED
};
```

Device fill (`vpab_capture.cpp`): for each LED `i`, `bytes[i*3+0]=final_bytes[i].r`, `+1=.g`, `+2=.b`, where `final_bytes` is the post-quantise `CRGB` output buffer. **The host reproduces exactly `bytes[i*3 .. i*3+2]` from its own `leds_16 → CRGB` quantise.** The header/metric fields (`render_us`, `quant_us`, …) are timing/telemetry; on host they are either measured wall-clock (`render_us`) or **emitted as `0` / `host` sentinels** and clearly labelled NOT-MEASURED so no one reads host timing as device timing.

---

## 5. File-by-file BoM

### 5.1 CREATE — `scripts/regression-harness/render_replay.py`
Primary deliverable. Mirrors `tempo_replay.py` structure exactly:
- Module docstring (purpose, determinism guarantee, "no hardware/bench").
- `ROOT = Path(__file__).resolve().parents[2]`; `FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"`.
- `ARDUINO_STUB`, `FREERTOS_STUB`, `FASTLED_STUB` string constants (written to a temp `stub/` dir, as tempo_replay does) — OR, if a stub grows beyond ~40 lines, ship it as a committed file under §5.4 and `-I` it. Prefer committed files for FastLED (it's the hard one and wants version review).
- `CPP_REPLAY` driver `main()` (string heredoc, written to `render_replay_main.cpp`): declares the introspection hook `extern "C" void sb_render_host_dump(...)` (§5.3), builds a `RenderParams rp`, `push_render_params(&rp)`, loops over input frames: write `chromagram_smooth[]` (and any future-mode globals) from the frame, set host `millis()`, call `light_mode_bloom_fast(leds_prev)`, quantise `leds_16 → CRGB[]`, emit one frame record (§6).
- `run_replay(compiler="clang++", keep_dir=None, mode="bloom", frames_path=..., seed=...)` — temp-dir lifecycle, builds the compile command (§7), runs compile then binary, returns `{ok, stage, returncode, stdout, stderr, workdir}` (identical contract to tempo_replay).
- `main(argv)` with `--compiler`, `--keep-dir`, `--mode`, `--frames` (input JSON/NDJSON path), `--seed`, `--out` (frame-dump path or stdout), `--json` (machine envelope). Exit `0` on success.
- **Mode registry**: a dict `{mode_id: {fn_name, sources:[...], snapshot_fields:[...]}}` so adding waveform/comet later is data, not new code paths.

### 5.2 CREATE — stub headers (committed, under `scripts/regression-harness/stubs/`)
- `stubs/Arduino.h` — core types, `millis()` (host-clock backed), `min/max/constrain/abs`, no-op `portMUX`. (Generalises tempo_replay's inline stub.)
- `stubs/FastLED.h` — the **curated subset** from §3 #1: `CRGB`, `CHSV`, ported `hsv2rgb_*`, `scale8`/`qadd8`/`qsub8`/`nblend`. Header carries a comment pinning the FastLED version the bodies were copied from.
- (Only if needed) `stubs/freertos_stub.h` — pulled in by shared firmware headers.

### 5.3 CREATE — `-DSB_RENDER_HOST_TEST` introspection hook (mirrors `sb_tempo_debug_dump`)
In `tempo_replay`, `sb_tempo.cpp` compiles `void sb_tempo_debug_dump(...)` only under `-DSB_TEMPO_HOST_TEST`, exposing internal state to the host `main`. Do the same for render: add to the chosen mode source (§5.5) a hook guarded by `#ifdef SB_RENDER_HOST_TEST`:

```c
#ifdef SB_RENDER_HOST_TEST
// Copies the current working buffer out for the host driver. Compiled ONLY on host.
extern "C" void sb_render_host_dump(uint8_t* out_bytes, int led_count);
#endif
```

`sb_render_host_dump` performs the **firmware's** `CRGB16 leds_16[i] → CRGB → out_bytes[i*3..+2]` quantise, so the host uses the device's exact reduction rather than re-implementing it in Python/`main`. Definition lives next to the mode (or in a tiny `render_host_hook.cpp`) and is `#ifdef`-fenced so it can never ship.

### 5.4 CREATE — `scripts/regression-harness/render_host_globals.cpp`
Supplies exactly the `extern` symbols the host link reports missing (e.g. `chromagram_smooth`, `hue_position`, `leds_16` if not pulled from a vendored `globals.cpp`, etc.). Keeps the audio-pipeline `.cpp`s off the host. Start empty; add symbols iteratively as the linker complains (documented in the build checklist §10).

### 5.5 MODIFY — the chosen mode source `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp`
- Add the `#ifdef SB_RENDER_HOST_TEST` introspection hook (§5.3) at the bottom. **No behavioural change to the render path** — the hook is read-only over `leds_16` and `#ifdef`-fenced; on the production build the macro is undefined so the file is byte-identical in behaviour.
- This is the **only** firmware file modified, and only additively under a host-test guard. (If a cleaner home exists, put the hook in a new `render_host_hook.cpp` that `#include`s the mode and reads its buffer — preferred if any reviewer objects to touching a shipping `.cpp`.)

### 5.6 CREATE — input fixtures `scripts/regression-harness/fixtures/`
3–5 canned synthetic-audio fixtures (NDJSON, one frame per line — see §6). Seed them from the real captured scenarios already in `docs/forensics/runtime-evidence/` (`steady-groove`, `kick-drop-heavy`, `sparse-breakdown-build`) by extracting their chromagram-equivalent series, plus 2 synthetic edge cases (silence; single sustained note). These double as the regression corpus for the champion baseline (later doc).

### 5.7 CREATE (later, referenced not built here) — `champion.json`
The frozen regression baseline of frame hashes/metrics. Out of scope for this harness file; named so the driver doc can wire it.

---

## 6. I/O contract

**Input — synthetic AudioDrive frames** (`--frames <path>`, NDJSON; one object per frame, time-ordered):
```json
{"frame": 0, "ms": 0, "chromagram": [c0, c1, ..., c11], "silence": false}
```
- `chromagram`: 12 floats in `[0,1]` (written into `chromagram_smooth[]` before the render call). The **only** audio field bloom needs.
- Future modes extend the object (`spectrogram[NUM_FREQS]`, `vu`, `novelty`, `beat_phase`) per the mode registry (§5.1); unknown fields are ignored by modes that don't read them. This object IS the assessment's `drive[t]` contract.
- `ms`: drives host `millis()` for any dt-based motion (bloom's `shift_multiplier` is constant via `_fast`, but the field is mandatory for motion-memory modes).
- `seed`: top-level `--seed`; any host PRNG (none for bloom) is seeded from it for reproducibility.

**Output — per-frame dump** (`--out <path>` or stdout; NDJSON, one object per rendered frame):
```json
{"frame": 0, "leds": 160, "byte_count": 480, "bytes": "<hex or base64 of LED_COUNT_VALUE*3 uint8>",
 "render_us": 0, "schema": "VPABBytesPayload", "tier": "host"}
```
- `bytes`: the `LED_COUNT_VALUE*3` uint8 triples **in `VPABBytesPayload.bytes` order** (`R,G,B` per LED, LED 0..N-1). Encode as hex or base64 (pick one, document it); a parallel `--raw` mode may emit the bare byte stream for a `vp_diff.py`-compatible binary if the device-tier parser wants identical bytes.
- Telemetry fields (`render_us`, `frame_us`, …): host emits `render_us` = measured wall-clock if cheap, all others `0`, with `"tier":"host"` so no consumer mistakes host timing for device [MEASURED] timing.
- A machine envelope (`--json`) wraps the run: `{ok, frame_count, sha256_of_all_frames, mode, seed, compiler, workdir}` — the `sha256_of_all_frames` is the determinism fingerprint used by acceptance §8 and the champion regression.

**Schema unity:** the `bytes` field is **identical in layout** to what `vpab_capture` dumps on device. A single parser (`vp_capture.py` / `vp_diff.py` family) must read both host and device frames. The host adds `"tier":"host"`; the device path stays as-is.

---

## 7. Compile & run

**Compile (clang++, C++17):**
```
clang++ -std=c++17 -Wall -Wextra \
  -DSB_RENDER_HOST_TEST \
  -I <workdir>/stubs \
  -I <repo>/scripts/regression-harness/stubs \
  -I <FastLED/FixedPoints vendor or library include path> \
  -I <repo>/SPECTRASYNQ_K1_FIRMWARE \
  <repo>/SPECTRASYNQ_K1_FIRMWARE/render_params.cpp \
  <repo>/SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp \
  <vendored CRGB16 / draw_sprite / mirror source(s) as the linker requires> \
  <repo>/scripts/regression-harness/render_host_globals.cpp \
  <workdir>/render_replay_main.cpp \
  -o <workdir>/render_replay
```
- `-DSB_RENDER_HOST_TEST` is the host-only switch — mirrors `-DSB_TEMPO_HOST_TEST`. It MUST be absent from every production/PlatformIO build env (assert this in the build checklist).
- Stub `-I` precedes firmware/library `-I` so `stubs/FastLED.h` and `stubs/Arduino.h` win over the real headers.
- The exact `.cpp` source list is **discovered by the linker** (start minimal, add as undefined-symbol errors appear — §10); the list above is the expected minimum for bloom.

**Run:**
```
render_replay --mode bloom --frames fixtures/steady-groove.ndjson --seed 1 --out -    # frames to stdout
render_replay --mode bloom --frames fixtures/steady-groove.ndjson --seed 1 --json     # machine envelope
```
`render_replay.py` orchestrates compile-then-run and returns the JSON envelope, exactly like `tempo_replay.run_replay`.

---

## 8. Acceptance criteria

A1. **Compiles clean.** `clang++ -std=c++17 -Wall -Wextra` builds with **zero warnings** from the harness/stub code (firmware-source warnings, if any pre-exist, are recorded but not introduced here). Compile failure → `{"ok":false,"stage":"compile"}` with full stderr (tempo_replay contract).

A2. **Deterministic.** Same `--frames` + `--seed` ⇒ **bit-identical** output across runs and machines: the `sha256_of_all_frames` envelope field is stable across ≥3 runs (and across clang versions, modulo any documented FastLED-version pin). No wall-clock, no uninitialised state, no unseeded PRNG in the frame path.

A3. **Byte-layout match.** The `bytes` array is `LED_COUNT_VALUE*3` long, ordered `R,G,B` per LED, and **decodes through the same parser** as a `vpab_capture` device dump (`vp_capture.py`/`vp_diff.py`). Prove by feeding one host frame and one device frame of the same input through the parser and confirming identical structure (values may differ — see R-FASTLED).

A4. **Sane known output.** A hand-checkable fixture yields the expected gross behaviour: e.g. an all-zero chromagram fixture → all-black frames (or the documented idle bloom decay); a single strong chromagram bin → energy localised at bloom's centre-insert pixels with the expected mirror symmetry. Documented as a tiny golden assertion in `render_replay.py` (mirrors tempo_replay's `check()`/`TEMPO_REPLAY_OK` pattern → emit `RENDER_REPLAY_OK frames=N`).

A5. **No production leakage.** Grep proves `SB_RENDER_HOST_TEST` and the `sb_render_host_dump` hook are absent from any PlatformIO build env and are `#ifdef`-fenced. (Developer Instrumentation Boundary, `.claude/CLAUDE.md`.)

---

## 9. Risks & landmines

| ID | Risk | Class | Mitigation |
|---|---|---|---|
| R-FASTLED | FastLED colour-correction, temperature, and the strip's gamma are **NOT modelled on host**. Host frames are pre-correction render maths only. | **[MECHANISM] not [MEASURED]** | Treat host bytes as *relative/regression* truth, never absolute colour truth. Any colour-clarity claim from host output is provisional; only Tier-2 `vpab_capture` (which sees the real post-correction `leds_out`) certifies colour. State this on every host artefact. |
| R-FP | Float-substituting `SQ15x16` silently changes rounding → host diverges from device, breaks determinism parity. | HIGH | VENDOR the real `FixedPoints` type. Never substitute `float`. Unit-check a few `SQ15x16` ops against known values. |
| R-SCALE8 | Re-implemented `scale8`/`hsv2rgb` rounds differently from FastLED → ±1 LSB drift per channel. | HIGH | Copy the **exact** bodies from the pinned FastLED version; pin the version in `stubs/FastLED.h`; unit-test known triples. |
| R-QUANT | Host `CRGB16→CRGB` quantise differs from the firmware's pre-strip reduction → byte mismatch even with identical maths. | HIGH | Perform the quantise **inside** `sb_render_host_dump` using the firmware's own conversion (§5.3), not in Python. |
| R-GLOBAL | Pulling a firmware `.cpp` to satisfy one `extern` drags the audio pipeline / hardware deps onto the host. | MED | Satisfy `extern`s via `render_host_globals.cpp` first; only vendor a real `.cpp` when its maths is genuinely needed (e.g. `draw_sprite`). Record each pulled source + why. |
| R-DITHER | Temporal dither (`dither_step`, `fastled_dither`) is a device-frame-sequence effect; host single-frame dump can't reproduce it. | MED | Host emits `dither_step_value`/`fastled_dither` as documented sentinels; dither fidelity is Tier-2 only. |
| R-LEAK | `-DSB_RENDER_HOST_TEST` or the dump hook leaks into a shippable build. | MED | `#ifdef`-fence everything; A5 grep gate; Developer Instrumentation Boundary compliance. |
| R-DRIVE | Synthetic chromagram fixtures don't represent real music distribution → host ranks the wrong effects. | MED | Seed fixtures from the **real** captured runtime-evidence scenarios (§5.6), not hand-drawn curves; Tier-2 keeps the loop honest. |

---

## 10. Step-by-step build checklist

1. **Read** the design SOT (`docs/architecture/visual-effects-autonomous-loop-assessment.md`) and this file. Confirm scope = Tier-1 host harness only; **no flashing**.
2. **Locate `CRGB16`** — confirm which firmware header/source declares `CRGB16` and its `CRGB16↔CRGB` conversion. Record the path.
3. **Pin FastLED + FixedPoints** — note the exact versions from `platformio.ini` / the installed library dirs. These pin the stub bodies.
4. **Scaffold dirs**: `scripts/regression-harness/stubs/`, `scripts/regression-harness/fixtures/`, `scripts/regression-harness/vendor/` (only if vendoring FixedPoints/FastLED bodies).
5. **Write `stubs/Arduino.h`** (generalise tempo_replay's inline stub: types, host-clock `millis()`, `min/max/constrain/abs`, no-op `portMUX`).
6. **Write `stubs/FastLED.h`** — curated subset (`CRGB`, `CHSV`, ported `hsv2rgb_*`, `scale8`/`qadd8`/`qsub8`/`nblend`), version comment. Unit-test a handful of triples vs known FastLED outputs (R-SCALE8).
7. **Add the `#ifdef SB_RENDER_HOST_TEST` `sb_render_host_dump` hook** to `light_mode_bloom.cpp` (§5.3) — additive, fenced, behaviour-preserving. Run the existing firmware host tests / a no-op compile to confirm the production path is unchanged.
8. **Create `render_host_globals.cpp`** empty; **create `render_replay.py`** with the `tempo_replay.py` skeleton (`ROOT`, stub-write, `CPP_REPLAY` heredoc, `run_replay`, `main`, mode registry seeded with `bloom`).
9. **Iterate the compile** (§7): run, read undefined-symbol/missing-include errors, satisfy each by (a) adding a symbol to `render_host_globals.cpp`, (b) adding a `-I`, or (c) vendoring exactly one firmware `.cpp` whose maths is needed (`draw_sprite`/`mirror`). Record each addition + reason. Loop until it links.
10. **Wire the frame loop** in `CPP_REPLAY`: parse NDJSON frames (or accept them via a host-side feed), write `chromagram_smooth[]` + `millis()`, `push_render_params(&rp)`, call `light_mode_bloom_fast(leds_prev)`, call `sb_render_host_dump()`, emit the §6 output record. Carry `leds_prev` across frames for motion memory.
11. **Author 3–5 fixtures** (§5.6): extract chromagram series from `docs/forensics/runtime-evidence/` scenarios + silence + single-note synthetic.
12. **Acceptance gates**: A1 clean compile; A2 run 3× → identical `sha256_of_all_frames`; A3 host+device frame through the shared parser → identical structure; A4 golden assertions (`RENDER_REPLAY_OK frames=N`); A5 leak grep.
13. **Label everything `[MECHANISM]`** — host frames are render-maths/regression truth, not colour [MEASURED] truth (R-FASTLED). Hand off to the Tier-2 / loop-driver doc.
14. **Changelog** this file and any modified firmware file; do not commit until gates A1–A5 are green and the diff is reviewed (Git discipline, `.claude/CLAUDE.md`).

---

## 11. Recon verified against source — 2026-06-03 (before build)

Every load-bearing claim in §2–§7 was checked against the actual firmware. **Build is GO.** Verified:

- **`light_mode_bloom.cpp`** (118 lines): `void light_mode_bloom(CRGB16* leds_prev_buffer, SQ15x16 shift_multiplier)` + `light_mode_bloom_fast(CRGB16*)` → calls with `SQ15x16(2.0)`. Audio reach-through is **`chromagram_smooth[]` only** (line 31) — confirmed. Also uses `active_render_params()`, `leds_16`, `draw_sprite`, `mirror_image_downwards`, `memset/memcpy`. ✓
- **`CRGB16` = `{ SQ15x16 r,g,b; }`** (`constants.h:157`) — the channels ARE the vendored FixedPoints `SQ15x16`, NOT a separate Q8.8 int. ⇒ R-FP is fully de-risked: **vendor `libraries/FixedPoints` (already in-repo, `file://libraries/FixedPoints` in platformio.ini) and CRGB16 math comes free.** Do not float-substitute.
- **`RenderParams`** at `render_params.h:23`; `build_primary_render_params()`, `push_render_params()`, `active_render_params()`, `active_render_params_depth()` all present. ✓
- **Counts:** `NATIVE_RESOLUTION = 160` (constants.h:23), active `LED_COUNT_VALUE = 160` (config_types.h:52) ⇒ dump is 160×3 = **480 bytes**. ✓
- **FastLED pinned 3.10.3** (platformio.ini) — the `stubs/FastLED.h` subset bodies (`scale8`/`hsv2rgb_*`/`qadd8`/`qsub8`/`nblend`) MUST be copied from **3.10.3**. This remains the single biggest HARD item (R-SCALE8). FixedPoints is the in-repo `libraries/FixedPoints`.

### ⚠ CORRECTION to §2 (bloom's reach-through is WIDER than "chromagram-only minimal")
§2 is right that bloom's **audio** input is `chromagram_smooth[12]` only — but its **colour path pulls a substantial shared subsystem** the §2 table omitted (full read of `light_mode_bloom.cpp`):
- **Palette system (referenced UNCONDITIONALLY at line 27, so required even on the non-palette branch):** `CRGBPalette16`, `cached_gradient_palette()`, `palette_chroma_colour()`, `render_params_palette_owns_colour()`, `render_params_palette_index()`. ⇒ the FastLED subset must include `CRGBPalette16` + palette **interpolation**, not just `scale8`/`hsv2rgb`.
- **Firmware colour helpers:** a custom `hsv(SQ15x16,SQ15x16,SQ15x16) → CRGB16` (NOT FastLED's hsv2rgb directly), `force_saturation(CRGB,…)`, `force_hue(CRGB,…)`.
- **Globals to supply in `render_host_globals.cpp`:** `vp_render_secondary_channel`, `chromatic_mode`, `chroma_val`, `hue_position`, and the `VP_*` flags/consts (`VP_BLOOM_SHIFT_SCALE`, `VP_FIX_BLOOM_DECAY`, `VP_BLOOM_ALPHA`, `VP_BLOOM_FORCE_SATURATION`).
- **RenderParams fields bloom reads:** `MOOD`, `SATURATION`, `SQUARE_ITER`, `CHROMA`.

**Net:** bloom is still a reasonable first target (small, well-understood, motion-memory via `leds_prev_buffer`+`draw_sprite`), but it is NOT a trivial "chromagram→colour" pull — budget for the palette/colour subsystem in the stub/vendor set. The §10 step-9 compile-iterate loop will surface these as undefined symbols; this list pre-loads them so the build isn't blindsided. (A genuinely colour-minimal mode does not obviously exist — the palette/colour helpers are shared across modes.)

### ⚠ CORRECTION to §5.3 / R-QUANT (the quantise is NOT a clean reduction)
The real `CRGB16 → CRGB(uint8)` reduction is in **`led_utilities.h:324–387`** and is **scale → `getInteger()`/`*255` → `apply_gamma8` → incandescent-filter (leakage/`incandescent_lookup`) → temporal dither** — i.e. it BAKES IN gamma + incandescent + dither, exactly the transforms §1/§9 say the host must NOT model. Therefore:

- **A host dump cannot be byte-identical to the device** without pulling gamma/dither/incandescent. §5.3's "use the firmware's own conversion to match device bytes" is **superseded**: `sb_render_host_dump` must perform a **pre-gamma, pre-dither, pre-incandescent `[MECHANISM]` reduction** of `leds_16` (linear `SQ15x16 → uint8`), and the artefact must state plainly that **byte LAYOUT matches `VPABBytesPayload` (invariant I3) but VALUES differ from device by the gamma/dither/incandescent stack** — which is Tier-2 `[MEASURED]` territory by design (consistent with §9 R-FASTLED; corrects §5.3/R-QUANT/I1's "match device" reading). Host determinism (I1: host-vs-host bit-identical) still holds and is what the champion regression uses.
- Net: the host renderer is a faithful model of the **effect maths + motion memory**, deliberately NOT of the optics/colour-correction stack. Use it for relative/regression ranking; certify colour only on-device.

**Build is de-risked and ready.** Remaining real work = the FastLED-3.10.3 curated subset (R-SCALE8) + the compile-iterate symbol loop (§10 step 9). Next session starts at checklist step 4 (scaffold dirs).

---

## 12. Build landed — 2026-06-03 [MECHANISM]

`render_replay` is **built, links, and passes A1–A5 + the R-SCALE8 unit test.** Files (all under `scripts/regression-harness/`, **zero firmware files modified**): `render_replay.py`, `render_host_globals.cpp`, `fastled_stub_test.cpp`, `stubs/{Arduino,FastLED,esp_random,Ticker,FirmwareMSC,USB}.h` + `stubs/freertos/task.h`, `fixtures/gen_fixtures.py` + 6 `.ndjson`. Run: `python3 scripts/regression-harness/render_replay.py --self-test`.

**Gate results:** A1 clean (0 warnings from harness/stub code; 124 pre-existing firmware-source warnings recorded, not introduced) · A2 deterministic (per-fixture sha256 stable ×3) · A3 byte-layout = 480 (`LED_COUNT_VALUE*3`, R,G,B) == `VPABBytesPayload.bytes` · A4 silence→all-black, broadband→bright (max_byte 160), chord→outward propagation + 80/80 mirror-symmetric · A5 no leakage (`SB_RENDER_HOST_TEST`/`sb_render_host_dump` absent from firmware + `platformio.ini`). R-SCALE8: 16-check unit test vs known FastLED values PASS.

**Deviations from this spec (load-bearing — read before extending):**
1. **Host compiler = `g++` (GCC), NOT `clang++`** (§7 assumed clang). The vendored FixedPoints (`SQ15x16`, R-FP must-not-float-substitute) declares `static constexpr SFixed` members of its own incomplete type; Apple clang rejects this, GCC (the firmware's xtensa-gcc lineage) accepts it. `render_replay.py` auto-detects a `g++-NN`/`g++` on PATH. More faithful, not a compromise.
2. **The dump hook lives in the harness `main`, NOT in `light_mode_bloom.cpp`** (supersedes §5.3/§5.5's "modify one mode .cpp"). `sb_render_host_dump` only needs the global `leds_16[]` + `NATIVE_RESOLUTION`, and §11 already established the reduction is a host-owned pre-gamma `[MECHANISM]` step (not the firmware's quantise). ⇒ **zero firmware files touched** — A5 is trivially green and no `/k1-firmware-change-gate` was needed.
3. **`stubs/FastLED.h` is a faithful reimplementation, not a verbatim carve.** 3.10.3 migrated colour types into the `fl::`-namespaced submodule (`lib8tion.h` `#error`s without `led_sysdefs.h`; pulls the platform layer), so a clean carve is impractical (§3 #1 confirmed). The stub copies the real `scale8` (FIXED path), `hsv2rgb_rainbow`, `rgb2hsv_approximate` bodies verbatim and reproduces the canonical `LINEARBLEND` `ColorFromPalette` + 16-stop gradient fill. **R-SCALE8 fix:** the host must use FastLED's `FASTLED_SCALE8_FIXED==1` path (`scale8` with NO inline `+1`); the non-FIXED `+1` form overflows desaturated reds (253+floor→256→0). Caught by the unit test + the single-note fixture.
4. **`-include strings.h`** is prepended to every TU (defines `SB_PASS`/`SB_FAIL` used in `led_utilities.h`) — replicates `SPECTRASYNQ_K1_FIRMWARE.ino`'s include order without modifying any firmware `.cpp`.
5. **Header chain is included whole** (not the §3 trimmed approach): `light_mode_bloom.cpp`→`lightshow_modes.h`→`led_utilities.h`(2133 ln)+`globals.h`. The fidelity-critical helpers (`draw_sprite`, `hsv`, `mirror_image_downwards`, `force_saturation/hue`, palette helpers) are all `inline` in those headers ⇒ real maths for free, no `.cpp` vendoring, no copy-divergence. `render_host_globals.cpp` defines only the `extern`-declared globals (`chromagram_smooth`, `chroma_val`, `hue_position`, `vp_render_secondary_channel`, `CONFIG`); the rest are `inline` in `globals.h`. Compile set: `render_params.cpp` + `Palettes.cpp` + `light_mode_bloom.cpp` + the shim + the generated main. `DEFINE_GRADIENT_PALETTE` must carry `extern` (else the palette arrays get internal linkage and don't link).

**Known limitation (R-DRIVE):** fixtures are SYNTHETIC structured stimuli, not real-music chromagrams (the `docs/forensics/runtime-evidence/` captures are LED-output byte dumps, not audio). Bloom double-squares its input (`bin*bin*share` then the `SQUARE_ITER` loop) so it is dim for sparse notes and bright for dense spectra — faithful, but the musical fixtures sit mid-range. Real-music chromagram fixtures need a `wav→K1-GDFT-chromagram` extractor (Lane A has `wav→novelty` only) — the documented **Tier-1.5** follow-up. Colour VALUES remain `[MECHANISM]` (Tier-2 `vpab_capture` certifies), per §11.

**Next:** PRD §03 (`loop.py` edit→render→score→rank + Captain gate) and §02 (proxy panel + `champion.json` from these baseline shas). The mode registry in `render_replay.py` makes adding waveform/comet "list the extra globals + a fixture column", not a rewrite.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | **MVP-0 BUILT + A1–A5 GREEN** (added §12). render_replay.py + stubs/ + render_host_globals.cpp + fastled_stub_test.cpp + fixtures/ ; zero firmware files modified. Host compiler = g++ (GCC, not clang — FixedPoints constexpr); dump hook in harness main (not bloom.cpp); FastLED.h faithful reimpl (real scale8 FIXED-path + hsv2rgb verbatim + canonical palette), R-SCALE8 unit test 16/16; `-include strings.h`; DEFINE_GRADIENT_PALETTE needs extern. R-DRIVE: synthetic fixtures (real-capture seeding = Tier-1.5). |
| 2026-06-03 | agent:claude-opus | Recon-verified §2–§7 against firmware source before build (added §11): bloom sig, CRGB16={SQ15x16 r,g,b} (R-FP de-risked via in-repo libraries/FixedPoints), RenderParams API, 160 LEDs/480 bytes, FastLED 3.10.3 pin. CORRECTED §2: bloom's AUDIO reach-through is chromagram-only but its COLOUR path pulls the palette subsystem (CRGBPalette16 + interpolation, cached_gradient_palette, palette_chroma_colour, render_params_palette_*), a custom hsv()→CRGB16, force_saturation/force_hue, and globals (vp_render_secondary_channel/chromatic_mode/chroma_val/hue_position + VP_* flags) — bigger stub/vendor surface than "minimal". CORRECTED §5.3/R-QUANT: the CRGB16→CRGB quantise (led_utilities.h:324-387) bakes in gamma+incandescent+dither, so host dump is a pre-gamma [MECHANISM] reduction — byte-LAYOUT-compatible with VPABBytesPayload but value-different from device by design. |
| 2026-06-03 | agent:claude-opus (delegation PRD1-renderreplay) | Created — BUILD SPEC for the Tier-1 host `render_replay` harness. First target `light_mode_bloom` (chromagram-only audio reach-through). Full stub set (Arduino/FreeRTOS STUB, FixedPoints/CRGB16/render_params/constants VENDOR, FastLED curated-subset HARD), file-by-file BoM (CREATE render_replay.py + stubs/ + render_host_globals.cpp + fixtures/ + a -DSB_RENDER_HOST_TEST `sb_render_host_dump` hook mirroring `sb_tempo_debug_dump`; MODIFY light_mode_bloom.cpp additively/fenced), clang++ -std=c++17 compile command, NDJSON I/O contract emitting VPABBytesPayload byte layout, acceptance criteria (clean/deterministic/byte-match/sane/no-leak), risk register (FastLED+LGP+gamma+dither NOT host-modelled → [MECHANISM]), and a 14-step build checklist. Pattern-donor: scripts/regression-harness/tempo_replay.py. |
