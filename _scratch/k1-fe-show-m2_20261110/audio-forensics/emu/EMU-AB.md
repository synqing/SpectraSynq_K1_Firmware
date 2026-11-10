---
abstract: "Loud guard ON vs OFF on firmware a6bad318, ESP32-S3 emulator, Main RPL (k1_main_rpl_emu), live mic PCM only. PARTIAL (checkpoint): first pair room level / mode 32 done end to end; the rest of the 2x2x3 matrix is running."
---

# Loud guard ON vs OFF in the emulator (af-emu, 10 Nov 2026)

STATUS: PARTIAL CHECKPOINT. One pair (room level, mode 32) is complete. The other 10 cases and the
determinism repeat are running (`runs/rest`).

## Checkpoint result (room level, mode 32, both edges)

- [FACT] Both cases accepted by `emu_capture.accept` (run.py status PASS), 2000 frames each, all
  frames mode 32, every scheduled command `rejected=0`, no `EMU_REJECT`.
- [FACT] Guard OFF changed the output: 2000/2000 frames differ on both edges from the first
  captured hop (1600).
- [FACT] Guard OFF made both edges dimmer, not brighter: edge A mean 0.039 -> 0.026, edge B
  0.043 -> 0.027 of full scale; motion 0.035 -> 0.023 (A), 0.038 -> 0.024 (B); dynamic range
  0.066 -> 0.037 (A), 0.061 -> 0.034 (B).
- [FACT] In mode 32 the light does not follow the loudness in either setting: brightness vs
  per-hop RMS r = -0.32 (ON) / -0.39 (OFF) on edge A; the quiet section (137-143 s) is as bright
  or brighter than the loud chorus (loud/quiet 0.72 ON, 0.61 OFF).
- [FACT] At room level the time-domain normaliser is identical ON and OFF (waveform_peak_scaled
  mean 0.681, >= 0.92 on 20.8 % of frames in both), as expected: the input never nears the clip
  point, so the guard's input trim stays at 1 and only its spectrum-side actions (GDFT trim,
  floor cut, colour unpin) differ.

Plot: `analysis-checkpoint/plot-m32-room.png`.
