# K1 Real Music Corpus APCAD Capture

- Generated: `2026-06-15T14:51:58+0800`
- Status: `failed`
- Tuple: `16000/120/d3`
- Profile: `steady_phase`
- Mix policy: `all_musical`
- Source corpus: `/Users/spectrasynq/Workspace_Management/Software/P4-nano/I2S_Audio_Demo-Waveshare_ESP32-P4-NANO/docs/bench/audio-references/p4-local-music-corpus.json`

## Results

| Reference | BPM | Role | AP Hz | NOV Hz | Active P95 us | Active Max us | Failures |
|-----------|-----|------|-------|--------|---------------|---------------|----------|
| `arminvanbuuren-sonicsamba-142bpm` | 142.000 | `upper_mid_transition` | 133.337 | 44.445 | 7040.0 | 7369.0 | `none` |
| `avicii-levels-126bpm` | 126.000 | `anchor_neighbourhood` | 133.334 | 44.444 | 7040.0 | 7397.0 | `none` |
| `brennanheart-jonathanmendelsohn-imaginary-150bpm` | 150.000 | `true_fast_negative` | 133.332 | 44.444 | 7040.0 | 7369.0 | `none` |
| `charlottedewitte-sgadilimi-135bpm` | 135.000 | `upper_mid_transition` | 133.334 | 44.445 | 7040.0 | 7398.0 | `none` |
| `collapz-the-valhalla-king-143bpm` | 143.000 | `upper_mid_transition` | 133.334 | 44.445 | 7040.0 | 7420.0 | `none` |
| `djkuba-neitanxravekings-renaissance-138bpm` | 138.000 | `upper_mid_transition` | 133.335 | 44.444 | 7040.0 | 7400.0 | `none` |
| `davidguettamorten-dreams-128bpm` | 128.000 | `anchor_neighbourhood` | 133.333 | 44.444 | 7040.0 | 7371.0 | `none` |
| `eric-clapton-wonderful-tonight-95bpm` | 95.000 | `low_mid_tempo_reference` | 133.335 | 44.445 | 7040.0 | 7376.0 | `none` |
| `fisher-losingit-125bpm` | 125.000 | `anchor_neighbourhood` | 133.334 | 44.444 | 7040.0 | 7458.0 | `none` |
| `hi-lo-poseidon-127bpm` | 127.000 | `anchor_neighbourhood` | 133.334 | 44.444 | 7040.0 | 7410.0 | `none` |
| `i-malive-125bpm` | 125.000 | `anchor_neighbourhood` | 133.334 | 44.445 | 7040.0 | 7371.0 | `none` |
| `kato-jon-turnthelightsoff-137bpm` | 137.000 | `upper_mid_transition` | 133.333 | 44.444 | 7040.0 | 7376.0 | `none` |
| `lavern-inmymind-130bpm` | 130.000 | `anchor_neighbourhood` | 133.335 | 44.444 | 7168.0 | 7404.0 | `none` |
| `maddix-activating-130bpm` | 130.000 | `anchor_neighbourhood` | 133.333 | 44.445 | 7040.0 | 7393.0 | `none` |
| `martingarrix-animals-128bpm` | 128.000 | `anchor_neighbourhood` | n/a | n/a | n/a | n/a | `capture_command_failed` |

## Boundary

- Real P4 musical stems are rendered locally; metronome stems are excluded unless `--mix-policy profile` explicitly selects otherwise.
- This runner does not send calibration, erase, reset, upload, or tuning commands.
- A pass here is a real-music runtime stress gate, not production promotion by itself.
