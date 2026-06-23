# SensoryBridge Tab5 UI Narrow-Fix Resume Handover

Date: 2026-06-07  
Working root: `/Users/spectrasynq/SensoryBridge-main 9`  
Protected HTML: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`  
Current protected HTML SHA-256 observed: `93956b417bd7d7079fe30fa197e722953a4324de80268b5c14dbbf94273a1044`

## Purpose

This handover is for the next agent resuming the SensoryBridge Tab5 Zone Composer UI work after a failed overcorrection.

Captain's latest direction is explicit: the previous design was significantly superior except for the annotated defects. The next pass must restore/preserve that design direction, fix the small visible errors Captain called out, and discuss button/function/menu handling before broader changes.

This is not a licence to redesign.

## Immediate Stop Rules

1. Do not overwrite `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
2. Do not edit the protected HTML directly unless Captain explicitly approves that exact file path.
3. Any prototype fix must be a new sibling draft, for example `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal-narrow-fix-draft.html`.
4. State exact file paths before any edit.
5. Do not use the chaotic V2/pixel-lab screenshots as the baseline.
6. Do not "improve" unannotated regions.
7. Do not claim Tab5 hardware proof unless the screen has actually been reviewed on the Tab5.
8. Treat all current live/backend/LED-readback claims as unproven unless SB firmware source proves them.

## Current Evidence To Preserve

- Existing post-failure handover: `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-handover-after-prototype-failure.md`.
- Protected restored proposal: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
- The protected proposal is currently untracked by git, so git is not a safe recovery path if it is overwritten.
- The restored HTML defines a `1280 x 720` Tab5 panel at lines 137-146.
- Header geometry is currently `.header { left: 20px; top: 10px; width: 1240px; height: 50px; }` at lines 164-173.
- The top surface selector row is `.mode-row` at lines 245-255 and DOM buttons at lines 1010-1014.
- The centre-origin LED/LGP hero is the core visual object at lines 1016-1033.
- Parameter cards for Mode, Palette, Photons, Chroma, and Mood are at lines 1041-1071.
- Lower overview cards for Primary Edge, Secondary Edge, and Smart Director are at lines 1074-1107.
- The footer/status strip is at lines 1109-1114, with CSS at lines 581-597.
- Surface selector JavaScript changes selected surface state only; it does not provide parameter editing mechanisms. See lines 1395-1443.
- Side prototype navigation exists outside the Tab5 panel at lines 1305-1312.
- Source-rationale copy inside the HTML says the UI is a visual proposal and the wireless backend remains API-needed at lines 1344-1361.
- Screenshot evidence in the repo root includes earlier proposal captures such as `sb-tab5-zone-composer-proposal-composer-final.png`, `sb-tab5-zone-composer-proposal-composer-final2.png`, and `sb-tab5-zone-composer-proposal-tab5-composer.png`.
- Rejected V2/pixel-lab evidence also exists, including `sb-tab5-zone-composer-v2-pixel-lab-home-final.png`; preserve it as failure evidence only, not a baseline.

## Captain's Annotated Defects To Fix Narrowly

These are the defects visible in Captain's annotated screenshot and messages. Fix these only, or bring the question back for discussion.

1. Header border is missing or unclear. Add visible header containment without changing the header's identity.
2. Header/footer borders must be fully visible and not clipped by the simulated screen edge.
3. Top buttons `PRIMARY EDGE`, `SECONDARY EDGE`, and `SMART DIRECTOR` look pointless. Do not delete them automatically; clarify whether they are selectors, navigation, or mode-state tabs.
4. The centre LED/LGP hero may need real LED data/readback. Treat this as a product/implementation question; do not fake live readback.
5. Parameter cards look like readouts but imply controls. The next design pass must show how Mode, Palette, Photons, Chroma, and Mood are changed.
6. Lower overview cards may make more sense as tappable buttons. Discuss or prototype narrowly; do not replace the whole layout.
7. Footer gap under the status strip is visually unjustified. Reduce, rebalance, or explicitly integrate that space.
8. Existing label/value alignment, overshoot, and legibility must be checked at exact `1280 x 720`.
9. Fake-live/status claims such as `WS LIVE`, `AUDIO SEMANTIC LIVE`, `QUEUE EMPTY`, and `SAVE DELAYED` must be removed, labelled simulated, or source-backed before presentation.

## Narrow Acceptance Criteria

1. The preferred restored design remains recognisably the same after the fix.
2. Only annotated defects change.
3. Header has a visible border/container and remains aligned within the panel.
4. Footer/status area no longer leaves an unexplained dead gap.
5. Top surface buttons have a stated role and matching affordance.
6. Each parameter card has a visible edit path or is clearly read-only.
7. Lower overview cards are either clearly summaries or clearly tappable controls.
8. No fake live/backend/audio/LED-readback claims remain.
9. The draft is visually captured at exact `1280 x 720`.
10. Protected original and draft are presented side by side before replacement is discussed.

## Button, Function, And Menu Questions For Discussion

- Should the top surface row remain as a selected-surface selector, become navigation into deeper surface pages, or be removed in favour of lower cards?
- Should Mode and Palette use steppers, full-screen pickers, or lower-card drill-downs?
- Should Photons, Chroma, and Mood be sliders, tap-to-open controls, or +/- touch zones?
- Should lower Primary/Secondary/Director cards be summary buttons that open detail pages?
- Should the LED hero be simulated preview, last-known LED frame, or live readback once SB has a backend?
- Should the footer be a status strip, navigation strip, or command-feedback strip?

## Do Not Touch Without Approval

- Do not replace the protected HTML file.
- Do not rename or delete existing screenshots.
- Do not move the project to a new visual language.
- Do not introduce a new page architecture.
- Do not add WiFi setup, password saving, user profiles, audio feedback, haptics, reset, calibration, OTA, or developer controls to the main screen.
- Do not revive the rejected V2 layout, two-page layout, or pixel-lab layout as the basis.
- Do not use full rewrite language such as "reset", "rebuild", "new architecture", or "from scratch" for the next pass.
- Do not claim SB firmware has firmware-v3 API/WS/REST parity until source-backed.

## Recommended Next Workflow

1. Read this handover and `2026-06-07-tab5-ui-handover-after-prototype-failure.md`.
2. Verify the protected HTML hash before touching anything.
3. Create a new sibling draft HTML only.
4. Make the smallest possible visual changes for the annotated defects.
5. Run a local screenshot capture at exact `1280 x 720` for original and draft.
6. Produce a compact diff table: element, old problem, narrow change, reason, remaining question.
7. Show Captain the original and draft side by side.
8. Wait for explicit approval before replacing the protected HTML.

## SSA Consumption Notes

Captain supplied two read-only SSA briefs for evidence inventory and narrow acceptance criteria. No callable SSA execution tool was exposed in this turn, so the briefs were consumed as guardrail contracts rather than external proof.

Model routing used:

- Product lens: preserve the job of the screen Captain preferred.
- Risk lens: prevent another overwrite or overcorrection.
- Systems lens: separate UI concept, backend proof, LED readback proof, and Tab5 hardware proof.
- Via negativa: remove scope creep; do not add new surfaces.

## Final Instruction To The Next Agent

Captain is asking for preservation plus narrow correction. Do not solve the broader Tab5 control architecture yet. Fix the annotated visual defects on a sibling draft, prove it visually, then discuss controls.
