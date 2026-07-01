---
abstract: "Incident + resolution record for the N2 silent-idle deterministic ~12.46s task_wdt reboot loop (IDLE0 starvation, CPU0 audio loopTask). Root cause: over-budget AP loop drains the 22.5ms I2S DMA slack so the unguarded portMAX_DELAY read at i2s_audio.h:277 stops blocking, killing the only implicit IDLE0 feed. Fixed by 827d73a (K1_AUDIO_FREEZE_GUARD_V1), flashed + validated on main K1 F887A500. Ancient/pre-fork defect present in ALL lanes incl. product line a11f2ed. Read for the full 8-agent forensic convergence and the panic-vs-pressure distinction."
---

# N2 Silent-Idle Watchdog Freeze — Incident + Resolution Record

**Date:** 2026-06-30
**Status:** RESOLVED (panic eliminated by `827d73a`; underlying pressure remediation tracked separately)
**Severity:** Launch-blocker — present on the active product line branch `lane/remoted-ble-midi-phase-f` (HEAD `a11f2ed`)
**Class:** This is a completed-work postmortem. It is NOT a forward task list.

---

## 1. Symptom

Under silent or near-silent ambient input ("N2" condition), the K1 entered a deterministic reboot loop:

- Reboot cadence fixed at **~12.46 s** wall-clock, repeating indefinitely.
- Trigger was an ESP-IDF **Task Watchdog (`task_wdt`) panic** naming the **IDLE0** task (CPU0) as starved, with the audio **`loopTask`** pinned on CPU0 identified as the starving hog.
- Failure was input-dependent in onset but timing-deterministic in outcome: quiet input reliably reproduced it; the reboot interval did not drift.

The combination — silent input, a fixed ~12.46 s period, and an IDLE0/CPU0 watchdog signature — is the diagnostic fingerprint of this defect.

---

## 2. Root Cause

The audio analysis (AP) loop on CPU0 runs over its per-emit time budget. The dominant cost is the autocorrelation/tempo path (**ACF ~1–1.5 ms per emit**) with **decimation pinned to 1** (no work-spreading), so the full ACF cost is paid every emit and is **signal-independent** — it does not get cheaper when the input is silent.

The I2S capture path provides a finite backlog of slack to absorb compute jitter: **3 DMA descriptors × 96 frames** of buffering, equating to roughly **22.5 ms of DMA slack**. When the AP loop runs over budget, it drains this backlog. Because the frame count consumed per emit is **fixed**, the backlog is exhausted in a deterministic number of iterations — this is what makes the reboot period a near-constant ~12.46 s rather than a jittery one.

Once the backlog is exhausted, the blocking I2S read at:

- `SPECTRASYNQ_K1_FIRMWARE/.../i2s_audio.h:277` — `i2s_channel_read(..., portMAX_DELAY)`

**stops actually blocking**: data is already waiting, so the call returns immediately every time. That blocking read was the **only implicit feed of the IDLE0 watchdog** — when the loop parks in a genuine block, the scheduler runs IDLE0 on CPU0 and the idle hook feeds the TWDT. There is **no explicit `esp_task_wdt` feed** on the audio loopTask, and `yield()` cannot schedule IDLE0 here. So once the read no longer blocks, CPU0 never idles, IDLE0 never runs, IDLE0 is never fed, and after the **5 s TWDT timeout** the panic fires and the board reboots.

This defect is **ancient / pre-fork** — inherited from the Sensory Bridge heritage of the audio loop — and is present in **every lane**, including the active product line at `a11f2ed`.

---

## 3. Eight-Agent Forensic Convergence

An 8-agent swarm independently investigated and converged on the single root cause above. One line each:

1. **Backtrace agent** — the panic backtrace is **IDLE0 starvation on CPU0, not a GDFT/DSP deadlock**; the loopTask is busy, not wedged.
2. **AGC agent** — the automatic-gain path is **bounded and non-causal** to the freeze; it is not the source of unbounded work.
3. **I2S agent** — the **`portMAX_DELAY` read at `i2s_audio.h:277` is unguarded**; this is the N2 mechanism (read stops blocking once the backlog drains).
4. **WDT agent** — the **TWDT timeout is 5 s**, and **only a genuine blocking call implicitly feeds IDLE0**; there is no explicit feed on the loopTask.
5. **Tempo/ACF agent** — the **ACF/tempo cost is signal-independent** (~1–1.5 ms/emit, decimation = 1), so silence does not relieve the over-budget condition.
6. **Regression agent** — the defect is **ancient**, **`a11f2ed` (product line) is affected**, and **a fix already exists at `827d73a`**.
7. **Timing (t12) agent** — the **~12.46 s period is deterministic backlog-exhaustion timing**: fixed frame consumption against a fixed DMA backlog yields a fixed countdown to panic.
8. **Repro/config agent** — independent **repro and configuration corroboration** of the silent-input trigger and the buffer/timeout constants.

---

## 4. Fix

Commit **`827d73a`** (flag **`K1_AUDIO_FREEZE_GUARD_V1`**) on branch `feat/n2-i2s-watchdog`:

- Adds **explicit `enableLoopWDT()` / `feedLoopWDT()`** on the audio `loopTask`, so IDLE0 no longer carries the sole responsibility for feeding the watchdog on CPU0.
- Replaces the unguarded `portMAX_DELAY` read at `i2s_audio.h:277` with a **bounded / zero-fill I2S read**, so the loop neither parks forever nor spins on an always-ready buffer.

**Validation:** `827d73a` was flashed to the main K1 (chip **F887A500**) and ran clean — **0 reboots, board alive, `bpm=126` streaming**.

### Panic vs. Pressure — the load-bearing distinction

- **`827d73a` stops the PANIC.** It guarantees the watchdog is fed regardless of whether the I2S read blocks, so the over-budget condition can no longer cascade into a reboot loop. This is the safety floor.
- **`827d73a` does NOT cure the PRESSURE.** The AP loop is still over budget under silence (ACF ~1–1.5 ms/emit, decimation pinned to 1). The DMA backlog is still being drained; the system is merely no longer fatal when it empties. The durable cure is **ACF work-spreading** (decimation / amortising the autocorrelation cost across emits) so the loop returns within budget and the I2S backlog is no longer exhausted.

Treating `827d73a` as a complete fix would be a category error: it is the panic guard, not the budget cure.

---

## 5. Launch-Blocker Status

The active product line branch `lane/remoted-ble-midi-phase-f` (HEAD **`a11f2ed`**) **ships this defect** — it does not contain the guard. A remediation branch **`fix/ble-n2-watchdog`** was prepared this session to carry the guard onto the product line. Until that lands, any silent-idle K1 on `a11f2ed` is exposed to the deterministic ~12.46 s reboot loop.

---

## 6. Evidence Summary

| Item | Reference |
|------|-----------|
| Fix commit | `827d73a` (`feat/n2-i2s-watchdog`), flag `K1_AUDIO_FREEZE_GUARD_V1` |
| Unguarded blocking read | `SPECTRASYNQ_K1_FIRMWARE/.../i2s_audio.h:277` (`i2s_channel_read`, `portMAX_DELAY`) |
| Affected product line HEAD | `a11f2ed` (`lane/remoted-ble-midi-phase-f`) |
| Remediation branch | `fix/ble-n2-watchdog` (prepared this session) |
| Validated hardware | Main K1, chip `F887A500` — 0 reboots, alive, `bpm=126` streaming |
| DMA slack | 3 descriptors × 96 frames ≈ 22.5 ms |
| ACF cost | ~1–1.5 ms/emit, decimation pinned to 1, signal-independent |
| TWDT timeout | 5 s |
| Reboot period | ~12.46 s, deterministic |

---

**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-06-30 | agent:claude-opus-4-8 | Created. Durable incident + resolution record for the N2 silent-idle watchdog freeze; grounded with commit `827d73a`, product-line HEAD `a11f2ed`, `i2s_audio.h:277`, chip F887A500, and the 8-agent convergence. Completed-work postmortem, not a forward task list. |
