# Agent Operating System — SpectraSynq K1 Firmware

Concise manual for Devin / Claude / Codex-style agents working on this repo.

---

## 1. Session bootstrap ritual

At the start of every session, run:

```bash
bash scripts/agent/session-bootstrap.sh
```

Then read this file and the files it flags as current. Do not proceed until you know:

- current branch
- HEAD commit
- dirty / untracked state
- active lane
- whether handoff docs are stale

---

## 2. Source-of-truth hierarchy

Trust sources in this order:

1. **Git branch + HEAD + working tree** — canonical current state
2. **`platformio.ini` + `scripts/platformio/k1_upload_guard.py`** — envs and hardware targets
3. **Lane-specific docs** — e.g. `docs/hardware/im73d122-ap-vp-migration-plan.md`
4. **`docs/hardware/device-build-registry.md`** — physically-deployed state (including dirty entries)
5. **`.claude/CLAUDE.md` + `AGENTS.md`** — load-bearing process rules
6. **`claude-mem`** — prior-session context and recurrence patterns only

`progress.md`, `.claude/handoff.md`, and `docs/spec-index.md` are authoritative only when confirmed fresh. If `scripts/agent/repo-truth.sh` flags them stale, treat them as historical, not current.

---

## 3. Current-lane verification rule

The current live lane is:

- **Branch:** `lane/im73d-pdm-eval`
- **Project:** `SpectraSynq_K1_Firmware`
- **Focus:** IM73D122 PDM microphone evaluation on bench K1 `B489A500`

Before any work, verify the lane has not shifted. If `git status` shows a different branch, or if the lane doc says something different, stop and report the conflict.

---

## 4. Stale-doc handling rule

If `repo-truth.sh` reports `handoff.md`, `progress.md`, or `spec-index.md` as stale:

- Do not rely on them for current lane status.
- Do not silently update them to match git.
- Report the stale docs in your handoff.
- Ask for explicit approval before editing governance/docs files.

The dirty `docs/hardware/device-build-registry.md` entries are current evidence. Do not auto-commit them.

---

## 5. claude-mem usage rule

- Use `claude-mem` only for historical context, prior bugs, failed attempts, and recurrence patterns.
- Use `search` → `timeline` → `get_observations` workflow.
- Never treat claude-mem as current lane truth.
- Record milestones at session start, green checkpoints, and blockers.

---

## 6. Allowed actions

- Read source, docs, and git history
- Edit files inside the scope approved by the user
- Run `pytest tests/` for validation
- Run `pio run -e <env>` **only via `scripts/agent/pio-build.sh <env>`** (the wrapper rejects upload/flash/monitor tokens and limits envs to `k1_hardware`, `k1_bench_reference`, `k1_bench_im73d`)
- Commit green checkpoints on feature/wip branches (pre-commit gate enforced)
- Use `scripts/hooks/wip-checkpoint.sh` for broken-work checkpoints
- Delegate to subagents with a written consumption contract
- Add `claude-mem` observations

## 7. Forbidden actions

- Edit firmware source unless explicitly scoped
- Change `platformio.ini` default envs or build behavior unless explicitly scoped
- Flash, upload, erase flash, or open a serial monitor without explicit approval
- Run `start_noise_cal` without the user confirming a silence window
- Auto-commit dirty `device-build-registry.md` or other governance docs
- Edit files outside the approved scope
- Install new MCPs, plugins, packages, or global tools
- Create large frameworks or task bureaucracy
- Treat stale handoff docs as current truth
- Run `pio run --target upload` without verifying the target via `k1_upload_guard.py`

---

## 8. Firmware safety / upload prohibition

Hardware writes are gated. `scripts/platformio/k1_upload_guard.py` matches the build env to the USB serial / chip ID before any upload. Even if the guard passes, you must get explicit user approval before:

- `pio run --target upload`
- `pio device monitor`
- `erase_flash`
- any serial command that writes to a device

Bench K1 (`B489A500`) is the only valid target for `k1_bench_im73d`.
Main K1 (`F887A500`) is the only valid target for `k1_hardware`.

---

## 9. Validation gate expectations

Before any non-`wip/*` commit:

1. `pytest tests/` must pass
2. `bash scripts/agent/pio-build.sh k1_hardware` must be clean for firmware source changes
3. The pre-commit hook runs automatically
4. For IM73D changes, `bash scripts/agent/pio-build.sh k1_bench_im73d` must also be clean

For visual-only changes, host-green is sufficient; device eyes-on is a tracked non-blocking follow-up.

---

## 10. Handoff / report template

End every session with:

```text
## Session Handoff

### Files changed
- file1: reason

### Commands run
- command: result

### Validation
- pytest: pass/fail
- build: pass/fail

### Evidence
- paths to logs / manifests / captures

### Blockers
- none, or specific unresolved issue

### Next step
- exact recommended action
```

---

## 11. Failure-report template

If a gate or build fails, capture:

```text
## Failure Report

### Symptom
- one-line summary

### Repro
- command that failed

### Error output
- relevant excerpt

### Git state
- branch / HEAD / dirty files

### Hypothesis
- most likely cause

### Next action
- narrow investigation or fix
```

---

Last updated: 2026-07-02
