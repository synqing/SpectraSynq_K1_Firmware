---
name: muller-brockmann-grid
description: Müller-Brockmann modular grid discipline with CSS scaffold generator and Puppeteer verification harness. Use for landing-section layout QA, 1440px comp geometry, and optional grid-adherence proof after sighted comp builds. Composes with k1fe-sighted-comp-build; does not replace k1fe-design-system tokens.
---

# Müller-Brockmann grid systems (Hyperagent import)

Upstream scripts: `scripts/hyperagent/grid/`. Full integration map: `docs/hyperagent-skills-integration.md`.

## K1 override

- **Palette/type defaults in upstream scaffold** (white paper, Swiss red) are demo defaults — K1 comps use void `#060606`, ink tiers, gold `#FFB84D` accent ≤45 % alpha.
- **1440px fixed geometry first** (Framer transcription rule) — run `verify_grid.js` at `1440,1180,900` before responsive passes.
- Grid verification is **additive** to band-density and SIGHTLINE — it does not replace them.

## When to use

- Building or auditing multi-column landing sections, bento bands, editorial spreads in static comps
- After `k1fe-sighted-comp-build` band-density PASS — **optional** layout proof for grid-heavy pages
- Design-harvest **Layout anatomy** chapters — naming column spans and baseline rhythm
- Framer lane: verify comp column lines before transcription (geometry order in `AGENTS.md`)

## Workflow hook (sighted comp lane)

```text
k1fe-sighted-comp-build loop (band-density PASS)
  → [optional] grid_tokens.py audit / verify_grid.js
  → taste_gate_runner.py
  → sightline_check.py certify (if output/**/*.html)
```

## Engineering essentials (from upstream)

1. **One `:root` source of truth** — `--cols`, `--gutter`, `--margin`, `--bl`, `--lh`, `--maxw`.
2. **Overlay inside the same `.wrap` as content** — full-width overlay siblings misalign on wide viewports.
3. **Subgrid bands** — `grid-column: 1 / -1` + `subgrid`; children place by column line.
4. **Baseline lock** — leading and vertical spacing in px multiples of baseline.
5. **Optical alignment** — display ink on the line, not the box (runtime JS in scaffold).

## Commands

```bash
# Emit scaffold HTML to stdout
python3 scripts/hyperagent/grid/grid_tokens.py --scaffold \
  --cols 12 --baseline 8 --gutter 24 --margin 48 --maxw 1440 \
  --accent '#FFB84D' > /tmp/k1-grid-scaffold.html

# Verify adherence (requires Chrome + puppeteer-core on PATH)
CHROME="$(which google-chrome || which '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')" \
  PUP=puppeteer-core \
  node scripts/hyperagent/grid/verify_grid.js /tmp/k1-grid-scaffold.html --widths=1440,1180,900
```

PASS line: `GRID VERIFY: PASS` with `col=0px overlay=0px baseline≤4px ink=0px`.

## Composition

| Primary | This skill |
|---------|------------|
| `k1fe-sighted-comp-build` | Mandatory loop first; grid verify optional |
| `k1fe-design-system` | Colour/type tokens |
| `k1fe-framer-transcription` | Comp geometry must be stable before Framer push |
| `framer-k1-fe-launch-target` | 1440px left=0 order |

---
## Changelog

- 2026-06-13: Imported from Hyperagent public skills; K1 remap + sighted-comp workflow hook.
