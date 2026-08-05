---
abstract: "Handover for the next K1 agent (2026-07-11). Go-dark + serial-toggle fix are SHIPPED to origin/main (accc5f0). The live thread: porting Captain's hand-rated PROVEN effects from Lightwave-Ledstrip (firmware-v3, READ-ONLY reference) into the K1 fork (~/SpectraSynq_K1_Firmware, the DEV TARGET). 10 gems surfaced with faithful algorithms + port plans in k1_gem_effects_surfaced_2026-07-11.md; animated visual published. AWAITING Captain's pick of which gem(s) to port first. Read the LOAD-BEARING LESSONS before doing anything visual or generative."
---

# K1 Handover — Gem Effects Port (2026-07-11)

## 0. Load-bearing lessons (read FIRST — each cost a Captain blow-up this session)

1. **DEV TARGET = the K1 fork `~/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE`.** `firmware-v3` (in `~/Workspace_Management/Software/Lightwave-Ledstrip/`) is a **READ-ONLY reference** to mine — build NOTHING there. Captain was emphatic ("be FUCKING SURE").
2. **Visual decisions are shown, never described.** Any effect/family/geometry choice Captain must judge by eye → build a self-contained animated HTML, headless-screenshot it (`Google Chrome --headless=new --virtual-time-budget=… --screenshot`), **Read the PNG, fix every flaw yourself, THEN publish** (Artifact tool). For MOTION, capture 2–3 timepoints and confirm the light actually moved. Presenting a visual decision as text/markdown is a STOP-class violation.
3. **The axis for light-show work is MOTION PROPAGATION** — light that visibly TRAVELS across the plate over frames. Stationary patterns (standing waves, static zones, breathing blobs) are BANNED and will be rejected.
4. **Work from Captain's PROVEN shortlist, do not invent.** He hand-rated ~42 real Lightwave-Ledstrip effects (tier 1/2, with 0x… IDs). Two rounds of *invented* families (static fields, then invented motion families) were rejected. The accepted approach: read the REAL code of his gems and surface them faithfully.
5. **Waveform-Fast / Waveform-Tempo = the motion-quality yardstick** (alive, trailing conveyance) — but their scroll mechanic is OFF-LIMITS to copy; Captain detects a waveform clone instantly.

## 1. State (verify before acting)

- **Repo:** K1 fork `~/SpectraSynq_K1_Firmware`. `origin/main` HEAD = **accc5f0** (serial-toggle fix) on top of **b538b14** (go-dark default-flip) on **e47877a** (loud-guard retune).
- **SHIPPED this session (done, hardware-validated):** (a) silence go-dark — plate darkens in silence, default-ON (b538b14); (b) `:standby_dimming` serial toggle fix (accc5f0). See `[[project_k1_godark_shipped]]`.
- **Devices (MAC-verify before ANY flash):** bench `usbmodem1401` = MAC `B4:3A:45:A5:89:B4` (IM73D bench, currently running the shipped go-dark+toggle build); main `usbmodem12401` = MAC `B4:3A:45:A5:87:F8` (untouched). Ports drift — match by `pio device list` SER=MAC.
- **Effect ID registry:** `firmware-v3/src/config/effect_ids.h` (EID_* constants). Implementations: `firmware-v3/src/effects/ieffect/` + `.../sensorybridge_reference/`.

## 2. The live thread — port a proven gem to the fork

**Where we are:** the gem research is DONE. Captain approved the approach ("exactly what was needed"). **AWAITING his pick of which gem(s) to port first.** Do not start coding until he picks.

**The 10 surfaced gems** (full faithful per-frame algorithms + fork port plans in `docs/research/k1_gem_effects_surfaced_2026-07-11.md`; animated visual published, URL id `cab13a1c-32d4-4f44-bdb2-84d949d1f695`):

| id | name | tier | motion |
|----|------|------|--------|
| 0x1B06 | Time-Reversal Mirror Mod1 | best ◆ | damped wave propagates out, then replays **backwards + phase-flipped** (u=1−v). Flagship novelty. |
| 0x1313 | K1 Waveform Hybrid | best ◆ | bouncing amplitude-dot + scroll trail (the reference feel) |
| 0x1309 | K1 Bloom BassTreble | best ◆ | audio-warped outward bloom (bass=birth, treble=speed, √-warp) |
| 0x1C05 | Mach Diamonds (5L-AR) | best | shock-cell train marches out, bass compresses spacing |
| 0x1C08 | Moiré Cathedral (5L-AR) | best | detuned gratings → migrating ribs |
| 0x1C0B | Rose Bloom (5L-AR) | best | breathing rhodonea figure (petal count 3→7) |
| 0x1404 | Beat Pulse Resonant | good ⚡ | two rings **contract inward** edge→centre (only inward transport) |
| 0x1A03 | LGP Bass Quake | good ⚡ | centre-launched **projectile** flies off the edge |
| 0x0E0A | Snapwave | good ⚡ | chord-wobble dot + 40-frame ring-buffer comet |
| 0x130E | SB Spectral Envelope | good | 8 frequency-anchored dots scroll out (streaming spectrogram) |

**Recommendation (mine, not yet Captain-confirmed):** port the **4 zero-input-gap easy wins first** — Beat Pulse Resonant, Bass Quake, Snapwave, Moiré Cathedral — to validate the fork port harness end-to-end, then tackle **Time-Reversal Mirror Mod1** as the flagship.

**Governance flags (do NOT port without clearing):**
- **0x1B04 Fresnel Caustic Sweep** — Captain REVOKED a prior GO (claude-mem obs #47095), design-survey protocol pending. Withheld.
- **0x0E06 Spectrum Detail Enhanced** — best-tier but UN-portable: needs a 64-bin spectrum the fork lacks (fork has only `bands[0..7]`).

## 3. How to port a gem into the fork (mechanics)

Fork top-level modes are plain functions in `effects/light_mode_*.cpp` writing `CRGB16 leds_16[NATIVE_RESOLUTION]`, centre-origin (content at LED 79/80, mirrored outward), no-heap, static/.bss buffers. To add one:
1. New `effects/light_mode_<name>.cpp` implementing the effect's real algorithm (from the dossier's simDigest — those were extracted faithfully from source).
2. Append an enum slot in `system/config_types.h` (tail was `LIGHT_MODE_PERCUSSION_BURST`; next free slot ~30 — verify against HEAD).
3. Add a dispatch arm in `SPECTRASYNQ_K1_FIRMWARE.ino` (render dispatch ~lines 274–381).
4. Register the serial/mode selection as needed.

**Recurring fork gaps (resolve ONCE, reusable across all ports):**
- `audioConfidence` / `silentScale` — firmware-v3 ControlBus envelopes the fork lacks → synthesise from rms+onset with a hold timer, or default 1.0.
- spectral **flux** (fastFlux / onset transient level) → map to fork onset/novelty or a band-delta, or zero the term (graceful degrade).
- `hopSequence()` → replace with per-frame updates.
- `circularChromaHueSmoothed` / `getHeavyChroma` / `AsymmetricFollower` → small helpers, port once (needed by Time-Reversal, the 5L-AR set).
- `cinema::apply` / LGPFilmPost → optional post layer, drop.
- **RAINBOW compliance:** nearly every gem uses a free-running `gHue` global rotation — FREEZE it or redirect to a chroma/chord-derived base hue on EVERY port (fork no-rainbow rule).
- **MEMORY:** only Time-Reversal (320KB history ring) and RD Triangle (2.5KB) need real buffers → Time-Reversal must be `EXT_RAM_BSS_ATTR` / one-time SPIRAM malloc at boot (8MB PSRAM), NEVER internal DRAM; no heap inside render().

## 4. Standing constraints & workflow

- **Dev lifecycle for a port:** `/brainstorming` → `/software-architecture` → `/test-driven-development` → implement. No production code without a failing test first.
- **Hardware-test-before-commit** — flash the MAC-verified bench, behaviourally validate, THEN commit. Commit/push ONLY when Captain asks.
- **RBDO gate:** label tactical output GROUNDED / DEGRADED-MODE / REFUSED.
- Centre-origin 79/80; no-heap-in-render; <2.0ms/frame @120FPS; no rainbows; British English everywhere.
- **Serial gotcha:** the fork routes typed `:cmd=val` setters through `serial_cmd_dispatch_pure_setter` (serial_menu.h:3326) FIRST — add/fix setters THERE, not in the serial_menu.h else-if ladder (it is shadowed/dead).
- **Tooling:** clangd NOT wired for the fork (use rg + Read). RTK corrupts grep STDOUT (use Read/file-redirect). Ultracode/Workflow for multi-agent research. Bench serial: never run afplay concurrent with a pio flash.

## 5. Prior (rejected) research — do NOT resurface
- `k1_lightshow_mode_families_research_2026-07-10.md` — invented STATIC families (standing wave, strata). REJECTED.
- `k1_motion_propagation_families_2026-07-10.md` — invented MOTION families (Detonation, Caustic, Soliton…). REJECTED as not-from-the-real-library. Kept only as motion-vocabulary reference.
- **Canonical = `k1_gem_effects_surfaced_2026-07-11.md`** (real gems from Captain's shortlist).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:claude-opus-4-8 | Created — go-dark + toggle shipped; gem-port thread handover; awaiting Captain's port pick. |
