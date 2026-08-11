---
abstract: "Canonical record for env:k1_bench_im69d_206led: current bench IM69D firmware with 206 physical LEDs on each output channel, bench GPIO 4/5 map, and the native 160-pixel render canvas resampled to both strips. Host/build proven only; not flashed in this session."
---

# K1 Bench IM69D 206-LED Dual-Channel Build

## Purpose

`env:k1_bench_im69d_206led` is a bench-only custom build for the current IM69D130
bench firmware with **206 physical LEDs per channel**:

- primary strip: 206 LEDs on the bench primary LED GPIO
- secondary strip: 206 LEDs on the bench secondary LED GPIO
- mic path: inherited from `k1_bench_im69d` (`K1_MIC_IM69D_PDM_V1`,
  `K1_MIC_IM69D_DSR_16S_V1`)
- LED GPIO map: inherited from `k1_bench_reference`, so GPIO `4/5`

The env is for bench `B489A500` only and is registered in the upload guard.

## Design Decision

The firmware keeps `NATIVE_RESOLUTION=160`. The 206-LED requirement changes the
physical output length, not the native effect canvas or GDFT topology.

That is intentional:

- the effect code, centre-origin logic, and audio mapping are built around the
  160-pixel native canvas
- the primary path already supports physical strip resampling through
  `scale_to_strip()`
- the secondary path now receives a compile-time `SECONDARY_LED_COUNT_VALUE`
  so it can allocate/output 206 LEDs without resizing the native secondary
  canvas

Native 206 would require a broader retopology of canvas buffers, effects,
mirrors, centre math, and DSP coupling. That is not needed for this build env.

## Source Gates

| File | Role |
|------|------|
| `platformio.ini` | Adds `[env:k1_bench_im69d_206led]` extending `k1_bench_im69d` with `-DK1_BENCH_IM69D_206_LED_V1=1`. |
| `system/config_types.h` | Maps `K1_BENCH_IM69D_206_LED_V1` to `LED_COUNT_VALUE=206` and `SECONDARY_LED_COUNT_VALUE=206`. |
| `system/globals.h` | Makes `SECONDARY_LED_COUNT` derive from `SECONDARY_LED_COUNT_VALUE` instead of hard-coded `160`. |
| `visual/led_utilities.h` | Extends the upsample OOB clamps to all physical-output builds longer than the 160 canvas. |
| `scripts/platformio/k1_upload_guard.py` | Binds the env to bench `B489A500` only. |
| `scripts/agent/pio-build.sh` | Allows build-only agent use of the new env. |
| `tests/test_custom_led_static.py` | Locks the 206 count, dual-channel secondary path, env inheritance, and upsample clamps. |

## Build And Flash

Build only:

```bash
bash scripts/agent/pio-build.sh k1_bench_im69d_206led
```

Flash only after live identity verification confirms bench `B489A500`:

```bash
pio run -e k1_bench_im69d_206led -t upload --upload-port <verified B489A500 port>
```

Do not flash this env to main `F887A500`; it uses the bench LED GPIO `4/5` map.

## Validation

Host/build evidence from 2026-08-06:

- `python3 -m pytest tests/test_custom_led_static.py tests/test_k1_upload_guard.py -q`
  -> `23 passed`
- `python3 -m pytest tests/test_dev_instrumentation_boundary.py -q`
  -> `9 passed`
- `python3 -m pytest tests/ -q` -> `857 passed, 1 skipped`
- `bash scripts/agent/pio-build.sh k1_bench_im69d_206led` -> `SUCCESS`,
  RAM `107792` bytes (`32.9%`), flash `655974` bytes (`10.0%`)
- `bash scripts/agent/pio-build.sh k1_bench_im69d` -> `SUCCESS`
- `bash scripts/agent/pio-build.sh k1_hardware` -> `SUCCESS`
- `git diff --check` -> clean

No device flash was performed for this env in this session.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-06 | agent:codex | Created `k1_bench_im69d_206led` design record and host/build evidence. |
