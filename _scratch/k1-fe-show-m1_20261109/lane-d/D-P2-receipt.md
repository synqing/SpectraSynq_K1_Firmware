---
abstract: "Lane D receipt, K1-FE-SHOW-M1 Rev 2, 9 Nov 2026 (AWST). One bench session on bench K1 B489A500 (resident ed0aa984, k1_fe_bench_b489). T2 (prepared Prim8 stream drives the renderer) = PARTIAL: the stream drives both edges, repeats, rejected input has no effect, seek and stop behave, live restored; fine timing gate A06 BLOCKED (no common-clock light sensor); live microphone leaks into Waveform Hybrid with music in the room; colour becomes palette-only. No flash, reset or erase."
---

# Lane D — real K1 bench session (T2 = M1)

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
- **T2 (M1): PARTIAL.** Met: prepared stream drives the renderer (primary edge measured; secondary edge footage, coarse); three repeats agree (0.93–0.99); rejected input (hz=0) has no effect in both conditions; forward and backward seek take effect; stop returns to live without freeze or stale replay; live baseline restored. Not met: A06 BLOCKED; with music in the room the live microphone mixes in (CR-A7); colour palette-only while authored.
- **T3 (M2): NOT RUN** (out of scope). Unobstructed; see C-spine receipt for the compiler pin mismatch.

## Timing statements (coarse only)
Host send error vs schedule p95 ≈2.0 ms (player, audio-clock paced) — host-side, not presentation timing. Player maps frames to the speaker's reported output time (`outputBufferDacTime`; Bose reports 161.7 ms latency, not independently measured). Device uses arrival time; no device-side timestamp of application exists without CR-A8. Emulator recovery (52.5 ms) is lockstep, not physical.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-09 | agent:claude (lead, Lane D) | Created after the bench session; all runs, restoration and findings recorded. |
