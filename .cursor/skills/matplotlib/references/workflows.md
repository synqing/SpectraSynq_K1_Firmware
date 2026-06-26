# Matplotlib Workflows Reference

## Contents
- Adding a New Diagnostic Plot to diag_helpers.py
- Running Plots in Headless Notebook (CI)
- A/B Comparison Workflow
- Saving a Multi-Panel Report Figure
- Iterate-Until-Pass Validation

---

## Adding a New Diagnostic Plot to diag_helpers.py

The project centralizes plot helpers in `notebooks/diag_helpers.py`. Before writing a new plot function, check if one exists:

```bash
grep -n "^def plot_" notebooks/diag_helpers.py
```

If extending:

1. Add your function following the return-fig contract (see patterns.md).
2. Import and call it from the notebook cell — do not inline plot code in notebook cells.
3. Validate output is saved correctly in headless mode.

**Copy this checklist:**
- [ ] Check `diag_helpers.py` for existing similar function
- [ ] Write function with `fig, ax = plt.subplots()` pattern
- [ ] Function accepts `out_path=None` and returns `fig`
- [ ] Call `plt.close(fig)` before returning
- [ ] Test in headless context: `jupyter nbconvert --to notebook --execute notebooks/audio_semantic_diagnostics.ipynb`
- [ ] Verify output PNG exists and is not blank

---

## Running Plots in Headless Notebook (CI)

```bash
# Execute notebook non-interactively, save outputs
jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=120 \
  notebooks/audio_semantic_diagnostics.ipynb \
  --output notebooks/audio_semantic_diagnostics_executed.ipynb
```

If this fails with a display error, the notebook is calling `plt.show()` — find and remove all calls:

```bash
grep -n "plt.show" notebooks/*.ipynb notebooks/*.py
```

**Iterate-until-pass:**
1. Run nbconvert command above
2. If error contains `cannot connect to X server` or `_tkinter`: add `matplotlib.use('Agg')` at top of helper imports
3. If error contains `plt.show`: remove the call, replace with `fig.savefig(...)` + `plt.close(fig)`
4. Repeat until notebook executes cleanly

---

## A/B Comparison Workflow

Used in this project to compare `sb_tempo` final vs baseline (see `notebooks/audio_semantic_diagnostics.ipynb`):

```python
# new code to add
def plot_ab_comparison(a_data, b_data, labels=('Baseline', 'Final'),
                       title='A/B Comparison', out_path=None):
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    for ax, data, label in zip(axes, (a_data, b_data), labels):
        ax.plot(data, linewidth=0.8)
        ax.set_title(label)
        ax.set_ylabel('Value')
    axes[-1].set_xlabel('Frame')
    fig.suptitle(title)
    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return fig
```

---

## Saving a Multi-Panel Report Figure

For forensic/measurement reports (e.g., `docs/measurements/`):

```python
# new code to add
def save_report_figure(panels, out_path, title='Diagnostic Report'):
    """
    panels: list of (x, y, label) tuples
    """
    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(14, 3 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (x, y, label) in zip(axes, panels):
        ax.plot(x, y, linewidth=0.8, label=label)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return out_path
```

Place outputs under `docs/measurements/` or `docs/forensics/` — never at project root.

---

## Common Errors and Solutions

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot connect to X server` | pyplot importing with Tk backend | `matplotlib.use('Agg')` before pyplot |
| Blank/white PNG | `plt.close(fig)` called before `savefig` | Save first, then close |
| Axes overlap | Missing `tight_layout()` | Add `fig.tight_layout()` before save |
| `plt.show()` hangs | Blocking call in headless kernel | Remove all `plt.show()` from helpers |
| Plot shows previous data | pyplot state machine reuse | Switch to `fig, ax = plt.subplots()` |

See the **numpy** skill for array construction, and the **jupyter** skill for notebook execution context.