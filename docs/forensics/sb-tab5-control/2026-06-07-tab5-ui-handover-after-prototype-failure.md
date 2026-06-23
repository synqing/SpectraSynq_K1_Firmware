# SensoryBridge Tab5 UI Handover After Prototype Failure

Date: 2026-06-07  
Working root: `/Users/spectrasynq/SensoryBridge-main 9`  
Protected source-truth HTML: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`

## Situation

Captain asked for the existing Tab5 Zone Composer proposal to be reviewed against strict pixel-match, visual hierarchy, control-type, label, alignment, secondary-page, edge-case, audio, input-feedback, and user-settings concerns.

The agent incorrectly treated that critique as permission to overhaul the proposal and overwrote `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`. Captain rejected the result as chaotic and unusable, then restored the prior version manually via CMD-Z. That restored HTML is now the protected design source for the next pass.

This handover exists to prevent the next agent from repeating the same failure.

## Immediate Non-Negotiables

1. Do not overwrite `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
2. Do not "improve", redesign, simplify, modernise, or recompose unannotated regions.
3. Preserve the previous design direction. Captain explicitly said the previous version was significantly superior except for the annotated errors.
4. Any next UI revision must be created as a separate sibling draft file, for example `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal-annotated-fix-draft.html`.
5. State the exact file paths before making any edit. If the edit touches anything except a new draft or a handover/checkpoint, stop and ask Captain.
6. Treat all layout and behaviour claims as unproven until source-backed and visually validated at 1280x720.
7. Do not claim Tab5 hardware proof unless the design has actually been viewed on the Tab5 device or otherwise validated against the real panel.
8. Use British English in docs, comments, labels, and UI strings.
9. Hard hash stop: if the protected HTML hash differs from the audit hash in
   [Final Audit Snapshot](#final-audit-snapshot), stop and ask Captain whether
   the restored source truth changed before doing anything else.
10. Write-target denylist: the protected HTML must not appear as an
    `apply_patch` target, shell redirection target, copy destination, formatter
    target, browser-save target, generated-output path, or bulk rewrite target.

## Current Local State Observed

This handover was written after a local check showed:

- `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html` exists.
- The protected HTML was listed as untracked by `git status --short` at the time of checking.
- The handover path `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-handover-after-prototype-failure.md` now exists as a new checkpoint file.
- The protected HTML currently identifies itself as `SensoryBridge Tab5 Touch Controller - Zone Composer Adaptation`.
- The restored design still contains the previous known issues at source level:
  - `LIGHT COMPOSER` title: `visual/sb-tab5-zone-composer-proposal.html:1002`
  - fake `WS LIVE`: `visual/sb-tab5-zone-composer-proposal.html:1005`
  - selected heading `PRIMARY EDGE PARAMETERS`: `visual/sb-tab5-zone-composer-proposal.html:1038`
  - footer strings `QUEUE EMPTY`, `SAVE DELAYED`, `AUDIO SEMANTIC LIVE`: `visual/sb-tab5-zone-composer-proposal.html:1111-1113`
  - four side/pitch-deck navigation buttons: `visual/sb-tab5-zone-composer-proposal.html:1308-1311`

Because the protected HTML was untracked in that check, do not assume git can recover it if overwritten. Verify current git status before doing anything else.

## Captain's Annotated Critique To Fix, Not Overhaul

The next agent should use Captain's annotated screenshot and comments as the delta list. The known issues called out were:

1. Header border visibility: Captain asked where the header border is. Fix border visibility without reworking the whole header.
2. Header/footer geometry: borders must be visible all around and not clipped by the screen edge.
3. Bottom footer gap: Captain asked why there is a large empty gap under the footer/status strip. Fix the footer spacing or justify it visually.
4. Dead top buttons: Captain challenged the purpose of the `PRIMARY EDGE`, `SECONDARY EDGE`, and `SMART DIRECTOR` buttons. Do not delete the whole structure automatically; decide whether they should be actual navigation/actions, visual state selectors, or removed after discussion.
5. LED strip data question: Captain asked whether the central strip can be fed LED data. Treat this as a design/implementation question, not decorative licence.
6. Parameter cards: Captain asked how the user changes Mode, Palette, Photons, Chroma, and Mood. The cards currently look like readouts but imply controls. Fix affordance clarity.
7. Lower panels: Captain suggested the lower Primary Edge, Secondary Edge, and Smart Director summaries may make more sense as buttons. Discuss and prototype this narrowly rather than redesigning the screen.
8. Visual hierarchy: apply hierarchy to existing elements first. Do not solve hierarchy by replacing the design language.
9. Alignment and label handling: inspect all labels and values at exact 1280x720; check overshoot, consistency, legibility, and standardised spacing.

## What Not To Use As Baseline

Do not use any overwritten chaotic V2 HTML as the new direction. If screenshots or files named around "v2", "final", "pixel-lab", or "reset" exist, treat them as rejected analysis artefacts unless Captain explicitly reinstates them.

The planning document `docs/forensics/sb-tab5-control/2026-06-07-zone-composer-proposal-v2-element-rationale.md` can be mined for cautionary constraints, but it must not override Captain's latest direction: restore the previous design and fix annotated errors only.

Also do not use `docs/forensics/sb-tab5-control/visual/sb-tab5-touch-mvp.html`
as the baseline. It is adjacent evidence only. The protected source-truth
visual direction is `sb-tab5-zone-composer-proposal.html` at the audit hash
listed below.

## Recommended Next Workflow

1. Re-read project instructions:
   - `AGENTS.md`
   - `.claude/CLAUDE.md`
   - `docs/spec-index.md`
2. Verify the protected HTML exists and record its current byte size/hash in the next checkpoint.
3. Open or render the protected HTML read-only at exact 1280x720.
4. Compare it against Captain's annotated screenshot and produce a delta table:
   - issue
   - affected element
   - proposed minimal fix
   - file to be created or edited
   - visual validation method
   - whether Captain approval is needed before implementation
5. Stop and get Captain's approval on the delta table before creating any draft
   HTML. Do not assume approval from the existence of this handover.
6. If Captain approves the delta table, create a new sibling draft HTML only.
   Do not overwrite the protected proposal.
7. Run a 1280x720 screenshot pass on the draft and the protected original.
8. Present side-by-side visual evidence and a short explanation of every changed element.
9. Ask Captain to choose whether the draft should replace the protected original. Do not replace it without explicit approval.

## Minimal-Fix Definition

For this lane, "minimal fix" means:

- Do not move, resize, restyle, rename, regroup, or delete unaffected elements.
- Header-border and footer-gap changes should be local CSS fixes unless Captain
  approves a layout change.
- If a control-affordance issue requires a choice between button, segmented
  control, slider, stepper, picker, or read-only card, present that choice in
  the delta table first. Do not silently implement the choice.
- The top surface buttons and lower overview cards are discussion targets, not
  automatic conversion targets.
- The LED strip readback question is a capability question. If live LED data is
  not wired, label it `schematic` or leave it as visual orientation only.

## UI Decision Discipline For The Next Pass

For every changed screen element, document:

- why it exists
- whether it is read-only, navigational, momentary, toggle, segmented, stepper, slider, picker, or guarded action
- exact bounds in pixels
- touch target size
- label size and overflow handling
- value alignment
- why it is placed left, centre, or right
- what the rejected alternatives were
- what visual proof was captured

Do not add elements because there is free space. Empty space is only valid if it improves hierarchy, touch accuracy, or visual breathing room.

## Source-Truth Boundaries

The proposed Tab5 UI is currently a concept/prototype lane, not a proven wireless control implementation. Do not claim any of the following without source-backed proof:

- WebSocket live control exists on SB firmware.
- REST API parity exists between firmware-v3 and SB firmware.
- Tab5 can already control SB firmware wirelessly.
- LED preview is fed by real K1 LED output.
- Audio semantic values are live.
- Settings such as WiFi password saving, user profile slots, audio feedback, or haptic feedback are implemented.

If a status is simulated, label it as simulated or omit it.

Reject or relabel any UI string containing these ideas unless source-backed:
`LIVE`, `Connected`, `100 FPS`, `QUEUE`, `SAVE`, `semantic`, `backend`,
`WebSocket`, `REST`, `AP control`, `wireless control`, `calibrated`, or
`persisted`. The protected original contains some of these strings as known
defects; the next draft must not promote them as truth.

## Read-Only SSA Risk Checklist

The requested read-only SSA returned the following risk checklist, consumed as provisional guardrail context:

### Non-negotiables

- Prompt-backed only: original HTML was restored by Captain via CMD-Z; do not treat the overwritten prototype as valid current state.
- Do not overwrite `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
- Any next iteration must be a separate draft file only, clearly named as experimental.
- Preserve the previous superior design; fix only Captain's annotated errors.
- All claims about behaviour, layout, or correctness must be source-backed and visual-validated.

### Likely Failure Modes

- Using the failed overhaul as the baseline and compounding the wrong design direction.
- Editing the restored file directly, destroying Captain's recovery point.
- "Improving" unannotated areas and losing the parts Captain preferred.
- Making confident UI claims without screenshot/visual comparison evidence.
- Redesigning the wrong surface or solving a broader Tab5 problem than requested.

### Recommended Next Action

- First inspect the restored HTML and Captain's annotated critique, then identify only the annotated deltas.
- Create a separate draft sibling file for changes; leave the restored proposal untouched.
- Validate by side-by-side visual review against the restored design before making any handover claim.

## Model Use

This handover used:

- `/thinking-model-router`: product plus risk plus system diagnosis.
- `/thinking-model-combination`: Jobs-to-be-Done, first principles, pre-mortem/red-team, and via negativa.
- `/ssa-management`: two read-only SSAs were spawned. One returned the risk checklist above and unexpectedly created this handover file despite being instructed not to edit; the orchestrator inspected and retained it because it was a new handover/checkpoint file, not the protected HTML. The second SSA timed out and was not used. Final judgement remains with the orchestrator.

## Orchestrator Audit

- The protected HTML was not edited during this handover pass.
- The only intentional durable output from this pass is this handover document.
- The next agent must not trust SSA claims without local inspection.
- The next agent must not use git restore as a safety net for the protected HTML because the file is currently untracked.
- The source line references above are current audit anchors, not permanent API.
  Re-run `rg` before using them if any file changes.
- If the next agent needs to prototype fixes, create a new sibling file first. Recommended name:
  `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal-annotated-fix-draft.html`.
- Before any draft work, write down the exact file list to be read and written. If `sb-tab5-zone-composer-proposal.html` appears in the write list, stop and ask Captain.

## Final Audit Snapshot

Audit timestamp: 2026-06-07, after Captain restored the HTML via CMD-Z.

Protected HTML:

- Path: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`
- Size at audit: `1451` lines, `44564` bytes.
- SHA-256 at audit:
  `93956b417bd7d7079fe30fa197e722953a4324de80268b5c14dbbf94273a1044`
- Git state at audit: untracked (`??`).
- Meaning: this file is fragile. Do not overwrite it, do not assume git can
  restore it, and do not treat it as expendable working copy material.

Handover file:

- Path: `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-handover-after-prototype-failure.md`
- Size before this final audit update: `158` lines, `10490` bytes.
- SHA-256 before this final audit update:
  `424d748018de8beaa23813e99911e0f4d4d03effa245eddaf0ef5f1a92e2487e`

Screenshot artefact handling:

- Files named `sb-tab5-zone-composer-proposal-*.png` are prior visual evidence
  for the restored/proposal family. Use them only for comparison, not as source.
- Files named `sb-tab5-zone-composer-v2-pixel-lab-*.png` came from the rejected
  chaotic overhaul. Do not use them as design direction unless Captain
  explicitly reinstates them.
- Any next draft must produce fresh side-by-side screenshots of the protected
  original and the draft at exact `1280x720`.
- Record browser viewport, browser zoom, device pixel ratio, and capture method.
- Capture a touch-bounds overlay for changed interactive elements.
- Every changed element must be explained against Captain's annotated screenshot,
  not against generic UI taste.

Cold-start sufficiency check:

- A new agent should be able to start by reading this handover, then `AGENTS.md`,
  `.claude/CLAUDE.md`, and `docs/spec-index.md`.
- The next safe action is read-only: verify the protected HTML hash and render
  it at exact `1280x720`.
- The next write action, if Captain requests it, is a separate sibling draft
  file only. The protected HTML is not a write target.

## Final Instruction To The Next Agent

Captain is not asking for a new concept. Captain is asking for the previous, preferred concept to be protected, minimally corrected, visually validated, and then discussed before any broader control/menu decisions are implemented.
