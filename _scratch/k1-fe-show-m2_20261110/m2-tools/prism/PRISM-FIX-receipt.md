# PRISM fix receipt — 10 Nov 2026 (agent: PRISM fix SSA for the K1-FE-SHOW lead)

**What happened.** The PRISM editor now runs the whole creator loop by itself. Through the real editor server it compiles the Loreen project, saves the bar-accent edit, reopens it and recompiles it. The result is byte-for-byte what M2 produced: ShowBundle `90855dde…`, Intent Trace `8128452f…` and stream `116981ee…`. Its playback engine now sends the K1 FE only guarded PRSM frames, with a resync preamble before each session and each seek. The wire bytes equal lane-b's `wire_packets` exactly. The byte audit passes. The broken `.g5r-clean/PRISM.studio` checkout works again and now sits at the lock cc00556d, so the Spine sees the locked PRISM. Nothing was pushed. No device, serial port, Spine file or `organs.*.json` was touched.

## Problems first

1. **Spine doctor printed PASS while PRISM was on the wrong commit (Spine defect, not fixed: not my repo).** Before the repair it reported `prism effective 07eb822` against `locked cc00556d`, plus `dirty: false`, even though `git status` in that checkout failed outright. Evidence: `raw/a2_spine_doctor_before.log`.
2. **The editor UI is very long on real compiled bundles (existing behaviour, not changed).** The curve editor renders every point of every Loreen curve, which puts the Project panel about 65,000 px down the page. The panel works; it is just far down. Evidence: `raw/e2_editor_ui_shot.log` (clip y = 65,628). Separately, the repo has no `button:disabled` style. The disabled Save button therefore looks the same as an enabled one, although it is disabled, carries the tooltip, and the load message says "read-only". See `ui/editor_header_save_disabled.png`.
3. **Other K1-FE byte paths in the editor that were not in the defect list were left unchanged.** Each is reported here:
   - `/api/instrument/mode` writes `:set_mode=N\n` to the port. On the FE that is a command that persists to flash.
   - The Composer mode drives the K1CT bridge (`k1ct_bridge_client.js`).
   - The scheduler still sends late frames in a catch-up burst after a stall; the lane-c player drops late frames instead.
4. **The new compile manifest differs from M2's in one field, by design.** `compiler.commit` is now the commit actually running, `87f0c43c…` (branch), where M2's run recorded `cc00556d…`. So `compile_manifest.json` is not byte-identical to M2's. That is the only differing field (`raw/c3_byte_compare_vs_m2.log`). After the lead pushes and the lock is moved by the Captain or Spine owner, a run at the new lock records that commit.
5. **One test needed a harness fix before it could fail cleanly on cc00556d.** The first run against cc00556d hung, because the old engine ignores the injected writer. I stopped it; no processes were left behind. I added per-test timeouts and resolve-on-stop, amended the commit, and ran it once more. Evidence: `raw/b2a_…archive_nogit.log`, `raw/b2_new_tests_on_cc00556d.log`.
6. **The editor stream has no lane-b sidecar.** The editor writes `stream_<hz>hz.prsm` plus `outputs.json`. It does not write the `k1-prim8-stream/0` sidecar, because the composition carries no asset identity. The `.prsm` bytes are identical to M2's.

## (a) `.g5r-clean/PRISM.studio` — metadata repair only

| | Before | After |
|---|---|---|
| `git status` | `fatal: bad object HEAD` (alternates → deleted `…/Software/PRISM.studio/.git/objects`) | `HEAD detached at cc00556`, `nothing to commit, working tree clean` |
| HEAD | 07eb8227 (file only; objects missing) | cc00556d1df2f863c6a0d914ef613886b050a408 |
| Spine doctor (`./bin/instrument doctor`, read-only) | PASS, prism effective **07eb822** ≠ locked cc00556d | PASS, prism effective = locked = **cc00556d** |

Steps:
- I moved `.git/objects/info/alternates` aside to `alternates.dead-20261110`, which is kept.
- `git fetch origin` failed. Two remote-tracking refs (`origin/feature/led-async-effects`, `origin/feature/trinity-compile-v0-3`) pointed at objects that only existed in the dead alternate, and `--refetch` failed the same way.
- `ls-remote` showed the remote still holds both refs at the same SHAs. I deleted the two stale tracking refs, and the next fetch restored them and every other ref. `fsck --connectivity-only` is clean.
- The working tree equalled 07eb822: `git diff --quiet 07eb822` held, there were 0 untracked files, and the only ignored item was `.tmp/` (VM replay outputs). Nothing was discarded.
- I ran `git checkout --detach cc00556d` with no force.
- The local `main` branch still points at 07eb822 and was left as it was.
- Logs: `raw/a1`–`a8`.
- I did not run Spine `verify`, because it writes into the Spine's `.tmp/` and the Spine is read-only for me.

## (b) Branch `fix/one-instrument-editor-loop` (clone `_scratch/k1-fe-show-m1_20261109/prism-studio-locked`)

The branch has one local commit, **87f0c43c78e73265fe260b08b8e732cdb83499ff**, on top of cc00556d. It is not pushed. After my runs I put the clone back to detached cc00556d with a clean tree, so the identity checks in other lanes (M2 `compose.mjs`) still pass. The branch is kept. No editor server, capture or headless browser is still running (`raw/f1_final_state.log`).

| # | Defect | Fix | Test (`tools/test_editor_instrument_loop.js`) |
|---|---|---|---|
| 1 | compile used `--contract/--stem-features`, so it always returned 500 | Uses compiler 0.3.1 flags `--in/--stems/--coverage-out/--manifest-out` with cwd `/tmp` (= Spine `compileOnce`). It checks manifest integrity, replays through `src/vm.js` and writes the trace and the `.prsm`. `record` stores the hashes in the composition; `verify` must match them. | "compile endpoint runs compiler 0.3.1…" |
| 2 | `compiler_commit` default was `e37c7da` | Uses the running `git rev-parse HEAD` and reports a dirty flag. A different requested commit gets 400; an unknown commit refuses to compile. | "compile manifest records the PRISM commit actually running…" |
| 3 | profile allow-list returned 400 for authored profiles | Accepts any profile that validates against `mapping_profile_v1` (Spine schema plus the closed enums of `validate_profile.mjs`; `device_profile` must be `none`). With a project open it saves an authored edit in the `compose.mjs edit` layout. | "profile endpoint accepts any valid mapping_profile_v1…" |
| 4 | `app.js` never called compile | New Project panel: Compile, Save authored edit (mapping profile JSON), Reopen, Recompile & verify | "editor UI wires…", plus the headless UI run below |
| 5 | `POST /api/bundle` edits were silently overwritten | Saving a compiled ShowBundle returns 409 with an explanation, and the UI disables Save with a tooltip. The authored source (mapping profile) is what gets saved. | "loop: compile, authored edit, save, reopen, recompile…" |
| 6 | server bound all interfaces | Binds `127.0.0.1` unless `--host` is given | "editor server binds 127.0.0.1 only…" |
| 7 | `playback.js` sent K1CT, had a stale 250 ms comment, and allowed hz 1–1000 | New `target`, default `k1_fe`: PRSM only, every frame one 64-byte write (30 NUL + frame), a 64-byte RESYNC_PREAMBLE before the first frame of each session and seek, hz 30–240 enforced in the engine and in `/api/device/play` before any device access. The comment is corrected (FE 50 ms; bridge 250 ms). Seek no longer sends the seek tick twice. `k1_usb_bridge` keeps the old behaviour. | three "K1 FE playback…" tests, plus a "K1CT only to k1_usb_bridge" preservation test |

I also updated two existing tests: `test_e2e_pipeline.js` E2E-6 now names the `k1_usb_bridge` target, and E2E-8 counts 64-byte writes. The CHANGELOG has a `[Unreleased] Fixed` entry. `npm test` was added.

### Tests

| Run | Result | Evidence |
|---|---|---|
| `npm test` on 87f0c43c, clean tree, port 7777 free | golden 3/3 PASS; `node --test` **48/48**; live streaming **34/0**; e2e software **26/0** (device test skipped, as intended) | `raw/b3_suite_branch_final.log` |
| New tests in the clone checked out at **cc00556d** (test file untracked, then removed) | **10/10 fail**, each on its defect: 500 ≠ 200; compile error (old payload); `prim8_natural_v1` ≠ `my_authored_v1`; 500; UI ids missing; `::1` reachable; `target` undefined; no RangeError; no preamble; no K1CT captured (old engine ignores the writer) | `raw/b2_new_tests_on_cc00556d.log` |

## E2E — Loreen through the real editor server (127.0.0.1, started and stopped by the script)

- **Project:** a copy of M2 `projects/loreen` in its pre-edit state, with the same input bytes (`raw/c0`), in `e2e/loreen/`.
- **Expectations:** declared before the run in `raw/c1_EXPECTED_DECLARED_BEFORE_RUN.md`.
- **Run log and result:** `raw/c2_editor_e2e.log`, `raw/c2_editor_e2e_result.json`.

| Step (HTTP API only) | HTTP | Result | = M2 (`cmp`) |
|---|---|---|---|
| compile pre-edit (`record`) | 200 | ShowBundle cae4fbc1…, trace 9491b071…, stream 65143215… | yes, all 4 files |
| authored edit `prim8.impact.transform.beat_amp_u16` 48000→12000 | 200 | profile `4847be0b…` | yes |
| `POST /api/bundle` (compiled bundle) | **409** | refused; file unchanged | — |
| compile post-edit (`record`) | 200 | **90855dde… / 8128452f… / 116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3**, 26,870 frames | yes: bundle, trace, coverage, stream |
| new server process → `GET /api/instrument/project` → compile `verify` | 200 / 200 | VERIFIED; diffs `[]` across 7 keys | yes |

- **File comparison:** `raw/c3_byte_compare_vs_m2.log`. Every file is identical except `compile_manifest.json`, which differs only in `compiler.commit` (Problem 4).
- **Headless UI run** (no window, real `app.js` clicks: Compile → edit the JSON → Save authored edit → Compile → Reopen → Recompile & verify): the same hashes, profile `4847be0b…`, no page errors, Save disabled on the compiled bundle. Evidence: `raw/e1_editor_ui_headless.log`, `ui/editor_ui_loop_steps.json`. Screenshots I looked at: `ui/editor_project_block_verified.png` (panel showing VERIFIED and the three hashes) and `ui/editor_header_save_disabled.png`.

## Playback wire bytes vs lane-b (no device: the engine's `write` hook captured every write)

| Session | Check | Result | Evidence |
|---|---|---|---|
| Full Loreen post-edit, `target` k1_fe (default), 120 Hz, real-time pacing (223.9 s), ends at seq 26,870, 0 dropped, 0 K1CT | capture = `RESYNC_PREAMBLE + b"".join(wire_packets(M2 stream))`: **True** (sha256 caea7a9e…, 1,719,744 B). The write boundaries equal lane-b's packet list: 26,871 writes, all 64 B. The frames with the guard removed are exactly `116981ee…`. | PASS | `raw/d1_playback_full_capture.log`, `raw/d3_full_compare_and_audit.log`, `wire/loreen_post_edit_full.{bin,json,prsm}` |
| Full, the same bytes | `audit_prsm_bytes.py --guard 30` (LANE_B_FW=fw_8b202f46) | **BENCH-ELIGIBLE 26870/26870, 0 hotkeys, exit 0** | `raw/d3_audit_full.json` |
| Seek: play 0 → after 1 s seek to 75 s → stop at 3 s | 363 writes, all 64 B; preambles at writes 0 and 122 only; each epoch = `RESYNC_PREAMBLE + wire_packets(frames)`; epoch 1 = M2 frames 0–120; epoch 2 = M2 ticks 9000+ with seq continuing from 121; no duplicate frame | PASS | `raw/d2`, `raw/d4_seek_compare_and_audit.log` |
| Seek, each epoch | `audit_prsm_bytes.py --guard 30` (LANE_B_FW=fw_8b202f46) | BENCH-ELIGIBLE 121/121 and 240/240, exit 0 | `raw/d4_audit_seek_e1.json`, `raw/d4_audit_seek_e2.json` |

## Re-run commands (lead)

```
R=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/prism-studio-locked
P=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-tools/prism
LB=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/lane-b
PY=/opt/homebrew/opt/python@3.13/bin/python3.13
M2S=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen/stream/loreen_post_edit_120hz.prsm
cd $R && /usr/bin/git checkout fix/one-instrument-editor-loop      # 87f0c43c
lsof -nP -iTCP:7777 -sTCP:LISTEN                                    # must be empty
npm test
# e2e: fresh pre-edit copy (the e2e/loreen folder already holds the edited project)
L=$P/rerun_lead/loreen; rm -rf $P/rerun_lead && mkdir -p $L/mapping && cp -R $P/e2e/loreen/inputs $L/ \
 && cp $P/e2e/loreen/mapping/prim8_natural_v1.json $L/mapping/ \
 && cp /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen/composition.pre_edit.snapshot.json $L/composition.json
node $P/tools/editor_e2e_loreen.mjs $R $L $L/result.json
shasum -a 256 $L/out/post_edit/{showbundle.json,trace_120hz.jsonl,stream_120hz.prsm}   # 90855dde… 8128452f… 116981ee…
cmp $L/out/post_edit/stream_120hz.prsm $M2S
# playback wire bytes (full run is real time, ~224 s) + lane-b compare + audit
node $P/tools/playback_wire_capture.mjs $R $L/out/post_edit/showbundle.json $P/rerun_lead/wire_full full
$PY $P/tools/compare_wire_laneb.py full $P/rerun_lead/wire_full $M2S $P/rerun_lead/wire_full
LANE_B_FW=fw_8b202f46 $PY $LB/audit_prsm_bytes.py $P/rerun_lead/wire_full.prsm --guard 30
/usr/bin/git checkout --detach cc00556d1df2f863c6a0d914ef613886b050a408   # restore the lock state for other lanes
```

## Ship path

1. **Done:** branch commit 87f0c43c in the existing clone (local); `.g5r-clean` checkout at the lock; evidence in this folder.
2. **Lead:** re-run the commands above, then `git push origin fix/one-instrument-editor-loop` and open the PR.
3. **PRISM owner:** review and merge.
4. **Captain or Spine owner:** repin `organs.lock.json` prism to the merge commit (agents never repin).
5. **What counts as shipped:** the Spine doctor shows effective = locked = the merge commit, and an editor compile at that commit reproduces stream 116981ee….

## Changelog
- 2026-11-10 agent:prism-fix — created (checkpoint), then final.
