---
abstract: "Lane C-emu receipt (K1-FE-SHOW-M1 Rev 2, tasks C3, C4, C5), 9 November 2026, revised for the resident source ed0aa984 and Lane B's guarded wire format. Prepared Prim8 stream frozen (v2, bench-eligible); emulator proof through a labelled PROTOTYPE ADAPTER; host show player with audio-clock pacing, 64-byte guarded writes, resync preamble and device-output watchdog. Problems first."
---

# Lane C-emu receipt — C3, C4, C5 (revision 2: resident source ed0aa984)

All paths are relative to `_scratch/k1-fe-show-m1_20261109/lane-c-emu/` unless absolute. Emulator timing is lockstep: nothing below is physical latency evidence.

## Gates

| Task | Verdict | One line |
|---|---|---|
| C3 Prim8 stream | **PASS** | `stream/loreen_75_155_120hz_v2.prsm`, 9,600 frames at 120 Hz. Lane B validator VALID. Lane B byte audit BENCH-ELIGIBLE (0 hotkey-reaching bytes, preamble 64 B, guard 30 B). |
| C4 emulator proof | **PASS** (PROTOTYPE ADAPTER) | On ed0aa984 with the bench audio/render flags and guarded packets: authored differs from live, 3 repeats byte-identical, hz=0, hz=241 and version=2 byte-identical to live, seek and stop behave. Waveform Hybrid K1 and Snapwave both. |
| C5 host player | **PASS** (software, pty only) | Audio-clock pacing (wall pacing failed: 590 ms drift against audio over 80 s). Guarded full run: drift 11 µs, p95 send error 0.73 ms, 0 hotkey-path bytes, 0 partial frames. Watchdog tested with injected device lines. |

## Problems first

1. **Bad magic leaks to hotkeys.** This is a finding, not a test case (lead ruling). Earlier run `runs/c4-wfh-001/wfh-rej-magic` (407fdf6f, unguarded): 362 flash saves, 2,371 state changes, 120 garbage `:` lines, then an esp-emu panic. Byte model over the full stream: about 240 `N` and 251 `Y`. It is removed from the rejected set.
2. **Live audio leaks into authored output, also on ed0aa984 with the bench HPF flag.** The same authored stream over all-zero input differs on every captured frame:
   - Waveform Hybrid K1: 1,778/1,778.
   - Snapwave: 1,777/1,778.

   In Waveform Hybrid the live peak dominates the 137 s breakdown. The authored-only output goes dark there; with music present it stays at about live level (`runs/c4-ed0-001/c4-ed0-levels.png`). The prepared stream can only add light. Firmware change request below.
3. **The emulator cannot reproduce the bench output format.** The bench image (`k1_fe_bench_b489`) drives WS2812 8-bit output through `K1_LOOK_LIB_WS2812_V1`. The emulator's dual-edge capture tap exists only on the WS2816 Lever-2 path. Emulator frames are the same render state in a different wire format; they are not device bytes.
4. **The adapter bypasses the USB peripheral.** It feeds bytes into the production `check_serial()` byte loop ahead of `USBSerial`, so it cannot model USB packet loss or the HWCDC >63 ms stall drop. Lane B's loss proof and the player watchdog cover that risk.
5. **Single host stalls remain.** In the guarded full run, 1 of 9,595 frames was sent 46.5 ms late (host scheduling stall on a shared Mac, load average 4.7). The late-drop rule means no burst followed.
6. **Default audio output is Bluetooth** (Bose Mini II SoundLink, 161.7 ms reported latency, pulls samples about 1.4% slow). That is why audio pacing is required.
7. A cleanup step that would have deleted a temporary folder was declined. I worked around it with no deletion; no temporary folder was left.

## Source identity

- **Export.** `src-ed0aa984/` = `git archive ed0aa984`, the resident bench build: lead D0 read-back, version 40103, env `k1_fe_bench_b489`. It includes the mode-32 silence fix (byte-identical to the shared tree's staged diff) and `K1_FX_BATTERY`. The PRSM files, `serial_menu.cpp`, the fixture and the emulator tools are byte-identical to 407fdf6f.
- **Adapter.** Applied with `patch` only inside the export. `git apply` was tried first and silently skipped the files, because the export sits inside the main repository; nothing outside the export changed (verified with `git status`). The shared tree is untouched throughout.
- **Diff.** `PROTOTYPE-ADAPTER-ed0aa984.diff` (297 lines, sha256 `a253f2d9470dc22bdc43521d0763afdeddba4b26cd7bc6220ad97f3424697ef8`). The adapter adds RX records `{u32 hop, u32 len, u8 bytes[128]}`, queued before hop h and read by the production `check_serial` ahead of `USBSerial` (two lines under `#ifdef K1_EMU_FIXTURE`), plus `EMU_RX`, `EMU_AUTH` and `EMU_RX_END` lines. 128 data bytes is one preamble plus one guarded packet, which equals the firmware's 128-byte drain per loop pass.
- **Checks.** ELF contains `k1_emu_fixture_rx_read` and the HPF symbol `k1_subsonic_hp_wave_fresh`. `k1_fe` product build exit 0 with 0 fixture symbols. Seams and acceptance tests: 61 passed (`logs/pytest-seams-acceptance-ed0aa984.log`).

### Emulator env (`k1_fe_emu` + 3 declared bench flags) vs device env `k1_fe_bench_b489`

Flags from `pio project config` (`logs/pio-config-ed0aa984.json`):

| Flag | Emulator | Device | Effect on modes 32/22 |
|---|---|---|---|
| `K1_AP_SUBSONIC_HPF_V1` | **added** | yes | Live peak, silence, AGC floor and follower; drives the live leak in mode 32. |
| `K1_TEMPO_CONSUMER_BANDS_V1` | **added** | yes | Tempo-consumer band repair (`visual/channel_effect_state.h`). |
| `K1_FX_BATTERY=1` | **added** | yes | Extra effect families and dispatch IDs; modes 32 and 22 are unchanged. |
| `K1_LOOK_LIB_V1` + `K1_WS2816_LEVER2_V1` + `K1_MAIN_RPL_PINMAP_V1` | yes | no (unflagged) | Output path: emulator captures 16-bit Lever-2 packs. |
| `K1_LOOK_LIB_WS2812_V1` | no | yes | Device output is WS2812 8-bit; not emulated. |
| `K1_BENCH_REFERENCE_PINMAP`, `K1_PCM1808_*` pins, `K1_FE_BENCH_B489_V1` | no | yes | Pins, line input, LED type and colour order (`system.h:481`), rtrace dual tap. `K1_SILENCE_DWELL_DEFAULT_MS` is 5000 in both branches at ed0aa984 (`globals.h:840-845`), so silence dwell is the same. |

Snapwave (22) sources, `k1_prsm.cpp` and `k1_authored_source.cpp` are identical between 407fdf6f and ed0aa984 (`git diff --stat` empty). Mode 32 differs (`light_mode_waveform_hybrid_k1.cpp`, 19 lines; `globals.h`, 2 lines). Both modes were rerun on ed0aa984 anyway.
| `K1_EMU_*`, `K1_RENDER_TRACE_V1` | yes | no | Declared emulator adapters. |

## C3 — prepared Prim8 stream (unchanged since revision 1)

- Asset: lane-a `ASSET.json` (Loreen, sha256 `a62e1f09…b0f`, repository-approved regression fixture; not song-0). Passage 75–155 s; transition 137 s.
- Method (`stream/make_stream.py`, recorded in the sidecar):
  - pressure: RMS mapped −30 → 0 and −6 dBFS → 1; instant attack, 300 ms release; floor 0.02 above −60 dBFS.
  - impact: spectral-flux onsets (adaptive median+MAD threshold), 120 ms release.
  - mass, momentum, texture: 20–150, 150–2000 and 2000–16000 Hz band power, p05–p99 normalised, 200 ms release.
  - heat, space, gravity: constant 0.
  - seq = tick index.
- Frozen: `.prsm` sha256 `eafb72aecbccedba880364930898420a727d284dbe21182f18c6bff3f1258fdd`; sidecar sha256 `e4c84bb2df73049e8d5e7be84af390c1ffa1d7ee5dac900ba114d0e95e2bdec3`.
- Checks: plot `stream/loreen_75_155_120hz_v2.png` read. Validator VALID. `audit_prsm_bytes.py --guard 30`: BENCH-ELIGIBLE (`runs/audit-v2-guard30.json`).
- Rejected v1 (`ea4b8f45…`): too little loud/quiet contrast.

## C4 — emulator proof on ed0aa984 (`runs/c4-ed0-001`, 20/20 runs accepted)

**Setup.**
- Arrival model: the bytes for a frame at original time T are consumed before hop `ceil((T−75 s)/7.5 ms)−1` (`emu/schedules_ed0/index.json`).
- Wire bytes are bench-equivalent: each frame is a 64-byte guarded packet; `RESYNC_PREAMBLE` precedes the first frame and each seek epoch. 614,464 bytes queued and consumed per authored run (seek run: 614,592).
- Fixed PCM, blank flash, declared epoch 1.0 s, both edges in the mode under test, capture every 6th hop (1,778 frames).

**Native A/B payload sha256:**

| Case | Waveform Hybrid K1 (32) | Snapwave (22) |
|---|---|---|
| live baseline | `dbf338b08a59fe7cfce33a126537372c5c26160ef1747dcac0d3b4a8a3cd6130` | `30eda5a53b4ad2d2d2397432f8429c7fd5d0f3490bcdc6ac58cd2a82024aecfe` |
| authored ×3 | `7dcb0d32a5558637b5bbffd8b202af9732a2411c1c235b48e7a74a76ee7ca4b0` ×3 **identical** | `faef042e313aaedad9fc869d426cfcb5ace3b63d919319e078b47ec1e0f006d5` ×3 **identical** |
| hz=0 / hz=241 / version=2 | all = baseline `dbf338b0…` **identical** | all = baseline `30eda5a5…` **identical** |
| authored over zero PCM | `71cc2862…f549`: differs on 1,778/1,778 (leak) | `a689af75…b001`: differs on 1,777 (leak) |

- **Authored vs live:** Waveform Hybrid differs on 1,748 (A) and 1,748 (B) of 1,778, first at hop 18. Snapwave differs on 1,777 (A) and 1,778 (B).
- **Seek** (`wfh-seek` `5e9ff48e…`): forward at original 100 s to 110 s, back at 120 s to 105 s, preamble at each epoch. Identical to authored up to hop 3330, then differs from hop 3336 (seek at hop 3332). State stays AUTHORED throughout, with no RECOVERY.
- **Stop** (`wfh-stop` `ae1b0a08…`; dense window vs `wfh-base-dense` `ae9fc1ec…`): last frame at hop 6665. RECOVERY after hop 6672 (52.5 ms), STANDALONE after 6673. Byte-identical to live from hop 6825 onward (1.2 s; render history before that). Every frame is non-zero on both edges (no blackout).
- **Note on 407fdf6f.** The earlier runs (`runs/c4-wfh-001`, `c4-snap-001`, `c4-v2-001`; unguarded, no bench flags) gave the same verdicts. They are kept as history.

## C5 — host show player (`player/show_player.py`, sha256 `39c686d1ee1a22ec020b7acea3be056eaa347a28dc98e6ab483953bdbf6b645d`)

**Wire format and stopping.**
- Each frame is one 64-byte write from `lane-b prim8_stream.wire_packets()`.
- `RESYNC_PREAMBLE` (64 B, one write) goes before the first frame of the session, of each seek epoch and of each resume.
- Signals only set a flag, so the in-flight packet always completes. Tested: SIGTERM at 3 s gave exit 2 and 0 partial-frame bytes at the reader (`runs/c5-sigterm`).
- No K1CT frames are ever built.

**Pacing.**
- Audio pacing is the default when audio plays: a frame goes out when the output stream's DAC position reaches its content time.
- Late-drop: only the newest due frame is sent, never a burst.
- The sending thread runs at user-interactive quality of service.

**Watchdog (Lane B table, verbatim prefixes in the source).**
- A reader thread on the same port logs every device line to `<log>.device.jsonl` with monotonic time and the last seq sent.
- `NOISE_CAL: armed` or `not armed`: no writes for 5.5 s, then preamble plus a new epoch; exit 3 if the show completes.
- `NOISE_CAL: queued`: stop, exit 4 (CRITICAL).
- Any other listed or unexpected line: stop, exit 2.
- It never sends `Y`, `N` or `:`.
- Pty tests, with the line injected from the device side:

| Injected line | Exit | Frames sent in the next 5.5 s | Resume |
|---|---|---|---|
| `NOISE_CAL: armed (5s window)` | 3 | 0 | after 5.52 s, with preamble (3 preambles counted at the reader) |
| `NOISE_CAL: queued` | 4 | 0 | — (stopped) |
| `SHOW_STATE_SAVED` | 2 | — | — (stopped) |
| an unknown line | 2 | — | — (stopped) |

Runs: `runs/c5-wd-*`.

**Safety.**
- Never touches volume or the output device.
- Refuses to start if `afplay` is running; stops only a previous instance of itself.
- Asset sha256 is checked before play.
- I played only all-zero audio and opened no `/dev/cu.*` device.

**Budget.** Derived from A06 p95 ≤ 25 ms: sender p95 ≤ 4 ms and cumulative drift ≤ 2 ms over 90 s, leaving about 19 ms for USB, the device hop and render quantisation, and the calibration residual.

### Measurements (full 80 s passage)

| Run | Result |
|---|---|
| **Guarded, audio pacing, pty** (`runs/c5-pty-guarded-full`) | Send error p50 1 µs, p95 0.73 ms, max 46.5 ms (1 frame > 25 ms, 2 > 10 ms). Cumulative drift 11 µs. Audio alignment p50 0 µs, p95 0.72 ms. 5 late frames dropped. Reader: 9,595 frames byte-identical, seq order equal, 0 hotkey-path bytes, 287,914 NUL/newline guard bytes (= 9,595 × 30 + 64), 0 partial bytes, 1 preamble. **PASS** against p95 and drift; the single 46.5 ms stall is reported. |
| Unguarded, audio pacing, raised QoS (revision 1) | p95 0.9 ms, drift 13 µs (`runs/c5-pty-silent-pacing-audio-qos`). |
| Wall pacing against the audio clock (`runs/c5-silent-pacing-wall`) | 590 ms drift over 80 s: **FAIL**, which is why audio pacing exists. |

### Bench options added in revision 3 (all tested on the pty; device port never opened by me)

- **Port-open boundary.** The reader discards everything before the first newline after open and only then arms the watchdog; nothing is sent before that boundary (default timeout 3 s). Test `runs/c5-boundary`: a partial line was injected 0.3 s after open, and the first full `[AP]` line at 0.8 s. The joined partial was discarded and logged; t0 was 0.63 s after open; `[AP]` lines passed with `--allow-line "[AP]"`. A later `NOISE_CAL: armed` paused for 5.5 s, then preamble and resume, exit 3. Reader: 0 hotkey-path bytes, 2 preambles.
- **Allow-list.** Bench device logs (D0 read-back, lane-d S1–S3) show only `[AP] ...` lines plus the first partial line, and rtrace prints nothing at capture end (`k1_render_trace.cpp`). So `--allow-line "[AP]"` is the only allow needed for a normal show on this build.
- **`--audio-only`.** Same audio start, pacing and header logging; no frames, no port opened (`runs/c5-audio-only.jsonl`, silent stream: 0 frames sent, exit 0).
- **`--rejected hz0|ver2`.** Transforms the frames, logs the rule and both sha256s, keeps guard, preamble and watchdog.
  - Pre-flight: whenever frames are produced, `audit_prsm_bytes.py --guard 30` runs on the exact bytes to be sent (`<log>.sent.prsm`), with `--allow-rejected-frames` for `--rejected`. The player refuses with exit 1 unless the audit exits 0. Without the allow flag, the audit refuses hz0 (exit 1).
  - hz0: sent sha256 `f7e76352…6cd9`; the reader's firmware-rule scanner rejected 480/480 for rate; 0 hotkey-path bytes.
  - ver2: sent sha256 `0a93f7e0…0c52`; 480/480 rejected for version.
  - Runs: `runs/c5-rej-*`.
- **`--start-delay-s N`.** Applied after pre-flight and port open, before audio and frames (hz0 test: 2.0 s delay, t0 2.12 s after open).
- **Exit codes** are documented at the top of the file: 0 completed, 1 refused before start, 2 stopped, 3 completed after a NOISE_CAL pause, 4 CRITICAL.

### Bench command (the lead owns the port and device)

```
cd /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-c-emu
.venv/bin/python player/show_player.py --stream stream/loreen_75_155_120hz_v2.prsm \
  --asset /Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3 \
  --port /dev/cu.usbmodem11301 --allow-line "[AP]" --log runs/bench-T2-run1.jsonl
#  live baseline with music: replace --port … with --audio-only
#  rejected input:           add --rejected hz0   (or ver2)
#  camera/LED capture first: add --start-delay-s 10
#  seek: --seek 25:110 --seek 45:105    stop: --stop-after-s 50
#  benign device lines seen at bench start can be allowed with --allow-line PREFIX (default: none; any line stops)
#  exit 0 ok | 2 stopped (watchdog or signal) | 3 completed after a NOISE_CAL pause | 4 CRITICAL (calibration queued)
```

## Change requests

1. **FW lead:** drop non-frame bytes while authored is active (Lane B CR-5: abort byte, scanner idle reset, CRC).
2. **FW lead / A7:** authored mode should read the authored snapshot only (Waveform Hybrid `fmaxf` with the live peak; Snapwave).
3. **Emulator tool owner:**
   - Adopt the RX-record adapter.
   - Hex-escape `EMU_HCMD` text (esp-emu 0.49.0 panics on non-UTF-8).
   - A WS2812 capture tap would let emulator frames match the bench byte format.
4. **PRISM.studio:** K1CT frames would hit FE hotkeys; its 250 ms freshness comment is stale (device: 50 ms).
5. **Bench (lead decision):** prefer wired audio output over Bluetooth.

| Date | Author | Change |
|---|---|---|
| 2026-11-09 | agent:claude-code (lane-c-emu) | Created (407fdf6f). |
| 2026-11-09 | agent:claude (lead, bench) | Player audio fix after the Captain heard stutter on the first music run: 64-frame `latency="low"` CoreAudio buffers on the Bluetooth output were starved by the pacing spin (GIL) and the camera encoder (3,200-frame spans took up to 112 ms vs 73 ms). Now `blocksize=4096, latency="high"`, `SPIN_NS = 0`. Verified on the bench: consumption 44,100 Hz at p1/p99 in every 4.6 s window (S6 and M0–M4), send error p95 ≈2.0 ms. show_player.py sha256 8623cb99…3593. Evidence: lane-d/D-P2-receipt.md. Housekeeping: src-407fdf6f deleted by the lead (wrong source for the resident build; reproducible with `git archive 407fdf6f`). |
| 2026-11-09 | agent:claude-code (lane-c-emu) | Revision 3: bench options --audio-only, --rejected hz0/ver2 with pre-flight audit on the exact bytes, --start-delay-s; watchdog armed only after the first newline after open (partial-line bench bug); exit codes documented; flag table adds silence dwell; Snapwave identity across commits. src-407fdf6f kept (folder deletion was declined at the permission prompt). |
| 2026-11-09 | agent:claude-code (lane-c-emu) | Revision 2: resident source ed0aa984 + bench flags; guarded packets and preamble in emulator and player; rejected set hz0/hz241/ver2; bad magic moved to findings; device-output watchdog with pty tests. |
