# Lane C-spine receipt (9 Nov 2026)
Raw logs and hashes: raw/ (sha256_all.txt). Clone: ../prism-studio-locked @ cc00556d1df2f863c6a0d914ef613886b050a408.

## C1 PASS (clone + diff done)
- Clone of synqing/PRISM.studio succeeded; detached at cc00556d (raw/c1_clone.log).
- .g5r-clean/PRISM.studio working tree is byte-identical to commit 07eb822 (7 differing files each cmp-equal to `git show 07eb822:<file>`), which is an ancestor of cc00556d, 3 commits behind (e37c7da compiler 0.3.1, d7bd14f minimal-editor workflow, cc00556 CLI realpath fix).
- Differing files (raw/c1_diff_compiler.patch, raw/c1_diff_others.patch): CHANGELOG.md, prism_minimal_editor/{server.js,public/app.js,public/index.html}, tools/mapping_transforms_v1.js, tools/test_trinity_compile_v0_3.js, tools/trinity_compile_showbundle_v0_3.js; clone-only: tools/test_mapping_transforms_v1.js; working-tree-only: .tmp/.
- Compiler differs: 0.3.0 (working tree) vs 0.3.1 (lock): activity-aware transform + fail-closed NaN + CLI realpath fix.
- Unchanged, identical sha256: vm.js 788f4860..., playback.js 165d4e37..., cdc.js 451a4886..., intent_cdc_stream.js 8a082869....
- Compiler sha256: clone 7b188785efee..., working tree 4dfa4d0968a5....

## C2 (host-only, env PRISM_ROOT for the clone run; organs.local.json untouched; writes only to gitignored Spine .tmp and my clone)
- doctor, working tree: PASS (prism effective 07eb822 vs locked cc00556; reported, not enforced).
- verify x1, working tree: FAIL "COMPILE_MANIFEST_MISMATCH" (compiler version/commit in manifest differ from pinned hash). Showbundle, coverage and trace hashes DO match expected.
- doctor, clone: PASS (effective == locked for prism and trinity).
- verify x2, clone: PASS both, identical hashes.
- npm test (Spine): PASS 14/14. PRISM node tests (adapter, compile v0.3, mapping transforms) in clone: PASS 38/38. npm run golden (v0.1-v0.3): PASS.
- Trinity pytest (2 files): BLOCKED, no pytest module for python3.13; nothing installed.
- tools/g5_clean_verify.sh: NOT RUN (it rewrites organs.local.json and clones to TMPDIR); its steps replicated manually above.
- Hashes: showbundle 6a0678c2..., coverage a800c778..., trace (Intent Trace) bcdd0c22...b8, identical on both trees; compile_manifest differs (wt 0240c348, clone 3a1af3d6); build_manifest differs (commit).
- A04 deterministic compile: PASS. Each verify compiles twice and byte-compares bundle, coverage, manifests; clone run-a and run-b showbundle both 6a0678c2.
