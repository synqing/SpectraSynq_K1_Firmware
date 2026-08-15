# FRTOS-05 — Concurrency primitives and cross-core hazard inventory

Date: 2026-08-15
Checkout: `/Users/spectrasynq/SpectraSynq_K1_Firmware`
Branch / HEAD observed: `main` / `b80e4ada58f08ee188154fb32403c311bba7a4c8`
Method: live declarations and call sites in `SPECTRASYNQ_K1_FIRMWARE/` plus
`platformio.ini`; no device inference. The working tree was already dirty and
was not modified except for this assigned evidence file.

## Verdict

`VERIFIED_WITH_SCOPE`: the default production build has only the Arduino
`loopTask` on Core 0 and one explicit `led_task` on Core 1. It has no application
FreeRTOS queue, semaphore, mutex, event group or task notification. It does,
however, have ten production `portMUX_TYPE` instances and several unmanaged
cross-core handshakes/shared buffers. The most important faults are not a lack
of more tasks: they are missing publication/coherency contracts between the two
existing tasks.

The source proves **semantic torn snapshots and C++ data races**. It does not by
itself prove a captured on-device hardware word tear. Aligned 32-bit loads may
be physically indivisible on the ESP32-S3, but that does not make a multi-field
or 80-element frame coherent, nor does `volatile` establish a C++ inter-thread
happens-before relation.

## Primitive inventory

| Primitive | Default `k1_hardware` | Optional/non-shipping surfaces | Live evidence |
|---|---:|---:|---|
| Tasks | Arduino `loopTask` on Core 0 plus explicit `led_task`, stack 8192, priority `tskIDLE_PRIORITY + 1`, Core 1 | `k1_ws` (priority +1), `ble_remoted` (priority 1), `k1_sync_io` (priority 1), each in separately flagged radio/probe envs | `.ino:722-724`; `network/k1_wireless.cpp:888-896`; `network/ble_remoted_central.cpp:961-963`; `network/k1_sync_link.cpp:1319-1321` |
| FreeRTOS queues | **None** | BLE Remoted static queue, capacity 16; dead/shelved SyncLink static clock-response queue, capacity 16 | `ble_remoted_central.cpp:63,113-116,954-957`; `k1_sync_link.cpp:206-210,1104-1107` |
| Application ring queues | None | Wi-Fi A/B custom request and TX rings, depth 8, copied under `g_queue_mux`; SyncLink two volatile SPSC rings | `k1_wireless.cpp:25,75-84,315-385`; `k1_sync_link.cpp:89-112,126-135,773-785,1117-1123` |
| Semaphores / FreeRTOS mutexes | **No declarations or calls found** | None found in application source. LittleFS/newlib may allocate an internal recursive mutex; that is library internals, not an application primitive | exact search command below; `persistence/bridge_fs.h:37-44` |
| Task notifications | **None found** | None found | exact search command below |
| Event groups / ringbuffer API | **None found** | None found | exact search command below |
| `portMUX_TYPE` spinlocks | **10 instances**: audio snapshot, onset, tempo, saliency; Smart Director config/output/manual; mode selection; visual hooks; EdgeMixer config | 1 Beat-Aware Director; 3 diagnostic; 5 radio/sync | declarations listed by rerun command below |
| C++ atomics | None | One `std::atomic<bool>` in compile/probe-only `ZoneComposer`; its other per-zone fields remain ordinary objects | `effects/framework/ZoneComposer.h:99-100,162`; default env does not compile the framework sources (`platformio.ini:1269-1272`) |
| Volatile shared state | Commit flags; feature-gated halt/park flags; diagnostic counters; various probe/radio state | Large additional probe/radio surface, including volatile structs and 64-bit ring elements | declarations listed by rerun command below |
| Blocking waits | Production I2S read is bounded to 100 ms because `K1_AUDIO_FREEZE_GUARD_V1` is enabled; AP and VP each end normal iterations with `vTaskDelay(1)` | `portMAX_DELAY` exists only in the flag-off reversion path and legacy `audio_transfer.h`; radio tasks use bounded delays | `platformio.ini:154`; `audio/i2s_audio.h:86-87,426-480`; `.ino:1081,1467` |
| Cross-core halt barrier | No-op in default production because `K1_EFFECT_FRAMEWORK_V1` is off | Framework builds use `volatile led_thread_halt` / `render_thread_parked`, 100 ms requester timeout and 1 s render self-heal | `system/globals.h:489-505,1043-1061`; `.ino:1117-1141`; framework flags at `platformio.ini:303,593,1296` |

### Production snapshot surfaces that are correctly spinlock-copied

- `K1AudioSnapshot`: Core 0 constructs a local value, then publishes and reads a
  value copy under `k1_audio_snapshot_mux`
  (`audio/k1_audio_snapshot.cpp:18-121,124-129`). With production V2 flags it
  carries at least the 80-float spectrum and 12-float chroma arrays in addition
  to scalar state (`platformio.ini:121-123`; `k1_audio_snapshot.h:64-97`).
- `K1OnsetBeatEvent`, `K1TempoEvent` and musical saliency use their own
  independent spinlocks (`k1_onset_beat.cpp:402-404,653-655`;
  `k1_tempo.cpp:458,473-475,1488-1490`;
  `k1_musical_saliency.cpp:33,54-63,254-268`).
- Smart Director, mode-selection, visual-hook and EdgeMixer configurations are
  copied under module-local spinlocks. EdgeMixer performs matrix maths outside
  the lock, then publishes config plus 36 fixed-point coefficients atomically
  (`director/k1_edgemixer.cpp:890-919`).

These are coherent **per module**. They do not produce one transaction spanning
snapshot + onset + tempo, and they do not cover the legacy direct globals below.

## Ranked hazards

### BLOCKER 1 — production AP-to-VP direct globals are a data race and an incoherent frame

Core 0 writes the 80-bin `spectrogram[]`, `waveform_peak_scaled`,
`max_waveform_val_raw`, `audio_vu_level`, `silence`, and related globals as
ordinary objects (`system/globals.h:97,218-221,255-256`;
`system/globals.cpp:45-47`; `audio/k1_gdft_core.cpp:471,548`;
`audio/i2s_audio.h:647-941`). Core 1 then directly reads them:

- `get_smooth_spectrogram()` walks live `spectrogram[0..79]` every render frame
  (`visual/lightshow_modes.h:19-35`; called at `.ino:1213`). Core 0 writes that
  array sequentially. A Core-1 pass can therefore combine old low bins with new
  high bins, even if every individual fixed-point word is physically atomic.
- Waveform effects directly read `waveform_peak_scaled` and
  `max_waveform_val_raw` (`effects/light_mode_waveform.cpp:9,74`;
  `light_mode_waveform_fast.cpp:47-52,151`;
  `light_mode_waveform_hybrid.cpp:21-33,152`).
- The source already has a coherent `K1AudioSnapshot` containing the V2 spectrum,
  but legacy smoothing/effects bypass it.

Impact: undefined C++ inter-thread behaviour plus a proven structural route to
hybrid spectral frames, inconsistent activity gates and visual jitter. This is
production-active and directly relevant to audio-to-visual correctness.

Recommended primitive shape: one AP publication per frame (double-buffer +
generation/seqlock, or a short pointer/index swap with release/acquire), then one
VP snapshot acquisition at frame top. Do not put a FreeRTOS mutex in the Core-0
audio path and do not queue 133 full spectrum messages per second unless measured;
the newest-complete-frame semantic is better served by overwrite/double-buffer.

### BLOCKER 2 — mode-transition flag is published before its payload

`mode_transition_queued` and `mode_destination` are ordinary globals
(`system/globals.h:534-535`). The serial and wireless control producers write
the flag **first**, then the destination
(`serial/serial_cmd_handlers.cpp:1610-1623`;
`control/k1_control_facade.cpp:480-481`). Core 1 reads/clears both in
`run_transition_fade()` (`visual/led_utilities.h:1683-1692`).

There is a real logical interleaving where Core 1 sees `queued=true` while
`mode_destination` is still `-1`, takes the button/default branch and advances
to the next mode instead of applying the requested mode. Independently, the
unsynchronised ordinary accesses are a C++ data race. This is the exact opposite
of a safe payload-then-release-flag protocol.

Recommended primitive shape: a single latest-wins command object protected by a
very short critical section, or a depth-1 overwrite queue/task notification
carrying a stable command generation. At minimum publish destination first and
use release/acquire semantics; merely changing the bool to `volatile` is not a
fix.

### BLOCKER 3 — the effect queue uses volatile as a multiword commit protocol

The production `k1_effect_queue` says Core 0 fills `g_pending[2]` then raises
`volatile g_commit_request` (`control/k1_effect_queue.cpp:50-70,473-508`). Core 1
reads that flag and copies the 15-field `K1ChannelPreset`, including multiple
floats, with no lock/fence/generation validation (`:587-604`). `volatile` neither
orders the preceding preset stores nor creates a C++ happens-before edge.

There is also a reverse race: Core 0's `k1_queue_arm_begin()` reads Core-1-owned
`g_transition[ch].phase/target` while Core 1 mutates them (`:155-240,473-482`).
Rapid arming during a transition can therefore seed from a hybrid target.

Impact: a scene commit can combine fields from different presets or lose/retarget
a command. The blast radius is full mode/palette/brightness state, not only a
telemetry counter.

Recommended primitive shape: a statically allocated command mailbox with an
explicit generation and release/acquire publication, or a static FreeRTOS queue
with overwrite/latest-wins semantics drained once at the frame boundary. Keep
transition runtime single-owner on Core 1; Core 0 should request a captured
effective target rather than reading Core-1 internals directly.

### SUGGESTION 4 — independent semantic locks can mix three different AP generations

`audio_semantic_read()` calls tempo, onset, then audio-snapshot accessors under
three independent locks (`audio/k1_semantic_state.cpp:36-40`). Dense Forge does
the same in the opposite order (`effects/light_mode_dense_forge.cpp:98-100` and
`light_mode_dense_forge_chord.cpp:104-106`). Core 0 publishes snapshot, onset,
saliency and tempo sequentially in `.ino:952-1003`.

Each returned object is internally coherent, but AP can advance between reads.
A render can therefore combine a new spectrum/chord with an older onset or a
new tempo tick with an older snapshot. No common `frame_id` exists to detect the
mix. The one-frame event booleans make this more consequential than ordinary
slow telemetry.

Recommended shape: publish one immutable semantic frame after all AP producers
finish, with a shared frame generation/timestamp. This also reduces repeated
Core-1 spinlock acquisitions and copies of the large audio snapshot.

### SUGGESTION 5 — framework flash/PSRAM barrier fails open without telling the caller

In framework builds, `lock_leds()` raises a volatile halt request and waits at
most 100 ms for `render_thread_parked`, but returns `void` regardless of whether
the acknowledgement arrived (`system/globals.h:1043-1057`). Persistence callers
then proceed with LittleFS work. The render side also force-clears the halt after
1 s (`.ino:1121-1134`). Volatile loads/stores do not formalise the ordering of
PSRAM accesses around the acknowledgement.

Impact is currently bounded to non-default framework/Beat-Aware builds, but in
those builds the stated purpose is preventing illegal PSRAM access during a
flash-cache-disable window. A timeout that silently proceeds defeats that
safety property. `k1_preset_slot_save()` and `k1_show_state_save()` also open
LittleFS directly before/without a matching barrier (`control/k1_effect_queue.cpp:360-373,549-558`;
`control/k1_show_state.cpp:258-268`).

Recommended shape: requester/ack generations with release/acquire ordering;
return success/failure from park, and fail the flash write closed on missing ack.
All framework-build flash writers must use the same barrier API.

### SUGGESTION 6 — diagnostic captures can perturb timing and can dump an in-flight write

The non-shipping diagnostic pool copies as many as 512 payload bytes while
holding `diag_capture_mux` (`diag/diagnostic_capture.cpp:135-172`;
`system/constants.h:185-189`). `portENTER_CRITICAL` disables local interrupts
and spins the other core, so this measurement surface can perturb the timing it
is intended to measure.

The stereo and render trace probes use only volatile `armed`/count handshakes.
Their dump paths clear `armed`, then CRC/read buffers without an acknowledgement
that the producer has left a possible in-flight `memcpy`
(`audio/k1_stereo_probe.cpp:40-49,72-86`;
`visual/k1_render_trace.cpp:50-71,101-114`). This does not affect production,
but it weakens forensic evidence integrity.

Recommended shape: producer-owned slot commit generations; stop request plus
producer acknowledgement before dump; copy payload outside the spinlock into a
reserved slot and publish the slot only after the copy completes.

### SUGGESTION 7 — shelved SyncLink SPSC rings rely on volatile, including 64-bit fields

The dead/shelved dual-sync probe describes two rings as lock-free SPSC but uses
volatile head/tail and volatile 64-bit/struct elements without acquire/release
ordering (`network/k1_sync_link.cpp:89-112,126-135,773-785,1117-1123`). The ISR
ring additionally stores a 64-bit timestamp on a 32-bit target. Source alone
cannot guarantee a non-torn timestamp or payload-before-head visibility.

This is not production debt because `SB_K1_SYNC_PROBE` is non-shipping and the
lane is explicitly shelved (`platformio.ini:777-783`). It must not be reused as
a concurrency pattern.

### NIT 8 — task creation failures only log; no operational state is latched

The LED task creation result is printed but setup continues when creation fails
(`.ino:722-750`). Radio/probe task creation similarly logs and returns. A failed
production LED task leaves the audio loop running with no plate output and no
explicit degraded-mode state for control/telemetry.

This is not a scheduling redesign argument, but a startup reliability gap.
Consider a fail-visible/restart policy and keep handles initialised to `nullptr`.

## Negative findings

- No application semaphore/mutex, event group, task notification, task suspend,
  task resume, or unbounded queue send/receive was found.
- Queue sends/receives in BLE and SyncLink use zero wait, so queue saturation
  drops and counts rather than blocking the AP loop.
- No nested production application spinlock acquisition was found in the
  inspected call sites. Enter/exit textual counts differ in some modules because
  early-return branches each exit the same single acquisition; no unmatched
  live branch was identified by inspection.
- No evidence supports a classic FreeRTOS mutex priority inversion today,
  because no application FreeRTOS mutex exists. Cross-core `portMUX` contention
  is the relevant bounded spin/interrupt-off mechanism.
- Production `portMAX_DELAY` is disabled by `K1_AUDIO_FREEZE_GUARD_V1`; the
  live I2S read has a 100 ms ceiling. The 100 ms ceiling is much larger than the
  nominal 7.5 ms audio hop, but it is bounded and watchdog-covered.

## Exact rerun commands

Run from the repository root.

```bash
# All application primitive declarations/uses.
/opt/homebrew/bin/rg -n --glob '*.{h,hpp,c,cpp,ino}' \
  '\b(QueueHandle_t|SemaphoreHandle_t|TaskHandle_t|EventGroupHandle_t|RingbufHandle_t|portMUX_TYPE|std::atomic|volatile)\b|\b(xQueueCreate|xQueueCreateStatic|xQueueSend|xQueueReceive|xSemaphore|xTaskNotify|ulTaskNotify|portENTER_CRITICAL|taskENTER_CRITICAL|portMAX_DELAY)\b' \
  SPECTRASYNQ_K1_FIRMWARE

# Prove absence/presence of semaphore, notification, event-group and ringbuffer APIs.
/opt/homebrew/bin/rg -n --glob '*.{h,hpp,c,cpp,ino}' \
  '\b(SemaphoreHandle_t|xSemaphore[A-Za-z_]*|EventGroupHandle_t|xEventGroup[A-Za-z_]*|RingbufHandle_t|xRingbuffer[A-Za-z_]*|xTaskNotify[A-Za-z_]*|ulTaskNotify[A-Za-z_]*)\b' \
  SPECTRASYNQ_K1_FIRMWARE

# Enumerate queues and task creation sites.
/opt/homebrew/bin/rg -n --glob '*.{h,hpp,c,cpp,ino}' \
  '\b(QueueHandle_t|xQueue[A-Za-z_]*|TaskHandle_t|xTaskCreatePinnedToCore|xTaskCreate)\b' \
  SPECTRASYNQ_K1_FIRMWARE

# Enumerate spinlock declarations and critical-section sites.
/opt/homebrew/bin/rg -n --glob '*.{h,hpp,c,cpp,ino}' \
  '\bportMUX_TYPE\b|\bport(ENTER|EXIT)_CRITICAL\b' \
  SPECTRASYNQ_K1_FIRMWARE

# Reproduce the production AP/VP direct-global paths.
/opt/homebrew/bin/rg -n \
  'spectrogram\[[^]]+\]|waveform_peak_scaled|max_waveform_val_raw|audio_vu_level' \
  SPECTRASYNQ_K1_FIRMWARE/audio SPECTRASYNQ_K1_FIRMWARE/effects \
  SPECTRASYNQ_K1_FIRMWARE/visual SPECTRASYNQ_K1_FIRMWARE/system

# Reproduce both unsafe commit protocols.
/opt/homebrew/bin/rg -n \
  'mode_transition_queued|mode_destination|g_commit_request|g_pending|g_transition\[' \
  SPECTRASYNQ_K1_FIRMWARE/serial SPECTRASYNQ_K1_FIRMWARE/control \
  SPECTRASYNQ_K1_FIRMWARE/visual SPECTRASYNQ_K1_FIRMWARE/system

# Reproduce build reachability: default filter/flags versus optional radio/framework envs.
/opt/homebrew/bin/rg -n \
  'default_envs|build_src_filter|K1_AUDIO_FREEZE_GUARD_V1|K1_EFFECT_FRAMEWORK_V1|K1_WIRELESS_ENABLED|K1_BLE_REMOTED|SB_K1_SYNC_PROBE' \
  platformio.ini
```

## Method risks and unverified boundary

- Static source inspection cannot measure contention duration, actual missed
  events, compiler output ordering, or a hardware word tear. MabuTrace/device
  causality would be required to quantify those runtime effects.
- The inventory is scoped to application code in `SPECTRASYNQ_K1_FIRMWARE/`.
  ESP-IDF, Arduino, FastLED, NimBLE, LittleFS and newlib contain internal RTOS
  primitives not declared in this repository.
- `firmware-v3/docs/reference/codebase-map.md` and `fsm-reference.md`, named by
  the repository instructions, do not exist in this checkout. Current source,
  `platformio.ini`, protocol contracts and lane docs were used instead.
- The generated ignored `SPECTRASYNQ_K1_FIRMWARE.ino.cpp` was not treated as an
  independent source authority; the tracked `.ino` is the source and PlatformIO
  regenerates the `.ino.cpp`.
