# Sensory Bridge Firmware — Architecture Review, Lineage Map and Extraction for SpectraSynq K1

**Date:** 2026-09-02 · **Reviewer:** Claude (Cowork) · **Requested by:** Captain
**Subject:** `github.com/connornishijima/SensoryBridge` — tags `1.0.0` → `4.1.1` (cloned 2026-09-02; `main` HEAD `5f32926`, 96 commits)
**Companion:** `2026-09-02-emotiscope-architecture-review.md` (the same author's successor project)
**Judged against:** `SpectraSynq_K1_Firmware` (`lane/colourlab-bench`, `36466cd5`) and the DualMCU rulings of 24–28 Aug 2026.

Evidence labels: **[FACT]** read from source, cited `file:line` on the named tag; **[INFERENCE]** my reading; **[UNVERIFIED]** not checked. Abbreviations expanded on first use.

---

## 0. Verdict in one screen

- **K1 is Sensory Bridge 4.1.1 plus sixty thousand lines.** K1's `FIRMWARE_VERSION` is `40103` — it continues Sensory Bridge's own `MmmPP` numbering from `40101` — and its heritage files (`GDFT.h`, `i2s_audio.h`, `led_utilities.h`, `bridge_fs.h`, `knobs.h`, `buttons.h`, `presets.h`, `serial_menu`) are the 4.1.1 files grown 3–7×. [FACT]
- **The same author answered the same ancestor twice.** Sensory Bridge → Emotiscope was a from-scratch rewrite that kept 6–7k lines. Sensory Bridge → K1 was accretion to ~68k. The DualMCU greenfield is K1's Emotiscope moment; this report is about doing it with K1's harness discipline and Emotiscope's economy.
- **Three inherited defects in K1 trace to specific Sensory Bridge lines:** the noise-calibration poisoning path (`SWEET_SPOT_MIN_LEVEL` learned from a raw peak mid-calibration), the 10-second sweet-spot silence gate, and the 12.8 kHz / 96-sample "build contract" — which is a January 2023 ESP32-S2 compute compromise (3.0.0 ran 24.4 kHz), not a musical decision. K1's planned move to 24 kHz is a return to Sensory Bridge 3.0.0's rate. [FACT]
- **What Sensory Bridge had that K1 dropped and may want back:** Sensory Sync (ESP-NOW multi-unit settings/noise-cal propagation), USB mass-storage drag-and-drop firmware updates, and the two-frame look-ahead flicker suppressor. What K1 carries dead from the ancestor: `audio_transfer.h` (an acoustic configuration modem, never wired in any release), an unused A-weighting table, a dead interlace flag, and the `function_id` profiler.
- **Licence fact (not legal advice):** every Sensory Bridge release through 4.1.0 shipped under MIT; the `LICENSE` file changed to GPL-3.0 on 2024-02-08 and 4.1.1 (2024-03-21) carries it, while the README still says MIT. K1 forked 4.1.1 and treats itself as GPL-3.0, which is consistent. [FACT]

---

## 1. What Sensory Bridge is (verified)

| Item | Finding | Evidence |
|---|---|---|
| Hardware | ESP32-S2 (single core), SPH0645 I2S microphone, 128-LED "Mini Mast" or external WS2812B/APA102, three knobs (PHOTONS, CHROMA, MOOD), two buttons (NOISE, MODE), three "Sweet Spot" level LEDs | `4.1.1` `constants.h:69-87`; README |
| Timeline | `1.0.0` 2022-09-15 → `1.1.0` 2022-09-22 → `2.0.0` 2022-11-16 → `3.0.0` 2023-01-25 (five betas in nine days) → `3.1.0` 2023-01-29 → `3.2.0` 2023-05-08 → `4.0.0` 2023-07-11 → `4.1.0` 2023-10-02 → `4.1.1` 2024-03-21 | `git tag` dates |
| Development style | 96 commits in 21 months; major versions arrive as single "Initial Upload" commits (4.0.0 is one commit). The repository is a release mirror, not a working log — trajectory has to be read from tags, release notes and the `extras/misc` experiments | `git log 3.2.0..4.0.0` |
| Successor | Emotiscope (ESP32-S3, Feb 2024 →) — its 1.0 README: "a sequel to Sensory Bridge" | companion report |
| Licence | MIT through 4.1.0; GPL-3.0 from commit `073398a` (2024-02-08); README unchanged | `git show <tag>:LICENSE` |

---

## 2. The versions as architectures

### 2.1 Shape by version

| | 1.0.0 / 1.1.0 | 2.0.0 | 3.0.0 | 3.1.0 | 3.2.0 | 4.0.0 | 4.1.x |
|---|---|---|---|---|---|---|---|
| Firmware LOC | 2 580 / 2 650 | 2 148 (+FFT lib 827) | 4 063 | 4 247 | 5 504 | 6 471 | 6 506 |
| Spectral engine | **256-pt FFT** @ 18.75 kHz, bins 6–127 warped by `pos²` to a pseudo-log scale | same, `fft_parser.h` | **GDFT**: 64 Goertzel bins at semitone spacing 110–4186 Hz, Q14 fixed-point, per-bin block size `fs/(2·Δf_neighbour)` capped at 2000 | + Hann window, **interlacing on the 16 lowest bins** | same | audio engine rewrite: float normalisation, `sqrt` magnitudes, MOOD-driven LPF; interlace flag left in but **unused** | same |
| Sample rate / chunk | 18 750 / 256 | 18 750 / 256 | **24 400 / 256** (~95 Hz) | **12 200 / 128** (~95 Hz) | 12 200 / 128 | **12 800 / 96** (133 Hz) | 12 800 / 96 |
| Loop structure | single `loop()`; mode `if` chain | `function_id` stage markers; `check_knobs → buttons → settings → serial → p2p → audio → fft → noise_cal → leds → sweet_spot` | same skeleton | **LED thread** (`xTaskCreatePinnedToCore`, "200 FPS") on a single-core part — time-slicing, not a second core | same | same | same; `vTaskDelay(1)` added in 4.1.1 to stop lock-ups |
| Colour pipeline | FastLED `CRGB`/`CHSV`, `gamma = v²` | same | same + transitions, standby dimming | + temporal dithering (4-phase table), MAX_CURRENT | + incandescent LUT, Perlin Kaleidoscope, auto colour shift | **`CRGB16` = three `SQ15x16` fixed-point channels**, custom dither, base coat, bulb cover, prism | + dual WS2812B chains ("MicroDose") |
| Control plane | knobs + 2 buttons; serial debug | + **Sensory Sync** (ESP-NOW broadcast of settings / noise-cal / identify; main vs secondary) + `serial_menu.h` | **WebSerial settings tool** (settings.sensorybridge.rocks), 30+ `key=value` UART commands, `sbs((name=csv))` live streams, **USB MSC drag-and-drop firmware** | + sensitivity, max current | + presets by name | + update notifications via the web tool | same |
| Persistence | LittleFS: config + noise cal + DC offset files, 3 s debounce | `bridge_fs.h`; raw `memcpy` of `CONFIG` struct to a 512-byte blob | file name carries the firmware version → new version starts from defaults | same | same | same | same |

### 2.2 The trajectory in one paragraph

Sensory Bridge spent 2022 as an FFT visualiser with knobs; in a 71-day burst (Nov 2022 – Jan 2023) it replaced the FFT with the Goertzel bank, grew a serial/WebSerial control plane, USB drag-and-drop updates, silence detection and mode transitions; 3.1 bought frame rate by halving the sample rate and interlacing; 3.2 and 4.0 were colour-fidelity releases (incandescent LUT, fixed-point 16-bit colour, dithering, base coat) explicitly described as "polish before planned WiFi remote control"; 4.1 added dual LED chains and then stability fixes. The planned WiFi remote control never landed in Sensory Bridge — it became Emotiscope on the S3, where the author also abandoned fixed point for float and Arduino for IDF. [FACT on the artefacts; the "became Emotiscope" link is the author's own statement in the Emotiscope 1.0 README]

Three unshipped experiments sit in `extras/misc`: `bpm.h` (autocorrelation of a spectral-velocity history, 76 lines), `onsets.h` (onset-grid correlation across 60–200 BPM, 70 lines) and `audio_transfer.html` (the browser half of the acoustic modem). These are the seed of Emotiscope's tempo bank and of K1's `k1_tempo`. [FACT]

---

## 3. Lineage map — what K1 inherited, changed, dropped, or carries dead

Measured against `4.1.1`. K1 paths are under `SPECTRASYNQ_K1_FIRMWARE/`.

| Sensory Bridge 4.1.1 | K1 today | Status |
|---|---|---|
| `SENSORY_BRIDGE_FIRMWARE.ino` 230 lines; `loop()` with `function_id` stages; `led_thread` on core 1 | `.ino` 1 756 lines; identical stage order (`check_knobs → check_buttons → check_settings → check_serial → acquire_sample_chunk → run_sweet_spot → calculate_vu → process_GDFT → …`); `led_thread` pinned to `K1_LED_TASK_CORE`; 260 preprocessor conditionals interleaved | **Kept skeleton, buried in instrumentation** |
| `GDFT.h` 242 lines, Q14 Goertzel, 64 bins, `interlace_flip` computed but unused (`:65-66`) | `GDFT.h` is a 73-line shim; the loop lives in `audio/k1_gdft_core.cpp` (int64 promotion); `NUM_FREQS 80` (`system/config_types.h:121`); `interlace_flip` still present in 2 files; header comment still says "64 instances" | **Changed (extended, promoted); dead flag and stale comment carried** |
| `system.h:238-240` block size `fs/(2·Δf)` cap 2000 | same rule (K1 record: "block_size formula fs/(Δf_neighbor·2) … cap 2000 … neighbouring bins are NOT independent") | **Kept unchanged** — Emotiscope moved to `fs/(4·Δf)` cap 4095 |
| `constants.h:4` `DEFAULT_SAMPLE_RATE 12800`, chunk 96 (`globals.h` defaults) | `DEFAULT_SAMPLE_RATE 12800`, `DEFAULT_SAMPLES_PER_CHUNK 96` (`config_types.h:37,41`) | **Kept** — the "12.8 kHz build contract" is this line |
| `i2s_audio.h:102-104` `SWEET_SPOT_MIN_LEVEL = peak×1.10` learned during frames 64–192 of noise cal, no admission gate | `SWEET_SPOT_MIN_LEVEL` in 16 files; Calibration Command Policy + Phase-B admission gates added *around* it after the 281→745 poisoning | **Kept the flaw, fenced it** |
| `i2s_audio.h:158-159` silence = 10 s below sweet-spot-min ×1.10 | SSL (sweet-spot level) fraction gates, `K1_SILENCE_RMS_ENTER/EXIT`, crest (`pky`) gate — all descendants | **Kept concept, elaborated** |
| `i2s_audio.h:190-236` RMS VU with `VU_LEVEL_FLOOR` learned ×1.5 in noise cal | `calculate_vu()` kept | Kept |
| `GDFT.h:141` noise subtraction ×1.5; `GDFT.h:149` MOOD → LPF cutoff `1 + 10·MOOD` | K1: static per-bin subtraction *disabled* after a chroma-wipe incident; mood kept as Tier-1 control | Changed |
| `led_utilities.h` 1 423 lines, `CRGB16`/`SQ15x16`, `quantize_color` 4-phase dither, incandescent, base coat, bulb cover, prism, transition fade, UI needle graphs | 3 087 lines; same primitives; Lever-2 16-bit WS2816 emit added; K1 record says chroma/base coat/incandescent/dither controls are never used by Captain | **Kept and doubled; half the knobs are ratified dead** |
| `lightshow_modes.h` 6 modes | 77 `light_mode_*` symbols, 32 effect directories | Extended ~10× |
| `serial_menu.h` 1 314 lines, 32 `key=value` commands, `ack()`/`bad_command()`, `sbs((` streams | `serial/serial_menu.cpp` 4 576 lines + 10.9k-line `serial/` directory; `sbs((` in 4 files | **Kept the hand-written parser pattern; it scaled linearly with controls** |
| `bridge_fs.h:67` raw `memcpy(&CONFIG)` blob; version-named file; `lock_leds()` around writes | `persistence/bridge_fs.h` 735 lines + `bridge_fs_config_codec.h` | Changed (codec added — name- or offset-keyed not verified here) |
| `p2p.h` Sensory Sync over ESP-NOW (`COMMAND_SYNC_SETTINGS`, `TRIGGER_NOISE_CAL`, `CLEAR_NOISE_CAL`, `IDENTIFY_MAIN`) | absent (`esp_now` 0 files); replaced by BLE-MIDI control plane | **Dropped** |
| `FirmwareMSC` USB drag-and-drop update (hold MODE at boot) | present in 2 files; web flasher (esptool-js) is the ratified path | Kept, status unknown on S3 |
| `audio_transfer.h` 740 lines — acoustic modem: 9 data tones, pulse-timed, 2 bits/symbol, checksum; **not included by any `.ino` in any tag** | identical 740-line file, not included anywhere | **Dead in both** |
| `system.h:161-196` A-weighting table computed into `frequencies[i].a_weighting_ratio`; never read | not checked in K1 beyond the field | Dead in ancestor |
| `globals.h:220` + `serial_menu.h:628` Ticker samples `function_id` every 5 ms into `function_hits[]` (`debug=true`) | `function_id` at `system/globals.h:524`, `debug_function_timing` kept | **Kept — the ancestor of Emotiscope's sampling profiler** |
| `GDFT.h` (3.0.0) `lookahead_smoothing()` two-frame delay spike suppressor; commented out of the loop by 4.1.1 (`.ino:163`) | present in 1 file | Dormant in both |
| `presets.h` five hand-coded presets | `system/presets.h` 85 lines, `set_preset` in 4 files; 10 slots added 2026-06-06 | Extended |
| `extras/misc/bpm.h`, `onsets.h` tempo experiments | `k1_tempo.cpp` Goertzel-over-novelty + PLL + onset classification | K1 finished what the ancestor sketched |

Reading: K1 kept every architectural decision of 4.1.1 — loop skeleton, fixed-point colour, blob-ish persistence, hand-written serial control plane, sweet-spot-derived calibration and silence — and added product surface plus guard rails. Nothing structural was removed. Emotiscope removed almost all of it. [INFERENCE from the table]

---

## 4. What deserves praise

### P1 — The GDFT essay is the best design document in either codebase
`GDFT.h:1-56` (identical text in 3.0.0 and 4.1.1, and carried into K1) states the two reasons for Goertzel over FFT — choose your own bin spacing (semitones), and choose each bin's window length independently to trade time against pitch resolution — in language a non-DSP reader can follow. The MOOD table in 3.0.0 `GDFT.h:195-207` documents exactly how one knob drives two smoothing algorithms. K1's doctrine of "architecture subordinate to perceptual impact" is this essay's descendant. [FACT]

### P2 — Perceptual composite controls
Three knobs, each a *perceptual* quantity rather than a parameter: PHOTONS (brightness with `v²` law), CHROMA (colour, with the top 10 % switching to note-driven colour), MOOD (reaction speed, mapped onto follower rate *and* exponential-average weight, `GDFT.h` 3.0.0 `:213-224,263-265`). K1's usage ratification (mode + palette + photons + mood as Tier 1) confirms that the composite controls are the ones people touch. [FACT + INFERENCE]

### P3 — The Sweet Spot: a physical affordance for the auto-ranger
Three LEDs tell the user whether the signal is too quiet, in range, or clipping (`i2s_audio.h:138-150`, `led_utilities.h:104`). It turns an invisible internal state (auto-range headroom) into something a person can act on by moving the device or the volume. The concept survives in K1's code; the K1 product has no such indicator surface yet. [FACT]

### P4 — Sensory Sync: multi-unit coordination with zero infrastructure
`p2p.h` (2.0.0 `:9-16`) broadcasts settings, noise-cal triggers and an identify-flash over ESP-NOW with a main/secondary flag — 200 lines, no router, no app. It is the simplest working answer to "two units in one room" in the lineage. [FACT]

### P5 — Update paths that need no toolchain
3.0.0 added USB mass-storage drag-and-drop firmware updates (hold MODE at boot; `system.h:87 enable_usb_update_mode`, `FirmwareMSC`) and the WebSerial settings tool. Both remove the Arduino IDE from the customer's life. K1's web flasher is the modern equivalent of the second; the first has no K1 equivalent. [FACT]

### P6 — Time-slicing was here first
3.1.0 interlaced the 16 lowest (most expensive) bins on alternate frames (`3.1.0` `GDFT.h:60-80`) and moved LED output to its own FreeRTOS task on a single core. Emotiscope generalised this; K1 never adopted it. [FACT]

### P7 — The look-ahead flicker suppressor
3.0.0 `GDFT.h:295-346`: delay output by two frames; if frame *n+1* moves against both neighbours, replace it with their mean. A median-of-three on the time axis, bought for 20 ms of latency, that kills `FPS/2` flicker in dim bins. Disabled by 4.1.1 — presumably for latency — but the idea is sound and cheap. [FACT on code; INFERENCE on why disabled]

### P8 — Operational hygiene that Emotiscope kept and K1 kept
3-second settings debounce (`1.0.0` `system.h:209-218`), `lock_leds()` around filesystem writes (`bridge_fs.h:13,36,52`), version-named config file so a new firmware never reads an old layout (`bridge_fs.h:7`), factory reset via both buttons at boot, `ack()`/`bad_command()` discipline on the serial protocol.

### P9 — The acoustic configuration modem (unshipped)
`audio_transfer.h` + `extras/misc/audio_transfer.html`: a phone plays a "magic tone", pulses to measure timing, then nine data tones carrying two bits per symbol with a checksum; the device decodes with a fast GDFT on nine dedicated bins and animates pass/fail. Provisioning through the one sensor the product already has, with no radio, no cable and no OS permission prompt. It never shipped, but it is the most original idea in the tree. [FACT on code; UNVERIFIED that it ever worked]

---

## 5. Red team — what is wrong with Sensory Bridge (and therefore inherited)

| # | Finding | Evidence | Consequence for K1 |
|---|---|---|---|
| R1 | Calibration learns `SWEET_SPOT_MIN_LEVEL` from the raw waveform peak during frames 64–192 of a 256-frame noise cal, with no check that the room is actually quiet | `4.1.1` `i2s_audio.h:102-104` | This *is* the 281→745 poisoning path. K1's admission gates fence a design flaw; the DualMCU should replace the mechanism (a level-invariant silence test — see companion report X3) |
| R2 | Silence = 10 s continuously below `SWEET_SPOT_MIN_LEVEL×1.10`; a single loud frame resets the timer | `i2s_audio.h:138-160` | Ancestor of every SSL/crest gate difficulty in the K1 record |
| R3 | 12.8 kHz / 96 was chosen to fit an ESP32-S2 after 3.0.0's 24.4 kHz proved too expensive; nothing above 6.4 kHz is analysed, and the top semitone bins alias | `3.0.0` `constants.h:4` (24 400) → `3.1.0` (12 200) → `4.x` (12 800) | K1's "build contract" inherits a compute compromise as if it were a spec; the 24 kHz plan is correct and overdue |
| R4 | Q14 fixed-point Goertzel with `sample >> 6` input truncation | `4.1.1` `GDFT.h:92-94` | Low-frequency precision loss; K1 already paid ~310 µs/frame to promote to int64 |
| R5 | Config persisted as a raw `memcpy` of the struct; layout- and padding-dependent; no in-file version, only a file name | `bridge_fs.h:67,93-130` | Any field reorder silently corrupts settings; Emotiscope moved to name-keyed NVS for this reason |
| R6 | Header-only unity build, all state global, cross-thread sharing by convention (`led_thread` reads arrays the audio loop writes with no synchronisation) | `.ino:179-230` | K1's `AudioSemanticState` publish surface is the fix; the rest of the sharing is still by convention |
| R7 | Dead code shipped in releases: `audio_transfer.h` (never included), A-weighting (computed, never applied), `interlace_flip` (toggled, never read), `lookahead_smoothing` (commented out) | §3 | K1 copied all four |
| R8 | Hand-written `if/else` serial parser — 32 commands in 1 314 lines | `serial_menu.h:268-1294` | Grew to 10.9k lines in K1; linear cost per control |
| R9 | Development in the dark: single-commit version drops, no history, README's licence statement contradicts the LICENSE file | `git log`; §1 | Anyone forking cannot see *why* a change was made; K1's docs-as-authority culture is the antidote |
| R10 | Stability fixes in 4.1.1 are "potential" fixes for lock-ups (`vTaskDelay(1)`, bigger stack) | commit messages 2024-03-21 | The LED-thread-on-one-core design was never fully debugged before the author left for the S3 |

---

## 6. Extraction and translation for K1

Because K1 *is* Sensory Bridge, the extraction question inverts: less "what to borrow" and more "what to shed, what to finish, what to bring back, and what the ancestor's trajectory says about K1's next step".

### 6.1 Shed in the DualMCU greenfield (do not port)

| Item | Why | Evidence |
|---|---|---|
| `audio_transfer.h` as code | Dead in every release of both projects; 740 lines of untested modem | §3 |
| `interlace_flip`, unused A-weighting field, `function_id` + Ticker profiler, `sbs((` streams (unless the web tool is still used) | Dead or superseded; the sampling profiler and the descriptor table (companion X5/X6) replace the live parts | §3 |
| Raw-struct config blob | Replace with name-keyed storage generated from the descriptor table | R5 |
| `SWEET_SPOT_MIN_LEVEL`-derived calibration and silence | Replace the mechanism, not just the gates; keep the *indicator* concept (P3) | R1, R2 |
| The 12.8 kHz / 96 contract as a design constant | It is an S2 budget artefact; carry the 133 Hz frame rate forward (24 000 / 180) so the tempo tracker stays byte-identical, per the K1 record | R3 |
| Hand-written serial parser | Generate from the descriptor table | R8 |

### 6.2 Finish what the ancestor left half-done

| # | Item | Source | Lands in | Note |
|---|---|---|---|---|
| F1 | **A-weighting actually applied** to the spectrogram (or a perceptual weighting chosen deliberately) | `4.1.1` `system.h:161-196` computed, never used; Emotiscope 2.0 applied `0.5 + 0.5·A` | RT1062 AP | Harness golden before/after; it changes every downstream number |
| F2 | **Look-ahead flicker suppressor** as an optional VP stage | `3.0.0` `GDFT.h:295-346` | RT1062 VP | Costs 2 frames (15 ms at 133 Hz); measure against the 50 ms latency budget before enabling |
| F3 | **Sweet Spot indicator on the deck** — too quiet / in range / clipping | `i2s_audio.h:138-150` | Tab5 UI | The one physical affordance of the ancestor that K1's knob-less product lost |
| F4 | **Perceptual composite controls** as the Tier-1 rule | P2 | Descriptor table / deck | Mood already survives; write the rule so new controls are composites, not raw parameters |

### 6.3 Bring back what K1 dropped — product decisions for Captain

| # | Item | Source | Where it could live | Decision needed |
|---|---|---|---|---|
| B1 | **Sensory Sync** — multi-unit settings + calibration propagation + identify-flash | `2.0.0` `p2p.h` | S3 radio companion: ESP-NOW (Wi-Fi-layer, coexists with BLE at a throughput cost) or a BLE broadcast dialect | Is multi-K1 in one room a product scenario? If yes, this is ~200 lines on the S3 and a K1BR message type |
| B2 | **USB mass-storage firmware update** | `3.0.0` `FirmwareMSC`, `system.h:87` | RT1062 has USB OTG; Teensy 4.1's factory bootloader is not MSC-based, so this needs a custom bootloader stage | Only worth it if the web flasher's Chromium-only Web Serial is a customer blocker |
| B3 | **Acoustic provisioning** (the idea, not the code) | `audio_transfer.h`, `extras/misc/audio_transfer.html` | Research lane | Zero-radio pairing/config through the microphone; a differentiator for a device whose whole identity is listening. Treat as a spike, not a plan |

### 6.4 What the trajectory says (systems view)

- The author left this architecture. Faced with the same ancestor, he chose float over `SQ15x16`, RMT over FastLED, a published schema over a hand-written parser, two real cores over one time-sliced core, and a 7k-line rewrite over accretion. K1 chose the opposite on every axis and hit the S3 wall with ~22 µs of headroom. The DualMCU greenfield is the point where K1 gets to make Emotiscope's choices with K1's harness. [INFERENCE from both repos]
- K1's advantage over both ancestors is process: a differential harness, a parity oracle, provenance rules, a device registry. Neither ancestor had any of it, and both shipped dead code and "potential" fixes as a result. Keep the process; shed the structure.
- Sample rate is the clearest example of an inherited constraint mistaken for a spec. 3.0.0 → 3.1.0 halved it to survive on an S2; K1 wrote it into a "build contract"; the RT1062 has no such constraint.

### 6.5 Translation rules

1. DualMCU only; the legacy repo stays the parity oracle.
2. Sensory Bridge code is already in K1 under GPL-3.0 attribution; anything re-derived from the 4.1.1 tag stays under that attribution. The MIT history of ≤4.1.0 is a fact, not a plan — consult counsel before relying on it.
3. Every shed item in §6.1 is a diff the harness must show as *no change in golden output* (dead code) or *an intended change with a new golden* (calibration, sample rate, A-weighting).
4. Sequence: shed dead code (F-free, zero risk) → descriptor table + name-keyed persistence (companion X6) → calibration/silence mechanism replacement (X3 + R1/R2) → 24 kHz/180 contract → F1/F2 as optional harness-gated stages → B1–B3 as product rulings.

---

## 7. Map vs territory

- All source was read; nothing was run. Frame-rate claims ("100 FPS", "200 FPS LED") are the author's. [UNVERIFIED]
- Release-note content comes from the GitHub releases page fetched today; the repository itself carries no changelogs.
- Whether K1's `bridge_fs_config_codec.h` is name-keyed or offset-keyed was not read; §3 says so.
- The acoustic modem's HTML half was inventoried (84 lines), not executed; whether the feature ever worked on hardware is unknown.
- Licence observations are file facts, not legal advice.

---

## Appendix A — Files read

`1.0.0`: `SENSORY_BRIDGE_FIRMWARE.ino`, `constants.h`, `globals.h`, `i2s.h`, `fft.h`, `system.h` (knobs/settings), `lightshow_modes.h` (duet), `noise_cal.h`.
`2.0.0`: `SENSORY_BRIDGE_FIRMWARE.ino`, `p2p.h`; file inventory.
`3.0.0`: `GDFT.h` (complete), defaults; `3.1.0` `GDFT.h` (interlace), defaults.
`4.1.1`: `SENSORY_BRIDGE_FIRMWARE.ino`, `GDFT.h`, `constants.h`, `i2s_audio.h`, `globals.h` (CONFIG + defaults), `presets.h`, `bridge_fs.h`, `knobs.h`, `system.h`, `serial_menu.h` (index + debug), `led_utilities.h` (index + `show_leds`), `lightshow_modes.h` (index + Kaleidoscope), `p2p.h`, `buttons.h`, `audio_transfer.h` (structure); `extras/misc/bpm.h`, `onsets.h`, inventory; `README.md`; `LICENSE` at every tag; release notes (web).
K1: heritage-file sizes, feature presence grep, `audio/GDFT.h` shim, `system/config_types.h` constants, `.ino` version line.

## Appendix B — Sources

- Sensory Bridge repository: https://github.com/connornishijima/SensoryBridge
- Releases: https://github.com/connornishijima/SensoryBridge/releases
- Emotiscope (successor): https://github.com/Lixie-Labs/Emotiscope
- Companion report: `docs/research/2026-09-02-emotiscope-architecture-review.md`
