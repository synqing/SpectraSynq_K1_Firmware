# Black Formatting Patterns

## Contents
- String Normalization
- Magic Trailing Comma
- Long Expressions
- Anti-Patterns
- Notebook Handling

---

## String Normalization

Black always converts to double quotes. Do not fight this.

```python
# BAD — black will rewrite these
label = 'tempo_novelty'
msg = 'confidence=%f' % conf

# GOOD — write double quotes from the start
label = "tempo_novelty"
msg = f"confidence={conf:.3f}"
```

**Why:** Single-quote drift in a codebase means every black run produces noisy diffs. Start with double quotes and diffs stay clean.

---

## Magic Trailing Comma

Black respects a trailing comma as an explicit "keep this expanded" signal.

```python
# Without trailing comma — black may collapse to one line
result = compute_onset(
    band=band,
    threshold=threshold
)
# → result = compute_onset(band=band, threshold=threshold)

# With trailing comma — black always expands
result = compute_onset(
    band=band,
    threshold=threshold,  # trailing comma = always multiline
)
```

**Use trailing commas in:**
- Function signatures with 3+ parameters
- Dict/list literals you want to keep readable
- Import groups

---

## Long Expressions in DSP Code

Black wraps long lines at 88 chars. Do not pre-wrap manually — let black do it.

```python
# BAD — manual wrapping that black will reformat anyway
confidence = (periodicity_score * 0.6 +
              onset_density * 0.3 +
              flux_peak * 0.1)

# GOOD — write naturally, let black wrap
confidence = periodicity_score * 0.6 + onset_density * 0.3 + flux_peak * 0.1

# For very long expressions, use parens to give black room
confidence = (
    periodicity_score * PERIODICITY_WEIGHT
    + onset_density * DENSITY_WEIGHT
    + flux_peak * FLUX_WEIGHT
)
```

---

## WARNING: Mixing Black and Manual Formatting

**The Problem:**

```python
# BAD — hand-formatted alignment that black destroys
gains = {
    "bass"  : 0.8,
    "mid"   : 1.0,
    "treble": 1.2,
}
```

**Why This Breaks:**
1. Black normalizes dict spacing — your alignment disappears on every run.
2. Pre-commit hooks reformat the file, causing a dirty working tree in CI.
3. Reviewers see spurious formatting diffs mixed with logic diffs.

**The Fix:**

```python
# GOOD — write what black would produce
gains = {
    "bass": 0.8,
    "mid": 1.0,
    "treble": 1.2,
}
```

---

## Notebook Cell Formatting

Black does not process `.ipynb` files natively — use `nbqa`.

```bash
# Check notebook
nbqa black notebooks/audio_semantic_diagnostics.ipynb --check

# Format notebook
nbqa black notebooks/audio_semantic_diagnostics.ipynb

# Format all notebooks
nbqa black notebooks/
```

**WARNING:** `nbqa` rewrites cell source in-place. Commit before running if the notebook has unsaved output you care about. Notebook outputs are not affected — only cell source code.

---

## `# fmt: off` / `# fmt: on` Escape Hatches

Use sparingly for genuinely unformattable code (lookup tables, matrices).

```python
# Acceptable use — structured numerical data
# fmt: off
OCTAVE_CENTERS = [
    32.7,   65.4,  130.8,  261.6,
    523.3, 1046.5, 2093.0, 4186.0,
]
# fmt: on

# BAD use — avoiding black because you prefer a style
# fmt: off
x=1; y=2; z=3  # don't do this
# fmt: on
```