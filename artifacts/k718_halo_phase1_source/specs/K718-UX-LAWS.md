---
abstract: "K718 hard UX laws + considered interaction/feedback design (Captain-ratified 2026-06-30). Bans on-screen PEND/CONF/status text and the centered value-number and on-screen rim dots. Defines the out-of-band feedback architecture (physical LED ring + speaker + haptic), the single-hand rotary+touch radial interaction model, and the mic-driven honest centre field. Read BEFORE any K718 UI/firmware work."
---

# K718 UX Laws & Interaction Design (LOAD-BEARING)

Captain-ratified 2026-06-30. These are **laws**, not suggestions. Violating a LAW is grounds for stopping the work.

## Hardware the design MUST capitalize on

Big central **rotary encoder** (no HW press) · full-round **capacitive touch** (360×360) · **physical 13-LED ring outside the glass** · **MEMS microphone** · **speaker** · **DRV2605 haptic** · BLE-MIDI link to K1.

The screen is ONE channel among many. Status and confirmation are **out-of-band**. The glass stays a clean, honest visual instrument.

## LAW 1 — No status text on the glass, ever (PEND/CONF BANNED)
Never render PEND / CONFIRMED / ACK / "received" / "applied" / connection-status as on-screen text or badges. Receipt/link state is communicated out-of-band only:
- **Failure suspected** (no ack / rejected / send-timeout) → **physical LED ring flashes RED rapidly ×5** + error tone (speaker) + sharp haptic.
- **BLE link lost** → **physical LED ring holds solid RED** while offline; clears + confirm chime on reconnect.
- The CONF/ack endpoints (`remoted_control_confirmed_mode`, `on_ble_rx`, `pending_age`) may be consumed *internally* to drive ring/speaker/haptic — never rendered as text.

## LAW 2 — Nothing in the bullseye but the visual
The centre is the hero audio-reactive field. **No number, no readout, no label slapped in the dead centre.** The active parameter's value lives on the **periphery** (an arc/gauge read like a dial), never over the focal point.

## LAW 3 — No on-screen rim dots
The **physical LED ring** owns rim-level indication. Do not duplicate it on glass. No decorative on-screen 13-LED ring, no redundant rim dot-ring.

## LAW 4 — The centre field must be honest
The centre visual is driven by the **K718's own MEMS mic** (local ambient audio analysis), so it genuinely reacts to the room's music. It is NOT a canned `bpm=128` animation. If mic-drive is unavailable, the field must read as deliberately ambient — never framed as "beat-reactive" while faking it.

## LAW 5 — Single-hand, friction-removing interaction
Designed for one thumb on a held device. The 80% case needs zero navigation; any function is ≤2 gestures. No linear 13-row menu.

- **Rotary turn** → adjust the active parameter (hero action; haptic + speaker tick per detent; eyes-free).
- **Swipe up (from bottom)** → **radial function picker** (icon sectors around the rim, the round screen's natural form). The **rotary scrubs the highlight**; **tap or dwell commits** — so selection works by feel, not precise tapping.
- **Swipe down** → back / home.
- **Swipe left / right** → switch channel **PRI ↔ SEC** (one thumb-flick; channel shown by field tint + LED-ring colour, not text).
- **Tap (centre)** → context toggle (EDGE/MIRROR) or commit.
- **Long-press / double-tap** → jump to the most-common function (e.g. BRIGHTNESS) — the "dim it NOW" shortcut.

## LAW 6 — Match UI to real capability
Do not show controls that do nothing. Show only the **5 committed presets** (not 10). Mark **VISUAL FIELD** and **SETTINGS** as local-only (they don't command the K1). No promise the firmware can't keep.

## Feedback channel map (out-of-band, screen stays clean)
| Event | LED ring | Speaker | Haptic | Screen |
|---|---|---|---|---|
| Detent / step | — | soft tick (mutable) | tick | arc updates |
| Applied OK | brief confirm sweep | optional chime | — | arc settles |
| Failure suspected | **RED ×5 rapid** | error tone | sharp buzz | **nothing** |
| BLE offline | **solid RED (held)** | — | — | field desaturates subtly |
| Channel PRI/SEC | tint segment | — | bump | field tint |

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-code | Created from Captain directives: banned on-screen PEND/CONF status text (LAW 1) + centered value-number (LAW 2) + on-screen rim dots (LAW 3); mandated mic-honest centre field (LAW 4), single-hand rotary+touch radial model (LAW 5), capability-truthful UI (LAW 6); defined out-of-band LED-ring/speaker/haptic feedback map. |
