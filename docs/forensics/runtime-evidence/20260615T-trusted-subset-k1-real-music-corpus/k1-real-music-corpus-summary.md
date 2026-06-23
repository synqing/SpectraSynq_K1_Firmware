# K1 Real Music Corpus APCAD Capture

- Generated: `2026-06-15T16:41:18+0800`
- Status: `passed`
- Tuple: `16000/120/d3`
- Profile: `steady_phase`
- Mix policy: `all_musical`
- Source corpus: `/Users/spectrasynq/Workspace_Management/Software/P4-nano/I2S_Audio_Demo-Waveshare_ESP32-P4-NANO/docs/bench/audio-references/p4-local-music-corpus.json`

## Results

| Reference | BPM | Role | AP Hz | NOV Hz | Active P95 us | Active Max us | Failures |
|-----------|-----|------|-------|--------|---------------|---------------|----------|
| `subfocus-solarsystem-174bpm` | 174.000 | `true_fast_negative` | 133.333 | 44.444 | 7040.0 | 7381.0 | `none` |
| `tntrecords-skyfire-151bpm` | 151.000 | `true_fast_negative` | 133.334 | 44.444 | 7040.0 | 7438.0 | `none` |
| `deadmau5-ghosts-n-stuff-129bpm` | 129.000 | `anchor_neighbourhood` | 133.334 | 44.444 | 7040.0 | 7393.0 | `none` |
| `martingarrix-animals-128bpm` | 128.000 | `anchor_neighbourhood` | 133.335 | 44.445 | 7040.0 | 7397.0 | `none` |

## Boundary

- Real P4 musical stems are rendered locally; metronome stems are excluded unless `--mix-policy profile` explicitly selects otherwise.
- This runner does not send calibration, erase, reset, upload, or tuning commands.
- A pass here is a real-music runtime stress gate, not production promotion by itself.
