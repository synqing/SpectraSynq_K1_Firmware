# Matplotlib Patterns Reference

## Contents
- Backend and Import Discipline
- Figure/Axes API vs pyplot State Machine
- Headless Save Pattern
- Time-Series and Spectrum Plots
- Anti-Patterns

---

## Backend and Import Discipline

ALWAYS set backend before importing pyplot in scripts and non-notebook Python:

```python
import matplotlib
matplotlib.use('Agg')  # must precede pyplot import
import matplotlib.pyplot as plt
```

In Jupyter notebooks, use the inline magic instead:
```python
%matplotlib inline
import matplotlib.pyplot as plt
```

**WARNING:** `plt.show()` silently fails in headless Jupyter kernels (confirmed issue in this project — see `notebooks/audio_semantic_diagnostics.ipynb`). Never call it in diagnostic helpers. Save to file or return the figure.

---

## Figure/Axes API (ALWAYS use this)

```python
# GOOD — explicit, composable, testable
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(x, y)
ax.set_title('Tempo Confidence')
ax.set_xlabel('Frame')
ax.set_ylabel('Confidence')
fig.tight_layout()
fig.savefig('out.png', dpi=150, bbox_inches='tight')
plt.close(fig)
```

### WARNING: pyplot State Machine

**The Problem:**
```python
# BAD — relies on implicit global figure state
plt.plot(x, y)
plt.title('Something')
plt.savefig('out.png')
```

**Why This Breaks:**
1. In loops or multi-function notebooks, the "current figure" is unpredictable — plots accumulate on the wrong figure.
2. No handle to close the figure → memory leak over many diagnostic runs.
3. Not composable into helper functions — callers can't pass `ax` or `fig`.

**The Fix:** Always use `fig, ax = plt.subplots()` and pass `ax` explicitly.

---

## Headless Save Pattern

Every plot helper in this project must follow this contract:

```python
def plot_something(data, out_path: str | None = None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(12, 4))
    # ... plotting logic ...
    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return fig
```

- Return `fig` so callers can embed in subplots or capture in notebooks.
- `plt.close(fig)` immediately after save — never rely on GC.
- `bbox_inches='tight'` prevents axis label clipping.

---

## Time-Series and Spectrum Plots (project-relevant)

Audio diagnostic plots in this project use frame index or time-in-seconds on x-axis:

```python
# new code to add
def plot_tempo_confidence(frames, confidence, fs_frames=44.4, out_path=None):
    """Plot tempo confidence over time (44.4 Hz novelty rate)."""
    fig, ax = plt.subplots(figsize=(12, 3))
    t = np.arange(len(frames)) / fs_frames
    ax.plot(t, confidence, color='steelblue', linewidth=0.9)
    ax.axhline(0.60, color='red', linestyle='--', linewidth=0.8, label='lock threshold')
    ax.set_ylim(0, 1)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Confidence')
    ax.set_title('Tempo Confidence (PLL)')
    ax.legend()
    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return fig
```

For multi-band spectrum (24 octave bands):

```python
# new code to add
def plot_octave_spectrum(band_matrix, title='Octave Spectrum', out_path=None):
    """band_matrix shape: (n_frames, 24)"""
    fig, ax = plt.subplots(figsize=(12, 5))
    im = ax.imshow(band_matrix.T, aspect='auto', origin='lower',
                   cmap='inferno', vmin=0, vmax=1)
    ax.set_xlabel('Frame')
    ax.set_ylabel('Band')
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    if out_path:
        fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return fig
```

---

## Anti-Patterns

### WARNING: Figures Accumulating in Memory

**The Problem:** Creating figures in a loop without closing them.

```python
# BAD
for track in tracks:
    plt.figure()
    plt.plot(track.data)
    plt.savefig(f'{track.name}.png')
# 100 tracks = 100 open figures still in memory
```

**The Fix:**
```python
for track in tracks:
    fig, ax = plt.subplots()
    ax.plot(track.data)
    fig.savefig(f'{track.name}.png', bbox_inches='tight')
    plt.close(fig)
```

### WARNING: Hardcoded Figure Size

Match figure size to output context. Diagnostic notebooks render at ~800px wide; use `figsize=(10-12, 3-5)` for inline display. Full-page exports use `figsize=(16, 9)`.