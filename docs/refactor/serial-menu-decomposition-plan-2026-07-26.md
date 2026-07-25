---
abstract: "M2.1 serial_menu.h decomposition — scoped, harness-first plan (NOT started). The behavioural oracle already exists (oracle_serial_replay.py + oracle_serial_struct.py, frozen goldens, CI-gated) BUT Gate 0 found its mutation battery partly ROTTED: 17/18 field-level mutations are inert because the handler bodies they patch were lifted to serial_cmd_handlers.cpp while the mutation regexes still target serial_menu.h. Phase R0 (repair/re-confirm the oracle's fault-evidence) MUST precede R1 (move 104 non-inline defs -> serial_menu.cpp, kill the ODR bomb) and R2 (table-migrate the 79 =value setter arms). Clamp-gap fixes ride a SEPARATE behaviour-changing ticket. Read before touching serial_menu.h."
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

## ⚠ Gate 0 FINDING (blocker — must resolve first)
`oracle_serial_replay.py --verify-mutations` on HEAD `f23bea3`: golden reproduces (determinism OK, 133 records) BUT **17 of 18 mutations MISSED — "regex did not match."** Cause: the field-level mutations (clamp, field-routing, echo, save-class-swap, secondary_*) still target `serial_menu.h`, but those handler bodies were lifted to `serial_cmd_handlers.cpp`; only `secondary_dispatcher_call_site_severed` (still in the header) CAUGHT. Classic skill hazard: *mutations go inert when the artefact is split; re-run Gate 0 after every change.*
- **Unresolved ambiguity:** `test_harness_selftest.py` passed earlier (~106 s) — so either the CI Gate-Fα uses a different (correct) file scope than the direct `--verify-mutations` path, OR it is rubber-stamping the inert mutations. **Resolve this BEFORE trusting the oracle** (read `verify_mutations()` file scope in oracle_serial_replay.py vs harness_selftest.py; check whether "regex did not match" hard-fails the CI gate).

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
