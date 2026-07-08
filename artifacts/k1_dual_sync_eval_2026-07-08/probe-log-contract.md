---
abstract: "Phase-0 dual-K1 sync probe: GPIO cross-trigger pin audit + shared serial log-line contract. Audits both K1 pinmaps (main K1 prod: LED 6/7, SPH0645 I2S 13/11/14; bench K1: LED 4/5, IM73D PDM clk13/din12/LR14) against constants.h and proposes TRIG_OUT=GPIO15, TRIG_IN=GPIO16 — provably unused on BOTH maps, non-strap, non-USB, non-flash/PSRAM. Includes physical cross-wiring instructions for Captain and the canonical serial log-line grammar shared by P0.4 firmware and the scripts/dual_sync_probe/ oracle."
---

# Phase 0 — Probe pin audit + serial log-line contract

Lane authority: [`phase0-plan.md`](./phase0-plan.md) (P0.3). Transport ratified: [`f2-transport-decision.md`](./f2-transport-decision.md).
This document fixes two things the oracle and the P0.4 firmware must agree on: **which two GPIOs carry the wired cross-trigger**, and **the exact serial log grammar** that turns two captured device logs into the four Phase-0 gate numbers.

British English throughout. `artifacts/` in a path is a literal directory name, not a spelling.

## 1. Pin audit

### 1.1 What each device already uses

Both K1 units are the **same** ESP32-S3-DevKitC-1 N16R8 devboard (16 MB quad flash + 8 MB **octal/OPI** PSRAM); only the firmware pin map and the mic differ. Pin macros live in `SPECTRASYNQ_K1_FIRMWARE/system/constants.h` under `#if defined(SB_K1_HARDWARE)` (the K1 block), switched by `SB_K1_BENCH_REFERENCE_PINMAP`.

**Main K1 (leader — production pinmap, SPH0645 I2S):**

| Function | GPIO | Source |
|---|---|---|
| WS2812 primary / secondary (LED_DATA / LED_CLOCK) | 6, 7 | `constants.h:329-330` |
| SPH0645 I2S BCLK / LRCLK / DIN | 13, 11, 14 | `constants.h:325-327` |
| I2C SDA / SCL (M5ROTATE8 encoder bus) | 17, 18 | `constants.h:345-346` |
| RNG seed / raw output | 8 | `constants.h:357`, also `audio/audio_transfer.h:172` (`pinMode(8, OUTPUT)`) |
| Physical controls + sweet-spot LEDs | −1 (disabled) | `constants.h:348-355` |

Main K1 occupied set: **{6, 7, 8, 11, 13, 14, 17, 18}**.

**Bench K1 (follower — bench-reference pinmap, IM73D122 PDM mic):**

| Function | GPIO | Source |
|---|---|---|
| WS2812 primary / secondary | 4, 5 | `constants.h:310-311` |
| IM73D PDM CLK / DIN / LR (active under `K1_MIC_IM73D_PDM_V1`) | 13, 12, 14 | `constants.h:318-320`; driven output at `audio/i2s_audio.h:226` |
| SPH0645 I2S pads (defined but UNUSED under the PDM flag) | 14, 12, 13 | `constants.h:306-308` (macros retained, not driven) |
| I2C SDA / SCL | 17, 18 | `constants.h:345-346` |
| RNG seed / raw output | 8 | `constants.h:357`, `audio/audio_transfer.h:172` |
| Physical controls + sweet-spot LEDs | −1 (disabled) | `constants.h:348-355` |

Bench K1 occupied set: **{4, 5, 8, 12, 13, 14, 17, 18}**.

The encoder is an **I2C** peripheral on 17/18 (`persistence/encoders.h:67` toggles `SCL_PIN`), not a dedicated GPIO — no extra pins to avoid there. Buttons (`system/system.h:377,380`) read `noise_button.pin` / `mode_button.pin`, both `−1` on K1, so no button GPIO is live.

**Union occupied across BOTH devices: {4, 5, 6, 7, 8, 11, 12, 13, 14, 17, 18}.**

### 1.2 Reserved / unsafe pins on ESP32-S3 N16R8 (must also avoid)

- **Strapping pins:** 0, 3, 45, 46 (boot mode / JTAG-source / VDD_SPI voltage / boot strap). Driving these at reset is unsafe. (Per brief; ESP32-S3 strapping spec.)
- **Native USB D−/D+:** 19, 20 — the CDC serial path we depend on for log capture.
- **Default UART0 TX/RX:** 43, 44 — avoid so no serial/boot-log path is disturbed.
- **On-board addressable RGB LED:** 38 (DevKitC-1 v1.1) / 48 (v1.0) — board-revision dependent, so avoid **both** 38 and 48.
- **SPI flash + OPI PSRAM:** GPIO **26–37** are consumed by the quad flash (26–32) *and* the octal PSRAM (33–37) on N16R8. The brief cites "26–32"; the non-K1 devkit branch of `constants.h:363-368` reuses 33–37 for a *different* board, which confirms 33–37 are the OPI data lanes on the S3 and are unavailable here. Treat all of **26–37** as forbidden.
- ESP32-S3 has no GPIO 22–25 (they do not exist on this part).

### 1.3 Proposed trigger pins

Free, interrupt-capable, and unreferenced on **both** pinmaps:

| Device | Role | TRIG_OUT | TRIG_IN |
|---|---|---|---|
| Main K1 (`k1_sync_probe_main`, leader) | leader | **GPIO 15** | **GPIO 16** |
| Bench K1 (`k1_sync_probe_bench`, follower) | follower | **GPIO 15** | **GPIO 16** |

Same pin numbers on both units because the devboards are identical and neither map touches 15 or 16.

**"Unused" proof — GPIO 15 and GPIO 16 appear in NO pin macro and NO GPIO call in the firmware tree.** A whole-tree grep of `SPECTRASYNQ_K1_FIRMWARE/` for pin/GPIO uses of 15 or 16 (across `#define *_PIN`, `pinMode`, `digitalRead/Write`, `attachInterrupt`, `gpio_*`, `GPIO_NUM_*`) returns zero hits; the only occupied pins are the union set in §1.1. Both are valid ESP32-S3 GPIOs (ADC2_CH4 / ADC2_CH5), non-strapping, outside the USB, UART0, RGB-LED and flash/PSRAM ranges, and support GPIO interrupts (all S3 GPIOs do). ADC2 is unused by this firmware and irrelevant to digital I/O; BLE (not WiFi) is the radio, so there is no ADC2/WiFi contention.

### 1.4 Physical wiring (for Captain)

Two signal jumpers, crossed, plus one common ground. With both units powered over their own USB (identity is by chip ID, not port):

```
  Main K1 (leader)                    Bench K1 (follower)
  ----------------                    -------------------
  GPIO 15 (TRIG_OUT) ───────────────► GPIO 16 (TRIG_IN)
  GPIO 16 (TRIG_IN)  ◄─────────────── GPIO 15 (TRIG_OUT)
  GND                ───────────────── GND   (common reference — REQUIRED)
```

- Three wires total: main-15 → bench-16, bench-15 → main-16, and a GND↔GND strap.
- The common ground is mandatory: without it the ISR edge reference floats and the wire-truth offset is meaningless.
- No series resistor needed for a short bench jumper (both are 3V3 push-pull GPIOs); keep leads short. Do not connect either trigger line to 5 V.
- These pins are output-low / input at boot for the probe; they are never driven by production firmware (the probe TU is `-DSB_K1_SYNC_PROBE`, non-shippable).

## 2. Serial log-line contract

Both the P0.4 probe firmware and `scripts/dual_sync_probe/` (`logfmt.py`) emit/parse **exactly** these lines. Timestamps are **device-local `micros()`**, 64-bit (no wrap within a probe run). Every field is decimal. Lines may be freely interleaved with unrelated serial noise; the parser skips and counts anything it cannot match, and drops truncated lines.

| Emitter | Line grammar |
|---|---|
| device raised its TRIG_OUT | `[sync_oracle] trig_out seq=<n> t_us=<u64>` |
| device ISR captured its TRIG_IN edge | `[sync_oracle] trig_in seq=<n> t_us=<u64>` |
| follower radio RTT clock estimate | `[k1_sync] clk est_offset_us=<i64> rtt_us=<u32> n=<samples>` |
| leader sent a stream packet | `[k1_sync] tx seq=<n> t_leader_us=<u64>` |
| follower received a stream packet | `[k1_sync] rx seq=<n> t_leader_us=<u64> t_local_us=<u64>` |
| follower applied a packet at render | `[k1_sync] apply seq=<n> t_render_us=<u64>` |
| 1 Hz health telemetry | `[k1_sync] health fps=<f> heap_min=<u32> ap_p95_us=<u32> dial_linked=<0\|1> loss=<u32> dup=<u32>` |

Contract notes that the firmware MUST honour:

- **`seq` pairing across the wire.** Each cross-trigger round `n` fires in BOTH directions and both devices log the SAME `seq=n`: the leader logs `trig_out seq=n` (its send) and `trig_in seq=n` (its capture of the follower's send); the follower logs `trig_in seq=n` and `trig_out seq=n`. The oracle pairs the four events per `seq` to derive the wire-truth offset and the ISR asymmetry bound (both directions).
- **`clk` and `health` carry no timestamp field** (matching the grammar above). The oracle reconstructs their device-local time by interpolating between the nearest timestamped lines in the same log, by line position. Firmware should emit `clk`/`health` interleaved with the timestamped stream so this reconstruction stays tight.
- **Stream `seq` is a dense monotonic counter** on the leader; the oracle derives loss (missing seq), dup (repeated seq) and reorder (out-of-order arrival) from the follower `rx`/`apply` streams.
- **`est_offset_us` is `follower_local − leader_local`** (signed), i.e. the follower's estimate of how far ahead its own clock is of the leader's. The wire-truth offset uses the identical sign so the clock-error series is `est_offset_us − wire_truth`.

The four gate numbers the oracle computes from a leader+follower log pair (thresholds are `gate_eval` defaults):

1. **Clock-offset error** p95 of `|est_offset_us − wire_truth|` ≤ **4000 µs**.
2. **Packet lateness** p99.9 of apply-lateness (follower apply mapped to leader clock, minus `t_leader_us`) ≤ **D = 30000 µs**.
3. **Leader end-to-end** (follower-visible leader-stamp→apply, the longer twin path) worst-case ≤ **50000 µs**.
4. **Health under load** — render FPS floor, `heap_min` above the abort line, Core-0 AP p95 ≤ 7500 µs, dial-link uptime 100 %, zero loss/dup beyond tolerance.

---

**Document Changelog**

| Date | Author | Change |
|------|--------|--------|
| 2026-07-08 | agent:claude-code | Created — GPIO cross-trigger pin audit (TRIG_OUT 15 / TRIG_IN 16, both maps) + shared serial log-line contract for P0.3 oracle and P0.4 firmware. |
