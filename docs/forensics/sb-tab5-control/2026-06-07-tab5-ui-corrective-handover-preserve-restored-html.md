# SensoryBridge Tab5 UI Corrective Handover - Preserve Restored HTML

Date: 2026-06-07
Working root: `/Users/spectrasynq/SensoryBridge-main 9`

## Purpose

This is the handover for the next agent after Captain rejected the broad V2
overhaul of the Tab5 Zone Composer HTML.

The next task is not a redesign. It is a preservation-first, narrow repair pass
on the previously preferred design. Captain explicitly said the previous version
was significantly superior except for the annotated defects.

## Protected Source

Protected restored HTML:

- `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`
- Observed SHA-256 after Captain's CMD-Z restore:
  `93956b417bd7d7079fe30fa197e722953a4324de80268b5c14dbbf94273a1044`
- Observed byte size: `44564`
- Observed git state: untracked in `git status --short --untracked-files=all`

If this hash/size no longer matches, stop and tell Captain before doing UI work.
Because the file is untracked, do not assume git can recover it if overwritten.

## Non-Negotiable Process Guardrails

1. Do not edit or overwrite
   `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`
   without explicit Captain approval.
2. Any change draft must be a sibling file, for example
   `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal-annotated-fix-draft.html`.
3. State exact target files before applying any patch.
4. Do not use any `v2`, `pixel-lab`, `reset`, or "final" overhaul artefact as
   the new design direction. Those are rejected or cautionary evidence unless
   Captain explicitly reinstates them.
5. Do not replace unannotated regions. Preserve the current visual language,
   hierarchy, typography, colour logic, and overall composition unless the
   annotated defect directly requires a local adjustment.
6. Do not claim Tab5 hardware proof unless the design has been viewed or tested
   on the physical Tab5.
7. Do not invent live backend truth. If status is simulated, remove it, mark it
   as simulated, or leave it for discussion.

## Evidence To Preserve

The restored HTML still contains the original preferred Composer structure:

- Header with `< BACK`, `LIGHT COMPOSER`, `K1 AP`, `WS LIVE`, `100 FPS` at
  `sb-tab5-zone-composer-proposal.html:1000-1008`.
- Top surface selector buttons `PRIMARY EDGE`, `SECONDARY EDGE`, `SMART
  DIRECTOR` at `:1010-1014`.
- Centre-origin LGP field and ticks `0`, `79|80`, `159` at `:1016-1033`.
- `PRIMARY EDGE PARAMETERS` and five parameter cards at `:1036-1072`.
- Lower overview cards for Primary Edge, Secondary Edge, and Smart Director at
  `:1074-1107`.
- Footer status strip `SELECTED: PRIMARY EDGE`, `QUEUE EMPTY`, `SAVE DELAYED`,
  `AUDIO SEMANTIC LIVE` at `:1109-1114`.

Existing screenshot evidence to preserve:

- `sb-tab5-zone-composer-proposal-tab5-composer.png`
- `sb-tab5-zone-composer-proposal-tab5-mix.png`
- `sb-tab5-zone-composer-proposal-tab5-health-final.png`
- `sb-tab5-zone-composer-proposal-tab5-protocol.png`

Those four Tab5 crop screenshots were observed at `1205x678`, not exact
`1280x720`. Treat them as review evidence, not pixel-truth proof.

Rejected/cautionary evidence also exists:

- `sb-tab5-zone-composer-v2-pixel-lab-home-final.png` observed at `2110x984`.
  It is not the accepted design baseline.
- `docs/forensics/sb-tab5-control/2026-06-07-zone-composer-proposal-v2-element-rationale.md`
  may contain useful warnings, but it does not override Captain's latest
  direction to preserve the previous design and fix only annotated errors.

## Annotated Defects To Fix Narrowly

Use Captain's annotated screenshot as the delta list. Fix these locally; do not
solve them by replacing the whole screen.

1. Header border visibility.
   - Captain asked where the header border is.
   - Current CSS places `.header` at `left:20px; top:10px; width:1240px;
     height:50px` with no visible structural border at `:164-173`.
   - Narrow fix: add or strengthen a visible header boundary without moving the
     whole composition unless spacing requires it.

2. Top surface selector purpose.
   - Captain asked what the point of the `PRIMARY EDGE`, `SECONDARY EDGE`, and
     `SMART DIRECTOR` buttons is.
   - Current `.mode-row` is `36px` high and uses buttons at `:245-265`; JS only
     changes selected title/card state at `:1421-1442`.
   - Narrow fix: decide with Captain whether they remain surface selectors,
     become actual page/action buttons, or are visually demoted/removed. Do not
     delete them without discussion.

3. LED strip readback/data.
   - Captain asked whether the hero strip can be fed LED data.
   - Current `.lgp-field` is a decorative/simulated field at `:311-323` and the
     DOM region is at `:1016-1033`.
   - Narrow fix: label as simulated, design an optional readback contract, or
     leave as static preview pending backend proof. Do not imply live LED data.

4. Parameter change mechanisms.
   - Captain asked how the user changes Mode, Palette, Photons, Chroma, and
     Mood.
   - Current cards are `<article class="param-card">` with 8px visual bars at
     `:1041-1072`; CSS bars are `height:8px` at `:475-481`.
   - Narrow fix: add clear affordance for each parameter. Candidates for
     discussion: Mode/Palette as large tap/step or picker entry; Photons/Chroma/
     Mood as true sliders or stepper controls. Do not silently choose all
     sliders.

5. Lower overview cards may be buttons.
   - Captain suggested Primary Edge, Secondary Edge, and Smart Director lower
     panels might make more sense as buttons.
   - Current lower cards are `<article>` summaries at `:1074-1107`.
   - Narrow fix: prototype only affordance treatment and explain whether each is
     read-only, navigational, or a command. Do not rebuild the overview section.

6. Footer gap.
   - Captain asked why there is a large gap under the footer/status strip.
   - Current footer DOM is at `:1109-1114`; local geometry needs visual audit.
   - Narrow fix: tighten or visually justify the footer area only. Do not use
     this as reason to rebuild the footer into a different navigation system.

7. Fake live/status claims.
   - Current header says `WS LIVE` at `:1005`; footer says `AUDIO SEMANTIC LIVE`
     at `:1113`.
   - Narrow fix: remove, mark simulated, or replace with truth-neutral wording
     until SB firmware/backend proof exists.

## Do Not Touch Without Approval

- Do not overwrite the protected HTML.
- Do not replace the screen architecture.
- Do not introduce a two-page primary navigation model unless Captain asks.
- Do not demote or remove the overall Zone Composer visual style.
- Do not replace fonts, colour palette, background, or broad card grammar.
- Do not delete the LGP hero strip.
- Do not turn all readouts into controls without explaining control type and
  failure state.
- Do not add WiFi password saving, profile slots, audio feedback, haptics, OTA,
  reset, factory actions, or network selection in this pass.
- Do not use popups/dropdowns as a shortcut unless their trigger, escape path,
  and failure state are documented.
- Do not claim any WebSocket, REST, audio semantic, or LED readback behaviour is
  live unless verified against source/runtime evidence.

## Pixel Reality Constraints

Relevant source-backed constraints from the local pixel contract:

- The target is a `1280x720` logical panel on a 5-inch display.
- `44px` is only about `3.80mm`; it is not a primary finger target.
- `72px` is about `6.23mm`; this is a compact floor, not comfort.
- Borders used for structure should be `2-3px`; `1px` is decorative.
- Every visible element must have exactly one reason to exist.
- Exact `1280x720` render proof is required; browser-scaled views are advisory.

References:

- `docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md:29-76`
- `docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md:78-105`

## Current HTML Red-Team Evidence

Existing read-only red-team evidence says the current HTML is visually useful
but not yet a firmware UI baseline:

- Action-looking controls are mostly inert display widgets.
- `.surface-button` is `36px` high, `.back` and `.status-card` are `44px`, and
  parameter bars are `8px`.
- Existing screenshots are not exact `1280x720` proof.
- The centre-origin marker survives and should be preserved.
- AP-only language survives and does not visibly violate the K1 AP-only rule.

Reference:

- `docs/forensics/sb-tab5-control/agents/current-html-pixel-redteam.md:35-147`

## Required Next Workflow

1. Verify protected HTML hash and size before starting.
2. Open/render the protected HTML read-only.
3. Produce a small delta table from Captain's annotated screenshot:
   issue, affected element, minimal fix, control type, bounds, and proof method.
4. Ask Captain to confirm the proposed fixes before code changes if any fix
   changes button/function/menu handling.
5. Create a new sibling draft HTML only.
6. Capture exact `1280x720` evidence for original and draft.
7. Present side-by-side comparison and explain every changed element.
8. Do not replace the protected original without explicit approval.

## SSA Consumption Notes

Captain requested SSA support. In this session no direct SSA execution tool was
available in the active callable tool list. Two requested read-only SSA briefs
were therefore consumed as constraints and refuted/rechecked by the orchestrator
against local files where possible.

### Evidence Inventory Brief - Consumed As Provisional Context

Evidence to preserve:

- Current restored HTML and its hash.
- Original Composer screenshot evidence.
- Annotated screenshot defects.
- Existing pixel contract and red-team notes.

Narrow fixes:

- header border, top button purpose, LED readback truth, parameter affordances,
  lower-card affordance, footer gap, fake live labels.

Do not touch:

- protected HTML, broad architecture, rejected V2 artefacts, unannotated design
  language, live/backend claims.

### Red-Team Brief - Return Contract

STATUS: VERIFIED_WITH_LIMITS
CLAIM: The handover must forbid overwriting and broad redesign; only narrow
annotated fixes are authorised.
EVIDENCE: This handover plus restored HTML hash and local line references.
COMMAND: Re-run `shasum -a 256 docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
METHOD_RISK: Conversation context is not fully reconstructable from disk, so
Captain's attached screenshot and latest instruction remain primary.
NEXT: Preserve, draft sibling, validate visually, then ask before replacement.

## Model Use

- `/thinking-model-router`: classified this as Product plus Risk plus
  Architecture, with Risk dominant because the failure mode is destructive
  overwrite and design drift.
- `/thinking-model-combination`: used a sequential combination of evidence
  inventory, via negativa, red-team, and narrow-scope decision discipline.
- `/ssa-management`: treated all SSA-style outputs as hypotheses until locally
  rechecked; no SSA prose is promoted above Captain's latest instruction.

## Final Instruction For The Next Agent

Preserve the restored superior design. Fix only Captain's annotated defects.
Discuss button/function/menu handling before implementation. Never overwrite the
protected HTML unless Captain explicitly approves replacement.
