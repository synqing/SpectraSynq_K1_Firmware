# FRTOS-19 — FastLED 3.10.3 RMT5 completion and buffer-lifetime research

**Date:** 2026-08-15  
**Scope:** read-only source research; no build, test, device, serial, web or Git action  
**Target:** default `k1_hardware`, ESP32-S3, two WS2812B controllers, 160 pixels per controller  
**Evidence class:** current repository source, materialised `.pio` FastLED 3.10.3 source, and the locally installed ESP-IDF 5.4.1 public headers

## Verdict

1. **`FastLED.show()` returns before the newly submitted RMT transmissions physically complete.** It copies/scales each application buffer into a separate FastLED/led-strip pixel buffer, then submits each controller asynchronously and returns.
2. **The prior transfer is waited only on the next submission for that same controller, not at the end of the current `show()`.** In FastLED 3.10.3 the wait is in `RmtStrip::drawAsync()`.
3. **There is a real internal-buffer lifetime defect in the installed backend.** On the next `FastLED.show()`, `CFastLED::show()` invokes every controller's `showLedsInternal()` before any controller's `endShowLeds()`. RMT5 loads new pixels during `showLedsInternal()`, but does not wait for the old transfer until `endShowLeds()` later calls `drawAsync()`. The ESP-IDF 5.4.1 API explicitly forbids modifying the RMT payload until transmission finishes. FastLED's own base-class comment says an async controller should wait in `beginShowLeds()`; this RMT5 controller does not override it.
4. **The K1 application buffers are not the unsafe payload.** `leds_out[]` and `leds_out_secondary[]` are synchronously read and copied into separate, internally allocated led-strip buffers before RMT submission. Core 1 may render the next frame into the application buffers after `FastLED.show()` returns. It is FastLED's internal `pixel_buf` that can be rewritten too early.
5. **The two controllers overlap in time on distinct RMT TX channels, but are not synchronised to the same hardware start edge.** FastLED submits them serially in controller-list order. The ESP32-S3 has four TX-capable RMT channels and hardware TX synchronisation, but FastLED 3.10.3 neither creates nor uses an RMT sync manager here.
6. **At 120 FPS, two 160-pixel strips fit on the wire only because they overlap.** Each channel occupies approximately `160 * 24 * 1.25 us + 280 us = 5,080 us`. Against an 8,333.33 us frame period that is 60.96% wire occupancy and leaves about 3,253 us between completion and the next same-channel submission under genuinely periodic 120 FPS pacing. Serialising the two strips would take about 10,160 us and cannot sustain 120 FPS.
7. **Recommended smallest completion oracle:** a dev-trace-only, source-controlled linker interposer around `rmt_new_tx_channel()` and `rmt_transmit()`, restricted to the two known LED GPIOs. It registers the official `on_trans_done` ISR callback and records fixed-size, static per-channel records using `esp_timer_get_time()`. It adds no heap, logging, queue send or wait to effect/render code. A source-controlled local FastLED fork is the more explicit fallback if linker interposition cannot be proven by the link map and fault battery.

## 1. Exact selected stack and K1 show path

### Toolchain and driver selection

- `platformio.ini:1-5,14-22,218-221` selects `k1_hardware`, pioarduino `54.03.20`, ESP32-S3 Arduino, and pins `fastled/FastLED@3.10.3`.
- `.pio/libdeps/k1_hardware/FastLED/library.json:1-3,37-46` confirms the materialised library is FastLED `3.10.3`.
- The installed target header reports ESP-IDF `5.4.1`: `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/include/esp_common/include/esp_idf_version.h:13-34`.
- `.pio/libdeps/k1_hardware/FastLED/src/third_party/espressif/led_strip/src/enabled.h:27-30,54-69` selects RMT5 for ESP32-S3 on IDF 5+.
- `.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/idf5_clockless_rmt_esp32.h:27-34` selects `DMA_AUTO`; `.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/strip_rmt.cpp:79-90` resolves AUTO to `with_dma=false` because the local FastLED source marks DMA buggy on ESP32-S3.

This is therefore **RMT5 without DMA**. The presence of `FASTLED_RMT_USE_DMA` at `idf5_clockless_rmt_esp32.h:6` does not override the actual `DMA_AUTO -> false` runtime choice.

### K1 controllers and geometry

- `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h:123-140,166-176` makes the default K1 geometry 160 primary + 160 secondary. Unit 2's separate flag is 206 + 206 and is not selected by default `k1_hardware`.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals_config.cpp:96-99` installs `LED_COUNT_VALUE` into `CONFIG.LED_COUNT`.
- `SPECTRASYNQ_K1_FIRMWARE/system/constants.h:419-427` assigns default production LED GPIOs 6 and 7.
- `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:1073-1092` maps the secondary data output to `LED_CLOCK_PIN`, hence GPIO 7.
- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1230-1246` allocates primary output storage at initialisation and registers one WS2812B controller on GPIO 6.
- `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:2416-2425` allocates secondary output storage and registers the second WS2812B controller on GPIO 7.
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:687-719` enables the secondary channel and calls the first two-controller `FastLED.show()` before starting `led_task`.
- The canonical per-frame path ends at `show_leds()` -> `FastLED.show()` in `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1194-1207`. The Core-1 render task calls it at `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:1447-1467`, then uses `vTaskDelay(1)`; the present loop is free-running, not an absolute 120 FPS release loop.

## 2. Exact call sequence and completion semantics

The current call path is:

```text
show_leds()
  -> FastLED.show()
     -> CFastLED::show(scale)
        -> every controller: beginShowLeds()            [no RMT5 override]
        -> every controller: showLedsInternal(scale)
           -> ClocklessController::showPixels()
              -> RmtController5::loadPixelData()
                 -> led_strip_set_pixel() x pixel count
        -> every controller: endShowLeds()
           -> RmtController5::showPixels()
              -> RmtStrip::drawAsync()
                 -> if old draw issued: waitDone()
                 -> led_strip_refresh_async()
                    -> rmt_enable()
                    -> rmt_transmit()
        -> return to K1 while new transfers remain active
```

Source proof:

- `.pio/libdeps/k1_hardware/FastLED/src/FastLED.cpp:131-181` is the three-pass `CFastLED::show()` implementation: all begins, then all `showLedsInternal()`, then all ends. There is no final controller completion wait.
- `.pio/libdeps/k1_hardware/FastLED/src/cpixel_ledcontroller.h:42-54` makes `showLedsInternal()` call the controller's `showPixels()`.
- `.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/idf5_clockless_rmt_esp32.h:43-54` makes `showPixels()` load data and `endShowLeds()` submit it.
- `.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/idf5_rmt.cpp:51-88` copies/scales all pixels with `setPixel()` and makes `showPixels()` call `drawAsync()`.
- `.pio/libdeps/k1_hardware/FastLED/src/platforms/esp/32/rmt_5/strip_rmt.cpp:112-130` waits for an old draw only immediately before submitting the new draw. Its wait calls `led_strip_refresh_wait_done()`.
- `.pio/libdeps/k1_hardware/FastLED/src/third_party/espressif/led_strip/src/led_strip_rmt_dev.c:98-120` implements async refresh as `rmt_enable()` + `rmt_transmit()` and implements completion wait as `rmt_tx_wait_all_done(..., -1)` + `rmt_disable()`.
- The exact installed IDF 5.4.1 declaration states that `rmt_transmit()` constructs a descriptor and pushes it to a queue, may return quickly, and that its payload **cannot be modified until transmission is finished**: `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/include/esp_driver_rmt/include/driver/rmt_tx.h:87-109`.
- That header also states `rmt_tx_wait_all_done(..., -1)` can block forever: the same file at `:111-125`. FastLED uses exactly `-1`; this violates the project's general “never block indefinitely” peripheral-driver rule even though a finite 160-pixel transaction should ordinarily finish.

### What the existing `show_us` really measures

`SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:1200-1207` brackets `FastLED.show()` and records that duration. It contains:

- both application-to-internal-buffer copies/scales;
- controller bookkeeping;
- immediate completion reaping for an already-finished prior transfer;
- any blocking remainder of an unfinished prior transfer;
- submission of both new transfers.

It does **not** contain the newly submitted transfers' full wire time and cannot be relabelled `rmt_complete_us`.

## 3. Buffer ownership and the early-rewrite defect

There are two distinct buffer layers.

### Layer A — K1 application buffers: safe to rewrite after return

`leds_out` and `leds_out_secondary` are the buffers registered with FastLED (`led_utilities.h:1233-1245,2416-2422`). During `CFastLED::show()` the RMT5 controller synchronously iterates over these buffers, scales/dithers each pixel, and calls `led_strip_set_pixel()` (`idf5_rmt.cpp:51-82`). After this loop finishes, RMT no longer refers to the K1 application pointer.

The led-strip backend owns a different `pixel_buf`. Because FastLED passes no external buffer, `led_strip_rmt_dev.c:143-182` allocates the internal `max_leds * bytes_per_pixel` buffer during the first show. `led_strip_rmt_set_pixel()` writes that internal buffer at `:61-77`.

**Conclusion:** the Core-1 effect/render pipeline may start rewriting K1's application output buffers after `FastLED.show()` returns. No application-side double buffer is required merely to protect the active RMT transfer.

### Layer B — FastLED internal `pixel_buf`: not safely protected

The next `CFastLED::show()` runs the load pass before the end/submit pass. Therefore `RmtController5::loadPixelData()` begins overwriting the internal `pixel_buf` before `RmtStrip::drawAsync()` checks `mDrawIssued` and waits for the old transfer.

This contradicts both:

- IDF 5.4.1's payload lifetime rule (`rmt_tx.h:94-96`); and
- FastLED's own async-controller contract in `.pio/libdeps/k1_hardware/FastLED/src/cled_controller.h:222-235`, which says `beginShowLeds()` should be the sync point that blocks until the prior frame completes.

The RMT5 `ClocklessController` overrides `endShowLeds()` but not `beginShowLeds()` (`idf5_clockless_rmt_esp32.h:37-54`). The old transfer wait is thus one phase too late.

The hazard is not theoretical copying into a fully buffered peripheral. The backend is non-DMA, leaves `mem_block_symbols=0` so the target default applies (`strip_rmt.cpp:39-65`), and the ESP32-S3 has only 48 RMT words per channel (`.../soc/esp32s3/include/soc/soc_caps.h:274-290`). A 160-pixel RGB transfer needs 3,840 data symbols, so the encoder necessarily continues reading the retained payload through RMT refill interrupts. The local encoder passes `primary_data` to the bytes encoder and yields on memory-full at `.pio/libdeps/k1_hardware/FastLED/src/third_party/espressif/led_strip/src/led_strip_rmt_encoder.c:30-64`.

**Failure mode:** if the next `FastLED.show()` starts loading a controller less than about 5.08 ms after its prior submission, the still-active prior transmission can read a mixture of old and new internal pixel bytes. The subsequent wait prevents two RMT transactions on one controller from overlapping; it does not undo payload corruption that happened before the wait.

This must be treated as a source-level defect to falsify on device, not as a claim that visible tearing has already been observed.

## 4. Two-controller concurrency

Controller objects join FastLED's linked list in construction order (`.pio/libdeps/k1_hardware/FastLED/src/cled_controller.cpp:14-20`). K1 registers the primary controller before the secondary. `CFastLED::show()` then calls the primary `endShowLeds()` and secondary `endShowLeds()` serially (`FastLED.cpp:158-175`). Each `RmtStrip` independently creates a led-strip RMT device, which independently calls `rmt_new_tx_channel()` (`strip_rmt.cpp:68-90`; `led_strip_rmt_dev.c:195-211`).

The first controller begins transmitting before the second controller is submitted, and both remain in flight after the second submission. They therefore **overlap/operate in parallel**, subject to a software submission skew. They are not phase-aligned at the first bit:

- the installed IDF exposes `rmt_new_sync_manager()` specifically to make multiple enabled TX channels start together (`.../driver/rmt_tx.h:63-69,144-160`);
- ESP32-S3 reports four TX-capable channels and TX-sync support (`soc_caps.h:274-290`);
- no FastLED RMT5 source in the active call path calls `rmt_new_sync_manager()` or `rmt_sync_reset()`.

For equal 160-pixel channels, completion times should differ roughly by the submission skew, but only completion callbacks can measure it. “Parallel” must not be restated as “simultaneous” or “synchronised”.

## 5. 120 FPS implications for two 160-pixel strips

FastLED defines WS2812 timing as `T1=250 ns`, `T2=625 ns`, `T3=375 ns`, total `1,250 ns/bit`, at `.pio/libdeps/k1_hardware/FastLED/src/chipsets.h:1048-1069`. RMT5 converts those control points to `T0H/T0L/T1H/T1L` (`.pio/libdeps/k1_hardware/FastLED/src/fl/convert.h:6-15`) and explicitly adds a 280 us reset when it creates the strip (`idf5_rmt.cpp:51-59`). The reset symbol is part of the encoded transaction (`led_strip_rmt_encoder.c:30-64,135-175`), so the official TX-done callback occurs after the latch/reset interval, not merely after the last RGB bit.

Per channel:

```text
RGB data       = 160 px * 24 bits/px * 1.25 us/bit = 4,800 us
reset/latch    =                                         280 us
wire complete  =                                       5,080 us
120 FPS period =                                    8,333.33 us
nominal margin =                                    3,253.33 us
wire occupancy = 5,080 / 8,333.33 =                     60.96%
```

Consequences:

- Parallel RMT output makes 120 FPS physically feasible for the default geometry; sequential output does not.
- `FastLED.show()` CPU time and wire time are not additive in the ordinary case. CPU can render while RMT transmits, but non-DMA refill ISR work continues during that interval; “CPU idle during output” is false.
- At exact periodic 120 FPS, the same controller should not need to block on the prior 5.08 ms transfer. A nonzero prior-wait duration is evidence of release jitter, overrun, interrupt starvation, or a changed strip/timing contract.
- Current free-running pacing can call `show()` earlier than 5.08 ms. The existing one-tick delay alone does not protect the internal payload lifetime.
- A 120 FPS deadline must be evaluated with at least: VP start-to-start period, CPU render/prep/show-submit time, per-controller submit timestamp, per-controller completion timestamp, completion skew, prior-wait count/duration, and dropped/late frames.
- If the product endpoint is `rmt_complete_us`, a sub-8 ms audio-to-visual contract leaves only about 2.92 ms from its chosen audio origin to RMT submission before the fixed 5.08 ms wire interval. This arithmetic makes the exact origin semantics and physical measurement indispensable.
- Unit 2's 206-pixel geometry would take approximately `206 * 30 us + 280 us = 6.46 ms` per channel, leaving only about 1.87 ms at 120 FPS. That is outside this default-target conclusion and needs its own capacity gate.

## 6. Completion instrumentation candidates

### Candidate A — recommended smallest: source-controlled linker interposer

Add a scheduling-trace-only source module plus two linker wrap flags:

```text
--wrap=rmt_new_tx_channel
--wrap=rmt_transmit
```

The source module should:

1. In `__wrap_rmt_new_tx_channel`, call `__real_rmt_new_tx_channel`, then recognise only the exact K1 LED GPIOs from the passed `rmt_tx_channel_config_t` (GPIO 6/7 for default production; bind from compile-time pin constants, never magic-port identity). Assign the returned channel handle to one of two fixed static channel slots.
2. Register one `IRAM_ATTR` `on_trans_done` callback with `rmt_tx_register_event_callbacks()` for each recognised handle. The exact IDF 5.4.1 API states the callback runs in ISR context and means “transmission is finished” (`rmt_tx.h:19-27,127-142`). `rmt_tx_done_event_data_t` also provides `num_symbols`, including EOF (`rmt_types.h:34-51`).
3. Immediately before `FastLED.show()`, let Core 1 publish the immutable VP/frame generation and final-byte identity to a fixed static “next submission” record. This is one bounded POD write, not effect work.
4. In `__wrap_rmt_transmit`, match the channel handle, record `rmt_submit_us` immediately before `__real_rmt_transmit`, and snapshot the pending frame identity into that channel's single in-flight slot. The timestamp definition must be **entry to accepted submission call**, not `FastLED.show()` entry/return. Preserve and check the real API return value.
5. In the ISR completion callback, call `esp_timer_get_time()` and append `{channel, frame_generation, rmt_submit_us, rmt_complete_us, num_symbols}` to a **fixed-size internal-SRAM ring**. Return `false`; do not wake a task. Each channel should have its own single-writer ring or slot so simultaneous controller callbacks never become multiwriter corruption.
6. Commit a record with a 32-bit sequence written last. Because a 64-bit timestamp is not assumed atomic on Xtensa LX7, the deferred reader must use a sequence/commit protocol and count overwrite/drop/corrupt records. Do not solve this with a mutex in the ISR.
7. Drain/serialise only after capture or from an existing bounded diagnostic owner. For the required causal lane, merge these same-clock records with MabuTrace output offline; do not print from the ISR or `show_leds()`.
8. Fail closed at initialisation if there are not exactly two recognised LED handles, callback registration fails, a handle is duplicated, the ring overflows, a completion has no matching submit, or a submit overwrites an in-flight identity.

Why this is smallest and still source-controlled:

- no edit to generated `.pio/libdeps`;
- no private FastLED type access;
- uses only stable public IDF 5.4.1 APIs already present locally;
- no heap or blocking added to render/effect code;
- exact TX-done ISR boundary rather than a timer estimate;
- the wrapper can be compiled only into a new non-shippable scheduling trace environment, preserving the production instrumentation boundary.

Production-safety qualification is still required before device use: the link map must prove both FastLED calls resolve to the wrappers; a host/static fault battery must reject missing wraps, wrong GPIOs and missing callbacks; paired minimally instrumented/device-trace runs must bound overhead; and the callback/ring must be proven IRAM/internal-RAM compatible. If any of those fail, Candidate A is rejected rather than silently degrading to `show_us`.

### Candidate B — fallback / long-term explicit fix: source-controlled local FastLED 3.10.3 fork

Pin a repository-owned local FastLED 3.10.3 fork instead of the registry package, with a minimal audited patch that:

- exposes or registers the RMT TX-done callback at `led_strip_rmt_dev.c` channel creation;
- records the same static submit/completion records;
- moves prior-transfer synchronisation to `ClocklessController::beginShowLeds()` or otherwise calls `waitDone()` **before** `loadPixelData()` touches the internal buffer;
- replaces the unbounded `rmt_tx_wait_all_done(..., -1)` with a finite, geometry-derived timeout and explicit fatal/degraded error stance;
- remains non-DMA unless a separate ESP32-S3 DMA gate proves the driver safe.

Candidate B is more maintainable and can fix the lifetime defect rather than merely observe it, but vendoring/forking the complete dependency is a materially larger source and update burden. It should be chosen if the linker wrapper cannot be independently proven or if the buffer-lifetime correction is authorised in the same lane.

## 7. Unsafe or insufficient instrumentation rejected

| Proposal | Disposition | Reason |
|---|---|---|
| Rename existing `show_us` to completion | **REJECT** | `FastLED.show()` returns after submission, before current transfer completion. |
| Timestamp immediately after `FastLED.show()` | **REJECT as completion** | Useful only as an upper bound on final controller submission/CPU return; not TX done. |
| Use the next `FastLED.show()` return or prior wait return | **REJECT as exact completion** | It can be arbitrarily later than physical completion and occurs after the unsafe internal-buffer rewrite. |
| Sleep/delay 5.08 ms after `show()` | **REJECT** | An estimate is not confirmation; it blocks Core 1 and converts parallel wire time into frame time. |
| Busy-poll `isDrawing()` or an RMT status bit in render | **REJECT** | Burns CPU, perturbs scheduling, and FastLED does not expose the private strip/controller state. |
| Print/log/trace-format directly in `on_trans_done` | **REJECT** | ISR callback; formatted output can block/allocate and destroys the measurement. |
| Allocate a queue/ring on first render frame | **REJECT** | Heap in the hot path and non-deterministic first-use cost. Allocate/fix storage at compile time. |
| `xQueueSendFromISR` for every completion | **REJECT as smallest design** | Legal if bounded and pre-created, but unnecessarily wakes/schedules a consumer at 240 events/s. A static ring plus deferred drain is less perturbing. |
| GPIO low-level sampling | **REJECT** | WS2812 zeros and the reset interval are also low; GPIO level alone does not identify transaction completion. |
| Application `leds_out` double buffering only | **REJECT as lifetime fix** | RMT uses FastLED's separate internal `pixel_buf`; application double buffering does not stop that internal buffer being rewritten before wait. |
| Enable RMT DMA to avoid refill reads | **REJECT without separate gate** | The installed FastLED 3.10.3 explicitly disables AUTO DMA on ESP32-S3 as buggy. |
| Edit `.pio/libdeps` in place | **REJECT** | Generated, non-source-controlled, and lost on dependency resolution. |

## 8. Unverified boundaries and next mechanical proof

This research establishes source semantics, not current-device timing. It does not prove:

- actual submit-to-complete p50/p95/p99/max;
- controller start/completion skew;
- whether current free-running frames have already torn the internal RMT payload;
- RMT refill ISR CPU percentage;
- 120 FPS across every enabled dual-channel/crossfade mode;
- acoustic-to-photon latency.

The next mechanical step is **not** to infer completion from current `show_us`. It is to implement Candidate A in the non-shippable scheduling trace lane, add a fail-closed static/link-map/fault battery, and then run a Captain-authorised, identity-verified paired device trace. A decisive lifetime falsification should alternate high-contrast old/new byte patterns while sweeping inter-submit intervals across 5.08 ms, and correlate final-byte identity, submit, TX-done, and captured physical output. The lifetime fix itself is a separate authorised production change.

## 9. Commands run

Only read/search commands were used. No build, test, device, serial, web or Git command was run.

```text
sed -n ... docs/agent/AGENT_EXECUTION_STANDARD.md AGENT_OS.md .claude/CLAUDE.md
sed -n ... /Users/spectrasynq/.codex/skills/esp32-render-path-safety/SKILL.md
rg -n ... platformio.ini SPECTRASYNQ_K1_FIRMWARE .pio/libdeps/k1_hardware/FastLED/src
find .pio/libdeps/k1_hardware/FastLED/src ...
find /Users/spectrasynq/.platformio/packages ... driver/rmt_tx.h ...
nl -ba ... | sed -n ...
```

No validation command was permitted or performed. All conclusions above are bounded to the exact local sources cited.
