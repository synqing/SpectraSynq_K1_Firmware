# ADR-0008: USB audio keeps the 12.8 kHz AP hop

**Status:** Accepted architecture (Captain 2026-08-25). Not a flash GO. Not a 48 kHz implementation lane.
**Date:** 2026-08-25
**Deciders:** Captain
**Tree:** [`SpectraSynq_K1_Firmware`](/Users/spectrasynq/SpectraSynq_K1_Firmware)
**Prototype:** [`docs/usb-audio/K1_USB_AUDIO_PROTOTYPE.md`](../usb-audio/K1_USB_AUDIO_PROTOTYPE.md)

---

## Decision (locked)

```text
Accept 48 kHz over USB          ≠          Run K1’s AP pipeline at 48 kHz
       feasible later                          forbidden
```

The USB-audio prototype stays:

```text
12.8 kHz  mono  S16  96 samples  7.5 ms
```

AP Core 0 must never know the host was 48 kHz. `DEFAULT_SAMPLE_RATE` stays 12800. GDFT, novelty, onset, tempo, canonical commit, and `acquire_sample_chunk` stay on that lattice.

Mac-side conversion is the prototype path: grouped output (or an application that converts independently) feeds 12.8 kHz to K1 and 48 kHz to speakers. Apple Multi-Output Device is **not** a design contract for mismatched rates.

---

## Context

The hop is 96 samples at 12.8 kHz = 7.5 ms (133.333 Hz). Scheduling restamp 2026-08-16 set AP service p99 to **8000 µs**. That is still not spare Core-0 budget for a resampler: tempo-emitting work already sits on the hop wall (admitted music compact p99 7712 µs under the 8000 µs gate). Putting even 100–300 µs of SRC inside `loopTask`, `acquire_sample_chunk`, commit, GDFT, or tempo would steal the wrong core.

USB Full-Speed can carry 48 kHz mono S16 (~0.77 Mbit/s). The S3 can almost certainly run a small 4/15 polyphase FIR. Core 0 AP cannot own it.

Arduino-ESP32 3.3.11 `USBAudioCard` creates `_uacReceiveTask` at priority 5 with `tskNO_AFFINITY`. That is acceptable only while the callback copies bytes and enqueues. A resampler inside that callback can preempt AP on Core 0.

---

## Options considered

### A — Keep 12.8 kHz UAC; Mac converts (chosen for this prototype)

| Dimension | Assessment |
|-----------|------------|
| AP cadence | Unchanged |
| Host complexity | Grouped-output / SoundSource trial |
| Product Multi-Output | Not guaranteed |

**Pros:** Zero extra Core-0 work. Exact current hop. **Cons:** Relies on Mac routing, not Apple Multi-Output as a rate converter.

### B — 96 samples at 48 kHz through AP

96 / 48000 = 2 ms → 500 AP frames/s (3.75×). Dead on arrival.

### C — 360 samples at 48 kHz through AP

Preserves 7.5 ms cadence but retargets history, windows, and every 12.8 kHz coefficient. New analysis engine. Rejected.

### D — Named transport SRC off AP (`K1_USB_AUDIO_48K_TRANSPORT_SRC`)

Only if native Multi-Output at mixed rates becomes a hard product requirement. Locked shape:

```text
UAC1 48 kHz mono S16
→ callback: byte copy into a static 48 kHz ring; return
→ Core-1 pinned SRC task: 360 → 96 polyphase FIR (4/15)
→ existing canonical mailbox
→ unchanged 12.8 kHz AP on Core 0
```

Forbidden: `DEFAULT_SAMPLE_RATE = 48000`, SRC in the UAC callback, SRC in `loopTask` / acquire / commit / GDFT / tempo.

No timing measurement, no promotion. Required before any promotion: SRC p50/p95/p99/max, AP active-work p99 before vs after, AP cadence and drops, mailbox underflows, 48 kHz ring overflows, LED FPS p50/p99, queue age, audio-to-analysis latency.

---

## Consequences

- Easier: prototype stays on the proven hop; agents cannot “just bump the rate”.
- Harder: Bose + K1 together needs a Mac converter, not a hope that Multi-Output resamples 12.8 kHz correctly.
- Revisit: only under a named GO for `K1_USB_AUDIO_48K_TRANSPORT_SRC`.

## Action items

1. [x] Record this ADR and ratchet the probe env to 12800 (host static test).
2. [ ] Prototype close remains A16–A26 on a Main-RPL-parented image (onset serial + 30 min soak still open). Product is restored; do not reflash USB without a new GO.
3. [ ] Mac grouped-output / SoundSource trial — only if Captain names it.
4. [ ] Do **not** open the 48 kHz SRC lane until Multi-Output at mixed rates is a named product requirement.
