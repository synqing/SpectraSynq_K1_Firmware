# Emotiscope Firmware — Architecture Review and Borrow Assessment for SpectraSynq K1

**Date:** 2026-09-02 · **Reviewer:** Claude (Cowork) · **Requested by:** Captain
**Subject:** `github.com/Lixie-Labs/Emotiscope` — branches `1.0`, `1.1`, `1.2`, `2.0` (cloned 2026-09-02, HEAD `d0fef9a` on `main`)
**Judged against:** `SpectraSynq_K1_Firmware` (branch `lane/colourlab-bench`, `36466cd5`) and the DualMCU direction recorded in the 24–28 Aug 2026 rulings.

Evidence labels used throughout: **[FACT]** = read directly from source, cited as `file:line` on the named branch; **[INFERENCE]** = my reading of intent or consequence; **[UNVERIFIED]** = plausible but not checked (usually because it needs hardware or a repo I could not reach). Abbreviations are expanded on first use.

---

## 0. Verdict in one screen

- Emotiscope is not a random neighbour: it is the **same author's successor to Sensory Bridge**, and K1's `NOTICE` records K1 as a GPL-3.0 derivative of Sensory Bridge. K1's own research (`docs/research/2026-06-05_AP_RE-Corpus_Excavation_Brief.md:21`) already names Emotiscope the canonical upstream. You are reviewing your own ancestor's next-of-kin. [FACT]
- Emotiscope is **small and opinionated**: 5.5–7.1k lines of firmware per version vs K1's ~68k. Its virtues are almost all *subtractive* (fewer decisions, fewer knobs, one table, one loop each core). [FACT on line counts; INFERENCE on virtue]
- Only **v1.1.0 ever shipped as a release** (13 May 2024). v1.2 was abandoned with its last commit literally titled "BROKEN VERSION"; v2.0 (the ESP-IDF rewrite) was never released and the repository has had no code commits since 30 Aug 2024. Treat 1.x as field-proven, 2.0 as a design sketch. [FACT]
- **Five things are worth borrowing**, all landing in the **DualMCU (RT1062 + ESP32-S3) greenfield**, none in the frozen legacy S3 oracle:
  1. Rendering the **tempo probability field** (all 96 tempo hypotheses with phase) instead of a single locked BPM — K1 already computes the bank and already flagged this as "the single richest unpublished signal in the firmware".
  2. A **single self-describing control descriptor table** (name, type, UI type, default, value) iterated for load/save/broadcast — one source of truth instead of per-control plumbing.
  3. A **sampling profiler** driven from the idle task (two lines per function, `__COUNTER__` IDs, per-core stacks) to retire the `ENABLE_*` timing-macro scaffolding that now makes up ~15% of K1's main `.ino`.
  4. The **mode taxonomy** ACTIVE / INACTIVE / SYSTEM, with SYSTEM modes bypassing user settings — this is exactly the structure the 28 Aug "ambient mode" ruling needs.
  5. **Time-slicing as a stated design rule** (interlaced bins, round-robin tempo bins, decoupled novelty rate) — not to apply to the S3 now, but to write down as the first lever when the RT1062 budget tightens.
- **Do not borrow**: the Wi-Fi/WebSocket/web-app control plane (BLE-MIDI is ratified), the header-only unity build, unchecked `strcat`/`sprintf` packet building, the embedded TLS private key, unsigned OTA (Over-The-Air update), the 3-strikes reboot-into-setup-mode behaviour, or the big-bang-rewrite pattern that left 2.0 unshipped.

---

## 1. What Emotiscope is (verified)

| Item | Finding | Evidence |
|---|---|---|
| Lineage | "I'm developing a sequel to Sensory Bridge that uses the dual-core ESP32-S3" | `1.0` `README.md` |
| Hardware | ESP32-S3, 128 WS2812-class LEDs on two RMT (Remote Control Transceiver peripheral) channels, SPH0645 I2S microphone, three capacitive touch pads, 4 hardware-version strap pins | `1.0` `led_driver.h:6-10`, `microphone.h:17-19,41`, `touch.h:3-7`, `hardware_version.h:1-4` |
| Timeline | First commit 5 Feb 2024 → `1.0.0` released 6 Apr 2024 → `1.1.0` released 13 May 2024 → `1.2` last commit 13 Jun 2024 ("BROKEN VERSION…") → `2.0` last commit 30 Aug 2024 → `main` README edits to 2 Oct 2024. No releases after 1.1.0. | `git log`, GitHub Releases page |
| Author | Solo developer (Connor Nishijima, @lixielabs); commit cadence 97 → 44 → ~45 → ~45 → 17 → 27 → 21 per month Feb–Aug 2024 | `git log --date=format:%Y-%m` |
| Licence | GPL-3.0 (same as K1) — code reuse is licence-compatible provided attribution is preserved, which K1's `NOTICE` pattern already does | `LICENSE`, K1 `NOTICE` |
| Motive for 2.0 | Port away from Arduino to raw ESP-IDF "to solve #106 [multiple simultaneous app clients] and gain deeper control"; web app rewritten in Godot → WASM, hosted off-device | `2.0` `README.md`, `the_multiplayer_update.md` |

K1 has **already lifted** Emotiscope's I2S slot configuration verbatim (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:374-402`) and K1's tempo tracker is described in-source as "Emotiscope-derived" via LightwaveOS (`audio/k1_tempo.h:6`). [FACT]

---

## 2. The four versions as four architectures

### 2.1 Size and shape

| | 1.0 | 1.1 | 1.2 (abandoned) | 2.0 (unreleased) |
|---|---|---|---|---|
| Framework | Arduino + PlatformIO, C++ | same | same | **ESP-IDF, pure C**, CMake |
| Firmware LOC | 5 548 | ~6 500 | ~7 100 | 7 063 (`main/` only; +28k vendored esp-dsp) |
| Web app LOC | 2 443 (served from device LittleFS) | 2 541 | 1 701 | 0 (moved to Godot/WASM, external repo) |
| Build model | header-only "unity build": every module is a `.h` included once into one `.ino` | same | same | same, into `Emotiscope.c` |
| Audio frame | 12.8 kHz, 64-sample chunks → **200 Hz** | same | **25.6 kHz** experiment + 256-pt FFT | 12.8 kHz, 128-sample chunks → **100 Hz**; half-rate (6.4 kHz) history for FFT |
| Spectral engine | 64 Goertzel bins, semitone spacing from A2, Gaussian window LUT, **interlaced** (half the bins per frame) | + continuous noise floor | + FFT | Goertzel on stride-2 samples + A-weighting; noise floor **disabled** (`goertzel.h:283`) |
| Tempo | 64 bins 32–160 BPM, Goertzel over 50 Hz novelty | **96 bins 48–144 BPM** | same | 96 bins **60–156 BPM**, novelty from FFT flux |
| Control plane | `set\|name\|value` strings over WebSocket (PsychicHTTP), 4 client slots, hand-written per-field NVS load/save | + menu dropdowns | **Self-describing `config_item` struct**, state broadcast over Server-Sent Events | `config_item` + `init_config_item()` factory, **stateless** WS handler on `esp_http_server`, Improv serial Wi-Fi provisioning |
| LED pipeline | float `CRGBF` buffer, custom RMT encoder (FastLED dropped), 4-phase ordered temporal dither | **HDR + tanh tonemap, gamma-last, error-diffusion dither**, white balance | + blur, Perlin | same + phosphor decay; hand-written Xtensa assembly for 4 array ops |
| OTA | HTTPS pull of `firmware.bin` + `littlefs.bin`, progress to client | same | same | **absent** |
| Profiling | lambda wrapper `profile_function([&]{…}, __func__)` counting cycles | same | same | **Sampling profiler**: idle task samples per-core function stacks |

### 2.2 What each version was *for* — first-principles read

- **1.0** answers "can the Sensory Bridge idea run at 200 Hz on two cores with a phone as the knob?" The architecture is the minimum that does that: one loop per core, globals, string commands. [INFERENCE from `EMOTISCOPE_FIRMWARE.ino:75-94`]
- **1.1** answers "how do 8-bit LEDs look like they aren't?" — the whole update is the colour pipeline (HDR, gamma-last, error diffusion, white balance) plus the first self-maintenance features (auto noise floor, auto touch calibration, self-test). [FACT: `extras/CHANGELOG_1.1.md`]
- **1.2** answers "how does the app stop knowing about individual settings?" — the `config_item` table and the `EMO~config|…` broadcast are the firmware publishing its own schema. It also started an FFT experiment at 25.6 kHz. It was abandoned mid-flight. [FACT: `1.2` `types.h`, `wireless.h:148-264`, last commit message]
- **2.0** answers "what breaks if I remove Arduino, FastLED, PsychicHTTP and the client-slot handshake?" — and the answer in the repo is "OTA, the noise floor, pitch detection and shipping". It is a rewrite that removed more than it finished. [FACT: no `esp_ota`/`esp_https_ota` symbol in `2.0/main`; `pitch.h:58-92` body commented out; `goertzel.h:283` zeroes the noise floor]

**Verification note on 2.0's own marketing.** `the_multiplayer_update.md` claims tempo detection "increased 100% to a new range of 60 BPM to 188 BPM" and a Fourier transform "from 1 Hz to 12,800 Hz". The code says `TEMPO_LOW 60`, `NUM_TEMPI 96` → 60–156 BPM (`global_defines.h:29-33`), and the FFT runs on a 6.4 kHz half-rate history with 256 points (`microphone.h:20-26`, `fft.h:1,45-57`) → 0–3.2 kHz at 25 Hz per bin. The 12.8 kHz claim matches the *abandoned 1.2* experiment (`SAMPLE_RATE 12800*2`), not 2.0. Document drifted from code. [FACT]

---

## 3. What deserves praise (ranked by relevance to K1)

### P1 — The tempo engine renders a probability field, not a decision
Emotiscope never "locks" a BPM. It runs a Goertzel bank over a 50 Hz novelty curve (`1.0` `tempo.h:140-192`), extracts **phase per tempo hypothesis** with `atan2` (`:168`), then on the *render* core advances every hypothesis as a phase-locked oscillator scaled by frame delta (`sync_beat_phase`, `:375-403`) and re-syncs it each time that bin is recomputed. Modes then draw *all* hypotheses weighted by contribution: Metronome draws 64 dots (`lightshow_modes/metronome.h:79-122`), Hype sums beats across bins (`hype.h:5-13`), Beat Tunnel in 2.0 draws all 96 (`light_modes/active/beat_tunnel.h:14-31`). Silence is detected as low *contrast* in recent novelty and the whole history is decayed so the bank forgets gracefully (`1.0` `tempo.h:317-342`).

Why this matters for K1: `audio/k1_tempo.h` publishes `winner_bin`, `winner_bpm`, `locked` — a single decision with a PLL (phase-locked loop) flywheel (`AGENTS.md` "Key Architectural Decisions"). K1's own investigation of 10 Jun 2026 concluded the parallel surface is "the single richest unpublished signal in the firmware" (`docs/research/2026-06-10-audio-visual-resolution-investigation.md:55`). Emotiscope is the reference implementation of the thing K1 already decided it wants. [FACT + INFERENCE]

### P2 — Budget is shaped by separating work in time, everywhere
- Half the Goertzel bins per audio frame, alternating (`1.0` `goertzel.h:238-253`; still there in `2.0` `goertzel.h:262-269`).
- One or two tempo bins recomputed per audio frame, round-robin (`1.0` `tempo.h:282-294`; `1.1` `:270-283`; `2.0` `:226-236`).
- Novelty logged at a fixed 50 Hz regardless of audio or render rate (`tempo.h:344-373`).
- Tempo *phase* advanced at render rate using a game-engine `delta` (`gpu_core.h:24-30`), so visual smoothness is decoupled from analysis rate.
- Stats/persistence serviced every 10th CPU iteration (`2.0` `cpu_core.h:21-27`).

This is one idea applied five times: nothing that can be updated slower is updated faster. It is the direct answer to K1's Core-0 budget wall (7 500 µs frame, ~22 µs headroom), which K1 chose to solve with a second MCU instead. Both are valid; only one is free. [FACT on mechanisms; INFERENCE on relevance]

### P3 — Configuration is one table the firmware publishes to a dumb UI
From 1.2 onward every setting is a `config_item {name, pretty_name, type_string, ui_type_string, type, ui_type, value, default_value}` (`2.0` `types.h:157-170`), created through one factory that also loads from NVS (Non-Volatile Storage) with a typed default (`configuration.h:211-235`). Save (`:461-482`), set-by-name (`:503`) and broadcast (`packets.h:56-90`) are each a *single loop* over `sizeof(configuration)/sizeof(config_item)`. The design note that preceded it is explicit: "the web app should be completely unaware of the latest features… Emotiscope itself will instruct the web-app which sliders to show" (`extras/WEB_APP_DESIGN_NOTES.txt`, section marked DONE).

Relevance: K1 has 138 distinct `-D` feature macros in a 93 KB `platformio.ini`, a BLE-MIDI (Bluetooth Low Energy MIDI) control map generated from an external JSON, and a Tab5 deck that is blocked on "registry v2" before it can address tier-2 controls. The Emotiscope pattern is the inverse direction of truth: firmware table → generated JSON → deck, rather than JSON → firmware header. [FACT on both codebases; INFERENCE on direction]

### P4 — A sampling profiler that costs two lines per function
`start_profile(__COUNTER__, __func__)` / `end_profile()` push and pop a compile-time-unique ID on a per-core stack (`2.0` `profiler.h:99-117`); the otherwise-idle `app_main` samples both stacks every tick and increments hit counters (`Emotiscope.c:167-172`, `profiler.h:87-97`). Disabled, both calls compile to nothing. The result is a statistical CPU profile per core with no timers in the hot path.

Contrast: K1's `SPECTRASYNQ_K1_FIRMWARE.ino` is 1 756 lines containing **260 preprocessor conditionals**; the main loop interleaves `ENABLE_VP_PERF_AUDIT`, `ENABLE_TEMPO_STREAM`, `K1_AP_STAGE_ATTRIBUTION_DETAIL` timestamp blocks between every stage (`:872-1000`), on top of the Sensory-Bridge-era `function_id` counter (`system/globals.h:524`). Same goal, ~two orders of magnitude more surface. [FACT]

### P5 — A linear-light float pipeline with a fixed, ordered post-stack
Render order in `1.1`/`2.0` `gpu_core.h`: draw → background → blur → UI overlay → brightness → softness LPF (low-pass filter) → phosphor decay → **tonemap** (`soft_clip_hdr`, linear below 0.75 then `tanh`, `leds.h:709-718`) → warmth → white balance → master brightness → **gamma last** (`x²`, `leds.h:615-619`) → **error-diffusion dither** (`led_driver.h:205-236`) → RMT transmit. Everything before gamma is linear and may exceed 1.0 ("HDR"). Mode transitions are not a separate engine: switching a mode sets `lpf_drag = 1.0` which temporarily drags the per-pixel LPF cutoff to 0.5 Hz (`gpu_core.h:71-89`, `lightshow_modes.h:59`) — a crossfade for free.

Relevance: K1's shipping render is SQ15x16 fixed-point (`visual/channel_effect_state.h`, `k1_lever2_emit.h`) inherited from Sensory Bridge on the S3; the DualMCU RT1062 (Cortex-M7, hardware FPU) removes the reason for fixed point in the *render buffer*, while K1's 16-bit WS2816 emit path already exceeds what Emotiscope's 8-bit dither achieves. Borrow the *ordering discipline*, not the dither. [FACT + INFERENCE]

### P6 — ACTIVE / INACTIVE / SYSTEM mode taxonomy
Introduced in 1.1 (`types.h`, `light_modes.h:36-54`): ACTIVE modes react to music, INACTIVE do not, SYSTEM modes (self-test, presets) are excluded from the user's mode cycle and **bypass brightness/colour settings** (`leds.h:621-629`: `apply_brightness` returns early for SYSTEM). The self-test is itself a mode with a small state machine (`light_modes/system/self_test.h`), triggered from the app or the BOOT button, and returns to the queued previous mode.

Relevance: K1's `AGENTS.md` still records "No on-device animation… no time-only effects" as a key decision; the 28 Aug 2026 ruling that K1 *will* have an ambient non-audio mode overturns it. Emotiscope shows the minimal schema change (one enum field on the mode record) plus the two consumers that need to know (mode cycling, settings bypass). [FACT + INFERENCE]

### P7 — Operational hygiene that is easy to miss
- Debounced persistence: settings must be stable for 3 s before an NVS write (`configuration.h:4,221-237`).
- LED transmission is suppressed while the filesystem is being written (`filesystem_ready` gate, `led_driver.h:223`) — flash writes stall the cache and would corrupt RMT timing.
- Hardware revision read from four strapped GPIOs at boot (`hardware_version.h`).
- CPU die temperature in the stats stream (`2.0` `system.h:5-21`).
- Continuous adaptive noise floor (1.1): a 10-second ring of raw magnitudes sampled at 1 Hz, averaged ×0.9, slow EMA, subtracted — "constant hums… get automatically filtered away… no calibration needed" (`1.1` `goertzel.h:229-270`, changelog). Note it was **turned off in 2.0** (`goertzel.h:283`), so treat as a promising hypothesis, not a proven method.
- The "longevity clause": the app can be loaded from the device's own IP "if the emotiscope.rocks website doesn't work in 20 years" (`WEB_APP_DESIGN_NOTES.txt`). A product-philosophy borrow: local-first control that survives the vendor.

### P8 — Fixing by removal (2.0 handshake)
Issue #106 ("multiplayer access not working… the welcoming handshake… some of the oldest code") was fixed not by improving the slot allocator but by deleting it: the 2.0 WebSocket handler is stateless — parse the frame, answer on the same `req` (`wireless.h:197-216`, `packets.h:223-304`). The 4-slot table, proof-of-life eviction and welcome messages are gone. [FACT]

---

## 4. Red team — what is wrong with Emotiscope (do not import these)

| # | Finding | Evidence | Why it matters to K1 |
|---|---|---|---|
| R1 | Header-only unity build; every module is globals + free functions; no compilation units, no interfaces, no tests | all versions | K1's failed refactors on the legacy monolith show where this ends up at 10× the size |
| R2 | Cross-core sharing "by convention": `magnitudes_locked` is set (`goertzel.h:234,335`) but **never read** by any consumer in 1.0 or 2.0; `waveform_locked`'s only reader is inside a comment block | `grep` across both trees | K1's "AudioSemanticState read-only, no mutex" rule is the disciplined version of the same idea — keep K1's rule, not Emotiscope's flags |
| R3 | `unwrap_phase()` computes `phase - phase` (always 0) → no-op in every version | `1.0` `tempo.h:129-138`, `2.0` `:121-130` | Harmless, but shows no tests would have caught it |
| R4 | VU curve computed for tempo but never used in the Goertzel (`sample` mixed then discarded) | `1.0` `tempo.h:154-157` | Dead data path; the "VU novelty" idea in the changelog is not actually in the tempo transform |
| R5 | `check_update()` falls off the end without `return` on HTTP failure (undefined behaviour) | `1.0` `ota.h:79-108` | — |
| R6 | A TLS **private key** is committed in source (unused, "HTTPS not working yet") | `1.0` `wireless.h:44-48` | Never |
| R7 | OTA pulls from HTTPS but performs **no image signature check**; 2.0 drops OTA entirely | `1.0` `ota.h:12-77` | K1 already has OTA signing (`k1_ota_signing_PUBLIC.pem`) — do not regress |
| R8 | Three failed Wi-Fi reconnects → reboot into setup AP mode | `1.0` `wireless.h:449-460` | Second-order: a router reboot at 3 am turns the product into a captive-portal until someone reprovisions it |
| R9 | 1.2 evicts app clients that miss a 200 ms proof-of-life | `1.2` `wireless.h:350-368` | Wi-Fi jitter on phones routinely exceeds 200 ms; this is a self-inflicted disconnect loop |
| R10 | Packet builders use `strcat`/`sprintf` into fixed buffers with no bounds checks; `load_section_at` has no length guard | `1.2` `wireless.h:148-264`, `2.0` `packets.h:4-10,191-221` | Any borrowed descriptor-broadcast must be bounded |
| R11 | `end_profile(__COUNTER__, __func__)` called with arguments the prototype does not take (C `()` prototype hides it) | `2.0` `packets.h:129,188` | Symptom of no `-Wall -Werror` discipline |
| R12 | Discovery "phone-home" every 10 min posts local IP + version + nickname to the vendor server | `wireless.h` all versions | Product/privacy decision; irrelevant to BLE-MIDI K1 |
| R13 | Marketing text diverged from code (tempo range, FT range — §2.2) | `the_multiplayer_update.md` vs `global_defines.h`, `fft.h` | K1's docs-as-authority culture is the antidote; keep it |
| R14 | The 2.0 rewrite: 6 months, Arduino/FastLED/PsychicHTTP removed, app engine changed, OTA/noise-floor/pitch left behind, never shipped | branch history | **Cautionary tale for the DualMCU greenfield.** The difference in K1's favour is the differential-parity harness and the read-only oracle — Emotiscope had neither |

Lindy note: only 1.1.0 has two years of field exposure. Ideas unique to 2.0 (stateless WS, sampling profiler, A-weighting, FFT novelty, assembly kernels) are untested in the wild. Borrow them as *designs*, not as *evidence*.

---

## 5. Borrow assessment — each candidate against K1 reality

K1 constraints applied to every row: (a) legacy S3 is the read-only parity oracle — nothing lands there; (b) DualMCU RT1062 owns AP (Audio Processing) + VP (Visual Processing) + render; S3 is radio-only over the K1BR SPI protocol which forbids AudioFeaturesV1/pixels; (c) control plane is BLE-MIDI only, Wi-Fi parked; (d) ambient mode is ruled in; (e) 2×160 WS2816 dual-DIN 16-bit emit.

| # | Borrow | Lands in | 1st-order gain | 2nd-order effects (and then what?) | Opportunity cost | Verdict |
|---|---|---|---|---|---|---|
| B1 | **Tempo probability field** — publish `tempi[].magnitude` + `phase` (96 bins) into the RT1062 feature surface; add Emotiscope-class renderers (Metronome / Hype / Beat Tunnel) | RT1062 (AP → VP, same MCU, so **zero K1BR cost** — the S3 never sees it) | Reactivity to polyrhythm and half/double-time ambiguity without a lock decision; visibly "more musical" | New effects will want per-bin phase *quality*; the PLL winner remains available for effects that need one beat. Contract gains a named `kValidTempi` block (the DualMCU contract already has this extension pattern). Parity harness needs a tempo-surface golden | Low — the P4 lane already has a 96-bin bank with SEARCH/CANDIDATE/LOCKED/COAST; this is a publish-and-render change | **Do it**, after K1-DM-020 parity so the oracle is not disturbed |
| B2 | **Time-slicing rule** (interlace bins, round-robin tempo, fixed-rate novelty, render-rate phase advance) | Design rule in DualMCU `AGENTS.md`; code only if budget demands | Reclaims ~50% of spectral compute per frame when needed | Per-bin update rate halves (200→100 Hz in Emotiscope; would be 133→66 Hz per bin on K1); smoothing constants and every downstream numeric shift → **breaks oracle parity** | On RT1062 at 53% budget today, none; on legacy S3 it would invalidate every golden vector | **Write it down, don't apply it** |
| B3 | **Descriptor-table registry** (`config_item` pattern): one iterable table with name / type / UI type / range / default; load, save, clamp, set-by-name, broadcast are single loops | S3 radio side (control authority) + RT1062 config mirror; generate the BLE-MIDI JSON *from* the table | One source of truth for controls; the Tab5 "registry v2" blocker becomes a codegen step; new controls stop needing five edits | Schema broadcast over BLE-MIDI needs SysEx (System Exclusive) or a GATT characteristic — MIDI CC (Control Change) cannot carry names. Tab5's "K1-confirmed values only" rule already matches Emotiscope's broadcast-then-reconcile model. Must be bounded (R10). Does *not* fix the 138 `-D` macros — those are build features, not controls | Medium: touches the frozen 68-control registry and its provenance labelling | **Spike it** on the S3 radio side with a generated JSON and a checksum against the canonical map |
| B4 | **Sampling profiler** (per-core function stack + idle sampler) | DualMCU both MCUs; on RT1062 sample from a low-priority timer or idle hook | Replace `ENABLE_*` timestamp blocks and `function_id` with two lines per function; harness gets a per-core % breakdown per build | Removing the stage timestamps removes µs-exact stage attribution — keep one hard-max frame timer (the 7 500 µs / 2.0 ms ceilings) alongside | Very low | **Do it** in the harness first |
| B5 | **Linear-light float render buffer, gamma-last, fixed post-stack** | RT1062 VP (`core/pixel.h` already exists) | Effects compose additively without clipping; one place for tonemap/warmth/WB/gamma | The WP0 dither truth-table work is on the *emit* side and stays; a float render buffer feeding the 16-bit WS2816 packer changes nothing there. Palette code (K1 palettes superseded chroma) must be linear-light aware | Low if done before effects are ported; high after | **Adopt the stage order as the VP spec**; skip the 8-bit dither |
| B6 | **Mode taxonomy** ACTIVE / INACTIVE / SYSTEM | RT1062 effect framework (`IEffect` has no kind field today — grep) | Ambient mode, self-test and future "presets" get a home; settings bypass for SYSTEM | Director/beat-aware routing must ignore INACTIVE modes; deck UI needs the category to build its mode list | Trivial | **Do it now** in the DualMCU contract |
| B7 | **Hardware-version straps** (2–4 GPIOs read at boot) | K1-CORE PCB (fork B vs C is still open) + both firmwares | Firmware knows carrier/module revision without a build flag | Costs 2–4 pins on a pin-rich RT1062; must be decided before the PCB lane freezes | Negligible | **Recommend to the PCB lane** |
| B8 | **Continuous adaptive noise floor** | Analysis-from-logs only | Could dissolve the noise-cal ceremony that the Calibration Command Policy exists to guard | Emotiscope turned it off in 2.0; K1's static subtraction is disabled after a VP chroma-wipe history; the SSL (silence) learn-window defect is a different mechanism | Unknown until measured | **Hypothesis for the listener-tuning lane; do not wire** |
| B9 | Improv serial Wi-Fi provisioning | — | — | — | — | **Skip** (Wi-Fi parked; web flasher exists) |
| B10 | Device-hosted web app + discovery server + Godot/WASM UI | — | — | — | — | **Skip** (BLE-MIDI + LVGL on Tab5 ratified) |
| B11 | Hand-written Xtensa assembly kernels | — | — | RT1062 is ARM; Xtensa asm is dead weight; CMSIS-DSP is the equivalent | — | **Skip** |
| B12 | ESP-IDF-native instead of Arduino on the S3 side | S3 radio-only firmware | Deeper control of BLE stack; smaller image | Emotiscope's 2.0 shows the migration cost for a 7k LOC project was the whole project. K1's S3 side is *new* code, so no migration — the question is only which framework the radio bridge starts on | Depends on NimBLE/Arduino-BLE choice already in flight | **Neutral** — decide on BLE-stack grounds, not Emotiscope's |

### 5.1 The two contradictions, named (TRIZ)

**C1.** "AP must compute *more* (parallel tempo surface, HF bands at 24 kHz) BUT the audio core's frame budget is *exhausted*." Emotiscope resolves it by **separation in time** (round-robin, interlace). K1 resolved it by **separation in space** (second MCU). Both are legitimate; K1's choice has already been ratified twice. B2 keeps the time lever in the drawer for the day the RT1062 budget is also exhausted.

**C2.** "The control schema must be *stable* (BLE-MIDI CC numbers, Tab5 layout, provenance-labelled registry) BUT *evolving* (tier-2 controls, page-2 listener tuning are not in the registry)." Emotiscope's answer is **separation by scale**: a stable transport with an evolving self-described table broadcast at connect. B3 is that answer transposed to BLE (SysEx or GATT for the schema, CC for the values).

### 5.2 Thought experiments that settled verdicts

- *Port the parallel-tempo render to the legacy S3 today.* The bank is computed (`k1_tempo.cpp`) but not published; the render would run on the VP core, whose budget is unmeasured for 96 motion-blurred dots at 100 FPS across 320 LEDs. Feasible on paper — but any change to the legacy repo breaks its role as oracle. → B1 lands in DualMCU only.
- *Interlace the legacy GDFT to buy headroom.* Recovers roughly 3.7 ms per frame (half of 7.5 ms) at 133 Hz; every magnitude-smoothing constant and the 6-sample average change meaning; the golden vectors die. → B2 is a rule, not a patch.
- *A single developer rewrites everything on a new framework in one branch.* Emotiscope 2.0: nothing shipped, three features lost. K1 DualMCU: same shape of risk, mitigated by the harness that the 24 Aug audit forced into honesty (composition root, post-link gates, build-role/verify-role separation). → R14 stays on the wall.

---

## 6. Systems view — why one is 7k lines and the other 68k

Emotiscope's smallness is not craft alone; it is scope: 128 LEDs, one channel, 7–15 modes, one author, no tests, no agents. K1 carries 77 light-mode symbols and 32 effect directories, dual channels, palettes, a director, BLE, a 10.9k-line serial menu, 4.6k lines of diagnostics and 213 test directories. Most of that is legitimate product surface.

The part that is *not* product surface is the reinforcing loop visible in the memory record: agent incident → new guard or macro (`K1_AUDIO_FREEZE_GUARD_V1`, `K1_BOOTLOOP_GUARD_V1`, startup ratchet, admission gates, calibration command policy) → more conditional compilation → more places for the next agent to misread → next incident. The two Emotiscope borrows that cut this loop at a leverage point are **B3** (one descriptor table removes per-control plumbing as a class) and **B4** (a sampling profiler removes per-stage timing macros as a class). Neither reduces product scope; both reduce the number of *places* scope lives.

---

## 7. Map vs territory — what this review could not verify

- I read every version's source; I **ran none of it**. Frame-rate claims ("450 FPS") are the author's, not mine. [UNVERIFIED]
- The DualMCU repository was not connected this session; its state is taken from the 24–28 Aug 2026 record (harness, contract, K1BR, WP0 dither). Verdicts that reference it assume that record is current. [UNVERIFIED today]
- Whether `IEffect` has a taxonomy field was checked by `grep` for `enum|kind|category` in `effects/framework/IEffect.h` (no hits) — not by reading the effect framework end to end. [FACT on the grep; INFERENCE on absence]
- Perceptual quality of the parallel-tempo render versus K1's PLL lock is an aesthetic judgement I cannot make from source. Emotiscope's product page and video exist; only Captain's eye settles it.
- GitHub issue and release pages were fetched via web (the issues list is blocked by robots.txt; the releases page confirmed 1.1.0 as the last release). Private development after Aug 2024 cannot be excluded. [UNVERIFIED]

Circle of competence: embedded DSP/render architecture and C/C++ code reading are inside; perceptual/aesthetic ranking and the commercial state of Lixie Labs are outside and are labelled as such.

---

## 8. Recommended sequence (means first, smallest reversible step first)

1. **Contract**: add a named `kValidTempi` extension to `AudioFeaturesV1` carrying 96 magnitudes + 96 phases (or a decimated 24) — no consumer yet. Reversible, cheap, unblocks B1 rendering later. Gate: after K1-DM-020 parity.
2. **Harness**: land the sampling profiler (B4) in the DualMCU harness with a per-core % report per build; keep the hard-max frame timers.
3. **Contract**: add the mode `kind` enum (B6) and the SYSTEM-bypass rule to the effect framework spec; register the ambient mode as the first INACTIVE mode.
4. **Spike**: descriptor-table registry (B3) on the S3 radio side; generate the canonical BLE-MIDI JSON from it and diff against the frozen 68-control registry (md5 already exists for the map header). Decide SysEx vs GATT for schema transport on the evidence.
5. **PCB lane**: reserve 2–4 hardware-version strap pins (B7) before K1-CORE fork B/C freezes.
6. **VP spec**: write the render stage order (B5) into the DualMCU VP specification before effects are ported.
7. **Listener lane**: log-based test of the continuous noise floor (B8) against the SSL learn-window defect — analysis only.

Nothing above touches the legacy S3 repository.

---

## 9. Extrapolation — what v2.1 would have been

Added 2026-09-02 at Captain's request. Two further evidence sources were pulled for this section: the 2.0 branch's own commit log (Jun–Aug 2024) and the **Remotiscope** repository (`github.com/Lixie-Labs/Remotiscope`, Godot 3.5.3, 905 lines of GDScript, last commit 30 Aug 2024 — the same day as the last firmware commit). The Lixie Labs organisation shows no repository activity in 2025 or 2026. [FACT]

### 9.1 The trajectory, read from artefacts

- **Each release adds an analysis field and renders it as a field, not a decision.** Spectrum + tempi (1.0) → colour fidelity (1.1) → FFT "harmonic" field (1.2 experiment, retained in 2.0 `fft.h`) → autocorrelation "pitch/wave" field (2.0 `pitch.h`, body still commented out; commits "Added autocorrelation and prototype Pitch Mode", 1–2 Jul 2024). The 1.0 `notes.h` names the next two fields in the sequence: an on-device MLP (multi-layer perceptron) instrument/vocal classifier — a trained 64→36→8→36→64 network already ships unused in `1.0` `neural.h` — and key detection (`1.0` `key_detection.h`, dropped after 1.0). [FACT]
- **Each release removes a dependency.** FastLED → own RMT encoder (1.0); PsychicHTTP + 4-slot handshake → stateless `esp_http_server` (2.0); Arduino → ESP-IDF (2.0); device-hosted web app → Godot app hosted off-device (2.0). [FACT]
- **The control plane drifts from commands to published truth.** `set|name|value` (1.0) → firmware-published schema (1.2 `config_item`) → device broadcasts state, app reconciles (2.0 `EMO~config`; Remotiscope's `SettingGallery` renders whatever the broadcast describes). Remotiscope already has a multi-device list (`Device.gd`) and a nickname screen; it has **no presets screen**. [FACT]
- **Cadence.** "Rapid progress on IDF port!" 23–27 Jun; "Tempo fixed!" on 27 Jun, "Fixed tempo detection" again 5 Jul, "Massive tempo code cleanup" 28 Jul; a 12-day gap in July; "(Current 2.0 changes stashed for later)" 20 Aug; a final burst on screen streaming and nicknames 24–30 Aug; then nothing. [FACT]

### 9.2 v2.1, conditional on it existing

| Confidence | Feature | Why |
|---|---|---|
| High | **OTA restored** on IDF (`esp_https_ota`, two-partition pattern from 1.x) | 2.0 has no update path; nothing can ship without it |
| High | **"The Presets Update" finally lands** — a named snapshot of the `config_item` table | Promised in the 1.1 changelog; stubbed as a SYSTEM mode in 1.1/1.2/2.0 (`light_modes/system/presets.h`); absent from Remotiscope; the descriptor table makes it nearly free |
| High | Pitch/Wave mode un-commented; "FFT" promoted to Harmonic; Rhythm Breeze built from tempi + the `draw_sprite` smear already in Beat Tunnel | All three are named in `the_multiplayer_update.md`; two have partial code |
| High | Noise floor re-enabled or replaced | `goertzel.h:283` zeroes it — a placeholder, not a decision; A-weighting was the partial substitute |
| Medium | Sample rate back to 25.6 kHz so the FFT reaches cymbals | 1.2 ran there; the 2.0 roadmap text still describes that build; cymbals are his stated reason for FFT novelty |
| Medium | Colour modes beyond Gradient/Perlin (`color_mode_t` enum exists); novelty-driven auto-colour; "sub-frame audio" interpolation between 100 Hz audio frames at ~450 FPS render | `types.h:123-126`; `1.0` `notes.h` "Sub-frame audio" |
| Medium | Multi-unit awareness — identify-flash or cross-unit sync | Device list exists in the app; design notes describe "swipe left/right between all units" |
| Low | Small MLP on the spectrogram for vocal presence / instrument class, rendered as colour | The 1.0 plan written before he had the compute; 2.0's assembly kernels and sampling profiler are the groundwork you lay for exactly this |
| Low | Key detection revived from the chromagram | Existed in 1.0, dropped, never mentioned again |

### 9.3 Steel-man: "there is no 2.1 — the trajectory ends at 2.0"

Strongest form: a solo developer; a product sold on Tindie; a rewrite that deleted the update path; a roadmap written six weeks into the port with half its items still absent from code; a commit titled "stashed for later"; twenty-four months of silence. This is the textbook end-state of a big-bang rewrite, and I judge it the **more probable** outcome. What is true in it: the base rate, and the fact that the roadmap describes a build (25.6 kHz, 60–188 BPM) the branch does not contain — his own map was ahead of his territory. What it does not defeat: the *direction* is unambiguous from artefacts even if no release follows. The honest framing is therefore "what 2.1 would have been", not "will be".

### 9.4 Red team on the extrapolation

- Aesthetic cuts are unpredictable: key detection, neurons, plot and waveform modes were dropped without comment. Expect a real 2.1 to remove two of the features in §9.2.
- Tempo semantics were still moving ("fixed" three times; novelty source changed from spectrogram flux to FFT flux). A 2.1 could revert.
- Godot 3.5 HTML export is a dead-end; a real 2.1 faces the Godot 4 migration he explicitly deferred.
- Nothing here is checked with the author; the issue tracker is robots-blocked to this session. [UNVERIFIED]

---

## 10. Extraction and translation for K1 — what, where, how

The trajectory in §9 converges on the layers Captain has already endorsed for the Music Intelligence programme (deterministic fields → musical state → a small learned layer → render) and on the Tab5 direction (deck renders what the K1 publishes). Emotiscope reached those conclusions on an S3 and ran out of budget and time; the DualMCU RT1062 removes the budget constraint. What follows is the extraction, sorted by what transfers cleanly.

### 10.1 Semantics to adopt as written principles (zero code, high leverage)

| Principle | Emotiscope form | K1 translation |
|---|---|---|
| **Fields, not decisions** | 96 tempi with phase drawn simultaneously; no "locked BPM" | `AudioFeaturesV1` publishes distributions (tempi magnitude + phase, chroma, per-band onset, later a periodicity field). The Smart Director remains *one consumer* of the field, never the only path from AP to VP |
| **Firmware publishes truth; the UI is a renderer** | `config_item` table → `EMO~config` broadcast → Remotiscope builds its gallery from it | Tab5 builds sheets from a K1-broadcast descriptor set; "K1-confirmed values only" is already the ratified rule — this makes the schema itself K1-confirmed |
| **Presets are name-keyed snapshots of the table** | promised 1.1, stubbed 1.1–2.0, never shipped | K1's ten preset slots (2026-06-06) should be checked: if they store values by *offset* they break when a control is added; name-keyed snapshots survive schema evolution |
| **One removal per release** | FastLED, PsychicHTTP, Arduino, the handshake | Name the removals for DualMCU up front: the 10.9k-line serial menu becomes generated from the descriptor table; `ENABLE_*` timing macros become the sampling profiler; `function_id` retires |
| **Budget is shaped in time before it is bought in silicon** | interlace, round-robin, fixed-rate novelty | Written rule in the DualMCU `AGENTS.md`; the first lever when RT1062 headroom tightens |
| **Restore the update path before adding fields** | 2.0 did the opposite and never shipped | DualMCU keeps the signed OTA + web flasher as a gate on every lane, not a later item |

### 10.2 Mechanisms to port (code, with a home)

| # | Mechanism | Source | Lands in | How |
|---|---|---|---|---|
| X1 | **Tempo field publish** — 96 × (magnitude, phase) into the feature surface as a named `kValidTempi` extension | `2.0` `tempo.h:152-259, 371-408` | RT1062 AP → VP (same MCU; never crosses K1BR) | Decimate to 24 or 48 bins if the contract budget objects; keep the PLL winner as a separate field |
| X2 | **Three field-renderers as reference effects** — Metronome (dots per hypothesis weighted by contribution), Hype (beat sum), Beat Tunnel (phase-gated smear) | `1.0` `metronome.h`, `hype.h`; `2.0` `beat_tunnel.h` | DualMCU effect framework, INACTIVE→ACTIVE taxonomy in place first | Port as `k1_` effects with provenance comments (the `k1_tempo.h` precedent); they double as visual proof that X1 is wired |
| X3 | **Silence as novelty *contrast*** over a 2.56 s window, with history decay on silence | `1.0` `tempo.h:317-342`; `2.0` `:284-314` | Listener-tuning lane, analysis-from-logs first | A third candidate signal for the conjunctive silence break (alongside crest `pky` and the SSL level line); it is level-invariant by construction, which is exactly what the crest threshold lacked |
| X4 | **Periodicity (autocorrelation) field** — 256-lag `dsps_corr_f32` over band-passed audio, rendered as a lag image | `2.0` `pitch.h:58-92` (commented out), `light_modes/active/pitch.h` | RT1062, CMSIS-DSP `arm_correlate_f32` | Responds to vocals and melody, ignores cymbals — a direct L1→L3 field for the MI programme; cheap on an M7 |
| X5 | **Sampling profiler** | `2.0` `profiler.h:87-117`, `Emotiscope.c:167-172` | DualMCU harness first, then both firmwares | On RT1062 sample from a low-priority timer; keep the two hard-max frame timers |
| X6 | **Descriptor-table registry** with one loop each for load / save / clamp / set-by-name / broadcast | `2.0` `types.h:157-170`, `configuration.h:211-235,461-503`, `packets.h:56-90` | S3 radio side (control authority), mirrored on RT1062 | Bounded buffers (R10); generate the canonical BLE-MIDI JSON from the table and diff it against the frozen 68-control registry (md5 already exists) |
| X7 | **Screen-preview streaming** — decimated frame, 6 bits per channel, on request | `2.0` `preview.h`, `packets.h:132-160` | Tab5 over BLE, *if* bandwidth allows | 2 × 40 px × 3 ch × 6 bit ≈ 180 B/frame; at 5 fps that is ~7 kbit/s — feasible over a GATT notify characteristic, marginal over BLE-MIDI SysEx. Value: the deck shows the K1 without line of sight. Prove bandwidth before designing UI for it |
| X8 | **Hardware-version straps**, self-test as a SYSTEM mode, debounced NVS writes, flash-write gating of LED emit | `1.0` `hardware_version.h`; `1.1` `self_test.h`; `configuration.h:221-237`; `led_driver.h:223` | PCB lane (straps); RT1062 (rest) | Straps must be reserved before K1-CORE fork B/C freezes |
| X9 | **MLP-on-spectrogram** rendered as colour ("Neurons" mode) | `1.0` `neural.h`, `notes.h` "Live Instrument Classifier" | EdgeAI-Lab repo (L2/L4), not the firmware yet | Emotiscope's contribution is the rendering idea and the training pipeline sketch (OpenMIC-2018 → ported Goertzel engine on host → 200 FPS frames → MLP), which mirrors K1's replay-harness approach |

### 10.3 Translation rules (how to bring anything across safely)

1. **DualMCU only.** The legacy S3 repository is the parity oracle; nothing from this review touches it.
2. **Emotiscope as a second oracle.** `2.0` `tempo.h` and `goertzel.h` are plain C with roughly eight trivial platform symbols to shim (`dsps_memset_aes3`, `dsps_memcpy_aes3`, `dsps_mulc_f32_ae32`, `esp_timer_get_time`, `start/end_profile`, `clip_float`, `window_lookup`, `shift_array_left`); esp-dsp itself ships ANSI fallbacks. A host-compiled Emotiscope tempo engine gives the differential harness golden vectors for the *field* behaviour (X1) that the legacy K1 oracle cannot provide, because K1 never published the field. [FACT on symbol count; INFERENCE on feasibility]
3. **Every borrowed algorithm enters through the harness**, with a golden vector, before it enters an effect.
4. **Provenance in code and in `NOTICE`.** GPL-3.0 → GPL-3.0; Emotiscope-derived files carry the `k1_` prefix and a header comment naming the source branch and lines, as `k1_tempo.h` already does. Ideas need no attribution; copied code does.
5. **Sequence by reversibility.** Contract extension (X1) and taxonomy enum are reversible and cheap — first. Effects (X2) and profiler (X5) next. Registry (X6) touches a frozen artefact — spike behind a diff gate. Streaming (X7) waits on a bandwidth measurement. X9 stays in the research repo.

### 10.4 Do not translate

Godot/WASM app (LVGL on Tab5 is ratified), the Wi-Fi/WebSocket/discovery plane (BLE-MIDI is ratified), the unity build, unbounded string packet building, unsigned OTA, the 3-strikes reboot-into-setup behaviour, the 200 ms client eviction, Xtensa assembly kernels (RT1062 is ARM — CMSIS-DSP is the equivalent).

---

## Appendix A — Files read (all four branches)

`1.0/src`: `EMOTISCOPE_FIRMWARE.ino`, `cpu_core.h`, `gpu_core.h`, `web_core.h`, `system.h`, `global_defines.h`, `types.h`, `microphone.h`, `goertzel.h`, `vu.h`, `tempo.h`, `leds.h`, `led_driver.h`, `configuration.h`, `sliders.h`, `toggles.h`, `menu_toggles.h`, `filesystem.h`, `commands.h`, `wireless.h`, `profiler.h`, `utilities.h`, `lightshow_modes.h` + `metronome.h`, `bloom.h`, `spectrum.h`, `hype.h`, `ota.h`, `touch.h`, `ui.h`, `standby.h`, `screensaver.h`, `key_detection.h`, `neural.h`, `hardware_version.h`, `notes.h`; `extras/WEB_APP_DESIGN_NOTES.txt`.
`1.1/src`: `global_defines.h`, `types.h`, `light_modes.h`, `EMOTISCOPE_FIRMWARE.ino`, `tempo.h`, `gpu_core.h`, `led_driver.h`, `leds.h` (tonemap/gamma/auto-colour/master), `goertzel.h` (noise floor), `light_modes/system/self_test.h`; `extras/CHANGELOG_1.1.md`.
`1.2/src`: `configuration.h`, `wireless.h`, `microphone.h` (diff), `extras/emotiscope_state_binary_layout.txt`; diffstats 1.0→1.1→1.2 including `data/js`.
`2.0/main`: `Emotiscope.c`, `global_defines.h`, `types.h`, `system.h`, `cpu_core.h`, `gpu_core.h`, `goertzel.h`, `fft.h`, `microphone.h`, `tempo.h`, `profiler.h`, `asm.h`, `dsps_mul_f32_ae32_fast.S`, `configuration.h`, `packets.h`, `wireless.h`, `serial.h` (structure + `check_serial`), `leds.h` (index + softness/phosphor/clamp), `led_driver.h` (quantise/transmit), `touch.h` (auto-threshold), `utilities.h` (LUTs), `light_modes.h`, `light_modes/active/spectrum.h`, `beat_tunnel.h`, `preview.h`, `testing.h`, `pitch.h`; `README.md`, `the_multiplayer_update.md`.
K1: `NOTICE`, `AGENTS.md` (architecture section), `SPECTRASYNQ_K1_FIRMWARE.ino:653-1000`, module line counts, `control/`, `visual/`, `persistence/`, `audio/k1_tempo.h` (struct surface), `system/config_types.h` (LED counts), `platformio.ini` macro census.

## Appendix B — Sources

- Emotiscope repository: https://github.com/Lixie-Labs/Emotiscope (branches `1.0`, `1.1`, `1.2`, `2.0`, `main`)
- Releases: https://github.com/Lixie-Labs/Emotiscope/releases (1.1.0 latest, 13 May 2024)
- Issue #106 "Multiplayer access not working": https://github.com/Lixie-Labs/Emotiscope/issues/106
- Sensory Bridge (common ancestor): https://github.com/connornishijima/SensoryBridge
- Remotiscope (Godot app, §9): https://github.com/Lixie-Labs/Remotiscope
- Lixie Labs organisation (activity check, §9): https://github.com/Lixie-Labs

---

## §11 Corrections from execution — 3 September 2026

§4 ranked the tempo probability field as the first thing to borrow. Building a host oracle from the pinned 2.0 source (`92e14bdd`) put numbers behind that recommendation and changed its shape. Borrow the *idea*; do not borrow the implementation. Four defects, all verified in source or in the oracle's own output.

**D1 — `tempo.h:165` reads out of bounds on every bin, every call.**
`uint16_t index = ((NOVELTY_HISTORY_LENGTH - 1) - block_size) + i;`
`init_num_tempi_float_lookup()` sets `progress = i/96`, so `tempo = 96·(i/96) + 60 = i + 60` — tempi are exactly 1 BPM apart, 60–155. Neighbour spacing is therefore 1/60 Hz, so `block_size = 50 / (0.016667 × 0.5) = 6000`, clamped to 1024 by `tempo.h:94` for **every** bin. At `i = 0` the index is `1023 − 1024 = −1`, and because `index` is unsigned it wraps to 65535 — a read roughly 256 kB past a 1024-float array, once per bin per call, in shipped firmware. The window also excludes the newest novelty sample. Correct expression: `(NOVELTY_HISTORY_LENGTH - block_size) + i`.

**D2 — the 96-bin bank carries about 34 independent values.**
`k = (int)(0.5 + block_size · target_tempo_hz / NOVELTY_LOG_HZ)` with `block_size = 1024` and `NOVELTY_LOG_HZ = 50` yields **34 distinct `k` across the 96 bins**, mostly in triplets. A 1024-sample Goertzel at 50 Hz resolves 50/1024 = 0.0488 Hz = **2.93 BPM**, against 1 BPM bin spacing — the bank is roughly 3× oversampled. Bins 59, 60 and 61 all take `k = 41`, so 119, 120 and 121 BPM are not separable. Confirmed in the oracle's output: bins 60 and 61 are bit-identical, 62 and 63 are bit-identical, and only 66 distinct magnitudes appear across 96 bins. A 120 BPM stimulus peaks at bin 59, decided by round-robin update order and the 0.995 smoothing rather than by frequency.
*For K1:* size the tempo bank to the resolution the history length actually supports, or lengthen the history. Do not publish 96 bins that carry 34 values and call it a probability distribution.

**D3 — `tempo_confidence` is unbounded and maximal on silence.**
`tempo_confidence = max_contribution / tempi_power_sum` (`tempo.h:405`) with `max_contribution` floored at `1e-7` and `tempi_power_sum` at `1e-8`. With no tempo energy it reads exactly **10.0** — its largest value precisely when there is no signal.

**D4 — `silence_level` reports full silence under strong excitation.**
Driven with a 1024-tick 120 BPM novelty train, `silence_level` is **1.0 on every record**, including ticks where 95 of 96 magnitudes are non-zero and confidence is 0.33. The detector (`tempo.h:288-311`) measures max−min contrast over the last 128 novelty samples after `fminf(0.5, x·novelty_scale_factor)·2` and `sqrt`; with autoranged scaling that window flattens and reports silence.

**Consequence for the borrow list.** §4's "publish the field, let the renderer read it" stands as an architectural principle — fields not decisions. Emotiscope's own field is not a usable reference implementation and is not a usable oracle. K1 does not need one: a synthetic periodic novelty train at a known BPM is ground truth by construction, and K1's bank can be asserted against it directly.

Together with the no-op `unwrap_phase()` recorded in §5, that is five defects in a tempo path that only ever shipped in 1.1.0.
