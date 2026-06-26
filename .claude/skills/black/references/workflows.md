# Black Formatting Workflows

## Contents
- Initial Formatting Run
- Pre-commit Integration
- CI Gate
- Notebook Workflow
- Iterate-Until-Pass Pattern

---

## Initial Formatting Run

When black is first introduced to an existing codebase, treat it as a single formatting commit — separate from logic changes.

```bash
# 1. See what would change (no writes)
black --check --diff scripts/ notebooks/diag_helpers.py

# 2. Apply all formatting
black scripts/ notebooks/diag_helpers.py
nbqa black notebooks/

# 3. Verify clean
black --check scripts/ notebooks/diag_helpers.py

# 4. Commit as formatting-only
git add -p  # or git add scripts/ notebooks/diag_helpers.py
git commit -m "style: apply black formatting"
```

**Never mix black formatting with logic changes in the same commit.** Reviewers cannot separate intent from style noise.

---

## Pre-commit Integration

```yaml
# new code to add — .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.3.0  # match installed version
    hooks:
      - id: black
        files: ^(scripts|notebooks)/.*\.py$
      - id: black-jupyter
        files: ^notebooks/.*\.ipynb$
```

Install and verify:

```bash
pre-commit install
pre-commit run black --all-files
```

**WARNING:** If `black-jupyter` is not in your pre-commit config but `.ipynb` files exist, notebooks will drift out of compliance silently. Add both hooks or neither.

---

## CI Gate

```bash
# new code to add — add to CI script or Makefile
.PHONY: check-format
check-format:
	black --check scripts/ notebooks/diag_helpers.py
	nbqa black --check notebooks/

.PHONY: format
format:
	black scripts/ notebooks/diag_helpers.py
	nbqa black notebooks/
```

The gate must use `--check` (exits non-zero on violations) — never run `black` without `--check` in CI, or the runner will reformat files and the diff is lost.

---

## Notebook Formatting Workflow

Notebooks require extra care because outputs are stored alongside source.

```bash
# 1. Commit current notebook state (including outputs)
git add notebooks/audio_semantic_diagnostics.ipynb
git commit -m "wip: save notebook outputs before format"

# 2. Format source cells only
nbqa black notebooks/audio_semantic_diagnostics.ipynb

# 3. Verify only source changed (outputs untouched)
git diff notebooks/audio_semantic_diagnostics.ipynb

# 4. If clean, commit
git add notebooks/audio_semantic_diagnostics.ipynb
git commit -m "style: black-format notebook cells"
```

For `diag_helpers.py` (plain Python, not a notebook), black runs directly:

```bash
black notebooks/diag_helpers.py
```

---

## Iterate-Until-Pass Pattern

For CI failures or pre-commit rejections:

1. Run check to see violations:
   ```bash
   black --check --diff scripts/ notebooks/diag_helpers.py
   ```
2. Apply formatting:
   ```bash
   black scripts/ notebooks/diag_helpers.py
   ```
3. Validate clean:
   ```bash
   black --check scripts/ notebooks/diag_helpers.py
   ```
4. If step 3 still fails, a `# fmt: off` block may be resisting — investigate with `--diff`.
5. Repeat until `black --check` exits 0.

---

## Integration with ruff

If the **ruff** skill is also active, be aware of overlap. Ruff includes a black-compatible formatter (`ruff format`) that can replace black entirely. Running both produces conflicts.

**Choose one:**
- `black` + `ruff` (linting only, `select` excludes `E501`/formatting rules)
- `ruff format` only (drops black dependency)

Do not configure both `black` and `ruff format` in pre-commit — you will get a reformat loop.