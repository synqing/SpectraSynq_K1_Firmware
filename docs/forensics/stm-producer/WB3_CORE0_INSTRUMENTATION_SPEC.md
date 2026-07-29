# WB-3 Core-0 instrumentation specification (bench-only)

**Status:** Specification only — **no firmware instrumentation landed** (clangd Gate 0 + device allocation blockers).

## Measurement goals (H3)

| Signal | Location (to verify via clangd) | Statistics |
|--------|----------------------------------|------------|
| `k1_stm_process` wall time | Core-0 AP frame, around producer call | p50, p95, p99, max, over-budget count |
| Enclosing AP frame time | Same frame | same |
| Stack high-water | Audio task | Before/after 10 min soak |
| AP deadline misses | Existing timing guard | Count |
| Snapshot age | `K1AudioSnapshot` publish | Max ms |
| Render frame time | Core-1 | p95, max; require < 2000 µs |
| Dropped frames | Renderer | Count |

## Build matrix (plan §9.2)

| Env | Purpose |
|-----|---------|
| `k1_hardware` | Flag-off baseline (production shape) |
| `k1_bench_im73d_stm` | Native STM treatment (`-DK1_STM`) |
| Bench variants with effect framework/registry | Combined compile probe |

Instrumentation **must** compile only under explicit bench macros (e.g. `K1_STM_BENCH_TIMING=1`), absent from `k1_hardware`.

## Overhead control

Empty-span timing around no-op when macro enabled; delta vs macro disabled on same binary.

## Artefacts

```
artifacts/stm-core0/<run-id>/
  build_identity.json
  baseline_summary.json
  treatment_summary.json
  regression_notes.txt
```

## Hard stops (regardless of budget)

- WDT / reset marker
- AP deadline miss
- Frame drop
- Progressive heap/stack collapse
- Render > 2.0 ms sustained breach

See `WB3_CORE0_BENCH_PROCEDURE.md` for execution steps.
