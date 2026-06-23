---
abstract: "End-to-end execution handover brief for the fresh K1-rooted Claude Code session that will execute the K1 SensoryBridge firmware refactor. Context preamble, ordered pre-read, gated mission sequence, the audit corrections that must be applied before the plan is ratifiable, operating constraints, and escalation rules. Read this in full before any action."
---

# K1 SensoryBridge Firmware Refactor — Execution Handover Brief

| Field | Value |
|---|---|
| Brief date | 2026-05-24 |
| For | A fresh Claude Code session, rooted in the K1 repo |
| Repo (working root) | `/Users/spectrasynq/SensoryBridge-main 9` |
| Branch | `feat/pio-core-bump` |
| Refactor baseline | The hotkey-layer commit — see §6 First Actions. Record its SHA as `<BASELINE-SHA>` and use it everywhere this brief and the plan say `c872032`. |
| Prior commit | `c872032` — `feat(audio): Fix-D` (superseded as baseline by the hotkey commit) |
| Status | Refactor NOT started. Plan NOT ratified. |

## 0. Who you are, and the one rule that frames everything

You are a fresh Claude Code session picking up execution of the K1 firmware refactor. This document is your mission brief, pre-read index, and operating constraints. **Read it in full before any action.**

The framing rule: **you do not cut a single line of refactor code until Captain has ratified a corrected plan.** The existing plan has three audit blockers. Your first job is to produce the corrected, ratifiable plan — not to execute the draft.

## 1. Context preamble — the story so far

**Product north star.** This project is not "clean firmware." It is a music-to-visual translation system intended to exceed Sensory Bridge's perceptual impact. Architecture is subordinate to that benchmark. (`.claude/CLAUDE.md` carries the full doctrine bridge.)

**The migration.** The PIO toolchain migration landed on 2026-05-24: arduino-esp32 3.2.0 / ESP-IDF 5.4.1 / FastLED 3.10.3 RMT5. `c872032` (`feat(audio): Fix-D`) was its final commit and the original refactor baseline.

**The refactor was planned, then audited.** A plan to strip the K1 firmware's header-monolith (1 `.ino` + 19 `.h`, with `led_utilities.h` at ~2045 LOC and `serial_menu.h` the second-worst) and split it into modules was produced. It was independently back-tested against live source. The audit (`docs/forensics/2026-05-24-refactor-plan-audit.md`) found **3 blockers and 6 significant weaknesses** and returned a *conditional approve* — not ratifiable as written.

**The plan was written from the wrong repo root.** The planning agent ran out of `LightwaveOS_Official`, not the K1 repo. That is the probable cause of the plan's source-count errors (it claimed 11 headers; there are 19 — and more). **This is why you are K1-rooted. Stay that way.** `LightwaveOS_Official` is read-only doctrine reference only.

**The handoff.** The planning agent stood down and produced a handoff package, now in `docs/k1-refactor-2026-05/`.

**The hotkey interlude.** A serial-hotkey feature was the last feature landed before the freeze ("land hotkeys first" — committing it before the immutable baseline rather than bolting it on after). It was audited across four revisions; one revision bound noise calibration to a single keystroke and the audit caught it as a hard blocker. The shipped design is `N` (arm, 5 s) then `Y` (confirm). It is the hotkey-layer commit that is now your refactor baseline. Receipt: `docs/forensics/2026-05-24-hotkeys-prefreeze-review.md`.

## 2. Current repo state

Branch `feat/pio-core-bump`. HEAD is (or must become — see §6) the hotkey-layer commit. **No git remote is configured** — the repo is local-only; this is audit Weakness 8 and Phase 1 must fix it. The refactor has not begun. The plan is not ratified.

## 3. Your mission, and the gated sequence

**End state:** the K1 firmware refactored per a corrected, Captain-ratified plan — header-monolith stripped and split into modules, every change harness-gated, behaviour proven equivalent to the freeze baseline.

**The sequence is gated. Do not skip a gate.**

- **A — Re-ground.** Root, re-anchor the baseline SHA, consolidate the plan into the repo, re-verify source counts against live source. (§6)
- **B — Produce the corrected plan.** Apply every item in §5. This is your Phase 0; its deliverable is a ratifiable plan set.
- **C — Captain ratifies.** Hard gate. Do not proceed to any firmware change without explicit ratification.
- **D — Phase 1: Freeze.** Tag the baseline, create the backup branch *and a remote*, create `refactor/main`, land harness firmware, capture the Freeze Baseline.
- **E — Phases 2–5** per the corrected plan, each sub-phase harness-gated.

You are at the start of A. Do not cut refactor code before C.

## 4. Pre-read — in this order

**Tier 1 — before you do anything:**

1. `.claude/CLAUDE.md` — the doctrine bridge, the calibration-command policy, serial-port discipline. This is operating law, not reference.
2. `docs/forensics/2026-05-24-refactor-plan-audit.md` — **the audit.** 3 blockers, 6 weaknesses, an 8-item pre-ratification checklist. This is your correction list; §5 below summarises it.
3. `docs/k1-refactor-2026-05/HANDOFF-to-k1-rooted-session.md` — the planning session's handoff: every load-bearing claim labelled `[FACT]`/`[INFERENCE]`/`[HYPOTHESIS]`, the audit-contradicted claims, and the decisions the planning session was not confident in.
4. The refactor plan — currently at `~/.claude/plans/transient-cuddling-wirth.md` (a *transient* location; copy it into the repo — see §6.3). Treat it as a **draft input**, not a ratified plan.

**Tier 2 — design inputs (drafts, audit-flagged):**

5. `docs/k1-refactor-2026-05/phase1-source-survey-from-explore-agents.md`
6. `docs/k1-refactor-2026-05/phase2-plan-agent-1-phase-execution.md`
7. `docs/k1-refactor-2026-05/phase2-plan-agent-2-architectural-target.md`
8. `docs/k1-refactor-2026-05/phase2-plan-agent-3-harness-design.md`
9. `docs/k1-refactor-2026-05/scoping-notes-and-rejected-alternatives.md`

**Tier 3 — reference:**

10. `LightwaveOS_Official/docs/agent-outputs/analysis/sensory-bridge-lessons-doctrine.md` — the 12-rule doctrine. Absolute path, read-only. You stay K1-rooted; you may *read* this.
11. `docs/forensics/2026-05-23-sb-waveform-bloom-s2-s3-forensic-reconstruction.html` — the K1-local fork evidence base.
12. `docs/forensics/2026-05-24-doctrine-gate-pio-migration.md`, `...-stage7-handoff.md`, `...-k1-waveform-fast-speed-investigation.md`, `...-hotkeys-prefreeze-review.md`.
13. `docs/hardware/k1-hardware-definition.md` — canonical hardware truth.

## 5. Corrections you must apply before the plan is ratifiable

From the audit. The first three are blockers.

1. **Equivalence claim (Blocker 1).** The plan's "The Equivalent Port — K1 matches S2 within instrumentation noise" is unverified and contradicted by `stage7-handoff.md`. Cite real evidence or downgrade the claim. The refactor harness self-baselines at the freeze commit, so it does not depend on S2-equivalence — fix the wording, do not redesign around it.
2. **Gate model (Blocker 2).** Per-commit harness gating + a hardware-capture bottleneck + a ~2-day Captain budget are mutually exclusive. Add a Phase 0 spike: *do the `light_mode_*` / `vp_probe_*` paths compile and run under a native env?* If yes, run VP Tier A as an agent-executed per-commit native gate; keep AP + visual smoke as hardware sessions with verified target identity, per-sub-phase. This spike decides the whole cost model.
3. **WAVEFORM_FAST fix (Blocker 3).** The plan freezes the baseline in Phase 1 but fixes WAVEFORM_FAST in Phase 3 — the harness then fails mode 7 by construction. Move the fix to the first commit of Phase 1, pre-freeze.
4. **Mode count.** Source has **13** `light_mode_*` definitions, not 9. Re-parameterise every hardcoded "9" in acceptance criteria and the harness spec to "all modes per the Phase 0-ratified roster."
5. **Harness detector test.** The plan never proves the harness *catches* a regression. Add a deliberate-regression injection test — revert the WAVEFORM_FAST fix on a throwaway branch, confirm the gate FAILs.
6. **Captain-time.** "~2 days Captain-time" is unrealistic (Phase 2 alone is ~186 serial commands; Phase 5 is 7 sub-phases of capture). Re-estimate honestly; expect the calendar figure to move.
7. **Off-machine backup.** No remote exists. Phase 1 must create one and push the baseline tag + backup branch.
8. **Baseline location.** Move the Freeze Baseline and harness scripts into the K1 repo (committed, tagged with the freeze tag) — not `LightwaveOS_Official`.

**Back-test count corrections** (verify against the baseline yourself; do not trust the plan): 19 `.h` files (plan said 11); 186 `strcmp` lines in `serial_menu.h`; 13 `light_mode_*`; `incandescent_lookup` is defined in `constants.h:439`, not `led_utilities.h`. Note `serial_menu.h` grew with the hotkey commit (~2786 LOC) — re-measure everything against the baseline commit, not `c872032`.

## 6. First actions — concrete

1. **Confirm environment.** Working root is `/Users/spectrasynq/SensoryBridge-main 9`. Confirm `.claude/CLAUDE.md` is loaded and `/sensorybridge-doctrine` resolves. If either fails, you are mis-rooted — stop and tell Captain.
2. **Confirm the baseline commit.** `git log -1`. If HEAD is the hotkey-layer commit (`feat(serial): K1 serial hotkey layer...`), record its SHA as `<BASELINE-SHA>`. If HEAD is still `c872032`, the hotkey commit has not landed — escalate to Captain before doing anything else; the refactor cannot freeze a baseline that does not exist.
3. **Consolidate the plan.** Copy `~/.claude/plans/transient-cuddling-wirth.md` into `docs/k1-refactor-2026-05/` (the transient location can be garbage-collected). It is a draft input.
4. **Re-anchor and re-verify.** Replace `c872032` with `<BASELINE-SHA>` across the plan and the audit. Re-verify every source count against the baseline with live `grep`/`wc` — `.h` count, `light_mode_*` count, `serial_menu.h` LOC, `incandescent_lookup` location. Trust your measurements, not the plan's.
5. **Produce the corrected plan** applying §5 in full, and present it to Captain for ratification. Stop there — gate C.

## 7. Operating constraints — non-negotiable

- **Doctrine.** Invoke `/sensorybridge-doctrine` before any non-trivial AP/VP, audio, visual, timing, or multi-file change.
- **Calibration policy.** Never auto-fire `start_noise_cal` or any calibration command. Wait for Captain to verbally confirm a silence window. The `N`/`Y` hotkey is governed by the same rule. Violation = STOP-and-rollback.
- **Hardware target discipline.** Serial monitors, firmware uploads/flashes, erase operations, and device-write commands are normal validation tools when the active task requires them. Before any such action, verify the exact target by port plus stable hardware identity such as USB MAC, adapter serial, chip ID, board role, or a captured identity signal. If identity is missing, ambiguous, or mismatched, stop and resolve it before interacting with the device.
- **Root discipline.** Stay in `/Users/spectrasynq/SensoryBridge-main 9`. Never run refactor work from `LightwaveOS_Official` — it is read-only doctrine reference.
- **Git discipline.** Use branches, commits, and tags deliberately for isolation and rollback safety. Never commit untested or unreviewed work; inspect the diff, stage only intended files, run the relevant tests/builds, and record the evidence first. Remote push, destructive history changes, and public release tags require explicit Captain instruction or an active publication lane.
- **Compile/upload is not runtime proof.** Architecture is not success if visual impact, musical responsiveness, dual-channel behaviour, colour clarity, or motion memory regress.
- **Evidence labelling.** Label every load-bearing claim `[FACT]` / `[INFERENCE]` / `[HYPOTHESIS]`. No hand-waving. No claim asserted as fact without a verified source.
- **Failure accountability.** After two failures of the same type, STOP — state what was attempted, the actual failure mechanism, and the proposed alternative. Do not paper over tool failures with workarounds.
- **Environment verification.** Verify paths resolve and tools reach their targets before relying on them.
- **Leverage.** Reject technically-correct but low-value work; propose the higher-leverage substitution.

## 8. Escalate to Captain — do not decide these yourself

- Any plan ambiguity, or a blocker that source-verification cannot resolve.
- Any harness-tolerance widening or build-envelope exception request (default answer: no, fix the code).
- Anything that touches calibration timing or needs a silence window.
- Any visual or audio behaviour deviation, whether the harness caught it or you spotted it.
- Strategic or scope decisions (keymap-class, feature KEEP/STRIP).
- Hardware identity is unclear before serial, flash/upload, erase, or device-write actions.
- Any remote publication, destructive history change, or release tag.

## 9. The Operating Contract — applies to you and to any agent you spawn

You are expected to operate as a combined CTO/CPO: evaluate technical feasibility, product value, and long-term maintainability together, and state trade-offs explicitly. Be direct and precise; generic advice and motivational filler are prohibited.

**The Agent Questioning Protocol applies to you without exception.** Ask Captain as many clarifying questions as the work genuinely requires — batch them, do not drip-feed. "Do your own work" means do not push research, commands, or tool-fixing onto Captain that you can do yourself; it does **not** mean suppress questions when strategic direction or domain context is genuinely needed. If you proceed without full clarity, state explicit, minimal, reversible assumptions and include how to detect when one is wrong.

If you delegate to sub-agents, propagate this contract: preserve the evidence-labelling and questioning protocol, and tell each sub-agent what to escalate — never encode "execute without asking" unless the task is fully specified and misinterpretation is trivially reversible.
