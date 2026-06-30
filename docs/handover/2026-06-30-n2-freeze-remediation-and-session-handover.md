---
abstract: "Session handover, 2026-06-30. (1) Strategic: SpectraSynq_K1_Firmware is the canonical go-forward K1 firmware line — BLE-MIDI is the control surface, WiFi is DROPPED; Lightwave-Ledstrip is an archived effects-donor (see the cross-pollination doc). (2) Incident: the N2 silent-idle watchdog-freeze — ancient pre-fork bug in EVERY lane, root-caused by an 8-agent swarm, fixed by 827d73a (K1_AUDIO_FREEZE_GUARD_V1), validated on hardware, and MERGED onto the BLE product line (lane/remoted-ble-midi-phase-f @ e2beac5, NOT pushed). Lists staged AGC + ACF lanes, exact device/repo state, and the non-negotiable operating doctrine (host-green != device-proof, bench-first, harness-is-the-gate, chip-ID-is-truth). READ before any K1 firmware work or hardware flash."
---

# K1 Firmware — Session Handover (2026-06-30)
## N2 silent-idle freeze: fixed & shipped to the BLE line + remediation state

> **TL;DR** — Your main K1 was reboot-looping every ~12.5 s in a quiet room. Root cause: an **ancient (pre-fork, Sensory-Bridge-heritage) audio-loop watchdog-starvation freeze (lane N2)** present in *every* branch including the shipping BLE line. It is now **fixed** (commit `827d73a`, flag `K1_AUDIO_FREEZE_GUARD_V1`), **validated on hardware**, and **merged onto the BLE product line** `lane/remoted-ble-midi-phase-f` (now at **`e2beac5`**, **NOT pushed**). The device is **recovered and stable**. Two firmware lanes (per-band AGC, ACF work-spreading) are **built + host-gated but await device/perceptual sign-off**. Read §6 (Operating Doctrine) before you flash anything.

---

## 1. Strategic context (decided earlier this session)

- **`SpectraSynq_K1_Firmware` is the canonical go-forward K1 firmware.** It is **not** a git fork of `Lightwave-Ledstrip` — both are independent descendants of Sensory Bridge (Lixie Labs, GPL-3.0). This repo is the active line; the monorepo is dormant.
- **Captain decision (UF2):** **BLE-MIDI is the control surface; WiFi is dropped entirely.** Consequence: the monorepo's WiFi dual-mode, REST/WS API, and iOS app are **product-deprecated** — not migration candidates. The only residual donor value from the monorepo is curated *effect taste*, and that is **deferred / possibly unneeded for launch**.
- **`Lightwave-Ledstrip` = archived effects-donor.** Full strategic analysis (forensic timeline, proposal inventory, cross-pollination matrix, the canonical-line decision): `Lightwave-Ledstrip/firmware-v3/docs/research/fork_reconciliation_crosspollination_2026-06-30.md`.
- Hardware is the **same board** for both lines: `esp32-s3-devkitc1-n16r8` (16 MB OPI PSRAM). The divergence is software (this line = ESP-IDF 5.4.1 / pioarduino / RMT5 / GDFT @ 133 Hz; monorepo = IDF 4.4.7 / RMT4 / ESV11 @ 32 kHz).

## 2. What happened this session (the arc)

Cross-pollination analysis → CTO strategy (fork = canonical) → prepared a per-band AGC perceptual fix (N6) → **blind-flashed it to the only K1 (mistake)** → device crash-looped → 10-agent SSA swarm investigation → **root cause = pre-existing N2 freeze, not the AGC change** → found the fix already existed (`827d73a`) → built, flashed, recovered the device → ran the harness-first remediation (cherry-pick onto the BLE line, AGC-on-stable-base, ACF root-fix, incident doc) → host-gated both branches green → device-attested the BLE-line fix → **merged it onto the product line**.

## 3. Current device + repo state (exact)

**Device** — main K1, chip **`F887A500`**, MAC **`b4:3a:45:a5:87:f8`**, currently enumerated on `/dev/cu.usbmodem2101` (ports re-enumerate — see §6.4). Currently **running `e2beac5`** (BLE line + N2 fix). Stable: ~260 s silent-idle soak, 0 watchdog, 0 reboots.

**Branches (in `/Users/spectrasynq/SpectraSynq_K1_Firmware`, none pushed):**
| Branch | HEAD | Contents | State |
|---|---|---|---|
| `lane/remoted-ble-midi-phase-f` (PRODUCT) | `e2beac5` | BLE line + **N2 fix merged (FF)** | host-gate GREEN, device-attested, **NOT pushed** |
| `fix/ble-n2-watchdog` | `e2beac5` | a11f2ed + cherry-pick(827d73a) | == product HEAD now |
| `feat/n2-i2s-watchdog` | `827d73a` | the N2 fix (origin of the cherry-pick) | host-proven |
| `lane/agc-on-n2` | `bdd3084` | 827d73a + cherry-pick(9c19b1f, per-band AGC) | host-gate GREEN, **needs device A/B + perceptual sign-off** |
| `feat/n6-agc-perband` | `9c19b1f` | per-band AGC candidate (origin) | host-proven |

**Dirty/untracked in the fork main checkout (review before committing):** modified `docs/hardware/device-build-registry.md`, `scripts/hooks/pre-commit`; untracked `docs/forensics/2026-06-30-n2-silent-idle-watchdog-freeze.md` (the incident postmortem) + this handover.

**Throwaway worktrees under `/private/tmp/` (EPHEMERAL — may be gone after reboot; branches persist in the repo):** `k1_ble_n2`, `k1_agc_n2`, `k1_acf` (detached @827d73a + ACF flag), `k1_n2_fix`, `k1_good_da4258e`, `k1_n6_agc_perband`.

## 4. The N2 incident — root cause + fix (headline deliverable)

**Symptom:** deterministic ~12.46 s `task_wdt` reboot loop in a quiet room — `IDLE0 (CPU0) did not reset`, `CPU0: loopTask`.

**Root cause (8-agent consensus, file:line-grounded — full detail in `docs/forensics/2026-06-30-n2-silent-idle-watchdog-freeze.md`):** the audio loop on CPU0 feeds the 5 s task-WDT **only** by blocking on `i2s_channel_read(..., portMAX_DELAY)` (`SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h`). There is **no explicit watchdog feed**, and `yield()` cannot schedule IDLE0 (priority 0 < loopTask 1). The AP loop is **over budget** (p95 ~9–11 ms vs the 7.5 ms / 133 Hz period; the unconditional ACF in `sb_tempo.cpp` is the driver). A tiny fixed per-frame overage drains the **22.5 ms I2S DMA slack** (3 desc × 96) at a fixed frame count → the read stops blocking → IDLE0 starves → 5 s panic → deterministic 12.46 s reboot. **Ancient/pre-fork; present in every lane including the shipping BLE line.** Not the AGC change (`process_GDFT` returns; AGC is bounded/constant-time/non-causal — both verified). The int64-magnitude (N9) overflow is a **red herring** for this — disproven on-device.

**Fix — `827d73a` / flag `K1_AUDIO_FREEZE_GUARD_V1` (default ON in `[env:k1_hardware]`):** bounds the I2S read to `pdMS_TO_TICKS(K1_I2S_READ_TIMEOUT_MS=100)` + zero-fills on timeout; adds `enableLoopWDT()` (`.ino`) + `feedLoopWDT()` every loop iteration; `esp_task_wdt_add/_reset` on the LED task; `esp_task_wdt_reconfigure` 5 s. Single `-D` revert. **Host-proven (580/579 pass + golden + Gate-0).** Hardware-validated on the main K1 and on the BLE line (0 reboots vs the old 12.5 s loop).

**Important nuance the fix only half-solves:** `827d73a` removes the **panic** (symptom). The **over-budget loop is the underlying pressure** and remains — that is what the ACF lane in §5 cures. Treat the N2 fix as "no longer bricks," not "loop is healthy."

## 5. Staged-but-incomplete forward work (each gated, awaiting a human/device checkpoint)

1. **Push the product line.** `lane/remoted-ble-midi-phase-f @ e2beac5` is local-only. `git push` when Captain authorises it onto the remote/fleet. *(Captain call.)*
2. **Per-band AGC (N6) — perceptual fix for "louder→dimmer".** Branch `lane/agc-on-n2 @ bdd3084` (on the N2 fix, so it won't reboot-loop). Host-gate GREEN; flag `SB_AGC_PERBAND_V1` **default OFF**. The original perceptual defect: a single global AGC scalar (`k1_gdft_core.cpp:376/384`) dims the whole field on loud broadband; per-band gain uses the existing `agc_bands[]` scaffold. **Needs:** hardware A/B (State A = no flag vs State B = `-DSB_AGC_PERBAND_V1`) on a **silent/approved** audio source (SPH0645) + Captain perceptual eyes-on to pick the default. *(This is SEPARATE from the freeze; per-band AGC is not the freeze cause.)*
3. **ACF work-spreading — the real over-budget root-fix.** Candidate built in `/private/tmp/k1_acf` (detached @827d73a) with `-DSB_TEMPO_ACF_SPREAD_PROBE=1 -DSB_TEMPO_ACF_SPREAD_LAGS_PER_EMIT=16` (spread code already in-tree; recommended over decimation, which leaves the worst refresh frame intact). **RBDO: DEGRADED-MODE** — p95-reduction estimates (~9–11 ms → ~5.4 ms) are from the 16 k probe, **not measured at production 12.8 k/96**. **Needs:** flash candidate → `scripts/regression-harness/device_ap_cadence_capture.py` at 12.8 k → confirm `total_ap_loop` p95 < 7500 µs → then a fixed-stimulus tempo-quality probe before promoting from probe to a `k1_hardware` default. Keep `SB_TEMPO_ACF_REFRESH_DECIMATION=1`. Plan: `docs/forensics/2026-06-15-16k120-acf-work-spreading-plan.md`.
4. **(Deferred, maybe unneeded) monorepo effect-taste harvest** — only if, after the AGC fix, the fork's own visuals still fall short of launch quality. See the cross-pollination doc §C.2.

## 6. Operating doctrine — hard-won this session, NON-NEGOTIABLE

This repo's founding law is **"the harness IS the product"** (`docs/architecture/firmware-modernization-program.md`; the `autonomous-agentic-build` skill is distilled from it). The N2 incident is its textbook violation. Inherit these:

1. **NEVER blind-flash the only K1. Host-green ≠ device-proof.** The whole crisis started by flashing a host-*compiled*-only change straight to the main unit. **Bench-first**; if no bench, the change must already be host-gated AND you accept the device may need BOOT-mode recovery.
2. **The per-unit gate is the fork's existing fault-evident harness, run by infra/orchestrator — not `pio` compile, not an agent's self-report.** Commands:
   `python -m pytest tests/test_golden_master.py tests/test_harness_selftest.py -q` (golden-master oracle + Gate-0 mutation self-test), then `python -m pytest tests/ -q` (full suite, ~78 files). **Immutability:** the change must touch **zero** files under `tests/golden/`, `tests/test_harness_selftest.py`, `.github/`, `gate0_*` (a lane that edits its own gate auto-fails). Gate the **post-merge HEAD**, not just the lane branch.
3. **Behaviour-CHANGING firmware rides its own ticketed track + a human/device checkpoint.** Default flags OFF. The host golden proves the *unchanged* boundaries; the *changed* boundary (audio acquisition under stall, per-band gain, ACF cadence) is device/perceptual — autonomy cannot self-certify it.
4. **Device identity = chip-ID `F887A500`, NOT the port string.** Ports re-enumerate (`1101→1401→2101→…`). The `k1_upload_guard` pre-script verifies the chip before flashing and refuses cross-flash to the bench unit (`B489A500`) — trust it; never hard-code a port as identity.
5. **Flashing:** `pio run -e k1_hardware -t upload --upload-port <port>` wrapped in `script -q <log>` (esptool **silently no-ops if stdout is piped**); confirm `Hash of data verified` + `Hard resetting` in the log or it didn't flash. A **crash-looping** device blocks auto-reset flashing — recover via **BOOT-mode** (hold `BOOT`, tap `RST`, release `BOOT`; strip goes dark, loop stops), then flash.
6. **SSA swarm discipline (ssa-management):** parallel read-only investigators in their own worktrees; the **orchestrator re-verifies decision-critical claims** (this session caught a wrong "different boards" claim and a wrong "int64 is the cause" claim). Name residual gaps — e.g. the N2 attestation could not reproduce the exact `max_raw≈1` crash telemetry (room floors at ~76), so it rests on survival + signal-independent mechanism, not an exact-regime A/B.

## 7. Cheat-sheet

- Repo: `/Users/spectrasynq/SpectraSynq_K1_Firmware`; firmware src under `SPECTRASYNQ_K1_FIRMWARE/`; prod env `k1_hardware`; bench env `k1_bench_reference`.
- Main K1 chip `F887A500` / MAC `b4:3a:45:a5:87:f8`; bench `B489A500`. Ports vary — verify via the upload guard, not the string.
- WDT: 5 s, panic, watches IDLE0 (CPU0); `ARDUINO_RUNNING_CORE=0` → audio loopTask on CPU0, render on CPU1.
- Audio: GDFT @ 133 Hz, 12.8 kHz, 96-sample; ACF unconditional (`SB_TEMPO_ACF_REFRESH_DECIMATION=1`).
- Telemetry: `[AP]` line at ~1 Hz; `silence=0` even in a quiet room; `max_raw≈1` only when truly dead-still.

## 8. Evidence trail

- Incident postmortem: `docs/forensics/2026-06-30-n2-silent-idle-watchdog-freeze.md`
- Cross-pollination / strategy: `Lightwave-Ledstrip/firmware-v3/docs/research/fork_reconciliation_crosspollination_2026-06-30.md`
- N2 RCA + fix origin: commit `827d73a` on `feat/n2-i2s-watchdog`; ACF plan: `docs/forensics/2026-06-15-16k120-acf-work-spreading-plan.md`
- Production-readiness lane (N1–N9): `docs/architecture/production-readiness-lane.md`

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 (orchestrator + SSA swarm) | Created. Session handover: N2 freeze root cause + fix merged onto the BLE product line (e2beac5, unpushed); strategic canonical-line context; staged AGC + ACF lanes; operating doctrine. |
