---
abstract: "Expectations declared BEFORE running the emulator gates on the current FE head 8b202f46 (K1-FE-SHOW lead, 10 Nov 2026 ~16:15 AWST). Any other outcome is a finding to diagnose before anything else."
---

# Declared expectations — gates.py on 8b202f46 (written before any run)

Sources (clean `git archive 8b202f46`, adapter applied by the lead before running, so each profile has its own tree hash and work copy):
- FE profile: `<scratchpad>/src-8b202f46-fe` + `PROTOTYPE-ADAPTER-ed0aa984.diff` (-p1, applied clean, no offsets).
- Main RPL profile: `<scratchpad>/src-8b202f46-rpl` + `PROTOTYPE-ADAPTER-ed0aa984-noflags.diff` (-p1, applied clean).

Why two exports: `gates.py` keys its work copy by source tree hash only, not by profile. Two profiles run from one un-patched export share one work copy; the second run's rsync reverts the first profile's patch and re-patches. It works only sequentially and is easy to get wrong. Pre-patching each export gives each profile its own tree hash.

| Run | G1 | G2 | G3 | G4 | Exit |
|---|---|---|---|---|---|
| `--profile fe --mode 32` | PASS | FAIL | FAIL | PASS | 2 |
| `--profile scenario --mode 32` | PASS | FAIL | FAIL | PASS | 2 |
| `--profile scenario --mode 18` | PASS | FAIL | FAIL | PASS | 2 |

Reasons: `k1_prsm.*`, `k1_authored_source.*` and the `check_serial` scanner are unchanged since `407fdf6f`; the live-peak OR at `light_mode_waveform_hybrid_k1.cpp:116` and the missing seek reconstruction are unfixed.

Risks that could change the outcome (each must be checked, not assumed):
1. **FE profile now compiles the K1-FE-Gx board** (`k1_fe` gained `-DK1_FE_BOARD_GX` in `c44172fa`; `k1_fe_emu` extends `k1_fe`). Gx sets an LED current budget from the USB-C CC lines (0 / 800 / 1900 mA). If the emulator reads the CC lines as "plain USB", the LED budget could be 0 and both edges dark or capped. Dark edges would make G1, G4 (and possibly G2) pass for the wrong reason. Check: payloads must be non-zero and comparable in brightness to the `ed0aa984` FE run.
2. `e2e83e53` (mode-32 silence fix) changes mode 32. G2's zero-PCM case exercises silence. Expect G2 still FAIL (the live peak OR is untouched), but per-pair counts may change.
3. `e28dd927` moved noise-calibration reset to the audio core and validates `:` setters. The stream path does not use `:`; expect no change.
4. The Main RPL profile at 8b202f46 still selects LED pins 15/16/17/18; pin numbers do not matter in emulation.

Baseline to compare against: `m2-emu/runs/fe-ed0aa984-m32-20261110T031959`, `rplproxy-ed0aa984-m32-20261110T031959`, `rplproxy-ed0aa984-m18-20261110T035112`.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (K1-FE-SHOW lead, session 2) | Created before running. |
