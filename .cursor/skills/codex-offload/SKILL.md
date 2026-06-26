---
name: codex-offload
description: >
  How to offload work to the OpenAI Codex CLI (`codex exec`) correctly — to spare the Claude
  token pool AND the Claude context window. Encodes the four gotchas that cost a full session of
  failed launches: the stdin hang (`< /dev/null`), context overflow on broad tasks (decompose +
  read-budget), the workspace-write sandbox (can't touch device/network/outside-repo → a codex
  "build RED" is NOT proof the code is broken; it can't flash; it can't commit), and the
  consume-tight pattern (write-to-disk + tight final message; never read the big run log into
  your own context). Invoke BEFORE dispatching anything to `codex exec`, or when a codex run
  hangs / overflows / reports a build failure. British English.
---

# Codex Offload — using `codex exec` without losing a session to its gotchas

Codex runs on the founder's near-unlimited OpenAI tokens, **separate** from the Claude 5-hour pool. Route heavy *reading / archaeology / drafting* to Codex to spare both your token budget and your context window. But Codex's sandbox cannot touch the device, the network, or anything outside the repo — so the division of labour (§5) is fixed. A codex offload is a knowledge-transfer surface, so `load-bearing-edges` applies: declare the bounded reads, and re-validate codex's results in the real environment.

## 0 · When to invoke
- before dispatching any task to `codex exec`;
- when a codex run hangs, overflows, or reports a build/test failure;
- when deciding what to route to Codex vs keep on Claude.

## 1 · The invocation (copy this)
```
codex exec -s workspace-write --skip-git-repo-check -C "<repo-abs-path>" \
  -o /tmp/codex_<task>_last.txt \
  "<bounded inline brief — see §3>" \
  < /dev/null > /tmp/codex_<task>_run.log 2>&1
```
Run it `run_in_background`. The `< /dev/null` is non-negotiable (§2.1).

## 2 · The four gotchas (each cost real time)
**2.1 stdin hang.** A backgrounded `codex exec "PROMPT"` prints `Reading additional input from stdin...` and BLOCKS forever (no EOF). → always `< /dev/null`. Tell: process alive, log frozen on that line, zero work done.
**2.2 context overflow on broad tasks.** A "read the whole architecture + implement + validate" task hit `context_length_exceeded` at ~249k tokens and its auto-compact ALSO failed → total loss. → (a) **decompose** (spec → implement → validate as separate runs); (b) put an explicit **READ-BUDGET** in the brief ("read ONLY these files / these line-ranges; do NOT explore; use `sed -n 'A,Bp'` for excerpts"). A self-contained spec lets the implement run skip re-reading the source.
**2.3 the workspace-write sandbox** (`-s workspace-write -C <repo>`: writes only inside the repo + `/tmp`, reads broadly). Design around all three consequences:
- **can't write `/dev/tty.*`** → codex CANNOT flash/erase/serial a device. Treat this as a *safety feature*; keep device ops on Claude (MAC-verified).
- **no network / platform cache** → `pio` platform/lib downloads fail → **a codex `pio run` going RED is the sandbox, not your code.** Re-verify the build in the real Claude env (which has network) before believing a failure. (Same for `pytest` when a dep like `pyserial` is missing in-sandbox.)
- **can't write outside the repo** → `.git/index` blocked (no commits), and `~/.claude/skills/`, `$HOME`, sibling repos are read-only. → codex writes deliverables as **in-repo files**; the orchestrator (unsandboxed) does commits + global-skill edits.
**2.4 can't commit** (`.git/index.lock: Operation not permitted`). → tell codex NOT to commit ("leave files on disk"); orchestrator commits after review. Clear a stale `.git/index.lock` first if a prior codex was killed mid-git.

## 3 · The brief (what goes in the prompt)
- the goal + the **bounded read list** (§2.2) + "do not explore, do not wait for stdin";
- **WRITE the deliverable to a named in-repo file** (not stdout);
- guardrails (read-only where required; no commit; no flash; no main-rate change for firmware);
- "if you cannot do X, report it honestly — do not fabricate";
- a **final message of ≤N lines** — the only thing the orchestrator will read.

## 4 · Consuming the result without blowing YOUR context
- read ONLY `/tmp/codex_<task>_last.txt` (the `-o` final message) — small;
- confirm the on-disk deliverable (`ls`, headings grep);
- `grep -E "context_length_exceeded|ERROR" /tmp/codex_<task>_run.log` (bounded) — did it finish or overflow?
- **never `Read`/`cat` the full run log** — it is the streaming transcript and will overflow your window;
- re-verify any codex BUILD/RESULT in the real env (§2.3) before trusting it.

## 5 · Division of labour (budget-aware orchestration)
| Codex — his tokens, sandboxed | Claude — your pool, real env |
|---|---|
| bounded reading, archaeology, drafting, in-repo docs, offline host code it can run | device flash/erase/serial (MAC-verified), **build verification** (needs network), **commits**, **global-skill edits**, the final synthesis/judgement |
Route heavy reading to Codex to spare the Claude 5-hour pool **and** your context. When your CONTEXT is the binding constraint: prefer write-to-disk + tight-verdict, and treat the current big task as the **last before `/compact`**.

## 6 · Pre-flight gate
```
To Codex? (heavy bounded reading/drafting; no device/network/commit needed): yes/no
Reads bounded + declared: <files/line-ranges>     Decomposed if broad: <runs>
< /dev/null: yes    Writes in-repo deliverable: <path>    No-commit / no-flash: yes
Final message <=N lines: yes    Will re-verify any build/result in real env: yes
```

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-04 | agent:orchestrator | Created — distilled from a session of codex offloads: the stdin-hang, context-overflow, workspace-write-sandbox (no device/network/outside-repo; build-RED≠broken; no flash; no commit), and consume-tight patterns; folds the budget-aware division of labour. Companion to load-bearing-edges. Promotion-worthy to ~/.claude/skills/. |
