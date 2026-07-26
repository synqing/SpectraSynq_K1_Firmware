# F0 host-trust evidence — 2026-07-27

Status: `VERIFIED` for host/compile scope. No silicon claim.

## Dependency resolution

| Environment | Declared | Resolved `library.properties` |
|---|---|---|
| `k1_sync_probe_main` | `h2zero/NimBLE-Arduino@2.5.0` | `version=2.5.0` |
| `k1_sync_probe_bench` | `h2zero/NimBLE-Arduino@2.5.0` | `version=2.5.0` |

## Validation

| Command | Result |
|---|---|
| `python3 -m pytest -p no:cacheprovider tests/test_dual_sync_oracle.py tests/test_dual_sync_probe_firmware_static.py -q` | 63 passed |
| `python3 -m pytest -p no:cacheprovider tests/ -q` | 731 passed, 1 skipped |
| `bash scripts/agent/pio-build.sh k1_hardware` | SUCCESS |
| `bash scripts/agent/pio-build.sh k1_sync_probe_main` | SUCCESS |
| `bash scripts/agent/pio-build.sh k1_sync_probe_bench` | SUCCESS |
| `bash -n scripts/dual_sync_probe/run_gate0_segments.sh scripts/dual_sync_probe/run_f2_abc.sh` | PASS |
| deprecated scratch runner | aborts with exit 64 |

The final adversarial SSA review is `VERIFIED` in
`recovery/ssa/f0_implementation_review.md`.

## Pre-commit build artefacts

These compile-gate artefacts embed parent HEAD `fe634bb`, as expected for a
pre-commit gate. They prove the exact-pin worktree builds; no binary was
flashed.

| Environment | Artefact | SHA-256 |
|---|---|---|
| `k1_hardware` | `firmware.elf` | `881165f06b32f808ae05baa5d5097bf0af29424218f5bebd2bb16e7a29a577ff` |
| `k1_hardware` | `firmware.bin` | `aa92c1c091d51956b1fad7ab280803e2abf2077c4a7dc42902c329791dbc394f` |
| `k1_sync_probe_main` | `firmware.elf` | `b67b7455ffc77de767202a7d091e025c0797073657896b50657b06ba80dc8d03` |
| `k1_sync_probe_main` | `firmware.bin` | `470f5b05ae06870610df736c98c6fb75e282a8f93fd6079ca39a679ef11708e7` |
| `k1_sync_probe_bench` | `firmware.elf` | `be4839c3a9dae78a1f3bb51ae957f57cedbbd128e3c208338e08e671133a9e5e` |
| `k1_sync_probe_bench` | `firmware.bin` | `2d6cc7b8cbcb2a521ff4f9e99414d36c0ce47a50f28392d8304764d9993768c1` |

## Boundary

- F0 proves the host oracle, capture controller, exact dependency resolution
  and compile surface.
- It does not prove BLE establishment, Link Ready on silicon, timing gates or
  Gate-0.
- F1 firmware and its sync-only environment remain a separate commit.
