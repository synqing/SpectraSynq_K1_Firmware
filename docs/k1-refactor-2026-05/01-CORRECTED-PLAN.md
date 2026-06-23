---
abstract: "SUPERSEDED 2026-05-25 by 02-SPLIT-JUSTIFICATION-MATRIX.md. Captain pivoted from 'split 7 monoliths' to 'split-justification matrix first; greenlit set = transitive closure of what passes Captain's 5-criterion × C-mandatory-AND-(A-OR-B) gate.' Net: ~2 splits + 1 command-layer extraction + conditionals, not 7 sub-phases. This document is retained as historical for its audit-corrections content (§1) and its Phase 0 spike/deliverable scoping (§4.2), both of which carry forward; the §5-§9 Phase 1+3+5 sub-phase structure is moot. §11/§14/§15 were mid-revision when the pivot arrived and do NOT reflect the gate-C Item-2 correction (native-compile spike is decision gate, not parallel investigation)."
---

> **⚠️ SUPERSEDED 2026-05-25 — DO NOT EXECUTE.**
>
> This plan was the gate-C submission. Captain reviewed it and ratified items 1, 3, 4, 5, 6, 7 (subject to listed checks) but rejected item 2 (gate model misread). I started revising for Item 2 — and Captain then issued a doctrinal pivot: apply Captain's own 5-criterion × C-mandatory-AND-(A-OR-B) gate to each proposed split before scheduling any of them.
>
> Net outcome of the pivot: the 7-sub-phase Phase 5 structure does not survive Captain's own gate. Likely greenlit set is ~2 splits (lightshow_modes + minimal globals partition as prerequisite) + 1 command-layer extraction (serial_menu dispatch) + 1 conditional (led_utilities partial extraction, gated on Spike #1 outcome). Total Phase 5 effort collapses from ~29-32d to ~10-18d. Most of `02-forensic-audit.md` through `07-phase-plan.md` is not worth writing in its original scope.
>
> **The active document is `02-SPLIT-JUSTIFICATION-MATRIX.md`.** Read it.
>
> Carried forward from this document: the audit-corrections mapping table (§1, except the rejected item 2 row), the open-items list (§2), the Phase 0 spike/deliverable scoping (§4.2 — 2 Spikes + 2 Deliverables), the WAVEFORM_FAST-as-only-intentional-VP-output-change framing (§5 Phase 1), and the doctrinal constraints (§0).

---

# K1 SensoryBridge Firmware Refactor — Corrected End-to-End Plan

| Field | Value |
|---|---|
| Plan date | 2026-05-25 |
| Plan author | Claude Code (Opus 4.7) with Captain Yeap |
| Status | **SUPERSEDED 2026-05-25 by `02-SPLIT-JUSTIFICATION-MATRIX.md`** per Captain's split-justification-gate pivot. Phase 5 7-sub-phase structure does not survive Captain's own 5-criterion × C-AND-(A-OR-B) gate. Likely greenlit set: ~2 splits + 1 extraction + conditionals (vs 7). |
| Baseline | `9423ea0833dc76998d2af4b2606bc18a73503cbe` on branch `feat/pio-core-bump` — `feat(serial): K1 serial hotkey layer with N/Y noise-cal arm/confirm gate` |
| Supersedes | `plan-draft-transient-cuddling-wirth.md` (draft input; structurally flawed per `docs/forensics/2026-05-24-refactor-plan-audit.md`) |
| Audit | `docs/forensics/2026-05-24-refactor-plan-audit.md` (3 blockers, 6 weaknesses; addressed in §1 below) |
| Captain rulings folded in | 2026-05-25 questioning round (Q1–Q4 + two riders) |

## 0. Status, framing, pre-read

This plan is the **Phase 0 deliverable** of the corrected sequence: it exists to be ratified by Captain so that Phase 1 (Freeze) can begin. It is NOT a programme that executes itself. Until Captain ratifies, no firmware change is permitted on `feat/pio-core-bump` other than what this plan itself prescribes for Phase 1 (the WAVEFORM_FAST fix, Phase 0 risk-reduction spikes, and the freeze-baseline capture).

**Read in this order:**

1. `docs/k1-refactor-2026-05/00-EXECUTION-HANDOVER-BRIEF.md` — operating contract, escalation rules, why this plan exists.
2. **This document** (`01-CORRECTED-PLAN.md`).
3. `docs/forensics/2026-05-24-refactor-plan-audit.md` — the audit. Findings are historical at commit `c872032`; §1 below maps each finding to its resolution in this plan.
4. `plan-draft-transient-cuddling-wirth.md` — draft input, structurally superseded. Useful only as a reference for what was tried.
5. Tier 2 design inputs in this directory (`phase1-source-survey-…`, `phase2-plan-agent-1/2/3`, `scoping-notes-…`) — useful as background but each carries audit-flagged claims; trust this plan over them on any conflict.

**Operating constraints in force throughout** (from `00-EXECUTION-HANDOVER-BRIEF.md §7` and `.claude/CLAUDE.md`):

- `/sensorybridge-doctrine` invoked before any non-trivial AP/VP/audio/visual/timing/multi-file change.
- Calibration command policy: agent never auto-fires `start_noise_cal`; Captain confirms verbal silence first. The `N`/`Y` hotkey is governed by the same rule.
- Hardware target discipline: serial capture, upload/flash, erase, and device-write actions are allowed when validation requires them, but the agent must verify the exact target by port plus stable hardware identity before interacting with the device.
- Root discipline: all work runs from `/Users/spectrasynq/SensoryBridge-main 9`. `LightwaveOS_Official` is read-only doctrine reference. Freeze Baseline + harness scripts live in **this** repo.
- Git discipline: branches, commits, and tags are rollback tools; use them after diff review and relevant tests/builds. Never commit untested or unreviewed work. Remote push, destructive history changes, and release tags require explicit Captain instruction or an active publication lane.
- Compile/upload is not runtime proof. The harness is the gate, not eyeball.
- Evidence labelling on every load-bearing claim: `[FACT]` / `[INFERENCE]` / `[HYPOTHESIS]`.

## 1. Audit corrections — mapping table

Each row in the audit's pre-ratification checklist (Blocker 1–3 + Weakness 4–9) is resolved here. Captain's 2026-05-25 rulings are referenced inline (Q1/Q2/Q3/Q4 + R1 reset-helper / R2 aggregate-init mini-spike).

| Audit item | Resolution in this plan |
|---|---|
| **Blocker 1 — equivalence claim unverified** | Equivalence is **NOT** treated as load-bearing for the refactor (per Captain Q4 ruling). The plan is canonical-agnostic and self-baselines at Freeze. Wording in §11 cites both `stage7-handoff.md` (K1 SSL=6092, mid-migration preliminary) and `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md` (K1 SSL=299, post-recal, Captain-ratified 2026-05-24 18:37 AWST) precisely, marks the silence-window hygiene check as the open item, and explicitly states the refactor does not depend on the resolution. "Within MEMS bias spec" is labelled as Captain's engineering judgment, not laundered as measurement. |
| **Blocker 2 — per-commit harness gating × Captain budget** | **Native-compile spike is the DECISION GATE** (Captain Q1 Option 1, ratified 2026-05-25; gate C revision). Phase 0 Spike #1 carries a binary pass criterion + agent-time timebox + pre-committed fallback. **Spike PASSES** → the native VP regression gate IS the per-commit VP gate (agent-executed, ~0 Captain-time, full per-commit bisection); hardware covers AP harness, sub-phase-boundary visual smoke, and agent-statically-flagged timing/integration-risk commits. **Spike FAILS** → per-sub-phase hardware gating for VP + per-commit static classification of VP-semantics commits to bound the bisect window. **Per-commit hardware gating throughout is neither branch** and is not what Q1 ratified; the prior version of this plan mis-attributed Option 3 to Q1 and is corrected here. **RESOLVED 2026-05-25 — Spike #1 = FAIL** (Class E vendored-FixedPoints in-class `static constexpr SFixed` non-literal is rejected by AppleClang 17 AND GCC-15; only lenient xtensa-gcc accepts it → a native compiler cannot be trusted as a compiler-equivalent gate; full record in `spike-1-native-compile-outcome.md`, Captain-ratified). **LOCKED MODEL: bounded-bisect hardware VP gating + per-commit static VP-semantics classification.** Native per-commit VP gate is abandoned. |
| **Blocker 3 — WAVEFORM_FAST fix vs Freeze ordering** | WAVEFORM_FAST fix is the **first commit of Phase 1, pre-freeze** — lands on `feat/pio-core-bump` before the freeze tag, so the Freeze Baseline encodes the *corrected* mode 7 behaviour. Captain visual smoke is the verification (no pre-fix harness to compare against). The Phase 4 "gotcha note" contradiction (plan said baseline was pre-fix in one place, post-fix in another) is now self-consistent. |
| **Weakness 4 — wrong mode count (13 not 9) baked into criteria** | Mode count: **13** distinct `light_mode_*` names (14 `void light_mode_*` grep hits; `bloom` has two overloads). Per Captain's cross-cutting finding, every "all modes" claim has been re-audited for hidden 9-mode scoping — not find-replaced. Acceptance criteria 10/11/20 re-parameterised explicitly. The vp_probe coverage decision (extend to 12 deterministic + 1 principled exception) is in Phase 0 deliverable §4. |
| **Weakness 5 — harness never proven to detect a real regression** | Added **deliberate-regression injection test** to Phase 4 (revert WAVEFORM_FAST fix on throwaway branch, confirm COM-slope gate returns FAIL). Plus Captain's R1 rider: probe each mode twice in succession in one run, assert bit-identical output for all 12 deterministic modes — proves the reset helper actually resets. |
| **Weakness 6 — Captain-time materially under-estimated** | Re-estimate in §14 as a **spike-conditional band**: Spike #1 PASSES → ~10-14 Captain hardware sessions total (~5-7 hours). Spike #1 FAILS → ~15-22 sessions (~7.5-11 hours). Plus ~1d doc review + ~3-4h Phase 2 ratification decisions. The draft's "~2d Captain-time" is abandoned; the prior version of this plan's "25-40 sessions / 12-20 hours" was the Option-3 cost envelope (not what Q1 ratified) and is also abandoned. Calendar figure (~10-12 weeks) is largely gate-model-independent. |
| **Weakness 7 — Phase 5a sequencing rationale doesn't hold** | Phase 5 reordered: **5c (system.h, 585 LOC) first as pattern-prover** (Captain Q2 ruling). Cheap pattern-prover proves basic strip+split mechanics on a recoverable module. Aggregate-init risk (which 5c does not exercise) handled by R2 mini-spike in Phase 0 before 5b. led_utilities follows once process is proven. |
| **Weakness 8 — no off-machine backup** | Phase 1 task list includes: (a) Captain chooses remote (GitHub private / GitLab private / separate bare repo on external media); (b) push baseline tag + `backup/pre-refactor-…` branch + `refactor/main` to remote; (c) ongoing push policy declared. **Captain decision point in Phase 1: which remote.** |
| **Weakness 9 — harness baseline in wrong repo** | **Freeze Baseline and harness scripts live in K1 repo.** New paths: `docs/refactor/baseline-envelope.json`, `docs/refactor/harness-baselines/freeze-9423ea0/`, `scripts/regression-harness/`. Committed and tagged with the freeze tag so firmware and gate are versioned together. No `LightwaveOS_Official` writes from this plan. |
| **Minor — envelope anchored to wrong commit** | Phase 1 measures envelope at `9423ea0` directly and writes it to `docs/refactor/baseline-envelope.json`. Acceptance criterion 7 reads "Flash within +1% of the Phase 1-measured 9423ea0 envelope" (the 552 622 B / 83 024 B figure from `2cbeea9` is no longer load-bearing). |
| **Minor — Phase 2 low-leverage per-command ratification** | Phase 2 task list now starts with **agent pre-classification** of all 186 serial commands (file:line evidence + proposed default of KEEP unless S2-hardware-specific or provably dead). Captain reviews only the contested subset and the strip candidates. Decision fatigue avoided. |
| **Source-count corrections** | Header count = 19 (not 11). `serial_menu.h` LOC = **2823** at baseline (was 2351 at c872032; +472 LOC from the hotkey layer commit). `strcmp` lines = 186 (not 141/125). `incandescent_lookup` defined in `constants.h:439` (not `led_utilities.h`). All Phase 5 sub-phase work re-anchored to these numbers. |

## 2. Open items (carried into refactor, not blockers for ratification)

These are items the corrected plan deliberately does NOT close — they are tracked for visibility, but the plan's correctness does not depend on their resolution.

1. **Equivalence silence-window hygiene check.** Captain-owned. Two resolution paths per Q4 ruling: (a) Captain confirms from memory the SSL=299 recal was performed under a confirmed silence window — claim resolves, CANONICAL_MILESTONES is canonical, plan can cite K1≈S2; (b) Captain re-runs noise cal under a confirmed silence window and confirms reproducibility — same outcome. Either way the refactor does not block on this; the harness self-baselines at Freeze.
2. **vp_probe coverage of `quantum_collapse`.** Mode 9 uses `random_float()` extensively + has persistent module-state arrays. Documented as principled-non-deterministic exception. Coverage is Tier B (energy/COM/FPS) + visual smoke — pending Captain R1's verification that Tier B metrics are themselves run-to-run stable for this mode. If Tier B wanders, mode 9 has zero automated coverage and that must be stated explicitly in the harness CANONICAL.md.
3. **"Within MEMS bias spec" provenance.** If Captain resolves item 1 in favour of CANONICAL_MILESTONES, the −19% delta needs either a citation of the SPH0645 datasheet sensitivity-tolerance figure, or a Captain-ratified label as engineering judgment. Not a measurement-laundered claim.
4. **5g constants.h aggregate-init verification.** Phase 0 Spike #2 proves the generic aggregate-init relocation pattern on `CONFIG_DEFAULTS`. 5g applies the proven pattern to `incandescent_lookup` and palette tables — **no second spike** (per Captain Item 4(a) ruling 2026-05-25: redundancy prohibited; no concrete structural difference vs `CONFIG_DEFAULTS` justifies a second spike). 5g step is "apply proven pattern + per-aggregate `objdump -s -j .rodata` byte-identity verification." If a per-aggregate verification fails, STOP and escalate; do not paper over with a per-case spike.
5. **TU-local static redistribution (5b post-acceptance).** Per §9 scoping, 5b is **pure-strip only** (definitions → `globals.cpp`, `extern` declarations stay in header). Redistribution of module-private globals to TU-local statics in their consuming `.cpp` is **deferred to a tracked post-acceptance optimisation pass** (per Captain Item 4(b) ruling 2026-05-25: "deferred work that is not on a list is abandoned work" — tracked here). Executed after the refactor satisfies the 22 acceptance criteria; out-of-scope for the corrected plan; not blocking on the gate-C ratification of this plan.

## 3. Strategic shape (unchanged)

**Freeze → Inventory → Strip(isolated) + WAVEFORM_FAST fix → Harness → Strip(cross-cutting) + Split.**

The shape was Captain-ratified in the prior planning round and survives the audit. What changes is *what each phase contains*, not the shape.

## 4. Phase 0 — Planning Artefacts + Risk-Reduction Spikes

**Goal:** produce a Captain-ratifiable artefact set AND complete the four risk-reduction spikes Captain prescribed before Freeze, so Phase 1 enters with maximum derisking.

**Effort:** ~6 days agent-time + ~1 day Captain-review time
**Branch:** all spike work on `feat/pio-core-bump` (the baseline branch — these are pre-Freeze additions). Doc work in `docs/k1-refactor-2026-05/`.
**Validation gate:** Captain reviews all deliverables + spike results in one ratification session.

### 4.1 Documents

1. **`02-forensic-audit.md`** — K1-fork source-verified audit at `9423ea0`. Per-file LOC (verified — see §1 corrections), inline-function count, global count, lookup-table count, header-monolith ranking, build-envelope baseline (measured at `9423ea0`), ODR/aggregate-init hazard inventory (separates `CONFIG_DEFAULTS` in `globals.h`, `incandescent_lookup`/palette tables in `constants.h`, `mode_names[]` in `globals.h`). 5-tier evidence taxonomy applied.

2. **`03-feature-inventory.md`** — Current-source-verified feature table. Columns: Feature, File:Line, Status (PRESENT-ACTIVE / PRESENT-GATED-OFF / ABSENT), Conflict (yes/no), Captain Decision (pending/KEEP/STRIP/DEFER), Strip-Class (Isolated / Cross-cutting / N/A), Phase (3 / 5 / DEFER). **Agent pre-classifies the 186 serial commands** with file:line evidence + default ruling (KEEP unless S2-hardware-specific or provably dead). Captain rules only the contested subset + strip candidates in Phase 2.

3. **`04-sweet-spot-investigation.md`** — Source-trace of SS as **two distinct components** (per Captain's prior clarification, now source-verified):
   - **SS AP algorithm** — `i2s_audio.h:254-315` runs SS calculations using `CONFIG.SWEET_SPOT_MIN_LEVEL`/`MAX_LEVEL`, updates `sweet_spot_state`/`follower`/`min_temp` regardless of LED presence. Default: KEEP-UNTOUCHED until Phase 5f when AP harness can re-validate any strip decision.
   - **SS LED output** — `led_utilities.h:run_sweet_spot()`, PWM writes, pin assignments in `constants.h:208-210` (gated by `SB_HAS_SWEET_SPOT_LEDS`). Default proposal: STRIP (vestigial on K1 — Captain confirmed no physical hardware). Captain ruling in Phase 2.

4. **`05-architectural-target.md`** — Post-refactor module decomposition, dependency DAG, header/source split rules, file organisation tree (`src/` proposed), globals strategy (**5b is pure strip per Captain's rider B**: definitions → `globals.cpp`, `extern` declarations remain in `globals.h`; redistribution to TU-local statics is out of scope for 5b — can be a separate optimisation post-acceptance), build-structure change (`k1_hardware` env unchanged; optional `native` env added if Phase 0 spike #1 succeeds), anti-patterns forbidden, current-file → new-module migration table. Acceptance criteria.

5. **`06-harness-spec.md`** — AP+VP equivalence harness design. **AP harness:** existing `dump_raw=silence`/`dump_raw=tone` + new `ap_stream=<ms>` envelope/spectrogram/chromagram capture. **VP harness Tier A:** wire extended `vp_probe_*` (12 of 13 deterministic modes; `quantum_collapse` documented exception) to `vp_probe=all`. **VP harness Tier B:** new `frame_dump=<metric>,<mode>,<dur>,<every_n>` for FNV hash + total energy + centre-of-mass spatial moment (transport-drift detector) + FPS streaming. Tolerance bands per metric per mode. **Reference data location:** `docs/refactor/harness-baselines/freeze-9423ea0/` (committed in K1 repo, not LightwaveOS). **Off-target diff scripts:** `scripts/regression-harness/` (also K1 repo).

6. **`07-phase-plan.md`** — This document (or a refined successor; this doc may be promoted to `07-phase-plan.md` after ratification).

### 4.2 Pre-Freeze risk-reduction work — two Spikes (decision-gated) + two Deliverables (must succeed)

Per Captain Item 5 ruling (2026-05-25), the four pre-Freeze items split by epistemic status. **Calling them all "spikes" leaves an undefined response to failure for the two that must not fail.** This reclassification fixes that.

- **Spikes (uncertain outcome, decision attached, agent-time timebox):** #1 native-compile, #2 aggregate-init. Each has a binary pass criterion AND a pre-committed response to failure.
- **Deliverables (defined output, must succeed, on the pre-Freeze commit path):** #3 vp_probe enumeration extension, #4 vp_probe reset helper. Failure = STOP and escalate; no proceed-with-caveat option.

#### Spike #1 — Native-compile feasibility (DECISION GATE for the VP gate model)

This is the spike whose outcome **locks the VP gate model for the entire refactor**. Per Captain Q1 Option 1 (ratified 2026-05-25, gate C revision).

- **Binary pass criterion:** (a) the vp_probe TU compiles under `[env:native_vp]` (shim only what `millis()`/`micros()`/FastLED palette helpers genuinely require); AND (b) at least one `light_mode_*` (recommend `light_mode_gdft` — pure spectrogram → CRGB, no inter-frame state, no static reset dependency yet) produces deterministic CRGB output from synthetic spectrogram input that matches a hardware-captured reference for the same input within Tier B tolerance.
- **Agent-time timebox:** 2 working days. If criterion not met within 2 days, declare FAIL and proceed to the fallback. No extensions without Captain authorisation.
- **Method:** add `[env:native_vp]` to root `platformio.ini` with `platform = native`; create shim headers for `Arduino.h`/`millis()`/`micros()`/FastLED palette types; build `vp_probe_seed_inputs` + `vp_probe_prepare_render` + `vp_probe_render_hash` for `light_mode_gdft`; run native and capture CRGB output; compare against hardware capture for same synthetic input.
- **PASS outcome → native VP regression gate becomes THE per-commit VP gate.** Agent-executed, ~0 Captain-time, full per-commit bisection across the entire refactor. Hardware covers: AP harness, sub-phase-boundary visual smoke, agent-statically-flagged timing/integration-risk commits. Spike #1 also enables coverage extension to remaining modes incrementally as needed.
- **FAIL outcome (pre-committed fallback) → bounded-bisect hardware VP gating.** Per-sub-phase hardware gating for VP AND per-commit static classification of VP-semantics commits (agent inspects each commit's diff for VP-semantic touches and flags those needing additional in-sub-phase hardware gating) to bound the bisect window. **Per-commit hardware gating throughout is NOT the fallback**; bounded-bisect is.
- **Recorded in:** `docs/k1-refactor-2026-05/spike-1-native-compile-outcome.md` with: pass/fail, shim list, build log, native↔hardware CRGB diff, and ratified VP gate model.

#### Spike #2 — Aggregate-init relocation (DECISION GATE for the 5b/5g pattern)

Per Captain rider R2, pulled ahead of 5b. Per Captain Item 4(a) ruling: this single spike proves the pattern; 5g APPLIES the proven pattern (no second spike, no concrete structural difference vs `CONFIG_DEFAULTS` to justify one).

- **Binary pass criterion:** `xtensa-esp32s3-elf-objdump -s -j .rodata` shows byte-identical bytes for `CONFIG_DEFAULTS` before vs after relocation; clean `pio run -e k1_hardware` build; no new symbols in `.bss`/`.data`; no static-init-order dependency surfaced (boot-trace inspection or `nm --print-armap` check).
- **Agent-time timebox:** 0.5 day.
- **Method:** on throwaway branch off `feat/pio-core-bump`, relocate `CONFIG_DEFAULTS` from `globals.h` to a new `globals.cpp`. Leave `extern conf CONFIG_DEFAULTS;` in `globals.h`. Build. Apply binary pass criterion.
- **PASS outcome:** 5b carries only blast-radius novelty (277 globals), not aggregate-init novelty. 5g applies the proven pattern to `incandescent_lookup` and palette tables with per-aggregate byte-identity verification (no second spike). Pattern also applies to `mode_names[]` in 5b (verify `.bss` byte identity since it's zero-initialised).
- **FAIL outcome:** STOP. Aggregate-init pattern is not yet understood. Resolution: enrich the pattern (explicit constructor-suppression, `constexpr` init alternatives, or per-aggregate analysis), then re-spike. 5b → 5g ordering may need revisiting if the aggregate-init pattern proves intrinsically unsafe.
- **Recorded in:** `docs/k1-refactor-2026-05/spike-2-aggregate-init-outcome.md`. Spike branch discarded; the actual 5b strip will redo the move on `refactor/phase5b-globals` after Freeze.

#### Deliverable #3 — vp_probe enumeration extension to 13 modes

Per Captain Q3 ruling. **Must succeed before Freeze** (pre-Freeze commit path).

- **Goal:** extend `vp_probe_print_mode()` enumeration to cover 13 modes (adding probes for `vu_dot`, `kaleidoscope`, `chromagram_gradient`, `quantum_collapse`).
- **Pass test:** build + flash; Captain runs `:vp_probe=all`; verify all 13 mode probes produce VPO serial output without error; the 12 deterministic modes produce reproducible hashes per Deliverable #4's pass test; `quantum_collapse` produces its expected non-deterministic hash but the probe exits cleanly.
- **Method:** edit `lightshow_modes.h:1873-1881` to add 4 `vp_probe_print_mode()` calls. Verify the enum-to-function mapping by source-walking `SPECTRASYNQ_K1_FIRMWARE.ino:67-115` dispatch (especially the `LIGHT_MODE_GDFT_CHROMAGRAM` vs `LIGHT_MODE_GDFT_CHROMAGRAM_GRADIENT` distinction). Verify `mode_names[]` carries names for the new entries.
- **Effort:** 0.5 day. **Gated on Deliverable #4** (extension is meaningless without reproducible probing).
- **Defined response to failure:** STOP. Most likely failure is enum→function mapping confusion. Resolve by source-walking dispatch; if a mode's constant doesn't dispatch to a `light_mode_*` function, that's a Captain-escalation item (potentially a runtime bug in the existing mode-dispatch).
- **Recorded in:** `docs/k1-refactor-2026-05/deliverable-3-vp-probe-extension-outcome.md`.

#### Deliverable #4 — vp_probe reset helper (Captain R1 — instruction, not discretion)

**Must succeed before Freeze.** Without this, multi-mode probing in a single run is not reproducible, the native gate (Spike #1) has no stable reference, and per-commit Tier A gating under either VP gate model is fictional. This is the load-bearing Phase 0 work.

- **Goal:** build `vp_probe_reset_mode_statics()` that resets every per-mode `static` variable in every `light_mode_*` function body so multi-mode probing is reproducible within a single run.
- **Pass test (Captain R1 condition):** probe each of the 12 deterministic modes twice in succession in one run; assert **bit-identical** Tier A hash output for all 12.
- **Method:**
  - **(a) Systematic grep:** `grep -nE '^\s+static\s+' SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h` to enumerate every static inside every `light_mode_*` body. **No hand-listing** — per Captain R1, a missed static is a silent reproducibility hole.
  - **(b) Strategy per static:** either (i) hoist to file scope and reset in the helper; or (ii) convert to parameter-passed state struct (matching the existing waveform-modes pattern in `vp_probe_prepare_render`). Default = hoist; (ii) only where the static is conceptually owned by a single call-site. Choice recorded per-static.
  - **(c) Invocation:** call `vp_probe_reset_mode_statics()` from `vp_probe_prepare_render()` between the existing waveform-state resets and the mode dispatch.
  - **(d) Verification:** apply pass test for all 12 deterministic modes.
  - **(e) Quantum_collapse Tier B stability check:** probe `quantum_collapse` twice (Tier B: energy/COM/FPS); record run-to-run delta. If delta exceeds a Captain-chosen Tier B tolerance, mode 9 has effectively zero automated coverage — the compensating control in §9 fires (mandatory Captain visual smoke for every commit touching mode 9 or its call-graph dependencies).
- **Effort:** 1-2 days.
- **Defined response to failure:** STOP. Resolution paths in priority order: (i) re-grep with looser regex (`static\s+\w+` with multiline; `static const`; etc.); (ii) restructure the failing mode's state into parameter-passed form; (iii) escalate to Captain — modes that cannot be made probe-reproducible become principled exceptions, joining `quantum_collapse` under the §9 compensating-control rule.
- **Recorded in:** `docs/k1-refactor-2026-05/deliverable-4-reset-helper-outcome.md`.

#### Sequencing

- Spike #2 standalone (anytime; ~0.5d).
- Spike #1 in parallel with Spike #2 (~2d timebox); its pass test is enabled by Deliverable #4 completing (the synthetic-input determinism check requires reset).
- **Deliverable #4 must complete before Deliverable #3** (extension is meaningless without reset).
- All four complete before Phase 0 ratification session.

#### Captain decision points (Phase 0, revised)

- **Spike #1 outcome → VP gate model locked** (native PASS or bounded-bisect hardware FAIL — no third option).
- **Spike #2 outcome → aggregate-init pattern viability for 5b/5g** (PASS = 5g uses proven pattern + per-aggregate verification; FAIL = re-spike or revisit ordering).
- **Deliverable #4 outcome → 12-mode Tier A coverage ratified; quantum_collapse Tier B stability assessment.** Captain reviews bit-identical-output evidence and Tier B run-to-run delta.
- **Deliverable #3 outcome → 13 mode probes responsive** (low-risk confirmation).

### 4.3 Phase 0 Captain decision points

- Approval of all six documents above.
- Spike #1 outcome → native gate yes/no/partial.
- Spike #4 outcome → if Tier A reset helper works for all 12 deterministic modes (Captain reviews bit-identical-output evidence).
- SS LED output STRIP / KEEP (default: STRIP per `04-sweet-spot-investigation.md`).
- SS AP algorithm KEEP-UNTOUCHED (default) / KEEP-WITH-LATER-REVIEW / STRIP.
- `PHOTONS_CURVE_MODE` ruling: keep `#ifdef` / hardwire to mode 2.
- Lightshow mode roster KEEP/STRIP per mode (after `02-forensic-audit.md` confirms 13).
- Music corpus: two pinned tracks (default) / no-music-MVP.
- Worktree topology: per-phase + per-sub-phase children (default) / single-worktree branch-only.

**Rollback:** discard all spike branches; doc files in `docs/k1-refactor-2026-05/` are doc-only. Zero firmware risk.

## 5. Phase 1 — Freeze

**Goal:** convert trunk into a refactor-only branch with immutable baselines, off-machine backup, and the worktree topology. The Freeze Baseline encodes the *corrected* mode-7 behaviour and the extended Tier A coverage.

**Effort:** ~2 days agent-time + 1-1.5 days Captain sessions (WAVEFORM_FAST visual smoke + freeze-baseline capture + remote setup decision)
**Entry criteria:** Phase 0 ratified by Captain (all six documents + Spikes #1/#2 outcomes + Deliverables #3/#4 outcomes).
**Validation gate:** clean build on `k1_hardware`; envelope measured and recorded; harness firmware additions present; freeze-baseline capture session complete; remote configured and tag/branch pushed.

**Baseline immutability framing (per Captain Item 3 check (a), 2026-05-25):** WAVEFORM_FAST (commit 1 below) is the **ONLY intentional VP-output change in the entire refactor.** Phase 3 strips affect SS GPIO outputs and serial command dispatch — not the WS2812 strip output that vp_probe/frame_dump capture. Phase 5 sub-phases are pure refactor (definitions move header→cpp, no semantic change; aggregate-init byte-identity verified per §9). Therefore: the Freeze Baseline captured AFTER commit 1 is **immutable** for the entire refactor. Post-Freeze gate semantics = **"any divergence from baseline = regression"** (Tier A: bit-identical hash for 12 deterministic modes; Tier B: within-tolerance for all 13 modes including quantum_collapse's principled exception). The versioned-baseline mechanism is not needed because there is only one intended VP change. **If during execution Captain authorises any additional intentional VP-output change, that change requires (i) explicit gate-C-style ratification and (ii) a new baseline capture session — it cannot be smuggled in as a "refactor commit".**

**Pre-freeze code changes** (land on `feat/pio-core-bump` IN THIS ORDER, each its own commit):

1. **WAVEFORM_FAST mode 7 frame-shift fix** at `lightshow_modes.h:1310-1312` — dt-scaled transport mirroring `light_mode_waveform_hybrid()` at `lightshow_modes.h:1457-1581`. **Intentional VP-output change**; Captain visual smoke required before commit (compare K1 mode 7 speed to S2 reference). Commit message: `fix(vp): correct WAVEFORM_FAST frame advance to match dt-scaled transport`. Per Blocker 3 resolution.
2. **vp_probe reset helper** (Deliverable #4) — `vp_probe_reset_mode_statics()` + invocation from `vp_probe_prepare_render()`. **Output-inert on render path** (helper is only invoked during probe execution via `vp_probe_prepare_render`, not from normal render dispatch). Required for reproducible probing.
3. **vp_probe enumeration extension** (Deliverable #3) — add 4 `vp_probe_print_mode()` calls. **Output-inert on render path** (extension only fires when `:vp_probe=all` is invoked).
4. **AP harness firmware additions** — `ap_stream=<ms>` command, gated behind `-DENABLE_AP_STREAM=1` build flag. **Output-inert on release build** (flag OFF → zero code path; flag ON → read-only audio internals capture, no AP state mutation).
5. **VP harness Tier B firmware additions** — `frame_dump=<metric>,<mode>,<dur>,<every_n>` command, gated behind `-DENABLE_FRAME_DUMP=1`. **Output-inert on release build** (flag OFF → zero code path; flag ON → read-only framebuffer capture, no render mutation).
6. **`vp_probe=all` serial command exposure** — gated behind `-DENABLE_VP_PROBE_CMD=1`. **Output-inert on release build** (flag OFF → no serial dispatch entry).
7. **`[env:native_vp]` addition to root `platformio.ini`** — **only if Spike #1 PASSES.** Optional env; default env remains `k1_hardware`. **Output-inert on `k1_hardware` build** (separate env, no shared compile units).

Each commit gets Captain visual smoke + (where applicable) Captain harness-flag-enabled smoke. Commits 2/3 must pass Deliverable #4's pass test (bit-identical probe-twice output for 12 deterministic modes). **The Freeze Baseline captured after commit 7 (or 6 if Spike #1 FAILS) is the immutable reference for the entire post-Freeze refactor.**

**Tasks (post-pre-freeze commits, in order):**

1. Capture **build envelope** at the post-pre-freeze HEAD: clean `pio run -e k1_hardware`, record flash bytes, RAM bytes, partition size, SHA, timestamp. Write `docs/refactor/baseline-envelope.json`. *This — not the `2cbeea9` figure — is the envelope reference for all subsequent phases.*
2. **Off-machine backup setup** (Captain decision point):
   - Captain chooses remote: GitHub private repo / GitLab private repo / bare repo on external media (USB / network mount).
   - `git remote add origin <chosen-url>`.
   - First push: current branch + all tags.
   - Ongoing policy declared in `docs/refactor/trunk-policy.md`: every named refactor branch and tag pushed to remote on update; the local-disk-only backup branch is **not** a sufficient floor.
3. **Tag baseline**: `git tag refactor-baseline-20260525 HEAD` (where HEAD is the post-pre-freeze commit). Push tag.
4. **Backup branch**: `git branch backup/pre-refactor-20260525 HEAD`. Push.
5. **Create `refactor/main`** from baseline tag. Push. Trunk policy added: `refactor/main` accepts no commits not bearing a `[refactor-phase-N]` prefix. `feat/pio-core-bump` archived as historical.
6. **Create worktrees** per Captain's Phase 0 topology decision: `git worktree add ../SB-refactor-phase2 refactor/phase2-inventory` (and similar for later phases as needed).
7. **Doctrine-gate re-test**: R5/R6/R7/R9/R11 with evidence-tier labels. Record at `docs/forensics/2026-05-25-freeze-gate.md`.
8. **Captain freeze-baseline capture session** (~45-60 min) — Captain runs:
   - Flash freeze build with harness flags enabled (`-DENABLE_AP_STREAM=1 -DENABLE_FRAME_DUMP=1 -DENABLE_VP_PROBE_CMD=1`).
   - `:start_noise_cal` under verbal silence (Captain confirms silence window).
   - AP capture: `:dump_raw=silence`, `:dump_raw=tone`, `:ap_stream=5000` × two music tracks.
   - VP capture: `:vp_probe=all` then `:frame_dump=all,<m>,5000,4` under confirmed silence only. **SUPERSEDED details:** current locked package is `03-hardware-gate-package.md`; roster is 12 modes, Tier A covers 11 deterministic modes, and tone/music are AP-only.
   - Captain hands log directory to agent.
9. **Agent processes baselines into canonical form**: parse logs, write per-metric JSON, store at `docs/refactor/harness-baselines/freeze-9423ea0/`. Files made read-only at filesystem level *and* committed + tagged with `refactor-baseline-20260525` so version control is the actual immutability mechanism. Write `docs/refactor/harness-baselines/freeze-9423ea0/CANONICAL.md` documenting the baseline (the visual+audio counterpart to The Equivalent Port).
10. **Re-confirm envelope** with harness flags OFF: `pio run -e k1_hardware` (no `-DENABLE_*` flags) → bytes should match step 1. If they don't, the harness leaked into hot path — STOP, investigate.
11. **Doctrine R5/R6/R7/R9/R11 re-test** and freeze-gate forensic at `docs/forensics/2026-05-25-freeze-gate.md`.
12. Announce freeze in Captain's log. No feature development on `refactor/main` except critical hardening (build break / doctrine-gate regression / hardware safety).

**Outputs:** WAVEFORM_FAST fix committed; vp_probe reset helper + 13-mode extension committed; harness firmware additions committed; `refactor-baseline-20260525` tag (pushed); `backup/pre-refactor-20260525` branch (pushed); `refactor/main` branch (pushed); `baseline-envelope.json`; freeze-gate forensic; worktrees; canonical Freeze Baseline (committed + tagged + filesystem-read-only); off-machine remote configured.

**Rollback:** `git reset --hard refactor-baseline-20260525`; or check out `backup/pre-refactor-20260525`. Remote provides the off-machine floor.

**Pre-empted gotchas:** PIO build cache is per-worktree (`.pio/` not shared, already in `.gitignore`). Harness flags must default OFF in release build envelope check. Calibration policy: `:start_noise_cal` only on Captain's verbal silence confirmation. The `N`/`Y` hotkey sequence is the same policy.

## 6. Phase 2 — Inventory Ratification

**Goal:** convert Phase 0's draft inventory into a committed, source-line-accurate, Captain-signed KEEP/STRIP/DEFER classification — with the agent doing the per-item pre-classification so Captain ratifies bundles, not individual rows.

**Effort:** ~2.5 days agent-time + ~3-4 hours Captain ratification (across one or two sessions)
**Entry criteria:** Phase 1 complete.
**Validation gate:** doc-only phase — no build gate. Verify every file:line reference resolves at `refactor-baseline-20260525`.

**Tasks:**

1. Re-verify every PRESENT row in `03-feature-inventory.md` against `refactor-baseline-20260525`. Catch any drift since Phase 0.
2. Add columns: `Strip-Class`, `Phase` (3 / 5 / DEFER), `Captain-Signature` (date).
3. Tabulate every `#ifdef`, `#if SB_HAS_*`, and dead branch in `encoders.h`, `serial_menu.h`, `led_utilities.h`, `globals.h`.
4. **Agent pre-classifies all 186 serial commands** with file:line + default ruling. Output: `docs/refactor/serial-commands-preclassified.md` with three buckets: KEEP-by-default (uncontested debug/diag/safe), STRIP-candidate (S2-hardware-specific or provably dead), CONTESTED (needs Captain rule).
5. Captain reviews the STRIP-candidate and CONTESTED buckets only. Bulk KEEP-by-default → accept-all-unless-objected.
6. Captain rules on SS LED output per Phase 0 `04-sweet-spot-investigation.md`.
7. Captain rules on SS AP algorithm (default: KEEP-UNTOUCHED).
8. Captain rules on `PHOTONS_CURVE_MODE`.
9. Captain rules on lightshow mode roster per Phase 0 audit (13 modes).
10. Commit `docs/refactor/inventory-ratified.md` on `refactor/phase2-inventory`; merge to `refactor/main` (doc-only).

**Outputs:** ratified inventory with Captain signatures; per-domain serial-command ratification; SS-LED ruling; SS AP ruling; `PHOTONS_CURVE_MODE` ruling; lightshow mode roster.

**Rollback:** revert doc-only merge.

## 7. Phase 3 — Strip-Isolated

**Goal:** delete clearly-isolated dead code with zero cross-cutting risk. (The WAVEFORM_FAST fix has already shipped in Phase 1, so Phase 3 is purely strips.)

**Effort:** ~3-4 days agent-time + Captain sign-off per commit group
**Entry criteria:** Phase 2 ratification merged.
**Validation gate (spike-conditional per Spike #1):** clean build; flash and RAM both **strictly decrease or stay equal** vs Phase 1 envelope; doctrine R5 green; **VP harness gate PASS vs Freeze Baseline** (Spike #1 PASS → agent-run native VP per commit; Spike #1 FAIL → bounded-bisect hardware VP per commit group, with agent flagging any VP-semantics commits for additional hardware gate); **AP harness gate PASS vs Freeze Baseline** (Captain hardware capture, batched per commit group); Captain visual smoke per commit group.

**Tasks (each its own commit; gate model follows Spike #1 outcome):**

1. Strip M5ROTATE8 / encoder dead branches in `encoders.h` (gated `SB_HAS_ROTATE8=0`).
2. Strip SS LED output code **only if Phase 2 ruled STRIP**. SS AP algorithm UNTOUCHED. The harness must show no AP-side regression — if it does, Phase 0 SS investigation was wrong about LED-vs-AP independence; STOP and revisit.
3. Strip ratified-STRIP serial commands. One commit per logical group (S2-hardware-UI commands, dead-code commands, etc.).
4. Remove `#ifdef` scaffolding that becomes unconditional after Phase 3 strips.
5. Doctrine R5 re-test; capture forensic at `docs/forensics/2026-05-26-phase3-strip.md`.
6. Update `docs/refactor/baseline-envelope.json` with post-Phase-3 envelope (allowed direction: flash ↓, RAM ↓ or =).
7. Merge `refactor/phase3-strip-isolated` → `refactor/main` only after Captain signs off.

**Outputs:** stripped source; per-strip commit chain; updated envelope; Phase-3 forensic; per-commit harness PASS evidence.

**Rollback:** per-commit `git revert`; or reset branch to `refactor-baseline-20260525`. Backup branch remains the floor.

## 8. Phase 4 — Harness Hardening

**Goal:** build off-target diff infrastructure; prove the harness actually detects a regression; document gate procedure; seal harness as load-bearing canon.

**Effort:** ~2-3 days agent-time + 1 Captain hardening session
**Entry criteria:** Phase 3 merged.
**Validation gate:** self-check PASS; **deliberate-regression injection test FAIL** (per Weakness 5 resolution — proves the harness is a detector); harness flags-disabled envelope byte-identical to Phase 3.

**Tasks:**

1. Build `scripts/regression-harness/` in K1 repo:
   - `ap_diff.py` — AP capture comparison vs baseline.
   - `vp_diff.py` — VP comparison (Tier A hash + Tier B energy/COM-slope/FPS).
   - `parse_serial.py` — shared tagged-block parser.
   - `run_diff.sh` — orchestrator. Exit code 0 = PASS for all metrics.
   - `README.md` — gate procedure.
2. Run `--self-check` on each script (baseline-vs-baseline → all PASS).
3. **Deliberate-regression injection test** (Weakness 5): on throwaway branch off `refactor/main`, revert the WAVEFORM_FAST fix (now at the start of Phase 1). Captain captures Tier B for mode 7. Run `vp_diff.py` against Freeze Baseline. **Expected result: FAIL** on COM-slope metric for mode 7. Outcome recorded in `docs/forensics/2026-05-27-harness-detector-validation.md`. Throwaway branch discarded.
4. Confirm `k1_hardware` env envelope **byte-identical** to Phase 3 with harness flags disabled. If not — harness leaked. STOP, investigate, fix.
5. **Post-Phase-3 re-capture under harness**: Captain re-runs freeze-baseline capture sequence on post-Phase-3 build with harness flags ON. Agent diffs vs Freeze Baseline. PASS within tolerance bands. Validates that Phase 3 strips did not regress AP/VP equivalence.
6. Document harness invocation in `docs/refactor/harness-runbook.md`. Update `docs/refactor/harness-baselines/freeze-9423ea0/CANONICAL.md`.
7. **Canonise "The Freeze Baseline"** as a load-bearing artefact in `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md` (sibling to The Equivalent Port).
8. Doctrine R5/R7 re-test confirms production envelope unchanged.
9. Merge `refactor/phase4-harness` → `refactor/main`.

**Outputs:** off-target diff scripts (in K1 repo); harness self-check evidence; deliberate-regression detector evidence; harness runbook; canonised Freeze Baseline.

**Rollback:** revert harness script additions (additive — revert clean). Harness firmware additions remain (Phase 1).

## 9. Phase 5 — Strip-Cross-Cutting + Split

**Goal:** the dangerous work. Per-module: strip cross-cutting dead code, then split header monolith into `.h` + `.cpp`. **Harness gates spike-conditional** (per Spike #1 outcome). Aggregate-init preservation enforced (Spike #2 proven pattern applied; per-aggregate byte-identity verification).

**Effort:** ~29-32 days agent-time across 7 sub-phases. Captain hardware-session load is spike-conditional — see §14.
**Entry criteria:** Phase 4 harness sealed.
**Validation gate (spike-conditional per Spike #1):**
- **Spike #1 PASS** → per-commit native VP gate (agent-run, ~0 Captain-time): Tier A hash-match for 12 deterministic modes + Tier B for `quantum_collapse`. Hardware gate at each sub-phase boundary (Captain hardware capture, full AP + VP + visual smoke). Per-commit hardware gate only on agent-flagged timing/integration-risk commits.
- **Spike #1 FAIL** → bounded-bisect hardware gate: per-sub-phase hardware capture (Captain) AND per-commit static classification of VP-semantics commits (agent flags any commit whose diff touches `light_mode_*` bodies, `render/`, `color/`, or shared `vp_*` state); flagged commits get additional in-sub-phase hardware gate to keep bisect window small.
- **Either branch:** envelope monotonic non-regression vs sub-phase start; aggregate-init `objdump -s -j .rodata` byte-identity per moved aggregate (applies in 5b for `CONFIG_DEFAULTS`/`mode_names[]`, in 5g for `incandescent_lookup`/palette tables, anywhere else the Phase 0 audit identifies).

**Sub-phase ordering (Captain Q2 ruling — 5c first as pattern-prover; tail order rationale below):**

- **5c — `system.h`** (585 LOC, 17 inline funcs, 76 globals) → splits into `system/boot.{h,cpp}`, `system/runtime.{h,cpp}`. **Pattern-prover** for basic strip+split mechanics and the per-commit gate. Static-init order map captured here (caught the migration's `clk_rate=12800` bug). **3 days.**
- **5b — `globals.h`** (684 LOC, 277 globals, 9 inline funcs, `CONFIG_DEFAULTS` aggregate, `mode_names[]` aggregate) → **pure-strip** (Captain Q2 rider B): all definitions → `globals.cpp`, all inline function bodies → `globals.cpp`, `extern` declarations + prototypes stay in `globals.h`. **No API change in this sub-phase.** Aggregate-init risk covered by Phase 0 Spike #2 + `objdump -s -j .rodata` byte-identity verification on `CONFIG_DEFAULTS` move. **5 days.** *(Optional redistribution of globals to TU-local statics is OUT of scope here; deferred to a separate post-acceptance optimisation pass.)*
- **5a — `led_utilities.h`** (2045 LOC, 52 inline funcs) → splits into `color/pipeline.{h,cpp}`, `render/pipeline.{h,cpp}`, `render/sweet_spot.{h,cpp}`. Consumes (but doesn't define) `incandescent_lookup`. **6 days.**
- **5d — `serial_menu.h`** (2823 LOC, 186 strcmp dispatch arms, hotkey layer; mechanical, no inline funcs) → splits into `ui/serial/dispatch.{h,cpp}`, `ui/serial/hotkey.{h,cpp}`, + 6 `commands_*.cpp` files (audio, render, config, vp, debug, diag). Strcmp chain replaced with static dispatch table. **5 days.**
- **5e — `lightshow_modes.h`** (1910 LOC, 13 modes + `vp_probe_*` machinery) → splits into `render/modes/*.cpp` (one TU per mode; 14 files since `bloom` has two overloads — Phase 5e decides whether to disambiguate by name or by keeping the overload pair in one file) + `debug/probes.{h,cpp}`. **4 days.**
- **5f — `i2s_audio.h` + `GDFT.h` + `audio_transfer.h`** → splits into `audio/capture.{h,cpp}`, `audio/analysis.{h,cpp}`, `audio/dump_raw.{h,cpp}`, possibly `audio/transfer.{h,cpp}`. **SS AP algorithm at `i2s_audio.h:254-315` travels intact** per Phase 0 investigation. **4 days.**
- **5g — Remainder + final acceptance**: `constants.h` → `platform/hardware_constants.h` + `platform/types.h` (carries `incandescent_lookup` + palette aggregate-init — **apply pattern proven in Phase 0 Spike #2 with per-aggregate `objdump -s -j .rodata` byte-identity verification**; no second spike per Captain Item 4(a) and Open Item #4); `bridge_fs.h` → `config/persistence.{h,cpp}`; `Palettes.h` → `color/palettes.{h,cpp}` (palette tables: array-of-struct aggregate-init, same proven pattern applied + verification); `knobs.h` + `buttons.h` → `system/input.{h,cpp}`; rename `.ino` → `main.cpp`; switch `build_src_filter` to `+<**/*.cpp>`; final acceptance verification. **4 days.**

**Dependency rationale for the 5c → 5b → 5a → 5d → 5e → 5f → 5g tail (Captain Item 4 check):**

- **5c → 5b**: pattern-prover (5c, 585 LOC) before foundation (5b, 277 globals + aggregate-init). Captain Q2 ratified.
- **5b → 5a**: globals split into `globals.cpp` (extern declarations in `globals.h` preserved) before consuming modules. After 5b, every later sub-phase references stable extern declarations; before 5b, splits would either duplicate global definitions or require ABI churn.
- **5a → 5d**: `serial_menu`'s 186 strcmp arms dispatch into many `render/color/sweet_spot` functions. Splitting `led_utilities` first means serial-dispatch targets live in known modules before the dispatch table is restructured.
- **5d → 5e**: dispatch-table reorganisation completed before per-mode TU explosion. (Alternatively 5e first would mean revising mode dispatch from the still-monolithic dispatcher; ordering this way means fewer cross-cutting edits.)
- **5e → 5f**: lightshow modes split (consumers of audio analysis outputs) before audio split. *Pure-strip discipline says splitting `i2s_audio.h` later doesn't change its interface — 5e built against header-monolithic audio still compiles after 5f relocates definitions. The reverse ordering would mean 5f's split happens while consumers (lightshow_modes) are still header-monolithic and reference audio internals freely, which is also workable but harder to verify cleanly.*
- **5f → 5g**: audio split before final keystone (constants/palettes/persistence/input/main rename + `build_src_filter` switch). 5g is the smallest changeset but the most architecturally final; ordering it last means everything else is already stable when the TU model flips.

**Quantum_collapse compensating control (Captain Item 6 addition, 2026-05-25):** If Deliverable #4's quantum_collapse Tier B stability check returns "unstable" (run-to-run delta exceeds tolerance), mode 9 has effectively zero automated coverage. Stating that in `CANONICAL.md` is necessary but **not sufficient**. Compensating rule: **every commit touching `quantum_collapse`'s code body OR any shared dependency in its call graph** — specifically `random_float()`, the `SQ15x16 wave_probabilities[]`/`fluid_velocity[]`/`temp_field[]`/`temp_fluid[]` arrays, `animation_phase`/`wave_phase` statics, and any audio input it reads (`bass_energy`/`mid_energy`/`high_energy`/`audio_vu_level`) — **gets mandatory Captain visual smoke** regardless of native gate verdict. Agent flags such commits during the static classification step (applicable under both VP gate model branches). Without this rule, mode 9 can silently regress for the entire refactor.

**Tasks per sub-phase (5c as template; pattern transfers):**

1. Spawn child worktree on `refactor/phase5<x>-<module>`.
2. Strip cross-cutting first: remove dead `#ifdef`s, dead branches, ratified-STRIP cross-cutting globals for this module. One commit. Per-commit harness gate.
3. Extend `build_src_filter` to include the new `.cpp` for this module (first dual-TU commit per module).
4. Split function bodies header → cpp: move each definition; leave prototypes in header. Commit in batches of 5-10. **Per-commit harness gate per batch.**
5. **Aggregate-initialiser discipline** (load-bearing, applies to 5b, 5e, 5g): preserve byte-identical initialiser syntax. No explicit type constructors. Verify each move via `xtensa-esp32s3-elf-objdump -s -j .rodata` diff. *5b and 5g start with a sub-phase-specific mini-spike on the aggregate move.*
6. **Globals migration (5b only, pure-strip)**: move definitions to `globals.cpp`; preserve `extern` declarations in `globals.h`. Capture init-order map.
7. Per-commit harness gate. Any AP/VP delta outside tolerance: STOP, investigate, revert if root cause not found in 30 min.
8. R5 doctrine trigger re-test at end of each sub-phase.
9. Merge sub-phase to `refactor/main` only after envelope check + full harness gate PASS + Captain sign-off.
10. Next sub-phase rebases on updated `refactor/main`.

**Outputs per sub-phase:** dual-TU build incrementally extended; per-module `.h`+`.cpp` pair; per-module forensic with envelope delta + harness diff; sub-phase merge commit on `refactor/main`.

**Rollback:** per-sub-phase revert merge commit; or reset to `refactor-phase5-start` tag (applied before 5c begins). Backup branch + remote remain the ultimate floor.

**Pre-empted gotchas:** aggregate-init regression (mitigated by byte-identical syntax rule + objdump diff + VP harness frame-hash gate + Phase 0 + 5g mini-spikes); static-init order (mitigated by init-order map captured in 5b, no file-scope objects whose constructors read CONFIG); ODR violations (mitigated by removing header body in same commit that adds cpp body); VP drift like WAVEFORM_FAST (mitigated by per-commit Tier B COM-slope gate); build envelope drift (per-commit monotonic non-regression rule); serial-port discipline; `start_noise_cal` discipline.

## 10. Architectural target (one-paragraph; full spec in Phase 0 `05-architectural-target.md`)

Post-refactor codebase: `main.cpp` (thinnest possible setup/loop) + `platform/` (hardware_constants, types, fixed_math — leaf) + `core/state.{h,cpp}` (or `globals.{h,cpp}` after 5b's pure strip — naming decided in `05-architectural-target.md`) + `config/` (CONFIG + persistence) + `audio/` (capture, analysis, noise_cal, dump_raw) + `color/` (pipeline, palettes) + `render/` (pipeline + modes/, one TU per mode where practical, 13 modes → 13-14 files) + `system/` (boot, runtime, input) + `peripherals/encoders.{h,cpp}` (stub if disabled) + `ui/serial/` (dispatch + hotkey + 6 commands_*.cpp) + `debug/` (vp_perf, probes). Dependency direction: platform → core → config → audio → color → render → system → peripherals → ui. Headers contain declarations only; aggregate-init syntax preserved byte-identical during moves. `build_src_filter` switches from `+<*.ino> +<*.ino.cpp>` to `+<**/*.cpp>` in 5g. Optional `native_vp` env (if Spike #1 succeeded) for agent-run VP probing.

## 11. Equivalence harness (one-paragraph; full spec in Phase 0 `06-harness-spec.md`)

Two-tier harness gating every Phase 3 + Phase 5 commit (per Captain Q1 — per-commit hardware gating). **Equivalence framing:** the harness self-baselines at the Freeze commit (`refactor-baseline-20260525` at `9423ea0` post-pre-freeze-commits) and does **not** depend on K1↔S2 equivalence. The K1↔S2 question is recorded distinctly: `docs/forensics/2026-05-24-stage7-handoff.md` (mid-migration, self-described preliminary) records K1 SSL=6092 vs S2=369; `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md` (post-recal, Captain-ratified 2026-05-24 18:37 AWST) records K1 SSL=299 vs S2=369. The later figure supersedes the earlier *if* the recal was performed under a confirmed silence window — that hygiene check is the open item (Open Item #1). The refactor proceeds regardless. **AP harness:** existing `dump_raw=silence`/`dump_raw=tone` + structured `ap_capture=<ms>` envelope/spectrogram/chromagram streaming. AP stimuli are confirmed silence for `dump_raw=silence`, `tone-1k` for `dump_raw=tone` + tone `ap_capture`, and two Captain-pinned music tracks for music `ap_capture`. **VP harness Tier A:** extended `vp_probe_*` machinery covering the locked 12-mode roster with 11 deterministic modes via `vp_probe=all` + reset-helper-guaranteed within-run reproducibility. `quantum_collapse` (mode 6) is documented exception — non-deterministic by design (`random_float()` + persistent state arrays); coverage via silence-only Tier B + visual smoke. **VP harness Tier B:** `frame_dump=<metric>,<mode>,<dur>,<every_n>` under confirmed silence only for FNV hash + total energy + centre-of-mass + FPS. Per-frame cost when streaming ~100 µs; per-frame cost when disabled = zero (`#if ENABLE_*` flags). Captain captures via serial monitor → log file → agent runs off-target Python diff scripts; PASS/FAIL per metric per mode against Freeze Baseline tolerance bands. **Reference data lives in K1 repo at `docs/refactor/harness-baselines/freeze-9423ea0/`; scripts at `scripts/regression-harness/`.**

## 12. Critical files

**Plan artefact home:** `docs/k1-refactor-2026-05/` (this directory; Phase 0 outputs land here).

**New paths created during execution (K1 repo, NOT LightwaveOS):**
- `docs/refactor/baseline-envelope.json` (Phase 1)
- `docs/refactor/trunk-policy.md` (Phase 1)
- `docs/refactor/harness-baselines/freeze-9423ea0/` (Phase 1; canonical, version-controlled, tagged)
- `docs/refactor/harness-runbook.md` (Phase 4)
- `docs/refactor/serial-commands-preclassified.md` (Phase 2 agent draft)
- `docs/refactor/inventory-ratified.md` (Phase 2 Captain-signed)
- `scripts/regression-harness/` (Phase 4)

**K1 fork files modified during execution:**

| File | Modified in | Why |
|---|---|---|
| `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h` | Phase 1 (WAVEFORM_FAST fix + vp_probe reset helper + 13-mode extension); Phase 5e (split) | mode 7 fix; harness; final TU-per-mode split |
| `SPECTRASYNQ_K1_FIRMWARE/i2s_audio.h` | Phase 1 (ap_stream additions); Phase 5f (split, SS AP algorithm travels intact) | harness; final split |
| `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h` | Phase 1 (vp_probe=all, frame_dump, ap_stream commands); Phase 5d (split) | harness; final 186→dispatch-table split |
| `SPECTRASYNQ_K1_FIRMWARE/encoders.h` | Phase 3 (dead-branch strip); Phase 5g (final stub/delete) | strip; final |
| `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h` | Phase 3 (SS LED if ruled STRIP); Phase 5a (split) | strip; biggest monolith split |
| `SPECTRASYNQ_K1_FIRMWARE/globals.h` | Phase 5b (pure strip: definitions → globals.cpp) | foundation split |
| `SPECTRASYNQ_K1_FIRMWARE/system.h` | Phase 5c (split — pattern-prover) | static-init-order safety |
| `SPECTRASYNQ_K1_FIRMWARE/GDFT.h` | Phase 5f | audio analysis split |
| `SPECTRASYNQ_K1_FIRMWARE/audio_transfer.h` | Phase 5f (review for dead-file status per stage7 #2) | possible cleanup |
| `SPECTRASYNQ_K1_FIRMWARE/constants.h` | Phase 5g (with start-of-5g aggregate-init mini-spike on `incandescent_lookup`) | hardware constants + final aggregate-init class |
| `SPECTRASYNQ_K1_FIRMWARE/Palettes.h` | Phase 5g (palette table aggregates) | color split |
| `SPECTRASYNQ_K1_FIRMWARE/bridge_fs.h` | Phase 5g | persistence split |
| `SPECTRASYNQ_K1_FIRMWARE/knobs.h` + `buttons.h` | Phase 5g | input split |
| `SPECTRASYNQ_K1_FIRMWARE.ino` | Phase 5g (rename → `main.cpp`) | TU model switch |
| `platformio.ini` | Phase 1 (optional `[env:native_vp]`); Phase 5g (`build_src_filter` switch) | build infrastructure |

**Existing reference artefacts (read-only):**
- `LightwaveOS_Official/docs/agent-outputs/analysis/sensory-bridge-lessons-doctrine.md` — 12 rules invoked at every phase gate.
- `docs/forensics/2026-05-24-stage7-handoff.md` — preliminary AP signature record (see Open Item #1).
- `docs/forensics/2026-05-24-k1-waveform-fast-speed-investigation.md` — anchor for Phase 1 WAVEFORM_FAST fix.
- `docs/hardware/k1-hardware-definition.md` — hardware truth; anchor for SS LED vestigiality ruling.
- `.claude/CLAUDE.md` — K1 fork doctrine bridge.
- `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md` — registry; receives "The Freeze Baseline" entry at Phase 4, *after* Open Item #1 is resolved or the canonisation language is explicitly conditional.

## 13. Acceptance criteria — refactor complete

Each independently verifiable. All must hold for refactor to be declared done.

### Structural
1. `grep -l "^[a-zA-Z_].*(.*) *{$" SPECTRASYNQ_K1_FIRMWARE/**/*.h | wc -l` = 0 (no function bodies in headers, modulo ≤ 5-line `inline` exceptions).
2. No global variable definitions in headers (only `extern` declarations).
3. `SPECTRASYNQ_K1_FIRMWARE.ino` no longer exists; `main.cpp` exists and is ≤ 120 LOC.
4. Dependency graph has zero cycles (verified by `compile_commands.json` analysis).
5. Soft size targets (deviations require justification comment): no `.cpp` > 500 LOC; no `.h` > 200 LOC.

### Build
6. `pio run -e k1_hardware` builds clean with same warning count or fewer.
7. Flash within +1% of the Phase 1-measured `9423ea0` envelope; RAM within +2% of same.
8. `compile_commands.json` regenerates cleanly via `pio run -t compiledb`.

### Behavioural equivalence (harness-verified against Freeze Baseline)
9. AP harness PASS for silence, 1 kHz tone, and both music tracks.
10. **VP Tier A: hash-exact match for all 12 deterministic modes** (the roster ratified in Phase 0 — see Spike #3 outcome and `02-forensic-audit.md` for the 13→12 enumeration; the unenumerated mode is `quantum_collapse`).
11. **VP Tier B: energy within tolerance, COM-slope within ±10%, FPS within ±5%** for the locked 12-mode roster under confirmed silence only. (`quantum_collapse` Tier B tolerance widened if run-to-run wander observed.)
12. `dump_raw` produces byte-identical output for the same I2S input as Freeze Baseline.
13. WAVEFORM_FAST mode 7 visual smoke: Captain confirms speed matches S2 reference (re-confirmation; the fix shipped in Phase 1).

### Surface preservation
14. All ratified-KEEP serial commands respond. Regression script fires each command and checks for non-`bad_command` response — 100% pass.
15. SS AP algorithm behaviour preserved (or its strip explicitly approved by Captain + harness-validated post-strip).
16. DC_OFFSET 2-layer guard (Fix-D) preserved with unit-testable interface.

### Discipline
17. VP_PERF_AUDIT instrumentation: when `ENABLE_VP_PERF_AUDIT=0`, resulting binary has zero `vp_perf_*` symbols (`nm` verification).
18. **Every moved aggregate-initialised table is byte-identical pre/post in `.rodata`** (`objdump -s -j .rodata` diff). Explicit list: `CONFIG_DEFAULTS` (5b), `incandescent_lookup` (5g), palette tables (5g), `mode_names[]` (5b), and any other aggregate the Phase 0 audit identifies.
19. Build flag policy documented in `.claude/CLAUDE.md`; existing flags preserved.

### Future-fitness (aspirational)
20. Adding a new lightshow mode = creating one new `.cpp` in `render/modes/`, adding one declaration, adding one enum value. Zero edits to existing mode code.
21. Adding a new serial command = adding one function + one registrar line. Zero edits to dispatch.
22. A fresh Claude session can answer "where does HSV→RGB conversion happen?" by reading the tree in under 30 seconds, without grep.

## 14. Effort estimate (honest — Captain Weakness 6 ruling)

| Phase | Agent days | Captain time | Notes |
|---|---|---|---|
| 0 — Plan + 4 spikes | 6 | ~1d review | 6 documents + spike #1 native (1-2d) + spike #2 agg-init (0.5d) + spike #3 vp_probe extend (0.5d) + spike #4 reset helper (1-2d). Most spike work parallel. |
| 1 — Freeze (WAVEFORM_FAST fix → pre-freeze commits → tag → backup → remote → capture) | 2 | 1-1.5d | Captain WAVEFORM_FAST visual smoke + freeze-baseline capture (~60 min) + remote-choice decision |
| 2 — Inventory ratification | 2.5 | ~3-4 hours | Agent pre-classifies 186 commands; Captain rules contested + STRIP subset only |
| 3 — Strip-isolated (per-commit hardware gate) | 3-4 | ~3-5 hardware sessions @ ~30-40 min each | Per-commit gate per Q1 |
| 4 — Harness hardening + detector test | 2-3 | 1 hardware session | Deliberate-regression injection + post-Phase-3 re-capture |
| 5c — system.h (pattern-prover) | 3 | ~3-5 sessions | First Phase 5 sub-phase |
| 5b — globals.h pure strip | 5 | ~5-7 sessions | Per-commit Captain hardware gate per batch (5-10 funcs/batch) |
| 5a — led_utilities.h | 6 | ~6-8 sessions | Worst monolith — pattern is proven by 5c+5b |
| 5d — serial_menu.h | 5 | ~5-7 sessions | 186 commands → dispatch table |
| 5e — lightshow_modes.h | 4 | ~4-6 sessions | 13 modes → 13-14 TUs |
| 5f — audio (i2s + GDFT + transfer) | 4 | ~4-6 sessions | SS AP algorithm travels intact |
| 5g — remainder + final acceptance (incl. 5g aggregate-init mini-spike) | 4 | ~3-5 sessions | constants.h aggregate-init class first encounter |
| **Total** | **~46-50 days agent-time** | **~25-40 Captain hardware sessions (~12-20 hours) + ~1.5d documentation review + ~3-4h ratification decisions** | **~10-12 weeks calendar at sustainable Captain-session pace** |

The dominant risk reservoirs: **Spike #4** (reset helper — if a missed static is later discovered, harness reproducibility breaks silently), **Phase 5a** (worst monolith, even with 5c+5b proving the pattern), **Phase 5g** (second aggregate-init class via `incandescent_lookup` + palettes). All deserve schedule buffer.

This estimate honours Captain's Weakness 6 ruling. The 9-week figure from the draft plan was optimistic; ~10-12 weeks is the honest band.

## 15. Captain decision points (consolidated)

**Pre-ratification (this document):**
- Ratify the four Q1–Q4 rulings as I've folded them in.
- Ratify the two R1/R2 riders.
- Ratify my interpretation that Phase 0 native-compile spike is *parallel investigation alongside* per-commit hardware gating, not a replacement (§1 Blocker 2 row).
- Ratify the per-mode static reset approach (hoist to file scope vs convert to parameter-passed state struct) — decision can also be deferred to Spike #4 execution.

**Phase 0:**
- SS LED output STRIP / KEEP (default: STRIP).
- SS AP algorithm KEEP-UNTOUCHED (default) / KEEP-WITH-LATER-REVIEW / STRIP.
- `PHOTONS_CURVE_MODE` keep-ifdef / hardwire-mode-2.
- Lightshow mode roster KEEP/STRIP per mode.
- Music corpus.
- Worktree topology.
- Spike #1 native outcome → native gate yes/no/partial.
- Spike #4 reset helper outcome → 12-mode Tier A coverage ratified or revised; quantum_collapse Tier B run-to-run wander assessment.

**Phase 1:**
- WAVEFORM_FAST fix visual smoke approval.
- Remote choice: GitHub private / GitLab private / external-media bare repo.
- Freeze baseline capture session timing.

**Phase 2 (per bundle, not per item):**
- Serial-command STRIP-candidate bucket ratification.
- Serial-command CONTESTED bucket per-row ratification.
- SS-LED / SS-AP / PHOTONS_CURVE_MODE / mode-roster final rulings.

**Phase 3 (per commit):**
- Sign-off on each strip commit group via per-commit harness gate session.

**Phase 4:**
- Freeze Baseline canonisation in `CANONICAL_MILESTONES.md` (conditional on Open Item #1).

**Phase 5 (per commit / per sub-phase):**
- Per-commit harness gate session (Q1 ruling).
- Per-sub-phase merge approval.
- Any envelope-drift or harness-tolerance exception requests (default answer: NO, fix the code).
- Visual deviation Captain spots that harness missed.

**Throughout:**
- `start_noise_cal` authorisation (Captain confirms verbal silence first).
- Hardware target discipline: direct serial/capture/upload work is allowed when required, but target identity must be verified before device interaction.
- Flash erase authorisation (Captain-owned).

**Off-critical-path (Open Item #1):**
- Equivalence silence-window hygiene check (Captain confirms from memory OR re-runs noise cal under confirmed silence and reports SSL).

## 16. Verification — how to test this plan end-to-end

1. **Captain ratifies via explicit acceptance** of: corrections applied (§1), open items (§2), Phase 0 deliverables + spike scope (§4), Phase 1 pre-freeze commit order (§5), Phase 5 sub-phase order (§9), acceptance criteria (§13), honest effort envelope (§14), decision-point summary (§15).
2. **Phase 0 ratification session** — Captain reviews six documents + four spike outcomes in one cycle. Any artefact rejected → revise before Phase 1 starts.
3. **Phase 1 freeze gate** — clean build matches measured `9423ea0` envelope; doctrine R5/R6/R7/R9/R11 green; Freeze Baseline captured + version-controlled + tagged; remote configured and pushed.
4. **Phase 2–5 harness gates** — every commit passes per-commit hardware AP+VP harness diff vs Freeze Baseline (`run_diff.sh` exit code 0).
5. **Per-sub-phase envelope monotonicity** — flash and RAM never regress within a sub-phase; final envelope within +1% flash / +2% RAM.
6. **Final acceptance** — all 22 acceptance criteria hold.
7. **Post-refactor canonisation** — refactor completion canonised in `CANONICAL_MILESTONES.md` as a load-bearing milestone (third entry after The Equivalent Port and The Freeze Baseline).

**The refactor is verified-complete when:** the K1 firmware on `refactor/main` builds clean on `k1_hardware`, passes AP+VP harness vs Freeze Baseline within tolerance, satisfies all 22 acceptance criteria, and a new contributor can add a lightshow mode or serial command with single-file edits per criteria 20–22.

**The refactor is NOT verified-complete merely because:** code compiles, code uploads, code "looks right" visually, or any agent reports success without harness evidence. The 2025-09-19 `incandescent_lookup` incident and the WAVEFORM_FAST 1.60× drift both compiled clean. The harness is the gate, not eyeball.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) + Captain Yeap | Created. Corrected end-to-end plan supersedes `plan-draft-transient-cuddling-wirth.md`. Folds in audit pre-ratification checklist (Blockers 1-3 + Weaknesses 4-9), Captain Q1-Q4 rulings (per-commit hardware gate; 5c-first; vp_probe 13-mode extension; canonical-agnostic equivalence framing), Captain riders R1 (reset helper as instruction, not discretion) + R2 (aggregate-init mini-spike pulled ahead of 5b). Source-anchored to baseline `9423ea0`. Phase 0 expanded with 4 spikes. WAVEFORM_FAST fix moved to first commit of Phase 1. Freeze Baseline + harness scripts relocated to K1 repo. Honest effort estimate. AWAITING CAPTAIN RATIFICATION. |
