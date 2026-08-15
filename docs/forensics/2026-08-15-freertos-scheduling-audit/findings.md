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
