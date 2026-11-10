# Prediction for (c), declared before the sectioned compile

Edit: `impact.transform.beat_amp_u16` 48000 → 12000 in ONE section: Loreen consumer contract segment 4, label `chorus`, 45.68–60.81 s (span [45,680,000, 60,810,000) µs). Section id `chorus_1`; every other segment keeps the top-level profile `prim8_natural_v1` (beat_amp 48000).

Written by `tools/predict.py` from M2's own pre-edit and whole-track post-edit streams plus the contract beats, before any sectioned stream existed (`c1_PREDICTION_written_before_compile.json`; re-run now, byte-identical: `c1b_…`).

- 120 Hz frames in the span: 1,816 (of 26,870).
- Frames that MUST change versus the pre-edit stream: exactly 116, frames 5542 … 7245. These are the ticks inside the span that fall in the 40 ms pulse after each of the 24 off-downbeat beats in the span (P2, first principles), and equal the M2 whole-track edit's changed frames restricted to the span (P1). P1 == P2.
- In each changed frame only bytes 20–21 (Prim8[1] impact) differ; new impact = whole-track post-edit value.
- No pulse straddles a section boundary.
- All other 26,754 frames MUST be byte-identical to the pre-edit stream `65143215…eba1`.
- Expected sectioned stream sha256: `ffa0dd3b27489cdd827e1d39d47ea0e88585d3e0f7dd84dc17de4568445dd6e2`.
- Intent Trace: rows with 45,680,000 ≤ t_us < 60,810,000 carry `"section":"chorus_1"`; all other rows have exactly the pre-edit bytes.
