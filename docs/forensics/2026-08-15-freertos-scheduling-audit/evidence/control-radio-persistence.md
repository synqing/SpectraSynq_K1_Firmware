# FRTOS-04 — control, radio, serial, and persistence interference audit

**Date:** 2026-08-15
**Scope:** read-only source/build-artifact audit of non-audio work that can execute on, or pre-empt, the Core-0 audio path. No firmware, device, serial, flash, upload, or timing experiment was performed.
**Verdict:** **NOT_VERIFIED for hard-real-time safety.** The current `k1_hardware` artefact is proven free of BLE/SyncLink, and its build definition excludes AP/WebSocket. That does **not** make Core 0 audio-only: production serial parsing/printing, controls, deferred persistence, and calibration persistence run synchronously in `loopTask` before or during audio processing. Radio probes add further Core-0 tasks and therefore cannot stand in for production timing.

## What the scheduler actually runs

`k1_hardware` defines `ARDUINO_RUNNING_CORE=0` and `K1_LED_TASK_CORE=1`; the Arduino core creates `loopTask` at priority 1. K1 creates `led_task` at priority 1 on Core 1. The production `loop()` performs knobs, buttons, settings/persistence and serial before audio acquisition, and ends with a one-tick delay.[^build-core][^arduino-loop][^loop-order]

This distinction is load-bearing:

- **same call path:** production serial/control/persistence consumes the Core-0 `loopTask`'s own audio-frame budget;
- **same-core pre-emption:** probe radio/LwIP/NimBLE tasks can pre-empt or time-slice with that `loopTask`;
- **other-core competition:** a probe's app/service task on Core 1 can compete with `led_task`, but saying that task is on Core 1 does not prove that its underlying radio host is off Core 0;
- **flash/cache coupling:** even when a future persistence worker moves to Core 1, flash operations require a separately proven cache/PSRAM/render safety protocol. Task migration alone does not make flash harmless.

The present AP budget has little documented slack: the production build comment records 6,784 us active p95 and zero frames over a 7,500 us budget after ACF spreading.[^ap-budget] That is historical measurement evidence, not a current bound on serial, flash, or radio interference.

## Production/probe matrix

| Surface | Build scope | Execution context in source | Bounded work/back-pressure | How it can interfere with audio | Classification |
|---|---|---|---|---|---|
| Knobs/buttons/control | Production | `loopTask`, Core 0, before `acquire_sample_chunk()` | Input polling is finite; downstream handlers have no common elapsed-time budget | Directly lengthens the audio frame before I2S acquisition; settings changes arm persistence | **Production interference surface** |
| USB serial RX and commands | Production (`serial/*.cpp` is in the production filter) | `check_serial()` in Core-0 `loopTask` | Poll at most every 10 ms and at most 32 input bytes per call; buffer 128 bytes. A completed command calls `parse_command()` synchronously; no command-body deadline | Command parsing, hotkeys, synchronous replies, mode/control operations, and immediate saves consume the audio task's budget | **Production; ingress bounded, execution not bounded** |
| USB serial streams/TX | Production code; runtime/debug flags select activity | Called from Core-0 `loopTask`, including post-GDFT stream calls | Some streams rate-limit themselves; `USBSerial.print/println` has no repo-level TX queue or per-frame byte/time contract | Formatting and CDC writes occur in the audio call path. Back-pressure behaviour is library/host dependent and was not timed here | **Production-capable; timing NOT_VERIFIED** |
| Delayed config persistence | Production | `check_settings()` in Core-0 `loopTask`; calls `save_config()` before audio acquisition | A 5 s quiet-period coalesces updates and low-heap failure retries. This bounds frequency, not write duration | `LittleFS.open`, 512 individual `file.write()` calls and close execute synchronously on Core 0 | **Production; event-rate bounded, service time not bounded** |
| Calibration persistence | Production, operator/calibration triggered | Accepted calibration in the audio DSP path writes noise calibration, config, and profile; clear/partial-DC paths also write synchronously | Rare and gated by explicit calibration state, but no elapsed-time ceiling | Multiple filesystem writes can extend the current audio frame; this is more severe than the ordinary one-file deferred save | **Production transient; not steady state** |
| Boot repair/default persistence | Production at setup/boot | Setup/initialisation path, before steady `loop()` cadence | Finite boot path; not an audio-frame queue | Can delay readiness, but must not be counted as steady audio jitter | **Production boot-only, not steady-state interference** |
| Render park around flash | Production calls `lock_leds()`, but production does **not** define `K1_EFFECT_FRAMEWORK_V1` | In `k1_hardware`, `lock_leds()`/`unlock_leds()` compile to no-ops. Only framework probe builds get the up-to-100 ms acknowledgement barrier | Framework wait has a 100 ms cap; production has no barrier | Any claim that production parks render safely around LittleFS is false under current flags | **Probe-only safety mechanism; absent in production** |
| AP-only WiFi/WebSocket | Only `k1_wireless_ab_probe`; production source filter excludes `network/k1_wireless.cpp` and lacks `K1_WIRELESS_ENABLED` | Probe `k1_ws` task defaults to Core 0 priority 1; `k1_wireless_poll()` also runs in Core-0 audio `loopTask`. Installed IDF config pins WiFi and LwIP TCP/IP to Core 0; TCP/IP priority is 18 | Static request and response queues depth 8; RX 768 B; TX 1024 B; drains at most 4 requests/AP tick and 4 frames/5 ms WS tick; busy/drop on full | WiFi/LwIP may pre-empt priority-1 audio; WS task time-slices with it; Core-0 poll applies controls/serialises replies before audio and accepted settings later cause flash writes | **Non-shippable probe risk, not production** |
| BLE Remoted control | Only BLE bench/probe environments under `K1_BLE_REMOTED` | K1 app `ble_remoted` task is Core 1 priority 1, **but** vendored NimBLE defaults its host to Core 0 at priority `configMAX_PRIORITIES-4` = 21. Notification decoding therefore runs in the high-priority Core-0 host; `k1_ble_remoted_poll()` drains controls in Core-0 `loopTask` | Notification decode emits at most 16 records/packet into a static depth-16 queue, non-blocking/drop-on-full. Core-0 poll drains **until empty**, with no max records or elapsed-time budget | High-priority host callbacks pre-empt audio; poll can apply the queue's full 16-record occupancy in one frame and can exceed 16 if the producer refills it while the `while` loop drains; controls may schedule persistence. Core-1 app-task placement does not isolate the radio stack | **Non-shippable probe; broad “BLE is on Core 1” claim refuted** |
| BLE deck-state TX | BLE probes only | Called by `k1_ble_remoted_poll()` in Core-0 loop; characteristic I/O is performed by the called code/library | Static delta queue depth 32; normal poll drains max 4. Empty-queue fast path writes immediately; overflow triggers immediate clear + full resnapshot; snapshot sends 18 paths; packet writer loops across MTU chunks | An ordinary drain is count-bounded, but reconnect/overflow/fast-path characteristic writes have no elapsed-time budget and can occur during audio-loop service | **Probe; partly bounded, exceptional path unbounded in time** |
| Dual-K1 sync | Deprecated, inert, non-shippable `k1_sync_probe_*` only under `SB_K1_SYNC_PROBE` | Added `k1_sync_io` task is Core 1 priority 1, but NimBLE host remains Core 0 priority 21; `k1_sync::poll()` executes in Core-0 audio loop | Stream ring has 64 slots (63 usable) and drops on full; clock queue depth 16/drop-on-full. Follower Core-0 apply service drains the entire stream ring and prints two serial lines per record, with no per-frame limit | Radio callback pre-emption plus up to 63 synchronous apply/log records can starve an audio frame | **Dead probe only; never project onto production** |

## Queue and drain semantics

| Queue/path | Capacity | Producer behaviour on full | Consumer drain limit | Timing conclusion |
|---|---:|---|---|---|
| Serial RX command buffer | 127 content bytes | Forces parse at 127; next command starts fresh | 32 input bytes per eligible call | Input work is count-bounded; parse/handler/TX time is not |
| AP request queue | 8 | Returns protocol `busy` if enqueue fails | 4 per Core-0 AP poll | Count-bounded; each control/state/capabilities operation lacks an elapsed-time budget |
| AP outbound frame queue | 8, with response-slot reservation | Counts TX drops; request processing pauses when no response capacity | 4 per 5 ms WS task tick | Count-bounded; up to 1,024-byte copy occurs while holding `portMUX`; send duration is not bounded by repo code |
| BLE decoded-control queue | 16 | `xQueueSend(..., 0)` drops and counts | **All queued records** per Core-0 poll | Producer is non-blocking; consumer burst is not per-frame bounded |
| BLE state delta queue | 32 | Overflow clears queue and synchronously resnapshots | 4 normal deltas per poll | Normal drain is bounded; overflow/reconnect recovery is not a bounded unit of work |
| Sync stream ring | 64 slots, 63 usable | New record silently omitted when full in callback | **All pending records** in follower Core-0 poll | Static memory is safe; CPU/serial burst is unbounded up to ring occupancy |
| Sync clock-response queue | 16 | `xQueueSend(..., 0)`, drop counter | All pending in Core-1 I/O task | Does not directly consume Core-0 loop, but producer callback is the high-priority Core-0 NimBLE host |
| Deferred settings flag | One coalesced pending save, 5 s deadline | Later change pushes deadline | One `save_config()` when due | Rate-bounded; filesystem latency is not bounded and there is no production render barrier |

## Flag-boundary proof and limits

The live `k1_hardware` map/ELF/bin passed `guard_k1_radio_isolation.py`: no BLE Remoted, NimBLE, decoder, or SyncLink symbols were found. The guard inspects BLE/Sync/ESP-NOW tokens, not `K1_WIRELESS_ENABLED`, WebSockets, or `k1_wireless.cpp`; AP exclusion is therefore established from the production `build_src_filter` and probe-only flag, not by that guard.[^radio-guard]

The first guard invocation with a relative `--build-dir .pio/build/k1_hardware` crashed at `Path.relative_to(ROOT)`. Use the absolute build directory in the rerun command below. This is a harness usability defect, not a firmware failure.

## Decision implications

1. **Do not redesign production around “radio contention” as though radio ships today.** Production radio absence is proven; serial/persistence isolation is the actual current scheduling debt.
2. **A dedicated higher-priority audio task would provide clearer precedence, but it is not sufficient by itself.** Command/control work must cross a bounded queue, consumers need record and elapsed-time budgets, and filesystem calls must leave the audio task entirely.
3. **Treat persistence as an asynchronous service request, not a delayed synchronous call.** Coalesce immutable config snapshots, use a depth-1/latest-wins mailbox, and expose enqueue, service-duration, failure, retry and flash-stall counters. Prove cache/render behaviour before selecting its core.
4. **Bound every Core-0 drain by both count and time.** BLE's “drain all 16” and sync's “drain all 63” are unacceptable templates for a hard-real-time audio core, even though they are probe-only today.
5. **Any production AP design must explicitly relocate/configure the platform tasks, not only the wrapper task.** The current installed WiFi/LwIP and NimBLE defaults place high-priority work on Core 0. A source comment saying the application task is Core 1 is not proof of isolation.
6. **Measurement gate:** before promotion, capture AP frame p50/p95/p99/max and over-budget count for idle, serial command burst, config save, calibration accept, connected-idle radio, and saturated request traffic. This audit cannot establish those durations from source.

## Exact rerun commands

Run from `/Users/spectrasynq/SpectraSynq_K1_Firmware`. These commands are read-only except that PlatformIO rebuilds if the optional build command is used.

```bash
# Current production build and task/flag boundaries.
sed -n '14,75p;145,162p;727,843p;1263,1297p' platformio.ini
sed -n '817,851p;923,929p;1074,1082p' SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino

# Production radio artefact guard; absolute build path is required by current script.
python3 scripts/ble_midi/guard_k1_radio_isolation.py \
  --env k1_hardware \
  --platformio-ini platformio.ini \
  --build-dir /Users/spectrasynq/SpectraSynq_K1_Firmware/.pio/build/k1_hardware

# Serial and persistence scheduling surfaces.
sed -n '3732,3787p' SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp
sed -n '631,644p' SPECTRASYNQ_K1_FIRMWARE/system/system.h
sed -n '160,220p' SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h
sed -n '1040,1071p' SPECTRASYNQ_K1_FIRMWARE/system/globals.h
sed -n '285,300p' SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp

# Radio probe queues, drains, and task placement.
sed -n '19,50p;265,418p;730,952p' SPECTRASYNQ_K1_FIRMWARE/network/k1_wireless.cpp
sed -n '250,312p;907,1008p' SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp
sed -n '21,74p;265,321p;378,459p' SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_tx.cpp
sed -n '769,805p;1115,1156p;1185,1258p;1305,1342p' SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp

# Installed framework/library task defaults used by the extant probe build.
sed -n '212,218p' .pio/libdeps/k1_ble_remoted_probe/NimBLE-Arduino/src/nimconfig.h
sed -n '37,57p' .pio/libdeps/k1_ble_remoted_probe/NimBLE-Arduino/src/nimble/porting/npl/freertos/src/nimble_port_freertos.c
sed -n '91,95p' ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/include/freertos/config/include/freertos/FreeRTOSConfig.h
sed -n '1063,1067p;1161,1165p;1223,1227p' ~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/qio_opi/include/sdkconfig.h
```

## Evidence notes

- The repository-mandated reference files `firmware-v3/docs/reference/codebase-map.md` and `firmware-v3/docs/reference/fsm-reference.md` were not present in this checkout. This audit therefore cites live source and build definitions directly.
- Build-artifact isolation proves absence from that extant artefact, not current device identity or flashed state. No device was queried.
- Source inspection proves capacities, affinities and call paths; it cannot prove worst-case runtime, interrupt occupancy, radio coexistence behaviour, USB host back-pressure, or flash/cache stall duration. Those remain **NOT_VERIFIED**.

[^build-core]: `platformio.ini:14-16`, `platformio.ini:44`, `platformio.ini:59-68`, `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:721-728`.
[^arduino-loop]: `~/.platformio/packages/framework-arduinoespressif32/cores/esp32/main.cpp:67-78,103-105`.
[^loop-order]: `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:817-846,923-928,1079-1081`.
[^ap-budget]: `platformio.ini:149-162`.
[^radio-guard]: `scripts/ble_midi/guard_k1_radio_isolation.py:17-50,101-126`; `platformio.ini:44,727-772,774-843`.

### Primary source citations by surface

- Serial: `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp:3732-3786`; `SPECTRASYNQ_K1_FIRMWARE/serial/serial_tx.cpp:27-58`.
- Persistence: `SPECTRASYNQ_K1_FIRMWARE/system/system.h:625-643`; `SPECTRASYNQ_K1_FIRMWARE/persistence/bridge_fs.h:160-220`; `SPECTRASYNQ_K1_FIRMWARE/system/globals.h:1040-1071`; `SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp:285-299`; `SPECTRASYNQ_K1_FIRMWARE/calibration/noise_cal.h:20-40,146-160`.
- AP/WebSocket: `SPECTRASYNQ_K1_FIRMWARE/network/k1_wireless.cpp:19-50,265-418,730-855,875-952`; installed `sdkconfig.h:1065,1163,1225-1226`.
- BLE: `SPECTRASYNQ_K1_FIRMWARE/network/ble_remoted_central.cpp:1-14,63,250-312,907-1008`; `SPECTRASYNQ_K1_FIRMWARE/network/k1_deck_state_tx.cpp:21-74,265-321,378-459`; vendored `NimBLE-Arduino/src/nimconfig.h:212-218`, `nimble_port_freertos.c:37-57`, `nimble_port.h:26-31`; installed `FreeRTOSConfig.h:91-94`.
- Sync: `SPECTRASYNQ_K1_FIRMWARE/network/k1_sync_link.cpp:1-25,132-133,205-209,769-805,1115-1156,1185-1258,1305-1342`.
