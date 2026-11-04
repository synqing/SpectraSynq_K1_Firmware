---
abstract: "First hardware-confirmed audio-frame-to-LED-frame latency measurement on K1, 2026-09-10, both units. Bench B489A500 (WS2812, 150 px/lane, music via mic): newest sample to rmt_complete p50 11,596 us, p99 15,444 us. RPL 9087A500 (line-in silent): p50 10,671 us, p99 17,482 us. The 8,000 us AP-service gate PASSES on both (p99 7,144 / 7,261). Records three defects found: the Lever-2 lane had no trace hook at all, k1_bench_scheduling_trace_dev does not link, and the Lever-2 wire carries 24 bits/px not 48. Read before quoting any K1 latency figure."
---

# Audio frame → LED frame, measured on hardware (2026-09-10)

**Status:** first end-to-end latency measurement taken on any K1 build.
**Authority:** Captain directive 2026-09-10, "conduct a FULL SCALE EVALUATION and
TEST to establish the fucking time taken between audio frame and led render frame".
**Firmware under test:** `5e7dd51f` + the Lever-2 hook fix in this commit.

## Headline

| | Bench `B489A500` | RPL `9087A500` |
|---|---|---|
| Lane | WS2812, 150 px/lane, 2 lanes | Lever-2 lane, 160 px/lane, 2 lanes |
| Audio source | IM69D130 PDM mic, **real music** | PCM1808 line-in, **silent** |
| Joined frames | 43 | 63 |
| Audio frame → analysis published, p50 / p99 | 4,742 / **7,144** | 3,583 / **7,261** |
| Published → transmission starts, p50 / p99 | 2,240 / 5,269 | 2,010 / 7,203 |
| LED wire, hardware-confirmed, p50 / p99 | 4,594 / 4,658 | 4,879 / 4,893 |
| **Newest sample → LED frame complete, p50 / p99** | **11,596 / 15,444** | **10,671 / 17,482** |
| Oldest sample in chunk → LED complete, p50 / p99 | 19,017 / 22,865 | 18,150 / 24,961 |

All values microseconds. Fastest single frame across both units: **9,058 µs**.
Nothing measured below 8 ms.

**The 8,000 µs gate passes on both units.** `ap_publication_freshness`
(`newest_sample_estimate_us` → `ap_publish_us`) came in at 7,144 µs p99 on the
bench and 7,261 µs p99 on the RPL. That gate only ever covered the first leg;
frame acquire, render and LED transmission all sit outside it.

**The 25,000 µs feature budget is close and, on the RPL, exceeded.** Worst
oldest-sample frame on the RPL was 25,547 µs. Nothing in the repository enforces
that budget — `feature_latency_contracts` is read by zero lines of code.

## Method

Two device-matched non-shippable probes, each parented to the environment its
unit was already running so the mic and LED profile could not drift:

- `k1_bench_led150_sched_trace_probe` → `B489A500`
- `k1_rpl_ws2816_sched_trace_probe` → `9087A500`

Audio leg from the on-device APCAD ring (`:apcad_capture=4000` then
`:apcad_dump=1`), giving `newest_sample_estimate_us` and `ap_publish_us`.
LED leg from `:scheduling_trace=start` / `=dump`, giving `rmt_submit_us` and
`rmt_complete_us`. Both clocks are `esp_timer_get_time()`, so the two rings join
directly.

`rmt_complete_us` is stamped inside the ESP-IDF RMT `on_trans_done` **hardware
interrupt** (`diag/k1_rmt_completion_trace.cpp:275`, flagged
`K1_RMT_TRACE_RECORD_CONFIRMED`). It is genuine transfer completion, not
`FastLED.show()` returning — the distinction the Gate 0 harness inventory
explicitly warns about.

Join rule: for each analysis publish, the **first** LED frame submitted after it.
That is the earliest possible light for that audio, so these figures are a
**floor**, not a worst case.

Capture health on both runs: 128 confirmed completions, `p_drops=0`, `s_drops=0`,
`wait_failures=0`, `capture_valid=1`, `auto_stops=1` (ring full at 64 frames).

Acoustic path confirmed live on the bench before capture: `max_raw` moved 29 →
1,666, `peak_scaled` 0.89, `silence=0`. Stimulus regenerable via
`make_stimulus.py`.

## Three defects this exposed

**1. The Lever-2 lane had no trace hook at all.**
`k1_scheduling_trace_before_fastled_show()` sits immediately before
`FastLED.show()` at the bottom of `visual/led_utilities.h`. The WS2816 Lever-2
branch has its own emit and `return`s ~140 lines earlier, so the hook was never
called on that lane. Every WS2816 capture returned with the arm request still
pending, `active=0`, `frames=0` and zero completions, while `p_submit` climbed
past 8,000 — the linker wrapper sees submits regardless of the hook. The render
trace had already been bitten by this exact return and carries a comment saying
so; the scheduling trace never got the same fix. Fixed in this commit.

**2. `k1_bench_scheduling_trace_dev` does not link.**
`` `dram0_0_seg' overflowed by 3608 bytes `` — it pulls in MabuTrace, which
neither `k1_rmt_completion_trace.cpp` nor `k1_scheduling_trace_telemetry.cpp`
references. This is the practical reason the measurement had never been taken.
The two probes above replace it and both link clean.

**3. The Lever-2 lane puts 24 bits per pixel on the wire, not 48.**
Measured on the RPL: `payload_bytes=480`, `num_symbols=3842` over 160 px, wire
4,879 µs — near-identical to the 24-bit bench unit. Protocol arithmetic for
48-bit packing predicts 9,600 µs. Either the two traced channels each carry a
dual-DIN half, or the 6-byte packed buffer is not what reaches them. **Unresolved
— do not quote a 16-bit colour claim until it is.**

## Also established

- **The two LED channels transmit in parallel.** Channel 1 submits 74 µs after
  channel 0 and they overlap completely; both together span 4,677 µs wall-clock,
  not 9,188. Wire cost is set by pixels *per lane*.
- **The VP free-runs at 191 FPS** (frame interval p50 5,229 µs) against a 133 Hz
  audio publish rate, so it renders ~1.43 frames per audio frame. The wire is
  **88 % of that frame interval** — LED transmission, not render, is the
  frame-rate limiter.

## Bounds

Sample counts are tens of frames, not thousands: the completion ring holds 64
frames per channel and auto-stops when full. The RPL had no audio into its
line-in (`sil` 76/76), so its analysis leg is representative (Goertzel cost is
data-independent) but its onset and tempo paths were never exercised — **treat
the RPL row as provisional**. Both devices were restored to their original
environments and identity-verified after capture.

## Files

| Path | Contents |
|---|---|
| `bench-B489A500/apcad_dump.txt` | 516 APCAD rows, 0 dropped |
| `bench-B489A500/k1rmt_dump.txt` | 128 confirmed RMT completions |
| `rpl-9087A500/apcad_dump.txt` | 533 APCAD rows, 0 dropped |
| `rpl-9087A500/k1rmt_dump.txt` | 128 confirmed RMT completions |
| `make_stimulus.py` | regenerates the acoustic stimulus |
| `join_latency.py` | reproduces every number in this document |

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-09-10 | agent:claude-code | Created — first hardware-confirmed audio-to-LED latency measurement on K1, both units, plus the three defects the attempt exposed. |
