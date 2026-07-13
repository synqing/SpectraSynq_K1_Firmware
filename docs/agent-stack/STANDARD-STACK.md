# SpectraSynq Standard Agent Stack — v1

**Status:** Ratified 2026-07-13 (Captain autonomous promotion doc)  
**Version:** 1.0  
**Authority:** [`AUTHORITY-CONTRACT.md`](./AUTHORITY-CONTRACT.md) (tool domains); [`AGENT_OS.md`](../../AGENT_OS.md) (firmware safety gates)  
**Scorecard:** [`knowledge/research/phase6-scorecard.md`](../../knowledge/research/phase6-scorecard.md)  
**Decision:** [`knowledge/decisions/agent-stack-standard-stack-2026-07-13.md`](../../knowledge/decisions/agent-stack-standard-stack-2026-07-13.md)

---

## Purpose

This manifest is the **canonical adoption list** for SpectraSynq agent infrastructure after
Phases 0–6 of [`PHASED-ROLLOUT.md`](./PHASED-ROLLOUT.md). Agents bootstrap from
`AGENT_OS.md` + this file for operator tooling, knowledge routing, and forbidden paths.

**Firmware lane verification** remains in `AGENT_OS.md` §3 — not overridden here.

---

## Adopted (standard stack v1)

| Component | Role | Version / pin | Config / scope | Evidence |
|-----------|------|---------------|----------------|----------|
| **Herdr** | Captain visibility console; one workspace per repo | **0.7.3** (Homebrew `herdr`) | Workspace `w1` → K1 repo root; agents **do not** execute through Herdr | [`phase1-herdr-proof.md`](../../knowledge/research/phase1-herdr-proof.md) |
| **Codex plugin** | Manual Claude↔Codex handoff (review, adversarial, rescue) | **codex@openai-codex 1.0.6**; Codex CLI **0.142.5** | `reviewGateEnabled: false` — **no auto stop-gate** | [`phase1-codex-plugin-audit.md`](../../knowledge/research/phase1-codex-plugin-audit.md) |
| **sqlite-utils** | Operator read-only SQLite snapshots | **3.39** (operator env) | Copy-before-query; no production writes | [`phase1-sqlite-utils-proof.md`](../../knowledge/research/phase1-sqlite-utils-proof.md) |
| **OpenKnowledge MCP** | Project-scoped durable knowledge accelerator | **`@inkeep/open-knowledge@0.29.1`** | `.ok/config.yml` → `content.dir: knowledge`; `.mcp.json` (Claude Code) + `.cursor/mcp.json` (Cursor, OK-only); **no user-global** | [`phase2-openknowledge-mcp-proof.md`](../../knowledge/research/phase2-openknowledge-mcp-proof.md) |
| **`knowledge/` scaffold** | Curated Markdown-in-git (authoritative over MCP) | Layout per authority contract | `index`, `decisions`, `runbooks`, `research`, `architecture`, `product` | [`knowledge/index.md`](../../knowledge/index.md) |
| **Claude-mem coexistence** | Episodic session history (read + hook writes) | Worker mode **13.6.0** | Compact injection budget per runbook; **never** lane truth | [`phase3-exit-gate-summary.md`](../../knowledge/research/phase3-exit-gate-summary.md) |
| **Routing skill** | Query routing: code vs OK vs claude-mem | `.cursor/skills/knowledge-memory-routing/` | Mirror: `.claude/skills/knowledge-memory-routing/` | Phase 3 Test 1–3 PASS |
| **Promote-learning skill** | Durable write path to `knowledge/` | `.cursor/skills/promote-learning/` | Mirror + [`knowledge/runbooks/promote-learning.md`](../../knowledge/runbooks/promote-learning.md) | P3-02, P3-07 audit |

### Session ritual (all agents)

1. `bash scripts/agent/session-bootstrap.sh`
2. Verify git lane (`git branch --show-current`, `HEAD`)
3. Read [`knowledge/runbooks/fresh-agent-handoff.md`](../../knowledge/runbooks/fresh-agent-handoff.md)
4. Claude-mem: `search` → `timeline` → `get_observations` (budget per compact-injection runbook)
5. Durable facts: `knowledge/decisions/` with `status: verified` + `last_verified`

### Install allowlist (operator machine)

Agents may install/verify **only** standard-stack components above. Document proof under `knowledge/research/`. Captain required for secrets, hardware flash, license click-through, or contract rejections — not for allowlisted `brew`/`npx` installs per [`agent-stack-autonomous-execution.md`](../../knowledge/decisions/agent-stack-autonomous-execution.md).

---

## Closed pilots (not in standard stack)

| Tool | Pilot outcome | Why not promoted | Follow-up |
|------|---------------|------------------|-----------|
| **Entire CLI** | Local pilot closed (unpromoted) | `entire enable --agent claude-code` used per runbook; npm **`entire-cli@0.0.3`** (registry latest 2026-07-13) lacks upstream hook surface — `entire --help` lists no `hooks`; `entire hooks claude-code` → `Unknown hooks subcommand: claude-code`; `entire rewind` empty | **CLOSED:** upgrade npm/Homebrew Entire before live lineage retest |
| **Ruflo** | Orchestration-only PASS in isolated worktree | Scorecard did not justify main-repo init; forbidden features out of scope | **CLOSED:** do **not** `ruflo init` on main `lane/*` branches |

Evidence: [`phase4-exit-gate-summary.md`](../../knowledge/research/phase4-exit-gate-summary.md).

---

## Closed benchmarks / future expansion (not rollout debt)

| Item | Status | Evidence |
|------|--------|----------|
| **Headroom compression** | **Compression benchmark PASS; operational qualification pending** — not in standard stack; no further Headroom testing this rollout | [`agent-stack-headroom-partial-2026-07-13.md`](../../knowledge/decisions/agent-stack-headroom-partial-2026-07-13.md) |
| **Entire `rewind` lineage** | Unpromoted — retest after Entire CLI > npm `0.0.3` (upstream: `entire enable --agent claude-code`) | [`agent-stack-entire-cli-limitation-2026-07-13.md`](../../knowledge/decisions/agent-stack-entire-cli-limitation-2026-07-13.md) |
| **Second-repo OpenKnowledge seed (P6-04)** | **Future expansion** — optional sibling-repo seed; not open debt for v1 | Phase 6 scorecard |

---

## Permanent rejections (binding)

| Tool / pattern | Verdict | Rationale |
|----------------|---------|-----------|
| **pxpipe** | **REJECT** | Silent exact-value corruption |
| **OmniRoute (primary gateway)** | **REJECT** | Lab only; no silent fallback for core work |
| **Ruflo full init** | **REJECT** | `--dual`, `--all-agents`, daemon, memory, RAG, SONA, federation |
| **Codex auto stop-gate** | **REJECT** | `reviewGateEnabled: true` forbidden |
| **Claude-mem → OpenKnowledge auto-sync** | **REJECT** | Violates promotion-not-sync curation model |

---

## Version pins (do not drift without decision doc)

```yaml
# OpenKnowledge — project MCP only
open_knowledge_npm: "@inkeep/open-knowledge@0.29.1"
content_dir: knowledge

# Codex plugin — manual invoke only
codex_plugin: "codex@openai-codex@1.0.6"
review_gate_enabled: false

# Herdr — operator visibility
herdr: "0.7.3"

# sqlite-utils — read-only operator snapshots
sqlite_utils: "3.39"

# Entire — pilot reference only (not standard stack)
entire_cli: "0.0.3"  # npm latest @ closure; unpromoted pilot

# Headroom — benchmark reference only (not standard stack)
headroom_ai: "0.31.0"  # compression-only probe; not installed for agents by default
```

---

## Configuration surfaces

| File | Purpose |
|------|---------|
| `.ok/config.yml` | OpenKnowledge `content.dir: knowledge`; `autoSync.enabled: null` |
| `.mcp.json` | Claude Code MCP servers (`open-knowledge` pinned) |
| `.cursor/mcp.json` | Cursor MCP (`open-knowledge` only) |
| `~/.claude/plugins/.../codex` | Codex companion; verify `reviewGateEnabled: false` |
| `scripts/agent/session-bootstrap.sh` | Prints agent-stack reminder + repo-truth |

**Forbidden config patterns:**

- User-global OpenKnowledge MCP registration
- `reviewGateEnabled: true` for Codex
- GitHub auto-sync jobs for `knowledge/`
- Cron/hooks copying claude-mem → `knowledge/`
- `RUFLO_DAEMON_AUTOSTART=1` or `ruflo init` on main firmware lanes

---

## Verification asset map (gates)

| Gate type | Tool | Phase |
|-----------|------|-------|
| Static / contract | pytest host harness (427+ tests) | Firmware |
| Build | `scripts/agent/pio-build.sh <env>` | Firmware |
| Lane integrity | `scripts/agent/repo-truth.sh` | Firmware + docs freshness |
| Coexistence | Phase 3 Tests 1–3 + P3-07 audit | Agent stack |
| Pilot isolation | Phase 4 Entire/Ruflo proofs | Agent stack |
| Compression benchmark | `scripts/agent/phase5-headroom-ab.py` | Agent stack (benchmark closed; not promoted) |

---

## Rollback (standard stack v1)

1. Revert `AGENT_OS.md` pointer to pre–Phase 6 wording if needed
2. Disable `open-knowledge` in `.mcp.json` / `.cursor/mcp.json` — retain `knowledge/` as plain Markdown
3. Disable Codex plugin / close Herdr workspace (no agent dependency)
4. Set affected decision frontmatter `status: rolled_back` — do not delete proof history

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-07-13 | agent:cursor | v1.0 — Phase 6 promotion; synthesizes Phases 0–5 scorecard |
