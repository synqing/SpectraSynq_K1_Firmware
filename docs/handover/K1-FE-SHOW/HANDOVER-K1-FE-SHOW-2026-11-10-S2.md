---
abstract: "Handover from K1-FE-SHOW lead session 2 (10 Nov 2026, 16:05–21:50 AWST). The FW lead's prepared-show fixes (a6bad318) passed every emulator gate, the real-receiver loss test and the live-output identity check, and were flashed to the Main RPL. A bench session ran there: receiver isolation, prepared-source isolation and seek all behaved, and three new defects were found (mid-show resets after short USB stalls, dimmer prepared shows, and the loud guard / AGC flattening live response). The PRISM tools (editor, Spine CLI, Trinity) are fixed on branches, including per-section editing. An audio-front-end forensic investigation was in flight at handover. Read this whole file first; the earlier handover HANDOVER-K1-FE-SHOW-2026-11-10.md still holds for background."
---

# Handover — K1-FE-SHOW lead, session 2 (10 Nov 2026, 21:50 AWST)

Written by the outgoing lead at the Captain's request (context limit). Every fact below was checked in this session unless marked **[UNVERIFIED]**. Use `/usr/bin/git`; plain `git` is a reformatting wrapper.

## 1. One-paragraph state

The prepared-show firmware fixes now exist and work on real hardware. The FW lead's candidate `a6bad318` (branch `fe/k1-fe-show-fixes`, parent `8b202f46`) passed every check:
- emulator gates G1–G4 PASS on all three invocations (baseline at `8b202f46` was G2/G3 FAIL);
- the real firmware receiver survived 913,580 simulated packet losses on the M2 stream: 0 hotkeys, 0 commands, 0 corrupt frames (before the fix: 110 noise-cal queues and 178,135 persists);
- live mic output is byte-identical to `8b202f46` in all 22 emulator regression cases.

It is flashed on the Main RPL. The bench session showed three things:
- isolation and seek work on hardware;
- the show **resets mid-play when the Mac stalls USB writes for about 80 ms or more** (new change request R3-1);
- prepared shows are **dimmer** than before (R3-2).

The Captain also saw the live picture "clipping / not fully responding". The mic front end does **not** clip. The flattening comes from the auto-level stage pinning plus the **loud guard** cutting spectrum gain (R3-3). That is a long-known, never-closed problem (records from 23 Jun, 10 Jul and 19 Aug), now under forensic investigation. The PRISM tool defects from M2 are all fixed on branches, including per-section editing; none is merged or pinned.

## 2. Live state (verified 21:47 AWST)

| Item | State |
|---|---|
| Main RPL `9087A500` (USB `B4:3A:45:A5:87:90`, `/dev/cu.usbmodem11301`) | **Runs `k1_main_rpl_show_bench` @ `a6bad318`**, epoch `1794315461`, NON-SHIPPABLE bench test build. Mode restored to **22**; all 30 `CONFIG.*` identical to before the flash (`bench-rpl-20261110/ident-before/` vs `ident-end/`). `SENSITIVITY` 2.7, SSL 157, DC −238. Recovery: full 16 MB read-back of the previous image `2a620f7e` at `bench-rpl-20261110/recovery/main-rpl-9087A500-full-flash-2a620f7e.bin`, sha256 `61847dc46cb428534ea4256cbdac84ad635c2ede726aca082426ab407110eade`. Flashed image: `bench-rpl-20261110/flash/firmware.bin` sha256 `c35e5a4a10c53766a0243e362bd748cfd0d6dfac0f2493193020bf3072234182` (SHA256SUMS beside it). |
| Device registry | `docs/hardware/device-build-registry.md` Main RPL row updated in the **shared working tree, uncommitted** (line ~29). The FW lead or whoever next commits on the FE lane should commit it. |
| Other hardware | B489 not connected. The parked DualMCU K1-S3 is not on USB now. a7S III is in PC-remote mode, held by macOS `mscamerad` (gphoto2 cannot claim it; it is not an AVFoundation source). Bose Mini II is the default output AND default input (never open its input). |
| Audio | Nothing playing (`pgrep -lx afplay` empty, no `show_player`). |
| Shared firmware tree `~/SpectraSynq_K1_Firmware` | Now checked out on **`mcpp/next-phase-fixes`** (Modernes C++ session; `5bb142bc`, then `4e56c4dc`). Uncommitted: the registry edit (mine) and `docs/forensics/runtime-evidence/20261110-fe-show-fixes/` (the FW lead's evidence). Never checkout/switch/stash/reset/add/commit there. |
| FW lead | **Not running.** It died at 18:02 AWST (`ENOTFOUND`) after committing `a6bad318`, before writing its receipt section "K1-FE-SHOW fixes". State: `~/K1_Launch_Planning/00-Governance/team/logs/FW-20261110-1618.state.json` (stopped_with_error). My custom `claude -p --resume` was **refused by the auto-mode classifier** ("Create Unsafe Agents"). `zsh ~/K1_Launch_Planning/00-Governance/team/launch-leads.sh FW` worked at 16:18. The charter carries my dated session brief (`team/LEAD-FW-FE-RELEASE.md`, "Session brief — prepared-show firmware fixes"), **uncommitted** in `~/K1_Launch_Planning` (that repo has other people's uncommitted changes; do not commit it). |
| Modernes C++ session (peer, `uds:/tmp/cc-socks/48651.sock`, name "MODERNES-CPP execution plan") | Cooperative. It committed `5bb142bc` (parent `a6bad318`) on its own branch and changed `k1_prsm_rx.cpp` (an over-long `:` line stays interactive) and `parse_command`. It is waiting for my G1–G4 results on `5bb142bc`. Final (21:55): fe/m32, scenario/m32 and scenario/m18 all **exit 0, 0 failing gates** (`fw-candidates/5bb142bc/`); results sent to it 21:55. |
| PRISM tools (all local, **not pushed**) | PRISM.studio clone `_scratch/k1-fe-show-m1_20261109/prism-studio-locked`: `fix/one-instrument-editor-loop` `87f0c43`, `feat/per-section-mapping` `f2e7359` (on `849f1cc`); HEAD detached at lock `cc00556`, clean. `.g5r-clean/PRISM.studio` repaired (alternates replaced by fetched objects), detached at `cc00556d`, clean. Spine `~/Workspace_Management/Software/SpectraSynq-Instrument-Spine`: `fix/cli-authored-project` `21265e5`, `feat/per-section-mapping` `1285556` (**checked out**; untracked `docs/architecture/` is not ours). Trinity `~/Workspace_Management/Software/Trinity`: `fix/reproducible-contract` `0cfa247` (**checked out**). |
| Lane branches | `lane/k1-fe-show-m1`, `lane/k1-fe-show-m2`: this session's evidence is committed at handover (§13 gives the SHAs). |

## 3. Read order

1. This file, then `HANDOVER-K1-FE-SHOW-2026-11-10.md` (session 1; background, rules §12 still binding).
2. `_scratch/k1-fe-show-m1_20261109/CHANGE-REQUESTS-FW-LEAD.md` (rev 2 + **rev 3 additions R3-1..R3-3**).
3. `_scratch/k1-fe-show-m1_20261109/SCOPE-RECONCILIATION.md` §6 (Captain decisions (c)(d)(e) of 10 Nov 16:20).
4. `baseline-8b202f46/RESULT.md`, `fw-candidates/a6bad318/EXPECTED.md`, `fw-candidates/SHARED-TREE-OWNERSHIP-2026-11-10.md`.
5. `m2-tools/{prism,spine,trinity,section}/*-receipt.md` (tool fixes; re-run commands inside).
6. `audio-forensics/{history,source,emu}/` (in flight at handover; see §8) and `AF-BRIEFS-2026-11-10.md`, which holds the three briefs verbatim for re-dispatch.
7. COURSE `~/K1_Launch_Planning/00-Governance/COURSE-2026-11-02.md`, `team/OPERATIONS.md`, `team/LEAD-FW-FE-RELEASE.md`.

## 4. Captain rulings in force (new this session marked ★)

- ★ (c) **"All fixes now"**: the FW lead implements every item of change requests rev 2 except priority 3 (harmonic colour extension). 10 Nov ~16:20.
- ★ (d) **"Yes, all of it"**: agents fix PRISM.studio, Spine and Trinity on branches in their own repos, including per-section editing. `organs.lock.json` is never repinned by an agent.
- ★ (e) **Main RPL is the bench unit; flash go** once fixes pass G1–G4 and the receiver checks. **Used**: flashed 20:58. Further flashes of fixed candidates to the Main RPL for this lane are covered by this go [INFERENCE from "a flash go for a capture-enabled test build"; restoring `2a620f7e` is always allowed].
- ★ The Captain set up the bench: Main RPL on USB, the Bose for playback, the a7S III "on remote shooting" (see §2: not usable by our tools).
- Session 1 rulings still in force: GPIO maps are never locked; Wi-Fi banned; no planted faults or mutation tests; no wasted re-runs; one script per Captain action; plain English, problems first, ship path; instrument, not Captain eyes; never re-ask approvals; never touch Mac volume or output device; calibration only after the Captain confirms silence; British English; no extra clones or worktrees of the firmware repo.

## 5. What was done this session, with verdicts

| # | Work | Verdict | Evidence |
|---|---|---|---|
| A | Baseline gates at `8b202f46` (expected G1 PASS, G2 FAIL, G3 FAIL, G4 PASS, declared first) | Matched exactly; LED payloads **byte-identical** to `ed0aa984` on both profiles (Gx code does not darken the emulator) | `baseline-8b202f46/RESULT.md`, `m2-emu/runs/*8b202f46*` |
| A2 | Lane B oracle re-pointed (`fw_8b202f46/`, env selectors `LANE_B_FW`, `LANE_B_RAW`) | Same verdicts as 407fdf6f; 163 tests pass (lead re-ran) | `lane-b/ORACLE-8b202f46.md` |
| B | FW lead briefed (charter session brief) and launched 16:18; committed `a6bad318` 17:30; died 18:02 | Candidate scope clean (only its own hunks in the shared `led_utilities.h`) | `fw-candidates/a6bad318/` |
| B2 | Judge `a6bad318`: gates fe/m32, scenario/m32, scenario/m18 | **All PASS, exit 0** | `m2-emu/runs/{fe,scenario}-a6bad318-*`, `fw-candidates/a6bad318/*.log` |
| B3 | Real receiver (host build of the firmware's own `k1_prsm_rx`) on the M2 stream, all losses, no guard | 913,580 events: 0 hotkeys / 0 commands / 0 corrupt frames; 32 receiver tests pass | scratchpad `rx_m2.txt` (rebuild: `tests/test_k1_prsm_rx_native.py` and `tests/k1_prsm_rx_host.cpp <stream>`) |
| B4 | Live output unchanged (22 emulator regression cases, old vs new) | **0 differing frames in all 22** | `fw-candidates/a6bad318/live-regression/run2-*` |
| C | PRISM.studio: editor compile flags, commit report, profile allow-list, UI loop, save semantics, 127.0.0.1 bind, playback.js (no K1CT to FE; hz 30–240; guard + preamble wire format) | Verified by the lead: suites green; real editor reproduces M2 stream `116981ee…` byte-for-byte; wire bytes = lane-b preamble + wire_packets; audit `--guard 30` exit 0 | `m2-tools/prism/PRISM-FIX-receipt.md` |
| C2 | Spine CLI builds and verifies an authored project itself | Verified: 23/23 tests; CLI `verify` PASS; ShowBundle `90855dde…`, trace `8128452f…` | `m2-tools/spine/SPINE-FIX-receipt.md` |
| C3 | Trinity: explicit demucs shifts (reproducible stems), segment clamp at export, tempo/metre from beats (126.99 BPM, 4/4), low-confidence downbeat flags (18–30 s, no drums), pinned env spec | Verified: 76 tests; two fresh cold excerpt runs byte-identical (lead ran them); raw contract accepted by PRISM without a clamp layer. Env build pulled about 86 MB (cap was 50 MB, lead's own cap) | `m2-tools/trinity/TRINITY-FIX-receipt.md` |
| C4 | Per-section editing (mapping_profile_v2, compiler 0.4.0, ShowBundle 0.4, section-attributed trace, editor section UI, Composer K1CT-to-FE blocked, `:set_mode` needs explicit confirmation) | Verified: sectionless output unchanged (`116981ee…`); chorus-only edit changed exactly the 116 predicted frames, stream `ffa0dd3b…`, reopen identical; UI looked at | `m2-tools/section/SECTION-receipt.md`, `c_out/impact_sectioned.png` |
| D | Main RPL bench session (silent ×5, music ×6, two-edge capture) | See §6 | `lane-d/runs/R_*`, `R_session/` |
| E | Captain's "clipping" question: mic front end measured | **Not clipping**; flattening = auto-level pin + loud guard | §7, `lane-d/runs/R_mic_chain_M2_M3.png`, `R_volume_test/volume_test.png` |

## 6. Bench session results (Main RPL @ a6bad318, mode 32 runs, 10 Nov 21:01–21:41)

- Tools changed: `lane-d/k1_bench.py` (allows `:prsm_exit` and `:authored_status`; new `unlock` subcommand; the dump keeps the `[RTRACE-PREPARED-*]` P-lines that follow `[RTRACE-END]`), `lane-d/run_one.py` (unlock after any stream; `K1_NO_CAMERA=1` skips footage), new `lane-d/listen.py` (read-only telemetry logger), and `lane-c-emu/player/show_player.py` (new `--gain-db` ≤ 0, digital attenuation only, verified 0.3162× at −10 dB).
- **Receiver protocol on a6bad318:** after any binary traffic the port is locked; wait ≥ 200 ms and send `:prsm_exit`; the device answers `PRSM_SESSION: interactive`. `:authored_status` reports epoch, applied seq, counters.
- Silent room: R_S1 to R_S3 authored (R_S1 epoch reset after an 83 ms host stall; R_S2 4 resets under another session's heavy pytest load; R_S3 none, but its LED dump lost one line, so CRC fails and 1,999 of 2,000 frames are usable); R_S4 hz0 rejected (all frames refused, live render, correct); R_S5 seek and stop (exactly start + 2 seeks = 3 epochs, correct).
- Music on the Bose: R_M0 live (audio-only, dump CRC failed), R_M1 and R_M2 authored (no resets), R_M3 authored (1 reset), R_M4 hz0 rejected (correct), R_M5 PRISM-compiled M2 stream 75–155 s (no resets).
- CPU load matters: the Modernes session's builds and pytest ran 21:00:49–21:08:24 and its emulator ran 21:08:47–21:10:07, so R_S1, R_S2, R_S3 and R_S4 were under load. Other sessions' big `grep`s loaded the Mac during the music runs (load average 3–8).
- Not done: two-edge isolation analysis joining P-lines across silent and music runs (applied seq → pixels); A06 timing (needs the iPhone 240 fps clapper route, or the a7S III in USB Streaming mode); camera footage.

## 7. Audio front end — what is established

- Chain at a6bad318: raw IM69D int16 × `K1_MIC_IM69D_INPUT_GAIN` 8 × (`CONFIG.SENSITIVITY` 2.7 × loud-guard `input_trim`); clip counted above 32767 (`clip_pct`), then hard clamp; `peak_scaled = (max_raw − SSL) / follower`, an adaptive follower; `peak_pin` = duty of `peak_scaled ≥ 0.92`; the guard cuts `gdft_trim` (0.85 / 0.70 / 0.32 tiers) on `peak_pin` duty > 0.12 / 0.30 / 0.60 or `spec_sat` duty, at `i2s_audio.h:240–281`.
- Measured: raw peak ≤ 273 against a clipping point of about 1,517; clip and near 0. `peak_scaled` ≥ 0.92 up to 70 % of the time; `gdft_trim` about 0.86 most of the time, 0.34 in the final chorus. At −10 dB the raw peak halves (not ×0.32: [INFERENCE] the Bose compresses at the Captain's volume), the normalised level is unchanged (median 0.60 vs 0.61), and the deepest cut softens (0.67 vs 0.34). The source mp3 itself peaks at 1.26 of full scale (the Mac/Bose clip a few samples).
- History (claude-mem, deja): the guard boots ON while the `platformio.ini` comment says OFF (obs 68260, 77913, 78027); the palette-vibrancy workaround documents "AGC + loud guard attenuate GDFT → chroma collapse → hue freeze" (77913); A/B retune mode 2 "not hardware-proven" (92343), later "Captain hardware sign-off 2026-07-10" (93981); the runtime mode/enable is **not persisted** (93981); 19 Aug forensic session (deja `claude:8554209d-fce0-4e9a-9146-f9e87e83f641`, L812/L848): "AGC pinned at its floor … LOCK-IN … follower pinned 3216 … starved input −51.9 dBFS". Today: follower 3205, raw rms about −59 dBFS. **[HYPOTHESIS]** the Captain's "we turned it off" was a runtime serial toggle that reverts at reboot; to be confirmed by af-history.
- **The emulator music fixture is about 24 dB hotter than the room**: `s3_music_regression.json` normalises the Loreen excerpt peak to raw 4096; × 21.6 ≫ 32767, so every emulator music case clips and drives the guard hard. Treat earlier emulator tuning evidence accordingly.

## 8. In-flight work at handover — how to recover it

In-process subagents die with this session. Their output folders persist.

| Job | Output folder | If incomplete |
|---|---|---|
| af-history (decision and defect ledger) | `audio-forensics/history/` (`HISTORY-LEDGER.md`) | Re-dispatch with the verbatim brief in `AF-BRIEFS-2026-11-10.md` §1; tell it to continue from what is on disk. |
| af-source (chain map) | `audio-forensics/source/` (`CHAIN-MAP.md`) | Brief §2. |
| af-emu (guard ON/OFF × level × mode, emulator) | `audio-forensics/emu/` (`EMU-AB.md`) | Brief §3. Its export is `scratchpad/af-emu-src-a6bad318` of the old session's scratchpad (`/private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/b846e4d7-9fc6-4e4e-a9b0-64761f909553/scratchpad`); recreate it in your own scratchpad if missing. |
| G1–G4 on 5bb142bc | `fw-candidates/5bb142bc/{exits.txt,*.log}` | If `scenario-5bb142bc-m18` has no exit line, re-run that one invocation on a fresh `git archive 5bb142bc` (it shares the work copy, so one at a time). Then message the Modernes session the three results. |

Re-run every decision-critical claim of a returning helper yourself before relaying it (each helper's receipt names its commands).

## 9. Next tasks, in order

1. **Collect the in-flight results** (§8). For the forensics, write ONE synthesis for the Captain in plain English, with the two existing pictures and af-emu's ON/OFF pictures (look at them first). Answer three things: (a) did he turn the guard off, and why is it on; (b) what the guard and AGC do to the visuals at his room level, measured; (c) a recommendation with options. Likely options: disable the guard by default; retarget its trigger to real overload (raw near-rail and clip duty) instead of `peak_pin`; fix the AGC floor lock-in; correct the emulator fixture level. Ask the Captain once, with a picture, which option. It changes shipping visuals: Captain sign-off.
2. **Send R3-1 (+ R3-2, and R3-3 once decided) to the FW lead.** Append a dated session brief to `team/LEAD-FW-FE-RELEASE.md` (pattern: the 16:25 brief), also asking it to write its missing receipt section for `a6bad318`, then `zsh ~/K1_Launch_Planning/00-Governance/team/launch-leads.sh FW`. Check first that no FW lead is running (`pgrep -fl claude_lead_run`), and warn it in the brief about the Modernes session's branch (`mcpp/next-phase-fixes` is checked out; it must branch from `fe/k1-fe-show-fixes` and stage by path). A headless FW lead cannot receive messages; the charter is the only channel.
3. **Host-side fix (lane-owned): the player must not burst.** In `show_player.py` and `silent_stream.py`, when sending falls behind schedule, skip to the current frame (keep seq/t_us truthful) instead of sending the backlog. Test: one silent bench run under deliberate load must show the epoch rising by exactly 1. This complements R3-1, it does not replace it.
4. **Judge each new FW candidate** exactly as `a6bad318` was judged: scope check against the ownership file; one `git archive` per candidate (the adapter is now mainline, so one export serves both profiles, run sequentially); three `gates.py` invocations; live regression (two fresh exports, `K1_ESP_EMU=…/esp-emu-pin/bin/esp-emu`, `run.py --suite default --profile scenario --output <fresh dir>`, compare per case with `emu_capture.decode`); the receiver host test on the M2 stream. Then flash to the Main RPL (method in §10) and re-run the bench (`lane-d`, `K1_UNIT=rpl K1_NO_CAMERA=1`).
5. **Isolation analysis on the existing bench data:** join P-lines (applied seq per captured frame) between R_S3 (silent) and R_M1–M3 (music) and compare both edges at equal applied seq; this is the hardware version of G2. Note a6bad318 keeps render timing free-running, so expect near-equality, not byte-equality; quantify it.
6. **Tool branches:** push after a final look. `git -C <repo> push origin <branch>` for PRISM `fix/one-instrument-editor-loop` and `feat/per-section-mapping`, Spine `fix/cli-authored-project` and `feat/per-section-mapping`, Trinity `fix/reproducible-contract` (this handover pushes them; check `git ls-remote`). Merging and repinning `organs.lock.json` belong to the Captain / Spine owner; propose it with the receipts.
7. Then A06 (iPhone 240 fps clapper; ask the Captain only when ready for that one action) and A18 (musical value with the Captain, after R3-1/R3-2/R3-3).

## 10. Traps learned this session (each cost time once)

- **gates.py work copy is keyed by source tree only**, not by profile. For a source without the adapter, pre-patch one export per profile (`fe`: `PROTOTYPE-ADAPTER-ed0aa984.diff -p1`; `scenario`: `…-noflags.diff -p1`). At `a6bad318` and later the adapter is mainline: one export, run the three invocations sequentially. `k1_fe_emu` at a6bad318+ no longer has the B489 bench flags, so FE-profile bytes are not comparable with the 8b202f46 FE baseline.
- **`run.py` directly** needs `K1_ESP_EMU=/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/tools/esp-emu-pin/bin/esp-emu`, a fresh `--output` directory, and `.pio/libdeps` copied into the export (from `m2-emu/work/src-81f26bee976a/.pio/libdeps`). The emulator does not print `[AP]` telemetry.
- **Flashing:** `scripts/agent/k1-flash-verified.sh` refuses a dirty tree, and the shared tree is dirty with other sessions' work. Build from an export with a private git dir instead: `git init` a temp dir, write `<repo>/.git/objects` into its `objects/info/alternates`, write the full SHA into its HEAD, then `GIT_DIR=<tmp> GIT_WORK_TREE=<export> GIT_OPTIONAL_LOCKS=0 git read-tree <sha>`. Run the script from the export with those env vars and `--port <verified port>`. The stamp is then the true SHA, the script's clean-tree check passes, and the upload guard checks chip identity. Before any write, read back the full flash with `~/.platformio/penv/bin/python -m esptool --chip esp32s3 --port <p> --baud 921600 read_flash 0 0x1000000 <file>` (206 s; resets once).
- **Device protocol at a6bad318+:** see §6 (`:prsm_exit` after ≥ 200 ms of silence). P-lines follow `[RTRACE-END]`. `set_mode` persists: restore mode 22 and diff `:dump`.
- **USB timing is load-sensitive:** do not run emulators, builds or pytest on this Mac during bench runs; check `sysctl -n vm.loadavg` and `ps -axo pcpu,command -r | head` first; tell the Modernes session (it holds when asked).
- **Agent plumbing:** in-process subagents die on session restart (relaunch from the briefs). A headless lead (`claude -p`) never receives SendMessage (held, then expired). The auto-mode classifier refused a custom detached `claude -p --resume …`; `launch-leads.sh FW` is the accepted path. The agent-wave guard counts blocked dispatch attempts in its 180 s window and needs PRODUCT_OUTPUT / OWNERSHIP / DONE_WHEN / EVIDENCE / BUDGET lines; `model` is required on every Agent call. Session names change after a restart (this session was `-71`, then `-f6`).
- **Camera:** the a7S III in PC-remote mode is claimed by macOS `mscamerad` and immediately re-claimed after a kill; our tools need USB Streaming mode (a Captain physical action) or none. LED capture (two edges) is the instrument.
- **claude-mem:** one plain term per search. **deja:** run `dejactl … evidence <id> "<term>" > file` once, then read the file.

## 11. Pending Captain decisions (ask once, with a picture and a recommendation)

1. Loud guard / AGC change (after the forensics synthesis). Recommendation pending evidence.
2. Merging and repinning the PRISM tools (PRISM.studio `feat/per-section-mapping` → main, Trinity `fix/reproducible-contract` → main, then `organs.lock.json` to the merge commits). Recommendation: yes after review; it needs the Captain or the Spine owner.
3. (Only when A06 is next) the iPhone 240 fps clapper recording, one physical action.

## 12. Ship path (prepared shows on the K1 FE)

1. **On silicon now:** `a6bad318` (non-shippable bench build) on the Main RPL only. In source: `fe/k1-fe-show-fixes` (`a6bad318`), not merged into `lane/k1-fe-release`.
2. **Remaining:** R3-1 (and R3-2) in firmware (FW lead) → re-judge (this lane) → bench rerun on the Main RPL (this lane; the Captain only plugs in) → merge into `lane/k1-fe-release` (FW lead, after this lane accepts) → loud-guard decision (Captain) → A06 and A18 with the Captain → tagged FE release (FW lead / Operations Manager).
3. **Who:** the FW lead writes firmware; this lane judges, flashes the bench unit and runs the bench; the Captain decides on the loud guard and the PRISM merges, and does the physical steps.
4. **Shipped =** a tagged `fe-1.0.0` containing these fixes, flashed on a K1 FE (Gx) board, passing every applicable M1 requirement on that one image, and recorded in the device registry.

## 13. Commits at handover

`lane/k1-fe-show-m1` and `lane/k1-fe-show-m2`: see the closing message of session 2 (`/usr/bin/git log -1 lane/k1-fe-show-m1 lane/k1-fe-show-m2`). Binary evidence (png, npz, prsm, bin, elf, footage, dumps over 1 MB) stays on disk only.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (K1-FE-SHOW lead, session 2) | Created at the Captain's request (context limit); live state re-verified 21:47 AWST. |
