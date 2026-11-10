# Expected results, declared before the Loreen editor e2e run (10 Nov 2026)

Source of expectations: M2 `m2-compose/M2C-receipt.md` and `m2-compose/raw/sha256_all.txt`.

- Every editor call returns HTTP 200, except `POST /api/bundle` on the compiled ShowBundle: HTTP 409.
- Pre-edit compile: ShowBundle `cae4fbc1…`, Intent Trace `9491b071…`, stream `65143215…` (= M2 pre-edit), byte-identical to M2 `out/pre_edit/run-a/*` and `stream/loreen_pre_edit_120hz.prsm`.
- Authored edit writes `mapping/prim8_natural_v1_bar_accent.json` byte-identical to M2's (sha256 `4847be0b…`).
- Post-edit compile: ShowBundle `90855dde…`, Intent Trace `8128452f…`, stream `116981ee920f9006954357293bc91ff5b2d02ddb06fff72e24de56951b5e97e3`, 26,870 frames, byte-identical to M2 `out/post_edit/run-a/*` and `stream/loreen_post_edit_120hz.prsm`. `mapping_coverage.json` identical too.
- Reopen (new server process) + recompile with verify: HTTP 200, verification ok, same three hashes.
- Expected differences (not findings): `compile_manifest.json` records compiler.commit = the branch commit actually running instead of cc00556d, so its bytes differ from M2's in that field only; the composition's recorded `outputs` block uses the editor's keys (adds stream_sha256, frames, compiler, compiler_commit, prism_tree_dirty; no build_manifest_sha256) and `recorded_from` = `out/post_edit`.
