---
abstract: "Lever-2 packed-wire occupancy KEEP on 9087A500: stim, hsv paint, and native music all PASS_TRUE16. Product restored to k1_main_rpl_im69d. Scored dump, not Captain eyes."
---

# Occupancy rtrace — Main RPL 9087A500 (2026-08-22)

**Verdict: KEEP (packer + hsv paint + native music).** The 48-bit Lever-2 emit is not an 8-bit peephole. Live show under music occupies thousands of independent low bytes.

**Close stamp:** scored dump, not the plate.

## Device

| Field | Value |
|---|---|
| Chip | `9087A500` |
| USB | `B4:3A:45:A5:87:90` |
| Port | `/dev/cu.usbmodem1401` |
| Music probe | `IDENTITY OK: git=b625e89a env=k1_main_rpl_rtrace_probe epoch=1787400579` |
| Product after music dump | `IDENTITY OK: git=b625e89a env=k1_main_rpl_im69d epoch=1787400761` |
| Tap | `k1_render_trace_on_frame16` on `ws2816_wire` before the Lever-2 return |
| Scorer | `scripts/regression-harness/score_rtrace_occupancy.py` |

Guard verified Main RPL before every write. Cal inherited (`SSL=157`, `cal_source=persisted_profile`). No `start_noise_cal`. B489 and P4 untouched.

## Dumps

| Leg | Frames | Chromatic | Verdict |
|---|---|---|---|
| Live show, room silent (`rtrace_silence.log`) | 785 | 0 | **INCONCLUSIVE** — silence gate, all zeros |
| Packer RGB stim (`rtrace_stim.log`) | 291 | 46560 | **PASS_TRUE16** (`mismatch_frac=0.995833`, 328 unique) |
| C2 `hsv()` stim (`rtrace_hsv_stim.log`) | 266 | 42560 | **PASS_TRUE16** (`mismatch_frac=0.664583`, 145 unique) |
| Native music, no stim (`rtrace_music.log`) | 866 | 48168 | **PASS_TRUE16** (`mismatch_frac=0.78067`, 21475 unique) |

Music JSON:

- `fmt=rgb16hex`
- Audio awake: `silence=0`, `bpm=124`, `lock=1`, `lightshow=7` (`LIGHT_MODE_WAVEFORM_FAST`)
- `mismatch_frac=0.78067`
- `unique_r=10351` `unique_g=4267` `unique_b=16999` `unique_chromatic=21475`
- Not the `k*257` lattice (`FAIL_REPLICATE8` needs mismatch_frac < 0.01 and unique ≤ 256)

## What this does not close

- Cold-cache `ColorFromPalette` inside `palette_manual_colour` if HD stops have not warmed.
- C3 bloom CRGB8 saturation round-trip and authored palette vertices (still 8-bit stops).

## Artefacts

- `rtrace_silence.log` + `rtrace_silence.occupancy.json`
- `rtrace_stim.log` + `rtrace_stim.occupancy.json`
- `rtrace_hsv_stim.log` + `rtrace_hsv_stim.occupancy.json`
- `rtrace_music.log` + `rtrace_music.occupancy.json`
- `capture.py`
