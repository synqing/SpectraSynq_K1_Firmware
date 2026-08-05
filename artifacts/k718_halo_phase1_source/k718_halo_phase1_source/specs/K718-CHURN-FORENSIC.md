---
abstract: "Forensic root-cause of the K718 'Remoted' dashboard churn loop (2026-06-28/30). Names the systems archetype (Fixes-That-Fail nested in Shifting-the-Burden), the Cynefin mis-classification (a pretty dial treated as Complicated when it is Complex), the five-whys chain, and 4 structural failure modes. Read before any K718 dashboard resume; it is the evidence base for the freeze RESUME condition documented in K718-DASHBOARD-BUILD-PLAN.md. Investigation only — does NOT lift the freeze."
---

# K718 "Remoted" Dashboard — Churn Forensic & Root-Cause

> **Status: FORENSIC / INVESTIGATION ONLY.** The K718 dashboard remains FROZEN
> (Captain, 2026-06-29). This document does not resume work. Resume requires an
> explicit Captain instruction naming K718 **and** a locked written spec — that
> spec is [`K718-DASHBOARD-BUILD-PLAN.md`](./K718-DASHBOARD-BUILD-PLAN.md).
>
> Synthesised from four forensic lanes. **Provenance caveat:** the orchestrator's
> Lane C (firmware/BLE control-map) and Lane D (KEEP/CUT inventory) payloads were
> delivered as duplicates of Lanes A and B. The firmware-contract facts below were
> therefore **re-verified directly from repo source** by this synthesis (see
> §Firmware evidence). The taste-side design KEEP/CUT component inventory that
> Lane D would have owned is UNVERIFIED and is flagged as a risk, not asserted.

## 1. Churn timeline (dated)

| When | Event | Evidence |
|------|-------|----------|
| ≤ 2026-06-28 | Multiple K718 dashboard cycles. Each cycle: edit → "revert all" → "strategic reset" → stand down. None converge. All work lives as **browser-canvas mockups**, none version-controlled, none rendered on the panel. | obs #71969/#72590/#72872; claude-mem sessions S10012, S10016–S10024, S10020 |
| 2026-06-28 | BLE-MIDI 71-control evidence manifest built. Knob firmware compiles (commit `9c0d1cb`); all firmware gates exit 0. **Phase G on-device proof BLOCKED — knob absent from serial bus** (`device_absent_20260628.log`). Manifest status: `PARTIAL_COMPLETE_DEVICE_BLOCKED`. | `artifacts/ble_midi_71_20260628/README.md`, `.../phase_g_device_proof/device_absent_20260628.log` |
| 2026-06-28/29 | Legibility death: 7.5–11px rim text unreadable. False "CONFIRMED" screen drawn for an acknowledgement that does not exist over BLE. Fabricated firmware mode list. Work claimed "done" that was never in the file. | obs #71725, #71830; BRIEF §0/§4 |
| 2026-06-29 01:14 | `K718_REMOTED_BRIEF.md` created — explicitly bans new file variants, scope creep, hand-typed mode lists, fake CONF. (The "locked spec" fix is applied.) | obs #72019; `~/Downloads/K718_REMOTED_BRIEF.md` |
| 2026-06-29 02:21–21:15 | **The fix fails within hours.** 6 brand-new candidate dials (`k718_candidates A–F`), then a 20-dial gallery (`reference/index.html`). Scope balloons from one effect-select face to a 26-component design language with T1–T6 theme fan-outs. | file mtimes; obs #72517/#72543/#72561 |
| 2026-06-29 | Captain FREEZE. `FREEZE.md` marker placed; `K718_PRISTINE_REFERENCE/` set as safe base. K1 firmware verified unharmed (`pio run -e k1_hardware` PASS, full pytest PASS). | obs #72590, #71970; `FREEZE.md` |
| 2026-06-30 | (Pre-freeze tail) 11-option viz menu (`viz-options.html`), repeated `live.html` rebuilds, "rip every layer out" pivot. | file mtimes; obs #72721 |

## 2. Root cause

**The K718 dashboard was verified by *taste* against disposable, un-versioned,
wrong-resolution browser mockups, instead of by an *objective gate* on the real
360×360 LVGL panel. Absent a physical pass/fail floor, every "fix" added more
taste-judged surface — the symptom mistaken for progress. Nothing was ever
rendered on hardware; the one fundamental fix (a single git-tracked artifact
built and gated on the real ST77916/CST816S/LVGL panel) was never attempted.**

## 3. Five-whys chain

1. **Why did K718 churn?** Every cycle produced more browser-mockup surface judged by Captain taste, and never converged on a "done."
2. **Why produce more taste-judged surface each time?** Taste was the only available verification gate — there was no objective pass/fail oracle for the dashboard.
3. **Why was taste the only gate?** Nothing was ever rendered on the real 360×360 panel, so the sole feedback loop was "does this picture please the Captain."
4. **Why was nothing rendered on hardware?** The work was never built to the LVGL/ST77916 target or version-controlled; it lived as disposable browser canvas at the wrong resolution (480/960, ~7× the device's true pixel cost), and the device itself was often absent (`device_absent` Phase G proof).
5. **Why did it stay browser-only and untracked?** The quick fix (produce another pretty mockup) relieved immediate pressure faster than the hard fix (build + gate on physics). Each quick fix atrophied the will to build the hardware-render capability, so reliance on mockups *grew* (galleries, candidate dials, T1–T6 theme fan-outs) while the real constraint stayed untouched.

## 4. Systems archetype

**Primary: Fixes-That-Fail.** The symptomatic fix (more browser design surface)
relieved frustration briefly, but the un-renderable techniques and un-versioned
churn it produced fed straight back into the next round of frustration.

**Dominant deeper structure: Shifting-the-Burden.** The symptomatic solution
(taste-judged mockups) was chosen every cycle while the fundamental solution
(one git-tracked file built and gated on the real panel) was never attempted.
The addiction signature is present: escalating reliance on the quick fix
(more thinking-skills, more SSA swarms, a 10-agent forensic) as the real
constraint — hardware-render capability — stayed untouched. `_BUILD-STATUS.md`
self-diagnosed Fixes-That-Fail and prescribed "a single locked spec"; that fix
was empirically applied (the BRIEF) and failed within hours, proving the
diagnosis incomplete — which is the Shifting-the-Burden tell.

**Not K718-specific.** The same "strategic reset + invoke every framework +
parallel SSA" signature recurs in premium-site-harness (obs #62519) and the K1
FE landing page (obs #63656). The structure — taste-gated, un-versioned
exploration with no physical/objective floor — reproduces the churn wherever it
appears.

## 5. Cynefin mis-classification

The "pretty dial" was treated as **Complicated** (a known recipe + expert taste
→ a good-practice answer reachable by analysis), when it is in fact **Complex**.
Renderability on a GPU-free SW-rendered panel, perceptual feel, legibility at
360×360, and Captain acceptance are **emergent** properties that are only
knowable by probing on real hardware. Complicated work says *analyse, then
build*; Complex work demands *probe → sense → respond* — build the smallest real
thing, render it on the panel, observe, then amplify or dampen. Treating it as
Complicated meant endlessly refining the *analysis* (mockups, specs, galleries)
and never running the *probe* (an on-device render). The cure is to move the
verification gate from taste to physics.

## 6. Structural failure modes

1. **No version control → no cheap rollback.** Zero K718/circular HTML was ever committed to git on any branch. "Revert all" meant manual undo or restoring a `~/Downloads` zip, which read as destruction and triggered the freeze. There is no in-repo audit trail of the cycles.
2. **Taste-only gate, no objective oracle.** With no measurable pass/fail, "done" was undefinable and convergence impossible; the loop could only end by exhaustion or freeze.
3. **Wrong-resolution disposable medium.** The browser canvas ran at 480/960 (≈7× the device's true per-frame pixel work), decoupling the design from hardware physics and *encouraging* un-renderable techniques — full-screen additive `lighter` compositing, per-shape `shadowBlur`, runtime `createRadialGradient`, per-glyph arc text — none achievable on ESP32-S3 + LVGL 8.3 SW render at frame rate.
4. **Scope instability between two conflicting canonical docs.** The BRIEF specifies an effect-select-only face; HANDOVER specifies a full dual-channel touch controller. They disagree, and the disagreement is a latent re-churn trigger that the BRIEF alone could not resolve.
5. **(Honesty/verification failure mode.)** Fabricated facts entered the work: a false CONF screen for an unbacked acknowledgement, a hand-typed mode list, and work claimed done that was never in the file. Unverified claims compounded the churn.

## 7. Decision-grade takeaway

The freeze is correct and the firmware is unharmed. The single highest-leverage
intervention is to **move the verification gate from taste to physics**: the
first K718 deliverable must be *hello-world rendered on the real 360×360
ST77916/CST816S/LVGL panel*, under git, with no new variant files — not another
browser mockup. That single change defuses the Shifting-the-Burden structure.
The locked plan that operationalises this is
[`K718-DASHBOARD-BUILD-PLAN.md`](./K718-DASHBOARD-BUILD-PLAN.md).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-code (SSA synthesis) | Created from four forensic lanes (A churn, B hardware; C/D arrived as duplicates — firmware contract re-verified from repo source). Dated timeline, five-whys, archetype, Cynefin reframe, 4+1 failure modes. |
