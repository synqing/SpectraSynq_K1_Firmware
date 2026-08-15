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
