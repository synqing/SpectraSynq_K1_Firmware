# FRTOS-06 — adversarial audit of scheduling alternatives

**Task:** FRTOS-06
**Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`
**Observed branch / HEAD:** `main` / `b80e4ada` (bootstrap, 2026-08-15)
**Default verdict:** `NOT_VERIFIED`
**Evidence class:** source facts + historical device evidence; the strategic survivor is
provisional because there is no current post-`K1_GDFT_INT64_*` Core-0 causal trace and no
audio-to-visible latency trace.

## 1. Decision in one sentence

**Keep the existing two-loop AP0/VP1 topology (Option A).** It is the only option that
survives the hard constraints and the strongest existing A/B. Adopt only the *measurement
and invariant-guard* subset of Option B; do **not** yet add fixed-period task pacing, raise
task priority, split the audio pipeline, or move DSP to Core 1. If the current shipping-main
baseline fails, first reduce the proven compute tail or remove non-audio work from Core 0;
FreeRTOS cannot schedule away a service-time deficit.

This is not a production-readiness approval. It is a topology verdict with an explicit
falsification gate.

## 2. Facts that constrain all four options

### 2.1 Current task model is not the stale “actor model” described in overview prose

- Shipping `k1_hardware` compiles Arduino `loopTask` onto Core 0 and the explicit LED task
  onto Core 1 (`platformio.ini:59-68`).
- Arduino creates `loopTask` with priority `1` and stack `8192` in the installed framework
  (`/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/cores/esp32/main.cpp:15-20,47-78,103-105`).
- The sketch creates `led_task` with stack `8192`, priority `tskIDLE_PRIORITY + 1`, pinned
  to `K1_LED_TASK_CORE` (`SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:721-724`).
- Therefore AP and VP are two equal-priority tasks on separate cores, not a graph of
  independently scheduled audio actors.
- A compile-time guard rejects same-core AP/VP in K1 builds (`.ino:109-132`), and boot emits
  timing/core/task-creation status (`.ino:724-752`).

### 2.2 AP is DMA-paced, not timer-paced

- Shipping cadence is `12800 / 96 = 133.333 Hz`, so one chunk arrives every `7.5 ms`
  (`platformio.ini:74-77`).
- `loop()` runs controls/pollers, calls `acquire_sample_chunk()`, then VU, GDFT, novelty,
  snapshot, onset, saliency and tempo in a same-frame sequence before a final
  `vTaskDelay(1)` (`.ino:792-1082`).
- `acquire_sample_chunk()` calls `i2s_channel_read()` for one full chunk; the production
  freeze guard makes the wait bounded at 100 ms and degrades a short/failed read to silence
  (`audio/i2s_audio.h:406-482`). Normal cadence is therefore driven by DMA readiness and
  total service time, not by a software periodic timer.
- `vTaskDelay(1)` is a deliberate watchdog/scheduler contract: IDLE0 is watched and a bare
  `yield()` may immediately reschedule `loopTask`; the static gate requires a real idle slot
  (`tests/test_i2s_watchdog_static.py:91-115`). The installed SDK runs FreeRTOS at 1000 Hz,
  so one tick is 1 ms
  (`/Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/opi_opi/include/sdkconfig.h:1110`).

### 2.3 VP is deliberately free-running

- `led_thread` renders both channels, calls `FastLED.show()`, updates measured `LED_FPS`,
  then delays one tick (`.ino:1112-1468`; `visual/led_utilities.h:1200-1208`).
- The live architecture explicitly says the render loop is uncapped and typically varies
  by mode/load; effect timing must use real `dt` (`effects/framework/EffectContext.h:32-41`).
- The declared diagnostic limits are `8333 us` per VP frame and `2000 us` for render work
  (`system/constants.h:200-202`), but VP performance instrumentation is non-shipping
  (`platformio.ini:707-725`).
- A cadence cap is consequently a perceptual-behaviour change unless every enabled effect
  is proven `dt`-correct. It is not a free scheduler clean-up.

### 2.4 The strongest scheduler A/B already exists

Historical live-matrix result on the same `12.8k / 96 /3` source contract:

| Core map | Measured AP | Measured novelty | Tempo consequence |
|---|---:|---:|---|
| AP1 / VP1 | about `95-96 Hz` | about `31.7-32.1 Hz` | wrong `87-88 BPM` lane |
| AP0 / VP1 | about `133.3 Hz` | about `44.4 Hz` | `126-127 BPM` recovered |

Authority: `docs/forensics/tempo_tracking_refactor/2026-06-06-ap-cadence-probe-implementation.md:12-17,199-209`
and `2026-06-06-ap0-vp1-implementation-handover.md:150-153,227-232`.

This directly refutes the claim that AP/VP co-location is harmless. It is also the closest
available experiment to Option D.

### 2.5 Current AP capacity is the decision-critical unknown

- A 2026-07-13 real-music capture at the production rate measured `active_p95_us=7168`
  against a `7500 us` chunk period, with maxima `7710/7762 us`, `29/30` active frames over
  7500, zero frame gaps, zero I2S failures and measured AP `133.333 Hz`.
- I re-read the source JSON rather than trusting prose:
  `docs/forensics/runtime-evidence/20260713T165500-device-eyes-on/captures/*__summary.json`.
- That capture predates the shipping `K1_GDFT_INT64_MAGNITUDE_V1` and
  `K1_GDFT_INT64_RECURRENCE_V1` flags now present in `platformio.ini:97-98`. The repo's
  2026-08-05 synthesis estimates only about `22 us` residual p95 headroom after the
  previously measured int64 delta, but correctly labels that as inference and says current
  shipping-main headroom has never been measured
  (`_scratch/ap_architecture_20260805/SYNTHESIS.md:1-25,217-255`).
- A queue of three DMA descriptors can absorb isolated over-period frames, so
  `active_us > 7500` is not automatically a dropped audio frame. The system constraint is
  sustained service rate plus bounded burst depth, not a single-sample cliff. It still
  leaves little evidence-backed margin for extra task handoffs.
- No current audio-to-visible causal trace exists. Older repo audits already marked even
  the looser `<50 ms` promise unmeasured (`docs/audit/2026-06-23-repo-audit.md:106,146`).

## 3. MUST criteria (Kepner–Tregoe screen)

An option fails before weighted preference if it cannot demonstrate all of these:

1. AP stays Core 0 and VP stays Core 1 unless a live A/B overturns the established result.
2. No extra full AP-frame delay in the publication path; the active product contract is
   sub-8 ms audio-to-visual, so one additional 7.5 ms pipeline stage consumes nearly all of it.
3. No blocking queue/mutex dependency in Core-0 audio. A bounded non-blocking handoff must
   have explicit overflow semantics if introduced.
4. Sustained AP cadence remains 133.333 Hz with zero frame gaps/I2S failures under real
   music and the shipping int64 GDFT path.
5. VP remains within the 8333 us frame and 2000 us render budgets under the enabled
   primary+secondary workload, with no perceptual timing/look regression.
6. Existing IDLE0/TWDT safety remains intact.
7. Same-frame feature coherence remains explicit: today Core 0 computes AP stages
   sequentially and publishes value snapshots under short `portMUX` critical sections
   (`audio/k1_audio_snapshot.cpp:28-129`; onset/tempo/saliency use the same pattern).

## 4. Option A — keep the two-loop AP0/VP1 architecture

### Strongest attack

1. **It may already be at the compute cliff.** The best real-music p95 leaves 332 us before
   int64 GDFT, with rare over-period frames. Post-int64 shipping-main is unmeasured.
2. **“Separate cores” is not complete isolation.** AP still runs serial/control polling
   before I2S (`.ino:817-840`), and AP/VP exchange value snapshots through cross-core
   `portMUX` critical sections. A long read copy can transiently spin the publisher.
3. **Equal priority is implicit, not designed.** Both application tasks are priority 1.
   That is harmless relative to each other because they are pinned to different cores, but
   their interaction with IDF/driver/system tasks on each core has not been traced.
4. **VP is intentionally uncapped.** It can consume all Core-1 slack and only yields one
   tick. That is acceptable only while AP remains isolated and VP itself meets its budget.
5. **The end-to-end product promise is unproved.** Stable scalar cadence does not prove
   capture-to-final-byte ordering or latency.

### Failure chain thought experiment

`int64 GDFT tail rises` -> AP service time exceeds arrival rate for consecutive frames ->
the three-descriptor DMA cushion fills -> next read returns backlog rather than pacing ->
feature timestamps lag real audio -> VP keeps rendering valid-but-stale snapshots -> plate
looks smooth while musical latency silently grows. Neither WDT nor `core_ok` must fire.

### What would falsify A

- Current shipping-equivalent MabuTrace + APCAD under worst real music shows persistent
  backlog, non-zero frame gaps/I2S errors, AP p95/mean that cannot sustain 7.5 ms, or
  audio-to-final-byte latency above the product contract.
- A paired control shows priority/deadline scheduling (Option B) fixes that defect without
  changing DSP cost, driver health, render budget or perceptual timing.
- Cross-core trace attributes meaningful AP tail latency to snapshot spinlock contention.

### Provisional result

**SURVIVES, conditional.** It already incorporates the one scheduling change that has a
strong causal A/B: core separation. Its remaining risk is unmeasured compute/cross-core
tail, not proven task-topology failure.

## 5. Option B — add task priorities and/or explicit cadence controls only

### Strongest attack

1. **A fixed AP delay duplicates the hardware clock.** DMA already supplies a 7.5 ms
   release cadence. `vTaskDelayUntil` at a 1 ms tick cannot express 7.5 ms with one fixed
   period; 7 ms runs ahead and 8 ms runs behind. A phase accumulator can dither, but it
   still creates two clocks whose relative phase can produce wait/backlog jitter.
2. **A fixed VP cap can worsen latency and alter the show.** The render path is uncapped and
   its measured rate is a mode-dependent state used to derive `dt`. Capping at 100 Hz adds
   up to 10 ms sampling wait; capping at 120 Hz adds up to 8.33 ms, already larger than the
   stated sub-8 ms product contract before render/show. Frame-count-coupled legacy effects
   would also change appearance.
3. **Relative AP/VP priority is meaningless across pinned cores.** Raising Core-0
   `loopTask` priority cannot pre-empt Core-1 render. It only changes competition with
   Core-0 IDF/driver/system work, creating a plausible priority inversion/starvation risk.
4. **The required 1 ms idle slot is not optional.** Removing or weakening it can starve
   watched IDLE0 and reproduce the freeze class that `test_i2s_watchdog_static.py` guards.
5. **Priority does not remove compute.** A 7.5 ms service-time deficit remains a deficit;
   priority can merely transfer missed deadlines to the driver, control or idle tasks.

### “Fixes that fail” archetype

`AP tail grows` -> raise task priority -> AP scalar cadence temporarily improves -> driver /
idle/control service is delayed -> DMA or WDT fault appears elsewhere -> raise priority or
timeouts again. Scheduling becomes the symptomatic solution while the compute tail remains.

### What would falsify the attack and validate B

- A paired trace, same binary workload and music, shows scheduler wake latency rather than
  DSP service time dominates the AP tail.
- A narrowly scoped priority or event-notification change lowers p99/frame gaps without
  increasing I2S errors, render drops, WDT risk, control latency or audio-to-visible latency.
- A render cadence controller is measured to preserve every enabled mode's `dt` behaviour
  and improve power/thermal or jitter without violating the latency target.

### Provisional result

**REJECT as an active pacing/priority redesign; ACCEPT only its observability and invariant
guards.** Do not conflate “cadence guard” with “software cadence generator”. Runtime health
counters, deadline-miss reporting and compile-time core affinity are high-value B features;
fixed delays or priority changes are not currently evidence-backed.

## 6. Option C — split audio into more tasks / actors

### Strongest attack

1. **Same-core task splitting creates no CPU capacity.** Acquisition, GDFT, novelty,
   snapshot, onset, saliency and tempo are serial data dependencies. On Core 0, actorising
   them adds context switches, notifications/queues, stacks and ownership state to the same
   amount of computation.
2. **A pipeline adds stock and delay.** If each stage accepts the next frame while the prior
   frame advances, queues become stocks. Any stage with service rate below 133.333 Hz grows
   backlog; a bounded queue then drops or overwrites musical frames. At least one full-frame
   stage delay is 7.5 ms, nearly consuming the sub-8 ms contract before render.
3. **Same-frame coherence is currently structural.** The single loop computes a feature
   chain from one acquired chunk. Independent actors need explicit frame IDs, immutable
   buffers, stale/drop policy and a join rule for snapshot/onset/saliency/tempo; otherwise VP
   can combine different music instants.
4. **Moving any actor to Core 1 collapses into Option D.** It competes with the render task
   and attacks the proven AP0/VP1 isolation.
5. **FreeRTOS primitives are not free or automatically hard-real-time safe.** A blocking
   queue contradicts the Core-0 contract; a lock-free ring needs overflow and memory-ordering
   proof. Existing value-copy `portMUX` publication is simpler than a multi-stage graph.

### Failure chain thought experiment

`GDFT actor occasionally exceeds 7.5 ms` -> input queue reaches capacity -> choose drop-old,
drop-new or block -> dropped frame corrupts novelty/tempo history, blocked acquisition loses
DMA freshness, or drop-old breaks timestamp continuity -> downstream actor still publishes
syntactically valid mixed-age state -> perceptual failure with no crash.

### What would falsify the attack

- A zero/one-copy prototype demonstrates less active CPU time or bounded jitter despite the
  handoffs, not merely cleaner code boundaries.
- It proves one frame identity from DMA through all semantic consumers, no blocking Core-0
  path, explicit bounded-overflow behaviour, AP cadence 133.333 Hz, and sub-8 ms
  audio-to-visible latency under worst music.
- A measured independent hardware engine or otherwise unused core actually executes a stage
  concurrently. The ESP32-S3 presently has no third application core.

### Provisional result

**REJECT.** This is architecture value theatre unless a specific measured variability source
needs isolation. Module boundaries can improve without FreeRTOS task boundaries.

## 7. Option D — offload DSP to Core 1

### Strongest attack

1. **It reintroduces the proven failure topology.** Full AP/VP co-location reduced AP from
   about 133 Hz to about 95-96 Hz and broke tempo. That is direct device evidence, not taste.
2. **Core 1 is the product-output core.** It performs smoothing, two channel renders,
   transitions, EdgeMixer transforms, quantisation/gamma and `FastLED.show()`
   (`.ino:1195-1467`). Transferring GDFT/semantic work makes visual and audio deadlines
   contend on the same core.
3. **The “spare Core 1” premise is not established.** Uncapped FPS is not idle-time proof;
   a task can run fast because it consumes all otherwise idle cycles. Production VP timing
   instrumentation is off.
4. **Cross-core transport adds latency/coherence cost.** Core 0 would need to publish PCM or
   partial DSP buffers; Core 1 would return semantics to a renderer on that same core. The
   resulting priority and buffer policy is a more complex form of Option C.
5. **Failure degrades both product loops at once.** A heavy musical frame now delays the
   semantic computation and the visual response it should trigger: a reinforcing latency
   loop, not a bulkhead.

### What would falsify the attack

- Current MabuTrace under the worst enabled dual-channel mode proves enough *bounded* Core-1
  idle capacity for the exact offloaded stage, including p99/max, not FPS inference.
- A paired prototype keeps AP 133.333 Hz, VP within 8333/2000 us budgets, zero drops, same
  frame semantics and sub-8 ms audio-to-visible latency.
- It explains why the historical AP1/VP1 failure does not apply (for example a genuinely
  tiny, bounded stage rather than the DSP path) and proves that distinction by A/B.

### Provisional result

**REJECT.** It conflicts with the strongest existing scheduling experiment and removes the
system's only meaningful real-time bulkhead.

## 8. Model synthesis

| Lens | Unique conclusion |
|---|---|
| Cynefin | This is **complicated**, not chaotic or irreducibly complex: task affinity, service time, queue depth and deadlines are measurable. Analyse and instrument before probing architecture. |
| Systems / queues | Scheduler changes cannot raise service capacity. When arrival rate exceeds the slowest stage, backlog is the stock and latency is the visible symptom. |
| Thought experiment | C/D create hidden mixed-age state and queue growth before they create a crash; perceptual staleness is the first failure, not WDT. |
| Red team | A is attacked by the missing current baseline; B by duplicate clocks/priority transfer; C by serial dependencies; D by the already-failed same-core A/B. |
| Opportunity cost | C/D consume high-risk architecture effort while the product's current visual and causal-latency proof remains incomplete. One current baseline has much higher decision value. |
| Effectuation | Reuse the existing APCAD, VP perf and MabuTrace seams. The affordable-loss experiment is a non-shipping paired capture, not a firmware rewrite. |
| Circle of competence | Do not infer RMT/FastLED asynchrony, driver task slack or CPU idle from comments/FPS. Those surfaces need measurement or upstream source inspection. |
| Archetypes | Raising priority to hide service-time debt is “Fixes that Fail”; actor queues risk “Shifting the Burden” from compute overrun to backlog/drop policy. |

## 9. Provisional survivor and next falsification step

### Survivor

**Option A, with a narrow B guardrail shell:**

- preserve AP0 / VP1;
- preserve DMA-paced acquisition and free-running, `dt`-correct render;
- preserve the 1 ms IDLE/WDT yield;
- add no audio actors and offload no DSP;
- treat cadence/deadline counters and core-affinity checks as observability, not a second clock;
- if the baseline is red, optimise the measured compute tail (the existing evidence points
  first to ACF-sweep frames) or move non-audio pollers—not DSP—off the hard-real-time path.

### Decision-killing experiment

Run a paired, non-shipping trace on current `main` / shipping-equivalent flags under one
Captain-confirmed real-music fixture and the worst enabled dual-channel render:

1. APCAD: active mean/p95/max, frames over 7500, frame gaps, I2S health, DMA backlog proxy,
   and per-stage cost.
2. VP perf: start-to-start p95/max, frame/render/show time, over-budget and dropped frames.
3. MabuTrace: DMA/read completion -> AP publish -> VP snapshot read -> final `FastLED.show`
   boundary, with cross-core critical-section wait attribution.
4. Paired control: same trace with diagnostic surfaces disabled or minimally scoped to bound
   probe perturbation.

**Decision rule:**

- If both loops and causal latency pass, keep A; no scheduler redesign has product value.
- If AP service time is the miss, keep A and reduce compute tail.
- If scheduler wake/pre-emption time is the miss while compute fits, trial one narrow B
  change and re-run the same trace.
- If Core-1 headroom is not bounded under worst render, D remains killed.
- C remains killed unless a specific, measured stage-isolation requirement appears.

## 10. Re-run commands

Read-only commands used to validate decision-critical facts:

```bash
git -C /Users/spectrasynq/SpectraSynq_K1_Firmware rev-parse --show-toplevel
bash scripts/agent/session-bootstrap.sh

# Shipping core map, timing tuple and hardening flags
nl -ba platformio.ini | sed -n '14,170p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino | sed -n '100,155p;680,1088p;1107,1469p'

# DMA wait / bounded-degrade path
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h | sed -n '400,510p'

# Current Arduino task priority and RTOS tick
nl -ba /Users/spectrasynq/.platformio/packages/framework-arduinoespressif32/cores/esp32/main.cpp | sed -n '15,110p'
rg -n 'CONFIG_FREERTOS_HZ|CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ' \
  /Users/spectrasynq/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/opi_opi/include/sdkconfig.h

# Snapshot critical sections and render timing contract
nl -ba SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp | sed -n '28,140p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectContext.h | sed -n '32,67p'
nl -ba SPECTRASYNQ_K1_FIRMWARE/system/constants.h | sed -n '194,204p'
nl -ba tests/test_i2s_watchdog_static.py | sed -n '83,130p'

# Historical same-core vs split-core A/B
rg -n 'AP1 / VP1|AP0 / VP1|95|96\.238|133\.311|same-core' \
  docs/forensics/tempo_tracking_refactor/2026-06-06-ap-cadence-probe-implementation.md \
  docs/forensics/tempo_tracking_refactor/2026-06-06-ap0-vp1-implementation-handover.md

# Recompute the strongest real-music AP scalar baseline from source JSON
for f in docs/forensics/runtime-evidence/20260713T165500-device-eyes-on/captures/*__summary.json; do
  jq -r '[input_filename,
    .apcad_soak.compact_soak.active_p95_us,
    .apcad_soak.compact_soak.active_max_us,
    .apcad_soak.compact_soak.active_over_7500,
    .apcad_soak.compact_soak.frame_gap,
    .apcad_soak.compact_soak.i2s_not_ok,
    .apcad_soak.compact_soak.meas_ap_hz] | @tsv' "$f"
done

# Confirm that the scalar baseline predates the current shipping int64 path
rg -n 'K1_GDFT_INT64_(MAGNITUDE|RECURRENCE)' platformio.ini
sed -n '1,30p;217,255p' _scratch/ap_architecture_20260805/SYNTHESIS.md
```

## 11. Evidence gaps / method risk

- The scalar AP baseline is historical and predates current shipping flags. It is enough to
  reject “abundant headroom”, not enough to claim current failure.
- The same-core A/B is strong for full co-location but does not mathematically rule out a
  tiny bounded Core-1 helper. Option D remains rejected because no such scoped helper or
  current Core-1 slack evidence was proposed.
- `portMUX` hazard is a plausible trace target, not a proven significant stall.
- Exact RMT5/FastLED blocking/asynchronous behaviour was not established in this audit; no
  spare-capacity claim depends on it.
- No device, serial, flash, upload, build, test, commit or firmware edit was performed by
  FRTOS-06.
