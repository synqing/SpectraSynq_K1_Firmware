# Track A — native 40-bin STM evidence bundle

**Track:** WB-3 Track A (`K1_STM`, env `k1_bench_im73d_stm`).  
**Policy:** `docs/forensics/stm-producer/WB3_CAPTAIN_DECISION_PENDING.md`.

## Integration base (verified 2026-07-29)

- `git fetch origin`
- `d40114f` and `a9ff00c` are ancestors of `origin/main` (**YES**)
- Suggested detached worktree: `git worktree add --detach /tmp/k1_wb3_track_a origin/main`

## Gate 0 — clangd

Record smoke outcome or pointer to `docs/forensics/stm-producer/GATE0_CLANGD_BLOCKER.md` in this run’s `manifest.json`. **Blocker:** C++ convergence edits until Gate 0 passes.

## H1 host replay (mechanism)

**Status 2026-07-29:** **PASS** on `origin/main` @ `f9bd28e` — 1/1 pytest.

```bash
cd /tmp/k1_wb3_track_a   # or any clean main worktree
python3 -m pytest tests/test_k1_stm_replay.py -q
```

**Blocker on `lane/dual-sync-phase0`:** `tests/test_k1_stm_replay.py` is absent on that branch — use main worktree only.

## Evidence checklist (per `<run-id>/`)

- [ ] `manifest.json` — git SHA, env, MAC (if flashed), rollback image, Captain playback citation
- [ ] `h1_pytest.log` — full pytest output for `test_k1_stm_replay.py`
- [ ] `gate0_clangd.txt` — diagnostics smoke or INDETERMINATE note
- [ ] `core0/` — outputs per `WB3_CORE0_BENCH_PROCEDURE.md` or `WB3_CORE0_BENCH_INDETERMINATE.md`
- [ ] `vp/` — `stm_vp_compare.py` artefacts + Captain eyes-on note for modes 7/8
- [ ] `bench_fixes.md` — list of implementation fixes applied on track branch (post–Gate 0)

## Hardware

**No flash or audio in this scaffolding session.** Captain must allocate bench K1, approve playback, and confirm MAC before any flash of `k1_bench_im73d_stm`.
