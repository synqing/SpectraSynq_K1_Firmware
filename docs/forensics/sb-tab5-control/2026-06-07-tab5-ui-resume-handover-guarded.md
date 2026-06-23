# SensoryBridge Tab5 Zone Composer Resume Handover - Guarded

Date: 2026-06-07  
Working root: `/Users/spectrasynq/SensoryBridge-main 9`  
Latest instruction: restore the previous Zone Composer design direction, fix only the annotated errors, and discuss button/function/menu handling before broader changes.  
Protected source-truth HTML: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`

## Critical Context

Captain rejected the attempted overhaul as unusable chaos. The important correction is not aesthetic disagreement. The failure was process: the agent overwrote the existing proposal file, changed the design direction without approval, and replaced a mostly preferred design instead of applying narrow fixes to the defects Captain annotated.

Captain then manually restored the prior proposal with CMD-Z. Treat the restored HTML as a fragile recovery point. At the time of this handover it is untracked by git, so git is not a safe recovery mechanism.

Current protected HTML evidence:

- Path: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`
- Size observed: `44564` bytes
- SHA-256 observed: `93956b417bd7d7079fe30fa197e722953a4324de80268b5c14dbbf94273a1044`
- `git status --short --untracked-files=all` lists the whole `docs/forensics/sb-tab5-control/` tree as untracked.

## Evidence To Preserve

- The restored HTML is the source of truth for the next visual pass. Do not replace it. Relevant current source regions:
  - Header geometry: lines 164-173.
  - Shared card/button border style: lines 175-188.
  - Parameter cards and tiny bars: lines 420-492.
  - Lower overview cards: lines 494-579.
  - Footer/status strip: lines 581-597.
  - Composer screen HTML: lines 1000-1114.
  - Surface-button state script: lines 1395-1425.
- Existing handover: `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-handover-after-prototype-failure.md`. Use it as supporting context, but this file is the latest guarded resume note.
- Pixel contract: `docs/forensics/sb-tab5-control/2026-06-07-tab5-pixel-match-operating-contract.md`. Preserve its physical Tab5 constraints and exact 1280x720 validation requirement.
- Rejected reset/V2 rationale: `docs/forensics/sb-tab5-control/2026-06-07-zone-composer-proposal-v2-element-rationale.md`. Mine it only for cautionary constraints. Do not use it as the UI baseline.
- Disk screenshots in the repo root named `sb-tab5-zone-composer-proposal-*.png` are evidence of the earlier proposal family. Disk screenshots named `sb-tab5-zone-composer-v2-pixel-lab-*.png` plus `sb-tab5-zone-composer-v2-home-snapshot.md` are evidence of the rejected overhaul family.
- Captain's annotated screenshot in the conversation is load-bearing. It marks: missing or unclear header border, meaningless top buttons, whether the LED strip can be fed real LED data, readout cards needing actual change mechanisms, lower summary cards possibly becoming buttons, and a footer gap.

## Annotated Defects To Fix Narrowly

Fix only the annotated defects first. Do not redesign unmarked regions.

1. Header border visibility.
   - Current `.header` has position and size but no visible enclosing border of its own at lines 164-173.
   - Narrow fix: add or expose a clear header boundary without moving the whole page or changing the header concept.

2. Header/footer clipping and geometry.
   - Current header is `left: 20px; top: 10px; width: 1240px; height: 50px`.
   - Current footer is `left: 20px; top: 638px; width: 1240px; height: 38px`.
   - Narrow fix: make structural borders visibly contained inside the 1280x720 Tab5 frame and account for the bottom gap, without converting the whole UI into the rejected V2 layout.

3. Top surface buttons.
   - Current buttons are `PRIMARY EDGE`, `SECONDARY EDGE`, `SMART DIRECTOR` at lines 1010-1014, with script-driven selection at lines 1395-1425.
   - Captain asked what the point of these buttons is.
   - Narrow fix options to discuss before implementation: make them explicit parameter-surface selectors, move their function into the lower cards, or remove them. Do not decide silently.

4. LED strip/readback question.
   - Current hero is a schematic LGP field at lines 1016-1034.
   - Captain asked whether it can be fed LED data.
   - Narrow fix: label it truthfully as schematic unless a source-backed live LED/readback path exists. Do not imply live LED output without proof.

5. Parameter cards need change mechanisms.
   - Current Mode, Palette, Photons, Chroma, Mood cards are readout-style articles at lines 1041-1072.
   - Captain asked how the user changes these values.
   - Narrow fix: decide per parameter whether the existing card becomes a button, stepper, slider entry, or picker entry. Preserve the visual language unless Captain approves a larger control redesign.

6. Lower overview cards may be buttons.
   - Current Primary Edge, Secondary Edge, Smart Director overview cards are articles at lines 1074-1107.
   - Captain suggested these might make more sense as buttons.
   - Narrow fix: prototype the interaction affordance only, or document a click/tap path, without changing their information hierarchy first.

7. Footer gap.
   - Current footer/status strip ends at `top 638 + height 38 = 676`, leaving visible space to the bottom of the 720px frame.
   - Narrow fix: either use the footer area intentionally or adjust the footer geometry so the bottom space reads as designed, not accidental.

8. Fake-live/status truth.
   - Current composer header includes `WS LIVE` at lines 1003-1006.
   - Footer includes `AUDIO SEMANTIC LIVE`, `QUEUE EMPTY`, and `SAVE DELAYED` at lines 1109-1114.
   - Narrow fix: remove or relabel any live/status claim that is not source-backed. Do not use fake green live indicators.

## Do Not Touch Without Approval

- Do not overwrite `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
- Do not replace the restored design with the rejected V2 direction.
- Do not edit existing screenshots or snapshot files.
- Do not rename, delete, move, or "clean up" the untracked SB Tab5 control artefacts.
- Do not change the overall visual language, layout composition, typography stack, colour system, or screen count as part of the narrow-fix pass.
- Do not convert the task into firmware API work, REST/WS implementation, AP networking, WiFi provisioning, profiles, haptics, or settings unless Captain explicitly scopes that work.
- Do not claim Tab5 hardware proof. Browser and Playwright evidence are not on-device proof.
- Do not treat `WS LIVE`, `AUDIO SEMANTIC LIVE`, or live LED preview as real without source-backed runtime evidence.
- Do not implement a destructive or broad action in the UI without a guarded state flow and explicit approval.
- Do not continue if the next step would edit any existing source-truth file. Stop, state the intended file path, and get approval.

## Required Resume Protocol

1. Re-read `AGENTS.md`, `.claude/CLAUDE.md`, and `docs/spec-index.md`.
2. Verify the protected HTML still matches the hash above or record the new hash and explain the difference.
3. Render the protected HTML read-only at exact `1280x720`.
4. Build a narrow delta table from Captain's annotated screenshot. Include: issue, current source line, minimal fix, whether approval is needed, and visual validation method.
5. Create a new sibling draft only, for example `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal-narrow-fix-draft.html`.
6. Capture original and draft side by side at exact `1280x720`.
7. Explain every changed element. Leave unchanged elements alone.
8. Ask Captain before replacing the protected proposal. Do not infer approval.

## SSA Guardrail Consumption

The user supplied two read-only SSA briefs for the handover:

- `SB-TAB5-HANDOVER-GUARDRAILS`: identify what the next agent must not do, using conversation evidence only.
- `SB-TAB5-HANDOVER-EVIDENCE-INVENTORY`: preserve evidence and annotated defects, with read-only file inspection allowed.

No callable SSA runner was exposed in this turn. The orchestrator therefore consumed those briefs as load-bearing guardrail contracts and re-ran the decisive inspection locally with read-only commands. Consumption result: use the restored HTML and Captain's annotated screenshot as source truth; reject any broad redesign; create only new draft files unless Captain approves modifying the source proposal.

## One-Sentence Instruction For The Next Agent

Protect the restored Zone Composer proposal, fix only Captain's annotated defects in a separate draft, visually validate the delta at exact 1280x720, and discuss button/function/menu handling before changing the design architecture.
