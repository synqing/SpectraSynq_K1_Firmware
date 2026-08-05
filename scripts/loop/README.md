# Tempo Winner-Selection Loop

A Karpathy-style loop applied to the K1's one open DSP gap. The agent edits winner-selection; the untouchable harness scores it; keep-or-rollback on the metric; repeat until target or cap. Runs in a throwaway worktree — **nothing merges without your review.**

## Files
- `program.md` — the loop's constitution (goal, editable surface, hard constraints, keep/rollback rule, stop conditions). The agent gets this every cycle.
- `tempo_loop.py` — the runner (worktree, measure, parse, keep/rollback, state log, stop).

## Install
Drop both into `SpectraSynq_K1_Firmware/scripts/loop/` (or run from anywhere; it uses absolute repo paths / `K1_REPO`).

## Use it safely — in this order
1. **Prove the plumbing first (no spend, no edits):**
   ```bash
   python3 scripts/loop/tempo_loop.py --dry-run
   ```
   Runs the harness once, parses Acc1(in-range) + lock-fraction + the 100–120 guard bucket, prints them vs target. If this prints sane numbers, the gate wiring is correct.
2. **Human-in-the-loop first run (still no script spend):**
   ```bash
   python3 scripts/loop/tempo_loop.py --manual --max-iters 5
   ```
   Each cycle it opens a worktree, prints the brief, and pauses for **you** (or a separate Claude/Codex window) to make one winner-selection edit, then measures + keeps/rolls-back. This is the safest way to feel the loop and confirm keep/rollback behaves before spending on autonomous cycles.
3. **Autonomous (spends tokens):**
   ```bash
   AGENT_CMD="claude -p" MAX_ITERS=25 python3 scripts/loop/tempo_loop.py
   ```
   Calls the agent CLI to make each edit. **The `AGENT_CMD` invocation is the one env-specific hook** — adjust flags for your claude-code / codex version so it can `Edit` `k1_tempo.cpp` non-interactively in the worktree. Start with a low `--max-iters`.

## Config (env overrides)
`K1_REPO`, `TARGET_ACC1` (default 75), `TARGET_LOCK` (default 60), `MAX_ITERS` (default 25), `K1_PYTEST` (e.g. `python3 -m pytest -q` to add the test gate; empty = skip), `AGENT_CMD`.

## Guardrails baked in
- **Untouchable gate:** the loop never edits `tempo_accuracy.py` or the gold GT.
- **Frozen levers:** `program.md` forbids re-tuning the tactus prior (documented plateau) and touching onset/chord.
- **No regression:** a change is kept only if Acc1(in-range) improves (or lock improves at equal Acc1) AND the 100–120 bucket doesn't drop.
- **Isolation:** all work in `~/.claude-worktrees/tempo-loop-<ts>`; canonical is untouched until you merge.
- **Two exits:** target met, or `--max-iters` cap.

## The honest reminders (from the loop-engineering skill)
- **Review the kept diffs.** This is real-time render-adjacent firmware — don't let it ship code you haven't read (comprehension debt).
- **Reap it.** When the loop ends, the worktree and any agent subprocesses should be cleaned up — undisciplined loops are exactly the MCP/process sprawl we're mid-fixing.
- Device validation stays human/hardware-gated; this loop optimises the **host-replay** metric only.
