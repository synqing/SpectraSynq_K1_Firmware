---
name: k718-radial-grid
description: Use when designing, laying out, reviewing, or critiquing any UI on a circular / round display — round LCD, smartwatch face, rotary-encoder screen, gauge, or the K718 Remoted / K1 dashboard. Triggers when content must be placed on a circle, when a rectilinear grid (Müller-Brockmann, columns) does not fit, or when checking bezel-safe margins, occlusion, and legibility on a curved canvas.
---

# k718-radial-grid

## Overview

Rectilinear grids (columns, baseline grids, Müller-Brockmann) assume a rectangle. A **circular display has no corners, no rows, no columns** — placing content with x/y columns wastes the center and clips the edges. HALO places content in **polar coordinates**: every element has a **radius band** (how far from center) and an **angular zone** (clock position). This skill is the reusable discipline; the worked instance is the K718 Remoted design language (`artifacts/K7180-Design-System/spec/K718-DESIGN-LANGUAGE.md`).

**Core principle:** *Importance is centrality.* The closer to the center, the more important and the more legible. The single most important value lives dead-center; navigation lives at the rim.

## When to use

- Laying out a round-LCD / encoder / smartwatch / gauge UI
- Reviewing a circular design for bezel-safe margins, occlusion, or legibility-on-curve
- Deciding where a value, label, control, or status lives on a circle
- A rectilinear column grid is being forced onto a circular canvas (anti-pattern — stop and use this)

Not for rectangular screens — use a column grid there.

## Quick reference — the polar grid

**Radius bands** (bezel → center), the concentric placement zones:

| Band | Role | Rule |
|---|---|---|
| Bezel-Safe Margin | dead zone / glow bleed | no critical content |
| Nav Ring | top-level navigation, modes | rim = lowest reading priority |
| Control Ring | active/interactive parameter | thumb-reachable |
| Signal/Content Core | live visualization / primary content | audio/data-driven |
| Readout Center | the ONE primary value + unit | sacred — never occluded, exactly one |

**Angular zones** (clock positions):

| Zone | Clock | Typical content |
|---|---|---|
| Crown | 12 | status / primary state badge |
| Right Arc | 1–5 | secondary nav / labels |
| Keel | 6 | persistent status, action bar |
| Left Arc | 7–11 | secondary nav / labels |

## The math (the part rectilinear grids can't give you)

```
Scale:            px_per_mm = active_px / active_mm        # K718: 480 / 60 = 8 px/mm
Active radius:    R = active_px / 2                        # 240 px
Bezel-safe:       R_safe = R * (1 - safe_pct)             # 6% → 226 px; keep critical content inside
Place at (r,θ):   x = cx + r * sin(θ)                      # θ in radians, 0 = 12 o'clock,
                  y = cy − r * cos(θ)                      #   clockwise positive
Clock→angle:      θ = hour * (2π / 12)                     # 3 o'clock = π/2
Even N dots:      θ_i = i * (2π / N)                       # ring of N dots, i = 0..N-1
Arc gap (px):     gap = r * Δθ                             # dot spacing grows with radius
```

**Legibility on a curve:** keep text on **straight horizontal baselines** (tangential text warps and fails at small sizes). Only decorative/label-ring text follows the arc, and never below the device's mid type rung. Size text by role against a legibility ladder with explicit min-contrast (see the K718 ladder T1–T6).

## Rules

1. **Importance ↔ centrality.** Most important value = center. Never bury the primary readout in a ring.
2. **Bezel-safe is a radius, not a rectangle.** Clip-test against `R_safe`, not against edges.
3. **Occlusion-aware.** A hand turning the encoder covers ~30% lower-left and ~30% lower-right arcs, ~15% bottom. Keep the readout clear of both thumb arcs; keep persistent status surviving *through* the bottom swipe.
4. **One readout per screen.** Two competing center values = two screens.
5. **Rings carry roles, not decoration.** A ring exists because it has a job (nav / control / signal), never because a circle "needs" another ring. Adding a decorative ring is the anti-pattern that produces variant-dial churn.

## Common mistakes

| Mistake | Fix |
|---|---|
| Column grid forced onto a circle | Place by radius band × angular zone |
| Primary value in a ring, decoration in center | Center is sacred — value goes dead-center |
| Critical text outside `R_safe` | Clip-test against the safe radius |
| Tangential (curved) text at small size | Straight horizontal baselines for anything you must read |
| "The circle looks empty, add a ring" | Empty is fine. Rings need a role, not a vacancy |
| Same content under the thumb zones | Move readable content out of the ~30% lower arcs |

## Validation gate

A radial layout is correct when: every element maps to one (band, zone); nothing critical crosses `R_safe`; the readout survives both thumb-occlusion arcs; all text meets its legibility-ladder rung; and no ring exists without a stated role. For K718, the reference component gallery (`artifacts/K7180-Design-System/reference/`) is the built proof of these rules.

## Live worked instance (added 2026-07-04)

The shipped K718 firmware dashboard is now the primary worked instance of this
grid. Its **current, device-proven band table** (FX push rect, curved name/value
radii + autofont threshold, value arc, picker sector ring, baked rings) lives in
the K718 repo's agent manual:
`~/Workspace_Management/Software/JC3636K518CN_knob_EN-bleremote/CLAUDE.md`
(§ Radial layout geometry) — read it before proposing band changes; it encodes
one constraint this doctrine implies but does not state: **any glyph pixel
inside the direct-push FX rect (square, corners at r≈147) is overwritten every
frame** — text bands must clear the square, not just the disc. Open doctrine
conflict awaiting Captain: LAW-2's empty bullseye vs this skill's
"readout centre is sacred" (the value currently sits in the bottom rim band,
inside the thumb-occlusion zone).
