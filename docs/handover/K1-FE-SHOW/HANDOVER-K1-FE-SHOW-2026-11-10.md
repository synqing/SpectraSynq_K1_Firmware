---
abstract: "Handover for the next lead of K1-FE-SHOW (PRISM prepared-show work on the K1 FE firmware), written 10 Nov 2026 15:55 AWST. M1 (prepared Prim8 stream drives the real K1) is PARTIAL; M2 (creator loop, host-side) is proven end to end on one real track; executable emulator gates exist for the firmware fixes. Firmware fixes are the FW lead's (change requests ranked). No device is connected that this lane may use. Read this file whole before acting."
---

# Handover — K1-FE-SHOW lead, 10 November 2026

Written by the outgoing lead (Claude, session spectrasynq-k1-firmware-71) at the Captain's request. Every fact below was checked in this session unless marked **[UNVERIFIED]**. Commit hashes are short SHAs in `~/SpectraSynq_K1_Firmware`; use `/usr/bin/git` (plain `git` is a reformatting wrapper).

---

## 1. Mission and one-paragraph state

**Mission.** Make PRISM's offline "recording → prepared show" path drive the real K1 safely and deterministically on both edges, and make the creator loop (generate, edit, save, reopen, replay) usable — without taking the Captain's time from the Founders' Edition (FE) board and launch. Programme destination: 100 paid K1 FE units shipped. Authority: `~/K1_Launch_Planning/00-Governance/COURSE-2026-11-02.md` (9 Nov 18:45 and 19:30 entries grant a **bounded exception**: host-side PRISM work by agents; one Captain bench session for M1; PRISM/K1-S3 firmware lane and all hardware lanes stay parked; FE firmware source changes only via FW-lead change request).

**State.** Three tests, never conflated: **T1** timed-command transport smoke — NOT RUN (optional; would write flash). **T2 = M1** prepared Prim8 stream drives the renderer on both real edges — **PARTIAL** (bench session 9 Nov on B489A500; see §6). **T3 = M2** creator loop — **host loop PROVEN** on the real Loreen track through Trinity → PRISM compiler (locked) → authored edit → save/reopen/reproduce → Prim8 stream → emulator playback (§7). Remaining work is mostly firmware (FW lead) and PRISM tool defects (owners), then one bench rerun.

---

## 2. Live state (verified 10 Nov 2026 15:48–15:55 AWST)

| Item | State |
|---|---|
| Shared working tree `~/SpectraSynq_K1_Firmware` | branch `lane/k1-fe-release` @ **`8b202f46`** (FW lead rc2 receipt). Only change: untracked `docs/plans/MODERNES-CPP-EXECUTION-PLAN.md` (not ours — leave it). The 9 Nov staged edits are now committed by the FW lead (`e2e83e53`). |
| FE lane commits after this lane's base `407fdf6f` | `125f7c61` registry (10 Nov B489 LED-count tests + Main RPL rewire), `e2e83e53` mode-32 silence fix, `e28dd927` serial input validation + noise-cal reset moved to audio core, `aac13ff9` Modernes C++ record, `c44172fa` K1-FE-Gx board profile on the FE lane, `545f00e4` G5 bring-up sheet, `8b202f46` FW lead receipt (`docs/handover/RECEIPT-FE-FW-2026-11-10.md`). Tag `fe-1.0.0-rc2` → `545f00e4` (local). |
| This lane's branches | `lane/k1-fe-show-m1` (M1 evidence + corrections) and `lane/k1-fe-show-m2` (M2 + this handover) — committed and pushed at session end; see §13 for the final SHAs. Both are based on `407fdf6f`, NOT on `8b202f46`. |
| Hardware on USB | **Only** `/dev/cu.usbmodem112201`, USB serial `DC:54:75:EA:36:14` = the **parked DualMCU lane's K1-S3 unit**. Another lane marks it read-only. **Do not open, read or flash it.** Neither the Main RPL nor B489 is connected. |
| Main RPL (`9087A500`, USB `B4:3A:45:A5:87:90`) | Last read back 10 Nov 02:33 AWST (read-only `:build`, `:chip_id`, `:dump`): `BUILD: version=40103 git=2a620f7e epoch=1794248403 env=k1_main_rpl_im69d`, primary mode 18, LED_COUNT 160. `2a620f7e` = `68a684dc` (20 Oct) + Captain-ordered LED rewire (primary DIN 2/3, secondary 5/6; mic DATA 8 / CLK 9). Flashed 10 Nov by another session; previous image `68a684dc` read back and matched a clean build except 45 stamp bytes (registry changelog). No LED capture in this build. Plate lit on both edges (a7S III still, `_scratch/k1-fe-show-m1_20261109/lane-d/raw/rpl_plate_check_1.png`). |
| B489A500 (bench K1v2, USB `B4:3A:45:A5:89:B4`) | Last read back 9 Nov: `ed0aa984`, env `k1_fe_bench_b489`; our bench session restored it to mode 22 with all 30 `CONFIG.*` identical to session start. The FW lead's rc2 receipt asks the Captain to plug B489 back in (with 4 Nov wiring) for `k1_fe_bench_b489` proof. |
| Running jobs / subagents | None running. All lane subagents of this session finished. Nothing is playing audio. |
| Cameras / audio | a7S III on USB was left in **USB Streaming** mode (AVFoundation device `ILCE-7SM3`, 1280×720 @ 25 fps + camera microphone) **[may have changed]**. iPhone "EiP Camera" available via Continuity. Default output: "Bose Mini II SoundLink" (Bluetooth, 44.1 kHz). **The Bose is also the default INPUT (16 kHz headset mic) — never open it** (it would drop the speaker into telephone mode). Use "MacBook Pro Microphone" for audible checks. |

---

## 3. Read order (do not skip; on-disk beats memory)

1. This file.
2. `~/K1_Launch_Planning/00-Governance/COURSE-2026-11-02.md` (whole; 9 Nov 17:55, 18:45, 19:30 entries) and `team/OPERATIONS.md`, `team/LEAD-FW-FE-RELEASE.md`.
3. `~/SpectraSynq_K1_Firmware/docs/handover/RECEIPT-FE-FW-2026-11-10.md` (FW lead, rc2; findings 1–6 and "Needs Captain").
4. Repo `AGENTS.md`, `CLAUDE.md`, `.claude/CLAUDE.md`, `K1_CANONICAL_CONTEXT.md`, `docs/agent/AGENT_EXECUTION_STANDARD.md`, `docs/process/SPECTRASYNQ-GIT-DOCTRINE.md`, `docs/process/SPECTRASYNQ-HOUSEKEEPING-DOCTRINE.md`, `docs/hardware/device-build-registry.md` (deployed-state table and 10 Nov changelog rows).
5. Briefs: `_scratch/k1-fe-show-m1_20261109/BRIEF-K1-FE-SHOW-M1-REV2.md` (binding scope), `BRIEF-K1-FE-SHOW-M1.md` (Rev 1, lane structure/hard rules), `PLAN-K1-PRISM-2026-11-09.md` (Captain's plan; §1, §4, §6 P0–P2, §7 acceptance A01–A22, §10 evidence rules).
6. `_scratch/k1-fe-show-m1_20261109/CHANGE-REQUESTS-FW-LEAD.md` (revision 2 + 10 Nov notes) — what the firmware must do and how it is tested.
7. `_scratch/k1-fe-show-m1_20261109/lane-d/D-P2-receipt.md` — the bench session, **starting with its "Corrections, 10 Nov" section**, which overrides the original claims.
8. `_scratch/k1-fe-show-m1_20261109/SCOPE-RECONCILIATION.md` (Captain decisions recorded in §6).
9. M2 receipts: `_scratch/k1-fe-show-m2_20261110/m2-analysis/M2A-receipt.md`, `m2-compose/M2C-receipt.md`, `m2-emu/M2E-receipt.md`.
10. Firmware comparison: `_scratch/k1-fe-show-m1_20261109/fw-diff-rpl-vs-b489/FW-DIFF-INDEX.md`.
11. Lane receipts as needed: `lane-a/A-P0-baseline.md` (+ `CR-A3`, `CR-A7`, `CR-A8`), `lane-b/B-P1-contract.md`, `lane-c-spine/C-spine-receipt.md`, `lane-c-emu/C-emu-receipt.md`.

Do **not** use as current truth: anything in `BRIEF-K1-FE-SHOW-M1.md` that Rev 2 corrects; the registry's Main RPL deployed-state row if it still says `a08dc10e`; the 9 Nov handback wording "only a timing sensor remains" (withdrawn after the external review).

---

## 4. Captain rulings in force (with dates)

- **GPIO assignments are never locked** — pin maps are per-build references only (10 Nov). Never frame a pin change as a lock or ask the Captain to rule on pins. The check is only: each build carries the map of the board it is flashed to, and one shared flag must not silently impose one board's map on another build.
- **M1 bench session: done "tonight"** (9 Nov, both conditions: silent room + music on the Bose at current volume). **M2 host-side: yes, before G4** (9 Nov). Recorded in `SCOPE-RECONCILIATION.md` §6 (the course file itself was not edited — the Operations Manager owns it).
- **Use the a7S III** for footage (9 Nov). The Captain set it to USB Streaming.
- **"Approved to continue"** (10 Nov) covered the tool updates and analysis — **not a flash**. No flash go has been given.
- **External review accepted (10 Nov):** the compiler proof and the music-stream proof are separate; seek is a failure; receiver isolation must be fixed in firmware; prepared-source isolation is an exact both-edge requirement; colour must be diagnosed before any protocol change; A06 must not block M2. All applied in the receipts and change requests.
- Standing (global/repo): Wi-Fi permanently banned (BLE/BLE-MIDI only); no planted-fault/mutation testing; no wasted re-runs; one script per Captain action; plain-English summaries; ship path in any "not done" answer; instrument, not Captain eyes; never re-request approval already given; never raise Mac volume, never leave playback running; British English; no files on Desktop/Downloads; no extra worktrees/clones of the firmware repo; calibration (`N`/`Y`, `start_noise_cal`) only after the Captain confirms silence verbally.

---

## 5. Programme context the next lead must not miss

- **FE release lane now targets K1-FE-Gx** (`c44172fa`, tag `fe-1.0.0-rc2`): 5 V USB-C, no STUSB4500. `k1_fe` is **blocked on every unit** (including Main RPL) until a Gx MAC is registered at G5; the Gx image drives GPIO8 at boot, which is the Main RPL's microphone data line.
- **The FE board may be moving off the ESP32-S3** to a Waveshare ESP32-S31 (FW lead finding 1; Captain-led `~/Downloads/K1-FE-S31-*`, `~/Workspace_Management/Software/K1-FE-S31-G03-routing-work`) **[UNVERIFIED by this lane]**. If true, every pin map and the S3 firmware assumptions move. Do not act on it; ask the Captain only if it changes your next task.
- **BLE-MIDI is still not in `k1_fe`** (FW lead finding 2) — not this lane's job.
- **Merge hazard (both leads found it):** `wip/rpl-pins-20261110` moves `K1_MAIN_RPL_PINMAP_V1` LED pins to 2/3/5/6, and `k1_fe` inherits that macro. Merged as-is, Gx LED data would land on pins the Gx board uses for other functions. The FE lane still has 15/16/17/18 for the Main RPL map, so **any FE-lane `k1_main_rpl_im69d` build flashed to the rewired Main RPL leaves its plate dark.** A Main RPL test build needs the rewire selected per target board (a bench-only env/flag), done by the FW lead.
- Version numbers are not identity: both K1s report `version=40103`. Identity = `git` + `env` + `epoch` from `:build`, plus USB serial.

---

## 6. M1 (T2) — what was done and what is true

Bench session 9 Nov 20:57–21:45 AWST on **B489A500** (`ed0aa984`, `k1_fe_bench_b489`, WS2812 8-bit, LED capture of the primary edge only). No flash, reset or erase. Full record: `lane-d/D-P2-receipt.md`.

**Established (with the corrections applied):**
- An offline-prepared Prim8 stream (`lane-c-emu/stream/loreen_75_155_120hz_v2.prsm`, sha256 `eafb72ae…58fdd`, 9,600 frames @ 120 Hz, Loreen 75–155 s; made by `make_stream.py`, **not** by PRISM) influences the renderer: primary-edge position vs stream pressure r = 0.989 / 0.991 / 0.962 (silent room), 0.77–0.80 (music in room); secondary edge seen in footage only.
- Rejected input (every frame hz=0) has no effect (r 0.19 silent, 0.26 with music — same as live).
- Repeats correlate 0.93–0.99 (not identical output).
- Stop returns to live without freeze or stale replay.
- 30 reported `CONFIG.*` values restored (hidden state such as presets/show state not read back).
- Device tempo locked to 126–127 BPM on authored frames (track 127 BPM) vs 61–86 BPM wandering on rejected frames.

**Not met / open (M1 cannot close until these pass on one final image):**
1. Receiver isolation (stray/broken stream bytes reach hotkeys: `N`/`Y` noise calibration, `!`–`)` preset saves, `S` show save, `:` command mode). Host mitigation used: 30-NUL guard + 64-byte preamble + watchdog (0 shortcut bytes in 614,336 simulated losses, but 249,394 still accept one garbage frame; assumes one 64-byte write = one USB packet, unmeasured).
2. Prepared-source isolation: live mic peak is OR-ed in (`light_mode_waveform_hybrid_k1.cpp:116`), auto colour shift keeps running, possible `silent_scale` dependency.
3. Seek reconstruction **fails** (colour changed and stayed after a backward seek; emulator G3 confirms persistent state).
4. Colour under authored mode: one flat palette colour; CR-A7 says an energy-driven colour walk exists — diagnose before any protocol change; do not repurpose `heat/space/gravity`.
5. Applied-state observation (no `:authored_status`; acceptance inferred).
6. Two-edge native capture on the bench unit.
7. A06 audio-to-light timing: **BLOCKED / unmeasured** (no common-clock rig; a7S III USB stream is 40 ms/frame). Routes with existing equipment, uncertainties and status: `D-P2-receipt.md` "A06-MEASUREMENT-ROUTES" (best candidate: iPhone 240 fps slow motion with audio + clapper calibration; R3 oscilloscope/logic-analyser inventory unconfirmed — ask, buy nothing).

**Audio playback incident (Captain heard stutter on the first music run):** cause reproduced by factorial test — the player's 64-frame `latency="low"` buffers on the Bluetooth output + a Python busy-wait pacing spin (late callbacks 4.4–7.8 % with the spin, 0.01 % without; video-encode load not material; underflow flag stayed 0 in every case, so it cannot detect this). Fixed: `blocksize=4096, latency="high"`, sleep-only pacing. Verified: digital loopback sample-exact (BlackHole, gain 0.158 = its device volume), and audible check via MacBook mic: 0 stutter holes for the fixed player and for `afplay` (reference); camera-mic recordings of the 9 Nov runs: stutter run 21 holes / 65 s, five fixed runs 0. Playback reliability ≠ synchronisation: timing remains unmeasured. A local bug-report draft (feedback tool) exists about this incident; its repro line mentions the video-encode load as a factor, which the factorial later showed is **not material** — correct that before anyone sends it. Do not send it without the Captain.

---

## 7. M2 (T3, host-side) — what was done and what is true

**Chain proven on the real track (Loreen, `/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3`, sha256 `a62e1f09…b9b0f`, approved as a repo regression fixture, not a Captain show sign-off):**

| Hop | Result | Evidence |
|---|---|---|
| Analysis (Trinity, locked `e271af39`, clean) | Full track analysed; retained cache; cold run 347 s (1.55× real time), warm 0.5 s byte-identical. 462 beats, 131 downbeats, 15 segments. | `m2-analysis/M2A-receipt.md`; `out/loreen/` (raw contract `18581f4c…`, stem_features `9053c7ad…`) |
| Contract into compiler | Raw contract **rejected** (last segment end 223.92 s > track 223.910023 s); disclosed 9.98 ms clamp layer `out/loreen/consumer/contract.json` (`f17a0c05…`) accepted. | `consumer/corrections.json` |
| Compose + compile (locked PRISM `cc00556d`, compiler 0.3.1, clone at `_scratch/k1-fe-show-m1_20261109/prism-studio-locked`) | Compile twice identical; pre-edit ShowBundle `cae4fbc1…`, Intent Trace `9491b071…`. | `m2-compose/M2C-receipt.md`, `projects/loreen/out/` |
| Authored edit | impact `beat_amp` 48000 → 12000 (bar accent), predicted before comparing; result matched: only Prim8[1] changed, 1,582 frames in 331 off-downbeat windows, ×¼ ±1; 131 downbeats and all other channels byte-identical. | `projects/loreen/diff/stream_channels.png` (read) |
| Save → reopen → recompile | Post-edit ShowBundle `90855dde…`, Intent Trace `8128452f…` — identical after reopen. | `out/post_edit/`, `out/reopen/` |
| Prepared stream | `projects/loreen/stream/loreen_post_edit_120hz.prsm` sha256 `116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3`, 26,870 frames, 120 Hz, device_profile none; reopened twin byte-identical; all frames byte-equal to PRISM `cdc.js` makePrsmPacket; validator VALID; byte audit `--guard 30` BENCH-ELIGIBLE, 0 hotkeys (lead re-ran both). | `stream/`, `stream_reopen/` |
| Emulator playback (G4) | PASS: 75–155 s window, both edges, reached AUTHORED, 9,599/9,599 RX records consumed; M2 stream and twin byte-identical on both edges — on FE config (`k1_fe_emu`) and Main RPL proxy config (`k1_main_rpl_emu`), modes 32 and 18. | `m2-emu/M2E-receipt.md`, `m2-emu/runs/*/gates.md` |

**M2 defects found (reported, not fixed — the trees were read-only for this lane):**
1. PRISM editor `/api/instrument/compile` passes `--contract/--stem-features`; compiler 0.3.1 wants `--in/--stems` + `--coverage-out/--manifest-out` → always HTTP 500; default `compiler_commit` is `e37c7da` (not the lock); profile allow-list rejects authored profiles (HTTP 400); `app.js` never calls compile; editor bundle saves are overwritten by recompile; server binds all interfaces.
2. Spine CLI hard-codes `mapping/prim8_natural_v1.json`; `verify --project` ignores `mapping_profile_path`; build manifest records compiler 0.3.0 while 0.3.1 runs; `organs.local.json` points at `.g5r-clean/PRISM.studio` = `07eb822` (0.3.0), not the lock `cc00556d` → `verify` fails `COMPILE_MANIFEST_MISMATCH` on today's checkouts (green only with `PRISM_ROOT=<locked clone>`). Workaround used: `m2-compose/tools/compose.mjs` (repeats Spine compileOnce/verify exactly, writes only to the lane).
3. No per-section scope in `mapping_profile_v1` / compiler 0.3.1 (edits apply to the whole track).
4. Trinity: `analyze_track.py:312` drops `--demucs-shifts 0` → stems not reproducible from source (retained cache is the only reference); `export_contract` does not clamp segment ends; contract `bpm` 125 (grid-quantised; beats give 127.27) and `6/4` metre are wrong — drive nothing from them; 18–30 s has 17/30 beats marked downbeat; shared conda env `trinity-music-intent-v0_1` cannot run Trinity (wrong natten, two OpenMP runtimes) — a lane-local env was built at `m2-analysis/conda-env/`.
5. PRISM `playback.js` sends K1CT PARAM_SET frames when `device_profile != "none"` (FE has no K1CT parser → bytes hit hotkeys); its 250 ms freshness comment is stale (device uses 50 ms); host allows hz 1–1000 but the device accepts 30–240.

---

## 8. Emulator gates — the acceptance tests for the firmware fixes

`_scratch/k1-fe-show-m2_20261110/m2-emu/gates.py` (sha256 `e1feb2fb…`). Results on `ed0aa984` (FE and Main RPL proxy configs, modes 32 and 18):

| Gate | Meaning | Today |
|---|---|---|
| G1 | prepared stream repeat runs byte-identical on both edges | **PASS** |
| G2 | changing unrelated live mic PCM must not change either edge (passage vs zero vs other music) | **FAIL** (1,705–1,778 / 1,778 frames differ) — acceptance test for prepared-source isolation |
| G3 | same musical position by continuous / forward-seek / backward-seek agrees after the declared reconstruction interval R = 5.0 s (667 hops) | **FAIL** (594–667 / 667 differ; pulses at beat rate, persistent state) — acceptance test for seek reconstruction (only isolates prepared-state once G2 passes) |
| G4 | the M2 compiled stream and its reopened twin produce identical frames | **PASS** |

Usage (from `M2E-receipt.md` §gates.py):
```
cd /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-emu
PY=../../k1-fe-show-m1_20261109/lane-c-emu/.venv/bin/python
C=../m2-compose/projects/loreen
$PY gates.py --src <candidate git-archive export> --profile fe --mode 32 \
   --m2-stream $C/stream/loreen_post_edit_120hz.prsm --m2-twin $C/stream_reopen/loreen_post_edit_120hz.prsm
$PY gates.py --src <candidate export> --profile scenario --mode 32 ...   # Main RPL config; repeat with --mode 18
$PY gates.py --analyse runs/<run dir>                                    # re-judge without the emulator
```
Exit code = number of non-PASS gates (expected today: 2). ~10 min per invocation; one invocation per source tree at a time. The emulator RX adapter is a **prototype** (`lane-c-emu/PROTOTYPE-ADAPTER-ed0aa984.diff`, sha256 `a253f2d9…`): bytes enter the production `check_serial` loop, not the USB peripheral, so USB loss is not modelled. Emulator timing is lockstep — never physical latency. The emulator captures the WS2816 path; B489 bench output is WS2812 (bytes not interchangeable); the Main RPL is WS2816. The resident Main RPL source `2a620f7e` predates the replay stack (no graft — lead ruling): the Main RPL proxy is `ed0aa984`'s `k1_main_rpl_emu` (its `-D` set = `k1_main_rpl_im69d` + 4 emulator flags; `platformio.ini` `[env:k1_main_rpl_im69d]` and `[env:k1_hardware]` sections byte-identical between `ed0aa984` and `2a620f7e`). The Waveform Hybrid `sat_ema` difference sits under `K1_POSITION_SMOOTH_V1`, defined in no device or emulator build — irrelevant to G3.

---

## 9. Firmware comparison (asked by the Captain 10 Nov)

`_scratch/k1-fe-show-m1_20261109/fw-diff-rpl-vs-b489/FW-DIFF-INDEX.md` (+ `catalogue_core.md` 38 files/142 items, `catalogue_visual.md` 54 files/91 items, `build_defines_diff.json`, `compiled_image_diff.json`, `settings_diff.json`, `commits_classified.tsv`). Main RPL `2a620f7e` vs its previous image `68a684dc`: only the four LED output drivers moved (15/16/17/18 → 2/3/5/6). Main RPL vs B489 `ed0aa984`: 172 commits; 92 firmware files (+6,752/−442); images 728,320 vs 807,552 B; 81 shared defines, 3 only Main RPL, 15 only bench; 12 of 30 settings differ. Notable: Main RPL saves settings 5 s after any change even mid-song (LEDs pause); bench waits for quiet or 60 s. Main RPL loop clock wraps every 71.6 min. Main RPL incandescent green term always 0 (reverse-order path only). Main RPL with reverse order ON skips primary WS2816 output setup. Bench has 14 FX battery modes (38–51), line-in, sub-110 Hz filter, LED capture. Note: these compare against `ed0aa984`; the FE lane has since moved to `8b202f46`.

---

## 10. Pending Captain decisions (ask once, with a recommendation; never re-ask)

1. **Phase 1 go:** let the FW lead implement change request 1 (receiver isolation) + the metadata fix now, ahead of G4. Recommendation: yes — it is a robustness defect of the shipping firmware, small, and gated by host oracles.
2. **PRISM repo write access:** allow agents to fix the §7 defects in PRISM.studio, the Spine and Trinity (until now read-only). Recommendation: yes for items 1, 2, 4, 5 (small, mechanical); per-section mapping (3) after the Captain sees the creator flow.
3. **Bench unit and flash go:** which K1 is the bench unit (the FW lead wants B489 back for `k1_fe_bench_b489` proof; this lane prefers the Main RPL for WS2816 parity), and a flash go for a capture-enabled test build with that unit's pin map once the fixes pass G1–G4. Recommendation: Main RPL for prepared-show work, B489 for the FE bench proof — they are different jobs.
(Already decided — do not re-ask: bench tonight (done), M2 host-side yes, both audio conditions, a7S III, GPIO never locked.)

---

## 11. Next tasks, in order (executable without the Captain unless marked)

**A. Rebase the lane's baseline on the current FE head (no device).**
- Create a clean export of `8b202f46` (`/usr/bin/git archive 8b202f46 | tar -x -C <scratch>/src-8b202f46`) and run `gates.py` on it for `--profile fe --mode 32` and `--profile scenario --mode 32/18` with the M2 stream. Acceptance: G1 PASS, G4 PASS, G2/G3 FAIL as before (declare expectations first); any other outcome is a finding caused by `e2e83e53`/`e28dd927`/`c44172fa` — diagnose it before anything else. Note the adapter may need re-applying (gates.py tries the ed0aa984 diff, then 407fdf6f).
- Re-point Lane B's differential oracle (`lane-b/oracle/`, snapshot of `407fdf6f`) at `8b202f46` and confirm the PRSM scanner/hotkey verdicts are unchanged (sources identical per `git diff --stat 407fdf6f 8b202f46 -- audio/k1_prsm.* audio/k1_authored_source.*` = empty; `check_serial` scanner lines unchanged).

**B. Hand the firmware work to the FW lead (do not implement FE source yourself).**
- Send `CHANGE-REQUESTS-FW-LEAD.md` revision 2 as the brief (items in priority order: receiver isolation + metadata; prepared-source isolation + deterministic colour start; seek reconstruction; applied-state observation + two-edge capture; provenance before flash; per-board pin-map selection for the Main RPL test build). Every candidate is judged by `gates.py` (G1–G4) and the Lane B oracle on a clean export of the candidate commit; the orchestrator re-runs those itself before accepting.
- If no FW lead session is active, report that to the Captain as the blocker; do not take over FE source without his word.

**C. PRISM tool defects (only after decision 2).** Fix in their own repos on branches, one writer per repo, with the repos' own tests; re-run the M2 loop (`m2-compose/tools/compose.mjs` flow) through the real editor/CLI afterwards; never repin `organs.lock.json` without the Captain/Spine owner.

**D. Bench rerun of M1 (needs decision 3 + a flash go + the Captain's physical setup).** On the fixed candidate with LED capture and the bench unit's pin map: identity read-back → settings dump → silent-room runs (authored ×3, rejected hz0, seek+stop) → music runs (live, authored ×3, rejected) → restore → settings diff. Use the PRISM-compiled M2 stream (`116981ee…`, window frames 9000–18599) as well as the M1 stream. Add the iPhone 240 fps slow-motion A06 attempt with clapper calibration. M1 closes only when all applicable requirements pass on one final image.

**E. Musical-value test (A18)** after D: prepared vs live on several tracks, Captain's eyes, four yes/no questions (k1-light-show-law).

Do not: build new effects, new dashboards or orchestrators; run bench sessions before the fixes; buy measurement gear; touch the parked DualMCU unit; edit the course file (propose entries to the Operations Manager).

---

## 12. Hard rules and traps learned in this lane (each cost time once)

**Device safety**
- Identify by USB serial before any port open: `ioreg`/`serial.tools.list_ports` only; never `esptool read_mac` (it resets into the bootloader). Lane tools take `K1_UNIT=rpl|b489` and refuse anything else (`lane-d/units.py`).
- Read-only commands only unless a flash/config change is authorised: `:build`, `:chip_id`, `:dump`, `:smart_status`, `:rtrace_*` (capture builds only), `:ap_stream=0/1`. `set_mode` **persists to flash** (its table row wrongly says it doesn't); restore the resident mode afterwards and diff `:dump`.
- Listen passively first: if the first lines are not K1 product telemetry (`[AP] ...`), send nothing (`lane-d/read_ident_any.py`).
- **Never send a bad-magic or truncated PRSM frame to hardware.** Rejected-input tests use hz=0 / hz=241 / version=2 only. Every frame is one 64-byte write (30 NUL + frame, `prim8_stream.wire_packets`), with the 64-byte `RESYNC_PREAMBLE` before the first frame of every session and seek; run `lane-b/audit_prsm_bytes.py --guard 30` on the exact bytes first (must exit 0). Stream with device_profile none (no K1CT).
- Watchdog: any device line other than `[AP]` stops the session; `NOISE_CAL: armed / not armed` (including in the first line after open) = isolation failure → no writes for 5.5 s, end session (player exit 5); `NOISE_CAL: queued` = CRITICAL (exit 4) — calibration policy: Captain re-calibrates under confirmed silence. Never send `Y`, `N` or `:` automatically.
- The first line read after opening the port is usually the tail of an `[AP]` line — skip it (but still treat `NOISE_CAL` in it as an incident).
- LED capture dumps: pause telemetry with `:ap_stream=0` during `:rtrace_dump=1`, restore `=1`; verify CRC (`lane-d/k1_bench.py parse`, supports rgb8/rgb16, one or two edges); one automatic re-dump on CRC failure. Arm capacity: 3,000 frames (`every` 6 ≈ 90 s at ~200 render fps).
- Calibration: never fire `start_noise_cal`/`N`/`Y` yourself.

**Audio**
- Never change system volume or output device. Check `pgrep -lx afplay` and any prior player before playing; always stop playback on exit. The Captain hates stutter: verify any new player configuration silently (all-zero output) or on BlackHole first, then a short audible check recorded with the MacBook microphone — never play music to the Captain on an unverified path.
- Player (`lane-c-emu/player/show_player.py`, sha256 `c65fab85…`): 4,096-frame buffers, `latency="high"`, sleep-only pacing, seek aborts and restarts the output stream (audio held inside the Bluetooth speaker itself, ~0.18 s, is beyond its control — audible seek alignment is still untested). Exit codes: 0 ok, 1 refused, 2 stopped, 4 critical, 5 isolation failure. Bench wrapper: `lane-d/music_batch.sh` / `lane-d/run_one.py` (set `K1_UNIT`).
- The PortAudio underflow flag is blind to this machine's dropouts; judge playback by captured audio (`lane-d/audio_continuity.py` approach, `lane-d/audio_probe.py` for callbacks/loopback).

**Git and shared tree**
- The firmware working tree is shared with other sessions (FW lead). **Never** `git checkout/switch/stash/reset/add/commit` there. Commit lane work with a separate index: `GIT_INDEX_FILE=<scratchpad>/x.index; /usr/bin/git read-tree <lane-branch>; hash-object -w + update-index --add --cacheinfo for each file; write-tree; commit-tree -p <old>; update-ref refs/heads/<lane> <new> <old>`. `_scratch/` is git-ignored, so evidence is committed this way (text only, < 1 MB; footage, dumps, `.prsm`, `.npz`, images stay on disk with sha256 recorded).
- Push lane branches at session end (`/usr/bin/git push origin <lane>`); never merge to main; commit trailer `Verify: none|host|device:<chip>@<receipt>`; CHANGELOG entry via the separate index.
- Shell traps: plain `git`/`find` may be wrapped (`rtk`) — use `/usr/bin/git`, `/usr/bin/grep` (plain `grep` is ripgrep), `/usr/bin/find`; zsh doesn't word-split `$VAR` (`${=VAR}`); `curl` blocked; foreground `sleep` blocked; Homebrew Python 3.14 lacks pyexpat — use `/opt/homebrew/opt/python@3.13/bin/python3.13`; numpy/matplotlib/sounddevice live in `_scratch/k1-fe-show-m1_20261109/lane-c-emu/.venv/bin/python`; macOS `awk` has no `strtonum`; killing system processes by pattern is denied by the permission system (it was, correctly).
- Builds for analysis: clean `git archive <sha>` into the session scratchpad, `pio run -e <env> -v` (≈ 40 s warm). Don't build in the shared tree (collides with the FW lead; the stamp script reads the enclosing repo).

**Evidence**
- Gates start NOT RUN → PASS/FAIL/BLOCKED/NOT RUN; declare expected results before running; one run per change; no mutation testing.
- A subagent's claim is a hypothesis: re-run the decisive command yourself before relaying (this lane caught three mis-statements that way).
- Keep host send timing, device application timing and sound-vs-light timing separate; never call emulator timing physical latency.
- Look at every plot/picture you cite.

---

## 13. Evidence map and commits

- M1 lane: `_scratch/k1-fe-show-m1_20261109/` — `lane-a/` baseline + CRs; `lane-b/` contract, fixtures, validator, oracle, byte audit (163 tests); `lane-c-spine/` PRISM clone diff + golden path; `lane-c-emu/` stream, player, emulator adapter, C4 runs; `lane-d/` bench tools, runs (`runs/S*`, `runs/M*`, footage `a7s3.mp4`), analysis (`analysis/*.png|json`), receipt; `fw-diff-rpl-vs-b489/`; `CHANGE-REQUESTS-FW-LEAD.md`; `SCOPE-RECONCILIATION.md`; briefs + plan.
- M2 lane: `_scratch/k1-fe-show-m2_20261110/` — `m2-analysis/`, `m2-compose/`, `m2-emu/`, this handover.
- Session-scratchpad builds (not committed; reproducible with `git archive`): `/private/tmp/claude-501/-Users-spectrasynq-SpectraSynq-K1-Firmware/87b98bf8-1288-4f63-be43-da323d1116b3/scratchpad/fwdiff/` (exports + verbose build logs of `2a620f7e`, `ed0aa984`, `68a684dc`).
- Disk: `m2-emu/runs` 2.4 G, `m2-emu/work` 2.1 G, `m2-emu/src-*` 1.1 G, `lane-c-emu/runs` 3.2 G, `lane-c-emu/src-ed0aa984` 0.7 G, `lane-d/runs` ~1.3 G (footage). Everything cited by a receipt is evidence — delete only uncited build copies, after checking citations.
- Commits (filled at session end): see the closing message of the outgoing session and `/usr/bin/git log lane/k1-fe-show-m2`.

---

## 14. Escalate only for

Device identity mismatch; any flash/reset/erase; a Captain ruling that would be contradicted; a premise found wrong (e.g. the FE board leaving the S3 changes the target); calibration activity seen on a device; a product/strategy choice with no default here. Escalate with one paragraph and a recommended answer, and keep doing other authorised work meanwhile. Frustration is not a stop instruction; only an explicit stop is.

## 15. Closing report the next lead owes

Plain English, problems first; per test (T1/T2/T3); decisions only the Captain can make; next executable task; links to every artefact with sha256; ship path (already on silicon / remaining steps / who / the stamp that means shipped); delegation ledger if subagents were used.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-10 | agent:claude (outgoing K1-FE-SHOW lead) | Created at the Captain's request; live state re-verified 15:48–15:55 AWST (FE lane at `8b202f46`, only the parked DualMCU unit on USB). |
