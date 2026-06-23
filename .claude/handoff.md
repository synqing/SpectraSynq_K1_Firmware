# Active session handoff

## ⏩ CURRENT ACTIVE LANE (2026-06-21): GDFT true-centre coefficient A/B — HOST-GREEN, DEVICE A/B PENDING
**Resume here:** [docs/handover/2026-06-21-gdft-true-center-ab.md](../docs/handover/2026-06-21-gdft-true-center-ab.md) — branch `feat/gdft-true-center-ab`.
**IMPLEMENTATION LANDED (host-green, unpushed):** flag is `K1_GDFT_TRUE_CENTER_V1` (NOT `SB_*` — naming-order corrected), default-OFF, gating only the k/coeff block in `precompute_goertzel_constants()`. pytest 574 green; OFF loadable image byte-identical to baseline; k1_hardware OFF + bench harness OFF/ON all build. Also fixed a red-on-arrival gate (bench harness env non-shippable label).
**THE ONE REMAINING GATE:** device A/B on **12201 (chip `B489A500`)** via `k1_bench_reference_harness` (device was NOT connected this session). Flash OFF then `-DK1_GDFT_TRUE_CENTER_V1=1`. **Acceptance: 440 Hz → bin 24, 415.3 → bin 23; if 440 does not reach bin 24, STOP — no tuning, top-5/neighbour telemetry required.** Then restore shippable `k1_bench_reference`. Push of the two new commits awaits Captain.
Everything below is older VME/Dense-Forge history.

---

**Authority:** [docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md](../docs/handover/2026-06-07-vme-l1-waveform-sandbox-handover.md)
**VMEWT incident gate:** [docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md](../docs/forensics/vme_l1/2026-06-07-vmewt-transport-incident.md)
**Previous lane handover:** [docs/handover/2026-06-07-dense-forge-closeout.md](../docs/handover/2026-06-07-dense-forge-closeout.md)
**Spec routing:** [docs/spec-index.md](../docs/spec-index.md)
**Last synced:** 2026-06-10 (git `wip/audio-saliency-recovery`, HEAD `88a1bc3`; verify current HEAD live). **This handover is the VME L1 / Dense Forge lane authority and predates the 2026-06-09 WS/Tab5/VPML feature commits** — those lanes are now registered in [docs/spec-index.md](../docs/spec-index.md) and the [2026-06-10 closeout audit](../docs/forensics/2026-06-10-weekly-closeout-audit.md). The `13ffe00` firmware-source baseline is **superseded** (feature firmware has since landed above it; no longer an empty-diff reference). Host gate is GREEN as of 2026-06-10 (`.venv` pytest 309 passed). Unfinished dirty lanes still quarantined at `wip/2026-06-07-unfinished-lanes-quarantine` @ `a40bdb8`; VME hardware capture frozen by transport incident.

Forward work queue lives in [progress.md](../progress.md), not here.

---

## Current state

Dense Forge mode 21 is recovered at source level and accepted by Captain eyes-on: `a5ce32e fix(vp): restore Dense Forge transport` restores per-frame transport and preserves the VU-gate removal. Exact clean-commit `a5ce32e` `k1_hardware` build passed and has been flashed to 1401 after Cursor released the serial port.

The live repo branch must be rechecked with `git status --short --branch --untracked-files=all` and `git rev-parse --short HEAD`. The firmware-source baseline under the VME handover docs is `13ffe00`. All unfinished June 7 work is preserved on quarantine branch `wip/2026-06-07-unfinished-lanes-quarantine` at commit `a40bdb8`; do not merge it into VME L1.

Next active lane is VME Level 1 sandbox for Waveform Fast, Waveform, and Waveform Tempo, but the hardware VMEWT path is frozen. The failed sandbox capture produced survivor rows from a corrupted serial transport, so it is not runtime proof. Restart VME from the incident reopen gate: fail-closed parser tests, bounded deferred transport, sequence/length/CRC validation, zero dropped/corrupt/overflow, and paired final-byte records for modes 7/8/18 primary and secondary.

---

## Decisions made and why

- **Dense Forge:** SOURCE COMMITTED + exact `a5ce32e` flashed to 1401; Captain eyes-on PASS was on the repair build before exact-source reflash.
- **Dirty-lane quarantine:** `a40bdb8` on `wip/2026-06-07-unfinished-lanes-quarantine` preserves unresolved anti-creep, mode 18 secondary-dark, Tempo Comet, VP chroma, trace-dev config, and evidence work.
- **VME L1:** Start from current branch HEAD after verifying it; target modes 7, 8, and 18 in sandbox/shadow mode only. Treat `13ffe00` as the unchanged firmware-source baseline beneath the docs.
- **VMEWT incident:** Hardware evidence is invalid until transport is clean, framed, complete, and fail-closed. Do not use survivor rows as proof.
- **Primary anti-creep:** PASS (eyes-on), but source remains in separate dirty lane — do not tune AGC, Phase 3 `silent_scale`, or SSL/noise floor without new evidence.
- **Secondary dark-state:** PATCH FLASHED, eyes-on status not promoted into Dense Forge closeout — only touch mode 18 or secondary render path if re-test fails.
- **Two-lane model:** Keep secondary darkness and Dense Forge separate (Captain-mandated).
- **Never auto-fire** `start_noise_cal` (Captain silence confirmation required).
- **Never flash/erase** without USB MAC + chip ID verification.
- **No push** unless Captain explicitly instructs.

---

## Failed approaches not to retry

- Treating Dense Forge starvation as the same bug as secondary dark-state (different modes, different write paths).
- Treating partial VMEWT survivor rows as proof after nonzero rejected records, ignored fragments, or parser issues.
- Quieting AP/VP streams, shortening rows, changing baud/cadence, or loosening parser tolerance to make a corrupt evidence channel look cleaner.
- Phase 3 `silent_scale ↔ agc_gated` as first response (primary already dark; blocked).
- Phase 2C spectrogram fast release (no named residual).
- Smart Director Comet allowlist changes (out of scope for this lane).

---

## Blocked on

- VME L1 has no approved production patch. Hardware VMEWT capture is additionally blocked by the transport incident reopen gate.
- K1 1401 was flashed with non-shippable probe builds during the failed lane. If the next use is product eyes-on, a regression sentinel, or handing the device back as trusted, restore or verify normal `k1_hardware` on the exact device. If the next use is a controlled probe/eval build after the VMEWT reopen gate passes, verify identity and flash that intended probe directly.
- Mode 18 is a VME target, but its quarantined secondary-dark fix is not part of the clean VME baseline.
- Remaining dirty lanes require separate acceptance decisions; do not bundle.

---

## Next steps in order

1. Read the VMEWT incident report before any VME work.
2. Do not treat 1401 as product-trusted while probe firmware may be present. Restore normal `k1_hardware` only before product eyes-on, regression sentinel, or trusted handback; for controlled probe/eval work, verify identity and flash the intended build directly.
3. Rebuild VME from the fail-closed transport contract; no hardware capture until the reopen gate passes.
4. Produce the baseline packet and primitive map for modes 7, 8, and 18.
5. Define the shadow VME port and paired final-byte probe before any production patch.
6. Keep dirty lanes quarantined unless Captain explicitly reopens one.

---

## Quarantined unfinished lanes

| Quarantine file/lane | Location |
|------|------|
| Secondary dark-state, anti-creep, Tempo Comet, VP chroma, trace-dev config, evidence | `wip/2026-06-07-unfinished-lanes-quarantine` @ `a40bdb8` |

Evidence bundle remains available from that branch at `evidence/20260607T025458Z-secondary-throttle-ab/` and `docs/forensics/runtime-evidence/2026-06-07-*`.

---

## Constraints encountered

- Branch `wip/audio-saliency-recovery` may be shared; always `git log --oneline -10` fresh before acting.
- Always verify `git rev-parse --short HEAD` before claims; expected lane is current `wip/audio-saliency-recovery` HEAD with firmware-source baseline `13ffe00`.
- Release NOT accepted: telemetry PASS, eyes-on FAIL pre-fix on secondary; post-fix eyes-on pending.
