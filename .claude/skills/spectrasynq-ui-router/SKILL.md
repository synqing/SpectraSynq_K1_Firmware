---
name: spectrasynq-ui-router
description: >-
  Route SpectraSynq UI work to the right skill. Single entry for optical gate,
  Tab5 LVGL dashboard, visual-decision-html, Tab5 wireless/ux/harness, and craft
  lenses. Use for UI, LVGL, Tab5 deck, font, layout, dashboard, soft key, HTML
  proof, type/geometry, FE control surfaces — or when unsure which UI skill fits.
---

# SpectraSynq UI Router

**Announce:** `Using spectrasynq-ui-router — dispatching UI skill.`

**Core principle:** Don't memorize the UI skill inventory — match
**scenario → one next skill**, then stop. Over-invocation is a process bug
(AGENT_OS §14). This is the UI counterpart to `/claude-mem-router` and
`/thinking-model-router`.

**Scope (global):** Applies to **any SpectraSynq UI** in **any checkout**
(Tab5/LVGL, firmware UI, FE control surfaces, product HTML sizes) — not K1
Firmware-repo-only. Evidence packs may live under that project's `_scratch/`
or `docs/`.

**Canonical home (symlink target for all agents):**
`/Users/spectrasynq/SpectraSynq_K1_Firmware/.claude/skills/spectrasynq-ui-router/`

**Design authority (absolute):**
`/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/UI_ROUTER_DESIGN.md`

**Unsure which UI skill?** Invoke **this router** — do not fan out the set.

---

## Keyword triggers (invoke this router)

UI · LVGL · Tab5 deck · `deck_ui` · `deck_type` · font · type ladder · layout ·
dashboard · soft key · sheet chrome · product HTML sizes · FE control surface ·
optical / typography audit · visual hierarchy on glass · HTML proof board for UI

---

## Quick gate (run in order)

```
1. Is this SpectraSynq UI design→code / look change?
   (LVGL/firmware UI, fonts, type/geometry/layout flags, soft-key chrome,
    product HTML sizes, FE control surfaces, colours-as-hierarchy)
   → /spectrasynq-ui-precode-optical-gate  FIRST
     BLOCKED until OPTICAL_GATE_RECEIPT.md + SHA-pinned MEASURED.json PASS
     (or Captain waiver string). Then continue to step 2+.

2. After optical PASS (or T3 / no-look companion task), match the table below
   → invoke ONE companion → act.

3. Still unsure which row? Stay on this router; do not invent a parallel path.
```

**Binary unlock for look edits:** optical PASS or BLOCKED. Router does not
waive the gate. Parent-agent “proceed” ≠ PASS.

---

## Scenario → skill

| Scenario / user shape | Invoke | Do NOT |
|-----------------------|--------|--------|
| Unsure which UI skill fits | `/spectrasynq-ui-router` (re-read table) | invoke all UI skills |
| New/changed UI design→code (any look surface) | `/spectrasynq-ui-precode-optical-gate` **FIRST** | write UI sources before PASS |
| Tab5/LVGL dashboard layout/controls **after** PASS | `/k1-tab5-lvgl-dashboard` | skip gate; treat C++ skim as PASS |
| Captain must approve geometry / form / CMF / dims-as-choice | `/visual-decision-html` | markdown/ASCII as decision surface |
| Tab5↔K1 wireless / WS / ACK / state desync | `/k1-tab5-wireless-control` | optical gate unless look also changes |
| Tab5 tones / mute / UX feedback cues | `/k1-tab5-ux-feedback` | optical gate unless chrome/type changes |
| Tab5 serial live harness / remote drive | `/k1-tab5-live-harness` | claim harness = optical PASS |
| Craft / aesthetic lens inside gate fanout | `impeccable` / `apple-design` / `emil-design-eng` | web fluid/clamp as LVGL law; lens alone as PASS |
| Pure docs / protocol / DSP / `NON_PRODUCT` research HTML | T3 — no optical pack | cite research HTML as firmware authority |

---

## Default UI ladder (design→code)

1. `/spectrasynq-ui-router` — confirm scenario (this skill)  
2. `/spectrasynq-ui-precode-optical-gate` — declare tier T0/T1/T2; build evidence pack  
3. On **PASS** → `/k1-tab5-lvgl-dashboard` (Tab5/LVGL) or scoped UI impl  
4. If Captain needs a geometry/form choice board → `/visual-decision-html` (may be a T0 artefact; **≠** LVGL optical PASS)  
5. Domain companions only as needed (wireless / ux-feedback / live-harness)  
6. Re-Observe stills after edits (OODA re-entry via optical gate discipline)

---

## Composition (router owns dispatch; others own domains)

| Skill | Role |
|-------|------|
| `/spectrasynq-ui-router` | Keyword scan + scenario table + hop order |
| `/spectrasynq-ui-precode-optical-gate` | Fail-closed PASS/BLOCKED law + MEASURED.json |
| `/k1-tab5-lvgl-dashboard` | Implementation **after** optical PASS |
| `/visual-decision-html` | Captain-facing HTML decision boards (orthogonal to ink PASS) |
| `/k1-tab5-wireless-control` | Radio / WS control lane |
| `/k1-tab5-ux-feedback` | Local feedback cues |
| `/k1-tab5-live-harness` | Serial simulator / remote drive |
| `impeccable` (global) | Craft lens only — never unlock |

### Reachability — global vs K1-repo-local

| Skill | Global (`~/.{claude,cursor,codex,agents}/skills`) | Notes when CWD ≠ K1 Firmware |
|-------|-----------------------------------------------------|------------------------------|
| `/spectrasynq-ui-router` | **Yes** (symlink → K1 `.claude`) | Always available |
| `/spectrasynq-ui-precode-optical-gate` | **Yes** (symlink → K1 `.claude`) | Always available; absolute canon paths in SKILL |
| `/visual-decision-html` | **Yes** (separate agent-skills install) | Geometry/CMF boards; ≠ optical PASS |
| `impeccable` / `apple-design` / `emil-design-eng` | **Yes** (global craft lenses; apple/emil may be Claude-home only) | Lens only — never unlock |
| `/k1-tab5-lvgl-dashboard` | **No — K1 Firmware `.claude/.cursor` only** | After optical PASS for Tab5/LVGL; if missing in CWD, open K1 path or copy skill — do **not** skip gate |
| `/k1-tab5-wireless-control` | **No — K1 repo-local** | Radio/WS lane |
| `/k1-tab5-ux-feedback` | **No — K1 repo-local** | Feedback cues |
| `/k1-tab5-live-harness` | **No — K1 repo-local** | Serial harness |

Orphan trap: invoking a repo-local companion from another checkout without the skill present is a miss — stay on this router, keep the optical gate (global), and either work in K1 Firmware or fetch the companion SKILL from the absolute K1 `.claude/skills/<name>/` path.

Do **not** copy optical checklists into companions. Point companions back here
for dispatch and to the gate for unlock law.

Orthogonal routers: `/claude-mem-router` (memory), `/thinking-model-router`
(mental models), `/k1-lineage-routing` (build/flash lineage).

---

## Anti-patterns

- Jumping to `k1-tab5-lvgl-dashboard` or font regen before optical PASS  
- Treating HTML decision boards, G0, or C++ inspection as optical PASS  
- Invoking impeccable / apple-design / emil-design-eng “to be safe” without a gate tier  
- Applying web fluid/clamp/responsive type recipes to fixed embedded UI  
- Fanning out every Tab5 skill on a one-line layout nudge  
- Building a second UI router or duplicating gate doctrine into AGENT_OS novels  

---

## Authority pointers (thin — absolute for cross-project invoke)

- Gate law: `/Users/spectrasynq/SpectraSynq_K1_Firmware/.claude/skills/spectrasynq-ui-precode-optical-gate/SKILL.md`  
- Process: `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md`  
- Canon: `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md`  
- AGENT_OS §7a (law) · §14 (skill scan → this router) — when present in the active repo  
- Design: `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/UI_ROUTER_DESIGN.md`  
- Global install receipt: `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/UI_ROUTER_GLOBAL_INSTALL.md`  

Post-session: `skills_used: spectrasynq-ui-router` (+ the dispatched skill).

## Refresh / global install

Canonical body: K1 Firmware `.claude/skills/spectrasynq-ui-router/`.  
Repo twins: **symlink** `.cursor/skills/` and `.codex/skills/` → `.claude/skills/` (no content copies; drift-proof).  
**Global (all agents / all projects):** symlink from
`~/.claude/skills/`, `~/.cursor/skills/`, `~/.codex/skills/`, and
`~/.agents/skills/` → the K1 Firmware `.claude` canonical (same pattern as
`claude-mem-router` / `computer-use`). See
`_scratch/precision_bay_r1/UI_ROUTER_GLOBAL_INSTALL.md`.
