# Codex Offload — Workflows Reference

## Contents
- Standard offload workflow
- Parallel offload workflow
- Iterative offload (iterate-until-pass)
- Rollback workflow
- SensoryBridge effect development offload

---

## Standard Offload Workflow

Copy this checklist and track progress:

- [ ] Step 1: Define consumption contract (INPUT / OUTPUT / GATE / ESCAPE)
- [ ] Step 2: Run gate baseline — record result
- [ ] Step 3: Dispatch Agent with contract embedded in prompt
- [ ] Step 4: Receive bounded output (diff or verdict)
- [ ] Step 5: Apply diff (if applicable)
- [ ] Step 6: Run gate — must match or improve on baseline
- [ ] Step 7: If gate fails → rollback, diagnose, do NOT re-offload the broken state

---

## Parallel Offload Workflow

When multiple independent subproblems exist, fan out:

```python
# new code to add
results = await parallel([
    lambda: Agent(description="Explore subsystem A", prompt="CONTRACT_A..."),
    lambda: Agent(description="Explore subsystem B", prompt="CONTRACT_B..."),
])
# Each result is bounded by its contract.
# Synthesize in orchestrator — keep synthesis <50 lines.
```

**When to use:** Exploring multiple files, validating multiple test suites, implementing multiple independent effects.

**When NOT to use:** When subproblems share a file (worktree isolation required) or when B depends on A's output.

---

## Iterative Offload (Iterate-Until-Pass)

For tasks where the first attempt may miss edge cases:

1. Dispatch subagent with contract
2. Apply diff
3. Validate: `pytest tests/ -v`
4. If validation fails:
   - Collect the failure output (max 20 lines)
   - Re-dispatch with failure included in new contract INPUT
   - Repeat from step 2
5. Only proceed when gate exits 0

**Cap iterations at 3.** If gate still fails after 3 rounds, escalate — the problem is likely architectural, not implementational.

---

## Rollback Workflow

If a subagent's diff breaks the gate:

```bash
# Stash or revert the applied diff
git diff HEAD  # inspect what changed
git checkout -- <affected files>  # revert

# Re-run gate to confirm clean state
pytest tests/ -v

# Diagnose before re-offloading
# DO NOT re-dispatch the same prompt — it will produce the same broken diff
```

**The Codex breakage pattern** (2026-06-11): A Codex dirty-tree revert restored HEAD but the restored state also failed eyes-on. Root cause: the rollback target (`dd2902f`) was confirmed safe, but the git operations ran against a dirty tree. Always verify `git status` is clean before a rollback target becomes the baseline.

---

## SensoryBridge Effect Development Offload

Standard workflow for adding a new beat-reactive effect (safe offload scope):

- [ ] Step 1: Define effect spec (mode number, name, beat reactivity type: spatial/transport ONLY — no global brightness-on-beat per THE STROBE LAW)
- [ ] Step 2: Run baseline: `pytest tests/ -v`
- [ ] Step 3: Dispatch Agent:
  ```
  INPUT:  src/effects/ (existing effects for pattern reference), src/globals.h (mode enum)
  OUTPUT: Diff adding new effect file + mode registration. Max 120 lines.
  GATE:   pytest tests/test_sb_tab5_wireless_controller_static.py -v must pass
  ESCAPE: No changes to src/audio/, src/goertzel/, platformio.ini, or existing effect files
  ```
- [ ] Step 4: Apply diff, run gate
- [ ] Step 5: Host visual validation via render_replay (dual-channel — see `project_sb_lgp_dual_channel_fidelity.md`)
- [ ] Step 6: Device eyes-on (final gate — not skippable)

**Never merge an effect that passed host tests but skipped device eyes-on.** The forward-graft promotion (2026-06-05) established device eyes-on as the mandatory final gate. Host harness validates correctness; device validates perceptual impact.

---

## Integration with context-mode

For large-scale exploration before an offload:

```python
# new code to add — gather facts into knowledge base first
ctx_batch_execute([
    {"label": "effect-inventory", "command": "ls src/effects/"},
    {"label": "mode-enum", "command": "grep -n 'LIGHT_MODE' src/globals.h"},
])
# Then search the indexed result — don't flood orchestrator with raw output
ctx_search(queries=["beat reactive effects", "strobe law compliance"])
# Offload with the compact search result embedded in contract INPUT
```

See the **context-mode** skill for `ctx_batch_execute` and `ctx_search` usage.