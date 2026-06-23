# K1 WAVEFORM-FAST Speed Investigation

Captured: 2026-05-24 18:38 AWST

Status: investigation checkpoint. No firmware fix applied.

## Verdict

H1 is confirmed for the current K1 runtime: `WAVEFORM-FAST` visible trail transport is render-frame based, and the current K1 render loop is running materially faster than the preserved S2/good-state snapshot.

The observed faster look is therefore downstream of the AP boundary. It is not caused by AP values being higher, and the current checked source does not use `VP_WAVEFORM_SHIFT_RATE` for `WAVEFORM-FAST`.

## Key Evidence

### Static source

- `LIGHT_MODE_WAVEFORM_FAST` is mode 7 in `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:67`.
- `render_lightshow_for_channel()` dispatches mode 7 directly to `light_mode_waveform_fast(...)` at `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:253-258`.
- `light_mode_waveform_fast()` has no `dt`, `millis()` delta, `micros()` delta, or sample-chunk speed scaling at `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:1186-1328`.
- In mirrored mode it calls `waveform_shift_upper_half_up(leds_16, 1)` at `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:1310-1312`, then mirrors down at `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:1324-1326`.
- Non-mirrored mode calls `shift_leds_up(leds_16, 1)` at `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:1312-1314`.
- The dt-scaled `VP_WAVEFORM_SHIFT_RATE * dt` path is in `light_mode_waveform_hybrid()`, not `light_mode_waveform_fast()`: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:1457-1581`.
- The LED task is uncapped apart from `vTaskDelay(1)`: render, `show_leds()`, `LED_FPS` update, then delay at `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:517-612`.
- `platformio.ini` selects arduino-esp32 3.2.0 / ESP-IDF 5.4.1 and `fastled/FastLED@3.10.3` at `platformio.ini:18-21` and `platformio.ini:68-71`.
- The repo-local FastLED 3.9.16 tree is disabled as `libraries/_FastLED.disabled`; `.pio/libdeps/k1_hardware/FastLED/library.properties:1-2` resolves the active package as FastLED 3.10.3.

### Live K1 serial evidence on `/dev/cu.usbmodem1101`

Non-persistent serial commands run during this investigation:

- `led_fps`
- `fps`
- `vp_status`
- `dump`
- `secondary_status`
- `vp_perf=start`
- `vp_perf=status`
- `vp_perf=stop`

Relevant live K1 values:

```ini
FIRMWARE_VERSION=40102
CHIP_ID=F887A500
CONFIG.LIGHTSHOW_MODE=7
CONFIG.MIRROR_ENABLED=1
CONFIG.SAMPLE_RATE=12800
CONFIG.SQUARE_ITER=1.00
CONFIG.SAMPLES_PER_CHUNK=96
CONFIG.SENSITIVITY=2.400000
CONFIG.SWEET_SPOT_MIN_LEVEL=299
CONFIG.DC_OFFSET=-4710
SYSTEM_FPS=138.86
LED_FPS=185.69
VP_WAVEFORM_SHIFT_RATE=120.0000
SECONDARY_MODE=3
```

AP stream during the same capture was alive and same-shape enough for this question:

```text
[AP] SSL=299 DC=-4710 max_raw=1108 follower=2868 peak_scaled=0.488 silent_scale=1.000 silence=0
[AP] SSL=299 DC=-4710 max_raw=2434 follower=2027 peak_scaled=0.835 silent_scale=1.000 silence=0
[AP] SSL=299 DC=-4710 max_raw=4338 follower=4256 peak_scaled=0.951 silent_scale=1.000 silence=0
```

`vp_perf` confirmed mode and frame timing:

```text
VPF,ver=1,seq=4,mode=7,smode=3,sec=1,...,show_us=1548/4227,frame_us=3681/5597,over=0,dropped=0,heap=266764
VP_PERF_FRAME: avg=3706 max=5632 over=0 dropped=0
```

Do not use the captured `quant_sec_us` values from this run; they printed impossible huge values and look like a VP perf instrumentation bug or stale accumulator. The `mode`, `show_us`, `frame_us`, `over`, `dropped`, and heap fields were coherent.

### S2 / preserved good-state comparison

The preserved 2026-05-22 perfect dual-channel snapshot has:

```ini
CONFIG.SAMPLE_RATE=12800
CONFIG.SQUARE_ITER=1.00
CONFIG.SAMPLES_PER_CHUNK=96
CONFIG.SENSITIVITY=2.400000
SYSTEM_FPS=48.26
LED_FPS=115.86
VP_WAVEFORM_SHIFT_RATE=120.0000
```

Source: `docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md:25-32`, `:53-54`, and `:93-100`.

K1 current `LED_FPS=185.69` versus preserved S2 `LED_FPS=115.86` implies approximately `1.60x` faster `WAVEFORM-FAST` trail transport, because the mode shifts one LED per render frame.

## Hypotheses

| Hypothesis | Result | Evidence |
|---|---:|---|
| H1: K1 loop runs faster, and `WAVEFORM-FAST` shift accumulates per frame | Confirmed | `lightshow_modes.h:1310-1314`; K1 `LED_FPS=185.69`; S2 snapshot `LED_FPS=115.86` |
| H2: dt is mis-measured inside `WAVEFORM-FAST` | Falsified for this mode | There is no dt path inside `light_mode_waveform_fast()` |
| H3: persisted config drift explains speed | Not supported for the checked knobs | K1 live `SAMPLE_RATE=12800`, `SAMPLES_PER_CHUNK=96`, `SQUARE_ITER=1.00`, `VP_WAVEFORM_SHIFT_RATE=120.0000`; same as preserved snapshot |
| H4: compiler/vectorisation changes pixel math timing | Not needed | Transport speed follows frame count directly; no vectorisation-specific explanation required |
| H5: PSRAM/DRAM placement makes it faster | Not supported | `waveform_history` is not read by `WAVEFORM-FAST`; it is used by hybrid |

## Root Cause Statement

`WAVEFORM-FAST` is a legacy frame-stepped visual mode. The migration/platform state now lets K1 execute the render/show loop faster than the preserved S2 baseline. Because the mode shifts by one LED per render call, visual wall-clock trail speed rises with `LED_FPS`.

This is a latent timing bug exposed by the migration and current driver/runtime behaviour. It is not an AP-to-VP data mismatch. It is not a persisted `VP_WAVEFORM_SHIFT_RATE` drift for mode 7.

## Implication

If the desired product behaviour is wall-clock-stable motion, `WAVEFORM-FAST` needs a dt-scaled transport/fade path like `WAVEFORM_HYBRID`, or the render loop needs an explicit frame-rate contract. The cleaner local fix is mode-local dt scaling, because it preserves the higher K1 frame budget for modes that benefit from smoother rendering.

Do not implement that fix without a separate code-change task and runtime visual validation, because changing `WAVEFORM-FAST` will intentionally slow the visible trail from current K1 behaviour back toward the S2/good-state wall-clock speed.
