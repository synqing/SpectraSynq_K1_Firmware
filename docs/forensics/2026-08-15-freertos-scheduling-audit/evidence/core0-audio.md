# FRTOS-02 — Core-0 I2S to audio-semantic scheduling evidence

**Audit snapshot:** live worktree at `8026807fe9d5`, 2026-08-15. Firmware sources
were clean; the shared audit directory was the only untracked path. This is a
read-only architecture finding, not device proof.

## Verdict

**NOT VERIFIED: the current HEAD has no current-device measurement of AP cadence,
active CPU time, DMA backlog/sample age, or acoustic-to-semantic/LED latency.** The
last production-tuple active-work measurement is useful historical evidence, but
it predates the current GDFT window sizing and subsequent AP changes. It cannot
certify current scheduling headroom.

Two premises that a scheduler redesign must not inherit are false:

1. Core 0 does **not** run a dedicated `AudioActor`. Arduino creates `loopTask`
   at priority 1 and pins it to `ARDUINO_RUNNING_CORE`; the production build sets
   that core to 0. The sketch's entire `loop()` is the audio pipeline plus control,
   serial and housekeeping work
   ([platformio.ini](../../../../platformio.ini):59-68;
   [Arduino main.cpp](../../../../../.platformio/packages/framework-arduinoespressif32/cores/esp32/main.cpp):47-78,103-105).
2. Core 0 does **not** publish one atomic `AudioSemanticState`. It publishes three
   independent portMUX-protected objects (snapshot, onset, tempo); a consumer later
   assembles them with three separate reads. Individual objects are protected, but
   the aggregate can mix adjacent producer generations
   ([k1_semantic_state.cpp](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.cpp):31-39,70-84).

## Do not conflate these five quantities

| Quantity | What it means here | Evidence / current status |
|---|---|---|
| I2S chunk duration | Audio represented by one 96-sample hop | `96 / 12800 = 7.500 ms` ([platformio.ini](../../../../platformio.ini):74-77). |
| Declared AP throughput | Intended calls/s when every hop is consumed once | `12800 / 96 = 133.333 Hz`; this is a declaration printed by the timing guard, not measured current throughput ([SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):726-740). Tempo's heavy emit path is exactly every third AP call, nominally `44.444 Hz` ([k1_tempo.cpp](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp):28-43,1361-1384). |
| CPU active time | Loop CPU work excluding time blocked in `i2s_channel_read` | Historical APCAD definition is `total_us - i2s_us`; it is not cadence or physical latency ([16k120 active-budget verdict](../../2026-06-15-16k120-acf-spread8-active-budget-verdict.md):19-31). Current HEAD: **unmeasured**. |
| Sample age at publication | Time from ADC sampling to snapshot/onset/tempo publication | **Unmeasured and not recoverable from `frame_ms`**: `t_now` is captured before the DMA read, then reused as the snapshot timestamp ([SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):792-797,846-846,956-992). No DMA hardware timestamp or queue-depth observation exists. |
| Physical latency | Acoustic wave -> mic/I2S -> semantic event -> render -> RMT/LED photons | **Unmeasured**. The repository audit likewise found no end-to-end trace ([repo audit](../../../audit/2026-06-23-repo-audit.md):106-106,146-146). Chunk time or AP rate cannot substitute for this measurement. |

## Exact causal path on Core 0

1. Arduino framework creates `loopTask`, stack 8192 bytes by the framework default,
   priority 1, pinned to build-selected core 0. The sketch separately creates only
   `led_task` at priority 1 on core 1; the production hardware build disables its
   optional USB MSC updater
   ([Arduino main.cpp](../../../../../.platformio/packages/framework-arduinoespressif32/cores/esp32/main.cpp):15-20,47-78,103-105;
   [SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):721-752;
   [constants.h](../../../../SPECTRASYNQ_K1_FIRMWARE/system/constants.h):220-225).
2. At each `loop()` entry, `loopTask` feeds its TWDT subscription, timestamps the
   frame, and then runs knobs, buttons, settings and serial before audio acquisition.
   Optional wireless/BLE/sync polls are compile-gated and absent from the production
   flags inspected here
   ([SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):792-840).
3. `acquire_sample_chunk()` requests 192 B for mono PDM or 384 B for stereo PDM /
   32-bit STD I2S. Production uses a bounded `i2s_channel_read(...,
   pdMS_TO_TICKS(100))`. A timeout or short read zero-fills the missing tail and
   continues; the shipping path does not surface the error beyond discarding the
   status. The flag-off path still uses `portMAX_DELAY`
   ([i2s_audio.h](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h):406-482,500-509).
4. Acquisition conditions all 96 samples (gain, clamp, DC removal and optional
   guards), shifts the 4096-sample history by 96, appends the new hop, and creates
   the fixed-point waveform
   ([i2s_audio.h](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h):647-764,1189-1199).
5. The loop computes sweet-spot/VU, then `process_GDFT()`. GDFT evaluates each of
   80 canvas bins, skips the nine bins above the current Nyquist limit, and walks
   backward through each bin's own history window before smoothing and AGC
   ([SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):846-920;
   [k1_gdft_core.cpp](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp):101-219,304-318,337-375).
6. `calculate_novelty()` computes positive frame-to-frame spectral flux over 80
   bins and advances its ring ([k1_gdft_core.cpp](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp):561-601).
7. Publication order is exact: `k1_audio_snapshot_update` -> snapshot readback ->
   `k1_onset_beat_update` -> onset readback -> `k1_musical_saliency_update` ->
   `k1_tempo_update`. Snapshot and onset publish every AP call. Tempo performs its
   main history/ACF/PLL work and publishes on every third call; cheap calls can
   republish only to clear a one-shot beat tick
   ([SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):949-1019;
   [k1_audio_snapshot.cpp](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp):28-129;
   [k1_tempo.cpp](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp):1342-1483).
8. After remaining colour/serial/encoder housekeeping, `vTaskDelay(1)` blocks the
   Core-0 loop for one FreeRTOS tick so `IDLE0` actually runs. Arduino-ESP32 requires
   `CONFIG_FREERTOS_HZ=1000`, so this is a nominal one-millisecond scheduling slot,
   not a zero-cost yield. It occurs **after** the current frame's publications but
   before the next DMA read
   ([SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):1021-1082;
   [Arduino CMakeLists.txt](../../../../../.platformio/packages/framework-arduinoespressif32/CMakeLists.txt):375-378).

## Window age and algorithmic delay

The shipped default is no longer a “96-sample analysis window.” `96` is the hop.
The shared history is 4096 samples, while each bin's block size is calculated as
`sample_rate / adjacent-note-spacing` and capped at 2000
([constants.h](../../../../SPECTRASYNQ_K1_FIRMWARE/system/constants.h):23-23,162-167,329-343;
[system.h](../../../../SPECTRASYNQ_K1_FIRMWARE/system/system.h):242-286).
For the default first bin (110 Hz; next note 116.5409 Hz), integer truncation gives
`floor(12800 / 6.5409) = 1956` samples = **152.8125 ms of spectral history**.
Its rectangular/Hann-equivalent centre age is approximately **76.37 ms** before
the newest sample; higher bins use shorter windows. This is feature integration
age, not CPU time and not a measured end-to-end delay.

The V2 per-band onset local maximum deliberately fires after it has observed the
following frame (`prev_flux > flux`), adding at least one AP hop to that detection
decision under nominal cadence ([k1_onset_beat.cpp](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.cpp):205-225).
Therefore a “7.5 ms audio-to-semantic” inference is specifically refuted.

The I2S channel is configured with three DMA descriptors of 96 frames. That is
nominally 22.5 ms of descriptor capacity, not proof that samples are 22.5 ms old:
the driver may have zero, one or multiple completed buffers queued depending on
preemption and compute overruns. When backlog exists the next read can return
immediately, eliminating DMA wait while **increasing** sample age
([platformio.ini](../../../../platformio.ini):74-77;
[i2s_audio.h](../../../../SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h):265-276).

## Watchdog and starvation evidence

- Setup reconfigures TWDT to 5000 ms, watches idle core 0, panics on timeout, then
  subscribes `loopTask`. Return from `esp_task_wdt_reconfigure` is unchecked;
  `enableLoopWDT` only logs add failure in the framework
  ([SPECTRASYNQ_K1_FIRMWARE.ino](../../../../SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino):754-764;
  [esp32-hal-misc.c](../../../../../.platformio/packages/framework-arduinoespressif32/cores/esp32/esp32-hal-misc.c):125-149).
- Feeding `loopTask` at loop entry does not prove schedulability. `IDLE0` is a
  separate watched task. The July N2c correction records that bounded DMA plus
  loop-task feeding remained insufficient; only the tail `vTaskDelay(1)` stopped
  the reproduced `IDLE0` WDT failure in a 28 s bench soak
  ([N2 freeze forensic](../../2026-06-30-n2-silent-idle-watchdog-freeze.md):57-74).
- The same forensic records the failure mechanism: over-budget DSP consumed the
  next DMA period, completed DMA reads returned immediately, and `loopTask`
  starved idle. This is a positive-feedback backlog loop, not evidence that FreeRTOS
  failed to schedule a ready audio task
  ([N2 freeze forensic](../../2026-06-30-n2-silent-idle-watchdog-freeze.md):14-38).
- Last production-tuple timing evidence (2026-06-30, historical code): ACF spread
  ON measured active p95 **6784 us**, max **7236 us**, 0/2667 above 7500 us; OFF
  measured p95 **9088 us**, max **9504 us**, 889/2667 above 7500 us
  ([ACF work-spreading plan](../../2026-06-15-16k120-acf-work-spreading-plan.md):159-180).
  This validates why ACF spreading was necessary then. It does **not** include
  current-head proof, current post-publication work, the one-tick tail delay,
  sample age, or render/LED latency.

## Scheduling decision implication

FreeRTOS already schedules the DMA driver/system work and the pinned Arduino
`loopTask`; merely splitting DSP into more Core-0 tasks cannot create CPU headroom.
At equal priority it adds wakeups, queue/copy/lock costs and can let descriptors age;
above priority it can starve idle/control; below priority it can miss hops. A split
could still improve isolation **only after** measuring execution-time distributions
and assigning explicit loss/backpressure semantics. The highest-leverage current
action is instrumentation: capture per-frame `i2s_wait_us`, full active sections,
completed-buffer/sample sequence age, actual publication cadence, stack high-water
marks and task runtime stats on the current production binary. Preserve the current
Core-0/Core-1 separation and do not schedule-refactor from the historical p95 alone.

## Exact read-only rerun commands

```sh
cd /Users/spectrasynq/SpectraSynq_K1_Firmware
git rev-parse HEAD
git status --short
nl -ba platformio.ini | sed -n '54,100p;115,175p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino | sed -n '721,805p;817,1082p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '265,276p;406,509p;647,764p;1189,1199p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_gdft_core.cpp | sed -n '101,219p;304,318p;337,375p;561,601p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp | sed -n '28,129p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_onset_beat.cpp | sed -n '205,225p;486,656p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp | sed -n '24,67p;1342,1491p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_semantic_state.cpp | sed -n '31,84p'
nl -ba "$HOME/.platformio/packages/framework-arduinoespressif32/cores/esp32/main.cpp" | sed -n '15,20p;47,78p;103,105p'
nl -ba "$HOME/.platformio/packages/framework-arduinoespressif32/cores/esp32/esp32-hal-misc.c" | sed -n '125,149p;186,199p'
nl -ba docs/forensics/2026-06-15-16k120-acf-work-spreading-plan.md | sed -n '159,180p'
nl -ba docs/forensics/2026-06-30-n2-silent-idle-watchdog-freeze.md | sed -n '14,38p;57,74p'
awk 'BEGIN {d=116.5409-110.0; b=int(12800/d); printf("block=%d window_ms=%.6f centre_age_ms=%.6f\n",b,1000*b/12800,1000*(b-1)/(2*12800))}'
```

## Method boundary

No build, device, serial, flash or upload was performed. The reference paths named
by the repo instructions (`firmware-v3/docs/reference/codebase-map.md`,
`firmware-v3/docs/reference/fsm-reference.md`, and both `docs/protocol/k1-*-contract.yaml`)
do not exist in this checkout; their absence was verified with `find`. That does not
block this source-path audit, but it lowers confidence in documentation-derived
architecture labels. Source and installed framework code were treated as authority.
