# Production Colour Lab Preview R1.1 — optical receipt

- Tier: **T0 — production DOM replacement from approved Preview authority**
- Surface: `colourlab.preview.production.r1.1`
- Date: 2026-08-28
- Verdict: **PASS — PRODUCTION PREVIEW CUTOVER**
- Device writes in Preview: **none**

## SHA-pinned result

- Production `index.html`: `e335b39990803a77d874e8ae2cc694ab6d6fb2fba42d735dfc58b8decc6f8e37`
- Byte-identical parity twin `workbench.html`: `e335b39990803a77d874e8ae2cc694ab6d6fb2fba42d735dfc58b8decc6f8e37`
- Production UI controller: `163995ad0928bc8515ae7c0b981402789426b5a4a01a8db77fe7e65e4ac7c8fe`
- Effective-look/comparison core: `5314b24a9ae2eef1e2f3c62619d7b7a27e9ee7080012cf29654272c1bf0670c2`
- Browser verifier: `944dd960747b2692a437b89e60afd07df514b54ca404b2a7f97c0e1f363c988b`

## Result

1. Source, Tune and Preview are parallel operator roles; the residual `01` / `02`
   step numbers are absent.
2. Preview carries no workflow step number and contains no device mutation control.
3. Output equality and Preview-basis equality are separate computed facts from
   `CL.compareStageFrames()`.
4. Primary and Secondary remain permanent independent rows; inheritance resolves an
   effective look inside Secondary's own frame.
5. One persistent `selectedLed` drives both RGB16/RGB8 rows through
   `CL.inspectStageFrame()` from the exact cached frames.
6. Pointer, touch, number input and left/right arrow keys converge on that selector.
7. Slot-15 unknown wording says knowledge is absent, keeps both selections
   pre-correction and makes no tune claim.
8. Preview is read-only. Test belongs to Source; Apply and Save belong to Tune.
9. Device Safety failure makes Preview unavailable. Product-policy failure retains
   permitted local analysis while blocking output boundaries.
10. No rainbow, hue wheel, full-spectrum sweep or wheel-spanning product surface exists.
11. A verified Bench profile hides and hard-guards unsupported Tune controls.
12. A verified Main profile discloses its Both-target ×0.30 scale; Bench does not.

## Measured optical result

- 740 px: document `740 = 740`; Primary strip offset `313.31 px`; strip height
  `58 px`; Secondary strip bottom `508.03 px`.
- 390 px: document `390 = 390`; inspector caption width `336 px`; semantic order
  remains header → comparison → Primary → Secondary → inspector → handoff.
- 800 px 200%-reflow equivalent: document `800 = 800`; no horizontal overflow.
- Fresh visual inspection of desktop and 390 px stills found no clipping, hierarchy
  inversion, residual numbered-step marker or prohibited wheel-spanning colour.

## Validation

- `python3 -m pytest tests/test_colourlab_*.py -q` → **92 passed**
- `python3 tools/colourlab/verify_workbench.py` → **FAILURES=0**, 14 fresh stills
- `python3 tools/colourlab/verify_browser.py` → compatibility path to the same gate,
  **FAILURES=0**, 14 fresh stills
- Production/parity-twin byte comparison → **identical**
- `git diff --check` over the Colour Lab slice → **PASS**

This receipt closes the production Preview R1.1 cutover, including the two
hardware-exposed capability corrections. `COLOUR_LAB_WEB_UI_HARDWARE_PASS` is
recorded separately in `VERIFICATION.md` for `9087A500` and `B489A500`. It does
not claim physical LED values, acrylic diffusion truth or LUT-node readback.
Merge to `main` remains a separate explicit action.
