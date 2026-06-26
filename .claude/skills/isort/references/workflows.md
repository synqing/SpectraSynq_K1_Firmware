# isort Workflows Reference

## Contents
- Initial setup workflow
- CI integration
- Pre-commit hook setup
- Fixing a specific file
- Iterate-until-pass pattern

---

## Initial Setup Workflow

Copy this checklist when adding isort to the repo:

- [ ] Step 1: Install — `pip install isort` (or add to `requirements-dev.txt`)
- [ ] Step 2: Audit current state — `python -m isort --check-only --diff tests/ tools/ scripts/`
- [ ] Step 3: Add `pyproject.toml` config (profile + first-party declarations)
- [ ] Step 4: Fix all files — `python -m isort tests/ tools/ scripts/`
- [ ] Step 5: Verify no ruff `I` rule conflicts — `ruff check --select I tests/ tools/`
- [ ] Step 6: Commit the sorted files as a standalone "sort imports" commit (keeps diff reviewable)
- [ ] Step 7: Add pre-commit hook so it never drifts again

---

## CI Integration

For the existing `pre-commit` hook at `scripts/hooks/pre-commit`:

```bash
# new code to add — append to scripts/hooks/pre-commit
echo "--- isort check ---"
python -m isort --check-only --diff tests/ tools/ scripts/ || {
  echo "isort: imports need sorting. Run: python -m isort tests/ tools/ scripts/"
  exit 1
}
```

Or via `pyproject.toml` + standard pre-commit framework:

```yaml
# .pre-commit-config.yaml — new code to add
repos:
  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]
        files: ^(tests|tools|scripts)/
```

---

## Fixing a Specific File

Iterate-until-pass for a single harness file:

1. Check what would change:
   ```bash
   python -m isort --check-only --diff tools/tab5_k1_dashboard_harness.py
   ```
2. Apply the fix:
   ```bash
   python -m isort --profile black tools/tab5_k1_dashboard_harness.py
   ```
3. Verify clean:
   ```bash
   python -m isort --check-only tools/tab5_k1_dashboard_harness.py
   # exit 0 = clean
   ```
4. Run affected tests to confirm no import-order breakage:
   ```bash
   pytest tests/test_tab5_dashboard_harness.py -v
   ```

---

## Sorting All Test Files at Once

```bash
# Dry run — review diff before touching files
python -m isort --profile black --check-only --diff tests/

# Apply
python -m isort --profile black tests/

# Validate pytest still passes
pytest tests/ -v --tb=short
```

---

## Debugging Wrong Section Placement

When a module lands in the wrong section (e.g., local harness module sorted as third-party):

```bash
# Show isort's classification of each import in a file
python -m isort --show-config
python -m isort --only-sections tools/tab5_k1_dashboard_harness.py

# Force reclassify by adding to pyproject.toml:
# [tool.isort]
# known_first_party = ["tab5_k1_dashboard_harness"]
# src_paths = ["tools", "tests"]
```

After updating config, re-run the iterate-until-pass pattern above.