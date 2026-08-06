# WB-3 Core-0 bench procedure

**Prerequisite:** Captain device allocation; MAC-verified flash; rollback image recorded in `device-build-registry.md`.

## Pre-flight

1. Confirm **not** on dual-sync recovery lane unless Captain re-scopes.
2. `esptool.py read_mac` → match registry row (`B489A500` for bench STM env).
3. Record `:build` git SHA, env, ELF hash.
4. **No audio playback** until Captain approves source, level, duration, stop command.

## Phase A — Instrumentation trust (no STM)

1. Flash bench build with timing macro ON, STM flag OFF.
2. 60 s ambient (no deliberate playback) serial capture.
3. Validate counters monotonic, no WDT.

## Phase B — Baseline (flag-off)

1. Five × 10 min repetitions, matched conditions.
2. Export timing summaries to `artifacts/stm-core0/`.

## Phase C — Treatment (`k1_bench_im73d_stm`)

1. Same repetitions with `-DK1_STM` enabled.
2. Compare distributions to frozen incremental budget (ratified before inspecting treatment).

## Phase D — System regression

1. Serial `s` — `showSkips=0`, failures=0.
2. Note render overbudget warnings.

## Current execution status (2026-07-29)

**INDETERMINATE** — see `WB3_CORE0_BENCH_INDETERMINATE.md`.
