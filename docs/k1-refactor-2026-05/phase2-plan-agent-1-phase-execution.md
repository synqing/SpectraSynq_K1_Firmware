---
abstract: "Verbatim output of Plan Agent 1 (2026-05-24) — phase-by-phase execution plan for the K1 SensoryBridge Strip+Split refactor. Recorded as a draft input to the K1-rooted handoff session. This output was synthesised into the final plan at ~/.claude/plans/transient-cuddling-wirth.md, but that final plan was subsequently AUDIT-FLAGGED for source-count errors and a self-contradiction (Phase 1 Freeze Baseline captures pre-fix mode 7, Phase 3 fixes it — harness fails mode 7 by construction). Treat this draft as design input, not as a ratified plan."
---

# Plan Agent 1 — Phase Execution Plan (Verbatim Draft)

> Recorded verbatim from the 2026-05-24 Phase 2 design dispatch. This output was synthesised (with modifications) into the final plan at `~/.claude/plans/transient-cuddling-wirth.md`. Both that final plan and parts of this draft contain claims subsequently AUDIT-CONTRADICTED — see `HANDOFF-to-k1-rooted-session.md`.

---

## Cross-cutting design decisions (rationale up front)

**Artefact split between repos.** Planning artefacts (forensic audit, feature inventory, architectural target, harness spec, phase ratification) live in **LightwaveOS_Official** under `docs/k1-refactor-2026-05/` because they are Captain-facing strategy documents that outlive the fork. Per-phase forensic records, build envelope deltas, and AP/VP reference captures live in the **K1 fork** under `docs/forensics/` and `docs/refactor/` because they are commit-correlated and must rebase with code. The harness itself (test harness source) lives in the fork at `tests/harness/` so it travels with the code under test. Harness *reference data* (binary AP/VP captures) lives at `tests/harness/golden/` and is versioned with git-lfs-style discipline — text manifests in git, binaries adjacent and SHA-pinned.

**NOTE FROM HANDOFF AUTHOR: the audit flagged "harness baseline versioned in a different repo from the firmware it gates" as a weakness. Plan Agent 1 split between repos; final plan placed harness in LightwaveOS_Official. K1-rooted session should re-decide this with full audit context.**

**Worktree topology.** One persistent trunk checkout (`/Users/spectrasynq/SensoryBridge-main 9/`) stays frozen on `refactor/main`. Each phase spawns a sibling worktree at `../SensoryBridge-refactor-phaseN/` on its own branch `refactor/phaseN-*`. Phase 5 sub-tasks (strip-cross-cutting per module, split per module) get *child* worktrees off the Phase 5 branch so harness gates run identically across parallel module work. Merge order is strictly serial back to `refactor/main`; no merge until that subsystem's gate passes.

**Strip-cross-cutting vs Split order.** Strip-cross-cutting runs **first within Phase 5, per module, immediately followed by Split for that same module**. Rationale: stripping dead cross-cutting code reduces the surface area that must be ODR-correctly split, and a strip+split pair per module produces a much smaller harness-gated commit than stripping everything then splitting everything. The alternative (strip-all-then-split-all) creates one giant unreviewable diff and forfeits incremental rollback granularity.

**WAVEFORM_FAST mode 7 bug.** Bundled into **Phase 3 as its own commit** (not Phase 5). Rationale: the fix is one-line frame-shift correction at `lightshow_modes.h:1310`, it is VP-only and behaviorally isolated, and shipping it on the frozen-baseline branch *before* the harness captures golden reference data means the harness records corrected behavior as canonical. Bundling it into Phase 5 would force the harness to encode a known bug as "correct."

**AUDIT-FLAGGED — Blocker 3: This rationale is internally contradictory. The final plan placed Freeze Baseline capture in Phase 1, which runs BEFORE Phase 3 mode 7 fix. So the Freeze Baseline encodes the BUGGY mode 7 behavior, not the corrected one. K1-rooted session must resolve: either fix mode 7 BEFORE Freeze, or re-capture baseline AFTER Phase 3, or accept known-mode-7-delta in harness.**

**Sweet-Spot LED conflict.** Resolved as a **Phase 0 Captain decision point**, not deferred. Rationale: every downstream phase that touches `led_utilities.h` (which is every phase) must know whether SS LED code paths are KEEP or STRIP, and the harness in Phase 4 must know whether to instrument SS pins. Deferring forces rework.

**NOTE FROM HANDOFF AUTHOR: Captain clarified 2026-05-24 that the SS AP algorithm is a separate concern from the SS LED output. The final plan added a 6th Phase 0 artefact (SS AP+LED investigation) accordingly. K1-rooted session inherits this distinction.**

**Acceptance criteria for "refactor done":** (a) `build_src_filter` extended to include `+<*.cpp>` with at least 6 hand-written `.cpp` files compiling, (b) zero function bodies in `.h` files except templates and explicit `inline` helpers under 10 LOC, (c) globals consolidated into one `globals.cpp` translation unit with `extern` declarations in `globals.h`, (d) flash within +1.0% / RAM within +2.0% of `2cbeea9` baseline (552 622 B / 83 024 B), (e) AP harness parity vs golden within instrumentation noise, (f) VP harness frame-hash parity for all 9 modes within tolerance, (g) doctrine-gate `2026-05-24` triggers re-verified green.

**AUDIT-FLAGGED: "9 modes" is contradicted by audit (13 distinct light_mode_* defs). Re-verify mode count in K1-rooted session.**

---

## Phase 0 — Planning Artefact Production

**Goal:** produce the five Captain-ratifiable documents that authorise Phase 1+.
**Entry criteria:** none — this is the launch phase. The Equivalent Port (2026-05-24) is canonised; HEAD is `c872032`.
**AUDIT-FLAGGED: "The Equivalent Port" equivalence claim contradicted by stage7-handoff.md per audit. Re-verify before treating as canonical.**

**Inputs:** current K1 fork at HEAD, doctrine gate doc, existing forensics directory, Phase 1 findings (the feature/file census in the brief).

**Tasks:**
1. Write **K1-fork forensic audit** at `LightwaveOS_Official/docs/k1-refactor-2026-05/00-forensic-audit.md` — per-file LOC, inline-function count, global count, lookup-table count, header-monolith ranking, build-envelope baseline.
2. Write **feature inventory** at `…/01-feature-inventory.md` — source-verified table with columns: Feature, File:Line, Status (PRESENT-ACTIVE / PRESENT-GATED-OFF / ABSENT), Conflict (yes/no), Captain Decision (pending/KEEP/STRIP/DEFER).
3. Write **architectural target** at `…/02-architectural-target.md` — describes the post-refactor file layout (one `.h` + one `.cpp` per module, single `globals.cpp`, build_src_filter extension, no header function bodies).
4. Write **harness spec** at `…/03-harness-spec.md` — AP harness inputs (deterministic I2S replay), VP harness outputs (frame-hash plus pin-toggle trace), tolerance budgets, golden-capture procedure.
5. Write **phase plan ratification** at `…/04-phase-plan.md` — this document.
6. Captain reviews all five. Open conflict items (SS LED, PHOTONS_CURVE_MODE default, 125 serial commands KEEP-set) collected into one ratification meeting.
7. Captain ratification recorded as signed-off git commit on a *LightwaveOS_Official* branch — no K1 fork changes yet.

**Outputs:** five `.md` artefacts in LightwaveOS_Official; Captain decision log capturing SS-LED ruling, PHOTONS_CURVE_MODE default, serial-command KEEP set.
**Validation gate:** none — planning only. Doctrine gate: not triggered (no firmware change).
**Rollback:** discard the LightwaveOS_Official branch. Zero firmware risk.
**Captain decision points:** SS-LED source-vs-doc conflict (hardware truth wins — if K1 has no SS LEDs, code becomes STRIP); PHOTONS_CURVE_MODE 2 vs source default 0 reconciliation; serial-command KEEP set; whether 125 → ~30 is the strip target.
**Gotchas:** none operationally — but the inventory MUST be re-verified against `c872032` source, not historical memory.
**Effort:** 4 days honest (5 docs at ~1 day each, minus parallelism, plus Captain review cycle).

---

## Phase 1 — Freeze

**Goal:** convert trunk into a refactor-only branch with immutable baselines and the worktree topology.
**Entry criteria:** Phase 0 ratified by Captain.
**Inputs:** Phase 0 artefacts; HEAD `c872032`; existing tag `pre-pio-migration-20260524-1320`.

**Tasks:**
1. Tag baseline: `git tag refactor-baseline-20260525 c872032` (immutable reference for the entire refactor).
2. Create backup branch: `backup/pre-refactor-20260525` pointing at `c872032`.
3. Create `refactor/main` branch from `c872032`. Trunk policy doc added: trunk = `refactor/main`; `feat/pio-core-bump` archived.
4. Capture build envelope: `pio run -e k1_hardware` clean build; record flash/RAM; write `docs/refactor/baseline-envelope.json` with SHA, flash bytes, RAM bytes, partition size, build timestamp. This file is the canonical envelope-drift reference.
5. Create worktrees for Phases 2-5: `git worktree add ../SB-refactor-phase2 refactor/phase2-inventory` etc. (Phase 5 worktrees created later as needed.)
6. Doctrine-gate retest: run R5/R6/R7/R9/R11 verification sequence on `refactor/main`; record evidence-tier-labelled output in `docs/forensics/2026-05-25-freeze-gate.md`.
7. Codeowners / branch protection: declare in repo docs that `refactor/main` accepts no commits not bearing a `[refactor-phase-N]` prefix.
8. Announce freeze in Captain's log — no feature development on trunk, only critical hardening (defined as: build breakage, doctrine-gate regression, hardware safety).

**Outputs:** `refactor-baseline-20260525` tag; `backup/pre-refactor-20260525` branch; `refactor/main` branch; `docs/refactor/baseline-envelope.json`; freeze-gate forensic; four-plus worktrees on disk.
**Validation gate:** clean build matches `2cbeea9` envelope ±0 bytes (since `c872032` already shipped); R5/R6/R7/R9/R11 doctrine-gate triggers green.
**Rollback:** `git reset --hard refactor-baseline-20260525`; or check out `backup/pre-refactor-20260525`. Worktrees can be `git worktree remove`'d safely.
**Captain decision points:** approve freeze announcement; confirm trunk policy.
**Gotchas:** worktree merge conflicts not yet a risk (no parallel commits yet); confirm `.pio/` is not shared between worktrees (PIO build cache per-worktree).
**Effort:** 1 day.

---

## Phase 2 — Inventory Ratification

**Goal:** convert Phase 0's feature inventory into a committed, source-line-accurate KEEP/STRIP/DEFER classification with Captain signatures.
**Entry criteria:** Phase 1 complete; worktree `SB-refactor-phase2` checked out.
**Inputs:** `01-feature-inventory.md` from Phase 0; current source at `refactor-baseline-20260525`.

**Tasks:**
1. Re-verify every PRESENT row by grepping the actual file:line against `refactor-baseline-20260525` — catch any drift between Phase 0 inventory draft and ratified source.
2. Add columns: `Strip-Class` (Isolated / Cross-cutting / N/A) and `Phase` (3 / 5 / DEFER).
3. Tabulate every `#ifdef`, `#if SB_HAS_*`, and dead branch in `encoders.h`, `serial_menu.h`, `led_utilities.h`, `globals.h`.
4. Captain walks the 125 serial-command list; marks KEEP/STRIP/DEFER per command. Output: `docs/refactor/serial-commands-ratified.md`.
5. Captain rules on SS-LED final disposition (referencing Phase 0 decision) — produces explicit file:line strip list if STRIP.
6. Captain rules on `PHOTONS_CURVE_MODE`: keep `#ifdef` or hardwire to mode 2? Update `led_utilities.h:185` sweet-spot inconsistency note.
7. Commit `docs/refactor/inventory-ratified.md` on `refactor/phase2-inventory`; merge to `refactor/main` (no code change, doc-only commit).
8. Cross-reference each STRIP item with whether it is Isolated (Phase 3) or Cross-cutting (Phase 5).

**Outputs:** `inventory-ratified.md` with per-feature Captain signature; serial-command ratification; SS-LED ruling; PHOTONS_CURVE_MODE ruling.
**Validation gate:** doc-only phase — no build gate. Verify all file:line references resolve at `refactor-baseline-20260525`.
**Rollback:** revert the doc-only merge commit; trivial.
**Captain decision points:** every KEEP/STRIP/DEFER. Captain-owned by definition.
**Gotchas:** silent file:line drift between Phase 0 draft and Phase 2 ratification — verification step (1) is mandatory.
**Effort:** 2 days (1 day verification, 1 day Captain walkthroughs).

---

## Phase 3 — Strip-Isolated

**Goal:** delete clearly-isolated dead code with zero cross-cutting risk; ship the WAVEFORM_FAST fix on the same branch.
**Entry criteria:** Phase 2 ratification merged.
**Inputs:** `inventory-ratified.md`; worktree `SB-refactor-phase3` on `refactor/phase3-strip-isolated`.

**Tasks:**
1. Strip M5ROTATE8 / encoder dead branches in `encoders.h` (gated by `SB_HAS_ROTATE8=0`). One commit. Build + envelope check.
2. Strip SS-LED code if Captain ruled STRIP — pins 7/8/9, related lookup, `led_utilities.h:185` quadratic hardcode. One commit. Build + envelope check.
3. Strip ratified serial commands (the Phase 2 STRIP set). One commit per logical group (e.g. all WiFi-residual commands, all P2P-residual commands). Build + envelope check per commit.
4. **WAVEFORM_FAST mode 7 frame-shift fix** at `lightshow_modes.h:1310` as a standalone, clearly-titled commit `[refactor-phase-3] fix(vp): correct WAVEFORM_FAST frame advance to match S2`. Build + manual visual smoke (Captain captures monitor log).
5. Remove any `#ifdef` scaffolding that becomes unconditional after Phase 3 strips.
6. Run R5 (monolith) re-test trigger from doctrine gate — capture forensic.
7. Update `docs/refactor/baseline-envelope.json` with post-Phase-3 envelope (allowed: flash ↓, RAM ↓ only).
8. Merge `refactor/phase3-strip-isolated` → `refactor/main` only after Captain signs off.

**Outputs:** stripped source; per-strip commit chain; updated envelope; WAVEFORM_FAST fix commit; Phase-3 forensic.
**Validation gate:** clean build; flash and RAM both strictly decrease or stay equal vs Phase 1 envelope (a strip phase that grows the binary is a red flag); doctrine R5 green; Captain VISUAL smoke for WAVEFORM_FAST OK.
**Rollback:** per-commit revert via `git revert`; or reset branch to `refactor-baseline-20260525` and restart. Backup branch unaffected.
**Captain decision points:** sign-off per strip commit group; VISUAL confirmation on WAVEFORM_FAST; serial-port log capture (agent does not touch port).
**Gotchas:** ODR is **not yet** a risk (still single-TU); static-init order **is not** a risk (no new globals); SS-LED conflict already resolved in Phase 2 so no ambiguity here; do NOT touch `incandescent_lookup` aggregate initializer (that work belongs to Phase 5); do NOT auto-fire `start_noise_cal`.

**AUDIT-FLAGGED: `incandescent_lookup` was claimed to live in `led_utilities.h` but audit says it's in `constants.h:439`. K1-rooted session must re-locate.**

**Effort:** 4 days.

---

## Phase 4 — Harness

**Goal:** build minimal AP+VP equivalence harnesses and capture golden reference data on the post-Phase-3 frozen baseline.
**Entry criteria:** Phase 3 merged to `refactor/main`.

**NOTE FROM HANDOFF AUTHOR: Plan Agent 1 placed harness build in Phase 4, AFTER Phase 3 strip. Final plan moved harness firmware into Phase 1 to capture baseline at freeze. This compounded the mode 7 self-contradiction (Blocker 3). K1-rooted session must redesign phase order.**

**Inputs:** harness spec from Phase 0; current K1 fork HEAD; deterministic I2S test vectors.

**Tasks:**
1. Create `tests/harness/` directory in fork. AP harness: a host-runnable extraction of the audio pipeline that consumes deterministic PCM input and emits goertzel/FFT/beat output traces. VP harness: an on-device mode that runs each lightshow_mode deterministically over a fixed AP trace and emits per-frame CRC of the LED buffer plus pin-toggle timing.
2. Define golden inputs: one synthetic 30-second multi-tone sweep WAV, one music excerpt, one silence segment.
3. Define golden outputs: AP trace (text, line-delimited JSON), VP trace (binary frame-hash stream).
4. Build host-side AP harness as a separate cmake project under `tests/harness/ap/` so it does NOT enter `build_src_filter` (preserves single-TU firmware build envelope).
5. Build on-device VP harness as a separate PIO env `[env:k1_harness]` — never default env. This env extends `build_src_filter` to include the harness `.cpp`; the production env `k1_hardware` stays single-TU. Document this in `platformio.ini`.
6. Run AP+VP on `refactor/main` HEAD; capture goldens to `tests/harness/golden/` with SHA-pinned manifests. Captain captures VP run log via serial-to-file (agent reads file).
7. Write `tests/harness/run.sh` (host runner) and `tests/harness/README.md` documenting the gate procedure.
8. Doctrine gate R5/R7 re-test on `k1_hardware` env to confirm production envelope unchanged by harness work.
9. Merge to `refactor/main`.

**Outputs:** AP+VP harness source; golden reference data; harness runbook; updated `platformio.ini` with the new env; harness baseline forensic in `docs/forensics/`.
**Validation gate:** `k1_hardware` env envelope **byte-identical** to Phase 3 (harness must not touch production build); AP harness reproduces its own golden; VP harness frame-hashes stable across two consecutive runs.
**Rollback:** revert harness commits; `tests/harness/` is additive so revert is clean.
**Captain decision points:** approve harness spec implementation; capture VP golden runs (serial-port discipline rule — agent never opens port).
**Gotchas:** keep harness OUT of `build_src_filter = +<*.ino> +<*.ino.cpp>` for `k1_hardware` to avoid drift; flag any non-deterministic VP output (random seeds, uninitialised memory reads, micros()-based timing) as a harness-design bug, not a code bug — must be fixed before goldens are sealed; **mode 7 WAVEFORM_FAST golden encodes the fixed behavior** because the fix landed in Phase 3.

**AUDIT-FLAGGED: This is the Blocker 3 self-contradiction. K1-rooted session must resolve.**

**Effort:** 7 days honest (harness design is the dominant unknown; AP harness host-runnable is most of the work).

---

## Phase 5 — Strip-Cross-Cutting + Split

**Goal:** the dangerous work. Per-module: strip cross-cutting dead code, then split header monolith into `.h` + `.cpp`. Harness gates every commit.

**Entry criteria:** Phase 4 goldens sealed; harness reproducible.
**Inputs:** harness; ratified inventory; per-file LOC census; `refactor/main` HEAD.

**Sub-phase ordering** (one module per child worktree, merged sequentially): **5a led_utilities** → **5b globals** → **5c system** → **5d serial_menu** → **5e lightshow_modes** → **5f i2s_audio + GDFT + audio_transfer** → **5g remainder**. Rationale: led_utilities is the worst monolith (52 inline funcs, 415 globals locally referenced) — solving it first proves the pattern and surfaces ODR/aggregate-init gotchas while the diff is still recoverable. globals second because every other module depends on it. Lightshow_modes deferred to mid-phase so the VP harness has caught any AP regressions first.

**Tasks per sub-phase (5a as template):**
1. Spawn child worktree `SB-refactor-phase5a-led-utilities` on `refactor/phase5a-led-utilities`.
2. **Strip cross-cutting first**: remove the dead `#ifdef`s, dead branches, and globals that ratified inventory marked STRIP-cross-cutting for this module. Commit. Run harness AP+VP gate. Envelope check.
3. Extend `build_src_filter` to include `led_utilities.cpp` (this is the build-system change — must be one of the first commits in 5a so the rest of 5a is exercising the dual-TU path).
4. **Split function bodies header → cpp**: move each inline function definition from `led_utilities.h` to `led_utilities.cpp`, leaving prototypes in the header. Commit in batches of 5-10 functions. Harness gate per batch.
5. **Aggregate-initializer discipline**: when moving `CRGB16 incandescent_lookup = { 1.0000, 0.4453, 0.1562 }` and similar, preserve **byte-identical initializer syntax** — do NOT add explicit `SQ15x16(...)` constructors (the 2025-09-19 incident regressed exactly this way with zero compile warnings).
6. **Globals migration (Phase 5b proper)**: move definitions from `globals.h` to `globals.cpp`; leave `extern` declarations in `globals.h`. Static-init order: review and document every global that is assigned in another global's initializer or that depends on `bridge_fs` runtime override (the `clk_rate=12800` precedent). Capture init-order map.
7. Harness gate per commit. Any AP delta outside instrumentation noise: STOP, investigate, revert if root cause not found in 30 min.
8. R5 doctrine trigger re-test at end of each sub-phase.
9. Merge sub-phase to `refactor/main` only after envelope check (flash ≤ baseline + 1%, RAM ≤ baseline + 2%) and full AP+VP golden parity.
10. Next sub-phase rebases on updated `refactor/main`.

**Outputs:** dual-TU build (`build_src_filter` extended), per-module `.h`+`.cpp` pair, `globals.cpp` translation unit, per-module forensic with envelope delta and harness diff, final acceptance commit on `refactor/main`.

**Validation gate per sub-phase:** AP harness within instrumentation noise vs golden; VP harness frame-hash matches golden for every mode (or Captain-documented tolerance); envelope within acceptance budget; doctrine R5/R7 green; build envelope **monotonic non-regression** vs sub-phase start (regression = STOP).

**Final acceptance gate (end of 5g):** all seven acceptance criteria from cross-cutting section above.

**Rollback:** per-sub-phase revert merge commit; or reset `refactor/main` to start-of-Phase-5 tag (recommended: tag `refactor-phase5-start` before 5a begins). Per-batch within sub-phase: standard `git revert`. Backup branch from Phase 1 remains the ultimate floor.

**Captain decision points:** approve each sub-phase merge; rule on any envelope-drift exception; rule on any harness-tolerance widening request (default answer: NO, fix the code); rule on any VISUAL deviation Captain spots that harness missed; serial-port discipline throughout (Captain captures, agent reads file).

**Gotchas (all pre-empted from brief):** ODR violations when same function defined in `.h` and `.cpp` after partial migration — mitigated by removing header body in same commit that adds cpp body; static-init order regressions like `clk_rate=12800` — mitigated by init-order map in 5b; aggregate-initializer silent runtime regression like the 2025-09-19 `incandescent_lookup` incident — mitigated by the byte-identical-syntax rule and VP harness frame-hash gate; VP drift like WAVEFORM_FAST that AP misses — mitigated by VP harness being a hard gate not advisory; build envelope drift — mitigated by per-commit envelope check with monotonic-non-regression rule; worktree merge conflicts — mitigated by strictly serial sub-phase merge order.

**Effort:** 5a led_utilities: 6 days; 5b globals: 5 days; 5c system: 3 days; 5d serial_menu: 4 days; 5e lightshow_modes: 4 days; 5f i2s/GDFT/audio_transfer: 4 days; 5g remainder + final acceptance: 3 days. **Total Phase 5: 29 days honest.**

---

## Total effort honest estimate (Plan Agent 1)

Phase 0: 4d · Phase 1: 1d · Phase 2: 2d · Phase 3: 4d · Phase 4: 7d · Phase 5: 29d. **Total: 47 working days (~9.5 weeks calendar at single-Captain pace with normal review cycles).**

**AUDIT-FLAGGED: Captain-time underestimated 3-5×. Per-commit harness gating × 40+ Phase 5 sub-phase commits × Captain-only-can-capture × ~30 min per harness session = far more than ~2 days Captain budget claimed elsewhere. K1-rooted session must re-budget.**

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | claude-code (Opus 4.7) | Persisted Plan Agent 1's phase execution plan verbatim. Audit-flagged claims inline. Created during handoff to K1-rooted session. |
