# program.md — Tempo Winner-Selection Loop (K1)

> This is the loop's constitution. The runner (`tempo_loop.py`) reads it; the proposing agent is handed it every cycle. It is the equivalent of Karpathy's `program.md`.

## Goal
Improve K1 tempo tracking on real music by editing **only the winner-selection** logic, measured by the untouchable host harness. Target: raise **in-range Acc1** and **mean locked-fraction** without regressing what already works.

## The objective gate (the agent may NOT weaken this)
- Evaluator: `python3 scripts/regression-harness/tempo_accuracy.py` → writes `docs/measurements/tempo-octave-baseline.md`.
- Metrics parsed from that file each cycle:
  - **Acc1 (in-range)** — primary.
  - **Mean locked-fraction** — secondary (the felt-quality metric; currently the real gap).
- Ground truth = HarmonixSet gold human BPM. **The agent may not touch the harness, the dataset, or the ground truth.**

## What the agent MAY edit
- `SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp` — the winner-selection path only:
  - `k1_update_tempo` (the quartic winner-exaggeration),
  - `k1_compute_acf_salience` (harmonic-comb salience),
  - the selection scoring / lobe handling.

## What the agent MUST NOT touch (hard constraints)
- `scripts/regression-harness/**` (the evaluator) and the HarmonixSet dataset / gold GT.
- **Onset** and **chord/chroma** code — they work (98.4% chord conf); out of scope.
- The **tactus prior** constants (`K1_TACTUS_BPM=88`, `K1_TACTUS_SIGMA=0.75`) — already swept to a documented robustness plateau; re-tuning them is a dead lever. Do not nudge them.
- The **confidence** prior (separate from selection on purpose).
- Anything in the render path / AGC / protected dirs.

## Keep / rollback rule
KEEP the change (commit in the worktree) only if ALL hold:
1. Build compiles (host replay compiles clean).
2. **Acc1 (in-range) improved**, OR Acc1 equal AND **mean locked-fraction improved**.
3. **No regression on the 100–120 BPM bucket** (currently ~89% — the guardrail bucket).
4. (If enabled) the pytest gate stays green.
Otherwise ROLL BACK (`git checkout -- <file>`).

## Stop conditions (two exits)
- **Goal met:** Acc1 in-range ≥ target (default 75%) AND mean locked-fraction ≥ target (default 60%).
- **Hard cap:** N iterations reached (default 25) OR wall-clock cap OR spend cap. Then STOP and report.

## Isolation & review
- The loop runs in a **throwaway git worktree**, never on the canonical branch.
- Nothing merges to canonical without **Captain review of the diff**. The loop proposes; the human merges.

## The known lever (context for the agent)
The novelty is sound; the winner-selection is the bottleneck. Failure is dominated by **low-bin pinning** (sub-harmonic wins). The comb + sub-lag interpolation are already committed. Open lane: **human-phrased 120–140 BPM material** (pop/funk/hip-hop), where lock-fraction is weakest — four-on-the-floor already locks well. Explore selection changes that break low-bin pinning on syncopated/weak-transient material **without** re-tuning the (frozen) tactus prior.

## Log
Every cycle appends to `state.md`: iteration, change summary, Acc1_inr before→after, locked-frac before→after, 100–120 bucket, KEEP/ROLLBACK, reason.
