---
abstract: "Full transfer-test gamut, 2026-08-12, both IM69D units on 68dd8d25 side by side facing the Bose. RESULT: music response is statistically identical (Unit2/bench 0.92, p=0.67, n=179 each) but Unit 2's QUIET state runs 1.54x hotter across three paired legs. Signal unaffected, noise added in quiet only. 1.25 x 1.67 = 2.09 predicts the observed 2.50/1.25 = 2.00 fraction ratio. LED-current coupling ruled out within-device by a 320px/412px A/B. Level tracks SPL 5.9x while peakiness is flat 1.02x, so the level fraction is placement-sensitive by construction and peakiness is not. Two live candidates remain: long PDM link noise, or an SSL learned at Unit 2's previous placement. Discriminator is an in-situ recalibration, which needs a spoken silence-go."
---

# Transfer test — full gamut, both units, 2026-08-12

**Devices:** Unit 2 `0C54FC00` (dual IM69D130, 206+206 px) and bench K1v2 `B489A500`
(IM69D130, 160+160 px), both on `68dd8d25`, **side by side facing the Bose**.
**Captain's context, given mid-session and load-bearing:**

1. In every previous calibration/test event the two mic boards were **more than a
   foot apart**. They were moved side by side only recently.
2. Unit 2 has **2× longer wiring** between the S3 and the dual-IM69D130 board.

Both facts changed the analysis. Neither was known when the lane derived its numbers.

## What was run

| Leg | Duration | Stimulus | Purpose |
|---|---|---|---|
| quiet ×4 | 45–90 s | none | noise floor + tail shape |
| ladder | 12 s ×3 | vol 40/55/70 | confirm the acoustic path lands |
| music ×2 | 45 s | vol 40, 55 | specified transfer legs |
| long | 180 s | vol 55 | statistical power (n=179/unit) |
| sweep | 60 s ×3 | vol 40/55/70 | level vs peakiness SPL sensitivity |
| LED A/B | 90 s ×3 | quiet | 320 px vs 412 px, within-device |

Both units captured **concurrently in every leg** — same room, same stimulus, same
wall-clock window — so the pairing cancels room variation. Witness mic resolved **by
name** each run (index 1 was the Bose's own mic; the hardcoded-index trap is live).
**No calibration was fired on either unit.**

## Result 1 — under music the two units are indistinguishable

180 s at vol 55, n=179 each:

| | value |
|---|---|
| Unit2/bench median-ratio | **0.920** |
| bootstrap 95% CI | **[0.730, 1.200]** |
| Mann-Whitney | z = −0.43, **p = 0.670** |
| quantile agreement p10→p95 | 0.895 – 1.217 |

The per-unit hypothesis, as originally framed, requires a device factor near **2.00×**
(fraction 1.25 vs 2.50). That is far outside the interval.

**Under music, Unit 2 is not less sensitive. Its raw `rms_raw` matches the bench's.**
This kills "loss of sensitivity" as a description of the defect.

## Result 2 — under QUIET the two units differ, consistently

Three paired quiet legs, room cancelled by pairing:

| build | witness max | Unit2 med | bench med | **Unit2/bench** |
|---|---|---|---|---|
| 320 px | −30.1 dBFS | 1.06× | 0.71× | **1.49** |
| 412 px | −49.0 dBFS | 0.92× | 0.62× | **1.47** |
| 320 px | −27.8 dBFS | 0.92× | 0.56× | **1.65** |

**Mean 1.54, stable across a 21 dB swing in room transients and across both LED
geometries.** Note also that as the room quietened over the session the bench's quiet
median followed it down (1.17× → 0.56×) while Unit 2's did not (1.06× → 0.92×):
**Unit 2 has a device-local noise floor that does not track the room.**

## Result 3 — the contrast is the whole answer

```
QUIET   Unit2/bench = 1.54
MUSIC   Unit2/bench = 0.92        (p=0.67, not distinguishable)
                      -----
        quiet runs   1.67x hotter than music would predict
```

The silence fraction is a threshold on exactly that quiet-vs-music separation, so:

```
bench fraction  1.25  x  1.67  =  2.09        derived Unit 2 fraction: 2.50
observed fraction ratio         2.50 / 1.25  =  2.00
```

**2.09 predicted against 2.00 observed.** The fraction delta is fully accounted for
by Unit 2's elevated quiet floor. It was never a property of the unit's *sensitivity*.

**Signal unaffected, noise added in the quiet state only.** That is the signature of
noise entering at the **link**, not at the capsule — which is what a digital PDM
interface does when it degrades: bit errors add noise, they do not scale amplitude.
Consistent with Captain's 2× longer run. Not consistent with lost sensitivity.

## Result 4 — LED current is not the aggressor (within-device, paired)

| geometry | Unit2/bench paired ratio |
|---|---|
| 320 px (`K1_UNIT2_LED160_AB`) | 1.49, 1.65 |
| 412 px (production) | 1.47 |

The two *same-geometry* legs differ from each other by more than either differs from
the other geometry. **Candidate (a), LED-supply coupling, is not supported** — tested
within-device on the same silicon, capsule and pins, which is a stronger design than
the between-device comparison.

## Result 5 — why the fraction could never transfer but the peakiness gate could

Across a 17.3 dB source change (7.3× amplitude):

| statistic | Unit 2 | bench | behaviour |
|---|---|---|---|
| level `max_raw/SSL` | 3.10× → 16.58× (**5.3×**) | 2.33× → 13.86× (**5.9×**) | **tracks SPL** |
| peakiness `pky` | 2.46 → 2.76 (**1.12×**) | 2.55 → 2.60 (**1.02×**) | **flat** |

A placement change *is* an SPL change at the capsule. Whatever tracks SPL tracks
placement. **The level term is ~5× more SPL-sensitive than peakiness**, so a constant
level fraction cannot survive a placement change and a peakiness threshold can.

That is why canon's peakiness 2.10 transferred across units while 1.25/2.50 did not,
and it is a structural property of the two statistics — not a tuning accident.

## Two live candidates, and the one test that separates them

Both fit every number above:

**(A) Long PDM link adds device-local noise.** Captain's wiring fact. Predicts an
elevated floor that does not follow the room down — which is observed.

**(B) Unit 2's SSL is stale for its current placement.** `SSL=136` was learned at the
*previous* position, a foot away. If that spot was quieter, SSL sits low, every ratio
inflates proportionally, and the fraction has to rise to compensate. Captain's
placement fact. Also predicts everything observed.

**Discriminator — in-situ recalibration of Unit 2:**

- If SSL rises to match its actual floor and the ratios collapse onto the bench's →
  **(B)**, a calibration-staleness problem, fixed by calibrating at final placement.
- If SSL rises but the **tail stays fat** relative to the bench → **(A)**, real added
  noise, and a hardware fix (shorter or shielded run, series termination, return-path
  and grounding review) rather than a firmware constant.

`start_noise_cal` is Captain-verbal-gated and was **not** fired. This test needs a
spoken silence-go. It is the single remaining action that closes the question.

One incidental datum worth a look during that work: the DC offsets differ sharply —
Unit 2 `DC=-220`, bench `DC=+137`.

## Corrections made during this session, recorded rather than quietly fixed

1. **"Therefore per-room" was wrong.** The first side-by-side result was read as
   proving the fraction is per-room. Side by side holds placement *constant*, so the
   experiment was structurally blind to the very effect Captain then named. Ruling out
   per-unit under identical acoustic input was valid; the per-room inference was not.
2. **"Per-unit is ruled out" was also wrong**, and this document reverses it. That
   claim rested on the *music* legs alone. The difference lives in **quiet**, which the
   music comparison cannot see. Per-unit is back, with a corrected mechanism.
3. **Two LED A/B legs were nearly compared across a 19 dB room change.** The bench
   control caught it. Any LED conclusion drawn from that pair would have been room
   noise wearing an LED costume.
4. **`[AP]` telemetry is command-gated**, and the dispatcher is `type=value`:
   `:ap_stream 1` returns `Bad command`, `:ap_stream=1` works. `ap_capture` *is*
   `#if ENABLE_AP_STREAM`-gated and absent from these envs; `ap_stream` is
   unconditional and present. Reading only the first fact yields the false conclusion
   that these builds cannot emit telemetry at all — briefly drawn and retracted.
5. **A sleep-then-read serial capture returns zero frames** on a live streaming device
   because the OS buffer overflows. Read continuously.

---
**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-08-12 | agent:claude-code | Created at the close of the full transfer-test gamut. Records the music/quiet contrast that explains the fraction delta, the within-device LED A/B, the level-vs-peakiness SPL sensitivity, the two remaining candidates and the recalibration discriminator, plus five corrections made during the session. |
