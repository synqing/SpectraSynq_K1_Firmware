# Codex Offload — Patterns Reference

## Contents
- Consumption Contract anatomy
- Gate discipline
- Output format contracts
- Anti-patterns
- SensoryBridge-specific offload boundaries

---

## Consumption Contract Anatomy

Every offload starts with a written contract. No contract → no offload.

```
INPUT:  [exact files, symbols, or queries the subagent needs]
OUTPUT: [format, max size, what is excluded]
GATE:   [command that must pass — pytest, bun run check-types, etc.]
ESCAPE: [hard prohibitions — commits, deploys, gate bypass flags]
```

**Why:** Without a contract, subagents over-read, over-write, and return walls of prose the orchestrator must parse. The contract is the interface. Treat it like a function signature.

---

## Gate Discipline

```bash
# DO — run gate before AND after every offload
pytest tests/ -v                          # baseline
# ... Agent offload ...
pytest tests/ -v                          # verify

# DON'T — trust the subagent's self-report
result = Agent(...)
# BAD: "subagent said tests pass, moving on"
```

**Why:** Subagents can hallucinate test results. The Codex breakage incident (2026-06-11, see `project_sb_codex_breakage_restore.md`) traced to a dirty-tree revert where both the offloaded change and the restored HEAD failed eyes-on. A host gate run would have caught it at the boundary.

**The class fix rule:** If you discover a gate is broken, fix the gate class first, then re-run. Never run the offload pipeline through a known-broken gate. (See `feedback_amend_broken_gates.md`.)

---

## Output Format Contracts

### Diff-only (preferred for code changes)

```
OUTPUT: Unified diff only. Max 80 lines. No prose explanation. No file paths outside src/.
```

### Verdict (preferred for analysis/exploration)

```
OUTPUT: One of [PASS|FAIL|UNCERTAIN] + max 5 bullet points. No raw file content.
```

### Summary (preferred for research)

```
OUTPUT: Max 200 tokens. Key finding + recommended next action. No raw logs.
```

**WARNING: Never accept "here is the full file" as output**

The subagent rewrote the whole file instead of diffing → you lose context on what changed, the gate becomes meaningless, and merge conflicts multiply. Enforce diff-only for all code changes.

---

## SensoryBridge-Specific Offload Boundaries

### NEVER offload these without Captain approval

- Changes to `src/audio/` or any DSP path (Core 0 hard real-time — blast radius = audio corruption)
- Changes to `platformio.ini` build flags (5 `SB_*_V2` flags govern the audio-semantic forward-graft)
- Changes to `tests/` gate files that loosen assertions

### Safe to offload

- New effect implementations in `src/effects/` (bounded, tested via host harness)
- Refactors within a single file when the gate covers that file
- Documentation and forensics in `docs/`
- New test fixtures in `tests/fixtures/`

### Audio pipeline rate — do not touch inline

AP rate is 133 Hz (12800/96). `SAMPLE_RATE` has high blast radius. If an offload touches timing constants, it must come back as a diff reviewed against `project_tempo_beat_foundation.md` before applying.

---

## Anti-Patterns

### WARNING: Offloading Without a Gate

**The Problem:**
```python
# BAD — no gate defined
Agent(prompt="Refactor the onset detection in goertzel.cpp")
```

**Why This Breaks:**
The subagent may silently break `test_onset_beat_replay.py`. Without a gate in the contract, you won't discover this until device eyes-on — which is the most expensive validation tier.

**The Fix:**
```python
# GOOD — gate is part of the contract
Agent(prompt="""
GATE: pytest tests/test_onset_beat_replay.py -v must exit 0
...
""")
```

---

### WARNING: Accepting Prose When You Needed a Diff

**The Problem:**
Subagent returns 300 lines of explanation + inline code snippets. Orchestrator must now parse what changed.

**The Fix:** Enforce format in the contract. If the subagent ignores the format, reject the result and re-dispatch with a stricter prompt. Do not extract the changes manually — that's how drift enters.

---

### WARNING: Using Codex to Bypass the Founder Execution Boundary

Codex offloads do NOT bypass the boundary. If a task requires Captain decision (irreversible, public-facing, high-blast-radius), offloading it to Codex and acting on the result is still a violation. The boundary applies to the *decision*, not the *execution surface*.