# FRTOS-08 — Gate and oracle plan review

**Date:** 2026-08-15
**Observed checkout:** `main` / `15d3a85d6d26e9698039a5b0d39dbaa1569718b4`
**Scope:** review and plan only; no firmware, test, build, git, device, serial or GUI mutation
**Evidence class:** current source/documents plus existing host and device-harness surfaces; no new runtime proof

## Verdict

**AMEND, THEN ACCEPT.**

Captain's recommendation set is strategically correct and materially stronger than the
original audit sequence. The original `Gate 0..4` plan is not yet implementation authority:
it combines contract work, behaviour changes, instrumentation and promotion; it does not
name independent acceptance owners; and its double-buffer pointer proposal has an
unproved lifetime under the recorded 38–40 ms VP stalls.

The smallest defensible execution programme is the Gate 0–8 DAG below. It preserves:

```text
AP0_VP1_TOPOLOGY               = LOCK
BROAD_RTOS_REWRITE             = REJECT
MULTI_ACTOR_AUDIO_PIPELINE     = REJECT
SPECULATIVE_PRIORITY_PACING    = REJECT
CORE1_DSP_OR_PARALLEL_RENDER   = REJECT
PRODUCTION_MUTATION_PRE_AP_P4  = NO
```

It changes the target from “more scheduling” to **bounded ownership, coherent musical
identity and measurable freshness**. The explicit audio task is a disposable experiment,
not a presumed destination.

## 1. Authority and provenance stop

The active authority is
`docs/handover/HANDOVER_2026-08-14b_AP_INPUT_INTEGRITY.md`. It says production must remain
byte-inert until the AP-input-integrity programme's **P4** and authorises no further
physical microphone test under T0.3. This scheduling programme must refer to that gate as
**AP-P4** to avoid confusing it with its own Gate 4.

The audit is already provenance-stale:

| Evidence | Observed SHA |
|---|---|
| delegated scheduling reports | `b80e4ada...` |
| reconciled audit | `8026807f...` |
| this review | `15d3a85d...` |

From `b80e4ada` to this review's SHA, decision-relevant AP files changed, including
`audio/i2s_audio.h`, `audio/k1_ap_drive_contract.h`,
`audio/k1_ap_structured_evidence.h`, `system/globals.h` and their host harnesses. The later
change introduces and then isolates the AP silence-candidate timer. It does not overturn
the AP0/VP1 or publication-race findings, but it changes the exact AP service path whose
cost and behaviour must be baselined.

**Stop rule:** no implementation ticket may cite this pack until Gate 0 records one exact
implementation SHA or proves, file by file, that every decision-critical delta is
irrelevant. Any later change to the AP loop, render loop, GDFT, publication, effect queue,
task creation, persistence or build flags invalidates downstream runtime evidence and
returns the programme to the earliest affected gate.

## 2. Acceptance ownership — no self-certification

| Role | May author | May accept |
|---|---|---|
| Production-lane agent | its assigned source and tests | **No** acceptance of its own lane |
| Harness owner | oracle, parsers, fixtures and fault battery | no production change that it judges |
| Independent gate runner/orchestrator | clean-worktree build, tests, artefact hashes, post-integration rerun | host/build/runtime metric gates, if it did not author the candidate |
| Captain | product contracts, AP-P4 permission, audible-real-music witness, perceptual/physical promotion | human and physical gates only |
| PLC/graph-loop or another agent fleet | bounded units after Gate 0 | **Never** its own gate; it may not modify the oracle, fixtures, CI or acceptance thresholds |

The repository's current tests are useful but are not, by themselves, an independent trust
root. Until a protected CI/gate runner exists, the minimum substitute is a clean
post-merge worktree run by the orchestrator, with the harness/fixture hashes frozen before
the production lane starts. That is suitable for bounded execution, not a claim of
unattended autonomous promotion.

`PASS` means the independent owner reproduced the required artefacts. “Agent says tests
passed”, “source contains the intended symbols”, a scalar FPS value, or an instrumented
binary passing its own parser is not acceptance.

## 3. Oracle portfolio and reusable surfaces

Inventory before invention:

| Boundary | Existing reusable surface | What it currently proves | Missing proof to add |
|---|---|---|---|
| AP cadence/service | `device_ap_cadence_capture.py`, `k1_real_music_corpus_capture.py`, APCAD firmware rows | bounded scalar/stage timing and declared cadence in probe builds | exact current-head freshness/backlog and minimally instrumented paired control |
| GDFT geometry | `gdft_center_honesty_model.py`, `test_gdft_center_honesty.py`, `gdft_check.py` | source/model parity, bin geometry and diagnostic schema | selected service contract's current device cost and product A/B |
| Semantic mapping | `test_semantic_state_replay.py` | current semantic forwarding/replay behaviour | one common frame generation, state/event timing and forced interleaving |
| Onset/beat | `test_onset_beat_replay.py`, onset event metrics | replay semantics for current event surface | sequence/count semantics when AP advances more than VP |
| Control scenes | `test_effect_queue_static.py`, `test_show_state_static.py` | current key/transition/storage structure | C++ happens-before, scene atomicity, ordered edge overflow and forced races |
| WDT/IDLE | `test_i2s_watchdog_static.py` | structural bounded read, WDT feeds and real one-tick IDLE slot | on-device normal-soak and deliberately faulted efficacy |
| Render trace | `test_render_trace_static.py`, VPAB and `k1_trace_capture.py` | diagnostic structure and partial render traces | full frame/show/RMT completion plus producer acknowledgement |
| Instrumentation boundary | `test_dev_instrumentation_boundary.py` | production exclusion of trace/diagnostic surfaces | proof that trace overhead does not manufacture the result |
| Production isolation | `mic_stable_byte_gate.sh`, radio-isolation guard | protected production bytes/radio absence within their envelopes | authorised post-AP-P4 behaviour-delta manifest |

The portfolio should use exact/differential tests where deterministic, property and
metamorphic tests for interleavings, and current-device paired experiments for timing and
perception. Do not force one golden master onto nondeterministic task timing.

## 4. Gate 0–8 DAG

```text
                         AP-P4 (external authority)
                                  |
G0 authority + contracts + fault-evident oracle
                                  |
                                  +---- AP-P4 ----> G1 exact-head baseline
                                                     |
                                                     v
                                              G2 GDFT contract
                                                     |
                                                     v
                                           G3 coherent AP frame
                                                     |
                                                     v
                                       G4 transactional controls/scenes
                                                     |
                                                     v
                                           G5 complete causal proof
                                                     |
                                      trigger true?  |  trigger false
                                             +-------+-------> close G6 NOT_REQUIRED
                                             v
                                     G6 explicit-audio-task A/B
                                             |
                                             v
                                  G7A service request isolation
                                             |
                                             v
                                  G7B flash/cache coexistence
                                             |
                                             v
                                      G8 integration/promotion

Radio promotion and 24 kHz/180-bin spectral work are separate DAGs. They do not enter G8.
```

Gates run on post-integration HEAD. Each behaviour-changing gate is one independently
revertible unit. G3 and G4 are ordered to minimise simultaneous ownership changes; that is
not a claim that their source edits are necessarily file-dependent.

## 5. Gate contracts

### Gate 0 — authority, timing contracts and oracle qualification

**Purpose:** freeze the exact implementation SHA, resolve 100 versus 120 FPS, define each
latency origin/end boundary, define tolerances from observed baseline variance, and prove
the harness rejects known faults before production work begins.

**Dependencies:** none for document/harness design; AP-P4 is required before any production
firmware mutation or physical scheduling test.

**Acceptance owner:** Captain for cadence/feature/physical-latency semantics; independent
harness owner plus gate runner for provenance and the fault battery.

**Positive tests:** three or more identical host replay/model runs; exact match wherever
deterministic; stable empirically characterised variance elsewhere; manifest resolves
source SHA, toolchain, build flags, device identity, config/NVS/calibration epoch, fixture,
mode pair and instrumentation state.

**Required RED witnesses:**

1. alter the expected SHA, build flag, sample tuple or mode pair — provenance gate rejects;
2. remove a required trace field or regress a timestamp — parser fails closed;
3. corrupt a frame generation — causal checker rejects;
4. delete/skip a required test or alter a frozen fixture — trust-root diff rejects;
5. enable a known perturbing stream or use the wrong device identity — run is inadmissible.

**Stop/rollback:** an uncaught mutation is an oracle blind spot, not a soft warning. No
production lane starts. Repair the harness and repeat the complete Gate 0 battery. If the
100/120 FPS or feature-latency contract remains unresolved, scheduler/pacing experiments
remain prohibited.

### Gate 1 — exact-current-head production baseline

**Purpose:** measure the current 12.8 kHz / 96 / d3 shipping contract before changing it.

**Dependencies:** Gate 0 and AP-P4.

**Acceptance owner:** gate runner owns build, identity and metrics; Captain confirms the
real-music fixture is audible at the correct level. The candidate author does not run the
acceptance capture alone.

**Positive tests:** exact production-equivalent binary plus a paired trace build whose
behavioural sections are reconciled; current GDFT flags; ordinary serial streaming off;
quiet plus Captain-confirmed real music; worst enabled primary/secondary pairing and
simultaneous crossfade. Record AP service/wait/backlog/sample-age, publication age, VP
whole-frame/RMT boundaries, task runtime, stack high-water and WDT state.

**Required RED witnesses:** parser rejects wrong chip identity, stale boot epoch, mismatched
sample tuple, missing audible confirmation, missing crossfade/mode manifest, capture drops
or an instrumentation build not matched to its minimally instrumented control.

**Stop/rollback:** there is no candidate to roll back. If current service cannot sustain
arrival or the two paired builds disagree beyond characterised instrumentation overhead,
classify the failure and proceed only to Gate 2/harness repair. Do not tune priority.

### Gate 2 — select the GDFT service contract

**Purpose:** decide the transform/window contract before scheduler mechanics.

**Dependencies:** Gate 1.

**Lane:** separate **behaviour-changing spectral-service lane**. It may change frequency
resolution, transient age and visual response; it is not a refactor hidden inside a timing
ticket. The 24 kHz/180-bin proposal is excluded.

**Acceptance owner:** independent gate runner for model/build/device metrics; Captain for
pre-registered perceptual comparison.

**Positive tests:** source/model parity; spectral geometry and representability; current
formula against shorter-window candidates such as provisional `x2_cross=40` and global
legacy `x2`; same device/music/config; sustainable AP service with margin, bounded sample
age/backlog and no tempo/onset/chord/render regression within the newly defined feature
contracts.

**Required RED witnesses:** mutate crossover/formula without updating the manifest; inflate
one live-bin loop count beyond the service budget; corrupt a centre coefficient; remove a
bin or schema row. The host/model/schema and device service oracles must detect their
respective fault classes. A synthetic host fault is not a substitute for the real-music
device A/B.

**Stop/rollback:** if no candidate meets both service margin and product behaviour, retain
the current formula and reopen the product cadence/feature contract. Never hide the
deficit with a larger hop or priority change. Reverting Gate 2 must be one atomic commit.

### Gate 3 — one coherent AP state/event frame

**Purpose:** make every VP frame consume one complete musical generation with truthful
timestamps and loss-aware event semantics.

**Dependencies:** Gate 2.

**First candidate:** Core 0 copies one complete `K1AudioFrame` plus generation under a
short `portMUX`; Core 1 copies it once at frame-top into VP-local storage under the same
lock; all downstream consumers receive that local `const` view. The lock encloses only
copy/generation publication. An unowned two-slot pointer swap is rejected. If copy cost
fails, use explicit three-slot ownership whose reuse safety is mechanically tested.

**Frame contract:** state includes generation and distinct read/sample-estimate/publish
times. Onset and beat use monotonic sequence, last-event time/strength and count since prior
publication; a transient boolean is not the event contract. Every-event forensic capture,
if required, uses a separate bounded ring with a drop counter.

**Acceptance owner:** harness owner accepts host oracle; gate runner accepts device lock and
freshness metrics; neither may be the production author.

**Positive tests:** fixed fixture produces only a complete old or complete new frame;
VP-local frame is stable for the entire render; multiple AP events between VP frames are
coalesced according to the declared policy; every enabled VP consumer uses the same
generation; `mixed_generation_count == 0`.

**Required RED witnesses:** pause producer after every field/array segment; pause consumer
during acquisition and during a 40 ms simulated render stall; publish generation early;
wrap generation/sequence counters; reuse a two-slot pointer while held; delete one event
increment; reintroduce a direct Core-1 read of live `spectrogram[]` or waveform globals.
Forced-interleaving and structural ratchets must go RED.

**Runtime numbers:** producer/consumer lock hold and wait p50/p95/p99/max, AP throughput,
sample/publication/VP-generation age and VP whole-frame cost.

**Stop/rollback:** any hybrid frame, sequence loss outside declared coalescing, direct AP
global read, unbounded critical section or material AP/VP regression rejects the candidate.
If whole-frame copy fails only on lock/copy margin, roll back that candidate and try owned
triple buffering; do not fall back to an unowned two-slot pointer.

### Gate 4 — transactional control and scene publication

**Purpose:** match the primitive to command semantics while keeping transition runtime
Core-1-owned.

**Dependencies:** Gate 3.

| Command class | Required primitive |
|---|---|
| complete desired state | static depth-one/latest-wins mailbox |
| complete two-channel scene | one immutable payload plus one scene generation |
| non-idempotent edge | small bounded ordered queue with sequence/drop counter |
| diagnostics/history | bounded ring; never block AP |

**Acceptance owner:** independent host gate owner, then gate runner for device frame-boundary
and control-latency evidence.

**Positive tests:** repeated state commands coalesce to the newest complete state; scene
applies both channels at one generation/frame boundary; edge commands preserve order and
execute once; overflow follows the documented reject/drop policy and increments a visible
counter; Core 0 never reads transition-runtime internals.

**Required RED witnesses:** publish generation before payload; interrupt each multi-field
copy; overflow the edge queue; duplicate/regress an edge sequence; issue a command during
dip/crossfade; corrupt one channel of a scene; replace the transaction with a
`volatile`-only flag. Each must fail structurally or behaviourally.

**Stop/rollback:** mixed-channel scene, lost/duplicated edge without declared counter,
blocking hot-path operation, or Core-0 ownership leak rejects and reverts the unit. Do not
weaken the event class to “latest wins” to make a test green.

### Gate 5 — complete causal proof

**Purpose:** carry one identity from I2S/sample estimate through final RMT completion and
establish that the proof apparatus does not manufacture its own result.

**Dependencies:** Gates 2–4.

**Acceptance owner:** harness owner signs trace integrity; independent gate runner captures
and analyses; Captain owns any acoustic-to-photon/perceptual boundary.

**Positive tests:** every admitted record contains ordered
`capture_sequence -> i2s_read_return -> sample estimates -> AP stages -> AP publish -> VP
acquire -> render start -> quantised bytes -> RMT submit -> RMT complete`; producer-owned
trace slots commit after payload copy; stop request receives producer acknowledgement;
instrumented and minimally instrumented paired runs agree inside empirically derived
overhead.

**Required RED witnesses:** omit/reorder a boundary, regress time, duplicate generation,
fabricate completion from submission, dump before producer acknowledgement, corrupt CRC,
overflow a ring without a drop count, or copy the large trace payload inside the critical
section. Parser/oracle must fail closed.

**Stop/rollback:** missing causal boundary, unexplained instrumentation delta, capture loss
or unknown sample-time assumptions means **NOT PROVEN**. G6/G7 cannot use the trace for
attribution. Fix the trace lane; do not reinterpret scalar APCAD/VPAB as causality.

### Gate 6 — conditional explicit audio-task experiment

**Entry predicate:** Gate 5 attributes a pre-registered material fraction of AP tail or
freshness failure to serial/control/service scheduling rather than GDFT service demand. A
threshold must be fixed at Gate 0/5; it may not be invented after seeing the A/B.

**Dependencies:** Gate 5. If the predicate is false, close as `NOT_REQUIRED`, not `PASS`.

**Lane:** reversible scheduler experiment. It does not authorise per-stage actors.

**Acceptance owner:** independent paired-experiment gate runner.

**Positive tests:** one DMA-paced `k1_audio_task` contains the complete AP transaction;
lower-priority service loop owns serial/control/persistence requests; AP0/VP1 remains;
IDLE0 receives service; stack/runtime and control latency remain bounded; the paired A/B
meets the pre-registered improvement without feature/render/WDT regression.

**Required RED witnesses:** inject bounded service bursts in the service loop; restore a
service call to the audio task; use a deliberately wrong priority; remove the IDLE delay;
starve the service loop; force task-creation failure. The oracle must detect AP interference,
WDT/IDLE risk, control starvation and the visible required-task failure state.

**Stop/rollback:** no material paired improvement, any regression, or unproved IDF/driver
interaction discards the candidate and locks the simpler two-task topology. “Cleaner task
diagram” has zero acceptance weight.

### Gate 7 — service request isolation, then flash/cache coexistence

**Dependencies:** Gate 5 and the Gate 6 topology decision.

**Gate 7A, no filesystem:** represent persistence as a bounded/coalescing request with
immutable data; exercise success, overwrite and failure using a stub worker. This proves
service ownership only.

**Gate 7B, real flash:** separately prove cache-disable behaviour, render/cache safety,
park acknowledgement, save coalescing, retry/failure stance, service duration, AP
discontinuity policy and core placement. A task migration is not evidence that flash is
safe.

**Acceptance owner:** independent host fault runner for 7A; device gate runner for 7B;
Captain only where an authorised device/persistence mutation is required.

**Required RED witnesses:** request saturation; stale/partial payload; missing park
acknowledgement; cache-disable during render access; filesystem error; restart mid-save;
retry storm; forced long service. The system must fail closed or expose the explicitly
chosen retry/degrade behaviour, never silently proceed after a timeout.

**Stop/rollback:** 7A may land only if it is useful without real flash and remains bounded.
Any 7B red rolls back actual flash servicing while retaining, if independently valuable,
the proven request boundary. No production save path is promoted from host-only proof.

### Gate 8 — integrated promotion on one HEAD

**Purpose:** prove the final selected compact architecture, not the union of every tested
candidate.

**Dependencies:** Gates 0–5, a closed Gate 6 decision, and Gate 7 if persistence was in
scope. AP-P4 and every relevant Captain gate must already be satisfied.

**Acceptance owner:** independent clean-worktree gate runner; Captain signs perceptual and
physical claims. Production authors and autonomous agents cannot approve.

**Positive tests:** full host suite/build; no deleted/newly skipped tests; oracle coverage
unchanged or higher; post-merge causal/device gate; authorised byte-delta manifest; task
creation visible; production instrumentation/radio boundary preserved; one record traced
end to end; rollback artefact proven usable.

**Required RED witnesses:** modify a golden/harness/CI/threshold from a production lane;
delete/skip a test; omit a manifest delta; flash a wrong identity; reintroduce direct AP
globals, volatile-only transactions, heap/blocking AP operations or a FIFO of newest-only
audio frames. The integration gate must reject each class.

**Stop/rollback:** any red blocks promotion and reverts the smallest behaviour-changing
unit. Never re-baseline a golden merely because the candidate changed it. A golden update
requires a separately approved behaviour-change ticket and Captain/device A/B where
applicable.

## 6. Structural ratchets required before promotion

At minimum, make these executable rather than prose:

```text
Core-1 code cannot read live AP spectrogram/waveform globals
every VP effect receives one const K1AudioFrame or approved derived view
all state consumed in a VP frame carries one AP generation
onset/beat edges use sequence/count semantics
mode/scene payload is complete before publication generation changes
no volatile-only multi-field commit protocol
no heap, blocking mutex/queue or filesystem call in AP hot path
no FIFO queue for newest-only AP frames
mixed_generation_count == 0
required task-creation failure is latched and visible
trace dump requires producer stop acknowledgement
```

A text-presence assertion is insufficient when a small host executable can exercise the
real C++ publication primitive. Static tests protect ownership boundaries; forced
interleaving/property tests protect behaviour; device traces protect timing.

## 7. Behaviour-changing lane separation

| Lane | Behaviour posture | May share a commit with |
|---|---|---|
| contracts/provenance/oracle | no production behaviour | only its own harness/trust-root work |
| GDFT service contract | intended spectral/timing/perceptual change | no publication, scheduler or radio work |
| coherent AP frame/events | correctness change; output may change by eliminating hybrids/lost edges | its own tests only |
| control/scene transactions | correctness change | its own tests only |
| trace instrumentation | non-shipping evidence change | no production algorithm change |
| explicit audio task | reversible scheduling experiment | no GDFT, persistence/flash or radio change |
| persistence request boundary | service ownership change | no actual flash/cache change |
| flash/cache coexistence | operational side-effect change | no scheduler or radio change |
| BLE/Wi-Fi promotion | **separate programme** | none of this DAG |
| 24 kHz/180-bin spectral upgrade | **separate bench programme** | none of this DAG |

One unit, one owner, one atomic commit, one independent gate. Parallel agents may develop
independent harness or analysis work, but decision-critical production units advance
serially through the DAG. PLC graph-loop, if deliberately invoked later, remains a manual,
allowlisted external process; it must not auto-trigger and must not own or edit its gate.

## 8. Cynefin, systems and TRIZ check

- **Clear:** structural prohibitions and provenance ratchets. Automate them.
- **Complicated:** frame ownership, command classification, timing definitions and flash
  safety. Use expert analysis plus deterministic host oracles.
- **Complex:** current-device scheduler interference, perceptual GDFT knee and
  instrumentation effects. Use bounded paired probes, not architectural prediction.
- **Chaotic:** none. A broad rewrite or emergency priority raise is unjustified.

The central TRIZ contradiction is: VP needs a stable whole frame for as long as rendering
takes, while AP must publish a newer frame every 7.5 ms without blocking. Separate in
space/ownership: a short shared copy plus VP-local immutable copy, with owned triple slots
only if measured copy cost fails. This resolves lifetime and freshness without actor queues.

The main system feedback trap is:

```text
service deficit -> backlog -> apparently faster I2S returns -> stale semantics
                -> priority/task patch -> less IDF/IDLE service -> new tail/fault
```

Gate 2 attacks service demand; Gates 3–4 fix information/ownership; Gate 6 is admitted only
when Gate 5 proves scheduler interference remains. That is the smallest leverage sequence.

## 9. Margin-of-safety rule

Do not promote a candidate merely because p95 fits the nominal 7.5 ms AP or 8.33/10 ms VP
period. The current uncertainty includes current-formula AP tails, descriptor backlog,
instrumentation overhead, crossfade outliers, RMT completion and flash/cache effects.

Gate 0 must pre-register a margin derived from measured p99/max sequences and the cost of a
breach. Until that evidence exists, no universal numeric percentage is honest. At minimum:

- mean sustainable AP service rate must remain below arrival demand with bounded consecutive
  over-period sequences and sample age;
- one worst observed frame cannot consume all DMA cushion without an explicit recovery
  proof;
- lock/copy p99/max must leave measured AP and VP slack, not merely average slack;
- queue/ring capacity must be justified from measured burst and drain rates, with visible
  saturation rather than silent loss.

Optimising exactly to the nominal period is a red result for a production music instrument,
not efficient engineering.

## 10. Final decision

**ACCEPT Captain's architecture destination. AMEND the original audit execution section to
this Gate 0–8 proof DAG before authorising implementation.**

Do not launch an autonomous production fleet yet. Gate 0 is not closed, AP-P4 still owns
the production-mutation boundary, the exact-head baseline is absent, and the current oracle
portfolio has not been shown to catch the proposed concurrency/timestamp faults. Once Gate
0 is fault-evident, the work is naturally decomposable into small, revertible units; until
then, autonomy would scale plausible self-certification rather than evidence.
