# Mode 32 (WAVEFORM HYBRID K1) dark-plate — real root cause and fix

**Date:** 2026-08-05
**Device:** bench K1 `B489A500` (USB serial `B4:3A:45:A5:89:B4`, port `/dev/cu.usbmodem112401`)
**Env:** `k1_bench_im69d` (non-shippable IM69D eval)
**Status:** FIXED — proven on device by serial capture of the LED buffer.
**Supersedes:** `docs/hardware/m32-dark-render-fix-2026-08-05.md` (that fix was necessary-looking but inert; see below).

---

## 1. Verdict

Mode 32 rendered an all-zero LED buffer on every build. The cause was **not** the
chromagram. It was a **dead audio snapshot**: the effect read
`k1_audio_snapshot_read()`, a surface whose producer is never called in any
shipping env, so `peak_scaled` and `vu_level` were **hard zero for the life of
the boot** while the audio front-end was perfectly healthy.

---

## 2. Root cause

`SPECTRASYNQ_K1_FIRMWARE/audio/k1_audio_snapshot.cpp` publishes into a
file-static, zero-initialised struct:

```cpp
static K1AudioSnapshot k1_audio_snapshot_current = {};
```

Its only producer, `k1_audio_snapshot_update()`, is called from exactly one site
in the entire tree — `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.cpp:118` —
and that call sits inside `#ifdef K1_STM`:

```cpp
#ifdef K1_STM
  k1_audio_snapshot_update(frame_ms);
#endif
```

`K1_STM` is defined by `k1_hardware_stm` only. It is **not** in the build flags of
`k1_bench_im69d`, `k1_bench_reference`, `k1_bench_im73d`, or `k1_hardware`.

Therefore, on every env anyone actually flashes, `k1_audio_snapshot_update()`
never runs and `k1_audio_snapshot_read()` returns an all-zero struct forever.

`light_mode_waveform_hybrid_k1` was the **only consumer of that surface in the
firmware**, which is exactly why no other mode showed the fault and why modes 8
and 11 stayed lit on identical audio — they read `sb_audio_snapshot` / the live
globals instead.

### The zero cascade

With `snap.peak_scaled == 0` and `snap.vu_level == 0`:

| Stage | Value | Consequence |
|---|---|---|
| `presence_target` | 0 (needs peak or vu > 0.02) | — |
| `confidence` (`wfhyb_hold_env`) | 0 | — |
| `col_gain = confidence * sil_scale` | **0** | `dot_col` forced to (0,0,0) |
| `fx.wfhyb_peak_last` | 0 | `amp = 0` |
| `pos_f = HALF + amp*HALF` | 80 | dot pinned dead-centre, never bounces |

The dot was drawn every frame — in black, at the one index the scroll loop
immediately zeroes. Nothing could ever light.

---

## 3. Why the first patch failed

The 2026-08-05 chroma-fallback patch added a peak/VU brightness fallback:

```cpp
float seed_level = peak;                       // snap.peak_scaled  -> 0
if (fx.wfhyb_peak_last > seed_level) ...       // 0
const float vu = wfhyb_clamp01(snap.vu_level); // snap.vu_level     -> 0
const bool seed_active = (peak > 0.02f) || (vu > 0.02f);   // FALSE
const float fallback_bright = seed_active ? ... : 0.0f;    // 0
```

**It drew its rescue value from the same dead well.** `seed_active` was false and
`fallback_bright` was 0, so the fallback contributed nothing. The patch was
logically well-formed and still produced an identical black frame.

It also rested on a **misdiagnosis**. The audit's "smoking gun" was that
brightness came from `chromagram_smooth` only, implying chroma was null. Device
telemetry shows the opposite: chroma was the **only healthy input**
(`chroma=0.4558`, `bright01=0.625`), while peak/VU — the inputs the patch trusted
— were the dead ones. Even a perfect chroma fix could not have worked, because
the kill was downstream at `col_gain = 0`.

---

## 4. The fix

`SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp` — one file.

**Primary (the operative fix).** Read the live snapshot. `sb_audio_snapshot_update(t_now)`
runs every AP frame (`SPECTRASYNQ_K1_FIRMWARE.ino:958`) and `SBAudioSnapshot`
carries the same `peak_scaled` / `vu_level` / `silence` fields under the same
spinlock discipline:

```cpp
-#include "k1_audio_snapshot.h"
+#include "sb_audio_snapshot.h"
-  const K1AudioSnapshot snap = k1_audio_snapshot_read();
+  const SBAudioSnapshot snap = sb_audio_snapshot_read();
```

**Secondary hardening (latent, not the operative cause).** Both were found while
tracing and are inert on healthy audio; they remove two independent paths to a
black plate that would each have survived the primary fix:

1. *Colour-level blend instead of brightness-level blend.* In chromatic mode
   (`PALETTE_MODE_ENABLED == false`), `effect_particle_colour()` routes to
   `effect_palette_or_chroma_colour()`, which builds its base RGB **only** from
   `chromagram_smooth[]` and applies the passed brightness as a **final
   multiplier** (`lightshow_modes.h:473–507`). Under null chroma the base is
   (0,0,0), so any brightness multiplies to black. Mode 32 now blends a
   chroma-independent `fallback_col` against `chroma_col` at the colour level —
   the proven mode-11 idiom (`light_mode_waveform_hybrid.cpp:93–106`).
   *Note:* the bench runs palette mode (`pal=1`), where brightness is applied to
   a non-zero gradient sample, so this path was not active during this failure.

2. *Floored silence gate.* `col_gain = confidence * sil_scale` is a purely
   multiplicative kill, and the global `silence` latches true after 10 s of
   `sweet_spot_state == -1` (`i2s_audio.h:795–802`). Modes 8/11 carry no such
   gate. `col_gain` and `quiet_factor` are now floored by `seed_level` whenever
   a real signal is present, so a latched flag cannot zero a live signal.

Amp/scroll/dot/mirror DNA is unchanged.

**Diagnostic.** A 1 Hz LED-buffer probe sits behind `M32_DARK_DIAG`, a macro
**no env defines**. Enable per-session without mutating `platformio.ini`:

```bash
PLATFORMIO_BUILD_FLAGS=-DM32_DARK_DIAG bash scripts/agent/pio-build.sh k1_bench_im69d
```

(An earlier revision guarded it with `K1_MIC_IM69D_PDM_V1`; that correctly
tripped `tests/test_waveform_hybrid_k1_static.py`, which forbids any mic/env
conditional in this TU.)

---

## 5. Evidence

Captured under music on `B489A500`, mode 32, 1 Hz. Full logs:
`_scratch/m32_fix2_20260805/m32_capture.log` (before),
`m32_capture_after.log` (after).

**Before** — front-end healthy, effect blind:

```
[AP]  peak_scaled=0.809 silence=0 cal_valid=1
[M32] ledmax=0.0000 bright01=0.625 chroma=0.4558 peak=0.000 vu=0.000
      amp=0.000 pos=80 colgain=0.000 conf=0.000 sil=1.000 dot=0.000/0.000/0.000
```

25 of 26 lines `ledmax=0.0000` (the one non-zero was boot-intro residue in the
first frame before mode 32 took over). Note the contradiction that identifies the
bug: `[AP] peak_scaled=0.809` but `[M32] peak=0.000`.

**After** — snapshot agrees with the front-end (`peak == gpeak`):

```
[M32] ledmax=1.0000 bright01=0.771 chroma=0.5495 peak=0.966 vu=0.026 gpeak=0.966
      amp=0.500 pos=119 colgain=1.000 conf=1.000 sil=1.000 dot=0.757/0.000/0.049
[M32] ledmax=0.7847 ... peak=0.749 gpeak=0.749 amp=0.605 pos=128 colgain=1.000
```

**27 of 27 consecutive lines non-zero: `ledmax` min 0.4152, max 1.0000.**

| Signal | Before | After |
|---|---|---|
| `ledmax` (max LED component) | 0.0000 | 0.4152 – 1.0000 |
| `peak` (effect) vs `gpeak` (global) | 0.000 vs ~0.8 | agree exactly |
| `conf` | 0.000 | 1.000 |
| `colgain` | 0.000 | 1.000 |
| `amp` / `pos` | 0.000 / 80 (pinned) | 0.32–0.64 / 105–131 (bouncing) |

The dot tracking `pos=105..131` in step with `peak` is the mode's signature
amplitude-mapped bounce, so this is correct behaviour, not merely non-zero pixels.

---

## 6. Gates

| Gate | Result |
|---|---|
| `pio-build.sh k1_bench_im69d` | SUCCESS |
| `pio-build.sh k1_hardware` (production) | SUCCESS |
| `test_waveform_hybrid_k1_static.py`, `test_dev_instrumentation_boundary.py`, `test_vp_probe_mode_coverage_static.py` | 18 passed |

Not committed (out of scope for this task). No calibration was run; `k1_bench_im73d`
was not built or flashed; the main K1 (`F887A500`, `/dev/cu.usbmodem2101`) was not touched.

---

## 7. Residual risk / follow-ups

1. **CLEAN REFLASH COMPLETE (2026-08-05, SSA `m32-clean-reflash`).** Port was free;
   flashed `k1_bench_im69d` **without** `-DM32_DARK_DIAG` (`PLATFORMIO_BUILD_FLAGS`
   unset). Guard verified `/dev/cu.usbmodem112401` → MAC `B4:3A:45:A5:89:B4` /
   chip `B489A500`. Upload `[SUCCESS]` (657296 B app, hash verified, hard reset).
   Silicon: `:chip_id -> B489A500`; `:build -> version=40103 git=3b59794
   epoch=1785931519 env=k1_bench_im69d`; `:set_mode=32` → `CONFIG.LIGHTSHOW_MODE: 32`;
   `:get_mode -> MODE: 32`. AP healthy (`peak_scaled` non-zero, `cal_valid=1`,
   `I2S PDM RX INIT: PASS`); VP streaming after `s`; **no** `M32_DARK` / crash
   markers. Evidence: `_scratch/m32_clean_reflash_20260805/upload.log`,
   `post_flash_serial.log`. No `noise_cal`. No commit. Main `F887A500` (`2101`) untouched.
2. **`k1_audio_snapshot` is a live trap.** It remains compiled into every build
   with a producer that only runs under `K1_STM`. Now that mode 32 no longer uses
   it, it has **zero consumers** outside `K1_STM`. Any future effect that calls
   `k1_audio_snapshot_read()` will silently read zeros. Recommend either calling
   the producer unconditionally or compiling the TU only under `K1_STM`. Out of
   scope here (it is not this effect's file).
3. The two secondary hardening changes are inert on healthy audio and were not
   validated against a genuinely latched-`silence` or null-chroma device state.
