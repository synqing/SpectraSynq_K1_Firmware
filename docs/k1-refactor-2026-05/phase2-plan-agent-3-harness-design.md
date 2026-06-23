---
abstract: "Verbatim output of Plan Agent 3 (2026-05-24) — AP+VP equivalence harness design for the K1 SensoryBridge refactor. Two-tier VP harness (Tier A static probe via existing vp_probe_* machinery, Tier B live streaming with framebuffer hash + energy + centre-of-mass + FPS). AP harness extends existing dump_raw with ap_stream. AUDIT-FLAGGED on multiple grounds: per-commit harness gating + agent-never-opens-serial + ~2-day Captain budget are mutually exclusive (Captain time underestimated 3-5×); harness never proven to detect a real regression; reference data location in different repo from gated code."
---

# Plan Agent 3 — Equivalence Harness Design (Verbatim Draft)

> Recorded verbatim from the 2026-05-24 Phase 2 design dispatch. Audit-flagged on operational viability (Captain-time math) and on placement (harness baseline versioned in different repo from firmware it gates). K1-rooted session must re-design.

---

## 0. Design philosophy

Three orthogonal regression surfaces, three lightweight capture mechanisms, one operational workflow.

| Surface | What can drift | How we catch it |
|---|---|---|
| **AP — audio pipeline** | DC bias, gain, follower envelope, spectral content | reuse existing `dump_raw=…` + extend |
| **VP-static — deterministic render** | Mode dispatch, palette mapping, framebuffer math | new `vp_probe=…` serial trigger over the existing in-tree `vp_probe_*` machinery at `lightshow_modes.h:1671-1875` |
| **VP-live — audio-reactive render** | Frame transport, `dt` scaling, position drift (the WAVEFORM_FAST class of bug) | new `frame_dump=<metric>` streaming capture, sampled |

The WAVEFORM_FAST 1.60× regression would have been caught by **centre-of-mass spatial moment streaming**, not by hashing — hashing alone misses speed-of-motion drift because the same frames just play at the wrong rate. COM-vs-time slope is the bug detector.

---

## 1. AP regression harness

### 1.1 Stimuli set

| Stimulus | Source | Duration | Purpose |
|---|---|---|---|
| **silence** | verbal "music paused" | one chunk | DC offset, SSL noise floor, silence_flag correctness |
| **1 kHz tone** | Captain's tone generator (Test A precedent) | one chunk | Gain calibration anchor, peak_scaled headroom |
| **music — pink-ish** | Captain-chosen track A, looped | 5 s capture | Mid-band envelope, follower behaviour |
| **music — transient** | Captain-chosen track B (drums/percussion) | 5 s capture | Follower attack, novelty |

Music corpus is **two Captain-pinned tracks** (filename + timestamp recorded in baseline metadata).

### 1.2 Reference-capture procedure at freeze (commit `c872032`)

Captain runs:
1. Flash freeze build.
2. Open serial monitor → log to file.
3. Wait 5 s for boot prints.
4. Issue `start_noise_cal` (agent waits for Captain "room is silent" verbal).
5. Wait for SSL cal to finish.
6. Stimulus = silence: `dump_raw=silence` (capture next ~1 s).
7. Stimulus = 1 kHz tone: `dump_raw=tone` (capture next ~1 s).
8. Stimulus = music A: `ap_stream=5000`.
9. Stimulus = music B: `ap_stream=5000`.
10. Save as `baseline-c872032-AP.log`.

### 1.3 Per-stimulus metrics (load-bearing set)

| Metric | Silence | 1 kHz | Music A | Music B |
|---|---|---|---|---|
| `silence_flag` | ✓ | (=0) | (=0) | (=0) |
| `DC_offset` (sign+mag) | ✓ | ✓ | ✓ | ✓ |
| `SSL` | ✓ | — | — | — |
| `max_raw` range | ✓ | ✓ | ✓ | ✓ |
| `peak_scaled` range | — | ✓ | ✓ | ✓ |
| `follower` mean+max | — | ✓ | ✓ | ✓ |
| `spectrogram[64]` mean+argmax | — | ✓ | ✓ | ✓ |
| `chromagram[12]` mean | — | — | ✓ | ✓ |

### 1.4 Required firmware addition

`ap_stream=<ms>` serial command — for the next ms milliseconds, prints one tagged line per audio chunk:

```
[AP] t=<ms> dc=<int> max_raw=<int> peak_scaled=<f> follower=<int> sgram_mean=<f> sgram_argmax=<i> chroma_mean=<f>
```

Implementation in `i2s_audio.h` adjacent to existing `raw_dump_request`. Gated by `-DENABLE_AP_STREAM=1`. Hot-path cost when disabled = zero.

### 1.5 Tolerance bands

| Metric | Band | Justification |
|---|---|---|
| `DC_offset` sign | exact match | Sign flip = wiring/init regression |
| `DC_offset` magnitude | ±50% | SPH0645 bias is unit-and-temperature dependent |
| `SSL` | ±25% | Unit-to-unit MEMS spec is ±19% per equivalence run |
| `max_raw` upper bound | ±15% | AC gain |
| `peak_scaled` max | absolute ≤ 0.95 | Hard saturation gate |
| `follower` mean | ±10% | Visual-coupling variable |
| `spectrogram` argmax @ 1 kHz | bin index ±1 | Anchored to tone |
| `spectrogram` mean (music) | ±15% per bin, or KS ≤ 0.10 over 64 bins | Soft band |
| `chromagram` mean (music) | KS ≤ 0.12 over 12 bins | Looser — downstream |
| `silence_flag` | exact match | Existing |

### 1.6 Comparison

Off-target Python `scripts/regression-harness/ap_diff.py`. Stdlib + numpy.

### 1.7 Reference-data location

```
LightwaveOS_Official/docs/agent-outputs/analysis/harness-baselines/
  freeze-c872032/
    baseline-c872032-AP.log               ← raw serial capture
    baseline-c872032-AP-parsed.json       ← normalised metrics
    baseline-c872032-AP.md                ← human summary
    stimuli-manifest.yaml                 ← track titles, timestamps, tone freq
```

**AUDIT-FLAGGED: harness baseline versioned in a different repo from the firmware it gates. K1-rooted session should re-decide.**

---

## 2. VP regression harness MVP

### 2.1 Tier A — static deterministic probe (`vp_probe`)

The repo already contains: `lightshow_modes.h:1671-1875` defines `vp_probe_seed_inputs`, `vp_probe_prepare_render`, `vp_probe_render_hash`, `vp_probe_print_mode`, `vp_probe_hash_leds`, `vp_probe_energy`. NOT yet wired to a serial command.

MVP addition: `vp_probe=all` (and `vp_probe=<mode_id>`) in `serial_menu.h`. Output format already exists. Full 9-mode hash + energy coverage with one Captain command and zero audio stimulus required.

**This is the bug-budget-friendliest VP regression detector. Cannot catch live-audio-coupled drift (would have missed WAVEFORM_FAST 1.60× because that bug is in frame transport, not single-frame render).**

### 2.2 Tier B — live streaming probe (`frame_dump`)

```
frame_dump=<metric>,<mode>,<duration_ms>,<every_n_frames>
  metric ∈ {hash, energy, com, all}
  mode   ∈ 0..8  (9 lightshow modes)
  duration_ms — wall-clock window
  every_n_frames — subsample (default 4 → ~25 Hz capture at 100 LED_FPS)
```

**AUDIT-FLAGGED: 9 modes per Plan Agent 3 but audit found 13. K1-rooted session re-counts and adjusts.**

Per captured frame:
```
[FD] mode=<m> t_us=<wall> frame=<n> hash=<fnv32> energy=<u32> com=<f> fps=<f>
```

- `hash` — FNV-1a over `leds_out[0..NUM_LEDS]` (post-quantise)
- `energy` — sum of r+g+b
- `com` — Σ(i × (r+g+b)) / Σ(r+g+b)
- `fps` — instantaneous

Subsampling: every-N-frames; 5 s × every-4th-frame × 100 Hz = 125 lines × ~80 bytes = 10 KB serial output.

Stimuli: **SUPERSEDED by `03-hardware-gate-package.md` LOCKED-AS-AMENDED**. VP Tier B is silence-only for every mode. Tone and music are AP-only stimuli.

### 2.3 Per-mode capture protocol

For each of 9 modes × 2 stimuli = 18 captures at freeze:
```
set_mode=<m>
frame_dump=all,<m>,5000,4
```

Per Plan Agent 3: ~5 min Captain time per stimulus × 2 = ~10 min for VP-live half. Plus 30 s for `vp_probe=all`. Plus AP from §1.2. **Total baseline session ≈ 30 minutes.**

**AUDIT-FLAGGED: Captain-time math wrong by 3-5× per audit. Per-commit harness × 40+ Phase 5 sub-phase commits × ~30 min each = 20+ Captain hours just for Phase 5 captures, not the ~2 days Captain budget claimed elsewhere. K1-rooted session must re-budget.**

### 2.4 Tolerance per metric per mode

| Metric | Tier A (static) | Tier B silence | Tier B 1 kHz |
|---|---|---|---|
| **hash** (`vp_probe`) | **exact match** — any drift = FAIL | — | — |
| **hash** (`frame_dump` per-frame) | — | exact match for first frame only | — (live render non-deterministic) |
| **energy** | ±2% (A); ±15% mean (B) | ±15% mean across window | ±15% mean |
| **com** | ±0.5 LED (A); slope ±10% (B) | ±2 LED mean | **slope ±10% ← WAVEFORM_FAST detector** |
| **fps** | — | ±5% mean | ±5% mean |

**COM-slope is the load-bearing metric for transport-drift bugs.** If WAVEFORM_FAST scrolls 1 LED/frame and frame rate goes from 60 to 96 Hz, COM-vs-time slope goes from 60 LED/s to 96 LED/s → 1.60× exactly. Slope tolerance ±10% catches this.

### 2.5 Per-mode tolerance overrides

| Mode | Tier B energy | Tier B COM |
|---|---|---|
| GDFT, GDFT_CHROMAGRAM, GDFT_CHROMAGRAM_DOTS | ±10%, ±1 LED | tight |
| BLOOM, BLOOM_FAST | ±20%, ±3 LED | loose-stochastic |
| VU | ±15%, ±2 LED | loose-ish |
| WAVEFORM_FAST | ±15%, **slope ±10%** | **load-bearing** |
| WAVEFORM, WAVEFORM_HYBRID | ±15%, slope ±10% | same |

### 2.6 What this DOESN'T catch

1. Sub-quantisation colour drift below hash sensitivity
2. Perceptual flicker at sub-COM-band amplitude
3. Mode-dispatch bugs that compensate
4. Mode-transition glitches (captures are stable-state)
5. Boot-only or first-N-frame bugs
6. Cross-strip mismatch (secondary not in MVP)
7. Real-music response quality (deferred)
8. Audio-to-visual latency (deferred)

### 2.7 Reference-data location (per Plan Agent 3)

```
LightwaveOS_Official/docs/agent-outputs/analysis/harness-baselines/
  freeze-c872032/
    baseline-c872032-VP-probe.log
    baseline-c872032-VP-fd-mode<m>-silence.log
    baseline-c872032-VP-fd-mode<m>-tone.log    (18 files)
    baseline-c872032-VP-parsed.json
    baseline-c872032-VP.md
```

---

## 3. Level-2 metrics (defer/include)

| Metric | MVP / Level-2 | Why |
|---|---|---|
| SSIM perceptual diff | **Defer** | Serial bandwidth punitive |
| Color histogram per frame | **Defer** | Tier A already catches palette drift |
| Per-LED-region energy (left/right) | **Include in MVP** | Trivial; catches strip-asymmetry |
| Motion-vector estimation | **Defer** | COM-slope substitutes |
| AP→VP lag cross-correlation | **Defer** | Doubles complexity |
| Secondary strip capture | **Defer** | Add later |
| Music-driven VP capture | **Defer** | Non-deterministic |

---

## 4. Combined harness workflow

### 4.1 Pre-phase (freeze) capture

Done once at commit `c872032`. Captain session described above.

### 4.2 Post-phase capture

After each phase tag commit:
1. Captain flashes new build.
2. Captain repeats capture sequence.
3. Captain hands log dir to agent.
4. Agent runs `scripts/regression-harness/run_diff.sh --baseline harness-baselines/freeze-c872032/ --candidate harness-baselines/phase-<N>-<commit>/`
5. Agent files report at `docs/agent-outputs/analysis/harness-results/phase-<N>-<commit>-report.md`.

**AUDIT-FLAGGED: per-commit harness × ~40 commits × Captain-only-can-capture × ~30 min = 20+ Captain hours minimum. K1-rooted session must redesign — possibilities: (a) batch harness captures across phase, not per commit; (b) selective harness gating (some commits don't need full re-capture); (c) Captain time budget honestly stated; (d) some other operational pattern.**

### 4.3 On regression (FAIL)
1. Agent locks plan, posts FAIL report.
2. Captain decides revert (default) or investigate.
3. If revert: `git revert <commit>`, re-flash, re-capture, confirm PASS.

### 4.4 On PASS
1. Agent records PASS in `harness-results/phase-<N>-<commit>-report.md`.
2. Plan advances.

### 4.5 Scripts location

```
LightwaveOS_Official/scripts/regression-harness/
  ap_diff.py, vp_diff.py, run_diff.sh, parse_serial.py, README.md
```

Off-target Python 3.11, stdlib + numpy only.

---

## 5. Reference-data canonisation

**Artefact name:** "The Freeze Baseline"
**Path:** `LightwaveOS_Official/docs/agent-outputs/analysis/harness-baselines/freeze-c872032/`
**Protection:** chmod a-w; agent may not modify; `CANONICAL.md` at directory root.
**Re-canonisation rule:** required if K1 hardware revision / SPH0645 unit change / LED_FPS / NUM_LEDS / audio chunk size / sample rate changes.

---

## 6. Effort estimate (Plan Agent 3)

| Component | Effort |
|---|---|
| `ap_stream=<ms>` firmware addition | 0.5 day |
| `frame_dump=<metric>,<mode>,<dur>,<every_n>` firmware | 1.0 day |
| Wire `vp_probe=all` serial command | 0.25 day |
| `ap_diff.py` + `parse_serial.py` | 0.5 day |
| `vp_diff.py` (Tier A + Tier B + slope regression) | 1.0 day |
| `run_diff.sh` + `--self-check` modes | 0.25 day |
| Captain freeze-baseline capture session | 0.5 day Captain-time |
| Agent processing of baseline | 0.5 day |
| Documentation | 0.5 day |
| **Total agent-time** | **~4.5 days** |
| **Total Captain-time (initial baseline only — NOT per-commit Phase 5)** | **~0.5 day** |

**AUDIT-FLAGGED: this Captain-time number is for initial baseline only. Per-commit harness across Phase 5 is unaccounted for. K1-rooted session must produce true Captain budget.**

---

## 7. Open Captain decision points (per Plan Agent 3)

1. Music corpus: 2 pinned tracks or none in MVP?
2. Tolerance bands: accept proposed, or tighter/looser?
3. SSIM in MVP: confirmed deferred to Level-2?
4. Reference-data path acceptable?
5. New firmware commands acceptable scope-add?
6. Phase-tag commit naming convention?
7. Test-A 1 kHz tone source recorded?

---

## 8. Constraints honour-check (per Plan Agent 3)

| Constraint | How honoured |
|---|---|
| Captain runs commands, agent never opens serial | All flows: Captain serial monitor → log file → agent reads file |
| Captain produces silence/1 kHz manually | Stimulus list uses only Captain-produced |
| Baseline captureable in one Captain session | ~30 min Captain time |
| Runnable per-commit during Split phase | `run_diff.sh` orchestrates **AUDIT-FLAGGED: incompatible with ~2-day Captain budget** |
| Telemetry must not affect hot-path | `#if ENABLE_*` build flags; zero cost when disabled |
| Harness not stripped during refactor | (a) firmware additions in K1 fork headers (b) off-target scripts in LightwaveOS (c) baselines in LightwaveOS **AUDIT-FLAGGED: baseline in different repo from firmware it gates** |

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-24 | claude-code (Opus 4.7) | Persisted Plan Agent 3's harness design verbatim. Audit-flagged claims inline. Created during handoff to K1-rooted session. |
