---
name: spectrasynq-ui-precode-optical-gate
description: >-
  HARD BLOCK before any SpectraSynq UI design→code (LVGL/firmware UI, font
  regen+rebind, type/geometry/layout flags, soft-key chrome, product HTML sizes,
  FE control surfaces). Entered via spectrasynq-ui-router; tiered fanout T0–T3;
  PASS only via OPTICAL_GATE_RECEIPT.md + SHA-pinned MEASURED.json + crops —
  prose/C++/CSS/G0 alone cannot PASS. Inventing measures or skipping for
  “small nudge” = BLOCKED.
---

# SpectraSynq UI Pre-code Optical Gate

**Announce:** `Using spectrasynq-ui-precode-optical-gate — UI code BLOCKED until optical PASS receipt.`

**Entered via:** `/spectrasynq-ui-router` owns UI skill dispatch. Prefer that
router as the entry point for any UI/LVGL/Tab5/font/layout task; it routes here
as the **mandatory first hop** for design→code. Do not bypass the router by
jumping straight to dashboard/impl skills.

**Scope (global):** Applies to **any SpectraSynq UI** in **any checkout** — not
K1 Firmware-repo-only. Put the evidence pack under **that project's**
`_scratch/<lane>_YYYYMMDD/` (or `docs/` if the project prefers). Absolute paths
in receipts/MEASURED.json remain mandatory.

**Canonical home (symlink target for all agents):**
`/Users/spectrasynq/SpectraSynq_K1_Firmware/.claude/skills/spectrasynq-ui-precode-optical-gate/`

**Authority (absolute paths — work from other repos)**

- Router (dispatch): `/Users/spectrasynq/SpectraSynq_K1_Firmware/.claude/skills/spectrasynq-ui-router/SKILL.md`
- Canon: `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/canon/SESSION_CANON_2026-08-09_ui_precode_optical_gate.md`
- Process: `/Users/spectrasynq/SpectraSynq_K1_Firmware/docs/process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md`
- Red-team (bypass suite): `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/UI_PRECODE_GATE_REDTEAM.md`
- Evidence archetype (FAIL teaching packs): `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/FONT_SIZE_*.md`
- Design: `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/UI_ROUTER_DESIGN.md`
- Global install receipt: `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/UI_ROUTER_GLOBAL_INSTALL.md`

**The token is not the glyph; the HTML is not the glass; the checklist is not the audit.**

---

## STOP — hard-stop checklist (load-bearing)

Do **not** edit gated UI paths until **all** boxes are true:

```text
[ ] Gate tier declared (T0/T1/T2/T3) and matches the change class
[ ] Surface ID + absolute paths of files to touch listed
[ ] Source inventory exists (role → call site → token → face)
[ ] Native or SDL still opened (`open -g`) AND vision-Read by the agent
[ ] Measured optical heights (ink and/or face line_height) for every role
    on the touched ladder — not nominal --size alone
[ ] Role → optical_target_px → face → token table LOCKED (no TBD)
[ ] Sorted-by-optical ladder shows content heroes ≥ chrome (no chevron/title
    theft) OR explicit accepted exception signed in receipt
[ ] HTML/CSS sizes, if used, converted or marked non-authority for LVGL
[ ] One positioning system per parent (no Flex + negative margin + translate +
    FLOATING stack) audited for touched widgets
[ ] Forbidden-fixes list present (session canon: do not shrink hero to escape
    title collision; fix geometry/face)
[ ] OPTICAL_GATE_RECEIPT.md written with SHA pins; verdict PASS
[ ] MEASURED.json present; still/crop/source SHAs match files on disk
[ ] If LVGL/Tab5: k1-tab5-lvgl-dashboard (or successor) consulted
[ ] Web fluid/clamp/responsive type recipes NOT applied to fixed embedded UI
[ ] Red-team subsection: ≥3 bypass attempts against THIS pack and why they fail
[ ] No P0 inversion unless Captain-accepted exception recorded

If any box is false → BLOCKED. Audit-only work may continue under the active project's _scratch/.
```

**Binary unlock:** PASS or BLOCKED. No “partial PASS — code in parallel.”

---

## Agents must never

1. Write UI firmware before an optical PASS receipt.  
2. Treat `--size` / CSS px as optical height.  
3. Assign instrument-size tokens to chrome (chevrons/arrows/rules).  
4. Dump unrelated roles onto one token (Mono34 landfill).  
5. Shrink the hero to fix a title/geometry collision.  
6. Stack Flex + FLOATING + translate + negative margin on one parent.  
7. Claim PASS from text-only design discussion or C++ skim.  
8. Cite G0/functional freeze as visual authority (`G0_PASS ≠ OPTICAL_PASS`).  
9. Reuse a prior audit pack without SHA-binding to current paths/stills.  
10. Apply web fluid-typography skills as LVGL law.  
11. Invent measurements, mark TBD tables PASS, or drop skill names without artefacts.  
12. Treat parent-agent “proceed” or this red-team doc as a PASS / waiver.

---

## Not exemptions (bypass suite — fail-closed)

These phrases **do not** unlock UI code:

| Attack | Counter |
|--------|---------|
| “Just a small nudge” / one-line font rebind | **Any** fonts, type tokens, widget geometry, layout flags, colours-as-hierarchy, soft-key chrome, sheets, product HTML sizes = gated. **No byte-count exemption.** |
| “Colour / opacity only” | If colour is sole hierarchy between same-size roles → gate applies. |
| “Comment / token rename only” | Role/face rebinds = gate. Pure spelling with no `#define`/enum/call-site change = T3. |
| “Bugfix: text clipped” | Clip/pad/align on text widgets **is** optical → gate. |
| “Font asset regen only” | Gate **before** regen and before rebind. |
| “Simulator harness only” | Sim is acceptance authority → gate. |
| “HTML decision board only” | Map for Captain; **not** LVGL optical PASS. Product HTML that asserts sizes = gate. |
| “We already audited” / yesterday’s pack | SHA-bind surface + paths + font hashes + still; drift ⇒ **re-run**. |
| “G0 / bindings passed” | Functional rail ≠ optical rail. |
| “C++ inspection PASS” | **Forbidden** as sole proof. |
| “impeccable said PASS in chat” | Written role table + MEASURED.json required. |
| Parent agent said proceed | Only Captain waiver string unlocks (§ Waiver). |

---

## Tiers (so the gate is not skipped for weight)

**Declare tier in writing before edits. Undeclared = T0. Lying about tier = violation.**

| Tier | When | Minimum fanout |
|------|------|----------------|
| **T0 — Full optical lock** | New surface, new type ladder, new face, MAIN/shell redesign, first HTML→firmware port | Source inventory + measured ink + craft + forensic ladder + skill lenses + visual decision board + full § Evidence pack |
| **T1 — Role rebind** | Reassign existing tokens/faces; no new faces | Source inventory **delta** + measured before/after crops + updated locked role table + receipt + MEASURED.json |
| **T2 — Geometry-only** | Pad/align/gap; **no** font token change | Geometry/ink-gap measure + squint note + cite **current locked** pack SHA + receipt + MEASURED gaps |
| **T3 — Exempt** | Non-UI; pure docs; pure protocol; pure audio/DSP; research HTML marked `NON_PRODUCT` (may not be cited as firmware authority) | No optical pack — **does not** unlock later UI code |

### Fanout producers (anti-rubber-stamp)

- **≥2 independent producers** OR one producer + one **adversarial** reviewer on the pack.  
- Invented px without crop = fraud → BLOCKED.  
- Specialists when T0 (load-bearing ledger): `deep-technical-analyst`, `ui-ux-designer`, `ui-visual-validator`.  
- T1/T2 may slim specialists if receipt states why; measurement still required.  
- Local skills: `k1-tab5-lvgl-dashboard` **mandatory** for LVGL/Tab5 **after** gate PASS path starts; `impeccable` / `apple-design` / `emil-design-eng` = **lenses only** (fixed px on embedded; fluid/clamp = FAIL).  
- Measured ink **beats** aesthetic preference — no averaging away P0 inversions.

---

## Thinking constraints (encode)

| Model | Constraint |
|-------|------------|
| **Map–territory** | Maps: `--size`, CSS px, C++ fonts, bounds JSON, G0, checklists. Territory: measured ink on opened still + SHA-pinned MEASURED.json. |
| **OODA** | Observe stills → Orient ladder → Decide PASS/FAIL → **then** Act on firmware. Coding first = **false tempo**. |
| **Systems** | Ban: title collision → shrink hero → chrome louder. |
| **Steel-man** | Strongest “ship faster without audit” → reject; session proves Observe was skipped. |
| **Red team** | ≥3 bypass attempts against **this** pack in receipt before PASS. |
| **Archetypes** | Shifting burden (metrics≠pixels); fixes that fail (shrink hero); accidental adversaries (Flex vs FLOATING). |

Prefer indexing large packs (context-mode) over dumping full audits into the prompt.

---

## Evidence pack (prose alone cannot PASS)

Under the **active project's** `_scratch/<lane>_YYYYMMDD/` (or project `docs/`
if that tree is the local convention). Teaching packs and process canon remain
in K1 Firmware at the absolute paths above.

| Artefact | T0 | T1 | T2 |
|----------|----|----|-----|
| `OPTICAL_GATE_RECEIPT.md` (one page: tier, surface, SHA pins, ladder ≤20 rows, P0, PASS/FAIL, paths) | ✓ | ✓ | ✓ |
| `SOURCE_INVENTORY.md` (or json) | ✓ | ✓ delta | cite locked |
| Still PNG (sim or device) | ✓ | ✓ | ✓ |
| Annotated crop PNG(s) | ✓ | ✓ | ✓ if geometry |
| `MEASURED.json` (machine-readable; see schema below) | ✓ | ✓ | gaps OK |
| `ROLE_LADDER_LOCKED.md` | ✓ | ✓ | cite SHA |
| `FORBIDDEN_FIXES.md` | ✓ | ✓ | ✓ |
| `SKILL_LENS_NOTES.md` | ✓ | short | short |
| Red-team subsection in receipt | ✓ | ✓ | optional |
| Visual decision HTML board | as needed | as needed | rare |

### `MEASURED.json` minimum (normative)

```json
{
  "surface_id": "tab5.deck.main",
  "still_png": "/absolute/path.png",
  "still_sha256": "...",
  "source_paths_sha256": { "deck_ui.cpp": "...", "deck_type.h": "..." },
  "roles": [
    {
      "role": "mode_hero",
      "token": "DISPLAY_40",
      "face": "countach",
      "nominal_size_px": 40,
      "line_height_px": 29,
      "ink_height_px": 28,
      "measure_method": "crop_amber_bbox",
      "crop_png": "/absolute/path.png"
    }
  ],
  "ladder_sorted_optical_desc": ["..."],
  "p0_inversions": ["wing_chevron > mode_hero"],
  "verdict": "FAIL"
}
```

**Anti-forgery:** `ink_height_px` without `crop_png` ⇒ invalid. `verdict: PASS` with non-empty `p0_inversions` without Captain exception ⇒ invalid. Missing `source_paths_sha256` for any file to edit ⇒ BLOCKED. Ladder sort must match measures (±1 px).

### PASS predicates (all required)

1. Tier declared and appropriate.  
2. Mandatory artefacts for tier at absolute paths.  
3. Vision-Read of primary still (craft sentence matches pixels).  
4. Locked ladder — no TBD.  
5. No unaccepted P0 inversion.  
6. HTML not LVGL authority without conversion table.  
7. Red-team subsection (≥3 attacks) for T0/T1.  
8. Receipt **and** MEASURED.json say PASS.

Long FONT_SIZE_* audits are **annexes**; the receipt is the PASS key.

---

## Captain waiver (only override)

Exact intent required in `WAIVER.md` (or receipt section):

```text
CAPTAIN_WAIVER_UI_PRECODE_OPTICAL_GATE
surface: <id>
tier_bypassed: T0|T1|T2
reason: <one sentence>
expires: <ISO-8601 or “end of session”>
post_condition: optical pack required before next UI commit / yes-flash
signed: Captain
```

Does **not** turn FAIL measures into PASS. Does **not** waive flash/identity/cal gates. Parent-agent “proceed” ≠ waiver. Next UI touch still needs a pack.

---

## Dual rail

- **Functional rail:** bindings, protocol, identity, build, G0.  
- **Optical rail:** this gate.  
- **Flash rail:** Captain go + device identity.  

Neither functional nor flash substitutes for optical PASS before UI look edits.

---

## After PASS / FAIL

- **PASS:** return to `/spectrasynq-ui-router` table → usually `k1-tab5-lvgl-dashboard` / scoped UI code; prefer `native_sdl`; flash/commit only on Captain go; re-Observe new still after edits (OODA re-entry).  
- **FAIL:** stop product UI sources; continue audit-only under the active project's `_scratch/`.  
- Post-session: `skills_used: spectrasynq-ui-router, spectrasynq-ui-precode-optical-gate`.
