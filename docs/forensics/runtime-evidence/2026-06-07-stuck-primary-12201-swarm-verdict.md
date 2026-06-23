# Stuck Primary Channel — SSA Swarm Verdict (12201)

**Date:** 2026-06-07  
**Device:** main K1 `/dev/tty.usbmodem12201` (chip B489A500)  
**Symptom:** Primary channel appears stuck / non-functional  
**Orchestrator re-run:** live serial `:vp_status`, `:smart_status`, `:edge_status`, `:dump` on 12201 vs 1401  

## Executive verdict

**NOT a single firmware regression.** The stuck-primary signature (`VP_CHROMA gate_gain=0`, `final_max=0`, `VP_AGC gated=true`) is **intermittent on 12201** and caused by a **calibration-domain mismatch**: post-cal `SSL=353` often exceeds live `max_raw` (80–300 under ambient/music), so `max_waveform_val = max_raw - SSL` stays **negative**, `peak_scaled` goes **negative**, spectrogram/chromagram goes **flat**, and the VP sparseness gate (`VP_FIX_CHROMAGRAM_SPARSENESS`) zeros output.

Secondary contributors:
- 12201 was **not in l1-reference posture** (`SMART_DIRECTOR_AUTONOMY: on`) until `:smart_scene=l1` was applied.
- Stale `noise_cal.bin` per-band subtraction (1.5×) can flatten spectrogram even when SSL looks sane.
- Recent AP open-quiet VU floor commits (**bd347fd**, **3295c43**) are **AP-only**; they do **not** set `gate_gain=0` directly.

## SSA delegation ledger

| ID | SSA | Claim | Class | Status | Evidence | Re-run | CONSUMED AS |
|----|-----|-------|-------|--------|----------|--------|-------------|
| VP-01 | VP gate code | gate_gain=0 when norm_max≤0.08 OR flatness≤0.08 in `make_smooth_chromagram()` | load-bearing | verified | led_utilities.h:1618-1637 | `:vp_status` | verified evidence |
| CAL-02 | NVS/cal | SSL-only fix insufficient; noise_cal + follower + AGC hysteresis persist | load-bearing | verified | GDFT.h, bridge_fs.h, i2s_audio.h | `:dump` + AP line | verified evidence |
| REG-03 | Regression timeline | VU floor 0.05f does not explain gate_gain=0 under music | load-bearing | verified | git bd347fd..3295c43 | git diff | verified evidence |
| ORCH | Live probe | 12201 intermittent gate collapse; 1401 stable open | decision-critical | verified | this doc §Live capture | python serial probe | verified evidence |

## Causal chain (Systems → Scientific)

```
I2S max_raw (often < SSL=353 on 12201)
  → max_waveform_val = max_raw - SSL  [negative]
  → peak_scaled negative / near zero
  → spectrogram_smooth flat / sparse
  → make_smooth_chromagram: norm_max≤0.08 OR flatness≤0.08
  → gate_gain=0, final_max=0  [primary appears stuck]
  → VP_AGC: gated=true while envelope < 2.5× floor
```

Load-bearing comment in `i2s_audio.h:249-253` documents this exact failure class.

## Live capture highlights (2026-06-07 orchestrator re-run)

### 12201 — collapsed frame (stuck signature)
```
VP_CHROMA: gate_gain=0.0000 norm_max=0.0262 flatness=0.0240 final_max=0.0000
VP_AGC: gain=9.9997 envelope=0.0015 floor=0.0010 gated=true
[AP] SSL=353 max_raw=221 peak_scaled=-0.307 silence=0 cal_valid=1
SMART_DIRECTOR_AUTONOMY: on   ← wrong posture pre :smart_scene=l1
SMART_AUDIO_ENERGY: 0.0100
```

### 12201 — open frame (same session, music transient)
```
VP_CHROMA: (via [VP]) chroma_final_max=0.7549 chroma_norm_max=0.8549
[AP] max_raw=231 peak_scaled=-0.268 bpm=70 conf=0.56 lock=1
```

### 1401 — stable open (comparison)
```
VP_CHROMA: gate_gain=1.0000 norm_max=0.4418 flatness=0.3727 final_max=0.3418
VP_AGC: gated=false
[AP] SSL=302 max_raw=247 peak_scaled=-0.215 cal_valid=1
```

### After recovery command on 12201
```
:smart_scene=l1  → SMART_DIRECTOR_AUTONOMY: off, APPLIED_MODE: 19
:edge_strength=0.35
[VP] chroma_final_max=1.0000 (transient open under stimulus)
```

## Ranked root causes

1. **SSL overshoot vs live max_raw (HIGH)** — noise cal captured a silence floor that dominates most runtime frames on 12201 mic path.
2. **VP chroma sparseness gate (HIGH)** — reactive gate; explains telemetry signature; pre-existing, not introduced by VU floor commits.
3. **Stale noise_cal.bin over-subtraction (MEDIUM)** — flat spectrogram even when SSL acceptable.
4. **Wrong smart scene on 12201 (MEDIUM)** — autonomy ON caused mode/scalar divergence from l1 reference; fixed by `:smart_scene=l1`.
5. **AP open-quiet VU 0.05f (LOW)** — does not set gate_gain; only affects onset/tempo permission.

## Recovery procedure (device-side, no flash)

Run on **12201** under confirmed silence, then under music:

```text
:smart_scene=l1
:edge_strength=0.35
:standby_dimming=false
:dump                    # note SWEET_SPOT_MIN_LEVEL, DC_OFFSET, STANDBY_DIMMING
N → Y                   # hotkey noise cal (NOT typed start_noise_cal)
# wait NOISE CAL COMPLETE
:dump
:vp_status              # under music: gate_gain>0, gated=false, norm_max>0.08
```

If still flat under music:
```text
:clear_noise_cal CONFIRM
# re-run N→Y cal under silence
:vp_chroma_gate=off     # diagnostic bypass only — confirms gate as bottleneck
```

**Do not use** `:restore_defaults CONFIRM` alone — leaves stale `noise_cal.bin`.

## Firmware fix candidates (if device recovery insufficient)

| Option | Trade-off |
|--------|-----------|
| Lower SSL multiplier (1.10 → 1.05) in Phase B | Risk false triggers on quiet input |
| Gate chroma sparseness on `peak_scaled` / VU, not flatness alone | VP behaviour change — doctrine review |
| Clamp `max_waveform_val` floor differently when max_raw < SSL | i2s_audio follower policy change |
| Post-cal sanity: if SSL > p95(max_raw) over N frames, auto-lower | New runtime guard |

## Contradictions resolved

- **Prior claim:** "12201 permanently gate_gain=0 after noise cal" → **REFUTED** as permanent; **CONFIRMED** as intermittent tied to flat spectrogram moments.
- **Prior claim:** "VU floor 0.05f regression caused stuck primary" → **REFUTED** for VP gate path; AP-only.

## Next orchestrator actions

1. Captain: re-run noise cal on **12201** under true silence (room quiet, no playback).
2. Verify under music: `max_raw > SSL`, `peak_scaled > 0`, `gate_gain > 0.08`.
3. If SSL still dominates: capture `:clear_noise_cal` + recal evidence.
4. Only then consider firmware follower/gate policy change.
