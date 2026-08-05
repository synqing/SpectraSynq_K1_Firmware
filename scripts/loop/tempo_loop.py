#!/usr/bin/env python3
"""Tempo Winner-Selection Loop (K1) — a Karpathy-style loop with a real, untouchable gate.

Loop: propose a winner-selection change -> run the host harness -> parse Acc1/lock ->
keep (commit in worktree) or roll back -> log to state.md -> repeat until target or cap.

The evaluator (tempo_accuracy.py + gold GT) is NEVER edited by the loop.
Runs in a throwaway git worktree; nothing merges to canonical without human review.

Modes:
  --dry-run   measure the CURRENT tree once, parse metrics, print. No agent, no spend, no edits.
  --manual    each cycle: print the brief, PAUSE for a human/other agent to edit k1_tempo.cpp,
              then measure + keep/rollback. No token spend by this script.
  (default)   auto: call the agent CLI (AGENT_CMD, default `claude -p`) to make the edit.

Read program.md next to this file for the constraints handed to the agent every cycle.
"""
from __future__ import annotations
import argparse, os, re, subprocess, sys, datetime, shutil, textwrap

# ---- Config (edit paths if the repo moves) ------------------------------------------
REPO       = os.environ.get("K1_REPO", "/Users/spectrasynq/SpectraSynq_K1_Firmware")
HARNESS    = "python3 scripts/regression-harness/tempo_accuracy.py"
REPORT_MD  = "docs/measurements/tempo-octave-baseline.md"        # harness writes this
EDIT_FILE  = "SPECTRASYNQ_K1_FIRMWARE/audio/k1_tempo.cpp"        # agent-editable surface
PYTEST_GATE= os.environ.get("K1_PYTEST", "")                     # e.g. "python3 -m pytest -q" ("" = skip)
AGENT_CMD  = os.environ.get("AGENT_CMD", "claude -p")            # headless agent invocation

TARGET_ACC1_INR = float(os.environ.get("TARGET_ACC1", "75"))    # %
TARGET_LOCK     = float(os.environ.get("TARGET_LOCK", "60"))    # %
GUARD_BUCKET    = "100-120"                                      # must not regress

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAM = open(os.path.join(HERE, "program.md")).read() if os.path.exists(os.path.join(HERE, "program.md")) else ""

def sh(cmd, cwd, check=True, capture=True):
    r = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), text=True,
                       capture_output=capture)
    if check and r.returncode != 0:
        raise RuntimeError(f"cmd failed ({r.returncode}): {cmd}\n{r.stderr}")
    return r

# ---- Metric parsing from the harness's markdown report ------------------------------
def parse_metrics(md_text: str) -> dict:
    def grab(pat, default=None):
        m = re.search(pat, md_text)
        return float(m.group(1)) if m else default
    acc1_inr = grab(r"\*\*Acc1\*\*[^|]*\|[^|]*\|\s*\*\*([\d.]+)%")          # bold in-range col
    lock     = grab(r"[Mm]ean locked-fraction[^:]*:\s*([\d.]+)%")
    # guard bucket row:  | 100-120 | n | Acc1% | Acc2% | gap% |
    gb = re.search(r"\|\s*" + re.escape(GUARD_BUCKET) + r"\s*\|[^|]*\|\s*([\d.]+)%", md_text)
    guard = float(gb.group(1)) if gb else None
    return {"acc1_inr": acc1_inr, "lock": lock, "guard": guard}

def measure(cwd) -> dict:
    sh(HARNESS, cwd=cwd)                                   # regenerates REPORT_MD
    md = open(os.path.join(cwd, REPORT_MD)).read()
    m = parse_metrics(md)
    if m["acc1_inr"] is None:
        raise RuntimeError("could not parse Acc1(in-range) from " + REPORT_MD)
    return m

def better(new, base) -> bool:
    # keep rule: Acc1_inr up, or equal-and-lock-up; and no guard-bucket regression
    if base["guard"] is not None and new["guard"] is not None and new["guard"] + 1e-9 < base["guard"]:
        return False
    if new["acc1_inr"] > base["acc1_inr"] + 1e-9:
        return True
    if abs(new["acc1_inr"] - base["acc1_inr"]) <= 1e-9 and (new["lock"] or 0) > (base["lock"] or 0) + 1e-9:
        return True
    return False

def met_target(m) -> bool:
    return (m["acc1_inr"] >= TARGET_ACC1_INR) and ((m["lock"] or 0) >= TARGET_LOCK)

# ---- Worktree ------------------------------------------------------------------------
def make_worktree() -> str:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    wt = os.path.expanduser(f"~/.claude-worktrees/tempo-loop-{stamp}")
    branch = f"tempo-loop/{stamp}"
    sh(f"git worktree add -b {branch} '{wt}' HEAD", cwd=REPO)
    return wt

# ---- Agent step (the one env-specific hook) -----------------------------------------
def propose_change(wt, state_text, metrics, manual: bool):
    brief = textwrap.dedent(f"""\
        You are in a tempo winner-selection improvement loop. Read program.md (below) and obey it EXACTLY.
        Make ONE focused change to {EDIT_FILE} (winner-selection only). Do not touch the harness,
        the tactus/confidence priors, onset, or chord. Do not explain — just edit the file.

        Current metrics: Acc1(in-range)={metrics['acc1_inr']}%  lock={metrics['lock']}%  {GUARD_BUCKET}-bucket={metrics['guard']}%
        Target: Acc1(in-range) >= {TARGET_ACC1_INR}%, lock >= {TARGET_LOCK}%.

        --- program.md ---
        {PROGRAM}
        --- recent state ---
        {state_text[-2000:]}
        """)
    if manual:
        print("\n" + "="*70 + "\nMANUAL STEP — make ONE winner-selection edit in the worktree, then press Enter.")
        print(f"  worktree: {wt}\n  file:     {EDIT_FILE}\n" + "="*70)
        print(brief)
        input("Press Enter when the edit is saved... ")
        return
    # auto: hand the brief to the agent CLI, working dir = worktree
    cmd = f'{AGENT_CMD} {subprocess.list2cmdline([brief])}'
    print(f"  [auto] invoking agent: {AGENT_CMD} (cwd={wt})")
    sh(cmd, cwd=wt, check=False)   # agent edits EDIT_FILE in place

# ---- State ---------------------------------------------------------------------------
def log_state(wt, line):
    p = os.path.join(wt, "state.md")
    with open(p, "a") as f:
        f.write(line + "\n")

# ---- Main ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="K1 tempo winner-selection loop")
    ap.add_argument("--max-iters", type=int, default=int(os.environ.get("MAX_ITERS", "25")))
    ap.add_argument("--dry-run", action="store_true", help="measure current tree once, parse, print, exit")
    ap.add_argument("--manual", action="store_true", help="pause for a human/other agent to make each edit")
    args = ap.parse_args()

    if args.dry_run:
        print("DRY RUN — measuring current tree (no worktree, no agent, no spend)...")
        m = measure(REPO)
        print(f"  Acc1(in-range) = {m['acc1_inr']}%   lock = {m['lock']}%   {GUARD_BUCKET}-bucket = {m['guard']}%")
        print(f"  target: Acc1>={TARGET_ACC1_INR}%  lock>={TARGET_LOCK}%  -> {'MET' if met_target(m) else 'not met'}")
        return

    wt = make_worktree()
    print(f"worktree: {wt}")
    base = measure(wt)
    log_state(wt, f"# Tempo loop  (target Acc1_inr>={TARGET_ACC1_INR}% lock>={TARGET_LOCK}%)\n"
                  f"baseline: Acc1_inr={base['acc1_inr']}% lock={base['lock']}% {GUARD_BUCKET}={base['guard']}%")
    print(f"baseline: Acc1_inr={base['acc1_inr']}% lock={base['lock']}%")

    for i in range(1, args.max_iters + 1):
        print(f"\n--- iteration {i}/{args.max_iters} ---")
        state_text = open(os.path.join(wt, "state.md")).read()
        propose_change(wt, state_text, base, manual=args.manual)
        # compile+measure via harness; if it fails to compile, roll back
        try:
            new = measure(wt)
        except Exception as e:
            print(f"  measure/compile failed -> ROLLBACK ({e})")
            sh(f"git checkout -- '{EDIT_FILE}'", cwd=wt, check=False)
            log_state(wt, f"- iter {i}: COMPILE/MEASURE FAIL -> rollback")
            continue
        gate_ok = True
        if PYTEST_GATE:
            gate_ok = sh(PYTEST_GATE, cwd=wt, check=False).returncode == 0
        keep = gate_ok and better(new, base)
        if keep:
            msg = "tempo loop iter {}: Acc1_inr {}->{} lock {}->{}".format(
                i, base["acc1_inr"], new["acc1_inr"], base["lock"], new["lock"])
            sh(["git", "add", "-A"], cwd=wt, check=False)
            sh(["git", "commit", "-q", "-m", msg], cwd=wt, check=False)
            log_state(wt, f"- iter {i}: KEEP  Acc1_inr {base['acc1_inr']}->{new['acc1_inr']}%  lock {base['lock']}->{new['lock']}%  {GUARD_BUCKET}={new['guard']}%")
            print(f"  KEEP  Acc1_inr {base['acc1_inr']}->{new['acc1_inr']}%  lock {base['lock']}->{new['lock']}%")
            base = new
        else:
            sh(f"git checkout -- '{EDIT_FILE}'", cwd=wt, check=False)
            log_state(wt, f"- iter {i}: ROLLBACK  (gate_ok={gate_ok})  Acc1_inr={new['acc1_inr']}% lock={new['lock']}% {GUARD_BUCKET}={new['guard']}%")
            print(f"  ROLLBACK  (no improvement or guard/gate failed)")
        if met_target(base):
            print(f"\nTARGET MET at iter {i}: Acc1_inr={base['acc1_inr']}% lock={base['lock']}%")
            break

    print(f"\nDONE. Best: Acc1_inr={base['acc1_inr']}% lock={base['lock']}%")
    print(f"Review the diff in the worktree, then merge to canonical ONLY after Captain review:\n  {wt}")
    print(f"State log: {os.path.join(wt, 'state.md')}")

if __name__ == "__main__":
    main()
