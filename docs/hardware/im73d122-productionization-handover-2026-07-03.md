---
abstract: "Handover for the IM73D122 productionization lane (2026-07-03). IM73D is the Captain-RATIFIED K1 production mic — selection is CLOSED. Bench runs the full production-candidate stack (3e06f9d): PDM front-end G=16, PDM-domain cal gates, persistent cal, tuned Waveform-Fast margin. Next mission: Phase 1 firmware productionization, starting with un-freezing config persistence under the PDM flag. Contains deployed state, proven-facts ledger, freeze inventory, key numbers, operational scars (serial ':' prefix, N/Y silence gate, MAC-not-port identity), and the phase roadmap."
---

# IM73D122 productionization handover — 2026-07-03

Supersedes `im73d122-graft-handover-2026-07-02.md` for lane state (that doc's
7 gotchas remain valid background). Read order for a fresh agent: this file →
`docs/hardware/device-build-registry.md` (deployed-state table) →
`_scratch/im73d_bringup/eyes-on-runbook.md` (sweep evidence + tuning verdict).

## 0 · Mission

**Phase 1 firmware productionization.** First task: **un-freeze config
persistence under `K1_MIC_IM73D_PDM_V1`** (§4). Then: `MicFrontend`
abstraction, test/gate migration, DSR_16S evaluation, production-flip
red-team. Phases 2–3 in §5.

## 1 · Decision state (do not reopen)

- **IM73D122 = K1 production microphone. Captain-ratified 2026-07-03.**
  ("We're keeping the im73d as production.") Selection is CLOSED; remaining
  work is productionization and tuning. Memory: `im73d-production-decision`.
- G=16 stays. Loud side already leans on the loud guard (rail kissed at
  close-range full-volume; guard trimmed to 0.758, clip ≤0.2%) — registry note
  "do NOT bump g=16" stands.
- Quiet-music partial gating (~20–35% duty at background volume) is
  **acoustically intrinsic** — quiet music overlaps the room's silence band;
  no threshold can separate them. Post-launch fix = presence-hysteresis
  feature (Phase 3), not more threshold surgery.

## 2 · Deployed state

| Device | Identity | Build | State |
|---|---|---|---|
| Bench K1v2 | `B4:3A:45:A5:89:B4` / chip `B489A500` | **`3e06f9d`** `k1_bench_im73d` | Full production-candidate IM73D stack. `cal_valid=1 cal_source=persisted_profile SSL=979 DC=10` — survives cold boot AND app reflash. |
| Main K1 (production) | `B4:3A:45:A5:87:F8` / chip `F887A500` | `2e2800d` `k1_hardware` (SPH0645) | **First-ever measured cal 2026-07-03**: `SSL=360 DC=−5722 cal_source=measured`, persisted to NVS. DC bias is real hardware (autopsy pending when mic is swapped). |

Lane `lane/im73d-pdm-eval`, chain since graft review:
`db3597c` (freeze factory_reset/restore_defaults) → `95faa9f` (silence-figure
correction) → `96d908a` (PDM cal-gate window 650→1000 / 720→1150, Outcome B
from 8 measured runs) → `85a6dc0` (PDM cal persistence, own file) → `3e06f9d`
(Waveform-Fast margin 1.10→0.95 PDM-gated) + registry commits. All through the
full commit gate; all device-proven.

## 3 · Proven facts (with evidence)

1. **Graft + cal pipeline**: PDM RX on live AP+VP, N/Y cal accepts in true
   silence (`SSL=979` learned, p90 890, 112/112 frames), rejects music
   (1040–1219) — the widened gates still discriminate.
2. **Persistence**: `/cal_profile_pdm.bin` (PDM-namespaced; SPH files frozen).
   Proven across cold boot AND firmware reflash (LittleFS untouched by app flash).
3. **Snappiness attribution** (3-SSA fan-out + simultaneous dual-device
   capture): attack latency UNCHANGED (drive recurrence is ratio math, ≤1 AP
   frame both mics); the perceived snap = honest floor position inside the
   music envelope (VP gate duty-cycling) + ~2× wider front-end dynamics
   (span 10.0× vs 5.8×, same audio same moment) + degraded SPH baseline
   (was uncalibrated + loud-guard trimming). `_scratch/im73d_bringup/snappiness/SYNTHESIS.md`.
4. **Three-volume sweep** (agent-run, Anchor Point ×3 volumes, both devices
   calibrated): quiet 30%→ (margin trim) 22% gated duty predicted, device-
   verified −8 pts on re-run (42%→34% on that run's quieter envelope);
   normal 5%, loud 1% with guard-managed headroom. Runbook update section.
5. **Main-K1 SPH envelope** (for any future comparison): music p50 1499–2968,
   never near rail; the registry's "14.9k–30.5k" row is the PDM bitstream
   misread through the STD driver — NOT SPH audio. Do not repeat that conflation.

## 4 · Freeze inventory — and the first task

Still frozen under `K1_MIC_IM73D_PDM_V1` in `persistence/bridge_fs.h`:
`save_config()`, `save_config_delayed()`, `save_ambient_noise_calibration()`,
`factory_reset()`, `restore_defaults()`. Un-frozen already: cal profile
save/clear (PDM-namespaced `/cal_profile_pdm.bin`).

**Consequence: knob/mode/brightness changes DO NOT persist on IM73D builds.**
Fine for the eval; unshippable. First task = extend the namespacing pattern:
- PDM config → own file (e.g. `CONFIG_FILE` → `/CONFIG_PDM_<ver>.BIN` under
  the flag, mirroring the cal-file pattern at bridge_fs.h `CAL_PROFILE_FILE`).
- Load path: `load_config()` must prefer the PDM file under the flag (fall
  back to compiled defaults, NEVER the SPH config file — its SENSITIVITY etc.
  are SPH-domain-adjacent but its cal fields are poison; note the boot
  force-invalidate in `system.h` currently scrubs cal fields regardless —
  KEEP that ordering, and mind the documented load-bearing adjacency comment).
- `save_ambient_noise_calibration` (noise_cal.bin): the PDM cal profile
  already stores noise_samples — decide whether a separate PDM noise file is
  needed at all (probably not; document the decision).
- `factory_reset`/`restore_defaults`: under the flag they should clear ONLY
  PDM-namespaced files. SPH files stay untouchable until the SPH is retired.
- Static tests pin base defines by text (`test_calibration_profile_static.py`
  147-152) — `#undef` overrides keep them green; follow that pattern.

### Update — 2026-07-04: Phase 1.1 firmware LANDED (`e2b62b5`), device-proof pending

Config persistence is un-frozen under the flag via the PDM namespace:
`update_config_filename()` is the single choke point → `/CONFIG_PDM_%05lu.BIN`
(every config reader/writer routes through `config_filename`). Un-frozen:
`save_config`, `save_config_delayed`, `factory_reset`, `restore_defaults`
(resets delete ONLY PDM files; `/noise_cal.bin`, SPH config/profile and preset
slots preserved + logged). Decisions closed: **no separate PDM noise file**
(`save_ambient_noise_calibration` stays frozen — PDM noise_samples persist
inside `/cal_profile_pdm.bin`), and `load_ambient_noise_calibration` is now
SKIPPED under the flag (never read SPH-domain noise floors). `system.h`
force-invalidate ordering untouched; its stale "NVS is frozen" comment fixed.
Golden `bridge_fs_config` re-frozen (intentional change; rec2/update_config_filename
only; MANIFEST recomputed; Gate Fα green). Gate: pytest 620 pass + `k1_hardware`
+ `k1_bench_im73d` builds green. Two initial pytest failures were mine and
textual: a comment mentioning the cal-save function moved a static test's
region anchor (reworded), and the golden pinned the intended body change.

**Remaining for Phase 1.1 (bench was disconnected from USB at the time):**
flash `e2b62b5` (guard-verified) → `:build` proof → cal regression check
(`persisted_profile SSL=979` must survive the reflash) → knob persistence proof
(set knob via `:` command → ≥5 s → `:reset` → `:dump` knob survived) → registry
deployed-state row. First boot on `e2b62b5` has no `/CONFIG_PDM_*.BIN` →
compiled defaults (expected, not a regression); the file appears after the
first knob save.

## 5 · Phase roadmap (Captain-acknowledged 2026-07-03)

- **Phase 1 (now, no hardware dependency):** (1) config persistence un-freeze
  ← START HERE; (2) `MicFrontend` abstraction (retire ~7-file ifdef sprawl;
  SPH byte-identical until flip); (3) test/byte-gate migration; (4) DSR_16S
  +2 dB evaluation; (5) production-flip readiness red-team.
- **Phase 2 (Captain-gated):** hardware switch timing (main-K1 rewire vs PCB
  rev; needs production GPIO map PDM pins — bench 12/13/14 was bench-only);
  BOM/supply diligence (IM73D122, Infineon); factory/first-boot cal UX;
  SPH autopsy on main K1 (DC −5722).
- **Phase 3 (post-launch polish):** presence-hysteresis for quiet music;
  PDM-domain sweep of other SSL consumers (waveform_hybrid runtime margin
  clamps ≥1.00; `lightshow_modes.h:789` SSL×2; VU floors); real-speaker loud
  characterization.

## 6 · Key numbers

| Constant / value | SPH (flag-off) | IM73D (flag-on) |
|---|---|---|
| Input gain | pedestal math ×0.000512>>2 | `K1_MIC_IM73D_INPUT_GAIN` **16.0f** |
| SENSITIVITY | 2.4 | 2.4 (shared) |
| Cal window: TRUSTED_P90 / MAX_VALID | 650 / 720 | **1000 / 1150** (measured-derived) |
| Boot SSL fallback | 350 | **120** |
| Waveform-Fast margin | 1.10 | **0.95** |
| Learned floor (this room) | 360 (main K1) | 979 (bench) |
| Music envelope (same audio) | p50 1.5–3k | p50 4.6–8.6k, max 14–32k |
| Silence p90 (this room) | ~300 | ~806–890 |

## 7 · Operational doctrine (scars — every one cost a session)

1. **Serial `:` prefix is LAW.** Bare bytes are live hotkeys (`check_serial`).
   Unprefixed command strings spray state mutations (2026-07-02 incident:
   SENSITIVITY 2.4→3.4 etc.; recovered via `:reset`). Only sanctioned bare
   keys: `N`, `Y` — and ONLY after Captain's verbal silence-go.
2. **The cal silence gate is ABSOLUTE and Captain-personal.** Auto-firing N/Y
   on inferred authorization ("unrestricted use" + measured silence) was a
   VIOLATION (2026-07-03, memory `cal-silence-gate-never-waived`). Words
   equivalent to "silence-go" in the current conversation, every time.
3. **Identity = USB MAC, never port names.** Drift log: bench 12201→1101→101;
   main 1401→2101→1101 (yesterday's bench port became the MAIN K1). Every
   script identity-gates before open; DTR/RTS held low (no reset).
4. **The Bash sandbox can hide /dev** — empty `ls /dev/cu.*` is NOT proof of
   absence; verify unsandboxed + `ioreg` (locationID 0xXY00000 ↔ usbmodemXY01).
5. **Upload guard**: fail-closed for registered envs; validates the GIVEN
   port's USB serial. CLI re-check: `python3 scripts/platformio/k1_upload_guard.py
   --env k1_bench_im73d --upload-port <port>`. `k1_bench_im73d` is registered
   to B489A500 ONLY.
6. **Commit gate tiers** (pre-commit hook): docs→none; tests→pytest; firmware/
   platformio.ini→pytest + `pio run -e k1_hardware`. If the gate is red on
   arrival, fix the gate class first. Corrupt `.pio` cache → clean rebuild.
7. **Registry discipline**: update `docs/hardware/device-build-registry.md`
   AFTER device-proof (`:build` = env+git on the device), not after upload.
8. **Cursor's serial-monitor tab** holds the port (Resource busy) AND turns
   stray typing into hotkeys — have Captain close it before serial work.
9. **The rtk tee wrapper truncates long tool output** — redirect to a file
   and analyze the file; `RC` from a pipeline is the LAST command's.
10. **"Waves" = Anchor Point.** The requested track doesn't exist on disk;
    Anchor Point is the project's canonical analysis track and was the
    Captain-accepted substitute.
11. **Concurrent lanes exist** (e.g. `lane/palette-vibrancy-v1`). Never commit
    on whatever branch the canonical tree happens to be on — verify, and use
    a worktree for cross-lane commits (established pattern, many under
    `/private/tmp/k1_*`).

## 8 · Evidence map

- `docs/hardware/device-build-registry.md` — deployed-state rows (canonical).
- `_scratch/im73d_bringup/eyes-on-runbook.md` — sweep results + tuning verdict.
- `_scratch/im73d_bringup/snappiness/` — SYNTHESIS.md, SSA evidence, dual logs,
  sweep timeline, analyzers (`sweep_analyze.py`, `dual_ap_capture.py`).
- `_scratch/im73d_bringup/` — capture/cal tooling (`silence_cal_ny.py`,
  `watch_and_cal_v2.py`, `post_flash_proof.py`, `main_k1_cal_ny.py`,
  `read_serial.py`), incident logs.
- Project memories: `im73d-production-decision`, `cal-silence-gate-never-waived`,
  `k1-serial-colon-command-surface`, `im73d-pdm-snr-modes`.

## 9 · Captain-gated vs autonomous

- **Autonomous**: all Phase 1 firmware (behind the flag, bench-proven, gated
  commits), bench flashes (guard-verified), passive captures on either device,
  BOM data gathering.
- **Captain only**: any cal firing (verbal silence-go), hardware-switch timing,
  BOM call, factory-cal UX direction, default-env flip, main-K1 flashes,
  anything perceptual (eyes-on).

## 10 · Update — 2026-07-06: Item-3 productionization audit + production-flag plan + Captain hardware-fork decision

Ran the productionization audit the triple-lane handover queued. Findings are
verified against the code on `lane/im73d-pdm-eval` at lane consolidation
(`55c536b` = merge of the vibrancy fix into this lane), not carried from prose.

### 10.1 · Live state of every bench-specific surface (audited 2026-07-06)

| Surface | Status | Anchor |
|---|---|---|
| Config-persistence un-freeze | **Firmware DONE (`e2b62b5`, 07-04) AND deployed** — verified `79d7fda ⊇ e2b62b5`, so the un-freeze code ships on the current bench build. | `bridge_fs.h:81` "un-frozen 2026-07-04"; `update_config_filename()` → `/CONFIG_PDM_%05lu.BIN` |
| Knob-persistence DEVICE-proof | **OWED** — the code ships, but "set knob via `:` → `:reset` → `:dump` survived" was never captured. Autonomous bench task (a config test, NOT an SNR test → any IM73D bench build is fine; radio-free `k1_bench_im73d` is cleanest). | no proof row in registry/`_scratch` |
| PDM pins | **BENCH-ONLY BY CONSTRUCTION.** `K1_PDM_CLK/DIN/LR_PIN` (13/12/14) exist ONLY inside `#if SB_K1_BENCH_REFERENCE_PINMAP → #ifdef K1_MIC_IM73D_PDM_V1`, overlaying the SPH bench pads (BCLK14/DIN13/LRCL12). The production `#else` branch (SPH BCLK=13 / LRCLK=11 / DIN=14, LEDs 6/7) has **no PDM pin block** → the graft cannot compile into `k1_hardware` today. This is the hardware-fork blocker. | `constants.h:297-345` |
| Input gain 16.0f | As documented; bench-characterized on an OPEN bench (SPH target ~7000 / IM73D obs 1317 → ×16). Enclosure re-characterization = Phase 2 (needs production hardware). | `constants.h:67-70` |
| SSL cal window | **"widen not bump" lever already pulled** — 650/720 → 1000/1150; silence p90 ~807 of 1150 = healthy headroom now. The "710-of-720" tightness predates the widen and is resolved. | `constants.h:40-60` |
| ifdef sprawl | **34** `K1_MIC_IM73D_PDM_V1` sites across 7 files (`bridge_fs.h` 13, `i2s_audio.h` 10, `system.h` 3, `constants.h` 3, `noise_cal.h` 3, `globals.h` 2, `platformio.ini` 2). This is the `MicFrontend` retirement target. | `git grep` |
| flag-OFF byte-identity | SPH `i2s_std` path untouched when flag OFF; `k1_hardware` byte-identical. Invariant to preserve through all production-flag work. | — |

**Net:** the handover's framing of "replace eval-era freeze with Phase 1.1
persistence" as pending is now stale — at the firmware level it is DONE and
deployed. The genuinely-open Phase 1 items are (a) the knob-persistence device
capture (owed, small), (b) the `MicFrontend` abstraction (Phase 1.2, the main
autonomous firmware), (c) DSR_16S eval, (d) production-flip red-team. None of
(a)-(d) needs new hardware. The ONE hard blocker that does need hardware truth
is the production PDM pin map — see §10.3.

### 10.2 · Production-flag plan (`K1_MIC_IM73D_PROD_V1`) — autonomous, steps 1-3 need no hardware

1. **Production PDM pin block.** Add `K1_PDM_CLK/DIN/LR_PIN` to the production
   `#else` branch (`constants.h`) guarded by `K1_MIC_IM73D_PROD_V1`. Until Captain
   confirms the PCB (§10.3), stamp a **PROVISIONAL** mapping = the production SPH
   pad trio (`BCLK 13 / DIN 14 / LRCLK 11`) as the most-likely same-footprint swap,
   clearly marked provisional. This lets Phase 1 firmware compile + host-gate
   without waiting on hardware.
2. **Promote the flag path, keep it revertible.** `K1_MIC_IM73D_PROD_V1` selects
   PDM in `init_i2s()`, the PDM read path, cal invariants, and the PDM-namespaced
   persistence — reusing the existing `K1_MIC_IM73D_PDM_V1` machinery, not a fork.
   SPH stays the default (flag OFF = byte-identical) until the production unit is
   device-proven.
3. **`MicFrontend` abstraction (Phase 1.2).** Collapse the 34-site ifdef sprawl
   behind one seam (init / read / gain / cal-domain / persistence-namespace).
   SPH byte-identical until the flip; bench IM73D unchanged. This is the largest
   remaining autonomous firmware lane — scope it as its own branch.
4. **Gates:** host (pytest + `k1_hardware` byte-identity flag-OFF) → bench proof
   (the bench IS the IM73D reference) → **production-unit** device proof (needs
   §10.3) → Captain silence-go recal on the production unit → eyes-on.

### 10.3 · Captain hardware-fork decision (ACCEPT / REJECT — recorded, not executed)

**Current state:** IM73D is the ratified production mic; all Phase-1 firmware can
be prepared behind `K1_MIC_IM73D_PROD_V1` with a PROVISIONAL pin map. The one
thing firmware cannot invent is the **production PDM pin map** (which GPIOs the
production PCB routes the IM73D CLK/DATA/SELECT to) and the **switch timing**.

**Decision required (two coupled sub-decisions):**
- **D1 — production PDM pin map.** (A) Same-footprint swap on the SPH0645 pads
  → PDM on the production trio `{13, 11, 14}` (firmware provisional assumes this);
  (B) dedicated PDM pins on a PCB rev → Captain supplies the trio.
- **D2 — switch timing.** (A) Hand-rewire the existing main-K1 unit now (like the
  bench) for early production-unit device-proof; (B) wait for a production PCB rev
  with the IM73D placed.

**Recommended path:** Firmware proceeds autonomously through §10.2 steps 1-3 with
the PROVISIONAL `{13,11,14}` map NOW (no hardware needed, fully revertible, SPH
default). Captain confirms **D1** when the PCB layout is fixed and **D2** when the
main-K1/PCB timeline is set — at which point firmware swaps the provisional map
for the confirmed trio (a one-line change) and the production-unit device-proof
runs. This unblocks all no-hardware firmware immediately and reserves for Captain
only the two decisions that genuinely require product/PCB truth.

**Blast radius:** none until a production unit is flashed — everything is behind a
default-OFF flag; SPH `k1_hardware` stays byte-identical. Mic selection is NOT
reopened (ratified 2026-07-03).

**Default if Captain does not respond:** firmware stops after §10.2 step 3
(host+bench-proven, provisional map) and does NOT flash any production unit or
flip any default — the SPH main K1 is untouched.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-03 | agent:claude-code (Fable) | Created — productionization handover after ratification, cal-gate fix, persistence, margin tune, and snappiness attribution. |
| 2026-07-04 | agent:claude-code (Fable) | Phase 1.1 firmware landed (`e2b62b5`): PDM-namespaced config persistence un-freeze; §4 update section added with device-proof protocol (bench off USB, proof pending). |
| 2026-07-06 | agent:claude-code (Fable) | §10 added: Item-3 productionization audit (code-verified live state — persistence un-freeze DONE+deployed, pins bench-only, SSL window already widened, knob device-proof owed), production-flag plan (`K1_MIC_IM73D_PROD_V1` + provisional pin map + `MicFrontend` Phase 1.2), and the Captain hardware-fork decision (D1 pin map / D2 switch timing) in accept-reject form. |
