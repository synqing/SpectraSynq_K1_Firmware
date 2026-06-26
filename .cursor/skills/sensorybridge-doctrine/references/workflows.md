---
abstract: "K1 firmware change workflows: AP/VP change checklist, new effect integration, DSP feature addition, gate recovery. Iterate-until-pass patterns."
---

# SensoryBridge K1 Workflows Reference

## Contents
- AP/VP Change Workflow
- New Effect Integration
- DSP Feature Addition
- Gate Recovery
- Eyes-On (Device) Verification

---

## AP/VP Change Workflow

Copy this checklist before any audio pipeline (AP) or visual pipeline (VP) change:

```
- [ ] 1. Read .claude/CLAUDE.md load-bearing rules
- [ ] 2. Run baseline: pytest tests/ -q --tb=no → record pass count
- [ ] 3. Identify which SB_*_V2 flags govern the change area
- [ ] 4. Make change under correct #ifdef gate
- [ ] 5. Build: pio run (k1_hardware env)
- [ ] 6. Run full gate: pytest tests/ -v
- [ ] 7. All tests pass → proceed to device eyes-on
- [ ] 8. Device eyes-on: pio run --target upload && pio device monitor
- [ ] 9. Confirm no regressions: onset response, beat lock, chord colour
```

Iterate steps 4–6 until ALL tests pass. Never proceed to device with a failing gate.

---

## New Effect Integration

Checklist for adding a new `light_mode_*` effect:

```
- [ ] 1. Confirm STROBE LAW: effect uses spatial/transport reactivity only
- [ ] 2. Name function light_mode_<name>(CRGB* leds, const SBAudioSemanticState* state)
- [ ] 3. Function is pure — no globals, no side effects outside leds[]
- [ ] 4. Register in effect dispatch table (grep for existing registrations)
- [ ] 5. Add host-simulatable pytest fixture in tests/
- [ ] 6. Eyes-on test: at minimum 30s of music, varied tempo and dynamics
- [ ] 7. Confirm no global brightness modulation at any amplitude
```

```bash
# Find effect dispatch table registration point
grep -rn "light_mode_" src/ --include="*.cpp" | grep -v "void light_mode_"
```

---

## DSP Feature Addition

For new beat/onset/chord/tempo DSP features:

```
- [ ] 1. Define new SB_<FEATURE>_V2 flag in platformio.ini (k1_hardware build_flags)
- [ ] 2. Wrap new code in #ifdef SB_<FEATURE>_V2
- [ ] 3. Preserve legacy path under #else / #ifndef
- [ ] 4. Add field to SBAudioSemanticState if new output is needed
- [ ] 5. Add pytest fixture covering the new behaviour
- [ ] 6. Run: pytest tests/ -v — ALL must pass, including legacy path tests
- [ ] 7. Build: pio run
- [ ] 8. Device eyes-on: monitor serial for confidence values, beat lock quality
```

Validation pattern — iterate until pass:

```bash
# 1. Make DSP change
# 2. Build and test
pio run && pytest tests/ -v --tb=short

# 3. If failing: read the specific failure, fix root cause
# 4. Repeat until:
pytest tests/ -q --tb=no 2>&1 | grep -E "passed|failed"
# Target: N passed, 0 failed
```

---

## Gate Recovery

When a gate is discovered broken (tests failing before your change):

```
- [ ] 1. STOP — do not proceed with the planned change
- [ ] 2. git stash (preserve your work)
- [ ] 3. git log --oneline -5 (identify when gate broke)
- [ ] 4. git bisect to find the breaking commit
- [ ] 5. Fix the gate failure as a class (not just the failing test)
- [ ] 6. pytest tests/ -v → confirm ALL pass
- [ ] 7. git stash pop (restore your change)
- [ ] 8. Continue original workflow from step 5
```

**Rule:** A broken gate is fixed before any new work lands. Running new code against a broken gate produces meaningless results. See `feedback_amend_broken_gates.md` in project memory.

---

## Eyes-On (Device) Verification

Host regression gates are necessary but not sufficient. Device eyes-on is the final gate for any AP/VP/effect change.

```bash
# Upload to K1 hardware
pio run -e k1_hardware --target upload

# Monitor live output (beat confidence, chord state, mode transitions)
pio device monitor --baud 115200

# Verification checklist:
# - Beat locks within 2-4 bars of music start
# - Chord colour shifts are perceptually distinct
# - No strobing at any tempo or amplitude
# - Onset events visible as spatial transients (not brightness spikes)
# - Silence → calibration → resume cycle works cleanly
```

For A/B evidence capture, use `k1_hardware_harness` env which surfaces AP/VP diagnostic data for the pytest replay harness.

See the **pytest** skill for fixture and replay harness patterns.