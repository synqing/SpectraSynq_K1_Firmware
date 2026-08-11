---
name: k1-deck16-session-discipline
description: >-
  HARD FAIL discipline from the 2026-08-07→08-09 Deck16 B1/B2, Mirror purge,
  Core-0 silent_scale / STANDBY strike, PRISM haunt, latency map≠RTT, layout16
  false MAIN approval, exclusive-port soak contention, and first-contact
  device-absence stop. Use before Tab5↔bench-K1 BLE work, identity hash claims,
  deck_state pending TX, 68/71 map drift, full-map harnesses, C6 soaks, dark-fade,
  MAIN glass authority, Mirror/STANDBY surfaces, or any claim about Deck16
  production readiness.
---

# K1 Deck16 Session Discipline (2026-08-09)

**Authority:**
[`docs/canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md`](../../../docs/canon/SESSION_CANON_2026-08-09_deck16_ble_backend_haunt_latency.md)

**Companion (HCI / IM69D HF-1…13):**
[`k1-vj-session-discipline`](../k1-vj-session-discipline/SKILL.md) ·
[`SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md`](../../../docs/canon/SESSION_CANON_2026-08-07_im69d_peakiness_deck16_boot.md)

Announce: "Using k1-deck16-session-discipline against SESSION_CANON_2026-08-09."

Then run the checklist. If any HARD FAIL would be violated, **stop and fix the
plan** before flash / soak / harness / claim.

## Thinking gate (required)

Route via `/thinking-model-router`. Default combo for this domain:

1. **Systems** — haunt feedback, soak-vs-flash contention, Core-0/1 races
2. **Map–territory** — host RTT / stale digests / layout JSON / port names vs silicon
3. **Archetypes** — Fixes That Fail (Core-1 pin); Shifting the Burden (delete grid)
4. **Steel-man** — strongest case for the tempting wrong fix, then kill with receipt
5. **Red team** — how the next PASS claim will lie
6. **OODA** — observe ports+hashes → orient peer identity → decide STOP or continue → act one exclusive lane

## Authority claim block (carry verbatim)

```text
DECK16_B1_B2_CORE_FUNCTIONAL_PASS=PASS
EXTENDED_RECOVERY_HARDENING=PASS
STANDBY_DIMMING=STRUCK
PRODUCTION_READY=NO
MERGE_TO_MAIN=DONE 2026-08-11 (Captain-authorised)
PROMOTION_TO_PRODUCTION=STILL_HOLD
```

Do not upgrade a line without a new on-disk receipt. `MERGE_TO_MAIN=DONE` is a
source-integration fact only: the boot-loop guard, the quiet-mic plate fix and
the dual-206 retarget carry HOST proof only, `PHASE1_GATE=FAIL` stands on
`B489A500`, and the flash freeze is unchanged. Merged is not proven.

## HARD FAIL checklist (HF-14…HF-31)

Copy and mark each item before acting:

- [ ] **HF-14** Not citing archaeology digests as live (`78fb9af9…`/`b60819a4…`, `d30c4fef…`/`cb549042…`). Re-read headers / `protocol-map-hashes.json`
- [ ] **HF-15** Not citing ~401 ms / ~4301 ms as BLE wire or apply RTT (host/harness artefacts)
- [ ] **HF-16** Not treating layout JSON / agent MAIN PASS as Captain MAIN approval
- [ ] **HF-17** Not deleting or permanently disabling the 16-grid (`DECK_UI_LAYOUT_MAP_DEBUG` stays)
- [ ] **HF-18** Not putting chroma/saturation/mirror/`secondary.enabled`/`prism_count` on MAIN
- [ ] **HF-19** Not re-enabling STANDBY_DIMMING anywhere
- [ ] **HF-20** Not weakening Core-0 silent_scale pin in `i2s_audio.h`
- [ ] **HF-21** Not reintroducing MIRROR to BLE/Deck (any synonym/stub)
- [ ] **HF-22** Not resuming full71/map harness without anti-haunt proof
- [ ] **HF-23** Not blind re-running all map paths — FAIL subset only; keep silence SKIPs
- [ ] **HF-24** Not running multi-hour soak concurrent with other flash/port lanes
- [ ] **HF-25** Not claiming radio dropout from `linked=null` dial misses
- [ ] **HF-26** Not substituting unknown USB serial for Tab5/bench — MAC/chip or STOP
- [ ] **HF-27** Not flashing C6 / `F887A500` / SoftAP / erase / commit without Captain
- [ ] **HF-28** Not reopening B1→B2 / optimistic ack_tx / Precision Bay
- [ ] **HF-29** Ran `tab5_protocol_parity_gate.py` before any coupled protocol build or flash
- [ ] **HF-30** Not treating the 71-control / `78fb9a...` registry as live authority
- [ ] **HF-31** Not claiming bidirectional closure from an ARMED snapshot alone

## 68/71 recovery gate

The live sender/receiver bytes are the territory. The current Unit2/Tab5
contract is exactly **68 controls** with registry MD5
`9b5db3fbb17438367adeaceb541db03b`. The 71-control / `78fb9a...` registry is
archaeology and must never be used to "correct" a live 68-control sender.

Before a protocol build, flash, commit, or compatibility claim:

```bash
python3 scripts/agent/tab5_protocol_parity_gate.py --repo-root .
```

For live closure, add `--serial-log <capture>`. `ARMED` plus one committed
snapshot and zero fault counters proves admission and snapshot compatibility.
Full bidirectional proof additionally requires `LIVE`, `sent>0`, and
`delta_commit>0` after one harmless physical control change.

## First-contact machine gate

Before any silicon claim:

```bash
bash scripts/agent/deck16-first-contact-gate.sh
# must print STEP1_PASS or STEP1_STOP with reasons
```

Manual order if script unavailable: handover §6 Steps 1→4, then ask Captain Lane A XOR B.

## Live digest stance (at Mirror purge; re-verify)

- controls **68**
- registry MD5 `9b5db3fbb17438367adeaceb541db03b`
- layout SHA-256 `f8e40f6b1ba7b115bb5e9f7310ac69636e0a10c8e478f7584dd1d5547b941510`

Hash gates = **admission/compatibility**, not anti-spoof.

## Devices (identity ≠ port)

| Role | Match | Env |
|------|-------|-----|
| Bench K1 | chip `B489A500` MAC `b4:3a:45:a5:89:b4` | `k1_bench_im69d_ble` |
| Tab5 P4 | MAC `30:ed:a0:e0:c1:a0` | `tab5_p4` |
| C6 | hosted HCI IF=4 | never reflash this lane |
| Main K1 | chip `F887A500` | **DO NOT TOUCH** |

## Canon sentences

1. Live digests live in headers — briefs rot when a purge lands.
2. Host RTT is a map; T0→T2 on-device is the territory.
3. Protocol loop PASS is not Captain MAIN approval.
4. Pending dirty across disconnect is a haunt.
5. Pin silence scale at Core-0.
6. Exclusive hardware ownership is required for soak science.
7. Absent peer → STOP. Alien Espressif ≠ Tab5.

## Closed vs open

**Do not redo:** B1/B2, recovery R1–R4, Mirror purge, STANDBY strike, Core-0 pin, Tier-1 MAIN + encoder-reserved grid.

**Do not claim PASS yet:** anti-haunt soak, VP-defaults reboot check, full71 27 FAIL burn-down, C6 `bar_4h_met`, optical MEASURED pack, PRODUCTION_READY/MERGE.

## Evidence pointer

See Evidence index in the session canon. Master handover:
`_scratch/deck16_session_handover_20260809/HANDOVER.md`.
