---
abstract: "Red-team timing/systems attack on the dual-K1 sync draft plan (v0.1). Two KILL-class findings: (1) the sync scheme as specified violates its own identical-inputs contract — the leader renders fresh 133 Hz state and quantised PLL phase while the follower renders 66 Hz delayed reconstruction with dead-reckoned phase, a systematic mismatch up to ~22.5 ms ≫ the 10 ms budget; (2) the Phase-0 gate measures raw transport p95 against the seam budget, the wrong quantity under timestamped replay — as written it fails both bake-off candidates on the plan's own numbers. Plus 66 Hz sits inside ESP-NOW's documented <20 ms collapse regime, and 'Core 0 stays clean' is unachievable (BT controller + WiFi tasks pinned to Core 0 in the precompiled framework sdkconfig). Topology and geometry survive; the wire protocol and gate definitions need rework."
---

# Red-Team — Timing / Systems Lens (dual-K1 sync draft v0.1)

Attacker stance: the plan is wrong until it survives. All attacks verified against real
source or the lane's own evidence files; labels: **[FACT]** = cited file:line or measured
doc, **[DERIVED]** = arithmetic from cited facts, **[EXTERNAL]** = provisional external
number (the plan's own [SEARCH]-tagged evidence).

Verified code facts this review rests on:

- `led_thread` is created with `xTaskCreatePinnedToCore(..., tskIDLE_PRIORITY + 1, ..., SB_LED_TASK_CORE)` with `SB_LED_TASK_CORE = 1` — render runs on Core 1 at the **lowest application priority** (`SPECTRASYNQ_K1_FIRMWARE.ino:705-706`, `:106-107`). [FACT]
- Wireless/BLE polls run on the Core-0 audio loop today (`ino:815-820`). [FACT]
- Precompiled pioarduino framework sdkconfig (`~/.platformio/packages/framework-arduinoespressif32-libs/esp32s3/sdkconfig`): `CONFIG_BT_CTRL_PINNED_TO_CORE=0` and `CONFIG_ESP_WIFI_TASK_PINNED_TO_CORE_0=y`. The BLE **controller** task and the WiFi task are pinned to **Core 0** and are not movable without a custom framework build; only the NimBLE **host** task (source-built, `CONFIG_BT_NIMBLE_PINNED_TO_CORE`) and the application sync task can be placed on Core 1. [FACT]
- AP frame = 96 samples @ 12.8 kHz = 7.5 ms; tempo/PLL phase emits at 44.444 Hz → 22.5 ms phase quantisation (`sb_tempo.cpp:43`; findings/sync-timing.md §0). [FACT]
- Apparent-motion doc measures **fusion (36–60 ms interval)** and **correspondence (28–32 px)** — it contains **no seam/displacement-detection measurement**; the sync-timing evidence itself labels the displacement threshold [EXTERNAL, unmeasured through the LGP] (`docs/measurements/apparent-motion-on-k1.md` §8; findings/sync-timing.md §4). [FACT]
- ESP-NOW buffering pathology: 140 B packets at <20 ms spacing → avg 50 ms / max 200 ms; >20 ms spacing → 5–6 ms (findings/prior-art.md, issue #115, marked [READ]). 66 Hz = **15.15 ms spacing**. [FACT + DERIVED]

---

## A1 · KILL — the scheme violates its own "identical inputs" contract

The plan's §1.1 defines the feature as *"give both devices identical inputs, flip one"*.
The scheme in §2 then gives the two devices **different inputs on different timelines**:

1. **Feature decimation mismatch.** The leader's effects consume `AudioSemanticState`
   fresh at 133 Hz; the follower receives a 66 Hz decimated stream. Even with perfect
   transport and perfect delay-matching, the follower's rendered features are up to one
   skipped AP frame (7.5 ms) staler than the leader's — **~1.4 px @185 px/s, ~70 % of the
   2 px budget consumed before a single microsecond of transport error is counted.** [DERIVED]
2. **Phase-signal mismatch.** The plan has the follower "dead-reckon beat phase from bpm
   between packets". The leader does not render a dead-reckoned smooth phase — it renders
   the PLL's emitted `phase01`, which steps at 44.4 Hz (22.5 ms quantisation,
   `sb_tempo.cpp:43`). A smooth follower phase against a stepped leader phase differs by
   **up to 22.5 ms systematically — 2.25× the entire seam budget**, worst on exactly the
   beat-locked modes the feature exists for. [DERIVED]
3. **No packet timestamps.** §2's wire protocol lists features, events + event-ids,
   control records and a clock beacon — **no leader-clock timestamp on feature packets or
   events**. Without timestamps the follower can only render "freshest received", so
   transport jitter translates 1:1 into seam offset and the delay-matching line item is
   unimplementable as specified: the leader delays by a constant p95 while the follower's
   applies are jitter-timed. [DERIVED]

**Failure scenario:** Waveform-class scroll (185 px/s), 120 BPM, BLE transport passing the
Phase-0 gate at p95 = 10 ms. Sum of the *systematic* errors above: 7.5 ms (decimation) +
up to 22.5 ms (phase signal) ≈ 2–5 px sustained kink at the seam, oscillating at the
44.4 Hz/66 Hz beat frequency — visible, and present even with a perfect radio.

**Fix (required, not fatal):** make replay the contract. Leader renders through the SAME
pipeline the follower does: a timestamp-indexed delay line of decimated feature snapshots
(leader buffers what it streams and renders snapshot T−D while the follower renders the
received snapshot T−D). Every packet and event carries a leader-clock timestamp. The
follower replays the leader's actual `phase01` sequence at leader time; dead-reckoning is
demoted to gap-filling between timestamped values, never an independent phase source.

---

## A2 · KILL — the Phase-0 gate measures the wrong quantity and fails both candidates on the plan's own numbers

Gate as written: *"one transport ≤ measured seam budget p95"* — i.e. raw transport p95
≤ ~10 ms. Two independent failures:

1. **Wrong quantity.** Under the (required, see A1) timestamped-replay design, transport
   latency does NOT appear at the seam — it is absorbed by the delay line. What appears at
   the seam is (a) **clock-offset estimation error** and (b) **tail lateness beyond the
   delay-line depth** (a packet later than D misses its render slot). Transport p95 only
   bounds D against the leader's <50 ms audio-to-LED budget:
   `7.5 ms mic chunk + ~2 ms AP compute + D + ≤5.4 ms frame + ~4.8 ms WS2812 wire-out (160 LED × 30 µs) < 50 ms → D ≤ ~30 ms`. [DERIVED]
   A transport with p95 = 25 ms and µs-class clock sync **passes the physics and fails the
   plan's gate**; a transport with p95 = 8 ms and 15 ms clock-offset error **passes the
   plan's gate and fails the seam**. The gate can both park a feasible feature and green a
   broken one.
2. **Both candidates already fail it on the lane's own evidence.** NimBLE notify median
   45 ms [EXTERNAL] > 10 ms; ESP-NOW at the plan's 66 Hz stream rate sits in the
   documented <20 ms-spacing collapse regime (avg 50 ms, A3). If the external numbers
   hold, Phase 0 as defined ends in "feature parks" against an architecture that is
   actually feasible once reframed.
3. **p95 leaves a defined 5 % failure rate with no specified behaviour.** At 66 Hz that is
   ~3.3 late packets/s. Follower policy on a late packet (hold-last vs drop) is nowhere
   stated; for scalar features hold-last is a ≤1-frame transient, but for edge events it
   is A7. Gate the **p99/p99.9 lateness against D**, not p95 against the seam budget.

**Fix:** redefine the Phase-0 gate as four measured numbers: (i) achievable clock-offset
error ≤ seam budget; (ii) p99.9 packet lateness ≤ D; (iii) leader end-to-end ≤ 50 ms with
D included; (iv) render-side health (A5). Keep "feature parks" as the honest outcome if
(i)–(iv) cannot be met by any candidate.

---

## A3 · MAJOR — 66 Hz puts ESP-NOW inside its own documented collapse regime

66 Hz = 15.15 ms packet spacing. The lane's own [READ] evidence (esp-now issue #115):
140 B packets at <20 ms spacing → **avg 50 ms / max 200 ms** delivery; >20 ms spacing →
5–6 ms. The plan's transport table even states the <20 ms collapse and that "33–50 Hz sits
at the edge" — then §2 specifies a 66 Hz stream. Candidate B is being sent into Phase 0
configured in its known-pathological regime. [FACT + DERIVED]

**Fix:** stream at 33.3 Hz (30 ms spacing) or batch two AP-decimated snapshots per packet
at 33 Hz packet rate; additionally distinguish the raw `esp_now_send()` API from the
esp-now *component* wrapper in the bake-off (issue #115 is against the component — the raw
API may not exhibit it; measure both). Events can ride the next scheduled packet or an
immediate out-of-band send spaced ≥20 ms from stream packets.

---

## A4 · MAJOR — "Core 0 stays clean" is unachievable on this framework

§2 asserts *"sync task + host stack targeted at Core 1 — Core 0 stays clean"*. The
precompiled framework sdkconfig pins `CONFIG_BT_CTRL_PINNED_TO_CORE=0` and
`CONFIG_ESP_WIFI_TASK_PINNED_TO_CORE_0=y` [FACT]. The BLE controller/link-layer task, the
WiFi driver task and the radio ISRs execute on **Core 0** regardless of where the NimBLE
host task is placed, and cannot be moved without a custom framework build (pioarduino
ships precompiled libs). Core-0 BLE contention has already produced a real DRAM crash on
this hardware (2026-07-05, fixed 1ac840a — findings.md §2). The architecture text
promises a guarantee the platform cannot deliver; the MabuTrace Core-0 AP p95 measurement
is the *actual* protection and must be framed as the load-bearing gate, with the
worst-case controller duty cycle (connection events + advertising/scanning + K718 dial
linked) in the Phase-0 matrix.

**Fix:** reword the claim to "movable stack components (NimBLE host, sync task) on Core 1;
controller/WiFi load on Core 0 is irreducible and is bounded by the measured Core-0 AP p95
gate". No architecture change needed — the honesty change prevents a false safety
assumption in Phase 4.

---

## A5 · MAJOR — Phase-0 gate has no render-side (Core 1) health criterion

The gate measures latency, jitter, loss, Core-0 AP p95 and heap — **nothing about the
render loop it proposes to co-locate the radio with**. Two concrete mechanisms:

1. **Priority inversion by design.** `led_thread` runs at `tskIDLE_PRIORITY + 1`
   (`ino:706`) — the lowest application priority. NimBLE host and LwIP/WiFi tasks default
   to high priorities and preempt it freely on Core 1. The budget table's "follower render
   window ≤10 ms" silently assumes the ~185 FPS cadence holds; nothing in Phase 0 verifies
   it under radio load. [FACT + DERIVED]
2. **RMT5 vs radio interrupts.** The K1 drives two 160-LED channels; ESP32-S3 RMT DMA is
   single-TX-channel class, so at least one channel's RMT refill is interrupt-timed.
   High-priority radio interrupts on the same core can starve refill → WS2812 latch
   glitches (the classic ESP32 radio+addressable-LED failure). Whether FastLED 3.10.3's
   RMT5 path runs DMA on either channel here is **unverified in this lane** — it must be,
   before "Core 1 placement" is treated as free. [DERIVED, verification owed]

**Fix:** add to the Phase-0 gate: render FPS floor (p95 frame time under radio load) and
an LED-glitch observation (eyes-on or logic-analyser) with the transport at full stream
rate. Cheap to add; catches a whole failure class the current gate is blind to.

---

## A6 · MAJOR — a 1 Hz one-way clock beacon cannot deliver seam-class offset accuracy over BLE

Offset estimation from **one-way** beacons has error of the order of the transport's
delay jitter. Over BLE that is ±1 connection interval (7.5–30 ms) [EXTERNAL — the lane's
own numbers]; min-filtering at 1 Hz converges over minutes, and §2's "forward-only slew"
slows acquisition further. A clock-offset error of even 7.5 ms consumes 75 % of the seam
budget on its own. Over ESP-NOW (~80 µs broadcast jitter, prior-art.md) the same beacon is
comfortably adequate — the mechanism is **transport-dependent** and the plan specifies it
transport-agnostically.

**Steel-man (attack that failed):** beacon *rate* is not the problem. ESP32-S3 crystal
tolerance is ±10–20 ppm per device → ≤40 µs/s relative drift; between 1 Hz beacons that is
µs-class. The plan's 1 Hz choice survives; the *estimator* is what is underspecified.

**Fix:** NTP-style two-way exchange (request/response RTT halving) in a burst at pairing
and after link recovery; beacon at 1 Hz for maintenance. Gate the achieved clock-offset
error in Phase 0 (this becomes gate quantity (i) of A2's fix).

---

## A7 · MAJOR — stale beat_tick recovery is named but not designed

`beat_tick` is a loss-permanent one-shot; the plan carries event-ids "for loss detection"
and re-anchors on beat_tick. Detection is not recovery: by the time a gap in event-ids is
observable, the missed tick is ≥1 packet interval (≥15 ms at 66 Hz, ≥30 ms at 33 Hz) stale
— beyond the seam budget by definition. Re-anchoring on a late-arriving tick **at its
arrival time** injects a phase error equal to its lateness; the follower "corrects"
itself into visible error on exactly the anchor event the scheme depends on.

**Fix (folds into A1's timestamp requirement):** every event carries its leader-clock
timestamp; the follower re-anchors to `tick_time + n·period` (back-dated), never to
arrival time; ticks older than half a beat period are discarded (the next on-time tick is
closer than any correction). This is standard dead-reckoning discipline and costs 4 bytes.

---

## A8 · MINOR — latency budget table omits wire-out and AP compute

§2's table stops at "follower render window ≤10 ms". WS2812 wire-out for 160 LEDs is
~4.8 ms (30 µs/LED) and AP compute is ~1–2 ms; both are common-mode across the seam (so
the seam maths is unaffected) but they belong in the leader's <50 ms audio-to-LED
accounting: at p95 = 10 ms delay-matching the total is ~30 ms (fine); at BLE-realistic
20–30 ms it is 45–50 ms — at the budget edge, which is exactly where an honest table
matters. [DERIVED]

## A9 · MINOR — the Phase-0 seam-threshold measurement is circular as scoped

The "two-device k1_motion_probe" that replaces the provisional 10 ms budget needs a
controlled, known inter-device offset — which requires a timing reference better than the
thing being measured. Running it over the radio under test conflates instrument and DUT;
the existing probe is also single-device (`mp_step`/`mp_flash` on one strip,
apparent-motion doc §1) and cannot present a seam-crossing stimulus at all.

**Fix:** wire a GPIO cross-trigger between the two bench units (sub-µs, radio-free) for
the perceptual measurement; extend the probe with a seam-crossing stimulus (one object
traversing strip A → strip B with commanded Δt). Small instrumentation task, but it must
be scheduled or Phase 0's "measured seam budget" input never materialises.

## A10 · MINOR — bake-off candidate A locks NimBLE against the lane's own evidence

prior-art.md's [READ] benchmark: Bluedroid notify median **14.6 ms** vs NimBLE **45 ms**.
The plan carries only NimBLE (the existing dependency) into the bake-off. If the 3×
penalty is real on K1, candidate A fails for a stack-choice reason, not a physics reason,
and the matrix has no Bluedroid fallback row. Cheap fix: permit a Bluedroid variant as
candidate A′ if NimBLE misses the (redefined) gate.

---

## Steel-man honesty — what the draft gets right under this lens

- **Rejecting dual-mic on the 22.5 ms PLL quantisation is sound.** Two independent PLLs
  cannot be held inside any plausible seam budget with corrections capped at 0.10
  beat/step; and under leader-follower the same 22.5 ms quantisation becomes common-mode
  (both halves render the same value) — the draft's core topology argument survives attack.
- **Pixel-streaming rejection maths is correct.** 480 B/frame at the measured ~185 FPS is
  88.8 kB/s per half — outside BLE application throughput with any headroom; the plan's
  numbers reproduce.
- **bpm-quantisation dead-reckoning drift is negligible** (u16 bpm at 0.1 BPM resolution
  → <1 ms accumulated phase error per beat interval). My accumulation attack failed; the
  dead-reckoning problem is *whose phase signal* is authoritative (A1.2), not arithmetic
  drift.
- **1 Hz beacon rate is adequate for oscillator drift** (µs/s class — see A6 steel-man).
- Targeting the *movable* stack components at Core 1 is the right direction (A4 corrects
  the overclaim, not the intent).

## Missed considerations (not in the draft at all)

1. **Join/rejoin acquisition window UX:** clock-sync acquisition + delay-line fill takes
   finite time; what the follower displays during acquisition (own-mic? black? last
   state?) is unspecified — same class as the link-loss stance §2 does cover.
2. **Scheduled control execution:** mode switches / crossfades must execute at a *future
   leader timestamp* ("switch at T"), or the two halves transition ~one transport delay
   apart — a whole-display event far more visible than a seam kink. The control mirror as
   drafted replays commands on arrival.
3. **FastLED RMT5 DMA-vs-interrupt mode on S3 with two channels** — unverified; feeds A5.
4. **The seam budget could tighten, not just loosen:** displacement/vernier detection at a
   fixed, known seam location is hyperacute in general vision; if the LGP blur does not
   raise it above ~1 px, the measured budget could come back ≤5 ms — the plan should state
   that Phase 0 may return a *harder* number and that the gate maths must be re-run
   against it, not only relaxed.

---
**Document Changelog**
| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code (red-team timing SSA) | Created — timing/systems red-team of draft v0.1: 2 KILL (identical-inputs violation; Phase-0 gate mismeasure), 5 MAJOR (ESP-NOW 66 Hz collapse, Core-0 pinning overclaim, missing render-health gate, one-way beacon estimator, stale beat_tick), 3 MINOR, steel-man items, 4 missed considerations. Code facts verified against ino:705-706/815-820, framework sdkconfig, apparent-motion doc, prior-art evidence. |
