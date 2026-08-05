---
abstract: "Handover for the K718 Remoted controller-UI design work. Next agent: READ THIS FIRST, then _BUILD-STATUS.md. Captures device truth, the 3 hard laws, Captain's KEEP/CHANGE/CUT decisions, the dual-channel + touch model, current artifacts, and the exact next step (pick + build a centre visualisation to the Afterglow reference). Do not re-litigate settled decisions."
---

# K718 Remoted — Controller UI · HANDOVER (2026-06-30)

**Working dir:** `/Users/spectrasynq/SpectraSynq_K1_Firmware/artifacts/K7180-Design-System/`
**Read order:** this file → `_BUILD-STATUS.md` → inspect the reference images (below) → `reference/live.html`.

## 1. What this is
Designing the **on-screen UI for the K718 Remoted** — a physical controller for the SpectraSynq **K1** audio-reactive lightshow. NOT the K1 firmware itself. The deliverables are HTML/canvas design previews + a spec + tokens + a skill.

## 2. DEVICE TRUTH (do not get this wrong — it caused days of churn)
- **Hardware:** Guition **JC3636K718**, round IPS LCD, **360×360** physical (boards drew 480×480 — design canvas is modelled at 480 then scales; 360 is the real flash target).
- **Transport: BLE-MIDI ONLY.** WiFi rejected (instability). Captain-locked.
- **Inputs:** rotary **encoder (rotation only — KNOB_LEFT/RIGHT, NO hardware press)** + **capacitive TOUCH** (swipe + tap).
- **13-LED physical ring** outside the glass = the real trust/confirm surface (CONF is unbacked over BLE; the K1 never acks).
- **DUAL CHANNEL: Primary + Secondary.** Most params are per-channel (mode, palette, photons, chroma, mood, saturation, mirror, incandescent…). Globals: brightness, sensitivity, edge, preset, calibration. Secondary has an ENABLED flag. (71-path BLE-MIDI map: `docs/protocol/k1-ble-midi-map.json` in the firmware repo.)
- **Firmware-honesty (Rule H-1):** a value is "live" only once it crosses the BLE feedback channel. Today only mode-numbers come back. BPM is computed but not yet transmitted. Audio (spectrum/chord) does NOT cross BLE → any spectrum on the dial is SIMULATED until a data path is built. KEY/TIME do not exist in firmware (Captain roadmap).

## 3. THE THREE HARD LAWS (Captain-hammered — never violate)
- **L1 — EVERYTHING RADIAL.** No straight lines/rows on a circular screen. (Killed the straight spectrum bars.)
- **L2 — ZERO COLLISIONS.** Strict radial-band zoning; nothing overlaps, clips, or leaves the screen. Ever. The Captain checks this ruthlessly.
- **L3 — CROWN SACRED.** Top of bezel (12 o'clock) is reserved for the BLE telltale only; nothing else passes through it.

## 4. INTERACTION MODEL (Captain-specified)
- **Swipe ↑ (touch)** → FUNCTION MENU (a tappable list of all control screens / more menus).
- **Tap (touch)** → select on screen (tap a palette swatch, a toggle, a menu row, the PRI/SEC tabs).
- **Turn (encoder) / scroll** → adjust the active value.
- **Channel:** persistent **PRI / SEC** tabs at the top (flanking the telltale); tap to switch; per-channel params follow the selected channel.
- Two axes: **touch = navigation, encoder = value.**

## 5. CAPTAIN'S ELEMENT DECISIONS (from `reference/element-guide.html` export — LOCKED)
**KEEP:** Display Canvas · Safe Area · 13-LED Ring · Encoder · Bezel (crown SACRED) · Readout · BLE Telltale.
**CHANGE (with notes):**
- Radius Bands → largest/outer ring = **BPM-reactive animation** (done: comet sweep).
- Curved Mode Labels → curved YES, but **off the sacred crown, on-screen, no collision** (done: keel).
- Dot-Ring → reimplement clean (done).
- Signal Viz → **RADIAL only** (in progress — see §7 viz options).
- Parameter Arcs → keep, execute cleanly (done: side arcs).
- State-Edge Label → stop overlap → folded into keel mode-name.
- Truth Ring → rework, **no collisions** (currently omitted; FAKE over BLE — LED ring does trust).
- Theme Directions → **gate themes in a "User Settings" menu** (single active theme on dial).
**CUT:** Graduation Marks (ticks) · Needle/Pointer · Focus/Active/Confirm rings · Alert Overlay.

## 6. VISUAL DIRECTION (the reference — INSPECT THESE FIRST)
The Captain's target look = **SPECTRASYNQ K1 "Afterglow District"**: dense, cinematic, **glowing layered** neon dial — concentric rings + radial parameter arcs + fine spectrum texture + bloom, magenta/cyan on near-black. NOT flat/minimal.
**Reference images (load these on a fresh context):**
- `~/Downloads/GPT_Dial_Inspo/ChatGPT Image Jun 27, 2026, 01_39_27 AM.png` (the K1 dashboard — verified)
- `~/Downloads/GPT_Dial_Inspo/ChatGPT Image Jun 27, 2026, 01_39_40 AM.png`
- `~/Downloads/GPT_Dial_Inspo/ChatGPT Image Jun 27, 2026, 01_39_47 AM.png`
- `~/Downloads/ChatGPT Image Jun 29, 2026, 08_05_23 PM.png`
- `~/Downloads/ChatGPT Image Jun 30, 2026, 07_19_04 AM.png`
- (+ 6 more images the Captain pasted in chat on 2026-06-30 ~07:25 — ask Captain to re-share or check that day's attachments.)

## 7. CURRENT ARTIFACTS (all in `reference/` unless noted)
- **`live.html`** — THE controller: multi-function, **dual-channel (PRI/SEC tabs)**, touch model (swipe↑ menu / tap / turn), function set MODE·PALETTE·PHOTONS·CHROMA·MOOD·SATURATION·BRIGHTNESS·SENSITIVITY·EDGE·MIRROR·PRESET·SETTINGS, radial value-arcs, palette swatch-ring + live gradient, BPM comet-sweep outer ring, crown telltale, 13-LED ring. Laws held. Stubs: SETTINGS, EDGE(toggle only), PRESET(no save/load), secondary-ENABLED gate.
- **`viz-options.html`** — **11 centre-visualisation options** (Radial Bars, Pulse Rings, Circular Wave, Liquid Blob, Particle Burst, Oscilloscope, Dot Matrix, Spiral, Liquid Fill, Aurora, **#11 AFTERGLOW★** = the dense glow-ring look matching the reference). **Captain is choosing one.** All radial, animated, 0 errors.
- **`element-guide.html`** — the jargon-format inspection guide (every layer isolated + KEEP/CHANGE/CUT + export). This is where the §5 decisions came from.
- `halo.js`, `gallery.css` — the static layer renderer + gallery styling (older).
- `spec/K718-DESIGN-LANGUAGE.md` — canonical spec (NEEDS: encode L1–L3, the dual-channel model, the touch model, the cut-list, themes-in-Settings — not yet done).
- `tokens/tokens.json`, `tokens.css`, `themes/themes.css` — design tokens (contrast-verified; **Oswald font is BANNED**; display = DIN Condensed Bold + Inter; web proxy = Saira Condensed).
- `00-03.*.png` boards, `fonts/` (the type standard).
- `~/.claude/.../k718-radial-grid/SKILL.md` (project `.claude/skills/`) — polar-grid skill (NEEDS updating with L1–L3 + collision + crown-sacred rules).

## 8. NEXT STEPS (in order)
1. **Inspect the reference images (§6)** at full context — extract the exact Afterglow look.
2. **Captain picks a centre viz** (from viz-options.html, likely #11 AFTERGLOW or a blend). Build the chosen one into `live.html`'s centre at real scale, tinted to the active palette + beat. Match the reference's density/glow/bloom.
3. Flesh the stub screens: SETTINGS (themes live here) · EDGE (toggle + strength) · PRESET (save/load 10 NVS slots) · Secondary ENABLED gate.
4. **Encode into the spec + `k718-radial-grid` skill:** L1–L3, dual-channel, touch model, function set, cut-list. So it stops drifting.

## 9. WORKING NOTES
- **Verify every render with Playwright headless** (Chrome extension is dead; Playwright installed in the session scratchpad). Pattern: write a tiny `.mjs`, `chromium.launch()`, screenshot, check console errors. The Captain WILL spot collisions/clipping — check screenshots yourself first.
- **Decode Captain decisions precisely; do NOT pre-decide** what to keep/cut — present and let Captain rule (that's why the element-guide exists).
- Captain communication is blunt/profane under frustration; stay focused on the work, decode the substance, don't moralise. Progress + correctness is what de-escalates.
- The churn that wasted days = building ONE screen (mode select) and missing scope (palette, other functions, dual channel, touch nav). Don't repeat: the K718 is a FULL multi-function dual-channel touch controller.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-code | Created handover at end of session: device truth, 3 laws, element decisions, dual-channel + touch model, Afterglow visual direction, 11 viz options, next steps. |
