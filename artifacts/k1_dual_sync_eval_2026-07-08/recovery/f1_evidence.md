# F1 link-hardening evidence

Status: `COMMIT_READY`, not silicon verified.

## Implemented contract

- SyncLink starts before optional Remoted on a dual-role leader.
- Case A has a separate sync-only leader environment with no Remoted sources or
  symbols.
- Advertising and both scanner start paths expose checked controller state.
- UUID-first discovery uses both `onDiscovered` and `onResult`.
- `link up` means application-ready, not raw GAP connected.
- Negotiated interval, latency, MTU and PHY are stable exact read-backs.
- `:sync_status` replays one coherent current lifecycle snapshot for
  late-attaching host capture.
- Lifecycle publication and characteristic use are connection-generation
  bound.
- Periodic application GATT operations run on Core 1; callback-time clock
  responses preserve `t4` and generation.
- Delay5/delay20 remain explicitly timestamp-fake until F3.

## Validation

```text
Focused: 103 passed, 24 subtests passed
Full:    760 passed, 1 skipped, 86 subtests passed

k1_hardware                    SUCCESS
k1_sync_probe_main             SUCCESS
k1_sync_probe_main_sync_only   SUCCESS
k1_sync_probe_bench            SUCCESS
```

All probe dependency graphs report `NimBLE-Arduino @ 2.5.0`.

## Adversarial disposition

- Host late-attach review: repaired in F0b commit `a4c2408`.
- Embedded generation/concurrency review: `APPROVE`.
- Final independent F1 source review: `APPROVE`; no deterministic F2
  false-PASS or in-scope crash path found.

## Boundary

These are source, host-test and compile proofs. There has been no flash, serial
capture or silicon claim. The binaries above embed pre-commit provenance
`a4c2408` and must be rebuilt after the F1 commit before F2.
