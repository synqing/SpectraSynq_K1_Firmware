---
name: nyt-data-viz
description: NYT/Upshot editorial chart discipline for data-true K1 artefacts — palette restraint, typography, chart-type selection, annotation. Use when rendering analysis panels, mechanism step icons, signal backgrounds, or any chart/dashboard in the harness. Composes after k1_audio_features.py; subordinate to k1fe-design-system for colour tokens.
---

# NYT-discipline data visualisation (Hyperagent import)

Upstream scripts: `scripts/hyperagent/nyt-viz/`. Full integration map: `docs/hyperagent-skills-integration.md`.

## K1 override (read before any render)

These rules **win** over default NYT palette/typography when the artefact is K1 production:

| NYT default | K1 remap |
|-------------|----------|
| Hero accent (NYT blue) | Brand Gold `#FFB84D` — stroke/glow only, not fills |
| Paper white background | Void `#060606` / `#000000` |
| Playfair / Libre Franklin stack | `-apple-system` + `ui-monospace` for instrument labels only |
| Decorative chart chrome | TASTE §5 signal-void lane: 3–8 % opacity backgrounds; no VJ sludge |

**Never** use fixture/synthetic audio data in production renders. Source: approved canonical WAV via `scripts/k1_audio_features.py`.

## When to use

- Phase 2 data-true artefacts (`CLAUDE.md`): `#2 signal_wave_background`, `#4 mechanism_step_icons`
- Upgrading `scripts/render_analysis_panel.py` outputs to editorial grade
- Any harness chart, dashboard, or analysis explainer with numeric truth claims
- **Not** for landing-page layout (use `muller-brockmann-grid`) or identity critique (use `vignelli-canon`)

## Workflow hook (Phase 2)

```text
k1_audio_features.py (WAV → JSON + .npy)
  → k1_tokens.py (K1 gold/void remap)
  → chart_selector.py (pick chart type from data shape)
  → annotate.py (headline, source line, direct labels)
  → render.py (static Plot HTML) OR interactive.py scaffold (D3 dashboard)
  → sighted loop if embedded in HTML comp (k1fe-sighted-comp-build)
  → SHA manifest
```

## The five core rules

1. **Colour** — one hero series (K1 gold); greys for context; no rainbow/jet; categorical cap ~7 (`palette.py sequential hero <n>`).
2. **Typography** — tabular nums on all numeric labels; sentence headlines, not chart titles (`annotate.py`).
3. **Chart choice** — line for time, bar second, never pie, never dual y-axes, bars from zero (`chart_selector.py <shape> <intent>`).
4. **Annotation** — direct series labels at endpoints; source line; inflection callouts in place.
5. **Archie Tse rule** — crucial info visible without hover; check at 375px width.

## Commands

```bash
# K1-remapped tokens (preferred over raw upstream palette on production artefacts)
python3 scripts/hyperagent/k1_tokens.py chart-palette
python3 scripts/hyperagent/k1_tokens.py css-vars

# Chart-type lint
python3 scripts/hyperagent/nyt-viz/chart_selector.py how_much

# Static Observable Plot page (needs data JSON path — see script header)
python3 scripts/hyperagent/nyt-viz/render.py --help 2>/dev/null || head -40 scripts/hyperagent/nyt-viz/render.py
```

For interactive D3 dashboards, import patterns from `scripts/hyperagent/nyt-viz/interactive.py` (`scaffold`, `voronoiHover`, hit-layer coordinate rules).

## Composition

| Primary | This skill |
|---------|------------|
| `k1_audio_features.py` | Data source + brand PNG baseline |
| `k1fe-design-system` | Token authority |
| `k1fe-sighted-comp-build` | If chart ships inside HTML comp |
| `sightline` | Mandatory if comp HTML is taste-certified |

---
## Changelog

- 2026-06-13: Imported from Hyperagent public skills; K1 remap block + Phase 2 workflow hook.
