# 03 — Verdict

**REDESIGN the field.** Live total 13/30. Principle #3 scored 0. The two-well IA is not the failure. Parking a 1180px raft with `margin-left: auto` is the failure — leftover grows with the window and becomes the first thing you see.

Highest-leverage moves:

1. **Aesthetic (#3) / Little design (#10):** Kill the right-dock. Put both wells on a named page field (12-col with `--cols/--gutter/--margin/--maxw`, or a centred `--maxw` whose leftover is *specified* equal margins). Evidence: `index.html:62-65`; live 712px left void @1920 vs 28px right (`MEASURED.json`).
2. **Unobtrusive (#5):** Leftover must be a named margin or an empty column span — not CAD wallpaper. Inspect sky is a QC state, not the idle room. Evidence: `BOARD.html:152`, `:194`; Brand leftover fact.
3. **Useful (#2) / Understandable (#4):** Failed Connect must keep the error. Do not overwrite with `"Disconnected."` Evidence: `:745-749`, `:912-929`; Captain 13:59 still.
4. **Thorough (#8):** One instrument height (no 187px empty metal on the guide well), `aria-live` on status, Flash disabled reason named. Evidence: 1440 live well 849 / empty chrome 187.
5. **Honest (#6):** Footer version = `PAGE_VERSION`. “Independent UART” → exclusive port. Evidence: `:310` vs `:365`; `:249` vs `:682-685`.

Do not restyle tokens. Do not gold-fill Flash. Do not add shafts. Do not implement until Captain names the field on `FIELD.html` and the optical gate passes.
