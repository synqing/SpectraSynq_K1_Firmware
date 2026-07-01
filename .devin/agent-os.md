# Devin Agent OS Overlay — SpectraSynq K1 Firmware

**Read [`AGENT_OS.md`](../../AGENT_OS.md) first.** It is the canonical,
tool-agnostic manual (bootstrap, source-of-truth, safety, gates, thinking gate,
skill awareness). This file is the Devin-specific overlay only.

---

## Devin-specific permissions

`.devin/config.local.json` (gitignored, local-only) controls what shell commands
Devin auto-approves vs asks vs denies. Current posture:

- **allow:** `python3`, `pytest`, read-only `git` (`status`/`log`/`diff`/`rev-parse`/`ls-files`), `bash scripts/agent/session-bootstrap.sh`, `bash scripts/agent/repo-truth.sh`
- **ask:** `bash scripts/agent/pio-build.sh` (host build — prompt every time), `git config` (could mutate `core.hooksPath`)
- **deny:** all `pio run --target upload` / `-t upload` forms, `pio device`, `pio device monitor`, `erase_flash`

This is local-only, not shared repo policy. Shared policy would require `.devin/config.json` (do not create without explicit approval).

---

## Devin environment setup

The Devin git-backed blueprint lives at `.devin/blueprint.yaml`. It is a
knowledge-only draft: it documents the repo's safe-command surface and does not
install speculative packages, call sync/build APIs, or configure hardware
access. Sync + build are triggered separately via Devin API/UI after the file
is committed to the default branch.

Reference: https://docs.devin.ai/onboard-devin/environment/git-backed-blueprints

---

## Guarded build wrapper

Devin cannot safely use `Exec(pio run -e ...)` directly because Devin `Exec(prefix)`
permissions match commands that start with the prefix, allowing appended arguments.
Use the wrapper instead:

```bash
bash scripts/agent/pio-build.sh k1_hardware
bash scripts/agent/pio-build.sh k1_bench_reference
bash scripts/agent/pio-build.sh k1_bench_im73d
```

The wrapper allowlist-exact-matches the env and rejects `upload`/`--target`/`-t`/
`erase`/`monitor`/`device`/shell-metacharacters. Direct `pio run` is not permitted
from Devin sessions.

---

Last updated: 2026-07-02
