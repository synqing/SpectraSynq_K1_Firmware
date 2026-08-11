---
abstract: "SpectraSynq global housekeeping doctrine (ratified 2026-08-06). Kills the seven filesystem sins structurally: tool-layer write denial outside the invoked repo, two-zone birth rule (canonical set vs _scratch), no orphan permanent docs, quarantine-never-delete, session-end sweep, CHANGELOG bound at merge. Sibling to SPECTRASYNQ-GIT-DOCTRINE.md — the session-protocol stanza there (steps 6–8) is the behavioural surface of this law. Identical copy in every SpectraSynq repo. Do not harden, do not extend without Captain ratification."
---

# SpectraSynq Housekeeping Doctrine

**Ratified by Captain, 2026-08-06:** scratch quarantine allowed once its lane
is closed AND nothing canonical cites it · existing-litter purges scheduled
as owed supervised lanes · CHANGELOG binds at merge to main · tool-layer
write denial delegated to the agent as CTO call — **ruled: full deny list**
(no legitimate agent write to Desktop/Downloads/Documents exists in this
workflow).

## The root cause (one paragraph of record)

Litter is a ratchet, not a character flaw. Creation is cheap and happens in
context; deletion is expensive and happens out of context — a later agent
cannot cheaply tell a load-bearing receipt from expired scrap, and in an
evidence culture deleting someone else's file is correctly terrifying. So
files flow in and never out. The fix moves the lifecycle decision to
**birth** — the only moment it is cheap — via two questions every new file
must answer: *who reads this after the session ends?* (no nameable reader →
scratch) and *who deletes this?* (the creator, at session end).

## The two zones

Every repo contains exactly two kinds of file. Nothing is born ambiguous.

**Canonical set** — enumerated, updated in place, never duplicated:
`README.md`, `CHANGELOG.md`, `CLAUDE.md`, `AGENTS.md`, `LICENSE`/`NOTICE`,
build manifests (`platformio.ini` etc.), the rolling trio
(`task_plan.md`, `findings.md`, `progress.md`), the `docs/` tree with its
indexes (spec-index, device-build-registry, protocol contracts), and
committed evidence under `artifacts/`/`evidence/`. **The repo root is a
closed set** — adding a new root-level file requires Captain ratification.

**`_scratch/<lane>_<YYYYMMDD>/`** — everything session- or lane-scoped:
probe outputs, one-shot analyses, working notes, draft comparisons. Born
deletable. Single-use documentation is *legal* — here, and only here.

## The five bans and one gate

1. **No writes outside the invoked repo — ever.** (Sins 1, 3, 4.) Enforced
   mechanically, not behaviourally: the global deny list below makes the
   write fail at the tool layer. Codex agents run `workspace-write`
   sandboxed. The stanza rule is the backstop for anything the deny list
   cannot see.
2. **Two-zone birth rule.** (Sins 2, 5.) Every new file is canonical or
   `_scratch/`. A naked new `.md` anywhere else is a violation.
3. **No orphan permanents.** (Sins 2, 7.) A new canonical file requires an
   inbound reference — spec-index row, docs link, or CHANGELOG line — **in
   the same commit**. Cannot name the referencer? Then you have answered
   the reader question: it is scratch. Prefer updating an existing
   canonical file over creating a new one, always.
4. **Quarantine, never delete.** (Sin 5, without the catastrophic failure
   mode.) Agents move suspected-stale material to `_graveyard/` at the repo
   root; only Captain empties it. **Cited = protected**: any file
   referenced from the canonical set may not be touched. Cross-agent
   quarantine of `_scratch/<lane>_*` is permitted only when that lane is
   closed in the spec-index AND nothing canonical cites the material.
5. **The sweep.** (Sin 5.) Session end = the creator deletes or quarantines
   their own uncited scratch, before the session-end commit. Stanza step 8.
6. **The gate.** (Sins 6, 7.) Merging to main requires a **dated**
   CHANGELOG.md entry for any behaviour change — part of the host-gate
   checklist, alongside green gates. Lane commits stay nag-free;
   `progress.md` remains the rolling session record. Curated history at
   main, messy truth on lanes.

## Tool-layer deny list (the permanent kill)

Merge `docs/process/claude-global-deny.json` into `~/.claude/settings.json`
(`permissions.deny`). Verify the patterns render as expected with
`/permissions` on your Claude Code version — glob semantics have shifted
between releases. Home-root loose-file dumping is covered by stanza step 6
rather than the deny list, because a home-root glob that accidentally
matched recursively would block every repo; add it only after `/permissions`
confirms non-recursive semantics on your install.

## Owed purge lanes (existing litter — scheduled, not executed)

One supervised purge lane per repo: agent proposes a quarantine
classification against the canonical set, Captain rules, material moves to
`_graveyard/`, nothing is destroyed. K1's runs together with the deferred
258-file triage.

| Repo | Known litter at audit (2026-08-06) |
|---|---|
| SpectraSynq_K1_Firmware | `AGENTS.md.bak.20260715233235` (root), `light_mode_waveform_tempo.cpp.wip`, the 258-entry uncommitted pile, root `findings.md`/`progress.md` staleness unassessed |
| JC3636K518CN_knob_EN-bleremote | Four planning files + gallery snapshot doc loose at root; `build_out*` dirs unassessed |
| tab5-encoder | Unassessed (not yet a git repo — purge folds into its init lane) |
| Universal-SMC-Mixer | Clean tree at audit; verify docs currency only |

## Non-goals (via negativa applies to the doctrine itself)

No document metadata schemas, no TTL daemons, no new master indexes, no
cleanup cron jobs, no per-file frontmatter mandates beyond what repos
already use. The existing indexes ARE the index. Agents: proposing
additional housekeeping machinery, filing standards, or "hardening" of this
file without Captain ratification is itself a doctrine violation.
