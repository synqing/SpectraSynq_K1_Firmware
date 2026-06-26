# PlatformIO Workflows Reference

## Contents
- New Environment Workflow
- Build → Test → Upload Gate
- Adding a New Library
- Diagnosing Build Failures
- Regression Harness Integration

---

## New Environment Workflow

Use this when creating a new named environment (e.g., a new bench variant or experiment environment).

Copy this checklist and track progress:
- [ ] Add `[env:my_new_env]` to `platformio.ini` with `extends = base_env`
- [ ] Add environment-specific `build_flags` only (avoid duplicating shared flags)
- [ ] Verify build: `pio run -e my_new_env`
- [ ] Confirm no flag drift vs. nearest sibling env: `diff <(pio run -e k1_hardware --dry-run 2>&1) <(pio run -e my_new_env --dry-run 2>&1)`
- [ ] Add env to CLAUDE.md Quick Start table if it's persistent

---

## Build → Test → Upload Gate

This is the canonical flow before any device upload. Never skip steps.

1. **Build firmware**
   ```bash
   pio run -e k1_hardware
   ```
2. **Run host regression harness**
   ```bash
   pytest tests/ -v
   ```
   If any test fails, fix it before proceeding — do not upload a build that fails host gates.

3. **Run type check**
   ```bash
   bun run check-types
   ```

4. **Upload (guard will verify device identity)**
   ```bash
   pio run -e k1_hardware --target upload
   ```

5. **Monitor**
   ```bash
   pio device monitor
   ```

Iterate until pass: if `pytest` fails, fix the issue and repeat from step 1. Only proceed to upload when all gates are green.

---

## Adding a New Library

1. Find the package name and version on the PlatformIO registry or GitHub.
2. Add to `lib_deps` in the shared `[base_env]` (or a specific env if the lib is env-scoped):
   ```ini
   lib_deps =
       fastled/FastLED@3.10.3
       author/newlib@=1.2.3   ; new code to add — pin exact version
   ```
3. Build to verify resolution:
   ```bash
   pio run -e k1_hardware
   ```
4. Confirm the library appears in `.pio/libdeps/k1_hardware/`.
5. Add to `lib_deps` in ALL environments that need it (or promote to `base_env`).

**DO NOT** copy library source into the project tree unless the library is heavily patched and the patches are documented. PIO's dependency manager handles updates; vendored copies rot.

---

## Diagnosing Build Failures

**Step 1 — Get verbose output:**
```bash
pio run -e k1_hardware -v 2>&1 | tee /tmp/pio_build.log
```

**Step 2 — Find the first error (not warnings):**
```bash
grep -n "error:" /tmp/pio_build.log | head -20
```

**Step 3 — Check flag conflicts:**
```bash
grep "build_flags" platformio.ini
```
Look for duplicate `-D` defines with conflicting values across inherited envs.

**Step 4 — Check library version conflict:**
```bash
ls .pio/libdeps/k1_hardware/
```
If a library directory is missing or shows an unexpected version, run `pio run --target clean` then rebuild.

**Step 5 — Toolchain mismatch:**
```bash
pio run -e k1_hardware --verbose 2>&1 | grep "xtensa-esp32s3-elf-g++"
```
Confirm the correct toolchain is being invoked. If not, the platform package URL in `platformio.ini` may have drifted.

---

## Regression Harness Integration

The `pytest` host harness gates every build. See the **pytest** skill for full test patterns.

Key integration points with PlatformIO:

- `k1_hardware_harness` environment enables diagnostic capture mode (`VPAB` packets) — use this env when generating test fixtures, not `k1_hardware`
- Test data lives in `tests/` and references audio snapshots from `docs/forensics/`
- The harness does **not** require a connected device; it replays recorded audio snapshots

```bash
# Run full harness (no device needed)
pytest tests/ -v

# Run only replay tests
pytest tests/test_onset_beat_replay.py -v

# Skip device-dependent tests
pytest tests/ -k "not device" -v
```

**Feedback loop:**
1. Edit firmware source
2. `pio run -e k1_hardware`
3. `pytest tests/ -v`
4. If tests fail → fix source → repeat from step 2
5. When green → `pio run -e k1_hardware --target upload`