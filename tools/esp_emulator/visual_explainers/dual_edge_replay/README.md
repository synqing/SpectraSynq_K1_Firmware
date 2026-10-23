---
abstract: "Raw Motion film of one accepted K1 dual-edge emulator capture. Presentation only. The decoder and the audio rebuild stay in the existing replay tools."
---

# Dual-edge replay explainer

One accepted capture becomes a 1920×1080, 60 fps film: edge A and edge B, the replay sample clock, and the case PCM. The scene reads immutable data. It does not decode UART, rebuild firmware, or invent pixels.

Pins, checked before a render:

- `eneskirca/raw-motion` `2e96bc3e5b1a3d214578d32338a0c49f73c1311a`
- `eneskirca/raw-motion-skill` `30bd029e63b1e5173a97edff53400d224deaa16c`

`scene/motion.js` is that engine's helper, copied with `scene/LICENSE-raw-motion.txt`. The engine checkout lives in the gitignored `_scratch/raw-motion-toolchain/` and is not updated by this tool.

```bash
python3 tools/esp_emulator/visual_explainers/dual_edge_replay/explain.py prepare \
  --run _scratch/esp-emulator/<accepted-run> \
  --output <explicit-output-directory> \
  --case startup-sqr

python3 tools/esp_emulator/visual_explainers/dual_edge_replay/explain.py render \
  --output <explicit-output-directory> --job film-1 \
  --stills 0,2.5,7,8.4,10.2

python3 tools/esp_emulator/visual_explainers/dual_edge_replay/explain.py render \
  --output <explicit-output-directory> --job film-1

python3 tools/esp_emulator/visual_explainers/dual_edge_replay/explain.py mux \
  --frames <explicit-output-directory>/jobs/film-1/frames \
  --wav <explicit-output-directory>/reference.wav \
  --mp4 <explicit-output-directory>/film.mp4
```

`--run` and `--output` are required. A new `--job` name is required because the renderer deletes `frames/` inside the project it is given. Private PCM stays in the output directory, not in this source tree.

The film clock is the case PCM. Sample 0 is movie time 0. The capture's boot epoch is recorded and is not an audio delay. A frame is the latest captured hop whose hop-end is at or before that time. A missing hop is shown as unavailable, not as a held picture.

| Date | Change |
|---|---|
| 2026-10-24 | Pilot 01. Adapter, scene, and entrypoint for an accepted startup-sqr capture. |
