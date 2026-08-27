# 02 — Scorecard (live flasher)

Scoring the **shipped** `tools/webflash/index.html` composition, not the proposal board.

1. Good design is innovative — Score: 1/3
   Evidence: 01-evidence Structural — 7 cards in a two-column dashboard (`index.html:508-662`); Axisform grain/grid is a layer, not a new pattern.
   Justification: Imitates the generic ESP web-flasher card wall with minor dress; not a wholesale copy of a named competitor, not a restrained new pattern.

2. Good design makes a product useful — Score: 2/3
   Evidence: Connect/Flash exist (`:514-516`); Erase essays sit in Control (`:540-560`); What happens + CLI cards add reading before doing (`:637-655`).
   Justification: Primary task completes, but adjacent surface adds steps. Not 3 (decoys) and not 1 (the buttons are still on the first screen).

3. Good design is aesthetic — Score: 1/3
   Evidence: Captain 22:16 screenshot — furniture covers the 80px grid; Window `.spot` (`:84-93`) has no frame/source. Token system exists (`:17-29`) but the room does not read.
   Justification: One jarring violation (atmosphere claimed, room occluded + sourceless shafts). Not 0 (there is a token system).

4. Good design makes a product understandable — Score: 2/3
   Evidence: Connect/Flash are nameable; Erase/Seed OTA-1 need the essays currently parked in Control (`:517-551`); How to flash is a flat chunk list (`:607-635`).
   Justification: One control cluster needs a tooltip/essay. Tie-break stays at 2, not 3.

5. Good design is unobtrusive — Score: 1/3
   Evidence: 7 cards + header well fill the viewport (01-evidence card count); grain/grid only survive in the gutter (Captain screenshot).
   Justification: Decoration/chrome competes with — and covers — the content of the room. Not 0 because type/tokens still recede somewhat inside each card.

6. Good design is honest — Score: 2/3
   Evidence: “Real build images” backed by manifest copy (`:501-504`). No dark patterns. “What happens” is accurate but padded.
   Justification: ≤1 minor inflation (process essay as a product card). Not 3 (the card implies you need to read it to flash).

7. Good design is long-lasting — Score: 2/3
   Evidence: Void/gold/mono is durable; foil gradient on K1 (`:196-201`) is one trend marker.
   Justification: One dated marker. Not 3, not a 2024-HUD costume.

8. Good design is thorough down to the last detail — Score: 1/3
   Evidence: Loading strings exist; errors live in a log; button focus is a sheen not a ring (`:290-333`); no empty-manifest well; disabled exists (`:324-331`).
   Justification: 2–3 states missing or rough (empty, success, focus).

9. Good design is environmentally friendly — Score: 2/3
   Evidence: Vendored esptool + crypto (`:487-669`) — initial JS >100KB and <2MB (estimated). Dark is the only mode. `prefers-reduced-motion` present (`:477-481`). No idle animation.
   Justification: Bundle over the 100KB bar, motion gated. Tie-break: 2 not 3.

10. Good design is as little design as possible — Score: 1/3
   Evidence: Removable without breaking flash: What happens, Prefer the CLI?, Erase essay in Control, extra header list (`:502-505`, `:637-655`).
   Justification: 3–5 removable elements. Not 0 (the page is not only decoration).

**Total: 15 / 30**
