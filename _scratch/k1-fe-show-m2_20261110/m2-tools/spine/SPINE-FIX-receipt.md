---
abstract: "Receipt for Spine branch fix/cli-authored-project (commit 21265e5, from main 597f315, not pushed). The real Spine CLI now compiles and verifies the authored Loreen project to M2's exact bytes, with no compose.mjs. Defects 1 to 4 fixed with 9 new tests that fail on main; defect 5 reported."
---

# Spine CLI authored-project fix, receipt (10 Nov 2026, agent lane-c-spine)

## What happened

The Spine command line can now build and check an authored composition on its own. Before, it always used the stock mapping profile and the Spine's own fixtures folder, so it could not handle the edited Loreen project and the lane needed the workaround driver `compose.mjs`. I fixed that on a new branch, then ran the real CLI on the Loreen project twice. ShowBundle, Intent Trace and the Prim8 stream all came out byte-identical to M2's. Nothing was pushed. Nothing was written into the m2-compose or lane-b folders (0 files newer than the start, checked at the end).

## Result against the brief

| Brief item | Result |
|---|---|
| Spine test suite green on branch | `npm test`: 23 tests, 23 pass, 0 fail, 0 skipped (main: 14). Log `raw/t4_branch_npm_test.log`. |
| New tests fail on main@597f315 | 9 of 9 fail with main's `tools/instrument.mjs` (`raw/m1_main_tools_new_tests.log`), 9 of 9 pass on the branch (`raw/t3_branch_new_tests_clean_organs.log`). |
| CLI compile + verify of projects/loreen, twice | Both runs PASS (`raw/f1a`, `f1b`, `f2a`, `f2b`). |
| ShowBundle byte-identical to M2 | Yes. sha256 `90855ddee4927439d638c5098b4ae2e32abe812fa6d984d0d936b53a2980801b` (starts 90855dde). |
| Intent Trace byte-identical to M2 | Yes. sha256 `8128452f0547283263b679fe9113b65cd9636bd6e5ead86b2c17b0657cea1bde` (starts 8128452f). |
| Prim8 stream | Yes. Stream built from the CLI's output with M2's own `make_stream.py`: sha256 `116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3`, 26,870 frames, equal to M2's file; sidecar also byte-equal (`raw/h1_make_stream_from_cli_output.log`). |
| Compile twice, identical | Yes. Run 1 and run 2 are byte-identical in every file; inside each run, run-a and run-b are identical too (A04). Coverage and compile manifest are also byte-equal to M2's. |

`raw/g1_byte_compare.log` has every pair. The only different file is the build manifest, and that is expected (finding 1 below).

## The four defects

1. **Hard-coded profile.** The CLI now takes contract, stem features and mapping profile from the project's own `inputs` (relative to the project file, or absolute; the old G5 project keeps its Spine-root-relative paths). It checks the input hashes, validates the profile with the Spine's `validateProfile` (the `mapping_profile_v1` check) and requires it to match `mapping_profile_id`. The PRISM example drift check now applies only to a profile that has the example's id, since an authored profile is not a copy of it.
2. **`verify --project` ignored the profile.** It now rebuilds from the project's inputs and compares every recorded hash it can reproduce: Intent Trace, ShowBundle, coverage, compile manifest. Fixture goldens (`<fixture>/expected`) still apply, but only to fixture x default profile, which is what they describe.
3. **False compiler version.** The build manifest said 0.3.0 while 0.3.1 ran (`raw/e1_defect3_and_organs_local_report.txt`). It is now read from the compile manifest the compiler wrote. The one golden that held the false value, `fixtures/ci_click_3s/expected/build_manifest.sha256`, is refreshed with the CLI's own `--write-expected`. The ShowBundle, trace, coverage and compile-manifest goldens did not change (`raw/d2`).
4. **Writes into its own `.tmp/`.** `--out DIR` is now accepted by `build-demo` and `verify` (fixture and project). Default is unchanged. A folder named with `--out` is never wiped (build-demo used to delete its output folder first; it still does for the default `.tmp` folder only).
5. **organs.local.json (reported, not edited).** It points PRISM at `.g5r-clean/PRISM.studio`. That checkout is now at the lock `cc00556d`, detached and clean, so the default organs resolve correctly. At the start of my work it was at `07eb822`. I used the default organs for every result above. The locked clone in the m1 folder is still at `cc00556d` but is now on branch `fix/one-instrument-editor-loop` with the PRISM agent's uncommitted edits (8 changed files, 2 new). A run through that clone reports PRISM dirty and fails the build-manifest golden. This happened once in my own first test run (`raw/t1_branch_new_tests.log`) and was environmental. Details in `raw/e1_defect3_and_organs_local_report.txt`.

## Findings

1. **Build manifest differs from M2's, by design.** The CLI's build manifest also records a `trinity` block and the PRISM remote. M2's `compose.mjs` wrote a smaller one (diff in `raw/g2_build_manifest_diff_vs_M2.txt`: exactly those two additions). It is a provenance record, so the CLI prints a NOTE and does not fail on it. M2's recorded `build_manifest_sha256` therefore will not match; the compile-manifest and content hashes do.
2. **Trace file name.** The CLI writes `run-a/trace.jsonl`. `make_stream.py` reads `trace_120hz.jsonl`. I staged a renamed copy (same bytes) for the stream step. I did not rename the CLI output because it was not asked for.
3. **`npm run test:c1` has one failing test, and it fails identically on main** (5 tests, 4 pass, 1 fail, `raw/m2_main_tools_test_c1.log` and `raw/t6_branch_test_c1.log`). It is the recorded C1 "TUNE" evidence gate, not part of `npm test`, and untouched by this change. `npm run test:c1t`: 31 of 31 pass.
4. **Commit trailer.** I used `Co-Authored-By: Claude Sonnet 5.5`, the model that actually ran, because the session's attribution rule requires it. The brief asked for the Opus 5.5 line.

## What the CLI still cannot do (not in the brief)

`init`, `edit` and `--record` (writing the recorded outputs into a new or edited project) are still only in `compose.mjs`. `verify` needs a project that already records its hashes. Until a record step exists in the CLI, the creator loop needs `compose.mjs compile --record` once per edit.

## Re-run commands (for the lead)

Use the default organs. Do not set `PRISM_ROOT` to the m1 clone while the PRISM agent is working in it.

```bash
cd /Users/spectrasynq/Workspace_Management/Software/SpectraSynq-Instrument-Spine
/usr/bin/git switch fix/cli-authored-project          # commit 21265e5
unset PRISM_ROOT; export GIT_OPTIONAL_LOCKS=0
npm test                                              # 23 tests

EV=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-tools/spine
L=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen/composition.json
for n in 1 2; do
  node tools/instrument.mjs build-demo --project $L --out $EV/out/run$n/build
  node tools/instrument.mjs verify     --project $L --out $EV/out/run$n/verify
done
bash $EV/compare_bytes.sh      # run1 vs run2, run-a vs run-b, CLI vs M2. Only the build manifest line says DIFFERENT (finding 1).
# stream (read-only use of M2's tool; stage the trace under the name it expects):
mkdir -p $EV/out/stream-input && cp $EV/out/run1/verify/run-a/{showbundle.json,compile_manifest.json} $EV/out/stream-input/ && cp $EV/out/run1/verify/run-a/trace.jsonl $EV/out/stream-input/trace_120hz.jsonl
M2=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/opt/python@3.13/bin/python3.13 /Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/tools/make_stream.py --run $EV/out/stream-input --project $M2/composition.json --asset-json $M2/inputs/asset.json --out $EV/out/loreen_post_edit_120hz.prsm
shasum -a 256 $EV/out/loreen_post_edit_120hz.prsm       # expect 116981ee...e97e3
# new tests failing on main (only tools/ and one golden are swapped to main's versions, then restored):
/usr/bin/git checkout 597f315 -- tools/instrument.mjs fixtures/ci_click_3s/expected/build_manifest.sha256
node --test tests/instrument_cli_authored.test.js       # expect 9 fail
/usr/bin/git checkout HEAD -- tools/instrument.mjs fixtures/ci_click_3s/expected/build_manifest.sha256
```

## Ship path

1. **Done:** the Spine CLI builds and verifies the authored Loreen project to M2's exact bytes, on a local branch with tests and a changelog entry.
2. **Remaining:** (a) the Spine owner reviews and merges `fix/cli-authored-project` (nothing is pushed); (b) add `--record` (and project init/edit) to the CLI so a new edit needs no `compose.mjs`; (c) the PRISM editor endpoint fix, which belongs to the PRISM agent; (d) m2-emu G4 and bench playback.
3. **Who acts:** (a) the lead or Captain on the Spine repo; (b) a Spine writer on a later brief; (c) the PRISM agent; (d) m2-emu and the Captain.
4. **What counts as shipped:** the branch merged to main with `npm test` and `g5_clean_verify.sh` green, and the stream sha `116981ee...` passing m2-emu G4.

## Not run

`tools/g5_clean_verify.sh` (it clones organs from GitHub and rewrites `organs.local.json`; not needed here). No device, no serial, no Wi-Fi, no mutation testing. Each suite was run once after its last code change; the one repeat (new tests, `t1` then `t3`) was because the organ checkout changed state, not the code.

## Changelog
- 2026-11-10 agent:lane-c-spine, created.
