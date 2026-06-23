---
abstract: "Lane 8 (SSA AP-1) — firmware-v3 audio pipeline reference for K1. firmware-v3 uses an IIR DC-blocking high-pass filter (per-sample, no stored constant) plus a per-bin post-Goertzel adaptive noise floor (EMA). It has NO per-device DC calibration, NO stored DC_OFFSET, and NO max_raw / SSL pre-cal phase. This explains why firmware-v3 is immune to SB's max_raw=0 / DC=-32767 pathology: there is no sentinel to write and no two-phase DC-then-SSL state machine to corrupt."
---

# Lane 8 — firmware-v3 audio pipeline reference for K1

RBDO: **GROUNDED** — every claim cites a specific firmware-v3 or SPECTRASYNQ_K1_FIRMWARE file:line, both repos inspected READ-ONLY.

## Files inspected

firmware-v3 (Lightwave-Ledstrip/firmware-v3/src/...):
- `audio/AudioCapture.h` (1–143)
- `audio/AudioCapture.cpp` (1–793) — both ESP32-S3 legacy and ESP32-P4 std driver paths
- `audio/backends/esv11/vendor/microphone.h` (1–232) — vendored Emotiscope v1.1_320 capture path
- `audio/backends/esv11/vendor/goertzel.h` (60–240) — per-bin noise floor adaptation

SB (cross-check, READ-ONLY):
- `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` (1–250)
- `SPECTRASYNQ_K1_FIRMWARE/noise_cal.h` (1–27)
- `SPECTRASYNQ_K1_FIRMWARE/GDFT.h` (136–175)

## firmware-v3 audio capture architecture

Two co-resident capture paths exist on K1 (ESP32-S3):

1. **LightwaveOS canonical path** — `AudioCapture` class (`AudioCapture.cpp`). Owned by `AudioActor` on Core 0. Reads stereo `int32_t` interleaved frames via legacy I2S driver, extracts the RIGHT channel (SPH0645), bit-shifts `>>10` to recover the 18-bit signed audio magnitude, then runs each sample through a first-order IIR high-pass DC blocker.

2. **ESV11 vendored path** — `backends/esv11/vendor/microphone.h::acquire_sample_chunk()`. Used when the build is configured with the ESV11 backend at 32 kHz (the canonical K1 production env per `firmware-v3/CLAUDE.md`). Reads the same stereo `int32_t` DMA buffer, extracts RIGHT, bit-shifts `>>10` for legacy driver (`>>14` for std driver), runs a near-identical IIR high-pass (`y[n] = G*(x - x_prev + R*y_prev)`), clamps to ±131072, then `dsps_mulc_f32(..., recip_scale=1/131072, ...)` normalises into the `sample_history[]` ring buffer for Goertzel.

Both paths converge on the same architectural commitment: **DC is removed by a real-time IIR high-pass filter applied per-sample. No stored DC constant exists in the time-domain path.**

## firmware-v3 noise calibration (if any)

There is **no time-domain noise calibration** of the SB shape (no startup phase that estimates a DC bias and stamps it into NVS). Two orthogonal mechanisms cover the same product surface:

1. **Per-sample IIR DC-blocker** (time-domain, `AudioCapture.cpp:42, 183–186` and `microphone.h:55–67, 217–225`):
   ```
   // AudioCapture.cpp:42
   static constexpr float DC_BLOCK_ALPHA = 1.0f - (2.0f * pi * 20.0f / SAMPLE_RATE);
   // ...
   float dcBlocked = input - m_dcPrevInput + DC_BLOCK_ALPHA * m_dcPrevOutput;
   m_dcPrevInput = input;
   m_dcPrevOutput = dcBlocked;
   ```
   `fc = 20 Hz` (LightwaveOS path) / `fc = 5 Hz, R = 0.997545, G = 0.998772` (ESV11 vendored path, `microphone.h:58–63`). State is two floats per filter instance, zero-initialised at construction (`AudioCapture.cpp:45–47`). Convergence to DC-free output is sub-second at audio rates — no calibration ritual is required.

2. **Per-bin post-Goertzel adaptive noise floor** (`goertzel.h:197, 222–235`):
   ```
   static float noise_floor[NUM_FREQS];
   // ... avg_val = 0.9 * mean(last 10 noise_history rows for bin i)
   noise_floor[i] = noise_floor[i] * (1 - kNoiseAlpha) + avg_val * kNoiseAlpha;
   magnitudes_noise_filtered[i] = max(magnitudes_raw[i] - noise_floor[i], 0);
   ```
   This is a continuous EMA of the bin magnitude itself, retuned against the baseline chunk rate of `12800 / 64 = 200 Hz` (`goertzel.h:230–233`). It runs forever, not as a one-shot calibration. There is no "noise_complete" gate. There is no NVS persistence.

The `noise_calibration_wait_frames_remaining` / `noise_calibration_active_frames_remaining` counters at `goertzel.h:72–73` are declared but no path in the vendored file initialises them to nonzero; they are vestigial from the upstream Emotiscope reference, not a live calibration phase.

## firmware-v3 DC offset handling

**There is no `DC_OFFSET` field, no `dc_offset_sum` accumulator, no stored DC constant, and no two-phase calibration.** DC is subtracted by the per-sample IIR filter at the very first stage of every capture, on every frame, every boot, every device.

Filter state lives in two `float` fields per AudioCapture instance:
```
// AudioCapture.h:132–134
float m_dcPrevInput = 0.0f;
float m_dcPrevOutput = 0.0f;
```
ESV11 vendored path uses file-scope statics `dc_blocker_x_prev` / `dc_blocker_y_prev` (`microphone.h:66–67`). Initial values are `0.0f`. The filter converges from `0` to true DC-free output within a few hundred samples (well under one hop) because the high-pass corner is 5–20 Hz. There is no warm-up phase exposed to the rest of the system.

Crucially: **the IIR DC blocker subtracts a value that is computed live from the recent input stream. It is mathematically incapable of writing -32767 (or any other sentinel) into a long-lived field, because no long-lived field exists.** The two floats it holds are bounded by the recent sample magnitudes themselves.

## firmware-v3 max_raw / AGC tracker

There is **no `max_waveform_val_raw` / `SWEET_SPOT_MIN_LEVEL` (SSL) tracker in the SB sense**. firmware-v3 tracks `peakSample` per hop in `AudioCapture::CaptureStats` (`AudioCapture.h:46, AudioCapture.cpp:193–197`), but it is purely diagnostic — not a control input to any AGC.

AGC for firmware-v3 K1 is downstream of capture, at two layers:

1. **Sample-domain clamp** — after the IIR filter, the LightwaveOS path clamps to ±131072 then `* RECIP_SCALE * 32767` to produce the int16 sample (`AudioCapture.cpp:289–292`). ESV11 path clamps to ±131072 then multiplies by `recip_scale = 1/131072` to produce a `[-1, +1]` float into `sample_history[]` (`microphone.h:222–228`).

2. **Magnitude-domain max tracking** in Goertzel — `max_val_smooth` and `magnitudes_smooth[]` are computed per frame across the 64-bin spectrum (`goertzel.h:195, 234–240`). This is post-Goertzel, post-noise-floor-subtraction, and it adapts continuously. It does **not** feed back into anything that could be written to a sentinel like `-32767`.

There is no equivalent of SB's `CONFIG.SWEET_SPOT_MIN_LEVEL`, `CONFIG.SWEET_SPOT_MAX_LEVEL`, `min_silent_level_tracker`, or `max_waveform_val_follower`. The "sweet spot" / silence / loud state machine simply does not exist as a single-domain coupling in firmware-v3.

## firmware-v3 I2S init

`AudioCapture.cpp:695–748` (ESP32-S3 legacy driver) and `microphone.h:126–158` (ESV11 vendored path, also legacy on K1 with the current toolchain) configure I2S identically in the parts that matter for SPH0645 on K1:

```
mode                 = I2S_MODE_MASTER | I2S_MODE_RX
sample_rate          = SAMPLE_RATE   (32000 for ESV11 32 kHz env, 12800/16000 otherwise)
bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT
channel_format       = I2S_CHANNEL_FMT_RIGHT_LEFT  (stereo interleave)
communication_format = I2S_COMM_FORMAT_STAND_MSB
bits_per_chan        = I2S_BITS_PER_CHAN_32BIT
mclk_multiple        = I2S_MCLK_MULTIPLE_256
dma_buf_count        = 4 (LightwaveOS) / 4 (ESV11)
dma_buf_len          = DMA_BUFFER_SAMPLES*2 / 512*2
```

Post-`i2s_set_pin`, the LightwaveOS SPH0645 branch (`AudioCapture.cpp:742–747`) applies:
```
REG_CLR_BIT(I2S_RX_CONF_REG, I2S_RX_MSB_SHIFT);    // clear (>>10 path)
REG_CLR_BIT(I2S_RX_CONF_REG, I2S_RX_WS_IDLE_POL);
REG_SET_BIT(I2S_RX_CONF_REG, I2S_RX_LEFT_ALIGN);
REG_SET_BIT(I2S_RX_TIMING_REG, BIT(9));
```
The ESV11 vendor path applies the identical register tweaks (`microphone.h:153–156`) — explicitly noted as "Match LWLS legacy alignment tweaks for SPH0645 RIGHT channel extraction."

Cross-check vs Lane 3 (SB I2S init in `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h:7–37`):
- SB uses `channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT` (mono right-only) vs firmware-v3 `RIGHT_LEFT` (stereo, then extract right). Both can yield valid SPH0645 data on ESP32-S3, but the firmware-v3 stereo-and-extract pattern is the one that bench-validated on K1.
- SB uses `communication_format = I2S_COMM_FORMAT_STAND_I2S` vs firmware-v3 `STAND_MSB`. This is the bigger structural delta on I2S framing. STAND_MSB matches the SPH0645's MSB-first format documentation more cleanly; STAND_I2S adds a 1-bit-clock data delay that can mis-align the 24-bit payload inside the 32-bit slot if the register tweaks above are not applied.
- SB does NOT apply the `REG_*` post-`set_pin` tweaks (only an S2-specific block at `i2s_audio.h:29–32`). firmware-v3 applies them unconditionally on legacy driver. This is a known SPH0645-on-S3 alignment requirement.

## Structural delta vs SB

| Aspect | SB | firmware-v3 |
|---|---|---|
| Per-device DC cal | YES — `start_noise_cal()` zeros `dc_offset_sum`, accumulates `waveform[0]` for 128 iterations, stamps `CONFIG.DC_OFFSET = dc_offset_sum/128`, persists to `noise_cal.bin` (LittleFS) | NO — no per-device cal, no NVS-stored DC, no startup phase |
| DC subtraction site | `waveform[i] = sample - CONFIG.DC_OFFSET` (`i2s_audio.h:77`) — one integer subtract of a stored constant | Per-sample IIR HPF `y[n] = x[n] - x[n-1] + R*y[n-1]` (`AudioCapture.cpp:183, microphone.h:218`) — no stored constant |
| DC source | Long-term accumulator of `waveform[0]` over 128 iters during noise_cal Phase A | Two `float` filter state vars (`m_dcPrevInput`, `m_dcPrevOutput`), bounded by recent samples |
| AC coupling | Post-cal only (after `noise_complete == true`); pre-cal `waveform[i]` is DC-biased | Always-on; first sample is already (input − 0) and filter converges within ~hundreds of samples |
| Noise floor strategy | One-shot per-bin max during cal (`noise_samples[i]` tracks peak magnitude over 256 iters in `GDFT.h:136–145`), subtracted post-cal with 1.5× gain (`GDFT.h:172–173`); persisted to NVS | Continuous per-bin EMA against rolling 10-row noise history; never persisted, never one-shot (`goertzel.h:197, 222–235`) |
| Max-raw tracker | `max_waveform_val_raw` recomputed every chunk, drives SSL during cal, drives sweet-spot/silence/loud state and AGC follower post-cal | `peakSample` is diagnostic-only; magnitude max tracked downstream at Goertzel layer; no time-domain peak feeds AGC |
| Two-domain coupling risk | YES — SB's 2026-05-20 single-domain fix exists precisely because the original code mixed DC-biased and AC-corrected peaks; the `-32767` / `max_raw=0` pathology lives in this domain seam | NONE — no two-domain seam exists. There is no constant to mis-stamp, no SSL to sample, no sentinel to write |
| State machine | 256-iter calibration FSM (`noise_iterations`, `noise_complete`) with two phases (DC then SSL) | None — pipeline is stateless across boots beyond the IIR filter's two-float warmup |
| I2S channel format | `I2S_CHANNEL_FMT_ONLY_RIGHT`, `STAND_I2S` | `I2S_CHANNEL_FMT_RIGHT_LEFT` + extract right, `STAND_MSB`, plus `REG_RX_*` tweaks (`AudioCapture.cpp:742–747`) |
| I2S DMA buf count | 2 | 4 |

## Most-load-bearing delta

**firmware-v3 has no time-domain stored DC constant.** The IIR DC blocker is a pure dataflow operation — input arrives, filter convolves with two floats of state, output departs. There is no "DC_OFFSET" field to corrupt, no "noise_cal.bin" to mis-write, no `dc_offset_sum` to leave at an unstable value, and no "Phase A vs Phase B" seam where a max-raw tracker can be sampled in the wrong domain.

This is the structural property that makes firmware-v3 immune to the K1 max_raw=0 / DC=-32767 pathology, regardless of MEMS DC polarity, regardless of NVS state, regardless of boot timing. The Captain note about MEMS DC being negative (~-8767) is irrelevant to firmware-v3 because firmware-v3 never asks "what is the DC bias?" — it just filters it out continuously.

The secondary load-bearing delta is **no `max_waveform_val_raw` feeding AGC**. SB's sweet-spot / silence-floor / loud-break state machine consumes a time-domain peak that is computed alongside the DC subtraction, in the same loop, in the same domain. Any error in the DC half of that loop poisons the max-raw half. firmware-v3 sidesteps this entirely by computing peak-equivalents *post*-Goertzel where the per-bin EMA noise floor and per-bin magnitude tracking are independent, adaptive, and continuously self-correcting.

## Recommended SB approach (grounded in firmware-v3 reference)

Two options, ordered by minimal-blast-radius:

1. **Patch-in-place: replace `start_noise_cal()` DC arm with an always-on IIR HPF.** Delete the DC half of `noise_cal` (lines `i2s_audio.h:108–129` plus the `CONFIG.DC_OFFSET` field path). At capture time, between the `i2s_read` and the `waveform[i] = sample - CONFIG.DC_OFFSET` line, run each `sample` through a per-sample IIR HPF using the firmware-v3 LightwaveOS coefficient (`fc=20 Hz, alpha = 1 - 2πfc/Fs`) and write the filtered float (rounded to int) into `waveform[i]`. Keep the SSL / sweet-spot / AGC follower intact but seed SSL from the post-filter peak after a fixed warmup (e.g. 256 iters, no DC phase). Result: `CONFIG.DC_OFFSET` is removed entirely; there is no sentinel left to write; the pre-2026-05-20 calibration mutex cannot recur because there is no Phase A / Phase B seam.

2. **Direct port: import the firmware-v3 ESV11 vendored DC blocker macros (`DC_BLOCKER_FC=5, DC_BLOCKER_R=0.997545, DC_BLOCKER_G=0.998772` from `microphone.h:58–64`) verbatim into SB's `acquire_sample_chunk()` and drop both `dc_offset_sum`/`CONFIG.DC_OFFSET` AND the two-phase noise_cal FSM**. SSL becomes a single-phase max-peak observation over `noise_iterations < 256`, with `max_waveform_val_raw` already living in AC domain because the IIR has filtered the input. This more closely tracks the firmware-v3 reference but requires a deeper SB refactor.

Option 1 preserves SB's user-facing behaviour (manual `start_noise_cal` for the per-bin spectrum floor) while removing the structurally broken DC arm. The remaining noise_cal becomes a pure Goertzel-magnitude noise floor probe — matching firmware-v3's separation of concerns: time-domain DC is filtered continuously, frequency-domain noise is adapted continuously, neither persists a constant that can be corrupted.

Either option must be paired with the I2S init alignment fixes (`STAND_MSB` + `REG_RX_LEFT_ALIGN` + `REG_RX_CONF_REG` clears) per the firmware-v3 K1 reference. That is Lane 3 territory, not Lane 8.

## Open questions

- **Filter group delay impact on Goertzel.** A 20 Hz HPF has ~8 ms group delay at 100 Hz, ~1 ms at 800 Hz, negligible above. firmware-v3's full pipeline tolerates this; SB's beat tracker may have implicit assumptions about transient onset timing that would shift by single-digit ms. Re-test trigger: beat-detection F-measure regression > 5%.
- **MEMS DC polarity (-8767) effect on filter warmup.** Negative DC of ~8767 means the filter input starts at ~-8767 with both states at 0. First filtered output is ~-8767, then the IIR settles to zero-mean over ~Fs / (2π·fc) ≈ 256 samples at fc=20 Hz / Fs=32 kHz. SB consumers may need to wait one warmup window before trusting the first peak. This is the only behavioural window where the firmware-v3 approach is not strictly superior to a calibrated constant — and it is bounded and predictable rather than corrupt.
- **NVS migration.** Existing K1 devices have `noise_cal.bin` with a stamped `DC_OFFSET`. If Option 1 is taken, the field must remain wire-compatible (read but ignore) or the NVS struct version bump must orphan it cleanly. FIRMWARE_VERSION already bumped to 40102 for the 2026-05-20 single-domain fix; a further bump for "DC_OFFSET removed" is the clean path.
- **ES8311 codec gain interaction (ESP32-P4 path).** firmware-v3's P4 path uses runtime ES8311 gain (`AudioCapture.cpp:678, 753–786`). K1 is ESP32-S3 with a passive SPH0645, so this is not directly applicable, but the principle — runtime-tunable input gain rather than baked-in calibration — is the modern shape and worth noting if SB later moves to a codec-gated mic.
- **Verification path.** Lane 8 has not run firmware-v3 on the K1 bench in this session; the "previously known working" claim is per the task brief. Re-test trigger: serial capture of `peakSample` distribution on a firmware-v3 build flashed to the bench K1 with quiet ambient, verifying no `peakSample == 0` sustained run and no negative-sentinel writes anywhere in the audio path.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-23 | agent:lane-8-ssa | Created — firmware-v3 audio pipeline reference for K1, structural delta vs SB, recommended SB approach grounded in IIR-HPF-only / no-stored-DC pattern |
