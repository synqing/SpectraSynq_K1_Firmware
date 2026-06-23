---
abstract: "Back-test and audit of the 'K1 SensoryBridge Firmware Refactor — End-to-End Plan' (plan dated 2026-05-24). Every checkable claim in the plan was verified against the K1 repo at HEAD c872032. Result: the plan is methodologically sound and doctrine-aware but NOT ratifiable as written. Three blockers: (1) the keystone 'Equivalent Port' equivalence claim is unverified and contradicted by the repo's own latest evidence; (2) per-commit harness gating, the then-stated agent-serial ban, and the 2-day Captain-time budget are mutually exclusive — the plan's core safety property is unaffordable as specified; (3) the Freeze Baseline captures the WAVEFORM_FAST bug while Phase 3 fixes it, so the harness fails mode 7 by construction. Plus a wrong mode count (13, not 9) hardcoded into binding acceptance criteria, an unproven harness, and no off-machine backup. Verdict: conditional approve after a defined pre-ratification checklist. Auditor environment could not reach LightwaveOS_Official or ~/.claude/memory — claims depending on those are flagged unverified, not false."
---

# Refactor Plan Audit — K1 SensoryBridge Firmware Refactor

| Field | Value |
|---|---|
| Audit date | 2026-05-24 |
| Repo | `~/SensoryBridge-main 9` (K1 fork) |
| HEAD at audit | `c87203273b34bbc68118775bc3f5830c92514f7c` — `feat(audio): Fix-D — two-layer defense against DC_OFFSET calibration poisoning` |
| Branch | `feat/pio-core-bump` |
| Plan audited | "K1 SensoryBridge Firmware Refactor — End-to-End Plan", plan date 2026-05-24, author Claude Code (Opus 4.7) |
| Auditor | agent:claude-opus-4-7 (Cowork session) |
| Method | Source-verified back-test of every checkable plan claim against HEAD `c872032`, followed by a logic/leverage audit |
| Verdict | **Conditional approve.** Not ratifiable as written. Three blockers + significant weaknesses below. |

## Verification environment and limits

This audit was run from a Cowork session with the K1 repo mounted. Two limits apply and are load-bearing for how findings are labelled:

1. **No build performed.** The auditor did not compile. All build-envelope statements are logical, not measured. The actual `c872032` flash/RAM figure is unverified.
2. **`LightwaveOS_Official` and `~/.claude/memory` are not reachable from this environment.** [FACT] `/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official` and `~/.claude/memory` do not resolve. The plan places its entire Phase 0 deliverable set, the harness baselines, the regression-harness scripts, the doctrine source, and the canonical milestone registry in those two locations. Claims depending on them are flagged **unverified**, not false — the plan author (Claude Code) runs natively on Captain's Mac where those paths do exist. This is itself an environment-verification finding (see Blocker 1 and Significant Weakness 5).

Evidence commands and raw output are in the Appendix.

## Verdict

The plan is methodologically serious and doctrine-aware. Strip-before-split, isolated-before-cross-cutting, per-sub-phase worktrees with serial merge, objdump `.rodata` verification for aggregate-initialiser moves, the static-init-order map, and the closing principle ("compiles ≠ done — the harness is the gate, not eyeball") are all correct and clearly informed by the 2025-09-19 `incandescent_lookup` incident and the LightwaveOS Phase 8 catastrophe.

It is **not ratifiable as written.** It ships on a keystone claim the repo contradicts, contains an operational contradiction that destroys its core safety property, and hardcodes a wrong constant into binding acceptance criteria.

## Back-test: plan claims vs repo at `c872032`

| # | Plan claims | Repo says | Verdict |
|---|---|---|---|
| 1 | Baseline `c872032`, Fix-D shipped | `c872032` = HEAD = `feat(audio): Fix-D — two-layer defense against DC_OFFSET calibration poisoning` | ✓ accurate |
| 2 | "K1 audio pipeline now matches the S2 baseline within instrumentation noise on every load-bearing variable" — canonised as "The Equivalent Port" | No such document exists in the repo. Latest in-repo AP-equivalence evidence (`docs/forensics/2026-05-24-stage7-handoff.md`) tabulates K1 ≠ S2 on SSL, max_raw, follower, peak_scaled | **✗ unverifiable + contradicted** |
| 3 | "1 .ino + 11 .h header-monolith" | 1 `.ino` + **19 `.h`** files in `SPECTRASYNQ_K1_FIRMWARE/` | ✗ undercount by 8 |
| 4 | led_utilities 2046 / serial_menu 2352 / globals 685 / system 586 / lightshow_modes 1911 LOC | 2045 / 2351 / 684 / 585 / 1910 | ✓ accurate to ±1 |
| 5 | "141 strcmp dispatch arms in serial_menu.h" (vs 125 from a second agent) | `grep -c strcmp serial_menu.h` = **186** | ✗ neither figure matches; surface larger than planned |
| 6 | "9 lightshow modes" | **13 distinct `light_mode_*` function definitions**, including `kaleidoscope` and `quantum_collapse` | ✗ wrong — and "9" is hardcoded into acceptance criteria 10/11/20 and the harness spec |
| 7 | `incandescent_lookup` is the led_utilities.h "aggregate-init bomb anchor" handled in Phase 5a | `incandescent_lookup` is **defined in `constants.h:439`**; `constants.h` splits in Phase 5g (last) | ✗ misattributed — see Significant Weakness 7 |
| 8 | vp_probe machinery at `lightshow_modes.h:1671-1875` | Present; `vp_probe_*` runs 1671 → ~1881 | ✓ accurate |
| 9 | Phase 0 artefacts / harness / baselines / doctrine source in `LightwaveOS_Official`; milestones in `~/.claude/memory` | Neither path resolves in the audit environment | ✗ unreachable here (see limits) |
| 10 | Build envelope 552 622 B flash / 83 024 B RAM | That figure is the `2cbeea9` measurement (from `stage7-handoff.md`); `c872032` = `2cbeea9` + 3 commits including `99a730b feat(debug): add dump_raw` — a runtime feature that changes flash | ✗ envelope anchored to the wrong commit |
| 11 | build_src_filter currently `+<*.ino> +<*.ino.cpp>`; partitions `default_16MB.csv` | Confirmed at `platformio.ini:37` and `:30` | ✓ accurate |

The plan's file-size figures (row 4) back-test clean. Its inventory *counts* (rows 3, 5, 6) do not. Its keystone premise (row 2) does not.

## Blockers — must be resolved before ratification

### Blocker 1 — the keystone equivalence claim is unverified and contradicted by the repo's own latest evidence

[FACT] The most recent AP-equivalence document in the repo, `docs/forensics/2026-05-24-stage7-handoff.md`, states K1 reached a *different* operating point from S2: SSL 6092 vs S2 369, max_raw roughly 5–10× higher, peak_scaled compressed, follower less dynamic. The plan asserts the opposite — "matches the S2 baseline within instrumentation noise on every load-bearing variable" — and labels it settled fact, canonised as "The Equivalent Port".

[INFERENCE] Fix-D (`c872032`) is a two-layer defence against DC_OFFSET calibration poisoning. It is a regression guard, not an equivalence proof. The plan conflates "Fix-D shipped" with "pipeline matches S2". They are different claims with different evidence requirements.

[FACT] There is no document in the K1 repo establishing AP equivalence to S2. The plan attributes the canonisation to `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md`, which is not reachable from the audit environment.

**Severity rationale.** The equivalence claim is the plan's entire "why now" ("we now have empirical equivalence verification ... Previous refactor attempts failed because they had no regression detector. We do now."). The mitigating fact: the refactor harness self-baselines at `c872032` (the Freeze Baseline captured in Phase 1), so the refactor mechanics do **not** depend on S2-equivalence being true. This is therefore an evidence-and-wording defect, not a design defect — but an unverified claim presented as fact in a document about to gate a 44-day effort is precisely the class of error the audit exists to catch.

**Fix.** Either cite the evidence file that establishes equivalence, or downgrade the claim to what the repo supports: "K1 reached a stable, Fix-D-guarded operating point." Delete "matches S2 within instrumentation noise" unless evidenced. Whichever way it resolves, the harness baseline must be the `c872032` freeze capture, not S2.

### Blocker 2 — per-commit harness gating, the serial-port discipline rule, and the 2-day Captain budget are mutually exclusive

This is the deepest flaw. The plan's safety thesis — and its claimed superiority over the failed LightwaveOS Phase 8 attempt — is "the harness gates every commit, so a regression is caught at a recoverable diff size." Three plan provisions make that unaffordable as specified:

1. The harness is captured over the serial port.
2. The plan forbids the agent from opening the port ("agent NEVER opens port; Captain captures, agent reads file").
3. The plan budgets ~2 total Captain-days.

[INFERENCE] Phase 5a alone splits 52 inline functions in batches of 5–10, with a "harness gate per batch" — roughly 6–10 Captain hardware-capture sessions in that sub-phase alone. Across all seven Phase 5 sub-phases plus Phase 3, per-batch gating is dozens of Captain sessions, not 2 days. The alternative — dropping to per-sub-phase gating to fit the budget — discards tight bisection: a failed gate at the end of a 6-day sub-phase leaves the regression somewhere in a large diff, which is exactly the Phase 8 failure mode. **The plan's core safety property and its cost model are in direct conflict.**

**Fix (high-leverage, the plan half-contains it).** VP harness Tier A (`vp_probe=all`) uses deterministic seeded inputs — no microphone, no live audio. [INFERENCE] If the render pipeline compiles under the plan's own proposed optional native env, Tier A runs **on the build machine, agent-executed, with zero Captain involvement and zero serial port** — a genuine automated per-commit gate. The AP harness genuinely requires hardware and Captain, but AP behaviour only changes in sub-phases 5b (globals) and 5f (audio); 5a/5c/5d/5e are AP-neutral.

Restructure the gate model:

- **VP Tier A → native, agent-run, per-commit.** Hard gate. This is the per-commit bisection guarantee.
- **AP harness + VP Tier B + visual smoke → Captain hardware session, per-sub-phase.** AP-gated only on 5b, 5f, Phase 3, and the freeze capture.

This cuts Captain from dozens of sessions to roughly 10–12 and makes per-commit bisection real.

**Required Phase 0 spike.** "Do the `light_mode_*` functions and `vp_probe_*` machinery compile and run under the native env?" [HYPOTHESIS] They likely do — the render modes are largely pure fixed-point math on `CRGB16`/`SQ15x16` buffers — but some modes may pull in `millis()`/`micros()` and need shimming. This spike determines whether the plan's central safety property is affordable. The plan currently assumes per-commit gating is affordable without specifying the mechanism. Make it an explicit Phase 0 deliverable; its outcome decides the gate model.

### Blocker 3 — the Freeze Baseline captures the WAVEFORM_FAST bug, then Phase 3 fixes it; the harness then fails mode 7 by construction

The Freeze Baseline is captured in **Phase 1**. The WAVEFORM_FAST mode-7 frame-shift fix lands in **Phase 3**. The Tier B centre-of-mass-slope metric is explicitly designed to detect the 1.60× transport drift.

Therefore the Phase 3 → Freeze Baseline harness diff for mode 7 is a deliberate ~1.6× mismatch measured against a ±10% tolerance band — a guaranteed gate failure baked into the design. The plan papers over this: Phase 4's gotcha note says "mode 7 WAVEFORM_FAST golden encodes fixed behavior because the fix landed in Phase 3", which directly contradicts "Freeze Baseline captured in Phase 1". Both cannot hold.

**Fix.** Move the WAVEFORM_FAST fix to the **first commit of Phase 1, before the freeze-baseline capture session.** It is a correctness fix, it qualifies under the plan's own "critical hardening" exception to the trunk freeze, and pre-freeze placement makes the golden clean for every mode. The plan's stated reason for Phase 3 placement — "a standalone, clearly-titled commit" — is cosmetic and not worth a structural gate contradiction.

## Significant weaknesses

### 4 — wrong mode count breaks binding acceptance criteria

[FACT] The source defines 13 distinct `light_mode_*` functions, including `kaleidoscope` and `quantum_collapse`. Acceptance criteria 10, 11, and 20, and the harness spec ("9-mode hash+energy"), hardcode "9". A harness scoped to 9 of 13 silently skips two-plus modes. Re-parameterise every "9" to "all modes per the Phase 0-ratified roster." The plan already commits Phase 0 to confirming the count — it must then *not* pre-bake the unconfirmed number into criteria.

### 5 — the harness is never proven to be a detector

Phase 4's self-check (baseline vs baseline → all PASS) proves only that the parser does not crash on identical input. It does not prove the harness *detects a real regression*. A regression detector that has never been observed catching a regression is not yet a detector. The plan cites the 2025-09-19 `incandescent_lookup` incident and the WAVEFORM_FAST drift as proof that "compiles clean" is insufficient — but never demonstrates the harness would catch either.

**Add a deliberate-regression injection test:** revert the WAVEFORM_FAST fix on a throwaway branch and confirm the COM-slope gate returns FAIL. The buggy commit exists; use it. This is the cheapest, highest-leverage hardening available and belongs in Phase 4 before the Freeze Baseline is sealed as canon.

### 6 — Captain-time is materially under-estimated

"~2 days Captain-time" is the least defensible number in the plan. Phase 2 is Captain personally ruling KEEP/STRIP/DEFER on ~186 serial commands plus every feature row. Phase 3 is per-commit-group sign-off. Phase 5 is seven sub-phases, each needing capture + visual smoke + merge approval. Realistic Captain load is 3–5× the estimate, and — because the harness capture is hardware-in-the-loop — Captain availability, not agent-days, is the calendar critical path. The plan calls its 44-day agent figure "honest, not optimistic"; the Captain column is not. Re-estimate it. The 9-week calendar figure will likely move; that is the estimate doing its job.

### 7 — Phase 5a sequencing rationale does not hold

The plan orders led_utilities.h first "because solving it ... surfaces ODR/aggregate-init gotchas while diff is still recoverable", and names it "the `incandescent_lookup` aggregate-init bomb anchor". [FACT] `incandescent_lookup` is defined in `constants.h:439`, not led_utilities.h; led_utilities.h only *consumes* it. `constants.h` splits in Phase 5g — last. So Phase 5a does not actually exercise the named aggregate-init risk; that move is deferred to the final sub-phase, contradicting the "surface it early" rationale.

Two further sequencing points: (a) doing the worst monolith first as the pattern-prover is risk-asymmetric — prove the strip+split mechanics and the end-to-end gate on a cheap module (system.h, 585 LOC) first, then apply a proven process to led_utilities; (b) 5a-before-5b forces a rework pass — 5a's new `.cpp` files reference the old `globals.h`, which 5b then restructures into `core/state` + `config/config`, requiring a second edit pass over 5a's output. The plan notes the dependency but not the rework cost.

### 8 — no off-machine backup

[FACT] `git remote -v` is empty; the repo is local-only. The plan's "ultimate floor", `backup/pre-refactor-20260525`, is a local branch on the same disk as everything it backs up — a single point of failure for 9 weeks of work plus the migration. Phase 1 must add a remote (private GitHub/GitLab, or a bare repo on separate physical media) and push the baseline tag, the backup branch, and `refactor/main` continuously. A local branch is not a backup.

### 9 — the harness baseline is versioned in the wrong repo

The Freeze Baseline gates every Phase 5 commit but is stored in `LightwaveOS_Official`, a different repo from the firmware it gates. The plan freezes it with `chmod a-w`; that is filesystem permission, not version control, and is undone by a single `chmod u+w`. If the two repos drift, the gate compares against a moving target. Move the Freeze Baseline into the K1 repo, commit it, and tag it with the freeze tag so firmware and gate are versioned together. The plan already routes some artefacts into `docs/refactor/` — extend that to the baseline and the regression-harness scripts.

## Minor / accuracy

Phase 2 having Captain individually rule all ~186 serial commands is low-leverage activity dressed as diligence. Most commands are debug/diagnostic, low-stakes, reversible. The agent should pre-classify each with file:line evidence and a proposed default (KEEP unless S2-hardware-specific or provably dead), and escalate to Captain only the contested subset and the strip candidates. This is consistent with the operating contract: do the agent's own work, escalate genuine decisions.

The "1 .ino + 11 .h" in the Context section should read "1 .ino + 19 .h" — the plan's own Critical Files section and Phase 5 sub-phases touch 14 headers, so the body already contradicts the header.

Phase 1's validation gate ("clean build matches 2cbeea9 envelope ±0 bytes") and acceptance criterion 7 ("Flash within +1% of 552 622 B") both anchor to `2cbeea9`. The baseline commit is `c872032`, which is `2cbeea9` plus three commits including `dump_raw` (a runtime feature). [INFERENCE] `c872032`'s envelope almost certainly differs from 552 622 B. Anchor the envelope to the measured `c872032` freeze build (Phase 1 task 4 already produces this) and rewrite the gate text and criterion 7 to reference it.

## What the plan gets right

Stated plainly for balance: the strip/split ordering, isolated-before-cross-cutting separation, per-sub-phase child worktrees with strictly serial merge, objdump `.rodata` byte-identity verification for aggregate-initialiser moves, the static-init-order map captured in 5b, Tier A reusing the real in-tree `vp_probe_*` code rather than inventing instrumentation, the explicit non-goals and Founder Execution Boundary, and the closing principle that compile/upload/eyeball are not acceptance — only harness evidence is. The author internalised the prior failures. The bones are sound; the defects above are correctable without redesigning the strategy.

## Recommendation — conditional approve

Ratify only after the following pre-ratification checklist is cleared:

1. **Equivalence claim** — cite the evidence or downgrade it (Blocker 1).
2. **Gate model** — add the Phase 0 native-compile spike; restructure to VP-Tier-A-native-per-commit and AP-hardware-per-sub-phase (Blocker 2).
3. **WAVEFORM_FAST fix** — move to pre-freeze Phase 1 (Blocker 3).
4. **Mode count** — re-parameterise every hardcoded "9" to the Phase 0-ratified roster (Weakness 4).
5. **Harness detector test** — add the deliberate-regression injection test to Phase 4 (Weakness 5).
6. **Captain-time** — re-estimate honestly; expect the calendar figure to move (Weakness 6).
7. **Backup** — add a remote in Phase 1 (Weakness 8).
8. **Baseline location** — move the Freeze Baseline and harness scripts into the K1 repo (Weakness 9).

Items 2 and 6 may extend the 9-week estimate. That is the estimate functioning correctly, not failing.

## Appendix — evidence

All commands run against `~/SensoryBridge-main 9` at HEAD `c872032`.

```
# Baseline commit
$ git log -1 --format="%H | %s"
c87203273b34bbc68118775bc3f5830c92514f7c | feat(audio): Fix-D — two-layer defense against DC_OFFSET calibration poisoning

# Branch / tags / remotes
branch: feat/pio-core-bump (also: main)
tags:   pre-pio-migration-20260524-1320   (only tag)
remote: (none — git remote -v empty)
branch commit chain: 93052a9 → 2cbeea9 → 99a730b → f8e87b7 → a0937ff → c872032

# Header inventory — SPECTRASYNQ_K1_FIRMWARE/
.h files: 19    .ino files: 1
LOC: led_utilities.h 2045, serial_menu.h 2351, lightshow_modes.h 1910,
     encoders.h 914, audio_transfer.h 740, globals.h 684, Palettes.h 567,
     system.h 585, i2s_audio.h 499, constants.h 453, GDFT.h 332,
     bridge_fs.h 301, utilities.h 108, knobs.h 85, buttons.h 83,
     presets.h 47, noise_cal.h 27, strings.h 14, user_config.h 14,
     SPECTRASYNQ_K1_FIRMWARE.ino 624

# Serial command surface
$ grep -c strcmp serial_menu.h
186

# Lightshow modes — distinct light_mode_* definitions (13)
gdft, gdft_chromagram, bloom, vu, vu_dot, kaleidoscope,
chromagram_gradient, chromagram_dots, quantum_collapse, bloom_fast,
waveform_fast, waveform, waveform_hybrid

# vp_probe machinery
lightshow_modes.h:1671 onward (vp_probe_quantise_channel ... vp_probe_print_mode ~1881)

# incandescent_lookup
constants.h:439:  CRGB16 incandescent_lookup = { 1.0000, 0.4453, 0.1562 };
(consumed in led_utilities.h:344-367)

# Build config
platformio.ini:30  board_build.partitions = default_16MB.csv
platformio.ini:37  build_src_filter = +<*.ino> +<*.ino.cpp>

# Environment limits
/Users/spectrasynq/Workspace_Management/Software/LightwaveOS_Official — does not resolve
~/.claude/memory — does not resolve
```

---

| Date | Author | Change |
|---|---|---|
| 2026-05-24 | agent:claude-opus-4-7 (Cowork) | Created. Back-test + audit of the 2026-05-24 refactor plan against HEAD c872032. Three blockers, six significant weaknesses, conditional approve. |
| 2026-05-25 | agent:claude-opus-4-7 (K1-rooted execution session) | Re-anchor addendum (below). Audit body retained as historical record at `c872032`. Baseline has since advanced to `9423ea0` (`feat(serial): K1 serial hotkey layer with N/Y noise-cal arm/confirm gate`). Pre-ratification checklist resolved by `docs/k1-refactor-2026-05/01-CORRECTED-PLAN.md`. |

---

## Re-anchor addendum — 2026-05-25

The audit body above is the historical record of plan defects at HEAD `c872032`. It is **not** rewritten to the current baseline because the findings are evidence-anchored to that commit. The corrections live in the corrected plan (`docs/k1-refactor-2026-05/01-CORRECTED-PLAN.md`), not in revisions to this document.

**Baseline transition:** `c872032` → `9423ea0` (`9423ea0833dc76998d2af4b2606bc18a73503cbe`). The hotkey-layer commit is the new refactor baseline per the execution-handover brief.

**Source-count deltas from re-verification at `9423ea0`:**

- **`.h` files: 19** (unchanged from c872032) — audit's count holds.
- **`.ino` files: 1** (unchanged) — audit's count holds.
- **`serial_menu.h` LOC: 2823** (was 2351 at c872032; **+472 LOC** from the hotkey-layer commit). All Phase 5d sub-phase planning re-anchored to the new figure.
- **`led_utilities.h` / `lightshow_modes.h` / `globals.h` / `system.h` LOC**: 2045 / 1910 / 684 / 585 — all unchanged from audit.
- **`serial_menu.h` strcmp count: 186** (unchanged) — audit's correction over the plan's 141 holds.
- **`light_mode_*` definitions: 13 distinct names** (14 `void light_mode_*` grep hits — `bloom` has two overloads at L357 and L865). Audit's correction over the plan's 9 holds.
- **`incandescent_lookup` defined at `constants.h:439`** (unchanged). Audit's correction over the plan's "led_utilities.h" placement holds.

**New finding not catalogued by original audit [FACT]:** `vp_probe_print_mode()` at `lightshow_modes.h:1873-1881` iterates only **9** modes — `vu_dot`, `kaleidoscope`, `quantum_collapse`, `chromagram_gradient` are **not** covered by Tier A. The audit's "13 modes" correction (Weakness 4) implicitly exposes this coverage gap. Resolved in corrected plan Phase 0 via Spike #3 (extend vp_probe to 13) + Spike #4 (reset helper as instruction, not discretion, per Captain).

**New finding not catalogued by original audit [FACT]:** `~/.claude/memory/spectrasynq/L1/CANONICAL_MILESTONES.md` exists (27 KB, Captain-ratified 2026-05-24 18:37 AWST). It records **K1 SSL=299 post-recal** vs S2=369 (−19%, within MEMS bias spec per Captain's engineering judgment). This contradicts `docs/forensics/2026-05-24-stage7-handoff.md`'s K1 SSL=6092 (mid-migration, self-described preliminary). The original audit environment could not reach `~/.claude/memory/` so this evidence was not considered. **Per Captain's Q4 ruling (2026-05-25):** equivalence is NOT Blocker 1; the harness self-baselines at Freeze and does not depend on the K1↔S2 question. Resolution path is canonical-agnostic plan wording + a Captain-owned off-critical-path silence-window hygiene check. See `01-CORRECTED-PLAN.md §11` and §2 Open Item #1.

**Build envelope re-anchor:** the plan's `552 622 B flash / 83 024 B RAM` figure is anchored to `2cbeea9` (4 commits behind baseline). At `9423ea0` the envelope must be re-measured. Phase 1 task list captures the measurement directly and writes it to `docs/refactor/baseline-envelope.json`; acceptance criterion 7 reads against the measured figure, not against `2cbeea9`.

**Pre-ratification checklist disposition:**

| Audit item | Status as of 2026-05-25 |
|---|---|
| Blocker 1 (equivalence) | Resolved by canonical-agnostic plan framing; not load-bearing for refactor |
| Blocker 2 (gate model) | Captain Q1 ruling: per-commit hardware gating throughout; Phase 0 native-compile spike retained as parallel investigation |
| Blocker 3 (WAVEFORM_FAST sequencing) | Resolved: fix moved to first commit of Phase 1, pre-freeze |
| Weakness 4 (mode count) | Resolved: 13 modes; every "all modes" claim re-audited per Captain's cross-cutting finding (no find-replace) |
| Weakness 5 (harness detector) | Deliberate-regression injection test added to Phase 4 |
| Weakness 6 (Captain-time) | Re-estimated honestly: ~25-40 hardware sessions, ~12-20 hours Captain-time |
| Weakness 7 (Phase 5a rationale) | Resolved by reordering: 5c first as pattern-prover (Captain Q2) |
| Weakness 8 (off-machine backup) | Phase 1 task added: Captain chooses remote, pushes tag + backup branch |
| Weakness 9 (baseline in wrong repo) | Freeze Baseline + harness scripts relocated to K1 repo |

All resolutions are in `docs/k1-refactor-2026-05/01-CORRECTED-PLAN.md`. The corrected plan awaits Captain ratification (gate C).
