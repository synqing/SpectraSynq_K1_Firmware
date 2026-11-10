---
abstract: "K1-FE-SHOW M2 lane E (m2-emu), 10 November 2026. Executable emulator gates G1–G4 that the firmware fixes will be judged by, run on two sources: ed0aa984 FE/B489 configuration (k1_fe_emu) and ed0aa984 Main RPL configuration (k1_main_rpl_emu, proxy for the resident 2a620f7e). G1 repeatability PASS, G2 live-input independence FAIL, G3 seek reconstruction FAIL, G4 M2-stream playback and twin PASS. One command, gates.py, reruns them all. Host only; no device was opened."
---

# M2 lane E: emulator gates (M2E receipt)

All paths are relative to `_scratch/k1-fe-show-m2_20261110/m2-emu/` unless absolute. This is a host-only lane: no `/dev/cu.*` port was opened and no device was touched.

## Problems first

1. **G2 FAIL. The live microphone changes both edges.** Same prepared stream, same initial state, different microphone PCM. Both edges differ on almost every frame in every pair (table below). The cause is known from M1: in Waveform Hybrid (mode 32), the live peak is OR-ed into the authored peak at `light_mode_waveform_hybrid_k1.cpp:116`.
   - This was the expected result today. It is the acceptance test for the FW lead's fix that isolates the prepared source.
2. **G3 FAIL. A seek leaves state that does not wash out.** I reached the musical window starting at 105.0 s three ways: continuous play, a forward seek and a backward seek.
   - After the declared 5.0 s reconstruction interval, both edges still differ on 594–667 of the 667 judged frames.
   - The difference pulses at the beat rate and does not shrink over the whole 10 s window (`runs/*/gates-diff.png`). So this is persistent state, not trail decay. [INFERENCE: it fits a beat/tempo phase or colour state; not localised in this lane.]
   - On today's build, the audio seeks with the stream, so live-path history is mixed into G3. G3 can only isolate prepared-state reconstruction once G2 passes.
3. **The resident Main RPL source (2a620f7e) cannot run these gates.** It branches from 68a684dc (20 October), which is before the R3 replay stack existed. At 2a620f7e there is:
   - no scenario blob, no lockstep, no time/random seams, no `emu_capture` and no `k1_main_rpl_emu`;
   - only the 158-line R2 fixture prototype;
   - nowhere for the adapter to apply: all 13 of its hunks fail.

   Lead ruling: **no graft**. The FW fixes will be built on the FE release lane, so the proxy below is the correct target. Every Main RPL result here is labelled **"ed0aa984 Main RPL configuration (k1_main_rpl_emu), not the resident 2a620f7e"**.
4. **The first combined run failed at blob build.** `runs/ed0aa984-all-20261110T015136` stopped with `ValueError: scenario blob 9386888 bytes exceeds the ota_1 partition`.
   - Cause: the whole 224 s track's PCM plus its RX records is 9.39 MB, and the ota_1 partition is 6.25 MB.
   - Fix: G4 now plays a declared window (default 75–155 s, the M1/C4 window). `gates.py` also refuses before running if a case would not fit, and names the case.
   - Whole-track coverage would need separate segments, and each segment starts from boot because no state carries across segments. Not run.
5. **The R3 SW criteria report shows SOFTWARE INCOMPLETE.** In `report.html`, SW04, SW11 and SW13 are FAIL in the gate runs. This is by construction:
   - the gate suite plants no captures and has no client cases;
   - the work copy carries the gate scenario, so it is not a clean export.

   These are R3 release criteria, not these gates. SW01 (every run accepted, executed app equals the built `firmware.bin`, image never patched) and SW07 (product build clean, 0 fixture symbols) PASS.

## Verdicts

| Gate | FE/B489 configuration, mode 32 | Main RPL configuration (proxy), mode 32 | Main RPL configuration (proxy), mode 18 |
|---|---|---|---|
| G1 prepared-stream repeatability | **PASS** | **PASS** | M18_G1 |
| G2 live-input independence | **FAIL** (expected) | **FAIL** (expected) | M18_G2 |
| G3 seek reconstruction | **FAIL** (expected) | **FAIL** (expected) | M18_G3 |
| G4 M2 stream and reopened twin | **PASS** | **PASS** | M18_G4 |
| Run directory | `runs/fe-ed0aa984-m32-20261110T031959` | `runs/rplproxy-ed0aa984-m32-20261110T031959` | `runs/rplproxy-ed0aa984-m18-20261110T035112` |
| gates.py exit code | 2 | 2 | M18_EXIT |

Earlier runs, kept as history:
- `runs/ed0aa984-base-20261110T004215`: G1–G3 FE. Byte-identical to the FE row on all 7 shared cases.
- `runs/ed0aa984-g4-click-20261110T014932`: G4 on m2-compose's `ci_click_3s` fixture stream and its twin. PASS: 400/400 frames identical per edge, AUTHORED, 359/359 records consumed.
- `runs/ed0aa984-all-20261110T015136`: the failed blob run in item 4.

Expected results were declared before running, in `gates.py` `EXPECTED_TODAY` and the first line of each `gates.log`:
- G1 PASS;
- G2 FAIL (M1 C4 leak);
- G3 FAIL (no reconstruction; bench S5);
- G4 PASS.

Every result matched. G2 and G3 are real tests that went red on real behaviour; nothing was planted. G1 and G4 use the same comparator that went red in G2 and G3.

## What each gate does

**Captured output.** Both edges' native payloads at the emulator tap:
- edge A = `ws2816_wire`, edge B = `ws2816_wire_secondary`;
- 160 logical pixels each, 6 bytes per pixel, G16BE R16BE B16BE;
- taken after the Lever-2 pack and before `FastLED.show()`;
- hashed per edge as the sha256 of the concatenated per-frame bytes.

**Inputs.**
- Both edges run the mode under test, set by `set_mode`, `secondary_mode` and `secondary_enabled=true` at hop 0.
- Blank flash, declared epoch 1.0 s.
- Stream bytes go through the M1 PROTOTYPE RX-record adapter into the production `check_serial()` byte loop, as Lane B guarded 64-byte packets with `RESYNC_PREAMBLE` at each epoch.
- Arrival model as in M1 C4: a frame due at run time t is consumed before hop ceil(t/7.5 ms)−1. The G1 schedule sha256 equals C4's `authored.rx` (`91d6d240…`).

**G1.**
- Two runs: the M1 stream (`loreen_75_155_120hz_v2.prsm`, sha256 `eafb72ae…8fdd`) over the 75–155 s passage, capturing every 6th hop (1,778 frames).
- Both edges must be byte-identical.
- The G3 continuous run shares the same input prefix, so it must also equal run 1 on the 222 shared frames.

**G2.**
- The same stream over three microphone PCMs:
  - (a) the passage, 75–155 s;
  - (b) all zeros;
  - (c) different real music: Loreen 56–136 s, which is `loreen_src` from `s3_music_regression.json`, starting at its `music_chorus` start and extended to 80 s.
- Each pair is compared per edge, byte for byte.

**G3.**
- Landing position D = 105.0 s. Authored pressure there is 0.50–1.00 (mean 0.73), so mode 32 trails are lit throughout.
- Three runs, with audio and stream jumping together as the bench player does:
  - continuous play;
  - forward seek: play 75.00→85.05 s, then jump to 105 s;
  - backward seek: play 75.00→125.025 s, then jump to 105 s.
- Offsets are whole multiples of 75 ms (10 hops = 9 ticks). After the seek, every sample, tick and arrival hop therefore sits at the same phase as in continuous play.
- The window D…D+10.005 s is captured densely (1,334 hops).
- **Declared reconstruction interval R = 667 hops (5.0025 s).** Justification:
  - The slowest-decaying history in mode 32 is the trail: fade = exp(−(0.8+3.5·peak)·dt) (`light_mode_waveform_hybrid_k1.cpp:297-307`).
  - With pressure ≥ 0.50 everywhere in 105–115 s, the decay rate is ≥ 2.55/s.
  - So a full-scale trail value falls below one 16-bit step within ln(65536)/2.55 = 4.35 s. R adds margin.
- The gate judges the remaining 667 hops. Per edge it reports the first and last differing hop over the whole window.
- R is mode-32-derived. Mode 18 reuses it as declared; no separate derivation was made.

**G4.**
- The M2 stream `m2-compose/projects/loreen/stream/loreen_post_edit_120hz.prsm` (sha256 `116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3`, sidecar `424ac52a…`).
- Its reopened-and-recompiled twin, `stream_reopen/…`: same stream and sidecar bytes.
- Window 75–155 s: frames 9000–18598 (seq 9000 first), 9,599 of 9,600 sent. The final frame falls inside the 2-hop end margin that keeps records off an ffmpeg-short tail.
- PCM: Loreen 75–155 s.
- Pass requires all of:
  - both runs accepted;
  - AUTHORED reached;
  - all RX bytes consumed;
  - 0 show-state changes from hotkeys;
  - both edges byte-identical between stream and twin.

## G1–G4 per edge (mode 32)

`F x/y` = differing frames / compared frames. "m-hop" is the hop counted from 75.0 s.

| Pair | FE edge A | FE edge B | RPL proxy edge A | RPL proxy edge B |
|---|---|---|---|---|
| G1 run 1 vs run 2 | 0/1778 | 0/1778 | 0/1778 | 0/1778 |
| G1 run 1 vs G3 continuous (shared frames) | 0/222 | 0/222 | 0/222 | 0/222 |
| G2 passage vs zero | 1778/1778, first hop 0, px 72 | 1778/1778, first hop 0, px 72 | 1778/1778, first hop 0, px 72 | 1778/1778, first hop 0, px 72 |
| G2 passage vs other music | 1775/1778, first hop 18, px 23 | 1775/1778, first hop 18, px 2 | 1773/1778, first hop 30, px 2 | 1773/1778, first hop 30, px 2 |
| G2 zero vs other music | 1778/1778, first hop 0, px 72 | 1778/1778, first hop 0, px 72 | 1778/1778, first hop 0, px 72 | 1778/1778, first hop 0, px 72 |
| G3 continuous vs forward, after R | 594/667, first m-hop 4667 | 594/667 | 602/667, first m-hop 4667 | 602/667 |
| G3 continuous vs backward, after R | 667/667 | 667/667 | 667/667 | 667/667 |
| G3 forward vs backward, after R | 667/667 | 667/667 | 667/667 | 667/667 |
| G4 M2 stream vs twin | 0/1778 | 0/1778 | 0/1778 | 0/1778 |

**G3 over the whole landing window.** The first difference is at the landing hop (m-hop 4000) in every pair, on both edges and both sources.
- Last differing hop: 5332 for continuous vs forward, and 5333 (the last captured hop) for the backward pairs.
- Total differing frames out of 1,334: FE 1,261 / 1,334 / 1,334; RPL proxy 1,269 / 1,334 / 1,334.
- So the difference lasts at least the whole 10.005 s window. There was no convergence in any pair.

**G4 checks, both sources.** `EMU_RX_END records=9599/9599 queued=614400 consumed=614400 auth_state=2`, 0 hotkey state changes, for both the stream and the twin.

### Per-edge payload sha256, mode 32

| Case | FE A | FE B | RPL proxy A | RPL proxy B |
|---|---|---|---|---|
| g1-a1 = g1-a2 | `25b0dcc3a5809144614ac7ff2a7971c180e330be75e2a529bcb0300caea52bf8` | `94ba3fdfad24003a7a9c4a26ecd861e775dceccb9f332179ef7d5a71da7b6754` | `94b83c05934f327cafc4e23849d9d3d13040d4fb8ad33ac7bf807f26c1865da9` | `9a79f63a544d970b7e38a32a6aadb8401d92f98e95ba4e34d44ea05207d3572e` |
| g2-zero | `72be8ecd55616d9107a9b26190b96b13dc10f53d29ced296067ca28045f429e7` | `efb54b08e7db2cfdf1d05739dae66d693589b968bf9867ae09529d6cdb434da5` | same as FE | same as FE |
| g2-other | `a88b7f385370f842908aae96319561a4490c85b64f12726323f36c06c8bb79ed` | `420db9bb4dea08afdea1dd0cbae99a928bbe79d8fcaa3cae3289aa511adb40f0` | `ec60f0728a5e98e50fb43485ea1710c0aa4b5aaf59a37c2f1af40ace0c89036d` | `b17c2a7017e1c53c64337b6e8a8c066bff97d9af5111d0ddb2f81fb4f266c4ad` |
| g3-cont | `40e0e7c433e4609e1f51825b180388281919556ca6a9f4ed314ab238b38a92c0` | `445ad58e401e93704f7976d6dd1a92703a529c447e3623e9de9918d9c83e0f75` | `d4fde3cb5ec1e51a3b42defb35311fdf31d2a37b20e9784bc0f055ad8ed66c5e` | `5f952aac0dac2fbb01a3edece8bcbc0c010b506eb37ca8b6b8ce01ed50378171` |
| g3-fwd | `cfd911470934047230c4a68a0873a24ffd371d8ce4e42b7795094a0027e8526e` | `aa588f929a096a1772921f0bd9d1f9463faef37dfba5b0cd762ce9f0f1473036` | `e93428c0a1c8fdc67d342fd5074b82226b002efcf8ac01242c5040c2ab361b7a` | `cf18188b5ff5b187d136ea2399de9e228a80994649b1b66edeac76873f2e8f95` |
| g3-back | `81b2cb042b5605341c4662f662158b8153b630f5a8e905d557117a4d3d6e9588` | `db7ba309e880a21a0c57ade0701ac12fe42286614af30c2016f28dca8f75399e` | `21e3992faf04010fc564895d68148cd5db1aaa7bcd22881a400a97cc2096c4f4` | `e8e845488504c2dc0c9905fdc3a1bc6dcb0ec1d699ed6a9e38b3b595b3edbcf0` |
| g4-m2 = g4-twin | `31400a4413307af46bfc2ddbb6b6075afc13c961326b2fd9c476b2188e29e5d3` | `594f8288a0ada97ca40bec539a483793f7165f1a758ff8dd5ac2b057893c07f6` | `f20c43f0547266c2758d2bf299247563518a3bd173ec95810b048ea74bdcdc57` | `e4738db40beef79f6b0849344c9844d1ce7cf55253c0b73d8dd0e234c75fc6c7` |

**Repeatability observations.**
- **Across invocations.** The FE run at 03:20 reproduced the 00:42 baseline byte for byte on all 7 shared cases, although the rebuilt ELF differs (build epoch). It ran concurrently with the RPL proxy run, so this was under parallel load.
- **g2-zero.** With all-zero microphone PCM the FE and Main RPL configurations give identical output on both edges. [INFERENCE: their differences, such as the B489 HPF and tempo-band flags, act only on live audio.]

## Mode 18 (Main RPL resident primary), proxy

M18_SECTION

## Source identity

| Source | What was built | Emulator env and flags |
|---|---|---|
| FE/B489 configuration | `src-ed0aa984/` = `git archive ed0aa984` + `PROTOTYPE-ADAPTER-ed0aa984.diff` (sha256 `a253f2d9…7ef8`) applied with `patch -p1`. `diff -rq` against M1 `lane-c-emu/src-ed0aa984` shows it identical, except that folder's identity file and C4 scenario. Work copy `work/src-171dd9e89e53`. | `k1_fe_emu` = `k1_fe` + declared emulator adapters + the 3 B489 bench flags `K1_AP_SUBSONIC_HPF_V1`, `K1_TEMPO_CONSUMER_BANDS_V1`, `K1_FX_BATTERY=1`, as in M1 C4. ELF sha256 `2627a0c848025e8502af4f365aa2d695ea5885fb36626d7d89506c59384afe91` (run fe-…-m32). |
| Main RPL configuration (proxy) | `src-ed0aa984-rpl/` = `git archive ed0aa984` + `PROTOTYPE-ADAPTER-ed0aa984-noflags.diff` (sha256 `7f598430…f826`): the same RX adapter without the platformio hunk. Work copy `work/src-c25d2b6d7936`. | `k1_main_rpl_emu` = `k1_main_rpl_im69d` + `K1_RENDER_TRACE_V1`, `K1_EMU_FIXTURE`, `K1_EMU_SKIP_EMIT`, `K1_EMU_UART0`, plus the forced-include clock header. The `-D` set of `k1_main_rpl_im69d` is identical at ed0aa984 and 2a620f7e (`pio project config`, `pio-config-src-*.json`; the lead confirmed the sections are byte-identical). None of the B489 bench flags are set. ELF sha256 `954c13cd1be26fac888f0a43e8301c7e7b2e3a93f66e8b9668a9a91a0a17feda` (run rplproxy-…-m32). |
| Resident 2a620f7e | `src-2a620f7e/` = `git archive 2a620f7e`, kept for reference; **not run** (problem 3). | — |

**Known source differences, proxy vs resident 2a620f7e.**
- Identical on the gate path: `k1_prsm.{h,cpp}` and `k1_authored_source.{h,cpp}`.
- Mode 18 (`light_mode_waveform_tempo.cpp`): ed0aa984 has 3 more lines.
- Mode 32: ed0aa984 changes 6 lines. They move `sat_ema` from a function-static into per-channel effect state. That code sits inside `#ifdef K1_POSITION_SMOOTH_V1`, which neither device build nor either emulator env defines. Checked in the `-D` lists of `k1_main_rpl_emu` and `k1_fe_emu`, and in the lead's `fw-diff-rpl-vs-b489/build_defines_diff.json`. So it is **present in source, compiled out**, and cannot affect any result here.
- `.ino`, `led_utilities.h` and `serial_menu.cpp` differ, partly through emulator hooks.
- `constants.h`: LED DIN pins. Pin numbers are irrelevant in emulation.

**Other identities.**
- Tool: esp-emu 0.49.0, executable sha256 `dea564e3…84a0` (hash-checked by `run.py` against `tool-lock.json`).
- Inputs:
  - M1 stream `eafb72ae…8fdd`;
  - M2 stream and twin `116981ee…97e3`;
  - passage PCM sha256 `ce0c535e…` (identical to C4);
  - Loreen source mp3 `a62e1f09…0b0f`.

## gates.py

```
cd /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-emu
PY=../../k1-fe-show-m1_20261109/lane-c-emu/.venv/bin/python     # python 3.13 + numpy/matplotlib
C=../m2-compose/projects/loreen
# FE / B489 candidate:
$PY gates.py --src <candidate export> --profile fe --mode 32 \
   --m2-stream $C/stream/loreen_post_edit_120hz.prsm --m2-twin $C/stream_reopen/loreen_post_edit_120hz.prsm
# Main RPL candidate (FE lane source + RPL pin map):
$PY gates.py --src <candidate export> --profile scenario --mode 32 ...   # and again with --mode 18
# re-judge an existing run without the emulator:   $PY gates.py --analyse runs/<run dir>
```

- **Source handling.**
  - `--src` is copied into `work/src-<tree hash>/` and never modified.
  - If the copy lacks the RX adapter, `gates.py` applies it there:
    - `--profile fe` uses the ed0aa984 diff with bench flags, falling back to the 407fdf6f diff (tested: both apply cleanly to 407fdf6f);
    - `--profile scenario` uses the no-flags diff.
  - The auto-apply path was tested on a clean `git archive ed0aa984`. It produced the same work tree hash as the baseline (`171dd9e8…`).
- **Run.** It writes the scenario and RX schedules, runs the existing `tools/esp_emulator/run.py`, judges, and prints the per-gate table.
- **Outputs.** It writes `gates.json`, `gates.md` and `gates-diff.png` in `runs/<label>-<stamp>/`. The emulator's own `result.json`, `report.html` and raw `uart.txt` per case are under `emu/`.
- **Exit code** = the number of selected gates that are not PASS (FAIL or BLOCKED). `--detach` returns at once and writes the code to `exit_code.txt`.
- **Wall time.** About 10 minutes per invocation for 9 cases.
- **Concurrency.** Run one invocation per source tree at a time, because the work copy and build cache are shared.
- **Other options.**
  - `--m2-window START:END` (default 75:155) selects the G4 window.
  - A case that would overflow ota_1 is refused before running, with its size.
- **Report checked.** `report.html` (baseline) was served on loopback and screenshotted at 1440 px and 390 px (`runs/ed0aa984-base-20261110T004215/report-desktop.png`, `report-phone.png`). Both render; the only console error is a missing favicon (404).

## Limitations

- **Output format.**
  - FE configuration: the emulator captures WS2816 16-bit Lever-2 packs, while the B489 bench unit drives WS2812 8-bit (`K1_LOOK_LIB_WS2812_V1`, not emulated). Same render state, different wire format.
  - Main RPL configuration: the WS2816 dual-edge capture matches the bench unit's LED type.
  - Pin numbers are irrelevant in emulation.
- **Lockstep timing.** Every hop is shown exactly once; nothing here is physical latency or device scheduling.
- **Input path.** The adapter feeds bytes into `check_serial()` ahead of USBSerial. It does not model USB packet loss or the HWCDC stall drop. The FE profile replays microphone PCM only (`K1_EMU_FE_MIC_ONLY`); line input is not covered.
- **Proxy.** Main RPL results come from ed0aa984 Main RPL configuration (k1_main_rpl_emu), not the resident 2a620f7e (problem 3).
- **Seek semantics.** A seek resends the original frames, so seq jumps with a preamble. This is what the bench player does. PRISM `playback.js` instead keeps seq contiguous; that variant is not run. The device ignores `t_us`.
- **Reconstruction interval.** R comes from mode 32's trail decay. A fix may declare a different R; it is the constant `G3_R_HOPS` in `gates.py`.

## Ship path

1. **Already done.** The gates exist and run from one command. On ed0aa984 they are green for G1 and G4 and red for G2 and G3, matching the declared expectations.
2. **Next.**
   - The FW lead builds the prepared-source isolation fix and the seek-reset fix on the FE release lane.
   - They export the candidate (`git archive`), then run `gates.py` twice: `--profile fe --mode 32`, and `--profile scenario` for modes 32 and 18.
   - G2 and G3 must turn PASS while G1 and G4 stay PASS: exit code 0 on all three invocations.
3. **Who.** The FW lead runs it. m2-emu can run it on request.
4. **Stamp.** `gates.json` with all four gates PASS for the candidate export, then the bench flash and observation by the lead.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude-code (m2-emu) | Created. FE and Main RPL proxy runs, modes 32 and 18. Blob-overflow failure diagnosed and fixed. 2a620f7e graft declined by the lead. |
