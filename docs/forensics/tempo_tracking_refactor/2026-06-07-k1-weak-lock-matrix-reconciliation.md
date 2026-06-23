# K1 Weak-Lock Matrix Reconciliation

## Verdict

Status: **reconciled except scoped Loreen residual**.

Production AP-stream labels still report `PASS_timing_but_weak_lock` for some required fixtures because the one-Hz AP capture surface lacks high-confidence locked rows. Declared-rate device NOV replay proof closes three of four weak-lock lanes as cadence/timing failures, not tempo-tracker failures.

## Reconciled (NOV replay lock proof)

| Fixture | AP-stream label | NOV replay classification | Evidence |
|---------|-----------------|---------------------------|----------|
| `slow_84_syncopated` | weak-lock | `declared_rate_device_nov_replay_locks_near_target` | `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-weak-lock-probe.md` |
| `click_127` | weak-lock | `declared_rate_device_nov_replay_locks_near_target` | gain-normalised `ffplay` +18 dB recapture |
| `fast_127_fourfloor` | weak-lock | `declared_rate_device_nov_replay_locks_near_target` | gain-normalised `ffplay` +18 dB recapture |

Harness policy: `WEAK_LOCK_NOV_RECONCILED_FIXTURES` in `k1_av_layer_classifier.py` — these fixtures no longer drive matrix `PARTIAL` on weak-lock alone.

## Scoped residual

| Fixture | Status | Notes |
|---------|--------|-------|
| `loreen_127` | **P2 scoped** | Near-target timing (`129 BPM` warm median); zero locked/high-confidence warm rows in bounded replay. Real-music confidence gap, not cadence failure. Does not block Scene Policy v2 serial state gate. |

Open finding tag: `P2_loreen_127_confidence_weak_lock_scoped`.

## Closed lanes (separate from weak-lock)

| Lane | Status | Evidence |
|------|--------|----------|
| Silence/open-quiet P1 | **CLOSED** | `docs/forensics/tempo_tracking_refactor/2026-06-07-k1-silence-open-quiet-vu-gate.md` |
| Scene Policy v2 serial A/B state | **PASS** | `docs/forensics/runtime-evidence/2026-06-07-scene-policy-v2-serial-ab-state-gate.md` |
| Main K1 primary channel (12201) | **RECOVERED** | `docs/forensics/runtime-evidence/2026-06-07-stuck-primary-12201-swarm-verdict.md` |

## Remaining promotion gate

Captain/video product judgement for Scene Policy v2 perceptual A/B — serial/state evidence captured; no camera attached.

## Matrix interpretation after reconciliation

- **FAIL**: runtime/tempo-lane regression on required music fixtures only.
- **PARTIAL**: unreconciled weak-lock (`loreen_127` only among required gates) or skipped fixtures.
- **PASS**: runtime green, no blocking failures, silence lane closed, weak-lock either absent or NOV-reconciled.
