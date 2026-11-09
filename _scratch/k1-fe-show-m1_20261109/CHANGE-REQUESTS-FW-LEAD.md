---
abstract: "K1-FE-SHOW-M1 Rev 2: firmware change requests for the FW lead, ranked. None implemented by this task (no FE source change). Each item names its source, bench evidence and the smallest change. Owner decides; Captain decides only item 5."
---

# Firmware change requests from K1-FE-SHOW-M1 (9 Nov 2026)

Resident build examined: `ed0aa984` (`k1_fe_bench_b489`, bench K1 B489A500). The PRSM/authored files are byte-identical to `407fdf6f`.

| # | Change | Why (evidence) | Smallest change | Detail |
|---|---|---|---|---|
| 1 | **Stray bytes must never reach hotkeys or `:` command mode while a binary stream is live** | One broken or truncated frame sends payload bytes to the single-byte hotkeys: `N`/`Y` queue noise calibration, `!`–`)` save preset slots, `S` saves show state. Exhaustive test on the real scanner: 110 loss cases queue calibration, 178,135 persist something (Lane B `raw/loss_exposure_cemu_guard0.json`). Emulator with bad-magic frames: 362 flash saves (C-emu `runs/c4-wfh-001/wfh-rej-magic`). The bench used a host-side 30-NUL guard (0 leaks); PRISM.studio `playback.js` has no guard and also sends K1CT frames that FE cannot parse. | Drop non-PRSM bytes while authored is active or within N ms of a broken frame; scanner reset after 20 ms idle; a command-mode abort byte; length + CRC in PRSM v2 | Lane A `lane-a/CR-A3-prsm-hotkey-fallthrough.md`; Lane B `B-P1-contract.md` CR-5 |
| 2 | **Authored mode must drive Waveform Hybrid (and modes 33–37, 18) from the stream only** | Live mic peak is OR-ed in (`light_mode_waveform_hybrid_k1.cpp:116`). Bench: edge position vs stream pressure r = 0.99 silent room, 0.77–0.80 with music in the room; run S3 (room noise) shows the leak. Auto colour shift still runs. | Source the peak from the snapshot only while authored; hold hue drift while authored (~8 lines) | `lane-a/CR-A7-wfhyb-authored-drive.md`; `lane-d/D-P2-receipt.md` |
| 3 | **Read-only `:authored_status`** (state STANDALONE/ACQUIRE/AUTHORED/RECOVERY, last seq, frames accepted/rejected, last arrival ms) | Today authored state, transitions and counters are invisible; the bench proved acceptance only indirectly (edge behaviour, tempo locking at 127 BPM). | ~45 lines, no persistence | `lane-a/CR-A8-authored-status-readout.md` |
| 4 | **Seek handling**: reset effect history on a seq discontinuity; drop duplicate seq | Bench S5: after a backward seek the primary colour changed and stayed; emulator shows history persists. Device accepts any seq gap without reset. | Reset effect-local state on ACQUIRE | Lane B `B-P1-contract.md` CR-2 |
| 5 | **Colour under authored mode (Captain/product decision)** | Chroma is zeroed while authored, so every mode becomes palette-only hue; Prim8 carries no harmony. Under THE LAW colour must track harmony or energy. | Options: map `heat` (Prim8[4], unused today) to palette position, or carry a harmony index in PRSM v2 | Lane A §A7 |
| 6 | **Metadata bug**: `serial_typed_cmd_table.def:141` declares `set_mode` flags 0, but its handler calls `save_config_delayed()` (`serial_cmd_handlers.cpp:1638`); `scripts/regression-harness/k1_serial_safety.py` therefore lists `set_mode` as read-only | Found by Lane A; confirmed by the lead (safety module returns read-only) | Set `CMD_PERSISTS` on the row; regenerate the safety literals | Lane A §A2 |
| 7 | **Registry stale** | `docs/hardware/device-build-registry.md` still records 407fdf6f for B489A500; the device reports `ed0aa984` epoch 1793984825 (6 Nov 17:07 UTC). No image or hash of that build is retained. | Add the row; retain the image | Lane A §A1/§A6 |
| 8 | **Emulator tooling** (emulator owner) | PRSM frames cannot be injected at hop coordinates with existing tools. A prototype RX-record adapter works (20/20 cases). | Adopt `lane-c-emu/PROTOTYPE-ADAPTER-ed0aa984.diff`; hex-escape EMU_HCMD text; add a WS2812 capture tap | C-emu receipt |

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-09 | agent:claude (lead) | Created from Lanes A, B, C-emu and the bench session. |
