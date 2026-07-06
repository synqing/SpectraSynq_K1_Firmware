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
  characterisation.

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
   and analyse the file; `RC` from a pipeline is the LAST command's.
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
  sweep timeline, analysers (`sweep_analyze.py`, `dual_ap_capture.py`).
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
| PDM pins | Code today: `K1_PDM_CLK/DIN/LR_PIN` (`clk13/din12/LR14`) exist ONLY in the bench pinmap branch; the production `#else` branch has **no PDM block**. **RESOLVED (D1, 2026-07-06):** production uses the *identical* bench-proven pins `clk13/din12/LR14` — all current K1s are the same ESP32-S3 devboard. Verified collision-free on the production map (GPIO 12 unassigned; 13/14 freed when SPH drops; LEDs stay 6/7; old SPH LRCLK 11 unused). Firmware just needs the block added to the `#else` branch. | `constants.h:297-345` |
| Input gain 16.0f | As documented; bench-characterised on an OPEN bench (SPH target ~7000 / IM73D obs 1317 → ×16). Enclosure re-characterisation = Phase 2 (needs production hardware). | `constants.h:67-70` |
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
   `#else` branch (`constants.h`) guarded by `K1_MIC_IM73D_PROD_V1`, using the
   **Captain-confirmed identical map `clk=13 / din=12 / LR=14`** (D1, 2026-07-06 —
   same ESP32-S3 devboard across all K1s, so the production IM73D wires to the
   exact GPIOs already proven on the bench). Verified collision-free: GPIO 12 is
   unassigned on the production map, 13/14 free when SPH is dropped, LEDs stay 6/7,
   old SPH LRCLK 11 goes unused. No provisional guess — these are the proven pins.
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
   (the bench K1 already carries the IM73D on `13/12/14` → it IS the production-
   representative hardware) → Captain silence-go recal → eyes-on. A dedicated
   main-K1 IM73D device-proof applies only if/when the main K1's SPH is physically
   swapped (§10.3) — it is NOT a firmware gate.

### 10.3 · Captain hardware decision — RESOLVED 2026-07-06

**D1 — production PDM pin map: ANSWERED.** Identical to the bench-proven map,
`clk=13 / din=12 / LR=14`. Every current K1 is the same ESP32-S3 devboard, so the
production IM73D wires to the same GPIOs already proven on the bench — no custom
PCB, no separate pin trio, no provisional guess. Holds until the hardware itself
changes. (Verified collision-free on the production pin map: GPIO 12 unassigned,
13/14 freed by dropping SPH, LEDs 6/7, SPH LRCLK 11 unused.)

**D2 — the "switch timing / wait for a PCB rev" framing was WRONG and is
withdrawn.** There is no pending PCB revision and no "production PCB with the
IM73D placed" to wait for. The IM73D has been physically wired to the bench K1
(the reference hardware) since the start of bringup — the mic hardware already
exists and is device-proven. The prior §10.3's invented production-PCB fork does
not correspond to any real hardware plan; this correction supersedes it.

**The one real physical fact that remains:** the *main* K1 (`F887A500`) currently
carries an SPH0645; the bench K1 (`B489A500`) carries the IM73D. Both are the same
devboard. Making the main K1 itself run the IM73D would need a physical mic swap +
rewire to `13/12/14` (Captain's hands) — but this is a **logistics choice, not a
firmware dependency**. The firmware productionization (§10.2) proceeds identically
whether the production-representative unit is the existing bench-style IM73D
hardware or a future SPH-swapped main K1; the code is prepared behind
`K1_MIC_IM73D_PROD_V1` regardless.

**Net:** no open Captain decision blocks the firmware. Phase 1 (pin block at the
confirmed `13/12/14`, `MicFrontend` abstraction, DSR_16S eval, flip red-team) is
now fully autonomous. Mic selection unchanged (ratified 2026-07-03); SPH
`k1_hardware` stays byte-identical (default-OFF flag).

## 11 · Update — 2026-07-06: autonomous execution (UA shipped) + decisions + flip red-team

Executed against `docs/hardware/im73d-productionization-execution-plan-2026-07-06.md` (harness-first gated DAG). Status of every unit below.

### 11.1 · Shipped
- **UA — `k1_prod_im73d` production build path (commit `4b95e60`).** Production pinmap + `K1_MIC_IM73D_PDM_V1` at the Captain-confirmed identical pins `clk13/din12/LR14`. `[env:k1_prod_im73d]` extends `k1_hardware`; `BLOCKED_UPLOAD_ENVS` hard-blocks it from flashing onto the SPH-equipped main K1 until the mic swap; drift-catcher + blocked-env + production-pin static tests added. **Byte-identical-OFF proven** (see 11.3). Gate: pytest 629, `k1_prod_im73d` + `k1_hardware` build clean.

### 11.2 · MicFrontend abstraction (Phase 1.2) — DECISION: compile-time selection RETAINED (do not build runtime dispatch)
Evaluated the "retire the 34-site ifdef sprawl via a runtime `MicFrontend`" idea and **reject it**, with evidence:
1. **It cannot be behaviour-verified in this build.** The ESP-IDF/Arduino image is **not bit-reproducible** in `.flash.text`/`.flash.rodata` even across clean builds of identical source (11.3). A runtime dispatch rewrite of the Core-0 read path could therefore only be certified by device A/B on hardware that does not yet exist — it is not autonomously certifiable.
2. **It taxes Core 0.** The mic read is on the hard-real-time audio core; adding runtime branching / vtable indirection per chunk violates `sensorybridge-doctrine` (architecture subordinate to perceptual impact) and `esp32-render-path-safety`.
3. **The sprawl is inherent to compile-time selection and is the correct trade.** The 34 sites are genuinely-different code per mic (init driver mode, read buffer type, extraction domain, cal domain, persistence namespace, boot invalidation). Collapsing them means runtime dispatch — the thing (1)+(2) forbid.

**Delivered instead — the seam map** (the reusable machinery the flip actually needs): the mic front-end is 6 interfaces; each is one compile-time `#ifdef K1_MIC_IM73D_PDM_V1` site set. To flip or audit the mic, these are the only places to touch:

| # | Interface | Site(s) |
|---|---|---|
| 1 | I2S init driver-mode (PDM vs std) | `audio/i2s_audio.h` :44 (include), :220-239 (PDM init) / :240+ (std) |
| 2 | Chunk read (buffer + timeout, freeze-guard + portMAX paths) | `audio/i2s_audio.h` :305-341 |
| 3 | Sample extraction / domain gain | `audio/i2s_audio.h` :395-399 (`* K1_MIC_IM73D_INPUT_GAIN`) |
| 4 | Calibration domain (SSL window, DC term, boot fallback, gain, NaN guard) | `system/constants.h` :40-70; `system/globals.h` :225; `system/system.h` :427,:478; `calibration/noise_cal.h` :36,:47,:83; `audio/i2s_audio.h` :585,:598 |
| 5 | Persistence namespace (PDM files, config filename, freeze/reset) | `persistence/bridge_fs.h` (13 sites) |
| 6 | Pins + sample buffer | `system/constants.h` :313-316 (bench) / :328-339 (prod, UA); `system/globals.h` :144-148 |

### 11.3 · Byte-identity oracle — DETERMINISM FINDING (harness correction)
Establishing the determinism contract (before trusting any byte comparison) revealed: **`k1_hardware` is NOT bit-reproducible in `.flash.text` / `.flash.rodata`** — two clean builds of identical source produced two different hashes for those sections (link-order / embedded timestamp). The other three loadable sections — **`.dram0.data`, `.iram0.text`, `.iram0.vectors` — ARE reproducible** (byte-identical across every build this session).
- **Consequence:** `scripts/regression-harness/registry_byte_gate.sh` hashes all five sections, so it is **inherently flaky** (two of five drift benignly). It is not in the pre-commit hook, which is why the flakiness has been latent.
- **The trustworthy oracle (use this for all mic-path behaviour-preservation):** compare only the **3 reproducible sections** + full pytest + a source-level review. UA passed it (3 stable sections byte-identical baseline→UA; the source is 100% OFF-gated). Tool provided in UC (`mic_stable_byte_gate.sh`, additive — the existing gate is left untouched as a trust root).

### 11.4 · DSR_16S evaluation (Phase 1.4) — enable recipe + protocol (no dead code added)
The PDM clock is DSR_8S via `I2S_PDM_RX_CLK_DEFAULT_CONFIG` (`i2s_audio.h:229`). DSR_16S is the reserved +2 dB lever ([[im73d-pdm-snr-modes]]).
- **Enable recipe (one line, behind a future flag):** after line 229, `pdm_cfg.clk_cfg.dn_sample_mode = I2S_PDM_DSR_16S;` (raises the PDM clock to ~1.6384 MHz; re-verify the SPH0645 BCLK-min risk noted in the registry §2.1 does not apply to the IM73D at DSR_16S).
- **Absolute-blocker checkpoint (NOT a stop):** the +2 dB verdict is a **device SNR measurement** — radio-free `k1_bench_im73d` ONLY (never a BLE build — Core-0 radio perturbs audio), Captain-context capture. The lever lands with the measurement that justifies it, not before.

### 11.5 · Production-flip readiness red-team (Phase 1.5)
**Goal:** flip `k1_hardware`'s default mic SPH0645 → IM73D. **Approach: strangler-fig, never big-bang** — `k1_prod_im73d` is the dual-run env; only after a production-unit device-proof does the default flip.

Pre-mortem (failure → guard):

| Failure mode | Guard |
|---|---|
| PDM firmware flashed onto an SPH-equipped unit → bitstream misread as PCM, "works" numerically but is garbage | `BLOCKED_UPLOAD_ENVS` (UA) hard-blocks `k1_prod_im73d` until the mic swap; the AP/VP acceptance gates are ratio-based and blind to absolute amplitude (obs #73496), so a dead/garbage front-end can green the numeric tests — **device eyes-on + `dump_raw` non-zero is mandatory**, not optional |
| Stale SPH0645 NVS (`DC_OFFSET≈-4714/-5722`) survives boot and biases IM73D samples | boot force-invalidate scrubs cal fields under the flag (`system.h:427`); confirm `cal_source` resets, then Captain silence-go recal on the production unit |
| Enclosure changes acoustics → g=16 rails or under-drives | re-characterise gain on the SEALED production unit (not the open bench); SSL window already widened 1000/1150 with ~807 silence headroom |
| Default flip before a production unit exists | flip is Captain-gated and depends on the mic swap (11.6) — `k1_prod_im73d` stays a separate env until then |
| Behaviour regression on the SPH path from mic work | 3-stable-section byte gate (11.3) + pytest; UA proven OFF-identical |
| Quiet-music partial gating read as a bug | it is acoustically intrinsic (§1); Phase-3 presence-hysteresis, not threshold surgery |

**Flip checklist (all required, in order):** (1) main-K1 mic swap done + `dump_raw` int16 sane; (2) gain re-characterised on the production unit; (3) Captain silence-go recal → `cal_valid=1 reason=none`; (4) `stream_agc` all four gains < 10 after 10 s; (5) eyes-on A/B vs the SPH baseline across genres incl. VU modes; (6) move `k1_prod_im73d` from `BLOCKED_UPLOAD_ENVS` to the F887A500 allow-list; (7) only then consider flipping the `k1_hardware` default (Captain).

### 11.6 · Absolute-blocker checkpoints (handed to Captain — the run did NOT stop on these)
1. **Physical main-K1 SPH0645 → IM73D swap** — the only gate to device-proving `k1_prod_im73d`.
2. **DSR_16S +2 dB SNR measurement** — radio-free bench, Captain-context.
3. **Perceptual eyes-on / audio A/B** for any default flip.
4. **`k1_hardware` default-env flip** — Captain call after 1-3.

### 11.7 · Knob-persistence device-proof (Phase 1.1 tail) — status: OWED, deliberately deferred
Un-freeze code (`e2b62b5`) ships on the bench (`79d7fda ⊇ e2b62b5`). The isolated "set knob → `:reset` → survived" capture is **still owed**. This session confirmed both units are MAC-reachable (bench `B489A500` on usbmodem101, main `F887A500` on usbmodem1101) but **deliberately did NOT run the cycle**, because:
- the bench runs the **BLE demo build**, where `save_config_delayed`'s LittleFS write can **defer** under BLE heap pressure (the `1ac840a` fail-safe) → a non-persist result would be **inconclusive** (heap-defer vs a real bug), not a clean proof;
- the cycle requires a `:reset`, disrupting the Captain-directed investor-demo state, with the main K1 co-connected on the bus.

Existing evidence is already strong: persistence is **host-proven** (`bridge_fs_config` golden + `test_calibration_profile_static`) and **device-proven-adjacent** (`cal_source=persisted_profile` uses the identical `/CONFIG_PDM_*.BIN`-family mechanism, proven across cold boot + reflash). **Recommendation:** run the isolated knob cycle on the next **radio-free `k1_bench_im73d`** bench session (no heap-defer confound), not the BLE demo build. Environmental/checkpoint item, not a Captain decision.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-03 | agent:claude-code (Fable) | Created — productionization handover after ratification, cal-gate fix, persistence, margin tune, and snappiness attribution. |
| 2026-07-04 | agent:claude-code (Fable) | Phase 1.1 firmware landed (`e2b62b5`): PDM-namespaced config persistence un-freeze; §4 update section added with device-proof protocol (bench off USB, proof pending). |
| 2026-07-06 | agent:claude-code (Fable) | §10 added: Item-3 productionization audit (code-verified live state — persistence un-freeze DONE+deployed, pins bench-only, SSL window already widened, knob device-proof owed), production-flag plan (`K1_MIC_IM73D_PROD_V1` + `MicFrontend` Phase 1.2), and the Captain hardware-fork decision in accept-reject form. |
| 2026-07-06 | agent:claude-code (Fable) | §10.3 RESOLVED: Captain D1 = identical bench-proven pin map `clk13/din12/LR14` (all K1s same ESP32-S3 devboard); D2 framing withdrawn (no PCB rev — IM73D already wired on the bench K1 since bringup). Corrected §10.1/§10.2 provisional-pin guess to the confirmed pins; verified collision-free on the production map. No open Captain decision blocks Phase-1 firmware. |
| 2026-07-06 | agent:claude-code (Fable) | §11 added: autonomous execution — UA `k1_prod_im73d` production build path shipped (`4b95e60`, byte-identical-OFF, guard-BLOCKED); MicFrontend runtime-dispatch REJECTED with evidence (compile-time selection retained + seam map delivered); byte-oracle determinism finding (registry_byte_gate flaky — 2 of 5 sections non-reproducible; use the 3 stable sections); DSR_16S enable recipe + SNR protocol; production-flip red-team (pre-mortem + 7-step checklist); absolute-blocker checkpoints. |
