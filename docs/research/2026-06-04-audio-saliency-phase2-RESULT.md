# Audio Saliency Phase 2 Result

## Files written
- [SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.h](/Users/spectrasynq/SensoryBridge-main%209/SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.h)
- [SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.cpp](/Users/spectrasynq/SensoryBridge-main%209/SPECTRASYNQ_K1_FIRMWARE/audio/sb_musical_saliency.cpp)
- [SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino](/Users/spectrasynq/SensoryBridge-main%209/SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino)
- [scripts/regression-harness/musical_saliency_benchmark.py](/Users/spectrasynq/SensoryBridge-main%209/scripts/regression-harness/musical_saliency_benchmark.py)

## Verification runs
- `pio run -e k1_hardware` => **RED** (environment blocked; PlatformIO could not download platform from github.com in this sandbox)
- `pytest` => **RED** (`pyserial` missing; no tests collected)
- `python3 scripts/regression-harness/musical_saliency_benchmark.py --json` => **RED**

## HarmonixSet salient-event metrics
All thresholds were evaluated on 36 WAVs (default corpus), 70 ms tolerance.

- Precision: **0.2074** (`45/217`), threshold 0.65 => **FAIL**
- Recall: **0.0030** (`45/14908`), threshold 0.45 => **FAIL**
- Music events/min: **18.2829**, window 40-180 => **FAIL**
- Silence events/min: **24.4608**, threshold <12 => **FAIL**

## Field substitution check
No field substitution was required: fork uses the required real fields `chroma_strength`, `novelty`, `spectral_energy`, `beat`, and `beat_confidence` directly.

## Behavioural impact note
No existing runtime cadence/path was changed besides additive saliency production in AP loop after `sb_audio_snapshot_update()` and before tempo consumer calls; no commit was made.
