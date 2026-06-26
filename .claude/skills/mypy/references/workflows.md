# mypy Workflows Reference

## Contents
- Check-then-fix loop
- Incremental adoption on partially-annotated files
- CI gate integration
- Upgrading mypy

---

## Check-Then-Fix Loop

```
1. Run the gate:
   bun run check-types

2. If errors: open the first failing file, fix the narrowest type issue
3. Re-run:
   python -m mypy <file> --show-error-codes
4. Repeat until clean
5. Run full gate before committing:
   bun run check-types
```

Copy this checklist for a new file annotation pass:
- [ ] Add return type to every public function
- [ ] Annotate all function parameters
- [ ] Replace `dict` / `list` with typed variants (`dict[str, float]`, `list[int]`)
- [ ] Replace bare `Any` with `TypedDict` or `Protocol` where possible
- [ ] Run `python -m mypy <file> --strict` and resolve or suppress with codes
- [ ] Confirm `bun run check-types` passes

---

## Incremental Adoption

NEVER enable `--strict` repo-wide on a partially-annotated codebase — it generates hundreds of errors and stalls development.

**Per-module strict opt-in** (in `mypy.ini` or `pyproject.toml`):

```ini
# mypy.ini — new code to add
[mypy]
python_version = 3.9
warn_return_any = true
warn_unused_ignores = true

[mypy-scripts.regression-harness.*]
strict = true

[mypy-notebooks.*]
ignore_missing_imports = true
```

Enable strict per file as you annotate, not before.

---

## WARNING: Annotating Notebooks Directly

**The Problem:**

Running mypy directly on `.ipynb` files fails — mypy does not parse Jupyter format.

**Why This Breaks:**
1. mypy reads `.py` source only; notebooks are JSON
2. CI fails with parse errors, not type errors

**The Fix:**

Annotate the extracted helper module (`notebooks/diag_helpers.py`), not the notebook itself. Keep notebook cells thin; push typed logic into the helper.

```bash
# GOOD - check the helper, not the notebook
python -m mypy notebooks/diag_helpers.py --show-error-codes

# BAD - will fail
python -m mypy notebooks/audio_semantic_diagnostics.ipynb
```

---

## Upgrading mypy

Iterate-until-pass pattern:

```
1. Bump version in requirements / pyproject.toml
2. Run: bun run check-types
3. New errors from stricter inference → fix or add scoped suppression
4. New "unused ignore" warnings → remove stale suppressions
5. Repeat until clean
6. Commit with: "chore: upgrade mypy to X.Y.Z"
```

NEVER pin mypy to an old version to avoid fixing errors — stale suppressions accumulate and mask real bugs.

---

## Integration with ruff

Run ruff before mypy. ruff fixes import order and unused imports that mypy would report as errors or noise.

```bash
# Canonical order
ruff check --fix .
bun run check-types
```

See the **ruff** skill for ruff configuration patterns.