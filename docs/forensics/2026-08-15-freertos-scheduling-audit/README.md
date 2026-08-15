# K1 FreeRTOS scheduling and concurrency architecture audit

**Date:** 2026-08-15
**Audit checkout:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`
**Branch / HEAD at audit reconciliation:** `main` / `8026807fe9d501720fe0c835f2b0dad077437d76`
**Post-review plan reconciliation:** `15d3a85d6d26e9698039a5b0d39dbaa1569718b4`
**Mode:** read-only firmware architecture analysis; no build, flash, serial, device, or GUI action
**Decision status:** **SCHEDULING IMPROVEMENT WARRANTED, BROAD RTOS REWRITE REJECTED**

## 1. CTO verdict

K1 would benefit from better FreeRTOS use, but not from turning every DSP stage into
an actor, raising task priorities, or moving audio work onto Core 1.

The shipping topology should remain **AP on Core 0 / VP on Core 1**. The valuable
change is a staged hardening programme:

1. **Repair or consciously renegotiate the Core-0 service-time contract.** The
   current GDFT formula doubles the per-frame inner-loop work relative to the last
   trustworthy 133 Hz timing evidence. FreeRTOS cannot schedule away a service-time
   deficit.
2. **Publish one immutable, generation-labelled AP frame and copy it once into
   VP-local storage at frame-top.** An unowned two-slot pointer swap is rejected;
   explicit three-slot ownership is the fallback only if whole-frame copy cost fails.
3. **Replace cross-core `volatile` handshakes with primitives matched to semantic
   class.** Complete desired state is latest-wins; non-idempotent edges are ordered;
   onset/beat use sequences; forensic history uses bounded rings.
4. **Only after those gates, prototype one explicit audio task on Core 0 above a
   lower-priority control/service loop.** This is the sole scheduling extraction
   with a credible product payoff: it can stop serial parsing and deferred
   persistence from sharing the AP call path. It must preserve the real IDLE0 slot,
   remain DMA/event paced, and prove that flash/cache stalls do not invalidate the
   isolation.
5. **Leave Core 1 as the render owner.** Do not put GDFT, parallel channel renders,
   radio application work, or another fixed-period clock there until current
   all-mode capacity is measured.

This is not an approval to edit the current AP-input-integrity lane. Its on-disk
authority keeps production byte-inert until P4. The findings below establish the
next architecture decision, not permission to bypass that gate.

## 2. Decision at a glance

| Question | Answer |
|---|---|
| Is the deployed firmware an AudioActor → ControlBus → RendererActor graph? | **No.** It is Arduino `loopTask` plus one explicit `led_task`. |
| Are AP and VP on the correct cores? | **Yes.** AP/Core 0 and VP/Core 1 is the strongest device-proven scheduling decision in the repository. |
| Should AP and VP priorities be raised? | **No current evidence.** They are on different cores; priority changes only redistribute time against IDF, driver, idle, and service tasks. |
| Should audio be split into multiple RTOS actors? | **No.** The stages are serially dependent and extra queues manufacture backlog, age, and mixed-frame policy. |
| Should DSP move to Core 1? | **No.** Core-1 spare capacity is unproved, RMT5 is non-DMA on this ESP32-S3 path, and same-core AP/VP previously failed cadence. |
| Is current Core-0 capacity proven? | **No; there is strong contrary evidence.** The current bank is 34,484 iterations and the most relevant live probe is about 10.1 ms active p95. |
| Is current AP→VP publication coherent? | **No.** Some paths use whole-value spinlocked snapshots; production effects still read sequentially written live globals. |
| Does production ship Wi-Fi/BLE today? | **No.** The current `k1_hardware` artefact passed the radio-isolation guard. |
| Does Core 0 only perform audio work? | **No.** Serial, controls, delayed LittleFS persistence, calibration saves, and diagnostics share the loop. |
| Is the sub-8 ms product latency contract demonstrated? | **No, and it conflicts with the current feature windows.** Latency must be specified per feature/effect. |

## 3. Authority and evidence boundary

### 3.1 Authority loaded before analysis

- `docs/agent/AGENT_EXECUTION_STANDARD.md`
- `AGENT_OS.md`
- `.claude/CLAUDE.md`
- `docs/spec-index.md`
- `.claude/handoff.md`
- `progress.md`
- `docs/protocol/k1-ws-contract.yaml`
- `docs/protocol/k1-rest-contract.yaml`
- `docs/handover/HANDOVER_2026-08-14b_AP_INPUT_INTEGRITY.md`
- `docs/plans/AP_INPUT_INTEGRITY_PLAN_2026-08-14.md`
- `docs/plans/P0_FINDINGS_2026-08-14.md`
- `docs/forensics/G1_AP_INPUT_SLOT_RATIFICATION_2026-08-15.md`

The prompt-named `firmware-v3/docs/reference/codebase-map.md` and
`firmware-v3/docs/reference/fsm-reference.md` do not exist in this checkout. Live
source, installed framework code, current build definitions, and the actual lane
authority were used instead.

### 3.2 Evidence classes

- **SOURCE-VERIFIED:** directly established from current source, build flags, or
  installed dependency source.
- **HISTORICAL DEVICE EVIDENCE:** real capture, but not the current binary or full
  current feature set.
- **INFERENCE:** arithmetic or causal consequence grounded in verified facts, not a
  current device measurement.
- **NOT VERIFIED:** requires a current device trace or physical measurement.

No source-only finding is promoted to current runtime proof.

## 4. Deployed task and system topology

### 4.1 Production application tasks

| Owner | Core | Priority | Stack | Release/pacing | Main work | Blocking/yield |
|---|---:|---:|---:|---|---|---|
| Arduino `loopTask` | 0 | 1 | 8192 B | DMA/data paced, not periodic | controls → I2S acquisition → VU/GDFT/novelty/snapshot/onset/saliency/tempo → diagnostics | bounded I2S wait; `vTaskDelay(1)` tail |
| K1 `led_task` | 1 | 1 | 8192 B | free-running, not periodic | frame state → primary render → secondary render → EdgeMixer → quantise → `FastLED.show()` | `vTaskDelay(1)` tail |

Sources:

- `platformio.ini:59-77`
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:109-132,721-764,791-1082,1107-1468`
- installed Arduino `cores/esp32/main.cpp:15-20,47-78,103-105`

The compile-time guard correctly rejects same-core AP/VP in K1 builds. Equal
numeric priority does not make the two application loops time-slice because they
are pinned to different cores.

### 4.2 Framework work that still matters

The application table is not the whole runtime. Current installed SDK values show:

- FreeRTOS tick = 1000 Hz, so `vTaskDelay(1)` is nominally one millisecond.
- `esp_timer` service is on Core 0 at high priority; the optional debug `Ticker`
  callback can pre-empt AP every 5 ms while enabled.
- Wi-Fi is pinned to Core 0 in the installed SDK, and TCP/IP is priority 18.
- The vendored NimBLE host used by BLE probe builds defaults to Core 0, priority
  21, even though K1's BLE application task is now created on Core 1.

An exhaustive exact-binary task list is **NOT VERIFIED** because production does
not expose `uxTaskGetSystemState()`, runtime shares, or stack high-water marks.

### 4.3 Production versus probe topology

| Surface | Production `k1_hardware` | Probe/non-shipping consequence |
|---|---|---|
| Wi-Fi/WebSocket | excluded from source filter | app WS task Core 0/p1 plus Core-0 Wi-Fi/TCP-IP service; AP poll applies up to four requests before acquisition |
| BLE Remoted | absent; artefact guard PASS | app task Core 1/p1, but NimBLE host Core 0/p21; AP poll drains up to the full 16-record queue |
| SyncLink | deprecated and absent | Core-1 app task plus Core-0 NimBLE host; follower poll can drain a 63-record ring |
| Effect framework | absent from shipping env | enables a render/flash park handshake; this is not a production safety mechanism |

The current product is radio-free, but future AP-only wireless promotion is a
scheduler change, not a harmless source inclusion.

## 5. Timing semantics before scheduler semantics

### 5.1 The four clocks are independent

| Name | Meaning | Current declared value | What it does **not** prove |
|---|---|---:|---|
| I2S hop | samples requested per AP iteration / sample rate | 96 / 12800 = 7.5 ms | compute time, sample age, feature delay, render cadence |
| AP throughput | completed audio-loop iterations per second | nominal 133.333 Hz | a periodic RTOS deadline or zero backlog |
| Novelty/tempo input | every third AP frame | nominal 44.444 Hz | the stale “50 Hz” call-site comment |
| VP throughput | free-running render-loop completions | mode/load dependent | fixed 100 or 120 FPS |

`active_us` subtracts I2S wait from only the instrumented AP interval. It is a
CPU-demand proxy, not capture freshness, AP→VP age, or acoustic-to-light latency.

### 5.2 Current GDFT window and service-time contradiction

Current source sets `K1_GDFT_X2_CROSSOVER_BIN=0`, so every bin uses the one-semitone
Rayleigh formula:

```text
block_size = sample_rate / neighbour_spacing
```

The current model reproduces:

- 80 bins;
- **34,484 total Goertzel inner iterations per AP frame**;
- bin 0 = 1,956 samples = 152.8125 ms of history;
- approximate bin-0 centre age = 76.37 ms;
- 96-sample hop still only 7.5 ms.

The pre-August formula used a `×2` denominator and totalled about 17,222
iterations. Therefore the current formula approximately doubled the dominant AP
cost term.

The promotion memo, `docs/hardware/ap-advice-phase2-x2-formula-decision-2026-08-05.md`,
said the expected Core-0 impact was “still low single-digit %”. That premise is
incompatible with both the operation count and the nearest live probe:

- current-formula, 12800/128/d2 bench probe: `active_p95_us=10112`,
  `active_max_us=10571`, measured AP `100.007 Hz`;
- its worst frames report GDFT around **6,584–7,043 us** before the remaining
  novelty/tempo/publication/control work;
- source artefact: `_scratch/ap_cadence_20260806/bench_im69d_default_apcad_20260806_024453__summary.json`.

That probe is not the shipping 96/d3 tuple, so it does not prove the current product
rate. It does prove the doubled bank is not a low-single-digit CPU change. The last
good 96/d3 real-music evidence (p95 7,168 us) predates both this global formula
change and other current AP work; it cannot establish current headroom.

**Decision consequence:** current shipping AP service capacity is **NOT VERIFIED
and plausibly below the declared 133.333 Hz arrival rate**. Increasing priority or
adding tasks cannot repair this. The formula/cadence product decision must be
reopened.

### 5.3 Latency contract contradiction

The global “sub-8 ms audio-to-visual” statement cannot describe every current
feature:

- one audio hop is already 7.5 ms;
- the low GDFT bins integrate 152.8 ms and have roughly 76.4 ms centre age;
- V2 onset local-maximum confirmation observes a following frame, adding at least
  one hop;
- AP compute, VP sampling, frame render, RMT submission, and physical emission are
  additional stages.

This does not mean the product necessarily feels slow. It means latency must be
named per feature:

- raw peak/VU response;
- transient/onset response;
- bass/kick response;
- beat/tempo phase;
- chord/harmonic colour;
- capture-to-final-byte;
- acoustic reference to first visible photon.

The 8 ms statement is currently an aspiration without compatible feature
semantics or proof. A scheduler design must not use it as though it were a measured
universal bound.

## 6. Core-0 audio path in exact order

Per `loop()` iteration, production executes:

1. task-WDT reset;
2. knob/button polling;
3. deferred settings check, including possible synchronous LittleFS save;
4. serial poll and synchronous command handling;
5. optional radio polls in probe builds;
6. one bounded I2S read for 96 samples;
7. sample conditioning and 4096-sample history shift/append;
8. VU and sweet-spot work;
9. 80-bin GDFT, smoothing, AGC, and spectrum write;
10. novelty calculation;
11. audio snapshot publication;
12. onset publication;
13. musical saliency publication;
14. tempo update/publication;
15. colour/diagnostic/serial housekeeping;
16. `vTaskDelay(1)` to give IDLE0 a real scheduler slot.

The bounded I2S read is intentionally blocking and has a 100 ms failure timeout.
This contradicts overview prose claiming “no blocking calls” on Core 0. The timeout
is a freeze bound, not a latency bound.

### 6.1 Queueing-system failure loop

```text
AP service time rises above sample arrival period
  -> DMA descriptors accumulate completed audio
  -> next I2S read blocks less or returns immediately
  -> loop consumes more Core-0 time and sample age grows
  -> IDLE0 loses natural slots
  -> explicit 1 ms tail delay prevents WDT panic
  -> product can remain alive while semantics are increasingly stale
```

The WDT/yield fix is necessary. It is not the compute-capacity cure.

## 7. Cross-core publication and correctness

The primary architectural debt is not too few tasks. It is mixed ownership.

### 7.1 What is coherent today

- `K1AudioSnapshot` is built locally, then assigned and read as a whole under one
  `portMUX`.
- production V2 flags make it approximately 428 bytes: scalars + 80-float spectrum
  + 12-float chroma + chord state.
- onset, tempo, saliency, Smart Director, mode-selection, hook, and EdgeMixer
  modules use their own short spinlocked copies.

Each module-local object is coherent by itself.

### 7.2 What remains incoherent

#### A. Live `spectrogram[]` bypasses the snapshot

Core 0 writes the 80 bins sequentially. Core 1's
`get_smooth_spectrogram()` reads the live array sequentially. A render can combine
old low bins and new high bins. Several waveform effects also directly read live
peak/raw globals.

This is a C++ data race and a structural route to hybrid frames even if aligned
individual words happen to be physically atomic.

#### B. Semantic state is assembled from separate generations

`audio_semantic_read()` takes tempo, onset, and audio-snapshot locks separately.
Core 0 publishes those objects sequentially. AP can advance between reads, and no
shared frame generation detects the mix.

#### C. Mode transition publishes readiness before payload

Serial and wireless writers set `mode_transition_queued=true` before writing
`mode_destination`. Core 1 can observe the request with the old destination and
take the button/default path.

#### D. Effect commits use `volatile` as a transaction

Core 0 fills multi-field pending presets then raises `volatile
g_commit_request`; Core 1 copies the presets without an atomic, lock, or generation
contract. `volatile` does not create inter-thread ordering.

### 7.3 Correct primitive shapes

| Data class | Required semantic | Recommended shape |
|---|---|---|
| high-rate AP frame | newest complete frame; no shared reader lifetime | whole-frame shared value under a short `portMUX`, then VP-local value copy; explicit owned triple slots only if measured copy cost fails |
| VP consumption | one coherent frame per render | acquire once at frame top into immutable local storage; pass one read-only view through all consumers |
| complete desired-state command | latest request wins | one static mailbox or depth-1 overwrite primitive; payload published before generation |
| non-idempotent command | preserve accepted order and once-only consumption | small bounded ordered queue with sequence and visible full/drop policy |
| multi-channel scene commit | both channels commit on one VP frame | immutable scene payload + one generation consumed at frame boundary |
| onset/beat event | survives AP publications skipped by VP | reset-aware cumulative sequence + last timestamp/strength; separate ring only if every record matters |
| telemetry/history | every record may matter | bounded ring with explicit drop counter and no Core-0 blocking |

Do not add a FreeRTOS mutex to the Core-0 hot path. Do not queue all 133 audio
frames when consumers only need the newest complete state.

## 8. Core-1 rendering and output

### 8.1 Render ownership

Core 1 sequentially owns:

- transition/effect-queue frame tick;
- spectrogram/chromagram smoothing;
- Smart Director/hooks;
- primary effect and possible second render for crossfade;
- primary runtime/buffer snapshot;
- secondary render through the shared `leds_16[]` scratch;
- secondary store/EdgeMixer/clip;
- primary restore/EdgeMixer/clip;
- final brightness, colour, scaling, quantisation, and `FastLED.show()`.

Both channels can crossfade, so a worst-case frame can perform four effect renders
plus two blends. The shared buffer, render globals, transition state, and parameter
stack make naïve parallel render tasks unsafe.

### 8.2 RMT5 correction

The installed FastLED 3.10.3 RMT5 backend is asynchronous but **not DMA-backed on
ESP32-S3 in AUTO mode**:

- `strip_rmt.cpp:82-89` explicitly sets `with_dma=false` because DMA is marked
  buggy on ESP32-S3;
- pixels are loaded through `setPixel()`;
- `drawAsync()` waits for the previous refresh before submitting the next one.

Therefore overview claims of “FastLED RMT5 DMA, CPU largely idle” are not current
source truth. `FastLED.show()` duration is neither the entire current wire time nor
a proof of Core-1 spare CPU.

### 8.3 Capacity evidence

Always-present `vp_render_us` ends before `show_leds()`. Full-frame/shown-wire
instrumentation is probe-only. Historical 2026-06 logs show typical frames around
4 ms but occasional 38–40 ms `show`/frame stalls. Those logs predate major August
render changes and do not cover the full enabled roster or simultaneous crossfades.

Current all-mode capacity, RMT ISR share, runtime percentage, stack high-water, and
120 FPS compliance are **NOT VERIFIED**. Do not move DSP to Core 1.

## 9. Control, persistence, and radio interference

### 9.1 Production work on Core 0

- Serial ingress is count-bounded to 32 bytes per eligible poll, but command-body
  and reply time have no common bound.
- `check_settings()` can call `save_config()` before acquisition.
- `save_config()` opens LittleFS, writes 512 bytes one byte at a time, and closes
  synchronously.
- calibration paths can perform multiple synchronous writes.
- production `lock_leds()` is a no-op because the effect-framework flag is off.

Moving persistence to another task is not automatically safe: flash/cache effects
can couple both cores. Any service extraction needs an explicit failure stance,
render/cache gate, immutable snapshot, coalescing, retry policy, duration counters,
and an AP discontinuity policy.

### 9.2 Future AP-only Wi-Fi

The existing probe is architecturally useful but not promotion-ready:

- a Core-0/p1 WS task shares the audio core;
- IDF Wi-Fi/TCP-IP also occupy Core 0 at higher priorities;
- AP applies up to four control requests before audio acquisition;
- custom request/TX queues copy payloads as large as 1,024 bytes inside a
  `portMUX` critical section;
- response JSON and control application have no elapsed-time budget.

If wireless becomes product-active, K1 remains **AP-only**. No scheduling finding
reopens STA mode. The radio promotion gate must include current AP/VP timing and
bounded request-service rules.

## 10. Mental-model synthesis

The thinking-model router selected a combination rather than one favourite lens.

### 10.1 Cynefin

The scheduler mechanics are **complicated**: affinities, priorities, service times,
queue depths, and generations are measurable. Physical musical response is
**complex**: it needs safe probes and eyes-on evidence. This supports analyse →
instrument → paired experiment, not a broad architectural probe.

### 10.2 Systems and archetypes

The limiting stock is queued/aged audio, not task count.

- **Limits to Growth:** sharper spectral resolution doubled the dominant compute
  term and hit the Core-0 service ceiling.
- **Fixes that Fail:** raising AP priority can improve a scalar while starving
  driver, idle, or control work and moving the failure elsewhere.
- **Shifting the Burden:** actor queues can hide a compute deficit as backlog,
  dropped frames, and mixed-age semantics.

### 10.3 Thought experiments

#### Raise AP priority

AP still needs about the same CPU. Higher priority cannot pre-empt Core-1 render
and may delay Core-0 IDF/idle/service tasks. The 1 ms IDLE0 slot remains mandatory.
Verdict: no capacity gain.

#### Split every DSP stage into actors

The stages remain serial dependencies on the same core. Added queues create frame
stock and force block/drop/overwrite policy. A one-frame pipeline stage adds 7.5 ms
before render. Verdict: cleaner boxes, worse product risk.

#### Move bottom GDFT bins to Core 1

It can save Core-0 time only if Core-1 deadline slack is real. A miss holds then
jumps bass magnitudes, which can manufacture false log-flux/onset peaks. Current
RMT/crossfade slack is unknown. Verdict: conditional research option, not the next
move.

#### Add `vTaskDelayUntil()`

AP already has a hardware clock. A 1 ms tick cannot express a constant 7.5 ms
period, and a second clock can add phase jitter/backlog. VP cadence control changes
look and latency unless every effect is proven `dt`-correct. Verdict: do not add
periodic pacing before the product cadence contract is resolved.

#### Extract one dedicated audio task

An explicit DMA-paced audio task can make ownership/priority intentional and keep
ordinary serial/control work in the Arduino service loop. Unlike per-stage actors,
it preserves the entire AP chain as one transaction. It still cannot cure excess
compute or flash/cache stalls. Verdict: the only scheduler extraction worth a
measured prototype after compute and publication repair.

### 10.4 Circle of competence

This audit does not claim:

- current device task runtime shares;
- current stack margin;
- exact radio coexistence cost;
- current all-mode VP p99/max;
- exact RMT ISR CPU occupancy;
- feature-specific physical light latency;
- field incidence of the statically proven data races.

Those surfaces remain measurement domains.

### 10.5 Effectuation and opportunity cost

Use the means already present: APCAD, VP perf, existing trace-dev, build provenance,
radio isolation guard, and current static harnesses. The affordable-loss experiment
is a non-shipping paired capture, not a multi-week actor rewrite.

The current AP-input-integrity P1/P2 lane and P4 product gate have higher immediate
value than speculative scheduler plumbing. Scheduling work earns priority only
where it removes a measured product limit or a proven coherence defect.

## 11. Kepner–Tregoe option screen

### 11.1 MUST criteria

1. Preserve AP0/VP1 unless a paired device A/B overturns it.
2. No heap, blocking mutex, or unbounded queue dependency in AP/render hot paths.
3. Sustain the chosen AP throughput with explicit backlog/drop semantics.
4. Deliver one coherent AP generation to each VP frame.
5. Preserve centre-origin, colour, motion, and `dt` behaviour.
6. Preserve the real IDLE0 slot and WDT safety.
7. Be measurable and reversible behind a non-shipping gate before promotion.

### 11.2 Options

| Option | MUST result | Weighted preference | Verdict |
|---|---|---:|---|
| A. Status quo unchanged | fails service-capacity proof and coherence | 48/100 | reject as an architecture closeout |
| B. Priority/pacing tune only | cannot remove compute or repair coherence | 44/100 | reject |
| C. Multi-actor audio pipeline | adds backlog, latency, and ownership cost | 41/100 | reject |
| D. Move DSP/render work onto Core 1 | violates proven bulkhead and lacks capacity proof | 26/100 | reject |
| **E. Staged compute + coherent publication + one bounded task extraction** | conditional pass | **80/100** | **recommend** |

Preference weights: musical response/latency 25, timing determinism 20, generation
coherence 20, reliability/observability 15, complexity/reversibility 10,
opportunity cost 10.

## 12. Superseding execution sequence

Captain's post-review has been folded into the authoritative
[`EXECUTION_PLAN.md`](EXECUTION_PLAN.md). It replaces the original coarse Gate 0-4
sequence with a fault-evident Gate 0-8 DAG:

```text
G0 authority/contracts/oracle
  -> G1 exact-head baseline
  -> G2 GDFT service contract
  -> G3 VP-local coherent frame + sequence-based events
  -> G4 state/scene/edge command transactions
  -> G5 complete non-perturbing causal proof
  -> G6 conditional audio-task A/B or NOT_REQUIRED
  -> G7A request isolation -> G7B flash/cache proof
  -> G8 one-HEAD integration/promotion
```

AP-input-integrity **AP-P4** is an external predecessor to production mutation.
Radio and 24 kHz/180-bin spectral work remain separate promotion programmes.

## 13. Explicit non-recommendations

- Do not raise AP or VP priority as a speculative performance patch.
- Do not remove the `vTaskDelay(1)` IDLE0 slot.
- Do not add `vTaskDelayUntil()` to the DMA-paced AP loop.
- Do not create one task per audio stage.
- Do not use a FreeRTOS mutex in Core-0 audio.
- Do not use FIFO semantics for newest-only AP frames.
- Do not move GDFT to Core 1 from inferred FPS slack.
- Do not parallelise primary and secondary rendering over the current shared state.
- Do not claim RMT5 DMA on the installed ESP32-S3 path.
- Do not claim universal sub-8 ms latency from the 7.5 ms hop.
- Do not promote the current wireless probe without a scheduler/radio gate.

## 14. Proof plan that can actually close the decision

One trace must carry a common frame identity through:

```text
I2S DMA completion / read return
  -> oldest/newest sample timestamp or backlog depth
  -> AP stage spans
  -> immutable AP publish generation
  -> VP frame-top acquired generation
  -> effect render span
  -> final quantised bytes
  -> RMT submit and completion boundary
  -> optional acoustic-reference-to-photodiode measurement
```

Capture dimensions:

- quiet and Captain-confirmed real music;
- worst enabled primary/secondary mode pair;
- simultaneous two-channel crossfade;
- serial command burst;
- deferred config save and calibration-save event;
- connected-idle and saturated request traffic for any radio candidate;
- instrumentation-on paired with minimally instrumented control.

Required numbers:

- AP measured throughput, active mean/p95/p99/max, over-budget sequences, DMA
  backlog/sample age, I2S failures, frame gaps;
- VP start-to-start, render/show/whole-frame p95/p99/max, drops, RMT completion,
  runtime share, stack high-water;
- AP generation age consumed by VP and mixed-generation count (must be zero);
- feature-specific and physical latency where the product claim requires it.

Current trace-dev contains VP scopes but no adequate Core-0 causal trace. That
instrumentation gap is a real prerequisite, not a licence for a broad framework.

## 15. Delegation ledger

Subagents were used because the user explicitly requested `codex-subagents` and
`ssa-management`. Their prose was treated as a hypothesis until reconciled against
live source.

| Task | Classification | Status | Evidence | Orchestrator consumption |
|---|---|---|---|---|
| FRTOS-01 task topology | explorer / helpful | contradictory docs found | `evidence/task-topology.md` | core/task/callback inventory rechecked against current source/framework |
| FRTOS-02 Core-0 AP | specialist / load-bearing | current runtime not verified | `evidence/core0-audio.md` | call order/window arithmetic re-run; current 34,484-iteration correction retained |
| FRTOS-03 Core-1 VP | specialist / load-bearing | spare capacity not verified | `evidence/core1-render.md` | RMT5 non-DMA source and timing boundary independently re-read |
| FRTOS-04 control/radio | explorer / load-bearing | production radio-free; interference open | `evidence/control-radio-persistence.md` | production artefact guard re-run PASS; serial/persistence paths re-read |
| FRTOS-05 concurrency | code review / load-bearing | source hazards verified with scope | `evidence/concurrency-primitives.md` | all three principal publication races independently re-read |
| FRTOS-06 red team | reality check / helpful | broad rewrite rejected | `evidence/red-team-options.md` | option attacks retained; stale pre-Rayleigh capacity premise corrected |
| FRTOS-07 publication/events | adversarial design review / load-bearing | amend then accept | `evidence/publication-event-plan-review.md` | unsafe two-slot lifetime rejected; PUB-01..10 and FI-01..14 folded into the execution plan |
| FRTOS-08 gate/oracle | independent gate review / load-bearing | amend then accept | `evidence/gate-oracle-plan-review.md` | AP-P4 predecessor, independent ownership and conditional Gate 6 closure folded into the proof DAG |

The evidence directory is intentionally ignored by the repository's generic
`evidence/` rule. The complete audit pack force-adds these bounded read-only reports
so their provenance survives the commit. This report and `EXECUTION_PLAN.md` are the
reconciled decision authorities; delegated evidence remains supporting material.

## 16. Validation completed this session

### Commands with decision value

```text
bash scripts/agent/session-bootstrap.sh
python3 -m pytest \
  tests/test_i2s_watchdog_static.py \
  tests/test_k1_av_regression_static.py \
  tests/test_k1_wireless_control_static.py \
  tests/test_token_scrub_static.py \
  tests/test_semantic_state_replay.py \
  tests/test_ble_midi_firmware_decoder.py \
  tests/test_deck_state_v1.py \
  tests/test_effect_queue_static.py \
  tests/test_show_state_static.py -q
python3 -m pytest tests/test_ap_input_integrity_p2.py -q
python3 scripts/ble_midi/guard_k1_radio_isolation.py \
  --env k1_hardware \
  --platformio-ini platformio.ini \
  --build-dir /Users/spectrasynq/SpectraSynq_K1_Firmware/.pio/build/k1_hardware
python3 scripts/regression-harness/gdft_center_honesty_model.py
/Users/spectrasynq/miniforge3/bin/python -c \
  'from docx import Document; p="docs/forensics/2026-08-15-freertos-scheduling-audit/K1_Scheduling_Hardening_System_Design.docx"; d=Document(p); assert len(d.paragraphs)>=88; assert len(d.tables)==9; print(len(d.paragraphs), len(d.tables), len(d.sections))'
/Applications/LibreOffice.app/Contents/MacOS/soffice --headless \
  --convert-to pdf --outdir /tmp/k1-scheduling-render-final.Ur2iac/out \
  docs/forensics/2026-08-15-freertos-scheduling-audit/K1_Scheduling_Hardening_System_Design.docx
/opt/homebrew/bin/pdftoppm -png -r 120 \
  /tmp/k1-scheduling-render-final.Ur2iac/out/K1_Scheduling_Hardening_System_Design.pdf \
  /tmp/k1-scheduling-render-final.Ur2iac/page
```

Results:

- bootstrap: PASS at session start; live authority identified;
- focused architecture host gate: **112 passed**;
- current-HEAD AP-input-integrity P2 gate: **5 passed**;
- production artefact guard: **`K1_RADIO_ISOLATION: PROVEN`**;
- current GDFT model: 80 bins, 34,484 total block iterations, bin 0 = 1,956
  samples;
- final plan-fold re-run: **112 passed**, **5 passed**, and
  **`K1_RADIO_ISOLATION: PROVEN`** on `15d3a85d...`;
- DOCX structural gate: **89 paragraphs, 9 tables, 1 section**;
- DOCX visual gate: **8/8 rendered pages inspected**, with no clipping, overlap,
  unresolved placeholder, orphaned architecture heading or illegible table header;
- no production build, device, upload, serial or physical-light validation was
  performed.

The focused host tests establish structural contracts, not current device timing or
physical product behaviour.

## 17. Skill and research outcome

The named model skills were routed into one decision process rather than stacked as
ceremonial sections. `find-skills` found two external FreeRTOS/embedded candidates,
but neither met the skill's recommended adoption threshold, so no third-party skill
was installed. Repository source and the installed framework were more authoritative
for this decision.

`claude-mem` supplied prior cadence hypotheses and the warning that sample block,
active CPU time, VP cadence, and physical latency must remain separate. Live source
overruled stale memory where it differed: production is still 96/d3, BLE's K1 app
task is now Core 1, and the current GDFT bank is the post-August 34,484-iteration
form.

## 18. Stop boundary

### Files created

- this reconciled audit;
- `DELEGATION_CONTRACTS.md`;
- `EXECUTION_PLAN.md`;
- `K1_Scheduling_Hardening_System_Design.docx`;
- planning recovery files (`task_plan.md`, `findings.md`, `progress.md`);
- eight read-only evidence reports under `evidence/`.

### Firmware files changed

- none.

### Validation not performed

- current production-equivalent build;
- device task list/runtime/stack telemetry;
- AP/VP MabuTrace with one frame identity;
- current 96/d3 GDFT timing;
- all-mode/crossfade VP capacity;
- Captain-confirmed real-music or physical latency proof.

### Real blockers

1. Active AP-input-integrity authority forbids a production scheduling edit before
   P4.
2. Current AP causal tracing is absent.
3. Current-head 96/d3 service capacity is unmeasured after the global GDFT window
   change and current AP work.
4. The product contracts conflict: 100 versus 120 FPS, universal sub-8 ms versus
   long-window semantics, and “RMT5 DMA” versus the installed non-DMA path.

### Next mechanical step

After P4 permits device work, build the smallest AP trace extension and run the
paired current-formula versus shorter-window capture on an identity-gated bench K1
with Captain-confirmed audible real music. The result selects the compute contract.
Only then start the coherent-publication implementation; a dedicated audio task is
a later, falsifiable candidate rather than an assumed destination.
