---
abstract: "Pre- and post-upgrade checklist for claude-mem 12.4.9 → 13.4. Repo-local spec routing (docs/spec-index.md) survives upgrade; this doc covers ~/.claude-mem operations only."
---

# claude-mem Pre-13.4 Upgrade Checklist

Repo-local spec accessibility (`docs/spec-index.md`, `.claude/handoff.md`, `progress.md`) does **not** require claude-mem version alignment. This checklist covers the memory worker and corpora only.

## Before upgrade (optional safety)

```bash
cp ~/.claude-mem/claude-mem.db ~/.claude-mem/backups/pre-13.4-manual.db
cp -r ~/.claude-mem/corpora ~/.claude-mem/backups/corpora-pre-13.4/
```

Record current worker version:

```bash
curl -sf http://127.0.0.1:37777/api/version
curl -sf http://127.0.0.1:37777/api/health
```

## Upgrade

Follow upstream install path (`npx claude-mem install` or marketplace plugin update to 13.4.x). Worker will restart; expect new `worker.pid`.

## After upgrade (required)

### 1. Verify worker

```bash
curl -sf http://127.0.0.1:37777/api/version
curl -sf http://127.0.0.1:37777/api/health
curl -sf http://127.0.0.1:37777/api/pending-queue
~/.claude/hooks/claude-mem-freshness-check.sh   # if installed
```

### 2. Rebuild corpora (structured filters)

Pre-13.4 corpora were empty (query-only builds failed validation on 12.4.9). Rebuild with `project` + `files` + `dateStart`:

**K1 secondary / Dense Forge forensic corpus:**

```
build_corpus
  name="k1_secondary_throttle_forensics"
  description="K1 secondary dark + Dense Forge forensic context"
  project="SensoryBridge-main 9"
  files="SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp,SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp,docs/handover/,docs/forensics/runtime-evidence/"
  types="bugfix,discovery,change,refactor"
  dateStart="2026-06-06"
  limit=200
```

Then:

```
prime_corpus name="k1_secondary_throttle_forensics"
```

Repeat `reprime_corpus` after significant new observations land.

### 3. Codex capture (13.3+)

13.3 disabled default Codex JSONL transcript replay in favour of native hooks. If Codex sessions stop producing observations:

- Confirm `~/.codex/config.toml` has hooks enabled per upstream docs
- Or set `CLAUDE_MEM_CODEX_TRANSCRIPT_INGESTION=true` in `~/.claude-mem/settings.json` to restore legacy watcher

### 4. MCP tool namespace

Re-verify tool names in `.claude/agents/*.md` match the post-upgrade MCP registration (13.3 fixed duplicate `mcp-search` warnings). Workflow unchanged: `search` → `timeline` → `get_observations`.

### 5. LiteLLM gateway (if used)

Captain's gateway on port 4000 is independent of plugin upgrade. After upgrade, confirm `CLAUDE_MEM_CLAUDE_AUTH_METHOD=gateway` still works:

```bash
curl -sf http://127.0.0.1:4000/health
```

### 6. Update spec-index maintenance note

Bump worker version line in [`docs/spec-index.md`](../spec-index.md) §Recall conventions when verification passes.

## What carries over automatically

| Asset | Location | Notes |
|-------|----------|-------|
| Observation DB | `~/.claude-mem/claude-mem.db` | Schema migrations on worker boot |
| Settings | `~/.claude-mem/settings.json` | Overrides new defaults |
| Corpus JSON files | `~/.claude-mem/corpora/` | On disk; rebuild content |
| Repo spec index | `docs/spec-index.md` | Version-proof |

## What does not carry over

- Primed corpus SDK `session_id` — run `reprime_corpus` after upgrade
- Stale operational observations (worker down, route 404) — verify live per session
