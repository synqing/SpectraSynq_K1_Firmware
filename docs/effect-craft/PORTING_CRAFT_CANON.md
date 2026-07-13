---
abstract: "Canonical craft standard for porting/authoring K1 fork light-show effects, distilled from the 2026-07-11 gem-port session where a run of technically-faithful ports were rejected as amateur. THREE non-negotiable layers a port must pass before it is worth Captain's eyes: (1) MANDATORY temporal easing — asymmetric fast-attack/slow-release on every audio drive, trail decay, smoothed silence gate, brightness floor (raw audio->brightness is the #1 amateur failure); (2) per-frame perf discipline — never call heavy colour/trig helpers per-LED (blew the 2ms ceiling twice); (3) the fork idiom + wiring + hardware-validate workflow. Uses visual/easing.h. Read before touching any effects/light_mode_*.cpp."
---

# K1 Effect Porting & Craft Canon

**Status: LOAD-BEARING. Read before creating, porting, or modifying any `effects/light_mode_*.cpp`.**
Companion to the `/k1-effect-development` skill (discovery), `visual/easing.h` (the shared kit), and `tests/test_effect_easing_static.py` (enforcement). STROBE LAW lives in `/sensorybridge-doctrine`.

> **Design authority vs execution playbook.** The *why* — how an effect factors as `Motion ∘ Mapping`,
> why temporal easing is the Responsiveness↔Grace resolution, and the measured attack/release
> constants — is the **canonical design method**: `docs/architecture/effect-decomposition/00-the-method.md`
> (esp. §4.1) and the per-class docs. THIS doc is the **execution playbook**: how to port/build/flash/
> validate that design into the fork without repeating the 2026-07-11 failures. When they overlap on
> easing, the-method is authoritative on *why*; this canon is authoritative on *how to ship it*.

## Prime law (why this doc exists)

**Faithful reproduction is the FLOOR, not the ceiling.** A technically-accurate import of a firmware-v3 effect that looks amateur on the K1 LGP is a **failure**, not a deliverable. The 2026-07-11 session proved this three times (see §7). Every failure was a faithful algorithm missing a *craft/context* layer. If you only reproduce the source, you have not done the job.

---

## 1. MANDATORY temporal easing — the professional "decay" layer (the #1 lesson)

**The failure:** ported effects wrote raw/instantaneous audio energy straight to brightness. Result: they lit the instant the drive rose and went **dark the instant it fell** — "stuttering / on-off," rejected by Captain as *"extremely jarring… amateur and unprofessional."* This is `EFFECT_DEVELOPMENT_STANDARD.md` anti-pattern §7.1 ("Raw Audio Driving Pixels Directly → seizure-inducing flicker"). Every **native** effect Captain likes avoids it. A port MUST too.

**The rules (all required for any audio-reactive effect):**

1. **Never write a raw audio value to brightness.** Every audio drive (rms, onset, chroma, band energy, beat_strength) passes through an **asymmetric one-pole follower** first: **fast attack, slow release.** Use `k1ease::follow(cur, target, dt, attack_tau, release_tau)` from `visual/easing.h`.
2. **Release ≥ 5× attack.** Attack ~0.03–0.05 s; release ~0.28–0.5 s. Native constants (copy these — they come from effects Captain already likes):

   | Use | attack | release |
   |---|---|---|
   | Beat / percussion | 0.02–0.05 s | 0.15–0.30 s |
   | Bass breathing | 0.05–0.10 s | 0.30–0.50 s |
   | Ambient / colour | 0.10–0.25 s | 0.50–1.50 s |
   | (native exemplars) | prism 0.035/0.32 · snapwave 0.05/0.28 · wfhyb 0.02/0.50 · moire 0.05/0.35 |

3. **Trail persistence / life decay.** A trigger must leave a *fading* object, never a pixel that vanishes next frame. Fade the previous frame every frame (`k1ease::decay(value, dt, tau)` or `pow(persistence, dt*60)`), and/or decay particle/ring life `*= expf(-k*dt)`.
4. **Smoothed silence gate — never `snap.silence ? 0`.** Ramp the boolean through a follower (`k1ease::follow(sil, snap.silence?0:1, dt, 0.05f, 0.30f)`) and multiply output by it → soft ~300 ms fade-to-dark. A hard `if(silence) 0` is allowed **only** for strictly event-gated effects with no continuous bed (e.g. percussion_burst).
5. **Brightness floor — never approach zero on the off-phase.** `mod = 0.4f + 0.6f * env` (STANDARD §4.4). Do not multiply the whole field by a raw beat value 0→1.
6. **STROBE LAW (fork-authoritative, strictest):** prefer routing reactivity to **spatial/transport** — position, phase, palette-shift, migration speed — not global brightness. Any hard global-brightness jump on audio is a rejectable strobe. When brightness *is* used, it must be eased + floored per above.
7. **dt-normalised, clamped `[0.001, 0.05]`.** Use `k1ease::safe_dt(millis(), fx.<prefix>_last_ms)`. Never frame-count (`counter++`) for a rate.
8. **Do not double-smooth pre-smoothed inputs.** Already smoothed: `peak_scaled`, band energies (`low/mid/high_energy`), onset `*_level`, `beat_strength`/EsBeatClock. **Instantaneous — you MUST smooth:** `vu_level`, `novelty`, `chroma_strength`, onset `*_strength`, raw `chromagram_smooth[]` bins.
9. **Use `visual/easing.h`.** There were 8+ duplicate private followers before this session; do not add a 9th — call `k1ease::follow/ema/decay/peak_follow/safe_dt`.

---

## 2. Per-frame perf discipline — the 2.0 ms ceiling (the second lesson)

**The failure:** two ports blew the ceiling (Bloom **3.9 ms**, Moiré **2.2 ms**). Cause was always **calling an expensive helper per-LED**.

1. **Colour is frame-constant if it depends on field/ring POSITION, not per-LED brightness → sample it ONCE per frame and scale per-LED.** (Bloom's centre-ring colour, Moiré's field colour, Beat Pulse's body colour are all frame-constant.)
2. **NEVER call these inside a per-LED loop:**
   - `effect_particle_colour()` — recomputes `chromagram_centroid_hue()` (12-term trig) on **every** call → ~960 trig ops/frame at 80 LEDs.
   - `palette_manual_colour()` — a ≤48-stop HD scan, ~30 µs/call.
   - `effect_palette_or_chroma_colour()` — ~35 µs/call; **this is the chromatic-mode hot path** (bench runs chromatic → the LUT-only fix did nothing until this was hoisted).
   Hoist the centroid/palette/chroma-base ONCE; for genuine per-LED hue variation build a small hue **LUT** (≤16 stops) once per frame and lerp+scale per-LED.
3. **`powf` per-LED → replace** with `x*x`/`x*x*x` or once-per-frame blend weights. **`sinf` per-LED → incremental angle-addition recurrence** (seed sin/cos, rotate one step per LED). Moiré went 160 sinf + 80 powf → **8 trig seeds/frame** this way with identical output.
4. **render_us is DATA-DEPENDENT** — it scales with lit-pixel count and palette-vs-chromatic mode. **Measure at full illumination**, not a quiet room; the quiet-room number lies low.
5. **How to measure:** `:vp_stream=on`, read `render_us` from the `[VP]` telemetry line. Ceiling **2000 µs**.

---

## 3. Fork idiom (the mechanics — build to the REAL signature)

- Signature: `void light_mode_<name>(CRGB16* leds_prev_buffer, ChannelEffectState& fx)`.
- Buffer: global `CRGB16 leds_16[NATIVE_RESOLUTION]` (==160). `HALF=80`. Author the **upper half** `[HALF,160)`, zero the lower half, then `finalize_additive_frame(leds_16, leds_prev_buffer, store_history)` and `if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16)`. Centre = index 80, edge = index 159; `dist = index-80`, `dist01 = (dist+0.5)/HALF`.
- Context: `const RenderParams* rp = active_render_params(); const bool render_secondary = vp_render_secondary_channel;`
- Colour: `effect_particle_colour(rp, render_secondary, hue01, SQ15x16(bright))` — palette-bounded + chroma-anchored (base = `chromagram_centroid_hue()`), inherently no-rainbow. **Hoist per §2.** Freeze any free-running `gHue`.
- Audio (value-copy, spinlock-safe): `k1_audio_snapshot_read()`, `k1_onset_beat_read()`, `k1_tempo_read()`; global `SQ15x16 chromagram_smooth[12]`. Only 3 octave bands exist (`low/mid/high_energy`), not 8.
- No heap/`new`/`malloc`/`String` in render; static/.bss only; buffers >64 B → `EXT_RAM_BSS_ATTR` (PSRAM), never internal DRAM. Small per-frame stack temps (e.g. a 16-entry hue LUT) are fine.

### Wiring touchpoints — ALL required (miss one and the build or a static gate fails)
1. `system/config_types.h` — append enum before `NUM_MODES` (append-only, never reorder — IDs are persisted).
2. `visual/channel_effect_state.h` — add per-channel state fields (`<prefix>_last_ms` + envelope `<prefix>_*_env`); zero-init is canonical.
3. `visual/lightshow_modes.h` — forward declaration.
4. `SPECTRASYNQ_K1_FIRMWARE.ino` — dispatch arm in `dispatch_legacy_lightshow()`.
5. `system/system.h` — `set_mode_name(N, "NAME")`.
6. **Probe coverage** (`visual/lightshow_modes.h`): a `mode == LIGHT_MODE_X` arm in `vp_probe_dispatch_and_hash` **and** a `vp_probe_print_mode(LIGHT_MODE_X)` line — **enforced by `tests/test_vp_probe_mode_coverage_static.py`**.

---

## 4. Build / flash / validate

- **Env:** `k1_bench_im73d`. **MAC-verify before ANY flash:** bench = `B4:3A:45:A5:89:B4` (`usbmodem1401`); main = `B4:3A:45:A5:87:F8` (`usbmodem12401`) — **DO NOT flash the main unit.**
- **Flash:** `pio run -e k1_bench_im73d -t upload --upload-port <port>`; confirm **`Hash of data verified`** + **`Hard resetting`** (silent-skip guard — exit 0 without these = not flashed).
- **Serial:** baud **230400**. Commands are **`:cmd=val\n`** (colon + equals). `set_mode 30` (space) is eaten **character-by-character as single-char hotkeys** — use **`:set_mode=31`**. Enable telemetry with `:vp_stream=on`. Opening the CDC port **resets the board** (reverts to the persisted boot mode). Telemetry floods the line — grep the exact ACK string.
- **Validate:** no-panic soak + `render_us < 2000 µs`. The **visual A/B is Captain's** — audio-playback-safety bars the agent from playing music, and go-dark blanks the plate in silence, so an agent literally cannot see an audio-reactive effect. Agent proves: builds, flashes, boots clean, selects, no crash, under budget. Captain judges the look.
- **Commit only after Captain hardware sign-off.** Never before.

---

## 5. Tooling frictions (do not relearn these)

- **clangd is NOT wired for the fork.** It emits constant false positives (`SFixed constexpr non-literal`, `CRGB16 no viable '='`, `hal.h not found`, Xtensa `-mlongcalls`). **Ignore clangd for the fork — the `pio` build is the only truth.** Navigate with `rg` + Read.
- **RTK corrupts `grep` stdout.** Read the file, or redirect `grep` to a file then Read it.
- **Cursor holds the serial port.** Its serial monitor auto-reconnects after each flash-reset and blocks esptool (`lsof | grep usbmodem` shows the `Cursor` PID on `tty.usbmodem1401`). The agent must NOT kill the editor — ask Captain to close the monitor and keep it closed during a flash/validate loop.
- **Native TDD for pure math:** extract dependency-free float maths into a header and host-compile a test (`clang++ -std=c++17`), red→green, independent of SQ15x16/Arduino (see `effects/beat_pulse_math.h` + `tests/native/test_beat_pulse_math.cpp`).

---

## 6. Orchestration pattern that worked

- **Parallel port agents:** each extracts ONE effect's faithful algorithm from the real firmware-v3 source and writes ONE self-contained `light_mode_<name>.cpp` (new distinct file → no write conflict) and returns a wiring spec. The **orchestrator owns all shared-file wiring + the single build** (agents never edit the enum/.ino/state-struct or build). `SendMessage` resumes an agent (context intact) for fixes.
- **Waves, not all-at-once.** Land a small *validated + eased* slate for Captain A/B before mass-producing — the port hit-rate is low enough that validating the approach first saves whole batches.

---

## 7. Anti-pattern catalogue — this session's actual failures (the evidence)

| # | What happened | Root cause | The rule it teaches |
|---|---|---|---|
| 1 | Beat Pulse (0x1404) faithfully ported → *"100% dogshit, worst effect ever"* | (a) a *good*-tier effect chosen as a harness test, not a flagship; (b) purely **beat-gated** → robotic on/off, no continuous bed | Pick by TIER from Captain's proven shortlist; beat-gating alone reads amateur — favour continuous-audio effects (§1) |
| 2 | Bloom 3.9 ms / Moiré 2.2 ms — over the ceiling | heavy colour/`powf`/`sinf` called **per-LED**; cost is data-dependent so a quiet-room measurement hid it | §2 — sample colour once/frame; measure at full illumination |
| 3 | All ports *"stuttering / on-off, jarring, amateur"* | **raw audio → brightness, no asymmetric release easing**; skipped `EFFECT_DEVELOPMENT_STANDARD.md` | §1 — the mandatory easing layer. **This is the big one.** |
| 4 | Stale first-contact handover (`origin/main @ accc5f0`, mission "port a gem") | the fork had advanced to a multi-lane launch push; handover reflected a past moment | Verify `git` state (branch/HEAD) before acting on any handover |

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:claude-opus-4-8 | Created — canonised the 2026-07-11 gem-port session's craft lessons (mandatory easing, per-LED perf, fork idiom + workflow, tooling frictions, anti-pattern catalogue) so no future agent repeats them. |
