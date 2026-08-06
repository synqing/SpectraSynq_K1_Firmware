# MODE 32 Dark Render Fix — 2026-08-05

**Task ID:** `m32-fix-dark-render`  
**Env / device:** `k1_bench_im69d` @ bench chip `B489A500` / USB MAC `B4:3A:45:A5:89:B4` @ `/dev/cu.usbmodem112401`  
**Classification:** load-bearing / eyes-on decision-critical  
**Noise cal:** NOT run (forbidden this lane)

## Evidence question

After fix, does MODE 32 WAVEFORM HYBRID K1 produce visible LED output on bench under music (not black)?

**Default until Captain eyes-on:** `NOT_VERIFIED` (agent cannot see LEDs).

## Root cause (one sentence)

`light_mode_waveform_hybrid_k1` derived `bright01` / `raw_col` from `chromagram_smooth` only, so null chroma on IM69/uncal-chroma left the bouncing dot black even with healthy `peak_scaled`.

## Patch summary

**File:** `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp`  
**Change:** After chroma soft-knee `bright01`, blend in a peak/VU brightness fallback mirroring `light_mode_waveform_hybrid.cpp:84–106`:

- `chroma_energy = mean(chromagram_smooth[12])`
- `blend = clamp01(chroma_energy * VP_WAVEFORM_CHROMA_BLEND_GAIN)`
- `seed_level = max(peak, wfhyb_peak_last, vu_level)`
- `fallback_bright = seed_active ? seed_level * VP_WAVEFORM_FALLBACK_BRIGHTNESS : 0`
- `bright01 = bright01 * blend + fallback_bright * (1 - blend)`

Amp/scroll DNA unchanged (peak still drives `wfhyb_peak_last` → dot position). Mode 32 remains ungated (`light_mode_is_enabled` default true).

## Device actions (this session)

| Step | Result |
|------|--------|
| `bash scripts/agent/pio-build.sh k1_bench_im69d` | SUCCESS (~18.6 s) |
| `k1_upload_guard.py --env k1_bench_im69d --upload-port /dev/cu.usbmodem112401` | PASS — B489A500 |
| `pio run -e k1_bench_im69d -t upload --upload-port …` | SUCCESS |
| Serial `dsrdtr=False` `:chip_id` | `B489A500` |
| `:build` | `env=k1_bench_im69d` git=`3b59794` |
| `:set_mode=32` | `CONFIG.LIGHTSHOW_MODE: 32` / `MODE: 32` |
| Live `[AP]` under music | `peak_scaled` ~0.57–1.05, `silence=0`, `silent_scale=1.000` |

## Verdicts

| Claim | Status |
|-------|--------|
| Root cause + code fix applied | VERIFIED |
| Build + identity flash + mode 32 selected | VERIFIED |
| Visible non-black LEDs under music | **NOT_VERIFIED — Captain eyes-on required** |

## NEXT

Captain: eyes-on MODE 32 under music on bench IM69 — confirm bouncing-dot / wake visible (not black plate).
