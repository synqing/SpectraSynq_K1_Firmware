---
abstract: "Stimuli manifest for freeze-88428a2 (REQUIRED, 03 §2.6). AP baseline captures use the three controlled stimuli below; VP Tier B is silence-only and does not use tone or music. Bands are stimulus-bound — every future gate capture MUST replay the matching stimulus per surface. Track identifiers are PLACEHOLDERS pending Captain. Immutable once the Freeze tag is applied."
---

# Stimuli Manifest — `freeze-88428a2`

Status: **track IDs recorded 2026-05-25** — track-A = Eagles – "Hotel California"; track-B = Lavern – "In My Mind". Tone spec fixed. Playback was acoustic (speaker → MEMS); exact dBFS not metered. Music windows are single live takes — not bit-reproducible, so music AP is a wide sanity band, not a tight replay band (§2.5).

| ID | Stimulus | Spec / to record at capture |
|---|---|---|
| `tone-1k` | **1 kHz reference tone** | 1000 Hz sine; playback level (dBFS or source position) **TBC**; source device + output path **TBC**; applied acoustically through the MEMS; duration ≥ the capture window. |
| `track-A` | **Eagles – "Hotel California"** | Single acoustic take, 2026-05-25 ~13:31 (speaker → K1 MEMS). Edition/source + exact 5 s window offset not pinned (acoustic single-take — not bit-reproducible by design). run-1: follower≈1444, spec_argmax 39→53, peak≤1.28. |
| `track-B` | **Lavern – "In My Mind"** | as `track-A` — single acoustic take, 2026-05-25 ~13:36. run-1: follower≈7693, spec_argmax 12, chroma 0.30, peak≤1.11. |

## Binding rules (03 §2.6)
- VP Tier B uses confirmed silence only: `:frame_dump=all,<mode>,5000,4` ×12. Do not run tone/music frame dumps for this freeze.
- AP uses the controlled stimuli: `:dump_raw=tone` + tone `:ap_capture=5000` use `tone-1k`; the music `:ap_capture=5000` runs use `track-A` then `track-B`.
- The manifest is **immutable once the Freeze tag is applied** (committed + tagged + read-only). Changing any stimulus invalidates the baseline and requires a new Freeze.
- A recal pre-step does not alter stimuli; it is logged in its own `recal-<ts>.md`, not here.

## Capture protocol binding (this freeze)
- Leg 1 (silence): Captain "silent, go" → `:dump_raw=silence` + `:frame_dump=all,<mode>,5000,4` ×12 (VP Tier B under silence only).
- Leg 2 (tone): Captain "tone running" → `:dump_raw=tone` + `:ap_capture=5000` (AP only).
- Leg 3 (track-A): Captain "track-A running" → `:ap_capture=5000`.
- Leg 4 (track-B): Captain "track-B running" → `:ap_capture=5000`.
- Repeat once for run-to-run noise → bands (§2.5).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-05-25 | claude-code (Opus 4.7) | Created (template). tone-1k spec fixed; track-A/B identifiers + levels/offsets PENDING Captain; protocol binding for the freeze-88428a2 coordinated capture. |
| 2026-05-25 | Codex | Amended per Captain ruling: VP Tier B is silence-only; tone/music stimuli are AP-only. |
| 2026-05-25 | claude-code (Opus 4.7) | Recorded Captain-pinned track-A = Eagles "Hotel California", track-B = Lavern "In My Mind"; noted acoustic single-take provenance (windows not bit-reproducible → music AP = wide sanity band). |
