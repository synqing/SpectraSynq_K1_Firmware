# Ruff Workflows Reference

## Contents
- Pre-Commit Integration
- CI Gate Workflow
- Fixing a Dirty Codebase
- Ruff + pytest in One Pass

---

## Pre-Commit Integration

Ruff runs in milliseconds — suitable as a pre-commit hook that never slows the developer.

```yaml
# new code to add — .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0  # pin to a specific version
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**Iterate-until-pass:**
1. `git add` your changes
2. `git commit` triggers the hook
3. If ruff auto-fixes, the commit is blocked — review fixes, `git add` them, retry
4. Clean commit only when both `ruff check` and `ruff format` exit 0

---

## CI Gate Workflow

Add ruff as a mandatory CI step. Exit code is non-zero on violations — CI fails automatically.

```bash
# In CI script (e.g., GitHub Actions step or local gate)
ruff check . --output-format=github   # annotates PRs with inline comments
ruff format --check .                  # non-destructive format check
```

```yaml
# new code to add — GitHub Actions example
- name: Lint Python
  run: |
    pip install ruff
    ruff check . --output-format=github
    ruff format --check .
```

**DO:** Use `--output-format=github` in CI — it produces inline PR annotations.

**DON'T:** Use `--fix` in CI. Auto-modifying files in CI creates noise commits and hides the root cause. Fix locally, commit clean.

---

## Fixing a Dirty Codebase

When introducing ruff to an existing codebase with many violations:

```bash
# Step 1: See what you're dealing with
ruff check . --statistics

# Step 2: Fix everything ruff can fix safely
ruff check --fix .
ruff format .

# Step 3: Review remaining violations — decide rule-by-rule
ruff check . --select E501   # check one rule category at a time

# Step 4: For rules you can't fix now, add to ignore temporarily
# pyproject.toml: ignore = ["E501", "N802"]
# Add a TODO comment in pyproject.toml to track debt

# Step 5: Commit the bulk fix as a standalone commit (no logic changes)
git add -p  # review changes
git commit -m "chore: apply ruff auto-fixes"
```

**WARNING:** Never mix ruff bulk-fix commits with logic changes. Reviewers can't diff logic through a sea of whitespace changes.

---

## Ruff + pytest in One Pass

This repo gates on both linting and tests. Run them in sequence:

```bash
# Full local gate — mirrors CI
ruff check --fix . && ruff format . && pytest tests/ -v
```

**Checklist before pushing:**
- [ ] `ruff check .` exits 0
- [ ] `ruff format --check .` exits 0
- [ ] `pytest tests/ -v` exits 0 (see the **pytest** skill for test details)

**If ruff introduces a fix that breaks a test:** The fix changed semantics — use `--unsafe-fixes` output to identify it, revert that specific change, and add a targeted `# noqa` with a comment explaining why.

---

## Baseline Config for This Repo

```toml
# new code to add — pyproject.toml
[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "N"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F811", "F401"]
"tools/*" = ["T201"]
"scripts/*" = ["T201"]
```