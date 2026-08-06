---
abstract: "Forensic, normative evidence catalogue extracted verbatim from the four K718 Remoted / SpectraSynq K1 circular-UI design boards (00 UI-Overview, 01 OS-Grammar, 02 Occlusion-Zones, 03 Dashboard-Concept). Single citable source of truth for geometry/grid, ring roles, colour territories + state accents, the legibility ladder + contrast tables, the 6-gesture model + 4 encoder focus states, all overlapping state models (Progressive Disclosure / Trust State / Truth Ring / A·B logic), the 5 modes + 10 canonical screens, the full component inventory, the 6 principles + DO/DON'T, and thumb/finger occlusion zones. Read before authoring any design token. Naming inconsistencies between boards are listed verbatim for reconciliation."
---

# K718 Remoted — Design Evidence Catalogue (DLG-02)

> **Scope.** Every design fact extracted from the four reference boards. Values labelled `(visual estimate)` are visually implied, not printed on the board. Hue names for colours are approximations of rendered pixels; canonical hex is NOT printed on any board and must be sampled downstream. Verbatim text is quoted with `"..."`. Where two boards disagree, both variants are listed so the token system can reconcile.

**Board IDs used throughout:**
- **B00** = `00.UI-Overview.png` — "SPECTRASYNQ K1 — CIRCULAR UI HANDOVER OVERVIEW" (Operating Model / Briefing Map / Design Reset; VERSION 1.0 • MAY 2025 • INTERNAL DESIGN BRIEF)
- **B01** = `01.OS-Grammar.png` — "SPECTRASYNQ K1 — CIRCULAR OS GRAMMAR" ("THE FIXED RULES THE DESIGN AGENT SHOULD NOT VIOLATE."; INTERNAL DESIGN SPEC)
- **B02** = `02.Occlusion-Zones.png` — "K1 HARDWARE VALIDATION BOARD" (Circular-screen crop, legibility, and encoder realism)
- **B03** = `03.Dashboard-Concept.png` — "K718 REMOTED | EXAMPLE 5: ZERO-G BAZAAR" (Circular OS Dashboard Concept • Internal Review Board)

**Device identity (printed on B02 + B03 header bars):** DEVICE = `K1 Encoder` / `PHYSICAL ENCODER CONTROLLER` (B00); SCREEN = `Round LCD` / `CIRCULAR DISPLAY`; RESOLUTION = `480×480`; BEZEL OD = `Ø 68.0 mm`. Vendor lockup: "SPECTRASYNQ LABS — HARMONIC INTELLIGENCE — THE MUSIC. DECODED." / "FOR MUSIC. DECODED." Tagline footer (B02/B03): "DESIGN WITH PURPOSE • BUILD FOR FLOW • VALIDATE FOR REALITY". Footer (B00/B01): "A HARMONIC INTELLIGENCE OPERATING SYSTEM • BUILT FOR CREATORS • DESIGNED FOR FLOW".

---

## 1. GEOMETRY & GRID

All hard spatial facts. Source board cited per fact.

| Fact | Value | Source |
|------|-------|--------|
| Bezel outer diameter (OD) | **Ø 68.0 mm** | B02 header, B03 header |
| Active display diameter | **Ø 60.0 mm = 480 px** | B02 §01 callout "ACTIVE DIAMETER Ø 60.0 mm (480px)" |
| Display resolution | **480 × 480 px** (square frame, circular crop) | B02 + B03 header |
| Screen shape | Round LCD, circular crop of a 480×480 raster | B02 |
| **px↔mm scale** | **480 px = 60 mm → 8 px/mm** (1 px = 0.125 mm) | derived from B02 active-diameter fact |
| Active radius | 240 px = 30 mm | derived (480/2) |
| Bezel ring width (radial, OD→active edge) | (68−60)/2 = **4.0 mm = 32 px** each side | derived from OD vs active dia |
| Bezel-safe margin | **6% of radius ≈ 14 px** ("Recommended: 6% of radius (~14px)") | B02 §01 "BEZEL-SAFE MARGIN" |
| Bezel-safe margin in mm | 6% × 30 mm = **1.8 mm** (≈14.4 px, board rounds to ~14px) | derived |
| Safe-area diameter | 480 − 2×14 = **~452 px (Ø ~56.5 mm)** `(visual estimate / derived)` | derived from margin |
| Device preview scales (B02 §02) | "1X DEVICE SCALE" and "2X CLOSE-UP (DETAIL)" | B02 §02 |
| Target render performance | "60fps at target brightness" | B02 §07 checklist |

**Named radial bands (bezel → centre)** — see §2 for full role text. Ordering is the consistent concentric stack on every dial:
1. **Outer Ring** (navigation) — outermost ring just inside bezel-safe margin.
2. **Mid Ring** (active parameter control) — middle annulus, thumb-accessible.
3. **Inner Core** (live feedback visualization) — inner annulus carrying waveform/spectrum/pulse.
4. **Center** (primary readout) — central disc, the large value (e.g. `128 BPM`).
5. **Bottom Edge / Bottom State Label Zone** — a dedicated arc at the bottom of the dial for persistent state/status (the "state edge"). On B02 this is the green "BOTTOM STATE LABEL ZONE: Persistent system state, status, and short labels. Always visible." On B01 it is "BOTTOM EDGE — State / status indicator." On B03 the bottom carries the `SCENE` label + the "MODE SELECT / PENDING" promotion lane.

**Bottom "state edge" zone** (the named bottom band): persistent, always-visible, lowest-priority-but-critical status strip occupying the bottom arc of the circle; overlaps the finger-swipe occlusion arc (§10) which is why status must persist there during swipes.

---

## 2. RING ROLES (bezel → centre) + naming reconciliation

Each board names the rings slightly differently. **All verbatim variants listed** so tokens can be reconciled to one canonical set.

| Canonical band | B00 §4 "RING GRAMMAR" | B01 §1 "RING ROLES" | B02 §01 "ZONE ANATOMY & SAFE AREAS" | Role / content carried |
|----------------|------------------------|----------------------|--------------------------------------|------------------------|
| **Outer Ring** | "OUTER RING – NAVIGATION: Move between modes, tools, presets and views. Context and navigation live here." | "OUTER RING: Top-level mode / category navigation." | "OUTER-RING NAVIGATION ZONE: Mode, category, and context navigation. Lower priority content." | Mode/category/context navigation; lowest visual priority |
| **Mid Ring** | "MID RING – ACTIVE CONTROL: The currently selected parameter layer. Adjust level, frequency, depth, density and more." | "MID RING: Active parameter control." | "MID-RING CONTROL ZONE: Interactive parameters & live controls. Thumb-accessible." | Currently-selected parameter layer; interactive live controls |
| **Inner Core** | "INNER CORE – LIVE FEEDBACK: Real-time signal visualization, waveform, spectrum, pulse maps, feedback and motion." | "INNER CORE: Live signal feedback visualization." | (covered by center/mid; not separately labelled) | Real-time signal viz: waveform, spectrum, pulse maps, motion |
| **Center** | "CENTER – PRIMARY READOUT: The most important value at a glance (e.g., BPM, Key, Slot, Intensity, % or Amount)." | "CENTER: Primary readout (value / unit)." | "PRIMARY CENTER READOUT ZONE: Place key values here. Max legibility, least occlusion." | The single most important value; max legibility, least occlusion |
| **Bottom edge** | (implicit in System Status Strip §9) | "BOTTOM EDGE: State / status indicator." | "BOTTOM STATE LABEL ZONE: Persistent system state, status, and short labels. Always visible." | Persistent state/status, always visible |

**Naming inconsistencies to reconcile (verbatim):**
- "Inner Core" (B00/B01) vs no inner-core zone on B02 (B02 collapses to outer/mid/center). Prompt also flags "Inner Core" vs **"Signal Core"** — *note: "Signal Core" does NOT appear verbatim on any of the four boards; only "INNER CORE" is printed.* Flagged for reconciliation in case a sibling board uses it.
- "Mid Ring" (B00/B01) vs **"Mid-Ring Control Zone"** (B02) vs "MID RING – ACTIVE CONTROL" (B00). Same band, three labels.
- "Outer Ring" vs "Outer-Ring Navigation Zone" (B02) vs "OUTER RING – NAVIGATION" (B00). Same band.
- "Bottom Edge" (B01) vs "Bottom State Label Zone" (B02). Same band.
- **Two layered/conditional rings** (B01 §1 inset): **"A / B LAYER — Appears only in A/B modes."** and **"ALERT LAYER — Appears only when needed."** These are overlay layers, not concentric bands.

---

## 3. COLOR

### 3a. The 5 Theme Territories ("Five visual languages. One system." — B00 §6, B03 §03)

| # | Territory | Character (verbatim) | Accent family (rendered) | Dot-swatch sequence (visual estimate, L→R) |
|---|-----------|----------------------|---------------------------|---------------------------------------------|
| 1 | **SIGNAL OBSERVATORY** | "Clean. Scientific. Precise." | Blue / cyan | blue · blue · blue · blue · violet |
| 2 | **AFTERGLOW DISTRICT** | "Cinematic. Moody. Electric." | Red / magenta | violet · magenta · pink · red · orange |
| 3 | **PRISM FIREWALL** | "Data-driven. Vivid. Adaptive." | Green / teal | teal · cyan · cyan · green · lime |
| 4 | **LASER LITURGY** | "Sacred. Focused. Ritual." | Violet / purple | violet · purple · magenta · pink · magenta |
| 5 | **ZERO-G BAZAAR** | "Energetic. Holographic. Alive." | Orange / amber | orange · amber · amber · amber · blue |

> B03 is rendered AS the ZERO-G BAZAAR territory ("EXAMPLE 5: ZERO-G BAZAAR") and shows that territory's row highlighted/boxed. Dot sequences are 5 swatches each `(visual estimate)`; exact hex not printed.

### 3b. Semantic / state accent colours

Pulled from the Trust State Legend (B03 §04), Truth Ring (B03 §02), Progressive Disclosure sublabels (B01 §6), and encoder focus legend (B02 §06). Hues are rendered approximations.

| Accent name | Approx hue | Meaning / where used |
|-------------|-----------|----------------------|
| **PEND / Pending** | amber-orange (dotted) | "Awaiting confirm" (B03 §04 PEND); top badge "PEND" on B03 dial |
| **PENDING FOCUS** | magenta/pink | "Mode not confirmed" (B03 §02 Truth Ring) |
| **GLANCEABLE** | cyan | "At-a-glance info" (B03 §04) / B01 Quiet-state sublabel "GLANCEABLE" |
| **AWARE / AWARE CONTEXT** | amber/orange | "Monitoring state" (B03 §04) / "Live context known" (B03 §02) / B01 Live-state sublabel "AWARE" |
| **ENGAGED / ENGAGED INPUT** | red→pink | "Active interaction" (B03 §04) / "User input detected" (B03 §02, rendered yellow) / B01 Edit-state sublabel "ENGAGED" (orange) |
| **FOCUSED** | magenta/violet | "Deep adjustment" (B03 §04) / B01 Detail-state sublabel "FOCUSED" (cyan) |
| **READY ZONE** | blue/cyan | "Confirm to commit" (B03 §02 Truth Ring) |
| **COMMITTED** | green | "Change applied" (B03 §04) / bottom-strip "COMMITTED" |
| **WARNING / ACT NOW** | red | "Alerts, conflicts, or critical states" (B01 §6 Warning state, sublabel "ACT NOW") |

> Note hue drift between boards: B03 Truth Ring renders ENGAGED INPUT as **yellow** while B03 Trust State Legend renders ENGAGED as **red/pink**; B01 renders FOCUSED sublabel **cyan** while B03 renders FOCUSED **magenta/violet**. Listed for reconciliation.

### 3c. FOCUS / ACTIVE / CONFIRM colours (B02 §06 legend, verbatim)

| Element | Colour (rendered) |
|---------|-------------------|
| **FOCUS RING** | cyan / blue |
| **FOCUS DOTS** | magenta / pink |
| **ACTIVE ARC** | orange / amber |
| **CONFIRM PULSE** | green |

(B02 §06 focus-state stages also colour-code: IDLE = green, FOCUS = cyan, ADJUSTING = red/amber arc, CONFIRM = green pulse.)

---

## 4. TYPOGRAPHY — Legibility Ladder & contrast tables (B02)

### 4a. Text Legibility Ladder (B02 §03 "TEXT LEGIBILITY LADDER (REFERENCE)")

Columns: SIZE (PX) · USE CASE · EXAMPLE · MIN CONTRAST.

| SIZE (px) | Use case | Example | Min contrast |
|-----------|----------|---------|--------------|
| **28–32** | Primary Numeric | `128` | **AAA** |
| **20–24** | Primary Labels | `WAVEFORM` | **AAA** |
| **16–18** | Secondary Labels | `RATE` | **AAA** |
| **13–15** | Tertiary Info | `INTENSITY` | **AA** |
| **11–12** | Micro Labels | `DUSK PAD` | **AA** |
| **9–10** | Micro / Fine Print | `LOCKED` | **A** |

> The prompt anticipated a 7-rung table; **6 rungs are legibly printed** on B02 (28–32, 20–24, 16–18, 13–15, 11–12, 9–10). No 7th rung is visible/readable. Flagged as a count discrepancy `(visual)` — possible that a 7th rung exists but is not resolvable in the supplied raster.

### 4b. Contrast checks — TEXT ON DARK BACKGROUND (B02 §04)

Columns: TEXT · EXAMPLE · RATIO · PASS.

| Text colour | Example | Ratio | Pass |
|-------------|---------|-------|------|
| White | `128` | **15.6:1** | ✓ |
| Cyan | `SYNC` | **9.7:1** | ✓ |
| Pink/Magenta | `RATE` | **8.1:1** | ✓ |
| Orange | `BLEND` | **7.2:1** | ✓ |
| Green | `LOCKED` | **6.3:1** | ✓ |
| Purple | `NEON PULSE` | **4.8:1** | ⚠ (warning, not pass-✓) |

### 4c. Contrast checks — RING / ACCENT CONTRAST (B02 §04)

Columns: ACCENT (colour bar) · ON DARK · RATIO · PASS. Bars only (no text example).

| Accent bar | Ratio | Pass |
|------------|-------|------|
| Cyan | **3.6:1** | ✓ |
| Pink | **3.4:1** | ✓ |
| Orange | **3.2:1** | ✓ |
| Green | **3.1:1** | ✓ |
| Purple | **2.9:1** | ✓ `(visual — mark/tick faint; lowest of the set)` |

---

## 5. INTERACTION

### 5a. Gesture Model — 6 gestures (B01 §2)

"ALL GESTURES ARE CONTEXT-SENSITIVE AND MODE-AWARE."

| Gesture | Action (verbatim) |
|---------|-------------------|
| **ROTATE** | "Turn the encoder. Adjust value / scrub / navigate." |
| **PRESS** | "Click the encoder. Select / Enter / Confirm." |
| **LONG PRESS** | "Press and hold (**800ms**). Open options / Context menu." |
| **DOUBLE PRESS** | "Press twice quickly. Reset / Default / Toggle view." |
| **HOLD + ROTATE** | "Press and hold, then rotate. Fine adjust / Scrub at higher resolution." |
| **TOUCH RING (OPTIONAL)** | "Touch outer or mid ring. Jump / Select mode or parameter directly." |

> Only stated timing is **long press = 800 ms**. Promotion-lane gestures (B03 §06) restate: Rotate = "explore / preview all modes"; Press = "confirm / commit selection"; Hold = "cancel / return to current".

### 5b. Encoder focus states — 4 states (B02 §06 "ENCODER FOCUS & HIGHLIGHT BEHAVIOR")

"How focused elements respond to encoder input."

| State | What changes (verbatim) |
|-------|--------------------------|
| **IDLE STATE** | "Normal appearance. Balanced ring brightness." |
| **FOCUS (SELECTED)** | "Focused ring & dots increase intensity. Label brightens." |
| **ADJUSTING (ACTIVE)** | "Arc fills and pulses while value changes. Real-time feedback." |
| **CONFIRM (COMMIT)** | "Brief confirm pulse then returns to focused state." |

Flow: IDLE → FOCUS → ADJUSTING → CONFIRM → (returns to FOCUS).

---

## 6. STATE MODELS (all overlapping models, verbatim, for rationalization)

### 6a. Progressive Disclosure (B01 §6) — "ONLY REVEAL WHAT IS RELEVANT NOW. REDUCE WHEN NOT NEEDED."

| State (title) | Parenthetical | Description (verbatim) | Sublabel | Example shown |
|---------------|---------------|------------------------|----------|----------------|
| **QUIET STATE** | (AT REST) | "Minimal information. Low motion. Focus on primary readout and state." | **GLANCEABLE** | `128 BPM` |
| **LIVE STATE** | (MONITORING) | "Signal feedback animated. Key metrics visible." | **AWARE** | spectrum animation |
| **EDIT STATE** | (ADJUSTING) | "Active parameter highlighted. Fine controls available." | **ENGAGED** | `CUTOFF 74%` |
| **DETAIL STATE** | (EXPLORING) | "Deep parameters and context revealed." | **FOCUSED** | `FILTER TYPE 24dB LPF` |
| **WARNING STATE** | (ALERT) | "Alerts, conflicts, or critical states surface clearly." | **ACT NOW** | `128 BPM` + alert glyph |

### 6b. Trust State Legend (B03 §04 — header printed verbatim as "TRUSE STATE LEGEND", typo for TRUST)

| State | Meaning (verbatim) |
|-------|--------------------|
| **PEND** | "Awaiting confirm" |
| **GLANCEABLE** | "At-a-glance info" |
| **AWARE** | "Monitoring state" |
| **ENGAGED** | "Active interaction" |
| **FOCUSED** | "Deep adjustment" |
| **COMMITTED** | "Change applied" |

### 6c. Truth Ring states (B03 §02 "TRUTH RING (PEND STATE)")

| State | Meaning (verbatim) |
|-------|--------------------|
| **PENDING FOCUS** | "Mode not confirmed" |
| **AWARE CONTEXT** | "Live context known" |
| **ENGAGED INPUT** | "User input detected" |
| **READY ZONE** | "Confirm to commit" |

### 6d. A/B Logic (B01 §5) — "A/B LAYER IS HIDDEN BY DEFAULT. IT APPEARS ONLY WHEN A COMPARE OR MORPH CONTEXT IS ACTIVE." / "EXITS AND RETURNS TO SINGLE SCREEN CONTEXT ON DEMAND."

| Mode | Parenthetical | Center value | Description (verbatim) |
|------|---------------|--------------|------------------------|
| **COMPARE MODE** | (VIEW) | `128 BPM` | "A and B screens shown side-by-side while retaining individual values." |
| **MORPH MODE** | (BLEND) | `58% MORPH` | "Blend between A and B. Center shows morph amount and direction (A ↔ B)." |
| **SYNC DIVERGENCE MODE** | (DIFF) | `12% DIFF` | "Highlights differences between A and B to aid alignment and sync." |

### 6e. Bottom progressive strip (B03, unlabelled section, 4 cards)

| Card | Description (verbatim) | Pill |
|------|------------------------|------|
| **GLANCEABLE** | "Quick snapshot. Information at a glance." | GLANCE |
| **AWARE** | "Monitoring. System is aware of your presence." | AWARE |
| **ENGAGED** | "You're in control. Parameters are actively responsive." | ENGAGED |
| **COMMITTED** | "Changes applied. System confirms with feedback." | COMMITTED |

> **Overlap / reconciliation map across 6a–6e:** Five distinct but converging vocabularies describe the same arousal/trust ladder. Rough alignment:
> - **At-rest/glance:** QUIET/GLANCEABLE (6a) ≈ GLANCEABLE (6b, 6e) ≈ (no Truth-Ring equiv).
> - **Monitoring:** LIVE/AWARE (6a) ≈ AWARE (6b, 6e) ≈ AWARE CONTEXT (6c).
> - **Adjusting:** EDIT/ENGAGED (6a) ≈ ENGAGED (6b, 6e) ≈ ENGAGED INPUT (6c).
> - **Deep:** DETAIL/FOCUSED (6a) ≈ FOCUSED (6b) ≈ (no Truth-Ring/strip equiv beyond READY ZONE).
> - **Pre-commit:** PEND (6b) ≈ PENDING FOCUS (6c) ≈ READY ZONE (6c, "confirm to commit").
> - **Post-commit:** COMMITTED (6b, 6e); 6a's WARNING/ACT NOW is an orthogonal alert axis with no 6b–6e twin.
> Token system must pick ONE canonical state enum and alias the rest.

---

## 7. MODES & SCREENS

### 7a. Five top-level modes + sub-items

B01 §3 sub-items are the authoritative hierarchy. B00 §2 gives the same 5 modes with one-line descriptions + sample readouts + bullet lists. B03 §01 restates the 5 with descriptions.

| Mode | One-line (B00 §2 / B03 §01) | Sample readout (B00 §2) | Sub-items (B01 §3) | Bullets (B00 §2) |
|------|------------------------------|--------------------------|---------------------|-------------------|
| **SIGNAL** | "Observe the audio in real time" / "Capture the audio in real time" | `128 BPM` | Home / Now · Spectrum · Waveform · Harmonic | Spectrum · Waveform · Harmonics · Pitch-Class Map |
| **SHAPE** | "Sculpt tone, timbre and effects" | `132 BPM` | Pitch / Scale · Effects · Filter · Dynamics | Effects / Shape · EQ / Filter · Modulation · Dynamics |
| **MOTION** | "Movement, rhythms and evolution" | `136 BPM` | Rate · Modulation · Step Sequencer · Random / Chaos | Motion Sequences · LFO / Envelopes · Step / Patterns · Mod Matrix |
| **SCENE** | "Presets, layers and morphing" / "Preset, layers and morphing" | `124 SLOTS` | Scene / Preset Morph · Preset Browser · Set List · Snapshots | Preset Morph · Layers / Parts · Macro Morph · Snapshot |
| **SYSTEM** | "Setup, sync and performance" | `110 BPM` | System / Sync · I/O / CV · MIDI · Settings / About | System / Sync · I/O / MIDI / Clock · Settings / About · Diagnostics |

> Sub-item naming drifts between B00 bullets and B01 sub-items (e.g. SIGNAL "Harmonics"/"Pitch-Class Map" vs "Harmonic"; MOTION "LFO / Envelopes" vs "Modulation"; SYSTEM "I/O / MIDI / Clock" vs separate "I/O / CV" + "MIDI"). Both retained.

### 7b. 10 canonical screens (B00 §5 "CANONICAL SCREEN SET (10)") + the question each answers (B01 §4 "CANONICAL SCREEN QUESTIONS")

| # | Screen (B00 §5) | At-a-glance description (B00 §5) | Sample value | Question it answers (B01 §4) |
|---|------------------|----------------------------------|--------------|-------------------------------|
| 1 | **HOME / NOW** | "At-a-glance status, key metrics and activity." | `128 BPM` | "What is happening right now?" |
| 2 | **MODE SELECT** | "Choose a top-level mode or sub-tool quickly." | — | (no separate question; selection screen) |
| 3 | **SPECTRUM** | "Real-time spectral analysis." | `128 BPM` | "What frequencies are active?" |
| 4 | **WAVEFORM** | "Waveform, phase and zero-crossing view." | — | "What does the signal look like?" |
| 5 | **HARMONIC INTEL** | "Harmonic radar, key, chord and emotional profile." | — | "How harmonic is the signal?" (B01 "HARMONIC") |
| 6 | **PITCH-CLASS MAP** | "Pitch-class distribution and key insight." | note ring A–G | "Which pitch classes are present?" (B01 "PITCH") |
| 7 | **EFFECTS / SHAPE** | "Filter, EQ, drive, reverb, delay and shaping." | `FILTER 132 HZ` | "How is the sound being shaped?" (B01 "EFFECTS") |
| 8 | **MOTION** | "LFOs, envelopes, patterns and modulation." | `1/16 RATE` | "How is it evolving over time?" |
| 9 | **SCENE / PRESET MORPH** | "Preset morphing, layers and macro control." | `68% A·B MORPH` | "What happens between two states?" (B01 "SCENE") |
| 10 | **SYSTEM / SYNC** | "Sync, I/O, CPU, latency and system health." | `CPU 23%` | "Is the system healthy and synced?" (B01 "SYSTEM") |

> B01 §4 lists 9 questions (no question for MODE SELECT); B00 §5 lists 10 screens. Reconcile: MODE SELECT is a navigation utility, not a content screen.

### 7c. Five Questions the UI must answer (B00 §3 "FIVE QUESTIONS THE UI MUST ANSWER")

1. "WHAT AM I HEARING?" — "Clear real-time signal feedback so I can see what's actually happening." (cyan)
2. "WHAT IS K1 DOING?" — "Show the active processes, parameters and transformations." (green)
3. "WHAT MODE AM I IN?" — "Always communicate context, mode and location." (magenta)
4. "WHAT CAN I CONTROL NOW?" — "Expose the right parameters at the right time, with depth on demand." (amber)
5. "IS THE SYSTEM HEALTHY & SYNCED?" — "Confidence through sync, levels, latency, CPU and status." (teal/cyan)

### 7d. Mode Compass Map layout (B03 §05 "MODE COMPASS MAP" — "Rotate to preview. Press to select.")

Radial fan layout, 5 sectors:
- **SIGNAL** — "Capture & Analyze" (upper-left)
- **SHAPE** — "Tone & Effects" (upper-right)
- **SYSTEM** — "Setup & Control" (lower-left)
- **MOTION** — "Rhythm & Evolution" (lower-right)
- **SCENE** — "Layers & Morphed Space" (centre, beneath)

---

## 8. COMPONENTS INVENTORY

Every distinct named UI element across the four boards.

| Component | Board(s) | What it is | Where it sits |
|-----------|----------|------------|---------------|
| **Center Readout / Primary Center Readout Zone** | B00 §4, B01 §1, B02 §01 | Largest value at a glance (BPM/Key/Slot/%/Amount) | Central disc |
| **Outer Ring (Navigation)** | B00/B01/B02 | Mode/category/context navigation ring | Outermost band |
| **Mid Ring (Active Control)** | B00/B01/B02 | Selected-parameter live control ring | Middle annulus |
| **Inner Core (Live Feedback)** | B00/B01 | Real-time signal viz (waveform/spectrum/pulse) | Inner annulus |
| **Bottom State Label Zone / Bottom Edge** | B01/B02 | Persistent status strip ("state edge") | Bottom arc |
| **A / B Layer** | B01 §1, B01 §5 | Overlay shown only in compare/morph contexts | Conditional overlay (left/right A·B nodes) |
| **Alert Layer** | B01 §1, B01 §6 | Overlay surfaced only on alert/conflict | Conditional overlay |
| **Truth Ring** | B03 §02 | Dotted ring encoding trust state via colour | Replaces/overlays dial ring (Pend state shown) |
| **Promotion Lane** | B03 §06 | Horizontal "MODE SELECT / PENDING" confirm lane with ◀◀ ▶▶ arrows | Below center, bottom of dial |
| **Status Badge / PEND badge** | B03 (top of dial), B03 §07 | Small pill showing pending/trust state ("PEND") | Top of dial |
| **Mode Compass Map** | B03 §05 | Radial fan to preview/select the 5 modes | Right panel |
| **System Status Strip (Global)** | B00 §9 | Always-visible global bar: key · BPM · meter · LINK · MIDI · CPU · LAT | Global (bottom strip) |
| **Theme Territory swatch rows** | B00 §6, B03 §03 | 5 named palettes w/ icon + character + dot swatches | Right panel |
| **Dot-ring (focus dots)** | B02 §06, B03 | Ring of dots that intensify on focus / encode position | Around mid/outer ring |
| **Spectrum bars** | B00, B02, B03 | Real-time frequency-bar visualization | Inner core / center bottom |
| **Waveform trace** | B00 §5, B01 §1, B02 | Live waveform line | Inner core |
| **Active Arc** | B02 §06 | Arc that fills/pulses during ADJUSTING | Mid ring |
| **Confirm Pulse** | B02 §06 | Brief green pulse on commit | Whole ring |
| **Focus Ring** | B02 §06 | Cyan ring marking the selected element | Around focused band |
| **Pitch-class note ring (A–G)** | B00 §5 (Pitch-Class Map) | Lettered note positions for key insight | Inner ring (Pitch screen) |
| **Mode dials (5)** | B00 §2 | Per-mode preview dials w/ value | Top hierarchy strip |
| **Canonical screen thumbnails (10)** | B00 §5 | Mini dial previews of each screen | Center grid |
| **Trust/Progressive state cards** | B01 §6, B03 bottom | Mini-dial cards showing each state | Bottom strips |
| **Device preview crops (1X / 2X)** | B02 §02 | Bezel-in-context renders at scale | Mid-right |
| **Validation Checklist** | B02 §07 | Pass/fail QA rows | Right panel |

---

## 9. PRINCIPLES & DO/DON'T

### 9a. Six design principles (B00 §8 "DESIGN PRINCIPLES", verbatim)

1. **CLARITY** — "First. One idea dominates."
2. **CONTEXT** — "Always. Mode, tool and focus."
3. **FEEDBACK** — "Real-time. See it. Feel it. Trust it."
4. **DEPTH** — "On Demand. Surface simple. Reveal power."
5. **CONSISTENCY** — "Everywhere. Predictable and learnable."
6. **PERFORMANCE** — "Matters. Smooth, fast, responsive."

### 9b. DO list (B00 §7, verbatim)

- "Build an operating grammar, not a gallery."
- "Prioritize clarity, hierarchy and context."
- "Use meaningful A / B only when needed."
- "Keep the center sacred for primary readout."
- "Reveal depth progressively, not all at once."
- "Respect performance and encoder UX."

### 9c. DON'T list (B00 §7, verbatim)

- "Don't make more decorative variant dials."
- "Don't put a collar on every screen."
- "Don't bury the key information."
- "Don't overload with simultaneous data."
- "Don't break consistency across modes."
- "Don't sacrifice legibility for style."

### 9d. Core objective + verbs (B00 §1)

"SpectraSynq K1 is a circular-screen operating system for a physical encoder controller. It is not a gallery of decorative dials. It is a coherent operating grammar that helps users see, understand and shape the music in real time." Four verbs: **OBSERVE · UNDERSTAND · SHAPE · PERFORM**.

### 9e. System Status Strip rule (B00 §9)

Contents (verbatim, L→R): `A MIN` · `128 BPM` · `4/4` · `C MIN` · `● LINK` · `● MIDI` · `CPU 23%` · `LAT 2.3ms` · [meter bars]. Rule: **"Always visible. Always legible. Always truthful."**

### 9f. Validation Checklist (B02 §07, verbatim — all PASS/FAIL/NOTES)

- "Primary value instantly readable at a glance"
- "All critical content inside bezel-safe margin"
- "Text meets minimum contrast (AA/AAA)"
- "Rings & accents visible in all modes"
- "Legible with thumb occlusion (both sides)"
- "Bottom state label always visible"
- "Encoder focus states are clear & consistent"
- "No moiré / aliasing on fine details"
- "Performance: 60fps at target brightness"

---

## 10. OCCLUSION (B02 §05 "THUMB & FINGER OCCLUSION ZONES")

Section rule: "Design so critical content remains readable in these zones."

| Zone | Coverage | Content rule (verbatim) | Colour |
|------|----------|--------------------------|--------|
| **LEFT THUMB ZONE** | **~30% coverage** | "Plan for lowest priority content in this area." | red/orange dashed |
| **RIGHT THUMB ZONE** | **~30% coverage** | "Keep primary readout clear of occlusion." | violet/purple dashed |
| **FINGER SWIPE ZONE (BOTTOM ARC)** | **~15% coverage** ("during swipe up/down") | "Persist status labels here." | green dashed |

> Design implication: the bottom **state edge / Bottom State Label Zone (§1, §2)** lives inside the ~15% finger-swipe arc — hence the "always visible / persist status labels here" mandate. Left-thumb arc = lowest-priority content; right-thumb arc must never occlude the center primary readout.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-29 | agent:deep-technical-analyst | Created — forensic extraction of all four K718 Remoted / SpectraSynq K1 design boards into a normative evidence catalogue (geometry, ring roles, colour, typography/contrast, interaction, state models, modes/screens, components, principles, occlusion). Verbatim transcription; visual estimates flagged; cross-board naming inconsistencies listed for reconciliation. |
