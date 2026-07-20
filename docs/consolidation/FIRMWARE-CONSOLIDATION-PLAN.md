# K1 Firmware Consolidation Plan

**Status:** Active · **Ratified:** 2026-07-21 · **Owner:** CTO/PM (firmware)
**Canon:** `synqing/SpectraSynq_K1_Firmware`

## 1. Context & the constraint

K1 firmware history is fragmented across ~15 repositories, all of them the same
animal: ESP32-S3 (`esp32-s3-devkitc1-n16r8`), Arduino framework, Goertzel/GDFT
audio→LED, all derived from Sensory Bridge (GPL-3.0). As of mid-2026 there were
**three live heads** (Lightwave-Ledstrip, SpectraSynq_K1_Firmware, rewrite) plus a
heritage analysis workspace (SB9). Active development had already migrated to
`SpectraSynq_K1_Firmware` (WS2816 dual-channel hardware bring-up) while
Lightwave-Ledstrip went into pruning/maintenance — a fork that was live and widening.

**Decision (ratified): `SpectraSynq_K1_Firmware` is canon.** It is the actively
developed, cleanly architected, production-named, heritage-compliant line built on a
deliberate effect-decomposition method. Lightwave-Ledstrip becomes the
reference-of-record whose breadth is migrated in, then archived.

## 2. Evidence base

Inventory (git mirror @ 2026-07-21) and claude-mem observation counts:

| Repo | Last activity | Files | Memory obs | Role |
|---|---|---|---|---|
| Lightwave-Ledstrip (`firmware-v3/`) | 2026-07-11 | 3,104 | 23,332 | Deep mainline; 194 effect files, full DSP, dashboard, iOS, composers |
| SpectraSynq_K1_Firmware | 2026-07-16 | 2,256 | 1,849 | Canon; clean architecture, prod env matrix, active HW bring-up |
| SpectraSynq-K1-Firmware-SB9- | 2026-06-26 | 2,754 | 7,360* | Heritage analysis workspace |
| rewrite | 2026-07-12 | 58 | — | Greenfield sim-first spike |
| FL.ledstrip + K1.* variants | 2025-09→2026-01 | varies | varies | Archaeology |

*SensoryBridge-main 9 project.

## 3. Parity verdict (measured 2026-07-21)

**Audio/DSP — near-complete architectural parity.** Canon's `audio/` (13 modules:
GDFT, gdft_core, chord_detect, musical_saliency, onset_beat, tempo, semantic_state,
spectral_honesty, i2s_audio) maps cleanly onto Lightwave's 81-file audio tree.
**Migration here = validate tuning constants against a harness, not rebuild.**

**Effects — ~17% by count.** Lightwave has ~194 effect files (~150 playable),
dominated by a ~130-effect `LGP*` physics suite. Canon has 26 `light_mode_*` effects —
every core *family archetype* but not the physics variations.
**The effect migration IS the consolidation work** (see EFFECT-MIGRATION-BACKLOG.md).

## 4. Roadmap (phased, gated)

### Phase 0 — Declare & freeze (this change)
- [x] `SOURCE-OF-TRUTH.md` declares canon; repo roles documented.
- [x] Lightwave frozen at tag `reference-of-record/v3-final` (`60009324`).
- [x] Working-copy inventory captured (WORKING-COPY-INVENTORY.md).
- [ ] Deprecation banners on SB9, rewrite, FL.ledstrip, K1.* (follow-up PRs per repo).

### Phase 1 — Parity harness first (gate for everything downstream)
- [ ] Port Lightwave capture/test suites (`docs/CAPTURE_TEST_SUITES.md`,
      onset capture workflow) into canon as the acceptance gate.
- [ ] Establish golden-reference captures for the 26 existing canon effects.
- **Exit criteria:** canon can reproduce a Lightwave capture within tolerance for
  ≥1 effect per core family.

### Phase 2 — DSP tuning validation
- [ ] Diff tuning constants (Goertzel bins, AGC, onset thresholds, tempo PLL)
      Lightwave → canon; reconcile via harness.
- **Exit criteria:** audio feature outputs match reference within tolerance.

### Phase 3 — Effect migration (batched, harness-gated)
Re-derive the LGP physics suite through the decomposition method, batch by batch
(see EFFECT-MIGRATION-BACKLOG.md). Each batch merges only when it passes the harness.
- **Exit criteria:** effect parity target met (recommend ≥ the curated
  "keeper" set, not all 194 — prune during migration).

### Phase 4 — Archive & spin-out
- [ ] Spin dashboard/iOS/composer/zone-mixer/tab5-encoder out of Lightwave monorepo
      into sibling repos under the org.
- [ ] Archive Lightwave (GitHub archive, not delete) + variants once parity signed off.
- [ ] Deduplicate working copies per WORKING-COPY-INVENTORY.md.

## 5. Risks & gates

| Risk | Severity | Mitigation / gate |
|---|---|---|
| Loss of tacit DSP/effect tuning | High | Parity harness (Phase 1) mandatory before any port; Lightwave frozen, never deleted until sign-off |
| Licence/heritage (GPL, prior AGPL/token leak alerts) | Medium | Canon carries NOTICE + `sb_` provenance; secret-scan gate on release builds |
| Fork keeps widening during migration | Medium | "No new features on Lightwave" freeze enforced from Phase 0 |
| Working-copy sprawl causes work on wrong copy | Medium | WORKING-COPY-INVENTORY.md; consolidate to canon primary |

## 6. Non-goals

- Not porting all 194 Lightwave effects verbatim — prune to a curated keeper set.
- Not migrating dashboard/iOS/composer into the firmware repo — those spin out.
