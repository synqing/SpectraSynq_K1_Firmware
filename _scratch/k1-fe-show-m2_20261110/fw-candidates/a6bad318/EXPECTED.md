---
abstract: "Expectations declared BEFORE judging FW-lead candidate a6bad318 (fe/k1-fe-show-fixes, 10 Nov 2026 17:30 AWST) with gates.py. Written by the K1-FE-SHOW lead at 20:25 AWST."
---

# Candidate a6bad318 — declared expectations

Candidate: `a6bad31853b8c3a2535290e40ea36852dc4d4c05`, parent `8b202f46`, 44 files. Scope check against `../SHARED-TREE-OWNERSHIP-2026-11-10.md`: PASS. The only shared file is `visual/led_utilities.h`; all four of its hunks are the FW lead's (`apply_brightness`, `show_leds` ×2, `apply_brightness_secondary`). There are 0 occurrences of the Modernes C++ symbols (`K1LookFrame`, `look.apply`, `k1_mode_request_land`).

Source: one clean `git archive a6bad318`. The RX adapter is now in mainline (`k1_emu_fixture_rx_read`, `rx_stream` present), so `gates.py` patches nothing. Both profiles share one work copy, so the three invocations run one after another.

Change from the baseline method: `k1_fe_emu` no longer carries the B489 bench flags, because the prototype adapter's platformio hunk is not applied. The FE profile is now pure `k1_fe` (Gx) plus emulator adapters. FE-profile bytes are therefore not comparable to the `8b202f46` FE baseline; the Main RPL profile (`k1_main_rpl_emu`) is comparable.

| Run | G1 | G2 | G3 | G4 | Exit |
|---|---|---|---|---|---|
| `--profile fe --mode 32` | PASS | PASS | PASS | PASS | 0 |
| `--profile scenario --mode 32` | PASS | PASS | PASS | PASS | 0 |
| `--profile scenario --mode 18` | PASS | PASS | PASS | PASS | 0 |

These are the change requests' completion conditions: G2 (the live mic cannot change either edge) and G3 (the same position reached by continuous play, a forward seek and a backward seek agrees after R = 5.0 s).

Risks to check, not assume:
1. **A trivially dark or frozen output would pass G2 and G3 falsely.** Check that both edges are lit and that they vary with the prepared stream: compare the g1 payload with the g4 payload and with the 8b202f46 brightness.
2. **Mode 18 now uses its unlocked scroll during a show** (commit note). G3 on mode 18 tests that. Check that it still moves with the music: frames must not all be the same.
3. **Live output must be unchanged** (not covered by G1–G4). This is a separate emulator check with no stream, a6bad318 against 8b202f46.
4. **G3 uses the old seek semantics.** A seek resends the original frames, so seq jumps after a preamble. The candidate treats a seq/time jump as a new epoch and clears state. That is the intended mechanism.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (K1-FE-SHOW lead) | Created before running. |
