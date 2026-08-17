---
name: ship-path-required
description: "HARD FAIL — never say a result does not mean ship, promote, close, or done without immediately giving the remaining numbered ship path. Captain standing order 2026-08-17. Use on every gate hold, device-confirm, eyes-on outstanding, host-green, probe-pass, or 'not production' withhold."
---

# Ship path required

**HARD FAIL** if violated. Captain 2026-08-17.

Never tell Captain that a result "does not mean ship it", "does not mean promote", "does not close the gate", "is not production", or any equivalent withhold, unless the **same answer** contains the remaining ship path.

## Required in the same answer

1. What is **already** promoted / already on silicon / already in source.
2. Numbered remaining steps to ship or promote.
3. Who acts on each step (Captain vs agent).
4. The exact stamp or flash that means shipped.

A hold without a ship path is a failed answer.

## Forbidden

- Ending on "eyes-on still required" with no next action and no close stamp.
- "Map is not the territory" as a substitute for the promote plan.
- Host-green or probe-pass presented as a dead end.

## Live G2 example (bench, 2026-08-17)

Already in `k1_hardware` source and on bench silicon `k1_bench_im69d` @ `e911f86d`. Numeric probe passed 8000 µs.

1. Captain looks at the bench lights on that binary with music. Say PASS or FAIL.
2. PASS → stamp `G2_DEVICE = CLOSED`. That is G2 device promotion.
3. Agent continues G3–G7 on the branch (no F887 flash).
4. G8 + separate Captain GO flashes main K1 (`F887A500`). That is the main-unit promote.
