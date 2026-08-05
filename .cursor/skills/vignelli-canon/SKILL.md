---
name: vignelli-canon
description: Vignelli Canon design discipline — timeless Swiss-modernist critique for typography, grid, and identity restraint. Use when auditing harvest port verdicts, taste audits, or anti-slop reviews. Critique lens only; k1fe-design-system is the K1 token authority.
---

# Vignelli Canon design system (Hyperagent import)

Upstream script: `scripts/hyperagent/vignelli/vignelli_system.py`. Full integration map: `docs/hyperagent-skills-integration.md`.

## K1 override

- Vignelli **primary-colour-as-identifier** maps to K1 gold `#FFB84D` (border/glow, not fill) on void — not Vignelli red or arbitrary primaries.
- **Six basic typefaces** doctrine → K1 uses `-apple-system` + mono for instrument register only (`k1fe-design-system`).
- Use this skill to **critique**, not to invent new K1 identity, copy, or pricing.

## When to use

- `k1fe-site-design-harvest` port verdicts — second opinion on ADOPT/ADAPT/REJECT for typography and layout discipline
- `spectrasynq-taste` audit — anti-slop, hierarchy through scale not colour noise
- Premium static-site workflow — restraint check before `premium-refinement-pass`
- **Not** for chart/data lanes (`nyt-data-viz`) or grid verification (`muller-brockmann-grid`)

## Intangibles (apply as critique checklist)

- Semantics before aesthetics — does the layout serve the message?
- Discipline — fewer sizes, larger jumps; no decorative type
- Appropriateness — entertainment product, not transit map (adapt railway module logic, do not copy literally)
- Timelessness — reject trend palettes, gradient slop, HUD chrome
- Equity — clarity at a glance

## Tangibles (apply as measurement)

- Modular grid with consistent margins
- Two-size type scale mindset (display vs body) — align with K1 ink tiers
- Primary colour identifies, not decorates
- White space as structure

## Commands

```bash
# Token sheet (remap --primary for K1 audits)
python3 scripts/hyperagent/vignelli/vignelli_system.py --format json --primary '#FFB84D'

# Grid map reference
python3 scripts/hyperagent/vignelli/vignelli_system.py --grid 4x8

# Railway signage module table (wayfinding reference only)
python3 scripts/hyperagent/vignelli/vignelli_system.py --signage
```

## Workflow hook (design harvest)

```text
k1fe-site-design-harvest inventory
  → per-feature port verdict (k1fe-design-system)
  → [optional] vignelli-canon critique on typography/layout ADOPT/ADAPT calls
  → spectrasynq-taste anti-slop if shipping to K1 comp
```

## Composition

| Primary | This skill |
|---------|------------|
| `k1fe-design-system` | K1 token authority — wins on conflict |
| `k1fe-site-design-harvest` | Port verdict producer |
| `spectrasynq-taste` | Operational anti-slop gates |
| `sightline` | Still mandatory before done claims on comps |

---
## Changelog

- 2026-06-13: Imported from Hyperagent public skills; critique-only K1 posture.
