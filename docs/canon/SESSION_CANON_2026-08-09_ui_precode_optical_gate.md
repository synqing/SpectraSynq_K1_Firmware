---
abstract: "Session canon for 2026-08-08→08-09 Precision Bay R1 / Deck16 Structural Repair R1 — font/optical hierarchy failures, layout-system contradictions, map≠territory UI thrash. Immune memory so agents never code SpectraSynq UI from C++ or prose alone."
status: active_canon
date: 2026-08-09
evidence_primary: _scratch/precision_bay_r1/
architecture: K1_DECK16_TAB5_BLE_R1
skill: spectrasynq-ui-precode-optical-gate
process: docs/process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md
thinking_models: [systems, map-territory, ooda, steel-manning, red-team, model-router, archetypes]
redteam: _scratch/precision_bay_r1/UI_PRECODE_GATE_REDTEAM.md
---

# Session Canon — UI Pre-code Optical Gate (2026-08-09)

**Reader:** every future agent touching SpectraSynq **operator UI** — Tab5 Deck16
`deck_ui*`, soft-key sheets, HTML-as-product surfaces, theme/type tokens, or any
design→firmware path that claims optical craft.

**Purpose:** not a diary. This is the **immune memory** of a multi-day UI session
that burned wall-clock rediscovering that **nominal font px ≠ ink**, that
**C++ inspection is not glass proof**, and that **shrinking the hero to dodge a
title** is a systems failure. Violating the HARD FAIL table is a process
incident.

**On-disk evidence beats memory.** Primary pack:
[`_scratch/precision_bay_r1/`](../../_scratch/precision_bay_r1/).

**Mandatory gate skill before UI code:**
[`spectrasynq-ui-precode-optical-gate`](../../.claude/skills/spectrasynq-ui-precode-optical-gate/SKILL.md)
· process doctrine:
[`docs/process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md`](../process/SPECTRASYNQ-UI-PRECODE-OPTICAL-GATE.md).

---

## 0. One-line map of the session

| Thread | Outcome | Status |
|--------|---------|--------|
| **A. Precision Bay visual system** | Captain rejected Bay chrome (grid / CH rails / dock look) as destination | **STOPPED** — functional G0 freeze kept |
| **B. G0 registry / soft-key freeze** | 7/7 bindings map-valid; empty-sheet + TX honesty bans | **PASS** (functional) |
| **C. Structural Repair R1** | Restore pre-Bay 4-box MAIN + KEEP optical/type layers | Landed on sim + flash per receipt; **type hierarchy still FAIL** |
| **D. Font / optical fan-out** | Source + measured + forensic + craft + skill audits | **Scale ladder FAIL** — gate invented so this never ships again without PASS |
| **E. Mode widget geometry** | Declared vs ink gaps; contract 12–14 ≠ achieved ~27 | Geometry pack exists; title/hero systems still wrong |

---

## 1. Complete lessons inventory

### 1.1 Failures (paid for in wall-clock)

| ID | Failure | Evidence |
|----|---------|----------|
| **F-1** | Treated LVGL / CSS **nominal `--size` / `font-size: Npx`** as optical height | Countach 40 → `line_height` **29** (~71%); HTML px ≠ LVGL ink (`FONT_SIZE_FORENSIC_AUDIT.md`) |
| **F-2** | **Shrunk mode hero** (55/89 → 40) to clear zone titles instead of fixing title geometry / role | Craft + forensic: collision workaround neuters hero (`FONT_SIZE_CRAFT_ASSESSMENT.md`) |
| **F-3** | Put **Mono55 on chevrons** — navigation chrome outranked mode Countach40 | Skill audit P0; measured object lh 57 vs hero 29 |
| **F-4** | **`MONO_34` semantic landfill** — brand, LINK, names, bus chips, sheet titles+values, % | Source inventory call-site map |
| **F-5** | **Flex + `FLOATING` + negative margin + translate** stacked on soft-key dock | Restore strategy KEEP ban; Structural Repair removed |
| **F-6** | **`pair_w` / `pair_x` recenter** walked palette index with name length | Restore KEEP; anchored fixed `index_x` |
| **F-7** | Shipped / nearly shipped **empty soft-key sheets** (`NO CONTROLS ON GLASS YET`) | G0 fail-closed; Structural Repair wired `deck_ui_sheets_build` |
| **F-8** | **Local-send-as-confirmed** (optimistic confirm before remote ACK) | G0 ack = `LOCAL_SEND_ONLY` / `SENT_UNCONFIRMED` only |
| **F-9** | **Text-only visual decisions** / C++-only PASS claims | Captain doctrine + pixel-inspect rules; glass requires PNG Read + `open -g` |
| **F-10** | **Bay chrome thrash** as product identity while functional freeze was the real keep | `VISUAL_RESTORE_STRATEGY.md` — G0 ≠ look |
| **F-11** | **G0-before-pixels** — celebrating registry PASS as visual done | G0 packet: functional only; visual destination separate |
| **F-12** | Zone titles / soft keys at **Mono21** (~14 px ink / ~1.6 mm) below instrument floor | Craft assessment; measured audit |
| **F-13** | Mode vs palette hero **DISPLAY_40 vs DISPLAY_55** without intentional hierarchy story | Forensic + skill audits |
| **F-14** | Token **comment drift** (`MONO_55` = brightness %; brightness uses 34; chevrons steal 55) | Source + skill audits |
| **F-15** | **`DISPLAY_89` linked, zero call sites** — dead embedded font weight | Forensic audit |
| **F-16** | Declared **numeral→name gap contract ~12–14** vs measured ink **~27–28** | `MODE_WIDGET_GEOMETRY_AUDIT.md` |
| **F-17** | Stale bounds dumps treated as live geometry (name Y 100 vs live 88) | Geometry audit §B/D |

### 1.2 Root causes

1. **Map≠territory:** source tokens, HTML CSS, font-converter `--size`, and LVGL `line_height` were treated as interchangeable maps of ink on glass.
2. **Role≠size:** agents assigned faces by leftover ladder rungs instead of locking an **optical scale ladder by role** (hero / name / title / chrome / telemetry).
3. **Symptom treatment:** title collision → shrink hero (balancing loop that digs the hole deeper) instead of re-orienting title geometry.
4. **Layout polyglot:** multiple positioning systems on one parent produce un-debuggable drift.
5. **Gate inversion:** functional registry freeze (G0) was allowed to feel like visual completion.
6. **No fail-closed optical gate** before design→code — inventing sizes/paths was cheaper than measuring.

### 1.3 Insights (keep forever)

1. Countach Bold Italic ≈ **~71%** of nominal `--size` as LVGL `line_height` / digit ink — **face-specific measurement required**.
2. Berkeley Mono ladder 21/34/55 is harmonically clean; **which role sits on which rung** was the failure.
3. **One positioning system per parent** — Flex *or* absolute *or* floating; never Flex+neg-margin+translate+FLOATING.
4. **Anchored palette index X** — never recentre from name string width.
5. **Functional G0** (bindings, empty-sheet ban, honest lamps, TX honesty) is independent of **visual destination**.
6. Visual destination after Bay rejection = **Deck16 Structural Repair R1** (pre-Bay 4-box amber instrument), not Bay theme.
7. Screenshots / HTML boards must be **`open -g`** + **vision Read**; metrics/magenta/SHA alone ≠ craft PASS.
8. Prefer **indexing** large evidence packs (context-mode / corpus) over dumping full audits into the prompt.

### 1.4 Resolved problems (do not re-open as unknowns)

| Resolved | How | Receipt |
|----------|-----|---------|
| Soft-key F01–F07 map bindings | G0 freeze + manifest | `G0_PACKET.md`, `ui/spec/deck_softkey_manifest.json` |
| Empty sheet shells on glass | Sheets build from manifest paths | `STRUCTURAL_REPAIR_R1_RECEIPT.md` |
| Hard-coded EDGE/SMART lamps ON | Lamps start OFF; honest feedback | same |
| Local→confirmed TX lie | `SENT_UNCONFIRMED` / bump-sent only | same + G0 |
| Bay as visual master | Captain STOP; restore strategy | `VISUAL_RESTORE_STRATEGY.md`, `GATE_STATUS.md` |
| Soft-key FLOATING/neg-margin/static translate | Real Flex; press translate only | Structural Repair receipt |
| Palette `pair_w` recenter | Fixed `index_x = WING_W+8` | same |
| LINK/RSSI fused string | Fixed `"RSSI"` title + value slot | same |
| Mode numeral 55/89 title collision (partial) | Mode uses DISPLAY_40 @ y=36 | **Partial only** — title/hero hierarchy still FAIL pending optical gate PASS |

### 1.5 Evidence index (absolute pack)

| Artefact | Path |
|----------|------|
| Font source inventory | `/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/precision_bay_r1/FONT_SIZE_SOURCE_INVENTORY.md` |
| Font measured ink | `…/FONT_SIZE_MEASURED_AUDIT.md` |
| Font forensic | `…/FONT_SIZE_FORENSIC_AUDIT.md` |
| Font craft | `…/FONT_SIZE_CRAFT_ASSESSMENT.md` |
| Font skill audit | `…/FONT_SIZE_SKILL_AUDIT.md` |
| Mode geometry | `…/MODE_WIDGET_GEOMETRY_AUDIT.md` |
| Visual restore | `…/VISUAL_RESTORE_STRATEGY.md` |
| Structural Repair receipt | `…/STRUCTURAL_REPAIR_R1_RECEIPT.md` |
| G0 packet / re-freeze | `…/G0_PACKET.md`, `…/G0_REFREEZE_RECEIPT.md` |
| Gate status | `…/GATE_STATUS.md` |
| Sim PNG | `…/STRUCTURAL_REPAIR_R1_SIM.png` |
| Lessons copy (scratch) | `…/LESSONS_INVENTORY.md` |
| Red-team / bypass suite | `…/UI_PRECODE_GATE_REDTEAM.md` |

---

## 2. HARD FAIL table (do not re-learn)

| ID | HARD FAIL | Why we paid | Correct stance |
|----|-----------|-------------|----------------|
| **HF-UI-1** | Code UI from **C++ / token inspection alone** and claim optical PASS | Map≠territory; glass lied | Fan-out optical gate **PASS** before design→code |
| **HF-UI-2** | Trust **HTML CSS px** or LVGL `--size` as ink height | Countach ~71% of nominal | Face-specific measured ink / line_height |
| **HF-UI-3** | **Shrink hero** to clear a colliding title | Neutered instrument datum | Fix title role/geometry; protect hero optical height |
| **HF-UI-4** | Put **largest Mono on chevrons / chrome** | Hierarchy inversion | Chrome ≤ content; chevrons subordinate |
| **HF-UI-5** | One token for incompatible roles (**Mono34 landfill**) | Squint test fails | Lock optical scale ladder by **role** |
| **HF-UI-6** | Flex + FLOATING + neg-margin + translate on one parent | Undebuggable layout | **One positioning system per parent** |
| **HF-UI-7** | `pair_w` / string-width **recenter** of fixed index columns | Index walks with name | Anchored fixed X |
| **HF-UI-8** | Empty soft-key sheets / invented map paths | Operator dead controls | Fail-closed; manifest + map only |
| **HF-UI-9** | Local send painted as **remote confirmed** | False operator trust | `SENT_UNCONFIRMED` until real ACK |
| **HF-UI-10** | **Text-only** visual decisions / boards without PNG/HTML opened | Captain cannot judge prose | Visual decision board + `open -g` + pixel Read |
| **HF-UI-11** | Treat **G0 / registry PASS** as visual done | Bay thrash after freeze | Functional freeze ≠ look |
| **HF-UI-12** | Invent sizes, paths, or guesses when evidence missing | Silent fabrication | **BLOCKED** — measure or stop |
| **HF-UI-13** | Drive MAIN look from **Bay tokens / theme-bay CSS** after rejection | Wrong destination | Structural Repair 4-box (or Captain-named successor) |
| **HF-UI-14** | Skip specialist fan-out on UI design→code | Single-agent blind spots | Source + measured + craft + forensic (+ skills listed in gate) |
| **HF-UI-15** | Skip gate for “small nudge” / clip bugfix / sim-only / colour-only hierarchy | Red-team §3.1 carve-outs | No byte-count exemption; declare tier; undeclared = T0 |
| **HF-UI-16** | Launder **stale** `_scratch` packs without SHA-bind | Red-team §3.2 | Surface + path + font + still hashes; drift ⇒ re-run |
| **HF-UI-17** | Rubber-stamp PASS with prose / TBD / skill-name drop-ins | Red-team §3.4 | `OPTICAL_GATE_RECEIPT.md` + `MEASURED.json` + crops only |
| **HF-UI-18** | Apply web fluid/`clamp`/responsive type to fixed LVGL | Red-team §3.6 | Fixed px optical targets; embedded skill mandatory |
| **HF-UI-19** | Overweight every change as T0 until agents skip the gate | Red-team §4.1 | Use T0/T1/T2/T3 honestly |
| **HF-UI-20** | Treat parent “proceed” or red-team doc as unlock | Red-team §3.7 / §6 | Captain waiver string only |

### Agents must never (ban list — red-team §5.3)

1. Never write UI firmware before an optical PASS receipt.  
2. Never treat `--size` / CSS px as optical height.  
3. Never assign instrument-size tokens to chrome (chevrons/arrows/rules).  
4. Never dump unrelated roles onto one token (Mono34 landfill).  
5. Never shrink the hero to fix a title/geometry collision.  
6. Never stack Flex + FLOATING + translate + negative margin on one parent.  
7. Never claim PASS from text-only design discussion or C++ skim.  
8. Never cite G0/functional freeze as visual authority.  
9. Never reuse a prior audit pack without SHA-binding to current paths/stills.  
10. Never apply web fluid-typography skills as LVGL law.

### Canon sentences (memorise)

1. **The map is not the glass** — C++, CSS px, and `--size` are maps; measured ink on a PNG is territory.
2. **Roles own the ladder** — never assign leftover sizes to heroes and chrome.
3. **Do not shrink the hero to forgive the title.**
4. **One layout system per parent.**
5. **G0 freezes function; pixels freeze look.**
6. **Inventing geometry is a hard stop, not a shortcut.**
7. **The checklist is not the audit** — PASS keys are SHA-pinned receipt + MEASURED.json + crops.
8. **False tempo is Act-before-Observe** — coding first recreates the thrash loop.

---

## 2b. Gate tiers & evidence (absorb red-team §4 / §7)

| Tier | When | Minimum |
|------|------|---------|
| T0 | New surface / ladder / face / MAIN redesign | Full fanout + board |
| T1 | Role rebind, no new faces | Delta inventory + before/after crops |
| T2 | Geometry only | Ink gaps + cite locked ladder SHA |
| T3 | Non-UI / docs / protocol / DSP | Exempt (does not unlock UI) |

**PASS keys:** `OPTICAL_GATE_RECEIPT.md` + `MEASURED.json` (still/crop/source SHA pins) + vision-Read. Prose alone cannot PASS. Prior FAIL audits under `_scratch/precision_bay_r1/` are **teaching territory**, not PASSes.

**Bypass regression suite:** `_scratch/precision_bay_r1/UI_PRECODE_GATE_REDTEAM.md` §3 — wording that softens those counters reopens the failure.

---

## 3. Systems / OODA / red-team encoding (why the gate exists)

**Systems (reinforcing failure):** title collision → shrink hero → hero weaker than chevrons → agent ups chevron size for “affordance” → hierarchy worse → more collision pressure.

**Map–territory traps paid for:**

| Map trusted | Territory measured |
|-------------|-------------------|
| `font-size: 55px` / `--size 55` | Countach lh **39**; Mono55 chevron object **57** |
| “Mode uses 40 so titles clear” | Titles still Mono21 pitiful; hero below glance floor |
| G0 = PASS | Functional only; look STOPPED / superseded |
| Bounds dump name@100 | Live name@88; stale dumps poison math |
| Token comment “MONO_55 = brightness %” | Brightness % is 34; chevrons own 55 |

**OODA for UI:** Observe (PNG + ink + source) → Orient (role ladder + one layout system) → Decide (gate PASS/FAIL) → Act (code only after PASS). Never Act→Observe.

**Steel-man then kill:** strongest case for “just tweak one size in C++” dies against measured hierarchy inversion and Countach fill ratio.

**Red team before PASS:** “How will this claim lie?” — CSS mock, stale dump, sim without vision Read, G0 confusion, invented token.

---

## 4. Operating procedure (pointer)

Full fail-closed procedure lives in the skill and process doctrine. Minimum:

1. Bootstrap + read this canon + red-team bypass suite.
2. **Declare tier (T0–T3)** in writing; undeclared = T0.
3. Invoke **`spectrasynq-ui-precode-optical-gate`** — **BLOCKED** until receipt+MEASURED PASS.
4. Evidence pack: `OPTICAL_GATE_RECEIPT.md`, `MEASURED.json`, still + crops, locked ladder, forbidden fixes; long audits as annexes.
5. Only then edit UI firmware / HTML-as-product; re-Observe still after edits.
6. Native sim PNG before Tab5 flash; flash only on Captain go.
7. Waiver only via exact `CAPTAIN_WAIVER_UI_PRECODE_OPTICAL_GATE` block.

---

## 5. Relation to other canon

| Doc | Relation |
|-----|----------|
| `SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md` | Silence / BLE / boot — complementary; not replaced |
| `docs/architecture/TAB5_DECK16_SESSION_CANON_2026-08-07.md` | HCI / product identity / type face law |
| `.cursor/rules/tab5-deck16-guardrails.mdc` | Flash / map TX / Countach=numerals; now points at optical gate |
| Pixel-inspect / no-pink / visual-decision-html rules | Still bind Captain openables |

---

*Built 2026-08-09 so the failure never repeats. Choose legacy over liability.*
