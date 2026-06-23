# SB Tab5 Zone Composer Resume Guarded Handover

Date: 2026-06-07
Working root: `/Users/spectrasynq/SensoryBridge-main 9`
Protected source-truth HTML: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`
Status: resume handover after failed overwrite and Captain CMD-Z restoration.

## Purpose

This is a guardrail handover for the next agent. Captain does not want a new
concept. Captain wants the restored, preferred Zone Composer proposal protected,
then the specific annotated defects fixed narrowly and visually validated before
any broader control/menu decisions are made.

## Evidence To Preserve

- Preserve `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html` as the current source truth. It is the version Captain restored manually via CMD-Z after the overwrite failure.
- Preserve the existing failure handover:
  `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-handover-after-prototype-failure.md`.
  It records the overwrite error, the source-truth HTML, and the "fix annotated errors only" direction.
- Preserve the current proposal screenshot set in the repo root:
  `sb-tab5-zone-composer-proposal-*.png`. These are evidence of the preferred-but-defective visual direction.
- Preserve the rejected overhaul evidence in the repo root:
  `sb-tab5-zone-composer-v2-pixel-lab-*.png` and
  `sb-tab5-zone-composer-v2-home-snapshot.md`. Treat these as rejected artefacts unless Captain explicitly reinstates them.
- Preserve red-team evidence in:
  `docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md`.
  It source-backs touch-size, fake-control, scaled-screenshot, and hierarchy risks.
- Preserve pixel discipline in:
  `docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md`.
  It defines exact `1280x720` evidence, physical touch-size expectations, and hit-map requirements.
- Preserve Zone Composer donor evidence in:
  `docs/forensics/sb-tab5-control/agents/zone-composer-design-history.md`.
  It explains why the original direction was strong: LED hero, centre marker, selected surface params, and overview cards.

## Annotated Defects To Fix Narrowly

The following are the narrow defects Captain annotated on the screenshot. Fix
these without redesigning unrelated regions.

1. Header border visibility.
   Source: `.header` is positioned at `left: 20px; top: 10px; width: 1240px; height: 50px`
   but has no structural border in the current CSS
   (`sb-tab5-zone-composer-proposal.html:164-169`). Fix the missing/unclear
   header boundary without changing the entire header composition.

2. Meaningless top selector buttons.
   Source: the top buttons are `PRIMARY EDGE`, `SECONDARY EDGE`, and
   `SMART DIRECTOR` (`html:1011-1013`), with styling at `html:245-263`.
   JavaScript only changes selected-surface title/colour/card styling
   (`html:1395-1442`). Decide narrowly whether these are state selectors,
   navigation, or should be converted into a clearer selected-surface control.
   Do not remove the whole selected-surface grammar without discussion.

3. LED data/readback question.
   Source: the centre LGP strip is a static CSS/DOM visual (`html:311-350`,
   `html:1024-1032`). Captain asked whether this can be fed LED data. Treat it
   as an implementation/data-source question: either label it schematic, or
   propose a real readback/feed path separately. Do not pretend it is live.

4. Parameter cards need change mechanisms.
   Source: Mode, Palette, Photons, Chroma, and Mood are `article.param-card`
   readouts (`html:1039-1072`) with static bars (`html:475-492`), not real
   controls. Fix the affordance mismatch. Options to discuss: stepper for Mode
   and Palette, slider or large +/- for Photons/Chroma/Mood, or make cards open
   dedicated control overlays. Do not scatter duplicate controls elsewhere.

5. Lower cards may become buttons.
   Source: the Primary Edge, Secondary Edge, and Smart Director lower panels
   are `article.overview-card` blocks (`html:1076-1106`), not buttons. Captain
   suggested they may make more sense as buttons. Prototype only this exact
   question if approved: cards as large surface-selection/detail-entry buttons,
   while preserving the existing visual hierarchy.

6. Footer gap.
   Source: `.footer` is `top: 638px; height: 38px` (`html:581-586`), leaving a
   visible dead area below the footer/status strip in the 720px canvas. Fix the
   gap or make the footer occupy the intended footer band. Do not rework the
   entire screen around a new footer system unless Captain approves.

7. Fake-live/status truth.
   Source: `WS LIVE` appears in the header (`html:1005`) and `AUDIO SEMANTIC
   LIVE` appears in the footer (`html:1113`). Current SB Tab5 work is a visual
   proposal/control concept, not proven live wireless SB telemetry. Either mark
   simulated/API-needed or remove live claims in the narrow draft.

## Do Not Touch Without Approval

- Do not overwrite `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
- Do not use the rejected V2/pixel-lab overhaul as the new baseline.
- Do not redesign the screen, replace the visual language, change page count,
  or collapse the preferred Zone Composer grammar.
- Do not "improve" unannotated areas because they look suboptimal.
- Do not edit existing evidence files when a new checkpoint/handover will do.
- Do not claim Tab5 hardware proof from browser screenshots.
- Do not claim WebSocket, REST, live LED readback, audio semantic live data, or
  K1 wireless control unless source-backed and runtime-validated.
- Do not introduce WiFi STA/provisioning UX. K1 is AP-only.
- Do not add calibration/reset/destructive controls to the main performance
  surface without a guarded flow and Captain approval.
- Do not replace discussion with implementation. First produce a delta table and
  exact `1280x720` visual evidence.

## Required Next-Agent Workflow

1. Re-read this file and
   `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-handover-after-prototype-failure.md`.
2. Verify current git status before touching anything. The protected HTML has
   been untracked in prior checks, so git may not save a mistake.
3. Record the protected HTML byte size and hash in a new checkpoint.
4. Render the protected HTML read-only at exact `1280x720`.
5. Produce a delta table for the seven annotated defects above:
   issue, source element, proposed minimal fix, exact file to create/edit,
   visual validation method, and whether Captain approval is required.
6. If implementation is approved, create a sibling draft only, for example:
   `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal-annotated-fix-draft.html`.
7. Capture side-by-side exact `1280x720` screenshots of protected original and
   draft.
8. Explain every changed element: why it exists, control type, exact bounds,
   touch target size, label handling, alignment, and rejected alternatives.
9. Ask Captain before replacing or renaming the protected original.

## SSA Guardrails From Conversation

- Verdict defaults to `NOT_VERIFIED` unless backed by direct conversation or
  source evidence.
- The overwrite error must not be sanitised. It is the load-bearing reason this
  handover exists.
- The restored HTML is source truth because Captain explicitly restored it.
- The requested direction is narrow fixes plus discussion, not a new design.
- Any SSA or assistant output is provisional until the orchestrator checks the
  file paths and visual evidence directly.

## Model Use For This Handover

- `/thinking-model-router`: routed this as Product plus Risk plus System
  Diagnosis.
- `/thinking-model-combination`: combined Jobs-to-be-Done, First Principles,
  Pre-mortem/Red Team, and Via Negativa.
- `/ssa-management`: treated the user-provided SSA briefs and existing agent
  evidence as guardrail hypotheses; final recommendations were re-checked
  against local source files before writing this handover.

