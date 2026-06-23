---
abstract: "Adversarial read-only backtest of whether K1 SensoryBridge's CRGB16/SQ15x16 visual pipeline produces meaningful LED-level value on 8-bit WS2812 output. Finds that the broad '16-bit colour precision' claim is overclaimed because many colour sources are already born 8-bit and all WS2812 frames are final 8-bit GRB bytes. Finds, however, that CRGB16 can be visually load-bearing in stateful history, fade, fractional transport, and temporal-dither paths because it changes final byte sequences over time. Recommends keeping high precision only where final-byte or trail metrics prove value, and adding a paired final-byte probe before any simplification."
---

# CRGB16 vs WS2812 Value Backtest

| Field | Value |
|---|---|
| Date | 2026-05-26 |
| Repo | `/Users/spectrasynq/SensoryBridge-main 9` |
| Mode | Read-only analysis. No firmware edit, no serial, no upload, no commit. |
| Current source head observed | `36d305e fix(gate): vp_diff magnitude-aware for fp-tolerant modes` |
| Question | Does upstream `CRGB16`/`SQ15x16` precision produce quantifiable visual value on 8-bit WS2812 LEDs? |
| SSA coverage | Reality-check, FastLED colour, and test-plan lanes completed. One source-trace lane timed out and was abandoned. |
| Evidence tiers | Local source, local FastLED source, WS2812B datasheet, offline numerical model. Not runtime proof. |

## 1. Doctrine Gate

### Relevant Rules

- [FACT] Architecture does not count as success if musical responsiveness, independent dual-channel behaviour, colour clarity, motion memory, or visual captivation regresses. Source: `AGENTS.md`.
- [FACT] Visual pipeline changes must preserve centre-origin behaviour, no heap in render, 120 FPS / 2.0 ms render ceiling, dt-correct smoothing, and sub-8 ms audio-to-visual latency. Source: `AGENTS.md`.
- [FACT] Agents must not open the serial port, and compile/upload are not runtime proof. Source: `AGENTS.md`.

### K1 Evidence Touched

- [FACT] `CRGB16` stores `SQ15x16 r/g/b`. Source: `SPECTRASYNQ_K1_FIRMWARE/constants.h:141-144`.
- [FACT] `SQ15x16` resolves to `SFixed<15, 16>`. Source: `libraries/FixedPoints/src/FixedPointsCommon/SFixedCommon.h:22`.
- [FACT] Final output buffers are FastLED `CRGB*` buffers. Source: `SPECTRASYNQ_K1_FIRMWARE/globals.h:233-234`, `SPECTRASYNQ_K1_FIRMWARE/globals.h:599-601`.
- [FACT] Primary output quantisation writes `uint8_t` channel values into `leds_out[]`. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:280-338`.
- [FACT] `show_leds()` applies brightness, clip, scale, quantisation, optional FastLED dither selection, then calls `FastLED.show()`. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:739-882`.

### North-Star Impact

- [INFERENCE] If `CRGB16` only changes upstream mathematical purity and not final LED-byte sequences, temporal output, centre-of-mass, energy, trail half-life, saturation, or Captain-visible behaviour, it is not product value.
- [INFERENCE] If `CRGB16` preserves low-level trails and fractional transport that an 8-bit state path drops, then it is not bit-depth theatre even though the final LEDs are 8-bit.

## 2. Hardware Ceiling

- [FACT] WS2812B output is 24-bit GRB: 8 bits for green, 8 bits for red, 8 bits for blue. The datasheet states each pixel receives 24-bit data in `G7..G0 R7..R0 B7..B0` order and each primary colour has 256 brightness levels. Source: Worldsemi WS2812B datasheet via Mouser, lines 7 and 102-104 in the retrieved PDF.
- [FACT] K1 registers WS2812B strips with GRB order. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:918`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:1774`.
- [FACT] FastLED `CRGB` and `CHSV` are 8-bit component types. Source: `.pio/libdeps/k1_hardware/FastLED/src/crgb.h:85`, `.pio/libdeps/k1_hardware/FastLED/src/fl/hsv.h:14-30`.

[INFERENCE] Therefore, `CRGB16` cannot produce 16-bit instantaneous LED output. The only possible gains are:

1. Better final 8-bit byte choices after multiple operations.
2. Better temporal byte sequences across frames.
3. Better sub-LSB averages through temporal dithering.
4. Better state retention in fades, trails, fractional shifts, interpolation, or accumulation.

## 3. Where The Precision Collapses

| Path | Evidence | Verdict |
|---|---|---|
| HSV hue source | `hsv()` converts `SQ15x16 h/s` into `CHSV(uint8_t(...))` before lifting to `CRGB16`. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:76-82`. | [INFERENCE] High-precision hue is mostly theatre here; hue and saturation are quantised to FastLED's 8-bit `CHSV`. |
| Palette source | `ColorFromPalette()` returns 8-bit `CRGB`, then K1 converts it into `CRGB16`. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:113-128`; FastLED source `.pio/libdeps/k1_hardware/FastLED/src/fl/colorutils.h:1508-1529`. | [INFERENCE] Palette source colour is already 8-bit. `CRGB16` can still preserve later scaling/fading, but not add original palette bit-depth. |
| Bloom colour forcing | Bloom converts fixed colour to `CRGB`, calls `force_saturation()` / `force_hue()`, then converts back to `CRGB16`. Source: `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp:60-71`. | [INFERENCE] This is a clear round-trip precision loss and a prime simplification target. |
| Final output | `quantize_color()` writes `uint8_t` channels into `leds_out[]`. Source: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:280-338`. | [FACT] Final per-frame precision is 8-bit per channel. |

## 4. Where The Precision Can Survive

| Path | Evidence | Why it can matter |
|---|---|---|
| Bloom history and fractional transport | Bloom transports the previous `CRGB16` frame via `draw_sprite()` with fractional position and alpha, then stores history before display-only fade/mirror. Sources: `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp:7-14`, `SPECTRASYNQ_K1_FIRMWARE/light_mode_bloom.cpp:88-112`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:1586-1628`. | Sub-byte fractions can survive across frames and later cross 8-bit thresholds. |
| Waveform trail memory | Waveform Fast fades the global `leds_16` trail by fixed-point `dynamic_fade_amount`, shifts it, and inserts a centre-origin dot. Source: `SPECTRASYNQ_K1_FIRMWARE/light_mode_waveform_fast.cpp:129-163`. | Low-level trails can persist longer than an 8-bit state buffer. |
| Brightness and soft clip | `show_leds()` scales brightness and runs hue-preserving soft clip before final quantisation. Sources: `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:238-278`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:92-127`. | Fractional channel ratios can affect the final byte after compression/scaling. |
| Temporal dithering | `TEMPORAL_DITHERING` defaults true, and `quantize_color()` uses fractional parts against a 4-entry table. Sources: `SPECTRASYNQ_K1_FIRMWARE/globals_config.cpp:75`, `SPECTRASYNQ_K1_FIRMWARE/led_utilities.h:280-328`, `SPECTRASYNQ_K1_FIRMWARE/constants.h:334-338`. | Fractional values below one byte can become time-averaged output pulses. |

## 5. Offline Quant Backtest

### Method

[FACT] I ran an offline numerical model in this session. It did not edit files and did not touch hardware. The model compared:

- `CRGB16-like` state: float/fixed-like state carried over frames, quantised only at output.
- `8-bit state` alternative: each frame's state is quantised to an 8-bit byte, lifted back to 0..1, then used by the next fade/shift step.

[INFERENCE] This is not a complete firmware simulator. It is a targeted falsification model for the core claim: whether high-precision history can change final LED bytes on an 8-bit output device.

### Results

| Scenario | Frames with any final-byte difference | p95 max byte diff | Peak difference | Last nonzero frame: high precision vs 8-bit state | Verdict |
|---|---:|---:|---|---|---|
| Bloom-like fractional shift, alpha `0.99`, shift `0.25 LED/frame` | 263 / 361 | 16 | frame 49: high precision energy 146 bytes vs 0 bytes in 8-bit state; max byte diff 20 | 265 vs 48 | [INFERENCE] Strong evidence that high-precision history can materially affect visible trail persistence. |
| Bloom Fast-like fractional shift, alpha `0.99`, shift `0.50 LED/frame` | 175 / 361 | 15 | frame 44: high precision energy 155 bytes vs 0 bytes; max byte diff 19 | 178 vs 43 | [INFERENCE] Strong trail-memory value. |
| Waveform idle fade, alpha `0.85` | 33 / 361 | 2 | frame 9: byte 59 vs 56; max diff 3 | 34 vs 25 | [INFERENCE] Modest value. Probably not worth global complexity by itself. |
| Reactive fade, alpha `0.96` | 134 / 361 | 10 | frame 71: byte 14 vs 1; max diff 13 | 135 vs 71 | [INFERENCE] Meaningful if this corresponds to a visible trail state. |
| Slow memory fade, alpha `0.99` | 358 / 361 | 42 | frame 168: byte 47 vs 0; max diff 47 | beyond 360 vs 167 | [INFERENCE] Very strong evidence for high-precision state in slow-decay trails. |

### Dither Micro-Test

The default K1 dither path multiplies by `254`, floors, then applies thresholds `0.25`, `0.50`, `0.75`, `1.00`.

| Normalised value | Non-dither byte | 4-frame dither sequence | Average byte |
|---:|---:|---|---:|
| `1/1024` | 0 | `0,0,0,0` | 0.00 |
| `1/512` | 0 | `1,0,0,0` | 0.25 |
| `1/256` | 0 | `1,1,1,0` | 0.75 |
| `1/255` | 1 | `1,1,1,0` | 0.75 |
| `0.005` | 1 | `2,1,1,1` | 1.25 |

[INFERENCE] This proves that fractional `CRGB16` values can affect final byte sequences through temporal dithering, but it also exposes a weirdness: a value near `1/255` averages lower in the dither path than the simple non-dither truncation. Also, a clamped `1.0` channel emits 254, not 255, in the default dither branch because `decimal = value * 254` has zero fraction at full scale.

## 6. Existing VP Gates Do Not Answer This Question

- [FACT] `vp_probe_hash_leds()` hashes `CRGB16` after 16-bit quantisation, not final WS2812 bytes. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:352-378`.
- [FACT] `frame_dump_tick()` emits COM, energy, and hash from `leds_16` before `show_leds()`. Source: `SPECTRASYNQ_K1_FIRMWARE/lightshow_modes.h:391-423`; call site `SPECTRASYNQ_K1_FIRMWARE/SPECTRASYNQ_K1_FIRMWARE.ino:600`.
- [FACT] `:vp_perf` is timing telemetry, not visual equivalence. Source: `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:409-462`, `SPECTRASYNQ_K1_FIRMWARE/serial_menu.h:2799-2864`.

[INFERENCE] Current gates protect the current upstream numeric surface. They do not prove that upstream precision reaches the actual LED-level output.

## 7. Adversarial Verdict

[INFERENCE] The broad defence of `CRGB16` as "higher precision colour" is mostly overclaimed. WS2812 output is 8-bit per channel, and many K1 colour sources already quantise through FastLED `CHSV`, `CRGB`, or `ColorFromPalette()` before re-entering `CRGB16`.

[INFERENCE] The narrow defence of `CRGB16` as a history/transport accumulator is legitimate. The offline backtest shows final-byte differences that are far larger than one LSB in slow fade and fractional shift scenarios. On stateful trails, an 8-bit state path can die hundreds of milliseconds or seconds earlier than a high-precision state path.

[INFERENCE] Therefore, `CRGB16` should not be treated as sacred globally, but it also should not be ripped out globally. The correct position is:

1. Keep high precision in stateful trail/history/fractional transport paths until a final-byte A/B proves it unnecessary.
2. Challenge and simplify stateless colour generation paths that bounce through `CHSV`/`CRGB` and back.
3. Stop using pre-output 16-bit hashes as proof of visible value.
4. Add a final-byte paired probe before deciding whether to collapse large parts of VP to `CRGB`.

## 8. Quantified Decision Thresholds

Treat an 8-bit alternative as visually equivalent only if all of these pass against final output bytes:

| Metric | Equivalence threshold |
|---|---:|
| Mean absolute byte error | `<= 0.5` |
| p95 absolute byte error | `<= 1` |
| Max byte error | `<= 8`, unless isolated and visually irrelevant |
| Changed RGB channel percentage | `<= 2%` over sustained windows |
| Energy delta | p95 `<= max(2%, 50 byte-energy units)` and worst-frame `<= 5%` |
| Centre-of-mass delta | median `<= 0.25 LED`, p95 `<= 1.0 LED` |
| COM slope delta | `<= 5%` |
| Trail zero-crossing delta | `<= 2 frames` |
| Low-light tail integral delta | `<= 10%` |
| Timing | render max `<= 2.0 ms`, frame max `<= 8.333 ms`, no over-budget/dropped frames |

[INFERENCE] If an 8-bit path passes these thresholds and improves render/quant timing materially, CRGB16 is expendable for that mode or helper. If it fails tail, COM, energy, or byte-sequence thresholds, CRGB16 is buying real output behaviour despite 8-bit LEDs.

## 9. Future Probe Contract

Applying the API-design skill to the future diagnostic contract: if a paired probe is added, it should be versioned, stable, and resource-like rather than a one-off debug print.

Suggested serial packet family:

```text
VPAB,ver=1,mode=7,frame=42,scenario=trail,mae8=0.73,p95_abs8=2,max_abs8=13,changed_pct=4.6,energy_a=812,energy_b=764,com_a=79.2,com_b=78.9,tail_a=135,tail_b=71
```

Rules:

- [INFERENCE] Version every packet with `ver=1`.
- [INFERENCE] Add fields only; do not silently change field meaning.
- [INFERENCE] Emit final-byte metrics after the same quantisation boundary used for `leds_out[]`.
- [INFERENCE] Keep pre-output `CRGB16` metrics separate from final-byte metrics.
- [INFERENCE] Do not display the 8-bit shadow path during measurement unless explicitly requested; it should be a probe, not a visual mode.

## 10. Recommended Next Action

[INFERENCE] Do not make a global `CRGB16` removal decision during the active refactor. Run a Level 1 paired final-byte probe design instead:

1. Target one history-heavy mode: Bloom or Waveform Fast.
2. Emit current final `leds_out[]` metrics and a quantise-early shadow path from identical seeded state.
3. Compare byte error, energy, COM, trail half-life, and timing.
4. Use Captain visual capture only after the final-byte metrics show a plausible difference.

The likely end-state is not "all `CRGB16`" or "all FastLED `CRGB`". It is a split: high precision for stateful visual memory; simpler 8-bit/FastLED-native helpers for stateless colour source work.

## Changelog

| Date | Change |
|---|---|
| 2026-05-26 | Initial adversarial backtest and SSA consolidation. |
