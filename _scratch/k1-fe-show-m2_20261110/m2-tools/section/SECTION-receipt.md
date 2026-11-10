---
abstract: "Receipt for per-section mapping (10 Nov 2026). PRISM feat/per-section-mapping f2e7359 (feature 849f1cc, parent 87f0c43) and Spine feat/per-section-mapping 1285556 (parent 21265e5), local, not pushed. A creator can now scope a mapping edit to one song section; on Loreen the chorus-only bar-accent edit changed exactly the 116 predicted frames and nothing else. Sectionless output is byte-identical to M2."
---

# Per-section mapping receipt — 10 Nov 2026 (agent: section SSA for the K1-FE-SHOW lead)

**What happened.** A creator can now apply a mapping edit to one named song section. I tested this on the Loreen track: the M2 bar-accent edit (impact `beat_amp` 48000 → 12000) was applied to the first chorus only (segment 4, 45.68–60.81 s). The stream changed in exactly the 116 frames I predicted before compiling, and in no others. Its sha256 equals the predicted `ffa0dd3b…`. Without sections, the editor and the Spine CLI still produce M2's exact bytes. Save, reopen and recompile is byte-identical. The editor's new "Section overrides" control creates, edits, saves and reopens an override. I also fixed the two small K1 FE byte-safety issues in the same PRISM branch. Nothing was pushed. No device, serial port or Wi-Fi path was used. `organs.*.json`, Trinity and `.g5r-clean/PRISM.studio` were not touched.

## Problems first

1. **The inherited splice was wrong by 1 LSB on falling slopes; fixed.** The interrupted agent's `tools/section_splice.js` assumed the VM returns a point's own value at that point. On a falling interval longer than 1 µs, however, `src/vm.js` gives `v + 1`, because BigInt division truncates toward zero. Its own test caught this (`t=2993: spliced 65226 != owner 65225`). I rewrote the exactness repair to use the VM's arithmetic exactly. I also added a test that covers falling slopes, falls to 0, cuts on source points and 1 µs spans. Loreen did not hit the defect: no pulse straddles the chorus boundaries. A boundary that cuts a ramp would have hit it.
2. **My first (c) run refused the "edit" step (my error, not a product defect).** I reused the profile id for the edit. The editor requires every authored edit to write a new profile file (parent-branch design), so it returned `400 EDIT_FIELDS`. The run therefore compiled the 20000 "create" value. I kept it as `raw/c2x_FIRST_RUN_*` and `c2x_first_run_project/` and reran from a fresh pre-edit copy with new ids. The prediction was not changed between the runs (`raw/c1b_…` is byte-identical to the earlier one).
3. **The locked compiler silently ignores `sections`.** PRISM 0.3.1 at the lock `cc00556d` compiles a `mapping_profile_v2` file as if it had no sections, so it applies the whole-track mapping. The Spine now refuses that (`SECTIONS_NOT_APPLIED`; see the test in `raw/t2_…`). Until the Captain or the Spine owner repins PRISM, the Spine's default organs cannot compile a sectioned project. They need `PRISM_ROOT=<0.4.0 checkout>`.
4. **The compile manifest's `compiler.version` is now `0.4.0` for every compile, including sectionless ones.** The manifest describes the compiler that ran, and the Spine's earlier fix exists precisely because a manifest claimed a version that was not running. So the sectionless compile manifest differs from M2's in `compiler.version` and in `compiler.commit` (the commit already differed per commit). ShowBundle, Intent Trace, coverage and stream are byte-identical.
5. **The "section boundary" of the 1 µs step is the compiler's existing beat-pulse step, not new smoothing.** The compiler applies no other smoothing at boundaries, so none is applied here.
6. **Rules exist in two places, guarded by a parity test.** The Spine cannot import PRISM code at the lock, because `src/mapping_profile.js` does not exist at `cc00556d`. The section rules are therefore mirrored in the Spine `tools/validate_profile.mjs`. Both repos carry a byte-identical 24-case list (`profile_section_cases.json`). Each repo checks its validator against it, and the Spine compares the two validators case by case when the resolved PRISM has the module (`raw/t3_…`: equal on all 24). At default organs that comparison is skipped, with the reason shown.
7. **UI craft fix.** In the first screenshot the "everywhere else: 48000" hint wrapped into the 140 px label column. A CSS-only commit (`f2e7359`) moves it under the input. The suites ran at `849f1cc`; I did not rerun them for the CSS-only commit.

## Done-when results

| | Check | Result | Evidence |
|---|---|---|---|
| (a) | PRISM `npm test` on the branch | golden 3/3, `node --test` **60/60**, live streaming 34/0, e2e software 26/0 | `raw/t1_prism_npm_test_branch.log` |
| (a) | Spine `npm test` on the branch (default organs = locked PRISM) | **26 pass, 0 fail, 2 skipped**; the skip reason (no compiler 0.4.0 at the lock) is printed | `raw/t2_spine_npm_test_branch_default_organs.log` |
| (a) | The 2 skipped Spine tests with `PRISM_ROOT=<clone@849f1cc>` | 4 pass, 1 skipped (the "old compiler refused" case, which only applies to the lock); PRISM and Spine verdicts are equal on 24/24 cases; v2 `build-demo` + `verify --project` PASS | `raw/t3_spine_parity_with_prism_849f1cc.log` |
| (a) | New tests on the parents | PRISM 87f0c43: the section test file fails (`src/mapping_profile.js` does not exist). Spine 21265e5: 2 fail (v2 rejected as `PROFILE_INVALID`; no `SECTIONS_NOT_APPLIED`). Guard probe on 87f0c43: Composer reaches its handler (400 "Composer not active", not refused), and `:set_mode` without confirmation returns 200. On the branch both return 409. | `raw/t4_…`, `raw/t6_…`, `raw/t5_guard_probe_parent_87f0c43.log` vs `raw/t5_guard_probe_branch_849f1cc.log` |
| (b) | Sectionless, real editor (pre-edit → edit → post-edit → reopen → verify) | ShowBundle **90855dde…**, Intent Trace **8128452f…**, stream **116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3**; `cmp` against M2's stream is equal; verify diffs `[]` | `raw/b1_editor_e2e_sectionless.log`, `raw/b1_post_edit_sha256.txt` |
| (b) | Sectionless, real Spine CLI `verify --project` (PRISM 849f1cc) + M2's `make_stream.py` | VERIFY_PROJECT: PASS; same ShowBundle / trace; stream `116981ee…` | `raw/b2_spine_verify_sectionless.log` |
| (c) | Prediction written before the compile | 116 frames (5542–7245, 24 windows) must change, impact bytes 20–21 only; the other 26,754 frames must equal the pre-edit bytes; expected stream `ffa0dd3b…` | `raw/c1_PREDICTION_written_before_compile.json`, `raw/c1c_PREDICTION_DECLARED.md`, `tools/predict.py` |
| (c) | Chorus-only edit through the real editor API | **MATCH**: 116 changed = predicted set; changed bytes {20, 21}; stream sha = predicted `ffa0dd3b27489cdd827e1d39d47ea0e88585d3e0f7dd84dc17de4568445dd6e2`; the whole-track edit's 1,466 changed frames outside the span stay at pre-edit bytes; Intent Trace: 1,816 rows in the span carry `"section":"chorus_1"`, and all 25,054 other rows are byte-identical to the pre-edit trace | `raw/c2_section_e2e.log`, `raw/c2_section_e2e_result.json`, `raw/c3_compare.log`, `c_out/compare_c.json`, `c_out/diff_table.md` |
| (c) | Plot (I looked at it) | Inside the shaded chorus the off-beat pulses drop to ~10–12 k; at 45.24 s, just before the boundary, the whole-track edit drops but the sectioned build keeps 46 k; the change strip shows red only inside 45.68–60.81 s | `c_out/impact_sectioned.png` |
| (c) | Unknown segment refused through the API | 400 `SECTION_UNKNOWN_SEGMENT` (segment 15 of 0..14) | `raw/c2_section_e2e_result.json` |
| (c) | Real Spine CLI on the sectioned (v2) Loreen project | VERIFY_PROJECT: PASS (ShowBundle `6f324e1c…`, trace `2f682b05…`) | `raw/c4_spine_verify_sectioned.log` |
| (d) | Save → reopen (new server process) → recompile | verify `ok`, diffs `[]`; `showbundle.json`, `trace_120hz.jsonl`, `stream_120hz.prsm`, `mapping_coverage.json` and `compile_manifest.json` byte-identical | `c_out/compare_c.json` (`reopen`), `raw/c2_section_e2e_result.json` |
| (e) | UI create / edit / save / reopen (headless Chromium, real `app.js`, real server on 127.0.0.1) | create 20000 → Edit → 12000 → server restarted + page reload → list shows `chorus_1 … = 12000`; no page errors | `raw/e1_section_ui_headless.log`, `ui/section_ui_steps.json` |
| (e) | Screenshots I looked at | `ui/section_control_2_edited.png` (segment "4 · chorus · 45.68 s–60.81 s", value 12000, hint "everywhere else: 48000", list entry with Edit/Remove), `ui/section_control_3_reopened.png` (after reopen) | `ui/` |

## Design, against the lead's decisions

- **Versioned.** `mapping_profile_v2` = v1 + `sections`. The v1 schema has no minor-version rule (the Spine's `mapping_profile_v1.schema.json` is a bare `required` list), so v2 is a new schema. Selection is by `segment_indices` and/or `label`, or by `time_range_us`, which must equal segment boundaries. Validation refuses unknown segments, label mismatches, off-boundary ranges, overlaps, empty overrides, overrides that change no value, provenance changes and unknown keys.
- **Sectionless ⇒ byte-identical.** With no sections the compiler emits ShowBundle `0.3` with no `sections` key, and the VM writes the same trace rows. Proven in (b).
- **ShowBundle 0.4, justified.** The 0.3 schema has `additionalProperties: false`. Recording which section produced which time span therefore needs a new top-level field, so the schema version moves to 0.4. 0.4 is emitted only when sections were applied.
- **`src/vm.js` changed, because it was unavoidable for the provenance rule.** The Intent Trace is written only by `replayToJsonl`. Making it name the section that produced each frame needs the VM to read `bundle.sections`. The change is gated on `version === "0.4"`: a 0.3 bundle takes exactly the old code path. Proof: golden 3/3 and the byte-identical (b). Downstream readers that parse trace rows (`traceToPrsmStream`, M2 `make_stream.py`) read only `t_us` and `prim8_u16`.
- **Boundaries.** Switching happens at the segment boundary with the compiler's existing 1 µs step. The section's dimension is computed over the whole track, so normalisation windows match the top-level one, and is then used only inside its spans.
- **Spine.** The schema, the validator, `build-demo` and `verify --project` accept v2. The rules are mirrored in two places, with the parity test from Problem 6.
- **K1 FE fixes (PRISM).**
  - The editor has a device target, `--device-target`, which defaults to `k1_fe`. Every `/api/composer/*` route returns 409 `K1CT_NOT_FOR_K1_FE` unless the editor was started with `--device-target k1_usb_bridge`, and `/api/device/play` cannot switch the target per request.
  - `/api/instrument/mode` writes `:set_mode` only when the request carries `confirm: "persist_mode_to_flash"`. The button reads "Save mode to device flash…" and asks for confirmation.
- **What I kept from the interrupted agent's diff.** I kept all of it: `mapping_profile.js`, the compiler changes, the 0.4 schema, the `vm.js` gate, the editor API and UI, and the two K1 FE guards all matched the decisions above. I replaced only the repair algorithm in `section_splice.js` (Problem 1). I added the shared case list, the Spine side, the CHANGELOGs and version-assertion updates (0.3.1 → 0.4.0 in two existing tests), and the CSS fix.

## Commits (local, not pushed)

- PRISM clone `_scratch/k1-fe-show-m1_20261109/prism-studio-locked`, branch `feat/per-section-mapping`: `849f1cc90d771c2b27b4e7a38bae883a0f6440cf` (feature), `f2e7359` (CSS). The clone is put back to detached `cc00556d` with a clean tree, as the PRISM fix lane left it. Both branches are kept.
- Spine, branch `feat/per-section-mapping`: `1285556620d156d11792ff2588472a1492c22f34`. The untracked `docs/architecture/` was not touched.

## Re-run commands (lead)

```
R=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m1_20261109/prism-studio-locked
S=/Users/spectrasynq/Workspace_Management/Software/SpectraSynq-Instrument-Spine
D=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-tools/section
P=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-tools/prism
M2=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-compose/projects/loreen
PYA=/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-analysis/conda-env/bin/python3   # has matplotlib
lsof -nP -iTCP:7777 -sTCP:LISTEN                       # must be empty
cd $R && /usr/bin/git switch feat/per-section-mapping && npm test
cd $S && /usr/bin/git switch feat/per-section-mapping && unset PRISM_ROOT && GIT_OPTIONAL_LOCKS=0 npm test
PRISM_ROOT=$R GIT_OPTIONAL_LOCKS=0 node --test tests/profile_rules_parity.test.js
# fresh pre-edit Loreen copy (helper)
fresh() { rm -rf $1 && mkdir -p $1/mapping && cp -R $P/e2e/loreen/inputs $1/ && cp $P/e2e/loreen/mapping/prim8_natural_v1.json $1/mapping/ && cp $M2/composition.pre_edit.snapshot.json $1/composition.json; }
# (b) sectionless: editor, then Spine CLI
fresh $D/rerun/b/loreen && node $P/tools/editor_e2e_loreen.mjs $R $D/rerun/b/loreen $D/rerun/b/result.json
shasum -a 256 $D/rerun/b/loreen/out/post_edit/{showbundle.json,trace_120hz.jsonl,stream_120hz.prsm}   # 90855dde 8128452f 116981ee
cd $S && PRISM_ROOT=$R node tools/instrument.mjs verify --project $D/rerun/b/loreen/composition.json --out $D/rerun/b/spine
# (c)+(d) chorus-only edit; prediction first, then compile, then compare
/opt/homebrew/opt/python@3.13/bin/python3.13 -I $D/tools/predict.py $D/rerun/prediction.json
fresh $D/rerun/c/loreen && node $D/tools/section_e2e.mjs $R $D/rerun/c/loreen $D/rerun/c/result.json
MPLCONFIGDIR=$(mktemp -d) $PYA -I $D/tools/compare_c.py $D/rerun/c/loreen $D/rerun/prediction.json $D/rerun/c/out   # verdict MATCH, exit 0
cd $S && PRISM_ROOT=$R node tools/instrument.mjs verify --project $D/rerun/c/loreen/composition.json --out $D/rerun/c/spine
# (e) UI
fresh $D/rerun/e/loreen && node $D/tools/section_ui_headless.mjs $R $D/rerun/e/loreen $D/rerun/e/ui /Users/spectrasynq/.npm/_npx/86170c4cd1c5da32/node_modules/playwright-core /Users/spectrasynq/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell
# guards, parent vs branch (no device; no route that opens a port)
node $D/tools/guard_probe.mjs $R
cd $R && /usr/bin/git switch --detach cc00556d1df2f863c6a0d914ef613886b050a408   # restore the lock state for other lanes
```

## Ship path

1. **Done.** Both branches are committed locally with tests and CHANGELOG entries. The evidence is in this folder.
2. **Lead.** Re-run the commands above, push both branches (PRISM `feat/per-section-mapping` sits on `fix/one-instrument-editor-loop`; the Spine branch sits on `fix/cli-authored-project`) and open the PRs in order: parent PRs first.
3. **PRISM and Spine owners.** Review and merge.
4. **Captain or Spine owner.** Repin `organs.lock.json` PRISM to the merge commit. Agents never repin. Until then the Spine's default organs refuse sectioned projects (`SECTIONS_NOT_APPLIED`), and sectionless projects behave as before.
5. **What counts as shipped.** After the repin (with the Spine goldens that pin compiler commit and version refreshed, as at every lock move), `npm test` in the Spine with default organs runs the parity and v2 CLI tests instead of skipping them, and the chorus-only Loreen edit reproduces stream `ffa0dd3b…` through the Spine CLI.

## Changelog
- 2026-11-10 agent:section-ssa — checkpoint after (b); final with (c)–(e).
