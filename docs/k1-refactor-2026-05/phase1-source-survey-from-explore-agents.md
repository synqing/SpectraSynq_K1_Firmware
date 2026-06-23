---
abstract: "Phase 1 source-verification outputs from three parallel Explore agents (2026-05-24). Recorded verbatim as session-context-only artefacts being persisted for the K1-rooted handoff session. Note: these outputs contain count claims (11 .h files, 9 modes, 125 then 141 commands, incandescent_lookup location) that were subsequently AUDIT-CONTRADICTED — see HANDOFF-to-k1-rooted-session.md for the re-verification list."
---

# Phase 1 Source Survey — Explore Agent Outputs (Verbatim)

These are the three parallel Explore agent outputs from the 2026-05-24 K1 refactor planning session. **Recorded verbatim as agents produced them.** Several claims here were subsequently contradicted by an audit run against live K1 source — those contradictions are flagged in `HANDOFF-to-k1-rooted-session.md` and must be re-verified by the K1-rooted session before any reliance.

---

## Agent 1 — K1 fork repo structure + build config

> Read-only inventory of the K1 SensoryBridge fork repo at `/Users/spectrasynq/SensoryBridge-main 9/`.

### 1. Top-Level Structure (Depth-2)

**Firmware source lives at:** `/SPECTRASYNQ_K1_FIRMWARE/` (platformio.ini `src_dir` setting).

Key directories:
- `/SPECTRASYNQ_K1_FIRMWARE/` — K1 firmware source (agent reported: 20 source files total — 11 `.h`, 1 `.ino`, 8 other). **NOTE: AUDIT-CONTRADICTED — audit found 19 .h files. Re-verify.**
- `/libraries/` — local vendored dependencies (FixedPoints, M5ROTATE8)
- `/docs/forensics/` — PIO migration doctrine and handoff records
- `/tools/` — legacy build scripts
- `/.pio/` — PlatformIO build outputs and downloaded libdeps

### 2. platformio.ini — Complete Configuration

**Default environment:** `k1_hardware`

**Platform & board:**
```ini
[env:k1_hardware]
platform = https://github.com/pioarduino/platform-espressif32/releases/download/54.03.20/platform-espressif32.zip
board = esp32-s3-devkitc1-n16r8
framework = arduino
```
(pioarduino 54.03.20 ≡ arduino-esp32 3.2.0 / ESP-IDF 5.4.1)

**Memory & flash:**
```ini
board_build.arduino.memory_type = qio_opi
board_build.psram_type = opi
board_build.flash_mode = qio
board_build.flash_size = 16MB
board_upload.flash_size = 16MB
board_build.partitions = default_16MB.csv
```

**Build flags:**
```ini
-DARDUINO_USB_MODE=1
-DARDUINO_USB_CDC_ON_BOOT=1
-DBOARD_HAS_PSRAM
-DSB_K1_HARDWARE
-DENABLE_VP_PERF_AUDIT=1
-DESP32_ARDUINO_NO_RGB_BUILTIN
-O3 -ffast-math -Wno-deprecated-declarations -Wno-narrowing
```

**Library dependencies:**
```ini
lib_deps =
    fastled/FastLED@3.10.3
    file://libraries/FixedPoints
    file://libraries/M5ROTATE8
```

**Build unit model:** Single-TU (classic Arduino):
```ini
build_src_filter = +<*.ino> +<*.ino.cpp>
```

### 3. File Census (as agent reported — AUDIT-CONTRADICTED on count)

Top 10 by LOC (agent's reading):
| # | File | LOC | Type | Contains |
|---|------|-----|------|----------|
| 1 | serial_menu.h | 2352 | .h | Menu/CLI handlers (no inline funcs) |
| 2 | led_utilities.h | 2046 | .h | 52 inline function bodies, 415 globals, 1 lookup table |
| 3 | lightshow_modes.h | 1911 | .h | Visual mode dispatch (no inline funcs) |
| 4 | encoders.h | 915 | .h | Encoder/ROTATE8 control |
| 5 | audio_transfer.h | 741 | .h | Audio pipeline |
| 6 | globals.h | 685 | .h | 10 inline funcs, 277 globals, 3 lookup tables |
| 7 | SPECTRASYNQ_K1_FIRMWARE.ino | 625 | .ino | setup/loop |
| 8 | system.h | 586 | .h | 17 inline funcs, 76 globals, 1 lookup table |
| 9 | Palettes.h | 568 | .h | Palette tables |
| 10 | i2s_audio.h | 500 | .h | I2S driver + audio I/O |

### 4. Build State at HEAD (agent's reading)

**Current branch:** `feat/pio-core-bump`
**Current commit SHA:** `c872032` (full: `c87203273b34bbc68118775bc3f5830c92514f7c`)
**Commit message:** `feat(audio): Fix-D — two-layer defense against DC_OFFSET calibration poisoning`

**Post-build figures** (from commit `2cbeea9`): Flash 552 622 B, RAM 83 024 B.

### 5. K1-vs-S2 Distinguishment (agent's reading)

Primary gate: `-DSB_K1_HARDWARE` build flag.

Secondary gates:
- `SB_HAS_ROTATE8` in `constants.h` (set to 0 on K1)
- `SB_K1_HARDWARE` in `constants.h`
- `SB_HAS_SWEET_SPOT_LEDS` derived from pin definitions
- `SWEET_SPOT_LEFT_PIN = 7`, `SWEET_SPOT_CENTER_PIN = 8`, `SWEET_SPOT_RIGHT_PIN = 9`

---

## Agent 2 — K1 fork feature inventory

> Read-only feature inventory of K1 fork firmware. **NOTE: Lightshow mode count, serial command count, and incandescent_lookup file location were subsequently AUDIT-CONTRADICTED.**

### Findings table (agent's reading)

| # | Feature | Status (per agent) | File:Line | Audit Status |
|---|---------|-------------------|-----------|--------------|
| 1 | P2P / ESP-NOW | REMOVED-FROM-SOURCE | none | Not contradicted |
| 2 | Cochlear AGC | PRESENT-GATED-OFF | GDFT.h:190 | Not contradicted |
| 3 | Broadband AGC v2 | PRESENT-ACTIVE | GDFT.h:190–220 | Not contradicted |
| 4 | M5ROTATE8 | PRESENT-GATED-OFF (`SB_HAS_ROTATE8=0`) | constants.h:35 | Not contradicted |
| 5 | Sweet Spot LEDs | PRESENT-ACTIVE (pin definition check) | constants.h:427 | Captain clarified separately: physical LEDs absent on K1; AP algorithm separate concern |
| 6 | INCANDESCENT_FILTER | PRESENT-ACTIVE (runtime gate) | led_utilities.h | Not directly contradicted |
| 7 | TEMPORAL_DITHERING | PRESENT-ACTIVE (runtime gate) | led_utilities.h | Not directly contradicted |
| 8 | reverse_leds | PRESENT-ACTIVE | led_utilities.h | Not contradicted |
| 9 | PHOTONS scaling | PRESENT-ACTIVE (mode 0/1/2 ifdef) | led_utilities.h:250–256 | Not contradicted |
| 10 | Serial menu commands | **125 unique handlers (per agent)** | serial_menu.h | **AUDIT: 186 strcmp lines. Plan Agent 2 said 141. Re-verify.** |
| 11 | WiFi / Bluetooth / USB | USB-ACTIVE; WiFi/BLE REMOVED | constants.h:51–53 | Not contradicted |
| 12 | noise_cal flow | PRESENT-ACTIVE | noise_cal.h + i2s_audio.h | Not contradicted |
| 13 | dump_raw command | PRESENT-ACTIVE (added at 99a730b7) | serial_menu.h + i2s_audio.h | Not contradicted |
| 14 | DC_OFFSET sanity clamp | PRESENT-ACTIVE (system.h:353–371) | system.h:353–371 | Not directly contradicted |
| 15 | dc_offset_sum accumulator | PRESENT-ACTIVE with rail rejection (`SAMPLE_RAIL_THRESHOLD 32000`) | i2s_audio.h + globals.h:200–201 | Not directly contradicted |
| 16 | Lightshow modes | **9 unique modes (per agent)** | lightshow_modes.h:1774–1793 | **AUDIT: 13 distinct `light_mode_*` definitions incl. kaleidoscope and quantum_collapse. Re-verify.** |

Agent's full list of 9 modes (per agent's reading):
1. LIGHT_MODE_GDFT
2. LIGHT_MODE_GDFT_CHROMAGRAM
3. LIGHT_MODE_GDFT_CHROMAGRAM_DOTS
4. LIGHT_MODE_BLOOM
5. LIGHT_MODE_BLOOM_FAST
6. LIGHT_MODE_VU
7. LIGHT_MODE_WAVEFORM_FAST
8. LIGHT_MODE_WAVEFORM
9. LIGHT_MODE_WAVEFORM_HYBRID

**AUDIT FOUND 13 — re-verify on K1-rooted session.**

### DC_OFFSET guard code (as agent reported)

```cpp
// system.h lines 353-371 (per agent)
if (CONFIG.DC_OFFSET == 0 || abs(CONFIG.DC_OFFSET) > 30000) {
  CONFIG.DC_OFFSET = 0;  // Override at runtime (no save_config)
}
```

`SAMPLE_RAIL_THRESHOLD = 32000` (per agent, in i2s_audio.h). Rail rejection in dc_offset_sum accumulator: only samples with `abs(sample) < SAMPLE_RAIL_THRESHOLD` are added.

---

## Agent 3 — K1 fork existing artefacts + doctrine

> Read-only survey of existing planning/forensic/doctrine artefacts in K1 fork.

### `docs/forensics/` (agent's reading)

| File/Directory | Coverage |
|---|---|
| `2026-05-23-archaeology/findings.md` | K1v2 purge master findings and archaeology lanes 1–9 |
| `2026-05-23-archaeology/findings/{lane-1-9}-hits.md` | Per-lane archaeology results |
| `2026-05-23-archaeology/progress.md`, `task_plan.md` | Archaeology task progression |
| `2026-05-23-sb-ap1-cal-state-investigation/` | Cal state forensics |
| `2026-05-24-doctrine-gate-pio-migration.md` | Doctrine reconciliation for PIO+ESP-IDF+FastLED migration |
| `2026-05-24-k1-waveform-fast-speed-investigation.md` | WAVEFORM-FAST latent timing bug |
| `2026-05-24-codex-review-checkpoint-1.md` | Codex review |
| `2026-05-24-stage7-handoff.md` | Stage 7/8 handoff: K1 functional, no commit yet |

**NOTE: `2026-05-24-stage7-handoff.md` was cited by Captain in the audit as contradicting "The Equivalent Port" equivalence claim. Re-read on K1-rooted session.**

### Doctrine Gate (agent's reading of `2026-05-24-doctrine-gate-pio-migration.md`)

Per agent: "1 `.ino` + **19** `.h` (classic single-TU Arduino layout)" — **the doctrine gate doc said 19, but Agent 1 reported 11. Audit confirms 19. Agent 1 was wrong.**

Pre-conditions enumerated:
- R5 (monolith teardown): narrow scope — build only, not architecture
- R6 (FastLED RMT driver-of-the-day): THREE re-test triggers crossed — FastLED 3.9.16→3.10.3, ESP-IDF 4.x→5.4.1, RMT4→RMT5
- R7 (I2S DMA = FPS gate): legacy `i2s.h` → `i2s_std.h` (re-test trigger)
- R9 (erase on partition change): `min_spiffs` (8MB) → `default_16MB.csv` (re-test trigger)
- R11 (fence refactors with `pre-*` tag + `backup/*` branch): WIP snapshot commit required pre-execution

### WAVEFORM-FAST Speed Investigation (agent's summary)

**Failure mode**: K1's `WAVEFORM-FAST` (mode 7) renders visibly 1.60× faster than S2 good-state snapshot (K1 LED_FPS=185.69 vs S2 LED_FPS=115.86).

**Root cause** at `lightshow_modes.h:1310`: Mode 7 shifts by 1 LED per render frame with no dt scaling. Frame-stepped transport directly accumulates with `LED_FPS`, not wall-clock time.

**Fix proposed but NOT applied**: Add dt-scaled transport like `WAVEFORM_HYBRID`, or cap render loop FPS. Left pending — product visual validation required before commit.

### K1 Hardware Definition (agent's summary of `docs/hardware/k1-hardware-definition.md`)

| Item | Value |
|---|---|
| Board | ESP32-S3-DevKitC-1 N16R8 (16 MB flash, 8 MB PSRAM) |
| LEDs | GPIO 6, 7 (2×160 WS2812 = 320 total) |
| Mic | SPH0645 I2S: BCLK 13, LRCLK 11, DIN 14 |
| I2C | SDA 17, SCL 18 |
| PSRAM | Always present — `-DBOARD_HAS_PSRAM` mandatory |
| Upload port | `/dev/tty.usbmodem1101` (K1); `/dev/tty.usbmodem02` (S2 protected — NEVER touch) |
| Controls | Disabled (`SB_HAS_*` off); no sweet-spot LEDs |

**Captain clarified 2026-05-24:** the physical SS LEDs are S2-only. They do NOT carry over to K1. But the Sweet Spot AP algorithm is hardwired into the audio pipeline regardless of LED presence and must be investigated before any strip decision.

### `.claude/` Directory (agent's reading)

| File | Contents |
|---|---|
| `.claude/CLAUDE.md` | Doctrine bridge + calibration policy |
| `.claude/skills/sensorybridge-doctrine/SKILL.md` | Product north star, doctrine priority order, gate outputs required |

**Calibration command policy (added 2026-05-24):** `start_noise_cal` NEVER auto-fired. Agent MUST wait for Captain to confirm silence verbally ("music paused, go") before sending. Violation = STOP-and-rollback. Origin: Stage 7 incident — agent auto-ran during music, poisoned `SWEET_SPOT_MIN_LEVEL` (281 → 745).

### Serial evidence at K1 Stage 7 (per agent)

```
FIRMWARE_VERSION=40102
CONFIG.LIGHTSHOW_MODE=7
CONFIG.SAMPLE_RATE=12800
LED_FPS=185.69
CONFIG.DC_OFFSET=0
[AP] SSL=299 DC=-4710 max_raw=1108-4338 peak_scaled=0.488-0.951
LEDs visibly responsive (Captain verbal: "YO! THAT IS REMARKABLY BETTER")
```

**NOTE: These numbers were captured before The Equivalent Port noise_cal recovery. The post-cal numbers I treated as canonical may or may not match this baseline. Audit says stage7-handoff.md contradicts the equivalence claim. Re-verify on K1-rooted session.**

### Visual-Equivalence Harness state (agent's reading)

- **Frame-buffer dumps**: None found
- **LED snapshot harness**: None found
- **Validation**: Manual — Captain visual confirm + serial perf counters (`vp_perf`, `show_us`, `frame_us`, `over`, `dropped`)
- **Test fixtures**: No bundled silence WAV, 1 kHz tone file, or music corpus in repo
- **`vp_probe_*` machinery**: Plan Agent 2 later identified this exists at `lightshow_modes.h:1671-1875` — Agent 3 did not surface it as a harness candidate

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | claude-code (Opus 4.7) | Persisted Phase 1 Explore agent outputs verbatim as session-context-only artefacts. Flagged audit-contradicted claims inline. Created during handoff to K1-rooted session. |
