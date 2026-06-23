---
abstract: "Evidence table for last-known-good pre-refactor SensoryBridge/K1 build candidates. Separates runtime-good visual state, functional migration state, source-fence tags, upload-only proof, and the sealed refactor harness baseline."
---

# Pre-Refactor Known-Good Build Candidates

## Evidence Model

- [FACT] Runtime-good means LED/audio behaviour or VP/AP harness behaviour was observed and recorded.
- [FACT] Source-fence means a clean SHA/tag exists for rollback or diffing, but that alone is not runtime proof.
- [FACT] Upload-only means the binary reached the device and serial sanity was seen, but visual/audio correctness remains unproven.
- [INFERENCE] "Last known good" has multiple valid answers in this repo because the visual state, PIO migration, and refactor freeze were captured by different artefacts.

## Candidates

| Rank | Candidate | SHA / tag / version | Evidence | Limits | Verdict |
|---|---|---|---|---|---|
| 1 | Formal pre-refactor regression baseline | Tag `refactor-baseline-2026-05-25` at `2e0e983`; firmware baseline `k1_hardware_harness@88428a2` captured while flashed from `6f42fae` | `docs/refactor/harness-baselines/freeze-88428a2/CANONICAL.md` records SEALED status, VP Tier A hashes, Tier B bands, and AP bands. `docs/k1-refactor-2026-05/EXECUTION-HANDOVER-ROWS-3-4-2.md` says `refactor/main` branched from this tag. | The tag commit is docs/freeze metadata; the actual firmware baseline is `88428a2` / byte-identical `6f42fae`, not the tag commit itself. | Best answer for "pre-refactor baseline" and rollback/equivalence work. |
| 2 | Best preserved pre-refactor visual runtime state | Firmware `40102`; docs commit `e78b6f6` | `docs/config-snapshots/2026-05-22-perfect-dual-channel-v40102.md` captures live primary Bloom, secondary WAVEFORM-FAST, VP candidate profile, and render timing. | Snapshot explicitly says the running firmware was older than repo head; not a clean rebuildable tag. | Best answer for "last known good look". Treat as configuration/runtime truth, not source truth. |
| 3 | Functional K1 PlatformIO migration state | Commit `2cbeea9` | `docs/forensics/2026-05-24-stage7-handoff.md` records K1 boot, I2S capture, waveform extraction, visibly responsive LEDs, and Captain verbal acceptance. | The handoff still records K1 operating-point questions and unresolved noise-floor differences. | Best answer for "first known-good S3/PIO functional build before the full refactor". |
| 4 | Pre-PIO rollback/source fence | Tag `pre-pio-migration-20260524-1320` at `93052a9` | `docs/forensics/2026-05-24-codex-review-checkpoint-1.md` and `docs/forensics/2026-05-24-stage7-handoff.md` identify it as rollback tag / Stage 0 WIP snapshot. | Not runtime proof. It is the source anchor before migration edits. | Use for rollback or diff boundary, not as a visual-good claim. |
| 5 | K1 hardware compile/upload proof | Commit `8b35022` | `docs/s3-migration-prep.md` records S3 compile, upload proof, hash verification, and serial sanity. | The same doc says it does not prove I2S capture, FastLED timing, dual-strip signal integrity, controls, or 120 FPS headroom. | Exclude from "known good" unless the question is strictly "uploaded and serial responded". |
| 6 | Serial hotkey/calibration safety pre-freeze state | Commit `9423ea0` | `docs/forensics/2026-05-24-hotkeys-prefreeze-review.md` records unit tests, `pio run`, upload success, and runtime hotkey smoke. | Serial/calibration safety only; not a visual/audio known-good baseline. | Useful safety reference, not a visual build baseline. |

## Working Interpretation

[FACT] For refactor work, the authoritative baseline is `refactor-baseline-2026-05-25` / `freeze-88428a2`, with the actual firmware reference at `88428a2` and byte-identical capture from `6f42fae`.

[FACT] For product/visual recovery, the strongest preserved state is firmware `40102` from `2026-05-22 19:56 AWST`, captured in the perfect dual-channel snapshot.

[FACT] For S3/PIO functional recovery, the strongest clean source commit is `2cbeea9`, backed by Stage 7 runtime evidence.

## Changelog

| Date | Author | Change |
|---|---|---|
| 2026-05-27 | Codex | Initial evidence table. |
