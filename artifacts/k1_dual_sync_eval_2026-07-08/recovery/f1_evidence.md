# F1 link-hardening evidence

Status: `COMPLETE`, not silicon verified.

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

## Committed artefacts

Commit and verified remote branch:

```text
862aea89efc1c0c98035268a1b2ecf1bc1bab6f2
```

Post-commit probe binaries:

| Environment | Embedded git | Firmware SHA-256 |
|---|---|---|
| `k1_sync_probe_main_sync_only` | `862aea8` | `e08c2e8629b8bf123489e8b5b6a44eb97ab49c9307ebfed036ff2279dbaaa861` |
| `k1_sync_probe_main` | `862aea8` | `e5b7210b8468c79b96921b3b9e7c78594789c1744a849586ab822b504947452e` |
| `k1_sync_probe_bench` | `862aea8` | `a83e1b798b9cc1a2c9bbd5860ac1f794dfdb29518e7ca1846d63e2886c6dc11b` |

## Adversarial disposition

- Host late-attach review: repaired in F0b commit `a4c2408`.
- Embedded generation/concurrency review: `APPROVE`.
- Final independent F1 source review: `APPROVE`; no deterministic F2
  false-PASS or in-scope crash path found.

## Boundary

These are source, host-test and compile proofs. There has been no flash, serial
capture or silicon claim. F2 must still verify chip identity, wiring, flashed
environment and runtime build provenance before evaluating Case A.
