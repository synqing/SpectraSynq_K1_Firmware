---
abstract: "End-to-end autonomous execution plan (2026-07-06) to complete every outstanding IM73D122 productionization phase. Harness-first (byte-identity oracle = registry_byte_gate.sh + pytest 627 + framework-safety-gate). Gated DAG: U0 oracle baseline → UA production IM73D build path (k1_prod_im73d, byte-identical-OFF, guard-mapped to the main K1 MAC after 2026-07-07 correction) → UB mic-config-authority header (byte-identical; compile-time selection RETAINED — runtime dispatch rejected as Core-0-unsafe + device-cert-gated) → UC byte-identity coverage for the IM73D env → UD DSR_16S enable-recipe + SNR protocol (no dead code) → UE production-flip red-team → UF knob-persistence device capture (opportunistic). Records the Captain hardware decision (D1 identical pins clk13/din12/LR14; D2 no PCB rev). Absolute blockers (device proof, device SNR A/B, eyes-on) are checkpoints, not stops. Read before executing or auditing the IM73D productionization lane."
---

# IM73D productionization — end-to-end autonomous execution plan (2026-07-06)

> **2026-07-07 correction:** the original hard-block plan for `k1_prod_im73d`
> is superseded. Captain confirmed both K1s are identical hardware; existing
> envs encode LED-map/configuration choice. `k1_bench_im73d` drives GPIO `4/5`;
> `k1_prod_im73d` drives GPIO `6/7` and is guard-mapped to the main K1 MAC.
> Do not re-add `k1_prod_im73d` to `BLOCKED_UPLOAD_ENVS` unless Captain creates
> a new explicit blocker.
>
> **2026-07-08 status note:** this file is now historical execution context, not
> the live task queue. UF knob persistence is closed by the radio-free
> `:chroma=0.150` -> `:reset` -> `:dump` proof, DSR16 is rejected by controlled
> audio evidence, and the physical swap blocker is superseded by Captain's
> identical-hardware confirmation. Use the resume brief, spec index, and
> device-build registry for live routing.

Companion to `im73d122-productionization-handover-2026-07-03.md` (§10 = the audit + the Captain decision). This file is the **executable DAG**: units, oracle, per-unit gate, risk/derisk, and the checkpoints autonomy cannot self-certify. Authored under `/autonomous-agentic-build` (harness-first) + `/planning-with-files`.

## Objective

Complete **all** outstanding Phase-1 productionization phases autonomously. Do not stop except at an **absolute blocker** — a checkpoint autonomy structurally cannot self-certify (physical mic swap, device SNR measurement, perceptual eyes-on). Those are documented and handed to Captain; the run continues on every other unit.

## Decision state carried in (do not reopen)

- **Mic:** IM73D122 = K1 production mic. Ratified 2026-07-03.
- **D1 (2026-07-06):** production PDM pin map = **identical bench-proven `clk=13 / din=12 / LR=14`** — all current K1s are the same ESP32-S3 devboard. Verified collision-free on the production pin map (GPIO 12 unassigned; 13/14 freed when SPH drops; LEDs 6/7; SPH LRCLK 11 unused).
- **D2 (2026-07-06):** no pending PCB revision — the IM73D is already wired on the bench K1 since bringup. The only physical open item is swapping the *main* K1's SPH0645 for an IM73D (Captain's hands) — a logistics choice, NOT a firmware dependency.

## The harness (oracle) — formalised, not invented (Step 0)

The behaviour-preservation oracle already half-exists:

| Oracle | Boundary it guards | Type |
|---|---|---|
| `scripts/regression-harness/registry_byte_gate.sh` | `k1_hardware` (SPH, production) loadable-section SHA vs committed reference | Golden-master |
| pytest `tests/` (627 pass) — incl. `bridge_fs_config` golden, `test_*_static.py`, guard drift-catchers | host logic + static contracts | Property/golden |
| `scripts/hooks/framework-safety-gate.sh` (CL-1/CL-2) | crash-safety / instrumentation boundary | Property |
| pre-commit hook (firmware tier) | runs pytest + `pio run -e k1_hardware` on every firmware commit | Infra gate |
| **NEW (UC):** section-hash fingerprint for `k1_bench_im73d` | IM73D path behaviour-preservation across UB | Golden-master |

**Behaviour-preservation gate for every restructure unit:** `registry_byte_gate.sh` GREEN (SPH path byte-identical) **and** `k1_bench_im73d` section-hash == baseline (IM73D path byte-identical) **and** full pytest green, zero deletions. If a unit cannot hold byte-identity, it is NOT merged to a shippable path autonomously — it escalates to a device A/B checkpoint.

## Gated DAG

```
U0 (oracle baseline) ──┬─▶ UA (prod build path) ──▶ UB (mic-config authority) ──▶ UC (IM73D byte-gate)
                       │                                                            │
                       └─▶ UE (flip red-team) ── UD (DSR_16S recipe) ──────────────┘
                                                                                    │
                                                             UF (knob device-proof, opportunistic)
```

### U0 — Oracle baseline (Foundation)
- `registry_byte_gate.sh` GREEN at HEAD (`a82c1d9`); capture `k1_bench_im73d` section-hash baseline; confirm pytest 627.
- **Gate:** all three captured/green. **Risk:** none (read-only).

### UA — Production IM73D build path (behaviour-CHANGING, small, byte-identical-OFF)
- `constants.h`: add `K1_PDM_CLK/DIN/LR_PIN` = `13/12/14` to the production `#else` branch under `#ifdef K1_MIC_IM73D_PDM_V1` (mirrors the bench branch; D1).
- `platformio.ini`: `[env:k1_prod_im73d]` extends `env:k1_hardware` + `-DK1_MIC_IM73D_PDM_V1`.
- `scripts/platformio/k1_upload_guard.py`: originally added `k1_prod_im73d` to **`BLOCKED_UPLOAD_ENVS`** while the main K1 still carried SPH0645. **Superseded 2026-07-07:** Captain confirmed the proof constraint is env/configuration choice, not hardware divergence; `k1_prod_im73d` now belongs in the main K1 allow-list and rejects bench cross-flash by USB MAC.
- `tests/`: static test asserting production PDM pins `13/12/14`, the env's flag inheritance, and the guard block (drift-catcher).
- **Gate:** `registry_byte_gate.sh` GREEN (k1_hardware byte-identical, flag OFF) · `pio run -e k1_prod_im73d` clean · `pio run -e k1_hardware` clean · pytest green.
- **Risk/derisk:** (a) pin block leaks into k1_hardware → guarded by the flag + byte gate proves OFF-identity. (b) production-pinmap PDM won't compile (a bench-only assumption in the PDM init) → caught by the `k1_prod_im73d` build. (c) fail-open on a wrong-device flash → upload-guard MAC binding + drift-catcher test.

### UB — Mic-config authority header (behaviour-PRESERVING, byte-identical)
- Create `SPECTRASYNQ_K1_FIRMWARE/audio/k1_mic_frontend.h`: the single documented source of truth for the mic-domain seam — the **6 interfaces** (init driver-mode, read buffer+timeout, sample extraction/domain, calibration domain: SSL window/DC/gain, persistence namespace, boot invalidation) — centralizing the config **data** (pins for both pinmaps, gain, DSR mode, buffer size, SSL window, boot fallback, PDM file names) with a map of where each compile-time `#ifdef` lives.
- **Decision (recorded, via-negativa):** compile-time mic selection is **retained**. A runtime "MicFrontend" dispatch would (i) change the binary → fail the byte-identity oracle, (ii) add Core-0 cost on the hard-real-time audio path (`sensorybridge-doctrine`: architecture subordinate to perceptual impact; `esp32-render-path-safety`), and (iii) be certifiable only by device A/B on hardware that does not yet exist. The maintainability win — one config authority + a documented seam instead of scattered magic numbers — is delivered **byte-identically**; the risky rewrite is deliberately NOT done.
- **Gate:** `registry_byte_gate.sh` GREEN · `k1_bench_im73d` section-hash == U0 baseline · pytest green.
- **Risk/derisk:** any byte drift on either env = the consolidation changed a compiled token → narrow until identical or STOP that site. No Core-0 read-path logic is rewritten.

### UC — Byte-identity coverage for the IM73D env (harness improvement)
- Commit a `k1_bench_im73d` section fingerprint + a check (extend the byte-gate pattern) so the IM73D path has the same rollback-on-red guard as k1_hardware. Closes the migration-plan gap ("registry_byte_gate covers k1_hardware only").
- **Gate:** the new check passes at HEAD; pytest green.

### UD — DSR_16S evaluation prep (analysis; NO dead code)
- Document the exact one-line enable recipe (`I2S_PDM_DSR_16S` in the clk config) + the SNR A/B measurement protocol (radio-free `k1_bench_im73d` ONLY — never a BLE build; Captain-context capture). Reserved +2 dB lever ([[im73d-pdm-snr-modes]]). No speculative flag added — the lever lands with the measurement that justifies it.
- **Absolute-blocker note:** the +2 dB verdict needs a device SNR measurement → Captain-context bench session. Documented, not stopped.

### UE — Production-flip readiness red-team (analysis)
- A pre-mortem/red-team: what must be TRUE before flipping `k1_hardware`'s default from SPH to IM73D — strangler-fig sequence, dual-run parity, per-unit factory-cal UX, the SPH-autopsy dependency, the failure modes and their guards. Feeds the eventual (Captain-gated) default flip.

### UF — Knob-persistence device capture (device; OPPORTUNISTIC)
- The un-freeze code (`e2b62b5`) ships on the bench (`79d7fda ⊇ e2b62b5`) but the "set knob → `:reset` → survived" proof was never recorded. If the bench is reachable + guard-verified: set a knob via `:`-prefixed command → `:reset` → `:dump` → confirm survived. **No cal firing** (no Captain silence-go needed). If unreachable → documented owed (environmental, not a Captain decision) and the run continues.

## Checkpoints autonomy CANNOT self-certify (superseded live state)

Closed/superseded since this plan was written:

1. Physical mic swap is no longer the mic-proof blocker; Captain confirmed both
   K1s are identical hardware, and env choice encodes the LED route/configuration.
2. DSR16 controlled-audio measurement is complete and rejected; keep `DSR_8S`.

Still Captain-gated:

1. Selected-env device proof and perceptual eyes-on for any default flip.
2. Default-env flip (`k1_hardware` -> IM73D) if Captain chooses it after proof.

## Execution status (2026-07-06)

| Unit | Status | Evidence |
|---|---|---|
| U0 oracle baseline | ✅ done | 3-stable-section baselines captured; **determinism finding**: `.flash.text`/`.flash.rodata` non-reproducible even clean → oracle = 3 stable sections |
| UA production build path | ✅ **shipped** `4b95e60` | `k1_prod_im73d` (pins 13/12/14), guard-mapped to main K1 after 2026-07-07 correction, byte-identical-OFF (3 stable sections), pytest 629 |
| UB MicFrontend | ✅ **resolved (decision)** | runtime dispatch REJECTED (un-byte-verifiable + Core-0 + doctrine); seam map delivered — handover §11.2 |
| UC IM73D byte-gate | ✅ **shipped** `d1ecc10` | `mic_stable_byte_gate.sh` + committed references (k1_hardware/k1_bench_reference/k1_bench_im73d) + static contract test; non-flaky check confirmed |
| UD DSR_16S recipe | ✅ done (doc) | enable recipe + SNR protocol — handover §11.4 (device SNR = Captain-context checkpoint) |
| UE flip red-team | ✅ done (doc) | pre-mortem + 7-step flip checklist — handover §11.5 |
| UF knob device-proof | ✅ **closed** | radio-free proof: `:chroma=0.150` survived `:reset`; final restore/readback `CONFIG.CHROMA: 0.100000`; `CAL_SOURCE: persisted_profile`; no `start_noise_cal` |

**Remaining Captain-gated checkpoints:** selected-env device proof + eyes-on for any default flip, and the default flip itself. DSR16 is closed/rejected; physical conversion of `F887A500` is optional product-unit work, not the current mic-proof blocker.

## Governance (fleet-of-one)
Retry budget 3 per unit (3-strike → escalate the decomposition, not the code). Byte-identity oracle is the trust root — never edited by a production unit. Every unit = one revertible commit through the pre-commit gate. Burndown tracked in `progress.md` + the working `task_plan.md`.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-06 | agent:claude-code (Fable) | Created: end-to-end autonomous execution plan for IM73D productionization (harness-first gated DAG U0-UF), carrying the Captain D1/D2 decision. |
