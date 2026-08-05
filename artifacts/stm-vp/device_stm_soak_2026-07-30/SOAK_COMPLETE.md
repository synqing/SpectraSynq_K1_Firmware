# Device STM telemetry soak — COMPLETE

- **When (UTC):** 2026-07-29T19:37:38Z
- **Device:** main K1 `/dev/cu.usbmodem112401` (`k1_hardware_stm`, `-DK1_STM=1`)
- **Stimulus:** `cal_tone_1khz.wav` via `afplay` (looped through ~44 s audio window within 60 s soak)
- **Harness:** `scripts/regression-harness/device_stm_telem_soak.py`
- **Config:** 8 s pre-silence, 44 s playback window, 8 s post-silence, `:stm_telem=report` every ~0.5 s, `stm_dual` @ 0.75 strength

## Result: **PASS** (device telemetry soak gate — not H2 VP PASS)

| Metric | Value |
|--------|-------|
| STM samples | 121 |
| ready fraction | 1.0 |
| Bad commands | 0 |
| temporal energy (ready) | mean 0.324, p50 0.323, max 0.468 |
| spectral energy (ready) | mean 0.293, p50 0.293, max 0.471 |

## Artefacts
- `device_stm_telem_soak_latest.json` / `.log` (canonical)
- Timestamped twin in same directory
- Mirror: `artifacts/stm-track-b/gate_b_spike_2026-07-29/eval_main_k1_2026-07-30/device_stm_soak/`

Re-run:
```bash
python3 scripts/regression-harness/device_stm_telem_soak.py \
  --port /dev/cu.usbmodem112401 \
  --out-dir artifacts/stm-vp/device_stm_soak_2026-07-30
```
