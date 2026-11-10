---
abstract: "Handover from K1-FE-SHOW lead session 3 (10 Nov 22:00 to 11 Nov 04:30 AWST). The Captain ordered the audio front end rebuilt before fe-1.0.0 and gave this lane full authority. AFE2 stage 1 (one loudness meter, one slow anchor, applied to output brightness) is built, committed (fe/k1-afe2 a6113aaf), flashed to the Main RPL and measured on five tracks in the emulator and A/B on the bench. Three firmware branches now await one merge. Read this file, then AFE2-PLAN-2026-11-10.md, before doing anything."
---

# Handover — K1-FE-SHOW lead, session 3 (11 Nov 2026, 04:30 AWST)

Every fact below was checked in this session unless marked **[UNVERIFIED]**. Use `/usr/bin/git`. British English. AWST.

## 1. Where things stand, in one paragraph

The Captain's "clipping" complaint led to a first-principles finding: the old front end adjusts level in four places, all faster than a song section, so loud and quiet sections reach the effects at the same size. He ordered a rebuild now and gave this lane full control (verbatim in `audio-forensics/AFE2-PLAN-2026-11-10.md` section 0). Stage 1 of eight is done: a meter on the raw microphone, one slow anchor, and a brightness factor `how_much` on both edges for the live path. It adds a control and removes none yet. On the real unit, same passage, stage off then on: loud ÷ breakdown light 1.02 → 2.95. The Captain has **not yet looked at it on the plate**; that is the acceptance test.

## 2. Live state (verified 11 Nov 04:15 unless noted)

| Item | State |
|---|---|
| Main RPL `9087A500` (USB `B4:3A:45:A5:87:90`, `/dev/cu.usbmodem11301`) | `k1_main_rpl_show_bench` @ **`a6113aaf`**, epoch `1794338367`, mode 22, 30 `CONFIG.*` unchanged. Last confirmed by the Modernes session at 03:51 after it borrowed and restored the unit (its read-back sha256 `70367545…97da`). `:k1_afe` is ON at boot on this image. Not re-read by me after 03:51. |
| Recovery images | `bench-rpl-20261110/afe2/main-rpl-9087A500-full-flash-a6bad318-pre-afe2.bin` (sha256 `07f0ce2dbcb0971d5f26ed10f7c06ed8f71eb4cd47b536400cd9fddc4205ff61`); older `recovery/…2a620f7e.bin`. Flash logs: `afe2/flash.log` (7ea24446), `afe2/flash-a6113aaf.log`. |
| `fe/k1-afe2` | `a6113aaf` (parent `7ea24446`, parent `a6bad318`). **Pushed.** AFE2 stage 1 + timing probe + emulator allow-list. |
| `fe/k1-fe-show-fixes` | `c949151c` (fix commit `245ed510`: show survives lost frames; prepared shows at full level). FW lead finished with a receipt (`docs/handover/RECEIPT-FE-FW-2026-11-10.md` on that branch). **Not pushed. Gates G1–G4: 3 of 3 exit 0.** Not yet: live regression, receiver host test, flash, bench. |
| `mcpp/next-phase-fixes` (Modernes C++ session, cooperative, `uds:/tmp/cc-socks/46584.sock`) | head `71526424`; code candidate `bd5d5a83` = `77283663` + two routing lines (`:look_load` / `:look_clear` were unreachable since 21 Aug). **Gates on `77283663`: 3 of 3 exit 0.** `bd5d5a83` not gated alone by agreement: gate the merge. Not pushed. It says nothing else is pending from its lane. |
| Shared checkout `~/SpectraSynq_K1_Firmware` | on `mcpp/next-phase-fixes`, 10 uncommitted entries (not mine except the registry edit). **Never checkout, stash, reset, add or commit there.** |
| Device registry | `docs/hardware/device-build-registry.md` in the shared tree is still uncommitted and now stale: it must record 7ea24446, a6113aaf and the Modernes interim flashes (77283663, bd5d5a83, bd5d5a83 + `ENABLE_VP_PROBE_CMD=1`, all overwritten). |
| Lanes | `lane/k1-fe-show-m1` and `lane/k1-fe-show-m2`: pushed at handover (see closing message for SHAs). |
| FW lead | not running (finished 23:42). `team/FW-HOLD` was deleted on the Captain's order. |
| Background jobs | none of mine. Nothing playing. |
| Explainer | https://claude.ai/artifact/NUPD343KnvpNrfJ67z3E3y (private to the Captain). Source `audio-forensics/design/k1-audio-front-end.html`, built by `build_explainer2.py`. |

## 3. Read order

1. This file.
2. `audio-forensics/AFE2-PLAN-2026-11-10.md` — the execution plan. Eight stages, each with purpose, inputs, outputs, acceptance, failure, STOP. Do not shorten it. Update its section 6 as you go.
3. `audio-forensics/design/afe2_reference.py` — the specification of stage 1.
4. `audio-forensics/research_notes/K1 audio front end design/system_first_principles.md` and `audio-forensics/source/CHAIN-MAP.md` — the old chain, stage by stage with line numbers.
5. `HANDOVER-K1-FE-SHOW-2026-11-10-S2.md` sections 9, 10 (how to judge a candidate, how to flash) and `HANDOVER-K1-FE-SHOW-2026-11-10.md` section 12 (rules).

## 4. Captain rulings made this session

- **Rebuild the front end now, before fe-1.0.0; this lane owns it** ("take full control of this project as if it were your own… Do whatever the fuck is necessary"). This lane writes audio-front-end firmware itself. R3-3 is closed into the AFE2 plan.
- **All holds terminated** ("I hereby authorise the hold or any hold to be effectively terminated and removed").
- He paused the Modernes session at about 00:00 because too many jobs ran at once and everything slowed. **Run one heavy job at a time** (emulator, pytest, build).
- He ordered the Modernes session to test on the Main RPL; it did and returned the unit.

## 5. What was done, with evidence

| Work | Result | Evidence |
|---|---|---|
| Audio forensics collected and re-checked | Guard never off; mic never clips; flattening is structural | `audio-forensics/SYNTHESIS-LOUD-GUARD-2026-11-10.md`, `history/`, `source/`, `emu/analysis*` |
| Sender skips late frames | `lane-d/silent_stream.py` fixed; loaded run still reset 180 times on a6bad318 (firmware limit of 3 frames) | `lane-d/runs/T_S1_*`, `runs/T_session3/` |
| Hardware isolation join | silent vs music difference equals music vs music floor | `lane-d/isolation_join.py`, `runs/T_session3/isolation.json` |
| AFE2 stage 1 | host test: firmware module = reference within 0.00034 on 13,333 hops; emulator: off byte-identical to a6bad318 in modes 22, 32, 18; five tracks × modes 22 and 32: tracking and contrast up in 10 of 10, movement kept 89–99 %; gates 3 of 3 on 7ea24446 | `tests/test_k1_afe2_native.py` (on the branch), `emu/analysis-afe2/`, `emu/analysis-tracks/tracks.md`, `fw-candidates/7ea24446/` |
| Bench A/B, Main RPL | loud ÷ breakdown 1.02 → 2.95 (edge 1), 2.04 → 2.93 (edge 2); meter cost 44 µs mean, 83 µs worst per 7,500 µs hop | `lane-d/runs/B_M1_*`, `runs/B_M1_bench_ab.json` |
| Two of my own claims refuted by probes | level-path scaling inverts mode 32 (so the factor went to brightness); the dark chorus in mode 22 is the mode's own oscillator, not the pitch gate and not the guard | `emu/analysis-afe2-levelpath-v0/`, `emu/analysis-gate/gate.md` |
| Research | three sourced notes and a report | `research_notes/…/`, `reports/K1 audio front end design.md` |

## 6. Not done, and honest gaps

- **Full `pytest tests/` on `a6113aaf` did not finish**: it stalled at 31 % and was stopped (cause not investigated; the Modernes session was building at the time). First run on 7ea24446: 2,074 passed, 4 failed; 3 were pinned checks I then updated (now passing in a targeted run), 1 needs another env's libdeps in an export. Re-run it, alone.
- The explainer's last build (five-track table, bench A/B chart, interactive model) was published **without my looking at the new sections**. Its script parses; the JavaScript model equals the reference to 5e-6. Look at it once and fix what is off.
- `c949151c` and the merge are not yet judged beyond gates.
- dB SPL figures assume unity gain in the PDM converter (needs a sound-level meter beside the unit: a Captain physical action).
- Mode 22 draws only on the positive side of its oscillator (dark stretches). Stage 8; needs the Captain's eye before any change.

## 7. Next tasks, in order

1. **Re-read identity** of the Main RPL (`K1_UNIT=rpl python3.13 lane-d/k1_bench.py ident <dir>`); expect `a6113aaf`, epoch `1794338367`, mode 22.
2. **Full pytest on `a6113aaf`**, alone, in a clean export with a private git dir (method: section 8). Record the counts in `AFE2-PLAN` section 6 and in `design/pytest_final.txt`, rebuild and republish the explainer (commands: section 8).
3. **Merge the three branches** into one candidate on a new branch (suggest `fe/k1-fe-rc3`, parent `a6113aaf`): merge `c949151c`, then `bd5d5a83`. Do it with a private index or in an export, never in the shared checkout. Expected small conflicts: `serial/serial_menu.cpp`, `scripts/regression-harness/k1_serial_safety.py` (regenerate `TYPED_DEF_BLOB_SHA` with `git hash-object` and add any new command names), `tools/esp_emulator/run.py`. Then judge the merge exactly as handover S2 section 9 item 4: gates ×3, live regression (0 differing frames with `:k1_afe` at its emulator default, off), receiver host test, commit gate. Flash to the Main RPL, re-run the loaded silent run (R3-1 acceptance: epoch rises by exactly 1), and the bench.
4. **AFE2 stage 2** (one silence test from the meter), then stage 3 (guard's false trigger and spectrum actions), following the plan. Each stage: reference first, host test against it, emulator off-identity then A/B on the five-track suite, gates, flash, bench A/B. Each stage must delete what the plan says it deletes.
5. **Ask the Captain once**, when he is at the plate: play anything in modes 22 and 32 and compare `:k1_afe=off` / `:k1_afe=on`, then try `:k1_afe_gamma=1.5` and `:k1_afe_floor=0.4`. Measured: gamma 1 gives 0.32–0.63 dB of light per dB of sound; gamma 2 gave 0.46 on Loreen. Research supports 0.6–1.0.
6. Commit the registry file on the merge branch with every flash since 10 Nov 20:58 recorded.
7. Then A06 (timing) and A18 (musical value) with the Captain; tag `fe-1.0.0`.

## 8. Commands that work (each cost time once)

- Paths: `R=~/SpectraSynq_K1_Firmware`, `M=$R/_scratch/k1-fe-show-m2_20261110`, `A=$M/audio-forensics`, venv python `V=$R/_scratch/k1-fe-show-m1_20261109/lane-c-emu/.venv/bin/python` (numpy, scipy, matplotlib; **no pytest deps**). The commit gate's python is plain `python3` (has yaml, pytest).
- **Development export** (not a checkout): `git -C $R archive <sha> | tar -x -C <scratch>/src`, then `cp -Rc <old export>/.pio <scratch>/src/.pio` to keep the build cache. Session 3's export `afe2-src` in its scratchpad equals `a6113aaf` plus two scratch fixtures in the inventory JSON; recreate from git if the scratchpad is gone.
- **Private git dir** (for pytest, the flash script, `git hash-object`): `git init -q --bare $X-git; echo $R/.git/objects > $X-git/objects/info/alternates; echo <full sha> > $X-git/HEAD; GIT_DIR=$X-git GIT_WORK_TREE=$X git read-tree <sha>`; then run with those two variables and `GIT_OPTIONAL_LOCKS=0`.
- **Commit without touching the checkout**: `export GIT_INDEX_FILE=<tmp>; GG=(/usr/bin/git --git-dir=$R/.git --work-tree=<export>); $GG read-tree <parent>; $GG add -- <paths>; C=$($GG commit-tree $($GG write-tree) -p <parent> -F msg.txt); $GG update-ref refs/heads/<branch> $C`. zsh: do not define a function named `g` (alias clash).
- **Flash**: fresh export of the commit + private git dir, then from the export `bash scripts/agent/k1-flash-verified.sh k1_main_rpl_show_bench --port /dev/cu.usbmodem11301`. Full read-back first (`~/.platformio/penv/bin/python -m esptool --chip esp32s3 --port <p> --baud 921600 read_flash 0 0x1000000 <file>`, 206 s).
- **Emulator**: from the export, `K1_ESP_EMU=~/Workspace_Management/Software/SpectraSynq-ESP-Emulator/tools/esp-emu-pin/bin/esp-emu $V tools/esp_emulator/run.py --scenario <json> --suite <name> --profile scenario --output <dir that does not exist>`. The runner's own verdict line says SOFTWARE INCOMPLETE for these suites (SW04/11/13 are about other things); judge by the per-case PASS lines. Scenario makers: `emu/make_scenario_afe2.py`, `make_scenario_tracks.py` (adds two local fixtures to the export's inventory copy; never commit that). Analyses: `emu/analyse_afe2.py`, `analyse_tracks.py`, each `--export <export>`.
- **A new serial command needs both tables**: a row in `serial_typed_cmd_table.def` + handler in `serial_typed_dispatch.cpp`, **and** a branch in the `parse_command` ladder in `serial_menu.cpp`; then `k1_serial_safety.py` (name list and `TYPED_DEF_BLOB_SHA`). The emulator and the device both go through the ladder.
- **Gates**: `cd $M/m2-emu; $V gates.py --src <export with .pio/libdeps copied from work/src-81f26bee976a> --profile fe|scenario --mode 32|18 --m2-stream ../m2-compose/projects/loreen/stream/loreen_post_edit_120hz.prsm --m2-twin ../m2-compose/projects/loreen/stream_reopen/loreen_post_edit_120hz.prsm`; three invocations, one after another.
- **Bench** (in `lane-d`, `K1_UNIT=rpl`): `k1_bench.py cmd <out> :k1_afe=off|on|status`, `arm <out> 92 6`, `listen.py <out.jsonl> 88` in the background, the player with `--audio-only --gain-db -10` (see `runs/B_M1_*/` for the exact line), then `dump`. `dump` rc 3 means a lost line (CRC flag false); the npz is still usable. Check `pgrep -lx afplay` first. Never touch Mac volume.
- **Explainer**: `$V design/explainer_data.py --export <export> --cache <dir>` (decodes seven tracks; cache was `fe-model` in the session scratchpad), `$V design/explainer_sim.py --cache <dir>`, `$V design/build_explainer2.py --export <export> --out design/k1-audio-front-end.html`, then republish the page to the link above with the publishing tool, passing that link as `url` (a new session must read it first).
- Headless Chrome will not render narrower than 500 px; measure overflow with `document.documentElement.scrollWidth`, not a 400 px screenshot.
- The Modernes session reports that opening the port with pyserial resets the chip. In my runs the telemetry flag `afe=0` persisted across open/close, so my tools did not reset it. Check the `afe=` field in telemetry rather than assume either way.

## 9. Rules that still bind

Device identity before any serial or flash action. Calibration only after the Captain confirms silence. No Wi-Fi. Never touch Mac volume or output device; one playback owner. No checkout, stash, add or commit in the shared tree. No planted faults or mutation tests; one real test per change. One heavy job at a time. Every Agent call needs `model=` and the WAVE_SIZE / PRODUCT_OUTPUT / OWNERSHIP / DONE_WHEN / EVIDENCE / BUDGET lines. Plain English to the Captain, problems first, ship path in any not-done answer. A visual is delivered only when it is on his screen (publish or `open`), not when it is a path. Before writing an inference as fact, run the probe: two of mine were wrong tonight.

## 10. Ship path

1. On the Main RPL now: AFE2 stage 1 (`a6113aaf`), bench build only. In source: three unmerged branches.
2. Next agent: pytest, merge, judge, flash, bench; then AFE2 stages 2 to 7.
3. Captain: one look at the plate (gamma and floor); later the timing and musical-value tests; one sound-level-meter reading if absolute dB SPL is wanted.
4. Shipped = tagged `fe-1.0.0` on an FE board passing every M1 check, recorded in the device registry.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-11 | agent:claude (K1-FE-SHOW lead, session 3) | Created at the Captain's request (context limit). |
