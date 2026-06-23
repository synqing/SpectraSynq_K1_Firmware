---
abstract: "Runtime evidence for the Smart Director demo-autonomy visibility fix after Captain reported no visible improvement on 1401."
---

# K1 Smart Autonomy Visible Orbit v2

| Field | Value |
|---|---|
| Date | 2026-05-29 |
| Repo branch | `feat/gdft-harness` |
| 1101 role | L1 reference, `k1_hardware`, `:smart_scene=l1` |
| 1401 role | Autonomy candidate, `k1_bench_reference`, `:smart_scene=auto` |
| Calibration | No calibration command issued in this pass |

## Result

[FACT] The previous failure mode was reproduced conceptually: Smart autonomy could be active while the visible surface still resolved near the L1/reference mode and palette.

[FACT] The patched build was uploaded to both devices:

- `pio run -e k1_hardware -t upload --upload-port /dev/cu.usbmodem1101`
- `pio run -e k1_bench_reference -t upload --upload-port /dev/cu.usbmodem1401`

[FACT] 1101 reference status after `:smart_scene=l1`:

- `SMART_DIRECTOR_AUTONOMY: off`
- `SMART_PALETTE_OVERLAY: 0`
- `SMART_PALETTE_INDEX: 29`
- `SMART_MANUAL_OWNER_ACTIVE: 0`
- `EDGE_STRENGTH: 0.350`

[FACT] 1401 candidate status after `:smart_scene=auto` and dwell:

- `SMART_DIRECTOR_AUTONOMY: on`
- `SMART_PALETTE_OVERLAY: 1`
- `SMART_PALETTE_INDEX: 31` then `22`
- `SMART_AUTO_COLOUR_SHIFT: 1`
- `SMART_MANUAL_OWNER_ACTIVE: 0`
- `SMART_APPLIED_MODE: 10`
- `SMART_INTENT_MODE: 3`
- `EDGE_STRENGTH: 0.650`

[INFERENCE] The runtime surface is now materially different from the reference lane: 1401 owns frame-local palette overlay, uses a stronger secondary edge mix, and has entered a visibly distinct VU mode while 1101 remains L1/reference with no palette overlay.

## Verification

[FACT] Host verification passed:

- `python3 -B -m unittest tests.test_smart_director_replay tests.test_smart_visual_engine_static`
- `python3 -B scripts/regression-harness/smart_director_replay.py --json`
- `python3 -B -m unittest discover -s tests`

[FACT] Build verification passed:

- `pio run -e k1_hardware`
- `pio run -e k1_bench_reference`

[FACT] Production instrumentation symbol checks returned no matches:

- `nm .pio/build/k1_hardware/firmware.elf | grep -i mabutrace || true`
- `nm .pio/build/k1_bench_reference/firmware.elf | grep -i mabutrace || true`

## Notes

[FACT] Smart autonomy remains frame-local. `CONFIG.LIGHTSHOW_MODE` is not the correct proof surface; use `SMART_APPLIED_MODE`, `SMART_INTENT_MODE`, `SMART_PALETTE_OVERLAY`, `SMART_PALETTE_INDEX`, and direct visual observation.

[INFERENCE] If Captain still does not perceive a difference, the next fix should not be another subtle scalar change. The next lever should be a stronger product-level scene policy: make autonomy own a named sequence of mode/palette/edge states for 20-30 seconds, with music events controlling timing and intensity rather than merely selecting adjacent mode families.
