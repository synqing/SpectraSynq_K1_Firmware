---
abstract: "The SensoryBridge commit gate: how agents commit CONTINUALLY but only AFTER work is verified. Two mechanisms, not one — crash-safety checkpoints (wip/* branches, ungated) vs milestone commits (feature branch, gated). Documents the tiered hard-block pre-commit hook (docs→none, tests→pytest, firmware→pytest+pio build), the binary/oversize guard, the wip convention, the non-blocking visual-eyes-on flag, install/bypass, and the cadence rule. Read before changing commit flow or the hook."
created: "2026-06-03"
status: "active"
---

# The commit gate — "commit continually, but only when it works"

The apparent contradiction (*commit constantly* vs *never commit broken work*)
dissolves once you stop using one mechanism for two needs.

| Need | Trigger | May be broken? | Goes to | Gated? |
|---|---|---|---|---|
| **Checkpoint** (don't lose work) | time / context limit | **yes** | `wip/<lane>` branch (or `git stash`, or a `.wip` file) | **no** |
| **Milestone** (this works) | a green gate | **no** | the feature branch | **yes** |

So: *checkpoint freely to a scratch lane; promote to a real commit only on green.*

## What "works" means — tiered by what you staged

The gate runs the **real** check for the change-class and **hard-blocks** on
failure (a self-asserted "I verified it" is not accepted — the build/tests run).
The common path stays fast so the gate is never worth routing around.

| Staged paths | Gate |
|---|---|
| docs / `*.md` / `.claude/**` / `AGENTS.md` / skills / hooks | **none** (instant) |
| `tests/*.py`, `scripts/regression-harness/*.py` | `pytest tests/` |
| `SPECTRASYNQ_K1_FIRMWARE/**` source, `platformio.ini` | `pytest tests/` **then** `pio run -e k1_hardware` |
| `sb-tab5-wireless-controller/**`, Tab5 harness/tools | `pytest tests/` **then** `pio run -d sb-tab5-wireless-controller -e tab5` |
| Tab5 on `main` or `substrate/tab5-*` | above **plus** `python tools/k1_tab5_release_gate.py` |
| any tier | staged blob is rejected if it is a denylisted binary or > 10 MB |
| on a `wip/*` branch | build+test **skipped** (binary guard still applies) |

Most stringent tier wins (firmware beats docs in a mixed commit). The gate runs
the build/test against your **working tree** — stage what you build.

## compile ≠ runtime proof — but only where it matters

Most changes (logic, refactors, AP plumbing, harness, docs) are fully closed by
the host gate above — no human review needed. A *narrow* set of **visual /
perceptual** changes (`light_mode_*`, `leds`, `lightshow`, `palette`,
`render_params`, `chroma`) still need Captain's on-device eyes-on. For those the
gate **does not block** — it prints a reminder that the commit records *host
proof only* and an on-device review is queued. The commit is honest; the device
proof is a tracked follow-up, never a blocker on the cadence.

## The cadence (the "continually" half)

Commit at **every green checkpoint** — after each sub-task whose gate passes,
not at end-of-session. Default to smaller, more frequent commits. The hook
guarantees each one is green; frequent green commits + `git push` = the branch
is always backed up off-machine.

## Install / use / bypass

```bash
scripts/hooks/install.sh          # one-time per clone (sets core.hooksPath)
scripts/hooks/wip-checkpoint.sh   # durable crash-safety checkpoint on wip/*
git commit --no-verify ...        # explicit, owner-chosen WIP escape (skips gate)
git config --unset core.hooksPath # uninstall
```

`--no-verify` is the sanctioned escape for genuine WIP — keep it on `wip/*`
branches so the clean lanes stay green.

## Why these choices (so future maintainers don't "simplify" them away)

- **Hard-block, not warn.** A warn-only gate is just the prose that already
  existed in `AGENTS.md`; it does not change behaviour. Enforcement must be
  mechanical or it drifts.
- **Fast docs path.** A heavy gate on every commit gets bypassed with
  `--no-verify` until it atrophies (Shifting-the-Burden). Docs commits cost ~0s.
- **Fail-closed.** If `pio`/`pytest` is missing on a tier that needs it, the
  commit is refused (can't verify ⇒ can't claim it works), with a wip/ escape.
- **Baseline must be green first.** The gate was landed only after the suite was
  restored to 96/96 + clean build — a gate on a red suite blocks everything
  (amend-broken-gates rule).
- **Branch-aware.** `wip/*` is the pressure valve that makes "commit constantly"
  safe without weakening "only when it works" on the real branches.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-03 | agent:claude-opus | Created — full commit-gate structure: two-mechanism model, tiers, visual-eyes-on flag, install/bypass, rationale. |
