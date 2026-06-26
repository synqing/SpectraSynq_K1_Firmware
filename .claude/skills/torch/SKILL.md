---
name: torch
description: |
  Project-specific torch (PyTorch) workflow guidance for SensoryBridge K1.
  Use when: writing offline audio analysis scripts, validating DSP algorithms against ML baselines, training beat/onset models, or running torch-based regression harnesses against K1 audio pipeline outputs.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, mcp__plugin_context-mode_context-mode__ctx_batch_execute, mcp__plugin_context-mode_context-mode__ctx_execute, mcp__plugin_context-mode_context-mode__ctx_search
---

# Torch Skill

PyTorch in this project is a **host-side analysis tool only** — it never runs on the ESP32. Use it for offline DSP validation (comparing Goertzel GDFT output against STFT/mel baselines), beat/onset regression against captured K1 audio fixtures, or training lightweight models whose outputs are baked into firmware constants. The firmware DSP (Goertzel, PLL, onset flux) is the ground truth; torch is a verification and exploration layer.

## Before You Code (REQUIRED)

This skill's content was captured at generation time and MAY be stale. For ANY non-trivial change involving torch, verify against current docs FIRST:



Then:

1. **Match the installed version.** Cross-reference against the version installed in this repo. APIs change across minor versions; do not assume.
2. **Discover provider best practices.** If the task touches a production-sensitive capability, inspect the provider service catalog, official docs, and project docs before choosing an implementation.
3. **Respect explicit direction.** If the user explicitly asks for a specific mechanism, follow it. If project docs clearly mandate a mechanism, follow the project. In both cases, mention the provider-recommended alternative and make the chosen path safe.
4. **Prefer provider-native primitives by default.** If no explicit user/project override exists and the change involves caching, rate limiting, background work, scheduled jobs, shared state, queues, or secrets, use the provider-recommended binding/API. Do not hand-roll an in-memory or polyfill solution that "works" locally but breaks under the provider's execution model — derive the need→native-primitive mapping yourself from this provider's docs.

## Skill Advantage Protocol

Using this skill should produce a meaningfully better result than an unskilled baseline. Apply this loop before and during implementation:

1. **Clarify only when it changes the outcome.** Ask the smallest useful set of questions when the request is ambiguous, preference-heavy, or could change architecture, user-visible behavior, data shape, security posture, analytics, or external side effects. If the safe assumption is obvious, state it and proceed. When asked to surface data that no existing code path captures, state up front the assumption that capture starts now (no backfill) or ask if a backfill source exists — do not silently build net-new storage without surfacing this.
2. **Inspect the nearest real patterns.** Read adjacent files, routes, components, tests, schema, infra, copy, and analytics surfaces before inventing structure. Treat local conventions as the starting point.
3. **Optimize the task's highest-leverage axis.** Identify what would make the result win a review: user-visible correctness, integration quality, accessibility, security, reliability, maintainability, operability, or speed of future change.
4. **Reuse before reimplementing.** Prefer existing components, hooks, helpers, formatting/utility functions, data registries, metadata builders, analytics, pricing, checkout, auth, routing utilities, and API procedures/endpoints/data sources over local one-off clones. Before adding a new API procedure, query, or data fetch, search for one that already returns this data and extend it in place — a surface that fetches data and only logs or partially uses it is a reuse target, not an absent one; never author a parallel endpoint or leave the original orphaned. Before importing for a data fetch, grep the screen for the call it already makes and reuse that exact client/singleton import path and endpoint/procedure name; never create a second client, transport, or parallel endpoint for data an existing call returns, and confirm every imported path and symbol actually exists in the repo before writing it.
5. **Use semantic structures.** Tables, lists, forms, buttons, links, headings, and disclosure controls should use native/project accessible primitives instead of div-only lookalikes.
6. **Prevent drift by construction.** Centralize repeated facts, labels, claims, product defaults, and shared table cells in registries or helpers when multiple surfaces need the same answer.
7. **Synthesize, do not merely comply.** Combine this skill's guidance with repo evidence and the user's goal. When two good approaches exist, borrow the strongest parts of each instead of blindly choosing one.
8. **Check claims against code.** Product copy, docs, and comments must not imply automation, integrations, performance, security, refresh cadence, counts, or data flow that the implementation does not actually provide. Any claim that one component writes, records, updates, calls, or is the source of truth for another is allowed only if the edit performing it is in this same change; before finishing, check each such cross-component claim against the actual edits and downgrade unbacked ones to an explicit TODO or implement them now.
9. **Ship the complete slice.** Include every adjacent artifact needed for the change to be usable and maintainable: wiring, state handling, validation, analytics, tests, docs, migrations, or infra when those surfaces are part of the behavior. When the task shows, displays, or lists user data, deliver the full vertical slice and do not stop at an internal/API/CLI layer: the data-model/schema change AND its migration (a schema change without a migration is incomplete), the path that writes or populates the data, an authenticated endpoint scoped to the current user, and the primary user-facing surface wired through the project's typed data client. Before declaring done, trace one record end-to-end (triggering event → write → read → render); if any hop exists only in a comment or docstring rather than edited code, the slice is NOT done. Shipping only the persistence layer (a schema/migration with no writer, reader, or surface) is an incomplete slice, not a milestone.

## Capability Contract

Use this section when the user prompt touches production risk, even if the prompt does not name this technology explicitly.




Required wiring surfaces:
- provider/runtime configuration discovered during implementation
- nearest typed request/context boundary
- handler/procedure boundary before external side effects

Side-effect barrier:
- Place guards before external APIs, auth mutations, email sends, analytics events, storage writes, and database mutations.


Fallback policy:
- Prefer provider-native/platform-managed primitives by default when no explicit override exists.
- Follow clear user/project overrides, but mention the native alternative and tradeoff.
- Fallbacks must be durable, multi-instance safe, and atomic under concurrency.

Verification rules:
- [error] native-or-explicit-override: Use the provider-native primitive first unless the user/project explicitly overrides it.
- [error] atomic-fallback: Fallback counters must be atomic under concurrency.

## Quick Start

### Verify torch is available in test environment

```bash
# new code to add
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
python -c "import torch, torchaudio; print(torch.__version__, torchaudio.__version__)"
```

### Validate K1 GDFT output against torch STFT baseline

```python
# new code to add — host-side only, never runs on device
import torch
import torchaudio.functional as F

def validate_gdft_against_stft(audio_fixture_path: str, k1_bins: list[float]) -> dict:
    """Compare K1 Goertzel bin energies to torch STFT for regression gating."""
    waveform, sr = torchaudio.load(audio_fixture_path)
    # K1 audio pipeline: 48 kHz, 12-bit, mono
    assert sr == 48000, f"Fixture must be 48kHz, got {sr}"
    
    stft = torch.stft(waveform[0], n_fft=1024, return_complex=True)
    mag = stft.abs().mean(dim=-1)  # time-averaged magnitude spectrum
    
    return {"stft_mag": mag.numpy(), "k1_bins": k1_bins}
```

## Key Concepts

| Concept | Usage | Notes |
|---------|-------|-------|
| `torchaudio.load` | Load `.wav` test fixtures | Returns `(waveform, sample_rate)` |
| `torch.stft` | STFT baseline for GDFT comparison | Use `n_fft=1024` to match K1 frequency resolution |
| `torch.Tensor.numpy()` | Bridge to pytest/numpy assertions | Requires CPU tensor; call `.cpu()` first if on GPU |
| `torchaudio.functional.resample` | Normalize fixture sample rates | K1 is 48 kHz; some fixtures may be 44.1 kHz |

## Common Patterns

### Onset detection baseline

**When:** Validating K1 per-band log-flux onset against a torch mel-spectrogram baseline.

```python
# new code to add
import torch
import torchaudio.transforms as T

def onset_energy_baseline(waveform: torch.Tensor, sr: int = 48000) -> torch.Tensor:
    mel = T.MelSpectrogram(sample_rate=sr, n_mels=24, n_fft=512)(waveform)
    log_mel = torch.log1p(mel)
    # Half-wave rectified first-order difference = onset envelope
    diff = torch.relu(log_mel[:, :, 1:] - log_mel[:, :, :-1])
    return diff.sum(dim=1)  # sum over mel bands → 1D onset envelope
```

### Gate pattern: torch result drives pytest assertion

```python
# new code to add
import pytest, torch

def test_onset_correlation_k1_vs_torch(audio_fixture, k1_onset_fixture):
    k1 = torch.tensor(k1_onset_fixture)
    baseline = onset_energy_baseline(audio_fixture)
    # Pearson correlation must exceed 0.7 — K1 and torch are NOT identical,
    # but must agree on peak positions
    corr = torch.corrcoef(torch.stack([k1, baseline[:len(k1)]]))[0, 1]
    assert corr > 0.7, f"Onset correlation too low: {corr:.3f}"
```

## See Also

- [patterns](references/patterns.md)
- [workflows](references/workflows.md)

## Related Skills

- See the **pytest** skill for fixture management and test gate patterns
- See the **python** skill for project-wide Python conventions
- See the **aiofiles** skill if loading fixtures asynchronously
- See the **dsp-performance-profiling** skill for connecting torch baselines to firmware profiling gates