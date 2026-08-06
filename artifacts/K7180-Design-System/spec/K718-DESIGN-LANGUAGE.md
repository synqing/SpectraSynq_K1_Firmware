---
abstract: "Canonical, normative design language for the K718 Remoted circular controller (round 480×480 LCD encoder for the SpectraSynq K1 lightshow). THE locked spec — names and defines every element of the dashboard: radial grid, ring roles, color/type/motion tokens, component set, the rationalized state model (Attention × Trust × Alert), gesture model, modes & screens, principles and governance. This document is authority; the four PNG boards are reference. Read before any K718 UI work."
---

# K718 Remoted — Circular Design Language
### codename **HALO** · the radial grammar for SpectraSynq round-display instruments

> ⛔ **HARD LAWS — see [`K718-UX-LAWS.md`](./K718-UX-LAWS.md) (Captain-ratified 2026-06-30):** (1) NO on-screen PEND/CONF/ACK/connection-status text — EVER; receipt/link state is out-of-band (physical LED ring red×5 / solid-red, speaker, haptic). (2) NO value-number in the centre bullseye. (3) NO on-screen rim dots (the physical LED ring owns the rim). (4) Centre field must be mic-honest, not faked. (5) Single-hand rotary+touch radial model. Any agent violating these is to be stopped.

> **Status:** v0.1 (authoring) · **Authority:** This document is the single source of truth for the K718 Remoted dashboard. The four boards in this folder (`00–03.*.png`) are *reference inspiration*; where they disagree with each other, **this spec rationalizes and wins**. Product names (K1, K718 Remoted) are fixed; HALO names only the *grammar*.
>
> **Why locked:** The K718 dashboard froze after a churn loop of decorative variant dials. This spec is the blueprint that ends it: variation may only happen *inside* the grammar defined here. Building a "new dial" is out of grammar; building within these named elements is in grammar.

---

## §0 · How to read this system

HALO is layered. Each layer constrains the one below it. Build top-down; never skip a layer.

| Layer | Question it answers | Section |
|---|---|---|
| **Foundations** | What are the raw materials? (grid, color, type, motion) | §1 |
| **Structure** | Where does content live on a circle? (rings, zones, occlusion) | §2 |
| **Components** | What are the named, reusable parts? | §3 |
| **Patterns** | How do parts behave over time and interaction? | §4 |
| **Application** | What modes/screens exist and what do they promise? | §5 |
| **Governance** | What is locked, what may vary, what is forbidden? | §6 |
| **Glossary** | The canonical name of every element | §7 |

**The one-sentence product truth (board 00 §1):** *The K718 Remoted is a coherent operating grammar that helps a user **see, understand, and shape** music in real time — it is not a gallery of decorative dials.*

---

## §1 · Foundations (Tokens)

> Precise numeric/hex values are finalized in `../tokens/tokens.json` and refined from the forensic evidence base (`_design-evidence.md`). Values below are the **design contract**; the token files are the **machine-readable implementation**. They must agree.

### 1.1 Geometry — the canvas

| Property | Value | Token |
|---|---|---|
| Bezel outer diameter | Ø 68.0 mm | `device.bezel.od` |
| Active display diameter | Ø 60.0 mm = **480 px** | `device.active.dia` |
| Scale | **8 px / mm** | `device.scale` |
| Active radius | 240 px (R\_max) | `device.active.r` |
| Bezel-safe margin | **6 % of radius ≈ 14 px** | `grid.safe.margin` |
| Safe radius (critical content) | ≈ 226 px (R\_safe) | `grid.safe.r` |

**Rule G-1 — Bezel-safe.** No critical content (values, labels, controls) outside R\_safe. The outer 14 px is decoration / glow bleed only.

### 1.2 The Radial Grid (polar coordinate model)

HALO does **not** use a rectilinear grid. Content is placed by **radius band** (distance from center) and **angular zone** (clock position). This is the core innovation the existing print-grid skills cannot express — see the `k718-radial-grid` skill.

**Radius bands**, bezel → center (canonical IDs; extents are design guidance, tunable per screen):

| Band | Name | Role | Approx. radius |
|---|---|---|---|
| B0 | **Bezel-Safe Margin** | dead zone / glow bleed | r 226–240 |
| B1 | **Nav Ring** | top-level mode & category navigation | r 188–226 |
| B2 | **Control Ring** | active parameter control (interactive) | r 138–188 |
| B3 | **Signal Core** | live signal visualization (spectrum/waveform) | r 70–138 |
| B4 | **Readout Center** | the single most important value + unit | r 0–70 |

**Angular zones** (clock positions, used for nav labels & mode placement):

| Zone | Clock | Default content |
|---|---|---|
| **Crown** | 12 o'clock | Status Badge / primary state |
| **Right Arc** | 1–5 | mode labels (e.g. SHAPE, MOTION) |
| **Keel** | 6 o'clock | State Edge label + Promotion Lane anchor |
| **Left Arc** | 7–11 | mode labels (e.g. SIGNAL, SYSTEM) |

**Rule G-2 — Importance ↔ centrality.** The closer to center, the more important and the more legible. The Readout Center is sacred (board 00 DO: "Keep the center sacred for primary readout").

### 1.3 Color

Color carries **meaning** before mood. Two systems:

**(a) Semantic / State accents** — *fixed across all themes*. These never change meaning:

| Token | Hue family | Meaning |
|---|---|---|
| `accent.focus` | cyan | focus ring — the selected element |
| `accent.active` | amber | active arc — value currently changing |
| `accent.input` | magenta | user input detected / pending focus |
| `accent.confirm` | green | commit confirmed / locked / healthy |
| `accent.alert` | red | warning, conflict, critical |
| *(refined hex from `_design-evidence.md` §3)* | | |

**(b) Themes** — *the only sanctioned visual-variation axis.* A **Theme** is a token set = {palette (bg + text + 5 swatch), the 5 semantic-accent hex, motion profile, density profile}, applied via `data-territory` — it restyles, never relayouts.

> **🔓 No theme is married (Captain 2026-06-29).** The *mechanism* is locked; the *specific themes are OPEN exploration candidates.* The board's original five (Signal Observatory / Afterglow District / Prism Firewall / Laser Liturgy / Zero-G Bazaar) are **not canonical** — they are one region (dark neon) of a much larger space. Everything is on the table: light/daylight surfaces, austere instrument, warm analog, mono-restraint, vivid-editorial, refined-dark. Because the grammar is locked, exploring themes is **on-grammar** (swap a token set, never draw a new dial) — this is the safe place to be ambitious. Candidate themes live in `tokens/themes/` and render through the same `halo.js`; none is privileged until Captain selects.
>
> *Audit note:* both Rams + Vignelli flagged mid-2020s neon-on-black as slop-prone / dating. The canonical *reference* theme (for proving the grammar) should be the most **austere** candidate; loud themes are sanctioned variation, not the reference.

**Rule C-1 — Meaning over mood.** Any theme may restyle the *palette* but may never reassign a *semantic accent's meaning* (green always = confirm, red always = alert). Exactly **five** semantic accents exist; decorative colours are theme-palette only, never semantic (no 6th accent).

### 1.4 Typography — the Legibility Ladder

Type is sized by **role**, not taste. Every rung carries a minimum contrast grade — legibility is non-negotiable on a 60 mm display at arm's length (board 02 §03–04).

| Rung | Size (px) | Role | Min contrast |
|---|---|---|---|
| T1 | 28–32 | Primary numeric (the Readout) | AAA |
| T2 | 20–24 | Primary labels | AAA |
| T3 | 16–18 | Secondary labels | AAA |
| T4 | 13–15 | Tertiary info | AA |
| T5 | **11 (floor)** | Micro labels | **AA** |

> **Micro floor raised (V1/Rams#8):** the old T6 (9–10 px @ A) is **retired** — at 60 mm/arm's length, A-grade micro text is not reliably legible. Nothing below **11 px / AA** ships. If content can't meet that, it doesn't belong on the display.

**Rule T-1 — The K1 Signal Interface standard (two families, named).** **Display + numerals = DIN Condensed Bold** (tabular figures — `tnum` — so live values don't jitter); **UI / labels = Inter Regular.** Source: `artifacts/K7180-Design-System/fonts` (Captain-referenced). No third face. *Device reality (Rams#1):* on ESP32-S3/LVGL both must be **compiled as bitmap glyph sets** at the ladder sizes — they are firmware build artifacts, not webfonts; the web gallery uses Oswald/Saira Condensed as a DIN render proxy.
**Rule T-2 — Size-compensated tracking (V3):** tracking increases as size drops (T2 0.05em → T5 0.12em); never one flat value.
**Rule T-3 — No critical text below T4** inside thumb-occlusion zones (§2.3).

### 1.5 Motion

Motion is **feedback**, never decoration (board 00 principle: "Feedback — Real-time. See it. Feel it. Trust it.").

| Token | Trigger | Behavior |
|---|---|---|
| `motion.idle` | at rest | balanced ring brightness, low energy |
| `motion.live` | signal present | signal viz animates to audio |
| `motion.focus` | element selected | focus ring + dots brighten, label sharpens |
| `motion.adjust` | value changing | active arc fills/pulses in real time |
| `motion.confirm` | commit | one brief confirm pulse, then settle |

**Rule M-1 — Performance is a feature** (board 00 principle 6): target 60 fps at full brightness. A dropped frame is a broken promise. No motion that cannot hold 60 fps.

### 1.6 Iconography

One glyph per top-level mode (SIGNAL/SHAPE/MOTION/SCENE/SYSTEM) + one per state. Glyphs are line-weight-consistent, drawn on the radial grid, legible at T5. No filled/skeuomorphic icons.

---

## §2 · Structure (the Ring System)

### 2.1 Ring Roles (canonical)

Reconciles the board variants ("Outer Ring / Mid Ring / Inner Core / Center / Bottom Edge" vs "...Zone" naming). **Canonical names are the §1.2 band names.** Cross-references:

| Canonical (HALO) | Board synonyms (deprecated) | Carries |
|---|---|---|
| **Nav Ring** (B1) | Outer Ring, Outer-Ring Navigation Zone | modes, tools, presets, navigation |
| **Control Ring** (B2) | Mid Ring, Mid-Ring Control Zone | the active parameter (level/freq/depth/density) |
| **Signal Core** (B3) | Inner Core, Live Feedback | waveform, spectrum, pulse maps |
| **Readout Center** (B4) | Center, Primary Center Readout Zone | one value + unit (BPM/Key/Slot/%) |
| **State Edge** | Bottom Edge, Bottom State Label Zone | persistent state/status (always visible) |

Plus two overlay layers (not bands):
- **A/B Layer** — appears only in compare/morph contexts; A flanks left, B flanks right.
- **Alert Layer** — appears only when needed; interrupts over everything.

### 2.2 Safe areas

All §1.1 G-rules apply. The **State Edge** at the Keel (6 o'clock) is always rendered and always legible — it is the one zone that never goes dark.

### 2.3 Occlusion zones (board 02 §05)

The user's hand covers part of the display while turning the encoder. Design around it.

| Zone | Coverage | Rule |
|---|---|---|
| **Left thumb** | ~30 % (lower-left arc) | lowest-priority content only |
| **Right thumb** | ~30 % (lower-right arc) | keep Readout Center clear of this |
| **Finger swipe** | ~15 % (bottom arc) | State Edge must persist *through* the swipe |

**Rule O-1 — Readout never occluded.** The Readout Center must remain readable under both thumb zones simultaneously.

---

## §3 · Components (named parts)

The complete, closed component set. Building a screen = composing these. *Adding a component requires a spec revision; restyling one via a Theme Territory does not.*

| Component | Definition | Lives in | Key rule |
|---|---|---|---|
| **Readout** | the single primary value + unit, T1 | Readout Center | exactly one per screen |
| **Dot-Ring** | ring of discrete LED-like dots; the shared primitive for Control Ring & Truth Ring | B1/B2 | dot color = semantic accent |
| **Nav Labels** | mode/category labels on arcs | Nav Ring / angular zones | T2/T3, current mode brightened |
| **Signal Viz** | live spectrum / waveform / harmonic render | Signal Core | audio-driven only, never time-only |
| **Active Arc** | arc that fills/pulses while a value changes | Control Ring | `accent.active` (amber) |
| **Focus Ring + Focus Dots** | brightened ring/dots marking the selected element | Control Ring | `accent.focus` (cyan) |
| **Confirm Pulse** | one-shot pulse on commit | whole ring | `accent.confirm` (green), single |
| **Status Badge** | state pill (e.g. `PEND`) | Crown (12 o'clock) | shows Trust State (§4.2) |
| **Truth Ring** | the Dot-Ring in `Pending` trust state, colored by trust progress zones | over B1/B2 | only in Pending (§4.2) |
| **Promotion Lane** | horizontal pending-action bar: ◄ rotate / press / hold ► | Keel (6 o'clock) | only in Pending; states the 3 verbs |
| **Mode Compass** | radial fan to preview/select top-level modes | center overlay | rotate to preview, press to select |
| **System Status Strip** | global bar: BPM · time · key · LINK · MIDI · CPU · LAT | State Edge (global) | always visible, always truthful |
| **A/B Markers** | A (left) / B (right) flank markers + compare/morph/diff readout | A/B Layer | only in A/B contexts |
| **Alert** | interrupt surface for warning/conflict | Alert Layer | `accent.alert` (red), preempts |

---

## §4 · Patterns (behavior over time)

### 4.1 The State Model — RATIONALIZED (rationalization R1)

The boards conflated three different things under overlapping names (Progressive Disclosure vs Trust State vs Truth Ring). HALO separates them into **three orthogonal concerns**. Any screen is described by a point in (Attention × Trust) with an optional Alert overlay.

**Axis A — Attention Level** *(how much the screen reveals + how much it moves; tracks user engagement).* A 4-step ramp:

| Level | Was (boards) | Shows | Motion |
|---|---|---|---|
| **Glanceable** | Quiet / At-rest | Readout + State Edge only | minimal |
| **Aware** | Live / Monitoring | + Signal Viz animated, key metrics | live |
| **Engaged** | Edit / Adjusting | + active parameter highlighted, fine controls | focus + adjust |
| **Focused** | Detail / Exploring | + deep parameters & context | full |

> **Rule P-1 — Progressive disclosure (board 01 §6):** *Only reveal what is relevant now. Reduce when not needed.* Default to Glanceable; climb the ramp on demand; fall back automatically.

**Axis B — Trust State** *(the commitment lifecycle of a pending change — the "remoted" PEND→commit flow).*

| State | Shows | Component |
|---|---|---|
| **Settled** | current state is live/applied; no pending change | — |
| **Pending** | a change previewed, not committed | Status Badge `PEND` + Truth Ring + Promotion Lane |
| **Committing** | confirm in progress (brief) | Confirm Pulse begins |
| **Committed** | applied; system confirms; returns to Settled | `accent.confirm` |

> The Truth Ring's internal zones (board 03: pending-focus → aware-context → engaged-input → ready-zone) are the **dot color progression** that visualizes how close a Pending change is to being committable. They are sub-states of `Pending`, not a separate axis.

**Overlay — Alert** *(interrupt).* `Alert` may appear over ANY (Attention × Trust) combination. It is the Alert Layer (§3), not a step on either axis. This is where board 01's "Warning / Act-Now" lives.

> **Rule P-2 — One pending change at a time.** Trust is single-threaded: a screen may have at most one Pending change. No nested pends.

### 4.2 Gesture Model (board 01 §2)

All gestures are **context-sensitive and mode-aware**.

| Gesture | Action |
|---|---|
| **Rotate** | adjust value / scrub / navigate |
| **Press** | select / enter / confirm |
| **Long Press** (≈800 ms) | open options / context menu |
| **Double Press** | reset / default / toggle view |
| **Hold + Rotate** | fine adjust / scrub at higher resolution |
| **Touch Ring** *(optional)* | jump / select mode or parameter directly |

The **Promotion Lane** names the three verbs that resolve a Pending change: *Rotate to explore · Press to confirm · Hold to cancel.*

### 4.3 A/B Logic (board 01 §5)

The A/B Layer is hidden by default; appears only in compare/morph contexts. Three modes:

| Mode | Behavior |
|---|---|
| **Compare (View)** | A and B shown side-by-side, each retaining its own values |
| **Morph (Blend)** | blend A↔B; center shows morph % and direction |
| **Sync-Divergence (Diff)** | highlights differences between A and B to aid alignment |

Exits and returns to single-screen context on demand.

### 4.4 Encoder Focus Behavior (board 02 §06)

How a focused element responds to the encoder — the mechanical loop behind Axis A:

`Idle` (balanced) → `Focus` (ring+dots brighten on select) → `Adjusting` (active arc fills while value changes) → `Confirm` (one pulse, returns to Focus).

---

## §5 · Application — Modes & Screens

> ✅ **TERRITORY VERIFIED (DLG-01, firmware-cited).** The taxonomy was verified against `config_types.h` (30 modes / 22 enabled), the 71-path BLE-MIDI control map (`docs/protocol/k1-ble-midi-map.json`), and `AudioSemanticState`. It is **partially grounded** — three drift findings below. The verification is now *load-bearing law* via the Honesty Rule.

> ### 🔒 Honesty Rule H-1 (LOCKED) — *the dashboard must never display a control or value the firmware cannot actually provide.*
> Every mode, screen, control, and readout carries a backing tag: **BACKED** (real firmware feature, available on the chosen transport) · **PARTIAL** (data exists internally but does not cross the wire / needs a path) · **ASPIRATIONAL** (no firmware feature). **A shippable screen contains only BACKED elements.** PARTIAL elements require a stated data path before use. ASPIRATIONAL elements must be visibly marked as roadmap (dimmed + `◇` tag) or excluded — never rendered as live truth. Violating H-1 ships a lie; that is a release blocker.

### 5.1 Top-level modes — verified backing (DLG-01)

| Mode | Purpose | Real firmware grounding | Backing |
|---|---|---|---|
| **SIGNAL** | observe the audio in real time | spectrum[80], chroma_pc[12], chord, energy all computed in `AudioSemanticState` — **but only `tempo_bpm`+`tempo_locked` are transmitted.** "Spectrum"/"Chromagram" screens point at modes GDFT/CHROMAGRAM (IDs 0–2) which are **DISABLED**. | **PARTIAL** |
| **SHAPE** | sculpt tone, timbre, effects | 34 primary+secondary control paths (photons, chroma, mood, saturation, palette, incandescent, prism_count…) directly in the BLE-MIDI map | **BACKED** |
| **MOTION** | movement, rhythm, evolution | 5 enabled tempo-locked effects (WAVEFORM_TEMPO 18, TEMPO_RIVER 19, TEMPO_COMET 20, TEMPO_COMET_ANTICIPATE 27, TEMPO_RIVER_WALK 29) + live `beat_phase01`/`beat_tick`/`bpm` | **BACKED** |
| **SCENE** | presets, layers, morphing | `scene.smart` (NRPN) + 10 NVS preset slots exist; **preset-morph/blend over the wire is NOT a named control** | **PARTIAL** |
| **SYSTEM** | setup, sync, performance | director (enabled/assist/autonomy/confidence_floor), global (sensitivity/master_brightness/chroma_profile/max_current_ma), calibration (noise arm/confirm/clear), hooks, edge.mode — all in the map | **BACKED** |

> **Real enabled modes (the actual product roster, 22):** BLOOM, WAVEFORM(+FAST/HYBRID/TEMPO), BLOOM_FAST, AURORA, COMET, SPECTRUM_RIVER(+V2), EMBER, TEMPO_RIVER, TEMPO_COMET(+ANTICIPATE), DENSE_FORGE(+CHORD), SNAPWAVE, PULSE_PRISM, CHROMA_CONSTELLATION, PERCUSSION_BURST, RIVER_SURGE, TEMPO_RIVER_WALK. *(Disabled, do not surface: GDFT, GDFT_CHROMAGRAM, GDFT_CHROMAGRAM_DOTS, VU, VU_DOT, KALEIDOSCOPE, QUANTUM_COLLAPSE, EMBER_V2.)*

### 5.1a Readout fields — backing + roadmap (DLG-01 + Captain 2026-06-29) · governs the Readout Center

> **Captain decision (2026-06-29):** KEY + TIME are a **committed K1 DSP roadmap** (key/scale detection + beat/bar tracking will be built). Until then they render as **ROADMAP ◇** (dimmed, never live). Under H-1, "computed in firmware" is not enough — a value is **live** only once it crosses the **BLE feedback channel** to the K718 (today that channel carries committed mode numbers only).

| Field | Firmware reality | Status |
|---|---|---|
| **BPM** | `tempo_bpm` computed live (`sb_tempo_read`); **not yet on BLE feedback** | **BACKED (computed)** · BLE readback = **near-term roadmap** |
| **KEY** | no key detection; only `chord_root` (pc 0–11) + triad type | **ROADMAP ◇** (DSP + protocol) |
| **TIME** (signature) | not computed anywhere; no beats-per-bar/downbeat | **ROADMAP ◇** (DSP + protocol) |
| **INTENSITY** | `vu_level`/`spectral_energy` computed internally, unnamed | **PARTIAL** · BLE readback = roadmap |

### 5.1b Transport — **BLE-only** (Captain decision 2026-06-29, product truth — overrides DLG-01's WiFi framing)

The K718 Remoted is **BLE-MIDI only**. WiFi/WebSocket is **rejected** as the K718 transport (instability); BLE is lighter and more reliable. This is locked product truth.

Consequences the design system must hold honestly:
- **Control** (K718→K1): the 71-path BLE-MIDI map is real and oracle-verified (mode/parameter control). **BACKED.**
- **Readback** (K1→K718): today the BLE feedback characteristic carries **committed mode numbers only** — no BPM, key, time, spectrum, or chord. Every *live value* on the K718 display (starting with BPM) is gated on **extending the BLE feedback channel** to carry it. That extension is the near-term roadmap; richer audio-semantic readback (spectrum/chord for SIGNAL screens) follows.
- **PEND→commit** has no BLE protocol counterpart — it is a *controller-local UX layer*, not a firmware handshake.
- Phase G device proof = `PARTIAL_COMPLETE_DEVICE_BLOCKED` (71/71 oracle pass; eyes-on hardware-blocked).

### 5.2 Canonical screens (board 00 §5 / board 01 §4) — each answers one question

| # | Screen | Question it answers |
|---|---|---|
| 1 | Home / Now | What is happening right now? |
| 2 | Mode Select | (navigation) |
| 3 | Spectrum | What frequencies are active? |
| 4 | Waveform | What does the signal look like? |
| 5 | Harmonic | How harmonic is the signal? |
| 6 | Pitch-Class | Which pitch classes are present? |
| 7 | Effects / Shape | How is the sound being shaped? |
| 8 | Motion | How is it evolving over time? |
| 9 | Scene / Preset Morph | What happens between two states? |
| 10 | System / Sync | Is the system healthy and synced? |

> **Rule A-1 — One screen, one question.** Every screen answers exactly one of the above. If a screen needs two questions, it is two screens.

### 5.3 The five questions the whole UI must answer (board 00 §3)

1. What am I hearing? 2. What is K1 doing? 3. What mode am I in? 4. What can I control now? 5. Is the system healthy & synced?

---

## §6 · Principles & Governance

### 6.1 The six principles (board 00 §8) — verbatim, load-bearing

1. **Clarity** — first. One idea dominates.
2. **Context** — always. Mode, tool, and focus.
3. **Feedback** — real-time. See it. Feel it. Trust it.
4. **Depth** — on demand. Surface simple, reveal power.
5. **Consistency** — everywhere. Predictable and learnable.
6. **Performance** — matters. Smooth, fast, responsive.

### 6.2 DO / DON'T (board 00 §7) — verbatim

**DO:** build an operating grammar not a gallery · prioritize clarity, hierarchy, context · use meaningful A/B only when needed · keep the center sacred for primary readout · reveal depth progressively · respect performance and encoder UX.

**DON'T:** make more decorative variant dials · put a collar on every screen · bury the key information · overload with simultaneous data · break consistency across modes · sacrifice legibility for style.

### 6.3 Governance — what is locked / open / forbidden

| | |
|---|---|
| **LOCKED** (spec revision required to change) | radial grid · ring roles · gesture model · state model (§4.1) · component set (§3) · legibility ladder · the six principles |
| **OPEN** (sanctioned variation) | **Theme only** — palette, motion profile, density. The theme space is *wide open* — no theme is canonical (Captain 2026-06-29); propose/swap freely. The grammar is theme-agnostic. |
| **FORBIDDEN** | new decorative dials · per-screen collars · burying key info · simultaneous-data overload · cross-mode inconsistency · legibility traded for style |

> **The governance test (apply before any K718 UI change):** *Does this compose existing named HALO elements within the locked grammar, varying only Theme Territory?* If yes → in grammar, proceed. If it invents a new layout/dial → out of grammar, STOP (this is the churn the freeze was meant to end).

---

## §7 · Glossary (the canonical names)

| Term | One-line definition |
|---|---|
| **HALO** | the radial design language / grammar for SpectraSynq round-display instruments |
| **Radial Grid** | placement by radius band × angular zone (polar, not rectilinear) |
| **Radius band (B0–B4)** | concentric zones bezel→center: Bezel-Safe · Nav Ring · Control Ring · Signal Core · Readout Center |
| **Angular zone** | Crown (12) · Right Arc · Keel (6) · Left Arc |
| **Readout Center** | the one sacred primary value+unit |
| **Nav Ring / Control Ring / Signal Core** | navigation / active-parameter / live-signal bands |
| **State Edge** | always-visible bottom status zone (hosts System Status Strip) |
| **Dot-Ring** | shared LED-dot ring primitive |
| **Truth Ring** | Dot-Ring in `Pending` state, colored by trust progress |
| **Promotion Lane** | pending-action bar (rotate/press/hold) |
| **Status Badge** | Trust-State pill at the Crown (`PEND` etc.) |
| **Mode Compass** | radial mode preview/select fan |
| **System Status Strip** | global truthful status bar |
| **A/B Layer / Alert Layer** | overlay layers (compare-morph / interrupt) |
| **Attention Level** | Glanceable→Aware→Engaged→Focused (Axis A) |
| **Trust State** | Settled→Pending→Committing→Committed (Axis B) |
| **Theme Territory** | the only sanctioned visual-variation axis (5 named) |
| **Semantic accent** | fixed-meaning color (focus/active/input/confirm/alert) |
| **Legibility Ladder** | role-based type scale T1–T6 with min contrast |

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-29 | agent:claude-code | Created v0.1 canonical spec: rationalized taxonomy from 4 boards; split conflated state model into Attention×Trust×Alert (R1); canonicalized ring roles (R2); preserved Theme Territory names as token sets (R3); marked Modes layer pending DLG-01 firmware verification (R4). Token values + Modes backing integrate from DLG-02 / DLG-01. |
