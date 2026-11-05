# 1. Changed artefacts
- `scripts/regression-harness/golden/harness_selftest.py`: excludes transient generated `*.ino.cpp` from mutation copies. Uncommitted; orchestrator owns commit.
- `sw-h/receipt.json`, `focused-receipt.json`, `final-receipt.json`, `gates.json`, `repair.diff`: full-run failure, focused repair and full rerun evidence.

# 2. Gates
| Gate | Command | Exit code | Receipt |
|---|---|---:|---|
| Full host suite, run 1 | `python3 -m pytest tests -q` | 1 | `sw-h/receipt.json` |
| Repaired mutation self-test | `python3 -m pytest tests/test_harness_selftest.py -q` | 0 | `sw-h/focused-receipt.json` |
| R accidental commit-hook full suite | `git commit` hook: `pytest tests/ -q` | Unavailable; terminated early | `sw-r/hook-termination.json` |
| Full host suite, run 2 | `python3 -m pytest tests -q` | 0 | `sw-h/final-receipt.json` |

# 3. Measured numbers
- Host run 1 at `19992ad7923efc18ff4e7ad8b60ae010531c3fb4`: 2,027 passed; 2 skipped; 1 failed before repair.
- Focused mutation self-test after repair: 1 passed, 0 failed.
- Host run 2 at `85da22248da22514a209c946ec5f0761d7f97933` plus the uncommitted copy fix: 2,028 passed; 2 skipped; 0 failed.
- No firmware timing measurements or device claims.

# 4. Not verified
- No open host-suite item at the tested source state.
- R's interrupted hook invocation produced no complete result; not counted as completed verification.
- First failure: mutation copy raced PlatformIO removal of generated `.ino.cpp`. `.gitignore:18–19` identifies these as generated build outputs. Authored sources and mutation checks remain unchanged.
- No other copytrees changed; no hardware touched.

# 5. Decisions
- None for Captain. Orchestrator reviews and commits the verified repair.
