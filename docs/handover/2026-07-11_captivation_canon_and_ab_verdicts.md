---
abstract: "Handover for the next K1 agent (2026-07-11, evening). Supersedes the earlier gem-port handover. The session's crown output: the CAPTIVATION-TRANSPOSITION framework (docs/architecture/effect-decomposition/00b-captivation-transposition.md) that solves Captain's single biggest frustration — transposing Waveform's captivation onto NEW effects without them collapsing into looking like Waveform. On-device A/B verdicts landed: mode 32 (Waveform Hybrid K1 = the OG Sensory Bridge waveform) is STUNNING (7.5-8/10, colour polish just flashed, awaiting re-verdict); modes 30/31/33 FAILED and are to be binned. Forward work: build Cannonade + Shockwave + Iris (distinct captivating families, FULL DNA). All work is UNCOMMITTED on branch lane/gem-port-beat-pulse. Read 00b + §0 lessons before any effect work."
---

# K1 Handover — Captivation Canon + A/B Verdicts (2026-07-11 evening)

## 0. The one thing that matters (read this first)

**Waveform mode is the PINNACLE** — the original Sensory Bridge effect (deprecated by SB's designer; Captain revived + improved it): *"fast, snappy, it captivates,"* a few lines refined over months. **Captain's single biggest frustration, and the product's core challenge:** transpose Waveform's *captivation* onto NEW effects **without them collapsing into looking like Waveform**.

The session produced the framework that solves it — **`docs/architecture/effect-decomposition/00b-captivation-transposition.md`. READ IT before touching any effect.** The law:

> **Transpose the temporal envelope + audio-causality (the captivation DNA — identity-neutral). Vary the spatial + engine identity.**

Collapse is STRUCTURAL, exactly two leaks: (1) the **outward-scroll-of-a-trace engine**, (2) **amplitude→position**. Keep either → it reads as Waveform. The captivation lives in the temporal envelope, not the silhouette.

## 1. State (verify before acting)

- **Branch:** `lane/gem-port-beat-pulse` (LOCAL, off `main` @ `e47877a`). **ALL WORK UNCOMMITTED.** Commit/push ONLY when Captain asks.
- **Bench:** `usbmodem1401`, MAC **B4:3A:45:A5:89:B4** (IM73D) — flashed with modes 30–33 + the mode-32 colour polish. **Main unit `usbmodem12401` MAC B4:3A:45:A5:87:F8 — DO NOT TOUCH.**
- **Build env:** `k1_bench_im73d`. MAC-verify every flash.

## 2. On-device A/B verdicts (Captain — the SENSE pass; these are FACT now, [PERCEPTION] resolved)

| Mode | Effect | Verdict | Action |
|---|---|---|---|
| 30 | Beat Pulse (0x1404) | FAIL — bland, no motion variation, no novelty | **BIN** |
| 31 | Bloom BassTreble (0x1309) | FAIL — "spastic, twitches and rotates in/out, can't control its limbs." Has *potential* but the engine is wrong | **BIN** (not tweakable) |
| 32 | **Waveform Hybrid K1 (0x1313)** | **WIN — "basically the OG SB waveform, still stunning, 7.5–8/10."** For 10: more colour variation/palette nuance | **KEEP** — colour polish flashed, awaiting re-verdict |
| 33 | Moiré Cathedral (0x1C08) | FAIL — "stuttering, unpredictable flickers, black-line segmenting, cheap sparse-strip look." 3/10 | **BIN** |

**Critical insight:** the easing retrofit (asymmetric release) fixed *brightness on/off* but NOT **incoherent MOTION** — 31/33 fail because their motion is erratic/uncaused (a core-algorithm problem the easing layer can't reach). Coherent transport (32/Waveform) captivates; field/pump gem-ports read as malfunction. **Purpose-built coherent-motion families (00b) > patching gem-ports.**

## 3. Forward work (priority order)

1. **Await Captain's verdict on the mode-32 colour polish** (is it 10/10?). Levers if more is needed, in `effects/light_mode_waveform_hybrid_k1.cpp`: `WFHYB_HUE_SPREAD` (0.25 — amplitude→palette walk) and `WFHYB_TAU_COLOUR` (0.08 s — colour EMA; lower = hue moves more). Motion is untouched; only these two colour knobs changed this session.
2. **Bin 30/31/33** (Captain's call). Enum is append-only/persisted — simplest is to gate them out via `light_mode_is_enabled()` / the director allow-list, not to delete enumerators. Or leave as also-rans if Captain prefers.
3. **THE BIG ONE — build the distinct captivating families:** **Cannonade + Shockwave + Iris** (00b §5–6), each via the §4 build recipe (separability gate → swap the engine out of Transport-scroll → sever amplitude→position → distribute/discretise injection → abstract the signal → inject the FULL 7-part DNA incl. *coherent audio-caused motion + swept re-stepping*, not just brightness easing → re-couple any autonomous engine → tempo-trap check → flicker guard). Behind a runtime toggle → **4-way on-device A/B vs Waveform.** This is the real product direction.
4. **Commit the canon** (below) when Captain approves.

## 4. The canon this session built (all UNCOMMITTED, in the fork)

- `docs/architecture/effect-decomposition/00b-captivation-transposition.md` — **THE framework. Read first.**
- `docs/architecture/effect-decomposition/00-the-method.md` — §4.1 (measured asymmetric easing; raw-level pole ruled out) + §1.5 level-driven corollary. Points to 00b.
- `docs/architecture/effect-decomposition/01-waveform-class.md` — formal Waveform-class decomposition (created, then CORRECTED after Captain's fact-check — see lesson 2).
- `docs/effect-craft/PORTING_CRAFT_CANON.md` — the execution playbook (perf, build, serial, workflow) — defers to the-method as design authority.
- `SPECTRASYNQ_K1_FIRMWARE/visual/easing.h` — `k1ease::follow/ema/decay/safe_dt/peak_follow` (shared kit; consolidates 8+ private followers).
- `.claude/skills/k1-effect-development/SKILL.md` (amended: mandatory easing + per-LED perf sections) · `.claude/skills/k1-effects-router/SKILL.md` (NEW — routes any effect task to the right skills).
- `tests/test_effect_easing_static.py` (6/6) + `tests/test_vp_probe_mode_coverage_static.py` — mechanical enforcement.
- Effects added: `effects/light_mode_{beat_pulse,bloom_bt,waveform_hybrid_k1,moire_cathedral}.cpp` + `beat_pulse_math.h` + `tests/native/test_beat_pulse_math.cpp`.

## 5. Load-bearing lessons (each cost a Captain correction — do not repeat)

1. **Waveform is the pinnacle; the goal is DISTINCT captivating families, not more waveforms.** Transpose the temporal envelope + audio-causality; vary the spatial/engine identity (00b). This is THE product problem.
2. **EPISTEMIC DISCIPLINE — never state look/feel as fact without Captain's on-device A/B.** I claimed mode 32 was "inferior/redundant" from ZERO visual evidence (confirmation bias, primed by an archetype); Captain overrode me and it turned out STUNNING. Label `[MECHANISM]` (code/file:line) vs `[PERCEPTION]` (interpretation, pending viewing) — the-method §8. **Captain's eye is the SOLE captivation-validation gate.**
3. **Easing fixes brightness on/off; it does NOT fix incoherent motion.** Motion coherence (audio-CAUSED, swept ≤28 px/step, never free-running) is a deeper, separate layer — the reason 31/33 still failed after the easing retrofit.
4. **Faithful gem-port works for coherent transports (Waveform), fails for field/pump effects (Bloom/Moiré → spastic).** Build purpose-made coherent families over patching ported field algorithms.
5. **Read the EXISTING canon before writing new canon.** I built PORTING_CRAFT_CANON in ignorance of `effect-decomposition/00-the-method.md` (which already framed easing as the Responsiveness↔Grace dial). Reconcile, don't compete.
6. **Mode-32 flat-colour cause:** single-centroid hue (`hue_offset=0`) + heavy 0.163 s RGB EMA = near-monochrome. Fix = palette walk + lighter EMA (done).

## 6. Standing constraints & tooling (don't relearn)

- **DEV = the fork** `~/SpectraSynq_K1_Firmware`; `firmware-v3` (in Lightwave-Ledstrip) = READ-ONLY reference to mine.
- **Effect idiom:** `void light_mode_X(CRGB16* leds_prev_buffer, ChannelEffectState& fx)`; global `leds_16[160]`, `HALF=80`, author upper half + `mirror_image_downwards`; centre-origin 79/80; no heap in render; <2.0 ms/frame; no rainbow (palette-bounded).
- **Per-LED perf:** NEVER call `effect_particle_colour` / `palette_manual_colour` / `effect_palette_or_chroma_colour` inside a per-LED loop — hoist once/frame. `render_us` is data-dependent — measure at full illumination via `:vp_stream=on`.
- **Easing MANDATORY** (via `visual/easing.h`): asymmetric `k1ease::follow` (attack 0.03–0.05 s / release 0.28–0.50 s, ≥5×), eased silence gate, `0.4+0.6·env` floor — PLUS coherent motion (00b).
- **6 wiring touchpoints** for a new mode: `config_types.h` enum (append-only) · `channel_effect_state.h` state fields · `lightshow_modes.h` decl · `.ino` `dispatch_legacy_lightshow` arm · `system.h` `set_mode_name` · **probe coverage** (`vp_probe_dispatch_and_hash` arm + `vp_probe_print_mode` line — enforced by `test_vp_probe_mode_coverage_static.py`).
- **Build/flash:** `pio run -e k1_bench_im73d [-t upload --upload-port <port>]`; confirm `Hash of data verified` + `Hard resetting` (silent-skip guard). MAC-verify bench first.
- **Serial:** baud **230400**; commands are `:cmd=val\n` (colon+equals) — `set_mode 30` (space) is eaten char-by-char as hotkeys, use `:set_mode=32`; `:vp_stream=on` for telemetry; opening the CDC port RESETS the board.
- **Cursor holds the serial port** — its monitor auto-reconnects after each flash-reset and blocks esptool (`lsof | grep usbmodem` shows the Cursor PID). Ask Captain to close it; don't kill the editor.
- **clangd is NOT wired for the fork** — ignore its errors (SFixed/CRGB16/hal.h/Xtensa); the `pio` build is the only truth. `rg`+Read to navigate. **RTK corrupts `grep` stdout** — Read files or redirect grep to a file.
- **Audio-playback-safety:** the agent CANNOT play music — the visual A/B is Captain's, always. **Hardware-test-before-commit. Commit/push ONLY when asked.** British English. RBDO labels (GROUNDED/DEGRADED/REFUSED).
- **Router:** `/k1-effects-router` routes any effect task (author/port/fix-stutter/perf/crash/colour/wire/debug) to the minimal relevant skills.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:claude-opus-4-8 | Created — supersedes the gem-port handover. Captures the Captivation-Transposition canon (00b), the on-device A/B verdicts (32 win / 30-31-33 bin), the mode-32 colour polish, the forward Cannonade/Shockwave/Iris build, and the session's load-bearing lessons (epistemic discipline, easing≠motion-coherence, read-existing-canon-first). |
