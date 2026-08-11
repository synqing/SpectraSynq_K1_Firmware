---
abstract: "SpectraSynq mandatory pre-code optical/typography gate. Fail-closed, tiered T0–T3. PASS = OPTICAL_GATE_RECEIPT.md + SHA-pinned MEASURED.json + crops — never prose. Absorbs UI_PRECODE_GATE_REDTEAM.md bypass suite. Entered via spectrasynq-ui-router."
status: active
date: 2026-08-09
router: spectrasynq-ui-router
skill: spectrasynq-ui-precode-optical-gate
canon: docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md
redteam: _scratch/precision_bay_r1/UI_PRECODE_GATE_REDTEAM.md
---

# SpectraSynq UI Pre-code Optical Gate

**Law:** No SpectraSynq UI firmware, LVGL layout, font regen+rebind, or product
HTML that asserts sizes may be **designed into code** until the optical gate
**PASSes** for the declared tier.

**Entered via:** [`spectrasynq-ui-router`](../../.claude/skills/spectrasynq-ui-router/SKILL.md)
owns UI skill dispatch. Agents should hit the router first for UI/LVGL/Tab5/font/layout
work; the router mandates this gate as the first hop for design→code. Design:
[`_scratch/precision_bay_r1/UI_ROUTER_DESIGN.md`](../../_scratch/precision_bay_r1/UI_ROUTER_DESIGN.md).

**Skill (gate law):** [`.claude/skills/spectrasynq-ui-precode-optical-gate/SKILL.md`](../../.claude/skills/spectrasynq-ui-precode-optical-gate/SKILL.md)
(mirrored `.cursor/skills/`, `.codex/skills/`).

**Session canon:** [`docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md`](../canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md).

**Red-team / bypass suite:** [`_scratch/precision_bay_r1/UI_PRECODE_GATE_REDTEAM.md`](../../_scratch/precision_bay_r1/UI_PRECODE_GATE_REDTEAM.md)
— threat model, **not** a PASS receipt.

---

## Dual rail (neither substitutes)

| Rail | Proves |
|------|--------|
| Functional (G0, bindings, build, identity) | Map-valid controls, TX honesty |
| Optical (this gate) | Hierarchy / legibility on glass |
| Flash | Captain go + chip identity |

`G0_PASS ≠ OPTICAL_PASS`.

---

## Tiers

| Tier | When | Weight |
|------|------|--------|
| **T0** | New surface / ladder / face / MAIN redesign / HTML→firmware | Full fanout |
| **T1** | Role↔token rebind, no new faces | Delta inventory + before/after crops |
| **T2** | Geometry only (no font token change) | Ink gaps + cite locked ladder SHA |
| **T3** | Docs / protocol / DSP / `NON_PRODUCT` research HTML | Exempt — does not unlock UI code |

Undeclared tier = **T0**.

---

## PASS keys (anti-prose)

Required for unlock: **`OPTICAL_GATE_RECEIPT.md`** + **`MEASURED.json`** (SHA-pinned
still, crops, source paths) + vision-Read still. Long audits are annexes.
Invented / TBD / skill-name-only ⇒ **BLOCKED**.

---

## Not exemptions

Small nudge · colour-only hierarchy · clip “bugfix” · sim-only · HTML-as-LVGL
proof · stale pack · G0-as-optical · C++ inspection · parent “proceed” · web
fluid type on embedded. See red-team §3 and skill ban list.

---

## Waiver

Only `CAPTAIN_WAIVER_UI_PRECODE_OPTICAL_GATE` block in `WAIVER.md` (skill §).
Verbal paraphrase insufficient.

---

*Detail lives in the skill. Do not duplicate novels into AGENT_OS.*
