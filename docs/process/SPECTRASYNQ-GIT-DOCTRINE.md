---
abstract: "SpectraSynq global git doctrine (ratified 2026-08-06). Separates recording (commit), integrating (merge), and endorsing (verification claims) so unverified work is always recorded and never falsely blessed. Six rules, the Verify: trailer contract, the agent session protocol stanza, minimal enforcement (commit-msg hook + session-end script), and per-repo adoption state. Applies to every SpectraSynq repo. Do not harden, do not extend without Captain ratification."
---

# SpectraSynq Git Doctrine

**Ratified by Captain, 2026-08-06:** main merges on host-gates only · lane
branches push at session end · enforcement design delegated to the agent
(delivered as: AGENTS.md stanza + commit-msg hook + session-end script,
nothing more) · **the doctrine is GLOBAL** — an identical copy lives at
`docs/process/SPECTRASYNQ-GIT-DOCTRINE.md` in every SpectraSynq repo, and
hook enforcement is installed machine-wide, not per-repo.

## The model in one paragraph

A commit is a **record**, not an endorsement. A merge to main is an
**integration**, gated by machine-runnable host gates. A verification claim
is an **endorsement**, and it lives in evidence (trailer + receipt), never in
vibes. The historical failure modes both came from fusing these: auto-commit
fused record with endorsement (unverified code looked blessed), and the
ban-until-verified reaction fused record with verification (weeks of
unrecorded work, 258-file dirty trees, half-hour merge sessions). Separated,
both disappear: careless agents' early commits are harmless — quarantined on
lanes and honestly labelled — and fastidious agents lose nothing.

## The six rules

1. **Recording is unconditional.** Every session ends with a clean tree:
   everything committed on that session's lane branch. WIP commits are legal
   and expected. Unrecorded work is the worst outcome git can have — a bad
   commit reverts in seconds; a clobbered dirty tree is gone.

2. **Truth-in-claims.** Every commit carries one trailer:
   `Verify: none | host | device:<chip>@<receipt>`. Claim words
   ("device-proven", "field-tested", "glass-pass") are forbidden in any
   commit whose trailer is not `device:` with a receipt anchor. Ban the
   claim, never the record.

3. **Integration is gated, not delayed.** `main` requires host-gate green
   only (build + unit/static gates — minutes, any agent, any machine).
   Device/field proof is deliberately NOT a merge requirement: it is
   recorded post-merge as a registry row (K1:
   `docs/hardware/device-build-registry.md`; other repos: their equivalent)
   and optionally an annotated tag `proof/<env>/<yyyymmdd>` pointing at the
   SHA. Integrate on host-gate cadence (hours–days), never field-test
   cadence (weeks) — merge conflict cost is a batch-size symptom.

4. **One lane = one branch = one worktree.** Parallel agents never share a
   dirty tree. Branch naming stays free (`lane/*`, `feat/*`, `fix/*`);
   what is doctrine is one branch per lane and a separate worktree per
   concurrently active lane. Composes with agent-mail file reservations.

5. **Session protocol** — the stanza below goes verbatim into each repo's
   AGENTS.md / CLAUDE.md.

6. **Every repo has a remote; lane branches push at session end.** Backup,
   cross-machine continuity, and the uncommitted-pile failure mode becomes
   visible the day it starts.

## The `Verify:` trailer contract

| Trailer | Meaning |
|---|---|
| `Verify: none` | Recorded, unendorsed. WIP, unbuilt, or untested. Always legal on a lane. |
| `Verify: host` | Host gates green (state which in the body when non-obvious: pytest suites, static gates, `pio run -e <env>`). Merge-eligible. |
| `Verify: device:B489A500@docs/hardware/<receipt>.md` | On-silicon proof with a receipt anchor (doc, registry row, or evidence bundle path). The only trailer that may accompany claim words. |

Merges/reverts/fixups are exempt (the hook skips them).

## AGENTS.md stanza (copy verbatim into each repo)

```markdown
### Git session protocol (SpectraSynq doctrine — do not harden, do not skip)
1. START: `git status` must be clean. If it is not, your first task is
   triage, not new work.
2. WORK: commit on the lane branch at every gate-pass or coherent
   checkpoint. Conventional prefix + `Verify:` trailer
   (`none` | `host` | `device:<chip>@<receipt>`).
3. CLAIMS: never write "device-proven" / "field-tested" / "glass-pass" in a
   commit without `Verify: device:<chip>@<receipt>`.
4. END: commit EVERYTHING (WIP is legal, `Verify: none`), push the lane to
   origin (`scripts/git_session_end.sh "<msg>" [trailer]`), update the
   handoff. A session that ends with a dirty tree is a failed session,
   regardless of what it built.
5. MERGE to main only with host gates green. Device proof is recorded
   post-merge (registry row / `proof/` tag), never required for merge.
```

## Enforcement (complete list — nothing else is authorised)

- **`.githooks/commit-msg`** — rejects a commit missing a well-formed
  `Verify:` trailer, and rejects device-claim words without a `device:`
  trailer. Deterministic, offline, ~25 lines.
- **`scripts/git_session_end.sh`** — stages all, commits with the trailer,
  pushes the lane. Refuses to run on main/master. Makes rule 1 the lazy path.

**Global install (preferred — run ONCE per dev machine, real terminal):**

```bash
bash scripts/setup_global_git.sh
```

This copies the hook to `~/.config/git/hooks/` and sets
`git config --global core.hooksPath` there, so the trailer contract binds
**every repo on the machine — present and future — with zero per-repo
adoption**. Caveat: a repo that sets its own *local* `core.hooksPath`
(e.g. a husky-managed web project) overrides the global one for that repo —
that is correct behaviour, leave it be.

**Per-repo fallback** (machines without the global install, or collaborators):

```bash
git config core.hooksPath .githooks && chmod +x .githooks/commit-msg scripts/git_session_end.sh
```

**Agent-manual routing:** the session-protocol stanza belongs in the GLOBAL
agent manual (`~/.claude/CLAUDE.md`) once, so every session in every repo
inherits it; per-repo AGENTS.md copies are reinforcement, not the source of
truth.

Agents: this doctrine is intentionally minimal. Proposing additional gates,
CI ceremony, branch-protection schemes, or "hardening" of this file without
Captain ratification is itself a doctrine violation.

## Per-repo adoption state (2026-08-06 audit)

All four connected repos carry identical copies of this doc, the hook, the
session-end script, and the global installer (2026-08-06).

| Repo | State | Owed |
|---|---|---|
| SpectraSynq_K1_Firmware | Git + GitHub remote. **258 uncommitted changes at audit time.** Doctrine files present. | Run global installer once; stanza into `~/.claude/CLAUDE.md` + AGENTS.md; triage the pile into coherent lane commits (2026-06-01 classification doc is the template) — deferred by Captain, owed. |
| Universal-SMC-Mixer | Git, clean tree. Remote `origin` set to `https://github.com/synqing/Universal-SMC-Mixer.git` (local config only). Doctrine files present. | Create the GitHub repo + first push (needs network/credentials on the Mac). |
| tab5-encoder | **Not a git repo** (`.gitignore` present, no `.git`). Doctrine files present, inert until init. | `git init` + first commit + remote — deferred by Captain, owed before any further firmware work there. Global hook binds it automatically the moment it is a repo. |
| JC3636K518CN_knob_EN-bleremote | Worktree of `../JC3636K518CN_knob_EN` (parent outside audited scope; docs say tracked, `master @ 8d998cc`). Doctrine files present. | Verify parent repo health + remote. |

## Non-goals

No PR ceremony for solo-plus-agents work. No CI-service mandate (host gates
are local and sufficient). No rebase religion — rebase a lane onto main
before merging when divergence is small; never force-push main; delete
merged lanes. Nothing in this doctrine requires network access at commit
time.
