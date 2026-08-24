# K1 Audio Contract (v2)

This contract is lifted from `audio/k1_audio_snapshot.h` and the adapter surface in
`effects/framework/K1AudioContext.h`.

## 1) Snapshot payload

### `K1AudioSnapshot`
- `frame_ms` (`uint32_t`) frame timestamp
- `peak_scaled` (`float`) peak envelope
- `vu_level` (`float`) overall level
- `novelty` (`float`) novelty proxy
- `spectral_energy` (`float`)
- `low_energy` (`float`)
- `mid_energy` (`float`)
- `high_energy` (`float`)
- `chroma_strength` (`float`)
- `silence` (`bool`)
- `K1_ONSET_V2` conditional fields:
  - `nyquist_safe_bin_hi` (`uint8_t`)
  - `spectrum[80]` (`float[80]`) per-note magnitude spectrum
- `K1_CHORD_V2` conditional fields:
  - `chroma_pc[12]` (`float[12]`) A-origin pitch classes
  - `chord` (`K1ChordState`)

### `K1OnsetBeatEvent`
- `event_id` (`uint32_t`)
- `event_ms` (`uint32_t`)
- `event_age_ms` (`uint32_t`)
- `onset_strength` (`float`)
- `bass_onset_strength` (`float`)
- `beat_phase` (`float`)
- `beat_confidence` (`float`)
- `onset` (`bool`)
- `bass_onset` (`bool`)
- `beat` (`bool`)
- `K1_ONSET_V2` conditional fields:
  - `transient`, `kick`, `snare`, `hihat` (`bool`)
  - `transient_strength`, `kick_strength`, `snare_strength`, `hihat_strength` (`float`)
  - `transient_level`, `kick_level`, `snare_level`, `hihat_level` (`float`)
  - `transient_event_id`, `kick_event_id`, `snare_event_id`, `hihat_event_id` (`uint32_t`)

## 2) Contract API

- `k1_audio_snapshot_publish(const K1AudioSnapshot& next)`
- `k1_audio_snapshot_read()`
- `k1_audio_snapshot_update(uint32_t frame_ms)` (producer-side scheduler input)

Lane B should expose equivalent read-only projection in a portable core module.

## 3) Accessor projection used by effects

The following projection shape mirrors `K1AudioContext`:
- `rms()`, `peak()`, `flux()`, `spectralEnergy()`
- `getBand(0..7)` with 80-bin fold into 8 bands, otherwise fallback to low/mid/high
- `bass()`, `mid()`, `treble()`
- `beatPhase()`, `beatConfidence()`, `isOnBeat()`, `hasOnset()`, `onsetStrength()`, `bassOnsetStrength()`
- `isKickHit()`, `isSnareHit()`, `isHihatHit()`, `kickLevel()`, `snareLevel()`, `hihatLevel()`
- `getChroma(label)`, `chromaStrength()`
- `hasChord()`, `isMinor()`, `isMajor()`, `isDiminished()`, `isAugmented()`, `chordRoot()`, `rootStrength()`, `thirdStrength()`, `fifthStrength()`
- `available()` indicates both snapshot and onset event are bound and `silence == false`

## 4) Chromatic mapping notes

- Chroma source in snapshot is A-origin (`chroma_pc[0] = A`).
- Effects expect C-origin labels.
- Current bridge mapping:
  - `getChroma(label)` maps C-origin label to A-origin index with +3 rotation.
  - `rootNote()` reverse map is +9 rotation.

These are inverse mappings in mod-12 and must remain paired.

## 5) Host/CI compatibility

- This contract is intentionally host compilable where possible.
- Build flags (`K1_ONSET_V2`, `K1_CHORD_V2`) preserve no-flag byte shape with additive fields.
