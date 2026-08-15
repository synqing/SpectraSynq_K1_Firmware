# FRTOS-01 — current task, callback, ISR, and poller topology

**Audit snapshot:** `main` at `8026807fe9d501720fe0c835f2b0dad077437d76` on 2026-08-15.  This is a static source audit only: no device was touched, and no runtime task-list or stack-high-water telemetry was collected.  The checkout was already dirty with concurrent audit artefacts, so this file cites live source rather than historical line references.

## Verdict

**CONTRADICTORY.**  The production application topology is source-verifiable, but the architecture narrative overstates its scheduling semantics.  `k1_hardware` has two application tasks, not a deployed `AudioActor -> ControlBus -> RendererActor` scheduler: Arduino `loopTask` runs the whole audio/control path on Core 0 and `led_task` runs the visual path on Core 1. Both are priority 1 with declared 8192-byte stacks. Neither uses `vTaskDelayUntil()` nor an explicit deadline. The AP loop is nominally hardware-paced by 96 samples at 12.8 kHz (133.333 Hz) and then yields one tick; the renderer is free-running as `work + show_leds() + vTaskDelay(1)`. Therefore the documented 133 Hz / approximately 100 FPS values are rates or targets, not FreeRTOS schedule contracts.

The in-source call-site comment that tempo “self-clocks to 50 Hz” is directly false: the tempo module emits every third nominal AP frame, 44.444 Hz. The `AGENTS.md` statement that Core 0 has “no blocking calls” is also false for the shipping build: `acquire_sample_chunk()` performs a blocking I2S read, bounded to 100 ms by the production freeze guard.

## Source-of-truth build selection

| Fact | Live evidence | Consequence |
|---|---|---|
| Shipping/default environment | `platformio.ini:14-18` selects `k1_hardware`. | “Current” below means this environment unless a row is explicitly marked gated. |
| Compiled application sources | `platformio.ini:32-44` includes the sketch, system, visual, effects, audio, director, control, and serial sources; it does **not** include `network/*.cpp`. | Wireless/BLE/sync tasks and callbacks are absent from the production image. |
| Application core map | `platformio.ini:59-68` removes the framework Core-1 default, defines `ARDUINO_RUNNING_CORE=0`, and defines `K1_LED_TASK_CORE=1`. | Audio/control `loopTask` is Core 0; `led_task` is Core 1. |
| AP nominal timing | `platformio.ini:74-77` defines 12,800 samples/s, 96 samples/chunk, tempo decimation 3. | Nominal AP chunk period = 7.5 ms = 133.333 Hz; tempo emit = 44.444 Hz. |
| Shipping bounded read | `platformio.ini:149-154` enables `K1_AUDIO_FREEZE_GUARD_V1`. | I2S block is finite but can be as long as 100 ms on a DMA/microphone failure. |
| Production hardware poller compile-outs | `system/constants.h:204-225` disables ROTATE8 and custom USB MSC on K1 hardware; `system/constants.h:445-455` sets both button pins and sweet-spot pins to `-1`. | Encoder, physical-button, sweet-spot GPIO, and TinyUSB MSC callback work is absent/no-op in `k1_hardware`. |

## Production application tasks

Stack values are the ESP-IDF byte arguments passed to task creation. Cadence is source semantics, not a claim of measured runtime frequency.

| Task / owner | Core | Priority | Declared stack | Cadence and work | Blocking / yield semantics | Evidence |
|---|---:|---:|---:|---|---|---|
| Arduino `loopTask` (AP/audio + controls) | 0 | 1 | 8192 B | Framework calls `setup()` once, then calls repository `loop()` forever. Every iteration performs control pollers, one audio acquisition, GDFT/VU/novelty/snapshot/onset/saliency, tempo update, colour shift, and diagnostics. Nominally paced by one 96-sample DMA chunk at 12.8 kHz, not by an RTOS deadline. | `i2s_channel_read()` blocks until a chunk or the shipping 100 ms timeout, then the loop calls `vTaskDelay(1)`. With the 1 kHz RTOS tick this is a one-tick yield. No `vTaskDelayUntil()`, deadline, overrun skip, or priority elevation. | Arduino main: `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/cores/esp32/main.cpp:15-20,39-40,47-78,103-105`; core flags `platformio.ini:59-68`; loop call graph `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:791-1082`; I2S wait `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:86-88,406-482`; tick rate `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/qio_opi/include/sdkconfig.h:1109`. |
| `led_task` / `led_thread` (VP/render) | 1 | 1 | 8192 B | Created once after boot animation. Each loop consumes transition/effect state, smooths audio-derived surfaces, renders primary and secondary channels, transforms/clips, calls `show_leds()`, and records an EMA of achieved FPS. It is **free-running**; no 10 ms/100 Hz regulator exists. | Normal and probe branches end in `vTaskDelay(1)`. Flash-park logic exists only under non-production `K1_EFFECT_FRAMEWORK_V1`; production has no render-task blocking primitive in this loop other than work performed by callees and the one-tick delay. | Creation `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:709-723`; body `:1084-1144,1195-1214,1221-1305,1328-1457,1464-1468`; `show_leds()` reaches `FastLED.show()` at `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:953-963,1198-1204`; production does not define framework flag (`platformio.ini:303,593,1296` are other environments only). |

### Production scheduling implications established by source

1. Equal numeric priority does not cause AP/VP time-slicing because the tasks are pinned to different cores. It does mean each application task is the lowest non-idle priority on its own core.
2. Core 0 is not “non-blocking”: DMA acquisition intentionally blocks to pace audio and is bounded at 100 ms (`audio/i2s_audio.h:426-469`). The tail delay exists specifically to give `IDLE0` a slot (`.ino:1079-1081`).
3. “133 Hz audio” is the declared DMA-frame rate. There is no catch-up/drop/deadline scheduler around the AP iteration, so source alone cannot guarantee it under overload.
4. “100 FPS render” is not encoded as a 10 ms schedule. The only explicit delay is one tick after work; `LED_FPS` is measurement only (`.ino:1464-1467`). Source therefore permits a faster rate when work is short and a slower rate when work/show is long.
5. Both tasks are subscribed to the five-second task watchdog in production (`.ino:754-764,1107-1115`), but a watchdog detects gross stalls; it does not enforce the 7.5 ms AP budget or a render cadence.

## Framework/system task services statically implicated

This table is deliberately separated from application-owned tasks. Precompiled ESP-IDF/Arduino components can create additional tasks dynamically; without `uxTaskGetSystemState()`/`vTaskList()` from the exact binary on a device, an exhaustive runtime list is **NOT_VERIFIED**.

| Service | Production presence / trigger | Core | Priority | Stack | Scheduling semantics | Evidence |
|---|---|---:|---:|---:|---|---|
| `IDLE0`, `IDLE1` | FreeRTOS kernel, steady-state | one per core | 0 | 1024 B configured | Run only when no ready task exists on their core. Core-0 idle is task-watchdog checked. | SDK config `.../sdkconfig.h:1027-1031,1112`; max priority/tick config `.../FreeRTOSConfig.h:86-96`. |
| `esp_timer` task | ESP-IDF system service; executes any Ticker callback | Core 0 | 22 (`25-3`) | 8192 B configured | High-priority timer-dispatch task. K1’s debug `Ticker` callback, when armed, runs here every 5 ms, pre-empting priority-1 `loopTask`. | Core/stack `.../sdkconfig.h:1044-1049`; priority `.../esp_task.h:27,45-47`; Ticker dispatch `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/libraries/Ticker/src/Ticker.cpp:33-47`. |
| FreeRTOS timer service `Tmr Svc` | Kernel configuration enables software timers; no repository `xTimer*` use was found | unpinned | 1 | 3120 configured depth | Event-driven software-timer daemon; repository has no identified callback submitted to it. | `.../sdkconfig.h:1115-1120`; rerun search below. |
| ESP `main` task | Starts `app_main`; transient after Arduino starts | Core 0 | 1 | 4096 B configured | Arduino `app_main()` initialises Arduino, creates `loopTask`, then returns. It is not a third steady application loop. | `.../sdkconfig.h:1013-1015`; `.../esp_task.h:56-58`; Arduino `main.cpp:81-106`. |
| IPC and driver-internal tasks | Framework-dependent | not established here | not established here | IPC configured 1024 B; other values component-specific | May be created by ESP-IDF internals. Static app-source searches cannot prove their runtime population. | IPC config `.../sdkconfig.h:1039-1041`; method-risk boundary below. |

The RTOS has 25 priority levels and pre-emption/time slicing enabled (`FreeRTOSConfig.h:86-96`). Thus the debug timer (priority 22), optional NimBLE host (priority 21), Arduino network events (priority 19), TCP/IP (priority 18), and radio/driver internals outrank application audio priority 1 whenever their gated subsystems are present.

## Production callbacks and ISRs

| Callback / ISR | State in `k1_hardware` | Execution context | Cadence / trigger | Blocking / boundedness | Evidence |
|---|---|---|---|---|---|
| `check_current_function()` via global `Ticker cpu_usage` | Available, inactive until serial `debug=true`; detached on `debug=false` | `esp_timer` task, Core 0, priority 22, stack 8192 | Periodic every 5 ms while debug enabled | Callback body only samples `function_id`; high-priority pre-emption still perturbs AP timing. | Global/callback `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:514`; body `SPECTRASYNQ_K1_FIRMWARE/system/system.h:48-50`; arm/detach `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp:3104-3115`; Ticker task dispatch cited above. |
| Hardware USB CDC / USB Serial JTAG ISR | Present after `USBSerial.begin()` in hardware-CDC mode; implementation-owned | Interrupt context; static source does not establish interrupt core/level here | USB RX/TX events | ISR services FIFOs and semaphores; no K1 app callback is registered. No separate Arduino event task is created unless `HWCDC.onEvent()` is called, and repository search found none. | Production USB mode `platformio.ini:62-65`; init `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp:623-636`; driver attach `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/cores/esp32/HWCDC.cpp:75-153,303-355`; rerun search below. |
| I2S RX driver interrupt/DMA completion | Present after audio channel initialisation; implementation-owned | ESP-IDF driver ISR context; affinity/level not asserted by repository | Audio DMA completion | Wakes/feeds the blocking `i2s_channel_read`; no K1 ISR body exists. | `SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h:401-403,406-482`; no app `attachInterrupt` in production sources (rerun search). |
| RMT/FastLED transmit callbacks/interrupts | Present as required by LED output library; implementation-owned | FastLED/ESP-IDF RMT driver context; exact task/ISR topology not established by repository source | Each `FastLED.show()` | Static K1 source establishes only the call boundary, not whether the installed driver blocks until submission/completion or its exact callback context. | `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h:953-963,1198-1204`; method-risk boundary below. |
| `usb_event_callback()` | **Compiled out** for `K1_HARDWARE` because `K1_ENABLE_USB_MSC_UPDATE=0` | If enabled, TinyUSB event task/callback context | USB/MSC events | Not a production callback. | Callback and registration `SPECTRASYNQ_K1_FIRMWARE/system/system.h:52-107`; compile-out `system/constants.h:220-225`. |

`process_GDFT()` is marked `IRAM_ATTR`, but it is a normal `loopTask` function call (`.ino:880-920`), **not an ISR**. The only repository-defined `attachInterrupt()` ISR found is the deprecated, gated dual-K1 sync trigger described below.

## Production AP pollers and periodic work

All rows execute on `loopTask` / Core 0 / priority 1 unless noted. “Every AP iteration” means after the previous iteration and its one-tick yield, with hardware acquisition as the dominant nominal pace; it is not a formal 133.333 Hz deadline.

| Poller / stage | Call cadence | Blocking / yield / work bound | Production state and evidence |
|---|---|---|---|
| `check_knobs(t_now)` | Every AP iteration | No physical ADC; copies CONFIG and recomputes smoothing. No yield. | Active computational shim; `persistence/knobs.h:1-12,27-85`, call `.ino:817-818`. |
| `check_buttons(t_now)` | Every AP iteration | Compiles to an empty body because both K1 hardware pins are `-1`. | Call `.ino:821-822`; guards `persistence/buttons.h:17-18,44`; pin map `system/constants.h:448-455`. |
| `check_settings(t_now)` | Every AP iteration; acts only after a deferred save deadline | Normally O(1). When armed, calls synchronous `save_config()` on Core 0; filesystem open/write has no task yield in the function. | `system/system.h:625-643`; save body `persistence/bridge_fs.h:165-220`; call `.ino:825-826`. |
| `check_serial(t_now)` | Called every AP iteration; reads only when elapsed time is `>10 ms` | Processes at most 32 available bytes per eligible poll. Reads are non-blocking, but completed commands execute their handler synchronously on Core 0; command cost is not globally bounded. | `serial/serial_menu.cpp:3732-3786`; call `.ino:829-830`. |
| Optional radio/sync poll calls | Every AP iteration if compiled | See gated section. | Calls `.ino:832-840`; no matching flags or network TUs in production source filter. |
| `acquire_sample_chunk(t_now)` | Once per AP iteration | Blocking `i2s_channel_read`; nominal chunk 7.5 ms, timeout 100 ms under production guard; timeout/short read zero-fills. | `.ino:842-852`; `audio/i2s_audio.h:86-88,406-482`; build flags `platformio.ini:74-77,149-154`. |
| `run_sweet_spot()` | Every AP iteration | GPIO work compiles away with all sweet-spot pins `-1`; residual function work is source-dependent. | `.ino:854-856`; pins `system/constants.h:451-455`. |
| `calculate_vu()` | Every AP iteration | Synchronous DSP; no explicit yield. | `.ino:858-867`. |
| `process_GDFT()` | Every AP iteration | Synchronous hot-path DSP; no explicit yield. | `.ino:880-920`. |
| loud guard and optional mic auto-sense | Loud guard every AP iteration in production; mic auto-sense only if separately flagged | Synchronous supervisors, no task delay at call site. | `.ino:891-901`; production loud guard flag `platformio.ini:142-148`. |
| AGC/VP/perf serial stream pollers; optional AP capture | Every AP iteration, internally gated | Serial output can consume Core-0 time; `stream_agc_data` uses a millisecond-modulo gate, not a periodic timer. | `.ino:923-929`; `serial/serial_menu.cpp:3788-3795`. |
| `calculate_novelty()` | Every AP iteration | Synchronous DSP; no yield. | `.ino:931-947`. |
| audio snapshot + onset + saliency | Every AP iteration | Synchronous updates plus short `portMUX` critical sections in their publish/read surfaces; no semaphore wait. | `.ino:949-991`; mutex definitions/uses `audio/k1_audio_snapshot.cpp:7,119-135`, `audio/k1_onset_beat.cpp:6,402,653`, `audio/k1_musical_saliency.cpp:33,54-60,254-262`. |
| `k1_tempo_update()` | Called every AP iteration; emits a new novelty sample every exact third AP frame | Two cheap non-emit calls, one full emit path; no RTOS delay. True declared emit rate is 44.444 Hz. | Call/comment `.ino:992`; authoritative maths and frame gate `audio/k1_tempo.cpp:28-43,1342-1390`. |
| colour shift, FPS logging, benchmark | Every AP iteration, internally conditional | Synchronous; benchmark serial report can run on Core 0. | `.ino:1021-1067`. |
| wired encoders | Compile-time gated out in `k1_hardware` | N/A in production. The gated implementation contains a 300 ms delay, so it must not be treated as harmless if re-enabled. | `.ino:1069-1072`; `system/constants.h:204-209`; `persistence/encoders.h:79`. |
| AP task watchdog feed and tail delay | Every AP iteration | Feed at entry; `vTaskDelay(1)` at tail. | `.ino:791-795,1074-1082`. |

## Render-loop pollers

All execute on `led_task` / Core 1 / priority 1, once per free-running render iteration unless gated: watchdog reset; optional framework flash-park poll; optional motion-probe ownership; queued transitions; `k1_effect_queue_frame_tick`; spectrogram/chromagram smoothing; Smart Director and visual hooks; primary and secondary effect renders; EdgeMixer; VPAB/frame dump; `show_leds`; achieved-FPS EMA; one-tick delay. The full call sequence is source-visible at `.ino:1107-1468`.

There is no queue receive, event wait, task notification, semaphore take, or `vTaskDelayUntil()` in the top-level render loop. Cross-core audio/director data uses short `portMUX` critical sections. The practical cadence and blocking behaviour of `show_leds()` remain library/hardware questions and are not upgraded to runtime fact here.

## Gated, non-production, and deprecated topology

These are current source capabilities, not current `k1_hardware` tasks. They matter because enabling an environment changes the scheduler materially.

| Environment / component | Tasks, core, priority, stack | Cadence / callbacks / poller semantics | Evidence |
|---|---|---|---|
| Wi-Fi/WebSocket A/B (`k1_wireless_ab_probe`) | App `k1_ws`: Core 0, priority 1, stack 6144 B. Arduino `arduino_events`: Core 1, priority 19, stack 4096 B. ESP Wi-Fi and TCP/IP tasks are framework-owned; TCP/IP is Core 0, priority 18, stack 4096 B from SDK config. | `k1_ws` calls WebSocket loop and drains at most 4 outbound frames, then delays 5 ms. `handle_ws_event` runs synchronously from that loop. AP `k1_wireless_poll` drains at most 4 requests per AP iteration and forces an extra one-tick AP yield at most every 250 ms while a client is connected. | Non-production env `platformio.ini:727-747`; constants/task/poll `network/k1_wireless.cpp:19-50,730-855,857-866,875-952`; event task `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/libraries/Network/src/NetworkEvents.cpp:63-71` plus SDK `sdkconfig.h:464`; TCP/IP `sdkconfig.h:1163-1165,1224-1226`. |
| BLE Remoted probes | App `ble_remoted`: Core 1, priority 1, stack 4096 B. NimBLE `nimble_host`: Core 0, priority 21 (`25-4`), stack 4096 B. BT controller is framework-owned at priority 23 with declared stack 3584 plus newlib extra. | App BLE task scans/connects and sleeps 150 ms normally, plus 500/800 ms failure delays. Scan/client/notify callbacks run in the high-priority NimBLE host context and enqueue bounded records. AP `k1_ble_remoted_poll` drains the static queue to empty (capacity 16) with zero-timeout receives each AP iteration; deck TX poll separately caps deltas at 4. | Non-production envs `platformio.ini:620-684,749-772`; app task/callbacks/poll `network/ble_remoted_central.cpp:63,113-117,295-409,907-987`; NimBLE defaults `.pio/libdeps/k1_bench_im69d_ble/NimBLE-Arduino/src/nimconfig.h:212-218`, creation `.pio/libdeps/k1_bench_im69d_ble/NimBLE-Arduino/src/nimble/porting/npl/freertos/src/nimble_port_freertos.c:25-57`; controller `esp_task.h:30-40`. |
| Dual-K1 sync | Explicitly deprecated/shelved. App `k1_sync_io`: Core 1, priority 1, stack 4096 B. Also creates NimBLE host as above. | I/O task polls/scans/clock response queue, delays 5 ms normally and 500/800 ms on failure. AP `k1_sync::poll()` runs every AP iteration. NimBLE server/client/scan/notify callbacks run on `nimble_host`. The one app ISR, `trig_in_isr`, is IRAM, allocation-free ring enqueue/drop-on-full and is attached during begin; source does not explicitly assert its interrupt core. | Dead-lane authority/envs `platformio.ini:774-843`; ISR `network/k1_sync_link.cpp:96-103,1305-1310`; I/O loop/create `:1185-1258,1317-1321`; AP poll `:1331-1342`; callback registrations `:558-712,760-917,1000-1055`. |
| TinyUSB MSC/update (non-hardware builds) | Arduino TinyUSB `usbd` task is library-created, unpinned, priority 24, stack 4096 B; FirmwareMSC can create `msc_disk`, priority 2, stack 1024 B. | USB/MSC events call `usb_event_callback`. Entire path is compiled out for K1 hardware. | Compile gate `system/constants.h:220-225`; K1 registration `system/system.h:52-107`; library creation `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/cores/esp32/esp32-hal-tinyusb.c:849`, `/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/cores/esp32/FirmwareMSC.cpp:389`. |

### Source contradictions caught

- `AGENTS.md:294,361-370` describes a hard-real-time, non-blocking/no-FreeRTOS-synchronisation Core-0 pipeline and a 100 FPS graceful-frame-drop render loop. Live source has a bounded blocking I2S read, multiple `portMUX` critical sections, no render deadline, and no frame-drop scheduler.
- `.ino:992` says tempo self-clocks to 50 Hz; `audio/k1_tempo.cpp:28-43` proves 44.444 Hz.
- `platformio.ini:630-632` says the custom BLE central “runs a Core-0 task”; current `ble_remoted_central.cpp:907-968` pins the app task to Core 1. The likely intended Core-0 warning remains true for the higher-priority NimBLE host, but the comment names the wrong task.
- An `IRAM_ATTR` annotation on `process_GDFT` is not evidence of ISR execution; it is called synchronously by `loopTask`.

## What remains NOT_VERIFIED

1. Exact runtime population, affinity, priority, state, CPU utilisation, and stack high-water for ESP-IDF internal tasks (IPC, Wi-Fi/Bluetooth controller when enabled, I2S/RMT/USB drivers). Static build configuration is not a runtime task list.
2. Actual AP period/jitter/overrun distribution, actual render cadence, and audio-to-LED latency on current hardware.
3. Whether the exact installed FastLED RMT5 path blocks the caller through wire completion, returns after DMA submission, or shifts between those modes. The K1 call boundary alone cannot settle that.
4. Interrupt affinity/level for I2S, RMT, HW CDC, and the deprecated sync GPIO ISR in the final linked image.
5. Production stack margin: the repository has no `uxTaskGetStackHighWaterMark()` for `loopTask` or `led_task`. The only located high-water accessor is NimBLE’s optional host helper.
6. The requested reference documents `firmware-v3/docs/reference/codebase-map.md` and `firmware-v3/docs/reference/fsm-reference.md` do not exist in this checkout; conclusions use live source and current top-level docs instead.

## Exact rerun searches

Run from `/Users/spectrasynq/SpectraSynq_K1_Firmware`:

```bash
git -C /Users/spectrasynq/SpectraSynq_K1_Firmware rev-parse --show-toplevel
git rev-parse HEAD
rg -n 'default_envs|build_src_filter|ARDUINO_RUNNING_CORE|K1_LED_TASK_CORE|DEFAULT_SAMPLE_RATE|DEFAULT_SAMPLES_PER_CHUNK|K1_TEMPO_NOVELTY_DECIMATION|K1_AUDIO_FREEZE_GUARD_V1|K1_WIRELESS_ENABLED|K1_BLE_REMOTED|SB_K1_SYNC_PROBE' platformio.ini
rg -n 'xTaskCreate|xTaskCreatePinnedToCore|xTaskCreateUniversal|vTaskDelete|vTaskDelayUntil|vTaskDelay\(|xTimer|uxTaskGetStackHighWaterMark' SPECTRASYNQ_K1_FIRMWARE tests platformio.ini
rg -n 'attachInterrupt|detachInterrupt|ARDUINO_ISR_ATTR|IRAM_ATTR|onEvent\(|setCallbacks\(|setClientCallbacks\(|setScanCallbacks\(|subscribe\(' SPECTRASYNQ_K1_FIRMWARE
rg -n 'check_knobs|check_buttons|check_settings|check_serial|k1_wireless_poll|k1_ble_remoted_poll|k1_sync::poll|acquire_sample_chunk|calculate_vu|process_GDFT|calculate_novelty|k1_audio_snapshot_update|k1_onset_beat_update|k1_musical_saliency_update|k1_tempo_update|show_leds|vTaskDelay\(1\)' SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino
rg -n 'CONFIG_FREERTOS_HZ|CONFIG_FREERTOS_IDLE_TASK_STACKSIZE|CONFIG_FREERTOS_TIMER|CONFIG_ESP_TIMER_TASK|CONFIG_ESP_MAIN_TASK|CONFIG_ESP_IPC_TASK|CONFIG_ARDUINO_EVENT_RUNNING_CORE|CONFIG_LWIP_TCPIP_TASK' /Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/qio_opi/include/sdkconfig.h
rg -n 'ESP_TASK_(PRIO_MAX|BT_CONTROLLER_PRIO|TIMER_PRIO|TIMER_STACK|EVENT|TCPIP|MAIN)' /Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/include/esp_system/include/esp_task.h
rg -n 'dispatch_method|ESP_TIMER_TASK|esp_timer_start_periodic' /Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/libraries/Ticker/src/Ticker.cpp
rg -n 'HWCDC\.onEvent|USB\.onEvent|MSC_Update\.onEvent|cpu_usage\.attach_ms|cpu_usage\.detach' SPECTRASYNQ_K1_FIRMWARE
rg -n 'NIMBLE_HOST_TASK_PRIORITY|xTaskCreatePinnedToCore|NIMBLE_CORE|CONFIG_BT_NIMBLE_(PINNED_TO_CORE|HOST_TASK_STACK_SIZE)' .pio/libdeps/k1_bench_im69d_ble/NimBLE-Arduino/src
```

## Audit conclusion for the scheduling decision

The accurate baseline is **two pinned application loops plus framework services**, not an actor model. Any FreeRTOS recommendation must first distinguish (a) cadence control for the two existing loops, (b) removing/bounding synchronous Core-0 work, and (c) the gated radio stacks that add high-priority Core-0 work. A proposal based on “raising the audio actor priority” or “splitting the current actors” starts from a topology that does not exist in the production source.
