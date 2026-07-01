---
abstract: "N9 GDFT int32-magnitude-overflow fix — Captain-decision memo (D5). The fix (K1_GDFT_INT64_MAGNITUDE_V1 / _RECURRENCE_V1) is present, default-OFF, and host-proven correct, but ships UNUSED. Recommendation: stays HELD for v1 — the 2026-06-30 #72837 finding showed the 'louder→dimmer' defect was the single-scalar AGC (now fixed via per-band AGC), NOT this overflow, removing the last product justification. No code change. Read before reopening D5."
---

# N9 — GDFT int32 overflow promotion: HELD (decision memo, D5)

**Class C · P2 · Decision: D5 (Captain-only — reverses a prior "no value" verdict).**

## State (verified 2026-06-30, read-only)
- Flags **default OFF**: `K1_GDFT_INT64_MAGNITUDE_V1 = 0` (`config_types.h:94-95`), `K1_GDFT_INT64_RECURRENCE_V1 = 0` (`config_types.h:110-111`).
- Fix code is **present and guarded** in `audio/k1_gdft_core.cpp` (~:118 magnitude, ~:142 recurrence). Host **Gate Fα** proves the int64-magnitude mutation is caught (the harness sees the difference).
- So: the overflow ships **unfixed-by-default**; the fix is device-proven-*correct* (earlier bench A/B: leg D passes true-centre acceptance) but has **no demonstrated product value**.

## Why it stays HELD (the case got *weaker*, not stronger)
The strongest argument for promoting N9 was the hypothesis that the int32 overflow caused the perceptual **"louder→dimmer"** defect. The 2026-06-30 root-cause spike (**obs #72837**) disproved that: the defect was the **single global-scalar broadband AGC**, and the int32 overflow is a **red herring** for it. That AGC defect is now **fixed and shipped** via per-band AGC (`SB_AGC_PERBAND_V1`, product line `2e2800d`, device-proven). So the one product symptom that might have justified N9 is resolved by a different, shipped fix.

## Remaining gates if ever reopened (S2 production-flip owes 3 device gates)
1. MabuTrace Core-0 timing margin under the int64 path (it is heavier than int32).
2. Production-env AGC-scale behaviour A/B (the magnitude change shifts AGC input).
3. Captain eyes-on perceptual A/B.

## Recommendation (D5)
**Stay HELD for v1.** The prior "no value" verdict stands and is reinforced by #72837. Promote only if a *future* requirement needs exact near-resonance bin magnitudes (e.g. a pitch/chord feature that the rounded-k centre + overflow visibly degrades) — at which point run the 3 device gates first. **No code change now.**
**Default if no override:** flags stay OFF; v1 ships with the documented rounded-k centre + int32 magnitude (no regression vs every prior shipped build).

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 | Created. N9 HELD decision memo: fix present/default-OFF/host-proven; recommendation stays HELD — #72837 showed the AGC (not this overflow) was the louder→dimmer cause and per-band AGC already shipped the fix, removing N9's product justification. |
