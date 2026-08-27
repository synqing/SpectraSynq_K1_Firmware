# 04 — Handoff prompt

```
/make-plan Redesign K1 Webflash page composition. Current design failed audit at 15/30 with critical gaps in principles 3 aesthetic, 5 unobtrusive, 8 thorough, 10 as little design as possible.

Verdict paragraph (quoted from 03-verdict.md):
> REDESIGN the room. Live total 15/30, no principle at 0, but the score is under 20 — the bones of flashing are fine; the bones of the page are a card wall that hides the product.

Why redesign and not refine: Total is 15/30 (under 20). The flash path works; the furniture does not.

Preserve from current design (MUST be non-empty):
- Void `#060606`, gold `#FFB84D` as identifier not fill (`tools/webflash/index.html:17-29`).
- Saira Condensed display + IBM Plex Mono body (`:10`, `:45`, `:188`).
- Foil on the word K1 only (`:196-201`).
- Machined opaque wells, no backdrop-filter (`:130-161`).
- Vertical page rail “SpectraSynq · K1 · Web Serial” (`:105-119`).
- Press `scale(0.97)` on buttons (`:333`).
- Entire flash/monitor `<script type="module">` (`:668` onward) — do not rewrite esptool flow.
- How to flash as one card (not deleted) — inner pockets only (`:606-635`).

Discard (MUST be non-empty):
- What happens page card. Evidence: `index.html:637-645`. Caused failure on principle #10.
- Prefer the CLI? page card. Evidence: `:647-655`. Caused failure on principle #10.
- Erase / Seed OTA-1 essays inside Control. Evidence: `:540-560`. Caused failure on principles #2 and #4.
- Sourceless Window `.spot` god-rays. Evidence: `:84-93`. Caused failure on principle #3.
- Two-column card wall that occludes the 80px grid. Evidence: `:508-662` + Captain 22:16 screenshot. Caused failure on principle #5.

Top 3–5 moves from the audit (verbatim):
1. As little design as possible (#10): Delete the What happens and Prefer the CLI? page cards. Evidence: `tools/webflash/index.html:637-655`; Captain 22:16 REMOVE marks.
2. Useful (#2) / Understandable (#4): Control is hands only. Move Erase / Seed OTA-1 warning copy into How to flash as inner pockets — keep How to flash as one card. Evidence: `:540-560` vs `:606-635`; Captain: “I never asked you to remove the tab boxes, I only asked you to segment the steps.”
3. Unobtrusive (#5) / Aesthetic (#3): Cluster remaining wells in the upper field so 80px grid + 4px grain read as a room. Evidence: Captain gutters-only grain; Axisform void-first.
4. Aesthetic (#3): Light must have a source you can point at (sash / mullion / north / slit / lamp / cove). No Vertex fan from empty top-left. Evidence: `.light .spot` `:84-93`; Captain “makes sense.”
5. Thorough (#8): Keep loading / error / disabled; add a real focus ring and a quiet success line on the control well.

Redesign principles in priority order:
1. Useful (#2) — Connect and Flash remain the first hands; warnings are next to the checkboxes geographically only inside How to flash pockets, not as Control essays.
2. As little design as possible (#10) — two wells (or one plate / one strip) plus void. If a third well is not the serial monitor or build map, it does not ship.
3. Aesthetic (#3) — atmosphere is the room; light has a named source from the proposal board.

Implement ONLY the layout letter + light number Captain names on `_scratch/webflash-void-20260824/BOARD.html` (A Console / B Island / C Plate / D Slab / E Workbar × 0–6 lights). Do not invent a seventh layout. Do not `vercel --prod` until Captain says deploy.

Deliverables for the plan:
- New information architecture (not derived from the seven-card wall)
- New primary flow (low-fi, labeled, compared side-by-side to current) — already visible on the proposal board; port that pair
- States checklist (empty, loading, error, success, focus, disabled)
- Migration path: same URL, same JS, HTML/CSS dress only
- Cutover criteria: Captain names pair → agent ports to `tools/webflash/index.html` → Captain says deploy → production URL MD5 matches dist

Anti-patterns to guard against (specific to REDESIGN):
- Porting old structure under new styling
- Keeping both designs behind a flag indefinitely
- Redesigning to follow a trend rather than the principles above
- Treating the Preserve list as optional — it must be filled before this handoff is valid
```
