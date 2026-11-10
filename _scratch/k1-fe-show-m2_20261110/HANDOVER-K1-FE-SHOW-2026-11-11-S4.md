---
abstract: "Handover from K1-FE-SHOW lead session 4 (11 Nov 2026, 04:20 to 07:10 AWST). The three firmware branches are merged (fe/k1-fe-rc3), judged and on the Main RPL, then replaced there by AFE2 stage 2 (fe/k1-afe2-s2, one silence test from the meter), which is built, gated, flashed and measured but not yet accepted because silence comes ~10 s after the music stops. Read this file, then AFE2-PLAN-2026-11-10.md section 6, before doing anything."
---

# Handover — K1-FE-SHOW lead, session 4 (11 Nov 2026, 07:10 AWST)

Every fact below was checked in this session unless marked **[UNVERIFIED]**. Use `/usr/bin/git`. British English. AWST. Session 3's handover (`HANDOVER-K1-FE-SHOW-2026-11-11-S3.md`) still holds for rules and commands; this file adds to it.

## 1. Where things stand

The merge of AFE2 stage 1, the FW lead's show fixes and the Modernes C++ fixes is done and judged on every count the plan names. On the real unit it keeps a prepared show running through dropped frames (one session, epoch +1, where `a6bad318` reset 180 times) and reproduces stage 1's bench result. AFE2 stage 2 replaces the old silence test, which called live music "silent" up to 79 % of the time, with one two-level test on the meter: 0 false silences in 15 emulator cases at three room levels and 0 of 81 lines on the bench. It is on the Main RPL now. One acceptance number is not met: after the music stops, silence is declared after ~10 s (bench) / 8–19 s (emulator), not within the 5 s dwell. The Captain has not yet looked at the plate for stage 1 or 2.

## 2. Live state (verified 11 Nov ~07:00)

| Item | State |
|---|---|
| Main RPL `9087A500` (USB `B4:3A:45:A5:87:90`, `/dev/cu.usbmodem11301`) | `k1_main_rpl_show_bench` @ **`d2701d9a`**, epoch `1794350924`, mode 22, 30 `CONFIG.*` unchanged since session 3, `afe=1 afe_sil=1` at boot |
| Restore images (full 16 MB read-backs) | `a6113aaf`: sha256 `4cec1e8a…6490` in `_scratch/20261111-k1-fe-show-s4/bench/flash-rc3/`; `24583a6a` (rc3): sha256 `8a44b8c0…75f5` in `…/bench/flash-s2/`. Not committed (16 MB binaries). |
| `fe/k1-fe-rc3` | `25511c90` = merge `24583a6a` + registry. Pushed this session (see closing report). |
| `fe/k1-afe2-s2` | `3c3d723c` = stage 2 `d2701d9a` + registry, parent `25511c90`. Pushed this session. |
| `fe/k1-afe2` | `a6113aaf`, unchanged, pushed (session 3). |
| `fe/k1-fe-show-fixes` | `c949151c`, now reachable through `fe/k1-fe-rc3`. |
| `mcpp/next-phase-fixes` | head `fcdefec5` (docs only, Modernes session); its code `bd5d5a83` is in rc3. That session is idle and asked to be told if anything in its code (look upload/clear, identify, serial overflow, saved-value repair, Gx limit replay) fails: nothing did. |
| Shared checkout | untouched by this session (no checkout, stash, add or commit). |
| Explainer | https://claude.ai/artifact/NUPD343KnvpNrfJ67z3E3y version 5: bench A/B chart rebuilt from the raw frames (the old series did not follow the frames' clock), table headers, round ticks, colour names in the model. |
| Background jobs | none. Nothing playing. |

## 3. What was done, with evidence

| Work | Result | Evidence |
|---|---|---|
| Identity | `a6113aaf`, epoch `1794338367`, mode 22, as expected | scratchpad `ident0` (also in `_scratch/20261111-k1-fe-show-s4/`) |
| Full pytest on `a6113aaf` | 2,077 passed, 9 skipped, 0 failed; 6 min; no stall. First pass showed 3 failures from `test_serial_cmd_persist_flags_static.py`, which ignores every file under a `_scratch` folder; rerun outside `_scratch`: 5/5 | `audio-forensics/design/pytest_final.txt`, `_scratch/20261111-k1-fe-show-s4/pytest-a6113aaf.log` |
| Explainer review | 4 faults fixed (see §2), republished to the same link | `design/build_explainer2.py`, `design/bench_ab_series.py`, `bench_ab_series.json` |
| Merge `fe/k1-fe-rc3` | `git merge-tree` + private index; 2 conflicts (safety SHAs from `git hash-object`; README changelog) | commit messages `c0896dd8`, `24583a6a` |
| rc3 judged | pytest 2,091/0; four envs build; G1–G4 ×3 0 failing; live regression 22/22 cases 0 differing frames vs `a6bad318`; receiver 913,580 losses, 0 hotkeys/commands/corrupt | `fw-candidates/24583a6a/` |
| rc3 on the unit | silent show under load (load avg 48, 28 frames dropped): epoch 1 → 2, no reset. Bench A/B loud ÷ breakdown 1.08 → 2.89 (edge 1), 0.82 → 2.42 (edge 2) | `_scratch/20261111-k1-fe-show-s4/bench/rc3-*`, `rc3_bench_ab.json` |
| Stage 2 | reference first, host test, off-identity 22/22, 30-case A/B, gates ×3, flash, quiet room, bench A/B — numbers in plan §6 | `audio-forensics/emu/analysis-s2/`, `_scratch/20261111-k1-fe-show-s4/s2/`, `…/bench/s2_*` |

## 4. Not done, and honest gaps

- **Stage 2 not accepted**: silence latency after a stop. Two ways forward: (a) accept it (recommended: during that time the plate already dims to the floor through stage 1; the only effect is a later beat-tracker reset between songs); (b) give the silence test its own fast-release copy of S (one float, 0.3 s release), re-run the 30-case A/B and the bench. Then delete the old IM69D crest/SSL thresholds as the plan says, which also means updating `tests/test_im69d_env_static.py::test_joint_silence_gate_is_scoped_to_im69d`.
- **Stage 3 not started** (loud guard: false trigger and spectrum actions). Code read: `i2s_audio.h:230-287` (`k1_loud_guard_update`, `gdft_target` from `peak_pin`/`spec_sat` duty), `k1_gdft_core.cpp:505-516, 598-606`, `visual/lightshow_modes.h:443`. Acceptance per plan: at room level the build with the guard on must equal today's `:k1_loud_guard=off` captures byte for byte (input trim is 1.000 at room level), and at the hot fixture the input side must match today's guard-on run.
- The emulator room segment for stage 2 is a model (Gaussian 2.5 counts rms); no raw microphone recording of the quiet room exists. The bench quiet-room run is the real check.
- Edge 2 with stage 1 off read 0.82 loud ÷ breakdown here and 2.04 in session 3 (stage on 2.42 / 2.93); one run each; cause not established.
- The Captain has not seen stage 1 or 2 on the plate.

## 5. Next tasks, in order

1. Decide stage 2's latency (§4), finish its acceptance, delete the old thresholds in the same commit, rerun pytest, builds, off-identity is no longer possible (record why), A/B, gates, flash, bench.
2. Stage 3 exactly as the plan states.
3. Ask the Captain once, at the plate: modes 22 and 32, `:k1_afe=off` vs `on`, then `:k1_afe_gamma=1.5` and `:k1_afe_floor=0.4`; which looks right.
4. Then stages 4–7, A06, A18, `fe-1.0.0`.

## 6. Commands added this session (each cost time once)

- **pytest exports must not live under `_scratch/`** (one static test skips such paths). Use the session scratchpad.
- **Merge without a worktree**: `git merge-tree --write-tree --name-only A B`; clean result = a tree id → `git commit-tree <tree> -p A -p B`. Conflicts: `git archive <conflicted tree> | tar -x` into an export, fix, then a private index: `read-tree <conflicted tree>`, `add` only the fixed files, `write-tree`, `commit-tree`. (Do not `read-tree` the parent afterwards: it drops the other side.)
- **Live regression**: `run.py --scenario tools/esp_emulator/s3_music_regression.json --suite default --profile scenario --output <new dir>`, then `_scratch/20261111-k1-fe-show-s4/tools/compare_live.py --export <export> --old <run> --new <run>`.
- **Receiver test**: `c++ -std=c++17 -O2 -Wall -Wextra -Werror -I<audio> tests/k1_prsm_rx_host.cpp <audio>/k1_prsm.cpp <audio>/k1_prsm_rx.cpp <audio>/k1_authored_source.cpp -o rx`; `rx` (self-test) and `rx <m2 stream>`.
- **Loaded silent show**: `BURN=32 bash _scratch/20261111-k1-fe-show-s4/tools/loaded_silent.sh <name>` (8 burners did not drop a frame on this 14-core Mac).
- **Bench A/B**: `LISTEN_S=110 bash _scratch/20261111-k1-fe-show-s4/tools/bench_ab.sh <name> <command>`. `k1_bench.py` now allows `:k1_afe_silence=on|off`.
- **Stage 2 emulator A/B**: on an export, `make_scenario_tracks.py`, then `make_scenario_s2.py`, `run.py --scenario tools/esp_emulator/afe2_s2_scenario.json --suite s2`, `analyse_s2.py <run> --out …`. Restore the export afterwards (`git checkout-index -f` the inventory; delete the two generated JSONs) before gates or a flash.
- The silence flag per hop is in the emulator's novelty trace (`N,gen,novelty,vu,silence,crc`).

## 7. Ship path

1. On the Main RPL now: `d2701d9a` (rc3 + stage 2), bench build only. In source: `fe/k1-afe2-s2` (pushed).
2. Next agent: stage 2 acceptance and deletion, stage 3, then stages 4–7; merge into the release lane; flash the FE board.
3. Captain: one look at the plate (gamma, floor; stage 2 needs no look); later A06 timing and A18 musical value.
4. Shipped = `fe-1.0.0` tagged on an FE board passing every M1 check, recorded in the device registry.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-11 | agent:claude (K1-FE-SHOW lead, session 4) | Created at the end of session 4. |
