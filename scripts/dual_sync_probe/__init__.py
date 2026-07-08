"""Dual-K1 BLE sync timing oracle (Phase 0, host-side, stdlib-only).

The oracle IS Phase 0's product: it turns two captured device serial logs
(leader + follower) into the four sync gate numbers, and it is proven
fault-evident against an injected fault battery (Gate 0) before any on-silicon
measurement is trusted. No network, no serial, no device access — pure,
deterministic analysis of captured text.

Modules:
    logfmt     — the canonical serial log-line grammar (firmware + oracle share it)
    correlate  — wire-truth offset, clock-error, apply-lateness, loss/dup, health
    gate_eval  — CLI + evaluate(): the four gate numbers as a deterministic verdict
    synth      — seeded synthetic log-pair generator for the fault battery

Lane authority: artifacts/k1_dual_sync_eval_2026-07-08/phase0-plan.md
Pin + log contract: artifacts/k1_dual_sync_eval_2026-07-08/probe-log-contract.md
"""

__all__ = ["logfmt", "correlate", "gate_eval", "synth"]
