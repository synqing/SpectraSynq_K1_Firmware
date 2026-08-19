# FPS / AGC clock — step 5 stamp (2026-08-19)

**Lane:** handover hybrid r1 (`feat/k1-scheduling-generation-hardening`)  
**Flash this session:** probe @ **`b8cd4ca9`** on `9087A500`.

## Already on silicon / in source

- **On silicon (Main RPL):** `IDENTITY OK: git=b8cd4ca9 env=k1_main_rpl_fps_agc_probe epoch=1787142506`. Probe NON-SHIPPABLE; clock **forced OFF**. **RMT alloc on VP core proven** (`SYSTEM_FPS` ~135–138 with show on).
- **In source:** `α=dt/(τ+dt)` default ON for ship envs; identity-budget packer skip; `K1_RMT_ALLOC_ON_VP_CORE_V1=1` on `k1_main_rpl_im69d` (and the probe). Not on `k1_hardware`.
- Look-without-AP-fix restore remains `k1_main_rpl_im69d` @ **`a6149b29`**.
- I2S0 is the mic; RMT 4×48 FIT; I2S LED **struck**.

## Host gate

- `pytest tests/`: **1421 passed, 1 skipped** (`b8cd4ca9`).
- `pio-build.sh k1_hardware`: SUCCESS.

## Probe decision (on disk)

Show-skip control: [`20260819T-fps-agc-probe-9087/RESULT.md`](../runtime-evidence/20260819T-fps-agc-probe-9087/RESULT.md)  
RMT-on-VP: [`20260819T-rmt-vp-core-9087/RESULT.md`](../runtime-evidence/20260819T-rmt-vp-core-9087/RESULT.md)

| Rule | Number | Verdict |
|---|---|---|
| Show-skip @ `b318a0ec` | ~78 → ~135 | Convicts Core-0 LED-wire *servicing* |
| SYSTEM_FPS with show @ `b8cd4ca9` | **134–138** | Hop recovered; first-show pinning **fixed** |
| gdft_us | 6.1 ms → **1.75 ms** | AP no longer spliced |
| acq_us | 1.5 ms → **3.8 ms** | Healthy I2S wait |
| LED_FPS | 203 → **~163** | Core 1 now owns RMT IRQs; still >100 FPS |

## Remaining ship path

1. **Agent (this commit):** `K1_RMT_ALLOC_ON_VP_CORE_V1=1` on `k1_main_rpl_im69d`.
2. **Agent / Captain:** flash **`k1_main_rpl_im69d`** (clock ON + RMT-on-VP + Lever-2 look) to `9087A500`. Stamp: `IDENTITY OK: git=<that SHA> env=k1_main_rpl_im69d`.
3. **Captain:** eyes-on under **music** (silence gate, sweet-spot, WAVEFORM-family).
4. Honour / `k1_hardware` / F887 / dull-show **#119716** stay separate.

**Close stamp for the AP hole on this unit:** `IDENTITY OK: git=b8cd4ca9 env=k1_main_rpl_fps_agc_probe epoch=1787142506` plus the RMT-on-VP RESULT. Product look+clock is the `k1_main_rpl_im69d` flash above.
