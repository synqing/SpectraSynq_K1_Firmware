# WB-3 comparative decision record (post-evidence only)

**Do not fill this document until** `artifacts/stm-track-a/` and `artifacts/stm-track-b/` each have a complete packet **or** Captain formally abandons a track.

## Preconditions

- [ ] Track A packet: H1 PASS on `origin/main`, Core-0 measured or INDETERMINATE bundle filed, VP matrix run or explicit deferral, artefact manifest hashes recorded.
- [ ] Track B packet: reference attestation closed **or** waived in writing, FFT spike microbenchmark, Core-0 + VP when reference valid, artefact manifest hashes recorded.
- [ ] clangd Gate 0 closed for any C++ convergence merged toward production.
- [ ] Captain eyes-on H5 for modes 7/8 if either track is a ship candidate.

## Decision (Captain only)

```yaml
date:
track_a_verdict: pass-bench | fail | abandoned
track_b_verdict: pass-bench | fail | abandoned
selected_path: A | B | C | bench-only-both
rationale:
production_intent: bench-only | promote-later | absent
evidence_hashes: []
captain_attestation:
```

## Notes

_(Empty — comparative rationale belongs here after both tracks.)_


## Track B spike packet (2026-07-29)

- Gate B waiver recorded; firmware `k1_hardware_fft512_bench` built.
- On-device µs metrics: **INDETERMINATE** (flash blocked — port busy).
- Comparative native vs FFT: **pending** Track A commit bundle + device microbench.
