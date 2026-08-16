---
abstract: "Active Gate 0-8 implementation plan for contained K1 scheduling, ownership and timing hardening. Preserves AP0/VP1, rejects a broad RTOS rewrite, and operates under Captain's direct 2026-08-15 scheduling implementation authority."
status: implementation-active
production_mutation_authority: FULL_UNRESTRICTED_SCHEDULING_IMPLEMENTATION_GO_2026-08-15
observed_plan_fold_sha: 15d3a85d6d26e9698039a5b0d39dbaa1569718b4
---

# K1 scheduling and musical-generation hardening — execution plan

> **2026-08-16 G0R stamp A:** Gate 0 **oracle machinery** remains CLOSED. Captain
> stamped **A** — deployed `gate0/contract.json` (12.8 kHz / 96 / d3 / 7.5 ms)
> remains controlling; no 10 ms AP hop. Gate 2 service stays **RED** against the
> frozen 6 ms p99. Gate 3 remains BLOCKED. B489 flash HOLD (this stamp is not
> the flash GO). Plan:
> [`docs/superpowers/plans/2026-08-16-g0r-cadence-authority.md`](../../superpowers/plans/2026-08-16-g0r-cadence-authority.md).
> Do not erase the negative matrix below.

## 1. Decision

Implement a **contained ownership, freshness and service-path hardening programme**.
Do not implement a broad FreeRTOS rewrite.

The production destination is:

```text
Core 0 AP owner
  DMA-paced acquisition -> complete DSP transaction -> one coherent publication

Core 1 VP owner
  one frame-top acquisition -> immutable local musical frame -> both channels -> RMT

Bounded command channels
  complete state != non-idempotent edge != persistence request != forensic history
```

The number of tasks is not the success criterion. Correct ownership, bounded execution,
coherent musical identity and measured freshness are the success criteria.

## 2. Locked decisions and open contracts

```text
STRATEGIC_RECOMMENDATION          = CONTAINED_HARDENING
AP0_VP1_TOPOLOGY                  = LOCK
BROAD_RTOS_REWRITE                = REJECT
MULTI_ACTOR_AUDIO_PIPELINE        = REJECT
SPECULATIVE_PRIORITY_OR_PACING    = REJECT
DSP_OR_PARALLEL_RENDER_ON_CORE1   = REJECT

CURRENT_HEAD_BASELINE             = REQUIRED
GDFT_SERVICE_CONTRACT             = REOPEN_AND_MEASURE
COHERENT_AP_FRAME                 = REQUIRED
DISCRETE_EVENT_SEMANTICS          = REQUIRED
CONTROL_SCENE_TRANSACTIONS        = REQUIRED

UNOWNED_TWO_SLOT_POINTER_SWAP     = REJECT
VP_LOCAL_FRAME_COPY               = FIRST_IMPLEMENTATION_CANDIDATE
TRIPLE_BUFFER_OWNERSHIP           = FALLBACK_IF_COPY_COST_FAILS

EXPLICIT_AUDIO_TASK               = CONDITIONAL_EXPERIMENT
PERSISTENCE_WORKER                = CONDITIONAL
FLASH_CACHE_SAFETY_GATE           = REQUIRED_SEPARATELY

FEATURE_LATENCY_CONTRACT          = REWRITE_REQUIRED
VP_TARGET                         = 120_FPS_PER_LOAD_BEARING_REPO_CONTRACT
VP_WHOLE_FRAME_MISS_POLICY        = GATE_0_RATIFICATION_REQUIRED
SPECTRAL_24K_180_UPGRADE          = SEPARATE_BENCH_LANE
SCHEDULING_MUTATION_AUTHORITY      = DIRECT_CAPTAIN_GO_2026_08_15
AP_INPUT_P4                        = OPEN_SEPARATE_PROGRAMME
```

The repository's load-bearing instruction sets 120 FPS and a 2.0 ms effect-code
ceiling. Existing 100 FPS prose is therefore treated as stale until reconciled. This
does **not** authorise `vTaskDelayUntil()` or another pacing clock: Gate 0 must define
whether 120 FPS applies to start-to-start throughput, whole-frame completion, allowed
miss sequences, or all three.

The universal sub-8 ms latency statement is not usable as written. It cannot cover a
7.5 ms hop, long low-frequency windows, onset confirmation, rendering and physical LED
emission as one value. Gate 0 must replace it with named feature contracts.

## 3. Authority and provenance

### 3.1 Scheduling implementation authority

Captain's direct 2026-08-15 instruction authorises full end-to-end scheduling
implementation. The durable receipt is
`docs/handover/HANDOVER_2026-08-15_SCHEDULING_HARDENING_IMPLEMENTATION.md`.
Gate 0 still blocks production source mutation until the oracle proves GREEN control,
RED fault witnesses and a frozen trust root; this is an engineering gate, not an
authority gap.

The separate AP-input-integrity P4 remains open and owns microphone slot, microphone
health, calibration and colour-lane promotion. Scheduling units may measure the current
production-equivalent AP path but may not bundle or imply completion of those changes.

### 3.2 SHA ledger

| Evidence layer | Observed SHA | Use |
|---|---|---|
| delegated audit reports | `b80e4ada...` | source hypotheses, not current runtime proof |
| reconciled audit | `8026807f...` | original CTO decision |
| plan-fold review | `15d3a85d...` | latest source reconciliation during planning |

Between the audit and plan-fold SHA, `audio/i2s_audio.h` changed in the active AP path.
The task topology and publication/control findings survived direct comparison, but the
runtime service path did not remain byte-identical.

**Implementation entry rule:** record one full `IMPLEMENTATION_SHA`, toolchain,
PlatformIO environment, build flags, artefact hashes, device identity, calibration/NVS
epoch and fixture manifest. Any later change to AP, VP, GDFT, publication, task creation,
control, persistence or build flags invalidates the earliest affected runtime gate.

## 4. Problem classification and design resolution

### 4.1 Cynefin

| Surface | Domain | Required approach |
|---|---|---|
| provenance, prohibited reads, payload-before-generation | Clear | executable ratchets |
| frame ownership, command classes, timing definitions, flash safety | Complicated | expert analysis plus deterministic oracles |
| scheduler interference, perceptual GDFT knee, trace perturbation | Complex | bounded paired device probes |
| current system state | Not chaotic | no emergency priority raise or rewrite |

### 4.2 Systems leverage order

```text
service demand exceeds arrival budget
  -> DMA backlog/sample age grows
  -> I2S reads appear faster
  -> scalar cadence can remain plausible while semantics age
  -> priority/task patch steals IDF/IDLE/service time
  -> failure moves rather than disappears
```

The leverage order is therefore:

1. establish service demand and timing semantics;
2. select a sustainable spectral contract;
3. repair information ownership and generation coherence;
4. prove the complete causal path;
5. experiment with scheduling only if interference remains attributable.

### 4.3 TRIZ contradictions

| Contradiction | Resolution |
|---|---|
| VP needs a stable frame for up to a stalled render; AP must publish every hop without waiting | Separate in space: shared value copy then VP-local immutable copy; owned triple slots only if measured copy cost fails |
| Continuous state should overwrite; onset/beat edges must remain observable | Separate by data class: state frame plus cumulative event sequences; ring only when every record matters |
| Service isolation is useful; flash can stall caches across cores | Separate in time and gate: request-only service isolation first, real flash/cache coexistence second |
| Tracing is required; tracing can create the measured tail | Separate producer ownership from commit, require stop acknowledgement, and compare instrumented versus minimal controls |

### 4.4 Margin of safety

No candidate passes merely because p95 fits the nominal 7.5 ms AP period or the
8.333 ms VP period. Gate 0 must pre-register margins from current p99/max sequences,
burst/recovery behaviour and the cost of a breach.

At minimum:

- sustainable AP service must remain below arrival demand with bounded consecutive
  over-period sequences and bounded sample age;
- the worst observed frame cannot consume all DMA cushion without recovery proof;
- lock/copy p99/max must leave measured AP and VP slack;
- ring/queue capacity must come from measured burst and drain rates;
- saturation must be visible, never silent.

No universal numeric margin is asserted before the current baseline exists.

## 5. Target data contracts

### 5.1 One continuous musical frame

The unified frame is fixed-size, trivially copyable and resident in internal RAM. It
contains one AP generation after the final semantic stage, not an aggregation of
separately locked generations.

Minimum identity/timing surface:

```text
boot_epoch
ap_generation
capture_sequence
i2s_read_return_us
newest_sample_estimate_us
oldest_sample_estimate_us
sample_time_assumption_id
ap_publish_us

spectrum/chroma/VU/peak/silence
tempo_bpm/tempo_confidence/beat_phase
other approved continuous semantic state
```

Where hardware sample timestamps are unavailable, estimates must retain an explicit
assumption identifier. Loop-entry `frame_ms` is not capture time.

### 5.2 Discrete musical events

Newest-frame state cannot reliably carry a one-frame onset or beat boolean. The frame
must carry reset-aware cumulative identity:

```text
event_epoch
onset_sequence_total
last_onset_time_us
last_onset_strength
beat_sequence_total
last_beat_time_us
```

VP retains the last consumed sequence. Unsigned delta gives the number of new events.
For `delta > 1`, the effect contract deliberately chooses one coalescer: count-scaled
energy, latest strength or an approved accumulator. If every timestamp/strength record
matters, use a separate bounded event ring with `dropped_event_records`.

### 5.3 Command classes

| Class | Primitive | Contract |
|---|---|---|
| complete desired state | static depth-one latest-wins mailbox | immutable payload, generation published last, overwrite counted |
| complete two-channel scene | one immutable scene plus one generation | both channels apply on the same VP frame |
| non-idempotent edge | small bounded ordered queue | sequence, at-most-once consume, visible full policy and drop/reject counter |
| persistence request | bounded service-owner request/result channel | coalesce only explicitly idempotent operations |
| diagnostics/history | bounded producer-owned ring | commit sequence after payload, drop counter, never block AP |

Core 1 remains sole owner of transition runtime. Core 0 may publish a complete desired
state or an ordered request; it may not inspect Core-1 transition internals to assemble
the next transaction.

### 5.4 Causal trace identity

The proof frame extends identity through:

```text
capture_sequence
  -> i2s_read_return/sample estimates
  -> AP stage spans
  -> ap_generation/ap_publish_us
  -> vp_acquire_us/render_start_us
  -> final quantised-byte identity
  -> rmt_submit_us
  -> rmt_complete_us
```

RMT submission must not be relabelled completion.

## 6. Publication implementation candidates

### Candidate A — first choice: shared copy plus VP-local copy

```text
Core 0 owner: producer_next
Shared:       published
Core 1 owner: vp_frame
```

Core 0 builds `producer_next` outside the lock. After all AP semantic stages complete,
it enters one shared `portMUX`, copies the complete POD value, updates generation and
minimal counters, then exits. Core 1 enters the same mux once at frame-top, copies value
plus generation to `vp_frame`, records acquisition time, then exits. No shared pointer
escapes. Every director/effect/channel pass receives only `const vp_frame`.

The critical section contains no DSP, smoothing, logging, allocation, derived work or
I/O. Producer and consumer lock wait/hold p50/p95/p99/max are promotion metrics.

### Candidate B — fallback: explicit three-slot ownership

Use only if Candidate A fails the pre-registered lock/copy margin. Slots must have a
mechanically tested ownership cycle equivalent to:

```text
FREE -> WRITING -> PUBLISHED -> READING -> FREE
```

AP may replace a PUBLISHED-but-unread newest state according to the declared freshness
policy, but may never return a VP-owned READING slot to WRITING. AP still may not block.

### Rejected candidate

Two slots plus an atomic active index while VP retains a shared pointer is rejected.
An index makes selection coherent; it does not prevent AP from reusing the slot during
a 38-40 ms render stall.

## 7. Gate DAG

```text
                     Captain scheduling authority receipt
                                       |
G0 authority/contracts/oracle ---------+
                                       |
                                       v
                             G1 exact-head baseline
                                       |
                                       v
                             G2 GDFT service contract
                                       |
                                       v
                             G3 coherent AP frame/events
                                       |
                                       v
                             G4 control/scene transactions
                                       |
                                       v
                             G5 complete causal proof
                                       |
                      interference attribution predicate?
                          no /                 \ yes
               G6 = NOT_REQUIRED          G6 audio-task A/B
                          \                   /
                           topology decision
                                  |
                                  v
                         G7A service requests
                                  |
                                  v
                         G7B flash/cache proof
                                  |
                                  v
                         G8 integrated promotion
```

BLE/Wi-Fi promotion and 24 kHz/180-bin spectral work are separate programmes and do
not enter Gate 8.

## 8. Gate contracts

### Gate 0 — authority, contracts and fault-evident oracle

**Entry:** plan/docs work may proceed; production work may not.

**Required outputs:**

1. exact implementation provenance manifest;
2. 120 FPS whole-frame/miss semantics and retained 2.0 ms effect ceiling;
3. feature-specific latency contracts and origins/endpoints;
4. pre-registered AP, VP, lock, queue and instrumentation margins;
5. frozen oracle/fixture hashes and acceptance ownership;
6. current test/harness inventory before new machinery;
7. direct scheduling authority receipt and proof that AP-input P4 remains separately
   scoped.

Feature contract ledger:

| Contract | Required origin | Required endpoint |
|---|---|---|
| raw peak/VU | named sample/acoustic boundary | first intended visible change |
| transient/onset | acoustic transient or accepted event | first intended visible response |
| bass energy | named analysis-window reference | first bass-driven output |
| tempo/beat phase | accepted beat/phase event | phase-aligned output |
| chord colour | named harmonic-window reference | intended colour change |
| AP freshness | newest-sample estimate | AP publication |
| VP generation age | AP publication | VP frame-top acquire |
| RMT output | submit | confirmed completion |
| physical product | acoustic reference | first visible photon |

**Fault battery before production work:** wrong SHA/flags/device/tuple; missing trace
field; corrupt generation; changed frozen fixture; deleted/skipped required test;
perturbing stream enabled; wrong device identity. The gate must reject all.

**Acceptance:** Captain owns product definitions and physical authority. An independent
harness owner and gate runner own provenance/oracle acceptance. An uncaught mutation is
an oracle defect and blocks all production lanes.

### Gate 1 — exact-current-head baseline

**Dependencies:** Gate 0. The separate AP-input P4 is not silently promoted by this
baseline and no AP-input default changes may be bundled.

Measure the exact 12.8 kHz / 96 / d3 production-equivalent path and paired trace build:

- current GDFT flags and current AP-input-integrity logic;
- ordinary serial streaming disabled except the bounded probe;
- quiet plus Captain-confirmed audible real music;
- worst enabled primary/secondary pairing and simultaneous crossfade;
- AP service/wait/backlog/sample-age and WDT/IDLE state;
- publication/VP generation age and skips;
- VP start-to-start, render, show and RMT boundaries;
- task runtime share and stack high-water;
- minimally instrumented control versus instrumented candidate.

Wrong identity, stale epoch, tuple mismatch, missing audible confirmation, incomplete
mode manifest, capture loss or unexplained trace perturbation makes the run inadmissible.
If service cannot sustain arrival, proceed only to Gate 2. Do not tune priority.

### Gate 2 — choose the GDFT service contract

**Dependencies:** Gate 1. **Behaviour-changing lane.**

Compare current `x2_cross=0` against pre-registered shorter-window candidates such as
provisional `x2_cross=40` and global legacy `x2`. Keep 24 kHz/180 bins out of this gate.

Require source/model parity, representable spectral geometry, sustainable service with
margin, bounded sample age/backlog, semantic regression checks and the pre-registered
real-music perceptual comparison.

If no candidate meets both compute and product contracts, retain the current formula and
reopen cadence/feature requirements. Do not hide the deficit with a larger hop or higher
priority. Gate 2 is one reversible behaviour-change unit.

### Gate 3 — coherent AP frame and event semantics

**Dependencies:** Gate 2.

Implement Candidate A first. Remove direct Core-1 reads of live AP globals and independent
audio/onset/tempo reads from effects/directors. Acquire once at VP frame-top. Add event
epoch/sequences, truthful timestamps, generation age/skip/mixed counters and fixed-size
internal-RAM assertions.

Required host interleavings include:

- consumer during private producer build sees the previous complete frame;
- producer/consumer paused after each copy segment sees only complete old/new values;
- VP-local frame remains unchanged through a simulated 40 ms stall while AP advances;
- generation cannot become visible before its payload;
- two events between VP frames yield sequence delta two;
- epoch/wrap creates no phantom burst;
- every field stamp matches the enclosing generation.

The fault battery must first catch deliberately unsafe early-generation, direct-global,
two-slot-reuse and lost-event variants. Device acceptance then requires lock wait/hold
p50/p95/p99/max plus unchanged service/freshness margins and
`mixed_generation_count == 0`.

If Candidate A fails only on measured copy/lock cost, revert and test Candidate B. Never
fall back to unowned double buffering.

### Gate 4 — transactional controls and scenes

**Dependencies:** Gate 3.

Implement command-class primitives from Section 5.3. Publish payload before generation,
apply at the VP frame boundary, transact both channels through one scene generation and
remove Core-0 reads of Core-1 transition runtime.

Tests must force interruption through every multi-field copy, state overwrites A/B/C,
scene channel skew, ordered-queue wrap/full, duplicate/regressed edge sequences and
commands during dip/crossfade. Visible counters must reconcile every intentional
overwrite, rejection or drop.

Any mixed scene, lost/duplicated accepted edge, silent overflow, blocking hot-path work
or ownership reversal rejects and reverts the unit.

### Gate 5 — complete causal proof and startup visibility

**Dependencies:** Gates 2-4.

Carry one admitted identity through the full trace in Section 5.4. Trace slots are
producer-owned; payload copies occur before commit; stop requires producer acknowledgement;
CRC/sequence/drop rules fail closed. Paired minimal/instrumented runs must stay inside the
Gate 0 perturbation margin.

Add the independent startup ratchet before this gate closes:

- required task-creation result latched;
- task handle validated;
- visible degraded/fault state;
- controlled restart or fail-safe policy;
- telemetry identifies the missing required task;
- forced task-creation failure proves the state is reached.

Missing/reordered timestamps, fabricated completion, unknown sample-time assumptions,
unacknowledged drain, unexplained instrumentation delta or capture loss remains
`NOT_PROVEN`. Scalar APCAD/VPAB output cannot be reinterpreted as causal proof.

### Gate 6 — conditional explicit audio-task experiment

**Entry predicate:** Gate 5 attributes a pre-registered material part of AP tail or
freshness failure to serial/control/service scheduling rather than DSP demand.

If false, record **`G6 = NOT_REQUIRED`** and retain the simpler two-task topology.

If true, test one reversible candidate:

| Task | Core | Responsibility |
|---|---:|---|
| `k1_audio_task` | 0 | DMA wait, complete AP transaction, one publication, WDT/IDLE-safe yield |
| Arduino service loop | 0 | serial, low-rate controls, diagnostic and persistence requests only |
| `led_task` | 1 | unchanged render ownership |

Priority is selected by paired A/B, not guessed. Faults restore a service call to AP,
select a wrong priority, remove the real IDLE slot, starve service and fail required task
creation. No material improvement or any regression discards the candidate. A cleaner task
diagram has no acceptance value.

### Gate 7 — persistence request isolation, then flash/cache safety

**Dependencies:** Gate 5 and the closed Gate 6 topology decision.

**Gate 7A — no filesystem:** immutable bounded/coalescing persistence request, stub
service owner, result/error channel, saturation/failure tests. This proves ownership only.

**Gate 7B — real flash:** separately prove cache-disable behaviour, render/cache safety,
park acknowledgement, coalescing, retry/failure stance, duration, AP discontinuity policy,
restart mid-save and correct core placement.

Gate 7B red rolls back real flash servicing without invalidating an independently useful
7A boundary. Task migration is not evidence that flash is harmless.

### Gate 8 — one-HEAD integration and promotion

Promote only the selected compact architecture, not every tested candidate.

Require:

- full suite and exact production build on clean post-integration HEAD;
- no deleted/newly skipped tests and no weakened oracle coverage;
- frozen harness/fixture/threshold trust root unchanged by production units;
- authorised behaviour/byte-delta manifest;
- radio/instrumentation production boundaries preserved;
- one complete current causal record;
- current device, identity, stack, WDT, freshness and feature-contract evidence;
- usable rollback artefact;
- Captain sign-off for perceptual and physical claims.

Any red blocks promotion and reverts the smallest behaviour-changing unit. Golden updates
require a separately authorised behaviour-change ticket; they are not made to accommodate
a failing candidate.

## 9. Structural ratchets

These must become executable before Gate 8:

```text
Core-1 source cannot read live AP spectrogram/waveform globals
effects/directors cannot independently acquire AP/onset/tempo state
every VP frame consumes one const K1AudioFrame or approved derived view
all consumed continuous state carries one AP generation
onset/beat edges expose reset-aware sequences
mode/scene payload is complete before publication generation changes
one scene generation covers both channels
no volatile-only multi-field transaction
no heap, blocking mutex/queue or filesystem call in AP hot path
no FIFO queue for newest-only AP frames
mixed_generation_count remains zero
required task-creation failure is latched and visible
trace dump requires producer stop acknowledgement
```

Static tests enforce ownership/banned paths. Host C++ forced-interleaving/property tests
enforce behaviour. Current-device traces enforce timing. Text-presence assertions alone
are insufficient where a small host executable can exercise the real primitive.

## 10. Verification trust and execution units

### 10.1 Oracle portfolio

| Boundary | Oracle |
|---|---|
| deterministic frame/control mapping | replay or differential golden |
| concurrency ownership/interleavings | property/metamorphic host executable |
| task/timing/freshness | paired current-device trace |
| GDFT service/perception | source/model parity plus real-music paired A/B |
| physical response | Captain-witnessed fixture and named physical measurement |

The harness must prove RED against its fault battery before judging production work.
Implementation lanes may not edit the harness, fixtures, CI or thresholds that accept
them. Gates run again on post-integration HEAD by an independent owner.

### 10.2 Atomic units

| Unit | Behaviour posture | May share a commit with |
|---|---|---|
| provenance/contracts/oracle | no production behaviour | only its own trust-root work |
| GDFT service contract | intended spectral/timing change | no publication/scheduler/radio work |
| coherent frame/events | correctness change | its own tests only |
| control/scene transactions | correctness change | its own tests only |
| trace instrumentation | non-shipping evidence | no production algorithm change |
| startup fault visibility | reliability change | its own tests only |
| explicit audio task | reversible scheduling experiment | no GDFT/flash/radio change |
| persistence request boundary | service ownership change | no real flash change |
| flash/cache coexistence | operational side effect | no scheduler/radio change |

One unit has one owner, one atomic commit, one independent gate and one rollback. A second
red after one targeted repair halts the unit for decomposition review; agents do not loop
indefinitely against the same failure.

## 11. Autonomous execution boundary

Do not launch an autonomous production fleet before Gate 0 acceptance. Captain has
authorised scheduling mutation, but the concurrency/timestamp oracle must demonstrate
fault evidence first.

If Captain later authorises autonomous execution:

- maximum two active implementation agents;
- decision-critical units advance serially through the DAG;
- harness/CI/fixtures/thresholds remain outside implementation write scope;
- independent clean-worktree gate on every integrated HEAD;
- bounded retry/decomposition stop;
- perceptual/device decisions return to Captain;
- PLC graph-loop, if chosen, is manually invoked through its allowlisted supervised
  launcher; it never auto-triggers and never self-accepts.

No Atomic Agents runtime or new agent framework belongs in K1 firmware. “Atomic” here
means typed unit inputs/outputs and separately verifiable commits, not a production
dependency.

## 12. Completion predicate

This programme is complete only when:

1. Gate 0 contracts and oracle are closed;
2. Captain's direct scheduling authority remains active and AP-input P4 remains a
   separate, unpromoted programme;
3. Gates 1-5 pass on exact evidence;
4. Gate 6 is either independently passed or explicitly closed `NOT_REQUIRED`;
5. Gate 7 is closed only for the persistence scope actually selected;
6. Gate 8 passes on one integrated HEAD;
7. Captain signs the product/perceptual/physical gates;
8. rollback and residual `NOT_VERIFIED` surfaces are named.

Until then, the architecture decision is approved but implementation promotion is not.

## 13. Separate programmes

- **BLE/Wi-Fi:** AP-only remains locked. Radio promotion requires its own host-task,
  queue, traffic, timing and production-isolation proof.
- **24 kHz / 180 bins:** separate bench spectral programme with its own calibration,
  service, memory, feature-latency and perceptual evidence.
- Neither programme may borrow a green result from this scheduling DAG.

## 14. Evidence inputs

- `README.md` — reconciled scheduling audit.
- `evidence/publication-event-plan-review.md` — publication lifetime, event and command
  invariants plus forced interleavings.
- `evidence/gate-oracle-plan-review.md` — independent Gate 0-8/oracle teardown.
- Existing FRTOS-01..06 evidence reports — task, AP, VP, control/radio, concurrency and
  red-team source findings.
