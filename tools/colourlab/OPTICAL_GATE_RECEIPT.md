# Optical gate receipt — Colour Lab Web UI

**Surface:** `tools/colourlab/index.html`  
**Tier declared:** T0 (new product HTML surface)  
**Date:** 2026-08-27  
**Optical verdict:** **BLOCKED** (measures not a PASS)  
**Look unlock:** **`COLOUR_LAB_WEB_UI_T0_LOOK_WAIVER_V1`** (Captain)

Entered via `/spectrasynq-ui-router`. Mandatory first hop
`/spectrasynq-ui-precode-optical-gate`. Parent-agent “execute the plan”
is not a waiver. Captain named the string.

## Waiver (only unlock)

See `tools/colourlab/WAIVER.md`. Scope is reuse of the existing
K1/webflash void/gold identity. Not a new identity. Does not waive
accessibility, pixel inspection, browser verification, or the hardware
programme. Does not authorise rewriting `colourlab-core.js` for look.
A later safety edit added Disconnect and persist-leave classifiers to
the core; that is not a look rewrite and is not optical PASS.

## Why this is still not optical PASS

1. No independent T0 measure pack was produced.
2. A waiver does not convert invented or missing ink into PASS.
3. `MEASURED.json` verdict remains `WAIVED`, not `PASS`.

## What the waiver permits

Apply the existing webflash tokens (void `#060606`, gold `#FFB84D`,
Saira Condensed + IBM Plex Mono) as a styling layer **on top of** the
contract-correct shell. Same IDs, same core, same state/safety/capability
model.

## Red-team (why these still fail as PASS)

1. “Waiver means optical PASS” — no. The skill says a waiver does not
   turn FAIL measures into PASS.
2. “Now we can invent a new gold treatment” — out of scope. Reuse only.
3. “Styling can tidy Set Identity into Revert” — forbidden. Semantics
   stay in the core.
4. “Connect-only is now hardware PASS” — orthogonal, and refused.

## Paths

- Waiver: `/Users/spectrasynq/SpectraSynq_K1_Firmware/tools/colourlab/WAIVER.md`
- Receipt: `/Users/spectrasynq/SpectraSynq_K1_Firmware/tools/colourlab/OPTICAL_GATE_RECEIPT.md`
- Measures: `/Users/spectrasynq/SpectraSynq_K1_Firmware/tools/colourlab/MEASURED.json`
- Core (oracle): `/Users/spectrasynq/SpectraSynq_K1_Firmware/tools/colourlab/colourlab-core.js`
