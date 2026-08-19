# FPS / AGC clock — step 5 stamp (2026-08-19)

**Lane:** handover hybrid r1 (`feat/k1-scheduling-generation-hardening`)  
**Flash this session:** `k1_main_rpl_fps_agc_probe` → `9087A500` only @ **`b318a0ec`**.

## Already on silicon / in source

- **On silicon (Main RPL):** `IDENTITY OK: git=b318a0ec env=k1_main_rpl_fps_agc_probe epoch=1787141154`. Probe NON-SHIPPABLE; clock flag **forced OFF**.
- **In source (not this binary):** `α=dt/(τ+dt)` default ON for ship envs (`K1_AGC_DT_CLOCK_V1=1`); identity-budget packer skip; `:show_skip=` routed in `parse_command` like `:vp_perf=`.
- Lever-2 ship restore remains `k1_main_rpl_im69d` @ **`a6149b29`**.
- I2S0 is the mic; RMT 4×48 FIT; I2S LED **struck**.

## Host gate

- `pytest tests/`: **1420 passed, 1 skipped** (commits `dec5fb53` + `b318a0ec`).
- `pio-build.sh k1_hardware`: SUCCESS on those commits.
- Probe env is **not** in the `pio-build.sh` allowlist; flashed via `k1-flash-verified.sh`.

## Probe decision (on disk)

Evidence: [`docs/forensics/runtime-evidence/20260819T-fps-agc-probe-9087/RESULT.md`](../runtime-evidence/20260819T-fps-agc-probe-9087/RESULT.md)

| Rule | Number | Verdict |
|---|---|---|
| `pack_us` | 123 / 146 µs | Cheap; not the AP hole |
| `show_us` | ~2.4 ms avg / 3.6 ms max | **Not** ≳ 9.6 ms — does not convict serialisation |
| `LED_FPS` | ~203 | VP interval ~4.9 ms — consistent |
| Show-skip `SYSTEM_FPS` | **~78 → 132.7–135.9** (mean 134.6) while armed; back to ~76–80 after | **Convicts LED-wire *servicing* (ISR/bus) on Core 0** |

C4 is closed for this unit: the 93-vs-133 hole is AP contention from `show()` servicing, not Lever-2 pack cost and not RMT wire serialisation.

## Remaining ship path

1. **Agent (done):** probe flash + pack/show + armed show-skip series + this stamp + registry §2.
2. **Captain:** named GO to **restore** Lever-2 look (`k1_main_rpl_im69d` @ `a6149b29`) **or** flash clock-fix ship (`k1_main_rpl_im69d` at `dec5fb53`+ lineage — not the probe env).
3. **Captain:** eyes-on under **music** after the clock-fix ship build (follower blast radius: silence gate, sweet-spot, WAVEFORM-family).
4. **Captain (new lane, not this probe):** ISR-core / RMT channel-allocation measurement. I2S LED stays struck. Do not treat this RESULT as a wire-driver swap.
5. **Shipped for this probe step:** `IDENTITY OK: git=b318a0ec env=k1_main_rpl_fps_agc_probe epoch=1787141154` plus `RESULT.md`. Honour / `k1_hardware` / F887 / dull-show **#119716** stay separate. Bench `LED_FPS` remains RPL-only unless a later `B489A500` GO.

**Close stamp for the probe discriminator:** show-skip jump on `9087A500` at `b318a0ec`. Device look restore / clock-fix music eyes-on are the next named GOs.
