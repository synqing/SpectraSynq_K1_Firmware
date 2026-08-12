---
abstract: "Session canon for 2026-08-06→08-07 — IM69D silence peakiness / conjunctive break, boot show lock, Tab5 Deck16 BLE HCI, crash-loop recovery. Hard rules + evidence map so agents never replay the same trial-and-error tax."
status: active_canon
date: 2026-08-07
worktree_primary: SpectraSynq_K1_Firmware-vj-lane
branch_primary: lane/k1-vj-ble-deck8
architecture: K1_DECK16_TAB5_BLE_R1
skill: k1-vj-session-discipline
thinking_models: [systems, map-territory, ooda, steel-manning, red-team, model-router]
---

# Session Canon — IM69D Peakiness × Deck16 × Boot Lock (2026-08-07)

**Reader:** every future agent touching silence gates, bench IM69D soaks,
boot defaults, or Tab5↔K1 BLE.

**Purpose:** this is not a diary. It is the **immune memory** of a multi-thread
session that burned substantial wall-clock rediscovering facts that were
already on silicon or in logs. Violating the HARD FAIL table below is a
process incident, not a style preference.

**On-disk evidence beats memory.** Primary receipts live on the VJ worktree
unless noted. Mirror this file into that worktree when syncing lanes.

---

## 0. One-line map of the session

| Thread | Outcome | Status |
|--------|---------|--------|
| **A. Silence / peakiness** | Crest alone has no static OP at night SPL; **crest AND level** is the composition | Wired on vj-lane (often uncommitted); joint on-device soak parked after crash |
| **B. Crash-loop** | Safe-mode intro → null LED buffers → `StoreProhibited` | Fixed + reflashed; not the AND math |
| **C. Deck16 BLE** | Product = **Tab5**, not K718; link blocked on Tab5 C6 HCI timeout | `BLE_HCI_PATH_UNDIAGNOSED`; software work remains |
| **D. Boot show** | Primary Hybrid K1 / Secondary Waveform-Fast / both Naberius Gold | Silicon PASS on bench; re-apply after Shift+S load |

---

## 1. HARD FAIL table (do not re-learn)

| ID | HARD FAIL | Why we paid | Correct stance |
|----|-----------|-------------|----------------|
| **HF-1** | Tune a **single crest break** hoping ambient latch and music wake both clear at night SPL | Ambient needs brk ≳2.8 to latch; music needs ≲2.2 to wake; crest distributions **overlap** | Treat crest and level as **complementary discriminators**; compose with **AND**, not OR |
| **HF-2** | Gate learning / silence on **RMS "floor-like"** | Music median RMS can be **below** ambient; hum is low-crest, music is high-crest | Admit ambient in **crest domain only**; never RMS-floor for learner admit |
| **HF-3** | Absolute crest clamps / magic numbers as product OP | Night SPL moves the distributions; absolute fences recreate dead states | Prefer **self-scaling** forms (`SSL × frac`); seed `frac=1.25`, brk=2.10, dwell=5000 |
| **HF-4** | Soak without **written predictions** (J/P numbered, falsifiable) | Post-hoc storytelling; Captain doctrine violated | Write predictions file **before** flash/soak; mark PASS/FAIL against them |
| **HF-5** | Call a music soak valid when the agent only typed serial / watched keyboard | Stimulus was ambient; music never entered the room | Drive music with **`afplay`** (or equivalent audible fixture); log stimulus |
| **HF-6** | Typed serial without leading **`:`** | Commands silently ignored | Always `:silence_peakiness_break=…` form |
| **HF-7** | Frame BLE success as **K718 Remoted dial pairing** | Product architecture is **Tab5 Deck16**; Captain exploded | Scan/connect for **Tab5** identity; K718 is retired for this lane |
| **HF-8** | Claim Tab5 BLE link PASS while C6 returns **`BLE_HS_ETIMEOUT_HCI`** | No advertising; K1 `linked=0` is expected | Diagnose HCI path; obey binding flags in HCI diagnosis (do not leap to external C6 flash) |
| **HF-9** | Boot palette lock **before** `k1_show_state_load()` / Shift+S restore only | Saved show restores BLOOM / wrong modes after lock | Lock modes+palettes; **re-apply after** show-state load |
| **HF-10** | Run boot intro in **safe-mode** / with **null** LED buffers | Reinforcing crash-loop under RTS churn | Null-guard buffer ops; **skip intro** when safe-mode or null buffers |
| **HF-11** | Identify device by **USB port name** | Ports scramble every session | Identity = **chip ID** (`B489A500` bench / `F887A500` main); consult device-build-registry |
| **HF-12** | Cross-flash P4↔S3 or wrong K1 env LED map | Dark channels / wrong silicon | Env↔device registry is law; Tab5 P4 ≠ K1 S3 |
| **HF-13** | Edit firmware in **main** dirty tree while active bench work is on **vj-lane** without intentional sync | Split-brain; lost fixes | Prefer `SpectraSynq_K1_Firmware-vj-lane` for this lane; sync deliberately |

### Canon sentences (memorise)

1. **Crest and level are complementary discriminators; each fails alone in a regime where the other holds.**
2. **RMS cannot separate music from this room's noise floor — in any gain domain.**
3. **OR composition of crest/level worsens ambient false-breaks; AND is the product form.**
4. **The map (K718 / crest-only / RMS gate / HCI timeout = hardware dead) is not the territory.**
5. **K1_DECK16_TAB5_BLE_R1 — Tab5 is the controller; K718 Remoted dial is retired.**

---

## 2. Systems view (why single-knob failed)

```text
Night ambient (hum, crest ~1.3) ──► needs HIGH crest-break to latch
Night music  (peaky, crest high) ──► needs LOW crest-break to wake
                    │
                    ▼
           crest-only OP EMPTY
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   raise break               lower break
   music stays dark          ambient never latches
        │                       │
        └───────────┬───────────┘
                    ▼
         add LEVEL axis (max_raw vs SSL×frac)
         break iff pky≥brk AND max_raw≥SSL×frac
```

**Reinforcing failure loop (crash):** RTS/reset churn → crash streak →
`BOOT_LOOP_GUARD` safe-mode → intro render on null buffers →
`StoreProhibited` → streak stays hot. **Balancing fix:** null guards + skip
intro in safe mode.

**Map–territory traps paid for:**

| Map trusted | Territory measured |
|-------------|-------------------|
| "Raise/lower pky_brk until both soaks pass" | No static crest OP |
| "RMS floor = quiet enough to learn" | Quiet music is RMS-floor-like and crest-structured |
| "K1 linked=0 means retarget scan names again" | Tab5 never advertised (C6 HCI dead) |
| "HCI timeout ⇒ must external-flash C6" | Binding flags: root cause NOT ESTABLISHED; software work remaining |
| "Boot defaults in CONFIG_DEFAULTS suffice" | Shift+S show restore after lock |

---

## 3. Operating procedure (silence / soak)

1. **Bootstrap** `scripts/agent/session-bootstrap.sh`; read registry + this canon + skill `k1-vj-session-discipline`.
2. **Worktree:** vj-lane unless Captain says otherwise.
3. **Device:** chip `B489A500`, env `k1_bench_im69d` or `k1_bench_im69d_ble` as scoped — never by port alone.
4. **Predictions file** under `docs/forensics/im69d-bringup-2026-08-06/` before the run.
5. **Stimulus:** ambient leg = confirmed quiet; music leg = `afplay` (or named fixture) with path logged.
6. **Serial:** leading `:`; read `[AP]` for `pky=`, `pky_brk=`, `pky_p95=`, `pky_frac=`, `pky_lvl=`, `SSL=`.
7. **Joint seed (as of 2026-08-07):** `brk=2.10`, `K1_SILENCE_JOINT_LEVEL_SSL_FRAC=1.25`, dwell `5000`.
   > **Superseded (2026-08-12)** — the fraction value and its transfer rule were corrected; see
   > *Update — 2026-08-12* at the end of this file. Shipping value is `1.75`, and the fraction
   > **transfers between units once each unit is calibrated at its final placement.**
8. **Slice 2 learner:** gated ~5 room-states; may learn **two** numbers (crest + level frac); both need transition logs; **build gated on multi-day soak**, not one night.
9. **After any flash that can trip safe-mode:** listen for `stable_clear=1` / no Guru Meditation before claiming soak validity.

---

## 4. Boot show lock (product forever)

| Channel | Mode name | Enum / note | Palette |
|---------|-----------|-------------|---------|
| Primary | WAVEFORM HYBRID K1 | mode **32** / `LIGHT_MODE_WAVEFORM_HYBRID_K1` | `K1_Naberius_Gold_gp` index **40** |
| Secondary | WAVEFORM-FAST | mode **7** | same |

**Order invariant:** apply boot lock **after** persisted config **and after**
`k1_show_state_load()` (Shift+S). Static gate: `tests/test_boot_palette_lock_static.py`
(extend for modes when present on the tree).

---

## 5. Deck16 / Tab5 BLE (product framing)

- Architecture authority: `docs/architecture/K1_DECK16_ARCHITECTURE_R1.md`
- Radio decision: `docs/architecture/RADIO_FALLBACK_DECISION.md`
- HCI session pack: `_scratch/deck16_tab5_k1_proof_20260807/HCI_PATH_DIAGNOSIS.md`
- Status label when timeout seen: `BLE_HCI_PATH_UNDIAGNOSED` — **not** "hardware blocked"
- Binding flags from that diagnosis remain in force until overturned with evidence
- Macro: `K1_BLE_REMOTED` (not stale `SB_K1_BLE_REMOTED`)
- Next physical/software steps: BT-capable hosted C6 path and/or arch P7 S3 fallback — **after** remaining software diagnosis, not instead of it

---

## 6. Evidence index (vj-lane forensics)

Directory: `docs/forensics/im69d-bringup-2026-08-06/` (worktree
`SpectraSynq_K1_Firmware-vj-lane`)

| Artefact | Role |
|----------|------|
| `FINDING-rms-cannot-separate.md` | RMS is dead as music/ambient separator |
| `p11-pky-soak-receipt-2026-08-06.md` | Early crest soak FAIL/INCONCLUSIVE; do not lower to ~1.7 |
| `s1-joint-break-analysis-2026-08-07.md` | Offline AND sweep; seed frac=1.25 |
| `s1-predictions-joint-and-2026-08-07.md` | Falsifiable J1–J4 |
| `s1-predictions-brk210-2026-08-07.md` | Crest-only prediction set (historical) |
| `s1-crash-loop-recovery-2026-08-07.md` | Safe-mode null LED path |
| `s1-driven-*-receipt-2026-08-07.md` | Driven soak receipts |
| `s2-soak-dataset-2026-08-07.md` | Dataset sentence / RS notes |
| `docs/superpowers/specs/2026-08-07-silence-peakiness-auto-design.md` | Slice 1/2 design (Slice 2 build-gated) |

Main checkout scratch HCI: `_scratch/deck16_tab5_k1_proof_20260807/`.

---

## 7. Thinking models that would have shortened this session

| Model | Forced question we skipped too long |
|-------|-------------------------------------|
| **Systems** | What complementary axis exists when crest alone has empty OP? |
| **Map–territory** | Which statistic is a map of "quiet" vs the acoustic territory? |
| **Steel-man** | Strongest case for OR / crest-only / RMS-learn — then kill with data |
| **Red team** | How does this soak lie? (no music, wrong port, post-hoc threshold) |
| **OODA** | Observe distributions → Orient overlap → Decide AND → Act flash |
| **Model router** | Domain=coding+debug+product silence UX → scientific + systems first |

Invoke `/thinking-model-router` before the next silence or BLE "obvious fix."

---

## 8. Encoding surfaces (so this sticks)

| Surface | Path | Job |
|---------|------|-----|
| **This canon** | `docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md` | Full inventory + evidence map |
| **Skill** | `.claude/skills/k1-vj-session-discipline/SKILL.md` (+ `.cursor` / `.codex`) | HARD FAIL checklist at task intake |
| **Spec index** | `docs/spec-index.md` | Discoverability |
| **Architecture** | `K1_DECK16_ARCHITECTURE_R1.md` | Product identity |
| **Static tests** | `tests/test_boot_palette_lock_static.py`, `tests/test_session_canon_2026_08_07_static.py` | Mechanical non-regression |
| **Hardware bring-up skill** | `.claude/skills/hardware-bringup/SKILL.md` | Pointer for board/peripheral work |

---

## 9. Explicit open items (do not mark closed)

- Joint night soak J1–J4 after crash recovery — **parked** until Captain eyes-on
- Daytime D1/D2 soaks — queued
- Slice 2 learner writer — design approved with corrections; **not built** until multi-day dataset
- Tab5 C6 HCI root cause — **not established**; software diagnosis continues under binding flags
- Uncommitted vj-lane dirty tree (silence AND, crash guards, Tab5 BLE retarget, boot show lock) — commit only when Captain asks and gates pass
)

---

### Update — 2026-08-12: joint fraction corrected (value AND transfer rule)

Landed with the `fix/im69d-rms-gate-and-gain-20260811` merge. Full evidence:
`docs/canon/SESSION_CANON_2026-08-12_device_evidence_integrity.md` (HF-29…HF-40),
`docs/forensics/unit2-bench-transfer-full-2026-08-12.md`, commits `9599714b` / `a8b1912a`.

1. **Value:** `K1_SILENCE_JOINT_LEVEL_SSL_FRAC = 1.75` (was seed 1.25, then 2.5 on Unit 2).
   The 2.5 was fitted against Unit 2's **stale** SSL=136; after in-situ recalibration
   (Captain silence-go, witness-verified room) SSL moved 136→167/229-series and the usable
   window re-derived to 1.75 — ~70% above the worst quiet p95 (1.03), ~18% under the worst
   music p25 (2.13). Both units then held silence 100% under true silence and 0% under music.
2. **Transfer rule:** the earlier "PER-UNIT, PER-ROOM, do not inherit" framing is **wrong** —
   it was an artefact of comparing a freshly calibrated unit against a stale one.
   Corrected rule: **calibrate at final placement, then the fraction TRANSFERS.** Placement
   is carried by SSL, which is what SSL is for.
3. **Scope:** the joint gate DECISION is now compiled only under `K1_MIC_IM69D_PDM_V1`
   (`a8b1912a`); SPH0645 production keeps its own characterised RMS Schmitt. Static ratchet:
   `test_joint_silence_gate_is_scoped_to_im69d`.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Appended fraction correction (1.75, transfers after final-placement cal) + IM69D scoping; superseded marker on §8 item 7. Owed at merge per HANDOVER_2026-08-12_im69d_rms_gate.md. |
| 2026-08-07 | agent:claude-code | Created (session canon, HF-1…HF-13). |
