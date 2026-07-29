# Gate 0 — clangd semantic tooling blocker (WB-3)

**Result state:** **INDETERMINATE** for symbol-level C++ verification this session.

## What was attempted

1. `tools/codex-clangd-mcp-reset.sh` from Lightwave-Ledstrip (hygiene only).
2. Cursor dynamic `cursor` namespace — **no `diagnostics` / clangd tools** exposed to this subagent session.

## Impact (RBDO DEGRADED-MODE)

| Unresolved assumption | Risk if wrong | Fallback |
|----------------------|---------------|----------|
| C++ call sites and guards match file-level grep on `origin/main` | Missed caller, wrong hook, false audit closure | **FALLBACK:** file:path + `git show origin/main:…` only; label claims **hypothesis** until clangd push-diagnostic smoke passes |
| Instrumentation insertion points | Wrong span, production leak | Bench-only flags; no C++ instrumentation landed this session |

**Revisit trigger:** clangd MCP available in agent session; run exactly one `diagnostics` smoke on `SpectraSynq_K1_Firmware` with `compile_commands.json` for `k1_hardware` / `k1_bench_im73d_stm`.

**Debt count:** 1 upstream fact → 6 audit hypotheses in `WB3_AUTHORITY_MAP.md` remain hypotheses.

## Allowed this session

- Git topology, registry, headers, host Python harnesses, documentation, `stm_vp_compare.py` (host-only).

## Forbidden until clangd clears

- Production C++ edits to producer, adapter, EdgeMixer, or render path claimed as verified symbol references.
