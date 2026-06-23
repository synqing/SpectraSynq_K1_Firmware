---
abstract: "Canonical incident report for the failed VMEWT hardware evidence lane: sandbox-only CSV serial transport was corrupted, survivor rows are not runtime proof, and VME hardware capture is frozen until a fail-closed transport contract exists."
---

# VMEWT Transport Incident - 2026-06-07

## Status

**FAILED / TRANSPORT INVALID / NOT RUNTIME PROOF**

This report is the canonical repo record for the failed VMEWT hardware evidence lane. The attempted VME Waveform Tempo runtime capture produced partial survivor rows from a corrupted serial transport. Those rows are salvage material only; they do not prove VME behaviour, final-byte parity, tempo fallback, or hardware readiness.

The VME hardware evidence lane is frozen until the reopen gate in this document is satisfied.

## Containment

Canonical repository state at the time of containment:

- Branch: `wip/audio-saliency-recovery`
- Observed HEAD: `76a657f`
- Firmware-source baseline under the current VME docs: `13ffe00`
- Firmware/platformio parity check: `git diff --name-status 13ffe00..HEAD -- SPECTRASYNQ_K1_FIRMWARE platformio.ini` produced no diff.
- Dense Forge recovery remains committed separately at `a5ce32e fix(vp): restore Dense Forge transport`.
- Failed VMEWT edits and captures were reported as sandbox-only under `/tmp/k1_vme_waveform_BloAgX/SensoryBridge-main 9`.
- No canonical Dense Forge, Scene Policy, Smart Director, Phase 2B, `led_utilities.h`, Waveform effect source, AGC, calibration, brightness, or silence-threshold change is accepted from the failed lane.

The `/tmp` sandbox is volatile evidence storage. Do not depend on it as durable source truth. This canonical report preserves the containment verdict and the metrics reported during the incident.

## Hardware Risk

K1 1401 was flashed with non-shippable VME probe builds during the failed lane. It is not product-trusted until firmware identity is verified.

Restore or verify normal `k1_hardware` only before product eyes-on, a regression sentinel, or handing the device back as trusted. If the next authorised use is a controlled probe/eval build after the VMEWT reopen gate passes, do not flash production first; verify the exact device by USB MAC/chip ID and flash the intended probe build directly.

Do not run calibration as part of either path. `start_noise_cal` still requires explicit Captain silence confirmation.

## Failed Evidence Summary

| Capture summary | Accepted records | Rejected records | Ignored lines | Issues | Channel coverage | Scenario coverage | Verdict |
|---|---:|---:|---:|---:|---|---|---|
| `2026-06-07-waveform-tempo-music-short-summary.json` | 92 | 12 | 103 | 11 | secondary only | weak-confidence only | invalid transport |
| `2026-06-07-waveform-tempo-music-quiet-summary.json` | 86 | 19 | 102 | 15 | secondary only | weak-confidence only | invalid transport |
| `2026-06-07-waveform-tempo-music-summary.json` | 91 | 5 | 228 | 5 | secondary only | weak-confidence only | invalid transport |
| `2026-06-07-waveform-tempo-summary.json` | 23 | 45 | 220 | 37 | secondary only | weak-confidence only | invalid transport |

Any nonzero rejected record, ignored fragment, malformed token issue, or missing coverage fails the transport layer. These captures failed before VME payload analysis could begin.

The strongest final failed log was reported at:

```text
/tmp/k1_vme_waveform_BloAgX/SensoryBridge-main 9/docs/forensics/vme_l1/captures/2026-06-07-waveform-tempo-vmewt-1401-music-short.log
```

Reported corruption examples:

- Lines 4-6 began mid-record with suffix-only fragments such as `u=...` and `vu=...`.
- Line 11 began with `,vu=...`.
- Line 22 began with `8,vu=...`.
- Line 26 began with `=1380,...`.
- Line 51 contained a malformed partial row ending around `f7,vu=...`.
- Line 187 contained a malformed partial row around `fr=11040,...,w87,...`.
- Line 203 contained a malformed partial row around `sc70,...`.

Those examples identify row truncation/framing loss, not a readable schema problem.

## Overclaim Correction

`/tmp/k1_vme_waveform_BloAgX/SensoryBridge-main 9/docs/forensics/vme_l1/2026-06-07-waveform-tempo-capture-analysis.md` reportedly stated that sandbox runtime capture was complete while also recording 23 accepted rows and 45 rejected corrupted/incomplete rows.

That conclusion is invalid. Treat that file as evidence of the mistaken reasoning pattern, not as a proof document.

The only defensible reading is:

```text
Partial secondary weak-confidence rows were salvaged from a corrupted transport.
They are not runtime proof.
```

## Root Cause

The attempted VMEWT evidence path emitted CSV/text from the firmware side while the host script read arbitrary serial chunks and decoded them as text. The transport had no hard framing contract:

- no sequence number
- no length prefix
- no CRC
- no ACK/retry
- no gap detection
- no backpressure accounting
- no deferred drain boundary
- no requirement that marker count equal accepted row count

The parser then accepted complete survivor rows while rejecting fragments. That created false confidence because the summary still contained metrics despite the transport being invalid.

## Operational Failure Pattern

The failed lane repeated this bad loop:

1. Ambient or live music was treated as meaningful evidence before a controlled input contract existed.
2. Some rows parsed, so the capture was treated as usable.
3. AP/VP interleaving was assumed to be the root cause, so diagnostic streams were quieted.
4. Row length was assumed to be the root cause, so the row was shortened.
5. Tests passed, so the hardware evidence path was treated as ready.
6. Survivor rows were analysed even though rejected records and malformed fragments persisted.

For VME proof work, this is backwards. Transport integrity is binary: clean, framed, complete, and fail-closed, or not evidence.

## Immediate Stop Order

Do not:

- run another VMEWT hardware capture
- flash another VME probe build
- tune baud rate, cadence, row length, or parser tolerance
- analyse survivor rows as proof
- accept AP stream, APCAP, or frame dump as VME final-byte proof
- patch production Waveform, Waveform Fast, or Waveform Tempo for VME
- touch Dense Forge, Scene Policy, Smart Director, Phase 2B, `led_utilities.h`, AGC, calibration, brightness, or silence thresholds

## Reopen Gate

VME hardware capture may reopen only after all of the following are true.

1. Host parser fail-closed tests exist and fail on corrupt logs.
   - Any rejected row fails.
   - Any malformed-token issue fails.
   - Any unexpected ignored line fails.
   - Any marker-count mismatch fails.
   - Any missing primary/secondary coverage fails.
   - Any missing mode 7/8/18 coverage fails.
   - Any missing silence, weak-confidence, locked/strong, onset, dense, and decay scenario coverage fails.

2. Firmware transport is a bounded deferred diagnostic pool, not render-path serial CSV.
   - Render-reachable code may push fixed-size records only.
   - No heap, `String`, file I/O, blocking call, or USBSerial print in render-reachable capture code.
   - Records include magic, version, kind, payload size, flags, sequence, frame, timestamp, and CRC.
   - Pool status exposes dropped, corrupt, overflow, high-water, and sequence-gap counters.
   - Serial drain happens only after stop/freeze, from lower-priority code.

3. VME payload proof is paired at the final-byte boundary.
   - Current Waveform path and candidate VME path receive identical seeded state and context.
   - Records cover modes 7, 8, and 18.
   - Records cover primary and secondary independently.
   - Mode 18 includes tempo state, including `ChannelEffectState::tempo_scroll_accum` and `tempo_last_ms`.
   - Metrics include final-byte error, active-pixel, centre-of-mass, trail/tail memory, hue/saturation, render time, frame time, and transport counters.

4. Offline gate passes before hardware.
   - Strict parser returns zero rejected records, zero issues, zero unexpected ignored lines, zero dropped/corrupt/overflow, and no sequence gaps.
   - `k1_hardware` does not link diagnostic transport or MabuTrace symbols.
   - `k1_hardware_harness` or trace/probe env remains explicitly non-shippable.

5. Only then perform one controlled hardware capture.
   - Device identity verified by USB MAC/chip ID.
   - Input source and track/scenario are named.
   - Mode, channel, smart state, palette/chroma settings, brightness, and runtime config are recorded.
   - If any transport counter fails, stop immediately. Do not patch around it.

## Minimal Architecture Direction

Use the existing VPAB-style deferred capture pattern as the model, not the failed VMEWT CSV firehose.

The target shape is:

```text
render path -> fixed-size binary record into preallocated pool
stop/freeze -> lower-priority drain emits framed records
host parser -> strict seq/length/CRC/coverage validation
analysis    -> final-byte VME parity only after transport passes
```

Current VPAB/final-byte machinery is a precedent, but existing self-shadow or absent-memory smoke output is not enough. The VME reopen must add paired current-vs-VME records and mode 18 coverage before any hardware claim is meaningful.

## Authority

This document supersedes any sandbox summary that describes VMEWT runtime capture as complete, passing, or proof-bearing. The VME L1 Waveform lane remains sandbox/shadow only, and its next valid step is a fail-closed transport contract before hardware is touched again.
