# FRTOS-03 — Core-1 render path and capacity evidence

**Audit point:** repository `main` at `8026807fe9d5`, inspected 2026-08-15.
**Decision verdict:** **NOT_VERIFIED** that Core 1 has spare capacity for more work. The execution path is source-verified; current production worst-case timing, CPU utilisation, stack margin, RMT interrupt cost and deadline margin are not.

## Production topology

`k1_hardware` puts the Arduino audio loop on Core 0 and `led_task` on Core 1 (`platformio.ini:59-68`). `led_task` is created with an 8192-byte stack at `tskIDLE_PRIORITY + 1` (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:721-752`). The production environment explicitly does **not** define `K1_EFFECT_FRAMEWORK_V1` or include the framework translation units (`platformio.ini:1271-1274`), so the shipping dispatcher is the legacy path, not the optional framework/registry path.

No production call to `uxTaskGetStackHighWaterMark()`, `vTaskGetRunTimeStats()` or `vTaskDelayUntil()` was found. The 8192-byte stack and any claim about Core-1 utilisation therefore have no current empirical margin evidence in this checkout.

## Exact audio snapshot to final LED path

```text
Core 0 audio frame
  k1_audio_snapshot_update()
    construct K1AudioSnapshot, including 80-bin spectrum under K1_ONSET_V2
    portENTER_CRITICAL -> whole-struct publish -> portEXIT_CRITICAL
                         |
                         | synchronous shared-value copy; no FreeRTOS queue
                         v
Core 1 led_task (priority idle+1)
  WDT reset
  effect-queue frame tick (volatile request flag; not a FreeRTOS Queue)
  smooth spectrogram + chromagram
  optional director/hooks snapshot + onset read
  render primary into shared leds_16[]
  optional primary transition: second effect render + blend
  snapshot primary buffer/runtime
  render secondary sequentially through the same leds_16[] scratch
  optional secondary transition: second effect render + blend
  store secondary -> EdgeMixer secondary -> clip
  restore primary/runtime -> optional EdgeMixer primary -> clip
  show_leds()
    primary brightness/colour/UI/precomp/clip/scale
    secondary colour/scale/brightness/quantise/reverse
    primary quantise/reverse
    FastLED.show() for both registered RMT5 controllers
  frame accounting
  vTaskDelay(1)
```

### Cross-core handoff

`k1_audio_snapshot_update()` builds the snapshot then publishes the complete struct inside a `portMUX` critical section; `k1_audio_snapshot_read()` copies the complete struct under the same critical section (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp:28-121,124-129`). This is not a queue or notification. With production `K1_ONSET_V2`, the copied object contains the 80-bin spectrum (`SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp:63-73`); the critical-section duration is not instrumented.

The SmartDirector/hooks branch reads one snapshot and onset event at `SPECTRASYNQ_K1_FIRMWARE.ino:1264-1277`. The optional non-production framework reads again per rendered channel (`SPECTRASYNQ_K1_FIRMWARE.ino:418-480`), and several legacy effects also call `k1_audio_snapshot_read()` themselves. Snapshot acquisition is therefore decentralised; a frame is not guaranteed to use one coherent, single-read audio view across all consumers.

### Frame transitions and effects

At frame top, Core 1 consumes effect commit requests and advances both channel transitions (`SPECTRASYNQ_K1_FIRMWARE/control/k1_effect_queue.cpp:585-613`). Despite its name, the effect queue uses a request flag written last (`control/k1_effect_queue.cpp:505-508`), not a FreeRTOS queue; its cross-core ordering and race margin are not proved by an atomic or `portMUX` boundary.

The primary effect is selected/rendered at `.ino:1231-1306`. An active crossfade snapshots the outgoing buffer, renders the incoming effect a second time, then blends all 160 logical pixels (`.ino:491-565`). Both channels can crossfade, so a worst-case frame can perform four effect renders plus two blends. No current evidence run exercises that worst case across the enabled roster.

### Dual-edge composition

Secondary rendering is deliberately sequential and stateful. Core 1 snapshots global render runtime and the primary `leds_16[]`, renders secondary through that same shared buffer, stores/EdgeMixes/clips it, then restores primary state and optionally applies the primary EdgeMixer (`.ino:1328-1426`). This makes naive parallel render tasks unsafe: `leds_16[]`, runtime globals, transition temp-application and the render-parameter stack are shared mutation surfaces.

### Final colour and wire output

`show_leds()` performs primary brightness/colour/UI/precomp/clip/scale, transforms and quantises secondary first, quantises primary, then calls `FastLED.show()` (`SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:953-1072,1074-1207`). FastLED 3.10.3 is pinned (`platformio.ini:218-220`; installed package `.pio/libdeps/k1_hardware/FastLED/library.json:41`).

The installed ESP32 RMT5 backend defaults to `DMA_AUTO` (`.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/idf5_clockless_rmt_esp32.h:27-33`) but explicitly resolves AUTO to `with_dma = false` because “DMA is buggy on ESP32S3” (`.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/strip_rmt.cpp:82-89`). It loads each pixel through `setPixel()` and starts `drawAsync()` (`.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/idf5_rmt.cpp:51-88`). A subsequent draw on the same controller waits for the prior asynchronous refresh (`strip_rmt.cpp:112-130`). Therefore the current path is **RMT5 asynchronous, non-DMA on ESP32-S3**, not “RMT5 DMA”. `FastLED.show()` timing can include pixel packing/setup and a prior-transfer wait, while returning before the current wire transfer completes; it is not by itself a full CPU-load or wire-completion measurement.

## Scheduling, WDT and pacing

Production enables `K1_AUDIO_FREEZE_GUARD_V1` (`platformio.ini:149-154`). Core 1 subscribes itself to the task watchdog and resets it once per frame (`.ino:1107-1115`); the watchdog timeout is defined as 5000 ms and applied at boot (`.ino:27-29,754-764`). This detects a multi-second freeze, not an 8.333 ms render deadline miss or high utilisation.

The shipping loop records its frame, calls `show_leds()`, updates an EMA FPS, then executes unconditional `vTaskDelay(1)` (`.ino:1447-1467`). The installed ESP32-S3 Arduino SDK resolves `configTICK_RATE_HZ` to `CONFIG_FREERTOS_HZ=1000` (`/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/sdkconfig:2338-2343`; `.../FreeRTOSConfig.h:91-94`), so one tick is nominally 1 ms. This is still a relative one-tick block, not a fixed 1 ms frame period: it has tick-phase and ready-list jitter and accumulates render-time drift. There is no `vTaskDelayUntil()`, absolute deadline or explicit frame-drop/backpressure. The intended visual cadence also needs one authoritative semantic definition before any scheduler change: source budgets name 8333 us/120 Hz (`system/constants.h:200-202`), while adjacent project prose still says 100 FPS.

## Instrumentation and actual capacity evidence

`ENABLE_VP_PERF_AUDIT` defaults off in production (`system/constants.h:176-202`) and is enabled in non-shippable probe environments such as `k1_bench_im69d_ap_integrity_probe` (`platformio.ini:340-362`). MabuTrace render scopes are confined to the non-shippable `k1_hardware_trace_dev` environment (`platformio.ini:860-873`). The always-present `vp_render_us_*` interval stops before `show_leds()` (`.ino:1447-1457`) and therefore cannot prove whole-frame margin.

Historical hardware logs show both apparent typical slack and real outliers:

- Mode 18 music, 2026-06-07: final sample `frame_us=3972/5552`, `show_us=3038/4620`, `over=0`, `dropped=0` (`docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-music.raw.log:145`).
- Mode 18 smoke, 2026-06-07: `frame_us=4024/40560`, `show_us=3092/38338`, `over=1`, `dropped=3` (`docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-smoke.raw.log:152`).
- Mode 22 wireless-on, 2026-06-11: `frame_us=3959/5098`, `show_us=2458/3705`, `over=0`, `dropped=0` (`docs/forensics/runtime-evidence/wireless-ab/20260611/on_1.log:478`).
- Mode 22 wireless-off, 2026-06-11: `frame_us=3944/39976`, `show_us=2557/37450`, `over=1`, `dropped=3` (`docs/forensics/runtime-evidence/wireless-ab/20260611/off_1.log:462`).

Those samples do **not** establish current spare capacity. They predate substantial render-path changes through August (dual-edge transforms, STM/EdgeMixer work, Mode 32, colour-pipeline and geometry changes), cover only two effect pairings, do not measure all enabled modes or simultaneous two-channel crossfades, do not expose task runtime percentage/ISR cost/stack watermarks, and sometimes contain 38–40 ms show/frame stalls.

## Decision

1. **Do not place additional work on Core 1 based on nominal FPS or the old typical 4 ms samples.** Spare capacity is NOT_VERIFIED.
2. **Do not split primary/secondary/effect stages into parallel FreeRTOS tasks.** The current sequential shared-state design would require a prior ownership redesign and adds synchronisation/jitter risk.
3. **A periodic `vTaskDelayUntil()`/deadline-driven render loop may improve scheduling determinism**, but this is only a candidate after the product cadence is resolved and current end-to-end evidence exists. It cannot create compute capacity and may expose asynchronous RMT overlap assumptions.
4. **Measure before changing scheduling:** current production-equivalent flags; all enabled primary/secondary pairs; simultaneous crossfades; EdgeMixer/STM worst cases; whole-frame and `FastLED.show()` distributions; actual RMT completion/ISR burden; task runtime share; Core-1 ready-list interference; and `led_task` stack high-water mark.

## Evidence gaps

- No current August production-equivalent on-device Core-1 trace.
- No p50/p95/p99/max whole-frame distribution across all enabled modes and dual-channel crossfades.
- No task runtime percentage, ready/running/blocking timeline, or RMT ISR CPU attribution.
- No `led_task` stack high-water mark or stack-overflow soak evidence.
- No measured audio-to-final-wire latency tied to the same frame identity.
- No authoritative 100-versus-120 FPS contract; the installed SDK tick is resolved at 1 kHz.
- No proof that effect-queue volatile request publication is race-free across cores.

## Read-only rerun commands

```bash
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
git rev-parse --short=12 HEAD
/opt/homebrew/bin/rg -n 'xTaskCreatePinnedToCore|k1_audio_snapshot_read|k1_effect_queue_frame_tick|render_queue_xfade_overlay|show_leds\(|FastLED\.show|vTaskDelay\(1\)' SPECTRASYNQ_K1_FIRMWARE
/opt/homebrew/bin/rg -n 'uxTaskGetStackHighWaterMark|vTaskGetRunTimeStats|vTaskDelayUntil|ENABLE_VP_PERF_AUDIT|FEATURE_TRACE_RENDER' SPECTRASYNQ_K1_FIRMWARE platformio.ini
nl -ba .pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/strip_rmt.cpp | sed -n '75,135p'
/opt/homebrew/bin/rg -n 'CONFIG_FREERTOS_HZ' /Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/sdkconfig
/opt/homebrew/bin/rg -n 'VPF.*(frame_us|show_us)' docs/forensics/runtime-evidence/2026-06-07-vpab-frame-mode18-1401-{music,smoke}.raw.log docs/forensics/runtime-evidence/wireless-ab/20260611/{on_1,off_1}.log | tail -20
```

An on-device capacity campaign is the necessary next proof step, but it was forbidden by this read-only SSA brief; no device, serial, flash or upload action was performed.
