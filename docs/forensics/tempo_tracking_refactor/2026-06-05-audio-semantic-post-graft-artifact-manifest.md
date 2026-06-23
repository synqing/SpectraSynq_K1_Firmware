---
abstract: "Artifact manifest + verification record for the post-graft validation package (branch wip/audio-saliency-recovery, HEAD fb83bd1). Confirms the three diagnostic HTML snapshots are the correct audio-semantic reports (NOT FastLED — that was a stray vendored file), reconciles the HEAD mismatch (3d16024 base vs fb83bd1 package, zero DSP delta), and records SHA256/sizes, grep verification, and exact regeneration commands. One renderer enhancement: the host-ceiling caption is now emitted as greppable HTML text."
---

# Post-Graft Validation — Artifact Manifest & Verification

## 1 · Branch & final HEAD
`wip/audio-saliency-recovery` @ **`fb83bd1`** (`docs(validation): post-graft diagnostic notebook package`). HEAD == fb83bd1.

## 2 · Validation base HEAD
**`3d16024`** (`chore(bench): … flash forward-graft`). The forward-graft DSP state the validation ran against.

## 3 · DSP diff status
`git diff 3d16024..fb83bd1 -- SPECTRASYNQ_K1_FIRMWARE/` → **empty. NO firmware/DSP changed.** The 3d16024..HEAD range touches only `notebooks/`, `scripts/regression-harness/`, the validation memo, and `tests/test_k1_upload_guard.py` (a port-fixture fix). This-turn change: `scripts/regression-harness/render_diagnostics.py` (caption-as-text only) — still no DSP.

## 4 · Exact artifact paths
- **Notebook:** `notebooks/audio_semantic_diagnostics.ipynb` (28 cells; parameters cell @ idx 2; sections 1–12; executes via nbconvert rc=0/0-errors).
- **Helper:** `notebooks/diag_helpers.py` (display-only).
- **Exporter:** `scripts/regression-harness/export_diagnostic_trajectories.py`.
- **AP_STREAM ingester:** `scripts/regression-harness/apstream_ingest.py` (`load_apstream`).
- **Renderers:** `scripts/regression-harness/render_diagnostics.py` (canonical for the delivered HTMLs — self-contained, no kernel) + `render_via_nbconvert.py` (executes the real notebook; captions in-figure).
- **Metric artifacts** (`build/audio-semantic-metrics/`, gitignored): `baseline.{json,md}`, `final.{json,md}`, `onset_v2_ab.json`, `chord_v2_ab.json`, `trajectories/` (12 JSON + `SCHEMA.md`).
- **HTML snapshots** (`build/audio-semantic-visuals/`, gitignored): `baseline/index.html`, `final/index.html`, `ab_diff/index.html`.

## 5 · HTML SHA256 + byte size (regenerated at HEAD fb83bd1)
| file | bytes | sha256 |
|---|---|---|
| baseline/index.html | 439020 | `164992b8f6f5fcc16315eba8349b7e0a8e02a0b1c79d14ccdce1973768e622d6` |
| final/index.html | 425607 | `57ebd590b56076a00f20df1f9b79e2c99cf21a6c9dd6ccea15e841ab3e3b7441` |
| ab_diff/index.html | 425601 | `5b4cedf082d07b1e8ff5b7e7b876f85b39ddd280fab6cf5bf1a3e45fff816621` |

## 6 · Artifact verification grep (all three HTMLs, per file)
`Audio Semantic`=1 · `MODELLED FRONT-END / HOST CEILING`=2 (now HTML text, was 0) · `Provenance`=1 · `Confidence`=1 · `beat_tick`=1 · `A/B`=2 · **`FastLED`=0 · `fastled.js`=0 · `index.js`=0**. Title = `diagnostics … baseline/final/ab`; `<h1>Audio Semantic Diagnostics</h1>`; provenance `head : fb83bd1…`. **PASS** — none are FastLED; none import `fastled.js`/`./index.js`; section markers + host-ceiling caption present.

## 7 · Exact regeneration commands
```
# from repo root
rm -rf build/audio-semantic-visuals/{baseline,final,ab_diff} build/audio-semantic-metrics/trajectories
python3 scripts/regression-harness/export_diagnostic_trajectories.py    # -> 12 trajectories + SCHEMA.md
python3 scripts/regression-harness/render_diagnostics.py                 # -> 3 index.html (canonical, no kernel needed)
# alternate (executes the real notebook; needs a numpy+matplotlib jupyter kernel):
DIAG_REPO_ROOT="$PWD" jupyter nbconvert --to html --execute notebooks/audio_semantic_diagnostics.ipynb
```

## 8 · The "FastLED index.html" finding
**Wrong file — not a wrong path of ours, and not a renderer bug.** The three delivered diagnostic HTMLs were always correct (verified §6). The FastLED page is a **vendored library template**: `libraries/_FastLED.disabled/src/platforms/wasm/compiler/index.html` (the FastLED WASM compiler's stock `index.html`), plus dozens of copies under `.claude/worktrees/*/.../FastLED/.../index.html`. A file-open/upload that matched `index.html` by name could surface one of those instead of `build/audio-semantic-visuals/<run>/index.html`. **Resolution:** none of the delivered artifacts was FastLED; the only change made was a narrow renderer enhancement (host-ceiling caption emitted as greppable HTML text) so a text-search audit can no longer be ambiguous. No DSP, no notebook-logic change.

## 9 · Final one-human-check pointer
See `2026-06-05-audio-semantic-post-graft-validation.md` **§6 · ONE FINAL HUMAN CHECK** — open the notebook + `final`/`ab_diff` HTMLs, verify K1 by serial `B4:3A:45:A5:87:F8` (not port), device already flashed, play 4-on-floor/syncopated/loud/silence tracks, confirm beat tracks music + effects fire/sustain + quiet on junk + transient onsets, capture AP_STREAM (memo §5), one-line rollback if needed.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-05 | agent:Orchestrator | Created — artifact manifest + verification. HEAD mismatch reconciled (3d16024 base / fb83bd1 package, zero DSP delta). Confirmed 3 HTMLs are the correct diagnostic reports (FastLED=0); the user's "FastLED index.html" = a stray vendored `_FastLED.disabled/.../compiler/index.html`. Regenerated from scratch; host-ceiling caption now greppable HTML text. |
