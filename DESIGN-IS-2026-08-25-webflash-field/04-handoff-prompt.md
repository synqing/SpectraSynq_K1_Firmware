# 04 — Handoff

````
/make-plan Redesign the K1 web flasher *field* (panel position and size). Current design failed audit at 13/30 with critical gaps in principles 3 (aesthetic 0), 4 (understandable 1), 5 (unobtrusive 1), 6 (honest 1), 8 (thorough 1), 10 (little design 1).

Verdict paragraph (quoted from 03-verdict.md):
> REDESIGN the field. Live total 13/30. Principle #3 scored 0. The two-well IA is not the failure. Parking a 1180px raft with `margin-left: auto` is the failure — leftover grows with the window and becomes the first thing you see.

Why redesign and not refine: load-bearing aesthetic scored 0 and total is under 20. The inner IA can be preserved; the page field cannot be patched with a colour tweak.

Preserve from current design (MUST be non-empty):
- Void `#060606`, gold `#FFB84D` identifier only — `tools/webflash/index.html:13-17`, `:86-103`, `:121-123`, `:175`, `:189`
- Two-well IA: hands (Connect, Flash, Erase/Seed checkboxes, variant, baud, status, log) + guide (Build map + How to flash pockets) — `:214-311`
- How-to pockets: Normal / If sync fails / Erase / Seed OTA-1 — essays stay in pockets, not in Control
- Original flash `<script type="module">` and IDs (`connectBtn`, `flashBtn`, `eraseAll`, `seedOta1`, `progressBar` as inner span, etc.)
- Press feedback `button:active { transform: scale(0.97) }` — `:119`
- D Dots Mid tokens (`--pitch: 20px; --dot-a: 0.34`) as a *receding* floor, not as leftover wallpaper
- No “What happens”, no “Prefer the CLI?”, no teal `#35e0c8`

Discard (MUST be non-empty):
- `.console { max-width: 1180px; margin: 4vh 0 0 auto }` right-dock. Evidence: `index.html:62-65`. Caused failure on principle #3 and #10.
- Always-on Inspect sky/lintel as the idle room. Evidence: `:45-54`, `:211`. Caused failure on #5 and #6.
- Status clobber `"Disconnected."` after a failed Connect. Evidence: `:745-749`, `:912-929`. Caused failure on #4 and #8.
- Guide well empty chrome (187px at 1440) as a second metal face. Evidence: `MEASURED.json`. Caused failure on #3 and #8.

Top 3–5 moves from the audit (verbatim):
1. Aesthetic (#3) / Little design (#10): Kill the right-dock. Put both wells on a named page field (12-col with `--cols/--gutter/--margin/--maxw`, or a centred `--maxw` whose leftover is specified equal margins). Evidence: `index.html:62-65`; live 712px left void @1920 vs 28px right (`MEASURED.json`).
2. Unobtrusive (#5): Leftover must be a named margin or an empty column span — not CAD wallpaper. Inspect sky is a QC state, not the idle room. Evidence: `BOARD.html:152`, `:194`.
3. Useful (#2) / Understandable (#4): Failed Connect must keep the error. Do not overwrite with `"Disconnected."` Evidence: `:745-749`, `:912-929`; Captain 13:59 still.
4. Thorough (#8): One instrument height (no 187px empty metal on the guide well), `aria-live` on status, Flash disabled reason named. Evidence: 1440 live well 849 / empty chrome 187.
5. Honest (#6): Footer version = `PAGE_VERSION`. “Independent UART” → exclusive port. Evidence: `:310` vs `:365`; `:249` vs `:682-685`.

Redesign principles in priority order:
1. Aesthetic (#3) — the first face is the instrument, not leftover dots. Leftover is n×80 or equal specified margins.
2. As little design as possible (#10) — two wells on a field; no third “empty shop” composition.
3. Understandable (#4) — Connect fail names the held port; next action is on the strip.

Deliverables for the plan:
- New information architecture for the *field only* (12-col vs centred max-width) — compared side-by-side on FIELD.html
- New primary flow is the same Connect → Flash; field change must not hide controls
- States checklist (empty, loading, error, success, focus, disabled) — especially Connect-fail
- Migration: keep IDs and flash JS; CSS field + status copy only
- Cutover: local `tools/webflash/index.html` after optical PASS; production only when Captain says deploy

Anti-patterns to guard against (specific to REDESIGN):
- Porting the right-dock under new styling
- Gold-filling Flash / progress / rays to “balance” the void
- Adding shafts, smears, or a fake window
- Treating the Preserve list as optional
- Implementing look edits before `/spectrasynq-ui-precode-optical-gate` PASS
- `vercel --prod` or flash

Captain field pick (required before CSS):
- F1 Centre: `margin-inline: auto`, leftover split equally, cap may rise above 1180
- F2 Fill: wells span the page inside named 12-col; 80px gutter on a column line
- F3 Specified left rail: leftover is an N×80 typed column (title lives there), not empty dots
````
