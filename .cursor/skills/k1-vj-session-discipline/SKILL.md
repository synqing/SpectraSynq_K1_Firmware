---
name: k1-vj-session-discipline
description: >-
  HARD FAIL discipline from the 2026-08-07 IM69D peakiness / Deck16 Tab5 BLE /
  boot-show session. Use before silence-gate tuning, peakiness soaks, IM69D
  bench work, Tab5↔K1 BLE linking, boot palette/mode defaults, safe-mode crash
  loops, or any task that might reframe Deck16 as K718 Remoted dial pairing.
---

# K1 VJ / IM69D Session Discipline

**Authority:** `docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md`

Announce: "Using k1-vj-session-discipline against SESSION_CANON_2026-08-07."

Then run the checklist. If any HARD FAIL would be violated, **stop and fix the
plan** before flash / soak / claim.

## Thinking gate (required on these tasks)

Route via `/thinking-model-router`. Default combo for this domain:

1. **Systems** — complementary axes, reinforcing crash loops
2. **Map–territory** — RMS / crest-only / K718 / HCI-timeout maps vs silicon
3. **Steel-man** — strongest case for the rejected approach, then kill with data
4. **Red team** — how the soak or BLE claim will lie
5. **OODA** — observe distributions → decide composition → act

## HARD FAIL checklist

Copy and mark each item before acting:

- [ ] **HF-1** Not tuning crest-only hoping ambient+music both clear at night SPL
- [ ] **HF-2** Not admitting learner samples via RMS "floor-like"
- [ ] **HF-3** Preferring SSL-relative level (`SSL × frac`) over absolute magic numbers
- [ ] **HF-4** Predictions file written **before** soak (falsifiable IDs)
- [ ] **HF-5** Music soak driven with audible fixture (`afplay` or named file), logged
- [ ] **HF-6** Typed serial uses leading `:`
- [ ] **HF-7** BLE/product framing is **Tab5 Deck16**, never "K718 Remoted success"
- [ ] **HF-8** Not claiming BLE link PASS under `BLE_HS_ETIMEOUT_HCI` / no advertise
- [ ] **HF-9** Boot lock (modes+palettes) re-applied **after** `k1_show_state_load()`
- [ ] **HF-10** Safe-mode / null LED buffers: no unguarded intro / buffer clears
- [ ] **HF-11** Device identity by **chip ID**, not port name
- [ ] **HF-12** Correct env↔device; no P4↔S3 cross-flash
- [ ] **HF-13** Active bench edits on intended worktree (vj-lane for this lane)

## Canon sentences

1. Crest and level are complementary discriminators; each fails alone where the other holds.
2. RMS cannot separate music from this room's noise floor — in any gain domain.
3. OR composition worsens ambient false-breaks; AND is the product form.
4. `K1_DECK16_TAB5_BLE_R1` — Tab5 is the controller; K718 Remoted dial is retired.

## Joint silence seed (2026-08-07)

| Knob | Seed |
|------|------|
| `K1_SILENCE_PEAKINESS_BREAK` | `2.10` |
| `K1_SILENCE_JOINT_LEVEL_SSL_FRAC` | `1.25` |
| dwell | `5000` ms |
| Composition | `pky ≥ brk AND max_raw ≥ SSL × frac` |

Do not declare a new static crest OP without a written offline distribution proof that ambient and music separate.

## Boot show lock (forever)

| Channel | Mode | Palette |
|---------|------|---------|
| Primary | WAVEFORM HYBRID K1 | `K1_Naberius_Gold_gp` (40) |
| Secondary | WAVEFORM-FAST | same |

## BLE / HCI stance

- Read `docs/architecture/K1_DECK16_ARCHITECTURE_R1.md` and
  `_scratch/deck16_tab5_k1_proof_20260807/HCI_PATH_DIAGNOSIS.md` when present.
- Status under C6 HCI timeout: `BLE_HCI_PATH_UNDIAGNOSED`.
- Do not set `EXTERNAL_FLASH_REQUIRED` or `HARDWARE_BLOCKED` without new evidence.
- Macro name: `K1_BLE_REMOTED` (not `SB_K1_BLE_REMOTED`).

## Worktree / build

- Prefer `SpectraSynq_K1_Firmware-vj-lane` / `lane/k1-vj-ble-deck8` for this lane.
- Build: `bash scripts/agent/pio-build.sh <env>` only.
- No flash / `start_noise_cal` without Captain scope (+ silence confirmation for cal).

**Evidence pointers**

See the Evidence index in the session canon. Forensic receipts under
`docs/forensics/im69d-bringup-2026-08-06/` on the vj-lane worktree.

## Companion — Deck16 backend / haunt / latency (2026-08-09)

For Tab5↔bench-K1 BLE identity digests, deck_state pending TX, full71/C6 soak,
dark-fade / STANDBY, MAIN glass authority, or Mirror claims, **also** load:

- Canon: `docs/canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md`
- Skill: `k1-deck16-session-discipline` (HF-14…HF-28)
- Gate: `bash scripts/agent/deck16-first-contact-gate.sh`

Do not treat this skill alone as sufficient for that domain.
)
