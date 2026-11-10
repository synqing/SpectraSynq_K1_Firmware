---
abstract: "Lane D receipt, K1-FE-SHOW-M1 Rev 2, 9 Nov 2026 (AWST), corrected 10 Nov after external review. One bench session on bench K1 B489A500 (resident ed0aa984, k1_fe_bench_b489). T2 = PARTIAL: an offline-prepared stream (not yet a PRISM-compiled show) influences the renderer; rejected input has no effect; stop returns to live; 30 reported settings restored. Not met: seek reconstruction (fails), independence from room sound, colour behaviour, receiver isolation, native secondary-edge capture, A06 timing. No flash, reset or erase."
---

# Lane D — real K1 bench session (T2 = M1)

## Corrections, 10 Nov 2026 (external review accepted; these override anything below)
- **The compiler proof and the music-stream proof are separate.** The verified PRISM compile (Lane C-spine) is the 3 s `ci_click_3s` fixture. The 80 s stream sent to the K1 came from `lane-c-emu/stream/make_stream.py` (offline loudness, onset and band analysis), as its sidecar `source` field records. This session tested prepared-input playback; it did NOT demonstrate recording → PRISM composition → compiler → device. That chain is M2 (`_scratch/k1-fe-show-m2_20261110/`).
- **Seek is a FAILURE, not an observation.** After the backward seek the primary colour changed and stayed; the same musical position reached by continuous play would not show that colour. This fails the repeatability requirement; the firmware fix (reconstruction on seek) is in the M1 corrective scope.
- **Audible seek not proven.** S5 was a no-audio run. The player's `Audio.seek()` did not flush queued audio; fixed 10 Nov (abort + restart of the output stream; pty test `lane-c-emu/runs/c5-seek-flush-review`), but audio held inside the Bluetooth speaker itself is beyond the player's control, and heard-audio-versus-light agreement after a seek is still untested.
- **"Deterministic on both edges" is not established.** Only the primary edge has native-data capture; physical comparisons are correlations, not identical output; the secondary edge is footage only.
- **Settings restore covers the 30 reported `CONFIG.*` values only**, not every stored or hidden state (presets, show state and edge-mixer RAM were not read back; no watchdog line indicated they changed).
- **"Zero leaks" under the guard means zero shortcut/command-mode bytes, not zero garbage frames:** 249,394 of 614,336 simulated guarded loss events still accept one garbage frame (`lane-b/raw/loss_exposure_cemu_guard30.json`, `outcome_counts.garbage_frame_accepted`). The guard also assumes one 64-byte write = one USB packet (unmeasured), and the preamble's newline can execute a command line left pending by an earlier writer. The receiver must be fixed; the guard is a mitigation.
- **Output latency figure:** the post-fix music runs report 183.5 ms (`os_output_latency_s`), the aborted run 161.7 ms. Neither is an acoustic measurement; any calibration must use the configuration actually played.
- **Audio-fix verification upgraded:** the output-underflow counter missed the stutter (it read 0 in the aborted run). Heard audio was re-checked from the a7S III microphone recording of each run: stutter-shaped holes (≥15 dB below the local 1 s median for 20–200 ms) inside the logged playback window — aborted run 21 holes in 65 s; M0–M4 0 holes in 65–69 s each (`analysis/audio_continuity.json`, `audio_continuity.py`). The remaining busy-wait in the player was removed 10 Nov (sleep-only pacing).
- **Player validation, 10 Nov (playback reliability only — says nothing about audio-to-light timing):**
  - Output device: "Bose Mini II SoundLink", Bluetooth, 44,100 Hz, 2 channels (system default; not changed). The Bose is ALSO the system default INPUT (16 kHz headset microphone); opening it would switch the speaker to telephone mode, so no tool opens it. Telephone mode was ruled out for the stutter: the stutter recording has MORE energy above 8 kHz than the good runs (0.047 vs 0.023–0.026 of the 1–8 kHz energy), consistent with dropout clicks, not a narrow-band link.
  - Cause, from a factorial on the Bose with silent output, 20 s each (`analysis/audio_probe/bose_*.json`): 64-frame "low" buffers alone 0.01% late callbacks; + video-encode load 0.01%; + the old busy-wait spin 4.4%; spin + load 7.8% (max interval 3.7–11.6 ms vs 1.45 ms buffers); 4,096-frame buffers 0 late with or without spin and load. The output-underflow flag stayed 0 in every case, so it cannot detect this. Conclusion: the spin starving the 64-frame callback is the reproduced trigger; load alone is not material.
  - Not reproduced inaudibly: on a digital loopback (BlackHole, sample-exact after one fitted gain of 0.158 = its device volume) even the 64-frame + spin + load case showed no mid-stream sample errors — the loopback driver absorbs a few ms of lateness. The audible holes on the Bluetooth path are shown only by the original room recording (21 holes). The faulty configuration was deliberately not replayed audibly.
  - Short audible check through the Bose at current volume, MacBook microphone (not the Bose microphone), 13 s analysed each: fixed player configuration (4,096 frames, no spin, encode load) 0 stutter holes; macOS `afplay` reference 0 holes; music 27–29 dB above the room floor, levels within 0.8 dB (`analysis/audio_probe/audible_check.json`, `mic_player_4096.wav`, `mic_afplay.wav`). `afplay` cannot give the speaker-clock mapping the stream pacing needs, so the fixed player stays the bench path with `afplay` as the reference.
- **Watchdog policy changed:** calibration activity (`NOISE_CAL: armed / not armed`, including in the first line after the port opens) now ENDS the session after a 5.5 s write hold (exit 5); the player no longer resumes the same stream. Tested on the pty (`runs/c5-wd-isolation-first`: 0 frames sent; `runs/c5-wd-isolation-mid`: stopped, no resume). `lane-d/silent_stream.py` given the same first-line check.
- **A06 is not the only remaining item, and it must not block M2.** Remaining for M1: receiver isolation, prepared-source isolation on both edges, seek reconstruction, deterministic colour start, applied-state observation, two-edge capture, then a physical rerun. A06 measurement routes using existing equipment: see `A06-MEASUREMENT-ROUTES` section at the end of this file.

Lead: Claude (K1-FE-SHOW-M1 lead session). Bench slot approved by Captain 9 Nov ("Tonight, once ready"; both conditions; a7S III footage).
All raw material: `lane-d/runs/<run>/` (run.json, LED capture `dump.txt` + CRC-checked `dump.npz(.json)`, sender/player logs, device-output logs, `a7s3.mp4` footage with camera sound). Analysis: `lane-d/analysis/`.

## Problems first
- **A06 fine timing: BLOCKED.** No common-clock audio + light sensor exists (scheduling audit inventory: "Missing", `docs/forensics/2026-08-15-freertos-scheduling-audit/evidence/gate0-harness-inventory.md:36`). The a7S III USB stream is 1280×720 at 25 fps (40 ms frames) — coarse evidence only. M1 is therefore **PARTIAL, not complete**.
- **Live microphone leaks into the prepared show (Waveform Hybrid, mode 32).** Edge position vs stream pressure: r = 0.99 in a silent room, 0.77–0.80 with the music playing in the room. Run S3 (room noise: device mic RMS up to 0.020 vs 0.002–0.003) shows the same leak. Source cause verified (`light_mode_waveform_hybrid_k1.cpp:116` at ed0aa984: `fmaxf(snap.peak_scaled, waveform_peak_scaled)`). Fix = FW-lead change request CR-A7.
- **Colour is palette-only under the stream** (chroma zeroed by design, `.ino` ~1597 at ed0aa984): one flat magenta on the primary edge; live runs show chroma-driven colour hits (yellow/orange at the breakdown). Under THE LAW (colour tracks harmony or energy) this is a regression while authored; Prim8 carries no harmony channel today.
- **Seek leaves effect history:** after the backward seek (S5, 45 s → 30 s) the primary colour changed magenta → yellow and stayed. Observation, not root-caused; consistent with Lane B CR-2 (seek does not reset effect history).
- **Audio stutter on the first music attempt (Captain heard it).** Cause: the player used 64-frame CoreAudio buffers on the Bluetooth speaker with a Python callback, and its pacing loop spun while holding the interpreter lock; 3,200-frame spans took up to 112 ms instead of 73 ms (`runs/X_M0_aborted_audio_stutter/player.jsonl`). Fixed by the lead in `lane-c-emu/player/show_player.py` (4,096-frame buffers, `latency="high"`, no spin). Verified under full load before any audible replay (S6: consumption 44,100 Hz at p1 and p99 of every 4.6 s window, send error p95 2.0 ms) and in all five music runs (44,099–44,101 Hz). The aborted run is kept as evidence and not used.
- **One LED dump lost 14 of 2,842 lines in transfer (S1)**; parsed by index, CRC not verifiable for that run; the dump tool now re-dumps once on a CRC failure. All other captures CRC-verified.
- **Second (secondary) edge is footage-only.** The bench build's LED capture records the primary edge only (`k1_render_trace.cpp:117–118`, no `K1_RTRACE_DUAL`).

## Identity and restoration (D0, D5)
| Check | Result | Evidence |
|---|---|---|
| USB identity | `B4:3A:45:A5:89:B4` (USB serial) = B489A500 on `/dev/cu.usbmodem11301` | ioreg; every tool refuses any other serial |
| Resident build | `BUILD: version=40103 git=ed0aa984 epoch=1793984825 env=k1_fe_bench_b489`; `CHIP ID: B489A500` | `raw/D0_build_20261109T114342Z.txt`, `raw/D0_ident_1257/ident.txt`, after: `raw/D5_ident_after/ident.txt` |
| Registry | STALE (records 407fdf6f / 8accab34) — not a device mismatch: same chip, same FE bench env, PRSM files byte-identical between 407fdf6f and ed0aa984 (Lane B) | Lane A §A1 |
| PRSM path present in resident image | YES, behaviourally: device accepted 9,600-frame streams (edge driven; device tempo locked at 126–127 BPM = track tempo, vs 61–86 BPM wandering for rejected frames) | `runs/S1..S3/stream.jsonl.device.jsonl` [AP] lines |
| Session changes | `:set_mode=32` (persists via `save_config_delayed`), later `:set_mode=22`; `:ap_stream=0/1` around dumps (RAM only); `:rtrace_arm/_dump` (RAM) | `raw/D_setmode32.txt`, `raw/D5_setmode22.txt` |
| Restoration | All 30 `CONFIG.*` lines identical to session start (diff empty); mode 22; telemetry on; post-restore silent capture mean brightness 8.3 vs 7.1 at start | `raw/D5_ident_after/`, `runs/D5_restore_live_silent_m22/` |
| Flash / reset / erase | none | — |
| Watchdog incidents | 0 in every run (no NOISE_CAL, save, slot or command-mode reply) | `*/stream.jsonl`, `*/player.jsonl` |

## Runs (primary edge mode 32 unless stated; stream = `lane-c-emu/stream/loreen_75_155_120hz_v2.prsm` sha256 `eafb72ae…58fdd`, 9,600 frames at 120 Hz, Loreen 75–155 s, transition 137 s)
Metric: luma-weighted distance of light from the strip centre (Waveform Hybrid shows energy as position), Pearson r against stream pressure after ONE fixed offset per run.

| Run | Condition | Frames sent | LED capture | r(position, pressure) |
|---|---|---|---|---|
| S0_live_silent | mode 22, live, silent room | — | 843, CRC ok | — |
| S0_m32_live_silent | live, silent room (20 s) | — | 808, CRC ok | 0.15 (max over offsets) |
| S1/S2/S3_m32_authored_silent | stream, no audio, silent room | 9,600 each, send p95 ≤0.008 ms | 2,828 (14 lost) / 2,773 / 2,757 | **0.989 / 0.991 / 0.962** (S3 room noise) |
| S4_m32_rejected_hz0_silent | every frame hz=0 | 9,600 | 2,867, CRC ok | 0.19 — no effect |
| S5_m32_seek_stop_silent | seek 25→35 s, 45→30 s, stop at 60 s | 7,200, 2 epochs | 2,153, CRC ok | seeks visible at the jump; live behaviour after stop |
| S6_m32_authored_silentaudio_fixcheck | player, all-zero audio to the speaker | 9,600, p95 2.0 ms | CRC ok | 0.959 |
| M0_m32_live_music | music on Bose, current volume, live | (audio only) | 2,648, CRC ok | 0.25 |
| M1/M2/M3_m32_authored_music | music + stream (audio-clock paced) | 9,597 / 9,600 / 9,600, p95 ≤2.0 ms | CRC ok ×3 | **0.773 / 0.768 / 0.798** |
| M4_m32_rejected_hz0_music | music + hz=0 frames | 9,595 | 2,651, CRC ok | 0.26 — same as live |
| X_M0_aborted_audio_stutter | first music attempt, stopped | — | — | not used |

Repeatability (position series, run vs run, `analysis/pairwise_spread_r.json`): S1~S2 0.992; M1~M2 0.992, M1~M3 0.931, M2~M3 0.935. The two live-driven music runs agree only 0.548 (M0~M4).

Pictures (read by the lead): `analysis/keogram_silent_m32.png`, `analysis/keogram_music_m32.png`, `analysis/keogram_silent_seek_rejected.png` (time × LED index, real captured colour); footage contact sheet `analysis/S2_contact.png` (both edges: dark before, lit at the ends in the chorus, reaching inward at the 137 s breakdown, dark after).

## Test verdicts
- **T1 (transport smoke): NOT RUN** (optional). Note: `set_mode` and palette commands persist to flash, so a timed T1 cue list would write flash (Lane A §A3).
- **T2 (M1): PARTIAL.** Met: prepared stream influences the renderer (primary edge measured; secondary edge footage, coarse); repeats correlate 0.93–0.99 (not identical output); rejected input (hz=0) has no effect in both conditions; stop returns to live without freeze or stale replay; the 30 reported settings restored. Not met (corrected 10 Nov): seek reconstruction FAILS (colour state persists after a backward seek); prepared output is not independent of room sound (CR-A7); colour behaviour under the stream undiagnosed; receiver isolation unfixed; secondary edge not natively captured; A06 BLOCKED.
- **T3 (M2): NOT RUN** (out of scope). Unobstructed; see C-spine receipt for the compiler pin mismatch.

## Timing statements (coarse only)
Host send error vs schedule p95 ≈2.0 ms (player, audio-clock paced) — host-side, not presentation timing. Player maps frames to the speaker's reported output time (`outputBufferDacTime`; the Bose reported 183.5 ms in the post-fix runs and 161.7 ms in the aborted run — not independently measured). Device uses arrival time; no device-side timestamp of application exists without CR-A8. Emulator recovery (52.5 ms) is lockstep, not physical.

## A06-MEASUREMENT-ROUTES (10 Nov; desk analysis, nothing measured yet)
Three measurements stay separate: host send error (have it: p95 ≈2 ms); device application/output time (needs firmware observation — the corrected CR 3 asks for the applied sequence and its render frame time, not just arrivals); heard sound versus emitted light (A06 itself, needs ≤5 ms uncertainty, A08).

| Route | Equipment | What it measures | Uncertainty (estimate, to be validated) | Status |
|---|---|---|---|---|
| R1 | a7S III internal recording, 4K 120p with in-camera audio (one file, one clock) | heard sound (camera mic) vs light, end to end | ±4.2 ms frame quantisation per event, plus the camera's own audio–video offset, which must be calibrated with a reference event (e.g. repeated clapper closures, mean of ≥20) | equipment present; needs the camera set to internal 120p recording and the card files handed over (Captain physical action) |
| R2 | iPhone 13 Pro ("EiP", iPhone14,2) slow-motion 240 fps with audio | same as R1 | ±2.1 ms frame quantisation, plus calibrated audio–video offset of the slow-motion file (unknown; same clapper calibration) | equipment present; Captain records; best existing-equipment candidate |
| R3 | photodiode on the plate + microphone or line tap into one logic analyser / oscilloscope | same, at sub-millisecond resolution | <1 ms | inventory UNCONFIRMED: an oscilloscope appears once in `docs/forensics/ws2816-degamma-audit-2026-08-18/S2-chip-truth.md:333`; no analyser or photodiode on USB today. Ask the Captain what exists; buy nothing. |
| R4 | device timestamps (corrected CR 3) + player audio-clock log | data application time on the device, not light | ~1 ms on the device clock; still needs one optical route to anchor | needs the firmware change |
| — | a7S III USB stream (used 9 Nov) | coarse composition only | 40 ms frames | not adequate for A06 |

A06 does not block M2 host-side work. It gates only the physical M1 completion claim.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (lead) | External review accepted: corrections section added at the top, verdicts and latency figure corrected, audio continuity re-verified from camera audio, player busy-wait removed, watchdog now stops on calibration activity, audio seek flush, A06 routes inventoried. |
| 2026-11-09 | agent:claude (lead, Lane D) | Created after the bench session; all runs, restoration and findings recorded. |
