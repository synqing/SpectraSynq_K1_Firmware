# K1 Real Music Corpus APCAD Capture

- Generated: `2026-06-15T17:20:09+0800`
- Status: `failed`
- Tuple: `16000/120/d3`
- Profile: `steady_phase`
- Mix policy: `all_musical`
- Source corpus: `/Users/spectrasynq/Workspace_Management/Software/P4-nano/I2S_Audio_Demo-Waveshare_ESP32-P4-NANO/docs/bench/audio-references/p4-local-music-corpus.json`

## Results

| Reference | BPM | Role | AP Hz | NOV Hz | Active P95 us | Active Max us | Failures |
|-----------|-----|------|-------|--------|---------------|---------------|----------|
| `ziggyx-summer-rave-155bpm` | 155.000 | `true_fast_negative` | 104.193 | 34.731 | 10496.0 | 13009.0 | `core_bad_count,active_ap_work_over_7500_count,emitted_active_ap_work_over_7500_count` |
| `subfocus-solarsystem-174bpm` | 174.000 | `true_fast_negative` | 103.964 | 34.655 | 10624.0 | 11648.0 | `core_bad_count,active_ap_work_over_7500_count,emitted_active_ap_work_over_7500_count` |
| `tntrecords-skyfire-151bpm` | 151.000 | `true_fast_negative` | 103.965 | 34.655 | 10624.0 | 11629.0 | `core_bad_count,active_ap_work_over_7500_count,emitted_active_ap_work_over_7500_count` |
| `deadmau5-ghosts-n-stuff-129bpm` | 129.000 | `anchor_neighbourhood` | 103.924 | 34.641 | 10624.0 | 11573.0 | `core_bad_count,active_ap_work_over_7500_count,emitted_active_ap_work_over_7500_count` |
| `martingarrix-animals-128bpm` | 128.000 | `anchor_neighbourhood` | 104.446 | 34.815 | 10368.0 | 11571.0 | `core_bad_count,active_ap_work_over_7500_count,emitted_active_ap_work_over_7500_count` |

## Boundary

- Real P4 musical stems are rendered locally; metronome stems are excluded unless `--mix-policy profile` explicitly selects otherwise.
- This runner does not send calibration, erase, reset, upload, or tuning commands.
- A pass here is a real-music runtime stress gate, not production promotion by itself.
