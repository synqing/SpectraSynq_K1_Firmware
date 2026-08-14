---
abstract: "Transfer-test QUIET leg, 2026-08-12: Unit 2 (0C54FC00) and bench (B489A500) captured simultaneously on identical firmware 39e0943, witness-verified silent room. SSL-normalised max_raw distributions agree within 9% at the median and 1% at p95 — evidence AGAINST a per-unit hardware cause for the 1.25-vs-2.50 joint-fraction delta. Music legs still required and blocked on the speaker. Also records the :ap_stream=1 type=value syntax."
---

# Transfer test — QUIET leg, both units, 2026-08-12

> **P0.0 quarantine notice (2026-08-15):** the B489 comparator belongs to the contaminated
> IM69D mono-default epoch, so the transfer ratio is `RE-DERIVED`; Unit 2 RIGHT-slot data
> remains valid only on its own. See
> `docs/forensics/P0_0_AP_INPUT_QUARANTINE_MANIFEST_2026-08-15.md`.

**Question this leg addresses:** the joint level fraction is **1.25** on the bench and
**2.50** on Unit 2. Captain's position is that it should transfer, and that the
"per-unit" framing is wrong. The handover's candidate mechanisms, in its order of
suspicion, were **(a)** LED current coupling into the mic supply, **(b)** capsule
sensitivity, **(c)** PDM trace routing — all three of which are *per-unit* causes.

A per-unit cause should be visible in **quiet**, where no stimulus is involved.
This leg tests exactly that, and it needs no speaker — so it was runnable now.

## Conditions

| | |
|---|---|
| Firmware | **both units on `39e0943d`** — parity established this session; previously they were on different builds |
| Unit 2 | `0C54FC00`, `/dev/cu.usbmodem1101`, env `k1_unit2_im69d_right`, 206+206 px |
| bench | `B489A500`, `/dev/cu.usbmodem12201`, env `k1_bench_im69d`, 160+160 px |
| Capture | 45 s, **both units concurrently** (same room, same wall-clock window) |
| Witness mic | MacBook Pro Microphone, **resolved by name** — index 1 was the Bose's own mic at capture time, the documented ffmpeg-index trap |
| Room, before | −67.3 dBFS mean |
| Room, **during** | **−58.5 dBFS mean, −37.5 dBFS max** over 3696 frames |
| Calibration | **inherited, NOT re-fired.** No `start_noise_cal` was sent to either unit — Captain-verbal-gated. |

## Result

| | frames | SSL | silence % | `rms_raw` med | **ratio med** | ratio p95 | ratio max |
|---|---|---|---|---|---|---|---|
| **Unit 2** | 49 | 136 | 61.2 % | 0.0004 | **1.06×** | 1.70× | 2.05× |
| **bench** | 45 | 144 | 57.8 % | 0.0013 | **1.17×** | 1.72× | 1.92× |

`ratio` = `max_raw ÷ that device's OWN SSL`, which is the transfer test's specified
comparison — not raw counts.

**Median 9 % apart. p95 1 % apart (1.70× vs 1.72×).**

## Reading

**The quiet distributions do not separate.** Whatever produces the 1.25-vs-2.50
fraction delta is **not present in quiet**, normalised. That is evidence against
all three of the handover's per-unit candidates, because a hardware asymmetry —
LED supply coupling, capsule sensitivity, trace routing — would not switch itself
off when the room is quiet. It leans toward Captain's position.

**What this leg does NOT establish, stated plainly:**

1. **Music legs are still required.** The fraction was derived under music; this
   leg is quiet only. It narrows the candidate set, it does not close the question.
2. **Both units are in the same room right now**, so a per-*room* hypothesis also
   predicts agreement here. This leg cannot separate per-room from "no effect" — it
   can only weigh against per-*unit*, which it does.
3. **SSL values are not directly comparable** (136 vs 144). Each was learned at a
   different time under a different calibration, and the bench's is recorded as
   stale. The comparison is deliberately *ratio*-based for that reason. Note in
   passing that Unit 2's SSL is *lower* than the bench's despite Unit 2 driving 412
   px against the bench's 320 — the opposite direction to what LED-current coupling
   would predict — but with uncomparable calibrations that is a hint, not a result.
4. **silence latched only ~58–61 %**, not ~100 %, on both units. The registry
   records the same for Unit 2 previously (70.8 %). Witness max of −37.5 dBFS during
   this window shows real room transients, so this is consistent rather than a new
   defect. The dwell/persistence gate recommended in the registry remains
   unimplemented.

## Still blocked

- **Music legs** — the Bose auto-sleeps and `blueutil` is denied Bluetooth
  permission on this host, so it cannot be woken programmatically. Laptop speakers
  deliver ~5× too little SPL to the K1. Needs a physical button press.
- **Bench recalibration** under a witness-verified silent room — `start_noise_cal`
  is Captain-verbal-gated and was not fired.
- **The `LED_COUNT_VALUE` 160 discriminator** on Unit 2 — one flash, same silicon,
  same capsule, only the LED current changes. Still the cheapest decisive test for
  candidate (a), and this quiet leg has already weakened (a) without it.

## Method note worth keeping

`ap_stream` is `SC_TYPED_ONLY` + `CMD_HARNESS` but **not** `CMD_PERSISTS` — it sets
the RAM flag `AP_STREAM_ENABLED` and writes no config, so it is safe and reversible.
Two traps cost time here:

- The dispatcher is **`type=value`**. `:ap_stream 1` returns `Bad command`;
  **`:ap_stream=1`** is correct. The space form failing on one unit and appearing to
  work on another is what made this look like an env asymmetry rather than a syntax
  error.
- `ap_capture` **is** `#if ENABLE_AP_STREAM`-gated and is absent from both of these
  envs; `ap_stream` at line 15 of `serial_typed_cmd_table.def` is unconditional and
  present. Reading only the first of those two facts produces the false conclusion
  that these builds cannot emit telemetry at all.

Both units were returned to `:ap_stream=0` after the leg.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Created. Quiet leg of the bench-vs-Unit2 transfer test, both units on 39e0943, witness-verified. Records the ratio agreement, what it does and does not establish, and the ap_stream syntax. |
