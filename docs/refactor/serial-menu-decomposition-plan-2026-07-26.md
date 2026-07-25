---
abstract: "M2.1 serial_menu.h decomposition — scoped, harness-first plan (NOT started). The behavioural oracle exists AND its CI gate is SOUND: harness_selftest.py (run by test_golden_master.py) rglobs the tree and CAUGHT all 18 serial_replay mutations on HEAD f23bea3 (orchestrator-confirmed 2026-07-26). The scare — oracle_serial_replay.py --verify-mutations reporting 17/18 inert — was a STALE STANDALONE PROBE (hardcodes serial_menu.h) not a rotted gate; canonical Gate-0 for this repo is harness_selftest.py, not per-oracle --verify-mutations. Small R0 hygiene: fix/retire that standalone path. Then R1 (move 104 non-inline defs -> serial_menu.cpp, kill the ODR bomb) + R2 (table-migrate the 79 =value setter arms). Clamp-gap fixes ride a SEPARATE behaviour-changing ticket. Read before touching serial_menu.h."
---

# M2.1 — serial_menu.h decomposition (harness-first plan, NOT started 2026-07-26)

Scoped 2026-07-26 (2 read-only scouts + orchestrator Gate-0 run). **No product code edited.** Captain approved the *approach*; execution deferred to fresh context. Follows the `autonomous-agentic-build` skill (harness IS the product).

## Current reality (audit 2026-06-23 is STALE)
- `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` is **4,329 lines** (was 6,191). A prior extraction already lifted setter bodies into `serial/serial_cmd_handlers.cpp` (1,948 L), `serial_tx.cpp`, `serial_parse_helpers.cpp`, `k1_ap_capture_telemetry.cpp`.
- **ODR bomb:** 104 non-inline, external-linkage function defs at file scope (0 inline). Legal only because exactly ONE TU includes it (`.ino:44`). `visual/lightshow_modes.h:15` already calls it "an ODR hazard."
- `parse_command()` @2757-~3797 (~1,040 L): table consult first (Row-1 `serial_cmd_table.def`, 34 rows, static_assert-guarded) then a **~79-arm strcmp/strncmp ladder** for `=value` setters, with **14 `#ifdef` feature gates** interleaved.
- `build_src_filter` already globs `+<serial/*.cpp>` → a new `serial/serial_menu.cpp` auto-compiles, **no platformio.ini change**.

## The oracle (Step-0 inventory — it EXISTS, is well-built)
- `scripts/regression-harness/golden/oracle_serial_replay.py` (1,068 L): host-compiles the REAL `parse_command`, drives a 100+ cmd corpus, captures per-command TRIPLE = emitted text + CONFIG-field delta (`snapshot()` ~65 fields) + side-effect flags (`save_config`/`save_config_delayed`/`reboot`/`bad_command`). Golden `tests/golden/serial_replay.golden.jsonl`.
- `oracle_serial_struct.py` (630 L): verbatim-lift statement-identity + dispatch-routing lock for function-call families (`set_mode`, queue, `smart_*`, `edgemixer`) that can't host-run. Golden `tests/golden/serial_struct.golden.jsonl`.
- Gated by `tests/test_golden_master.py` (`test_manifest_integrity` checksum anti-gaming + `test_oracles_reproduce_golden`) + `harness_selftest.py` Gate-Fα. Registered in `ORACLE_MODULES` (:43/:48).

## Gate 0 FINDING — RESOLVED: the CI gate is SOUND; only a standalone probe is stale
`oracle_serial_replay.py --verify-mutations` (the `__main__` convenience path) on HEAD `f23bea3` reported **17/18 mutations MISSED — "regex did not match."** That path hardcodes `serial_menu.h` as the mutation target (comment :713 "All are edits to serial_menu.h's setter handlers"), written before the handler bodies were lifted to `serial_cmd_handlers.cpp` — so post-lift the anchors aren't found *there*.
- **RESOLVED (orchestrator re-ran the authoritative CI self-test, 2026-07-26):** `harness_selftest.py` `_mutated_capture` (the path `tests/test_golden_master.py` actually runs) does NOT hardcode a file — it `rglob`s the whole firmware copy and mutates whichever `.cpp`/`.h` matches each pattern. It therefore finds the moved anchors in `serial_cmd_handlers.cpp` and **CAUGHT all 18 serial_replay mutations** (every one of the "MISSED" set shows `[PASS] regression CAUGHT`). **The CI trust root is intact; the earlier scare was a stale standalone probe, not a rotted gate.**
- **Residual R0 (now small, harness-only):** either (a) make `oracle_serial_replay.py`'s `__main__ --verify-mutations` tree-search like `harness_selftest` (so the standalone probe stops lying), or (b) delete it and point developers at `harness_selftest.py`/`test_golden_master.py` as the canonical Gate-0. Then the oracle is trustworthy AND self-consistent. This is a prerequisite hygiene fix, not a blocker on the whole battery. **Lesson: `harness_selftest.py` (not the per-oracle `--verify-mutations`) is the canonical Gate-0 for THIS repo — the per-oracle path can go stale after an extraction.**

## Plan (execute fresh; each unit small + independently revertible; gate runs in infra)
- **Phase R0 — repair the trust root (harness-only, FIRST):** resolve the ambiguity above; re-point the 17 orphaned mutations at their real current locations (mostly `serial_cmd_handlers.cpp`); make "regex did not match" a HARD FAIL; re-freeze Gate 0 so all mutations CAUGHT + a positive control (clean case passes). Only then is the oracle a trustworthy gate.
- **Phase R1 — kill the ODR bomb (behaviour-preserving, the real M2.1 win):** create `serial/serial_menu.cpp`; move the 104 non-inline bodies out of the header (declarations stay), **in family batches**, preserving the 14 `#ifdef` gates + exact command spelling. After each batch: `pio run -e k1_prod_im73d` clean AND `oracle_serial_replay` reproduces the golden byte-for-byte → commit; divergence = behaviour changed → revert. Close-out: a 2nd throwaway TU `#include`s the header + compiles → ODR bomb defused.
- **Phase R2 — finish the table migration (later, bigger):** extend the `serial_cmd_table.def` row shape to carry typed args (current handler is `void(*)()`), migrate the 79 `=value` setter arms. `oracle_serial_struct` locks the function-call families.

## SEPARATE behaviour-CHANGING ticket (NEVER fold into R0/R1/R2 — will intentionally re-baseline the golden)
Converge serial setters onto the `control/k1_control_facade.cpp` validate→apply→structured-result model (`k1_control_apply`, `needs_number_range`, `strlcpy`). Current clamp gaps on main:
- `serial_menu.h:3703-3704` `SECONDARY_MODE` alias: `atoi(command_buf + 15)` reads one byte past the 14-char literal (`"SECONDARY_MODE5"` drops the first digit). STILL EXISTS.
- `serial_menu.h:2806/2818` fixed `command_type[32]` / `command_data[94]` copy loops silently truncate long tokens; no explicit NUL-on-full. STILL EXISTS (core parser).
- `serial_menu.h:3401/3405/3415/3419` `silence_enter/exit/rms_enter/rms_exit` = `(float)atof` unclamped, no `bad_command`; `silence_dwell` `:3409` `atol` unclamped. **Currently OUTSIDE golden coverage** — add corpus rows BEFORE moving them.
- Note: the audit's `SENSITIVITY=atof` (~:4585) is already CLOSED (`serial_cmd_handlers.cpp:272` clamps via `constrain`).

## Key files
`serial/serial_menu.h`, `serial/serial_cmd_handlers.cpp`, `serial/serial_cmd_table.def`, `control/k1_control_facade.cpp`; `scripts/regression-harness/golden/{oracle_serial_replay,oracle_serial_struct,harness_selftest}.py`; `tests/test_golden_master.py`; `tests/golden/{serial_replay,serial_struct}.golden.jsonl`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-26 | agent:claude-code | Created — M2.1 scoped (2 scouts + Gate-0). Oracle exists but mutation battery partly rotted (17/18 inert); R0 repair must precede R1 body-extraction + R2 table-migration. Clamp gaps fenced to a separate behaviour-changing ticket. Not started. |
