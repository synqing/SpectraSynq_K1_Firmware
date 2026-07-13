# Agent Stack — Actionable Task Backlog

**Status:** Active backlog — Phase 0 complete, **Phase 1 exit criteria DONE** (2026-07-13; P1-08 contract debt remediated same day)  
**Parent:** [`PHASED-ROLLOUT.md`](./PHASED-ROLLOUT.md), [`AUTHORITY-CONTRACT.md`](./AUTHORITY-CONTRACT.md)  
**Phase ledger:** [`knowledge/current-priorities.md`](../../knowledge/current-priorities.md)  
**Legend:** Owner = role responsible; Dep = task IDs; Risk = H/M/L

---

## Phase 0 — Preconditions & authority contract

| ID | Task | Owner | Dep | Acceptance criteria | Risk | Status |
|----|------|-------|-----|---------------------|------|--------|
| P0-01 | Ratify `AUTHORITY-CONTRACT.md` with Captain | Captain | — | Captain sign-off recorded in `knowledge/decisions/` or PR comment | L | **DONE** |
| P0-02 | Add `docs/agent-stack/` index link from `AGENT_OS.md` (governance section) | Knowledge curator | P0-01 | PR merged; `AGENT_OS.md` references agent-stack docs | L | Open — **non-blocking** for Phase 1 exit |
| P0-03 | Document OpenKnowledge v0.29.1 pre-1.0 maturity risk in `knowledge/decisions/` | Knowledge curator | P0-01 | Decision doc with `status: verified`, rollback trigger defined | M | **DONE** |
| P0-04 | Define promotion workflow spec (Claude-mem → OpenKnowledge) | Knowledge curator | P0-01 | Workflow in `SWARM-ORCHESTRATION.md` § Promotion; no auto-sync path | M | **DONE** |
| P0-05 | Inventory existing verification assets (pytest, PIO, repo-truth) for agent-stack gates | Provenance auditor | — | Inventory table in Phase 6 eval doc; maps to gate types | L | Open — **non-blocking** for Phase 1 exit |
| P0-06 | Confirm AGPL implications for Herdr org deploy | Captain | — | Written note: deploy scope or defer org-wide | M | Open — **non-blocking** for Phase 1 exit |

---

## Phase 1 — Immediate adoption (Herdr, Codex plugin, sqlite-utils)

| ID | Task | Owner | Dep | Acceptance criteria | Risk | Status |
|----|------|-------|-----|---------------------|------|--------|
| P1-01 | Create Herdr workspace for `SpectraSynq_K1_Firmware` | Agent (ops) | P0-01 | Workspace visible; repo path correct; no agent execution routed through Herdr | L | **DONE** — [`phase1-herdr-proof.md`](../../knowledge/research/phase1-herdr-proof.md) |
| P1-02 | Document Herdr workspace layout per repo in `SWARM-ORCHESTRATION.md` | Knowledge curator | P1-01 | Section lists workspace name, repos, human checkpoint hooks | L | **DONE** — SWARM § Herdr + runbook |
| P1-03 | Install `openai/codex-plugin-cc` in Claude Code (scoped) | Agent | P0-01 | Plugin loads; documented in handoff template | M | **DONE** — [`phase1-codex-plugin-audit.md`](../../knowledge/research/phase1-codex-plugin-audit.md) |
| P1-04 | Write Codex handoff contract (review / adversarial / rescue) | Orchestrator | P1-03 | Contract in `SWARM-ORCHESTRATION.md`; includes required context bundle | M | **DONE** — SWARM § Codex handoff |
| P1-05 | Verify Codex plugin has **no** auto stop-gate enabled | Provenance auditor | P1-03 | Config audit log; explicit `DO NOT` in contract | H | **DONE** — `reviewGateEnabled: false` in audit |
| P1-06 | Install sqlite-utils in operator environment | Agent | P0-01 | `sqlite-utils --version` succeeds on operator machine | L | **DONE** — [`phase1-sqlite-utils-proof.md`](../../knowledge/research/phase1-sqlite-utils-proof.md) |
| P1-07 | Document read-only sqlite snapshot recipes (claude-mem DB, local stores) | Knowledge curator | P1-06 | Runbook in `knowledge/runbooks/sqlite-snapshots.md` | L | **DONE** — runbook + proof snapshot |
| P1-08 | Run first manual Codex adversarial review on a docs-only PR | Reviewer | P1-04 | Handoff artifact archived; Captain rates usefulness 1–5 | M | **DONE** — [`phase1-p1-08-codex-adversarial-result.md`](../../knowledge/research/phase1-p1-08-codex-adversarial-result.md) (scoped `codex exec`, ~99KB); verdict **FAIL** on contract coherence (12 findings); Captain usefulness **pending**; agent-self-rated: **4** |
| P1-09 | Add agent-stack bootstrap check to session ritual (read authority contract) | Knowledge curator | P0-02 | `AGENT_OS.md` or bootstrap script prints agent-stack reminder | L | **DONE** — `session-bootstrap.sh` + AGENT_OS pointer |

---

## Phase 2 — OpenKnowledge pilot (project-scoped)

| ID | Task | Owner | Dep | Acceptance criteria | Risk | Status |
|----|------|-------|-----|---------------------|------|--------|
| P2-01 | Scaffold `knowledge/` directory per authority contract layout | Knowledge curator | P0-04 | Dirs exist: index, product, architecture, decisions, runbooks, research | L | **DONE** — layout per contract |
| P2-02 | Install/configure OpenKnowledge MCP v0.29.1 (project scope) | Implementer | P2-01 | MCP reachable; scoped to this repo only | M | **DONE** — `@inkeep/open-knowledge@0.29.1`; project `.mcp.json` only; `content.dir: knowledge` — [`phase2-openknowledge-mcp-proof.md`](../../knowledge/research/phase2-openknowledge-mcp-proof.md) |
| P2-03 | Write `knowledge/index.md` with navigation and maturity disclaimer | Knowledge curator | P2-01 | Links all subdirs; notes pre-1.0 risk | L | **DONE** — updated 2026-07-13 |
| P2-04 | Migrate 3 high-value decisions from handoff/spec-index into `knowledge/decisions/` | Knowledge curator | P2-01 | Each has frontmatter: status, last_verified, sources | M | **DONE** — 4 decisions `status: verified` |
| P2-05 | Configure manual git commits for knowledge (no auto GitHub sync) | Captain | P2-02 | Documented policy; no bot auto-push | L | **DONE** — [`openknowledge-manual-git-policy.md`](../../knowledge/runbooks/openknowledge-manual-git-policy.md) |
| P2-06 | Implement compact Claude-mem injection policy (search budget) | Orchestrator | P2-02 | Documented max queries + terms; aligns with `AGENT_OS.md` | M | **DONE** — [`claude-mem-compact-injection.md`](../../knowledge/runbooks/claude-mem-compact-injection.md) |
| P2-07 | Seed `knowledge/current-priorities.md` from fresh `progress.md` | Knowledge curator | P2-03 | Priorities match git-verified lane; `last_verified` date set | M | **DONE** — seeded; Phase 2 ledger updated |
| P2-08 | Captain review: OpenKnowledge pilot go/no-go | Captain | P2-04 | Sign-off or rollback to Phase 1 only | M | **DONE** — Captain ratified **go** 2026-07-13; [`agent-stack-openknowledge-pilot-go-2026-07-13.md`](../../knowledge/decisions/agent-stack-openknowledge-pilot-go-2026-07-13.md); live MCP PASS [`phase2-openknowledge-mcp-proof.md`](../../knowledge/research/phase2-openknowledge-mcp-proof.md) |

---

## Phase 3 — Claude-mem + OpenKnowledge coexistence

| ID | Task | Owner | Dep | Acceptance criteria | Risk | Status |
|----|------|-------|-----|---------------------|------|--------|
| P3-01 | Author routing skill (`.cursor/skills/` + `.claude/skills/`) | Knowledge curator | P2-08 | Skill matches minimal routing content in authority contract | L | **DONE** — `.cursor/skills/knowledge-memory-routing/SKILL.md` + `.claude/skills/` mirror; verified 2026-07-13 via [`phase3-test1-fresh-handoff.md`](../../knowledge/research/phase3-test1-fresh-handoff.md) |
| P3-02 | Author promote-learning workflow skill | Knowledge curator | P0-04 | Step list: identify → draft → review → frontmatter → commit | M | **DONE** — [`knowledge/runbooks/promote-learning.md`](../../knowledge/runbooks/promote-learning.md); end-to-end demo: [`repo-truth-im73d-manifest-check-2026-07-13.md`](../../knowledge/decisions/repo-truth-im73d-manifest-check-2026-07-13.md) § Promotion workflow trace |
| P3-03 | Add promote-learning checklist to post-session report template | Knowledge curator | P3-02 | Template field: `openknowledge_promoted: <path\|none>` | L | **DONE** — [`knowledge/runbooks/promote-learning.md`](../../knowledge/runbooks/promote-learning.md); pointer + field in [`scripts/agent/post-session-report.md`](../../scripts/agent/post-session-report.md) |
| P3-04 | **Test 1:** Fresh-agent handoff — new agent completes scoped task using only promoted knowledge + code | Tester | P3-01 | Task completed without Captain re-brief; evidence log | M | **DONE** — [`phase3-test1-retest.md`](../../knowledge/research/phase3-test1-retest.md) (PASS vs original FAIL in [`phase3-test1-fresh-handoff.md`](../../knowledge/research/phase3-test1-fresh-handoff.md); G1–G3 closed; G4/G5 residual non-blocking) |
| P3-05 | **Test 2:** Old bug resurrection — agent finds prior fix via Claude-mem, confirms against code | Tester | P3-01 | Correct root cause cited; no doc/code conflict | M | **DONE** — [`phase3-test2-bug-resurrection.md`](../../knowledge/research/phase3-test2-bug-resurrection.md) (PASS; G1 `repo-truth.sh` manifest guard check fixed 2026-07-13) |
| P3-06 | **Test 3:** Architectural decision retrieval — agent cites `knowledge/decisions/` not stale handoff | Tester | P3-01 | Decision doc cited with `last_verified`; git lane verified | M | **DONE** — [`phase3-test3-arch-decision.md`](../../knowledge/research/phase3-test3-arch-decision.md) (PASS; MEDIUM friction on promotion-not-sync grep gap closed by [`agent-stack-promotion-not-sync.md`](../../knowledge/decisions/agent-stack-promotion-not-sync.md)) |
| P3-07 | Audit: confirm zero auto-sync pipelines Claude-mem → OpenKnowledge | Provenance auditor | P3-02 | Grep/config audit PASS; documented in audit log | H | **DONE** — audit log in [`repo-truth-im73d-manifest-check-2026-07-13.md`](../../knowledge/decisions/repo-truth-im73d-manifest-check-2026-07-13.md) § P3-07 auto-sync audit (2026-07-13; zero pipelines) |
| P3-08 | Phase 3 exit gate: all 3 tests PASS + auditor sign-off | Captain | P3-04..07 | Written gate record in `knowledge/decisions/` | M | Open |

---

## Phase 4 — Controlled pilots (Entire, Ruflo orchestration-only)

### Entire

| ID | Task | Owner | Dep | Acceptance criteria | Risk | Status |
|----|------|-------|-----|---------------------|------|--------|
| P4-E01 | Select one private pilot repo for Entire | Captain | P3-08 | Repo named in decision doc; not production firmware default | M | **DONE** — `SpectraSynq_K1_Firmware` @ `lane/gem-port-beat-pulse`; see [`phase4-entire-pilot-proof.md`](../../knowledge/research/phase4-entire-pilot-proof.md) |
| P4-E02 | Enable Entire: `entire enable --agent claude-code --local --skip-push-sessions --telemetry=false` | Implementer | P4-E01 | Command succeeds; config documented | M | **DONE** — `entire-cli@0.0.3`; enable PASS; config in proof |
| P4-E03 | Run 5-session pilot; verify local checkpoint lineage | Provenance auditor | P4-E02 | Checkpoints retrievable; no remote session push | M | **DONE (methodology + shell evidence)** — [`phase4-entire-lineage-proof.md`](../../knowledge/research/phase4-entire-lineage-proof.md) + [`phase4-entire-session-log.md`](../../knowledge/research/phase4-entire-session-log.md); 5 shell cycles + manual `entire hooks git`; `entire rewind` still empty (`hooks claude-code` missing in 0.0.3); live CC checkpoint retrieval **deferred**; `skipPushSessions` PASS |
| P4-E04 | Document Entire vs git vs OpenKnowledge boundaries | Knowledge curator | P4-E03 | Runbook clarifies authority (see contract) | L | **DONE** — [`entire-local-pilot.md`](../../knowledge/runbooks/entire-local-pilot.md) (+ proof § boundaries) |
| P4-E05 | Entire pilot go/no-go | Captain | P4-E03 | Continue, extend, or disable — recorded | M | **DONE** — **autonomous go** (Captain ratified 2026-07-13); `--local --skip-push-sessions --telemetry=false`; dual-path hooks ADR [`agent-stack-entire-hooks-dual-path.md`](../../knowledge/decisions/agent-stack-entire-hooks-dual-path.md) |

### Ruflo

| ID | Task | Owner | Dep | Acceptance criteria | Risk | Status |
|----|------|-------|-----|---------------------|------|--------|
| P4-R01 | Create isolated git worktree for Ruflo pilot | Implementer | P3-08 | Worktree path documented; not main firmware lane | M | **DONE** — `/tmp/ruflo-pilot-k1`, branch `pilot/ruflo-orchestration-phase4`; [`phase4-ruflo-pilot-proof.md`](../../knowledge/research/phase4-ruflo-pilot-proof.md) §1 |
| P4-R02 | Init Ruflo minimal: `RUFLO_DAEMON_AUTOSTART=0 npx ruflo@latest init --minimal --no-global` | Implementer | P4-R01 | Init succeeds; no global config pollution | H | **DONE** — ruflo v3.25.6; `--no-global`; proof §2 |
| P4-R03 | Verify Ruflo forbidden features disabled (daemon, memory, routing) | Provenance auditor | P4-R02 | Checklist PASS per authority contract | H | **DONE** — checklist **PASS**; proof §3 |
| P4-R04 | **Eval 1:** Independent implementation lanes (backend/frontend/tests) | Orchestrator | P4-R03 | 3 lanes complete; merge via normal git; metrics captured | M | **DONE** — docs-only bounded lanes (Captain adaptation); proof §4–§5 |
| P4-R05 | **Eval 2:** Cross-cutting defect — competing hypotheses investigation | Orchestrator | P4-R03 | Hypothesis log; winner evidence-based; no authority collision | M | **DONE** — repo-truth dual-track (P1-08-04); proof §8 |
| P4-R06 | **Eval 3:** Release prep (review, tests, docs, risk, readiness) | Orchestrator | P4-R03 | Readiness checklist complete; human checkpoint in Herdr | M | **DONE** — readiness §9; Herdr bundle §9.2 |
| P4-R07 | Ruflo pilot scorecard vs manual orchestration | Captain | P4-R04..06 | Written score: time, quality, failure modes | M | **DONE** — proof §10 |
| P4-R08 | Tear down or quarantine Ruflo worktree if pilot fails | Implementer | P4-R07 | No residual daemon/global config | M | Open — pilot PASS; teardown optional: `git worktree remove /tmp/ruflo-pilot-k1` |

---

## Phase 5 — Headroom compression benchmark

| ID | Task | Owner | Dep | Acceptance criteria | Risk |
|----|------|-------|-----|---------------------|------|
| P5-01 | Define Headroom A/B protocol (compression-only) | Orchestrator | P4-R07 or P3-08 | Protocol excludes: memory, learn, instruction writes, output shaping | M |
| P5-02 | Establish baseline token/headroom metrics on representative tasks | Tester | P5-01 | 3 task types measured: debug, implement, review | M |
| P5-03 | Run Headroom compression variant; capture metrics | Tester | P5-02 | A/B table with task ID, tokens, outcome quality | M |
| P5-04 | Human quality review of Headroom outputs | Captain | P5-03 | No unacceptable information loss on 3/3 tasks | H |
| P5-05 | Headroom go/no-go for standard stack | Captain | P5-04 | Decision doc; default remains no Headroom in prod | M |

---

## Phase 6 — Evaluation gates & promotion to standard stack

| ID | Task | Owner | Dep | Acceptance criteria | Risk |
|----|------|-------|-----|---------------------|------|
| P6-01 | Compile phase scorecards (Phases 1–5) | Provenance auditor | P5-05 | Single matrix: tool, status, evidence links | L |
| P6-02 | Define standard stack manifest (`docs/agent-stack/STANDARD-STACK.md`) | Captain | P6-01 | Lists adopted tools, configs, forbidden tools | M |
| P6-03 | Update `AGENT_OS.md` with standard stack pointer | Knowledge curator | P6-02 | Agents see stack on bootstrap | L |
| P6-04 | Roll out OpenKnowledge to second SpectraSynq repo (if Phase 3 PASS) | Implementer | P6-02 | Second repo `knowledge/` seeded | M |
| P6-05 | Training runbook for new agents (routing + promote + Herdr) | Knowledge curator | P6-02 | Runbook in `knowledge/runbooks/agent-onboarding.md` | L |
| P6-06 | Final Captain sign-off: agent stack v1 | Captain | P6-01..05 | Promotion recorded; rejected tools remain rejected | L |

---

## Explicit rejections (no tasks — binding)

| Tool | Action | Owner |
|------|--------|-------|
| **pxpipe** | Do not install, evaluate, or document as optional | Captain |
| **OmniRoute (primary)** | Lab experiments only with Captain approval; never default gateway | Captain |
| **Ruflo full init** | Never run `--dual`, `--all-agents`, or enable daemon | Provenance auditor |
| **Codex auto stop-gate** | Never enable | Provenance auditor |
| **Claude-mem → OpenKnowledge auto-sync** | Never implement | Provenance auditor |

---

## Dependency graph (summary)

```
P0 ──► P1 ──► P2 ──► P3 ──► P4 (E + R parallel) ──► P5 ──► P6
         │              │
         └──────────────┴──► Routing skill + promote workflow (P3)
```

---

## Risk register

| Risk | Mitigation | Phase |
|------|------------|-------|
| OpenKnowledge v0.29.1 breaking changes pre-1.0 | Pin version; pilot scope; rollback to Claude-mem + git docs | 2–3 |
| Ruflo scope creep (memory, routing) | Provenance auditor checklist; isolated worktree | 4 |
| Authority collision (memory vs knowledge vs code) | Routing skill + contract; promotion-only writes | 0–3 |
| pxpipe-style silent corruption | Hard reject; no pilot | — |
| Codex bypassing firmware safety | Handoff contract requires AGENT_OS acknowledgment | 1 |
| Herdr AGPL compliance | P0-06 legal/scope review | 0 |

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-07-13 | agent:cursor | P2-08 DONE — Captain ratified stack; live MCP search/config PASS; Phase 2 exit gate PASS — [`phase2-openknowledge-mcp-proof.md`](../../knowledge/research/phase2-openknowledge-mcp-proof.md) |
| 2026-07-13 | agent:cursor | **Phase 2 DONE** — P2-08 Captain ratified go; exit gate PASS; canonical proof [`phase2-openknowledge-mcp-proof.md`](../../knowledge/research/phase2-openknowledge-mcp-proof.md); `.mcp.json` only (duplicate `.cursor/mcp.json` removed) |
| 2026-07-13 | agent:search-specialist | P2-02 UNBLOCKED: correct package `@inkeep/open-knowledge` (v0.29.1) identified and installed; `.mcp.json` + `.cursor/mcp.json` registered; MCP server callable; Phase 2 exit criteria on track for P2-08 Captain review |
| 2026-07-13 | agent:orchestrator | Initial task backlog from architecture review |
| 2026-07-13 | agent:cursor | Phase 1 executed autonomously; P1-01–07, P1-09 DONE; P1-08 partial |
| 2026-07-13 | agent:cursor | P1-08 contract remediation; Phase 1 exit = DONE; P0-02/05/06 marked non-blocking |
| 2026-07-13 | agent:cursor | Phase 2 partial: P2-01,03–07 DONE; P2-02 MCP BLOCKED; markdown pilot active |
| 2026-07-13 | agent:cursor | Phase 3 test1: P3-01 DONE; P3-04 IN PROGRESS — [`phase3-test1-fresh-handoff.md`](../../knowledge/research/phase3-test1-fresh-handoff.md) PARTIAL FAIL (G1–G6) |
| 2026-07-13 | agent:cursor | P3-04 Test 1 retest PASS — [`phase3-test1-retest.md`](../../knowledge/research/phase3-test1-retest.md); G1–G3 remediation verified (agent `022139ef`) |
| 2026-07-13 | agent:cursor | P3-06 Test 3 DONE — [`phase3-test3-arch-decision.md`](../../knowledge/research/phase3-test3-arch-decision.md); promotion-not-sync ADR added |
| 2026-07-13 | agent:cursor | Phase 4 Ruflo partial: P4-R01–R04 DONE (orchestration-only PASS in isolated worktree) — [`phase4-ruflo-pilot-proof.md`](../../knowledge/research/phase4-ruflo-pilot-proof.md); main repo ingest only (no worktree merge, no Ruflo init on lane) |
| 2026-07-13 | agent:cursor | Phase 4 Entire partial: P4-E01–E02, E04 DONE; P4-E03/E05 open — [`phase4-entire-pilot-proof.md`](../../knowledge/research/phase4-entire-pilot-proof.md); `core.hooksPath` vs Entire git hooks |
| 2026-07-13 | agent:cursor | P4-E03 lineage audit — [`phase4-entire-lineage-proof.md`](../../knowledge/research/phase4-entire-lineage-proof.md); status IN PROGRESS (live 5-session retrieval open) |
| 2026-07-13 | agent:cursor | P4-E03 **DONE** (methodology + shell evidence) — [`phase4-entire-session-log.md`](../../knowledge/research/phase4-entire-session-log.md); checkpoint `rewind` deferred pending Claude Code + Entire CLI hook fix |
| 2026-07-13 | agent:cursor | P4-E05 **DONE** — Captain ratified autonomous go; hooks dual-path ADR [`agent-stack-entire-hooks-dual-path.md`](../../knowledge/decisions/agent-stack-entire-hooks-dual-path.md); P4-E03 remains open (5-session lineage) |
| 2026-07-13 | agent:cursor | Phase 4 Ruflo Eval 2–3 + P4-R05–R07 DONE — proof §8–§10; worktree orchestration-only |
