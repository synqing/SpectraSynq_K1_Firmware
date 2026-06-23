# K1 Real Music Corpus APCAD Capture

- Generated: `2026-06-15T14:23:52+0800`
- Status: `passed`
- Tuple: `16000/120/d3`
- Profile: `steady_phase`
- Mix policy: `all_musical`
- Source corpus: `/Users/spectrasynq/Workspace_Management/Software/P4-nano/I2S_Audio_Demo-Waveshare_ESP32-P4-NANO/docs/bench/audio-references/p4-local-music-corpus.json`

## Results

| Reference | BPM | Role | AP Hz | NOV Hz | Active P95 us | Active Max us | Failures |
|-----------|-----|------|-------|--------|---------------|---------------|----------|
| `collapz-the-valhalla-king-143bpm` | 143.000 | `upper_mid_transition` | 133.334 | 44.445 | 7040.0 | 7391.0 | `none` |

## Boundary

- Real P4 musical stems are rendered locally; metronome stems are excluded unless `--mix-policy profile` explicitly selects otherwise.
- This runner does not send calibration, erase, reset, upload, or tuning commands.
- A pass here is a real-music runtime stress gate, not production promotion by itself.
