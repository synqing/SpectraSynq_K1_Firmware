---
abstract: "Failproof, flag-gated (K1_MIC_IM73D_PDM_V1) plan to evaluate the IM73D122 PDM mic on the LIVE K1 AP+VP, bench-only (chip B489A500); SPH0645 (i2s_std) stays the byte-identical product default when the flag is OFF. Domain-match strategy: one pre-sensitivity input-gain lands PDM in the SPH0645 4k-10k band so no downstream constant is edited. 7 ordered #ifdef edits (PDM init/pins/int16-read/extraction, flag-aware calibration_profile_valid + boot force-invalidate, function-level NVS no-op in bridge_fs.h) + gain characterization + Captain-silence recal + staged capture + per-band-AGC acceptance via stream_agc + rollback + risk table. Red-team round 2 (2-member panel) = ready-with-fixes, all 9 folded. Read before touching i2s_audio.h/constants.h/system.h/bridge_fs.h/platformio.ini/k1_upload_guard.py for the IM73D lane."
---

# IM73D122 PDM → LIVE K1 AP+VP — Failproof, Flag-Gated Graft Plan (FINAL)

**Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware` · **Flag:** `K1_MIC_IM73D_PDM_V1` · **Bench K1 ONLY** (chip `B489A500`, USB serial `B4:3A:45:A5:89:B4`, port `/dev/tty.usbmodem12201`) · **SPH0645 (i2s_std) stays the product default.** · **Pre-graft baseline commit: `26eebb1` (current HEAD).**

> **Captain locks (non-negotiable):** SPH0645 default unchanged. IM73D is a bench-only evaluation behind one flag. Main K1 (`F887A500`) + Tab5 untouched. No `erase_flash`. No commit to feature/main without Captain. `start_noise_cal` never auto-fired. Do NOT flip `default_envs`.

---

## 1. Context

The SPH0645 front-end is two coupled contracts: a **driver/pin** contract (`i2s_std` channel + hand-tuned slot_cfg on bench pins BCLK=14/LRCLK=12/DIN=13) and an **amplitude-domain** contract (~15 downstream consumers with hardcoded raw-amplitude constants tuned to SPH0645's post-extraction working band, `max_raw ≈ 4k–10k` under music).

The IM73D122 changes **both**: different driver (`i2s_pdm_rx`), different pins (clk=13/din=12/LR=14 driven LOW), and a different raw numeric domain (**16-bit** int16 PCM, quiet ±20-40 / loud ±600-1100, DC≈0) vs SPH0645's 32-bit left-justified word run through `(raw*0.000512)+56000-5120; >>2`.

**De-risk strategy — domain-match, not domain-retune.** Replace *only* (a) driver init, (b) pins, (c) read buffer/width/geometry, (d) raw-extraction math — all under one flag. Choose a PDM pre-gain so post-extraction `max_waveform_val_raw` under music lands in the **measured** SPH0645 4k–10k band. Every downstream absolute constant then stays valid unchanged; ratio/log/learned quantities are scale-invariant by construction.

**Verified corrections folded in (all load-bearing, source-anchored):**
- **PDM is 16-bit-only on ESP32-S3** (IDF 5.4.1 `driver/i2s_pdm.h`). 32-bit slot is dead — use dedicated int16 buffer + 192-byte read + adjusted freeze-guard stride.
- **Init AND extraction co-gated under the same flag** — a PDM ±600 through the SPH line-346 math becomes a ~30,528 pedestal → DC-cal rejects → dead visual.
- **Double-gain trap:** the PDM branch joins the shared path at `*= k1_effective_sensitivity` (`SENSITIVITY 2.4 × input_trim`); `INPUT_GAIN` is **pre-sensitivity**, effective = `G × 2.4`.
- **`DC_OFFSET==0` is a poison sentinel** — `calibration_profile_valid()` requires `DC != 0`; boot sanity treats `DC==0` as "never calibrated" and wipes SSL/VU. Must be made legal under the flag.
- **Per-band AGC is ACTIVE** (`-DSB_AGC_PERBAND_V1=1`) — four independent gains, each capped at `AGC_MAX_GAIN=10.0`. Acceptance inspects **all four**.
- **NVS persistence is gated at the FUNCTION level** (not per call-site) — grep finds **34 call sites across 9 files**; only function-level no-op is provably complete.
- **Byte-identity is proven by two-commit PROGBITS baseline** — `registry_byte_gate.sh` is hardwired to `k1_hardware` and checks against a committed reference; `k1_bench_reference` needs an explicit before/after diff.
- **AGC acceptance reads all 4 bands via `stream_agc`**, not `[AP]` (which prints band-0 only).
- **Upload guard fail-OPENS for unregistered envs** — registration is a precondition to the first flash; any created sibling env must be registered atomically.

---

## 2. Ordered edits (file → what → why)

All firmware edits are `#ifdef K1_MIC_IM73D_PDM_V1 … #else <verbatim SPH0645> … #endif`. Flag defined in exactly ONE new env. Land in order; do not flash before EDIT 5 (guard) is green.

### EDIT 1 — `platformio.ini`: new bench-only env (additive)
Append after `[env:k1_bench_reference_harness]` (do **not** touch `[platformio] default_envs`):
```ini
; IM73D122 PDM MIC EVALUATION (2026-07-01) — NON-SHIPPABLE, BENCH K1 (B489A500 / 12201) ONLY.
; SPH0645 (i2s_std) STAYS the product default; this env is the ONLY build that defines the flag.
; Runs the LIVE production AP+VP (not a probe). REVERT = delete this env + the guard tuple line.
[env:k1_bench_im73d]
extends = env:k1_bench_reference
build_flags =
    ${env:k1_bench_reference.build_flags}
    -DK1_MIC_IM73D_PDM_V1
    ; -DK1_MIC_IM73D_DSR_16S_V1  ; RESERVE (KEEP OFF): Normal 1.638 MHz ~71 dB. Warrant-gated.
```
**Diagnostic sibling — DECISION REQUIRED (must_fix #4): default is to OMIT it.** `[APCAP]` spec_argmax is a *nice-to-have*; the authoritative acceptance runs on `[AP]` + `stream_agc` on the production-shape env. **Only create the sibling if `[APCAP]` is genuinely needed, and if so its guard registration (EDIT 5) + test coverage (EDIT 6) MUST land in the SAME edit — atomically.** Do not create it with a commented-out guard line.
```ini
; CREATE ONLY WITH ATOMIC GUARD REGISTRATION (EDIT 5) + TEST COVERAGE (EDIT 6).
[env:k1_bench_im73d_harness]
extends = env:k1_bench_ap_frontend_probe
build_flags =
    ${env:k1_bench_ap_frontend_probe.build_flags}
    -DK1_MIC_IM73D_PDM_V1
```
*Why:* `k1_bench_reference` is the only clean, production-equivalent, bench-GPIO, zero-instrumentation base; it inherits the bench upload port + guard via `extra_scripts`.

### EDIT 2 — `SPECTRASYNQ_K1_FIRMWARE/system/constants.h`: PDM pin macros + PDM-domain SSL fallback
Inside `SB_K1_BENCH_REFERENCE_PINMAP` (near `:264-270`), add — do **not** edit existing STD pins:
```c
#ifdef K1_MIC_IM73D_PDM_V1
  #define K1_PDM_CLK_PIN 13   // PDM clock out   (proven probe)
  #define K1_PDM_DIN_PIN 12   // PDM data in     (proven probe)
  #define K1_PDM_LR_PIN  14   // SELECT/LR driven LOW = LEFT slot / falling edge
#endif
```
And, near the cal-window block — **redefine the boot SSL fallback for the PDM domain (must_fix #3):**
```c
#ifdef K1_MIC_IM73D_PDM_V1
  // Boot fallback in the PDM silence domain (~216 loud-scaled). SPH default 350 is
  // OUT of the PDM silence band; seed measured on bench (Stage 5), NOT guessed.
  #undef  NOISE_CAL_SSL_BOOT_FALLBACK_RAW
  #define NOISE_CAL_SSL_BOOT_FALLBACK_RAW 120   // SEED — retune from PDM silence p90 on bench
#endif
```
*Why:* GPIO12/13/14 are a **physical mic swap** between mics (cannot run both) — confirm the swap before flashing (Stage 0). GPIO14 was STD `BCLK`; PDM has no BCLK/WS, so driving 14 LOW as GPIO is safe (LEDs 4/5, I2C 17/18, RNG 8 non-conflicting).

### EDIT 3 — `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`: guarded PDM driver init
Near `#include <driver/i2s_std.h>` (`:43`):
```c
#ifdef K1_MIC_IM73D_PDM_V1
  #include <driver/i2s_pdm.h>
  #include <driver/gpio.h>
#endif
```
In `init_i2s()` (`:203`) keep the **shared prologue** (`chan_cfg` + `dma_desc_num=SB_I2S_DMA_DESC_NUM(3)` + `dma_frame_num=CONFIG.SAMPLES_PER_CHUNK(96)` + `auto_clear=false` + `i2s_new_channel(&chan_cfg,NULL,&rx_chan)`) and the **shared epilogue** (`i2s_channel_enable` + print). Wrap only the mode config:
```c
#ifdef K1_MIC_IM73D_PDM_V1
  gpio_reset_pin((gpio_num_t)K1_PDM_LR_PIN);                    // clear residual STD BCLK binding
  gpio_set_direction((gpio_num_t)K1_PDM_LR_PIN, GPIO_MODE_OUTPUT);
  gpio_set_level((gpio_num_t)K1_PDM_LR_PIN, 0);                 // static LEFT select
  i2s_pdm_rx_config_t pdm = {
    .clk_cfg  = I2S_PDM_RX_CLK_DEFAULT_CONFIG(CONFIG.SAMPLE_RATE),        // DSR_8S default
    .slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,  // 16-bit ONLY (S3)
                                               I2S_SLOT_MODE_MONO),
    .gpio_cfg = { .clk = (gpio_num_t)K1_PDM_CLK_PIN,
                  .din = (gpio_num_t)K1_PDM_DIN_PIN,
                  .invert_flags = { .clk_inv = 0 } },
  };
  #ifdef K1_MIC_IM73D_DSR_16S_V1   // RESERVE — undefined everywhere; no-op.
    pdm.clk_cfg.dn_sample_mode = I2S_PDM_DSR_16S;
  #endif
  esp_err_t result = i2s_channel_init_pdm_rx_mode(rx_chan, &pdm);
  USBSerial.print("I2S PDM RX INIT: "); USBSerial.println(result == ESP_OK ? "PASS" : "FAIL");
#else
  /* existing i2s_std_config_t block :227-261 VERBATIM */
#endif
```
*Why:* preserves the init contract (void return, PASS/FAIL prints, **no `ESP_ERROR_CHECK`**). `I2S_PDM_RX_SLOT_DEFAULT_CONFIG(MONO)` already sets `slot_mask=LEFT` and default `dn_sample_mode=DSR_8S`. **Print the `esp_err_t`** so a rejected 16-bit/DSR combo is visible, not silent.

### EDIT 4 — read buffer + freeze-guard + extraction + dump_raw (CONCRETE CODE, must_fix #1 & #7)
The active read is inside `#ifdef K1_AUDIO_FREEZE_GUARD_V1` (this flag IS defined via `platformio.ini` and inherited by `k1_bench_im73d`). **Both** the freeze-guard branch and the `#else portMAX_DELAY` branch read into `i2s_samples_raw` and the guard zero-fills `i2s_samples_raw[z]` with `sizeof(int32_t)` stride. The buffer, byte count, divisor, zero-fill target, AND dump_raw print must ALL flip together — no comments, real nested `#ifdef`.

**`system/globals.h`** after `i2s_samples_raw` (`:140`):
```c
#ifdef K1_MIC_IM73D_PDM_V1
  inline DRAM_ATTR int16_t im73d_samples_i16[1024] = { 0 };   // dedicated typed buffer; no int32 alias UB
#endif
```
**`system/constants.h`** near loud-guard block:
```c
#ifdef K1_MIC_IM73D_PDM_V1
  #ifndef K1_MIC_IM73D_INPUT_GAIN
    #define K1_MIC_IM73D_INPUT_GAIN 3.0f   // PRE-SENSITIVITY seed. Effective = 3.0 * SENSITIVITY(2.4) = 7.2.
    // RETUNE on bench from measured SPH0645 max_raw baseline (Section 3). NOT a guess.
  #endif
#endif
```
**`audio/i2s_audio.h`** — replace the `bytes_requested` line + the ENTIRE `K1_AUDIO_FREEZE_GUARD_V1`/`#else` read block (`:277-300`) with a fully nested form:
```c
#ifdef K1_MIC_IM73D_PDM_V1
  const size_t bytes_requested = CONFIG.SAMPLES_PER_CHUNK * sizeof(int16_t);   // 192 B
#else
  const size_t bytes_requested = CONFIG.SAMPLES_PER_CHUNK * sizeof(int32_t);   // 384 B
#endif
  ...
#ifdef K1_AUDIO_FREEZE_GUARD_V1
  #ifdef K1_MIC_IM73D_PDM_V1
    const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, im73d_samples_i16, bytes_requested, &bytes_read, pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS));
    if (i2s_read_status != ESP_OK || bytes_read < bytes_requested) {
      const size_t samples_got = bytes_read / sizeof(int16_t);
      for (size_t z = samples_got; z < CONFIG.SAMPLES_PER_CHUNK; z++) im73d_samples_i16[z] = 0;
    }
  #else
    const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, i2s_samples_raw, bytes_requested, &bytes_read, pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS));
    if (i2s_read_status != ESP_OK || bytes_read < bytes_requested) {
      const size_t samples_got = bytes_read / sizeof(int32_t);
      for (size_t z = samples_got; z < CONFIG.SAMPLES_PER_CHUNK; z++) i2s_samples_raw[z] = 0;
    }
  #endif
#else
  #ifdef K1_MIC_IM73D_PDM_V1
    const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, im73d_samples_i16, bytes_requested, &bytes_read, portMAX_DELAY);
  #else
    const esp_err_t i2s_read_status = i2s_channel_read(rx_chan, i2s_samples_raw, bytes_requested, &bytes_read, portMAX_DELAY);
  #endif
#endif
```
**dump_raw one-shot (`:315-324`)** — flag-gate the loop to print int16 decimal (the characterization instrument):
```c
    for (uint16_t i = 0; i < dump_n; i++) {
#ifdef K1_MIC_IM73D_PDM_V1
      USBSerial.printf("  %d\n", (int)im73d_samples_i16[i]);
#else
      USBSerial.printf("  %08lx\n", (unsigned long)(uint32_t)i2s_samples_raw[i]);
#endif
    }
```
**Extraction (`:346-348`):**
```c
#ifdef K1_MIC_IM73D_PDM_V1
  int32_t sample = (int32_t)((float)im73d_samples_i16[i] * K1_MIC_IM73D_INPUT_GAIN);  // no 0.000512/+bias/>>2
#else
  int32_t sample = (i2s_samples_raw[i] * 0.000512) + 56000 - 5120;
  sample = sample >> 2;
#endif
```
*Why:* everything after extraction — `*= k1_effective_sensitivity` (`:350`, shared, applies 2.4 + trim + `record_preclip`), `±32767` clamp (`:356`), `waveform[i] = sample − CONFIG.DC_OFFSET` (`:362`), peak/follower/`peak_scaled`, cal, GDFT — is shared and unchanged. **Do not trust any Stage-4/7 result until `dump_raw` shows non-zero int16 PCM** — this is the anti-DEAD-but-PASS check.

### EDIT 5 — `scripts/platformio/k1_upload_guard.py`: register env (MANDATORY, precondition to any flash)
In the `role="2nd bench K1"` / `usb_serial="B4:3A:45:A5:89:B4"` / `chip_id="B489A500"` `envs` tuple (`:77-86`):
```python
            "k1_bench_agc_probe",
            "k1_bench_im73d",              # IM73D122 PDM eval — bench B489A500 ONLY
            # add "k1_bench_im73d_harness" HERE — and ONLY IF — the sibling env is created in EDIT 1
```
Do **not** add to the main-K1 (`F887A500`) tuple; do **not** add to `BLOCKED_UPLOAD_ENVS`. *Why:* unregistered → guard **fail-OPENS** (`:156-158`, `"no K1 upload mapping enforced"`, exit 0) → a `--upload-port 1401` could write bench PDM/GPIO firmware onto the main K1. If EDIT 1's sibling is created, its registration line here is **not optional and not commented** (must_fix #4).

### EDIT 6 — `tests/test_k1_upload_guard.py`: explicit coverage
Add `"k1_bench_im73d"` to `test_bench_reference_env_is_bound_to_second_bench_k1` and `("k1_bench_im73d", "/dev/tty.usbmodem1401")` to `test_cross_flash_attempts_are_rejected`. If (and only if) the sibling env exists, add it to both tests too so `test_all_k1_chip_bound_envs_are_registered_in_guard` (`:138`) stays green.

### EDIT 7 — calibration guardrails (RAM-only, boot force-invalidate, persistence-off)
All `#ifdef K1_MIC_IM73D_PDM_V1`:

- **`globals.h` `calibration_profile_valid()` (`:214-220`):** drop the `DC_OFFSET != 0` term (DC-free PDM legitimately learns 0); keep `|DC| ≤ NOISE_CAL_DC_MAX_VALID_ABS` and the SSL-range term. `#else` verbatim. **Single mandatory edit** — without it every PDM cal is rejected.
- **`system.h` boot cal-load (`~:438-486`) — ordering fixed (must_fix #3 & #8):** there are **TWO sequential repair blocks**. Block 1 fires on `DC==0` (the LEGAL PDM state) → wipes SSL/VU + persists; Block 2 fires on `SSL<NOISE_CAL_SSL_MIN_VALID_RAW` → resets SSL to fallback + persists. Under the flag:
  - (a) **skip the `DC_OFFSET==0` rejection term** so DC=0 is legal (else every boot wipes a just-learned cal);
  - (b) run the intended **force-invalidate BEFORE both blocks** (`DC_OFFSET=0; VU_LEVEL_FLOOR=0; noise_samples cleared; calibration_profile_loaded=false; CAL_SOURCE_DEFAULT_INVALID`) so a stale SPH profile is never applied;
  - (c) **do NOT set SSL=0 and do NOT bypass the SSL clamp** — leave boot SSL at the PDM-domain `NOISE_CAL_SSL_BOOT_FALLBACK_RAW` (EDIT 2). A literal `SSL=0` (or SPH-domain 350) reaching the runtime branch leaves the follower floor at 0, making `waveform_peak_scaled_raw = max/follower` a **0/0 = NaN** at cold-boot silence. **Verify no NaN before first re-cal.**
- **NVS persistence-off — FUNCTION-LEVEL gating (must_fix #6):** call-site enumeration is unsound (34 sites, 9 files, incl. `serial/serial_cmd_handlers.h` and `persistence/bridge_fs_config_codec.h`). Instead, early-return no-op at the **single definitions in `persistence/bridge_fs.h`**:
  - `save_config()` (`:78`), `save_config_delayed()` (`:119`), `save_ambient_noise_calibration()` (`:217`), `save_calibration_profile()` (`:294`, return `false`), `clear_calibration_profile()` (`:418`, return `false`).
  ```c
  void save_config() {
  #ifdef K1_MIC_IM73D_PDM_V1
    return;   // NVS frozen for PDM eval — SPH0645 profile on disk is structurally untouchable
  #endif
    ...existing body...
  }
  ```
  ~5 edits, provably covers all 34 sites. This also neutralizes the persist calls inside both boot-repair blocks (must_fix #8d). Bench eval loses brightness/mode/preset persistence across reboot — Captain OK.

*Why:* PDM cal is RAM-only, re-learned each boot under a Captain-confirmed silence window; no cross-domain NVS poison in either direction is possible.

### Downstream threshold decisions (explicit)
**Default = ZERO downstream threshold edits.** If characterization lands loud `max_raw` in the measured SPH0645 4k–10k band, these hold unchanged via the shared post-extraction path: `SAMPLE_RAIL_THRESHOLD=32000`, `K1_LOUD_GUARD_NEAR_RAIL_RAW=28000`, `PEAK_PIN=0.92`, `SPEC_SAT=0.92/0.18`, `SWEET_SPOT_MAX_LEVEL=30000`, `AGC_FLOOR_*`, SSL windows `[50,720]/1500/650`, `DC_MAX_VALID_ABS=12000`, per-band `AGC_MAX_GAIN=10`. Loud-guard defaults **ON** — with matched gain it sits at trim=1.0 and never mis-fires low. **Fallback only if the bench A/B proves no single `G` satisfies the SSL window and the per-band AGC-cap simultaneously:** a flag-gated widen of the SSL band and/or `AGC_MAX_GAIN` under the flag, zero impact on SPH0645 default.

---

## 3. Input-gain characterization method (empirical, not baked)

`K1_MIC_IM73D_INPUT_GAIN` is **pre-sensitivity**; effective = `G × SENSITIVITY(2.4) × input_trim(1.0)`. Sweep and score in **total-gain terms**.

1. **Capture an SPH0645 baseline FIRST** (Stage 0): on `k1_bench_reference`, at fixed stimulus + matched SPL, record `[AP]` `max_raw`, `follower`, and — via `stream_agc` (see below) — all four `agc_bands[].gain`, plus (harness) per-band spectrogram magnitudes + `chroma_mean`. This is the parity anchor — the 4k–10k number must be the board's *measured* operating point, not the 20-28k protection ceilings.
2. **Confirm the int16 layout** with `dump_raw=silence` / `dump_raw=tone`: floor ±20-40 decimal, tone swings, one sample per `im73d_samples_i16[i]` (no 4-byte-slotted padding = no 16-in-32 misconfig). Confirm effective **Fs=12800** — scope GPIO13 for the realized PDM clock (DSR_8S ≈ 819.2 kHz via `mclk_multiple=256`, **not** a bare Fs×64 assumption); if the live AP path runs Fs=16000, re-derive and re-confirm the mic's rated band.
3. **Sweep `G` ∈ {2, 3, 4.5, 6}** (total 4.8/7.2/10.8/14.4). For each, under representative music read `[AP]` `max_raw` over 30 s; set `G = 3.0 × (SPH_baseline_peak / observed_peak)`.
4. **Score against BOTH binding constraints simultaneously** (they do not co-scale — SSL keys off per-frame peak, AGC off mean magnitude):
   - loud `max_raw` in the measured SPH band, **below** near-rail 28000, non-railed;
   - **all four** `agc_bands[].gain` NOT pinned at 10.0 under music (read via `stream_agc`);
   - silence-frame peak lands SSL in `[50,720]`, p90 ≤ 650.
5. Lock `G` where all conditions hold with margin. If none exists → the flag-gated SSL/AGC widen fallback (itself untested until the bench A/B — treat "no single G works" as a real branch, not an edge case).

---

## 4. Re-cal sequence under Captain silence-go (load-bearing policy)

`start_noise_cal` is **NEVER agent-auto-fired.**

1. Flash `k1_bench_im73d` (identity-gated). Boot force-invalidates any stale profile → device boots uncalibrated (over-sensitive by design, SSL at PDM-domain fallback, no NaN). Allow the PDM decimator HPF to settle (a few seconds after `i2s_channel_enable`) before cal.
2. Agent **waits** for Captain verbal "music paused, silence, go."
3. Agent sends `start_noise_cal`. Watch `[AP]` + the `NOISE CAL QUALITY / ACCEPTED` print: expect `cal_reason=NONE`, `cal_valid=1`, `dc_valid=1` with `DC≈0` (legal under flag), `ssl_valid=1` in-band. `profile_invalid`/`ssl_range` = a flagged constant still needs tuning (or `G` off).
4. Agent **waits** for Captain "resume" before assuming normal acoustics.
5. Cal is RAM-only; every reboot repeats steps 2-4 (persistence-off under flag).

---

## 5. Staged build → flash → capture protocol

Reuse existing surfaces only: `dump_raw` (ungated), `[AP]` 1 Hz (ungated `:ap_stream=on`), `stream_agc` (ungated runtime toggle), `[APCAP]` (`ENABLE_AP_STREAM` — sibling only), the DTR/RTS-LOW reader in `scripts/regression-harness/wireless_ab_bench.py`, `parse_serial.py`, `apstream_ingest.py`. **Correction:** `_scratch/im73d_bringup/read_serial.py` **does** exist (created this session; the DTR/RTS-LOW-before-`open()` reader, mirrors `wireless_ab_bench.py:848-873`) and is fine for simple `[AP]` stream capture; use `wireless_ab_bench.py` for gated `[APCAP]` / U1-U7 runs. Do NOT author a third parallel capture endpoint.

- **Stage 0 — Pre-flight.** Confirm the physical mic is the IM73D (13/12/14), not SPH0645 (14/12/13) — physical swap; record who performed it. Capture the SPH0645 baseline (§3.1, incl. `stream_agc` g0..g3). Note: rollback cal is a **fresh re-cal**, not a snapshot restore.
- **Stage 1 — Host gate.** `pytest tests/` GREEN (must stay 427/427; DRIFT-CATCHER + boundary tests pass after EDIT 5/6).
- **Stage 2 — Byte-identity gate (two-commit PROGBITS baseline, must_fix #2 & #9).** You cannot have pre- and post-graft binaries at the SAME HEAD (shared TUs carry the new `#ifdef`). Correct method:
  - **`k1_hardware`:** run `bash scripts/regression-harness/registry_byte_gate.sh` on **HEAD `26eebb1`** (pre-graft) to confirm GREEN against the committed reference — establishing the pre-graft baseline. After landing EDIT 1-7, rebuild `k1_hardware` and re-run the gate; GREEN proves the `#else` path is verbatim (the flag never reaches this env).
  - **`k1_bench_reference`:** the gate script is **hardwired to `k1_hardware`** and does NOT cover this env. Prove it explicitly — on `26eebb1` build `k1_bench_reference` and record the five PROGBITS section SHAs (`objcopy` dump of `.flash.text .flash.rodata .dram0.data .iram0.text .iram0.vectors` → `sha256`, path-invariant caveat for `.flash.rodata`), then after the graft rebuild and diff against the stored baseline (same toolchain, two commits). Do **not** cite `registry_byte_gate.sh` as the bench_reference proof.
  - Also build `k1_bench_im73d` clean (manual — the pre-commit hook only builds `k1_hardware`).
- **Stage 3 — Identity-gated flash.** `pio run -e k1_bench_im73d -t upload`. Guard MUST print `verified as 2nd bench K1 (B4:3A:45:A5:89:B4, chip B489A500)`; a dry `--upload-port /dev/tty.usbmodem1401` MUST exit 2. No `erase_flash`.
- **Stage 4 — Read proof (pre-re-cal, `dump_raw` ONLY).** Boot serial: `I2S PDM RX INIT: PASS` + `I2S ENABLE: PASS`. `dump_raw` confirms **non-zero int16 PCM** (floor ±20-40, tone swing) and Fs=12800. **Do NOT trust any `[AP]` amplitude here** — stale SPH0645 DC/SSL still bias it. A zero dump = the EDIT 4 buffer swap is wrong; stop.
- **Stage 5 — Characterize `G`** (§3), lock PDM-domain SSL fallback (EDIT 2), re-flash.
- **Stage 6 — Captain silence-go re-cal** (§4). Gate: `cal_valid=1`, `cal_reason=NONE`, no NaN.
- **Stage 7 — Autonomous AP capture (post-re-cal).** DTR/RTS-LOW open → `:ap_stream=on` + `stream_agc` → block on the FIRST `[AP]` line (AP stream may be off at boot) → collect `[AP]` + `sbs((agc_debug=…))` over real music + a click track → `parse_serial.py`, `wireless_ab_bench.py` gates U1-U7. For `[APCAP]` spec_argmax, use the sibling if created.
- **Stage 8 — Captain eyes-on** (§6, blocking).
- **Stage 9 — Rollback** (§7).

---

## 6. Acceptance criteria (all required)

Grounded in real `[AP]` / `stream_agc` / `[APCAP]` fields; **all amplitude/colour gates evaluated only AFTER Stage-6 re-cal.**

**Absolute-amplitude parity (anti-false-pass gate):**
- loud `max_raw` within ≈0.5×–2× of the Stage-0 SPH0645 baseline at matched SPL, non-railed (no sustained pin ~32000);
- **all four `agc_bands[].gain` read via `stream_agc` (must_fix #5)** NOT pinned at `AGC_MAX_GAIN=10.0` under music. **`[AP]` prints band-0 only — a band-0-only PASS is the exact 2026-06-21 "louder→dimmer"/washed-colour false-works vector and is FORBIDDEN as the sole source.** Enable `stream_agc` (`serial_menu.h:3438`; emits `sbs((agc_debug=…;gain:g0,g1,g2,g3;…))` for all `NUM_AGC_BANDS`, compiled unconditionally, runtime-gated by `stream_agc_debug`) and gate on g0..g3 each < 10.0;
- silence-frame SSL in `[50,720]`, p90 ≤ 650, `cal_valid=1`, `DC≈0`.

**Dynamics + timing (ratio/log — scale-invariant, still verify span):**
- quiet→loud `max_raw` swing tracks (≈30 dB), `waveform_peak_scaled` swings (not pinned 0/1, **no NaN**);
- `bpm` within tolerance, `conf` high, `lock=1` on click track + real music; `onset=1`/`bass=1` on transients;
- (harness) `spec_argmax` follows a swept tone; `follower_mean` rises with level.

**Colour clarity:** (harness) `chroma_mean` + chord-hue band-separation within bound of the SPH0645 baseline across a **bass-heavy** and a **treble/broadband** track (a scalar gain cannot fix a frequency-response/HPF-corner mismatch — bass roll-off regresses drop-cut/onset/low-band colour).

**Perceptual (blocking, per Sensory Bridge doctrine — invoke `/sensorybridge-doctrine` before landing):** Captain eyes-on A/B vs SPH0645 baseline, multiple genres, incl. VU-family modes (no top-end AGC → compression risk). Reject on: dimmer-than-SPH, compressed loud-vs-quiet dynamics, washed/greyed hue, quiet-passage noise-floor flicker, dual-channel/motion-memory regression. Host/telemetry green does **not** close this.

---

## 7. Rollback

1. Reflash `k1_bench_reference` (SPH0645) — guard-gated to 12201/B489A500.
2. **Fresh Captain silence-go SPH0645 re-cal** (the Stage-0 snapshot is a cross-check target, not a restore mechanism — no serial path writes DC/SSL to NVS, and PDM cal was RAM-only, so NVS was never poisoned).
3. Confirm `[AP]` shows SPH0645-domain DC (learned empirically, soft expectation ~-4714, not a gate) + sane SSL.
4. Update `docs/hardware/device-build-registry.md` deployed-state row.
5. **Full revert of the graft** = delete `[env:k1_bench_im73d]` (EDIT 1) + the guard tuple line (EDIT 5) + the `#ifdef` blocks. Production (`k1_hardware`) and bench SPH0645 (`k1_bench_reference`) are per-section byte-identical (two-commit PROGBITS baseline, Stage 2) — the flag never reaches them.

---

## 8. Non-goals (explicit)

- **NOT** flipping the product default. `default_envs=k1_hardware` untouched; SPH0645 stays the shipping mic.
- **NOT** touching main K1 (`F887A500`) or Tab5. **No `erase_flash`.**
- **NOT** committing to feature/main without Captain (`wip/*` or `--no-verify` for crash-checkpoints only).
- **NOT** enabling DSR_16S (reserved/undefined; the +2 dB is datasheet-gated, needs its own scope + could backfire via doubled-clock EMI). Keep DSR_8S.
- **NOT** editing any downstream consumer, GDFT core, or default-path threshold constant — the graft is one env + guarded init/pins/read/extraction/cal + function-level NVS gate. Threshold changes are a flag-gated fallback only.
- **NOT** adding MabuTrace/harness/probe to the acceptance-authoritative env (stays production-shape; only the optional sibling carries `[APCAP]`).
- **NOT** auto-firing `start_noise_cal`.
- **NOT** treating compile, `.bin` hash, band-0-only AGC, or `[AP]` numbers as musical proof.

---

## 9. Risk table (risk | mitigation | proof)

| Risk | Mitigation | Proof |
|---|---|---|
| SPH0645 default regresses (flag OFF) | 100% new code under `#ifdef`, verbatim `#else`; flag only in new env | `k1_hardware` `registry_byte_gate.sh` GREEN pre & post at commits 26eebb1→post; `k1_bench_reference` five-PROGBITS SHA diff GREEN (two-commit) |
| EDIT 4 read-block wired to wrong buffer → DEAD-but-PASS | Concrete nested `#ifdef` swaps buffer+bytes+divisor+zero-fill+dump_raw together (both freeze-guard & `#else` branches) | Stage-4 `dump_raw` shows **non-zero int16 PCM**; zero dump = stop |
| PDM 32-bit slot rejected/downgraded | 16-bit slot + dedicated int16 buffer + 192 B read + adjusted stride; print `esp_err_t` | `I2S PDM RX INIT: PASS`; `dump_raw` one int16/sample; cadence 133 Hz |
| Init flips PDM but SPH extraction runs → DC annihilation | Init AND extraction co-gated under SAME flag | Stage-4 `dump_raw` + Stage-7 `[AP]` `DC≈0`, AC present |
| Double-gain → railing / SSL reject | `INPUT_GAIN` pre-sensitivity; characterize total `G×2.4` vs measured SPH band | Stage-5 sweep: loud non-railed in 4k-10k, silence SSL ∈ [50,720] |
| `DC_OFFSET==0` sentinel → cal rejected + boot-wiped | Flag-aware `calibration_profile_valid()` (drop `!=0`) + skip DC==0 rejection + boot force-invalidate before both repair blocks | Stage-6 `cal_valid=1, cal_reason=NONE, DC≈0` |
| Boot SSL=0 / SPH-350 → 0/0 NaN in `waveform_peak_scaled` | PDM-domain `NOISE_CAL_SSL_BOOT_FALLBACK_RAW`; preserve (don't bypass) SSL clamp | Cold-boot silence: SSL non-zero in-domain, no NaN before re-cal |
| Per-band AGC pins at 10× → dim/washed colour, band-0-only false PASS | Land gain in SPH band; inspect **all four** `agc_bands[].gain` via `stream_agc` (not `[AP]`) | `sbs((agc_debug=…;gain:g0,g1,g2,g3))` all <10.0 under music; `chroma_mean`≈baseline |
| NVS cross-contamination (both directions) | **Function-level** no-op of save/clear in `bridge_fs.h` (covers all 34 sites) + RAM-only cal + boot force-invalidate | `config.bin`/`noise_cal.bin` byte-identical across full PDM session incl. reboot; SPH reload clean |
| Wrong-device flash (port drift) | Register env in guard B489A500 tuple **before** first flash; identity by USB serial | Guard prints B489A500 verify; `--upload-port 1401` → exit 2; DRIFT-CATCHER green |
| Sibling env created but unregistered → guard fail-OPEN | Sibling create + guard registration + test coverage are ATOMIC, else omit sibling | `test_all_k1_chip_bound_envs_are_registered_in_guard` GREEN |
| Stale SPH cal poisons Stage-3 amplitude reads | Trust only `dump_raw` pre-re-cal; all `[AP]`/`stream_agc` amplitude gates AFTER re-cal | Ordering enforced in §5 |
| Spectral-shape / bass-roll-off (scalar gain can't fix) | Same-acoustic A/B on bass-heavy + treble; Captain multi-genre eyes-on | `chroma_mean`/band-sep ≈ baseline; onset/drop-cut fire on bass |
| VU modes compress (no top-end AGC) | VU-family in eyes-on gate | Eyes-on: VU dynamics track quiet→loud |
| Effective Fs ≠ 12800 → GDFT/tempo drift | Scope GPIO13 clock; confirm Fs; re-derive if 16000 | Logic-analyzer clock + `bpm/lock` on click track |
| GPIO14 residual STD BCLK binding on warm reflash | 14 free in PDM; `gpio_reset_pin` before drive-LOW; cold-flash | Boot PASS + non-railed reads |
| Byte-identity method un-runnable ("same HEAD") | Two-commit baseline: hash on 26eebb1, rebuild+diff post-graft | Stage 2 procedure |
| Reset-on-open drops device mid-capture | DTR/RTS-LOW-before-open reader | Autonomous capture completes without reset |
| Cal fired during music | Never auto-fire; Captain "silence, go"/"resume" | Verbal confirmation logged |
| PDM HPF startup transient poisons first cal | Cal only after enable + settle | `cal_reason=NONE` on stable silence window |
| Shared chan_cfg vs probe DMA geometry (residual) | Diff probe chan_cfg vs production; scope realized 819.2 kHz | Stage-4 clock scope + PASS |

**Reused, not rebuilt:** proven probe PDM config, `[AP]`/`[APCAP]`/`dump_raw`/`stream_agc`, freeze-guard, two-phase noise-cal, `wireless_ab_bench.py` reader + U1-U7, `parse_serial.py`, `apstream_ingest.py`, `registry_byte_gate.sh` (k1_hardware only), `k1_upload_guard.py`.

**Key source anchors (verified this session):** `audio/i2s_audio.h` (init `:203`; `bytes_requested` `:278`; freeze-guard read `:287-300` reads `i2s_samples_raw`, zero-fills `sizeof(int32_t)` stride; dump_raw int32-hex `:315-324`; extraction `:346`; `[AP]` band-0-only `:718`); `system/constants.h` (bench pins `:264-270`); `system/globals.h` (`i2s_samples_raw :140`, `calibration_profile_valid :214-220`); `system/system.h` (two boot repair blocks `~:438-486`); `serial/serial_menu.h` (`stream_agc` toggle `:3438`, `stream_agc_data` emitter `:3519-3560`, all `NUM_AGC_BANDS`, runtime-gated `stream_agc_debug :80`); `persistence/bridge_fs.h` (`save_config :78`, `save_config_delayed :119`, `save_ambient_noise_calibration :217`, `save_calibration_profile :294`, `clear_calibration_profile :418`); `scripts/regression-harness/registry_byte_gate.sh` (`ENV_NAME="k1_hardware"` hardwired, committed reference, `--update`); pre-graft HEAD `26eebb1`.

---

## 10. Red-team round 2

**Panel size: 2. Actual verdicts: `ready-with-fixes`, `ready-with-fixes` (must_fix non-empty — 9 items).** This was NOT a clean pass. **Post-fold status: ready** — every must_fix is folded below with the source anchor confirmed this session.

| # | Sev | must_fix (verbatim gist) | How this FINAL plan now handles it |
|---|---|---|---|
| 1 | high | EDIT 4 read wired the buffer swap as comments only; active read is inside `#ifdef K1_AUDIO_FREEZE_GUARD_V1` and both branches read `i2s_samples_raw` + zero-fill `sizeof(int32_t)` → literal exec leaves read/zero-fill/dump_raw on int32 → all-zero waveform, dead LEDs, boot prints PASS | EDIT 4 now ships **concrete nested `#ifdef` code** for both the freeze-guard and `#else` branches (read target, byte count, divisor, zero-fill target all swapped) + flag-gated int16-decimal `dump_raw`. Stage-4 gate: non-zero int16 PCM or STOP. Confirmed against `i2s_audio.h:277-324`. |
| 2 | high | `registry_byte_gate.sh` is hardwired to `k1_hardware` + checks a committed reference; it does NOT cover `k1_bench_reference` — the "both envs identical" claim was overstated | Stage 2 + Risk table now: `registry_byte_gate.sh` proves **`k1_hardware` only**; `k1_bench_reference` gets an **explicit five-PROGBITS `objcopy`+`sha256` before/after diff**. Confirmed hardwired `ENV_NAME="k1_hardware"` + committed reference. |
| 3 | med | Boot force-invalidate set SSL=0 + skipped clamps → SSL 0 (or SPH-350) reaches runtime; follower floor 0 → `max/follower` = 0/0 NaN at cold-boot silence | EDIT 2 adds PDM-domain `NOISE_CAL_SSL_BOOT_FALLBACK_RAW`; EDIT 7 **preserves the SSL clamp** (no SSL=0, no bypass). Acceptance adds explicit **no-NaN** check before first re-cal. |
| 4 | med | Optional sibling env is chip-bound but EDIT 5 showed its guard registration commented → RED test or fail-open to main K1 | EDIT 1 default is to **OMIT the sibling**; if created, guard registration (EDIT 5) + test coverage (EDIT 6) are **atomic in the same edit**, never commented. |
| 5 | high | 4-band AGC gate has no telemetry in cited surfaces — `[AP]` prints band-0 only → false-PASS on the 2026-06-21 washed-colour defect | Acceptance now reads **all four bands via `stream_agc`** (`serial_menu.h:3438`/`:3519`, emits `gain:g0,g1,g2,g3`, compiled unconditionally). Band-0-only PASS explicitly FORBIDDEN. Confirmed emitter source. |
| 6 | high | NVS "untouchable" was per-call-site (partial) — grep finds 34 sites/9 files incl. unnamed files → PDM save can still write | EDIT 7 switches to **function-level no-op** at the 5 single definitions in `bridge_fs.h` (`:78/:119/:217/:294/:418`) — provably covers all 34 sites. Confirmed definitions. |
| 7 | med | Freeze-guard degrade-to-silence PDM path was a comment sketch → risk of zero-filling the wrong buffer on every timeout | Folded into EDIT 4's concrete code (same fix as #1): the entire guard block is fully `#ifdef`'d with `im73d_samples_i16` + `sizeof(int16_t)` divisor. |
| 8 | med | Boot force-invalidate ordering under-specified vs TWO sequential repair blocks (Block 1 on DC==0 wipes+persists; Block 2 on SSL<min resets+persists) | EDIT 7 now: (a) skip DC==0 rejection, (b) force-invalidate BEFORE both blocks, (c) PDM-domain SSL fallback, (d) persist calls neutralized by the function-level NVS gate (#6). Confirmed two blocks at `system.h:~438-486`. |
| 9 | med | Stage 2 "before vs after at the SAME HEAD" is un-runnable (shared TUs carry the new `#ifdef` once landed) | Stage 2 rewritten as a **two-commit baseline**: hash on pre-graft `26eebb1`, rebuild + diff post-graft. "Same HEAD" wording dropped. HEAD confirmed = `26eebb1`. |

**Residual risks carried forward (not blocking, tracked):** shared `chan_cfg` vs probe DMA geometry (Stage-4 scope); `G=3.0` is a seed and the SPL-matched A/B spans a physical mic swap (manual, error-prone — characterization mandatory); spectral-shape/HPF-corner mismatch not scalar-correctable (bass-heavy + treble eyes-on only); flag-gated SSL/AGC-widen fallback itself untested until bench A/B ("no single G" is a real branch); NVS-freeze loses persistence across reboot (confirm no boot path refuses to boot on an unwritten profile); `registry_byte_gate.reference` must be current on this branch HEAD; SSL-vs-AGC constraints do not co-scale; PDM HPF startup transient; warm-reflash GPIO14 residual binding; SPH0645 DC doc inconsistency (~8000 vs ~-4714, empirical, non-load-bearing).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-01 | agent:claude-code | Promoted the hardened-workflow **round-2** plan to canonical (supersedes the round-1 hand-patched draft). Provenance: SSA workflow (27 agents — scope → per-surface design → dual-adversarial verify → synth → red-team → finalize). The round-1 red-team **crashed mid-response** and the auto-finalizer misread its `null` as "clean"; that was caught, the pipeline was **hardened** (retried 2-member red-team panel + a finalize that is forbidden from claiming clean when the red-team failed or has a non-empty must_fix) and **re-run**. Round-2 red-team **completed** (2× `ready-with-fixes`, 9 must_fix) and INDEPENDENTLY converged on the round-1 manual fixes **plus two material refinements the manual pass got wrong**: (1) `DC_OFFSET==0` is a poison sentinel → make `calibration_profile_valid()` flag-aware, don't merely set DC=0; (2) NVS lockout must be **function-level** in `bridge_fs.h` (34 sites / 9 files), not per-call-site. Corrected the stale "`read_serial.py` does not exist" note (it exists — created this session). Status: **post-fold READY**. No production firmware edited (plan only). |