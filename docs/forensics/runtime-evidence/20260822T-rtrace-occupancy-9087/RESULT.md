---
abstract: "Lever-2 packed-wire occupancy KEEP, then C2 hsv paint PASS_TRUE16 on 9087A500. Product k1_main_rpl_im69d carries geometric hsv plus seven palette_manual_colour swaps. Scored dump, not Captain eyes."
---

# Occupancy rtrace — Main RPL 9087A500 (2026-08-22)

**Verdict: KEEP (packer + hsv paint).** The 48-bit Lever-2 emit is not an 8-bit peephole. Colour through `hsv()` is not the old CHSV uint8 bridge.

**Close stamp:** scored dump, not the plate.

## Device

| Field | Value |
|---|---|
| Chip | `9087A500` |
| USB | `B4:3A:45:A5:87:90` |
| Port | `/dev/cu.usbmodem1401` |
| C2 probe | `IDENTITY OK: git=a30d38e1 env=k1_main_rpl_rtrace_probe epoch=1787388705` (working tree; SHA is HEAD at flash, bytes include uncommitted hsv/palette) |
| Product after PASS | `IDENTITY OK: git=a30d38e1 env=k1_main_rpl_im69d epoch=1787388790` |
| Product stamp | `IDENTITY OK: git=c2738b88 env=k1_main_rpl_im69d epoch=1787390639` |
| Tap | `k1_render_trace_on_frame16` on `ws2816_wire` before the Lever-2 return |
| Scorer | `scripts/regression-harness/score_rtrace_occupancy.py` |

Guard verified Main RPL before every write. Cal inherited. No `start_noise_cal`. B489 and P4 untouched.

## Dumps

| Leg | Frames | Chromatic | Verdict |
|---|---|---|---|
| Live show, room silent (`rtrace_silence.log`) | 785 | 0 | **INCONCLUSIVE** — silence gate, all zeros |
| Packer RGB stim (`rtrace_stim.log`) | 291 | 46560 | **PASS_TRUE16** (`mismatch_frac=0.995833`, 328 unique) |
| C2 `hsv()` stim (`rtrace_hsv_stim.log`) | 266 | 42560 | **PASS_TRUE16** (`mismatch_frac=0.664583`, 145 unique) |

C2 JSON:

- `fmt=rgb16hex`
- `mismatch_frac=0.664583`
- `unique_r=51` `unique_g=54` `unique_b=54` `unique_chromatic=145`
- Not the `k*257` lattice

Order: dump scored **before** commit. Product env restored after PASS so instrumentation does not stay on the plate.

## What this does not close

- Native ember/river occupancy under music (silent dump had no chromatic samples).
- Cold-cache `ColorFromPalette` inside `palette_manual_colour` if HD stops have not warmed.

## Artefacts

- `rtrace_silence.log` + `rtrace_silence.occupancy.json`
- `rtrace_stim.log` + `rtrace_stim.occupancy.json`
- `rtrace_hsv_stim.log` + `rtrace_hsv_stim.occupancy.json`
- `capture.py`
