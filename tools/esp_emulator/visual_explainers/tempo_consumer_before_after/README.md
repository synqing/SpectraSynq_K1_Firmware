---
abstract: "Raw Motion film of the retained K1 tempo-consumer lock-off captures. Presentation only. It does not rerun tempo or close DEF-002."
---

# Tempo-consumer lock-off explainer

Two retained music-a captures, before and after the lock-off consumer repair, become one 1920×1080, 60 fps film. Both sides use the same sample clock. The scene reads immutable evidence. It does not decode a new emulator run or change cue thresholds.

Pins, checked before a render:

- `eneskirca/raw-motion` `2e96bc3e5b1a3d214578d32338a0c49f73c1311a`
- `eneskirca/raw-motion-skill` `30bd029e63b1e5173a97edff53400d224deaa16c`

The engine checkout is the gitignored `_scratch/raw-motion-toolchain/raw-motion`. This tool refuses a different commit. `scene/motion.js` is copied from that pin at stage time, with its MIT license.

Declared local dependencies, not bundled:

- Node 22 or newer, Google Chrome, and ffmpeg
- `/System/Library/Fonts/Supplemental/Arial.ttf` and `Arial Bold.ttf`
- Fixture `loreen_127` at `/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3` when evidence is rebuilt rather than reused
- The retained capture directories named by `--before` and `--after`

```bash
python3 tools/esp_emulator/visual_explainers/tempo_consumer_before_after/adapt.py export \
  --before _scratch/esp-emulator/tempo-lock-r1/consumer-before \
  --after _scratch/esp-emulator/tempo-lock-r1/consumer-after \
  --output _scratch/esp-emulator/tempo-lock-r1/visual-explainers/<fresh-dir>
```

`--before`, `--after`, and `--output` are required. `--output` must be a fresh directory. The command rebuilds music-a PCM through `tempo_lane_emu.music_a_pcm` and stops unless the 10-second window matches `d5964a5128de2ef2f974418eabdc6b3bdc81ee8c0610f5665c1a1f6bdbdd58bc`. Private PCM stays in that output directory.

A caption-only revision can reuse an already verified evidence directory and copy an existing AAC stream:

```bash
python3 tools/esp_emulator/visual_explainers/tempo_consumer_before_after/adapt.py export \
  --before _scratch/esp-emulator/tempo-lock-r1/consumer-before \
  --after _scratch/esp-emulator/tempo-lock-r1/consumer-after \
  --output _scratch/esp-emulator/tempo-lock-r1/visual-explainers/<fresh-dir> \
  --reuse-from _scratch/esp-emulator/tempo-lock-r1/visual-explainers/<earlier-dir> \
  --copy-audio _scratch/esp-emulator/tempo-lock-r1/visual-explainers/<earlier-dir>/<film>.mp4
```

The film clock is hop-end audio time. Movie time 0 is original 68.000 seconds. A frame is the latest captured hop at or before that time. Published lock on the badge is the captured `c_locked` field. Confidence is shown to four decimal places so 0.5999 is not printed as 0.60. Confidence does not set the lock badge.

| Date | Change |
|---|---|
| 2026-10-24 | Pilot 02. Adapter, scene, and one export command for the retained lock-off pair. |
| 2026-10-24 | Confidence text uses four decimal places. The DEF-002 closeout no longer treats one locked capture as closure. |
