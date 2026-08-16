# Findings — plan fold

## Accepted strategic invariants

- Preserve AP/Core 0 and VP/Core 1.
- Reject a broad RTOS rewrite, per-stage audio actors, speculative priority/pacing,
  DSP migration and parallel rendering.
- Reopen and measure the GDFT service contract before scheduler experiments.
- Keep the explicit audio task conditional on measured scheduler/service interference.
- Preserve production byte-inert status before P4.

## Amendments requiring plan changes

- Reject an unowned two-slot pointer swap. First candidate is a short `portMUX`
  shared-frame copy followed by one VP-local frame copy; use explicit three-slot
  ownership only if measured copy/lock cost fails.
- Continuous state and discrete musical events require different semantics.
- Latest-wins is valid only for complete desired state, not non-idempotent edges.
- Frame identity requires capture/read/publication/acquisition/render/RMT times with
  explicit timestamp assumptions.
- Product timing contracts must distinguish feature and physical boundaries.
- Service-loop extraction and flash/cache coexistence are separate gates.
- Add structural ratchets, fail-visible required-task creation, non-perturbing trace
  ownership, and exact-SHA provenance closure.

## Evidence boundary

These are plan requirements. They do not establish current device timing, lock cost,
sample freshness, stack margin, RMT completion timing or physical latency.

## Provenance reconciliation

- Delegated source reports began from `b80e4ada`.
- The reconciled audit was closed at `8026807fe9d501720fe0c835f2b0dad077437d76`.
- The plan-fold pass observed `15d3a85d6d26e9698039a5b0d39dbaa1569718b4`.
- Between the audit SHA and plan-fold SHA, `audio/i2s_audio.h` added a dedicated AP
  silence-candidate timer and its structural test. This changes the active AP path,
  but does not change the task topology, snapshot locking, mode/effect publication,
  GDFT formula or Core-1 render ownership conclusions.
- Implementation authority must freeze one exact SHA; historical device timing must
  remain labelled against the binary that produced it.

## Skill research

- Agent Reach health check selected Jina Reader for general web pages; Exa is not
  configured.
- The current skills.sh pages still do not provide a higher-authority FreeRTOS/K1
  planning skill than the repo-local embedded and architecture guidance. No install.

## Implementation authority and model synthesis — 2026-08-15

- Captain's new directive authorises the scheduling Gate 0-8 implementation and
  supersedes the scheduling lane's pre-implementation byte hold.
- The AP-input P4 promotion remains a distinct programme: do not bundle microphone
  slot/health/calibration changes into scheduling commits.
- Cynefin classification: governance and structural ratchets are clear; ownership and
  concurrency design are complicated; device timing and perceptual GDFT choice are
  complex safe-to-fail probes.
- Systems leverage order remains service demand -> freshness -> publication ownership ->
  scheduler experiment; priority changes cannot repay accumulated sample age.
- TRIZ separations retained: shared publication versus VP-local lifetime; continuous
  state versus discrete events; request isolation versus flash/cache coexistence.
- Margin values must be pre-registered from the exact baseline, not guessed from the
  nominal 7.5 ms/8.33 ms periods.
- Agent Reach used Jina Reader. Current skills.sh results list `embedded-systems`,
  `freertos` and `esp32-firmware-engineer`; none outranks current repo/source/ESP-IDF
  authority and none was installed.
- ESP-IDF 5.4.1 official documentation confirms the modified dual-core ESP-IDF FreeRTOS
  implementation and provides ring-buffer/idle-hook primitives. Primitive availability
  is not evidence that a new task or queue benefits K1.
- The installed generic actor skill's Core-1 DSP premise conflicts with K1's measured
  AP0/VP1 bulkhead. Retain bounded communication and stack/queue visibility only.
- Atomic Agents is not a firmware dependency. Writing-skills routes recurring rules to
  executable ratchets rather than a new project-specific prose skill.

## Gate 0 firmware-change preflight

**Current truth.** Production is one Arduino `loopTask` on Core 0 plus `led_task` on
Core 1. The VP loop is free-running, its documented whole-frame target is 8,333 us,
and the separately defined effect-code ceiling is 2,000 us. Current source still
permits mixed-age AP reads and volatile-only multi-field control commits. Current
device service, freshness and lock budgets are not proven.

**Change class.** Gate 0 is host-only verification infrastructure and authority
reconciliation. It changes no production firmware behaviour.

**Files and seams touched.** The unit may add a scheduling contract, provenance
validator, mutation/fault battery and host tests under the existing audit, script and
test trees. It may correct stale authority prose in the execution plan. It may not edit
the AP, VP, effect, control, persistence, PlatformIO or device-identity implementation.

**Known breakage avoided.** Do not introduce a pacing clock, task, queue, mutex, heap
allocation, radio flag, sample tuple or GDFT change. Do not conflate the separate
AP-input P4 lane with scheduling authority. Do not turn an expected hash into a
self-referential file hash or allow an implementation unit to update its own oracle.

**State ownership.** The Gate 0 contract is immutable input. The validator only reads
repo/run manifests. Mutation fixtures are created in temporary directories and never
replace the trusted files. The independent gate runner owns final acceptance.

**Runtime proof.** None is claimed by Gate 0. Its job is to fail closed on wrong
provenance, tuple, identity, mode-pair strategy, instrumentation state, trace schema,
fixture hash, test inventory and corrupted generation. Gate 1 owns device measurement.

**Minimal edit.** Reuse pytest, JSON and the existing device identity/build provenance
surfaces. Add no framework dependency and no generated binary fixture.

**Non-goals.** No production source change, build, upload, serial write, calibration,
music playback, timing claim, GDFT selection or scheduler experiment.

**Stop conditions.** Any required mutation that remains accepted, a non-deterministic
host result, a dirty/unresolved trust root, or an unowned acceptance edit blocks all
production work until Gate 0 is repaired and independently rerun.

## Exhaustive current-source synthesis

The seven manifest readers independently reconciled all 535 first-party source paths.
Decision-critical additions to the original audit are:

- the bounded I2S read can wait 100 ms, over thirteen nominal 7.5 ms arrivals; timeout
  semantics must be separated from ordinary service time in Gate 1;
- accepted calibration can synchronously persist from the AP/GDFT path;
- three LittleFS open-failure paths can leak the current LED park/lock state, and one
  direct blocking-flash path bypasses the normal park acknowledgement;
- saliency/onset event surfaces remain overwriteable between VP frames, while audio,
  semantic, onset and tempo snapshots have no shared aggregate generation;
- effect-queue payloads and commit flags remain plain/volatile shared fields without a
  complete release/acquire transaction;
- several shipped effects and smoothing/fade paths remain per-render-call rather than
  delta-time correct, so a cadence change would alter product motion as well as timing;
- current host FreeRTOS stubs erase real cross-core interleavings, and current trace /
  VPAB surfaces stop short of confirmed RMT completion and physical output;
- the 8,333 us whole-frame target, 2,000 us effect ceiling and older 100 FPS comments
  are genuinely inconsistent; Gate 0 therefore defines separate measured boundaries
  and does not add a pacing clock.

These findings strengthen the contained hardening order. They do not justify an actor
rewrite or a speculative priority change.

## RMT completion and payload lifetime

The exact local FastLED 3.10.3/ESP-IDF 5.4.1 sources establish:

- `FastLED.show()` copies/scales the K1 application buffers into FastLED-owned buffers,
  submits RMT asynchronously and returns before the new transfers complete;
- the current `show_us` metric therefore measures preparation/submission and any
  remaining wait from the previous transfer, not current physical completion;
- each default 160-pixel WS2812B channel uses about 5,080 us including the 280 us reset;
  two controllers overlap on distinct RMT channels but are software-skewed, not
  hardware-synchronised;
- FastLED waits for the previous same-controller transfer in the next `drawAsync()`,
  after its three-pass show path has already rewritten the retained internal payload.
  ESP-IDF requires that payload to remain unchanged until completion.

The K1 application buffers are safe to reuse after the copy; application double
buffering does not fix the internal FastLED payload lifetime. Gate 1 will add an exact,
trace-only RMT submit/TX-done oracle using static records and official completion
callbacks. Gate 5 will decide the production lifetime fence from measured evidence.

## Gate 1 trace-unit firmware preflight

**Current truth.** Gate 0 is independently accepted. The main production K1
`F887A500` is not currently enumerated. Bench `B489A500` is present on
`/dev/cu.usbmodem12401`; another enumerated USB serial does not match the registered
Unit 2 identity and is inadmissible. Existing AP/VP probes do not supply truthful sample
timestamps or current-transfer RMT completion.

**Change class.** Non-shippable scheduling trace instrumentation plus host/static
oracles. Production behaviour and default build flags remain unchanged.

**Files and seams touched.** One trace-only PlatformIO environment; fixed-size RMT
submit/completion instrumentation in `diag/`; bounded AP/VP timing fields at existing
acquire/publish/frame/show seams; parser/admission tests. Production algorithm files may
receive compile-gated calls only where the timestamp boundary physically exists.

**Known breakage avoided.** Do not relabel `show_us` as completion. Do not log, allocate,
wake a task or send a queue item from the RMT ISR. Do not edit generated `.pio/libdeps`.
Do not enable RMT DMA, serial streaming, radio, a pacing clock or a new audio task. Do
not use the mismatched Unit 2 identity or cross-flash `k1_hardware` onto the bench pinmap.

**State ownership.** Core 1 owns pending frame identity and submission. Each RMT channel
ISR owns its own fixed completion slot/ring and commits sequence last. Deferred dump is
the only reader. AP trace state is Core-0-owned; VP acquires published identity once.

**Runtime proof.** Link-map/static gates must prove both RMT symbols are wrapped and
both exact LED GPIO channels register official TX-done callbacks. Host fault tests must
reject missing wraps, wrong GPIO, incomplete records, overwrite and missing completion.
Build the production-equivalent and trace environments before any guarded bench upload.

**Minimal edit.** Reuse ESP-IDF 5.4.1 public RMT callbacks/wait APIs, existing VP perf /
APCAD capture ownership and current serial dump infrastructure. Static internal-RAM POD
storage only.

**Non-goals.** No Gate 2 GDFT change, Gate 3 publication change, Gate 4 control change,
production RMT backend replacement, physical timing claim or perceptual claim.

**Stop conditions.** Wrapper absence in the link map, callback registration failure,
anything other than exactly two admitted LED channels, ring overwrite/drop, unmatched
submit/complete, unbounded wait, trace perturbation above the Gate 0 margin, wrong device
identity or missing Captain-confirmed audible fixture rejects the trace run.

## Gate 1 connected-bench checkpoint

The B489A500 trace smoke closed the source/link/callback mechanism without claiming the
absent production baseline. Both exact wrappers linked, the allowlisted GPIO 4/5 build
uploaded through `/dev/cu.usbmodem12401`, and a bounded capture returned 64 contiguous
paired generations per channel with zero trace drops. Confirmed RMT durations were
primary p99 4955 us and secondary p99 4919.5 us.

Independent review then rejected the capture's original CRC seam: it hashed application
buffers before FastLED scaling/dithering. The corrected wrapper hashes the actual 480-byte
ESP-IDF payload and the caller can no longer supply CRCs. Host mutation proof and the main
trace build are green, but the bench disconnected before recapture; the earlier completion
timings remain valid while device final-byte identity is explicitly `NOT_VERIFIED`.

The truthful APCAD timestamp lane also worked: assumption ID 1 was explicit, generations
were contiguous, and timestamp order remained valid. However, short trace and minimal
bench captures both failed sustainable 7500 us AP service: 101.61 Hz / active p95 10008 us
and 95.57 Hz / active p95 11067 us respectively. Their ordering is not a trustworthy
instrumentation-delta estimate, but both independently trigger the execution plan's Gate 2
service-contract lane. Main F887A500, Captain-confirmed music, worst dual-channel crossfade
and acoustic-to-photon proof remain open; see `evidence/gate1-bench-trace-smoke.md`.
