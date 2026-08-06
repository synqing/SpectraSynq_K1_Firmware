# WAVEFORM HYBRID K1 (mode 32) — all-builds receipt

**Date:** 2026-08-05  
**Lane:** `lane/dual-sync-phase0`  
**Task:** `waveform-hybrid-k1-all-builds`  
**Verdict:** PROVEN (host builds + bench device select)

## Captain order

Make `LIGHT_MODE_WAVEFORM_HYBRID_K1` (mode 32 / `WAVEFORM HYBRID K1`) present, enabled, and dispatched in the **common** firmware path so every PlatformIO env that inherits the base `build_src_filter` can build and select it — **not** env-gated behind `K1_MIC_IM69D` / `IM73D` / similar.

## Enum confirmation

| Ordinal | Enumerator | Selectable |
|--------:|------------|------------|
| 30 | `LIGHT_MODE_BEAT_PULSE` | no (tombstone ID reserve; no body) |
| 31 | `LIGHT_MODE_BLOOM_BT` | no (tombstone ID reserve; no body) |
| **32** | **`LIGHT_MODE_WAVEFORM_HYBRID_K1`** | **yes** (`light_mode_is_enabled` default `true`) |

Slots 30/31 exist only so ordinal 32 stays append-only-stable vs `lane/gem-port-beat-pulse`. No silent renumber. No modes 33–36 bulk-ported.

## Files touched

- `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp` (from gem-port `49ea369`; dropped unused `k1_onset_beat.h` / `k1_tempo.h` includes)
- `SPECTRASYNQ_K1_FIRMWARE/system/config_types.h` (enum + tombstone disables)
- `SPECTRASYNQ_K1_FIRMWARE/system/system.h` (`set_mode_name(32, "WAVEFORM HYBRID K1")`)
- `SPECTRASYNQ_K1_FIRMWARE/visual/channel_effect_state.h` (`wfhyb_*` state)
- `SPECTRASYNQ_K1_FIRMWARE/visual/lightshow_modes.h` (decl + dispatch + vp_probe)
- `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino` (common dispatch)
- `SPECTRASYNQ_K1_FIRMWARE/effects/framework/EffectRegistry.cpp` (rows for 30–32)
- `tests/test_waveform_hybrid_k1_static.py` (new)
- `platformio.ini` — see below
- this receipt

## platformio.ini filter note (edgemixer)

**Change:** base `env:k1_hardware` `build_src_filter` gained `+<director/k1_edgemixer.cpp>`.

**Why:** dual-sync working-tree `.ino` already calls `k1_edgemixer_*`; without the TU, `k1_hardware` failed link (`undefined reference to k1_edgemixer_config/apply/...`). Pre-existing on this branch; not mode-32 logic. Required so “all builds” that inherit the base filter actually link.

**Not scope creep into mic/env gating.** Mode 32 itself is picked up by existing `+<effects/light_mode_*.cpp>` on the base filter (all inheriting envs).

## Env-gating check

Mode 32 dispatch / enum / cpp are **not** wrapped in `K1_MIC_IM69D`, `K1_MIC_IM73D`, or any mic/env `#ifdef`. Confirmed by static test + source inspection.

## Host verification

| Check | Result |
|-------|--------|
| `bash scripts/agent/pio-build.sh k1_hardware` | SUCCESS (firmware.bin present; elf exports `light_mode_waveform_hybrid_k1`) |
| `bash scripts/agent/pio-build.sh k1_bench_im69d` | SUCCESS (20.5 s; Flash 10.0% / RAM 33.0%) |
| `python3 -m pytest tests/test_waveform_hybrid_k1_static.py tests/test_vp_probe_mode_coverage_static.py -q` | **9 passed** |

## Device proof (bench only)

- **Target:** chip `B489A500`, USB serial `B4:3A:45:A5:89:B4`
- **Port (this session):** `/dev/cu.usbmodem112401` (port names drift; identity = MAC/chip)
- **Guard:** `k1_upload_guard.py --env k1_bench_im69d` → verified bench, RC=0
- **Flash:** `pio run -e k1_bench_im69d -t upload` → `[SUCCESS]`, hash verified
- **Serial:** `dsrdtr=False` (no download-mode wedge)
- **Proof:**
  - `:chip_id` → `B489A500`
  - `:build` → `env=k1_bench_im69d`
  - `:set_mode=32` → `CONFIG.LIGHTSHOW_MODE: 32`
  - `:get_mode` → `MODE: 32`
  - `:get_mode_name=32` → `MODE_NAME: WAVEFORM HYBRID K1`
- Logs: `_scratch/waveform_hybrid_k1_20260805/set_mode_32_name_proof.log`
- **No** `start_noise_cal`. **No** main-K1 flash. **No** im73d env on IM69 wiring. **No** commit.

## Source of truth

Effect body from `lane/gem-port-beat-pulse` @ `49ea369` (clamp fix on `7b3bb99` ADD).
