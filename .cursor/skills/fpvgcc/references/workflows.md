# fpvgcc Workflows Reference

## Contents
- Adding a new build environment
- Changing compiler optimisation level
- Diagnosing a flag-induced gate failure
- Checklist: flag change gate sequence

---

## Adding a New Build Environment

New environments must extend an existing one. Never copy-paste the full `build_flags` block — use `extends` to inherit and override only what differs.

```ini
; new code to add
[env:k1_hardware_experiment]
extends = env:k1_hardware
build_flags =
  ${env:k1_hardware.build_flags}
  -DEXPERIMENT_FLAG
```

After adding:
1. Build: `pio run -e k1_hardware_experiment`
2. Confirm no unexpected symbols bleed into production: `pio run -e k1_hardware`
3. Add the environment to the device registry in `CLAUDE.md` or `.claude/CLAUDE.md` if it ships.

---

## Changing Compiler Optimisation Level

The default is `-O2` (set by the arduino-esp32 board definition). Changing it for the full build is high blast-radius.

**Scope the change to one translation unit first:**

```ini
; new code to add — per-file flag via build_src_filter + extra_scripts, or via component pragma
; For targeted investigation only:
[env:k1_hardware_o3_probe]
extends = env:k1_hardware
build_flags =
  ${env:k1_hardware.build_flags}
  -O3
```

Then run the full gate:

```bash
pytest tests/ -v
```

If the gate passes with no hash changes, the optimisation level is safe for that environment. Promote to `k1_hardware` only after eyes-on device validation confirms no perceptual regression.

---

## Diagnosing a Flag-Induced Gate Failure

When a `pytest` run fails after a `platformio.ini` change:

1. **Isolate the flag:** revert to the last passing `platformio.ini` and re-run to confirm the test was passing before.
2. **Identify the failure class:**
   - Hash mismatch in VP diff → likely fp reassociation (benign if mode-specific)
   - Assertion error in onset/beat replay → numeric divergence in DSP accumulator (investigate)
   - Build error → incompatible flag for Xtensa LX7 (remove the flag)
3. **For reassociation failures:** check if the affected mode is already in the fp-tolerant exception list in the test fixture. If not, add it after confirming the visual output is correct on-device.
4. **Never silence the gate by weakening the tolerance globally.** Widen tolerance only for the specific mode and document the reason.

```bash
# Narrow the failure to a specific test
pytest tests/test_vp_diff.py -v --tb=short 2>&1 | grep FAILED
```

---

## Checklist: Flag Change Gate Sequence

Copy this checklist and track progress:

- [ ] Read current `platformio.ini` build_flags for the target environment
- [ ] Make the flag change in the correct `[env:*]` block (not `[env]` shared)
- [ ] Build: `pio run -e k1_hardware` — confirm zero errors and zero new warnings
- [ ] Run: `pytest tests/ -v` — confirm all tests pass
- [ ] If hashes changed: determine benign (reassociation) vs semantic (algorithm)
- [ ] If benign: update fixture tolerance for the specific mode, document reason in test file
- [ ] If semantic: investigate DSP output before proceeding
- [ ] Build all other environments: `pio run` (builds default set) — confirm no bleed
- [ ] Commit `platformio.ini` and any updated test fixtures together in one commit
- [ ] Update `CLAUDE.md` environment table if a new environment was added

---

## Integration with pytest Gate

See the **pytest** skill for full gate usage. The fpvgcc-specific integration points:

- `tests/test_vp_diff.py` — VP hash regression; most sensitive to fp flag changes
- `tests/test_onset_beat_replay.py` — onset/beat numeric paths; sensitive to `-O` level changes
- Static analysis tests — independent of compiler flags; always run as a sanity check

```bash
# Minimum viable gate after any flag change
pytest tests/test_vp_diff.py tests/test_onset_beat_replay.py -v
```