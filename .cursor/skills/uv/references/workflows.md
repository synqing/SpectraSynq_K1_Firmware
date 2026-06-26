# uv Workflows Reference

## Contents
- New Project Setup
- Adding / Removing Dependencies
- CI Configuration
- Migrating from requirements.txt
- Notebook Environment (this repo)

---

## New Project Setup

```bash
# Initialize pyproject.toml (if missing)
uv init

# Pin Python version
uv python pin 3.11

# Create lockfile and venv
uv sync

# Verify
uv run python --version
```

Copy this checklist:
- [ ] `pyproject.toml` has `[project]` and `[dependency-groups]` sections
- [ ] `.python-version` committed
- [ ] `uv.lock` committed
- [ ] `.venv/` in `.gitignore`

---

## Adding / Removing Dependencies

```bash
# Add runtime dep
uv add scipy

# Add dev dep
uv add --dev pytest-xdist

# Remove dep
uv remove scipy

# After any add/remove, verify tests still pass
uv run pytest tests/ -v
```

Iterate until pass:
1. `uv add <package>`
2. `uv run pytest tests/ -v`
3. If tests fail, investigate import errors or version conflicts
4. Only commit `pyproject.toml` + `uv.lock` together when tests pass

---

## CI Configuration

```yaml
# GitHub Actions example
- name: Install uv
  uses: astral-sh/setup-uv@v4

- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest tests/ -v
```

Key rules for CI:
- Always `--frozen` on `uv sync` — fail fast if lockfile is stale
- Never `uv add` in CI — only `uv sync`
- Cache `.venv` by hashing `uv.lock` for faster runs

---

## Migrating from requirements.txt

```bash
# Import existing requirements into pyproject.toml
uv add $(cat requirements.txt | grep -v '^#' | tr '\n' ' ')

# Or use pip compat layer for complex requirements files
uv pip install -r requirements.txt

# Freeze current env into lockfile
uv lock
```

**WARNING:** `requirements.txt` files often have unpinned or conflicting deps. After migration:
1. Run `uv run pytest tests/ -v`
2. Fix any resolution errors reported by uv
3. Delete `requirements.txt` once `uv.lock` is stable — don't maintain both

---

## Notebook Environment (this repo)

This repo uses Jupyter notebooks in `notebooks/` for audio diagnostics. See the **jupyter** skill for notebook patterns.

```bash
# Install notebook deps
uv add --dev jupyter ipykernel matplotlib plotly pandas

# Launch notebook in managed env
uv run jupyter notebook notebooks/audio_semantic_diagnostics.ipynb

# Run notebook non-interactively (CI diagnostics)
uv run jupyter nbconvert --to notebook --execute notebooks/audio_semantic_diagnostics.ipynb
```

**Why `uv run jupyter` not `jupyter notebook` directly:**
- Ensures the notebook kernel uses the project venv, not whatever Python is on PATH
- Prevents "import numpy works in terminal but not in notebook" failures caused by mismatched kernels

See the **numpy**, **scipy**, **matplotlib**, and **plotly** skills for the analysis libraries used in this repo's diagnostic notebooks.