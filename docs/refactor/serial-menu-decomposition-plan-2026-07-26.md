---
abstract: "M2.1 serial_menu.h decomposition — R1+R2 COMPLETE (2026-07-26): 104/104 defs in serial_menu.cpp; 151-row SERIAL_TYPED_CMD_TABLE; parse_command strcmp ladder retired; golden + Gate-Fα green. Clamp-gap fixes ride a SEPARATE behaviour-changing ticket."
---

# M2.1 — serial_menu.h decomposition (R1+R2 COMPLETE 2026-07-26)

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

## R1 EXECUTION STATUS — COMPLETE (2026-07-26)

Branch `feat/serial-menu-decomposition-r1` off `main` `1c131a9` (local, unpushed — Captain merges). Batches 1–5 moved 26 defs leaf-first; **batch 6+ bulk move** (`scripts/refactor/r1_move_serial_menu_defs.py`) moved the remaining **78 defs** in one gate-green pass (including `init_serial`, `dump_info`, `parse_command`, `check_serial`, all `cmd_*`, hotkey helpers, queue helpers, `stream_*`, etc.). Close-out state:

| Metric | Value |
|--------|-------|
| Non-inline defs moved | **104 / 104** |
| `serial_menu.h` | **573 lines** (declarations + `inline constexpr SERIAL_CMD_TABLE[]` + integrity `static_assert`s only) |
| `serial_menu.cpp` | **4065 lines** (all moved bodies + substrate) |
| Golden reproduce | **PASS** (`test_golden_master.py` + `harness_selftest.py` → Gate-Fα PROVEN) |
| Builds | **PASS** `k1_hardware`, `k1_bench_im73d` |
| Host pytest (serial surface) | **702 passed** (5 skipped; 10 failures isolated to pre-existing `test_im73d_audio_eval_harness.py`) |

Supporting close-out edits (same branch, behaviour-preserving unless noted):
- `FIRMWARE_VERSION` → `system/constants.h` (`#ifndef` guard); `.ino` local `#define` removed.
- `vp_apply_profile` double-def resolved: body stays in `serial_menu.cpp`; duplicate removed from `k1_control_facade.cpp`.
- Oracle: `oracle_serial_struct.py` reads `serial_menu.h` + `serial_menu.cpp`; replay driver stubs for host-only symbols.
- Static tests: `tests/_fwpath.py::read_serial_menu_surface()` — grep h+cpp for moved bodies.

**R2 is COMPLETE** (2026-07-26 close-out). See `progress.md` §2026-07-26 R2.

### R2 EXECUTION STATUS — COMPLETE (2026-07-26)

| Metric | Value |
|--------|-------|
| Typed table rows | **151** (`serial_typed_cmd_table.def`) |
| Handler TU | `serial_typed_dispatch.cpp` (+ thin wrappers to `serial_cmd_dispatch_*`) |
| `parse_command()` body | **142 lines** (2530–2671): Row-1 table + typed lookup + deprecated `SECONDARY_*` tail |
| ODR smoke | `tests/test_serial_menu_odr_static.py` + `serial_menu_odr_driver.cpp` |
| Host mirror | `tests/test_serial_typed_dispatch_table_static.py` |
| Oracle updates | `oracle_serial_struct._routed` via typed wrappers; sever mutations target `return serial_cmd_dispatch_*` |
| Gates | pytest **718** pass; golden reproduce; Gate-Fα PROVEN; `k1_hardware` + `k1_bench_im73d` |

### Batches 1–5 (leaf-first, committed incrementally)

| Batch | Commit | Moved | Pattern proven |
|-------|--------|-------|----------------|
| 1 | `2a0a514` | 7 edge name/parse (`k1_edge_*_name`, `k1_parse_edge_*`) | pure leaves; NEW `serial_menu.cpp` + substrate + oracle `MODULE_CPPS` add |
| 2 | `bfcc3af` | 9 edge status/control (`k1_print_edge_status`, `serial_edge_*`) | with-deps, moved-sibling linkage, substrate growth (`serial_tx.h` + `vp_bool_text` decl) |
| 3 | `320fd62` | 5 vivid | static-test-anchored (re-point) + gated (`K1_VIVID_PRECOMP_V1`) |
| 4 | `23f00af` | 3 loud-guard + 1 beat-director status | multi-gate; needs `pio run -e k1_effect_framework` to validate the `K1_EFFECT_FRAMEWORK_V1` move |
| 5 | `1b45957` | 1 `k1_print_smart_status` | big status printer; OUTPUT-STRING static anchor (re-point) |

### Batch 6+ (bulk close-out, uncommitted at session start)

Moved ~78 remaining defs via `r1_move_serial_menu_defs.py` between `// --- R1 bulk move ---` / `// --- end R1 bulk move ---` markers in `serial_menu.cpp`. Landmines handled in the same pass:

- **`FIRMWARE_VERSION`**: relocated to `constants.h` so `init_serial` / `cmd_version` / `cmd_build` / `dump_info` / `cmd_help` could move.
- **`vp_apply_profile`**: duplicate in `k1_control_facade.cpp` removed (extern linkage to `serial_menu.cpp`).
- **Host oracle link**: replay driver stubs for `factory_reset`, `restore_defaults`, `clear_noise_cal`, queue transition scales, `raw_dump_request`, `vp_print_secondary_state`.
- **Static tests**: re-pointed to `read_serial_menu_surface()` across ~15 test files + `test_k1_av_regression_static.py` surface concat.
- **Substrate discipline**: `serial_menu.cpp` includes `serial_menu.h` (for dispatch-table types) but NOT `system.h` / `bridge_fs.h` / `presets.h` / `buttons.h` / `knobs.h` (inline ODR with `.ino`).

### The proven mechanism (per batch)
1. Move the body/bodies **VERBATIM** into `serial/serial_menu.cpp` (append; preserve source order for internal sibling calls; move `#ifdef` gates arm-for-arm). `serial_menu.cpp` includes the SUBSTRATE (`globals.h` + the `k1_*.h` stack + `serial_tx.h` + gated `beat_aware_director.h`) but **NEVER `serial_menu.h`** (avoids ODR double-def against the `.ino` TU).
2. Leave a DECLARATION (gated if the family is gated) in `serial_menu.h` at the same position.
3. `serial_menu.cpp` is in `oracle_serial_replay.py` `MODULE_CPPS` (added batch 1) — **REQUIRED** so the host oracle links the moved defs (the brief omitted this; it is the S4 `serial_cmd_handlers.cpp` precedent).
4. Still-in-header callee → forward-declare it (external linkage) in `serial_menu.cpp` (e.g. `vp_bool_text`).
5. Gate: `pio -e k1_prod_im73d` + `k1_hardware` clean AND golden reproduces byte-for-byte AND Gate-Fα intact; framework-gated moves ALSO need `pio -e k1_effect_framework`. Divergence = behaviour changed = revert.

### Landmines for the remaining ~74 (verify BEFORE each move)
- **Static-test anchors ≠ function-name grep.** Batch 5 broke 3 tests anchored on OUTPUT STRINGS (`SMART_TRANSIENT:` …), not the name. Grep `tests/` for the function name AND its distinctive echo tokens; re-point by searching the whole serial surface (`serial_menu.h` + `serial_menu.cpp`), non-weakening.
- **Host-stubbed subsystem calls = oracle-link trap.** `serial_queue_*`, `cmd_queue_commit`, `cmd_slot_list` call `sb_queue_*` (stubbed static/inline in the replay driver) → moving to a `MODULE_CPP` breaks the host link unless the stubs are promoted to guaranteed-external. AVOID until handled.
- **`vp_apply_profile` DOUBLE-DEF** — defined in both `serial_menu.h` AND `control/k1_control_facade.cpp` (both compiled via `build_src_filter +<control/k1_*.cpp>`). Firmware links today → exactly one is live (one must be gated). Resolve which links first. Skipped this session.
- **`FIRMWARE_VERSION`-blocked** (need a `FIRMWARE_VERSION`→header relocation first): `init_serial`, `cmd_version`, `cmd_build` (± `dump_info`, `cmd_help`).
- **`constexpr` table guards STAY** (implicitly inline; needed in-header for `static_assert`): `serial_table_all_have_handlers`, `serial_cstr_eq`, `serial_table_no_duplicate_names`, `serial_table_no_dangerous_hotkey`.
- **`parse_command` (~1040 L) + `check_serial` + `stream_*`: move LAST** (largest symbol/forward-decl surface).

### Recommended next safe batches (no landmine)
`cmd_*` leaves that only print globals/accessors (`cmd_chip_id/reset/reset_reason/fps/led_fps/stop/dump/get_num_modes/get_mode/identify/trace_dump/event_status/get_knobs/get_buttons/vp_out_test/bootloop_inject`); target print helpers (`serial_target_name/mode_name/print_mode_line/print_palette_line/print_target_float/print_target_bool`, `k1_confirmed_mode`); `vp_profile_name` + `vp_print_status` (skip `vp_apply_profile`); `k1_apply_smart_scene`; the hotkey help/status printers. For each: (a) no host-stubbed subsystem call, (b) grep tests/ for name AND output strings, (c) no facade double-def, (d) gated moves get their gate's build.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-26 | agent:claude-code | Created — M2.1 scoped (2 scouts + Gate-0). Oracle exists but mutation battery partly rotted (17/18 inert); R0 repair must precede R1 body-extraction + R2 table-migration. Clamp gaps fenced to a separate behaviour-changing ticket. Not started. |
| 2026-07-26 | agent:cursor | R2 COMPLETE — 151-row typed table; parse_command ladder retired; ODR smoke + host mirror tests; oracle struct/replay R2 routing; pytest 718; builds green. |
| 2026-07-26 | agent:cursor | R1 COMPLETE — batch 6+ bulk move (78 defs); header 573 L / cpp 4065 L; golden + Gate-Fα + k1_hardware + k1_bench_im73d green; static tests re-pointed via read_serial_menu_surface(); FIRMWARE_VERSION→constants.h; vp_apply_profile deduped. |
