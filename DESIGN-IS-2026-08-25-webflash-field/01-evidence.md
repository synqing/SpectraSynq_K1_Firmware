# 01 — Evidence

Specialists: [Structural](4e9ce6ee-209c-4ea8-9f32-274da337c224), [Copy](1288bc56-dc52-4828-a493-14654da25562), [Weight](ffb585a5-460c-4923-a672-95cf32908ef6), [A11y](22ee4ec7-0971-4922-a3e5-cd72b019849c), [UI Designer](7297b654-169a-4c34-8c76-665f9a579065), [Brand](bb8288a4-256e-48a6-b6b8-05aeab9a923f), [UX](866206f3-b3df-48dd-a13f-fe215e2820bc), [Visual](f449523f-fa83-416b-af1e-bb015044651e).

Numbers: `MEASURED.json` (NumPy CSS identity + live `getBoundingClientRect`).

---

## Field (the complaint)

Source: `tools/webflash/index.html:62-65` — copied from `_scratch/webflash-void-20260824/BOARD.html:359`.

```
.console { max-width: 1180px; margin: 4vh 0 0 auto;
           grid-template-columns: 1.1fr 0.95fr; gap: 80px; }
.page { padding: 36px 28px 96px 56px; }  /* :61 */
```

`margin-left: auto` parks a capped 1180px object on the right of an uncapped page. Leftover is `V − 1180 − 28`.

| Viewport | Left void | n × 80 | Hands | Gap | Guide | Right pad |
|---|---|---|---|---|---|---|
| 1440 live | **232** | 2.90 | 590 | 80 | 510 | 28 |
| 1920 live | **712** | 8.90 | 590 | 80 | 510 | 28 |
| 2143 CSS | **935** | 11.69 | 590 | 80 | 510 | 28 |

Inner split is designed (590 / 80 / 510). Outer remainder is not: not integer 80px modules, not a named column. Vignelli test on the board (`BOARD.html:579`): “if you cannot see 80px modules in the gutters, the layout has failed.” The *between-wells* gutter is 80. The *left field* is remainder dressed with D Dots + always-on Inspect sky.

Well boxes at 1440×900: both **849px** tall. Guide has **187px** empty chrome under the last pocket. Height mismatch on the still is fill, not box (unless the window is ≤980, where wells stack 951 vs 1046).

---

## Structural

- 12 interactive controls (`index.html` 219–263). Nesting depth 7.
- 6 repeated patterns (two baud selects, two Connect-initiation buttons, four `.term` wells).
- 5 dead props (`--ok`, `.mono`, `.role-hands`, `.role-guide`, unread `state.simpleMode`).
- `#updateBtn` hidden except `?mode=simple`.

## Copy & honesty

- Inflations: “Real build images.” (`:218`), “S3 USB usually finds the bootloader.” (`:281`).
- Footer HTML `v1.0.0` (`:310`) vs JS `PAGE_VERSION = "1.1.0"` (`:365`).
- Failed `connect()` writes an error, then `disconnect()` overwrites status with `"Disconnected."` (`:745-749`, `:912-929`). Captain 13:59 still matches that.
- How-to “Quit pio device monitor” (`:283`) does not name the page holding `SerialPort`.
- Erase / Seed essays always visible; checkboxes hidden in simple mode.
- “Independent UART terminal” (`:249`) is exclusive with the flasher port (`:682-685`).

## Weight

- Initial JS **293,550** bytes (crypto-js 48,316 + esptool 218,551 + inline 26,683).
- Cold requests: 9 (4 local + Google Fonts CSS + 4 faces).
- Idle animations: **0**. No `prefers-reduced-motion`.
- Modals: 0.

## Accessibility

- Ink / muted / gold on void: 18.10 / 8.03 / 11.79 — AA+AAA pass.
- Page-rail 50% gold ≈ 3.49:1 — AA fail (decorative).
- Landmarks: **0**. Skip-link: **no**. No `aria-live` on status.
- `#monitorInput` placeholder only, no label.

## Apple / Emil (facts, not scores)

| Before | After | Why |
|---|---|---|
| `margin: 4vh 0 0 auto` on a 1180 cap | Named field: 12-col or `margin-inline: auto` inside `--maxw` | Purpose / simplicity: leftover is not a margin you can name |
| Wells content-height, 187px empty chrome | One instrument height, or no painted empty metal | Craft: two faces must read as one bench |
| `transition: transform 140ms` + `:active scale(0.97)` | Keep | Press feedback is already correct (Emil / Apple §1) |
| Failed Connect → `"Disconnected."` | Keep the error; do not clobber | Agency / honesty: the strip must name the held port |
| Always-on Inspect sky on leftover | Inspect after a write, or kill idle sky | Spatial consistency: QC light without a QC job |

No idle springs. Do not add motion to “fix” a field.

## Müller-Brockmann

No `--cols`, `--gutter`, `--margin`, `--maxw` on the live page. Overlay cannot be verified. The only module is the 80px *inner* gap. Page pads 56 / 28 are not on that module.

## Vignelli

Gold on the 13:59 still is the allowed identifier set (kicker, K1 foil, Connect rim, offsets, Erase/Seed pocket titles). Not fills, not progress, not rays. Leftover void-as-wallpaper **is** the Vignelli miss: space is remainder, not structure.

## NYT / SciPy

Offset table is a table, not a chart. Gold on offsets is identifier. Archie Tse: Connect / Flash / offsets are visible without hover. Leftover arithmetic is `V − 1208` — do not invent a different leftover from the 1024px chat downscale.
