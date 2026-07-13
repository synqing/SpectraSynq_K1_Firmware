---
title: Phase 4 exit gate — summary
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/PHASED-ROLLOUT.md § Phase 4
  - docs/agent-stack/ACTIONABLE-TASKS.md § Phase 4
  - knowledge/research/phase4-entire-pilot-proof.md
  - knowledge/research/phase4-entire-lineage-proof.md
  - knowledge/research/phase4-ruflo-pilot-proof.md
  - knowledge/decisions/agent-stack-entire-hooks-dual-path.md
owner: knowledge-curator
---

# Phase 4 exit gate summary

**Theme:** Controlled pilots — Entire commit provenance + Ruflo orchestration-only (isolated worktree).  
**Exit date:** 2026-07-13  
**Verdict:** **PASS with documented debt** (Captain ratified autonomous go, P4-08)

---

## Composite verdict

| Track | Task range | Status | Pilot outcome |
|-------|------------|--------|---------------|
| **Entire** | P4-E01–E05 | **DONE** | Local enable PASS; shell lineage evidence; live checkpoint retrieval **deferred** |
| **Ruflo** | P4-R01–R08 | **COMPLETE** | Orchestration-only **PASS**; worktree torn down; no main-repo contamination |
| **Phase 4 exit** | P4-08 | **PASS** | Both pilots evaluated; debt documented; Phase 5 entry unblocked |

Phase 4 is **not** a full production adoption gate. It proves pilots ran in isolation, forbidden features stayed off, and Captain go/no-go is recorded per tool. Entire debt does **not** block Phase 5 (Headroom benchmark is independent per `PHASED-ROLLOUT.md`).

---

## Entire (P4-E01–E05)

| ID | Deliverable | Result | Evidence |
|----|-------------|--------|----------|
| P4-E01 | Pilot repo selection | **DONE** | `SpectraSynq_K1_Firmware` @ `lane/gem-port-beat-pulse` — [`phase4-entire-pilot-proof.md`](./phase4-entire-pilot-proof.md) |
| P4-E02 | Enable Entire local | **DONE** | `entire-cli@0.0.3`; `--local --skip-push-sessions --telemetry=false` |
| P4-E03 | 5-session lineage | **DONE (methodology + shell evidence)** | [`phase4-entire-lineage-proof.md`](./phase4-entire-lineage-proof.md) + [`phase4-entire-session-log.md`](./phase4-entire-session-log.md) |
| P4-E04 | Authority boundaries runbook | **DONE** | [`entire-local-pilot.md`](../runbooks/entire-local-pilot.md) |
| P4-E05 | Captain go/no-go | **DONE** | Autonomous go (Captain ratified 2026-07-13); [`agent-stack-entire-hooks-dual-path.md`](../decisions/agent-stack-entire-hooks-dual-path.md) |

### CLI limitation note (`entire-cli@0.0.3`)

| Limitation | Impact | Mitigation / follow-up |
|------------|--------|------------------------|
| **No Codex agent** — README lists Claude Code, Cursor, Gemini CLI, OpenCode; pilot used `--agent claude-code` only | Codex/Cursor sessions do not get Entire agent hooks via shipped CLI | Defer Codex Entire enable until upstream documents support |
| **npm `entire-cli@0.0.3` hook CLI gap** — `entire --help` has no `hooks`; `entire hooks claude-code` → `Unknown hooks subcommand: claude-code`; enable path is `entire enable --agent claude-code` per upstream README | No session store / empty `entire rewind` in pilot | Upgrade Entire beyond npm `0.0.3` or Homebrew channel; retest lineage |
| **Dual-path git hooks** — `core.hooksPath=scripts/hooks` → Entire `.git/hooks/*` dormant on normal commits | K1 pre-commit gate wins (correct); Entire git checkpoint hooks inactive unless chained | Documented in dual-path ADR; manual `entire hooks git` invocations exit 0 but create no checkpoints without session |
| **No `entire blame` / `entire why`** | Rollout language maps to `entire explain` + `entire rewind` | Mapped in lineage proof §2 |
| **`entire rewind` empty** after P4-E03 | Live checkpoint retrieval not proven | **Deferred debt** — not blocking Phase 4 exit |

**Entire partial PASS interpretation:** Install, policy (`skipPushSessions`, telemetry off), boundaries, and five capture cycles are proven. **Checkpoint lineage retrieval** remains follow-up work, not a Phase 4 blocker.

---

## Ruflo (P4-R01–R08) — orchestration-only COMPLETE

| ID | Deliverable | Result | Evidence |
|----|-------------|--------|----------|
| P4-R01 | Isolated worktree | **DONE** | `/tmp/ruflo-pilot-k1`, branch `pilot/ruflo-orchestration-phase4` — proof §1 |
| P4-R02 | Minimal init | **DONE** | `RUFLO_DAEMON_AUTOSTART=0`; `ruflo v3.25.6`; `--minimal --no-global` — proof §2 |
| P4-R03 | Forbidden-features checklist | **PASS** | Daemon, memory, routing, federation absent — proof §3 |
| P4-R04 | Eval 1 — bounded lanes | **PASS** | Docs-only 3 lanes + orchestrator — proof §4–§5 |
| P4-R05 | Eval 2 — cross-cutting defect | **PASS** | Repo-truth dual-track (P1-08-04); H3 accepted — proof §8 |
| P4-R06 | Eval 3 — release prep | **PASS** | Readiness checklist + Herdr bundle — proof §9 |
| P4-R07 | Scorecard vs manual | **DONE** | Orchestration-only PASS; provenance repeatability wins — proof §10 |
| P4-R08 | Worktree teardown | **DONE** | Worktree absent; main repo no `.claude-flow` — proof §11 |

**Ruflo verdict:** **PASS (orchestration-only)** — 0 forbidden-feature command violations; 3 evals scored; worktree quarantined and removed. Full `swarm coordinate` with API execution **not** evaluated (explicit deferral).

---

## Exit gate criteria (composite)

| Criterion | Entire | Ruflo | Composite |
|-----------|--------|-------|-----------|
| Pilot isolated from main firmware lane | Local on feature lane; no session push | Worktree-only; torn down | **PASS** |
| Forbidden / out-of-scope features off | No remote push; telemetry off | No daemon, memory, routing, federation | **PASS** |
| Evaluated per tool go/no-go | P4-E05 autonomous go | P4-R07 scorecard + proof §10 | **PASS** |
| Lineage / orchestration proof | Shell evidence; `rewind` deferred | Eval 1–3 complete | **PASS with debt** (Entire checkpoints) |
| Captain ratification | P4-E05 + P4-08 | P4-R07 + P4-08 | **PASS** (2026-07-13) |

---

## Documented debt (non-blocking)

1. **Entire live checkpoint retrieval** — `entire rewind` empty on npm `0.0.3`; unpromoted — retest after CLI upgrade (`entire enable --agent claude-code` per upstream).
2. **Entire Codex enable** — not attempted; `entire-cli@0.0.3` has no Codex integration path.
3. **Ruflo full swarm** — orchestration CLI + manual merge only; defer `swarm coordinate` until API keys + explicit Captain scope.
4. **Host disk** — Ruflo `doctor` disk check failed at 97% used (environmental; noted in proof §6).

---

## Authority model (post Phase 4)

```
Git history / PR truth     → source of record (unchanged)
knowledge/ markdown        → OpenKnowledge pilot (Phase 2–3)
Claude-mem                 → episodic recall (Phase 3 routing)
Entire                     → optional local provenance pilot (continue local-only)
Ruflo                      → orchestration-only reference; no init on main lane/*
Human checkpoint           → Herdr + Captain
```

**Forbidden (unchanged):** Entire remote session push; Ruflo `--dual` / memory / daemon on firmware lane; treating Entire as git replacement.

---

## Next phase pointer

Phase 5 — Headroom compression benchmark (compression-only A/B). See
[`PHASED-ROLLOUT.md`](../../docs/agent-stack/PHASED-ROLLOUT.md) § Phase 5.

Entry: Phase 4 complete (this gate). Headroom **compression-only** benchmark is **agent-autonomous** — no Captain spend gate ([`agent-stack-autonomous-execution.md`](../decisions/agent-stack-autonomous-execution.md)).
