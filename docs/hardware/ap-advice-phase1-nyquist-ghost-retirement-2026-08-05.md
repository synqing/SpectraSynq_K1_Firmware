# AP advice Phase 1 — Nyquist ghost retirement (2026-08-05)

**Task ID:** `phase1-nyquist-authority` (behavior-change ticket; formula untouched)  
**Branch:** `feat/ap-advice-phase0-im69d-gain8`  
**Prereq:** Phase 0 PASS (`1ae9d4a`, G=4, SSL=74, silence=1)

## Decision

Keep `NUM_FREQS=80` canvas. Analysis authority = bins with `target_freq ≤ fs/2` via `sb_gdft_nyquist_safe_bin_hi()` (default profile → **71**; ghosts **71–79**).

## Changes

| Surface | Action |
|---|---|
| `k1_gdft_core.cpp` | Skip Goertzel for `i >= nyquist_safe_bin_hi`; force magnitude / EMA avg to 0 |
| River / surge / tempo-river family | Inject only `analysis_bins`; hue denom from safe count |
| `light_mode_gdft` | Map LEDs across `analysis_hi`, not `NUM_FREQS-1` |
| Dense Forge (+ chord) | Band sums / moiré index clamp to analysis bins |
| Quantum collapse | High-band energy stops at safe_hi |
| Host | `tests/test_nyquist_bin_hygiene_static.py` asserts skip + VP authority + ×2 formula still present |

## Gates

| Gate | Result |
|---|---|
| `pytest tests/test_nyquist_bin_hygiene_static.py` (+ GDFT honesty) | PASS |
| `pio-build.sh k1_bench_im69d` | PASS |
| `pio-build.sh k1_hardware` | PASS |
| Flash bench `B489A500` | Deferred if no USB port at commit time — re-flash with Phase 2 if needed |

## Explicit non-goals

- No change to `block_size = fs/(Δf·2)` (Phase 2 only)
- No decimator
- No dual-mic / parabolic / adaptive floor (Phase 3 deferred)
