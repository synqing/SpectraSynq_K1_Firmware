> **⚠️ SUPERSEDED 2026-05-25 — DRAFT INPUT ONLY, DO NOT EXECUTE.**
>
> This document is the transient plan draft copied from `~/.claude/plans/transient-cuddling-wirth.md` into the repo per the execution-handover brief §6.3. It has been **superseded by `01-CORRECTED-PLAN.md`** in this same directory, which folds in the audit's pre-ratification checklist (`docs/forensics/2026-05-24-refactor-plan-audit.md` — 3 blockers, 6 weaknesses) and Captain's 2026-05-25 questioning-round rulings.
>
> Material defects vs. live source at baseline `9423ea0`:
> - L13 equivalence claim ("matches the S2 baseline within instrumentation noise") — unverified; see `01-CORRECTED-PLAN.md §11` for the precise canonical-agnostic framing
> - L16 "1 .ino + 11 .h" — actual: 19 `.h`
> - L20 "141 strcmp" — actual: 186
> - L62, L202, L297, L298, L323, L332, L335 etc. — "9 modes" — actual: 13 (with Tier A vp_probe currently covering only 9; Phase 0 extends to 12 deterministic + 1 principled exception)
> - L92-94, L144-145, L185 — WAVEFORM_FAST Phase 1 freeze vs Phase 3 fix logical contradiction — resolved by moving the fix to the first commit of Phase 1, pre-freeze
> - L264 — SS AP claimed in `audio_transfer.h`; actually lives in `i2s_audio.h:254-315`
> - L325 — "~2 days Captain-time" — under-estimate; per-commit hardware gating means ~25-40 Captain hardware sessions
> - L250-253 — Phase 0 artefact home and Freeze Baseline location in `LightwaveOS_Official`; corrected plan puts them in this repo
>
> **Read `01-CORRECTED-PLAN.md` instead. This file is retained as historical input only.**

---

# K1 SensoryBridge Firmware Refactor — End-to-End Plan

**Plan date:** 2026-05-24
**Plan author:** Claude Code (Opus 4.7) with Captain Yeap, after Phase 1 source verification and three parallel Plan-agent designs
**Target repo:** `/Users/spectrasynq/SensoryBridge-main 9/` (K1 fork)
**Planning artefact home:** `LightwaveOS_Official/docs/agent-outputs/analysis/k1-refactor-2026-05/`
**Baseline:** commit `c872032` on branch `feat/pio-core-bump` (Fix-D shipped; 552 622 B flash / 83 024 B RAM at migration baseline `2cbeea9`)

---

## Context

The PIO toolchain migration landed cleanly on 2026-05-24: arduino-esp32 3.2.0 + ESP-IDF 5.4.1 + FastLED 3.10.3 RMT5. The K1 audio pipeline now matches the S2 baseline within instrumentation noise on every load-bearing variable (SSL, max_raw, follower, peak_scaled, silence_flag, DC sign). This achievement is canonised as "The Equivalent Port" at `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md`.

But the underlying codebase is structurally unfit for further feature development:
- 1 `.ino` + 11 `.h` header-monolith
- Single-TU build (`build_src_filter = +<*.ino> +<*.ino.cpp>`)
- 277+ globals in `globals.h` with inline function bodies
- `led_utilities.h` is 2046 LOC with 52 inline functions and 415 globals
- 141 `strcmp` dispatch arms in `serial_menu.h`
- Documented runtime hazard from header→cpp moves (the 2025-09-19 `incandescent_lookup` aggregate-init incident broke runtime silently with zero compile warnings)
- Project's own `CLAUDE.md` ground rule already states: "Headers = declarations only (no function bodies, no globals)" — the current code violates this rule

The K1 → FE → Kickstarter critical path requires adding feature surface. Every feature added on top of the current foundation increases the cost of fixing it later. The refactor is paid off now, or it compounds.

**The methodology that just produced The Equivalent Port applies here:** forensic-first, source-verified, doctrine-enforced, empirical-capture-gated, Founder Execution Boundary respected, parallel SSA dispatch for research. The migration was downstream of methodology. The refactor will be too.

**Strategic shape (Captain-ratified):** Freeze → Inventory → Strip(isolated) → Harness → Strip(cross-cutting) + Split.

**Why now:** we now have empirical equivalence verification (dump_raw + post-Fix-D guards). Previous refactor attempts (LightwaveOS Phase 8 "Agent-Induced Catastrophe") failed because they had no regression detector. We do now.

---

## Phase 0 — Planning Artefact Production

**Goal:** produce six Captain-ratifiable documents that authorise Phase 1+.

**Effort:** 5 days agent-time, ~1 day Captain-review time
**Branch:** none yet — Phase 0 work lives in `LightwaveOS_Official` only
**Validation gate:** Captain reviews and ratifies all six artefacts in a single decision session

**Deliverables** (all under `LightwaveOS_Official/docs/agent-outputs/analysis/k1-refactor-2026-05/`):

1. **`00-forensic-audit.md`** — K1-fork source-verified audit. Per-file LOC, inline-function count, global count, lookup-table count, header-monolith ranking, build-envelope baseline, ODR/aggregate-init hazard inventory. 5-tier evidence taxonomy. Anchored to commit `c872032`.

2. **`01-feature-inventory.md`** — Current-source-verified feature table with columns: Feature, File:Line, Status (PRESENT-ACTIVE / PRESENT-GATED-OFF / ABSENT), Conflict (yes/no), Captain Decision (pending/KEEP/STRIP/DEFER), Strip-Class (Isolated / Cross-cutting / N/A), Phase (3 / 5 / DEFER). Source-anchored to `c872032`.

3. **`02-sweet-spot-investigation.md` — NEW PER CAPTAIN CLARIFICATION 2026-05-24.** Source-trace the Sweet Spot AP algorithm and the Sweet Spot LED output code as **two distinct components**. Identify every consumer of SS L/C/R levels (LED outputs only? AP-internal? render modes? AGC? silence detection?). Classify each consumer as LED-output-only or AP-load-bearing. Captain decision matrix:
   - SS LED output (PWM writes, pin assignments, hardcoded `led_utilities.h:185` brightness): proposed STRIP (vestigial on K1, no physical hardware)
   - SS AP algorithm: STATUS PENDING — Captain decides after reading the forensic. Default: KEEP-UNTOUCHED until at least the Harness phase, when behavioral equivalence to S2 can be re-validated under any future strip decision.

4. **`03-architectural-target.md`** — Post-refactor module decomposition, dependency DAG, header/source split rules, file organization (proposed `src/` tree), globals strategy (hybrid: shared in `core/state.cpp`, module-private as TU-local statics, `CONFIG` in `config/config.cpp`), build structure (`k1_hardware` env unchanged + optional `native` env for off-target unit tests), anti-patterns forbidden, current-file→new-module migration table. Acceptance criteria for declaring the architectural target achieved.

5. **`04-harness-spec.md`** — Minimal AP+VP equivalence harness design. AP harness: extends existing `dump_raw=` with `ap_stream=<ms>` for envelope/spectrogram/chromagram capture. VP harness: two tiers — Tier A wires the existing-in-tree `vp_probe_*` machinery (`lightshow_modes.h:1671-1875`) to a new serial command for 9-mode hash+energy coverage; Tier B adds `frame_dump=<metric>,<mode>,<dur>,<every_n>` for live streaming of framebuffer hash, energy, centre-of-mass (the WAVEFORM_FAST 1.60× speed-drift detector), and FPS. Tolerance bands per metric per mode. Reference data location: `LightwaveOS_Official/docs/agent-outputs/analysis/harness-baselines/freeze-c872032/`. Off-target diff scripts at `LightwaveOS_Official/scripts/regression-harness/`. **SUPERSEDED stimulus detail:** current locked package uses AP-only tone/music captures and silence-only VP Tier B.

6. **`05-phase-plan.md`** — This document, refined with Phase 0 findings.

**Captain decision points within Phase 0:**
- SS AP algorithm KEEP / KEEP-PENDING-INVESTIGATION / STRIP (default: KEEP-PENDING)
- SS LED output STRIP / KEEP (default: STRIP, vestigial on K1)
- `PHOTONS_CURVE_MODE` ruling: keep `#ifdef` (0/1/2) or hardwire to mode 2 (Captain's stated default)
- Lightshow mode count verification: Agent 2 found 9; Plan Agent 2 hinted at additional modes (kaleidoscope, quantum_collapse) — Phase 0 audit confirms actual count and KEEP/STRIP per mode
- Serial command surface: 141 commands per Plan Agent 2 (vs 125 from Agent 2 — Phase 0 audit reconciles). Captain rules KEEP/STRIP per command
- Music corpus: two pinned tracks vs no-music-in-MVP harness
- Worktree topology: one-worktree-per-phase + child-worktrees-per-sub-phase in Phase 5 (default) vs single-worktree branch-only topology

**Rollback:** discard the `LightwaveOS_Official` planning branch. Zero firmware risk.

---

## Phase 1 — Freeze

**Goal:** convert trunk into a refactor-only branch with immutable baselines and the worktree topology.
**Effort:** 1 day agent-time + 0.5 day Captain freeze-baseline capture session
**Entry criteria:** Phase 0 ratified by Captain
**Validation gate:** clean build matches `2cbeea9` envelope ±0 bytes (since `c872032` already shipped); doctrine R5/R6/R7/R9/R11 triggers green; harness baseline captured

**Tasks:**

1. Tag baseline: `git tag refactor-baseline-20260525 c872032` (immutable reference for the entire refactor).
2. Create backup branch: `backup/pre-refactor-20260525` pointing at `c872032`.
3. Create `refactor/main` branch from `c872032`. Trunk policy doc added; `feat/pio-core-bump` archived as historical.
4. Capture build envelope: clean build, record flash/RAM, write `docs/refactor/baseline-envelope.json` with SHA + flash bytes + RAM bytes + partition size + timestamp. This is the canonical envelope-drift reference for all subsequent phases.
5. Create worktrees: `git worktree add ../SB-refactor-phase2 refactor/phase2-inventory` etc.
6. Doctrine-gate re-test: R5/R6/R7/R9/R11 verification with evidence-tier labels; record at `docs/forensics/2026-05-25-freeze-gate.md`.
7. Codeowners policy: declare in repo docs that `refactor/main` accepts no commits not bearing a `[refactor-phase-N]` prefix.
8. **Land harness firmware additions** (gated behind `-DENABLE_AP_STREAM=1`, `-DENABLE_FRAME_DUMP=1`, `-DENABLE_VP_PROBE_CMD=1` build flags). One commit, zero hot-path cost when disabled. Required for harness reference capture later in this phase.
9. **Captain freeze-baseline capture session** (~30 min):
   - Flash freeze build with harness flags enabled
   - `start_noise_cal` under verbal silence (Captain confirms)
   - AP capture: `dump_raw=silence`, `dump_raw=tone`, `ap_stream=5000` × 2 music tracks
   - VP capture: `vp_probe=all` then `frame_dump=all,<m>,5000,4` under confirmed silence only. **SUPERSEDED details:** current locked package uses the 12-mode roster with 11 deterministic Tier A modes.
   - Captain hands log directory to agent
10. Agent processes baselines into canonical form. Files chmod a-w. Write `docs/agent-outputs/analysis/harness-baselines/freeze-c872032/CANONICAL.md` ("The Freeze Baseline" — visual+audio counterpart to The Equivalent Port).
11. Announce freeze in Captain's log. No feature development on trunk except critical hardening (definition: build breakage, doctrine-gate regression, hardware safety).

**Outputs:** `refactor-baseline-20260525` tag; `backup/pre-refactor-20260525` branch; `refactor/main` branch; baseline envelope JSON; freeze-gate forensic; worktrees on disk; harness firmware additions committed; canonical harness baseline captured and protected.

**Rollback:** `git reset --hard refactor-baseline-20260525`; or check out `backup/pre-refactor-20260525`. Worktrees `git worktree remove`'d.

**Pre-empted gotchas:** PIO build cache per-worktree (`.pio/` not shared); harness flags must default OFF in release build envelope check (envelope measured with flags disabled to preserve hot-path purity claim).

---

## Phase 2 — Inventory Ratification

**Goal:** convert Phase 0's draft inventory into a committed, source-line-accurate, Captain-signed KEEP/STRIP/DEFER classification.
**Effort:** 2 days agent-time + Captain walkthrough cycles
**Entry criteria:** Phase 1 complete; worktree `SB-refactor-phase2` checked out
**Validation gate:** doc-only phase — no build gate. Verify all file:line references resolve at `refactor-baseline-20260525`.

**Tasks:**

1. Re-verify every PRESENT row by grepping the actual file:line against `refactor-baseline-20260525`. Catch any drift between Phase 0 inventory draft and ratified source.
2. Add columns to inventory: `Strip-Class` (Isolated / Cross-cutting / N/A), `Phase` (3 / 5 / DEFER), `Captain-Signature` (date).
3. Tabulate every `#ifdef`, `#if SB_HAS_*`, and dead branch in `encoders.h`, `serial_menu.h`, `led_utilities.h`, `globals.h`.
4. Captain walks the 141-command serial surface; marks KEEP/STRIP/DEFER per command. Output: `docs/refactor/serial-commands-ratified.md`.
5. **Captain rules on SS LED output** per Phase 0 `02-sweet-spot-investigation.md`: STRIP (default — vestigial on K1) or KEEP. Strip target = PWM writes, pin assignments, hardcoded brightness at `led_utilities.h:185`.
6. **Captain rules on SS AP algorithm**: KEEP-UNTOUCHED (default — investigation showed AP consumers exist) or KEEP-WITH-LATER-REVIEW (investigation found only LED consumers — flag for post-Harness re-evaluation). DEFER until Phase 5 or later regardless; not in Phase 3 strip scope.
7. Captain rules on `PHOTONS_CURVE_MODE`: keep `#ifdef` (3 modes) or hardwire to mode 2.
8. Captain rules on lightshow mode roster (per Phase 0 mode-count verification).
9. Commit `docs/refactor/inventory-ratified.md` on `refactor/phase2-inventory`; merge to `refactor/main` (doc-only commit, no code change).

**Outputs:** `inventory-ratified.md` with per-feature Captain signature; serial-command ratification; SS-LED ruling; SS AP ruling; `PHOTONS_CURVE_MODE` ruling; lightshow mode roster ratification.

**Rollback:** revert the doc-only merge commit; trivial.

**Pre-empted gotchas:** silent file:line drift between Phase 0 draft and Phase 2 ratification (mitigated by mandatory re-verification step 1); Captain decision fatigue across 141 commands (mitigated by grouping into logical bundles for batch ratification).

---

## Phase 3 — Strip-Isolated

**Goal:** delete clearly-isolated dead code with zero cross-cutting risk. Ship the WAVEFORM_FAST mode 7 frame-shift fix on the same branch.
**Effort:** 4 days agent-time
**Entry criteria:** Phase 2 ratification merged
**Validation gate:** clean build; flash and RAM both **strictly decrease or stay equal** vs Phase 1 envelope; doctrine R5 green; harness AP+VP gate PASS vs Freeze Baseline; Captain visual smoke for WAVEFORM_FAST OK

**Tasks:**

1. Strip M5ROTATE8 / encoder dead branches in `encoders.h` (gated `SB_HAS_ROTATE8=0`). One commit. Build + envelope check + harness gate.
2. Strip SS LED output code (PWM writes, pin assignments, `led_utilities.h:185` hardcoded quadratic) **only if Phase 2 ruled STRIP**. SS AP algorithm UNTOUCHED. One commit. Build + envelope check + harness gate (the harness must show no AP-side regression — if it does, Phase 0 SS investigation was wrong about LED-vs-AP independence, STOP and revisit).
3. Strip ratified-STRIP serial commands. One commit per logical group (e.g., all S2-hardware-UI commands, all dead-code commands). Build + envelope check + harness gate per commit.
4. **WAVEFORM_FAST mode 7 frame-shift fix** at `lightshow_modes.h:1310` as a standalone, clearly-titled commit: `[refactor-phase-3] fix(vp): correct WAVEFORM_FAST frame advance to match S2`. The fix: add `dt`-scaled transport (mirror what `WAVEFORM_HYBRID` does) so frame-stepping doesn't accumulate with `LED_FPS`. Bundled in Phase 3 so the Freeze Baseline captures *corrected* mode 7 behavior — not the bug. Captain visual smoke confirmation required before commit.
5. Remove `#ifdef` scaffolding that becomes unconditional after Phase 3 strips.
6. Doctrine R5 re-test; capture forensic at `docs/forensics/2026-05-26-phase3-strip.md`.
7. Update `docs/refactor/baseline-envelope.json` with post-Phase-3 envelope (allowed direction: flash ↓, RAM ↓ or =).
8. Merge `refactor/phase3-strip-isolated` → `refactor/main` only after Captain signs off.

**Outputs:** stripped source; per-strip commit chain; WAVEFORM_FAST fix commit; updated envelope; Phase-3 forensic; harness PASS evidence.

**Rollback:** per-commit `git revert`; or reset branch to `refactor-baseline-20260525` and restart. Backup branch unaffected.

**Pre-empted gotchas:** ODR is not yet a risk (still single-TU); static-init order is not a risk (no new globals introduced); SS-LED conflict already resolved in Phase 2; do NOT touch `incandescent_lookup` aggregate initializer (that work belongs to Phase 5b); do NOT auto-fire `start_noise_cal` — Captain confirms silence verbally before any cal command; serial-port discipline (agent never opens port; Captain captures, agent reads file).

---

## Phase 4 — Harness Hardening

**Goal:** confirm AP+VP harness reproducibility; build off-target diff infrastructure; document gate procedure; seal harness as load-bearing canon.
**Effort:** 3 days agent-time (most harness firmware already landed in Phase 1 to support freeze baseline)
**Entry criteria:** Phase 3 merged to `refactor/main`
**Validation gate:** AP+VP self-check (baseline-vs-baseline diff returns all PASS); harness instrumentation enabled flags produce no envelope change to `k1_hardware` env (verified by build with all `-DENABLE_*=0`)

**Tasks:**

1. Build `LightwaveOS_Official/scripts/regression-harness/` directory:
   - `ap_diff.py` — AP capture comparison vs baseline
   - `vp_diff.py` — VP capture comparison (Tier A hash + Tier B energy/COM/FPS with slope regression for transport-drift)
   - `parse_serial.py` — shared tagged-block parser
   - `run_diff.sh` — orchestrator
   - `README.md` — gate procedure documentation
2. Run `--self-check` modes on each script (baseline vs baseline must report all PASS — confirms parser correctness).
3. Confirm `k1_hardware` env envelope **byte-identical** to Phase 3 when harness flags disabled. If not, harness leaked into hot path — STOP, investigate, fix.
4. **Post-Phase-3 re-capture under harness**: Captain re-runs the freeze-baseline capture sequence on post-Phase-3 build with harness flags ON. Agent diffs vs Freeze Baseline. Must PASS within tolerance bands. This validates that Phase 3 strips did not regress audio or visual equivalence.
5. Document harness invocation in `docs/refactor/harness-runbook.md` and in `LightwaveOS_Official/docs/agent-outputs/analysis/harness-baselines/freeze-c872032/CANONICAL.md`.
6. Canonise "The Freeze Baseline" as a load-bearing artefact in `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md` (sibling to "The Equivalent Port"). Visual-equivalence reference data is now a protected canonical asset.
7. Doctrine R5/R7 re-test confirms production envelope unchanged.
8. Merge `refactor/phase4-harness` → `refactor/main`.

**Outputs:** off-target diff scripts; harness self-check evidence; harness runbook; canonised Freeze Baseline; Phase-3 harness validation (proves Phase 3 strips clean).

**Rollback:** revert harness script additions; `tests/harness/` additive so revert is clean. Harness firmware additions remain (they were Phase 1, before strip).

**Pre-empted gotchas:** keep harness OUT of default-build code paths via `#if ENABLE_*` macros (zero hot-path cost when disabled, mandatory); flag any non-deterministic VP output (random seeds, uninitialised memory reads, `micros()`-based timing) as harness-design bug not code bug — must be fixed before goldens are sealed; mode 7 WAVEFORM_FAST golden encodes *fixed* behavior because the fix landed in Phase 3 (this is intentional — the Freeze Baseline canonises the corrected pipeline, not the buggy one).

---

## Phase 5 — Strip-Cross-Cutting + Split

**Goal:** the dangerous work. Per-module: strip cross-cutting dead code, then split header monolith into `.h` + `.cpp`. Harness gates every commit. Aggregate-init preservation enforced.
**Effort:** ~29 days agent-time across 7 sub-phases
**Entry criteria:** Phase 4 harness sealed and validated; Phase 3 strip merged
**Validation gate per sub-phase:** AP harness within instrumentation noise vs Freeze Baseline; VP harness frame-hash match for every mode (or Captain-documented tolerance); envelope within acceptance budget (flash ≤ baseline +1%, RAM ≤ baseline +2%); doctrine R5/R7 green; **build envelope monotonic non-regression vs sub-phase start (regression = STOP)**.

**Sub-phase ordering (one module per child worktree, merged sequentially):**

- **5a — `led_utilities.h`** (worst monolith: 2046 LOC, 52 inline funcs, 415 globals, the `incandescent_lookup` aggregate-init bomb anchor) → splits into `color/pipeline.{h,cpp}`, `render/pipeline.{h,cpp}`, `render/sweet_spot.{h,cpp}`. **6 days.** First because solving it proves the pattern and surfaces ODR/aggregate-init gotchas while diff is still recoverable.
- **5b — `globals.h`** (685 LOC, 277 globals, 3 lookup tables — every other module depends on it) → splits into `core/state.{h,cpp}` (shared, ~80 globals), `config/config.{h,cpp}` (CONFIG, mode_names), module-private TU-local statics elsewhere (~150 globals collapse here). **5 days.**
- **5c — `system.h`** (586 LOC, 17 inline funcs, 76 globals) → splits into `system/boot.{h,cpp}`, `system/runtime.{h,cpp}`. Static-init order map captured here (caught the migration's `clk_rate=12800` bug). **3 days.**
- **5d — `serial_menu.h`** (2352 LOC, 141 strcmp dispatch arms — mostly mechanical, no inline funcs) → splits into `ui/serial/dispatch.{h,cpp}` + 6 `commands_*.cpp` files (audio, render, config, vp, debug, diag). Strcmp chain replaced with static dispatch table. **4 days.**
- **5e — `lightshow_modes.h`** (1911 LOC, 9 modes, plus `vp_probe_*` machinery) → splits into 9 `render/modes/*.cpp` files (one per mode) + `debug/probes.{h,cpp}`. Each mode in its own TU; future mode addition = create one file. **4 days.** Deferred to mid-phase so VP harness has caught any AP regressions from 5a–5c first.
- **5f — `i2s_audio.h` + `GDFT.h` + `audio_transfer.h`** → splits into `audio/capture.{h,cpp}`, `audio/analysis.{h,cpp}`, `audio/dump_raw.{h,cpp}`, possibly `audio/transfer.{h,cpp}` (depending on Phase 0 SS investigation findings — SS AP algorithm lives somewhere in here and must travel intact). **4 days.**
- **5g — Remainder + final acceptance**: `constants.h` → `platform/hardware_constants.h` + `platform/types.h`; `bridge_fs.h` → `config/persistence.{h,cpp}`; `Palettes.h` → `color/palettes.{h,cpp}`; `knobs.h` + `buttons.h` → `system/input.{h,cpp}`; rename `.ino` → `main.cpp`; switch `build_src_filter` from `+<*.ino> +<*.ino.cpp>` to `+<**/*.cpp>`; final acceptance verification. **3 days.**

**Tasks per sub-phase (5a as template, applies to all):**

1. Spawn child worktree on `refactor/phase5<x>-<module>`.
2. **Strip cross-cutting first**: remove dead `#ifdef`s, dead branches, globals marked STRIP-cross-cutting for this module per ratified inventory. One commit. Harness gate.
3. **Extend `build_src_filter`** to include the new `.cpp` for this module (this is the first dual-TU commit per module; rest of sub-phase exercises the dual-TU path).
4. **Split function bodies header → cpp**: move each function definition from `.h` to `.cpp`, leaving prototypes in header. Commit in batches of 5-10 functions. Harness gate per batch.
5. **Aggregate-initializer discipline (load-bearing)**: when moving any global with an aggregate initializer (e.g., `incandescent_lookup`, `note_chromagram`, palette tables, `CONFIG`), preserve **byte-identical initializer syntax**. Do NOT add explicit type constructors. Verify after each move via `xtensa-esp32s3-elf-objdump -s -j .rodata` diff (before vs after must be identical in the moved table's bytes).
6. **Globals migration (5b)**: move definitions from `globals.h` to `core/state.cpp` (shared) or module-private `static` (TU-local). Leave `extern` declarations in `globals.h`. Capture init-order map.
7. Harness gate per commit. Any AP delta outside instrumentation noise: STOP, investigate, revert if root cause not found in 30 min.
8. R5 doctrine trigger re-test at end of each sub-phase.
9. Merge sub-phase to `refactor/main` only after envelope check + full harness gate PASS.
10. Next sub-phase rebases on updated `refactor/main`.

**Outputs per sub-phase:** dual-TU build incrementally extended; per-module `.h`+`.cpp` pair; per-module forensic with envelope delta and harness diff; sub-phase merge commit on `refactor/main`.

**Final acceptance gate (end of 5g):** see Acceptance Criteria section.

**Rollback:** per-sub-phase revert merge commit; or reset `refactor/main` to start-of-Phase-5 tag (`refactor-phase5-start`, applied before 5a begins). Per-batch within sub-phase: standard `git revert`. Backup branch from Phase 1 remains the ultimate floor.

**Pre-empted gotchas (all from Phase 1 findings, applied here):**
- **Aggregate-init silent runtime regression** (2025-09-19 `incandescent_lookup` incident): mitigated by byte-identical-syntax rule + `objdump` diff verification + VP harness frame-hash gate
- **Static-init order regression** (`clk_rate=12800` precedent): mitigated by init-order map in 5b, no file-scope objects whose constructors read CONFIG
- **ODR violations**: mitigated by removing header body in same commit that adds cpp body (no overlap window)
- **VP drift like WAVEFORM_FAST**: mitigated by VP harness being a hard gate not advisory; COM-slope metric specifically catches transport-drift bugs
- **Build envelope drift**: mitigated by per-commit envelope check with monotonic non-regression rule
- **Worktree merge conflicts**: mitigated by strictly serial sub-phase merge order
- **Hardware target discipline**: serial capture, upload/flash, erase, and device-write actions are allowed when validation requires them; verify the exact target by port plus stable hardware identity before touching the device.
- **`start_noise_cal` discipline**: NEVER auto-fired; Captain confirms verbal silence first.

---

## Architectural Target (one-paragraph summary; full spec in Phase 0 `03-architectural-target.md`)

Post-refactor codebase organised as: `main.cpp` (thinnest possible setup/loop) + `platform/` (hardware_constants, types, fixed_math — leaf) + `core/state.{h,cpp}` (the one TU defining shared globals) + `config/` (CONFIG + persistence) + `audio/` (capture, analysis, noise_cal, dump_raw) + `color/` (pipeline, palettes) + `render/` (pipeline + modes/, one TU per mode) + `system/` (boot, runtime, input) + `peripherals/encoders.{h,cpp}` (stub when disabled) + `ui/serial/` (dispatch + 6 commands_*.cpp grouped by domain) + `debug/` (vp_perf, probes). Dependency direction: platform → core → config → audio → color → render → system → peripherals → ui (UI depends on every module it commands; hot path never depends on UI). Headers contain declarations only; aggregate-init syntax preserved byte-identical during moves. `build_src_filter` switches from `+<*.ino> +<*.ino.cpp>` to `+<**/*.cpp>`. Optional `native` env for off-target unit tests of pure-logic modules (forcing function: a module that can't compile native has hidden Arduino/ESP-IDF coupling).

## Equivalence Harness (one-paragraph summary; full spec in Phase 0 `04-harness-spec.md`)

Two-tier harness gating every Phase 5 sub-phase commit. **AP harness:** existing `dump_raw=silence`/`dump_raw=tone` + new `ap_stream=<ms>` for envelope/spectrogram/chromagram streaming. AP stimuli: confirmed silence for raw silence, 1 kHz tone for raw/tone AP capture, and two Captain-pinned music tracks for music AP capture. Metrics: SSL, DC, max_raw, peak_scaled, follower mean, spectrogram argmax @ 1 kHz, chromagram mean. **VP harness Tier A:** wire existing-in-tree `vp_probe_*` machinery (`lightshow_modes.h:1671-1875`) to `vp_probe=all` — deterministic seeded inputs, 9-mode hash+energy, one serial round-trip, ~10 ms. **VP harness Tier B:** new `frame_dump=<metric>,<mode>,<dur>,<every_n>` under confirmed silence only for live streaming of framebuffer FNV hash, total energy, **centre-of-mass spatial moment** (slope regression catches WAVEFORM_FAST 1.60× transport-drift class of bug), and FPS. Per-frame cost when streaming: ~100 µs at 240 MHz, well inside 10 ms frame budget at 100 Hz LED_FPS. Per-frame cost when disabled: zero (`#if ENABLE_*` build flags). Captain captures via serial monitor → log file; agent reads file and runs off-target Python diff scripts; PASS/FAIL emitted per metric per mode against Freeze Baseline tolerance bands. Freeze Baseline canonised as load-bearing artefact at `LightwaveOS_Official/docs/agent-outputs/analysis/harness-baselines/freeze-c872032/`.

---

## Critical Files

**Plan artefact home** (Phase 0 outputs land here):
- `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official/docs/agent-outputs/analysis/k1-refactor-2026-05/` (new directory)
- `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official/docs/agent-outputs/analysis/harness-baselines/freeze-c872032/` (new directory; Phase 1 output)
- `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official/scripts/regression-harness/` (new directory; Phase 4 output)

**K1 fork files modified during execution:**
- `/Users/spectrasynq/SensoryBridge-main 9/platformio.ini` — `build_src_filter` change in 5g; harness env optional addition
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` — becomes `main.cpp` in 5g
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/led_utilities.h` — splits in 5a (worst monolith, biggest risk)
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/globals.h` — splits in 5b (globals consolidation)
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/system.h` — splits in 5c (static-init-order safety)
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/serial_menu.h` — splits in 5d (141 commands → dispatch table)
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h` — splits in 5e (mode-per-TU; WAVEFORM_FAST fix lands in Phase 3 first)
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` — splits in 5f; harness `ap_stream` adds in Phase 1
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/GDFT.h` — splits in 5f
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/audio_transfer.h` — splits in 5f; **carries SS AP algorithm per Phase 0 investigation finding — TREAT WITH CARE**
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/constants.h` — splits in 5g
- `/Users/spectrasynq/SensoryBridge-main 9/SPECTRASYNQ_K1_FIRMWARE/encoders.h` — Phase 3 dead-branch strip; 5g final stub if KEEP, deletion if STRIP

**Existing reference artefacts reused (no modification):**
- `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official/docs/agent-outputs/analysis/forensic-audit-s2-to-s3.html` — audit methodology template (5-tier evidence taxonomy applied to Phase 0 K1-fork audit)
- `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official/docs/agent-outputs/analysis/sensory-bridge-lessons-doctrine.md` — 12 rules invoked at every phase gate
- `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/2026-05-24-doctrine-gate-pio-migration.md` — doctrine gate template for Phase 1 re-test
- `/Users/spectrasynq/SensoryBridge-main 9/docs/forensics/2026-05-24-k1-waveform-fast-speed-investigation.md` — anchor for the Phase 3 WAVEFORM_FAST fix
- `/Users/spectrasynq/SensoryBridge-main 9/docs/hardware/k1-hardware-definition.md` — hardware truth, anchor for SS LED vestigiality ruling
- `/Users/spectrasynq/SensoryBridge-main 9/.claude/CLAUDE.md` — K1 fork doctrine bridge (start_noise_cal discipline, serial-port discipline, evidence-tier labels)
- `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md` — canonical milestone registry; receives "The Freeze Baseline" entry at Phase 4

---

## Acceptance Criteria — Refactor Complete

Each independently verifiable. All must hold for refactor to be declared done.

### Structural
1. `grep -l "^[a-zA-Z_].*(.*) *{$" SPECTRASYNQ_K1_FIRMWARE/**/*.h | wc -l` = 0 (no function bodies in headers, modulo ≤ 5-line `inline` exceptions).
2. No global variable definitions in headers (only `extern` declarations).
3. `SPECTRASYNQ_K1_FIRMWARE.ino` no longer exists; `main.cpp` exists and is ≤ 120 LOC.
4. Dependency graph has zero cycles.
5. No `.cpp` exceeds 500 LOC. No `.h` exceeds 200 LOC. (Soft targets; deviations require justification comment.)

### Build
6. `pio run -e k1_hardware` builds clean with same warning count or fewer.
7. Flash within +1% of 552 622 B; RAM within +2% of 83 024 B.
8. `compile_commands.json` regenerates cleanly via `pio run -t compiledb`.

### Behavioral equivalence (harness-verified)
9. AP harness PASS vs Freeze Baseline for silence, 1 kHz tone, and both music tracks.
10. VP Tier A: hash-exact match for all 9 modes.
11. VP Tier B: energy within tolerance; COM-slope within ±10%; FPS within ±5% under confirmed silence only. **SUPERSEDED details:** current locked package uses the 12-mode roster.
12. dump_raw produces byte-identical output for the same I2S input as Freeze Baseline.
13. WAVEFORM_FAST mode 7 visual smoke: Captain confirms speed matches S2 reference.

### Surface preservation
14. All ratified-KEEP serial commands respond. Regression script that fires each command and checks for non-`bad_command` response passes 100%.
15. SS AP algorithm behavior preserved (or its strip explicitly approved by Captain + harness-validated post-strip).
16. DC_OFFSET 2-layer guard (Fix-D) preserved in `audio/capture.cpp` with unit-testable interface.

### Discipline
17. VP_PERF_AUDIT instrumentation: when `ENABLE_VP_PERF_AUDIT=0`, resulting binary has zero `vp_perf_*` symbols (`nm` verification).
18. `incandescent_lookup` table and every other moved aggregate-initialized table are byte-identical pre/post in `.rodata` (`objdump -s -j .rodata` diff).
19. Build flag policy documented in `CLAUDE.md`; existing flags preserved.

### Future-fitness (aspirational)
20. Adding a new lightshow mode = creating one new `.cpp` in `render/modes/`, adding one declaration, adding one enum value. Zero edits to existing mode code.
21. Adding a new serial command = adding one function + one registrar line. Zero edits to dispatch.
22. A fresh Claude session can answer "where does HSV→RGB conversion happen?" by reading the tree in under 30 seconds, without grep.

---

## Effort Estimate (honest, not optimistic)

| Phase | Effort | Notes |
|---|---|---|
| 0 — Planning artefacts | 5d agent + 1d Captain | 6 deliverables incl. SS investigation |
| 1 — Freeze + baseline | 1d agent + 0.5d Captain | Harness firmware lands here; Freeze Baseline captured |
| 2 — Inventory ratification | 2d agent + Captain cycles | Captain owns 141-command + SS rulings |
| 3 — Strip-isolated | 4d agent + Captain sign-off | Incl. WAVEFORM_FAST fix |
| 4 — Harness hardening | 3d agent + 0.5d Captain | Off-target scripts; canonisation of Freeze Baseline |
| 5a — led_utilities.h split | 6d | Worst monolith first |
| 5b — globals.h split | 5d | Static-init order map |
| 5c — system.h split | 3d | |
| 5d — serial_menu.h split | 4d | Dispatch table |
| 5e — lightshow_modes.h split | 4d | 9-modes-per-TU |
| 5f — audio (i2s+GDFT+transfer) | 4d | SS AP algorithm travels intact |
| 5g — remainder + final acceptance | 3d | `.ino` → `main.cpp`, `build_src_filter` |
| **Total** | **~44 working days agent-time + ~2 days Captain-time** | ~9 weeks calendar at single-Captain pace |

The dominant risk reservoirs are **Phase 5a** (proves the strip+split pattern works on the worst monolith) and **Phase 0 SS AP investigation** (could surface AP-load-bearing dependencies that change scope). Both deserve schedule buffer.

This is the honest number. Optimistic estimates of 30 days would be wrong — the methodology that produced The Equivalent Port in 2 hours did so because the PIO migration was bounded-scope toolchain delta. This is open-scope structural work on a header monolith with documented silent-regression history.

---

## Consolidated Captain Decision Points

**Phase 0 (resolve before Phase 1 begins):**
- SS LED output: STRIP (default) / KEEP
- SS AP algorithm: KEEP-UNTOUCHED (default) / KEEP-WITH-LATER-REVIEW / STRIP
- `PHOTONS_CURVE_MODE`: keep `#ifdef` (3 modes) / hardwire to mode 2
- Lightshow mode roster KEEP/STRIP per mode (after Phase 0 audit confirms actual count)
- Music corpus: two pinned tracks (default) / no-music-MVP
- Worktree topology: per-phase + per-sub-phase children (default) / single-worktree branch-only

**Phase 2 (per item):**
- KEEP/STRIP/DEFER for every feature in the ratified inventory
- KEEP/STRIP/DEFER for every one of the 141 serial commands

**Phase 3 (per commit):**
- Sign-off on each strip commit group
- Visual smoke confirmation on WAVEFORM_FAST fix

**Phase 4:**
- Freeze Baseline canonisation in `CANONICAL_MILESTONES.md`

**Phase 5 (per sub-phase):**
- Merge approval to `refactor/main`
- Any envelope-drift exception requests (default answer: NO, fix the code)
- Any harness-tolerance widening requests (default answer: NO, fix the code)
- Any VISUAL deviation Captain spots that harness missed

**Throughout:**
- `start_noise_cal` authorisation (Captain confirms verbal silence first; agent never auto-fires)
- Hardware target identity verification before serial, upload/flash, erase, or device-write actions.
- Flash erase only when the validation lane requires it, with verified target identity and evidence recorded.

---

## Verification — How to Test the Plan End-to-End

This plan is itself a deliverable. It is verified by:

1. **Captain ratifies via ExitPlanMode approval** — explicit acceptance of strategic shape, 6 Phase 0 artefacts, phase ordering, acceptance criteria, effort envelope.
2. **Phase 0 ratification session** — Captain reviews all 6 artefacts in one decision cycle. Any artefact rejected → revise before Phase 1 starts.
3. **Phase 1 freeze gate** — clean build matches `2cbeea9` envelope; doctrine R5/R6/R7/R9/R11 green; Freeze Baseline captured and protected.
4. **Phase 2–5 harness gates** — every phase commit passes AP+VP harness diff vs Freeze Baseline (PASS exit code 0 from `run_diff.sh`).
5. **Per-sub-phase envelope monotonicity** — flash and RAM never regress within a sub-phase; final envelope within +1% flash / +2% RAM.
6. **Final acceptance** — all 22 acceptance criteria above hold.
7. **Post-refactor canonisation** — refactor completion canonised in `CANONICAL_MILESTONES.md` as a load-bearing milestone (third entry after "The Equivalent Port" and "The Freeze Baseline").

**The refactor is verified-complete when:** the K1 firmware on `refactor/main` builds clean on `k1_hardware`, passes AP+VP harness vs Freeze Baseline within tolerance, satisfies all 22 acceptance criteria, and a new contributor can add a lightshow mode or serial command with single-file edits per criteria 20–22.

**The refactor is NOT verified-complete merely because:** code compiles, code uploads, code "looks right" visually, or any agent reports success without harness evidence. The 2025-09-19 `incandescent_lookup` incident and the WAVEFORM_FAST 1.60× drift both compiled clean. The harness is the gate, not eyeball.

---

**Plan Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | claude-code (Opus 4.7) + Captain Yeap | Created. End-to-end plan for K1 SensoryBridge firmware Strip+Split refactor. Strategic shape ratified prior; 6 Phase 0 artefacts (forensic audit, feature inventory, **SS AP+LED investigation per Captain clarification 2026-05-24**, architectural target, harness spec, phase plan). 5-phase execution: Freeze → Inventory → Strip-isolated → Harness → Strip-cross-cutting + Split. 22 acceptance criteria. Effort ~44 days agent-time + ~2 days Captain-time. |
