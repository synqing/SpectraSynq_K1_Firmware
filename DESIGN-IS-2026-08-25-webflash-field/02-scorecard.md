# 02 — Scorecard

Total **13 / 30**. Tie-breaker: lower score. Worst instance, not mean.

## 1. Innovative — 2/3

Evidence: two-well Console is a refresh of a bench, not a new pattern; right-dock is a 2020s dashboard hang (`index.html:62-65`, BOARD `:359`).
Justification: improvement over the seven-card wall, but the field is an imitation of a right-parked console, not a new grammar.

## 2. Useful — 2/3

Evidence: Connect → Flash is on the first row; after a failed Connect the strip says Disconnected and Flash stays dead ([UX](866206f3-b3df-48dd-a13f-fe215e2820bc); `:745-749`). Serial monitor is a second product in the hands well.
Justification: the primary task is present, but an adjacent surface and a clobbered error add steps. Not 1 — the task is still on the screen.

## 3. Aesthetic — 0/3

Evidence: live left void 232px @1440, 712px @1920, 935px CSS @2143; 8.9–11.7 leftover modules that are not 80px structure (`MEASURED.json`; `index.html:62-65`). First face on a wide window is empty lattice.
Justification: worst instance is “active visual noise” / no page-scale system. The inner 590/80/510 split is composed; the page is leftover. Lower of 1 vs 0.

## 4. Understandable — 1/3

Evidence: “Disconnected.” after a Connect attempt; two baud defaults (460800 vs 115200); “port is already open” vs How-to PIO line; Seed OTA-1 / NVS jargon ([Copy](1288bc56-dc52-4828-a493-14654da25562), [UX](866206f3-b3df-48dd-a13f-fe215e2820bc)).
Justification: two to three unclear mappings, not one tooltip.

## 5. Unobtrusive — 1/3

Evidence: leftover floor + always-on Inspect sky are the majority unread surface as V grows ([UI Designer](7297b654-169a-4c34-8c76-665f9a579065); Brand leftover ~1/3 of the 2143 still).
Justification: chrome / wallpaper competes with Connect → Flash. Not 0 — wells still exist.

## 6. Honest — 1/3

Evidence: “Real build images.” (`:218`); footer `v1.0.0` vs `1.1.0` (`:310`, `:365`); Inspect-as-idle vs board “after the write”; “Independent UART” while ports are exclusive.
Justification: two-plus inflations / mismatches. No dark-pattern 0.

## 7. Long-lasting — 2/3

Evidence: CAD-dot wallpaper + right-dock is one dated dashboard marker. Tokens and machined wells are not a 2024 fad gradient.
Justification: one dated marker, not three.

## 8. Thorough — 1/3

Evidence: missing `aria-live`, skip-link, landmarks, Connect-fail state, empty-log hint, erase confirm; progress track always at 0% ([A11y](22ee4ec7-0971-4922-a3e5-cd72b019849c), [UX](866206f3-b3df-48dd-a13f-fe215e2820bc)). Focus and disabled exist.
Justification: two to three load-bearing states missing or clobbered.

## 9. Environmentally friendly — 2/3

Evidence: 293,550 B JS; 0 idle animations; dark page; no `prefers-reduced-motion` ([Weight](ffb585a5-460c-4923-a672-95cf32908ef6)).
Justification: under 500KB and no idle motion, but over 100KB and PRM absent — not a 3.

## 10. As little design as possible — 1/3

Evidence: removable leftover field, idle Inspect, page-rail, always-on progress, serial-as-second-product, unused `#updateBtn` in default view.
Justification: three to five removable elements. The 80px inner gutter earns its place; the left remainder does not.
