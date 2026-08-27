# COLOUR_LAB_WEB_UI_T0_LOOK_WAIVER_V1

Issued by Captain 2026-08-27. Named string is load-bearing.

> Historical pre-cutover authority. The greenfield production Workbench now has
> its own T0 PASS in `OPTICAL_GATE_RECEIPT.md`; this waiver is retained only to
> preserve the decision trail.

```text
CAPTAIN_WAIVER_UI_PRECODE_OPTICAL_GATE
named: COLOUR_LAB_WEB_UI_T0_LOOK_WAIVER_V1
surface: tools/colourlab/index.html
tier_bypassed: T0
reason: Waive the prerequisite T0 optical-pack requirement only for reuse of the existing K1/webflash void/gold visual identity on Colour Lab.
expires: end of Colour Lab Web UI lane
post_condition: optical pack still required before any new visual identity or next UI commit that invents tokens/faces
signed: Captain
```

## Scope

Waive the prerequisite T0 optical-pack requirement **only for reuse of the
existing K1/webflash void/gold visual identity on Colour Lab**.

The waiver does **not**:

- approve a new visual identity
- waive accessibility
- waive pixel inspection
- waive responsive / browser verification
- waive functional verification
- permit styling changes to alter the contract-correct Colour Lab core,
  state semantics, safety behaviour, or device capability model

The existing no-look shell/core remains the functional oracle beneath
the styling layer. `colourlab-core.js` is not restyled by rewriting it.

## Authority reused (not invented)

Webflash tokens already on disk in `tools/webflash/index.html`:

- void `#060606`
- gold `#FFB84D`
- ink `#F2F2F2`
- muted `#A3A3A3`
- faces: Saira Condensed (display) + IBM Plex Mono (instrument)

## What this is not

This is **not** `OPTICAL_GATE` PASS. Invented ink heights are still
forbidden. The next *new* identity still needs a T0 pack.
