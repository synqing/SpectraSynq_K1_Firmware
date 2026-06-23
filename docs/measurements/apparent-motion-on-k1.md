---
abstract: "Protocol + instrument + (to-be-filled) results for characterising the apparent-motion perceptual envelope of the K1 LED substrate (160px, centre-mirrored, diffusing light-guide). Measures the motion↔blink fusion threshold (single stepping point) and the one-object↔two-flashes correspondence limit (two-flash phi/beta), as seen through the mandatory diffusing LGP (the only condition the K1 is ever experienced in). The question is a timing×spacing relationship, NOT max frame rate. Instrument: the non-shipping compile-gated motion-probe harness (env k1_motion_probe; serial mp_step/mp_flash/mp_off/mp_status). Findings labelled [FACT] (measured on-device) / [INFERENCE] / [HYPOTHESIS]. Read before tuning any motion effect (incl. beat-phase-lock) — this is the empirical envelope the Motion layer must live within. MEASURED on-device 2026-06-02 (flashed to 2nd-bench K1 / usbmodem1401, single observer): fusion is an inter-step INTERVAL threshold ≈36–60 ms (timing, not px/s); correspondence limit ≈28–32 px; fused-motion ISI window ~50–90 ms. Verdict — current per-frame effects are NOT constrained (they step every ~5.4 ms, deep in the smooth regime); the binding constraint is that beat-phase-lock must modulate CONTINUOUS scroll velocity, NOT jump per beat (a ~500 ms beat-jump reads as a blink)."
---

# Apparent-Motion Thresholds on the K1 Substrate — Protocol & Findings

*Measurement study · captured 2026-06-02 (branch feat/gdft-harness @ f67054d) · instrument compile-verified; on-device data PENDING*

> **The question (precise).** Not "what is the max frame rate." It is the **perceptual
> boundary between motion and blinking** — a *timing × spacing* relationship. When do
> discrete, separated illuminations **fuse** into one moving object (phi/beta), and when do
> they read as separate blinks? This is the empirical envelope the **Motion layer**
> ([effect-decomposition/00-the-method.md §1](../architecture/effect-decomposition/00-the-method.md))
> must operate within on *this* substrate. Beat-phase-lock and every future motion effect
> consume the result.

**Operating discipline:** every claim is labelled **[FACT]** (measured on-device),
**[INFERENCE]** (derived from code/arithmetic), or **[HYPOTHESIS]** (from the literature /
prediction, unmeasured). British English throughout.

---

## 1 · The instrument (built, compile-verified, non-shipping)

A compile-gated test harness — **not** a roster mode, **not** shipping firmware (Developer
Instrumentation Boundary). [FACT]

- **Build env:** `[env:k1_motion_probe]` (extends `k1_hardware`, adds `-DENABLE_MOTION_PROBE=1`).
  Absent from `k1_hardware` / `k1_bench_reference` production builds. [FACT]
- **Compile-verified:** `pio run -e k1_motion_probe` → SUCCESS, RAM 25.7% / Flash 9.0%, 2026-06-02. [FACT]
- **Files:** new `motion_probe.h` (inline, gdft_harness pattern) + gated callers in
  `serial_menu.h`, `SPECTRASYNQ_K1_FIRMWARE.ino` (one `led_thread` branch), `led_utilities.h`
  (silent_scale pin). No `light_mode_*.cpp` touched. [FACT]

**Serial commands** (USB-CDC, typed `:cmd=data`):

| Command | Effect | Reports (ACHIEVED, measured) |
|---|---|---|
| `mp_step=interval_ms,size_px[,lum]` | A single point jumps `size_px` every `interval_ms`, wrapping the 160px strip (dt-clamped, wall-clock-stable). | `achieved_interval_ms`, `eff_pps` (=size/interval), `pos` |
| `mp_flash=a_px,b_px,gap_ms,lum,on_ms` | Two-flash phi/beta: light A for `on_ms`, dark `gap_ms` (the ISI), light B for `on_ms`, dark `gap_ms`, loop. | `achieved_gap_ms`, `on_ms`, `achieved_cycle_ms`, `sep_px` (=\|b−a\|) |
| `mp_off` | Stop, restore CONFIG, resume normal render. | — |
| `mp_status` | Probe state + params + measured `led_fps` + `frame_ms`. | — |

Parameters are **live-adjustable** — re-issue a command mid-run to sweep without restarting. [FACT]

**Confounds neutralised on arm, restored on `mp_off`** [FACT] — *this is what makes the
measurement valid* (map↔territory: the stimulus you present = what the strip emits):

1. `CONFIG.TEMPORAL_DITHERING = false` — else the 4-step Bayer dither ghosts a flash across ≤4 frames.
2. `CONFIG.INCANDESCENT_MODE = false`, `INCANDESCENT_FILTER = 0` — else output is colour-shifted.
3. `silent_scale` pinned `= 1.0` in `apply_brightness` — **else brightness depends on room noise** (the mic), contaminating luminance (a governing variable).
4. `CONFIG.PHOTONS = 1.0`; the probe draws **un-mirrored** across the full 160px regardless of `MIRROR_ENABLED`.

**Residual instrument caveats** [INFERENCE]:
- Output gamma (`apply_gamma8`) still applies → commanded `lum` (0–255) is monotonic but **not photometrically linear**. Adequate for threshold *bracketing*; report commanded `lum`, not cd/m².
- Pixel **pitch** and the LGP's optical magnification are physical quantities not in code → spatial separation is commanded/measured in **pixels**; angular/physical separation is a **Captain/hardware measurement** (LGP truth). [HYPOTHESIS until measured]

---

## 2 · Substrate facts that bound the experiment

| # | Fact | Label | Source |
|---|---|---|---|
| 2.1 | Render loop is **uncapped / runtime-variable** (`led_thread` `vTaskDelay(1)`, no FPS target); paced by `FastLED.show()`. | [FACT] | `SPECTRASYNQ_K1_FIRMWARE.ino` led_thread |
| 2.2 | Observed rate ~**185 FPS** on K1 → frame period ≈ **5.4 ms**. | [FACT] code comment / [INFERENCE] ms | `light_mode_waveform_fast.cpp:9` |
| 2.3 | Stimuli can only change on a rendered frame → **finest ISI ≈ one frame ≈ 5.4 ms**, and it *jitters* with render load. | [INFERENCE] | 2.1+2.2 |
| 2.4 | ∴ the harness reports **achieved** (measured-millis) timing, never just requested. | [FACT] (design) | `motion_probe.h` |

**Doability verdict [INFERENCE]:** the ~5.4 ms granularity is **finer than the perceptual
thresholds it targets** (apparent-motion windows are tens of ms — see §3), so the substrate
can bracket them. Limitation: ISI is quantised to ~5.4 ms and the rate jitters; mitigated by
reporting achieved timing and averaging.

---

## 3 · Predictions (so we know what we're looking for)

**Literature priors [HYPOTHESIS]:**
- Beta (optimal) apparent motion between two flashes peaks around **ISI ≈ 30–200 ms**; below
  ~30 ms → simultaneity/flicker; above ~200 ms → succession (two separate flashes).
- **Korte's laws [HYPOTHESIS]:** to keep the percept of motion, required ISI rises with
  spatial separation and with luminance — so the correspondence limit is a *surface*, not a
  single number.
- A continuously stepping point reads as **smooth** when steps are small+frequent and
  **strobes/blinks** when steps are large+infrequent.

**Substrate-specific predictions [INFERENCE/HYPOTHESIS]:**
- [INFERENCE] ISIs from ~5 ms upward in ~5 ms increments are presentable → the 30–200 ms
  window is well-resolved.
- [HYPOTHESIS] Single point: fusion (smooth) likely holds for small steps (1–3 px) at short
  intervals (~5–20 ms); expect the **blink transition** as interval grows past tens of ms
  and/or step size grows past a few px.
- [HYPOTHESIS] **The LGP's bloom is baked into every threshold.** The diffuser optically
  overlaps adjacent pixels, bridging the dark gap between A and B → it should *raise* the A–B
  separation at which motion still fuses (vs a hypothetical bare strip). The LGP is
  **mandatory** (the K1 is never run without it), so there is no bare-strip condition to
  compare — every measured threshold already includes the bloom, which is correct because it
  is the only state the product exists in.

---

## 4 · Sweep protocol

Pre-flight each session: `mp_status` (confirm `led_fps`/`frame_ms`), set a fixed viewing
distance, ambient dark, fixed `lum` (e.g. 160) unless luminance is the variable. Record the
**achieved** values the harness prints, not the requested ones. Captain calls each percept.

### Experiment A — Single-point fusion threshold (motion ↔ travelling blink)
Hold `size_px` fixed; ramp `interval_ms` until the moving point stops reading as smooth motion
and starts reading as a travelling blink. Repeat per `size_px`.
- `size_px ∈ {1, 2, 4, 8}` · `interval_ms` swept (e.g. 5 → 120 in ~5–10 ms steps).
- Record the fusion→blink `achieved_interval_ms` (and `eff_pps`) per `size_px`.

### Experiment B — Two-flash correspondence limit (one object ↔ two flashes)
- **B1 (separation sweep):** fix `gap_ms` at the beta optimum found viable (~50 ms start),
  `on_ms ≈ 30`, sweep `sep_px` (`a=80`, `b=80+sep`) `∈ {2,4,8,16,32}` → find the separation at
  which "one object moving" becomes "two separate flashes".
- **B2 (ISI sweep):** fix a mid `sep_px`, sweep `gap_ms` (10 → 250) → find the lower
  (flicker/simultaneity) and upper (succession) ISI bounds of fused motion.

### Experiment C — Light-guide (RESOLVED: mandatory, guide-on only)
The LGP is a **mandatory operational requirement** — the K1 is never experienced without it
(Captain, 2026-06-02). There is therefore **no bare-strip condition**; Experiments A and B are
*already* the guide-on measurements and need no repeat. The bloom is baked into every
threshold — which is the correct product truth. (Resolves the original brief's conditional:
guide not removable → guide-on only.)

### 4b · Observation runbook (exact commands — 6 boundary readings)

**Flash (Captain, target-verified):**
`script -q /tmp/mp.log pio run -e k1_motion_probe -t upload --upload-port <verified-port>` →
confirm the `k1_upload_guard` MAC line + `Hash of data verified`. Open serial @115200.
(Disconnect Cursor's monitor on that port first; Errno 35 = busy.)

**Orient:** `mp_status` (expect `led_fps`~185, `frame_ms`~5.4) → `mp_step=16,2` — a single dot
steps along the strip; confirm its brightness does **not** drift as the room stays quiet (the
harness pins it — see §1 confound 3).

**A — fusion threshold (smooth ↔ travelling-blink): 3 readings.**
*Judgment each trial:* ONE continuous object gliding, **or** a dot TELEPORTING/strobing between
positions? Per step size, raise the interval until it flips to blink; record the printed
`achieved_interval_ms` at the flip.
- size 1: `mp_step=8,1` → `12,1` → `16,1` → `24,1` → `32,1` → `48,1`
- size 4: `mp_step=8,4` → `12,4` → `16,4` → `24,4` → `32,4` → `48,4`
- size 8: `mp_step=8,8` → `12,8` → `16,8` → `24,8` → `32,8` → `48,8`

**B1 — correspondence limit (one object ↔ two flashes): 1 reading.** `gap=50`, `on=30`, A=80.
*Judgment:* ONE light JUMPING between two spots, **or** TWO lights BLINKING separately? Grow B
outward; record the `sep_px` at the flip to "two flashes".
- `mp_flash=80,84,50,160,30` → `80,88,50,160,30` → `80,96,50,160,30` → `80,112,50,160,30` → `80,144,50,160,30`

**B2 — ISI bounds of fused motion: 2 readings.** Fix separation at a value that read "one
object" in B1 (e.g. b=88). Vary `gap`; record the LOWER bound (both-on/flicker → motion) and
the UPPER bound (motion → two-separate-in-succession).
- lower: `mp_flash=80,88,10,160,30` → raise gap `15,20,30…` until it becomes clean single motion.
- upper: keep raising gap `80,120,180,250…` until motion breaks into two separate flashes.

**Done:** `mp_off` (restores normal rendering). *Optional, not required:* repeat A at `lum=40`
(`mp_step=16,2,40`) to probe luminance dependence (Korte's law).

---

## 5 · Results — parameter → perception table (TO FILL on-device)

> Empty pending Captain observation. Fill the **Perception** + **Achieved** columns from the
> serial readout and label each row **[FACT]**. Until filled, thresholds remain [HYPOTHESIS].

**A — fusion threshold (single point):**

| size_px | requested interval_ms | achieved_interval_ms | eff_pps (at boundary) | Perception @ boundary | Label |
|---|---|---|---|---|---|
| 1 | 36 | 35–40 (~38) | ~26 | smooth→blink flip | [FACT] |
| 2 | 56–60 | ~60 | ~33 | smooth→blink flip | [FACT] |
| 4 | 40–44 | 40–46 (~43) | ~87–100 | smooth→blink flip | [FACT] |
| 8 | — | — | — | not run (cycle used 1/2/4) | — |

**Reading:** the *interval* at the flip is ~38/60/43 ms across sizes (noisy, single observer) — i.e. fusion is governed by **inter-step interval ≈ 36–60 ms**, not px/s. eff_pps at the boundary rises with step size only because more pixels are covered per (constant) interval. Achieved jitters ±~5 ms off requested = the predicted one-frame quantisation. [FACT]

**B1 — correspondence limit (separation), gap ≈ 54 ms (achieved), on 30 ms:**

| sep_px | gap_ms (achieved) | Perception (one-moving / two-flashes) | Label |
|---|---|---|---|
| ≤ ~24 | ~54 | one moving object | [INFERENCE] (ramped through; held as one) |
| 28 | 54 | at/near flip | [FACT] |
| 32 | 54 | two flashes | [FACT] |

**Correspondence limit ≈ 28–32 px** at ~54 ms ISI: below ~28 px the two flashes fuse into one moving object; beyond ~32 px they read as two separate flashes. [FACT]

**B2 — ISI bounds of fused motion:**

| sep_px | gap_ms (achieved) | Perception | Label |
|---|---|---|---|
| 14–18 | 50 | one moving object (lower bound NOT pushed below 50) | [FACT] |
| 2 | 80 | still motion | [FACT] |
| 2 | 90 | breaks → two-in-succession | [FACT] |

**Upper ISI bound ≈ 80–90 ms** (fused motion → succession). **Lower bound ≤ 50 ms** — still fused at 50 ms; not driven lower this session (gap floor not explored). Note: separation drifted between rows (18 → 2 px), so the upper bound is at small separation; a clean re-run would fix separation across the gap sweep. [FACT, with protocol-drift caveat]

**C — light-guide:** removed — LGP mandatory, no bare-strip condition (§4 Experiment C).
Tables A/B are guide-on by definition.

---

## 6 · Blockers & handoff

- **[RESOLVED]** Light-guide removability: the LGP is a **mandatory** operational requirement
  (Captain, 2026-06-02) — never removed. No bare-strip condition; all measurements are guide-on.
- **[HANDOFF — flash + observe]** Flashing requires device-identity verification (port + USB
  MAC/chip-id; hardware-target discipline) — not auto-done. Suggested:
  `script -q /tmp/mp.log pio run -e k1_motion_probe -t upload --upload-port <verified-port>`
  then confirm `Hash of data verified` + the k1_upload_guard MAC line. (Cursor's serial monitor
  may hold the port → disconnect it first; Errno 35 = port busy.)
- **[Captain]** The measurement itself (calling each percept) is yours; I provide the instrument
  + protocol + the table to fill.

---

## 7 · Decision rule (pre-registered — does this constrain effect design?)

After the table is filled, apply this rule so the conclusion isn't post-hoc:

- Compare the measured fusion threshold (`eff_pps` / `interval_ms`) against the **live effects'
  actual scroll rates** — e.g. Waveform ≈ 1 px/frame ≈ **~185 px/s** [INFERENCE], Spectrum
  River drift ≈ 0.55 px/frame ≈ **~100 px/s** [INFERENCE].
- **Constrains design** if the fusion→blink boundary falls **within** the px/s range real
  effects use (i.e. some effects can cross into "blink" territory) → then motion effects
  (incl. beat-phase-locked scroll) have a *speed/step ceiling* to respect, and the
  light-guide Δ tells us how much spatial-separation headroom the diffuser buys.
- **Negligible** if the boundary sits far outside any plausible effect parameter → note it and
  move on.

Expected payoff sentence to complete: *"Scroll faster than **X px/s** (or step larger than
**N px** at **interval Y ms**) and motion stops fusing; the light-guide extends the fusion
separation by ~**Z px** versus the bare strip."* — fill X/N/Y/Z from §5.

---

## 8 · Findings & verdict (measured 2026-06-02, single observer)

**Headline.** The motion↔blink boundary on the K1 substrate is an **inter-step interval
threshold ≈ 36–60 ms** (re-step ~17–28×/s) — **not** a px/s figure. A point covering more
pixels per step crosses into "blink" at roughly the same *interval*, just at a higher px/s.
This confirms the governing variable is **timing, not speed**. [FACT → INFERENCE]

**Measured thresholds [FACT]:**
- Fusion (smooth motion): inter-step interval ≲ ~40–60 ms; eff_pps at the boundary 26 (1 px) → 91 (4 px).
- Correspondence (one object vs two): ≈ **28–32 px** separation at ~54 ms ISI.
- Fused-motion ISI window: ≤ 50 ms (lower; still fused, not pushed lower) up to ~**80–90 ms** (upper; breaks to succession).

**Decision-rule verdict — does this constrain effect design?**
- **Current effects: NOT constrained.** They scroll ~1 px (or sub-px) **every frame** (~5.4 ms
  interval ≈ 185 re-steps/s) — 7–11× faster than the ~40–60 ms fusion floor, i.e. deep in the
  smooth regime. Waveform (~185 px/s) and Spectrum River (~100 px/s) fuse because their step is
  small **and** frequent, not because of their px/s. [INFERENCE]
- **The binding constraint is on beat-phase-lock (task a).** A *naïve* beat-lock — jump the
  trace forward on each `beat_tick` — spaces its steps ~500 ms apart at 120 BPM, **~10× past the
  fusion threshold** → it will read as a discrete **teleport/blink on every beat, not motion.**
  [INFERENCE, high-confidence from the measured ISI threshold] **∴ beat-phase-lock must modulate
  the *continuous per-frame scroll velocity* (tempo-locked rate, still stepping every frame), NOT
  advance in per-beat jumps.** Correct design: keep the Transport engine stepping every frame
  (≤~5 ms) and let beat-phase set the *rate* (e.g. the river travels one strip-length per bar) —
  smoothness preserved, tempo expressed.
- **Discrete/particle effects (Comet):** two onsets within ~28–32 px **and** ~50–90 ms will fuse
  into apparent motion rather than read as two events — relevant if closely-spaced kicks spawn
  nearby comets. [INFERENCE]

**The payoff sentence:** *"Re-step within ~40–60 ms (≥~20 updates/s) and motion fuses; spaced
longer it reads as a travelling blink regardless of px/s. Two flashes fuse into one moving object
only when ≲30 px apart and within a ~50–90 ms ISI window. The current per-frame effects sit deep
in the smooth regime (unconstrained); the live constraint is that beat-phase-lock must modulate
continuous scroll velocity, not jump per beat."*

**Quality caveats (map↔territory):** single observer, single session; 3 step sizes (1/2/4, not
1/4/8); B2 separation drifted between rows (18→2 px); lower ISI bound not explored. The robust
conclusions (interval-not-speed; the ~40–60 ms fusion floor; the beat-jump-blinks implication)
hold despite the noise. A tighter re-run (fixed separation across the gap sweep, push the lower
ISI bound, add size 8) would sharpen the numbers but is unlikely to change the design verdict.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-02 | agent:claude-opus | Created — protocol + instrument record + predictions + empty results table + decision rule for the K1 apparent-motion characterisation. Instrument (k1_motion_probe harness) compile-verified; on-device data pending Captain observation. Confounds (frame-quantised/variable timing, audio-dependent brightness, temporal dither, incandescent) identified and neutralised in the harness. |
| 2026-06-02 | agent:claude-opus | LGP correction (Captain): light-guide is a mandatory operational requirement → no bare-strip condition. Removed Experiment C guide-off + the removability blocker; reframed bloom as baked into every guide-on threshold. Added §4b observation runbook (exact serial commands, 6 boundary readings). |
| 2026-06-02 | agent:claude-opus + captain (observer) | MEASURED on-device (harness flashed to usbmodem1401, guard-verified). Filled §5 tables A/B1/B2 [FACT] + wrote §8 findings/verdict. Key result: fusion is an inter-step INTERVAL threshold (~36–60 ms), not px/s; correspondence ≈28–32 px; ISI window ~50–90 ms. Verdict: current per-frame effects unconstrained; beat-phase-lock must modulate continuous scroll velocity (not per-beat jumps) or it blinks. |
