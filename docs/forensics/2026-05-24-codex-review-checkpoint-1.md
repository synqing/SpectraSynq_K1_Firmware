---
abstract: "Codex review package for checkpoint 1 of the K1 PIO migration. Contains the three Stage-1+3 diffs (platformio.ini new + i2s_audio.h driver migration + globals.h DRAM_ATTR), the Stage-0-tag byte-identity proof for lines 39-378 of i2s_audio.h, the §9 gotcha checklist with per-item handling, binary deltas vs the arduino-cli baseline, and the three specific must-confirm items per the execution envelope. The executing model (Claude Code) has finished Stages 0-3 and is HOLDING for Codex pass/flag before Stage 4."
---

# Codex Review Checkpoint 1 — K1 PIO Migration (Stages 0-3 complete)

| Field | Value |
|------|------|
| Date | 2026-05-24 |
| Repo | `~/SensoryBridge-main 9` |
| Branch | `feat/pio-core-bump` |
| Rollback tag | `pre-pio-migration-20260524-1320` → SHA `93052a9c6522de8f3712233b320fba8b09ec5be7` (in `/tmp/rollback_tag.txt`) |
| HEAD on branch | `93052a9` (Stage-0 WIP snapshot); Stage 1/2/3 edits are staged/working-tree, **NOT yet committed** — single consolidated commit lands at Stage 8 per plan §8 S8 |
| Plan | `LightwaveOS_Official/docs/agent-outputs/analysis/2026-05-24-pio-core-bump-scoping/MIGRATION_PLAN-v2-rebaselined.md` |
| Doctrine gate | `docs/forensics/2026-05-24-doctrine-gate-pio-migration.md` |
| K1-local forensic | `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html` |
| Executing model | Claude Code (claude-opus-4-7, 1M context) |
| Reviewer asked | OpenAI Codex (read-only, fresh context, NO shared working tree) |

This document is a **review package**, not an action item. The executing model is HOLDING until Codex returns pass/flag.

---

## 0. What Codex must confirm (binding, per user prompt + plan §6)

Three specific items. Each one is **independently sufficient to flag** if wrong:

### Item A — Philips slot defaults NOT overridden beyond `slot_mask`
- In the new `init_i2s()`, the only override on `std_cfg.slot_cfg` is:
  ```cpp
  std_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_RIGHT;
  ```
- `ws_pol`, `bit_shift`, `slot_bit_width`, `data_bit_width`, `slot_mode`, `bit_order_lsb` are NOT touched. The Philips macro `I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT, I2S_SLOT_MODE_MONO)` provides them.
- The plan §11 defect #2 trace: v1 added `ws_pol=true` on top of the Philips macro, double-applying the MSB shift. v2 must NOT do that. **Codex: confirm no second override.**

### Item B — Read size is `SAMPLES_PER_CHUNK * sizeof(int32_t)`, NOT the buffer `sizeof`
- The migrated read call (new line numbers around 78-80 of i2s_audio.h):
  ```cpp
  i2s_channel_read(rx_chan, i2s_samples_raw, CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t), &bytes_read, portMAX_DELAY);
  ```
- `CONFIG.SAMPLES_PER_CHUNK = 96` (`globals.h:80`), so this is **96 × 4 = 384 bytes**.
- The buffer is `int32_t i2s_samples_raw[1024]` (4096 bytes). The plan §11 defect #3 trace: v1 used `sizeof(i2s_samples_raw)` (4096 B) — a 10.6× over-read that would have corrupted DMA timing. v2 must NOT do that. **Codex: confirm no `sizeof(buffer)` form.**

### Item C — Lines 39-378 of pre-migration `i2s_audio.h` are byte-identical in the migrated file
- Pre-migration tag: `pre-pio-migration-20260524-1320` @ `93052a9`. Pre-migration line range: 39-378 (the extraction, DC calibration, sweet-spot, AGC, `calculate_vu` body).
- Captain's binding rule: this region must survive verbatim.
- **Direct diff result** (pre-migration lines 39-378 vs post-Stage-3 equivalent block, starting at current line 67 = `void acquire_sample_chunk(...) {`):
  ```diff
  11c11,13
  <   i2s_read(I2S_PORT, i2s_samples_raw, CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t), &bytes_read, portMAX_DELAY);
  ---
  >   // PIO-MIGRATION-STAGE-3 (2026-05-24): i2s_read → i2s_channel_read (rx_chan handle).
  >   // Read size unchanged (96 * 4 = 384 B). portMAX_DELAY blocking unchanged.
  >   i2s_channel_read(rx_chan, i2s_samples_raw, CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t), &bytes_read, portMAX_DELAY);
  ```
- **The ONLY delta in lines 39-378 is the single `i2s_read` → `i2s_channel_read` call substitution** (the explicit scope of the plan's S3 read-call replacement) plus two added traceability comment lines. Extraction (`(raw * 0.000512) + 56000 - 5120` then `>>2`), DC calibration (iters 0-127 / iter 128 stamp / iters 129-240 sweet-spot floor), AGC, `calculate_vu` — all byte-identical. **Codex: confirm only the documented call substitution.**

---

## 1. Scope addendum that landed during Stage 2 (Captain-approved 2026-05-24)

The plan §3 file list was widened from **3 files** to **8 files** during Stage 2 by Captain's APPROVE (in-session). Reason: arduino-esp32 3.2.0 / IDF 5.4.1 has a deprecated `STATUS` enum in `rom/ets_sys.h:553` whose `FAIL` value collides with the K1's bare `#define FAIL "..."` macro from `strings.h:1-2`. Pure namespace rename, zero behaviour change:

- `strings.h` — `PASS`/`FAIL` → `SB_PASS`/`SB_FAIL` (+ `#pragma once` added as hygiene, **NOT** the Class-2 fix; the redefinition errors at strings.h:4-5 turned out to be cascade from the macro collision, not real double-inclusion)
- `led_utilities.h:960, 1785` — 2 use-sites renamed
- `serial_menu.h:101` — 1 use-site renamed
- `bridge_fs.h:207` — 1 use-site renamed
- `i2s_audio.h:27, 36` — 2 use-sites renamed (these get **swept up into the Stage-3 rewrite** below, so they're inside the new `init_i2s()` body)

**Completeness gate (Captain-mandated):** `grep -rnwE 'PASS|FAIL' SPECTRASYNQ_K1_FIRMWARE/` returns ONLY:
- `audio_transfer.h:169, 174, 189` — dead file per plan §1.5 (not in `.ino` include list)
- `.ino:355` — string literal `"FAIL (alloc returned NULL — feature disabled)"`, NOT a macro use
- `strings.h:10, 11` — the **string-literal values** of the renamed macros (`#define SB_PASS "PASS"`, `#define SB_FAIL "FAIL ###..."`); must stay this way to preserve console output bytes
- 5 traceability-comment lines (lexical references in the `// PIO-MIGRATION-NAMESPACE-FIX (2026-05-24):` blocks)

No code-level macro USE of bare `PASS`/`FAIL` survives in any live TU.

---

## 2. Unexpected positive finding (informational — Codex should know)

Plan §8 S2 expected the first compile to fail on legacy I2S API removal (`missing driver/i2s.h symbols`). Reality: **arduino-esp32 3.2.0 / IDF 5.4.1 ships `driver/i2s.h` as a deprecation-warning *shim*, not a removal**. After the namespace fix, the legacy `i2s_driver_install`/`i2s_set_pin`/`i2s_read` API still compiled and linked cleanly, producing a working `firmware.bin`. The shim is slated for removal in IDF v6.0 (per the `STATUS` enum's `__attribute__((deprecated("Use ETS_STATUS instead")))` annotation).

Implication: Stage 3's I2S migration becomes a **forward-compatibility upgrade** (silences the deprecation warning, future-proofs against IDF v6.0) rather than a "required to compile" change. The plan still calls for it; we proceeded.

The single remaining warning after Stage 3 is **out of scope**: `system.h:48:28: warning: '++' expression of 'volatile'-qualified type is deprecated [-Wvolatile]`. C++20 rule on volatile post-increment of `function_hits[function_id]`. Persisted from Stage 2; not in the §3 file list. Stage 4 will decide if `-Wno-volatile` is added to `platformio.ini` build_flags or if Captain authorises a `system.h` edit.

---

## 3. The three diffs (against `pre-pio-migration-20260524-1320`)

### 3.1 `platformio.ini` (new file — 64 lines)

```ini
; PIO-MIGRATION (2026-05-24): K1 firmware build moved arduino-cli → PlatformIO.
;
; What:  this file replaces tools/compile-k1-arduino.sh as the canonical K1 build.
;        Targets pioarduino 54.03.20 = arduino-esp32 3.2.0 / ESP-IDF 5.4.1 and
;        FastLED 3.10.3 from lib_deps (vendored 3.9.16 retired).
; Why:   arduino-esp32 3.x deprecates the legacy I2S driver this firmware was
;        built against; the K1 hardware also needs the full N16R8 flash budget
;        (16 MB, currently under-provisioned at 8 MB).
; How:   see docs/forensics/2026-05-24-doctrine-gate-pio-migration.md (gate)
;        and MIGRATION_PLAN-v2-rebaselined.md (plan).
; Rollback: tag pre-pio-migration-20260524-1320 (SHA in /tmp/rollback_tag.txt).
; Scope: build tooling + I2S driver only. No DSP / visual / sample-rate change.

[platformio]
default_envs = k1_hardware
src_dir = SPECTRASYNQ_K1_FIRMWARE

[env:k1_hardware]
; pioarduino tag 54.03.20 ≡ arduino-esp32 3.2.0 (FastLED's blessed pinning for S3).
platform = https://github.com/pioarduino/platform-espressif32/releases/download/54.03.20/platform-espressif32.zip
board    = esp32-s3-devkitc1-n16r8
framework = arduino

; OPI PSRAM — both knobs required; flash size = full N16R8 budget.
board_build.arduino.memory_type = qio_opi
board_build.psram_type          = opi
board_build.flash_mode          = qio
board_build.flash_size          = 16MB
board_upload.flash_size         = 16MB
board_build.partitions          = default_16MB.csv

; BT-11: single-TU classic-Arduino layout — only the .ino enters compile.
; PIO preprocesses the .ino in place to <Sketch>.ino.cpp inside src_dir, so the
; filter must accept both the source .ino and the conversion output; otherwise
; PIO emits "Error: Nothing to build" (observed 2026-05-24 with PIO 6.1.19).
; The src dir has 0 hand-written .cpp files, so this stays strictly single-TU.
build_src_filter = +<*.ino> +<*.ino.cpp>

monitor_speed = 115200
upload_speed  = 921600
upload_port   = /dev/tty.usbmodem1101
monitor_port  = /dev/tty.usbmodem1101

build_flags =
    -DARDUINO_USB_MODE=1
    -DARDUINO_USB_CDC_ON_BOOT=1
    -DBOARD_HAS_PSRAM
    -DSB_K1_HARDWARE
    -DENABLE_VP_PERF_AUDIT=1
    -DESP32_ARDUINO_NO_RGB_BUILTIN
    -O3
    -ffast-math
    -Wno-deprecated-declarations
    -Wno-narrowing

; Dropped from arduino-cli K1_FLAGS (RMT4-era; no-ops or anti-patterns on RMT5):
;   FASTLED_RMT_BUILTIN_DRIVER=0   FASTLED_RMT_MAX_CHANNELS=4
;   FASTLED_RMT_MAX_TICKS_FOR_GTX_SEM=100   FASTLED_ESP32_FLASH_LOCK=0
;   FASTLED_INTERRUPT_RETRY_COUNT=0

lib_deps =
    fastled/FastLED@3.10.3
    file://libraries/FixedPoints
    file://libraries/M5ROTATE8
```

**Per-line deviation from plan §8 S1:**
- One adjustment: `build_src_filter = +<*.ino> +<*.ino.cpp>` (plan said `+<*.ino>` only). Reason: PIO 6.1.19 preprocesses the `.ino` to a `.ino.cpp` *inside `src_dir`*, and a `+<*.ino>`-only filter excluded the conversion output → "Error: Nothing to build". This is still strictly single-TU (src dir has 0 hand-written `.cpp` files; the only `.ino.cpp` is the PIO-generated wrapper from the single `.ino`).

### 3.2 `globals.h` diff (1 line changed)

```diff
@@ -183,7 +183,11 @@ bool chromatic_mode = true;
 // ------------------------------------------------------------
 // Audio samples (i2s_audio.h) --------------------------------

-int32_t i2s_samples_raw[1024]                = { 0 };
+// PIO-MIGRATION-STAGE-3 (2026-05-24): DRAM_ATTR added (BT-04). Defensive — keeps
+// the I2S RX DMA target in internal DRAM (not PSRAM) so the IDF 5.x DMA engine
+// sees coherent memory without explicit cache-flush. Likely already in DRAM by
+// default; zero-cost belt-and-braces.
+DRAM_ATTR int32_t i2s_samples_raw[1024]      = { 0 };
 short   sample_window[SAMPLE_HISTORY_LENGTH] = { 0 };
 short   waveform[1024]                       = { 0 };
 SQ15x16 waveform_fixed_point[1024]           = { 0 };
```

### 3.3 `i2s_audio.h` diff (-37 / +66 lines net)

Full diff produced by `git diff pre-pio-migration-20260524-1320 -- SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h`. The PIO-MIGRATION-NAMESPACE-FIX and PIO-MIGRATION-STAGE-3 traceability comments are inline.

**Replacement at top (lines 5-37 of pre-migration → lines 5-65 of post):**

```diff
-#include <driver/i2s.h>
-
-const i2s_config_t i2s_config = {
-  .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
-  .sample_rate = CONFIG.SAMPLE_RATE,
-  .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
-  .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
-  .communication_format = I2S_COMM_FORMAT_STAND_I2S,
-  .dma_buf_count = 2,
-  .dma_buf_len = CONFIG.SAMPLES_PER_CHUNK,
-};
-
-const i2s_pin_config_t pin_config = {
-  .bck_io_num = I2S_BCLK_PIN,
-  .ws_io_num = I2S_LRCLK_PIN,
-  .data_out_num = -1,  // not used (only for outputs)
-  .data_in_num = I2S_DIN_PIN
-};
-
-void init_i2s() {
-  esp_err_t result = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
-  USBSerial.print("INIT I2S: ");
-  USBSerial.println(result == ESP_OK ? PASS : FAIL);
-
-#if defined(CONFIG_IDF_TARGET_ESP32S2)
-  REG_SET_BIT(I2S_TIMING_REG(I2S_PORT), BIT(9));
-  REG_SET_BIT(I2S_CONF_REG(I2S_PORT), I2S_RX_MSB_SHIFT);
-#endif
-
-  result = i2s_set_pin(I2S_PORT, &pin_config);
-  USBSerial.print("I2S SET PINS: ");
-  USBSerial.println(result == ESP_OK ? PASS : FAIL);
-}
+// PIO-MIGRATION-STAGE-3 (2026-05-24): I2S driver migrated to ESP-IDF 5.x i2s_std.
+// Was: legacy driver/i2s.h (i2s_config_t + i2s_pin_config_t + i2s_driver_install +
+//      i2s_set_pin + i2s_read). Deprecated under arduino-esp32 3.2.0 / IDF 5.4.1;
+//      shimmed but slated for removal in IDF v6.0.
+// Now: driver/i2s_std.h (i2s_chan_config_t + i2s_std_config_t + i2s_new_channel +
+//      i2s_channel_init_std_mode + i2s_channel_enable + i2s_channel_read).
+// Preserved 1:1 from the legacy config — DMA sizing (dma_desc_num=2,
+// dma_frame_num=SAMPLES_PER_CHUNK=96), Philips slot timing (ws_pol/bit_shift
+// defaults), slot_mask=RIGHT (SPH0645 SEL=HIGH; OI-2), data_bit_width=32 (OI-1).
+// portMAX_DELAY blocking and read size (SAMPLES_PER_CHUNK*sizeof(int32_t)=384 B)
+// preserved verbatim. Init keeps the void return + PASS/FAIL print contract; NO
+// ESP_ERROR_CHECK (init failure must not panic-reboot).
+// Lines below (acquire_sample_chunk extraction, DC calibration, sweet-spot, AGC,
+// calculate_vu) are byte-identical to the pre-migration tag — DO NOT modify.
+// See: docs/forensics/2026-05-24-doctrine-gate-pio-migration.md
+//      and MIGRATION_PLAN-v2-rebaselined.md §8 Stage 3.
+#include <driver/i2s_std.h>
+
+static i2s_chan_handle_t rx_chan = NULL;
+
+void init_i2s() {
+  esp_err_t result;
+
+  // RX channel — mirror legacy dma_buf_count=2, dma_buf_len=SAMPLES_PER_CHUNK.
+  i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_PORT, I2S_ROLE_MASTER);
+  chan_cfg.dma_desc_num  = 2;
+  chan_cfg.dma_frame_num = CONFIG.SAMPLES_PER_CHUNK;   // 96
+  chan_cfg.auto_clear    = false;
+  result = i2s_new_channel(&chan_cfg, NULL, &rx_chan); // tx=NULL → RX-only
+  USBSerial.print("INIT I2S (channel): ");
+  USBSerial.println(result == ESP_OK ? SB_PASS : SB_FAIL);
+
+  // Standard-mode config — the documented 1:1 of legacy I2S_COMM_FORMAT_STAND_I2S.
+  i2s_std_config_t std_cfg = {
+    .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(CONFIG.SAMPLE_RATE),
+    .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
+                    I2S_DATA_BIT_WIDTH_32BIT,   // mirrors legacy bits_per_sample=32 — OI-1
+                    I2S_SLOT_MODE_MONO),        // mirrors legacy ONLY_RIGHT (contiguous packing)
+    .gpio_cfg = {
+      .mclk = I2S_GPIO_UNUSED,
+      .bclk = (gpio_num_t)I2S_BCLK_PIN,         // 13
+      .ws   = (gpio_num_t)I2S_LRCLK_PIN,        // 11
+      .dout = I2S_GPIO_UNUSED,
+      .din  = (gpio_num_t)I2S_DIN_PIN,          // 14
+      .invert_flags = { .mclk_inv = false, .bclk_inv = false, .ws_inv = false },
+    },
+  };
+  // SP-2: Philips macro hardcodes slot_mask=BOTH. SPH0645 SEL=HIGH → RIGHT (OI-2).
+  std_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_RIGHT;
+  // DO NOT override ws_pol or bit_shift. Philips defaults (ws_pol=false,
+  // bit_shift=true) ARE the equivalent of legacy I2S_COMM_FORMAT_STAND_I2S.
+  // (v1's bug: adding ws_pol=true on top, double-applying the MSB shift.)
+
+  result = i2s_channel_init_std_mode(rx_chan, &std_cfg);
+  USBSerial.print("I2S STD INIT: ");
+  USBSerial.println(result == ESP_OK ? SB_PASS : SB_FAIL);
+
+  result = i2s_channel_enable(rx_chan);   // new driver does NOT auto-start
+  USBSerial.print("I2S ENABLE: ");
+  USBSerial.println(result == ESP_OK ? SB_PASS : SB_FAIL);
+}
```

**Read call change (inside `acquire_sample_chunk`, line ~78 of current file):**

```diff
   size_t bytes_read = 0;
-  i2s_read(I2S_PORT, i2s_samples_raw, CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t), &bytes_read, portMAX_DELAY);
+  // PIO-MIGRATION-STAGE-3 (2026-05-24): i2s_read → i2s_channel_read (rx_chan handle).
+  // Read size unchanged (96 * 4 = 384 B). portMAX_DELAY blocking unchanged.
+  i2s_channel_read(rx_chan, i2s_samples_raw, CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t), &bytes_read, portMAX_DELAY);
```

---

## 4. §9 gotcha checklist — Codex cross-check

| ID | Gotcha | Handling | Codex confirms? |
|----|--------|----------|-----------------|
| G-01 | Legacy + new I2S driver coexistence panic | i2s_audio.h fully migrated to `i2s_std`. Stage 5 (next, post-Codex) will grep-confirm no live TU keeps `driver/i2s.h`. Current grep result: only `i2s_audio.h:6` (a comment referencing the old include) and `audio_transfer.h:1` (dead — per plan §1.5 not in `.ino` include list). | ☐ |
| G-02/03 | Legacy RMT pulled by core internals / CDC-on-boot conflict | `-DESP32_ARDUINO_NO_RGB_BUILTIN` retained as zero-cost insurance per plan §8 S1. `-DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1` set. | ☐ |
| G-04 | FastLED < 3.7 vs arduino-esp32 3.x | `fastled/FastLED@3.10.3` exact pin in `lib_deps`. Vendored `libraries/FastLED` (3.9.16) renamed to `libraries/_FastLED.disabled` via `git mv` (R10 — disable, don't delete; Stage 8 finalises deletion). | ☐ |
| G-14 | Partition transition → boot loop without erase | `min_spiffs` (8MB) → `default_16MB.csv` (16MB). Stage 6 is Captain-owned `erase_flash` — agent will NOT execute. | ☐ |
| BT-04 | PSRAM cache-coherency on the I2S DMA buffer | `DRAM_ATTR` added to `i2s_samples_raw` in globals.h. Defensive (likely already in DRAM by default). | ☐ |
| BT-11 | Multi-TU ODR firestorm | `build_src_filter = +<*.ino> +<*.ino.cpp>` — only the .ino + its preprocessor output, no `.h`/`.cpp` glob. Src dir has 0 hand-written .cpp files. | ☐ |
| BT-14 | Acceptance-gate slip on ODR | Stage 3/5 grep for `multiple definition` / `undefined reference` returned **zero hits**. | ☐ |
| SP-1 | S2-only register pokes | `#if defined(CONFIG_IDF_TARGET_ESP32S2)` block **deleted** (already inert on K1; new driver handles declaratively). | ☐ |
| SP-2 | Philips macro hardcodes `slot_mask=BOTH` | Overridden to `I2S_STD_SLOT_RIGHT` — the **only** slot override (Item A above). | ☐ |
| G-12 | `ledcSetup`/`ledcAttachPin` removed in 3.x | NOT a K1 blocker — `#if SB_HAS_SWEET_SPOT_LEDS` is 0 on K1 (all sweet-spot pins -1). Latent for non-K1 envs only. Captain's WIP commit (93052a9) already wraps the LEDC calls under the macro guard. | ☐ |

---

## 5. Open items (OI-1..OI-4) state

| OI | State after Stage 3 |
|---|---------------------|
| OI-1 (`data_bit_width` 32 vs 24) | **Default applied** (`I2S_DATA_BIT_WIDTH_32BIT`). Stage 7 (Captain-owned hardware verify) will compare `max_waveform_val_raw` and raw `i2s_samples_raw[]` magnitudes against the Stage-0 baseline. Fallback: switch to 24-bit width (`dma_frame_num=96` already multiple of 3). |
| OI-2 (SPH0645 SEL strap = HIGH → RIGHT slot) | **Applied** (`slot_mask = I2S_STD_SLOT_RIGHT`). Stage 7 catches: audio silent/half-rate → strap or slot wrong. Fallback: `I2S_STD_SLOT_LEFT`. |
| OI-3 (FastLED 3.10.3 RMT5 multi-strip on S3) | **No flags applied** (default RMT5). Stage 7 catches: missing strip, `no free tx channels`. Fallback: `-DFASTLED_RMT_MEM_BLOCKS=1`. |
| OI-4 (`esp32-s3-devkitc1-n16r8` in pioarduino 54.03.20) | **CLOSED.** Stage 2 build confirmed board resolves: `ESP32-S3-DevKitC-1-N16R8V (16 MB Flash Quad, 8 MB PSRAM Octal)`. |

---

## 6. Binary metrics (advisory)

| Stage | Toolchain | Sketch flash | Partition | RAM (globals) | Note |
|-------|-----------|--------------|-----------|---------------|------|
| Stage 0 baseline | arduino-cli + esp32:esp32@2.0.9 + FastLED 3.9.16 | 470,205 B (23.0%) | `min_spiffs` 8 MB → 1.97 MB app | 80,284 B (24.5%) | `/tmp/sb-k1-build/SPECTRASYNQ_K1_FIRMWARE.ino.bin` (470,576 B) |
| Stage 2 post-rename | pioarduino 54.03.20 + arduino-esp32 3.2.0 + FastLED 3.10.3 + legacy I2S shim | 550,074 B (8.4%) | `default_16MB.csv` 16 MB → 6.4 MB app | 83,112 B (25.4%) | `firmware.bin` produced |
| **Stage 3 post-driver-migration** | same + `driver/i2s_std.h` | **552,618 B (8.4%)** | same | **83,024 B (25.3%)** | **`firmware.bin` 553,024 B** |

Stage 0 → Stage 3 delta:
- Flash: +82,413 B (+17.5%) — well inside plan §7 ±30% advisory tolerance (toolchain bump alone can shift binary size significantly)
- RAM: +2,740 B (+3.4%) — within noise

The Stage 2 → Stage 3 delta (after the driver migration alone) is **+2,544 B flash, -88 B RAM** — essentially neutral. The new `i2s_std` driver replaces the legacy DMA bookkeeping with smaller channel-based state.

---

## 7. Open warning (out of scope)

The post-Stage-3 build emits exactly **one warning**:

```
SPECTRASYNQ_K1_FIRMWARE/system.h:48:28: warning: '++' expression of 'volatile'-qualified type is deprecated [-Wvolatile]
```

- C++20 deprecation rule. `function_hits[function_id]++` where `function_hits` is declared `volatile`.
- `system.h` is **NOT** in the §3 file list. Stage 4 will decide remediation:
  - (a) Add `-Wno-volatile` to `platformio.ini` build_flags (in-scope edit)
  - (b) Captain-authorised system.h edit to rewrite as `function_hits[function_id] = function_hits[function_id] + 1`
  - (c) Leave it — it's a single warning, non-blocking, the binary signs cleanly
- The I2S-deprecation warning from `driver/i2s.h:27` that Stage 2 emitted is **GONE** post-Stage-3 ✓ (the whole point of the migration).

---

## 8. Pass / flag

Codex must respond with one of:

- **PASS**: items A, B, C all confirmed; §9 gotcha checklist clean; no objections to the diffs. Executing model proceeds to Stage 4.
- **FLAG: <specific item>**: itemise. Executing model addresses each flag before proceeding.
- **REJECT**: structural objection. Executing model stops, reports to Captain, awaits decision.

Specifically for Codex's independent class-of-error attention:
- Hidden override of Philips slot defaults (Item A).
- Wrong read size (Item B).
- Any line within pre-migration 39-378 that ISN'T the documented i2s_read substitution (Item C).
- Any `lib_deps` ordering pitfall (FastLED before/after FixedPoints).
- Any silent re-introduction of a dropped FastLED RMT4-era flag.
- Any path-with-spaces hazard (`~/SensoryBridge-main 9` has a literal space).

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | agent:claude-opus-4-7 | Created. Stage 3 gate passed; HOLD for Codex checkpoint 1. Includes the three diffs (platformio.ini, globals.h, i2s_audio.h), the byte-identity proof for lines 39-378, the §9 gotcha checklist, OI-1..OI-4 state, binary metrics, and the three must-confirm items per the user prompt. Scope addendum recorded (PASS/FAIL → SB_PASS/SB_FAIL across 5 files, in-session Captain-approved). |
