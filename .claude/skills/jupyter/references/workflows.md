# Jupyter Workflows Reference

## Contents
- Diagnostic run workflow
- Adding a new diagnostic series
- A/B comparison workflow
- CI-safe notebook execution

## Diagnostic Run Workflow

Copy this checklist and track progress:

- [ ] Set `matplotlib.use('Agg')` as first statement in import cell
- [ ] Run `apstream_ingest.py` to parse the AP stream log into a DataFrame
- [ ] Apply `window_mask` to isolate the capture window of interest
- [ ] Call `plot_ap_capture_summary()` and `plot_agc_debug()` from `diag_helpers.py`
- [ ] Save all figures to `notebooks/output/` with descriptive filenames
- [ ] Call `plt.close('all')` at end of notebook
- [ ] Run `jupyter nbconvert --to notebook --execute` to verify clean top-to-bottom execution

## Adding a New Diagnostic Series

1. **Add parser support** in `scripts/regression-harness/apstream_ingest.py` — add the new field to the row parser, handle missing values with NaN fill.

2. **Add helper** in `notebooks/diag_helpers.py` following the `plot_<series>(df, window_mask=None, ax=None)` convention.

3. **Add cell** in `notebooks/audio_semantic_diagnostics.ipynb` using `NotebookEdit`.

4. **Validate:**
   ```bash
   jupyter nbconvert --to notebook --execute notebooks/audio_semantic_diagnostics.ipynb \
     --output /tmp/diag_test_out.ipynb
   # Check exit code 0; inspect /tmp/diag_test_out.ipynb for errors in output cells
   ```

5. If validation fails, fix the parse/plot function and repeat step 4.

## A/B Comparison Workflow

Used to compare `sb_tempo Final` vs baseline (pattern from existing notebook):

```python
# new code to add — A/B overlay pattern
fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

plot_ap_capture_summary(df_baseline, window_mask=mask_baseline, ax=axes[0])
axes[0].set_title('Baseline')

plot_ap_capture_summary(df_final, window_mask=mask_final, ax=axes[1])
axes[1].set_title('Final (sb_tempo V2)')

fig.tight_layout()
fig.savefig('notebooks/output/ab_comparison.png', dpi=150, bbox_inches='tight')
plt.close(fig)
```

**Scalar summary pattern** (for commit-reportable metrics):

```python
metrics = {
    'density_in_band_baseline': df_baseline['density_in_band'].mean(),
    'density_in_band_final': df_final['density_in_band'].mean(),
}
# Print only — no figure. Scalars go in notebook output, not saved files.
print(metrics)
```

## CI-Safe Notebook Execution

NEVER depend on notebook state from a previous interactive session. For regression harness integration:

```bash
# Clear all outputs before committing
jupyter nbconvert --ClearOutputPreprocessor.enabled=True \
  --to notebook notebooks/audio_semantic_diagnostics.ipynb \
  --output notebooks/audio_semantic_diagnostics.ipynb

# Execute fresh
jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=120 \
  notebooks/audio_semantic_diagnostics.ipynb \
  --output notebooks/audio_semantic_diagnostics_executed.ipynb
```

**Why clear first:** stale cell outputs in committed `.ipynb` cause spurious diffs and can mask regressions by making a broken notebook appear to have valid output.

## WARNING: Notebook State Pollution

**The Problem:** Running cells out of order leaves hidden state. A cell that worked interactively fails in CI because it depends on a variable defined in a cell run earlier — but not above it in file order.

**The Fix:** After any interactive session, always run the full notebook top-to-bottom via `nbconvert --execute` before committing. If it fails non-interactively, the notebook is broken regardless of what the interactive session showed.

## Related Skills

- See the **python** skill for data processing patterns
- See the **matplotlib** skill for figure configuration
- See the **pandas** skill for DataFrame manipulation in ingest scripts
- See the **pytest** skill for integrating notebook outputs into regression gates