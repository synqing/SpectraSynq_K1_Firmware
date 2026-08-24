# Harness seeds (Phase 0)

## Scope

This folder captures hostable test/probe seams already proven in-tree.

- `gdft` harness seed: from `diag/gdft_harness.h`
  - deterministic probe runner
  - synthetic sine injection
  - existing serial line shape (`GDFTP,...`)
- AP capture telemetry seed: from `serial/k1_ap_capture_telemetry.h/cpp`
  - telemetry buffers and stream state moved from static header-local symbols
  - production-gated and bench-only by feature flags

These seeds are intentionally non-shipping and should be moved into a shared harness
lane only when portability tests demand them.
