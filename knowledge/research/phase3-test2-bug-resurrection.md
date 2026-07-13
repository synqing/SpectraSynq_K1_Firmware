---
title: Phase 3 Test 2 — Old Bug Resurrection
status: verified
last_verified: 2026-07-13
sources:
  - docs/agent-stack/PHASED-ROLLOUT.md § Phase 3 test scenarios
  - docs/agent-stack/ACTIONABLE-TASKS.md P3-05
  - .cursor/skills/knowledge-memory-routing/SKILL.md
  - knowledge/runbooks/claude-mem-compact-injection.md
  - knowledge/decisions/agent-stack-repo-truth-dual-track.md
  - knowledge/research/phase1-p1-08-codex-adversarial-result.md
owner: tester
test_scenario: phase3-test2-bug-resurrection
---

# Phase 3 Test 2 — Old Bug Resurrection

**Scenario:** SWARM-ORCHESTRATION / `PHASED-ROLLOUT.md` Test 2 — agent finds a prior fix or known bug in Claude-mem, validates against current code, cites correct root cause.

**Acceptance target (P3-05):** Correct root cause cited; no doc/code conflict.

**Execution date:** 2026-07-13  
**Method:** `knowledge-memory-routing` skill → `knowledge/` decisions first → Claude-mem `search` (single-term queries per runbook) → `get_observations` → live `session-bootstrap.sh` + `repo-truth.sh` + source grep. No firmware edits; no Captain prompts.

## Resurrected bug (selected)

| Field | Value |
|-------|-------|
| **Symptom** | `session-bootstrap.sh` / `repo-truth.sh` → **OVERALL FAIL** — `k1_upload_guard.py does not reference k1_bench_im73d` |
| **First documented (durable)** | P1-08 adversarial review (2026-07-13) finding **P1-08-04**; live Codex run during review |
| **Episodic trail** | Claude-mem IM73D / upload-guard sessions Jul 6–10, 2026 |
| **Why “resurrection”** | Known IM73D lane-integrity failure reappears on every bootstrap despite manifest-based guard refactor and prior upload-guard fixes |

## Routing skill compliance

| Step | Skill rule | Action taken |
|------|------------|--------------|
| 1 | Durable decision before mem | Read `knowledge/decisions/agent-stack-repo-truth-dual-track.md`, `phase1-p1-08-contract-remediation.md` |
| 2 | Episodic for “prior bug / what did we try?” | Claude-mem `search` + `get_observations` |
| 3 | Implementation truth | `repo-truth.sh`, `k1_upload_guard.py`, `k1_device_identities.json`, `tests/test_k1_upload_guard.py` |
| 4 | One term per mem query | Compound queries returned **0 rows**; single-term queries succeeded |
| 5 | Conflict → report, don’t average | Mem #75426 vs current manifest — resolved via code + lane docs (see § Conflict) |

## Claude-mem retrieval log

### Search calls

| Query | Result | Notes |
|-------|--------|-------|
| `IM73D repo-truth k1_bench_im73d` | **0** | Compound query — runbook violation |
| `repo-truth FAIL upload guard` | **0** | Compound |
| `k1_upload_guard k1_bench_im73d` | **0** | Compound |
| `phase3 openknowledge memory routing` | **0** | Compound |
| `IM73D` | **60** (20 obs shown) | **Hit** — upload guard, manifest, misflash evidence |
| `upload` | **45** (15 obs) | **Hit** — includes #70918 K1 guard discovery |
| `repo-truth` | **6** | **Hit** — sparse; no direct IM73D-guard FAIL obs |
| `guard` | **30** (10 obs) | **Hit** — includes #71283 manifest architecture |

### Observations fetched (`get_observations`)

| ID | Date | Type | Title | Relevance |
|----|------|------|-------|-----------|
| **#71283** | 2026-06-27 | feature | K1 Upload Guard Identity System: manifest + guard split | Explains why env names left `k1_upload_guard.py` |
| **#75426** | 2026-07-06 | change | `k1_prod_im73d` blocked in `BLOCKED_UPLOAD_ENVS` | Prior **fix** on SpectraSynq_K1_Firmware project |
| **#76126** | 2026-07-08 | discovery | H1 gap: guard validates serial/env, not compiled MIC type | Related gotcha; worktree context |
| **#70918** | 2026-06-27 | discovery | Guard validates USB serial before flash | Baseline guard behavior |

**Budget:** 4 `search`, 1 `get_observations` batch (4 IDs) — within `claude-mem-compact-injection.md` caps.

## `knowledge/` retrieval log

| Path | `status` | Used for |
|------|----------|----------|
| `knowledge/index.md` | verified | Authority table; promotion-not-sync pointer |
| `knowledge/decisions/agent-stack-repo-truth-dual-track.md` | verified | Docs-only proceed under FAIL; firmware blocked |
| `knowledge/research/phase1-p1-08-codex-adversarial-result.md` | verified | P1-08-04: bootstrap FAIL vs rollout narrative |
| `knowledge/research/phase1-p1-08-contract-remediation.md` | verified | Remediation map; open item: firmware repo-truth FAIL |
| `knowledge/current-priorities.md` | verified | IM73D lane + dual-track table |
| `knowledge/runbooks/claude-mem-compact-injection.md` | verified | Single-term query rule |

**Gap:** No promoted ADR names the **manifest-vs-grep** root cause for `IM73D guard: FAIL`. Durable knowledge correctly states FAIL exists and dual-track policy; it does not explain that the guard check in `repo-truth.sh` is stale relative to the manifest refactor.

## Live validation (2026-07-13)

```text
branch       : lane/gem-port-beat-pulse
HEAD         : 61768ee
repo-truth   : FAIL
  IM73D env  : PASS
  IM73D guard: FAIL  ← k1_upload_guard.py does not reference k1_bench_im73d
  IM73D plan : PASS
```

### Code truth

| Check | Result |
|-------|--------|
| `platformio.ini` has `[env:k1_bench_im73d]` | **Yes** |
| `k1_device_identities.json` lists `k1_bench_im73d` for bench B489A500 | **Yes** (lines 63–66) |
| `k1_upload_guard.py` contains string `k1_bench_im73d` | **No** — loads envs from manifest via `load_identities()` |
| `validate_upload_target("k1_bench_im73d", main_port)` rejects cross-flash | **Yes** — `tests/test_k1_upload_guard.py` L155–157 |
| Guard functional for IM73D bench env | **Yes** — identity-by-serial via manifest |

### Root cause (cited)

**Primary:** `scripts/agent/repo-truth.sh` L44–48 uses a **literal grep** on `k1_upload_guard.py` for `k1_bench_im73d`. After the N4a manifest refactor (claude-mem #71283; manifest is single source of truth), env names live in `k1_device_identities.json`, not as string literals in the guard module. The check is **stale** — it reports FAIL while upload protection for `k1_bench_im73d` is implemented.

**Secondary (related, not repo-truth FAIL):** Claude-mem #76126 documents H1 — `k1_bench_reference` remains in bench B489A500 allowed envs; guard does not verify compiled `K1_MIC_IM73D_PDM_V1`. Still true in manifest L67. Separate from grep FAIL.

## Conflict: mem vs code (#75426)

| Source | Claim |
|--------|-------|
| Claude-mem **#75426** | `k1_prod_im73d` added to `BLOCKED_UPLOAD_ENVS` to prevent misflash on main K1 (SPH0645) |
| Current manifest | `k1_prod_im73d` in **authorized** envs for F887A500 (L45); only `k1_sample_rate_32k_spike` blocked |
| Tests | `test_prod_im73d_env_is_bound_to_main_k1` expects **accept** on main port |

**Resolution (precedence: code + lane docs > mem):**

- `docs/hardware/im73d-productionization-execution-plan-2026-07-06.md` documents **2026-07-07 correction**: Captain confirmed identical hardware; `k1_prod_im73d` guard-mapped to main MAC; do not re-add block unless new explicit blocker.
- Mem #75426 is **historical** — fix was later **intentionally superseded**, not silently regressed.
- **No doc/code conflict** when mem is read as episodic hypothesis and lane handover docs are consulted.

## Routing quality assessment

| Layer | Route correct? | Evidence |
|-------|----------------|----------|
| **Durable knowledge** | **PARTIAL** | Dual-track + P1-08 FAIL acknowledged; root cause of grep staleness not promoted |
| **Episodic memory** | **PASS** | Single-term `IM73D` / `guard` surfaced manifest refactor + prior block story |
| **Implementation truth** | **PASS** | Manifest + tests prove guard works; `repo-truth.sh` grep does not |
| **Precedence applied** | **PASS** | Code/manifest wins over mem #75426; mem wins over stale handoff narrative |
| **Promotion-not-sync** | **PASS** | This test file is research evidence only; no auto-dump from mem |

### Anti-pattern checks

| Anti-pattern | Avoided? |
|--------------|----------|
| Treating Claude-mem as lane truth | Yes — git/bootstrap authoritative |
| Auto-syncing mem → `knowledge/` | Yes — analysis only |
| Treating `knowledge/` as override for code | Yes — code/manifest cited for guard behavior |
| Averaging mem vs code on #75426 | Yes — reported conflict, cited 2026-07-07 correction |

## P3-05 verdict

| Criterion | Result |
|-----------|--------|
| Prior fix/bug found via Claude-mem | **PASS** — #71283, #75426, #76126, IM73D search index |
| Validated against current code | **PASS** — manifest, guard loader, pytest, live `repo-truth.sh` |
| Correct root cause cited | **PASS** — stale `repo-truth.sh` grep after manifest migration |
| No doc/code conflict | **PASS** — #75426 resolved via lane docs; dual-track policy consistent with docs-only scope |

**Overall:** **PASS**

## Gaps (remediation backlog)

| ID | Gap | Severity | Remediation |
|----|-----|----------|-------------|
| G1 | `repo-truth.sh` IM73D guard check grep-only | **H** | Update check to grep manifest **or** `k1_device_identities.json` for `k1_bench_im73d` |
| G2 | No promoted decision for manifest migration vs repo-truth | **M** | **Closed** — [`repo-truth-im73d-manifest-check-2026-07-13.md`](../decisions/repo-truth-im73d-manifest-check-2026-07-13.md) |
| G3 | Compound mem queries return zero | **L** | Already in runbook; reinforce in routing skill examples |
| G4 | `repo-truth` token sparse in mem | **L** | Optional observation on grep staleness when G1 fixed |

## Evidence

- Simulation date: 2026-07-13
- Agent: cursor (autonomous Phase 3 subagent)
- Bootstrap: `session-bootstrap.sh` exit **nonzero** (repo-truth FAIL) — expected for docs-only test
- Claude-mem MCP: reachable per bootstrap
- No firmware edits; no Captain prompts

## Follow-up: repo-truth fix applied

- **2026-07-13:** `scripts/agent/repo-truth.sh` IM73D guard check now validates `k1_device_identities.json` authorizes `k1_bench_im73d` and that `k1_upload_guard.py` loads the manifest (replaces stale grep for env literal in `.py`).
- **Evidence:** `bash scripts/agent/repo-truth.sh` → IM73D guard **PASS**, OVERALL **WARN** (registry dirty only); `bash scripts/agent/session-bootstrap.sh` exit **0** (was **1** before fix).
