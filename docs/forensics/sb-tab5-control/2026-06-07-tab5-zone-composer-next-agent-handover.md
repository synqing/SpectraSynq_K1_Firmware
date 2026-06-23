# Tab5 Zone Composer Next-Agent Handover

Date: 2026-06-07  
Working root: `/Users/spectrasynq/SensoryBridge-main 9`  
Protected HTML: `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`  
Status: Handover after failed overwrite/redesign pass. This file is a guardrail for the next agent.

## Executive Boundary

Captain is not asking for a new Tab5 UI concept. Captain explicitly rejected the later overhaul as "utter chaos" and said the previous version was significantly superior except for the annotated errors. The next task is therefore:

1. preserve the restored previous design,
2. fix only the annotated defects or prepare a narrow draft for them,
3. discuss unresolved button/function/menu handling before broader changes,
4. never overwrite the protected HTML without explicit approval.

## Source Evidence

- The restored protected proposal exists at `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
- The current HTML source still contains the original-style `LIGHT COMPOSER` screen, the top `PRIMARY EDGE / SECONDARY EDGE / SMART DIRECTOR` buttons, the LGP hero, parameter cards, overview cards, and footer status row.
- Header CSS: `.header` is positioned `left: 20px`, `top: 10px`, `width: 1240px`, `height: 50px`, with no explicit enclosing header border in the selector itself. Source: `sb-tab5-zone-composer-proposal.html:164`.
- Top surface buttons: `.mode-row` is `left: 20px`, `top: 64px`, `width: 1240px`, `height: 36px`; `.surface-button` is `height: 36px`, `min-width: 170px`. Source: `sb-tab5-zone-composer-proposal.html:245`.
- LGP hero: `.hero-strip` is `left: 40px`, `top: 108px`, `width: 1200px`, `height: 130px`; `.lgp-field` is `width: 1160px`, `height: 64px`; the simulated LED lines are CSS repeating gradients. Source: `sb-tab5-zone-composer-proposal.html:285` and `:311`.
- Parameter cards: `.param-grid` is five columns, `left: 20px`, `top: 284px`, `width: 1240px`, `height: 160px`; the cards display Mode, Palette, Photons, Chroma, Mood. Source: `sb-tab5-zone-composer-proposal.html:420` and `:1041`.
- Lower overview cards: `.overview-grid` is three columns, `left: 20px`, `top: 458px`, `width: 1240px`, `height: 170px`; cards show Primary Edge, Secondary Edge, Smart Director summaries. Source: `sb-tab5-zone-composer-proposal.html:494` and `:1074`.
- Footer: `.footer` is `left: 20px`, `top: 638px`, `width: 1240px`, `height: 38px`; source content is `SELECTED: PRIMARY EDGE`, `QUEUE EMPTY`, `SAVE DELAYED`, `AUDIO SEMANTIC LIVE`. Source: `sb-tab5-zone-composer-proposal.html:581` and `:1109`.
- Existing local screenshots include original/proposal screenshots and rejected V2 screenshots at repo root:
  - `sb-tab5-zone-composer-proposal-composer-final.png`
  - `sb-tab5-zone-composer-proposal-composer-final2.png`
  - `sb-tab5-zone-composer-proposal-composer-v2.png`
  - `sb-tab5-zone-composer-proposal-tab5-composer.png`
  - `sb-tab5-zone-composer-v2-pixel-lab-home-final.png` and related `v2-pixel-lab-*` files
- Treat any `v2-pixel-lab-*` screenshot or V2 rationale as rejected evidence, not a new baseline.
- Existing failure handover: `docs/forensics/sb-tab5-control/2026-06-07-tab5-ui-handover-after-prototype-failure.md`. Keep it as background, but do not treat any claim inside it as permission to edit the protected HTML.

## Captain's Annotated Defects To Fix Narrowly

These are the defects visible in Captain's annotated screenshot and follow-up comments. Fix the specific failure, not the whole composition.

1. Header border: Captain asked where the header border is. The next pass should add or clarify the header boundary while preserving the header's composition unless Captain approves a different structure.
2. Top buttons: Captain asked what the point of `PRIMARY EDGE`, `SECONDARY EDGE`, and `SMART DIRECTOR` is. Do not remove them by default. Decide whether they become actual selectable controls, page tabs, state selectors, or remain as labels, then discuss before implementation.
3. LGP/LED data: Captain asked whether the centre strip can be fed LED data. Treat the current CSS LED lines as simulated. Do not claim live LED readback unless the SB firmware/backend path exists and is verified.
4. Parameter cards: Captain asked how the user changes Mode, Palette, Photons, Chroma, and Mood. The cards currently read as display cards with progress bars. The next pass must clarify whether each is a button, stepper, slider entry, picker, or read-only readout.
5. Lower overview cards: Captain suggested the Primary Edge, Secondary Edge, and Smart Director summary panels may make more sense as buttons. Prototype or document this narrowly; do not redesign all pages.
6. Footer gap: Captain asked why there is a gap under the footer/status strip. The footer sits at `top: 638px`, `height: 38px` on a 720px panel, leaving a visible lower region. Fix the spacing or explain the intentional buffer visually.
7. Alignment and borders: Check header/footer border visibility on all four sides, spacing to adjacent elements, and whether `1px` borders are too weak on the 5 inch Tab5 display.
8. Labels and values: Inspect at exact 1280x720. Verify label legibility, value alignment, overshoot, and whether `Rajdhani`, `Bebas Neue`, and `JetBrains Mono` remain appropriate at the actual rendered sizes.

## Do Not Touch Without Approval

- Do not overwrite `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal.html`.
- Do not replace the visual language with the rejected V2 layout.
- Do not remove the existing screen composition just because an element is flawed.
- Do not promote `WS LIVE`, `AUDIO SEMANTIC LIVE`, `QUEUE EMPTY`, `SAVE DELAYED`, or LED-preview claims as real without source-backed runtime proof.
- Do not add wireless/backend/control features that SB firmware does not currently expose.
- Do not add WiFi STA selection; K1 is AP-only.
- Do not add settings, profile slots, haptic/audio feedback, or calibration flows to this screen without first proving the implementation path and Captain approving their placement.
- Do not convert the handover into a design manifesto. The next agent needs a narrow delta, screenshots, and a reviewable draft.

## Required Next Workflow

1. Read this handover and `2026-06-07-tab5-ui-handover-after-prototype-failure.md`.
2. Run read-only verification first: file exists, byte size, hash, and screenshot at exact 1280x720.
3. Create a new sibling draft only, for example `docs/forensics/sb-tab5-control/visual/sb-tab5-zone-composer-proposal-annotated-fix-draft.html`.
4. In the draft, make only annotated fixes:
   - visible header border,
   - top-button purpose/affordance clarity,
   - LED preview truth labelling or data-path note,
   - parameter-card control affordances,
   - lower-card button affordance option,
   - footer gap correction,
   - alignment/label pass.
5. Capture original and draft screenshots at exact 1280x720.
6. Present side-by-side evidence to Captain before replacing or merging anything.

## SSA Consumption Note

Captain supplied a read-only SSA brief for this handover. In this session no separate callable SSA runner was available, so the brief is consumed as a task constraint, not as independent verification. The orchestrator re-checked the protected HTML and repo evidence directly. If the next agent has an SSA runner, use the supplied brief exactly and consume the output as provisional unless the decisive source checks are personally re-run.

## Model Use

- `/thinking-model-router`: classified this as product plus risk plus handover safety.
- `/thinking-model-combination`: used pre-mortem, systems thinking, and via negativa. The main failure to prevent is another broad redesign when the requested move is a narrow correction.
- `/ssa-management`: applied the rule that agent/subagent prose is not proof. Source lines and screenshot evidence remain the decision substrate.

## Final Instruction

Protect the restored design. Fix the annotated errors narrowly. Do not overwrite the protected HTML. Prove the draft visually before asking Captain to accept any replacement.
