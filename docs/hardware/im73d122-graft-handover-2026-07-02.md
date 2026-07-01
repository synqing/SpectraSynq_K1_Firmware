---
abstract: "Session handover for the IM73D122 PDM mic graft into the K1 audio front-end (flag K1_MIC_IM73D_PDM_V1, bench B489A500 only). Graft is DONE, committed (lane/im73d-pdm-eval: 545d331 + c3584fa), host-gated GREEN (pytest 619, clean compile, flag-OFF byte-identity), and DEVICE-PROVEN end-to-end on silicon (boot -> PDM read on live AP+VP -> silence-go recal cal_valid=1 -> no NaN). Gain characterized g=16 (loud max_raw ~4339 in the SPH 4k-10k band, non-railed). REMAINING: per-band AGC telemetry (stream_agc, 4 gains <10) + Captain eyes-on A/B. SPH0645 stays the byte-identical product default; no default flip. Read before touching the IM73D lane."
---

# IM73D122 PDM graft — session handover (2026-07-02)

## TL;DR
The IM73D122 PDM microphone is grafted into the K1 production audio front-end behind `K1_MIC_IM73D_PDM_V1`, **bench-only** (`B489A500`). It is **DONE, committed, host-gated green, and device-proven end-to-end**. Two acceptance items remain (per-band AGC telemetry + Captain eyes-on). The SPH0645 (`i2s_std`) is **byte-identically preserved** as the product default when the flag is OFF.

## Branch & commits
- Branch: **`lane/im73d-pdm-eval`** (off `26eebb1`).
- `545d331` — the graft (all 11 spec points).
- `c3584fa` — bench-characterized `K1_MIC_IM73D_INPUT_GAIN 3.0 -> 16.0`.

## Authoritative spec / design
- **Execution spec (approved):** `~/.claude/plans/execute-the-im73d-graft-generic-journal.md` — Captain's final 11-point source-verified amendment set. This is the contract; every commit maps to it.
- **Canonical design:** `docs/hardware/im73d122-ap-vp-migration-plan.md` (round-2, red-teamed).
- **Probe evidence / tooling:** `_scratch/im73d_bringup/` (`read_serial.py` = safe DTR/RTS-low reader).

## Files changed (all flag-gated `#ifdef K1_MIC_IM73D_PDM_V1 … #else … #endif`)
| File | What |
|---|---|
| `platformio.ini` | `[env:k1_bench_im73d]` extends `k1_bench_reference` + **only** `-DK1_MIC_IM73D_PDM_V1` |
| `scripts/platformio/k1_upload_guard.py` (+ `tests/test_k1_upload_guard.py`) | env registered in the `B489A500` tuple (unknown envs fail-OPEN); same-port/main-port/drift tests |
| `system/constants.h` | `K1_PDM_*` pins (clk13/din12/LR14); `NOISE_CAL_SSL_BOOT_FALLBACK_RAW`→120; `K1_MIC_IM73D_INPUT_GAIN` 16.0f |
| `system/globals.h` | `im73d_samples_i16[1024]` DRAM buffer; `calibration_profile_valid()` drops `DC!=0` term under flag |
| `system/system.h` | boot force-invalidate **before both** repair blocks; Block-1 `DC==0` legal under flag |
| `audio/i2s_audio.h` | PDM init (assign existing `result`), int16 read (both freeze-guard + portMAX), `dump_raw` int16, extraction gain, **follower/NaN guard** before the peak-scaled division |
| `calibration/noise_cal.h` | failed-cal-restore + `clear_noise_cal` set `SSL=fallback` (never 0) + seed follower |
| `persistence/bridge_fs.h` | function-level NVS freeze; **`save_calibration_profile` = RAM-only SEMANTIC SUCCESS** (not `return false`) |

## Gates — all GREEN
- **pytest 619 pass** / 1 skip (incl. guard drift-catcher).
- **`pio run -e k1_bench_im73d`** clean (RAM 32.8% / Flash 9.8%).
- **flag-OFF byte-identity PROVEN** for `k1_hardware` AND `k1_bench_reference`: identical section **sizes** (396204 / 161012), identical `.dram0/.iram0` SHAs; `.flash.text`/`.rodata` SHA churn is **only** `K1_BUILD_EPOCH` (proven by clean-vs-clean determinism test — two identical-source builds differ the same way). Zero `__LINE__`/`assert` in the tree, so inserted lines shift nothing. → No functional leak.

## Device proof (bench `B489A500`, on silicon)
- Boots, **PDM RX reads the mic on the LIVE AP+VP**: `onset`/`bass`/`bpm` firing, `lock=1` achieved.
- Boot force-invalidate: `SSL=120 DC=0`, **no NaN** in `peak_scaled` at cold-boot/invalid-cal.
- **Gain g=16 device-proven in-band:** loud `max_raw` ~**4339** (SPH 4k–10k band), `clip_pct=near_pct=0.000` (non-railed, ~6× headroom).
- **Silence-go recal PASSED:** `NOISE CAL ACCEPTED`, `cal_source=measured cal_valid=1 cal_reason=none SSL=710 DC=-13`. → proves the load-bearing **`save_calibration_profile` RAM-only semantic success** (a bare `return false` would leave `cal_valid=0` forever).
- **Failed-cal path proven:** first attempt `ssl_too_loud` → restored `SSL=120` (fallback, **not 0**), no NaN → the SSL-never-0 + NaN-guard invariant works.

## Hard-won gotchas (READ — these cost real time)
1. **Device I/O is human-in-the-loop.** Scripted serial opens (`read_serial.py`, inline pyserial) intermittently reset the board into **download mode** (esp. right after a flash), and can't send commands. **Captain's interactive `pio device monitor` is the reliable path** — don't script captures; ask Captain to run/paste. The mic itself is fine; this is a tooling/reset-circuit reality on the native USB-Serial-JTAG.
2. **RAM-only cal.** NVS is frozen under the flag, and **every serial-open/reset re-runs the boot force-invalidate** → `cal_valid=0`, `SSL=120`. So a fresh **silence-go recal is needed each power-up**. This is by design (SPH0645 profile on disk untouchable).
3. **`g=16` is near the UPPER practical limit.** Loud lands in-band (4339, low end) AND silence cals to `SSL=710` (top of the valid `[50,720]`). Going higher (g≥22) pushes the silence floor past 720 → `ssl_too_loud` cal failure. **Do NOT bump the gain.** If eyes-on wants more brightness, the plan's flag-gated SSL-window-widen fallback is the bounded escalation — not a gain bump.
4. **`start_noise_cal` = `N` (arm) → `Y` (confirm) within 5 s, under confirmed silence.** NEVER auto-fire; wait for Captain's verbal "silence, go", then "resume".
5. **Identity by MAC, never port.** Ports drift. Bench `B489A500` was on `usbmodem1101`; main K1 `F887A500` on `usbmodem2101` (this session). Verify USB `serial_number` == MAC via `pio device list` before ANY write. Main K1 is **production — read-only, and even a read-open can wedge it into download (power-cycle to recover).**
6. **Byte-identity ≠ raw `sha256(firmware.bin)`.** `K1_BUILD_EPOCH` (wall-clock, `k1_build_provenance.py`) churns `.text`/`.rodata` every build. Use section **sizes** + `.dram0`/`.iram0` SHAs, or `registry_byte_gate.sh` (k1_hardware only).
7. **The primary-channel-dead symptom was HARDWARE** (bench mic-swap rework disturbed the primary LED wiring on GPIO4), **not the graft** — confirmed by secondary-works-primary-doesn't (shared audio drive => graft exonerated) and **fixed by Captain**. If it recurs: check GPIO4 data wiring, not firmware.

## Remaining acceptance (both need Captain)
1. **Per-band AGC:** Captain types `:stream_agc` in the monitor under music → confirm all four `gain:g0,g1,g2,g3 < 10` (broadband `agc_gain` was ~0.35, so starvation is unlikely). This is the anti-washed-colour gate; `[AP]` band-0-only is a forbidden sole source.
2. **Eyes-on A/B** vs SPH0645 across genres incl. VU modes (Sensory Bridge doctrine gate; telemetry-green does not close it). Note the cross-unit caveat: gain target came from the SPH's documented 4k–10k band (`i2s_audio.h:26`), not a same-board capture.

## Housekeeping TODO
- Update `docs/hardware/device-build-registry.md` deployed-state row: bench `B489A500` now on `k1_bench_im73d @ c3584fa` (gain=16), recal-provable `cal_valid=1`.
- (Optional) point `.claude/handoff.md` at this file.

## Rollback
- **Restore bench to SPH-reference:** `pio run -e k1_bench_reference -t upload --upload-port <verified B489A500 port>` (reads the physically-installed IM73D as garbage but LEDs render; NVS was never touched under the flag). Fresh silence-go recal after.
- **Full code revert:** delete `[env:k1_bench_im73d]` + its guard tuple line; the `#ifdef` blocks are inert with the flag undefined (`k1_hardware`/`k1_bench_reference` already byte-identical).

## Product decision (not this lane)
Whether the K1 product moves SPH0645 → IM73D122 is a **separate, later, Captain-gated** decision after eyes-on. Until then the flag stays bench-only and SPH0645 is the shipping default (`default_envs=k1_hardware`, unchanged).

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-02 | agent:claude-code | Created: session handover for the IM73D122 PDM graft — implemented (11-point spec), committed, host-gated, device-proven end-to-end; gain g=16 characterized; remaining = per-band AGC + eyes-on; primary-channel issue was bench hardware (fixed). |
