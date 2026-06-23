---
abstract: "Row 1 command-equivalence matrix: every K1 serial command -> expected behaviour before vs after the strcmp-chain -> static-dispatch-table refactor in serial_menu.h. Marks the 3 signed behavioural deltas (D5 typed start_noise_cal disabled; D6 destructive trio require CONFIRM; harness cmds flag-gated) and asserts all other commands are behaviour-preserving. Records what the host test covers vs what needs hardware smoke. Read before reviewing or merging the Row 1 diff."
---

# Row 1 — Command Equivalence Matrix

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Scope | `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h` — control-plane (serial command parsing/dispatch) only |
| Change | Hand-rolled `strcmp`/`strncmp` bare-command chain -> static `constexpr` dispatch table (`SERIAL_CMD_TABLE`) owning routing + safety class. Rows live in `SPECTRASYNQ_K1_FIRMWARE/serial_cmd_table.def` (X-macro) shared with the host test. Legacy strcmp chain DELETED (not just dead-wrapped). Typed `type=value` setters keep their exact value-interpretation bodies. |
| Authority | `04-row1-dispatch-table-safety-class-sketch.md` (Captain rulings D5/D6) |
| Builds | `pio run -e k1_hardware` PASS (RAM 83064 B = baseline; Flash 558702 B, -612 B vs 559314 baseline). `pio run -e k1_hardware_harness` PASS. |
| Host test | `scripts/regression-harness/row1_dispatch_table_test.cpp` — exercises the SHARED `.def` rows (25 rows); 0 failures. Includes the D5-teeth, D6-CONFIRM, and trailing-token-on-non-FORBIDDEN regression cases. |
| Runtime proof | Compile + host-logic test are NOT runtime proof. Calibration arm/confirm + CONFIRM-token behaviour need hardware smoke (orchestrator). |

> **Doctrine note.** Compile/upload is not runtime proof (`.claude/CLAUDE.md` rule 5). This matrix is the *expected* contract; the equivalence is proven for the table-routing logic by the host test and by string/symbol inspection of the release ELF, but the on-device serial behaviour of the gated paths is a hardware-gate deliverable.

---

## 1. The three signed deltas (the ONLY behavioural changes)

| # | Command(s) | Before (pre-Row-1) | After (Row 1) | Verified |
|---|---|---|---|---|
| **D5** | `start_noise_cal` (typed `:start_noise_cal`) | `ack()`; sets `noise_transition_queued = true` -> fires calibration immediately, no silence gate, no arm. | Routed to `cmd_start_noise_cal_guidance()` -> prints guidance, **does NOT queue calibration**. `N`(arm)->`Y`(confirm) within the 5 s silence window is the sole calibration trigger (unchanged). | Host test (CAL_GUIDANCE, not queued; SC_ARM_REQUIRED). Release ELF carries the guidance string and retains the `NOISE_CAL: armed/queued` machinery. |
| **D6** | `factory_reset`, `restore_defaults`, `clear_noise_cal` | Bare command -> `ack()` + immediate destructive execute. | Requires typed `CONFIRM` token (`:factory_reset CONFIRM`). Bare / wrong-token -> usage line, no effect. Rows are `SC_FORBIDDEN_SINGLE_BYTE`, `hotkey == 0`, `IS_TYPED_ONLY` — structurally unreachable from a keystroke (static_assert + host test). | Host test (bare -> NONE; `X YES` -> NONE; `X CONFIRM` -> fires). Release ELF carries the "requires confirmation" string. |
| **D-harness** | `ap_capture=<ms>`, `frame_dump=...`, `vp_probe=all` | Already `#ifdef`-gated (`ENABLE_AP_STREAM`/`ENABLE_FRAME_DUMP`/`ENABLE_VP_PROBE_CMD`). | Unchanged — kept gated; absent from release build. | Release ELF: `ap_capture`/`frame_dump` strings = 0, exact `vp_probe` command token = 0; harness ELF: present. |

> **D-harness-2 (NOT done in Row 1 — tracked).** `dump_raw=silence|tone` and the boolean `ap_stream=on|off` toggle are present in the release build today and are **NOT** gated out by Row 1. Gating them behind `ENABLE_AP_STREAM` (or a dedicated flag) would *remove* commands that currently ship — an **unsigned behavioural removal**, which is out of scope for a behaviour-neutral control-plane refactor. It is recorded here as a future signed delta **"D-harness-2"** (gate `dump_raw` / `ap_stream=` behind `ENABLE_AP_STREAM`, behind a Captain ruling) and intentionally deferred. Row 1 leaves these two commands exactly as base.

---

## 2. Bare-command vocabulary — behaviour-preserving rows (table-dispatched)

All rows below dispatch through `SERIAL_CMD_TABLE`. "Surface" = which input may reach it. Behaviour is byte-identical to the pre-Row-1 arm except where a delta is marked.

| Command | Safety class | Surface | Behaviour | Delta? |
|---|---|---|---|---|
| `v` / `V` / `version` | SAFE | both | print firmware version | — |
| `h` / `H` / `help` | SAFE | both | print serial-menu help (help text edited to reflect D5/D6; command behaviour unchanged) | text only |
| `SB?` | SAFE | both | print `SB!` (device autodetect) | — |
| `reset` | TYPED_ONLY (DISRUPTIVE) | typed | `ack()` + reboot | — |
| `factory_reset` | FORBIDDEN_SINGLE_BYTE | typed + CONFIRM | delete all config incl. cal, reboot | **D6** |
| `restore_defaults` | FORBIDDEN_SINGLE_BYTE | typed + CONFIRM | delete config, reboot | **D6** |
| `clear_noise_cal` | FORBIDDEN_SINGLE_BYTE | typed + CONFIRM | clear stored noise cal | **D6** |
| `chip_id` | SAFE | both | print chip MAC | — |
| `identify` | TYPED_ONLY | typed | 2 yellow flashes | — |
| `start_noise_cal` | ARM_REQUIRED | typed | guidance only (no cal) | **D5** |
| `get_num_modes` | SAFE | both | print NUM_MODES | — |
| `get_mode` | SAFE | both | print current mode | — |
| `reset_reason` | SAFE | both | print ESP reset reason | — |
| `dump` | SAFE | both | dump variables | — |
| `stop` | SAFE | both | stop streams + ack | — |
| `fps` | SAFE | both | print SYSTEM_FPS | — |
| `led_fps` | SAFE | both | print LED_FPS | — |
| `vp_status` | SAFE | both | VP diagnostic status | — |
| `vp_out_test` | SAFE | both | VP output probe | — |
| `get_knobs` | SAFE | both | print PHOTONS/CHROMA/MOOD JSON | — |
| `get_buttons` | SAFE | both | print NOISE/MODE button state JSON | — |

**Surface note.** Pre-Row-1, none of these bare commands were reachable from a single keystroke either — the single-byte path (`serial_hotkey_is_immediate`) only ever dispatched the SAFE hotkey set + the N/Y cal pair, and is left untouched by Row 1. The table governs only the typed `:cmd` surface; it makes the keystroke-unreachability of the destructive rows a *structural* guarantee (static_assert) instead of an emergent property of the parser. No previously-keystroke command lost its keystroke; no new command gained one.

**Trailing-token note (BLOCKER fix).** The `:cmd CONFIRM` parsing splits a bare command on its first space ONLY when the looked-up head row is `SC_FORBIDDEN_SINGLE_BYTE` (the destructive trio — the only commands that take an argument). For any other bare command, a trailing token is not meaningful: `reset now`, `dump junk`, `version 1` are **not** dispatched by the table — the buffer is restored and they fall through to the metadata parser, ending in `bad_command`, exactly as the pre-Row-1 base did. Without this scoping, `reset now` would have rebooted (an unsigned delta on a `CMD_DISRUPTIVE` command). Guarded by host-test cases `reset now`/`dump junk`/`version 1` -> NONE.

---

## 3. Single-byte hotkeys — UNCHANGED

`serial_hotkey_is_immediate()` and `serial_handle_hotkey()` are untouched. The immediate hotkey set (`space h ; N Y [ ] 1-6 i/I o/O p/P j/J k/K l/L q/Q w/W e/E r/R t/T , . / a s d f`) and their handlers are byte-identical. The N(arm)/Y(confirm) calibration pair and its 5 s fail-closed window are unchanged — this is the reference ARM-REQUIRED pattern and the **sole** calibration path after D5.

---

## 4. Typed `type=value` setters — UNCHANGED

The 75 typed setters (`vp_profile=`, `ap_stream=`, `vp_stream=`, `vp_perf=`, the `vp_*` flag/float setters, `debug=`, `sample_rate=`, `set_mode=`, `get_mode_name=`, `note_offset=`, `square_iter=`, `led_type=`, `led_count=`, `led_interpolation=`, `base_coat=`, `temporal_dithering=`, `led_color_order=`, `samples_per_chunk=`, `sensitivity=`, `boot_animation=`, `mirror_enabled=`, `sweet_spot_min=`, `sweet_spot_max=`, `chromagram_range=`, `standby_dimming=`, `bass_mode=`, `reverse_order=`, `max_current_ma=`, `stream=`, `auto_color_shift=`, `incandescent_filter=`, `incandescent_mode=`, `bulb_opacity=`, `saturation=`, `prism_count=`, `preset=`, all `secondary_*`, `start_benchmark=`, `stream_spectrogram=`, `stream_agc=`, `stream_chromagram=`) keep their exact bodies in the metadata parser block. Reasoning: each parses `command_data` differently; rewriting them into a uniform `handler(args)` shape would be a large behaviour-risk change outside the control-plane scope, and none of them is keystroke-reachable, so they are not a safety surface. The table owns routing + safety; not the re-implementation of value parsing.

The deprecated bare aliases `SECONDARY_ON` / `SECONDARY_OFF` / `SECONDARY_STATUS` and the `strncmp(command_buf, "SECONDARY_MODE", 14)` prefix match are preserved verbatim inside the metadata parser block (they compare `command_buf` directly; not in the table; reached unchanged when no table row matches).

---

## 5. Equivalence proof — covered vs not covered

**Proven in software (this session):**
- Table integrity (no duplicate names, every row has a handler, no dangerous keystroke) — firmware `static_assert` (build-time) + host test, both reading the SHARED `.def` rows.
- D5 routing: typed `start_noise_cal` -> guidance, never queues cal — host test (with teeth: a simulated re-wire to the queueing handler was confirmed to FAIL the test) + release-ELF string.
- D6 routing: destructive trio fire only on exact `CONFIRM`; bare / wrong-token / near-miss token -> no effect — host test + release-ELF string.
- BLOCKER: trailing token on a non-FORBIDDEN bare command (`reset now`, `dump junk`, `version 1`) is NOT consumed by the table — host test.
- Harness commands absent from release, present in harness — release/harness ELF string + symbol diff.
- Both envs compile clean; envelope direction correct (RAM flat at 83064 B, Flash 558702 B = -612 B).

**NOT proven in software — needs hardware smoke (orchestrator):**
- On-device serial round-trip: `:start_noise_cal` prints guidance and the LEDs/audio show no calibration transition.
- `N` then `Y` within 5 s under confirmed silence still performs a real noise calibration; `Y` without `N` still fails closed.
- `:factory_reset CONFIRM` actually wipes config + reboots; `:factory_reset` (bare) does nothing; same for `restore_defaults` and `clear_noise_cal`.
- The full pre/post differential firing every recognised command on hardware (HANDOFF item D: strcmp prefix-order vs table-lookup) — the named migration risk. **The table uses exact-match `strcmp` for bare commands — no prefix ambiguity** (and after the BLOCKER fix, a trailing token never silently dispatches a non-FORBIDDEN head). The only `strncmp` prefix command (`SECONDARY_MODE`) stayed in the metadata parser unchanged, so ordering is preserved. Hardware differential still recommended to close the gate.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | agent:embedded-firmware (Opus 4.7) | Created. Full command-equivalence matrix for the Row 1 strcmp-chain -> dispatch-table refactor; 3 signed deltas marked (D5/D6/harness); behaviour-preserving rows enumerated; software-covered vs hardware-smoke gap documented. Builds + host test results recorded. |
| 2026-05-25 | agent:embedded-firmware (Opus 4.7) | Review fixes: (1 BLOCKER) trailing-token split scoped to FORBIDDEN rows only — `reset now`/`dump junk`/`version 1` no longer dispatch; restored §5 exact-match accuracy. (3 M2) rows moved to shared X-macro `serial_cmd_table.def` consumed by firmware + host test. (4 M3) D5 host assertion given teeth. (5) legacy `if(false)` strcmp chain deleted. (6) added D-harness-2 deferred note (`dump_raw`/`ap_stream=` not gated in Row 1). (7) softened "single source of truth for keystroke-reachability" wording; `input_surface` flagged compile-time-only. Flash 558702 B (-612 B). |
