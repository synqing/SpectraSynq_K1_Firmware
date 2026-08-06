---
abstract: "SSA forensics (2026-08-05): WHEN LIGHT_MODE_WAVEFORM_HYBRID_K1 (mode 32) was first introduced in git, HOW it was implemented (donor 0x1313 / SbK1WaveformHybridEffect, fork-idiom port), and whether chroma-only brightness was intentional OG behaviour vs accidental port omission. Load-bearing. Default NOT_VERIFIED for casual summaries; evidence from git + donor source + handover docs + claude-mem. NO firmware patches proposed."
task_id: m32-origin-how-implemented
classification: load-bearing
default: NOT_VERIFIED
---

# MODE 32 Origin / Implementation Forensics — 2026-08-05

**Task ID:** `m32-origin-how-implemented`  
**Repo:** `/Users/spectrasynq/SpectraSynq_K1_Firmware`  
**Scope:** FORENSICS ONLY — no firmware edits, no flash, no commit.  
**Evidence stance:** refute casual “we forgot brightness” summaries against donor + first-intro commit.

---

## 1. Timeline (git-verified)

| When | What | Evidence |
|---|---|---|
| **2026-05-06/07** | Donor `0x1313` already live in firmware-v3; Captain darkness complaint → donor `brightMag` 1.5×→3.0× (chroma path); still chroma-primary + RMS invisible-dot failsafe | claude-mem #49330, #49335, #49338; donor path below |
| **2026-07-10/11** | Gem survey ranks `0x1313` #1; port authored **uncommitted** on `lane/gem-port-beat-pulse`; Captain A/B: mode 32 **WIN** 7.5–8/10 on IM73D; colour polish = `WFHYB_HUE_SPREAD` + lighter `WFHYB_TAU_COLOUR` (0.08 s) | `docs/research/k1_gem_effects_surfaced_2026-07-11.md`; `docs/handover/2026-07-11_captivation_canon_and_ab_verdicts.md`; mem #78834, #78705, #78842 |
| **2026-07-13 17:18:44 +0800** | **FIRST git ADD** of `light_mode_waveform_hybrid_k1.cpp` | SHA **`7b3bb9926eea447a23fcb55ddfcfb1e6f942c6c2`** |
| **2026-07-13 20:10:48 +0800** | Follow-up adversarial fix commit (tombstones / Iris / BLE roster) — **does not change mode-32 brightness path** | `49ea3695041c7c08d737a896100ee30c44f4a431` |
| **2026-08-05** | WT on `lane/dual-sync-phase0`: re-landed / all-builds wiring + peak/VU colour-level fallback patch (uncommitted relative to HEAD `3b59794`; **7b3bb99 is NOT an ancestor of current HEAD**) | WT `light_mode_waveform_hybrid_k1.cpp`; `docs/hardware/m32-dark-render-fix-2026-08-05.md`; mem #89302, #89303 |

### 1.1 First-add commit (required fields)

| Field | Value |
|---|---|
| **FIRST_SHA** | `7b3bb9926eea447a23fcb55ddfcfb1e6f942c6c2` |
| **DATE** | 2026-07-13 17:18:44 +0800 |
| **AUTHOR** | SpectraSynq `<elroy@spectrasynq.com>` (Co-authored-by: Cursor) |
| **SUBJECT** | `feat(effects): ship captivation families Shockwave and Iris` |
| **PARENT** | `6be1240ff1c28454381f86ed1876463cf17d2e16` (`docs(agent-stack): ledger sibling pointer SHAs`, 2026-07-13 12:24:42 +0800) |
| **BODY (why bundled)** | Ships purpose-built modes 35/36 + host-tested math; tombstones failed gem-ports 30/33/34; device eyes-on pending. Mode 32 cpp is included in the same bulk landing of the captivation / gem-port family set. |

**Re-show command:**

```bash
git show 7b3bb9926eea447a23fcb55ddfcfb1e6f942c6c2 -- SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp
```

### 1.2 Parent-commit context — what else landed (enums 30–36)

Same commit added the full gem-port + captivation roster. At `7b3bb99`, `config_types.h` ordinals:

| Ordinal | Enumerator | Role in that commit |
|---|---|---|
| 30 | `LIGHT_MODE_BEAT_PULSE` | gem-port 0x1404 (later tombstoned) |
| 31 | `LIGHT_MODE_BLOOM_BT` | gem-port 0x1309 (later tombstoned) |
| **32** | **`LIGHT_MODE_WAVEFORM_HYBRID_K1`** | **gem-port 0x1313 — KEEP** |
| 33 | `LIGHT_MODE_MOIRE_CATHEDRAL` | gem-port 0x1C08 (later tombstoned) |
| 34 | `LIGHT_MODE_CANNONADE` | captivation family |
| 35 | `LIGHT_MODE_SHOCKWAVE` | captivation family (commit subject) |
| 36 | `LIGHT_MODE_IRIS` | captivation family (commit subject) |

Also in that commit: `beat_pulse` / `bloom_bt` / `moire_cathedral` / `cannonade` / `shockwave` / `iris` cpp + math headers, `EffectRegistry.cpp`, `channel_effect_state.h` (`wfhyb_*` fields), `easing.h`, native math tests, `test_effect_easing_static.py`, ble_midi golden refresh. **28 files, +3000 / −21.**

### 1.3 Branches that first contained it

- **First containing branch tip (local):** `lane/gem-port-beat-pulse` (`git name-rev` → `lane/gem-port-beat-pulse~12` relative to tip at forensics time).
- **Also contains `7b3bb99`:** `melodic-bloom`, `e1/waveform-tempo-close`, `bench/k1ev-tap`, `probe/p3-beat-aware-director`, assorted `agent/*` / `agent/tool-qual-*` locals; remotes: `origin/melodic-bloom`, `origin/e1/waveform-tempo-close`, `origin/bench/k1ev-tap`, `origin/probe/p3-beat-aware-director`.
- **Does NOT contain `7b3bb99`:** `main`, `origin/main`, current `lane/dual-sync-phase0` HEAD (`3b59794`). Mode 32 on current WT is a **re-landing / graft**, not a merge of the gem-port commit.

**Pre-commit authoring:** handover + mem place the cpp as **uncommitted work on 2026-07-11** on `lane/gem-port-beat-pulse` (Captain A/B already run). First *git object* that adds the file remains `7b3bb99` (2026-07-13).

---

## 2. HOW it was implemented (first-intro `7b3bb99` body)

Header self-description (verbatim intent): *faithful port of firmware-v3 effect 0x1313 “K1 Waveform Hybrid” (`SbK1WaveformHybridEffect`).* Signature = amplitude-mapped **bouncing dot** + exponentially-fading outward scroll wake; colour = heavily EMA’d chroma-anchored palette sample.

### 2.1 Inputs

| Input | Role in first-intro |
|---|---|
| `k1_audio_snapshot_read()` → `peak_scaled`, `vu_level`, `silence` | Peak → two-stage EMA (`WFHYB_TAU_PEAK1/2` 0.016/0.023) → `wfhyb_peak_last` for **dot position**; peak/VU → presence hold; silence → `wfhyb_sil_scale` |
| Global `chromagram_smooth[12]` | **Sole source of `bright01` / particle colour magnitude** (contrast-square × 1.5, soft-knee, led-share 0.25) |
| `leds_prev_buffer` / `finalize_additive_frame(..., store_history=true)` | Persistent wake (replaces donor private `trailBuffer[160]`) |
| `effect_particle_colour(rp, …, hue_walk, bright01)` | Palette-bounded, chroma-centroid-anchored colour; `hue_walk = peak_last * WFHYB_HUE_SPREAD` (0.25) — colour polish from Jul-11 session |
| Unused includes in first blob | `k1_onset_beat.h`, `k1_tempo.h` (later dropped on WT) |

**Not used:** raw `waveform_history` (that is mode 11). Peak drives **position + fade rate**, not primary colour energy.

### 2.2 Brightness / colour path (OG port)

1. Sum contrast-squared chroma bins × `WFHYB_BRIGHT_BOOST` (1.5) → `total_mag`.
2. `bright_raw = total_mag * WFHYB_LED_SHARE` (0.25); `bright01 = 1 - exp(-bright_raw)`.
3. `raw_col = effect_particle_colour(..., bright01)`.
4. RGB EMA with `WFHYB_TAU_COLOUR` (**0.080 s** in first commit — already the Jul-11 colour polish vs donor’s 0.163 s).
5. `col_gain = confidence * sil_scale` gates the smoothed dot.

### 2.3 Amp / scroll / palette

- **Amp:** `amp = clamp(wfhyb_peak_last * 0.7 / sensitivity)`; `posF = HALF + amp * HALF`; sub-pixel split add onto trail.
- **Scroll:** `WFHYB_SCROLL_RATE = 405` px/s (150 × 27/10 Captain-locked native speed); max 8 steps/frame; outward centre→edge.
- **Fade:** `decay = 0.8 + 3.5*|peak|` (+ silence accel); `fade = exp(-decay*dt)`.
- **Palette:** chroma-anchored particle colour + amplitude hue walk; no free hue wheel (fork no-rainbow).

### 2.4 Documented fork-idiom differences (first-commit header)

- Trail → global history buffer, not PSRAM `trailBuffer`.
- Peak envelope reconstructed from `peak_scaled` (no raw waveform samples on snapshot).
- `audioConfidence` / `silentScale` synthesised from peak/VU + `snap.silence`.
- Photons compensation **intentionally not** re-applied (global PHOTONS downstream).

---

## 3. Donor (location + quotes)

### 3.1 Path (READ-ONLY reference — not in this repo)

```
/Users/spectrasynq/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3/src/effects/ieffect/sensorybridge_reference/SbK1WaveformHybridEffect.cpp
```

(+ matching `.h`). ID: `EID_SB_K1_WAVEFORM_HYBRID = 0x1313`.

Handover quote (`docs/research/k1_handover_2026-07-11_gems_port.md`):

> **DEV TARGET = the K1 fork** … **`firmware-v3` (in `~/Workspace_Management/Software/Lightwave-Ledstrip/`) is a READ-ONLY reference** to mine — build NOTHING there.

Research quote (`docs/research/k1_gem_effects_surfaced_2026-07-11.md`):

> **Source:** `firmware-v3/src/effects/ieffect/sensorybridge_reference/SbK1WaveformHybridEffect.cpp` (ID `EID_SB_K1_WAVEFORM_HYBRID = 0x1313` …).  
> **Colour.** … `b = chroma[c]²`; `b = min(b·1.5, 1)`; `dotColor += paletteColor(c/12, b·0.25)` … EMA … finally `*= confidence·silentScale`.

Captivation handover (`docs/handover/2026-07-11_captivation_canon_and_ab_verdicts.md`):

> Mode 32 \| **Waveform Hybrid K1 (0x1313)** \| **WIN — "basically the OG SB waveform, still stunning, 7.5–8/10."** … colour polish: `WFHYB_HUE_SPREAD` / `WFHYB_TAU_COLOUR` … Motion is untouched.

### 3.2 Donor brightness design (source-read 2026-08-05)

Primary path (**intentional chroma character**):

- Contrast-square chroma bins → ×1.5 → accumulate palette note colours at `kLedShare = 1/4`.
- Soft-knee / chromatic peak normalize; RGB EMA τ ≈ 0.163 s; × confidence × silentScale.

**Also intentional — invisible-dot FAILSAFE** (donor lines 187–194):

```cpp
// FAILSAFE: invisible dot prevention (gated by silentScale ...)
if (totalMag < 0.01f && ctx.audio.rms() > 0.02f
    && ctx.audio.controlBus.silentScale > 0.5f) {
    float fbPos = m_chromaHue + m_huePosition;
    dotColor = paletteColorF(ctx.palette, fbPos, ctx.audio.rms());
    totalMag = ctx.audio.rms();
}
```

This is **not** “peak drives everyday brightness.” It is a **gated rescue** when chroma energy collapses while RMS proves music is present. The Jul-13 port **did not carry this failsafe**.

---

## 4. First-intro vs today’s WT (peak-fallback patch) — what changed

| Aspect | First intro `7b3bb99` | Today WT (post Aug-5 dark-render work) |
|---|---|---|
| Snapshot API | `k1_audio_snapshot_read()` | `sb_audio_snapshot_read()` (comment: K1 snap dead without `K1_STM`) |
| Includes | + unused `k1_onset_beat.h` / `k1_tempo.h` | dropped |
| Colour brightness | chroma soft-knee **only** → `effect_particle_colour` | still chroma soft-knee, **plus** mode-11-style peak/VU `fallback_bright` + **colour-level** blend with HSV/palette `fallback_col` when chroma energy low |
| Donor RMS failsafe | **absent** | not restored as donor wrote it; replaced by sibling mode-11 blend idiom |
| Amp / scroll / fade DNA | unchanged intent | amp/scroll DNA claimed unchanged in fix notes |
| Colour polish knobs | `WFHYB_TAU_COLOUR=0.08`, `HUE_SPREAD=0.25` | same constants still present |

**Refutation of casual summary “OG forgot brightness / chroma-only was a bug”:**

1. Primary chroma→brightness is **documented design** in donor header (“SB 3.0.0 colour synthesis character”), gem research, and first-commit file header.
2. Captain Jul-11 A/B on IM73D called mode 32 stunning — chroma path was sufficient under that mic/calibration.
3. Donor’s own May-2026 brightness lift was **×1.5→×3.0 on the chroma path**, not a peak-brightness redesign.
4. What *was* omitted in the port: donor’s **RMS invisible-dot failsafe** (and photons compensation, intentionally). Calling the whole chroma-primary path “accidental” is **false**. Calling the missing failsafe an **accidental port omission** is **supported**.

---

## 5. Intentional-vs-bug assessment (chroma brightness)

| Claim | Verdict | Evidence |
|---|---|---|
| Chroma-primary colour/brightness is OG / donor design | **intentional** | Donor §COLOUR SYNTHESIS; port header §1 Colour; research deep-dive; architecture `01-waveform-class.md` L4 |
| Peak drives everyday plate brightness in OG | **false** | Peak → position (`amp`) + trail decay; colour energy from chroma |
| Missing RMS/invisible-dot failsafe in first port | **accidental port omission** | Donor lines 187–194 present; absent in `7b3bb99` blob |
| Aug-5 mode-11 peak/HSV blend = restoring OG | **NOT_VERIFIED / divergent** | Restores *robustness class*, not donor’s exact `paletteColorF(..., rms)` failsafe; changes null-chroma aesthetic vs donor |
| “We fixed brightness without understanding OG” risk | **VALID CAPTAIN CONCERN** | Fix docs cite mode 11 sibling, not donor failsafe; chroma-primary was never an accident |

**CHROMA_BRIGHTNESS_INTENT (contract field):** **intentional** (primary path) — with **accidental omission** of donor’s secondary RMS failsafe. Do not treat chroma-primary itself as a bug.

---

## 6. Mem-search notes (filtered)

| Query | Salient obs | Use |
|---|---|---|
| `WAVEFORM HYBRID K1` | #78834 port confirmed distinct bouncing-dot; #79026 Captain halted “inferior” claim; #89302/#89303 Aug-5 dark audit/fix | Port method + later patch narrative |
| `0x1313` | #49330 donor operational; #49335/#49338 donor brightness ×3; #78705 crown jewel | Donor history |
| `SbK1WaveformHybridEffect` | #78834 389-line source; #49335 brightMag | Donor file truth |
| `gem-port waveform` | (no hits) | —; use `0x1313` / handover docs instead |

On-disk handovers beat mem for **current** lane status; mem used here for **implementation chronology** only.

---

## 7. SSA CONTRACT (≤15 lines)

```
FIRST_SHA: 7b3bb9926eea447a23fcb55ddfcfb1e6f942c6c2
DATE:      2026-07-13 17:18:44 +0800 (author SpectraSynq; msg ships Shockwave/Iris but ADDS mode-32 cpp)
HOW:
  - Faithful fork-idiom port of fw-v3 0x1313 bouncing-dot + outward wake (not mode-11 scope seed)
  - Peak→EMA→dot position + fade; chromagram_smooth→soft-knee bright01→particle colour→RGB EMA→confidence×silence gate
  - Trail = leds_prev history; scroll 405 px/s; HUE_SPREAD/TAU_COLOUR colour polish already in first blob
DONOR: ~/Workspace_Management/Software/Lightwave-Ledstrip/firmware-v3/.../SbK1WaveformHybridEffect.cpp (0x1313)
CHROMA_BRIGHTNESS_INTENT: intentional (primary) + accidental omission of donor RMS invisible-dot failsafe (187–194)
  evidence: donor colour block; first-commit header; captivation handover WIN on chroma path; failsafe absent in 7b3bb99
COMMAND: git show 7b3bb9926eea447a23fcb55ddfcfb1e6f942c6c2 -- SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp
BRANCHES: first on lane/gem-port-beat-pulse; NOT on main/origin/main; NOT ancestor of lane/dual-sync-phase0 HEAD
```

---

**Document Changelog**

| Date | Author | Change |
|---|---|---|
| 2026-08-05 | agent:cursor-forensics | Created — git first-add, donor failsafe vs port omission, WT peak-fallback delta, intentional-vs-bug assessment. No firmware edits. |
