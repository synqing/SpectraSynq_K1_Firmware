# fpvgcc Patterns Reference

## Contents
- -ffast-math and DSP gates
- Per-environment flag discipline
- FPU and vectorisation flags
- WARNING: Shared env block mutation
- WARNING: Silent numeric divergence

---

## -ffast-math and DSP Gates

`-ffast-math` permits floating-point reassociation, which changes the numeric result of accumulated DSP operations. The K1 host pytest gate uses bit-exact hashes for VP (visual pipeline) diffs. A `-ffast-math` change **will** flip those hashes.

**Known benign case:** mode 11 (`waveform_hybrid`) hash divergence under `-ffast-math` is a reassociation artefact, not a logic regression. The gate was updated to be fp-tolerant for this mode. Do NOT revert the flag to silence the gate — fix the gate tolerance instead.

```bash
# Reproduce the divergence locally before concluding it is benign
pytest tests/test_vp_diff.py -v -k "mode_11"
```

**Rule:** a gate failure caused by `-ffast-math` reassociation is fixed **as a class** (fp-tolerant gate), never by disabling the flag unless the perceptual output also regresses.

---

## Per-Environment Flag Discipline

Each `[env:*]` block in `platformio.ini` is independent. The `[env]` shared block propagates to all environments.

**DO:**
```ini
[env:k1_hardware]
build_flags =
  ${env.build_flags}
  -DSB_TEMPO_CONF_V2
  -DSB_ONSET_V2
```

**DON'T:**
```ini
[env]
build_flags = -DSB_TEMPO_CONF_V2   ; BAD — affects every environment including dev/probe envs
```

**Why:** Dev/probe environments (`k1_hardware_trace_dev`, `k1_motion_probe`) rely on the shared block being clean. Polluting it with feature flags silently enables production DSP paths in diagnostic builds, making trace captures misleading.

---

## FPU and Vectorisation Flags

The Xtensa LX7 has a hardware FPU. The pioarduino toolchain enables it by default. Do not add `-mfpu` or `-mfloat-abi` manually — the board definition already sets the correct values for ESP32-S3.

```bash
# Verify the board definition sets FPU correctly
grep -r "mfpu\|mfloat-abi" ~/.platformio/packages/framework-arduinoespressif32/
```

**Xtensa LX7 does not support NEON/SVE.** Do not add ARM vectorisation flags. The compiler will reject or silently ignore them, but they add confusion to flag audits.

---

### WARNING: Shared env Block Mutation

**The Problem:**

```ini
; BAD — modifying the shared block
[env]
build_flags =
  -DARDUINO_USB_MODE=1
  -DSB_NEW_FEATURE        ; <-- added here "for convenience"
```

**Why This Breaks:**
1. All environments pick up `SB_NEW_FEATURE`, including `k1_motion_probe` and `k1_tempo_probe` which have narrow, isolated test purposes.
2. Diagnostic captures from probe environments no longer reflect the isolated subsystem — they silently include the new feature.
3. Gate failures in probe environments become ambiguous (probe regression vs. feature regression).

**The Fix:**

```ini
; GOOD — scoped to the target environment
[env:k1_hardware]
build_flags =
  ${env.build_flags}
  -DSB_NEW_FEATURE
```

---

### WARNING: Silent Numeric Divergence

**The Problem:**

Changing `-O2` to `-O3` or adding `-ffast-math` on Core 0 (audio pipeline) can silently alter Goertzel accumulator results. The pytest host gate catches this via VP diff hashes, but only if the test fixture exercises the affected bin range.

**Why This Breaks:**
1. Goertzel uses accumulated multiply-add; reassociation changes the order → different rounding.
2. The visual output changes subtly (colour shift, brightness crush) without any build error.
3. DSP regressions at 133 Hz manifest as perceptual drift, not crashes.

**The Fix:**
- Run `pytest tests/ -v` after any `-O` or `-f` flag change.
- For changes to audio-path files, also run `pytest tests/test_onset_beat_replay.py tests/test_vp_diff.py -v`.
- If hashes change, determine whether the change is benign (reassociation) or semantic (algorithm changed) before updating the fixture.