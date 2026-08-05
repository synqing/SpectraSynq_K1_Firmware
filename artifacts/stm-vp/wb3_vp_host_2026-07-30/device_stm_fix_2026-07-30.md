# Device STM fix (2026-07-30)

## Root cause
`env:k1_hardware_stm` linked `k1_edgemixer.cpp` but did **not** define `-DK1_STM=1`, so serial used `sb_parse_edge_mode` (`Bad command: edge_mode=stm_dual`) and STM never ran on the AP path.

## Fixes
1. `platformio.ini`: `-DK1_STM=1` on `k1_hardware_stm`.
2. `sb_audio_snapshot.cpp`: call `k1_audio_snapshot_update()` each AP frame when `K1_STM`.
3. Serial `:stm_telem=report|reset` for device-side VP capture.

## Verification (main K1 F887A500, `/dev/cu.usbmodem112401`)
- `EDGE_MODE: stm_dual`, `EDGE_STRENGTH: 0.750`, zero bad commands.
- `STM_TELEM: ready=1` with non-zero temporal/spectral during `cal_tone_1khz.wav` playback.
- Log: `device_playback_cal_tone_v2.log`.

H2 VP PASS still **not** claimed (host ref vs native FAIL unchanged).
