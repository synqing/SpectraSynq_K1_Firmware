# clang-format Workflows

## Contents
- One-Shot Format Pass
- CI Format Gate
- Pre-commit Hook Integration
- Iterate-Until-Pass Loop
- Introducing clang-format to an Existing Codebase

---

## One-Shot Format Pass

Apply to all firmware sources excluding PlatformIO artifacts:

```bash
find . \( -name '*.cpp' -o -name '*.h' \) \
  ! -path './.pio/*' \
  ! -path './build/*' \
  | xargs clang-format -i
git diff --stat   # review scope before committing
```

Commit as a standalone "style: apply clang-format" commit. Never mix format changes with logic changes — it destroys `git blame` and makes review impossible.

---

## CI Format Gate

Check-only mode exits non-zero on any violation. Wire this before the build step so format failures surface immediately without burning a full PlatformIO compile.

```bash
# new code to add — suitable for GitHub Actions or local gate
FORMAT_TARGETS=$(find . \( -name '*.cpp' -o -name '*.h' \) \
  ! -path './.pio/*' ! -path './build/*')

echo "$FORMAT_TARGETS" | xargs clang-format --dry-run --Werror
if [ $? -ne 0 ]; then
  echo "Format violations found. Fix with:"
  echo "  echo \"\$FORMAT_TARGETS\" | xargs clang-format -i"
  exit 1
fi
```

---

## Pre-commit Hook Integration

The repo already has `scripts/hooks/pre-commit`. Add the format check there rather than creating a parallel hook file.

```bash
# Append to scripts/hooks/pre-commit — new code to add
STAGED_CPP=$(git diff --cached --name-only | grep -E '\.(cpp|h)$' | grep -v '\.pio/')
if [ -n "$STAGED_CPP" ]; then
  echo "$STAGED_CPP" | xargs clang-format --dry-run --Werror || {
    echo ""
    echo "  Fix: git diff --cached --name-only | grep -E '\\.(cpp|h)$' | xargs clang-format -i"
    exit 1
  }
fi
```

---

## Iterate-Until-Pass Loop

Copy this checklist for introducing or enforcing format compliance:

```
- [ ] Step 1: Verify clang-format is installed: `clang-format --version`
- [ ] Step 2: Confirm .clang-format exists at repo root (or create from patterns.md template)
- [ ] Step 3: Dry-run to assess scope: `find . \( -name '*.cpp' -o -name '*.h' \) ! -path './.pio/*' | xargs clang-format --dry-run --Werror 2>&1 | wc -l`
- [ ] Step 4: Apply in-place: `... | xargs clang-format -i`
- [ ] Step 5: Re-run dry-run — must exit 0 before proceeding
- [ ] Step 6: Review `git diff` — confirm no logic changes, only whitespace/style
- [ ] Step 7: Commit as isolated style commit
- [ ] Step 8: Add pre-commit gate so violations cannot re-enter
```

Validation loop:
1. Make changes or run format pass
2. Validate: `find . \( -name '*.cpp' -o -name '*.h' \) ! -path './.pio/*' | xargs clang-format --dry-run --Werror`
3. If validation fails, fix violations and repeat step 2
4. Only proceed when validation exits 0

---

## Introducing clang-format to an Existing Codebase

When the codebase has no `.clang-format` yet, do NOT apply a style blindly — the first pass will produce a multi-thousand-line diff that buries real changes.

1. **Agree on style** — pick `BasedOnStyle` before touching files. `LLVM` is the least surprising for ESP-IDF / Arduino C++ projects.
2. **Single commit, whole tree** — format everything in one atomic commit labelled `style: initial clang-format pass`. Future commits stay clean.
3. **Update git blame ignore** — add the format commit SHA to `.git-blame-ignore-revs`:
   ```bash
   echo "<format-commit-sha>" >> .git-blame-ignore-revs
   git config blame.ignoreRevsFile .git-blame-ignore-revs
   ```
4. **Lock it in** — add the pre-commit gate immediately so the codebase never drifts again.