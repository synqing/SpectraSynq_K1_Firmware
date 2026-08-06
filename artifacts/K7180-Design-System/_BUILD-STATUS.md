---
abstract: "Live build tracker + SSA delegation ledger for the K718 Remoted circular design system. Read FIRST on resume — it records what is locked, what is in-flight, and which sub-agent produced which evidence. Survives /compact. Captain decisions: full system + component gallery; rationalize full taxonomy."
---

# K718 Remoted — Circular Design System · Build Status

**Working dir:** `artifacts/K7180-Design-System/`
**Started:** 2026-06-29 · **Branch:** `lane/remoted-ble-midi-phase-f`
**Captain decisions (locked):** (1) Deliverable = **full system + component gallery**, referencing the 4 boards. (2) Naming authority = **rationalize the full taxonomy** (rename for coherence where it improves the system; product names K1 / K718 Remoted stay fixed).

## Why this exists
K718 dashboard was frozen 2026-06-29 after a decorative-variant-dial churn loop (the boards' own DON'T column forbids "more variant dials"). Diagnosis: **Fixes-That-Fail** archetype — the missing leverage point is a single written, normative, locked spec. This folder builds that spec so variation can only happen *inside* the grammar. Memory note "resume only with locked spec" → this IS the locked spec.

## Source of truth (reference, do not redesign)
- `00.UI-Overview.png` — handover overview (objective, ring grammar, screen set, theme territories, principles, DO/DON'T)
- `01.OS-Grammar.png` — fixed rules (ring roles, gesture model, mode hierarchy, canonical screen Qs, A/B logic, progressive disclosure)
- `02.Occlusion-Zones.png` — hardware validation (zone anatomy, legibility ladder, contrast, occlusion, focus behavior)
- `03.Dashboard-Concept.png` — worked example (Zero-G Bazaar theme, trust states, mode compass, promotion lane)

## Deliverable map (full system)
| Layer | Artifact | Status |
|---|---|---|
| Canonical spec | `spec/K718-DESIGN-LANGUAGE.md` | ✅ v0.1 (§5 firmware-verified) |
| Evidence base | `spec/_design-evidence.md` | ✅ DLG-02 |
| Tokens | `tokens/tokens.json` + `tokens/tokens.css` | ✅ contrast-verified |
| Radial grid skill | `.claude/skills/k718-radial-grid/SKILL.md` (NEW — fills polar-UI gap) | ✅ |
| Component gallery | `reference/{index.html, halo.js, gallery.css}` | ✅ renders 20/20 dials, 0 errors |
| Visual proof | `reference/_proof-gallery.png` (Playwright headless) | ✅ |
| Audit gate | design-is (Rams) + Vignelli + visual-validator + contrast | contrast ✅; A1/A2/A3 in-flight |

## Proof (no completion without proof)
- Playwright headless render: **20/20 dials, 0 config errors, 0 console errors**.
- WCAG contrast (computed vs bg #06070A): text 20:1, focus 11.4:1, active 9.5:1, confirm 10.9:1, alert 6.2:1, violet 5.9:1 — all AA+. Magenta actual 7.1:1 (claim corrected from 8.1).
- The single token-driven renderer (`halo.js`) IS the validation gate for the `k718-radial-grid` skill — gallery builds from it.

## OPEN — Captain decision (K1 product truth, surfaced not assumed)
DLG-01 found the Readout promises **KEY** + **TIME** that the firmware cannot provide (no key detection; no time-sig), and the BLE transport is pre-production (production = WiFi/WebSocket; only BPM crosses the wire). Honesty Rule H-1 currently marks them ASPIRATIONAL ◇. Decision = drop / keep-as-roadmap / commit-to-build. See response.

## Rationalization decisions (the core "define" work)
- **R1 — State axes split.** Boards conflate disclosure + trust. Resolved into THREE orthogonal concerns: **Attention ramp** (Glanceable→Aware→Engaged→Focused) × **Trust lifecycle** (Pending→Committed) × **Alert overlay** (interrupt). See spec §Patterns.
- **R2 — Ring roles** get canonical IDs + names (bezel→center).
- **R3 — Theme Territories** names preserved (brand/product identity); formalized as token *sets* (palette + motion + density profile).
- **R4 — Mode taxonomy** pending DLG-01 firmware verification before lock.

## SSA delegation ledger
| ID | Role | Class | Status | Evidence consumed |
|---|---|---|---|---|
| DLG-01 | Firmware map↔territory (Explore) | load-bearing | **received** | SHAPE/MOTION/SYSTEM=BACKED; SIGNAL/SCENE=PARTIAL; KEY/TIME=ASPIRATIONAL; BLE pre-prod; PEND=UX-local. Integrated into spec §5 + Honesty Rule H-1 |
| DLG-A1 | Rams design-is audit (UI Designer) | load-bearing (craft) | **received** | Grammar strong; fixes: name fonts/LVGL, motion ms, ◇ in renders, austere theme canonical, status-strip spec |
| DLG-A2 | Vignelli restraint audit | load-bearing (craft) | **received** | violet contaminant (fixed), 5→3 trust-zone (fixed), per-size tracking (fixed), 6-rung floor, territory names will date |
| DLG-A3 | Visual defect validation | load-bearing (craft) | **received** | M-1 trust lifecycle not differentiated (fixing: committed=green confirmRing); Mode Compass caption; no blockers |

## Captain decisions (2026-06-29, locked)
- **Transport = BLE-only** (WiFi rejected, instability). Spec §5.1b rewritten. Readback gated on extending BLE feedback channel (today: mode-number only).
- **KEY/TIME = committed K1 DSP roadmap** — render ROADMAP ◇, not live. Spec §5.1a.
- **No theme is married** — theme space wide open; mechanism locked, specific themes are exploration candidates. Spec §1.3b/§6.3 reframed. → 6-way theme fan-out:

## Theme exploration ledger (DLG-T1..T6, on-grammar — swap token set, no new dials)
| ID | Direction | Status | Result |
|---|---|---|---|
| T1 | Austere instrument | **received** | `measurement-grade` — dark mono cool, oscilloscope; contrast ✓ |
| T2 | Daylight-legible | **received** | `daylight-panel` — light field, deep-pigment accents; contrast ✓ |
| T3 | Warm analog | in-flight | — |
| T4 | Mono restraint | **received** | `neutral-field` — grayscale-at-rest, color on active; contrast ✓ |
| T5 | Vivid editorial | in-flight | — |
| T6 | Refined dark-luminous | in-flight | — |

## Craft fixes applied (theme-independent)
tokens: violet removed from semantic namespace; trust-zone 5→3 steps; committing=amber (no yellow collision); per-size tracking; micro floor→AA. halo.js: confirmRing (committed=green), 3-step truth ring. Pending: trust-lifecycle gallery configs, Mode Compass caption, theme board rebuild, re-render.
| DLG-02 | Forensic design extraction (deep-technical-analyst) | load-bearing | **received** | `spec/_design-evidence.md` — 6-rung ladder (not 7), "Signal Core" is HALO coinage, 9 semantic accents, ENGAGED/FOCUSED hue drift, 26-component inventory, "TRUSE"=typo |

## Reconciliation flags consumed (from DLG-02)
- Legibility ladder = **6 rungs** (T1–T6) ✓ spec already correct
- Ring "Signal Core" appears on no board (only "Inner Core") — kept as HALO canonical coinage per R2; synonym table credits "Inner Core" ✓
- **9 semantic accents** (more than the 5 in spec §1.3a) — expand in tokens
- ENGAGED/FOCUSED hues drift across boards — pick canonical hue per accent in tokens (semantic = fixed meaning)
- Component inventory = 26 rows — cross-check gallery covers all; spec §3 lists the 14 structural ones

## Artifacts done
- `spec/K718-DESIGN-LANGUAGE.md` — v0.1 canonical spec ✓
- `.claude/skills/k718-radial-grid/SKILL.md` — NEW skill, polar-grid gap filled ✓ (validation gate = gallery builds from it)

## ⤳ DIRECTION PIVOT (2026-06-29, evening) — the real deliverable
Captain clarified across a rapid sequence: (1) **BLE-only** transport; (2) KEY/TIME = future DSP roadmap; (3) **no theme married** — explore freely; (4) **ALL ring/section text MUST CURVE to its radius** (hard rule — only the central readout stays straight); (5) the board's elaborate semantic grammar (5 accents, trust lifecycle/PEND, attention ramp, A/B, alert) is over-built — the ONE status that matters is a **BLE glyph: green=connected / red=not**; (6) **PROCESS:** I must NOT decide which layers to keep — Captain "has no idea of the jargon" and needs **every layer RIPPED OUT and presented ISOLATED for inspection**, modeled on the **web-design-jargon-guide** (`~/Workspace_Management/Software/premium-site-harness/output/web-design-jargon-guide/`).

**New deliverable:** a **K718 design-jargon / element-inspection guide** — each design layer/element shown ALONE as a live HALO specimen, named + plain-language defined + provenance + a **KEEP / CUT / CHANGE** verdict slot for the Captain to rule on each. The earlier "full system" is the *source* of layers to isolate, not the ship target.

**Renderer:** `halo.js` rebuilt as a **layer-isolation engine** (every layer = independent toggleable element, self-sufficient color fallbacks, curved text throughout).

## SSA swarm (context for the guide — Captain-ordered, claude-mem digs)
| ID | Task | Status |
|---|---|---|
| DLG-J1 | Jargon-guide format forensics (reproduce the template) | **received** — full template |

## CAPTAIN DECISIONS (from element-guide export, 2026-06-29) — LOCKED
KEEP: canvas, safe, led, encoder, bezel (crown-top SACRED), readout, telltale.
CHANGE: bands→outer ring = BPM-reactive sweep · arctext→curved YES but off-crown/no-collision/on-screen · dotring→reimplement clean · spectrum→RADIAL only (no straight bars) · paramarc→keep, polish · stateedge→stop overlap (folded into keel mode-name) · truthring→rework, no collisions · themes→gate in User Settings (single active on dial).
CUT: ticks, needle, focus/active/confirm rings, alert.
**Hard laws (now design contract):** L1 EVERYTHING RADIAL (no straight lines) · L2 ZERO COLLISIONS / nothing clips or leaves screen · L3 CROWN SACRED (telltale only). TODO: encode L1–L3 + cut-list + themes-in-Settings into spec §+ k718-radial-grid skill.

## ✅ live.html REBUILT v2 (2026-06-30) — addresses all CHANGE notes
Radial equalizer (radiates from centre) · BPM comet-sweep on largest ring · mode name curved at keel (no crown collision, on-screen) · active dot paired at keel · PHOTONS/MOOD side arcs · single theme (others = Settings) · ticks/needle/focus/alert removed · crown = telltale only. Playwright 0 errors, collision-free verified.

## (superseded) earlier `reference/live.html` — ANIMATED INTERACTIVE dial
Canvas 60fps, vibrant, self-contained. Real 22 K1 modes; ring spins to the selected mode (scroll/←→/drag); animated spectrum (simulated — audio-over-BLE is roadmap, honest); live PHOTONS/MOOD param arcs (real BLE controls); BLE telltale + 13-LED ring pulse green/red (B toggles); confirm-bloom + beat-pulse; T cycles vibrant themes; space = auto-demo. Playwright-verified, 0 errors; video proof in scratchpad/vid/.

## ✅ DELIVERED: `reference/element-guide.html` — the inspection guide
22 layer cards across 5 chapters (Hardware · Grid · Content · Status · Colour&Type), 25 live isolated HALO specimens, 0 render/console errors (Playwright-verified). Each card = name + correct jargon (aka) + isolated live specimen + plain-English definition + BACKED/ROADMAP/FAKE/FLAGGED firmware tag + provenance + a clickable **KEEP/CUT/CHANGE** decision (persists to localStorage). Modeled on the Captain's web-design-jargon-guide (brand void/gold, glass cards, replay, spec-tag). Captain inspects each layer & rules; agent pre-decides nothing. **NEXT: Captain walks the guide and rules; then rebuild the dial from KEPT layers only.**
| DLG-J2 | claude-mem K718 UI element history + Captain verdicts | **received** — full inventory |
| DLG-J3 | claude-mem K718/K1 design decisions + brand constraints | **received** |
| DLG-J4 | Circular-instrument UI jargon reference (correct terminology) | **received** |

## ⚠ LOAD-BEARING CONSTRAINTS surfaced by swarm (must shape the guide)
- **Device = Guition JC3636K718, 360×360 round IPS** (NOT 480×480 — the boards were wrong; my HALO spec inherited the error). Legibility floors are physical-size-calibrated. Flag for reconciliation.
- **BUILDABILITY (axis 4): LVGL 8.3.11 SW-render, ESP32-S3 — NO arc-text, NO dashed arcs, NO radial gradients, NO native blur, NO morphing waveform.** ⇄ **CONFLICT** with Captain's "all radial text MUST curve" mandate → surface on the arc-text layer card (Captain's call wins; flag per-glyph feasibility, don't silently obey/ignore).
- **Vibrant mandate (Captain, obs #72078):** muted palette REJECTED — dial must be vibrant/high-saturation. Tempers the Rams "austere canonical" lean; vibrant leads.
- **Oswald = BANNED font** (brand violation) — FIXED (swapped web proxy → Saira Condensed).
- **Brand:** Void `#060606`; Brand Gold `#FFB84D` = sole accent, never flat fill except 1 CTA. (Dial vibrant mandate may extend this — flag layer.)
- **Rim-text rule (text-protection principle):** allowed only with (1) size≥floor AND (2) keep-out scrim. Live values must PROMOTE to centre (rim = static/learned only: wordmark, ticks, min/max anchors, mode-family legend).
- **Role hypothesis P2 — Performance Knob:** eyes-free live shaping, one big readout, ring+haptic confirm; Tab5 owns deep settings.
- **Honesty H-1:** value is "live" only once it crosses the BLE feedback channel (today: mode-number only).
- Jargon authority (J4): bezel · chapter ring · arc-text/radial-label · readout/register · graduation marks/indices · pointer/needle/hand · sub-dial/register · arc gauge · **telltale** (ISO 2575 — the BLE light) · safe area/inscribed rectangle · keep-out zone.
- **13-LED physical ring (outside the glass) = the REAL trust surface** (hue+motion+extent; obs #71830). On-SCREEN trust rings (Truth Ring/Promotion Lane/Confirm Pulse) are aspirational — flag them.
- **Encoder is ROTATION-ONLY, no hardware press** (`KNOB_LEFT/RIGHT`). "Press to confirm" gestures may lack hardware backing — honesty flag on gesture/promotion layers.
- Full layer list to isolate (J2): hardware [display canvas, safe radius, 13-LED ring, rotation-only encoder] · bands [B0 bezel-safe, B1 nav ring, B2 control ring, B3 signal core, B4 readout] · zones [crown/right/keel/left] · 14 closed components [readout, dot-ring, nav labels, signal viz, active arc, focus ring, confirm pulse, BLE telltale, truth ring, promotion lane, mode compass, status strip, A/B, alert] · supplementary [needle/pointer, LED bloom ring, bezel, PHOTONS/MOOD param arcs, state-edge label, palette rim, family-sector arc, glow filter, grid guides, screen bg] · themes [5 board + 6 explored].

## State of earlier artifacts (recoverable, not committed)
spec/tokens/gallery reflect the pre-pivot "full system" + partial simplify. All current file-state, fully editable. The jargon guide is the next build once the swarm lands.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-29 | agent:claude-code | Created tracker; Phase A/audit/theme swarms; **PIVOT** → isolated-element jargon guide; halo.js → layer-isolation engine; J1–J4 swarm dispatched |
