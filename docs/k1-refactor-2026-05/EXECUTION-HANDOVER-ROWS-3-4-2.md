---
abstract: "End-to-end execution handover brief for the K1 refactor's remaining ratified scope: closeout → Row 3 (globals MINIMAL partition) → Row 4 (led_utilities MINIMAL extraction, first dual-TU commit) → Row 2 (lightshow_modes per-mode-TU split) → done. Defines the operating mode (continuous autonomous execution; surface only on the STOP list), the per-row gate procedure under the locked bounded-bisect hardware model, the doctrine constraints, and the definition of done. Authoritative source docs: 02-SPLIT-JUSTIFICATION-MATRIX.md and 03-hardware-gate-package.md — this brief operationalises them, it does not supersede them."
---

# K1 Refactor — End-to-End Execution Handover Brief

| Field | Value |
|---|---|
| Date | 2026-05-25 |
| From | Sandbox/Refactor PM |
| To | Executing agent (CC) |
| Authoritative sources | `02-SPLIT-JUSTIFICATION-MATRIX.md` (rows, scope), `03-hardware-gate-package.md` (gate procedure). Ground every decision in these committed docs — do not paraphrase from memory or relay a sub-agent summary. |
| Branch | `refactor/main`, branched from freeze tag `refactor-baseline-2026-05-25` (gate package §2.2) |
| First act | Commit this brief, then begin Stage 0. |

## 0. Mission — non-negotiable

The product north star: a music-to-visual translation system that exceeds Sensory Bridge's perceptual impact and musical relevance. Architecture is subordinate to that benchmark. Rows 3/4/2 are **pure extractions** — they must change **zero observable behaviour**. A row that compiles, links and hashes clean but regresses visual impact, musical responsiveness, dual-channel behaviour, colour clarity or motion memory is a **FAIL** → STOP. "Builds clean" is not success. "Gate-green AND unchanged on hardware" is.

## 1. Operating mode — read this first

**Default: continuous autonomous execution.** Do not stop, do not report, between milestones. You STOP only for the items in §5. Everything else — you handle it yourself, silently.

- **No status chatter.** No "builds clean", no "starting Row N", no progress percentages, no intermediate updates. Captain treats any noise update as a failure.
- **The reverse failure is equally real.** Do NOT suppress a STOP-list item to avoid interrupting. Every item on that list is a case where *not* stopping costs Captain more than stopping. A short, correct interruption is signal; silence on a real blocker is the failure.
- This is not "execute without asking" — see §5. It is "a large green zone and a short, exhaustive stop list."

## 2. Where you are starting from

- [FACT] Freeze baseline sealed: commit `2e0e983`, tag `refactor-baseline-2026-05-25`. Reference artefacts: `docs/refactor/harness-baselines/freeze-88428a2/` (`canonical-tier-a.json` = VP Tier A reference; `CANONICAL.md` = bands).
- [FACT] Phase 0 complete. Row 1 (`serial_menu.h` dispatch extraction, `6267825`) — **code done on worktree branch `worktree-agent-a2df0c67d0041f2cd`; NOT merged — gated-pending its own hardware gate + Captain delta sign-off (see Stage 0 amendment).** Deliverables #3/#4 (vp_probe 12-mode enumeration + reset helper) — landed pre-freeze.
- Spike #2 (aggregate-init, `944f74c`) — **confirm a clear PASS from its outcome doc before Row 3** (Row 3 relies on the proven `CONFIG_DEFAULTS` relocation pattern). If it is not a clear PASS → STOP (§5.6).
- Gate model: **bounded-bisect HARDWARE gating** (Spike #1 FAILED — native compile abandoned). Per gate package §1.1: **you never open the serial port.** You write code and build; Captain flashes, captures and does visual smoke.

## 3. The work — strict order

### Stage 0 — finish the closeout
Confirm complete; complete any that are not: freeze tag created on the seal commit + pushed to the GitHub backup; governance files committed; the `02-SPLIT-JUSTIFICATION-MATRIX.md` "Spike #1 PASS/FAIL" conditionals collapsed to the FAIL branch; working tree clean. Then proceed.

> **Amended 2026-05-25 (Captain ruling — Option B).** "Row 1 merged" is **struck** from closeout. Row 1 (`6267825`) is a **gated row, not a closeout step** — it carries signed safety-critical command-dispatch deltas (typed-`start_noise_cal` bypass, N/Y-only cal, CONFIRM tokens) whose final delta list is signed off **at the Row 1 hardware gate** (matrix Row 1). It lands via its own device gate + Captain delta sign-off when Captain runs it — conflict-free with Rows 3/4/2 (disjoint files: Row 1 = `serial_menu.h`/`serial_cmd_table.def`; Rows 3/4/2 = `globals.h`/`led_utilities.h`/`lightshow_modes.h`). `refactor/main` is branched from the freeze tag **without** Row 1; Rows 3/4/2 proceed independently and continuously.

### Row 3 — `globals.h` MINIMAL partition — equivalence gate
Scope: **only** the globals referenced by `light_mode_*` bodies and `vp_probe_*` machinery — `CONFIG`, `spectrogram_smooth[]`, `chromagram_smooth[]`, `audio_vu_level_*`, `note_chromagram[]`, palette functions, and the `vp_render_secondary_channel`/`chroma_val`/`hue_position` state. Move definitions → `globals.cpp`; `extern` declarations stay in `globals.h`. **NOT** a full 277-global migration. **NOT** TU-local static redistribution (deferred — Open Item #5). Aggregate-init moves use the Spike #2-proven pattern + per-aggregate `objdump -s -j .rodata` byte-identity check. Prereq: Spike #2 PASS.

### Row 4 — `led_utilities.h` MINIMAL extraction — equivalence gate — FIRST DUAL-TU COMMIT
Scope: move all **58 plain** (non-`inline`, non-`static`) function definitions → new `led_utilities.cpp`; add prototypes to `led_utilities.h`; keep the **1 `static inline`** function (`write_sweet_spot_pwm`) in the header; extend `build_src_filter` in `platformio.ini` with `+<led_utilities.cpp>`. **NOT** a full 2045-LOC split, **not** API restructuring. This is the first dual-TU build of the refactor — expect compiler/linker subtleties (inline-hint loss, ODR duplicates from transitive includes); **FPS is part of the gate** (relocation can change inlining). Technically independent of Row 3; execute in ratified order.

### Row 2 — `lightshow_modes.h` per-mode-TU split — equivalence gate
Scope: pure split, one `.cpp` per mode → `render/modes/light_mode_*.cpp` (~13–14 files; the two `light_mode_bloom` overloads co-locate). `vp_probe_*` machinery → `debug/probes.cpp`. **Mandatory include-hygiene pass per TU** (Spike #1 Class C evidence — each `.cpp` must include its own dependencies explicitly; do not rely on `.ino` include order). Prereqs: Row 3 + Row 4 done.

## 4. The gate — run after EVERY row, no exceptions

1. **You**: write the row's code; build `pio run -e k1_hardware_harness` (build only — never `-t upload`, never open the port); commit each logical step.
2. **You**: run `scripts/regression-harness/vp_semantics_classifier.py` on every commit diff. `yes` → that commit needs an in-sub-phase hardware gate; `no` → it rides to the row boundary. When in doubt the classifier returns `yes`; trust it.
3. **Row boundary**: hand to Captain for the device capture — he flashes the harness build, runs the gate-package §2.3 capture sequence, does visual smoke. **This handoff is required signal, not noise.**
4. **You**: run `scripts/regression-harness/run_diff.sh` on Captain's returned log dir. Exit 0 = PASS.
5. **PASS** = all 11 Tier A hashes bit-identical AND all Tier B metrics in band AND all AP metrics in band AND visual smoke clean → merge the row, start the next.
6. **FAIL** → STOP (§5.2). Never widen a tolerance to pass.

## 5. STOP list — the ONLY reasons to surface to Captain

1. **Row code-complete → hardware gate needed.** Terse: "Row N code-complete, build green, needs device gate." (Planned handoff.)
2. **Gate FAIL** you cannot root-cause and fix within 30 min / 2 attempts → STOP and state: what you tried, the actual mechanism of failure, the proposed alternative. Do not thrash; do not paper over.
3. **Anything requiring the silence window or a real calibration** → Captain-only, doctrine-absolute (calibration policy).
4. **The matrix/gate-package is wrong, or a row cannot be done as specified** (a missed dependency, a split that proves unsafe) → escalate; do not improvise around it.
5. **Executing as written would breach a doctrine constraint** (§6) → STOP rather than breach.
6. **Spike #2 verdict is not a clear PASS** → STOP before Row 3.

Anything not on this list: handle it yourself, silently, and keep moving.

## 6. Doctrine constraints — a breach is a STOP, not a judgement call

Centre-origin at LEDs 79/80. No rainbow / full hue-wheel sweep. No heap allocation in render or render-transitive code. 120 FPS / 2.0 ms frame budget. dt-correct smoothing. Calibration commands are NEVER auto-fired — the silence window is Captain-only. Compile/upload is not runtime proof. Device port `/dev/tty.usbmodem1101` only — NEVER `usbmodem02` (S2, protected) — and per gate package §1.1 you never open it regardless.

## 7. Discipline

- **"Done" = committed AND gate-verified.** Never "tool ran" or "builds clean". A ✅ counts only against a committed, diffed, gate-passed artefact.
- Each row = its own commit(s); commit before moving on; never leave a load-bearing artefact uncommitted.
- Two same-type failures → STOP and state the mechanism (not "it didn't work").
- Label claims `[FACT]` / `[INFERENCE]` / `[HYPOTHESIS]`. Ground in the source docs; never relay a summary as fact.

## 8. Definition of done (end-to-end)

Closeout complete; Row 3, Row 4 and Row 2 all merged to `refactor/main`, each gate-PASS; working tree clean; everything committed and pushed to the GitHub backup. At that point the ratified refactor scope is complete. Rows 5/6/7 are deferred — do not touch them. The sandbox Phase C / fixed-point-parity work is a separate later lane — not in this scope.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | Sandbox/Refactor PM | Created. End-to-end execution handover for Rows 3/4/2 (closeout → Row 3 → Row 4 → Row 2). |
| 2026-05-25 | claude-code (Opus 4.7) + Captain Yeap | **Stage 0 amended (Captain ruling, Option B):** "Row 1 merged" struck from closeout — Row 1 is a gated row (its own hardware gate + delta sign-off), not a closeout step. `refactor/main` branched from freeze tag `refactor-baseline-2026-05-25` (seal `2e0e983`) **without** Row 1. §2 starting-state corrected: Row 1 + Spike #2 confirmed isolated on worktree branches, never integrated. Closeout verified complete (freeze tag created; governance committed; matrix Spike-#1 conditionals collapsed; backup remote `synqing/SpectraSynq-K1-Firmware-SB9-` configured + pushed). Rows 3/4/2 proceed continuously per ratified order. |
