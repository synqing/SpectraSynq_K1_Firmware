---
abstract: "Session-context scoping notes from the 2026-05-24 K1 refactor planning session. Records the strategic shape rationale (Freeze-Inventory-Strip-Harness-Split), rejected alternatives (Split-in-place, Modular, Clean-slate), key design decisions and their justifications, the parallel-team-correction concessions, Captain's SS LED/AP clarification, and the methodology-continuity argument. Persisted for the K1-rooted handoff session so design reasoning is not lost. AUDIT-FLAGGED: several rationale anchors (equivalence claim, source counts, mode 7 sequencing) were subsequently contradicted — see HANDOFF doc."
---

# Scoping Notes and Rejected Alternatives — K1 Refactor 2026-05-24

> Session-context reasoning from the 2026-05-24 planning session. Captures decisions, rationales, rejected alternatives, and the concessions made to the parallel-team-correction during the session. Persisted so the K1-rooted handoff session inherits the design thinking, not just the conclusions.

---

## 1. Why this refactor, why now

**Captain's framing (verbatim):** "WE did it. This is TRULY a momentous occasion." [referring to The Equivalent Port] → followed by recognition that the codebase as it stands "is not fit for further development" and needs refactor.

**Strategic case:**
- The S2→S3 audio equivalence achievement gives a measured baseline (canonised as "The Equivalent Port" 2026-05-24 18:37 AWST).
- The K1 → FE → Kickstarter critical path requires adding feature surface to the codebase. Every feature added on top of the current crufty foundation increases the cost of refactoring later.
- Now is the cheapest the refactor will ever be. The cost compounds with each cycle of "add a feature, work around the monolith."
- We now have empirical equivalence verification (dump_raw, Fix-D, the metrics) — the previous Phase 8 "Agent-Induced Catastrophe" refactor failed without this safety net.

**AUDIT-FLAGGED: The equivalence-achieved framing is contradicted by stage7-handoff.md per Captain's audit. The strategic case still holds in principle — the codebase IS unfit for further development independent of equivalence — but the "we have a measured baseline to defend" claim must be re-grounded against the actual stage7-handoff record on the K1-rooted session.**

---

## 2. Strategic shape decision (Freeze → Inventory → Strip → Harness → Split)

Four paths considered:

### Path A — Split-in-place
- Take K1 fork as-is, split each header monolith into header+cpp, validate after each split.
- **Pro:** Incremental, bisectable, reversible.
- **Con:** Slow. Every split is a potential aggregate-init bomb. Have to validate after every change. Cruft of accumulated S2 design decisions doesn't get questioned — just modernized in place.
- **REJECTED:** doesn't address the real problem (codebase carrying S2-product assumptions for K1).

### Path B — Strip-then-Split (initially recommended by me)
- Aggressively delete features K1 doesn't need first; then split header monolith.
- **Pro:** Stripping is reversible per-feature; smaller surface to refactor.
- **Con:** Stripping changes behavior; have to validate stripped state against S2 baseline before splitting.
- **PROVISIONAL ADOPT, then REFINED by parallel team to Path B'** ↓

### Path B' — Freeze, Inventory, Strip, Harness, Split (parallel-team correction)
- Explicit Freeze step (operational hygiene I implicit-assumed).
- Explicit Harness step before Split (parallel team made this load-bearing; I had it as an "open decision").
- **Final adoption.**
- Further refined: my version split Strip into "Strip-isolated (pre-harness)" and "Strip-cross-cutting (post-harness, in Phase 5)" so harness gates the dangerous strip work.

### Path C — Modular interfaces refactor
- Define module boundaries first via explicit C++ interfaces; refactor module-by-module.
- **Pro:** Boundary-first; forces explicit thinking about responsibilities.
- **Con:** Designing interfaces before understanding what each subsystem does = building the wrong interfaces. SB codebase is not well-understood by any current participant.
- **REJECTED:** premature abstraction.

### Path D — Clean-slate rebuild
- Build fresh K1 firmware codebase from scratch with K1 fork as behavioral reference.
- **Pro:** Architectural cleanliness from day one.
- **Con:** Reproducing the validated reference costs exactly the trust we'd be discarding. Risk of "second-system effect." Risk of missing subtle behavior baked into the old code.
- **REJECTED:** the K1 fork at `99a730b7` IS the validated artefact; Strip-then-Split improves it; clean-slate replaces it.

---

## 3. Anti-pattern that must NOT happen

**Refactor into elegance at the expense of preserving behavior.**

The temptation when modernizing legacy embedded code is to apply current-best-practice C++ patterns — RAII, smart pointers, exceptions, templates, runtime polymorphism, dependency injection. Most of these don't fit K1's constraints:
- Real-time (audio chunk + LED frame budgets)
- Memory-constrained (PSRAM helps, but render hot path is no-heap)
- Deterministic execution (no exception support in typical embedded toolchains)
- No heap allocation in hot path

Right targets for K1:
- Explicit data flow (no hidden control flow)
- Static memory only in hot path
- Single owner per resource
- Minimal indirection (no virtual dispatch in hot path)
- Headers contain *declarations only*
- Globals consolidated to one TU (`src/core/globals.cpp` per existing rule)
- Module boundaries via include-direction discipline, not interface classes

**Captain's anchor:** "fit for further development." Not elegant. Not patterns-textbook. Behavior-preserved.

---

## 4. Three orthogonal regression surfaces (harness rationale)

Plan Agent 3 articulated this; I'm capturing the orthogonality argument here so K1-rooted session inherits it.

| Surface | Drift mode | Detector |
|---|---|---|
| AP — audio pipeline | DC bias, gain, follower envelope, spectral content | `dump_raw=` + `ap_stream=` |
| VP-static — deterministic render | Mode dispatch, palette mapping, framebuffer math | `vp_probe=` (existing in-tree machinery) |
| VP-live — audio-reactive render | Frame transport, dt scaling, position drift (WAVEFORM_FAST class) | `frame_dump=` with COM-slope metric |

WAVEFORM_FAST 1.60× drift is empirical proof that VP-static can't catch transport-drift bugs (same frames, wrong rate). COM-slope = derivative of centre-of-mass over time = catches transport drift exactly. Without it, the harness has a known blind spot the codebase has already exploited.

---

## 5. The aggregate-init preservation rule

The 2025-09-19 `incandescent_lookup` incident (recorded in K1 fork's project CLAUDE.md as a load-bearing rule):

```cpp
// ORIGINAL (in header) - WORKS
CRGB16 incandescent_lookup = { 1.0000, 0.4453, 0.1562 };

// "FIXED" (in .cpp) - COMPILES BUT BREAKS AT RUNTIME!
CRGB16 incandescent_lookup = { SQ15x16(1.0000), SQ15x16(0.4453), SQ15x16(0.1562) };
```

Same data, same target type, same compiler — runtime behavior different. The aggregate-init expression's *syntax* affects how the C++ compiler evaluates static initialization. Adding explicit constructors changes the initialization point and can silently regress runtime behavior with ZERO compile warnings.

**Mitigation rule in plan:** byte-identical initializer syntax preserved across header→cpp moves. Verification via `objdump -s -j .rodata` diff before vs after.

**Plus VP harness frame-hash gate** to catch any silent regression.

**AUDIT-FLAGGED: Plan claims `incandescent_lookup` lives in `led_utilities.h`. Audit says `constants.h:439`. K1-rooted session must source-verify and update all module-target claims that depend on its location.**

---

## 6. SS LED vs SS AP algorithm — Captain's clarification 2026-05-24

Captain stated:
- The 3 PWM indicator LEDs are unique to the SB-S2 "official" hardware and do NOT carry over to K1 at all.
- HOWEVER, the Sweet Spot AP algorithm (associated with the LEDs) MUST BE CAREFULLY HANDLED — it is hardwired and a functional part of the system's AP regardless of whether the physical LEDs are present.
- Captain not certain whether SS AP algorithm should or should not be removed — requires further investigation.

**Folded into the plan:**
1. Phase 0 gets a 6th planning artefact: `02-sweet-spot-investigation.md` — source-trace SS algorithm, identify consumers, classify each as LED-output-only or AP-load-bearing.
2. Phase 3 strip-set for SS = LED output code ONLY (PWM writes, pin assignments). SS AP algorithm UNTOUCHED.
3. Phase 2 inventory ratification: SS LED output STRIP-pending-investigation-confirmation; SS AP algorithm KEEP-PENDING.
4. The harness is the safety net: even if Captain later strips SS AP algorithm, harness detects whether removal regresses audio equivalence.

This is one of the most important design decisions in the plan and Captain owns it. K1-rooted session inherits the distinction.

---

## 7. The parallel-team correction (audit precedent)

Mid-session, a parallel team did source-verification against current K1 fork source and corrected several of my claims:

- I cited P2P sync and cochlear AGC as strip candidates from memory — they were already removed/replaced in source.
- I cited the SS LED hardware-doc-vs-source conflict.
- I missed the WAVEFORM_FAST evidence proving VP-by-eyeball insufficient.

**Concession discipline:** Memory Trust Freeze rule applies — my memory of K1-fork state is stale across compactions; the parallel team with direct K1-fork source access caught me using stale memory as fact. The contract worked as designed.

**What I should have done from the start:** every load-bearing source claim grounded in a current-source grep, not memory.

**What happened anyway in the final plan:** propagated Agent 1's `11 .h` count without cross-checking the doctrine gate's `19 .h` count. Same failure mode. Audit caught it. K1-rooted session: source-grep everything.

---

## 8. Why planning artefacts live in LightwaveOS, execution in K1 fork

Pattern from the PIO migration that worked:
- LightwaveOS_Official owned forensic audit, doctrine, migration plan (planning artefacts)
- K1 fork owned execution (commits, branches, tags)
- Cross-references explicit (K1 fork commits cite LightwaveOS plan SHAs)

Applied to refactor:
- Planning artefacts (forensic audit, feature inventory, SS investigation, architectural target, harness spec, phase plan) → `LightwaveOS_Official/docs/agent-outputs/analysis/k1-refactor-2026-05/`
- Execution (branches, commits, worktrees, code changes) → K1 fork at `/Users/spectrasynq/SensoryBridge-main 9/`

**AUDIT-FLAGGED: this placement creates the "harness baseline versioned in different repo from firmware it gates" weakness. K1-rooted session must decide: keep the LightwaveOS-side planning split AND find a different home for harness reference data, OR collapse harness baseline into K1 fork.**

---

## 9. Captain Decision Points consolidated (from final plan)

### Phase 0 (resolve before Phase 1):
- SS LED output: STRIP (default) / KEEP
- SS AP algorithm: KEEP-UNTOUCHED (default) / KEEP-WITH-LATER-REVIEW / STRIP
- `PHOTONS_CURVE_MODE`: keep `#ifdef` (3 modes) / hardwire to mode 2
- Lightshow mode roster KEEP/STRIP per mode (after Phase 0 audit confirms actual count)
- Music corpus: two pinned tracks (default) / no-music-MVP
- Worktree topology: per-phase + per-sub-phase children (default) / single-worktree branch-only

### Phase 2 (per item):
- KEEP/STRIP/DEFER for every feature in the ratified inventory
- KEEP/STRIP/DEFER for every one of the 141 serial commands [AUDIT: 186]

### Phase 3 (per commit):
- Sign-off on each strip commit group
- Visual smoke confirmation on WAVEFORM_FAST fix

### Phase 4:
- Freeze Baseline canonisation in `CANONICAL_MILESTONES.md`

### Phase 5 (per sub-phase):
- Merge approval to `refactor/main`
- Any envelope-drift exception requests (default: NO)
- Any harness-tolerance widening requests (default: NO)
- Any VISUAL deviation Captain spots that harness missed

### Throughout:
- `start_noise_cal` authorisation (Captain confirms verbal silence first)
- Hardware target identity verification before serial, upload/flash, erase, or device-write actions.
- Flash erase only when the validation lane requires it, with verified target identity and evidence recorded.

---

## 10. Methodology continuity argument

The methodology that produced "The Equivalent Port" in 2 hours applies to this refactor wholesale:

- Forensic audit first → K1-fork audit as prerequisite artefact (Phase 0 #1)
- Doctrine enforced → SB doctrine invoked before any non-trivial change
- Source-verification over empiricism → no "let's try it and see"; every mechanical move justified by citation
- Empirical capture infrastructure → dump_raw + new visual capture harness as regression gates
- Founder Execution Boundary → Captain owns product decisions (KEEP/STRIP); agents own execution
- Parallel SSA dispatch → for feature inventory, architectural target, harness design
- Phase plan before code → discipline applied at refactor scale

**But:** the PIO migration was bounded-scope toolchain delta. This is open-scope structural work. Methodology applies; effort envelope does not transfer.

**The right scale comparison:** the LightwaveOS-side modernization already partially done (`src/core/globals.cpp`, the `src/` tree restructure visible in gitStatus). Multi-cycle, visible scars, not finished. This is the same shape of work on a different codebase.

---

## 11. Things I got wrong (own them)

Per Captain's audit:

1. **Source-count claims propagated without cross-verification** — I had two source signals available (Agent 1: 11 .h, doctrine gate doc: 19 .h) and propagated Agent 1's without reconciling. The doctrine gate count was right. Audit confirms 19. Mode count: 9 vs 13. Strcmp: 141 vs 186. `incandescent_lookup` location: led_utilities.h vs constants.h:439.

2. **Self-contradiction on mode 7 Phase 1↔Phase 3 sequencing** — Plan said Freeze Baseline captures *corrected* mode 7 behavior, but the fix lands in Phase 3, AFTER Phase 1 Freeze. Logical impossibility I missed and the audit caught immediately.

3. **Equivalence numbers from conversation memory, not source-verified against stage7-handoff.md** — I treated Captain's verbal/text reports as canonical and never grounded the equivalence claim against the written stage7-handoff.md record. Audit says stage7-handoff.md contradicts the equivalence claim. K1-rooted session: read stage7-handoff.md, decide what's canonical.

4. **Per-commit harness × Captain-budget math** — Plan claimed ~2 day Captain budget. Per-commit harness gating across 40+ Phase 5 sub-phase commits, each requiring ~30 min Captain session = 20+ Captain hours minimum. Math doesn't close. K1-rooted session must re-budget honestly or change the harness operational model.

5. **Harness never proven to detect a real regression** — the plan asserts the harness will catch regressions, but it was never run against a known regression case before being designated as the gate. K1-rooted session should run the harness against a synthesized regression to confirm detection works.

6. **No off-machine backup specified** — the plan documented `backup/pre-refactor-20260525` as a branch on the same git repo as `refactor/main`. Both are on Captain's single machine. Any disk failure or repo corruption loses both. K1-rooted session should add off-machine backup.

7. **Harness baseline in different repo from firmware it gates** — auditing-the-gated-from-outside-the-gate-zone violates locality. K1-rooted session decides whether to centralise.

---

## 12. What's actually fit-for-purpose in this scoping

Things from this session that K1-rooted session should reuse:

- **Strategic shape (Freeze-Inventory-Strip-Harness-Split)** with parallel team's refinement — sound
- **Phase 0 6-artefact deliverable set** (forensic, inventory, SS investigation, architectural target, harness spec, phase plan) — sound structure
- **The three orthogonal regression surfaces** (AP / VP-static / VP-live) — sound concept
- **COM-slope as the transport-drift detector** — sound (mathematically catches WAVEFORM_FAST-class bugs)
- **Aggregate-init preservation rule + objdump verification** — sound (the 2025-09-19 incident is the worked example)
- **Strip(isolated) before Harness, Strip(cross-cutting) after Harness** — sound risk-classification
- **The 22 acceptance criteria** — sound (mostly mechanical / verifiable)
- **The anti-pattern list** (no header function bodies, no global defs in headers, no `#include` of `.cpp`, etc.) — sound
- **The methodology continuity** (forensic-first, source-verified, doctrine-enforced, parallel SSA) — sound

Things to NOT carry forward as-is:
- The specific count claims (11 .h, 9 modes, 141 strcmp, etc.)
- The specific source location claims (incandescent_lookup file, audio_transfer.h SS algorithm location)
- The "The Equivalent Port" framing without re-grounding against stage7-handoff.md
- The Phase 1↔Phase 3 mode 7 sequencing
- The ~2-day Captain budget
- The Phase 4 "harness Hardening" placement (final plan moved harness firmware to Phase 1; this compounded the mode 7 problem)

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | claude-code (Opus 4.7) | Persisted session-context scoping notes, rejected alternatives, design rationales. Audit-flagged claims inline. Created during handoff to K1-rooted session. |
