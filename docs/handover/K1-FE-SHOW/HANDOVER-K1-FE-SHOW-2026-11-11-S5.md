---
abstract: "Handover for the next K1-FE-SHOW lead (session 5), written 11 Nov 2026 ~09:15 AWST at the end of session 4. AFE2 stages 1–3 are built, judged, committed, pushed and running on the Main RPL (df435671). This file is self-contained: live state with identities, every outstanding task in order with inputs, method, acceptance, failure handling and STOP, the exact commands that work, the traps that each cost time once, and the ship path. Read it whole, then AFE2-PLAN-2026-11-10.md (sections 4 and 6), before touching anything."
---

# Handover — K1-FE-SHOW lead, session 4 → session 5 (11 Nov 2026, ~09:15 AWST)

Every fact below was checked in session 4 unless marked **[UNVERIFIED]**. Use `/usr/bin/git`. British English. AWST. This file supersedes `HANDOVER-K1-FE-SHOW-2026-11-11-S4.md` (kept for history); session 3's handover (`…-S3.md`) is still the reference for the older commands it lists.

---

## 1. Objective and authority

**Destination:** 100 paid K1 Founders' Edition units shipped. The FE firmware is the shipping `SpectraSynq_K1_Firmware` S3 build.

**This lane's job:** finish AFE2, the rebuild of the K1 audio front end, then merge it into the release lane for `fe-1.0.0`. The Captain ordered the rebuild on 10 Nov 2026 ~23:15 AWST and gave this lane full authority to design and write the audio-front-end firmware itself (verbatim in `audio-forensics/AFE2-PLAN-2026-11-10.md` §0). He also removed every hold the same evening. On 11 Nov he said "continue as planned" (session 4 continued on that).

**The plan is the execution plan:** `audio-forensics/AFE2-PLAN-2026-11-10.md`. Eight stages, each with purpose, inputs, outputs, acceptance, failure handling and STOP. **Never shorten it.** Record progress in its §6 (live state) and changelog.

**Escalate to the Captain only for:** device identity mismatch; any need to run a calibration command; contradicting one of his rulings; a product choice with no sensible default. One paragraph, with a recommendation, then keep doing other work.

---

## 2. Live state (verified 11 Nov ~09:10 AWST)

| Item | State |
|---|---|
| **Main RPL** — chip `9087A500`, USB `B4:3A:45:A5:87:90`, `/dev/cu.usbmodem11301` (the only K1 attached) | env `k1_main_rpl_show_bench` @ **`df435671`** (AFE2 stages 1–3), epoch `1794383885`, mode 22, all 30 `CONFIG.*` identical to session 3's read (`:dump`). Boot defaults on this bench env only: `:k1_afe` on (stage 1 brightness factor), gamma 1.00, floor 0.25. NON-SHIPPABLE bench build (10 Nov rewire 2/3/5/6 + two-edge LED capture). |
| **Restore images** (full 16 MB read-backs, taken before each flash; in `_scratch/20261111-k1-fe-show-s4/bench/`, not committed) | `a6113aaf` `4cec1e8a…6490` (`flash-rc3/`), `24583a6a` `8a44b8c0…75f5` (`flash-s2/`), `d2701d9a` `f763a236…8b60` (`flash-s2final/`), `7177d90a` `56a47a95…c815` (`flash-s3/`). Restore = `esptool write_flash 0 <file>` on the identified port. |
| **Branches** (all pushed, local = remote) | `fe/k1-afe2-s3` **`714277c8`** (code `df435671` + registry) ← `fe/k1-afe2-s2` **`c36a9225`** (code `7177d90a`) ← `fe/k1-fe-rc3` **`25511c90`** (merge `24583a6a` of `fe/k1-afe2` `a6113aaf` + `fe/k1-fe-show-fixes` `c949151c` + Modernes `bd5d5a83`). Lanes: `lane/k1-fe-show-m2` **`d1476794`** (all lane documents and evidence), `lane/k1-fe-show-m1` **`2b2a45c3`** (bench tools). |
| **Release lane** | `lane/k1-fe-release` exists locally and on origin. AFE2 is **not** merged into it yet. |
| **Device registry** | Canonical, up to date through flash 11, on `fe/k1-afe2-s3` (`docs/hardware/device-build-registry.md`: device row, §2 deployed-state row, changelog rows for flashes 1–11 of 10–11 Nov). The shared checkout has an older **uncommitted** registry edit from session 2: never commit it; it is stale. |
| **Shared checkout** `~/SpectraSynq_K1_Firmware` | on `mcpp/next-phase-fixes` with other sessions' uncommitted files. **Never checkout, stash, reset, add or commit there.** Session 4 did not touch it. |
| **Other sessions** | Modernes C++ session (`uds:/tmp/cc-socks/46584.sock`, name changes on restart): idle; its code is in rc3 and passed everything; it asked to be told only if its code (look upload/clear, identify, serial overflow, saved-value repair, Gx limit replay) fails. FW lead: not running. |
| **Explainer** | https://claude.ai/artifact/NUPD343KnvpNrfJ67z3E3y version 5 (built by `audio-forensics/design/build_explainer2.py`). It describes stage 1 only; it does **not** yet show stages 2–3. The artefact watch from session 4 dropped; re-read before any republish. |
| **Background jobs** | none. Nothing playing. |

---

## 3. What is done (evidence on the lane branches)

| Stage / task | Result | Evidence |
|---|---|---|
| Full pytest `a6113aaf` | 2,077 passed, 0 failed (first pass showed 3 failures only because the export sat under `_scratch/`) | `audio-forensics/design/pytest_final.txt` |
| Merge rc3 `24583a6a` | pytest 2,091/0; four envs build; G1–G4 ×3 0 failing; live regression 22/22 cases 0 differing frames vs `a6bad318`; receiver 913,580 losses, 0 hotkeys/commands/corrupt; loaded silent show (load avg 48, 28 frames dropped) one session, epoch +1 | `fw-candidates/24583a6a/`, `_scratch/20261111-k1-fe-show-s4/bench/rc3-*` |
| **AFE2-S1** exposure (stage 1) | done in session 3; bench re-run on rc3: loud ÷ breakdown 1.08 → 2.89 (edge 1) | plan §6 |
| **AFE2-S2** one silence test — **accepted** | Silence = two-level test on `Sq`, a 0.3 s-release copy of the meter (quiet below 16 counts², music above 25), then the existing 5 s dwell. Deleted: `K1_SILENCE_PEAKINESS_BREAK`, `K1_SILENCE_JOINT_LEVEL_SSL_FRAC`, the IM69D crest×level path, its tunables, the temporary `:k1_afe_silence` switch, `tests/test_im69d_consumer_floors_behavioural.py`. Emulator: 0 false silences in 15 cases (5 tracks × −10/0/+10 dB), silence 5.4–7.6 s after a stop, held, cleared on return; old test was wrong up to 79 % of hops. Bench: 0 of 85 music lines silent | `audio-forensics/emu/analysis-s2/s2-fast-release.md`, plan §6 |
| **AFE2-S3** guard off the spectrum — done, one check open (§5 T2) | Deleted: GDFT trim target, AGC target/floor scaling, floor-cut, ceiling knee, colour unpin, retune matrix and their constants. `k1_loud_gdft_trim` fixed at 1.000; `peak_pin`/`spec_sat` measured for telemetry only; input trim kept until S5. Emulator room level, modes 22/32/18: guard ON = stage-2 guard OFF, 0 of 2,000 frames differ (the old guard changed 1,926–2,000 of 2,000). Bench: `gdft_trim` 1.000 on 110/110 lines; loud light 4.0 → 7.0 %; loud ÷ breakdown 2.03 → 3.52 | `_scratch/20261111-k1-fe-show-s4/s3/s3-compare.txt`, `bench/s3_bench.json` |
| Self-adjusting / gating stages removed so far | 2 of the plan's list (crest silence gate; guard's spectrum actions). Still present: four-band AGC (S4), fixed ×21.6 gain + clamp + `>>6` + guard input trim (S5), VU absolute RMS (S6), calibration ritual (S7) | plan §2, §3 |

---

## 4. Rules that bind (each was paid for once)

- **Device identity** before any serial or flash action: port **and** USB serial `B4:3A:45:A5:87:90` (the lane-d tools check it; `esptool` prints `MAC: b4:3a:45:a5:87:90`). Never auto-switch ports; never touch another device.
- **Calibration** commands (`start_noise_cal`, `N`/`Y`) only after the Captain confirms silence verbally. None is needed for the remaining stages.
- **No Wi-Fi** of any kind. **Never touch Mac volume or output device.** One playback owner: `pgrep -lx afplay` before any playback.
- **Shared checkout is read-only for you** (§2). All firmware work happens in a `git archive` export with a private git dir; commits use a private index (§6).
- **pytest exports must not live under any folder named `_scratch`** (one static test skips such paths and fails three tests). Use the session scratchpad (`/private/tmp/claude-501/…/scratchpad`).
- **One heavy job at a time** (pytest, `pio run`, emulator, `gates.py`). No heavy job during a bench run (USB timing). Check `sysctl -n vm.loadavg` before bench runs.
- **No planted faults or mutation tests.** One real test per change.
- **Before writing an inference as fact, run the probe.** Session 4 wrote an acceptance decision (accept the silence delay) that new evidence (20.6 s on a loud clip) overturned; the probe found it.
- **Every Agent call** needs `model=` and the WAVE_SIZE / PRODUCT_OUTPUT / OWNERSHIP / DONE_WHEN / EVIDENCE / BUDGET lines (session 4 used none).
- **Plain English to the Captain**, problems first, a ship path in any not-done answer. A picture is delivered only when it is on his screen (publish or open), not as a path.
- **Storage:** your working files go only in your own dated folder from `python3 ~/Workspace_Management/Mac-Health/storage/ssq_storage.py scratch "<task>"`; state the fate of each line of `ssq_storage.py footprint` at hand-back. Never plain-copy big files (`cp -c`).

---

## 5. Outstanding tasks, in order

Each task: purpose → inputs → method → acceptance → failure → STOP. Repair authority: you fix and re-run without asking, inside the rules above.

### T1. Captain's look at the plate (ask once, when he is at the plate)
- **Purpose.** His eye is the acceptance test for stages 1–3 together (plan §0: "An agent cannot judge the light").
- **Ask, in one message:** "In modes 22 and 32, send `:k1_afe=off` then `:k1_afe=on`; then try `:k1_afe_gamma=1.5` and `:k1_afe_floor=0.4`. Which looks right? Do loud sections hit, does it breathe, is it ever idle, can you follow one thing?" Measured to tell him: gamma 1 gives 0.32–0.63 dB of light per dB of sound; research supports 0.6–1.0; on the bench stage 3 nearly doubled loud-passage light (4.0 → 7.0 %).
- **Acceptance.** His answer recorded verbatim in plan §6. If he picks other gamma/floor values, change the defaults in `audio/k1_afe2.h` (`K1_AFE2_GAMMA_DEFAULT`, `K1_AFE2_FLOOR_DEFAULT`), re-run the host test, commit, flash.
- **Failure.** "Quiet sections look dead": raise floor / lower gamma at runtime with him, then set the defaults. Do not re-add any removed stage to brighten a mode (plan S3 failure rule).
- **Do not block on him:** T2–T4 proceed in parallel; just do not flash the FE board (T7) before his look.

### T2. Stage 3's open check: hot input level (no hard clipping)
- **Purpose.** Plan S3 acceptance: "Emulator at the hot fixture level: equals today's guard-on behaviour for the input side (no hard clipping)". Not run in session 4.
- **Inputs.** Scenario `audio-forensics/emu/guard_ab_scenario.json`, suite `guardab`, cases `fix-m{22,32,18}-{on,off}` (Loreen excerpt at peak 4,096 raw, above the clip point 1,517). The per-frame probe record logs `input_trim`, `gdft_trim`, `clip_count`, `sample_count` when the firmware is built with `K1_EMU_TEMPO_PROBE` (`audio/k1_emu_fixture.cpp` ~line 884; emitted at ~line 564). **[UNVERIFIED]** how `run.py` selects the tempo-probe env (`k1_main_rpl_emu_tempo_probe` exists in `platformio.ini`); read `tools/esp_emulator/run.py` first.
- **Method.** Two exports: `fe/k1-afe2-s2` (`c36a9225`) and `fe/k1-afe2-s3` (`714277c8`). Run the `fix-*-on` cases on both with the probe record on. Compare per frame: `input_trim` and `clip_count` must be identical (the input side was not touched); `gdft_trim` must be 1.000 throughout on S3 and below 1 somewhere on S2. If the probe env cannot be used with the scenario runner, state that and fall back to: S3 `fix-*-on` vs S3 `fix-*-off` frames must differ (the input trim still acts) and S3 `room-*-on` = `room-*-off` (it does not act at room level).
- **Acceptance.** As above, written into plan §6 with the numbers.
- **Failure.** Any input-side difference: find it before anything else; the S3 commit must not have changed the input path (diff `df435671~1..df435671 -- SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`).
- **STOP.** None specific.

### T3. AFE2-S4 — Spectrum exposure: one gain replaces the four-band AGC
- **Plan text:** `AFE2-PLAN` §4 "AFE2-S4" (purpose, inputs, outputs, acceptance, failure, STOP — follow it exactly; do not shorten it).
- **Where the code is now (line numbers moved in session 4).** `audio/k1_gdft_core.cpp`, function `process_GDFT()`: the AGC block starts after `const SQ15x16 AGC_TARGET` (constants `AGC_TARGET`, `AGC_MAX_GAIN`, `effective_target`, `agc_gain_floor`); the per-band path is `#ifdef K1_AGC_PERBAND_V1` (envelopes `pb_envelope[b]`, gains `pb_gain[]`, `freq_to_band_map`); the broadband path is its `#else` (`agc_envelope`, `agc_gain`); then `spectral_tilt_lut[i]`, the optional soft knee (`VP_FIX_AGC_SOFT_KNEE`), clamp to [0, 1] into `spectrogram[i]`. Which AGC path is live: `-DK1_AGC_PERBAND_V1=1` is set in `[env:k1_hardware]` (`platformio.ini` ~line 187), which `k1_main_rpl_im69d`, `k1_main_rpl_show_bench`, `k1_main_rpl_emu` and `k1_fe` inherit, so the per-band path is the live one (verified 11 Nov); the broadband `#else` is the fallback. Telemetry `agc_gain` / `agc_env` lives in `i2s_audio.h`'s `[AP]` line.
- **Design (plan §3 item 5, S4 outputs).** Every bin divided by the same slow anchor (S1's `k1_afe2.anchor`, counts²; mind units: the GDFT magnitudes are not raw counts — derive the scale on a recorded passage, state it), fixed tilt, fixed soft ceiling. Write the reference first (extend `design/afe2_reference.py` or a new `design/afe2_s4_reference.py`), host test against it, then firmware behind a runtime switch, default off except `k1_main_rpl_show_bench`.
- **Method.** As every stage: reference → host test → emulator off-identity (switch off = `fe/k1-afe2-s3` byte for byte, default suite and the five-track suite) → A/B on the five-track suite at −10/0/+10 dB, spectral modes plus 22 and 32 (`emu/make_scenario_tracks.py`; extend with levels as `emu/make_scenario_s2.py` does) → full pytest → four builds → G1–G4 ×3 → read-back → flash → bench A/B → delete the four-band AGC (`K1_AGC_PERBAND_V1` code and the broadband `#else`, dead `agc_env` telemetry) in the acceptance commit, with tests updated in the same commit.
- **Acceptance.** Plan S4: section tracking and contrast up, movement kept ≥ 85 %, no band stuck at 0 or at the ceiling, palette vibrancy unchanged or better by hue-bin count; Captain's eye on 22, 32 and two spectral modes (bundle with T1 if timing allows).
- **Failure / STOP.** Bass dominates → adjust the fixed tilt constant, never a per-band loop. If two attempts do not beat today's numbers, stop patching and redesign from the research notes (log spectrum against a fixed reference) — plan S4 STOP.

### T4. AFE2-S5, S6, S7 in plan order
- **S5** capture at full precision; delete the ×21.6 gain, 16-bit clamp, `>> 6` and the guard's input trim (`audio/i2s_audio.h` pre-gain/sensitivity/clamp block, `audio/k1_gdft_lane4_exact.h:24`, `k1_gdft_core.cpp` Goertzel). STOP on any Core 0 overrun; measure hop time (the AFE2 cost probe `afe_us` shows the method).
- **S6** VU from the meter (`calculate_vu()` in `i2s_audio.h`). Captain's eye on mode 18.
- **S7** line-in gets the same meter (`audio/k1_audio_ingress.h`); calibration ritual reduced or removed; dead code; registry and lane documents. STOP: FE board identity not confirmed.
- **S8** (mode 22 dark stretches) is a picture for the Captain before any change; no code without his look.
- Each follows the same method and acceptance discipline as T3; plan §4 is the authority.

### T5. Explainer update
- Add stages 2–3 results (silence before/after table; guard bench numbers) to `design/build_explainer2.py`, rebuild, look at the new sections in a headless browser at 1,280 px and 500 px, fix, republish to the **same** link (read it first with the publishing tool; pass `url`).

### T6. Integration into the release lane
- Merge the final AFE2 branch into `lane/k1-fe-release` (or whatever the release lead names; check `git log lane/k1-fe-release` and the governance course file `~/K1_Launch_Planning/00-Governance/COURSE-2026-11-02.md` first) with `git merge-tree` + private index (§6). Judge: pytest, four builds, G1–G4 ×3, live regression, receiver test, commit gate.

### T7. FE board, A06, A18, `fe-1.0.0`
- FE board flash only when it is on USB and its identity is confirmed (plan S7 STOP). A06 (timing, iPhone 240 fps clapper; one Captain action) and A18 (musical value with the Captain). Tag `fe-1.0.0` only on an FE board passing every M1 check, recorded in the registry. Tagging/pushing tags is a publication step: confirm with the Captain if not already ordered.

### Known open items to carry (do not lose)
- Edge 2 loud ÷ breakdown with stage 1 off read 0.82 (session 4) vs 2.04 (session 3); stage on 2.42 vs 2.93. One run each; cause not established.
- Skill documents `.claude/skills/k1-vj-session-discipline/SKILL.md` (and the `.cursor` / `.codex` copies) still list the deleted constants `K1_SILENCE_PEAKINESS_BREAK` / `K1_SILENCE_JOINT_LEVEL_SSL_FRAC`; `scripts/agent/k1-session-preflight.sh` uses them as examples. Update when the AFE2 branches merge to the release lane.
- dB SPL figures assume unity PDM gain (needs a sound-level meter beside the unit: Captain physical action, optional).

---

## 6. Commands that work (copy them; do not rediscover)

Paths: `R=~/SpectraSynq_K1_Firmware`, `M=$R/_scratch/k1-fe-show-m2_20261110`, `A=$M/audio-forensics`, venv python `V=$R/_scratch/k1-fe-show-m1_20261109/lane-c-emu/.venv/bin/python` (numpy/scipy/matplotlib; no pytest), plain `python3` has pytest. Session-4 tools: `T=$R/_scratch/20261111-k1-fe-show-s4/tools` (also on `lane/k1-fe-show-m2`).

- **Export + private git dir** (in the session scratchpad, not under `_scratch`):
  `X=<scratchpad>/<name>; mkdir -p $X; /usr/bin/git -C $R archive <sha> | tar -x -C $X; /usr/bin/git init -q --bare $X-git; echo $R/.git/objects > $X-git/objects/info/alternates; echo <full sha> > $X-git/HEAD; GIT_DIR=$X-git GIT_WORK_TREE=$X /usr/bin/git read-tree <sha>`; library caches: `mkdir -p $X/.pio; cp -Rc <previous export>/.pio/libdeps $X/.pio/` (envs needed: `k1_hardware k1_main_rpl_show_bench k1_main_rpl_im69d k1_fe k1_fe_emu k1_main_rpl_emu k1_bench_im69d_led150`; the last is needed by one pytest test; source `$R/.pio/libdeps/<env>`). Run tools with `GIT_DIR=$X-git GIT_WORK_TREE=$X GIT_INDEX_FILE=$X-git/index GIT_OPTIONAL_LOCKS=0`.
- **Commit without touching the checkout:** `export GIT_INDEX_FILE=<scratchpad>/x.index; GG=(/usr/bin/git --git-dir=$R/.git --work-tree=$X); $GG read-tree <parent>; $GG add -A -- SPECTRASYNQ_K1_FIRMWARE platformio.ini scripts tools tests docs; $GG diff --cached --stat <parent>` (**read the stat**), `C=$($GG commit-tree $($GG write-tree) -p <parent> -F msg.txt); $GG update-ref refs/heads/<branch> $C <old>`. Then point the export's private git dir at `$C` (`echo $C > $X-git/HEAD; read-tree $C`). Lane files under `_scratch` need `add -f` (`_scratch` is git-ignored).
- **Merge without a worktree:** `/usr/bin/git merge-tree --write-tree --name-only A B` → tree id (clean) → `commit-tree <tree> -p A -p B`. Conflicts: `git archive <conflicted tree> | tar -x` into an export, fix, private index: `read-tree <conflicted tree>`, `add` only the fixed files. **Do not** `read-tree` the parent afterwards (session 4 did once and dropped the other side; caught by `diff --stat`).
- **Full pytest:** `cd $X && python3 -m pytest tests/ -q -p no:cacheprovider` (≈4 min). Count the deleted tests when comparing totals.
- **Builds:** `~/.platformio/penv/bin/pio run -e <env>` for `k1_hardware k1_main_rpl_show_bench k1_main_rpl_im69d k1_fe` (≈20 s each with cache).
- **Live regression / off-identity:** `K1_ESP_EMU=/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-ESP-Emulator/tools/esp-emu-pin/bin/esp-emu $V tools/esp_emulator/run.py --scenario tools/esp_emulator/s3_music_regression.json --suite default --profile scenario --output <new dir>`; then `$V $T/compare_live.py --export $X --old <run> --new <run> --out <txt>`. The runner's SW07/SW11 FAIL lines and "SOFTWARE INCOMPLETE" are its own suite checks (same on every candidate); judge by per-case PASS and the comparison. Latest baseline runs: rc3 `$M/fw-candidates/24583a6a/live-regression`, stage 2 `$R/_scratch/20261111-k1-fe-show-s4/s2q/live`.
- **Five-track / level suites:** on the export, `$V $A/emu/make_scenario_tracks.py $X`, then e.g. `S2_NEW_ONLY=1 $V $A/emu/make_scenario_s2.py $X`; run with `--scenario tools/esp_emulator/afe2_s2_scenario.json --suite s2`. **Afterwards restore the export** (`git checkout-index -f -- scripts/regression-harness/fixtures/k1_av_regression_fixtures.template.json`; delete the generated `tools/esp_emulator/afe2_*scenario.json`) before gates or a flash. Per-hop silence is in the novelty trace `N,gen,novelty,vu,silence,crc`.
- **Guard / room-level identity:** copy `$A/emu/guard_ab_tail_scenario.json` into the export's `tools/esp_emulator/`, `--suite tail` (cases `tail-m{22,32,18}-{on,off}`, 2,000 frames each); remove it afterwards.
- **Gates:** `cd $M/m2-emu; for pm in fe:32 scenario:32 scenario:18; do …; $V gates.py --src $X --profile $p --mode $m --m2-stream ../m2-compose/projects/loreen/stream/loreen_post_edit_120hz.prsm --m2-twin ../m2-compose/projects/loreen/stream_reopen/loreen_post_edit_120hz.prsm > $M/fw-candidates/<sha>/$p-<sha>-m$m.log; done` (≈10 min each; "failing gates: 0" ×3).
- **Receiver test:** `c++ -std=c++17 -O2 -Wall -Wextra -Werror -I$X/SPECTRASYNQ_K1_FIRMWARE/audio $X/tests/k1_prsm_rx_host.cpp <audio>/k1_prsm.cpp <audio>/k1_prsm_rx.cpp <audio>/k1_authored_source.cpp -o rx; ./rx; ./rx $M/m2-compose/projects/loreen/stream/loreen_post_edit_120hz.prsm`.
- **Flash:** read-back first `~/.platformio/penv/bin/python -m esptool --chip esp32s3 --port /dev/cu.usbmodem11301 --baud 921600 read_flash 0 0x1000000 <file>` (206 s; check `MAC: b4:3a:45:a5:87:90`), then from a clean export (`git status --porcelain` empty) `bash scripts/agent/k1-flash-verified.sh k1_main_rpl_show_bench --port /dev/cu.usbmodem11301` → `IDENTITY OK: git=<sha>`. Then `cd $R/_scratch/k1-fe-show-m1_20261109/lane-d; K1_UNIT=rpl python3.13 k1_bench.py ident <dir>` and diff the 30 `CONFIG.*` lines against the previous ident.
- **Bench A/B:** `LISTEN_S=110 bash $T/bench_ab.sh <name> <allow-listed command>` (Loreen 75–155 s at 10 dB under the Captain's volume, mode 22; telemetry `ap.jsonl`, LED dump `dump.npz`, `dump rc=3` = one damaged line, still usable). Loud / breakdown windows: 20–34 s / 66–78 s from the first captured frame. New commands must be added to `k1_bench.py`'s `ALLOWED` regex first.
- **Loaded silent show** (prepared-show regressions): `BURN=32 bash $T/loaded_silent.sh <name>` → `epoch before=N after=N+1` (8 burners did not drop a frame on this 14-core Mac).
- **Registry:** edit the copy in the export, commit it alone on the stage branch right after each flash (device row "Current silicon", §2 deployed-state row with the previous row marked superseded, a changelog row with read-back sha, identity, judgement and bench numbers).
- **New serial command** = row in `serial_typed_cmd_table.def` + handler/declaration in `serial_typed_dispatch.{cpp,h}` + branch in `serial_menu.cpp`'s `parse_command` ladder + name in `k1_serial_safety.py` and its `TYPED_DEF_BLOB_SHA` (`git hash-object` of the .def) + `tools/esp_emulator/run.py` allow-list.
- **Traps:** `find` and `git` in zsh are wrappers (use `/usr/bin/find`, `/usr/bin/git`, or Python); zsh does not word-split; the Playwright MCP may only write under `$R`; the `/dev` listing needs the sandbox off; a static test reads the IM69D block of `i2s_audio.h` up to the first `#endif` — even inside a comment; `tools/esp_emulator/k1_lightshow_acceptance.json` pins sha256 of `constants.h` and four other files: re-pin when you change them.

---

## 7. Ship path

1. **On silicon now:** Main RPL runs AFE2 stages 1–3 (`df435671`), bench build only. **In source:** `fe/k1-afe2-s3` (pushed), built on rc3.
2. **Next agent:** T2 (hot-input check), T3 (S4), T4 (S5–S7), T5 (explainer), T6 (release-lane merge), T7 (FE board).
3. **Captain:** T1 (one look at the plate); later A06 and A18; optional sound-level-meter reading.
4. **Shipped** = `fe-1.0.0` tagged on an FE board passing every M1 check, recorded in `docs/hardware/device-build-registry.md`.

---

## 8. Done-when for session 5 (suggested)

T2 recorded; S4 built, judged, flashed and benched with the four-band AGC deleted; plan §6 and a new handover updated; lanes and stage branches pushed; closing report with what is true, what is not, links with sha256, ship path, delegation ledger, storage fates.

## Changelog
| Date | Author | Change |
|---|---|---|
| 2026-11-11 | agent:claude (K1-FE-SHOW lead, session 4) | Created at the Captain's request: comprehensive handover for session 5. |
