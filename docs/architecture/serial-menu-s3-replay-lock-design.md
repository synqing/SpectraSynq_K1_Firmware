---
abstract: "S3 design for the serial command-input→serial-output behavior-lock that gates serial_menu.h handler extractions (S4+). Mirrors the GDFT golden-master oracle pattern (oracle exports NAME/capture()/MUTATIONS, registered in harness_selftest.ORACLE_MODULES, gated by test_golden_master.py with MANIFEST.sha256 anti-gaming, proven by Gate-Fα). The load-bearing capture surface is the TRIPLE per command: (a) emitted serial text, (b) CONFIG field deltas, (c) side-effect flags (save_config/reboot fired). Host-compiles parse_command + serial_cmd_handlers against the oracle_hostcompile stub family with USBSerial→string-capture, save_config/reboot→recording-no-op, millis→deterministic. SMALLEST-FIRST-LOCK (S3.0) = the 24 pure CONFIG-setter branches (photons/chroma/saturation/sensitivity/…) — parse→CONFIG write→save_config→echo, zero subsystem coupling, zero reboot. Hazards: FIRMWARE_VERSION/.ino-context coupling (init_serial stays put), the 9 reboot-bearing setters needing neutralization, uninitialized CONFIG determinism, build_src_filter (+<serial/*.cpp> already present). Read before implementing S3 or starting S4."
---

# Phase A · Lane 2 — S3: serial command→output replay behavior-lock (design)

**Status:** designed (read-only; no firmware/test edited). **Verdict default was NOT_VERIFIED; every claim below carries a `file:line` from a first-hand read.**
**Pattern source:** the GDFT golden-master oracle ([`gdft-decomposition-lane.md`](./gdft-decomposition-lane.md) §5–§6 "S1.5 — Golden-lock") + the live golden harness (`scripts/regression-harness/golden/`, `tests/test_golden_master.py`). **Scope source:** [`serial-menu-decomposition-scope.md`](./serial-menu-decomposition-scope.md) §4 layer 3 ("the strongest lock; build it for Unit H") and §6 step S3.

All `file:line` refs are into `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` unless prefixed. Current state confirmed: S0 (filter) + S1 (`k1_ap_capture_telemetry.{cpp,h}`) + S2 (`serial_tx.{cpp,h}`, `serial_parse_helpers.{cpp,h}`) are **already extracted** (`SPECTRASYNQ_K1_FIRMWARE/serial/` listing); `+<serial/*.cpp>` is **already in** `build_src_filter` (`platformio.ini:44`). S3 is next; S4 (handler extraction) is blocked on it.

---

## 1 · CAPTURE SURFACE — what locks behavior

A serial command's observable behavior is a **triple**, not a single output. From a first-hand read of the `parse_command` Stage-B setter chain (2411→4706, **2296 lines, 132 `command_type` branches**):

| # | Output channel | Evidence | Load-bearing? |
|---|---|---|---|
| **(a)** | **Emitted serial text** — every handler echoes via the `serial_tx` envelope: `tx_begin()`→`USBSerial.print(...)`→`tx_end()`, or `bad_command()` on parse failure. **245 `USBSerial.` sites, 88 `tx_begin`/88 `tx_end`, 93 `bad_command` in `parse_command` alone.** | `serial_menu.h:3374-3377` (CHROMA echo), `serial_tx.cpp:27-58` (envelope bodies) | **YES — primary.** This is the user-facing protocol contract and the thing most likely to silently drift on a careless move. |
| **(b)** | **CONFIG field deltas** — **30 distinct `CONFIG.<field>` writes** (CHROMA, PHOTONS, SATURATION, SENSITIVITY, SQUARE_ITER, LED_COUNT, SWEET_SPOT_*, …). | `serial_menu.h:3376` `CONFIG.CHROMA = constrain(...)`; field set enumerated below | **YES — co-primary.** A handler that echoes the right text but writes the wrong field (or clamps differently) is a real regression text alone misses. |
| **(c)** | **Side-effect flags** — `save_config()` (10) / `save_config_delayed()` (24) / `reboot()` (9) fired, and the stream flags reset by `stop_streams()` (`serial_tx.cpp:60-80`). | `serial_menu.h:3373` `save_config_delayed()`; reboot at the `note_offset` setter (`serial_menu.h:3437`) | **YES — but captured as a fired/not-fired boolean,** never executed (see §3). Distinguishes `square_iter` (save_config_delayed, no reboot) from `note_offset` (save_config + reboot). |

**Load-bearing decision:** **(a)+(b)+(c) together** form one frozen record per command. (a) is the dominant signal (matches the repo's other goldens, which emit a text/numeric record per step), (b) catches field-routing regressions text can hide, (c) catches the safety-class behavior (does a destructive setter still reboot?). This is the direct analogue of the GDFT golden's "one JSON record per step covering every public output field" (`oracle_smart_director.py:307-338`).

**Per-command record (frozen as one JSONL line):**
```json
{"cmd":"chroma=0.5","emitted":["sbr{{","CONFIG.CHROMA: 0.500000","}}"],
 "config_delta":{"CHROMA":0.5},"save_config":true,"save_config_delayed":false,"reboot":false,"bad_command":false}
```
This mirrors the `{step, ...fields}` shape of `smart_director.golden.jsonl` but keys on the command string and splits the three channels.

---

## 2 · HOST-COMPILABILITY — can parse_command + handlers host-compile?

**YES** — same substrate that already host-compiles `sb_smart_director.cpp`, `k1_gdft_core`, and the row-1 dispatch test. The proof is structural: the `parse_command` Stage-A path is **already** host-compiled today by `scripts/regression-harness/row1_dispatch_table_test.cpp` (it includes the real `serial_cmd_table.def:138` and mirrors `serial_cmd_lookup`/`serial_dispatch_typed_row`). S3 extends that exact approach from Stage-A (routing) to Stage-B (setter bodies).

**Dependency surface of `parse_command` Stage-B (measured, not estimated):**
- **245 `USBSerial.` sites** → needs a `USBSerial`/`Serial` capture stub that **records** each `print`/`println` into a string list (not a no-op — the text IS the golden). This is the one extension over `oracle_hostcompile`'s no-op `USBSerial`.
- **30 `CONFIG.<field>` writes** → needs a host `CONFIG`/`CONFIG_DEFAULTS` struct stub (the relevant fields only; same pattern as `oracle_smart_director.py:163-176` `RenderParams` stub).
- **34 `save_config*` + 9 `reboot()`** → recording-no-op stubs (set a fired-flag, do nothing). §3.
- **46 distinct subsystem calls** (`sb_smart_director_*`, `vp_apply_profile`, `vp_print_status`, `sb_edgemixer_*`, `serial_queue_*`, `sb_visual_hooks_*`, …) → **the reason S3.0 is scoped to the pure setters** (§4). The pure subset touches **none** of these.
- `vp_parse_bool`/`vp_parse_float`/`serial_clamp_float` → already extracted to `serial_parse_helpers.{cpp,h}` and **already host-compilable** (leaf utilities, no globals — `serial-menu-decomposition-scope.md:68`); compile the real TU in.
- `millis()` → deterministic stub returning a fixed/monotonic counter.

**What must be stubbed (the host boundary):**
1. `Arduino.h` shim — reuse `oracle_hostcompile.ARDUINO_STUB` (`oracle_hostcompile.py:26-33`), extended with the recording `USBSerial`/`Serial` object.
2. `config_types.h` / `globals.h` `CONFIG` struct — host stub carrying the 30 written fields + `CONFIG_DEFAULTS` (the `*=default` branches read it, e.g. `serial_menu.h:3428`).
3. `save_config()`, `save_config_delayed()`, `reboot()` — recording-no-ops (§3).
4. `millis()` — deterministic.
5. For S3.0, the pure setters need **nothing else**; for later slices, stub the subsystem entry points the chosen family touches.

**`.ino`-context coupling — DO NOT pull in:** `init_serial()` (`serial_menu.h:111-135`) references the `FIRMWARE_VERSION` macro, which is `#define`d in the `.ino` TU, not a header — `serial_tx.h:25-27` already documents that `init_serial` "stays in serial_menu.h … only compiles inside the .ino include context." **The replay must NOT compile `init_serial` or `dump_info` (`serial_menu.h:140`, prints `FIRMWARE_VERSION`).** S3.0 drives `parse_command` directly; it never boots the menu.

---

## 3 · SIDE-EFFECT HANDLING — neutralize device I/O deterministically

Commands that persist or reboot must be **observed, not executed**. The GDFT lane's precedent: the cal-FSM was neutralized by forcing `noise_complete=true` so the host run is deterministic and safe (`gdft-decomposition-lane.md:48`). The serial analogue:

| Side effect | Sites | Host stub behavior |
|---|---|---|
| `save_config()` | `serial_menu.h` ×10 | `g_save_config_fired = true;` (recording no-op) — flag enters the golden record (c), flash never written |
| `save_config_delayed()` | ×24 | `g_save_config_delayed_fired = true;` — separate flag (the two are behaviorally distinct: immediate vs deferred) |
| `reboot()` | ×9 (e.g. `note_offset` `serial_menu.h:3437`) | `g_reboot_fired = true; return;` — **must still `return`** so the handler's control flow is identical, but the process does not exit. Captured in (c). |
| `stop_streams()` | `serial_tx.cpp:60-80` | real TU compiles in; sets host stream-flag stubs (already needed for `serial_tx`) |

**Determinism guarantee:** with `USBSerial` recording to a string list and all three device side-effects as flag-setting no-ops, replaying the same command sequence twice yields byte-identical output — the exact property `harness_selftest.run_selftest()` asserts (`harness_selftest.py:112`, "capture() is deterministic"). The reboot stub's mandatory `return` preserves the handler's early-exit so no downstream branch behavior shifts.

---

## 4 · INPUT CORPUS — smallest set that meaningfully locks behavior

The corpus is a **deterministic ordered list of command strings** fed one-by-one through `parse_command`. The measured branch inventory splits cleanly:

- **24 PURE config setters** (parse → `CONFIG.<field>` write → `save_config*` → `tx_begin`/echo/`tx_end`, **zero subsystem coupling, zero reboot**): `set_mode, photons, chroma, mood, palette_mode, palette_index, square_iter, led_interpolation, base_coat, temporal_dithering, sensitivity, mirror_enabled, sweet_spot_min, sweet_spot_max, chromagram_range, standby_dimming, reverse_order, max_current_ma, auto_color_shift, incandescent_filter, incandescent_mode, bulb_opacity, saturation, prism_count`.
- **9 reboot-bearing setters**: `sample_rate, note_offset, led_type, led_count, led_color_order, samples_per_chunk, boot_animation, set_chroma_profile, bass_mode`.
- The remainder (~99 branches) couple to subsystems (`vp_*`, `sb_*`, queue, edge) — locked in **later** slices, not S3.0.

**S3.0 corpus (smallest meaningful lock) — three sub-classes, ~20 lines:**
1. **Valid pure sets** (one per pure setter, a representative value): `chroma=0.5`, `photons=0.8`, `saturation=0.25`, `sensitivity=2.5`, `square_iter=4`, `mirror_enabled=true`, `sweet_spot_min=100`, … — locks (a) echo text + (b) the exact CONFIG write/clamp + (c) `save_config_delayed` fired.
2. **Clamp/boundary** (proves `constrain()` bounds, 25 `constrain` calls in-chain): `chroma=9.9` (→ clamped 1.0), `photons=-1` (→ 0.0), `square_iter=99` (→ 10) — clamp behavior is a classic silent-drift target on a move.
3. **`=default` + malformed**: `chroma=default` (reads `CONFIG_DEFAULTS`), `chroma=` (empty → `vp_parse_float` fails → `bad_command`), `unknown_cmd=1` (→ `bad_command`, (d)=true) — locks the failure path, which is where a botched extraction most often regresses.

S3.0 deliberately **excludes** the reboot setters and all subsystem-coupled commands. Once the pattern is proven on the pure subset, S3.1 adds the 9 reboot setters (with the reboot-fired flag), and S5/S6 slices add the subsystem families as each is extracted.

---

## 5 · GOLDEN FORMAT + GATE — frozen record + registration

**Mirror the existing golden machinery one-for-one** (this is the cheapest, already-proven path — `tests/test_golden_master.py` + `harness_selftest.py:ORACLE_MODULES`):

1. **Oracle module** `scripts/regression-harness/golden/oracle_serial_replay.py`, self-describing exactly like the others (`harness_selftest.py:104-120` requires `NAME`, `capture()`, `MUTATIONS`):
   - `NAME = "serial_replay"`.
   - `MODULE_CPPS` = the extracted handler TU(s) + `serial_parse_helpers.cpp` + `serial_tx.cpp`. **For S3.0, before S4 extracts handlers, `parse_command` still lives in `serial_menu.h`** — so the S3.0 oracle compiles a **driver that `#include`s `serial_menu.h`** under the host stub set (the same way `row1_dispatch_table_test.cpp:138` includes the real `.def`). After S4, `MODULE_CPPS` points at `serial_cmd_handlers.cpp` and the include shrinks. The golden record is **identical across that move — that identity IS the S4 proof.**
   - `DEFINES` = the production `k1_hardware` flag set (match `oracle_smart_director.py:32-37` discipline: same defines the shipped TU sees, so the golden pins production behavior).
   - `capture(firmware_root=None)` — compile `-O0 -fno-fast-math` (determinism, per `oracle_hostcompile.py:9-13` and `gdft-decomposition-lane.md:67`), run, emit one JSONL line per corpus command.
   - `MUTATIONS` — ≥3 real edits that MUST diverge the golden (Gate-Fα teeth), e.g.: flip a `constrain(value, 0.0f, 1.0f)` bound on `chroma`; swap `CONFIG.PHOTONS =` target to `CONFIG.MOOD`; change a `save_config_delayed()` to `save_config()` on a pure setter. Each must change the captured record (`harness_selftest.py:117-120`).
2. **Freeze** `tests/golden/serial_replay.golden.jsonl` + append its sha256 to `tests/golden/MANIFEST.sha256` (anti-gaming: `test_golden_master.py:55-66` re-hashes every golden and fails on drift — a refactor lane cannot edit the golden to make a regression pass).
3. **Register** by adding `"oracle_serial_replay"` to `ORACLE_MODULES` (`harness_selftest.py:36-52`). That single edit wires it into **both** `test_golden_master.py` (reproduction gate, imports the same list `:27`) **and** `harness_selftest.py` (Gate-Fα self-test).
4. **Gate for S4+:** every handler-extraction commit must keep `python harness_selftest.py` green (Gate-Fα: oracle still catches its mutations) **and** `pytest tests/test_golden_master.py` green (the frozen `serial_replay.golden.jsonl` reproduces byte-for-byte). **Reproducing the golden = behavior preserved.** This sits alongside the existing per-slice gate from the scope doc (`serial-menu-decomposition-scope.md:135`): `pio run -e k1_hardware` + `row1_dispatch_table_test.cpp` + `test_serial_hotkeys_static.py` re-pointed.

---

## 6 · SMALLEST FIRST LOCK (S3.0) — the minimal implementable slice

**Deliverable:** `oracle_serial_replay.py` + `serial_replay.golden.jsonl` + MANIFEST line + `ORACLE_MODULES` registration, locking **only the 24 pure CONFIG setters** via the §4 S3.0 corpus, with the §5 host stubs.

Why this is the right first cut (all evidence-backed):
- **No subsystem coupling** — the pure setters touch none of the 46 `sb_*`/`vp_*`/queue calls, so the host stub surface is just `USBSerial`-capture + `CONFIG` struct + `save_config*` no-ops + `millis`. Smallest possible boundary.
- **No reboot** — zero `reboot()` in the pure subset, so no early-exit control-flow subtlety in the first lock.
- **Exercises all three capture channels** — echo text (a), CONFIG write+clamp (b), `save_config_delayed` fired (c), plus the `bad_command` failure path (d).
- **Establishes the pattern S4 needs** — once `serial_replay.golden.jsonl` is frozen and `oracle_serial_replay` is in `ORACLE_MODULES`, S4 (extract the 31 `cmd_*` row handlers + later the pure setters into `serial_cmd_handlers.cpp`) is **gated**: the golden must reproduce across the move.

**S3.0 done-criteria:** `python harness_selftest.py` PASS (serial_replay catches its ≥3 mutations) + `pytest tests/test_golden_master.py` PASS (golden reproduces, MANIFEST intact) + the oracle compiles `-O0` clean on host. No firmware behavior changes (S3.0 only adds test infra; `parse_command` is untouched).

---

## 7 · HAZARDS — determinism traps & coupling

1. **`FIRMWARE_VERSION` / `.ino`-context coupling.** `init_serial`/`dump_info` print `FIRMWARE_VERSION` (a `.ino` `#define`, `serial_tx.h:25-27`). The replay must drive `parse_command` **directly** and never call `init_serial`/`dump_info` — else the host compile fails (macro undefined) or the golden carries a version string that drifts every release. Keep them out of `MODULE_CPPS`/driver.
2. **Uninitialized CONFIG.** A handler that reads `CONFIG.<field>` before writing (e.g. a toggle, or `*=default` reading `CONFIG_DEFAULTS`) makes the record depend on the host `CONFIG` init values. **The driver must zero-init the host `CONFIG`/`CONFIG_DEFAULTS` struct to fixed, documented values** (a `CONFIG c = {};` + explicit defaults block, like `oracle_smart_director.py:294` `SBAudioSnapshot a = {};`). Document the init in the oracle so the golden is reproducible cross-machine.
3. **The 9 reboot-bearing setters.** Excluded from S3.0; when added (S3.1) the `reboot()` stub MUST `return` so control flow matches, and the fired-flag goes in (c). A reboot that actually exits the host process = no golden line, silent gap.
4. **`save_config` vs `save_config_delayed`.** Behaviorally distinct (immediate vs deferred flash). Capture as **two separate flags** (§3) — collapsing them would let a move swap one for the other undetected.
5. **`build_src_filter`.** `+<serial/*.cpp>` is **already present** (`platformio.ini:44`) — no change needed for S3 (it adds no production TU). But when S4 creates `serial_cmd_handlers.cpp`, the filter already accepts it; the inherited envs (`platformio.ini:178,205,616,650`) pick it up via `${env:k1_hardware.build_src_filter}`. The S3 oracle is host-only and never sees `build_src_filter` at all.
6. **`-O0 -fno-fast-math` (not production `-O3 -ffast-math`).** The golden locks **algorithm/branch structure** (refactor-equivalence), not device numerics — the same caveat as every existing golden (`gdft-decomposition-lane.md:92`, `oracle_hostcompile.py:9-13`). For the integer/string command surface this is exact; the float CONFIG values (`chroma`, `photons`) use a tolerance (`test_golden_master.py:32` `FLOAT_TOL=1e-3`) which already absorbs cross-compiler last-digit drift.
7. **Float echo precision.** Handlers print floats with explicit precision (`USBSerial.println(CONFIG.CHROMA, 6)`, `serial_menu.h:3376`). The recording `USBSerial` stub must reproduce Arduino's `print(float, N)` formatting **exactly** (N decimal places, no exponent) or the emitted-text channel (a) drifts spuriously. This is the single subtlest stub detail — pin it against a known device output line in the oracle's comments.
8. **`serial_cmd_table.def` stays put.** The X-macro single-source rule (`serial-menu-decomposition-scope.md:127`): the replay driver, if it routes through Stage-A, must include the real `.def` at its committed relative path — never re-type rows. S3.0 (pure setters) is Stage-B only, so it sidesteps this, but S3.1+/S4 that touch Stage-A inherit the row1-test discipline.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-24 | agent:deep-technical-analyst | Created: S3 command→output replay behavior-lock design. Capture triple (emitted serial text + CONFIG deltas + side-effect flags), host-compilability via oracle_hostcompile stub family extended with USBSerial-capture + CONFIG struct stub, side-effect neutralization (save_config/reboot recording-no-ops), S3.0 corpus = 24 pure CONFIG setters (measured: 132 command_type branches, 24 pure / 9 reboot-bearing / ~99 subsystem-coupled), golden format mirroring oracle_smart_director + test_golden_master + MANIFEST.sha256 + ORACLE_MODULES registration + Gate-Fα, 8 hazards. Grounded in row1_dispatch_table_test.cpp, oracle_hostcompile.py, oracle_smart_director.py, test_golden_master.py, harness_selftest.py, serial_tx.cpp, and a first-hand parse_command read (serial_menu.h:2411-4706). Read-only; no firmware/test edited. |
