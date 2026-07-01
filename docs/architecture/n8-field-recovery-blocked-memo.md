---
abstract: "N8 laptop-free field recovery — BLOCKED memo (Captain decision D6). The K1 production GPIO map compiles out ALL control + status pins (= -1), so a button-combo factory-reset and any status-indicator path are both dead on K1. Cannot be implemented until Captain assigns enclosure GPIO(s). Default: v1 ships with serial-only recovery as a documented limitation. Read before reopening D6 or attempting N8 code."
---

# N8 — laptop-free field recovery: BLOCKED on hardware GPIO (memo, D6)

**Class D-gated · P1 · Decision: D6 (Captain-only — hardware/enclosure).**

## The gap
A backer with a wedged unit has **no laptop-free recovery**. Today's only factory-reset is **serial-only** (USB CDC) + a typed `CONFIRM` — useless to a field user without a computer and the serial protocol.

## Why it is BLOCKED (verified 2026-06-30, read-only)
The K1 production build **compiles out every control and status pin**:
- `constants.h:288-292` — PHOTONS / CHROMA / MOOD / NOISE_CAL / **MODE_PIN all `= -1`**.
- `constants.h:293-295` — SWEET_SPOT status-indicator pins all `= -1`.
- (The non-K1 dev path *does* define real pins: `MODE_PIN 45`, sweet-spot `7/8/9` — so the code paths exist, but K1 has no physical pins wired to them.)

Consequence: both the **button-combo factory-reset** path and any **status-indicator** (visual "resetting…/ok") path are dead on K1. Writing N8 code now would mean inventing GPIO assignments — guessing against unassigned hardware, which is exactly the failure mode to avoid.

## What unblocks it (D6 — Captain)
Assign K1 enclosure GPIO(s) for: (a) a reset button or button-combo input, and (b) at minimum one status-indicator output (can reuse the existing LED strip for a status pattern if no spare GPIO). Once assigned, the autonomous scope is straightforward and host/build-gated: a debounced button-combo → factory-reset (reuse the existing serial reset path) + a status pattern, all **gated on the pins being defined** (`!= -1`).

## Recommendation (D6)
**Decision required:** does v1 get a laptop-free recovery affordance, and if so which GPIO(s)?
**Options:** (a) assign a dedicated reset GPIO + spare status LED; (b) button-combo on an existing input + status via the LED strip (no new GPIO); (c) defer — v1 ships serial-only.
**Recommended:** (b) if any existing input can carry a long-press combo — lowest hardware cost, real field-recovery. **Blast radius:** enclosure/hardware (irreversible once tooled).
**Default if no override:** ship v1 with **serial-only recovery documented as a known limitation**; revisit for v2 hardware. No code until pins are assigned.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 | Created. N8 blocked memo: K1 compiles out all control/status pins (constants.h:288-295 = -1); button-combo + status-indicator recovery impossible until Captain assigns enclosure GPIO (D6). Default = serial-only recovery, documented limitation. |
