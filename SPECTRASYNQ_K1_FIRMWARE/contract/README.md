# Contract boundary — API and schema for portable-core handoff

Purpose:
- Keep the AP feature-vector contract explicit, so Lane B can implement it once and the VP side can consume it repeatedly.
- Preserve exact snapshot semantics from `audio/k1_audio_snapshot.h` and `effects/framework/K1AudioContext.h`.
- Decouple build-gated extensions (`K1_ONSET_V2`, `K1_CHORD_V2`) from core contract shape.

Files in this folder are the first migration source of truth for:
- `K1AudioSnapshot` structure contract
- `K1OnsetBeatEvent` contract
- effect-side accessor expectations (`K1AudioContext`-style projection)

All comments and docs use British spelling.
