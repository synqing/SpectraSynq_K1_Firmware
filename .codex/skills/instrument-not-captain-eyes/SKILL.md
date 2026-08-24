---
name: instrument-not-captain-eyes
description: >-
  HARD FAIL — never pull Captain into a visual-inspection / eyes-on /
  "look at the plate" validation loop when a render-path or LED-buffer
  dump already exists. Captain standing order 2026-08-22, every agent
  surface, every project. Use whenever validating LED output, colour,
  occupancy, packing, hue, decay, KEEP/KILL WS2816, rtrace, LED-buffer
  harvest, or any claim about what the firmware is rendering.
---

# Instrument, not Captain eyes

**HARD FAIL** if violated. Captain 2026-08-22. Binds every agent, every workspace.

Captain's words (verbatim):

> I hereby mandate across all agents surfaces and all projects that I am
> no longer to be pulled into the validation loop for stupid visual
> inspections when there is a perfectly working tool that I created for
> that exact purpose.

## What this covers

Any claim whose evidence lives in **what the renderer emitted**: LED
codes, packed wire, hue, occupancy, REPLICATE8 vs TRUE16, palette honour,
decay steps, "is 16-bit actually on the buffer."

The close stamp is a **scored dump**, not Captain walking to the plate.

## Required

1. Find this project's existing dump (do not invent a new one).
2. Arm it, capture, score offline. Write a receipt.
3. If the tap is on the **wrong buffer**, **move the tap**. Still do not
   pull Captain. Wrong tap is an agent bug, not an eyes-on request.
4. Report numbers. Captain is asked only for flash GO, product KEEP/KILL
   after the dump, or a genuine strategic fork.

## Forbidden

- "Captain, please look at the lights / plate / LGP" as the validator
- "eyes-on still required" as the close for a buffer question
- Optical KEEP as a substitute for occupancy / packing / hue proof
- Opening the plate as Plan A when `:rtrace_dump` / LED-buffer harvest /
  an equivalent dump exists
- Using an 8-bit `leds_out` dump to "prove" 16-bit occupancy on a path
  that never writes `leds_out`

## Split vs pixel-inspect

| Question | Validator |
|---|---|
| What did firmware emit? | Dump + scorer. **Never Captain.** |
| Finished PNG/HTML product-craft board | Agent Reads the PNG first (`pixel-inspect-before-captain`). Captain may then pick. That is **not** LED-plate squinting. |
| Named product taste *after* the dump exists | Captain, only if they asked. Dump still comes first. |

## K1 (canonical tool)

Captain already built **render path trace**:

- Serial: `:rtrace_arm=<seconds>[,<every_n>]` · `:rtrace_status=1` · `:rtrace_dump=1`
- Capture: `SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.{h,cpp}`
- Decoder (RGB8): `scripts/regression-harness/hue_coverage.py` (`rtrace_frames`)
- Occupancy (RGB16 packed wire): `scripts/regression-harness/score_rtrace_occupancy.py`
- Scorer example: `scripts/regression-harness/score_palette_resolver_rtrace.py`
- Closed this way: `docs/forensics/runtime-evidence/20260820T-palette-resolver-rtrace/RESULT.md`

**Known gap (do not paper over with eyes-on):**

- Shipping `k1_main_rpl_im69d` still does **not** compile `K1_RENDER_TRACE_V1`. The Lever-2 packed-wire tap lives on diagnostic env `k1_main_rpl_rtrace_probe` only. Occupancy KEEP/KILL still needs a named flash GO, then a scored `rgb16hex` dump — not Captain looking at the plate.

Palette bake pick is the LED-buffer harvest scorer, not `phd var` eyes-on (`k1-ws2816-lever2`).

## Close stamp

`RESULT.md` + scored JSON (occupancy histogram, hue error, REPLICATE8 lattice vs TRUE16) + device `IDENTITY OK` when silicon was involved.

Not: "Captain looked and said it seemed smoother."
