---
abstract: "Every difference between the Main RPL K1's current firmware (2a620f7e, k1_main_rpl_im69d) and the previous bench K1's firmware (ed0aa984, k1_fe_bench_b489, B489A500), at four levels: build flags, compiled image, source (two catalogues, 92 files, 233 items) and stored settings. Also the Main RPL's own previous image (68a684dc): LED output pins only. 10 Nov 2026."
---

# Main RPL firmware vs previous K1 firmware — index

| Build | Commit | Env | Device | Read back |
|---|---|---|---|---|
| Main RPL now | `2a620f7e` (wip/rpl-pins-20261110 = 68a684dc + LED pin commit) | `k1_main_rpl_im69d` | chip 9087A500, USB B4:3A:45:A5:87:90 | 10 Nov `:build` epoch 1794248403 |
| Previous bench K1 | `ed0aa984` (68a684dc + 172 commits) | `k1_fe_bench_b489` | chip B489A500, USB B4:3A:45:A5:89:B4 | 9 Nov `:build` epoch 1793984825 |
| Main RPL's previous image | `68a684dc` | `k1_main_rpl_im69d` | 9087A500 | registry, 10 Nov (read-back matched a clean build except 45 stamp bytes) |

Method (map vs territory): a source diff overstates what reaches a device, so each level is shown separately. Builds were made by the lead from clean `git archive` exports with `pio run -v` (`build_*.log` in the session scratchpad); defines from the real compile lines; functions from `xtensa-esp32s3-elf-nm` on the ELFs. Limitation: the device images themselves were not read back (that needs a bootloader reset); identity rests on the `:build` read-backs naming commit and env. Function-name comparison can mis-report static functions that share a name (seen once: `select_notif_callback_isr`).

## A. Main RPL now vs its own previous image (68a684dc)
Only difference in the compiled image: the four LED output drivers moved from GPIO 15/16 (primary) and 17/18 (secondary) to GPIO 2/3 and 5/6 (`ClocklessController<15..18>` replaced by `<2,3,5,6>`; nothing else). Source: one file, `system/constants.h` (+14/−4), under `K1_MAIN_RPL_PINMAP_V1`. Stored settings were not changed by the flash.

## B. Main RPL now vs previous bench K1 (ed0aa984)
1. Build flags (`build_defines_diff.json`): 81 shared. Only Main RPL: `K1_LOOK_LIB_V1`, `K1_MAIN_RPL_PINMAP_V1=1`, `K1_WS2816_LEVER2_V1`. Only bench: `K1_AP_SUBSONIC_HPF_V1`, `K1_BENCH_REFERENCE_PINMAP=1`, `K1_FE_BENCH_B489_V1`, `K1_FE_BOARD_V1`, `K1_FX_BATTERY=1`, `K1_LOOK_LIB_WS2812_V1`, `K1_PCM1808_BCLK_PIN=11`, `K1_PCM1808_CANON_TRIM_Q15=2048`, `K1_PCM1808_DIN_PIN=10`, `K1_PCM1808_LINE_SWITCH=1`, `K1_PCM1808_LRCK_PIN=9`, `K1_PCM1808_MONO_POLICY=K1_PCM1808_MONO_MID`, `K1_PCM1808_NFC_CS_HOLD_PIN=-1`, `K1_RENDER_TRACE_V1`, `K1_TEMPO_CONSUMER_BANDS_V1`. Different value: `K1_BUILD_ENV`.
2. Compiled image (`compiled_image_diff.json`, `sizes_*.txt`): app image 728,320 B vs 807,552 B; code in flash 456,240 vs 520,716 B (+64,476); read-only data 179,824 vs 194,272 B; internal RAM zeroed at start 97,912 vs 175,664 B (+77,752: LED capture and line-in buffers); fast-RAM code 71,467 vs 71,847 B. Functions 3,027 vs 3,208: 43 only in Main RPL (LED drivers on GPIO 2/3/6, WS2816 16-bit packer, look library, Colour Lab, `__ieee754_pow`, file rename/mkdir), 224 only in bench, 69 changed size. Source files compiled only in the bench: `audio/k1_pcm1808_input.cpp`, `system/k1_fe_board.cpp` and the 14 `effects/light_mode_fx_*.cpp`; none compiled only in Main RPL.
3. Source, every change with "in Main RPL build / in bench build" and its guard: `catalogue_core.md` (38 files: audio, system, serial, persistence, diag, control, sketch, build config; 142 items) and `catalogue_visual.md` (54 files: effects and visual; 91 items). Lead spot-checks against the commits (all held): shared audio-frame flag `volatile` in Main RPL, plain in bench (`audio/k1_audio_frame.cpp`); loop clock from microseconds in Main RPL (wraps every 71.6 min) vs `millis()` in bench (`.ino`); settings save "5 s after last change" vs "quiet + 5 s or 60 s maximum" (`system/system.h`); incandescent-filter green term `uint16 >> 16` (always 0) in Main RPL vs `uint32` in bench (`visual/led_utilities.h` R:3026/B:3082); Waveform Hybrid saturation-memory fix guarded by `K1_POSITION_SMOOTH_V1`, defined in neither build.
4. Non-firmware: 452 further files differ (documents, tests, tools, scratch); none is compiled into either image. Commit list: `commits_classified.tsv` (172 commits, 113 touch firmware inputs).
5. Stored settings (`settings_diff.json`; bench read 9 Nov, Main RPL read 10 Nov): 12 of 30 differ — BASE_COAT_INTENSITY 0.050 vs 0.000, CHROMA 0.10 vs 0.15, DC_OFFSET 57 vs −238, INCANDESCENT_FILTER 0.50 vs 0.00, LED_TYPE 0 (one data line) vs 1 (two data lines), LIGHTSHOW_MODE 22 vs 18, MAX_CURRENT_MA 1913 vs 2500, MOOD 0.0 vs 0.8, PRISM_COUNT 1.00 vs 1.25, SENSITIVITY 2.6 vs 2.7, SQUARE_ITER 0.75 vs 1.00, SWEET_SPOT_MIN_LEVEL 108 vs 157 (bench value first).

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (lead) | Created after the unit swap, at the Captain's request; catalogues by two subagents, verified by the lead. |
