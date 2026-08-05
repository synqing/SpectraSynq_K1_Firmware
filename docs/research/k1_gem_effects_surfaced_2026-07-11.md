---
abstract: "Captain's hand-rated GEM effects surfaced from the Lightwave-Ledstrip firmware-v3 shortlist, described faithfully by their REAL render math and — the axis Captain cares about — how light MOVES across the plate. For each: exact per-frame transport, fork-port plan (files, fork ControlBus signals, effort, risks), and missing-input caveats. Ground-truthed against firmware-v3/src/effects/ieffect on 2026-07-11 (scroll rate 150, wave-eqn leapfrog, phase-flip u=1-v, PSRAM history all confirmed). Read when planning which proven effects to port to the SPECTRASYNQ_K1_FIRMWARE fork first. Crown jewels: 0x1313 Waveform Hybrid, 0x1B06 Time-Reversal Mirror Mod1, 0x1309 Bloom BassTreble."
---

# K1 Gem Effects — Surfaced from the Lightwave-Ledstrip Shortlist

**Development target:** the K1 fork at `/Users/spectrasynq/SpectraSynq_K1_Firmware/SPECTRASYNQ_K1_FIRMWARE` — Sensory-Bridge-derived, single `.ino`, plain functions writing `CRGB16 leds_16[NATIVE_RESOLUTION]`, centre-origin (content at LED 79/80, mirrored outward), no heap in render, static buffers, dual-strip 320 LED (2×160). **No** IEffect class system, **no** PatternRegistry, **no** actor model.

**Source read (READ-ONLY):** `Lightwave-Ledstrip/firmware-v3/src/effects/ieffect/` (+ `sensorybridge_reference/`, `esv11_reference/`). ID→name map: `firmware-v3/src/config/effect_ids.h`.

**Fork ControlBus signals available:** `rms`, `bands[0..7]`, `chroma[0..11]`, `beat`, `onset`, `tempo`/BPM+phase, percussion (`kick`/`snare`/`hihat`), `chord`. firmware-v3 effects may use richer inputs (64-bin spectrogram, saliency, novelty, musical-grid beat-in-bar) — flagged per card where a port needs an input the fork lacks.

**Ground-truth note (2026-07-11):** the deep-dive math below was spot-verified against real render bodies. Confirmed directly in source: Waveform Hybrid `kBaseScrollRate=150.0f`, `decayRate = 0.8 + 3.5*absAmp`, `posF = halfLen + amp*halfLen`, sub-pixel additive split; Time-Reversal leapfrog wave equation, forward/reverse phase machine, `u_curr[i] = 1.0f - snap[i]; // Phase flip`, and the `heap_caps_malloc(..., MALLOC_CAP_SPIRAM)` PSRAM history allocation. The remaining cards are transcribed from the faithful shortlist extraction and carry the same provenance.

---

## 1. Executive summary — port these first

**MOTION is the axis.** Every card below is rated on *how luminous energy travels across the plate over frames*, not on a static look. These are the PROVEN, known-good effects — the gems.

### Crown jewels (surface always — all portable)

| # | ID | Name | Effort | One-line MOTION |
|---|----|------|--------|-----------------|
| 1 | `0x1313` | K1 Waveform Hybrid | MEDIUM | A bright sub-pixel dot bounces along the radius (distance = amplitude) trailing an exponentially-fading wake that scrolls outward; colour = a heavily-EMA'd 12-note chroma sum. |
| 2 | `0x1B06` | LGP Time-Reversal Mirror Mod1 | MEDIUM | A real damped wave propagates outward from centre for ~6 s while every frame is recorded — then the recording is replayed **backwards** with sub-frame interpolation **and phase-inverted (u = 1 − v)**. The crown-jewel time-machine. |
| 3 | `0x1309` | K1 Bloom BassTreble | EASY | Bass sets how bright the centre pixel is born; treble sets how fast that greyscale bloom flees outward (1 vs 2 px/frame); a √-warp accelerates content as it leaves centre. |

Mod1 is the single most distinctive motion in the entire corpus (recorded-forward → reverse-replay-with-phase-inversion) and the only true simulated-PDE with a time-machine rewind.

### Easiest wins for a first port sprint (near-zero input gaps — validate the fork port harness on these)

- **`0x1404` Beat Pulse (Resonant)** — scalar-only, zero buffers, no missing inputs. The only **inward** transport in the set (rings contract edge→centre).
- **`0x1A03` Bass Quake** — a true one-way projectile (`m_shockPos` integrates at fixed velocity centre→off-plate). No missing inputs.
- **`0x0E0A` Snapwave** — 1:1 port; `rms`, `chroma`, `timeMs` all native. Ring-buffer comet trail.
- **`0x1C08` Moire Cathedral** — stateless two-grating moire, no tempo dependency, 2 sinf + 1 powf per LED.

### The gem that does NOT translate

**`0x0E06` LGP Spectrum Detail Enhanced** is best-tier and gorgeous (64 independently-breathing frequency points, subpixel AA, backbeat wake) but is essentially **un-portable**: the fork has no 64-bin spectrum (only `bands[0..7]`) and no `musicalGrid.beat_in_bar`/`bar_phase01`. Degrading to 8 radial points loses the whole point. Deliberately NOT surfaced in the top 10 — keep only if the fork gains a real multi-bin spectrogram.

### Governance gate

**`0x1B04` Fresnel Caustic Sweep** is an EASY, distinctive scanning-beam port and would surface on merit — but claude-mem obs **#47095** records Captain **REVOKED** a prior `0x1B04` "GO" pending a design-survey protocol. Withheld from the top-10 pending that gate. **Flag before promoting.**

---

## 2. Motion-family clusters across the shortlist

The shortlist decomposes into ten distinct **transport classes** — the way to reason about ports is by family, because the fork-side machinery (buffers, envelopes, missing inputs) is shared within a family.

1. **Bouncing amplitude-dot + trail (waveform scope).** A single bright sub-pixel dot whose distance from centre is amplitude-mapped, leaving a scrolling or ring-buffer history trail. A scope, not a field — the transport is the dot's position plus its wake. — *0x1313 Waveform Hybrid, 0x0E0A Snapwave.*

2. **Centre-injected outward bloom advection (SB `light_mode_bloom` lineage).** Energy synthesised each frame and injected at the two centre pixels, then advected outward by a sub-pixel/integer scroll with high persistence (0.99/0.995 decay). Colour born at centre drifts to the edges, edge-faded, then mirrored. **Scroll speed is a mood/scene knob; audio only sets the centre injection.** — *0x1301 Bloom, 0x1309 Bloom BassTreble, 0x1307 Bloom Colour History, 0x130A Bloom Exponential, 0x1500 Bloom (Parity).*

3. **Frequency-anchored spectral scroll (streaming spectrogram).** Per-band/per-bin energy stamped at FIXED radial positions (bass near centre, treble toward edge), then the whole trail buffer scrolls outward as streaming history. Reads as a spatial spectrogram with comet tails. — *0x130E SB Spectral Envelope, 0x0E06 LGP Spectrum Detail Enhanced.*

4. **Simulated physical field (damped wave / reaction-diffusion PDE).** A genuine PDE integrated on an 80-cell half-strip — leapfrog damped wave, or Gray-Scott reaction-diffusion (proper name — `british-english-guard: ignore`). Motion is emergent centre-out propagation, never scripted. **Time-Reversal Mods add the crown-jewel twist:** record every forward frame into a ring buffer, replay backwards with sub-frame interpolation AND a phase-flip (u = 1 − v). — *0x1B06/07/08 Time-Reversal Mirror Mod1/2/3, 0x1701 LGP RD Triangle.*

5. **Contracting rings (edge → centre).** Every beat launches fronts that START at the plate edge and sweep INWARD, in fixed wall-clock ms (not audio-scaled). A pure closed-form time-function of the last beat timestamp — no trail buffer, deterministic. **The only family that travels inward.** — *0x1404 Beat Pulse (Resonant), 0x1405 Beat Pulse (Ripple).*

6. **Expanding shell / projectile (centre → edge) over a bed.** A beat or kick launches an outward-travelling ring/shell/front from centre over a centre-weighted glow bed. Either exponential-decay pulse (ring parks/fades) or a true constant-velocity projectile that runs off the plate. — *0x1200 Ripple (ES tuned), 0x1A03 Bass Quake, 0x1A07 Saliency Bloom, 0x1A01 Beat Prism, 0x1A08 Transient Lattice.*

7. **Migrating moire / interference lattice (no discrete front).** Two detuned spatial sines multiplied/subtracted into a low-frequency beat envelope; bright bands slowly migrate as the gratings drift in opposite phase directions. Standing-but-crawling shimmer — the motion IS the moire beat. — *0x1603 Moire Silk, 0x1606 Stress Glass, 0x1C08 Moire Cathedral, 0x0E03 Interference Scanner, 0x1A04 Treble Net.*

8. **Scanning beam sweep along the distance axis.** A single bright Gaussian focus sweeps along the centre-distance axis (sinusoidal or linearly-wrapping), surrounded by ring/halo/hash texture, with a specular pop on beat. — *0x1B04 Fresnel Caustic Sweep, 0x1607 Grating Scan.*

9. **Breathing / morphing standing radial figure.** A standing figure (rhodonea rose, Mach-diamond train, superposed harmonic tide) whose GEOMETRY is reshaped by audio — it opens/closes, changes petal count, compresses cell spacing. **Audio moves the structure itself, not merely its brightness.** — *0x1C0B Rose Bloom, 0x1C05 Mach Diamonds, 0x1A02 Harmonic Tide.*

10. **Tier2 "oscillating" phase-scroll + PLL travelling waves.** Free-run phase oscillator yanked by a PLL correction toward `beatPhase` under a Schmitt tempo lock — the source of the "oscillating uncontrollable" random direction reversals Captain flagged. — *0x0E08 Wave Collision, 0x0E07 Star Burst, 0x0E02 Chevron Waves.* (See §5.)

---

## 3. Ranked surfaced table

| Rank | ID | Name | Tier | Effort | MOTION (how light travels) |
|------|----|------|------|--------|----------------------------|
| 1 | `0x1313` | K1 Waveform Hybrid | best | MEDIUM | Amplitude-mapped bouncing dot + exponentially-fading wake scrolling outward at ~150·(speed/10) px/s; colour = 0.163 s-EMA'd 12-note chroma sum. |
| 2 | `0x1B06` | Time-Reversal Mirror Mod1 | best | MEDIUM | Damped wave propagates outward ~6 s (recorded every frame), then history replayed backwards with sub-frame interp + phase-flip (u = 1 − v). |
| 3 | `0x1309` | K1 Bloom BassTreble | best | EASY | Centre-injected greyscale bloom; bass = birth brightness, treble = scroll speed (1 vs 2 px/frame), √-warp accelerates content outward. |
| 4 | `0x1C08` | Moire Cathedral (5L-AR) | best | EASY | Two detuned gratings slide oppositely; moire "cathedral arch" ribs migrate outward/inward; mid shifts pitch, bass sharpens ribs. |
| 5 | `0x1C0B` | Rose Bloom (5L-AR) | best | MEDIUM | Rhodonea rose breathes open/closed via slow LFO; mid morphs petal count 3→7; bass = brightness; beat flashes petal edges. No lateral transport. |
| 6 | `0x1C05` | Mach Diamonds (5L-AR) | best | EASY-MED | Shock-diamond train marches outward while bass COMPRESSES cell spacing (thrust); treble/beat sharpen peaks; snare punches an accent. |
| 7 | `0x1404` | Beat Pulse (Resonant) | good | EASY | Two rings CONTRACT edge→centre on every beat — white 280 ms attack snap chased by a warm 480 ms Gaussian body. The only inward transport. |
| 8 | `0x130E` | SB Spectral Envelope | good | MEDIUM | 8 frequency-anchored dots (band 0 centre, band 7 edge) stamped at fixed positions, whole buffer scrolls outward ~200 px/s — streaming spatial spectrum. |
| 9 | `0x1A03` | LGP Bass Quake | good | EASY | Constant centre-pressure field + discrete outward shock rings — a true one-way projectile that launches on a heavy kick and runs off the edge. |
| 10 | `0x0E0A` | Snapwave | good | EASY | A chord-driven Lissajous dot bounces along the radius; a 40-entry ring buffer redraws recent positions as a quadratically-fading comet. |

---

## 4. Deep-dives — the top 5

### Rank 1 — `0x1313` K1 Waveform Hybrid  *(best · MEDIUM)*

**Source:** `firmware-v3/src/effects/ieffect/sensorybridge_reference/SbK1WaveformHybridEffect.cpp` (ID `EID_SB_K1_WAVEFORM_HYBRID = 0x1313`, effect_ids.h:259).

**What it really does.** This IS the reference waveform-scroll, but its *signature* is NOT the scroll — it is the **amplitude-mapped bouncing DOT** (louder = dot further from centre) plus a 0.163 s colour EMA that turns a noisy 12-note chroma sum into organic drift, plus an **audio-coupled fade** that tightens the wake on transients. The scroll is just the wake transport underneath a physical bouncing point.

**Exact per-frame transport** (Half = 80, centre 79/80; `trailBuffer[160]` float-RGB, `scrollAccum`, `dotColorSmooth`):

1. **Colour.** `dotColor = 0`; for c = 0..11: `b = chroma[c]²`; `b = min(b·1.5, 1)`; `dotColor += paletteColor(c/12, b·0.25)`. Then `dotColor *= min(brightness/255·1.30, 1)`. EMA `a = 1 − exp(−dt/0.163)`; `dotColorSmooth += (dotColor − dotColorSmooth)·a`; `dotColor = dotColorSmooth`; finally `*= confidence·silentScale` (sim: rms-gated hold envelope, else 1).
2. **Fade.** `absAmp = clamp(|wfPeakScaled|, 0, 1)`; `decayRate = 0.8 + 3.5·absAmp` (confirmed `kMinDecayRate=0.8f`, `kDecayScale=3.5f`; +10·(1−quietFactor) accel on real silence); `fade = exp(−decayRate·dt)`; `trailBuffer[i] *= fade` all i.
3. **Scroll.** `scrollAccum += 150·(max(speed,27)/10)·dt` (`kBaseScrollRate=150.0f` confirmed); `n = floor(scrollAccum)`; `scrollAccum −= n`; repeat n×: for i = 159..1 `trailBuffer[i] = trailBuffer[i−1]`; `trailBuffer[0] = 0`.
4. **Dot.** `amp = clamp(wfPeakLast·0.7/sensitivity, −1, 1)`; `posF = 80 + amp·80`; `pI = floor(posF)`; `f = posF − pI`; `trailBuffer[pI] += dotColor·(1−f)`; `trailBuffer[pI+1] += dotColor·f`.
5. **Mirror.** `trailBuffer[79−i] = trailBuffer[80+i]`, i = 0..79.
6. **Output.** `leds[0..159] = clip(trailBuffer)`; `leds[160..319] = leds[0..159]`.

**Waveform-peak simulation from rms:** envelope follower attack τ 0.007 / decay 0.100, subtract a noise floor (~750), normalise, then two-stage EMA τ 0.016 then 0.023 → `wfPeakLast`; `wfPeakScaled` = the normalised version.

**Fork port plan.** New plain function writing `leds_16[]`. **Effort MEDIUM.** The fork is SB-derived, so raw waveform samples for the peak envelope are almost certainly native — reimplement `updateWaveformPeak` exactly (max|wf|, 750 floor, follower τ 0.007/0.100, two-stage EMA). Colour needs `chroma[0..11]` (have it) + a palette lookup (substitute fixed HSV note colours if no palette). All static/PSRAM, no heap in render. British spelling already used.
- **RISK / missing input:** `audioConfidence` + `silentScale` are firmware-v3 ControlBus envelopes the fork lacks — synthesise a confidence/hold envelope from `rms`+`onset`, or drop the gates and gate on `rms` with a hold timer.

---

### Rank 2 — `0x1B06` LGP Time-Reversal Mirror Mod1  *(best · MEDIUM)*

**Source:** `firmware-v3/src/effects/ieffect/LGPTimeReversalMirrorEffect_AR.cpp` (ID `EID_LGP_TIME_REVERSAL_MIRROR_MOD1 = 0x1B06`, effect_ids.h:335). Confirmed in source: leapfrog wave equation, forward/reverse phase machine, `u_curr[i] = 1.0f - snap[i]; // Phase flip` (line ~392), `heap_caps_malloc(sizeof(PsramData), MALLOC_CAP_SPIRAM)`.

**What it really does.** The total opposite of a scroll. Forward is a genuine physics simulation — a **damped wave equation propagating outward** from centre with reflection and edge absorption. The reverse phase is **exact recorded-history replayed backwards and phase-inverted** — energy visibly runs in reverse toward centre, flipped. No buffer-shift scroll anywhere; the motion is a solved PDE plus a time-machine rewind.

**Exact per-frame transport** (field `u_prev/u_curr/u_next[80]`, cell 0 = LED 79/80; `history[1024][80]` ring; c² ≈ 0.14):

- **Seed:** `u_curr[i] = 0.5 + 0.3·exp(−(i/79)²·18)`, `u_prev = u_next = 0.5`.
- **Forward** (`phaseTimer < forwardDur ≈ 6 s / speedNorm`): `introEnv = 1 − smooth01(phaseTimer/1.6)`; inject k<16 `u_curr[k] += exp(−k²·0.18)·introGain·introEnv`. Every ~96 frames (or on beat, 16-frame cooldown): `imp = 0.42 + 0.46·clamp(rms·1.8,0,1)`; k<10 `u_curr[k] += exp(−k²·0.35)·imp·0.19`.
- **Leapfrog** i = 0..79: `L = (i==0? u_curr[1] : u_curr[i−1])`; `R = (i==79? u_curr[79] : u_curr[i+1])`; `lap = L − 2·u_curr[i] + R`; `edge = clamp((i/79 − 0.75)/0.25, 0, 1)`; `damp = moodDamping + edge·edgeAbsorb`; `u_next[i] = 2·u_curr[i] − u_prev[i] + c²·lap − damp·u_curr[i]`; clamp (source uses [−0.5, 1.5]). Then `u_prev = u_curr; u_curr = u_next; history[w] = u_curr; w = (w+1)%1024; count = min(count+1, 1024)`.
- **Switch to reverse** when `phaseTimer ≥ forwardDur && count > 8`; `reverseCursor = count − 1`.
- **Reverse:** `cur = clamp(reverseCursor, 0, count−1)`; `c0 = floor, c1 = c0+1, t = frac`; snap0/1 from ring; `u_curr[i] = 1 − (snap0[i] + (snap1[i] − snap0[i])·t)` — **the phase-flip + sub-frame interpolation**; `reverseCursor −= (count−1)/reverseDur·dt`; exit when `cur ≤ 0` (0.92·carry + 0.08·0.5 re-centre).
- **Render:** `normMin/normMax` follow field min/max at 6 Hz; LED i<160 `dist = |i − 79.5|`, `fi = min(dist, 79)`; `v = clamp((u_curr[fi] − normMin)/range, 0, 1)`; `sculpt = pow(v, 1.35)`; `bright = sculpt·brightness`; `hue = baseHue(chroma circular-mean) + min(dist·0.45, 36) + (reverse? 16 : 0)`; strip2 `fi+8`, `hue+24` at `i+160`.

**Fork port plan.** Dedicated `.ino` function + one boot-time buffer alloc. **Effort MEDIUM.** Math is plain float and centre-origin already (cell 0 = LED 79/80). Three issues:
1. **Memory.** `history[1024][80] = 320 KB` must be a one-time `heap_caps_malloc(MALLOC_CAP_SPIRAM)` at boot or `EXT_RAM_BSS_ATTR` static (single-zone → 320 KB, fine on 8 MB PSRAM). **Never internal DRAM.** No heap in `render()` (all memcpy into pre-allocated buffers).
2. **Missing inputs.** Fork has `chroma`/`rms`/`beat`; lacks `hopSequence` (replace with per-frame chroma update) and `getHeavyChroma`/`circularChromaHueSmoothed` helpers (port small helpers or derive hue from circular mean of `chroma[]`).
3. **Rainbow.** Replace the free-running `gHue` with a chroma/chord-derived base hue.
- **Timing:** 80-cell wave + 160-LED loop, 2 powf/LED — well under 2 ms.

**Mod2 / Mod3 (0x1B07 / 0x1B08, good tier)** share this exact transport; Mod2 adds a per-pixel spatial-warp shimmer (2× `sampleFieldLinear` + several sinf/LED), Mod3 adds a ridge-crest tracker (`ridgeEnv[80]` + an 80-cell slope pass — the heaviest, profile first). Same 320 KB PSRAM + same helper ports.

---

### Rank 3 — `0x1309` K1 Bloom BassTreble  *(best · EASY)*

**Source:** `firmware-v3/src/effects/ieffect/sensorybridge_reference/` (SbK1BloomV2 BASSTREBLE variant; ID `EID_SB_K1_BLOOM_V2_BASS_TREBLE = 0x1309`, effect_ids.h:249).

**What it really does.** It scrolls, but the scroll SPEED is audio-modulated (treble doubles it) and a √ spatial warp makes motion NON-linear — content accelerates toward the edge instead of streaming at constant rate. Bass controls the birth brightness of each centre pixel, so the transport reads as a musically-driven bloom, not a fixed-rate trail. This is SB's own `light_mode_bloom` lineage, so it drops onto `CRGB16 leds_16` natively.

**Exact per-frame transport** (buffers `work/scroll/aux/fx[160]`, `iter`):

- **EVEN frames** (`iter & 1 == 0`): `bass = max over c=0..5 of chroma[c]^contrast` (clamp 1); `treble = max over c=6..11` same; `grey = {bass,bass,bass}`; `trebleRatio = treble/(bass+treble+0.001)`; `fast = (treble > 0.5)`.
- **Scroll:** if `fast`: j=159..82 `work[j] = scroll[j−2]`, `work[80] = work[81] = grey` (2 px/frame); else j=159..81 `work[j] = scroll[j−1]`, `work[80] = grey` (1 px/frame).
- **Save-decay:** `scroll[80+i] = work[80+i]·0.995` (i 0..79).
- **√ warp** i 0..79: `prog = i/79`; `src = min(80 + sqrt(prog)·79, 158)`; `fx[80+i] = lerp(work[floor src], work[floor src+1], frac)`; copy `fx[80..] → work[80..]`.
- **Edge fade:** `work[80+i] *= (79−i)/79`.
- **Mirror:** `work[79−i] = work[80+i]`.
- **Colour:** `dominant = argmax chroma`; `btHue = trebleRatio·0.33`; per pixel `bright = work[i].r > 0.001 → hsv(noteHue[dominant] + huePosition + btHue wrapped, sat, bright)`. `aux = work`.
- **ODD frames:** `work = aux` (replay — this is what makes the effective scroll 0.5–1 px/frame).
- **Output:** `leds[0..159] = work`; copy to 160..319.

**Fork port plan.** `.ino` function, static `work/scroll/aux/fx[160]` `.bss` arrays (drop PSRAM). **Effort EASY** — SB's own bloom lineage drops onto `CRGB16 leds_16` natively. Needs only `chroma[0..11]` (have it) + dominant-bin + a slow `huePosition` drift. Colour path: HSV branch with `kNoteHues[12]` (no palette needed). All transport centre-origin + heap-free static buffers.
- **WATCH:** keep `prismCount` low/off (per-layer +5% hue is bounded, not a rainbow, but disable to be safe); **PRESERVE the even/odd frame alternation exactly** — it sets the effective scroll speed. Freeze the free-running hue base.

The whole Bloom family (`0x1301` base, `0x1307` Colour History, `0x130A` Exponential, `0x1500` Parity) is the same transport with a one-line injection/energy-law difference — port one variant and the rest are trivial. `0x1500` Bloom (Parity) and `0x1200` Ripple (ES) currently `heap_caps_malloc` their PSRAM buffers in `init()`; on the fork convert to static `.bss` RGBf/CRGB16 arrays.

---

### Rank 4 — `0x1C08` LGP Moire Cathedral (5L-AR)  *(best · EASY)*

**Source:** `firmware-v3/src/effects/ieffect/LGPMoireCathedralAREffect.cpp` (ID `EID_LGP_MOIRE_CATHEDRAL_AR = 0x1C08`, effect_ids.h:349).

**What it really does.** No scroll and no trail buffer at all — a true two-grating moire computed **statelessly per pixel** from two sine phases. The bright "cathedral arch" ribs appear to travel because the gratings are DETUNED and drift oppositely, so the beat envelope migrates optically. Wave-optics, not history transport. **Lowest-risk port in the whole set.**

**Exact per-frame transport** (centre-out `dist` 0..79):

- Inputs: `bass = (bands0+bands1)/2`, `mid = (bands2+bands3+bands4)/3`, `beatStr`, `chroma[12]`. EMA `m_bass` (τ 0.05), `m_mid` (τ 0.055). Circular chroma EMA → angle (τ 0.3); `baseHue = angle·255/2π + frozen gHue`. Max-followers `bassMax/midMax` (attack τ 0.058, decay τ 0.5, floor 0.04) → `normBass, normMid`.
- `impact`: if `beatStr > impact` set; `impact *= exp(−dt/0.2)`; `beatMod = 0.3 + 0.7·beatStr`.
- `p1 = clamp(7.5 + 3·(normMid−0.5), 6, 9)`; `p2 = p1 + 0.6`; `w1 = 0.65 + 0.4·speedNorm`; `w2 = 0.58 + 0.35·speedNorm`; `m_t += (0.85 + 3.5·speedNorm)·dtVis`; `ribPow = clamp(1.35 + 0.45·normBass + 0.3·impact, 1.3, 2.5)`. Fade `amt = clamp(18 + 35·(1−normBass), 12, 55)` via `fadeToBlackByDt`.
- **Per LED:** `progress = dist/79`; `g1 = sin(2π·dist/p1 + m_t·w1)`; `g2 = sin(2π·dist/p2 − m_t·w2)`; `moire = |g1 − g2|`; `wave = clamp(moire·0.55, 0, 1)`; `wave = pow(wave, ribPow)`; `impactAdd = impact·wave·0.35`; `b = (normBass·wave + impactAdd)·beatMod·silScale`; `b *= b`; `val = clamp(b,0,1)·255` scaled by brightness; `hue = baseHue + wave·42 + progress·12`; `setCentrePair(dist, CHSV(hue, sat, val))`.

**Fork port plan.** `.ino` function, per-effect float statics (no heap). **Effort EASY** — cheapest of the 5L-AR trio: 2 sinf + 1 powf per LED. Inputs `bass`/`mid`/`chroma`/`beatStrength` all derive from fork `bands[0..7]`+`chroma`+`beat`/`onset`. **No tempo/BPM/downbeat dependency** — nothing else gated.
- **Missing:** `silentScale()` (substitute an rms noise-gate or set 1.0) and `cinema::apply` post layer (optional, drop). Freeze `gHue` drift, keep hue chroma-anchored for no-rainbow compliance.

---

### Rank 5 — `0x1C0B` LGP Rose Bloom (5L-AR)  *(best · MEDIUM)*

**Source:** `firmware-v3/src/effects/ieffect/` (LGP Rose Bloom AR; ID `EID_..._ROSE_BLOOM_AR = 0x1C0B`). Proven on hardware (5L-AR fix, 2026-03-23 — see MEMORY `feedback_5lar_fix_pattern`).

**What it really does.** There is **no lateral transport at all** — the rose radius is recomputed centre-outward each frame and the figure OPENS/CLOSES in place while its petal count morphs. Light re-organises into more/fewer standing rings; the only "travel" is the breathing scale and a faint outward shimmer — the opposite of a scrolling trail.

**Exact per-frame transport** (`dist` 0..79):

- Inputs `bass = (bands0+1)/2`, `mid = (bands2+3+4)/3`, `beatStr`, `chroma[12]`. EMA `m_bass` (τ 0.05), `m_mid` (τ 0.055). Circular chroma EMA → angle (τ 0.3). Max-followers → `normBass, normMid` (attack 0.058 / decay 0.5, floor 0.04).
- `impact`: `beatStr` rise then `*= exp(−dt/0.18)`; `beatMod = 0.3 + 0.7·beatStr`. `petalK` exp-chase to `3 + 4·normMid` (alpha = 1 − exp(−dt/0.25)) clamp [3, 7]. `m_t += (0.3 + 1.8·speedNorm)·dtVis`; `bloomMod = 0.55 + 0.45·sin(m_t·0.35)`; `bandWidth = clamp(0.14 − 0.04·impact, 0.08, 0.18)`; `baseHue = angle·255/2π + frozen gHue`. Fade `amt = clamp(20 + 35·(1−normBass), 14, 55)`.
- **Per LED:** `progress = dist/79`; `rCurve = |cos(petalK·π·progress)|·79·bloomMod`; `distToCurve = |dist − rCurve|/79`; `band = exp(−distToCurve²/bandWidth²)`; `breathing = 0.90 + 0.10·cos(2π·(progress + m_t·0.25))`; `impactAdd = impact·band·0.35`; `bright = (normBass·band·breathing + impactAdd)·beatMod·silScale`; `bright *= bright`; `val = clamp(bright,0,1)·255` scaled; `hue = baseHue + band·45 + progress·20`; `setCentrePair(dist, CHSV(hue, sat, val))`.

**Fork port plan.** `.ino` function, per-effect float statics. **Effort MEDIUM.** *Baseline* is EASY (1 cos + 1 exp + 1 cos per LED). Inputs `bass`/`mid`/`chroma`/`beatStrength` from fork ControlBus. Squared brightness gives perceptual punch. Freeze `gHue`, keep chroma-anchored.
- **Missing:** `silentScale()` (rms noise-gate or 1.0) and `cinema::apply` (optional). The **full A/B mode-set is where it turns medium:** modes A/C/D/F need `isOnDownbeat`/`bpm`/`tempoConfidence`, which the fork's tempo may only partly supply. **Port only the Baseline (proven default)** and optionally mode H (petal spring, needs nothing extra); skip downbeat-gated modes.

**Sibling `0x1C05` Mach Diamonds (rank 6, EASY-MED)** is the same 5L-AR machinery in a shock-diamond geometry: `tri01(cellPhase)` train drifts outward while `spacing = clamp(0.16 − 0.06·normBass, 0.08, 0.20)` COMPRESSES the cells on a bass transient (the "thrust" signature); `sharpExp` rises with treble+impact; `isSnareHit` (fork percussion snare, present) punches an accent. Its only extra requirement over Moire is the snare trigger.

---

## 5. Shortlist coverage — the rest, the buggy siblings, and the recurring gaps

### Cards held just below the top 10

All "ok"-tier expanding-shell / standing-figure cards are portable but held on tier + distinctiveness, **not because they are buggy**:
- **`0x1A08` Transient Lattice** (medium) — transient-launched outward ring on a phase-scrolling lattice + leaky-integrator persistence field. Missing `fastFlux` (substitute onset/band-delta).
- **`0x1A04` Treble Net** (medium) — stateless counter-scrolling interference net; `heavyTreble` from `bands[5..7]`, `isHihatHit` native. Missing `timbralSaliency` (drop/substitute).
- **`0x1A02` Harmonic Tide** (hard) — dual counter-travelling + standing sine tide; motion is easy but the **colour identity IS the effect**: needs chord root/quality/confidence for the root/third/fifth triad. Confirm fork chord-API depth (`rootNote`, `isMinor`, confidence) before committing — else the triadic gradient collapses to a single-hue tide.
- **`0x1A01` Beat Prism** (medium) — beat-launched outward front over a phase-drifting crystal field; `beatStrength` soft-missing (substitute beat magnitude/tempo-phase strength; graceful degrade). Heaviest trig load — verify < 2 ms.
- **`0x1A07` Saliency Bloom** (medium) — beat-decay ring over a centre bed; the one missing input is `overallSaliency` (novelty) — substitute a smoothed onset/rms novelty follower.

Other good-tier cards fully portable: `0x1405` Beat Pulse Ripple (EASY, 3 concurrent contracting rings, same inputs as 0x1404), `0x1200` Ripple ES tuned (MEDIUM — convert PSRAM radial buffer to static, map `hopSequence`/flux/percussion), `0x0E00` BPM Enhanced (MEDIUM, beat-spawned outward ring pool — drive background phase from tempo phase, **not** the free-run+PLL hybrid), `0x0E03` Interference Scanner Enhanced (MEDIUM, clean high-value port; explicitly notes it used **brightness-not-speed** coupling to *avoid* the jog-dial jitter that plagues its buggy siblings). Standing-lattice cards `0x1603` Moire Silk / `0x1606` Stress Glass / `0x1607` Grating Scan and PDE `0x1701` RD Triangle (2.5 KB static `.bss`, no heap) are all EASY–MEDIUM stateless/small-buffer ports. Cloak/soliton family (`0x0609`, `0x0608`, `0x0605`, `0x060B`) are EASY–MEDIUM but consume **no audio** — flag reactive hooks as optional enhancements.

### The buggy "oscillating uncontrollable" siblings (tier2 — DEMOTE, or fix-on-port)

**None of these are in the surfaced top 10**, but they are in the corpus and Captain flagged the symptom. `0x0E08` Wave Collision, `0x0E07` Star Burst, `0x0E02` Chevron Waves all share one defect: `m_phase` is a **FREE-RUN oscillator** that is ALSO yanked by a **PLL P-correction** toward `beatPhase·628.3` whenever `tempoLocked` (Schmitt 0.6/0.4). When the lock toggles or `beatPhase` is noisy, `phaseError` wrapping (±314.15) plus the additive free-run makes the wave **visibly jump/reverse direction at random** — exactly the "oscillating uncontrollable" symptom. (The `VALIDATION_REVERSAL_CHECK` instrumentation exists to catch this.)
- **The FIX is the port opportunity:** on the fork, **drop the free-run + PLL hybrid** and drive phase directly from tempo/BPM phase (`phase = tempoPhase·2π·k`, or integrate BPM continuously), OR keep pure free-run without the additive `beatPhase` correction. That removes the random oscillation. `sceneParameters` → default to unity. Port + debug together; do not ship as-is.

### The un-portable gem

**`0x0E06` LGP Spectrum Detail Enhanced** — best-tier, but the fork has no 64-bin spectrum (only `bands[0..7]`) and no `musicalGrid.beat_in_bar`/`bar_phase01`. A faithful port needs a 64-point spectral input the fork lacks; degrading to 8 radial points loses the whole point. **Keep only if the fork gains a real multi-bin spectrogram.**

### Recurring fork gaps — resolve ONCE, reuse across ports

1. **`audioConfidence` / `silentScale`** — firmware-v3 ControlBus envelopes absent on the fork. Synthesise from `rms`+`onset` with a hold timer, or default to 1.0. *Affects Waveform Hybrid + all three surfaced 5L-AR effects.*
2. **Spectral FLUX** (`fastFlux` / `onset.transient.level01` / `onsetBassFlux` family) — fork exposes `onset` + percussion but may lack a 0..1 flux level; map to fork onset/novelty or a band-delta, or zero the term (graceful degrade). *Affects Spectral Envelope, Ripple ES, Interference Scanner, Transient Lattice, Treble Net.*
3. **`hopSequence()`** — fork has no 125 Hz analysis-hop counter; replace with per-frame updates or an onset-edge/beat-phase gate.
4. **`circularChromaHueSmoothed` / `getHeavyChroma` / `AsymmetricFollower`** — small helper ports needed by the Time-Reversal trio, Rose/Cathedral/Diamonds, Fresnel, Interference Scanner. **Port once, reuse everywhere.**
5. **`cinema::apply` / `LGPFilmPost`** — optional post layer on the 5L-AR set; drop or reimplement gamma.

### Rainbow compliance (fork hard rule)

Nearly every card uses a free-running `ctx.gHue` global hue rotation. Under the no-rainbow rule this **must be frozen or redirected to a chroma/chord-derived base hue on EVERY port.** The moire/interference band·hue spreads (Spectral Envelope `band·32`, Interference `+90`, moire `±42`) are fixed-per-band two-tone splits, **not** cycling sweeps — acceptable, but **review Spectral Envelope's full-wheel band spread specifically** before shipping.

### Memory

Only **Time-Reversal (320 KB history)** and **RD Triangle (2.5 KB)** need sizeable buffers. Time-Reversal must be `EXT_RAM_BSS_ATTR` / one-time SPIRAM malloc at boot (single-zone = 320 KB, fine on 8 MB PSRAM), **never internal DRAM**. All surfaced effects are heap-free *inside* `render()`.

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-11 | agent:research | Created. Surfaced 10 gem effects from the Lightwave-Ledstrip shortlist with faithful real-effect motion, per-frame transport, fork-port plans, and missing-input caveats. Ground-truthed crown jewels (0x1313, 0x1B06) against firmware-v3/src/effects/ieffect source — scroll rate 150, leapfrog wave eqn, phase-flip u=1-v, and PSRAM history alloc all confirmed. |
