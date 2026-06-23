---
abstract: "Record + rationale for the 2026-06-03 working-tree staging that split a 200+-file dirty tree on feat/gdft-harness into 7 atomic commits (31d7220..48c029a). Covers the change taxonomy, the per-commit context (problem / design / alternatives / testing / limitations), the two load-bearing decisions (gitignore 158 MB of binary evidence; leave the .cpp.wip untracked), lessons learned (decorated git-diff workaround for non-interactive hunk-splitting), and maintenance guidance. Read this to understand why the tree was committed the way it was and how to extend the runtime-evidence + handoff conventions."
evidence_tier: "source-only"
proof_boundary: "git-state + working-tree inspection only; no firmware build/upload/device action"
created: "2026-06-03"
status: "complete"
---

# Working-Tree Staging Strategy — 2026-06-03

A long-running dirty tree on `feat/gdft-harness` (3 modified tracked files +
~200 untracked files, ~175 MB) was decomposed into **7 atomic commits**, none
pushed. This document is both the historical record and the onboarding resource
for the conventions it applied.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-06-03 | agent:claude-opus | Created — full staging record: taxonomy, per-commit context, 2 load-bearing decisions, lessons, contributor guidance. |

---

## 1 · Pre-staging state

- Branch `feat/gdft-harness` @ `fccbc71` (ahead of origin, not pushed).
- **Tracked modified (3):** `.claude/CLAUDE.md`, `AGENTS.md`,
  `.claude/SESSION-HANDOFF-2026-06-02-tempo-lock.md`.
- **Untracked:** the Spec Kit toolchain (`.specify/**`, `.claude/skills/speckit-*`,
  `.agents/skills/speckit-*`, root `CLAUDE.md`); two session-handoff/forensic docs;
  one firmware `*.cpp.wip`; and a large `docs/forensics/runtime-evidence/` payload
  (logs + JSON + ~158 MB of `.mp4`/`.jpg` capture media).

`AGENTS.md` carried **two unrelated concerns** in one diff (parallel-agent
orchestration rule + a Spec Kit install note) — these had to be separated.

## 2 · Change taxonomy

| Category | Files | Commit |
|---|---|---|
| Configuration | `.gitignore` (media exclusions) | `31d7220` |
| Documentation (forensic) | orchestration timeout incident | `6780dda` |
| Governance / instructions | `.claude/CLAUDE.md` + `AGENTS.md` rule 9 | `ba03950` |
| Tooling / chore | Spec Kit toolchain + both rule-file notes + root loader | `19e0bb4` |
| Documentation (governance) | Spec Kit P0 preflight | `0514523` |
| Documentation (evidence) | Smart-Auto A/B logs + manifests | `c78af6f` |
| Documentation (handoff) | tempo-lock reconcile + VE-Auto-Loop handoff | `48c029a` |
| **Deliberately uncommitted** | `light_mode_waveform_tempo.cpp.wip` | — |
| **Deliberately git-ignored** | `*.mp4`, `*frames*/`, `capture-probe/` | (via `31d7220`) |

No firmware **source** entered any commit → **no build gate was required**. (The one
firmware artefact, the `.cpp.wip`, was excluded precisely because committing it would
have triggered the build/test gate it cannot yet pass.)

## 3 · The commit sequence (dependency-ordered)

The order is causal, not alphabetical: config that protects later steps first;
each "policy" commit preceded by the "evidence" commit that motivates it.

1. **`31d7220` `chore(gitignore)`** — exclude heavy media *first*, so no later
   `git add` can suck in 158 MB. Verified with `git check-ignore -v` (media
   matched; JSON manifests confirmed *not* ignored).
2. **`6780dda` `docs(forensics)`** — the 2026-05-29 timeout incident (the *why*).
3. **`ba03950` `docs(governance)`** — the orchestration discipline (the *rule*),
   referencing #2. Same contract added to `.claude/CLAUDE.md` (prose) and
   `AGENTS.md` (numbered rule) so it holds whichever file a surface loads.
4. **`19e0bb4` `chore(speckit)`** — the Spec Kit toolchain (the *thing*).
5. **`0514523` `docs(speckit)`** — the P0 governance preflight gating #4's use.
6. **`c78af6f` `docs(forensics)`** — Smart-Auto A/B text evidence; guarded so the
   commit aborts if any `.mp4`/`.jpg` reaches the index.
7. **`48c029a` `docs(handoff)`** — session-continuity docs.

## 4 · Per-commit context

### 4.1 `chore(gitignore)` — exclude heavy runtime-evidence media
- **Problem.** ~143 MB `.mp4` + ~15 MB frame `.jpg` were untracked-and-stageable.
- **Decision.** Ignore the media; track only text evidence. See §5.1 for the full
  decision record.
- **Alternatives considered.** (a) Commit to plain git — rejected (irreversible
  history bloat, no precedent). (b) Git LFS — viable but heavier setup; deferred,
  can be layered later without rework. (c) Leave untracked-but-visible — rejected
  (158 MB of permanent `git status` noise + accidental-`git add .` risk).
- **Limitation.** Manifests now reference local-only media paths (expected, standard).

### 4.2 `docs(forensics)` — orchestration timeout incident
- **Problem.** A SEV3 process failure (blocking forever on delegated sub-agents,
  then mis-reframing load-bearing research as optional) had no durable record.
- **Design.** House-style forensic; pairs with #3 as cause→policy.

### 4.3 `docs(governance)` — parallel-agent orchestration discipline
- **Problem.** No codified contract for dispatching/consuming parallel agents.
- **Design.** Consumption contract + load-bearing/optional classification +
  dependency barrier + stuck-agent recovery + delegation ledger.
- **Architectural impact.** Binds every orchestration surface; near-identical
  wording in two files is intentional redundancy, not drift.
- **Challenge overcome.** `AGENTS.md` mixed this with the Spec Kit note — split
  via exact-text edit (see §5.3), verified `grep -c SPECKIT == 0` in the staged
  diff before committing.

### 4.4 `chore(speckit)` — Spec Kit toolchain
- **Problem.** Manual spec workflow needed scaffolding without an autonomous runner.
- **Design / safety.** Hooks disabled (`auto_execute_hooks: false`), empty workflow
  registry, implement/taskstoissues/agent-context skills not wired; constitution
  left as upstream placeholder (tracked backlog). Root `CLAUDE.md` defers to the
  canonical `.claude/CLAUDE.md`.
- **Security consideration.** `.specify/scripts/*.sh` are vendored shell scripts —
  reviewed as inert scaffolding (not invoked by this repo's build).

### 4.5 `docs(speckit)` — P0 governance preflight
- **Problem.** Spec Kit could be misused as an implementation/automation surface.
- **Design.** Source-truth order + unsafe-surface ignore-list + dirty-tree baseline,
  as a pure documentation gate (performs no Spec Kit action).

### 4.6 `docs(forensics)` — Smart-Auto A/B runtime evidence
- **Problem.** Three A/B capture runs (firmware 40103, two K1 units) needed a
  durable record without committing the heavy media.
- **Design.** Track logs + JSON manifests (the parser-compatible source of truth);
  media stays local per §4.1.
- **Testing methodology of the captures.** Capture-only — each manifest's `notes`
  confirms no calibration/erase/upload/source-edit by the harness.
- **Known limitation / follow-up.** The `2026-06-01T212939` and `T213207` sessions
  produced **video-only** output (no text manifest) → now that media is ignored,
  they leave **no git-tracked record**. Recommend back-filling text manifests.

### 4.7 `docs(handoff)` — session continuity
- **Problem.** The tempo-lock handoff's git posture had gone stale ("nothing
  committed" → actually 3 commits @ `456153d`); the VE-Auto-Loop lane had no handoff.
- **Design.** Reconcile the stale doc; add the Lane B MVP-0 handover.

## 5 · Load-bearing decisions (the two that changed the plan)

### 5.1 Binary runtime evidence → git-ignored, not committed
- **Evidence:** zero `.mp4`/`.jpg` ever tracked vs **167** text evidence files
  already tracked under `runtime-evidence/`; a prior in-repo handoff states *"do NOT
  commit binaries"*; global binary-asset policy; ~158 MB at stake.
- **Frameworks:** *Tragedy of the Commons* (shared history is a depletable resource)
  + *Reversibility* (plain-git binary commit is Type-1/irreversible; ignore is Type-2).
- **Verdict:** track text, ignore media. Reversible; LFS remains a future option.

### 5.2 `light_mode_waveform_tempo.cpp.wip` → left untracked
- **Evidence:** it is the unwired/incomplete tempo reference impl; git discipline
  forbids committing untested/broken work; the prior handoff *deliberately* kept the
  non-`.wip` form untracked because it breaks a fresh `pio run`.
- **Verdict:** leave it untracked **and visible** (not git-ignored) so the next agent
  finds it as the build BoM. It becomes commit-worthy only when the tempo-lock lane
  builds clean (handoff §4). The `.wip` suffix already keeps it out of the
  `+<light_mode_*.cpp>` build filter.

## 6 · Lessons learned

1. **`git diff` output is decorated in this environment** (indented `@@`, summary
   header/footer) even when redirected to a file — so it is **not raw-patch-usable**
   for `git apply --cached`. Combined with interactive flags being disabled
   (`git add -p`/`-i` unavailable), the reliable way to split one file's concerns
   into separate commits is: **exact-text `Edit` to remove concern B → stage+commit
   concern A → `Edit` to restore concern B → stage+commit B.** Verified clean with a
   `git diff` round-trip (`AGENTS.md` matched committed state afterward).
2. **Guard binary commits at the index, not by trust.** The evidence commit used
   `git diff --cached --name-only | grep -Eq '\.(mp4|jpg)$'` to *abort* before
   committing — cheap insurance against an accidental binary.
3. **Order config first.** Landing the gitignore commit before any evidence `add`
   made every later staging step safe-by-construction.
4. **`git check-ignore -v` before relying on a new ignore rule** — confirm it
   matches the binaries *and* spares the text you intend to keep.

## 7 · Future-contributor guidance

- **Adding runtime evidence:** commit `.log` / `.json` / `.md`; never commit
  `.mp4`/frame `.jpg`/`capture-probe/` (already ignored). Always include a JSON
  manifest — it is the only git-tracked record of a capture run. If a run is
  video-only, write a manifest anyway (see the §4.6 follow-up).
- **If video must be versioned:** introduce Git LFS for `docs/forensics/**/*.mp4`
  rather than committing to plain git; this is additive to the current setup.
- **Splitting mixed-concern files:** use the §6.1 edit-remove/commit/edit-restore
  pattern; do not reach for `git add -p` (interactive, unavailable here).
- **The `.cpp.wip`:** do not commit until the tempo-lock lane builds clean
  (`pio run -e k1_hardware`) and the New-Light-Mode change-gate passes; see
  `.claude/SESSION-HANDOFF-2026-06-02-tempo-lock.md` §4 and `/sensorybridge-doctrine`.
- **Pushing:** `feat/gdft-harness` is ahead of origin and **was not pushed** here —
  remote push requires explicit Captain instruction (git-discipline rule).

## 8 · Pitfalls to avoid

- Do **not** `git add .` / `git add -A` in this tree — it would re-surface the
  `.cpp.wip` and (absent the ignore rules) the 158 MB of media.
- Do **not** "fix" the stale-looking media references in manifests by committing the
  media — the local-only posture is intentional.
- Do **not** treat the duplicated orchestration wording across `.claude/CLAUDE.md`
  and `AGENTS.md` as drift to dedupe — it is deliberate redundancy.
