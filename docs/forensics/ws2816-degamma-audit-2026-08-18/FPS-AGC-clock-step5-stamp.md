# FPS / AGC clock — step 5 stamp (2026-08-19)

**Lane:** handover hybrid r1 (`feat/k1-scheduling-generation-hardening`)  
**Flash this session:** none.

## Already on silicon / in source

- Lever-2 RPL firmware tree matches HEAD at `a6149b29` lineage; I2S0 is the mic; RMT 4×48 FIT.
- Source now has: host α↔τ tests at **100 Hz**, `agc_env=%.4f`, C1 comment fix, 1.3 liveness write-up, `α=dt/(τ+dt)` on GDFT + i2s follower (default ON), identity-budget packer skip, probe env `k1_main_rpl_fps_agc_probe` (clock **off**).

## Host gate (closed this session)

- `pytest tests/`: **1420 passed, 1 skipped**.
- `pio-build.sh`: `k1_hardware` SUCCESS, `k1_bench_im69d` SUCCESS, `k1_main_rpl_im69d` SUCCESS. Provenance git=`293b211c`.
- Flash: **none**.

## Remaining ship path

1. **Agent (done):** host suite + three-env compile. No flash.
2. **Captain:** named GO to flash **`k1_main_rpl_fps_agc_probe`** to **`9087A500` only**. Stamp: pack/show numbers + show-skip `SYSTEM_FPS` series in an evidence folder.
3. **Captain:** eyes-on under **music** after the clock-fix ship build (follower blast radius: silence gate, sweet-spot, WAVEFORM-family).
4. **Shipped for this lane:** host suite green + this probe decision on disk + clock-fix commit on the branch (commit still Captain-authorised). Honour / `k1_hardware` / F887 / dull-show **#119716** stay separate.
5. **Bench `LED_FPS`:** RPL-only weaken unless Captain GOs a later `B489A500` flash. Discriminator remains `:dump` under music (serial GO) — see `LED_FPS-bench-liveness-1.3.md`.

## Probe decision (pre-flash)

- Env: `k1_main_rpl_fps_agc_probe` — NON-SHIPPABLE, `9087A500` only.
- `-DK1_AGC_DT_CLOCK_V1=0` so a baseline flash still measures dumped-silicon alphas.
- `-DENABLE_VP_PERF_AUDIT=1` + Lever-2 pack/show timers **before** `:1105` return.
- `:show_skip` (default 5 s) skips `show_leds()`; render loop stays. Watch `SYSTEM_FPS`.
- Never promote from this env.

**Close stamp for host side of this lane:** pytest green on this tree. Device close is the Captain GO + music eyes-on above.
