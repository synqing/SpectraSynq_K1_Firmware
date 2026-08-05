---
abstract: "Phase-0 execution plan (dual-K1 sync): harness-first build of the BLE transport-verification oracle. Gated DAG of 6 units — guard/env registration, GPIO cross-trigger timing oracle (Gate 0 fault-evidence), dual-role NimBLE probe firmware, measurement runs producing the four F1/F2 gate numbers. Includes the Captain physical checklist (devices offline at plan time). Branch: lane/dual-sync-phase0."
---

# Phase 0 — Transport Verification (execution plan)

Doctrine: autonomous-agentic-build (harness-first). **The oracle IS Phase 0's product** — probe firmware only exists to flow through it. Ratified inputs: F1 (~8 ms standard), F2 (BLE GATT, CI 7.5 ms), F5 (gate authority + 1401 flashing). Branch: `lane/dual-sync-phase0` (from `628f69b`).

## Oracle choice & determinism contract
- **Oracle type:** property/metamorphic over a wired reference channel. The wired GPIO cross-trigger (leader toggles a pin at event T_leader; follower ISR captures local `micros()` at the edge; wire ≈ ns) gives a radio-independent clock mapping. The radio-based sync's claimed offset is then *differenced against the wire truth* — the oracle measures the sync system, and the radio under test never times itself.
- **Determinism contract:** `micros()` monotonic 64-bit wrap-handled; ISR latency characterised (measure N edge round-trips back-to-back, derive tolerance empirically — never guessed); serial log lines carry device-local µs timestamps; host correlator is pure/deterministic over captured logs; all scenario scripts seeded/versioned.
- **Gate 0 (fault-evidence, human-signed):** inject KNOWN faults — fixed +5 ms and +20 ms artificial apply-delays on the follower, a deliberately mis-set clock offset, dropped-packet bursts — and require the oracle to report each within its characterised tolerance. An uncaught injection = oracle blind spot → widen before any measurement is trusted.
- **Anti-gaming / trust root:** oracle scripts + gate evaluator live in `scripts/dual_sync_probe/` and are committed before probe firmware; pre-commit gate (pytest + build) runs in infra; no unit may modify the oracle and the firmware it measures in the same commit.

## The four gate numbers (from F1/F2, evaluated by the oracle)
1. Inter-device clock-offset error ≤ **4 ms** (p95), vs wire truth.
2. Packet lateness p99.9 ≤ delay-line depth **D** (target D ≤ 25–30 ms).
3. Leader end-to-end (mic→LED incl. D) ≤ **50 ms**.
4. Health under full load (33 Hz stream + K718 dial linked): render FPS floor, zero WS2812 glitches, `internal_min_ever` above abort line, Core-0 AP p95 ≤ 7.5 ms, **K718 dial-link uptime 100%**.

## Unit DAG
| Unit | What | Depends | Gate |
|---|---|---|---|
| **P0.1** Recon | DONE — devices offline; restore baselines already in registry (main `k1_hardware @ 67227da`, bench `k1_bench_im73d @ f2f7c45`); branch open | — | — |
| **P0.2** Guard + envs | Extend `guard_k1_radio_isolation.py` tokens (sync TU symbols); add non-shippable `k1_sync_probe_bench` (GPIO 4/5 + IM73D) & `k1_sync_probe_main` (GPIO 6/7 + SPH) envs; register both in `k1_upload_guard.py` + device registry (pending-flash rows) | P0.1 | pytest + both envs build + prod byte-identity untouched |
| **P0.3** Timing oracle | `scripts/dual_sync_probe/`: log-capture correlator, gate evaluator, fault-injection battery, ISR-jitter characteriser; GPIO pin choice from `k1-hardware-definition.md` (safe, unused, both pinmaps) | P0.1 | pytest (host tests over synthetic logs incl. injected-fault battery) |
| **P0.4** Probe firmware | `k1_sync_probe` TU: NimBLE dual-role (leader: central→K718 + peripheral sync svc; follower: central→leader), CI 7.5 ms + DLE, 33 Hz timestamped dummy-replay stream, RTT clock-sync burst, GPIO cross-trigger hooks, 1 Hz health telemetry (heap watermark/FPS/AP p95/dial-link state), event-id loss counters | P0.2, P0.3 | pytest + builds green both envs + instrumentation-boundary tests |
| **P0.5** Gate-0 + measurement runs | Flash both units (identity-verified), characterise ISR jitter, run fault-injection battery on-silicon (**Gate 0 — Captain-visible**), then scenarios: idle / music / dial-linked+turning / 30–60 min soak → oracle produces the four numbers | P0.4 + physical checklist | The four gate numbers, evidence-logged |
| **P0.0** Seam trial | Day-zero physical seam photos (gates **M2 only**, not transport) | hands only | Captain eyes-on |

## Captain physical checklist (the steps autonomy cannot do)
1. **Power/plug both K1s** (any USB ports — identity is verified by chip ID, ports drift).
2. **One jumper wire + common ground** between the two units (exact GPIO pins will be named by P0.3 after pinmap audit — wiring happens before P0.5).
3. **K718 dial powered** during the dial-uptime scenarios (and a few dial turns during the soak).
4. **Music playing** for the load scenarios (any source, normal listening level).
5. *(M2 only, whenever convenient)* Seam trial: butt the two enclosures together, static pattern, 2–3 photos at fixed exposure.

## Failure stances
- Any gate number red → Phase 0 reports numbers; contingency ladder engages (ESP-NOW paper spec → 2nd-MCU rev). No re-runs-until-green: a red gate is a finding, not an obstacle.
- Cal policy unchanged: **no `start_noise_cal` ever fires in probe firmware**; cal fields untouched.
- Every flash: registry deployed-state row updated; restore to baseline env recorded above when Phase 0 ends.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code | Created — Phase-0 harness-first execution plan; devices offline at plan time. |
