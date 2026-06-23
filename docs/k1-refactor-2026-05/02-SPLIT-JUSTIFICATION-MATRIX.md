---
abstract: "Split-justification matrix per Captain's 2026-05-25 pivot. Applies Captain's 5-criterion × C-mandatory-AND-(A-OR-B) gate to each proposed monolith split before scheduling any of them. Per row: which criterion (1-5 or none), evidence-grade failure mode (named code path or actual incident, not speculative worry), differential-or-equivalence gate, dependency edges. Greenlit set = transitive closure of what passes. Likely outcome: ~2 splits (lightshow_modes + minimal globals partition) + 1 command-layer extraction (serial_menu dispatch) + 1 conditional (led_utilities partial extraction, gated on Spike #1). Total Phase 5 effort collapses from ~29-32d (corrected plan) to ~10-18d (matrix). This is the NEW first Phase 0 deliverable per Captain's pivot; supersedes 01-CORRECTED-PLAN.md's 7-sub-phase Phase 5 structure. Awaits Captain ratification of the per-row rulings + Spike #1 outcome before any execution."
---

# K1 SensoryBridge Firmware Refactor — Split-Justification Matrix

| Field | Value |
|---|---|
| Matrix date | 2026-05-25 (created); 2026-05-25 (ratified) |
| Matrix author | Claude Code (Opus 4.7) with Captain Yeap |
| Status | **RATIFIED by Captain 2026-05-25 (path B).** Per-row rulings locked. Row 4 **PROMOTED from CONDITIONAL to HARD PREREQUISITE for Row 2** via source-verified C3/linkage evidence (2026-05-25 update — see Row 4 below). C5 ruled UNEVIDENCED. Spike #1 authorised native-only on throwaway branch/worktree (no serial, no hardware capture by agent, no commit/push/tag without explicit approval). |
| Baseline | `9423ea0` on branch `feat/pio-core-bump` |
| Supersedes | `01-CORRECTED-PLAN.md` §5–§9 (7-sub-phase Phase 5 structure no longer load-bearing). Carries forward: §1 audit-corrections, §2 open items, §4.2 spike/deliverable scoping, §5 WAVEFORM_FAST-as-only-intentional-VP-change framing. |
| Companion artefacts (in flight) | Spike #1 (native-compile feasibility) — beginning post-matrix-ratification per Captain directive. Spike #2 (aggregate-init), Deliverables #3/#4 — also gated on greenlit-set ratification; queued for after Spike #1 returns its verdict (sequence them to avoid pre-Spike-1 wasted scope). |

## 0. Why this document exists

Captain rejected the "split 7 monoliths" frame as failing Captain's own gate. The pivot: apply the gate to each proposed split before scheduling any of them. The matrix is the doctrinally correct artefact; the corrected plan's 7-sub-phase Phase 5 structure was operating in the rejected frame.

**Captain's directive (verbatim):** "Next action: the CC agent's first Phase 0 deliverable is not 02–06, it is a **split-justification matrix** — per monolith: which criterion (1–5 or none), evidence-grade failure mode, differential-or-equivalence gate, dependency edges. The greenlit set is the transitive closure of what passes. That matrix probably collapses 46–50 days to something far smaller, and it tells you how much of 02–06 is even worth writing."

## 1. The doctrine

### 1.1 The five criteria (per Captain's 2026-05-25 mapping)

| # | Criterion | What it actually requires |
|---|---|---|
| **C1** | **Safe command contract** | Command parser rebuilt. The dangerous-action surface is the **186-strcmp dispatch in `serial_menu.h`**. Resolution = targeted extraction of the dispatch table wherever it lives, **not** a full header-monolith programme. |
| **C2** | **Modes without collateral** | The one genuine monolith-split case: the **VP/modes monolith** (`lightshow_modes.h`). Future mode additions should be one-`.cpp`-per-mode operations, zero edits to existing mode code. |
| **C3** | **Deterministic harness** | Answered by **Spike #1 (native-compile feasibility)**, not by faith. If render code host-compiles deterministically on current single-TU structure → harness with **no split at all**. If it does not → minimal render extraction needed to make it host-testable = C3 justification, with spike failure as the evidence. |
| **C4** | **Parallel agent work** | Earns a globals partition (or any other split) **only if parallel agent work is real and queued** — not hypothetical. Currently no parallel agent work is queued for K1 firmware. |
| **C5** | **Enforced invariants** | Decomposes: **no-heap-render** and **dt-correctness** are guards/lints/types needing **no split at all**. **Centre-origin** and **no-rainbow** need a constrained render API, which **does need the VP boundary** (= `led_utilities.h` extraction). |

### 1.2 The gate

A split is justified iff it passes **C (mandatory) AND (A OR B)**:

- **A — Capability-unlock.** Something new becomes possible that wasn't before (e.g., adding a mode by creating one `.cpp` instead of editing the monolith in three places).
- **B — Safety-hazard-removal.** A demonstrated safety hazard is removed (e.g., `start_noise_cal`-on-one-byte → N/Y arm/confirm gate). The hazard must be a named code path or an actual incident, not speculation.
- **C — Regression gate.** A gate that catches behaviour regressions, mandatory either way.

**A and B are independent sufficient triggers.** A split that removes a demonstrated hazard but unlocks no new capability is greenlit (e.g., the hotkey-layer commit `9423ea0` is the canonical example — safety-only, no capability-unlock). A split that unlocks new capability without removing a hazard is also greenlit. C is required for either.

### 1.3 Differential vs equivalence gate

The regression gate (C) takes one of two forms depending on whether the split is coupled to a behaviour change:

- **Pure extraction** (no behaviour change intended): **equivalence gate** — zero delta required for PASS. Hash-identical / byte-identical / within-instrumentation-noise per metric.
- **Extraction bundled with a fix** (behaviour change intended, e.g., C1 safer command surface, C5 enforced invariants): **differential gate** — enumerated, Captain-signed-off delta list. Equivalence gate either falsely blocks the work or waves an unreviewed change through.

The matrix below records which gate form applies per row.

## 2. Evidence-grade failure modes — the standard

Per Captain rider on point 5: **"a 'hidden global-state collision' must be a named code path or an actual incident — your hotkey example is the standard — not a speculative worry, or it becomes a magic phrase that justifies anything."**

What counts as evidence-grade:

- ✅ **Named code path** — a specific file:line where the hazard / capability gap lives, source-verified at baseline `9423ea0`.
- ✅ **Actual incident** — a documented historical failure (e.g., 2025-09-19 `incandescent_lookup` aggregate-init runtime regression; Stage 7 `start_noise_cal` cal-poisoning; the hotkey-layer Rev3 `N`-as-single-keystroke audit catch).
- ❌ **Speculative worry** — "what if globals collide later" / "what if a future mode needs X" / "we might want to add Y" — without a named referent.

This standard applies to every row of the matrix.

## 3. Per-monolith matrix

For each candidate split, the criterion (or none), evidence-grade failure mode, gate form, dependency edges, and ruling. Source-verified at `9423ea0`.

### Row 1 — `serial_menu.h` (2823 LOC, 186 strcmp dispatch arms)

| Field | Value |
|---|---|
| Criterion | **C1** (safe command contract) |
| Trigger | **B — safety-hazard-removal** (capability-unlock A also partially applies) |
| Evidence-grade failure mode | **Actual incident:** hotkey-layer Rev3 audit caught `N`-as-single-keystroke binding for `start_noise_cal` as a hard blocker (see `docs/forensics/2026-05-24-hotkeys-prefreeze-review.md`). The 186-strcmp dispatch in `serial_menu.h` is the surface where every dangerous-action command is wired. **Named code path:** the strcmp chain at `serial_menu.h` (186 lines distributed through the file) carries no safety-class metadata, so an agent or human adding a command has no structural way to know whether it requires an arm/confirm gate. The N/Y precedent codified the pattern; the dispatch surface doesn't enforce it. |
| Scope | **Targeted extraction**, not full file split. Extract the strcmp chain into a static dispatch table (one row per command: name → handler → safety class). Replace strcmp loop with table lookup. Annotate each row with safety class (SAFE / ARM-REQUIRED / FORBIDDEN-FROM-SINGLE-BYTE / TYPED-ONLY). Leave the rest of `serial_menu.h` (command handlers themselves) alone in this pass. |
| Gate form | **Differential** — the dispatch behaviour changes for some commands (annotation enforces what was previously by-convention). Captain-signed-off delta list of commands whose dispatch behaviour changes. Pure-extraction gate also applies for the lookup mechanics (table lookup must produce same handler routing as strcmp chain for every command that doesn't change class). |
| Dependency edges | **None material.** Extraction can happen in-place in `serial_menu.h`. Does not require globals partition (handlers stay in-place, calling the same globals they already call). Does not require modes split. |
| Ruling | **GREENLIT — RATIFIED 2026-05-25** (B + C, no prerequisites). Targeted extraction only, not full serial_menu split. |
| Estimated effort | ~3-5 agent-days (build dispatch table, classify 186 commands, replace strcmp loop, differential gate). Captain time: per-commit hardware harness gate per logical batch + sign-off on the delta list. Per Captain ratification: safety-class taxonomy + candidate behaviour delta list **sketched in Phase 0** (before Row 1 execution); final exact delta list signed off at Row 1 gate. |

### Row 2 — `lightshow_modes.h` (1910 LOC, 13 modes, vp_probe machinery)

| Field | Value |
|---|---|
| Criterion | **C2** (modes without collateral); **C3 conditionally** (if Spike #1 fails and modes need extraction to host-compile); **C5 partially** (centre-origin and no-rainbow invariants, *only if* C5 evidence-grade failure mode exists — see Row 4) |
| Trigger | **A — capability-unlock** (one-`.cpp`-per-mode operation; future mode additions become single-file edits per acceptance criteria 20-22 of the corrected plan) |
| Evidence-grade failure mode | **Named code path:** the hotkey-layer commit `9423ea0` had to touch `lightshow_modes.h` (for VPO output extension in vp_probe), `serial_menu.h` (hotkey dispatch), and globals to land a single feature. Per-mode-TU structure would localise mode-touching changes to single files. **Actual incident:** the WAVEFORM_FAST 1.60× frame-shift bug (`docs/forensics/2026-05-24-k1-waveform-fast-speed-investigation.md`) lived inside `lightshow_modes.h:1310-1312` for an unknown duration — review/audit/test of a single mode requires reading the whole 1910-line monolith. |
| Scope | **Pure split** per mode: `render/modes/light_mode_gdft.cpp`, `render/modes/light_mode_bloom.cpp`, etc. 13 modes → ~13-14 files (the two `light_mode_bloom` overloads at lines 357 and 865 likely co-locate). `vp_probe_*` machinery extracted to `debug/probes.cpp`. |
| Gate form | **Equivalence** — pure extraction, zero behaviour change intended. Tier A hash-identical for 12 deterministic modes + Tier B within-tolerance for `quantum_collapse`. |
| Dependency edges | **HARD prerequisite #1: globals partition (Row 3, minimal scope).** Per-mode `.cpp` files cannot link against globals defined in headers without multiple-definition errors. Modes-referenced globals (`CONFIG`, `spectrogram_smooth`, `chromagram_smooth`, `audio_vu_level_*`, palette functions, vp_probe-touched state) must move to a `.cpp` with `extern` declarations in the header. **HARD prerequisite #2: `led_utilities.h` minimal extraction (Row 4) — PROMOTED 2026-05-25 from soft to hard via source-verified C3/linkage evidence.** See Row 4 below: 58 plain function definitions in `led_utilities.h` produce ODR violations when included from multiple `light_mode_X.cpp` TUs. **SOFT prerequisite: `vp_probe_*` extension to 13 modes + reset helper (Deliverables #3/#4)** — pre-Freeze deliverables; gate the equivalence harness used to validate the split, not the split itself. |
| Ruling | **GREENLIT — RATIFIED 2026-05-25, conditional on prerequisites.** Sequence: Spike #2 → Row 3 (globals minimal) → Row 4 (led_utilities minimal definitions→cpp) → Row 2 (per-mode TU split). |
| Estimated effort | ~4-5 agent-days (split per mode, redirect dispatch, regenerate vp_probe enumeration). Captain time: per-sub-phase hardware harness (Spike #1 FAILED 2026-05-25 → bounded-bisect locked; see Appendix A.8). |

### Row 3 — `globals.h` (684 LOC, 277 globals)

| Field | Value |
|---|---|
| Criterion | **C4 standalone (FAILS)** — no parallel agent work is currently real or queued for K1 firmware. **Prerequisite to C2** (Row 2 lightshow_modes split). |
| Trigger | **None standalone.** Pulled in by transitive closure from Row 2 (B-trigger via Row 2). |
| Evidence-grade failure mode (standalone) | **None evidence-grade.** No named hazard from globals being in a header. The 277-global count is large but not a documented incident source. C4-driven justification would require a named queued parallel-agent work-stream — currently none exists. |
| Evidence-grade failure mode (as Row 2 prerequisite) | **Named code path:** per-mode `.cpp` files in Row 2 cannot compile without `extern` declarations for the globals they reference. Compiler errors are deterministic and immediate. |
| Scope | **MINIMAL** — only the globals referenced by `light_mode_*` function bodies and `vp_probe_*` machinery. Source-verified subset: `CONFIG` struct, `spectrogram_smooth[]`, `chromagram_smooth[]`, `audio_vu_level_*`, `note_chromagram[]`, palette functions (`palette_owns_colour_source` etc.), and the `vp_render_secondary_channel` / `chroma_val` / `hue_position` state used by `vp_probe_prepare_render`. **Not** a full 277-global migration; **not** redistribution to TU-local statics (that's a tracked post-acceptance optimisation per `01-CORRECTED-PLAN.md` Open Item #5). |
| Gate form | **Equivalence** — pure extraction, zero behaviour change. Aggregate-init byte-identity verified per Spike #2 proven pattern (`CONFIG_DEFAULTS` move). |
| Dependency edges | **Prerequisite: Spike #2 PASS** (aggregate-init pattern proven for CONFIG_DEFAULTS). Spike #2 failure blocks Row 3 (and therefore Row 2). |
| Ruling | **GREENLIT — RATIFIED 2026-05-25 as Row 2 prerequisite ONLY** (transitive closure). Standalone C4 fails (no queued parallel work). Scope strictly limited to modes/vp_probe-referenced globals; not a full 277-global migration. |
| Estimated effort | ~3-4 agent-days (identify referenced subset, relocate to globals.cpp, verify byte-identity for `CONFIG_DEFAULTS` + `mode_names[]` if both moved). Captain time: per-sub-phase hardware harness (Spike #1 FAILED 2026-05-25 → bounded-bisect locked; see Appendix A.8); aggregate-init `objdump` verification is agent-only. |

### Row 4 — `led_utilities.h` (2045 LOC, 58 plain function definitions, 1 static-inline)

**STATUS UPDATE 2026-05-25: PROMOTED from CONDITIONAL to HARD PREREQUISITE for Row 2** via source-verified C3/linkage evidence (Captain's tightening + my 2026-05-25 grep verification). C5 ruled UNEVIDENCED by Captain and removed from this row's justification.

| Field | Value |
|---|---|
| Criterion | **C3 — linkage path (source-verified):** per-mode TUs cannot link against `led_utilities.h` while it contains plain (non-`inline`, non-`static`) function definitions. **C5 ruled UNEVIDENCED 2026-05-25** — Captain confirmed no named centre-origin/no-rainbow incident; do not use doctrine or speculative risk as evidence. Re-open C5 only if a named incident/source path is produced later. |
| Trigger | **A — capability-unlock** (Row 2 per-mode TUs only become possible after Row 4). |
| Evidence-grade failure mode (C3 linkage) | **Source-verified at `9423ea0` 2026-05-25 [FACT]:** `grep -cE '^inline\\s+' SPECTRASYNQ_K1_FIRMWARE/led_utilities.h` = **0**; `grep -cE '^static\\s+' ...` = **1** (only `write_sweet_spot_pwm` at line 153); plain external-linkage function definitions = **58** (`interpolate_hue`, `force_incandescent_colour`, `set_dot_position`, `draw_line`, `apply_incandescent_filter`, etc.). `lightshow_modes.h` `#include`s `led_utilities.h` and has 126 callsites into it. **Per-mode `.cpp` TUs (Row 2) would each include `led_utilities.h` and produce N copies of each of 58 plain definitions → 58 × (N-1) "multiple definition" link errors.** Compiler/linker behaviour is deterministic; no Spike required to confirm this — the rule is C++ ODR. (Captain's framing: "true per-mode translation units will probably trip ODR/linkage unless they create a slim declarations header plus one compiled definition unit.") |
| Evidence-grade failure mode (C3 host-compile, additional) | **Independent justification gated on Spike #1 outcome.** If Spike #1 fails because `light_mode_gdft`'s shim list cannot avoid pulling in `led_utilities.h` plain definitions, that's a second C3 trigger — but already covered by the linkage path above. Spike #1 outcome may refine SCOPE (which 58 functions need careful shim treatment), not WHETHER Row 4 happens. |
| Scope | **MINIMAL — definitions-to-cpp only.** Move all 58 plain function definitions from `led_utilities.h` to a new `led_utilities.cpp`. Add prototypes (function signatures + semicolons) to `led_utilities.h`. Keep the 1 `static inline` function (`write_sweet_spot_pwm`) in the header (internal linkage, no ODR issue). Extend `build_src_filter` in `platformio.ini` to include `+<led_utilities.cpp>` — this is the **first dual-TU commit** of the refactor. **NOT a full 2045-LOC file split.** NOT API restructuring. NOT C5 invariant enforcement (deferred). |
| Gate form | **Equivalence** — pure extraction, zero behaviour change intended. Tier A hash + Tier B within-tolerance per Freeze Baseline. Performance check (FPS) is part of Tier B: function relocation can interact with compiler inlining heuristics — if FPS drops materially, re-evaluate inlining hints on the moved functions. |
| Dependency edges | **None upstream.** Row 4 is the first dual-TU commit — it doesn't depend on Spike #2 (aggregate-init) because `led_utilities.h` has no aggregate-init declarations at top level (only enum + forward declarations + plain functions). The aggregates (`incandescent_lookup` in `constants.h`, `CONFIG_DEFAULTS` in `globals.h`) are *consumed* by these functions but not defined in `led_utilities.h`. **Downstream:** Row 2 depends on Row 4. |
| Ruling | **GREENLIT — RATIFIED 2026-05-25 as Row 2 prerequisite via source-verified C3/linkage evidence.** Scope strictly limited to definitions-to-cpp move. |
| Estimated effort | ~3-4 agent-days (move 58 function definitions, add prototypes, extend `build_src_filter`, verify equivalence gate). First dual-TU build of the refactor — may surface arbitrary compiler/linker subtleties that hadn't materialised in single-TU mode (e.g., `inline` hint losses, ODR-defended duplicates from transitively-included libraries). Schedule buffer warranted. Captain time: per-sub-phase hardware harness gate (Spike #1 FAILED 2026-05-25 → bounded-bisect locked; see Appendix A.8). |

### Row 5 — `system.h` (585 LOC, 17 inline funcs)

| Field | Value |
|---|---|
| Criterion | **None pass.** |
| Trigger | None. |
| Evidence-grade failure mode | **None at evidence-grade.** The migration-era `clk_rate=12800` bug was caught and lives in commit history. DC_OFFSET sanity clamp at `system.h:353-371` is a guard, not a split candidate (per C5: guards/lints don't need splits). No named incident, no current hazard. |
| Scope | N/A |
| Gate form | N/A |
| Dependency edges | None — no consumer requires system.h to be split. |
| Ruling | **DEFER.** The corrected plan's Phase 5c "system.h pattern-prover" rationale doesn't survive Captain's gate — there's no criterion-passing reason to split system.h. Pattern-proving is a means, not an end; if no row needs proving, no proving needs to happen. |
| Estimated effort | 0 (deferred). |

### Row 6 — `i2s_audio.h` + `GDFT.h` + `audio_transfer.h`

| Field | Value |
|---|---|
| Criterion | **None pass.** SS AP algorithm could be a C5 candidate but Captain prior-ruled KEEP-UNTOUCHED. Fix-D guard is in place. |
| Trigger | None. |
| Evidence-grade failure mode | **None at evidence-grade.** Stage 7 K1↔S2 SSL numbers are unverified-pending-silence-window-check (corrected plan Open Item #1) but that is not a split-justification; it's a measurement-hygiene question. No named hazard from audio being header-monolithic. |
| Scope | N/A |
| Gate form | N/A |
| Dependency edges | None — modes are downstream of audio and don't require audio split. |
| Ruling | **DEFER.** SS AP algorithm KEEP-UNTOUCHED holds. `audio_transfer.h` cleanup (per stage7-handoff #2) is a separate hygiene task, not a refactor split. |
| Estimated effort | 0 (deferred). |

### Row 7 — `constants.h` + `Palettes.h` + `bridge_fs.h` + `knobs.h` + `buttons.h` + `.ino → main.cpp` + `build_src_filter` switch

| Field | Value |
|---|---|
| Criterion | **None pass.** |
| Trigger | None. |
| Evidence-grade failure mode | **None at evidence-grade.** Files are small (47-453 LOC). No incidents. The `.ino → main.cpp` rename and `build_src_filter` switch are cosmetic relative to architecture. C4 might be invoked if parallel work materialises, but it isn't queued. |
| Scope | N/A |
| Gate form | N/A |
| Dependency edges | None — no consumer requires these splits. **However:** Row 3 (globals minimal) touches `incandescent_lookup` consumption pattern indirectly via Spike #2's proof on `CONFIG_DEFAULTS`. If Row 2 lands and Row 3 lands, the `constants.h` aggregate-init class for `incandescent_lookup` and palette tables remains in `constants.h` (still header-only); consumers in the modes `.cpp` files reference the extern declarations from `constants.h`. No split needed. |
| Ruling | **DEFER all.** |
| Estimated effort | 0 (deferred). |

## 4. Dependency graph (post-ratification 2026-05-25)

```
                              [Spike #2]
                              aggregate-init
                              pattern proof
                                  │
                                  ▼ (PASS required)
                        ┌──────────────────┐
                        │ Row 3            │
                        │ globals.h        │
                        │ MINIMAL          │
                        │ partition        │
                        └──────────────────┘
                                  │
                                  ▼ (HARD prereq)
                        ┌──────────────────┐
                        │ Row 4            │
                        │ led_utilities.h  │ ◀── HARD PREREQ
                        │ MINIMAL: 58      │     (source-verified
                        │ defs → .cpp +    │      C3/linkage 2026-05-25)
                        │ prototypes in .h │
                        └──────────────────┘
                                  │
                                  ▼ (HARD prereq)
[Deliverable #4]──────▶ ┌──────────────────┐
reset helper            │ Row 2            │
(must succeed)          │ lightshow_modes  │
        │               │ per-mode-TU      │
        ▼               │ split (13 modes) │
[Deliverable #3]──────▶ └──────────────────┘
vp_probe extension
(must succeed)

[Spike #1] FAILED     (Captain ruling 2026-05-25 option B)
native-compile         Class E: vendored FixedPoints static-constexpr
feasibility            rejected by clang AND gcc-15; xtensa-gcc lenient.
  → VP GATE MODEL LOCKED: bounded-bisect HARDWARE gating
    (per-sub-phase HW capture + per-commit static VP-semantics
     classification + WAVEFORM_FAST regression injection test).
    Row 4 still happens (source-verified C3/linkage, unaffected by FAIL).

[Row 1]
serial_menu           (no prerequisites; standalone)
dispatch extraction   ─────────────▶ GREENLIT (RATIFIED)

[Rows 5/6/7]
system.h, audio,
constants/etc.        (no criteria pass) ──▶ DEFER (RATIFIED)
```

## 5. Greenlit set — RATIFIED 2026-05-25 (transitive closure)

**Base greenlit set (executes unconditionally per ratification):**

1. **Row 1 — `serial_menu.h` dispatch-table extraction.** Independent. (C1 / B+C / differential gate)
2. **Spike #2** → proves aggregate-init pattern (PASS required to proceed; FAIL = STOP + escalate).
3. **Row 3 — `globals.h` MINIMAL partition** (Row 2 prerequisite via transitive closure). Scope = modes/vp_probe-referenced globals only. (equivalence gate)
4. **Row 4 — `led_utilities.h` MINIMAL extraction** (Row 2 prerequisite via source-verified C3/linkage evidence). Scope = 58 plain function definitions → `led_utilities.cpp`; prototypes in header; extend `build_src_filter`. First dual-TU commit of the refactor. (equivalence gate)
5. **Deliverable #4 — vp_probe reset helper** (must succeed pre-Freeze; gates Tier A reproducibility for Row 2's equivalence harness).
6. **Deliverable #3 — vp_probe enumeration extension to 13 modes** (must succeed pre-Freeze; gated on #4).
7. **Row 2 — `lightshow_modes.h` per-mode-TU split.** Depends on Rows 3 + 4 + Deliverables #3/#4. (C2 / A+C / equivalence gate)

**Spike #1 RESULT: FAIL (Captain ruling 2026-05-25, option B).** VP gate model is LOCKED to the bounded-bisect hardware fallback. The native VP per-commit gate is abandoned — Class E (vendored FixedPoints in-class `static constexpr SFixed` non-literal) is rejected by both AppleClang 17 and GCC-15; only lenient xtensa-gcc accepts it, so a native compiler cannot be trusted as a compiler-equivalent gate. Evidence: `spike-1-native-compile-outcome.md §8`. **Active VP gate model:**
- **Bounded-bisect hardware VP gating** — per-sub-phase hardware capture (Captain), NOT per-commit native.
- **Per-commit static classification of VP-semantics commits** — agent flags any commit touching `light_mode_*` bodies / `render/` / `color/` / shared `vp_*` state; flagged commits get an additional in-sub-phase hardware gate to bound the bisect window.
- **Deliberate WAVEFORM_FAST regression injection test on the hardware gate** (Phase 4) — proves the hardware harness detects regressions.
- Cost: ~15-22 Captain hardware sessions across the refactor (vs ~8-10 a native gate would have allowed). Accepted knowingly; Captain-time is the calendar critical path.
- **Row 2 include-hygiene scope-add (NEW, from Spike #1 evidence):** the spike confirmed `lightshow_modes.h`/`constants.h` rely on `.ino`-driven include order (Class C + the `constants.h`/`FixedPointsCommon.h` source-hygiene defect). Row 2/Row 4 per-TU `.cpp` files require an explicit include-hygiene pass, not just `#include "lightshow_modes.h"`. Tracked as a Row 2 sub-task.

**C5 status: UNEVIDENCED 2026-05-25.** Re-opens only on a named incident/source path. Default = no C5-driven splits.

**Deferred (RATIFIED 2026-05-25):** Rows 5/6/7 (system.h, audio modules, constants/Palettes/bridge_fs/knobs/buttons, .ino rename, build_src_filter switch to `+<**/*.cpp>`). Not on the wishlist-strike — eligible for revisit when evidence-grade justification appears.

## 6. What's deferred and why

Deferred items are NOT struck from the long-term refactor wishlist — they are removed from the *current* refactor's scope because no criterion currently justifies them at evidence grade. Captured for future revisit:

- **system.h** — defer until a named incident or capability-unlock appears. The 17 inline funcs and 76 globals are not a hazard per se.
- **i2s_audio.h + GDFT.h + audio_transfer.h** — defer; SS AP KEEP-UNTOUCHED holds; `audio_transfer.h` cleanup is hygiene not refactor.
- **constants.h** + **Palettes.h** + **bridge_fs.h** + **knobs.h** + **buttons.h** — defer all; no named hazards, no capability gates.
- **`.ino → main.cpp` rename + `build_src_filter = +<**/*.cpp>` switch** — defer; cosmetic relative to architecture; the existing `+<*.ino> +<*.ino.cpp>` filter works fine; the rename can happen as part of a future C4-driven push if/when parallel work is real.
- **TU-local static redistribution of globals** — already tracked deferred in `01-CORRECTED-PLAN.md` Open Item #5.

## 7. Revised effort estimate — RATIFIED 2026-05-25 (vs corrected plan)

Row 4 promoted to hard prerequisite adds ~3-4 agent-days vs the pre-ratification estimate. Net still well below the corrected plan.

| Work | Corrected plan (7 sub-phases) | Matrix (greenlit set, ratified) |
|---|---|---|
| Phase 0 documents | 6d agent + 1d Captain review (six documents) | ~2-3d agent + ~0.5d Captain review (matrix + per-row ruling; minimal `02-forensic-audit.md` baseline anchor + `04-sweet-spot-investigation.md` + reduced `03-feature-inventory.md` Row 1 deltas only + spike/deliverable outcome docs; 05/07 dropped) |
| Phase 0 spikes/deliverables | Same: 2 Spikes + 2 Deliverables | Same: 2 Spikes + 2 Deliverables (carries forward unchanged) |
| Phase 1 (Freeze + pre-Freeze commits) | 2d agent + 1-1.5d Captain | Same: 2d agent + 1-1.5d Captain |
| Phase 2 (Inventory ratification) | 2.5d agent + 3-4h Captain | ~1.5d agent + ~2h Captain (reduced scope: only Row 1 dispatch-class commands need Captain ruling, not all 186) |
| Phase 3 (Strip-isolated) | 3-4d agent + 1-3 Captain hardware sessions | ~1-2d agent + ~1 Captain hardware session (encoder dead-branch + SS LED if STRIP-ruled; rest is in Row 1) |
| Phase 4 (Harness hardening) | 2-3d agent + 1 Captain hardware session | Same: 2-3d agent + 1 Captain hardware session |
| **Phase 5 = greenlit-set execution** | **~29-32d agent** (7 sub-phases) | **~13-18d agent** (Row 1 ~3-5d + Row 3 ~3-4d + Row 4 ~3-4d + Row 2 ~4-5d) |
| **Total agent-days** | **~46-50d** | **~24-32d** |
| **Total Captain hardware sessions** | **~25-40** (Q1 mis-read in 01-CORRECTED-PLAN) | **~8-15** spike-conditional (PASS = ~8-10; FAIL = ~12-15) |
| **Calendar (sustainable pace)** | ~10-12 weeks | **~5-7 weeks** |

The matrix still collapses the refactor by roughly half in both agent-time and Captain-time. Row 4 promotion adds ~3-4 agent-days but is necessary — not optional — per source-verified C3/linkage evidence.

## 8. Open questions — RESOLVED by Captain 2026-05-25 ratification

1. **Row 4 C5 evidence — RESOLVED: NONE supplied.** Captain confirmed no evidence-grade centre-origin/no-rainbow incident. "Do not use general doctrine or speculative risk as evidence. Re-open only if a named incident/source path is produced later." C5 removed from Row 4's justification entirely.
2. **Row 2 vs Row 4 prerequisite hardness — RESOLVED: HARD.** Source-verified 2026-05-25 via grep on `led_utilities.h`: 58 plain function definitions, 0 `inline`, 1 `static`. Per-mode TUs would trip ODR. Row 4 promoted to hard prerequisite via C3/linkage evidence. (Captain framing: "true per-mode translation units will probably trip ODR/linkage unless they create a slim declarations header plus one compiled definition unit.")
3. **Row 1 differential delta sign-off cadence — RESOLVED: Phase 0 sketch + Row 1 gate sign-off.** Per Captain: "Phase 0 sketch required. I want the safety-class taxonomy and candidate behaviour delta list before Row 1 execution. Final exact delta list is signed off at Row 1 gate." Folded into Row 1 estimated effort.
4. **5g aggregate-init verification scope — RESOLVED: confirmed.** Per Captain: "If constants.h/Palettes.h are deferred, incandescent_lookup and palette tables do not move, so no objdump verification for them. Spike #2 only proves the pattern for moved Row 3 aggregates such as CONFIG_DEFAULTS and any other aggregate actually moved."
5. **Phase 0 deliverable trimming — RESOLVED: accepted with harness-contract caveat.** Per Captain: "Keep a minimal harness contract somewhere in the spike/deliverable outputs; do not let the harness spec disappear entirely." See Appendix A below. Folded: `03-feature-inventory.md` reduced to Row 1 command deltas + 13-mode roster only; `05-architectural-target.md` and `07-phase-plan.md` dropped unless new evidence appears.

## 9. Next actions (post-ratification 2026-05-25)

**In flight now:**
- **Spike #1 — native-compile feasibility.** Authorised by Captain post-matrix-ratification. Scope: native-only on throwaway branch/worktree. Agent-doable portion: throwaway worktree, `[env:native_vp]` addition, shim header creation, native build attempt for `vp_probe_*` + `light_mode_gdft`, native CRGB output capture for synthetic input. No serial, no hardware capture by agent, no commit/push/tag without explicit Captain approval. Captain hardware reference capture is the final PASS criterion step (queued for when convenient).

**Queued (do not start before Spike #1 returns verdict):**
- Spike #2 — aggregate-init relocation (decision gate for Row 3 + Row 4 strategy).
- Deliverable #4 — vp_probe reset helper (must succeed pre-Freeze).
- Deliverable #3 — vp_probe enumeration extension (must succeed pre-Freeze, gated on #4).
- Phase 0 documents `02-forensic-audit.md`, `03-feature-inventory.md` (reduced), `04-sweet-spot-investigation.md`.
- Row 1 dispatch-table sketch + safety-class taxonomy (per Captain Q3 ruling — Phase 0).

**Reconvene per Captain directive:** when Spike #1 returns its verdict (native build PASS/FAIL + native CRGB output). At that point: VP gate model locks, Spike #2 begins, Phase 0 documents draft begins, and a minimal-execution plan (the successor to the superseded `01-CORRECTED-PLAN.md`) can be drafted with confidence in scope.

---

## Appendix A — Minimal Harness Contract (per Captain caveat on Phase 0 trimming)

Captain ratified dropping `06-harness-spec.md` from Phase 0 deliverables on the condition that **the harness spec content survives somewhere**. This appendix carries the minimal contract; the spike/deliverable outcome docs (#1, #2, #3, #4) carry the implementation details.

### A.1 What the harness is

A two-tier regression detector that gates every commit (Spike #1 PASS) or every commit-group (Spike #1 FAIL) against the Freeze Baseline. Self-baselines at the Freeze commit (after WAVEFORM_FAST fix lands as pre-Freeze commit 1; immutable thereafter). Semantics = "any divergence from baseline = regression" (corrected plan §11 framing carries forward).

### A.2 The two tiers

- **Tier A — hash equivalence.** `vp_probe=all` produces a deterministic hash per mode under synthetic-input render. Pass = bit-identical hash for all 12 deterministic modes vs baseline. `quantum_collapse` is the documented exception (non-deterministic by design; falls to Tier B + visual smoke).
- **Tier B — metric tolerance.** `frame_dump=<metric>,<mode>,<dur>,<every_n>` streams FNV hash + total energy + centre-of-mass spatial moment (transport-drift detector — the WAVEFORM_FAST 1.60× class of bug catcher) + FPS for any mode under live or synthetic input. Pass = within Captain-ratified tolerance bands per mode.

### A.3 The required-for-correctness prerequisites

- **Deliverable #3 — vp_probe enumeration to 13 modes** (must succeed pre-Freeze): `lightshow_modes.h:1873-1881` extended to cover the 4 modes currently outside Tier A.
- **Deliverable #4 — vp_probe reset helper** (must succeed pre-Freeze, Captain R1 instruction not discretion): `vp_probe_reset_mode_statics()` resets every per-mode `static` so multi-mode probing is reproducible within a single run. Pass test = probe each of 12 deterministic modes twice in succession, assert bit-identical Tier A output. Quantum_collapse Tier B run-to-run stability tested separately; if unstable, mode 9 has zero automated coverage and the §3 Row 2 + §9 quantum_collapse compensating control (mandatory Captain visual smoke for any commit touching mode 9 or its call-graph dependencies) applies.

### A.4 The deliberate-regression injection test

Phase 4 hardening includes a deliberate-regression injection: on throwaway branch off `refactor/main`, revert the WAVEFORM_FAST fix (which lands pre-Freeze as commit 1). Captain captures Tier B for mode 7. Run `vp_diff.py` against Freeze Baseline. **Expected result: FAIL** on COM-slope metric for mode 7. This proves the harness is a detector, not a passport. Outcome recorded in `docs/forensics/2026-05-27-harness-detector-validation.md`. Throwaway branch discarded.

### A.5 Stimuli set

- Silence (for cal verification).
- 1 kHz tone (deterministic AP envelope).
- Two Captain-pinned music tracks (recorded in `stimuli-manifest.yaml` at Phase 1; Phase 0 carries proposed track list).

### A.6 Reference data location

`docs/refactor/harness-baselines/freeze-<BASELINE-SHA>/` in K1 repo (committed + tagged with freeze tag; filesystem-read-only as additional defence). NOT in LightwaveOS.

### A.7 Off-target diff scripts

`scripts/regression-harness/` in K1 repo: `ap_diff.py`, `vp_diff.py`, `parse_serial.py`, `run_diff.sh`, `README.md`. Exit code 0 = PASS for all metrics. Phase 4 deliverable.

### A.8 Gate model — LOCKED to Spike #1 FAIL branch (2026-05-25)

**Spike #1 FAILED (Captain ruling 2026-05-25 option B).** The native VP gate path (`native_diff.py`) is abandoned — see `spike-1-native-compile-outcome.md §8`. The **bounded-bisect hardware path is active**:

- **`vp_semantics_classifier.py`** (~50 LOC Python) in `scripts/regression-harness/`: given a commit diff, returns "VP-semantics-touch: yes/no" by filepath rules (touches `light_mode_*` bodies, `render/`, `color/`, shared `vp_*` state, or — per Spike #1's quantum_collapse rule — `random_float`/`SQ15x16` mode arrays/mode call-graph). 
- **Bounded-bisect window math:** any sub-phase with ≥1 VP-semantics commit gets per-commit hardware gating from that commit until the next no-VP-touch commit, keeping the bisect window small without per-commit hardware on AP-neutral commits.
- **Per-sub-phase hardware capture** (Captain) is the baseline cadence; the classifier escalates specific commits to in-sub-phase hardware gates.
- **WAVEFORM_FAST deliberate-regression injection test** (A.4) runs on this hardware gate to prove it detects regressions.

This is the minimum harness spec needed to gate the refactor under the FAIL branch. If any item disappears, the harness fails open.

---

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) + Captain Yeap | Created. Split-justification matrix per Captain's pivot from "split 7 monoliths" to "apply 5-criterion × C-AND-(A-OR-B) gate to each proposed split." Per-row matrix for 7 candidate monoliths. Likely greenlit set: Row 1 (serial_menu dispatch extraction, C1), Row 3 (globals minimal partition, C2 transitive), Row 2 (lightshow_modes per-mode-TU split, C2), Row 4 conditional (led_utilities minimal extraction, C3 gated on Spike #1 OR C5 gated on Captain evidence). Rows 5/6/7 deferred (no criteria pass). Effort collapses ~46-50d agent → ~21-32d agent; ~25-40 Captain sessions → ~8-15. Awaits Captain ratification of per-row rulings + Spike #1 verdict before execution. |
| 2026-05-25 | Captain Yeap + claude-code (Opus 4.7) | **RATIFIED (path B): matrix first, then Spike #1.** Per-row rulings locked. **Row 4 PROMOTED from CONDITIONAL to HARD PREREQUISITE for Row 2** via source-verified C3/linkage evidence (`grep` 2026-05-25: 58 plain function definitions in `led_utilities.h`, 0 `inline`, 1 `static`; per-mode TUs would trip ODR at link). **C5 ruled UNEVIDENCED** (no named centre-origin/no-rainbow incident); re-opens only on evidence. Open questions 1-5 resolved (see §8). Phase 0 deliverable trimming accepted with harness-contract caveat (Appendix A added). Effort estimate updated for Row 4 promotion: ~24-32d agent (was ~21-32d); ~8-15 Captain hardware sessions spike-conditional. Spike #1 authorised native-only on throwaway branch/worktree; no serial, no hardware capture by agent, no commit/push/tag without explicit approval. |
| 2026-05-25 | Captain Yeap + claude-code (Opus 4.7) | **Spike #1 VERDICT: FAIL (option B).** Native VP gate abandoned — Class E (vendored FixedPoints in-class static-constexpr SFixed non-literal) rejected by AppleClang 17 AND GCC-15; only lenient xtensa-gcc accepts it, so native cannot be a trusted compiler-equivalent gate. VP gate model LOCKED to bounded-bisect hardware fallback: per-sub-phase HW capture + per-commit static VP-semantics classification (`vp_semantics_classifier.py`) + WAVEFORM_FAST regression injection test. §4 graph, §5 greenlit set, Appendix A.8 updated to FAIL branch. Cost: ~15-22 Captain HW sessions (accepted). Row 2 gains an include-hygiene sub-task (Spike #1 Class C evidence). Worktree preserved as evidence; no vendored patch; no commit/push/tag. Next: hardware fallback harness contract → Row 1 dispatch-table safety-class sketch → freeze-baseline capture plan → then ratified-row execution under hardware gating. Production rows do NOT start until fallback harness/freeze gate is locked. |
| 2026-05-25 | claude-code (Opus 4.7) | Closeout: collapsed residual per-row gate-cadence conditionals (Rows 2/3/4 "Estimated effort" cells) from "per-commit (Spike #1 PASS) or per-sub-phase (Spike #1 FAIL)" to the locked FAIL branch (per-sub-phase, bounded-bisect; see Appendix A.8). Criterion-justification text at the C3-conditional rows left intact (records ratification rationale). No ruling or scope change. |
