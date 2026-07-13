---
abstract: "Concrete build spec for the three purpose-built captivating effect families approved in 00b-captivation-transposition.md §6 — Cannonade (mode 34), Shockwave (35), Iris (36) — for a 4-way on-device A/B against Waveform Hybrid K1 (mode 32). Encodes the SHARED coherence contract (signature, dt/easing/silence-floor, centre-origin+mirror, no-heap/<2ms, per-LED perf, colour-source assignment) and each family's concrete physics (Cannonade = ballistic lob+inward-gravity+centre-crack; Shockwave = pure-AGE-integrated expanding shells, the deliberate contrast to amplitude-coupled pulse_prism; Iris = spring dilate-recoil membrane driven by the LIVE beat axis). TDD-first: each family has a pure math core (effects/<fam>_math.h) host-tested before the effect body. All look/feel is [PERCEPTION — PENDING Captain on-device A/B]; the agent cannot self-validate (audio-playback-safety). Created 2026-07-11 evening."
---

# Captivation Families — Build Spec (Cannonade · Shockwave · Iris)

*Execution spec for [`../architecture/effect-decomposition/00b-captivation-transposition.md`](../architecture/effect-decomposition/00b-captivation-transposition.md) §5–6. Design authority = 00b + [`../architecture/effect-decomposition/00-the-method.md`](../architecture/effect-decomposition/00-the-method.md). This doc is the concrete contract; it defers to those for the *why*.*

> **Goal:** three DISTINCT captivating families that carry Waveform's captivation DNA WITHOUT collapsing into looking like Waveform, wired behind manual `:set_mode` for a **4-way on-device A/B: mode 32 (Waveform Hybrid K1) vs 34 (Cannonade) vs 35 (Shockwave) vs 36 (Iris)**. Captain's eye is the sole captivation gate — every look/feel claim here is `[PERCEPTION — PENDING VIEWING]`.

## 0. Reconnaissance already done (do not re-litigate)
- The beat/tempo axis is **LIVE**: `k1_tempo_update()` runs in the AP loop (`SPECTRASYNQ_K1_FIRMWARE.ino:983`); `k1_tempo_read()` is consumed by 7+ effects. Iris may use it directly. (00b's "consumed by nothing" line is stale.)
- `pulse_prism` is an existing, enabled, director-selectable centre ring-pool BUT its radius is **amplitude-coupled** (`vel = reach/beat_s`, `reach ∝ spawn_strength`). Shockwave is built as the deliberate **pure-AGE** contrast; **`pulse_prism` is left UNTOUCHED** so the A/B tests 00b's hypothesis with zero regression.
- Cannonade and Iris are **net-new** (no existing effect has arc-return+centre-crack, or a spring dilate-recoil membrane).

## 1. Shared coherence contract (ALL three obey)
- **Signature:** `void light_mode_<fam>(CRGB16* leds_prev_buffer, ChannelEffectState& fx);` declared in `visual/lightshow_modes.h`, defined in `effects/light_mode_<fam>.cpp`.
- **dt:** `float dt = k1ease::safe_dt(millis(), fx.<fam>_last_ms);` (clamped, frame-rate-independent).
- **Persistence / trail:** `memcpy(leds_16, leds_prev_buffer, sizeof(CRGB16)*NATIVE_RESOLUTION);` → fade the trail with an **eased** decay → author the **upper half `[HALF, NATIVE_RESOLUTION)`** only (clear `[0,HALF)` first) → `finalize_additive_frame(leds_16, leds_prev_buffer, /*store_history=*/true);` → `if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);`. `HALF = NATIVE_RESOLUTION/2 == 80`; the mirror makes **centre origin 79/80** (HARD CONSTRAINT).
- **Easing MANDATORY** (`visual/easing.h`, namespace `k1ease`): route EVERY continuous audio level through the asymmetric `k1ease::follow(cur, tgt, dt, attack_tau, release_tau)` (attack 0.03–0.05 s, release 0.28–0.50 s, release ≥5× attack) BEFORE it touches any channel (brightness, radius, extent, launch velocity). **No raw audio→pixel** (the amateur strobe).
- **Silence + floor (00b §2.7):** an eased silence gate `fx.<fam>_sil` (fast-in ~0.05 s, slow-out ~0.30 s) fades the plate to **honest dark** on `snap.silence`; when active, apply a **breathe-not-blink brightness floor `0.4 + 0.6·env`**; keep reactivity OUT of the 5–20 Hz global-brightness flicker band (route it **spatially**, not as a global brightness pulse).
- **Swept re-stepping (00b §2.3):** integrate positions with dt and draw the **swept path** (prev→current), never a teleporting endpoint; clamp per-frame displacement ≤ ~28 px (sub-step if needed).
- **No-heap / perf:** no `new`/`malloc`/`String`; static consts only; **<2.0 ms/frame**; **hoist** `effect_particle_colour`/`effect_palette_or_chroma_colour`/`palette_manual_colour`/`cached_gradient_palette` OUT of any per-LED loop (compute per-frame, or per-particle at most). Measure at full illumination via `:vp_stream=on`.
- **Audio API (value-copy reads):** `k1_audio_snapshot_read()` → `peak_scaled, vu_level, novelty, low_energy, mid_energy, high_energy, chroma_strength, silence`; `k1_onset_beat_read()` → `event_id` (dedupe on change), `onset`, `bass_onset`, `onset_strength`, `bass_onset_strength`; `k1_tempo_read()` → `phase01, beat_tick, locked, confidence, beat_strength`. Do NOT invent fields — these are the whole surface.
- **Colour (no rainbow; palette-bounded).** Colour-source assignment (distinctness lever, 00b §2.6):
  - **Cannonade** → warm impact palette, palette-position by launch strength (harmony-anchored OK).
  - **Shockwave** → **broken off harmony→hue toward TIMBRE**: hue from spectral tilt `high_energy/(low_energy+high_energy+ε)` (or `novelty`), via `palette_manual_colour`. This is the family that varies the colour source.
  - **Iris** → chroma-anchored (`effect_particle_colour`), optionally beat-modulated.
- **British English** in all comments/strings.

## 2. Per-family physics

### Cannonade — mode 34 `LIGHT_MODE_CANNONADE` (ballistic LOB, arc-and-return)
- **Pool** `canna_*[CANNA_MAX]` (~6): `pos` (px from centre, 0..HALF), `vel` (px/s), `life`, `hue`, `impact_flash`.
- **Spawn** on fresh `bass_onset` (edge-detect `event_id`): launch from `pos=0` with **v0 = f(bass_onset_strength)** — amplitude→**velocity** (allowed), never position. Constant inward **gravity g** (optionally tempo-scaled).
- **Math core** `effects/cannonade_math.h`: `pos += v·dt; v -= g·dt;` apex at `v==0`; **impact** when `pos` returns to ≤0 → set `impact_flash ∝ |v_impact|`. Per-frame displacement clamp ≤28 px (sub-step). Pure, host-testable.
- **Draw:** comet-like head at `pos` + short wake (swept prev→pos); on the impact frame inject a bright **CRACK flash at centre 79/80** (eased). The strong-gravity **RETURN + centre crack** is the anti-Waveform signature.

### Shockwave — mode 35 `LIGHT_MODE_SHOCKWAVE` (EXPAND, pure-age shells)
- **Pool** `shock_*[SHOCK_MAX]` (~6): `age` (s), `life` (s), `vel` (px/s, **FIXED at spawn** — constant or tempo-bar-derived, **NOT amplitude**), `bright`, `hue`.
- **Spawn** on fresh `onset`: birth a ring at `age=0`, `life=fixed`. **Amplitude drives BRIGHTNESS / THICKNESS / spawn density — never radius or vel.**
- **Math core** `effects/shockwave_math.h`: `radius(age) = vel·age` (**= f(age) ONLY**); a thickness/brightness envelope over `age` (a wavefront that thins as it expands); death at `age ≥ life`. Pure, host-testable — a key assertion is **radius independent of amplitude**.
- **Draw:** an **annulus/shell** at `radius` with thickness, several coexisting shells (born/expand/thin/die), eased brightness. Explicitly the pure-age contrast to `pulse_prism`.

### Iris — mode 36 `LIGHT_MODE_IRIS` (DILATE + recoil in place, spring membrane)
- **State (single membrane):** `iris_r, iris_v, iris_target, iris_last_ms, iris_sil, iris_beat_phase` (+ `iris_baseline`).
- **Dynamics** `effects/iris_math.h` (pure): damped spring — `v += (k·(target - r) - c·v)·dt; r += v·dt;` (choose k,c for a lively **underdamped** overshoot-then-recoil; assert bounded/stable). **Impact** (fresh `onset`) sets `target = base + gain·onset_strength` (amplitude→**extent** of a bounded membrane, NOT a travelling point). The **live beat axis** breathes the baseline: `baseline = base + amp·(0.5 - 0.5·cos(2π·phase01))` (inflate toward the beat, recoil after) using `k1_tempo_read().phase01`.
- **Draw:** an in-place luminous **disc/membrane** filled from centre out to `r` with a soft edge — **NO advection** (no scroll, no particle). The boundary **REVERSING** (dilate then recoil about fixed 79/80) is the percept scroll cannot make.

## 3. TDD (non-negotiable — test FIRST)
For each family, write `tests/native/test_<fam>_math.cpp` against `effects/<fam>_math.h` and see it FAIL before implementing the core. Minimum assertions:
- **Cannonade:** launched with v0>0 under gravity g returns to pos≤0 (impact fires) after ~2·v0/g; apex height ≈ v0²/(2g); impact NOT fired mid-flight; displacement clamp holds.
- **Shockwave:** `radius` strictly increasing in age; **`radius` identical for two rings with different spawn amplitude** (radius ⟂ amplitude); ring dies exactly at `age≥life`.
- **Iris:** spring converges to a static target; **underdamped overshoot then recoil** (r exceeds target then returns) for lively params; no blow-up over 10 s; returns to baseline when target=baseline.
Follow the existing `tests/native/test_beat_pulse_math.cpp` harness pattern.

## 4. Wiring (6 touchpoints × 3 modes — orchestrator applies centrally)
1. `system/config_types.h` — append `LIGHT_MODE_CANNONADE, LIGHT_MODE_SHOCKWAVE, LIGHT_MODE_IRIS` before `NUM_MODES` (append-only; ordinals 34/35/36). Do NOT add to the `light_mode_is_enabled` disabled list (→ enabled). Do NOT add to the director allow-list (`director/k1_mode_selection.cpp`) → manual A/B only.
2. `visual/channel_effect_state.h` — append each family's field block.
3. `visual/lightshow_modes.h` — 3 `void light_mode_<fam>(CRGB16*, ChannelEffectState&);` decls + 3 probe arms (`vp_probe_dispatch_and_hash` + `vp_probe_print_mode`) — enforced by `tests/test_vp_probe_mode_coverage_static.py`.
4. `SPECTRASYNQ_K1_FIRMWARE.ino` — 3 `else if (mode == LIGHT_MODE_<fam>) light_mode_<fam>(channel.history, *channel.effect);` arms in `dispatch_legacy_lightshow`.
5. `system/system.h` — 3 `set_mode_name` entries.
6. New files: `effects/light_mode_<fam>.cpp` + `effects/<fam>_math.h` + `tests/native/test_<fam>_math.cpp`.

## 5. Acceptance
- Native math tests pass (host g++).
- `pio run -e k1_bench_im73d` builds; each mode <2.0 ms/frame at full illumination (`:vp_stream=on`).
- `test_vp_probe_mode_coverage_static.py` + `test_effect_easing_static.py` pass.
- Captain flashes the bench (MAC B4:3A:45:A5:89:B4) and runs the 4-way A/B. **No commit until Captain signs off** (hardware-test-before-commit).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:claude-opus-4-8 | Created — concrete build spec for Cannonade/Shockwave/Iris per 00b §6: shared coherence contract, per-family physics, TDD-first math cores, 6-touchpoint wiring, and the pure-age-vs-pulse_prism Shockwave decision. |
