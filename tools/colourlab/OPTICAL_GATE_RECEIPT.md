# Production Colour Lab Preview R1.1 — optical receipt

- Tier: **T0 — production DOM replacement from approved Preview authority**
- Surface: `colourlab.preview.production.r1.1`
- Date: 2026-08-28
- Verdict: **PASS — PRODUCTION PREVIEW CUTOVER**
- Device writes in Preview: **none**

## SHA-pinned result

- Production `index.html`: `ce023f219b54bb1b7c7b3d6c0e26f69afaf716df131f5df0b1e806167aa0b43e`
- Byte-identical parity twin `workbench.html`: `ce023f219b54bb1b7c7b3d6c0e26f69afaf716df131f5df0b1e806167aa0b43e`
- Production UI controller: `78e6e31cc7ceb2a961563875ce093c2b5d0d094fede340659ea2d1cc0f59af54`
- Effective-look/comparison core: `5314b24a9ae2eef1e2f3c62619d7b7a27e9ee7080012cf29654272c1bf0670c2`
- Browser verifier: `b14517da2f1d5c2a8961151f95be9e4a10970cbcbb84295a17bf89a91fcca2c3`

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

## Measured optical result

- 740 px: document `740 = 740`; Primary strip offset `313.31 px`; strip height
  `58 px`; Secondary strip bottom `508.03 px`.
- 390 px: document `390 = 390`; inspector caption width `336 px`; semantic order
  remains header → comparison → Primary → Secondary → inspector → handoff.
- 800 px 200%-reflow equivalent: document `800 = 800`; no horizontal overflow.
- Fresh visual inspection of desktop and 390 px stills found no clipping, hierarchy
  inversion, residual numbered-step marker or prohibited wheel-spanning colour.

## Validation

- `python3 -m pytest tests/test_colourlab_*.py -q` → **90 passed**
- `python3 tools/colourlab/verify_workbench.py` → **FAILURES=0**, 13 fresh stills
- `python3 tools/colourlab/verify_browser.py` → compatibility path to the same gate,
  **FAILURES=0**, 13 fresh stills
- Production/parity-twin byte comparison → **identical**
- `git diff --check` over the Colour Lab slice → **PASS**

This receipt closes the local production Preview R1.1 cutover. It does not claim
physical LED output, acrylic diffusion, LUT-node readback or hardware-session proof.
Those remain gated by `COLOUR_LAB_WEB_UI_HARDWARE_PASS` on `9087A500` and
`B489A500` before merge to `main`.
