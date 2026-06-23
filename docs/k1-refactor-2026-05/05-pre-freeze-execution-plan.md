---
abstract: "Execution plan for the six pre-freeze commits from the LOCKED hardware-gate package (03 §2.1): (1) WAVEFORM_FAST dt-scaled transport fix — the only intentional VP-output change; (2) vp_probe reset helper; (3) vp_probe enumeration → full mode coverage; (4) AP structured stream; (5) VP Tier B frame_dump; (6) vp_probe=all command exposure. Each commit has file:line targets, the change, output-inert proof strategy, pass test, dependency order, and an autonomy classification under the no-serial / no-calibration / no-commit boundary. §3 is a CORRECTION PATCH for source-contradicted facts in the locked 03 (mode count 13→12, deterministic 12→11, quantum_collapse mode 9→6, ap_stream-already-exists) — requires Captain ratification before execution. NOT Row 1/2/3/4. Source-anchored to 00a0fcb."
---

# Pre-Freeze Execution Plan (six commits → Freeze Baseline)

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| Status | **PLAN — awaiting Captain go.** §3 correction-patch needs ratification first. |
| Authority | `03-hardware-gate-package.md` (LOCKED 2026-05-25) §2.1 commit order |
| Boundaries | **No serial opened by agent. No calibration fired. No git commit by agent.** Not Rows 1/2/3/4. |
| Source anchor | `00a0fcb`; verified `.ino:58-74`, `lightshow_modes.h`, `globals.h`, `serial_menu.h`, `i2s_audio.h` |
| Gate model | Bounded-bisect hardware VP gating (Spike #1 FAIL branch) |

> **Prerequisite:** ratify the §3 correction patch to `03` before commits 2/3/4 execute — those commits encode the (corrected) mode count + indices, and one (#4) depends on the fact that `ap_stream` already exists.

---

## 1. Commit sequence — order, autonomy, Captain touchpoints

Order is fixed by `03 §2.1` (the freeze baseline must encode the *corrected* mode 7). "Agent-autonomous" = I may write the code and compile-verify (`pio run -e k1_hardware` / `-e k1_hardware_harness`, **build only, no upload**); I never open serial, fire cal, or commit.

| # | Commit | VP output? | Agent-autonomous (write + compile) | Captain touchpoint (gates the commit) |
|---|---|---|---|---|
| 1 | WAVEFORM_FAST dt-fix | **YES — the only one** | write + compile | **Visual smoke** (perceptual trail speed) before commit |
| 2 | vp_probe reset helper | No (inert) | write + compile | Pass test: probe 11 det. modes ×2 → bit-identical (hardware capture) |
| 3 | vp_probe enumeration → 12 | No (inert) | write + compile | Captured probe shows all modes; gated on #2 |
| 4 | AP structured stream | No (flag-gated) | write + compile | Serial capture sanity (Captain) |
| 5 | VP Tier B frame_dump | No (flag-gated) | write + compile | Serial capture sanity (Captain) |
| 6 | vp_probe=all exposure | No (flag-gated) | write + compile | Serial capture sanity (Captain) |

After all six: Freeze tag + baseline capture per `03 §2.2–§2.6` (Captain-run, with the corrected stimuli manifest).

---

## 2. Per-commit detail

### Commit 1 — WAVEFORM_FAST dt-scaled transport fix (the only intentional VP change)

- **Target:** `lightshow_modes.h` — `light_mode_waveform_fast()` (starts `:1186`). The frame-coupled transport is `:1310-1313`:
  ```cpp
  if (CONFIG.MIRROR_ENABLED) { waveform_shift_upper_half_up(leds_16, 1); }   // raw "1" / frame
  else                       { shift_leds_up(leds_16, 1); }                  // raw "1" / frame
  ```
- **Root cause** (`docs/forensics/2026-05-24-k1-waveform-fast-speed-investigation.md`): 1 LED shift per *render call*; K1 runs `LED_FPS ≈ 185.69` vs S2 good-state `≈ 115.86` → **~1.60× too fast**, wall-clock.
- **Fix (mirror `light_mode_waveform_hybrid` `:1457-1470, 1576-1581`):** dt accumulator.
  - Add globals (`globals.h`, beside `waveform_fast_*` at `:243-246`): `waveform_fast_shift_accum_primary/secondary` (float), `waveform_fast_last_frame_ms_primary/secondary` (uint32_t).
  - Extend signature: `light_mode_waveform_fast(..., float& shift_accum, uint32_t& last_frame_ms)`.
  - Compute `dt` from `millis()` delta, clamp `[0.001, 0.050]` (hybrid's clamp); `shift_accum += RATE * dt`; `steps = min(floor(shift_accum), 8)`; carry fractional remainder; shift by `steps` (0 allowed).
  - **`RATE` is the calibration knob:** target S2 reference (~115.86 shifts/s). Mirror hybrid's `VP_WAVEFORM_SHIFT_RATE` *as a reference*, but the exact value is **perceptual — Captain visual smoke decides it.** Do not assume fast == hybrid rate.
  - Update call site `:1788` (primary) + the secondary-channel equivalent to pass the new state.
- **Output-inert proof:** none — this IS the output change. Compile-clean is necessary, not sufficient.
- **Captain touchpoint:** visual smoke comparing trail speed to S2 reference *before* commit. After this commit the baseline is immutable.

### Commit 2 — Deliverable #4: `vp_probe_reset_mode_statics()`

- **Target:** `lightshow_modes.h` vp_probe machinery (`:1671-1907`). Add `vp_probe_reset_mode_statics()`; call it from `vp_probe_prepare_render()` (`:1733-1767`, which already zeroes most statics at `:1755-1766`).
- **State to zero** (must be reproducible run-to-run for Tier A bit-identity): the per-mode `*_primary/_secondary` statics — `waveform_fast_last_color` / `waveform_last_color` / `waveform_hybrid_last_color`; `*_peak_scaled_last`; `waveform_shift_accum` / `waveform_hybrid_shift_accum` (**+ the new `waveform_fast_shift_accum` from commit 1**); `*_last_frame_ms` (**+ new `waveform_fast_last_frame_ms`**); `vu_level_smooth` / `vu_max_level`. (Full list verified in source.)
- **Output-inert:** yes (render-path inert; only resets between probes). Hardware, not native — Spike #1 FAIL does not block it.
- **Pass test:** probe each deterministic mode twice in one run → bit-identical hashes (Captain capture).

### Commit 3 — Deliverable #3: vp_probe enumeration → full 12-mode coverage

- **Target:** the probe list `lightshow_modes.h:1872-1881` (currently **9** modes).
- **Change:** add the 3 missing modes — `LIGHT_MODE_VU_DOT` (4), `LIGHT_MODE_KALEIDOSCOPE` (5), `LIGHT_MODE_QUANTUM_COLLAPSE` (6). Tier A hashes the **11 deterministic** modes; **`QUANTUM_COLLAPSE` (mode 6) is flagged non-deterministic** (`random_float()` at `:1059-1073`) → Tier B + visual smoke only, never a Tier A hash assertion.
- **Output-inert:** yes. Gated on commit 2.

### Commit 4 — AP structured stream (`-DENABLE_AP_STREAM`)

- **Reality (corrects 03):** `ap_stream` **already exists** — an unconditional boolean toggle `AP_STREAM_ENABLED` (`globals.h:335`) driving a 1 Hz debug emit (`i2s_audio.h:444`). It is **not** the `<ms>`-windowed structured stream the harness diff scripts need, and it is **not** flag-gated.
- **Change:** extend `ap_stream` to the `:ap_stream=<ms>` structured form emitting the §1.2 metrics (max_raw range, peak_scaled range, follower mean, spectrogram argmax @1 kHz, chromagram mean, silence_flag — sourced from `spectrogram_smooth`/`chromagram_smooth`/`max_waveform_val_*`/`smoothing_follower`/`agc_envelope`, `globals.h:160-210,497-610`), and wrap the emit in `#ifdef ENABLE_AP_STREAM` so release carries it OFF.
  - **`SSL` metric has no source global** — define it (sweet-spot level) during this commit or drop it from the metric set. **Open Q (O3).**
- **Output-inert:** yes when the flag is OFF (release).
- **Decision (O1):** extend the existing toggle vs. add a parallel windowed command. Recommend **extend** (one command, gated).

### Commit 5 — VP Tier B `frame_dump` (`-DENABLE_FRAME_DUMP`)

- **Target:** new `else if (strcmp(command_type,"frame_dump")...)` branch in `serial_menu.h` (~`:1460` block), behind `#ifdef ENABLE_FRAME_DUMP`. Form: `:frame_dump=<metric>,<mode>,<dur>,<every_n>`.
- **Helpers:** FNV hash + energy already exist (`vp_probe_hash_leds() :1684`, `vp_probe_energy() :1700`). **COM (centre-of-mass spatial moment) and FPS do not exist — add them.**
- **Output-inert:** yes when flag OFF.

### Commit 6 — `vp_probe=all` command exposure (`-DENABLE_VP_PROBE_CMD`)

- **Target:** new command branch in `serial_menu.h` behind `#ifdef ENABLE_VP_PROBE_CMD`, calling `vp_run_output_probe()` (`:1839`). Machinery exists; this commit exposes it as a serial command.
- **Output-inert:** yes when flag OFF.

---

## 3. CORRECTION PATCH for LOCKED `03` (Captain ratification required)

Source contradicts four claims in the locked package. These are load-bearing — a wrong mode index means the harness probes/skips the wrong mode and the freeze baseline's determinism contract is invalid. Evidence: `SPECTRASYNQ_K1_FIRMWARE.ino:58-74` (enum, `NUM_MODES=12`), `lightshow_modes.h:1059-1073` (quantum_collapse RNG), `serial_menu.h:1398` + `i2s_audio.h:444` (existing ap_stream).

| Loc in 03 | Current (wrong) | Corrected |
|---|---|---|
| §1.2 | "Mode roster (13 total, per source-verified count)" | "Mode roster (**12** total — `NUM_MODES=12`, `.ino:58-74`)" |
| §1.2 | "Tier A covers **12 deterministic** modes" | "Tier A covers the **11 deterministic** modes" |
| §1.2 | "quantum_collapse (**mode 9**)" | "quantum_collapse (**mode 6**)" |
| §1.3 | "per-mode FNV hash (**12** det. modes)" | "(**11** det. modes)" |
| §2.1 #3 | "vp_probe enumeration → **13 modes**" | "→ full **12-mode** enumeration (adds VU_DOT, KALEIDOSCOPE, QUANTUM_COLLAPSE; QC non-det)" |
| §2.3 | "vp_probe=all # **12 deterministic**" | "# **11 deterministic** (QC mode 6 exits clean, non-det)" |
| §2.3 | "frame_dump … # for each of **13 modes**" | "# for each of **12 modes**" |
| §1.1/§2.1 #4 | implies `ap_stream` is a new add | note it **already exists** (boolean 1 Hz toggle); commit #4 *reshapes* it to the `<ms>` structured, flag-gated form |

`mode 7 = WAVEFORM_FAST` (§1.7, §2.3) is **correct** — no change.

**Possible non-error:** if "13" reflects a *planned* 13th mode rather than a miscount, say so and I'll frame #3 as "current 12 + 1 reserved." Default assumption: miscount → correct to 12.

---

## 4. After the six commits — Freeze (per 03 §2.2–§2.6, Captain-run)

Tag `refactor-baseline-<date>`, branch `refactor/main`, capture AP + VP Tier A + VP Tier B + visual smoke under the **corrected stimuli manifest** (§2.6). VP Tier B `frame_dump` is **silence-only**. AP uses `tone-1k`, `track-A`, and `track-B`. Derive bands (§2.5). Calibration is the explicit Captain-only pre-step (§2.3) — never scripted.

## 5. Autonomy summary

- **I can do now, on your go (no serial / no cal / no commit):** write all six commits' code and compile-verify each under `k1_hardware` (release, flags OFF) and `k1_hardware_harness` (flags ON). Stage as uncommitted diffs for your review.
- **Only you can:** flash, open serial, run captures, fire any calibration, apply the Freeze tag, and `git commit`. Commit 1 additionally needs your visual smoke before it is a commit at all.

## 6. Decisions — all RULED by Captain 2026-05-25

- **O1 — `ap_stream` → RULED:** add a **parallel** harness-only timed command **`:ap_capture=<ms>`** (behind `-DENABLE_AP_STREAM`). Do NOT overload the existing boolean `ap_stream` 1 Hz debug toggle — preserve its operator/debug semantics. (Commit #4 builds `ap_capture`, not an `ap_stream` extension.)
- **O2 — §3 correction patch → RULED:** ratified; `03` re-locked **LOCKED-AS-AMENDED** with the 12-mode / mode-6 / ap_stream-exists / envdump errata.
- **O3 — `SSL` → RULED:** keep `SSL` (sweet-spot level) as **captured metadata only, NOT a pass/fail gate metric**. Gate on AP response metrics; record SSL for context (too policy/stimulus/environment-bound to gate on).
- **O4 — execution kickoff → RULED:** authorised. Commits **1–3 landed** (1 hardware-validated: `330f59f`, `f7df772`, `54699d2`). Boundary update: agent flash/upload is permitted when Captain confirms the port (as 2026-05-25); still no calibration, no serial-command control beyond probe/capture reads.

### Status (2026-05-25)
- ✅ **#1** WAVEFORM_FAST dt-fix — flashed + visual smoke PASSED — `330f59f`
- ✅ **#2** vp_probe reset helper (generation counter; vu_dot + kaleidoscope) — `f7df772`
- ✅ **#3** vp_probe enumeration → 12 modes (11 Tier A + quantum nondet=1) — `54699d2`
- ⏳ **#4** `ap_capture=<ms>` (O1) + SSL metadata (O3), behind `-DENABLE_AP_STREAM`; needs `platformio.ini` harness env committed
- ⏳ **#5** `frame_dump` (`-DENABLE_FRAME_DUMP`) — add COM + FPS helpers (FNV/energy already exist)
- ⏳ **#6** `vp_probe=all` command exposure (`-DENABLE_VP_PROBE_CMD`; legacy command `vp_out_test`)
- then Freeze tag + baseline capture (Captain, §2.2–§2.6)

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) | Created. Pre-freeze execution plan for the six commits in locked `03 §2.1`, source-anchored to 00a0fcb. Per-commit file:line targets, output-inert proofs, pass tests, autonomy classification under no-serial/no-cal/no-commit. §3 correction patch for source-contradicted facts in locked `03` (12 modes not 13; 11 deterministic not 12; quantum_collapse mode 6 not 9; ap_stream already exists). WAVEFORM_FAST dt-fix specified mirroring light_mode_waveform_hybrid, rate constant flagged as Captain visual-smoke calibration. Awaiting Captain go + §3 ratification. |
