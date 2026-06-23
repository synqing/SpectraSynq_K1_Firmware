---
abstract: "Agent handover (2026-06-07) — silence anti-creep + secondary dark-state lane. Branch wip/audio-saliency-recovery @ 9288c84 with UNCOMMITTED local changes. Primary anti-creep materially fixed (eyes-on PASS). Secondary dark-state root-caused (Waveform Tempo mode 18), patch SHIPPED+FLASHED to 1401, Captain eyes-on NOT YET RE-RUN. Dense Forge starvation remains separate blocked lane. Read §2 locked decisions before touching anything."
---

# Handover — Secondary dark-state fix + silence anti-creep (2026-06-07)

> **Read top-to-bottom before acting.** Verified against live repo state at handover time.
> Supersedes prior handovers on **silence creep / secondary darkness / Dense Forge acceptance** only.
> For tempo primitive history see `docs/handover/2026-06-05-cto-session-handover-3.md`.

---

## 0 · Role & what the Captain wants

You are continuing **K1 firmware product acceptance** work on the Smart Auto candidate (1401).

**North star:** perceptual impact — architecture subordinate to eyes-on correctness.

**Captain posture:** blunt, impatient with prose without proof. **Do the test, capture evidence, report pass/fail.** Do not reopen solved lanes or propose tuning without proving the write path.

**Standing prohibitions (load-bearing):**
- Never auto-fire `start_noise_cal` (requires Captain silence confirmation).
- Never flash/erase without verifying device identity (USB MAC + chip ID).
- Never push unless explicitly instructed.
- Never commit unless explicitly instructed (all work is local uncommitted as of handover).

---

## 1 · One-paragraph state

The **primary-channel silence creep** (AGC chasing to 10× in quiet room) is **materially fixed** via Phase 1B envelope-fall cap + Phase 2 VP normalization. Captain eyes-on confirmed **primary goes dark** in quiet-room silence.

The **secondary channel** failed eyes-on because **mode 18 (Waveform Tempo)** unconditionally repainted every frame from persistent history + centre chroma mapping — independent of primary Dense Forge going dark.

**Root cause documented:** `docs/forensics/runtime-evidence/2026-06-07-secondary-dark-state-last-writer-verdict.md`

**Fix implemented and flashed:** `light_mode_waveform_tempo.cpp` — dark gate drains history @ 0.82/frame and skips mapping write when `snap.silence || snap.agc_gated || !tempo_presence_ok(snap)`.

**NOT DONE:** Captain eyes-on re-test of secondary darkness after flash. **Dense Forge starvation** (primary mode 21) remains a **separate FAIL** — do not conflate with secondary lane.

**Release status:** Telemetry PASS, eyes-on FAIL (pre-fix), **release NOT accepted**.

---

## 2 · Locked decisions (do not reopen without Captain approval)

| Lane | Status | Rule |
|------|--------|------|
| Primary anti-creep | **PASS** (eyes-on) | Do not tune AGC, Phase 3 `silent_scale`, SSL/noise floor |
| Secondary dark-state | **PATCH FLASHED, eyes-on PENDING** | Only touch if re-test FAILs — narrow fixes in mode 18 or secondary render path |
| Dense Forge starvation | **FAIL (separate)** | **Do not patch until secondary eyes-on PASS** |
| Phase 3 `silent_scale ↔ agc_gated` | **BLOCKED** | Primary already dark; not justified as first response |
| Phase 2C spectrogram fast release | **BLOCKED** | No named residual source |
| Smart Director Comet allowlist | **BLOCKED** | Product routing, out of scope |

**Two-lane model (Captain-mandated):**
1. Secondary-channel darkness / render ownership
2. Dense Forge effect starvation

Keep them separate.

---

## 3 · Git & branch truth

```
Branch:  wip/audio-saliency-recovery
HEAD:    9288c84  (unchanged — all session work is UNCOMMITTED)
Status:  8 modified firmware/docs files + many untracked evidence logs
```

**Modified (uncommitted):**
| File | Change |
|------|--------|
| `SPECTRASYNQ_K1_FIRMWARE/audio/GDFT.h` | Phase 1A gated release + Phase 1B envelope-fall gain cap |
| `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` | Phase 2A max_peak decay + Phase 2B gate_gain rise cap |
| `SPECTRASYNQ_K1_FIRMWARE/audio/sb_audio_snapshot.h/.cpp` | Publish `agc_gated` on snapshot |
| `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_dense_forge.cpp` | Phase 4 inject_scale gate (`presence && !silence`) |
| `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_tempo_comet.cpp` | Phase 4 Clamp-3 spawn guards |
| `SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp` | **Secondary dark-state fix (THIS SESSION)** |
| `docs/forensics/runtime-evidence/2026-06-07-scene-policy-v2-serial-ab-state-gate.md` | Updated A/B run_id |

**Untracked evidence (commit when Captain approves canonisation):**
- `docs/forensics/runtime-evidence/2026-06-07-silence-anti-creep-verdict.md`
- `docs/forensics/runtime-evidence/2026-06-07-secondary-dark-state-last-writer-verdict.md`
- `docs/forensics/runtime-evidence/2026-06-07-k1-eyes-on-guided-retry.log`
- `docs/forensics/runtime-evidence/2026-06-07-silence-creep-*.log` (baseline + phase captures)
- `docs/forensics/runtime-evidence/2026-06-07T090803-smart-auto-ab-*` (dual-device A/B)
- `docs/forensics/runtime-evidence/2026-06-07T1401-stuck-primary-probe.log`

**Shared-branch warning:** `wip/audio-saliency-recovery` may be shared with parallel workflows. Always `git log --oneline -10` fresh. Do not force-reset. Commit small if Captain asks.

---

## 4 · Hardware map

| Port | Role | Chip ID | Env | Notes |
|------|------|---------|-----|-------|
| `/dev/tty.usbmodem1401` | **Smart Auto candidate** | `F887A500` | `k1_hardware` | Anti-creep + secondary fix **flashed here** |
| `/dev/tty.usbmodem12201` | L1 reference / bench | `B489A500` | `k1_bench_reference` | A/B capture reference device |
| `/dev/tty.usbmodem12401` | Unknown | — | — | Present on bus; verify before use |

**platformio.ini default upload:** 1401 for `k1_hardware`.

**Verify before flash:**
```bash
ls /dev/tty.usbmodem*
pio device monitor -p /dev/tty.usbmodem1401 -b 115200
# then :chip_id  → expect F887A500 on 1401
```

---

## 5 · What was fixed (mechanism, not file list)

### Primary silence creep (DONE — eyes-on PASS)

**Wrong hypothesis:** frozen gain while `agc_gated` (Phase 1A never exercised — gate never closes in quiet room).

**Actual mechanism:** envelope stays ~0.008–0.03 above `gate_close_th≈0.0025` → ungated branch chases `target_gain = 0.25/envelope` → saturates at `AGC_MAX_GAIN=10`.

**Effective fix:** Phase 1B — block upward gain chase when `envelope_falling && target_gain > agc_gain`.

**Evidence:** silence1 max gain dropped from **10.0** (baseline) to **3.04** (preflight). Full ledger: `2026-06-07-silence-anti-creep-verdict.md`.

### Secondary dark-state (PATCHED — eyes-on PENDING)

**Owner:** `light_mode_waveform_tempo()` on **secondary pass only** (mode 18 fixed; Smart Auto does not retarget secondary).

**Render chain:**
```
primary: Smart Director mode 21 (Dense Forge) → leds_16
secondary: mode 18 → leds_16 → store → leds_16_secondary
           → sb_edgemixer_lite_apply (auto scene: complementary @ 0.65)
           → show_secondary_leds() → FastLED.show()
```

**Bug:** Every frame wrote `leds_16[pos] = col` from chroma/palette with ~1.0 fade when quiet; scroll halted on `silence` but mapping did not.

**Fix (in tree + on 1401):**
```cpp
// light_mode_waveform_tempo.cpp
const bool dark_gate = snap.silence || snap.agc_gated || !tempo_presence_ok(snap);
// presence_ok mirrors Dense Forge: vu >= 0.05 && !(spec < 0.08 && novelty < 0.08)
if (dark_gate) fade = 0.82; else normal reactive fade
if (dark_gate) return;  // skip mapping write + mirror
```

**Why `tempo_presence_ok`:** Eyes-on telemetry showed `agc_gated=false` entire silence window — `silence` alone may lag ~10s (I2S SSL). Presence gate matches Dense Forge inject contract.

**Dense Forge:** excluded as secondary writer. Primary-only mode 21.

---

## 6 · Your immediate mission (hit the ground running)

### Step 1 — Confirm flash matches source

```bash
cd "/Users/spectrasynq/SensoryBridge-main 9"
pio run -e k1_hardware                    # must PASS
# optional re-flash if unsure:
pio run -e k1_hardware --target upload    # targets 1401
```

### Step 2 — Captain eyes-on: secondary dark-state re-test

This is the **gate** before any Dense Forge work or commit canonisation.

**Setup (serial 115200, device 1401):**
```
:standby_dimming=false
:smart_scene=auto
:smart_status
:edge_status
```

**Expect after `:smart_scene=auto`:**
- `SMART_DIRECTOR_AUTONOMY: on`
- `SMART_APPLIED_MODE: 21` (Dense Forge) once music plays / director settles
- `EDGE_ENABLED: on`, `EDGE_MODE: complementary`, `EDGE_STRENGTH: 0.650`
- Secondary mode stays **18** (Waveform Tempo) — not changed by smart scene

**Stimulus sequence (mirror prior guided retry):**

| Step | Action | Duration |
|------|--------|----------|
| 1 | Play music (`Regard_Ride_It.mp3` @ 125s, -3dB) | 15 s |
| 2 | Stop audio — **quiet room silence** | **30 s** |
| 3 | `:vp_status` | once |
| 4 | Captain judgement: **both channels dark?** | — |

**Music asset path (if using ffplay):** check repo `tests/` fixtures or Captain's local path from prior capture scripts (`scripts/regression-harness/smart_auto_product_ab_capture.py` references clip manifest).

**PASS criteria (Captain eyes-on):**
- Primary stays dark in quiet-room silence (already PASS pre-fix — regression check)
- **Secondary stays dark** within ~30 s silence (NEW — this is what the fix targets)

**FAIL criteria:**
- Secondary still visibly lit / creeping after 30 s silence
- If FAIL: capture `:vp_status` + `:ap_stream=on` for 10 s, save log under `docs/forensics/runtime-evidence/2026-06-07-secondary-dark-post-fix-*.log` before any new patch

**Append judgement to log file:**
```
# CAPTAIN_JUDGEMENT YYYY-MM-DD
# verdict=PASS|FAIL
# primary_channel=dark_in_silence|not_dark
# secondary_channel=dark_in_silence|not_dark
# dense_forge=accepted|still_gated_starved
```

Reference prior format: `2026-06-07-k1-eyes-on-guided-retry.log` (lines 195–200).

### Step 3 — If secondary PASS → open Dense Forge lane

Only after secondary eyes-on PASS:
- Re-run Dense Forge music check (mode 21, 20 s music, Captain visual)
- Diagnose starvation separately — Phase 4 inject gate may be too aggressive
- Do **not** fix Dense Forge by touching global AGC or secondary renderer

### Step 4 — If both lanes PASS → canonisation

Captain must approve before commit. Pre-commit gate for firmware:
```bash
pytest tests/ && pio run -e k1_hardware && git commit ...
```

Update `2026-06-07-silence-anti-creep-verdict.md` with post-fix eyes-on result.

---

## 7 · Host gate (current)

| Check | Result | Notes |
|-------|--------|-------|
| `pio run -e k1_hardware` | **PASS** | After waveform_tempo patch |
| `pytest tests/` | **174 pass, 4 fail** | Pre-existing — not introduced this session |
| Failing tests | `test_onset_beat_replay`, `test_rate_consistency` (×2), `test_semantic_state_replay` | Do not chase unless Captain asks |
| `test_k1_av_regression_static.py` | PASS (prior session) | Re-run if touching AP/VP |

---

## 8 · Key telemetry knobs (for interpreting captures)

| Signal | Meaning | Trap |
|--------|---------|------|
| `agc_gated` | AGC gate closed | Often **false** in quiet room even when visually quiet |
| `silence` (I2S SSL) | Hardware silence flag | **Lags ~10s** — do not use alone for effect gates |
| `silent_scale` | VP dimming multiplier | Captures used `:standby_dimming=false` → stays 1.0 |
| `tempo_presence_ok` | vu≥0.05 && energy/novelty | Used in new secondary dark gate |
| `inject_scale` (Dense Forge) | 0 when !presence \|\| silence | Primary-only |

**Silence1 regression stop (AP telemetry):** `agc_gain` max ≥ **9.0** = FAIL.

---

## 9 · Architecture reference (secondary render)

Read if patch fails or secondary still lit:

| File | Why |
|------|-----|
| `SPECTRASYNQ_K1_FIRMWARE.ino` ~800–850 | Secondary render pass, edge apply, store |
| `SPECTRASYNQ_K1_FIRMWARE/system/globals.h` | `SECONDARY_LIGHTSHOW_MODE = 18` |
| `SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h` | `sb_apply_smart_scene()` — edge on for auto, secondary mode unchanged |
| `SPECTRASYNQ_K1_FIRMWARE/director/sb_edgemixer_lite.cpp` | Post-effect hue mix — amplifier only, not root cause |
| `SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h` | `show_leds()` / `show_secondary_leds()` / `apply_brightness_secondary()` |

**Edge case if still lit after mode-18 fix:**
- Residual history decay too slow (0.82/frame ≈ few seconds to black — should be enough in 30 s)
- Edge mixer recolouring non-zero buffer (should drain to zero first)
- Wrong secondary mode if Captain changed `SECONDARY_LIGHTSHOW_MODE` manually
- Room noise keeping `tempo_presence_ok` true — check `:vp_status` vu/novelty

---

## 10 · Evidence index

| Document | Purpose |
|----------|---------|
| `docs/forensics/runtime-evidence/2026-06-07-silence-anti-creep-verdict.md` | Full phase 0–4 ledger + pre-fix eyes-on FAIL |
| `docs/forensics/runtime-evidence/2026-06-07-secondary-dark-state-last-writer-verdict.md` | Static last-writer proof |
| `docs/forensics/runtime-evidence/2026-06-07-k1-eyes-on-guided-retry.log` | Pre-fix guided retry + Captain FAIL |
| `docs/forensics/runtime-evidence/2026-06-07T090803-smart-auto-ab-manifest.json` | Dual-device A/B (serial/state only) |
| `docs/forensics/runtime-evidence/2026-06-07-scene-policy-v2-serial-ab-state-gate.md` | Scene policy gate doc |

---

## 11 · Explicit non-goals (this handover)

- Phase 3 global `silent_scale` coupling
- SSL / noise floor / `start_noise_cal`
- Dense Forge tuning (until secondary PASS)
- Refactoring renderer / edge mixer
- Committing or pushing without Captain instruction
- Reopening primary anti-creep tuning

---

## 12 · Skills & rules to load

1. `.claude/CLAUDE.md` — load-bearing discipline
2. `.claude/skills/k1-firmware-change-gate/SKILL.md` — before any firmware edit
3. `.claude/skills/sensorybridge-doctrine/SKILL.md` — before AP/VP changes
4. `.claude/skills/load-bearing-edges/SKILL.md` — if porting gates/thresholds

---

## 13 · Handoff checklist for next agent

- [ ] Read this doc + `2026-06-07-secondary-dark-state-last-writer-verdict.md`
- [ ] Confirm 1401 chip ID `F887A500` on serial
- [ ] Run secondary dark-state eyes-on test (§6 Step 2)
- [ ] Log result to `docs/forensics/runtime-evidence/2026-06-07-secondary-dark-post-fix-*.log`
- [ ] If PASS → proceed Dense Forge lane with Captain eyes-on
- [ ] If FAIL → diagnose with vp_status; do not tune AGC or Dense Forge first
- [ ] Ask Captain before commit

---

**Handover author:** Cursor agent session 2026-06-07  
**Firmware on 1401:** built + uploaded same session (post `waveform_tempo` patch)  
**Captain eyes-on after fix:** **NOT YET RUN — this is the critical next step**
