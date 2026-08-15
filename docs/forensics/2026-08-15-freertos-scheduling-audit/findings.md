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
