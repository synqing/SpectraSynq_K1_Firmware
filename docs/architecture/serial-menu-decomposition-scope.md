---
abstract: "Phase A Lane 2 scoping report: the decomposition surface of serial/serial_menu.h (6191 lines / 221 KB, header-only, single-includer via the .ino). Maps the X-macro command table (.def, 31 typed rows + host-shared row1 test), the 2296-line parse_command else-if metadata dispatch (246 strcmp branches), 6 functional groups, the device-I/O coupling (1714 USBSerial, 42 save_config, reboot()), and the safe incremental extraction sequence into clean serial/*.cpp TUs. Verification is structural+behavioral (NOT numeric golden): the existing row1_dispatch_table_test.cpp host pattern + test_serial_hotkeys_static.py extend to lock the command surface. CRITICAL: globals.h does NOT include serial_menu.h (no inversion); serial/ is NOT in build_src_filter (new TUs need an entry). Read before touching serial_menu.h or proposing the first slice."
---

# Phase A · Lane 2 — serial_menu.h Decomposition (scoping report)

**Status:** scoped (read-only cartography; no firmware edited). **Pattern source:** [`gdft-decomposition-lane.md`](./gdft-decomposition-lane.md) — same strangler-fig discipline (whole-lift + extern-globals + gate-every-step), adapted from numeric-golden to structural/behavioral verification.
**Default verdict was NOT_VERIFIED; every claim below is substantiated with `file:line` from a first-hand read.**

All `file:line` refs are into `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` unless prefixed otherwise. Total = **6191 lines** (`wc -l`, 221.4 KB).

---

## 1 · STRUCTURE

### 1.1 Top-level shape (header-only, single includer)

`serial_menu.h` is a **header-only translation unit included exactly once** — by the sketch:

- Only includer in the whole repo: `SPECTRASYNQ_K1_FIRMWARE.ino:39` (`#include "serial_menu.h"`). Repo-wide grep for `#include.*serial_menu\.h` returns that single line.
- It is guarded `#ifndef SERIAL_MENU_H` (line 5) and pulls in 13 firmware headers + 5 std headers (lines 8-40), including `globals.h` (8), `constants.h` (9), plus the DSP/director/effect-registry surface (25-38).

There is **no class** — it is a flat namespace of free functions (the inherited Sensory Bridge serial-menu style). 113 function definitions at file scope (enumerated via the def-regex sweep).

### 1.2 The two dispatch entry points

There is **not one** dispatch entry — there are **two parallel command surfaces**, deliberately separated for safety:

1. **Typed `:cmd` surface → `parse_command(char* command_buf)`** (3373-5668, **~2296 lines** — the single largest construct in the file, ~37% of the TU). Two sub-stages:
   - **Stage A — Row-1 table lookup** (3380-3408): bare commands (no `=`) route through `serial_cmd_lookup()` → `serial_dispatch_typed_row()` against the X-macro table. This is the safety-class-enforced surface (D5 cal-guidance, D6 CONFIRM trio).
   - **Stage B — metadata `else if` chain** (3445-5664): `type=value` typed setters. `command_type[32]` and `command_data[94]` are split by hand (3422-3441), then a **246-branch `strcmp(command_type, ...)` else-if chain** dispatches (count via grep over 3373-5669). Terminates in `bad_command()` (5665).

2. **Single-byte hotkey surface → `serial_handle_hotkey` / `serial_hotkey_is_immediate`** (gate at 2279) — a **separate runtime path**, constrained independently of the table (the `.def` header explicitly documents this split at `serial_cmd_table.def:24-28`). `check_serial(uint32_t t_now)` (5669) is the per-frame driver that routes a byte either to the hotkey path or buffers it for `parse_command` (asserted by `test_serial_hotkeys_static.py:88-95`).

### 1.3 The X-macro command table (`serial_cmd_table.def`)

- **What it is:** 67 lines, **31 `SERIAL_CMD(...)` rows** (`grep -c '^SERIAL_CMD'`). Each row: `(name, hotkey, handler, safety_class, flags, input_surface)` (`serial_cmd_table.def:11`). Every row's `hotkey` is `0` — the keystroke surface is governed separately (`:13-14`, `:24-28`).
- **Where it's `#include`d (X-macro expansion sites):**
  - `serial_menu.h:3276` — builds the real `SERIAL_CMD_TABLE[]` (the consumer `#define`s `SERIAL_CMD(...)` just above at the "the table" banner 3262, then includes).
  - `scripts/regression-harness/row1_dispatch_table_test.cpp:138` — the **host** test re-includes the SAME `.def` with a model `SERIAL_CMD` macro (`:136-139`), so the test can never silently diverge from the shipped table (`.def:5-8`). **This is the load-bearing precedent for Lane 2 verification** (§4).
- **What each expansion generates:** in firmware, one `serial_cmd_row_t` struct literal per row → a `static const serial_cmd_row_t SERIAL_CMD_TABLE[]`; in the host test, the same array against stub handlers that record an `Effect` enum so the test asserts *which* handler each name routes to (`row1_dispatch_table_test.cpp:71-79`, `:135-146`).
- **Safety flags** (`CMD_*`) and **safety classes** (`SC_*`) defined at `serial_menu.h:2775-2779` and used in the `.def` rows (e.g. `factory_reset` = `SC_FORBIDDEN_SINGLE_BYTE | CMD_IRREVERSIBLE | CMD_DISRUPTIVE`, `.def:40`).
- **Compile-time integrity:** constexpr static_asserts at the "compile-time integrity checks" banner (3282) evaluate table consistency at build time.

### 1.4 Major functional groups (author's own banners + handler clustering)

| Group | Evidence (`serial_menu.h` lines) | Owns |
|---|---|---|
| **TX framing / ack / errors** | `tx_begin` 231, `tx_end` 239, `ack` 247, `bad_command` 251, `stop_streams` 264, `init_serial` 286 | serial protocol envelope |
| **dump / info** | `dump_info` 314 (~200 lines) | full config dump |
| **VP profile + vivid + loud-guard + beat-director status** | `vp_parse_bool/float` 517/529, `serial_*_k1_loud_guard` 547/566, `serial_print_beat_director_status` 584, `serial_*_vivid_*` 605-644 | visual-pipeline toggles/status |
| **AP capture/telemetry (diagnostics)** | `ap_nov_capture_*` 644-774, `ap_cad_capture_*` / `ap_cad_soak_*` 774-1410 (**~640 lines**, mostly `#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG`-gated, 643) | novelty/cadence capture buffers |
| **VP status / smart / edge / perf / vpab** | `vp_apply_profile` 1410, `vp_print_status` 1420, `sb_*_smart/edge_status` 1538/1636, `sb_apply_smart_scene` 1648, `vp_perf_*` 1721-1782, `vpab_command` 1782 | director/edge/perf control |
| **Targeted-control helpers + hotkey help/status** | `serial_clamp_float` 1858 … `serial_adjust_target_*` 1961-2052, `serial_queue_slot_*` 2073-2155, `serial_print_hotkey_help` 2155, `serial_print_hotkey_status` 2221, `serial_hotkey_is_immediate` 2279, `manual_commands[]` static 2428 | knob/target UI + hotkey surface |
| **Row-1 bare-command handlers** | `cmd_*` 2801-3228 (31 handlers behind the "bare-command handlers" banner 2797) | the typed-table handler bodies |
| **Dispatch + frame loop** | `serial_dispatch_typed_row` 3346, `parse_command` 3373, `check_serial` 5669, `stream_*` 5727-6113 | the runtime spine |

---

## 2 · DECOMPOSITION SEAMS (candidate extraction units)

Ordered low→high risk. "Dep weight" = coupling to globals/CONFIG/device-I/O.

| # | Unit (proposed TU) | Lines (approx) | Size | Owns | Dep weight |
|---|---|---|---|---|---|
| **A** | `serial/ap_capture_telemetry.{cpp,h}` — `ap_nov_capture_*` + `ap_cad_capture_*` + `ap_cad_soak_*` | 644-1410 | **~770** | novelty + cadence capture/soak buffers, percentile histograms | **LOW** — entirely behind `#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG` (643); diagnostics-only, **absent from production**; touches capture statics + `SBTempoDebugSnapshot`, not CONFIG. **This is the smallest, lowest-risk first cut.** |
| **B** | `serial/serial_tx.{cpp,h}` — `tx_begin/tx_end/ack/bad_command/stop_streams/init_serial` | 231-313 | ~85 | serial protocol envelope | LOW — pure `USBSerial` + a few stream flags; widely *called* but self-contained |
| **C** | `serial/serial_parse_helpers.{cpp,h}` — `vp_parse_bool/float`, `serial_clamp_float`, `serial_wrap_index` | 517-545, 1858-1875 | ~50 | input parsing primitives | LOW — leaf utilities, no globals |
| **D** | `serial/vp_serial_control.{cpp,h}` — vivid/loud-guard/beat-director/vp_profile/vp_perf/vpab + `vp_apply_profile`/`vp_print_status` | 547-644, 1410-1820 | ~520 | VP toggle/status/profile commands | MED — reads/writes VP globals, `#ifdef`-heavy (`K1_LOUD_GUARD_V1`, `SB_VIVID_PRECOMP_V1`, `ENABLE_VP_PERF_AUDIT`, `ENABLE_VPAB_PROBE`) |
| **E** | `serial/serial_target_control.{cpp,h}` — `serial_adjust_target_*`, `serial_toggle_target_*`, `serial_queue_slot_*`, `serial_print_mode/palette/target_*` | 1876-2155 | ~280 | knob/target-channel UI + preset-slot arm | MED — `K1_EFFECT_REGISTRY_V1`-gated; touches CONFIG mode/palette + queue |
| **F** | `serial/serial_hotkey.{cpp,h}` — `serial_print_hotkey_help/status`, `serial_hotkey_is_immediate`, `manual_commands[]`, `serial_handle_hotkey` | 2155-2730 | ~575 | the single-byte hotkey surface | MED — safety-load-bearing (guarded by `test_serial_hotkeys_static.py`); `SB_VIVID_PRECOMP_V1`/`ENABLE_MOTION_PROBE`-gated |
| **G** | `serial/serial_cmd_handlers.{cpp,h}` — the 31 `cmd_*` row handlers + `serial_dispatch_typed_row` + the table-build site | 2801-3346 | ~550 | typed-table handler bodies | MED — shares `.def` with the host test; `serial_cmd_table.def` stays put |
| **H** | `serial/serial_config_setters.{cpp,h}` — the `type=value` metadata `else if` chain | 3445-5664 | **~2220** | **all** typed config setters (led_*, chroma, saturation, mode, secondary_control, …) | **HIGH** — 246 strcmp branches, 42 `save_config`, `reboot()`, ~30 distinct CONFIG fields. **The keystone; extract LAST, in slices.** |
| **I** | `serial/serial_streams.{cpp,h}` — `stream_agc_data/vp_data/tempo_data/ap_frontend_debug/vp_perf_data` + `check_serial` driver | 5669-6191 | ~520 | per-frame stream emitters + frame loop | MED — many `#if` gates; `check_serial` is the entry the `.ino` loop calls |

**Smallest, lowest-risk first slice = Unit A** (AP capture/telemetry): ~770 lines, fully production-gated-out, no CONFIG coupling, self-contained statics. Extracting it cannot move production behavior (it compiles out of `k1_hardware`) — the ideal strangler-fig opener.

---

## 3 · DEPENDENCY SURFACE

### 3.1 CRITICAL — the inversion claim is FALSE (no globals.h → serial_menu.h cycle)

The brief hypothesized that `system/globals.h` includes `serial_menu.h` (an inversion that would pollute the whole build). **Verified FALSE:**

- `grep -nE '#include.*serial_menu' system/globals.h` → **NO MATCH**.
- The only `#include "serial_menu.h"` in the repo is `SPECTRASYNQ_K1_FIRMWARE.ino:39`.
- The direction is the **other way**: `serial_menu.h:8` includes `globals.h`. The brief's "Included by 6 files" list is the reverse — those 6 (`.ino`, `motion_probe.h`, `gdft_harness.h`, `globals.h`, `i2s_audio.h`, `lightshow_modes.h`) are headers `serial_menu.h` *consumes* or that are co-included, not includers of it. **`globals.h` is a dependency OF serial_menu.h, not a consumer.** No inversion to repair; the single-includer property is exactly what makes this a clean strangler-fig target (same shape as GDFT.h).

### 3.2 What it touches

| Category | Evidence | Notes |
|---|---|---|
| **CONFIG fields (write)** | ~30 distinct: `CONFIG.SQUARE_ITER`(×15), `CONFIG.SENSITIVITY`(×15), `CONFIG.SATURATION`(×13), `CONFIG.LIGHTSHOW_MODE`(×11), `CONFIG.LED_COLOR_ORDER`(×11), … `CONFIG.SAMPLE_RATE`, `CONFIG.LED_COUNT`, `CONFIG.SWEET_SPOT_*` | almost entirely inside Unit H (the metadata chain); the heavy coupling |
| **Flash persistence** | `save_config` ×42 (grep) | side-effect after most setters; **device-I/O** — same hazard class as the GDFT cal-FSM |
| **Reboot / disruptive** | `reboot()` (extern `system.h:47`) at 2984, 4226, 4399, 4443, 4460 | `factory_reset`/`restore_defaults`/`reset` paths |
| **Device serial I/O** | `USBSerial.` ×**1714** | every handler echoes; the dominant coupling — host extraction needs a `USBSerial` stub (the GDFT oracle already has one: `oracle_hostcompile` no-ops) |
| **Subsystem calls** | `sb_smart_director_*`, `sb_audio_snapshot`, `sb_edgemixer_lite`, `sb_onset_beat`, `sb_tempo`, `beat_aware_director`, `EffectRegistry` (includes 25-38) | director/DSP read surface |
| **NVS / WiFi / EEPROM** | grep `nvs_|Preferences|EEPROM|WiFi|websocket` → **none** | no direct flash-driver or wireless calls; persistence is via `save_config()` only, no wireless commands in this file |
| **Reused setter helpers** | `serial_adjust_target_float`(×13), `vp_set_float_command`(×11), `vp_set_flag_command`(×8), `serial_adjust_target_mode/palette`(×3 each) | the chain is NOT 246 bespoke bodies — it leans on ~7 shared helpers, which lowers Unit H risk if those helpers extract first (Unit C/E) |

### 3.3 Heavy couplings (flag before extraction)

1. **`USBSerial` (1714 sites)** — any host-compilable TU needs the stub. Already solved by the GDFT lane's `oracle_hostcompile`.
2. **`save_config()` (42) + `reboot()` (5)** — device side-effects mid-handler (the GDFT-lane "embedded I/O mid-function" trap, §5). In Unit H the side-effects sit *after* the CONFIG write, so they are tail side-effects (less entangled than the GDFT cal-FSM's mid-function AGC-reset), but must be carried verbatim.
3. **Dense `#ifdef` lattice** — 80+ preprocessor gates (grep). Families: `ENABLE_TEMPO_STREAM`/`ENABLE_AP_FRONTEND_DEBUG` (telemetry), `K1_EFFECT_REGISTRY_V1`, `SB_VIVID_PRECOMP_V1`, `K1_LOUD_GUARD_V1`, `ENABLE_*` probe gates, `FEATURE_MABUTRACE`. Each TU must carry its gates verbatim (GDFT-lane rule).

---

## 4 · VERIFICATION SHAPE

A **numeric golden-master does NOT fit** — serial_menu is command/UI/protocol logic, not numeric DSP (no spectrum/onset/chord arrays produced). The behavior to preserve is *"the same command string produces the same dispatch + the same serial output + the same safety enforcement."* Three layers, **all already precedented in this repo**:

1. **X-macro table host test (already exists — extend it).** `scripts/regression-harness/row1_dispatch_table_test.cpp` already host-compiles the `.def` and asserts (a) every row routes to the correct handler, (b) no duplicate names, (c) D5/D6 safety-class teeth (`:101-104`, `:198-283`). Any extraction of Unit G (handlers) is locked by this test — if a name re-wires, it fails. **This is the closest analogue to the GDFT golden** and it already passes.
2. **Structural Python test (already exists — extend it).** `tests/test_serial_hotkeys_static.py` (129 lines) asserts function existence + brace-balance (`:20`, `:31`), the hotkey allowlist (`:34-50`), no destructive single-byte cal hotkeys (`:52-64`), the noise-cal arm/confirm guard (`:66-86`), and `check_serial` line-buffer behavior (`:88-95`). After each extraction, re-point its `SERIAL_MENU = FW / "serial_menu.h"` to the new TU(s) and re-assert the moved functions still exist + are balanced.
3. **Command-input → serial-output replay (the strongest lock; build it for Unit H).** Host-compile the extracted setter TU against the `oracle_hostcompile` stub (USBSerial/save_config/reboot as recording no-ops), feed a corpus of `type=value` command strings, capture the emitted `USBSerial` lines + the resulting CONFIG mutations, and diff pre- vs post-extraction. This is the behavioral equivalent of the GDFT golden `.jsonl`. There is a sibling precedent: `tests/test_tab5_dispatch_replay.py` already does command-dispatch replay.

**Host-compilability:** YES for Units A, B, C, G, and H *if* the `USBSerial`/`save_config`/`reboot`/`millis` stubs are provided (the GDFT lane already built this stub family). Units D, F, I are more device-coupled (director/stream subsystem state) but their *dispatch* is still structurally testable. The recommended lock per slice: **build-green (`pio run -e k1_hardware`) + the two existing tests re-pointed + (for H) the new input→output replay**, mirroring the GDFT "gate every step" rule.

---

## 5 · EXTRACTION HAZARDS (GDFT-lane traps, located here)

1. **`build_src_filter` allowlist — CONFIRMED: `serial/` is NOT in it.** `platformio.ini:44` lists `+<system/…> +<visual/…> +<effects/…> +<audio/…> +<director/…> +<control/…>` — **no `serial/`**. serial_menu.h compiles today only because it is `#include`d as a header into the `.ino` TU. **Every new `serial/*.cpp` MUST add an explicit `+<serial/…>` filter entry** (in `k1_hardware` and all envs that inherit it via `${env:k1_hardware.build_src_filter}` — lines 178, 205, 616, 650). This is the GDFT-lane's #1 mechanical trap and it applies in full.
2. **Embedded device-I/O mid-handler.** `save_config()` (×42) and `reboot()` (×5) sit inside handler bodies (e.g. reboot at 4226/4399/4443/4460). Carry verbatim; stub in host. The GDFT cal-FSM was *worse* (mid-function AGC-reset ordering); here the I/O is mostly tail side-effect, but the rule stands — do not "clean up" the I/O during the move.
3. **Function-static state.** `manual_commands[]` (2428, `static const`), and the stream/loop statics `last_check`/`command_mode` (5674-5675), `last_vp_stream` (5774), `last_tempo_stream` (5838), `last_emit_count`/`last_apdbg_stream` (5982-5983). These pin per-frame cadence — must move with their owning function (Unit B/I), not be reset.
4. **X-macro fragility.** `serial_cmd_table.def` is the **single source** shared by firmware (3276) AND the host test (`row1_dispatch_table_test.cpp:138`). **Do not move or rename the `.def`**; an extracted `serial_cmd_handlers.cpp` must keep including it at the same relative path, and the host test's `../../SPECTRASYNQ_K1_FIRMWARE/serial/serial_cmd_table.def` path must stay valid. The `SERIAL_CMD`/`CMD_*`/`SC_*` macro context (2775-2779) must be visible at the `.def` expansion site in whatever TU owns it.
5. **Ordering couplings.** Stage A (table lookup) must run **before** Stage B (metadata chain) in `parse_command` (3380 before 3445) — the `strchr(command_buf, '=')` gate (3380) is load-bearing (bare vs `=value` routing). If `parse_command` itself is split, the two stages cannot be reordered. The `SC_FORBIDDEN_SINGLE_BYTE` trailing-token branch (3395-3406) is a deliberate guard against `reset now` becoming a silent reboot — preserve exactly.
6. **The 246-branch chain is one function.** Unit H is a single `else if` ladder inside `parse_command` — it cannot be *partially* lifted without first refactoring the ladder into dispatchable sub-functions (a behavior-preserving in-place step that should be its OWN gated commit before any file move). Slice it by command family (telemetry / config-set / secondary) only after the ladder is sub-functioned.

---

## 6 · RECOMMENDED SEQUENCE (incremental, each behavior-preserving + gated)

Gate at every step = `pio run -e k1_hardware` green **+** `row1_dispatch_table_test.cpp` passes **+** `test_serial_hotkeys_static.py` passes (re-pointed) **+** (from S3) the new input→output replay.

- **S0 — Stub + filter scaffolding.** Add `+<serial/…>` to `build_src_filter` (platformio.ini:44) and confirm the `oracle_hostcompile` stub family (USBSerial/save_config/reboot/millis no-ops) covers serial. No code moved yet. Prove: build still green, filter accepts a trivial empty `serial/_probe.cpp`.
- **S1 — Extract Unit A (AP capture/telemetry).** Lift `ap_nov_capture_*` + `ap_cad_*` (644-1410) whole into `serial/ap_capture_telemetry.{cpp,h}`, extern-globals. **Lowest risk** — production-gated-out, no CONFIG. serial_menu.h `#include`s the new header. Prove: build green; the telemetry `#if` gates compile out of `k1_hardware` exactly as before; tests pass.
- **S2 — Extract leaf utilities (Units B + C).** `serial_tx.*` (TX envelope 231-313) and `serial_parse_helpers.*` (517-545, 1858-1875). Pure, widely-called — moving them first de-risks H. Prove: build green; structural test re-pointed.
- **S3 — Build the command-input→serial-output replay harness.** Before touching handlers, lock the behavioral contract: host-compile the dispatch path against the stub, freeze a `serial.golden.jsonl` of (command → emitted lines + CONFIG delta). This is the serial analogue of S1.5 in the GDFT lane — **the command surface is now locked.**
- **S4 — Extract Unit G (row-1 handlers).** Move the 31 `cmd_*` bodies + `serial_dispatch_typed_row` (2801-3346) into `serial/serial_cmd_handlers.cpp`, keeping `serial_cmd_table.def` in place and the table-build site with it. Already double-locked by `row1_dispatch_table_test.cpp`. Prove: that host test + the new replay both reproduce.
- **S5 — Extract Units D, E, F (vp-control, target-control, hotkey).** Each is a coherent ~300-575-line group with its own `#ifdef` family; extract one per gated commit. Unit F (hotkey) is safety-load-bearing — lean on `test_serial_hotkeys_static.py` re-pointed.
- **S6 — Sub-function the 246-branch ladder, then extract Unit H by family.** First, in-place, refactor the `else if` chain into family dispatchers (`dispatch_led_config`, `dispatch_secondary_control`, `dispatch_chroma`, …) — a behavior-preserving step gated by the S3 replay. Then lift the families into `serial/serial_config_setters.*`. **This is the keystone and goes LAST**, fully behind the locked replay.
- **S7 — Extract Unit I (streams + check_serial).** The per-frame emitters + frame-loop driver (5669-6191), preserving the cadence statics. serial_menu.h shrinks to a thin include-shim (or is deleted, with the `.ino` including the new TUs directly).

**Net:** 6191-line god-header → ~8 cohesive TUs averaging ~300-770 lines, every move behavior-preserving and gated by tests that already exist (extended), with the highest-risk 2220-line dispatch chain locked behind a command→output replay before it is touched.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-23 | agent:deep-technical-analyst | Created: Phase A Lane 2 serial_menu.h decomposition scope. Structure map (parse_command 2296 lines / 246 strcmp branches, .def 31-row X-macro, dual command surface), 9 candidate seams, dependency surface (FALSE inversion claim verified — globals.h does NOT include serial_menu.h; 1714 USBSerial / 42 save_config / 5 reboot; serial/ NOT in build_src_filter), structural+behavioral verification shape (existing row1_dispatch_table_test.cpp + test_serial_hotkeys_static.py + new input→output replay), 6 extraction hazards, 8-step gated sequence. Read-only cartography; no firmware edited. |
