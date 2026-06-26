# uv Patterns Reference

## Contents
- Lockfile Discipline
- Dev vs Prod Dependency Split
- Python Version Pinning
- Escape Hatches
- Anti-Patterns

---

## Lockfile Discipline

`uv.lock` is the source of truth for reproducible installs. Commit it. Never hand-edit it.

```bash
# Generate/update lockfile after changing pyproject.toml
uv lock

# Install exactly what lockfile says (CI, deploy)
uv sync --frozen

# Update a specific package
uv lock --upgrade-package numpy
```

**NEVER run `uv sync` without `--frozen` in CI.** Without it, uv will silently re-resolve if the lockfile is absent, producing a non-reproducible build that passes locally and breaks in production.

---

## Dev vs Prod Dependency Split

```toml
# pyproject.toml
[project]
dependencies = [
    "numpy>=1.26",
    "scipy>=1.12",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "ruff",
    "jupyter",
    "ipykernel",
]
```

```bash
# Production install (no dev deps)
uv sync --no-dev

# Full install including dev
uv sync
```

Keep test and notebook deps in `[dependency-groups] dev`. Production firmware companion scripts must not drag in 200 MB of Jupyter on the target machine.

---

## Python Version Pinning

```bash
# Pin to a specific Python (written to .python-version)
uv python pin 3.11

# Install that Python if not present
uv python install 3.11
```

Commit `.python-version`. Without it, different developers get different Pythons and `uv sync` produces different envs silently.

---

## Escape Hatches

When a package isn't in PyPI or needs special flags, use `uv pip` as a pip-compatible layer:

```bash
# Install editable local package
uv pip install -e ./scripts/regression-harness

# Install from a git ref
uv pip install git+https://github.com/org/repo@main
```

`uv pip` still writes into the uv-managed venv — it does NOT bypass the venv.

---

## WARNING: Mixing pip and uv

**The Problem:**
```bash
# BAD — activating venv then using system pip
source .venv/bin/activate
pip install requests
```

**Why This Breaks:**
1. Bypasses uv lockfile — install is not recorded in `uv.lock`
2. Next `uv sync` may remove the package or pin a conflicting version
3. CI will have a different environment than local

**The Fix:**
```bash
# GOOD — always go through uv
uv add requests        # for project deps
uvx requests-cache     # for one-off tools
uv pip install ...     # only when uv add can't handle it
```

---

## WARNING: Global Tool Pollution

**The Problem:**
```bash
# BAD — installs ruff globally
pip install ruff
ruff check .
```

**Why This Breaks:**
1. Tool version not pinned to project
2. Conflicts with other projects' tools
3. Breaks on machines where pip installs to user site-packages

**The Fix:**
```bash
# GOOD — ephemeral, version-pinned
uvx ruff check .

# Or pin in dev deps
uv add --dev ruff
uv run ruff check .
```