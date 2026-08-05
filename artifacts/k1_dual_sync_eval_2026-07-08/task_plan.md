---
abstract: "Task plan for the dual-K1 sync feature lane (2026-07-08): research → evaluation → implementation plan for syncing two K1s into one 320-LED widened display (K1#1 = left, K1#2 = right), candidate transport BLE MIDI piggyback. Read to see phase status and decisions."
---

# Task Plan — Dual-K1 Sync (widened 320-LED display)

## Goal
Produce a decision-grade evaluation + implementation plan for a "sync" function: when a 2nd K1 is online, the two units merge into one widened display surface (160+160 = 320 LEDs), K1#1 = left half, K1#2 = right half. Candidate transport: piggyback on existing BLE MIDI protocol. Deliverable = plan, not implementation (unless Captain widens scope).

## Non-negotiables (from repo doctrine)
- Perceptual impact > architecture. Seam continuity and musical responsiveness are the bar.
- Core 0 audio hard real-time: no blocking calls, no mutexes on audio path.
- <50 ms audio-to-LED budget; sync jitter across the seam must be imperceptible.
- Instrumentation boundary: any probe/harness code is non-shippable.
- No device flash/serial writes during this research lane without identity verification.

## Phases
| # | Phase | Status |
|---|-------|--------|
| 1 | Recall + Understand fan-out (9 SSA readers) | DONE — 9/9 returned, decisive claims orchestrator re-run (findings.md ledger) |
| 2 | Clarify with Captain | DONE — 4 answers in decision log below |
| 3 | Evaluation: options matrix + architecture | DONE — evaluation-and-plan.md v1.0 |
| 4 | Red-team + pre-mortem | DONE — 4 lenses, 3 KILLs + 13 MAJORs consumed; decisive attacks re-verified (ember half-canvas, facade cal paths, BT core pinning, device registry) |
| 5 | Plan doc + HTML seam-geometry mockup | DONE — evaluation-and-plan.md v1.0 (M1 twins → M2 widened); mockup rendered/verified/published |

## Key decisions log
| Date | Decision | By |
|------|----------|----|
| 2026-07-08 | Lane opened; ultracode opted-in by Captain | Captain |
| 2026-07-08 | Transport: evaluate ALL K1-to-K1 links (BLE MIDI, raw BLE GATT, ESP-NOW, WiFi) and recommend; BLE MIDI is incumbent candidate, not mandate | Captain |
| 2026-07-08 | Audio source of truth (leader mic vs dual independent analysis): evaluation decides via options matrix | Captain |
| 2026-07-08 | Pairing UX + left/right assignment: evaluation proposes after weighing failure modes | Captain |
| 2026-07-08 | Deliverable scope: plan doc + HTML seam-geometry visual mockup; NO firmware edits this lane | Captain |
| 2026-07-08 | **F4 RATIFIED: Option 1 — seam-centred, one origin at the junction** is the M2 widened geometry (eyes-on via hosted mockup). | Captain |
| 2026-07-08 | **F1 RATIFIED (framework):** scheduling is a NON-ISSUE — software dev always runs parallel to crowdfunding; Phase 0 is green-lit. Radio choice is merit-driven. Minimum standard set: perceived-lag/seam budget ≈ **8 ms + small margin**. WiFi must prove (a) AP can absorb its Core-0 overhead at that standard and (b) device-to-device reliability (Captain's field experience: WiFi temperamental). BLE carries a strong field prior: K718 BLE MIDI = 100% uptime, zero drops, since introduction — acknowledged lower throughput; find the happy middle ground. | Captain |
| 2026-07-08 | **F5 RATIFIED:** full authority granted to silence/remove gates/contracts that block running/developing/testing this project, with clear documented reasons. Flashing 1401 for two-device testing is authorised under this grant. Interpretation recorded: safety-critical device-identity checks are UPDATED (envs registered), not deleted — they prevent wrong-target flashes, they do not block development; the Captain-verbal cal silence gate is not a dev-blocking gate and stands. | Captain |
| 2026-07-08 | **F2 RATIFIED: BLE-family custom GATT** (dual-role NimBLE, sync link CI 7.5 ms, K718 untouched). Phase 0 = verification of BLE against the four gate numbers; ESP-NOW = paper contingency tier 1. **Captain-added contingency tier 2: if all else fails, add a 2nd MCU (another ESP32-S3, or an ESP32-C5) as a radio co-processor.** Brief: f2-transport-decision.md. | Captain |

## Errors encountered
| Error | Attempt | Resolution |
|-------|---------|------------|

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code | Created — lane plan for dual-K1 sync research/eval/planning. |
