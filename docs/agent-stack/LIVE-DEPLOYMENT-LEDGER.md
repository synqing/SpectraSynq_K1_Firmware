# Agent Stack — Live Deployment Ledger

**Purpose:** Governed log of **live deployment campaign** sessions on the standard stack (post–rollout-close `d5639cd`).  
**Canonical manifest:** [`STANDARD-STACK.md`](./STANDARD-STACK.md)  
**Rollout close:** `d5639cd` — `docs(agent-stack): close rollout v1` (ancestor of firmware-lane work).

**Policy:** Sibling repos get pointer files only — no full `knowledge/` tree copy. Entire / Ruflo / Headroom not enabled on siblings unless explicitly scoped. **No new architecture research or rollout phases** during live deployment.

---

## Session runs

| # | date | repo | task | tools | outcome | captain_interventions | verification | tokens/efficiency | defects | promotion_rec |
|---|------|------|------|-------|---------|----------------------|--------------|-------------------|---------|---------------|
| 1 | 2026-07-13 | `SpectraSynq_K1_Firmware` (`w1`) | Session 1: ship IM73D `repo-truth` manifest guard (`2a4be6b`) on `lane/gem-port-beat-pulse` | Herdr `w1` (pre-existing); `session-bootstrap.sh`; OK scope; claude-mem reachable; Codex `exec review --commit 2a4be6b`; Entire `status`/`doctor`/`rewind` | **Shipped** `fix(agent): validate IM73D via device identity manifest` — separate from rollout doc commit `d5639cd` | none | **5 signals:** (1) bootstrap exit **0**; (2) `repo-truth` IM73D env/guard/plan **PASS**, OVERALL **WARN** (registry dirty, expected no auto-commit); (3) `ok-scope` **PASS**; (4) Herdr workspace **w1** focused; (5) Entire **enabled**, strategy `manual-commit`, **rewind empty** (npm `entire-cli@0.0.3` — no lineage points). Commit-gate **docs** tier PASS. Targeted pytest upload/guard **24 passed**. Full suite **690 passed / 13 failed** on dirty lane (not staged; not gate for this commit). | Codex review ~173s; scoped single-file commit | Codex **P2:** guard checks env membership only, not bench chip `B489A500` row binding. Lane-wide pytest failures (effect registry, golden master, IM73D harness) — **pre-existing**, not introduced by `2a4be6b`. | **No** `knowledge/` promote — follow-up optional: tighten repo-truth to assert `k1_bench_im73d` ↔ bench identity row |

---

## Repo deployment status (sibling pointers)

Deployed **2026-07-13** by agent:cursor (sibling pointer rollout).

| Repo | Path | Herdr `workspace_id` | Pointer file | README / AGENTS line | Notes |
|------|------|----------------------|--------------|----------------------|-------|
| **K1.esp32s3** | `/Users/spectrasynq/Workspace_Management/Software/K1.esp32s3` | `w2` | `docs/agent-stack-link.md` | `AGENTS.md` (1 line) | ESP32-S3 renderer / OSC firmware |
| **K1.juce** | `/Users/spectrasynq/Workspace_Management/Software/K1.juce` | `w3` | `docs/agent-stack-link.md` | `AGENTS.md` (1 line) | JUCE desktop host |
| **K1.tab5** | `/Users/spectrasynq/Workspace_Management/Software/T-Keyboard-S3-Pro/K1.tab5` | `w4` | `docs/agent-stack-link.md` | `README.md` (1 line) | Tab5 deck controller; no `AGENTS.md` |
| **SpectraSynq.LandingPage** | `/Users/spectrasynq/SpectraSynq.LandingPage` → archive path | `w5` | `docs/agent-stack-link.md` | `README.md` (1 line) | Active K1 FE landing; symlink to archive dir |
| **SpectraSynq_K1_Firmware** | `/Users/spectrasynq/SpectraSynq_K1_Firmware` | `w1` | *(canonical)* | `AGENT_OS.md` §2 | Full stack + `knowledge/` authority |

### Not deployed (surveyed, out of scope)

| Candidate | Path | Reason |
|-----------|------|--------|
| `spectrasynq-design-system` | `/Users/spectrasynq/Workspace_Management/Software/spectrasynq-design-system` | Not a git repo |
| `K1.Landing-Page` | `/Users/spectrasynq/Workspace_Management/Software/K1.Landing-Page` | Superseded by `SpectraSynq.LandingPage` per landing README |
| K718 design system artifacts | `SpectraSynq_K1_Firmware/artifacts/K7180-Design-System/` | Lives inside firmware repo, not a sibling checkout |

### Herdr summary (operator machine)

| `workspace_id` | Label | `cwd` |
|----------------|-------|-------|
| `w1` | `SpectraSynq_K1_Firmware` | `/Users/spectrasynq/SpectraSynq_K1_Firmware` |
| `w2` | `K1.esp32s3` | `/Users/spectrasynq/Workspace_Management/Software/K1.esp32s3` |
| `w3` | `K1.juce` | `/Users/spectrasynq/Workspace_Management/Software/K1.juce` |
| `w4` | `K1.tab5` | `/Users/spectrasynq/Workspace_Management/Software/T-Keyboard-S3-Pro/K1.tab5` |
| `w5` | `SpectraSynq.LandingPage` | `/Users/spectrasynq/SpectraSynq/archive/SpectraSynq.LandingPage.archived_2026-05-14` |

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-07-13 | agent:cursor | Session run table + row #1 (live deployment Session 1) |
| 2026-07-13 | agent:cursor | Initial sibling pointer deployment (4 repos + ledger) |
