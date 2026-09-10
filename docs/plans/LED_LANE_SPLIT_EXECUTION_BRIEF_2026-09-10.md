---
abstract: "Phased execution brief for the LED lane split on branch lane/led-lane-split. Primary goal is removing the LED wire as the frame-rate ceiling (it is 88% of the frame interval) and buying headroom for true 16-bit WS2816; sub-8ms audio-to-light is a side effect, not the objective. Two tracks: Track A (docs + gate wiring, no hardware, start now) and Track B (P1 wiring truth -> P2 24-vs-48-bit -> P3 4-lane emitter bring-up -> P4 re-measure -> P5 optional early-publish). P3 carries a known brick precedent requiring full-chain flash. Read with 20260910T-audio-to-led-latency/RESULT.md, which is the baseline every phase is measured against."
---

# LED lane split — phased execution brief

**Branch:** `lane/led-lane-split`
**Baseline:** `docs/forensics/runtime-evidence/20260910T-audio-to-led-latency/RESULT.md`
**Authored:** 2026-09-10, after the first hardware-confirmed audio-to-LED measurement.

## Why this work exists

The LED wire occupies **88 % of the render frame interval** (4,594 µs of 5,229 µs,
measured). It is the frame-rate ceiling, and it is the reason true 16-bit WS2816
cannot work: 48-bit packing over 160 px needs 9,600 µs of transmission, which is
longer than the 7,500 µs audio period, so that lane could never sustain one frame
per audio frame.

The two LED channels were measured transmitting **genuinely in parallel** —
channel 1 starts 74 µs after channel 0 and they overlap completely. Transmission
cost is therefore set by *pixels per lane*, so redistributing pixels across more
lanes reduces it proportionally.

### What this is NOT for

**This is not a latency programme.** At a measured 11.6 ms median, K1 is already
inside the window where a person cannot detect the offset between a sound and the
light answering it. Sub-8 ms falls out of the lane split as a side effect; it is
not a reason to spend risk. If a phase below can only be justified by "it gets us
to 8 ms", stop and re-read this paragraph.

Ranked objectives:

1. Remove the wire as the frame-rate ceiling.
2. Make true 16-bit WS2816 sustainable at one frame per audio frame.
3. Stop the "sub-8 ms" claim propagating through canon (Track A).
4. Make the latency budgets enforceable rather than decorative (Track A).
5. Sub-8 ms median audio-to-light, if 1–2 deliver it for free.

## Guardrails

- Both units are currently on their original environments, identity-verified.
  Any probe flash is reverted at phase end and the device re-verified.
- `k1_hardware` is not touched by Track B. All Track B work is RPL-first
  (`9087A500`) and bench-second, both non-shippable.
- Chip identity governs, never port number. The device registry's advisory ports
  are stale — `B489A500` is on `usbmodem1101`, not `12201`.
- No phase closes on a build or a code read. Each closes on a device capture of
  the kind already built, stored under `docs/forensics/runtime-evidence/`.
- Existing hard rules in `AGENTS.md` and `.claude/CLAUDE.md` bind throughout.

---

# Track A — no hardware, start immediately

Independent of Track B. Cheap, and it stops the wrong number spreading.

## A1 · Correct the record

**Problem.** `~/.claude/memory/spectrasynq/L1/05_architecture.md:134` states
"**Sub-8 ms audio-to-visual latency** end-to-end" as canon. Line 198 of the same
file shows where it came from — "Frame rate 125 Hz (8 ms hops)" — and the whole
document describes **Lightwave-Ledstrip `firmware-v3`** (32 kHz SPH0645, 204
effects, RMT4), not this firmware. K1 runs 12.8 kHz at 7.5 ms hops. The number is
an audio hop period from another codebase, written up as an end-to-end latency.

Three in-repo forensic docs repeat it with a fabricated citation:

- `docs/forensics/2026-05-25-vp-palette-auto-colour-audit.md:17`
- `docs/forensics/2026-05-26-crgb16-ws2812-value-backtest.md:22`
- `docs/forensics/2026-05-26-vp-fastled-comparison-audit.md:21`

each asserting `[FACT] ... sub-8 ms audio-to-visual latency. Source: AGENTS.md`.
`AGENTS.md:310` says `<50 ms (audio capture → LED update)` and has never said 8 ms.

**Steps.** Replace each with the measured figure and a pointer to
`20260910T-audio-to-led-latency/RESULT.md`. In the L1 doc, either scope the line
to the Lightwave firmware it describes or strike it.

**Exit.** No document in the repo or in L1 memory asserts sub-8 ms as fact.
`grep -rn "sub-8" docs/` returns only historical annotations marked superseded.

**Who acts.** Agent. L1 memory edit needs Captain's nod since it is canon.

## A2 · Wire a checker to the feature latency budgets

**Problem.** `gate0/contract.json` carries seven `budget_us: 25000` entries and
one at `35000`. The gate runner references `ap_service_p99` eight times and
`feature_latency_contracts`, `budget_us`, `budget_formula`, `25000` and `35000`
**zero** times. The budgets are inert text. The RPL already exceeded 25,000 µs on
its worst measured frame (25,547 µs) and nothing noticed.

**Steps.**
1. Teach `scripts/regression-harness/k1_scheduling_gate0.py` to read
   `feature_latency_contracts` and evaluate them against a joined capture, using
   `join_latency.py` as the reference implementation.
2. **Prove it can go red.** Feed it a capture with a deliberately blown budget and
   confirm the specific budget fails while the others stay green. A checker never
   seen to fail is not a checker.
3. Add the fault to the Gate 0 required-faults battery.

**Exit.** Runner fails on a blown feature budget and passes on today's bench
capture. Mutation evidence recorded.

**Who acts.** Agent.

---

# Track B — hardware-gated, sequential

Each phase gates the next. Do not begin a phase whose entry criteria are unmet.

## B1 · Establish the physical truth of the RPL LED wiring

**Entry.** None.

**The unknown.** The RPL pinmap defines four LED lines — `LED_DATA_PIN 15`,
`LED_CLOCK_PIN 16`, `SECONDARY_LED_DATA_PIN 17`, `SECONDARY_LED_CLOCK_PIN 18` —
and the device registry describes them as "WS2816 dual-DIN primary GPIO15/16 +
secondary GPIO17/18". For WS2812/WS2816 there is no clock line, so 16 and 18 are
second data injection points. **Whether they are physically connected to the
strips, and at which pixel, is not knowable from software.** The whole lane-split
package rests on this.

**Steps.**
1. Probe build that drives a distinct known pattern on 16 and 18 only.
2. Observe: do any pixels respond, and from which pixel index?
3. If nothing responds, scope the pins to distinguish "not wired" from "wired but
   not driven".

**Exit.** A written answer: dual-DIN wired (and at which injection point), or not.

**Decision.** Wired → B2. Not wired → the split becomes a board change for the
next revision; Track B pauses and Track A continues.

**Who acts.** Agent builds and flashes the probe; **Captain confirms what the
plate does**, because this one is genuinely an eyes-on question about physical
wiring, not a render-path question an instrument already answers.

**Rollback.** Restore `k1_main_rpl_pcm1808_p6_probe`, verify identity.

## B2 · Resolve 24-bit versus 48-bit on the Lever-2 lane

**Entry.** B1 answered.

**The unknown.** The RPL measured `payload_bytes=480`, `num_symbols=3842` over
160 px — **24 bits per pixel**, wire 4,879 µs, near-identical to the 24-bit bench
unit. Protocol arithmetic for the 6-byte Lever-2 packing predicts 9,600 µs. So
either the two traced channels each carry a dual-DIN half, or the packed
`ws2816_wire` buffer is not what reaches them. **Until this is settled, no 16-bit
colour claim can be made about the shipping RPL build.** This matters
independently of latency.

**Steps.**
1. `:rtrace_arm` / `:rtrace_dump` on `k1_main_rpl_rtrace_probe` to capture the
   packed buffer; count bytes per logical LED.
2. Compare that against `payload_bytes` on each RMT channel from the scheduling
   trace, on the same frame.
3. Determine whether `K1_LED_I2S_DIRECT_V1` is required for true 16-bit emit, or
   whether the RMT path can carry it.

**Exit.** A definitive statement of what the RPL currently puts on the wire, with
byte counts from both taps on the same frame.

**Who acts.** Agent. Instrument, not Captain's eyes — the render-path tap exists.

## B3 · Bring up the four-lane emitter

**Entry.** B1 = wired, B2 answered.

**What exists already.** `visual/k1_i2s_emit.cpp` — a direct LCD_CAM ("Yves")
driver behind `K1_LED_I2S_DIRECT_V1`, called as
`k1_i2s_emit_init(ws2816_wire, 4, CONFIG.LED_COUNT, pins)` with a 4-pin array.
Env `k1_main_rpl_i2sled_probe` exists, RPL-only, non-shippable, parked.

**Known hazards, both documented.**
- **Brick precedent.** `20260820T-i2sled-rpl-brick/RESULT.md`: flashing this probe
  left the RPL with "No bootable app partitions". The postmortem is explicit that
  the app never started, so it was **a flash failure, not an I2S runtime fault**.
  Recovery required a full-chain write — bootloader `0x0`, partitions `0x8000`,
  `boot_app0` `0xe000`, app `0x10000`. App-only was not enough.
- **FastLED shim is poison here.** `FASTLED_USES_ESP32S3_I2S` forces
  `COLOR_ORDER_RBG` (blue-for-gold) and re-inits `RectangularDrawBuffer` per
  strip, killing the secondary. The direct driver must be used, not the shim.

**Steps.**
1. **Bench first, not RPL.** Prove the driver on `B489A500` where a brick is
   cheap.
2. Full-chain esptool flash, never app-only. Unbrick runbook open before the
   first write.
3. Verify identity, then colour correctness on both strips (primary and
   secondary alive, no RBG swap), then FPS.
4. Only then repeat on the RPL, under a named GO.

**Exit.** Both strips correct on both units, identity verified, FPS recorded.

**Rollback.** Full-chain flash back to the parent env; verify identity and
`CAL_VALID`.

**Who acts.** Agent flashes; **Captain gives the named GO before the RPL write**,
per the standing rule on that env.

## B4 · Re-measure

**Entry.** B3 green.

**Steps.** Re-run the Phase 0 capture unchanged — same probes, same commands,
same `join_latency.py` — on the four-lane build. Bench with real music.
**The RPL needs a cable from the Mac output into its PCM1808 line-in**; without it
its onset and tempo paths are never exercised and its row stays provisional.

**Exit.** A new dated directory under `docs/forensics/runtime-evidence/` with the
same table as the baseline, and a diff against it.

**Success is judged on the ranked objectives, not on 8 ms:**

| Objective | Baseline | Target |
|---|---|---|
| Wire as fraction of frame interval | 88 % | < 50 % |
| Wire time p50 | 4,594 µs | ≈ 2,400 µs |
| Frame interval p50 | 5,229 µs (191 FPS) | shorter |
| 16-bit sustainable at one frame per audio frame | no | yes |
| Newest sample → LED complete p50 | 11,596 µs | ≈ 8,600 µs (projection) |

**Kill criterion.** If wire time does not drop materially, the package has failed
its primary objective. Stop; do not proceed to B5 chasing the latency number.

## B5 · Early publish — optional, contract change

**Entry.** B4 green **and** Captain has decided sub-8 ms is worth a contract
change. Skip by default.

**Change.** Publish the fast features (level, onset) as soon as they are known,
and let chord and tempo land on the following frame. Most of the p99 tail is the
tempo stage, which runs every third frame and costs 1,500–2,200 µs.

**Contract impact.** Breaks `locked_architecture.ap_pipeline:
"single_complete_transaction"` in `K1_SCHEDULING_GATE0_2026_08_15`. Requires a
Captain restamp and, per the contract's own change rule, a Gate 0
requalification before candidate measurement.

**Hazard.** Two generations in flight. The trace already carries
`mixed_generation_count`, so the detector exists before the hazard — assert on it.

**Exit.** AP leg p50 and p99 both reduced, `mixed_generation_count` zero,
requalification complete.

## B6 · Promotion decision

**Entry.** B4 green, B5 done or skipped.

Nothing above ships by default — every Track B env is non-shippable. Promotion
means a separate, deliberate decision to move the four-lane emit onto
`k1_hardware` and/or `k1_main_rpl_im69d`, with its own eyes-on and its own
capture. Note `k1_hardware` has only two LED lines defined, so promotion there is
blocked on a board revision regardless of firmware readiness.

---

## What "done" looks like

| Item | Stamp |
|---|---|
| A1 | No repo or L1 document asserts sub-8 ms as fact |
| A2 | Gate runner fails a blown feature budget, with mutation evidence |
| B1 | Written answer on dual-DIN wiring, Captain-confirmed |
| B2 | Byte counts from both taps on the same frame |
| B3 | Both strips correct on both units, identity verified |
| B4 | Dated capture directory + diff against the 2026-09-10 baseline |
| B5 | Restamped contract + requalification, or explicitly skipped |
| B6 | A named Captain promotion decision, or the branch stays a probe lane |

## Open questions for Captain

1. **Is the RPL's dual-DIN actually wired to the strips, and at which pixel?**
   B1 exists to answer this, but if you already know, it skips a phase.
2. **Do you want sub-8 ms at all,** given 11.6 ms is already imperceptible and B5
   costs a locked-architecture change? Default in this brief is no.
3. **What is the published latency figure?** Recommendation: **11.6 ms,
   hardware-verified** — 2.3× better than the 26.4 ms that made you reject the
   "≤20 ms" copy, and it meets your own rule that only hardware-verified numbers
   go into marketing.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-09-10 | agent:claude-code | Created — phased brief for the LED lane split, written against the same-day hardware latency baseline. |
